import unittest
from src.game.audio.combat_collision_logger import CombatCollisionLogger

class TestCombatCollisionLogger(unittest.TestCase):
    def setUp(self):
        self.logger = CombatCollisionLogger()

    def test_log_skeleton_collision(self):
        sound = self.logger.log_collision(
            attacker="player",
            defender="skeleton",
            defender_id="skel_01",
            defender_state="alive"
        )
        self.assertEqual(sound, "collision_player_skeleton")
        logs = self.logger.get_encounter_logs()
        self.assertEqual(len(logs), 1)
        self.assertEqual(logs[0]["defender"], "skeleton")
        self.assertEqual(logs[0]["defender_id"], "skel_01")
        self.assertEqual(logs[0]["sound_played"], "collision_player_skeleton")

    def test_log_zombie_collision(self):
        sound = self.logger.log_collision(
            attacker="player",
            defender="zombie",
            defender_id="zomb_04"
        )
        self.assertEqual(sound, "collision_player_zombie")

    def test_log_boss_collision(self):
        sound = self.logger.log_collision(
            attacker="player",
            defender="fire_wizard",
            defender_id="boss_01"
        )
        self.assertEqual(sound, "collision_player_boss")

    def test_log_defend_collision(self):
        sound = self.logger.log_collision(
            attacker="skeleton",
            defender="player",
            action="defend"
        )
        self.assertEqual(sound, "collision_player_defend")

if __name__ == "__main__":
    unittest.main()
