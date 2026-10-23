"""
Smart sprite source analysis — figure out *what* an image actually is before
anyone tries to animate it.

Problem this solves
-------------------
Asset packs ship sprites in many shapes: folders of numbered frames, single
strips, multi-row sheets where every row is a different animation, sheets
with non-square cells (80x64, 112x128, 96x112 ...), plus tilesets and
background layers sitting in the very same folder. Naively treating "every
PNG in a folder" as animation frames, or blitting a whole sheet as one
frame, produces the giant-sheet-on-screen mess seen in the level editor.

Detection pipeline (first confident answer wins)
------------------------------------------------
1. **Sidecar JSON** next to the image — Aseprite / TexturePacker exports
   (``frames`` + ``meta.frameTags``) or the simple
   ``{"cols", "rows", "frame_width", "frame_height"}`` format.
2. **Aseprite source file** (``.ase`` / ``.aseprite``) next to the image —
   its binary header stores the exact canvas (= frame) size, and its tag
   chunk stores animation names ("Idle", "Death", ...) and frame durations.
3. **Filename hints** — ``_strip8`` style frame counts.
4. **Alpha-grid analysis** — tries every frame size that divides the sheet
   and picks the smallest grid whose cell borders never slice through
   opaque pixels, never leave holes in the middle of a row, and whose
   cells look alike. Verified against Aseprite ground truth on real packs.
5. **Square-strip heuristic** — ``W % H == 0`` strips (legacy behaviour).

Images are also classified as ``sheet`` / ``single`` / ``tileset`` /
``background`` so tools can refuse to animate a tileset as an NPC.

Directories are classified as a frame ``sequence`` (numbered / same-size
frames), a single-file folder, or a heterogeneous ``collection`` of
unrelated images (from which a primary sprite is picked automatically).

Everything here fails soft: unreadable files yield empty results with a
warning instead of exceptions, so the game loop and editors never crash on
a weird asset.
"""

from __future__ import annotations

import json
import os
import re
import struct
from dataclasses import dataclass, field
from typing import Iterable, Optional, Sequence, Union

import pygame as pg

try:  # numpy is a declared dependency, but stay importable without it.
    import numpy as np
except Exception:  # pragma: no cover - exercised only on broken installs
    np = None  # type: ignore[assignment]

__all__ = [
    "IMAGE_EXTS",
    "Clip",
    "SheetLayout",
    "SpriteSource",
    "analyze_image",
    "describe_source",
    "load_animation",
    "load_named_animation",
    "read_aseprite_meta",
    "clear_cache",
    "IDLE_KEYWORDS",
    "WALK_KEYWORDS",
    "DEATH_KEYWORDS",
    "SPAWN_KEYWORDS",
]

IMAGE_EXTS = (".png", ".webp", ".jpg", ".jpeg", ".bmp", ".gif", ".tga")
ASEPRITE_EXTS = (".ase", ".aseprite")

KIND_SHEET = "sheet"
KIND_SINGLE = "single"
KIND_TILESET = "tileset"
KIND_BACKGROUND = "background"

SRC_SEQUENCE = "sequence"
SRC_COLLECTION = "collection"
SRC_EMPTY = "empty"
SRC_MISSING = "missing"

IDLE_KEYWORDS = ("idle", "stand", "breath", "loop", "sitting", "default", "move")
WALK_KEYWORDS = ("walk", "run", "move", "fly", "flying")
DEATH_KEYWORDS = ("death", "die", "dead", "dying")
SPAWN_KEYWORDS = ("spawn", "appear", "rise", "summon")

_TILESET_TOKENS = {"tile", "tiles", "tileset", "tilesets", "tilemap", "terrain", "autotile"}
_BG_FILE_TOKENS = {"background", "backgrounds", "bg", "parallax", "layer", "backdrop", "sky"}
_BG_DIR_TOKENS = {"background", "backgrounds", "parallax"}

# Grid detector tolerances (tuned against Aseprite ground truth).
_CUT_TOLERANCE = 0.02       # max fraction of a cell border allowed to slice opaque pixels
_INTERIOR_TOLERANCE = 0.15  # max ratio of "holes" (empty cells before the row's last frame)
_SIMILARITY_FLOOR = 0.30    # min mean bbox overlap between neighbouring frames
_ALPHA_THRESHOLD = 16


# ════════════════════════════════════════════════════════════════════════════
# Data model
# ════════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class Clip:
    """A named animation: an ordered list of indices into ``SheetLayout.rects``."""

    name: str
    indices: tuple[int, ...]
    frame_ms: int = 0  # 0 = unknown, use caller default

    def __len__(self) -> int:
        return len(self.indices)


