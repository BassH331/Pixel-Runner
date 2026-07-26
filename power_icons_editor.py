#!/usr/bin/env python3
"""
power_icons_editor.py
Power Icons & Screen Placement Plugin for Pixel-Runner.
Pick icon images from your asset folders and place them on the game screen.
"""

import os
import sys
import json
import glob
import shutil
import math
from datetime import datetime
import pygame as pg

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

pg.init()
pg.font.init()

# ── Window ────────────────────────────────────────────────────────────────────
SW, SH = 1440, 860
screen = pg.display.set_mode((SW, SH))
pg.display.set_caption("Power Icons Editor  ·  Pixel Runner")
clock = pg.time.Clock()

# ── Fonts ─────────────────────────────────────────────────────────────────────
def make_font(size, bold=False):
    return pg.font.SysFont("dejavusans,ubuntu,arial,helvetica,sans-serif", size, bold=bold)

F_TITLE  = make_font(22, bold=True)
F_HEAD   = make_font(16, bold=True)
F_BODY   = make_font(14)
F_SMALL  = make_font(12)
F_BADGE  = make_font(12, bold=True)
F_ICON   = make_font(11)

# ── Colour Palette ────────────────────────────────────────────────────────────
C_BG         = ( 13,  15,  23)
C_PANEL      = ( 22,  26,  38)
C_PANEL_DARK = ( 16,  19,  29)
C_HEADER     = ( 28,  34,  52)
C_BORDER     = ( 48,  58,  85)
C_BORDER_HI  = ( 80, 100, 150)
C_TEXT       = (230, 235, 248)
C_MUTED      = (130, 142, 170)
C_CYAN       = (  0, 220, 255)
C_GREEN      = (  0, 220, 110)
C_ORANGE     = (255, 150,  30)
C_PURPLE     = (160,  60, 255)
C_RED        = (220,  50,  70)
C_YELLOW     = (255, 210,  60)
C_WHITE      = (255, 255, 255)
C_SEL        = ( 30,  60, 100)

# ── Human-readable power names ────────────────────────────────────────────────
POWER_NAMES = {
    "ATTACK_THRUST":       "⚔  Thrust Attack",
    "ATTACK_SMASH":        "🔨  Smash Attack",
    "ATTACK_POWER":        "💥  Power Strike",
    "DEFEND":              "🛡  Block / Defend",
    "SPECIAL_ATTACK":      "✨  Special Move",
    "DASH":                "💨  Quick Dash",
    "ROLL":                "🔄  Evade Roll",
    "JUMP":                "⬆  Jump",
    "TRANSFORM":           "🔁  Transform",
    "MANA_BAR_ICON":       "💧  Mana Bar Icon",
    "STAMINA_BAR_ICON":    "⚡  Stamina Bar Icon",
    "SOULS_COUNTER_ICON":  "👻  Souls Counter Icon",
    "RELIC_COUNTER_ICON":  "🗡  Relic Counter Icon",
}

POWER_COLORS = {
    "ATTACK_THRUST":       C_CYAN,
    "ATTACK_SMASH":        C_ORANGE,
    "ATTACK_POWER":        C_RED,
    "DEFEND":              C_GREEN,
    "SPECIAL_ATTACK":      C_PURPLE,
    "DASH":                C_YELLOW,
    "ROLL":                (100, 200, 255),
    "JUMP":                (180, 255, 180),
    "TRANSFORM":           (220, 180, 255),
    "MANA_BAR_ICON":       (70, 160, 255),
    "STAMINA_BAR_ICON":    (140, 230, 90),
    "SOULS_COUNTER_ICON":  (220, 180, 255),
    "RELIC_COUNTER_ICON":  (255, 215, 0),
}


# ══════════════════════════════════════════════════════════════════════════════
#  Utility drawing helpers
# ══════════════════════════════════════════════════════════════════════════════

def draw_rect_alpha(surf, color, rect, alpha=180, radius=8):
    s = pg.Surface((rect.width, rect.height), pg.SRCALPHA)
    pg.draw.rect(s, (*color, alpha), (0, 0, rect.width, rect.height), border_radius=radius)
    surf.blit(s, rect.topleft)

def draw_text(surf, text, font, color, x, y, anchor="topleft"):
    t = font.render(str(text), True, color)
    r = t.get_rect()
    setattr(r, anchor, (x, y))
    surf.blit(t, r)
    return r

def draw_panel(surf, rect, header_text=None, header_color=None):
    """Draw a rounded dark panel, optionally with a header band."""
    pg.draw.rect(surf, C_PANEL, rect, border_radius=12)
    pg.draw.rect(surf, C_BORDER, rect, width=1, border_radius=12)
    if header_text:
        hdr = pg.Rect(rect.x, rect.y, rect.width, 44)
        pg.draw.rect(surf, C_HEADER, hdr, border_radius=12)
        # square off bottom corners of header
        pg.draw.rect(surf, C_HEADER, (rect.x, rect.y + 30, rect.width, 14))
        pg.draw.rect(surf, C_BORDER, hdr, width=1, border_radius=12)
        pg.draw.line(surf, C_BORDER, (rect.x, rect.y + 44), (rect.right, rect.y + 44))
        col = header_color or C_CYAN
        draw_text(surf, header_text, F_HEAD, col, rect.centerx, rect.y + 22, "center")


# ══════════════════════════════════════════════════════════════════════════════
#  UI Widgets
# ══════════════════════════════════════════════════════════════════════════════

