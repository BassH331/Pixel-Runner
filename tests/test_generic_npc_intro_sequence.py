from unittest.mock import MagicMock, patch
import pygame as pg

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

from src.game.entities.generic_npc import GenericNPC, _GenericNPCState
from src.game.states.game_state import GameState

def test_generic_npc_intro_sequence_lifecycle():
    npc = GenericNPC(
        x=800,
        y=600,
        sprite_dir="assets/graphics/Necromancer/Idle",
        text="Act I: The Entry",
        title="Act I: The Entry",
        play_death_on_interact=True,
        is_intro_npc=True,
        proximity_radius=180
    )

    # 1. Entrance: Starts in WALK state
    assert npc.is_intro_npc is True
    assert npc.is_walking is True
    assert npc.is_death_complete is False
    assert npc.state == _GenericNPCState.WALK

    # 2. Intercept: Check proximity when player is close (x=650 vs x=800)
    player_rect = pg.Rect(650, 600, 40, 80)
    in_range = npc.check_proximity(player_rect)

    assert npc.is_walking is False
    assert npc.is_trance_active is True
    assert npc._trance_phase == 1
    assert npc.state == _GenericNPCState.SPAWN

    # 3. Simulate SPAWN animation finishing -> Phase 2 (Camera Zoom-In)
    npc.animation_index = len(npc.animations[_GenericNPCState.SPAWN]) - 1
    npc.update(dt=16.67, scroll_speed=0)

    assert npc.is_spawning is False
    assert npc._trance_phase == 2
    assert npc.state == _GenericNPCState.IDLE

    # 4. Trigger dialogue completion -> DEATH state (Phase 5)
    npc.trigger_death()
    assert npc.state == _GenericNPCState.DEATH
    assert npc.is_death_complete is False

    # 5. Simulate DEATH disintegration animation finishing -> Complete & Unlocked
    npc.animation_index = len(npc.animations[_GenericNPCState.DEATH]) - 1
    npc.update(dt=16.67, scroll_speed=0)

    assert npc.is_death_complete is True
