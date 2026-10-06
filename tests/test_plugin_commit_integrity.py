"""
tests/test_plugin_commit_integrity.py

Verification suite for multi-plugin commit integrity across Pixel Runner editors:
1. Cross-plugin preservation between LevelEditor, The Eye, and WaveEditor
2. Prevention of item resurrection and clobbering across concurrent plugin workflows
3. Atomic transactional file writes and non-empty backup safety
4. Rollback checkpoint integrity and isolation
"""

import os
import json
import copy
import pytest
from src.game.systems.the_eye_manager import TheEyePerceptionManager


def _create_sample_level_data():
    return {
        "level_name": "Test Realm - Dark Woods",
        "level_end_distance": 36000,
        "spawn_zones": [
            {"id": "zone_1", "min_dist": 0, "max_dist": 2000, "types": ["bat"]},
            {"id": "zone_2", "min_dist": 2000, "max_dist": 5000, "types": ["skeleton"]},
        ],
        "world_events": [
            {
                "id": 10,
                "distance": 650,
                "type": "npc",
                "params": {
                    "npc_type": "generic",
                    "title": "The Sealed Book",
                    "text": "Initial book text",
                    "is_magic_book": True,
                },
            },
            {
                "id": 14,
                "distance": 2558,
                "type": "boss",
                "params": {
                    "title": "Blood Zombie",
                    "health": 120.0,
                },
            },
        ],
        "environment": {
            "ground_y": 551,
            "props": [
                {
                    "texture_path": "assets/graphics/prop1.png",
                    "pos_x": 400.0,
                    "pos_y": 500.0,
                    "width": 64,
                    "height": 64,
                    "layer_index": 6,
                    "in_front": True,
                }
            ],
        },
        "entities": [{"type": "player", "x": 200, "y": 600}],
    }


def test_the_eye_save_preserves_external_level_modifications(tmp_path):
    """
    Simulate scenario where LevelEditor modifies environment props and deletes an event,
    and TheEye subsequently saves dialogue. TheEye MUST NOT overwrite the environment
    props or resurrect deleted events!
    """
    level_path = str(tmp_path / "level_1.json")
    story_path = str(tmp_path / "storyline_config.json")

    init_data = _create_sample_level_data()
    with open(level_path, "w", encoding="utf-8") as f:
        json.dump(init_data, f, indent=4)
    with open(story_path, "w", encoding="utf-8") as f:
        json.dump({"boss_dialogue": {}, "relics": {}}, f, indent=4)

    # 1. Initialize TheEye
    eye_mgr = TheEyePerceptionManager(level_path=level_path, storyline_path=story_path)

    # 2. Simulate external modification by LevelEditor while TheEye is running:
    # LevelEditor deletes event 14 and adds a second prop
    with open(level_path, "r", encoding="utf-8") as f:
        disk_data = json.load(f)
    disk_data["world_events"] = [e for e in disk_data["world_events"] if e.get("id") != 14]
    disk_data["environment"]["props"].append({
        "texture_path": "assets/graphics/prop2.png",
        "pos_x": 800.0,
        "pos_y": 520.0,
        "width": 32,
        "height": 32,
        "layer_index": 6,
        "in_front": False,
    })
    with open(level_path, "w", encoding="utf-8") as f:
        json.dump(disk_data, f, indent=4)

    # 3. In TheEye, update conversation on the magic book (id 10)
    book_node = eye_mgr.get_node_by_id("node_01_grimoire")
    assert book_node is not None
    book_node.conversations["primary"] = "Updated by The Eye Perception Plugin!"

    # 4. Save perception
    success, msg = eye_mgr.save_perception()
    assert success is True

    # 5. Verify disk integrity
    with open(level_path, "r", encoding="utf-8") as f:
        final_disk = json.load(f)

    # Deleted event 14 MUST NOT be resurrected!
    event_ids = [e.get("id") for e in final_disk["world_events"]]
    assert 14 not in event_ids
    assert 10 in event_ids

    # Dialogue updated by TheEye MUST be preserved!
    book_ev = next(e for e in final_disk["world_events"] if e.get("id") == 10)
    assert book_ev["params"]["text"] == "Updated by The Eye Perception Plugin!"

    # External props added by LevelEditor MUST be preserved!
    assert len(final_disk["environment"]["props"]) == 2
    assert final_disk["environment"]["props"][1]["texture_path"] == "assets/graphics/prop2.png"


