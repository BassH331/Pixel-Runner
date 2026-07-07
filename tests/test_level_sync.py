import os
import sys
import unittest
import tempfile
import json
from unittest.mock import patch, MagicMock

# Ensure project root is on the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pygame as pg
if not pg.get_init():
    pg.init()

from src.game.entities.hitbox_registry import HitboxRegistry, HitboxMargins

class TestLevelSync(unittest.TestCase):
    def setUp(self):
        # Clear cache first to ensure test isolation
        HitboxRegistry._cached_config = {}
        # Create a temp file for entity dimensions configuration
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_config_path = os.path.join(self.temp_dir.name, "entity_dimensions.json")
        
        # Setup initial content for config
        initial_data = {
            "wizard_npc": {
                "left": 0,
                "right": 0,
                "top": 0,
                "bottom": 0,
                "ground_offset": 34,
                "scale": 2.0
            },
            "generic_npc_masked_man": {
                "left": 0,
                "right": 0,
                "top": 0,
                "bottom": 0,
                "ground_offset": 34,
                "scale": 2.0
            }
        }
        with open(self.temp_config_path, "w") as f:
            json.dump(initial_data, f)

    def tearDown(self):
        self.temp_dir.cleanup()
        HitboxRegistry._cached_config = {}
        HitboxRegistry._rollback_checkpoint = {}

    def test_sync_with_level_config(self):
        # Patch CONFIG_PATH and ConfigClient.fetch_config to point to our temp file and avoid network requests
        with patch("src.game.entities.hitbox_registry.CONFIG_PATH", self.temp_config_path), \
             patch("src.game.services.ConfigClient.fetch_config", return_value=None):
            # Load config to clear cache and start fresh
            HitboxRegistry._cached_config = {}
            HitboxRegistry._load_config()
            
            # Verify initial scale
            self.assertEqual(HitboxRegistry.get_margins("wizard_npc").scale, 2.0)
            self.assertEqual(HitboxRegistry.get_margins("generic_npc_masked_man").scale, 2.0)
            
            # Level data containing different scales
            level_data = {
                "world_events": [
                    {
                        "type": "npc",
                        "params": {
                            "npc_type": "wizard",
                            "scale": 3.5
                        }
                    },
                    {
                        "type": "npc",
                        "params": {
                            "npc_type": "generic",
                            "sprite_dir": "assets/graphics/masked_man",
                            "scale": 4.5
                        }
                    },
                    {
                        "type": "npc",
                        "params": {
                            "npc_type": "generic",
                            "sprite_dir": "assets/graphics/new_character/idle",
                            "scale": 5.0
                        }
                    }
                ]
            }
            
            # Sync
            HitboxRegistry.sync_with_level_config(level_data)
            
            # Verify scales are updated in cache
            self.assertEqual(HitboxRegistry.get_margins("wizard_npc").scale, 3.5)
            self.assertEqual(HitboxRegistry.get_margins("generic_npc_masked_man").scale, 4.5)
            self.assertEqual(HitboxRegistry.get_margins("generic_npc_new_character").scale, 5.0)
            
            # Verify scales are saved on disk
            with open(self.temp_config_path, "r") as f:
                saved_data = json.load(f)
            self.assertEqual(saved_data["wizard_npc"]["scale"], 3.5)
            self.assertEqual(saved_data["generic_npc_masked_man"]["scale"], 4.5)
            self.assertEqual(saved_data["generic_npc_new_character"]["scale"], 5.0)

if __name__ == "__main__":
    unittest.main()
