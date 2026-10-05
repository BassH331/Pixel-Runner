"""
Unit Test Suite for CinematicNarrativeOverlay & Anti-Turtling Mechanics.
Tests overlay activation, typewriter text progress, keypress input handling [1] and [2], and guard-break stun state.
"""
import pytest
import pygame as pg
from unittest.mock import MagicMock

from src.game.ui.cinematic_narrative_overlay import CinematicNarrativeOverlay
from v3x_zulfiqar_gideon import UITheme
from src.game.entities.player import Player, PlayerState


@pytest.fixture(scope="module", autouse=True)
def setup_pygame():
    pg.init()
    pg.display.set_mode((1280, 720), pg.HIDDEN)
    UITheme.configure_buttons(
        assets={
            "big": ("dummy_big", "dummy_big_p"),
            "medium": ("dummy_med", "dummy_med_p"),
            "cancel": ("dummy_cancel", "dummy_cancel_p"),
            "new_start": ("dummy_new", "dummy_new_p"),
        },
        font_path="assets/font/Abaddon Bold.ttf"
    )
    UITheme.configure_notifications(
        banner_path="assets/graphics/UI/PNG/IRONY TITLE  Large.png",
        icons={"gray": "dummy_gray", "red": "dummy_red", "yellow": "dummy_yellow"},
        font_path="assets/font/Abaddon Bold.ttf"
    )
    UITheme.configure_overlays(
        stone_path="assets/graphics/UI/PNG/UI board Medium  stone.png",
        parchment_path="assets/graphics/UI/PNG/UI board Medium  parchment.png",
        title_font_path="assets/font/Abaddon Bold.ttf",
        body_font_path="assets/graphics/Darinia/Darinia.ttf",
    )
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


def test_cinematic_narrative_overlay_space_and_return_advance():
    """Verify pressing SPACE or RETURN advances single-option monologue."""
    overlay = CinematicNarrativeOverlay()
    callback_mock = MagicMock()
    evt = {
        "speaker_name": "Andras, Marquis of Discord",
        "dialogue_text": "I know your past...",
        "option_1_label": "[SPACE] Continue",
        "option_1_buff": {"close_overlay_only": True}
    }
    overlay.activate(evt, callback_mock)
    
    space_event = pg.event.Event(pg.KEYDOWN, key=pg.K_SPACE)
    handled = overlay.handle_event(space_event)
    assert handled
    assert not overlay.is_active
    callback_mock.assert_called_once_with({"close_overlay_only": True})

    # Test RETURN
    callback_mock.reset_mock()
    overlay.activate(evt, callback_mock)
    return_event = pg.event.Event(pg.KEYDOWN, key=pg.K_RETURN)
    handled = overlay.handle_event(return_event)
    assert handled
    assert not overlay.is_active
    callback_mock.assert_called_once_with({"close_overlay_only": True})


def test_cinematic_narrative_overlay_slowed_animation_delay():
    """Verify demon avatar frame delay is slowed to 0.28s for deliberate pacing."""
    overlay = CinematicNarrativeOverlay()
    assert overlay._AVATAR_FRAME_SPEED == 0.28


def test_player_spawn_ground_level_alignment():
    """Verify player spawned at y=222 has rect.bottom aligned at ground_y 606."""
    player = Player(200, 222, MagicMock())
    assert player.rect.bottom == 606


def test_player_demonic_pact_revival_and_is_dead_setter():
    """Verify player is_dead setter and GameState._on_pact_choice resuscitation."""
    from src.game.states.game_state import GameState
    from v3x_zulfiqar_gideon import StateManager

    player = Player(200, 222, MagicMock())
    # 1. Test is_dead setter
    player.is_dead = True
    assert player.is_dead
    assert player.state == PlayerState.DEATH

    player.is_dead = False
    assert not player.is_dead
    assert player.state == PlayerState.IDLE

    # 2. Test string-safe set_state
    player.set_state("idle", force=True)
    assert player.state == PlayerState.IDLE

    # 3. Test GameState._on_pact_choice resuscitation
    sm = StateManager(audio_manager=MagicMock())
    game_state = GameState(sm)
    p = game_state.player.sprite
    p.is_dead = True
    assert p.is_dead

    # Trigger demonic pact transformation choice
    game_state._on_pact_choice({"trigger_transformation": True})

    assert not p.is_dead
    assert p.is_enhanced
    assert p.health == 200
    assert p.state == PlayerState.IDLE
    assert p.can_move