def test_level_editor_commit_preserves_wave_editor_spawn_zones(tmp_path):
    """
    Verify LevelEditor commit preserves spawn_zones and other non-owned keys
    written to the level JSON by WaveEditor.
    """
    import pygame as pg
    if not pg.get_init():
        pg.init()

    from level_editor import App

    level_path = str(tmp_path / "level_test.json")
    init_data = _create_sample_level_data()
    with open(level_path, "w", encoding="utf-8") as f:
        json.dump(init_data, f, indent=4)

    # Instantiate App in headless mode
    surf = pg.Surface((1280, 720))
    app = App.__new__(App)
    app.surf = surf
    app.level_files = [level_path]
    app.active_idx = 0
    app.level_data = copy.deepcopy(init_data)
    app.level_backup = copy.deepcopy(init_data)
    app.pending = copy.deepcopy(init_data["world_events"])
    app.reg_del = set()
    app.modal = None

    # Simulate WaveEditor modifying spawn_zones on disk before LevelEditor commits
    with open(level_path, "r", encoding="utf-8") as f:
        disk_data = json.load(f)
    disk_data["spawn_zones"].append({
        "id": "zone_wave_custom",
        "min_dist": 6000,
        "max_dist": 8000,
        "types": ["dark_ronin"],
    })
    with open(level_path, "w", encoding="utf-8") as f:
        json.dump(disk_data, f, indent=4)

    # LevelEditor adds an event in-memory and commits
    app.pending.append({
        "id": 99,
        "distance": 5000,
        "type": "npc",
        "params": {"title": "New Event from Editor", "npc_type": "generic"},
    })
    app.commit()

    # Verify disk level has BOTH the new event AND the preserved spawn_zones
    with open(level_path, "r", encoding="utf-8") as f:
        saved = json.load(f)

    event_ids = [e.get("id") for e in saved["world_events"]]
    assert 99 in event_ids

    zone_ids = [z.get("id") for z in saved["spawn_zones"]]
    assert "zone_wave_custom" in zone_ids
    assert len(saved["spawn_zones"]) == 3


def test_wave_editor_commit_preserves_world_events_and_props(tmp_path):
    """
    Verify WaveEditor commit preserves world_events, environment, and other
    keys modified by LevelEditor.
    """
    from wave_editor import WaveEditorApp

    level_path = str(tmp_path / "level_wave.json")
    init_data = _create_sample_level_data()
    with open(level_path, "w", encoding="utf-8") as f:
        json.dump(init_data, f, indent=4)

    app = WaveEditorApp.__new__(WaveEditorApp)
    app.level_files = [level_path]
    app.active_idx = 0
    app.level_data = copy.deepcopy(init_data)
    app.level_backup = copy.deepcopy(init_data)
    app.pending = copy.deepcopy(init_data["spawn_zones"])
    app.modal = None

    # Simulate LevelEditor updating environment on disk
    with open(level_path, "r", encoding="utf-8") as f:
        disk_data = json.load(f)
    disk_data["environment"]["ground_y"] = 606
    disk_data["environment"]["props"][0]["scale"] = 2.5
    with open(level_path, "w", encoding="utf-8") as f:
        json.dump(disk_data, f, indent=4)

    # WaveEditor modifies spawn_zones and commits
    app.pending.append({
        "id": "zone_3",
        "min_dist": 9000,
        "max_dist": 12000,
        "types": ["boss_wizard"],
    })
    app.commit()

    with open(level_path, "r", encoding="utf-8") as f:
        saved = json.load(f)

    # WaveEditor's spawn zone must be saved
    zone_ids = [z.get("id") for z in saved["spawn_zones"]]
    assert "zone_3" in zone_ids

    # LevelEditor's ground_y and prop scale must be intact!
    assert saved["environment"]["ground_y"] == 606
    assert saved["environment"]["props"][0]["scale"] == 2.5
    assert len(saved["world_events"]) == 2


def test_atomic_save_never_creates_empty_backups_and_prunes(tmp_path):
    """
    Verify that _save_with_backup never writes 0-byte corrupt backup files
    and prunes backups to keep at most 5 recent non-empty backups.
    """
    target_file = str(tmp_path / "config.json")
    with open(target_file, "w", encoding="utf-8") as f:
        json.dump({"step": 0}, f)

    story_file = str(tmp_path / "story.json")
    with open(story_file, "w", encoding="utf-8") as f:
        json.dump({}, f)

    mgr = TheEyePerceptionManager(level_path=target_file, storyline_path=story_file)

    # Save 8 times
    for i in range(1, 9):
        mgr._save_with_backup(target_file, {"step": i})

    # Verify target file has the latest step
    with open(target_file, "r", encoding="utf-8") as f:
        saved = json.load(f)
    assert saved["step"] == 8

    # Verify backup files: no 0-byte files, and count pruned to <= 5
    backups = [f for f in os.listdir(tmp_path) if f.startswith("config.json.backup_")]
    assert len(backups) <= 5
    for b in backups:
        bpath = str(tmp_path / b)
        assert os.path.getsize(bpath) > 0, f"Corrupt 0-byte backup found: {b}"


