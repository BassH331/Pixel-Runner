"""Unit tests for the Boss Configuration Editor's Green Monster integration (boss_editor.py)."""

import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Set video driver to dummy to allow initializing Pygame without display window
os.environ["SDL_VIDEODRIVER"] = "dummy"

import pygame as pg
# Make sure pygame is initialized
pg.init()

from boss_editor import BossEditorApp, Slider

class TestBossEditorGreenMonster(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        
        # Override game_data paths for test isolation
        self.wizard_config_path = os.path.join(self.test_dir, "enemy_wizard_config.json")
        self.green_monster_config_path = os.path.join(self.test_dir, "enemy_green_monster_config.json")
        
        # Write dummy configs
        with open(self.wizard_config_path, "w") as f:
            json.dump({
                "max_health": 50.0,
                "max_mana": 100.0,
                "spell_mana_cost": 35.0,
                "stagnant_duration": 3.0,
                "teleport_dist_min": 380,
                "teleport_dist_max": 450,
                "mana_recharge_rate": 50.0,
                "chase_delay_duration": 0.8,
                "attack_cooldown_min": 1.2,
                "attack_cooldown_max": 2.0,
                "spidey_sense": 0.2
            }, f)
            
        with open(self.green_monster_config_path, "w") as f:
            json.dump({
                "max_health": 40.0,
                "max_mana": 100.0,
                "spell_mana_cost": 35.0,
                "stagnant_duration": 3.0,
                "teleport_dist_min": 380,
                "teleport_dist_max": 450,
                "mana_recharge_rate": 50.0,
                "chase_delay_duration": 0.8,
                "attack_cooldown_min": 1.0,
                "attack_cooldown_max": 1.8,
                "spidey_sense": 0.0
            }, f)

        # Mock loading of actual image files
        self.mock_animations = {
            "green_monster": {
                "IDLE": [pg.Surface((10, 10)) for _ in range(15)],
                "CHASE": [pg.Surface((10, 10)) for _ in range(12)],
                "ATTACK": [pg.Surface((10, 10)) for _ in range(7)],
                "HURT": [pg.Surface((10, 10)) for _ in range(5)],
                "DEATH": [pg.Surface((10, 10)) for _ in range(11)]
            },
            "wizard": {
                "IDLE": [pg.Surface((10, 10)) for _ in range(8)],
                "CHASE": [pg.Surface((10, 10)) for _ in range(8)],
                "ATTACK": [pg.Surface((10, 10)) for _ in range(8)],
                "HURT": [pg.Surface((10, 10)) for _ in range(4)],
                "DEATH": [pg.Surface((10, 10)) for _ in range(4)]
            }
        }
        
        self.load_all_patch = patch.object(BossEditorApp, "load_all_animations", lambda self_app: None)
        self.load_all_patch.start()

        self.app = BossEditorApp()
        self.app.animations = self.mock_animations
        
        # Override configuration file paths in the schema
        self.app.bosses["wizard"]["schema"]["config_file"] = self.wizard_config_path
        self.app.bosses["green_monster"]["schema"]["config_file"] = self.green_monster_config_path
        
        # Re-load configurations from temporary path
        self.app.load_boss_config("wizard")
        self.app.load_boss_config("green_monster")
        
        # Select wizard by default, then switch
        self.app.select_boss("wizard")

    def tearDown(self):
        self.load_all_patch.stop()
        shutil.rmtree(self.test_dir)

    def test_green_monster_schema_and_sliders(self):
        """Test that selecting the green monster loads its correct schema and sliders."""
        self.app.select_boss("green_monster")
        self.assertEqual(self.app.selected_boss, "green_monster")
        
        # Verify specific walking-wizard-style sliders are present
        self.assertIn("max_mana", self.app.sliders)
        self.assertIn("spell_mana_cost", self.app.sliders)
        self.assertIn("spidey_sense", self.app.sliders)
        
        # Verify they got loaded with the correct values from config
        self.assertEqual(self.app.sliders["max_mana"].val, 100.0)
        self.assertEqual(self.app.sliders["spell_mana_cost"].val, 35.0)
        self.assertEqual(self.app.sliders["spidey_sense"].val, 0.0)

    def test_green_monster_simulation_update(self):
        """Test that green monster simulation runs update_wizard_simulation and behaves correctly."""
        self.app.select_boss("green_monster")
        self.app.set_mode("SIMULATION")
        self.assertEqual(self.app.mode, "SIMULATION")
        
        # Initial simulation state check
        self.assertEqual(self.app.sim_boss_state, "CHASE")
        self.assertEqual(self.app.sim_boss_mana, 100.0)
        
        # Force distance to 200 (sweet spot)
        self.app.sim_boss_x = 300
        self.app.sim_player_x = 100 # distance = 200
        
        # Run simulation update step to trigger attack
        self.app.sim_boss_attack_cooldown = 0.0
        self.app.update_simulation(0.1)
        self.assertEqual(self.app.sim_boss_state, "ATTACK")
        
        # Advance animation to frame 4 to trigger projectile (toxic glob / fireball) cast
        self.app.frame_index = 4.0
        self.app.update_simulation(0.01)
        self.assertTrue(self.app.sim_boss_has_cast)
        self.assertEqual(len(self.app.sim_fireballs), 1)
        self.assertEqual(self.app.sim_boss_mana, 65.0) # 100 - 35
        
        # Check that event log is populated correctly
        self.assertTrue(any("Toxic glob cast" in log for log in self.app.sim_events))

    def test_green_monster_presets(self):
        """Test that preset saving and loading functions correctly for the green monster."""
        self.app.select_boss("green_monster")
        self.app.presets_path = os.path.join(self.test_dir, "green_monster_presets.json")
        self.app.load_presets()
        
        # Load preset 2 (HARD)
        self.app.apply_preset_slot(2)
        # HARD preset for wizard/green_monster sets max_mana to 120.0
        self.assertEqual(self.app.sliders["max_mana"].val, 120.0)
        self.assertEqual(self.app.sliders["spidey_sense"].val, 0.6)
        
        # Modify and save to slot 2
        self.app.sliders["max_mana"].val = 145.0
        self.app.save_to_active_preset()
        
        # Clear and load presets again
        self.app.presets_data = {}
        self.app.load_presets()
        self.app.apply_preset_slot(2)
        self.assertEqual(self.app.sliders["max_mana"].val, 145.0)

    def test_green_monster_save_constraints(self):
        """Test that saving the green monster config enforces constraints and backups."""
        self.app.select_boss("green_monster")
        
        # Set invalid constraint: teleport_dist_min (500) > teleport_dist_max (300)
        self.app.sliders["teleport_dist_min"].val = 500
        self.app.sliders["teleport_dist_max"].val = 300
        
        self.app.confirm_save_config()
        
        # Verify they were clamped to be equal (dist_max updated to dist_min)
        self.assertEqual(self.app.sliders["teleport_dist_max"].val, 500)
        
        # Verify JSON file has correct updated fields
        with open(self.green_monster_config_path, "r") as f:
            config = json.load(f)
        self.assertEqual(config["teleport_dist_min"], 500)
        self.assertEqual(config["teleport_dist_max"], 500)

if __name__ == "__main__":
    unittest.main()
