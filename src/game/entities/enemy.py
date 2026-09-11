import pygame as pg
import random
import math
from enum import Enum
from v3x_zulfiqar_gideon import Actor, AssetManager
from .hitbox_registry import HitboxRegistry
from src.game.audio.entity_audio_mixin import EntityAudioMixin

class EnemyState(Enum):
    FLY = 0

class BatFlightState(Enum):
    FLAP_BURST = 0  # Rapid consecutive wing flaps (up-up-up)
    GLIDE = 1       # Slow descent on air cushion with wings outstretched

class EnemyStateConfig:
    def __init__(self, animation_speed: float):
        self.animation_speed = animation_speed
        self.loops = True
        self.frame_speeds = None
        self.next_state = None

class Enemy(EntityAudioMixin, Actor):
    """
    Base class for all enemy entities in the game.
    Handles common enemy behaviors like movement, animation, and collision.
    """
    _fly_frames_caches: dict[float, list[pg.Surface]] = {}

    # Shadow rendering constants (shared across all bat instances)
    _SHADOW_SQUASH: float = 0.25
    _SHADOW_ALPHA: int = 45
    _SHADOW_FADE_HEIGHT: float = 400.0
    _SHADOW_Y_OFFSET: int = -4
    _SHADOW_GROUND_OFFSET: int = 34  # Same ground offset as the player

    def __init__(self, audio_manager=None):
        super().__init__(0, 0)
        self._bat_audio_manager = audio_manager  # store for post-init setup
        
        # Load bat configuration via ConfigClient
        from src.game.services.config_client import ConfigClient
        bat_config = ConfigClient.fetch_config("enemy_bat") or {}
        config_scale = float(bat_config.get("scale", 1.0))
        config_speed = float(bat_config.get("speed", 250.0))
        
        # Load margins and base scale
        margins = HitboxRegistry.get_margins("enemy")
        base_scale = margins.scale * config_scale
        
        # Add slight variation to scale to simulate depth (near/far bats)
        # Scale variation: 0.85 to 1.15 of base scale, rounded to 1 decimal place to keep cache small
        self.depth_scale_factor = 0.85 + random.random() * 0.30
        scale = round(base_scale * self.depth_scale_factor, 1)
        # Store actual scale factor relative to the base scale
        self.depth_scale_factor = scale / base_scale
        
        # Load frames only once per scale if not already cached
        if scale not in Enemy._fly_frames_caches:
            cache = []
            try:
                for i in range(8):
                    path = f"assets/graphics/bat/running/bat_running_{i}.png"
                    frame = AssetManager.get_texture(path)
                    
                    original_size = frame.get_size()
                    scaled_size = (int(original_size[0] * scale), int(original_size[1] * scale))
                    
                    scaled_frame = pg.transform.scale(frame, scaled_size)
                    cache.append(scaled_frame)
            except Exception as e:
                print(f"Error loading bat animation for scale {scale}: {e}")
                cache = [pg.Surface((int(25 * scale), int(25 * scale)), pg.SRCALPHA) for _ in range(8)]
            Enemy._fly_frames_caches[scale] = cache
        
        # Use actor system
        self.animations = {EnemyState.FLY: Enemy._fly_frames_caches[scale]}
        
        # Relative speed ratio compared to default 250.0 px/s baseline
        speed_ratio = max(0.1, config_speed / 250.0)

        # Randomize flapping speed to give a natural, non-synchronized feel,
        # scaled inversely with speed_ratio so higher speed flaps faster (lower frame duration)
        random_flap_speed = (0.12 + random.random() * 0.12) / speed_ratio
        self.state_configs = {
            EnemyState.FLY: EnemyStateConfig(animation_speed=random_flap_speed)
        }
        
        self.set_state(EnemyState.FLY)
        
        # Randomize the initial animation frame so bats do not flap in perfect phase unison
        num_frames = len(self.animations[EnemyState.FLY])
        self.animation_index = random.uniform(0.0, float(num_frames))
        
        # Normalized flapping ratio (0.0 for slowest, 1.0 for fastest)
        flap_ratio = ((random_flap_speed * speed_ratio) - 0.12) / 0.12
        
        # Movement properties physically coupled to the wing flap speed + depth parallax:
        # 1. Horizontal speed: faster flapping = faster horizontal flight (range: -2.0 to -4.0 scaled by speed_ratio)
        # We also scale by depth_scale_factor to simulate 3D perspective parallax (farther = slower)
        self.speed = (-2.0 - flap_ratio * 2.0) * speed_ratio * self.depth_scale_factor
        
        # -------------------------------------------------------------
        # Flight Physics & Aerodynamics Configuration
        # -------------------------------------------------------------
        self._cfg_gravity = float(bat_config.get("gravity", 220.0))
        self._cfg_flap_power = float(bat_config.get("flap_power", 175.0))
        self._cfg_glide_duration = float(bat_config.get("glide_duration", 0.8))

        # Individualized personality variance (+/- 15% entropy per bat)
        entropy = 0.85 + random.random() * 0.30
        self.bat_gravity = self._cfg_gravity * entropy
        self.bat_flap_power = self._cfg_flap_power * (1.15 - (entropy - 0.85))
        self.bat_base_glide_dur = self._cfg_glide_duration * (0.8 + random.random() * 0.4)

        # Sub-pixel position & vertical physics
        self._y_base: float = 0.0
        self.pos_y: float = 0.0
        self.vel_y: float = 0.0
        self._pos_y_initialized: bool = False

        # Flight state machine: FLAP_BURST ("up-up-up") vs GLIDE (slow cushioned descent)
        self.flight_state = BatFlightState.FLAP_BURST
        self.burst_flaps_target = random.choices([1, 2, 3, 4], weights=[15, 45, 30, 10])[0]
        self.flaps_completed = 0
        self.flap_interval = (0.16 + random.random() * 0.06) / speed_ratio
        self.flap_interval_timer = 0.0
        self.glide_timer = 0.0
        self.glide_duration = self.bat_base_glide_dur

        # Setup separation/steering variables
        self.y_avoid_offset = 0.0
        self.y_avoid_vel = 0.0
        
        # Setup rectangle
        if self.state in self.animations:
            self.image = self.animations[self.state][int(self.animation_index) % num_frames]
        self.rect = self.image.get_rect()
        # Reduce hitbox using the margins loaded from the HitboxRegistry
        margins = HitboxRegistry.get_margins("enemy")
        self.adjust_hitbox_sides(left=margins.left, right=margins.right, top=margins.top, bottom=margins.bottom)

        # Audio trigger system (non-fatal; gracefully skipped if audio_manager is None)
        self._init_entity_audio_config(self._bat_audio_manager, "bat")

        # Shadow system: compute ground plane from screen height
        surf = pg.display.get_surface()
        screen_h = surf.get_height() if surf else 720
        self._ground_y: int = screen_h - self._SHADOW_GROUND_OFFSET
        self._shadow_cache: dict[tuple, pg.Surface] = {}

    @property
    def y_base(self) -> float:
        return self._y_base

    @y_base.setter
    def y_base(self, val: float):
        self._y_base = val
        if not getattr(self, "_pos_y_initialized", False) or self.pos_y == 0.0:
            self.pos_y = val
            self._pos_y_initialized = True

    def take_damage(self, amount: float, knockback: tuple[float, float] | None = None) -> None:
        """Apply damage to this enemy. Override in subclasses."""
        pass

    def update_flight_physics(self, dt: float):
        """Update aerodynamic forces, flap impulses, and altitude corridor integration."""
        if not self._pos_y_initialized:
            self.pos_y = float(self.rect.y if self.rect.y != 0 else self.y_base)
            self._pos_y_initialized = True

        dist_from_ceiling = self.pos_y - (self.y_base - 40.0)  # negative if above ceiling
        dist_from_floor = self.pos_y - (self.y_base + 45.0)    # positive if below floor

        if self.flight_state == BatFlightState.FLAP_BURST:
            # Wingbeat cycle countdown
            self.flap_interval_timer -= dt
            if self.flap_interval_timer <= 0.0:
                # Deliver discrete upward flap impulse
                impulse = self.bat_flap_power * random.uniform(0.90, 1.15)
                self.vel_y = -impulse
                self.flaps_completed += 1
                self.flap_interval_timer = self.flap_interval

                # End burst if quota reached or bat has climbed above ceiling
                if self.flaps_completed >= self.burst_flaps_target or dist_from_ceiling < 0:
                    self.flight_state = BatFlightState.GLIDE
                    self.glide_timer = 0.0
                    self.glide_duration = self.bat_base_glide_dur * random.uniform(0.7, 1.3)
                    self.flaps_completed = 0
                    self.burst_flaps_target = random.choices([1, 2, 3, 4], weights=[15, 45, 30, 10])[0]

        elif self.flight_state == BatFlightState.GLIDE:
            self.glide_timer += dt
            # Trigger new flap burst when glide ends or bat drops below floor
            if self.glide_timer >= self.glide_duration or dist_from_floor > 0:
                self.flight_state = BatFlightState.FLAP_BURST
                self.flap_interval_timer = 0.0  # Immediate initial flap

        # -------------------------------------------------------------
        # Physics Integration: Gravity, Drag, and Corridor Tethering
        # -------------------------------------------------------------
        if self.vel_y < 0:
            # Ascending from flap: gravity acts against upward momentum
            self.vel_y += self.bat_gravity * 0.9 * dt
        else:
            # Descending: aerodynamic drag creates air cushion (slow, floaty descent)
            drag = 0.94 ** (dt * 60.0)
            self.vel_y = (self.vel_y + self.bat_gravity * dt) * drag
            if self.flight_state == BatFlightState.GLIDE:
                self.vel_y = min(self.vel_y, 95.0)  # Gentle glide speed cap

        # Soft corridor spring tethering to keep bat around cruising altitude y_base
        tether_force = (self.y_base - self.pos_y) * 1.8
        self.vel_y += tether_force * dt

        # Sub-pixel position integration
        self.pos_y += self.vel_y * dt
        self.rect.y = int(self.pos_y + self.y_avoid_offset)

    def update(self, dt=None, scroll_speed=0):
        """
        Update enemy state each frame.
        """
        if dt is None:
            dt = 1.0 / 60.0
        dt_sec = dt / 1000.0 if dt > 1.0 else dt

        # Apply scrolling (move left with the world)
        self.rect.x -= scroll_speed
        
        # Horizontal flight with burst propulsion:
        # Thrust boost during wing flap bursts, gentle glide during rest
        h_boost = 1.15 if self.flight_state == BatFlightState.FLAP_BURST else 0.90
        self.rect.x += int(self.speed * h_boost)
        
        # Calculate separation force from other bats in the same group to steer around each other
        separation_y = 0.0
        groups = self.groups()
        if groups:
            for other in groups[0]:
                if other is not self and isinstance(other, Enemy):
                    # Check distance
                    dx = self.rect.centerx - other.rect.centerx
                    dy = self.rect.centery - other.rect.centery
                    dist = math.hypot(dx, dy)
                    if dist < 45: # avoidance radius
                        if dist == 0:
                            dist = 0.1
                        push_strength = (45 - dist) / 45.0
                        # Push vertically based on relative position, breaking tie if centery matches
                        y_direction = (dy / dist) if dist > 0 else (1.0 if id(self) > id(other) else -1.0)
                        if abs(dy) < 5:
                            y_direction = 1.0 if self.rect.centery >= other.rect.centery else -1.0
                        separation_y += y_direction * push_strength * 3.0

        # Apply separation to vertical velocity with damping
        self.y_avoid_vel = self.y_avoid_vel * 0.85 + separation_y * 0.15
        self.y_avoid_offset += self.y_avoid_vel
        
        # Decay vertical offset back to 0 when far apart
        if abs(separation_y) < 0.05:
            self.y_avoid_offset *= 0.95
            
        # Update flight physics state machine and vertical motion
        self.update_flight_physics(dt_sec)
        
        # Remove if off-screen to the left
        if self.rect.right < 0:
            self.kill()
            
        if self.flight_state == BatFlightState.GLIDE:
            # During glide, hold wings-outstretched glide frame (Frame 0)
            if self.state in self.animations and self.animations[self.state]:
                self.image = self.animations[self.state][0]
            self._update_animation_audio()
        else:
            super().update(dt)  # Actor handles animation and base components
            self._update_animation_audio()

    def _generate_shadow_surface(self, source: pg.Surface, scale_factor: float = 1.0) -> pg.Surface:
        """Generate a squashed black silhouette for a bat shadow."""
        frame_idx = int(self.animation_index)
        cache_key = (frame_idx, scale_factor >= 1.0)

        if scale_factor >= 1.0 and cache_key in self._shadow_cache:
            return self._shadow_cache[cache_key]

        shadow = source.copy()
        shadow.fill((0, 0, 0), special_flags=pg.BLEND_RGB_MIN)

        w = max(1, int(shadow.get_width() * scale_factor))
        h = max(1, int(shadow.get_height() * self._SHADOW_SQUASH * scale_factor))
        shadow = pg.transform.smoothscale(shadow, (w, h))

        alpha = int(self._SHADOW_ALPHA * min(scale_factor, 1.0))
        shadow.set_alpha(max(0, alpha))

        if scale_factor >= 1.0:
            self._shadow_cache[cache_key] = shadow

        return shadow

    def draw(self, surface: pg.Surface) -> None:
        """Draw the bat with a ground-projected shadow beneath it."""
        # ── Shadow ────────────────────────────────────────────────────────
        if self.image is not None:
            air_height = max(0, self._ground_y - self.rect.bottom)

            if air_height >= self._SHADOW_FADE_HEIGHT:
                scale_factor = 0.0
            else:
                # Scale shadow by depth factor so farther bats cast smaller shadows
                scale_factor = (1.0 - (air_height / self._SHADOW_FADE_HEIGHT)) * self.depth_scale_factor

            if scale_factor > 0.05:
                shadow_surf = self._generate_shadow_surface(self.image, scale_factor)

                draw_pos = self.rect.topleft - self.image_offset
                shadow_x = draw_pos[0] + (self.image.get_width() - shadow_surf.get_width()) // 2
                shadow_y = self._ground_y - shadow_surf.get_height() + self._SHADOW_Y_OFFSET

                surface.blit(shadow_surf, (shadow_x, shadow_y))

        # ── Bat sprite ────────────────────────────────────────────────────
        super().draw(surface)
