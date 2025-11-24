import pygame as pg
import random
import math
from src.my_engine.ecs import Entity
from src.my_engine.asset_manager import AssetManager

class Enemy(Entity):
    def __init__(self):
        # Initialize without image first, we'll set it manually
        super().__init__(0, 0)
        self.fly_frames = []
        try:
            for i in range(7):
                path = f"assets/graphics/bat/running/bat_running_{i}.png"
                frame = AssetManager.get_texture(path)
                original_size = frame.get_size()
                size_multiplier = 1.5 + random.random()
                scaled_size = (int(original_size[0] * size_multiplier), int(original_size[1] * size_multiplier))
                scaled_frame = pg.transform.scale(frame, scaled_size)
                flipped_frame = pg.transform.flip(scaled_frame, False, False)
                self.fly_frames.append(flipped_frame)
        except Exception as e:
            print(f"Error loading bat animation: {e}")
            self.fly_frames = [pg.Surface((50, 50), pg.SRCALPHA) for _ in range(7)]
        
        self.current_frames = self.fly_frames
        self.animation_index = 0
        self.image = self.current_frames[self.animation_index]
        self.speed = -2 - random.random() * 2
        self.y_base = 0
        self.y_amplitude = 20
        self.y_frequency = 0.05
        self.time = 0
        self.rect = self.image.get_rect()
        # Reduce hitbox size: 100px narrower, 100px shorter than the image
        self.reduce_hitbox(100, 100)

    def update(self, dt=None):
        self.rect.x += self.speed
        self.time += 1
        self.rect.y = self.y_base + self.y_amplitude * math.sin(self.y_frequency * self.time)
        self.animation_index += 0.15
        if self.animation_index >= len(self.current_frames):
            self.animation_index = 0
        self.image = self.current_frames[int(self.animation_index)]
        if self.rect.right < 0:
            self.kill()
        super().update(dt)
