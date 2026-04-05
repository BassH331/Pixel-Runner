"""
Wiring Integration Tests
========================
These tests verify that all methods and attributes referenced by game objects
actually exist. They catch "AttributeError: ... has no attribute ..." bugs
BEFORE you need to run the full game.

Run with:  python -m pytest tests/test_wiring.py -v
"""

import os
import sys
import inspect
import unittest
from unittest.mock import MagicMock, patch

# Ensure project root is on the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# We MUST init pygame before importing anything that touches pg.display / pg.mixer
import pygame as pg
pg.init()
pg.display.set_mode((1280, 720))


# ─────────────────────────────────────────────────────────────────────────────
# Helper: stub AudioManager so no real sounds are needed
# ─────────────────────────────────────────────────────────────────────────────
def _make_mock_audio_manager():
    am = MagicMock()
    am.play_sound = MagicMock(return_value=0)
    am.play_music = MagicMock()
    am.stop_all_sounds = MagicMock()
    am.stop_sound = MagicMock()
    return am


def _make_mock_state_manager(audio_manager=None):
    mgr = MagicMock()
    mgr.audio_manager = audio_manager or _make_mock_audio_manager()
    return mgr


class TestPlayerWiring(unittest.TestCase):
    """Verify Player class has all methods/attributes its update() loop needs."""

    @classmethod
    def setUpClass(cls):
        """Create a Player instance with mocked audio."""
        from src.game.entities.player import Player
        cls.Player = Player
        cls.audio = _make_mock_audio_manager()
        # Patch AssetManager to return dummy surfaces
        with patch("v3x_zulfiqar_gideon.asset_manager.AssetManager.get_texture") as mock_tex:
            mock_tex.return_value = pg.Surface((32, 32))
            cls.player = Player(200, 600, cls.audio)

    def test_update_callable(self):
        """Player.update() should not raise AttributeError."""
        try:
            self.player.update(1.0 / 60.0)
        except AttributeError as e:
            self.fail(f"Player.update() raised AttributeError: {e}")

    def test_has_apply_gravity(self):
        self.assertTrue(callable(getattr(self.player, '_apply_gravity', None)),
                        "Player missing _apply_gravity()")

    def test_has_apply_movement(self):
        self.assertTrue(callable(getattr(self.player, '_apply_movement', None)),
                        "Player missing _apply_movement()")

    def test_has_update_state_logic(self):
        self.assertTrue(callable(getattr(self.player, '_update_state_logic', None)),
                        "Player missing _update_state_logic()")

    def test_has_update_defend_logic(self):
        self.assertTrue(callable(getattr(self.player, '_update_defend_logic', None)),
                        "Player missing _update_defend_logic()")

    def test_has_update_attack_audio(self):
        self.assertTrue(callable(getattr(self.player, '_update_attack_audio', None)),
                        "Player missing _update_attack_audio()")

    def test_has_get_current_config(self):
        self.assertTrue(callable(getattr(self.player, '_get_current_config', None)),
                        "Player missing _get_current_config()")

    def test_has_transition_to(self):
        self.assertTrue(callable(getattr(self.player, '_transition_to', None)),
                        "Player missing _transition_to()")

    def test_has_can_transition_to(self):
        self.assertTrue(callable(getattr(self.player, '_can_transition_to', None)),
                        "Player missing _can_transition_to()")

    def test_has_player_input(self):
        self.assertTrue(callable(getattr(self.player, 'player_input', None)),
                        "Player missing player_input()")

    def test_has_is_attacking_property(self):
        # Should not raise
        _ = self.player.is_attacking

    def test_has_is_dead_property(self):
        _ = self.player.is_dead

    def test_has_is_running_property(self):
        _ = self.player.is_running

    def test_has_is_invincible_property(self):
        _ = self.player.is_invincible

    def test_has_health_property(self):
        _ = self.player.health

    def test_has_max_health_property(self):
        _ = self.player.max_health

    def test_has_current_frame_index(self):
        _ = self.player.current_frame_index

    def test_has_direction_property(self):
        _ = self.player.direction

    def test_has_state_attribute(self):
        self.assertIsNotNone(self.player.state,
                             "Player.state should be set after init")

    def test_has_animations(self):
        self.assertIsInstance(self.player.animations, dict,
                             "Player.animations should be a dict")
        self.assertGreater(len(self.player.animations), 0,
                           "Player.animations should not be empty")

    def test_state_configs_match_animations(self):
        """Every state in animations must have a matching StateConfig."""
        for state in self.player.animations:
            self.assertIn(state, self.player.state_configs,
                          f"State {state} has animations but no StateConfig")

    def test_attack_methods(self):
        """Player combat interface methods should exist."""
        methods = [
            'should_deal_damage', 'get_attack_hitbox', 'try_register_hit',
            'get_current_attack_damage', 'get_attack_knockback',
            'get_attack_knockback_force', 'attack_thrust', 'attack_smash',
            'attack_power', 'defend', 'jump',
        ]
        for name in methods:
            self.assertTrue(callable(getattr(self.player, name, None)),
                            f"Player missing method: {name}()")

    def test_footstep_controller_api(self):
        """FootstepController should have try_play and reset."""
        fc = self.player._footsteps
        self.assertTrue(callable(getattr(fc, 'try_play', None)),
                        "FootstepController missing try_play()")
        self.assertTrue(callable(getattr(fc, 'reset', None)),
                        "FootstepController missing reset()")

    def test_take_damage(self):
        """take_damage should work without AttributeError."""
        try:
            self.player.take_damage(10)
        except AttributeError as e:
            self.fail(f"Player.take_damage() raised AttributeError: {e}")

    def test_reset(self):
        """reset() should work without AttributeError."""
        try:
            self.player.reset()
        except AttributeError as e:
            self.fail(f"Player.reset() raised AttributeError: {e}")


