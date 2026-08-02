import os
import json
import pytest
from unittest.mock import patch, MagicMock

from src.game.plugins.vfx_plugin import VFXPlugin

def test_vfx_plugin_load_and_query():
    VFXPlugin._config_cache = None
    config = VFXPlugin.load_config()
    assert "entity_rules" in config
    assert "vfx_library" in config
    
    # Query rule for skeleton
    rule_skel = VFXPlugin.get_rule("skeleton")
    assert rule_skel["has_blood"] is False
    assert rule_skel["vfx_type"] == "magic_shot"
    
    # Query rule for player
    rule_player = VFXPlugin.get_rule("player")
    assert rule_player["has_blood"] is True
    assert rule_player["vfx_type"] == "blood"

def test_vfx_plugin_set_rule():
    VFXPlugin._config_cache = None
    with patch("src.game.plugins.vfx_plugin.VFXPlugin.save_config") as mock_save:
        # Dynamically make skeleton bleed!
        rule = VFXPlugin.set_rule("skeleton", has_blood=True, vfx_type="blood_large", vfx_scale=3.0)
        assert rule["has_blood"] is True
        assert rule["vfx_type"] == "blood_large"
        assert rule["vfx_scale"] == 3.0
        
        # Verify query returns updated rule
        queried = VFXPlugin.get_rule("skeleton")
        assert queried["has_blood"] is True
        assert queried["vfx_type"] == "blood_large"

def test_vfx_plugin_apply_to_entity():
    VFXPlugin._config_cache = None
    entity = MagicMock()
    entity.__class__.__name__ = "Skeleton"
    
    VFXPlugin.apply_to_entity(entity)
    assert entity.has_blood is False
    assert entity.vfx_type == "magic_shot"
    assert entity.vfx_scale == 2.5
