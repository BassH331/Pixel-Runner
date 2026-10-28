"""
tests/test_game_state_popup_triggers.py

Comprehensive E2E Verification Suite for GameState Pop-up Triggers & Scene Configurations.

Verifies:
1. Headless Pygame fixture using dummy video/audio driver.
2. Complete resolution of all 9 GameState event IDs in scene_popups_config.json:
   - event_prologue_awakening
   - event_book_ponder
   - event_first_encounter
   - event_first_kill
   - event_forest_inquiry_1400m
   - event_moonstone_keeper
   - event_soul_quota_betrayal
   - event_level_complete
   - event_demon_time_unlocked
3. Schema integrity: valid non-empty title/text, positive hold times, valid themes in THEME_PRESETS, valid icons.
4. Programmatic confirmation that all pop-up triggers in GameState resolve to valid configs without fallbacks.
5. Content verification: event_prologue_awakening contains title "The Awakening" and body text specific
   to the prologue awakening, NOT the Fabricator's Enforcer.
6. Entity trigger distances and IDs match game_data/level_1.json (Entities 10, 14, 13, 1, 3).
7. Default level pointer (.level_default.json) references an existing, valid level configuration.
8. Silenced systems invariants: WhispererSystem.ENABLED is False, boss taunt loop in game_state.py:1476
   remains commented out, and ObjectiveDisplay starts inactive.
9. Headless rendering of SideNotification(1280, 720) with each retrieved config without unhandled exceptions.
"""

from __future__ import annotations

import os
import json
import re
import pytest
import pygame as pg

from src.game.systems.popup_scene_manager import PopupSceneManager
from src.game.systems.notification_config_manager import THEME_PRESETS
from src.game.ui.side_notification import SideNotification, _NotificationItem
from src.game.systems.whisperer_system import WhispererSystem
from src.game.ui.objective_display import ObjectiveDisplay


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module", autouse=True)
def headless_pygame_env():
    """Ensure headless pygame display and font drivers are initialized."""
    os.environ["SDL_VIDEODRIVER"] = "dummy"
    os.environ["SDL_AUDIODRIVER"] = "dummy"
    if not pg.get_init():
        pg.init()
    if not pg.font.get_init():
        pg.font.init()
    try:
        if not pg.mixer.get_init():
            pg.mixer.init()
    except Exception:
        pass
    screen = pg.display.set_mode((1280, 720))
    yield screen
    # Do not call pg.quit() at module level to prevent breaking session fixtures


@pytest.fixture
def popup_manager():
    """Provides a freshly loaded PopupSceneManager instance."""
    PopupSceneManager.reset_instance()
    mgr = PopupSceneManager.get_instance()
    mgr.load_config()
    return mgr


# ── Constant Definitions ──────────────────────────────────────────────────────

