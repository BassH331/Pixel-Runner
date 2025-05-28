import pygame as pg
from sys import exit
from random import randint, random
import os
import math as math

pg.joystick.init()

# Initialize the joystick
if pg.joystick.get_count() > 0:
    joystick = pg.joystick.Joystick(0)
    joystick.init()
    print(f"Joystick detected: {joystick.get_name()}")
    print(f"Number of buttons: {joystick.get_numbuttons()}")
    print(f"Number of axes: {joystick.get_numaxes()}")
else:
    joystick = None
    print("No joystick detected")
    
class PlayerUI:
    def __init__(self):
        # Initialize UI values
        self.max_health = 100
        self.current_health = 100
        self.relics = 0
        self.start_time = 0  # Will be set when game starts
        self.power_ups = []  # List to store active power-ups
        
        # UI positioning and appearance
        self.health_bar_width = 200
        self.health_bar_height = 20
        self.health_bar_pos = (20, 20)
        self.relic_icon_pos = (20, 50)
        self.power_up_icon_pos = (20, 80)
        self.time_pos = (info.current_w - 150, 20)
        
        # Load UI assets
        self.relic_icon = self.load_icon("Resources/graphics/ui/relic_icon.png", (30, 30))
        self.power_up_icons = {
            "double_jump": self.load_icon("Resources/graphics/ui/powerup_doublejump.png", (30, 30)),
            "speed_boost": self.load_icon("Resources/graphics/ui/powerup_speed.png", (30, 30)),
            "invincibility": self.load_icon("Resources/graphics/ui/powerup_invincible.png", (30, 30))
        }
        
        # Font for text rendering
        self.font = pg.font.Font('Resources/font/Pixeltype.ttf', 30)
    
    def load_icon(self, path, size):
        try:
            icon = pg.image.load(path).convert_alpha()
            return pg.transform.scale(icon, size)
        except:
            # Fallback if icon can't be loaded
            surface = pg.Surface(size, pg.SRCALPHA)
            pg.draw.rect(surface, (255, 0, 0), (0, 0, *size))
            return surface
    
    def start_timer(self):
        """Call this when the game starts"""
        self.start_time = pg.time.get_ticks()
    
    def get_elapsed_time(self):
        """Returns elapsed time in seconds"""
        return (pg.time.get_ticks() - self.start_time) // 1000
    
    def format_time(self, seconds):
        """Format time as MM:SS"""
        minutes = seconds // 60
        seconds = seconds % 60
        return f"{minutes:02d}:{seconds:02d}"
    
    def update_health(self, amount):
        self.current_health = max(0, min(self.max_health, self.current_health + amount))
    
    def add_relic(self, amount=1):
        self.relics += amount
    
    def add_power_up(self, power_up_type, duration):
        """Add a power-up with a duration in milliseconds"""
        self.power_ups.append({
            "type": power_up_type,
            "start_time": pg.time.get_ticks(),
            "duration": duration
        })
    
    def update(self):
        # Check for expired power-ups
        current_time = pg.time.get_ticks()
        self.power_ups = [pu for pu in self.power_ups 
                         if current_time - pu["start_time"] < pu["duration"]]
    
    def draw(self, surface):
        # Draw health bar
        health_ratio = self.current_health / self.max_health
        health_fill_width = int(self.health_bar_width * health_ratio)
        
        # Health bar background
        pg.draw.rect(surface, (50, 50, 50), 
                    (*self.health_bar_pos, self.health_bar_width, self.health_bar_height))
        # Health bar fill
        health_color = (255 * (1 - health_ratio), 255 * health_ratio, 0)
        pg.draw.rect(surface, health_color, 
                    (*self.health_bar_pos, health_fill_width, self.health_bar_height))
        # Health bar outline
        pg.draw.rect(surface, (255, 255, 255), 
                    (*self.health_bar_pos, self.health_bar_width, self.health_bar_height), 2)
        
        # Draw health text
        health_text = self.font.render(f"HP: {self.current_health}/{self.max_health}", True, (255, 255, 255))
        surface.blit(health_text, (self.health_bar_pos[0] + self.health_bar_width + 10, self.health_bar_pos[1]))
        
        # Draw relic counter
        surface.blit(self.relic_icon, self.relic_icon_pos)
        relic_text = self.font.render(f"x {self.relics}", True, (255, 255, 255))
        surface.blit(relic_text, (self.relic_icon_pos[0] + 35, self.relic_icon_pos[1]))
        
        # Draw power-up icons
        y_offset = 0
        for power_up in self.power_ups:
            icon = self.power_up_icons.get(power_up["type"], None)
            if icon:
                surface.blit(icon, (self.power_up_icon_pos[0], self.power_up_icon_pos[1] + y_offset))
                # Show remaining time as percentage
                elapsed = current_time - power_up["start_time"]
                remaining = max(0, power_up["duration"] - elapsed)
                percent = int((remaining / power_up["duration"]) * 100)
                time_text = self.font.render(f"{percent}%", True, (255, 255, 255))
                surface.blit(time_text, (self.power_up_icon_pos[0] + 35, self.power_up_icon_pos[1] + y_offset))
                y_offset += 35
        
        # Draw time (formatted as MM:SS)
        elapsed_seconds = self.get_elapsed_time()
        time_text = self.font.render(f"Time: {self.format_time(elapsed_seconds)}", True, (255, 255, 255))
        time_rect = time_text.get_rect(topright=self.time_pos)
        surface.blit(time_text, time_rect)

