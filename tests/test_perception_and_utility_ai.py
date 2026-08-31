"""
Unit tests for Sensory Perception System, Squad Token Manager, and Utility Combat Engine.
"""

from unittest.mock import MagicMock
import pygame as pg

pg.init()
pg.display.set_mode((1280, 720), pg.NOFRAME)

from src.game.ai.perception_system import PerceptionSystem, AlertLevel
from src.game.ai.squad_token_manager import SquadTokenManager
from src.game.ai.utility_combat_engine import UtilityCombatEngine, TacticalAction


def test_perception_vision_cone_and_hearing():
    perception = PerceptionSystem(fov_angle=120.0, vision_range=500.0, hearing_range=300.0, reaction_delay_sec=0.0)
    enemy_rect = pg.Rect(500, 500, 40, 60)

    # Player in front of enemy (facing right, player to the right)
    player_mock = MagicMock()
    player_mock.is_dead = False
    player_mock.rect.centerx = 650
    player_mock.rect.centery = 500
    player_mock.is_attacking = False
    player_mock.is_running = False
    player_mock.is_landing = False

    alert = perception.update(0.1, enemy_rect, facing_left=False, player=player_mock)
    assert alert == AlertLevel.ENGAGED

    # Player behind enemy (facing right, player to the left) -> cannot see unless making sound
    player_mock.rect.centerx = 350
    perception.alert_level = AlertLevel.UNAWARE  # Reset alert state
    alert = perception.update(0.1, enemy_rect, facing_left=False, player=player_mock)
    assert alert == AlertLevel.UNAWARE

    # Player behind enemy makes loud sound (weapon attack) -> perceived via hearing
    player_mock.is_attacking = True
    alert = perception.update(0.3, enemy_rect, facing_left=False, player=player_mock)
    assert alert in (AlertLevel.SUSPICIOUS, AlertLevel.ALERT, AlertLevel.ENGAGED)


def test_squad_token_manager():
    manager = SquadTokenManager(max_simultaneous_attackers=2)
    manager.clear()

    e1_id = 101
    e2_id = 102
    e3_id = 103
    boss_id = 999

    manager.register_enemy(e1_id, "minion")
    manager.register_enemy(e2_id, "minion")
    manager.register_enemy(e3_id, "minion")
    manager.register_enemy(boss_id, "boss")

    # First two minions get tokens
    assert manager.request_attack_token(e1_id) is True
    assert manager.request_attack_token(e2_id) is True

    # Third minion is denied token (max 2 active)
    assert manager.request_attack_token(e3_id) is False

    # Boss always gets token regardless of limit
    assert manager.request_attack_token(boss_id) is True

    # Release token from e1 -> e3 can now acquire token
    manager.release_attack_token(e1_id)
    assert manager.request_attack_token(e3_id) is True


def test_utility_combat_engine_whiff_punishment_and_spacing():
    engine = UtilityCombatEngine(has_dash_evasion=False, has_block_anim=False, preferred_spacing=60.0)
    enemy_rect = pg.Rect(500, 500, 40, 60)

    player_mock = MagicMock()
    player_mock.is_dead = False
    player_mock.rect.centerx = 540
    player_mock.rect.centery = 500
    player_mock.is_attacking = False
    player_mock.is_recovering = True  # Player missed attack and is in recovery!

    # Whiff punishment evaluated
    action = engine.evaluate_action(enemy_rect, player_mock, can_attack=True, has_attack_token=True, dt_sec=0.016)
    assert action == TacticalAction.PUNISH_WHIFF

    # Player actively swinging at close range -> step back / retract spacing (no block animation!)
    player_mock.is_recovering = False
    player_mock.is_attacking = True
    engine.retract_chance = 1.0  # Force 100% retract evaluation for test

    action = engine.evaluate_action(enemy_rect, player_mock, can_attack=True, has_attack_token=True, dt_sec=0.016)
    assert action == TacticalAction.RETRACT_SPACING
