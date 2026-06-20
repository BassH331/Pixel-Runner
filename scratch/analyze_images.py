import os
import pygame as pg

# Initialize pygame in headless mode
os.environ["SDL_VIDEODRIVER"] = "dummy"
pg.init()
pg.display.set_mode((1, 1))

base_dir = "/home/chosen333/Software/Pixel-Runner/assets/shadow_warrior"
attack_dirs = [
    "1_atk", "2_atk", "3_atk", "sp_atk",
    "e_1_atk", "e_2_atk", "e_3_atk", "e_sp_atk"
]

print("Analyzing attack animation frames pixel-by-pixel for exact non-transparent bounds:")
for adir in attack_dirs:
    path = os.path.join(base_dir, adir)
    if not os.path.isdir(path):
        print(f"Directory {adir} not found!")
        continue
    
    files = sorted([f for f in os.listdir(path) if f.endswith(".png")], key=lambda x: int(''.join(filter(str.isdigit, x)) or 0))
    print(f"\n--- Category: {adir} ({len(files)} frames) ---")
    
    for idx, f in enumerate(files):
        f_path = os.path.join(path, f)
        try:
            img = pg.image.load(f_path)
            w, h = img.get_size()
            
            # Find bounding box of non-transparent pixels
            min_x, max_x = w, 0
            min_y, max_y = h, 0
            has_pixels = False
            
            for y in range(h):
                for x in range(w):
                    r, g, b, a = img.get_at((x, y))
                    if a > 0: # not fully transparent
                        has_pixels = True
                        if x < min_x: min_x = x
                        if x > max_x: max_x = x
                        if y < min_y: min_y = y
                        if y > max_y: max_y = y
            
            if has_pixels:
                bbox_w = max_x - min_x + 1
                bbox_h = max_y - min_y + 1
                # Center of the image is (w/2, h/2)
                # Let's calculate the relative offset from the center
                offset_x = (min_x + max_x) // 2 - w // 2
                offset_y = (min_y + max_y) // 2 - h // 2
                print(f"Frame {idx}: file={f}, size={w}x{h}, bbox=[x:{min_x}..{max_x}, y:{min_y}..{max_y}], bbox_size={bbox_w}x{bbox_h}, relative_center_offset=({offset_x}, {offset_y})")
            else:
                print(f"Frame {idx}: file={f}, EMPTY")
        except Exception as e:
            print(f"Error loading {f}: {e}")
