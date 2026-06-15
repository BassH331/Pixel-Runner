"""
Level Spawner Editor v2  —  Wizard-Style Plugin
Run from the Pixel-Runner project root: python level_editor.py

Stage flow:
  1  Level Select   — pick level_*.json
  2  Event List     — view / delete events, choose what to add
  3  Event Builder  — step-by-step event configuration + folder browser
  4  Review & Commit— diff view + transactional flock write with rollback
"""

import os, sys, json, fcntl, copy
from typing import Optional
import pygame as pg

sys.path.insert(0, os.path.dirname(__file__))
from src.game.entities.hitbox_registry import HitboxRegistry, HitboxMargins

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
               3: "Event Builder", 4: "Review & Commit"}


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
    def __init__(self, title: str, body: str, confirm_cb, cancel_cb=None):
        self.title, self.body = title, body
        self.confirm_cb, self.cancel_cb = confirm_cb, cancel_cb

    def draw(self, surf: pg.Surface, tf: pg.font.Font, f: pg.font.Font):
        overlay = pg.Surface((W, H), pg.SRCALPHA)
        overlay.fill((8, 8, 15, 210))
        surf.blit(overlay, (0, 0))

        dw, dh = 540, 230
        dx, dy = (W - dw) // 2, (H - dh) // 2
        dr = pg.Rect(dx, dy, dw, dh)
        pg.draw.rect(surf, PANEL, dr, border_radius=14)
        pg.draw.rect(surf, WARN,  dr, width=3,  border_radius=14)

        surf.blit(tf.render(self.title, True, WARN),
                  tf.render(self.title, True, WARN).get_rect(centerx=dr.centerx, y=dy+28))
        surf.blit(f.render(self.body, True, TXT),
                  f.render(self.body, True, TXT).get_rect(centerx=dr.centerx, y=dy+88))

        m = pg.mouse.get_pos()
        for rect, label, col, hov in [
            (pg.Rect(dx+40,  dy+155, 200, 42), "CONFIRM", SUCCESS, SUCC_H),
            (pg.Rect(dx+300, dy+155, 200, 42), "CANCEL",  DANGER,  DANGH),
        ]:
            c = hov if rect.collidepoint(m) else col
            pg.draw.rect(surf, c, rect, border_radius=8)
            t = f.render(label, True, TXT)
            surf.blit(t, t.get_rect(center=rect.center))

    def on(self, event: pg.event.Event):
        if event.type != pg.MOUSEBUTTONDOWN or event.button != 1: return
        dw, dh = 540, 230
        dx, dy = (W - dw) // 2, (H - dh) // 2
        if pg.Rect(dx+40, dy+155, 200, 42).collidepoint(event.pos):
            self.confirm_cb()
        elif pg.Rect(dx+300, dy+155, 200, 42).collidepoint(event.pos):
            if self.cancel_cb: self.cancel_cb()
        elif event.type == pg.KEYDOWN:
            if event.key in (pg.K_RETURN, pg.K_y): self.confirm_cb()
            elif event.key in (pg.K_ESCAPE, pg.K_n):
                if self.cancel_cb: self.cancel_cb()


# ── Helpers ────────────────────────────────────────────────────────────────
def _npc_key(d: str) -> str:
    n = os.path.basename(d.rstrip("/"))
    if n.lower() == "idle":
        n = os.path.basename(os.path.dirname(d.rstrip("/")))
    return f"generic_npc_{n.lower()}"

def _load_preview(path: str, scale: float = 2.0) -> list[pg.Surface]:
    frames: list[pg.Surface] = []
    if not os.path.exists(path): return frames
    for fn in sorted(f for f in os.listdir(path) if f.lower().endswith(".png")):
        img = pg.image.load(os.path.join(path, fn)).convert_alpha()
        w, h = img.get_size()
        frames.append(pg.transform.scale(img, (int(w*scale), int(h*scale))))
    return frames


