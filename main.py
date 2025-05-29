import pygame as pg
from sys import exit
from random import randint
from player import Player
from enemies import Enemy, Goblin
from ui import PlayerUI

# Initialize pygame
pg.init()

# Initialize joystick
pg.joystick.init()
if pg.joystick.get_count() > 0:
    joystick = pg.joystick.Joystick(0)
    joystick.init()
    print(f"Joystick detected: {joystick.get_name()}")
    print(f"Number of buttons: {joystick.get_numbuttons()}")
    print(f"Number of axes: {joystick.get_numaxes()}")
else:
    joystick = None
    print("No joystick detected")

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
next_bat_group_time = 0
bat_group_min_delay = 5000
bat_group_max_delay = 15000

# Goblin spawning variables
goblin_spawned = False
goblin_spawn_time = 1000

# Background music
bg_music = pg.mixer.Sound("Resources/audio/music.wav")
bg_music.play(loops=-1)
bg_music.set_volume(0)

# Player
player = pg.sprite.GroupSingle()
player.add(Player())

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
how_to_play_rect = how_to_play.get_rect(center=(400, 350))
game_name = test_font.render('Pixel Runner', False, (111, 196, 169))
game_name_rect = game_name.get_rect(center=(400, 80))
player_stand = pg.image.load("Resources/graphics/player/player_stand.png").convert_alpha()
player_stand = pg.transform.rotozoom(player_stand, 0, 2)
player_stand_rect = player_stand.get_rect(center=(400, 200))

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
                    goblin_spawned = False
                    player_ui.start_timer()
                    
                if exit_button_pressed and exit_button_rect.collidepoint(mouse_pos):
                    pg.quit()
                    exit()
                    current_exit_button = exit_btn_original
                    exit_button_pressed = False
                
            if event.type == pg.KEYDOWN and event.key == pg.K_SPACE:
                game_active = True
                start_time = int(pg.time.get_ticks() / 1000)
                goblin_spawned = False
                player_ui.start_timer()
        
    if game_active:
        current_time = pg.time.get_ticks()

        # Spawn a new bat group
        if current_time > next_bat_group_time:
            bat_count = randint(3, 5)
            for i in range(bat_count):
                y_pos = randint(100, info.current_h - 600)
                x_offset = randint(0, 175)
                bat = Enemy()
                bat.rect.midleft = (info.current_w + x_offset, y_pos)
                bat.y_base = y_pos
                obstacle_group.add(bat)
            next_bat_group_time = current_time + randint(bat_group_min_delay, bat_group_max_delay)

        # Spawn goblin
        if not goblin_spawned and current_time - start_time * 1000 >= goblin_spawn_time:
            print(f"Spawning goblin at time: {current_time / 1000:.2f}s, position: ({info.current_w - 100}, {info.current_h + 130})")
            goblin = Goblin(player.sprite, info.current_w - 100, info.current_h - 130)
            obstacle_group.add(goblin)
            goblin_spawned = True

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
        
        player_ui.update()
        player_ui.draw(screen)
        
        player.draw(screen)
        player.update()
        obstacle_group.draw(screen)
        obstacle_group.update()
    
    else:
        screen.fill((94, 129, 162))
        score_message = test_font.render(f'Your score: {score}', False, (111, 196, 169))
        score_message_rect = score_message.get_rect(center=(400, 330))

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