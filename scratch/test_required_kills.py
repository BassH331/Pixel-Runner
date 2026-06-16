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
from src.game.entities.skeleton import Skeleton, SkeletonState
from v3x_zulfiqar_gideon import StateManager

# Create a dummy manager
manager = StateManager(audio_manager=MagicMock())

# Initialize GameState
game_state = GameState(manager)
game_state.on_enter()

# Close the tutorial and objective displays so the game updates
game_state.tutorial_overlay._active = False
game_state.objective_display._active = False

# Override spawn zones with a custom zone that has required_kills = 2
custom_zone = {
    "min_dist": 0,
    "max_dist": 1000,
    "max_skeletons": 5,
    "delay": 100,  # very short delay for rapid spawning
    "required_kills": 2,
    "tier": "minion"
}
game_state._spawn_zones = [custom_zone]

print("Starting test...")
print(f"Required kills config: {custom_zone['required_kills']}")

# Let's perform a few updates to spawn skeletons
game_state.update(0.1) # dt=100ms
print("Skeletons after first spawn check:", sum(1 for s in game_state.obstacle_group if isinstance(s, Skeleton)))

# Grab the spawned skeleton and make it take damage to die
spawned_skeletons = [s for s in game_state.obstacle_group if isinstance(s, Skeleton)]
assert len(spawned_skeletons) > 0, "No skeletons spawned!"

# Force skeleton death to trigger the kill counter
first_skeleton = spawned_skeletons[0]
print("Killing first skeleton...")
# We simulate take_damage which will transition state to DEATH
first_skeleton.take_damage(first_skeleton.max_health)
# Call game_state method to process death sound/kill count
game_state._apply_player_damage_to_enemy(game_state.player.sprite, first_skeleton)

print(f"Zone killed count: {custom_zone.get('killed_count', 0)}")
assert custom_zone.get('killed_count', 0) == 1, "Killed count did not increment to 1!"

# Let's update skeleton so it is cleaned up/removed
for _ in range(50):
    first_skeleton.update(0.1, 0)
print("Skeletons in obstacle group:", sum(1 for s in game_state.obstacle_group if isinstance(s, Skeleton)))

# Let's spawn another one
game_state.next_skeleton_spawn_time = 0
game_state.update(0.1)

# Grab the second skeleton and kill it too
spawned_skeletons = [s for s in game_state.obstacle_group if isinstance(s, Skeleton) and s.state != SkeletonState.DEATH]
assert len(spawned_skeletons) > 0, "Second skeleton did not spawn!"
second_skeleton = spawned_skeletons[0]
print("Killing second skeleton...")
second_skeleton.take_damage(second_skeleton.max_health)
game_state._apply_player_damage_to_enemy(game_state.player.sprite, second_skeleton)

print(f"Zone killed count: {custom_zone.get('killed_count', 0)}")
assert custom_zone.get('killed_count', 0) == 2, "Killed count did not increment to 2!"

# Let's clean up second skeleton
for _ in range(50):
    second_skeleton.update(0.1, 0)

# Now, with 2 kills completed, try to spawn again
game_state.next_skeleton_spawn_time = 0
game_state.update(0.1)

active_skeletons = sum(1 for s in game_state.obstacle_group if isinstance(s, Skeleton) and s.state != SkeletonState.DEATH)
print("Skeletons spawning after required kills met:", active_skeletons)
assert active_skeletons == 0, f"Error: Skeletons are still spawning! Count: {active_skeletons}"

print("Success! Required kills limit prevents automatic spawning successfully.")
