import pygame as pg
from src.my_engine.animation import Animation, Animator
from src.my_engine.asset_manager import AssetManager

class Bat(pg.sprite.Sprite):
    def __init__(self, x, y, screen_width, scale=1.0, start_delay=0.0):
        super().__init__()
        self.animator = Animator()
        self.scale = scale
        self.screen_width = screen_width
        self.start_delay = start_delay
        self.load_animations()
        
        self.image = self.animator.get_frame()
        self.rect = self.image.get_rect(midbottom=(x, y))
        
        # Movement & State
        self.speed = 250 # Faster than ground monsters
        self.state = "WAITING" if start_delay > 0 else "ENTER" # WAITING, ENTER, IDLE, ATTACK, EXIT
        self.state_timer = 0
        self.start_x = x
        
    def set_scale(self, scale):
        self.scale = scale
        self.load_animations()
        # Update rect size but keep position
        old_midbottom = self.rect.midbottom
        self.image = self.animator.get_frame()
        self.rect = self.image.get_rect(midbottom=old_midbottom)

    def load_animations(self):
        base_path = "assets/graphics/bat"
        
        # Helper to scale frames
        def load_and_scale(path):
            frames = AssetManager.get_animation_frames(path)
            if self.scale != 1.0:
                scaled_frames = []
                for frame in frames:
                    new_size = (int(frame.get_width() * self.scale), int(frame.get_height() * self.scale))
                    scaled_frames.append(pg.transform.scale(frame, new_size))
                return scaled_frames
            return frames
        
        # Idle
        idle_frames = load_and_scale(f"{base_path}/idle")
        self.animator.add("idle", Animation(idle_frames, 0.1))
        
        # Fly (using running assets)
        fly_frames = load_and_scale(f"{base_path}/running")
        self.animator.add("fly", Animation(fly_frames, 0.1))
        
        # Attack (No loop)
        atk_frames = load_and_scale(f"{base_path}/attacking")
        self.animator.add("attack", Animation(atk_frames, 0.1, loop=False))
        
        self.animator.set("fly")

    def update(self, dt):
        dt_sec = dt / 1000.0
        
        if self.state == "WAITING":
            self.state_timer += dt_sec
            if self.state_timer >= self.start_delay:
                self.state = "ENTER"
                self.state_timer = 0
                
        elif self.state == "ENTER":
            # Fly to center from left
            self.rect.x += self.speed * dt_sec
            self.animator.set("fly")
            self.animator.flip_x = True # Face right (flipped)
            
            if self.rect.centerx >= self.screen_width // 2:
                self.state = "IDLE"
                self.state_timer = 0
                self.animator.set("idle")
                
        elif self.state == "IDLE":
            self.state_timer += dt_sec
            if self.state_timer >= 0.5: # Wait 0.5s
                self.state = "ATTACK"
                self.animator.set("attack")

        elif self.state == "ATTACK":
            if self.animator.current_animation.finished:
                self.state = "EXIT"
                self.animator.set("fly")
                
        elif self.state == "EXIT":
            # Fly off screen to right
            self.rect.x += self.speed * dt_sec
            self.animator.set("fly")
            self.animator.flip_x = True # Face right (flipped)
            
            # Reset when off screen
            if self.rect.left > self.screen_width:
                self.rect.right = 0
                self.state = "ENTER"
            
        self.animator.update(dt_sec)
        self.image = self.animator.get_frame()
        
    def draw(self, surface):
        if self.state != "WAITING":
            surface.blit(self.image, self.rect)
