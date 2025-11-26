import pygame as pg
from src.my_engine.state_machine import State
from src.my_engine.asset_manager import AssetManager
from src.my_engine.ui import Button
import sys

class MainMenuState(State):
    def __init__(self, manager):
        super().__init__(manager)
        self.width = pg.display.get_surface().get_width() 
        self.height = pg.display.get_surface().get_height() 
        # Background Animation
        self.frames = []
        self.current_frame_index = 0
        self.frame_timer = 0
        self.frame_delay = 80 # 0.08s from filename
        self.loading_thread = None
        
        # Start loading in background
        self.loading_progress = 0.0
        import threading
        self.loading_thread = threading.Thread(target=self.load_frames, daemon=True)
        self.loading_thread.start()
        
        # Fallback/Loading placeholder
        self.bg_placeholder = pg.Surface((self.width, self.height))
        self.bg_placeholder.fill((30, 30, 30))

        # Title - bottom
        self.title_font = AssetManager.get_font('assets/font/Abaddon Bold.ttf', 100)
        self.title_surf = self.title_font.render("Guardian Runner", False, (111, 196, 169))
        self.title_rect = self.title_surf.get_rect(center=(self.width // 2, 150))

        # Title - top
        self.title_font_top  = AssetManager.get_font('assets/font/Abaddon Bold.ttf', 100)
        self.title_surf_top = self.title_font_top.render("Guardian Runner", False, (0, 0, 0))
        self.title_rect_top = self.title_surf_top.get_rect(center=(self.width // 2 - 6, 155))
        
        # Buttons
        self.buttons = []
        self.create_buttons()

    def load_frames(self):
        bg_dir = "assets/graphics/background images/intro_bg"
        try:
            import os
            frame_files = sorted([f for f in os.listdir(bg_dir) if f.endswith(".gif") or f.endswith(".png")])
            total_frames = len(frame_files)
            
            loaded_frames = []
            for i, f in enumerate(frame_files):
                # Note: Pygame image loading must happen on main thread usually, 
                # but loading into surface is often thread-safe if not drawing.
                # However, to be safe and simple, we load here.
                # If this crashes, we might need to load bytes and decode on main thread,
                # but standard pygame.image.load often works in threads for simple cases.
                try:
                    img = pg.image.load(os.path.join(bg_dir, f)).convert_alpha()
                    img = pg.transform.scale(img, (self.width, self.height)) # Faster than smoothscale
                    loaded_frames.append(img)
                except Exception as e:
                    print(f"Error loading frame {f}: {e}")
                
                # Update progress
                self.loading_progress = (i + 1) / total_frames
            
            self.frames = loaded_frames
            print(f"Loaded {len(self.frames)} frames in background.")
            
        except Exception as e:
            print(f"Failed to load background frames: {e}")
        
    def create_buttons(self):
        # TODO: Implement your own buttons here using the guide!
        # Example:
        # self.start_btn = Button(x, y, image, hover_image, scale, callback)
        # self.buttons.append(self.start_btn)
        pass

    def start_game(self):
        from .story_state import StoryState
        self.manager.set(StoryState(self.manager))
        
    def exit_game(self):
        pg.quit()
        sys.exit()
        

        
    # Redefining handle_event to pass to buttons
    def handle_event(self, event):
        for btn in self.buttons:
            btn.handle_event(event)
            
    def update(self, dt):
        # Update Background Animation
        if self.frames:
            self.frame_timer += dt
            if self.frame_timer >= self.frame_delay:
                self.frame_timer = 0
                self.current_frame_index = (self.current_frame_index + 1) % len(self.frames)

        for btn in self.buttons:
            btn.update(dt) # Update animations

    def draw(self, surface):
        if self.frames:
            surface.blit(self.frames[self.current_frame_index], (0, 0))
        else:
            surface.blit(self.bg_placeholder, (0, 0))
            # Optional: Draw "Loading..." text
            
        surface.blit(self.title_surf, self.title_rect)
        surface.blit(self.title_surf_top, self.title_rect_top)
        
        for btn in self.buttons:
            btn.draw(surface)
