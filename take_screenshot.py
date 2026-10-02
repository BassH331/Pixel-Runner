import os
os.environ["SDL_VIDEODRIVER"] = "dummy"

import pygame as pg
from v3x_zulfiqar_gideon import V3XCore, V3XManifest

from src.game.states.story_state import StoryState

class ScreenshotState(StoryState):
    def __init__(self, manager):
        super().__init__(manager)
        self.frames = 0
        
    def update(self, dt):
        super().update(dt)
        self.frames += 1
        # Wait 30 frames to let the text start typing out, or jump to end
        if self.frames == 10:
            self.anim_renderer.skip_to_end()
            self.text_progress = float(len(self.story_text))
            self.is_text_complete = True
            
        if self.frames >= 30:
            pg.image.save(pg.display.get_surface(), "screenshot_story.png")
            print("Saved screenshot_story.png")
            import sys
            sys.exit(0)

# We'll just define a minimal manifest
manifest = V3XManifest(
    title="Test",
    base_width=1280,
    base_height=720,
    initial_state=ScreenshotState,
    routes={},
    theme={
        "buttons": {
            "assets": {
                "big": ("assets/graphics/UI/PNG/TextBTN_Big.png", "assets/graphics/UI/PNG/TextBTN_Big_Pressed.png"),
                "medium": ("assets/graphics/UI/PNG/TextBTN_Medium.png", "assets/graphics/UI/PNG/TextBTN_Medium_Pressed.png"),
                "cancel": ("assets/graphics/UI/PNG/TextBTN_Cancel.png", "assets/graphics/UI/PNG/TextBTN_Cancel_Pressed.png"),
                "new_start": ("assets/graphics/UI/PNG/TextBTN_New-Start.png", "assets/graphics/UI/PNG/TextBTN_New-Start_Pressed.png"),
            },
            "font_path": "assets/Colorfiction_HandDrawnFonts/Colorfiction - Papyrus.otf",
        },
        "notifications": {
            "banner_path": "assets/graphics/UI/PNG/IRONY TITLE  Large.png",
            "icons": {
                "gray": "assets/graphics/UI/PNG/Exclamation_Gray.png",
                "red": "assets/graphics/UI/PNG/Exclamation_Red.png",
                "yellow": "assets/graphics/UI/PNG/Exclamation_Yellow.png",
            },
            "font_path": "assets/font/Abaddon Bold.ttf",
        },
        "overlays": {
            "stone_path": "assets/graphics/UI/PNG/UI board Medium  stone.png",
            "parchment_path": "assets/graphics/UI/PNG/UI board Medium  parchment.png",
            "title_font_path": "assets/font/Abaddon Bold.ttf",
            "body_font_path": "assets/graphics/Darinia/Darinia.ttf",
            "text_color": (60, 40, 20),
            "font_size": 32,
            "backdrop_alpha": 170,
        }
    },
    audio={}
)

engine = V3XCore()
engine.launch(manifest)
