import os
import pygame as pg
from typing import Dict, Any, Optional, Callable, List
from v3x_zulfiqar_gideon import AssetManager, UITheme
from src.game.systems.custom_events import Speaker


class CinematicNarrativeOverlay:
    """In-game slow-motion cinematic narrative overlay component.
    
    When activated by Kimi AI Director or key story events, combat slows to
    10% speed while a dark radial vignette and floating dialogue box appear with
    typewriter dialogue text and interactive keypress choices ([1] or [2]).
    """

    def __init__(self):
        self.is_active: bool = False
        self._current_event: Optional[Dict[str, Any]] = None
        self._on_choice_selected: Optional[Callable[[Dict[str, Any]], None]] = None
        self._speaker: Optional[Speaker] = None

        # Text animation states
        self._full_text: str = ""
        self._displayed_text: str = ""
        self._char_index: int = 0
        self._char_timer: float = 0.0
        self._CHAR_SPEED_SEC: float = 0.025

        # Avatar animation
        self._avatar_frames: List[pg.Surface] = []
        self._avatar_frame_idx: int = 0
        self._avatar_frame_timer: float = 0.0
        self._AVATAR_FRAME_SPEED: float = 0.28  # seconds per frame (calm, ominous demon pacing)

        # Surface & dimension caching
        self._width: int = 1280
        self._height: int = 720
        self._vignette_surface: Optional[pg.Surface] = None
        self._btn1_rect: Optional[pg.Rect] = None
        self._btn2_rect: Optional[pg.Rect] = None
        self._rebuild_vignette()

    def _rebuild_vignette(self) -> None:
        """Create a completely black void overlay."""
        surface = pg.display.get_surface()
        if surface:
            self._width = surface.get_width()
            self._height = surface.get_height()

        self._vignette_surface = pg.Surface((self._width, self._height), pg.SRCALPHA)
        # The user requested a completely black void
        self._vignette_surface.fill((0, 0, 0, 255))

    def activate(self, narrative_event: Dict[str, Any], on_choice_selected: Optional[Callable[[Dict[str, Any]], None]] = None) -> None:
        """Trigger slow-motion cinematic overlay with Kimi narrative event dictionary."""
        self._current_event = narrative_event
        self._on_choice_selected = on_choice_selected
        self._full_text = narrative_event.get("dialogue_text", "")
        self._displayed_text = ""
        self._char_index = 0
        self._char_timer = 0.0
        self._avatar_frame_idx = 0
        self._avatar_frame_timer = 0.0
        
        self._avatar_frames = []
        avatar_path = narrative_event.get("avatar_sprite")
        if avatar_path:
            try:
                # Special handling for Agis: load all Agis_XX.png files in sorted order
                agis_dir = avatar_path  # e.g. 'assets/Agis'
                individual_pngs = sorted(
                    [f for f in os.listdir(agis_dir) if f.lower().endswith(".png") and not os.path.isdir(os.path.join(agis_dir, f))]
                )
                if individual_pngs:
                    scale = 3.5
                    for fname in individual_pngs:
                        img = pg.image.load(os.path.join(agis_dir, fname)).convert_alpha()
                        w = int(img.get_width() * scale)
                        h = int(img.get_height() * scale)
                        self._avatar_frames.append(pg.transform.smoothscale(img, (w, h)))
                else:
                    # Fallback: use AssetManager
                    frames = AssetManager.get_animation_frames(avatar_path)
                    if frames:
                        scale = 3.5
                        for f in frames:
                            self._avatar_frames.append(pg.transform.smoothscale(f, (int(f.get_width() * scale), int(f.get_height() * scale))))
            except Exception as e:
                print(f"[CinematicOverlay] Avatar load error: {e}")

        self.is_active = True

    def show_bark(self, text: str, speaker: Optional[Speaker] = None) -> None:
        """Show a whisperer bark line via the overlay.

        Creates a minimal narrative event dict so the existing typewriter
        and panel machinery runs unchanged.  No avatar is loaded and the
        dismiss prompt reads "[ ] Continue" so the player can skip.

        Args:
            text:    The bark text to display with typewriter animation.
            speaker: Optional ``Speaker`` enum value that controls the
                     overlay tint and label colour.
        """
        self._speaker = speaker
        event: Dict[str, Any] = {
            "dialogue_text": text,
            "option_1_label": "[SPACE] Continue",
        }
        self.activate(event)

    def deactivate(self) -> None:
        """Dismiss overlay and restore full game speed."""
        self.is_active = False
        self._current_event = None
        self._on_choice_selected = None
        self._speaker = None
        self._avatar_frames = []
        self._avatar_frame_idx = 0

    def handle_event(self, event: pg.event.Event) -> bool:
        """Handle keypresses [1], [2], SPACE, ENTER, ESC, or mouse clicks to select story choice."""
        if not self.is_active or not self._current_event:
            return False

        if event.type == pg.KEYDOWN:
            if event.key in (pg.K_1, pg.K_KP1, pg.K_RETURN, pg.K_SPACE, pg.K_ESCAPE):
                self._select_option(1)
                return True
            elif event.key in (pg.K_2, pg.K_KP2) and "option_2_label" in self._current_event:
                self._select_option(2)
                return True
        elif event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
            mpos = event.pos
            if self._btn2_rect and self._btn2_rect.collidepoint(mpos):
                self._select_option(2)
                return True
            elif self._btn1_rect and self._btn1_rect.collidepoint(mpos):
                self._select_option(1)
                return True
            elif "option_2_label" not in self._current_event:
                # In single-option monologue, clicking anywhere advances
                self._select_option(1)
                return True
        return False

    def _select_option(self, option_index: int) -> None:
        """Apply selected choice buff and deactivate overlay."""
        if not self._current_event:
            return

        buff_key = f"option_{option_index}_buff"
        buff_data = self._current_event.get(buff_key, {})
        
        if self._on_choice_selected:
            self._on_choice_selected(buff_data)

        self.deactivate()

    def update(self, dt: float) -> None:
        """Update typewriter text animation and avatar frame animation."""
        if not self.is_active:
            return

        # Typewriter effect
        if self._char_index < len(self._full_text):
            self._char_timer += dt
            while self._char_timer >= self._CHAR_SPEED_SEC and self._char_index < len(self._full_text):
                self._char_timer -= self._CHAR_SPEED_SEC
                self._char_index += 1
                self._displayed_text = self._full_text[:self._char_index]

        # Avatar frame cycling
        if len(self._avatar_frames) > 1:
            self._avatar_frame_timer += dt
            if self._avatar_frame_timer >= self._AVATAR_FRAME_SPEED:
                self._avatar_frame_timer -= self._AVATAR_FRAME_SPEED
                self._avatar_frame_idx = (self._avatar_frame_idx + 1) % len(self._avatar_frames)

    def draw(self, surface: pg.Surface) -> None:
        """Render dark vignette and floating bottom dialogue box."""
        if not self.is_active or not self._current_event:
            return

        # 1. Draw radial vignette — tinted per speaker when a bark is active
        if self._vignette_surface:
            if self._speaker is Speaker.ANDRAS:
                tint = pg.Surface((self._width, self._height), pg.SRCALPHA)
                tint.fill((60, 0, 10, 160))
                surface.blit(self._vignette_surface, (0, 0))
                surface.blit(tint, (0, 0))
            elif self._speaker is Speaker.MOON_KNIGHT:
                tint = pg.Surface((self._width, self._height), pg.SRCALPHA)
                tint.fill((10, 20, 60, 140))
                surface.blit(self._vignette_surface, (0, 0))
                surface.blit(tint, (0, 0))
            else:
                surface.blit(self._vignette_surface, (0, 0))

        # 1.5 Draw animated Avatar Sprite centered in the void
        if self._avatar_frames:
            frame = self._avatar_frames[self._avatar_frame_idx % len(self._avatar_frames)]
            av_x = (self._width - frame.get_width()) // 2
            av_y = (self._height - frame.get_height()) // 3
            surface.blit(frame, (av_x, av_y))

        # 2. Modern UI Dialogue Panel Base
        card_w = int(self._width * 0.85)
        card_h = 180
        card_x = (self._width - card_w) // 2
        card_y = self._height - card_h - 25

        # Background with a sleek dark glass look
        card_rect = pg.Rect(card_x, card_y, card_w, card_h)
        pg.draw.rect(surface, (15, 15, 20, 240), card_rect, border_radius=8)
        
        # Subtle inner highlight for 3D depth
        inner_rect = pg.Rect(card_x + 1, card_y + 1, card_w - 2, card_h - 2)
        pg.draw.rect(surface, (45, 45, 55, 180), inner_rect, width=1, border_radius=8)
        
        # Sleek accent border (Gold/Neon)
        pg.draw.rect(surface, (235, 190, 80), card_rect, width=2, border_radius=8)

        # Subtle top accent line (for modern flair)
        top_accent_rect = pg.Rect(card_x + 15, card_y, card_w - 30, 2)
        pg.draw.rect(surface, (255, 215, 110), top_accent_rect)

        # 3. Draw Speaker Tag (Modern Header)
        # When a whisperer bark is active, override the speaker label with a
        # small all-caps coloured label; otherwise use the event's speaker_name.
        if self._speaker is Speaker.ANDRAS:
            speaker_label = "ANDRAS"
            speaker_colour = (200, 30, 30)
        elif self._speaker is Speaker.MOON_KNIGHT:
            speaker_label = "MOON KNIGHT"
            speaker_colour = (120, 160, 220)
        else:
            speaker_label = str(self._current_event.get("speaker_name", "Kimi Narrative Director"))
            speaker_colour = (255, 220, 100)

        if self._speaker is not None:
            # Small all-caps whisperer label (11px) drawn above the standard header position
            font_whisper = AssetManager.get_font(None, 11)
            label_surf = font_whisper.render(speaker_label, True, speaker_colour)
            label_shadow = font_whisper.render(speaker_label, True, (0, 0, 0))
            surface.blit(label_shadow, (card_x + 27, card_y + 7))
            surface.blit(label_surf, (card_x + 25, card_y + 6))
            font_title = AssetManager.get_font(None, 24)
            # Render transparent placeholder for speaker_name slot so layout stays intact
            speaker_shadow_surf = font_title.render("", True, (0, 0, 0))
            surface.blit(speaker_shadow_surf, (card_x + 27, card_y + 17))
        else:
            font_title = AssetManager.get_font(None, 24)
            speaker_surf = font_title.render(speaker_label, True, speaker_colour)
            speaker_shadow_surf = font_title.render(speaker_label, True, (0, 0, 0))
            surface.blit(speaker_shadow_surf, (card_x + 27, card_y + 17))
            surface.blit(speaker_surf, (card_x + 25, card_y + 15))

        # Separator line under speaker
        pg.draw.line(surface, (80, 75, 70), (card_x + 25, card_y + 45), (card_x + card_w - 25, card_y + 45), 1)

        # 4. Draw Typewriter Dialogue Text with Word Wrap
        font_body = AssetManager.get_font(None, 20)
        max_line_width = card_w - 50
        words = self._displayed_text.split(" ")
        lines = []
        cur_line = ""
        for word in words:
            test_line = f"{cur_line} {word}".strip() if cur_line else word
            if font_body.size(test_line)[0] <= max_line_width:
                cur_line = test_line
            else:
                if cur_line:
                    lines.append(cur_line)
                cur_line = word
        if cur_line:
            lines.append(cur_line)

        line_y = card_y + 55
        for line in lines[:3]:
            d_surf = font_body.render(line, True, (240, 240, 245))
            surface.blit(d_surf, (card_x + 25, line_y))
            line_y += 22

        # 5. Draw Modern Interactive Choice Buttons
        opt1 = str(self._current_event.get("option_1_label", "[SPACE] Continue"))

        font_choice = AssetManager.get_font(None, 18)
        
        # Button 1 (Embrace / Affirmative / Continue) - Pill Shape
        btn1_w = font_choice.size(opt1)[0] + 40
        self._btn1_rect = pg.Rect(card_x + 25, card_y + 130, btn1_w, 34)
        pg.draw.rect(surface, (30, 50, 40, 230), self._btn1_rect, border_radius=17)
        pg.draw.rect(surface, (80, 200, 100), self._btn1_rect, width=1, border_radius=17)
        opt1_surf = font_choice.render(opt1, True, (160, 240, 160))
        surface.blit(opt1_surf, (card_x + 45, card_y + 137))

        # Button 2 (Reject / Negative) - Pill Shape (Only if option_2_label exists)
        if "option_2_label" in self._current_event:
            opt2 = str(self._current_event["option_2_label"])
            btn2_w = font_choice.size(opt2)[0] + 40
            self._btn2_rect = pg.Rect(card_x + btn1_w + 45, card_y + 130, btn2_w, 34)
            pg.draw.rect(surface, (50, 25, 30, 230), self._btn2_rect, border_radius=17)
            pg.draw.rect(surface, (220, 80, 80), self._btn2_rect, width=1, border_radius=17)
            opt2_surf = font_choice.render(opt2, True, (240, 150, 150))
            surface.blit(opt2_surf, (card_x + btn1_w + 65, card_y + 137))
        else:
            self._btn2_rect = None
