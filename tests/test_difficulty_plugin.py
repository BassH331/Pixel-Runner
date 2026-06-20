"""Unit tests for the Telemetry-based Difficulty Manager and Preview Scaler components."""

import json
import os
import shutil
import tempfile
import unittest
import pygame as pg
from pathlib import Path

from src.game.debug.telemetry_log_parser import TelemetryLogParser
from src.game.boss.difficulty_manager import DifficultyManager
from src.game.editor.preview_scaler import PreviewScaler

class TestDifficultyPlugin(unittest.TestCase):
    def setUp(self) -> None:
        # Create a temporary directory for telemetry logs
        self.test_dir = tempfile.mkdtemp()
        self.parser = TelemetryLogParser(log_dir=self.test_dir)
        self.manager = DifficultyManager()

    def tearDown(self) -> None:
        shutil.rmtree(self.test_dir)

    def test_rotated_log_grouping(self) -> None:
        # Write mock chunk files for two different sessions
        session_1_chunks = ["session_20260620_020000_001.jsonl", "session_20260620_020000_002.jsonl"]
        session_2_chunks = ["session_20260620_033000_001.jsonl"]

        for filename in session_1_chunks + session_2_chunks:
            p = Path(self.test_dir) / filename
            p.write_text("{}", encoding="utf-8") # Empty JSON

        groups = self.parser._group_rotated_files()
        self.assertEqual(len(groups), 2)
        self.assertIn("session_20260620_020000", groups)
        self.assertIn("session_20260620_033000", groups)
        self.assertEqual(len(groups["session_20260620_020000"]), 2)
        self.assertEqual(len(groups["session_20260620_033000"]), 1)

        # Verify get_latest_session
        latest = self.parser.get_latest_session()
        self.assertIsNotNone(latest)
        self.assertEqual(latest[0], "session_20260620_033000")

        # Verify get_recent_sessions
        recent = self.parser.get_recent_sessions(limit=5)
        self.assertEqual(len(recent), 2)
        self.assertEqual(recent[0][0], "session_20260620_033000")
        self.assertEqual(recent[1][0], "session_20260620_020000")

    def test_parser_with_mock_events(self) -> None:
        # Create a mock telemetry session with frame samples and state changes
        log_file = Path(self.test_dir) / "session_20260620_120000_001.jsonl"
        
        events = [
            {"type": "frame_sample", "timestamp_ms": 1000, "fps": 60.0, "player": {"position": [100, 100, 32, 64]}, "boss": {"position": [400, 100, 64, 64], "state": "chase", "is_stagnant": False, "is_recharging": False, "mana": 100.0, "teleport_cooldown": 0.0}},
            {"type": "frame_sample", "timestamp_ms": 2000, "fps": 60.0, "player": {"position": [150, 100, 32, 64]}, "boss": {"position": [350, 100, 64, 64], "state": "idle", "is_stagnant": False, "is_recharging": False, "mana": 100.0, "teleport_cooldown": 0.0}},
            {"type": "event", "event_type": "boss_state_changed", "timestamp_ms": 2500, "old_state": "idle", "new_state": "attack"},
            {"type": "event", "event_type": "damage_received", "timestamp_ms": 2600, "damage": 15.0},
            {"type": "event", "event_type": "damage_dealt", "timestamp_ms": 2800, "damage": 25.0},
            {"type": "frame_sample", "timestamp_ms": 3000, "fps": 60.0, "player": {"position": [200, 100, 32, 64]}, "boss": {"position": [360, 100, 64, 64], "state": "attack", "is_stagnant": False, "is_recharging": False, "mana": 65.0, "teleport_cooldown": 0.0}},
            {"type": "frame_sample", "timestamp_ms": 61000, "fps": 60.0, "player": {"position": [200, 100, 32, 64]}, "boss": {"position": [360, 100, 64, 64], "state": "idle", "is_stagnant": False, "is_recharging": False, "mana": 65.0, "teleport_cooldown": 0.0}},
        ]
        
        with open(log_file, "w") as f:
            for ev in events:
                f.write(json.dumps(ev) + "\n")

        parsed = self.parser.parse_session([log_file])
        self.assertEqual(parsed["total_frames"], 4)
        self.assertEqual(parsed["player_damage_taken"], 15.0)
        self.assertEqual(parsed["boss_damage_taken"], 25.0)
        self.assertEqual(parsed["boss_attacks"], 1)
        self.assertAlmostEqual(parsed["duration_sec"], 60.0)

        # Evaluate session metrics
        eval_result = self.manager.evaluate_sessions([parsed])
        self.assertEqual(eval_result["valid_session_count"], 1)
        self.assertEqual(eval_result["confidence"], "low") # only 1 session
        self.assertIn("recommended_difficulty", eval_result)

    def test_difficulty_presets_and_clamping(self) -> None:
        # Easy preset parameters should be correctly retrieved and clamped
        easy_config = self.manager.get_preset_config("EASY")
        self.assertEqual(easy_config["max_mana"], 80.0)
        self.assertEqual(easy_config["spell_mana_cost"], 45.0)
        self.assertEqual(easy_config["stagnant_duration"], 4.5)
        self.assertGreaterEqual(easy_config["teleport_dist_max"], easy_config["teleport_dist_min"])

        # Nightmare preset
        nm_config = self.manager.get_preset_config("NIGHTMARE")
        self.assertEqual(nm_config["max_mana"], 150.0)
        self.assertEqual(nm_config["spell_mana_cost"], 20.0)
        self.assertEqual(nm_config["stagnant_duration"], 1.0)
        self.assertGreaterEqual(nm_config["teleport_dist_max"], nm_config["teleport_dist_min"])

    def test_preview_scaler_auto_fit(self) -> None:
        # Create a mock surface
        surf = pg.Surface((100, 200), pg.SRCALPHA)
        # Draw some non-transparent pixels inside it
        surf.fill((255, 255, 255, 255), pg.Rect(10, 20, 80, 160))

        preview_rect = pg.Rect(430, 80, 820, 400)
        floor_y = 420

        fit = PreviewScaler.calculate_auto_fit(surf, preview_rect, floor_y, margin=0.90)
        self.assertFalse(fit["fallback"])
        self.assertGreater(fit["scale"], 0)
        self.assertLessEqual(fit["scaled_width"], preview_rect.width)
        # Bottom of visible bounding box is exactly at floor_y
        visible_bottom_y = fit["y_pos"] + (fit["visible_rect"][1] + fit["visible_rect"][3]) * fit["scale"]
        self.assertAlmostEqual(visible_bottom_y, floor_y, delta=1.5)

    def test_short_session_defeat(self) -> None:
        # Create a mock session where the boss is defeated in 15 seconds
        parsed = {
            "session_id": "session_20260620_150000",
            "files_parsed": ["file.jsonl"],
            "total_valid_events": 10,
            "malformed_lines": 0,
            "duration_sec": 15.0,
            "active_combat_duration_sec": 15.0,
            "total_frames": 900,
            "avg_fps": 60.0,
            "player_damage_taken": 0.0,
            "boss_damage_taken": 100.0,
            "player_hits_received": 0,
            "boss_hits_received": 5,
            "boss_attacks": 0,
            "successful_boss_attacks": 0,
            "boss_spell_casts": 0,
            "projectile_hits": 0,
            "projectile_misses": 0,
            "time_in_detection_range_frames": 100,
            "time_in_attack_range_frames": 50,
            "boss_detected_in_range_frames": 0,
            "boss_attacked_in_range_attacks": 0,
            "bad_attacks": 0,
            "missed_opportunities": 0,
            "boss_defeated": True
        }

        # Evaluate session metrics (should bypass 60-second limit and recommend Nightmare)
        eval_result = self.manager.evaluate_sessions([parsed])
        self.assertEqual(eval_result["valid_session_count"], 1)
        self.assertEqual(eval_result["recommended_difficulty"], "NIGHTMARE")
        self.assertEqual(eval_result["confidence"], "low")

    def test_adjust_difficulty_level(self) -> None:
        # Start with medium configuration
        cfg = self.manager.get_preset_config("MEDIUM")
        
        # Raise difficulty
        harder = self.manager.adjust_difficulty_level(cfg, 1)
        self.assertGreater(harder["max_mana"], cfg["max_mana"])
        self.assertLess(harder["stagnant_duration"], cfg["stagnant_duration"])
        self.assertLessEqual(harder["teleport_dist_min"], cfg["teleport_dist_min"])

        # Lower difficulty
        easier = self.manager.adjust_difficulty_level(cfg, -1)
        self.assertLess(easier["max_mana"], cfg["max_mana"])
        self.assertGreater(easier["stagnant_duration"], cfg["stagnant_duration"])

