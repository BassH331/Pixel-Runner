"""
tests/test_editor_plugins_adversarial_m2.py

Adversarial Verification Suite for Milestone 2:
Empirically challenges editor plugins atomic save patterns:
1. `boss_editor.py`: Saving boss and minion configs to temporary paths,
   validating atomic_write_json usage, valid JSON, and backup cap <= 5.
2. `level_editor.py`: Testing commit() path, atomic replacement, non-empty backups,
   and 3-way merge retention of spawn_zones/props.
3. `wave_editor.py`: Testing simulate() immutability on production level file,
   clean temp file disposal, and atomic commit() workflow.
4. `player_editor.py`: Testing request_save_config() with custom external keys,
   validating external key preservation, backup pruning to 5, and detecting
   the exit-hook clobber vulnerability in lines 1968-1975.
"""

import os
import sys
import copy
import json
import glob
import time
import pytest
from unittest.mock import MagicMock, patch

import pygame as pg

# Ensure headless pygame
if not pg.get_init():
    os.environ["SDL_VIDEODRIVER"] = "dummy"
    pg.init()


def _create_sample_level_data():
    return {
        "level_name": "Adversarial Realm - M2 Challenge",
        "level_end_distance": 36000,
        "spawn_zones": [
            {"id": "zone_1", "min_dist": 0, "max_dist": 2000, "types": ["bat"]},
            {"id": "zone_2", "min_dist": 2000, "max_dist": 5000, "types": ["skeleton"]},
        ],
        "world_events": [
            {
                "id": 10,
                "distance": 1013,
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
        "custom_realm_metadata": {"difficulty_tier": "adversarial", "seed": 424242},
    }


# ==============================================================================
# 1. BOSS EDITOR ADVERSARIAL CHALLENGE
# ==============================================================================

def test_adversarial_boss_editor_atomic_save_and_backup_cap(tmp_path):
    """
    Challenge boss_editor.py:
    - Save boss and minion configs to isolated temporary paths.
    - Verify atomic_write_json produces valid JSON.
    - Verify minion config is synced with skeleton parameters.
    - Repeatedly save (8 times) and verify backups never exceed 5.
    - Verify all backups are non-empty (>0 bytes) and valid JSON.
    """
    from boss_editor import BossEditorApp, Slider

    boss_config_path = str(tmp_path / "boss_skeleton_config.json")
    minion_config_path = str(tmp_path / "enemy_skeleton_minion_config.json")

    init_boss = {
        "max_health": 100.0,
        "speed": 3.0,
        "spidey_sense": 0.5,
        "teleport_dist_min": 150,
        "teleport_dist_max": 400,
        "teleport_cooldown": 4.0,
        "teleport_reaction_delay": 0.3,
        "external_boss_lore": "Ancient Skeletal Monarch",
    }
    init_minion = {
        "max_health": 30.0,
        "speed": 2.0,
        "spidey_sense": 0.1,
        "teleport_dist_min": 50,
        "teleport_dist_max": 200,
        "teleport_cooldown": 8.0,
        "teleport_reaction_delay": 0.8,
        "minion_squad_id": "alpha_pack",
    }

    with open(boss_config_path, "w", encoding="utf-8") as f:
        json.dump(init_boss, f, indent=2)
    with open(minion_config_path, "w", encoding="utf-8") as f:
        json.dump(init_minion, f, indent=2)

    app = BossEditorApp.__new__(BossEditorApp)
    app.selected_boss = "skeleton"
    app.bosses = {
        "skeleton": {
            "class": MagicMock(),
            "schema": {
                "config_file": boss_config_path,
                "defaults": copy.deepcopy(init_boss),
            },
        }
    }
    app.boss_configs = {"skeleton": copy.deepcopy(init_boss)}
    app.sliders = {
        "speed": Slider("speed", "Speed", 0, 0, 100, 1.0, 10.0, 5.5, True),
        "spidey_sense": Slider("spidey_sense", "Spidey", 0, 0, 100, 0.0, 1.0, 0.95, True),
        "teleport_dist_min": Slider("teleport_dist_min", "TeleMin", 0, 0, 100, 50, 500, 250, False),
        "teleport_dist_max": Slider("teleport_dist_max", "TeleMax", 0, 0, 100, 50, 500, 450, False),
    }

    app.minion_config_path = minion_config_path

    # Mock cache services in boss_editor
    with patch("boss_editor.LocalCache", create=True), \
         patch("boss_editor.ConfigClient", create=True):

        # Save 8 times to challenge backup rotation cap (max 5)
        # Use patch to simulate different timestamps so backups have distinct names
        for step in range(1, 9):
            app.sliders["speed"].val = 5.0 + (step * 0.1)
            fake_ts = 1700000000 + (step * 10)
            with patch("time.time", return_value=fake_ts):
                app.confirm_save_config()

    # 1. Verify boss config validity and updated values
    assert os.path.exists(boss_config_path)
    with open(boss_config_path, "r", encoding="utf-8") as f:
        saved_boss = json.load(f)
    assert saved_boss["speed"] == pytest.approx(5.8, 0.01)
    assert saved_boss["spidey_sense"] == 0.95
    assert saved_boss["teleport_dist_min"] == 250
    # Verify unowned external keys preserved in boss config
    assert saved_boss.get("external_boss_lore") == "Ancient Skeletal Monarch"

    # 2. Verify minion config validity and synchronized keys
    assert os.path.exists(minion_config_path)
    with open(minion_config_path, "r", encoding="utf-8") as f:
        saved_minion = json.load(f)
    assert saved_minion["spidey_sense"] == 0.95
    assert saved_minion["teleport_dist_min"] == 250
    assert saved_minion["speed"] == pytest.approx(5.8, 0.01)
    assert saved_minion.get("minion_squad_id") == "alpha_pack"

    # 3. Verify backup count cap <= 5 for boss config
    boss_backups = glob.glob(f"{boss_config_path}.backup_*")
    assert 0 < len(boss_backups) <= 5, f"Boss backups count {len(boss_backups)} exceeded 5!"
    for b in boss_backups:
        assert os.path.getsize(b) > 0, f"Empty boss backup: {b}"
        with open(b, "r", encoding="utf-8") as bf:
            b_data = json.load(bf)
            assert isinstance(b_data, dict)


# ==============================================================================
# 2. LEVEL EDITOR ADVERSARIAL CHALLENGE
# ==============================================================================

def test_adversarial_level_editor_commit_atomic_merge_and_backups(tmp_path):
    """
    Challenge level_editor.py commit() path:
    - Verify atomic transactional file replacement.
    - Verify 3-way merge preserves spawn_zones and props added by external plugins.
    - Verify non-empty backups are created and pruned to <= 5 across multiple commits.
    """
    from level_editor import App

    level_path = str(tmp_path / "adversarial_level.json")
    init_data = _create_sample_level_data()
    with open(level_path, "w", encoding="utf-8") as f:
        json.dump(init_data, f, indent=4)

    app = App.__new__(App)
    app.surf = pg.Surface((1280, 720))
    app.level_files = [level_path]
    app.active_idx = 0
    app.level_data = copy.deepcopy(init_data)
    app.level_backup = copy.deepcopy(init_data)
    app.pending = copy.deepcopy(init_data["world_events"])
    app.reg_del = set()
    app.modal = None

    # Step A: External plugin modifies disk concurrently:
    # 1. Adds a new spawn zone ("zone_external_3")
    # 2. Adds dialogue text and combat taunts to event 10
    # 3. Adds an external prop
    with open(level_path, "r", encoding="utf-8") as f:
        disk_data = json.load(f)
    disk_data["spawn_zones"].append({
        "id": "zone_external_3",
        "min_dist": 6000,
        "max_dist": 9000,
        "types": ["dark_ronin"],
    })
    for ev in disk_data["world_events"]:
        if ev.get("id") == 10:
            ev["params"]["text"] = "External Plugin Dialogue Update"
            ev["params"]["combat_taunts"] = ["Face the pages!", "Knowledge burns!"]
            ev["params"]["the_eye_custom_meta"] = {"reviewed": True}
    disk_data["environment"]["props"].append({
        "texture_path": "assets/graphics/prop_adversarial.png",
        "pos_x": 950.0,
        "pos_y": 520.0,
        "width": 32,
        "height": 32,
        "layer_index": 5,
        "in_front": False,
    })
    with open(level_path, "w", encoding="utf-8") as f:
        json.dump(disk_data, f, indent=4)

    # Step B: LevelEditor makes an in-memory modification:
    # Adds a new world event without touching event 10's text
    app.pending.append({
        "id": 88,
        "distance": 4500,
        "type": "npc",
        "params": {"title": "Challenger Gatekeeper", "npc_type": "generic"},
    })

    # Step C: Commit 7 times with timestamp offsets to verify atomic writes & backup cap
    with patch("level_editor.HitboxRegistry.commit_transaction"):
        for step in range(1, 8):
            fake_ts = 1700000000 + (step * 20)
            with patch("time.time", return_value=fake_ts):
                app.commit()

    # Step D: Verify disk integrity
    with open(level_path, "r", encoding="utf-8") as f:
        committed = json.load(f)

    # 1. Newly added event 88 must exist
    event_ids = [e.get("id") for e in committed["world_events"]]
    assert 88 in event_ids

    # 2. Concurrent spawn_zones must be completely retained!
    spawn_zone_ids = [z.get("id") for z in committed["spawn_zones"]]
    assert "zone_external_3" in spawn_zone_ids
    assert len(committed["spawn_zones"]) == 3

    # 3. 3-way merge must retain external text, taunts, and custom extra keys on event 10!
    book_event = next(e for e in committed["world_events"] if e.get("id") == 10)
    assert book_event["params"]["text"] == "External Plugin Dialogue Update"
    assert "Knowledge burns!" in book_event["params"]["combat_taunts"]
    assert book_event["params"].get("the_eye_custom_meta") == {"reviewed": True}

    # 4. Custom realm metadata must remain intact!
    assert committed.get("custom_realm_metadata") == {"difficulty_tier": "adversarial", "seed": 424242}

    # 5. Backups must be non-empty and capped at <= 5
    backups = glob.glob(f"{level_path}.backup_*")
    assert 0 < len(backups) <= 5, f"Backup count {len(backups)} exceeded 5!"
    for b in backups:
        assert os.path.getsize(b) > 0


# ==============================================================================
# 3. WAVE EDITOR ADVERSARIAL CHALLENGE
# ==============================================================================

def test_adversarial_wave_editor_simulation_isolation_and_atomic_commit(tmp_path):
    """
    Challenge wave_editor.py:
    - Test simulate(): MUST NOT modify, corrupt, or truncate the production level JSON file.
    - Test simulate(): Temporary simulation file must be cleaned up even if game crashes/cancels.
    - Test commit(): Must atomically save spawn zones while preserving world events and environment.
    """
    from wave_editor import WaveEditorApp, Slider

    level_path = str(tmp_path / "prod_level.json")
    init_data = _create_sample_level_data()
    with open(level_path, "w", encoding="utf-8") as f:
        json.dump(init_data, f, indent=4)

    # Record initial file state
    initial_bytes = open(level_path, "rb").read()
    initial_mtime = os.path.getmtime(level_path)

    app = WaveEditorApp.__new__(WaveEditorApp)
    app.surf = pg.Surface((1280, 720))
    app.level_files = [level_path]
    app.active_idx = 0
    app.level_data = copy.deepcopy(init_data)
    app.level_backup = copy.deepcopy(init_data)
    app.pending = copy.deepcopy(init_data["spawn_zones"])
    app.modal = None
    app.s3_mode = "create"
    app.s3_idx = -1
    app.browser = MagicMock(selected=None)
    app.bmap = MagicMock(mapping={})
    app.tf = MagicMock()
    app.tf.render.return_value = pg.Surface((100, 20))

    # Setup s3_ui sliders for a simulation zone
    app.s3_ui = {
        "min": Slider("min", 0, 0, 100, 0, 10000, 500),
        "max": Slider("max", 0, 0, 100, 0, 10000, 1500),
        "count": Slider("count", 0, 0, 100, 1, 20, 5),
        "delay": Slider("delay", 0, 0, 100, 500, 10000, 3000),
        "required_kills": Slider("req", 0, 0, 100, 0, 50, 0),
        "tier": "minion",
    }

    # Simulate 1: Launch simulation where subprocess completes normally
    sim_captured_files = []
    def mock_subprocess_run(cmd, **kwargs):
        # Extract --level argument passed to main.py
        lvl_arg_idx = cmd.index("--level") + 1
        sim_file = cmd[lvl_arg_idx]
        sim_captured_files.append(sim_file)
        # Verify sim_file is a temporary simulation file, NOT the production level_path!
        assert sim_file != level_path, "CRITICAL: Simulation ran against production level file!"
        assert f"prod_level.json.sim_{os.getpid()}.json" in sim_file
        assert os.path.exists(sim_file), "Temporary simulation file was not created on disk!"
        # Verify temporary file has uncommitted simulation zone
        with open(sim_file, "r", encoding="utf-8") as sf:
            sim_json = json.load(sf)
        assert len(sim_json["spawn_zones"]) == len(init_data["spawn_zones"]) + 1

    with patch("subprocess.run", side_effect=mock_subprocess_run):
        app.simulate()

    # Verify production level file was COMPLETELY UNTOUCHED by simulate()!
    current_bytes = open(level_path, "rb").read()
    assert current_bytes == initial_bytes, "Production level file was modified during simulate()!"
    assert os.path.getmtime(level_path) == initial_mtime

    # Verify temporary simulation file was cleaned up
    for sf in sim_captured_files:
        assert not os.path.exists(sf), f"Temporary simulation file {sf} was not deleted!"

    # Simulate 2: Launch simulation where subprocess raises an unhandled error
    def mock_subprocess_crash(cmd, **kwargs):
        raise RuntimeError("Simulated crash in game subprocess")

    with patch("subprocess.run", side_effect=mock_subprocess_crash):
        app.simulate()

    # Verify production file still untouched and no lingering sim files
    assert open(level_path, "rb").read() == initial_bytes
    lingering_sim = glob.glob(f"{level_path}.sim_*")
    assert len(lingering_sim) == 0, f"Lingering simulation files found: {lingering_sim}"

    # Now test WaveEditor commit():
    app.pending.append({
        "id": "zone_committed_wave",
        "min_dist": 8000,
        "max_dist": 10000,
        "types": ["boss_wizard"],
    })
    app.commit()

    # Verify commit output
    with open(level_path, "r", encoding="utf-8") as f:
        committed = json.load(f)
    zone_ids = [z["id"] for z in committed["spawn_zones"]]
    assert "zone_committed_wave" in zone_ids
    # Existing world events and environment must be preserved!
    assert len(committed["world_events"]) == len(init_data["world_events"])
    assert committed["environment"]["ground_y"] == 551


# ==============================================================================
# 4. PLAYER EDITOR ADVERSARIAL CHALLENGE
# ==============================================================================

def test_adversarial_player_editor_external_keys_and_backup_rotation(tmp_path):
    """
    Challenge player_editor.py:
    - Save player config with custom external keys (physics, narrative, metadata).
    - Verify request_save_config() preserves all custom external keys.
    - Verify backup pruning strictly maintains <= 5 non-empty backups.
    - Verify scan_backups() accurately discovers atomic backups.
    """
    from player_editor import PlayerEditorApp

    cfg_dir = str(tmp_path / "game_data")
    os.makedirs(cfg_dir, exist_ok=True)
    cfg_path = os.path.join(cfg_dir, "player_config.json")

    init_player_data = {
        "states": {
            "IDLE": {"animation_speed": 0.2, "loops": True, "interruptible": True},
            "RUN": {"animation_speed": 0.15, "loops": True, "interruptible": True},
        },
        "attacks": {
            "THRUST": {"damage": 25.0, "knockback": 5.0},
        },
        # External keys not owned by PlayerEditor
        "external_combat_meta": {"combo_multiplier": 1.5, "version": "2.4"},
        "controller_deadzones": {"left_stick": 0.15, "right_stick": 0.20},
        "character_lore": "Zulfiqar - The Crescent Blade of Gideon",
    }

    with open(cfg_path, "w", encoding="utf-8") as f:
        json.dump(init_player_data, f, indent=2)

    app = PlayerEditorApp.__new__(PlayerEditorApp)
    app.config_dir = cfg_dir
    app.config_path = cfg_path
    app.mode = "MENU"
    app.config = copy.deepcopy(init_player_data["states"])
    app.attack_config = copy.deepcopy(init_player_data["attacks"])
    app.backups = []
    app.selected_backup_index = -1
    app.show_toast = MagicMock()

    # Modify an in-memory state parameter
    app.config["IDLE"]["animation_speed"] = 0.35

    # Commit 8 times with timestamp offsets to challenge backup rotation cap (max 5)
    for step in range(1, 9):
        fake_ts = 1700000000 + (step * 30)
        with patch("time.time", return_value=fake_ts):
            app.request_save_config()

    # 1. Verify target file contains updated state
    with open(cfg_path, "r", encoding="utf-8") as f:
        saved = json.load(f)
    assert saved["states"]["IDLE"]["animation_speed"] == 0.35

    # 2. Verify all external keys are 100% retained!
    assert saved.get("external_combat_meta") == {"combo_multiplier": 1.5, "version": "2.4"}
    assert saved.get("controller_deadzones") == {"left_stick": 0.15, "right_stick": 0.20}
    assert saved.get("character_lore") == "Zulfiqar - The Crescent Blade of Gideon"

    # 3. Verify backup count cap <= 5
    backups = glob.glob(f"{cfg_path}.backup_*")
    assert 0 < len(backups) <= 5, f"Player config backups count {len(backups)} exceeded 5!"
    for b in backups:
        assert os.path.getsize(b) > 0

    # 4. Verify scan_backups() discovered the backups
    app.scan_backups()
    assert len(app.backups) == len(backups)


# ==============================================================================
# 5. ADVERSARIAL VULNERABILITY AUDIT: PLAYER EDITOR EXIT HOOK
# ==============================================================================

def test_adversarial_player_editor_exit_hook_audit(tmp_path):
    """
    Forensic Adversarial Audit:
    Inspect player_editor.py lines 1968-1976.
    Verify whether the application exit hook performs raw open("w") without
    external key preservation or atomic save.
    """
    with open("player_editor.py", "r", encoding="utf-8") as f:
        source_code = f.read()

    # Locate the exit save block in run()
    assert "def run(self):" in source_code
    
    # Check if lines 1968-1976 contain raw non-atomic write
    has_raw_exit_write = 'with open(self.config_path, "w") as f:' in source_code
    assert has_raw_exit_write is False, "Exit hook must not contain raw unbuffered write"
    assert "self.request_save_config()" in source_code, "Exit hook must invoke self.request_save_config()"

    # Demonstrate the blast radius:
    # If a developer/user triggers the exit save block directly instead of request_save_config(),
    # external keys would be clobbered.
    target_path = str(tmp_path / "clobber_test.json")
    original_data = {
        "states": {"IDLE": {"animation_speed": 0.2}},
        "attacks": {},
        "preserved_key": "MUST_NOT_BE_LOST",
    }
    with open(target_path, "w", encoding="utf-8") as f:
        json.dump(original_data, f)

    # Simulated legacy exit write:
    combined_data = {
        "states": {"IDLE": {"animation_speed": 0.25}},
        "attacks": {},
    }
    # Raw write clobbers "preserved_key"
    with open(target_path, "w") as f:
        json.dump(combined_data, f, indent=2)

    with open(target_path, "r", encoding="utf-8") as f:
        clobbered_data = json.load(f)
    assert "preserved_key" not in clobbered_data, "Demonstrated: raw exit write drops external keys"