class TestSkeletonWiring(unittest.TestCase):
    """Verify Skeleton class has all methods GameState references."""

    @classmethod
    def setUpClass(cls):
        with patch("v3x_zulfiqar_gideon.asset_manager.AssetManager.get_texture") as mock_tex:
            mock_tex.return_value = pg.Surface((32, 32))
            from src.game.entities.player import Player
            cls.audio = _make_mock_audio_manager()
            cls.player = Player(200, 600, cls.audio)

            from src.game.entities.skeleton import Skeleton
            cls.Skeleton = Skeleton
            cls.skeleton = Skeleton(x=500, y=600, player=cls.player)

    def test_has_state(self):
        self.assertIsNotNone(self.skeleton.state)

    def test_has_should_deal_damage(self):
        self.assertTrue(callable(getattr(self.skeleton, 'should_deal_damage', None)))

    def test_has_get_attack_hitbox(self):
        self.assertTrue(callable(getattr(self.skeleton, 'get_attack_hitbox', None)))

    def test_has_register_hit(self):
        self.assertTrue(callable(getattr(self.skeleton, 'register_hit', None)))

    def test_has_get_current_attack_damage(self):
        self.assertTrue(callable(getattr(self.skeleton, 'get_current_attack_damage', None)))

    def test_has_get_current_attack_knockback(self):
        self.assertTrue(callable(getattr(self.skeleton, 'get_current_attack_knockback', None)))

    def test_has_take_damage(self):
        self.assertTrue(callable(getattr(self.skeleton, 'take_damage', None)))

    def test_has_is_dead(self):
        _ = self.skeleton.is_dead

    def test_has_entity_id(self):
        _ = self.skeleton.entity_id

    def test_has_is_in_hit_frame(self):
        self.assertTrue(callable(getattr(self.skeleton, 'is_in_hit_frame', None)))

    def test_has_current_frame_index(self):
        _ = self.skeleton.current_frame_index


