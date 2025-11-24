import pygame as pg
from src.my_engine.state_machine import State
from src.my_engine.asset_manager import AssetManager

class IntroState(State):
    def __init__(self, manager):
        super().__init__(manager)
        self.intro_index = 0
        self.story_slides = [
            {"line1": "In the heart of Aethelgard, the Star-Fire balanced light and shadow.", 
             "line2": "But a creeping Shadow Curse now threatens to extinguish its flame forever."},
            {"line1": "You are the last of the Star-Fire Guardians, a lineage sworn to protect the light.", 
             "line2": "Your journey begins now, a desperate race against the encroaching darkness."},
            {"line1": "Guided by ancient prophecies and the whispers of a forgotten wizard,", 
             "line2": "You have found the lost Fire Sword, a blade that sings with the Star-Fire's hymn."},
            {"line1": "Now, Guardian, your trial begins. Wield the flame, purge the shadows,", 
             "line2": "And run to save Aethelgard from eternal night. Your destiny awaits!"}
        ]
        self.width = pg.display.get_surface().get_width()
        self.height = pg.display.get_surface().get_height()
        self.story_font = AssetManager.get_font('assets/font/Pixeltype.ttf', 60)
        self.test_font = AssetManager.get_font('assets/font/Pixeltype.ttf', 50)
        self.story_images = self._load_story_images()

    def _load_story_images(self):
        images = []
        colors = [(34, 139, 34), (139, 69, 19), (255, 255, 255), (50, 50, 50)]
        for i in range(4):
            try:
                img = AssetManager.get_texture(f"assets/graphics/story/slide{i+1}.png")
                img = pg.transform.smoothscale(img, (1600, 800))
                images.append(img)
            except Exception:
                surf = pg.Surface((self.width, self.height))
                surf.fill(colors[i])
                images.append(surf)
        return images

    def update(self, dt):
        keys = pg.key.get_pressed()
        # Event handling is done in main loop usually, but here we check keys in update or handle events passed down?
        # The StateMachine pattern usually handles events in update or a separate handle_input method.
        # For now, I'll assume we check keys here or use event queue if passed.
        # But wait, main loop consumes events. I should probably pass events to update or have a handle_event method.
        # The user's example `State` class had `update(dt)` and `draw(surface)`.
        # I will add `handle_event(event)` to State class in a bit, or just check keys here.
        # Checking keys for single press is hard without event loop.
        # I will modify StateMachine to pass events or handle them.
        # For now, I'll rely on `pg.event.get()` being called in main and passed down?
        # Or I can just check `pg.key.get_just_pressed()` if using pygame 2.5+ but user might be on older.
        # I'll stick to checking keys but for single press I need a flag or event handling.
        # I will add `handle_event` to `State` class.
        pass

    def handle_event(self, event):
        if event.type == pg.KEYDOWN:
            if event.key == pg.K_SPACE:
                self.intro_index += 1
                if self.intro_index >= len(self.story_slides):
                    from .menu_state import MenuState
                    self.manager.set(MenuState(self.manager))
            elif event.key == pg.K_ESCAPE:
                from .menu_state import MenuState
                self.manager.set(MenuState(self.manager))

    def draw(self, surface):
        if self.intro_index < len(self.story_images):
            surface.blit(self.story_images[self.intro_index], (0, 0))
        
        overlay = pg.Surface((self.width, 200))
        overlay.set_alpha(180)
        overlay.fill((0,0,0))
        surface.blit(overlay, (0, self.height - 200))
        
        current_slide = self.story_slides[self.intro_index]
        text_surf1 = self.story_font.render(current_slide["line1"], False, (255, 255, 255))
        text_rect1 = text_surf1.get_rect(center=(self.width//2, self.height - 140))
        
        text_surf2 = self.story_font.render(current_slide["line2"], False, (200, 200, 200))
        text_rect2 = text_surf2.get_rect(center=(self.width//2, self.height - 80))
        
        surface.blit(text_surf1, text_rect1)
        surface.blit(text_surf2, text_rect2)
        
        hint = self.test_font.render("Press SPACE to continue", False, (111, 196, 169))
        hint_rect = hint.get_rect(bottomright=(self.width - 20, self.height - 20))
        surface.blit(hint, hint_rect)
