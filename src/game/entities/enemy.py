import pygame as pg
import random
import math
from src.my_engine.ecs import Entity
from src.my_engine.asset_manager import AssetManager

class Enemy(Entity):
    """
    Base class for all enemy entities in the game.
    Handles common enemy behaviors like movement, animation, and collision.
    """
    def __init__(self):
        # Initialize without image first, we'll set it manually
        super().__init__(0, 0)
        
        # Animation frames for the enemy
        self.fly_frames = []
        
        try:
            # Load and prepare animation frames for the enemy
            for i in range(7):
                path = f"assets/graphics/bat/running/bat_running_{i}.png"
                frame = AssetManager.get_texture(path)
                original_size = frame.get_size()
                
                # Randomize size for variety
                size_multiplier = 1.5 + random.random()
                scaled_size = (int(original_size[0] * size_multiplier), 
                             int(original_size[1] * size_multiplier))
                
                # Scale and prepare the frame
                scaled_frame = pg.transform.scale(frame, scaled_size)
                flipped_frame = pg.transform.flip(scaled_frame, False, False)
                self.fly_frames.append(flipped_frame)
        except Exception as e:
            print(f"Error loading bat animation: {e}")
            # Fallback to a simple surface if loading fails
            self.fly_frames = [pg.Surface((50, 50), pg.SRCALPHA) for _ in range(7)]
        
        # Animation state
        self.current_frames = self.fly_frames
        self.animation_index = 0
        self.image = self.current_frames[self.animation_index]
        
        # Movement properties
        self.speed = -2 - random.random() * 2  # Random speed between -2 and -4
        self.y_base = 0                        # Base Y position for sine wave movement
        self.y_amplitude = 20                  # Height of the sine wave
        self.y_frequency = 0.05               # Speed of the sine wave
        self.time = 0                          # Timer for sine wave calculation
        
        # Setup rectangle and collision
        self.rect = self.image.get_rect()
        self.reduce_hitbox(20, 20)  # Make hitbox smaller than sprite for better gameplay

    def update(self, dt=None, scroll_speed=0):
        """
        Update enemy state each frame.
        
        Args:
            dt: Delta time since last update (unused in base implementation)
            scroll_speed: How fast the world is scrolling to the left
        """
        # Apply scrolling (move left with the world)
        self.rect.x -= scroll_speed
        
        # Move enemy based on its speed
        self.rect.x += self.speed
        
        # Update sine wave movement for floating effect
        self.time += 1
        self.rect.y = self.y_base + self.y_amplitude * math.sin(self.y_frequency * self.time)
        
        # Update animation frame
        self.animation_index += 0.15  # Controls animation speed
        if self.animation_index >= len(self.current_frames):
            self.animation_index = 0
        self.image = self.current_frames[int(self.animation_index)]
        
        # Remove if off-screen to the left
        if self.rect.right < 0:
            self.kill()
            
        super().update(dt)  # Call parent class update
