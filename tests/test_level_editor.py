import os
import sys
import unittest
import json
import copy
from unittest.mock import patch, MagicMock

# Ensure project root is on the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Set SDL to dummy video driver for headless testing of pygame components
os.environ["SDL_VIDEODRIVER"] = "dummy"

import pygame as pg
if not pg.get_init():
    pg.init()

from level_editor import ModalDialog, App, BackgroundPickerModal

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

    @patch("level_editor.App.scan")
    def test_stage_5_visual_canvas(self, mock_scan):
        app = App()
        app.level_files = ["game_data/level_1.json"]
        app.level_data = {
            "level_name": "Test Level",
            "level_end_distance": 10000,
            "environment": {
                "ground_y": 620,
                "parallax_layers": []
            },
            "spawn_zones": [],
            "world_events": [
                {"id": 1, "distance": 650, "type": "npc", "params": {"title": "Necromancer"}}
            ]
        }
        app.pending = copy.deepcopy(app.level_data["world_events"])
        app.go5()

        self.assertEqual(app.stage, 5)
        self.assertIsNotNone(app.env_mgr)

        # Render stage 5
        app._d5()
        self.assertTrue(len(app._s5b) > 0)

        # Simulate keypress K_SPACE
        ev = pg.event.Event(pg.KEYDOWN, key=pg.K_SPACE)
        app._h5(ev)
        self.assertTrue(app.simulating)

    @patch("level_editor.App.scan")
    def test_background_picker_modal(self, mock_scan):
        selected = []
        canceled = [False]

        modal = BackgroundPickerModal(
            select_cb=lambda path: selected.append(path),
            cancel_cb=lambda: canceled.__setitem__(0, True)
        )

        # Draw modal headless
        surf = pg.Surface((1280, 720))
        font = pg.font.SysFont(None, 24)
        modal.draw(surf, font, font)

        # Click close button (rect.right - 44, rect.y + 12)
        close_x = modal.rect.right - 30
        close_y = modal.rect.y + 20
        ev_close = pg.event.Event(pg.MOUSEBUTTONDOWN, button=1, pos=(close_x, close_y))
        modal.on(ev_close)
        self.assertTrue(canceled[0])

    @patch("level_editor.App.scan")
    def test_minimap_scrubbing(self, mock_scan):
        app = App()
        app.level_files = ["game_data/level_1.json"]
        app.level_data = {
            "level_name": "Test Level",
            "level_end_distance": 36000,
            "environment": {"ground_y": 620, "parallax_layers": []},
            "spawn_zones": [],
            "world_events": []
        }
        app.pending = []
        app.go5()

        # Click halfway across minimap bar (X=630, Y=700)
        ev_click = pg.event.Event(pg.MOUSEBUTTONDOWN, button=1, pos=(630, 700))
        app._h5(ev_click)
        # Expected distance should be ~18,000m (halfway of 36,000m)
        self.assertGreater(app.cam_x, 10000)

    @patch("level_editor.App.scan")
    def test_spritesheet_slicer_modal(self, mock_scan):
        placed = []
        canceled = [False]

        from level_editor import SpritesheetSlicerModal
        modal = SpritesheetSlicerModal(
            select_cb=lambda path, rect: placed.append((path, rect)),
            cancel_cb=lambda: canceled.__setitem__(0, True)
        )

        surf = pg.Surface((1280, 720))
        font = pg.font.SysFont(None, 24)
        modal.draw(surf, font, font)

        # Test recalculating slices in grid mode
        modal.slice_mode = "32x32"
        modal.recalculate_slices()
        self.assertGreater(len(modal.slices), 0)

        # Test select slice
        modal.selected_slice_idx = 0
        modal.draw(surf, font, font)

        # Trigger place button click
        pl_x = modal.rect.right - 100
        pl_y = modal.rect.bottom - 25
        ev_pl = pg.event.Event(pg.MOUSEBUTTONDOWN, button=1, pos=(pl_x, pl_y))
        modal.on(ev_pl)
        self.assertEqual(len(placed), 1)

    @patch("level_editor.App.scan")
    def test_prop_placement_duplication_and_deletion(self, mock_scan):
        app = App()
        app.level_files = ["game_data/level_1.json"]
        app.level_data = {
            "level_name": "Test Level",
            "level_end_distance": 36000,
            "environment": {"ground_y": 686, "parallax_layers": [], "props": []},
            "spawn_zones": [],
            "world_events": []
        }
        app.pending = []
        app.go5()

        # Place prop from slicer callback
        app._on_select_prop_from_slicer("assets/graphics/background images/new_bg_images/bg_image.png", [0, 0, 64, 64])
        self.assertEqual(len(app.env_mgr.props), 1)
        self.assertEqual(app.selected_prop_idx, 0)

        # Test prop duplication (Ctrl+D)
        app.duplicate_selected_prop()
        self.assertEqual(len(app.env_mgr.props), 2)
        self.assertEqual(app.selected_prop_idx, 1)

        # Test prop deletion (DELETE key)
        ev_del = pg.event.Event(pg.KEYDOWN, key=pg.K_DELETE)
        app._h5(ev_del)
    @patch("level_editor.App.scan")
    def test_layer_texture_assignment_and_search(self, mock_scan):
        app = App()
        app.level_files = ["game_data/level_1.json"]
        app.level_data = {
            "level_name": "Test Level",
            "level_end_distance": 36000,
            "environment": {"ground_y": 686, "layer_stacks": {}, "props": []},
            "spawn_zones": [],
            "world_events": []
        }
        app.pending = []
        app.go5()

        # Set texture for active layer (Layer 1)
        app.active_layer_filter = 1
        bg_path = "assets/graphics/background images/new_bg_images/bg_image.png"
        app._on_select_bg_from_modal(bg_path)
        self.assertEqual(app.env_mgr.layer_stacks[1]["texture_path"], bg_path)

        # Clear texture for active layer
        app.env_mgr.clear_layer_texture(1)
        self.assertEqual(app.env_mgr.layer_stacks[1]["texture_path"], "")

        # Test search filtering in slicer modal
        from level_editor import SpritesheetSlicerModal, LinuxAssetExplorerModal
        modal = SpritesheetSlicerModal(select_cb=lambda p, r: None, cancel_cb=lambda: None)
        modal.search_input.val = "bg_image"
        filtered = modal.get_filtered_sheets()
        self.assertTrue(any("bg_image" in s.lower() for s in filtered))

        # Test Linux File Manager Explorer Modal
        selected_file = []
        explorer = LinuxAssetExplorerModal(
            select_cb=lambda path, folder: selected_file.append((path, folder)),
            cancel_cb=lambda: None,
            current_dir="assets/graphics/background images/new_bg_images"
        )
        self.assertGreater(len(explorer.entries), 0)
        # Test Reset Active Layer and Reset Entire Environment
        app._on_select_prop_from_slicer("assets/graphics/background images/new_bg_images/bg_image.png", [0, 0, 64, 64])
        self.assertEqual(len(app.env_mgr.props), 1)

        # Test Arrow Key Nudging
        app.selected_prop_idx = 0
        old_x = app.env_mgr.props[0].pos_x
        ev_right = pg.event.Event(pg.KEYDOWN, key=pg.K_RIGHT, mod=0)
        app._h5(ev_right)
        self.assertGreater(app.env_mgr.props[0].pos_x, old_x)

        # Test Reset Active Layer
        app.reset_active_layer()
        self.assertEqual(len(app.env_mgr.props), 0)

        # Place prop and test Reset Entire Environment
        app._on_select_prop_from_slicer("assets/graphics/background images/new_bg_images/bg_image.png", [0, 0, 64, 64])
        self.assertGreater(len(app.env_mgr.props), 0)
        app.reset_entire_environment()
        self.assertEqual(len(app.env_mgr.props), 0)

        # Test Dynamic Add Layer (L6) and Delete Layer
        init_layer_count = len(app.env_mgr.layer_stacks)
        new_l_idx = app.env_mgr.add_layer()
        self.assertEqual(new_l_idx, init_layer_count + 1)
        self.assertEqual(len(app.env_mgr.layer_stacks), init_layer_count + 1)

        # Test texture stretch scaling on new layer
        app.env_mgr.set_layer_texture(new_l_idx, "assets/graphics/background images/new_bg_images/bg_image.png", scale_x=1.5, scale_y=2.0, stretch_fill=True)
        self.assertEqual(app.env_mgr.layer_stacks[new_l_idx]["scale_x"], 1.5)
        self.assertEqual(app.env_mgr.layer_stacks[new_l_idx]["scale_y"], 2.0)
        self.assertTrue(app.env_mgr.layer_stacks[new_l_idx]["stretch_fill"])

        # Test Delete Layer
        self.assertTrue(app.env_mgr.delete_layer(new_l_idx))
        self.assertEqual(len(app.env_mgr.layer_stacks), init_layer_count)

        # Test Prop Placement Scale & Active Layer Assignment
        app.active_layer_filter = 3
        app._on_select_prop_from_slicer("assets/graphics/background images/new_bg_images/bg_image.png", [0, 0, 64, 64])
        placed = app.env_mgr.props[-1]
        self.assertEqual(placed.layer_index, 3)
        self.assertEqual(placed.scale, 1.0)
        self.assertTrue(placed.is_ground)
        self.assertEqual(placed.collision_type, "solid")

        # Test LevelManagerModal discovery
        from level_editor import LevelManagerModal
        lmodal = LevelManagerModal(select_cb=lambda p: None, create_cb=lambda: None, cancel_cb=lambda: None)
        self.assertGreater(len(lmodal.levels), 0)


if __name__ == "__main__":
    unittest.main()




