"""Unit tests for BossManager tagging spawned bosses with a stable boss_key."""

import pygame as pg
import pytest

from src.game.entities.boss_manager import BossManager


class MockPlayer:
    def __init__(self):
        self.rect = pg.Rect(100, 100, 32, 64)
        self.facing_left = True


@pytest.fixture(scope="module", autouse=True)
def setup_pygame():
    if not pg.get_init():
        pg.init()
    if not pg.font.get_init():
        pg.font.init()
    if not pg.display.get_init() or pg.display.get_surface() is None:
        pg.display.init()
        pg.display.set_mode((1280, 720))
    yield


def test_spawn_boss_tags_wizard_with_boss_wizard_key():
    player = MockPlayer()
    boss = BossManager.spawn_boss(
        {"title": "Fire Wizard", "sprite_dir": "assets/wizard/Idle"},
        player,  # type: ignore
        1280,
        720,
    )
    assert getattr(boss, "boss_key", None) == "boss_wizard"


def test_spawn_boss_tags_non_wizard_with_boss_skeleton_key():
    player = MockPlayer()
    # No sprite_dir -> resolve_boss_class() falls back to Skeleton
    boss = BossManager.spawn_boss(
        {"title": "Skeleton Boss"},
        player,  # type: ignore
        1280,
        720,
    )
    assert getattr(boss, "boss_key", None) == "boss_skeleton"
