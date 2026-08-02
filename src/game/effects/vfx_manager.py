"""
Modular Hit Visual Effect Manager (Hit FX, Blood Bursts, Magic Shot Effects).

Manages cached animation frame sets and active temporary visual effect overlays.
Rules:
- Skeletons (has_blood=False) trigger spark / magic energy impact bursts.
- Fleshy entities (Player, Blood Zombie, Green Monster, Goblin with has_blood=True) trigger blood bursts.
"""

import os
from typing import Optional, List, Dict, Tuple, Any
import pygame as pg

from v3x_zulfiqar_gideon import AssetManager


class VisualEffect(pg.sprite.Sprite):
    """An animated visual effect sprite that plays once and self-destructs."""

    def __init__(self, x: int, y: int, frames: List[pg.Surface], fps: float = 30.0):
        super().__init__()
        self.frames = frames
        self.frame_duration = 1.0 / fps
        self.current_frame = 0.0
        self.image = self.frames[0]
        self.rect = self.image.get_rect(center=(x, y))

    def update(self, dt: float = 0.016, scroll_speed: int = 0) -> None:
        self.rect.x -= scroll_speed
        self.current_frame += dt / self.frame_duration
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
        "blood": "assets/graphics/MiniBlood/Polished/1",
        "blood_large": "assets/graphics/MiniBlood/Polished/3",
        "magic_shot": "assets/graphics/Magic shots/1",
        "magic_swirl": "assets/graphics/swirl magic shots/1",
    }

    @classmethod
    def get_effect_frames(cls, effect_key: str, scale: float = 1.0) -> List[pg.Surface]:
        cache_key = (effect_key, scale)
        if cache_key in cls._vfx_cache:
            return cls._vfx_cache[cache_key]

        path = cls.VFX_PATHS.get(effect_key, cls.VFX_PATHS["blood"])
        raw_frames = AssetManager.get_animation_frames(path)
        if not raw_frames:
            # Fallback placeholder if path missing
            surf = pg.Surface((24, 24), pg.SRCALPHA)
            pg.draw.circle(surf, (255, 0, 0, 200), (12, 12), 10)
            raw_frames = [surf]

        scaled_frames: List[pg.Surface] = []
        for frame in raw_frames:
            w = int(frame.get_width() * scale)
            h = int(frame.get_height() * scale)
            if w > 0 and h > 0:
                scaled_frames.append(pg.transform.scale(frame, (w, h)))
            else:
                scaled_frames.append(frame)

        cls._vfx_cache[cache_key] = scaled_frames
        return scaled_frames

    @classmethod
    def spawn_hit_vfx(
        cls,
        x: int,
        y: int,
        entity: Optional[Any] = None,
        vfx_type: Optional[str] = None,
        scale: float = 1.0,
    ) -> Optional[VisualEffect]:
        """Spawns an impact VFX at (x, y).

        Rules:
        - If entity is a Skeleton or has `has_blood == False`, spawns sparks/magic_shot VFX.
        - If entity is Player, Blood Zombie, Green Monster, Goblin or has `has_blood == True`, spawns blood burst.
        """
        if vfx_type is None and entity is not None:
            try:
                from src.game.plugins.vfx_plugin import VFXPlugin
                rule = VFXPlugin.get_rule(entity)
                vfx_type = rule["vfx_type"]
                if scale == 1.0:
                    scale = float(rule.get("vfx_scale", 2.5))
            except Exception:
                has_blood = getattr(entity, "has_blood", None)
                is_skeleton = getattr(entity, "is_skeleton", False)
                if has_blood is False or is_skeleton:
                    vfx_type = "magic_shot"
                else:
                    vfx_type = "blood"

        if not vfx_type:
            vfx_type = "blood"

        # Apply prominent default scaling if not explicitly overridden (2.5x scale)
        if scale == 1.0:
            scale = 2.5 if vfx_type in ("blood", "blood_large", "magic_shot", "magic_swirl") else 1.8

        frames = cls.get_effect_frames(vfx_type, scale=scale)
        if not frames:
            return None

        vfx = VisualEffect(x, y, frames)
        cls._active_effects.add(vfx)
        return vfx

    @classmethod
    def update(cls, dt: float = 0.016, scroll_speed: int = 0) -> None:
        cls._active_effects.update(dt=dt, scroll_speed=scroll_speed)

    @classmethod
    def draw(cls, surface: pg.Surface) -> None:
        for vfx in cls._active_effects:
            vfx.draw(surface)

    @classmethod
    def clear(cls) -> None:
        cls._active_effects.empty()
