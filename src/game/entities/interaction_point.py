"""
Interaction point entity for proximity-based objective triggers.

A world-positioned invisible marker that scrolls with the background.
When the player is within proximity, a "Talk [X / ENTER]" prompt
floats above the point. Pressing the interact button opens the
objective parchment overlay.
"""

from __future__ import annotations

from typing import Optional

import pygame as pg

from v3x_zulfiqar_gideon.asset_manager import AssetManager


class InteractionPoint(pg.sprite.Sprite):
    """An invisible world marker that triggers dialogue on proximity.

    Args:
        x: Initial world X position (scrolls with background).
        y: Screen Y position (fixed vertically).
        text: Objective/dialogue text shown in the parchment overlay.
        title: Header text for the parchment overlay.
        proximity_radius: Pixel distance to trigger the talk prompt.
    """

    _FONT_PATH = "assets/Colorfiction_HandDrawnFonts/Colorfiction - Papyrus.otf"
    _FONT_SIZE = 30
    _PROMPT_COLOR = (255, 255, 255)
    _PROMPT_BG_COLOR = (30, 30, 30, 200)
    _PROMPT_PADDING_X = 16
    _PROMPT_PADDING_Y = 8
    _PROMPT_OFFSET_Y = -70  # Above the interaction position
    _PROMPT_BORDER_RADIUS = 8

    def __init__(
        self,
        x: int,
        y: int,
        text: str,
        title: str = "Objective",
        proximity_radius: int = 150,
    ) -> None:
        super().__init__()

        self.text = text
        self.title = title
        self.proximity_radius = proximity_radius
        self._interacted: bool = False  # True after player has interacted

        # Invisible sprite — 1×1 pixel, fully transparent
        self.image = pg.Surface((1, 1), pg.SRCALPHA)
        self.image.fill((0, 0, 0, 0))
        self.rect = pg.Rect(x, y, 1, 1)

        # Build the talk prompt surface (cached for performance)
        self._font = AssetManager.get_font(self._FONT_PATH, self._FONT_SIZE)
        self._prompt_surface = self._build_prompt()
        self._in_range: bool = False

    def _build_prompt(self) -> pg.Surface:
        """Create the "Talk [X / ENTER]" prompt surface with background."""
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
        # Subtle border
        pg.draw.rect(
            bg,
            (200, 200, 200, 120),
            (0, 0, w, h),
            width=2,
            border_radius=self._PROMPT_BORDER_RADIUS,
        )
        bg.blit(text_surf, (self._PROMPT_PADDING_X, self._PROMPT_PADDING_Y))
        return bg

    # ─────────────────────────────────────────────────────────────────────────

    @property
    def can_interact(self) -> bool:
        """Whether the player is close enough to interact."""
        return self._in_range and not self._interacted

    @property
    def has_been_used(self) -> bool:
        """Whether this point has already been interacted with."""
        return self._interacted

    def mark_interacted(self) -> None:
        """Mark this point as used (won't show the prompt again)."""
        self._interacted = True

    def reset(self) -> None:
        """Allow re-interaction (e.g., for repeatable dialogues)."""
        self._interacted = False

    # ─────────────────────────────────────────────────────────────────────────

    def check_proximity(self, player_rect: pg.Rect) -> bool:
        """Update proximity state based on player position.

        Args:
            player_rect: The player's bounding rect.

        Returns:
            True if player is within interaction range.
        """
        dx = abs(self.rect.centerx - player_rect.centerx)
        dy = abs(self.rect.centery - player_rect.centery)
        distance = (dx * dx + dy * dy) ** 0.5
        self._in_range = distance <= self.proximity_radius
        return self._in_range

    def update(
        self,
        dt: Optional[float] = None,
        scroll_speed: int = 0,
    ) -> None:
        """Scroll with the world.

        Args:
            dt: Delta time (unused, kept for interface compatibility).
            scroll_speed: Horizontal scroll delta from background parallax.
        """
        self.rect.x -= scroll_speed

    def draw(self, surface: pg.Surface) -> None:
        """Draw the talk prompt if player is in range.

        Args:
            surface: Target rendering surface.
        """
        if not self.can_interact:
            return

        # Pulsing alpha for visibility
        ticks = pg.time.get_ticks()
        alpha = 180 + int(75 * abs(((ticks // 8) % 200 - 100) / 100))
        self._prompt_surface.set_alpha(alpha)

        # Position prompt centered above the interaction point
        px = self.rect.centerx - self._prompt_surface.get_width() // 2
        py = self.rect.centery + self._PROMPT_OFFSET_Y
        surface.blit(self._prompt_surface, (px, py))
