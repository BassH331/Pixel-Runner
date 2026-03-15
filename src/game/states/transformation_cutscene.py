"""
Transformation cutscene state.

Plays a cinematic sequence: fade-in → transform (white/red flash) →
attack left → attack right → red flashes + revert to human.

Can be used as a transitional state (StoryState → Cutscene → GameState)
or pushed mid-game (push on stack, pops itself when done).
"""

from __future__ import annotations

import math
from enum import IntEnum, auto
from typing import Callable, Optional

import pygame as pg

from v3x_zulfiqar_gideon.asset_manager import AssetManager
from v3x_zulfiqar_gideon.state_machine import State
from v3x_zulfiqar_gideon.ui import NotificationBanner


class _Phase(IntEnum):
    """Sequential cutscene phases."""

    FADE_IN = 0
    TRANSFORM = auto()
    ATTACK_LEFT = auto()
    ATTACK_RIGHT = auto()
    REVERT = auto()
    LEVEL_INTRO = auto()
    DONE = auto()


def _ease_in_out(t: float) -> float:
    """Smooth ease-in-out (sine curve). t in [0,1] → [0,1]."""
    return 0.5 - 0.5 * math.cos(math.pi * t)


class TransformationCutscene(State):
    """Full-screen cinematic transformation sequence.

    Args:
        manager:            StateManager instance.
        next_state_factory: Callable that returns the next State to transition to
                            when the cutscene ends.  Pass ``None`` when using
                            push/pop mid-game.
        on_complete:        Optional callback fired when the cutscene finishes
                            (e.g. ``lambda: manager.pop()`` for mid-game use).
    """

    # ── Timing ────────────────────────────────────────────────────────────────
    _FADE_IN_DURATION = 1.5          # seconds – slower, more dramatic
    _FRAME_DURATION = 0.07           # seconds per sprite frame (~14 fps, smoother)
    _CROSSFADE_DURATION = 0.35       # seconds to blend between phases
    _FLASH_HOLD = 0.08              # seconds at peak white/red
    _FLASH_FADE = 0.25              # seconds to fade flash out
    _RED_FLASH_COUNT = 4             # number of red flashes during revert
    _RED_FLASH_CYCLE = 0.22          # total duration of one red flash cycle
    _POST_REVERT_PAUSE = 0.6        # brief hold after revert before exit

    # ── Level intro timing ────────────────────────────────────────────────────
    _INTRO_FADE_IN = 0.8             # seconds to fade the banner in
    _INTRO_HOLD = 2.0                # seconds to hold the banner on screen
    _INTRO_FADE_OUT = 0.8            # seconds to fade the banner out

    # ── Sprite scaling ────────────────────────────────────────────────────────
    _SPRITE_SCALE = 3.5

    # ── Asset paths ───────────────────────────────────────────────────────────
    _TRANSFORM_DIR = "assets/shadow_warrior/transform"
    _ATK_LEFT_DIR = "assets/shadow_warrior/e_3_atk"
    _ATK_RIGHT_DIR = "assets/shadow_warrior/e_sp_atk"
    _REVERT_DIR = "assets/shadow_warrior/back2human"

    def __init__(
        self,
        manager,
        next_state_factory: Optional[Callable] = None,
        on_complete: Optional[Callable] = None,
        level_title: str = "The Blight Begins",
        notification: str = "gray",
    ) -> None:
        super().__init__(manager)
        self._next_state_factory = next_state_factory
        self._on_complete = on_complete
        self._level_title = level_title
        self._notification_type = notification

        info = pg.display.Info()
        self._sw = info.current_w
        self._sh = info.current_h

        # ── Load & scale frame sets ──────────────────────────────────────────
        self._frames_transform = self._load_scaled(self._TRANSFORM_DIR)
        self._frames_atk_left = self._load_scaled(self._ATK_LEFT_DIR)
        self._frames_atk_right = self._load_scaled(self._ATK_RIGHT_DIR, flip=True)
        self._frames_revert = self._load_scaled(self._REVERT_DIR)

        # ── Level intro banner (shared component) ────────────────────────────
        self._banner = NotificationBanner(scale=0.6, icon_scale=0.6)

        # ── Persistent overlay surfaces ──────────────────────────────────────
        self._overlay = pg.Surface((self._sw, self._sh), pg.SRCALPHA)

        # ── Runtime state (all reset in on_enter) ────────────────────────────
        self._reset_state()

    def _reset_state(self) -> None:
        self._phase = _Phase.FADE_IN
        self._phase_timer = 0.0        # time spent in current phase
        self._frame_idx = 0
        self._frame_timer = 0.0

        # Cross-fade between phases
        self._crossfading = False
        self._crossfade_timer = 0.0
        self._prev_frame: Optional[pg.Surface] = None

        # Flash VFX
        self._flash_alpha = 0.0
        self._flash_color: tuple[int, int, int] = (255, 255, 255)
        self._transform_flash_triggered = False
        self._transform_red_triggered = False

        # Revert red flashes
        self._red_flashes_done = 0
        self._red_flash_timer = 0.0
        self._post_pause_timer = 0.0

    # ─── Asset helpers ───────────────────────────────────────────────────────

    def _load_scaled(
        self, directory: str, flip: bool = False
    ) -> list[pg.Surface]:
        """Load animation frames, scale them up, optionally flip horizontally."""
        raw_frames = AssetManager.get_animation_frames(directory)
        scaled: list[pg.Surface] = []
        for f in raw_frames:
            w = int(f.get_width() * self._SPRITE_SCALE)
            h = int(f.get_height() * self._SPRITE_SCALE)
            s = pg.transform.smoothscale(f, (w, h))
            if flip:
                s = pg.transform.flip(s, True, False)
            scaled.append(s)
        return scaled

    # ─── State interface ─────────────────────────────────────────────────────

    def on_enter(self) -> None:
        self._reset_state()

    def handle_event(self, event: pg.event.Event) -> None:
        if event.type == pg.KEYDOWN and event.key in (pg.K_SPACE, pg.K_RETURN):
            self._finish()

    # ─── Update ──────────────────────────────────────────────────────────────

    def update(self, dt: float) -> None:
        dt_sec = dt / 1000.0
        self._phase_timer += dt_sec

        # Decay any active flash overlay smoothly
        if self._flash_alpha > 0:
            self._flash_alpha = max(0.0, self._flash_alpha - dt_sec * (255 / self._FLASH_FADE))

        # Advance cross-fade
        if self._crossfading:
            self._crossfade_timer += dt_sec
            if self._crossfade_timer >= self._CROSSFADE_DURATION:
                self._crossfading = False
                self._prev_frame = None

        if self._phase == _Phase.FADE_IN:
            self._update_fade_in()
        elif self._phase == _Phase.TRANSFORM:
            self._update_anim(dt_sec, self._frames_transform, _Phase.ATTACK_LEFT)
            self._update_transform_flash()
        elif self._phase == _Phase.ATTACK_LEFT:
            self._update_anim(dt_sec, self._frames_atk_left, _Phase.ATTACK_RIGHT)
        elif self._phase == _Phase.ATTACK_RIGHT:
            self._update_anim(dt_sec, self._frames_atk_right, _Phase.REVERT)
        elif self._phase == _Phase.REVERT:
            self._update_revert(dt_sec)
        elif self._phase == _Phase.LEVEL_INTRO:
            self._banner.update(dt)
            if not self._banner.is_active:
                self._finish()

    def _update_fade_in(self) -> None:
        if self._phase_timer >= self._FADE_IN_DURATION:
            self._enter_phase(_Phase.TRANSFORM)

    def _update_anim(
        self,
        dt_sec: float,
        frames: list[pg.Surface],
        next_phase: _Phase,
    ) -> None:
        self._frame_timer += dt_sec
        while self._frame_timer >= self._FRAME_DURATION:
            self._frame_timer -= self._FRAME_DURATION
            self._frame_idx += 1
            if self._frame_idx >= len(frames):
                self._enter_phase(next_phase)
                return

    def _update_transform_flash(self) -> None:
        """White flash then red flash at the midpoint of the transform."""
        mid = len(self._frames_transform) // 2
        if self._frame_idx >= mid and not self._transform_flash_triggered:
            # Trigger white flash
            self._transform_flash_triggered = True
            self._flash_color = (255, 255, 255)
            self._flash_alpha = 255.0
        elif (
            self._transform_flash_triggered
            and not self._transform_red_triggered
            and self._flash_alpha < 80
        ):
            # Once white has mostly faded, fire a red flash
            self._transform_red_triggered = True
            self._flash_color = (180, 20, 20)
            self._flash_alpha = 200.0

    def _update_revert(self, dt_sec: float) -> None:
        """Play back2human frames + rapid red screen flashes."""
        # Advance animation
        self._frame_timer += dt_sec
        while self._frame_timer >= self._FRAME_DURATION:
            self._frame_timer -= self._FRAME_DURATION
            if self._frame_idx < len(self._frames_revert) - 1:
                self._frame_idx += 1

        # Red flash pulses
        if self._red_flashes_done < self._RED_FLASH_COUNT:
            self._red_flash_timer += dt_sec
            cycle_pos = self._red_flash_timer % self._RED_FLASH_CYCLE
            half = self._RED_FLASH_CYCLE / 2.0

            if cycle_pos < half:
                # Rising
                t = cycle_pos / half
                self._flash_color = (200, 15, 15)
                self._flash_alpha = 180.0 * _ease_in_out(t)
            else:
                # Falling
                t = (cycle_pos - half) / half
                self._flash_color = (200, 15, 15)
                self._flash_alpha = 180.0 * (1.0 - _ease_in_out(t))

            if self._red_flash_timer >= self._RED_FLASH_CYCLE:
                self._red_flash_timer -= self._RED_FLASH_CYCLE
                self._red_flashes_done += 1
        else:
            self._flash_alpha = 0.0
            # All flashes done + animation done → pause then level intro
            if self._frame_idx >= len(self._frames_revert) - 1:
                self._post_pause_timer += dt_sec
                if self._post_pause_timer >= self._POST_REVERT_PAUSE:
                    self._enter_phase(_Phase.LEVEL_INTRO)
                    self._banner.show(
                        self._level_title,
                        notification=self._notification_type,
                    )

    # ─── Phase management ────────────────────────────────────────────────────

    def _enter_phase(self, phase: _Phase) -> None:
        """Transition to a new phase with a cross-fade from the last frame."""
        # Capture the last frame of the current phase for cross-fading
        old_frames = self._get_current_frames()
        if old_frames:
            idx = min(self._frame_idx, len(old_frames) - 1)
            self._prev_frame = old_frames[idx]
            self._crossfading = True
            self._crossfade_timer = 0.0

        self._phase = phase
        self._phase_timer = 0.0
        self._frame_idx = 0
        self._frame_timer = 0.0
        self._transform_flash_triggered = False
        self._transform_red_triggered = False

    def _get_current_frames(self) -> list[pg.Surface]:
        """Return the frame list for the current phase."""
        if self._phase == _Phase.TRANSFORM:
            return self._frames_transform
        elif self._phase == _Phase.ATTACK_LEFT:
            return self._frames_atk_left
        elif self._phase == _Phase.ATTACK_RIGHT:
            return self._frames_atk_right
        elif self._phase == _Phase.REVERT:
            return self._frames_revert
        return []

    def _finish(self) -> None:
        if self._phase == _Phase.DONE:
            return
        self._phase = _Phase.DONE

        if self._on_complete:
            self._on_complete()
        elif self._next_state_factory:
            self.manager.set(self._next_state_factory())

    # ─── Draw ────────────────────────────────────────────────────────────────

    def draw(self, surface: pg.Surface) -> None:
        surface.fill((0, 0, 0))

        if self._phase == _Phase.FADE_IN:
            self._draw_fade_in(surface)
        elif self._phase == _Phase.TRANSFORM:
            self._draw_phase_sprite(surface, self._frames_transform)
            self._draw_flash(surface)
        elif self._phase == _Phase.ATTACK_LEFT:
            self._draw_phase_sprite(surface, self._frames_atk_left)
        elif self._phase == _Phase.ATTACK_RIGHT:
            self._draw_phase_sprite(surface, self._frames_atk_right)
        elif self._phase == _Phase.REVERT:
            self._draw_phase_sprite(surface, self._frames_revert)
            self._draw_flash(surface)
        elif self._phase == _Phase.LEVEL_INTRO:
            self._banner.draw(surface)

    def _draw_fade_in(self, surface: pg.Surface) -> None:
        """Fade from black with eased curve, showing first transform frame."""
        if not self._frames_transform:
            return
        t = min(1.0, self._phase_timer / self._FADE_IN_DURATION)
        alpha = int(255 * _ease_in_out(t))

        frame = self._frames_transform[0]
        rect = frame.get_rect(center=(self._sw // 2, self._sh // 2))
        frame.set_alpha(alpha)
        surface.blit(frame, rect)
        frame.set_alpha(255)  # restore for later use

    def _draw_phase_sprite(
        self, surface: pg.Surface, frames: list[pg.Surface]
    ) -> None:
        """Draw the current animation frame, with optional cross-fade from previous phase."""
        cx, cy = self._sw // 2, self._sh // 2

        # Cross-fade: draw the previous phase's last frame fading out
        if self._crossfading and self._prev_frame is not None:
            t = min(1.0, self._crossfade_timer / self._CROSSFADE_DURATION)
            fade_out = int(255 * (1.0 - _ease_in_out(t)))
            rect = self._prev_frame.get_rect(center=(cx, cy))
            self._prev_frame.set_alpha(fade_out)
            surface.blit(self._prev_frame, rect)
            self._prev_frame.set_alpha(255)

            # New frame fading in
            if frames:
                idx = min(self._frame_idx, len(frames) - 1)
                frame = frames[idx]
                rect = frame.get_rect(center=(cx, cy))
                fade_in = int(255 * _ease_in_out(t))
                frame.set_alpha(fade_in)
                surface.blit(frame, rect)
                frame.set_alpha(255)
        else:
            # Normal rendering
            if not frames:
                return
            idx = min(self._frame_idx, len(frames) - 1)
            frame = frames[idx]
            rect = frame.get_rect(center=(cx, cy))
            surface.blit(frame, rect)

    def _draw_flash(self, surface: pg.Surface) -> None:
        """Draw screen flash overlay with current alpha."""
        if self._flash_alpha <= 0:
            return
        r, g, b = self._flash_color
        a = int(min(255.0, self._flash_alpha))
        self._overlay.fill((r, g, b, a))
        surface.blit(self._overlay, (0, 0))