class Button:
    def __init__(self, label, rect, callback=None, color=None, text_color=None, icon=None):
        self.label = label
        self.rect  = pg.Rect(rect)
        self.cb    = callback
        self.color = color or C_HEADER
        self.tcol  = text_color or C_TEXT
        self.icon  = icon
        self.hover = False
        self.active = False          # pressed highlight

    def draw(self, surf):
        col = C_SEL if self.active else (C_BORDER_HI if self.hover else self.color)
        pg.draw.rect(surf, col, self.rect, border_radius=8)
        border_c = C_CYAN if self.hover else C_BORDER
        pg.draw.rect(surf, border_c, self.rect, width=1, border_radius=8)
        draw_text(surf, self.label, F_BODY, self.tcol, self.rect.centerx, self.rect.centery, "center")

    def handle(self, ev):
        if ev.type == pg.MOUSEMOTION:
            self.hover = self.rect.collidepoint(ev.pos)
        if ev.type == pg.MOUSEBUTTONDOWN and ev.button == 1 and self.rect.collidepoint(ev.pos):
            if self.cb:
                self.cb()
            return True
        return False


class Slider:
    def __init__(self, label, rect, lo, hi, value, fmt="{:.1f}", on_change=None):
        self.label  = label
        self.rect   = pg.Rect(rect)
        self.lo, self.hi = lo, hi
        self.value  = value
        self.fmt    = fmt
        self.on_change = on_change
        self.drag   = False

    def _ratio(self):
        return (self.value - self.lo) / max(0.001, self.hi - self.lo)

    def draw(self, surf):
        # Label row
        draw_text(surf, self.label, F_SMALL, C_MUTED, self.rect.x, self.rect.y - 18)
        val_str = self.fmt.format(self.value)
        draw_text(surf, val_str, F_SMALL, C_CYAN, self.rect.right, self.rect.y - 18, "topright")

        # Track
        track = pg.Rect(self.rect.x, self.rect.centery - 4, self.rect.width, 8)
        pg.draw.rect(surf, C_PANEL_DARK, track, border_radius=4)
        fill_w = int(track.width * self._ratio())
        if fill_w > 0:
            pg.draw.rect(surf, C_CYAN, (track.x, track.y, fill_w, track.height), border_radius=4)

        # Handle
        hx = track.x + fill_w
        hy = track.centery
        pg.draw.circle(surf, C_WHITE, (hx, hy), 9)
        pg.draw.circle(surf, C_CYAN, (hx, hy), 6)

    def handle(self, ev):
        if ev.type == pg.MOUSEBUTTONDOWN and ev.button == 1:
            grab = pg.Rect(self.rect.x, self.rect.centery - 12, self.rect.width, 24)
            if grab.collidepoint(ev.pos):
                self.drag = True
        if ev.type == pg.MOUSEBUTTONUP and ev.button == 1:
            self.drag = False
        if ev.type == pg.MOUSEMOTION and self.drag:
            ratio = (ev.pos[0] - self.rect.x) / max(1, self.rect.width)
            self.value = round(max(self.lo, min(self.hi, self.lo + ratio * (self.hi - self.lo))), 2)
            if self.on_change:
                self.on_change(self.value)


