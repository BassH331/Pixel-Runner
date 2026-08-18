from unittest.mock import MagicMock
import pygame as pg

pg.init()
pg.display.set_mode((1280, 720), pg.NOFRAME)

from src.game.entities.dark_ronin import DarkRonin, DarkRoninState


def test_dark_ronin_initialization():
    player_mock = MagicMock()
    ronin = DarkRonin(500, 600, player_mock)

    assert ronin.health == 35.0
    assert ronin._state == DarkRoninState.IDLE
    assert not ronin.is_invincible
    assert ronin.rect.bottom == 609


def test_dark_ronin_chase_and_attack_state():
    player_mock = MagicMock()
    p_sprite = MagicMock()
    p_sprite.rect.centerx = 540  # Within 65px melee range
    player_mock.sprite = p_sprite

    ronin = DarkRonin(500, 600, player_mock)

    # Within melee range -> transition to ATTACK state
    ronin.update(16.67)
    assert ronin._state == DarkRoninState.ATTACK


def test_dark_ronin_dash_strike_trigger():
    player_mock = MagicMock()
    p_sprite = MagicMock()
    p_sprite.rect.centerx = 700  # 200px distance -> triggers high-speed dash strike
    p_sprite.direction = 1
    player_mock.sprite = p_sprite

    ronin = DarkRonin(500, 600, player_mock)
    ronin.update(16.67)

    # Should enter DASH_STRIKE state
    assert ronin._state == DarkRoninState.DASH_STRIKE


def test_dark_ronin_take_damage_and_death():
    player_mock = MagicMock()
    ronin = DarkRonin(500, 600, player_mock)

    # Take damage (not dead yet)
    damaged = ronin.take_damage(15.0)
    assert damaged
    assert ronin.health == 20.0
    assert ronin._state == DarkRoninState.HURT

    # Fatal damage -> DEATH state
    ronin.take_damage(25.0)
    assert ronin.health == 0.0
    assert ronin._state == DarkRoninState.DEATH
