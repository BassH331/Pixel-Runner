import pygame as pg
from src.my_engine.state_machine import State
from src.my_engine.asset_manager import AssetManager

class MenuState(State):
    def __init__(self, manager):
        super().__init__(manager)
        self.width = pg.display.get_surface().get_width()
        self.height = pg.display.get_surface().get_height()
        self.test_font = AssetManager.get_font('assets/font/Pixeltype.ttf', 50)
        
        # Buttons
        play_btn = AssetManager.get_texture("assets/graphics/ui/PlayBtn.png")
        self.play_button = pg.transform.scale(play_btn, (120, 60))
        play_btn_pressed = AssetManager.get_texture("assets/graphics/ui/PlayClick.png")
        self.play_button_pressed = pg.transform.scale(play_btn_pressed, (115, 55))
        self.play_button_rect = self.play_button.get_rect(center=(self.width//2, self.height//2))
        
        exit_btn = AssetManager.get_texture("assets/graphics/ui/ExitIcon.png")
        self.exit_btn_original = pg.transform.scale(exit_btn, (25, 25))
        exit_btn_pressed = AssetManager.get_texture("assets/graphics/ui/ExitIconClick.png")
        self.exit_btn_pressed = pg.transform.scale(exit_btn_pressed, (36, 36))
        self.exit_button_rect = self.exit_btn_original.get_rect(topright=(self.width - 10, 10))
        
        self.game_name = self.test_font.render('Guardian Runner', False, (111, 196, 169))
        self.game_name_rect = self.game_name.get_rect(center=(self.width//2, 80))
        
        self.current_play_button = self.play_button
        self.current_exit_button = self.exit_btn_original
        self.button_pressed = False
        self.exit_button_pressed = False
        self.button_press_time = 0
        self.exit_press_time = 0
        
        # Score (passed via manager or global? For now assume 0 or need a way to share data)
        # I'll add a shared data dict to StateManager or just use a global singleton for GameData
        self.score = 0 

    def handle_event(self, event):
        mouse_pos = pg.mouse.get_pos()
        
        if event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
            if self.play_button_rect.collidepoint(mouse_pos):
                self.current_play_button = self.play_button_pressed
                self.button_pressed = True
                self.button_press_time = pg.time.get_ticks()
            elif self.exit_button_rect.collidepoint(mouse_pos):
                self.current_exit_button = self.exit_btn_pressed
                self.exit_button_pressed = True
                self.exit_press_time = pg.time.get_ticks()
        
        if event.type == pg.MOUSEBUTTONUP and event.button == 1:
            if self.button_pressed and self.play_button_rect.collidepoint(mouse_pos):
                self.current_play_button = self.play_button
                self.button_pressed = False
                from .game_state import GameState
                self.manager.set(GameState(self.manager))
                
            if self.exit_button_pressed and self.exit_button_rect.collidepoint(mouse_pos):
                pg.quit()
                exit()
        
        if event.type == pg.KEYDOWN and event.key == pg.K_SPACE:
            from .game_state import GameState
            self.manager.set(GameState(self.manager))

    def update(self, dt):
        if self.button_pressed and pg.time.get_ticks() - self.button_press_time > 200:
            self.current_play_button = self.play_button
        if self.exit_button_pressed and pg.time.get_ticks() - self.exit_press_time > 200:
            self.current_exit_button = self.exit_btn_original

    def draw(self, surface):
        surface.fill((94, 129, 162))
        score_message = self.test_font.render(f'Your score: {self.score}', False, (111, 196, 169))
        score_message_rect = score_message.get_rect(center=(self.width//2, self.height//2 + 50))

        surface.blit(self.current_play_button, self.play_button_rect)
        if self.score > 0:
            surface.blit(self.current_exit_button, self.exit_button_rect)
            surface.blit(score_message, score_message_rect)

        surface.blit(self.game_name, self.game_name_rect)
        
        if self.score == 0:
            instr = self.test_font.render("Press SPACE to Start", False, (255, 255, 255))
            instr_rect = instr.get_rect(center=(self.width//2, self.height//2 + 150))
            surface.blit(instr, instr_rect)
