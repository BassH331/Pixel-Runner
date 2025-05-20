import pygame as pg
from sys import exit
from random import randint, choice

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
        if keys[pg.K_SPACE] and self.rect.bottom >= 300:
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
bg_music.set_volume(3)
# Create instance of Player class
player = pg.sprite.GroupSingle()
player.add(Player())

# Create instance of objects fly/snail
obstacle_group = pg.sprite.Group()

#Making the surfaces
sky_surface = pg.image.load("Resources/graphics/Sky.png").convert()# convert the image to file format pygame can work with more easier
ground_surface = pg.image.load("Resources/graphics/ground.png").convert()

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
            #Pressing the space button will then restart the game
            if event.type == pg.KEYDOWN:
                if event.key == pg.K_SPACE:
                    # Game starts again
                    game_active = True
                    start_time = int(pg.time.get_ticks() / 1000)# Use this as milliseconds so we divide it by 1000 and convert it to int so that it doesn't return decimals
        
        if game_active:
            # Dynamicly place objects in game [LOGIC]
            if event.type == obstacle_timer:
                obstacle_group.add(Obstacle(choice(['fly', 'sanil', 'snail', 'snail'])))
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
        screen.blit(player_stand, player_stand_rect)
        
        # If there is a score display the score but if there isnt one then display the game message
        score_message = test_font.render(f'Your score: {score}', False, (111, 196, 169))
        score_message_rect = score_message.get_rect(center = (400, 330))

        # So that game stops and restarts and refreshes the obstacle x postion (this will be done by clearing the obstacle_list so that everything starts from scratch)
        #obstacle_rect_list.clear()
        #player_rect.midbottom = (80, 300)
        player_gravity = 0

        if score == 0:
            #title and how-to-play
            screen.blit(how_to_play, how_to_play_rect)
        else: 
            screen.blit(score_message, score_message_rect)

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