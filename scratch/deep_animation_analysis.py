"""
Deep Animation Flow Analysis
Examines every frame of every animation pixel-by-pixel to map:
  - Center-of-mass (CoM) shifts between frames → reveals anticipation wind-ups
  - Bounding box expansion/contraction → reveals reach/retraction phases
  - Pixel delta rate → reveals visual intensity of motion
  - Vertical/horizontal motion bias → reveals directional intent
"""
import os
import json
from typing import Any
import pygame as pg

os.environ["SDL_VIDEODRIVER"] = "dummy"
pg.init()
pg.display.set_mode((1, 1))

BASE = "/home/chosen333/Software/Pixel-Runner/assets/shadow_warrior"

# Only analyze the animations the game actually uses
ACTIVE_ANIMS = [
    "idle", "run", "jump_up_loop", "jump_down_loop",
    "1_atk", "2_atk", "3_atk",
    "take_hit", "death", "defend", "roll", "dash",
    "sp_atk", "transform",
    "e_idle", "e_run", "e_jump_up", "e_jump_down",
    "e_1_atk", "e_2_atk", "e_3_atk",
    "e_take_hit", "e_defend", "e_sp_atk",
]

def analyze_frame(img):
    """Extract pixel-level metrics from a single frame."""
    w, h = img.get_size()
    min_x, max_x = w, 0
    min_y, max_y = h, 0
    total_alpha = 0
    weighted_x = 0
    weighted_y = 0
    pixel_count = 0

    for y in range(h):
        for x in range(w):
            r, g, b, a = img.get_at((x, y))
            if a > 10:  # threshold to skip near-invisible pixels
                pixel_count += 1
                total_alpha += a
                weighted_x += x * a
                weighted_y += y * a
                if x < min_x: min_x = x
                if x > max_x: max_x = x
                if y < min_y: min_y = y
                if y > max_y: max_y = y

    if pixel_count == 0:
        return None

    com_x = weighted_x / total_alpha
    com_y = weighted_y / total_alpha
    bbox_w = max_x - min_x + 1
    bbox_h = max_y - min_y + 1

    return {
        "pixel_count": pixel_count,
        "bbox": {"x": min_x, "y": min_y, "w": bbox_w, "h": bbox_h},
        "com": {"x": round(com_x, 2), "y": round(com_y, 2)},
        "canvas": {"w": w, "h": h},
    }


def compute_frame_delta(prev_img, curr_img):
    """Count pixels that changed between two frames."""
    w, h = curr_img.get_size()
    changed = 0
    total_checked = 0
    for y in range(h):
        for x in range(w):
            r1, g1, b1, a1 = prev_img.get_at((x, y))
            r2, g2, b2, a2 = curr_img.get_at((x, y))
            if a1 > 10 or a2 > 10:
                total_checked += 1
                if abs(r1 - r2) > 15 or abs(g1 - g2) > 15 or abs(b1 - b2) > 15 or abs(a1 - a2) > 30:
                    changed += 1
    return changed, total_checked


results: dict[str, dict[str, Any]] = {}

for anim_name in ACTIVE_ANIMS:
    anim_path = os.path.join(BASE, anim_name)
    if not os.path.isdir(anim_path):
        continue

    files = sorted(
        [f for f in os.listdir(anim_path) if f.endswith(".png")],
        key=lambda x: int(''.join(filter(str.isdigit, x)) or 0)
    )
    if not files:
        continue

    images = []
    for f in files:
        images.append(pg.image.load(os.path.join(anim_path, f)))

    frames_data: list[dict[str, Any]] = []
    for idx, img in enumerate(images):
        metrics = analyze_frame(img)
        if metrics is None:
            frames_data.append({"frame": idx, "empty": True})
            continue

        entry = {
            "frame": idx,
            "file": files[idx],
            "pixel_count": metrics["pixel_count"],
            "bbox": metrics["bbox"],
            "com_x": metrics["com"]["x"],
            "com_y": metrics["com"]["y"],
        }

        if idx > 0:
            prev_metrics = analyze_frame(images[idx - 1])
            if prev_metrics:
                entry["com_dx"] = round(metrics["com"]["x"] - prev_metrics["com"]["x"], 2)
                entry["com_dy"] = round(metrics["com"]["y"] - prev_metrics["com"]["y"], 2)
                entry["bbox_dw"] = metrics["bbox"]["w"] - prev_metrics["bbox"]["w"]
                entry["bbox_dh"] = metrics["bbox"]["h"] - prev_metrics["bbox"]["h"]

                changed, total = compute_frame_delta(images[idx - 1], img)
                entry["pixels_changed"] = changed
                entry["change_rate"] = round(changed / max(total, 1), 3)

        frames_data.append(entry)

    results[anim_name] = {
        "total_frames": len(files),
        "canvas_size": f"{images[0].get_width()}x{images[0].get_height()}",
        "frames": frames_data,
    }
    print(f"  ✓ {anim_name}: {len(files)} frames analyzed")

# Save full results
out_path = "/home/chosen333/Software/Pixel-Runner/scratch/animation_flow_data.json"
with open(out_path, "w") as f:
    json.dump(results, f, indent=2)

print(f"\nFull data saved to {out_path}")

# Now generate the human-readable summary
print("\n" + "="*80)
print("ANIMATION FLOW SUMMARY — Anticipation & Smoothness Analysis")
print("="*80)

for anim_name, data in results.items():
    frames = data["frames"]
    print(f"\n{'─'*60}")
    print(f"  {anim_name.upper()} ({data['total_frames']} frames, canvas {data['canvas_size']})")
    print(f"{'─'*60}")

    for fr in frames:
        if fr.get("empty"):
            print(f"  Frame {fr['frame']:>2}: [EMPTY]")
            continue

        line = f"  Frame {fr['frame']:>2}: "
        line += f"bbox={fr['bbox']['w']:>3}x{fr['bbox']['h']:<3} "
        line += f"CoM=({fr['com_x']:>6.1f},{fr['com_y']:>6.1f}) "

        if "com_dx" in fr:
            dx = fr["com_dx"]
            dy = fr["com_dy"]
            cr = fr.get("change_rate", 0)
            bw = fr.get("bbox_dw", 0)
            bh = fr.get("bbox_dh", 0)

            # Classify the motion
            tags = []
            if abs(dx) > 5:
                tags.append("H-SHIFT" if dx > 0 else "H-PULL")
            if abs(dy) > 3:
                tags.append("RISE" if dy < 0 else "DROP")
            if bw > 20:
                tags.append("EXPAND")
            elif bw < -20:
                tags.append("CONTRACT")
            if cr > 0.6:
                tags.append("**BURST**")
            elif cr > 0.35:
                tags.append("ACTIVE")
            elif cr < 0.15:
                tags.append("hold")

            motion = f"Δ({dx:>+6.1f},{dy:>+5.1f}) chg={cr:.0%} bboxΔw={bw:>+4}"
            if tags:
                motion += f"  [{', '.join(tags)}]"
            line += motion

        print(line)

print("\n✅ Analysis complete.")
