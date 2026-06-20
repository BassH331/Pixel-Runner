import os
import pygame as pg

os.environ["SDL_VIDEODRIVER"] = "dummy"
pg.init()
pg.display.set_mode((1, 1))

base_dir = "/home/chosen333/Software/Pixel-Runner/assets/shadow_warrior"

configs = {
    "THRUST_ATTACK_CONFIG": {"dir": "1_atk", "hit_frames": [2, 3, 4, 5, 6, 7], "startup_frames": [0, 1], "recovery_frames": [8]},
    "SMASH_ATTACK_CONFIG": {"dir": "2_atk", "hit_frames": [2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14], "startup_frames": [0, 1], "recovery_frames": [15, 16]},
    "POWER_ATTACK_CONFIG": {"dir": "3_atk", "hit_frames": [6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22], "startup_frames": list(range(6)), "recovery_frames": []},
    "SPECIAL_ATTACK_CONFIG": {"dir": "sp_atk", "hit_frames": list(range(14, 34)), "startup_frames": list(range(14)), "recovery_frames": []},
    
    # Enhanced Shadow Form Configs
    "ENHANCED_SPECIAL_ATTACK_CONFIG": {"dir": "e_sp_atk", "hit_frames": list(range(6, 19)), "startup_frames": list(range(6)), "recovery_frames": []},
}

for name, meta in configs.items():
    path = os.path.join(base_dir, meta["dir"])
    files = sorted([f for f in os.listdir(path) if f.endswith(".png")], key=lambda x: int(''.join(filter(str.isdigit, x)) or 0))
    
    print(f"\n    \"{name}\": {{")
    print(f"        \"hit_frames\": {meta['hit_frames']},")
    # Add dummy constants for now, we will keep original base stats
    print(f"        \"hitbox_data\": {{")
    
    for idx in meta["hit_frames"]:
        f_path = os.path.join(path, files[idx])
        img = pg.image.load(f_path)
        w, h = img.get_size()
        min_x, max_x = w, 0
        min_y, max_y = h, 0
        has_pixels = False
        for y in range(h):
            for x in range(w):
                r, g, b, a = img.get_at((x, y))
                if a > 0:
                    has_pixels = True
                    if x < min_x: min_x = x
                    if x > max_x: max_x = x
                    if y < min_y: min_y = y
                    if y > max_y: max_y = y
        if has_pixels:
            bbox_w = max_x - min_x + 1
            bbox_h = max_y - min_y + 1
            offset_x = (min_x + max_x) // 2 - w // 2
            offset_y = (min_y + max_y) // 2 - h // 2
            
            # Scale to 3.0 and adjust center
            scaled_w = int(bbox_w * 3.0)
            scaled_h = int(bbox_h * 3.0)
            hitbox_offset_x = int(offset_x * 3.0)
            hitbox_offset_y = int((offset_y * 3.0) - 75)
            
            print(f"            \"{idx}\": {{\"offset_x\": {hitbox_offset_x}, \"offset_y\": {hitbox_offset_y}, \"width\": {scaled_w}, \"height\": {scaled_h}}},")
    print("        },")
    print(f"        \"startup_frames\": {meta['startup_frames']},")
    print(f"        \"recovery_frames\": {meta['recovery_frames']}")
    print("    },")
