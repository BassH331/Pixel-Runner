"""
Objective & Atmospheric Dialogue Overlay System

Provides character-themed elemental intro animations (e.g. Dark Fire & Settling Smoke for Necromancer,
Ice Storm for frost characters), followed by an atmospheric typewriter text reveal.
"""

from enum import Enum, auto
import os
from typing import Optional, List, Tuple, Any
import pygame as pg

from v3x_zulfiqar_gideon import ParchmentDisplay, AssetManager


class FXState(Enum):
    FLAME_BURST = auto()
    SMOKE_SETTLE = auto()
    TYPEWRITER = auto()
    COMPLETE = auto()


class ObjectiveDisplay(ParchmentDisplay):
    """
    Enhanced Dialogue & Objective display overlay.
    Supports character-themed elemental intro sequences (Dark Fire, Smoke, Ice)
    and typewriter text reveals.
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._fx_state: FXState = FXState.COMPLETE
        self._current_theme: str = "necromancer_dark_fire"

        # Animation frame buffers
        self._flame_frames: List[pg.Surface] = []
        self._smoke_frames: List[pg.Surface] = []
        
        self._flame_idx: float = 0.0
        self._smoke_idx: float = 0.0
        self._char_count: float = 0.0
        self._typing_speed: float = 45.0  # Chars per second

        self._full_raw_text: str = ""
        self._loaded_theme: Optional[str] = None
        self._load_effects()

    def _load_effects(self) -> None:
        """Pre-load and scale elemental FX animation frames."""
        flame_dir = "assets/graphics/Fire Effect 2/Explosion2_frames"
        if os.path.exists(flame_dir):
            raw_flames = AssetManager.get_animation_frames(flame_dir)
            if raw_flames:
                # Scale flames to fit nicely over the parchment text area
                fw, fh = self._text_max_w, int(self._text_max_h * 0.9)
                self._flame_frames = [
                    pg.transform.smoothscale(f, (fw, fh)) for f in raw_flames
                ]

        smoke_dir = "assets/graphics/Pixel Explosion Effects Pack 01 v1_1/DustExplosion/Frames"
        if os.path.exists(smoke_dir):
            raw_smoke = AssetManager.get_animation_frames(smoke_dir)
            if raw_smoke:
                sw, sh = int(self._text_max_w * 1.1), int(self._text_max_h * 1.1)
                self._smoke_frames = [
                    pg.transform.smoothscale(f, (sw, sh)) for f in raw_smoke
                ]

    def show(self, text: str, title: str = "Objective", theme: str = "necromancer_dark_fire") -> None:
        """Show dialogue overlay with thematic intro animation."""
        super().show(text, title)
        self._full_raw_text = text
        self._current_theme = theme

        if theme == "necromancer_dark_fire" and self._flame_frames:
            self._fx_state = FXState.FLAME_BURST
        else:
            self._fx_state = FXState.TYPEWRITER

        self._flame_idx = 0.0
        self._smoke_idx = 0.0
        self._char_count = 0.0

    def update(self, dt: float) -> None:
        """Update animation state machine and typewriter reveal."""
        if not self._active:
            return

        # dt is in seconds or ms — normalize to seconds
        dt_sec = dt if dt < 1.0 else dt / 1000.0

        if self._fx_state == FXState.FLAME_BURST:
            # Advance flame frames at ~18 fps
            self._flame_idx += 18.0 * dt_sec
            if int(self._flame_idx) >= len(self._flame_frames):
                if self._smoke_frames:
                    self._fx_state = FXState.SMOKE_SETTLE
                    self._smoke_idx = 0.0
                else:
                    self._fx_state = FXState.TYPEWRITER
                    self._char_count = 0.0

        elif self._fx_state == FXState.SMOKE_SETTLE:
            # Advance smoke frames at ~12 fps
            self._smoke_idx += 12.0 * dt_sec
            if int(self._smoke_idx) >= len(self._smoke_frames):
                self._fx_state = FXState.TYPEWRITER
                self._char_count = 0.0

        elif self._fx_state == FXState.TYPEWRITER:
            # Typewriter character reveal
            self._char_count += self._typing_speed * dt_sec
            if self._char_count >= len(self._full_raw_text):
                self._char_count = float(len(self._full_raw_text))
                self._fx_state = FXState.COMPLETE

    def handle_event(self, event: pg.event.Event) -> bool:
        """
        Handle input event.
        Returns True if the dialogue should be DISMISSED (closed).
        Returns False if the input skipped/fast-forwarded the animation to full text.
        """
        if not self._active:
            return False

        is_trigger = (
            (event.type == pg.KEYDOWN and event.key in (pg.K_SPACE, pg.K_RETURN, pg.K_x))
            or (event.type == pg.JOYBUTTONDOWN and event.button in (0, 6))
        )

        if not is_trigger:
            return False

        if self._fx_state != FXState.COMPLETE:
            # Fast-forward / skip intro FX & typewriter directly to complete
            self._fx_state = FXState.COMPLETE
            self._char_count = float(len(self._full_raw_text))
            return False
        else:
            # Already complete -> dismiss dialogue
            self.dismiss()
            return True

    def draw(self, surface: Any) -> None:
        """Render background, elemental intro FX, typewriter text, and prompt."""
        if not self._active:
            return

        # 1. Base parchment background & stone border
        surface.blit(self._backdrop, (0, 0))
        surface.blit(self._stone, self._stone_rect)
        surface.blit(self._parchment, self._parch_rect)

        # 2. Title rendering
        title_color = self._cfg.get("title_color", (200, 40, 40) if "necromancer" in self._current_theme else (180, 140, 60))
        title_surf = self._title_font.render(self._title, True, title_color)
        title_x = self._parch_rect.centerx - title_surf.get_width() // 2
        title_y = self._text_y
        surface.blit(title_surf, (title_x, title_y))

        content_y_start = title_y + title_surf.get_height() + self._line_spacing * 2

        # 3. State-based rendering
        if self._fx_state == FXState.FLAME_BURST:
            # Draw flame animation over the text region
            if self._flame_frames:
                frame_i = min(int(self._flame_idx), len(self._flame_frames) - 1)
                flame_surf = self._flame_frames[frame_i]
                fx_x = self._parch_rect.centerx - flame_surf.get_width() // 2
                fx_y = content_y_start
                surface.blit(flame_surf, (fx_x, fx_y), special_flags=pg.BLEND_ADD)

        elif self._fx_state == FXState.SMOKE_SETTLE:
            # Draw partial text starting to show through smoke
            visible_len = max(1, int(len(self._full_raw_text) * 0.2))
            partial_text = self._full_raw_text[:visible_len]
            lines = self._wrap_text(partial_text, self._font, self._text_max_w, self._cfg["text_color"])
            y = content_y_start
            for line_surf in lines:
                if y + line_surf.get_height() > self._text_y + self._text_max_h:
                    break
                lx = self._text_x + (self._text_max_w - line_surf.get_width()) // 2
                line_surf.set_alpha(100)
                surface.blit(line_surf, (lx, y))
                y += line_surf.get_height() + self._line_spacing

            # Draw settling smoke overlay
            if self._smoke_frames:
                frame_i = min(int(self._smoke_idx), len(self._smoke_frames) - 1)
                smoke_surf = self._smoke_frames[frame_i]
                fx_x = self._parch_rect.centerx - smoke_surf.get_width() // 2
                fx_y = content_y_start - 10
                surface.blit(smoke_surf, (fx_x, fx_y))

        elif self._fx_state in (FXState.TYPEWRITER, FXState.COMPLETE):
            # Render typewriter or full text
            curr_len = int(self._char_count) if self._fx_state == FXState.TYPEWRITER else len(self._full_raw_text)
            displayed_text = self._full_raw_text[:curr_len]
            lines = self._wrap_text(displayed_text, self._font, self._text_max_w, self._cfg["text_color"])

            y = content_y_start
            for line_surf in lines:
                if y + line_surf.get_height() > self._text_y + self._text_max_h:
                    break
                lx = self._text_x + (self._text_max_w - line_surf.get_width()) // 2
                surface.blit(line_surf, (lx, y))
                y += line_surf.get_height() + self._line_spacing

            # Prompt only appears in COMPLETE state
            if self._fx_state == FXState.COMPLETE and self._prompt_surface:
                px = self._parch_rect.centerx - self._prompt_surface.get_width() // 2
                py = self._parch_rect.bottom - int(self._parch_rect.height * self._pad_y_bottom_frac * 0.6)
                alpha = 160 + int(95 * abs(((pg.time.get_ticks() // 8) % 200 - 100) / 100))
                self._prompt_surface.set_alpha(alpha)
                surface.blit(self._prompt_surface, (px, py))
