"""
Tests for PixelRunnerEngine cross-platform display presentation,
scaling, ground alignment, and fullscreen support.
"""
import os
import pytest
import pygame as pg
from unittest.mock import patch, MagicMock

from main import PixelRunnerEngine, BASE_WIDTH, BASE_HEIGHT
from src.game.entities.player import Player


@pytest.fixture(scope="module", autouse=True)
def init_pygame():
    pg.init()
    yield
    pg.quit()


def test_pixel_runner_engine_initializes_with_1280x720_canvas():
    """Verify PixelRunnerEngine locks internal logical canvas to 1280x720."""
    engine = PixelRunnerEngine(
        title="Test Engine",
        fullscreen=False,
        windowed=True,
        base_width=1280,
        base_height=720,
    )

    assert engine.width == 1280
    assert engine.height == 720
    assert os.environ.get("SDL_VIDEO_CENTERED") == "1"

    surface = pg.display.get_surface()
    assert surface.get_width() == 1280
    assert surface.get_height() == 720


def test_pixel_runner_engine_fullscreen_toggle():
    """Verify fullscreen flag triggers toggle_fullscreen on display."""
    with patch("pygame.display.toggle_fullscreen") as mock_toggle:
        engine = PixelRunnerEngine(
            title="Test Engine",
            fullscreen=True,
            windowed=False,
        )
        mock_toggle.assert_called_once()


def test_pixel_runner_engine_default_windowed_mode():
    """Verify default engine instantiates and retains 1280x720 screen."""
    engine = PixelRunnerEngine(
        title="Test Engine",
        fullscreen=False,
        windowed=False,
    )
    assert engine.width == 1280
    assert engine.height == 720
    assert engine.screen.get_size() == (1280, 720)


def test_player_ground_y_matches_level_ground():
    """Verify player spawned at y=222 is aligned with ground level 606."""
    player = Player(200, 222, MagicMock())
    assert player.rect.bottom == 606
