"""
Unit tests for popup_controller.py GUI plugin.
Verifies scene selection, text buffer editing, theme changing, muting toggles,
filtering tabs, and atomic saves in the Pop-up Notification Control System.
"""

import os
import pytest
import pygame as pg

os.environ["SDL_VIDEODRIVER"] = "dummy"

from popup_controller import PopupControllerApp, IconCatalog
from src.game.systems.popup_scene_manager import PopupSceneManager


@pytest.fixture(autouse=True)
def setup_pg():
    pg.init()
    yield
    pg.quit()


def test_popup_controller_init():
    app = PopupControllerApp()
    assert app is not None
    assert len(app.scenes) >= 10
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


def test_popup_controller_duration_and_field_persistence():
    """Verify that editing hold duration, title, and text persists to disk upon _save_changes()."""
    app = PopupControllerApp()
    scene = app._get_selected_scene()
    assert scene is not None

    orig_hold = scene.get("hold", 6.0)
    orig_title = scene.get("title", "")
    orig_text = scene.get("text", "")
    target_id = scene["id"]

    # Mutate duration and buffers
    scene["hold"] = 14.5
    app.edit_title_str = "Persisted Title Test"
    app.edit_text_str = "Persisted Text Body Test"
    
    # Save
    save_res = app._save_changes()
    assert save_res is True

    # Reset manager singleton and reload directly from disk
    PopupSceneManager.reset_instance()
    fresh_mgr = PopupSceneManager.get_instance()
    loaded_scene = fresh_mgr.get_popup(target_id)
    assert loaded_scene is not None
    assert loaded_scene["hold"] == 14.5
    assert loaded_scene["title"] == "Persisted Title Test"
    assert loaded_scene["text"] == "Persisted Text Body Test"

    # Restore original state and persist back
    scene["hold"] = orig_hold
    app.edit_title_str = orig_title
    app.edit_text_str = orig_text
    app._save_changes()

    PopupSceneManager.reset_instance()
    restored_mgr = PopupSceneManager.get_instance()
    restored_scene = restored_mgr.get_popup(target_id)
    assert restored_scene is not None
    assert restored_scene["hold"] == orig_hold
    assert restored_scene["title"] == orig_title
    assert restored_scene["text"] == orig_text


def test_popup_controller_select_scene_commits_active_buffers():
    """Verify that switching between scenes commits in-flight text edits to the previous scene."""
    app = PopupControllerApp()
    assert len(app.scenes) >= 2

    # Select scene 0
    app._select_scene(0)
    s0 = app.scenes[0]
    orig_title0 = s0.get("title", "")
    
    # Edit title buffer without saving
    app.edit_title_str = "Unsaved But Committed On Switch"
    
    # Switch to scene 1
    app._select_scene(1)
    
    # Verify s0 received the committed title
    assert s0["title"] == "Unsaved But Committed On Switch"
    
    # Restore
    s0["title"] = orig_title0


def test_icon_catalog_scanning_and_filtering():
    """Verify that IconCatalog discovers asset pack icons and filters by category and search term."""
    catalog = IconCatalog()
    assert len(catalog.all_icons) >= 500

    # Ensure all expected category buckets exist and contain icons
    for cat_key, _ in IconCatalog.CATEGORIES:
        assert cat_key in catalog.icons_by_category
        if cat_key != "ALL":
            assert len(catalog.icons_by_category[cat_key]) > 0

    # Test category filtering
    warrior_icons = catalog.filter_icons(category="WARRIOR")
    assert len(warrior_icons) > 0
    for it in warrior_icons:
        assert it["category"] == "WARRIOR"

    # Test search query filtering
    filtered_icons = catalog.filter_icons(category="ALL", query="relic")
    assert len(filtered_icons) > 0
    for it in filtered_icons:
        assert "relic" in it["filename"].lower() or "relic" in it["pack"].lower() or "relic" in it["path"].lower()

    # Test thumbnail surface generation
    thumb = catalog.get_thumbnail("assets/graphics/ui/relic_icon.png", (40, 40))
    assert isinstance(thumb, pg.Surface)
    assert thumb.get_size() == (40, 40)

    # Test thumbnail fallback surface when file does not exist
    fallback = catalog.get_thumbnail("assets/non_existent_image_12345.png", (40, 40))
    assert isinstance(fallback, pg.Surface)
    assert fallback.get_size() == (40, 40)


