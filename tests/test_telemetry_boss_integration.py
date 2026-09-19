"""Unit test verifying boss telemetry tracking and log parsing integration."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import pygame as pg

from src.game.debug.gameplay_tracker import GameplayTracker
from src.game.debug.telemetry_log_parser import TelemetryLogParser
from src.game.boss.difficulty_manager import DifficultyManager


class TestTelemetryBossIntegration(unittest.TestCase):
    def setUp(self):
        pg.init()
        self.tmp_dir = tempfile.mkdtemp()
        self.log_dir = Path(self.tmp_dir)

    def tearDown(self):
        pg.quit()

    def test_parse_session_with_active_boss_data(self):
        """Test that TelemetryLogParser computes non-zero accuracies and combat dynamics
        when frame samples contain valid player and boss snapshots."""
        session_file = self.log_dir / "session_20260919_120000_001.jsonl"
        
        # Mock frame samples with active boss in detection/attack range
        events = []
        for i in range(1000):
            events.append({
                "type": "frame_sample",
                "timestamp_ms": 1000 + i * 16,
                "frame": i,
                "fps": 60.0,
                "player": {
                    "class": "Player",
                    "health": 100.0,
                    "position": [200, 300, 50, 100],
                    "state": "idle" if i % 2 == 0 else "defend",
                    "velocity": [0.0, 0.0]
                },
                "boss": {
                    "class": "FireWizard",
                    "health": 90.0,
                    "position": [380, 300, 80, 120],
                    "state": "chase",
                    "mana": 50.0,
                    "teleport_cooldown": 0.0
                }
            })
            
        # Add boss state change event
        events.append({
            "type": "event",
            "event_type": "boss_state_changed",
            "timestamp_ms": 1500,
            "old_state": "chase",
            "new_state": "attack",
            "new": "attack"
        })

        with open(session_file, "w", encoding="utf-8") as f:
            for ev in events:
                f.write(json.dumps(ev) + "\n")

        parser = TelemetryLogParser(log_dir=str(self.log_dir))
        parsed = parser.parse_session([session_file])

        self.assertGreater(parsed["total_active_combat_frames"], 0)
        self.assertGreater(parsed["time_in_detection_range_frames"], 0)
        self.assertGreater(parsed["time_in_attack_range_frames"], 0)

        # Test evaluation with DifficultyManager
        dm = DifficultyManager()
        analytics = dm.evaluate_sessions([parsed])

        self.assertEqual(analytics["valid_session_count"], 1)
        self.assertIn("accuracies", analytics)
        self.assertIn("combat_dynamics", analytics)
        self.assertGreater(analytics["accuracies"]["detection_accuracy"], 0.0)


if __name__ == "__main__":
    unittest.main()