GAMESTATE_9_EVENT_IDS = [
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

EXPECTED_LEVEL_ENTITIES = {
    10: {
        "title": "The Sealed Book",
        "distance": 1013,
        "scene_id": "event_sealed_book_encounter",
        "theme": "grimoire_leather",
    },
    14: {
        "title": "Blood Zombie",
        "distance": 2558,
        "scene_id": "event_boss_blood_zombie",
        "theme": "blood_bone",
    },
    13: {
        "title": "The Moonstone Keeper",
        "distance": 10500,
        "scene_id": "event_moonstone_keeper",
        "theme": "arcane_void",
    },
    1: {
        "title": "The Gatekeeper",
        "distance": 12500,
        "scene_id": "event_gatekeeper_encounter",
        "theme": "gothic_gold",
    },
    3: {
        "title": "The Fabricator's Enforcer",
        "distance": 34500,
        "scene_id": "event_fabricators_enforcer",
        "theme": "clean_minimalist",
    },
}


# ── Test Cases ────────────────────────────────────────────────────────────────

class TestGameStatePopupTriggers:
    """Test suite verifying all pop-up triggers and configurations referenced by GameState."""

    @pytest.mark.parametrize("event_id", GAMESTATE_9_EVENT_IDS)
    def test_gamestate_event_ids_exist_and_valid(self, popup_manager, event_id):
        """
        Verify that each of the 9 GameState event IDs exists in scene_popups_config.json
        with positive hold times, valid themes in THEME_PRESETS, and non-empty valid fields.
        """
        popup = popup_manager.get_popup(event_id)
        assert popup is not None, f"GameState event '{event_id}' must resolve in PopupSceneManager (got None)"

        # Title checks
        assert "title" in popup, f"Missing 'title' in event '{event_id}'"
        assert isinstance(popup["title"], str) and len(popup["title"].strip()) > 0, (
            f"Event '{event_id}' has empty or invalid title"
        )

        # Text checks
        assert "text" in popup, f"Missing 'text' in event '{event_id}'"
        assert isinstance(popup["text"], str) and len(popup["text"].strip()) > 0, (
            f"Event '{event_id}' has empty or invalid text"
        )

        # Hold time checks
        assert "hold" in popup, f"Missing 'hold' in event '{event_id}'"
        assert isinstance(popup["hold"], (int, float)), f"Event '{event_id}' hold time must be numeric"
        assert popup["hold"] > 0.0, f"Event '{event_id}' hold time must be positive (got {popup['hold']})"

        # Theme checks
        assert "theme" in popup, f"Missing 'theme' in event '{event_id}'"
        theme = popup["theme"]
        assert theme in THEME_PRESETS, (
            f"Event '{event_id}' theme '{theme}' is not recognized in THEME_PRESETS "
            f"({list(THEME_PRESETS.keys())})"
        )

        # Icon checks
        assert "icon" in popup, f"Missing 'icon' in event '{event_id}'"
        assert isinstance(popup["icon"], str) and len(popup["icon"].strip()) > 0, (
            f"Event '{event_id}' icon path must be non-empty string"
        )

        # Enabled check
        assert popup.get("enabled", True) is True, f"Event '{event_id}' should be enabled by default"

    def test_prologue_awakening_content_not_fabricator(self, popup_manager):
        """
        Verify that event_prologue_awakening contains title 'The Awakening' and
        body text specific to the prologue awakening, NOT the Fabricator's Enforcer.
        """
        prologue = popup_manager.get_popup("event_prologue_awakening")
        assert prologue is not None, "event_prologue_awakening must exist"

        # Assert correct title
        assert prologue["title"] == "The Awakening", (
            f"Prologue awakening title must be 'The Awakening', got '{prologue['title']}'"
        )

        # Assert prologue narrative context, strictly distinct from the boss encounter
        text_lower = prologue["text"].lower()
        assert "fabricator" not in text_lower, "Prologue text must not mention the Fabricator"
        assert "clanking gears" not in text_lower, "Prologue text must not contain Fabricator boss text"
        assert any(word in text_lower for word in ("catacombs", "death", "dark", "shadows", "advance")), (
            f"Prologue text '{prologue['text']}' missing expected awakening narrative cues"
        )

        # Also verify event_fabricators_enforcer remains distinct as entity 3
        enforcer = popup_manager.get_popup("event_fabricators_enforcer")
        assert enforcer is not None
        assert "Fabricator" in enforcer["title"]
        assert prologue["id"] != enforcer["id"]

    def test_entity_trigger_distances_and_ids_match_level_1(self, popup_manager):
        """
        Verify that entity trigger distances and IDs match game_data/level_1.json
        (Entities 10, 14, 13, 1, 3).
        """
        level_path = "game_data/level_1.json"
        assert os.path.exists(level_path), f"Canonical level file {level_path} missing"

        with open(level_path, "r", encoding="utf-8") as f:
            level_data = json.load(f)

        world_events = level_data.get("world_events", [])
        events_by_id = {ev.get("id"): ev for ev in world_events}

        for eid, exp in EXPECTED_LEVEL_ENTITIES.items():
            # 1. Verify entity exists in level_1.json world_events
            assert eid in events_by_id, f"Entity {eid} ({exp['title']}) missing from level_1.json"
            lvl_ev = events_by_id[eid]
            lvl_dist = lvl_ev.get("distance")
            assert lvl_dist == exp["distance"], (
                f"Entity {eid} distance in level_1.json is {lvl_dist}, expected {exp['distance']}"
            )

            # 2. Verify entity lookup in PopupSceneManager
            popup = popup_manager.get_popup_by_entity(eid)
            assert popup is not None, f"PopupSceneManager must find popup for entity {eid}"
            assert popup["id"] == exp["scene_id"], (
                f"Entity {eid} mapped to scene '{popup['id']}', expected '{exp['scene_id']}'"
            )
            assert popup.get("distance") == exp["distance"], (
                f"Popup scene '{popup['id']}' distance {popup.get('distance')} does not match "
                f"expected level distance {exp['distance']} for Entity {eid}"
            )
            assert popup.get("theme") == exp["theme"], (
                f"Popup scene '{popup['id']}' theme '{popup.get('theme')}' != expected '{exp['theme']}'"
            )

        # Specifically assert Entity 10 is at 1013m, NOT legacy erroneous 650m
        sealed_book_popup = popup_manager.get_popup_by_entity(10)
        assert sealed_book_popup["distance"] == 1013, (
            f"Entity 10 (Sealed Book) distance must be 1013m (level_1 parity), got {sealed_book_popup['distance']}"
        )

    def test_default_level_pointer_references_existing_level(self):
        """
        Verify that game_data/.level_default.json references an existing, valid level file.
        """
        default_ptr_path = "game_data/.level_default.json"
        assert os.path.exists(default_ptr_path), f"{default_ptr_path} must exist"

        with open(default_ptr_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert "last_level" in data, f"{default_ptr_path} missing 'last_level' key"
        target_level = data["last_level"]

        # Ensure it does not point to non-existent level_2.json
        assert target_level != "game_data/level_2.json", (
            "Default level pointer must not point to non-existent 'level_2.json'"
        )

        # Ensure the pointed file exists on disk and is a valid JSON level file
        assert os.path.exists(target_level), f"Target level file '{target_level}' does not exist on disk"
        with open(target_level, "r", encoding="utf-8") as f:
            lvl_content = json.load(f)

        assert "world_events" in lvl_content, f"Level file '{target_level}' missing 'world_events'"
        assert "level_end_distance" in lvl_content, f"Level file '{target_level}' missing 'level_end_distance'"

    def test_silenced_systems_remain_disabled(self):
        """
        Verify that silenced systems remain confirmed disabled:
        1. WhispererSystem.ENABLED = False
        2. Boss combat taunt loop in game_state.py:1476 remains commented out
        3. ObjectiveDisplay starts inactive
        """
        # 1. WhispererSystem invariant
        assert hasattr(WhispererSystem, "ENABLED"), "WhispererSystem must declare ENABLED attribute"
        assert WhispererSystem.ENABLED is False, (
            f"WhispererSystem.ENABLED must remain False (got {WhispererSystem.ENABLED})"
        )

        # 2. Boss combat taunts loop in src/game/states/game_state.py
        game_state_file = "src/game/states/game_state.py"
        assert os.path.exists(game_state_file), f"{game_state_file} missing"

        with open(game_state_file, "r", encoding="utf-8") as f:
            lines = f.readlines()

        uncommented_taunts = []
        commented_found = False
        for idx, line in enumerate(lines, start=1):
            stripped = line.strip()
            if "_update_boss_combat_taunts" in stripped:
                if stripped.startswith("def "):
                    continue
                if stripped.startswith("#"):
                    commented_found = True
                else:
                    uncommented_taunts.append((idx, stripped))

        assert commented_found is True, (
            "Commented boss combat taunts reference ('# self._update_boss_combat_taunts(dt)') "
            "must remain in game_state.py"
        )
        assert len(uncommented_taunts) == 0, (
            f"Found active uncommented boss combat taunts calls in game_state.py: {uncommented_taunts}"
        )

        # 3. ObjectiveDisplay invariant
        from v3x_zulfiqar_gideon import UITheme
        UITheme.configure_overlays(
            stone_path="assets/graphics/UI/PNG/UI board Medium  stone.png",
            parchment_path="assets/graphics/UI/PNG/UI board Medium  parchment.png",
            title_font_path="assets/Colorfiction_HandDrawnFonts/Colorfiction - Gothic - Regular.otf",
            body_font_path="assets/Colorfiction_HandDrawnFonts/Colorfiction - Papyrus.otf",
            text_color=(60, 40, 20),
        )
        obj_display = ObjectiveDisplay()
        assert hasattr(obj_display, "is_active"), "ObjectiveDisplay must have is_active attribute"
        assert obj_display.is_active is False, (
            f"ObjectiveDisplay must initialize inactive (got {obj_display.is_active})"
        )

    def test_programmatic_gamestate_trigger_resolution_without_fallback(self, popup_manager):
        """
        Programmatically confirm all pop-up triggers in GameState resolve to existing,
        valid config entries in scene_popups_config.json without falling back to hardcoded error states.
        """
        # Define the exact trigger lookup contract from GameState
        trigger_scenarios = [
            # Game start / prologue entry (GameState:966)
            {
                "name": "Prologue Entry",
                "lookup": lambda mgr: mgr.get_popup("event_prologue_awakening"),
                "expected_id": "event_prologue_awakening",
            },
            # Soul quota milestone (GameState:899)
            {
                "name": "Soul Quota Harvest",
                "lookup": lambda mgr: mgr.get_popup("event_soul_quota_betrayal"),
                "expected_id": "event_soul_quota_betrayal",
            },
            # Sealed Book / Grimoire ambient lore & buff data (GameState:919, 2127)
            {
                "name": "Book Ponder Reflection",
                "lookup": lambda mgr: mgr.get_popup("event_book_ponder"),
                "expected_id": "event_book_ponder",
            },
            # Sealed Book entity interaction (GameState:1070, 1112)
            {
                "name": "Sealed Book Entity Interaction",
                "lookup": lambda mgr: mgr.get_popup_by_entity(10),
                "expected_id": "event_sealed_book_encounter",
            },
            # Blood Zombie boss entity interaction (GameState:1070, 1112)
            {
                "name": "Blood Zombie Entity Interaction",
                "lookup": lambda mgr: mgr.get_popup_by_entity(14),
                "expected_id": "event_boss_blood_zombie",
            },
            # Demon Time unlock @ 2600m (GameState:1646)
            {
                "name": "Demon Time Unlock",
                "lookup": lambda mgr: mgr.get_popup("event_demon_time_unlocked"),
                "expected_id": "event_demon_time_unlocked",
            },
            # Forest inquiry distance milestone @ 1400m (GameState:1677)
            {
                "name": "1400m Forest Inquiry",
                "lookup": lambda mgr: mgr.get_popup("event_forest_inquiry_1400m"),
                "expected_id": "event_forest_inquiry_1400m",
            },
            # Moonstone Keeper entity interaction @ 10500m (GameState:1070, 1112)
            {
                "name": "Moonstone Keeper Interaction",
                "lookup": lambda mgr: mgr.get_popup_by_entity(13),
                "expected_id": "event_moonstone_keeper",
            },
            # The Gatekeeper entity interaction @ 12500m (GameState:1070, 1112)
            {
                "name": "Gatekeeper Interaction",
                "lookup": lambda mgr: mgr.get_popup_by_entity(1),
                "expected_id": "event_gatekeeper_encounter",
            },
            # Level endpoint completion @ 36000m (GameState:1575)
            {
                "name": "Level Completion",
                "lookup": lambda mgr: mgr.get_popup("event_level_complete"),
                "expected_id": "event_level_complete",
            },
            # Flag trigger: First Kill (GameState:1835, 1842)
            {
                "name": "First Kill Flag Trigger",
                "lookup": lambda mgr: mgr.get_popup_by_flag("first_kill"),
                "expected_id": "event_first_kill",
            },
            # Flag trigger / text match: First Encounter (GameState:1840)
            {
                "name": "First Encounter Lookup",
                "lookup": lambda mgr: mgr.get_popup("event_first_encounter"),
                "expected_id": "event_first_encounter",
            },
            # Flag trigger: Soul Quota (GameState:1835)
            {
                "name": "Soul Quota Flag Trigger",
                "lookup": lambda mgr: mgr.get_popup_by_flag("soul_quota"),
                "expected_id": "event_soul_quota_betrayal",
            },
            # Flag trigger: Book Ponder (GameState:1835)
            {
                "name": "Book Ponder Flag Trigger",
                "lookup": lambda mgr: mgr.get_popup_by_flag("book_ponder"),
                "expected_id": "event_book_ponder",
            },
        ]

        for scn in trigger_scenarios:
            result = scn["lookup"](popup_manager)
            assert result is not None, (
                f"GameState trigger scenario '{scn['name']}' returned None! "
                f"This triggers a hardcoded in-code fallback state."
            )
            assert isinstance(result, dict), f"Scenario '{scn['name']}' must return a configuration dict"
            assert result.get("id") == scn["expected_id"], (
                f"Scenario '{scn['name']}' returned scene '{result.get('id')}', expected '{scn['expected_id']}'"
            )
            assert result.get("enabled", True) is True, f"Scenario '{scn['name']}' returned disabled scene"

    def test_side_notification_headless_rendering_all_scenes(self, popup_manager):
        """
        Test headless rendering of SideNotification(1280, 720) with each retrieved
        configuration without unhandled exceptions.
        """
        all_scenes = popup_manager.get_all_popups()
        assert len(all_scenes) >= 13, f"Expected at least 13 scenes in config, found {len(all_scenes)}"

        for scene in all_scenes:
            sn = SideNotification(1280, 720)
            assert sn is not None
            scene_id = scene["id"]
            title = scene.get("title", "Test Title")
            text = scene.get("text", "Test Body")
            theme = scene.get("theme", "gothic_gold")
            icon = scene.get("icon", None)
            hold = scene.get("hold", 6.0)

            # Show the notification
            sn.show(
                text=text,
                title=title,
                icon=icon,
                hold=hold,
                theme=theme,
            )

            # Assert item queued/active
            assert sn._current_item is not None, f"Scene '{scene_id}' failed to set _current_item"
            assert sn._current_item.theme == theme

            # Build tab surface headlessly
            try:
                sn._build_tab_surface(sn._current_item)
            except Exception as exc:
                pytest.fail(f"Headless rendering for scene '{scene_id}' raised unexpected exception: {exc}")

            # Verify surface dimensions and state
            assert sn._current_tab_surface is not None, f"Scene '{scene_id}' generated None tab surface"
            assert sn._current_tab_surface.get_width() > 0, f"Scene '{scene_id}' width <= 0"
            assert sn._current_tab_surface.get_height() > 0, f"Scene '{scene_id}' height <= 0"

            # Tick updates through transitions
            sn.update(0.1)
            sn.update(1.0)
            sn.clear()
