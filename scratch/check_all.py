import os
import sys

# Set dummy video driver for headless check
os.environ["SDL_VIDEODRIVER"] = "dummy"

import pygame as pg
pg.init()

plugins = [
    ("boss_editor", "BossEditorApp"),
    ("entity_editor", "HitboxEditorApp"),
    ("player_editor", "PlayerEditorApp"),
    ("wave_editor", "WaveEditorApp"),
    ("level_editor", "App"),
]

for module_name, class_name in plugins:
    print(f"Testing {module_name}...")
    try:
        module = __import__(module_name)
        app_class = getattr(module, class_name)
        # Instantiate to check constructor
        app = app_class()
        print(f"  -> {module_name} initialized successfully.")
    except Exception as e:
        print(f"  -> [FAIL] {module_name} failed: {e}")
        import traceback
        traceback.print_exc()
