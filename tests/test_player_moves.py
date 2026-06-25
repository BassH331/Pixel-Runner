import os
import sys
import unittest
from unittest.mock import MagicMock

# Ensure project root is on the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pygame as pg

def _ensure_pygame_init():
    if not pg.get_init():
        pg.init()
    if not pg.font.get_init():
        pg.font.init()
    if not pg.display.get_init() or pg.display.get_surface() is None:
        pg.display.init()
        pg.display.set_mode((1280, 720))

_ensure_pygame_init()

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
        _ensure_pygame_init()
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
        self.assertEqual(self.player._current_attack_config, self.player.special_attack_config)

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
        self.player.attack_state.begin(self.player.special_attack_config)
        self.assertEqual(self.player.get_current_attack_damage(), 52.5)

        # Special attack should use ENHANCED_SPECIAL_ATTACK_CONFIG now
        self.player.set_state(PlayerState.IDLE, force=True)
        self.player.special_attack()
        self.assertEqual(self.player._current_attack_config, self.player.enhanced_special_attack_config)

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

    def test_attack_zeroes_direction(self):
        """Entering an attack state must clear _direction to prevent drift."""
        self.player.set_state(PlayerState.IDLE, force=True)
        self.player._direction = 1  # Simulate moving right
        self.player.attack_thrust()
        self.assertEqual(self.player._direction, 0)

    def test_no_drift_during_attack(self):
        """Holding movement keys during a non-hit attack frame must not move the player."""
        self.player.set_state(PlayerState.IDLE, force=True)
        self.player.attack_thrust()

        # Force animation to a non-hit frame (frame 0 = startup)
        self.player.animation_index = 0.0
        self.player.attack_state.update(0)

        self.player._direction = 1  # Simulate holding right
        start_x = self.player.rect.x
        self.player._apply_movement()
        self.assertEqual(self.player.rect.x, start_x,
                         "Player must not drift during attack non-hit frames")

    def test_attack_sway_on_hit_frames(self):
        """Active hit frames should apply a small forward sway, not full movement."""
        self.player.set_state(PlayerState.IDLE, force=True)
        self.player.facing_left = False
        self.player.attack_thrust()

        # Advance to a known hit frame (frame 2 for thrust)
        self.player.animation_index = 2.0
        self.player.attack_state.update(2)

        start_x = self.player.rect.x
        self.player._apply_movement()

        # Should move by int(0.8) = 0 per frame (sub-pixel, rounds to 0)
        # The sway is subtle — verify it doesn't move at full speed
        delta = self.player.rect.x - start_x
        self.assertLessEqual(abs(delta), 1,
                             "Attack sway should be tiny, not full movement speed")

    def test_ground_attack_requires_grounded(self):
        """Ground attacks (thrust, smash, power) must fail while airborne."""
        self.player.set_state(PlayerState.IDLE, force=True)

        # Put player in the air
        self.player.rect.bottom = self.player._ground_y - 100

        self.assertFalse(self.player.attack_thrust(),
                         "Thrust should fail while airborne")
        self.assertFalse(self.player.attack_smash(),
                         "Smash should fail while airborne")
        self.assertFalse(self.player.attack_power(),
                         "Power should fail while airborne")

        # Special attack should still work airborne
        self.assertTrue(self.player.special_attack(),
                        "Special attack should be allowed while airborne")

    def test_ground_attack_succeeds_on_ground(self):
        """Ground attacks should succeed when player is on the ground."""
        self.player.set_state(PlayerState.IDLE, force=True)
        # Ensure player is grounded
        self.player.rect.bottom = self.player._ground_y

        self.assertTrue(self.player.attack_thrust(),
                        "Thrust should succeed on ground")
