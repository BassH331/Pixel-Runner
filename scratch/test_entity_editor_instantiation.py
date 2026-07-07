import os
import sys
from unittest.mock import MagicMock

# Set pygame dummy driver
os.environ["SDL_VIDEODRIVER"] = "dummy"

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + "/.."))

import pygame as pg
pg.init()

from entity_editor import HitboxEditorApp

print("Starting test...")
app = HitboxEditorApp()
for idx, config in enumerate(app.entity_configs):
    app.active_index = idx
    print(f"Testing entity index {idx}: key={config['key']}, type={config['type']}")
    try:
        app.reload_entity()
        print("Success!")
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"FAILED: {e}")
