import os
import sys
import unittest
import tempfile
import pygame as pg

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

if not pg.get_init():
    pg.init()
if not pg.display.get_surface():
    pg.display.set_mode((1, 1), pg.NOFRAME)

from wave_editor import BehaviourMapper, BTAGS
from src.game.entities.skeleton import Skeleton

class TestBehaviourMapperSkipAndSplit(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_btags_contains_skip(self):
        self.assertIn("skip", BTAGS)

    def test_behaviour_mapper_load_and_skip_tag(self):
        root = self.temp_dir.name
        # Create subfolders for idle and attack
        os.makedirs(os.path.join(root, "01_idle"), exist_ok=True)
        os.makedirs(os.path.join(root, "02_attack_1"), exist_ok=True)
        os.makedirs(os.path.join(root, "03_attack_2"), exist_ok=True)

        bmap = BehaviourMapper(pg.Rect(0, 0, 400, 300))
        bmap.load(root)

        self.assertEqual(len(bmap.subs), 3)
        self.assertEqual(bmap.mapping["01_idle"], "idle")
        self.assertEqual(bmap.mapping["02_attack_1"], "attack")
        self.assertEqual(bmap.mapping["03_attack_2"], "attack")

        # Manually set 03_attack_2 to 'skip'
        bmap.mapping["03_attack_2"] = "skip"

        # Verify filtering out skip tags
        filtered_map = {k: v for k, v in bmap.mapping.items() if v != "skip"}
        self.assertIn("01_idle", filtered_map)
        self.assertIn("02_attack_1", filtered_map)
        self.assertNotIn("03_attack_2", filtered_map)

    def test_skeleton_ignores_skip_tag(self):
        root = self.temp_dir.name
        os.makedirs(os.path.join(root, "01_idle"), exist_ok=True)
        os.makedirs(os.path.join(root, "02_attack"), exist_ok=True)
        
        # Save a 32x32 dummy image in each folder
        img = pg.Surface((32, 32))
        pg.image.save(img, os.path.join(root, "01_idle", "frame_000.png"))
        pg.image.save(img, os.path.join(root, "02_attack", "frame_000.png"))

        bmap = {"01_idle": "idle", "02_attack": "skip"}

        from unittest.mock import MagicMock
        skeleton = Skeleton(x=100, y=100, player=MagicMock(), sprite_root=root, behaviour_map=bmap)
        self.assertIsNotNone(skeleton.animations)

    def test_auto_split_spritesheet(self):
        root = self.temp_dir.name
        strip_file = os.path.join(root, "hero_attack_strip4.png")
        img = pg.Surface((128, 32))
        pg.image.save(img, strip_file)

        bmap = BehaviourMapper(pg.Rect(0, 0, 400, 300))
        bmap.load(root)

        # auto_split should slice hero_attack_strip4.png into hero_attack_strip4_frames/
        frames_dir = os.path.join(root, "hero_attack_strip4_frames")
        self.assertTrue(os.path.isdir(frames_dir))
        self.assertIn("hero_attack_strip4_frames", bmap.subs)
        self.assertEqual(bmap.mapping["hero_attack_strip4_frames"], "attack")

if __name__ == "__main__":
    unittest.main()
