"""
Tests for Foreground Prop Depth Rendering, Deletion Persistence, and CIA Triad Security Hardening.
"""

import os
import json
import pytest
import pygame as pg

if not pg.get_init():
    pg.init()
if not pg.display.get_surface():
    pg.display.set_mode((1280, 720), pg.NOFRAME)

from src.game.systems.environment_manager import EnvironmentManager, EnvironmentProp
from src.game.systems.the_eye_manager import TheEyePerceptionManager


# ── 1. PROP DEPTH & Z-ORDER TESTS ──────────────────────────────────────────────

def test_prop_is_in_front_layer_depth():
    """Verify that default in_front is derived from layer index (layers 1-6 = False, 7-9 = True)."""
    p_bg = EnvironmentProp(
        texture_path="assets/graphics/background images/new_bg_images/bg_image.png",
        slice_rect=[0, 0, 64, 64],
        pos_x=100.0,
        pos_y=500.0,
        layer_index=3,
    )
    assert p_bg.is_in_front() is False

    p_road = EnvironmentProp(
        texture_path="assets/graphics/background images/new_bg_images/bg_image.png",
        slice_rect=[0, 0, 64, 64],
        pos_x=100.0,
        pos_y=500.0,
        layer_index=6,
    )
    assert p_road.is_in_front() is False

    p_l7 = EnvironmentProp(
        texture_path="assets/graphics/background images/new_bg_images/bg_image.png",
        slice_rect=[0, 0, 64, 64],
        pos_x=100.0,
        pos_y=500.0,
        layer_index=7,
    )
    assert p_l7.is_in_front() is True

    p_l9 = EnvironmentProp(
        texture_path="assets/graphics/background images/new_bg_images/bg_image.png",
        slice_rect=[0, 0, 64, 64],
        pos_x=100.0,
        pos_y=500.0,
        layer_index=9,
    )
    assert p_l9.is_in_front() is True


def test_prop_is_in_front_explicit_override():
    """Verify that explicit in_front overrides layer index."""
    p_override_front = EnvironmentProp(
        texture_path="assets/graphics/background images/new_bg_images/bg_image.png",
        slice_rect=[0, 0, 64, 64],
        pos_x=100.0,
        pos_y=500.0,
        layer_index=3,  # Normally background
        in_front=True,
    )
    assert p_override_front.is_in_front() is True

    p_override_back = EnvironmentProp(
        texture_path="assets/graphics/background images/new_bg_images/bg_image.png",
        slice_rect=[0, 0, 64, 64],
        pos_x=100.0,
        pos_y=500.0,
        layer_index=8,  # Normally foreground
        in_front=False,
    )
    assert p_override_back.is_in_front() is False


def test_prop_serialization_preserves_in_front():
    """Verify that to_dict and deserialization preserve in_front state."""
    p = EnvironmentProp(
        texture_path="assets/graphics/background images/new_bg_images/bg_image.png",
        slice_rect=[0, 0, 64, 64],
        pos_x=100.0,
        pos_y=500.0,
        layer_index=4,
        in_front=True,
    )
    d = p.to_dict()
    assert d.get("in_front") is True

    mgr = EnvironmentManager(1280, 720, env_config={"props": [d]})
    assert len(mgr.props) == 1
    assert mgr.props[0].is_in_front() is True


def test_environment_draw_foreground_pass_split():
    """Verify that draw() separates background and foreground rendering passes without error."""
    surf = pg.Surface((1280, 720))
    p_back = EnvironmentProp(
        texture_path="assets/graphics/background images/new_bg_images/bg_image.png",
        slice_rect=[0, 0, 64, 64],
        pos_x=100.0,
        pos_y=500.0,
        layer_index=3,
        in_front=False,
    )
    p_front = EnvironmentProp(
        texture_path="assets/graphics/background images/new_bg_images/bg_image.png",
        slice_rect=[0, 0, 64, 64],
        pos_x=100.0,
        pos_y=500.0,
        layer_index=5,
        in_front=True,
    )

    mgr = EnvironmentManager(1280, 720)
    mgr.props = [p_back, p_front]

    # Background pass: draws layers <= 6 and behind props
    mgr.draw(surf, cam_x=0.0, cam_y=0.0, foreground_pass=False)

    # Foreground pass: doesn't clear bg, and draws layers >= 7 and in-front props
    mgr.draw(surf, cam_x=0.0, cam_y=0.0, clear_bg=False, foreground_pass=True)


# ── 2. DATA INTEGRITY & DELETION PERSISTENCE TESTS ─────────────────────────────

def test_the_eye_save_perception_does_not_resurrect_deleted_entities(tmp_path):
    """Verify that saving perception does not recreate entities that were deleted from level_1.json."""
    level_file = str(tmp_path / "test_level.json")
    story_file = str(tmp_path / "test_story.json")

    # Start with level containing only player and one boss
    initial_level = {
        "level_name": "Test Level",
        "level_end_distance": 36000,
        "world_events": [
            {"id": "14", "type": "boss", "params": {"title": "Blood Zombie"}},
        ],
        "entities": [{"type": "player", "x": 200, "y": 600}],
    }
    with open(level_file, "w", encoding="utf-8") as f:
        json.dump(initial_level, f)

    with open(story_file, "w", encoding="utf-8") as f:
        json.dump({"boss_dialogue": {}, "relics": {}, "enemy_taunts": {}}, f)

    mgr = TheEyePerceptionManager(level_path=level_file, storyline_path=story_file)
    success, _ = mgr.save_perception()
    assert success is True

    # Read back level file: verify no deleted items (void scribe, candora, etc.) were resurrected!
    with open(level_file, "r", encoding="utf-8") as f:
        saved_level = json.load(f)

    event_ids = [e.get("id") for e in saved_level.get("world_events", [])]
    assert "npc_void_scribe" not in event_ids
    assert "npc_candora_messenger" not in event_ids
    assert "lore_void_bloom" not in event_ids
    assert "14" in event_ids


def test_atomic_file_write_creates_backup(tmp_path):
    """Verify that atomic write creates timestamped backup and valid JSON."""
    test_file = str(tmp_path / "data.json")
    with open(test_file, "w", encoding="utf-8") as f:
        json.dump({"version": 1}, f)

    story_file = str(tmp_path / "story.json")
    with open(story_file, "w", encoding="utf-8") as f:
        json.dump({"version": 1}, f)

    mgr = TheEyePerceptionManager(level_path=test_file, storyline_path=story_file)
    mgr._save_with_backup(test_file, {"version": 2})

    # Read target file
    with open(test_file, "r", encoding="utf-8") as f:
        saved = json.load(f)
    assert saved["version"] == 2

    # Verify backup exists
    backups = [f for f in os.listdir(tmp_path) if f.startswith("data.json.backup_")]
    assert len(backups) >= 1


# ── 3. CIA TRIAD CONFIDENTIALITY AUDIT TEST ────────────────────────────────────

def test_cia_confidentiality_no_tracked_tokens():
    """Verify that no sensitive credential files or tokens are tracked in git index."""
    import subprocess
    res = subprocess.run(
        ["git", "ls-files"],
        capture_output=True,
        text=True,
        cwd=os.path.abspath(os.path.join(os.path.dirname(__file__), "..")),
    )
    tracked_files = res.stdout.splitlines()

    forbidden_patterns = [
        "env_production",
        ".env.local",
        ".token",
        ".key",
        ".pem",
    ]
    for tf in tracked_files:
        for pat in forbidden_patterns:
            assert pat not in tf.lower(), f"Security violation: Sensitive file tracked in git: {tf}"
