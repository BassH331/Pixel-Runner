import pygame as pg
from src.my_engine.state_machine import State
from src.my_engine.asset_manager import AssetManager
from src.my_engine.ui import Button

class StoryState(State):
    def __init__(self, manager):
        super().__init__(manager)
        self.width = pg.display.get_surface().get_width()
        self.height = pg.display.get_surface().get_height()
        self.font = AssetManager.get_font('assets/font/Pixeltype.ttf', 50)
        
        # Placeholder Text
        self.text_lines = [
            "Long ago, the world was full of light...",
            "But darkness has returned.",
            "You must run to save us all!",
            "",
            "(UI to be added by user)"
        ]
        
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
            on_click=self.start_game
        )
        
    def start_game(self):
        from .game_state import GameState
        self.manager.set(GameState(self.manager))
        
    def handle_event(self, event):
        self.continue_btn.handle_event(event)
        
    def update(self, dt):
        self.continue_btn.update(dt)
        
    def draw(self, surface):
        surface.fill((20, 20, 30)) # Dark background
        
        # Draw Text
        y = 100
        for line in self.text_lines:
            text_surf = self.font.render(line, False, (200, 200, 200))
            text_rect = text_surf.get_rect(center=(self.width // 2, y))
            surface.blit(text_surf, text_rect)
            y += 60
            
        self.continue_btn.draw(surface)
