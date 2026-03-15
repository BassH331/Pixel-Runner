import pygame as pg
import random
import math
from enum import Enum
from v3x_zulfiqar_gideon.ecs import Actor
from v3x_zulfiqar_gideon.asset_manager import AssetManager

class EnemyState(Enum):
    FLY = 0

class Enemy(Actor):
    """
    Base class for all enemy entities in the game.
    Handles common enemy behaviors like movement, animation, and collision.
    """
    _fly_frames_cache: list[pg.Surface] | None = None

    def __init__(self):
        super().__init__(0, 0)
        
        # Load frames only once if not already cached
        if Enemy._fly_frames_cache is None:
            Enemy._fly_frames_cache = []
            try:
                for i in range(7):
                    path = f"assets/graphics/bat/running/bat_running_{i}.png"
                    frame = AssetManager.get_texture(path)
                    
                    # Use a fixed scale for performance (caching pre-scaled frames)
                    original_size = frame.get_size()
                    scaled_size = (int(original_size[0] * 2.0), int(original_size[1] * 2.0))
                    
                    scaled_frame = pg.transform.scale(frame, scaled_size)
                    Enemy._fly_frames_cache.append(scaled_frame)
            except Exception as e:
                print(f"Error loading bat animation: {e}")
                Enemy._fly_frames_cache = [pg.Surface((50, 50), pg.SRCALPHA) for _ in range(7)]
        
        # Use actor system
        self.animations = {EnemyState.FLY: Enemy._fly_frames_cache}
        self.set_state(EnemyState.FLY)
        
        # Movement properties
        self.speed = -2 - random.random() * 2
        self.y_base = 0
        self.y_amplitude = 20
        self.y_frequency = 0.05
        self.time = 0
        
        # Setup rectangle
        self.rect = self.image.get_rect()
        self.reduce_hitbox(20, 20)

    def update(self, dt=None, scroll_speed=0):
        """
        Update enemy state each frame.
        """
        if dt is None: dt = 1.0/60.0
        
        # Apply scrolling (move left with the world)
        self.rect.x -= scroll_speed
        
        # Move enemy based on its speed
        self.rect.x += self.speed
        
        # Update sine wave movement for floating effect
        self.time += 1
        self.rect.y = self.y_base + self.y_amplitude * math.sin(self.y_frequency * self.time)
        
        # Remove if off-screen to the left
        if self.rect.right < 0:
            self.kill()
            
        super().update(dt)  # Actor handles animation and base components
