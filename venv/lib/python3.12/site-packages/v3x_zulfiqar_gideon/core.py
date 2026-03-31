"""
Core engine wrapper for V3X ZULFIQAR-GIDEON.
Centralizes the game loop, state management, and event handling.
"""

from __future__ import annotations
import pygame as pg
from sys import exit
from typing import Type, Optional, Any

from .state_machine import StateManager, State
from .audio_manager import AudioManager
from .router import V3XManifest, Router
from .ui import UITheme

class V3XCore:
    """The central engine class that manages the application lifecycle."""
    
    def __init__(self, width: int = 0, height: int = 0, title: str = "V3X Engine", base_width: int = 1280, base_height: int = 720):
        """
        Initialize the engine and display.
        """
        # Pre-initialize mixer
        pg.mixer.pre_init(frequency=44100, size=-16, channels=2, buffer=2048)
        pg.init()
        pg.mixer.set_num_channels(32)
        
        # Determine actual resolution
        if width == 0 or height == 0:
            info = pg.display.Info()
            screen_w, screen_h = info.current_w, info.current_h
            scale_factor = min(screen_w / base_width, screen_h / base_height) * 0.999
            self.width, self.height = int(base_width * scale_factor), int(base_height * scale_factor)
        else:
            self.width, self.height = width, height
            
        self.screen = pg.display.set_mode((self.width, self.height), pg.RESIZABLE)
        pg.display.set_caption(title)
        
        self.clock = pg.time.Clock()
        self.audio_manager = AudioManager()
        self.state_manager = StateManager()
        self.state_manager.audio_manager = self.audio_manager
        self.is_running = True

    def launch(self, manifest: V3XManifest) -> None:
        """Launch the engine using a project manifest."""
        # 1. Apply UI Theme
        if manifest.theme:
            if "buttons" in manifest.theme: UITheme.configure_buttons(**manifest.theme["buttons"])
            if "notifications" in manifest.theme: UITheme.configure_notifications(**manifest.theme["notifications"])
            if "overlays" in manifest.theme: UITheme.configure_overlays(**manifest.theme["overlays"])
            
        # 2. Register Audio
        for name, path in manifest.audio.items():
            self.audio_manager.load_sound(name, path)
            
        # 3. Setup Router
        if manifest.routes:
            router = Router(manifest.routes)
            self.state_manager.set_router(router)
            
        # 4. Start Loop
        if not manifest.initial_state:
            raise ValueError("V3XManifest must specify an initial_state class.")
            
        self.run(manifest.initial_state)
        
    def run(self, initial_state_class: Type[State], **kwargs: Any) -> None:
        """Start the main game loop with an initial state."""
        initial_state = initial_state_class(self.state_manager, **kwargs)
        self.state_manager.push(initial_state)
        
        while self.is_running:
            dt = self.clock.get_time()
            for event in pg.event.get():
                if event.type == pg.QUIT: self.quit()
                self.state_manager.handle_event(event)
            
            self.state_manager.update(dt)
            self.audio_manager.update()
            self.state_manager.draw(self.screen)
            pg.display.update()
            self.clock.tick(60)
            
    def quit(self) -> None:
        self.is_running = False
        pg.quit()
        exit()
