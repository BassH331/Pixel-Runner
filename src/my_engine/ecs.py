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
            
        self.components = {}
        
    def add_component(self, component):
        self.components[component.name] = component
        component.owner = self
        
    def get_component(self, name):
        return self.components.get(name)
        
    def update(self, dt):
        for component in self.components.values():
            component.update(dt)

class Component:
    def __init__(self):
        self.name = "base_component"
        self.owner = None
        
    def update(self, dt):
        pass
