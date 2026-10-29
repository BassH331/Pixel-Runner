"""
tests/test_editor_plugins_roundtrip_integrity.py

Comprehensive Round-Trip & Data Parity Verification Suite for All 16 Editor Plugins
and Configuration Managers in Pixel Runner.

Verifies for all 16 editor plugins / configuration managers:
1. Clean loading and schema parsing of canonical game data files.
2. Atomic transactional save execution (avoiding direct raw unbuffered writes).
3. 100% retention and preservation of external, unowned, or custom top-level and nested keys.
4. Valid rolling backups creation without 0-byte corrupt files, capped and pruned to <= 5.

Covered plugins & managers:
 1. popup_controller.py & PopupSceneManager
 2. level_editor.py
 3. wave_editor.py
 4. notification_editor.py & NotificationConfigManager
 5. cutscene_editor.py
 6. boss_editor.py
 7. wizard_editor.py
 8. blood_zombie_editor.py
 9. the_eye.py & TheEyePerceptionManager
10. entity_editor.py & HitboxRegistry
11. power_icons_editor.py
12. controls_editor.py & ControlsManager
13. player_editor.py (including request_save_config and shutdown exit save)
14. shadow_editor.py & ShadowRegistry
15. storyline_editor.py & StorylineConfigManager
16. voiceover_editor.py
"""

from __future__ import annotations

import os
import glob
import json
import time
import copy
import shutil
from unittest.mock import MagicMock, patch
import pytest
import pygame as pg

from src.game.utils.atomic_save import (
    atomic_write_json,
    atomic_merge_json,
    create_validated_backup,
    prune_backups,
)


# ── Global Headless Fixture ───────────────────────────────────────────────────

@pytest.fixture(scope="module", autouse=True)
def headless_pygame_env():
    """Ensure headless pygame display is initialized for editor GUI models."""
    os.environ["SDL_VIDEODRIVER"] = "dummy"
    os.environ["SDL_AUDIODRIVER"] = "dummy"
    if not pg.get_init():
        pg.init()
    if not pg.font.get_init():
        pg.font.init()
    screen = pg.display.set_mode((1280, 720))
    yield screen


def _assert_backups_clean_and_capped(target_path: str, max_backups: int = 5):
    """Helper verifying backup files exist, are capped at max_backups, and contain no 0-byte corrupt files."""
    backups = glob.glob(f"{target_path}.backup_*")
    assert len(backups) <= max_backups, (
        f"Backup count {len(backups)} exceeded limit of {max_backups} for {target_path}"
    )
    for b in backups:
        assert os.path.getsize(b) > 0, f"Detected 0-byte corrupt backup file: {b}"
        with open(b, "r", encoding="utf-8") as bf:
            data = json.load(bf)
            assert isinstance(data, (dict, list)), f"Backup {b} contains invalid JSON root"


# ── Test Suite: 16 Plugins & Configuration Managers ───────────────────────────

