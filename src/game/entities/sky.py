import pygame as pg
from src.my_engine.asset_manager import AssetManager

class Sky:
    def __init__(self, screen_width, screen_height):
        self.width = screen_width
        self.height = screen_height
        
        # Load and scale layers
        base_path = "assets/graphics/Clouds 3"
        self.layers = []
        for i in range(1, 5):
            img = AssetManager.get_texture(f"{base_path}/{i}.png")
            scaled_img = pg.transform.scale(img, (screen_width, screen_height))
            self.layers.append(scaled_img)
            
        # Scrolling positions for layers 3 and 4
        # Layer index 2 is file 3.png
        # Layer index 3 is file 4.png
        self.scroll_x_3 = 0
        self.scroll_x_4 = 0
        
        self.speed_3 = 20 # Pixels per second
        self.speed_4 = 40 # Pixels per second
        
    def update(self, dt):
        dt_sec = dt / 1000.0
        
        # Scroll layer 3 (Right to Left)
        self.scroll_x_3 -= self.speed_3 * dt_sec
        if self.scroll_x_3 <= -self.width:
            self.scroll_x_3 = 0
            
        # Scroll layer 4 (Right to Left)
        self.scroll_x_4 -= self.speed_4 * dt_sec
        if self.scroll_x_4 <= -self.width:
            self.scroll_x_4 = 0
            
    def draw(self, surface):
        # Draw static layers (1 & 2)
        surface.blit(self.layers[0], (0, 0))
        surface.blit(self.layers[1], (0, 0))
        
        # Draw scrolling layer 3
        surface.blit(self.layers[2], (self.scroll_x_3, 0))
        surface.blit(self.layers[2], (self.scroll_x_3 + self.width, 0))
        
        # Draw scrolling layer 4
        surface.blit(self.layers[3], (self.scroll_x_4, 0))
        surface.blit(self.layers[3], (self.scroll_x_4 + self.width, 0))
