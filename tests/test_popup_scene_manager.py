"""
Unit tests for PopupSceneManager and theme-enabled SideNotification.
Verifies loading, lookups (by id, entity, flag, distance), updating, toggles, atomic saves, and theming.
"""

import json
import os
import tempfile
import pytest
import pygame as pg

from src.game.systems.popup_scene_manager import PopupSceneManager
from src.game.ui.side_notification import SideNotification, _NotificationItem
from src.game.systems.notification_config_manager import THEME_PRESETS


@pytest.fixture(autouse=True)
def setup_pg():
    pg.init()
    yield
    pg.quit()


def test_popup_scene_manager_load_and_lookup():
    PopupSceneManager.reset_instance()
    mgr = PopupSceneManager.get_instance()
    
    popups = mgr.get_all_popups()
    assert len(popups) >= 13, f"Expected at least 13 popups, got {len(popups)}"
    
    # Check lookup by ID
    prologue = mgr.get_popup("event_prologue_awakening")
    assert prologue is not None
    assert prologue["title"] == "The Awakening"
    assert prologue["theme"] == "gothic_gold"
    assert prologue["enabled"] is True

    # Check lookup by Entity ID
    grimoire = mgr.get_popup_by_entity(10)
    assert grimoire is not None
    assert grimoire["id"] == "event_sealed_book_encounter"
    assert grimoire["theme"] == "grimoire_leather"

    blood_zombie = mgr.get_popup_by_entity(14)
    assert blood_zombie is not None
    assert blood_zombie["id"] == "event_boss_blood_zombie"
    assert blood_zombie["theme"] == "blood_bone"

    # Check lookup by Flag
    first_kill = mgr.get_popup_by_flag("first_kill")
    assert first_kill is not None
    assert first_kill["id"] == "event_first_kill"

    # Check lookup by Distance
    dist_1400 = mgr.get_popups_by_distance(1400.0, tolerance=25.0)
    assert len(dist_1400) >= 1
    assert dist_1400[0]["id"] == "event_forest_inquiry_1400m"


def test_popup_scene_manager_toggle_and_update():
    PopupSceneManager.reset_instance()
    mgr = PopupSceneManager.get_instance()

    # Toggle enabled
    assert mgr.set_popup_enabled("event_prologue_awakening", False) is True
    p = mgr.get_popup("event_prologue_awakening")
    assert p["enabled"] is False

    # Restore enabled
    assert mgr.set_popup_enabled("event_prologue_awakening", True) is True
    p = mgr.get_popup("event_prologue_awakening")
    assert p["enabled"] is True

    # Update text and theme
    orig = mgr.get_popup("event_book_ponder")
    orig_text = orig["text"]
    assert mgr.update_popup("event_book_ponder", {"text": "Updated forbidden lore."}) is True
    updated = mgr.get_popup("event_book_ponder")
    assert updated["text"] == "Updated forbidden lore."

    # Restore original text
    mgr.update_popup("event_book_ponder", {"text": orig_text})


def test_popup_scene_manager_atomic_save():
    PopupSceneManager.reset_instance()
    mgr = PopupSceneManager.get_instance()

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_cfg = os.path.join(tmp_dir, "test_popups.json")
        success = mgr.save_config(target_path=tmp_cfg)
        assert success is True
        assert os.path.exists(tmp_cfg)

        with open(tmp_cfg, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert "scenes" in data
        assert len(data["scenes"]) >= 13


def test_side_notification_per_theme_rendering():
    sn = SideNotification(1280, 720)
    assert sn is not None

    # Test all 5 themes
    themes = ["gothic_gold", "blood_bone", "arcane_void", "grimoire_leather", "clean_minimalist"]
    for theme_name in themes:
        assert theme_name in THEME_PRESETS
        item = _NotificationItem(
            text="The blood moon rises high over the ancient graveyard.",
            title=f"Testing {theme_name}",
            theme=theme_name,
        )
        sn._build_tab_surface(item)
        assert sn._current_tab_surface is not None
        assert sn._current_tab_surface.get_width() > 0
        assert sn._current_tab_surface.get_height() > 0

    # Test show() queuing with theme
    sn.show("Body text", "Header Title", theme="blood_bone")
    assert sn._current_item is not None
    assert sn._current_item.theme == "blood_bone"
    sn.update(0.1)


def test_popup_scene_manager_add_and_delete():
    PopupSceneManager.reset_instance()
    mgr = PopupSceneManager.get_instance()

    new_scene = {
        "id": "event_test_custom_add",
        "title": "Custom Test Milestone",
        "text": "A dark power coalesces in the shadows.",
        "trigger_type": "entity",
        "entity_id": 14,
        "distance": 2558,
        "theme": "blood_bone",
        "hold": 6.5,
        "enabled": True,
    }

    # Test adding
    assert mgr.add_popup(new_scene) is True
    found = mgr.get_popup("event_test_custom_add")
    assert found is not None
    assert found["title"] == "Custom Test Milestone"

    # Test deleting
    assert mgr.delete_popup("event_test_custom_add") is True
    assert mgr.get_popup("event_test_custom_add") is None

