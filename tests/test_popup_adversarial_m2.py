"""
Adversarial Verification Suite for Milestone 2:
PopupSceneManager & popup_controller.py Hardening.

Author: Challenger 1 (Milestone 2)
Scope:
- Scene entries with distance: null, negative distances, non-numeric strings, out-of-order
- PopupControllerApp sorting methods and timeline formatting with null distances
- Linked Entity Inspector resilience with non-numeric / invalid IDs ("?", None, "unknown", etc.)
- PopupSceneManager.get_popups_by_distance() with None, negative, extreme floats, NaN, inf
- PopupSceneManager.save_config() preservation of unowned / external top-level keys
"""

import json
import math
import os
import tempfile
from typing import Any, Dict, List
import pytest
import pygame as pg

os.environ["SDL_VIDEODRIVER"] = "dummy"

from popup_controller import (
    PopupControllerApp,
    EntityCatalog,
    _safe_float,
    safe_render_text,
)
from src.game.systems.popup_scene_manager import PopupSceneManager


@pytest.fixture(autouse=True)
def setup_pg():
    pg.init()
    yield
    pg.quit()


# ─────────────────────────────────────────────────────────────────────────────
# 1. Adversarial Distances & Out-of-Order Scene Sorting
# ─────────────────────────────────────────────────────────────────────────────

def test_safe_float_robustness():
    """Verify _safe_float defensively handles all edge-case, corrupt, and non-numeric inputs."""
    assert _safe_float(None, 0.0) == 0.0
    assert _safe_float(None, -1.0) == -1.0
    assert _safe_float("", 0.0) == 0.0
    assert _safe_float("   ", 0.0) == 0.0
    assert _safe_float("invalid", 42.0) == 42.0
    assert _safe_float("NaN_str", 0.0) == 0.0
    assert _safe_float([], 0.0) == 0.0
    assert _safe_float({}, 0.0) == 0.0
    assert _safe_float(object(), 0.0) == 0.0

    # Valid numeric representations
    assert _safe_float(100) == 100.0
    assert _safe_float(-250.5) == -250.5
    assert _safe_float("1400.25") == 1400.25
    assert _safe_float("-50") == -50.0


def test_scene_entries_distance_adversarial_sorting():
    """Verify sorting scenes containing null, negative, non-numeric, and out-of-order distances."""
    scenes: List[Dict[str, Any]] = [
        {"id": "s_out_5000", "distance": 5000.0, "title": "5000m"},
        {"id": "s_neg_100", "distance": -100.0, "title": "-100m"},
        {"id": "s_null_1", "distance": None, "title": "Null 1"},
        {"id": "s_str_invalid", "distance": "corrupt_data", "title": "Corrupt String"},
        {"id": "s_zero", "distance": 0, "title": "0m"},
        {"id": "s_missing_key", "title": "No Distance Key"},
        {"id": "s_str_num", "distance": "750.5", "title": "750.5m string"},
        {"id": "s_neg_25", "distance": -25.0, "title": "-25m"},
        {"id": "s_null_2", "distance": None, "title": "Null 2"},
    ]

    # Must sort without raising TypeError or ValueError
    scenes.sort(key=lambda s: _safe_float(s.get("distance", 0)))

    sorted_distances = [_safe_float(s.get("distance", 0)) for s in scenes]
    assert sorted_distances == sorted(sorted_distances)
    assert sorted_distances[0] == -100.0
    assert sorted_distances[1] == -25.0
    assert sorted_distances[-1] == 5000.0


# ─────────────────────────────────────────────────────────────────────────────
# 2. PopupControllerApp Timeline Formatting & Sort Methods with Null Distances
# ─────────────────────────────────────────────────────────────────────────────