@dataclass
class SheetLayout:
    """How a single image file is divided into frames and animations."""

    path: str
    width: int
    height: int
    rects: list[tuple[int, int, int, int]]
    clips: list[Clip]
    kind: str
    source: str  # sidecar-json | aseprite | filename | alpha-grid | square-strip | single
    frame_w: int = 0
    frame_h: int = 0
    cols: int = 1
    rows: int = 1

    @property
    def frame_count(self) -> int:
        return len(self.rects)

    @property
    def is_animated(self) -> bool:
        return any(len(c) > 1 for c in self.clips)

    @property
    def clip_names(self) -> list[str]:
        return [c.name for c in self.clips]

    def find_clip(self, selector: Union[None, int, str, Sequence[str]] = None) -> Optional[Clip]:
        """Resolve a clip by index, exact/fuzzy name, or keyword list."""
        return _select_clip(self.clips, selector)

    def describe(self) -> str:
        name = os.path.basename(self.path)
        if self.kind == KIND_TILESET:
            return f"{name} · tileset {self.width}×{self.height}"
        if self.kind == KIND_BACKGROUND:
            return f"{name} · background {self.width}×{self.height}"
        if self.frame_count <= 1:
            return f"{name} · single sprite {self.width}×{self.height}"
        grid = f"{self.cols}×{self.rows} @ {self.frame_w}×{self.frame_h}" if self.frame_w else f"{self.frame_count} rects"
        return f"{name} · {grid} · {self.frame_count} frames · {len(self.clips)} clip(s) · via {self.source}"


@dataclass
class SpriteSource:
    """What a ``sprite_dir`` value (folder *or* file) resolves to."""

    path: str
    kind: str  # sheet | single | tileset | background | sequence | collection | empty | missing
    layout: Optional[SheetLayout] = None
    files: list[str] = field(default_factory=list)
    primary: Optional[str] = None  # the image actually used for a collection / 1-file folder

    @property
    def animatable(self) -> bool:
        """True if this can sensibly drive an NPC/boss animation."""
        if self.kind == SRC_SEQUENCE:
            return True
        if self.kind in (KIND_SHEET, KIND_SINGLE):
            return True
        if self.kind == SRC_COLLECTION:
            return self.layout is not None and self.layout.kind in (KIND_SHEET, KIND_SINGLE)
        return False

    @property
    def clip_names(self) -> list[str]:
        if self.layout is not None and self.kind != SRC_SEQUENCE:
            return self.layout.clip_names
        return []

    def describe(self) -> str:
        if self.kind == SRC_MISSING:
            return "Path not found"
        if self.kind == SRC_EMPTY:
            return "No images in this folder"
        if self.kind == SRC_SEQUENCE:
            return f"{os.path.basename(self.path.rstrip('/'))} · {len(self.files)}-frame sequence"
        if self.kind == SRC_COLLECTION:
            if self.layout is None:
                return f"{len(self.files)} unrelated images (no sprite found) — pick a file"
            return f"{len(self.files)} unrelated images — auto-picked {self.layout.describe()}"
        return self.layout.describe() if self.layout else os.path.basename(self.path)


# ════════════════════════════════════════════════════════════════════════════
# Caches
# ════════════════════════════════════════════════════════════════════════════

_LAYOUT_CACHE: dict[tuple, SheetLayout] = {}
_SOURCE_CACHE: dict[tuple, SpriteSource] = {}
_SURFACE_CACHE: dict[tuple, pg.Surface] = {}


def clear_cache() -> None:
    _LAYOUT_CACHE.clear()
    _SOURCE_CACHE.clear()
    _SURFACE_CACHE.clear()


def _stat_key(path: str) -> tuple:
    try:
        st = os.stat(path)
        return (os.path.abspath(path), st.st_mtime_ns, st.st_size)
    except OSError:
        return (os.path.abspath(path), 0, 0)


def _dir_key(path: str) -> tuple:
    try:
        names = tuple(sorted(os.listdir(path)))
        return (os.path.abspath(path), os.stat(path).st_mtime_ns, hash(names))
    except OSError:
        return (os.path.abspath(path), 0, 0)


# ════════════════════════════════════════════════════════════════════════════
# Small helpers
# ════════════════════════════════════════════════════════════════════════════

def _natural_key(name: str) -> list:
    return [int(s) if s.isdigit() else s.lower() for s in re.split(r"(\d+)", name)]


def _tokens(text: str) -> set[str]:
    return {t for t in re.split(r"[^a-z0-9]+", text.lower()) if t}


