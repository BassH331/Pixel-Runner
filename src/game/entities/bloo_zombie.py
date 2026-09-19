"""
Blood Zombie (Bloo Zombie) enemy entity with skeleton-based combat mechanics.
Specialized variant with enhanced health, unique sprites, and modified behavior.
"""

from __future__ import annotations

import os
import math
import random
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import TYPE_CHECKING, Final, Optional

import pygame as pg

from v3x_zulfiqar_gideon import AssetManager, Actor, AttackConfig
from src.game.audio.entity_audio_mixin import EntityAudioMixin
from .hitbox_registry import HitboxRegistry
from ..services import ConfigClient
from src.game.ai import PerceptionSystem, AlertLevel, SquadTokenManager, SquadCoordinator, SquadRole, UtilityCombatEngine, TacticalAction

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
        sprite_root: Optional[str] = None,
        behaviour_map: Optional[dict[str, str]] = None,
        tier: str = "boss",  # Blood Zombie is always a boss variant
        custom_scale: Optional[float] = None,
        custom_health: Optional[float] = None,
        audio_manager=None,
    ) -> None:
        super().__init__(x, y)

        self._player: Player = player
        self._ghost_trail = []
        self.natively_facing_left: bool = False
        self.state_configs = self.STATE_CONFIGS
        self.tier = tier

        # Load hitbox margins specifically for blood_zombie boss
        margins_key = "boss:bloodzombie"
        margins = HitboxRegistry.get_margins(margins_key)

        if margins.scale == 1.0 and margins.ground_offset == 0:
            margins = HitboxRegistry.get_margins("boss")

        registry_scale = None
        try:
            if HitboxRegistry.has_custom_margins(margins_key):
                registry_scale = margins.scale
        except Exception:
            pass

        # Fetch configuration from ConfigClient as primary single source of truth
        config: dict = {}
        try:
            config = ConfigClient.fetch_config("enemy_blood_zombie") or {}
        except Exception as e:
            print(f"[WARNING] Error fetching blood zombie config: {e}")

        # Resolve entity scale (editor config > explicit custom_scale > HitboxRegistry)
        if "scale" in config:
            self.scale = float(config["scale"])
        elif custom_scale is not None:
            self.scale = float(custom_scale)
        elif registry_scale is not None:
            self.scale = float(registry_scale)
        else:
            self.scale = float(margins.scale)

        # Load animation frames dynamically from assets/graphics/bloodZombie folders
        def load_dir_frames(folder_path: str) -> list[pg.Surface]:
            if not os.path.exists(folder_path):
                return []
            files = sorted([f for f in os.listdir(folder_path) if f.endswith(".png")])
            frames = []
            for fname in files:
                full_p = os.path.join(folder_path, fname)
                try:
                    img = pg.image.load(full_p).convert_alpha()
                    w = int(img.get_width() * self.scale)
                    h = int(img.get_height() * self.scale)
                    frames.append(pg.transform.scale(img, (w, h)))
                except Exception:
                    pass
            return frames

        base_dir = sprite_root if (sprite_root and os.path.exists(sprite_root)) else "assets/graphics/bloodZombie"

        idle_frames = load_dir_frames(os.path.join(base_dir, "Idle"))
        move_frames = load_dir_frames(os.path.join(base_dir, "Move"))
        atk1_frames = load_dir_frames(os.path.join(base_dir, "Attack1"))
        atk2_frames = load_dir_frames(os.path.join(base_dir, "Attack2"))
        death_frames = load_dir_frames(os.path.join(base_dir, "Death"))

        self.animations[BloodZombieState.IDLE] = idle_frames
        self.animations[BloodZombieState.CHASE] = move_frames if move_frames else idle_frames
        self._attack1_frames = atk1_frames if atk1_frames else idle_frames
        self._attack2_frames = atk2_frames if atk2_frames else self._attack1_frames
        self.animations[BloodZombieState.ATTACK] = self._attack1_frames
        self.animations[BloodZombieState.DEATH] = death_frames if death_frames else idle_frames
        self.animations[BloodZombieState.HURT] = idle_frames

        # Extract stats from config (with tier-appropriate fallbacks)
        default_hp = 180.0 if self.tier == "boss" else 90.0
        self._max_health = float(config.get("max_health", custom_health if custom_health is not None else default_hp))
        self._health: float = self._max_health
        self._speed = float(config.get("speed", 3.0 if self.tier == "boss" else 2.8))

        damage_scale = float(config.get("damage_scale", 3.5 if self.tier == "boss" else 1.8))
        knockback_scale = float(config.get("knockback_scale", 2.0 if self.tier == "boss" else 1.5))
        
        self._detection_range = int(config.get("detection_range", 3500 if self.tier == "boss" else 1200))
        self._attack_range = int(config.get("attack_range", 108 if self.tier == "boss" else 70))
        self._vertical_tolerance = int(config.get("vertical_tolerance", 600 if self.tier == "boss" else 200))
        self._attack_hitbox_width = int(config.get("attack_hitbox_width", 70))
        self._attack_hitbox_height = int(config.get("attack_hitbox_height", 90))
        self.frame_offsets = config.get("frame_offsets", {})

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
        if self.state in self.animations and self.animations[self.state]:
            self.image = self.animations[self.state][0]
        self.rect: pg.Rect = self.image.get_rect(midbottom=(x, y)) if self.image else pg.Rect(x, y, 64, 64)
        
        # Hitbox adjustment using blood zombie specific margins
        self.adjust_hitbox_sides(left=margins.left, right=margins.right, top=margins.top, bottom=margins.bottom)
        
        # Movement and physics
        self._gravity: float = 0.0
        surf = pg.display.get_surface()
        height = surf.get_height() if surf else 720
        self._ground_y: Optional[int] = height - margins.ground_offset
        
        # AI configuration & perception components
        if not hasattr(self, "_detection_range"):
            self._detection_range = 3500 if self.tier == "boss" else 1200
        if not hasattr(self, "_attack_range"):
            self._attack_range = 90 if self.tier == "boss" else 70
        if not hasattr(self, "_vertical_tolerance"):
            self._vertical_tolerance = 600 if self.tier == "boss" else 200
        self.spawn_zone: Optional[dict] = None

        self.perception = PerceptionSystem(
            vision_range=float(self._detection_range),
            hearing_range=700.0,
            reaction_delay_sec=0.20,
        )
        self.utility_engine = UtilityCombatEngine(
            has_dash_evasion=False,
            has_block_anim=False,
            preferred_spacing=float(self._attack_range),
        )
        SquadTokenManager.get_instance().register_enemy(id(self), self.tier)

        # Precalculate scaled hitbox dimensions for performance
        self._scaled_hitbox_w: int = int(self._attack_hitbox_width * self.scale)
        self._scaled_hitbox_h: int = int(self._attack_hitbox_height * self.scale)

        # Telemetry and metadata tracking fields for behavioral analysis
        self._last_ai_action: str = "IDLE"
        self._attack_count: int = 0
        self.behavior_metadata: dict = {}

        # Procedural Hit Reaction Engine (Juice & Combat Feel)
        self._hit_flash_duration: float = float(config.get("hit_flash_duration", 0.12))
        self._hit_recoil_dist: float = float(config.get("hit_recoil_dist", 12.0))
        self._squash_stretch_enabled: bool = bool(config.get("squash_stretch_enabled", True))
        self._hit_flash_timer: float = 0.0
        self._hit_recoil_dx: float = 0.0

        # Force Field Orb Shield System
        self._shield_enabled: bool = bool(config.get("shield_enabled", True))
        self._shield_radius_base: float = float(config.get("shield_radius", 55.0))
        self._shield_color: tuple[int, int, int] = (230, 40, 70)
        self._shield_pulse_time: float = 0.0

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
    @property
    def last_ai_action(self) -> str: return self._last_ai_action
    @property
    def attack_count(self) -> int: return self._attack_count

    def apply_config(self, config: dict) -> None:
        """Dynamically apply configuration updates to the Blood Zombie entity at runtime."""
        if not config or not isinstance(config, dict):
            return

        try:
            if "max_health" in config:
                new_max = float(config["max_health"])
                if new_max > 0:
                    health_ratio = self._health / self._max_health if self._max_health > 0 else 1.0
                    self._max_health = new_max
                    self._health = self._max_health * health_ratio

            if "speed" in config:
                self._speed = float(config["speed"])

            if "detection_range" in config:
                self._detection_range = int(config["detection_range"])
                if hasattr(self, "perception"):
                    self.perception.vision_range = float(self._detection_range)

            if "attack_range" in config:
                self._attack_range = int(config["attack_range"])
                if hasattr(self, "utility_engine"):
                    self.utility_engine.preferred_spacing = float(self._attack_range)

            if "vertical_tolerance" in config:
                self._vertical_tolerance = int(config["vertical_tolerance"])

            if "attack_hitbox_width" in config:
                self._attack_hitbox_width = int(config["attack_hitbox_width"])
                self._scaled_hitbox_w = int(self._attack_hitbox_width * self.scale)

            if "attack_hitbox_height" in config:
                self._attack_hitbox_height = int(config["attack_hitbox_height"])
                self._scaled_hitbox_h = int(self._attack_hitbox_height * self.scale)

            if "damage_scale" in config or "knockback_scale" in config:
                dmg_s = float(config.get("damage_scale", 1.0))
                kb_s = float(config.get("knockback_scale", 1.0))
                self.attack1_config = AttackConfig(
                    hit_frames=self.ATTACK_1_CONFIG.hit_frames,
                    base_damage=self.ATTACK_1_CONFIG.base_damage * dmg_s,
                    knockback_force=self.ATTACK_1_CONFIG.knockback_force * kb_s,
                )
                self.attack2_config = AttackConfig(
                    hit_frames=self.ATTACK_2_CONFIG.hit_frames,
                    base_damage=self.ATTACK_2_CONFIG.base_damage * dmg_s,
                    knockback_force=self.ATTACK_2_CONFIG.knockback_force * kb_s,
                )

            if "ground_offset" in config:
                ground_off = int(config["ground_offset"])
                surf = pg.display.get_surface()
                height = surf.get_height() if surf else 720
                self._ground_y = height - ground_off
                if self.rect:
                    self.rect.bottom = self._ground_y

            if "frame_offsets" in config:
                self.frame_offsets = config["frame_offsets"]

            if "hit_flash_duration" in config:
                self._hit_flash_duration = float(config["hit_flash_duration"])

            if "hit_recoil_dist" in config:
                self._hit_recoil_dist = float(config["hit_recoil_dist"])

            if "squash_stretch_enabled" in config:
                self._squash_stretch_enabled = bool(config["squash_stretch_enabled"])

            if "shield_enabled" in config:
                self._shield_enabled = bool(config["shield_enabled"])

            if "shield_radius" in config:
                self._shield_radius_base = float(config["shield_radius"])

            if "shield_color" in config and isinstance(config["shield_color"], (list, tuple)):
                self._shield_color = tuple(config["shield_color"][:3])
        except Exception as e:
            print(f"[WARNING] Error applying blood zombie config overrides: {e}")

    def get_metadata(self) -> dict:
        """Return rich metadata tracking structure for debugging and behavioral telemetry."""
        player_rect = getattr(self._player, "rect", None) if self._player else None
        px = player_rect.centerx if player_rect else None
        py = player_rect.centery if player_rect else None

        center_dist_x = abs(self.rect.centerx - px) if px is not None else None
        if player_rect and self.rect:
            if self.rect.right < player_rect.left:
                edge_dist_x = float(player_rect.left - self.rect.right)
            elif player_rect.right < self.rect.left:
                edge_dist_x = float(self.rect.left - player_rect.right)
            else:
                edge_dist_x = 0.0
        else:
            edge_dist_x = None

        dist_y = abs(self.rect.centery - py) if py is not None else None

        return {
            "entity_id": id(self),
            "entity_type": "blood_zombie",
            "tier": self.tier,
            "state": self.state.name if hasattr(self.state, "name") else str(self.state),
            "health": round(float(self._health), 2),
            "max_health": float(self._max_health),
            "health_ratio": round(float(self._health / self._max_health), 3) if self._max_health > 0 else 0.0,
            "is_dead": self.is_dead,
            "facing_left": self.facing_left,
            "scale": self.scale,
            "speed": self._speed,
            "position": {"x": self.rect.x, "y": self.rect.y, "centerx": self.rect.centerx, "centery": self.rect.centery},
            "ground_y": self._ground_y,
            "gravity": self._gravity,
            "perception": {
                "alert_level": self.perception.alert_level.name if hasattr(self.perception.alert_level, "name") else str(self.perception.alert_level),
                "detection_range": self._detection_range,
                "vertical_tolerance": self._vertical_tolerance,
            },
            "tactics": {
                "attack_range": self._attack_range,
                "center_dist_x": center_dist_x,
                "edge_dist_x": edge_dist_x,
                "dist_y": dist_y,
                "can_attack": (edge_dist_x <= float(self._attack_range)) if edge_dist_x is not None else False,
                "last_action": self._last_ai_action,
                "squad_role": SquadCoordinator.get_instance().get_role(id(self)).name,
            },
            "combat_stats": {
                "attack_count": self._attack_count,
                "attack_hitbox_width": self._scaled_hitbox_w,
                "attack_hitbox_height": self._scaled_hitbox_h,
            },
        }

    def get_telemetry(self) -> dict:
        """Alias for get_metadata() returning standardized telemetry payload."""
        return self.get_metadata()

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
        dt_sec = dt if dt < 1.0 else dt / 1000.0

        self.rect.x -= scroll_speed
        
        self._apply_gravity()

        # Update hit flash timer
        if self._hit_flash_timer > 0.0:
            self._hit_flash_timer = max(0.0, self._hit_flash_timer - dt_sec)

        # Check for real-time live editor save updates on disk
        self._hot_reload_timer = getattr(self, "_hot_reload_timer", 0.0) + dt_sec
        if self._hot_reload_timer >= 0.5:
            self._hot_reload_timer = 0.0
            updated_config = ConfigClient.check_for_updates("enemy_blood_zombie")
            if updated_config:
                self.apply_config(updated_config)
                print(f"[BLOOD ZOMBIE HOT-RELOAD] Live updated! Range={self._attack_range}, Speed={self._speed}, HP={self._max_health}")

        self._update_ai(dt_sec)
        
        super().update(dt)  # Handles state machines and animations
        self._update_animation_audio()

        # ── Necromancer Staff Strike Black & White Lightning Effect ────────────
        if self.state == BloodZombieState.ATTACK:
            curr_frame = int(self.animation_index)
            if curr_frame in (5, 6, 7):
                if not getattr(self, "_lightning_triggered_this_attack", False):
                    setattr(self, "_lightning_triggered_this_attack", True)
                    from src.game.effects.lightning_effect import LightningEffect
                    LightningEffect.get_instance().trigger(duration=1.0, staff_pos=self.rect.midbottom)
        else:
            setattr(self, "_lightning_triggered_this_attack", False)

        if self.state != BloodZombieState.ATTACK:
            SquadTokenManager.get_instance().release_attack_token(id(self))
        
        # Cleanup on death animation completion
        if self.state == BloodZombieState.DEATH and int(self.animation_index) >= len(self.animations[BloodZombieState.DEATH]) - 1:
            SquadTokenManager.get_instance().unregister_enemy(id(self))
            self.kill()

    def kill(self) -> None:
        SquadTokenManager.get_instance().unregister_enemy(id(self))
        super().kill()

    def take_damage(self, amount: float = 0.5, knockback: tuple[float, float] | None = None) -> None:
        if self.state in (BloodZombieState.HURT, BloodZombieState.DEATH):
            return

        SquadTokenManager.get_instance().release_attack_token(id(self))
        
        # Reduce health, but never allow health to go below 0
        self._health = max(0, self._health - amount)
        
        # Trigger procedural hit reaction flash & recoil
        self._hit_flash_timer = self._hit_flash_duration
        recoil_dir = 1 if self.facing_left else -1
        self._hit_recoil_dx = recoil_dir * self._hit_recoil_dist * self.scale

        # Apply knockback if provided
        if knockback is not None and isinstance(knockback, (tuple, list)) and len(knockback) >= 2:
            self.rect.x += int(knockback[0])
            self.rect.y += int(knockback[1])
        
        # If the zombie was attacking, cancel the attack
        self.attack_state.end()
        
        # If health is depleted, switch to death animation
        if self._health <= 0:
            SquadTokenManager.get_instance().unregister_enemy(id(self))
            self.set_state(BloodZombieState.DEATH, force=True)
        # Otherwise, switch to hurt animation
        else:
            self.set_state(BloodZombieState.HURT, force=True)

    # ─────────────────────────────────────────────────────────────────────────
    # Private: AI Logic
    # ─────────────────────────────────────────────────────────────────────────

    def _update_ai(self, dt_sec: float = 0.016) -> None:
        if self._player is None or self.state in (BloodZombieState.HURT, BloodZombieState.DEATH):
            return
            
        # 1. Perception Update
        alert = self.perception.update(dt_sec, self.rect, self.facing_left, self._player)
        if alert == AlertLevel.UNAWARE:
            self.set_state(BloodZombieState.IDLE)
            self._last_ai_action = "IDLE"
            return

        if self.state == BloodZombieState.ATTACK:
            return

        player_rect = getattr(self._player, "rect", None)
        if player_rect is None:
            return

        # 2. Distance Calculations (Center and Edge-to-Edge)
        center_dist_x = abs(self.rect.centerx - player_rect.centerx)
        if self.rect.right < player_rect.left:
            edge_dist_x = float(player_rect.left - self.rect.right)
        elif player_rect.right < self.rect.left:
            edge_dist_x = float(self.rect.left - player_rect.right)
        else:
            edge_dist_x = 0.0

        dist_y = abs(self.rect.centery - player_rect.centery)

        # Melee attack reach check:
        # Attack allowed if edge distance <= attack_range OR center distance <= attack_range + 40
        attack_reach = float(self._attack_range)
        can_attack = (edge_dist_x <= attack_reach) or (center_dist_x <= attack_reach + 40.0)

        # Token & Utility Action Evaluation
        has_token = SquadTokenManager.get_instance().request_attack_token(id(self))

        is_pincer = SquadCoordinator.get_instance().should_trigger_pincer_attack(
            id(self), center_dist_x, can_attack=can_attack
        )

        action = self.utility_engine.evaluate_action(
            enemy_rect=self.rect,
            player=self._player,
            can_attack=can_attack,
            has_attack_token=has_token,
            dt_sec=dt_sec,
        )

        self._last_ai_action = action.name if hasattr(action, "name") else str(action)
        self.behavior_metadata = self.get_metadata()

        if is_pincer or action in (TacticalAction.PUNISH_WHIFF, TacticalAction.ATTACK) or (can_attack and has_token and dist_y < 120):
            self.facing_left = (self.rect.centerx > player_rect.centerx)
            self._begin_attack()
        elif action == TacticalAction.RETRACT_SPACING:
            if can_attack and has_token:
                self.facing_left = (self.rect.centerx > player_rect.centerx)
                self._begin_attack()
            else:
                step_dir = 1 if self.rect.centerx > player_rect.centerx else -1
                self.rect.x += step_dir * int(self._speed * 0.8)
                self.facing_left = (self.rect.centerx > player_rect.centerx)
                self.set_state(BloodZombieState.CHASE)
        elif action == TacticalAction.CHASE:
            if can_attack:
                self.facing_left = (self.rect.centerx > player_rect.centerx)
                if has_token:
                    self._begin_attack()
                else:
                    self.set_state(BloodZombieState.IDLE)
            else:
                self.set_state(BloodZombieState.CHASE)
                self._chase_player(player_rect)
        else:
            self.facing_left = (self.rect.centerx > player_rect.centerx)
            self.set_state(BloodZombieState.IDLE)

    def _begin_attack(self) -> None:
        self._attack_count += 1
        if self._player and hasattr(self._player, "rect"):
            self.facing_left = (self.rect.centerx > self._player.rect.centerx)
        if random.random() < 0.5:
            # Primary attack animation
            self.animations[BloodZombieState.ATTACK] = self._attack1_frames
            self.current_attack_config = self.attack1_config
            self._current_attack_anim_key = "Attack1"
        else:
            # Secondary attack animation
            self.animations[BloodZombieState.ATTACK] = self._attack2_frames
            self.current_attack_config = self.attack2_config
            self._current_attack_anim_key = "Attack2"
        self.set_state(BloodZombieState.ATTACK)

    def _chase_player(self, player_rect: pg.Rect) -> None:
        target_x = SquadCoordinator.get_instance().get_target_offset_x(
            id(self), player_rect, getattr(self._player, "facing_left", False), float(self._attack_range)
        )
        dx = target_x - self.rect.centerx
        if abs(dx) > 5:
            move_dir = 1 if dx > 0 else -1
            self.rect.x += move_dir * int(self._speed)
            self.facing_left = (self.rect.centerx > player_rect.centerx)

    # ─────────────────────────────────────────────────────────────────────────
    # Private: Physics
    # ─────────────────────────────────────────────────────────────────────────

    def set_ground_y(self, ground_y: Optional[int]) -> None:
        """Update physics ground floor level from environment manager (None = freefall)."""
        self._ground_y = ground_y

    def _apply_gravity(self) -> None:
        """Apply gravitational acceleration and ground collision."""
        self._gravity += 1.0
        self.rect.y += int(self._gravity)
        
        # Ground collision
        if self._ground_y is not None and self.rect.bottom >= self._ground_y:
            self.rect.bottom = self._ground_y
            self._gravity = 0.0

    # ─────────────────────────────────────────────────────────────────────────
    # Rendering
    # ─────────────────────────────────────────────────────────────────────

    def draw(self, surface: pg.Surface) -> None:
        """
        Draw the blood zombie with per-frame root motion offset alignment and UI elements.
        
        Args:
            surface: Target surface for rendering.
        """
        attack_anim_key = getattr(self, "_current_attack_anim_key", "Attack1")
        anim_key_map = {
            BloodZombieState.IDLE: "Idle",
            BloodZombieState.CHASE: "Move",
            BloodZombieState.ATTACK: attack_anim_key,
            BloodZombieState.HURT: "Death",
            BloodZombieState.DEATH: "Death",
        }
        anim_key = anim_key_map[self.state] if self.state in anim_key_map else "Idle"
        frame_idx = str(int(self.animation_index))
        offset = self.frame_offsets.get(anim_key, {}).get(frame_idx, {})
        dx = int(offset.get("dx", 0) * self.scale)
        dy = int(offset.get("dy", 0) * self.scale)

        if self.facing_left:
            dx = -dx

        # Apply image_offset (set by adjust_hitbox_sides) to align sprite over hitbox,
        # matching the base Entity.draw() behavior: rect.topleft - image_offset
        base_x = self.rect.x - int(self.image_offset.x)
        base_y = self.rect.y - int(self.image_offset.y)
        draw_x = base_x + dx
        draw_y = base_y + dy

        # self.image is already correctly oriented by Actor.update_animation()
        # which handles facing_left via self._animations_flipped cache.
        render_img = self.image

        # Apply procedural squash and stretch deformation during hit flash
        if self._hit_flash_timer > 0.0 and getattr(self, "_squash_stretch_enabled", True):
            progress = self._hit_flash_timer / max(0.01, self._hit_flash_duration)
            squash_w = int(render_img.get_width() * (1.0 + 0.15 * progress))
            squash_h = int(render_img.get_height() * (1.0 - 0.15 * progress))
            if squash_w > 0 and squash_h > 0:
                render_img = pg.transform.scale(render_img, (squash_w, squash_h))
                draw_y -= (squash_h - self.image.get_height())

            # Apply recoil offset
            draw_x += int(self._hit_recoil_dx * progress)

        # Sanguine Chromatic Phase Shift (Eldritch Red Channel Split & Ghost Afterimages)
        if self.state in (BloodZombieState.CHASE, BloodZombieState.ATTACK):
            phase_shift = int(6 * self.scale)
            cur_pos = (draw_x, draw_y)

            if not hasattr(self, "_ghost_trail") or self._ghost_trail is None:
                self._ghost_trail = []

            if len(self._ghost_trail) == 0 or math.hypot(cur_pos[0] - self._ghost_trail[-1][1][0], cur_pos[1] - self._ghost_trail[-1][1][1]) > 8:
                self._ghost_trail.append((render_img.copy(), cur_pos))
                if len(self._ghost_trail) > 5:
                    self._ghost_trail.pop(0)

            # Draw decaying afterimage ghosts (using render_img)
            for idx, (g_surf, (gx, gy)) in enumerate(self._ghost_trail[:-1]):
                alpha = int(140 * (idx + 1) / float(len(self._ghost_trail)))
                g_copy = g_surf.copy()
                g_tint = pg.Surface(g_surf.get_size(), pg.SRCALPHA)
                g_tint.fill((200, 20, 40, alpha))
                g_copy.blit(g_tint, (0, 0), special_flags=pg.BLEND_RGBA_MULT)
                surface.blit(g_copy, (gx, gy))

            # Chromatic RGB Red Channel offset blit (using render_img)
            p_dx = -phase_shift if self.facing_left else phase_shift
            red_surf = render_img.copy()
            red_tint = pg.Surface(render_img.get_size(), pg.SRCALPHA)
            red_tint.fill((255, 30, 30, 180))
            red_surf.blit(red_tint, (0, 0), special_flags=pg.BLEND_RGBA_MULT)
            surface.blit(red_surf, (draw_x + p_dx, draw_y - 2), special_flags=pg.BLEND_ADD)

        # Draw main sprite surface
        surface.blit(render_img, (draw_x, draw_y))

        # Blit pure white silhouette flash mask over render_img during hit flash
        if self._hit_flash_timer > 0.0:
            flash_mask = pg.Surface(render_img.get_size(), pg.SRCALPHA)
            flash_mask.fill((255, 255, 255, 220))
            flash_mask.blit(render_img, (0, 0), special_flags=pg.BLEND_RGBA_MULT)
            surface.blit(flash_mask, (draw_x, draw_y))
        
        # Draw translucent pulsing force field orb shield at collision center coordinates
        self._draw_force_field_shield(surface)

        # Draw health bar when damaged and alive
        if self._health < self._max_health and self.state != BloodZombieState.DEATH:
            self._draw_health_bar(surface)

    def _draw_force_field_shield(self, surface: pg.Surface) -> None:
        """
        Render an ethereal semi-transparent pulsing orb force field shield
        protecting the BloodZombie at the collision center coordinates.
        """
        if not getattr(self, "_shield_enabled", True) or self.state == BloodZombieState.DEATH:
            return

        ticks = pg.time.get_ticks()
        pulse = math.sin(ticks * 0.005) * 4.0
        radius = int((self._shield_radius_base * self.scale) + pulse)

        # Center coordinates based on collision hitbox center
        cx = self.rect.centerx
        cy = self.rect.centery

        # Create transparent surface for smooth alpha blending
        diameter = radius * 2 + 20
        shield_surf = pg.Surface((diameter, diameter), pg.SRCALPHA)
        center = (diameter // 2, diameter // 2)

        # Base energy tint (flares white/gold on hit, otherwise crimson/blood energy)
        if self._hit_flash_timer > 0.0:
            core_color = (255, 230, 180, 130)
            rim_color = (255, 255, 255, 240)
            glow_color = (255, 180, 50, 180)
        else:
            r, g, b = getattr(self, "_shield_color", (230, 40, 70))
            core_color = (r, g, b, 45)
            rim_color = (min(255, r + 40), min(255, g + 80), min(255, b + 80), 200)
            glow_color = (r, min(255, g + 20), min(255, b + 20), 90)

        # 1. Outer ambient glow aura
        pg.draw.circle(shield_surf, glow_color, center, radius + 4, width=3)

        # 2. Inner translucent energy dome fill
        pg.draw.circle(shield_surf, core_color, center, radius)

        # 3. Bright reinforced rim arc
        pg.draw.circle(shield_surf, rim_color, center, radius, width=2)

        # 4. Energy ripple rings (hexagonal/arc energy pattern)
        ripple_r = int((radius * 0.6) + ((ticks % 1000) / 1000.0) * (radius * 0.35))
        pg.draw.circle(shield_surf, (255, 255, 255, 90), center, ripple_r, width=1)

        # 5. Directional front shield arc (half-shield facing the player)
        front_arc_angle = 0.0 if not self.facing_left else math.pi
        arc_rect = pg.Rect(center[0] - radius, center[1] - radius, radius * 2, radius * 2)
        start_angle = front_arc_angle - math.pi / 2.2
        end_angle = front_arc_angle + math.pi / 2.2
        pg.draw.arc(shield_surf, (255, 255, 255, 240), arc_rect, start_angle, end_angle, width=3)

        # Blit shield surface onto game screen centered at (cx, cy)
        surface.blit(shield_surf, (cx - diameter // 2, cy - diameter // 2))

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