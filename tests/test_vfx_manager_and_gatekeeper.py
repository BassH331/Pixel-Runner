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

from src.game.effects.vfx_manager import VisualEffectManager, VisualEffect
from src.game.entities.skeleton import Skeleton
from src.game.entities.player import Player
from src.game.entities.green_monster import GreenMonster, GatekeeperState, MagicShotProjectile

def test_vfx_entity_blood_rules():
    VisualEffectManager.clear()
    
    player = MagicMock()
    player.has_blood = True
    
    skeleton = MagicMock()
    skeleton.has_blood = False
    skeleton.is_skeleton = True
    
    # Player hit -> blood VFX
    vfx_player = VisualEffectManager.spawn_hit_vfx(100, 100, entity=player)
    assert vfx_player is not None
    
    # Skeleton hit -> spark/magic VFX (no blood for bones!)
    vfx_skel = VisualEffectManager.spawn_hit_vfx(200, 200, entity=skeleton)
    assert vfx_skel is not None
    
    assert len(VisualEffectManager._active_effects) == 2

def test_gatekeeper_enraged_phase():
    with patch("v3x_zulfiqar_gideon.asset_manager.AssetManager.get_texture") as mock_tex, \
         patch("v3x_zulfiqar_gideon.asset_manager.AssetManager.get_font") as mock_font:
        mock_tex.return_value = pg.Surface((32, 32))
        mock_font.return_value = pg.font.Font(None, 20)
        
        player = MagicMock()
        player.rect = pg.Rect(100, 100, 50, 50)
        player.is_invincible = False
        
        boss = GreenMonster(x=400, y=100, player=player, custom_health=300.0)
        assert boss._max_health == 300.0
        assert boss.has_blood is True
        assert boss.is_enraged is False
        
        # Take 100 damage -> health 200 (> 50%) -> not enraged yet
        boss.take_damage(100.0)
        assert boss._health == 200.0
        assert boss.is_enraged is False
        
        # Reset state from HURT to IDLE to simulate next attack window
        boss.set_state(GatekeeperState.IDLE, force=True)
        
        # Take 60 damage -> health 140 (<= 50% of 300) -> ENRAGED!
        boss.take_damage(60.0)
        assert boss._health == 140.0
        assert boss.is_enraged is True
