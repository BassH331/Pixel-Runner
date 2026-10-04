import os
os.environ["SDL_VIDEODRIVER"] = "dummy"

import pygame as pg
pg.init()
# Must set mode even in dummy
screen = pg.display.set_mode((1280, 720))

# Manually load font and dependencies
from v3x_zulfiqar_gideon import AssetManager
from src.game.ui.cinematic_narrative_overlay import CinematicNarrativeOverlay

def dummy_callback(x):
    pass

overlay = CinematicNarrativeOverlay()
pact_event = {
    "speaker_name": "Andras, Marquis of Discord",
    "avatar_sprite": "assets/Agis",
    "dialogue_text": "I can grant you power to burn this world, but it comes with a cost. Your soul will be mine.",
    "option_1_label": "[1] Submit to the Void",
    "option_1_buff": {"trigger_transformation": True},
    "option_2_label": "[2] Resist the Darkness",
    "option_2_buff": {"kill_player": True}
}

overlay.activate(pact_event, dummy_callback)

# Fast-forward the typewriter effect and vignette
for i in range(200):
    overlay.update(16.0)

# Draw
screen.fill((50, 50, 50)) # Gray base screen so the vignette is visible
overlay.draw(screen)

pg.image.save(screen, "/home/chosen333/.gemini/antigravity-ide/brain/4d7a970c-57e1-4fad-b673-734fd5d7242b/screenshot_andras.png")
print("Saved screenshot_andras.png")
pg.quit()
