#!/usr/bin/env python3
"""
popup_controller.py — Pop-up Notification Control System Plugin for Pixel Runner.

Comprehensive, studio-grade GUI control center for designing, editing, theming,
adding, deleting, and muting/enabling in-game pop-up notifications linked to Level 1 scenes,
distances, and entities.

Key Features:
1. True Full-Screen & Auto-Maximize: Fills 100% of the display with responsive multi-resolution layout.
2. Direct Entity Linking & Visualization: Live EntityCatalog parsing level_1.json, showing entity
   names, boss/NPC tiers, distance triggers, and sprite avatar thumbnails.
3. [+ Add Pop-up] Creator: Direct modal workflow to add new pop-ups linked to any entity, distance, or flag.
4. [🗑 Delete Pop-up]: Ability to remove custom or unwanted pop-up notifications.
5. Chronological Timeline: Smooth scrolling via mouse wheel and draggable scrollbar.
6. Unified Rect Architecture: Shared Rect single source of truth guarantees 100% hitbox alignment.
7. Procedural Vector Micro-Icons: Magnifying glass, speaker, floppy disk, play arrow, clock, palette, check, warning, trash, link.
8. Simulated Game Screen: 1280x720 virtual display with live animated SideNotification preview.
9. Reading Pace Telemetry Inspector: Word count, estimated reading time, pace indicator, world trigger context.
10. Atomic Persistence: Saves cleanly via PopupSceneManager and atomic_write_json.
"""

from __future__ import annotations

import json
import math
import os
import sys
import time
from typing import Dict, Any, List, Optional, Tuple

import pygame as pg

# Ensure workspace root is in sys.path
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from src.game.systems.popup_scene_manager import PopupSceneManager
from src.game.systems.notification_config_manager import THEME_PRESETS
from src.game.ui.side_notification import SideNotification, _NotificationItem

# ─────────────────────────────────────────────────────────────────────────────
# Dark Fantasy & Modern Glass Color Palette
# ─────────────────────────────────────────────────────────────────────────────

C_BG = (13, 11, 18)
C_HEADER = (20, 16, 28)
C_HEADER_BORDER = (160, 125, 45)
C_PANEL_BG = (19, 17, 26)
C_PANEL_BORDER = (42, 38, 56)
C_CARD_BG = (25, 22, 34)
C_CARD_HOVER = (33, 29, 44)
C_CARD_ACTIVE = (40, 34, 56)
C_CARD_BORDER = (50, 46, 68)
C_CARD_ACTIVE_BORDER = (255, 215, 80)

C_TEXT_LIGHT = (245, 242, 235)
C_TEXT_MUTED = (155, 150, 170)
C_GOLD = (255, 215, 80)
C_GREEN = (60, 205, 115)
C_RED = (235, 75, 75)
C_CYAN = (0, 220, 255)
C_AMBER = (255, 185, 70)
C_PURPLE = (175, 110, 245)

C_INPUT_BG = (12, 10, 17)
C_INPUT_BORDER = (65, 60, 82)
C_INPUT_FOCUS = (255, 215, 80)


def safe_render_text(font: pg.font.Font, text: str, color: Tuple[int, int, int]) -> pg.Surface:
    """Safely renders text with glyph fallback."""
    try:
        return font.render(text, True, color)
    except Exception:
        try:
            clean = text.encode("ascii", "replace").decode("ascii")
            return font.render(clean, True, color)
        except Exception:
            fallback = pg.font.SysFont("Arial", font.get_height())
            return fallback.render(text, True, color)


# ─────────────────────────────────────────────────────────────────────────────
# Procedural Vector Micro-Icons (Zero missing glyph tofu boxes)
# ─────────────────────────────────────────────────────────────────────────────

def draw_icon_search(surf: pg.Surface, x: int, y: int, color: Tuple[int, int, int]) -> None:
    """Renders a sharp magnifying glass icon."""
    pg.draw.circle(surf, color, (x + 5, y + 5), 4, 1)
    pg.draw.line(surf, color, (x + 8, y + 8), (x + 12, y + 12), 2)


def draw_icon_speaker(surf: pg.Surface, x: int, y: int, color: Tuple[int, int, int], muted: bool = False) -> None:
    """Renders a speaker icon with sound waves or mute 'x'."""
    pts = [(x, y + 4), (x + 3, y + 4), (x + 7, y + 1), (x + 7, y + 11), (x + 3, y + 8), (x, y + 8)]
    pg.draw.polygon(surf, color, pts)
    if muted:
        pg.draw.line(surf, color, (x + 10, y + 3), (x + 14, y + 9), 2)
        pg.draw.line(surf, color, (x + 14, y + 3), (x + 10, y + 9), 2)
    else:
        pg.draw.arc(surf, color, pg.Rect(x + 6, y + 2, 6, 8), -math.pi / 2.5, math.pi / 2.5, 1)
        pg.draw.arc(surf, color, pg.Rect(x + 9, y + 0, 7, 12), -math.pi / 2.5, math.pi / 2.5, 1)


def draw_icon_disk(surf: pg.Surface, x: int, y: int, color: Tuple[int, int, int]) -> None:
    """Renders a 14x14 floppy disk save icon."""
    pg.draw.rect(surf, color, pg.Rect(x, y, 14, 14), 1, border_radius=1)
    pg.draw.rect(surf, color, pg.Rect(x + 3, y, 6, 5))
    pg.draw.rect(surf, color, pg.Rect(x + 2, y + 7, 10, 6), 1)


def draw_icon_play(surf: pg.Surface, x: int, y: int, color: Tuple[int, int, int]) -> None:
    """Renders a sharp play triangle icon."""
    pts = [(x, y), (x + 10, y + 6), (x, y + 12)]
    pg.draw.polygon(surf, color, pts)


def draw_icon_clock(surf: pg.Surface, x: int, y: int, color: Tuple[int, int, int]) -> None:
    """Renders a minimal clock icon."""
    cx, cy = x + 5, y + 5
    pg.draw.circle(surf, color, (cx, cy), 5, 1)
    pg.draw.line(surf, color, (cx, cy), (cx, cy - 3), 1)
    pg.draw.line(surf, color, (cx, cy), (cx + 3, cy), 1)


def draw_icon_palette(surf: pg.Surface, x: int, y: int, color: Tuple[int, int, int]) -> None:
    """Renders a mini color-tag / swatch indicator."""
    pg.draw.circle(surf, (255, 110, 110), (x + 3, y + 5), 3)
    pg.draw.circle(surf, (100, 220, 120), (x + 8, y + 5), 3)
    pg.draw.circle(surf, (100, 180, 255), (x + 13, y + 5), 3)


def draw_icon_check(surf: pg.Surface, x: int, y: int, color: Tuple[int, int, int]) -> None:
    """Renders an anti-aliased checkmark."""
    pg.draw.line(surf, color, (x, y + 5), (x + 4, y + 9), 2)
    pg.draw.line(surf, color, (x + 4, y + 9), (x + 11, y + 2), 2)


def draw_icon_warning(surf: pg.Surface, x: int, y: int, color: Tuple[int, int, int]) -> None:
    """Renders an alert triangle."""
    pts = [(x + 6, y), (x, y + 11), (x + 12, y + 11)]
    pg.draw.polygon(surf, color, pts, width=1)
    pg.draw.line(surf, color, (x + 6, y + 4), (x + 6, y + 7), 1)
    pg.draw.circle(surf, color, (x + 6, y + 9), 1)


def draw_icon_plus(surf: pg.Surface, x: int, y: int, color: Tuple[int, int, int]) -> None:
    """Renders a clean plus sign for addition."""
    pg.draw.line(surf, color, (x, y + 5), (x + 10, y + 5), 2)
    pg.draw.line(surf, color, (x + 5, y), (x + 5, y + 10), 2)


def draw_icon_trash(surf: pg.Surface, x: int, y: int, color: Tuple[int, int, int]) -> None:
    """Renders a delete / trash icon."""
    pg.draw.rect(surf, color, pg.Rect(x + 2, y + 4, 8, 8), 1, border_radius=1)
    pg.draw.line(surf, color, (x, y + 3), (x + 12, y + 3), 1)
    pg.draw.line(surf, color, (x + 4, y + 1), (x + 8, y + 1), 1)


def draw_icon_link(surf: pg.Surface, x: int, y: int, color: Tuple[int, int, int]) -> None:
    """Renders an interlocking link icon."""
    pg.draw.rect(surf, color, pg.Rect(x, y + 2, 7, 5), 1, border_radius=2)
    pg.draw.rect(surf, color, pg.Rect(x + 4, y + 4, 7, 5), 1, border_radius=2)


