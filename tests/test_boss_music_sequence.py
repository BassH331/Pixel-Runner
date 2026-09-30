import os
import json
import unittest
from unittest.mock import MagicMock, patch
import pygame as pg

from v3x_zulfiqar_gideon import UITheme
from src.game.audio.audio_lock import verify_config_integrity
from v3x_zulfiqar_gideon.audio_manager import AudioManager
from v3x_zulfiqar_gideon.event_bus import EntityDied


class TestBossMusicSequence(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not pg.mixer.get_init():
            pg.mixer.pre_init(frequency=44100, size=-16, channels=2, buffer=2048)
            pg.mixer.init()
        if not pg.display.get_surface():
            pg.display.set_mode((1280, 720), pg.NOFRAME)

        UITheme.configure_buttons(
            assets={
                "big": ("dummy_big", "dummy_big_p"),
                "medium": ("dummy_med", "dummy_med_p"),
                "cancel": ("dummy_cancel", "dummy_cancel_p"),
                "new_start": ("dummy_new", "dummy_new_p"),
            },
            font_path="dummy_font"
        )
        UITheme.configure_notifications(
            banner_path="dummy_banner",
            icons={"gray": "dummy_gray", "red": "dummy_red", "yellow": "dummy_yellow"},
            font_path="dummy_font"
        )
        UITheme.configure_overlays(
            stone_path="dummy_stone",
            parchment_path="dummy_parchment",
            title_font_path="dummy_font",
            body_font_path="dummy_font",
            prompt_font_path="dummy_font"
        )

    def test_master_audio_config_contains_boss_music_sequence(self):
        config_path = "game_data/master_audio_config.json"
        lock_path = "game_data/master_audio_config.lock"

        self.assertTrue(os.path.exists(config_path))
        self.assertTrue(os.path.exists(lock_path))

        with open(config_path, "r") as f:
            config = json.load(f)

        self.assertIn("boss_music_sequence", config)
        self.assertIsInstance(config["boss_music_sequence"], list)
        self.assertGreaterEqual(len(config["boss_music_sequence"]), 2)
        self.assertEqual(config["boss_music_sequence"][0], "game_loop")
        self.assertEqual(config["boss_music_sequence"][1], "game_loop_2")

        # Verify lockfile hash validation
        is_valid, reason = verify_config_integrity(config_path, lock_path)
        self.assertTrue(is_valid, f"Integrity check failed: {reason}")

    def test_game_state_boss_defeat_music_transition(self):
        # Create dummy AudioManager with master config
        audio_mgr = AudioManager()
        audio_mgr.master_audio_config = {
            "sounds": {
                "game_loop": "assets/audio/Combat Pack - vol 1/2. One Last Day on Earth - 110bpm - LOOP 52s.wav",
                "game_loop_2": "assets/audio/Combat Pack - vol 1/2. One Last Day on Earth - 110bpm - LONG LOOP 1min44s.wav"
            },
            "boss_music_sequence": [
                "game_loop",
                "game_loop_2"
            ]
        }
        audio_mgr.play_music = MagicMock()

        # Create mock state manager
        manager = MagicMock()
        manager.audio_manager = audio_mgr

        # Import GameState and initialize with mock manager
        with patch("src.game.states.game_state.pg.font.Font"), \
             patch("src.game.states.game_state.pg.font.SysFont"), \
             patch("src.game.states.game_state.AssetManager"):
            from src.game.states.game_state import GameState
            game_state = GameState(manager)
            game_state.on_enter()

            # Verify initial track played on enter
            self.assertEqual(game_state._current_bg_music_track, "game_loop")
            self.assertEqual(game_state._boss_defeat_count, 0)
            audio_mgr.play_music.assert_called_with("game_loop", loop=True)

            # Reset call mock and simulate mini-boss defeat event
            audio_mgr.play_music.reset_mock()
            boss_enemy = MagicMock()
            setattr(boss_enemy, "tier", "mini_boss")
            setattr(boss_enemy, "boss_title", "Gatekeeper Mini-Boss")
            event = EntityDied(entity=boss_enemy, soul_value=100, is_boss=True)

            game_state._on_entity_died(event)

            # Assert boss defeat count incremented and music track switched to game_loop_2
            self.assertEqual(game_state._boss_defeat_count, 1)
            self.assertEqual(game_state._current_bg_music_track, "game_loop_2")
            audio_mgr.play_music.assert_called_with("game_loop_2", loop=True)


if __name__ == "__main__":
    unittest.main()
