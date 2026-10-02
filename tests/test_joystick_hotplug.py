"""
tests/test_joystick_hotplug.py
Unit tests for ControlsManager dynamic joystick hot-plugging and auto-detection.
"""

import pytest
import pygame as pg
from unittest.mock import MagicMock, patch
from src.game.controls_manager import ControlsManager
from src.game.entities.player import Player


@pytest.fixture(autouse=True)
def reset_controls_manager():
    mgr = ControlsManager()
    mgr._active_joystick = None
    mgr.reset_to_defaults()
    yield
    mgr._active_joystick = None


def test_get_active_joystick_when_no_joystick():
    with patch.object(pg.joystick, "get_count", return_value=0):
        mgr = ControlsManager()
        js = mgr.get_active_joystick()
        assert js is None
        assert mgr._active_joystick is None


def test_get_active_joystick_auto_detect():
    mock_js = MagicMock()
    mock_js.get_init.return_value = True
    mock_js.get_name.return_value = "Test Gamepad"
    mock_js.get_numbuttons.return_value = 12

    with patch.object(pg.joystick, "get_count", return_value=1), \
         patch.object(pg.joystick, "Joystick", return_value=mock_js):
        mgr = ControlsManager()
        js = mgr.get_active_joystick()
        assert js is mock_js
        assert mgr._active_joystick is mock_js


def test_get_active_joystick_invalidation_on_error():
    stale_js = MagicMock()
    stale_js.get_init.return_value = True
    stale_js.get_name.side_effect = pg.error("Joystick disconnected")

    new_js = MagicMock()
    new_js.get_init.return_value = True
    new_js.get_name.return_value = "Reconnected Gamepad"
    new_js.get_numbuttons.return_value = 12

    mgr = ControlsManager()
    mgr._active_joystick = stale_js

    with patch.object(pg.joystick, "get_count", return_value=1), \
         patch.object(pg.joystick, "Joystick", return_value=new_js):
        js = mgr.get_active_joystick()
        assert js is new_js
        assert mgr._active_joystick is new_js


def test_handle_event_joydeviceadded_and_removed():
    mgr = ControlsManager()

    mock_js = MagicMock()
    mock_js.get_init.return_value = True
    mock_js.get_name.return_value = "Hotplugged Controller"

    event_added = MagicMock()
    event_added.type = pg.JOYDEVICEADDED
    event_added.device_index = 0

    with patch.object(pg.joystick, "Joystick", return_value=mock_js):
        mgr.handle_event(event_added)
        assert mgr._active_joystick is mock_js

    event_removed = MagicMock()
    event_removed.type = pg.JOYDEVICEREMOVED

    mgr.handle_event(event_removed)
    assert mgr._active_joystick is None


def test_player_delegates_joystick_to_controls_manager():
    mock_js = MagicMock()
    mock_js.get_init.return_value = True
    mock_js.get_name.return_value = "Test Gamepad"
    mock_js.get_numbuttons.return_value = 12

    with patch.object(pg.joystick, "get_count", return_value=1), \
         patch.object(pg.joystick, "Joystick", return_value=mock_js):
        player = Player(100, 100, audio_manager=None)
        assert player._get_joystick() is mock_js
