"""
RelicRevealState — a lightweight overlay State that displays relic lore via
a typewriter cutscene.

Pushed onto the state stack when a relic is collected; pops itself when the
player presses any key or clicks.  Gameplay beneath is paused while active
(standard push/pop behaviour of the state stack).
"""

from __future__ import annotations

import math
import pygame as pg

from v3x_zulfiqar_gideon import State
from src.game.ui.animated_dialogue_renderer import AnimatedDialogueRenderer

# Panel dimensions (centred on screen).
_PANEL_W = 600
_PANEL_H = 300

# Colours
_OVERLAY_COLOUR = (0, 0, 0, 180)
_PANEL_BG = (15, 5, 25)
_PANEL_BORDER = (80, 40, 100)
_NAME_COLOUR = (220, 200, 255)
_SUBTITLE_COLOUR = (140, 110, 160)
_LORE_COLOUR = (200, 185, 220)
_PROMPT_COLOUR = (120, 100, 140)

# Blink rate for "[ Press any key ]" prompt.
_BLINK_HZ = 1.0


class RelicRevealState(State):
    """Overlay state that shows relic name, subtitle, and typewriter lore text.

    Args:
        manager:    ``StateManager`` instance (passed by the push mechanism).
                    May be ``None`` when constructed before push; the manager is
                    set by ``StateManager.push`` via the standard ``State`` contract.
        relic_id:   String identifier (used only for debug logging).
        relic_data: Dict with keys ``name``, ``subtitle``, and ``lore`` sourced
                    from ``storyline_config.json``.
        on_dismiss: Optional callback invoked when the player dismisses the screen.
    """

    is_overlay: bool = True

    def __init__(self, manager, relic_id: str, relic_data: dict, on_dismiss=None) -> None:
        super().__init__(manager)
        self._relic_id = relic_id
        self._relic_data = relic_data
        self._on_dismiss = on_dismiss
        self.is_active: bool = True

        self._renderer = AnimatedDialogueRenderer(typing_speed=40.0, max_scale=1.4)

        # Fonts — created lazily in on_enter to ensure pygame display is up.
        self._font_name: pg.font.Font | None = None
        self._font_subtitle: pg.font.Font | None = None
        self._font_lore: pg.font.Font | None = None
        self._font_prompt: pg.font.Font | None = None

        # Semi-transparent overlay surface (created once in on_enter).
        self._overlay: pg.Surface | None = None

        # Elapsed time used for blink animation.
        self._elapsed: float = 0.0

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def on_enter(self) -> None:
        """Start typewriter animation and prepare surfaces."""
        self.is_active = True
        display = pg.display.get_surface()
        sw = display.get_width() if display else 800
        sh = display.get_height() if display else 600

        # Full-screen semi-transparent overlay.
        self._overlay = pg.Surface((sw, sh), pg.SRCALPHA)
        self._overlay.fill(_OVERLAY_COLOUR)

        # Fonts.
        self._font_name = pg.font.SysFont("Arial", 22, bold=True)
        self._font_subtitle = pg.font.SysFont("Arial", 16)
        self._font_lore = pg.font.SysFont("Arial", 15)
        self._font_prompt = pg.font.SysFont("Arial", 13)

        lore = self._relic_data.get("lore", "")
        self._renderer.set_text(lore)
        self._elapsed = 0.0

    def on_exit(self) -> None:
        """Mark overlay inactive upon exit."""
        self.is_active = False

    # ── Update ────────────────────────────────────────────────────────────────

    def update(self, dt: float) -> None:
        dt_sec = dt / 1000.0 if dt > 1.0 else dt
        self._elapsed += dt_sec
        self._renderer.update(dt_sec)

    # ── Draw ──────────────────────────────────────────────────────────────────

    def draw(self, surface: pg.Surface) -> None:
        sw, sh = surface.get_size()

        # 1. Dark semi-transparent full-screen overlay.
        if self._overlay is None or self._overlay.get_size() != (sw, sh):
            self._overlay = pg.Surface((sw, sh), pg.SRCALPHA)
            self._overlay.fill(_OVERLAY_COLOUR)
        surface.blit(self._overlay, (0, 0))

        # 2. Centre panel.
        px = (sw - _PANEL_W) // 2
        py = (sh - _PANEL_H) // 2
        panel_rect = pg.Rect(px, py, _PANEL_W, _PANEL_H)
        pg.draw.rect(surface, _PANEL_BG, panel_rect, border_radius=6)
        pg.draw.rect(surface, _PANEL_BORDER, panel_rect, width=1, border_radius=6)

        padding = 20

        # 3. Relic name (top section).
        if self._font_name:
            name = self._relic_data.get("name", self._relic_id)
            name_surf = self._font_name.render(name, True, _NAME_COLOUR)
            name_rect = name_surf.get_rect(centerx=panel_rect.centerx,
                                           top=panel_rect.top + padding)
            surface.blit(name_surf, name_rect)
            text_top = name_rect.bottom + 4
        else:
            text_top = panel_rect.top + padding

        # 4. Subtitle.
        if self._font_subtitle:
            subtitle = self._relic_data.get("subtitle", "")
            sub_surf = self._font_subtitle.render(subtitle, True, _SUBTITLE_COLOUR)
            sub_rect = sub_surf.get_rect(centerx=panel_rect.centerx, top=text_top)
            surface.blit(sub_surf, sub_rect)
            lore_top = sub_rect.bottom + 14
        else:
            lore_top = text_top + 20

        # 5. Typewriter lore text (middle section).
        if self._font_lore:
            prompt_h = 30  # reserve space at bottom for prompt
            lore_rect = pg.Rect(
                panel_rect.left + padding,
                lore_top,
                _PANEL_W - padding * 2,
                panel_rect.bottom - lore_top - prompt_h,
            )
            self._renderer.render(
                surface,
                self._font_lore,
                lore_rect,
                color=_LORE_COLOUR,
                shadow_color=(0, 0, 0),
                align="left",
                line_spacing=5,
            )

        # 6. Blinking prompt at the bottom (Keyboard & Gamepad friendly).
        if self._font_prompt:
            blink_visible = math.sin(self._elapsed * _BLINK_HZ * math.pi * 2) >= 0
            if blink_visible:
                prompt_surf = self._font_prompt.render(
                    "[ Press any key, click, or controller button to continue ]",
                    True,
                    _PROMPT_COLOUR
                )
                prompt_rect = prompt_surf.get_rect(
                    centerx=panel_rect.centerx,
                    bottom=panel_rect.bottom - 10,
                )
                surface.blit(prompt_surf, prompt_rect)

    # ── Input ─────────────────────────────────────────────────────────────────

    def dismiss(self) -> None:
        """Dismiss the relic reveal cutscene and invoke any callbacks."""
        self.is_active = False
        if callable(self._on_dismiss):
            try:
                self._on_dismiss()
            except Exception as e:
                print(f"[RelicRevealState] on_dismiss error: {e}")
        if (
            self.manager is not None
            and hasattr(self.manager, "stack")
            and self.manager.stack
            and self.manager.stack[-1] is self
        ):
            self.manager.pop()

    def handle_event(self, event: pg.event.Event) -> bool:
        """Any key, mouse click, or controller button dismisses the relic reveal panel."""
        if not self.is_active:
            return False

        if event.type in (pg.KEYDOWN, pg.MOUSEBUTTONDOWN, pg.JOYBUTTONDOWN):
            self.dismiss()
            return True
        return False
