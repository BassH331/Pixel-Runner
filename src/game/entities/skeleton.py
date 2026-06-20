"""
Skeleton enemy module with precision frame-based combat system.

This module implements a skeletal enemy with state-machine AI and
frame-accurate hit detection for responsive, fair combat gameplay.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import TYPE_CHECKING, Final, Optional, Sequence

import pygame as pg

from v3x_zulfiqar_gideon import AssetManager, Actor, AttackConfig
from .hitbox_registry import HitboxRegistry

if TYPE_CHECKING:
    from src.game.entities.player import Player


class SkeletonState(Enum):
    """Enumeration of all possible skeleton behavioral states."""
    
    DEATH = 0
    HURT = 10
    ATTACK = 20
    CHASE = 30
    IDLE = 40


@dataclass(slots=True)
class StateConfig:
    animation_speed: float = 0.15
    loops: bool = True
    next_state: Optional[SkeletonState] = None
    interruptible: bool = True


class Skeleton(Actor):
    """
    A skeletal enemy with state-machine AI and frame-precise combat.
    """
    
    # Class-level attack configurations (immutable)
    ATTACK_1_CONFIG: Final[AttackConfig] = AttackConfig(
        hit_frames=frozenset({6}),
        base_damage=1.0,
        knockback_force=8.0,
    )
    
    ATTACK_2_CONFIG: Final[AttackConfig] = AttackConfig(
        hit_frames=frozenset({5, 6}),
        base_damage=0.75,
        knockback_force=5.0,
    )
    
    STATE_CONFIGS: Final[dict[Enum, StateConfig]] = {
        SkeletonState.IDLE: StateConfig(0.1),
        SkeletonState.CHASE: StateConfig(0.15),
        SkeletonState.ATTACK: StateConfig(0.15, loops=False, next_state=SkeletonState.IDLE, interruptible=False),
        SkeletonState.HURT: StateConfig(0.15, loops=False, next_state=SkeletonState.IDLE, interruptible=False),
        SkeletonState.DEATH: StateConfig(0.15, loops=False, interruptible=False),
    }

    def __init__(
        self,
        x: int,
        y: int,
        player: Player,
        sprite_root: Optional[str] = None,
        behaviour_map: Optional[dict[str, str]] = None,
        tier: str = "minion",
        custom_scale: Optional[float] = None,
        custom_health: Optional[float] = None,
    ) -> None:
        super().__init__(x, y)
        
        self._player: Player = player
        self.state_configs = self.STATE_CONFIGS
        self.tier = tier
        
        # Load margins and scale first
        if self.tier == "boss":
            margins_key = "boss"
            if sprite_root:
                import os
                folder_name = os.path.basename(sprite_root.rstrip("/"))
                margins_key = f"boss:{folder_name.lower()}"
        else:
            margins_key = "skeleton"
            if sprite_root:
                import os
                folder_name = os.path.basename(sprite_root.rstrip("/"))
                margins_key = f"skeleton_{folder_name.lower()}"
        
        margins = HitboxRegistry.get_margins(margins_key)
        # If margins for custom skeleton/boss are missing, fall back to default
        if margins.scale == 1.0 and margins.ground_offset == 0:
            if self.tier == "boss":
                margins = HitboxRegistry.get_margins("boss")
            else:
                margins = HitboxRegistry.get_margins("skeleton")
            
        # Determine scale: registry priority -> custom_scale priority -> default margins scale
        registry_scale = None
        try:
            if HitboxRegistry.has_custom_margins(margins_key):
                registry_scale = margins.scale
        except Exception:
            pass

        self.scale = registry_scale if registry_scale is not None else (custom_scale if custom_scale is not None else margins.scale)
        self._scale_is_explicit = (registry_scale is not None or custom_scale is not None)
        
        # 1. Load default animations
        self.animations[SkeletonState.IDLE] = self._load_frames(
            "assets/skeleton/Skeleton_01_White_Idle/skeleton-idle_{}.png", 8
        )
        self.animations[SkeletonState.CHASE] = self._load_frames(
            "assets/skeleton/Skeleton_01_White_Walk/skeleton-walk_{:02d}.png", 10
        )
        self._attack1_frames = self._load_frames(
            "assets/skeleton/Skeleton_01_White_Attack1/skeleton-atk2_{:02d}.png", 10
        )
        self.animations[SkeletonState.ATTACK] = self._attack1_frames
        # Handle secondary attack animation implicitly or add it to state machine
        self._attack2_frames = self._load_frames(
            "assets/skeleton/Skeleton_01_White_Attack2/skeleton-atk1_{}.png", 9
        )
        self.animations[SkeletonState.HURT] = self._load_frames(
            "assets/skeleton/Skeleton_01_White_Hurt/skeleton-hurt_{}.png", 5
        )
        self.animations[SkeletonState.DEATH] = self._load_frames(
            "assets/skeleton/Skeleton_01_White_Die/skeleton-death_{:02d}.png", 13
        )
        
        # 2. Overwrite with dynamic sprites if provided
        if sprite_root and behaviour_map:
            import os
            tag_to_folders = {}
            for sub, tag in behaviour_map.items():
                tag_to_folders.setdefault(tag, []).append(os.path.join(sprite_root, sub))
                
            def load_from_folders(folders: list[str]) -> list[pg.Surface]:
                frames = []
                for f in folders:
                    raw = AssetManager.get_animation_frames(f)
                    for frame in raw:
                        w = int(frame.get_width() * self.scale)
                        h = int(frame.get_height() * self.scale)
                        frames.append(pg.transform.scale(frame, (w, h)))
                return frames
                
            if "idle" in tag_to_folders:
                self.animations[SkeletonState.IDLE] = load_from_folders(tag_to_folders["idle"])
            if "walk" in tag_to_folders or "chase" in tag_to_folders:
                walk_folders = tag_to_folders.get("walk", []) + tag_to_folders.get("chase", [])
                self.animations[SkeletonState.CHASE] = load_from_folders(walk_folders)
            if "attack" in tag_to_folders:
                attack_folders = tag_to_folders["attack"]
                if len(attack_folders) >= 2:
                    self._attack1_frames = load_from_folders([attack_folders[0]])
                    self._attack2_frames = load_from_folders([attack_folders[1]])
                    self.animations[SkeletonState.ATTACK] = self._attack1_frames
                else:
                    self._attack1_frames = load_from_folders(attack_folders)
                    self._attack2_frames = self._attack1_frames
                    self.animations[SkeletonState.ATTACK] = self._attack1_frames
            if "hurt" in tag_to_folders:
                self.animations[SkeletonState.HURT] = load_from_folders(tag_to_folders["hurt"])
            if "death" in tag_to_folders:
                self.animations[SkeletonState.DEATH] = load_from_folders(tag_to_folders["death"])
                
        # 3. Apply Tier Scaling (Health, Speed, Size)
        damage_scale = 1.0
        knockback_scale = 1.0
        
        if self.tier == "boss":
            if not sprite_root and not self._scale_is_explicit:
                self.scale *= 1.8
                # Scale all pre-loaded animation frames to boss scale
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
            self._max_health = custom_health if custom_health is not None else 150.0
            self._speed = 3.2
            damage_scale = 3.0
            knockback_scale = 1.8
        elif self.tier == "elite":
            if not sprite_root and not self._scale_is_explicit:
                self.scale *= 1.3
                # Scale all pre-loaded animation frames to elite scale
                for state in list(self.animations.keys()):
                    self.animations[state] = [
                        pg.transform.scale(img, (int(img.get_width() * 1.3), int(img.get_height() * 1.3)))
                        for img in self.animations[state]
                    ]
                self._attack1_frames = [
                    pg.transform.scale(img, (int(img.get_width() * 1.3), int(img.get_height() * 1.3)))
                    for img in self._attack1_frames
                ]
                self._attack2_frames = [
                    pg.transform.scale(img, (int(img.get_width() * 1.3), int(img.get_height() * 1.3)))
                    for img in self._attack2_frames
                ]
            self._max_health = custom_health if custom_health is not None else 60.0
            self._speed = 3.2
            damage_scale = 1.6
            knockback_scale = 1.3
        else:  # minion
            self._max_health = custom_health if custom_health is not None else 30.0
            self._speed = 2.5
            damage_scale = 1.0
            knockback_scale = 1.0
            
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
        self.set_state(SkeletonState.IDLE)
        if self.state in self.animations:
            self.image = self.animations[self.state][0]
        self.rect: pg.Rect = self.image.get_rect(midbottom=(x, y))
        
        # Hitbox adjustment - loaded dynamically via the central HitboxRegistry
        self.adjust_hitbox_sides(left=margins.left, right=margins.right, top=margins.top, bottom=margins.bottom)
        
        # Movement and physics
        self._gravity: float = 0.0
        # Load dynamic ground offset from HitboxRegistry using the active display surface height
        surf = pg.display.get_surface()
        height = surf.get_height() if surf else 720
        self._ground_y: int = height - margins.ground_offset
        
        # AI configuration
        self._detection_range: int = 3000 if self.tier == "boss" else 1000
        self._attack_range: int = 60
        self._vertical_tolerance: int = 500 if self.tier == "boss" else 100
        self.spawn_zone: Optional[dict] = None
        
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
            scale_factor: Multiplier for sprite dimensions.
            
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
                # Log but continue - partial animation sets may be acceptable
                print(f"Warning: Failed to load frame {i} from '{path}': {e}")
                
        if not frames:
            raise RuntimeError(
                f"Failed to load any frames from pattern: {path_pattern}"
            )
            
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
    def is_dead(self) -> bool: return self.state == SkeletonState.DEATH
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
        """Return the attack hitbox based on skeleton facing and position."""
        if not self.should_deal_damage():
            return None
        # Simple forward hitbox in front of the skeleton
        hitbox_w, hitbox_h = 60, 80
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
        
        super().update(dt) # Handles state machines and animations
        
        # Cleanup on death animation completion
        if self.state == SkeletonState.DEATH and int(self.animation_index) >= len(self.animations[SkeletonState.DEATH]) - 1:
            self.kill()

    def take_damage(self, amount: float = 0.5) -> None:
        if self.state in (SkeletonState.HURT, SkeletonState.DEATH):
            return
            
        self._health = max(0, self._health - amount)
        self.attack_state.end()
        
        if self._health <= 0:
            self.set_state(SkeletonState.DEATH, force=True)
        else:
            self.set_state(SkeletonState.HURT, force=True)
    
    # ─────────────────────────────────────────────────────────────────────────
    # Private: AI Logic
    # ─────────────────────────────────────────────────────────────────────────
    
    def _update_ai(self) -> None:
        if self._player is None or self.state in (SkeletonState.HURT, SkeletonState.DEATH):
            return
            
        player_rect = self._player.rect
        dist_x = abs(self.rect.centerx - player_rect.centerx)
        dist_y = abs(self.rect.centery - player_rect.centery)
        
        if self.state == SkeletonState.ATTACK:
            return
            
        if dist_x < self._attack_range and dist_y < self._vertical_tolerance:
            self._begin_attack()
        elif dist_x < self._detection_range and dist_y < self._vertical_tolerance:
            self.set_state(SkeletonState.CHASE)
        else:
            self.set_state(SkeletonState.IDLE)
            
        if self.state == SkeletonState.CHASE:
            self._chase_player(player_rect)
    
    def _begin_attack(self) -> None:
        if random.random() < 0.5:
            # Primary attack animation
            self.animations[SkeletonState.ATTACK] = self._attack1_frames
            self.current_attack_config = self.attack1_config
        else:
            # Secondary attack animation
            self.animations[SkeletonState.ATTACK] = self._attack2_frames
            self.current_attack_config = self.attack2_config
        self.set_state(SkeletonState.ATTACK)
    
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
    def _apply_frame(self) -> None:
        pass # Handle by Actor superclass
    
    # ─────────────────────────────────────────────────────────────────────────
    # Rendering
    # ─────────────────────────────────────────────────────────────────────────

    def draw(self, surface: pg.Surface) -> None:
        """
        Draw the skeleton and UI elements.
        
        Args:
            surface: Target surface for rendering.
        """
        super().draw(surface)
        
        # Draw health bar when damaged and alive
        if self._health < self._max_health and self.state != SkeletonState.DEATH:
            self._draw_health_bar(surface)
    
    def _draw_health_bar(self, surface: pg.Surface) -> None:
        """Render the health bar above the skeleton."""
        bar_width: int = 40
        bar_height: int = 5
        bar_x: int = self.rect.centerx - bar_width // 2
        bar_y: int = self.rect.top - 10
        
        # Background (empty health)
        pg.draw.rect(
            surface,
            (50, 50, 50),
            (bar_x, bar_y, bar_width, bar_height),
        )
        
        # Current health (red fill)
        health_ratio = self._health / self._max_health
        pg.draw.rect(
            surface,
            (255, 0, 0),
            (bar_x, bar_y, int(bar_width * health_ratio), bar_height),
        )