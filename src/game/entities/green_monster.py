import pygame as pg
from src.my_engine.animation import Animation, Animator
from src.my_engine.asset_manager import AssetManager

class GreenMonster(pg.sprite.Sprite):
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
        self.speed = 200
        self.state = "WAITING" if start_delay > 0 else "ENTER" # WAITING, ENTER, IDLE_1, ATTACK_1, IDLE_2, ATTACK_2, EXIT
        self.state_timer = 0
        
    def set_scale(self, scale):
        self.scale = scale
        self.load_animations()
        # Update rect size but keep position
        old_midbottom = self.rect.midbottom
        self.image = self.animator.get_frame()
        self.rect = self.image.get_rect(midbottom=old_midbottom)

    def load_animations(self):
        base_path = "assets/graphics/green_monster"
        
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
        
        # Walk
        walk_frames = load_and_scale(f"{base_path}/walk")
        self.animator.add("walk", Animation(walk_frames, 0.1))
        
        # Attacks (No loop)
        atk1_frames = load_and_scale(f"{base_path}/1atk")
        self.animator.add("attack_1", Animation(atk1_frames, 0.15, loop=False)) # Slower attack
        
        atk2_frames = load_and_scale(f"{base_path}/2atk")
        self.animator.add("attack_2", Animation(atk2_frames, 0.15, loop=False)) # Slower attack
        
        self.animator.set("walk")

    def update(self, dt):
        dt_sec = dt / 1000.0
        
        if self.state == "WAITING":
            self.state_timer += dt_sec
            if self.state_timer >= self.start_delay:
                self.state = "ENTER"
                self.state_timer = 0
        
        elif self.state == "ENTER":
            # Run to center
            self.rect.x += self.speed * dt_sec
            self.animator.set("walk")
            self.animator.flip_x = False
            
            if self.rect.centerx >= self.screen_width // 2:
                self.state = "IDLE_1"
                self.state_timer = 0
                self.animator.set("idle")
                
        elif self.state == "IDLE_1":
            self.state_timer += dt_sec
            if self.state_timer >= 0.5: # Wait 0.5s
                self.state = "ATTACK_1"
                self.animator.set("attack_1")
    
        elif self.state == "ATTACK_1":
            if self.animator.current_animation.finished:
                self.state = "IDLE_2"
                self.state_timer = 0
                self.animator.set("idle")
                
        elif self.state == "IDLE_2":
            self.state_timer += dt_sec
            if self.state_timer >= 0.2: # Wait 0.2s
                self.state = "ATTACK_2"
                self.animator.set("attack_2")
                
        elif self.state == "ATTACK_2":
            if self.animator.current_animation.finished:
                self.state = "EXIT"
                self.animator.set("walk")
                
        elif self.state == "EXIT":
            # Run off screen
            self.rect.x += self.speed * dt_sec
            self.animator.set("walk")
            
            # Optional: Reset or disappear when off screen
            if self.rect.left > self.screen_width:
                # Could reset to loop the sequence or just stay off screen
                # For now, let's loop it for testing/interest
                self.rect.right = 0
                self.state = "ENTER"
            
        self.animator.update(dt_sec)
        self.image = self.animator.get_frame()
        
    def draw(self, surface):
        surface.blit(self.image, self.rect)
