"""
Level Spawner Editor v2  —  Wizard-Style Plugin
Run from the Pixel-Runner project root: python level_editor.py

Stage flow:
  1  Level Select   — pick level_*.json
  2  Event List     — view / delete events, choose what to add
  3  Event Builder  — step-by-step event configuration + folder browser
  4  Review & Commit— diff view + transactional flock write with rollback
"""

import os, sys, json, fcntl, copy, math
from typing import Optional
import pygame as pg

sys.path.insert(0, os.path.dirname(__file__))
from src.game.entities.hitbox_registry import HitboxRegistry, HitboxMargins
from src.game.systems.environment_manager import EnvironmentManager, EnvironmentProp
from v3x_zulfiqar_gideon import AssetManager

# ── Colour tokens ──────────────────────────────────────────────────────────
BG      = (14,  14,  20)
PANEL   = (22,  22,  33)
PANEL2  = (30,  30,  45)
BORDER  = (50,  50,  70)
ACCENT  = (100, 150, 255)
ACCH    = (130, 175, 255)
DANGER  = (231,  76,  60)
DANGH   = (255, 106,  90)
SUCCESS = ( 46, 204, 113)
SUCC_H  = ( 70, 230, 140)
WARN    = (241, 196,  15)
TXT     = (240, 240, 240)
TXT2    = (160, 160, 180)
TXT3    = (100, 100, 120)

W, H       = 1280, 720
TOPBAR_H   = 58
BTMBAR_H   = 60
CONTENT_Y  = TOPBAR_H + 4
CONTENT_H  = H - TOPBAR_H - BTMBAR_H - 8

STAGE_NAMES = {1: "Select Level", 2: "Event List",
               3: "Event Builder", 4: "Review & Commit", 5: "Visual World Canvas"}


# ── Shared UI components ───────────────────────────────────────────────────

class Button:
    _STYLES = {
        "ghost":   (PANEL2, (45,45,62), TXT),
        "primary": (ACCENT, ACCH,       TXT),
        "danger":  (DANGER, DANGH,      TXT),
        "success": (SUCCESS, SUCC_H,    TXT),
        "warn":    (WARN,   (255,215,40),(20,20,20)),
    }

    def __init__(self, label: str, x: int, y: int, w: int, h: int,
                 cb, style: str = "ghost", enabled: bool = True):
        self.label   = label
        self.rect    = pg.Rect(x, y, w, h)
        self.cb      = cb
        self.style   = style
        self.enabled = enabled

    def draw(self, surf: pg.Surface, font: pg.font.Font):
        base, hover, tcol = self._STYLES.get(self.style, self._STYLES["ghost"])
        col = (TXT3[0]-20, TXT3[1]-20, TXT3[2]-20) if not self.enabled \
              else (hover if self.rect.collidepoint(pg.mouse.get_pos()) else base)
        pg.draw.rect(surf, col,    self.rect, border_radius=7)
        pg.draw.rect(surf, BORDER, self.rect, width=1, border_radius=7)
        t = font.render(self.label, True, TXT3 if not self.enabled else tcol)
        surf.blit(t, t.get_rect(center=self.rect.center))

    def on(self, event: pg.event.Event):
        if self.enabled and event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self.cb()


