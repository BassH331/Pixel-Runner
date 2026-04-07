"""
Generic NPC — a data-driven NPC that can use any sprite folder.

Add new NPCs purely from ``level_1.json`` without writing Python code::

    {
        "id": 6,
        "distance": 5000,
        "type": "npc",
        "params": {
            "npc_type": "generic",
            "sprite_dir": "assets/graphics/Goblin/Idle",
            "title": "Goblin Merchant",
            "radius": 160,
            "scale": 2.0,
            "text": "Got some rare trinkets, if you're interested..."
        }
    }

The ``sprite_dir`` should point to a folder of numbered PNG frames
(e.g. idle_0.png, idle_1.png …).  The NPC will loop through them as
its idle animation.
"""

from __future__ import annotations

from typing import Optional
from enum import Enum

import pygame as pg

from v3x_zulfiqar_gideon.ecs import Actor
from v3x_zulfiqar_gideon.asset_manager import AssetManager


class _GenericNPCState(Enum):
    IDLE = 0


class GenericNPC(Actor):
    """A reusable NPC driven entirely by constructor arguments.

    Args:
        x, y:               Spawn position (y = feet/midbottom).
        sprite_dir:         Path to the folder containing animation frames.
        text:               Dialogue shown on interaction.
        title:              Name shown above dialogue.
        scale:              Sprite scale multiplier.
        proximity_radius:   Pixel distance to show the "Talk" prompt.
        frame_duration:     Seconds per animation frame.
        prompt_text:        Text shown on the proximity prompt.
    """

    # Prompt styling (same as WizardNPC for visual consistency)
    _FONT_PATH = "assets/Colorfiction_HandDrawnFonts/Colorfiction - Papyrus.otf"
    _FONT_SIZE = 30
    _PROMPT_COLOR = (255, 255, 255)
    _PROMPT_BG_COLOR = (30, 30, 30, 200)
    _PROMPT_PADDING_X = 16
    _PROMPT_PADDING_Y = 8
    _PROMPT_OFFSET_Y = -70
    _PROMPT_BORDER_RADIUS = 8

    def __init__(
        self,
        x: int,
        y: int,
        sprite_dir: str,
        text: str,
        title: str = "NPC",
        scale: float = 2.0,
        proximity_radius: int = 160,
        frame_duration: float = 0.15,
        prompt_text: str = "Talk  [ X / ENTER ]",
    ) -> None:
        super().__init__(x, y)

        self.text = text
        self.title = title
        self.proximity_radius = proximity_radius
        self._interacted: bool = False
        self._in_range: bool = False

        # ── Load animation frames from the given folder ─────────────────────
        raw_frames = AssetManager.get_animation_frames(sprite_dir)
        if not raw_frames:
            # Fallback: create a placeholder surface so the game doesn't crash
            placeholder = pg.Surface((32, 32), pg.SRCALPHA)
            placeholder.fill((255, 0, 255, 180))
            raw_frames = [placeholder]

        scaled_frames: list[pg.Surface] = []
        for frame in raw_frames:
            w = int(frame.get_width() * scale)
            h = int(frame.get_height() * scale)
            scaled_frames.append(pg.transform.scale(frame, (w, h)))

        self.animations[_GenericNPCState.IDLE] = scaled_frames
        self.state_configs[_GenericNPCState.IDLE] = type(
            "SC", (), {"animation_speed": frame_duration, "loops": True, "interruptible": False}
        )()
        self.set_state(_GenericNPCState.IDLE)

        self.rect = self.image.get_rect(midbottom=(x, y))

        # ── Talk prompt (cached surface) ────────────────────────────────────
        self._font = AssetManager.get_font(self._FONT_PATH, self._FONT_SIZE)
        self._prompt_surface = self._build_prompt(prompt_text)

    def _build_prompt(self, text: str) -> pg.Surface:
        text_surf = self._font.render(text, True, self._PROMPT_COLOR)
        w = text_surf.get_width() + self._PROMPT_PADDING_X * 2
        h = text_surf.get_height() + self._PROMPT_PADDING_Y * 2

        bg = pg.Surface((w, h), pg.SRCALPHA)
        pg.draw.rect(bg, self._PROMPT_BG_COLOR, (0, 0, w, h),
                     border_radius=self._PROMPT_BORDER_RADIUS)
        pg.draw.rect(bg, (200, 200, 200, 120), (0, 0, w, h),
                     width=2, border_radius=self._PROMPT_BORDER_RADIUS)
        bg.blit(text_surf, (self._PROMPT_PADDING_X, self._PROMPT_PADDING_Y))
        return bg

    # ─── Interaction interface (same as WizardNPC) ───────────────────────────

    @property
    def can_interact(self) -> bool:
        return self._in_range and not self._interacted

    @property
    def has_been_used(self) -> bool:
        return self._interacted

    def mark_interacted(self) -> None:
        self._interacted = True

    def reset(self) -> None:
        self._interacted = False

    def check_proximity(self, player_rect: pg.Rect) -> bool:
        dx = abs(self.rect.centerx - player_rect.centerx)
        dy = abs(self.rect.centery - player_rect.centery)
        distance = (dx * dx + dy * dy) ** 0.5
        self._in_range = distance <= self.proximity_radius
        return self._in_range

    # ─── Update & Draw ───────────────────────────────────────────────────────

    def update(self, dt: Optional[float] = None, scroll_speed: int = 0) -> None:
        self.rect.x -= scroll_speed
        super().update(dt)

    def draw(self, surface: pg.Surface) -> None:
        super().draw(surface)

        if not self.can_interact:
            return

        ticks = pg.time.get_ticks()
        alpha = 180 + int(75 * abs(((ticks // 8) % 200 - 100) / 100))
        self._prompt_surface.set_alpha(alpha)

        px = self.rect.centerx - self._prompt_surface.get_width() // 2
        py = self.rect.top + self._PROMPT_OFFSET_Y
        surface.blit(self._prompt_surface, (px, py))
