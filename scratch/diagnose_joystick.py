"""
Run this with your controller plugged in:
    python scratch/diagnose_joystick.py

Prints whatever pygame/SDL detects, then live-streams axis/button/hat
values for 20 seconds so you can see exactly which index moves when you
press a stick/button/trigger. Paste the output back for calibration.
"""
import pygame as pg

pg.init()
pg.joystick.init()
pg.display.set_mode((200, 200))  # a window is required for the event loop to pump

count = pg.joystick.get_count()
print(f"pg.joystick.get_count() = {count}")
if count == 0:
    print("No joystick detected by pygame/SDL at all. This means the OS/driver")
    print("layer isn't exposing it to SDL2 -- not something fixable in game code.")
    raise SystemExit(0)

joy = pg.joystick.Joystick(0)
joy.init()
print(f"Name: {joy.get_name()}")
print(f"Axes: {joy.get_numaxes()}  Buttons: {joy.get_numbuttons()}  Hats: {joy.get_numhats()}")
print("\nMove sticks / press buttons / pull triggers for ~20s...\n")

clock = pg.time.Clock()
elapsed = 0.0
while elapsed < 20.0:
    for event in pg.event.get():
        pass  # just pump the queue so get_axis/get_button stay fresh

    axes = [round(joy.get_axis(i), 2) for i in range(joy.get_numaxes())]
    buttons = [i for i in range(joy.get_numbuttons()) if joy.get_button(i)]
    hats = [joy.get_hat(i) for i in range(joy.get_numhats())]

    if any(abs(a) > 0.15 for a in axes) or buttons or any(h != (0, 0) for h in hats):
        print(f"axes={axes} buttons_pressed={buttons} hats={hats}")

    dt = clock.tick(30) / 1000.0
    elapsed += dt

print("\nDone.")
