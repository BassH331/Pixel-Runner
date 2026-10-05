#!/usr/bin/env python3
"""
notification_editor.py — Pop-Up & Side Notification Plugin Editor for Pixel-Runner.

Dedicated interactive GUI editor to configure, tweak, and test in-game pop-up notifications
(SideNotification) in real time. Provides full control over:
- Timings: slide-in duration, hold duration, slide-out duration, dynamic word-count scaling,
  breathing oscillation speed and amplitude, and alpha fade.
- Layout & Geometry: card width, min height, screen margins, padding, corner radius, borders,
  accent ribbon notches, badge framing, and icon scaling.
- Color Palette & Opacity: obsidian/glass backgrounds, inner depth fills, filigree borders,
  accent highlights, badge styling, text colors, and drop shadows.
- Typography: font sizing, drop shadow toggles, and line spacing.
- Curated Presets: one-click themes (Gothic Gold, Blood & Bone, Arcane Void, Grimoire Leather, Sleek Dark Glass).
- Live Simulation: interactive 1280x720 canvas rendering against the real game forest background
  with live animation preview, freeze/pause, scrub, and sample narrative taunts.
- Hot-Reloading: saves directly to game_data/notification_config.json with automatic timestamped backups,
  immediately syncing with the running game without restarts.
"""

from __future__ import annotations

import os
import sys
import json
import math
import copy
import time
from typing import Optional, Dict, List, Tuple, Any

import pygame as pg

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from src.game.systems.notification_config_manager import (
    NotificationConfigManager,
    DEFAULT_NOTIFICATION_CONFIG,
    THEME_PRESETS,
    CONFIG_PATH,
)
from src.game.ui.side_notification import SideNotification, NotificationState


# ── Color Palette for Editor UI ────────────────────────────────────────────────
C_BG            = ( 12,  14,  22)
C_PANEL         = ( 19,  23,  35)
C_PANEL_DARK    = ( 14,  17,  26)
C_HEADER        = ( 25,  30,  46)
C_BORDER        = ( 42,  52,  78)
C_BORDER_HI     = ( 75,  95, 140)
C_TEXT          = (232, 238, 250)
C_MUTED         = (125, 138, 165)
C_GOLD          = (245, 200,  70)
C_CYAN          = (  0, 220, 255)
C_GREEN         = (  0, 220, 115)
C_CRIMSON       = (235,  55,  75)
C_ORANGE        = (255, 150,  35)
C_WHITE         = (255, 255, 255)
C_SEL           = ( 32,  65, 105)


def make_sys_font(size: int, bold: bool = False) -> pg.font.Font:
    """Safely obtain system font."""
    return pg.font.SysFont("dejavusans,ubuntu,segoeui,arial,helvetica,sans-serif", size, bold=bold)


