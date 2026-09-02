import os
import pygame as pg
import pytest
from unittest.mock import MagicMock, patch
from src.game.states.transformation_cutscene import TransformationCutscene, _Phase

@pytest.fixture(autouse=True)
def init_pygame():
    pg.init()
    if not pg.display.get_init():
        pg.display.init()
    pg.display.set_mode((1, 1), pg.NOFRAME)
    yield
    pg.quit()

@patch("src.game.states.transformation_cutscene.NotificationBanner")
def test_transformation_cutscene_timeline_audio_triggers(mock_banner):
    manager = MagicMock()
    audio_mgr = MagicMock()
    audio_mgr.sound_library = {}
    manager.audio_manager = audio_mgr

    cutscene = TransformationCutscene(manager)
    cutscene._config = {
        "phases": {
            "fade_in": {
                "duration": 1.5,
                "sfx_timeline": [
                    {"key": "test_sound_1", "offset": 0.0, "duration": 1.0, "volume": 0.8, "muted": False},
                    {"key": "test_sound_2", "offset": 0.5, "duration": 0.5, "volume": 0.5, "muted": False},
                    {"key": "test_sound_muted", "offset": 0.0, "duration": 1.0, "volume": 1.0, "muted": True},
                ]
            }
        },
        "global": {"background_color": [0, 0, 0]},
        "assets": {}
    }
    cutscene._reset_state()
    cutscene._phase = _Phase.FADE_IN
    cutscene._phase_timer = 0.0

    # At t=0.0s, test_sound_1 should trigger with volume 0.8, muted should not trigger
    cutscene._update_audio()
    audio_mgr.play_sound.assert_called_with("test_sound_1", volume=0.8)

    # Reset mock call history
    audio_mgr.play_sound.reset_mock()

    # At t=0.2s, test_sound_2 shouldn't trigger yet (offset is 0.5s)
    cutscene._phase_timer = 0.2
    cutscene._update_audio()
    audio_mgr.play_sound.assert_not_called()

    # At t=0.55s, test_sound_2 should trigger with volume 0.5
    cutscene._phase_timer = 0.55
    cutscene._update_audio()
    audio_mgr.play_sound.assert_called_with("test_sound_2", volume=0.5)

    # Calling again at t=0.6s should not re-trigger test_sound_2
    audio_mgr.play_sound.reset_mock()
    cutscene._phase_timer = 0.6
    cutscene._update_audio()
    audio_mgr.play_sound.assert_not_called()

@patch("src.game.states.transformation_cutscene.NotificationBanner")
def test_transformation_cutscene_global_audio_timeline(mock_banner):
    manager = MagicMock()
    audio_mgr = MagicMock()
    audio_mgr.sound_library = {}
    channel_mock = MagicMock()
    audio_mgr.channels = [channel_mock]
    audio_mgr.play_sound.return_value = 0
    manager.audio_manager = audio_mgr

    cutscene = TransformationCutscene(manager)
    cutscene._config = {
        "audio_timeline": [
            {"key": "lead_roar", "time": 0.0, "duration": 2.0, "volume": 1.2, "pan": -0.5, "muted": False},
            {"key": "slash_impact", "time": 3.5, "duration": 1.0, "volume": 0.9, "pan": 0.8, "muted": False},
            {"key": "muted_spell", "time": 0.0, "duration": 1.0, "volume": 1.0, "muted": True},
        ],
        "phases": {
            "fade_in": {"duration": 1.5}
        }
    }
    cutscene._reset_state()
    cutscene._total_elapsed_time = 0.0

    # At t=0.0s, lead_roar triggers with volume 1.2
    cutscene._update_audio()
    audio_mgr.play_sound.assert_called_with("lead_roar", volume=1.2)
    # Panning test: pan = -0.5 -> left = 1.5 * 1.2 = 1.0 (clamped), right = 0.5 * 1.2 = 0.6
    channel_mock.set_volume.assert_called()

    # Reset
    audio_mgr.play_sound.reset_mock()

    # Advance time to t=2.0s: slash_impact at t=3.5s should not trigger yet
    cutscene._total_elapsed_time = 2.0
    cutscene._update_audio()
    audio_mgr.play_sound.assert_not_called()

    # Advance time to t=3.6s: slash_impact should trigger
    cutscene._total_elapsed_time = 3.6
    cutscene._update_audio()
    audio_mgr.play_sound.assert_called_with("slash_impact", volume=0.9)

