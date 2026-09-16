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
    assert hud.side_notification is not None


def test_hud_overlay_update_and_draw():
    hud = HUDOverlay(1280, 720)
    target_surf = pg.Surface((1280, 720))

    # Trigger a side notification
    hud.side_notification.show("Test kill text", "First kill!!")
    assert hud.side_notification.is_active is True

    # Update lifecycle
    hud.update(16.0)

    # Draw world UI
    hud.draw_world_ui(target_surf)

    # Draw boss health bar
    obstacle_group = pg.sprite.Group()
    hud.draw_boss_health_bar(target_surf, obstacle_group)

    # Draw screen overlays (includes side_notification)
    hud.draw_screen_overlays(target_surf)


def test_player_ui_layout_bounds():
    from src.game.ui.player_ui import PlayerUI
    ui = PlayerUI()
    
    mana_y = ui.mana_bar_pos[1]
    stamina_y = ui.stamina_bar_pos[1]
    souls_y = ui.souls_icon_pos[1]
    relic_y = ui.relic_icon_pos[1]
    
    # Assert each element has at least 50px vertical spacing to prevent framed icon & text collisions
    assert stamina_y >= mana_y + 50, f"Stamina y ({stamina_y}) is too close to Mana y ({mana_y})"
    assert souls_y >= stamina_y + 50, f"Souls y ({souls_y}) is too close to Stamina y ({stamina_y})"
    assert relic_y >= souls_y + 60, f"Relic icon y ({relic_y}) is too close to Souls y ({souls_y})"
    
    # Test rendering without raising errors
    surf = pg.Surface((1280, 720))
    ui.draw(surf)


