"""
Tutorial overlay system — teaches controls via in-game banners.

Displays sequential tutorial steps on top of gameplay, each showing:
 - Player animation on the left (demonstrating the move)
 - Text + animated key sprites in the centre (showing which buttons to press)
 - Oracle tower animating on the right side (narrator)

Gameplay freezes while the overlay is active (same pattern as ObjectiveDisplay).


HOW TO TWEAK POSITIONS
──────────────────────
All positions are pre-computed in ``__init__`` into ``self._pos`` — a simple
dict of *named pixel coordinates*.  The ``draw()`` method never does maths;
it just reads ``self._pos["sprite_center"]``, ``self._pos["oracle_center"]``, etc.

To move something, find its name in the ``PRE-COMPUTE`` section and change
the pixel numbers.

    ┌──────────────────────────────────────────────────────────────────┐
    │  PARCHMENT BANNER                                               │
    │                                                                  │
    │   ┌───────────┐   Title                        ┌──────────┐     │
    │   │           │   Description text ...          │  ORACLE  │     │
    │   │  PLAYER   │                                 │  TOWER   │     │
    │   │  SPRITE   │   [ KEY ] [ KEY ]               │  (anim)  │     │
    │   │           │                                 └──────────┘     │
    │   └───────────┘                                                  │
    │                    prompt               step counter             │
    └──────────────────────────────────────────────────────────────────┘
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional

import pygame as pg

from v3x_zulfiqar_gideon.asset_manager import AssetManager
from v3x_zulfiqar_gideon.ui import UITheme


# ─────────────────────────────────────────────────────────────────────────────
# Step Definition
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class TutorialStep:
    """Configuration for a single tutorial lesson.

    Attributes:
        title:          Heading shown on the banner (e.g. "Movement").
        description:    Body text explaining the action.
        key_names:      Filenames **without** .png from ``assets/graphics/KEYS/``.
        animation_dir:  Path to the shadow_warrior animation folder to play.
        accepted_keys:  Pygame key constants that advance this step.
    """
    title: str
    description: str
    key_names: list[str]
    animation_dir: str
    accepted_keys: list[int]


# ─────────────────────────────────────────────────────────────────────────────
# Default Steps  — edit these to change what the tutorial teaches
# ─────────────────────────────────────────────────────────────────────────────

DEFAULT_STEPS: list[TutorialStep] = [
    TutorialStep(
        title="Movement",
        description="Use the arrow keys to move left and right.",
        key_names=["ARROWLEFT", "ARROWRIGHT"],
        animation_dir="assets/shadow_warrior/run",
        accepted_keys=[pg.K_LEFT, pg.K_RIGHT],
    ),
    TutorialStep(
        title="Jump",
        description="Press SPACE to jump over obstacles.",
        key_names=["SPACE"],
        animation_dir="assets/shadow_warrior/jump_up_loop",
        accepted_keys=[pg.K_SPACE],
    ),
    TutorialStep(
        title="Thrust Attack",
        description="Press Q for a quick thrust attack.",
        key_names=["Q"],
        animation_dir="assets/shadow_warrior/1_atk",
        accepted_keys=[pg.K_q],
    ),
    TutorialStep(
        title="Smash Attack",
        description="Press E for a powerful smash attack.",
        key_names=["E"],
        animation_dir="assets/shadow_warrior/2_atk",
        accepted_keys=[pg.K_e],
    ),
    TutorialStep(
        title="Power Attack",
        description="Press W to unleash a devastating power attack.",
        key_names=["W"],
        animation_dir="assets/shadow_warrior/3_atk",
        accepted_keys=[pg.K_w],
    ),
    TutorialStep(
        title="Defend",
        description="Hold R to raise your shield and block incoming attacks.",
        key_names=["R"],
        animation_dir="assets/shadow_warrior/defend",
        accepted_keys=[pg.K_r],
    ),
]


# ─────────────────────────────────────────────────────────────────────────────
# Tutorial Overlay
# ─────────────────────────────────────────────────────────────────────────────

class TutorialOverlay:
    """In-game tutorial overlay that teaches the player controls.

    Uses the parchment board as the banner background.  The oracle tower,
    player sprite, text, and key icons all sit *inside* the single banner.

    Usage inside GameState::

        self.tutorial = TutorialOverlay()
        self.tutorial.start()                   # on first on_enter()

        if self.tutorial.is_active:
            self.tutorial.handle_event(event)   # in handle_event()
            ...
            self.tutorial.update(dt)            # in update()
            return                              # freeze gameplay
            ...
            self.tutorial.draw(surface)         # in draw()
    """

    def __init__(
        self,
        steps: Optional[list[TutorialStep]] = None,
        *,
        # ── SIZES ───────────────────────────────────────────────────────────
        #    How big each element is. Change these to resize things.
        banner_width: float  = 0.60,     # parchment width  (fraction of screen)
        sprite_scale: int    = 3,        # player animation scale multiplier
        oracle_scale: int    = 0.6,        # oracle tower scale multiplier
        key_scale: int       = 4,        # key icon scale multiplier

        # ── POSITIONS ───────────────────────────────────────────────────────
        #    Where the banner sits on screen.  Fractions of the screen
        #    (0.0 = left/top, 1.0 = right/bottom).
        banner_x: float      = 0.50,     # banner horizontal centre
        banner_y: float      = 0.50,     # banner vertical centre

        # ── INNER POSITIONS (within the banner) ─────────────────────────────
        #    These position elements *relative to the banner*.
        #    0.0 = left/top edge of the banner, 1.0 = right/bottom edge.
        sprite_x: float      = 0.50,     # player sprite horizontal centre
        sprite_y: float      = 0.50,     # player sprite vertical centre
        title_x: float       = 0.50,     # title horizontal centre
        title_y: float       = 0.19,     # title vertical position (top edge)
        text_x: float        = 0.50,     # description / keys horizontal centre
        text_wrap_width: float = 0.35,   # max text width (fraction of banner)
        oracle_x: float      = 0.50,     # oracle tower horizontal centre
        oracle_y: float      = 0.13,     # oracle tower vertical centre
        prompt_y: float      = 0.92,     # prompt vertical position (bottom edge)
        counter_x: float     = 0.95,     # step counter horizontal (right-aligned)

        # ── SPACING (pixels) ────────────────────────────────────────────────
        key_spacing: int     = 12,       # gap between adjacent key icons
        key_gap: int         = 16,       # gap between description and keys
        desc_line_gap: int   = 4,        # gap between wrapped description lines
        desc_title_gap: int  = 10,       # gap between title and first desc line

        # ── ANIMATION ───────────────────────────────────────────────────────
        player_fps: float    = 0.08,     # seconds per player animation frame
        oracle_fps: float    = 0.10,     # seconds per oracle animation frame
        pulse_speed: float   = 3.0,      # key pulse oscillation speed (Hz)
        pulse_amount: float  = 0.15,     # key pulse scale variance (±15%)

        # ── COLOURS ─────────────────────────────────────────────────────────
        backdrop_alpha: int  = 160,      # 0 = transparent, 255 = solid black
        title_color: tuple   = (60, 40, 20),       # dark parchment-friendly
        desc_color: tuple    = (80, 60, 35),
        prompt_color: tuple  = (100, 75, 50),
        counter_color: tuple = (120, 90, 60),

        # ── FONTS ───────────────────────────────────────────────────────────
        title_font_size: int  = 36,
        desc_font_size: int   = 24,
        prompt_font_size: int = 20,

        # ── ASSET PATHS ─────────────────────────────────────────────────────
        banner_path: str = "assets/graphics/UI/PNG/UI board Medium  parchment.png",
        keys_dir: str    = "assets/graphics/KEYS",
        oracle_dir: str  = "assets/graphics/RedMoonTower",
    ) -> None:

        # ── Screen dimensions ───────────────────────────────────────────────
        info = pg.display.Info()
        sw = info.current_w
        sh = info.current_h

        # ── Store animation / colour settings ───────────────────────────────
        self._player_fps    = player_fps
        self._oracle_fps    = oracle_fps
        self._pulse_speed   = pulse_speed
        self._pulse_amount  = pulse_amount
        self._title_color   = title_color
        self._desc_color    = desc_color
        self._prompt_color  = prompt_color
        self._counter_color = counter_color
        self._key_spacing   = key_spacing
        self._key_gap       = key_gap
        self._desc_line_gap  = desc_line_gap
        self._desc_title_gap = desc_title_gap

        # ── Steps / state ───────────────────────────────────────────────────
        self._steps = steps or DEFAULT_STEPS
        self._step_idx = 0
        self._active = False
        self._completed = False

        # ── Timers ──────────────────────────────────────────────────────────
        self._player_timer = 0.0
        self._player_frame = 0
        self._oracle_timer = 0.0
        self._oracle_frame = 0
        self._pulse_timer  = 0.0

        # ── Load assets ─────────────────────────────────────────────────────
        cfg = UITheme.get("notifications")
        font_path = cfg["font_path"]

        # Parchment banner (single board — everything sits inside it)
        raw_banner = AssetManager.get_texture(banner_path)
        bw = int(sw * banner_width)
        bh = int(bw * raw_banner.get_height() / raw_banner.get_width())
        self._banner = pg.transform.smoothscale(raw_banner, (bw, bh))

        # ── PRE-COMPUTE ALL PIXEL POSITIONS ─────────────────────────────────
        #
        #    This is the ONLY place where position maths happens.
        #    Everything below is a plain (x, y) tuple or int.
        #    The draw() method just reads from self._pos.
        #
        self._pos = {}

        # Banner top-left (derived from centre)
        bx = int(sw * banner_x) - bw // 2
        by = int(sh * banner_y) - bh // 2
        self._pos["banner_topleft"] = (bx, by)

        # Player sprite — left region of the banner
        self._pos["sprite_center"] = (
            bx + int(bw * sprite_x),
            by + int(bh * sprite_y),
        )

        # Title — centred horizontally, near the top
        self._pos["title_centerx"] = bx + int(bw * title_x)
        self._pos["title_top"]     = by + int(bh * title_y)

        # Description / keys — below the title, centred
        self._pos["text_centerx"]   = bx + int(bw * text_x)
        self._pos["text_max_width"] = int(bw * text_wrap_width)

        # Oracle tower — right region of the banner
        self._pos["oracle_center"] = (
            bx + int(bw * oracle_x),
            by + int(bh * oracle_y),
        )

        # Prompt — bottom of the banner, centred
        self._pos["prompt_centerx"] = bx + bw // 2
        self._pos["prompt_bottom"]  = by + int(bh * prompt_y)

        # Step counter — bottom-right of the banner
        self._pos["counter_right"]  = bx + int(bw * counter_x)
        self._pos["counter_bottom"] = by + int(bh * prompt_y)

        # ── Store banner rect for reference ─────────────────────────────────
        self._banner_rect = pg.Rect(bx, by, bw, bh)

        # ── Fonts ───────────────────────────────────────────────────────────
        self._title_font  = AssetManager.get_font(font_path, title_font_size)
        self._desc_font   = AssetManager.get_font(font_path, desc_font_size)
        self._prompt_font = AssetManager.get_font(font_path, prompt_font_size)

        # ── Backdrop ────────────────────────────────────────────────────────
        self._backdrop = pg.Surface((sw, sh), pg.SRCALPHA)
        self._backdrop.fill((0, 0, 0, backdrop_alpha))

        # ── Oracle tower animation frames ───────────────────────────────────
        self._oracle_frames = self._load_scaled_frames(oracle_dir, oracle_scale)

        # ── Pre-load key images per step ────────────────────────────────────
        self._step_key_imgs: list[list[pg.Surface]] = []
        for step in self._steps:
            keys = []
            for kn in step.key_names:
                raw = AssetManager.get_texture(f"{keys_dir}/{kn}.png")
                keys.append(pg.transform.scale(
                    raw, (raw.get_width() * key_scale, raw.get_height() * key_scale)
                ))
            self._step_key_imgs.append(keys)

        # ── Pre-load player animation frames per step ───────────────────────
        self._step_player_frames: list[list[pg.Surface]] = []
        for step in self._steps:
            self._step_player_frames.append(
                self._load_scaled_frames(step.animation_dir, sprite_scale)
            )

    # ─── Asset helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _load_scaled_frames(directory: str, scale: int) -> list[pg.Surface]:
        return [
            pg.transform.scale(f, (f.get_width() * scale, f.get_height() * scale))
            for f in AssetManager.get_animation_frames(directory)
        ]

    # ─── Public interface ────────────────────────────────────────────────────

    @property
    def is_active(self) -> bool:
        return self._active

    @property
    def is_completed(self) -> bool:
        return self._completed

    def start(self) -> None:
        """Begin the tutorial sequence from step 0."""
        if self._completed:
            return
        self._step_idx = 0
        self._active = True
        self._reset_anim()

    def handle_event(self, event: pg.event.Event) -> None:
        """Advance on the taught key, SPACE, or ENTER."""
        if not self._active or event.type != pg.KEYDOWN:
            return
        step = self._steps[self._step_idx]
        if event.key in step.accepted_keys or event.key in (pg.K_SPACE, pg.K_RETURN):
            self._advance()

    def update(self, dt: float) -> None:
        """Advance animations. *dt* is in **milliseconds**."""
        if not self._active:
            return
        dt_sec = dt / 1000.0

        # Player animation
        frames = self._step_player_frames[self._step_idx]
        if frames:
            self._player_timer += dt_sec
            if self._player_timer >= self._player_fps:
                self._player_timer -= self._player_fps
                self._player_frame = (self._player_frame + 1) % len(frames)

        # Oracle animation
        if self._oracle_frames:
            self._oracle_timer += dt_sec
            if self._oracle_timer >= self._oracle_fps:
                self._oracle_timer -= self._oracle_fps
                self._oracle_frame = (self._oracle_frame + 1) % len(self._oracle_frames)

        # Key pulse clock
        self._pulse_timer += dt_sec

    # ─── Draw ────────────────────────────────────────────────────────────────
    #
    #   Every position is read from  self._pos["name"]  — no maths here.
    #   If you want to move something, change it in __init__  ↑ above.
    #

    def draw(self, surface: pg.Surface) -> None:
        if not self._active:
            return

        p = self._pos                           # shorthand
        step = self._steps[self._step_idx]

        # ── 1. Dark backdrop ────────────────────────────────────────────────
        surface.blit(self._backdrop, (0, 0))

        # ── 2. Parchment banner ─────────────────────────────────────────────
        surface.blit(self._banner, p["banner_topleft"])

        # ── 3. Player sprite (left side) ────────────────────────────────────
        frames = self._step_player_frames[self._step_idx]
        if frames:
            sprite = frames[min(self._player_frame, len(frames) - 1)]
            surface.blit(sprite, sprite.get_rect(center=p["sprite_center"]))

        # ── 4. Oracle tower (right side) ────────────────────────────────────
        if self._oracle_frames:
            oracle = self._oracle_frames[min(self._oracle_frame, len(self._oracle_frames) - 1)]
            surface.blit(oracle, oracle.get_rect(center=p["oracle_center"]))

        # ── 5. Title (centre-top) ──────────────────────────────────────────
        title_surf = self._title_font.render(step.title, True, self._title_color)
        title_rect = title_surf.get_rect(
            centerx=p["title_centerx"],
            top=p["title_top"],
        )
        surface.blit(title_surf, title_rect)

        # ── 6. Description text (below title) ──────────────────────────────
        desc_lines = self._wrap_text(
            step.description, self._desc_font, p["text_max_width"], self._desc_color
        )
        y = title_rect.bottom + self._desc_title_gap
        for line_surf in desc_lines:
            surface.blit(line_surf, line_surf.get_rect(centerx=p["text_centerx"], top=y))
            y += line_surf.get_height() + self._desc_line_gap

        # ── 7. Key icons (pulsing, below description) ──────────────────────
        pulse = 1.0 + self._pulse_amount * math.sin(
            self._pulse_timer * self._pulse_speed * 2 * math.pi
        )
        key_imgs = self._step_key_imgs[self._step_idx]
        total_w = sum(k.get_width() for k in key_imgs) + self._key_spacing * max(0, len(key_imgs) - 1)
        kx = p["text_centerx"] - total_w // 2
        ky = y + self._key_gap

        for img in key_imgs:
            pw, ph = int(img.get_width() * pulse), int(img.get_height() * pulse)
            pulsed = pg.transform.scale(img, (pw, ph))
            surface.blit(pulsed, pulsed.get_rect(midtop=(kx + img.get_width() // 2, ky)))
            kx += img.get_width() + self._key_spacing

        # ── 8. "Press KEY to continue" prompt ──────────────────────────────
        alpha = 160 + int(95 * abs(((pg.time.get_ticks() // 8) % 200 - 100) / 100))
        prompt_surf = self._prompt_font.render(
            f"Press {' / '.join(step.key_names)} to continue", True, self._prompt_color
        )
        prompt_surf.set_alpha(alpha)
        surface.blit(prompt_surf, prompt_surf.get_rect(
            centerx=p["prompt_centerx"],
            bottom=p["prompt_bottom"],
        ))

        # ── 9. Step counter (bottom-right) ─────────────────────────────────
        counter_surf = self._prompt_font.render(
            f"{self._step_idx + 1} / {len(self._steps)}", True, self._counter_color
        )
        surface.blit(counter_surf, counter_surf.get_rect(
            right=p["counter_right"],
            bottom=p["counter_bottom"],
        ))

    # ─── Internal helpers ────────────────────────────────────────────────────

    def _advance(self) -> None:
        self._step_idx += 1
        if self._step_idx >= len(self._steps):
            self._active = False
            self._completed = True
        else:
            self._reset_anim()

    def _reset_anim(self) -> None:
        self._player_timer = 0.0
        self._player_frame = 0
        self._pulse_timer  = 0.0

    @staticmethod
    def _wrap_text(text: str, font, max_width: int, color: tuple) -> list[pg.Surface]:
        words = text.split()
        lines: list[pg.Surface] = []
        current = ""
        for word in words:
            test = f"{current} {word}".strip()
            if font.size(test)[0] <= max_width:
                current = test
            else:
                if current:
                    lines.append(font.render(current, True, color))
                current = word
        if current:
            lines.append(font.render(current, True, color))
        return lines
