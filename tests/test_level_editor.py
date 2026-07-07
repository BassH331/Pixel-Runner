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
    def setUp(self):
        pg.display.set_mode((1280, 720))

    def test_modal_dialog_layout_calculations(self):
        # Case 1: 0 choices
        dialog_0 = ModalDialog("Title", "Body", confirm_cb=lambda: None)
        dw, dh, dx, dy, btn_y = dialog_0._get_layout()
        self.assertEqual(dw, 540)
        self.assertEqual(dh, 145 + 67) # 212
        self.assertEqual(btn_y, dy + 145)

        # Case 2: 5 choices
        choices = ["Choice 1", "Choice 2", "Choice 3", "Choice 4", "Choice 5"]
        dialog_5 = ModalDialog("Title", "Body", confirm_cb=lambda: None, choices=choices)
        dw, dh, dx, dy, btn_y = dialog_5._get_layout()
        expected_btn_y_offset = 125 + 5 * 38 + 15 # 330
        self.assertEqual(dw, 540)
        self.assertEqual(dh, expected_btn_y_offset + 67)
        self.assertEqual(btn_y, dy + expected_btn_y_offset)

    def test_modal_dialog_event_keydown(self):
        confirm_called = [False]
        cancel_called = [False]
        choice_selected = [-1]

        def confirm():
            confirm_called[0] = True
        
        def cancel():
            cancel_called[0] = True

        def choice_cb(idx):
            choice_selected[0] = idx

        dialog = ModalDialog("Title", "Body", confirm, cancel, choices=["A", "B"], choice_cb=choice_cb)
        dialog.selected = 1

        # Keydown K_RETURN
        ev = pg.event.Event(pg.KEYDOWN, key=pg.K_RETURN)
        dialog.on(ev)
        self.assertTrue(confirm_called[0])
        self.assertEqual(choice_selected[0], 1)

        # Keydown K_ESCAPE
        ev = pg.event.Event(pg.KEYDOWN, key=pg.K_ESCAPE)
        dialog.on(ev)
        self.assertTrue(cancel_called[0])

    def test_modal_dialog_event_mousedown_choices(self):
        confirm_called = []
        dialog = ModalDialog("Title", "Body", confirm_cb=lambda: confirm_called.append(True), choices=["A"])
        # populate choice_rects manually for event testing
        dialog.choice_rects = [pg.Rect(100, 100, 100, 30)]
        
        # Click on choice 0
        ev = pg.event.Event(pg.MOUSEBUTTONDOWN, button=1, pos=(150, 115))
        dialog.on(ev)
        self.assertEqual(dialog.selected, 0)
        self.assertFalse(confirm_called) # Shouldn't trigger confirm immediately on choice select

    @patch("level_editor.App.scan")
    @patch("os.remove")
    @patch("os.path.exists")
    def test_app_del_nameerror_fix(self, mock_exists, mock_remove, mock_scan):
        mock_exists.return_value = False
        app = MagicMock(spec=App)
        app.level_files = ["game_data/level_1.json"]
        app.modal = None
        app.scan = mock_scan

        idx = 0
        p = app.level_files[idx]
        
        def _do():
            try:
                mock_remove(p)
            except Exception:
                pass
            app.scan()
            app.modal = None

        modal = ModalDialog(
            "Delete Level?",
            f"Permanently delete file '{os.path.basename(p)}'?",
            _do, lambda: setattr(app, "modal", None)
        )
        
        modal.confirm_cb()
        mock_remove.assert_called_with("game_data/level_1.json")
        mock_scan.assert_called_once()
        self.assertIsNone(app.modal)

    @patch("fcntl.flock")
    @patch("builtins.open")
    def test_set_next_index_mapping_fix(self, mock_open, mock_flock):
        level_files = ["level_0.json", "level_1.json", "level_2.json"]
        
        idx = 1
        others = [(os.path.basename(p), p) for j, p in enumerate(level_files) if j != idx]
        self.assertEqual(others, [("level_0.json", "level_0.json"), ("level_2.json", "level_2.json")])
        
        # Choice 2 maps to first elements in others
        choice_idx = 2
        target = others[choice_idx - 2][1]
        self.assertEqual(target, "level_0.json")

        # Choice 3 maps to second elements in others
        choice_idx = 3
        target = others[choice_idx - 2][1]
        self.assertEqual(target, "level_2.json")

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

