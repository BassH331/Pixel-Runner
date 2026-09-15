"""
Unit tests for LightningEffect module.
"""
import pytest
import pygame as pg

pg.init()
pg.display.set_mode((1, 1), pg.NOFRAME)

from src.game.effects.lightning_effect import LightningEffect


def test_lightning_effect_initialization():
    effect = LightningEffect.get_instance()
    assert effect.active is False
    assert effect.timer == 0.0


def test_lightning_effect_trigger_and_decay():
    effect = LightningEffect.get_instance()
    effect.trigger(duration=1.0, staff_pos=(400, 500))

    assert effect.active is True
    assert effect.timer == 1.0
    assert len(effect.bolt_points) > 0

    # Halfway through 1.0s duration
    effect.update(0.5)
    assert effect.active is True
    assert effect.timer == 0.5

    # Complete 1.0s duration
    effect.update(0.6)
    assert effect.active is False
    assert effect.timer == 0.0
    assert len(effect.bolt_points) == 0


def test_lightning_effect_render():
    surface = pg.Surface((800, 600), pg.SRCALPHA)
    effect = LightningEffect.get_instance()
    effect.trigger(duration=1.0)
    
    # Render should succeed cleanly without audio calls
    effect.render(surface)
    assert effect.active is True