def test_popup_controller_timeline_formatting_with_null_and_adversarial_distances():
    """Verify PopupControllerApp can sort, format, and render timeline cards with null and negative distances."""
    app = PopupControllerApp(headless=True)
    app.screen = pg.Surface((1400, 850))

    adversarial_scenes = [
        {
            "id": "adv_null_dist",
            "title": "Null Distance Scene",
            "text": "Distance is explicitly null in this scene definition.",
            "trigger_type": "distance",
            "distance": None,
            "theme": "gothic_gold",
            "icon": "assets/graphics/ui/relic_icon.png",
            "hold": 6.0,
            "enabled": True,
        },
        {
            "id": "adv_neg_dist",
            "title": "Negative Distance Scene",
            "text": "Distance is negative, e.g., pre-start milestone.",
            "trigger_type": "distance",
            "distance": -350.0,
            "theme": "blood_bone",
            "icon": "assets/graphics/ui/relic_icon.png",
            "hold": 5.0,
            "enabled": True,
        },
        {
            "id": "adv_str_dist",
            "title": "String Distance Scene",
            "text": "Distance is a non-numeric string.",
            "trigger_type": "distance",
            "distance": "non_numeric_distance",
            "theme": "arcane_void",
            "icon": "assets/graphics/ui/relic_icon.png",
            "hold": 4.0,
            "enabled": True,
        },
        {
            "id": "adv_missing_dist",
            "title": "Missing Distance Scene",
            "text": "Scene dict completely lacks distance key.",
            "trigger_type": "distance",
            "theme": "clean_minimalist",
            "icon": "assets/graphics/ui/relic_icon.png",
            "hold": 4.0,
            "enabled": True,
        },
        {
            "id": "adv_flag_null_dist",
            "title": "Flag Null Distance",
            "text": "Flag-triggered popup with null distance.",
            "trigger_type": "flag",
            "flag": "flag_adversarial_test",
            "distance": None,
            "theme": "grimoire_leather",
            "icon": "assets/graphics/ui/relic_icon.png",
            "hold": 5.0,
            "enabled": False,
        },
    ]

    # Inject into app scenes
    app.scenes.extend(adversarial_scenes)

    # Sort app scenes
    app.scenes.sort(key=lambda s: _safe_float(s.get("distance", 0)))

    # Test filtering across tabs
    for tab in ("ALL", "DISTANCE", "ENTITY", "FLAGS"):
        app.filter_tab = tab
        filtered = app._get_filtered_scenes()
        assert isinstance(filtered, list)

    # Test timeline card rendering for every scene
    app.filter_tab = "ALL"
    for i, s in enumerate(app.scenes):
        app._select_scene(i)
        # draw() executes the entire timeline formatting and center editor card logic
        app.draw()

    # Test distance adjustment steppers on null distance scene
    null_scene = next(s for s in app.scenes if s.get("id") == "adv_null_dist")
    app.selected_index = app.scenes.index(null_scene)

    ed_rects = app._get_editor_rects(null_scene)
    if "dist_minus" in ed_rects:
        # Simulate dist_minus logic: cur_dist = _safe_float(scene.get("distance", 0))
        cur = _safe_float(null_scene.get("distance", 0))
        null_scene["distance"] = max(0.0, cur - 50.0)
        assert null_scene["distance"] == 0.0

    if "dist_plus" in ed_rects:
        cur = _safe_float(null_scene.get("distance", 0))
        null_scene["distance"] = cur + 50.0
        assert null_scene["distance"] == 50.0


# ─────────────────────────────────────────────────────────────────────────────
# 3. Linked Entity Inspector Resilience against Invalid / Non-Numeric Entity IDs
# ─────────────────────────────────────────────────────────────────────────────

def test_entity_catalog_invalid_ids():
    """Verify EntityCatalog methods safely tolerate non-numeric, null, or corrupted IDs."""
    catalog = EntityCatalog("game_data/level_1.json")

    invalid_eids = ["?", None, "unknown", "", "-1", "999999", 999999, [], {}, object()]

    for eid in invalid_eids:
        # get_entity must return None or fallback without throwing ValueError or TypeError
        ent = catalog.get_entity(eid)
        if eid not in (1, 3, 10, 13, 14):  # known valid entities
            assert ent is None or isinstance(ent, dict)

        # get_avatar_surface must return a valid Surface without raising
        avatar = catalog.get_avatar_surface(eid, size=(44, 44))
        assert isinstance(avatar, pg.Surface)
        assert avatar.get_size() == (44, 44)


def test_popup_controller_entity_inspector_rendering_invalid_ids():
    """Verify app.draw() renders entity inspector card for invalid entity IDs without crashing."""
    app = PopupControllerApp(headless=True)
    app.screen = pg.Surface((1400, 850))

    adversarial_eids = ["?", None, "unknown", "", "-99", "abc_123", 999999]

    for eid in adversarial_eids:
        test_scene = {
            "id": f"adv_entity_{eid}",
            "title": f"Entity Scene {eid}",
            "text": "Testing entity inspector robustness with invalid entity ID.",
            "trigger_type": "entity",
            "entity_id": eid,
            "distance": 1000.0,
            "theme": "gothic_gold",
            "icon": "assets/graphics/ui/relic_icon.png",
            "hold": 6.0,
            "enabled": True,
        }
        app.scenes = [test_scene]
        app.selected_index = 0

        # Rendering must not raise ValueError: invalid literal for int()
        app.draw()


# ─────────────────────────────────────────────────────────────────────────────
# 4. PopupSceneManager.get_popups_by_distance() Boundary & Extreme Value Tests
# ─────────────────────────────────────────────────────────────────────────────

