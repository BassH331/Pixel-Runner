"""
Unit tests for verifying system-wide consistency of entity editor dimensions,
hitbox margins, ground offsets, and scale factors across HitboxRegistry,
level configurations, ConfigClient, and game entity classes.
"""

import json
import os
import unittest
from unittest.mock import patch, MagicMock

import pygame as pg
if not pg.get_init():
    pg.init()
if not pg.display.get_surface():
    pg.display.set_mode((800, 600))

from src.game.entities.hitbox_registry import HitboxRegistry, HitboxMargins
from src.game.services import ConfigClient, LocalCache
from src.game.entities.player import Player
from src.game.entities.enemy import Enemy
from src.game.entities.bloo_zombie import BloodZombie
from src.game.entities.green_monster import GreenMonster
from src.game.entities.fire_wizard import FireWizard


class TestEntityEditorConsistency(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        HitboxRegistry._cached_config = {}
        HitboxRegistry._load_config()

    def test_entity_dimensions_json_contains_all_edited_entities(self):
        """Verify that entity_dimensions.json has committed and locked values matching entity editor."""
        cfg_path = "game_data/entity_dimensions.json"
        self.assertTrue(os.path.exists(cfg_path))
        with open(cfg_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # 1. Player
        self.assertIn("player", data)
        player_cfg = data["player"]
        self.assertEqual(player_cfg["left"], 387)
        self.assertEqual(player_cfg["right"], 391)
        self.assertEqual(player_cfg["top"], 191)
        self.assertEqual(player_cfg["bottom"], 0)
        self.assertEqual(player_cfg["ground_offset"], 34)
        self.assertEqual(player_cfg["scale"], 3.0)

        # 2. Enemy (Bat)
        self.assertIn("enemy", data)
        enemy_cfg = data["enemy"]
        self.assertEqual(enemy_cfg["left"], 75)
        self.assertEqual(enemy_cfg["right"], 75)
        self.assertEqual(enemy_cfg["top"], 75)
        self.assertEqual(enemy_cfg["bottom"], 75)
        self.assertEqual(enemy_cfg["ground_offset"], 0)
        self.assertEqual(enemy_cfg["scale"], 1.34)

        # 3. Boss: Blood Zombie
        self.assertIn("boss:bloodzombie", data)
        bz_cfg = data["boss:bloodzombie"]
        self.assertEqual(bz_cfg["left"], 65)
        self.assertEqual(bz_cfg["right"], 189)
        self.assertEqual(bz_cfg["top"], 136)
        self.assertEqual(bz_cfg["bottom"], 28)
        self.assertEqual(bz_cfg["ground_offset"], 65)
        self.assertEqual(bz_cfg["scale"], 2.0)

        # 4. Boss: Green Monster (Gatekeeper)
        self.assertIn("boss:green_monster", data)
        gm_cfg = data["boss:green_monster"]
        self.assertEqual(gm_cfg["left"], 216)
        self.assertEqual(gm_cfg["right"], 210)
        self.assertEqual(gm_cfg["top"], 101)
        self.assertEqual(gm_cfg["bottom"], 39)
        self.assertEqual(gm_cfg["ground_offset"], 127)
        self.assertEqual(gm_cfg["scale"], 2.63)

        # 5. Boss: Wizard
        self.assertIn("boss:wizard", data)
        wiz_cfg = data["boss:wizard"]
        self.assertEqual(wiz_cfg["left"], 259)
        self.assertEqual(wiz_cfg["right"], 281)
        self.assertEqual(wiz_cfg["top"], 208)
        self.assertEqual(wiz_cfg["bottom"], 192)
        self.assertEqual(wiz_cfg["ground_offset"], 127)
        self.assertEqual(wiz_cfg["scale"], 4.11)

    def test_hitbox_registry_defaults_integral(self):
        """Ensure HitboxRegistry fallback baseline defaults mirror the tuned entity dimensions."""
        defaults = HitboxRegistry.DEFAULTS
        self.assertEqual(defaults["player"], HitboxMargins(387, 391, 191, 0, 34, 3.0))
        self.assertEqual(defaults["enemy"], HitboxMargins(75, 75, 75, 75, 0, 1.34))
        self.assertEqual(defaults["boss:bloodzombie"], HitboxMargins(65, 189, 136, 28, 65, 2.0))
        self.assertEqual(defaults["boss:green_monster"], HitboxMargins(216, 210, 101, 39, 127, 2.63))
        self.assertEqual(defaults["boss:wizard"], HitboxMargins(259, 281, 208, 192, 127, 4.11))

    def test_level_1_boss_scales_match_registry(self):
        """Ensure level_1.json world_events scales for bosses match HitboxRegistry values exactly."""
        with open("game_data/level_1.json", "r", encoding="utf-8") as f:
            lvl = json.load(f)

        events = {e.get("params", {}).get("title"): e.get("params", {}) for e in lvl.get("world_events", []) if e.get("type") == "boss"}

        # Blood Zombie
        self.assertIn("Blood Zombie", events)
        self.assertEqual(events["Blood Zombie"]["scale"], HitboxRegistry.get_margins("boss:bloodzombie").scale)

        # Gatekeeper (Green Monster)
        self.assertIn("The Gatekeeper", events)
        self.assertEqual(events["The Gatekeeper"]["scale"], HitboxRegistry.get_margins("boss:green_monster").scale)

        # Wizard
        self.assertIn("The Fabricator's Enforcer", events)
        self.assertEqual(events["The Fabricator's Enforcer"]["scale"], HitboxRegistry.get_margins("boss:wizard").scale)

    def test_blood_zombie_config_client_scale_parity(self):
        """Ensure enemy_blood_zombie_config.json scale aligns with HitboxRegistry scale (2.0)."""
        bz_config = ConfigClient.fetch_config("enemy_blood_zombie")
        self.assertIsNotNone(bz_config)
        self.assertEqual(bz_config.get("scale"), 2.0)
        self.assertEqual(bz_config.get("ground_offset"), 65)

    def test_player_entity_instantiation_uses_editor_margins(self):
        """Ensure Player entity instantiates with the exact calibrated margins and scale."""
        player = Player(x=100, y=100, audio_manager=None)
        margins = HitboxRegistry.get_margins("player")
        self.assertEqual(player.scale, margins.scale)
        surf_h = pg.display.get_surface().get_height() if pg.display.get_surface() else 720
        self.assertEqual(player._ground_y, surf_h - margins.ground_offset)

    def test_enemy_entity_instantiation_uses_editor_margins(self):
        """Ensure Enemy (Bat) entity instantiates with the calibrated margins and scale factor."""
        enemy = Enemy(audio_manager=None)
        margins = HitboxRegistry.get_margins("enemy")
        self.assertEqual(margins.scale, 1.34)
        self.assertEqual(margins.left, 75)
        self.assertEqual(margins.right, 75)
        self.assertEqual(margins.top, 75)
        self.assertEqual(margins.bottom, 75)
