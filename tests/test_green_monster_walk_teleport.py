import pygame as pg
import pytest

from src.game.entities.green_monster import GreenMonster, GatekeeperState


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


def _make_green_monster() -> GreenMonster:
    player = MockPlayer()
    return GreenMonster(200, 600, player, tier="boss", custom_scale=1.0, custom_health=100.0)  # type: ignore


def test_green_monster_apply_config():
    monster = _make_green_monster()
    monster.apply_config({
        "max_mana": 120.0,
        "spell_mana_cost": 25.0,
        "spidey_sense": 0.5
    })

    assert monster._max_mana == 120.0
    assert monster._spell_mana_cost == 25.0
    assert monster._spidey_sense == 0.5


def test_green_monster_gravity_and_grounding():
    monster = _make_green_monster()
    monster.rect.bottom = monster._ground_y - 200
    monster._gravity = 0.0

    # Apply gravity: should increase gravity and drop rect down
    monster._apply_gravity()
    assert monster._gravity > 0.0
    assert monster.rect.bottom > monster._ground_y - 200