def test_popup_scene_manager_distance_queries_adversarial():
    """Verify get_popups_by_distance with None, negative, extreme floats, NaN, and inf."""
    PopupSceneManager.reset_instance()
    mgr = PopupSceneManager.get_instance()

    # None distance must return empty list without TypeError
    assert mgr.get_popups_by_distance(None) == []

    # Negative distance queries
    assert mgr.get_popups_by_distance(-100.0) == []
    assert mgr.get_popups_by_distance(-1e15) == []

    # Extreme positive floats
    assert mgr.get_popups_by_distance(1e30) == []

    # Floating point infinities and NaN
    assert mgr.get_popups_by_distance(float("inf")) == []
    assert mgr.get_popups_by_distance(float("-inf")) == []
    assert mgr.get_popups_by_distance(float("nan")) == []

    # Inject scenes with corrupted distance fields into manager
    corrupt_scenes = [
        {"id": "corr_null", "trigger_type": "distance", "distance": None},
        {"id": "corr_str", "trigger_type": "distance", "distance": "unparseable"},
        {"id": "corr_missing", "trigger_type": "distance"},
        {"id": "corr_neg", "trigger_type": "distance", "distance": -150.0},
        {"id": "corr_valid", "trigger_type": "distance", "distance": 1400.0},
    ]
    orig_scenes = mgr.get_all_popups()
    mgr.set_all_scenes(orig_scenes + corrupt_scenes)

    # Corrupt scenes must be skipped safely
    matches = mgr.get_popups_by_distance(1400.0, tolerance=10.0)
    assert any(m["id"] == "corr_valid" for m in matches)
    assert not any(m["id"] in ("corr_null", "corr_str", "corr_missing") for m in matches)

    # Query near negative distance
    neg_matches = mgr.get_popups_by_distance(-150.0, tolerance=5.0)
    assert len(neg_matches) == 1
    assert neg_matches[0]["id"] == "corr_neg"

    # Restore original scenes
    mgr.set_all_scenes(orig_scenes)


# ─────────────────────────────────────────────────────────────────────────────
# 5. PopupSceneManager.save_config() External & Unowned Top-Level Key Preservation
# ─────────────────────────────────────────────────────────────────────────────

def test_popup_scene_manager_save_config_preserves_unowned_keys():
    """Verify that save_config() preserves external top-level JSON fields intact across updates."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        cfg_file = os.path.join(tmp_dir, "scene_popups_with_meta.json")

        initial_payload = {
            "version": "4.2.0-custom",
            "description": "Custom verified popups configuration",
            "author": "Antigravity Pipeline Specialist",
            "schema_flags": {"strict_validation": True, "checksum": "deadbeef88"},
            "custom_metadata_tags": ["cinematic", "act_1", "hardened"],
            "telemetry_hooks": {
                "endpoint": "https://api.pixelrunner.game/v1/telemetry",
                "sample_rate": 0.05,
            },
            "scenes": [
                {
                    "id": "event_initial_mock",
                    "title": "Mock Initial",
                    "text": "Initial text body.",
                    "trigger_type": "distance",
                    "distance": 100.0,
                    "theme": "gothic_gold",
                    "icon": "assets/graphics/ui/relic_icon.png",
                    "hold": 6.0,
                    "enabled": True,
                }
            ],
        }

        with open(cfg_file, "w", encoding="utf-8") as f:
            json.dump(initial_payload, f, indent=2)

        # Initialize manager targeting the custom file
        PopupSceneManager.reset_instance()
        mgr = PopupSceneManager.get_instance(config_path=cfg_file)

        # Mutate existing popup
        assert mgr.update_popup("event_initial_mock", {"title": "Updated Mock Title"}) is True

        # Add a new popup
        mgr.add_popup({
            "id": "event_added_adversarial",
            "title": "Adversarially Added Event",
            "text": "Testing external key preservation under additions.",
            "trigger_type": "flag",
            "flag": "flag_save_test",
            "distance": 0,
            "theme": "blood_bone",
            "hold": 5.0,
            "enabled": True,
        })

        # Save to disk
        assert mgr.save_config() is True

        # Read back raw disk JSON and verify top-level unowned keys are 100% intact
        with open(cfg_file, "r", encoding="utf-8") as f:
            saved_data = json.load(f)

        assert saved_data["version"] == "4.2.0-custom"
        assert saved_data["description"] == "Custom verified popups configuration"
        assert saved_data["author"] == "Antigravity Pipeline Specialist"
        assert saved_data["schema_flags"] == {"strict_validation": True, "checksum": "deadbeef88"}
        assert saved_data["custom_metadata_tags"] == ["cinematic", "act_1", "hardened"]
        assert saved_data["telemetry_hooks"] == {
            "endpoint": "https://api.pixelrunner.game/v1/telemetry",
            "sample_rate": 0.05,
        }

        # Verify scenes array updated properly
        assert len(saved_data["scenes"]) == 2
        mock_scene = next(s for s in saved_data["scenes"] if s["id"] == "event_initial_mock")
        assert mock_scene["title"] == "Updated Mock Title"
        added_scene = next(s for s in saved_data["scenes"] if s["id"] == "event_added_adversarial")
        assert added_scene["flag"] == "flag_save_test"

        # Clean reset
        PopupSceneManager.reset_instance()
