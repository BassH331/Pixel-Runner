"""
Unit and integration tests for Notification Plugin Editor and Config Manager.
Validates config persistence, hot-reloading, theme presets, dynamic geometry, and editor staging.
"""

import os
import json
import time
import tempfile
import pytest
import pygame as pg

if not pg.get_init():
    pg.init()
if not pg.display.get_surface():
    pg.display.set_mode((1280, 720), pg.NOFRAME)

from src.game.systems.notification_config_manager import (
    NotificationConfigManager,
    DEFAULT_NOTIFICATION_CONFIG,
    THEME_PRESETS,
)
from src.game.ui.side_notification import SideNotification, NotificationState
from notification_editor import NotificationEditorApp, EditorSlider, EditorToggle


@pytest.fixture(autouse=True)
def clean_config_manager_singleton():
    """Ensure NotificationConfigManager singleton is clean before and after each test."""
    NotificationConfigManager.reset_instance()
    yield
    NotificationConfigManager.reset_instance()


def test_notification_config_manager_defaults():
    """Verify default notification config structure and deep merge."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_cfg_path = os.path.join(tmp_dir, "notification_config.json")
        mgr = NotificationConfigManager(config_path=tmp_cfg_path)

        assert os.path.exists(tmp_cfg_path)
        assert "timing" in mgr.data
        assert "layout" in mgr.data
        assert "colors" in mgr.data
        assert "typography" in mgr.data

        assert mgr.data["timing"]["slide_in_time"] == 0.35
        assert mgr.data["timing"]["default_hold_time"] == 8.5
        assert mgr.data["layout"]["tab_width"] == 390
        assert mgr.data["layout"]["corner_radius"] == 10


def test_notification_config_manager_backup_and_save():
    """Verify that saving configuration writes JSON and creates a backup."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_cfg_path = os.path.join(tmp_dir, "notification_config.json")
        mgr = NotificationConfigManager(config_path=tmp_cfg_path)

        # Modify parameter and save
        mgr.data["timing"]["default_hold_time"] = 12.0
        mgr.data["layout"]["tab_width"] = 420
        save_success = mgr.save_config(mgr.data)
        assert save_success is True

        # Second save creates a backup file
        mgr.data["timing"]["default_hold_time"] = 14.0
        mgr.save_config(mgr.data)

        files = os.listdir(tmp_dir)
        backups = [f for f in files if "backup" in f]
        assert len(backups) >= 1

        # Re-read from disk
        with open(tmp_cfg_path, "r", encoding="utf-8") as f:
            saved = json.load(f)
        assert saved["timing"]["default_hold_time"] == 14.0
        assert saved["layout"]["tab_width"] == 420


def test_notification_config_theme_presets():
    """Verify applying all curated theme presets."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_cfg_path = os.path.join(tmp_dir, "notification_config.json")
        mgr = NotificationConfigManager(config_path=tmp_cfg_path)

        for preset_key, preset_data in THEME_PRESETS.items():
            applied = mgr.apply_preset(preset_key)
            assert applied is True
            # Colors match preset definition
            for col_k, col_val in preset_data["colors"].items():
                assert mgr.data["colors"][col_k] == col_val


def test_side_notification_hot_reload_and_geometry():
    """Verify that SideNotification hot-reloads when config manager data changes."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_cfg_path = os.path.join(tmp_dir, "notification_config.json")
        mgr = NotificationConfigManager(config_path=tmp_cfg_path)

        notif = SideNotification(1280, 720, config_manager=mgr)
        assert notif._tab_width == 390
        assert notif._default_hold_time == 8.5

        # Update manager layout and save
        mgr.data["layout"]["tab_width"] = 450
        mgr.data["timing"]["default_hold_time"] = 11.0
        mgr.data["layout"]["corner_radius"] = 16
        mgr.save_config(mgr.data)

        # Sleep slightly to ensure mtime triggers hot-reload check
        time.sleep(0.05)

        # Trigger update() which checks hot-reload
        notif.update(0.016)
        assert notif._tab_width == 450
        assert notif._default_hold_time == 11.0
        assert notif._base_corner_radius == 16


def test_side_notification_word_scaling_with_custom_factors():
    """Verify that hold time respects words_per_sec and base_hold_pad from config."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_cfg_path = os.path.join(tmp_dir, "notification_config.json")
        mgr = NotificationConfigManager(config_path=tmp_cfg_path)

        mgr.data["timing"]["default_hold_time"] = 4.0
        mgr.data["timing"]["words_per_sec"] = 0.5
        mgr.data["timing"]["base_hold_pad"] = 3.0
        mgr.save_config(mgr.data)

        notif = SideNotification(1280, 720, config_manager=mgr)
        # 10 words -> 10 * 0.5 + 3.0 = 8.0s hold time
        sample_text = "one two three four five six seven eight nine ten"
        notif.show(sample_text, "Title")

        assert notif._current_item is not None
        assert notif._current_item.hold == pytest.approx(8.0, 0.1)


def test_notification_editor_app_smoke():
    """Verify that the GUI editor app can run headlessly and trigger notifications cleanly."""
    app = NotificationEditorApp(headless=True)
    assert app.sw == 1440
    assert app.sh == 880
    assert app.running is True

    # Check that controls exist
    assert len(app.timing_sliders) >= 7
    assert len(app.layout_sliders) >= 12
    assert len(app.theme_buttons) == 5
    assert len(app.sample_buttons) == 5

    # Switch tab to layout
    app.current_tab = "layout"
    app.update(0.016)
    app.draw()

    # Switch tab to colors
    app.current_tab = "colors"
    app.selected_color_key = "border_color"
    app._sync_color_sliders()
    app.update(0.016)
    app.draw()

    # Trigger custom notification
    app.input_title.text = "Editor Test Title"
    app.input_body.text = "Editor Test Body"
    app.trigger_notification()

    assert app.side_notif.is_active is True
    assert app.side_notif._current_item is not None
    assert app.side_notif._current_item.title == "Editor Test Title"
    assert app.side_notif._current_item.text == "Editor Test Body"

    # Advance animation
    app.update(0.4)
    app.draw()
    assert app.side_notif._state == NotificationState.HOLD
