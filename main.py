import pygame as pg
from sys import exit
from random import randint
from player import Player
from enemies import Enemy
from ui import PlayerUI

# --- GLOBAL CONSTANTS ---
BASE_WIDTH, BASE_HEIGHT = 1280, 720
BAT_GROUP_MIN_DELAY = 5000
BAT_GROUP_MAX_DELAY = 15000

# --- SETUP FUNCTIONS ---
def init_joystick():
    pg.joystick.init()
    if pg.joystick.get_count() > 0:
        joystick = pg.joystick.Joystick(0)
        joystick.init()
        print(f"Joystick detected: {joystick.get_name()}")
        return joystick
    else:
        print("No joystick detected")
        return None

def setup_display():
    info = pg.display.Info()
    display_width, display_height = info.current_w, info.current_h
    
    # Calculate scaling factors
    width_scale = display_width / BASE_WIDTH
    height_scale = display_height / BASE_HEIGHT
    scale_factor = min(width_scale, height_scale) * 0.9
    
    # New dimensions
    width = int(BASE_WIDTH * scale_factor)
    height = int(BASE_HEIGHT * scale_factor)
    
    screen = pg.display.set_mode((width, height), pg.RESIZABLE)
    pg.display.set_caption("Runner: Guardian of the Star-Fire")
    return screen, width, height

def load_story_images(width, height):
    """Loads story images safely. If missing, creates colored placeholders."""
    images = []
    colors = [(34, 139, 34), (139, 69, 19), (255, 255, 255), (50, 50, 50)] # Fallback colors
    
    for i in range(4):
        try:
            # Assumes you saved images as slide1.png, slide2.png, etc.
            img = pg.image.load(f"Resources/graphics/story/slide{i+1}.png").convert()
            img = pg.transform.scale(img, (1600, 800))
            images.append(img)
        except FileNotFoundError:
            print(f"Story image slide{i+1}.png not found. Using placeholder.")
            surf = pg.Surface((width, height))
            surf.fill(colors[i])
            images.append(surf)
    return images

# --- GAME LOGIC FUNCTIONS ---
def reset_game():
    """Resets the game state for a new run"""
    global start_time, score, game_state, next_bat_group_time
    
    game_state = "playing" # Switch state
    start_time = int(pg.time.get_ticks() / 1000)
    score = 0
    next_bat_group_time = pg.time.get_ticks() 
    obstacle_group.empty() 
    player_ui.start_timer()

def update_background(dt_scroll):
    """Handles the infinite scrolling background"""
    global bg_x1, bg_x2
    
    bg_x1 -= dt_scroll
    bg_x2 -= dt_scroll

    if dt_scroll > 0:
        if bg_x1 <= -width: bg_x1 = width
        if bg_x2 <= -width: bg_x2 = width
    elif dt_scroll < 0:
        if bg_x1 >= width: bg_x1 = -width
        if bg_x2 >= width: bg_x2 = -width
        
    screen.blit(bg_image_1, (bg_x1, 0))
    screen.blit(bg_image_1, (bg_x2, 0))

def spawn_enemies(current_time):
    global next_bat_group_time
    if current_time > next_bat_group_time:
        bat_count = randint(3, 5)
        for i in range(bat_count):
            y_pos = randint(100, height - 200) # Dynamic height
            x_offset = randint(0, 175)
            bat = Enemy()
            bat.rect.midleft = (width + x_offset, y_pos)
            bat.y_base = y_pos
            obstacle_group.add(bat)
        next_bat_group_time = current_time + randint(BAT_GROUP_MIN_DELAY, BAT_GROUP_MAX_DELAY)

# --- STATE FUNCTIONS ---

