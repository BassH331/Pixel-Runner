"""
EndingState — three-branch ending cutscene for Pixel-Runner.

Drives a 7-phase sequence (fade_in → title → lines → outro → credits →
fade_out → return to main menu) derived from storyline_config["endings"].

All narrative text comes from JSON.  SPACE / ENTER skips the current
phase (not the whole ending) so the player can still read at their own pace.
"""

from __future__ import annotations

import math
from enum import Enum, auto
from typing import Optional

import pygame as pg

from v3x_zulfiqar_gideon import State, AssetManager


class EndingType(Enum):
    DARK = auto()
    LIGHT = auto()
    AMBIGUOUS = auto()


# ── Phase durations (seconds) ───────────────────────────────────────────────
_FADE_IN_DUR  = 1.5
_TITLE_DUR    = 3.0
_LINE_SHOW    = 3.0   # each narrative line is visible for this long
_LINE_FADE    = 0.8   # fade-in duration per line
_OUTRO_DUR    = 4.0
_CREDITS_DUR  = 5.0
_FADE_OUT_DUR = 2.0

# ── Colours ──────────────────────────────────────────────────────────────────
_WHITE         = (255, 255, 255)
_LINE_COLOUR   = (200, 200, 200)
_OUTRO_COLOUR  = (160, 140, 130)
_CREDITS_COLOUR= (120, 120, 120)

_GAME_TITLE    = "PIXEL RUNNER"
_ENGINE_CREDIT = "Made with V3X Engine"


