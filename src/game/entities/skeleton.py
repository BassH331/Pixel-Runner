import pygame as pg
import random
from src.my_engine.ecs import Entity
from src.my_engine.asset_manager import AssetManager

class Skeleton(Entity):
    def __init__(self, x, y, player):
        super().__init__(x, y)
        self.player = player
        
        # Load Animations
        self.idle_frames = self._load_frames("assets/skeleton/Skeleton_01_White_Idle/skeleton-idle_{}.png", 8)
        self.walk_frames = self._load_frames("assets/skeleton/Skeleton_01_White_Walk/skeleton-walk_{:02d}.png", 10)
        self.attack_frames = self._load_frames("assets/skeleton/Skeleton_01_White_Attack1/skeleton-atk2_{:02d}.png", 10)
        self.attack2_frames = self._load_frames("assets/skeleton/Skeleton_01_White_Attack2/skeleton-atk1_{}.png", 9)
        self.hurt_frames = self._load_frames("assets/skeleton/Skeleton_01_White_Hurt/skeleton-hurt_{}.png", 5)
        self.death_frames = self._load_frames("assets/skeleton/Skeleton_01_White_Die/skeleton-death_{:02d}.png", 13)
        
        self.current_frames = self.idle_frames
        self.animation_index = 0
        self.image = self.current_frames[self.animation_index]
        self.rect = self.image.get_rect(midbottom=(x, y))
        
        # Hitbox adjustment (make it a bit smaller than the sprite)
        self.reduce_hitbox(40, 20, align='bottom')
        
        # AI Stats
        self.speed = 2.5
        self.detection_range = 1000
        self.attack_range = 60
        self.state = "IDLE" # IDLE, CHASE, ATTACK, HURT, DEATH
        self.facing_left = True
        self.gravity = 0
        self.ground_y = pg.display.Info().current_h - 34 # Match player ground check
        self.health = 2
        
    def _load_frames(self, path_pattern, count):
        frames = []
        for i in range(count):
            path = path_pattern.format(i)
            frame = AssetManager.get_texture(path)
            # Scale up a bit if needed, or keep original. 
            # Skeleton assets look small (~32x32?), let's scale by 2 for now to match game style
            original_size = frame.get_size()
            scaled_size = (original_size[0] * 2, original_size[1] * 2)
            scaled_frame = pg.transform.scale(frame, scaled_size)
            frames.append(scaled_frame)
        return frames

    def update(self, dt=None, scroll_speed=0):
        self.rect.x -= scroll_speed
        self.apply_gravity()
        self.ai_logic()
        self.animate()
        super().update(dt)
        
    def take_damage(self):
        if self.state in ["HURT", "DEATH"]:
            return
            
        self.health -= 1
        if self.health <= 0:
            self.state = "DEATH"
        else:
            self.state = "HURT"
        self.animation_index = 0
        
    def ai_logic(self):
        if not self.player or self.state in ["HURT", "DEATH"]:
            return
            
        player_rect = self.player.sprite.rect
        dist_x = abs(self.rect.centerx - player_rect.centerx)
        dist_y = abs(self.rect.centery - player_rect.centery)
        
        # Simple state machine
        
        if self.state == "ATTACK":
            # If attacking, wait for animation to finish (handled in animate)
            pass
        else:
            if dist_x < self.attack_range and dist_y < 100:
                self.state = "ATTACK"
                self.animation_index = 0
                # Randomize attack
                if random.random() > 0.5:
                    self.current_frames = self.attack_frames
                else:
                    self.current_frames = self.attack2_frames
            elif dist_x < self.detection_range and dist_y < 100:
                if self.state != "CHASE":
                     pass
                self.state = "CHASE"
            else:
                self.state = "IDLE"
                
        # Behavior
        if self.state == "CHASE":
            if self.rect.centerx > player_rect.centerx:
                self.rect.x -= self.speed
                self.facing_left = True
            else:
                self.rect.x += self.speed
                self.facing_left = False

    def apply_gravity(self):
        self.gravity += 1
        self.rect.y += self.gravity
        if self.rect.bottom >= self.ground_y:
            self.rect.bottom = self.ground_y
            self.gravity = 0
                
    def animate(self):
        if self.state == "DEATH":
            self.current_frames = self.death_frames
            self.animation_index += 0.15
            if self.animation_index >= len(self.current_frames):
                self.kill() # Remove from groups
                return
        elif self.state == "HURT":
            self.current_frames = self.hurt_frames
            self.animation_index += 0.15
            if self.animation_index >= len(self.current_frames):
                self.state = "IDLE"
                self.animation_index = 0
        elif self.state == "ATTACK":
            self.animation_index += 0.15
            if self.animation_index >= len(self.current_frames):
                self.animation_index = 0
                self.state = "IDLE" # Return to idle after attack
                self.current_frames = self.idle_frames
        elif self.state == "CHASE":
            self.current_frames = self.walk_frames
            self.animation_index += 0.15
            if self.animation_index >= len(self.current_frames):
                self.animation_index = 0
        else: # IDLE
            self.current_frames = self.idle_frames
            self.animation_index += 0.1
            if self.animation_index >= len(self.current_frames):
                self.animation_index = 0
                
        if int(self.animation_index) < len(self.current_frames):
            self.image = self.current_frames[int(self.animation_index)]
            if self.facing_left:
                self.image = pg.transform.flip(self.image, True, False)
