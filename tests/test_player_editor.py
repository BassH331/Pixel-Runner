"""Unit tests for the Player Animation Configurator & Hitbox Tuner (player_editor.py)."""

import json
import os
import shutil
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Set video driver to dummy to allow initializing Pygame without display window
os.environ["SDL_VIDEODRIVER"] = "dummy"

import pygame as pg
# Make sure pygame is initialized
pg.init()

from player_editor import PlayerEditorApp, Slider, Checkbox, DEFAULT_PLAYER_CONFIGS, DEFAULT_ATTACK_CONFIGS

class TestPlayerEditor(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        
        # Mock loading of assets to avoid actually loading images during test
        self.load_anim_patch = patch.object(PlayerEditorApp, "load_all_animations")
        self.load_anim_patch.start()

        self.app = PlayerEditorApp()
        self.app.config_dir = self.test_dir
        self.app.config_path = os.path.join(self.test_dir, "player_config.json")
        self.app.load_config()
        self.app.mode = "STATES"
        self.app.load_state_parameters("IDLE")

    def tearDown(self):
        self.load_anim_patch.stop()
        shutil.rmtree(self.test_dir)

    def test_default_config_loading(self):
        """Test that default player configurations are correctly initialized."""
        self.assertEqual(len(self.app.config), len(DEFAULT_PLAYER_CONFIGS))
        self.assertEqual(self.app.config["IDLE"]["animation_speed"], 0.15)
        self.assertEqual(len(self.app.attack_config), len(DEFAULT_ATTACK_CONFIGS))

    def test_save_and_backup_transaction(self):
        """Test that saving configurations writes player_config.json and creates a backup."""
        # Create an initial file in the nested structure
        initial_data = {
            "states": self.app.config,
            "attacks": self.app.attack_config
        }
        with open(self.app.config_path, "w") as f:
            json.dump(initial_data, f)

        # Modify a state value
        self.app.mode = "STATES"
        self.app.anim_speed_slider.val = 0.45
        self.app.checkboxes[0].val = False # Disable loops
        
        # Save
        self.app.request_save_config()
        
        # Verify file exists
        self.assertTrue(os.path.exists(self.app.config_path))
        with open(self.app.config_path, "r") as f:
            saved_data = json.load(f)
            
        self.assertEqual(saved_data["states"]["IDLE"]["animation_speed"], 0.45)
        self.assertFalse(saved_data["states"]["IDLE"]["loops"])

        # Verify backup was created
        self.app.scan_backups()
        self.assertGreater(len(self.app.backups), 0)
        self.assertTrue(self.app.backups[0].startswith("player_config.backup_"))

    def test_rollback(self):
        """Test rollback to a previous backup configuration."""
        initial_data = {
            "states": self.app.config,
            "attacks": self.app.attack_config
        }
        # Create an initial file
        with open(self.app.config_path, "w") as f:
            json.dump(initial_data, f)

        # 1. Set slider to 0.10 and save original state (backs up initial file)
        self.app.mode = "STATES"
        self.app.anim_speed_slider.val = 0.10
        self.app.request_save_config()
        
        # Sleep to ensure different timestamp for the next backup file
        time.sleep(1.1)

        # 2. Modify to a new state 0.99 and save again (backs up 0.10 file)
        self.app.mode = "STATES"
        self.app.anim_speed_slider.val = 0.99
        self.app.request_save_config()

        # Scan backups
        self.app.scan_backups()
        self.assertGreaterEqual(len(self.app.backups), 2)

        # 3. Select the newest backup (index 0 is the backup created in step 2 containing the 0.10 config)
        self.app.mode = "STATES"
        self.app.selected_backup_index = 0
        self.app.rollback_config()

        # Check that value rolled back to 0.10
        self.assertEqual(self.app.config["IDLE"]["animation_speed"], 0.10)

    def test_reset_defaults(self):
        """Test resetting configurations to baseline defaults."""
        self.app.config["IDLE"]["animation_speed"] = 0.99
        self.app.reset_defaults()
        self.assertEqual(self.app.config["IDLE"]["animation_speed"], 0.15)

    def test_attack_config_modification_and_saving(self):
        """Test that attack configurator values can be modified and saved."""
        self.app.mode = "ATTACKS"
        self.app.load_attack_parameters("THRUST_ATTACK_CONFIG")
        
        # Modify general attack sliders
        self.app.attack_sliders[0].val = 99.0  # base damage
        self.app.attack_sliders[1].val = 25.0  # knockback force
        self.app.attack_can_hit_multiple_cb.val = False
        
        # Modify active frame timeline role & hitbox
        self.app.selected_attack_frame = 3
        self.app.load_frame_parameters()
        self.app.frame_role_checkboxes[0].val = True  # is hit active
        
        # Re-load frame parameters to enable sliders after checking hit active
        self.app.save_current_frame_parameters()
        self.app.load_frame_parameters()
        self.app.frame_sliders[0].val = 190.0  # offset_x
        self.app.frame_sliders[2].val = 300.0  # width
        
        # Save attack config
        self.app.request_save_config()
        
        # Load from file to verify save
        with open(self.app.config_path, "r") as f:
            saved_data = json.load(f)
            
        saved_atk = saved_data["attacks"]["THRUST_ATTACK_CONFIG"]
        self.assertEqual(saved_atk["base_damage"], 99.0)
        self.assertEqual(saved_atk["knockback_force"], 25.0)
        self.assertFalse(saved_atk["can_hit_multiple"])
        self.assertEqual(saved_atk["hitbox_data"]["3"]["offset_x"], 190)
        self.assertEqual(saved_atk["hitbox_data"]["3"]["width"], 300)

    def test_speed_curve_modification_and_isolation(self):
        """Test that speed curve overrides are saved per-frame and do not bleed to adjacent frames on transition."""
        self.app.mode = "SPEED_CURVES"
        self.app.load_speed_curve_parameters("RUN")
        
        # Verify frame 0 starts with no override
        self.assertEqual(self.app.selected_speed_curve_frame, 0)
        self.assertFalse(self.app.frame_override_cb.val)
        
        # Enable override for frame 0 and set speed to 0.45
        self.app.frame_override_cb.val = True
        self.app.frame_speed_slider.val = 0.45
        self.app.save_current_speed_curve_parameters()
        
        # Advance timeline slider to frame 1 and trigger frame change logic
        self.app.timeline_slider.val = 1.0
        self.app.check_speed_curve_frame_change()
        
        # Verify new selected frame is 1
        self.assertEqual(self.app.selected_speed_curve_frame, 1)
        # Verify frame 1 has no override (does not inherit frame 0's speed/override!)
        self.assertFalse(self.app.frame_override_cb.val)
        
        # Enable override for frame 1 and set speed to 0.75
        self.app.frame_override_cb.val = True
        self.app.frame_speed_slider.val = 0.75
        self.app.save_current_speed_curve_parameters()
        
        # Go back to frame 0
        self.app.timeline_slider.val = 0.0
        self.app.check_speed_curve_frame_change()
        
        # Verify frame 0 still has its override and correct speed value
        self.assertEqual(self.app.selected_speed_curve_frame, 0)
        self.assertTrue(self.app.frame_override_cb.val)
        self.assertEqual(self.app.frame_speed_slider.val, 0.45)

if __name__ == "__main__":
    unittest.main()
