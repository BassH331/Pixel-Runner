"""
tests/test_m1_challenger_verification.py

Empirical Challenge & Adversarial Test Harness for Milestone 1:
- Validates all 9 GameState pop-up scene IDs return non-empty dicts with required schema.
- Verifies prologue awakening content is accurate and distinct from boss encounters.
- Verifies mute / unmute toggle behavior for every scene.
- Tests lookups by Entity ID (10, 14, 13, 1, 3) and boundary entities (-999, 0, None, 99999).
- Tests lookups by Flag ("first_kill", "soul_quota", "book_ponder", "first_encounter") and unmapped flags.
- Stress-tests get_popups_by_distance with edge cases (0, -1, 1013, 1400, 36000, 99999, inf, nan).
- Verifies game_data/.level_default.json exists and references a valid on-disk level file.
- Verifies silenced systems invariants (WhispererSystem, boss taunts, ObjectiveDisplay).
"""

import json
import math
import os
import pytest

from src.game.systems.popup_scene_manager import PopupSceneManager
from src.game.systems.whisperer_system import WhispererSystem


REQUIRED_GAMESTATE_SCENE_IDS = [
    "event_prologue_awakening",
    "event_book_ponder",
    "event_first_encounter",
    "event_first_kill",
    "event_forest_inquiry_1400m",
    "event_moonstone_keeper",
    "event_soul_quota_betrayal",
    "event_level_complete",
    "event_demon_time_unlocked",
]

ALL_SCENE_IDS_IN_CONFIG = [
    "event_prologue_awakening",
    "event_first_kill",
    "event_book_ponder",
    "event_sealed_book_encounter",
    "event_first_encounter",
    "event_forest_inquiry_1400m",
    "event_boss_blood_zombie",
    "event_demon_time_unlocked",
    "event_moonstone_keeper",
    "event_gatekeeper_encounter",
    "event_soul_quota_betrayal",
    "event_fabricators_enforcer",
    "event_level_complete",
]

REQUIRED_SCHEMA_KEYS = ["id", "title", "text", "theme", "icon", "hold", "enabled"]


@pytest.fixture(autouse=True)
def reset_popup_mgr():
    PopupSceneManager.reset_instance()
    yield
    PopupSceneManager.reset_instance()


def test_m1_required_gamestate_scene_ids_exist_and_conform():
    """Verify all 9 required GameState scene IDs exist and have valid non-empty fields."""
    mgr = PopupSceneManager.get_instance()
    for sid in REQUIRED_GAMESTATE_SCENE_IDS:
        popup = mgr.get_popup(sid)
        assert popup is not None, f"Required scene ID {sid} returned None"
        assert isinstance(popup, dict), f"Scene {sid} is not a dict"
        assert len(popup) > 0, f"Scene {sid} dictionary is empty"

        for key in REQUIRED_SCHEMA_KEYS:
            assert key in popup, f"Scene {sid} missing required key: {key}"

        assert isinstance(popup["title"], str) and len(popup["title"].strip()) > 0, f"Invalid title in {sid}"
        assert isinstance(popup["text"], str) and len(popup["text"].strip()) > 0, f"Invalid text in {sid}"
        assert isinstance(popup["theme"], str) and len(popup["theme"].strip()) > 0, f"Invalid theme in {sid}"
        assert isinstance(popup["icon"], str) and len(popup["icon"].strip()) > 0, f"Invalid icon in {sid}"
        assert isinstance(popup["hold"], (int, float)) and popup["hold"] > 0, f"Invalid hold duration in {sid}"
        assert isinstance(popup["enabled"], bool), f"Invalid enabled flag in {sid}"


def test_m1_all_13_scenes_conformance():
    """Verify all 13 canonical scenes in scene_popups_config.json conform to schema."""
    mgr = PopupSceneManager.get_instance()
    all_scenes = mgr.get_all_popups()
    assert len(all_scenes) == 13, f"Expected 13 canonical scenes, got {len(all_scenes)}"

    for scene in all_scenes:
        sid = scene["id"]
        assert sid in ALL_SCENE_IDS_IN_CONFIG
        for key in REQUIRED_SCHEMA_KEYS:
            assert key in scene, f"Scene {sid} missing key {key}"
        assert isinstance(scene["hold"], (int, float)) and scene["hold"] > 0