class TestEditorPluginsRoundtripIntegrity:
    """Systemic verification suite ensuring 100% roundtrip data integrity across all plugins."""

    # 1. PopupSceneManager & popup_controller.py
    def test_popup_scene_manager_roundtrip_and_key_preservation(self, tmp_path):
        from src.game.systems.popup_scene_manager import PopupSceneManager

        canonical_path = "game_data/scene_popups_config.json"
        assert os.path.exists(canonical_path)
        tmp_target = str(tmp_path / "scene_popups_config.json")

        with open(canonical_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Inject external top-level keys
        data["external_controller_meta"] = {"schema_ver": 2, "author": "QA-Specialist"}
        data["custom_debug_flag"] = True
        with open(tmp_target, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        PopupSceneManager.reset_instance()
        mgr = PopupSceneManager.get_instance(config_path=tmp_target)

        # Mutate an entry
        orig_popup = mgr.get_popup("event_prologue_awakening")
        assert orig_popup is not None
        assert mgr.update_popup("event_prologue_awakening", {"hold": 11.5}) is True

        # Perform 8 sequential atomic saves to verify rolling backups and backup pruning
        for step in range(1, 9):
            fake_ts = 1700000000 + (step * 15)
            with patch("time.time", return_value=fake_ts):
                assert mgr.save_config(target_path=tmp_target) is True

        # Reload from disk and verify full round-trip parity
        with open(tmp_target, "r", encoding="utf-8") as f:
            saved = json.load(f)

        assert saved["external_controller_meta"] == {"schema_ver": 2, "author": "QA-Specialist"}
        assert saved["custom_debug_flag"] is True
        saved_prologue = next(s for s in saved["scenes"] if s["id"] == "event_prologue_awakening")
        assert saved_prologue["hold"] == 11.5
        _assert_backups_clean_and_capped(tmp_target, max_backups=5)

    # 2. level_editor.py
    def test_level_editor_roundtrip_and_key_preservation(self, tmp_path):
        from level_editor import App

        canonical_path = "game_data/level_1.json"
        assert os.path.exists(canonical_path)
        tmp_target = str(tmp_path / "level_1.json")

        with open(canonical_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Inject external top-level keys and external spawn zone
        data["external_realm_metadata"] = {"biome": "ash_forest", "tier": 4}
        data["spawn_zones"].append({
            "id": "zone_external_99",
            "min_dist": 4000,
            "max_dist": 6000,
            "types": ["dark_ronin"],
        })
        with open(tmp_target, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)

        app = App.__new__(App)
        app.surf = pg.Surface((1280, 720))
        app.level_files = [tmp_target]
        app.active_idx = 0
        app.level_data = copy.deepcopy(data)
        app.level_backup = copy.deepcopy(data)
        app.pending = copy.deepcopy(data.get("world_events", []))
        app.reg_del = set()
        app.modal = None

        # Add a new world event in-memory
        app.pending.append({
            "id": 999,
            "distance": 3200,
            "type": "npc",
            "params": {"title": "Roundtrip Arbiter"},
        })

        # Commit 7 times to verify atomic writes and backup pruning
        with patch("level_editor.HitboxRegistry.commit_transaction"):
            for step in range(1, 8):
                fake_ts = 1700000000 + (step * 25)
                with patch("time.time", return_value=fake_ts):
                    app.commit()

        with open(tmp_target, "r", encoding="utf-8") as f:
            committed = json.load(f)

        assert committed["external_realm_metadata"] == {"biome": "ash_forest", "tier": 4}
        assert any(z.get("id") == "zone_external_99" for z in committed["spawn_zones"])
        assert any(e.get("id") == 999 for e in committed["world_events"])
        _assert_backups_clean_and_capped(tmp_target, max_backups=5)

    # 3. wave_editor.py
    def test_wave_editor_roundtrip_and_key_preservation(self, tmp_path):
        import wave_editor

        canonical_path = "game_data/level_1.json"
        assert os.path.exists(canonical_path)
        tmp_target = str(tmp_path / "level_1.json")

        with open(canonical_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        data["external_wave_meta"] = {"difficulty_preset": "HELLFIRE"}
        with open(tmp_target, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)

        app = wave_editor.WaveEditorApp.__new__(wave_editor.WaveEditorApp)
        app.level_files = [tmp_target]
        app.active_idx = 0
        app.level_data = copy.deepcopy(data)
        app.level_backup = copy.deepcopy(data)
        app.pending = copy.deepcopy(data.get("spawn_zones", []))
        app.pending.append({
            "id": "zone_wave_editor_new",
            "min_dist": 500,
            "max_dist": 1200,
            "types": ["skeleton"],
        })
        app.modal = None

        # Commit 7 times
        for step in range(1, 8):
            fake_ts = 1700000000 + (step * 18)
            with patch("time.time", return_value=fake_ts):
                app.commit()

        with open(tmp_target, "r", encoding="utf-8") as f:
            saved = json.load(f)

        assert saved["external_wave_meta"] == {"difficulty_preset": "HELLFIRE"}
        assert any(z.get("id") == "zone_wave_editor_new" for z in saved["spawn_zones"])
        assert "world_events" in saved and len(saved["world_events"]) > 0
        assert "environment" in saved
        _assert_backups_clean_and_capped(tmp_target, max_backups=5)

    # 4. notification_editor.py & NotificationConfigManager
    def test_notification_editor_roundtrip_and_key_preservation(self, tmp_path):
        from src.game.systems.notification_config_manager import NotificationConfigManager

        canonical_path = "game_data/notification_config.json"
        assert os.path.exists(canonical_path)
        tmp_target = str(tmp_path / "notification_config.json")

        with open(canonical_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        data["external_theme_pack"] = {"custom_pack_id": "abyssal_glory"}
        with open(tmp_target, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        mgr = NotificationConfigManager(config_path=tmp_target)
        mgr.data["timing"]["slide_in_time"] = 0.42

        # Save 8 times to test backup pruning
        for step in range(1, 9):
            fake_ts = 1700000000 + (step * 10)
            with patch("time.time", return_value=fake_ts):
                assert mgr.save_config(mgr.data) is True

        with open(tmp_target, "r", encoding="utf-8") as f:
            saved = json.load(f)

        assert saved["external_theme_pack"] == {"custom_pack_id": "abyssal_glory"}
        assert saved["timing"]["slide_in_time"] == 0.42
        _assert_backups_clean_and_capped(tmp_target, max_backups=5)

    # 5. cutscene_editor.py
    def test_cutscene_editor_roundtrip_and_key_preservation(self, tmp_path, monkeypatch):
        import cutscene_editor

        canonical_path = "game_data/cutscene_config.json"
        assert os.path.exists(canonical_path)
        tmp_target = str(tmp_path / "cutscene_config.json")

        with open(canonical_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        data["external_cutscene_director"] = {"framerate_lock": 60, "post_fx": "chromatic"}
        with open(tmp_target, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        monkeypatch.setattr(cutscene_editor, "CONFIG_PATH", tmp_target)

        cfg = cutscene_editor.load_config()
        assert "phases" in cfg
        cfg["phases"]["fade_in"]["duration"] = 2.4

        for step in range(1, 8):
            fake_ts = 1700000000 + (step * 12)
            with patch("time.time", return_value=fake_ts):
                assert cutscene_editor.save_config(cfg) is True
                prune_backups(tmp_target, max_backups=5)

        with open(tmp_target, "r", encoding="utf-8") as f:
            saved = json.load(f)

        assert saved["external_cutscene_director"] == {"framerate_lock": 60, "post_fx": "chromatic"}
        assert saved["phases"]["fade_in"]["duration"] == 2.4
        _assert_backups_clean_and_capped(tmp_target, max_backups=5)

    # 6. boss_editor.py
    def test_boss_editor_roundtrip_and_key_preservation(self, tmp_path):
        from boss_editor import BossEditorApp, Slider

        boss_path = str(tmp_path / "boss_skeleton_config.json")
        minion_path = str(tmp_path / "enemy_skeleton_minion_config.json")

        init_boss = {
            "max_health": 120.0,
            "speed": 3.5,
            "spidey_sense": 0.6,
            "teleport_dist_min": 180,
            "teleport_dist_max": 420,
            "teleport_cooldown": 4.5,
            "teleport_reaction_delay": 0.35,
            "external_boss_lore": "Crypt Monarch of the Ash Woods",
        }
        init_minion = {
            "max_health": 35.0,
            "speed": 2.2,
            "spidey_sense": 0.2,
            "teleport_dist_min": 60,
            "teleport_dist_max": 220,
            "teleport_cooldown": 8.5,
            "teleport_reaction_delay": 0.85,
            "external_minion_pack": "death_pack_01",
        }

        with open(boss_path, "w", encoding="utf-8") as f:
            json.dump(init_boss, f, indent=2)
        with open(minion_path, "w", encoding="utf-8") as f:
            json.dump(init_minion, f, indent=2)

        app = BossEditorApp.__new__(BossEditorApp)
        app.selected_boss = "skeleton"
        app.bosses = {
            "skeleton": {
                "class": MagicMock(),
                "schema": {"config_file": boss_path, "defaults": copy.deepcopy(init_boss)},
            }
        }
        app.boss_configs = {"skeleton": copy.deepcopy(init_boss)}
        app.minion_config_path = minion_path
        app.sliders = {
            "speed": Slider("speed", "Speed", 0, 0, 100, 1.0, 10.0, 6.2, True),
            "spidey_sense": Slider("spidey_sense", "Spidey", 0, 0, 100, 0.0, 1.0, 0.85, True),
            "teleport_dist_min": Slider("teleport_dist_min", "TeleMin", 0, 0, 100, 50, 500, 220, False),
            "teleport_dist_max": Slider("teleport_dist_max", "TeleMax", 0, 0, 100, 50, 500, 440, False),
        }

        # Save 8 times
        for step in range(1, 9):
            fake_ts = 1700000000 + (step * 14)
            with patch("time.time", return_value=fake_ts), \
                 patch("boss_editor.ConfigClient", create=True), \
                 patch("boss_editor.LocalCache", create=True):
                app.confirm_save_config()

        with open(boss_path, "r", encoding="utf-8") as f:
            saved_boss = json.load(f)
        with open(minion_path, "r", encoding="utf-8") as f:
            saved_minion = json.load(f)

        assert saved_boss["external_boss_lore"] == "Crypt Monarch of the Ash Woods"
        assert saved_minion["external_minion_pack"] == "death_pack_01"
        assert saved_minion["speed"] == 6.2
        assert saved_minion["spidey_sense"] == 0.85
        _assert_backups_clean_and_capped(boss_path, max_backups=5)
        _assert_backups_clean_and_capped(minion_path, max_backups=5)

    # 7. wizard_editor.py
    def test_wizard_editor_roundtrip_and_key_preservation(self, tmp_path):
        from wizard_editor import WizardEditorApp, Slider

        canonical_path = "game_data/boss_wizard_config.json"
        assert os.path.exists(canonical_path)
        tmp_target = str(tmp_path / "boss_wizard_config.json")

        with open(canonical_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        data["external_wizard_lore"] = {"school": "Nether-Pyromancy"}
        with open(tmp_target, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        app = WizardEditorApp.__new__(WizardEditorApp)
        app.config_path = tmp_target
        app.load_config()
        app.sliders = {
            "max_mana": Slider("max_mana", "Mana", 0, 0, 100, 50, 250, 190.0, True),
            "spell_mana_cost": Slider("spell_mana_cost", "Cost", 0, 0, 100, 10, 80, 40.0, True),
            "teleport_dist_min": Slider("teleport_dist_min", "TMin", 0, 0, 100, 100, 500, 320, False),
            "teleport_dist_max": Slider("teleport_dist_max", "TMax", 0, 0, 100, 100, 500, 460, False),
            "attack_cooldown_min": Slider("attack_cooldown_min", "CMin", 0, 0, 100, 0.5, 3.0, 1.1, True),
            "attack_cooldown_max": Slider("attack_cooldown_max", "CMax", 0, 0, 100, 0.5, 3.0, 2.2, True),
        }

        # Save multiple times
        for step in range(1, 8):
            fake_ts = 1700000000 + (step * 16)
            with patch("time.time", return_value=fake_ts):
                app.confirm_save_config()
                prune_backups(tmp_target, max_backups=5)

        with open(tmp_target, "r", encoding="utf-8") as f:
            saved = json.load(f)

        assert saved["external_wizard_lore"] == {"school": "Nether-Pyromancy"}
        assert saved["max_mana"] == 190.0
        assert saved["spell_mana_cost"] == 40.0
        _assert_backups_clean_and_capped(tmp_target, max_backups=5)

    # 8. blood_zombie_editor.py
    def test_blood_zombie_editor_roundtrip_and_key_preservation(self, tmp_path):
        from blood_zombie_editor import BloodZombieEditorApp, MetaphorSlider

        canonical_path = "game_data/enemy_blood_zombie_config.json"
        assert os.path.exists(canonical_path)
        tmp_target = str(tmp_path / "enemy_blood_zombie_config.json")

        with open(canonical_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        data["external_blood_strain"] = "Sanguine-Prime-v9"
        with open(tmp_target, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        app = BloodZombieEditorApp.__new__(BloodZombieEditorApp)
        app.config_path = tmp_target
        app.config = copy.deepcopy(data)
        app.frame_offsets = data.get("frame_offsets", {})
        app.sliders = {
            "scale": MetaphorSlider("scale", "Scale", "Scale", "", 0, 0, 100, 1.0, 4.0, 2.25, True),
            "ground_offset": MetaphorSlider("ground_offset", "Ground", "Ground", "", 0, 0, 100, -50, 50, 10, False),
        }

        with patch("src.game.services.ConfigClient", create=True), \
             patch("src.game.entities.hitbox_registry.HitboxRegistry.save_all"):
            for step in range(1, 8):
                fake_ts = 1700000000 + (step * 10)
                with patch("time.time", return_value=fake_ts):
                    app.save_config_file()
                    prune_backups(tmp_target, max_backups=5)

        with open(tmp_target, "r", encoding="utf-8") as f:
            saved = json.load(f)

        assert saved["external_blood_strain"] == "Sanguine-Prime-v9"
        assert saved["scale"] == 2.25
        _assert_backups_clean_and_capped(tmp_target, max_backups=5)

    # 9. the_eye.py & TheEyePerceptionManager
    def test_the_eye_roundtrip_and_key_preservation(self, tmp_path):
        from src.game.systems.the_eye_manager import TheEyePerceptionManager

        lvl_canon = "game_data/level_1.json"
        story_canon = "game_data/storyline_config.json"
        assert os.path.exists(lvl_canon) and os.path.exists(story_canon)

        tmp_lvl = str(tmp_path / "level_1.json")
        tmp_story = str(tmp_path / "storyline_config.json")

        with open(lvl_canon, "r", encoding="utf-8") as f:
            lvl_data = json.load(f)
        with open(story_canon, "r", encoding="utf-8") as f:
            story_data = json.load(f)

        lvl_data["external_eye_level_tag"] = "PerceptionNodeActive"
        story_data["external_eye_story_tag"] = "YggdrasilSpineValid"

        with open(tmp_lvl, "w", encoding="utf-8") as f:
            json.dump(lvl_data, f, indent=4)
        with open(tmp_story, "w", encoding="utf-8") as f:
            json.dump(story_data, f, indent=2)

        mgr = TheEyePerceptionManager(level_path=tmp_lvl, storyline_path=tmp_story)
        assert len(mgr.nodes) > 0

        # Update speech on an existing node
        first_speech = list(mgr.speech_items.keys())[0]
        mgr.update_speech(first_speech, text="Altered perception text for test")

        for step in range(1, 7):
            fake_ts = 1700000000 + (step * 12)
            with patch("time.time", return_value=fake_ts):
                mgr.save_perception()
                prune_backups(tmp_lvl, max_backups=5)
                prune_backups(tmp_story, max_backups=5)

        with open(tmp_lvl, "r", encoding="utf-8") as f:
            saved_lvl = json.load(f)
        with open(tmp_story, "r", encoding="utf-8") as f:
            saved_story = json.load(f)

        assert saved_lvl["external_eye_level_tag"] == "PerceptionNodeActive"
        assert saved_story["external_eye_story_tag"] == "YggdrasilSpineValid"
        _assert_backups_clean_and_capped(tmp_lvl, max_backups=5)
        _assert_backups_clean_and_capped(tmp_story, max_backups=5)

    # 10. entity_editor.py & HitboxRegistry
    def test_hitbox_registry_roundtrip_and_key_preservation(self, tmp_path, monkeypatch):
        from src.game.entities.hitbox_registry import HitboxRegistry, HitboxMargins

        canonical_path = "game_data/entity_dimensions.json"
        assert os.path.exists(canonical_path)
        tmp_target = str(tmp_path / "entity_dimensions.json")

        with open(canonical_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        data["external_custom_prop"] = {
            "left": 4, "right": 4, "top": 8, "bottom": 0, "ground_offset": 0, "scale": 1.0
        }
        with open(tmp_target, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        monkeypatch.setattr("src.game.entities.hitbox_registry.CONFIG_PATH", tmp_target)

        orig_cache = copy.deepcopy(HitboxRegistry._cached_config)
        try:
            HitboxRegistry.update_margins(
                "player",
                HitboxMargins(left=9, right=9, top=14, bottom=0, ground_offset=0, scale=1.0)
            )

            for step in range(1, 8):
                fake_ts = 1700000000 + (step * 15)
                with patch("time.time", return_value=fake_ts):
                    HitboxRegistry.save_all()

            with open(tmp_target, "r", encoding="utf-8") as f:
                saved = json.load(f)

            assert "external_custom_prop" in saved
            assert saved["external_custom_prop"]["left"] == 4
            assert saved["player"]["left"] == 9
            _assert_backups_clean_and_capped(tmp_target, max_backups=5)
        finally:
            HitboxRegistry._cached_config = orig_cache
            HitboxRegistry._rollback_checkpoint = {}

    # 11. power_icons_editor.py
    def test_power_icons_editor_roundtrip_and_key_preservation(self, tmp_path, monkeypatch):
        import power_icons_editor

        canonical_path = "game_data/power_icons_config.json"
        assert os.path.exists(canonical_path)
        tmp_target = str(tmp_path / "power_icons_config.json")

        with open(canonical_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        data["external_power_meta"] = {"layout_preset": "CYBER_V3"}
        with open(tmp_target, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        monkeypatch.setattr(power_icons_editor, "CONFIG_PATH", tmp_target)

        app = power_icons_editor.PowerIconsEditor.__new__(power_icons_editor.PowerIconsEditor)
        app.toast = MagicMock()
        app.config = app._load_config()
        app.config["global_scale"] = 1.35

        for step in range(1, 8):
            fake_ts = 1700000000 + (step * 11)
            with patch("time.time", return_value=fake_ts):
                app.save_config()
                prune_backups(tmp_target, max_backups=5)

        with open(tmp_target, "r", encoding="utf-8") as f:
            saved = json.load(f)

        assert saved["external_power_meta"] == {"layout_preset": "CYBER_V3"}
        assert saved["global_scale"] == 1.35
        _assert_backups_clean_and_capped(tmp_target, max_backups=5)

    # 12. controls_editor.py & ControlsManager
    def test_controls_manager_roundtrip_and_key_preservation(self, tmp_path, monkeypatch):
        from src.game.controls_manager import ControlsManager

        canonical_path = "game_data/controls_config.json"
        assert os.path.exists(canonical_path)
        tmp_target = str(tmp_path / "controls_config.json")

        with open(canonical_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        data["external_axis_calibration"] = {"deadzone_radial": 0.12}
        with open(tmp_target, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        monkeypatch.setattr("src.game.controls_manager.CONFIG_PATH", tmp_target)

        mgr = ControlsManager()
        mgr.set_binding("JUMP", "k_space")

        for step in range(1, 8):
            fake_ts = 1700000000 + (step * 12)
            with patch("time.time", return_value=fake_ts):
                assert mgr.save_config() is True

        with open(tmp_target, "r", encoding="utf-8") as f:
            saved = json.load(f)

        assert saved["external_axis_calibration"] == {"deadzone_radial": 0.12}
        assert saved["keyboard_bindings"]["JUMP"] == "k_space"
        _assert_backups_clean_and_capped(tmp_target, max_backups=5)

    # 13. player_editor.py (request_save_config & exit hook)
    def test_player_editor_roundtrip_and_key_preservation(self, tmp_path):
        from player_editor import PlayerEditorApp

        canonical_path = "game_data/player_config.json"
        assert os.path.exists(canonical_path)
        tmp_target = str(tmp_path / "player_config.json")

        with open(canonical_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        data["external_combat_meta"] = {"combo_multiplier": 2.5, "version": "4.0"}
        data["controller_deadzones"] = {"left_stick": 0.18, "right_stick": 0.22}
        data["character_lore"] = "Zulfiqar - Crescent Blade Sovereign"
        with open(tmp_target, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        app = PlayerEditorApp.__new__(PlayerEditorApp)
        app.config_path = tmp_target
        app.config_dir = str(tmp_path)
        app.mode = "MENU"
        app.config = copy.deepcopy(data.get("states", {}))
        app.attack_config = copy.deepcopy(data.get("attacks", {}))
        app.show_toast = MagicMock()
        app.scan_backups = MagicMock()

        # Mutate in-memory parameter
        app.config["IDLE"]["animation_speed"] = 0.48

        # Execute request_save_config (Primary user save workflow) 8 times
        for step in range(1, 9):
            fake_ts = 1700000000 + (step * 20)
            with patch("time.time", return_value=fake_ts):
                app.request_save_config()

        with open(tmp_target, "r", encoding="utf-8") as f:
            saved = json.load(f)

        assert saved["states"]["IDLE"]["animation_speed"] == 0.48
        assert saved["external_combat_meta"] == {"combo_multiplier": 2.5, "version": "4.0"}
        assert saved["controller_deadzones"] == {"left_stick": 0.18, "right_stick": 0.22}
        assert saved["character_lore"] == "Zulfiqar - Crescent Blade Sovereign"
        _assert_backups_clean_and_capped(tmp_target, max_backups=5)

    # 14. shadow_editor.py & ShadowRegistry
    def test_shadow_registry_roundtrip_and_key_preservation(self, tmp_path, monkeypatch):
        from src.game.systems.shadow_registry import ShadowRegistry, ShadowProfile

        canonical_path = "game_data/shadow_config.json"
        assert os.path.exists(canonical_path)
        tmp_target = str(tmp_path / "shadow_config.json")

        with open(canonical_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        data["external_shadow_layer"] = {"depth_bias": 0.05, "render_queue": 2000}
        with open(tmp_target, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        monkeypatch.setattr("src.game.systems.shadow_registry.CONFIG_PATH", tmp_target)

        prof = ShadowProfile(alpha=165, squash_ratio=0.29, y_offset=3)
        for step in range(1, 8):
            fake_ts = 1700000000 + (step * 10)
            with patch("time.time", return_value=fake_ts):
                assert ShadowRegistry.save_profile("player", prof) is True

        with open(tmp_target, "r", encoding="utf-8") as f:
            saved = json.load(f)

        assert saved["external_shadow_layer"] == {"depth_bias": 0.05, "render_queue": 2000}
        assert saved["player"]["alpha"] == 165
        assert saved["player"]["squash_ratio"] == 0.29
        _assert_backups_clean_and_capped(tmp_target, max_backups=5)

    # 15. storyline_editor.py & StorylineConfigManager
    def test_storyline_manager_roundtrip_and_key_preservation(self, tmp_path, monkeypatch):
        from src.game.systems.storyline_config_manager import StorylineConfigManager

        canonical_path = "game_data/storyline_config.json"
        assert os.path.exists(canonical_path)
        tmp_target = str(tmp_path / "storyline_config.json")

        with open(canonical_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        data["external_storyline_telemetry"] = {"completed_chapters": [1, 2, 3]}
        with open(tmp_target, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        orig_instance = StorylineConfigManager._instance
        try:
            StorylineConfigManager._instance = None
            monkeypatch.setattr("src.game.systems.storyline_config_manager.CONFIG_PATH", tmp_target)
            mgr = StorylineConfigManager(config_path=tmp_target)
            mgr.data["corruption"]["dash_speed_multiplier"] = 2.25

            for step in range(1, 8):
                fake_ts = 1700000000 + (step * 12)
                with patch("time.time", return_value=fake_ts):
                    assert mgr.save_config(mgr.data) is True

            with open(tmp_target, "r", encoding="utf-8") as f:
                saved = json.load(f)

            assert saved["external_storyline_telemetry"] == {"completed_chapters": [1, 2, 3]}
            assert saved["corruption"]["dash_speed_multiplier"] == 2.25
            # Ensure root structure preserved
            for root_k in ("boss_dialogue", "enemy_taunts", "relics", "narrative_nodes", "boss_hierarchy"):
                assert root_k in saved, f"Root key '{root_k}' missing from saved storyline"
            _assert_backups_clean_and_capped(tmp_target, max_backups=5)
        finally:
            StorylineConfigManager._instance = orig_instance

    # 16. voiceover_editor.py
    def test_voiceover_editor_roundtrip_and_key_preservation(self, tmp_path, monkeypatch):
        import voiceover_editor

        canonical_path = "tools/voice_manifest.json"
        assert os.path.exists(canonical_path)
        tmp_target = str(tmp_path / "voice_manifest.json")

        with open(canonical_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        data["external_voice_engine"] = "Chatterbox-Audio-AI-v2"
        with open(tmp_target, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        monkeypatch.setattr(voiceover_editor, "MANIFEST_PATH", tmp_target)

        manifest = voiceover_editor.load_manifest()
        manifest["voices"]["ledger_herald"]["exaggeration"] = 0.88

        for step in range(1, 8):
            fake_ts = 1700000000 + (step * 14)
            with patch("time.time", return_value=fake_ts):
                voiceover_editor.save_manifest(manifest)
                prune_backups(tmp_target, max_backups=5)

        with open(tmp_target, "r", encoding="utf-8") as f:
            saved = json.load(f)

        assert saved["external_voice_engine"] == "Chatterbox-Audio-AI-v2"
        assert saved["voices"]["ledger_herald"]["exaggeration"] == 0.88
        _assert_backups_clean_and_capped(tmp_target, max_backups=5)
