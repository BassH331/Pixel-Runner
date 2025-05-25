import pygame as pg
from sys import exit
from random import randint, choice

pg.joystick.init()
    
    
#Inititalize the joystick
# Initialize the first joystick
joystick = pg.joystick.Joystick(0)
joystick.init()
# At the start of your game, after initializing the joystick:
print(f"Joystick detected: {joystick.get_name()}")
print(f"Number of buttons: {joystick.get_numbuttons()}")
print(f"Number of axes: {joystick.get_numaxes()}")

#Player Class 
class Player(pg.sprite.Sprite):
    def __init__(self):
        super().__init__()
        #import player
        player_walk_1 = pg.image.load("Resources/graphics/player/player_walk_1.png").convert_alpha()
        player_walk_2 = pg.image.load("Resources/graphics/player/player_walk_2.png").convert_alpha()
        # The ones with self can be used outside of this function
        self.player_walk = [player_walk_1, player_walk_2]
        self.player_index = 0
        self.player_jump = pg.image.load("Resources/graphics/player/jump.png").convert_alpha()

        self.image = self.player_walk[self.player_index]
        self.rect = self.image.get_rect(midbottom = (200, 300))
        self.gravity = 0

        #import sound
        self.jump_sound = pg.mixer.Sound("Resources/audio/jump.mp3")
        self.jump_sound.set_volume(1)

    def player_input(self):
        keys = pg.key.get_pressed()
        if keys[pg.K_SPACE] or (joystick and (joystick.get_button(1) or  # PS4 Cross button (usually button 1)
                        joystick.get_button(0))) and self.rect.bottom >= 300:  # PS4 Square button (usually button 0)
            self.gravity = -20
            self.jump_sound.play()
    
        # Alternative jump with joystick up motion
        if joystick and abs(joystick.get_axis(1)) > 0.5 and self.rect.bottom >= 300:  # Left stick up
            self.gravity = -20
            self.jump_sound.play()
    
    def apply_gravity(self):
        self.gravity += 1
        self.rect.y += self.gravity
        if self.rect.bottom >= 300:
            self.rect.bottom = 300
    
    def animation_state(self):
        if self.rect.bottom < 300:
            self.image = self.player_jump
        else:
            self.player_index += 0.1
            if self.player_index >= len(self.player_walk):
                self.player_index = 0
            self.image = self.player_walk[int(self.player_index)]
            
    def apply_movement(self):
        # Horizontal movement
        if self.direction != 0:
            self.rect.x += self.direction * self.speed
            
            # Boundary checking
            if self.rect.left < 0:
                self.rect.left = 0
            if self.rect.right > 800:  # Screen width
                self.rect.right = 800

    def update(self):
        self.player_input()
        self.apply_gravity()
        self.animation_state()

