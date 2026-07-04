"""Unit tests for GameplayTracker threading boss_key/player_side_swaps into
the telemetry session payload submitted to the cloud."""

import shutil
import tempfile

import pygame as pg
import pytest

from src.game.services import TelemetryClient
from src.game.debug.gameplay_tracker import GameplayTracker


@pytest.fixture(scope="module", autouse=True)
def setup_pygame():
    if not pg.get_init():
        pg.init()
    if not pg.font.get_init():
        pg.font.init()
    if not pg.display.get_init() or pg.display.get_surface() is None:
        pg.display.init()
        pg.display.set_mode((1280, 720))
    yield


def test_session_payload_includes_boss_key_and_side_swaps(monkeypatch):
    captured = {}

    def fake_submit_session(session_data):
        captured.update(session_data)

    monkeypatch.setattr(TelemetryClient, "submit_session", staticmethod(fake_submit_session))

    test_dir = tempfile.mkdtemp()
    try:
        tracker = GameplayTracker({"enabled": True, "log_dir": test_dir})
        tracker.set_boss_key("boss_wizard")
        tracker.player_side_swaps = 3

        tracker.close()

        assert captured.get("boss_key") == "boss_wizard"
        assert captured.get("player_side_swaps") == 3
    finally:
        shutil.rmtree(test_dir)


def test_session_payload_boss_key_defaults_to_none(monkeypatch):
    captured = {}

    def fake_submit_session(session_data):
        captured.update(session_data)

    monkeypatch.setattr(TelemetryClient, "submit_session", staticmethod(fake_submit_session))

    test_dir = tempfile.mkdtemp()
    try:
        tracker = GameplayTracker({"enabled": True, "log_dir": test_dir})
        tracker.close()

        assert captured.get("boss_key") is None
    finally:
        shutil.rmtree(test_dir)
