import pygame as pg
from random import randint
from src.my_engine.state_machine import State
from src.my_engine.asset_manager import AssetManager
from src.game.entities.player import Player
from src.game.entities.enemy import Enemy
from src.game.ui import PlayerUI

class GameState(State):
    def __init__(self, manager):
        super().__init__(manager)
        self.width = pg.display.get_surface().get_width()
        self.height = pg.display.get_surface().get_height()
        
        # Audio
        self.audio_manager = self.manager.audio_manager
        self.bg_music_channel = None
        
        # Entities
        self.player = pg.sprite.GroupSingle()
        self.player.add(Player(200, self.height + 135, self.audio_manager)) # y pos will be fixed by gravity/ground check
        self.obstacle_group = pg.sprite.Group()
        self.player_ui = PlayerUI()
        
        # Background
        self.bg_image = AssetManager.get_texture("assets/graphics/background images/new_bg_images/bg_image.png")
        self.bg_image = pg.transform.smoothscale(self.bg_image, (self.width, self.height))
        self.bg_x1 = 0
        self.bg_x2 = self.width
        self.bg_scroll_speed = 0
        self.max_bg_scroll_speed = 5
        
        # Game Logic
        self.score = 0
        self.start_time = int(pg.time.get_ticks() / 1000)
        self.next_bat_group_time = pg.time.get_ticks()
        
        # Load Level Data
        from src.game.levels.level_loader import LevelLoader
        self.level_loader = LevelLoader()
        self.level_data = self.level_loader.load_level("level_1.json")
        
        if self.level_data:
            self.BAT_GROUP_MIN_DELAY = self.level_data.get("spawn_rate_min", 5000)
            self.BAT_GROUP_MAX_DELAY = self.level_data.get("spawn_rate_max", 15000)
            # Set player pos if available
            player_data = next((e for e in self.level_data.get("entities", []) if e["type"] == "player"), None)
            if player_data:
                self.player.sprite.rect.midbottom = (player_data["x"], player_data["y"])
        else:
            self.BAT_GROUP_MIN_DELAY = 5000
            self.BAT_GROUP_MAX_DELAY = 15000
            
        self.debug_mode = False
        
    def on_enter(self):
        self.audio_manager.stop_all_sounds()
        
        self.audio_manager.play_sound("forest", loop=True, volume=0.8)
        self.player_ui.start_timer()
        
    def on_exit(self):
        self.audio_manager.stop_all_sounds() # Or just music?
        
    def handle_event(self, event):
        if event.type == pg.KEYDOWN:
            if event.key == pg.K_d:
                self.debug_mode = not self.debug_mode
        
    def spawn_enemies(self, current_time):
        if current_time > self.next_bat_group_time:
            bat_count = randint(3, 5)
            for i in range(bat_count):
                y_pos = randint(50, self.height // 2)
                x_offset = randint(0, 175)
                bat = Enemy()
                # Manually set rect as Enemy init doesn't take x,y yet (my bad, I should have fixed Enemy init)
                # But Enemy update uses rect.x/y.
                # I'll set it here.
                bat.rect.midleft = (self.width + x_offset, y_pos)
                bat.y_base = y_pos
                self.obstacle_group.add(bat)
            self.audio_manager.play_sound("bats")
            self.next_bat_group_time = current_time + randint(self.BAT_GROUP_MIN_DELAY, self.BAT_GROUP_MAX_DELAY)

    def update_background(self, dt_scroll):
        self.bg_x1 -= dt_scroll
        self.bg_x2 -= dt_scroll

        if dt_scroll > 0:
            if self.bg_x1 <= -self.width: self.bg_x1 = self.width
            if self.bg_x2 <= -self.width: self.bg_x2 = self.width
        elif dt_scroll < 0:
            if self.bg_x1 >= self.width: self.bg_x1 = -self.width
            if self.bg_x2 >= self.width: self.bg_x2 = -self.width

    def update(self, dt):
        current_time = pg.time.get_ticks()
        self.spawn_enemies(current_time)
        
        player_sprite = self.player.sprite
        if player_sprite.is_running:
            self.bg_scroll_speed = self.max_bg_scroll_speed * player_sprite.direction
        else:
            self.bg_scroll_speed = 0
            
        self.update_background(self.bg_scroll_speed)
        self.player_ui.update()
        self.player.update()
        self.obstacle_group.update()
        
        # Collision detection
        if pg.sprite.spritecollide(player_sprite, self.obstacle_group, False):
             if player_sprite.is_attacking:
                 pg.sprite.spritecollide(player_sprite, self.obstacle_group, True)
                 self.audio_manager.play_sound("smash") # Or some hit sound
                 self.score += 10 # Example score
             else:
                 # Game Over
                 from .main_menu_state import MainMenuState
                 menu = MainMenuState(self.manager)
                 # menu.score = self.score # Pass score if MainMenu supports it, for now just go back
                 self.manager.set(menu)

    def draw(self, surface):
        surface.blit(self.bg_image, (self.bg_x1, 0))
        surface.blit(self.bg_image, (self.bg_x2, 0))
        self.player_ui.draw(surface)
        self.player_ui.draw(surface)
        
        # Draw player
        self.player.sprite.draw(surface)
        
        # Draw enemies
        for enemy in self.obstacle_group:
            enemy.draw(surface)
        
        if self.debug_mode:
            # Draw player rect (Red)
            pg.draw.rect(surface, (255, 0, 0), self.player.sprite.rect, 2)
            # Draw enemy rects (Green)
            for sprite in self.obstacle_group:
                pg.draw.rect(surface, (0, 255, 0), sprite.rect, 2)
