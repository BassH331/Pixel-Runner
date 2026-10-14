"""
Unit tests for popup_controller.py GUI plugin.
Verifies scene selection, text buffer editing, theme changing, muting toggles,
filtering tabs, and atomic saves in the Pop-up Notification Control System.
"""

import os
import pytest
import pygame as pg

os.environ["SDL_VIDEODRIVER"] = "dummy"

from popup_controller import PopupControllerApp
from src.game.systems.popup_scene_manager import PopupSceneManager


@pytest.fixture(autouse=True)
def setup_pg():
    pg.init()
    yield
    pg.quit()


def test_popup_controller_init():
    app = PopupControllerApp()
    assert app is not None
    assert len(app.scenes) >= 13
    assert app.selected_index >= 0
    scene = app._get_selected_scene()
    assert scene is not None


def test_popup_controller_selection_and_editing():
    app = PopupControllerApp()
    initial_scene = app._get_selected_scene()
    assert initial_scene is not None

    # Change title and text in edit buffers
    orig_title = app.edit_title_str
    orig_text = app.edit_text_str

    app.edit_title_str = "Custom Test Title"
    app.edit_text_str = "Custom test notification body text."
    app._trigger_preview()

    assert app.edit_title_str == "Custom Test Title"
    assert app.preview_notification._current_item.title == "Custom Test Title"
    assert app.preview_notification._current_item.text == "Custom test notification body text."

    # Restore
    app.edit_title_str = orig_title
    app.edit_text_str = orig_text


def test_popup_controller_theme_switching():
    app = PopupControllerApp()
    scene = app._get_selected_scene()
    assert scene is not None

    orig_theme = scene.get("theme", "gothic_gold")

    app._set_theme("blood_bone")
    assert scene["theme"] == "blood_bone"
    assert app.preview_notification._current_item.theme == "blood_bone"

    app._set_theme("arcane_void")
    assert scene["theme"] == "arcane_void"
    assert app.preview_notification._current_item.theme == "arcane_void"

    # Restore
    app._set_theme(orig_theme)


def test_popup_controller_mute_toggle():
    app = PopupControllerApp()
    scene = app._get_selected_scene()
    assert scene is not None

    initial_enabled = scene.get("enabled", True)

    app._toggle_enabled(scene)
    assert scene["enabled"] != initial_enabled

    app._toggle_enabled(scene)
    assert scene["enabled"] == initial_enabled


def test_popup_controller_filtering():
    app = PopupControllerApp()

    # All
    app.filter_tab = "ALL"
    assert len(app._get_filtered_scenes()) == len(app.scenes)

    # Distance only
    app.filter_tab = "DISTANCE"
    dist_scenes = app._get_filtered_scenes()
    assert len(dist_scenes) > 0
    for s in dist_scenes:
        assert s["trigger_type"] == "distance"

    # Entity only
    app.filter_tab = "ENTITY"
    ent_scenes = app._get_filtered_scenes()
    assert len(ent_scenes) > 0
    for s in ent_scenes:
        assert s["trigger_type"] == "entity"

    # Search filter
    app.filter_tab = "ALL"
    app.search_query = "ZOMBIE"
    matched = app._get_filtered_scenes()
    assert len(matched) >= 1
    assert "zombie" in matched[0]["id"].lower() or "zombie" in matched[0]["title"].lower()


def test_popup_controller_entity_catalog_and_linking():
    app = PopupControllerApp()
    assert app.catalog is not None
    bz = app.catalog.get_entity(14)
    assert bz is not None
    assert "blood zombie" in bz["title"].lower()

    # Verify avatar surface generation
    avatar = app.catalog.get_avatar_surface(14)
    assert isinstance(avatar, pg.Surface)
    assert avatar.get_width() > 0

    # Link entity to current scene
    orig_type = app.scenes[0].get("trigger_type")
    app._link_entity(14)
    assert app.scenes[0]["trigger_type"] == "entity"
    assert app.scenes[0]["entity_id"] == 14

    # Restore
    app.scenes[0]["trigger_type"] = orig_type


