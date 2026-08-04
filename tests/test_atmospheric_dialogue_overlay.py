"""
Unit tests for ObjectiveDisplay atmospheric dialogue overlay effects and skip logic.
"""

import pytest
import pygame as pg

if not pg.get_init():
    pg.init()
if not pg.display.get_surface():
    pg.display.set_mode((1, 1), pg.NOFRAME)

from v3x_zulfiqar_gideon import UITheme
from src.game.ui.objective_display import ObjectiveDisplay, FXState


@pytest.fixture(autouse=True)
def setup_ui_theme():
    UITheme.configure_overlays(
        stone_path="assets/graphics/UI/PNG/UI board Medium  stone.png",
        parchment_path="assets/graphics/UI/PNG/UI board Medium  parchment.png",
        title_font_path="assets/Colorfiction_HandDrawnFonts/Colorfiction - Gothic - Regular.otf",
        body_font_path="assets/Colorfiction_HandDrawnFonts/Colorfiction - Papyrus.otf",
        text_color=(60, 40, 20),
    )


def test_objective_display_theme_show():
    overlay = ObjectiveDisplay()
    overlay.show("The end of the long nightmare is in sight...", "Act I: The Entry", theme="necromancer_dark_fire")
    assert overlay.is_active is True
    assert overlay._fx_state == FXState.FLAME_BURST


def test_objective_display_skip_flow():
    overlay = ObjectiveDisplay()
    overlay.show("Short test dialogue", "Test", theme="necromancer_dark_fire")
    assert overlay._fx_state == FXState.FLAME_BURST

    # Pressing ENTER while in FLAME_BURST should fast-forward to COMPLETE
    dummy_event = pg.event.Event(pg.KEYDOWN, key=pg.K_RETURN)
    dismissed = overlay.handle_event(dummy_event)
    assert dismissed is False
    assert overlay._fx_state == FXState.COMPLETE

    # Pressing ENTER again while COMPLETE should dismiss overlay
    dismissed_again = overlay.handle_event(dummy_event)
    assert dismissed_again is True
    assert overlay.is_active is False


def test_objective_display_typewriter_update():
    overlay = ObjectiveDisplay()
    overlay.show("Typewriter text test", "Test", theme="default")
    assert overlay._fx_state == FXState.TYPEWRITER

    # Advance 1 second (1000ms)
    overlay.update(1000.0)
    assert overlay._char_count > 0
