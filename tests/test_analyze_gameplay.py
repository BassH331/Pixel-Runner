"""Unit tests for the gameplay analysis engine (analyze_gameplay.py)."""

import json
import os
import tempfile
import unittest
from pathlib import Path
from analyze_gameplay import analyze_session, generate_report

class TestAnalyzeGameplay(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.log_path = Path(self.test_dir) / "session_test.jsonl"
        self.report_path = Path(self.test_dir) / "report_test.md"

    def tearDown(self):
        if self.log_path.exists():
            os.remove(self.log_path)
        if self.report_path.exists():
            os.remove(self.report_path)
        os.rmdir(self.test_dir)

    def write_mock_logs(self, entries):
        with open(self.log_path, "w") as f:
            for entry in entries:
                f.write(json.dumps(entry) + "\n")

    def test_empty_log(self):
        """Test behavior when telemetry file is empty."""
        self.write_mock_logs([])
        result = analyze_session(self.log_path)
        self.assertIsNone(result)

    def test_basic_analysis(self):
        """Test session analysis calculation with simple trace entries."""
        entries = [
            {
                "type": "frame_sample",
                "timestamp_ms": 1000,
                "fps": 60.0,
                "player": {
                    "state": "idle",
                    "animation_index": 0.0,
                    "inputs": {"roll": False}
                }
            },
            {
                "type": "frame_sample",
                "timestamp_ms": 1016,
                "fps": 60.0,
                "player": {
                    "state": "idle",
                    "animation_index": 1.0,
                    "inputs": {"roll": True} # Press roll
                }
            },
            {
                "type": "frame_sample",
                "timestamp_ms": 1032,
                "fps": 60.0,
                "player": {
                    "state": "roll", # Swapped state
                    "animation_index": 0.0,
                    "is_invincible": True,
                    "inputs": {"roll": False}
                }
            },
            {
                "type": "event",
                "event_type": "damage_received",
                "timestamp_ms": 1032,
                "damage": 10.0
            }
        ]
        self.write_mock_logs(entries)
        
        analysis = analyze_session(self.log_path)
        self.assertIsNotNone(analysis)
        if analysis:
            self.assertEqual(analysis["total_frames"], 3)
            self.assertEqual(analysis["avg_fps"], 60.0)
            self.assertEqual(analysis["duration_sec"], 0.032)
            self.assertEqual(analysis["rolls"], 1)
            self.assertEqual(analysis["damage_avoided"], 1)
            self.assertIn("ROLL", analysis["state_pcts"])
            # Latency: input was pressed at 1016, state changed at 1032. Diff = 16ms
            self.assertEqual(analysis["avg_latency_ms"], 16.0)

            # Test report generation
            generate_report(analysis, self.report_path)
            self.assertTrue(self.report_path.exists())
            with open(self.report_path, "r") as f:
                content = f.read()
                self.assertIn("Gameplay Telemetry", content)
                self.assertIn("16.0 ms", content)

if __name__ == "__main__":
    unittest.main()
