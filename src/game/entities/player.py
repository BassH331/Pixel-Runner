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
        
        # Movement and state variables
        self.gravity = 0            # Vertical movement speed (positive = falling, negative = jumping)
        self.is_running = False     # Whether player is currently moving horizontally
        self.direction = 0          # Horizontal direction (-1 = left, 0 = none, 1 = right)
        self.facing_left = False    # Sprite facing direction
        self.speed = 3              # Horizontal movement speed
        
        # Attack system
        self.is_attacking = False   # Whether player is currently in an attack animation
        self.attack_cooldown = 0    # Cooldown timer between attacks (currently unused)
        
        # Health system
        self.death_frames = self._load_frames("assets/shadow_warrior/death/death_{}.png", 12, start_index=1)
        self.max_health = 100       # Maximum health capacity
        self.health = 100           # Current health
        self.is_dead = False        # Whether player is dead

    def take_damage(self, amount):
        """
        Handle player taking damage.
        
        Args:
            amount (int): Amount of damage to apply
            
        If health drops to 0 or below, triggers death state and switches to death animation.
        Does nothing if player is already dead.
        """
        if self.is_dead:
            return  # Prevent damage after death
            
        self.health = max(0, self.health - amount)  # Ensure health doesn't go below 0
        
        if self.health <= 0:
            self.health = 0
            self.is_dead = True
            self.animation_index = 0
            self.current_frames = self.death_frames  # Play death animation
        
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
        
        # Attack 1 (Thrust) - Q button or right bumper
        if (keys[pg.K_q] or (joystick and joystick.get_button(2))) and not self.is_attacking:
            self.is_attacking = True
            self.current_frames = self.thrust_frames
            self.animation_index = 0
            self.is_running = False  # Stop running when attacking
            self.audio_manager.play_sound("thrust")
        
        # Attack 2 (Smash) - E button or left bumper
        if (keys[pg.K_e] or (joystick and joystick.get_button(1))) and not self.is_attacking:
            self.is_attacking = True
            self.current_frames = self.smash_frames
            self.animation_index = 0
            self.audio_manager.play_sound("smash")

    def apply_gravity(self):
        self.gravity += 1
        self.rect.y += self.gravity
        if self.rect.bottom >= pg.display.Info().current_h - 34:
            self.rect.bottom = pg.display.Info().current_h - 34

    def apply_movement(self):
        if self.is_dead: return # No movement if dead
        
        if self.direction != 0:
            self.rect.x += self.direction * self.speed 
            
            if self.rect.left < 0:
                self.rect.left = 0
            if self.rect.right > 1100:
                self.rect.right = 1100
    
    def animation_state(self):
        # Handle death animation first (highest priority)
        if self.is_dead:
            self.animation_index += 0.15  # Slow down death animation
            if self.animation_index >= len(self.current_frames):
                self.animation_index = len(self.current_frames) - 1  # Stay on last frame
            
            self.image = self.current_frames[int(self.animation_index)]
            return

        # Handle attack animation (high priority)
        if self.is_attacking:
            self.animation_index += 0.33  # Attack animation speed
            
            # Check if attack animation is complete
            if self.animation_index >= len(self.current_frames):
                self.animation_index = 0
                self.is_attacking = False
                # Return to appropriate animation based on movement state
                self.current_frames = self.run_frames if self.is_running else self.idle_frames
        # Handle movement-based animations (lower priority than attack/death)
        elif self.rect.bottom < pg.display.Info().current_h - 230:  # In air
            # Choose between ascending or descending animation based on vertical movement
            self.current_frames = self.jump_up_frames if self.gravity < 0 else self.jump_down_frames
        elif self.is_running:
            self.current_frames = self.run_frames  # Running animation
        else:
            self.current_frames = self.idle_frames  # Default idle animation

        if not self.is_attacking: # Only advance non-attack animations if not attacking
            self.animation_index += 0.27
            if self.animation_index >= len(self.current_frames):
                self.animation_index = 0
        
        self.image = self.current_frames[int(self.animation_index)]
        if self.facing_left:
            self.image = pg.transform.flip(self.image, True, False)

    def update(self, dt=None): # Added dt to match Entity signature
        if not self.is_dead:
            self.player_input()
        self.apply_gravity()
        self.apply_movement()
        self.animation_state()
        super().update(dt)
