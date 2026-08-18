import pygame as pg
from unittest.mock import MagicMock

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
    body_font_path="dummy_font",
    prompt_font_path="dummy_font"
)

from src.game.ui.hud_overlay import HUDOverlay


def test_hud_overlay_initialization():
    hud = HUDOverlay(1280, 720)
    assert hud.screen_width == 1280
    assert hud.screen_height == 720
    assert hud.player_ui is not None
    assert hud.objective_display is not None
    assert hud.notification_banner is not None
    assert hud.tutorial_overlay is not None


def test_hud_overlay_update_and_draw():
    hud = HUDOverlay(1280, 720)
    target_surf = pg.Surface((1280, 720))

    # Update lifecycle
    hud.update()

    # Draw world UI
    hud.draw_world_ui(target_surf)

    # Draw boss health bar
    obstacle_group = pg.sprite.Group()
    hud.draw_boss_health_bar(target_surf, obstacle_group)

    # Draw screen overlays
    hud.draw_screen_overlays(target_surf)
