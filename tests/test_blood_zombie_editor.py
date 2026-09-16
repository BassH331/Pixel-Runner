"""
test_blood_zombie_editor.py
Unit tests for the Blood Zombie High-Engine Laboratory Plugin (blood_zombie_editor.py).
"""

import os
import json
import unittest
from unittest.mock import patch, MagicMock

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

import pygame as pg
pg.init()

from blood_zombie_editor import (
    BloodZombieEditorApp,
    MetaphorSlider,
    Button,
    BloodParticle,
)


class TestBloodZombieEditorPlugin(unittest.TestCase):
    def setUp(self):
        # Instantiate App in dummy SDL mode
        self.app = BloodZombieEditorApp()

    def test_editor_app_initialization(self):
        """Verify app loads sliders, animations, buttons, and modes correctly."""
        self.assertIsNotNone(self.app.sliders)
        self.assertIn("anim_speed", self.app.sliders)
        self.assertIn("max_health", self.app.sliders)
        self.assertIn("blood_spray_pressure", self.app.sliders)
        self.assertIn("frame_offset_x", self.app.sliders)
        self.assertEqual(self.app.mode, "ANIMATION")

    def test_slider_metaphors_and_technical_formulas(self):
        """Verify sliders contain correct metaphor labels and physics formulas."""
        slider = self.app.sliders["anim_speed"]
        self.assertEqual(slider.metaphor_label, "Cardiac Pulse Tempo")
        self.assertIn("dt", slider.formula)

        slider_visc = self.app.sliders["lerp_viscosity"]
        self.assertEqual(slider_visc.metaphor_label, "Viscous Rheology")

        slider_reach = self.app.sliders["attack_range"]
        self.assertEqual(slider_reach.metaphor_label, "Carnivorous Reach")

    def test_per_frame_pivot_offsets(self):
        """Verify per-frame X,Y pivot nudging and offset dictionary state."""
        self.app.select_anim("Attack1")
        self.app.frame_index = 6.0
        self.app.set_current_frame_offset(12, -8)

        dx, dy = self.app.get_current_frame_offset()
        self.assertEqual(dx, 12)
        self.assertEqual(dy, -8)
        self.assertIn("Attack1", self.app.frame_offsets)
        self.assertEqual(self.app.frame_offsets["Attack1"]["6"]["dx"], 12)

    def test_stagnant_player_dummy_reaction(self):
        """Verify stagnant player dummy exists and responds to attack hit impact."""
        self.assertTrue(self.app.show_stagnant_player)
        self.assertIsNotNone(self.app.player_stand_sprite)
        self.assertIsNotNone(self.app.player_hurt_sprite)

        # Trigger impact frame on Attack1 frame 6 with precise frame timestep
        self.app.select_anim("Attack1")
        self.app.frame_index = 6.0
        self.app.last_played_frame = -1
        self.app.update(0.01)

        # Player hurt reaction timer should be active
        self.assertGreater(self.app.player_hurt_timer, 0.0)

    def test_onion_skinning_ghost_frames(self):
        """Verify onion skinning ghost frame toggle and alpha opacity."""
        self.assertTrue(self.app.show_onion_skin)
        self.assertIn("onion_skin_alpha", self.app.sliders)
        self.assertEqual(self.app.sliders["onion_skin_alpha"].val, 0.35)

    def test_preset_application(self):
        """Verify applying presets updates slider metrics correctly."""
        self.app.apply_preset("berserker")
        self.assertEqual(self.app.sliders["max_health"].val, 80.0)
        self.assertEqual(self.app.sliders["speed"].val, 4.5)
        self.assertEqual(self.app.sliders["blood_spray_pressure"].val, 45)

        self.app.apply_preset("boss_default")
        self.assertEqual(self.app.sliders["max_health"].val, 50.0)

    def test_mode_switching(self):
        """Verify laboratory modes switch between ANIMATION, COMBAT_METRICS, and SIMULATOR."""
        self.app.set_mode("COMBAT_METRICS")
        self.assertEqual(self.app.mode, "COMBAT_METRICS")

        self.app.set_mode("SIMULATOR")
        self.assertEqual(self.app.mode, "SIMULATOR")

    def test_timeline_scrubbing_and_playback(self):
        """Verify frame transport controls and animation step forward/backward."""
        self.app.select_anim("Attack1")
        self.assertEqual(self.app.current_anim_state, "Attack1")

        self.app.step_frame_forward()
        self.assertEqual(self.app.frame_index, 1.0)

        self.app.step_frame_backward()
        self.assertEqual(self.app.frame_index, 0.0)

    def test_particle_emitter_burst(self):
        """Verify arterial blood particle bursts create blood droplets."""
        self.app.particles.clear()
        self.app.spawn_blood_burst(100, 100, count=10)
        self.assertGreater(len(self.app.particles), 0)

        # Update particle
        p = self.app.particles[0]
        initial_life = p.life
        p.update(0.1)
        self.assertLess(p.life, initial_life)

    def test_config_save_simulation(self):
        """Verify config saving writes valid JSON payload including frame_offsets."""
        test_file = "scratch/test_blood_zombie_config.json"
        os.makedirs("scratch", exist_ok=True)
        self.app.config_path = test_file

        self.app.sliders["max_health"].val = 77.5
        self.app.select_anim("Attack1")
        self.app.frame_index = 6.0
        self.app.set_current_frame_offset(15, -10)
        self.app.save_config_file()

        self.assertTrue(os.path.exists(test_file))
        with open(test_file, "r") as f:
            data = json.load(f)
            self.assertEqual(data["max_health"], 77.5)
            self.assertIn("frame_offsets", data)
            self.assertEqual(data["frame_offsets"]["Attack1"]["6"]["dx"], 15)


    def test_shadow_warrior_player_sprite_loading(self):
        """Verify that Shadow Warrior character sprite is loaded for target player dummy."""
        self.assertIsNotNone(self.app.player_stand_sprite)
        self.assertIsNotNone(self.app.player_hurt_sprite)
        # Check that loaded sprite has valid dimensions
        self.assertGreater(self.app.player_stand_sprite.get_width(), 0)
    def test_auto_align_pivots(self):
        """Verify auto_align_pivots analyzes frame bounding boxes and populates smooth offsets."""
        self.app.auto_align_pivots()
        self.assertIn("Move", self.app.frame_offsets)
        self.assertIn("Attack1", self.app.frame_offsets)
        # Check that Move frame 7 offset is calculated and populated
        self.assertIn("7", self.app.frame_offsets["Move"])
        self.assertIn("dx", self.app.frame_offsets["Move"]["7"])


    def test_harmonic_c1_smooth(self):
        """Verify harmonic_c1_smooth applies circular C1 velocity smoothing across offsets."""
        self.app.harmonic_c1_smooth()
        self.assertIn("Move", self.app.frame_offsets)
        self.assertIn("7", self.app.frame_offsets["Move"])


    def test_sanguine_phase_shift_controls(self):
        """Verify Sanguine Phase Shift controls and phase toggle state."""
        self.assertTrue(self.app.show_phase)
        self.assertIn("sanguine_phase_shift", self.app.sliders)
        self.app.toggle_phase()
        self.assertFalse(self.app.show_phase)
        self.app.toggle_phase()
        self.assertTrue(self.app.show_phase)

    def test_cycle_phase_mode(self):
        """Test cycling through Sanguine Phase Shift modes."""
        initial_mode = self.app.phase_modes[self.app.phase_mode_idx]
        self.app.cycle_phase_mode()
        new_mode = self.app.phase_modes[self.app.phase_mode_idx]
        self.assertNotEqual(initial_mode, new_mode)

    def test_ghost_trail_buffer(self):
        """Test ghost snapshot queue accumulation."""
        dummy_surf = pg.Surface((30, 30))
        self.app.ghost_trail.append((dummy_surf, (100, 100), 1.0))
        self.assertEqual(len(self.app.ghost_trail), 1)


if __name__ == "__main__":
    unittest.main()

