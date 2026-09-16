"""
Unit tests for BloodZombie AI behavior, attack triggering in close range,
and metadata/telemetry structure tracking.
"""

from unittest.mock import MagicMock
import pygame as pg

from src.game.entities.bloo_zombie import BloodZombie, BloodZombieState
from src.game.ai import SquadTokenManager


def setup_module():
    if not pg.display.get_init():
        pg.init()
        pg.display.set_mode((800, 600))


def test_blood_zombie_metadata_and_telemetry():
    """Verify that get_metadata() and get_telemetry() return rich structured dicts."""
    player_mock = MagicMock()
    player_mock.rect = pg.Rect(500, 300, 40, 60)
    player_mock.is_dead = False
    player_mock.facing_left = False
    player_mock.is_attacking = False
    player_mock.is_recovering = False

    zombie = BloodZombie(x=400, y=300, player=player_mock, tier="boss")
    
    metadata = zombie.get_metadata()
    assert isinstance(metadata, dict)
    assert metadata["entity_type"] == "blood_zombie"
    assert metadata["tier"] == "boss"
    assert "health" in metadata
    assert "position" in metadata
    assert "perception" in metadata
    assert "tactics" in metadata
    assert "combat_stats" in metadata
    assert metadata["combat_stats"]["attack_count"] == 0

    telemetry = zombie.get_telemetry()
    assert telemetry == metadata


def test_blood_zombie_attacks_when_in_range():
    """Verify that when close and in range, BloodZombie triggers an attack instead of walking away."""
    SquadTokenManager.get_instance().clear()

    player_mock = MagicMock()
    player_mock.rect = pg.Rect(450, 240, 40, 60)
    player_mock.is_dead = False
    player_mock.facing_left = False
    player_mock.is_attacking = False
    player_mock.is_recovering = False

    # Spawn zombie right next to player (within attack range)
    zombie = BloodZombie(x=400, y=300, player=player_mock, tier="boss")
    
    # Pre-engage perception with filled reaction timer
    zombie.perception.alert_level = zombie.perception.alert_level.ENGAGED
    zombie.perception._reaction_timer = 0.5

    # Update AI step
    zombie._update_ai(0.016)

    # Zombie should enter ATTACK state and increment attack_count
    assert zombie.state == BloodZombieState.ATTACK
    assert zombie.attack_count == 1
    assert zombie.facing_left == False  # Player is to the right (x=450 vs x=400)
