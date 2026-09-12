"""
Prologue Story State — Atmospheric scene with NPC-style dialogue presentation.

Presents the core story premise using the established in-game dialogue aesthetic:
dark translucent slate, luminous gold typography, atmospheric backdrop, and
pulsing continue prompt.
"""

from __future__ import annotations

import math
from typing import Optional
import pygame as pg

from v3x_zulfiqar_gideon import State, AssetManager
from src.game.ui.animated_dialogue_renderer import AnimatedDialogueRenderer
from src.game.audio.voiceover_manager import VoiceoverManager


class StoryState(State):
    """Atmospheric prologue state displaying the core pitch in NPC-dialogue style."""

    _PROLOGUE_TEXT = (
        "Her hand slipped. You let her fall. Death didn't take Elysia—a debt collector did. "
        "Borrow his black flame to tear her back. Run. Slay. But remember: each demon slash "
        "burns away the brother she loved."
    )

    def __init__(
        self,
        manager,
        *args,
        text: Optional[str] = None,
        title: str = "THE UNPAID DEBT",
        **kwargs,
    ):
        super().__init__(manager)
        self.width = pg.display.get_surface().get_width()
        self.height = pg.display.get_surface().get_height()

        self.title = title
        self.story_text = text if text is not None else self._PROLOGUE_TEXT

        # ── Fonts (Clean, crisp, highly legible pixel fonts matching the title) ──
        self.title_font = AssetManager.get_font(
            "assets/font/Abaddon Bold.ttf",
            44,
        )
        self.font = AssetManager.get_font(
            "assets/font/Abaddon Bold.ttf",
            28,
        )
        self.prompt_font = AssetManager.get_font(
            "assets/font/Abaddon Bold.ttf",
            24,
        )

        # ── Background Art & Parallax ─────────────────────────────────────────
        bg_path = "assets/graphics/Pixel-Art-Battlegrounds/PNG/Battleground3/Bright/jungle_bg.png"
        trees_path = "assets/graphics/Pixel-Art-Battlegrounds/PNG/Battleground3/Bright/trees&bushes.png"
        sky_path = "assets/graphics/Pixel-Art-Battlegrounds/PNG/Battleground3/Bright/sky.png"

        self._sky_img: Optional[pg.Surface] = None
        self._bg_img: Optional[pg.Surface] = None
        self._trees_img: Optional[pg.Surface] = None

        try:
            raw_sky = AssetManager.get_texture(sky_path)
            self._sky_img = pg.transform.smoothscale(raw_sky, (self.width, self.height))
        except Exception:
            pass

        try:
            raw_bg = AssetManager.get_texture(bg_path)
            self._bg_img = pg.transform.smoothscale(raw_bg, (self.width, self.height))
        except Exception:
            pass

        try:
            raw_trees = AssetManager.get_texture(trees_path)
            self._trees_img = pg.transform.smoothscale(raw_trees, (self.width, self.height))
        except Exception:
            pass

        # ── Ambient Ember Particles ──────────────────────────────────────────
        self._particles = [
            {
                "x": float((i * 37) % self.width),
                "y": float(self.height - 180 + (i * 13) % 150),
                "speed_x": 12.0 + (i % 5) * 6.0,
                "speed_y": -15.0 - (i % 4) * 8.0,
                "size": 2 + (i % 3),
                "alpha_phase": (i * 0.7),
            }
            for i in range(35)
        ]

        # ── Dialogue Box Dimensions ──────────────────────────────────────────
        self.box_w = min(1160, self.width - 80)
        self.box_h = 270
        self.box_x = (self.width - self.box_w) // 2
        self.box_y = self.height - self.box_h - 35

        # ── Dialogue Box & Typewriter State ──────────────────────────────────
        self.alpha: float = 0.0
        self.fade_speed: float = 300.0
        self.elapsed: float = 0.0
        self.text_progress: float = 0.0
        self.text_speed: float = 45.0
        self.is_text_complete: bool = False
        self.is_exiting: bool = False
        self.exit_alpha: float = 0.0

        self.anim_renderer = AnimatedDialogueRenderer(
            typing_speed=self.text_speed,
            scale_duration=1.0,
            max_scale=1.8,
            theme="necromancer",
        )
        self.anim_renderer.set_text(self.story_text)

        # Word wrap pre-calculation (box_w - 70 padding)
        self._wrapped_lines: list[str] = self._word_wrap(self.story_text, max_width=self.box_w - 70)
        self._black_overlay = pg.Surface((self.width, self.height), pg.SRCALPHA)

        # Voiceover for prologue narration
        self._voiceover = VoiceoverManager()
        self._voiceover.load_manifest()

    def _word_wrap(self, text: str, max_width: int) -> list[str]:
        words = text.split(" ")
        lines: list[str] = []
        curr = ""
        for w in words:
            test = f"{curr} {w}".strip() if curr else w
            if self.font.size(test)[0] <= max_width:
                curr = test
            else:
                if curr:
                    lines.append(curr)
                curr = w
        if curr:
            lines.append(curr)
        return lines

    # ── Lifecycle ────────────────────────────────────────────────────────────

    def on_enter(self):
        self.alpha = 0.0
        self.elapsed = 0.0
        self.text_progress = 0.0
        self.is_text_complete = False
        self.is_exiting = False
        self.exit_alpha = 0.0
        if hasattr(self.manager, "audio_manager") and self.manager.audio_manager:
            self.manager.audio_manager.play_music("background_music", volume=0.45)
        # Start prologue voiceover
        self._voiceover.play_line("prologue_narration")

    def on_exit(self):
        self._voiceover.stop(fadeout_ms=500)

    # ── Events ───────────────────────────────────────────────────────────────

    def handle_event(self, event: pg.event.Event):
        advance_pressed = (
            (event.type == pg.KEYDOWN and event.key in (pg.K_RETURN, pg.K_SPACE, pg.K_e, pg.K_x))
            or (event.type == pg.JOYBUTTONDOWN and event.button in (0, 1, 6, 7))
        )

        if advance_pressed:
            if not self.is_text_complete:
                # First press instantly completes the text
                self.anim_renderer.skip_to_end()
                self.text_progress = float(len(self.story_text))
                self.is_text_complete = True
            elif not self.is_exiting:
                # Second press starts smooth transition to transformation cutscene
                self.is_exiting = True
                self._voiceover.stop(fadeout_ms=300)

    # ── Update ───────────────────────────────────────────────────────────────

    def update(self, dt: float):
        dt_sec = dt / 1000.0 if dt > 0.5 else dt
        self.elapsed += dt_sec

        # Fade in screen
        if self.alpha < 255.0:
            self.alpha = min(255.0, self.alpha + self.fade_speed * dt_sec)

        # Advance typewriter text
        if not self.is_text_complete:
            self.anim_renderer.update(dt_sec)
            self.text_progress = float(self.anim_renderer.current_char_count)
            if self.anim_renderer.is_complete:
                self.text_progress = float(len(self.story_text))
                self.is_text_complete = True

        # Update ambient embers
        for p in self._particles:
            p["x"] += p["speed_x"] * dt_sec
            p["y"] += p["speed_y"] * dt_sec
            if p["x"] > self.width + 20:
                p["x"] = -20
            if p["y"] < -20:
                p["y"] = float(self.height - 200)

        # Handle exit fade
        if self.is_exiting:
            self.exit_alpha += 450.0 * dt_sec
            if self.exit_alpha >= 255.0:
                self.finish("NEW_GAME")

    # ── Draw ─────────────────────────────────────────────────────────────────

    def draw(self, surface: pg.Surface):
        surface.fill((12, 10, 20))

        # 1. Background Layers with gentle subtle drift
        drift = math.sin(self.elapsed * 0.3) * 6.0
        if self._sky_img:
            surface.blit(self._sky_img, (0, 0))
        if self._bg_img:
            surface.blit(self._bg_img, (int(drift * 0.5), 0))
        if self._trees_img:
            surface.blit(self._trees_img, (int(drift), 0))

        # Dark atmospheric vignette / gradient over top and bottom
        vignette = pg.Surface((self.width, self.height), pg.SRCALPHA)
        vignette.fill((8, 6, 14, 130))
        surface.blit(vignette, (0, 0))

        # 2. Ambient Glowing Particles (Embers / Fireflies)
        ticks = pg.time.get_ticks()
        for p in self._particles:
            p_pulse = (math.sin(ticks * 0.004 + p["alpha_phase"]) + 1.0) * 0.5
            p_alpha = int(120 + 110 * p_pulse)
            glow_surf = pg.Surface((16, 16), pg.SRCALPHA)
            pg.draw.circle(glow_surf, (255, 180, 40, int(p_alpha * 0.4)), (8, 8), 6)
            pg.draw.circle(glow_surf, (255, 220, 100, p_alpha), (8, 8), p["size"])
            surface.blit(glow_surf, (int(p["x"]) - 8, int(p["y"]) - 8))

        # 3. Bottom NPC-Style Dialogue Box
        box_w = self.box_w
        box_h = self.box_h
        box_x = self.box_x
        box_y = self.box_y

        # Obsidian Dark Slate Background with Gold Border
        box_surf = pg.Surface((box_w, box_h), pg.SRCALPHA)
        box_surf.fill((10, 6, 18, 230))
        # Outer gold accent frame
        pg.draw.rect(
            box_surf,
            (255, 190, 50, 200),
            (0, 0, box_w, box_h),
            width=2,
            border_radius=10,
        )
        # Inner subtle highlight ring
        pg.draw.rect(
            box_surf,
            (120, 80, 20, 90),
            (4, 4, box_w - 8, box_h - 8),
            width=1,
            border_radius=8,
        )
        surface.blit(box_surf, (box_x, box_y))

        # 4. Title Header Tag (e.g. THE UNPAID DEBT)
        title_y = box_y + 18
        title_x = box_x + 35

        # Drop shadow
        t_shd = self.title_font.render(self.title, True, (0, 0, 0))
        surface.blit(t_shd, (title_x + 2, title_y + 2))
        # Main Title (Luminous Amber / Gold)
        t_surf = self.title_font.render(self.title, True, (255, 205, 70))
        surface.blit(t_surf, (title_x, title_y))

        # 5. Typewriter Story Text
        text_start_y = title_y + 48
        text_rect = pg.Rect(box_x + 35, text_start_y, box_w - 70, box_h - 80)
        self.anim_renderer.render(
            surface=surface,
            font=self.font,
            rect=text_rect,
            color=(245, 235, 215),
            shadow_color=(0, 0, 0),
            align="left",
            line_spacing=6,
        )

        # 6. Pulsing Continue Prompt
        if self.is_text_complete:
            p_pulse = (math.sin(ticks * 0.007) + 1.0) * 0.5
            p_alpha = int(140 + 115 * p_pulse)
            prompt_str = "[ PRESS SPACE OR ENTER TO BEGIN ]"

            p_w = self.prompt_font.size(prompt_str)[0]
            px = box_x + box_w - p_w - 30
            py = box_y + box_h - 36

            p_shd = self.prompt_font.render(prompt_str, True, (0, 0, 0))
            p_shd.set_alpha(int(p_alpha * 0.85))
            surface.blit(p_shd, (px + 2, py + 2))

            p_txt = self.prompt_font.render(prompt_str, True, (255, 215, 90))
            p_txt.set_alpha(p_alpha)
            surface.blit(p_txt, (px, py))

        # 7. Cinematic Fade-In / Exit Transition
        if self.alpha < 255.0:
            fade_overlay = pg.Surface((self.width, self.height), pg.SRCALPHA)
            fade_overlay.fill((0, 0, 0, int(255 - self.alpha)))
            surface.blit(fade_overlay, (0, 0))

        if self.is_exiting and self.exit_alpha > 0.0:
            exit_overlay = pg.Surface((self.width, self.height), pg.SRCALPHA)
            exit_overlay.fill((0, 0, 0, int(min(255.0, self.exit_alpha))))
            surface.blit(exit_overlay, (0, 0))
