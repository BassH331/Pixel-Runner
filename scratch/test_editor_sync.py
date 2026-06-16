import os
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from level_editor import App
from src.game.entities.hitbox_registry import HitboxRegistry

def test_editor_scale_propagation():
    # Initialize LevelEditor App
    editor = App()
    editor.active_idx = 0
    # Simulate editor loading level 1
    editor.load(0)
    
    # Verify starting state
    print("Initial level_1.json event scale:", editor.pending[0]["params"]["scale"])
    print("Initial registry scale for masked man:", HitboxRegistry.get_margins("generic_npc_masked_man").scale)
    
    # Find the NPC event (id: 1)
    npc_idx = next(i for i, ev in enumerate(editor.pending) if ev["id"] == 1)
    
    # Init stage 3 for this NPC event
    editor.go3("edit", "npc", npc_idx)
    # Set the slider value directly to 4.5
    editor.s3_ui["scale"].val = 4.5
    
    # Submit stage 3 (calls _read_s3 and updates event & registry)
    editor.submit_s3()
    
    # Verify in-memory updates
    npc_event_after = next(ev for ev in editor.pending if ev["id"] == 1)
    print("In-memory level event scale after submit:", npc_event_after["params"]["scale"])
    print("In-memory registry scale after submit:", HitboxRegistry.get_margins("generic_npc_masked_man").scale)
    
    assert npc_event_after["params"]["scale"] == 4.5
    assert HitboxRegistry.get_margins("generic_npc_masked_man").scale == 4.5
    
    # Simulate committing changes to disk
    editor.commit()
    
    # Re-read files from disk to make sure they match
    with open("game_data/level_1.json", "r") as f:
        level_data = json.load(f)
    with open("game_data/entity_dimensions.json", "r") as f:
        dimensions_data = json.load(f)
        
    disk_level_scale = level_data["world_events"][0]["params"]["scale"]
    disk_registry_scale = dimensions_data["generic_npc_masked_man"]["scale"]
    
    print("Disk level_1.json scale after commit:", disk_level_scale)
    print("Disk entity_dimensions.json scale after commit:", disk_registry_scale)
    
    assert disk_level_scale == 4.5
    assert disk_registry_scale == 4.5
    
    print("TEST PASSED: Editor scale propagation successfully updated both files in sync!")

if __name__ == "__main__":
    import pygame as pg
    pg.init()
    pg.display.set_mode((100, 100))
    try:
        test_editor_scale_propagation()
    finally:
        pg.quit()