# Object class
class Obstacle(pg.sprite.Sprite):
    def __init__(self, type):
        super().__init__()
        #import images 
        if type == 'fly':
            fly_1 = pg.image.load("Resources/graphics/fly/fly1.png").convert_alpha()
            fly_2 = pg.image.load("Resources/graphics/fly/fly2.png").convert_alpha()
            self.frames = [fly_1, fly_2]
            y_pos = 210
        elif type == 'python':
            # Load and scale images to 64x64 pixels
            python_1 = pg.transform.scale(pg.image.load("Resources/graphics/python/python_0.png").convert_alpha(), (64, 64))
            python_2 = pg.transform.scale(pg.image.load("Resources/graphics/python/python_1.png").convert_alpha(), (64, 64))
            python_3 = pg.transform.scale(pg.image.load("Resources/graphics/python/python_2.png").convert_alpha(), (64, 64))
            python_4 = pg.transform.scale(pg.image.load("Resources/graphics/python/python_3.png").convert_alpha(), (64, 64))
            python_5 = pg.transform.scale(pg.image.load("Resources/graphics/python/python_4.png").convert_alpha(), (64, 64))
            python_6 = pg.transform.scale(pg.image.load("Resources/graphics/python/python_5.png").convert_alpha(), (64, 64))
            python_7 = pg.transform.scale(pg.image.load("Resources/graphics/python/python_6.png").convert_alpha(), (64, 64))
            python_8 = pg.transform.scale(pg.image.load("Resources/graphics/python/python_7.png").convert_alpha(), (64, 64))
            self.frames = [pg.transform.flip(frame, True, False) for frame in [python_1, python_2, python_3, python_4, python_5, python_6, python_7, python_8]]
            y_pos = 300
        elif type == 'snake':
            # Load and scale images to 64x64 pixels
            snake_1 = pg.transform.scale(pg.image.load("Resources/graphics/snake/white_snake_0.png").convert_alpha(), (64, 64))
            snake_2 = pg.transform.scale(pg.image.load("Resources/graphics/snake/white_snake_1.png").convert_alpha(), (64, 64))
            snake_3 = pg.transform.scale(pg.image.load("Resources/graphics/snake/white_snake_2.png").convert_alpha(), (64, 64))
            snake_4 = pg.transform.scale(pg.image.load("Resources/graphics/snake/white_snake_3.png").convert_alpha(), (64, 64))
            self.frames = [pg.transform.flip(frame, True, False) for frame in [snake_1, snake_2, snake_3, snake_4]]
            y_pos = 300
        elif type == 'pigeon':
            # Load and scale images to 64x64 pixels
            pigeon_1 = pg.transform.scale(pg.image.load("Resources/graphics/pigeon/pigeon_0.png").convert_alpha(), (64, 64))
            pigeon_2 = pg.transform.scale(pg.image.load("Resources/graphics/pigeon/pigeon_1.png").convert_alpha(), (64, 64))
            pigeon_3 = pg.transform.scale(pg.image.load("Resources/graphics/pigeon/pigeon_2.png").convert_alpha(), (64, 64))
            pigeon_4 = pg.transform.scale(pg.image.load("Resources/graphics/pigeon/pigeon_3.png").convert_alpha(), (64, 64))
            self.frames = [pg.transform.flip(frame, True, False) for frame in [pigeon_1, pigeon_2, pigeon_3, pigeon_4]]
            y_pos = 210
        else:
            snail_1 = pg.image.load("Resources/graphics/snail/snail1.png").convert_alpha()
            snail_2 = pg.image.load("Resources/graphics/snail/snail2.png").convert_alpha()
            self.frames = [snail_1, snail_2]
            y_pos = 300
        
        self.animation_index = 0
        self.image = self.frames[self.animation_index]
        self.rect = self.image.get_rect(midbottom = (randint(900, 1100),y_pos))

    def animation_state(self):
        self.animation_index += 0.1
        if self.animation_index >= len(self.frames):
            self.animation_index = 0
        self.image = self.frames[int(self.animation_index)]
    
    def update(self):
        self.animation_state()
        self.rect.x -= 6
        self.destroy()
    
    def destroy(self):
        if self.rect.x <= -100:
            self.kill()

# Function display score
def display_score():
    current_time = int(pg.time.get_ticks() / 1000) - start_time
    score_surface = test_font.render(f'Score: {current_time}', False, (64, 64, 64))
    score_rect = score_surface.get_rect(center = (400, 50))
    screen.blit(score_surface, score_rect)
    return current_time


def collision(player, obstacles):
    if obstacles:
        for obstacle_rect in obstacles:
            if player.colliderect(obstacle_rect):
                return False
    return True

# Function to check player and obstacle collisions
def collision_sprites():
    if pg.sprite.spritecollide(player.sprite, obstacle_group, False):# spritecollide(sprite = value, group = value, bool = True/False)
        obstacle_group.empty()# So that it doesnt glitch and all obsatacles go back to the beginning of the screen
        # if (sprite=value) collides with (group=value), then the consider wether the gorup will be deleted from the list or not (bool = True/False)
        return False
    else:
        return True

# RUN BEFORE ANY PYGMAE CODE
pg.init()

print("Joystick initialized!")

#We create a display surface
width = 800 
height = 400
screen = pg.display.set_mode((width, height))
#Setting title of the game
game_title = "Runner"
pg.display.set_caption(game_title)
#set frame-rate
clock = pg.time.Clock()

def set_clock(time):
    clock.tick(int(time))

time = 60

#create font
test_font = pg.font.Font('Resources/font/Pixeltype.ttf', 50)#Font(font type, size)

# Game active state so that we can check for when the user wants to either restart the game or quit
game_active = False

# Variabale for keeping track of the start time for the game score
start_time = 0
score = 0

# import background music
bg_music = pg.mixer.Sound("Resources/audio/music.wav")
bg_music.play(loops = -1)# loops = [how many times you want to loop the music] (-1 means forever)
bg_music.set_volume(0.1)
# Create instance of Player class
player = pg.sprite.GroupSingle()
player.add(Player())

