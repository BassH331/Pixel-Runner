import pygame as pg
import random  # Changed import to full random module
import math

class Enemy(pg.sprite.Sprite):
    def __init__(self):
        super().__init__()
        self.fly_frames = []
        try:
            for i in range(7):
                frame = pg.image.load(f"Resources/graphics/bat/running/bat_running_{i}.png").convert_alpha()
                original_size = frame.get_size()
                size_multiplier = 1.5 + random.random()  # Use random.random()
                scaled_size = (int(original_size[0] * size_multiplier), int(original_size[1] * size_multiplier))
                scaled_frame = pg.transform.scale(frame, scaled_size)
                flipped_frame = pg.transform.flip(scaled_frame, False, False)
                self.fly_frames.append(flipped_frame)
        except FileNotFoundError as e:
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

    def update(self):
        self.rect.x += self.speed
        self.time += 1
        self.rect.y = self.y_base + self.y_amplitude * math.sin(self.y_frequency * self.time)
        self.animation_index += 0.15
        if self.animation_index >= len(self.current_frames):
            self.animation_index = 0
        self.image = self.current_frames[int(self.animation_index)]
        if self.rect.right < 0:
            self.kill()

class Goblin(pg.sprite.Sprite):
    def __init__(self, player, start_x, start_y):
        super().__init__()
        self.player = player
        self.health = 100
        self.max_health = 100
        self.is_alive = True
        self.state = "run"
        self.last_attack_time = 0
        self.attack_cooldown = 2000
        self.attack_range = 100
        self.detection_range = 1300
        self.speed = 5
        self.direction = -1 if player.rect.centerx < start_x else 1
        self.gravity = 0
        
        # Animation settings
        self.animations = {
            "idle": self.load_animation_frames("Resources/graphics/Goblin/Idle/", "idle_", 4),
            "run": self.load_animation_frames("Resources/graphics/Goblin/Run/", "goblin_", 8),
            "attack": self.load_animation_frames("Resources/graphics/Goblin/Attack/", "goblin_atk_", 8),
            "take_hit": self.load_animation_frames("Resources/graphics/Goblin/Take_hit/", "hit_", 4),
            "death": self.load_animation_frames("Resources/graphics/Goblin/Death/", "death_", 4)
        }
        self.animation_speeds = {
            "idle": 0.1,
            "run": 0.3,  # Increased for snappier run
            "attack": 0.4,  # Increased for sharper attack
            "take_hit": 0.2,
            "death": 0.2
        }
        self.current_frames = self.animations["run"]
        self.animation_index = 0
        self.image = self.current_frames[self.animation_index]
        self.rect = self.image.get_rect(bottomleft=(start_x, start_y))
        
        self.attack_damage = 10
        self.last_hit_time = 0
        self.hit_cooldown = 500
        self.attack_frame = 4
        self.attack_applied = False
        
        self.attack_sound = pg.mixer.Sound("Resources/audio/goblin_attack.mp3")
        self.hit_sound = pg.mixer.Sound("Resources/audio/goblin_hit.mp3")
        self.death_sound = pg.mixer.Sound("Resources/audio/goblin_death.mp3")
        
        self.run_bounce = 0
        self.attack_shake = 0
        self.attack_scale = 1.0  # For scale pulse

    def load_animation_frames(self, path, prefix, count):
        frames = []
        try:
            for i in range(count):
                frame_path = f"{path}{prefix}{i}.png"
                frame = pg.image.load(frame_path).convert_alpha()
                scaled_frame = pg.transform.scale(frame, (frame.get_width() * 2, frame.get_height() * 2))
                flipped_frame = pg.transform.flip(scaled_frame, True, False)
                frames.append(flipped_frame)
            print(f"Loaded {count} frames for {path}")
        except Exception as e:
            print(f"Error loading animation {path}: {e}")
            frames = [pg.Surface((50, 50), pg.SRCALPHA) for _ in range(count)]
        return frames
    
    def take_damage(self, amount):
        current_time = pg.time.get_ticks()
        if current_time - self.last_hit_time < self.hit_cooldown:
            return False
            
        self.health -= amount
        self.last_hit_time = current_time
        
        if self.health <= 0:
            self.health = 0
            self.state = "death"
            self.animation_index = 0
            self.current_frames = self.animations["death"]
            self.death_sound.play()
            return True
            
        self.state = "take_hit"
        self.animation_index = 0
        self.current_frames = self.animations["take_hit"]
        self.hit_sound.play()
        return True
    
    def apply_gravity(self):
        self.gravity += 1
        self.rect.y += self.gravity
        ground_level = pg.display.Info().current_h + 130  # Aligned with player
        if self.rect.bottom >= ground_level:
            self.rect.bottom = ground_level
            self.gravity = 0
    
    def update_state(self):
        if not self.is_alive:
            return
            
        current_time = pg.time.get_ticks()
        
        if self.state in ["attack", "take_hit", "death"]:
            if self.animation_index >= len(self.current_frames) - 1:
                if self.state == "death":
                    self.is_alive = False
                    return
                elif self.state == "attack":
                    self.attack_applied = False
                self.state = "run"
                self.current_frames = self.animations["run"]
                self.animation_index = 0
            return
        
        distance_to_player = abs(self.player.rect.centerx - self.rect.centerx)
        print(f"Goblin state: {self.state}, distance to player: {distance_to_player}, position: {self.rect.center}")
        
        if distance_to_player < self.attack_range:
            if current_time - self.last_attack_time > self.attack_cooldown:
                self.state = "attack"
                self.animation_index = 0
                self.current_frames = self.animations["attack"]
                self.last_attack_time = current_time
                self.attack_sound.play()
                self.attack_applied = False
        else:
            self.state = "run"
            if self.player.rect.centerx < self.rect.centerx:
                self.direction = -1
            else:
                self.direction = 1
    
    def update_movement(self):
        if not self.is_alive or self.state in ["attack", "take_hit", "death"]:
            return
            
        if self.state == "run":
            self.rect.x += self.direction * self.speed
            
            if self.rect.left < 0:
                self.rect.left = 0
            if self.rect.right > pg.display.Info().current_w:
                self.rect.right = pg.display.Info().current_w
    
    def update_animation(self):
        animation_speed = self.animation_speeds.get(self.state, 0.15)
        self.animation_index += animation_speed
        
        if self.state == "death" and self.animation_index >= len(self.current_frames):
            self.animation_index = len(self.current_frames) - 1
        
        if self.animation_index >= len(self.current_frames):
            self.animation_index = 0
        
        self.image = self.current_frames[int(self.animation_index)]
        
        # Run bounce effect
        if self.state == "run":
            self.run_bounce = math.sin(self.animation_index * math.pi) * 1.5  # Reduced amplitude
            self.rect.y -= self.run_bounce
        
        # Attack shake and scale effect
        if self.state == "attack":
            if int(self.animation_index) == self.attack_frame and not self.attack_applied:
                if abs(self.player.rect.centerx - self.rect.centerx) < self.attack_range:
                    self.player.player_ui.update_health(-self.attack_damage)
                    self.attack_applied = True
                self.attack_scale = 1.1  # Scale pulse on hit
            else:
                self.attack_scale = 1.0
            self.attack_shake = random(-2, 2) if int(self.animation_index) < self.attack_frame else 0
            self.rect.x += self.attack_shake
        
        # Apply scale
        if self.attack_scale != 1.0:
            orig_w, orig_h = self.image.get_size()
            self.image = pg.transform.scale(self.image, (int(orig_w * self.attack_scale), int(orig_h * self.attack_scale)))
            # Adjust rect to keep centered
            old_center = self.rect.center
            self.rect = self.image.get_rect(center=old_center)
        
        if self.state not in ["attack", "take_hit", "death"]:
            if self.direction > 0:
                self.image = pg.transform.flip(self.image, True, False)
    
    def draw_health_bar(self, surface):
        if not self.is_alive or self.health == self.max_health:
            return
            
        health_ratio = self.health / self.max_health
        bar_width = 50
        bar_height = 5
        fill_width = int(bar_width * health_ratio)
        
        bar_x = self.rect.centerx - bar_width // 2
        bar_y = self.rect.top - 10
        
        pg.draw.rect(surface, (50, 50, 50), (bar_x, bar_y, bar_width, bar_height))
        health_color = (255 * (1 - health_ratio), 255 * health_ratio, 0)
        pg.draw.rect(surface, health_color, (bar_x, bar_y, fill_width, bar_height))
    
    def update(self):
        if not self.is_alive:
            return
            
        self.update_state()
        self.apply_gravity()
        self.update_movement()
        self.update_animation()
    
    def draw(self, surface):
        draw_rect = self.rect.copy()
        if self.state == "run":
            draw_rect.y += self.run_bounce
        surface.blit(self.image, draw_rect)
        pg.draw.rect(surface, (255, 0, 0), self.rect, 2)
        self.draw_health_bar(surface)