# ── Interactive Slider Component ──────────────────────────────────────────────
class EditorSlider:
    def __init__(
        self,
        label: str,
        section: str,
        key: str,
        x: int,
        y: int,
        w: int,
        min_val: float,
        max_val: float,
        current_val: float,
        is_float: bool = True,
        format_str: str = "{val}",
        unit: str = "",
        tooltip: str = "",
    ):
        self.label = label
        self.section = section
        self.key = key
        self.rect = pg.Rect(x, y + 18, w, 10)
        self.base_y = y
        self.handle_r = 8
        self.min_val = min_val
        self.max_val = max_val
        self.val = current_val
        self.dragging = False
        self.is_float = is_float
        self.format_str = format_str
        self.unit = unit
        self.tooltip = tooltip
        self.hovered = False

    def get_handle_pos(self) -> Tuple[int, int]:
        if self.max_val == self.min_val:
            ratio = 0.0
        else:
            ratio = (self.val - self.min_val) / (self.max_val - self.min_val)
        ratio = max(0.0, min(1.0, ratio))
        return int(self.rect.x + ratio * self.rect.width), self.rect.centery

    def handle_event(self, event: pg.event.Event) -> bool:
        changed = False
        if event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
            hx, hy = self.get_handle_pos()
            hit_handle = math.hypot(event.pos[0] - hx, event.pos[1] - hy) <= self.handle_r + 5
            hit_track = self.rect.inflate(0, 14).collidepoint(event.pos)
            if hit_handle or hit_track:
                self.dragging = True
                self._update_val_from_mouse(event.pos[0])
                changed = True
        elif event.type == pg.MOUSEBUTTONUP and event.button == 1:
            if self.dragging:
                self.dragging = False
                changed = True
        elif event.type == pg.MOUSEMOTION and self.dragging:
            self._update_val_from_mouse(event.pos[0])
            changed = True
        return changed

    def _update_val_from_mouse(self, mouse_x: int) -> None:
        ratio = (mouse_x - self.rect.x) / float(self.rect.width)
        ratio = max(0.0, min(1.0, ratio))
        raw_val = self.min_val + ratio * (self.max_val - self.min_val)
        if self.is_float:
            self.val = round(raw_val, 2)
        else:
            self.val = int(round(raw_val))

    def set_value(self, val: float) -> None:
        self.val = max(self.min_val, min(self.max_val, val))

    def draw(self, surface: pg.Surface, font_lbl: pg.font.Font, font_val: pg.font.Font) -> None:
        m_pos = pg.mouse.get_pos()
        hx, hy = self.get_handle_pos()
        self.hovered = (
            math.hypot(m_pos[0] - hx, m_pos[1] - hy) <= self.handle_r + 4
            or pg.Rect(self.rect.x, self.base_y, self.rect.width, 36).collidepoint(m_pos)
        )

        val_display = self.format_str.format(
            val=round(self.val, 2) if self.is_float else int(self.val)
        ) + (f" {self.unit}" if self.unit else "")

        label_col = C_CYAN if self.hovered or self.dragging else C_TEXT
        txt_label = font_lbl.render(self.label, True, label_col)
        txt_val = font_val.render(val_display, True, C_GOLD if self.dragging else C_MUTED)

        surface.blit(txt_label, (self.rect.x, self.base_y))
        surface.blit(txt_val, (self.rect.right - txt_val.get_width(), self.base_y))

        # Track background
        pg.draw.rect(surface, (28, 34, 48), self.rect, border_radius=5)
        pg.draw.rect(surface, C_BORDER, self.rect, width=1, border_radius=5)

        # Active fill track
        fill_w = max(0, hx - self.rect.x)
        fill_rect = pg.Rect(self.rect.x, self.rect.y, fill_w, self.rect.height)
        fill_col = C_CYAN if self.dragging else (C_CYAN[0] // 2, C_CYAN[1] // 2, C_CYAN[2] // 2)
        pg.draw.rect(surface, fill_col, fill_rect, border_radius=5)

        # Handle
        handle_col = C_GOLD if self.dragging else (C_WHITE if self.hovered else (200, 210, 230))
        pg.draw.circle(surface, handle_col, (hx, hy), self.handle_r)
        pg.draw.circle(surface, C_BORDER_HI, (hx, hy), self.handle_r, width=1)


# ── Interactive Toggle Switch ─────────────────────────────────────────────────
class EditorToggle:
    def __init__(
        self,
        label: str,
        section: str,
        key: str,
        x: int,
        y: int,
        current_state: bool,
        tooltip: str = "",
    ):
        self.label = label
        self.section = section
        self.key = key
        self.x = x
        self.y = y
        self.state = current_state
        self.tooltip = tooltip
        self.rect = pg.Rect(x + 280, y, 44, 22)
        self.hovered = False

    def handle_event(self, event: pg.event.Event) -> bool:
        if event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
            hit_box = pg.Rect(self.x, self.y, 330, 26)
            if hit_box.collidepoint(event.pos):
                self.state = not self.state
                return True
        return False

    def draw(self, surface: pg.Surface, font: pg.font.Font) -> None:
        m_pos = pg.mouse.get_pos()
        hit_box = pg.Rect(self.x, self.y, 330, 26)
        self.hovered = hit_box.collidepoint(m_pos)

        lbl_col = C_CYAN if self.hovered else C_TEXT
        txt_lbl = font.render(self.label, True, lbl_col)
        surface.blit(txt_lbl, (self.x, self.y + 2))

        # Switch pill
        bg_col = C_GREEN if self.state else (40, 46, 62)
        pg.draw.rect(surface, bg_col, self.rect, border_radius=11)
        pg.draw.rect(surface, C_BORDER_HI if self.hovered else C_BORDER, self.rect, width=1, border_radius=11)

        # Switch knob
        knob_x = self.rect.right - 11 if self.state else self.rect.x + 11
        pg.draw.circle(surface, C_WHITE, (knob_x, self.rect.centery), 8)


# ── Interactive Button ────────────────────────────────────────────────────────
class EditorButton:
    def __init__(
        self,
        rect: pg.Rect,
        text: str,
        color_theme: Tuple[int, int, int] = C_PANEL,
        text_color: Tuple[int, int, int] = C_TEXT,
        border_color: Tuple[int, int, int] = C_BORDER,
        tooltip: str = "",
        badge: Optional[str] = None,
    ):
        self.rect = rect
        self.text = text
        self.color_theme = color_theme
        self.text_color = text_color
        self.border_color = border_color
        self.tooltip = tooltip
        self.badge = badge
        self.hovered = False
        self.is_active = False

    def handle_event(self, event: pg.event.Event) -> bool:
        if event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                return True
        return False

    def draw(self, surface: pg.Surface, font: pg.font.Font) -> None:
        m_pos = pg.mouse.get_pos()
        self.hovered = self.rect.collidepoint(m_pos)

        if self.is_active:
            bg_col = C_SEL
            bdr_col = C_CYAN
        elif self.hovered:
            bg_col = (
                min(255, self.color_theme[0] + 25),
                min(255, self.color_theme[1] + 25),
                min(255, self.color_theme[2] + 35),
            )
            bdr_col = C_BORDER_HI
        else:
            bg_col = self.color_theme
            bdr_col = self.border_color

        pg.draw.rect(surface, bg_col, self.rect, border_radius=8)
        pg.draw.rect(surface, bdr_col, self.rect, width=1, border_radius=8)

        txt_surf = font.render(self.text, True, self.text_color)
        t_rect = txt_surf.get_rect(center=self.rect.center)
        surface.blit(txt_surf, t_rect)


# ── Editable Text Input Field ─────────────────────────────────────────────────
class EditorTextInput:
    def __init__(self, rect: pg.Rect, label: str, initial_text: str = ""):
        self.rect = rect
        self.label = label
        self.text = initial_text
        self.active = False
        self.cursor_timer = 0.0

    def handle_event(self, event: pg.event.Event) -> bool:
        if event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
            self.active = self.rect.collidepoint(event.pos)
            return self.active
        if self.active and event.type == pg.KEYDOWN:
            if event.key == pg.K_BACKSPACE:
                self.text = self.text[:-1]
                return True
            elif event.key == pg.K_RETURN:
                self.active = False
                return True
            elif event.unicode and len(self.text) < 160:
                self.text += event.unicode
                return True
        return False

    def update(self, dt: float) -> None:
        self.cursor_timer = (self.cursor_timer + dt) % 1.0

    def draw(self, surface: pg.Surface, font_lbl: pg.font.Font, font_txt: pg.font.Font) -> None:
        # Draw Label
        lbl_surf = font_lbl.render(self.label, True, C_MUTED)
        surface.blit(lbl_surf, (self.rect.x, self.rect.y - 18))

        # Box
        bdr_col = C_CYAN if self.active else C_BORDER
        bg_col = (15, 18, 28) if self.active else C_PANEL_DARK
        pg.draw.rect(surface, bg_col, self.rect, border_radius=6)
        pg.draw.rect(surface, bdr_col, self.rect, width=1, border_radius=6)

        # Content clipping
        disp_text = self.text
        txt_surf = font_txt.render(disp_text, True, C_TEXT)
        surface.blit(txt_surf, (self.rect.x + 8, self.rect.y + 6))

        if self.active and self.cursor_timer < 0.5:
            cx = self.rect.x + 8 + txt_surf.get_width() + 2
            cy = self.rect.y + 5
            pg.draw.line(surface, C_GOLD, (cx, cy), (cx, cy + 18), 2)


# ══════════════════════════════════════════════════════════════════════════════
#  Main Notification Editor Application
# ══════════════════════════════════════════════════════════════════════════════
class NotificationEditorApp:
    SAMPLE_MESSAGES = [
        {
            "id": "taunt_kill",
            "name": "Grimoire First Kill",
            "title": "Cursed Grimoire",
            "body": "The blood of the forest is on your hands. There is no turning back now, wanderer.",
        },
        {
            "id": "taunt_encounter",
            "name": "Grimoire Encounter",
            "title": "Whispers of the Tome",
            "body": "Those who enter the deep woods wither into husks. Prepare your steel, or perish.",
        },
        {
            "id": "taunt_combat",
            "name": "Zombie In-Combat",
            "title": "Blood Zombie",
            "body": "Thou callest that a swing?! Come closer, whelp, my teeth are thirsty!",
        },
        {
            "id": "milestone_short",
            "name": "Relic Milestone",
            "title": "Ancient Relic",
            "body": "Memory Fragment II recovered. Corruption reduced.",
        },
        {
            "id": "lore_long",
            "name": "Eldritch Archive",
            "title": "Eldritch Archive",
            "body": "The pact sealed long ago in ash and iron bound the warrior to the tome. Each strike claims a tithe of humanity, until only the demon remains.",
        },
    ]

    COLOR_KEYS = [
        ("bg_color", "Card Background", True),
        ("inner_color", "Inner Depth Fill", True),
        ("border_color", "Card Border", True),
        ("accent_notch_color", "Left Accent Ribbon", True),
        ("badge_bg_color", "Badge Background", True),
        ("badge_border_color", "Badge Border", True),
        ("title_color", "Title Text", False),
        ("title_shadow_color", "Title Drop Shadow", False),
        ("body_color", "Body Text", False),
        ("body_shadow_color", "Body Drop Shadow", False),
    ]

    QUICK_PALETTES = [
        ("Gothic Gold", [218, 165, 32, 230]),
        ("Obsidian", [16, 12, 24, 235]),
        ("Eldritch Blood", [200, 30, 45, 240]),
        ("Arcane Cyan", [0, 210, 255, 230]),
        ("Bone White", [240, 235, 225, 240]),
        ("Dark Glass", [12, 14, 20, 220]),
    ]

    def __init__(self, headless: bool = False):
        self.headless = headless
        self.sw, self.sh = 1440, 880

        if not pg.get_init():
            pg.init()
        if not pg.font.get_init():
            pg.font.init()

        if headless:
            if not pg.display.get_surface():
                pg.display.set_mode((self.sw, self.sh), pg.HIDDEN)
            self.screen = pg.display.get_surface() or pg.Surface((self.sw, self.sh))
        else:
            self.screen = pg.display.set_mode((self.sw, self.sh))
            pg.display.set_caption("Notification & Pop-Up Plugin Editor  ·  Pixel Runner")

        self.clock = pg.time.Clock()
        self.running = True

        # Load Fonts
        self.f_title = make_sys_font(20, bold=True)
        self.f_head  = make_sys_font(15, bold=True)
        self.f_body  = make_sys_font(13)
        self.f_small = make_sys_font(11)
        self.f_badge = make_sys_font(10, bold=True)

        # Config Data
        self.config_mgr = NotificationConfigManager.get_instance()
        self.data: Dict[str, Any] = json.loads(json.dumps(self.config_mgr.data))

        # Status & Feedback
        self.status_msg = "Ready. Configure timing, layout, colors, or apply curated themes."
        self.status_timer = 0.0

        # Tabs: "timing", "layout", "colors", "typography"
        self.current_tab = "timing"

        # Color picker active state
        self.selected_color_key = "bg_color"

        # Simulation Viewport & SideNotification instance
        self.preview_surface = pg.Surface((1280, 720))
        self.viewport_rect = pg.Rect(20, 68, 800, 450)
        self.side_notif = SideNotification(1280, 720, config_manager=self.config_mgr)

        # Animation Playback State
        self.is_paused = False
        self.sample_idx = 0
        self.input_title = EditorTextInput(
            pg.Rect(20, 672, 280, 32), "Custom Title", self.SAMPLE_MESSAGES[0]["title"]
        )
        self.input_body = EditorTextInput(
            pg.Rect(310, 672, 510, 32), "Custom Body Message", self.SAMPLE_MESSAGES[0]["body"]
        )

        # In-game background surface for preview
        self.bg_backdrop: Optional[pg.Surface] = None
        self._load_background_backdrop()

        # Build UI Controls
        self._init_controls()

        # Trigger initial notification
        self.trigger_notification()

    def _load_background_backdrop(self) -> None:
        """Load in-game background to make pop-up preview 100% authentic."""
        bg_paths = [
            "assets/graphics/background images/middleground.png",
            "assets/graphics/background images/background.png",
        ]
        for p in bg_paths:
            if os.path.exists(p):
                try:
                    img = pg.image.load(p).convert()
                    self.bg_backdrop = pg.transform.smoothscale(img, (1280, 720))
                    break
                except Exception:
                    pass

        if not self.bg_backdrop:
            self.bg_backdrop = pg.Surface((1280, 720))
            self.bg_backdrop.fill((20, 24, 38))
            # Draw subtle atmospheric ground
            pg.draw.rect(self.bg_backdrop, (32, 28, 24), (0, 606, 1280, 114))
            pg.draw.line(self.bg_backdrop, (60, 50, 40), (0, 606), (1280, 606), 2)

    def _init_controls(self) -> None:
        """Create tab buttons, sliders, color pickers, and preset buttons."""
        # Top Bar Action Buttons
        self.btn_save = EditorButton(pg.Rect(1140, 14, 130, 34), "💾 Save Config", color_theme=(25, 80, 50), text_color=C_WHITE)
        self.btn_reset = EditorButton(pg.Rect(1280, 14, 140, 34), "↺ Reset Defaults", color_theme=(60, 35, 45), text_color=C_WHITE)

        # Playback Controls under Viewport
        self.btn_trigger = EditorButton(pg.Rect(20, 526, 130, 32), "▶ Trigger Pop-up", color_theme=(30, 60, 100), text_color=C_CYAN)
        self.btn_pause = EditorButton(pg.Rect(160, 526, 110, 32), "⏸ Pause", color_theme=C_PANEL, text_color=C_TEXT)
        self.btn_reset_anim = EditorButton(pg.Rect(280, 526, 90, 32), "↺ Reset", color_theme=C_PANEL, text_color=C_TEXT)

        # Tab Selection Buttons
        tab_names = [("timing", "⏱ Timing"), ("layout", "📐 Layout"), ("colors", "🎨 Colors"), ("typography", "🔤 Typography")]
        self.tab_buttons: Dict[str, EditorButton] = {}
        tx = 840
        for tab_id, tab_label in tab_names:
            btn = EditorButton(pg.Rect(tx, 68, 142, 34), tab_label, color_theme=C_PANEL)
            self.tab_buttons[tab_id] = btn
            tx += 148

        # Timing Sliders & Toggles
        self.timing_sliders: List[EditorSlider] = [
            EditorSlider("Slide-In Time", "timing", "slide_in_time", 850, 120, 560, 0.10, 1.50, self.data["timing"]["slide_in_time"], is_float=True, format_str="{val:.2f}", unit="s"),
            EditorSlider("Base Hold Duration", "timing", "default_hold_time", 850, 175, 560, 1.0, 20.0, self.data["timing"]["default_hold_time"], is_float=True, format_str="{val:.1f}", unit="s"),
            EditorSlider("Slide-Out Time", "timing", "slide_out_time", 850, 230, 560, 0.10, 1.50, self.data["timing"]["slide_out_time"], is_float=True, format_str="{val:.2f}", unit="s"),
            EditorSlider("Hold Time Per Word", "timing", "words_per_sec", 850, 285, 560, 0.00, 1.00, self.data["timing"]["words_per_sec"], is_float=True, format_str="{val:.2f}", unit="s/word"),
            EditorSlider("Word Calc Base Pad", "timing", "base_hold_pad", 850, 340, 560, 0.0, 6.0, self.data["timing"]["base_hold_pad"], is_float=True, format_str="{val:.1f}", unit="s"),
            EditorSlider("Breath Shimmer Speed", "timing", "breath_speed", 850, 395, 560, 0.5, 8.0, self.data["timing"]["breath_speed"], is_float=True, format_str="{val:.1f}", unit="rad/s"),
            EditorSlider("Breath Shimmer Amplitude", "timing", "breath_amplitude", 850, 450, 560, 0.0, 10.0, self.data["timing"]["breath_amplitude"], is_float=True, format_str="{val:.1f}", unit="px"),
        ]
        self.timing_toggles: List[EditorToggle] = [
            EditorToggle("Floating Breath Oscillation", "timing", "breath_shimmer_enabled", 850, 515, self.data["timing"]["breath_shimmer_enabled"]),
            EditorToggle("Fade Out Alpha on Exit", "timing", "fade_on_slide_out", 850, 555, self.data["timing"]["fade_on_slide_out"]),
        ]

        # Layout Sliders & Toggles
        self.layout_sliders: List[EditorSlider] = [
            EditorSlider("Card Width", "layout", "tab_width", 850, 115, 560, 260, 600, self.data["layout"]["tab_width"], is_float=False, format_str="{val}", unit="px"),
            EditorSlider("Minimum Card Height", "layout", "min_height", 850, 165, 560, 50, 160, self.data["layout"]["min_height"], is_float=False, format_str="{val}", unit="px"),
            EditorSlider("Screen Margin X (Right)", "layout", "margin_x", 850, 215, 560, 0, 80, self.data["layout"]["margin_x"], is_float=False, format_str="{val}", unit="px"),
            EditorSlider("Screen Y (From Top)", "layout", "top_y", 850, 265, 560, 20, 260, self.data["layout"]["top_y"], is_float=False, format_str="{val}", unit="px"),
            EditorSlider("Internal Padding X", "layout", "padding_x", 850, 315, 560, 4, 32, self.data["layout"]["padding_x"], is_float=False, format_str="{val}", unit="px"),
            EditorSlider("Internal Padding Y", "layout", "padding_y", 850, 365, 560, 4, 32, self.data["layout"]["padding_y"], is_float=False, format_str="{val}", unit="px"),
            EditorSlider("Corner Radius", "layout", "corner_radius", 850, 415, 560, 0, 24, self.data["layout"]["corner_radius"], is_float=False, format_str="{val}", unit="px"),
            EditorSlider("Border Width", "layout", "border_width", 850, 465, 560, 0, 6, self.data["layout"]["border_width"], is_float=False, format_str="{val}", unit="px"),
            EditorSlider("Left Accent Ribbon Width", "layout", "accent_notch_width", 850, 515, 560, 1, 14, self.data["layout"]["accent_notch_width"], is_float=False, format_str="{val}", unit="px"),
            EditorSlider("Icon Badge Frame Size", "layout", "badge_size", 850, 565, 560, 24, 80, self.data["layout"]["badge_size"], is_float=False, format_str="{val}", unit="px"),
            EditorSlider("Icon Inner Size", "layout", "icon_size", 850, 615, 560, 16, 64, self.data["layout"]["icon_size"], is_float=False, format_str="{val}", unit="px"),
            EditorSlider("Title to Body Spacing", "layout", "spacing", 850, 665, 560, 0, 16, self.data["layout"]["spacing"], is_float=False, format_str="{val}", unit="px"),
        ]
        self.layout_toggles: List[EditorToggle] = [
            EditorToggle("Enable Left Accent Ribbon", "layout", "accent_notch_enabled", 850, 725, self.data["layout"]["accent_notch_enabled"]),
        ]

        # Typography Sliders & Toggles
        self.typography_sliders: List[EditorSlider] = [
            EditorSlider("Title Font Size", "typography", "title_font_size", 850, 125, 560, 12, 36, self.data["typography"]["title_font_size"], is_float=False, format_str="{val}", unit="pt"),
            EditorSlider("Body Font Size", "typography", "body_font_size", 850, 185, 560, 10, 26, self.data["typography"]["body_font_size"], is_float=False, format_str="{val}", unit="pt"),
            EditorSlider("Line Spacing Multiplier", "typography", "line_spacing", 850, 245, 560, 0.8, 2.0, self.data["typography"]["line_spacing"], is_float=True, format_str="{val:.2f}", unit="x"),
        ]
        self.typography_toggles: List[EditorToggle] = [
            EditorToggle("Title Drop Shadow", "typography", "title_drop_shadow", 850, 315, self.data["typography"]["title_drop_shadow"]),
            EditorToggle("Body Drop Shadow", "typography", "body_drop_shadow", 850, 365, self.data["typography"]["body_drop_shadow"]),
        ]

        # Color RGBA Sliders (dynamically bind to selected_color_key)
        self.color_r_slider = EditorSlider("Red (R)", "colors", "r", 850, 480, 560, 0, 255, 0, is_float=False, format_str="{val}")
        self.color_g_slider = EditorSlider("Green (G)", "colors", "g", 850, 535, 560, 0, 255, 0, is_float=False, format_str="{val}")
        self.color_b_slider = EditorSlider("Blue (B)", "colors", "b", 850, 590, 560, 0, 255, 0, is_float=False, format_str="{val}")
        self.color_a_slider = EditorSlider("Alpha / Opacity (A)", "colors", "a", 850, 645, 560, 0, 255, 255, is_float=False, format_str="{val}")
        self._sync_color_sliders()

        # Preset Buttons under custom text inputs
        self.theme_buttons: List[Tuple[str, EditorButton]] = []
        preset_items = [
            ("gothic_gold", "Gothic Gold"),
            ("blood_bone", "Blood & Bone"),
            ("arcane_void", "Arcane Void"),
            ("grimoire_leather", "Grimoire Leather"),
            ("clean_minimalist", "Sleek Dark Glass"),
        ]
        px = 20
        for p_key, p_name in preset_items:
            btn = EditorButton(pg.Rect(px, 735, 154, 32), p_name, color_theme=C_PANEL, text_color=C_TEXT)
            self.theme_buttons.append((p_key, btn))
            px += 162

        # Sample message preset chips
        self.sample_buttons: List[EditorButton] = []
        sx = 20
        for i, s in enumerate(self.SAMPLE_MESSAGES):
            btn = EditorButton(pg.Rect(sx, 574, 154, 28), s["name"], color_theme=C_PANEL_DARK, text_color=C_MUTED)
            if i == 0:
                btn.is_active = True
            self.sample_buttons.append(btn)
            sx += 162

    def _sync_color_sliders(self) -> None:
        """Update R, G, B, A sliders from currently selected color in self.data."""
        val = self.data["colors"].get(self.selected_color_key, [255, 255, 255, 255])
        self.color_r_slider.set_value(val[0])
        self.color_g_slider.set_value(val[1])
        self.color_b_slider.set_value(val[2])
        if len(val) >= 4:
            self.color_a_slider.set_value(val[3])
        else:
            self.color_a_slider.set_value(255)

    def trigger_notification(self) -> None:
        """Trigger the pop-up notification with active text and current settings."""
        title = self.input_title.text.strip() or "Pop-Up Notification"
        body = self.input_body.text.strip() or "Sample test notification."

        # Pass current configuration directly to manager and side notification
        self.config_mgr.data = copy.deepcopy(self.data)
        self.side_notif._apply_config(force_rebuild=True)
        self.side_notif._queue.clear()
        self.side_notif._state = NotificationState.IDLE
        self.side_notif.show(body, title)

    def apply_preset(self, preset_key: str) -> None:
        """Apply a curated theme preset and re-sync all sliders."""
        preset = THEME_PRESETS.get(preset_key)
        if not preset:
            return

        if "colors" in preset:
            self.data["colors"].update(preset["colors"])
        if "layout" in preset:
            self.data["layout"].update(preset["layout"])

        self._reload_all_controls_from_data()
        self.status_msg = f"Applied theme preset: '{preset.get('name', preset_key)}'!"
        self.status_timer = 3.5
        self.trigger_notification()

    def _reload_all_controls_from_data(self) -> None:
        """Synchronize all UI controls with self.data state."""
        for s in self.timing_sliders:
            s.set_value(self.data["timing"][s.key])
        for t in self.timing_toggles:
            t.state = bool(self.data["timing"][t.key])

        for s in self.layout_sliders:
            s.set_value(self.data["layout"][s.key])
        for t in self.layout_toggles:
            t.state = bool(self.data["layout"][t.key])

        for s in self.typography_sliders:
            s.set_value(self.data["typography"][s.key])
        for t in self.typography_toggles:
            t.state = bool(self.data["typography"][t.key])

        self._sync_color_sliders()

    def save_configuration(self) -> None:
        """Persist current configuration to game_data/notification_config.json."""
        success = self.config_mgr.save_config(self.data)
        if success:
            self.status_msg = f"Successfully saved configuration to {CONFIG_PATH} (Backup created)!"
            self.side_notif._apply_config(force_rebuild=True)
        else:
            self.status_msg = f"Error: Failed to save to {CONFIG_PATH}!"
        self.status_timer = 4.0

    def reset_defaults(self) -> None:
        """Restore all parameters to factory defaults."""
        self.data = json.loads(json.dumps(DEFAULT_NOTIFICATION_CONFIG))
        self._reload_all_controls_from_data()
        self.status_msg = "Reset all parameters to factory defaults (Unsaved until saved)."
        self.status_timer = 3.5
        self.trigger_notification()

    # ── Event Handling ────────────────────────────────────────────────────────
    def handle_event(self, event: pg.event.Event) -> None:
        if event.type == pg.QUIT:
            self.running = False
            return

        if event.type == pg.KEYDOWN:
            if event.key == pg.K_ESCAPE:
                self.running = False
                return
            elif event.key == pg.K_SPACE and not self.input_title.active and not self.input_body.active:
                self.trigger_notification()
                return

        # Text input fields
        if self.input_title.handle_event(event):
            self.trigger_notification()
            return
        if self.input_body.handle_event(event):
            self.trigger_notification()
            return

        # Top Action Buttons
        if self.btn_save.handle_event(event):
            self.save_configuration()
            return
        if self.btn_reset.handle_event(event):
            self.reset_defaults()
            return

        # Playback Controls
        if self.btn_trigger.handle_event(event):
            self.trigger_notification()
            return
        if self.btn_pause.handle_event(event):
            self.is_paused = not self.is_paused
            self.btn_pause.text = "▶ Resume" if self.is_paused else "⏸ Pause"
            return
        if self.btn_reset_anim.handle_event(event):
            self.trigger_notification()
            return

        # Tab Selection Buttons
        for tab_id, btn in self.tab_buttons.items():
            if btn.handle_event(event):
                self.current_tab = tab_id
                return

        # Sample Message Buttons
        for idx, btn in enumerate(self.sample_buttons):
            if btn.handle_event(event):
                self.sample_idx = idx
                for b in self.sample_buttons:
                    b.is_active = False
                btn.is_active = True
                msg = self.SAMPLE_MESSAGES[idx]
                self.input_title.text = msg["title"]
                self.input_body.text = msg["body"]
                self.trigger_notification()
                return

        # Theme Preset Buttons
        for p_key, btn in self.theme_buttons:
            if btn.handle_event(event):
                self.apply_preset(p_key)
                return

        # Tab-Specific Control Handling
        if self.current_tab == "timing":
            for s in self.timing_sliders:
                if s.handle_event(event):
                    self.data["timing"][s.key] = s.val
                    self.config_mgr.data["timing"][s.key] = s.val
                    self.side_notif._apply_config(force_rebuild=True)
            for t in self.timing_toggles:
                if t.handle_event(event):
                    self.data["timing"][t.key] = t.state
                    self.config_mgr.data["timing"][t.key] = t.state
                    self.side_notif._apply_config(force_rebuild=True)

        elif self.current_tab == "layout":
            for s in self.layout_sliders:
                if s.handle_event(event):
                    self.data["layout"][s.key] = int(s.val)
                    self.config_mgr.data["layout"][s.key] = int(s.val)
                    self.side_notif._apply_config(force_rebuild=True)
            for t in self.layout_toggles:
                if t.handle_event(event):
                    self.data["layout"][t.key] = t.state
                    self.config_mgr.data["layout"][t.key] = t.state
                    self.side_notif._apply_config(force_rebuild=True)

        elif self.current_tab == "typography":
            for s in self.typography_sliders:
                if s.handle_event(event):
                    self.data["typography"][s.key] = s.val if s.is_float else int(s.val)
                    self.config_mgr.data["typography"][s.key] = self.data["typography"][s.key]
                    self.side_notif._apply_config(force_rebuild=True)
            for t in self.typography_toggles:
                if t.handle_event(event):
                    self.data["typography"][t.key] = t.state
                    self.config_mgr.data["typography"][t.key] = t.state
                    self.side_notif._apply_config(force_rebuild=True)

        elif self.current_tab == "colors":
            # Color list selector click detection
            if event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
                cy = 120
                for c_key, c_name, has_a in self.COLOR_KEYS:
                    row_rect = pg.Rect(850, cy, 560, 32)
                    if row_rect.collidepoint(event.pos):
                        self.selected_color_key = c_key
                        self._sync_color_sliders()
                        break
                    cy += 34

                # Quick palette chips
                qy = 705
                qx = 850
                for pal_name, pal_val in self.QUICK_PALETTES:
                    chip_rect = pg.Rect(qx, qy, 90, 26)
                    if chip_rect.collidepoint(event.pos):
                        # Apply to currently selected color
                        current_c = self.data["colors"][self.selected_color_key]
                        if len(current_c) >= 4 and len(pal_val) >= 4:
                            self.data["colors"][self.selected_color_key] = list(pal_val)
                        else:
                            self.data["colors"][self.selected_color_key] = list(pal_val[:len(current_c)])
                        self._sync_color_sliders()
                        self.config_mgr.data["colors"][self.selected_color_key] = self.data["colors"][self.selected_color_key]
                        self.side_notif._apply_config(force_rebuild=True)
                        break
                    qx += 95

            # Handle RGBA sliders
            c_changed = False
            if self.color_r_slider.handle_event(event):
                c_changed = True
            if self.color_g_slider.handle_event(event):
                c_changed = True
            if self.color_b_slider.handle_event(event):
                c_changed = True
            if self.color_a_slider.handle_event(event):
                c_changed = True

            if c_changed:
                curr_c = self.data["colors"][self.selected_color_key]
                new_c = [
                    int(self.color_r_slider.val),
                    int(self.color_g_slider.val),
                    int(self.color_b_slider.val),
                ]
                if len(curr_c) >= 4:
                    new_c.append(int(self.color_a_slider.val))
                self.data["colors"][self.selected_color_key] = new_c
                self.config_mgr.data["colors"][self.selected_color_key] = new_c
                self.side_notif._apply_config(force_rebuild=True)

    # ── Update & Rendering ────────────────────────────────────────────────────
    def update(self, dt: float) -> None:
        if self.status_timer > 0:
            self.status_timer -= dt

        self.input_title.update(dt)
        self.input_body.update(dt)

        if not self.is_paused:
            self.side_notif.update(dt)

        # Tab button active states
        for tab_id, btn in self.tab_buttons.items():
            btn.is_active = (self.current_tab == tab_id)

    def draw(self) -> None:
        self.screen.fill(C_BG)

        # 1. Top Navigation Bar
        hdr_rect = pg.Rect(0, 0, self.sw, 56)
        pg.draw.rect(self.screen, C_HEADER, hdr_rect)
        pg.draw.line(self.screen, C_BORDER, (0, 56), (self.sw, 56), 1)

        txt_title = self.f_title.render("POP-UP & NOTIFICATION EDITOR", True, C_GOLD)
        self.screen.blit(txt_title, (20, 16))
        txt_sub = self.f_body.render("Interactive Live Staging & Configuration Plugin", True, C_MUTED)
        self.screen.blit(txt_sub, (370, 20))

        self.btn_save.draw(self.screen, self.f_body)
        self.btn_reset.draw(self.screen, self.f_body)

        # 2. Status Message Strip
        status_col = C_GREEN if "Successfully" in self.status_msg or "Applied" in self.status_msg else C_TEXT
        txt_status = self.f_small.render(f"● {self.status_msg}", True, status_col)
        self.screen.blit(txt_status, (20, 785))

        txt_hotreload = self.f_small.render("⚡ Hot-reloading active — game updates automatically on save", True, C_CYAN)
        self.screen.blit(txt_hotreload, (self.sw - txt_hotreload.get_width() - 20, 785))

        # 3. Left Panel — Simulation Viewport
        self._draw_simulation_viewport()

        # 4. Under Viewport Controls (Playback, Presets, Custom Text)
        self._draw_viewport_controls()

        # 5. Right Panel — Inspector Tabs
        self._draw_inspector_panel()

        if not self.headless:
            pg.display.flip()

    def _draw_simulation_viewport(self) -> None:
        """Render the 1280x720 simulated game screen scaled into the editor window."""
        # Draw frame panel
        frame_rect = self.viewport_rect.inflate(12, 12)
        pg.draw.rect(self.screen, C_PANEL, frame_rect, border_radius=10)
        pg.draw.rect(self.screen, C_BORDER, frame_rect, width=1, border_radius=10)

        # Render 1280x720 canvas
        if self.bg_backdrop:
            self.preview_surface.blit(self.bg_backdrop, (0, 0))
        else:
            self.preview_surface.fill((16, 20, 30))

        # In-game HUD Mock overlay (Top-Left & Top-Right)
        self._draw_mock_hud(self.preview_surface)

        # Live SideNotification
        self.side_notif.draw(self.preview_surface)

        # Blit scaled preview surface onto screen
        scaled_preview = pg.transform.smoothscale(self.preview_surface, (self.viewport_rect.width, self.viewport_rect.height))
        self.screen.blit(scaled_preview, self.viewport_rect.topleft)

        # Frame outline over scaled surface
        pg.draw.rect(self.screen, C_BORDER_HI, self.viewport_rect, width=1)

    def _draw_mock_hud(self, surface: pg.Surface) -> None:
        """Draw realistic in-game HUD elements so positioning is accurate."""
        # Top-Right Time & Distance Counters
        hud_box = pg.Rect(1020, 20, 240, 50)
        pg.draw.rect(surface, (14, 16, 26, 210), hud_box, border_radius=6)
        pg.draw.rect(surface, (70, 85, 120, 180), hud_box, width=1, border_radius=6)

        t_hud = self.f_head.render("TIME: 02:45  ·  DIST: 680m", True, C_GOLD)
        surface.blit(t_hud, (hud_box.x + 14, hud_box.y + 16))

        # Top-Left Health & Mana Bars
        hp_bar_bg = pg.Rect(30, 25, 200, 16)
        pg.draw.rect(surface, (30, 20, 25), hp_bar_bg, border_radius=4)
        hp_fill = pg.Rect(30, 25, 170, 16)
        pg.draw.rect(surface, (220, 45, 60), hp_fill, border_radius=4)
        pg.draw.rect(surface, (100, 40, 50), hp_bar_bg, width=1, border_radius=4)

        mana_bar_bg = pg.Rect(30, 46, 160, 12)
        pg.draw.rect(surface, (15, 25, 40), mana_bar_bg, border_radius=3)
        mana_fill = pg.Rect(30, 46, 130, 12)
        pg.draw.rect(surface, (0, 180, 240), mana_fill, border_radius=3)
        pg.draw.rect(surface, (40, 70, 100), mana_bar_bg, width=1, border_radius=3)

    def _draw_viewport_controls(self) -> None:
        """Render animation status bar, playback buttons, sample messages, and custom text inputs."""
        # 1. Playback buttons
        self.btn_trigger.draw(self.screen, self.f_body)
        self.btn_pause.draw(self.screen, self.f_body)
        self.btn_reset_anim.draw(self.screen, self.f_body)

        # 2. Live Animation Status Chip
        state_colors = {
            NotificationState.IDLE: C_MUTED,
            NotificationState.SLIDE_IN: C_GREEN,
            NotificationState.HOLD: C_CYAN,
            NotificationState.SLIDE_OUT: C_ORANGE,
        }
        st = self.side_notif._state
        st_color = state_colors.get(st, C_TEXT)
        st_text = f"STATE: {st.name}"
        if st == NotificationState.HOLD and self.side_notif._current_item:
            hold_total = self.side_notif._current_item.hold
            st_text += f" ({self.side_notif._timer:.1f}s / {hold_total:.1f}s)"

        chip_surf = self.f_head.render(st_text, True, st_color)
        chip_rect = pg.Rect(400, 528, chip_surf.get_width() + 16, 28)
        pg.draw.rect(self.screen, C_PANEL, chip_rect, border_radius=6)
        pg.draw.rect(self.screen, st_color, chip_rect, width=1, border_radius=6)
        self.screen.blit(chip_surf, (chip_rect.x + 8, chip_rect.y + 5))

        # 3. Sample Message Preset Buttons
        lbl_samples = self.f_small.render("SAMPLE NARRATIVE & TAUNT PRESETS:", True, C_MUTED)
        self.screen.blit(lbl_samples, (20, 560))
        for btn in self.sample_buttons:
            btn.draw(self.screen, self.f_small)

        # 4. Custom Inputs
        self.input_title.draw(self.screen, self.f_small, self.f_body)
        self.input_body.draw(self.screen, self.f_small, self.f_body)

        # 5. Curated Themes
        lbl_themes = self.f_small.render("ONE-CLICK CURATED THEMES & PRESETS:", True, C_MUTED)
        self.screen.blit(lbl_themes, (20, 718))
        for _, btn in self.theme_buttons:
            btn.draw(self.screen, self.f_small)

    def _draw_inspector_panel(self) -> None:
        """Render the right inspector tab and controls."""
        panel_rect = pg.Rect(840, 110, 580, 660)
        pg.draw.rect(self.screen, C_PANEL, panel_rect, border_radius=10)
        pg.draw.rect(self.screen, C_BORDER, panel_rect, width=1, border_radius=10)

        # Draw tab buttons
        for btn in self.tab_buttons.values():
            btn.draw(self.screen, self.f_body)

        # Render Active Tab Controls
        if self.current_tab == "timing":
            for s in self.timing_sliders:
                s.draw(self.screen, self.f_small, self.f_body)
            for t in self.timing_toggles:
                t.draw(self.screen, self.f_body)

        elif self.current_tab == "layout":
            for s in self.layout_sliders:
                s.draw(self.screen, self.f_small, self.f_body)
            for t in self.layout_toggles:
                t.draw(self.screen, self.f_body)

        elif self.current_tab == "typography":
            for s in self.typography_sliders:
                s.draw(self.screen, self.f_small, self.f_body)
            for t in self.typography_toggles:
                t.draw(self.screen, self.f_body)

        elif self.current_tab == "colors":
            self._draw_color_tab(panel_rect)

    def _draw_color_tab(self, panel_rect: pg.Rect) -> None:
        """Render the color picker inspector."""
        # Top: List of 10 color attributes
        cy = 120
        for c_key, c_name, has_a in self.COLOR_KEYS:
            row_rect = pg.Rect(850, cy, 560, 30)
            is_sel = (c_key == self.selected_color_key)

            bg_row = C_SEL if is_sel else (C_PANEL_DARK if (cy // 32) % 2 == 0 else C_PANEL)
            pg.draw.rect(self.screen, bg_row, row_rect, border_radius=6)
            if is_sel:
                pg.draw.rect(self.screen, C_CYAN, row_rect, width=1, border_radius=6)

            # Color Swatch Box
            c_val = self.data["colors"].get(c_key, [255, 255, 255, 255])
            swatch_rect = pg.Rect(856, cy + 4, 38, 22)
            # Checkerboard background for alpha preview
            pg.draw.rect(self.screen, (80, 80, 80), swatch_rect, border_radius=4)
            pg.draw.rect(self.screen, (140, 140, 140), (856, cy + 4, 19, 11))
            pg.draw.rect(self.screen, (140, 140, 140), (875, cy + 15, 19, 11))

            swatch_surf = pg.Surface((38, 22), pg.SRCALPHA)
            swatch_surf.fill(tuple(c_val))
            self.screen.blit(swatch_surf, swatch_rect.topleft)
            pg.draw.rect(self.screen, C_BORDER_HI, swatch_rect, width=1, border_radius=4)

            # Label & Value text
            lbl_color = C_GOLD if is_sel else C_TEXT
            txt_lbl = self.f_body.render(c_name, True, lbl_color)
            self.screen.blit(txt_lbl, (906, cy + 6))

            hex_code = "#{:02X}{:02X}{:02X}".format(*c_val[:3])
            if len(c_val) >= 4:
                hex_code += f" ({c_val[3]}a)"
            txt_hex = self.f_small.render(hex_code, True, C_MUTED)
            self.screen.blit(txt_hex, (row_rect.right - txt_hex.get_width() - 12, cy + 7))

            cy += 34

        # Divider
        pg.draw.line(self.screen, C_BORDER, (850, 465), (1410, 465), 1)

        # Active Color RGBA Sliders
        active_c = self.data["colors"][self.selected_color_key]
        has_alpha = len(active_c) >= 4
        self.color_r_slider.draw(self.screen, self.f_small, self.f_body)
        self.color_g_slider.draw(self.screen, self.f_small, self.f_body)
        self.color_b_slider.draw(self.screen, self.f_small, self.f_body)
        if has_alpha:
            self.color_a_slider.draw(self.screen, self.f_small, self.f_body)

        # Quick Palette chips at bottom
        lbl_pal = self.f_small.render("QUICK SWATCHES:", True, C_MUTED)
        self.screen.blit(lbl_pal, (850, 685))

        qy = 705
        qx = 850
        for pal_name, pal_val in self.QUICK_PALETTES:
            chip_rect = pg.Rect(qx, qy, 90, 26)
            pg.draw.rect(self.screen, (25, 30, 45), chip_rect, border_radius=6)
            pg.draw.rect(self.screen, C_BORDER, chip_rect, width=1, border_radius=6)

            # mini swatch
            swatch_mini = pg.Rect(qx + 4, qy + 4, 18, 18)
            swatch_s = pg.Surface((18, 18), pg.SRCALPHA)
            swatch_s.fill(tuple(pal_val))
            self.screen.blit(swatch_s, swatch_mini.topleft)
            pg.draw.rect(self.screen, C_BORDER_HI, swatch_mini, width=1, border_radius=3)

            txt_chip = self.f_badge.render(pal_name[:8], True, C_TEXT)
            self.screen.blit(txt_chip, (qx + 26, qy + 6))
            qx += 95


def main() -> None:
    """Launch the notification plugin editor."""
    import argparse
    parser = argparse.ArgumentParser(description="Notification & Pop-up Plugin Editor for Pixel Runner")
    parser.add_argument("--smoke", action="store_true", help="Run in headless smoke test mode and exit cleanly")
    args = parser.parse_args()

    app = NotificationEditorApp(headless=args.smoke)

    if args.smoke:
        print("[NotificationEditor] Smoke test initializing...")
        app.update(0.016)
        app.draw()
        app.trigger_notification()
        app.update(0.1)
        app.draw()
        print("[NotificationEditor] Smoke test passed successfully.")
        pg.quit()
        sys.exit(0)

    # Interactive Loop
    while app.running:
        dt = app.clock.tick(60) / 1000.0
        for event in pg.event.get():
            app.handle_event(event)
        app.update(dt)
        app.draw()

    pg.quit()
    sys.exit(0)


if __name__ == "__main__":
    main()
