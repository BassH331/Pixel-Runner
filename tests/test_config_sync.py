"""
Unit tests for atomic ConfigClient.save_and_sync, BloodZombie.apply_config,
and editor-to-game config synchronization.
"""

import json
import os
import tempfile
from unittest.mock import MagicMock
import pygame as pg

from src.game.services import ConfigClient, LocalCache
from src.game.entities.bloo_zombie import BloodZombie
from src.game.entities.hitbox_registry import HitboxRegistry, HitboxMargins


def setup_module():
    if not pg.display.get_init():
        pg.init()
        pg.display.set_mode((800, 600))


def test_config_client_save_and_sync():
    """Verify that ConfigClient.save_and_sync updates disk JSON, RAM session cache, and LocalCache."""
    test_key = "enemy_blood_zombie"
    original_config = ConfigClient.fetch_config(test_key)

    modified_config = dict(original_config)
    modified_config["attack_range"] = 77
    modified_config["speed"] = 3.45

    success = ConfigClient.save_and_sync(test_key, modified_config, async_push=False)
    assert success is True

    # 1. Check RAM session cache
    fetched = ConfigClient.fetch_config(test_key)
    assert fetched["attack_range"] == 77
    assert fetched["speed"] == 3.45

    # 2. Check SQLite LocalCache directly
    sqlite_config = LocalCache.get_config(test_key)
    assert sqlite_config["attack_range"] == 77
    assert sqlite_config["speed"] == 3.45

    # Restore original config
    ConfigClient.save_and_sync(test_key, original_config, async_push=False)


def test_blood_zombie_apply_config():
    """Verify that BloodZombie.apply_config hot-reloads stats dynamically at runtime."""
    player_mock = MagicMock()
    player_mock.rect = pg.Rect(500, 300, 40, 60)
    player_mock.is_dead = False

    zombie = BloodZombie(x=400, y=300, player=player_mock, tier="boss")
    
    new_config = {
        "max_health": 250.0,
        "speed": 4.2,
        "attack_range": 82,
        "attack_hitbox_width": 95,
        "detection_range": 1600,
    }

    zombie.apply_config(new_config)

    assert zombie.max_health == 250.0
    assert zombie._speed == 4.2
    assert zombie._attack_range == 82
    assert zombie._attack_hitbox_width == 95
    assert zombie._detection_range == 1600
    assert zombie.perception.vision_range == 1600.0
    assert zombie.utility_engine.preferred_spacing == 82.0


def test_blood_zombie_realtime_hot_reload():
    """Verify that external disk saves trigger live hot-reloading during entity update()."""
    test_key = "enemy_blood_zombie"
    original_config = ConfigClient.fetch_config(test_key)

    player_mock = MagicMock()
    player_mock.rect = pg.Rect(500, 300, 40, 60)
    player_mock.is_dead = False

    zombie = BloodZombie(x=400, y=300, player=player_mock, tier="boss")

    # Prime ConfigClient mtime tracker
    ConfigClient.check_for_updates(test_key)

    # Simulate external editor save with a new attack_range and speed
    modified_config = dict(original_config)
    modified_config["attack_range"] = 99
    modified_config["speed"] = 3.99
    ConfigClient.save_and_sync(test_key, modified_config, async_push=False)

    # Force mtime trigger update in ConfigClient
    from src.game.services.config_client import LOCAL_FILE_MAP
    file_path = LOCAL_FILE_MAP[test_key]
    os.utime(file_path, None)

    # Execute entity update step (triggers 0.5s timer check)
    zombie._hot_reload_timer = 0.5
    zombie.update(dt=0.016)

    # Entity should be live updated!
    assert zombie._attack_range == 99
    assert zombie._speed == 3.99

    # Restore original config
    ConfigClient.save_and_sync(test_key, original_config, async_push=False)
