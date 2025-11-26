import pygame as pg

class Button:
    def __init__(self, x, y, image, hover_image=None, scale=1.0, size=None, on_click=None, anchor='topleft'):
        self.on_click = on_click
        self.anchor = anchor
        self.x = x
        self.y = y
        
        # Base images
        self.base_image = image
        self.base_hover_image = hover_image if hover_image else image
        
        # Determine initial size
        if size:
            self.width, self.height = size
            self.scale = 1.0 # Scale is relative to the provided size if needed, but usually size overrides scale
        else:
            self.width = int(image.get_width() * scale)
            self.height = int(image.get_height() * scale)
            self.scale = scale

        # Prepare processed images
        self._update_images()
        
        self.rect = self.image.get_rect()
        self._update_position()
        
        self.is_hovered = False
        self.is_pressed = False
        
        # Animation
        self.hover_scale = 1.1
        self.animation_speed = 10
        self.current_scale = 1.0
        
        print(f"[DEBUG] Button created at ({self.x}, {self.y}) with size ({self.width}, {self.height})")
        
    def _update_images(self):
        self.image_original = pg.transform.scale(self.base_image, (self.width, self.height))
        self.hover_image_original = pg.transform.scale(self.base_hover_image, (self.width, self.height))
        self.image = self.image_original

    def _update_position(self):
        if self.anchor == 'center':
            self.rect.center = (self.x, self.y)
        elif self.anchor == 'topright':
            self.rect.topright = (self.x, self.y)
        elif self.anchor == 'topleft':
            self.rect.topleft = (self.x, self.y)
        else:
            setattr(self.rect, self.anchor, (self.x, self.y))

    def set_position(self, x, y, anchor=None):
        self.x = x
        self.y = y
        if anchor:
            self.anchor = anchor
        self._update_position()
        print(f"[DEBUG] Button position updated to ({self.x}, {self.y})")

    def set_size(self, width, height):
        self.width = width
        self.height = height
        self._update_images()
        self.rect = self.image.get_rect()
        self._update_position()
        print(f"[DEBUG] Button size updated to ({self.width}, {self.height})")

    def handle_event(self, event):
        if event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
            if self.is_hovered:
                self.is_pressed = True
                print("[DEBUG] Button pressed")
        
        if event.type == pg.MOUSEBUTTONUP and event.button == 1:
            if self.is_pressed and self.is_hovered:
                print("[DEBUG] Button clicked")
                if self.on_click:
                    self.on_click()
            self.is_pressed = False

    def update(self, dt):
        mouse_pos = pg.mouse.get_pos()
        was_hovered = self.is_hovered
        self.is_hovered = self.rect.collidepoint(mouse_pos)
        
        if self.is_hovered and not was_hovered:
            print("[DEBUG] Button hovered")
        
        # Hover Animation
        target_scale = self.hover_scale if self.is_hovered else 1.0
        dt_sec = dt / 1000.0
        
        # Smoothly interpolate current scale
        self.current_scale += (target_scale - self.current_scale) * (self.animation_speed * dt_sec)
        
        # Apply Scale
        # We scale from the *current* base size (self.width, self.height)
        if abs(self.current_scale - 1.0) > 0.001:
            # Calculate new dimensions based on current_scale
            new_w = int(self.width * self.current_scale)
            new_h = int(self.height * self.current_scale)
            
            # Choose which image to scale
            source_img = self.base_hover_image if self.is_hovered else self.base_image
            
            self.image = pg.transform.scale(source_img, (new_w, new_h))
            
            # Keep centered on the original rect center
            old_center = self.rect.center
            self.rect = self.image.get_rect(center=old_center)
        else:
            self.image = self.hover_image_original if self.is_hovered else self.image_original
            # Reset rect to standard position/size to avoid drift
            self._update_position()

    def draw(self, surface):
        surface.blit(self.image, self.rect)