# Create instance of objects fly/snail
obstacle_group = pg.sprite.Group()

#Making the surfaces
sky_surface = pg.image.load("Resources/graphics/Sky.png").convert()# convert the image to file format pygame can work with more easier
ground_surface = pg.image.load("Resources/graphics/ground.png").convert()

# Defining the images for the welcome screen
play_btn = pg.image.load("Resources/graphics/ui/PlayBtn.png").convert()
play_button = pg.transform.scale(play_btn, (120, 60))

play_btn_pressed = pg.image.load("Resources/graphics/ui/PlayClick.png").convert()
play_button_pressed = pg.transform.scale(play_btn_pressed, (115, 55))

play_button_rect = play_button.get_rect(center=(400, 200))
current_play_button = play_button
button_pressed = False
button_press_time = 0

# Load exit button images
exit_btn = pg.image.load("Resources/graphics/ui/ExitIcon.png").convert_alpha()
exit_btn_original = pg.transform.scale(exit_btn, (25, 25))  # Adjust size as needed

exit_btn_pressed = pg.transform.scale(pg.image.load("Resources/graphics/ui/ExitIconClick.png").convert_alpha(), (36, 36))  # Slightly smaller
exit_button_rect = exit_btn_original.get_rect(topright=(width - 10, 10))  # 10px from top-right corner

current_exit_button = exit_btn_original
exit_button_pressed = False
exit_press_time = 0

"""
score_surface = test_font.render('My game', False, (64,64,64))# Render(text, Anti-Aliazing, color)
score_rect = score_surface.get_rect(center = (400, 50))
"""
# Text for game intro, the game-title, score and how-to-play 
how_to_play = test_font.render('Press space to make player jump & start-game', False, (111, 196, 169))# Render(text, Anti-Aliazing, color)
how_to_play_rect = how_to_play.get_rect(center = (400, 350))
game_name = test_font.render('Pixel Runner', False, (111, 196, 169))
game_name_rect = game_name.get_rect(center = (400, 80)) 

#Intro screen
player_stand = pg.image.load("Resources/graphics/player/player_stand.png").convert_alpha()
player_stand = pg.transform.rotozoom(player_stand, 0,2)# We will resize the above image so that we can display it in the intro
# Arguements for rotozoom(surface, angle, size)
player_stand_rect = player_stand.get_rect(center = (400, 200))

#Creating gravity for the game. Gravity will allow the players motion to look more natural
player_gravity = 0

# Timer - This will help us dynamically generate objects to make th game more interesting
obstacle_timer = pg.USEREVENT + 1 #always add plus 1
pg.time.set_timer(obstacle_timer, 1200)# set_timer(event_we_want_to_trigger = value, how_often_we_trigger_it = value[in milliseconds])

# Create timers for obstacle animation 
snail_animation_timer = pg.USEREVENT + 2
pg.time.set_timer(snail_animation_timer, 300)

fly_animation_timer = pg.USEREVENT + 3
pg.time.set_timer(fly_animation_timer, 70)

python_animation_timer = pg.USEREVENT + 2
pg.time.set_timer(python_animation_timer, 100)

snake_animation_timer = pg.USEREVENT + 2
pg.time.set_timer(snake_animation_timer, 100)

pigeon_animation_timer = pg.USEREVENT + 2
pg.time.set_timer(pigeon_animation_timer, 200)

"""
1] Create a list of obstacle rectangles
2] Everytime the timer triggers we add a new rectangle to that list
3] We move every rectangle in that list to the left on every frame
4] Delete rectangles to far to the left
"""



