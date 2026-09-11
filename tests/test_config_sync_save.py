"""
Unit test verifying ConfigClient priority for local file edits, cloud pushes, and equality sync.
"""

import os
import json
import pytest
from src.game.services.config_client import ConfigClient
from src.game.services.local_cache import LocalCache


def test_config_client_local_file_priority_and_push(tmp_path, monkeypatch):
    """Test that local JSON files take precedence over unequal cloud data and trigger cloud pushes."""
    config_file = tmp_path / "boss_skeleton_config.json"
    local_data = {"spidey_sense": 0.35, "max_health": 150.0}
    config_file.write_text(json.dumps(local_data))

    ConfigClient.invalidate_cache("boss_skeleton")
    monkeypatch.setattr(ConfigClient, "_load_fallback", lambda key: json.loads(config_file.read_text()))

    # Track cloud pushes
    pushed_configs = []
    monkeypatch.setattr(ConfigClient, "_send_push_to_api", lambda key, data: pushed_configs.append((key, data)) or True)

    # 1. Fetch config -> returns local values (0.35)
    fetched = ConfigClient.fetch_config("boss_skeleton")
    assert fetched["spidey_sense"] == 0.35

    # 2. Unequal cloud data (0.65 vs 0.35) -> local takes priority and pushes 0.35 to cloud
    cloud_data = {"spidey_sense": 0.65, "max_health": 150.0}
    monkeypatch.setattr(ConfigClient, "_fetch_from_api", lambda key: cloud_data)
    ConfigClient._async_api_sync("boss_skeleton")

    sync_fetched = ConfigClient.fetch_config("boss_skeleton")
    assert sync_fetched["spidey_sense"] == 0.35
    assert len(pushed_configs) == 1
    assert pushed_configs[0][1]["spidey_sense"] == 0.35


def test_config_client_equal_cloud_data_used(tmp_path, monkeypatch):
    """Test that if local and cloud configs are equal, cloud data is accepted directly without pushing."""
    config_file = tmp_path / "boss_wizard_config.json"
    data = {"spidey_sense": 0.40, "max_mana": 100.0}
    config_file.write_text(json.dumps(data))

    ConfigClient.invalidate_cache("boss_wizard")
    monkeypatch.setattr(ConfigClient, "_load_fallback", lambda key: json.loads(config_file.read_text()))

    pushed = []
    monkeypatch.setattr(ConfigClient, "_send_push_to_api", lambda key, data: pushed.append(key) or True)

    cloud_equal_data = {"spidey_sense": 0.40, "max_mana": 100.0}
    monkeypatch.setattr(ConfigClient, "_fetch_from_api", lambda key: cloud_equal_data)
    ConfigClient._async_api_sync("boss_wizard")

    fetched = ConfigClient.fetch_config("boss_wizard")
    assert fetched["spidey_sense"] == 0.40
    # No unnecessary push triggered when both are equal
    assert len(pushed) == 0


def test_push_config_updates_cache_and_triggers_api(tmp_path, monkeypatch):
    """Test that push_config updates RAM cache, LocalCache, and triggers network push."""
    pushed = []
    monkeypatch.setattr(ConfigClient, "_send_push_to_api", lambda key, data: pushed.append((key, data)) or True)

    new_cfg = {"spidey_sense": 0.15, "speed": 4.0}
    success = ConfigClient.push_config("boss_skeleton", new_cfg, async_push=False)

    assert success is True
    assert ConfigClient.fetch_config("boss_skeleton")["spidey_sense"] == 0.15
    assert LocalCache.get_config("boss_skeleton")["spidey_sense"] == 0.15
    assert len(pushed) == 1
    assert pushed[0][1]["spidey_sense"] == 0.15
