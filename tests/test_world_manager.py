from unittest.mock import MagicMock
import pygame as pg

pg.init()
pg.display.set_mode((1280, 720), pg.NOFRAME)

from src.game.systems.world_manager import WorldManager


def test_world_manager_initialization():
    wm = WorldManager(1280, 720)
    assert wm.screen_width == 1280
    assert wm.screen_height == 720
    assert wm.environment_manager is not None
    assert wm.event_manager is not None


def test_world_manager_config_loading_and_event_trigger():
    wm = WorldManager(1280, 720)

    callback = MagicMock()
    wm.register_event_handler("spawn_boss", callback)

    level_data = {
        "environment": {
            "ground_y": 600
        },
        "world_events": [
            {
                "id": 101,
                "distance": 500.0,
                "event_type": "spawn_boss",
                "params": {"boss_id": "necromancer"}
            }
        ]
    }

    wm.load_level_config(level_data)
    assert wm.ground_y == 600

    # At distance 200 -> event should not trigger yet
    wm.update(dt_seconds=0.016, bg_scroll_speed=2.0, world_distance=200.0)
    callback.assert_not_called()

    # At distance 600 -> event should trigger
    wm.update(dt_seconds=0.016, bg_scroll_speed=2.0, world_distance=600.0)
    callback.assert_called_once_with({"boss_id": "necromancer"})


def test_world_manager_ground_height_lookup():
    wm = WorldManager(1280, 720)
    ground_y = wm.get_ground_y_at(150.0)
    assert isinstance(ground_y, int)
