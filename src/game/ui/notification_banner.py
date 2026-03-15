"""
Reusable notification banner overlay.

Shows an iron title banner with an exclamation icon and text.
Fades in, holds, then fades out automatically.

Usage:
    banner = NotificationBanner()
    banner.show("The Blight Begins", notification="red")
    # In update loop:
    banner.update(dt)
    # In draw loop (after everything else):
    banner.draw(surface)
"""

from __future__ import annotations

import math
from typing import Optional, Tuple

import pygame as pg

from v3x_zulfiqar_gideon.asset_manager import AssetManager


def _ease_in_out(t: float) -> float:
    """Smooth ease-in-out (sine curve). t in [0,1] → [0,1]."""
    return 0.5 - 0.5 * math.cos(math.pi * t)


class NotificationBanner:
    """Self-contained notification banner with fade-in / hold / fade-out.

    Every visual aspect is configurable via constructor arguments.

    Args:
        fade_in:          Fade-in duration (seconds).
        hold:             On-screen hold duration (seconds).
        fade_out:         Fade-out duration (seconds).
        scale:            Overall size multiplier (banner + font).
        icon_scale:       Extra multiplier for the exclamation icon only.
        banner_width_frac: Banner width as fraction of screen width.
        y_frac:           Vertical position (0.0 = top, 0.5 = center, 1.0 = bottom).
        font_size:        Base font size before ``scale`` is applied.
        text_color:       RGB tuple for title text.
        shadow_color:     RGB tuple for drop-shadow text.
    """

    # ── Asset paths ──────────────────────────────────────────────────────────
    _BANNER_PATH = "assets/graphics/UI/PNG/IRONY TITLE  Large.png"
    _ICONS = {
        "gray": "assets/graphics/UI/PNG/Exclamation_Gray.png",
        "red": "assets/graphics/UI/PNG/Exclamation_Red.png",
        "yellow": "assets/graphics/UI/PNG/Exclamation_Yellow.png",
    }
    _FONT_PATH = (
        "assets/Colorfiction_HandDrawnFonts/Colorfiction - Gothic - Regular.otf"
    )

    # ── Defaults ─────────────────────────────────────────────────────────────
    _DEFAULT_FADE_IN = 0.8
    _DEFAULT_HOLD = 2.0
    _DEFAULT_FADE_OUT = 0.8
    _DEFAULT_FONT_SIZE = 52
    _DEFAULT_TEXT_COLOR = (230, 220, 200)
    _DEFAULT_SHADOW_COLOR = (20, 15, 10)

    def __init__(
        self,
        fade_in: float = _DEFAULT_FADE_IN,
        hold: float = _DEFAULT_HOLD,
        fade_out: float = _DEFAULT_FADE_OUT,
        scale: float = 1.0,
        icon_scale: float = 1.0,
        banner_width_frac: float = 0.45,
        y_frac: float = 0.5,
        font_size: int = _DEFAULT_FONT_SIZE,
        text_color: Tuple[int, int, int] = _DEFAULT_TEXT_COLOR,
        shadow_color: Tuple[int, int, int] = _DEFAULT_SHADOW_COLOR,
    ) -> None:
        # Timing
        self._fade_in = fade_in
        self._hold = hold
        self._fade_out = fade_out

        # Colors
        self._text_color = text_color
        self._shadow_color = shadow_color

        # Position
        self._y_frac = y_frac

        info = pg.display.Info()
        self._sw = info.current_w
        self._sh = info.current_h

        # Pre-scale the banner once
        raw_banner = AssetManager.get_texture(self._BANNER_PATH)
        banner_w = int(self._sw * banner_width_frac * scale)
        banner_h = int(banner_w * (raw_banner.get_height() / raw_banner.get_width()))
        self._banner = pg.transform.smoothscale(raw_banner, (banner_w, banner_h))
        self._banner_h = banner_h

        # Pre-scale all icon variants
        icon_size = int(banner_h * 1.1 * icon_scale)
        self._icons: dict[str, pg.Surface] = {}
        for key, path in self._ICONS.items():
            raw = AssetManager.get_texture(path)
            self._icons[key] = pg.transform.smoothscale(raw, (icon_size, icon_size))

        # Font (scaled)
        self._font = AssetManager.get_font(
            self._FONT_PATH, int(font_size * scale)
        )

        # Runtime state
        self._active = False
        self._timer = 0.0
        self._title = ""
        self._icon_key = "gray"

    # ── Public API ───────────────────────────────────────────────────────────

    @property
    def is_active(self) -> bool:
        """True while the banner is visible."""
        return self._active

    def show(
        self,
        title: str,
        notification: str = "gray",
    ) -> None:
        """Display the banner with the given title and icon type.

        Args:
            title:        Text to display on the banner.
            notification: Icon variant — ``"gray"``, ``"red"``, or ``"yellow"``.
        """
        self._title = title
        self._icon_key = notification if notification in self._icons else "gray"
        self._timer = 0.0
        self._active = True

    def dismiss(self) -> None:
        """Immediately hide the banner."""
        self._active = False

    # ── Update / Draw ────────────────────────────────────────────────────────

    def update(self, dt: float) -> None:
        """Advance the banner timer.  ``dt`` is in **milliseconds**."""
        if not self._active:
            return
        self._timer += dt / 1000.0
        total = self._fade_in + self._hold + self._fade_out
        if self._timer >= total:
            self._active = False

    def draw(self, surface: pg.Surface) -> None:
        """Render the banner overlay on top of the game frame."""
        if not self._active:
            return

        t = self._timer
        fade_end = self._fade_in
        hold_end = fade_end + self._hold
        total = hold_end + self._fade_out

        # Alpha with easing
        if t < fade_end:
            alpha = _ease_in_out(t / fade_end)
        elif t < hold_end:
            alpha = 1.0
        else:
            alpha = 1.0 - _ease_in_out(min(1.0, (t - hold_end) / self._fade_out))
        alpha_int = int(255 * max(0.0, min(1.0, alpha)))

        # Slight upward slide during fade-in
        slide = int(20 * (1.0 - alpha)) if t < fade_end else 0

        cx = self._sw // 2
        cy = int(self._sh * self._y_frac) + slide

        # Banner
        banner_rect = self._banner.get_rect(center=(cx, cy))
        self._banner.set_alpha(alpha_int)
        surface.blit(self._banner, banner_rect)
        self._banner.set_alpha(255)

        # Icon (on top of banner)
        icon = self._icons.get(self._icon_key, self._icons["gray"])
        icon_rect = icon.get_rect(centerx=cx, bottom=cy - 15)
        icon.set_alpha(alpha_int)
        surface.blit(icon, icon_rect)
        icon.set_alpha(255)

        # Text with drop shadow
        shadow = self._font.render(self._title, True, self._shadow_color)
        text = self._font.render(self._title, True, self._text_color)

        text_rect = text.get_rect(center=(cx, cy))
        shadow_rect = shadow.get_rect(center=(cx + 2, cy + 2))

        shadow.set_alpha(int(alpha_int * 0.5))
        surface.blit(shadow, shadow_rect)
        shadow.set_alpha(255)

        text.set_alpha(alpha_int)
        surface.blit(text, text_rect)
        text.set_alpha(255)
