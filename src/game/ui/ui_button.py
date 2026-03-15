"""
Reusable UI button built on the TextBTN asset sprites.

Renders a label (e.g. "Play", "Skip", "Start") centred on the
wooden button background. Supports normal, hovered, and pressed
visual states via the `_Pressed` variant of each asset.

Usage:
    btn = UIButton("Start", x=400, y=300)

    # In event loop:
    btn.handle_event(event)

    # In draw:
    btn.draw(surface)

    # Check if clicked:
    if btn.clicked:
        ...
"""

from __future__ import annotations

from typing import Callable, Optional

import pygame as pg

from v3x_zulfiqar_gideon.asset_manager import AssetManager


# Available button sizes and their asset paths
_BTN_ASSETS = {
    "big": (
        "assets/graphics/UI/PNG/TextBTN_Big.png",
        "assets/graphics/UI/PNG/TextBTN_Big_Pressed.png",
    ),
    "medium": (
        "assets/graphics/UI/PNG/TextBTN_Medium.png",
        "assets/graphics/UI/PNG/TextBTN_Medium_Pressed.png",
    ),
    "cancel": (
        "assets/graphics/UI/PNG/TextBTN_Cancel.png",
        "assets/graphics/UI/PNG/TextBTN_Cancel_Pressed.png",
    ),
    "new_start": (
        "assets/graphics/UI/PNG/TextBTN_New-Start.png",
        "assets/graphics/UI/PNG/TextBTN_New-Start_Pressed.png",
    ),
}

# Defaults
_FONT_PATH = "assets/Colorfiction_HandDrawnFonts/Colorfiction - Papyrus.otf"
_FONT_SIZE = 36
_TEXT_COLOR = (240, 230, 210)       # Light parchment text
_TEXT_COLOR_HOVER = (255, 245, 225)  # Slightly brighter on hover
_TEXT_COLOR_PRESSED = (200, 190, 170)  # Dimmer when pressed
_SHADOW_COLOR = (30, 20, 10)


class UIButton:
    """A clickable button rendered on a wooden UI sprite.

    Args:
        label:    Text to display on the button.
        x, y:     Centre position of the button on screen.
        size:     One of ``"big"``, ``"medium"``, ``"cancel"``, ``"new_start"``.
        scale:    Multiplier applied to the raw asset size (default 1.0).
        on_click: Optional callback invoked when the button is clicked.
        font_size: Override the default font size.
    """

    def __init__(
        self,
        label: str,
        x: int,
        y: int,
        *,
        size: str = "big",
        scale: float = 1.0,
        on_click: Optional[Callable[[], None]] = None,
        font_size: int = _FONT_SIZE,
    ) -> None:
        self.label = label
        self.on_click = on_click

        # Load normal & pressed textures
        if size not in _BTN_ASSETS:
            raise ValueError(
                f"Unknown button size '{size}'. Choose from: {list(_BTN_ASSETS)}"
            )
        normal_path, pressed_path = _BTN_ASSETS[size]
        raw_normal = AssetManager.get_texture(normal_path)
        raw_pressed = AssetManager.get_texture(pressed_path)

        # Scale
        w = int(raw_normal.get_width() * scale)
        h = int(raw_normal.get_height() * scale)
        self._img_normal = pg.transform.smoothscale(raw_normal, (w, h))
        self._img_pressed = pg.transform.smoothscale(raw_pressed, (w, h))

        # Build a subtle hover variant (slightly brighter normal)
        self._img_hover = self._img_normal.copy()
        bright = pg.Surface((w, h), pg.SRCALPHA)
        bright.fill((255, 255, 255, 25))
        self._img_hover.blit(bright, (0, 0))

        # Rect (centred at x, y)
        self.rect = self._img_normal.get_rect(center=(x, y))

        # Font
        self._font = AssetManager.get_font(_FONT_PATH, font_size)

        # Pre-render label surfaces
        self._label_normal = self._render_label(_TEXT_COLOR)
        self._label_hover = self._render_label(_TEXT_COLOR_HOVER)
        self._label_pressed = self._render_label(_TEXT_COLOR_PRESSED)

        # Interaction state
        self._hovered = False
        self._pressed = False
        self.clicked = False  # True for one frame after a click

    # ─────────────────────────────────────────────────────────────────────────

    def _render_label(self, color: tuple[int, int, int]) -> pg.Surface:
        """Render the label text with a subtle drop-shadow."""
        shadow = self._font.render(self.label, True, _SHADOW_COLOR)
        text = self._font.render(self.label, True, color)

        # Composite with 2px offset shadow
        w = text.get_width() + 2
        h = text.get_height() + 2
        surf = pg.Surface((w, h), pg.SRCALPHA)
        shadow.set_alpha(120)
        surf.blit(shadow, (2, 2))
        surf.blit(text, (0, 0))
        return surf

    # ─────────────────────────────────────────────────────────────────────────

    def set_label(self, label: str) -> None:
        """Change the button text at runtime."""
        self.label = label
        self._label_normal = self._render_label(_TEXT_COLOR)
        self._label_hover = self._render_label(_TEXT_COLOR_HOVER)
        self._label_pressed = self._render_label(_TEXT_COLOR_PRESSED)

    def set_position(self, x: int, y: int) -> None:
        """Move the button centre to a new position."""
        self.rect.center = (x, y)

    # ─────────────────────────────────────────────────────────────────────────

    def handle_event(self, event: pg.event.Event) -> bool:
        """Process a pygame event.  Returns ``True`` if the button was clicked."""
        self.clicked = False

        if event.type == pg.MOUSEMOTION:
            self._hovered = self.rect.collidepoint(event.pos)

        elif event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self._pressed = True

        elif event.type == pg.MOUSEBUTTONUP and event.button == 1:
            if self._pressed and self.rect.collidepoint(event.pos):
                self.clicked = True
                if self.on_click:
                    self.on_click()
            self._pressed = False

        return self.clicked

    # ─────────────────────────────────────────────────────────────────────────

    def draw(self, surface: pg.Surface) -> None:
        """Render the button onto *surface*."""
        # Pick the right sprite + label variant
        if self._pressed and self._hovered:
            img = self._img_pressed
            label = self._label_pressed
            # Slight downward offset to sell the press
            offset_y = 3
        elif self._hovered:
            img = self._img_hover
            label = self._label_hover
            offset_y = 0
        else:
            img = self._img_normal
            label = self._label_normal
            offset_y = 0

        surface.blit(img, self.rect)

        # Centre label on button
        lx = self.rect.centerx - label.get_width() // 2
        ly = self.rect.centery - label.get_height() // 2 + offset_y
        surface.blit(label, (lx, ly))
