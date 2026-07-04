"""
Green Monster ("The Gatekeeper") boss module.

A winged elite that hovers a short distance off the ground, alternating
between diving melee ground-slams when the player closes in and lobbed
toxic globs when kept at range.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Final, Optional

import pygame as pg

from v3x_zulfiqar_gideon import AssetManager, Actor, AttackConfig
from .hitbox_registry import HitboxRegistry
from ..services import ConfigClient

if TYPE_CHECKING:
    from src.game.entities.player import Player


class ToxicGlob(pg.sprite.Sprite):
    """A lobbed toxic projectile spat by the Gatekeeper. Arcs under gravity
    rather than flying flat, distinguishing it from the Fire Wizard's fireball."""

    def __init__(
        self,
        x: int,
        y: int,
        direction: int,
        scale: float,
        damage: float,
        knockback: float,
        player: Player,
    ) -> None:
        super().__init__()
        self._player = player
        self.direction = direction
        self.speed = 5.0
        self._vy = -6.0
        self._gravity = 0.35
        self.damage = damage
        self.knockback = knockback

        size = max(14, int(20 * scale))
        self.image = pg.Surface((size, size), pg.SRCALPHA)
        center = size // 2
        # Toxic glow: outer haze -> mid glob -> pale core
        pg.draw.circle(self.image, (60, 140, 20, 140), (center, center), center)
        pg.draw.circle(self.image, (110, 200, 40, 210), (center, center), int(center * 0.7))
        pg.draw.circle(self.image, (190, 255, 120, 255), (center, center), int(center * 0.35))

        self.rect = self.image.get_rect(center=(x, y))

        self.is_projectile = True
        self.is_boss = False

    def update(self, dt: Optional[float] = None, scroll_speed: int = 0) -> None:
        self.rect.x -= scroll_speed
        self.rect.x += int(self.direction * self.speed)

        self._vy += self._gravity
        self.rect.y += int(self._vy)

        # Destroy once it arcs off-screen or well past the ground
        if self.rect.top > 1400 or self.rect.right < -200 or self.rect.left > 2200:
            self.kill()
            return

        if self.rect.colliderect(self._player.rect):
            if not self._player.is_invincible:
                damage_applied = self._player.take_damage(self.damage)
                if damage_applied and self.knockback > 0:
                    apply_kb = getattr(self._player, "apply_knockback", None)
                    if apply_kb:
                        kb_dir = -1 if self.rect.centerx > self._player.rect.centerx else 1
                        apply_kb(self.knockback * kb_dir)
            self.kill()

    def draw(self, surface: pg.Surface) -> None:
        surface.blit(self.image, self.rect)


class GatekeeperState(Enum):
    """Enumeration of all possible Gatekeeper behavioral states."""

    DEATH = 0
    HURT = 10
    ATTACK = 20
    CHASE = 30
    IDLE = 40


@dataclass(slots=True)
class StateConfig:
    animation_speed: float = 0.12
    loops: bool = True
    next_state: Optional[GatekeeperState] = None
    interruptible: bool = True


