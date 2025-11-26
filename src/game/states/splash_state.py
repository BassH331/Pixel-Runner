import pygame as pg
from src.my_engine.state_machine import State
from src.my_engine.asset_manager import AssetManager
from src.game.states.main_menu_state import MainMenuState

class SplashState(State):
    def __init__(self, manager):
        super().__init__(manager)
        self.width = pg.display.get_surface().get_width()
        self.height = pg.display.get_surface().get_height()
        
        # Load Logo
        try:
            self.logo = AssetManager.get_texture("assets/graphics/Game_logo/Game Logo.png")
            # Scale logo if too big (e.g., max 80% width)
            logo_rect = self.logo.get_rect()
            if logo_rect.width > self.width * 0.8:
                scale = (self.width * 0.8) / logo_rect.width
                self.logo = pg.transform.scale_by(self.logo, scale)
            self.logo_rect = self.logo.get_rect(center=(self.width // 2, self.height // 2))
        except:
            print("Failed to load Game Logo.png")
            self.logo = None
            
        # Load Space Key Prompt
        try:
            self.space_key = AssetManager.get_texture("assets/graphics/ui/KEYS/SPACE.png")
            self.space_key = pg.transform.scale_by(self.space_key, 4.0) # Scale up a bit
            self.space_key_rect = self.space_key.get_rect(midbottom=(self.width // 2, self.height - 50))
        except:
            print("Failed to load SPACE.png")
            self.space_key = None

        # Animation
        self.alpha = 0
        self.fade_speed = 255 # Full fade in 1 second (approx)
        self.state = "FADE_IN" # FADE_IN, WAIT, FADE_OUT
        self.timer = 0
        self.wait_time = 1.0 # Seconds to wait at full opacity
        
        # Pre-load Main Menu (starts the thread)
        self.main_menu = MainMenuState(manager)
        
    def update(self, dt):
        dt_sec = dt / 1000.0
        
        # Animation Logic
        if self.state == "FADE_IN":
            self.alpha += self.fade_speed * dt_sec
            if self.alpha >= 255:
                self.alpha = 255
                self.state = "WAIT"
                
        elif self.state == "WAIT":
            # Wait for both timer AND loading to finish
            self.timer += dt_sec
            if self.timer >= self.wait_time and self.main_menu.loading_progress >= 1.0:
                self.state = "FADE_OUT"
                
        elif self.state == "FADE_OUT":
            self.alpha -= self.fade_speed * dt_sec
            if self.alpha <= 0:
                self.alpha = 0
                # Transition
                self.manager.set(self.main_menu)
                
        # Update Main Menu (for thread check if needed, though thread runs independently)
        # self.main_menu.update(dt) # Not needed as update only handles animation there
        
    def draw(self, surface):
        surface.fill((0, 0, 0))
        
        if self.logo:
            self.logo.set_alpha(int(self.alpha))
            surface.blit(self.logo, self.logo_rect)
            
        # Draw Loading Bar
        if self.main_menu.loading_progress < 1.0:
            bar_width = self.width * 0.6
            bar_height = 10
            bar_x = (self.width - bar_width) // 2
            bar_y = self.height - 50
            
            # Background
            pg.draw.rect(surface, (50, 50, 50), (bar_x, bar_y, bar_width, bar_height))
            # Fill
            fill_width = bar_width * self.main_menu.loading_progress
            pg.draw.rect(surface, (255, 255, 255), (bar_x, bar_y, fill_width, bar_height))
            
            # Draw Percentage Text
            percent = int(self.main_menu.loading_progress * 100)
            font = AssetManager.get_font('assets/font/Pixeltype.ttf', 30)
            text_surf = font.render(f"{percent}%", False, (255, 255, 255))
            text_rect = text_surf.get_rect(midbottom=(self.width // 2, bar_y - 10))
            surface.blit(text_surf, text_rect)
