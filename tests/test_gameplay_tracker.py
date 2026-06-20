"""
Unit and Integration Tests for GameplayTracker
"""

import os
import sys
import shutil
import unittest
import json
from unittest.mock import MagicMock, patch

# Force SDL dummy video driver for headless test runner compatibility
os.environ["SDL_VIDEODRIVER"] = "dummy"

import pygame as pg

# Ensure project root is on path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.game.debug.gameplay_tracker import GameplayTracker

class TestGameplayTrackerConfig(unittest.TestCase):
    
    def test_default_config(self) -> None:
        tracker = GameplayTracker(overrides={"enabled": False})
        self.assertFalse(tracker.enabled)
        self.assertEqual(tracker.log_dir, "logs/gameplay_tracking")
        self.assertEqual(tracker.config["sample_every_n_frames"], 10)

    def test_overrides(self) -> None:
        tracker = GameplayTracker(overrides={
            "enabled": True,
            "sample_every_n_frames": 5,
            "log_dir": "test_logs_dir"
        })
        self.assertTrue(tracker.enabled)
        self.assertEqual(tracker.log_dir, "test_logs_dir")
        self.assertEqual(tracker.config["sample_every_n_frames"], 5)
        # Cleanup
        if os.path.exists("test_logs_dir"):
            shutil.rmtree("test_logs_dir")

    def test_env_overrides(self) -> None:
        os.environ["GAMEPLAY_TRACKING_ENABLED"] = "True"
        os.environ["GAMEPLAY_TRACKING_SAMPLE_EVERY_N_FRAMES"] = "3"
        os.environ["GAMEPLAY_TRACKING_LOG_DIR"] = "env_logs_dir"
        
        tracker = GameplayTracker()
        self.assertTrue(tracker.enabled)
        self.assertEqual(tracker.log_dir, "env_logs_dir")
        self.assertEqual(tracker.config["sample_every_n_frames"], 3)
        
        # Cleanup env
        del os.environ["GAMEPLAY_TRACKING_ENABLED"]
        del os.environ["GAMEPLAY_TRACKING_SAMPLE_EVERY_N_FRAMES"]
        del os.environ["GAMEPLAY_TRACKING_LOG_DIR"]
        if os.path.exists("env_logs_dir"):
            shutil.rmtree("env_logs_dir")


class TestGameplayTrackerLogging(unittest.TestCase):
    
    def setUp(self) -> None:
        self.test_dir = "temp_test_logs"
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
            
        self.tracker = GameplayTracker(overrides={
            "enabled": True,
            "log_dir": self.test_dir,
            "max_file_size_mb": 0.001, # ~1KB to trigger rotation quickly
            "console_output": False
        })

    def tearDown(self) -> None:
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_log_creation_and_append(self) -> None:
        self.tracker.log_event("test_event", {"some": "data"})
        
        log_path = self.tracker._get_current_log_path()
        self.assertTrue(os.path.exists(log_path))
        
        with open(log_path, "r") as f:
            lines = f.readlines()
            
        self.assertEqual(len(lines), 1)
        data = json.loads(lines[0])
        self.assertEqual(data["event"], "test_event")
        self.assertEqual(data["data"]["some"], "data")
        self.assertEqual(data["session_id"], self.tracker.session_id)

    def test_rolling_file_rotation(self) -> None:
        # Write enough lines to exceed 1KB and trigger rotation
        large_payload = "x" * 500
        for i in range(5):
            self.tracker.log_event(f"event_{i}", {"payload": large_payload})
            
        # Manifest should be updated and file index should be > 1
        self.assertGreater(self.tracker.file_index, 1)
        
        # Verify both log files exist
        file_1 = os.path.join(self.test_dir, f"session_{self.tracker.session_id}_001.jsonl")
        file_2 = os.path.join(self.test_dir, f"session_{self.tracker.session_id}_002.jsonl")
        self.assertTrue(os.path.exists(file_1))
        self.assertTrue(os.path.exists(file_2))

    def test_manifest_file(self) -> None:
        manifest_path = os.path.join(self.test_dir, "latest_session.json")
        self.assertTrue(os.path.exists(manifest_path))
        
        with open(manifest_path, "r") as f:
            manifest = json.load(f)
            
        self.assertEqual(manifest["session_id"], self.tracker.session_id)
        self.assertEqual(manifest["config"]["log_dir"], self.test_dir)