class TextBox:
    def __init__(self, label, rect, value="", on_change=None, max_len=20):
        self.label = label
        self.rect  = pg.Rect(rect)
        self.value = value
        self.on_change = on_change
        self.active = False
        self.max_len = max_len

    def draw(self, surf):
        if self.label:
            draw_text(surf, self.label, F_SMALL, C_MUTED, self.rect.x, self.rect.y - 18)
        bg = C_SEL if self.active else C_PANEL_DARK
        bc = C_CYAN if self.active else C_BORDER
        pg.draw.rect(surf, bg, self.rect, border_radius=6)
        pg.draw.rect(surf, bc, self.rect, width=1, border_radius=6)
        display = self.value + ("|" if self.active and (pg.time.get_ticks() // 500) % 2 == 0 else "")
        draw_text(surf, display, F_BODY, C_TEXT, self.rect.x + 10, self.rect.centery, "midleft")

    def handle(self, ev):
        if ev.type == pg.MOUSEBUTTONDOWN and ev.button == 1:
            self.active = self.rect.collidepoint(ev.pos)
        if ev.type == pg.KEYDOWN and self.active:
            if ev.key in (pg.K_RETURN, pg.K_ESCAPE):
                self.active = False
            elif ev.key == pg.K_BACKSPACE:
                self.value = self.value[:-1]
                if self.on_change: self.on_change(self.value)
            elif len(ev.unicode) == 1 and ev.unicode.isprintable() and len(self.value) < self.max_len:
                self.value += ev.unicode
                if self.on_change: self.on_change(self.value)


# ══════════════════════════════════════════════════════════════════════════════
#  Toast notification
# ══════════════════════════════════════════════════════════════════════════════

class Toast:
    def __init__(self):
        self.msg = ""
        self.ticks = 0
        self.color = C_GREEN

    def show(self, msg, color=None):
        self.msg   = msg
        self.ticks = 180
        self.color = color or C_GREEN

    def draw(self, surf):
        if self.ticks <= 0:
            return
        self.ticks -= 1
        alpha = min(255, self.ticks * 6)
        t = F_BODY.render(self.msg, True, C_WHITE)
        w, h = t.get_width() + 40, 44
        s = pg.Surface((w, h), pg.SRCALPHA)
        pg.draw.rect(s, (*self.color, min(200, alpha)), (0, 0, w, h), border_radius=10)
        pg.draw.rect(s, (*C_WHITE, min(100, alpha)), (0, 0, w, h), width=1, border_radius=10)
        s.blit(t, (20, (h - t.get_height()) // 2))
        surf.blit(s, (SW // 2 - w // 2, SH - 80))


# ══════════════════════════════════════════════════════════════════════════════
#  Main Plugin
# ══════════════════════════════════════════════════════════════════════════════

CONFIG_PATH = "game_data/power_icons_config.json"

# Mapping from pygame BUTTON_ IDs to PS symbols
PS_SYMBOLS = {
    "BUTTON_0": "✕",
    "BUTTON_1": "○",
    "BUTTON_2": "△",
    "BUTTON_3": "□",
    "BUTTON_4": "L1",
    "BUTTON_5": "R1",
    "BUTTON_6": "L2",
    "BUTTON_7": "R2",
}

FRAME_STYLES = ["circle", "square", "glowing", "none"]

LAYOUT_PRESETS = {
    "Bottom Bar": "bottom_bar",
    "Diamond": "diamond",
    "Left Stack": "left_stack",
    "Arc": "arc",
}

IMG_EXTS = {".png", ".jpg", ".jpeg", ".bmp", ".webp"}
THUMB_SZ = 64      # thumbnail size in gallery grid
FOLDER_ROW_H = 36


class PowerIconsEditor:
    # ── Panel geometry ─────────────────────────────────────────────────────────
    LEFT_W   = 340
    RIGHT_W  = 380
    TOP_H    = 70
    BOT_H    = 110
    MID_H    = SH - TOP_H - BOT_H

    def __init__(self):
        self.config = self._load_config()
        self.toast  = Toast()

        # viewport (game canvas - 16:9 aspect ratio matching 1280x720 game screen)
        self.game_w = self.config.get("screen_width", 1280)
        self.game_h = self.config.get("screen_height", 720)

        avail_w = SW - self.LEFT_W - self.RIGHT_W - 40
        avail_h = self.MID_H - 40

        aspect = self.game_w / self.game_h
        if avail_w / avail_h > aspect:
            vh = avail_h
            vw = int(vh * aspect)
        else:
            vw = avail_w
            vh = int(vw / aspect)

        vx = self.LEFT_W + 20 + (avail_w - vw) // 2
        vy = self.TOP_H + 20 + (avail_h - vh) // 2

        self.viewport = pg.Rect(vx, vy, vw, vh)
        self.sx = self.viewport.width / self.game_w
        self.sy = self.viewport.height / self.game_h

        # asset browser state
        self.folders: list[str] = []
        self.sel_folder_idx  = 0
        self.images: list[str]  = []
        self.thumbs: dict[str, pg.Surface] = {}
        self.thumb_scroll   = 0       # row offset for gallery
        self.folder_scroll  = 0
        self.slot_scroll    = 0       # scroll offset for right panel power slots
        self.sel_image: str | None = None
        self.search = ""

        # slot / drag state
        self.active_key: str = list(self.config["icons"].keys())[0] if self.config["icons"] else "ATTACK_THRUST"
        self.drag_key: str | None = None
        self.drag_off = (0, 0)

        # widgets
        self._build_widgets()

        # scan
        self._scan_folders()
        self._load_images()
        self._cache_icon_surfs()

    # ── Config I/O ─────────────────────────────────────────────────────────────

    def _default_config(self):
        spacing = 72
        count   = 6
        start_x = self.game_w // 2 - ((count - 1) * spacing) // 2
        y       = 660
        defaults = [
            ("ATTACK_THRUST",       "□",         C_CYAN,   "circle",  start_x),
            ("ATTACK_SMASH",        "○",         C_ORANGE, "circle",  start_x + spacing),
            ("ATTACK_POWER",        "△",         C_RED,    "circle",  start_x + spacing*2),
            ("DEFEND",              "R2",        C_GREEN,  "circle",  start_x + spacing*3),
            ("SPECIAL_ATTACK",      "F",         C_PURPLE, "glowing", start_x + spacing*4),
            ("TRANSFORM",           "T",         (220,180,255), "glowing", start_x + spacing*5),
            ("MANA_BAR_ICON",       "MANA",      (70,160,255),  "circle", 20),
            ("STAMINA_BAR_ICON",    "STAMINA",   (140,230,90),  "circle", 20),
            ("SOULS_COUNTER_ICON",  "SOULS",     (220,180,255), "circle", 20),
            ("RELIC_COUNTER_ICON",  "RELICS",    (255,215,0),   "circle", 120),
        ]
        icons = {}
        for key, kb, col, style, x in defaults:
            icons[key] = {
                "enabled": True,
                "label": POWER_NAMES.get(key, key),
                "asset_path": "",
                "x": x, "y": y,
                "width": 56, "height": 56,
                "scale": 1.0, "opacity": 255,
                "keybind": kb,
                "frame_style": style,
                "border_color": list(col),
                "badge_bg": [20, 20, 40],
                "anchor": "center",
            }
        return {
            "screen_width": 1280, "screen_height": 720,
            "show_keybind_badges": True,
            "global_scale": 1.0,
            "icons": icons,
        }

    def _load_config(self):
        if os.path.exists(CONFIG_PATH):
            try:
                with open(CONFIG_PATH) as f:
                    cfg = json.load(f)
                if "icons" in cfg:
                    return cfg
            except Exception:
                pass
        return self._default_config()

    def save_config(self):
        os.makedirs("game_data", exist_ok=True)
        if os.path.exists(CONFIG_PATH):
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            shutil.copy2(CONFIG_PATH, f"game_data/power_icons_config.backup_{ts}.json")
        with open(CONFIG_PATH, "w") as f:
            json.dump(self.config, f, indent=2)
        self.toast.show("✓ Saved successfully!", C_GREEN)

    # ── Widget construction ────────────────────────────────────────────────────

    def _build_widgets(self):
        # TOP toolbar buttons
        bw, bh = 140, 40
        by = (self.TOP_H - bh) // 2
        self.btn_save = Button("💾 Save Config",   (14,  by, bw, bh), self.save_config,    color=(0, 130, 80))
        self.btn_load = Button("📂 Load Config",   (160, by, bw, bh), self._reload,        color=C_HEADER)
        self.btn_reset = Button("↺ Reset Layout",  (306, by, bw, bh), self._reset_default, color=(100, 30, 30))

        # PRESET buttons (bottom bar)
        bby  = SH - self.BOT_H + 38
        pbw  = 160
        pbh  = 40
        gap  = 12
        px   = self.LEFT_W + 14
        self.preset_btns = [
            Button("⬛ Bottom Bar",   (px,              bby, pbw, pbh), lambda: self._apply_preset("bottom_bar")),
            Button("◆ Diamond",       (px + pbw + gap,  bby, pbw, pbh), lambda: self._apply_preset("diamond")),
            Button("▮ Left Stack",    (px + (pbw+gap)*2,bby, pbw, pbh), lambda: self._apply_preset("left_stack")),
            Button("〇 Arc",          (px + (pbw+gap)*3,bby, pbw, pbh), lambda: self._apply_preset("arc")),
        ]

        # ASSIGN IMAGE button in Left Panel
        assign_y = SH - self.BOT_H - 52
        self.btn_assign = Button("🎯 Assign to Active Slot", (10, assign_y, self.LEFT_W - 20, 44),
                                 self.assign_image, color=(0, 140, 70), text_color=C_WHITE)

        # RIGHT PANEL widgets
        rx = SW - self.RIGHT_W + 20
        self._build_right_widgets(rx)

        # Search box
        self.search_box = TextBox("", (14, self.TOP_H + 46, self.LEFT_W - 28, 34),
                                  on_change=self._on_search)

        # Slot selection hitboxes (updated dynamically in draw_right_panel)
        self.slot_rects: list[tuple[pg.Rect, str]] = []

    def _build_right_widgets(self, rx):
        pw = self.RIGHT_W - 40

        def prop(key):
            return self.config["icons"].get(self.active_key, {}).get(key, "")

        self.btn_add_slot = Button("＋ Add Power Slot", (rx + 10, 0, 170, 32), self.add_slot)
        self.btn_del_slot = Button("✕ Delete Slot",    (rx + 190, 0, 170, 32), self.delete_active, color=(110, 30, 30))

        # Frame style selector buttons
        fsw = pw // len(FRAME_STYLES)
        self.btn_frame_styles = []
        for i, st in enumerate(FRAME_STYLES):
            b = Button(st.capitalize(), (rx + 10 + i * fsw, 0, fsw - 4, 30),
                       callback=lambda s=st: self._set("frame_style", s))
            self.btn_frame_styles.append(b)

        self.sld_scale = Slider(
            "Icon Size (Scale)", (rx + 20, 0, pw, 24), 0.3, 3.0,
            prop("scale") or 1.0, fmt="{:.2f}x",
            on_change=lambda v: self._set("scale", v))

        self.sld_opacity = Slider(
            "Opacity", (rx + 20, 0, pw, 24), 0, 255,
            prop("opacity") or 255, fmt="{:.0f}",
            on_change=lambda v: self._set("opacity", int(v)))

        self.sld_cost = Slider(
            "Resource Cost (Stamina / Mana)", (rx + 20, 0, pw, 24), 0, 100,
            prop("cost") or 20.0, fmt="{:.0f} pts",
            on_change=lambda v: self._set("cost", float(v)))

        rtw = pw // 3
        self.btn_res_types = []
        for i, rt in enumerate(["stamina", "mana", "none"]):
            b = Button(rt.capitalize(), (rx + 10 + i * rtw, 0, rtw - 4, 28),
                       callback=lambda r=rt: self._set("resource_type", r))
            self.btn_res_types.append(b)

        self.tb_keybind = TextBox(
            "Button Badge (e.g. △ ○ □ ✕ L1 R1)",
            (rx + 20, 0, pw, 34),
            value=str(prop("keybind")),
            on_change=lambda v: self._set("keybind", v))

        self.tb_label = TextBox(
            "Display Name",
            (rx + 20, 0, pw, 34),
            value=str(prop("label")),
            on_change=lambda v: self._set("label", v))

    def _get_all_buttons(self) -> list[Button]:
        """Return master list of all interactive buttons for event processing."""
        btns = [
            self.btn_save, self.btn_load, self.btn_reset,
            self.btn_assign, self.btn_add_slot, self.btn_del_slot
        ]
        btns.extend(self.preset_btns)
        btns.extend(self.btn_frame_styles)
        btns.extend(self.btn_res_types)
        return btns

    def _refresh_right_widgets(self):
        icon = self.config["icons"].get(self.active_key, {})
        self.sld_scale.value   = icon.get("scale",   1.0)
        self.sld_opacity.value = icon.get("opacity",  255)
        self.sld_cost.value    = icon.get("cost",     20.0)
        self.tb_keybind.value  = str(icon.get("keybind", ""))
        self.tb_label.value    = str(icon.get("label", ""))

    # ── Asset browser ──────────────────────────────────────────────────────────

    def _scan_folders(self):
        self.folders = []
        for root, dirs, files in os.walk("assets"):
            if any(os.path.splitext(f)[1].lower() in IMG_EXTS for f in files):
                self.folders.append(os.path.relpath(root))
        self.folders.sort()
        if not self.folders:
            self.folders = ["assets"]

    def _load_images(self):
        self.images = []
        self.thumbs = {}
        self.thumb_scroll = 0
        if not self.folders:
            return
        folder = self.folders[min(self.sel_folder_idx, len(self.folders) - 1)]
        if not os.path.isdir(folder):
            return
        for f in sorted(os.listdir(folder)):
            ext = os.path.splitext(f)[1].lower()
            if ext in IMG_EXTS:
                full = os.path.join(folder, f)
                if not self.search or self.search.lower() in f.lower():
                    self.images.append(full)
        # generate thumbnails
        for p in self.images[:120]:
            try:
                img  = pg.image.load(p).convert_alpha()
                img  = pg.transform.smoothscale(img, (THUMB_SZ, THUMB_SZ))
                self.thumbs[p] = img
            except Exception:
                pass

    def _on_search(self, val):
        self.search = val
        self._load_images()

    # ── Icon surface cache (for viewport) ─────────────────────────────────────

    def _cache_icon_surfs(self):
        self._icon_surfs: dict[str, pg.Surface] = {}
        for key, data in self.config["icons"].items():
            path = data.get("asset_path", "")
            if path and os.path.exists(path):
                try:
                    img = pg.image.load(path).convert_alpha()
                    self._icon_surfs[key] = img
                except Exception:
                    pass

    # ── Config helpers ─────────────────────────────────────────────────────────

    def _reload(self):
        self.config = self._load_config()
        self._cache_icon_surfs()
        self._refresh_right_widgets()
        self.toast.show("Config reloaded.", C_CYAN)

    def _reset_default(self):
        self.config = self._default_config()
        self._cache_icon_surfs()
        self._refresh_right_widgets()
        self.toast.show("Reset to default layout.", C_ORANGE)

    def _set(self, key, value):
        self.config["icons"].setdefault(self.active_key, {})
        self.config["icons"][self.active_key][key] = value

    def _icon_data(self, key=None):
        k = key or self.active_key
        return self.config["icons"].get(k, {})

    def _human(self, key):
        return POWER_NAMES.get(key, key.replace("_", " ").title())

    # ── Presets ────────────────────────────────────────────────────────────────

    def _apply_preset(self, name):
        keys = [k for k, v in self.config["icons"].items() if v.get("enabled", True)]
        n    = len(keys)
        gw, gh = self.game_w, self.game_h

        if name == "bottom_bar":
            spacing = 72
            sx = gw // 2 - ((n - 1) * spacing) // 2
            for i, k in enumerate(keys):
                self.config["icons"][k]["x"] = sx + i * spacing
                self.config["icons"][k]["y"] = gh - 60

        elif name == "diamond" and n >= 4:
            cx, cy, r = gw - 120, gh - 130, 60
            offs = [(0,-r),(r,0),(0,r),(-r,0)]
            for i, k in enumerate(keys[:4]):
                self.config["icons"][k]["x"] = cx + offs[i][0]
                self.config["icons"][k]["y"] = cy + offs[i][1]

        elif name == "left_stack":
            for i, k in enumerate(keys):
                self.config["icons"][k]["x"] = 50
                self.config["icons"][k]["y"] = 200 + i * 70

        elif name == "arc":
            cx, cy, r = gw // 2, gh + 100, 280
            for i, k in enumerate(keys):
                ang = math.radians(200 + (i / max(1, n-1)) * 140)
                self.config["icons"][k]["x"] = int(cx + r * math.cos(ang))
                self.config["icons"][k]["y"] = int(cy + r * math.sin(ang))

        self.toast.show(f"Applied preset: {name.replace('_',' ').title()}", C_CYAN)

    def assign_image(self):
        if self.sel_image and self.active_key:
            self._set("asset_path", self.sel_image)
            try:
                img = pg.image.load(self.sel_image).convert_alpha()
                self._icon_surfs[self.active_key] = img
            except Exception:
                pass
            self.toast.show("✓  Icon assigned!", C_GREEN)

    def add_slot(self):
        idx = len(self.config["icons"]) + 1
        key = f"CUSTOM_POWER_{idx}"
        self.config["icons"][key] = {
            "enabled": True, "label": f"Power {idx}",
            "asset_path": "",
            "x": self.game_w // 2, "y": self.game_h - 60,
            "width": 56, "height": 56, "scale": 1.0, "opacity": 255,
            "keybind": str(idx), "frame_style": "circle",
            "border_color": [0, 200, 255], "badge_bg": [20, 20, 40],
            "anchor": "center",
        }
        self.active_key = key
        self._refresh_right_widgets()
        self.toast.show(f"Added slot: Power {idx}", C_CYAN)

    def delete_active(self):
        if self.active_key in self.config["icons"]:
            del self.config["icons"][self.active_key]
            keys = list(self.config["icons"].keys())
            self.active_key = keys[0] if keys else ""
            self._refresh_right_widgets()
            self.toast.show("Slot deleted.", C_ORANGE)

    # ── Coordinate helpers ─────────────────────────────────────────────────────

    def g2v(self, gx, gy):
        return (int(self.viewport.x + gx * self.sx),
                int(self.viewport.y + gy * self.sy))

    def v2g(self, vx, vy):
        return (max(0, min(self.game_w, int((vx - self.viewport.x) / self.sx))),
                max(0, min(self.game_h, int((vy - self.viewport.y) / self.sy))))

    # ══════════════════════════════════════════════════════════════════════════
    #  Draw routines
    # ══════════════════════════════════════════════════════════════════════════

    def draw_topbar(self):
        pg.draw.rect(screen, C_HEADER, (0, 0, SW, self.TOP_H))
        pg.draw.line(screen, C_BORDER, (0, self.TOP_H), (SW, self.TOP_H))
        draw_text(screen, "POWER ICONS EDITOR", F_TITLE, C_CYAN, SW - 20, self.TOP_H // 2, "midright")
        for b in [self.btn_save, self.btn_load, self.btn_reset]:
            b.draw(screen)

    def draw_left_panel(self):
        panel = pg.Rect(0, self.TOP_H, self.LEFT_W, SH - self.TOP_H)
        pg.draw.rect(screen, C_PANEL, panel)
        pg.draw.line(screen, C_BORDER, (self.LEFT_W, self.TOP_H), (self.LEFT_W, SH))

        y = self.TOP_H + 10
        draw_text(screen, "📁  Icon Library", F_HEAD, C_CYAN, 14, y)
        y += 34

        # search box
        self.search_box.rect.y = y
        draw_text(screen, "🔍  Search", F_SMALL, C_MUTED, 14, y - 16)
        self.search_box.draw(screen)
        y += 52

        # folder list
        draw_text(screen, "Folder", F_SMALL, C_MUTED, 14, y)
        y += 20
        folder_area = pg.Rect(10, y, self.LEFT_W - 20, 180)
        pg.draw.rect(screen, C_PANEL_DARK, folder_area, border_radius=8)
        pg.draw.rect(screen, C_BORDER, folder_area, width=1, border_radius=8)

        visible_count = 5
        visible = self.folders[self.folder_scroll: self.folder_scroll + visible_count]
        for i, folder in enumerate(visible):
            fy = y + 4 + i * FOLDER_ROW_H
            real_idx = i + self.folder_scroll
            is_sel   = (real_idx == self.sel_folder_idx)
            if is_sel:
                pg.draw.rect(screen, C_SEL, (12, fy, self.LEFT_W - 24, FOLDER_ROW_H - 4), border_radius=6)

            short = folder.replace("assets/", "").replace("assets\\", "")
            if len(short) > 32: short = "…" + short[-30:]
            col = C_CYAN if is_sel else C_TEXT
            draw_text(screen, short, F_SMALL, col, 24, fy + 10)
        y += 188

        # gallery
        draw_text(screen, "Icons  (click to select)", F_SMALL, C_MUTED, 14, y + 4)
        y += 22

        cols  = 4
        pad   = 8
        cell  = THUMB_SZ + pad
        rows_vis = 4
        gallery_h = rows_vis * cell + pad
        gallery   = pg.Rect(10, y, self.LEFT_W - 20, gallery_h)
        pg.draw.rect(screen, C_PANEL_DARK, gallery, border_radius=8)
        pg.draw.rect(screen, C_BORDER, gallery, width=1, border_radius=8)

        start_row = self.thumb_scroll
        for idx, path in enumerate(self.images):
            row = idx // cols
            col = idx  % cols
            if row < start_row or row >= start_row + rows_vis:
                continue
            ix = gallery.x + pad + col * cell
            iy = gallery.y + pad + (row - start_row) * cell
            tr = pg.Rect(ix, iy, THUMB_SZ, THUMB_SZ)

            is_sel = (path == self.sel_image)
            pg.draw.rect(screen, C_SEL if is_sel else C_HEADER, tr, border_radius=6)
            bc = C_CYAN if is_sel else C_BORDER
            pg.draw.rect(screen, bc, tr, width=2, border_radius=6)

            thumb = self.thumbs.get(path)
            if thumb:
                screen.blit(thumb, tr)
            else:
                draw_text(screen, "?", F_BODY, C_MUTED, tr.centerx, tr.centery, "center")

        # scroll hint
        total_rows = max(1, math.ceil(len(self.images) / cols))
        if total_rows > rows_vis:
            scroll_info = f"↑↓ scroll  ({start_row+1}–{min(start_row+rows_vis, total_rows)} / {total_rows} rows)"
            draw_text(screen, scroll_info, F_ICON, C_MUTED, gallery.centerx, gallery.bottom + 4, "midtop")
        y += gallery_h + 20

        if self.sel_image:
            short = os.path.basename(self.sel_image)
            draw_text(screen, f"Selected:  {short}", F_SMALL, C_MUTED, 14, y)
            y += 24

        # assign button
        self.btn_assign.rect.topleft = (10, SH - self.BOT_H - 52)
        self.btn_assign.draw(screen)

    def draw_viewport(self):
        vp = self.viewport
        pg.draw.rect(screen, C_PANEL_DARK, vp, border_radius=8)
        pg.draw.rect(screen, C_BORDER_HI, vp, width=2, border_radius=8)

        # label
        draw_text(screen, "Game Screen  (drag icons to reposition)", F_SMALL, C_MUTED,
                  vp.centerx, vp.y - 20, "midbottom")

        # grid
        for gx in range(0, self.game_w + 1, 160):
            vx, _ = self.g2v(gx, 0)
            if vp.left <= vx <= vp.right:
                pg.draw.line(screen, (28, 34, 50), (vx, vp.top), (vx, vp.bottom))
        for gy in range(0, self.game_h + 1, 90):
            _, vy = self.g2v(0, gy)
            if vp.top <= vy <= vp.bottom:
                pg.draw.line(screen, (28, 34, 50), (vp.left, vy), (vp.right, vy))

        # icons
        for key, data in self.config["icons"].items():
            if not data.get("enabled", True):
                continue
            gx, gy = data.get("x", 640), data.get("y", 660)
            vx, vy = self.g2v(gx, gy)
            w = max(10, int(data.get("width", 56) * data.get("scale", 1.0) * self.sx))
            h = max(10, int(data.get("height", 56) * data.get("scale", 1.0) * self.sy))
            r = pg.Rect(vx - w//2, vy - h//2, w, h)

            style  = data.get("frame_style", "circle")
            col    = tuple(data.get("border_color", [0, 200, 255]))
            is_act = (key == self.active_key)

            # frame
            if style == "circle":
                pg.draw.circle(screen, (*col, 60), (vx, vy), w // 2 + 2)
                pg.draw.circle(screen, col, (vx, vy), w // 2, width=3 if is_act else 2)
            elif style == "glowing":
                for gr, ga in [(w//2+6, 30),(w//2+3, 80),(w//2, 220)]:
                    gs = pg.Surface((gr*2+4, gr*2+4), pg.SRCALPHA)
                    pg.draw.circle(gs, (*col, ga), (gr+2, gr+2), gr, width=2)
                    screen.blit(gs, (vx-gr-2, vy-gr-2))
                pg.draw.circle(screen, (20,22,32), (vx, vy), w//2)
            else:
                pg.draw.rect(screen, (*col, 50), r, border_radius=6)
                pg.draw.rect(screen, col, r, width=3 if is_act else 2, border_radius=6)

            # icon image
            surf = self._icon_surfs.get(key)
            if surf:
                scaled = pg.transform.smoothscale(surf, (w-4, h-4))
                if style in ("circle", "glowing"):
                    mask = pg.Surface(scaled.get_size(), pg.SRCALPHA)
                    pg.draw.circle(mask, (255, 255, 255, 255), (scaled.get_width() // 2, scaled.get_height() // 2), min(scaled.get_width(), scaled.get_height()) // 2)
                    res = pg.Surface(scaled.get_size(), pg.SRCALPHA)
                    res.blit(scaled, (0, 0))
                    res.blit(mask, (0, 0), special_flags=pg.BLEND_RGBA_MULT)
                    scaled = res
                op = data.get("opacity", 255)
                if op < 255:
                    alpha_s = pg.Surface(scaled.get_size(), pg.SRCALPHA)
                    alpha_s.fill((255, 255, 255, op))
                    scaled.blit(alpha_s, (0, 0), special_flags=pg.BLEND_RGBA_MULT)
                screen.blit(scaled, (vx - (w-4)//2, vy - (h-4)//2))
            else:
                # placeholder letter
                letter = self._human(key)[:2].upper()
                draw_text(screen, letter, F_BADGE, col, vx, vy, "center")

            # keybind badge
            kb = data.get("keybind", "")
            if kb:
                bt = F_ICON.render(kb, True, C_WHITE)
                bw = bt.get_width() + 8
                bh = 16
                brect = pg.Rect(vx - bw//2, vy + h//2 - 4, bw, bh)
                pg.draw.rect(screen, tuple(data.get("badge_bg",[20,20,40])), brect, border_radius=4)
                screen.blit(bt, (brect.x + 4, brect.y + 2))

            # active highlight
            if is_act:
                pg.draw.rect(screen, C_ORANGE, r.inflate(10, 10), width=2, border_radius=8)
                draw_text(screen, self._human(key), F_ICON, C_ORANGE, vx, r.top - 14, "midbottom")

    def draw_right_panel(self):
        rx = SW - self.RIGHT_W
        panel = pg.Rect(rx, self.TOP_H, self.RIGHT_W, SH - self.TOP_H)
        pg.draw.rect(screen, C_PANEL, panel)
        pg.draw.line(screen, C_BORDER, (rx, self.TOP_H), (rx, SH))

        y = self.TOP_H + 10
        draw_text(screen, "⚡ Power Slots", F_HEAD, C_CYAN, rx + 20, y)
        y += 28

        # slot list
        icons = self.config["icons"]
        slot_area_h = 166
        slot_area = pg.Rect(rx + 10, y, self.RIGHT_W - 20, slot_area_h)
        pg.draw.rect(screen, C_PANEL_DARK, slot_area, border_radius=8)
        pg.draw.rect(screen, C_BORDER, slot_area, width=1, border_radius=8)

        old_clip = screen.get_clip()
        screen.set_clip(slot_area)

        self.slot_rects.clear()
        keys = list(icons.keys())
        for i, key in enumerate(keys):
            data = icons[key]
            sy = y + 4 + (i - self.slot_scroll) * 32
            s_rect = pg.Rect(rx + 12, sy, self.RIGHT_W - 24, 30)
            self.slot_rects.append((s_rect, key))

            if sy + 30 >= y and sy <= y + slot_area_h:
                is_act = (key == self.active_key)
                if is_act:
                    pg.draw.rect(screen, C_SEL, s_rect, border_radius=6)

                col = POWER_COLORS.get(key, C_CYAN) if is_act else C_TEXT
                label = self._human(key)
                draw_text(screen, label, F_BODY, col, rx + 24, sy + 7)

                # enabled toggle dot
                dcol = C_GREEN if data.get("enabled", True) else C_RED
                pg.draw.circle(screen, dcol, (rx + self.RIGHT_W - 22, sy + 15), 6)

        screen.set_clip(old_clip)

        if len(keys) > 5:
            scroll_text = f"↑↓ Scroll slots ({self.slot_scroll + 1}–{min(self.slot_scroll + 5, len(keys))}/{len(keys)})"
            draw_text(screen, scroll_text, F_ICON, C_MUTED, slot_area.centerx, slot_area.bottom - 12, "midbottom")

        y += slot_area_h + 8

        # Add / Delete buttons
        self.btn_add_slot.rect.topleft = (rx + 10, y)
        self.btn_del_slot.rect.topleft = (rx + 190, y)
        self.btn_add_slot.draw(screen)
        self.btn_del_slot.draw(screen)
        y += 40

        draw_text(screen, "─" * 46, F_ICON, C_BORDER, rx + 20, y)
        y += 10

        # ACTIVE slot heading
        col = POWER_COLORS.get(self.active_key, C_CYAN)
        draw_text(screen, self._human(self.active_key), F_HEAD, col, rx + 20, y)
        y += 26

        # Position readout
        data = self._icon_data()
        px, py = data.get("x", 0), data.get("y", 0)
        draw_text(screen, f"Position — X: {px}  Y: {py}   (Arrow keys nudge)", F_SMALL, C_MUTED, rx + 20, y)
        y += 28

        # Sliders
        self.sld_scale.rect.x   = rx + 20
        self.sld_scale.rect.y   = y
        self.sld_scale.draw(screen)
        y += 46

        self.sld_opacity.rect.x = rx + 20
        self.sld_opacity.rect.y = y
        self.sld_opacity.draw(screen)
        y += 46

        self.sld_cost.rect.x    = rx + 20
        self.sld_cost.rect.y    = y
        self.sld_cost.draw(screen)
        y += 46

        # Resource Type buttons
        draw_text(screen, "Resource Type", F_SMALL, C_MUTED, rx + 20, y)
        y += 18
        rtw = (self.RIGHT_W - 40) // 3
        curr_rt = data.get("resource_type", "stamina")
        for i, rt in enumerate(["stamina", "mana", "none"]):
            b = self.btn_res_types[i]
            b.rect.topleft = (rx + 10 + i * rtw, y)
            b.active = (curr_rt == rt)
            b.draw(screen)
        y += 36

        # Frame style
        draw_text(screen, "Frame Style", F_SMALL, C_MUTED, rx + 20, y)
        y += 18
        fsw = (self.RIGHT_W - 40) // len(FRAME_STYLES)
        for i, st in enumerate(FRAME_STYLES):
            b = self.btn_frame_styles[i]
            b.rect.topleft = (rx + 10 + i * fsw, y)
            b.active = (data.get("frame_style") == st)
            b.draw(screen)
        y += 36

        # Text boxes
        self.tb_keybind.rect.x = rx + 20
        self.tb_keybind.rect.y = y
        self.tb_keybind.draw(screen)
        y += 50

        self.tb_label.rect.x = rx + 20
        self.tb_label.rect.y = y
        self.tb_label.draw(screen)

    def draw_bottom_bar(self):
        by = SH - self.BOT_H
        pg.draw.rect(screen, C_HEADER, (0, by, SW, self.BOT_H))
        pg.draw.line(screen, C_BORDER, (0, by), (SW, by))
        draw_text(screen, "Layout Presets", F_HEAD, C_MUTED,
                  self.LEFT_W + 14, by + 14)
        for b in self.preset_btns:
            b.draw(screen)

    # ══════════════════════════════════════════════════════════════════════════
    #  Event handling
    # ══════════════════════════════════════════════════════════════════════════

    def handle_events(self):
        for ev in pg.event.get():
            if ev.type == pg.QUIT:
                return False

            # Dispatch all button events
            for b in self._get_all_buttons():
                if b.handle(ev):
                    break

            # widgets in right panel & search
            for w in [self.sld_scale, self.sld_opacity, self.tb_keybind, self.tb_label]:
                w.handle(ev)
            self.search_box.handle(ev)

            if ev.type == pg.MOUSEBUTTONDOWN and ev.button == 1:
                mx, my = ev.pos
                self._on_click(mx, my)

            elif ev.type == pg.MOUSEBUTTONUP and ev.button == 1:
                self.drag_key = None

            elif ev.type == pg.MOUSEMOTION and self.drag_key:
                gx, gy = self.v2g(ev.pos[0] - self.drag_off[0],
                                   ev.pos[1] - self.drag_off[1])
                self.config["icons"][self.drag_key]["x"] = gx
                self.config["icons"][self.drag_key]["y"] = gy

            elif ev.type == pg.MOUSEWHEEL:
                mx, my = pg.mouse.get_pos()
                # folder scroll
                if 10 <= mx <= self.LEFT_W - 10 and self.TOP_H + 100 <= my <= self.TOP_H + 300:
                    self.folder_scroll = max(0, min(max(0, len(self.folders) - 5),
                                                    self.folder_scroll - ev.y))
                # gallery scroll
                elif 10 <= mx <= self.LEFT_W - 10 and my > self.TOP_H + 300:
                    cols      = 4
                    max_rows  = max(0, math.ceil(len(self.images) / cols) - 4)
                    self.thumb_scroll = max(0, min(max_rows, self.thumb_scroll - ev.y))
                # right panel slot scroll
                elif mx >= SW - self.RIGHT_W and self.TOP_H <= my <= self.TOP_H + 260:
                    max_slots = max(0, len(self.config["icons"]) - 5)
                    self.slot_scroll = max(0, min(max_slots, self.slot_scroll - ev.y))

            elif ev.type == pg.KEYDOWN and not any(
                    w.active for w in [self.tb_keybind, self.tb_label, self.search_box]):
                self._on_key(ev)

        return True

    def _on_click(self, mx, my):
        # Folder list selection
        folder_y0 = self.TOP_H + 130
        for i in range(5):
            fy = folder_y0 + 4 + i * FOLDER_ROW_H
            if 10 <= mx <= self.LEFT_W - 10 and fy <= my <= fy + FOLDER_ROW_H - 4:
                idx = i + self.folder_scroll
                if 0 <= idx < len(self.folders):
                    self.sel_folder_idx = idx
                    self._load_images()
                return

        # Gallery thumbnail selection
        gallery_y0 = self.TOP_H + 340
        cols = 4
        pad  = 8
        cell = THUMB_SZ + pad
        rows_vis = 4
        gallery_rect = pg.Rect(10, gallery_y0, self.LEFT_W - 20, rows_vis * cell + pad)
        if gallery_rect.collidepoint(mx, my):
            col_i = (mx - gallery_rect.x - pad) // cell
            row_i = (my - gallery_rect.y - pad) // cell + self.thumb_scroll
            idx   = row_i * cols + col_i
            if 0 <= idx < len(self.images):
                self.sel_image = self.images[idx]
            return

        # Slot list selection from rendered rects
        for s_rect, key in self.slot_rects:
            if s_rect.collidepoint(mx, my):
                self.active_key = key
                self._refresh_right_widgets()
                return

        # Viewport drag interaction
        if self.viewport.collidepoint(mx, my):
            for key, data in self.config["icons"].items():
                gx, gy = data.get("x", 0), data.get("y", 0)
                vx, vy = self.g2v(gx, gy)
                w = max(10, int(data.get("width", 56) * data.get("scale", 1.0) * self.sx))
                h = max(10, int(data.get("height", 56) * data.get("scale", 1.0) * self.sy))
                r = pg.Rect(vx - w//2, vy - h//2, w, h)
                if r.collidepoint(mx, my):
                    self.active_key = key
                    self.drag_key   = key
                    self.drag_off   = (mx - vx, my - vy)
                    self._refresh_right_widgets()
                    break

    def _on_key(self, ev):
        icons = self.config["icons"]
        if self.active_key not in icons:
            return
        step = 10 if (pg.key.get_mods() & pg.KMOD_SHIFT) else 2
        if ev.key == pg.K_LEFT:  icons[self.active_key]["x"] -= step
        if ev.key == pg.K_RIGHT: icons[self.active_key]["x"] += step
        if ev.key == pg.K_UP:    icons[self.active_key]["y"] -= step
        if ev.key == pg.K_DOWN:  icons[self.active_key]["y"] += step
        if ev.key == pg.K_s and (pg.key.get_mods() & pg.KMOD_CTRL):
            self.save_config()

    # ══════════════════════════════════════════════════════════════════════════
    #  Main loop
    # ══════════════════════════════════════════════════════════════════════════

    def run(self):
        while True:
            if not self.handle_events():
                break

            screen.fill(C_BG)
            self.draw_topbar()
            self.draw_left_panel()
            self.draw_viewport()
            self.draw_right_panel()
            self.draw_bottom_bar()
            self.toast.draw(screen)

            pg.display.flip()
            clock.tick(60)

        pg.quit()


if __name__ == "__main__":
    PowerIconsEditor().run()
