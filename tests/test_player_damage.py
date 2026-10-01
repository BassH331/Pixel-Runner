"""
Unit test for GAME-01 defend state damage reduction math.
"""
import pytest
import pygame as pg

pg.init()
pg.display.set_mode((1, 1), pg.NOFRAME)

from src.game.entities.player import Player, PlayerState


def test_player_defend_damage_reduction_small_attacks():
    """Verify that defending against small damage attacks (1.0, 2.0, 3.0) reduces health by 1 point instead of 0."""
    player = Player(x=100, y=100, audio_manager=None)
    
    # Set to DEFEND state
    player.set_state(PlayerState.DEFEND, force=True)
    initial_health = player.health
    
    # 1. Take 1.0 damage while defending
    result = player.take_damage(1.0)
    assert result is True
    assert player.health == initial_health - 1

    # 2. Take 2.0 damage while defending
    initial_health = player.health
    player.take_damage(2.0)
    assert player.health == initial_health - 1

    # 3. Take 3.0 damage while defending
    initial_health = player.health
    player.take_damage(3.0)
    assert player.health == initial_health - 1


def test_player_defend_damage_reduction_large_attacks():
    """Verify that defending against large damage attacks (10.0) reduces damage by 70% (takes 3 damage)."""
    player = Player(x=100, y=100, audio_manager=None)
    player.set_state(PlayerState.DEFEND, force=True)
    initial_health = player.health
    
    player.take_damage(10.0)
    assert player.health == initial_health - 3


def test_player_undefended_damage():
    """Verify that undefended state takes full damage."""
    player = Player(x=100, y=100, audio_manager=None)
    player.state = PlayerState.IDLE
    initial_health = player.health
    
    player.take_damage(2.0)
    assert player.health == initial_health - 2