class TextInput:
    def __init__(self, label: str, x: int, y: int, w: int, h: int = 36,
                 initial: str = "", placeholder: str = ""):
        self.label, self.rect = label, pg.Rect(x, y, w, h)
        self.val, self.placeholder, self.active = str(initial), placeholder, False

    def draw(self, surf: pg.Surface, f: pg.font.Font, lf: pg.font.Font):
        surf.blit(lf.render(self.label, True, TXT2), (self.rect.x, self.rect.y - 21))
        pg.draw.rect(surf, PANEL2 if not self.active else (40,40,60), self.rect, border_radius=6)
        pg.draw.rect(surf, ACCENT if self.active else BORDER, self.rect, width=2, border_radius=6)
        disp = self.val if self.val else self.placeholder
        tcol = TXT if self.val else TXT3
        t = f.render(disp, True, tcol)
        clip = pg.Rect(self.rect.x+8, self.rect.y, self.rect.w-16, self.rect.h)
        surf.set_clip(clip)
        bx = self.rect.x + 8
        if t.get_width() > self.rect.w - 16:
            bx = self.rect.x + 8 + self.rect.w - 16 - t.get_width()
        surf.blit(t, (bx, self.rect.y + (self.rect.h - t.get_height()) // 2))
        surf.set_clip(None)
        if self.active and (pg.time.get_ticks() // 500) % 2 == 0:
            cx = min(self.rect.x + 8 + t.get_width(), self.rect.right - 8)
            pg.draw.line(surf, TXT, (cx, self.rect.y+6), (cx, self.rect.bottom-6), 2)

    def on(self, event: pg.event.Event):
        if event.type == pg.MOUSEBUTTONDOWN:
            self.active = self.rect.collidepoint(event.pos)
        elif event.type == pg.KEYDOWN and self.active:
            if event.key == pg.K_BACKSPACE: self.val = self.val[:-1]
            elif event.key == pg.K_RETURN:  self.active = False
            elif event.unicode.isprintable(): self.val += event.unicode


class TextArea:
    """Multiline text area component with auto-wrapping, vertical scrolling, and line/char counters."""

    def __init__(self, label: str, x: int, y: int, w: int, h: int = 110,
                 initial: str = "", placeholder: str = ""):
        self.label = label
        self.rect = pg.Rect(x, y, w, h)
        self.val = str(initial)
        self.placeholder = placeholder
        self.active = False
        self.scroll = 0

    def _wrap_text(self, f: pg.font.Font, max_w: int) -> list[str]:
        lines: list[str] = []
        raw_paragraphs = self.val.split("\n") if self.val else [""]
        for paragraph in raw_paragraphs:
            if not paragraph:
                lines.append("")
                continue
            words = paragraph.split(" ")
            curr_line = ""
            for word in words:
                test_line = f"{curr_line} {word}".strip() if curr_line else word
                if f.size(test_line)[0] <= max_w:
                    curr_line = test_line
                else:
                    if curr_line:
                        lines.append(curr_line)
                    curr_line = word
            if curr_line:
                lines.append(curr_line)
        return lines

    def draw(self, surf: pg.Surface, f: pg.font.Font, lf: pg.font.Font):
        # Label above
        surf.blit(lf.render(self.label, True, TXT2), (self.rect.x, self.rect.y - 21))

        # Background and border
        bg_col = (35, 38, 55) if self.active else PANEL2
        border_col = ACCENT if self.active else BORDER
        pg.draw.rect(surf, bg_col, self.rect, border_radius=6)
        pg.draw.rect(surf, border_col, self.rect, width=2 if self.active else 1, border_radius=6)

        max_text_w = self.rect.w - 24
        wrapped_lines = self._wrap_text(f, max_text_w)

        # Character & Line counter badge at top right
        info_text = f"{len(self.val)} chars  ·  {len(wrapped_lines)} lines"
        info_surf = lf.render(info_text, True, WARN if self.active else TXT3)
        surf.blit(info_surf, (self.rect.right - info_surf.get_width() - 4, self.rect.y - 21))

        # Clipping container
        clip_rect = pg.Rect(self.rect.x + 8, self.rect.y + 6, self.rect.w - 20, self.rect.h - 12)
        surf.set_clip(clip_rect)

        line_h = f.get_linesize() + 3
        total_h = len(wrapped_lines) * line_h
        max_scroll = max(0, total_h - clip_rect.h)
        self.scroll = max(0, min(self.scroll, max_scroll))

        # Render wrapped lines
        tcol = TXT if self.val else TXT3
        if not self.val and self.placeholder:
            ph = f.render(self.placeholder, True, TXT3)
            surf.blit(ph, (self.rect.x + 10, self.rect.y + 8))
        else:
            for i, line_str in enumerate(wrapped_lines):
                ly = self.rect.y + 8 + i * line_h - self.scroll
                if ly + line_h < clip_rect.y or ly > clip_rect.bottom:
                    continue
                t_surf = f.render(line_str, True, tcol)
                surf.blit(t_surf, (self.rect.x + 10, ly))

        # Blinking cursor at the end of the text when active
        if self.active and (pg.time.get_ticks() // 500) % 2 == 0:
            last_line = wrapped_lines[-1] if wrapped_lines else ""
            last_line_idx = len(wrapped_lines) - 1 if wrapped_lines else 0
            cursor_x = self.rect.x + 10 + f.size(last_line)[0]
            cursor_y = self.rect.y + 8 + last_line_idx * line_h - self.scroll
            if clip_rect.y <= cursor_y <= clip_rect.bottom:
                pg.draw.line(surf, TXT, (cursor_x + 2, cursor_y + 2), (cursor_x + 2, cursor_y + line_h - 2), 2)

        surf.set_clip(None)

        # Scrollbar if text exceeds height
        if total_h > clip_rect.h:
            bar_h = max(16, int(clip_rect.h * clip_rect.h / total_h))
            bar_y = clip_rect.y + int(self.scroll * (clip_rect.h - bar_h) / max(1, max_scroll))
            pg.draw.rect(surf, BORDER, pg.Rect(self.rect.right - 8, bar_y, 5, bar_h), border_radius=3)

    def on(self, event: pg.event.Event):
        if event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
            self.active = self.rect.collidepoint(event.pos)
        elif event.type == pg.MOUSEWHEEL and self.rect.collidepoint(pg.mouse.get_pos()):
            self.scroll -= event.y * 22
        elif event.type == pg.KEYDOWN and self.active:
            if event.key == pg.K_BACKSPACE:
                self.val = self.val[:-1]
            elif event.key == pg.K_RETURN:
                self.val += "\n"
            elif event.key == pg.K_TAB:
                self.val += "    "
            elif event.unicode and event.unicode.isprintable():
                self.val += event.unicode


class Slider:
    def __init__(self, label: str, x: int, y: int, w: int,
                 mn: float, mx: float, val: float, is_float: bool = False):
        self.label, self.track = label, pg.Rect(x, y, w, 8)
        self.mn, self.mx, self.val, self.is_float = mn, mx, val, is_float
        self.dragging, self._r = False, 11

    def _hx(self):
        span = self.mx - self.mn
        r = 0.0 if span == 0 else (self.val - self.mn) / span
        return int(self.track.x + r * self.track.w)

    def draw(self, surf: pg.Surface, f: pg.font.Font, lf: pg.font.Font):
        vs = f"{self.val:.2f}" if self.is_float else str(int(self.val))
        surf.blit(lf.render(f"{self.label}:  {vs}", True, TXT2),
                  (self.track.x, self.track.y - 22))
        pg.draw.rect(surf, BORDER, self.track, border_radius=4)
        hx = self._hx()
        pg.draw.rect(surf, ACCENT,
                     pg.Rect(self.track.x, self.track.y, hx - self.track.x, self.track.h),
                     border_radius=4)
        pg.draw.circle(surf, TXT,  (hx, self.track.centery), self._r)
        if self.dragging:
            pg.draw.circle(surf, ACCH, (hx, self.track.centery), self._r - 3)

    def _set(self, mx: int):
        r = max(0.0, min(1.0, (mx - self.track.x) / self.track.w))
        raw = self.mn + r * (self.mx - self.mn)
        self.val = round(raw, 2) if self.is_float else int(round(raw))

    def on(self, event: pg.event.Event):
        hx = self._hx()
        if event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
            d = ((event.pos[0]-hx)**2 + (event.pos[1]-self.track.centery)**2)**0.5
            if d <= self._r + 5 or self.track.collidepoint(event.pos):
                self.dragging = True
                self._set(event.pos[0])
        elif event.type == pg.MOUSEBUTTONUP: self.dragging = False
        elif event.type == pg.MOUSEMOTION and self.dragging: self._set(event.pos[0])


class FolderBrowser:
    """Scrollable directory tree rooted at `root`. Selectable leaf folders contain PNGs."""
    ROW_H = 30
    IND   = 18

    def __init__(self, root: str, rect: pg.Rect, allow_parent: bool = False):
        self.root, self.rect = root, rect
        self.allow_parent = allow_parent
        self.expanded: set[str] = set()
        self.selected: Optional[str] = None
        self.scroll = 0
        self._visible: list[dict] = []
        self._rebuild()

    def _rebuild(self):
        self._visible = []
        self._walk(self.root, 0)

    def _walk(self, path: str, depth: int):
        try: entries = sorted(e for e in os.listdir(path)
                               if os.path.isdir(os.path.join(path, e)))
        except OSError: return
        for name in entries:
            fp = os.path.join(path, name)
            try:
                children = [e for e in os.listdir(fp)
                            if os.path.isdir(os.path.join(fp, e))]
                pngs = [e for e in os.listdir(fp)
                        if e.lower().endswith(".png") and
                        os.path.isfile(os.path.join(fp, e))]
            except OSError: children, pngs = [], []
            self._visible.append({
                "path": fp, "name": name, "depth": depth,
                "has_pngs": len(pngs) > 0, "has_children": len(children) > 0,
            })
            if fp in self.expanded:
                self._walk(fp, depth + 1)

    def draw(self, surf: pg.Surface, font: pg.font.Font, lf: pg.font.Font):
        surf.blit(lf.render("Sprite Folder", True, TXT2), (self.rect.x, self.rect.y - 22))
        pg.draw.rect(surf, PANEL, self.rect, border_radius=6)
        pg.draw.rect(surf, BORDER, self.rect, width=1, border_radius=6)
        surf.set_clip(self.rect)

        total_h = len(self._visible) * self.ROW_H
        self.scroll = max(0, min(self.scroll, max(0, total_h - self.rect.h)))
        m = pg.mouse.get_pos()

        for i, item in enumerate(self._visible):
            y = self.rect.y + i * self.ROW_H - self.scroll
            if y + self.ROW_H < self.rect.y or y > self.rect.bottom:
                continue
            row = pg.Rect(self.rect.x, y, self.rect.w, self.ROW_H)
            is_sel = item["path"] == self.selected
            is_hov = row.collidepoint(m) and self.rect.collidepoint(m)
            if is_sel:
                pg.draw.rect(surf, (40, 55, 90), row)
            elif is_hov:
                pg.draw.rect(surf, PANEL2, row)

            x = self.rect.x + 8 + item["depth"] * self.IND
            # Arrow
            if item["has_children"]:
                arrow = "▾" if item["path"] in self.expanded else "▸"
                surf.blit(font.render(arrow, True, TXT2),
                          (x, y + (self.ROW_H - font.size(arrow)[1]) // 2))
            x += 14
            # Name
            is_selectable = item["has_pngs"] or (self.allow_parent and item["has_children"])
            col = WARN if is_sel else (TXT if is_selectable else TXT2)
            surf.blit(font.render(item["name"], True, col),
                      (x, y + (self.ROW_H - font.size(item["name"])[1]) // 2))
            # SELECT badge
            if is_selectable:
                badge = font.render("[SELECT]", True, SUCCESS if is_sel else TXT3)
                surf.blit(badge, (self.rect.right - badge.get_width() - 8,
                                  y + (self.ROW_H - badge.get_height()) // 2))

        surf.set_clip(None)

        # Scroll bar
        if total_h > self.rect.h:
            bar_h = max(20, int(self.rect.h * self.rect.h / total_h))
            bar_y = self.rect.y + int(self.scroll * (self.rect.h - bar_h) /
                                       max(1, total_h - self.rect.h))
            pg.draw.rect(surf, BORDER,
                         pg.Rect(self.rect.right - 6, bar_y, 4, bar_h), border_radius=2)

    def on(self, event: pg.event.Event):
        if event.type == pg.MOUSEWHEEL and self.rect.collidepoint(pg.mouse.get_pos()):
            self.scroll -= event.y * self.ROW_H * 3
        elif event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
            if not self.rect.collidepoint(event.pos): return
            m = event.pos
            for i, item in enumerate(self._visible):
                y = self.rect.y + i * self.ROW_H - self.scroll
                row = pg.Rect(self.rect.x, y, self.rect.w, self.ROW_H)
                if row.collidepoint(m):
                    is_selectable = item["has_pngs"] or (self.allow_parent and item["has_children"])
                    if is_selectable:
                        self.selected = item["path"]
                    if item["has_children"]:
                        if item["path"] in self.expanded:
                            self.expanded.discard(item["path"])
                        else:
                            self.expanded.add(item["path"])
                        self._rebuild()
                    break


class ModalDialog:
    def __init__(self, title: str, body: str, confirm_cb, cancel_cb=None,
                 choices: list[str] | None = None, choice_cb=None):
        self.title, self.body = title, body
        self.confirm_cb, self.cancel_cb = confirm_cb, cancel_cb
        self.choices = choices or []
        self.choice_cb = choice_cb
        self.selected = -1
        self.choice_rects: list[pg.Rect] = []

    def _get_layout(self):
        N = len(self.choices)
        btn_y_offset = 145 if N == 0 else 125 + N * 38 + 15
        dw, dh = 540, btn_y_offset + 67
        dx, dy = (W - dw) // 2, (H - dh) // 2
        btn_y = dy + btn_y_offset
        return dw, dh, dx, dy, btn_y

    def draw(self, surf: pg.Surface, tf: pg.font.Font, f: pg.font.Font):
        overlay = pg.Surface((W, H), pg.SRCALPHA)
        overlay.fill((8, 8, 15, 210))
        surf.blit(overlay, (0, 0))

        dw, dh, dx, dy, btn_y = self._get_layout()
        dr = pg.Rect(dx, dy, dw, dh)
        pg.draw.rect(surf, PANEL, dr, border_radius=14)
        pg.draw.rect(surf, WARN,  dr, width=3,  border_radius=14)

        surf.blit(tf.render(self.title, True, WARN),
                  tf.render(self.title, True, WARN).get_rect(centerx=dr.centerx, y=dy+28))
        surf.blit(f.render(self.body, True, TXT),
                  f.render(self.body, True, TXT).get_rect(centerx=dr.centerx, y=dy+88))

        m = pg.mouse.get_pos()
        self.choice_rects = []
        cy = dy + 125
        for i, choice in enumerate(self.choices):
            cr = pg.Rect(dx + 40, cy, dw - 80, 30)
            self.choice_rects.append(cr)
            is_sel = i == self.selected
            is_hov = cr.collidepoint(m)
            col = ACCENT if is_sel else (PANEL2 if not is_hov else (50, 50, 70))
            pg.draw.rect(surf, col, cr, border_radius=6)
            pg.draw.rect(surf, BORDER, cr, width=1, border_radius=6)
            t = f.render(choice, True, TXT)
            surf.blit(t, t.get_rect(center=cr.center))
            cy += 38

        for rect, label, col, hov in [
            (pg.Rect(dx+40,  btn_y, 200, 42), "CONFIRM", SUCCESS, SUCC_H),
            (pg.Rect(dx+300, btn_y, 200, 42), "CANCEL",  DANGER,  DANGH),
        ]:
            c = hov if rect.collidepoint(m) else col
            pg.draw.rect(surf, c, rect, border_radius=8)
            t = f.render(label, True, TXT)
            surf.blit(t, t.get_rect(center=rect.center))

    def on(self, event: pg.event.Event):
        if event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
            dw, dh, dx, dy, btn_y = self._get_layout()
            clicked = False
            for i, rect in enumerate(self.choice_rects):
                if rect.collidepoint(event.pos):
                    self.selected = i
                    clicked = True
                    break
            if clicked:
                return
            for rect, label, col, hov in [
                (pg.Rect(dx+40,  btn_y, 200, 42), "CONFIRM", SUCCESS, SUCC_H),
                (pg.Rect(dx+300, btn_y, 200, 42), "CANCEL",  DANGER,  DANGH),
            ]:
                if rect.collidepoint(event.pos):
                    if label == "CONFIRM":
                        if self.choice_cb and self.selected >= 0:
                            self.choice_cb(self.selected)
                        self.confirm_cb()
                    else:
                        if self.cancel_cb: self.cancel_cb()
        elif event.type == pg.KEYDOWN:
            if event.key in (pg.K_RETURN, pg.K_y):
                if self.choice_cb and self.selected >= 0:
                    self.choice_cb(self.selected)
                self.confirm_cb()
            elif event.key in (pg.K_ESCAPE, pg.K_n):
                if self.cancel_cb: self.cancel_cb()


# ── Helpers ────────────────────────────────────────────────────────────────
def _npc_key(d: str) -> str:
    n = os.path.basename(d.rstrip("/"))
    if n.lower() == "idle":
        n = os.path.basename(os.path.dirname(d.rstrip("/")))
    return f"generic_npc_{n.lower()}"


def _registry_key(etype: str, npc_type: str = "", sprite_dir: str = "") -> str:
    """Return the exact key used by entity_dimensions.json / HitboxRegistry."""
    if etype == "npc":
        if npc_type == "wizard":
            return "wizard_npc"
        if sprite_dir:
            return _npc_key(sprite_dir)
    elif etype == "boss":
        if sprite_dir:
            return f"boss:{os.path.basename(sprite_dir.rstrip('/'))}"
        return "boss"
    return ""


def _scale_from_registry(etype: str, npc_type: str = "", sprite_dir: str = "", fallback: float = 1.0) -> float:
    """Keep level JSON scale in sync with entity_dimensions.json.

    The simulation compares the scale in the level event with the scale in
    entity_dimensions.json. If both are allowed to drift, the simulation should
    fail. This helper makes the registry the source of truth whenever a known
    key exists.
    """
    key = _registry_key(etype, npc_type, sprite_dir)
    if not key:
        return fallback
    try:
        return HitboxRegistry.get_margins(key).scale
    except Exception as e:
        if etype == "boss":
            try:
                return HitboxRegistry.get_margins("skeleton").scale
            except Exception:
                pass
        print(f"[WARN] Could not read registry scale for {key!r}: {e}")
        return fallback

from v3x_zulfiqar_gideon import AssetManager

def _load_preview(path: str, scale: float = 2.0) -> list[pg.Surface]:
    frames: list[pg.Surface] = []
    if not os.path.exists(path): return frames
    raw_frames = AssetManager.get_animation_frames(path)
    for img in raw_frames:
        w, h = img.get_size()
        frames.append(pg.transform.scale(img, (int(w*scale), int(h*scale))))
    return frames


class LinuxAssetExplorerModal:
    """Modern GTK/Linux File Manager styled asset explorer modal with clean path breadcrumbs, places sidebar, and visual file grid."""

    def __init__(self, select_cb, cancel_cb, current_dir: Optional[str] = None):
        self.select_cb = select_cb
        self.cancel_cb = cancel_cb
        self.rect = pg.Rect(W // 2 - 460, H // 2 - 280, 920, 560)
        self.current_dir = current_dir if (current_dir and os.path.exists(current_dir)) else "assets/graphics/background images"
        self.search_input = TextInput("", self.rect.right - 270, self.rect.y + 14, 210, 32, initial="", placeholder="Filter files...")
        self.page = 0
        self.per_page = 9
        self._thumb_cache: dict[str, Optional[pg.Surface]] = {}
        self.places = [
            {"name": "[BG] Background Images", "path": "assets/graphics/background images"},
            {"name": "[NEW] New BG Images", "path": "assets/graphics/background images/new_bg_images"},
            {"name": "[TREE] Winter Forest", "path": "assets/graphics/background images/Free Pixel Art Winter Forest"},
            {"name": "[PROP] Props & Decor", "path": "assets/graphics/Props"},
            {"name": "[TWR] RedMoonTower", "path": "assets/graphics/RedMoonTower"},
            {"name": "[HOME] Root Assets", "path": "assets/graphics"},
        ]
        self.entries = self._scan_directory()

    def _scan_directory(self) -> list[dict]:
        entries = []
        if not os.path.exists(self.current_dir):
            return entries

        query = self.search_input.val.lower().strip()
        try:
            items = sorted(os.listdir(self.current_dir))
            # 1. Subdirectories
            for item in items:
                full_p = os.path.join(self.current_dir, item).replace("\\", "/")
                if os.path.isdir(full_p):
                    if query and query not in item.lower():
                        continue
                    count = 0
                    for _, _, files in os.walk(full_p):
                        count += len([f for f in files if f.lower().endswith((".png", ".jpg", ".jpeg"))])
                    entries.append({
                        "type": "folder",
                        "name": item,
                        "path": full_p,
                        "count": count
                    })

            # 2. Image files
            for item in items:
                full_p = os.path.join(self.current_dir, item).replace("\\", "/")
                if os.path.isfile(full_p) and item.lower().endswith((".png", ".jpg", ".jpeg")):
                    if query and query not in item.lower():
                        continue
                    entries.append({
                        "type": "file",
                        "name": item,
                        "path": full_p
                    })
        except Exception:
            pass
        return entries

    def _navigate_to(self, new_dir: str):
        if os.path.exists(new_dir):
            self.current_dir = os.path.normpath(new_dir).replace("\\", "/")
            self.entries = self._scan_directory()
            self.page = 0

    def draw(self, surf: pg.Surface, font: pg.font.Font, sfont: pg.font.Font):
        overlay = pg.Surface((W, H), pg.SRCALPHA)
        overlay.fill((0, 0, 0, 210))
        surf.blit(overlay, (0, 0))

        pg.draw.rect(surf, PANEL, self.rect, border_radius=12)
        pg.draw.rect(surf, ACCENT, self.rect, width=2, border_radius=12)

        # ── 1. HEADER BAR & BREADCRUMBS ──────────────────────────────────────────
        up_parent = os.path.dirname(self.current_dir)
        can_up = os.path.exists(up_parent) and len(self.current_dir) > len("assets")

        def _do_up():
            if can_up: self._navigate_to(up_parent)

        up_btn = Button("^ Up", self.rect.x + 16, self.rect.y + 14, 55, 32, _do_up, "primary" if can_up else "ghost")
        up_btn.draw(surf, sfont)

        # Breadcrumb Container Pill
        path_rect = pg.Rect(self.rect.x + 80, self.rect.y + 14, 360, 32)
        pg.draw.rect(surf, (30, 34, 48), path_rect, border_radius=6)
        pg.draw.rect(surf, BORDER, path_rect, width=1, border_radius=6)

        rel_path = self.current_dir
        path_disp = rel_path if len(rel_path) <= 38 else f"...{rel_path[-35:]}"
        surf.blit(sfont.render(f"Path: {path_disp}", True, WARN), (path_rect.x + 10, path_rect.y + 8))

        # Search Input
        self.search_input.draw(surf, font, sfont)

        close_btn = Button("X", self.rect.right - 44, self.rect.y + 14, 32, 32, self.cancel_cb, "danger")
        close_btn.draw(surf, sfont)

        pg.draw.line(surf, BORDER, (self.rect.x, self.rect.y + 58), (self.rect.right, self.rect.y + 58), 1)

        # ── 2. PLACES SIDEBAR (LEFT) ─────────────────────────────────────────────
        side_rect = pg.Rect(self.rect.x, self.rect.y + 59, 210, self.rect.h - 104)
        pg.draw.rect(surf, PANEL2, side_rect, border_bottom_left_radius=12)
        pg.draw.line(surf, BORDER, (side_rect.right, side_rect.y), (side_rect.right, side_rect.bottom), 1)

        surf.blit(sfont.render("PLACES / SHORTCUTS", True, ACCENT), (side_rect.x + 14, side_rect.y + 12))

        py = side_rect.y + 36
        m_pos = pg.mouse.get_pos()
        for place in self.places:
            p_path = place["path"]
            p_name = place["name"]
            is_cur = (self.current_dir == p_path or self.current_dir.startswith(p_path + "/"))
            p_rect = pg.Rect(side_rect.x + 8, py, 194, 32)
            is_h = p_rect.collidepoint(m_pos)

            if is_cur or is_h:
                bg_c = (52, 152, 219) if is_cur else (45, 45, 65)
                pg.draw.rect(surf, bg_c, p_rect, border_radius=6)

            surf.blit(sfont.render(p_name, True, TXT if is_cur else (WARN if is_h else TXT2)), (p_rect.x + 8, py + 8))
            py += 36

        # ── 3. MAIN CONTENT VIEWPORT (FILES & FOLDERS GRID) ───────────────────────
        grid_rect = pg.Rect(side_rect.right + 1, self.rect.y + 59, self.rect.w - side_rect.w - 1, self.rect.h - 104)

        self.entries = self._scan_directory()
        start_idx = self.page * self.per_page
        end_idx = min(start_idx + self.per_page, len(self.entries))
        page_entries = self.entries[start_idx:end_idx]

        cols = 3
        for idx, entry in enumerate(page_entries):
            r = idx // cols
            c = idx % cols
            bx = grid_rect.x + 16 + c * 225
            by = grid_rect.y + 12 + r * 142
            card_rect = pg.Rect(bx, by, 215, 130)

            is_h = card_rect.collidepoint(m_pos)
            is_folder = (entry["type"] == "folder")

            bg_col = (45, 45, 65) if is_h else (PANEL2 if not is_folder else (32, 38, 52))
            border_col = ACCH if is_h else (BORDER if not is_folder else (52, 152, 219))

            pg.draw.rect(surf, bg_col, card_rect, border_radius=8)
            pg.draw.rect(surf, border_col, card_rect, width=2 if is_h else 1, border_radius=8)

            if is_folder:
                # Folder Icon Card
                tag_rect = pg.Rect(bx + 10, by + 10, 75, 22)
                pg.draw.rect(surf, (52, 152, 219), tag_rect, border_radius=4)
                surf.blit(sfont.render("DIR", True, TXT), (tag_rect.x + 22, tag_rect.y + 3))

                surf.blit(font.render(entry["name"][:18], True, WARN if is_h else TXT), (bx + 10, by + 38))
                surf.blit(sfont.render(f"{entry['count']} image files", True, TXT2), (bx + 10, by + 74))
                surf.blit(sfont.render("Click to open ->", True, SUCCESS if is_h else TXT2), (bx + 10, by + 98))
            else:
                # Image File Card
                path = entry["path"]
                if path not in self._thumb_cache:
                    try:
                        raw = AssetManager.get_texture(path)
                        sc = pg.transform.smoothscale(raw, (195, 76))
                        self._thumb_cache[path] = sc
                    except Exception:
                        self._thumb_cache[path] = None

                thumb = self._thumb_cache.get(path)
                if thumb:
                    surf.blit(thumb, (bx + 10, by + 8))

                surf.blit(sfont.render(entry["name"][:22], True, WARN if is_h else TXT), (bx + 10, by + 88))
                surf.blit(sfont.render(path[-28:], True, TXT2), (bx + 10, by + 106))

        # ── 4. FOOTER PAGINATION BAR ─────────────────────────────────────────────
        pg.draw.line(surf, BORDER, (self.rect.x, self.rect.bottom - 44), (self.rect.right, self.rect.bottom - 44), 1)

        max_pages = max(1, (len(self.entries) + self.per_page - 1) // self.per_page)
        p_str = f"Total Items: {len(self.entries)}  |  Page {self.page + 1} of {max_pages}"
        surf.blit(sfont.render(p_str, True, TXT2), (self.rect.x + 220, self.rect.bottom - 30))

        if self.page > 0:
            def _prev(): self.page -= 1
            Button("< Prev", self.rect.right - 180, self.rect.bottom - 36, 75, 28, _prev, "ghost").draw(surf, sfont)
        if self.page < max_pages - 1:
            def _next(): self.page += 1
            Button("Next >", self.rect.right - 95, self.rect.bottom - 36, 75, 28, _next, "ghost").draw(surf, sfont)

    def on(self, ev: pg.event.Event):
        self.search_input.on(ev)

        if ev.type == pg.MOUSEBUTTONDOWN and ev.button == 1:
            close_btn_rect = pg.Rect(self.rect.right - 44, self.rect.y + 14, 32, 32)
            if close_btn_rect.collidepoint(ev.pos):
                self.cancel_cb()
                return

            up_parent = os.path.dirname(self.current_dir)
            can_up = os.path.exists(up_parent) and len(self.current_dir) > len("assets")
            if can_up and pg.Rect(self.rect.x + 16, self.rect.y + 14, 55, 32).collidepoint(ev.pos):
                self._navigate_to(up_parent)
                return

            # Check Places Sidebar
            side_rect = pg.Rect(self.rect.x, self.rect.y + 59, 210, self.rect.h - 104)
            if side_rect.collidepoint(ev.pos):
                py = side_rect.y + 36
                for place in self.places:
                    p_rect = pg.Rect(side_rect.x + 8, py, 194, 32)
                    if p_rect.collidepoint(ev.pos):
                        self._navigate_to(place["path"])
                        return
                    py += 36

            # Check Pagination
            max_pages = max(1, (len(self.entries) + self.per_page - 1) // self.per_page)
            if self.page > 0 and pg.Rect(self.rect.right - 180, self.rect.bottom - 36, 75, 28).collidepoint(ev.pos):
                self.page -= 1
                return
            if self.page < max_pages - 1 and pg.Rect(self.rect.right - 95, self.rect.bottom - 36, 75, 28).collidepoint(ev.pos):
                self.page += 1
                return

            # Check Content Grid Cards
            grid_rect = pg.Rect(side_rect.right + 1, self.rect.y + 59, self.rect.w - side_rect.w - 1, self.rect.h - 104)
            start_idx = self.page * self.per_page
            end_idx = min(start_idx + self.per_page, len(self.entries))
            page_entries = self.entries[start_idx:end_idx]

            cols = 3
            for idx, entry in enumerate(page_entries):
                r = idx // cols
                c = idx % cols
                bx = grid_rect.x + 16 + c * 225
                by = grid_rect.y + 12 + r * 142
                card_rect = pg.Rect(bx, by, 215, 130)
                if card_rect.collidepoint(ev.pos):
                    if entry["type"] == "folder":
                        self._navigate_to(entry["path"])
                    else:
                        self.select_cb(entry["path"], self.current_dir)
                    return

        elif ev.type == pg.MOUSEWHEEL:
            max_pages = max(1, (len(self.entries) + self.per_page - 1) // self.per_page)
            if ev.y < 0 and self.page < max_pages - 1:
                self.page += 1
            elif ev.y > 0 and self.page > 0:
                self.page -= 1


BackgroundPickerModal = LinuxAssetExplorerModal


class SpritesheetSlicerModal:
    """Visual modal for loading tilesets/spritesheets, searching asset sheets, slicing via Auto-Contour or Grid, and selecting slice frames."""

    def __init__(self, select_cb, cancel_cb, active_folder: Optional[str] = None):
        self.select_cb = select_cb
        self.cancel_cb = cancel_cb
        self.active_folder = active_folder or "assets/graphics/background images/new_bg_images"
        self.rect = pg.Rect(W // 2 - 470, H // 2 - 285, 940, 570)

        self.search_input = TextInput("Search Sheets", self.rect.x + 20, self.rect.y + 52, 240, 34, initial="", placeholder="Search sheets e.g. ground, props, tiles...")
        self.selected_category = "Active Theme" if active_folder else "All"
        self.categories = ["Active Theme", "Props", "Tilesets", "Nature", "All"]

        self.showing_gallery = False
        self.file_explorer_modal: Optional[LinuxAssetExplorerModal] = None
        self.all_sheets = self._discover_sheets()
        self.sheet_idx = 0
        self.slice_mode = "Auto"  # "Auto", "32x32", "64x64", "128x128"
        self.slices: list[list[int]] = []
        self.selected_slice_idx = -1
        self.current_surface: Optional[pg.Surface] = None
        self.current_sheet_path: str = ""
        self.slice_page = 0
        self.slice_per_page = 12
        self.gallery_page = 0
        self.gallery_per_page = 6
        self._thumb_cache: dict[str, Optional[pg.Surface]] = {}

        filtered = self.get_filtered_sheets()
        if filtered:
            self._load_sheet(filtered[0])
        elif self.all_sheets:
            self._load_sheet(self.all_sheets[0])

    def _discover_sheets(self) -> list[str]:
        results = []
        exclude_keywords = [
            "Clouds", "intro_bg", "KEYS", "UI", "ui", "font", "PS4", "PC", "Analogue", "button", "KEYS_",
            "250 WARRIOR ICONS", "MAGE ICONS", "free-undead-loot", "icon", "ICONS", "Player", "player",
            "skeleton", "Goblin", "Wizard_NPC", "Necromancer", "DarkFantasyEnemies", "Monsters", "audio",
            "Sound", "VFX", "PIPOYA", "Explosion", "MiniBlood", "blood", "shadow_warrior", "Moon_knight"
        ]
        if os.path.exists("assets"):
            for root, _, files in os.walk("assets"):
                if any(ex.lower() in root.lower() for ex in exclude_keywords):
                    continue
                for f in files:
                    if f.lower().endswith((".png", ".jpg", ".jpeg")):
                        rel = os.path.relpath(os.path.join(root, f)).replace("\\", "/")
                        results.append(rel)
        return sorted(results)

    def get_filtered_sheets(self) -> list[str]:
        query = self.search_input.val.lower().strip()
        cat = self.selected_category
        filtered = []
        for s in self.all_sheets:
            s_lower = s.lower()

            if cat == "Active Theme" and self.active_folder:
                if self.active_folder.lower() not in s_lower and os.path.basename(self.active_folder).lower() not in s_lower:
                    continue
            elif cat == "Props" and not any(k in s_lower for k in ["prop", "chest", "rock", "object", "item", "building", "house", "tower", "sign"]):
                continue
            elif cat == "Tilesets" and not any(k in s_lower for k in ["tile", "ground", "platform", "block", "floor", "sheet"]):
                continue
            elif cat == "Nature" and not any(k in s_lower for k in ["tree", "forest", "bush", "grass", "plant", "wood", "flower", "winter"]):
                continue

            if query and query not in s_lower:
                continue
            filtered.append(s)
        return filtered if filtered else (self.all_sheets if not query and cat == "Active Theme" else [])

    def _open_file_explorer(self):
        self.file_explorer_modal = LinuxAssetExplorerModal(
            select_cb=self._on_pick_sheet_from_explorer,
            cancel_cb=lambda: setattr(self, "file_explorer_modal", None),
            current_dir=self.active_folder
        )

    def _on_pick_sheet_from_explorer(self, file_path: str, folder_path: str):
        self.file_explorer_modal = None
        self.active_folder = folder_path
        if file_path not in self.all_sheets:
            self.all_sheets.append(file_path)
            self.all_sheets.sort()
        self._load_sheet(file_path)
        self.showing_gallery = False

    def _load_sheet(self, path: str):
        try:
            self.current_sheet_path = path
            self.current_surface = AssetManager.get_texture(path)
            self.recalculate_slices()
        except Exception:
            self.current_surface = None
            self.current_sheet_path = path
            self.slices = []

    def recalculate_slices(self):
        if not self.current_surface:
            self.slices = []
            return
        surf = self.current_surface
        w, h = surf.get_width(), surf.get_height()
        self.slices = []
        self.selected_slice_idx = 0 if surf else -1
        self.slice_page = 0

        if self.slice_mode in ("32x32", "64x64", "128x128"):
            gw = int(self.slice_mode.split("x")[0])
            gh = gw
            for y in range(0, h, gh):
                for x in range(0, w, gw):
                    box_w = min(gw, w - x)
                    box_h = min(gh, h - y)
                    sub = surf.subsurface(pg.Rect(x, y, box_w, box_h))
                    mask = pg.mask.from_surface(sub)
                    if mask.count() > 0:
                        self.slices.append([x, y, box_w, box_h])
        else:  # Auto Contour
            try:
                mask = pg.mask.from_surface(surf)
                rects = mask.get_bounding_rects()
                if rects:
                    for r in rects:
                        if isinstance(r, (list, tuple)) and len(r) >= 4:
                            rx, ry, rw, rh = int(r[0]), int(r[1]), int(r[2]), int(r[3])
                        else:
                            rx, ry, rw, rh = int(getattr(r, 'x', 0)), int(getattr(r, 'y', 0)), int(getattr(r, 'w', 0)), int(getattr(r, 'h', 0))
                        if rw >= 4 and rh >= 4:
                            self.slices.append([rx, ry, rw, rh])
                else:
                    self.slices.append([0, 0, w, h])
            except Exception:
                self.slices.append([0, 0, w, h])

    def draw(self, surf: pg.Surface, font: pg.font.Font, sfont: pg.font.Font):
        if self.file_explorer_modal:
            self.file_explorer_modal.draw(surf, font, sfont)
            return

        overlay = pg.Surface((W, H), pg.SRCALPHA)
        overlay.fill((0, 0, 0, 200))
        surf.blit(overlay, (0, 0))

        pg.draw.rect(surf, PANEL, self.rect, border_radius=12)
        pg.draw.rect(surf, ACCENT, self.rect, width=2, border_radius=12)

        title = font.render("✂️ Spritesheet Slicer & Ground Tile Chooser", True, TXT)
        surf.blit(title, (self.rect.x + 20, self.rect.y + 16))

        close_btn = Button("✕", self.rect.right - 44, self.rect.y + 12, 32, 32, self.cancel_cb, "danger")
        close_btn.draw(surf, sfont)

        # Linux File Explorer Launcher Button
        exp_btn = Button("📁 Browse Files (Linux Manager)", self.rect.x + 270, self.rect.y + 52, 185, 34, self.self_open_explorer, "primary")
        exp_btn.draw(surf, sfont)

        # Search Bar
        self.search_input.draw(surf, font, sfont)

        # Category Filter Tabs
        cat_x = self.rect.x + 465
        for cat in self.categories[:3]:
            is_cat_sel = (self.selected_category == cat)
            def _set_cat(c=cat):
                self.selected_category = c
                self.gallery_page = 0
            b = Button(cat, cat_x, self.rect.y + 52, 90, 34, _set_cat, "primary" if is_cat_sel else "ghost")
            b.draw(surf, sfont)
            cat_x += 95

        # Toggle Button: Gallery vs Viewport
        def _toggle_gal():
            self.showing_gallery = not self.showing_gallery
        gal_btn = Button("📁 Gallery" if not self.showing_gallery else "✂️ Slicer", self.rect.right - 105, self.rect.y + 52, 90, 34, _toggle_gal, "warn" if self.showing_gallery else "ghost")
        gal_btn.draw(surf, sfont)

        if self.showing_gallery:
            # ── GALLERY VIEW: 3x2 Thumbnail Grid of Image Files ──────────────────
            filtered_sheets = self.get_filtered_sheets()
            surf.blit(sfont.render(f"Found {len(filtered_sheets)} image sheets matching filters:", True, TXT2), (self.rect.x + 20, self.rect.y + 100))

            start_idx = self.gallery_page * self.gallery_per_page
            end_idx = min(start_idx + self.gallery_per_page, len(filtered_sheets))
            page_sheets = filtered_sheets[start_idx:end_idx]

            cols = 3
            m_pos = pg.mouse.get_pos()
            for idx, path in enumerate(page_sheets):
                r = idx // cols
                c = idx % cols
                bx = self.rect.x + 20 + c * 300
                by = self.rect.y + 130 + r * 185
                card_rect = pg.Rect(bx, by, 285, 175)

                is_h = card_rect.collidepoint(m_pos)
                pg.draw.rect(surf, PANEL2 if is_h else (28, 28, 40), card_rect, border_radius=8)
                pg.draw.rect(surf, ACCENT if is_h else BORDER, card_rect, width=2 if is_h else 1, border_radius=8)

                if path not in self._thumb_cache:
                    try:
                        raw = AssetManager.get_texture(path)
                        sc = pg.transform.smoothscale(raw, (265, 115))
                        self._thumb_cache[path] = sc
                    except Exception:
                        self._thumb_cache[path] = None

                thumb = self._thumb_cache.get(path)
                if thumb:
                    surf.blit(thumb, (bx + 10, by + 10))

                fname = os.path.basename(path)
                surf.blit(font.render(fname[:26], True, WARN if is_h else TXT), (bx + 10, by + 132))
                surf.blit(sfont.render(path[-42:], True, TXT2), (bx + 10, by + 154))

            # Gallery Pagination
            max_g = max(1, (len(filtered_sheets) + self.gallery_per_page - 1) // self.gallery_per_page)
            surf.blit(sfont.render(f"Page {self.gallery_page + 1} of {max_g}", True, TXT2), (self.rect.x + 20, self.rect.bottom - 38))

            if self.gallery_page > 0:
                def _gp_prev(): self.gallery_page -= 1
                Button("< Prev Page", self.rect.x + 130, self.rect.bottom - 45, 95, 34, _gp_prev, "ghost").draw(surf, sfont)
            if self.gallery_page < max_g - 1:
                def _gp_next(): self.gallery_page += 1
                Button("Next Page >", self.rect.x + 235, self.rect.bottom - 45, 95, 34, _gp_next, "ghost").draw(surf, sfont)

        else:
            # ── SLICER VIEW: Spritesheet Viewport & Detected Slices ────────────────
            filtered_sheets = self.get_filtered_sheets()
            if filtered_sheets:
                cur_path = filtered_sheets[self.sheet_idx % len(filtered_sheets)]
                file_name = os.path.basename(cur_path)
                surf.blit(font.render(f"Sheet: {file_name[:26]}", True, WARN), (self.rect.x + 20, self.rect.y + 95))
                surf.blit(sfont.render(f"({(self.sheet_idx % len(filtered_sheets)) + 1}/{len(filtered_sheets)}) {cur_path[-55:]}", True, TXT2), (self.rect.x + 20, self.rect.y + 118))

                def _prev_file():
                    self.sheet_idx = (self.sheet_idx - 1) % len(filtered_sheets)
                    self._load_sheet(filtered_sheets[self.sheet_idx])

                def _next_file():
                    self.sheet_idx = (self.sheet_idx + 1) % len(filtered_sheets)
                    self._load_sheet(filtered_sheets[self.sheet_idx])

                Button("◀ Prev", self.rect.x + 360, self.rect.y + 95, 65, 32, _prev_file, "ghost").draw(surf, sfont)
                Button("Next ▶", self.rect.x + 430, self.rect.y + 95, 65, 32, _next_file, "ghost").draw(surf, sfont)

            surf.blit(sfont.render("Slice Mode:", True, TXT2), (self.rect.x + 515, self.rect.y + 100))
            modes = ["Auto", "32x32", "64x64", "128x128"]
            mx_pos = self.rect.x + 595
            for m in modes:
                is_m_active = (self.slice_mode == m)
                def _set_m(mode=m):
                    self.slice_mode = mode
                    self.recalculate_slices()
                btn = Button(m, mx_pos, self.rect.y + 95, 68, 32, _set_m, "primary" if is_m_active else "ghost")
                btn.draw(surf, sfont)
                mx_pos += 74

            # Spritesheet Viewport (Left Area)
            sheet_box = pg.Rect(self.rect.x + 20, self.rect.y + 145, 560, 360)
            pg.draw.rect(surf, PANEL2, sheet_box, border_radius=8)
            pg.draw.rect(surf, BORDER, sheet_box, width=1, border_radius=8)

            if self.current_surface:
                raw_w, raw_h = self.current_surface.get_size()
                scale_factor = min(sheet_box.w / float(raw_w), sheet_box.h / float(raw_h))
                disp_w = int(raw_w * scale_factor)
                disp_h = int(raw_h * scale_factor)

                disp_surf = pg.transform.smoothscale(self.current_surface, (disp_w, disp_h))
                off_x = sheet_box.x + (sheet_box.w - disp_w) // 2
                off_y = sheet_box.y + (sheet_box.h - disp_h) // 2
                surf.blit(disp_surf, (off_x, off_y))

                for s_idx, s_rect in enumerate(self.slices):
                    rx, ry, rw, rh = s_rect
                    sx = off_x + int(rx * scale_factor)
                    sy = off_y + int(ry * scale_factor)
                    sw = max(2, int(rw * scale_factor))
                    sh = max(2, int(rh * scale_factor))
                    is_sel = (s_idx == self.selected_slice_idx)
                    col = (241, 196, 15) if is_sel else (52, 152, 219)
                    pg.draw.rect(surf, col, pg.Rect(sx, sy, sw, sh), width=2 if is_sel else 1)

            # Slices Grid (Right Area)
            list_box = pg.Rect(self.rect.x + 595, self.rect.y + 145, 325, 360)
            pg.draw.rect(surf, PANEL2, list_box, border_radius=8)
            pg.draw.rect(surf, BORDER, list_box, width=1, border_radius=8)

            surf.blit(font.render(f"Detected Slices ({len(self.slices)})", True, TXT), (list_box.x + 12, list_box.y + 10))

            start_i = self.slice_page * self.slice_per_page
            page_slices = self.slices[start_i:start_i + self.slice_per_page]

            cols = 3
            m_pos = pg.mouse.get_pos()
            for idx, s_rect in enumerate(page_slices):
                global_idx = start_i + idx
                r = idx // cols
                c = idx % cols
                bx = list_box.x + 12 + c * 100
                by = list_box.y + 40 + r * 95
                c_rect = pg.Rect(bx, by, 92, 88)

                is_sel = (global_idx == self.selected_slice_idx)
                is_h = c_rect.collidepoint(m_pos)

                bg_c = (45, 45, 65) if (is_sel or is_h) else PANEL
                b_c = (241, 196, 15) if is_sel else (ACCENT if is_h else BORDER)

                pg.draw.rect(surf, bg_c, c_rect, border_radius=6)
                pg.draw.rect(surf, b_c, c_rect, width=2 if is_sel else 1, border_radius=6)

                if self.current_surface:
                    rx, ry, rw, rh = s_rect
                    sub = self.current_surface.subsurface(pg.Rect(rx, ry, rw, rh))
                    sc_sub = pg.transform.smoothscale(sub, (60, 55))
                    surf.blit(sc_sub, (bx + 16, by + 8))

                surf.blit(sfont.render(f"{s_rect[2]}x{s_rect[3]}", True, TXT2), (bx + 14, by + 66))

            b_str = f"Slice {self.selected_slice_idx + 1} of {len(self.slices)}" if self.selected_slice_idx >= 0 else "No slice selected"
            surf.blit(sfont.render(b_str, True, TXT2), (self.rect.x + 20, self.rect.bottom - 40))

            max_p = max(1, (len(self.slices) + self.slice_per_page - 1) // self.slice_per_page)
            if self.slice_page > 0:
                def _p_prev(): self.slice_page -= 1
                Button("< Prev", self.rect.x + 600, self.rect.bottom - 45, 75, 34, _p_prev, "ghost").draw(surf, sfont)
            if self.slice_page < max_p - 1:
                def _p_next(): self.slice_page += 1
                Button("Next >", self.rect.x + 680, self.rect.bottom - 45, 75, 34, _p_next, "ghost").draw(surf, sfont)

            def _do_place():
                if 0 <= self.selected_slice_idx < len(self.slices) and self.current_sheet_path:
                    self.select_cb(self.current_sheet_path, self.slices[self.selected_slice_idx])

            pl_btn = Button("＋ Place into Canvas", self.rect.right - 165, self.rect.bottom - 45, 150, 36, _do_place, "success" if self.selected_slice_idx >= 0 else "ghost")
            pl_btn.enabled = (self.selected_slice_idx >= 0)
            pl_btn.draw(surf, sfont)

    def self_open_explorer(self):
        self.file_explorer_modal = LinuxAssetExplorerModal(
            select_cb=self._on_pick_sheet_from_explorer,
            cancel_cb=lambda: setattr(self, "file_explorer_modal", None),
            current_dir=self.active_folder
        )

    def on(self, ev: pg.event.Event):
        if self.file_explorer_modal:
            self.file_explorer_modal.on(ev)
            return

        self.search_input.on(ev)

        if ev.type == pg.MOUSEBUTTONDOWN and ev.button == 1:
            close_btn_rect = pg.Rect(self.rect.right - 44, self.rect.y + 12, 32, 32)
            if close_btn_rect.collidepoint(ev.pos):
                self.cancel_cb()
                return

            exp_btn_rect = pg.Rect(self.rect.x + 270, self.rect.y + 52, 185, 34)
            if exp_btn_rect.collidepoint(ev.pos):
                self.self_open_explorer()
                return

            cat_x = self.rect.x + 465
            for cat in self.categories[:3]:
                if pg.Rect(cat_x, self.rect.y + 52, 90, 34).collidepoint(ev.pos):
                    self.selected_category = cat
                    self.gallery_page = 0
                    return
                cat_x += 95

            gal_btn_rect = pg.Rect(self.rect.right - 105, self.rect.y + 52, 90, 34)
            if gal_btn_rect.collidepoint(ev.pos):
                self.showing_gallery = not self.showing_gallery
                return

            if self.showing_gallery:
                filtered_sheets = self.get_filtered_sheets()
                start_idx = self.gallery_page * self.gallery_per_page
                end_idx = min(start_idx + self.gallery_per_page, len(filtered_sheets))
                page_sheets = filtered_sheets[start_idx:end_idx]

                cols = 3
                for idx, path in enumerate(page_sheets):
                    r = idx // cols
                    c = idx % cols
                    bx = self.rect.x + 20 + c * 300
                    by = self.rect.y + 130 + r * 185
                    card_rect = pg.Rect(bx, by, 285, 175)
                    if card_rect.collidepoint(ev.pos):
                        self.sheet_idx = filtered_sheets.index(path)
                        self._load_sheet(path)
                        self.showing_gallery = False
                        return
            else:
                filtered_sheets = self.get_filtered_sheets()
                if filtered_sheets:
                    if pg.Rect(self.rect.x + 360, self.rect.y + 95, 65, 32).collidepoint(ev.pos):
                        self.sheet_idx = (self.sheet_idx - 1) % len(filtered_sheets)
                        self._load_sheet(filtered_sheets[self.sheet_idx])
                        return
                    if pg.Rect(self.rect.x + 430, self.rect.y + 95, 65, 32).collidepoint(ev.pos):
                        self.sheet_idx = (self.sheet_idx + 1) % len(filtered_sheets)
                        self._load_sheet(filtered_sheets[self.sheet_idx])
                        return

                modes = ["Auto", "32x32", "64x64", "128x128"]
                mx_pos = self.rect.x + 595
                for m in modes:
                    if pg.Rect(mx_pos, self.rect.y + 95, 68, 32).collidepoint(ev.pos):
                        self.slice_mode = m
                        self.recalculate_slices()
                        return
                    mx_pos += 74

                list_box = pg.Rect(self.rect.x + 595, self.rect.y + 145, 325, 360)
                start_i = self.slice_page * self.slice_per_page
                page_slices = self.slices[start_i:start_i + self.slice_per_page]
                cols = 3
                for idx, s_rect in enumerate(page_slices):
                    r = idx // cols
                    c = idx % cols
                    bx = list_box.x + 12 + c * 100
                    by = list_box.y + 40 + r * 95
                    c_rect = pg.Rect(bx, by, 92, 88)
                    if c_rect.collidepoint(ev.pos) and list_box.collidepoint(ev.pos):
                        self.selected_slice_idx = start_i + idx
                        return

                sheet_box = pg.Rect(self.rect.x + 20, self.rect.y + 145, 560, 360)
                if sheet_box.collidepoint(ev.pos) and self.current_surface:
                    raw_w, raw_h = self.current_surface.get_size()
                    scale_factor = min(sheet_box.w / float(raw_w), sheet_box.h / float(raw_h))
                    disp_w = int(raw_w * scale_factor)
                    disp_h = int(raw_h * scale_factor)
                    off_x = sheet_box.x + (sheet_box.w - disp_w) // 2
                    off_y = sheet_box.y + (sheet_box.h - disp_h) // 2

                    click_x = int((ev.pos[0] - off_x) / scale_factor)
                    click_y = int((ev.pos[1] - off_y) / scale_factor)

                    for s_idx, s_rect in enumerate(self.slices):
                        rx, ry, rw, rh = s_rect
                        if rx <= click_x <= rx + rw and ry <= click_y <= ry + rh:
                            self.selected_slice_idx = s_idx
                            return

                if self.selected_slice_idx >= 0 and self.current_sheet_path:
                    pl_rect = pg.Rect(self.rect.right - 165, self.rect.bottom - 45, 150, 36)
                    if pl_rect.collidepoint(ev.pos):
                        self.select_cb(self.current_sheet_path, self.slices[self.selected_slice_idx])
                        return

        elif ev.type == pg.MOUSEWHEEL:
            if self.showing_gallery:
                filtered_sheets = self.get_filtered_sheets()
                max_g = max(1, (len(filtered_sheets) + self.gallery_per_page - 1) // self.gallery_per_page)
                if ev.y < 0 and self.gallery_page < max_g - 1:
                    self.gallery_page += 1
                elif ev.y > 0 and self.gallery_page > 0:
                    self.gallery_page -= 1
            else:
                max_p = max(1, (len(self.slices) + self.slice_per_page - 1) // self.slice_per_page)
                if ev.y < 0 and self.slice_page < max_p - 1:
                    self.slice_page += 1
                elif ev.y > 0 and self.slice_page > 0:
                    self.slice_page -= 1


class LevelManagerModal:
    """Modal for browsing existing saved level JSON files in game_data/ and creating new level files."""

    def __init__(self, select_cb, create_cb, cancel_cb):
        self.select_cb = select_cb
        self.create_cb = create_cb
        self.cancel_cb = cancel_cb
        self.rect = pg.Rect(W // 2 - 400, H // 2 - 250, 800, 500)
        self.levels = self._discover_levels()

    def _discover_levels(self) -> list[dict]:
        levels = []
        folder = "game_data"
        if os.path.exists(folder):
            for f in sorted(os.listdir(folder)):
                if f.endswith(".json") and not f.startswith("."):
                    path = os.path.join(folder, f)
                    try:
                        with open(path, "r") as fh:
                            data = json.load(fh)
                        if isinstance(data, dict) and "level_name" in data:
                            levels.append({
                                "filename": f,
                                "path": path,
                                "name": data.get("level_name", f),
                                "props_count": len(data.get("environment", {}).get("props", [])),
                                "layers_count": len(data.get("environment", {}).get("layer_stacks", {}))
                            })
                    except Exception:
                        pass
        return levels

    def draw(self, surf: pg.Surface, font: pg.font.Font, sfont: pg.font.Font):
        overlay = pg.Surface((W, H), pg.SRCALPHA)
        overlay.fill((0, 0, 0, 200))
        surf.blit(overlay, (0, 0))

        pg.draw.rect(surf, PANEL, self.rect, border_radius=12)
        pg.draw.rect(surf, ACCENT, self.rect, width=2, border_radius=12)

        title = font.render("📂 Level Save Files & Manager", True, TXT)
        surf.blit(title, (self.rect.x + 20, self.rect.y + 18))

        close_btn = Button("✕", self.rect.right - 44, self.rect.y + 12, 32, 32, self.cancel_cb, "danger")
        close_btn.draw(surf, sfont)

        sub = sfont.render("Saved Level Files in 'game_data/' directory:", True, TXT2)
        surf.blit(sub, (self.rect.x + 20, self.rect.y + 55))

        create_btn = Button("➕ Create New Level File", self.rect.right - 210, self.rect.y + 50, 190, 32, self.create_cb, "success")
        create_btn.draw(surf, sfont)

        # List Level Cards
        card_y = self.rect.y + 92
        m_pos = pg.mouse.get_pos()
        for idx, lvl in enumerate(self.levels):
            card_rect = pg.Rect(self.rect.x + 20, card_y, 760, 60)
            is_h = card_rect.collidepoint(m_pos)
            pg.draw.rect(surf, PANEL2 if is_h else (28, 28, 40), card_rect, border_radius=8)
            pg.draw.rect(surf, ACCENT if is_h else BORDER, card_rect, width=2 if is_h else 1, border_radius=8)

            surf.blit(font.render(f"🎮 {lvl['name']} ({lvl['filename']})", True, WARN if is_h else TXT), (card_rect.x + 14, card_rect.y + 10))
            surf.blit(sfont.render(f"File: {lvl['path']}  |  Props: {lvl['props_count']} objects  |  Layers: {lvl['layers_count']}", True, TXT2), (card_rect.x + 14, card_rect.y + 34))

            def _load_this(p=lvl["path"]): self.select_cb(p)
            btn = Button("✏️ Edit Level", card_rect.right - 130, card_rect.y + 14, 115, 32, _load_this, "primary")
            btn.draw(surf, sfont)
            card_y += 68

    def on(self, ev: pg.event.Event):
        if ev.type == pg.MOUSEBUTTONDOWN and ev.button == 1:
            close_btn_rect = pg.Rect(self.rect.right - 44, self.rect.y + 12, 32, 32)
            if close_btn_rect.collidepoint(ev.pos):
                self.cancel_cb()
                return

            create_btn_rect = pg.Rect(self.rect.right - 210, self.rect.y + 50, 190, 32)
            if create_btn_rect.collidepoint(ev.pos):
                self.create_cb()
                return

            card_y = self.rect.y + 92
            for lvl in self.levels:
                btn_rect = pg.Rect(self.rect.x + 20 + 760 - 130, card_y + 14, 115, 32)
                if btn_rect.collidepoint(ev.pos):
                    self.select_cb(lvl["path"])
                    return
                card_y += 68


class AssetBrowserModal:
    """Visual asset browser and search modal for searching, previewing, and spawning entities onto the level canvas."""

    def __init__(self, spawn_cb, cancel_cb):
        self.spawn_cb = spawn_cb
        self.cancel_cb = cancel_cb
        self.rect = pg.Rect(W // 2 - 410, H // 2 - 270, 820, 540)
        self.search_input = TextInput("Search Assets", self.rect.x + 20, self.rect.y + 55, 480, 36, placeholder="Type name, e.g. necro, wizard, skeleton, goblin...")
        self.selected_category = "All"
        self.categories = ["All", "NPCs", "Enemies", "Bosses", "Props"]
        self.page = 0
        self.per_page = 6
        self.all_items = self._discover_catalog()
        self._thumb_cache = {}

    def _discover_catalog(self):
        catalog = [
            {"title": "Necromancer", "path": "assets/graphics/Necromancer/Idle", "type": "npc", "category": "NPCs", "scale": 3.38},
            {"title": "Dying Villager / Fairy", "path": "assets/graphics/Fairy", "type": "npc", "category": "NPCs", "scale": 2.0},
            {"title": "Goblin Merchant", "path": "assets/graphics/Goblin/Idle", "type": "npc", "category": "NPCs", "scale": 2.0},
            {"title": "Masked Stranger", "path": "assets/graphics/masked_man", "type": "npc", "category": "NPCs", "scale": 4.5},
            {"title": "Red Moon Tower", "path": "assets/graphics/RedMoonTower", "type": "interaction", "category": "Props", "scale": 2.0},
            {"title": "White Skeleton", "path": "assets/skeleton", "type": "minion_zone", "category": "Enemies", "scale": 2.0},
            {"title": "Fire Wizard Boss", "path": "assets/wizard", "type": "boss", "category": "Bosses", "scale": 4.11},
            {"title": "Elise the Apostate", "path": "assets/graphics/bloodZombie", "type": "boss", "category": "Bosses", "scale": 2.0},
            {"title": "Green Monster", "path": "assets/graphics/green_monster", "type": "boss", "category": "Bosses", "scale": 2.5},
            {"title": "Evil Jack", "path": "assets/graphics/Evil_jack", "type": "boss", "category": "Bosses", "scale": 2.2},
            {"title": "Ronin Warrior", "path": "assets/graphics/Ronin", "type": "npc", "category": "NPCs", "scale": 2.0},
            {"title": "Kobold Warrior", "path": "assets/graphics/Kobold_Warrior", "type": "minion_zone", "category": "Enemies", "scale": 2.0},
        ]
        if os.path.exists("assets/graphics"):
            for root, dirs, files in os.walk("assets/graphics"):
                pngs = [f for f in files if f.lower().endswith(".png")]
                if pngs and not any(d in root for d in ["Clouds", "background images", "UI", "KEYS", "pigeon", "snail"]):
                    rel = os.path.relpath(root).replace("\\", "/")
                    if not any(item["path"] == rel for item in catalog):
                        basename = os.path.basename(rel)
                        cat = "Props" if any(k in rel.lower() for k in ["prop", "tower", "book", "icon", "totem"]) else "NPCs"
                        catalog.append({
                            "title": basename.replace("_", " ").title(),
                            "path": rel,
                            "type": "npc",
                            "category": cat,
                            "scale": 2.0
                        })
        return catalog

    def _get_thumbnail(self, path: str) -> Optional[pg.Surface]:
        if path in self._thumb_cache:
            return self._thumb_cache[path]
        try:
            frames = AssetManager.get_animation_frames(path)
            if frames:
                orig = frames[0]
                scaled = pg.transform.smoothscale(orig, (55, 55))
                self._thumb_cache[path] = scaled
                return scaled
        except Exception:
            pass
        self._thumb_cache[path] = None
        return None

    def get_filtered_items(self):
        query = self.search_input.val.strip().lower()
        res = []
        for item in self.all_items:
            title_str = str(item.get("title", ""))
            path_str = str(item.get("path", ""))
            type_str = str(item.get("type", ""))
            cat_str = str(item.get("category", ""))
            match_cat = (self.selected_category == "All" or cat_str == self.selected_category)
            match_q = (not query or query in title_str.lower() or query in path_str.lower() or query in type_str.lower())
            if match_cat and match_q:
                res.append(item)
        return res

    def draw(self, surf: pg.Surface, font: pg.font.Font, sfont: pg.font.Font):
        overlay = pg.Surface((W, H), pg.SRCALPHA)
        overlay.fill((0, 0, 0, 195))
        surf.blit(overlay, (0, 0))

        pg.draw.rect(surf, PANEL, self.rect, border_radius=12)
        pg.draw.rect(surf, ACCENT, self.rect, width=2, border_radius=12)

        title = font.render("🔍 Asset Library & Custom Entity Browser", True, TXT)
        surf.blit(title, (self.rect.x + 20, self.rect.y + 16))

        close_btn = Button("✕", self.rect.right - 44, self.rect.y + 12, 32, 32, self.cancel_cb, "danger")
        close_btn.draw(surf, sfont)

        self.search_input.draw(surf, font, sfont)

        px = self.rect.x + 515
        for cat in self.categories:
            is_active = (self.selected_category == cat)
            def _set_cat(c=cat):
                self.selected_category = c
                self.page = 0
            btn = Button(cat, px, self.rect.y + 55, 52, 36, _set_cat, "primary" if is_active else "ghost")
            btn.draw(surf, sfont)
            px += 56

        filtered = self.get_filtered_items()
        start_idx = self.page * self.per_page
        page_items = filtered[start_idx:start_idx + self.per_page]

        cols = 3
        m_pos = pg.mouse.get_pos()

        for idx, item in enumerate(page_items):
            r = idx // cols
            c = idx % cols
            bx = self.rect.x + 20 + c * 260
            by = self.rect.y + 110 + r * 170
            card_rect = pg.Rect(bx, by, 248, 155)

            is_hover = card_rect.collidepoint(m_pos)
            bg_col = (45, 45, 65) if is_hover else PANEL2
            border_col = ACCH if is_hover else BORDER

            pg.draw.rect(surf, bg_col, card_rect, border_radius=8)
            pg.draw.rect(surf, border_col, card_rect, width=2 if is_hover else 1, border_radius=8)

            item_path = str(item.get("path", ""))
            item_title = str(item.get("title", ""))
            item_type = str(item.get("type", ""))
            item_cat = str(item.get("category", ""))

            thumb = self._get_thumbnail(item_path)
            if thumb:
                surf.blit(thumb, (bx + 12, by + 12))
            else:
                pg.draw.circle(surf, ACCENT, (bx + 40, by + 40), 20)

            tl = font.render(item_title[:16], True, TXT)
            surf.blit(tl, (bx + 78, by + 10))

            t_badge = sfont.render(f"Type: {item_type} ({item_cat})", True, WARN if item_type=='boss' else ACCENT)
            surf.blit(t_badge, (bx + 78, by + 34))

            path_lbl = sfont.render(item_path[-26:], True, TXT3)
            surf.blit(path_lbl, (bx + 12, by + 76))

            def _do_spawn(itm=item):
                self.spawn_cb(itm)

            spw_btn = Button("＋ Spawn to Canvas", bx + 12, by + 105, 224, 36, _do_spawn, "primary")
            spw_btn.draw(surf, sfont)

        max_pages = max(1, (len(filtered) + self.per_page - 1) // self.per_page)
        p_str = f"Showing {len(filtered)} assets  ·  Page {self.page + 1} of {max_pages}"
        surf.blit(sfont.render(p_str, True, TXT2), (self.rect.x + 20, self.rect.bottom - 38))

        if self.page > 0:
            def _prev(): self.page -= 1
            Button("< Prev", self.rect.right - 180, self.rect.bottom - 45, 75, 34, _prev, "ghost").draw(surf, sfont)
        if self.page < max_pages - 1:
            def _next(): self.page += 1
            Button("Next >", self.rect.right - 95, self.rect.bottom - 45, 75, 34, _next, "ghost").draw(surf, sfont)

    def on(self, ev: pg.event.Event):
        self.search_input.on(ev)
        if ev.type == pg.MOUSEBUTTONDOWN and ev.button == 1:
            close_btn_rect = pg.Rect(self.rect.right - 44, self.rect.y + 12, 32, 32)
            if close_btn_rect.collidepoint(ev.pos):
                self.cancel_cb()
                return

            px = self.rect.x + 515
            for cat in self.categories:
                c_rect = pg.Rect(px, self.rect.y + 55, 52, 36)
                if c_rect.collidepoint(ev.pos):
                    self.selected_category = cat
                    self.page = 0
                    return
                px += 56

            filtered = self.get_filtered_items()
            max_pages = max(1, (len(filtered) + self.per_page - 1) // self.per_page)

            if self.page > 0:
                prev_rect = pg.Rect(self.rect.right - 180, self.rect.bottom - 45, 75, 34)
                if prev_rect.collidepoint(ev.pos):
                    self.page -= 1
                    return
            if self.page < max_pages - 1:
                next_rect = pg.Rect(self.rect.right - 95, self.rect.bottom - 45, 75, 34)
                if next_rect.collidepoint(ev.pos):
                    self.page += 1
                    return

            start_idx = self.page * self.per_page
            page_items = filtered[start_idx:start_idx + self.per_page]
            cols = 3
            for idx, item in enumerate(page_items):
                r = idx // cols
                c = idx % cols
                bx = self.rect.x + 20 + c * 260
                by = self.rect.y + 110 + r * 170
                spw_rect = pg.Rect(bx + 12, by + 105, 224, 36)
                if spw_rect.collidepoint(ev.pos):
                    self.spawn_cb(item)
                    return

        elif ev.type == pg.MOUSEWHEEL:
            filtered = self.get_filtered_items()
            max_pages = max(1, (len(filtered) + self.per_page - 1) // self.per_page)
            if ev.y < 0 and self.page < max_pages - 1:
                self.page += 1
            elif ev.y > 0 and self.page > 0:
                self.page -= 1


class App:
    def __init__(self):
        pg.init()
        pg.display.set_caption("Level Spawner Editor  v2")
        self.surf  = pg.display.set_mode((W, H), pg.RESIZABLE)
        self.native_surf = pg.Surface((1280, 720))
        self.clock = pg.time.Clock()
        self.running = True
        self.panels_collapsed = False
        self.fullscreen = False
        self.dragging_minimap = False
        self.tf = pg.font.SysFont("Arial", 22, bold=True)
        self.f  = pg.font.SysFont("Arial", 16)
        self.sf = pg.font.SysFont("Arial", 13)
        self.stage = 1
        self.level_files: list[str] = []
        self.active_idx = 0
        self.level_data: dict = {}
        self.level_backup: dict = {}
        self.pending: list[dict] = []
        self.reg_del: set[str] = set()
        self.modal: Optional[ModalDialog] = None
        self.s3_mode = "create"
        self.s3_type = "npc"
        self.s3_idx  = -1
        self.s3_ui: dict = {}
        self.prev_frames: list[pg.Surface] = []
        self.prev_timer = 0.0
        self.prev_idx   = 0
        self.prev_dir   = ""
        self.browser    = FolderBrowser("assets",
                                         pg.Rect(12, CONTENT_Y+52, 438, CONTENT_H-68), allow_parent=True)
        from wave_editor import BehaviourMapper
        self.bmap       = BehaviourMapper(pg.Rect(856, CONTENT_Y+48, 412, CONTENT_H-68))
        self._topback: Optional[Button] = None
        self._s1b: list[Button] = []
        self._s2b: list[Button] = []
        self._s3b: list[Button] = []
        self.new_level_mode = False
        self.new_level_title_input: Optional[TextInput] = None
        self.new_level_filename_input: Optional[TextInput] = None
        self.scan()

    def _update_minimap_scrub(self, mx: float):
        map_w = min(650, max(200, W - 500))
        map_x = max(10, (W - map_w) // 2)
        end_dist = float(self.level_data.get("level_end_distance", 36000))
        canvas_rect = self._get_s5_canvas_rect()
        
        # Calculate exact width of yellow viewport handle on track
        cam_view_w = max(16, int(((canvas_rect.w / self.cam_zoom) / end_dist) * map_w))

        # Clamp mouse X to the minimap track bounds
        clamped_mx = max(float(map_x), min(float(map_x + map_w), float(mx)))

        # Center the yellow handle precisely on clamped_mx
        target_start_x = clamped_mx - (cam_view_w / 2.0)
        r = (target_start_x - map_x) / float(map_w)

        # Max camera world X coordinate so view never exceeds level end
        max_cam_x = max(0.0, end_dist - 1280.0 / self.cam_zoom)
        self.cam_x = max(0.0, min(max_cam_x, r * end_dist))

    def _get_s5_avail_bounds(self) -> pg.Rect:
        if getattr(self, "panels_collapsed", False):
            return pg.Rect(10, 50, W - 20, max(200, H - 115))
        return pg.Rect(280, 50, max(200, W - 560), max(200, H - 115))

    def _get_s5_canvas_rect(self) -> pg.Rect:
        avail = self._get_s5_avail_bounds()
        avail_w = avail.w
        avail_h = avail.h
        target_ratio = 16.0 / 9.0

        if avail_w / float(avail_h) > target_ratio:
            fit_h = avail_h
            fit_w = int(fit_h * target_ratio)
        else:
            fit_w = avail_w
            fit_h = int(fit_w / target_ratio)

        vp_x = avail.x + (avail_w - fit_w) // 2
        vp_y = avail.y + (avail_h - fit_h) // 2
        return pg.Rect(vp_x, vp_y, fit_w, fit_h)

    def _toggle_panels(self):
        self.panels_collapsed = not getattr(self, "panels_collapsed", False)

    def _toggle_fullscreen(self):
        global W, H
        self.fullscreen = not getattr(self, "fullscreen", False)
        if self.fullscreen:
            self.surf = pg.display.set_mode((0, 0), pg.FULLSCREEN | pg.RESIZABLE)
        else:
            self.surf = pg.display.set_mode((W, H), pg.RESIZABLE)
        W, H = self.surf.get_width(), self.surf.get_height()



    def scan(self):
        files = []
        for folder in ["game_data", "storyline"]:
            if os.path.isdir(folder):
                for f in os.listdir(folder):
                    if (f.startswith("level_") or f.startswith("prologue_")) and f.endswith(".json"):
                        path = os.path.join(folder, f)
                        if self._is_valid_level(path):
                            files.append(path)
        self.level_files = sorted(files)

    @staticmethod
    def _is_valid_level(path: str) -> bool:
        try:
            with open(path, "r") as fh:
                data = json.load(fh)
            if not isinstance(data, dict):
                return False
            if "level_name" not in data or not isinstance(data["level_name"], str):
                return False
            if "level_end_distance" not in data or not isinstance(data["level_end_distance"], (int, float)):
                return False
            if "world_events" in data and not isinstance(data["world_events"], list):
                return False
            if "entities" in data and not isinstance(data["entities"], list):
                return False
            return True
        except Exception:
            return False

    def load(self, idx: int):
        self.active_idx = idx
        if not self._is_valid_level(self.level_files[idx]):
            self.modal = ModalDialog(
                "Invalid Level File",
                f"'{os.path.basename(self.level_files[idx])}' is not a valid level JSON.",
                lambda: setattr(self, "modal", None),
            )
            return
        with open(self.level_files[idx], "r") as fh:
            fcntl.flock(fh, fcntl.LOCK_EX)
            self.level_data = json.load(fh)
        HitboxRegistry.sync_with_level_config(self.level_data)
        self.level_data.setdefault("world_events", [])
        self.level_backup = copy.deepcopy(self.level_data)
        self.pending = copy.deepcopy(self.level_data["world_events"])
        self.pending.sort(key=lambda e: e["distance"])
        self.reg_del = set()
        HitboxRegistry.begin_transaction()

        # Persist the selected level as the default for the game
        try:
            with open(os.path.join("game_data", ".level_default.json"), "w") as df:
                json.dump({"last_level": self.level_files[self.active_idx]}, df)
        except Exception:
            pass

    def commit(self):
        for k in self.reg_del:
            is_used = False
            for ev in self.pending:
                if ev.get("type") in ("npc", "boss"):
                    p = ev.get("params", {})
                    nt = p.get("npc_type", "generic")
                    sprite_dir = p.get("sprite_dir") or ""
                    if _registry_key(ev["type"], nt, sprite_dir) == k:
                        is_used = True
                        break
            if not is_used:
                HitboxRegistry._cached_config.pop(k, None)
        self.pending.sort(key=lambda e: e["distance"])
        self.level_data["world_events"] = copy.deepcopy(self.pending)
        with open(self.level_files[self.active_idx], "w") as fh:
            fcntl.flock(fh, fcntl.LOCK_EX)
            json.dump(self.level_data, fh, indent=4)
        HitboxRegistry.commit_transaction()
        self.level_backup = copy.deepcopy(self.level_data)
        self.reg_del = set()
        self.modal = None

    def rollback(self):
        self.level_data = copy.deepcopy(self.level_backup)
        self.pending = copy.deepcopy(self.level_data["world_events"])
        self.pending.sort(key=lambda e: e["distance"])
        self.reg_del = set()
        HitboxRegistry.rollback_transaction()
        self.modal = None

    def go1(self): self.stage = 1; self.scan()
    def go2(self): self.stage = 2; self.ev_scroll = 0; self.modal = None

    def go3(self, mode: str, etype: str, idx: int = -1):
        self.stage, self.s3_mode, self.s3_type, self.s3_idx = 3, mode, etype, idx
        self._init_s3(etype, idx)

    def go5(self):
        self.stage = 5
        self.modal = None
        self.bg_picker_modal = None
        self.slicer_modal = None
        self.cam_x = 0.0
        self.cam_y = 0.0
        self.cam_zoom = 1.0
        self.panning_canvas = False
        self.pan_start_pos = (0, 0)
        self.pan_start_cam = (0.0, 0.0)
        self.selected_prop_idx = -1
        self.dragging_prop_idx = -1
        self.active_layer_filter = 3  # 1: Sky, 2: Mid-BG, 3: Ground & Terrain, 4: Props, 5: Foreground
        self.active_asset_folder = "assets/graphics/background images/new_bg_images"
        self.grid_snap = 32
        self.simulating = False
        self.sim_speed = 350.0
        self._s5b = []

        env_cfg = self.level_data.get("environment", {})
        self.env_mgr = EnvironmentManager(W, H, env_config=env_cfg)
        self._init_s5_widgets()

    def _recenter_cam(self):
        self.cam_x = 0.0
        self.cam_y = 0.0
        self.cam_zoom = 1.0

    def _init_s5_widgets(self):
        gy = self.env_mgr.ground_y
        self.s5_ground_slider = Slider("Ground Y (px)", W - 266, 450, 252, 450, 720, gy, is_float=False)
        self.s5_ratio_slider = None

    def _on_select_prop_from_slicer(self, texture_path: str, slice_rect: list[int]):
        self.slicer_modal = None
        cam_center = self.cam_x + 500.0
        gy = float(self.env_mgr.ground_y)
        init_scale = 1.0
        slice_h = slice_rect[3] if slice_rect and len(slice_rect) >= 4 else 64
        target_layer = self.active_layer_filter
        target_ratio = 1.0 if target_layer in (3, 4) else self.env_mgr.layer_stacks.get(target_layer, {}).get("scroll_ratio", 1.0)
        new_prop = EnvironmentProp(
            texture_path=texture_path,
            slice_rect=slice_rect,
            pos_x=cam_center,
            pos_y=max(0.0, gy - float(slice_h * init_scale)),
            scale=init_scale,
            layer_index=target_layer,
            parallax_ratio=target_ratio,
            flip_x=False,
            flip_y=False,
            is_ground=True,
            collision_type="solid",
        )
        self.env_mgr.props.append(new_prop)
        self.selected_prop_idx = len(self.env_mgr.props) - 1
        self.level_data["environment"] = self.env_mgr.to_config_dict()

    def duplicate_selected_prop(self):
        if 0 <= self.selected_prop_idx < len(self.env_mgr.props):
            p = self.env_mgr.props[self.selected_prop_idx]
            cloned = EnvironmentProp(
                texture_path=p.texture_path,
                slice_rect=copy.deepcopy(p.slice_rect),
                pos_x=p.pos_x + 32.0,
                pos_y=p.pos_y,
                scale=p.scale,
                layer_index=p.layer_index,
                parallax_ratio=p.parallax_ratio,
                flip_x=p.flip_x,
                flip_y=p.flip_y,
                is_ground=getattr(p, "is_ground", True),
                collision_type=getattr(p, "collision_type", "solid"),
                collision_offset_y=getattr(p, "collision_offset_y", 0.0),
            )
            self.env_mgr.props.append(cloned)
            self.selected_prop_idx = len(self.env_mgr.props) - 1
            self.level_data["environment"] = self.env_mgr.to_config_dict()

    def delete_selected_prop(self):
        if 0 <= self.selected_prop_idx < len(self.env_mgr.props):
            self.env_mgr.props.pop(self.selected_prop_idx)
            self.selected_prop_idx = -1
            self.level_data["environment"] = self.env_mgr.to_config_dict()

    def reset_active_layer(self):
        """Clears background texture and wipes all placed objects on active layer."""
        self.env_mgr.clear_layer_texture(self.active_layer_filter)
        if self.active_layer_filter == 1:
            self.env_mgr.sky = None
        self.env_mgr.props = [p for p in self.env_mgr.props if p.layer_index != self.active_layer_filter]
        self.selected_prop_idx = -1
        self.level_data["environment"] = self.env_mgr.to_config_dict()

    def reset_entire_environment(self):
        """Resets all 5 environment layers, sky overlay, parallax layers, and wipes all placed objects to clean slate."""
        for l_idx in range(1, 6):
            self.env_mgr.clear_layer_texture(l_idx)
        self.env_mgr.sky = None
        self.env_mgr.parallax_layers.clear()
        self.env_mgr.props.clear()
        self.selected_prop_idx = -1
        self.level_data["environment"] = self.env_mgr.to_config_dict()

    def _h5(self, ev: pg.event.Event):
        if self.bg_picker_modal:
            self.bg_picker_modal.on(ev)
            return

        if self.slicer_modal:
            self.slicer_modal.on(ev)
            return

        for b in self._s5b:
            b.on(ev)

        if self.s5_ground_slider: self.s5_ground_slider.on(ev)
        if self.s5_ratio_slider: self.s5_ratio_slider.on(ev)

        canvas_rect = self._get_s5_canvas_rect()

        if ev.type == pg.MOUSEBUTTONDOWN:
            mx, my = ev.pos
            mods = pg.key.get_mods()
            is_alt = bool(mods & pg.KMOD_ALT)

            # Canvas Panning start (Middle click, Right click, or Shift+Left click)
            if canvas_rect.collidepoint(mx, my) and (ev.button in (2, 3) or (ev.button == 1 and bool(mods & pg.KMOD_SHIFT))):
                self.panning_canvas = True
                self.pan_start_pos = (mx, my)
                self.pan_start_cam = (self.cam_x, self.cam_y)
                return

            if ev.button == 1:
                # Minimap scrubbing area (Y: H - 65 to H)
                if my >= H - 65:
                    map_w = min(650, max(200, W - 500))
                    map_x = max(10, (W - map_w) // 2)
                    if map_x <= mx <= map_x + map_w:
                        self.dragging_minimap = True
                        self._update_minimap_scrub(float(mx))
                        return

                # Canvas Viewport area (strictly 16:9 canvas_rect)
                if canvas_rect.collidepoint(mx, my):
                    nx = (mx - canvas_rect.x) * (1280.0 / float(canvas_rect.w))
                    ny = (my - canvas_rect.y) * (720.0 / float(canvas_rect.h))

                    clicked_idx = -1
                    # Priority 1: Check props on active layer first
                    for pidx in reversed(range(len(self.env_mgr.props))):
                        prop = self.env_mgr.props[pidx]
                        if prop.layer_index == self.active_layer_filter:
                            draw_x = int(prop.pos_x - self.cam_x * prop.parallax_ratio)
                            draw_y = int(prop.pos_y - self.cam_y)
                            prect = pg.Rect(draw_x, draw_y, prop.width, prop.height)
                            if prect.collidepoint(int(nx), int(ny)):
                                clicked_idx = pidx
                                break

                    # Priority 2: If no match on active layer, check across all visible layers
                    if clicked_idx < 0:
                        for pidx in reversed(range(len(self.env_mgr.props))):
                            prop = self.env_mgr.props[pidx]
                            draw_x = int(prop.pos_x - self.cam_x * prop.parallax_ratio)
                            draw_y = int(prop.pos_y - self.cam_y)
                            prect = pg.Rect(draw_x, draw_y, prop.width, prop.height)
                            if prect.collidepoint(int(nx), int(ny)):
                                clicked_idx = pidx
                                break

                    if clicked_idx >= 0:
                        self.selected_prop_idx = clicked_idx
                        self.active_layer_filter = self.env_mgr.props[clicked_idx].layer_index

                        # FL Studio Alt-Drag Duplication!
                        if is_alt:
                            self.duplicate_selected_prop()
                            self.dragging_prop_idx = self.selected_prop_idx
                        else:
                            self.dragging_prop_idx = clicked_idx
                    else:
                        self.selected_prop_idx = -1

        elif ev.type == pg.MOUSEBUTTONUP:
            if ev.button in (1, 2, 3):
                self.panning_canvas = False
            if ev.button == 1:
                self.dragging_prop_idx = -1
                self.dragging_minimap = False

        elif ev.type == pg.MOUSEMOTION:
            if getattr(self, "panning_canvas", False):
                mx, my = ev.pos
                scale_w = 1280.0 / float(canvas_rect.w)
                scale_h = 720.0 / float(canvas_rect.h)
                dx = (mx - self.pan_start_pos[0]) * scale_w
                dy = (my - self.pan_start_pos[1]) * scale_h
                self.cam_x = max(0.0, self.pan_start_cam[0] - dx)
                self.cam_y = self.pan_start_cam[1] - dy
            elif getattr(self, "dragging_minimap", False):
                self._update_minimap_scrub(float(ev.pos[0]))
            elif 0 <= self.dragging_prop_idx < len(self.env_mgr.props):
                mx, my = ev.pos
                if canvas_rect.collidepoint(mx, my):
                    prop = self.env_mgr.props[self.dragging_prop_idx]
                    nx = (mx - canvas_rect.x) * (1280.0 / float(canvas_rect.w))
                    ny = (my - canvas_rect.y) * (720.0 / float(canvas_rect.h))

                    # Target screen position for prop top-left corner
                    target_draw_x = nx - prop.width / 2.0
                    target_draw_y = ny - prop.height / 2.0

                    # Convert screen position back to world coordinates
                    raw_x = target_draw_x + self.cam_x * prop.parallax_ratio
                    raw_y = target_draw_y + self.cam_y

                    if self.grid_snap > 0:
                        prop.pos_x = float(round(raw_x / float(self.grid_snap)) * self.grid_snap)
                        prop.pos_y = float(round(raw_y / float(self.grid_snap)) * self.grid_snap)
                    else:
                        prop.pos_x = float(raw_x)
                        prop.pos_y = float(raw_y)
                    self.level_data["environment"] = self.env_mgr.to_config_dict()

        elif ev.type == pg.MOUSEWHEEL:
            mx, my = pg.mouse.get_pos()
            if canvas_rect.collidepoint(mx, my):
                mods = pg.key.get_mods()
                if mods & pg.KMOD_SHIFT:
                    self.cam_y -= ev.y * 40.0
                elif mods & pg.KMOD_CTRL:
                    self.cam_zoom = max(0.2, min(3.0, self.cam_zoom + ev.y * 0.1))
                else:
                    self.cam_x = max(0.0, self.cam_x - ev.y * (250.0 / self.cam_zoom))

        elif ev.type == pg.KEYDOWN:
            mods = pg.key.get_mods()
            if ev.key == pg.K_HOME:
                self._recenter_cam()
                return

            if mods & pg.KMOD_SHIFT:
                if ev.key == pg.K_UP:
                    self.cam_y -= 40.0
                    return
                elif ev.key == pg.K_DOWN:
                    self.cam_y += 40.0
                    return

            step = float(self.grid_snap) if self.grid_snap > 0 else 4.0

            # Arrow keys nudge selected prop
            if self.selected_prop_idx >= 0 and 0 <= self.selected_prop_idx < len(self.env_mgr.props):
                p = self.env_mgr.props[self.selected_prop_idx]
                if ev.key == pg.K_LEFT and not (mods & pg.KMOD_SHIFT):
                    p.pos_x = max(0.0, p.pos_x - step)
                    self.level_data["environment"] = self.env_mgr.to_config_dict()
                    return
                elif ev.key == pg.K_RIGHT and not (mods & pg.KMOD_SHIFT):
                    p.pos_x += step
                    self.level_data["environment"] = self.env_mgr.to_config_dict()
                    return
                elif ev.key == pg.K_UP and not (mods & pg.KMOD_SHIFT):
                    p.pos_y -= step
                    self.level_data["environment"] = self.env_mgr.to_config_dict()
                    return
                elif ev.key == pg.K_DOWN and not (mods & pg.KMOD_SHIFT):
                    p.pos_y += step
                    self.level_data["environment"] = self.env_mgr.to_config_dict()
                    return

            if ev.key == pg.K_d and (mods & pg.KMOD_CTRL):
                self.duplicate_selected_prop()
            elif ev.key == pg.K_SPACE:
                self.simulating = not self.simulating
            elif ev.key == pg.K_LEFT:
                self.cam_x = max(0.0, self.cam_x - 300.0)
            elif ev.key == pg.K_RIGHT:
                self.cam_x += 300.0
            elif ev.key in (pg.K_DELETE, pg.K_BACKSPACE):
                if self.selected_prop_idx >= 0:
                    self.delete_selected_prop()

    def _d5(self):
        self._s5b = []

        # Sync ground Y slider
        if self.s5_ground_slider:
            self.env_mgr.ground_y = int(self.s5_ground_slider.val)

        # Update simulation & parallax layer movement
        if self.simulating:
            dt = 0.016
            self.cam_x += self.sim_speed * dt
            self.env_mgr.update(dt, player_speed=15.0)
        else:
            self.env_mgr.update(0.016, player_speed=0.0)

        # ── 1. NATIVE CANVAS VIEWPORT & PARALLAX RENDER ─────────────────────────
        canvas_rect = self._get_s5_canvas_rect()
        native_surf = getattr(self, "native_surf", None)
        if native_surf is None:
            self.native_surf = pg.Surface((1280, 720))
            native_surf = self.native_surf

        # Render Sky, Background Parallax, and Environment Props onto native game surface
        # (env_mgr.draw fills surface first, then renders all layers — same pipeline as game)
        self.env_mgr.draw(native_surf, cam_x=self.cam_x, cam_y=self.cam_y)

        # FL Studio Piano Roll Style Snap Grid Overlay (semi-transparent, over the scene)
        if self.grid_snap > 0:
            step = int(self.grid_snap)
            cached_step = getattr(self, "_cached_grid_step", 0)
            if cached_step != step or not hasattr(self, "_grid_overlay"):
                self._grid_overlay = pg.Surface((1280, 720), pg.SRCALPHA)
                grid_col = (80, 90, 120, 40)
                for gx in range(0, 1280, step):
                    pg.draw.line(self._grid_overlay, grid_col, (gx, 0), (gx, 720), 1)
                for gy_line in range(0, 720, step):
                    pg.draw.line(self._grid_overlay, grid_col, (0, gy_line), (1280, gy_line), 1)
                self._cached_grid_step = step
            native_surf.blit(self._grid_overlay, (0, 0))

        # Render Ground Line Indicator
        gy = self.env_mgr.ground_y
        gy_draw = int(gy - self.cam_y)
        pg.draw.line(native_surf, SUCCESS, (0, gy_draw), (1280, gy_draw), 2)

        # Render Ruler Ticks
        start_m = int(self.cam_x // 500 * 500)
        for dist_m in range(start_m, start_m + int(1280 / self.cam_zoom) + 1000, 500):
            cx = int((dist_m - self.cam_x) * self.cam_zoom)
            if 0 <= cx <= 1280:
                pg.draw.line(native_surf, BORDER, (cx, gy_draw), (cx, gy_draw + 15), 2)
                t = self.sf.render(f"{dist_m}m", True, TXT2)
                native_surf.blit(t, (cx - t.get_width() // 2, gy_draw + 18))

        # Render Prop Selection Highlights & Corner Gizmos on Canvas
        if 0 <= self.selected_prop_idx < len(self.env_mgr.props):
            prop = self.env_mgr.props[self.selected_prop_idx]
            draw_x = int(prop.pos_x - self.cam_x * prop.parallax_ratio)
            draw_y = int(prop.pos_y - self.cam_y)
            prect = pg.Rect(draw_x, draw_y, prop.width, prop.height)
            
            col_type_val = getattr(prop, "collision_type", "solid")
            col_icon = "🧱 SOLID" if col_type_val == "solid" else ("🪜 PLATFORM" if col_type_val == "platform" else ("⚠️ HAZARD" if col_type_val == "hazard" else "🌿 DECO"))
            box_col = (231, 76, 60) if col_type_val == "hazard" else ACCENT
            pg.draw.rect(native_surf, box_col, prect, width=2, border_radius=4)
            for cx, cy in [(prect.left, prect.top), (prect.right, prect.top), (prect.left, prect.bottom), (prect.right, prect.bottom)]:
                pg.draw.rect(native_surf, (241, 196, 15), pg.Rect(cx - 4, cy - 4, 8, 8))

            # Cyan Ground Contact Line Gizmo (for Solid & Platform props)
            if col_type_val in ("solid", "platform"):
                offset_y = getattr(prop, "collision_offset_y", 0.0)
                contact_draw_y = int(draw_y + offset_y)
                # Cyan solid line across prop width
                pg.draw.line(native_surf, (0, 255, 255), (prect.left, contact_draw_y), (prect.right, contact_draw_y), 3)
                # Draw small handle point at center
                pg.draw.circle(native_surf, (0, 255, 255), (prect.centerx, contact_draw_y), 5)
                # Tag label
                c_lbl = self.sf.render(f"CONTACT Y: +{int(offset_y)}px", True, (0, 255, 255))
                native_surf.blit(c_lbl, (prect.right + 8, contact_draw_y - c_lbl.get_height() // 2))

            ptag = self.sf.render(f"[{col_icon}] L{prop.layer_index} | Pos: ({int(prop.pos_x)}, {int(prop.pos_y)}) | Size: {prop.width}x{prop.height}px | Scale: {prop.scale:.1f}x", True, (20, 20, 20))
            tag_box = ptag.get_rect(midbottom=(prect.centerx, max(12, prect.y - 6))).inflate(12, 6)
            pg.draw.rect(native_surf, box_col, tag_box, border_radius=4)
            native_surf.blit(ptag, ptag.get_rect(center=tag_box.center))

        # Render Player Character Guide / Simulation Sprite (100% compliance with game physics)
        player_tex_path = "assets/shadow_warrior/idle/idle_1.png"
        player_tex_raw = AssetManager.get_texture(player_tex_path)
        if player_tex_raw and player_tex_raw.get_width() > 1:
            # Scale to match game (3x = player scale from entity_dimensions.json)
            player_scale = 3.0
            player_tex = pg.transform.smoothscale(
                player_tex_raw,
                (int(player_tex_raw.get_width() * player_scale),
                 int(player_tex_raw.get_height() * player_scale))
            )
            pw, ph = player_tex.get_width(), player_tex.get_height()
            px = 120
            eff_gy_val = self.env_mgr.get_ground_y_at(px + self.cam_x)
            eff_gy = eff_gy_val if eff_gy_val is not None else float(self.env_mgr.ground_y)
            py = int(eff_gy - ph - self.cam_y)
            if self.simulating:
                t_step = int((pg.time.get_ticks() / 150) % 2) + 1
                w_path = f"assets/shadow_warrior/run/run_{t_step}.png"
                w_tex_raw = AssetManager.get_texture(w_path)
                if w_tex_raw and w_tex_raw.get_width() > 1:
                    w_tex = pg.transform.smoothscale(
                        w_tex_raw,
                        (int(w_tex_raw.get_width() * player_scale),
                         int(w_tex_raw.get_height() * player_scale))
                    )
                    native_surf.blit(w_tex, (px, int(eff_gy - w_tex.get_height() - self.cam_y)))
                else:
                    native_surf.blit(player_tex, (px, py))
            else:
                ghost_surf = player_tex.copy()
                ghost_surf.set_alpha(220)
                native_surf.blit(ghost_surf, (px, py))
                rtag = self.sf.render("PLAYER", True, (241, 196, 15))
                native_surf.blit(rtag, (px + pw // 2 - rtag.get_width() // 2, py - 18))

        # Render Ambient Bats Floating in Sky (100% compliance with game)
        bat_tex = AssetManager.get_texture("assets/graphics/bat/idle/bat_idle_0.png")
        if bat_tex and bat_tex.get_width() > 1:
            ticks = pg.time.get_ticks() / 1000.0
            bat_coords = [
                (450, int(180 + math.sin(ticks * 2.0) * 10 - self.cam_y * 0.1)),
                (520, int(240 + math.sin(ticks * 2.5 + 1.0) * 12 - self.cam_y * 0.1)),
                (550, int(280 + math.sin(ticks * 2.2 + 2.0) * 8 - self.cam_y * 0.1)),
                (600, int(220 + math.sin(ticks * 2.8 + 1.5) * 14 - self.cam_y * 0.1))
            ]
            for bx, by in bat_coords:
                native_surf.blit(bat_tex, (bx, by))

        # Blit native 1280x720 surface scaled smoothly to the 16:9 editor viewport
        avail_rect = self._get_s5_avail_bounds()
        pg.draw.rect(self.surf, BG, avail_rect)
        scaled_viewport = pg.transform.smoothscale(native_surf, (canvas_rect.w, canvas_rect.h))
        self.surf.blit(scaled_viewport, (canvas_rect.x, canvas_rect.y))
        pg.draw.rect(self.surf, BORDER, canvas_rect, width=2)

        # Top Bar Panel, Fullscreen, and Recenter View Control Buttons
        b_recenter = Button("🎯 Recenter (Home)", W - 485, 10, 155, 32, self._recenter_cam, "ghost")
        b_recenter.draw(self.surf, self.sf)
        self._s5b.append(b_recenter)

        p_txt = "► Show Panels (Tab)" if getattr(self, "panels_collapsed", False) else "◄ Hide Panels (Tab)"
        b_panels = Button(p_txt, W - 325, 10, 150, 32, self._toggle_panels, "ghost")
        b_panels.draw(self.surf, self.sf)
        self._s5b.append(b_panels)

        fs_txt = "🖥️ Windowed (F11)" if getattr(self, "fullscreen", False) else "🖥️ Fullscreen (F11)"
        b_fs = Button(fs_txt, W - 165, 10, 155, 32, self._toggle_fullscreen, "ghost")
        b_fs.draw(self.surf, self.sf)
        self._s5b.append(b_fs)

        # ── 2. LEFT SIDEBAR (ENVIRONMENT STUDIO & SLICER TOOLS) ─────────────────
        left_panel = pg.Rect(0, 50, 280, H - 115)
        if not getattr(self, "panels_collapsed", False):
            pg.draw.rect(self.surf, PANEL, left_panel)
            pg.draw.line(self.surf, BORDER, (left_panel.right, left_panel.y), (left_panel.right, left_panel.bottom), 2)

        if 0 <= self.selected_prop_idx < len(self.env_mgr.props):
            prop = self.env_mgr.props[self.selected_prop_idx]
            hdr = self.tf.render("Prop Inspector", True, (241, 196, 15))
            self.surf.blit(hdr, (14, left_panel.y + 12))

            def _desel_p():
                self.selected_prop_idx = -1
                self._init_s5_widgets()

            Button("Deselect ✕", 170, left_panel.y + 10, 95, 28, _desel_p, "ghost").draw(self.surf, self.sf)

            fname = os.path.basename(prop.texture_path)
            self.surf.blit(self.sf.render(f"Asset: {fname[:24]}", True, TXT2), (14, left_panel.y + 45))
            self.surf.blit(self.sf.render(f"Pos: ({int(prop.pos_x)}, {int(prop.pos_y)})px  |  Size: {prop.width}x{prop.height}px", True, TXT), (14, left_panel.y + 65))

            # Pos X Adjusters
            def _adj_px(d: int):
                prop.pos_x += d
                self.level_data["environment"] = self.env_mgr.to_config_dict()
            b_px_m = Button("-50px", 14, left_panel.y + 85, 115, 26, lambda: _adj_px(-50), "ghost")
            b_px_p = Button("+50px", 145, left_panel.y + 85, 115, 26, lambda: _adj_px(50), "ghost")
            b_px_m.draw(self.surf, self.sf); b_px_p.draw(self.surf, self.sf)

            # Pos Y Adjusters
            def _adj_py(d: int):
                prop.pos_y += d
                self.level_data["environment"] = self.env_mgr.to_config_dict()
            b_py_m = Button("-10px", 14, left_panel.y + 115, 115, 26, lambda: _adj_py(-10), "ghost")
            b_py_p = Button("+10px", 145, left_panel.y + 115, 115, 26, lambda: _adj_py(10), "ghost")
            b_py_m.draw(self.surf, self.sf); b_py_p.draw(self.surf, self.sf)

            # Scale / Size Enlargement Controls
            self.surf.blit(self.sf.render(f"Scale / Size: {prop.scale:.1f}x", True, TXT2), (14, left_panel.y + 148))

            def _adj_pscale(delta: float):
                prop.scale = max(0.2, round(prop.scale + delta, 1))
                raw_texture = AssetManager.get_texture(prop.texture_path)
                if prop.slice_rect and len(prop.slice_rect) == 4:
                    rx, ry, rw, rh = prop.slice_rect
                    rx = max(0, min(rx, raw_texture.get_width() - 1))
                    ry = max(0, min(ry, raw_texture.get_height() - 1))
                    rw = max(1, min(rw, raw_texture.get_width() - rx))
                    rh = max(1, min(rh, raw_texture.get_height() - ry))
                    sub_surf = raw_texture.subsurface(pg.Rect(rx, ry, rw, rh))
                else:
                    sub_surf = raw_texture

                if prop.flip_x or prop.flip_y:
                    sub_surf = pg.transform.flip(sub_surf, prop.flip_x, prop.flip_y)

                target_w = max(1, int(sub_surf.get_width() * prop.scale))
                target_h = max(1, int(sub_surf.get_height() * prop.scale))
                prop.image = pg.transform.smoothscale(sub_surf, (target_w, target_h))
                prop.width = prop.image.get_width()
                prop.height = prop.image.get_height()
                self.level_data["environment"] = self.env_mgr.to_config_dict()

            def _set_pscale(target: float):
                _adj_pscale(target - prop.scale)

            b_sc_m = Button("🔍 -0.5x", 14, left_panel.y + 168, 115, 26, lambda: _adj_pscale(-0.5), "ghost")
            b_sc_p = Button("🔍 +0.5x", 145, left_panel.y + 168, 115, 26, lambda: _adj_pscale(0.5), "ghost")
            b_sc_m.draw(self.surf, self.sf); b_sc_p.draw(self.surf, self.sf)

            b_sc1 = Button("1.0x", 14, left_panel.y + 198, 55, 24, lambda: _set_pscale(1.0), "ghost")
            b_sc2 = Button("2.0x", 74, left_panel.y + 198, 55, 24, lambda: _set_pscale(2.0), "ghost")
            b_sc3 = Button("3.0x", 134, left_panel.y + 198, 55, 24, lambda: _set_pscale(3.0), "ghost")
            b_sc4 = Button("4.0x", 194, left_panel.y + 198, 55, 24, lambda: _set_pscale(4.0), "ghost")
            b_sc1.draw(self.surf, self.sf); b_sc2.draw(self.surf, self.sf)
            b_sc3.draw(self.surf, self.sf); b_sc4.draw(self.surf, self.sf)

            # Layer Depth Controls
            max_layer_key = max(self.env_mgr.layer_stacks.keys(), default=5)
            self.surf.blit(self.sf.render(f"Layer Depth: Layer {prop.layer_index}", True, TXT2), (14, left_panel.y + 230))
            def _adj_layer(d: int):
                prop.layer_index = max(1, min(max_layer_key, prop.layer_index + d))
                prop.parallax_ratio = self.env_mgr.layer_stacks.get(prop.layer_index, {}).get("scroll_ratio", 1.0)
                self.level_data["environment"] = self.env_mgr.to_config_dict()
            def _set_l6_ground():
                prop.layer_index = 6
                prop.parallax_ratio = 1.0
                self.level_data["environment"] = self.env_mgr.to_config_dict()

            b_l_m = Button("⬇ Back", 14, left_panel.y + 250, 75, 26, lambda: _adj_layer(-1), "ghost")
            b_l_p = Button("⬆ Front", 94, left_panel.y + 250, 75, 26, lambda: _adj_layer(1), "ghost")
            b_l_6 = Button("📌 L6 Ground", 174, left_panel.y + 250, 92, 26, _set_l6_ground, "primary")
            b_l_m.draw(self.surf, self.sf); b_l_p.draw(self.surf, self.sf); b_l_6.draw(self.surf, self.sf)

            col_type = getattr(prop, "collision_type", "solid")
            col_labels = {
                "solid": "🧱 Type: Solid Ground",
                "platform": "🪜 Type: Jump Platform",
                "hazard": "⚠️ Type: Hazard / Trap (Spikes)",
                "deco": "🌿 Type: Decorative"
            }
            col_styles = {
                "solid": "success",
                "platform": "primary",
                "hazard": "warning",
                "deco": "ghost"
            }
            self.surf.blit(self.sf.render("Physics & Collision Type:", True, TXT2), (14, left_panel.y + 284))

            def _cycle_col_type():
                types = ["solid", "platform", "hazard", "deco"]
                cur_i = types.index(getattr(prop, "collision_type", "solid")) if getattr(prop, "collision_type", "solid") in types else 0
                next_t = types[(cur_i + 1) % len(types)]
                prop.collision_type = next_t
                prop.is_ground = (next_t in ("solid", "platform"))
                if next_t in ("solid", "platform", "hazard"):
                    prop.layer_index = 6
                    prop.parallax_ratio = 1.0
                self.level_data["environment"] = self.env_mgr.to_config_dict()

            b_col_type = Button(col_labels.get(col_type, "🧱 Type: Solid Ground"), 14, left_panel.y + 304, 252, 30, _cycle_col_type, col_styles.get(col_type, "primary"))
            b_col_type.draw(self.surf, self.sf)

            # Ground Surface Contact Y Offset Controls (for Solid & Platform props)
            if col_type in ("solid", "platform"):
                offset_y = getattr(prop, "collision_offset_y", 0.0)
                eff_contact_y = int(prop.pos_y + offset_y)
                lbl_offset = self.sf.render(f"Contact Offset: +{int(offset_y)}px (Y: {eff_contact_y}px)", True, ACCENT)
                self.surf.blit(lbl_offset, (14, left_panel.y + 342))

                def _adj_offset(delta: float):
                    cur = getattr(prop, "collision_offset_y", 0.0)
                    new_val = max(0.0, min(float(prop.height - 1), cur + delta))
                    prop.collision_offset_y = new_val
                    self.level_data["environment"] = self.env_mgr.to_config_dict()

                def _auto_detect_offset():
                    prop.auto_detect_collision_offset()
                    self.level_data["environment"] = self.env_mgr.to_config_dict()

                b_off_m5 = Button("-5px", 14, left_panel.y + 364, 55, 24, lambda: _adj_offset(-5.0), "ghost")
                b_off_p5 = Button("+5px", 74, left_panel.y + 364, 55, 24, lambda: _adj_offset(5.0), "ghost")
                b_off_m1 = Button("-1px", 134, left_panel.y + 364, 55, 24, lambda: _adj_offset(-1.0), "ghost")
                b_off_p1 = Button("+1px", 194, left_panel.y + 364, 55, 24, lambda: _adj_offset(1.0), "ghost")
                b_off_auto = Button("🪄 Auto Detect Contact Line", 14, left_panel.y + 394, 252, 28, _auto_detect_offset, "primary")

                b_off_m5.draw(self.surf, self.sf); b_off_p5.draw(self.surf, self.sf)
                b_off_m1.draw(self.surf, self.sf); b_off_p1.draw(self.surf, self.sf)
                b_off_auto.draw(self.surf, self.sf)
                self._s5b += [b_off_m5, b_off_p5, b_off_m1, b_off_p1, b_off_auto]

            # Duplicate & Delete Buttons
            b_dup = Button("📋 Duplicate (Ctrl+D)", 14, left_panel.bottom - 95, 252, 36, self.duplicate_selected_prop, "primary")
            b_del = Button("🗑 Delete Prop (Delete)", 14, left_panel.bottom - 50, 252, 38, self.delete_selected_prop, "danger")
            b_dup.draw(self.surf, self.f); b_del.draw(self.surf, self.f)
            self._s5b += [b_px_m, b_px_p, b_py_m, b_py_p, b_sc_m, b_sc_p, b_sc1, b_sc2, b_sc3, b_sc4, b_l_m, b_l_p, b_col_type, b_dup, b_del]

        else:
            hdr = self.tf.render("5-Layer Environment Engine", True, ACCENT)
            self.surf.blit(hdr, (14, left_panel.y + 14))

            def _open_slicer():
                cur_stack = self.env_mgr.layer_stacks.get(self.active_layer_filter, {})
                tpath = cur_stack.get("texture_path", "")
                folder = os.path.dirname(tpath).replace("\\", "/") if tpath else getattr(self, "active_asset_folder", "assets/graphics/background images/new_bg_images")
                self.slicer_modal = SpritesheetSlicerModal(
                    select_cb=self._on_select_prop_from_slicer,
                    cancel_cb=lambda: setattr(self, "slicer_modal", None),
                    active_folder=folder
                )

            slicer_btn = Button("✂️ Open Spritesheet Slicer", 14, left_panel.y + 45, 252, 38, _open_slicer, "success")
            slicer_btn.draw(self.surf, self.f)
            self._s5b.append(slicer_btn)

            def _add_new_layer():
                new_idx = self.env_mgr.add_layer()
                self.active_layer_filter = new_idx
                self.level_data["environment"] = self.env_mgr.to_config_dict()

            add_layer_btn = Button("➕ Add Layer", 14, left_panel.y + 90, 252, 32, _add_new_layer, "primary")
            add_layer_btn.draw(self.surf, self.f)
            self._s5b.append(add_layer_btn)

            pg.draw.line(self.surf, BORDER, (14, left_panel.y + 128), (left_panel.right - 14, left_panel.y + 128))

            sub_lbl = self.sf.render("Select Active Layer:", True, TXT2)
            self.surf.blit(sub_lbl, (14, left_panel.y + 134))

            ly_y = left_panel.y + 154
            for l_idx in sorted(self.env_mgr.layer_stacks.keys()):
                l_info = self.env_mgr.layer_stacks[l_idx]
                l_name = l_info.get("name", f"L{l_idx}: Layer {l_idx}")
                is_active = (self.active_layer_filter == l_idx)
                def _set_l(li=l_idx): self.active_layer_filter = li
                b = Button(f"L{l_idx}: {l_name[:20]}", 14, ly_y, 252, 30, _set_l, "primary" if is_active else "ghost")
                b.draw(self.surf, self.sf)
                self._s5b.append(b)
                ly_y += 34

            pg.draw.line(self.surf, BORDER, (14, left_panel.bottom - 105), (left_panel.right - 14, left_panel.bottom - 105))
            b_rst_layer = Button("🔄 Reset Active Layer", 14, left_panel.bottom - 92, 252, 34, self.reset_active_layer, "danger")
            b_rst_env = Button("⚠️ Reset All Environment", 14, left_panel.bottom - 48, 252, 34, self.reset_entire_environment, "danger")
            b_rst_layer.draw(self.surf, self.f); b_rst_env.draw(self.surf, self.f)
            self._s5b += [b_rst_layer, b_rst_env]

        # ── 3. RIGHT SIDEBAR (LAYER PARALLAX INSPECTOR) ─────────────────────────
        right_panel = pg.Rect(W - 280, 50, 280, H - 115)
        if not getattr(self, "panels_collapsed", False):
            pg.draw.rect(self.surf, PANEL, right_panel)
            pg.draw.line(self.surf, BORDER, (right_panel.x, right_panel.y), (right_panel.x, right_panel.bottom), 2)

            cur_stack = self.env_mgr.layer_stacks.get(self.active_layer_filter, {})
            rhdr = self.tf.render(f"Layer {self.active_layer_filter} Inspector", True, SUCCESS)
            self.surf.blit(rhdr, (right_panel.x + 14, right_panel.y + 14))

            layer_title = cur_stack.get("name", f"Layer {self.active_layer_filter}")
            self.surf.blit(self.f.render(layer_title, True, TXT), (right_panel.x + 14, right_panel.y + 40))

            bg_path = cur_stack.get("texture_path", "")
            bg_name = os.path.basename(bg_path) if bg_path else "None (Transparent)"
            self.surf.blit(self.sf.render(f"Texture: {bg_name[:22]}", True, WARN if bg_path else TXT2), (right_panel.x + 14, right_panel.y + 64))

            def _open_bg_picker():
                cur_stack = self.env_mgr.layer_stacks.get(self.active_layer_filter, {})
                tpath = cur_stack.get("texture_path", "")
                folder = os.path.dirname(tpath).replace("\\", "/") if tpath else getattr(self, "active_asset_folder", "assets/graphics/background images/new_bg_images")
                self.bg_picker_modal = LinuxAssetExplorerModal(
                    select_cb=self._on_select_bg_from_modal,
                    cancel_cb=lambda: setattr(self, "bg_picker_modal", None),
                    current_dir=folder
                )

            bg_pick_btn = Button(f"🖼 Set L{self.active_layer_filter} Texture", right_panel.x + 14, right_panel.y + 88, 252, 34, _open_bg_picker, "primary")
            bg_clear_btn = Button(f"🔄 Reset L{self.active_layer_filter} Layer", right_panel.x + 14, right_panel.y + 126, 252, 30, self.reset_active_layer, "danger")
            bg_pick_btn.draw(self.surf, self.f); bg_clear_btn.draw(self.surf, self.sf)
            self._s5b += [bg_pick_btn, bg_clear_btn]

            if len(self.env_mgr.layer_stacks) > 1:
                def _del_layer():
                    if self.env_mgr.delete_layer(self.active_layer_filter):
                        self.active_layer_filter = min(self.env_mgr.layer_stacks.keys(), default=1)
                        self.level_data["environment"] = self.env_mgr.to_config_dict()
                del_layer_btn = Button(f"🗑 Delete Layer L{self.active_layer_filter}", right_panel.x + 14, right_panel.y + 160, 252, 28, _del_layer, "danger")
                del_layer_btn.draw(self.surf, self.sf)
                self._s5b.append(del_layer_btn)

            if self.active_layer_filter == 1:
                sky_on = (self.env_mgr.sky is not None)
                def _toggle_sky():
                    self.env_mgr.toggle_sky()
                    self.level_data["environment"] = self.env_mgr.to_config_dict()
                sky_btn = Button("🌌 Sky Overlay: ON" if sky_on else "🌌 Sky Overlay: OFF", right_panel.x + 14, right_panel.y + 192, 252, 28, _toggle_sky, "success" if sky_on else "ghost")
                sky_btn.draw(self.surf, self.sf)
                self._s5b.append(sky_btn)

            pg.draw.line(self.surf, BORDER, (right_panel.x + 14, right_panel.y + 226), (right_panel.right - 14, right_panel.y + 226))

            self.surf.blit(self.sf.render(f"Scroll Ratio: {cur_stack.get('scroll_ratio', 0.1):.2f}", True, TXT2), (right_panel.x + 14, right_panel.y + 234))
            def _adj_sratio(delta: float):
                cur_stack["scroll_ratio"] = max(0.0, round(cur_stack.get("scroll_ratio", 0.1) + delta, 2))
                if cur_stack.get("parallax_layer"):
                    cur_stack["parallax_layer"].scroll_ratio = cur_stack["scroll_ratio"]
                self.level_data["environment"] = self.env_mgr.to_config_dict()

            b_sr_m = Button("-0.05", right_panel.x + 14, right_panel.y + 254, 115, 26, lambda: _adj_sratio(-0.05), "ghost")
            b_sr_p = Button("+0.05", right_panel.x + 145, right_panel.y + 254, 115, 26, lambda: _adj_sratio(0.05), "ghost")
            b_sr_m.draw(self.surf, self.sf); b_sr_p.draw(self.surf, self.sf)
            self._s5b += [b_sr_m, b_sr_p]

            # Texture Stretch & Scale Controls
            sx = cur_stack.get("scale_x", 1.0)
            sy = cur_stack.get("scale_y", 1.0)
            sf = cur_stack.get("stretch_fill", False)

            self.surf.blit(self.sf.render(f"Scale X: {sx:.1f}x  |  Scale Y: {sy:.1f}x", True, TXT2), (right_panel.x + 14, right_panel.y + 286))

            def _adj_sx(d: float):
                new_sx = max(0.1, round(cur_stack.get("scale_x", 1.0) + d, 1))
                self.env_mgr.set_layer_texture(self.active_layer_filter, cur_stack.get("texture_path", ""), scale_x=new_sx)
                self.level_data["environment"] = self.env_mgr.to_config_dict()

            def _adj_sy(d: float):
                new_sy = max(0.1, round(cur_stack.get("scale_y", 1.0) + d, 1))
                self.env_mgr.set_layer_texture(self.active_layer_filter, cur_stack.get("texture_path", ""), scale_y=new_sy)
                self.level_data["environment"] = self.env_mgr.to_config_dict()

            b_sx_m = Button("-0.2x X", right_panel.x + 14, right_panel.y + 306, 115, 26, lambda: _adj_sx(-0.2), "ghost")
            b_sx_p = Button("+0.2x X", right_panel.x + 145, right_panel.y + 306, 115, 26, lambda: _adj_sx(0.2), "ghost")
            b_sy_m = Button("-0.2x Y", right_panel.x + 14, right_panel.y + 336, 115, 26, lambda: _adj_sy(-0.2), "ghost")
            b_sy_p = Button("+0.2x Y", right_panel.x + 145, right_panel.y + 336, 115, 26, lambda: _adj_sy(0.2), "ghost")
            b_sx_m.draw(self.surf, self.sf); b_sx_p.draw(self.surf, self.sf)
            b_sy_m.draw(self.surf, self.sf); b_sy_p.draw(self.surf, self.sf)
            self._s5b += [b_sx_m, b_sx_p, b_sy_m, b_sy_p]

            def _toggle_stretch():
                new_sf = not cur_stack.get("stretch_fill", False)
                self.env_mgr.set_layer_texture(self.active_layer_filter, cur_stack.get("texture_path", ""), stretch_fill=new_sf)
                self.level_data["environment"] = self.env_mgr.to_config_dict()

            b_stretch = Button("📐 Mode: Fill Canvas" if sf else "📐 Mode: Ratio Scale", right_panel.x + 14, right_panel.y + 366, 252, 28, _toggle_stretch, "primary" if sf else "ghost")
            b_stretch.draw(self.surf, self.sf)
            self._s5b.append(b_stretch)

            pg.draw.line(self.surf, BORDER, (right_panel.x + 14, right_panel.y + 280), (right_panel.right - 14, right_panel.y + 280))

            if self.s5_ground_slider: self.s5_ground_slider.draw(self.surf, self.f, self.sf)

        # ── 4. BOTTOM TRACK MINIMAP & CONTROL BAR ───────────────────────────────
        bbar = pg.Rect(0, H - 65, W, 65)
        pg.draw.rect(self.surf, PANEL, bbar)
        pg.draw.line(self.surf, BORDER, (0, bbar.y), (W, bbar.y), 2)

        self.surf.blit(self.sf.render("Grid Snap:", True, TXT2), (14, bbar.y + 22))
        snaps = [0, 16, 32, 64, 500]
        for i, sval in enumerate(snaps):
            label = "Free" if sval == 0 else (f"{sval}px" if sval < 100 else f"{sval}m")
            is_active = (self.grid_snap == sval)
            def _set_snap(v=sval): self.grid_snap = v
            sb = Button(label, 80 + i * 44, bbar.y + 16, 40, 32, _set_snap, "primary" if is_active else "ghost")
            sb.draw(self.surf, self.sf)
            self._s5b.append(sb)

        # Track Minimap
        map_w = min(650, max(200, W - 500))
        map_x = max(10, (W - map_w) // 2)
        map_y = bbar.y + 16
        map_h = 32
        pg.draw.rect(self.surf, PANEL2, pg.Rect(map_x, map_y, map_w, map_h), border_radius=6)
        pg.draw.rect(self.surf, BORDER, pg.Rect(map_x, map_y, map_w, map_h), width=1, border_radius=6)

        end_dist = float(self.level_data.get("level_end_distance", 36000))
        for p in self.env_mgr.props:
            px = map_x + int((p.pos_x / end_dist) * map_w)
            if map_x <= px <= map_x + map_w:
                pg.draw.circle(self.surf, (241, 196, 15), (px, map_y + map_h // 2), 3)

        cam_start_x = map_x + int((self.cam_x / end_dist) * map_w)
        cam_view_w = max(16, int(((canvas_rect.w / self.cam_zoom) / end_dist) * map_w))
        pg.draw.rect(self.surf, WARN, pg.Rect(cam_start_x, map_y, cam_view_w, map_h), width=2, border_radius=4)

        def _open_level_mgr():
            def _select_level(path: str):
                self.level_mgr_modal = None
                if path in self.level_files:
                    idx = self.level_files.index(path)
                    self.load(idx)
                    self.go5()

            def _create_level():
                self.level_mgr_modal = None
                self.go1()

            self.level_mgr_modal = LevelManagerModal(
                select_cb=_select_level,
                create_cb=_create_level,
                cancel_cb=lambda: setattr(self, "level_mgr_modal", None)
            )

        def _toggle_sim(): self.simulating = not self.simulating
        def _save_canvas():
            self.level_data["environment"] = self.env_mgr.to_config_dict()
            self.commit()
            fname = os.path.basename(self.level_files[self.active_idx]) if self.level_files else "level_1.json"
            self.modal = ModalDialog("Level Saved ✓", f"Saved environment configuration to '{fname}'!", lambda: setattr(self, "modal", None))

        files_btn = Button("📂 Switch / New Level", W - 435, 10, 140, 32, _open_level_mgr, "primary")
        files_btn.draw(self.surf, self.sf); self._s5b.append(files_btn)

        sim_btn = Button("PAUSE ❚❚" if self.simulating else "SIMULATE ▶", W - 290, bbar.y + 14, 130, 36, _toggle_sim, "warn" if self.simulating else "primary")
        save_btn = Button("Save Level ✓", W - 145, bbar.y + 14, 130, 36, _save_canvas, "success")
        sim_btn.draw(self.surf, self.sf); save_btn.draw(self.surf, self.sf)
        self._s5b += [sim_btn, save_btn]

        if hasattr(self, "level_mgr_modal") and self.level_mgr_modal:
            self.level_mgr_modal.draw(self.surf, self.tf, self.sf)
        if self.bg_picker_modal:
            self.bg_picker_modal.draw(self.surf, self.tf, self.sf)
        if self.slicer_modal:
            self.slicer_modal.draw(self.surf, self.tf, self.sf)

    def _on_select_bg_from_modal(self, bg_path: str, folder_path: Optional[str] = None):
        self.env_mgr.set_layer_texture(self.active_layer_filter, bg_path)
        if folder_path:
            self.active_asset_folder = folder_path
        self.level_data["environment"] = self.env_mgr.to_config_dict()
        self.bg_picker_modal = None

    def _find_event_at_canvas_pos(self, mx: int, my: int) -> int:
        native_x = (mx - 280) * (1280.0 / (W - 560))
        native_y = (my - 50) * (720.0 / (H - 115))
        gy = self.env_mgr.ground_y
        for idx, ev in enumerate(self.pending):
            dist = ev.get("distance", 0)
            cx = int((dist - self.cam_x) * self.cam_zoom)
            if abs(native_x - cx) < 45 and gy - 140 <= native_y <= gy + 30:
                return idx
        return -1

    def _next_id(self) -> int:
        return max((e["id"] for e in self.pending), default=0) + 1

    def _init_s3(self, etype: str, idx: int):
        ev   = self.pending[idx] if idx >= 0 else {}
        p    = ev.get("params", {})
        _end_raw = self.level_data.get("level_end_distance", 8000)
        end  = float(_end_raw) if isinstance(_end_raw, (int, float)) else 8000.0
        _dist_raw = ev.get("distance", 500)
        dist = float(_dist_raw) if isinstance(_dist_raw, (int, float)) else 500.0
        if etype == "npc":
            nt = p.get("npc_type", "generic")
            sprite_dir = p.get("sprite_dir") or ""

            # Registry wins over stale level JSON. This prevents reports like:
            # level JSON scale=3.86 but entity_dimensions.json scale=4.61.
            current_scale = float(p.get("scale", 1.0))
            default_scale = _scale_from_registry("npc", nt, sprite_dir, current_scale)

            self.s3_ui = {
                "npc_type": nt,
                "title":  TextInput("NPC Title", 472, CONTENT_Y+56,  782, initial=p.get("title","New NPC")),
                "text":   TextArea("Dialogue",   472, CONTENT_Y+116, 782, 110, initial=p.get("text","..."), placeholder="Enter dialogue text..."),
                "radius": Slider("Proximity Radius", 472, CONTENT_Y+252, 782, 50, 400, float(p.get("radius",160))),
                "dist":   Slider("Trigger Distance", 472, CONTENT_Y+320, 782, 0, end, dist),
                "scale":  Slider("Scale", 472, CONTENT_Y+388, 782, 0.5, 6.0, default_scale, True),
            }
            self.browser.selected = p.get("sprite_dir") or None
        elif etype == "boss":
            current_scale = float(p.get("scale", 2.0))
            default_scale = _scale_from_registry("boss", "", p.get("sprite_dir") or "", current_scale)
            self.s3_ui = {
                "title":  TextInput("Boss Name", 462, CONTENT_Y+48,  380, initial=p.get("title","Mini Boss")),
                "dist":   Slider("Trigger Distance", 462, CONTENT_Y+132, 380, 0, end, dist),
                "scale":  Slider("Boss Scale", 462, CONTENT_Y+218, 380, 0.5, 6.0, default_scale, True),
                "health": Slider("Boss Health", 462, CONTENT_Y+304, 380, 10, 500, float(p.get("health",100.0))),
                "tier":   str(p.get("tier", "boss")),
            }
            self.browser.selected = p.get("sprite_dir") or None
            self.bmap.load(self.browser.selected, p.get("behaviour_map"))
        else:
            self.s3_ui = {
                "title":  TextInput("Title",    160, CONTENT_Y+60,  940, initial=p.get("title","Sign")),
                "text":   TextArea("Dialogue", 160, CONTENT_Y+124, 940, 140, initial=p.get("text","..."), placeholder="Enter dialogue text..."),
                "radius": Slider("Proximity Radius", 160, CONTENT_Y+294, 940, 50, 400, float(p.get("radius",160))),
                "dist":   Slider("Trigger Distance", 160, CONTENT_Y+374, 940, 0, end, dist),
            }
        self.prev_frames, self.prev_timer, self.prev_idx, self.prev_dir = [], 0.0, 0, ""

    def _read_s3(self) -> dict:
        ui   = self.s3_ui
        t    = self.s3_type
        ev   = self.pending[self.s3_idx] if self.s3_idx >= 0 else {}
        eid  = ev.get("id", self._next_id())
        dist = int(ui["dist"].val)
        if t == "npc":
            nt = ui.get("npc_type", "generic")
            p: dict = {"npc_type": nt, "title": ui["title"].val,
                       "text": ui["text"].val, "radius": int(ui["radius"].val)}
            sprite_dir = ""
            if nt == "generic":
                sprite_dir = self.browser.selected or ""
                p["sprite_dir"] = sprite_dir

            # Save the new scale to both level JSON and HitboxRegistry
            new_scale = float(ui["scale"].val)
            key = _registry_key("npc", nt, sprite_dir)
            if key:
                old_margins = HitboxRegistry.get_margins(key)
                new_margins = HitboxMargins(
                    left=old_margins.left,
                    right=old_margins.right,
                    top=old_margins.top,
                    bottom=old_margins.bottom,
                    ground_offset=old_margins.ground_offset,
                    scale=new_scale
                )
                HitboxRegistry.update_margins(key, new_margins)
            p["scale"] = new_scale
        elif t == "boss":
            sprite_dir = self.browser.selected or ""
            p = {
                "title": ui["title"].val,
                "scale": float(ui["scale"].val),
                "health": float(ui["health"].val),
                "tier": ui.get("tier", "boss"),
                "sprite_dir": sprite_dir,
                "behaviour_map": dict(self.bmap.mapping)
            }
            new_scale = float(ui["scale"].val)
            key = _registry_key("boss", "", sprite_dir)
            if key:
                old_margins = None
                try:
                    old_margins = HitboxRegistry.get_margins(key)
                except Exception:
                    try:
                        old_margins = HitboxRegistry.get_margins("skeleton")
                    except Exception:
                        pass
                if old_margins:
                    new_margins = HitboxMargins(
                        left=old_margins.left,
                        right=old_margins.right,
                        top=old_margins.top,
                        bottom=old_margins.bottom,
                        ground_offset=old_margins.ground_offset,
                        scale=new_scale
                    )
                    HitboxRegistry.update_margins(key, new_margins)
        else:
            p = {"title": ui["title"].val, "text": ui["text"].val,
                 "radius": int(ui["radius"].val)}
        return {"id": eid, "distance": dist, "type": t, "params": p}

    def submit_s3(self, force_confirm=False):
        if self.s3_type == "boss" and not force_confirm:
            ui = self.s3_ui
            new_scale = float(ui["scale"].val)
            sprite_dir = self.browser.selected or ""
            key = _registry_key("boss", "", sprite_dir)
            registry_scale = None
            if key:
                try:
                    registry_scale = HitboxRegistry.get_margins(key).scale
                except Exception:
                    pass
            if registry_scale is None or abs(registry_scale - new_scale) > 0.01:
                def _do_confirm():
                    self.modal = None
                    if key:
                        old_margins = None
                        try:
                            old_margins = HitboxRegistry.get_margins(key)
                        except Exception:
                            try:
                                old_margins = HitboxRegistry.get_margins("skeleton")
                            except Exception:
                                pass
                        new_margins = HitboxMargins(
                            left=old_margins.left if old_margins else 65,
                            right=old_margins.right if old_margins else 65,
                            top=old_margins.top if old_margins else 20,
                            bottom=old_margins.bottom if old_margins else 0,
                            ground_offset=old_margins.ground_offset if old_margins else 127,
                            scale=new_scale
                        )
                        HitboxRegistry.update_margins(key, new_margins)
                        HitboxRegistry.save_all()
                    self.submit_s3(force_confirm=True)

                msg = f"Set registry scale for '{key}' to {new_scale:.2f}?"
                if registry_scale is not None:
                    msg = f"Update '{key}' registry scale: {registry_scale:.2f} -> {new_scale:.2f}?"
                self.modal = ModalDialog(
                    "Sync Registry Scale?",
                    msg,
                    _do_confirm,
                    lambda: setattr(self, "modal", None)
                )
                return

        ev = self._read_s3()
        if self.s3_mode == "create": self.pending.append(ev)
        else: self.pending[self.s3_idx] = ev
        self.pending.sort(key=lambda e: e["distance"])
        self.go2()

    def simulate_s3(self):
        """
        Run the simulation like the real game flow.

        Previous versions jumped to distance-300 and only ran for 6 seconds.
        That made the test fast, but it broke the actual spawning context:
        events behind the artificial start point could be detected late, and
        nearby NPCs/objects could look as if they were moving toward the edited
        event. This version starts from 0 and runs long enough to naturally
        reach the edited trigger distance.
        """
        ev = self._read_s3()
        temp_pending = list(self.pending)
        if self.s3_mode == "create":
            temp_pending.append(ev)
        else:
            temp_pending[self.s3_idx] = ev
        temp_pending.sort(key=lambda e: e["distance"])

        # Real-flow simulation: do NOT skip to the edited event.
        # Starting at 0 keeps all earlier NPCs/objects in their proper order.
        target_dist = max(0.0, float(ev.get("distance", 0)))
        start_dist = 0.0

        # The logs show world distance advancing about 1200 units in 6 seconds,
        # which is roughly 200 distance-units per second. Add a safety buffer so
        # the target has time to spawn and be observed.
        SIM_DISTANCE_PER_SEC = 200.0
        SIM_BUFFER_SEC = 4.0
        duration = max(6.0, (target_dist / SIM_DISTANCE_PER_SEC) + SIM_BUFFER_SEC)

        print(
            f"[SIM] Full-flow editor simulation: start_dist={start_dist:.1f}, "
            f"target_event_id={ev.get('id')}, target_dist={target_dist:.1f}, "
            f"duration={duration:.1f}s, events={len(temp_pending)}"
        )

        level_file = self.level_files[self.active_idx]
        try:
            with open(level_file, "r") as f:
                original_content = f.read()
        except Exception as e:
            print(f"Error backing up level file: {e}")
            return

        # Remove stale reports before running so a failed subprocess does not
        # leave you reading yesterday's simulation result.
        report_file = os.path.join("scratch", "simulation_report.json")
        try:
            if os.path.exists(report_file):
                os.remove(report_file)
        except Exception as e:
            print(f"[WARN] Could not delete stale simulation report: {e}")

        temp_data = copy.deepcopy(self.level_data)
        temp_data["world_events"] = temp_pending
        try:
            with open(level_file, "w") as f:
                json.dump(temp_data, f, indent=4)
        except Exception as e:
            print(f"Error writing temporary simulation file: {e}")
            return

        import subprocess
        import sys

        self.surf.blit(self.tf.render("Launching Full Simulation...", True, WARN), (W//2 - 190, H//2 - 20))
        pg.display.flip()

        try:
            cmd = [
                sys.executable,
                "main.py",
                "--level", level_file,
                "--start-dist", str(start_dist),
                "--duration", str(duration),
                "--target-event-id", str(ev.get('id')),
            ]
            venv_python = os.path.join(".venv", "bin", "python")
            if os.path.exists(venv_python):
                cmd[0] = venv_python
            subprocess.run(cmd, env=dict(os.environ, PYTHONPATH="."))
        except Exception as e:
            print(f"Error launching game subprocess: {e}")
        finally:
            try:
                with open(level_file, "w") as f:
                    f.write(original_content)
            except Exception as e:
                print(f"Error restoring original level file content: {e}")

        # Check simulation report results. This still depends on main.py's
        # simulation reporter, but now the run itself matches the real level flow.
        if os.path.exists(report_file):
            try:
                with open(report_file, "r") as f:
                    report = json.load(f)
                if report.get("status") == "FAILED":
                    self.modal = ModalDialog(
                        "Simulation Failure",
                        "Dimension mismatch or scrolling error detected!",
                        lambda: setattr(self, "modal", None),
                        lambda: setattr(self, "modal", None)
                    )
            except Exception as e:
                print(f"Error reading simulation report: {e}")
        else:
            print("[WARN] No simulation_report.json was produced.")

    def delete_event(self, idx: int):
        ev = self.pending[idx]
        def _do():
            if ev["type"] == "npc" and ev["params"].get("npc_type") == "generic":
                sd = ev["params"].get("sprite_dir","")
                if sd: self.reg_del.add(_npc_key(sd))
            elif ev["type"] == "boss":
                sd = ev["params"].get("sprite_dir","")
                self.reg_del.add(_registry_key("boss", "", sd))
            self.pending.pop(idx)
            self.pending.sort(key=lambda e: e["distance"])
            self.modal = None
        self.modal = ModalDialog(
            "Delete Event?",
            f"Remove event #{ev['id']} at {ev['distance']}m + its registry entry?",
            _do, lambda: setattr(self,"modal",None))

    def run(self):
        while self.running:
            dt = self.clock.tick(60) / 1000.0
            self._update(dt)
            self._handle()
            self._draw()
        pg.quit()

    def _update(self, dt: float):
        self.prev_timer += dt
        if self.prev_timer >= 0.15:
            self.prev_timer = 0.0
            self.prev_idx  += 1
        if self.stage == 3 and self.s3_type in ("npc", "boss"):
            if self.s3_type == "npc":
                nt  = self.s3_ui.get("npc_type","generic")
                tgt = ("assets/graphics/Wizard_NPC" if nt == "wizard"
                       else self.browser.selected or "")
            else:
                tgt = self.browser.selected or ""
                if tgt and os.path.isdir(tgt):
                    pngs = [f for f in os.listdir(tgt) if f.lower().endswith(".png")]
                    if not pngs:
                        subs = sorted([d for d in os.listdir(tgt) if os.path.isdir(os.path.join(tgt, d))])
                        for sub in subs:
                            subpath = os.path.join(tgt, sub)
                            if any(f.lower().endswith(".png") for f in os.listdir(subpath)):
                                tgt = subpath
                                break
            if tgt and tgt != self.prev_dir:
                self.prev_frames = _load_preview(tgt)
                self.prev_dir    = tgt

    def _handle(self):
        for ev in pg.event.get():
            if ev.type == pg.QUIT: self.running = False; return
            if ev.type == pg.VIDEORESIZE:
                global W, H
                W, H = ev.w, ev.h
                self.surf = pg.display.set_mode((W, H), pg.RESIZABLE)
                continue
            if ev.type == pg.KEYDOWN:
                if ev.key == pg.K_F11:
                    self._toggle_fullscreen()
                    continue
                elif ev.key == pg.K_TAB and self.stage == 5:
                    self._toggle_panels()
                    continue
            if self.modal:
                self.modal.on(ev)
                continue
            if self._topback: self._topback.on(ev)
            if ev.type == pg.KEYDOWN and ev.key == pg.K_ESCAPE:
                {1: self.running.__class__, 2: self.go1, 3: self.go2}.get(self.stage, self.go2)()
                if self.stage == 1: self.running = False; return
            if self.stage == 1: self._h1(ev)
            elif self.stage == 2: self._h2(ev)
            elif self.stage == 3: self._h3(ev)
            elif self.stage == 5: self._h5(ev)

    def _h1(self, ev: pg.event.Event):
        if self.new_level_mode:
            if self.new_level_title_input:
                self.new_level_title_input.on(ev)
            if self.new_level_filename_input:
                self.new_level_filename_input.on(ev)
        for b in self._s1b: b.on(ev)


    def _h2(self, ev: pg.event.Event):
        for b in self._s2b: b.on(ev)
        if ev.type == pg.MOUSEWHEEL: self.ev_scroll -= ev.y * 36

    def _h3(self, ev: pg.event.Event):
        for v in self.s3_ui.values():
            if hasattr(v, "on"): v.on(ev)
        if self.s3_type in ("npc", "boss"):
            before = self.browser.selected
            self.browser.on(ev)
            after = self.browser.selected
            if after != before:
                self.prev_frames = []
                self.prev_dir = ""
                if self.s3_type == "npc":
                    if after and "scale" in self.s3_ui:
                        nt = self.s3_ui.get("npc_type", "generic")
                        self.s3_ui["scale"].val = _scale_from_registry("npc", nt, after, self.s3_ui["scale"].val)
                elif self.s3_type == "boss":
                    self.bmap.load(after)
                    if after and "scale" in self.s3_ui:
                        self.s3_ui["scale"].val = _scale_from_registry("boss", "", after, self.s3_ui["scale"].val)
            if self.s3_type == "boss":
                self.bmap.on(ev)
        for b in self._s3b: b.on(ev)

    def _draw(self):
        self.surf.fill(BG)
        self._topbar()
        if self.stage == 1:   self._d1()
        elif self.stage == 2: self._d2()
        elif self.stage == 3: self._d3()
        elif self.stage == 5: self._d5()
        if self.modal: self.modal.draw(self.surf, self.tf, self.f)
        pg.display.flip()

    def _topbar(self):
        pg.draw.rect(self.surf, PANEL, pg.Rect(0,0,W,TOPBAR_H))
        pg.draw.line(self.surf, BORDER, (0,TOPBAR_H),(W,TOPBAR_H), 2)
        title = f"Level Spawner Editor   ·   Stage {self.stage}: {STAGE_NAMES.get(self.stage,'')}"
        t = self.tf.render(title, True, TXT)
        self.surf.blit(t, t.get_rect(centerx=W//2, y=16))
        for i in range(1,4):
            col = WARN if i == self.stage else (SUCCESS if i < self.stage else BORDER)
            pg.draw.circle(self.surf, col, (W-120+(i-1)*28, 29), 7)
        if self.stage > 1:
            bk = Button("← Back", 14, 10, 88, 36,
                        {2: self.go1, 3: self.go2, 5: self.go2}.get(self.stage, self.go1), "ghost")
            bk.draw(self.surf, self.f)
            self._topback = bk
        else:
            self._topback = None

    def _d1(self):
        self._s1b = []
        if self.new_level_mode:
            hdr = self.tf.render("Create New Level", True, TXT)
            self.surf.blit(hdr, hdr.get_rect(centerx=W//2, y=CONTENT_Y+28))

            if self.new_level_title_input:
                self.new_level_title_input.draw(self.surf, self.f, self.tf)
            if self.new_level_filename_input:
                self.new_level_filename_input.draw(self.surf, self.f, self.tf)

            def _cancel():
                self.new_level_mode = False

            def _confirm():
                title = self.new_level_title_input.val.strip() if self.new_level_title_input else ""
                filename = self.new_level_filename_input.val.strip() if self.new_level_filename_input else ""

                if not title:
                    self.modal = ModalDialog("Error", "Level title cannot be empty.", lambda: setattr(self, "modal", None))
                    return
                if not filename:
                    self.modal = ModalDialog("Error", "Filename cannot be empty.", lambda: setattr(self, "modal", None))
                    return

                if not filename.endswith(".json"):
                    filename += ".json"
                if not (filename.startswith("level_") or filename.startswith("prologue_")):
                    filename = "level_" + filename
                
                path = os.path.join("game_data", filename)
                if os.path.exists(path):
                    self.modal = ModalDialog("Error", f"File '{filename}' already exists.", lambda: setattr(self, "modal", None))
                    return

                try:
                    new_data = {
                        "level_name": title,
                        "level_end_distance": 8000,
                        "world_events": [],
                        "entities": []
                    }
                    os.makedirs("game_data", exist_ok=True)
                    with open(path, "w") as fh:
                        json.dump(new_data, fh, indent=4)
                    self.scan()
                    self.new_level_mode = False
                except Exception as e:
                    self.modal = ModalDialog("Error", f"Failed to create file: {str(e)}", lambda: setattr(self, "modal", None))

            btn_conf = Button("CREATE", W//2 - 210, CONTENT_Y + 280, 200, 42, _confirm, "success")
            btn_canc = Button("CANCEL", W//2 + 10, CONTENT_Y + 280, 200, 42, _cancel, "danger")
            btn_conf.draw(self.surf, self.f)
            btn_canc.draw(self.surf, self.f)
            self._s1b += [btn_conf, btn_canc]
            return

        hdr = self.tf.render("Select a Level to Edit", True, TXT)
        self.surf.blit(hdr, hdr.get_rect(centerx=W//2, y=CONTENT_Y+28))

        def _start_new():
            self.new_level_title_input = TextInput("Level Title", W//2-200, CONTENT_Y+120, 400, 36, placeholder="e.g. Level 2 - Forest Run")
            self.new_level_filename_input = TextInput("Filename (saved under game_data/)", W//2-200, CONTENT_Y+200, 400, 36, placeholder="e.g. level_2.json")
            self.new_level_mode = True

        create_btn = Button("+ CREATE NEW", W//2 + 180, CONTENT_Y + 20, 170, 38, _start_new, "success")
        create_btn.draw(self.surf, self.f)
        self._s1b.append(create_btn)

        for i, path in enumerate(self.level_files):
            try:
                with open(path,"r") as fh:
                    fcntl.flock(fh, fcntl.LOCK_SH); d = json.load(fh)
                valid = True
                nm = d.get("level_name", os.path.basename(path))
                ln = d.get("level_end_distance","?")
                ec = len(d.get("world_events",[]))
            except Exception:
                valid = False
                nm, ln, ec = os.path.basename(path), "?", "?"
            cy   = CONTENT_Y + 100 + i*105
            card = pg.Rect(W//2-350, cy, 700, 88)
            pg.draw.rect(self.surf, PANEL, card, border_radius=10)
            pg.draw.rect(self.surf, BORDER, card, width=1, border_radius=10)
            self.surf.blit(self.tf.render(nm, True, TXT), (card.x+18, cy+12))
            status = "✔ Valid" if valid else "✖ Invalid"
            nm_w = self.tf.size(nm)[0]
            self.surf.blit(self.sf.render(status, True, SUCCESS if valid else DANGER),
                           (card.x+18 + nm_w + 12, cy+18))
            self.surf.blit(self.f.render(f"Length: {ln}m  ·  {ec} events", True, TXT2),
                           (card.x+18, cy+50))
            def _go(idx=i): self.load(idx); self.go2()
            def _del(idx=i):
                p = self.level_files[idx]
                def _do():
                    try: os.remove(p)
                    except Exception: pass
                    try:
                        dp = os.path.join("game_data", ".level_default.json")
                        if os.path.exists(dp):
                            with open(dp, "r") as f:
                                cfg = json.load(f)
                            if cfg.get("last_level") == p:
                                cfg.pop("last_level", None)
                                with open(dp, "w") as f:
                                    json.dump(cfg, f)
                    except Exception:
                        pass
                    self.scan()
                    self.modal = None
                self.modal = ModalDialog(
                    "Delete Level?",
                    f"Permanently delete file '{os.path.basename(p)}'?",
                    _do, lambda: setattr(self,"modal",None))
            def _set_next(idx=i):
                others = [(os.path.basename(p), p) for j, p in enumerate(self.level_files) if j != idx]
                target_path = self.level_files[idx]
                try:
                    with open(target_path, "r") as fh:
                        fcntl.flock(fh, fcntl.LOCK_SH); d = json.load(fh)
                    cur = d.get("next_level", "")
                    cur_name = os.path.basename(cur) if cur else "—"
                except Exception:
                    cur_name = "—"
                choices = ["(none)", "Clear"] + [name for name, _ in others]

                def _apply(choice_idx):
                    try:
                        with open(target_path, "r") as fh:
                            fcntl.flock(fh, fcntl.LOCK_SH); d = json.load(fh)
                        if choice_idx == 0 or choice_idx == 1:
                            d.pop("next_level", None)
                        else:
                            target = others[choice_idx - 2][1]
                            d["next_level"] = os.path.relpath(target, os.path.dirname(target_path))
                        with open(target_path, "w") as fh:
                            fcntl.flock(fh, fcntl.LOCK_EX)
                            json.dump(d, fh, indent=4)
                    except Exception:
                        pass
                label = f"Choose the level that follows '{os.path.basename(target_path)}'"
                self.modal = ModalDialog(
                    "Set level order",
                    label,
                    confirm_cb=lambda: (setattr(self, "modal", None), self.go1()),
                    cancel_cb=lambda: setattr(self, "modal", None),
                    choices=choices,
                    choice_cb=_apply,
                )
            btn = Button("SELECT  →", card.right-270, cy+24, 110, 40, _go, "primary")
            dlb = Button("✕", card.right-50, cy+24, 36, 40, _del, "danger")
            nxt = Button("NEXT »", card.right-150, cy+24, 90, 40, _set_next, "ghost")
            btn.draw(self.surf, self.f); dlb.draw(self.surf, self.f); nxt.draw(self.surf, self.f)
            self._s1b += [btn, dlb, nxt]



    def _d2(self):
        self._s2b = []
        lw = 830
        pg.draw.rect(self.surf, PANEL, pg.Rect(0, CONTENT_Y, lw, H-CONTENT_Y))
        pg.draw.line(self.surf, BORDER, (lw,CONTENT_Y),(lw,H), 2)
        nm  = self.level_data.get("level_name","Level")
        self.surf.blit(self.tf.render(nm, True, WARN), (14, CONTENT_Y+10))
        self.surf.blit(self.f.render(
            f"{len(self.pending)} events  ·  {len(self.reg_del)} pending deletions  ·  "
            f"{self.level_data.get('level_end_distance','?')}m", True, TXT2),
            (14, CONTENT_Y+40))

        ROW   = 48
        ly0   = CONTENT_Y + 72
        lh    = H - ly0 - BTMBAR_H
        maxsc = max(0, len(self.pending)*ROW - lh)
        self.ev_scroll = max(0, min(self.ev_scroll, maxsc))
        self.surf.set_clip(pg.Rect(0, ly0, lw, lh))
        TC = {"npc": ACCENT, "interaction": (155,89,182), "boss": WARN}
        for i, ev in enumerate(self.pending):
            ry  = ly0 + i*ROW - self.ev_scroll
            row = pg.Rect(6, ry, lw-12, ROW-4)
            if not (ly0-ROW < ry < ly0+lh): continue
            pg.draw.rect(self.surf, PANEL2, row, border_radius=6)
            pg.draw.rect(self.surf, BORDER, row, width=1, border_radius=6)
            tc  = TC.get(ev["type"], TXT2)
            tb  = self.sf.render(ev["type"].upper(), True, tc)
            self.surf.blit(tb, (row.x+8, ry+(ROW-4-tb.get_height())//2))
            lbl = (ev["params"].get("title") or
                   f"{ev['params'].get('count','?')}× {ev['params'].get('type','bat')}")
            self.surf.blit(self.f.render(f"{ev['distance']}m  —  {lbl}", True, TXT),
                           (row.x+115, ry+(ROW-4-self.f.size(lbl)[1])//2))
            def _ed(idx=i): self.go3("edit", self.pending[idx]["type"], idx)
            def _dl(idx=i): self.delete_event(idx)
            eb = Button("EDIT", row.right-148, ry+8, 60, 30, _ed, "ghost")
            db = Button("✕",    row.right-78,  ry+8, 34, 30, _dl, "danger")
            eb.draw(self.surf, self.sf); db.draw(self.surf, self.sf)
            self._s2b += [eb, db]
        self.surf.set_clip(None)

        rx = lw + 16
        self.surf.blit(self.tf.render("Add Event", True, TXT), (rx, CONTENT_Y+10))
        adds = [
            Button("＋ NPC",                  rx, CONTENT_Y+55,  420, 50, lambda: self.go3("create","npc"),         "primary"),
            Button("＋ Interaction",           rx, CONTENT_Y+118, 420, 50, lambda: self.go3("create","interaction"),"ghost"),
            Button("＋ Boss Fight",            rx, CONTENT_Y+181, 420, 50, lambda: self.go3("create","boss"),       "warn"),
            Button("🎨 Visual Canvas Studio",  rx, CONTENT_Y+248, 420, 52, self.go5,                            "primary"),
        ]
        for b in adds: b.draw(self.surf, self.f)

        def _save():
            self.modal = ModalDialog(
                "Commit Changes?",
                f"Write  '{os.path.basename(self.level_files[self.active_idx])}'  to disk?",
                self.commit, lambda: setattr(self,"modal",None))
        rst = Button("↩  Reset",       rx,     H-BTMBAR_H+8, 200, 42, self.rollback, "ghost")
        sav = Button("Save Level  ✓",  rx+215, H-BTMBAR_H+8, 205, 42, _save, "success")
        rst.draw(self.surf, self.f); sav.draw(self.surf, self.f)
        self._s2b += adds + [rst, sav]

    def _d3(self):
        self._s3b = []
        TYPE_LBL = {"npc":"NPC Event","interaction":"Interaction","boss":"Boss Fight"}
        mode_str = "Create" if self.s3_mode == "create" else "Edit"
        self.surf.blit(self.tf.render(f"{mode_str}  ·  {TYPE_LBL.get(self.s3_type,'')}", True, WARN),
                       (14, CONTENT_Y+6))

        if self.s3_type == "npc":
            self.browser.draw(self.surf, self.f, self.sf)
            nt = self.s3_ui.get("npc_type","generic")
            def _tgl():
                new_nt = "wizard" if self.s3_ui.get("npc_type", "generic") == "generic" else "generic"
                self.s3_ui["npc_type"] = new_nt
                sprite_dir = "" if new_nt == "wizard" else (self.browser.selected or "")
                if "scale" in self.s3_ui:
                    self.s3_ui["scale"].val = _scale_from_registry("npc", new_nt, sprite_dir, self.s3_ui["scale"].val)
                self.prev_frames = []; self.prev_dir = ""
            tb = Button(f"Type: {nt.capitalize()}  (toggle)", 472, CONTENT_Y+10, 240, 32, _tgl, "ghost")
            tb.draw(self.surf, self.sf)
            self._s3b.append(tb)
            if nt == "generic":
                sel = self.browser.selected or "—  select folder on left"
                st  = self.sf.render(f"Sprite Folder:  {sel}", True, WARN if self.browser.selected else TXT3)
                self.surf.blit(st, (724, CONTENT_Y+17))
            for v in self.s3_ui.values():
                if hasattr(v,"draw"): v.draw(self.surf, self.f, self.sf)
            sprite_dir = "" if nt == "wizard" else (self.browser.selected or "")
            key = _registry_key("npc", nt, sprite_dir)
            registry_scale = None
            if key:
                try:
                    registry_scale = HitboxRegistry.get_margins(key).scale
                except Exception:
                    pass
            if registry_scale is not None:
                current_val = float(self.s3_ui["scale"].val)
                comp_y = self.s3_ui["scale"].track.y + 16
                comp_text = f"JSON config scale: {current_val:.2f}  |  Registry scale: {registry_scale:.2f}"
                color = SUCCESS if abs(current_val - registry_scale) < 0.01 else WARN
                self.surf.blit(self.sf.render(comp_text, True, color), (self.s3_ui["scale"].track.x, comp_y))
            pbox = pg.Rect(472, CONTENT_Y+458, 782, 142)
            pg.draw.rect(self.surf, PANEL2, pbox, border_radius=8)
            pg.draw.rect(self.surf, BORDER, pbox, width=1, border_radius=8)
            self.surf.blit(self.sf.render("Live Preview", True, TXT2), (pbox.x+8, pbox.y+6))
            if self.prev_frames:
                fr = self.prev_frames[self.prev_idx % len(self.prev_frames)]
                self.surf.blit(fr, fr.get_rect(center=pbox.center))
            else:
                ph = self.sf.render("No preview — select a sprite folder", True, TXT3)
                self.surf.blit(ph, ph.get_rect(center=pbox.center))
        elif self.s3_type == "boss":
            self.browser.draw(self.surf, self.f, self.sf)
            tier = self.s3_ui.get("tier", "boss")
            def _tgl_tier():
                new_tier = "elite" if self.s3_ui.get("tier", "boss") == "boss" else "boss"
                self.s3_ui["tier"] = new_tier
            tb = Button(f"Tier: {tier.upper()}  (toggle)", 462, CONTENT_Y+390, 380, 32, _tgl_tier, "ghost")
            tb.draw(self.surf, self.sf)
            self._s3b.append(tb)

            sel = self.browser.selected or "—  default skeleton assets"
            st  = self.sf.render(f"Sprite Folder:  {sel}", True, WARN if self.browser.selected else TXT3)
            self.surf.blit(st, (462, CONTENT_Y+12))

            for k, v in self.s3_ui.items():
                if k != "tier" and hasattr(v, "draw"):
                    v.draw(self.surf, self.f, self.sf)

            sprite_dir = self.browser.selected or ""
            key = _registry_key("boss", "", sprite_dir)
            registry_scale = None
            if key:
                try:
                    registry_scale = HitboxRegistry.get_margins(key).scale
                except Exception:
                    pass
            if registry_scale is not None:
                current_val = float(self.s3_ui["scale"].val)
                comp_y = self.s3_ui["scale"].track.y + 16
                comp_text = f"JSON scale: {current_val:.2f}  |  Registry: {registry_scale:.2f}"
                color = SUCCESS if abs(current_val - registry_scale) < 0.01 else WARN
                self.surf.blit(self.sf.render(comp_text, True, color), (self.s3_ui["scale"].track.x, comp_y))

            # Live Preview box at bottom of middle column
            pbox = pg.Rect(462, CONTENT_Y+435, 380, 150)
            pg.draw.rect(self.surf, PANEL2, pbox, border_radius=8)
            pg.draw.rect(self.surf, BORDER, pbox, width=1, border_radius=8)
            self.surf.blit(self.sf.render("Live Preview", True, TXT2), (pbox.x+8, pbox.y+6))
            if self.prev_frames:
                fr = self.prev_frames[self.prev_idx % len(self.prev_frames)]
                self.surf.blit(fr, fr.get_rect(center=pbox.center))
            else:
                ph = self.sf.render("No preview — select a sprite folder", True, TXT3)
                self.surf.blit(ph, ph.get_rect(center=pbox.center))

            self.bmap.draw(self.surf, self.f, self.sf)
        else:
            for v in self.s3_ui.values():
                if hasattr(v,"draw"): v.draw(self.surf, self.f, self.sf)

        ready = not (self.s3_type == "npc" and
                     self.s3_ui.get("npc_type") == "generic" and
                     not self.browser.selected)
        lbl = "Add to Level  ✓" if self.s3_mode == "create" else "Save Changes  ✓"
        sub = Button(lbl,       W-468, H-BTMBAR_H+8, 248, 42,
                     self.submit_s3 if ready else lambda: None,
                     "success" if ready else "ghost")
        cnl = Button("← Cancel", W-210, H-BTMBAR_H+8, 110, 42, self.go2, "ghost")
        sim = Button("Simulate  ▶", W-690, H-BTMBAR_H+8, 210, 42,
                     self.simulate_s3 if ready else lambda: None,
                     "primary" if ready else "ghost")
        sub.enabled = ready
        sim.enabled = ready
        sub.draw(self.surf, self.f); cnl.draw(self.surf, self.f); sim.draw(self.surf, self.f)
        self._s3b += [sub, cnl, sim]


if __name__ == "__main__":
    App().run()
