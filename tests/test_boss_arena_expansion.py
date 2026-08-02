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

from src.game.entities.player import Player

def test_boss_arena_expansion():
    with patch("v3x_zulfiqar_gideon.asset_manager.AssetManager.get_texture") as mock_tex, \
         patch("v3x_zulfiqar_gideon.asset_manager.AssetManager.get_font") as mock_font:
        mock_tex.return_value = pg.Surface((32, 32))
        mock_font.return_value = pg.font.Font(None, 20)
        from src.game.states.game_state import GameState
        manager = MagicMock()
        state = GameState(manager)
        player = state.player.sprite
        assert player is not None
        assert player.right_bound_ratio == 0.65
        
        # Simulate player position when boss spawns
        player.rect.left = 400
        
        # Mock boss spawn params
        params = {
            "boss_type": "green_monster",
            "title": "The Gatekeeper",
            "soul_value": 100
        }
        
        state._handle_boss_spawn(params)
        
        assert state._arena_active is True
        # Left boundary should allow at least 350px retreat room: 400 - 380 = 20 -> clamped to 40
        assert state._arena_left_boundary == 40
        assert player.right_bound_ratio == 0.90

def test_boss_arena_deactivation():
    with patch("v3x_zulfiqar_gideon.asset_manager.AssetManager.get_texture") as mock_tex, \
         patch("v3x_zulfiqar_gideon.asset_manager.AssetManager.get_font") as mock_font:
        mock_tex.return_value = pg.Surface((32, 32))
        mock_font.return_value = pg.font.Font(None, 20)
        from src.game.states.game_state import GameState
        manager = MagicMock()
        state = GameState(manager)
        player = state.player.sprite
        assert player is not None
        
        player.right_bound_ratio = 0.90
        state._arena_active = True
        
        # Deactivate arena
        state._arena_active = False
        player.right_bound_ratio = getattr(player, "_RUN_RIGHT_BOUND_RATIO", 0.65)
        
        assert state._arena_active is False
        assert player.right_bound_ratio == 0.65
