import math
import pygame as pg
from v3x_zulfiqar_gideon import State, AssetManager

class SplashState(State):
    """Sleek, atmospheric splash screen matching the game's obsidian and gold aesthetic."""

    def __init__(self, manager):
        super().__init__(manager)
        self.width = pg.display.get_surface().get_width()
        self.height = pg.display.get_surface().get_height()
        
        # Logo (Full screen 16:9 illustration)
        try:
            raw_logo = AssetManager.get_texture("assets/graphics/Game_logo/Game Logo.png")
            self.logo = pg.transform.smoothscale(raw_logo, (self.width, self.height))
            self.logo_rect = self.logo.get_rect(topleft=(0, 0))
        except Exception:
            self.logo = None
            
        # ── Ambient Floating Particles (Embers) ──────────────────────────────
        self._particles = [
            {
                "x": float((i * 113) % self.width),
                "y": float((i * 73) % self.height),
                "speed_x": 8.0 + (i % 4) * 5.0,
                "speed_y": -12.0 - (i % 3) * 6.0,
                "size": 2 + (i % 3),
                "alpha_phase": (i * 0.8),
            }
            for i in range(25)
        ]

        # ── Decoupled Pre-loading ────────────────────────────────────────────
        self.next_state = None
        if hasattr(self.manager, 'router') and self.manager.router:
            next_class = self.manager.router.get_next(self)
            if next_class:
                print(f"[Splash] Priming next state: {next_class.__name__}")
                self.next_state = next_class(self.manager)

        self.alpha = 0.0
        self.fade_speed = 320.0
        self.state = "FADE_IN"
        self.timer = 0.0
        self.wait_time = 1.0 
        self.min_loading_time = 0.6
        self.loading_timer = 0.0
        
        self.font = AssetManager.get_font(
            "assets/font/Abaddon Bold.ttf", 24
        )

    def handle_event(self, event):
        if event.type == pg.KEYDOWN:
            pass

    def update(self, dt):
        dt_sec = dt / 1000.0 if dt > 0.5 else dt
        
        # Update particles
        for p in self._particles:
            p["x"] += p["speed_x"] * dt_sec
            p["y"] += p["speed_y"] * dt_sec
            if p["x"] > self.width + 10:
                p["x"] = -10
            if p["y"] < -10:
                p["y"] = float(self.height + 10)

        # Pump next state progress if needed
        loading_active = self.next_state is not None and hasattr(self.next_state, 'loading_progress')
        if loading_active:
            self.loading_timer += dt_sec

        if self.state == "FADE_IN":
            self.alpha += self.fade_speed * dt_sec
            if self.alpha >= 255.0:
                self.alpha = 255.0
                self.state = "WAIT"
                
        elif self.state == "WAIT":
            self.timer += dt_sec
            loading_done = True
            if self.next_state is not None and hasattr(self.next_state, 'loading_progress'):
                progress = getattr(self.next_state, 'loading_progress', 0.0)
                if progress < 1.0 or self.loading_timer < self.min_loading_time:
                    loading_done = False
                
            if self.timer >= self.wait_time and loading_done:
                self.state = "FADE_OUT"
                
        elif self.state == "FADE_OUT":
            self.alpha -= self.fade_speed * dt_sec
            if self.alpha <= 0.0:
                self.alpha = 0.0
                if self.next_state:
                    self.manager.set(self.next_state)
                else:
                    self.finish()
        
    def draw(self, surface):
        surface.fill((10, 8, 16))

        if self.logo:
            self.logo.set_alpha(int(self.alpha))
            surface.blit(self.logo, self.logo_rect)

        # Ambient floating embers
        ticks = pg.time.get_ticks()
        for p in self._particles:
            p_pulse = (math.sin(ticks * 0.005 + p["alpha_phase"]) + 1.0) * 0.5
            p_alpha = int((80 + 90 * p_pulse) * (self.alpha / 255.0))
            if p_alpha > 0:
                glow = pg.Surface((12, 12), pg.SRCALPHA)
                pg.draw.circle(glow, (255, 180, 40, int(p_alpha * 0.5)), (6, 6), 5)
                pg.draw.circle(glow, (255, 220, 100, p_alpha), (6, 6), p["size"])
                surface.blit(glow, (int(p["x"]) - 6, int(p["y"]) - 6))
            
        # Draw Sleek Gold Loading Bar if next state is loading
        if self.next_state is not None and hasattr(self.next_state, 'loading_progress'):
            progress = getattr(self.next_state, 'loading_progress', 0.0)
            if progress < 1.0:
                bar_width = int(self.width * 0.42)
                bar_height = 6
                bar_x = (self.width - bar_width) // 2
                bar_y = self.height - 55
                
                # Outer track border
                track_surf = pg.Surface((bar_width + 4, bar_height + 4), pg.SRCALPHA)
                track_surf.fill((14, 10, 20, int(self.alpha * 0.9)))
                pg.draw.rect(
                    track_surf,
                    (180, 140, 50, int(self.alpha * 0.7)),
                    (0, 0, bar_width + 4, bar_height + 4),
                    width=1,
                    border_radius=3,
                )
                surface.blit(track_surf, (bar_x - 2, bar_y - 2))
                
                # Gold Fill
                fill_width = max(2, int(bar_width * progress))
                fill_surf = pg.Surface((fill_width, bar_height), pg.SRCALPHA)
                fill_surf.fill((255, 215, 80, int(self.alpha * 0.95)))
                surface.blit(fill_surf, (bar_x, bar_y))
                
                # Percent text
                percent = int(progress * 100)
                text_surf = self.font.render(f"Loading... {percent}%", True, (240, 215, 140))
                text_surf.set_alpha(int(self.alpha * 0.9))
                text_rect = text_surf.get_rect(midbottom=(self.width // 2, bar_y - 8))
                surface.blit(text_surf, text_rect)