class App:
    def __init__(self):
        pg.init()
        pg.display.set_caption("Level Spawner Editor  v2")
        self.surf  = pg.display.set_mode((W, H))
        self.clock = pg.time.Clock()
        self.running = True
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
        self.ev_scroll  = 0
        self.browser    = FolderBrowser("assets/graphics",
                                         pg.Rect(12, CONTENT_Y+34, 438, CONTENT_H-50))
        self._topback: Optional[Button] = None
        self._s1b: list[Button] = []
        self._s2b: list[Button] = []
        self._s3b: list[Button] = []
        self.scan()

    def scan(self):
        gd = "game_data"
        self.level_files = sorted(
            os.path.join(gd, f) for f in os.listdir(gd)
            if f.startswith("level_") and f.endswith(".json")
        ) if os.path.isdir(gd) else []

    def load(self, idx: int):
        self.active_idx = idx
        with open(self.level_files[idx], "r") as fh:
            fcntl.flock(fh, fcntl.LOCK_EX)
            self.level_data = json.load(fh)
        self.level_data.setdefault("world_events", [])
        self.level_backup = copy.deepcopy(self.level_data)
        self.pending = copy.deepcopy(self.level_data["world_events"])
        self.reg_del = set()
        HitboxRegistry.begin_transaction()

    def commit(self):
        for k in self.reg_del:
            HitboxRegistry._cached_config.pop(k, None)
        self.level_data["world_events"] = sorted(self.pending, key=lambda e: e["distance"])
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
        self.reg_del = set()
        HitboxRegistry.rollback_transaction()
        self.modal = None

    def go1(self): self.stage = 1; self.scan()
    def go2(self): self.stage = 2; self.ev_scroll = 0; self.modal = None

    def go3(self, mode: str, etype: str, idx: int = -1):
        self.stage, self.s3_mode, self.s3_type, self.s3_idx = 3, mode, etype, idx
        self._init_s3(etype, idx)

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
            if nt == "wizard":
                npc_key = "wizard_npc"
            else:
                sprite_dir = p.get("sprite_dir") or ""
                folder_name = os.path.basename(sprite_dir.rstrip("/"))
                if folder_name.lower() == "idle":
                    parent_dir = os.path.dirname(sprite_dir.rstrip("/"))
                    folder_name = os.path.basename(parent_dir)
                npc_key = f"generic_npc_{folder_name.lower()}"
            from src.game.entities.hitbox_registry import HitboxRegistry
            margins = HitboxRegistry.get_margins(npc_key)
            default_scale = margins.scale

            self.s3_ui = {
                "npc_type": nt,
                "title":  TextInput("NPC Title", 472, CONTENT_Y+48,  782, initial=p.get("title","New NPC")),
                "text":   TextInput("Dialogue",  472, CONTENT_Y+132, 782, initial=p.get("text","...")),
                "radius": Slider("Proximity Radius", 472, CONTENT_Y+218, 782, 50, 400, float(p.get("radius",160))),
                "dist":   Slider("Trigger Distance", 472, CONTENT_Y+308, 782, 0, end, dist),
                "scale":  Slider("Scale", 472, CONTENT_Y+388, 782, 0.5, 6.0, float(p.get("scale", default_scale)), True),
            }
            self.browser.selected = p.get("sprite_dir") or None
        elif etype == "enemy_wave":
            self.s3_ui = {
                "count": Slider("Enemy Count",      160, CONTENT_Y+120, 940, 1, 15, float(p.get("count",3))),
                "dist":  Slider("Trigger Distance", 160, CONTENT_Y+220, 940, 0, end, dist),
            }
        else:
            self.s3_ui = {
                "title":  TextInput("Title",    160, CONTENT_Y+90,  940, initial=p.get("title","Sign")),
                "text":   TextInput("Dialogue", 160, CONTENT_Y+180, 940, initial=p.get("text","...")),
                "radius": Slider("Proximity Radius", 160, CONTENT_Y+280, 940, 50, 400, float(p.get("radius",160))),
                "dist":   Slider("Trigger Distance", 160, CONTENT_Y+370, 940, 0, end, dist),
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
                       "text": ui["text"].val, "radius": int(ui["radius"].val),
                       "scale": float(ui["scale"].val)}
            if nt == "generic":
                p["sprite_dir"] = self.browser.selected or ""
        elif t == "enemy_wave":
            p = {"count": int(ui["count"].val), "type": "bat"}
        else:
            p = {"title": ui["title"].val, "text": ui["text"].val,
                 "radius": int(ui["radius"].val)}
        return {"id": eid, "distance": dist, "type": t, "params": p}

    def submit_s3(self):
        ev = self._read_s3()
        if self.s3_mode == "create": self.pending.append(ev)
        else: self.pending[self.s3_idx] = ev
        self.go2()

    def delete_event(self, idx: int):
        ev = self.pending[idx]
        def _do():
            if ev["type"] == "npc" and ev["params"].get("npc_type") == "generic":
                sd = ev["params"].get("sprite_dir","")
                if sd: self.reg_del.add(_npc_key(sd))
            self.pending.pop(idx)
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
        if self.stage == 3 and self.s3_type == "npc":
            nt  = self.s3_ui.get("npc_type","generic")
            tgt = ("assets/graphics/Wizard_NPC" if nt == "wizard"
                   else self.browser.selected or "")
            if tgt and tgt != self.prev_dir:
                self.prev_frames = _load_preview(tgt)
                self.prev_dir    = tgt

    def _handle(self):
        for ev in pg.event.get():
            if ev.type == pg.QUIT: self.running = False; return
            if self.modal:
                self.modal.on(ev)
                if ev.type == pg.KEYDOWN:
                    if ev.key in (pg.K_RETURN, pg.K_y):   self.modal.confirm_cb()
                    elif ev.key in (pg.K_ESCAPE, pg.K_n):
                        if self.modal.cancel_cb: self.modal.cancel_cb()
                continue
            if ev.type == pg.KEYDOWN and ev.key == pg.K_ESCAPE:
                {1: self.running.__class__, 2: self.go1, 3: self.go2}.get(self.stage, self.go2)()
                if self.stage == 1: self.running = False; return
            if self.stage == 1: self._h1(ev)
            elif self.stage == 2: self._h2(ev)
            elif self.stage == 3: self._h3(ev)

    def _h1(self, ev: pg.event.Event):
        for b in self._s1b: b.on(ev)

    def _h2(self, ev: pg.event.Event):
        for b in self._s2b: b.on(ev)
        if ev.type == pg.MOUSEWHEEL: self.ev_scroll -= ev.y * 36

    def _h3(self, ev: pg.event.Event):
        for v in self.s3_ui.values():
            if hasattr(v, "on"): v.on(ev)
        if self.s3_type == "npc":
            self.browser.on(ev)
            if ev.type == pg.MOUSEBUTTONDOWN: self.prev_frames = []
        for b in self._s3b: b.on(ev)

    def _draw(self):
        self.surf.fill(BG)
        self._topbar()
        if self.stage == 1:   self._d1()
        elif self.stage == 2: self._d2()
        elif self.stage == 3: self._d3()
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
                        {2: self.go1, 3: self.go2}.get(self.stage, self.go1), "ghost")
            bk.draw(self.surf, self.f)
            self._topback = bk
        else:
            self._topback = None

    def _d1(self):
        self._s1b = []
        hdr = self.tf.render("Select a Level to Edit", True, TXT)
        self.surf.blit(hdr, hdr.get_rect(centerx=W//2, y=CONTENT_Y+28))
        for i, path in enumerate(self.level_files):
            try:
                with open(path,"r") as fh:
                    fcntl.flock(fh, fcntl.LOCK_SH); d = json.load(fh)
                nm = d.get("level_name", os.path.basename(path))
                ln = d.get("level_end_distance","?")
                ec = len(d.get("world_events",[]))
            except Exception:
                nm, ln, ec = os.path.basename(path), "?", "?"
            cy   = CONTENT_Y + 100 + i*105
            card = pg.Rect(W//2-350, cy, 700, 88)
            pg.draw.rect(self.surf, PANEL, card, border_radius=10)
            pg.draw.rect(self.surf, BORDER, card, width=1, border_radius=10)
            self.surf.blit(self.tf.render(nm, True, TXT), (card.x+18, cy+12))
            self.surf.blit(self.f.render(f"Length: {ln}m  ·  {ec} events", True, TXT2),
                           (card.x+18, cy+50))
            def _go(idx=i): self.load(idx); self.go2()
            btn = Button("SELECT  →", card.right-155, cy+20, 130, 46, _go, "primary")
            btn.draw(self.surf, self.f)
            self._s1b.append(btn)

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
        TC = {"npc": ACCENT, "enemy_wave": DANGER, "interaction": (155,89,182)}
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
                   f"{ev['params'].get('count','?')}× bat")
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
            Button("＋ NPC",          rx, CONTENT_Y+55,  420, 50, lambda: self.go3("create","npc"),         "primary"),
            Button("＋ Enemy Wave",    rx, CONTENT_Y+118, 420, 50, lambda: self.go3("create","enemy_wave"), "danger"),
            Button("＋ Interaction",   rx, CONTENT_Y+181, 420, 50, lambda: self.go3("create","interaction"),"ghost"),
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
        TYPE_LBL = {"npc":"NPC Event","enemy_wave":"Enemy Wave","interaction":"Interaction"}
        mode_str = "Create" if self.s3_mode == "create" else "Edit"
        self.surf.blit(self.tf.render(f"{mode_str}  ·  {TYPE_LBL.get(self.s3_type,'')}", True, WARN),
                       (14, CONTENT_Y+10))

        if self.s3_type == "npc":
            self.browser.draw(self.surf, self.f, self.sf)
            nt = self.s3_ui.get("npc_type","generic")
            def _tgl():
                self.s3_ui["npc_type"] = "wizard" if nt=="generic" else "generic"
                self.prev_frames = []; self.prev_dir = ""
            tb = Button(f"Type: {nt.capitalize()}  (toggle)", 472, CONTENT_Y+10, 380, 32, _tgl, "ghost")
            tb.draw(self.surf, self.sf)
            self._s3b.append(tb)
            if nt == "generic":
                sel = self.browser.selected or "—  select folder on left"
                st  = self.sf.render(f"Sprite Folder:  {sel}", True, WARN if self.browser.selected else TXT3)
                self.surf.blit(st, (472, CONTENT_Y+47))
            for v in self.s3_ui.values():
                if hasattr(v,"draw"): v.draw(self.surf, self.f, self.sf)
            pbox = pg.Rect(472, CONTENT_Y+460, 782, 160)
            pg.draw.rect(self.surf, PANEL2, pbox, border_radius=8)
            pg.draw.rect(self.surf, BORDER, pbox, width=1, border_radius=8)
            self.surf.blit(self.sf.render("Live Preview", True, TXT2), (pbox.x+8, pbox.y+6))
            if self.prev_frames:
                fr = self.prev_frames[self.prev_idx % len(self.prev_frames)]
                self.surf.blit(fr, fr.get_rect(center=pbox.center))
            else:
                ph = self.sf.render("No preview — select a sprite folder", True, TXT3)
                self.surf.blit(ph, ph.get_rect(center=pbox.center))
        else:
            for v in self.s3_ui.values():
                if hasattr(v,"draw"): v.draw(self.surf, self.f, self.sf)

        npc_ready = not (self.s3_type == "npc" and
                         self.s3_ui.get("npc_type") == "generic" and
                         not self.browser.selected)
        lbl = "Add to Level  ✓" if self.s3_mode == "create" else "Save Changes  ✓"
        sub = Button(lbl,       W-468, H-BTMBAR_H+8, 248, 42,
                     self.submit_s3 if npc_ready else lambda: None,
                     "success" if npc_ready else "ghost")
        cnl = Button("← Cancel", W-210, H-BTMBAR_H+8, 110, 42, self.go2, "ghost")
        sub.enabled = npc_ready
        sub.draw(self.surf, self.f); cnl.draw(self.surf, self.f)
        self._s3b += [sub, cnl]


if __name__ == "__main__":
    App().run()
