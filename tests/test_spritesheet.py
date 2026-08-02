import os
import sys
import unittest
import tempfile
import json
import pygame as pg

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

if not pg.get_init():
    pg.init()
if not pg.display.get_surface():
    pg.display.set_mode((1, 1), pg.NOFRAME)

from v3x_zulfiqar_gideon import AssetManager
from split_spritesheet import split_spritesheet

class TestSpriteSheet(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_asset_manager_slice_spritesheet(self):
        surf = pg.Surface((128, 32))
        frames = AssetManager.slice_spritesheet(surf, cols=4, rows=1)
        self.assertEqual(len(frames), 4)
        self.assertEqual(frames[0].get_width(), 32)
        self.assertEqual(frames[0].get_height(), 32)

    def test_asset_manager_auto_strip_detection(self):
        strip_path = os.path.join(self.temp_dir.name, "test_strip4.png")
        img = pg.Surface((128, 32))
        img.fill((255, 0, 0))
        pg.image.save(img, strip_path)

        frames = AssetManager.get_animation_frames(strip_path)
        self.assertEqual(len(frames), 4)
        self.assertEqual(frames[0].get_width(), 32)

    def test_split_spritesheet_utility(self):
        sheet_path = os.path.join(self.temp_dir.name, "hero_sheet.png")
        out_dir = os.path.join(self.temp_dir.name, "output_frames")
        img = pg.Surface((192, 64))
        img.fill((0, 255, 0))
        pg.image.save(img, sheet_path)

        saved = split_spritesheet(
            input_path=sheet_path,
            output_dir=out_dir,
            cols=3,
            rows=1,
            prefix="hero",
            create_json=True
        )

        self.assertEqual(len(saved), 3)
        self.assertTrue(os.path.exists(os.path.join(out_dir, "hero_000.png")))
        self.assertTrue(os.path.exists(os.path.join(out_dir, "config.json")))

        with open(os.path.join(out_dir, "config.json"), "r") as f:
            meta = json.load(f)
        self.assertEqual(meta["cols"], 3)
        self.assertEqual(meta["frame_width"], 64)

if __name__ == "__main__":
    unittest.main()