def _norm_stem(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", os.path.splitext(name)[0].lower())


def _is_image(name: str) -> bool:
    return name.lower().endswith(IMAGE_EXTS)


def _resolve(path: str) -> str:
    """Resolve relative asset paths against CWD, then the repo root."""
    if not path:
        return path
    if os.path.exists(path):
        return path
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
    cand = os.path.join(repo_root, path)
    return cand if os.path.exists(cand) else path


def _load_surface(path: str) -> Optional[pg.Surface]:
    key = _stat_key(path)
    cached = _SURFACE_CACHE.get(key)
    if cached is not None:
        return cached
    try:
        surf = pg.image.load(path)
        if pg.display.get_init() and pg.display.get_surface() is not None:
            surf = surf.convert_alpha()
        elif surf.get_flags() & pg.SRCALPHA == 0:
            surf = surf.convert_alpha() if pg.display.get_surface() else surf
    except Exception as exc:
        print(f"[SPRITE ANALYZER WARNING] Could not load image {path!r}: {exc}")
        return None
    _SURFACE_CACHE[key] = surf
    return surf


def _png_size(path: str) -> Optional[tuple[int, int]]:
    """Read PNG dimensions straight from the IHDR chunk (no decode)."""
    try:
        with open(path, "rb") as f:
            head = f.read(24)
        if head[:8] == b"\x89PNG\r\n\x1a\n" and head[12:16] == b"IHDR":
            w, h = struct.unpack(">II", head[16:24])
            return int(w), int(h)
    except OSError:
        pass
    return None


def _image_size(path: str) -> Optional[tuple[int, int]]:
    size = _png_size(path) if path.lower().endswith(".png") else None
    if size:
        return size
    surf = _load_surface(path)
    return surf.get_size() if surf is not None else None


def _select_clip(clips: Sequence[Clip], selector) -> Optional[Clip]:
    if not clips:
        return None
    if selector is None:
        return _select_clip(clips, IDLE_KEYWORDS) or clips[0]
    if isinstance(selector, bool):
        return clips[0]
    if isinstance(selector, int):
        return clips[selector] if 0 <= selector < len(clips) else None
    if isinstance(selector, str):
        s = selector.strip().lower()
        if not s:
            return _select_clip(clips, None)
        for c in clips:
            if c.name.lower() == s:
                return c
        for c in clips:
            if s in c.name.lower():
                return c
        if s.isdigit():
            return _select_clip(clips, int(s))
        return None
    # keyword list: first keyword that matches any clip wins (keyword priority)
    for kw in selector:
        kw_l = str(kw).lower()
        for c in clips:
            if kw_l in _tokens(c.name) or c.name.lower().startswith(kw_l):
                return c
    return None


# ════════════════════════════════════════════════════════════════════════════
# 1. Sidecar JSON (Aseprite / TexturePacker / simple grid)
# ════════════════════════════════════════════════════════════════════════════

def _grid_rects(w: int, h: int, fw: int, fh: int) -> tuple[list[tuple[int, int, int, int]], int, int]:
    cols, rows = max(1, w // fw), max(1, h // fh)
    rects = [(c * fw, r * fh, fw, fh) for r in range(rows) for c in range(cols)]
    return rects, cols, rows


def _from_sidecar(path: str, w: int, h: int) -> Optional[SheetLayout]:
    stem = os.path.splitext(path)[0]
    candidates = [path + ".json", stem + ".json"]
    dir_cfg = os.path.join(os.path.dirname(path), "config.json")
    for jpath in candidates + [dir_cfg]:
        if not os.path.isfile(jpath):
            continue
        try:
            with open(jpath, "r", encoding="utf-8") as f:
                meta = json.load(f)
        except Exception:
            continue
        if not isinstance(meta, dict):
            continue
        if jpath == dir_cfg:
            # config.json describes *some* sheet in the folder — only trust it
            # when it is clearly about this image.
            src = meta.get("source")
            if src and os.path.basename(str(src).replace("\\", "/")) != os.path.basename(path):
                continue
            sw, sh = meta.get("sheet_width"), meta.get("sheet_height")
            if (sw and sw != w) or (sh and sh != h):
                continue
        layout = _parse_texture_atlas(path, w, h, meta) or _parse_simple_grid(path, w, h, meta)
        if layout:
            return layout
    return None


def _parse_texture_atlas(path: str, w: int, h: int, meta: dict) -> Optional[SheetLayout]:
    frames = meta.get("frames")
    if not frames:
        return None
    items = list(frames.values()) if isinstance(frames, dict) else list(frames)
    if isinstance(frames, dict):
        names = list(frames.keys())
        order = sorted(range(len(items)), key=lambda i: _natural_key(names[i]))
        items = [items[i] for i in order]
    rects: list[tuple[int, int, int, int]] = []
    durations: list[int] = []
    for it in items:
        fr = it.get("frame") if isinstance(it, dict) else None
        if not isinstance(fr, dict):
            continue
        x, y, fw, fh = int(fr.get("x", 0)), int(fr.get("y", 0)), int(fr.get("w", 0)), int(fr.get("h", 0))
        if fw <= 0 or fh <= 0 or x + fw > w or y + fh > h:
            continue
        rects.append((x, y, fw, fh))
        durations.append(int(it.get("duration", 0) or 0))
    if not rects:
        return None
    clips: list[Clip] = []
    tags = (meta.get("meta") or {}).get("frameTags") or []
    for t in tags:
        try:
            a, b = int(t["from"]), int(t["to"])
        except Exception:
            continue
        idx = tuple(i for i in range(a, b + 1) if i < len(rects))
        if not idx:
            continue
        if str(t.get("direction", "forward")).lower() == "reverse":
            idx = idx[::-1]
        clips.append(Clip(str(t.get("name") or f"Tag {len(clips) + 1}"), idx, _mode([durations[i] for i in idx])))
    if not clips:
        clips = [Clip("Default", tuple(range(len(rects))), _mode(durations))]
    fw0, fh0 = rects[0][2], rects[0][3]
    uniform = all(r[2] == fw0 and r[3] == fh0 for r in rects)
    return SheetLayout(path, w, h, rects, clips, KIND_SHEET if len(rects) > 1 else KIND_SINGLE,
                       "sidecar-json", fw0 if uniform else 0, fh0 if uniform else 0,
                       max(1, w // fw0) if uniform else 0, max(1, h // fh0) if uniform else 0)


def _parse_simple_grid(path: str, w: int, h: int, meta: dict) -> Optional[SheetLayout]:
    c, r = meta.get("cols"), meta.get("rows")
    fw, fh = meta.get("frame_width"), meta.get("frame_height")
    if c is None and r is None and fw is None and fh is None:
        return None
    try:
        if c is not None or r is not None:
            cols, rows = max(1, int(c or 1)), max(1, int(r or 1))
            fw, fh = w // cols, h // rows
        else:
            fw, fh = max(1, int(fw or w)), max(1, int(fh or h))
    except (TypeError, ValueError):
        return None
    if fw <= 0 or fh <= 0:
        return None
    rects, cols, rows = _grid_rects(w, h, fw, fh)
    total = meta.get("total_frames")
    if isinstance(total, int) and 0 < total < len(rects):
        rects = rects[:total]
    clips: list[Clip] = []
    anims = meta.get("animations") or meta.get("clips")
    if isinstance(anims, dict):
        for name, idx in anims.items():
            if isinstance(idx, list):
                valid = tuple(int(i) for i in idx if isinstance(i, int) and 0 <= i < len(rects))
                if valid:
                    clips.append(Clip(str(name), valid))
    if not clips:
        clips = _row_clips(cols, rows, None, len(rects))
    return SheetLayout(path, w, h, rects, clips, KIND_SHEET if len(rects) > 1 else KIND_SINGLE,
                       "sidecar-json", fw, fh, cols, rows)


def _mode(values: Iterable[int]) -> int:
    vals = [v for v in values if v > 0]
    if not vals:
        return 0
    return max(set(vals), key=vals.count)


# ════════════════════════════════════════════════════════════════════════════
# 2. Aseprite source metadata
# ════════════════════════════════════════════════════════════════════════════

@dataclass
class AsepriteMeta:
    width: int
    height: int
    frames: int
    durations: list[int]
    tags: list[tuple[str, int, int, int]]  # (name, from, to, direction)


def read_aseprite_meta(path: str) -> Optional[AsepriteMeta]:
    """Parse canvas size, frame count, durations and tags from a .ase/.aseprite file.

    Only headers and the Tags chunk are read — pixel data is never decoded.
    """
    try:
        with open(path, "rb") as f:
            data = f.read()
        if len(data) < 128:
            return None
        _size, magic, n_frames, w, h = struct.unpack_from("<IHHHH", data, 0)
        if magic != 0xA5E0 or w <= 0 or h <= 0:
            return None
        off = 128
        durations: list[int] = []
        tags: list[tuple[str, int, int, int]] = []
        for _ in range(n_frames):
            if off + 16 > len(data):
                break
            fsize, fmagic, old_chunks, dur = struct.unpack_from("<IHHH", data, off)
            if fmagic != 0xF1FA or fsize < 16:
                break
            new_chunks = struct.unpack_from("<I", data, off + 12)[0]
            n_chunks = new_chunks or old_chunks
            durations.append(int(dur))
            coff = off + 16
            for _c in range(n_chunks):
                if coff + 6 > len(data):
                    break
                csize, ctype = struct.unpack_from("<IH", data, coff)
                if csize < 6:
                    break
                if ctype == 0x2018 and not tags:
                    p = coff + 6
                    n_tags = struct.unpack_from("<H", data, p)[0]
                    p += 10
                    for _t in range(n_tags):
                        a, b, direction = struct.unpack_from("<HHB", data, p)
                        p += 17
                        slen = struct.unpack_from("<H", data, p)[0]
                        p += 2
                        name = data[p:p + slen].decode("utf-8", "replace")
                        p += slen
                        tags.append((name, int(a), int(b), int(direction)))
                coff += csize
            off += fsize
        return AsepriteMeta(int(w), int(h), int(n_frames), durations, tags)
    except Exception as exc:
        print(f"[SPRITE ANALYZER WARNING] Could not parse Aseprite file {path!r}: {exc}")
        return None


def _find_aseprite_sibling(path: str) -> Optional[str]:
    folder = os.path.dirname(path) or "."
    target = _norm_stem(os.path.basename(path))
    if not target:
        return None
    try:
        ase_files = [f for f in os.listdir(folder) if f.lower().endswith(ASEPRITE_EXTS)]
    except OSError:
        return None
    exact = [f for f in ase_files if _norm_stem(f) == target]
    if exact:
        return os.path.join(folder, exact[0])
    # e.g. "GandalfHardcore Old Demon.ase" ↔ "Old Demon.png"
    fuzzy = [f for f in ase_files if _norm_stem(f).endswith(target) or target.endswith(_norm_stem(f))]
    fuzzy = [f for f in fuzzy if len(_norm_stem(f)) >= 4]
    if fuzzy:
        fuzzy.sort(key=lambda f: abs(len(_norm_stem(f)) - len(target)))
        return os.path.join(folder, fuzzy[0])
    return None


def _from_aseprite(path: str, w: int, h: int, mask_fn) -> Optional[SheetLayout]:
    ase = _find_aseprite_sibling(path)
    if not ase:
        return None
    meta = read_aseprite_meta(ase)
    if meta is None:
        return None
    fw, fh = meta.width, meta.height
    if (fw, fh) == (w, h):
        return None  # exported a single canvas (e.g. tileset/background) — nothing to slice
    if w % fw or h % fh:
        return None
    cols, rows = w // fw, h // fh
    rects, _, _ = _grid_rects(w, h, fw, fh)
    mask = mask_fn()
    occ = _occupancy(mask, fw, fh) if mask is not None else None

    clips = _aseprite_clips(meta, cols, rows, occ)
    return SheetLayout(path, w, h, rects, clips, KIND_SHEET if len(rects) > 1 else KIND_SINGLE,
                       "aseprite", fw, fh, cols, rows)


def _aseprite_clips(meta: AsepriteMeta, cols: int, rows: int, occ) -> list[Clip]:
    n_cells = cols * rows
    # Build the tag sequence; untagged frame runs become their own clips.
    spans: list[tuple[str, int, int, int]] = []
    covered = set()
    for name, a, b, d in sorted(meta.tags, key=lambda t: t[1]):
        a, b = max(0, a), min(meta.frames - 1, b)
        if a > b:
            continue
        spans.append((name, a, b, d))
        covered.update(range(a, b + 1))
    run_start = None
    extra: list[tuple[str, int, int, int]] = []
    for i in range(meta.frames + 1):
        if i < meta.frames and i not in covered:
            run_start = i if run_start is None else run_start
        elif run_start is not None:
            extra.append(("Untagged" if not spans else f"Frames {run_start}-{i - 1}", run_start, i - 1, 0))
            run_start = None
    spans = sorted(spans + extra, key=lambda t: t[1])

    def _dur(a: int, b: int) -> int:
        return _mode(meta.durations[a:b + 1]) if meta.durations else 0

    # Layout A: every tag starts on a new row (Aseprite "split tags" export).
    layout_a: list[tuple[str, tuple[int, ...], int, int]] = []
    row = 0
    ok_a = True
    for name, a, b, d in spans:
        n = b - a + 1
        idx = tuple(row * cols + k for k in range(n))
        if idx and idx[-1] >= n_cells:
            ok_a = False
            break
        layout_a.append((name, idx, d, _dur(a, b)))
        row += -(-n // cols)
    # Layout B: frames packed row-major.
    layout_b = [(name, tuple(range(a, b + 1)), d, _dur(a, b)) for name, a, b, d in spans]
    ok_b = meta.frames <= n_cells

    def _fit(layout) -> float:
        if occ is None:
            return 0.0
        pred = set(i for _, idx, _, _ in layout for i in idx)
        flat = occ.reshape(-1)
        hits = sum(1 for i in range(min(len(flat), n_cells)) if (i in pred) == bool(flat[i]))
        return hits / max(1, n_cells)

    candidates = []
    if ok_a:
        candidates.append((_fit(layout_a), 1, layout_a))
    if ok_b:
        candidates.append((_fit(layout_b), 0, layout_b))
    if not candidates:
        return _row_clips(cols, rows, occ, n_cells)
    candidates.sort(key=lambda c: (c[0], c[1]), reverse=True)
    chosen = candidates[0][2]
    clips: list[Clip] = []
    for name, idx, d, dur in chosen:
        if d == 1:  # reverse
            idx = idx[::-1]
        elif d == 2:  # ping-pong
            idx = idx + idx[-2:0:-1]
        clips.append(Clip(name or f"Tag {len(clips) + 1}", idx, dur))
    if len(spans) == 1 and spans[0][0] == "Untagged":
        clips = [Clip("Default", clips[0].indices, clips[0].frame_ms)]
    return clips


# ════════════════════════════════════════════════════════════════════════════
# 3/4/5. Filename hints, alpha-grid analysis, square strips
# ════════════════════════════════════════════════════════════════════════════

def _alpha_mask(surf: pg.Surface):
    """Boolean (H, W) opacity mask. Handles colour-keyed / opaque sheets."""
    if np is None:
        return None
    try:
        s = surf if surf.get_flags() & pg.SRCALPHA else surf.convert_alpha()
    except pg.error:
        s = surf
    try:
        alpha = pg.surfarray.array_alpha(s).T
    except Exception:
        return None
    mask = alpha > _ALPHA_THRESHOLD
    if mask.size and mask.all():
        # Fully opaque — maybe a solid background colour shared by all corners.
        try:
            rgb = pg.surfarray.array3d(s).transpose(1, 0, 2)
        except Exception:
            return mask
        corners = {tuple(rgb[0, 0]), tuple(rgb[0, -1]), tuple(rgb[-1, 0]), tuple(rgb[-1, -1])}
        if len(corners) == 1:
            bg = np.array(next(iter(corners)), dtype=rgb.dtype)
            mask = np.any(rgb != bg, axis=2)
    return mask


def _divisors(n: int, lo: int) -> list[int]:
    return [d for d in range(max(1, lo), n + 1) if n % d == 0] or [n]


def _cut_fraction(mask, f: int, axis: int) -> float:
    """Fraction of grid-line length that slices between two opaque pixels."""
    size = mask.shape[axis]
    n = size // f
    if n <= 1:
        return 0.0
    idx = np.arange(1, n) * f
    if axis == 1:
        cut = np.count_nonzero(mask[:, idx - 1] & mask[:, idx])
        length = mask.shape[0] * (n - 1)
    else:
        cut = np.count_nonzero(mask[idx - 1, :] & mask[idx, :])
        length = mask.shape[1] * (n - 1)
    return cut / max(1, length)


def _occupancy(mask, fw: int, fh: int):
    H, W = mask.shape
    cols, rows = W // fw, H // fh
    if cols == 0 or rows == 0:
        return None
    cells = mask[: rows * fh, : cols * fw].reshape(rows, fh, cols, fw).sum(axis=(1, 3))
    return cells > max(2, int(0.002 * fw * fh))


def _interior_ratio(occ) -> float:
    rows = occ.shape[0]
    holes = 0
    last_row = -1
    for r in range(rows):
        nz = np.nonzero(occ[r])[0]
        if len(nz):
            holes += int(np.count_nonzero(~occ[r, : nz[-1] + 1]))
            last_row = r
    # Entirely empty rows sandwiched between used rows are holes too.
    for r in range(max(0, last_row)):
        if not occ[r].any():
            holes += occ.shape[1]
    return holes / max(1, int(occ.sum()))


def _frames_look_alike(mask, fw: int, fh: int, occ) -> bool:
    """Neighbouring frames of an animation overlap heavily in cell space."""
    scores = []
    rows, cols = occ.shape
    for r in range(rows):
        prev = None
        for c in range(cols):
            if not occ[r, c]:
                prev = None
                continue
            cell = mask[r * fh:(r + 1) * fh, c * fw:(c + 1) * fw]
            ys = np.nonzero(cell.any(axis=1))[0]
            xs = np.nonzero(cell.any(axis=0))[0]
            box = (xs[0], ys[0], xs[-1] + 1, ys[-1] + 1)
            if prev is not None:
                ix = max(0, min(box[2], prev[2]) - max(box[0], prev[0]))
                iy = max(0, min(box[3], prev[3]) - max(box[1], prev[1]))
                a1 = (box[2] - box[0]) * (box[3] - box[1])
                a2 = (prev[2] - prev[0]) * (prev[3] - prev[1])
                scores.append((ix * iy) / max(1, min(a1, a2)))
            prev = box
    if not scores:
        return True  # single frame per row — nothing to compare
    return float(np.mean(scores)) >= _SIMILARITY_FLOOR


def _detect_grid(mask) -> Optional[tuple[int, int]]:
    H, W = mask.shape
    if H == 0 or W == 0 or not mask.any():
        return None
    lo = 8 if min(W, H) <= 64 else 16
    good_w = [fw for fw in _divisors(W, min(lo, W)) if _cut_fraction(mask, fw, 1) <= _CUT_TOLERANCE]
    good_h = [fh for fh in _divisors(H, min(lo, H)) if _cut_fraction(mask, fh, 0) <= _CUT_TOLERANCE]
    pairs = sorted(((fw, fh) for fw in good_w for fh in good_h), key=lambda p: (p[0] * p[1], p[0]))
    for fw, fh in pairs:
        if fw == W and fh == H:
            return None
        occ = _occupancy(mask, fw, fh)
        if occ is None or int(occ.sum()) < 2:
            continue
        if _interior_ratio(occ) > _INTERIOR_TOLERANCE:
            continue
        if not _frames_look_alike(mask, fw, fh, occ):
            continue
        return fw, fh
    return None


def _row_clips(cols: int, rows: int, occ, n_rects: int) -> list[Clip]:
    """One clip per used row (trailing empty cells trimmed)."""
    clips: list[Clip] = []
    for r in range(rows):
        if occ is not None:
            nz = np.nonzero(occ[r])[0]
            if not len(nz):
                continue
            count = int(nz[-1]) + 1
        else:
            count = cols
        idx = tuple(i for i in range(r * cols, r * cols + count) if i < n_rects)
        if idx:
            clips.append(Clip(f"Row {r + 1}", idx))
    if len(clips) == 1:
        clips = [Clip("Default", clips[0].indices)]
    elif len(clips) > 1:
        all_idx = tuple(i for c in clips for i in c.indices)
        clips.append(Clip("All frames", all_idx))
    if not clips:
        clips = [Clip("Default", tuple(range(n_rects)))]
    return clips


def _grid_layout(path: str, w: int, h: int, fw: int, fh: int, mask, source: str) -> SheetLayout:
    rects, cols, rows = _grid_rects(w, h, fw, fh)
    occ = _occupancy(mask, fw, fh) if mask is not None else None
    clips = _row_clips(cols, rows, occ, len(rects))
    return SheetLayout(path, w, h, rects, clips, KIND_SHEET if len(rects) > 1 else KIND_SINGLE,
                       source, fw, fh, cols, rows)


def _classify(path: str, layout: SheetLayout, mask) -> str:
    base_tokens = _tokens(os.path.splitext(os.path.basename(path))[0])
    dir_tokens = _tokens(os.path.basename(os.path.dirname(path)))
    if base_tokens & _TILESET_TOKENS:
        return KIND_TILESET
    if layout.frame_count > 1 and layout.source in ("sidecar-json", "aseprite", "filename"):
        return KIND_SHEET  # explicit metadata beats keyword guesses
    if layout.frame_count <= 1:
        if base_tokens & _BG_FILE_TOKENS:
            return KIND_BACKGROUND
        if dir_tokens & _BG_DIR_TOKENS and layout.width >= 320:
            return KIND_BACKGROUND
        if mask is not None and layout.width >= 800 and float(mask.mean()) >= 0.85:
            return KIND_BACKGROUND
        if dir_tokens & _TILESET_TOKENS and layout.width >= 256 and layout.height >= 128:
            return KIND_TILESET
        return KIND_SINGLE
    return KIND_SHEET


def analyze_image(path: str) -> Optional[SheetLayout]:
    """Work out how an image file is divided into frames and clips (cached)."""
    path = _resolve(path)
    if not path or not os.path.isfile(path) or not _is_image(path):
        return None
    key = _stat_key(path)
    cached = _LAYOUT_CACHE.get(key)
    if cached is not None:
        return cached

    surf = _load_surface(path)
    if surf is None:
        return None
    w, h = surf.get_size()
    _mask_holder: dict = {}

    def mask_fn():
        if "m" not in _mask_holder:
            _mask_holder["m"] = _alpha_mask(surf)
        return _mask_holder["m"]

    layout = _from_sidecar(path, w, h) or _from_aseprite(path, w, h, mask_fn)

    if layout is None:
        m = re.search(r"_strip(\d+)", os.path.basename(path), re.IGNORECASE)
        if m and int(m.group(1)) > 0 and w // int(m.group(1)) > 0:
            n = int(m.group(1))
            layout = _grid_layout(path, w, h, w // n, h, None, "filename")
            layout.rects = layout.rects[:n]
            layout.clips = [Clip("Default", tuple(range(len(layout.rects))))]

    if layout is None:
        mask = mask_fn()
        grid = _detect_grid(mask) if mask is not None else None
        if grid:
            layout = _grid_layout(path, w, h, grid[0], grid[1], mask, "alpha-grid")

    if layout is None and h > 0 and w > h and w % h == 0:
        layout = _grid_layout(path, w, h, h, h, None, "square-strip")
    elif layout is None and w > 0 and h > w and h % w == 0 and h // w <= 64:
        layout = _grid_layout(path, w, h, w, w, None, "square-strip")

    if layout is None:
        layout = SheetLayout(path, w, h, [(0, 0, w, h)], [Clip("Default", (0,))], KIND_SINGLE,
                             "single", w, h, 1, 1)

    layout.kind = _classify(path, layout, mask_fn() if layout.frame_count <= 1 else None)
    _LAYOUT_CACHE[key] = layout
    return layout


# ════════════════════════════════════════════════════════════════════════════
# Directory / path resolution
# ════════════════════════════════════════════════════════════════════════════

def _looks_like_frame_sequence(files: list[str], folder: str) -> bool:
    if len(files) < 2:
        return False
    stems = [os.path.splitext(f)[0] for f in files]
    numbered = [re.sub(r"\d+", "#", s).lower() for s in stems if re.search(r"\d", s)]
    if len(numbered) == len(stems) and len(set(numbered)) <= max(1, len(stems) // 4):
        return True
    sizes = {_image_size(os.path.join(folder, f)) for f in files}
    sizes.discard(None)
    return len(sizes) == 1


def describe_source(path: str) -> SpriteSource:
    """Classify a ``sprite_dir`` value (folder or image file)."""
    path = _resolve(path or "")
    if not path or not os.path.exists(path):
        return SpriteSource(path, SRC_MISSING)
    if os.path.isfile(path):
        layout = analyze_image(path)
        if layout is None:
            return SpriteSource(path, SRC_EMPTY)
        return SpriteSource(path, layout.kind, layout, [path], path)

    key = _dir_key(path)
    cached = _SOURCE_CACHE.get(key)
    if cached is not None:
        return cached

    try:
        files = sorted((f for f in os.listdir(path)
                        if _is_image(f) and os.path.isfile(os.path.join(path, f))), key=_natural_key)
    except OSError:
        files = []
    full = [os.path.join(path, f) for f in files]

    if not files:
        src = SpriteSource(path, SRC_EMPTY)
    elif len(files) == 1:
        layout = analyze_image(full[0])
        kind = layout.kind if layout else SRC_EMPTY
        src = SpriteSource(path, kind, layout, full, full[0])
    elif any("_strip" in f.lower() for f in files):
        primary = next(p for p, f in zip(full, files) if "_strip" in f.lower())
        layout = analyze_image(primary)
        src = SpriteSource(path, layout.kind if layout else SRC_EMPTY, layout, full, primary)
    elif _looks_like_frame_sequence(files, path):
        src = SpriteSource(path, SRC_SEQUENCE, None, full, None)
    else:
        primary, layout = _pick_primary(full)
        src = SpriteSource(path, SRC_COLLECTION, layout, full, primary)

    _SOURCE_CACHE[key] = src
    return src


def _pick_primary(files: list[str]) -> tuple[Optional[str], Optional[SheetLayout]]:
    best: tuple[float, Optional[str], Optional[SheetLayout]] = (-1.0, None, None)
    for p in files:
        layout = analyze_image(p)
        if layout is None or layout.kind not in (KIND_SHEET, KIND_SINGLE):
            continue
        tokens = _tokens(os.path.basename(p))
        score = 0.0
        if tokens & set(IDLE_KEYWORDS):
            score += 4
        if layout.kind == KIND_SHEET:
            score += 2 + min(1.0, layout.frame_count / 32)
        else:
            score += 1
        if layout.find_clip(IDLE_KEYWORDS):
            score += 1
        if score > best[0]:
            best = (score, p, layout)
    return best[1], best[2]


# ════════════════════════════════════════════════════════════════════════════
# Frame loading
# ════════════════════════════════════════════════════════════════════════════

def _slice(layout: SheetLayout, clip: Clip) -> list[pg.Surface]:
    surf = _load_surface(layout.path)
    if surf is None:
        return []
    out: list[pg.Surface] = []
    bounds = surf.get_rect()
    for i in clip.indices:
        if 0 <= i < len(layout.rects):
            r = pg.Rect(layout.rects[i]).clip(bounds)
            if r.w > 0 and r.h > 0:
                out.append(surf.subsurface(r).copy())
    return out


def _load_sequence(files: list[str]) -> list[pg.Surface]:
    frames = []
    for p in files:
        s = _load_surface(p)
        if s is not None:
            frames.append(s)
    return frames


def _load_gif_frames(path: str) -> list[pg.Surface]:
    loader = getattr(pg.image, "load_animation", None)  # pygame-ce >= 2.5
    if loader is None:
        return []
    try:
        return [fr for fr, _delay in loader(path)]
    except Exception:
        return []


def load_named_animation(path: str, selector=None, *, strict: bool = False) -> tuple[list[pg.Surface], Optional[Clip]]:
    """Load frames for ``path`` and also return the clip that was used.

    ``selector`` may be ``None`` (prefer an idle-like clip), a clip name,
    an index, or a keyword list. With ``strict=True`` a selector that does
    not match any clip returns no frames instead of falling back.
    """
    src = describe_source(path)
    if src.kind in (SRC_MISSING, SRC_EMPTY):
        return [], None
    if src.kind == SRC_SEQUENCE:
        if strict and selector is not None:
            return [], None
        return _load_sequence(src.files), None
    layout = src.layout
    if layout is None:
        return [], None
    if layout.path.lower().endswith(".gif") and layout.frame_count <= 1:
        gif = _load_gif_frames(layout.path)
        if gif:
            return gif, Clip("Default", tuple(range(len(gif))))
    clip = layout.find_clip(selector)
    if clip is None:
        if strict:
            return [], None
        clip = layout.find_clip(None)
    if clip is None:
        return [], None
    return _slice(layout, clip), clip


def load_animation(path: str, selector=None, *, strict: bool = False) -> list[pg.Surface]:
    """Smart replacement for ``AssetManager.get_animation_frames``.

    Works for frame folders, single images, strips and multi-row sheets,
    returning only the frames of ONE animation (never the whole sheet).
    """
    frames, _clip = load_named_animation(path, selector, strict=strict)
    return frames
