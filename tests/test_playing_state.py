import pygame as pg
from unittest.mock import MagicMock

pg.init()
pg.display.set_mode((1280, 720), pg.NOFRAME)

from v3x_zulfiqar_gideon import StateManager, UITheme
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
    icons={"gray": "dummy_gray", "red": "dummy_red", "yellow": "dummy_yellow"},
    font_path="dummy_font"
)
UITheme.configure_overlays(
    stone_path="dummy_stone",
    parchment_path="dummy_parchment",
    title_font_path="dummy_font",
    body_font_path="dummy_font",
    prompt_font_path="dummy_font"
)

from src.game.states.playing_state import PlayingState
from src.game.states.game_state import GameState


def test_playing_state_lifecycle():
    manager = StateManager()
    state = PlayingState(manager)
    assert not state.is_active

    state.on_enter()
    assert state.is_active
    assert not state.is_paused

    state.on_exit()
    assert not state.is_active


def test_game_state_is_playing_state_subclass():
    manager = StateManager()
    game_state = GameState(manager)
    assert isinstance(game_state, PlayingState)
    assert isinstance(game_state, PlayingState)
