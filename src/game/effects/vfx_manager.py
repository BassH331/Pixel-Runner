"""
Modular Impact & Hit Visual Effect Manager.

Manages cached animation frame sets and active temporary visual effect overlays for
magic shots, energy impacts, and spark effects.
"""

import os
import re
from typing import Optional, List, Dict, Tuple, Any
import pygame as pg

from v3x_zulfiqar_gideon import AssetManager


class VisualEffect(pg.sprite.Sprite):
    """An animated visual effect sprite that plays once and self-destructs."""

    def __init__(
        self,
        x: int,
        y: int,
        frames: List[pg.Surface],
        fps: float = 16.0,
        target_entity: Optional[Any] = None,
    ):
        super().__init__()
        self.frames = frames
        self.frame_duration = 1.0 / max(1.0, fps)
        self.current_frame = 0.0
        self.image = self.frames[0]
        self.rect = self.image.get_rect(center=(x, y))
        self.target_entity = target_entity

    def update(self, dt: float = 0.016, scroll_speed: int = 0) -> None:
        dt_sec = dt if dt < 1.0 else dt / 1000.0
        if self.target_entity is not None and hasattr(self.target_entity, "rect"):
            self.rect.center = self.target_entity.rect.center
        else:
            self.rect.x -= scroll_speed

        self.current_frame += dt_sec / self.frame_duration
        idx = int(self.current_frame)
        if idx >= len(self.frames):
            self.kill()
        else:
            self.image = self.frames[idx]

    def draw(self, surface: pg.Surface) -> None:
        surface.blit(self.image, self.rect)


class VisualEffectManager:
    """Central manager for spawning modular hit/impact VFX across the game."""

    _vfx_cache: Dict[Tuple[str, float], List[pg.Surface]] = {}
    _active_effects: pg.sprite.Group = pg.sprite.Group()

    VFX_PATHS = {
        "magic_shot": "assets/graphics/Magic shots/1",
        "magic_swirl": "assets/graphics/swirl magic shots/1",
        "blood_splatter": "assets/graphics/MiniBlood/Polished/1",
        "blood_mini": "assets/graphics/blood_animation",
        "toxic_splatter": "assets/graphics/MiniBlood/Polished/1",
        "dark_shadow": "assets/graphics/swirl magic shots/1",
        "fire_sparks": "assets/graphics/Fw effects",
        "bone_sparks": "assets/graphics/swirl magic shots/1",
    }

    VFX_TINTS: Dict[str, Tuple[int, int, int]] = {
        "toxic_splatter": (60, 240, 60),
        "dark_shadow": (160, 40, 240),
        "bone_sparks": (220, 230, 245),
        "fire_sparks": (255, 140, 30),
    }

    @classmethod
    def get_effect_frames(cls, effect_key: str, scale: float = 1.0) -> List[pg.Surface]:
        cache_key = (effect_key, scale)
        if cache_key in cls._vfx_cache:
            return cls._vfx_cache[cache_key]

        path = cls.VFX_PATHS.get(effect_key, cls.VFX_PATHS["magic_shot"])
        raw_frames: List[pg.Surface] = []

        if os.path.exists(path) and os.path.isdir(path):
            try:
                files = [f for f in os.listdir(path) if f.lower().endswith((".png", ".jpg"))]

                def _sort_key(filename: str) -> int:
                    m = re.search(r"\d+", filename)
                    return int(m.group()) if m is not None else 0

                files.sort(key=_sort_key)
                for fname in files:
                    fpath = os.path.join(path, fname)
                    raw_frames.append(AssetManager.get_texture(fpath))
            except Exception:
                pass

        if not raw_frames:
            raw_frames = AssetManager.get_animation_frames(path)

        if not raw_frames:
            surf = pg.Surface((24, 24), pg.SRCALPHA)
            pg.draw.circle(surf, (255, 200, 0, 200), (12, 12), 10)
            raw_frames = [surf]

        tint = cls.VFX_TINTS.get(effect_key)

        scaled_frames: List[pg.Surface] = []
        for frame in raw_frames:
            w = int(frame.get_width() * scale)
            h = int(frame.get_height() * scale)
            base_surf = frame
            if w > 0 and h > 0:
                base_surf = pg.transform.scale(frame, (w, h))

            if tint is not None:
                tinted = base_surf.copy()
                tint_mask = pg.Surface(base_surf.get_size(), pg.SRCALPHA)
                tint_mask.fill((*tint, 255))
                tinted.blit(tint_mask, (0, 0), special_flags=pg.BLEND_RGBA_MULT)
                scaled_frames.append(tinted)
            else:
                scaled_frames.append(base_surf)

        cls._vfx_cache[cache_key] = scaled_frames
        return scaled_frames

    VFX_FPS: Dict[str, float] = {
        "fire_sparks": 12.0,
        "blood_mini": 14.0,
        "blood_splatter": 18.0,
        "toxic_splatter": 18.0,
        "dark_shadow": 24.0,
        "bone_sparks": 24.0,
        "magic_shot": 18.0,
        "magic_swirl": 24.0,
    }

    @classmethod
    def spawn_hit_vfx(
        cls,
        x: int,
        y: int,
        entity: Optional[Any] = None,
        vfx_type: Optional[str] = None,
        scale: float = 1.0,
        target_entity: Optional[Any] = None,
        fps_override: Optional[float] = None,
    ) -> Optional[VisualEffect]:
        """Spawns an impact magic/spark VFX at (x, y)."""
        if not vfx_type:
            vfx_type = "magic_shot"

        if scale == 1.0:
            scale = 2.5

        frames = cls.get_effect_frames(vfx_type, scale=scale)
        if not frames:
            return None

        fps = fps_override if fps_override is not None else cls.VFX_FPS.get(vfx_type, 18.0)
        vfx = VisualEffect(x, y, frames, fps=fps, target_entity=target_entity or entity)
        cls._active_effects.add(vfx)
        return vfx

    @classmethod
    def update(cls, dt: float = 0.016, scroll_speed: int = 0) -> None:
        dt_sec = dt if dt < 1.0 else dt / 1000.0
        cls._active_effects.update(dt=dt_sec, scroll_speed=scroll_speed)

    @classmethod
    def draw(cls, surface: pg.Surface) -> None:
        for vfx in cls._active_effects:
            vfx.draw(surface)

    @classmethod
    def clear(cls) -> None:
        cls._active_effects.empty()
