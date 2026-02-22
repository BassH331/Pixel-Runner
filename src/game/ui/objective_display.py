"""
Objective display overlay using a parchment background.

Shows level objectives/hints as text on a parchment board,
pausing gameplay until the player dismisses it.
"""

from __future__ import annotations

from typing import Optional

import pygame as pg

from src.my_engine.asset_manager import AssetManager


class ObjectiveDisplay:
    """Full-screen overlay that shows objective text on a parchment board.

    Usage:
        display = ObjectiveDisplay()
        display.show("Defeat all skeletons to proceed!")

        # In game loop:
        if display.is_active:
            display.draw(surface)     # render overlay
            # skip update() to freeze gameplay
    """

    # Parchment sizing relative to screen
    _PARCHMENT_SCALE = 0.55

    # Text padding inside parchment (fraction of parchment size)
    _PAD_X_FRAC = 0.12
    _PAD_Y_TOP_FRAC = 0.15
    _PAD_Y_BOTTOM_FRAC = 0.20  # Extra room for the dismiss prompt

    # Backdrop dimming
    _BACKDROP_ALPHA = 140

    # Text styling
    _TEXT_COLOR = (60, 40, 20)
    _PROMPT_COLOR = (100, 75, 50)
    _TITLE_COLOR = (45, 25, 10)
    _FONT_PATH = "assets/font/Pixeltype.ttf"
    _FONT_SIZE = 38
    _TITLE_FONT_SIZE = 48
    _PROMPT_FONT_SIZE = 28
    _LINE_SPACING = 8

    def __init__(self) -> None:
        display_info = pg.display.Info()
        self._screen_w = display_info.current_w
        self._screen_h = display_info.current_h

        # Load and scale parchment
        raw = AssetManager.get_texture(
            "assets/graphics/UI/PNG/UI board Medium  parchment.png"
        )
        parch_w = int(self._screen_w * self._PARCHMENT_SCALE)
        parch_h = int(parch_w * (raw.get_height() / raw.get_width()))
        self._parchment = pg.transform.smoothscale(raw, (parch_w, parch_h))
        self._parch_rect = self._parchment.get_rect(
            center=(self._screen_w // 2, self._screen_h // 2)
        )

        # Pre-compute text area
        self._text_x = self._parch_rect.x + int(parch_w * self._PAD_X_FRAC)
        self._text_y = self._parch_rect.y + int(parch_h * self._PAD_Y_TOP_FRAC)
        self._text_max_w = parch_w - int(parch_w * self._PAD_X_FRAC * 2)
        self._text_max_h = parch_h - int(
            parch_h * (self._PAD_Y_TOP_FRAC + self._PAD_Y_BOTTOM_FRAC)
        )

        # Fonts
        self._font = AssetManager.get_font(self._FONT_PATH, self._FONT_SIZE)
        self._title_font = AssetManager.get_font(
            self._FONT_PATH, self._TITLE_FONT_SIZE
        )
        self._prompt_font = AssetManager.get_font(
            self._FONT_PATH, self._PROMPT_FONT_SIZE
        )

        # Dark backdrop surface (created once)
        self._backdrop = pg.Surface(
            (self._screen_w, self._screen_h), pg.SRCALPHA
        )
        self._backdrop.fill((0, 0, 0, self._BACKDROP_ALPHA))

        # State
        self._active: bool = False
        self._title: str = ""
        self._wrapped_lines: list[pg.Surface] = []
        self._prompt_surface: Optional[pg.Surface] = None

    # ─────────────────────────────────────────────────────────────────────────

    @property
    def is_active(self) -> bool:
        """Whether the overlay is currently showing."""
        return self._active

    def show(self, text: str, title: str = "Objective") -> None:
        """
        Activate the overlay with the given objective text.

        Args:
            text: The objective description to display.
            title: Header text shown above the objective.
        """
        self._active = True
        self._title = title
        self._wrapped_lines = self._wrap_text(text, self._font, self._text_max_w)
        self._prompt_surface = self._prompt_font.render(
            "[ Press SPACE to continue ]", True, self._PROMPT_COLOR
        )

    def dismiss(self) -> None:
        """Hide the overlay and resume gameplay."""
        self._active = False

    # ─────────────────────────────────────────────────────────────────────────

    def draw(self, surface: pg.Surface) -> None:
        """Render the overlay on top of the current frame."""
        if not self._active:
            return

        # 1) Dim backdrop
        surface.blit(self._backdrop, (0, 0))

        # 2) Parchment board
        surface.blit(self._parchment, self._parch_rect)

        # 3) Title (centered)
        title_surf = self._title_font.render(
            self._title, True, self._TITLE_COLOR
        )
        title_x = self._parch_rect.centerx - title_surf.get_width() // 2
        title_y = self._text_y
        surface.blit(title_surf, (title_x, title_y))

        # 4) Body text (below title)
        y = title_y + title_surf.get_height() + self._LINE_SPACING * 2
        for line_surf in self._wrapped_lines:
            if y + line_surf.get_height() > self._text_y + self._text_max_h:
                break  # Don't overflow
            # Center each line within text area
            lx = self._text_x + (self._text_max_w - line_surf.get_width()) // 2
            surface.blit(line_surf, (lx, y))
            y += line_surf.get_height() + self._LINE_SPACING

        # 5) Dismiss prompt (bottom center of parchment)
        if self._prompt_surface:
            px = self._parch_rect.centerx - self._prompt_surface.get_width() // 2
            py = (
                self._parch_rect.bottom
                - int(self._parch_rect.height * self._PAD_Y_BOTTOM_FRAC * 0.6)
            )
            # Subtle pulsing alpha
            alpha = 160 + int(95 * abs(((pg.time.get_ticks() // 8) % 200 - 100) / 100))
            self._prompt_surface.set_alpha(alpha)
            surface.blit(self._prompt_surface, (px, py))

    # ─────────────────────────────────────────────────────────────────────────

    @staticmethod
    def _wrap_text(
        text: str,
        font: pg.font.Font,
        max_width: int,
    ) -> list[pg.Surface]:
        """Word-wrap text into rendered line surfaces."""
        words = text.split()
        lines: list[pg.Surface] = []
        current_line = ""

        for word in words:
            test = f"{current_line} {word}".strip()
            if font.size(test)[0] <= max_width:
                current_line = test
            else:
                if current_line:
                    lines.append(
                        font.render(current_line, True, ObjectiveDisplay._TEXT_COLOR)
                    )
                current_line = word

        if current_line:
            lines.append(
                font.render(current_line, True, ObjectiveDisplay._TEXT_COLOR)
            )

        return lines
