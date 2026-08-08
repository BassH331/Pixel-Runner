"""
Tests for EnvironmentManager and LDtkImporter systems.
"""

from __future__ import annotations

import os
import tempfile
import pygame as pg
import pytest

from src.game.systems.environment_manager import EnvironmentManager, ParallaxLayer
from src.game.levels.ldtk_importer import LDtkImporter


@pytest.fixture(scope="module", autouse=True)
def setup_pygame():
    pg.init()
    pg.display.set_mode((1, 1), pg.HIDDEN)
    yield
    pg.quit()


def test_environment_manager_defaults():
    env = EnvironmentManager(1280, 720)
    assert env.screen_width == 1280
    assert env.screen_height == 720
    assert env.bg_music_track == "game_loop"
    assert env.ground_y == 686


def test_environment_manager_custom_config():
    config = {
        "bg_music_track": "custom_track",
        "ground_y": 550,
        "sky": {
            "layers": []
        },
        "parallax_layers": []
    }
    env = EnvironmentManager(1280, 720, env_config=config)
    assert env.bg_music_track == "custom_track"
    assert env.ground_y == 550


def test_ldtk_importer_conversion():
    ldtk_data = {
        "levels": [
            {
                "identifier": "Test_Level",
                "pxWid": 10000,
                "pxHei": 720,
                "bgRelPath": "assets/graphics/background images/new_bg_images/bg_image.png",
                "fieldInstances": [
                    {"__identifier__": "level_name", "__value__": "Test Level Name"}
                ],
                "layerInstances": [
                    {
                        "__identifier__": "Entities",
                        "__type__": "Entities",
                        "entityInstances": [
                            {
                                "__identifier__": "GenericNPC",
                                "px": [500, 300],
                                "fieldInstances": [
                                    {"__identifier__": "title", "__value__": "Test NPC"},
                                    {"__identifier__": "text", "__value__": "Hello!"},
                                    {"__identifier__": "sprite_dir", "__value__": "assets/graphics/Necromancer/Idle"}
                                ]
                            }
                        ]
                    }
                ]
            }
        ]
    }

    config = LDtkImporter.convert_ldtk_to_level_config(ldtk_data, 0)
    assert config["level_name"] == "Test Level Name"
    assert config["level_end_distance"] == 10000
    assert len(config["world_events"]) == 1
    assert config["world_events"][0]["params"]["title"] == "Test NPC"
