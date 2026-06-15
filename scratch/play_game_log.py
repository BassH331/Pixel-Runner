import sys
import os
sys.path.insert(0, os.getcwd())

import pygame as pg
pg.init()
pg.display.set_mode((1280, 720))

# Mock key pressed class to simulate holding Right Arrow
class MockKeys:
    def __getitem__(self, key):
        return key == pg.K_RIGHT

import pygame
import src.game.entities.player
mock_keys = MockKeys()
pygame.key.get_pressed = lambda: mock_keys  # type: ignore
src.game.entities.player.pg.key.get_pressed = lambda: mock_keys  # type: ignore

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
from src.game.entities.player import PlayerState
from v3x_zulfiqar_gideon import StateManager

manager = StateManager(audio_manager=MagicMock())
game_state = GameState(manager)
game_state.on_enter()

# Close overlays properly by modifying internal active flags
game_state.tutorial_overlay._active = False
game_state.objective_display._active = False

print("--- Simulated Game Loop Starting ---")
for frame in range(600): # 600 frames at 60 FPS = ~10 seconds of running
    # Update game state
    game_state.update(16) # 16 ms dt
    
    # Debug print player state and distance
    player_sprite = game_state.player.sprite
    if frame % 10 == 0 or len(game_state.npc_group) > 0:
        print(f"Frame {frame:03d} | Player state: {player_sprite.state} | is_running: {player_sprite.is_running} | dir: {player_sprite.direction} | world_distance: {game_state.world_distance} | npc_count: {len(game_state.npc_group)}")
    
    if len(game_state.npc_group) > 0:
        for npc in game_state.npc_group:
            print(f"  NPC: {npc.title} | Rect: {npc.rect} | Prompt range: {npc.can_interact}")
        print("-" * 40)
    
    # Terminate after passing distance 2000
    if game_state.world_distance >= 2000:
        print("Reached world distance 2000, ending simulation.")
        break
