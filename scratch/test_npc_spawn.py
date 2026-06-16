import sys
import os
sys.path.insert(0, os.getcwd())

import pygame as pg
pg.init()
pg.display.set_mode((1280, 720))

from unittest.mock import MagicMock
from v3x_zulfiqar_gideon import UITheme

# Configure UITheme
UITheme.configure_buttons(
    assets={
        "big": ("assets/graphics/UI/PNG/TextBTN_Big.png", "assets/graphics/UI/PNG/TextBTN_Big_Pressed.png"),
        "medium": ("assets/graphics/UI/PNG/TextBTN_Medium.png", "assets/graphics/UI/PNG/TextBTN_Medium_Pressed.png"),
        "cancel": ("assets/graphics/UI/PNG/TextBTN_Cancel.png", "assets/graphics/UI/PNG/TextBTN_Cancel_Pressed.png"),
        "new_start": ("assets/graphics/UI/PNG/TextBTN_New-Start.png", "assets/graphics/UI/PNG/TextBTN_New-Start_Pressed.png"),
    },
    font_path="assets/Colorfiction_HandDrawnFonts/Colorfiction - Papyrus.otf"
)
UITheme.configure_notifications(
    banner_path="assets/graphics/UI/PNG/IRONY TITLE  Large.png",
    icons={
        "gray": "assets/graphics/UI/PNG/Exclamation_Gray.png",
        "red": "assets/graphics/UI/PNG/Exclamation_Red.png",
        "yellow": "assets/graphics/UI/PNG/Exclamation_Yellow.png",
    },
    font_path="assets/graphics/Darinia/Darinia.ttf"
)
UITheme.configure_overlays(
    stone_path="assets/graphics/UI/PNG/UI board Medium  stone.png",
    parchment_path="assets/graphics/UI/PNG/UI board Medium  parchment.png",
    title_font_path="assets/Colorfiction_HandDrawnFonts/Colorfiction - Gothic - Regular.otf",
    body_font_path="assets/Colorfiction_HandDrawnFonts/Colorfiction - Papyrus.otf",
    text_color=(60, 40, 20)
)

from src.game.states.game_state import GameState
from src.game.entities.generic_npc import GenericNPC
from v3x_zulfiqar_gideon import StateManager

# Create a dummy manager
manager = StateManager(audio_manager=MagicMock())

# Initialize GameState
game_state = GameState(manager)
game_state.on_enter()

# Close the tutorial and objective displays so the game updates
game_state.tutorial_overlay._active = False
game_state.objective_display._active = False

print("Initial world_distance:", game_state.world_distance)
print("Initial npc_group size:", len(game_state.npc_group))

# Fast forward world distance to 505
game_state.world_distance = 505.0
# Call update to trigger the event manager
game_state.world_manager.update(game_state.world_distance)

print("After update, npc_group size:", len(game_state.npc_group))

for npc in game_state.npc_group:
    print("\n--- NPC Info ---")
    print("Class:", npc.__class__.__name__)
    print("Title:", getattr(npc, "title", "None"))
    print("Text:", getattr(npc, "text", "None"))
    print("Rect:", npc.rect)
    print("Scale:", getattr(npc, "scale", "None"))
    print("Image size:", npc.image.get_size() if npc.image else "No Image")
    print("Visible (rect within screen):", npc.rect.colliderect(pg.Rect(0, 0, 1280, 720)))
    
    # Run a few updates with scrolling to see where it moves
    print("Simulating scroll of 5 pixels per frame:")
    for frame in range(10):
        game_state.npc_group.update(1.0/60.0, 5) # dt=1/60, scroll_speed=5
    print("After 10 frames scroll, Rect:", npc.rect)
    print("Visible (rect within screen):", npc.rect.colliderect(pg.Rect(0, 0, 1280, 720)))
