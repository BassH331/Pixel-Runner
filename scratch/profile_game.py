import os
import sys
import cProfile
import pstats
import pygame as pg

# Configure dummy audio and video drivers for headless profiling
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

sys.path.insert(0, os.getcwd())

pg.init()
pg.display.set_mode((1280, 720))

from unittest.mock import MagicMock
from v3x_zulfiqar_gideon import UITheme, StateManager
from src.game.states.game_state import GameState

# Configure UITheme to prevent load crashes
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

manager = StateManager(audio_manager=MagicMock())
game_state = GameState(manager)
game_state.on_enter()

# Close overlays
game_state.tutorial_overlay._active = False
game_state.objective_display._active = False

# Spawn entities to load updates and collision checks
for i in range(15):
    # Spawn skeleton
    game_state.spawn_skeleton({
        "x": 300 + i * 50,
        "y": 400,
        "tier": "minion",
        "scale": 1.0,
        "health": 30.0
    })

print("Profiling 1000 frames of gameplay update loop...")
pr = cProfile.Profile()
pr.enable()

for _ in range(1000):
    game_state.update(1.0 / 60.0)

pr.disable()
ps = pstats.Stats(pr).sort_stats('tottime')
ps.print_stats(25)
