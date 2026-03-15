import pygame as pg
from v3x_zulfiqar_gideon.state_machine import State
from v3x_zulfiqar_gideon.asset_manager import AssetManager
from v3x_zulfiqar_gideon.effects import SceneHighlighter
from v3x_zulfiqar_gideon.ui import UIButton
from v3x_zulfiqar_gideon.ui import NotificationBanner


class StoryState(State):
    """Story narration screen with parchment menu.

    Shows the intro scene illustration with a voiceover, then presents
    a stone+parchment menu with New Game / Continue / Settings.

    Every layout/timing value is a constructor argument so you can tweak
    the look by changing a single number.

    Args:
        manager:           State manager reference.
        voiceover_delay:   Seconds to wait before playing the voiceover.
        menu_delay:        Seconds to wait (after scene fade-in) before the menu appears.
        scene_fade_speed:  Alpha units per second for the scene image fade-in.
        menu_fade_speed:   Alpha units per second for the menu fade-in.
        menu_x_frac:       Horizontal position of the menu as fraction of screen width
                           (0.0 = left edge, 1.0 = right edge).
        menu_y_frac:       Vertical position of the menu as fraction of screen height
                           (0.0 = top, 1.0 = bottom).
        menu_x_margin:     Pixel margin from the edge (applied after x_frac).
        parchment_scale:   Parchment board width as fraction of screen width.
        stone_scale:       Stone board width as fraction of screen width.
        btn_scale:         Scale multiplier for all menu buttons.
        btn_spacing:       Vertical gap (pixels) between each button.
        btn_y_offset:      Vertical offset (pixels) of the first button relative to menu centre.
        btn_size:          UIButton asset size (``"big"``, ``"medium"``, etc.).
    """

    # ── Asset paths (not configurable — they're file locations) ──────────────
    _VOICEOVER_PATH = "assets/audio/voice_over.mp3"
    _STONE_PATH = "assets/graphics/UI/PNG/UI board Medium  stone.png"
    _PARCHMENT_PATH = "assets/graphics/UI/PNG/UI board Medium  parchment.png"

    def __init__(
        self,
        manager,
        *,
        voiceover_delay: float = 3.0,
        menu_delay: float = 60.0,
        scene_fade_speed: float = 60,
        menu_fade_speed: float = 200,
        menu_x_frac: float = 0.5,
        menu_y_frac: float = 0.5,
        menu_x_margin: int = 0,
        parchment_scale: float = 0.45,
        stone_scale: float = 0.49,
        btn_scale: float = 0.7,
        btn_spacing: int = 85,
        btn_y_offset: int = -60,
        btn_size: str = "medium",
    ):
        super().__init__(manager)
        self.width = pg.display.get_surface().get_width()
        self.height = pg.display.get_surface().get_height()

        # Store configurable timing
        self._voiceover_delay = voiceover_delay
        self._menu_delay = menu_delay
        self._scene_fade_speed = scene_fade_speed
        self._menu_fade_speed = menu_fade_speed

        self.font = AssetManager.get_font(
            "assets/Colorfiction_HandDrawnFonts/Colorfiction - Gothic - Regular.otf",
            50,
        )

        # ── Scene image ──────────────────────────────────────────────────────
        self.scene_image = pg.image.load("assets/scenes/intro_scene.jpg").convert()
        img_w, img_h = self.scene_image.get_size()
        scale = self.width / img_w
        self.scene_image = pg.transform.smoothscale(
            self.scene_image, (self.width, int(img_h * scale))
        )
        self.scene_rect = self.scene_image.get_rect(
            center=(self.width // 2, self.height // 2)
        )

        # ── Story paragraphs (kept for reference / future scroll) ────────────
        self.story_paragraphs = [
            "They promised us a golden age. Instead, they gave us the Blight. "
            "In the silence of the burning embers, I realized... prayer was no longer enough.",
            "",
            "",
            "",
            "Then, the heavens seemed to open. A voice like silk whispered a solution. "
            "'A life for a life,' he said. 'A debt to be paid in the currency of darkness.'",
            "",
            "The deal was simple. One thousand Extractions of the Blight. "
            "One thousand souls harvested. Then, and only then, would my village be restored. "
            "My soul was the collateral.",
            "",
            "When I took the scythe, I didn't feel power. I felt a void. "
            "The moment I touched the steel, the weight of the world shifted. "
            "The hunter had become the harvest.",
            "",
            "The Fabricator lied. The more I culled, the more I changed. "
            "I realized I wasn't saving my soul; I was being encased in a living tomb of my own sins.",
            "",
            "One down. Nine-hundred and ninety-nine to go. "
            "But with every swing of the blade, I forget the faces of the people I'm trying to save.",
            "",
            "The thousandth soul will be my end. My only hope now lies in the Sanctuary of the All-Knowing. "
            "I must find the Truth... before the Demon finds me.",
        ]

        # ── Voiceover state ──────────────────────────────────────────────────
        self.narration_channel = None
        self._vo_timer = 0.0
        self._vo_started = False

        # ── Fade & timing ────────────────────────────────────────────────────
        self.alpha = 0
        self.elapsed = 0.0
        self._menu_alpha = 0
        self._menu_wait_timer = 0.0
        self._scene_faded_in = False
        self._menu_ready = False

        # ── Parchment + stone boards ─────────────────────────────────────────
        raw_stone = AssetManager.get_texture(self._STONE_PATH)
        stone_w = int(self.width * stone_scale)
        stone_h = int(stone_w * (raw_stone.get_height() / raw_stone.get_width()))
        self._stone = pg.transform.smoothscale(raw_stone, (stone_w, stone_h))

        raw_parch = AssetManager.get_texture(self._PARCHMENT_PATH)
        parch_w = int(self.width * parchment_scale)
        parch_h = int(parch_w * (raw_parch.get_height() / raw_parch.get_width()))
        self._parchment = pg.transform.smoothscale(raw_parch, (parch_w, parch_h))

        # Position boards using fractional coordinates
        board_cx = int(self.width * menu_x_frac) + menu_x_margin
        board_cy = int(self.height * menu_y_frac)
        self._stone_rect = self._stone.get_rect(center=(board_cx, board_cy))
        self._parch_rect = self._parchment.get_rect(center=(board_cx, board_cy))

        # ── Menu buttons (stacked vertically on the parchment) ───────────────
        btn_x = board_cx
        btn_start_y = board_cy + btn_y_offset

        self._buttons = [
            UIButton(
                "New Game",
                x=btn_x,
                y=btn_start_y,
                size=btn_size,
                scale=btn_scale,
                on_click=self._on_new_game,
            ),
            UIButton(
                "Continue",
                x=btn_x,
                y=btn_start_y + btn_spacing,
                size=btn_size,
                scale=btn_scale,
                on_click=self._on_continue,
            ),
            UIButton(
                "Settings",
                x=btn_x,
                y=btn_start_y + btn_spacing * 2,
                size=btn_size,
                scale=btn_scale,
                on_click=self._on_settings,
            ),
        ]

        # ── Settings placeholder banner ──────────────────────────────────────
        self._settings_banner = NotificationBanner(
            scale=0.5, icon_scale=0.5, hold=1.5,
        )

        # ── Scene Highlighter ────────────────────────────────────────────────
        self._highlighter = SceneHighlighter(self.scene_rect)
        # Schedule: (time_in_seconds, section_index)
        # We start highlighting after voiceover_delay
        self._highlight_schedule = [
            (0.0, 0),   # Section 1
            (10.0, 1),   # Section 2
            (22.0, 2),  # Section 3
            (33.0, 3),  # Section 4
            (43.0, 4),  # Section 5
            (53.0, 5),  # Section 6
            (63.0, 6),  # Section 7
            (73.0, -1), # End highlight
        ]

    # ── Lifecycle ────────────────────────────────────────────────────────────

    def on_enter(self):
        self._vo_timer = 0.0
        self._vo_started = False

    def on_exit(self):
        if self.narration_channel:
            self.narration_channel.stop()

    # ── Button callbacks ─────────────────────────────────────────────────────

    def _on_new_game(self):
        from .transformation_cutscene import TransformationCutscene
        from .game_state import GameState

        self.manager.set(
            TransformationCutscene(
                self.manager,
                next_state_factory=lambda: GameState(self.manager),
            )
        )

    def _on_continue(self):
        # No checkpoints yet — button is present but does nothing
        pass

    def _on_settings(self):
        self._settings_banner.show("Coming Soon", notification="yellow")

    # ── Events ───────────────────────────────────────────────────────────────

    def handle_event(self, event):
        # Only accept button input once the menu is fully visible
        if self._scene_faded_in:
            for btn in self._buttons:
                btn.handle_event(event)

    # ── Update ───────────────────────────────────────────────────────────────

    def update(self, dt):
        dt_sec = dt / 1000.0
        self.elapsed += dt_sec

        # Fade in the scene image
        if self.alpha < 255:
            self.alpha = min(255, self.alpha + self._scene_fade_speed * dt_sec)
        else:
            self._scene_faded_in = True

        # Wait for menu_delay after scene is visible, then fade in menu
        if self._scene_faded_in and not self._menu_ready:
            self._menu_wait_timer += dt_sec
            if self._menu_wait_timer >= self._menu_delay:
                self._menu_ready = True

        if self._menu_ready and self._menu_alpha < 255:
            self._menu_alpha = min(
                255, self._menu_alpha + self._menu_fade_speed * dt_sec
            )

        # Delayed voiceover and highlight timer
        self._vo_timer += dt_sec
        if not self._vo_started:
            if self._vo_timer >= self._voiceover_delay:
                self._vo_started = True
                sound = AssetManager.get_sound(self._VOICEOVER_PATH)
                if sound:
                    self.narration_channel = sound.play()

        # Update highlighted section based on voiceover progress
        if self._vo_started:
            vo_elapsed = self._vo_timer - self._voiceover_delay
            active_idx = -1
            for t, idx in self._highlight_schedule:
                if vo_elapsed >= t:
                    active_idx = idx
                else:
                    break
            self._highlighter.set_active_section(active_idx)

        # Settings banner
        self._settings_banner.update(dt)

    # ── Draw ─────────────────────────────────────────────────────────────────

    def draw(self, surface):
        surface.fill((0, 0, 0))

        # Scene image with fade-in
        if self.alpha >= 255:
            surface.blit(self.scene_image, self.scene_rect)
        else:
            temp = self.scene_image.copy()
            temp.set_alpha(int(self.alpha))
            surface.blit(temp, self.scene_rect)

        # Spotlight highlight
        if self._scene_faded_in:
            self._highlighter.draw(surface)

        # Parchment menu (fades in after delay)
        if self._menu_ready:
            alpha = int(self._menu_alpha)

            # Stone (behind parchment)
            self._stone.set_alpha(alpha)
            surface.blit(self._stone, self._stone_rect)
            self._stone.set_alpha(255)

            # Parchment
            self._parchment.set_alpha(alpha)
            surface.blit(self._parchment, self._parch_rect)
            self._parchment.set_alpha(255)

            # Buttons (only draw when menu is mostly visible)
            if self._menu_alpha > 180:
                for btn in self._buttons:
                    btn.draw(surface)

        # Settings banner (topmost)
        self._settings_banner.draw(surface)
