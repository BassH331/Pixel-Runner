"""
Unit tests for tools/voice_manifest.json validation and hash utilities.
"""

import json
import os
import unittest


class TestVoiceManifest(unittest.TestCase):
    """Validates the structure and sanity of the voice manifest configuration."""

    MANIFEST_PATH = "tools/voice_manifest.json"

    def test_manifest_file_exists(self):
        """Ensure voice_manifest.json exists on disk."""
        self.assertTrue(
            os.path.exists(self.MANIFEST_PATH),
            f"Manifest file does not exist at {self.MANIFEST_PATH}",
        )

    def test_manifest_schema_structure(self):
        """Ensure voice_manifest.json has required root keys: output_dir, voices, lines."""
        with open(self.MANIFEST_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.assertIn("output_dir", data)
        self.assertIn("voices", data)
        self.assertIn("lines", data)

        self.assertIsInstance(data["output_dir"], str)
        self.assertIsInstance(data["voices"], dict)
        self.assertIsInstance(data["lines"], list)

    def test_voice_profiles(self):
        """Ensure all voice profiles have valid fields (exaggeration, cfg_weight)."""
        with open(self.MANIFEST_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)

        voices = data["voices"]
        self.assertGreater(len(voices), 0, "Manifest should define at least one voice profile")

        for voice_id, profile in voices.items():
            self.assertIn("display_name", profile)
            self.assertIn("exaggeration", profile)
            self.assertIn("cfg_weight", profile)
            self.assertGreaterEqual(profile["exaggeration"], 0.0)
            self.assertLessEqual(profile["exaggeration"], 1.0)

    def test_lines_reference_valid_voices(self):
        """Ensure each line references a voice defined in voices dict."""
        with open(self.MANIFEST_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)

        voices = data["voices"]
        lines = data["lines"]

        for line in lines:
            self.assertIn("id", line)
            self.assertIn("voice", line)
            self.assertIn("text", line)
            self.assertIn("output_file", line)
            self.assertIn(
                line["voice"],
                voices,
                f"Line '{line['id']}' references unknown voice '{line['voice']}'",
            )


if __name__ == "__main__":
    unittest.main()
