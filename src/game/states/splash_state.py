import pygame as pg
from v3x_zulfiqar_gideon.state_machine import State
from v3x_zulfiqar_gideon.asset_manager import AssetManager

class SplashState(State):
    def __init__(self, manager):
        super().__init__(manager)
        self.width = pg.display.get_surface().get_width()
        self.height = pg.display.get_surface().get_height()
        
        # Logo
        try:
            self.logo = AssetManager.get_texture("assets/graphics/Game_logo/Game Logo.png")
            logo_rect = self.logo.get_rect()
            if logo_rect.width > self.width * 0.8:
                scale = (self.width * 0.8) / logo_rect.width
                self.logo = pg.transform.scale_by(self.logo, scale)
            self.logo_rect = self.logo.get_rect(center=(self.width // 2, self.height // 2))
        except:
            self.logo = None
            
        # ── Decoupled Pre-loading ────────────────────────────────────────────
        # We ask the router what's next, and instantiate it to start its loading thread.
        self.next_state = None
        if hasattr(self.manager, 'router') and self.manager.router:
            next_class = self.manager.router.get_next(self)
            if next_class:
                print(f"[Splash] Priming next state: {next_class.__name__}")
                self.next_state = next_class(self.manager)

        self.alpha = 0
        self.fade_speed = 255
        self.state = "FADE_IN"
        self.timer = 0
        self.wait_time = 1.0 
        self.min_loading_time = 0.5
        self.loading_timer = 0
        
    def handle_event(self, event):
        # Consume events to prevent "Space bar buffering" into next state
        if event.type == pg.KEYDOWN:
            pass

    def update(self, dt):
        dt_sec = dt / 1000.0
        
        # Pump next state progress if needed (usually happens in thread)
        loading_active = self.next_state and hasattr(self.next_state, 'loading_progress')
        if loading_active:
            self.loading_timer += dt_sec

        if self.state == "FADE_IN":
            self.alpha += self.fade_speed * dt_sec
            if self.alpha >= 255:
                self.alpha = 255
                self.state = "WAIT"
                
        elif self.state == "WAIT":
            self.timer += dt_sec
            
            # Decide if we are done
            loading_done = True
            if loading_active:
                # Must stay in wait at least as long as min_loading_time if it's actually loading something
                if self.next_state.loading_progress < 1.0 or self.loading_timer < self.min_loading_time:
                    loading_done = False
                
            if self.timer >= self.wait_time and loading_done:
                self.state = "FADE_OUT"
                
        elif self.state == "FADE_OUT":
            self.alpha -= self.fade_speed * dt_sec
            if self.alpha <= 0:
                self.alpha = 0
                if self.next_state:
                    self.manager.set(self.next_state)
                else:
                    self.finish()
        
    def draw(self, surface):
        surface.fill((0, 0, 0))
        if self.logo:
            self.logo.set_alpha(int(self.alpha))
            surface.blit(self.logo, self.logo_rect)
            
        # Draw Loading Bar if next state is loading
        if self.next_state and hasattr(self.next_state, 'loading_progress'):
            progress = self.next_state.loading_progress
            if progress < 1.0:
                bar_width = self.width * 0.6
                bar_height = 10
                bar_x = (self.width - bar_width) // 2
                bar_y = self.height - 50
                
                # Background
                pg.draw.rect(surface, (50, 50, 50), (bar_x, bar_y, bar_width, bar_height))
                # Fill
                fill_width = bar_width * progress
                pg.draw.rect(surface, (255, 255, 255), (bar_x, bar_y, fill_width, bar_height))
                
                # Percent
                percent = int(progress * 100)
                font = AssetManager.get_font('assets/Colorfiction_HandDrawnFonts/Colorfiction - Papyrus.otf', 30)
                text_surf = font.render(f"Loading... {percent}%", False, (180, 180, 180))
                text_rect = text_surf.get_rect(midbottom=(self.width // 2, bar_y - 10))
                surface.blit(text_surf, text_rect)
