"""
Unit Test Suite for CinematicNarrativeOverlay & Anti-Turtling Mechanics.
Tests overlay activation, typewriter text progress, keypress input handling [1] and [2], and guard-break stun state.
"""
import pytest
import pygame as pg
from unittest.mock import MagicMock

from src.game.ui.cinematic_narrative_overlay import CinematicNarrativeOverlay
from src.game.entities.player import Player, PlayerState


@pytest.fixture(scope="module", autouse=True)
def setup_pygame():
    pg.init()
    pg.display.set_mode((800, 600), pg.HIDDEN)
    yield
    pg.quit()


def test_cinematic_narrative_overlay_initial_state():
    """Verify overlay starts in inactive state."""
    overlay = CinematicNarrativeOverlay()
    assert not overlay.is_active
    assert overlay._current_event is None


def test_cinematic_narrative_overlay_activation():
    """Verify activate sets event data and activates overlay."""
    overlay = CinematicNarrativeOverlay()
    evt = {
        "speaker_name": "The Evil Eye",
        "dialogue_text": "Test dialogue",
        "option_1_label": "[1] Shadow",
        "option_1_buff": {"dmg_mult": 1.4},
        "option_2_label": "[2] Light",
        "option_2_buff": {"hp_restore": 30}
    }
    overlay.activate(evt)
    assert overlay.is_active
    assert overlay._full_text == "Test dialogue"


def test_cinematic_narrative_overlay_typewriter_update():
    """Verify update advances typewriter text."""
    overlay = CinematicNarrativeOverlay()
    evt = {"dialogue_text": "Hello world!"}
    overlay.activate(evt)
    
    overlay.update(0.05)
    assert len(overlay._displayed_text) > 0


def test_cinematic_narrative_overlay_keypress_choice_selection():
    """Verify pressing key 1 triggers option 1 choice callback and deactivates overlay."""
    overlay = CinematicNarrativeOverlay()
    callback_mock = MagicMock()
    evt = {
        "speaker_name": "The Moon Knight",
        "dialogue_text": "Choose your fate",
        "option_1_label": "[1] Choice One",
        "option_1_buff": {"speed_mult": 1.3},
        "option_2_label": "[2] Choice Two",
        "option_2_buff": {"mana_restore": 50}
    }
    overlay.activate(evt, callback_mock)
    
    key_event = pg.event.Event(pg.KEYDOWN, key=pg.K_1)
    handled = overlay.handle_event(key_event)
    
    assert handled
    assert not overlay.is_active
    callback_mock.assert_called_once_with({"speed_mult": 1.3})


def test_player_guard_stun_mechanic():
    """Verify player enters GUARD_STUN when hit by Guard-Break attack while defending."""
    player = Player(100, 100, MagicMock())
    player.defend()
    assert player.state == PlayerState.DEFEND
    
    # Apply guard-break attack damage
    player.take_damage(20.0, is_guard_break=True)
    assert player.state == PlayerState.GUARD_STUN
