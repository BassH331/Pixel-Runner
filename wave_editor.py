"""
Enemy Wave Designer v2 — Wizard-Style Plugin
Run: python wave_editor.py

Stages:
  1  Level Select       — pick level_*.json
  2  Zone Manager       — list / add / delete spawn zones
  3  Zone Builder       — configure zone + optional sprite mapping
"""
from __future__ import annotations
import os, sys, json, fcntl, copy
from typing import Optional
import pygame as pg

sys.path.insert(0, os.path.dirname(__file__))
from level_editor import (
    Button, Slider, FolderBrowser, ModalDialog,
    BG, PANEL, PANEL2, BORDER, ACCENT,
    DANGER, SUCCESS, SUCC_H, WARN,
    TXT, TXT2, TXT3,
    W, H, TOPBAR_H, BTMBAR_H, CONTENT_Y, CONTENT_H,
)

STAGE_NAMES = {1: "Select Level", 2: "Zone Manager", 3: "Zone Builder"}
TIERS = ["minion", "elite", "boss"]
BTAGS = ["idle", "walk", "chase", "attack", "hurt", "death"]
TIER_COL = {"minion": ACCENT, "elite": WARN, "boss": DANGER}


class BehaviourMapper:
    """Sub-folder → behaviour tag mapper.
    Auto-detects behaviour from folder names with keyword scoring.
    Shows auto-detected tags in green, manually overridden in orange.
    Click a tag badge to cycle it."""
    ROW_H = 34

    # Keyword → behaviour scoring (weighted for accuracy)
    _KEYWORDS: dict[str, list[str]] = {
        "idle":   ["idle", "stand", "rest", "wait", "breathe"],
        "walk":   ["walk", "move", "patrol", "wander"],
        "chase":  ["run", "chase", "sprint", "dash", "charge"],
        "attack": ["attack", "atk", "strike", "slash", "swing", "hit", "combat"],
        "hurt":   ["hurt", "damage", "pain", "hit", "flinch", "stagger"],
        "death":  ["death", "die", "dead", "fall", "collapse", "defeat"],
    }

    def __init__(self, rect: pg.Rect):
        self.rect = rect
        self.subs: list[str] = []
        self.mapping: dict[str, str] = {}
        self.auto_tags: dict[str, str] = {}  # what was auto-detected
        self.scroll = 0
        self._btns: list[tuple[pg.Rect, str]] = []

    def load(self, root: Optional[str], existing: Optional[dict[str, str]] = None):
        self.subs, self.mapping, self.auto_tags, self.scroll = [], {}, {}, 0
        if not root or not os.path.isdir(root):
            return
        try:
            self.subs = sorted(d for d in os.listdir(root)
                               if os.path.isdir(os.path.join(root, d)))
        except OSError:
            return
        for s in self.subs:
            auto = self._smart_guess(s)
            self.auto_tags[s] = auto
            self.mapping[s] = (existing or {}).get(s, auto)

    @classmethod
    def _smart_guess(cls, name: str) -> str:
        """Score folder name against keyword lists; highest score wins."""
        lo = name.lower().replace("_", " ").replace("-", " ")
        best, best_score = "idle", 0
        for tag, keywords in cls._KEYWORDS.items():
            score = sum(2 if kw in lo else 0 for kw in keywords)
            # Bonus for exact substring match at word boundary
            for kw in keywords:
                if lo.startswith(kw) or lo.endswith(kw):
                    score += 1
            if score > best_score:
                best, best_score = tag, score
        return best

    def draw(self, surf: pg.Surface, f: pg.font.Font, sf: pg.font.Font):
        # Header with match summary
        mapped = sum(1 for s in self.subs if self.mapping.get(s) != "idle"
                     or self.auto_tags.get(s) != "idle")
        total = len(self.subs)
        hdr = f"Behaviour Map  ({mapped}/{total} matched)" if total else "Behaviour Map"
        surf.blit(sf.render(hdr, True, TXT2), (self.rect.x, self.rect.y - 18))

        pg.draw.rect(surf, PANEL, self.rect, border_radius=6)
        pg.draw.rect(surf, BORDER, self.rect, width=1, border_radius=6)
        if not self.subs:
            ph = sf.render("← Select a sprite folder to auto-map", True, TXT3)
            surf.blit(ph, ph.get_rect(center=self.rect.center))
            return

        surf.set_clip(self.rect)
        th = len(self.subs) * self.ROW_H
        self.scroll = max(0, min(self.scroll, max(0, th - self.rect.h)))
        m = pg.mouse.get_pos()
        self._btns = []
        TCOL = {"idle": ACCENT, "walk": (46, 204, 113), "chase": SUCCESS,
                "attack": DANGER, "hurt": WARN, "death": (155, 89, 182)}

        for i, name in enumerate(self.subs):
            ry = self.rect.y + i * self.ROW_H - self.scroll
            if ry + self.ROW_H < self.rect.y or ry > self.rect.bottom:
                continue
            row = pg.Rect(self.rect.x+4, ry+1, self.rect.w-8, self.ROW_H-2)
            hov = row.collidepoint(m) and self.rect.collidepoint(m)
            pg.draw.rect(surf, (40,40,55) if hov else PANEL2, row, border_radius=4)

            # Folder name (truncated if needed)
            display_name = name if len(name) < 30 else name[:27] + "…"
            surf.blit(f.render(display_name, True, TXT),
                      (row.x+8, ry+(self.ROW_H-f.get_height())//2))

            # Tag badge
            tag = self.mapping.get(name, "idle")
            auto = self.auto_tags.get(name, "idle")
            is_auto = (tag == auto)
            tc = TCOL.get(tag, TXT2)
            # Show ✓ for auto-detected, ✎ for manually overridden
            prefix = "✓ " if is_auto else "✎ "
            bt = f.render(f"{prefix}{tag.upper()}", True, tc)
            bx = row.right - bt.get_width() - 8
            by = ry + (self.ROW_H - bt.get_height()) // 2
            br = pg.Rect(bx-4, by-2, bt.get_width()+8, bt.get_height()+4)
            bg = (25, 50, 35) if is_auto else (50, 40, 25)
            pg.draw.rect(surf, bg, br, border_radius=4)
            surf.blit(bt, (bx, by))
            self._btns.append((br, name))

        surf.set_clip(None)

    def on(self, ev: pg.event.Event):
        if ev.type == pg.MOUSEWHEEL and self.rect.collidepoint(pg.mouse.get_pos()):
            self.scroll -= ev.y * self.ROW_H * 2
        elif ev.type == pg.MOUSEBUTTONDOWN and ev.button == 1:
            for r, n in self._btns:
                if r.collidepoint(ev.pos):
                    cur = self.mapping.get(n, "idle")
                    ci = BTAGS.index(cur) if cur in BTAGS else 0
                    self.mapping[n] = BTAGS[(ci+1) % len(BTAGS)]
                    break


class WaveEditorApp:
    def __init__(self):
        pg.init()
        pg.display.set_caption("Enemy Wave Designer v2")
        self.surf = pg.display.set_mode((W, H))
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
        self.modal: Optional[ModalDialog] = None

        self.s3_mode = "create"
        self.s3_idx = -1
        self.s3_ui: dict = {}
        self.zscroll = 0

        self.browser = FolderBrowser("assets",
                                     pg.Rect(12, CONTENT_Y+50, 438, CONTENT_H-70),
                                     allow_parent=True)
        self.bmap = BehaviourMapper(pg.Rect(462, CONTENT_Y+345, 800, CONTENT_H-365))
        self._prev_sel: Optional[str] = None

        self._s1b: list[Button] = []
        self._s2b: list[Button] = []
        self._s3b: list[Button] = []
        self._topback: Optional[Button] = None
        self.scan()

    # I/O
    def scan(self):
        gd = "game_data"
        self.level_files = sorted(
            os.path.join(gd, f) for f in os.listdir(gd)
            if f.startswith("level_") and f.endswith(".json")
        ) if os.path.isdir(gd) else []

    def load(self, idx: int):
        self.active_idx = idx
        with open(self.level_files[idx]) as fh:
            fcntl.flock(fh, fcntl.LOCK_EX)
            self.level_data = json.load(fh)
        self.level_data.setdefault("spawn_zones", [])
        self.level_backup = copy.deepcopy(self.level_data)
        self.pending = copy.deepcopy(self.level_data["spawn_zones"])

    def commit(self):
        self.level_data["spawn_zones"] = sorted(
            self.pending, key=lambda z: z.get("min_dist", 0))
        with open(self.level_files[self.active_idx], "w") as fh:
            fcntl.flock(fh, fcntl.LOCK_EX)
            json.dump(self.level_data, fh, indent=4)
        self.level_backup = copy.deepcopy(self.level_data)
        self.modal = None

    def rollback(self):
        self.level_data = copy.deepcopy(self.level_backup)
        self.pending = copy.deepcopy(self.level_data["spawn_zones"])
        self.modal = None

    # Navigation
    def go1(self): self.stage = 1; self.scan()
    def go2(self): self.stage = 2; self.zscroll = 0; self.modal = None

    def go3(self, mode: str, idx: int = -1):
        self.stage, self.s3_mode, self.s3_idx = 3, mode, idx
        z = self.pending[idx] if idx >= 0 else {}
        _e = self.level_data.get("level_end_distance", 8000)
        end = float(_e) if isinstance(_e, (int, float)) else 8000.0
        def _f(v, d: float) -> float:
            return float(v) if isinstance(v, (int, float)) else d
        mn = _f(z.get("min_dist", 0), 0.0)
        mx = _f(z.get("max_dist", end), end)
        if mx >= 99999: mx = end
        self.s3_ui = {
            "min":   Slider("Zone Start Distance (m)", 462, CONTENT_Y+50,  800, 0, end, mn),
            "max":   Slider("Zone End Distance (m)",   462, CONTENT_Y+105, 800, 0, end, mx),
            "count": Slider("Max Concurrent Enemies",  462, CONTENT_Y+160, 800, 1, 20,
                            _f(z.get("max_skeletons",3), 3.0)),
            "delay": Slider("Spawn Delay (ms)",        462, CONTENT_Y+215, 800, 500, 10000,
                            _f(z.get("delay",4000), 4000.0)),
            "required_kills": Slider("Required Kills (0=inf)", 462, CONTENT_Y+270, 800, 0, 50,
                            _f(z.get("required_kills",0), 0.0)),
            "tier": str(z.get("tier", "minion")),
        }
        sr = z.get("sprite_root")
        self.browser.selected = sr if isinstance(sr, str) and sr else None
        self._prev_sel = self.browser.selected
        bm = z.get("behaviour_map")
        self.bmap.load(self.browser.selected,
                       bm if isinstance(bm, dict) else None)

    def _read(self) -> dict:
        ui = self.s3_ui
        if not ui or not all(k in ui for k in ("min", "max", "count", "delay", "required_kills")):
            return {}
        mn, mx = int(ui["min"].val), int(ui["max"].val)
        if mx <= mn: mx = mn + 100
        r: dict = {"min_dist": mn, "max_dist": mx,
                    "max_skeletons": int(ui["count"].val),
                    "delay": int(ui["delay"].val),
                    "required_kills": int(ui["required_kills"].val),
                    "tier": ui.get("tier", "minion")}
        if self.browser.selected:
            r["sprite_root"] = self.browser.selected
            r["behaviour_map"] = dict(self.bmap.mapping)
        return r

    def submit(self):
        z = self._read()
        if not z:
            return
        if self.s3_mode == "create": self.pending.append(z)
        else: self.pending[self.s3_idx] = z
        self.go2()

    def simulate(self):
        z = self._read()
        if not z:
            return
        temp_pending = list(self.pending)
        if self.s3_mode == "create":
            temp_pending.append(z)
        else:
            temp_pending[self.s3_idx] = z

        level_file = self.level_files[self.active_idx]
        try:
            with open(level_file, "r") as f:
                original_content = f.read()
        except Exception as e:
            print(f"Error backing up level file: {e}")
            return

        temp_data = dict(self.level_data)
        temp_data["spawn_zones"] = temp_pending
        try:
            with open(level_file, "w") as f:
                json.dump(temp_data, f, indent=4)
        except Exception as e:
            print(f"Error writing temporary simulation file: {e}")
            return

        # Start distance: max(0, min_dist - 200)
        start_dist = max(0.0, float(z["min_dist"]) - 200.0)

        import subprocess
        import sys

        self.surf.blit(self.tf.render("Launching Simulation...", True, WARN), (W//2 - 150, H//2 - 20))
        pg.display.flip()

        try:
            cmd = [sys.executable, "main.py", "--start-dist", str(start_dist), "--duration", "6.0"]
            venv_python = os.path.join(".venv", "bin", "python")
            if os.path.exists(venv_python):
                cmd[0] = venv_python
            subprocess.run(cmd, env=dict(os.environ, PYTHONPATH="."))
        except Exception as e:
            print(f"Error launching game subprocess: {e}")

        try:
            with open(level_file, "w") as f:
                f.write(original_content)
        except Exception as e:
            print(f"Error restoring original level file content: {e}")

        # Check simulation report results
        report_file = "scratch/simulation_report.json"
        if os.path.exists(report_file):
            try:
                with open(report_file, "r") as f:
                    report = json.load(f)
                if report.get("status") == "FAILED":
                    self.modal = ModalDialog(
                        "Simulation Failure",
                        "No dynamic enemies spawned during simulation!",
                        lambda: setattr(self, "modal", None),
                        lambda: setattr(self, "modal", None)
                    )
                else:
                    self.modal = ModalDialog(
                        "Simulation Passed",
                        f"Spawned {len(report.get('enemies', []))} enemies successfully!",
                        lambda: setattr(self, "modal", None),
                        lambda: setattr(self, "modal", None)
                    )
            except Exception as e:
                print(f"Error reading simulation report: {e}")
        else:
            print("[WARN] No simulation_report.json was produced.")

    def delete(self, idx: int):
        z = self.pending[idx]
        def _do(): self.pending.pop(idx); self.modal = None
        self.modal = ModalDialog(
            "Delete Zone?",
            f"Remove {z.get('min_dist',0)}m – {z.get('max_dist','?')}m?",
            _do, lambda: setattr(self, "modal", None))

    # Loop
    def run(self):
        while self.running:
            self.clock.tick(60)
            self._handle()
            self._draw()
        pg.quit()

    def _handle(self):
        for ev in pg.event.get():
            if ev.type == pg.QUIT: self.running = False; return
            if self.modal:
                self.modal.on(ev)
                if ev.type == pg.KEYDOWN:
                    if ev.key in (pg.K_RETURN, pg.K_y): self.modal.confirm_cb()
                    elif ev.key in (pg.K_ESCAPE, pg.K_n) and self.modal.cancel_cb:
                        self.modal.cancel_cb()
                continue
            if ev.type == pg.KEYDOWN and ev.key == pg.K_ESCAPE:
                if self.stage == 1: self.running = False; return
                elif self.stage == 2: self.go1()
                elif self.stage == 3: self.go2()
                continue
            # Delegate to top-back button
            if self._topback: self._topback.on(ev)
            if self.stage == 1:
                for b in self._s1b: b.on(ev)
            elif self.stage == 2:
                for b in self._s2b: b.on(ev)
                if ev.type == pg.MOUSEWHEEL: self.zscroll -= ev.y * 40
            elif self.stage == 3:
                for v in self.s3_ui.values():
                    if hasattr(v, "on"): v.on(ev)
                self.browser.on(ev)
                self.bmap.on(ev)
                for b in self._s3b: b.on(ev)
                # Auto-reload behaviour map when folder selection changes
                if self.browser.selected != self._prev_sel:
                    self.bmap.load(self.browser.selected)
                    self._prev_sel = self.browser.selected

    def _draw(self):
        self.surf.fill(BG)
        self._topbar()
        if self.stage == 1: self._d1()
        elif self.stage == 2: self._d2()
        elif self.stage == 3: self._d3()
        if self.modal: self.modal.draw(self.surf, self.tf, self.f)
        pg.display.flip()

    def _topbar(self):
        pg.draw.rect(self.surf, PANEL, pg.Rect(0,0,W,TOPBAR_H))
        pg.draw.line(self.surf, BORDER, (0,TOPBAR_H),(W,TOPBAR_H),2)
        t = self.tf.render(
            f"Enemy Wave Designer  ·  Stage {self.stage}: "
            f"{STAGE_NAMES.get(self.stage,'')}", True, TXT)
        self.surf.blit(t, t.get_rect(centerx=W//2, y=16))
        for i in range(1,4):
            c = WARN if i==self.stage else (SUCCESS if i<self.stage else BORDER)
            pg.draw.circle(self.surf, c, (W-100+(i-1)*26, 29), 7)
        if self.stage > 1:
            self._topback = Button("← Back", 14, 12, 88, 34,
                                   {2:self.go1,3:self.go2}.get(self.stage,self.go1),"ghost")
            self._topback.draw(self.surf, self.f)
        else:
            self._topback = None

    def _d1(self):
        self._s1b = []
        self.surf.blit(self.tf.render("Select a Level", True, TXT),
                       self.tf.render("Select a Level", True, TXT).get_rect(
                           centerx=W//2, y=CONTENT_Y+28))
        for i, path in enumerate(self.level_files):
            try:
                with open(path) as fh:
                    fcntl.flock(fh, fcntl.LOCK_SH); d = json.load(fh)
                nm = str(d.get("level_name", os.path.basename(path)))
                zc = len(d.get("spawn_zones", []))
            except Exception:
                nm, zc = os.path.basename(path), "?"
            cy = CONTENT_Y + 100 + i * 100
            card = pg.Rect(W//2-340, cy, 680, 82)
            pg.draw.rect(self.surf, PANEL, card, border_radius=10)
            pg.draw.rect(self.surf, BORDER, card, width=1, border_radius=10)
            self.surf.blit(self.tf.render(nm, True, TXT), (card.x+18, cy+12))
            self.surf.blit(self.f.render(f"{zc} spawn zones", True, TXT2),
                           (card.x+18, cy+48))
            def _go(idx=i): self.load(idx); self.go2()
            b = Button("SELECT →", card.right-140, cy+18, 120, 44, _go, "primary")
            b.draw(self.surf, self.f); self._s1b.append(b)

    def _d2(self):
        self._s2b = []
        lw = 830
        pg.draw.rect(self.surf, PANEL, pg.Rect(0, CONTENT_Y, lw, H-CONTENT_Y))
        pg.draw.line(self.surf, BORDER, (lw, CONTENT_Y), (lw, H), 2)

        nm = str(self.level_data.get("level_name", "Level"))
        self.surf.blit(self.tf.render(nm, True, WARN), (14, CONTENT_Y+10))
        self.surf.blit(self.f.render(
            f"{len(self.pending)} zones  ·  "
            f"{self.level_data.get('level_end_distance','?')}m total",
            True, TXT2), (14, CONTENT_Y+40))

        # Help
        help_lines = [
            "Each zone controls enemy spawning for a distance range.",
            "Enemies spawn up to the max count at the given delay.",
        ]
        for hi, hl in enumerate(help_lines):
            self.surf.blit(self.sf.render(hl, True, TXT3), (14, CONTENT_Y+64+hi*16))

        ROW = 56
        ly0 = CONTENT_Y + 100
        lh = H - ly0 - BTMBAR_H
        maxsc = max(0, len(self.pending)*ROW - lh)
        self.zscroll = max(0, min(self.zscroll, maxsc))
        self.surf.set_clip(pg.Rect(0, ly0, lw, lh))

        for i, z in enumerate(self.pending):
            ry = ly0 + i*ROW - self.zscroll
            row = pg.Rect(8, ry, lw-16, ROW-4)
            if not (ly0-ROW < ry < ly0+lh): continue
            pg.draw.rect(self.surf, PANEL2, row, border_radius=6)
            pg.draw.rect(self.surf, BORDER, row, width=1, border_radius=6)

            mn_d = z.get("min_dist", 0)
            mx_d = z.get("max_dist", "∞")
            if isinstance(mx_d, (int,float)) and mx_d >= 99999: mx_d = "∞"
            tier = str(z.get("tier", "minion"))
            tc = TIER_COL.get(tier, TXT2)

            # Top line: range
            self.surf.blit(self.f.render(f"🗺  {mn_d}m  →  {mx_d}m", True, TXT),
                           (row.x+12, ry+5))
            # Bottom line: details
            detail = (f"Max enemies: {z.get('max_skeletons','?')}   ·   "
                      f"Delay: {z.get('delay','?')}ms   ·   "
                      f"Tier: {tier.upper()}")
            self.surf.blit(self.sf.render(detail, True, tc), (row.x+12, ry+28))

            def _ed(idx=i): self.go3("edit", idx)
            def _dl(idx=i): self.delete(idx)
            eb = Button("EDIT", row.right-155, ry+12, 65, 30, _ed, "ghost")
            db = Button("DELETE", row.right-80, ry+12, 70, 30, _dl, "danger")
            eb.draw(self.surf, self.sf); db.draw(self.surf, self.sf)
            self._s2b += [eb, db]

        self.surf.set_clip(None)

        rx = lw + 16
        self.surf.blit(self.tf.render("Actions", True, TXT), (rx, CONTENT_Y+10))
        desc = self.sf.render("Add a new distance-based spawn zone.", True, TXT2)
        self.surf.blit(desc, (rx, CONTENT_Y+40))
        add = Button("＋  Add Spawn Zone", rx, CONTENT_Y+65, 420, 50,
                     lambda: self.go3("create"), "primary")
        add.draw(self.surf, self.f)

        def _save():
            self.modal = ModalDialog(
                "Commit Changes?",
                f"Write zones to '{os.path.basename(self.level_files[self.active_idx])}'?",
                self.commit, lambda: setattr(self,"modal",None))
        rst = Button("↩  Reset",      rx,     H-BTMBAR_H+8, 200, 42, self.rollback, "ghost")
        sav = Button("Save Zones  ✓", rx+215, H-BTMBAR_H+8, 205, 42, _save, "success")
        rst.draw(self.surf, self.f); sav.draw(self.surf, self.f)
        self._s2b += [add, rst, sav]

    def _d3(self):
        self._s3b = []
        mode_str = "Create New" if self.s3_mode == "create" else "Edit"

        # ── Left column: Folder browser ──
        pg.draw.rect(self.surf, PANEL, pg.Rect(0, CONTENT_Y, 450, H-CONTENT_Y))
        pg.draw.line(self.surf, BORDER, (450, CONTENT_Y), (450, H), 2)
        self.surf.blit(self.tf.render(f"{mode_str} Spawn Zone", True, WARN),
                       (14, CONTENT_Y+10))
        self.surf.blit(self.sf.render(
            "Pick the sprite folder for this enemy type (optional).",
            True, TXT2), (14, CONTENT_Y+34))
        self.browser.draw(self.surf, self.f, self.sf)

        # Selection indicator
        if self.browser.selected:
            self.surf.blit(self.sf.render(
                f"✓ Selected: {os.path.basename(self.browser.selected)}",
                True, SUCCESS), (14, H-BTMBAR_H-16))

        # ── Right column: Sliders + tier + behaviour map ──
        rx = 462
        self.surf.blit(self.tf.render("Zone Properties", True, TXT), (rx, CONTENT_Y+10))
        self.surf.blit(self.sf.render(
            "Set distance range, enemy count cap, and spawn timing.",
            True, TXT2), (rx, CONTENT_Y+38))

        for v in self.s3_ui.values():
            if hasattr(v, "draw"): v.draw(self.surf, self.f, self.sf)

        # Tier toggle
        tier = str(self.s3_ui.get("tier", "minion"))
        def _cyc():
            c = str(self.s3_ui.get("tier","minion"))
            ci = TIERS.index(c) if c in TIERS else 0
            self.s3_ui["tier"] = TIERS[(ci+1)%len(TIERS)]
        tc = TIER_COL.get(tier, TXT2)
        tier_lbl = self.sf.render(f"Enemy Tier:  {tier.upper()}", True, tc)
        self.surf.blit(tier_lbl, (rx, CONTENT_Y+315))
        tb = Button(f"[ {tier.upper()} ]  click to cycle", rx+180, CONTENT_Y+311, 260, 24, _cyc, "ghost")
        tb.draw(self.surf, self.sf)
        self._s3b.append(tb)

        # Behaviour mapper
        self.bmap.draw(self.surf, self.f, self.sf)

        # Bottom bar
        sub = Button("Add Zone  ✓" if self.s3_mode=="create" else "Save Changes  ✓",
                     W-470, H-BTMBAR_H+8, 250, 42, self.submit, "success")
        cnl = Button("← Cancel", W-210, H-BTMBAR_H+8, 110, 42, self.go2, "ghost")
        sim = Button("Simulate  ▶", W-690, H-BTMBAR_H+8, 210, 42, self.simulate, "primary")
        sub.draw(self.surf, self.f); cnl.draw(self.surf, self.f); sim.draw(self.surf, self.f)
        self._s3b += [sub, cnl, sim]


if __name__ == "__main__":
    WaveEditorApp().run()