def run_intro():
    """Handles drawing the story slides"""
    global intro_index, game_state
    
    # Draw the current image
    current_slide = story_slides[intro_index]
    screen.blit(story_images[intro_index], (0, 0))
    
    # Draw a dark overlay for text readability
    overlay = pg.Surface((width, 200))
    overlay.set_alpha(180)
    overlay.fill((0,0,0))
    screen.blit(overlay, (0, height - 200))
    
    # Draw Text
    text_surf1 = story_font.render(current_slide["line1"], False, (255, 255, 255))
    text_rect1 = text_surf1.get_rect(center=(width//2, height - 140))
    
    text_surf2 = story_font.render(current_slide["line2"], False, (200, 200, 200))
    text_rect2 = text_surf2.get_rect(center=(width//2, height - 80))
    
    screen.blit(text_surf1, text_rect1)
    screen.blit(text_surf2, text_rect2)
    
    # "Press Space" hint
    hint = test_font.render("Press SPACE to continue", False, (111, 196, 169))
    hint_rect = hint.get_rect(bottomright=(width - 20, height - 20))
    screen.blit(hint, hint_rect)

def run_gameplay():
    """The main game state"""
    global bg_scroll_speed, score
    
    current_time = pg.time.get_ticks()
    spawn_enemies(current_time)

    # Player Logic
    player_sprite = player.sprite
    if player_sprite.is_running:
        bg_scroll_speed = max_bg_scroll_speed * player_sprite.direction
    else:
        bg_scroll_speed = 0
    
    # Visuals
    update_background(bg_scroll_speed)
    player_ui.update()
    player_ui.draw(screen)
    player.draw(screen)
    player.update()
    obstacle_group.draw(screen)
    obstacle_group.update()

def draw_menu():
    """The menu/game over state"""
    global current_play_button, current_exit_button
    
    screen.fill((94, 129, 162))
    score_message = test_font.render(f'Your score: {score}', False, (111, 196, 169))
    score_message_rect = score_message.get_rect(center=(width//2, height//2 + 50))

    # Draw Buttons
    screen.blit(current_play_button, play_button_rect)
    if score > 0:
        screen.blit(current_exit_button, exit_button_rect)
        screen.blit(score_message, score_message_rect)

    screen.blit(game_name, game_name_rect)
    
    # Instructions
    if score == 0:
        instr = test_font.render("Press SPACE to Start", False, (255, 255, 255))
        instr_rect = instr.get_rect(center=(width//2, height//2 + 150))
        screen.blit(instr, instr_rect)

# ==========================================
# MAIN INITIALIZATION
# ==========================================

pg.init()
joystick = init_joystick()
screen, width, height = setup_display()
clock = pg.time.Clock()

# Assets
test_font = pg.font.Font('Resources/font/Pixeltype.ttf', 50)
story_font = pg.font.Font('Resources/font/Pixeltype.ttf', 60)

bg_image_1 = pg.image.load("Resources/graphics/background images/new_bg_images/bg_image.png").convert()
bg_image_1 = pg.transform.scale(bg_image_1, (width, height))

# Load Story Images
story_images = load_story_images(width, height)

# Audio
bg_music = pg.mixer.Sound("Resources/audio/music.wav")
bg_music.play(loops=-1)
bg_music.set_volume(0.3)

# Groups
player = pg.sprite.GroupSingle()
player.add(Player())
player_ui = PlayerUI()
obstacle_group = pg.sprite.Group()

# UI Elements
play_btn = pg.image.load("Resources/graphics/ui/PlayBtn.png").convert()
play_button = pg.transform.scale(play_btn, (120, 60))
play_btn_pressed = pg.image.load("Resources/graphics/ui/PlayClick.png").convert()
play_button_pressed = pg.transform.scale(play_btn_pressed, (115, 55))
play_button_rect = play_button.get_rect(center=(width//2, height//2))

exit_btn = pg.image.load("Resources/graphics/ui/ExitIcon.png").convert_alpha()
exit_btn_original = pg.transform.scale(exit_btn, (25, 25))
exit_btn_pressed = pg.transform.scale(pg.image.load("Resources/graphics/ui/ExitIconClick.png").convert_alpha(), (36, 36))
exit_button_rect = exit_btn_original.get_rect(topright=(width - 10, 10))

game_name = test_font.render('Guardian Runner', False, (111, 196, 169))
game_name_rect = game_name.get_rect(center=(width//2, 80))

# Global State Variables
game_state = "intro" # Options: "intro", "menu", "playing"
intro_index = 0
start_time = 0
score = 0
bg_x1 = 0
bg_x2 = width
bg_scroll_speed = 0
max_bg_scroll_speed = 5
next_bat_group_time = 0

current_play_button = play_button
button_pressed = False
button_press_time = 0
current_exit_button = exit_btn_original
exit_button_pressed = False
exit_press_time = 0

# Story Text Data
story_slides = [
    {"line1": "Aethelgard Forest was once peaceful...", "line2": "But the Shadow Curse has corrupted the land."},
    {"line1": "You journeyed through the scorching deserts,", "line2": "Fighting giant beasts to gain strength."},
    {"line1": "In the frozen mountains, the Wizard guided you,", "line2": "Revealing the location of the lost power."},
    {"line1": "Now, armed with the Fire Sword,", "line2": "You must defeat the darkness. RUN!"}
]

# ==========================================
# MAIN LOOP
# ==========================================
while True:
    # 1. EVENT HANDLING
    for event in pg.event.get():
        if event.type == pg.QUIT:
            pg.quit()
            exit()

        # INPUT: INTRO STATE
        if game_state == "intro":
            if event.type == pg.KEYDOWN and event.key == pg.K_SPACE:
                intro_index += 1
                if intro_index >= len(story_slides):
                    game_state = "menu" # Intro done, go to menu
            
            elif event.type == pg.KEYDOWN and event.key == pg.K_ESCAPE:
                game_state = "menu" # Skip intro

        # INPUT: MENU STATE
        elif game_state == "menu":
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
                if button_pressed and play_button_rect.collidepoint(mouse_pos):
                    current_play_button = play_button
                    button_pressed = False
                    reset_game()
                    
                if exit_button_pressed and exit_button_rect.collidepoint(mouse_pos):
                    pg.quit()
                    exit()
            
            if event.type == pg.KEYDOWN and event.key == pg.K_SPACE:
                reset_game()

    # 2. STATE MANAGEMENT (Drawing)
    if game_state == "intro":
        run_intro()
    elif game_state == "playing":
        run_gameplay()
    else: # "menu"
        draw_menu()
        # Reset buttons visual state logic
        if button_pressed and pg.time.get_ticks() - button_press_time > 200:
            current_play_button = play_button
        if exit_button_pressed and pg.time.get_ticks() - exit_press_time > 200:
            current_exit_button = exit_btn_original

    # 3. UPDATE DISPLAY & CLOCK
    pg.display.update()
    
    clock_speed = 60
    if score > 10: clock_speed = 75
    if score > 50: clock_speed = 115
    clock.tick(clock_speed)