#Keep code running forever - entire game will run under here
while True:

    #make sure user can close the game
    for event in pg.event.get():# this loop looks for event changes, better yet user interactions

        # If user presses quit it closes the program
        if event.type == pg.QUIT:
            pg.quit()#closes the entire program
            exit()

        if game_active == False:
            
            # Handle mouse events for both buttons
            mouse_pos = pg.mouse.get_pos()
            
            # Play button handling (existing code)
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
                if button_pressed:
                    if play_button_rect.collidepoint(mouse_pos):
                        game_active = True
                        start_time = int(pg.time.get_ticks() / 1000)
                    current_play_button = play_button
                    button_pressed = False
                    
                if exit_button_pressed:
                    if exit_button_rect.collidepoint(mouse_pos):
                        pg.quit()
                        exit()
                    current_exit_button = exit_btn_original
                    exit_button_pressed = False
                
            #Pressing the space button will then restart the game
            if event.type == pg.KEYDOWN:
                if event.key == pg.K_SPACE:
                    # Game starts again
                    game_active = True
                    start_time = int(pg.time.get_ticks() / 1000)# Use this as milliseconds so we divide it by 1000 and convert it to int so that it doesn't return decimals
        
        if game_active:
            # Dynamicly place objects in game [LOGIC]
            if event.type == obstacle_timer:
                obstacle_group.add(Obstacle(choice(['fly', 'pigeon', 'pigeon', 'python', 'snail', 'snail', 'snake'])))
                """
                if randint(0,2):
                    obstacle_rect_list.append(snail_surface.get_rect(midbottom = (randint(900,1100), 300)))
                else:
                    obstacle_rect_list.append(fly_surface.get_rect(midbottom = (randint(900,1100), 210)))
                """

            # Here we will be checking the timers and in the loop change the animations for the snail/fly
            #if event.type == snail_animation_timer:
                #if snail_frame_index == 0:
                   # snail_frame_index = 1
                #else:
                    #snail_frame_index = 0
                #snail_surface = snail_frames[snail_frame_index]
            #if event.type == fly_animation_timer:
                #if fly_frame_index == 0:
                    #fly_frame_index = 1
                #else:
                    #fly_frame_index = 0
                #fly_surface = fly_frames[fly_frame_index]
                    
    

    if game_active:

        #call display surface
        screen.blit(ground_surface, (0, 300))
        screen.blit(sky_surface, (0,0))#argueements = (surface=value, position=(x=value, y=value))
        """
        # Use draw object to draw a rectangl = .rect()
        pg.draw.rect(screen, '#c0e8ec', score_rect)
        pg.draw.rect(screen, '#c0e8ec', score_rect, 10)
        screen.blit(score_surface, score_rect)
        """
        score = display_score()

        # Obstacle movement
        #obstacle_rect_list = obstacle_movement(obstacle_rect_list)

        # Collision
        game_active = collision_sprites()# Which will return true or false if there are any collisions

        # Display the player
        #player_animation()
        #screen.blit(player_surface, player_rect)
        #Using the player object to display the sprite instead of using blit
        player.draw(screen)
        player.update()#class function that will handle the updates of the sprite in the game
        obstacle_group.draw(screen)# Draw the obstacles onto the screen
        obstacle_group.update()

        # Stop the game once the player collides with the snail
    
    else:
        # Display the background for the intro to tell the users their score and hwo to play/ start the game 
        screen.fill((94, 129, 162))
        #display the player_stand character
        
        # If there is a score display the score but if there isnt one then display the game message
        score_message = test_font.render(f'Your score: {score}', False, (111, 196, 169))
        score_message_rect = score_message.get_rect(center = (400, 330))

        # So that game stops and restarts and refreshes the obstacle x postion (this will be done by clearing the obstacle_list so that everything starts from scratch)
        #obstacle_rect_list.clear()
        #player_rect.midbottom = (80, 300)
        player_gravity = 0

        if score == 0:
            # Display the play button
            screen.blit(current_play_button, play_button_rect)
            
            # If button was pressed but not yet released, show pressed state temporarily
            if button_pressed and pg.time.get_ticks() - button_press_time > 200:  # 200ms press duration
                current_play_button = play_button
            
        else: 
            screen.blit(score_message, score_message_rect)
            
            # Display the play button
            screen.blit(current_play_button, play_button_rect)
            
            # Display the exit button (always visible when game is not active)
            screen.blit(current_exit_button, exit_button_rect)
            
            ## Handle button press animations
        if button_pressed and pg.time.get_ticks() - button_press_time > 200:
            current_play_button = play_button
            
        if exit_button_pressed and pg.time.get_ticks() - exit_press_time > 200:
            current_exit_button = exit_btn_original

        #displayt the game name
        screen.blit(game_name, game_name_rect)
        #draw all our elements 
        #update everything
    

    pg.display.update()
    #method to set the maximum framerate for the game, increases as the score goes up
    
    if score < 10:
        time = 60
    if score > 10:
        time = 75
    if score > 20:
        time = 85
    if score > 35:
        time = 95
    if score > 50:
        time = 115
    if score > 65:
        time = 120
    #set the frame rate of game
    set_clock(time)