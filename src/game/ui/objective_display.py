"""
Objective display overlay using a parchment background.

Shows level objectives/hints as text on a parchment board,
pausing gameplay until the player dismisses it.
"""

from __future__ import annotations

from typing import Optional, Tuple

import pygame as pg

from v3x_zulfiqar_gideon.asset_manager import AssetManager


class ObjectiveDisplay:
    """Full-screen overlay that shows objective text on a parchment board.

    Every visual aspect is configurable via constructor arguments.

    Usage:
        display = ObjectiveDisplay()
        display.show("Defeat all skeletons to proceed!")

        # Custom styling:
        display = ObjectiveDisplay(
            parchment_scale=0.6,
            title_color=(80, 30, 10),
            font_size=42,
            prompt_text="[ Press SPACE ]",
        )

        # In game loop:
        if display.is_active:
            display.draw(surface)     # render overlay
            # skip update() to freeze gameplay

    Args:
        parchment_scale:   Parchment width as fraction of screen width.
        stone_scale:       Stone board width as fraction of screen width.
        backdrop_alpha:    Dim-overlay opacity (0–255).
        text_color:        RGB for body text.
        title_color:       RGB for title text.
        prompt_color:      RGB for dismiss prompt.
        font_size:         Body text font size.
        title_font_size:   Title font size.
        prompt_font_size:  Dismiss prompt font size.
        line_spacing:      Pixel gap between text lines.
        prompt_text:       Text shown for the dismiss prompt.
        pad_x_frac:        Horizontal text padding (fraction of parchment width).
        pad_y_top_frac:    Top text padding (fraction of parchment height).
        pad_y_bottom_frac: Bottom padding reserved for prompt.
    """

    # ── Asset paths ──────────────────────────────────────────────────────────
    _STONE_PATH = "assets/graphics/UI/PNG/UI board Medium  stone.png"
    _PARCHMENT_PATH = "assets/graphics/UI/PNG/UI board Medium  parchment.png"
    _TITLE_FONT_PATH = (
        "assets/Colorfiction_HandDrawnFonts/Colorfiction - Gothic - Regular.otf"
    )
    _BODY_FONT_PATH = (
        "assets/Colorfiction_HandDrawnFonts/Colorfiction - Papyrus.otf"
    )

    # ── Defaults ─────────────────────────────────────────────────────────────
    _DEF_PARCHMENT_SCALE = 0.55
    _DEF_STONE_SCALE = 0.59
    _DEF_BACKDROP_ALPHA = 140
    _DEF_TEXT_COLOR = (60, 40, 20)
    _DEF_TITLE_COLOR = (45, 25, 10)
    _DEF_PROMPT_COLOR = (100, 75, 50)
    _DEF_FONT_SIZE = 38
    _DEF_TITLE_FONT_SIZE = 48
    _DEF_PROMPT_FONT_SIZE = 28
    _DEF_LINE_SPACING = 8
    _DEF_PROMPT_TEXT = "[ Press SPACE to continue ]"
    _DEF_PAD_X_FRAC = 0.12
    _DEF_PAD_Y_TOP_FRAC = 0.15
    _DEF_PAD_Y_BOTTOM_FRAC = 0.20

    def __init__(
        self,
        parchment_scale: float = _DEF_PARCHMENT_SCALE,
        stone_scale: float = _DEF_STONE_SCALE,
        backdrop_alpha: int = _DEF_BACKDROP_ALPHA,
        text_color: Tuple[int, int, int] = _DEF_TEXT_COLOR,
        title_color: Tuple[int, int, int] = _DEF_TITLE_COLOR,
        prompt_color: Tuple[int, int, int] = _DEF_PROMPT_COLOR,
        font_size: int = _DEF_FONT_SIZE,
        title_font_size: int = _DEF_TITLE_FONT_SIZE,
        prompt_font_size: int = _DEF_PROMPT_FONT_SIZE,
        line_spacing: int = _DEF_LINE_SPACING,
        prompt_text: str = _DEF_PROMPT_TEXT,
        pad_x_frac: float = _DEF_PAD_X_FRAC,
        pad_y_top_frac: float = _DEF_PAD_Y_TOP_FRAC,
        pad_y_bottom_frac: float = _DEF_PAD_Y_BOTTOM_FRAC,
    ) -> None:
        # Store instance config
        self._text_color = text_color
        self._title_color = title_color
        self._prompt_color = prompt_color
        self._line_spacing = line_spacing
        self._prompt_text = prompt_text
        self._pad_y_bottom_frac = pad_y_bottom_frac

        display_info = pg.display.Info()
        self._screen_w = display_info.current_w
        self._screen_h = display_info.current_h

        # Load and scale stone
        raw = AssetManager.get_texture(self._STONE_PATH)
        stone_w = int(self._screen_w * stone_scale)
        stone_h = int(stone_w * (raw.get_height() / raw.get_width()))
        self._stone = pg.transform.smoothscale(raw, (stone_w, stone_h))
        self._stone_rect = self._stone.get_rect(
            center=(self._screen_w // 2, self._screen_h // 2)
        )

        # Load and scale parchment
        raw = AssetManager.get_texture(self._PARCHMENT_PATH)
        parch_w = int(self._screen_w * parchment_scale)
        parch_h = int(parch_w * (raw.get_height() / raw.get_width()))
        self._parchment = pg.transform.smoothscale(raw, (parch_w, parch_h))
        self._parch_rect = self._parchment.get_rect(
            center=(self._screen_w // 2, self._screen_h // 2)
        )

        # Pre-compute text area
        self._text_x = self._parch_rect.x + int(parch_w * pad_x_frac)
        self._text_y = self._parch_rect.y + int(parch_h * pad_y_top_frac)
        self._text_max_w = parch_w - int(parch_w * pad_x_frac * 2)
        self._text_max_h = parch_h - int(
            parch_h * (pad_y_top_frac + pad_y_bottom_frac)
        )

        # Fonts – Gothic for title, Papyrus for body & prompt
        self._font = AssetManager.get_font(self._BODY_FONT_PATH, font_size)
        self._title_font = AssetManager.get_font(
            self._TITLE_FONT_PATH, title_font_size
        )
        self._prompt_font = AssetManager.get_font(
            self._BODY_FONT_PATH, prompt_font_size
        )

        # Dark backdrop surface (created once)
        self._backdrop = pg.Surface(
            (self._screen_w, self._screen_h), pg.SRCALPHA
        )
        self._backdrop.fill((0, 0, 0, backdrop_alpha))

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
        self._wrapped_lines = self._wrap_text(
            text, self._font, self._text_max_w, self._text_color
        )
        self._prompt_surface = self._prompt_font.render(
            self._prompt_text, True, self._prompt_color
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

        # 2) Stone board (behind parchment)
        surface.blit(self._stone, self._stone_rect)

        # 3) Parchment board
        surface.blit(self._parchment, self._parch_rect)

        # 4) Title (centered)
        title_surf = self._title_font.render(
            self._title, True, self._title_color
        )
        title_x = self._parch_rect.centerx - title_surf.get_width() // 2
        title_y = self._text_y
        surface.blit(title_surf, (title_x, title_y))

        # 5) Body text (below title)
        y = title_y + title_surf.get_height() + self._line_spacing * 2
        for line_surf in self._wrapped_lines:
            if y + line_surf.get_height() > self._text_y + self._text_max_h:
                break  # Don't overflow
            # Center each line within text area
            lx = self._text_x + (self._text_max_w - line_surf.get_width()) // 2
            surface.blit(line_surf, (lx, y))
            y += line_surf.get_height() + self._line_spacing

        # 6) Dismiss prompt (bottom center of parchment)
        if self._prompt_surface:
            px = self._parch_rect.centerx - self._prompt_surface.get_width() // 2
            py = (
                self._parch_rect.bottom
                - int(self._parch_rect.height * self._pad_y_bottom_frac * 0.6)
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
        color: Tuple[int, int, int],
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
                    lines.append(font.render(current_line, True, color))
                current_line = word

        if current_line:
            lines.append(font.render(current_line, True, color))

        return lines