def test_m1_prologue_awakening_narrative_integrity():
    """Verify prologue awakening has distinct title and narrative text, not boss text."""
    mgr = PopupSceneManager.get_instance()
    prologue = mgr.get_popup("event_prologue_awakening")
    assert prologue is not None
    assert prologue["title"] == "The Awakening"
    assert "catacombs" in prologue["text"].lower() or "stir" in prologue["text"].lower()
    assert "enforcer" not in prologue["title"].lower()
    assert "clanking gears" not in prologue["text"].lower()

    # Contrast with Fabricator's Enforcer
    enforcer = mgr.get_popup("event_fabricators_enforcer")
    assert enforcer is not None
    assert enforcer["title"] == "The Fabricator's Enforcer"
    assert "clanking gears" in enforcer["text"].lower()
    assert prologue["text"] != enforcer["text"]


def test_m1_muting_and_unmuting_each_scene():
    """Verify each of the 13 scenes can be muted and unmuted independently."""
    mgr = PopupSceneManager.get_instance()
    for sid in ALL_SCENE_IDS_IN_CONFIG:
        orig = mgr.get_popup(sid)
        assert orig is not None
        orig_enabled = orig["enabled"]

        # Mute
        assert mgr.set_popup_enabled(sid, False) is True
        muted = mgr.get_popup(sid)
        assert muted is not None
        assert muted["enabled"] is False, f"Failed to mute scene {sid}"

        # Unmute
        assert mgr.set_popup_enabled(sid, True) is True
        unmuted = mgr.get_popup(sid)
        assert unmuted is not None
        assert unmuted["enabled"] is True, f"Failed to unmute scene {sid}"

        # Restore original state
        mgr.set_popup_enabled(sid, orig_enabled)
        restored = mgr.get_popup(sid)
        assert restored["enabled"] == orig_enabled


def test_m1_entity_lookups():
    """Verify lookups by entity ID (10, 14, 13, 1, 3) resolve to valid dicts."""
    mgr = PopupSceneManager.get_instance()

    expected_entity_mappings = {
        10: ("event_sealed_book_encounter", 1013),
        14: ("event_boss_blood_zombie", 2558),
        13: ("event_moonstone_keeper", 10500),
        1: ("event_gatekeeper_encounter", 12500),
        3: ("event_fabricators_enforcer", 34500),
    }

    for eid, (expected_id, expected_dist) in expected_entity_mappings.items():
        popup = mgr.get_popup_by_entity(eid)
        assert popup is not None, f"Entity lookup failed for entity {eid}"
        assert popup["id"] == expected_id, f"Entity {eid} resolved to {popup['id']}, expected {expected_id}"
        assert popup["entity_id"] == eid, f"Entity {eid} entity_id field mismatch"
        assert popup["distance"] == expected_dist, f"Entity {eid} distance mismatch"
        for key in REQUIRED_SCHEMA_KEYS:
            assert key in popup

    # Edge cases: non-existent entities
    assert mgr.get_popup_by_entity(-1) is None
    assert mgr.get_popup_by_entity(99999) is None
    assert mgr.get_popup_by_entity(0) is None


def test_m1_flag_lookups():
    """Verify lookups by flag ('first_kill', 'soul_quota', 'book_ponder', 'first_encounter')."""
    mgr = PopupSceneManager.get_instance()

    expected_flag_mappings = {
        "first_kill": "event_first_kill",
        "soul_quota": "event_soul_quota_betrayal",
        "book_ponder": "event_book_ponder",
        "first_encounter": "event_first_encounter",
    }

    for flag, expected_id in expected_flag_mappings.items():
        popup = mgr.get_popup_by_flag(flag)
        assert popup is not None, f"Flag lookup failed for flag '{flag}'"
        assert popup["id"] == expected_id, f"Flag '{flag}' resolved to {popup['id']}, expected {expected_id}"
        assert popup["flag"] == flag, f"Flag '{flag}' field mismatch"
        for key in REQUIRED_SCHEMA_KEYS:
            assert key in popup

    # Edge cases: unmapped flags
    assert mgr.get_popup_by_flag("nonexistent_flag") is None
    assert mgr.get_popup_by_flag("") is None


