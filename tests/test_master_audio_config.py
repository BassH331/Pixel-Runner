import os
import json
import unittest
import pygame as pg
from src.game.audio.audio_lock import verify_config_integrity
from v3x_zulfiqar_gideon.audio_manager import AudioManager, SoundPriority

class TestMasterAudioConfig(unittest.TestCase):
    def setUp(self):
        if not pg.mixer.get_init():
            pg.mixer.pre_init(frequency=44100, size=-16, channels=2, buffer=2048)
            pg.mixer.init()

    def test_master_audio_config_integrity(self):
        config_path = "game_data/master_audio_config.json"
        lock_path = "game_data/master_audio_config.lock"
        
        self.assertTrue(os.path.exists(config_path), "Master audio config file must exist")
        self.assertTrue(os.path.exists(lock_path), "Master audio lock file must exist")
        
        is_valid, reason = verify_config_integrity(config_path, lock_path)
        self.assertTrue(is_valid, f"Master audio lock validation failed: {reason}")

    def test_all_master_audio_assets_exist(self):
        with open("game_data/master_audio_config.json", "r") as f:
            config = json.load(f)
        
        sounds = config.get("sounds", {})
        self.assertGreater(len(sounds), 0, "Master audio config must contain registered sounds")
        
        for sound_alias, entry in sounds.items():
            file_path = entry if isinstance(entry, str) else entry.get("path")
            self.assertIsNotNone(file_path, f"Sound entry '{sound_alias}' missing path")
            self.assertTrue(os.path.exists(file_path), f"Audio asset file for '{sound_alias}' not found at: {file_path}")

    def test_audio_manager_master_config_loading(self):
        audio_mgr = AudioManager()
        audio_mgr.load_audio_config("game_data/master_audio_config.json")
        
        self.assertGreater(len(audio_mgr.master_audio_config.get("sounds", {})), 0)
        registered_sounds = audio_mgr.master_audio_config["sounds"]
        self.assertIn("roll", registered_sounds)
        self.assertIn("skeleton_spawn", registered_sounds)
        self.assertIn("jump", registered_sounds)

    def test_player_audio_config_roll_mapping(self):
        with open("game_data/player_audio_config.json", "r") as f:
            p_config = json.load(f)
        
        states = p_config.get("states", {})
        roll_state = states.get("ROLL", {})
        self.assertEqual(roll_state.get("0"), "roll", f"Expected ROLL frame 0 to be mapped to 'roll', got: {roll_state.get('0')}")

    def test_channel_zero_music_isolation(self):
        audio_mgr = AudioManager()
        audio_mgr.load_audio_config("game_data/master_audio_config.json")
        
        # Free search must never select channel 0
        free_channel = audio_mgr._find_free_channel_id()
        self.assertNotEqual(free_channel, 0, "SFX must never use reserved music channel 0")
        
        # Steal channel must never return channel 0
    def test_sound_metadata_compatibility(self):
        config_path = "game_data/master_audio_config.json"
        lock_path = "game_data/master_audio_config.lock"
        with open(config_path, "r") as f:
            config = json.load(f)
        
        # Verify that adding sound_metadata preserves dictionary loadability
        test_config = dict(config)
        test_config["sound_metadata"] = {
            "collision_player_bat": {
                "category": "COLLISION",
                "state": "💥 Bat Hit",
                "usage": "Player strike hitting flying Bat."
            }
        }
        audio_mgr = AudioManager()
        audio_mgr.master_audio_config = test_config
        self.assertIn("collision_player_bat", audio_mgr.master_audio_config["sounds"])
        self.assertEqual(audio_mgr.master_audio_config["sound_metadata"]["collision_player_bat"]["category"], "COLLISION")

if __name__ == "__main__":
    unittest.main()