class TestGameplayTrackerSignatures(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls) -> None:
        pg.init()
        pg.display.set_mode((1280, 720))

    def test_signature_computation_and_matching(self) -> None:
        tracker = GameplayTracker(overrides={"enabled": False})
        
        # Create a simple surface with a distinct color pattern
        surf = pg.Surface((40, 40), pg.SRCALPHA)
        surf.fill((0, 0, 0, 0)) # Transparent
        # Draw some non-transparent pixels
        pg.draw.circle(surf, (255, 0, 0, 255), (20, 20), 10)
        
        # Test signature
        sig = tracker._compute_signature(surf)
        self.assertEqual(sig["size"], [40, 40])
        self.assertGreater(sig["non_transparent_count"], 0)
        self.assertEqual(len(sig["colors"]), 5)
        
        # Mock entity
        entity = MagicMock()
        entity.state = "RUN"
        entity.animation_index = 0.0
        entity.image = surf
        entity.facing_left = False
        entity.animations = {"RUN": [surf]}
        
        # Cache signatures
        tracker._cache_signatures(entity, None)
        self.assertTrue(tracker._verify_signature(entity, is_boss=False))
        
        # Flip entity
        entity.facing_left = True
        # Since the shape is a center circle, a horizontal flip should still match!
        self.assertTrue(tracker._verify_signature(entity, is_boss=False))

    def test_position_mismatch(self) -> None:
        tracker = GameplayTracker(overrides={"enabled": False})
        
        # Create a surface
        surf = pg.Surface((40, 40), pg.SRCALPHA)
        surf.fill((0, 0, 0, 0))
        pg.draw.circle(surf, (255, 0, 0, 255), (20, 20), 5)
        
        # Entity with aligned hitbox
        entity = MagicMock()
        entity.image = surf
        entity.rect = pg.Rect(100, 100, 40, 40)
        entity.image_offset = pg.math.Vector2(0, 0)
        
        self.assertFalse(tracker._check_position_mismatch(entity))
        
        # Entity with far away visual rendering (large offset)
        entity.image_offset = pg.math.Vector2(400, 0)
        self.assertTrue(tracker._check_position_mismatch(entity))


class TestGameStateIntegration(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls) -> None:
        pg.init()
        pg.display.set_mode((1280, 720))

    @patch("v3x_zulfiqar_gideon.asset_manager.AssetManager.get_texture")
    @patch("v3x_zulfiqar_gideon.asset_manager.AssetManager.get_sound")
    def test_game_state_wire_up(self, mock_snd, mock_tex) -> None:
        mock_tex.return_value = pg.Surface((32, 32))
        mock_snd.return_value = None
        
        # Configure UI theme so GameState init doesn't fail
        from v3x_zulfiqar_gideon import UITheme
        UITheme.configure_buttons(
            assets={
                "big": ("dummy_big", "dummy_big_p"),
                "medium": ("dummy_med", "dummy_med_p"),
                "cancel": ("dummy_cancel", "dummy_cancel_p"),
                "new_start": ("dummy_new", "dummy_new_p"),
            },
            font_path="dummy_font"
        )
        UITheme.configure_notifications(
            banner_path="dummy_banner",
            icons={"gray": "dummy_gray", "red": "dummy_red", "yellow": "dummy_yellow"},
            font_path="dummy_font"
        )
        UITheme.configure_overlays(
            stone_path="dummy_stone",
            parchment_path="dummy_parchment",
            title_font_path="dummy_font",
            body_font_path="dummy_font"
        )
        
        from src.game.states.game_state import GameState
        mgr = MagicMock()
        mgr.audio_manager = MagicMock()
        
        # Instantiate GameState with tracking enabled
        with patch.dict(os.environ, {"GAMEPLAY_TRACKING_ENABLED": "True", "GAMEPLAY_TRACKING_LOG_DIR": "temp_int_logs"}):
            state = GameState(mgr)
            self.assertTrue(state.tracker.enabled)
            self.assertEqual(state.tracker.log_dir, "temp_int_logs")
            
            # Tick state update to ensure no exceptions are raised
            state.update(16.6)
            
            # Clean up
            if os.path.exists("temp_int_logs"):
                shutil.rmtree("temp_int_logs")

if __name__ == "__main__":
    unittest.main()
