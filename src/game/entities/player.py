import pygame as pg
from src.my_engine.ecs import Entity
from src.my_engine.asset_manager import AssetManager

class Player(Entity):
    def __init__(self, x, y, audio_manager):
        super().__init__(x, y)
        self.audio_manager = audio_manager
        
        # Load animations
        # Shadow Warrior assets use 1-based indexing
        self.idle_frames = self._load_frames("assets/shadow_warrior/idle/idle_{}.png", 12, start_index=1)
        self.run_frames = self._load_frames("assets/shadow_warrior/run/run_{}.png", 10, start_index=1)
        self.jump_up_frames = self._load_frames("assets/shadow_warrior/jump_up_loop/jump_up_loop_{}.png", 3, start_index=1)
        self.jump_down_frames = self._load_frames("assets/shadow_warrior/jump_down_loop/jump_down_loop_{}.png", 3, start_index=1)
        self.thrust_frames = self._load_frames("assets/shadow_warrior/1_atk/1_atk_{}.png", 9, start_index=1)
        self.smash_frames = self._load_frames("assets/shadow_warrior/2_atk/2_atk_{}.png", 17, start_index=1)

        self.current_frames = self.idle_frames
        self.animation_index = 0
        self.image = self.current_frames[self.animation_index]
        self.rect = self.image.get_rect(midtop=(x, y))
        # Adjust hitbox sides independently:
        # Left/Right: 105px each (total 210px width reduction)
        # Top: 150px (height reduction)
        # Bottom: 100px (raise bottom edge)
        self.adjust_hitbox_sides(left=315, right=315, top=150, bottom=0)
        
        # Manually adjust image offset if needed to fix visual sinking/shifting
        # self.set_image_offset(120, 150) # Example: Match top/left shrink values
        
        self.gravity = 0
        self.is_running = False
        self.direction = 0
        self.facing_left = False
        self.speed = 2.5
        self.is_attacking = False
        self.attack_cooldown = 0
        
    def _load_frames(self, path_pattern, count, start_index=0):
        frames = []
        for i in range(start_index, start_index + count):
            path = path_pattern.format(i)
            frame = AssetManager.get_texture(path)
            original_size = frame.get_size()
            scaled_size = (original_size[0] * 3, original_size[1] * 3)
            scaled_frame = pg.transform.scale(frame, scaled_size)
            frames.append(scaled_frame)
        return frames

    def player_input(self):
        keys = pg.key.get_pressed()
        joystick = None
        if pg.joystick.get_count() > 0:
            joystick = pg.joystick.Joystick(0)
        
        if self.is_attacking:
            return
        
        if keys[pg.K_LEFT] or (joystick and joystick.get_axis(0) < -0.5):
            self.direction = -1
            self.is_running = True
            self.facing_left = True
        elif keys[pg.K_RIGHT] or (joystick and joystick.get_axis(0) > 0.5):
            self.direction = 1
            self.is_running = True
            self.facing_left = False
        else:
            self.direction = 0
            self.is_running = False
            
        # Jump
        if (keys[pg.K_SPACE] or (joystick and joystick.get_button(0))) and self.rect.bottom >= pg.display.Info().current_h - 230:
            self.gravity = -29
            self.audio_manager.play_sound("jump")
            
        if joystick and abs(joystick.get_axis(1)) > 0.5 and self.rect.bottom >= pg.display.Info().current_h - 230:
            self.gravity = -29
            self.audio_manager.play_sound("jump")
        
        # Attacks
        if (keys[pg.K_q] or (joystick and joystick.get_button(2))) and not self.is_attacking:
            self.is_attacking = True
            self.current_frames = self.thrust_frames
            self.animation_index = 0
            self.audio_manager.play_sound("thrust")
        
        if (keys[pg.K_e] or (joystick and joystick.get_button(1))) and not self.is_attacking:
            self.is_attacking = True
            self.current_frames = self.smash_frames
            self.animation_index = 0
            self.audio_manager.play_sound("smash")

    def apply_gravity(self):
        self.gravity += 1
        self.rect.y += self.gravity
        if self.rect.bottom >= pg.display.Info().current_h - 230:
            self.rect.bottom = pg.display.Info().current_h - 230

    def apply_movement(self):
        if self.direction != 0:
            self.rect.x += self.direction * self.speed 
            
            if self.rect.left < 0:
                self.rect.left = 0
            if self.rect.right > 1100:
                self.rect.right = 1100
    
    def animation_state(self):
        if self.is_attacking:
            pass
        elif self.rect.bottom < pg.display.Info().current_h - 230: # In air
            if self.gravity < 0:
                self.current_frames = self.jump_up_frames
            else:
                self.current_frames = self.jump_down_frames
        elif self.is_running:
            self.current_frames = self.run_frames
        else:
            self.current_frames = self.idle_frames

        if self.is_attacking:
            self.animation_index += 0.55
            
            if self.animation_index >= len(self.current_frames):
                self.animation_index = 0
                self.is_attacking = False
                if self.is_running:
                    self.current_frames = self.run_frames
                else:
                    self.current_frames = self.idle_frames
        else:
            self.animation_index += 0.3
            if self.animation_index >= len(self.current_frames):
                self.animation_index = 0
        
        self.image = self.current_frames[int(self.animation_index)]
        if self.facing_left:
            self.image = pg.transform.flip(self.image, True, False)

    def update(self, dt=None): # Added dt to match Entity signature
        self.player_input()
        self.apply_gravity()
        self.apply_movement()
        self.animation_state()
        super().update(dt)