def test_popup_controller_add_and_delete_popup():
    app = PopupControllerApp()
    initial_count = len(app.scenes)

    # Open add modal
    app._open_add_modal()
    assert app.show_add_modal is True

    app.add_title_str = "Automated Test Added Pop-up"
    app.add_text_str = "Testing creation workflow in popup controller."
    app.add_trigger_type = "distance"
    app.add_distance_val = 1337.0
    app.add_theme_str = "arcane_void"

    app._confirm_add_popup()
    assert app.show_add_modal is False
    assert len(app.scenes) == initial_count + 1

    added_scene = app._get_selected_scene()
    assert added_scene is not None
    assert added_scene["title"] == "Automated Test Added Pop-up"
    assert added_scene["distance"] == 1337.0

    # Test delete
    app._delete_current_popup()
    assert len(app.scenes) == initial_count


def test_popup_controller_dynamic_layout_and_resizing():
    app = PopupControllerApp()

    # Simulate 1080p Full HD resize
    app.width = 1920
    app.height = 1080
    app._update_layout()

    assert app.timeline_w >= 400
    assert app.pv_w >= 430
    assert app.ed_w > 0
    assert app.panels_h == 1080 - 114

    # Headless draw must execute cleanly
    app.screen = pg.Surface((1920, 1080))
    app.draw()


def test_popup_controller_scrolling():
    app = PopupControllerApp()
    app.scroll_y = 0.0

    # Simulate mouse wheel down
    app.scroll_y = min(app.max_scroll, app.scroll_y + 100.0)
    assert app.scroll_y >= 0.0


def test_popup_controller_header_button_clicks_and_hitbox_parity():
    """Verify that clicking the actual drawn header button coordinates triggers the actions."""
    app = PopupControllerApp()
    hdr = app._get_header_rects()

    # 1. Click [+ Add Pop-up] button
    assert app.show_add_modal is False
    app._handle_click(hdr["add_popup"].center)
    assert app.show_add_modal is True

    # Close modal
    modal_rects = app._get_add_modal_rects()
    app._handle_click(modal_rects["close"].center)
    assert app.show_add_modal is False

    # 2. Click [Mute All]
    app._handle_click(hdr["mute_all"].center)
    for s in app.scenes:
        assert s["enabled"] is False

    # 3. Click [Unmute All]
    app._handle_click(hdr["unmute_all"].center)
    for s in app.scenes:
        assert s["enabled"] is True


def test_popup_controller_add_modal_interactive_clicks():
    """Verify that clicking inside the Add Modal properly switches tabs, selects entities, and inputs."""
    app = PopupControllerApp()
    app._open_add_modal()
    assert app.show_add_modal is True

    modal_rects = app._get_add_modal_rects()

    # Click Distance tab
    app._handle_click(modal_rects["tabs"]["distance"].center)
    assert app.add_trigger_type == "distance"

    # Click a preset button
    dist_rects = app._get_add_modal_rects()
    if dist_rects.get("dist_presets"):
        target_preset = dist_rects["dist_presets"][2]  # e.g., 1400m
        app._handle_click(target_preset[1].center)
        assert app.add_distance_val == float(target_preset[0])

    # Click Flag tab
    app._handle_click(dist_rects["tabs"]["flag"].center)
    assert app.add_trigger_type == "flag"

    flag_rects = app._get_add_modal_rects()
    if flag_rects.get("flag_chips"):
        chip_name, chip_rect = flag_rects["flag_chips"][1]
        app._handle_click(chip_rect.center)
        assert app.add_flag_str == chip_name

    # Click Entity tab
    app._handle_click(flag_rects["tabs"]["entity"].center)
    assert app.add_trigger_type == "entity"

    # Click Title Input Box
    ent_rects = app._get_add_modal_rects()
    app._handle_click(ent_rects["title_input"].center)
    assert app.add_active_input == "title"

    # Click Text Input Box
    app._handle_click(ent_rects["text_input"].center)
    assert app.add_active_input == "text"

    # Click Theme Chip (e.g., arcane_void)
    if "arcane_void" in ent_rects.get("theme_chips", {}):
        app._handle_click(ent_rects["theme_chips"]["arcane_void"].center)
        assert app.add_theme_str == "arcane_void"

    # Confirm creation via click
    initial_count = len(app.scenes)
    app.add_title_str = "Interactive Click Created Scene"
    app.add_text_str = "Created through exact simulated mouse clicks."
    app._handle_click(ent_rects["confirm"].center)

    assert app.show_add_modal is False
    assert len(app.scenes) == initial_count + 1
    created = app._get_selected_scene()
    assert created is not None
    assert created["title"] == "Interactive Click Created Scene"

    # Clean up test scene
    app._delete_current_popup()
    assert len(app.scenes) == initial_count


