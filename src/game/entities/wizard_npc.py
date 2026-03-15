"""
Wizard NPC entity — an animated, non-hostile character placed in the game world.

Loads the 6 idle-animation frames from ``assets/graphics/Wizard_NPC/``,
scrolls with the background, and displays a proximity-based "Talk" prompt
using the same UX pattern as :class:`InteractionPoint`.
"""

from __future__ import annotations

from typing import Optional

import pygame as pg

from v3x_zulfiqar_gideon.animation import Animation, Animator
from v3x_zulfiqar_gideon.asset_manager import AssetManager


class WizardNPC(pg.sprite.Sprite):
    """Animated Wizard NPC with proximity-based dialogue support.

    Args:
        x: Initial world X position.
        y: Screen Y position (foot anchor).
        text: Dialogue text shown in the parchment overlay.
        title: Header for the parchment overlay (default ``"Wizard"``).
        scale: Sprite scale factor (default ``2.0``).
        proximity_radius: Pixel distance to activate the talk prompt.
    """

    _SPRITE_DIR = "assets/graphics/Wizard_NPC"
    _FRAME_COUNT = 6
    _FRAME_DURATION = 0.18  # seconds per frame

    # Prompt styling (mirrors InteractionPoint)
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
        text: str,
        title: str = "Wizard",
        scale: float = 2.0,
        proximity_radius: int = 160,
    ) -> None:
        super().__init__()

        self.text = text
        self.title = title
        self.proximity_radius = proximity_radius
        self._interacted: bool = False
        self._in_range: bool = False

        # --- Animation ---
        self.scale = scale
        self.animator = Animator()
        self._load_animations()

        self.image = self.animator.get_frame()
        self.rect = self.image.get_rect(midbottom=(x, y))

        # --- Talk prompt (cached surface) ---
        self._font = AssetManager.get_font(self._FONT_PATH, self._FONT_SIZE)
        self._prompt_surface = self._build_prompt()

    # ------------------------------------------------------------------
    # Animation helpers
    # ------------------------------------------------------------------

    def _load_animations(self) -> None:
        frames: list[pg.Surface] = []
        for i in range(self._FRAME_COUNT):
            path = f"{self._SPRITE_DIR}/wizard_npc_{i}.png"
            frame = AssetManager.get_texture(path)
            if self.scale != 1.0:
                new_w = int(frame.get_width() * self.scale)
                new_h = int(frame.get_height() * self.scale)
                frame = pg.transform.scale(frame, (new_w, new_h))
            frames.append(frame)

        self.animator.add("idle", Animation(frames, self._FRAME_DURATION, loop=True))
        self.animator.set("idle")

    # ------------------------------------------------------------------
    # Talk prompt
    # ------------------------------------------------------------------

    def _build_prompt(self) -> pg.Surface:
        """Create the cached "Talk [X / ENTER]" prompt surface."""
        text_surf = self._font.render(
            "Talk  [ X / ENTER ]", True, self._PROMPT_COLOR
        )
        w = text_surf.get_width() + self._PROMPT_PADDING_X * 2
        h = text_surf.get_height() + self._PROMPT_PADDING_Y * 2

        bg = pg.Surface((w, h), pg.SRCALPHA)
        pg.draw.rect(
            bg,
            self._PROMPT_BG_COLOR,
            (0, 0, w, h),
            border_radius=self._PROMPT_BORDER_RADIUS,
        )
        pg.draw.rect(
            bg,
            (200, 200, 200, 120),
            (0, 0, w, h),
            width=2,
            border_radius=self._PROMPT_BORDER_RADIUS,
        )
        bg.blit(text_surf, (self._PROMPT_PADDING_X, self._PROMPT_PADDING_Y))
        return bg

    # ------------------------------------------------------------------
    # Interaction API (same interface as InteractionPoint)
    # ------------------------------------------------------------------

    @property
    def can_interact(self) -> bool:
        """True when the player is nearby and hasn't yet interacted."""
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

    # ------------------------------------------------------------------
    # Sprite update / draw
    # ------------------------------------------------------------------

    def update(
        self,
        dt: Optional[float] = None,
        scroll_speed: int = 0,
    ) -> None:
        """Scroll with the world and advance idle animation."""
        self.rect.x -= scroll_speed

        dt_sec = (dt / 1000.0) if dt and dt > 1 else (dt or 0)
        self.animator.update(dt_sec)
        self.image = self.animator.get_frame()

    def draw(self, surface: pg.Surface) -> None:
        """Render the NPC sprite and, if applicable, the talk prompt."""
        surface.blit(self.image, self.rect)

        if not self.can_interact:
            return

        # Pulsing alpha for visibility
        ticks = pg.time.get_ticks()
        alpha = 180 + int(75 * abs(((ticks // 8) % 200 - 100) / 100))
        self._prompt_surface.set_alpha(alpha)

        px = self.rect.centerx - self._prompt_surface.get_width() // 2
        py = self.rect.top + self._PROMPT_OFFSET_Y
        surface.blit(self._prompt_surface, (px, py))
