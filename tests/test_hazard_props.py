from unittest.mock import MagicMock, patch
import pygame as pg
import pytest

pg.init()
pg.display.set_mode((1280, 720), pg.NOFRAME)

from v3x_zulfiqar_gideon import UITheme
UITheme.configure_buttons(
    assets={
        "big": ("dummy_big", "dummy_big_p"),
        "medium": ("dummy_med", "dummy_med_p"),
        "cancel": ("dummy_cancel", "dummy_cancel_p"),
        "new_start": ("dummy_new", "dummy_new_p"),
    },
    font_path="dummy_font"
)
UITheme.configure_notifications(
    banner_path="dummy_banner",
    icons={
        "gray": "dummy_gray",
        "red": "dummy_red",
        "yellow": "dummy_yellow",
    },
    font_path="dummy_font"
)
UITheme.configure_overlays(
    stone_path="dummy_stone",
    parchment_path="dummy_parchment",
    title_font_path="dummy_font",
    body_font_path="dummy_font"
)

from src.game.systems.environment_manager import EnvironmentProp
from src.game.entities.player import PlayerState

def test_environment_prop_hazard_collision_type():
    prop = EnvironmentProp(
        texture_path="assets/graphics/Spikes/spikes_1.png",
        pos_x=100.0,
        pos_y=600.0,
        scale=1.0,
        collision_type="hazard"
    )
    assert prop.collision_type == "hazard"
    d = prop.to_dict()
    assert d["collision_type"] == "hazard"

def test_game_state_environmental_hazard_damage():
    with patch("v3x_zulfiqar_gideon.asset_manager.AssetManager.get_texture") as mock_tex, \
         patch("v3x_zulfiqar_gideon.asset_manager.AssetManager.get_font") as mock_font:
        mock_tex.return_value = pg.Surface((32, 32))
        mock_font.return_value = pg.font.Font(None, 20)
        from src.game.states.game_state import GameState
        
        manager = MagicMock()
        state = GameState(manager)
        player = state.player.sprite
        assert player is not None

        # Position player and spike prop in exact overlapping rectangles
        player.rect = pg.Rect(100, 100, 64, 64)
        
        spike_prop = EnvironmentProp(
            texture_path="assets/graphics/Spikes/spikes_1.png",
            pos_x=100.0,
            pos_y=100.0,
            scale=1.0,
            collision_type="hazard"
        )
        spike_prop.width = 64
        spike_prop.height = 64
        state.environment_manager.props.append(spike_prop)

        # Force state to RUN and clear invincibility
        player.set_state(PlayerState.RUN, force=True)
        player._invincibility_timer = 0.0
        player._invincibility_duration = 0.0
        
        health_before = player.health
        assert player.is_invincible is False

        # Execute environmental hazard check
        state.combat_system.check_environmental_hazards()
        assert player.health < health_before
        assert player.is_invincible is True
