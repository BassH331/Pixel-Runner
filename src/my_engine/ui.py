import pygame as pg

class Button:
    def __init__(self, x, y, image, hover_image=None, scale=1.0, on_click=None):
        self.scale = scale
        self.image_original = pg.transform.scale_by(image, scale)
        self.image = self.image_original
        
        if hover_image:
            self.hover_image = pg.transform.scale_by(hover_image, scale)
        else:
            self.hover_image = self.image_original
            
        self.rect = self.image.get_rect(topleft=(x, y))
        self.on_click = on_click
        
        self.is_hovered = False
        self.is_pressed = False
        
        # Animation
        self.hover_scale = 1.1
        self.animation_speed = 0.1
        self.current_scale = 1.0
        
    def handle_event(self, event):
        if event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
            if self.is_hovered:
                self.is_pressed = True
        
        if event.type == pg.MOUSEBUTTONUP and event.button == 1:
            if self.is_pressed and self.is_hovered:
                if self.on_click:
                    self.on_click()
            self.is_pressed = False

    def update(self, dt):
        mouse_pos = pg.mouse.get_pos()
        self.is_hovered = self.rect.collidepoint(mouse_pos)
        
        # Hover Animation
        target_scale = self.hover_scale if self.is_hovered else 1.0
        # Simple lerp for smooth scaling
        # dt is in milliseconds, convert to seconds for consistent speed
        dt_sec = dt / 1000.0
        self.current_scale += (target_scale - self.current_scale) * (10 * dt_sec) # 10 is speed factor
        
        # Apply Scale
        if abs(self.current_scale - 1.0) > 0.001:
            scaled_image = self.hover_image if self.is_hovered else self.image_original
            # Note: Repeatedly scaling from original to avoid degradation
            self.image = pg.transform.scale_by(scaled_image, self.current_scale / self.scale) 
            self.rect = self.image.get_rect(center=self.rect.center)
        else:
            self.image = self.hover_image if self.is_hovered else self.image_original
            self.rect = self.image.get_rect(center=self.rect.center)

    def draw(self, surface):
        surface.blit(self.image, self.rect)
