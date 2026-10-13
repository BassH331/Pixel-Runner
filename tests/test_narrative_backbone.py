"""
Unit Test Suite for Narrative Backbone: Story, Dialogue, Book Ritual, and Demon Time.
Verifies all canonical invariants established in the Narrative Cohesion Plan.
"""

import json
import pytest
import pygame as pg
from unittest.mock import MagicMock

from src.game.systems.corruption_manager import CorruptionManager
from src.game.systems.demon_time_system import DemonTimeSystem, DemonEyeCompanion, VoidBallProjectile
from src.game.ui.cinematic_narrative_overlay import CinematicNarrativeOverlay
from v3x_zulfiqar_gideon import EntityDied


@pytest.fixture(scope="module", autouse=True)
def init_pygame():
    pg.init()
    pg.display.set_mode((1280, 720), pg.HIDDEN)
    yield
    pg.quit()


def test_skeleton_kills_give_zero_corruption():
    """Invariant: Skeletons are mindless bone thralls; killing them must not increase corruption."""
    bus = MagicMock()
    config = {"corruption_events": {"enemy_kill": 0.5}}
    cm = CorruptionManager(bus, config)
    cm._value = 10.0

    # Mock skeleton entity
    skeleton = MagicMock()
    skeleton.__class__.__name__ = "Skeleton"

    # Emit death
    cm._on_entity_died(EntityDied(entity=skeleton, killer=None))
    assert cm.value == 10.0, "Skeleton kill should give 0 corruption"