def test_rollback_isolation_does_not_clobber_disk(tmp_path):
    """
    Verify that invoking rollback() in LevelEditor reverts in-memory edits to the
    last commit checkpoint and NEVER prematurely writes to or clobbers the disk file.
    """
    import pygame as pg
    if not pg.get_init():
        pg.init()

    from level_editor import App

    level_path = str(tmp_path / "rollback_test.json")
    init_data = _create_sample_level_data()
    with open(level_path, "w", encoding="utf-8") as f:
        json.dump(init_data, f, indent=4)

    surf = pg.Surface((1280, 720))
    app = App.__new__(App)
    app.surf = surf
    app.level_files = [level_path]
    app.active_idx = 0
    app.level_data = copy.deepcopy(init_data)
    app.level_backup = copy.deepcopy(init_data)
    app.pending = copy.deepcopy(init_data["world_events"])
    app.reg_del = set()
    app.modal = None

    # Delete all pending events in-memory (uncommitted)
    app.pending.clear()
    assert len(app.pending) == 0

    # Trigger rollback (simulates user clicking '↩ Reset')
    app.rollback()

    # In-memory events are restored
    assert len(app.pending) == len(init_data["world_events"])

    # Disk file remains untouched
    with open(level_path, "r", encoding="utf-8") as f:
        disk_content = json.load(f)
    assert len(disk_content["world_events"]) == len(init_data["world_events"])


def test_consecutive_multi_plugin_interleaved_saves(tmp_path):
    """
    Full lifecycle test simulating interleaved workflows:
    1. LevelEditor loads level and edits props
    2. WaveEditor loads level and updates spawn zones -> commits
    3. TheEye loads level and edits dialogue -> saves
    4. LevelEditor commits its props
    Verify that ALL THREE plugins' contributions are preserved in the main JSON!
    """
    level_path = str(tmp_path / "lifecycle_level.json")
    story_path = str(tmp_path / "lifecycle_story.json")

    init_data = _create_sample_level_data()
    with open(level_path, "w", encoding="utf-8") as f:
        json.dump(init_data, f, indent=4)
    with open(story_path, "w", encoding="utf-8") as f:
        json.dump({"boss_dialogue": {}, "relics": {}}, f, indent=4)

    import pygame as pg
    if not pg.get_init():
        pg.init()
    from level_editor import App
    from wave_editor import WaveEditorApp

    # Step 1: LevelEditor loads level
    lvl_app = App.__new__(App)
    lvl_app.surf = pg.Surface((1280, 720))
    lvl_app.level_files = [level_path]
    lvl_app.active_idx = 0
    lvl_app.level_data = copy.deepcopy(init_data)
    lvl_app.level_backup = copy.deepcopy(init_data)
    lvl_app.pending = copy.deepcopy(init_data["world_events"])
    lvl_app.reg_del = set()
    lvl_app.modal = None
    # User edits prop
    lvl_app.level_data["environment"]["ground_y"] = 620

    # Step 2: WaveEditor updates spawn zones and commits
    wave_app = WaveEditorApp.__new__(WaveEditorApp)
    wave_app.level_files = [level_path]
    wave_app.active_idx = 0
    wave_app.load(0)
    wave_app.pending.append({
        "id": "zone_wave_interleaved",
        "min_dist": 15000,
        "max_dist": 18000,
        "types": ["boss_wizard"],
    })
    wave_app.commit()

    # Step 3: TheEye updates dialogue and saves
    eye_mgr = TheEyePerceptionManager(level_path=level_path, storyline_path=story_path)
    book_node = eye_mgr.get_node_by_id("node_01_grimoire")
    assert book_node is not None
    book_node.conversations["primary"] = "Interleaved TheEye dialogue update!"
    eye_mgr.save_perception()

    # Step 4: LevelEditor commits its props and events
    lvl_app.commit()

    # Final Verification: ALL modifications must be present in the main JSON!
    with open(level_path, "r", encoding="utf-8") as f:
        final_level = json.load(f)

    # 1. LevelEditor ground_y change is present
    assert final_level["environment"]["ground_y"] == 620

    # 2. WaveEditor spawn zone is present
    wave_zone_ids = [z["id"] for z in final_level["spawn_zones"]]
    assert "zone_wave_interleaved" in wave_zone_ids

    # 3. TheEye dialogue update is present
    book_ev = next(e for e in final_level["world_events"] if e.get("id") == 10)
    assert book_ev["params"]["text"] == "Interleaved TheEye dialogue update!"

