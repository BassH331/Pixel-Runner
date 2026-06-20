"""Unit tests for the GameplayTracker telemetry system.

Tests cover:
- Configuration loading and validation
- JSONL file creation and rotation
- Event logging verification
- Session manifest tracking
- Pixel signature caching
- Headless environment compatibility
"""

import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

try:
    import pygame as pg
    PYGAME_AVAILABLE = True
except ImportError:
    PYGAME_AVAILABLE = False

from src.game.debug.gameplay_tracker import GameplayTracker, EventType


class TestGameplayTrackerConfig(unittest.TestCase):
    """Test configuration loading and validation."""
    
    def test_default_config(self):
        """Test that default config is applied when none provided."""
        tracker = GameplayTracker()
        self.assertFalse(tracker.enabled)
        self.assertEqual(tracker.sample_every_n_frames, 10)
        self.assertEqual(tracker.log_dir, Path("logs/gameplay_tracking"))
        self.assertEqual(tracker.max_file_size_bytes, 5 * 1024 * 1024)
    
    def test_config_override(self):
        """Test that user config overrides defaults."""
        custom_config = {
            "enabled": True,
            "sample_every_n_frames": 5,
            "log_dir": "custom_logs",
            "max_file_size_mb": 10,
        }
        tracker = GameplayTracker(config=custom_config)
        self.assertTrue(tracker.enabled)
        self.assertEqual(tracker.sample_every_n_frames, 5)
        self.assertEqual(tracker.log_dir, Path("custom_logs"))
        self.assertEqual(tracker.max_file_size_bytes, 10 * 1024 * 1024)
    
    def test_partial_config_override(self):
        """Test that partial config merges with defaults."""
        partial_config = {"enabled": True}
        tracker = GameplayTracker(config=partial_config)
        self.assertTrue(tracker.enabled)
        self.assertEqual(tracker.sample_every_n_frames, 10)  # Default


