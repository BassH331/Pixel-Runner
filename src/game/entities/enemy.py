import pygame as pg
import random
import math
from enum import Enum
from v3x_zulfiqar_gideon import Actor, AssetManager
from .hitbox_registry import HitboxRegistry

class EnemyState(Enum):
    FLY = 0

class Enemy(Actor):
    """
    Base class for all enemy entities in the game.
    Handles common enemy behaviors like movement, animation, and collision.
    """
    _fly_frames_caches: dict[float, list[pg.Surface]] = {}

    def __init__(self):
        super().__init__(0, 0)
        
        # Load margins and scale
        margins = HitboxRegistry.get_margins("enemy")
        scale = margins.scale
        
        # Load frames only once per scale if not already cached
        if scale not in Enemy._fly_frames_caches:
            cache = []
            try:
                for i in range(7):
                    path = f"assets/graphics/bat/running/bat_running_{i}.png"
                    frame = AssetManager.get_texture(path)
                    
                    original_size = frame.get_size()
                    scaled_size = (int(original_size[0] * scale), int(original_size[1] * scale))
                    
                    scaled_frame = pg.transform.scale(frame, scaled_size)
                    cache.append(scaled_frame)
            except Exception as e:
                print(f"Error loading bat animation for scale {scale}: {e}")
                cache = [pg.Surface((int(25 * scale), int(25 * scale)), pg.SRCALPHA) for _ in range(7)]
            Enemy._fly_frames_caches[scale] = cache
        
        # Use actor system
        self.animations = {EnemyState.FLY: Enemy._fly_frames_caches[scale]}
        self.set_state(EnemyState.FLY)
        
        # Movement properties
        self.speed = -2 - random.random() * 2
        self.y_base = 0
        self.y_amplitude = 20
        self.y_frequency = 0.05
        self.time = 0
        
        # Setup rectangle
        if self.state in self.animations:
            self.image = self.animations[self.state][0]
        self.rect = self.image.get_rect()
        # Reduce hitbox using the margins loaded from the HitboxRegistry
        margins = HitboxRegistry.get_margins("enemy")
        self.adjust_hitbox_sides(left=margins.left, right=margins.right, top=margins.top, bottom=margins.bottom)

    def take_damage(self, amount: float, knockback: tuple[float, float] | None = None) -> None:
        """Apply damage to this enemy. Override in subclasses."""
        pass

    def update(self, dt=None, scroll_speed=0):
        """
        Update enemy state each frame.
        """
        if dt is None: dt = 1.0/60.0
        
        # Apply scrolling (move left with the world)
        self.rect.x -= scroll_speed
        
        # Move enemy based on its speed
        self.rect.x += int(self.speed)
        
        # Update sine wave movement for floating effect
        self.time += 1
        self.rect.y = int(self.y_base + self.y_amplitude * math.sin(self.y_frequency * self.time))
        
        # Remove if off-screen to the left
        if self.rect.right < 0:
            self.kill()
            
        super().update(dt)  # Actor handles animation and base components