# Player Class
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
        self.rect = self.image.get_rect(midbottom = (200, info.current_h + 135))
        self.gravity = 0
        self.is_running = False
        self.direction = 0
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
        
        if self.is_attacking:
            return
        
        if keys[pg.K_LEFT] or (joystick and joystick.get_axis(0) < -0.5):
            self.direction = -1
            self.is_running = True
        elif keys[pg.K_RIGHT] or (joystick and joystick.get_axis(0) > 0.5):
            self.direction = 1
            self.is_running = True
        else:
            self.direction = 0
            self.is_running = False
            
        if (keys[pg.K_SPACE] or (joystick and joystick.get_button(0))) and self.rect.bottom >= info.current_h + 130:
            self.gravity = -20
            self.jump_sound.play()
            
        if joystick and abs(joystick.get_axis(1)) > 0.5 and self.rect.bottom >= info.current_h + 130:
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
        if self.rect.bottom >= info.current_h + 130:
            self.rect.bottom = info.current_h + 130

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
        
        if not self.is_attacking and self.direction < 0:
            self.image = pg.transform.flip(self.image, True, False)

    def update(self):
        self.player_input()
        self.apply_gravity()
        self.apply_movement()
        self.animation_state()


#Enemy Class
class Enemy(pg.sprite.Sprite):
    def __init__(self):
        super().__init__()
        # Load bat flying animations
        self.fly_frames = []
        try:
            for i in range(7):
                frame = pg.image.load(f"Resources/graphics/bat/running/bat_running_{i}.png").convert_alpha()
                original_size = frame.get_size()
                # Random size variation (1.5x to 2.5x original size)
                size_multiplier = 1.5 + random()
                scaled_size = (int(original_size[0] * size_multiplier), int(original_size[1] * size_multiplier))
                scaled_frame = pg.transform.scale(frame, scaled_size)
                # Flip each frame to face left
                flipped_frame = pg.transform.flip(scaled_frame, False, False)
                self.fly_frames.append(flipped_frame)
        except FileNotFoundError as e:
            print(f"Error loading bat animation: {e}")
            # Fallback to a blank surface to prevent crash
            self.fly_frames = [pg.Surface((50, 50), pg.SRCALPHA) for _ in range(7)]
        
        self.current_frames = self.fly_frames
        self.animation_index = 0
        self.image = self.current_frames[self.animation_index]
        # Random speed between -4 and -2 for leftward movement
        self.speed = -2 - random() * 2
        # For vertical oscillation
        self.y_base = 0  # Base y position set when spawned
        self.y_amplitude = 20  # Amplitude of vertical oscillation
        self.y_frequency = 0.05  # Speed of vertical oscillation
        self.time = 0  # Time counter for oscillation
        # Spawn position will be set when added to group
        self.rect = self.image.get_rect()

    def update(self):
        # Move left
        self.rect.x += self.speed
        # Add vertical oscillation for natural flying motion
        self.time += 1
        self.rect.y = self.y_base + self.y_amplitude * math.sin(self.y_frequency * self.time)
        # Animate smoothly
        self.animation_index += 0.15  # Slower animation speed for smoother transitions
        if self.animation_index >= len(self.current_frames):
            self.animation_index = 0
        self.image = self.current_frames[int(self.animation_index)]
        # Remove bat if it moves off-screen
        if self.rect.right < 0:
            self.kill()

