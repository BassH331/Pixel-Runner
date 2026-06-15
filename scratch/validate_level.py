import os
import json
import pygame as pg
from unittest.mock import MagicMock

def test_level_loading():
    pg.init()
    pg.display.set_mode((1280, 720))
    
    # Load level JSON
    with open("game_data/level_1.json", "r") as f:
        level_data = json.load(f)
        
    print("Level name:", level_data["level_name"])
    print("Spawn zones count:", len(level_data["spawn_zones"]))
    print("World events count:", len(level_data["world_events"]))
    
    # Verify Tower of Darkness NPC details
    events = level_data["world_events"]
    tower_event = next((e for e in events if e["distance"] == 2145), None)
    assert tower_event is not None, "Tower of Darkness event at 2145 should exist"
    assert tower_event["type"] == "npc", f"Tower of Darkness event type should be 'npc', got '{tower_event['type']}'"
    params = tower_event["params"]
    assert params["npc_type"] == "generic", "Tower should be generic NPC"
    assert params["sprite_dir"] == "assets/graphics/RedMoonTower", "Tower sprite_dir should be assets/graphics/RedMoonTower"
    assert params["scale"] == 2.0, "Tower scale should be 2.0"
    print("Tower of Darkness event validation: PASSED")
    
    # Verify Masked Stranger NPC details
    masked_event = next((e for e in events if e["distance"] == 400), None)
    assert masked_event is not None, "Masked Stranger event at 400 should exist"
    assert masked_event["params"]["scale"] == 6.0, f"Masked Stranger scale should be 6.0, got {masked_event['params']['scale']}"
    print("Masked Stranger event validation: PASSED")
    
    # Mock game state and run _handle_npc_spawn
    from src.game.states.game_state import GameState
    game_state_mock = MagicMock(spec=GameState)
    game_state_mock.width = 1280
    game_state_mock.height = 720
    game_state_mock.npc_group = pg.sprite.Group()
    
    # Call the actual _handle_npc_spawn logic on game_state_mock
    # We will bind _handle_npc_spawn from GameState to our mock
    import types
    game_state_mock._handle_npc_spawn = types.MethodType(GameState._handle_npc_spawn, game_state_mock)
    
    # Test spawning Masked Stranger
    print("Spawning Masked Stranger...")
    game_state_mock._handle_npc_spawn(masked_event["params"])
    assert len(game_state_mock.npc_group) == 1, "Should have spawned 1 NPC"
    npc = list(game_state_mock.npc_group)[0]
    print(f"Spawned Masked Stranger scale: {npc.scale}, rect: {npc.rect}")
    assert npc.scale == 6.0, f"Masked Stranger NPC instance scale should be 6.0, got {npc.scale}"
    
    # Test spawning Tower of Darkness
    print("Spawning Tower of Darkness...")
    game_state_mock.npc_group.empty()
    game_state_mock._handle_npc_spawn(tower_event["params"])
    assert len(game_state_mock.npc_group) == 1, "Should have spawned 1 NPC"
    tower_npc = list(game_state_mock.npc_group)[0]
    print(f"Spawned Tower of Darkness NPC scale: {tower_npc.scale}, rect: {tower_npc.rect}")
    assert tower_npc.scale == 2.0, f"Tower NPC instance scale should be 2.0, got {tower_npc.scale}"
    
    print("\nALL LEVEL CONFIGURATION AND SPAWN TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    test_level_loading()