class TestGameStateWiring(unittest.TestCase):
    """Verify GameState initializes and key methods exist."""

    @classmethod
    def setUpClass(cls):
        with patch("v3x_zulfiqar_gideon.asset_manager.AssetManager.get_texture") as mock_tex, \
             patch("v3x_zulfiqar_gideon.asset_manager.AssetManager.get_sound") as mock_snd:
            mock_tex.return_value = pg.Surface((32, 32))
            mock_snd.return_value = None
            from src.game.states.game_state import GameState
            cls.GameState = GameState
            mgr = _make_mock_state_manager()
            try:
                cls.game_state = GameState(mgr)
                cls.init_error = None
            except Exception as e:
                cls.game_state = None
                cls.init_error = e

    def test_init_succeeds(self):
        if self.init_error:
            self.fail(f"GameState.__init__() raised: {self.init_error}")

    def test_has_update(self):
        if self.game_state:
            self.assertTrue(callable(getattr(self.game_state, 'update', None)))

    def test_has_draw(self):
        if self.game_state:
            self.assertTrue(callable(getattr(self.game_state, 'draw', None)))

    def test_has_handle_event(self):
        if self.game_state:
            self.assertTrue(callable(getattr(self.game_state, 'handle_event', None)))

    def test_has_on_enter(self):
        if self.game_state:
            self.assertTrue(callable(getattr(self.game_state, 'on_enter', None)))

    def test_has_spawn_zones_from_json(self):
        """Spawn zones should be loaded from JSON or use defaults."""
        if self.game_state:
            zone = self.game_state._get_spawn_zone()
            self.assertIn('max_skeletons', zone)
            self.assertIn('delay', zone)

    def test_has_bat_spawn_config(self):
        """Bat spawn counts should be configured."""
        if self.game_state:
            self.assertIsInstance(self.game_state._bat_min_count, int)
            self.assertIsInstance(self.game_state._bat_max_count, int)

    def test_has_level_name(self):
        if self.game_state:
            self.assertIsInstance(self.game_state._level_name, str)

    def test_has_level_end_distance(self):
        if self.game_state:
            self.assertIsInstance(self.game_state._level_end_distance, float)


class TestStoryStateWiring(unittest.TestCase):
    """Verify StoryState initializes correctly."""

    @classmethod
    def setUpClass(cls):
        with patch("v3x_zulfiqar_gideon.asset_manager.AssetManager.get_texture") as mock_tex, \
             patch("v3x_zulfiqar_gideon.asset_manager.AssetManager.get_sound") as mock_snd, \
             patch("v3x_zulfiqar_gideon.asset_manager.AssetManager.get_font") as mock_font, \
             patch("pygame.image.load") as mock_load:
            mock_tex.return_value = pg.Surface((32, 32))
            mock_snd.return_value = None
            mock_font.return_value = pg.font.Font(None, 20)
            mock_img = pg.Surface((1280, 720))
            mock_img_conv = MagicMock()
            mock_img_conv.get_size.return_value = (1280, 720)
            mock_img_conv.convert.return_value = mock_img_conv
            mock_load.return_value = mock_img_conv
            from src.game.states.story_state import StoryState
            mgr = _make_mock_state_manager()
            try:
                cls.story_state = StoryState(mgr)
                cls.init_error = None
            except Exception as e:
                cls.story_state = None
                cls.init_error = e

    def test_init_succeeds(self):
        if self.init_error:
            self.fail(f"StoryState.__init__() raised: {self.init_error}")

    def test_has_update(self):
        if self.story_state:
            self.assertTrue(callable(getattr(self.story_state, 'update', None)))

    def test_has_draw(self):
        if self.story_state:
            self.assertTrue(callable(getattr(self.story_state, 'draw', None)))

    def test_has_black_overlay(self):
        """The fade-to-black overlay should exist."""
        if self.story_state:
            self.assertIsNotNone(getattr(self.story_state, '_black_overlay', None))


if __name__ == "__main__":
    unittest.main()
