import pygame as pg
from src.my_engine.state_machine import State
from src.my_engine.asset_manager import AssetManager
from src.my_engine.ui import Button

class MenuState(State):
    def __init__(self, manager):
        super().__init__(manager)
        self.width = pg.display.get_surface().get_width()
        self.height = pg.display.get_surface().get_height()
        self.test_font = AssetManager.get_font('assets/font/Pixeltype.ttf', 50)
        
        # Buttons
        play_btn_img = AssetManager.get_texture("assets/graphics/ui/PlayBtn.png")
        play_btn_hover = AssetManager.get_texture("assets/graphics/ui/PlayClick.png")
        
       
        
        exit_btn_img = AssetManager.get_texture("assets/graphics/ui/ExitIcon.png")
        exit_btn_hover = AssetManager.get_texture("assets/graphics/ui/ExitIconClick.png")
        
        self.exit_button = Button(
            x=self.width - 10, 
            y=10, 
            image=exit_btn_img, 
            hover_image=exit_btn_hover, 
            size=(25, 25),
            anchor='topright',
            on_click=self.quit_game
        )
        
        self.game_name = self.test_font.render('Guardian Runner', False, (111, 196, 169))
        self.game_name_rect = self.game_name.get_rect(center=(self.width//2, 80))
        
        self.score = 0 

    def start_game(self):
        from .game_state import GameState
        self.manager.set(GameState(self.manager))

    def quit_game(self):
        pg.quit()
        exit()

    def handle_event(self, event):
        self.play_button.handle_event(event)
        if self.score > 0:
            self.exit_button.handle_event(event)
        
        if event.type == pg.KEYDOWN and event.key == pg.K_SPACE:
            self.start_game()

    def update(self, dt):
        self.play_button.update(dt)
        if self.score > 0:
            self.exit_button.update(dt)

    def draw(self, surface):
        surface.fill((94, 129, 162))
        score_message = self.test_font.render(f'Your score: {self.score}', False, (111, 196, 169))
        score_message_rect = score_message.get_rect(center=(self.width//2, self.height//2 + 50))

        self.play_button.draw(surface)
        
        if self.score > 0:
            self.exit_button.draw(surface)
            surface.blit(score_message, score_message_rect)

        surface.blit(self.game_name, self.game_name_rect)
        
        if self.score == 0:
            instr = self.test_font.render("Press SPACE to Start", False, (255, 255, 255))
            instr_rect = instr.get_rect(center=(self.width//2, self.height//2 + 150))
            surface.blit(instr, instr_rect)
