import os
import sys
import json

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

# Set dummy video driver for headless execution
os.environ["SDL_VIDEODRIVER"] = "dummy"

import pygame as pg
from boss_editor import BossEditorApp

def test_editor_functionality():
    print("Initializing BossEditorApp in headless mode...")
    app = BossEditorApp()
    
    expected_keys = [
        "wizard",
        "skeleton",
        "skeleton_minion",
        "goblin",
        "green_monster",
        "skeleton_zombie",
        "blood_zombie",
        "bat"
    ]
    
    print("Checking registered boss keys...")
    assert len(app.boss_keys) == len(expected_keys), f"Expected {len(expected_keys)} keys, got {len(app.boss_keys)}"
    for key in expected_keys:
        assert key in app.boss_keys, f"Missing expected key: {key}"
        print(f"  - Discovered entity: {key}")

    print("\nVerifying select, config loading, saving, and simulation for each entity:")
    for key in expected_keys:
        print(f"\nTesting entity: {key}")
        
        # Select the entity
        app.select_boss(key)
        assert app.selected_boss == key, f"Failed to select {key}"
        
        # Check config exists in memory
        config = app.boss_configs[key]
        schema = app.bosses[key]["schema"]
        
        # Verify defaults are present
        for param, default_val in schema["defaults"].items():
            assert param in config, f"Parameter {param} not found in config for {key}"
            print(f"  * {param}: {config[param]} (default: {default_val})")
            
        # Verify save config functionality
        print("  * Saving configuration...")
        app.confirm_save_config()
        cfg_file_path = schema["config_file"]
        assert os.path.exists(cfg_file_path), f"Saved config file {cfg_file_path} not found"
        
        # Load and verify JSON file content
        with open(cfg_file_path, "r") as f:
            saved_data = json.load(f)
        for param, default_val in schema["defaults"].items():
            assert param in saved_data, f"Saved JSON missing parameter {param}"
            
        # Verify simulation tick runs without raising exception
        print("  * Initializing and ticking simulation...")
        app.init_simulation_state()
        app.update_simulation(0.016)
        print(f"  * Simulation tick OK. Event log: {app.sim_events[-1]}")
        
    print("\nAll programmatic checks passed successfully!")

if __name__ == "__main__":
    try:
        test_editor_functionality()
    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
