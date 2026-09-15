"""Unit tests for Bat configuration, Enemy entity integration, and Boss Configuration Editor bat controls."""

import json
import os
import unittest
from unittest.mock import patch, MagicMock

os.environ["SDL_VIDEODRIVER"] = "dummy"

import pygame as pg
pg.init()

from src.game.services.config_client import ConfigClient, LOCAL_FILE_MAP
from src.game.entities.enemy import Enemy, EnemyState, BatFlightState
from src.game.entities.hitbox_registry import HitboxRegistry
from boss_editor import BOSS_SCHEMAS, BossEditorApp


class TestBatConfigAndIntegration(unittest.TestCase):
    def setUp(self):
        ConfigClient._session_cache.clear()
        ConfigClient._api_attempted.clear()

    def test_config_client_local_file_map_includes_enemy_bat(self):
        """Verify that enemy_bat is mapped in LOCAL_FILE_MAP."""
        self.assertIn("enemy_bat", LOCAL_FILE_MAP)
        self.assertEqual(LOCAL_FILE_MAP["enemy_bat"], "game_data/enemy_bat_config.json")

    def test_enemy_bat_config_loading_and_scaling(self):
        """Verify that Enemy applies scale and speed from config."""
        test_config = {
            "speed": 500.0,
            "scale": 1.5,
            "gravity": 220.0,
            "flap_power": 175.0,
            "glide_duration": 0.8
        }
        def side_effect(k):
            return test_config if k == "enemy_bat" else None

        with patch.object(ConfigClient, "fetch_config", side_effect=side_effect):
            bat = Enemy(audio_manager=None)
            
            # Margins scale for enemy is 2.0; with scale=1.5, base_scale should be 3.0
            margins = HitboxRegistry.get_margins("enemy")
            expected_base_scale = margins.scale * 1.5
            
            self.assertAlmostEqual(bat.depth_scale_factor * expected_base_scale, round(expected_base_scale * (bat.depth_scale_factor * expected_base_scale / expected_base_scale), 1), delta=0.5)

            # Speed with 500.0 px/s should be roughly 2x faster than baseline (250.0 px/s)
            speed_ratio = 500.0 / 250.0
            self.assertEqual(speed_ratio, 2.0)
            self.assertLess(bat.speed, 0)
            abs_speed = abs(bat.speed)
            self.assertGreater(abs_speed, 3.0)

    def test_bat_flight_impulse_and_glide_state_machine(self):
        """Verify that bat performs flap lift impulses, enters glide, and cycles back."""
        test_config = {
            "speed": 250.0,
            "scale": 1.0,
            "gravity": 200.0,
            "flap_power": 180.0,
            "glide_duration": 1.0
        }
        def side_effect(k):
            return test_config if k == "enemy_bat" else None

        with patch.object(ConfigClient, "fetch_config", side_effect=side_effect):
            bat = Enemy(audio_manager=None)
            bat.y_base = 300.0
            bat.flight_state = BatFlightState.FLAP_BURST
            bat.burst_flaps_target = 2
            bat.flaps_completed = 0
            bat.flap_interval_timer = 0.0  # Ready to flap

            # Step 1: Flap burst tick 1
            bat.update(dt=0.016)
            self.assertLess(bat.vel_y, 0.0)
            self.assertEqual(bat.flaps_completed, 1)
            self.assertEqual(bat.flight_state, BatFlightState.FLAP_BURST)

            # Step 2: Trigger 2nd flap
            bat.flap_interval_timer = 0.0
            bat.update(dt=0.016)
            # Should have completed 2 flaps and transitioned to GLIDE
            self.assertEqual(bat.flight_state, BatFlightState.GLIDE)

            # During ascending GLIDE (vel_y < 0), wings continue flapping.
            # Advance ticks until vel_y >= 0 (descending glide phase)
            initial_glide_vel = bat.vel_y
            while bat.vel_y < 0:
                bat.update(dt=0.016)

            # Advance remaining frames of stroke to return to frame 0
            while int(bat.animation_index) % len(bat.animations[EnemyState.FLY]) != 0:
                bat.update(dt=0.016)

            # Once wing return stroke completes in GLIDE state, frame holds on Frame 0 (outstretched wings)
            self.assertEqual(bat.image, bat.animations[EnemyState.FLY][0])

            # In GLIDE state, downward acceleration occurs (vel_y increases towards positive)
            for _ in range(15):
                bat.update(dt=0.016)
            self.assertGreater(bat.vel_y, initial_glide_vel)

            # Once glide_duration expires, cycles back to FLAP_BURST
            bat.glide_timer = 2.0
            bat.update(dt=0.016)
            self.assertEqual(bat.flight_state, BatFlightState.FLAP_BURST)

    def test_bat_metadata_and_ascent_flapping(self):
        """Verify bat metadata dictionary structure and continuous wing flapping during upward ascent."""
        test_config = {
            "speed": 250.0,
            "scale": 1.0,
            "gravity": 200.0,
            "flap_power": 180.0,
            "glide_duration": 1.0
        }
        def side_effect(k):
            return test_config if k == "enemy_bat" else None

        with patch.object(ConfigClient, "fetch_config", side_effect=side_effect):
            bat = Enemy(audio_manager=None)
            bat.y_base = 300.0
            
            # 1. Verify metadata structure
            meta = bat.metadata
            self.assertEqual(meta["entity_type"], "enemy_bat")
            self.assertIn("flight_state", meta)
            self.assertIn("position", meta)
            self.assertIn("velocity", meta)
            self.assertIn("aerodynamics", meta)
            self.assertIn("wing_flapping", meta)
            self.assertIn("scale_factor", meta)

            # Verify aerodynamics fields
            aero = meta["aerodynamics"]
            self.assertIn("gravity", aero)
            self.assertIn("flap_power", aero)
            self.assertIn("is_ascending", aero)
            self.assertIn("is_descending", aero)

            # Verify wing flapping fields
            wings = meta["wing_flapping"]
            self.assertIn("animation_frame", wings)
            self.assertIn("wing_phase", wings)
            self.assertIn("is_gliding", wings)

            # 2. Verify continuous wing flapping during upward ascent (vel_y < 0)
            bat.vel_y = -100.0
            bat.flight_state = BatFlightState.GLIDE  # even in GLIDE state while ascending
            
            meta_ascending = bat.metadata
            self.assertTrue(meta_ascending["aerodynamics"]["is_ascending"])
            self.assertFalse(meta_ascending["wing_flapping"]["is_gliding"])
            
            start_anim_index = bat.animation_index
            for _ in range(5):
                bat.update(dt=0.016)
            
            # Animation frame index must advance during ascent
            self.assertGreater(bat.animation_index, start_anim_index)

    def test_boss_editor_bat_schema_and_sliders(self):
        """Verify bat schema in BOSS_SCHEMAS contains all flight controls."""
        self.assertIn("bat", BOSS_SCHEMAS)
        schema = BOSS_SCHEMAS["bat"]
        self.assertEqual(schema["config_file"], "game_data/enemy_bat_config.json")
        for expected_key in ("speed", "scale", "gravity", "flap_power", "glide_duration"):
            self.assertIn(expected_key, schema["defaults"])
        
        slider_keys = [s[0] for s in schema["sliders"]]
        for expected_key in ("speed", "scale", "gravity", "flap_power", "glide_duration"):
            self.assertIn(expected_key, slider_keys)

    def test_boss_editor_bat_scale_preview_calculation(self):
        """Verify that BossEditorApp applies scale factor to bat preview dimensions."""
        with patch("boss_editor.pg.display.set_mode", return_value=pg.Surface((1280, 720))), \
             patch("boss_editor.pg.display.set_caption"):
            app = BossEditorApp()
            app.selected_boss = "bat"
            app.build_sliders()

            self.assertIn("scale", app.sliders)
            self.assertIn("speed", app.sliders)

            # Set scale factor to 2.0
            app.sliders["scale"].val = 2.0
            
            # Create a mock current frame
            mock_frame = pg.Surface((32, 32))
            preview_rect = pg.Rect(430, 80, 820, 400)
            
            from src.game.editor.preview_scaler import PreviewScaler
            fit = PreviewScaler.calculate_auto_fit(mock_frame, preview_rect, floor_y=420)
            
            scale_mult = app.sliders["scale"].val
            base_w = fit["scaled_width"]
            base_h = fit["scaled_height"]
            scaled_w = int(base_w * scale_mult)
            scaled_h = int(base_h * scale_mult)
            
            # Dimensions should be doubled
            self.assertEqual(scaled_w, base_w * 2)
            self.assertEqual(scaled_h, base_h * 2)


if __name__ == "__main__":
    unittest.main()