def draw_styled_button(
    surf: pg.Surface,
    rect: pg.Rect,
    text: str,
    font: pg.font.Font,
    text_color: Tuple[int, int, int],
    bg_color: Tuple[int, int, int],
    border_color: Tuple[int, int, int],
    hover_bg: Optional[Tuple[int, int, int]] = None,
    hover_border: Optional[Tuple[int, int, int]] = None,
    border_radius: int = 6,
    border_width: int = 1,
    icon_type: Optional[str] = None,
    icon_color: Optional[Tuple[int, int, int]] = None,
) -> bool:
    """
    Renders an interactive button with smooth hover feedback, anti-aliased border,
    and optional micro-icon. Returns True if mouse is currently hovering.
    """
    mx, my = pg.mouse.get_pos()
    is_hover = rect.collidepoint(mx, my)

    final_bg = hover_bg if (is_hover and hover_bg) else bg_color
    final_border = hover_border if (is_hover and hover_border) else border_color
    final_text_col = (255, 255, 255) if is_hover else text_color

    # Draw button background and border
    pg.draw.rect(surf, final_bg, rect, border_radius=border_radius)
    pg.draw.rect(surf, final_border, rect, width=border_width, border_radius=border_radius)

    # Calculate content width
    t_surf = safe_render_text(font, text, final_text_col)
    has_icon = icon_type is not None
    icon_w = 14 if has_icon else 0
    gap = 8 if has_icon else 0
    total_w = icon_w + gap + t_surf.get_width()

    start_x = rect.centerx - total_w // 2
    if has_icon:
        ic_col = icon_color or final_text_col
        ic_y = rect.centery - 6
        if icon_type == "plus":
            draw_icon_plus(surf, start_x, ic_y + 1, ic_col)
        elif icon_type == "disk":
            draw_icon_disk(surf, start_x, ic_y - 1, ic_col)
        elif icon_type == "speaker_mute":
            draw_icon_speaker(surf, start_x, ic_y, ic_col, muted=True)
        elif icon_type == "speaker_unmute":
            draw_icon_speaker(surf, start_x, ic_y, ic_col, muted=False)
        elif icon_type == "play":
            draw_icon_play(surf, start_x, ic_y, ic_col)
        elif icon_type == "trash":
            draw_icon_trash(surf, start_x, ic_y, ic_col)
        elif icon_type == "check":
            draw_icon_check(surf, start_x, ic_y, ic_col)
        elif icon_type == "link":
            draw_icon_link(surf, start_x, ic_y, ic_col)

    surf.blit(t_surf, (start_x + icon_w + gap, rect.centery - t_surf.get_height() // 2))
    return is_hover


# ─────────────────────────────────────────────────────────────────────────────
# EntityCatalog — Live Level 1 Entity Metadata & Avatar Thumbnails
# ─────────────────────────────────────────────────────────────────────────────

class EntityCatalog:
    """Live catalog of Level 1 entities from game_data/level_1.json."""

    def __init__(self, level_path: str = "game_data/level_1.json") -> None:
        self.level_path = level_path
        self.entities: Dict[int, Dict[str, Any]] = {}
        self.avatar_cache: Dict[int, pg.Surface] = {}
        self.load()

    def load(self) -> None:
        if not os.path.exists(self.level_path):
            return
        try:
            with open(self.level_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            events = data.get("world_events", [])
            for ev in events:
                eid = ev.get("id")
                if eid is None:
                    continue
                p = ev.get("params", {})
                title = p.get("title", f"Entity #{eid}")
                etype = ev.get("type", "entity")
                dist = ev.get("distance", 0)
                sprite_dir = p.get("sprite_dir", "")
                tier = p.get("tier", "npc" if etype == "npc" else "standard")
                health = p.get("health")
                self.entities[int(eid)] = {
                    "id": int(eid),
                    "title": title,
                    "type": etype,
                    "tier": tier,
                    "distance": dist,
                    "sprite_dir": sprite_dir,
                    "health": health,
                    "description": p.get("text", "Level 1 game entity"),
                }
        except Exception as e:
            print(f"[EntityCatalog] Error loading {self.level_path}: {e}")

    def get_entity(self, eid: Any) -> Optional[Dict[str, Any]]:
        if eid is None:
            return None
        try:
            return self.entities.get(int(eid))
        except (ValueError, TypeError):
            return None

    def get_all_entities(self) -> List[Dict[str, Any]]:
        return sorted(self.entities.values(), key=lambda e: float(e.get("distance", 0)))

    def get_nearest_entity(self, distance: float) -> Optional[Dict[str, Any]]:
        if not self.entities:
            return None
        return min(self.entities.values(), key=lambda e: abs(float(e.get("distance", 0)) - distance))

    def _find_image_recursive(self, path: str) -> Optional[str]:
        if not path:
            return None
        if os.path.isfile(path) and path.lower().endswith((".png", ".jpg")):
            return path
        if os.path.isdir(path):
            for root, _, files in os.walk(path):
                for f in sorted(files):
                    if f.lower().endswith((".png", ".jpg")):
                        return os.path.join(root, f)
        return None

    def get_avatar_surface(self, eid: Any, size: Tuple[int, int] = (44, 44)) -> pg.Surface:
        if eid is None:
            surf = pg.Surface(size, pg.SRCALPHA)
            pg.draw.rect(surf, (30, 26, 40), (0, 0, size[0], size[1]), border_radius=6)
            return surf
        try:
            int_eid = int(eid)
        except (ValueError, TypeError):
            int_eid = -1

        if int_eid in self.avatar_cache:
            return self.avatar_cache[int_eid]

        surf = pg.Surface(size, pg.SRCALPHA)
        pg.draw.rect(surf, (30, 26, 40), (0, 0, size[0], size[1]), border_radius=6)
        pg.draw.rect(surf, (150, 120, 60), (0, 0, size[0], size[1]), width=1, border_radius=6)

        ent = self.get_entity(eid)
        img_loaded = False
        if ent and ent.get("sprite_dir"):
            img_path = self._find_image_recursive(ent["sprite_dir"])
            if img_path:
                try:
                    loaded = pg.image.load(img_path).convert_alpha()
                    scaled = pg.transform.smoothscale(loaded, (size[0] - 8, size[1] - 8))
                    surf.blit(scaled, (4, 4))
                    img_loaded = True
                except Exception:
                    pass

        if not img_loaded:
            # Procedural pixel-art icon fallback based on tier
            tier = ent.get("tier", "standard").lower() if ent else "standard"
            cx, cy = size[0] // 2, size[1] // 2
            if tier == "boss" or (ent and "boss" in ent.get("title", "").lower()):
                pg.draw.circle(surf, (220, 50, 60), (cx, cy), size[0] // 3)
                pg.draw.circle(surf, (255, 200, 200), (cx - 4, cy - 2), 2)
                pg.draw.circle(surf, (255, 200, 200), (cx + 4, cy - 2), 2)
            elif tier == "npc":
                pg.draw.rect(surf, (180, 140, 50), (cx - 8, cy - 8, 16, 16), border_radius=3)
                pg.draw.line(surf, (255, 230, 140), (cx - 4, cy), (cx + 4, cy), 2)
            else:
                pg.draw.circle(surf, (100, 140, 220), (cx, cy), size[0] // 3)

        self.avatar_cache[int_eid] = surf
        return surf


# ─────────────────────────────────────────────────────────────────────────────
# PopupControllerApp — Core Interactive Plugin Engine
# ─────────────────────────────────────────────────────────────────────────────

class PopupControllerApp:
    def __init__(self) -> None:
        pg.init()
        pg.font.init()

        os.environ["SDL_VIDEO_CENTERED"] = "1"
        self.width = 1440
        self.height = 880
        self.screen = pg.display.set_mode((self.width, self.height), pg.RESIZABLE)
        pg.display.set_caption("Pixel Runner — Pop-up Notification Control System")

        # Auto-maximize window on desktop like main.py
        try:
            win = pg.Window.from_display_module()
            win.maximize()
            self.width, self.height = self.screen.get_size()
        except Exception:
            pass

        self.clock = pg.time.Clock()
        self.running = True

        # High-Legibility Typography System
        self.font_brand = self._load_font("assets/font/Abaddon Bold.ttf", 23, bold=True)
        self.font_heading = self._load_font("assets/font/Abaddon Bold.ttf", 17, bold=True)
        self.font_subheading = self._load_font("assets/font/Abaddon Bold.ttf", 15, bold=True)

        self.font_ui = self._load_sys_font(["Segoe UI", "Arial", "Helvetica"], 14)
        self.font_ui_bold = self._load_sys_font(["Segoe UI", "Arial", "Helvetica"], 14, bold=True)
        self.font_ui_large = self._load_sys_font(["Segoe UI", "Arial", "Helvetica"], 15, bold=True)
        self.font_small = self._load_sys_font(["Segoe UI", "Arial", "Helvetica"], 12)
        self.font_small_bold = self._load_sys_font(["Segoe UI", "Arial", "Helvetica"], 12, bold=True)
        self.font_mono = self._load_sys_font(["Consolas", "Courier New"], 12)

        # Entity Catalog
        self.catalog = EntityCatalog(os.path.join(BASE_DIR, "game_data", "level_1.json"))

        # Systems & Pop-up Config
        self.manager = PopupSceneManager.get_instance()
        self.scenes: List[Dict[str, Any]] = self.manager.get_all_popups()
        self.scenes.sort(key=lambda s: float(s.get("distance", 0)))
        self.selected_index: int = 0 if self.scenes else -1

        # Timeline Layout & Scrolling
        self.scroll_y: float = 0.0
        self.max_scroll: float = 0.0
        self.timeline_item_h = 92
        self.is_dragging_scrollbar = False

        # Dynamic layout metrics
        self._update_layout()

        # Active Field Editing
        self.active_field: Optional[str] = None  # "title", "text", "search"
        self.edit_title_str: str = ""
        self.edit_text_str: str = ""
        self.search_query: str = ""
        self.cursor_blink_time: float = 0.0

        # Live Preview System
        self.preview_notification = SideNotification(1280, 720)
        self.is_preview_animating: bool = False
        self.preview_timer: float = 0.0

        # UI Feedback Toast
        self.toast_msg: str = ""
        self.toast_time: float = 0.0
        self.toast_color: Tuple[int, int, int] = C_GREEN

        # Filter Tabs
        self.filter_tab: str = "ALL"  # ALL, DISTANCE, ENTITY, FLAG, MUTED

        # Theme metadata dictionary
        self.theme_meta = {
            "gothic_gold": {
                "label": "Gothic Gold",
                "sub": "Obsidian & Antique Gold",
                "desc": "Classic Dark Fantasy HUD aesthetic",
            },
            "blood_bone": {
                "label": "Blood & Bone",
                "sub": "Crimson Gore & Polished Bone",
                "desc": "Designed for Blood Zombie & necrotic events",
            },
            "arcane_void": {
                "label": "Arcane Void",
                "sub": "Cyan Starlight & Void Navy",
                "desc": "Designed for Demon Time & celestial relics",
            },
            "grimoire_leather": {
                "label": "Grimoire Leather",
                "sub": "Bound Leather & Amber Runes",
                "desc": "Designed for the Sealed Book & ancient tomes",
            },
            "clean_minimalist": {
                "label": "Sleek Dark Glass",
                "sub": "Modern Charcoal & Silver Frost",
                "desc": "Minimalist high-contrast HUD aesthetic",
            },
        }

        # [+ Add Pop-up] Modal State
        self.show_add_modal: bool = False
        self.add_trigger_type: str = "entity"  # "entity", "distance", "flag"
        self.add_selected_entity_id: int = 14
        self.add_distance_val: float = 1400.0
        self.add_flag_str: str = "first_encounter"
        self.add_title_str: str = "New Pop-up"
        self.add_text_str: str = "Enter pop-up notification message here."
        self.add_theme_str: str = "blood_bone"
        self.add_hold_val: float = 7.0
        self.add_active_input: Optional[str] = None  # "title", "text", "dist", "flag"

        # Entity Picker Dropdown State
        self.show_entity_picker: bool = False

        # Select initial scene
        if self.selected_index >= 0:
            self._select_scene(self.selected_index)

    def _update_layout(self) -> None:
        """Dynamically computes 3-column responsive layout based on window width and height."""
        self.timeline_w = max(400, min(470, int(self.width * 0.28)))
        self.pv_w = max(430, min(520, int(self.width * 0.31)))
        self.pv_x = self.width - self.pv_w - 12
        self.ed_x = self.timeline_w + 16
        self.ed_w = self.pv_x - self.ed_x - 12
        self.panels_h = self.height - 114

    # ─────────────────────────────────────────────────────────────────────────
    # Single Source of Truth: Layout Rect Calculation Methods
    # ─────────────────────────────────────────────────────────────────────────

    def _get_header_rects(self) -> Dict[str, pg.Rect]:
        """Calculates exact hitboxes for top navigation bar elements."""
        x_save = self.width - 175
        x_unmute = x_save - 118
        x_mute = x_unmute - 108
        x_add = x_mute - 156
        x_stat = x_add - 198
        return {
            "save": pg.Rect(x_save, 10, 165, 38),
            "unmute_all": pg.Rect(x_unmute, 12, 108, 34),
            "mute_all": pg.Rect(x_mute, 12, 98, 34),
            "add_popup": pg.Rect(x_add, 12, 146, 34),
            "status": pg.Rect(x_stat, 12, 188, 34),
        }

    def _get_filter_rects(self) -> Tuple[pg.Rect, List[Tuple[str, pg.Rect]]]:
        """Calculates exact hitboxes for filter bar tabs and search box."""
        srch = pg.Rect(14, 65, 175, 26)
        tab_list = [("ALL", 205, 55), ("DISTANCE", 268, 85), ("ENTITY", 361, 80), ("FLAG", 449, 75), ("MUTED", 532, 75)]
        tabs = [(name, pg.Rect(x, 66, w, 24)) for name, x, w in tab_list]
        return srch, tabs

    def _get_editor_rects(self, scene: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculates exact hitboxes for center editor controls."""
        if not scene:
            return {}
        ed_x = self.ed_x
        ed_w = self.ed_w
        tt = scene.get("trigger_type", "")
        rects: Dict[str, Any] = {
            "toggle_enabled": pg.Rect(ed_x + ed_w - 230, 114, 215, 32),
            "ent_card": pg.Rect(ed_x + 18, 162, ed_w - 36, 56),
            "title_box": pg.Rect(ed_x + 18, 246, ed_w - 36, 34),
            "text_box": pg.Rect(ed_x + 18, 308, ed_w - 36, 110),
            "dur_minus": pg.Rect(ed_x + 140, 428, 45, 28),
            "dur_val": pg.Rect(ed_x + 195, 428, 60, 28),
            "dur_plus": pg.Rect(ed_x + 265, 428, 45, 28),
            "del_btn": pg.Rect(ed_x + ed_w - 145, 428, 127, 28),
            "theme_tiles": {},
        }
        if tt == "entity":
            rects["switch_entity"] = pg.Rect(ed_x + ed_w - 170, 176, 140, 28)
        elif tt == "distance":
            rects["dist_minus"] = pg.Rect(ed_x + ed_w - 140, 176, 40, 26)
            rects["dist_plus"] = pg.Rect(ed_x + ed_w - 46, 176, 40, 26)

        theme_keys = list(THEME_PRESETS.keys())
        tile_w = (ed_w - 46) // 2
        tile_h = 66
        tile_gap = 10
        for idx, t_key in enumerate(theme_keys):
            row = idx // 2
            col = idx % 2
            tx = ed_x + 18 + col * (tile_w + tile_gap)
            ty = 494 + row * (tile_h + tile_gap)
            rects["theme_tiles"][t_key] = pg.Rect(tx, ty, tile_w, tile_h)
        return rects

    def _get_add_modal_rects(self) -> Dict[str, Any]:
        """Calculates exact hitboxes for [+ Add Pop-up] modal dialog."""
        mw, mh = 760, 630
        mx0 = self.width // 2 - mw // 2
        my0 = self.height // 2 - mh // 2

        rects: Dict[str, Any] = {
            "modal": pg.Rect(mx0, my0, mw, mh),
            "close": pg.Rect(mx0 + mw - 42, my0 + 16, 28, 28),
            "cancel": pg.Rect(mx0 + mw - 250, my0 + mh - 50, 110, 36),
            "confirm": pg.Rect(mx0 + mw - 130, my0 + mh - 50, 115, 36),
            "tabs": {
                "entity": pg.Rect(mx0 + 24, my0 + 64, 226, 32),
                "distance": pg.Rect(mx0 + 258, my0 + 64, 226, 32),
                "flag": pg.Rect(mx0 + 492, my0 + 64, 244, 32),
            },
            "entity_cards": [],
            "dist_presets": [],
            "dist_steppers": [],
            "flag_chips": [],
            "title_input": pg.Rect(mx0 + 24, my0 + 346, mw - 48, 34),
            "text_input": pg.Rect(mx0 + 24, my0 + 410, mw - 48, 64),
            "theme_chips": {},
            "hold_minus": pg.Rect(mx0 + mw - 150, my0 + mh - 112, 36, 26),
            "hold_plus": pg.Rect(mx0 + mw - 60, my0 + mh - 112, 36, 26),
        }

        # Step 2 Target Geometry
        if self.add_trigger_type == "entity":
            all_ents = self.catalog.get_all_entities()
            ey = my0 + 124
            for ent in all_ents[:5]:
                rects["entity_cards"].append((ent["id"], pg.Rect(mx0 + 24, ey, mw - 48, 36)))
                ey += 40
        elif self.add_trigger_type == "distance":
            rects["dist_box"] = pg.Rect(mx0 + 24, my0 + 128, 170, 34)
            st_x = mx0 + 205
            for delta in [-500, -100, 100, 500]:
                rects["dist_steppers"].append((delta, pg.Rect(st_x, my0 + 128, 68, 34)))
                st_x += 74
            px = mx0 + 24
            py = my0 + 172
            for p_dist, _ in [
                (0, "0m"),
                (650, "650m"),
                (1400, "1,400m"),
                (2558, "2,558m"),
                (12500, "12,500m"),
                (34500, "34,500m"),
            ]:
                pw = 110
                rects["dist_presets"].append((p_dist, pg.Rect(px, py, pw, 28)))
                px += pw + 8
        else:  # flag
            rects["flag_box"] = pg.Rect(mx0 + 24, my0 + 128, 260, 34)
            chips = ["first_encounter", "first_kill", "demon_time_ready", "relic_unlocked", "boss_defeated", "near_death"]
            fx = mx0 + 24
            fy = my0 + 172
            for fc in chips:
                fw = self.font_small_bold.size(fc)[0] + 20
                if fx + fw > mx0 + mw - 24:
                    fx = mx0 + 24
                    fy += 32
                rects["flag_chips"].append((fc, pg.Rect(fx, fy, fw, 26)))
                fx += fw + 8

        # Theme chips
        tkeys = list(THEME_PRESETS.keys())
        tx = mx0 + 24
        ty = my0 + 504
        for tk in tkeys:
            rects["theme_chips"][tk] = pg.Rect(tx, ty, 136, 28)
            tx += 144

        return rects

    def _load_font(self, font_path: str, size: int, bold: bool = False) -> pg.font.Font:
        full_path = os.path.join(BASE_DIR, font_path)
        if os.path.exists(full_path):
            try:
                return pg.font.Font(full_path, size)
            except Exception:
                pass
        return pg.font.SysFont("Arial", size, bold=bold)

    def _load_sys_font(self, font_names: List[str], size: int, bold: bool = False) -> pg.font.Font:
        for name in font_names:
            try:
                f = pg.font.SysFont(name, size, bold=bold)
                if f:
                    return f
            except Exception:
                pass
        return pg.font.SysFont("Arial", size, bold=bold)

    def _select_scene(self, index: int) -> None:
        filtered = self._get_filtered_scenes()
        if 0 <= index < len(filtered):
            scene = filtered[index]
            real_idx = self.scenes.index(scene)
            self.selected_index = real_idx
            self.edit_title_str = str(scene.get("title", ""))
            self.edit_text_str = str(scene.get("text", ""))
            self.active_field = None
            self.show_entity_picker = False
            self._trigger_preview()

    def _get_selected_scene(self) -> Optional[Dict[str, Any]]:
        if 0 <= self.selected_index < len(self.scenes):
            return self.scenes[self.selected_index]
        return None

    def _get_filtered_scenes(self) -> List[Dict[str, Any]]:
        q = self.search_query.lower().strip()
        result = []
        for s in self.scenes:
            tt = s.get("trigger_type", "")
            if self.filter_tab == "DISTANCE" and tt != "distance":
                continue
            elif self.filter_tab == "ENTITY" and tt != "entity":
                continue
            elif self.filter_tab == "FLAG" and tt != "flag":
                continue
            elif self.filter_tab == "MUTED" and s.get("enabled", True):
                continue

            if q:
                title = str(s.get("title", "")).lower()
                text = str(s.get("text", "")).lower()
                sid = str(s.get("id", "")).lower()
                eid = str(s.get("entity_id", ""))
                ent = self.catalog.get_entity(s.get("entity_id", -1))
                ent_name = ent.get("title", "").lower() if ent else ""
                if q not in title and q not in text and q not in sid and q not in eid and q not in ent_name:
                    continue
            result.append(s)
        return result

    def _trigger_preview(self) -> None:
        """Trigger an instant preview of the active notification."""
        scene = self._get_selected_scene()
        if not scene:
            return

        self.preview_notification = SideNotification(1280, 720)
        self.preview_notification.show(
            text=self.edit_text_str or scene.get("text", ""),
            title=self.edit_title_str or scene.get("title", "Notification"),
            icon=scene.get("icon"),
            hold=float(scene.get("hold", 6.0)),
            theme=scene.get("theme", "gothic_gold"),
        )
        self.is_preview_animating = True
        self.preview_timer = 0.0

    def _save_changes(self) -> None:
        """Save current edit buffers into scene and persist atomically."""
        scene = self._get_selected_scene()
        if not scene:
            return

        scene["title"] = self.edit_title_str
        scene["text"] = self.edit_text_str

        success = self.manager.save_config()
        if success:
            self.toast_msg = "Config saved successfully! Pop-ups updated in running game."
            self.toast_color = C_GREEN
        else:
            self.toast_msg = "Error saving config file!"
            self.toast_color = C_RED
        self.toast_time = 3.5

    def _set_theme(self, theme_key: str) -> None:
        scene = self._get_selected_scene()
        if scene and theme_key in THEME_PRESETS:
            scene["theme"] = theme_key
            self._trigger_preview()

    def _toggle_enabled(self, scene: Dict[str, Any]) -> None:
        scene["enabled"] = not scene.get("enabled", True)
        self._trigger_preview()

    def _mute_all(self, enabled: bool) -> None:
        for s in self.scenes:
            s["enabled"] = enabled
        self._save_changes()

    def _open_add_modal(self) -> None:
        self.show_add_modal = True
        self.add_trigger_type = "entity"
        self.add_selected_entity_id = 14
        ent = self.catalog.get_entity(14)
        self.add_title_str = ent.get("title", "New Pop-up") if ent else "New Pop-up"
        self.add_text_str = "A powerful entity blocks your advance. Steel your resolve."
        self.add_theme_str = "blood_bone"
        self.add_hold_val = 7.0
        self.add_active_input = None

    def _close_add_modal(self) -> None:
        self.show_add_modal = False
        self.add_active_input = None

    def _confirm_add_popup(self) -> None:
        """Instantiate new pop-up scene, persist via manager, and focus it."""
        sid = f"event_{self.add_trigger_type}_{int(time.time())}"
        new_scene: Dict[str, Any] = {
            "id": sid,
            "title": self.add_title_str.strip() or "Untitled Pop-up",
            "text": self.add_text_str.strip() or "Notification message.",
            "trigger_type": self.add_trigger_type,
            "theme": self.add_theme_str,
            "hold": self.add_hold_val,
            "enabled": True,
        }

        if self.add_trigger_type == "entity":
            new_scene["entity_id"] = self.add_selected_entity_id
            ent = self.catalog.get_entity(self.add_selected_entity_id)
            new_scene["distance"] = ent.get("distance", 0) if ent else 0
            new_scene["description"] = f"Encounter with {ent.get('title', 'entity')}" if ent else "Entity encounter"
        elif self.add_trigger_type == "distance":
            new_scene["distance"] = float(self.add_distance_val)
            new_scene["description"] = f"World milestone at {int(self.add_distance_val)}m"
        else:
            new_scene["flag"] = self.add_flag_str.strip() or "custom_flag"
            new_scene["distance"] = 0
            new_scene["description"] = f"Event triggered by flag: {new_scene['flag']}"

        self.manager.add_popup(new_scene)
        self.scenes = self.manager.get_all_popups()
        self.scenes.sort(key=lambda s: float(s.get("distance", 0)))

        # Select newly created scene
        for i, s in enumerate(self.scenes):
            if s.get("id") == sid:
                self.selected_index = i
                break
        self._select_scene(self.selected_index)

        self.toast_msg = "New pop-up created and saved!"
        self.toast_color = C_GREEN
        self.toast_time = 3.5
        self.show_add_modal = False

    def _delete_current_popup(self) -> None:
        """Remove currently selected pop-up."""
        scene = self._get_selected_scene()
        if not scene:
            return
        sid = scene.get("id", "")
        self.manager.delete_popup(sid)
        self.scenes = self.manager.get_all_popups()
        self.scenes.sort(key=lambda s: float(s.get("distance", 0)))
        self.selected_index = max(0, min(self.selected_index, len(self.scenes) - 1))
        if self.scenes:
            self._select_scene(self.selected_index)
        self.toast_msg = f"Deleted pop-up '{sid}'."
        self.toast_color = C_AMBER
        self.toast_time = 3.5

    def _link_entity(self, eid: int) -> None:
        """Link currently selected scene to an entity."""
        scene = self._get_selected_scene()
        if not scene:
            return
        ent = self.catalog.get_entity(eid)
        if not ent:
            return
        scene["trigger_type"] = "entity"
        scene["entity_id"] = eid
        scene["distance"] = ent.get("distance", scene.get("distance", 0))
        scene["description"] = f"Encounter with {ent.get('title', 'entity')}"
        self.show_entity_picker = False
        self._trigger_preview()
        self.toast_msg = f"Linked to {ent.get('title')} (#{eid})!"
        self.toast_color = C_GREEN
        self.toast_time = 3.0

    # ─────────────────────────────────────────────────────────────────────────
    # Event Handling
    # ─────────────────────────────────────────────────────────────────────────

    def handle_events(self) -> None:
        for event in pg.event.get():
            if event.type == pg.QUIT:
                self.running = False
                return

            elif event.type == pg.VIDEORESIZE:
                self.width = max(1100, event.w)
                self.height = max(700, event.h)
                self.screen = pg.display.set_mode((self.width, self.height), pg.RESIZABLE)
                self._update_layout()

            elif event.type == pg.KEYDOWN:
                if event.key == pg.K_s and (event.mod & pg.KMOD_CTRL):
                    self._save_changes()
                    continue

                if self.show_add_modal:
                    if event.key == pg.K_ESCAPE:
                        self._close_add_modal()
                    elif self.add_active_input == "title":
                        if event.key in (pg.K_RETURN, pg.K_ESCAPE):
                            self.add_active_input = None
                        elif event.key == pg.K_BACKSPACE:
                            self.add_title_str = self.add_title_str[:-1]
                        elif event.unicode and len(self.add_title_str) < 60:
                            self.add_title_str += event.unicode
                    elif self.add_active_input == "text":
                        if event.key == pg.K_ESCAPE:
                            self.add_active_input = None
                        elif event.key == pg.K_BACKSPACE:
                            self.add_text_str = self.add_text_str[:-1]
                        elif event.key == pg.K_RETURN:
                            self.add_text_str += "\n"
                        elif event.unicode:
                            self.add_text_str += event.unicode
                    elif self.add_active_input == "dist":
                        if event.key in (pg.K_RETURN, pg.K_ESCAPE):
                            self.add_active_input = None
                        elif event.key == pg.K_BACKSPACE:
                            self.add_distance_val = float(str(int(self.add_distance_val))[:-1] or 0)
                        elif event.unicode.isdigit():
                            self.add_distance_val = float(f"{int(self.add_distance_val)}{event.unicode}")
                    elif self.add_active_input == "flag":
                        if event.key in (pg.K_RETURN, pg.K_ESCAPE):
                            self.add_active_input = None
                        elif event.key == pg.K_BACKSPACE:
                            self.add_flag_str = self.add_flag_str[:-1]
                        elif event.unicode and len(self.add_flag_str) < 30:
                            self.add_flag_str += event.unicode
                    continue

                if self.active_field == "search":
                    if event.key in (pg.K_RETURN, pg.K_ESCAPE):
                        self.active_field = None
                    elif event.key == pg.K_BACKSPACE:
                        self.search_query = self.search_query[:-1]
                    elif event.unicode and len(self.search_query) < 30:
                        self.search_query += event.unicode

                elif self.active_field == "title":
                    if event.key in (pg.K_RETURN, pg.K_ESCAPE):
                        self.active_field = None
                    elif event.key == pg.K_BACKSPACE:
                        self.edit_title_str = self.edit_title_str[:-1]
                        self._trigger_preview()
                    else:
                        if event.unicode and len(self.edit_title_str) < 60:
                            self.edit_title_str += event.unicode
                            self._trigger_preview()

                elif self.active_field == "text":
                    if event.key == pg.K_ESCAPE:
                        self.active_field = None
                    elif event.key == pg.K_BACKSPACE:
                        self.edit_text_str = self.edit_text_str[:-1]
                        self._trigger_preview()
                    elif event.key == pg.K_RETURN:
                        self.edit_text_str += "\n"
                        self._trigger_preview()
                    else:
                        if event.unicode:
                            self.edit_text_str += event.unicode
                            self._trigger_preview()

            elif event.type == pg.MOUSEWHEEL:
                mx, my = pg.mouse.get_pos()
                if mx < self.timeline_w:
                    self.scroll_y -= event.y * 36
                    self.scroll_y = max(0.0, min(self.max_scroll, self.scroll_y))

            elif event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
                self._handle_click(event.pos)

            elif event.type == pg.MOUSEBUTTONUP and event.button == 1:
                self.is_dragging_scrollbar = False

            elif event.type == pg.MOUSEMOTION:
                if self.is_dragging_scrollbar and self.max_scroll > 0:
                    my = event.pos[1]
                    track_h = self.panels_h - 20
                    rel_y = max(0, min(track_h, my - 118))
                    self.scroll_y = (rel_y / track_h) * self.max_scroll

    def _handle_click(self, pos: Tuple[int, int]) -> None:
        mx, my = pos

        # If Add Modal is active, intercept clicks
        if self.show_add_modal:
            self._handle_add_modal_click(pos)
            return

        # If Entity Picker is active, intercept clicks
        if self.show_entity_picker:
            if self._handle_entity_picker_click(pos):
                return

        # 1. Header Buttons via unified rects
        hdr_rects = self._get_header_rects()
        if hdr_rects["save"].collidepoint(mx, my):
            self._save_changes()
            return

        if hdr_rects["mute_all"].collidepoint(mx, my):
            self._mute_all(False)
            return

        if hdr_rects["unmute_all"].collidepoint(mx, my):
            self._mute_all(True)
            return

        if hdr_rects["add_popup"].collidepoint(mx, my):
            self._open_add_modal()
            return

        # 2. Filter Bar via unified rects
        srch_box, tab_rects = self._get_filter_rects()
        if srch_box.collidepoint(mx, my):
            self.active_field = "search"
            return

        for tab_name, tab_rect in tab_rects:
            if tab_rect.collidepoint(mx, my):
                self.filter_tab = tab_name
                self.selected_index = 0
                self._select_scene(0)
                return

        # 3. Timeline Item Click, Scrollbar Drag & Inline Toggle
        if 10 <= mx <= self.timeline_w and my >= 105:
            sb_x = self.timeline_w - 6
            if mx >= sb_x - 4:
                self.is_dragging_scrollbar = True
                return

            rel_y = my - 108 + self.scroll_y
            item_idx = int(rel_y // (self.timeline_item_h + 8))
            filtered = self._get_filtered_scenes()
            if 0 <= item_idx < len(filtered):
                clicked_scene = filtered[item_idx]
                card_top = 108 + item_idx * (self.timeline_item_h + 8) - self.scroll_y
                card_rect = pg.Rect(16, card_top, self.timeline_w - 24, self.timeline_item_h)

                # Check if click landed on the toggle pill
                tog_rect = pg.Rect(card_rect.right - 80, card_rect.y + 10, 72, 22)
                if tog_rect.collidepoint(mx, my):
                    self._toggle_enabled(clicked_scene)
                    return

                self._select_scene(item_idx)
                return

        # 4. Center Editor Controls via unified rects
        scene = self._get_selected_scene()
        if not scene:
            return

        ed_rects = self._get_editor_rects(scene)
        if ed_rects.get("toggle_enabled") and ed_rects["toggle_enabled"].collidepoint(mx, my):
            self._toggle_enabled(scene)
            return

        if ed_rects.get("switch_entity") and ed_rects["switch_entity"].collidepoint(mx, my):
            self.show_entity_picker = not self.show_entity_picker
            return

        if ed_rects.get("dist_minus") and ed_rects["dist_minus"].collidepoint(mx, my):
            cur_dist = float(scene.get("distance", 0))
            scene["distance"] = max(0.0, cur_dist - 50.0)
            self._trigger_preview()
            return

        if ed_rects.get("dist_plus") and ed_rects["dist_plus"].collidepoint(mx, my):
            cur_dist = float(scene.get("distance", 0))
            scene["distance"] = cur_dist + 50.0
            self._trigger_preview()
            return

        if ed_rects.get("title_box") and ed_rects["title_box"].collidepoint(mx, my):
            self.active_field = "title"
            return

        if ed_rects.get("text_box") and ed_rects["text_box"].collidepoint(mx, my):
            self.active_field = "text"
            return

        if ed_rects.get("dur_minus") and ed_rects["dur_minus"].collidepoint(mx, my):
            cur_hold = float(scene.get("hold", 6.0))
            scene["hold"] = max(2.0, round(cur_hold - 0.5, 1))
            self._trigger_preview()
            return

        if ed_rects.get("dur_plus") and ed_rects["dur_plus"].collidepoint(mx, my):
            cur_hold = float(scene.get("hold", 6.0))
            scene["hold"] = min(15.0, round(cur_hold + 0.5, 1))
            self._trigger_preview()
            return

        if ed_rects.get("del_btn") and ed_rects["del_btn"].collidepoint(mx, my):
            self._delete_current_popup()
            return

        for t_key, t_rect in ed_rects.get("theme_tiles", {}).items():
            if t_rect.collidepoint(mx, my):
                self._set_theme(t_key)
                return

        # 5. Right Simulation Panel: Test Pop-up button
        anim_btn = pg.Rect(self.pv_x + 14, 372, 180, 32)
        if anim_btn.collidepoint(mx, my):
            self._trigger_preview()
            return

        # Dismiss input focus on background click
        self.active_field = None

    def _handle_add_modal_click(self, pos: Tuple[int, int]) -> None:
        """Handles clicks inside the [+ Add Pop-up] modal dialog using unified rects."""
        mx, my = pos
        rects = self._get_add_modal_rects()

        # Close / Cancel
        if rects["close"].collidepoint(mx, my) or rects["cancel"].collidepoint(mx, my):
            self._close_add_modal()
            return

        # Confirm & Create
        if rects["confirm"].collidepoint(mx, my):
            self._confirm_add_popup()
            return

        # Step 1: Trigger Mechanism Tabs
        for tt_key, tab_rect in rects["tabs"].items():
            if tab_rect.collidepoint(mx, my):
                self.add_trigger_type = tt_key
                return

        # Step 2: Target Selectors
        if self.add_trigger_type == "entity":
            for eid, ecard in rects.get("entity_cards", []):
                if ecard.collidepoint(mx, my):
                    self.add_selected_entity_id = eid
                    ent = self.catalog.get_entity(eid)
                    if ent:
                        self.add_title_str = ent.get("title", self.add_title_str)
                    return

        elif self.add_trigger_type == "distance":
            if rects.get("dist_box") and rects["dist_box"].collidepoint(mx, my):
                self.add_active_input = "dist"
                return
            for delta, srect in rects.get("dist_steppers", []):
                if srect.collidepoint(mx, my):
                    self.add_distance_val = max(0.0, self.add_distance_val + delta)
                    return
            for p_dist, prect in rects.get("dist_presets", []):
                if prect.collidepoint(mx, my):
                    self.add_distance_val = float(p_dist)
                    return

        else:  # flag
            if rects.get("flag_box") and rects["flag_box"].collidepoint(mx, my):
                self.add_active_input = "flag"
                return
            for fc, crect in rects.get("flag_chips", []):
                if crect.collidepoint(mx, my):
                    self.add_flag_str = fc
                    return

        # Step 3: Pop-up Header / Title Input
        if rects["title_input"].collidepoint(mx, my):
            self.add_active_input = "title"
            return

        # Step 4: Pop-up Message Text Input
        if rects["text_input"].collidepoint(mx, my):
            self.add_active_input = "text"
            return

        # Step 5: Visual Theme Selector Chips
        for tk, chip_rect in rects.get("theme_chips", {}).items():
            if chip_rect.collidepoint(mx, my):
                self.add_theme_str = tk
                return

        # Hold Duration Stepper in Modal
        if rects["hold_minus"].collidepoint(mx, my):
            self.add_hold_val = max(2.0, round(self.add_hold_val - 0.5, 1))
            return
        if rects["hold_plus"].collidepoint(mx, my):
            self.add_hold_val = min(15.0, round(self.add_hold_val + 0.5, 1))
            return

    def _handle_entity_picker_click(self, pos: Tuple[int, int]) -> bool:
        mx, my = pos
        all_ents = self.catalog.get_all_entities()
        dropdown_w = 340
        dropdown_h = len(all_ents) * 44 + 30
        dx = self.ed_x + self.ed_w - dropdown_w
        dy = 205
        drect = pg.Rect(dx, dy, dropdown_w, dropdown_h)
        if not drect.collidepoint(mx, my):
            self.show_entity_picker = False
            return False

        item_y = dy + 28
        for ent in all_ents:
            irect = pg.Rect(dx + 6, item_y, dropdown_w - 12, 38)
            if irect.collidepoint(mx, my):
                self._link_entity(ent["id"])
                return True
            item_y += 42
        return True

    # ─────────────────────────────────────────────────────────────────────────
    # Update & Animation
    # ─────────────────────────────────────────────────────────────────────────

    def update(self, dt: float) -> None:
        self.cursor_blink_time += dt
        if self.toast_time > 0:
            self.toast_time -= dt
            if self.toast_time <= 0:
                self.toast_msg = ""

        if self.preview_notification:
            self.preview_notification.update(dt)

    # ─────────────────────────────────────────────────────────────────────────
    # Rendering
    # ─────────────────────────────────────────────────────────────────────────

    def draw(self) -> None:
        self.screen.fill(C_BG)
        mx, my = pg.mouse.get_pos()

        # ── 1. Top Header Bar (Full Width) ───────────────────────────────────
        header_rect = pg.Rect(0, 0, self.width, 58)
        pg.draw.rect(self.screen, C_HEADER, header_rect)
        pg.draw.line(self.screen, C_HEADER_BORDER, (0, 58), (self.width, 58), 2)

        # Brand Title & Subtitle in clean typography
        t_surf = safe_render_text(self.font_brand, "POP-UP NOTIFICATION CONTROL SYSTEM", C_GOLD)
        self.screen.blit(t_surf, (20, 8))
        sub_surf = safe_render_text(self.font_small, "Data-Driven Scene & Entity Pop-up Notification Engine • Pixel Runner", C_TEXT_MUTED)
        self.screen.blit(sub_surf, (22, 34))

        # Top Navigation Buttons via Unified Rects
        hdr = self._get_header_rects()

        # Status Badge (Pulsing green indicator)
        active_count = sum(1 for s in self.scenes if s.get("enabled", True))
        stat_bg = hdr["status"]
        stat_color = C_GREEN if active_count > 0 else C_RED
        pg.draw.rect(self.screen, (22, 34, 26) if active_count > 0 else (36, 20, 24), stat_bg, border_radius=6)
        pg.draw.rect(self.screen, stat_color, stat_bg, width=1, border_radius=6)
        pg.draw.circle(self.screen, stat_color, (stat_bg.x + 14, stat_bg.centery), 4)
        stat_surf = safe_render_text(self.font_small_bold, f"{active_count}/{len(self.scenes)} Pop-ups Active", stat_color)
        self.screen.blit(stat_surf, (stat_bg.x + 24, stat_bg.centery - stat_surf.get_height() // 2))

        # [+ Add Pop-up] Glowing Primary Action Button
        draw_styled_button(
            surf=self.screen,
            rect=hdr["add_popup"],
            text="Add Pop-up",
            font=self.font_small_bold,
            text_color=C_GREEN,
            bg_color=(24, 46, 32),
            border_color=C_GREEN,
            hover_bg=(36, 70, 48),
            hover_border=(100, 240, 160),
            icon_type="plus",
            icon_color=C_GREEN,
        )

        # Mute All Button
        draw_styled_button(
            surf=self.screen,
            rect=hdr["mute_all"],
            text="Mute All",
            font=self.font_small_bold,
            text_color=(240, 160, 160),
            bg_color=(34, 22, 28),
            border_color=(130, 55, 65),
            hover_bg=(50, 28, 36),
            hover_border=(200, 75, 85),
            icon_type="speaker_mute",
            icon_color=(240, 160, 160),
        )

        # Unmute All Button
        draw_styled_button(
            surf=self.screen,
            rect=hdr["unmute_all"],
            text="Unmute All",
            font=self.font_small_bold,
            text_color=(160, 240, 180),
            bg_color=(22, 36, 28),
            border_color=(55, 140, 80),
            hover_bg=(32, 54, 40),
            hover_border=(80, 210, 120),
            icon_type="speaker_unmute",
            icon_color=(160, 240, 180),
        )

        # Save Button
        draw_styled_button(
            surf=self.screen,
            rect=hdr["save"],
            text="SAVE CONFIG",
            font=self.font_ui_bold,
            text_color=C_GOLD,
            bg_color=(56, 44, 18),
            border_color=C_GOLD,
            hover_bg=(80, 64, 26),
            hover_border=(255, 235, 120),
            border_radius=8,
            border_width=2,
            icon_type="disk",
            icon_color=C_GOLD,
        )

        # ── 2. Filter & Search Bar ───────────────────────────────────────────
        filter_bar = pg.Rect(0, 59, self.width, 40)
        pg.draw.rect(self.screen, (16, 14, 22), filter_bar)
        pg.draw.line(self.screen, (36, 32, 46), (0, 98), (self.width, 98), 1)

        srch_box, tab_rects = self._get_filter_rects()

        # Search Input with procedural magnifying glass icon
        is_srch_active = (self.active_field == "search")
        pg.draw.rect(self.screen, C_INPUT_BG, srch_box, border_radius=4)
        pg.draw.rect(self.screen, C_INPUT_FOCUS if is_srch_active else C_INPUT_BORDER, srch_box, width=1, border_radius=4)
        col_srch = C_TEXT_LIGHT if self.search_query or is_srch_active else C_TEXT_MUTED
        draw_icon_search(self.screen, srch_box.x + 8, srch_box.centery - 6, col_srch)

        disp_srch = self.search_query or ("Search scenes..." if not is_srch_active else "")
        if is_srch_active and int(self.cursor_blink_time * 2) % 2 == 0:
            disp_srch += "|"
        srch_surf = safe_render_text(self.font_small, disp_srch, col_srch)
        self.screen.blit(srch_surf, (srch_box.x + 26, srch_box.centery - srch_surf.get_height() // 2))

        # Filter Tabs
        for tab_name, tab_rect in tab_rects:
            is_active = (self.filter_tab == tab_name)
            is_hover = tab_rect.collidepoint(mx, my)
            t_col = C_GOLD if is_active else (C_TEXT_LIGHT if is_hover else C_TEXT_MUTED)
            bg_col = (42, 34, 18) if is_active else ((34, 29, 44) if is_hover else (24, 21, 32))
            border_col = C_GOLD if is_active else ((70, 60, 90) if is_hover else (45, 38, 60))

            pg.draw.rect(self.screen, bg_col, tab_rect, border_radius=4)
            pg.draw.rect(self.screen, border_col, tab_rect, width=1, border_radius=4)
            t_surf = safe_render_text(self.font_small_bold, tab_name, t_col)
            self.screen.blit(t_surf, (tab_rect.centerx - t_surf.get_width() // 2, tab_rect.centery - t_surf.get_height() // 2))

        # ── 3. Left Panel: Timeline List ─────────────────────────────────────
        timeline_panel = pg.Rect(10, 104, self.timeline_w, self.panels_h)
        pg.draw.rect(self.screen, C_PANEL_BG, timeline_panel, border_radius=8)
        pg.draw.rect(self.screen, C_PANEL_BORDER, timeline_panel, width=1, border_radius=8)

        clip_rect = pg.Rect(12, 106, self.timeline_w - 4, self.panels_h - 4)
        self.screen.set_clip(clip_rect)

        filtered_scenes = self._get_filtered_scenes()
        total_content_h = len(filtered_scenes) * (self.timeline_item_h + 8)
        self.max_scroll = max(0.0, float(total_content_h - (self.panels_h - 12)))

        for idx, scene in enumerate(filtered_scenes):
            item_y = 108 + idx * (self.timeline_item_h + 8) - self.scroll_y
            if item_y + self.timeline_item_h < 100 or item_y > self.height:
                continue

            card_rect = pg.Rect(16, item_y, self.timeline_w - 24, self.timeline_item_h)
            is_selected = (self.selected_index >= 0 and self.selected_index < len(self.scenes) and self.scenes[self.selected_index] == scene)
            is_hover = card_rect.collidepoint(mx, my)

            # Card background
            if is_selected:
                card_bg = C_CARD_ACTIVE
                border_col = C_CARD_ACTIVE_BORDER
                border_w = 2
            elif is_hover:
                card_bg = C_CARD_HOVER
                border_col = (85, 75, 110)
                border_w = 1
            else:
                card_bg = C_CARD_BG
                border_col = C_CARD_BORDER
                border_w = 1

            pg.draw.rect(self.screen, card_bg, card_rect, border_radius=6)
            pg.draw.rect(self.screen, border_col, card_rect, width=border_w, border_radius=6)

            # Tag & Entity Badges
            ttype = scene.get("trigger_type", "distance")
            dist = scene.get("distance", 0)
            if ttype == "entity":
                eid = scene.get("entity_id", "?")
                ent = self.catalog.get_entity(eid)
                ent_name = ent.get("title", f"Entity #{eid}") if ent else f"Entity #{eid}"
                tag_label = f"#{eid}: {ent_name}"
                tag_bg = (52, 28, 70)
                tag_border = (160, 75, 210)
            elif ttype == "distance":
                tag_label = f"📍 {int(float(dist))}m"
                tag_bg = (28, 48, 80)
                tag_border = (65, 120, 210)
            else:
                flag = scene.get("flag", "flag")
                tag_label = f"Flag: {flag}"
                tag_bg = (70, 28, 28)
                tag_border = (180, 65, 65)

            tag_tw = self.font_small_bold.size(tag_label)[0]
            tag_w = min(card_rect.width - 95, max(60, tag_tw + 14))
            tag_rect = pg.Rect(card_rect.x + 8, card_rect.y + 10, tag_w, 22)
            pg.draw.rect(self.screen, tag_bg, tag_rect, border_radius=4)
            pg.draw.rect(self.screen, tag_border, tag_rect, width=1, border_radius=4)

            # Label truncation for badge if necessary
            disp_tag = tag_label
            if self.font_small_bold.size(disp_tag)[0] > tag_w - 8:
                while len(disp_tag) > 3 and self.font_small_bold.size(disp_tag + "..")[0] > tag_w - 8:
                    disp_tag = disp_tag[:-1]
                disp_tag += ".."
            tag_surf = safe_render_text(self.font_small_bold, disp_tag, C_TEXT_LIGHT)
            self.screen.blit(tag_surf, (tag_rect.centerx - tag_surf.get_width() // 2, tag_rect.centery - tag_surf.get_height() // 2))

            # Title
            title_text = scene.get("title", "Untitled")
            t_col = C_GOLD if is_selected else C_TEXT_LIGHT
            title_x = tag_rect.right + 10
            max_title_w = card_rect.right - 85 - title_x
            if self.font_ui_bold.size(title_text)[0] > max_title_w:
                while len(title_text) > 3 and self.font_ui_bold.size(title_text + "...")[0] > max_title_w:
                    title_text = title_text[:-1]
                title_text += "..."
            st_surf = safe_render_text(self.font_ui_bold, title_text, t_col)
            self.screen.blit(st_surf, (title_x, card_rect.y + 11))

            # Body snippet
            raw_body = scene.get("text", "").replace("\n", " ")
            snip_w = card_rect.width - 24
            if self.font_small.size(raw_body)[0] > snip_w:
                while len(raw_body) > 3 and self.font_small.size(raw_body + "...")[0] > snip_w:
                    raw_body = raw_body[:-1]
                raw_body += "..."
            snip_surf = safe_render_text(self.font_small, raw_body, C_TEXT_MUTED)
            self.screen.blit(snip_surf, (card_rect.x + 10, card_rect.y + 38))

            # Theme Pill & Duration
            theme_key = scene.get("theme", "gothic_gold")
            theme_short = self.theme_meta.get(theme_key, {}).get("label", theme_key)
            draw_icon_palette(self.screen, card_rect.x + 10, card_rect.y + 65, (185, 175, 210))
            theme_pill = safe_render_text(self.font_small, theme_short, (185, 175, 210))
            self.screen.blit(theme_pill, (card_rect.x + 30, card_rect.y + 63))

            draw_icon_clock(self.screen, card_rect.x + 160, card_rect.y + 65, C_TEXT_MUTED)
            dur_pill = safe_render_text(self.font_small, f"{scene.get('hold', 6.0)}s", C_TEXT_MUTED)
            self.screen.blit(dur_pill, (card_rect.x + 175, card_rect.y + 63))

            # Toggle Switch Pill [● ON] / [○ MUTED]
            is_enabled = scene.get("enabled", True)
            tog_rect = pg.Rect(card_rect.right - 78, card_rect.y + 10, 70, 22)
            is_tog_hover = tog_rect.collidepoint(mx, my)

            tog_bg = (28, 52, 34) if (is_enabled and is_tog_hover) else ((22, 42, 28) if is_enabled else ((50, 22, 28) if is_tog_hover else (40, 18, 22)))
            tog_border = (80, 240, 140) if (is_enabled and is_tog_hover) else (C_GREEN if is_enabled else C_RED)
            tog_txt = "● ON" if is_enabled else "○ MUTED"
            tog_col = C_GREEN if is_enabled else C_RED

            pg.draw.rect(self.screen, tog_bg, tog_rect, border_radius=4)
            pg.draw.rect(self.screen, tog_border, tog_rect, width=1, border_radius=4)
            tog_surf = safe_render_text(self.font_small_bold, tog_txt, tog_col)
            self.screen.blit(tog_surf, (tog_rect.centerx - tog_surf.get_width() // 2, tog_rect.centery - tog_surf.get_height() // 2))

        self.screen.set_clip(None)

        # Draggable Scrollbar on timeline
        if self.max_scroll > 0:
            track_h = self.panels_h - 20
            sb_h = max(30, int(track_h * (track_h / total_content_h)))
            sb_y = 114 + int((self.scroll_y / self.max_scroll) * (track_h - sb_h))
            sb_rect = pg.Rect(self.timeline_w + 3, sb_y, 4, sb_h)
            pg.draw.rect(self.screen, (100, 95, 130), sb_rect, border_radius=2)

        # ── 4. Center Panel: Pop-up Editor ──────────────────────────────────
        ed_x = self.ed_x
        ed_w = self.ed_w
        editor_panel = pg.Rect(ed_x, 104, ed_w, self.panels_h)
        pg.draw.rect(self.screen, C_PANEL_BG, editor_panel, border_radius=8)
        pg.draw.rect(self.screen, C_PANEL_BORDER, editor_panel, width=1, border_radius=8)

        scene = self._get_selected_scene()
        if not scene:
            no_sel = safe_render_text(self.font_heading, "No scene selected. Click '+ Add Pop-up' to create one.", C_TEXT_MUTED)
            self.screen.blit(no_sel, (ed_x + 30, 260))
            return

        ed_rects = self._get_editor_rects(scene)

        # Scene Details Header
        sid = scene.get("id", "")
        tt = scene.get("trigger_type", "")
        id_surf = safe_render_text(self.font_heading, f"Scene: {sid}", C_GOLD)
        self.screen.blit(id_surf, (ed_x + 18, 114))

        meta_info = f"Trigger: {tt.upper()} • Distance: {scene.get('distance')}m"
        meta_surf = safe_render_text(self.font_small, meta_info, C_TEXT_MUTED)
        self.screen.blit(meta_surf, (ed_x + 18, 138))

        # Checkbox / Enable switch (top right of center panel)
        is_en = scene.get("enabled", True)
        chk_rect = ed_rects["toggle_enabled"]
        is_chk_hover = chk_rect.collidepoint(mx, my)
        chk_bg = (32, 54, 38) if (is_en and is_chk_hover) else ((24, 42, 28) if is_en else ((52, 26, 32) if is_chk_hover else (42, 20, 24)))
        chk_border = (80, 240, 140) if (is_en and is_chk_hover) else (C_GREEN if is_en else C_RED)
        pg.draw.rect(self.screen, chk_bg, chk_rect, border_radius=6)
        pg.draw.rect(self.screen, chk_border, chk_rect, width=1, border_radius=6)

        lbl_str = "Pop-up Enabled in Game" if is_en else "Pop-up Muted (Silenced)"
        chk_txt = safe_render_text(self.font_ui_bold, lbl_str, chk_border)
        start_x = chk_rect.centerx - (14 + 8 + chk_txt.get_width()) // 2
        if is_en:
            draw_icon_check(self.screen, start_x, chk_rect.centery - 6, C_GREEN)
        else:
            draw_icon_speaker(self.screen, start_x, chk_rect.centery - 6, C_RED, muted=True)
        self.screen.blit(chk_txt, (start_x + 20, chk_rect.centery - chk_txt.get_height() // 2))

        # ── Linked Entity Inspector Card ────────────────────────────────────
        ent_card_rect = ed_rects["ent_card"]
        pg.draw.rect(self.screen, (24, 21, 33), ent_card_rect, border_radius=6)
        pg.draw.rect(self.screen, (60, 50, 80), ent_card_rect, width=1, border_radius=6)

        eid = scene.get("entity_id")
        if tt == "entity" and eid is not None:
            avatar = self.catalog.get_avatar_surface(int(eid), size=(44, 44))
            self.screen.blit(avatar, (ent_card_rect.x + 6, ent_card_rect.y + 6))

            ent = self.catalog.get_entity(int(eid))
            ename = ent.get("title", f"Entity #{eid}") if ent else f"Entity #{eid}"
            etier = ent.get("tier", "encounter").upper() if ent else "ENTITY"
            ehp = f" • Health: {ent.get('health')}" if ent and ent.get("health") else ""

            e_title = safe_render_text(self.font_ui_bold, f"Linked Entity: {ename} [{etier}{ehp}]", C_GOLD)
            self.screen.blit(e_title, (ent_card_rect.x + 58, ent_card_rect.y + 8))

            e_sub = safe_render_text(self.font_small, f"Level 1 World Event #{eid} @ {scene.get('distance')}m • Proximity Approach Trigger", C_TEXT_LIGHT)
            self.screen.blit(e_sub, (ent_card_rect.x + 58, ent_card_rect.y + 30))

            # Change Entity Button
            change_btn = ed_rects["switch_entity"]
            draw_styled_button(
                surf=self.screen,
                rect=change_btn,
                text="Switch Entity",
                font=self.font_small_bold,
                text_color=(210, 200, 230),
                bg_color=(34, 30, 48),
                border_color=(90, 80, 120),
                hover_bg=(48, 42, 68),
                hover_border=(150, 130, 190),
                icon_type="link",
                icon_color=(210, 200, 230),
            )

        elif tt == "distance":
            nearest = self.catalog.get_nearest_entity(float(scene.get("distance", 0)))
            near_str = f" • Nearest Entity: {nearest['title']} @ {nearest['distance']}m" if nearest else ""
            d_title = safe_render_text(self.font_ui_bold, f"Linked Trigger: Distance Milestone @ {int(float(scene.get('distance', 0)))}m", C_CYAN)
            self.screen.blit(d_title, (ent_card_rect.x + 14, ent_card_rect.y + 8))
            d_sub = safe_render_text(self.font_small, f"Triggers when player runs past {int(float(scene.get('distance', 0)))}m mark{near_str}", C_TEXT_LIGHT)
            self.screen.blit(d_sub, (ent_card_rect.x + 14, ent_card_rect.y + 30))

            # Distance adjustment stepper: [-50m] and [+50m]
            draw_styled_button(self.screen, ed_rects["dist_minus"], "-50m", self.font_small_bold, C_TEXT_LIGHT, (30, 40, 54), (60, 90, 140), hover_bg=(40, 56, 76))
            draw_styled_button(self.screen, ed_rects["dist_plus"], "+50m", self.font_small_bold, C_TEXT_LIGHT, (30, 40, 54), (60, 90, 140), hover_bg=(40, 56, 76))

        else:
            f_title = safe_render_text(self.font_ui_bold, f"Linked Trigger: Game Event Flag [{scene.get('flag')}]", C_AMBER)
            self.screen.blit(f_title, (ent_card_rect.x + 14, ent_card_rect.y + 8))
            f_sub = safe_render_text(self.font_small, f"Fired when event flag '{scene.get('flag')}' is dispatched in GameState.", C_TEXT_LIGHT)
            self.screen.blit(f_sub, (ent_card_rect.x + 14, ent_card_rect.y + 30))

        # Section: Notification Title Input
        lbl_title = safe_render_text(self.font_ui_bold, "Pop-up Header / Title:", C_TEXT_LIGHT)
        self.screen.blit(lbl_title, (ed_x + 18, 226))
        char_title = safe_render_text(self.font_small, f"{len(self.edit_title_str)}/60", C_TEXT_MUTED)
        self.screen.blit(char_title, (ed_x + ed_w - 75, 226))

        title_box = ed_rects["title_box"]
        is_title_active = (self.active_field == "title")
        pg.draw.rect(self.screen, C_INPUT_BG, title_box, border_radius=4)
        pg.draw.rect(self.screen, C_INPUT_FOCUS if is_title_active else C_INPUT_BORDER, title_box, width=1 if not is_title_active else 2, border_radius=4)

        disp_title = self.edit_title_str
        if is_title_active and int(self.cursor_blink_time * 2) % 2 == 0:
            disp_title += "|"
        t_val_surf = safe_render_text(self.font_ui, disp_title, C_GOLD)
        self.screen.blit(t_val_surf, (title_box.x + 10, title_box.centery - t_val_surf.get_height() // 2))

        # Section: Notification Body Text
        lbl_body = safe_render_text(self.font_ui_bold, "Pop-up Message Text (Multi-line):", C_TEXT_LIGHT)
        self.screen.blit(lbl_body, (ed_x + 18, 288))
        char_body = safe_render_text(self.font_small, f"{len(self.edit_text_str)} chars", C_TEXT_MUTED)
        self.screen.blit(char_body, (ed_x + ed_w - 95, 288))

        text_box = ed_rects["text_box"]
        is_text_active = (self.active_field == "text")
        pg.draw.rect(self.screen, C_INPUT_BG, text_box, border_radius=4)
        pg.draw.rect(self.screen, C_INPUT_FOCUS if is_text_active else C_INPUT_BORDER, text_box, width=1 if not is_text_active else 2, border_radius=4)

        # Word wrap text for multiline rendering
        body_words = self.edit_text_str.split("\n")
        line_y = text_box.y + 8
        last_line_rendered = ""
        for paragraph in body_words:
            words = paragraph.split(" ")
            curr_line = ""
            for w in words:
                test_line = f"{curr_line} {w}".strip() if curr_line else w
                if self.font_ui.size(test_line)[0] > text_box.width - 20:
                    if curr_line:
                        surf = safe_render_text(self.font_ui, curr_line, C_TEXT_LIGHT)
                        self.screen.blit(surf, (text_box.x + 8, line_y))
                        line_y += 18
                    curr_line = w
                else:
                    curr_line = test_line
            if curr_line:
                surf = safe_render_text(self.font_ui, curr_line, C_TEXT_LIGHT)
                self.screen.blit(surf, (text_box.x + 8, line_y))
                last_line_rendered = curr_line
                line_y += 18

        if is_text_active and int(self.cursor_blink_time * 2) % 2 == 0:
            cx_offset = self.font_ui.size(last_line_rendered)[0] if last_line_rendered else 0
            cursor_surf = safe_render_text(self.font_ui, "|", C_GOLD)
            self.screen.blit(cursor_surf, (text_box.x + 8 + cx_offset, max(text_box.y + 8, line_y - 18)))

        # Section: Hold Duration Controls & Delete Pop-up
        lbl_dur = safe_render_text(self.font_ui_bold, "Hold Duration:", C_TEXT_LIGHT)
        self.screen.blit(lbl_dur, (ed_x + 18, 434))

        # Stepper [-0.5s] [ 6.0s ] [+0.5s]
        draw_styled_button(self.screen, ed_rects["dur_minus"], "-0.5s", self.font_ui_bold, C_TEXT_LIGHT, (32, 28, 44), (65, 60, 85), hover_bg=(48, 42, 66))

        val_rect = ed_rects["dur_val"]
        pg.draw.rect(self.screen, C_INPUT_BG, val_rect, border_radius=4)
        dur_val = safe_render_text(self.font_ui_bold, f"{scene.get('hold', 6.0)}s", C_GOLD)
        self.screen.blit(dur_val, (val_rect.centerx - dur_val.get_width() // 2, val_rect.centery - dur_val.get_height() // 2))

        draw_styled_button(self.screen, ed_rects["dur_plus"], "+0.5s", self.font_ui_bold, C_TEXT_LIGHT, (32, 28, 44), (65, 60, 85), hover_bg=(48, 42, 66))

        # [🗑 Delete Pop-up] Button in Center Panel
        draw_styled_button(
            surf=self.screen,
            rect=ed_rects["del_btn"],
            text="Delete Pop-up",
            font=self.font_small_bold,
            text_color=(240, 160, 160),
            bg_color=(38, 20, 24),
            border_color=(140, 50, 60),
            hover_bg=(58, 26, 32),
            hover_border=(220, 70, 80),
            icon_type="trash",
            icon_color=(240, 160, 160),
        )

        # Section: Preset Theme Selector (2-Column Grid of Responsive Cards)
        lbl_theme = safe_render_text(self.font_ui_bold, "Visual Pop-up Theme:", C_TEXT_LIGHT)
        self.screen.blit(lbl_theme, (ed_x + 18, 468))

        curr_theme = scene.get("theme", "gothic_gold")
        theme_keys = list(THEME_PRESETS.keys())

        for t_key in theme_keys:
            t_rect = ed_rects["theme_tiles"].get(t_key)
            if not t_rect:
                continue

            t_data = THEME_PRESETS[t_key]
            t_colors = t_data.get("colors", {})
            t_border_col = tuple(t_colors.get("border_color", [218, 165, 32]))[:3]
            t_bg_col = tuple(t_colors.get("bg_color", [16, 12, 24]))[:3]
            t_notch_col = tuple(t_colors.get("accent_notch_color", [255, 215, 80]))[:3]

            meta = self.theme_meta.get(t_key, {"label": t_key, "sub": ""})

            is_active_theme = (curr_theme == t_key)
            is_hover_theme = t_rect.collidepoint(mx, my)

            pg.draw.rect(self.screen, t_bg_col, t_rect, border_radius=6)
            b_width = 2 if is_active_theme else 1
            b_color = C_GOLD if is_active_theme else ((90, 80, 115) if is_hover_theme else (55, 50, 70))
            pg.draw.rect(self.screen, b_color, t_rect, width=b_width, border_radius=6)

            # Left accent notch
            pg.draw.rect(self.screen, t_notch_col, (t_rect.x + 3, t_rect.y + 6, 4, t_rect.height - 12), border_radius=2)

            # Swatch circles: Background, Border, Notch
            sx = t_rect.x + 16
            sy = t_rect.centery
            pg.draw.circle(self.screen, t_bg_col, (sx, sy), 6)
            pg.draw.circle(self.screen, (90, 85, 110), (sx, sy), 6, width=1)
            pg.draw.circle(self.screen, t_border_col, (sx + 16, sy), 6)
            pg.draw.circle(self.screen, t_notch_col, (sx + 32, sy), 6)

            # Title & Subtitle in tile
            t_lbl = safe_render_text(self.font_ui_bold, meta["label"], C_GOLD if is_active_theme else C_TEXT_LIGHT)
            self.screen.blit(t_lbl, (t_rect.x + 64, t_rect.y + 12))

            sub_lbl = safe_render_text(self.font_small, meta["sub"], C_TEXT_MUTED)
            self.screen.blit(sub_lbl, (t_rect.x + 64, t_rect.y + 36))

            if is_active_theme:
                active_pill = safe_render_text(self.font_small_bold, "● ACTIVE", C_GOLD)
                self.screen.blit(active_pill, (t_rect.right - active_pill.get_width() - 8, t_rect.y + 12))

        # ── 5. Right Area: Live Simulation Viewport & Inspector ─────────────
        pv_x = self.pv_x
        pv_w = self.pv_w
        preview_box = pg.Rect(pv_x, 104, pv_w, self.panels_h)
        pg.draw.rect(self.screen, (12, 10, 16), preview_box, border_radius=8)
        pg.draw.rect(self.screen, (45, 40, 58), preview_box, width=1, border_radius=8)

        # Simulation Viewport Header
        vp_header = pg.Rect(pv_x, 104, pv_w, 36)
        pg.draw.rect(self.screen, (18, 15, 24), vp_header, border_radius=8)
        pg.draw.line(self.screen, (38, 34, 48), (pv_x, 140), (pv_x + pv_w, 140), 1)

        pv_title = safe_render_text(self.font_subheading, "SIMULATED GAME SCREEN", C_GOLD)
        self.screen.blit(pv_title, (pv_x + 14, 112))

        res_pill = safe_render_text(self.font_mono, "1280x720 VIRTUAL", C_TEXT_MUTED)
        self.screen.blit(res_pill, (pv_x + pv_w - res_pill.get_width() - 14, 114))

        # Simulated Game Screen Canvas (Subtle gradient and dungeon atmosphere)
        sim_canvas = pg.Rect(pv_x + 12, 150, pv_w - 24, 210)
        pg.draw.rect(self.screen, (8, 7, 12), sim_canvas, border_radius=8)
        pg.draw.rect(self.screen, (35, 30, 48), sim_canvas, width=1, border_radius=8)

        # Draw SideNotification directly inside simulation canvas
        if self.preview_notification and hasattr(self.preview_notification, "_current_tab_surface"):
            tab_surf = self.preview_notification._current_tab_surface
            if tab_surf:
                cx = sim_canvas.centerx - tab_surf.get_width() // 2
                cy = sim_canvas.centery - tab_surf.get_height() // 2
                self.screen.blit(tab_surf, (cx, cy))

        # Direct Playback Button below canvas
        anim_btn = pg.Rect(pv_x + 14, 372, 180, 32)
        draw_styled_button(
            surf=self.screen,
            rect=anim_btn,
            text="Test Pop-up",
            font=self.font_ui_bold,
            text_color=(180, 220, 255),
            bg_color=(32, 42, 60),
            border_color=(60, 110, 190),
            hover_bg=(44, 60, 88),
            hover_border=(90, 150, 240),
            icon_type="play",
            icon_color=(180, 220, 255),
        )

        # Notification Telemetry & Reading Pace Inspector Card
        insp_rect = pg.Rect(pv_x + 12, 418, pv_w - 24, self.panels_h - 326)
        pg.draw.rect(self.screen, (16, 14, 22), insp_rect, border_radius=6)
        pg.draw.rect(self.screen, (38, 34, 48), insp_rect, width=1, border_radius=6)

        insp_hdr = safe_render_text(self.font_ui_bold, "Reading Pace & Location Telemetry", C_TEXT_LIGHT)
        self.screen.blit(insp_hdr, (insp_rect.x + 14, insp_rect.y + 12))

        # Calculate Reading Metrics
        word_count = len(self.edit_text_str.split())
        est_read_time = round(max(1.5, word_count * 0.35 + 2.0), 1)
        configured_hold = float(scene.get("hold", 6.0))
        is_pace_good = (configured_hold >= est_read_time - 0.5)

        m1_lbl = safe_render_text(self.font_small, "• Word Count:", C_TEXT_MUTED)
        self.screen.blit(m1_lbl, (insp_rect.x + 14, insp_rect.y + 38))
        m1_val = safe_render_text(self.font_small_bold, f"{word_count} words", C_TEXT_LIGHT)
        self.screen.blit(m1_val, (insp_rect.x + 140, insp_rect.y + 38))

        m2_lbl = safe_render_text(self.font_small, "• Est. Reading Time:", C_TEXT_MUTED)
        self.screen.blit(m2_lbl, (insp_rect.x + 14, insp_rect.y + 60))
        m2_val = safe_render_text(self.font_small_bold, f"~{est_read_time}s (@ 3.5 wps)", C_TEXT_LIGHT)
        self.screen.blit(m2_val, (insp_rect.x + 140, insp_rect.y + 60))

        m3_lbl = safe_render_text(self.font_small, "• Reading Pace:", C_TEXT_MUTED)
        self.screen.blit(m3_lbl, (insp_rect.x + 14, insp_rect.y + 82))
        pace_col = C_GREEN if is_pace_good else C_AMBER
        if is_pace_good:
            draw_icon_check(self.screen, insp_rect.x + 140, insp_rect.y + 83, C_GREEN)
            m3_val = safe_render_text(self.font_small_bold, "Comfortable (Ample Time)", pace_col)
            self.screen.blit(m3_val, (insp_rect.x + 158, insp_rect.y + 82))
        else:
            draw_icon_warning(self.screen, insp_rect.x + 140, insp_rect.y + 83, C_AMBER)
            m3_val = safe_render_text(self.font_small_bold, "Fast (Consider Increasing Hold)", pace_col)
            self.screen.blit(m3_val, (insp_rect.x + 158, insp_rect.y + 82))

        m4_lbl = safe_render_text(self.font_small, "• In-Game Trigger:", C_TEXT_MUTED)
        self.screen.blit(m4_lbl, (insp_rect.x + 14, insp_rect.y + 104))
        m4_val = safe_render_text(self.font_small_bold, f"Level 1 @ {scene.get('distance')}m", C_TEXT_LIGHT)
        self.screen.blit(m4_val, (insp_rect.x + 140, insp_rect.y + 104))

        m5_lbl = safe_render_text(self.font_small, "• Event Context:", C_TEXT_MUTED)
        self.screen.blit(m5_lbl, (insp_rect.x + 14, insp_rect.y + 126))
        desc_text = scene.get("description", "Standard gameplay event")
        m5_val = safe_render_text(self.font_small, desc_text, C_TEXT_LIGHT)
        self.screen.blit(m5_val, (insp_rect.x + 140, insp_rect.y + 126))

        # ── 6. Entity Picker Overlay (Dropdown) ──────────────────────────────
        if self.show_entity_picker:
            self._draw_entity_picker()

        # ── 7. New Pop-up Modal Dialog (Modal Sheet) ────────────────────────
        if self.show_add_modal:
            self._draw_add_modal()

        # ── 8. Toast Notification ───────────────────────────────────────────
        if self.toast_msg and self.toast_time > 0:
            t_surf = safe_render_text(self.font_ui_bold, self.toast_msg, self.toast_color)
            total_w = 14 + 10 + t_surf.get_width()
            toast_w = total_w + 36
            toast_rect = pg.Rect(self.width // 2 - toast_w // 2, self.height - 55, toast_w, 38)
            pg.draw.rect(self.screen, (20, 24, 20), toast_rect, border_radius=8)
            pg.draw.rect(self.screen, self.toast_color, toast_rect, width=2, border_radius=8)
            start_x = toast_rect.centerx - total_w // 2
            if self.toast_color == C_GREEN:
                draw_icon_check(self.screen, start_x, toast_rect.centery - 6, C_GREEN)
            else:
                draw_icon_warning(self.screen, start_x, toast_rect.centery - 6, C_RED)
            self.screen.blit(t_surf, (start_x + 20, toast_rect.centery - t_surf.get_height() // 2))

        pg.display.flip()

    def _draw_entity_picker(self) -> None:
        """Renders dropdown list of all Level 1 entities for quick linking."""
        all_ents = self.catalog.get_all_entities()
        dropdown_w = 340
        dropdown_h = len(all_ents) * 44 + 32
        dx = self.ed_x + self.ed_w - dropdown_w
        dy = 205
        drect = pg.Rect(dx, dy, dropdown_w, dropdown_h)

        pg.draw.rect(self.screen, (22, 18, 30), drect, border_radius=8)
        pg.draw.rect(self.screen, C_GOLD, drect, width=2, border_radius=8)

        hdr = safe_render_text(self.font_small_bold, "Select Level 1 Entity to Link:", C_GOLD)
        self.screen.blit(hdr, (dx + 12, dy + 8))

        item_y = dy + 28
        mx, my = pg.mouse.get_pos()
        for ent in all_ents:
            irect = pg.Rect(dx + 6, item_y, dropdown_w - 12, 38)
            is_hover = irect.collidepoint(mx, my)
            pg.draw.rect(self.screen, (36, 30, 48) if is_hover else (28, 23, 38), irect, border_radius=4)
            pg.draw.rect(self.screen, (75, 65, 95), irect, width=1, border_radius=4)

            avatar = self.catalog.get_avatar_surface(ent["id"], size=(28, 28))
            self.screen.blit(avatar, (irect.x + 6, irect.y + 5))

            lbl = safe_render_text(self.font_small_bold, f"{ent['title']} ({ent['type']})", C_TEXT_LIGHT)
            self.screen.blit(lbl, (irect.x + 40, irect.y + 5))

            dist_lbl = safe_render_text(self.font_small, f"Level 1 @ {ent['distance']}m", C_TEXT_MUTED)
            self.screen.blit(dist_lbl, (irect.x + 40, irect.y + 20))

            item_y += 42

    def _draw_add_modal(self) -> None:
        """Renders the New Pop-up Creator modal using unified rects."""
        # Deep translucent dark glass scrim
        scrim = pg.Surface((self.width, self.height), pg.SRCALPHA)
        scrim.fill((0, 0, 0, 205))
        self.screen.blit(scrim, (0, 0))

        rects = self._get_add_modal_rects()
        modal_rect = rects["modal"]
        mx, my = pg.mouse.get_pos()

        # Modal Container with double glowing gold border
        pg.draw.rect(self.screen, (20, 17, 28), modal_rect, border_radius=10)
        pg.draw.rect(self.screen, (160, 125, 45), modal_rect, width=2, border_radius=10)
        pg.draw.rect(self.screen, (50, 42, 24), modal_rect.inflate(-6, -6), width=1, border_radius=8)

        # Header Title & Subtitle
        mhdr = safe_render_text(self.font_heading, "CREATE NEW POP-UP NOTIFICATION", C_GOLD)
        self.screen.blit(mhdr, (modal_rect.x + 24, modal_rect.y + 16))
        msub = safe_render_text(self.font_small, "Design in-game event banners linked to world encounters and milestones", C_TEXT_MUTED)
        self.screen.blit(msub, (modal_rect.x + 24, modal_rect.y + 38))

        # Close X Button with hover
        btn_close = rects["close"]
        is_close_hover = btn_close.collidepoint(mx, my)
        pg.draw.rect(self.screen, (42, 24, 30) if is_close_hover else (28, 22, 34), btn_close, border_radius=4)
        x_txt = safe_render_text(self.font_ui_bold, "✕", C_RED if is_close_hover else C_TEXT_MUTED)
        self.screen.blit(x_txt, (btn_close.centerx - x_txt.get_width() // 2, btn_close.centery - x_txt.get_height() // 2))

        # ── Step 1: Trigger Mechanism Tabs ──
        tab_y = modal_rect.y + 64
        for tt_key, tab_rect in rects["tabs"].items():
            is_active = (self.add_trigger_type == tt_key)
            is_hover = tab_rect.collidepoint(mx, my)

            bg_col = (46, 36, 18) if is_active else ((36, 30, 48) if is_hover else (26, 22, 36))
            border_col = C_GOLD if is_active else ((80, 70, 100) if is_hover else (55, 46, 70))
            text_col = C_GOLD if is_active else (C_TEXT_LIGHT if is_hover else C_TEXT_MUTED)

            pg.draw.rect(self.screen, bg_col, tab_rect, border_radius=6)
            pg.draw.rect(self.screen, border_col, tab_rect, width=1 if not is_active else 2, border_radius=6)

            label_map = {"entity": "⚔ Entity Encounter", "distance": "📍 Distance Milestone", "flag": "⚡ Game Flag"}
            lbl = safe_render_text(self.font_small_bold, label_map.get(tt_key, tt_key), text_col)
            self.screen.blit(lbl, (tab_rect.centerx - lbl.get_width() // 2, tab_rect.centery - lbl.get_height() // 2))

        # ── Step 2: Linked Target Selection ──
        step2_lbl = safe_render_text(self.font_small_bold, "2. Select Linked Event / Milestone Target:", C_TEXT_LIGHT)
        self.screen.blit(step2_lbl, (modal_rect.x + 24, modal_rect.y + 104))

        if self.add_trigger_type == "entity":
            for eid, ecard in rects.get("entity_cards", []):
                ent = self.catalog.get_entity(eid)
                is_sel = (self.add_selected_entity_id == eid)
                is_hover = ecard.collidepoint(mx, my)

                card_bg = (42, 34, 56) if is_sel else ((32, 26, 44) if is_hover else (24, 20, 32))
                card_border = C_GOLD if is_sel else ((75, 65, 95) if is_hover else (50, 44, 65))

                pg.draw.rect(self.screen, card_bg, ecard, border_radius=6)
                pg.draw.rect(self.screen, card_border, ecard, width=2 if is_sel else 1, border_radius=6)

                avatar = self.catalog.get_avatar_surface(eid, size=(28, 28))
                self.screen.blit(avatar, (ecard.x + 6, ecard.centery - 14))

                ename = ent.get("title", f"Entity #{eid}") if ent else f"Entity #{eid}"
                elbl = safe_render_text(self.font_small_bold, ename, C_GOLD if is_sel else C_TEXT_LIGHT)
                self.screen.blit(elbl, (ecard.x + 42, ecard.centery - elbl.get_height() // 2))

                # Tier badge
                etier = ent.get("tier", "encounter").upper() if ent else "ENTITY"
                tier_col = C_RED if "BOSS" in etier else C_PURPLE
                tier_surf = safe_render_text(self.font_small_bold, f"[{etier}]", tier_col)
                self.screen.blit(tier_surf, (ecard.x + 42 + elbl.get_width() + 8, ecard.centery - tier_surf.get_height() // 2))

                dist_text = f"Level 1 @ {ent.get('distance', 0)}m" if ent else ""
                dist_lbl = safe_render_text(self.font_small, dist_text, C_TEXT_MUTED)
                self.screen.blit(dist_lbl, (ecard.right - dist_lbl.get_width() - 14, ecard.centery - dist_lbl.get_height() // 2))

        elif self.add_trigger_type == "distance":
            # Big digital distance display
            dist_box = rects["dist_box"]
            is_dist_active = (self.add_active_input == "dist")
            pg.draw.rect(self.screen, C_INPUT_BG, dist_box, border_radius=6)
            pg.draw.rect(self.screen, C_INPUT_FOCUS if is_dist_active else C_INPUT_BORDER, dist_box, width=2 if is_dist_active else 1, border_radius=6)
            dtxt = safe_render_text(self.font_ui_bold, f"{int(self.add_distance_val)} m", C_GOLD)
            self.screen.blit(dtxt, (dist_box.centerx - dtxt.get_width() // 2, dist_box.centery - dtxt.get_height() // 2))

            # Stepper buttons: [-500m] [-100m] [+100m] [+500m]
            for delta, srect in rects.get("dist_steppers", []):
                draw_styled_button(self.screen, srect, f"{delta:+d}m", self.font_small_bold, C_TEXT_LIGHT, (32, 28, 44), (65, 55, 85), hover_bg=(48, 42, 66))

            # Preset pills
            p_names = {0: "0m Awakening", 650: "650m Book", 1400: "1.4km Gloom", 2558: "2.5km Zombie", 12500: "12.5km Gate", 34500: "34.5km Boss"}
            for p_dist, prect in rects.get("dist_presets", []):
                is_p_active = (int(self.add_distance_val) == p_dist)
                draw_styled_button(
                    self.screen,
                    prect,
                    p_names.get(p_dist, f"{p_dist}m"),
                    self.font_small,
                    C_GOLD if is_p_active else C_TEXT_MUTED,
                    (42, 34, 18) if is_p_active else (28, 24, 38),
                    C_GOLD if is_p_active else (60, 50, 75),
                    hover_bg=(48, 38, 58),
                )

        else:  # flag
            flag_box = rects["flag_box"]
            is_flag_active = (self.add_active_input == "flag")
            pg.draw.rect(self.screen, C_INPUT_BG, flag_box, border_radius=6)
            pg.draw.rect(self.screen, C_INPUT_FOCUS if is_flag_active else C_INPUT_BORDER, flag_box, width=2 if is_flag_active else 1, border_radius=6)
            disp_flag = self.add_flag_str + ("|" if is_flag_active and int(self.cursor_blink_time * 2) % 2 == 0 else "")
            ftxt = safe_render_text(self.font_ui, disp_flag, C_GOLD)
            self.screen.blit(ftxt, (flag_box.x + 10, flag_box.centery - ftxt.get_height() // 2))

            for fc, crect in rects.get("flag_chips", []):
                is_c_active = (self.add_flag_str == fc)
                draw_styled_button(
                    self.screen,
                    crect,
                    fc,
                    self.font_small,
                    C_GOLD if is_c_active else C_TEXT_LIGHT,
                    (42, 34, 18) if is_c_active else (28, 24, 38),
                    C_GOLD if is_c_active else (60, 50, 75),
                    hover_bg=(48, 38, 58),
                )

        # ── Step 3: Pop-up Header / Title ──
        step3_lbl = safe_render_text(self.font_small_bold, "3. Pop-up Header / Title:", C_TEXT_LIGHT)
        self.screen.blit(step3_lbl, (modal_rect.x + 24, modal_rect.y + 328))
        char_t = safe_render_text(self.font_small, f"{len(self.add_title_str)}/60", C_TEXT_MUTED)
        self.screen.blit(char_t, (modal_rect.right - 75, modal_rect.y + 328))

        t_in = rects["title_input"]
        is_tin_active = (self.add_active_input == "title")
        pg.draw.rect(self.screen, C_INPUT_BG, t_in, border_radius=4)
        pg.draw.rect(self.screen, C_INPUT_FOCUS if is_tin_active else C_INPUT_BORDER, t_in, width=2 if is_tin_active else 1, border_radius=4)
        t_str = self.add_title_str + ("|" if is_tin_active and int(self.cursor_blink_time * 2) % 2 == 0 else "")
        self.screen.blit(safe_render_text(self.font_ui, t_str, C_GOLD), (t_in.x + 10, t_in.centery - 8))

        # ── Step 4: Pop-up Message Text (Multi-line) ──
        step4_lbl = safe_render_text(self.font_small_bold, "4. Pop-up Message Text:", C_TEXT_LIGHT)
        self.screen.blit(step4_lbl, (modal_rect.x + 24, modal_rect.y + 392))
        char_b = safe_render_text(self.font_small, f"{len(self.add_text_str)} chars", C_TEXT_MUTED)
        self.screen.blit(char_b, (modal_rect.right - 85, modal_rect.y + 392))

        b_in = rects["text_input"]
        is_bin_active = (self.add_active_input == "text")
        pg.draw.rect(self.screen, C_INPUT_BG, b_in, border_radius=4)
        pg.draw.rect(self.screen, C_INPUT_FOCUS if is_bin_active else C_INPUT_BORDER, b_in, width=2 if is_bin_active else 1, border_radius=4)
        b_str = self.add_text_str + ("|" if is_bin_active and int(self.cursor_blink_time * 2) % 2 == 0 else "")
        self.screen.blit(safe_render_text(self.font_small, b_str[:120], C_TEXT_LIGHT), (b_in.x + 10, b_in.y + 8))

        # ── Step 5: Visual Theme Selector ──
        step5_lbl = safe_render_text(self.font_small_bold, "5. Visual Theme Preset:", C_TEXT_LIGHT)
        self.screen.blit(step5_lbl, (modal_rect.x + 24, modal_rect.y + 486))

        for tk, chip in rects.get("theme_chips", {}).items():
            is_active = (self.add_theme_str == tk)
            meta = self.theme_meta.get(tk, {"label": tk})
            draw_styled_button(
                self.screen,
                chip,
                meta["label"],
                self.font_small,
                C_GOLD if is_active else C_TEXT_MUTED,
                (42, 34, 18) if is_active else (26, 22, 34),
                C_GOLD if is_active else (60, 50, 75),
                hover_bg=(40, 32, 50),
            )

        # ── Hold Duration Stepper in Modal ──
        lbl_h = safe_render_text(self.font_small_bold, "Hold Duration:", C_TEXT_LIGHT)
        self.screen.blit(lbl_h, (modal_rect.x + 24, modal_rect.y + modal_rect.height - 45))

        draw_styled_button(self.screen, pg.Rect(modal_rect.x + 130, modal_rect.y + modal_rect.height - 48, 36, 26), "-0.5s", self.font_small_bold, C_TEXT_LIGHT, (32, 28, 44), (65, 55, 85))
        h_val = safe_render_text(self.font_ui_bold, f"{self.add_hold_val}s", C_GOLD)
        self.screen.blit(h_val, (modal_rect.x + 176, modal_rect.y + modal_rect.height - 44))
        draw_styled_button(self.screen, pg.Rect(modal_rect.x + 225, modal_rect.y + modal_rect.height - 48, 36, 26), "+0.5s", self.font_small_bold, C_TEXT_LIGHT, (32, 28, 44), (65, 55, 85))

        # Action Buttons: Cancel and Create
        draw_styled_button(
            surf=self.screen,
            rect=rects["cancel"],
            text="Cancel",
            font=self.font_small_bold,
            text_color=C_TEXT_MUTED,
            bg_color=(34, 28, 42),
            border_color=(75, 65, 95),
            hover_bg=(50, 42, 62),
            hover_border=(110, 95, 140),
        )

        draw_styled_button(
            surf=self.screen,
            rect=rects["confirm"],
            text="✓ Create",
            font=self.font_small_bold,
            text_color=C_GREEN,
            bg_color=(24, 46, 32),
            border_color=C_GREEN,
            hover_bg=(36, 70, 48),
            hover_border=(100, 240, 160),
            icon_type="check",
            icon_color=C_GREEN,
        )

    def run(self) -> None:
        while self.running:
            dt = self.clock.tick(60) / 1000.0
            self.handle_events()
            self.update(dt)
            self.draw()
        pg.quit()


def main() -> None:
    app = PopupControllerApp()
    app.run()


if __name__ == "__main__":
    main()
