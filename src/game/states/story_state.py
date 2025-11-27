import pygame as pg
from src.my_engine.state_machine import State
from src.my_engine.asset_manager import AssetManager
from src.my_engine.ui import Button
from src.my_engine.tts_manager import TTSManager
from src.game.entities.green_monster import GreenMonster
from src.game.entities.goblin import Goblin
from src.game.entities.bat import Bat

class StoryState(State):
    def __init__(self, manager):
        super().__init__(manager)
        self.width = pg.display.get_surface().get_width()
        self.height = pg.display.get_surface().get_height()
        self.font = AssetManager.get_font('assets/font/Pixeltype.ttf', 50)
        
        # Story Text
        self.text_lines = [
            "In the beginning, the Star-Fire illuminated the cosmos,",
            "bringing life and harmony to all worlds.",
            "",
            "But the Shadow King, envious of its brilliance,",
            "stole the Star-Fire and shattered it into fragments,",
            "casting the universe into eternal twilight.",
            "",
            "Darkness spread like a plague, consuming planets",
            "and corrupting the hearts of the innocent.",
            "",
            "You are the last Guardian.",
            "Chosen by the fading light,",
            "you must run through the corrupted lands,",
            "reclaim the Star-Fire fragments,",
            "and restore light to the galaxy.",
            "",
            "Run, Guardian. Run before the light is lost forever."
        ]
        
        # Generate Audio
        full_text = " ".join(self.text_lines)
        self.audio_path = "assets/audio/story_narration.mp3"
        TTSManager.generate_audio(full_text, self.audio_path)
        self.narration_channel = None
        
        # Scrolling
        self.scroll_y = self.height # Start at the bottom
        self.scroll_speed = 30 # Pixels per second
        
        # Monsters
        self.monster = GreenMonster(-100, self.height - 150, self.width, scale=3.0)
        self.bat = Bat(-100, self.height - 350, self.width, scale=3.0, start_delay=2.0)
        self.goblin = Goblin(-100, self.height - 50, self.width, scale=3.0, start_delay=4.0)
        
        # Continue Button
        # Using PlayBtn as placeholder for Continue
        btn_img = AssetManager.get_texture("assets/graphics/ui/PlayBtn.png")
        btn_hover = AssetManager.get_texture("assets/graphics/ui/PlayClick.png")
        
        self.continue_btn = Button(
            x=self.width - 150,
            y=self.height - 100,
            image=btn_img,
            hover_image=btn_hover,
            scale=1.0,
            size=(140, 70),
            anchor='center',
            on_click=self.start_game
        )
        
    def on_enter(self):
        # Play narration
        sound = AssetManager.get_sound(self.audio_path)
        if sound:
            self.narration_channel = sound.play()
            
    def on_exit(self):
        # Stop narration
        if self.narration_channel:
            self.narration_channel.stop()
        
    def start_game(self):
        from .game_state import GameState
        self.manager.set(GameState(self.manager))
        
    def handle_event(self, event):
        self.continue_btn.handle_event(event)
        
    def update(self, dt):
        self.continue_btn.update(dt)
        self.monster.update(dt)
        self.bat.update(dt)
        self.goblin.update(dt)
        
        # Scroll Text
        dt_sec = dt / 1000.0
        self.scroll_y -= self.scroll_speed * dt_sec # Move up
        
        # Reset if it goes too far (optional, or just stop)
        # if self.scroll_y > self.height:
        #     self.scroll_y = -len(self.text_lines) * 60
        
    def draw(self, surface):
        surface.fill((20, 20, 30)) # Dark background
        
        # Draw Text
        y = self.scroll_y
        for line in self.text_lines:
            text_surf = self.font.render(line, False, (200, 200, 200))
            text_rect = text_surf.get_rect(center=(self.width // 2, y))
            
            # Only draw if visible
            if -50 < y < self.height + 50:
                surface.blit(text_surf, text_rect)
            y += 60
            
        self.monster.draw(surface)
        self.bat.draw(surface)
        self.goblin.draw(surface)
        self.continue_btn.draw(surface)