class GreenMonster(Actor):
    """
    The Gatekeeper -- a hovering elite enemy. Keeps just out of easy reach,
    diving down for a ground-slam when the player gets close and lobbing
    toxic globs when kept at a distance.
    """

    # Ground-slam impact window: frames 2-4 of the 7-frame "1atk" clip.
    ATTACK_CONFIG: Final[AttackConfig] = AttackConfig(
        hit_frames=frozenset({2, 3, 4}),
        base_damage=3.0,
        knockback_force=9.0,
        max_hits_per_target=1,
    )

    STATE_CONFIGS: Final[dict[Enum, StateConfig]] = {
        GatekeeperState.IDLE: StateConfig(0.1),
        GatekeeperState.CHASE: StateConfig(0.15),
        GatekeeperState.ATTACK: StateConfig(0.15, loops=False, next_state=GatekeeperState.IDLE, interruptible=False),
        GatekeeperState.HURT: StateConfig(0.15, loops=False, next_state=GatekeeperState.IDLE, interruptible=False),
        GatekeeperState.DEATH: StateConfig(0.12, loops=False, interruptible=False),
    }

    # Frame (within the 9-frame "2atk" clip) at which the toxic glob is released.
    _SPIT_RELEASE_FRAME: Final[int] = 5

    def __init__(
        self,
        x: int,
        y: int,
        player: Player,
        tier: str = "elite",
        sprite_root: Optional[str] = None,
        behaviour_map: Optional[dict[str, str]] = None,
        custom_scale: Optional[float] = None,
        custom_health: Optional[float] = None,
    ) -> None:
        super().__init__(x, y)

        self._player: Player = player
        self.state_configs = self.STATE_CONFIGS
        self.tier = tier
        self._base_path: str = (sprite_root or "assets/graphics/green_monster").rstrip("/")

        # AI tuning -- overridden below by enemy_green_monster config if available
        self._speed: float = 2.2
        self._melee_range: int = 110
        self._ranged_range: int = 420
        self._detection_range: int = 900
        self._vertical_tolerance: int = 260
        self._attack_cooldown_min: float = 1.0
        self._attack_cooldown_max: float = 1.8
        self._chase_cooldown_duration: float = 1.0
        self._hover_height: int = 110
        self._attack_hitbox_width: int = 90
        self._attack_hitbox_height: int = 70

        self._chase_cooldown: float = 0.0
        self._attack_cooldown: float = 0.0
        self._attack_kind: str = "slam"  # "slam" (melee) or "spit" (ranged)
        self._has_spawned_attack_effect: bool = False
        self._hover_timer: float = random.uniform(0.0, math.tau)

        # Load margins/scale via the shared "boss:<folder>" registry convention
        # (see HitboxRegistry.sync_with_level_config, which auto-registers this
        # key from level_1.json's "scale" field).
        key = f"boss:{self._base_path.rsplit('/', 1)[-1].lower()}"
        margins = HitboxRegistry.get_margins(key)
        registry_scale = None
        try:
            if HitboxRegistry.has_custom_margins(key):
                registry_scale = margins.scale
        except Exception:
            pass

        self.scale = registry_scale if registry_scale is not None else (
            custom_scale if custom_scale is not None else margins.scale
        )

        # 1. Load animations
        self.animations[GatekeeperState.IDLE] = self._load_scaled(f"{self._base_path}/idle")
        self.animations[GatekeeperState.CHASE] = self._load_scaled(f"{self._base_path}/fly")
        self._attack_slam_frames = self._load_scaled(f"{self._base_path}/1atk")
        self._attack_spit_frames = self._load_scaled(f"{self._base_path}/2atk")
        self.animations[GatekeeperState.ATTACK] = self._attack_slam_frames
        self.animations[GatekeeperState.HURT] = self._load_scaled(f"{self._base_path}/hurt")
        self.animations[GatekeeperState.DEATH] = self._load_scaled(f"{self._base_path}/death")

        # 2. Tier-based stat scaling (mirrors Skeleton/FireWizard conventions)
        damage_scale = 1.0
        knockback_scale = 1.0
        if self.tier == "boss":
            self._max_health = custom_health if custom_health is not None else 100.0
            damage_scale, knockback_scale = 2.2, 1.6
        elif self.tier == "elite":
            self._max_health = custom_health if custom_health is not None else 60.0
            damage_scale, knockback_scale = 1.4, 1.2
        else:
            self._max_health = custom_health if custom_health is not None else 35.0

        try:
            config = ConfigClient.fetch_config("enemy_green_monster")
            if config:
                self._max_health = float(config.get("max_health", self._max_health))
                self._speed = float(config.get("speed", self._speed))
                damage_scale = float(config.get("damage_scale", damage_scale))
                knockback_scale = float(config.get("knockback_scale", knockback_scale))
                self._detection_range = int(config.get("detection_range", self._detection_range))
                self._melee_range = int(config.get("attack_range", self._melee_range))
                self._attack_hitbox_width = int(config.get("attack_hitbox_width", self._attack_hitbox_width))
                self._attack_hitbox_height = int(config.get("attack_hitbox_height", self._attack_hitbox_height))
                # Note: vertical_tolerance/ranged_range are deliberately NOT sourced
                # from this shared config -- its schema assumes a ground-walking
                # melee enemy, and the Gatekeeper's hover offset needs a wider
                # vertical allowance than a walker would.
        except Exception as e:
            print(f"[WARNING] Error loading green_monster config: {e}")

        self._health: float = self._max_health

        self.current_attack_config = AttackConfig(
            hit_frames=self.ATTACK_CONFIG.hit_frames,
            base_damage=self.ATTACK_CONFIG.base_damage * damage_scale,
            knockback_force=self.ATTACK_CONFIG.knockback_force * knockback_scale,
        )

        # Initial state/frame
        self.set_state(GatekeeperState.IDLE)
        if self.state in self.animations:
            self.image = self.animations[self.state][0]
        self.rect: pg.Rect = self.image.get_rect(midbottom=(x, y))

        # Hitbox adjustment from margins registry
        self.adjust_hitbox_sides(left=margins.left, right=margins.right, top=margins.top, bottom=margins.bottom)

        # Hover positioning -- no gravity; the Gatekeeper floats at a fixed
        # height above the ground and only dips down during a slam attack
        # or its death animation.
        surf = pg.display.get_surface()
        height = surf.get_height() if surf else 720
        self._ground_y: int = height - margins.ground_offset
        self._hover_y: float = float(self._ground_y - self._hover_height)
        self.rect.bottom = int(self._hover_y)

        self.spawn_zone: Optional[dict] = None

        # Precalculate scaled hitbox dimensions for the melee slam reach
        self._scaled_hitbox_w: int = int(self._attack_hitbox_width * self.scale)
        self._scaled_hitbox_h: int = int(self._attack_hitbox_height * self.scale)

    def _load_scaled(self, folder: str) -> list[pg.Surface]:
        """Load every frame in a folder (natural-sorted) and scale it."""
        frames = AssetManager.get_animation_frames(folder)
        if not frames:
            raise RuntimeError(f"Failed to load any frames from '{folder}'")
        if self.scale == 1.0:
            return list(frames)
        scaled = []
        for frame in frames:
            w = int(frame.get_width() * self.scale)
            h = int(frame.get_height() * self.scale)
            scaled.append(pg.transform.scale(frame, (w, h)))
        return scaled

    # ── Combat interface (mirrors Skeleton/FireWizard) ─────────────────────
    @property
    def health(self) -> float: return self._health
    @property
    def max_health(self) -> float: return self._max_health
    @property
    def entity_id(self) -> int: return id(self)
    @property
    def is_dead(self) -> bool: return self.state == GatekeeperState.DEATH

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
        """Melee reach in front of the Gatekeeper -- only active during the
        ground-slam. The ranged toxic-spit deals damage via its own
        projectile, not through this hitbox."""
        if not self.should_deal_damage() or self._attack_kind != "slam":
            return None
        hitbox_w = self._scaled_hitbox_w
        hitbox_h = self._scaled_hitbox_h
        if self.facing_left:
            hitbox_x = self.rect.left - hitbox_w
        else:
            hitbox_x = self.rect.right
        hitbox_y = self.rect.centery - hitbox_h // 2
        return pg.Rect(hitbox_x, hitbox_y, hitbox_w, hitbox_h)

    def set_state(self, new_state: Enum, force: bool = False) -> None:
        old_state = self.state
        super().set_state(new_state, force=force)

        if old_state == GatekeeperState.ATTACK and self.state != GatekeeperState.ATTACK:
            self.attack_state.end()
            self._chase_cooldown = self._chase_cooldown_duration

        if new_state == GatekeeperState.ATTACK:
            self._has_spawned_attack_effect = False

    def update(self, dt: Optional[float] = None, scroll_speed: int = 0) -> None:
        if dt is None:
            dt_sec = 1.0 / 60.0
        elif dt > 0.5:
            dt_sec = dt / 1000.0
        else:
            dt_sec = dt

        self.rect.x -= scroll_speed
        self._hover_timer += dt_sec

        if self._chase_cooldown > 0.0:
            self._chase_cooldown = max(0.0, self._chase_cooldown - dt_sec)
        if self._attack_cooldown > 0.0:
            self._attack_cooldown = max(0.0, self._attack_cooldown - dt_sec)

        # Spawn the toxic glob mid-way through the spit animation
        if (
            self.state == GatekeeperState.ATTACK
            and self._attack_kind == "spit"
            and not self._has_spawned_attack_effect
            and int(self.animation_index) >= self._SPIT_RELEASE_FRAME
        ):
            self._has_spawned_attack_effect = True
            self._spawn_toxic_glob()

        self._update_ai()
        self._update_vertical_position()

        super().update(dt_sec)

        # Clean up once death animation is fully finished
        if (
            self.state == GatekeeperState.DEATH
            and int(self.animation_index) >= len(self.animations[GatekeeperState.DEATH]) - 1
        ):
            self.kill()

    def _update_vertical_position(self) -> None:
        """Manage the hover offset: gentle bob while idle/chasing, a dive
        toward the ground during a slam, and a slow descent on death."""
        if self.state == GatekeeperState.DEATH:
            frames = self.animations[GatekeeperState.DEATH]
            progress = min(1.0, self.animation_index / max(1, len(frames) - 1))
            self.rect.bottom = int(self._hover_y + progress * self._hover_height)
            return

        if self.state == GatekeeperState.ATTACK and self._attack_kind == "slam":
            frames = self._attack_slam_frames
            progress = self.animation_index / max(1, len(frames) - 1)
            dive = math.sin(min(1.0, progress) * math.pi)  # 0 -> 1 -> 0
            self.rect.bottom = int(self._hover_y + dive * self._hover_height)
            return

        bob = math.sin(self._hover_timer * 3.0) * 6
        self.rect.bottom = int(self._hover_y + bob)

    def _spawn_toxic_glob(self) -> None:
        direction = -1 if self.facing_left else 1
        spawn_x = self.rect.left if self.facing_left else self.rect.right
        spawn_y = self.rect.centery

        damage = self.current_attack_config.base_damage if self.current_attack_config else 3.0
        knockback = self.current_attack_config.knockback_force if self.current_attack_config else 6.0

        glob = ToxicGlob(
            x=spawn_x,
            y=spawn_y,
            direction=direction,
            scale=self.scale,
            damage=damage,
            knockback=knockback,
            player=self._player,
        )
        for group in self.groups():
            group.add(glob)  # type: ignore

    def take_damage(self, amount: float = 0.5) -> None:
        if self.state in (GatekeeperState.HURT, GatekeeperState.DEATH):
            return

        self._health = max(0, self._health - amount)
        self.attack_state.end()

        if self._health <= 0:
            self.set_state(GatekeeperState.DEATH, force=True)
        else:
            self.set_state(GatekeeperState.HURT, force=True)

    def _update_ai(self) -> None:
        if self._player is None or self.state in (GatekeeperState.HURT, GatekeeperState.DEATH):
            return
        if self.state == GatekeeperState.ATTACK:
            return

        player_rect = self._player.rect
        dist_x = self.rect.centerx - player_rect.centerx
        abs_dist_x = abs(dist_x)
        dist_y = abs(self.rect.centery - player_rect.centery)

        if self._chase_cooldown <= 0.0 and self._attack_cooldown <= 0.0 and dist_y < self._vertical_tolerance:
            if abs_dist_x <= self._melee_range:
                self._begin_attack("slam")
                return
            if abs_dist_x <= self._ranged_range:
                self._begin_attack("spit")
                return

        if abs_dist_x > self._melee_range and abs_dist_x <= self._detection_range:
            self.facing_left = dist_x > 0
            self.set_state(GatekeeperState.CHASE)
            self.rect.x += int((-1 if dist_x > 0 else 1) * self._speed)
            return

        self.facing_left = dist_x > 0
        self.set_state(GatekeeperState.IDLE)

    def _begin_attack(self, kind: str) -> None:
        self._attack_kind = kind
        self.animations[GatekeeperState.ATTACK] = (
            self._attack_slam_frames if kind == "slam" else self._attack_spit_frames
        )
        self.facing_left = self.rect.centerx > self._player.rect.centerx
        self.set_state(GatekeeperState.ATTACK, force=True)
        self._attack_cooldown = random.uniform(self._attack_cooldown_min, self._attack_cooldown_max)

    def draw(self, surface: pg.Surface) -> None:
        super().draw(surface)
        if self._health < self._max_health and self.state != GatekeeperState.DEATH:
            self._draw_health_bar(surface)

    def _draw_health_bar(self, surface: pg.Surface) -> None:
        bar_width = 40
        bar_height = 5
        bar_x = self.rect.centerx - bar_width // 2
        bar_y = self.rect.top - 12

        pg.draw.rect(surface, (50, 50, 50), (bar_x, bar_y, bar_width, bar_height))
        health_ratio = max(0.0, self._health / self._max_health)
        pg.draw.rect(surface, (80, 200, 60), (bar_x, bar_y, int(bar_width * health_ratio), bar_height))
