import pygame as pg
import os

pg.init()
pg.display.set_mode((100, 100), pg.HIDDEN)

print("Wizard Attack Frames Inspection:")
pattern = "assets/wizard/Attack/wizard_atk1{}.png"
for i in range(8):
    path = pattern.format(i)
    if os.path.exists(path):
        img = pg.image.load(path)
        w, h = img.get_size()
        bbox = img.get_bounding_rect()
        print(f"Frame {i}: Size = {w}x{h} | Bounding Box = {bbox}")
    else:
        print(f"Frame {i}: Path '{path}' not found!")
