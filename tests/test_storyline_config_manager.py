"""
Unit tests for StorylineConfigManager data-driven plugin architecture.
"""
import os
import json
import pytest
from src.game.systems.storyline_config_manager import StorylineConfigManager, CONFIG_PATH


def test_storyline_config_manager_load():
    manager = StorylineConfigManager.get_instance()
    data = manager.data

    assert "relics" in data
    assert "corruption" in data
    assert "boss_hierarchy" in data
    assert "whisperers" in data


def test_relics_config_content():
    manager = StorylineConfigManager.get_instance()
    relics = manager.get_relics()

    assert "shattered_gauntlet" in relics
    assert "voragis_inkwell" in relics
    assert relics["shattered_gauntlet"]["title"] == "Shattered Gauntlet"
    assert "rain and stone dust" in relics["shattered_gauntlet"]["memory_text"]


def test_corruption_config_values():
    manager = StorylineConfigManager.get_instance()
    corr = manager.get_corruption_config()

    assert corr.get("dash_speed_multiplier") == 1.5
    assert corr.get("damage_multiplier") == 1.5
    assert corr.get("instability_enabled") is True


def test_boss_hierarchy_config():
    manager = StorylineConfigManager.get_instance()
    hierarchy = manager.get_boss_hierarchy()

    assert hierarchy == ["green_monster", "gatekeeper", "necromancer", "fire_wizard", "dark_ronin"]
