"""Unit tests for FireWizard.apply_config()."""

import pygame as pg
import pytest

from src.game.entities.fire_wizard import FireWizard


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


def _make_wizard() -> FireWizard:
    player = MockPlayer()
    return FireWizard(200, 600, player, tier="boss", custom_scale=1.0, custom_health=100.0)  # type: ignore


def test_apply_config_updates_specified_keys():
    wizard = _make_wizard()
    original_stagnant = wizard._stagnant_duration

    wizard.apply_config({"max_mana": 150.0, "spell_mana_cost": 20.0})

    assert wizard._max_mana == 150.0
    assert wizard._spell_mana_cost == 20.0
    # Unspecified keys are left untouched
    assert wizard._stagnant_duration == original_stagnant


def test_apply_config_empty_dict_is_safe_noop():
    wizard = _make_wizard()
    before = {
        "max_mana": wizard._max_mana,
        "spell_mana_cost": wizard._spell_mana_cost,
        "teleport_dist_min": wizard._teleport_dist_min,
        "teleport_dist_max": wizard._teleport_dist_max,
        "spidey_sense": wizard._spidey_sense,
    }

    wizard.apply_config({})

    assert wizard._max_mana == before["max_mana"]
    assert wizard._spell_mana_cost == before["spell_mana_cost"]
    assert wizard._teleport_dist_min == before["teleport_dist_min"]
    assert wizard._teleport_dist_max == before["teleport_dist_max"]
    assert wizard._spidey_sense == before["spidey_sense"]


def test_apply_config_does_not_touch_mana():
    wizard = _make_wizard()
    wizard._mana = 12.34

    wizard.apply_config({"max_mana": 200.0})

    # apply_config() intentionally leaves _mana alone; callers resync it explicitly
    assert wizard._mana == 12.34
    assert wizard._max_mana == 200.0