class TestGameplayTrackerSessionManagement(unittest.TestCase):
    """Test session initialization, cleanup, and manifest management."""
    
    def setUp(self):
        """Set up temporary directory for tests."""
        self.test_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Clean up temporary directory."""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def test_session_initialization(self):
        """Test that session initializes log directory and first file."""
        config = {
            "enabled": True,
            "log_dir": self.test_dir,
        }
        tracker = GameplayTracker(config=config)
        
        self.assertTrue(os.path.exists(self.test_dir))
        self.assertIsNotNone(tracker.current_file_path)
        self.assertTrue(tracker.current_file_path.parent.exists())
    
    def test_manifest_creation(self):
        """Test that session manifest is created correctly."""
        config = {
            "enabled": True,
            "log_dir": self.test_dir,
        }
        tracker = GameplayTracker(config=config)
        tracker.flush()
        
        manifest_path = Path(self.test_dir) / "latest_session.json"
        self.assertTrue(manifest_path.exists())
        
        with open(manifest_path, "r") as f:
            manifest = json.load(f)
        
        self.assertIn("session_timestamp", manifest)
        self.assertIn("session_start", manifest)
        self.assertIn("latest_file", manifest)
        self.assertIn("config", manifest)


@unittest.skipUnless(PYGAME_AVAILABLE, "pygame not available")
class TestGameplayTrackerEventLogging(unittest.TestCase):
    """Test event logging functionality."""
    
    def setUp(self):
        """Set up temporary directory and tracker."""
        self.test_dir = tempfile.mkdtemp()
        self.config = {
            "enabled": True,
            "log_dir": self.test_dir,
            "event_logging_enabled": True,
        }
        self.tracker = GameplayTracker(config=self.config)
        pg.init()
    
    def tearDown(self):
        """Clean up."""
        self.tracker.close()
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
        pg.quit()
    
    def test_log_event_string(self):
        """Test logging event with string event type."""
        self.tracker.log_event("damage_dealt", {
            "target": "Skeleton",
            "damage": 10,
        })
        
        self.assertEqual(self.tracker.event_count, 1)
        self.assertTrue(self.tracker.current_file_path.exists())
    
    def test_log_event_enum(self):
        """Test logging event with EventType enum."""
        self.tracker.log_event(EventType.DAMAGE_DEALT, {
            "target": "Skeleton",
            "damage": 10,
        })
        
        self.assertEqual(self.tracker.event_count, 1)
    
    def test_event_content(self):
        """Test that logged events have correct structure."""
        self.tracker.log_event("test_event", {
            "key1": "value1",
            "key2": 42,
        })
        
        with open(self.tracker.current_file_path, "r") as f:
            line = f.readline()
        
        entry = json.loads(line)
        self.assertEqual(entry["type"], "event")
        self.assertEqual(entry["event_type"], "test_event")
        self.assertEqual(entry["key1"], "value1")
        self.assertEqual(entry["key2"], 42)
        self.assertIn("timestamp_ms", entry)
    
    def test_disabled_tracking(self):
        """Test that events are not logged when tracking is disabled."""
        disabled_tracker = GameplayTracker(config={"enabled": False})
        disabled_tracker.log_event("test_event", {"data": "value"})
        
        self.assertEqual(disabled_tracker.event_count, 0)


@unittest.skipUnless(PYGAME_AVAILABLE, "pygame not available")
class TestGameplayTrackerFrameSampling(unittest.TestCase):
    """Test frame sampling functionality."""
    
    def setUp(self):
        """Set up temporary directory and tracker."""
        self.test_dir = tempfile.mkdtemp()
        self.config = {
            "enabled": True,
            "log_dir": self.test_dir,
            "sample_every_n_frames": 10,
        }
        self.tracker = GameplayTracker(config=self.config)
        pg.init()
    
    def tearDown(self):
        """Clean up."""
        self.tracker.close()
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
        pg.quit()
    
    def test_sample_frame(self):
        """Test frame sampling with flexible kwargs."""
        self.tracker.sample_frame(
            frame=100,
            fps=60,
            player_health=45,
        )
        
        self.assertEqual(self.tracker.frame_count, 1)
        self.assertTrue(self.tracker.current_file_path.exists())
    
    def test_frame_content(self):
        """Test that frame samples have correct structure."""
        self.tracker.sample_frame(
            frame=50,
            fps=59.5,
        )
        
        with open(self.tracker.current_file_path, "r") as f:
            line = f.readline()
        
        entry = json.loads(line)
        self.assertEqual(entry["type"], "frame_sample")
        self.assertEqual(entry["frame"], 50)
        self.assertAlmostEqual(entry["fps"], 59.5)
        self.assertIn("timestamp_ms", entry)


@unittest.skipUnless(PYGAME_AVAILABLE, "pygame not available")
class TestGameplayTrackerFileRotation(unittest.TestCase):
    """Test JSONL file rotation functionality."""
    
    def setUp(self):
        """Set up temporary directory and tracker with small file size."""
        self.test_dir = tempfile.mkdtemp()
        self.config = {
            "enabled": True,
            "log_dir": self.test_dir,
            "max_file_size_mb": 0.001,  # ~1KB for testing
        }
        self.tracker = GameplayTracker(config=self.config)
        pg.init()
    
    def tearDown(self):
        """Clean up."""
        self.tracker.close()
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
        pg.quit()
    
    def test_file_rotation(self):
        """Test that files rotate when size limit is reached."""
        first_file = self.tracker.current_file_path
        
        # Log events until rotation occurs
        for i in range(50):
            self.tracker.log_event("test_event", {
                "index": i,
                "data": "x" * 100,
            })
        
        second_file = self.tracker.current_file_path
        
        # Files should be different after rotation
        self.assertNotEqual(str(first_file), str(second_file))
        self.assertTrue(first_file.exists())
        self.assertTrue(second_file.exists())


@unittest.skipUnless(PYGAME_AVAILABLE, "pygame not available")
class TestGameplayTrackerPixelSignatures(unittest.TestCase):
    """Test pixel signature caching and verification."""
    
    def setUp(self):
        """Set up temporary directory and tracker."""
        self.test_dir = tempfile.mkdtemp()
        self.config = {
            "enabled": True,
            "log_dir": self.test_dir,
            "pixel_signatures_enabled": True,
        }
        self.tracker = GameplayTracker(config=self.config)
        pg.init()
    
    def tearDown(self):
        """Clean up."""
        self.tracker.close()
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
        pg.quit()
    
    def test_cache_pixel_signature(self):
        """Test caching pixel signatures."""
        # Create a simple test surface
        surface = pg.Surface((32, 32), pg.SRCALPHA)
        surface.fill((255, 0, 0, 255))
        
        self.tracker.cache_pixel_signature(
            entity_id="test_entity_1",
            entity_type="player",
            image=surface,
            bounding_box=(0, 0, 32, 32),
            sample_points=[(0, 0), (16, 16), (31, 31)],
        )
        
        self.assertIn("test_entity_1", self.tracker.pixel_signatures)
        sig = self.tracker.pixel_signatures["test_entity_1"]
        self.assertEqual(sig["entity_type"], "player")
        self.assertEqual(sig["bounding_box"], (0, 0, 32, 32))
    
    def test_verify_visual_alignment(self):
        """Test visual alignment verification."""
        # Create surfaces for caching and verification
        surface1 = pg.Surface((32, 32), pg.SRCALPHA)
        surface1.fill((255, 0, 0, 255))
        
        self.tracker.cache_pixel_signature(
            entity_id="test_entity_2",
            entity_type="enemy",
            image=surface1,
            bounding_box=(0, 0, 32, 32),
            sample_points=[(0, 0), (16, 16), (31, 31)],
        )
        
        surface2 = pg.Surface((32, 32), pg.SRCALPHA)
        surface2.fill((255, 0, 0, 255))
        
        result = self.tracker.verify_visual_alignment(
            entity_id="test_entity_2",
            current_image=surface2,
        )
        
        self.assertTrue(result["verified"])
        self.assertIn("checks", result)


class TestGameplayTrackerHeadlessMode(unittest.TestCase):
    """Test compatibility with headless environments."""
    
    def setUp(self):
        """Set up temporary directory."""
        self.test_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Clean up."""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    @patch('pygame.time.get_ticks', return_value=1000)
    def test_headless_initialization(self, mock_ticks):
        """Test that tracker initializes without pygame display."""
        # This should not raise an error even without pygame display
        config = {
            "enabled": True,
            "log_dir": self.test_dir,
        }
        tracker = GameplayTracker(config=config)
        
        self.assertTrue(tracker.enabled)
        self.assertIsNotNone(tracker.current_file_path)
        tracker.close()


if __name__ == "__main__":
    unittest.main()
