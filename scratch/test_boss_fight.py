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
from src.game.entities.player import Player, PlayerState

# Create a dummy manager
manager = StateManager(audio_manager=MagicMock())

# Initialize GameState
game_state = GameState(manager)
game_state.on_enter()

# Close the tutorial and objective displays so the game updates
game_state.tutorial_overlay._active = False
game_state.objective_display._active = False

print("Starting Boss Fight end-to-end verification test...")

# 1. Trigger Boss Spawn Event
boss_params = {
    "title": "Grom, The Undead King",
    "scale": 2.5,
    "health": 120.0,
    "tier": "boss",
    "_event_id": 99,
    "_event_distance": 200.0
}
game_state._handle_boss_spawn(boss_params)

# Verify boss spawned in obstacle group
boss_sprites = [s for s in game_state.obstacle_group if getattr(s, "is_boss", False)]
assert len(boss_sprites) == 1, "Boss entity was not spawned!"
boss = boss_sprites[0]

print(f"Boss Spawned successfully: {boss.boss_title} | Scale: {boss.scale} | Health: {boss._health}/{boss._max_health}")
assert boss.boss_title == "Grom, The Undead King", "Boss title mismatch"
assert boss.scale == 2.5, f"Expected scale 2.5, got {boss.scale}"
assert boss._health == 120.0, "Expected health 120.0"
assert boss._max_health == 120.0, "Expected max_health 120.0"
assert boss.tier == "boss", "Expected tier 'boss'"
assert boss.event_id == 99, "Expected event_id 99"

# 2. Verify Scroll Lock Logic
# Stub is_running and direction to always return True/1 for the test on the Player class
# so that player.update() does not reset them
setattr(Player, "is_running", property(lambda self: True))
setattr(Player, "direction", property(lambda self: 1))

player = game_state.player.sprite
player._direction = 1

# Run state update
game_state.update(0.1)

# Scroll speed should be 0 because boss is active
print(f"Player is running. bg_scroll_speed under active boss: {game_state.bg_scroll_speed}")
assert game_state.bg_scroll_speed == 0, f"Expected scroll speed to be locked to 0, got {game_state.bg_scroll_speed}"
assert game_state._is_boss_active() == True, "Boss should be flagged as active"

# 3. Verify Boss Health Bar rendering does not crash
# Create a dummy screen surface to draw on
screen = pg.Surface((1280, 720))
try:
    game_state.draw(screen)
    print("Boss Health Bar rendered successfully without crashes.")
except Exception as e:
    print(f"Error rendering Boss Health Bar: {e}")
    sys.exit(1)

# 4. Defeat Boss and Verify Scroll Unlock & Victory Transition
print("Simulating defeating the boss...")
# Force death state
boss.take_damage(boss._max_health)
# Process death/defeat in game state
game_state._apply_player_damage_to_enemy(player, boss)

print(f"Is boss active after defeat? {game_state._is_boss_active()}")
assert game_state._is_boss_active() == False, "Boss should not be active after defeat"

# Dismiss the victory screen so gameplay updates normally in this test script
game_state.objective_display._active = False

# Run state update again
game_state.update(0.1)

# With boss defeated, bg_scroll_speed should be restored (since player is running)
expected_speed = game_state.max_bg_scroll_speed * player.direction
print(f"Player is running. bg_scroll_speed after boss defeat: {game_state.bg_scroll_speed} (expected {expected_speed})")
assert game_state.bg_scroll_speed == expected_speed, f"Scroll speed did not restore! Got {game_state.bg_scroll_speed}"

# Level completion flag should be set
print(f"Level complete state: {game_state._level_complete}")
assert game_state._level_complete == True, "Level complete was not triggered upon final boss death"

print("\nAll tests PASSED successfully!")
pg.quit()
sys.exit(0)