def display_score():
    current_time = int(pg.time.get_ticks() / 1000) - start_time
    score_surface = test_font.render(f'Score: {current_time}', False, (64, 64, 64))
    score_rect = score_surface.get_rect(center = (400, 50))
    screen.blit(score_surface, score_rect)
    return current_time

# Initialize pygame
pg.init()

# Initialize screen
info = pg.display.Info()
width = info.current_w
height = info.current_h
screen = pg.display.set_mode((width, height))

# Background scrolling variables
bg_x1 = 0
bg_x2 = width
bg_scroll_speed = 0
max_bg_scroll_speed = 5

# Set game title
pg.display.set_caption("Runner")
clock = pg.time.Clock()

def set_clock(time):
    clock.tick(int(time))

time = 60
test_font = pg.font.Font('Resources/font/Pixeltype.ttf', 50)
game_active = False
start_time = 0
score = 0

# Bat spawning variables
next_bat_group_time = 0  # When the next group should spawn
bat_group_min_delay = 5000  # 5 seconds minimum
bat_group_max_delay = 15000  # 15 seconds maximum

# Background music
bg_music = pg.mixer.Sound("Resources/audio/music.wav")
bg_music.play(loops = -1)
bg_music.set_volume(0)

# Player
player = pg.sprite.GroupSingle()
player.add(Player())

# Inititalize player ui screen object
# Player UI
player_ui = PlayerUI()

# Obstacle group
obstacle_group = pg.sprite.Group()

# Load and resize background images
bg_image_1 = pg.image.load("Resources/graphics/background images/new_bg_images/bg_image.png").convert()
bg_image_1 = pg.transform.scale(bg_image_1, (width, height))

# UI elements
play_btn = pg.image.load("Resources/graphics/ui/PlayBtn.png").convert()
play_button = pg.transform.scale(play_btn, (120, 60))
play_btn_pressed = pg.image.load("Resources/graphics/ui/PlayClick.png").convert()
play_button_pressed = pg.transform.scale(play_btn_pressed, (115, 55))
play_button_rect = play_button.get_rect(center=(400, 200))
current_play_button = play_button
button_pressed = False
button_press_time = 0

exit_btn = pg.image.load("Resources/graphics/ui/ExitIcon.png").convert_alpha()
exit_btn_original = pg.transform.scale(exit_btn, (25, 25))
exit_btn_pressed = pg.transform.scale(pg.image.load("Resources/graphics/ui/ExitIconClick.png").convert_alpha(), (36, 36))
exit_button_rect = exit_btn_original.get_rect(topright=(width - 10, 10))
current_exit_button = exit_btn_original
exit_button_pressed = False
exit_press_time = 0

how_to_play = test_font.render('Press space to make player jump & start-game', False, (111, 196, 169))
how_to_play_rect = how_to_play.get_rect(center = (400, 350))
game_name = test_font.render('Pixel Runner', False, (111, 196, 169))
game_name_rect = game_name.get_rect(center = (400, 80))
player_stand = pg.image.load("Resources/graphics/player/player_stand.png").convert_alpha()
player_stand = pg.transform.rotozoom(player_stand, 0, 2)
player_stand_rect = player_stand.get_rect(center = (400, 200))

