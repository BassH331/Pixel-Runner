"""
DarkRonin enemy module — High-speed elite warrior enemy with dash-slash combat AI.

Features a state-machine AI with high mobility, rapid forward dash strikes,
and heavy melee blade attacks using the Ronin sprite assets.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Final, Optional

import pygame as pg

from v3x_zulfiqar_gideon import AssetManager, Actor, AttackConfig
from src.game.audio.entity_audio_mixin import EntityAudioMixin
from .hitbox_registry import HitboxRegistry

if TYPE_CHECKING:
    from src.game.entities.player import Player


class DarkRoninState(Enum):
    """Enumeration of all possible Dark Ronin behavioral states."""
    
    DEATH = 0
    HURT = 10
    ATTACK = 20
    DASH_STRIKE = 25
    CHASE = 30
    IDLE = 40


@dataclass(slots=True)
class StateConfig:
    animation_speed: float = 0.15
    loops: bool = True
    next_state: Optional[DarkRoninState] = None
    interruptible: bool = True


class DarkRonin(EntityAudioMixin, Actor):
    """
    High-mobility elite Dark Ronin minion with high-speed dash strikes.
    """

    SLASH_CONFIG: Final[AttackConfig] = AttackConfig(
        hit_frames=frozenset({12, 13, 14, 15}),
        base_damage=2.0,
        knockback_force=12.0,
    )

    DASH_STRIKE_CONFIG: Final[AttackConfig] = AttackConfig(
        hit_frames=frozenset({4, 5, 6, 7}),
        base_damage=2.8,
        knockback_force=18.0,
    )

    STATE_CONFIGS: Final[dict[Enum, StateConfig]] = {
        DarkRoninState.IDLE: StateConfig(0.12),
        DarkRoninState.CHASE: StateConfig(0.20),
        DarkRoninState.ATTACK: StateConfig(0.25, loops=False, next_state=DarkRoninState.IDLE, interruptible=False),
        DarkRoninState.DASH_STRIKE: StateConfig(0.22, loops=False, next_state=DarkRoninState.IDLE, interruptible=False),
        DarkRoninState.HURT: StateConfig(0.25, loops=False, next_state=DarkRoninState.IDLE, interruptible=False),
        DarkRoninState.DEATH: StateConfig(0.15, loops=False, interruptible=False),
    }

    def __init__(
        self,
        x: int,
        y: int,
        player: Player,
        audio_manager=None,
        move_speed: float = 4.0,
    ) -> None:
        super().__init__(x, y)

        self._player: Player = player
        self.state_configs = self.STATE_CONFIGS
        self.move_speed: float = move_speed

        self._health: float = 35.0
        self._max_health: float = 35.0
        self._direction: int = -1  # -1 = facing left, 1 = facing right
        self._state: Enum = DarkRoninState.IDLE
        self.animation_index: float = 0.0

        # Dash strike cooldown & range parameters
        self.dash_cooldown_ms: int = 4000
        self.last_dash_time: int = -self.dash_cooldown_ms

        # Load hitbox margins
        self.margins = HitboxRegistry.get_margins("dark_ronin")

        # Load animations from assets/graphics/Ronin
        self.animations: dict[Enum, list[pg.Surface]] = {}
        self._load_animations()

        # Set default image & rect
        self.image = self.animations[DarkRoninState.IDLE][0]
        self.rect = self.image.get_rect(midbottom=(x, y))
        surf = pg.display.get_surface()
        screen_h = surf.get_height() if surf else 720
        self.y_ground: int = screen_h - self.margins.ground_offset
        self.rect.bottom = self.y_ground

        self._hit_targets: set[int] = set()
        self._is_invincible: bool = False
        self._audio_manager = audio_manager
        # Audio setup
        self._init_entity_audio_config(audio_manager, "skeleton")

    @property
    def is_invincible(self) -> bool:
        return self._is_invincible

    @property
    def health(self) -> float:
        return self._health

    @property
    def max_health(self) -> float:
        return self._max_health

    @property
    def direction(self) -> int:
        return self._direction

    def _load_animations(self) -> None:
        """Load animation frames from assets/graphics/Ronin."""
        base_dir = os.path.join("assets", "graphics", "Ronin")
        file_mapping = {
            DarkRoninState.IDLE: "spr_RoninIdle_strip8.png",
            DarkRoninState.CHASE: "spr_RoninRun_strip10.png",
            DarkRoninState.ATTACK: "spr_RoninAttack_strip33.png",
            DarkRoninState.DASH_STRIKE: "spr_RoninDash_strip10.png",
            DarkRoninState.HURT: "spr_RoninGetHit_strip7.png",
            DarkRoninState.DEATH: "spr_RoninDeath_strip16.png",
        }

        scale = self.margins.scale
        for state, file_name in file_mapping.items():
            file_path = os.path.join(base_dir, file_name)
            raw_frames = AssetManager.get_animation_frames(file_path)
            scaled_frames = []
            for frame in raw_frames:
                w = int(frame.get_width() * scale)
                h = int(frame.get_height() * scale)
                scaled_frames.append(pg.transform.smoothscale(frame, (w, h)))
            self.animations[state] = scaled_frames if scaled_frames else [pg.Surface((32, 32))]

    def set_ground_y(self, ground_y: Optional[int]) -> None:
        """Set ground level height."""
        if ground_y is not None:
            self.y_ground = ground_y
            self.rect.bottom = ground_y

    def set_state(self, new_state: Enum, force: bool = False) -> None:
        """Transition to a new behavioral state."""
        if self._state == DarkRoninState.DEATH and not force:
            return

        current_config = self.STATE_CONFIGS.get(self._state, StateConfig())
        if not current_config.interruptible and not force and self._state != new_state:
            return

        if self._state != new_state:
            self._state = new_state
            self.animation_index = 0.0
            self._hit_targets.clear()

    def update(self, dt: float = 16.67, bg_scroll_speed: float = 0.0) -> None:
        """Update DarkRonin AI, movement, and animation frames."""
        current_time = pg.time.get_ticks()

        # Adjust position for background scrolling
        self.rect.x -= int(bg_scroll_speed)

        # Handle Death State
        if self._state == DarkRoninState.DEATH:
            self._update_animation()
            return

        # AI Behavior
        player_sprite = getattr(self._player, "sprite", self._player)
        if player_sprite and hasattr(player_sprite, "rect"):
            dist_x = player_sprite.rect.centerx - self.rect.centerx
            abs_dist = abs(dist_x)

            # Face player direction
            if abs_dist > 10 and self._state in (DarkRoninState.IDLE, DarkRoninState.CHASE):
                self._direction = 1 if dist_x > 0 else -1

            # Check Dash Strike trigger (120px - 280px range, off cooldown)
            if (
                120 <= abs_dist <= 280
                and current_time - self.last_dash_time >= self.dash_cooldown_ms
                and self._state in (DarkRoninState.IDLE, DarkRoninState.CHASE)
            ):
                self.last_dash_time = current_time
                self.set_state(DarkRoninState.DASH_STRIKE)

            # Normal attack (in melee range < 65px)
            elif abs_dist <= 65 and self._state in (DarkRoninState.IDLE, DarkRoninState.CHASE):
                self.set_state(DarkRoninState.ATTACK)

            # Chase player
            elif abs_dist > 65 and self._state in (DarkRoninState.IDLE, DarkRoninState.CHASE):
                self.set_state(DarkRoninState.CHASE)
                self.rect.x += int(self._direction * self.move_speed)

        # Handle Dash Movement
        if self._state == DarkRoninState.DASH_STRIKE:
            dash_velocity = 8.0
            self.rect.x += int(self._direction * dash_velocity)

        self._update_animation()

    def _update_animation(self) -> None:
        """Advance animation frame and update sprite image."""
        frames = self.animations.get(self._state, self.animations[DarkRoninState.IDLE])
        config = self.STATE_CONFIGS.get(self._state, StateConfig())

        self.animation_index += config.animation_speed
        if self.animation_index >= len(frames):
            if config.loops:
                self.animation_index = 0.0
            else:
                self.animation_index = float(len(frames) - 1)
                if config.next_state:
                    self.set_state(config.next_state, force=True)

        idx = int(self.animation_index) % len(frames)
        raw_image = frames[idx]

        # Flip horizontally if facing right
        if self._direction == 1:
            self.image = pg.transform.flip(raw_image, True, False)
        else:
            self.image = raw_image

    def take_damage(self, amount: float) -> bool:
        """Apply damage unless dead."""
        if self._is_invincible or self._state == DarkRoninState.DEATH:
            return False

        self._health = max(0.0, self._health - amount)
        if self._health <= 0.0:
            self.set_state(DarkRoninState.DEATH, force=True)
            if self._audio_manager:
                try:
                    self._audio_manager.play_sound("skeleton_death")
                except Exception:
                    pass
        else:
            self.set_state(DarkRoninState.HURT, force=True)
            if self._audio_manager:
                try:
                    self._audio_manager.play_sound("skeleton_hurt")
                except Exception:
                    pass
        return True

    def get_attack_hitbox(self) -> Optional[pg.Rect]:
        """Get current attack hitbox if on an active hit frame."""
        config = None
        if self._state == DarkRoninState.ATTACK:
            config = self.SLASH_CONFIG
        elif self._state == DarkRoninState.DASH_STRIKE:
            config = self.DASH_STRIKE_CONFIG

        if not config:
            return None

        idx = int(self.animation_index)
        if idx in config.hit_frames:
            hitbox_w = 90
            hitbox_h = 70
            if self._direction == -1:
                hx = self.rect.left - hitbox_w + 20
            else:
                hx = self.rect.right - 20
            hy = self.rect.top + 10
            return pg.Rect(hx, hy, hitbox_w, hitbox_h)
        return None

    def should_deal_damage(self) -> bool:
        """Return True if on an active attack hit frame."""
        return self.get_attack_hitbox() is not None

    def register_hit(self, target_id: int) -> bool:
        """Register hit target ID to prevent multi-hitting in a single swing cycle."""
        if target_id in self._hit_targets:
            return False
        self._hit_targets.add(target_id)
        return True

    def get_current_attack_damage(self) -> float:
        """Return current attack damage."""
        if self._state == DarkRoninState.DASH_STRIKE:
            return self.DASH_STRIKE_CONFIG.base_damage
        return self.SLASH_CONFIG.base_damage

    def get_current_attack_knockback(self) -> float:
        """Return current attack knockback."""
        if self._state == DarkRoninState.DASH_STRIKE:
            return self.DASH_STRIKE_CONFIG.knockback_force
        return self.SLASH_CONFIG.knockback_force

    def draw(self, surface: pg.Surface) -> None:
        """Render DarkRonin onto target surface."""
        surface.blit(self.image, self.rect)
        if self._health < self._max_health and self._state != DarkRoninState.DEATH:
            self._draw_health_bar(surface)

    def _draw_health_bar(self, surface: pg.Surface) -> None:
        """Render the health bar above DarkRonin."""
        bar_width: int = 50
        bar_height: int = 6
        bar_x: int = self.rect.centerx - bar_width // 2
        bar_y: int = self.rect.top - 12
        pg.draw.rect(surface, (40, 40, 40), (bar_x, bar_y, bar_width, bar_height))
        ratio = self._health / self._max_health
        pg.draw.rect(surface, (220, 20, 20), (bar_x, bar_y, int(bar_width * ratio), bar_height))
