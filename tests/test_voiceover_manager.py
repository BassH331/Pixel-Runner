"""
Unit tests for VoiceoverManager runtime playback system.
"""

import json
import os
import tempfile
import unittest
import pygame as pg

from src.game.audio.voiceover_manager import VoiceoverManager


class TestVoiceoverManager(unittest.TestCase):
    """Tests loading, querying, and fallback behavior of VoiceoverManager."""

    @classmethod
    def setUpClass(cls):
        pg.init()
        pg.mixer.init()

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.manifest_path = os.path.join(self.temp_dir.name, "voice_manifest.json")
        self.output_dir = os.path.join(self.temp_dir.name, "voiceovers")
        os.makedirs(self.output_dir, exist_ok=True)

        self.sample_manifest = {
            "output_dir": self.output_dir,
            "voices": {
                "test_voice": {
                    "display_name": "Test Voice",
                    "exaggeration": 0.5,
                    "cfg_weight": 0.5,
                }
            },
            "lines": [
                {
                    "id": "line_1",
                    "voice": "test_voice",
                    "text": "Hello world!",
                    "output_file": "line_1.wav",
                },
                {
                    "id": "line_missing",
                    "voice": "test_voice",
                    "text": "Missing audio file",
                    "output_file": "line_missing.wav",
                },
            ],
        }
        with open(self.manifest_path, "w", encoding="utf-8") as f:
            json.dump(self.sample_manifest, f)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_load_manifest_success(self):
        """Test loading a valid manifest file."""
        vm = VoiceoverManager(manifest_path=self.manifest_path)
        success = vm.load_manifest()
        self.assertTrue(success)
        self.assertIn("line_1", vm._lines)

    def test_load_manifest_missing_file(self):
        """Test graceful failure when manifest file does not exist."""
        vm = VoiceoverManager(manifest_path="non_existent_manifest.json")
        success = vm.load_manifest()
        self.assertFalse(success)

    def test_has_line_returns_false_for_missing_wav(self):
        """test has_line returns False if the wav file is not on disk."""
        vm = VoiceoverManager(manifest_path=self.manifest_path)
        vm.load_manifest()

        self.assertFalse(vm.has_line("line_missing"))

    def test_play_line_missing_file_fallback(self):
        """Test playing a missing voice line returns False without raising exception."""
        vm = VoiceoverManager(manifest_path=self.manifest_path)
        vm.load_manifest()

        result = vm.play_line("line_missing")
        self.assertFalse(result)
        self.assertFalse(vm.is_playing())

    def test_play_line_unknown_id(self):
        """Test playing an unknown line ID returns False."""
        vm = VoiceoverManager(manifest_path=self.manifest_path)
        vm.load_manifest()

        result = vm.play_line("unknown_line_id")
        self.assertFalse(result)


if __name__ == "__main__":
    unittest.main()