class EndingState(State):
    """Cinematic ending state with 7 sequential phases.

    Args:
        ending_type:      Which ending branch (DARK / LIGHT / AMBIGUOUS).
        ending_data:      Dict loaded from ``storyline_config["endings"][key]``.
        corruption_value: Final corruption percentage (0–100) for credits display.
    """

    def __init__(
        self,
        manager,
        ending_type: EndingType,
        ending_data: dict,
        corruption_value: float,
    ) -> None:
        super().__init__(manager)

        self._ending_type    = ending_type
        self._ending_data    = ending_data
        self._corruption     = corruption_value

        # ── Pull content from data ────────────────────────────────────────────
        self._title: str       = ending_data.get("title", "THE END")
        self._lines: list[str] = list(ending_data.get("lines", []))

        # Determine outro speaker + text
        if "moon_knight_outro" in ending_data:
            self._outro_speaker = "MOON KNIGHT"
            self._outro_text    = ending_data["moon_knight_outro"]
        else:
            self._outro_speaker = "ANDRAS"
            self._outro_text    = ending_data.get("andras_outro", "")

        # Background tint colour (very dark)
        tint = ending_data.get("background_tint", [10, 5, 15])
        self._bg_colour: tuple = (int(tint[0]), int(tint[1]), int(tint[2]))

        # ── State machine ─────────────────────────────────────────────────────
        self._phase: str        = "fade_in"
        self._phase_timer: float = _FADE_IN_DUR

        # For "lines" phase
        self._line_index: int   = 0
        self._line_alpha: float = 0.0   # 0–255 fade-in per line

        # Global overlay alpha (0 = opaque black, 255 = fully visible)
        self._screen_alpha: float = 0.0  # used in fade_in / fade_out

        # Fonts — initialised in on_enter so the display is guaranteed up
        self._font_title:   Optional[pg.font.Font] = None
        self._font_lines:   Optional[pg.font.Font] = None
        self._font_outro:   Optional[pg.font.Font] = None
        self._font_credits: Optional[pg.font.Font] = None

        # Screen dimensions (set in on_enter)
        self._w: int = 0
        self._h: int = 0

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def on_enter(self) -> None:
        display = pg.display.get_surface()
        self._w = display.get_width()  if display else 800
        self._h = display.get_height() if display else 600

        try:
            self._font_title   = AssetManager.get_font("assets/font/Abaddon Bold.ttf", 30)
            self._font_lines   = AssetManager.get_font("assets/font/Abaddon Bold.ttf", 17)
            self._font_outro   = AssetManager.get_font("assets/font/Abaddon Bold.ttf", 14)
            self._font_credits = AssetManager.get_font("assets/font/Abaddon Bold.ttf", 13)
        except Exception:
            self._font_title   = pg.font.SysFont("Arial", 30, bold=True)
            self._font_lines   = pg.font.SysFont("Arial", 17)
            self._font_outro   = pg.font.SysFont("Arial", 14)
            self._font_credits = pg.font.SysFont("Arial", 13)

        # Reset phase
        self._phase       = "fade_in"
        self._phase_timer = _FADE_IN_DUR
        self._screen_alpha = 0.0
        self._line_index   = 0
        self._line_alpha   = 0.0

    def on_exit(self) -> None:
        pass

    # ── Input ─────────────────────────────────────────────────────────────────

    def handle_event(self, event: pg.event.Event) -> None:
        """SPACE or ENTER skips the *current* phase only."""
        skip = (
            (event.type == pg.KEYDOWN and event.key in (pg.K_SPACE, pg.K_RETURN))
            or (event.type == pg.JOYBUTTONDOWN and event.button in (0, 1, 6, 7))
        )
        if skip:
            self._advance_phase()

    # ── Update ────────────────────────────────────────────────────────────────

    def update(self, dt: float) -> None:
        dt_s = dt / 1000.0 if dt > 0.5 else dt

        if self._phase == "fade_in":
            self._screen_alpha = min(255.0, self._screen_alpha + (255.0 / _FADE_IN_DUR) * dt_s)
            self._phase_timer -= dt_s
            if self._phase_timer <= 0:
                self._advance_phase()

        elif self._phase == "title":
            self._phase_timer -= dt_s
            if self._phase_timer <= 0:
                self._advance_phase()

        elif self._phase == "lines":
            # Fade-in the current line
            if self._line_alpha < 255.0:
                self._line_alpha = min(255.0, self._line_alpha + (255.0 / _LINE_FADE) * dt_s)
            self._phase_timer -= dt_s
            if self._phase_timer <= 0:
                self._next_line()

        elif self._phase == "outro":
            self._phase_timer -= dt_s
            if self._phase_timer <= 0:
                self._advance_phase()

        elif self._phase == "credits":
            self._phase_timer -= dt_s
            if self._phase_timer <= 0:
                self._advance_phase()

        elif self._phase == "fade_out":
            self._screen_alpha = max(0.0, self._screen_alpha - (255.0 / _FADE_OUT_DUR) * dt_s)
            self._phase_timer -= dt_s
            if self._phase_timer <= 0:
                self._finish()

    # ── Draw ──────────────────────────────────────────────────────────────────

    def draw(self, surface: pg.Surface) -> None:
        # 1. Very dark background tint
        surface.fill(self._bg_colour)

        # 2. Semi-transparent black depth layer
        depth = pg.Surface((self._w, self._h), pg.SRCALPHA)
        depth.fill((0, 0, 0, 180))
        surface.blit(depth, (0, 0))

        # 3. Phase content
        if self._phase == "fade_in":
            pass  # nothing to show yet — fade overlay handles it below

        elif self._phase == "title":
            self._draw_centred_text(
                surface, self._title, self._font_title, _WHITE,
                self._h // 2 - 20, alpha=255,
            )

        elif self._phase == "lines":
            if self._line_index < len(self._lines):
                self._draw_centred_text(
                    surface,
                    self._lines[self._line_index],
                    self._font_lines,
                    _LINE_COLOUR,
                    self._h // 2,
                    alpha=int(self._line_alpha),
                )

        elif self._phase == "outro":
            if self._outro_text:
                speaker_line = f"{self._outro_speaker}:  {self._outro_text}"
                self._draw_centred_text(
                    surface, speaker_line, self._font_outro, _OUTRO_COLOUR,
                    self._h // 2, alpha=255,
                )

        elif self._phase == "credits":
            self._draw_credits(surface)

        # 4. Fade-in / fade-out overlay (black → transparent on enter; transparent → black on exit)
        if self._phase == "fade_in":
            overlay_alpha = int(255 - self._screen_alpha)
        elif self._phase == "fade_out":
            overlay_alpha = int(255 - self._screen_alpha)
        else:
            overlay_alpha = 0

        if overlay_alpha > 0:
            fade_surf = pg.Surface((self._w, self._h), pg.SRCALPHA)
            fade_surf.fill((0, 0, 0, min(255, overlay_alpha)))
            surface.blit(fade_surf, (0, 0))

    # ── Private helpers ───────────────────────────────────────────────────────

    def _draw_centred_text(
        self,
        surface: pg.Surface,
        text: str,
        font: Optional[pg.font.Font],
        colour: tuple,
        y: int,
        alpha: int = 255,
    ) -> None:
        if font is None:
            return
        rendered = font.render(text, True, colour)
        if alpha < 255:
            rendered.set_alpha(alpha)
        rect = rendered.get_rect(centerx=self._w // 2, centery=y)
        surface.blit(rendered, rect)

    def _draw_credits(self, surface: pg.Surface) -> None:
        if self._font_credits is None:
            return
        lines = [
            _GAME_TITLE,
            "",
            _ENGINE_CREDIT,
            "",
            f"Final Corruption: {self._corruption:.0f}%",
        ]
        line_h = self._font_credits.get_height() + 6
        total_h = len(lines) * line_h
        start_y = (self._h - total_h) // 2
        for i, ln in enumerate(lines):
            if not ln:
                continue
            rendered = self._font_credits.render(ln, True, _CREDITS_COLOUR)
            rect = rendered.get_rect(centerx=self._w // 2, top=start_y + i * line_h)
            surface.blit(rendered, rect)

    def _next_line(self) -> None:
        """Advance to the next narrative line or move to outro phase."""
        self._line_index += 1
        if self._line_index >= len(self._lines):
            self._advance_phase()
        else:
            self._phase_timer = _LINE_SHOW
            self._line_alpha  = 0.0

    def _advance_phase(self) -> None:
        """Move to the next phase in sequence."""
        order = ["fade_in", "title", "lines", "outro", "credits", "fade_out"]
        try:
            idx = order.index(self._phase)
        except ValueError:
            return
        next_idx = idx + 1
        if next_idx >= len(order):
            self._finish()
            return

        next_phase = order[next_idx]
        self._phase = next_phase

        # Set timers / state for the incoming phase
        if next_phase == "fade_in":
            self._phase_timer = _FADE_IN_DUR
            self._screen_alpha = 0.0
        elif next_phase == "title":
            self._phase_timer = _TITLE_DUR
        elif next_phase == "lines":
            self._line_index  = 0
            self._line_alpha  = 0.0
            self._phase_timer = _LINE_SHOW
            if not self._lines:
                # Skip straight to outro if no lines
                self._advance_phase()
        elif next_phase == "outro":
            self._phase_timer = _OUTRO_DUR
            if not self._outro_text:
                self._advance_phase()
        elif next_phase == "credits":
            self._phase_timer = _CREDITS_DUR
        elif next_phase == "fade_out":
            self._phase_timer = _FADE_OUT_DUR
            self._screen_alpha = 255.0

    def _finish(self) -> None:
        """Tear down entire stack and show main menu."""
        from src.game.states.main_menu_state import MainMenuState
        self.manager.set(MainMenuState(self.manager))
