import os
import sys
import unittest
import json
from unittest.mock import patch, MagicMock

# Ensure project root is on the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Set SDL to dummy video driver for headless testing of pygame components
os.environ["SDL_VIDEODRIVER"] = "dummy"

import pygame as pg
if not pg.get_init():
    pg.init()

from level_editor import ModalDialog, App

class TestLevelEditor(unittest.TestCase):
    @patch("level_editor.App.scan")
    @patch("os.makedirs")
    @patch("builtins.open")
    @patch("os.path.exists")
    def test_create_new_level_workflow(self, mock_exists, mock_open, mock_makedirs, mock_scan):
        mock_exists.return_value = False
        app = App()
        
        # Test default/initial state
        self.assertFalse(app.new_level_mode)
        self.assertIsNone(app.new_level_title_input)
        self.assertIsNone(app.new_level_filename_input)
        
        # Call the start new callback via _d1()
        app._d1()
        # Find the "+ CREATE NEW" button
        create_btn = next(b for b in app._s1b if b.label == "+ CREATE NEW")
        create_btn.cb()
        
        self.assertTrue(app.new_level_mode)
        self.assertIsNotNone(app.new_level_title_input)
        self.assertIsNotNone(app.new_level_filename_input)
        
        # Enter valid details safely
        if app.new_level_title_input:
            app.new_level_title_input.val = "Test Adventure"
        if app.new_level_filename_input:
            app.new_level_filename_input.val = "test_level"
        
        # Call _d1 again to populate buttons in creation mode
        app._d1()

        confirm_btn = next(b for b in app._s1b if b.label == "CREATE")
        
        # Mock file writing
        mock_file = MagicMock()
        mock_open.return_value.__enter__.return_value = mock_file
        
        confirm_btn.cb()
        
        # Verify directory creation and file opening
        mock_makedirs.assert_called_with("game_data", exist_ok=True)
        mock_open.assert_called_with("game_data/level_test_level.json", "w")
        
        # Verify scanner called and mode reset
        self.assertEqual(mock_scan.call_count, 2)
        self.assertFalse(app.new_level_mode)


if __name__ == "__main__":
    unittest.main()

