import pygame as pg

class Player(pg.sprite.Sprite):
    def __init__(self):
        super().__init__()
        # Load idle animations
        self.idle_frames = []
        for i in range(8):
            frame = pg.image.load(f"Resources/Moon_knight/idle/moon_knight_{i}.png").convert_alpha()
            original_size = frame.get_size()
            scaled_size = (original_size[0] * 3, original_size[1] * 3)
            scaled_frame = pg.transform.scale(frame, scaled_size)
            self.idle_frames.append(scaled_frame)
            
        # Load run animations
        self.run_frames = []
        for i in range(8):
            frame = pg.image.load(f"Resources/Moon_knight/run/m_knight_run{i}.png").convert_alpha()
            original_size = frame.get_size()
            scaled_size = (original_size[0] * 3, original_size[1] * 3)
            scaled_frame = pg.transform.scale(frame, scaled_size)
            self.run_frames.append(scaled_frame)

        # Load thrust animations (Square button / Q key)
        self.thrust_frames = []
        for i in range(13):
            frame = pg.image.load(f"Resources/Moon_knight/thrust/thrust_{i:02d}.png").convert_alpha()
            original_size = frame.get_size()
            scaled_size = (original_size[0] * 3, original_size[1] * 3)
            scaled_frame = pg.transform.scale(frame, scaled_size)
            self.thrust_frames.append(scaled_frame)

        # Load smash animations (Circle button / E key)
        self.smash_frames = []
        for i in range(17):
            frame = pg.image.load(f"Resources/Moon_knight/smash/smash_{i:02d}.png").convert_alpha()
            original_size = frame.get_size()
            scaled_size = (original_size[0] * 3, original_size[1] * 3)
            scaled_frame = pg.transform.scale(frame, scaled_size)
            self.smash_frames.append(scaled_frame)

        self.current_frames = self.idle_frames
        self.animation_index = 0
        self.image = self.current_frames[self.animation_index]
        self.rect = self.image.get_rect(midbottom=(200, pg.display.Info().current_h + 135))
        self.gravity = 0
        self.is_running = False
        self.direction = 0
        self.facing_left = False
        self.speed = 2.5
        self.is_attacking = False
        self.attack_cooldown = 0

        # Sound effects
        self.jump_sound = pg.mixer.Sound("Resources/audio/jump.mp3")
        self.jump_sound.set_volume(0)
        self.thrust_sound = pg.mixer.Sound("Resources/audio/thrust.mp3")
        self.smash_sound = pg.mixer.Sound("Resources/audio/smash.mp3")

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
            
        if (keys[pg.K_SPACE] or (joystick and joystick.get_button(0))) and self.rect.bottom >= pg.display.Info().current_h + 130:
            self.gravity = -20
            self.jump_sound.play()
            
        if joystick and abs(joystick.get_axis(1)) > 0.5 and self.rect.bottom >= pg.display.Info().current_h + 130:
            self.gravity = -20
            self.jump_sound.play()
        
        if (keys[pg.K_q] or (joystick and joystick.get_button(2))) and not self.is_attacking:
            self.is_attacking = True
            self.current_frames = self.thrust_frames
            self.animation_index = 0
            self.thrust_sound.play()
        
        if (keys[pg.K_e] or (joystick and joystick.get_button(1))) and not self.is_attacking:
            self.is_attacking = True
            self.current_frames = self.smash_frames
            self.animation_index = 0
            self.smash_sound.play()

    def apply_gravity(self):
        self.gravity += 1
        self.rect.y += self.gravity
        if self.rect.bottom >= pg.display.Info().current_h + 130:
            self.rect.bottom = pg.display.Info().current_h + 130

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

    def update(self):
        self.player_input()
        self.apply_gravity()
        self.apply_movement()
        self.animation_state()