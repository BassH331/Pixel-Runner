import pygame
from .asset_manager import AssetManager

class Entity(pygame.sprite.Sprite):
    def __init__(self, x, y, image_path=None):
        super().__init__()
        if image_path:
            self.image = AssetManager.get_texture(image_path)
            self.rect = self.image.get_rect(topleft=(x, y))
        else:
            self.image = pygame.Surface((32, 32))
            self.image.fill((255, 255, 255))
            self.rect = self.image.get_rect(topleft=(x, y))
            
        self.image_offset = pygame.math.Vector2(0, 0)
        self.components = {}
        
    def add_component(self, component):
        self.components[component.name] = component
        component.owner = self
        
    def get_component(self, name):
        return self.components.get(name)
        
    def update(self, dt):
        for component in self.components.values():
            component.update(dt)
            
    def draw(self, surface):
        """Draws the entity's image at the rect position minus the offset."""
        draw_pos = self.rect.topleft - self.image_offset
        surface.blit(self.image, draw_pos)

    def set_hitbox_size(self, width, height):
        """
        Sets the absolute size of the collision rect, maintaining center.
        Use this if you know the exact dimensions you want for the hitbox.
        
        Args:
            width (int): The new width of the hitbox.
            height (int): The new height of the hitbox.
        """
        center = self.rect.center
        self.rect.size = (width, height)
        self.rect.center = center

    def reduce_hitbox(self, reduce_w, reduce_h, align='center', offset_y=0):
        """
        Reduces the collision rect by the specified width and height.
        Use this to make the hitbox smaller than the sprite image.
        
        Args:
            reduce_w (int): Amount to reduce the width by (total).
            reduce_h (int): Amount to reduce the height by (total).
            align (str): 'center' or 'bottom'. Defaults to 'center'.
                         'bottom' keeps the bottom edge fixed (good for platformers).
            offset_y (int): Additional vertical offset to raise the bottom (only for align='bottom').
        """
        if align == 'center':
            self.rect.inflate_ip(-reduce_w, -reduce_h)
            self.image_offset = pygame.math.Vector2(reduce_w // 2, reduce_h // 2)
        elif align == 'bottom':
            original_bottom = self.rect.bottom
            self.rect.inflate_ip(-reduce_w, -reduce_h)
            self.rect.bottom = original_bottom - offset_y
            self.image_offset = pygame.math.Vector2(reduce_w // 2, reduce_h - offset_y)

    def adjust_hitbox_sides(self, top=0, bottom=0, left=0, right=0):
        """
        Shrinks the hitbox by the specified amount from each side.
        Positive values shrink the box, negative values expand it.
        
        Args:
            top (int): Amount to shrink from the top.
            bottom (int): Amount to shrink from the bottom.
            left (int): Amount to shrink from the left.
            right (int): Amount to shrink from the right.
        """
        self.rect.x += left
        self.rect.y += top
        self.rect.width -= (left + right)
        self.rect.height -= (top + bottom)
        
        # Update image offset to keep image stationary relative to the new rect
        self.image_offset.x += left
        self.image_offset.y += top

    def set_image_offset(self, x, y):
        """
        Manually sets the image offset relative to the hitbox top-left corner.
        
        Args:
            x (int): Horizontal offset. Positive moves image LEFT relative to hitbox.
            y (int): Vertical offset. Positive moves image UP relative to hitbox.
        """
        self.image_offset = pygame.math.Vector2(x, y)

class Component:
    def __init__(self):
        self.name = "base_component"
        self.owner = None
        
    def update(self, dt):
        pass