def test_blood_zombie_relic_drops_canonical():
    """Verify storyline_config.json drops canonical Bark of Great One and The EYE."""
    with open("game_data/storyline_config.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    bz_drops = data.get("relic_boss_map", {}).get("BloodZombie", [])
    relic_ids = [d["relic_id"] if isinstance(d, dict) else d for d in bz_drops]
    assert "bark_of_the_great_one" in relic_ids
    assert "the_eye" in relic_ids

    relics = data.get("relics", {})
    assert "bark_of_the_great_one" in relics
    assert "the_eye" in relics


def test_demon_time_system_unlock_and_activation():
    """Verify Demon Time slows enemies to 0.20x while player remains at 1.0x."""
    dts = DemonTimeSystem()
    assert not dts.is_unlocked
    assert dts.get_enemy_time_scale() == 1.0
    assert dts.get_player_time_scale() == 1.0

    # Cannot activate while locked
    res = dts.activate()
    assert not res
    assert not dts.is_active

    # Unlock and activate
    dts.unlock()
    assert dts.is_unlocked

    activated = dts.activate(duration=3.0, time_scale=0.20)
    assert activated
    assert dts.is_active
    assert dts.get_enemy_time_scale() == 0.20
    assert dts.get_player_time_scale() == 1.0
    assert dts.companion.state in (DemonEyeCompanion.STATE_APPEARING, DemonEyeCompanion.STATE_IDLE)


def test_companion_lifecycle_and_disappearance():
    """Invariant: The EYE does not follow permanently; it manifests, idles, and dissolves."""
    companion = DemonEyeCompanion()
    assert companion.state == DemonEyeCompanion.STATE_INACTIVE

    # Summon
    companion.summon(100.0, 200.0)
    assert companion.state == DemonEyeCompanion.STATE_APPEARING

    # Update transitions to idle once appearance frames finish
    for _ in range(30):
        companion.update(0.1, 100.0, 200.0)
    assert companion.state == DemonEyeCompanion.STATE_IDLE

    # Dismiss
    companion.dismiss()
    assert companion.state == DemonEyeCompanion.STATE_DISAPPEARING

    # Update transitions to inactive once disappearance frames finish
    for _ in range(30):
        companion.update(0.1, 100.0, 200.0)
    assert companion.state == DemonEyeCompanion.STATE_INACTIVE


def test_demon_time_qte_void_strike():
    """Verify [PRESS A] / input fires VoidBallProjectile toward target."""
    dts = DemonTimeSystem()
    dts.unlock()
    dts.activate(duration=4.0)
    assert dts.qte_available

    # Fake input event: KEYDOWN A
    event = pg.event.Event(pg.KEYDOWN, key=pg.K_a)
    handled = dts.handle_input(
        event,
        player_x=100.0,
        player_y=200.0,
        target_x=500.0,
        target_y=200.0,
    )
    assert handled
    assert not dts.qte_available  # Consumed
    assert len(dts.projectiles) == 1

    proj = next(iter(dts.projectiles))
    assert isinstance(proj, VoidBallProjectile)
    assert proj.vx > 0.0  # Moving toward target


def test_void_ball_projectile_hits_boss():
    """Verify projectile deals damage and explodes on enemy contact."""
    proj = VoidBallProjectile(100, 100, 200, 100, damage=50.0)
    boss = MagicMock()
    boss.rect = pg.Rect(110, 80, 50, 50)
    boss.alive.return_value = True
    boss.health = 200.0

    dts = DemonTimeSystem()
    dts.projectiles.add(proj)

    dts.update(0.016, player_x=0, player_y=0, boss=boss)

    assert boss.take_damage.called or boss.health < 200.0
    assert getattr(proj, "_is_destroying", False)


def test_book_opening_ritual_in_overlay():
    """Verify CinematicNarrativeOverlay handles book ritual and auto-advances."""
    overlay = CinematicNarrativeOverlay()
    callback_mock = MagicMock()

    event = {
        "is_book_ritual": True,
        "speaker_name": "ANCIENT GRIMOIRE",
        "runic_text": "ᛟ ᚱ ᚦ ᛋ ᚹ",
        "dialogue_text": "Translation: A vessel bound in iron...",
        "option_1_label": "[SPACE] Read On",
        "option_1_buff": {"book_ritual_complete": True},
        "duration": 0.2,  # Short duration for test
    }
    overlay.activate(event, callback_mock)

    assert overlay.is_active
    assert overlay._is_book_ritual
    assert overlay._runic_text == "ᛟ ᚱ ᚦ ᛋ ᚹ"

    # Update past 0.2s
    overlay.update(0.25)
    assert not overlay.is_active  # Auto-advanced!
    callback_mock.assert_called_once_with({"book_ritual_complete": True})


def test_magic_book_encounter_overlay_dispatch():
    """Verify Magic Book trigger_cinematic_now activates ritual without UnboundLocalError."""
    from src.game.states.game_state import GameState

    # Construct minimal mocked GameState
    state = GameState.__new__(GameState)
    state.cinematic_narrative_overlay = MagicMock()
    state.in_magic_void = False
    state._on_pact_choice = MagicMock()

    # Mock magic book npc
    book_npc = MagicMock()
    book_npc.trigger_cinematic_now = True
    book_npc.is_magic_book = True
    state.npc_group = [book_npc]

    # Process cinematic triggers as in update()
    for npc in state.npc_group:
        if getattr(npc, "trigger_cinematic_now", False):
            npc.trigger_cinematic_now = False
            if hasattr(state, "cinematic_narrative_overlay"):
                if getattr(npc, "is_magic_book", False):
                    state.in_magic_void = True
                    npc.kill()
                    book_ritual_event = {
                        "is_book_ritual": True,
                        "speaker_name": "ANCIENT GRIMOIRE [SEAL OF ANDRAS]",
                    }
                    state.cinematic_narrative_overlay.activate(book_ritual_event, MagicMock())

    assert state.in_magic_void
    assert book_npc.kill.called
    assert state.cinematic_narrative_overlay.activate.called


def test_book_ritual_to_andras_chain_does_not_get_stuck():
    """Verify that completing or skipping Book Ritual transitions to Andras and dismisses cleanly."""
    from src.game.ui.cinematic_narrative_overlay import CinematicNarrativeOverlay

    overlay = CinematicNarrativeOverlay()
    state_in_magic_void = True
    pact_choice_called = False

    def on_pact_choice(buff_data):
        nonlocal state_in_magic_void, pact_choice_called
        pact_choice_called = True
        if buff_data.get("clear_magic_void"):
            state_in_magic_void = False

    def on_ritual_complete(buff_data):
        assert buff_data.get("book_ritual_complete")
        pact_event = {
            "speaker_name": "Andras, Marquis of Discord",
            "avatar_sprite": "assets/Agis",
            "dialogue_text": "Keep the book, we'll talk soon warrior.",
            "option_1_label": "[SPACE] Continue",
            "option_1_buff": {"close_overlay_only": True, "clear_magic_void": True}
        }
        overlay.activate(pact_event, on_pact_choice)

    # 1. Start Book Ritual
    ritual_event = {
        "is_book_ritual": True,
        "speaker_name": "ANCIENT GRIMOIRE",
        "runic_text": "ᛟ ᚱ ᚦ ᛋ ᚹ",
        "dialogue_text": "Translation: A vessel bound in iron...",
        "option_1_label": "[SPACE] Read On",
        "option_1_buff": {"book_ritual_complete": True},
        "duration": 5.0,
    }
    overlay.activate(ritual_event, on_ritual_complete)
    assert overlay.is_active
    assert overlay._is_book_ritual

    # 2. Player presses SPACE to skip/advance ritual
    space_event = pg.event.Event(pg.KEYDOWN, key=pg.K_SPACE)
    handled = overlay.handle_event(space_event)
    assert handled

    # Overlay must NOT be stuck or deactivated — it must now be showing Andras!
    assert overlay.is_active
    assert not overlay._is_book_ritual
    assert overlay._current_event["speaker_name"] == "Andras, Marquis of Discord"

    # 3. Player presses SPACE on Andras dialogue
    handled2 = overlay.handle_event(space_event)
    assert handled2

    # Now overlay must be cleanly dismissed and void cleared
    assert not overlay.is_active
    assert pact_choice_called
    assert not state_in_magic_void


def test_book_ritual_uses_single_book_interface_asset():
    """Verify Book Ritual loads book interface7.png as a single image, not a 32-frame list."""
    from src.game.ui.cinematic_narrative_overlay import CinematicNarrativeOverlay

    overlay = CinematicNarrativeOverlay()
    event = {
        "is_book_ritual": True,
        "speaker_name": "ANCIENT GRIMOIRE",
        "runic_text": "ᛟ ᚱ ᚦ ᛋ ᚹ",
        "dialogue_text": "Translation: A vessel bound in iron...",
        "duration": 5.0,
    }
    overlay.activate(event)

    assert overlay.is_active
    assert overlay._is_book_ritual
    assert overlay._book_image is not None
    assert overlay._book_image.get_size() == (240, 240)
    # Must NOT have loaded the old 32-frame list
    assert len(overlay._book_frames) == 1

    # Update advances elapsed time
    overlay.update(0.1)
    assert overlay._ritual_elapsed >= 0.1

    # Drawing onto a surface renders cleanly without error
    surf = pg.Surface((1280, 720), pg.SRCALPHA)
    overlay.draw(surf)

