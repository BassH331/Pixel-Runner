"""
Base Enemy Class providing unified combat feel, hit reactions, force field shields,
shadow positioning, and standardized telemetry metadata across all Pixel-Runner enemies.
"""
from __future__ import annotations

import os
import math
import random
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Final, Optional, List, Tuple

import pygame as pg
from v3x_zulfiqar_gideon import Actor, AttackConfig
from src.game.audio.entity_audio_mixin import EntityAudioMixin
from src.game.ai import PerceptionSystem, SquadTokenManager, UtilityCombatEngine

if TYPE_CHECKING:
    from src.game.entities.player import Player


class BaseEnemyShardParticle:
    """Procedural crystalline energy shard spawned when enemy force field shatters."""

    def __init__(self, x: float, y: float, vx: float, vy: float, size: float, color: tuple[int, int, int], lifetime: float):
        self.x = float(x)
        self.y = float(y)
        self.vx = float(vx)
        self.vy = float(vy)
        self.size = float(size)
        self.color = color
        self.lifetime = float(lifetime)
        self.max_lifetime = float(lifetime)
        self.rotation = random.uniform(0.0, 360.0)
        self.rot_speed = random.uniform(-400.0, 400.0)

    def update(self, dt_sec: float, scroll_speed: int = 0) -> bool:
        self.x += (self.vx - scroll_speed) * dt_sec * 60.0
        self.y += self.vy * dt_sec * 60.0
        self.vy += 12.0 * dt_sec
        self.rotation += self.rot_speed * dt_sec
        self.lifetime -= dt_sec
        return self.lifetime <= 0.0

    def draw(self, surface: pg.Surface) -> None:
        if self.lifetime <= 0.0:
            return
        alpha = max(0, min(255, int(255 * (self.lifetime / self.max_lifetime))))
        w = max(2, int(self.size))
        poly_surf = pg.Surface((w * 2 + 4, w * 2 + 4), pg.SRCALPHA)
        pts = [(w, 0), (w * 2, w), (w, w * 2), (0, w)]
        r, g, b = self.color
        pg.draw.polygon(poly_surf, (r, g, b, alpha), pts)
        pg.draw.polygon(poly_surf, (255, 255, 255, alpha), pts, width=1)
        
        rot_surf = pg.transform.rotate(poly_surf, self.rotation)
        rect = rot_surf.get_rect(center=(int(self.x), int(self.y)))
        surface.blit(rot_surf, rect)


class BaseEnemy(EntityAudioMixin, Actor):
    """
    Abstract Base Enemy providing core rendering, hit reactions, shield mechanics,
    and telemetry protocols.
    """

    hit_vfx_type: str = "blood_splatter"

    def __init__(self, x: int, y: int) -> None:
        super().__init__(x, y)
        self.tier: str = "minion"
        self._health: float = 100.0
        self._max_health: float = 100.0
        self._speed: float = 2.5
        self.facing_left: bool = False
        self._margin_left: int = 0
        self._margin_right: int = 0
        self.frame_offsets: dict = {}

        # Procedural hit flash & recoil
        self._hit_flash_duration: float = 0.18
        self._hit_flash_timer: float = 0.0
        self._hit_recoil_dist: float = 12.0
        self._hit_recoil_dx: float = 0.0
        self._squash_stretch_enabled: bool = True

        # Shield mechanics
        self._shield_enabled: bool = False
        self._shield_radius_base: float = 50.0
        self._shield_color: tuple[int, int, int] = (230, 40, 70)
        self._max_shield_health: float = 0.0
        self._shield_health: float = 0.0
        self._shield_recharge_delay: float = 8.0
        self._shield_recharge_timer: float = 0.0
        self._shield_shatter_particles: List[BaseEnemyShardParticle] = []

    @property
    def health(self) -> float:
        return self._health

    @property
    def max_health(self) -> float:
        return self._max_health

    @property
    def is_dead(self) -> bool:
        return self._health <= 0.0

    def get_render_position(self) -> tuple[int, int]:
        """Calculate screen (draw_x, draw_y) for sprite rendering and shadow alignment."""
        anim_key = self.state.name.capitalize() if hasattr(self.state, "name") else "Idle"
        frame_idx = str(int(getattr(self, "animation_index", 0)))
        offset = self.frame_offsets.get(anim_key, {}).get(frame_idx, {})
        dx = int(offset.get("dx", 0) * getattr(self, "scale", 1.0))
        dy = int(offset.get("dy", 0) * getattr(self, "scale", 1.0))

        if self.facing_left:
            dx = -dx

        offset_x = getattr(self, "_margin_right", int(self.image_offset.x)) if self.facing_left else getattr(self, "_margin_left", int(self.image_offset.x))
        base_x = self.rect.x - offset_x
        base_y = self.rect.y - int(self.image_offset.y)
        return base_x + dx, base_y + dy

    def trigger_hit_flash(self) -> None:
        """Trigger procedural white silhouette hit flash & recoil."""
        self._hit_flash_timer = self._hit_flash_duration
        recoil_dir = 1 if self.facing_left else -1
        self._hit_recoil_dx = recoil_dir * self._hit_recoil_dist * getattr(self, "scale", 1.0)

    def draw_white_hit_flash(self, surface: pg.Surface, render_img: pg.Surface, draw_x: int, draw_y: int) -> None:
        """Render pure white additive silhouette flash mask over the sprite when hit."""
        if self._hit_flash_timer > 0.0:
            progress = self._hit_flash_timer / max(0.01, self._hit_flash_duration)
            flash_alpha = int(240 * progress)
            if flash_alpha > 0:
                white_flash = render_img.copy()
                white_flash.fill((255, 255, 255, 0), special_flags=pg.BLEND_RGB_ADD)
                white_flash.set_alpha(flash_alpha)
                surface.blit(white_flash, (draw_x, draw_y))
