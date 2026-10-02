import pygame as pg
from typing import Dict, Any, Optional, Callable
from v3x_zulfiqar_gideon import AssetManager, UITheme


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

        # Text animation states
        self._full_text: str = ""
        self._displayed_text: str = ""
        self._char_index: int = 0
        self._char_timer: float = 0.0
        self._CHAR_SPEED_SEC: float = 0.025

        # Surface & dimension caching
        self._width: int = 1280
        self._height: int = 720
        self._vignette_surface: Optional[pg.Surface] = None
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
        
        self._avatar_surface = None
        avatar_path = narrative_event.get("avatar_sprite")
        if avatar_path:
            # We assume it's a directory of frames or a single image. Try loading a single image first.
            try:
                # If it's a directory like 'assets/Agis', we might need to load the first frame.
                frames = AssetManager.get_animation_frames(avatar_path)
                if frames:
                    self._avatar_surface = pg.transform.smoothscale(frames[0], (int(frames[0].get_width() * 3.5), int(frames[0].get_height() * 3.5)))
            except Exception:
                pass

        self.is_active = True

    def deactivate(self) -> None:
        """Dismiss overlay and restore full game speed."""
        self.is_active = False
        self._current_event = None
        self._on_choice_selected = None
        self._avatar_surface = None

    def handle_event(self, event: pg.event.Event) -> bool:
        """Handle keypresses [1] or [2] to select story choice."""
        if not self.is_active or not self._current_event:
            return False

        if event.type == pg.KEYDOWN:
            if event.key in (pg.K_1, pg.K_KP1):
                self._select_option(1)
                return True
            elif event.key in (pg.K_2, pg.K_KP2):
                self._select_option(2)
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
        """Update typewriter text animation."""
        if not self.is_active or self._char_index >= len(self._full_text):
            return

        self._char_timer += dt
        while self._char_timer >= self._CHAR_SPEED_SEC and self._char_index < len(self._full_text):
            self._char_timer -= self._CHAR_SPEED_SEC
            self._char_index += 1
            self._displayed_text = self._full_text[:self._char_index]

    def draw(self, surface: pg.Surface) -> None:
        """Render dark vignette and floating bottom dialogue box."""
        if not self.is_active or not self._current_event:
            return

        # 1. Draw radial vignette
        if self._vignette_surface:
            surface.blit(self._vignette_surface, (0, 0))

        # 1.5 Draw Avatar Sprite centered in the void
        if getattr(self, "_avatar_surface", None):
            av_x = (self._width - self._avatar_surface.get_width()) // 2
            av_y = (self._height - self._avatar_surface.get_height()) // 3
            surface.blit(self._avatar_surface, (av_x, av_y))

        # 2. Modern UI Dialogue Panel Base
        card_w = int(self._width * 0.85)
        card_h = 170
        card_x = (self._width - card_w) // 2
        card_y = self._height - card_h - 30

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
        speaker = str(self._current_event.get("speaker_name", "Kimi Narrative Director"))
        font_title = AssetManager.get_font(None, 24)
        speaker_surf = font_title.render(speaker, True, (255, 220, 100))
        # Add a subtle drop shadow to the speaker text
        speaker_shadow = font_title.render(speaker, True, (0, 0, 0))
        surface.blit(speaker_shadow, (card_x + 27, card_y + 17))
        surface.blit(speaker_surf, (card_x + 25, card_y + 15))
        
        # Separator line under speaker
        pg.draw.line(surface, (80, 75, 70), (card_x + 25, card_y + 45), (card_x + card_w - 25, card_y + 45), 1)

        # 4. Draw Typewriter Dialogue Text (Crisp, High Contrast)
        font_body = AssetManager.get_font(None, 20)
        dialogue_surf = font_body.render(self._displayed_text, True, (240, 240, 245))
        surface.blit(dialogue_surf, (card_x + 25, card_y + 60))

        # 5. Draw Modern Interactive Choice Buttons
        opt1 = str(self._current_event.get("option_1_label", "[1] Choice 1"))
        opt2 = str(self._current_event.get("option_2_label", "[2] Choice 2"))

        font_choice = AssetManager.get_font(None, 18)
        
        # Button 1 (Embrace / Affirmative) - Pill Shape
        btn1_w = font_choice.size(opt1)[0] + 40
        btn1_rect = pg.Rect(card_x + 25, card_y + 120, btn1_w, 32)
        pg.draw.rect(surface, (30, 50, 40, 230), btn1_rect, border_radius=16)
        pg.draw.rect(surface, (80, 200, 100), btn1_rect, width=1, border_radius=16)
        opt1_surf = font_choice.render(opt1, True, (160, 240, 160))
        surface.blit(opt1_surf, (card_x + 45, card_y + 127))

        # Button 2 (Reject / Negative) - Pill Shape
        btn2_w = font_choice.size(opt2)[0] + 40
        btn2_rect = pg.Rect(card_x + btn1_w + 40, card_y + 120, btn2_w, 32)
        pg.draw.rect(surface, (50, 25, 30, 230), btn2_rect, border_radius=16)
        pg.draw.rect(surface, (220, 80, 80), btn2_rect, width=1, border_radius=16)
        opt2_surf = font_choice.render(opt2, True, (240, 150, 150))
        surface.blit(opt2_surf, (card_x + btn1_w + 60, card_y + 127))
