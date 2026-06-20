import os
import sys
import unittest
from unittest.mock import MagicMock

# Ensure project root is on the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pygame as pg
pg.init()
pg.display.set_mode((1280, 720))

from src.game.entities.player import Player, PlayerState

def _make_mock_audio_manager():
    am = MagicMock()
    am.play_sound = MagicMock(return_value=0)
    am.play_music = MagicMock()
    am.stop_all_sounds = MagicMock()
    am.stop_sound = MagicMock()
    return am

class TestPlayerMoves(unittest.TestCase):
    def setUp(self):
        self.audio = _make_mock_audio_manager()
        self.player = Player(200, 600, self.audio)

    def test_roll_trigger(self):
        # Set state to IDLE
        self.player.set_state(PlayerState.IDLE, force=True)
        # Should be allowed to transition to ROLL
        success = self.player.roll()
        self.assertTrue(success)
        self.assertEqual(self.player.state, PlayerState.ROLL)
        self.assertTrue(self.player.is_invincible)

    def test_dash_trigger(self):
        self.player.set_state(PlayerState.IDLE, force=True)
        success = self.player.dash()
        self.assertTrue(success)
        self.assertEqual(self.player.state, PlayerState.DASH)
        # Dash does not grant invincibility by default
        self.assertFalse(self.player.is_invincible)

    def test_special_attack_trigger(self):
        self.player.set_state(PlayerState.IDLE, force=True)
        success = self.player.special_attack()
        self.assertTrue(success)
        self.assertEqual(self.player.state, PlayerState.SPECIAL_ATTACK)
        self.assertTrue(self.player.is_invincible)
        self.assertEqual(self.player._current_attack_config, Player.SPECIAL_ATTACK_CONFIG)

    def test_transform_enhanced_flow(self):
        self.player.set_state(PlayerState.IDLE, force=True)
        self.assertFalse(self.player._is_enhanced)
        
        # Start transformation
        success = self.player.transform()
        self.assertTrue(success)
        self.assertEqual(self.player.state, PlayerState.TRANSFORM)
        self.assertTrue(self.player.is_invincible)

        # Simulating completion of TRANSFORM animation by transitioning to IDLE (needs force=True because TRANSFORM is uninterruptible)
        self.player.set_state(PlayerState.IDLE, force=True)
        # Verify it toggled _is_enhanced
        self.assertTrue(self.player._is_enhanced)

        # Scale factor check
        # When enhanced, get_current_attack_damage should be scaled (SPECIAL_ATTACK_CONFIG base is 35.0)
        self.player.attack_state.begin(Player.SPECIAL_ATTACK_CONFIG)
        self.assertEqual(self.player.get_current_attack_damage(), 52.5)

        # Special attack should use ENHANCED_SPECIAL_ATTACK_CONFIG now
        self.player.set_state(PlayerState.IDLE, force=True)
        self.player.special_attack()
        self.assertEqual(self.player._current_attack_config, Player.ENHANCED_SPECIAL_ATTACK_CONFIG)

        # Transform again to toggle back to normal
        self.player.set_state(PlayerState.IDLE, force=True)
        self.player.transform()
        self.player.set_state(PlayerState.IDLE, force=True)
        self.assertFalse(self.player._is_enhanced)

    def test_movement_displacement(self):
        # Roll movement
        self.player.set_state(PlayerState.ROLL, force=True)
        self.player.facing_left = False
        start_x = self.player.rect.x
        self.player._apply_movement()
        self.assertEqual(self.player.rect.x, start_x + 8) # int(8.5)

        # Dash movement (facing left)
        self.player.set_state(PlayerState.DASH, force=True)
        self.player.facing_left = True
        start_x = self.player.rect.x
        self.player._apply_movement()
        self.assertEqual(self.player.rect.x, start_x - 14)