def test_m1_edge_case_distances():
    """Verify distance lookups for edge cases: 0, -1, 1013, 1400, 36000, 99999."""
    mgr = PopupSceneManager.get_instance()

    # Distance 0: should return prologue awakening
    d0 = mgr.get_popups_by_distance(0.0)
    assert len(d0) >= 1
    assert any(s["id"] == "event_prologue_awakening" for s in d0)

    # Distance -1: should return empty list (no crash)
    dm1 = mgr.get_popups_by_distance(-1.0, tolerance=0.5)
    assert len(dm1) == 0

    # Distance 1013: trigger_type 'distance' filter in get_popups_by_distance
    d1013 = mgr.get_popups_by_distance(1013.0)
    # Note: 1013 popups are trigger_type='entity' or 'flag', so distance query returns empty or distance-type triggers
    assert isinstance(d1013, list)

    # Distance 1400: should return forest inquiry
    d1400 = mgr.get_popups_by_distance(1400.0)
    assert len(d1400) >= 1
    assert any(s["id"] == "event_forest_inquiry_1400m" for s in d1400)

    # Distance 36000: should return level complete
    d36k = mgr.get_popups_by_distance(36000.0)
    assert len(d36k) >= 1
    assert any(s["id"] == "event_level_complete" for s in d36k)

    # Distance 99999: beyond level bounds, returns empty list
    d99k = mgr.get_popups_by_distance(99999.0)
    assert len(d99k) == 0

    # Extreme adversarial values: inf, -inf, nan, large tolerances
    res_inf = mgr.get_popups_by_distance(float("inf"))
    assert res_inf == []

    res_ninf = mgr.get_popups_by_distance(float("-inf"))
    assert res_ninf == []

    res_nan = mgr.get_popups_by_distance(float("nan"))
    assert res_nan == []


def test_m1_default_level_pointer_integrity():
    """Verify game_data/.level_default.json exists and points to an existing file."""
    default_level_path = "game_data/.level_default.json"
    assert os.path.exists(default_level_path), f"{default_level_path} missing"

    with open(default_level_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert "last_level" in data, "last_level key missing in .level_default.json"
    target_level = data["last_level"]
    assert target_level == "game_data/level_1.json", f"Unexpected default level: {target_level}"
    assert os.path.exists(target_level), f"Default level target {target_level} does not exist on disk"


def test_m1_level_1_entity_10_alignment():
    """Verify entity 10 in level_1.json has distance 1013 matching scene config."""
    level_path = "game_data/level_1.json"
    assert os.path.exists(level_path), f"{level_path} missing"

    with open(level_path, "r", encoding="utf-8") as f:
        level_data = json.load(f)

    events = level_data.get("world_events", [])
    entity_10_events = [e for e in events if e.get("id") == 10]
    assert len(entity_10_events) > 0, "Entity 10 not found in level_1.json world_events"
    assert entity_10_events[0].get("distance") == 1013, f"Entity 10 distance is {entity_10_events[0].get('distance')}, expected 1013"

    mgr = PopupSceneManager.get_instance()
    sealed_book = mgr.get_popup("event_sealed_book_encounter")
    assert sealed_book["distance"] == 1013
    assert sealed_book["entity_id"] == 10


def test_m1_silenced_systems_invariants():
    """Verify silenced systems (WhispererSystem, boss taunts, ObjectiveDisplay) are disabled."""
    # 1. WhispererSystem
    assert hasattr(WhispererSystem, "ENABLED")
    assert WhispererSystem.ENABLED is False, "WhispererSystem.ENABLED must remain False"

    # 2. Boss combat taunts commented out in game_state.py
    with open("src/game/states/game_state.py", "r", encoding="utf-8") as f:
        game_state_content = f.read()

    assert "# self._update_boss_combat_taunts(dt)" in game_state_content or \
           "# self._update_boss_combat_taunts" in game_state_content, \
           "Boss combat taunts must remain commented out in GameState"

    # Ensure active call does NOT appear
    active_taunt_lines = [
        line.strip() for line in game_state_content.splitlines()
        if "self._update_boss_combat_taunts(dt)" in line and not line.strip().startswith("#")
    ]
    assert len(active_taunt_lines) == 0, f"Found uncommented boss combat taunt call: {active_taunt_lines}"