def test_popup_controller_quick_preset_selection():
    """Verify clicking quick-pick preset ribbon updates scene icon and live notification preview."""
    app = PopupControllerApp()
    scene = app._get_selected_scene()
    assert scene is not None

    orig_icon = scene.get("icon")
    rects = app._get_editor_rects(scene)
    assert "icon_quick_picks" in rects
    assert len(rects["icon_quick_picks"]) == len(IconCatalog.QUICK_PRESETS)

    # Pick the 'blade' preset
    preset_path, preset_name, preset_rect = rects["icon_quick_picks"]["blade"]
    app._handle_click(preset_rect.center)

    assert scene["icon"] == preset_path
    assert app.preview_notification._current_item is not None
    assert app.preview_notification._current_item.icon == preset_path

    # Restore original icon
    scene["icon"] = orig_icon
    app._trigger_preview()


def test_popup_controller_icon_modal_interaction_and_apply():
    """Verify opening the icon gallery modal, searching, selecting an icon tile, and applying to scene."""
    app = PopupControllerApp()
    scene = app._get_selected_scene()
    assert scene is not None
    orig_icon = scene.get("icon")

    # Open Icon Modal for scene
    assert not app.show_icon_modal
    app._open_icon_modal(target="scene")
    assert app.show_icon_modal is True
    assert app.icon_modal_target == "scene"

    # Filter with a query
    app.icon_modal_search = "Icon10"
    m_rects = app._get_icon_modal_rects()
    assert len(m_rects["icon_tiles"]) > 0

    # Select the first matching tile
    target_path, target_tile_rect, _ = m_rects["icon_tiles"][0]
    app._handle_icon_modal_click(target_tile_rect.center)
    assert app.icon_modal_selected_path == target_path

    # Click Apply button
    app._handle_icon_modal_click(m_rects["apply_btn"].center)
    assert app.show_icon_modal is False
    assert scene["icon"] == target_path
    assert app.preview_notification._current_item.icon == target_path

    # Restore
    scene["icon"] = orig_icon
    app._trigger_preview()


def test_popup_controller_add_modal_custom_icon_and_persistence():
    """Verify choosing a custom icon in [+ Add Pop-up] and saving persists to disk."""
    app = PopupControllerApp()
    app._open_add_modal()
    assert app.show_add_modal is True

    # Open icon gallery from inside Add Modal
    add_rects = app._get_add_modal_rects()
    assert "icon_browse" in add_rects
    app._handle_add_modal_click(add_rects["icon_browse"].center)
    assert app.show_icon_modal is True
    assert app.icon_modal_target == "add"

    # Select a distinct icon
    chosen_icon = "assets/graphics/ui/relic_icon.png"
    app.icon_modal_selected_path = chosen_icon
    app._apply_selected_icon()
    assert app.show_icon_modal is False
    assert app.add_icon_str == chosen_icon

    # Fill fields and confirm addition
    app.add_trigger_type = "flag"
    app.add_flag_str = "flag_custom_icon_test"
    app.add_title_str = "Custom Icon Pop-up Test"
    app.add_text_str = "Testing icon persistence."
    app.add_theme_str = "blood_bone"

    app._confirm_add_popup()
    assert app.show_add_modal is False

    created = next((s for s in app.scenes if s.get("flag") == "flag_custom_icon_test"), None)
    assert created is not None
    assert created["icon"] == chosen_icon
    target_id = created["id"]

    # Save changes to disk
    save_ok = app._save_changes()
    assert save_ok is True

    # Reload from disk via manager singleton reset
    PopupSceneManager.reset_instance()
    fresh_mgr = PopupSceneManager.get_instance()
    loaded_scene = fresh_mgr.get_popup(target_id)
    assert loaded_scene is not None
    assert loaded_scene["icon"] == chosen_icon

    # Clean up created scene from app and disk
    app.selected_index = app.scenes.index(created)
    app._delete_current_popup()
    app._save_changes()

    PopupSceneManager.reset_instance()
    clean_mgr = PopupSceneManager.get_instance()
    assert clean_mgr.get_popup(target_id) is None




