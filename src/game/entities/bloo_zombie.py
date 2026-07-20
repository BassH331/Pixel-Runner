"""
Blood Zombie (Bloo Zombie) enemy entity with skeleton-based combat mechanics.
Specialized variant with enhanced health, unique sprites, and modified behavior.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import TYPE_CHECKING, Final, Optional

import pygame as pg

from v3x_zulfiqar_gideon import AssetManager, Actor, AttackConfig
from src.game.audio.entity_audio_mixin import EntityAudioMixin
from .hitbox_registry import HitboxRegistry
from ..services import ConfigClient

if TYPE_CHECKING:
    from src.game.entities.player import Player


class BloodZombieState(Enum):
    """Enumeration of all possible blood zombie behavioral states."""
    
    DEATH = 0
    HURT = 10
    ATTACK = 20
    CHASE = 30
    IDLE = 40


@dataclass(slots=True)
class StateConfig:
    animation_speed: float = 0.15
    loops: bool = True
    next_state: Optional[BloodZombieState] = None
    interruptible: bool = True


class BloodZombie(EntityAudioMixin, Actor):
    """
    A blood zombie enemy (Bloo Zombie) with enhanced stats and skeleton-based combat.
    Features unique sprites, higher health, and modified attack patterns.
    """
    
    # Class-level attack configurations (immutable)
    ATTACK_1_CONFIG: Final[AttackConfig] = AttackConfig(
        hit_frames=frozenset({6}),
        base_damage=2.0,  # Higher base damage than regular skeletons
        knockback_force=10.0,  # Higher knockback
    )
    
    ATTACK_2_CONFIG: Final[AttackConfig] = AttackConfig(
        hit_frames=frozenset({5, 6}),
        base_damage=1.5,
        knockback_force=6.0,
    )
    
    STATE_CONFIGS: Final[dict[Enum, StateConfig]] = {
        BloodZombieState.IDLE: StateConfig(0.1),
        BloodZombieState.CHASE: StateConfig(0.15),
        BloodZombieState.ATTACK: StateConfig(0.15, loops=False, next_state=BloodZombieState.IDLE, interruptible=False),
        BloodZombieState.HURT: StateConfig(0.15, loops=False, next_state=BloodZombieState.IDLE, interruptible=False),
        BloodZombieState.DEATH: StateConfig(0.15, loops=False, interruptible=False),
    }

    def __init__(
        self,
        x: int,
        y: int,
        player: Player,
        tier: str = "boss",  # Blood Zombie is always a boss variant
        custom_scale: Optional[float] = None,
        custom_health: Optional[float] = None,
        audio_manager=None,
    ) -> None:
        super().__init__(x, y)
        
        self._player: Player = player
        self.state_configs = self.STATE_CONFIGS
        self.tier = tier
        
        # Load hitbox margins specifically for blood_zombie boss
        margins_key = "boss:bloodzombie"  # Specific key for blood zombie boss hitbox data
        margins = HitboxRegistry.get_margins(margins_key)
        
        # Fallback to generic boss margins if specific ones missing
        if margins.scale == 1.0 and margins.ground_offset == 0:
            margins = HitboxRegistry.get_margins("boss")
        
        # Determine scale: explicit custom > registry > default margins
        registry_scale = None
        try:
            if HitboxRegistry.has_custom_margins(margins_key):
                registry_scale = margins.scale
        except Exception:
            pass
        
        self.scale = registry_scale if registry_scale is not None else (custom_scale if custom_scale is not None else margins.scale)
        self._scale_is_explicit = (registry_scale is not None or custom_scale is not None)
        
        # Load default animations first (fallback if sprite loading fails)
        self.animations[BloodZombieState.IDLE] = self._load_frames(
            "assets/graphics/bloodZombie/Idle/blood_idle_{:02d}.png", 10
        )
        self.animations[BloodZombieState.CHASE] = self._load_frames(
            "assets/graphics/bloodZombie/Move/blood_chase_{}.png", 8
        )
        self._attack1_frames = self._load_frames(
            "assets/graphics/bloodZombie/Attack1/blood_attack2_{:02d}.png", 16
        )
        self.animations[BloodZombieState.ATTACK] = self._attack1_frames
        self._attack2_frames = self._load_frames(
            "assets/graphics/bloodZombie/Attack2/blood_attack1_{:02d}.png", 16
        )
        self.animations[BloodZombieState.HURT] = self._load_frames(
            "assets/graphics/bloodZombie/Hurt/blood_hurt_{}.png", 6
        )
        self.animations[BloodZombieState.DEATH] = self._load_frames(
            "assets/graphics/bloodZombie/Death/blood_death_{}.png", 6
        )
        
        # Apply Tier Scaling (Health, Speed, Size)
        damage_scale = 1.0
        knockback_scale = 1.0
        
        if self.tier == "boss":
            # Apply boss scaling (already applied via sprite loading in skeleton logic, but adjust here too)
            if not self._scale_is_explicit:
                self.scale *= 1.8
                # Scale all animation frames
                for state in list(self.animations.keys()):
                    self.animations[state] = [
                        pg.transform.scale(img, (int(img.get_width() * 1.8), int(img.get_height() * 1.8)))
                        for img in self.animations[state]
                    ]
                self._attack1_frames = [
                    pg.transform.scale(img, (int(img.get_width() * 1.8), int(img.get_height() * 1.8)))
                    for img in self._attack1_frames
                ]
                self._attack2_frames = [
                    pg.transform.scale(img, (int(img.get_width() * 1.8), int(img.get_height() * 1.8)))
                    for img in self._attack2_frames
                ]
            
            self._max_health = custom_health if custom_health is not None else 180.0  # Higher than regular skeleton boss
            self._speed = 3.0
            damage_scale = 3.5
            knockback_scale = 2.0
            
            # Blood Zombie specific AI parameters
            self._detection_range = 3500
            self._attack_range = 90
            self._vertical_tolerance = 600
        else:  # Should not happen for blood zombie but keep for completeness
            self._max_health = custom_health if custom_health is not None else 90.0
            self._speed = 2.8
            damage_scale = 1.8
            knockback_scale = 1.5
            self._detection_range = 1200
            self._attack_range = 70
            self._vertical_tolerance = 200
        
        self._attack_hitbox_width = 70
        self._attack_hitbox_height = 90
        
        # Load configuration from config service
        try:
            config = ConfigClient.fetch_config("enemy_blood_zombie")
            if config:
                self._max_health = float(config.get("max_health", self._max_health))
                self._speed = float(config.get("speed", self._speed))
                damage_scale = float(config.get("damage_scale", damage_scale))
                knockback_scale = float(config.get("knockback_scale", knockback_scale))
                self._detection_range = int(config.get("detection_range", self._detection_range))
                self._attack_range = int(config.get("attack_range", self._attack_range))
                self._vertical_tolerance = int(config.get("vertical_tolerance", self._vertical_tolerance))
                self._attack_hitbox_width = int(config.get("attack_hitbox_width", self._attack_hitbox_width))
                self._attack_hitbox_height = int(config.get("attack_hitbox_height", self._attack_hitbox_height))
        except Exception as e:
            print(f"[WARNING] Error loading blood zombie config: {e}")
        
        # Apply damage and knockback scaling
        if custom_health is not None:
            self._max_health = custom_health
        self._health: float = self._max_health
        
        self.attack1_config = AttackConfig(
            hit_frames=self.ATTACK_1_CONFIG.hit_frames,
            base_damage=self.ATTACK_1_CONFIG.base_damage * damage_scale,
            knockback_force=self.ATTACK_1_CONFIG.knockback_force * knockback_scale,
        )
        self.attack2_config = AttackConfig(
            hit_frames=self.ATTACK_2_CONFIG.hit_frames,
            base_damage=self.ATTACK_2_CONFIG.base_damage * damage_scale,
            knockback_force=self.ATTACK_2_CONFIG.knockback_force * knockback_scale,
        )
        
        # Initial setup
        self.set_state(BloodZombieState.IDLE)
        if self.state in self.animations:
            self.image = self.animations[self.state][0]
        self.rect: pg.Rect = self.image.get_rect(midbottom=(x, y))
        
        # Hitbox adjustment using blood zombie specific margins
        self.adjust_hitbox_sides(left=margins.left, right=margins.right, top=margins.top, bottom=margins.bottom)
        
        # Movement and physics
        self._gravity: float = 0.0
        surf = pg.display.get_surface()
        height = surf.get_height() if surf else 720
        self._ground_y: int = height - margins.ground_offset
        
        # AI configuration
        if not hasattr(self, "_detection_range"):
            self._detection_range = 3500 if self.tier == "boss" else 1200
        if not hasattr(self, "_attack_range"):
            self._attack_range = 90 if self.tier == "boss" else 70
        if not hasattr(self, "_vertical_tolerance"):
            self._vertical_tolerance = 600 if self.tier == "boss" else 200
        self.spawn_zone: Optional[dict] = None
        
        # Precalculate scaled hitbox dimensions for performance
        self._scaled_hitbox_w: int = int(self._attack_hitbox_width * self.scale)
        self._scaled_hitbox_h: int = int(self._attack_hitbox_height * self.scale)

        # Audio trigger system (non-fatal; gracefully skipped if audio_manager is None)
        self._init_entity_audio_config(audio_manager, "blood_zombie")

    def _load_frames(
        self,
        path_pattern: str,
        count: int,
        scale_factor: Optional[float] = None,
    ) -> list[pg.Surface]:
        """
        Load and scale animation frames from a file pattern.
        
        Args:
            path_pattern: Format string for frame paths with index placeholder.
            count: Number of frames to load (0-indexed).
            scale_factor: Multiplier for sprite dimensions (defaults to self.scale).
            
        Returns:
            List of scaled pygame Surface objects.
            
        Raises:
            RuntimeError: If no frames could be loaded from the pattern.
        """
        if scale_factor is None:
            scale_factor = self.scale
        
        frames: list[pg.Surface] = []
        
        for i in range(count):
            path = path_pattern.format(i)
            try:
                frame = AssetManager.get_texture(path)
                original_size = frame.get_size()
                scaled_size = (
                    int(original_size[0] * scale_factor),
                    int(original_size[1] * scale_factor),
                )
                scaled_frame = pg.transform.scale(frame, scaled_size)
                frames.append(scaled_frame)
            except (FileNotFoundError, pg.error) as e:
                print(f"Warning: Failed to load frame {i} from '{path}': {e}")
                
        if not frames:
            raise RuntimeError(f"Failed to load any frames from pattern: {path_pattern}")
            
        return frames

    # ─────────────────────────────────────────────────────────────────────────
    # Public API: Combat and State Inspection
    # ─────────────────────────────────────────────────────────────────────────

    @property
    def health(self) -> float: return self._health
    @property
    def max_health(self) -> float: return self._max_health
    @property
    def entity_id(self) -> int: return id(self)
    @property
    def is_dead(self) -> bool: return self.state == BloodZombieState.DEATH
    @property
    def current_frame_index(self) -> int: return int(self.animation_index)

    def is_in_hit_frame(self) -> bool:
        return self.attack_state.is_hit_frame_active()

    def should_deal_damage(self) -> bool:
        return self.attack_state.is_hit_frame_active()

    def register_hit(self, target_id: int = 0) -> bool:
        return self.attack_state.try_register_hit(target_id)

    def try_register_hit(self, target_id: int) -> bool:
        return self.attack_state.try_register_hit(target_id)

    def get_current_attack_damage(self) -> float:
        return self.attack_state.get_current_damage()

    def get_current_attack_knockback(self) -> float:
        return self.attack_state.config.knockback_force if self.attack_state.config else 0.0

    def get_attack_hitbox(self) -> Optional[pg.Rect]:
        """Return the attack hitbox based on blood zombie facing and position."""
        if not self.should_deal_damage():
            return None
        hitbox_w = self._scaled_hitbox_w
        hitbox_h = self._scaled_hitbox_h
        if self.facing_left:
            hitbox_x = self.rect.left - hitbox_w
        else:
            hitbox_x = self.rect.right
        hitbox_y = self.rect.centery - hitbox_h // 2
        return pg.Rect(hitbox_x, hitbox_y, hitbox_w, hitbox_h)

    def update(self, dt: Optional[float] = None, scroll_speed: int = 0) -> None:
        if dt is None: dt = 1.0 / 60.0
        self.rect.x -= scroll_speed
        
        self._apply_gravity()
        self._update_ai()
        
        super().update(dt)  # Handles state machines and animations
        self._update_animation_audio()
        
        # Cleanup on death animation completion
        if self.state == BloodZombieState.DEATH and int(self.animation_index) >= len(self.animations[BloodZombieState.DEATH]) - 1:
            self.kill()

    def take_damage(self, amount: float = 0.5, knockback: tuple[float, float] | None = None) -> None:
        """
        Reduce the blood zombie's health and switch its animation state.
        
        Important:
        This method does NOT play sound directly.
        Reason:
        The BloodZombie class should only care about zombie logic:
        - health
        - attack state
        - hurt state
        - death state
        
        Audio is handled in GameState because GameState owns the audio manager
        and knows which gameplay event just happened.
        """
        # Do not allow repeated damage while already hurt or dead
        if self.state in (BloodZombieState.HURT, BloodZombieState.DEATH):
            return
        
        # Reduce health, but never allow health to go below 0
        self._health = max(0, self._health - amount)
        
        # If the zombie was attacking, cancel the attack
        self.attack_state.end()
        
        # If health is depleted, switch to death animation
        if self._health <= 0:
            self.set_state(BloodZombieState.DEATH, force=True)
        # Otherwise, switch to hurt animation
        else:
            self.set_state(BloodZombieState.HURT, force=True)

    # ─────────────────────────────────────────────────────────────────────────
    # Private: AI Logic
    # ─────────────────────────────────────────────────────────────────────────

    def _update_ai(self) -> None:
        if self._player is None or self.state in (BloodZombieState.HURT, BloodZombieState.DEATH):
            return
            
        player_rect = self._player.rect
        dist_x = abs(self.rect.centerx - player_rect.centerx)
        dist_y = abs(self.rect.centery - player_rect.centery)
        
        if self.state == BloodZombieState.ATTACK:
            return
            
        if dist_x < self._attack_range and dist_y < self._vertical_tolerance:
            self._begin_attack()
        elif dist_x < self._detection_range and dist_y < self._vertical_tolerance:
            self.set_state(BloodZombieState.CHASE)
        else:
            self.set_state(BloodZombieState.IDLE)
            
        if self.state == BloodZombieState.CHASE:
            self._chase_player(player_rect)

    def _begin_attack(self) -> None:
        if random.random() < 0.5:
            # Primary attack animation
            self.animations[BloodZombieState.ATTACK] = self._attack1_frames
            self.current_attack_config = self.attack1_config
        else:
            # Secondary attack animation
            self.animations[BloodZombieState.ATTACK] = self._attack2_frames
            self.current_attack_config = self.attack2_config
        self.set_state(BloodZombieState.ATTACK)

    def _chase_player(self, player_rect: pg.Rect) -> None:
        if self.rect.centerx > player_rect.centerx:
            self.rect.x -= int(self._speed)
            self.facing_left = True
        else:
            self.rect.x += int(self._speed)
            self.facing_left = False

    # ─────────────────────────────────────────────────────────────────────────
    # Private: Physics
    # ─────────────────────────────────────────────────────────────────────────

    def _apply_gravity(self) -> None:
        """Apply gravitational acceleration and ground collision."""
        self._gravity += 1.0
        self.rect.y += int(self._gravity)
        
        # Ground collision
        if self.rect.bottom >= self._ground_y:
            self.rect.bottom = self._ground_y
            self._gravity = 0.0

    # ─────────────────────────────────────────────────────────────────────────
    # Rendering
    # ─────────────────────────────────────────────────────────────────────

    def draw(self, surface: pg.Surface) -> None:
        """
        Draw the blood zombie and UI elements.
        
        Args:
            surface: Target surface for rendering.
        """
        super().draw(surface)
        
        # Draw health bar when damaged and alive
        if self._health < self._max_health and self.state != BloodZombieState.DEATH:
            self._draw_health_bar(surface)

    def _draw_health_bar(self, surface: pg.Surface) -> None:
        """Render the health bar above the blood zombie."""
        bar_width: int = 50
        bar_height: int = 6
        bar_x: int = self.rect.centerx - bar_width // 2
        bar_y: int = self.rect.top - 12
        
        # Background (empty health)
        pg.draw.rect(
            surface,
            (40, 40, 40),
            (bar_x, bar_y, bar_width, bar_height),
        )
        
        # Current health (dark red fill for blood zombie theme)
        health_ratio = self._health / self._max_health
        pg.draw.rect(
            surface,
            (180, 0, 0),
            (bar_x, bar_y, int(bar_width * health_ratio), bar_height),
        )