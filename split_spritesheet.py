#!/usr/bin/env python3
"""
Sprite Sheet Splitter Utility

Slices sprite sheet images into individual animation PNG frame files or sidecar JSON configs.
Mirrors the functionality of web sprite splitters using Pygame.

Usage:
    python split_spritesheet.py --input path/to/sheet.png --cols 6 --rows 1 --output path/to/output_dir
    python split_spritesheet.py --input path/to/sheet.png --frame-width 64 --frame-height 64
"""

import argparse
import json
import os
import sys
import re
from typing import Optional
import pygame as pg

if not pg.get_init():
    pg.init()
if not pg.display.get_surface():
    pg.display.set_mode((1, 1), pg.NOFRAME)

def pad_number(n: int, width: int = 3) -> str:
    return str(n).zfill(width)

def split_spritesheet(
    input_path: str,
    output_dir: Optional[str] = None,
    cols: Optional[int] = None,
    rows: Optional[int] = None,
    frame_width: Optional[int] = None,
    frame_height: Optional[int] = None,
    prefix: str = "frame",
    pad: int = 3,
    start_index: int = 0,
    trim: bool = False,
    create_json: bool = True,
) -> list[str]:
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Input file not found: {input_path}")

    img = pg.image.load(input_path).convert_alpha()
    w, h = img.get_size()

    base_name = os.path.basename(input_path)
    if cols is None and rows is None and frame_width is None and frame_height is None:
        strip_match = re.search(r'_strip(\d+)', base_name, re.IGNORECASE)
        if strip_match:
            cols = int(strip_match.group(1))
            rows = 1
        elif w > h and h > 0 and w % h == 0:
            cols = w // h
            rows = 1
        elif h > w and w > 0 and h % w == 0:
            cols = 1
            rows = h // w
        else:
            cols = 1
            rows = 1

    if cols is not None or rows is not None:
        c = max(1, cols if cols is not None else 1)
        r = max(1, rows if rows is not None else 1)
        fw = w // c
        fh = h // r
    elif frame_width is not None or frame_height is not None:
        fw = max(1, frame_width if frame_width is not None else w)
        fh = max(1, frame_height if frame_height is not None else h)
        c = max(1, w // fw)
        r = max(1, h // fh)
    else:
        fw, fh = w, h
        c, r = 1, 1

    if output_dir is None:
        raw_name = os.path.splitext(base_name)[0]
        output_dir = os.path.join(os.path.dirname(input_path) or ".", f"{raw_name}_frames")

    os.makedirs(output_dir, exist_ok=True)

    saved_files = []
    frame_idx = start_index

    for row in range(r):
        for col in range(c):
            rect = pg.Rect(col * fw, row * fh, fw, fh)
            frame = img.subsurface(rect).copy()

            if trim:
                bounding_rect = frame.get_bounding_rect()
                if bounding_rect.width > 0 and bounding_rect.height > 0:
                    frame = frame.subsurface(bounding_rect).copy()

            filename = f"{prefix}_{pad_number(frame_idx, pad)}.png"
            out_file = os.path.join(output_dir, filename)
            pg.image.save(frame, out_file)
            saved_files.append(out_file)
            frame_idx += 1

    if create_json:
        json_data = {
            "source": os.path.abspath(input_path),
            "sheet_width": w,
            "sheet_height": h,
            "cols": c,
            "rows": r,
            "frame_width": fw,
            "frame_height": fh,
            "total_frames": len(saved_files),
        }
        json_path = os.path.join(output_dir, "config.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(json_data, f, indent=4)

    return saved_files

def main():
    parser = argparse.ArgumentParser(description="Split sprite sheet images into animation frames.")
    parser.add_argument("--input", "-i", required=True, help="Path to input sprite sheet image.")
    parser.add_argument("--output", "-o", default=None, help="Directory to save output frames.")
    parser.add_argument("--cols", "-c", type=int, default=None, help="Number of columns.")
    parser.add_argument("--rows", "-r", type=int, default=None, help="Number of rows.")
    parser.add_argument("--frame-width", "-w", type=int, default=None, help="Frame width in pixels.")
    parser.add_argument("--frame-height", "-fh", type=int, default=None, help="Frame height in pixels.")
    parser.add_argument("--prefix", "-p", default="frame", help="Prefix for output frames.")
    parser.add_argument("--pad", type=int, default=3, help="Digit padding width (default: 3).")
    parser.add_argument("--start", type=int, default=0, help="Starting index (default: 0).")
    parser.add_argument("--trim", action="store_true", help="Trim transparent bounding borders.")
    parser.add_argument("--no-json", action="store_true", help="Do not generate sidecar config.json.")

    args = parser.parse_args()

    try:
        files = split_spritesheet(
            input_path=args.input,
            output_dir=args.output,
            cols=args.cols,
            rows=args.rows,
            frame_width=args.frame_width,
            frame_height=args.frame_height,
            prefix=args.prefix,
            pad=args.pad,
            start_index=args.start,
            trim=args.trim,
            create_json=not args.no_json,
        )
        print(f"Successfully sliced {len(files)} frames to '{args.output or 'output directory'}'")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
