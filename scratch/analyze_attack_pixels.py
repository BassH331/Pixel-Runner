import pygame as pg
import os

pg.init()
pg.display.set_mode((100, 100), pg.HIDDEN)

print("Wizard Attack Frames Pixel Analysis (Right Half):")
pattern = "assets/wizard/Attack/wizard_atk1{}.png"
for i in range(8):
    path = pattern.format(i)
    if os.path.exists(path):
        img = pg.image.load(path)
        w, h = img.get_size()
        right_half_pixels = 0
        for x in range(90, w):
            for y in range(h):
                color = img.get_at((x, y))
                if color[3] > 10:  # Alpha threshold
                    right_half_pixels += 1
        print(f"Frame {i}: Non-transparent pixels in right half = {right_half_pixels}")
    else:
        print(f"Frame {i}: Path '{path}' not found!")