# Main game loop
while True:
    for event in pg.event.get():
        if event.type == pg.QUIT:
            pg.quit()
            exit()

        if not game_active:
            mouse_pos = pg.mouse.get_pos()
            if event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
                if play_button_rect.collidepoint(mouse_pos):
                    current_play_button = play_button_pressed
                    button_pressed = True
                    button_press_time = pg.time.get_ticks()
                elif exit_button_rect.collidepoint(mouse_pos):
                    current_exit_button = exit_btn_pressed
                    exit_button_pressed = True
                    exit_press_time = pg.time.get_ticks()
                    
            if event.type == pg.MOUSEBUTTONUP and event.button == 1:
                mouse_pos = pg.mouse.get_pos()
                if button_pressed and play_button_rect.collidepoint(mouse_pos):
                    game_active = True
                    start_time = int(pg.time.get_ticks() / 1000)
                    current_play_button = play_button
                    button_pressed = False
                    
                if exit_button_pressed and exit_button_rect.collidepoint(mouse_pos):
                    pg.quit()
                    exit()
                    current_exit_button = exit_btn_original
                    exit_button_pressed = False
                
            if event.type == pg.KEYDOWN and event.key == pg.K_SPACE:
                game_active = True
                start_time = int(pg.time.get_ticks() / 1000)
        
    if game_active:
        current_time = pg.time.get_ticks()

        # Spawn a new bat group when it's time
        if current_time > next_bat_group_time:
            # Determine how many bats in this group (3-5)
            bat_count = randint(3, 5)
            
            # Spawn the bats with vertical variation
            for i in range(bat_count):
                # Add some randomness to their y positions and spacing
                y_pos = randint(100, info.current_h - 600)
                x_offset = randint(0, 175)  # Stagger their x positions slightly
                bat = Enemy()
                bat.rect.midleft = (info.current_w + x_offset, y_pos)
                bat.y_base = y_pos  # Set the base y-position for oscillation
                obstacle_group.add(bat)
            
            # Set next spawn time (random delay between 5-15 seconds)
            next_bat_group_time = current_time + randint(bat_group_min_delay, bat_group_max_delay)

        player_sprite = player.sprite
        if player_sprite.is_running:
            bg_scroll_speed = max_bg_scroll_speed * player_sprite.direction
        else:
            bg_scroll_speed = 0
        
        bg_x1 -= bg_scroll_speed
        bg_x2 -= bg_scroll_speed

        if bg_scroll_speed > 0:
            if bg_x1 <= -width:
                bg_x1 = width
            if bg_x2 <= -width:
                bg_x2 = width
        elif bg_scroll_speed < 0:
            if bg_x1 >= width:
                bg_x1 = -width
            if bg_x2 >= width:
                bg_x2 = -width
            
        screen.blit(bg_image_1, (bg_x1, 0))
        screen.blit(bg_image_1, (bg_x2, 0))
    
        # In your game_active section, replace:
        # score = display_score()
        # With:
        player_ui.start_timer()
        player_ui.get_elapsed_time()# Start the game timer # Or whatever score logic you want
        player_ui.update()
        player_ui.draw(screen)
        
        player.draw(screen)
        player.update()
        obstacle_group.draw(screen)
        obstacle_group.update()
        
        # Check for collisions
        """
        if pg.sprite.spritecollide(player.sprite, obstacle_group, False):
            game_active = False
            obstacle_group.empty()  # Clear enemies on collision
        """
    
    else:
        screen.fill((94, 129, 162))
        score_message = test_font.render(f'Your score: {score}', False, (111, 196, 169))
        score_message_rect = score_message.get_rect(center = (400, 330))
        player_gravity = 0

        if score == 0:
            screen.blit(current_play_button, play_button_rect)
        else:
            screen.blit(score_message, score_message_rect)
            screen.blit(current_play_button, play_button_rect)
            screen.blit(current_exit_button, exit_button_rect)
            
        if button_pressed and pg.time.get_ticks() - button_press_time > 200:
            current_play_button = play_button
        if exit_button_pressed and pg.time.get_ticks() - exit_press_time > 200:
            current_exit_button = exit_btn_original

        screen.blit(game_name, game_name_rect)

    pg.display.update()
    if score < 10:
        time = 60
    elif score > 10:
        time = 75
    elif score > 20:
        time = 85
    elif score > 35:
        time = 95
    elif score > 50:
        time = 115
    elif score > 65:
        time = 120
    set_clock(time)