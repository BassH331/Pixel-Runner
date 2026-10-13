#!/usr/bin/env python3
"""
the_eye.py — 3D Interactive Story Tree & Dialogue Controller for Pixel-Runner.

"The Eye" is an interactive 3D narrative perception controller.
It renders the player's full journey as a living 3D narrative tree (Yggdrasil of Discord):
- Trunk / Spine: Timeline distance progressing upwards through the 4 Acts (0m to 36,000m).
- Major Branches: Branching out in 3D golden-ratio spiral to distance milestones and entities.
- Speech / Taunt Leaves: Sprouting from each entity:
  * [TAUNT]: Crimson glowing thorns/crystals triggering in-combat audio barks & side pop-ups.
  * [DIALOGUE]: Cyan glowing runes/orbs triggering cinematic narrative overlays & cutscenes.

Interactive 3D Controls:
- Left-Click & Drag: 360° Orbit camera rotation (Yaw & Pitch)
- Right-Click & Drag: Pan camera in 3D space
- Mouse Wheel: Smooth Zoom in / out (250px to 1800px)
- Node Picking: Click any 3D node to inspect properties and anchor view
- Mode Switcher: Toggle between [🌌 3D Interactive Tree] and [📋 2D Hierarchy TreeView]
"""

from __future__ import annotations

import os
import sys
import math
import time
import copy
import json
from typing import Optional, Dict, List, Tuple, Any

import pygame as pg

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from src.game.systems.the_eye_manager import (
    TheEyePerceptionManager,
    StoryNode,
    SpeechItem,
    TreeItem,
    GameEventItem,
    EVENT_CATEGORIES,
    EVENT_CATEGORY_ICONS,
    LEVEL_1_PATH,
    STORYLINE_PATH,
    NOTIFICATION_EVENTS_PATH,
)
from src.game.ui.side_notification import SideNotification

# ── Color Palette ─────────────────────────────────────────────────────────────
C_BG            = (  8,  10,  16)
C_PANEL         = ( 16,  20,  32)
C_PANEL_DARK    = ( 12,  15,  24)
C_HEADER        = ( 20,  25,  40)
C_BORDER        = ( 38,  48,  74)
C_BORDER_HI     = ( 70,  90, 140)
C_TEXT          = (232, 238, 252)
C_MUTED         = (120, 134, 164)

# Celestial & Occult Accents
C_GOLD          = (255, 215,  75)
C_GOLD_DARK     = (180, 140,  30)
C_PURPLE        = (175,  75, 255)
C_PURPLE_DARK   = ( 90,  35, 140)
C_CYAN          = (  0, 220, 255)
C_CYAN_GLOW     = (  0, 160, 220)
C_GREEN         = (  0, 225, 120)
C_CRIMSON       = (240,  55,  75)
C_CRIMSON_GLOW  = (180,  30,  50)
C_CRIMSON_DARK  = (140,  25,  40)
C_ORANGE        = (255, 145,  35)
C_WHITE         = (255, 255, 255)
C_SEL_BG        = ( 28,  55,  95)
C_SEL_LINE      = (  0, 200, 255)

NODE_COLORS = {
    "NPC":       C_CYAN,
    "ENEMY":     C_ORANGE,
    "MINI-BOSS": C_CRIMSON,
    "BOSS":      C_GOLD,
    "RELIC":     C_PURPLE,
    "LORE":      C_GREEN,
}

EVENT_COLORS = {
    "INTERACTION":    C_CYAN,
    "RELIC":          C_PURPLE,
    "SOUL_QUOTA":     C_GREEN,
    "LEVEL_COMPLETE": C_GOLD,
    "AMBIENT_LORE":   C_ORANGE,
    "ITEM_DISCOVERY": C_CRIMSON,
}

EVENT_GLYPHS = {
    "INTERACTION":    "[ACT]",
    "RELIC":          "[RLC]",
    "SOUL_QUOTA":     "[QTA]",
    "LEVEL_COMPLETE": "[EXT]",
    "AMBIENT_LORE":   "[LOR]",
    "ITEM_DISCOVERY": "[ITM]",
}


def draw_event_category_icon(surface: pg.Surface, cat: str, color: Tuple[int, int, int], cx: int, cy: int, size: int = 16) -> None:
    """Draw crisp arcade vector icon without font/emoji dependency."""
    half = size // 2
    if cat == "RELIC":
        pts = [(cx, cy - half), (cx + half, cy), (cx, cy + half), (cx - half, cy)]
        pg.draw.polygon(surface, color, pts)
        pg.draw.polygon(surface, C_WHITE, pts, width=1)
    elif cat == "INTERACTION":
        pg.draw.circle(surface, color, (cx, cy), max(2, half // 2))
        pg.draw.line(surface, C_WHITE, (cx - half, cy), (cx + half, cy), 2)
        pg.draw.line(surface, C_WHITE, (cx, cy - half), (cx, cy + half), 2)
    elif cat == "SOUL_QUOTA":
        pg.draw.circle(surface, (*color[:3], 120), (cx, cy), half)
        pg.draw.circle(surface, color, (cx, cy), max(2, half - 3))
        pg.draw.circle(surface, C_WHITE, (cx, cy), 2)
    elif cat == "LEVEL_COMPLETE":
        pts = [(cx - half, cy + half - 2), (cx, cy - half), (cx + half, cy + half - 2)]
        pg.draw.polygon(surface, color, pts)
        pg.draw.polygon(surface, C_GOLD, pts, width=1)
    elif cat == "AMBIENT_LORE":
        s_rect = pg.Rect(cx - half + 2, cy - half + 1, size - 4, size - 2)
        pg.draw.rect(surface, color, s_rect, border_radius=2)
        pg.draw.line(surface, C_WHITE, (cx - half + 4, cy - 2), (cx + half - 4, cy - 2), 1)
        pg.draw.line(surface, C_WHITE, (cx - half + 4, cy + 2), (cx + half - 4, cy + 2), 1)
    elif cat == "ITEM_DISCOVERY":
        pts = [(cx, cy - half), (cx + half, cy), (cx, cy + half), (cx - half, cy)]
        pg.draw.polygon(surface, color, pts)
        pg.draw.circle(surface, C_WHITE, (cx, cy), 2)
    else:
        pg.draw.circle(surface, color, (cx, cy), half)


def make_font(size: int, bold: bool = False) -> pg.font.Font:
    """Safe system font generator with graceful fallbacks."""
    return pg.font.SysFont("dejavusans,ubuntu,segoeui,arial,helvetica,sans-serif", size, bold=bold)


# ── Animated All-Seeing Eye Widget ────────────────────────────────────────────
class AnimatedAllSeeingEye:
    """Occult animated eye iris that tracks mouse movement and dilates."""

    def __init__(self, cx: int, cy: int, radius: int = 18):
        self.cx = cx
        self.cy = cy
        self.radius = radius
        self.pupil_x = float(cx)
        self.pupil_y = float(cy)
        self.dilation = 1.0
        self.blink_timer = 0.0

    def update(self, dt: float, mouse_pos: Tuple[int, int], gaze_target: Optional[Tuple[int, int]] = None) -> None:
        self.blink_timer += dt
        target_pos = gaze_target if gaze_target is not None else mouse_pos
        dx = target_pos[0] - self.cx
        dy = target_pos[1] - self.cy
        dist = math.hypot(dx, dy)
        max_offset = self.radius * 0.45
        if dist > 0:
            nx = dx / dist
            ny = dy / dist
            offset = min(max_offset, dist * 0.05)
            target_px = self.cx + nx * offset
            target_py = self.cy + ny * offset
        else:
            target_px = self.cx
            target_py = self.cy

        self.pupil_x += (target_px - self.pupil_x) * min(1.0, dt * 10.0)
        self.pupil_y += (target_py - self.pupil_y) * min(1.0, dt * 10.0)
        self.dilation = 1.0 + 0.15 * math.sin(self.blink_timer * 2.5)

    def draw(self, surface: pg.Surface) -> None:
        glow_r = int(self.radius * 1.35)
        glow_surf = pg.Surface((glow_r * 2, glow_r * 2), pg.SRCALPHA)
        pg.draw.circle(glow_surf, (175, 75, 255, 45), (glow_r, glow_r), glow_r)
        surface.blit(glow_surf, (self.cx - glow_r, self.cy - glow_r))

        almond_pts = [
            (self.cx - self.radius - 4, self.cy),
            (self.cx, self.cy - self.radius + 2),
            (self.cx + self.radius + 4, self.cy),
            (self.cx, self.cy + self.radius - 2),
        ]
        pg.draw.polygon(surface, (20, 16, 30), almond_pts)
        pg.draw.lines(surface, C_GOLD, True, almond_pts, width=2)
        pg.draw.circle(surface, (240, 235, 250), (self.cx, self.cy), int(self.radius * 0.8))

        iris_r = int(self.radius * 0.5 * self.dilation)
        pg.draw.circle(surface, C_PURPLE, (int(self.pupil_x), int(self.pupil_y)), iris_r)
        pg.draw.circle(surface, C_CYAN, (int(self.pupil_x), int(self.pupil_y)), max(1, iris_r - 2), width=1)

        pupil_w = max(2, int(iris_r * 0.35))
        pupil_h = max(4, int(iris_r * 0.9))
        pupil_rect = pg.Rect(
            int(self.pupil_x - pupil_w // 2),
            int(self.pupil_y - pupil_h // 2),
            pupil_w,
            pupil_h,
        )
        pg.draw.ellipse(surface, (10, 8, 14), pupil_rect)
        pg.draw.circle(
            surface, C_WHITE, (int(self.pupil_x - pupil_w * 0.7), int(self.pupil_y - pupil_h * 0.4)), 2
        )


# ── Interactive UI Components ─────────────────────────────────────────────────
class EyeButton:
    """Clickable styled button with hover, click press animation, and success flash states."""

    def __init__(
        self,
        rect: pg.Rect,
        text: str,
        color_theme: Tuple[int, int, int] = C_PANEL,
        text_color: Tuple[int, int, int] = C_TEXT,
        border_color: Tuple[int, int, int] = C_BORDER,
    ):
        self.rect = rect
        self.text = text
        self.color_theme = color_theme
        self.text_color = text_color
        self.border_color = border_color
        self.hovered = False
        self.is_active = False
        self.pressed_timer = 0.0
        self.success_timer = 0.0
        self.success_text = ""

    def trigger_success(self, msg: str = "", duration: float = 2.0) -> None:
        """Trigger glowing visual feedback state on button."""
        self.success_timer = duration
        self.success_text = msg

    def update(self, dt: float) -> None:
        """Advance animation timers."""
        if self.pressed_timer > 0:
            self.pressed_timer = max(0.0, self.pressed_timer - dt)
        if self.success_timer > 0:
            self.success_timer = max(0.0, self.success_timer - dt)

    def handle_event(self, event: pg.event.Event) -> bool:
        if event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self.pressed_timer = 0.15
                return True
        return False

    def draw(self, surface: pg.Surface, font: pg.font.Font, dt: float = 0.0) -> None:
        if dt > 0:
            self.update(dt)

        m_pos = pg.mouse.get_pos()
        self.hovered = self.rect.collidepoint(m_pos)

        # Offset rect for press animation (2px down when pressed)
        draw_rect = self.rect.move(0, 2) if self.pressed_timer > 0 else self.rect.copy()

        if self.pressed_timer > 0:
            bg_col = (35, 140, 75)
            bdr_col = (0, 255, 160)
            txt_col = (255, 255, 255)
        elif self.success_timer > 0:
            bg_col = (20, 130, 65)
            bdr_col = (0, 255, 180)
            txt_col = (255, 255, 255)
        elif self.is_active:
            bg_col = C_SEL_BG
            bdr_col = C_CYAN
            txt_col = self.text_color
        elif self.hovered:
            bg_col = (
                min(255, self.color_theme[0] + 25),
                min(255, self.color_theme[1] + 25),
                min(255, self.color_theme[2] + 35),
            )
            bdr_col = C_BORDER_HI
            txt_col = self.text_color
        else:
            bg_col = self.color_theme
            bdr_col = self.border_color
            txt_col = self.text_color

        pg.draw.rect(surface, bg_col, draw_rect, border_radius=6)
        bdr_width = 2 if (self.pressed_timer > 0 or self.success_timer > 0) else 1
        pg.draw.rect(surface, bdr_col, draw_rect, width=bdr_width, border_radius=6)

        display_text = self.success_text if (self.success_timer > 0 and self.success_text) else self.text
        txt_surf = font.render(display_text, True, txt_col)
        surface.blit(txt_surf, txt_surf.get_rect(center=draw_rect.center))



class MultiLineTextInput:
    """Full-featured multi-line editable text box with cursor and wrapping."""

    def __init__(self, rect: pg.Rect, label: str = ""):
        self.rect = rect
        self.label = label
        self.text = ""
        self.active = False
        self.cursor_timer = 0.0

    def set_text(self, text: str) -> None:
        self.text = text or ""

    def handle_event(self, event: pg.event.Event) -> bool:
        if event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
            self.active = self.rect.collidepoint(event.pos)
            return self.active

        if self.active and event.type == pg.KEYDOWN:
            if event.key == pg.K_BACKSPACE:
                self.text = self.text[:-1]
                return True
            elif event.key == pg.K_RETURN:
                self.text += "\n"
                return True
            elif event.key == pg.K_TAB:
                self.text += "    "
                return True
            elif event.unicode and len(self.text) < 600:
                self.text += event.unicode
                return True
        return False

    def update(self, dt: float) -> None:
        self.cursor_timer = (self.cursor_timer + dt) % 1.0

    def draw(self, surface: pg.Surface, font_lbl: pg.font.Font, font_txt: pg.font.Font) -> None:
        bg_col = (14, 18, 28) if self.active else C_PANEL_DARK
        bdr_col = C_CYAN if self.active else C_BORDER
        pg.draw.rect(surface, bg_col, self.rect, border_radius=8)
        pg.draw.rect(surface, bdr_col, self.rect, width=1, border_radius=8)

        # Inline placeholder when text is empty and not active
        if not self.text and not self.active and self.label:
            ph_surf = font_txt.render(self.label, True, (80, 95, 120))
            surface.blit(ph_surf, (self.rect.x + 12, self.rect.y + 12))

        # Word wrap text
        words = self.text.replace("\n", " \n ").split(" ")
        lines = []
        curr_line = ""
        max_w = self.rect.width - 24

        for w in words:
            if w == "\n":
                lines.append(curr_line)
                curr_line = ""
                continue
            test_line = f"{curr_line} {w}".strip() if curr_line else w
            if font_txt.size(test_line)[0] <= max_w:
                curr_line = test_line
            else:
                if curr_line:
                    lines.append(curr_line)
                curr_line = w
        if curr_line:
            lines.append(curr_line)

        line_h = font_txt.get_linesize()
        y = self.rect.y + 10
        for i, line in enumerate(lines[:5]):
            line_surf = font_txt.render(line, True, C_TEXT)
            surface.blit(line_surf, (self.rect.x + 10, y))
            if self.active and i == len(lines) - 1 and self.cursor_timer < 0.5:
                cx = self.rect.x + 10 + line_surf.get_width() + 2
                pg.draw.line(surface, C_GOLD, (cx, y), (cx, y + line_h - 2), 2)
            y += line_h

        if self.active and not self.text and self.cursor_timer < 0.5:
            pg.draw.line(
                surface, C_GOLD, (self.rect.x + 10, self.rect.y + 10), (self.rect.x + 10, self.rect.y + 24), 2
            )

        w_count = len(self.text.split())
        c_count = len(self.text)
        stats = f"{w_count} words | {c_count} chars"
        stat_surf = font_lbl.render(stats, True, C_MUTED)
        surface.blit(stat_surf, (self.rect.right - stat_surf.get_width() - 8, self.rect.bottom - 16))


# ── Search Input Field ────────────────────────────────────────────────────────
class SearchInputField:
    """Compact search text box for filtering Tree nodes."""

    def __init__(self, rect: pg.Rect, placeholder: str = "Filter tree nodes..."):
        self.rect = rect
        self.placeholder = placeholder
        self.text = ""
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
            elif event.key == pg.K_ESCAPE:
                self.text = ""
                self.active = False
                return True
            elif event.unicode and len(self.text) < 40 and event.key != pg.K_RETURN:
                self.text += event.unicode
                return True
        return False

    def update(self, dt: float) -> None:
        self.cursor_timer = (self.cursor_timer + dt) % 1.0

    def draw(self, surface: pg.Surface, font: pg.font.Font) -> None:
        bg_col = (14, 18, 28) if self.active else C_PANEL_DARK
        bdr_col = C_CYAN if self.active else C_BORDER
        pg.draw.rect(surface, bg_col, self.rect, border_radius=6)
        pg.draw.rect(surface, bdr_col, self.rect, width=1, border_radius=6)

        prefix_surf = font.render("Search:", True, C_GOLD)
        surface.blit(prefix_surf, (self.rect.x + 8, self.rect.y + (self.rect.height - prefix_surf.get_height()) // 2))
        px = self.rect.x + 8 + prefix_surf.get_width() + 6

        if self.text:
            txt_surf = font.render(self.text, True, C_TEXT)
            surface.blit(txt_surf, (px, self.rect.y + (self.rect.height - txt_surf.get_height()) // 2))
            if self.active and self.cursor_timer < 0.5:
                cx = px + txt_surf.get_width() + 1
                cy = self.rect.y + 6
                pg.draw.line(surface, C_CYAN, (cx, cy), (cx, cy + self.rect.height - 12), 2)
        else:
            ph_surf = font.render(self.placeholder, True, C_MUTED)
            surface.blit(ph_surf, (px, self.rect.y + (self.rect.height - ph_surf.get_height()) // 2))
            if self.active and self.cursor_timer < 0.5:
                cx = px
                cy = self.rect.y + 6
                pg.draw.line(surface, C_CYAN, (cx, cy), (cx, cy + self.rect.height - 12), 2)


# ══════════════════════════════════════════════════════════════════════════════
#  3D Interactive Tree Engine (Yggdrasil of Discord)
# ══════════════════════════════════════════════════════════════════════════════
class Node3D:
    """A node positioned in 3D coordinate space."""

    def __init__(
        self,
        node_id: str,
        node_type: str,  # "trunk", "milestone", "entity", "speech"
        x: float,
        y: float,
        z: float,
        label: str,
        data: Any = None,
        is_taunt: Optional[bool] = None,
        color: Tuple[int, int, int] = C_CYAN,
        radius: float = 8.0,
        parent_id: Optional[str] = None,
    ):
        self.node_id = node_id
        self.node_type = node_type
        self.x = x
        self.y = y
        self.z = z
        self.label = label
        self.data = data
        self.is_taunt = is_taunt
        self.color = color
        self.radius = radius
        self.parent_id = parent_id


class Interactive3DTreeWidget:
    """
    Horizontal Expedition Track & Perception Journey Map.
    Provides a clean, intuitive, side-scrolling timeline of the entire 36,000m run
    across Acts I-IV, with clear, non-overlapping staggered milestone cards,
    Act biome zones, gateway monoliths, and live real-time runner position tracking.
    """

    def __init__(self, rect: pg.Rect, manager: TheEyePerceptionManager):
        self.rect = rect
        self.mgr = manager

        # Camera & Navigation Parameters (2D Expedition Track)
        self.margin_x = 45.0
        self.scroll_x = 0.0          # Camera X offset in world meters
        self.target_scroll_x = 0.0
        self.zoom = (self.rect.width - 90.0) / 36000.0  # Pixels per meter
        self.target_zoom = self.zoom
        self.pan_y = 0.0
        self.target_pan_y = 0.0
        self.track_y = self.rect.height // 2  # Central baseline in viewport

        # 3D Backwards-Compatibility Fields (preserved for tests and smoke runs)
        self.yaw = 0.65
        self.pitch = 0.35
        self.distance = 720.0
        self.pan_x = 0.0
        self.fov = 680.0
        self.auto_rotate = False

        # Interaction tracking
        self.is_panning = False
        self.is_orbiting = False
        self.is_scrubbing = False
        self.drag_start = (0, 0)
        self.drag_start_scroll = 0.0
        self.drag_start_pan_y = 0.0

        # Model Data
        self.nodes_3d: Dict[str, Node3D] = {}
        self.branches_3d: List[Tuple[str, str, Tuple[int, int, int], int]] = []
        self.stars_3d: List[Tuple[float, float, float, float]] = []

        # Card geometry cache: node_id -> pg.Rect (in screen coordinates)
        self.card_rects: Dict[str, pg.Rect] = {}

        # Selection & Filters
        self.selected_node_id: Optional[str] = None
        self.hovered_node_id: Optional[str] = None
        self.type_filter = "ALL"  # "ALL", "TAUNT_ONLY", "DIALOGUE_ONLY"
        self.search_text = ""

        # Fonts
        self.f_label = make_font(11, bold=True)
        self.f_tooltip = make_font(12, bold=True)
        self.f_small = make_font(10)
        self.f_act = make_font(13, bold=True)
        self.f_card_title = make_font(11, bold=True)
        self.f_card_sub = make_font(9)

        # Quick Act Jump Buttons (Embedded directly in viewport header)
        bx = self.rect.x + 12
        by = self.rect.y + 8
        self.btn_act_fit = EyeButton(pg.Rect(bx, by, 84, 24), "Fit 36km", color_theme=(20, 26, 40), text_color=C_GOLD)
        self.btn_act_1   = EyeButton(pg.Rect(bx + 90, by, 84, 24), "Act I", color_theme=(12, 28, 20), text_color=(70, 225, 140))
        self.btn_act_2   = EyeButton(pg.Rect(bx + 180, by, 84, 24), "Act II", color_theme=(10, 24, 34), text_color=(50, 205, 245))
        self.btn_act_3   = EyeButton(pg.Rect(bx + 270, by, 84, 24), "Act III", color_theme=(32, 14, 16), text_color=(255, 100, 75))
        self.btn_act_4   = EyeButton(pg.Rect(bx + 360, by, 84, 24), "Act IV", color_theme=(24, 12, 34), text_color=(205, 110, 255))
        self.act_buttons = [self.btn_act_fit, self.btn_act_1, self.btn_act_2, self.btn_act_3, self.btn_act_4]

        # Scrubber timeline rect
        self.scrubber_rect = pg.Rect(self.rect.x + 10, self.rect.bottom - 24, self.rect.width - 20, 16)

        self._init_starfield()
        self.build_3d_tree()

    def _init_starfield(self) -> None:
        """Create subtle background cosmic ambient dust."""
        self.stars_3d.clear()
        for i in range(120):
            sx = float((i * 307) % 36000)
            sy = float(((i * 73) % 400) - 200)
            br = 0.2 + (i % 5) * 0.15
            self.stars_3d.append((sx, sy, 0.0, br))

    def build_3d_tree(self) -> None:
        """Construct the horizontal journey timeline nodes and speech mappings."""
        self.nodes_3d.clear()
        self.branches_3d.clear()

        story_nodes = self.mgr.get_nodes()
        if not story_nodes:
            return

        # Base Root at 0m
        self.nodes_3d["root"] = Node3D(
            node_id="root",
            node_type="trunk",
            x=0.0,
            y=0.0,
            z=0.0,
            label="Verge Portal [0m]",
            color=(175, 75, 255),
            radius=10.0,
        )

        prev_trunk_id = "root"

        for idx, node in enumerate(story_nodes):
            m_dist = float(node.distance)

            # Central highway spine node
            trunk_id = f"trunk_{node.node_id}"
            self.nodes_3d[trunk_id] = Node3D(
                node_id=trunk_id,
                node_type="trunk",
                x=m_dist,
                y=0.0,
                z=0.0,
                label=f"Spine {int(m_dist)}m",
                color=(160, 130, 60),
                radius=5.0,
                parent_id=prev_trunk_id,
            )
            self.branches_3d.append((prev_trunk_id, trunk_id, (140, 110, 45), 3))
            prev_trunk_id = trunk_id

            # Clean Staggered Vertical Card Offset
            # Alternates cleanly between above and below the central track across 3 distinct vertical tiers
            tier = (idx // 2) % 3
            if idx % 2 == 0:
                card_offset_y = -float(95 + tier * 58)  # Above the highway
            else:
                card_offset_y = float(95 + tier * 58)   # Below the highway

            ev = self.mgr.get_event_for_node(node.node_id)
            ev_cat = ev.category if ev else ("RELIC" if node.entity_type == "RELIC" else "INTERACTION")
            ev_color = EVENT_COLORS.get(ev_cat, NODE_COLORS.get(node.entity_type, C_CYAN))

            # Entity / Event Card Node
            self.nodes_3d[node.node_id] = Node3D(
                node_id=node.node_id,
                node_type="entity",
                x=m_dist,
                y=card_offset_y,
                z=0.0,
                label=f"[{ev_cat}] {node.character_name} [{int(m_dist)}m]",
                data=node,
                color=ev_color,
                radius=12.0,
                parent_id=trunk_id,
            )
            self.branches_3d.append((trunk_id, node.node_id, (ev_color[0] // 2, ev_color[1] // 2, ev_color[2] // 2), 2))

            # Speech & Taunt sub-nodes associated with this entity
            speeches = self.mgr._get_speeches_for_node(node.node_id)
            for s_idx, sp in enumerate(speeches):
                sub_y = card_offset_y + (28.0 if card_offset_y > 0 else -28.0)
                is_taunt = sp.is_taunt
                leaf_color = C_CRIMSON if is_taunt else C_CYAN
                preview = sp.text.replace("\n", " ").strip()
                if len(preview) > 28:
                    preview = preview[:25] + "..."

                self.nodes_3d[sp.speech_id] = Node3D(
                    node_id=sp.speech_id,
                    node_type="speech",
                    x=m_dist,
                    y=sub_y,
                    z=0.0,
                    label=f"[{'TAUNT' if is_taunt else 'DIALOGUE'}] \"{preview}\"",
                    data=sp,
                    is_taunt=is_taunt,
                    color=leaf_color,
                    radius=6.0,
                    parent_id=node.node_id,
                )

        if not self.selected_node_id:
            for nid, n in self.nodes_3d.items():
                if n.node_type == "entity":
                    self.selected_node_id = nid
                    break

    def reset_camera(self) -> None:
        """Reset camera zoom and scroll to fit all 36km in the viewport."""
        self.target_scroll_x = 0.0
        self.target_zoom = (self.rect.width - 90.0) / 36000.0
        self.target_pan_y = 0.0
        self.yaw = 0.65
        self.pitch = 0.35

    def focus_node(self, node_id: str) -> None:
        """Center camera smoothly on the requested milestone node."""
        node = self.nodes_3d.get(node_id)
        if node:
            center_screen_m = (self.rect.width * 0.45) / self.zoom
            self.target_scroll_x = max(0.0, node.x - center_screen_m)
            self.selected_node_id = node_id

    def project_3d_point(self, x: float, y: float, z: float) -> Tuple[Optional[int], Optional[int], float]:
        """Maps 2D world coordinates (meters, offset_y) to screen coordinates."""
        sx = int(self.rect.x + self.margin_x + (x - self.scroll_x) * self.zoom)
        sy = int(self.rect.y + self.track_y + self.pan_y + y)
        return sx, sy, 100.0

    def handle_event(self, event: pg.event.Event) -> Optional[Node3D]:
        """Handles panning, zooming, Act jumping, and clean node selection."""
        m_pos = pg.mouse.get_pos()
        in_viewport = self.rect.collidepoint(m_pos)

        # 1. Quick Act Jump Buttons
        for btn in self.act_buttons:
            if btn.handle_event(event):
                if btn == self.btn_act_fit:
                    self.reset_camera()
                elif btn == self.btn_act_1:
                    self.target_scroll_x = 0.0
                    self.target_zoom = (self.rect.width - 110.0) / 9000.0
                elif btn == self.btn_act_2:
                    self.target_scroll_x = 9000.0
                    self.target_zoom = (self.rect.width - 110.0) / 9000.0
                elif btn == self.btn_act_3:
                    self.target_scroll_x = 18000.0
                    self.target_zoom = (self.rect.width - 110.0) / 9000.0
                elif btn == self.btn_act_4:
                    self.target_scroll_x = 27000.0
                    self.target_zoom = (self.rect.width - 110.0) / 9000.0
                return None

        # 2. Bottom Scrubber Interaction
        if self.scrubber_rect.collidepoint(m_pos) and event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
            self.is_scrubbing = True
            ratio = max(0.0, min(1.0, (m_pos[0] - self.scrubber_rect.x) / float(self.scrubber_rect.width)))
            center_m = ratio * 36000.0
            half_view_m = (self.rect.width * 0.5) / self.zoom
            self.target_scroll_x = max(0.0, min(36000.0, center_m - half_view_m))
            return None

        if event.type == pg.MOUSEBUTTONUP and event.button == 1:
            self.is_scrubbing = False

        if self.is_scrubbing and event.type == pg.MOUSEMOTION:
            ratio = max(0.0, min(1.0, (m_pos[0] - self.scrubber_rect.x) / float(self.scrubber_rect.width)))
            center_m = ratio * 36000.0
            half_view_m = (self.rect.width * 0.5) / self.zoom
            self.target_scroll_x = max(0.0, min(36000.0, center_m - half_view_m))
            return None

        # 3. Mouse Wheel Zooming (Centered on cursor)
        if event.type == pg.MOUSEWHEEL and in_viewport:
            factor = 1.20 if event.y > 0 else 0.82
            min_zoom = (self.rect.width - 90.0) / 36000.0 * 0.8
            max_zoom = 0.35
            old_zoom = self.target_zoom
            new_zoom = max(min_zoom, min(max_zoom, old_zoom * factor))

            # Focus zoom around mouse X
            m_rel_x = m_pos[0] - self.rect.x - self.margin_x
            world_m_at_mouse = self.target_scroll_x + m_rel_x / old_zoom
            self.target_zoom = new_zoom
            self.target_scroll_x = max(-500.0, world_m_at_mouse - m_rel_x / new_zoom)
            return None

        # 4. Mouse Button Down (Card Selection or Panning)
        if event.type == pg.MOUSEBUTTONDOWN and in_viewport:
            if event.button == 1:
                clicked_node = self._pick_node_at_screen_pos(m_pos)
                if clicked_node:
                    self.selected_node_id = clicked_node.node_id
                    return clicked_node
                else:
                    self.is_panning = True
                    self.drag_start = m_pos
                    self.drag_start_scroll = self.target_scroll_x
                    self.drag_start_pan_y = self.target_pan_y
            elif event.button == 3:
                self.is_panning = True
                self.drag_start = m_pos
                self.drag_start_scroll = self.target_scroll_x
                self.drag_start_pan_y = self.target_pan_y

        elif event.type == pg.MOUSEBUTTONUP:
            if event.button in (1, 3):
                self.is_panning = False

        elif event.type == pg.MOUSEMOTION:
            if self.is_panning:
                dx = m_pos[0] - self.drag_start[0]
                dy = m_pos[1] - self.drag_start[1]
                self.target_scroll_x = self.drag_start_scroll - dx / self.zoom
                self.target_pan_y = max(-180.0, min(180.0, self.drag_start_pan_y + dy * 0.7))
            elif in_viewport:
                hov = self._pick_node_at_screen_pos(m_pos)
                self.hovered_node_id = hov.node_id if hov else None

        return None

    def _pick_node_at_screen_pos(self, pos: Tuple[int, int]) -> Optional[Node3D]:
        """Detect which milestone card or node was clicked on screen."""
        # 1. Check card rectangles first
        for nid, rect in self.card_rects.items():
            if rect.collidepoint(pos):
                node = self.nodes_3d.get(nid)
                if node and self._passes_filter(node):
                    return node

        # 2. Check highway spine checkpoints
        for node in self.nodes_3d.values():
            if not self._passes_filter(node):
                continue
            sx, sy, _ = self.project_3d_point(node.x, node.y, node.z)
            if sx is not None and sy is not None:
                if math.hypot(pos[0] - sx, pos[1] - sy) <= 16:
                    return node

        return None

    def _passes_filter(self, node: Node3D) -> bool:
        if node.node_type == "speech":
            if self.type_filter == "TAUNT_ONLY" and not node.is_taunt:
                return False
            if self.type_filter == "DIALOGUE_ONLY" and node.is_taunt:
                return False
            if self.search_text and self.search_text.lower() not in node.label.lower():
                return False
        elif self.search_text:
            return self.search_text.lower() in node.label.lower()
        return True

    def update(self, dt: float) -> None:
        """Smoothly interpolate camera zoom, scroll, and auto-scroll."""
        if self.auto_rotate:
            self.target_scroll_x = (self.target_scroll_x + dt * 1200.0) % 36000.0

        # Smooth damping
        ease = min(1.0, dt * 14.0)
        self.scroll_x += (self.target_scroll_x - self.scroll_x) * ease
        self.zoom += (self.target_zoom - self.zoom) * ease
        self.pan_y += (self.target_pan_y - self.pan_y) * ease

    def draw(self, surface: pg.Surface, live_player_dist: Optional[float] = None, pulse: float = 0.0) -> Optional[Tuple[int, int]]:
        """Renders the comprehensive 2D Horizontal Expedition Track Journey Map."""
        # Background frame
        pg.draw.rect(surface, (10, 13, 22), self.rect, border_radius=8)
        pg.draw.rect(surface, C_BORDER, self.rect, width=1, border_radius=8)

        clip_w, clip_h = self.rect.width, self.rect.height
        clip_surf = pg.Surface((clip_w, clip_h), pg.SRCALPHA)
        clip_surf.fill((8, 10, 16))

        # Clear card rect cache for this frame
        self.card_rects.clear()

        # ── 1. Draw Act Biome Background Sectors ───────────────────────────────
        act_sectors = [
            (0, 9000, "ACT I: THE FOREST VERGE", (10, 24, 18), (60, 200, 120)),
            (9000, 18000, "ACT II: SUNKEN CATACOMBS", (10, 20, 30), (40, 180, 220)),
            (18000, 27000, "ACT III: THRESHOLD OF DISCORD", (28, 12, 14), (255, 90, 60)),
            (27000, 36000, "ACT IV: THE VOID NEXUS", (22, 10, 30), (180, 80, 255)),
        ]

        rail_y = self.track_y + int(self.pan_y)

        for start_m, end_m, act_name, bg_col, accent_col in act_sectors:
            x1 = int(self.margin_x + (start_m - self.scroll_x) * self.zoom)
            x2 = int(self.margin_x + (end_m - self.scroll_x) * self.zoom)
            if x2 < 0 or x1 > clip_w:
                continue

            sec_rect = pg.Rect(max(0, x1), 38, min(clip_w, x2) - max(0, x1), clip_h - 68)
            pg.draw.rect(clip_surf, (*bg_col, 160), sec_rect)

            # Act Top Ribbon
            if x1 < clip_w and x2 > 0:
                txt_act = self.f_act.render(act_name, True, (*accent_col, 200))
                lbl_x = max(16, x1 + 14)
                if lbl_x + txt_act.get_width() < min(clip_w - 10, x2):
                    clip_surf.blit(txt_act, (lbl_x, 44))

        # ── 2. Draw Gateway Laser Pillars ─────────────────────────────────────
        gateways = [
            (9000, "GATEWAY I -> II [9km]", (60, 220, 160)),
            (18000, "GATEWAY II -> III [18km]", (50, 190, 255)),
            (27000, "GATEWAY III -> IV [27km]", (255, 110, 80)),
            (36000, "EXTRACTION PORTAL [36km]", (210, 100, 255)),
        ]
        for gm, glabel, gcolor in gateways:
            gx = int(self.margin_x + (gm - self.scroll_x) * self.zoom)
            if -40 <= gx <= clip_w + 40:
                # Vertical laser line
                pg.draw.line(clip_surf, (*gcolor, 120), (gx, 42), (gx, clip_h - 32), 2)
                # Gateway Pillar Badge
                txt_g = self.f_small.render(glabel, True, gcolor)
                bg_g = pg.Rect(gx - txt_g.get_width() // 2 - 6, clip_h - 48, txt_g.get_width() + 12, 16)
                pg.draw.rect(clip_surf, (14, 18, 28, 220), bg_g, border_radius=4)
                pg.draw.rect(clip_surf, gcolor, bg_g, width=1, border_radius=4)
                clip_surf.blit(txt_g, (bg_g.x + 6, bg_g.y + 1))

        # ── 3. Draw The Runner Highway Rail & Distance Ticks ──────────────────
        track_start_x = int(self.margin_x + (0.0 - self.scroll_x) * self.zoom)
        track_end_x = int(self.margin_x + (36000.0 - self.scroll_x) * self.zoom)

        # Base rail girder
        pg.draw.line(clip_surf, (40, 48, 65), (track_start_x, rail_y), (track_end_x, rail_y), 8)
        # Glowing inner rail
        pg.draw.line(clip_surf, (220, 185, 75), (track_start_x, rail_y), (track_end_x, rail_y), 3)

        # Distance ruler ticks
        tick_step = 1000 if self.zoom > 0.025 else 3000
        first_tick = int(self.scroll_x // tick_step) * tick_step
        last_tick = int((self.scroll_x + clip_w / self.zoom) // tick_step + 1) * tick_step

        for tick_m in range(max(0, first_tick), min(36001, last_tick + 1), tick_step):
            tx = int(self.margin_x + (tick_m - self.scroll_x) * self.zoom)
            if 0 <= tx <= clip_w:
                pg.draw.line(clip_surf, (140, 155, 180), (tx, rail_y - 6), (tx, rail_y + 6), 1)
                t_lbl = f"{tick_m//1000}k" if tick_m >= 1000 else f"{tick_m}m"
                txt_t = self.f_small.render(t_lbl, True, (120, 135, 160))
                clip_surf.blit(txt_t, (tx - txt_t.get_width() // 2, rail_y + 9))

        # ── 4. Draw Staggered Milestone Event Cards ───────────────────────────
        story_nodes = self.mgr.get_nodes()
        card_w, card_h = 164, 48

        for idx, node in enumerate(story_nodes):
            m_dist = float(node.distance)
            tier = (idx // 2) % 3
            card_offset_y = -float(95 + tier * 58) if (idx % 2 == 0) else float(95 + tier * 58)

            cx = int(self.margin_x + (m_dist - self.scroll_x) * self.zoom)
            cy = rail_y + int(card_offset_y)

            card_rect_local = pg.Rect(cx - card_w // 2, cy - card_h // 2, card_w, card_h)
            card_rect_screen = pg.Rect(self.rect.x + card_rect_local.x, self.rect.y + card_rect_local.y, card_w, card_h)
            self.card_rects[node.node_id] = card_rect_screen

            # Cull off-screen cards
            if cx + card_w < -50 or cx - card_w > clip_w + 50:
                continue

            ev = self.mgr.get_event_for_node(node.node_id)
            ev_cat = ev.category if ev else ("RELIC" if node.entity_type == "RELIC" else "INTERACTION")
            ev_col = EVENT_COLORS.get(ev_cat, NODE_COLORS.get(node.entity_type, C_CYAN))

            is_selected = (self.selected_node_id == node.node_id or
                           any(self.selected_node_id == sp.speech_id for sp in self.mgr._get_speeches_for_node(node.node_id)))
            is_hovered = (self.hovered_node_id == node.node_id)

            # Laser connection stem from highway to card
            stem_col = (*ev_col, 180) if is_selected else (*ev_col, 90)
            pg.draw.line(clip_surf, stem_col, (cx, rail_y), (cx, cy), 2 if is_selected else 1)

            # Checkpoint disc on rail
            disc_rad = 7 if is_selected else 5
            pg.draw.circle(clip_surf, ev_col, (cx, rail_y), disc_rad)
            pg.draw.circle(clip_surf, C_WHITE, (cx, rail_y), max(2, disc_rad - 3))

            # Card Background
            bg_col = (24, 30, 44) if is_hovered else (16, 20, 30)
            if is_selected:
                bg_col = (28, 38, 54)
            pg.draw.rect(clip_surf, bg_col, card_rect_local, border_radius=6)

            # Border
            border_col = C_GOLD if is_selected else (ev_col if is_hovered else C_BORDER)
            border_w = 2 if is_selected else 1
            pg.draw.rect(clip_surf, border_col, card_rect_local, width=border_w, border_radius=6)

            # Selected Pulsing Bracket Frame
            if is_selected:
                bracket_len = 10
                bx, by, bw, bh = card_rect_local.x, card_rect_local.y, card_rect_local.width, card_rect_local.height
                # Top-left
                pg.draw.line(clip_surf, C_CYAN, (bx - 2, by - 2), (bx + bracket_len, by - 2), 2)
                pg.draw.line(clip_surf, C_CYAN, (bx - 2, by - 2), (bx - 2, by + bracket_len), 2)
                # Bottom-right
                pg.draw.line(clip_surf, C_CYAN, (bx + bw + 2, by + bh + 2), (bx + bw - bracket_len, by + bh + 2), 2)
                pg.draw.line(clip_surf, C_CYAN, (bx + bw + 2, by + bh + 2), (bx + bw + 2, by + bh - bracket_len), 2)

            # Left Icon Block with Custom Geometric Vector Art
            icon_rect = pg.Rect(card_rect_local.x + 5, card_rect_local.y + 5, 38, 38)
            pg.draw.rect(clip_surf, (*ev_col, 50), icon_rect, border_radius=4)
            pg.draw.rect(clip_surf, ev_col, icon_rect, width=1, border_radius=4)

            icx, icy = icon_rect.centerx, icon_rect.centery - 4
            cat_abbr = {
                "INTERACTION": "ACT",
                "RELIC": "RLC",
                "SOUL_QUOTA": "QTA",
                "LEVEL_COMPLETE": "EXT",
                "AMBIENT_LORE": "LOR",
                "ITEM_DISCOVERY": "ITM",
            }.get(ev_cat, "POI")

            draw_event_category_icon(clip_surf, ev_cat, ev_col, icx, icy, size=16)

            txt_cat_code = self.f_card_sub.render(cat_abbr, True, C_WHITE)
            clip_surf.blit(txt_cat_code, (icx - txt_cat_code.get_width() // 2, icon_rect.bottom - 11))

            # Text Details
            tx = card_rect_local.x + 48
            # Category & Distance Line
            d_str = f"{int(m_dist)}m" if m_dist < 1000 else f"{m_dist/1000:.1f}km"
            cat_str = f"[{ev_cat}] · {d_str}"
            txt_cat = self.f_card_sub.render(cat_str, True, ev_col)
            clip_surf.blit(txt_cat, (tx, card_rect_local.y + 6))

            # Title Line (truncated if needed)
            title_str = node.character_name
            if len(title_str) > 16:
                title_str = title_str[:15] + "…"
            txt_tit = self.f_card_title.render(title_str, True, C_WHITE if not is_selected else C_GOLD)
            clip_surf.blit(txt_tit, (tx, card_rect_local.y + 20))

            # Speech count indicator chip
            speeches = self.mgr._get_speeches_for_node(node.node_id)
            if speeches:
                sp_txt = f"{len(speeches)} line{'s' if len(speeches) > 1 else ''}"
                txt_sp = self.f_card_sub.render(sp_txt, True, C_MUTED)
                clip_surf.blit(txt_sp, (tx, card_rect_local.y + 34))

        # ── 5. Draw Live Runner Marker (If Game Connected) ────────────────────
        runner_screen_pos: Optional[Tuple[int, int]] = None
        if live_player_dist is not None:
            r_dist = float(live_player_dist)
            rx = int(self.margin_x + (r_dist - self.scroll_x) * self.zoom)
            ry = rail_y
            runner_screen_pos = (self.rect.x + rx, self.rect.y + ry)

            if -30 <= rx <= clip_w + 30:
                # Vertical laser beacon
                pg.draw.line(clip_surf, (0, 255, 180, 160), (rx, 38), (rx, clip_h - 30), 2)

                # Pulsing beacon circle
                pulse_r = int(12 + math.sin(pulse * 6.0) * 4)
                pg.draw.circle(clip_surf, (0, 255, 180, 70), (rx, ry), pulse_r)
                pg.draw.circle(clip_surf, (0, 255, 200), (rx, ry), 8)
                pg.draw.circle(clip_surf, C_WHITE, (rx, ry), 4)

                # Floating Runner Badge
                d_txt = f"{int(r_dist)}m" if r_dist < 1000 else f"{r_dist/1000:.1f}km"
                b_str = f"▶ RUNNER @ {d_txt}"
                txt_b = self.f_label.render(b_str, True, (0, 255, 180))
                b_rect = pg.Rect(rx - txt_b.get_width() // 2 - 8, ry - 32, txt_b.get_width() + 16, 20)
                pg.draw.rect(clip_surf, (10, 20, 28, 230), b_rect, border_radius=4)
                pg.draw.rect(clip_surf, (0, 255, 180), b_rect, width=1, border_radius=4)
                clip_surf.blit(txt_b, (b_rect.x + 8, b_rect.y + 3))

        # ── 6. Draw Bottom Scrubber Minimap ───────────────────────────────────
        sb_local = pg.Rect(10, clip_h - 22, clip_w - 20, 14)
        pg.draw.rect(clip_surf, (14, 18, 26), sb_local, border_radius=4)
        pg.draw.rect(clip_surf, C_BORDER, sb_local, width=1, border_radius=4)

        # 4 Act colored segments on scrubber
        for s_idx, (start_m, end_m, _, _, col) in enumerate(act_sectors):
            x_a = sb_local.x + int((start_m / 36000.0) * sb_local.width)
            x_b = sb_local.x + int((end_m / 36000.0) * sb_local.width)
            seg_r = pg.Rect(x_a, sb_local.y, x_b - x_a, sb_local.height)
            pg.draw.rect(clip_surf, (*col, 120), seg_r)

        # Milestone dots on scrubber
        for n in story_nodes:
            dx = sb_local.x + int((n.distance / 36000.0) * sb_local.width)
            pg.draw.circle(clip_surf, C_WHITE, (dx, sb_local.centery), 2)

        # Viewport lens rectangle on scrubber
        view_start_m = max(0.0, self.scroll_x)
        view_end_m = min(36000.0, self.scroll_x + clip_w / self.zoom)
        vx1 = sb_local.x + int((view_start_m / 36000.0) * sb_local.width)
        vx2 = sb_local.x + int((view_end_m / 36000.0) * sb_local.width)
        v_rect = pg.Rect(vx1, sb_local.y - 1, max(8, vx2 - vx1), sb_local.height + 2)
        pg.draw.rect(clip_surf, (80, 220, 255, 80), v_rect, border_radius=3)
        pg.draw.rect(clip_surf, C_CYAN, v_rect, width=1, border_radius=3)

        # Blit main canvas to surface
        surface.blit(clip_surf, (self.rect.x, self.rect.y))

        # ── 7. Draw Quick Act Jump Buttons on Top ─────────────────────────────
        for btn in self.act_buttons:
            btn.draw(surface, self.f_small)

        # Return live runner screen position
        return runner_screen_pos



# ══════════════════════════════════════════════════════════════════════════════
#  Unity-Style 2D TreeView Widget (Alternative View)
# ══════════════════════════════════════════════════════════════════════════════
class UnityTreeViewWidget:
    """Unity-Style 2D Resource TreeView for structured hierarchical browsing."""

    ROW_HEIGHT = 28
    INDENT_STEP = 18

    def __init__(self, rect: pg.Rect, manager: TheEyePerceptionManager):
        self.rect = rect
        self.mgr = manager
        self.view_mode = "timeline"
        self.search_text = ""
        self.type_filter = "ALL"

        self.timeline_root = self.mgr.build_timeline_tree()
        self.entity_root = self.mgr.build_entity_tree()

        self.selected_item_id: Optional[str] = None
        self.selected_item: Optional[TreeItem] = None

        self.scroll_y = 0.0
        self.target_scroll_y = 0.0
        self.max_scroll = 0.0
        self.is_dragging_scrollbar = False

        self.f_row = make_font(12)
        self.f_bold = make_font(12, bold=True)
        self.f_badge = make_font(10, bold=True)
        self.f_arrow = make_font(11, bold=True)

    def get_current_root(self) -> TreeItem:
        return self.timeline_root if self.view_mode == "timeline" else self.entity_root

    def rebuild_trees(self) -> None:
        self.timeline_root = self.mgr.build_timeline_tree()
        self.entity_root = self.mgr.build_entity_tree()

    def set_view_mode(self, mode: str) -> None:
        if mode in ("timeline", "entity"):
            self.view_mode = mode
            self.scroll_y = 0.0
            self.target_scroll_y = 0.0

    def expand_all(self) -> None:
        self.mgr.expand_all(self.get_current_root())

    def collapse_all(self) -> None:
        self.mgr.collapse_all(self.get_current_root())

    def handle_event(self, event: pg.event.Event) -> Optional[TreeItem]:
        if event.type == pg.MOUSEWHEEL:
            m_pos = pg.mouse.get_pos()
            if self.rect.collidepoint(m_pos):
                self.target_scroll_y = max(0.0, min(self.max_scroll, self.target_scroll_y - event.y * 36.0))
                return None

        if event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
            m_pos = event.pos
            if not self.rect.collidepoint(m_pos):
                return None

            sb_x = self.rect.right - 14
            if m_pos[0] >= sb_x:
                self.is_dragging_scrollbar = True
                return None

            rel_y = m_pos[1] - self.rect.y + self.scroll_y
            row_idx = int(rel_y // self.ROW_HEIGHT)

            flat_rows = self.mgr.flatten_tree(
                self.get_current_root(),
                filter_text=self.search_text,
                type_filter=self.type_filter,
            )

            if 0 <= row_idx < len(flat_rows):
                item, depth = flat_rows[row_idx]
                row_x = self.rect.x + depth * self.INDENT_STEP

                foldout_hit = (row_x <= m_pos[0] <= row_x + 18)
                if foldout_hit and item.has_children:
                    self.mgr.toggle_expand(item)
                    return item

                self.selected_item_id = item.item_id
                self.selected_item = item
                return item

        elif event.type == pg.MOUSEBUTTONUP and event.button == 1:
            self.is_dragging_scrollbar = False

        elif event.type == pg.MOUSEMOTION and self.is_dragging_scrollbar:
            track_h = self.rect.height - 20
            rel_m_y = max(0, min(track_h, event.pos[1] - self.rect.y - 10))
            if track_h > 0:
                ratio = rel_m_y / track_h
                self.target_scroll_y = ratio * self.max_scroll

        return None

    def update(self, dt: float) -> None:
        self.scroll_y += (self.target_scroll_y - self.scroll_y) * min(1.0, dt * 14.0)

    def draw(self, surface: pg.Surface) -> None:
        pg.draw.rect(surface, C_PANEL_DARK, self.rect, border_radius=8)
        pg.draw.rect(surface, C_BORDER, self.rect, width=1, border_radius=8)

        flat_rows = self.mgr.flatten_tree(
            self.get_current_root(),
            filter_text=self.search_text,
            type_filter=self.type_filter,
        )

        total_h = len(flat_rows) * self.ROW_HEIGHT
        self.max_scroll = max(0.0, total_h - self.rect.height)
        self.scroll_y = max(0.0, min(self.max_scroll, self.scroll_y))

        clip_surf = pg.Surface((self.rect.width - 16, self.rect.height), pg.SRCALPHA)
        clip_surf.fill((12, 15, 24))

        m_pos = pg.mouse.get_pos()
        rel_mx = m_pos[0] - self.rect.x
        rel_my = m_pos[1] - self.rect.y

        start_idx = max(0, int(self.scroll_y // self.ROW_HEIGHT))
        end_idx = min(len(flat_rows), int((self.scroll_y + self.rect.height) // self.ROW_HEIGHT) + 2)

        for i in range(start_idx, end_idx):
            item, depth = flat_rows[i]
            ry = int(i * self.ROW_HEIGHT - self.scroll_y)
            row_rect = pg.Rect(0, ry, self.rect.width - 16, self.ROW_HEIGHT)

            is_sel = (item.item_id == self.selected_item_id)
            is_hov = (0 <= rel_mx < self.rect.width - 16 and ry <= rel_my < ry + self.ROW_HEIGHT)

            if is_sel:
                pg.draw.rect(clip_surf, C_SEL_BG, row_rect)
                pg.draw.line(clip_surf, C_SEL_LINE, (0, ry), (0, ry + self.ROW_HEIGHT), 3)
            elif is_hov:
                pg.draw.rect(clip_surf, (22, 28, 44), row_rect)

            for d in range(depth):
                gx = 12 + d * self.INDENT_STEP
                pg.draw.line(clip_surf, (30, 38, 58), (gx, ry), (gx, ry + self.ROW_HEIGHT), 1)

            nx = 8 + depth * self.INDENT_STEP

            if item.has_children:
                arrow_txt = "▼" if item.expanded else "▶"
                arrow_surf = self.f_arrow.render(arrow_txt, True, C_GOLD if is_sel else C_MUTED)
                clip_surf.blit(arrow_surf, (nx, ry + 7))
            nx += 14

            # Procedural icon
            if item.node_type == "act":
                pg.draw.rect(clip_surf, (200, 160, 60), (nx, ry + 8, 12, 11), border_radius=2)
                pg.draw.rect(clip_surf, (240, 190, 80), (nx, ry + 6, 6, 4), border_top_left_radius=2, border_top_right_radius=2)
            elif item.node_type == "milestone":
                pts = [(nx + 6, ry + 7), (nx + 11, ry + 13), (nx + 6, ry + 19), (nx + 1, ry + 13)]
                pg.draw.polygon(clip_surf, C_GOLD, pts)
            elif item.node_type == "entity":
                pg.draw.circle(clip_surf, C_CYAN, (nx + 6, ry + 9), 3)
                pg.draw.rect(clip_surf, C_CYAN, (nx + 2, ry + 13, 8, 6), border_radius=2)
            elif item.node_type == "speech":
                if item.is_taunt:
                    pts = [(nx + 8, ry + 6), (nx + 3, ry + 13), (nx + 7, ry + 13), (nx + 4, ry + 20), (nx + 11, ry + 11), (nx + 7, ry + 11)]
                    pg.draw.polygon(clip_surf, C_CRIMSON, pts)
                else:
                    pg.draw.rect(clip_surf, C_CYAN, (nx + 1, ry + 7, 10, 8), border_radius=2)
                    pg.draw.polygon(clip_surf, C_CYAN, [(nx + 3, ry + 15), (nx + 7, ry + 15), (nx + 3, ry + 18)])

            nx += 18

            label_col = C_WHITE if is_sel else C_TEXT
            font_use = self.f_bold if item.has_children else self.f_row

            max_label_w = row_rect.width - nx - 90
            display_label = item.label
            if font_use.size(display_label)[0] > max_label_w:
                while display_label and font_use.size(display_label + "...")[0] > max_label_w:
                    display_label = display_label[:-1]
                display_label += "..."

            lbl_surf = font_use.render(display_label, True, label_col)
            clip_surf.blit(lbl_surf, (nx, ry + 6))

            if item.badge:
                badge_bg = (
                    item.badge_color[0] // 4,
                    item.badge_color[1] // 4,
                    item.badge_color[2] // 4,
                )
                badge_txt_surf = self.f_badge.render(item.badge, True, item.badge_color)
                bw = badge_txt_surf.get_width() + 10
                bh = 16
                bx = row_rect.right - bw - 8
                by = ry + 6

                pg.draw.rect(clip_surf, badge_bg, (bx, by, bw, bh), border_radius=4)
                pg.draw.rect(clip_surf, item.badge_color, (bx, by, bw, bh), width=1, border_radius=4)
                clip_surf.blit(badge_txt_surf, (bx + 5, by + 1))

        surface.blit(clip_surf, (self.rect.x, self.rect.y))


# ══════════════════════════════════════════════════════════════════════════════
#  Main "The Eye" Plugin Application
# ══════════════════════════════════════════════════════════════════════════════
class TheEyeApp:
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
            pg.display.set_caption("THE EYE  ·  3D Interactive Story Tree & Dialogue Controller")

        self.clock = pg.time.Clock()
        self.running = True

        # Fonts
        self.f_title  = make_font(19, bold=True)
        self.f_head   = make_font(14, bold=True)
        self.f_body   = make_font(13)
        self.f_small  = make_font(11)
        self.f_badge  = make_font(10, bold=True)

        # Perception Manager
        self.mgr = TheEyePerceptionManager.get_instance()

        # View Mode: "3D_TREE" (default) or "2D_TREEVIEW"
        self.active_view = "3D_TREE"

        # 3D Interactive Tree Widget
        self.tree_3d = Interactive3DTreeWidget(pg.Rect(20, 110, 780, 720), self.mgr)

        # 2D Unity TreeView Widget (Alternative View)
        self.tree_2d = UnityTreeViewWidget(pg.Rect(20, 150, 780, 680), self.mgr)

        # Occult Eye Emblem
        self.eye_emblem = AnimatedAllSeeingEye(35, 28, radius=18)

        # Search Bar
        self.search_bar = SearchInputField(pg.Rect(20, 70, 310, 32))

        # Inspector Selection
        self.active_speech: Optional[SpeechItem] = None
        self.active_node: Optional[StoryNode] = None
        self.active_event: Optional[GameEventItem] = None

        # Live SideNotification instance for in-editor pop-up preview & test
        self.side_notification = SideNotification(self.sw, self.sh)

        # Text Editor
        self.text_editor = MultiLineTextInput(pg.Rect(825, 356, 585, 106), "Event Description / Inscription Text (Click to Edit)")

        # Simulation Typewriter
        self.sim_dialogue_char = 0
        self.sim_dialogue_timer = 0.0

        # Status Strip
        self.status_msg = "The Eye Ready · Drag to Pan Expedition Track · Click any event card to inspect."
        self.status_timer = 0.0

        # Save Confirmation Toast Banner
        self.save_toast_msg = ""
        self.save_toast_timer = 0.0

        # Live Game Observer Bridge
        self.live_state_path = os.path.join("scratch", "the_eye_live_state.json")
        self.is_game_connected = False
        self.live_state: Dict[str, Any] = {}
        self.live_poll_timer = 0.0
        self.live_pulse = 0.0
        self.live_runner_screen_pos: Optional[Tuple[int, int]] = None
        self._poll_live_game_state()

        # Build UI Controls
        self._init_controls()
        self._sync_inspector_from_3d_selection()

    def _poll_live_game_state(self) -> None:
        """Polls scratch/the_eye_live_state.json emitted by running game."""
        if not os.path.exists(self.live_state_path):
            self.is_game_connected = False
            return
        try:
            with open(self.live_state_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            ts = data.get("timestamp", 0)
            if time.time() - ts < 5.0:
                self.is_game_connected = True
                self.live_state = data
            else:
                self.is_game_connected = False
        except Exception:
            pass

    def _init_controls(self) -> None:
        """Create buttons for view switching, 3D camera, filters, and inspector."""
        # Top Bar Action Buttons
        self.btn_save = EyeButton(
            pg.Rect(1140, 12, 140, 36), "Save Changes", color_theme=(20, 75, 45), text_color=C_WHITE
        )
        self.btn_revert = EyeButton(
            pg.Rect(1290, 12, 130, 36), "Reset Node", color_theme=(60, 30, 40), text_color=C_WHITE
        )

        # View Mode Switchers
        self.btn_mode_3d = EyeButton(
            pg.Rect(340, 70, 150, 32), "Expedition Track", color_theme=C_PANEL_DARK, text_color=C_GOLD
        )
        self.btn_mode_3d.is_active = True

        self.btn_mode_2d = EyeButton(
            pg.Rect(498, 70, 140, 32), "2D List TreeView", color_theme=C_PANEL_DARK, text_color=C_MUTED
        )

        # Track Navigation Controls
        self.btn_reset_cam = EyeButton(
            pg.Rect(646, 70, 75, 32), "Fit 36km", color_theme=C_PANEL_DARK, text_color=C_CYAN
        )
        self.btn_orbit_toggle = EyeButton(
            pg.Rect(729, 70, 71, 32), "Auto-Scroll", color_theme=C_PANEL_DARK, text_color=C_MUTED
        )

        # Quick Filter Chips (Placed in 2D or 3D header)
        self.btn_filter_all = EyeButton(
            pg.Rect(825, 70, 55, 32), "All", color_theme=C_PANEL_DARK, text_color=C_WHITE
        )
        self.btn_filter_all.is_active = True

        self.btn_filter_taunt = EyeButton(
            pg.Rect(888, 70, 110, 32), "Taunts Only", color_theme=C_PANEL_DARK, text_color=C_CRIMSON
        )
        self.btn_filter_dialogue = EyeButton(
            pg.Rect(1006, 70, 120, 32), "Dialogue Only", color_theme=C_PANEL_DARK, text_color=C_CYAN
        )

        # Event Category Selector Chips - Clean 1-row grid of 6 buttons for legitimate game events
        self.event_cat_buttons: List[Tuple[str, EyeButton]] = []
        ev_cats = [
            ("INTERACTION", "ACT: Interact"),
            ("RELIC", "RLC: Relic"),
            ("SOUL_QUOTA", "QTA: Quota"),
            ("LEVEL_COMPLETE", "EXT: Extract"),
            ("AMBIENT_LORE", "LOR: Lore"),
            ("ITEM_DISCOVERY", "ITM: Item"),
        ]
        ev_btn_w = 93
        ev_spacing = 5
        for idx, (cid, clbl) in enumerate(ev_cats):
            bx = 825 + idx * (ev_btn_w + ev_spacing)
            btn = EyeButton(pg.Rect(bx, 238, ev_btn_w, 24), clbl, color_theme=C_PANEL_DARK, text_color=C_MUTED)
            self.event_cat_buttons.append((cid, btn))

        # Explicit "Is Taunt" Toggle Segmented Buttons (maintained for backward compatibility)
        self.btn_type_dialogue = EyeButton(
            pg.Rect(825, 266, 285, 22), "Dialogue (Narrative Overlay)", color_theme=C_PANEL_DARK, text_color=C_MUTED
        )
        self.btn_type_taunt = EyeButton(
            pg.Rect(1120, 266, 290, 22), "Taunt (In-Combat Bark)", color_theme=C_PANEL_DARK, text_color=C_MUTED
        )

        # Category Selector Chips - Clean 2-row grid of 4 buttons each
        self.cat_buttons: List[Tuple[str, EyeButton]] = []
        col_w = 140
        spacing = 8

        row1_cats = [
            ("encounter", "Encounter"),
            ("combat_taunt", "Combat Taunt"),
            ("pre_fight", "Pre-Fight"),
            ("death_line", "Defeat Line"),
        ]
        for idx, (cat_id, cat_lbl) in enumerate(row1_cats):
            bx = 825 + idx * (col_w + spacing)
            btn = EyeButton(pg.Rect(bx, 292, col_w, 20), cat_lbl, color_theme=C_PANEL_DARK, text_color=C_MUTED)
            self.cat_buttons.append((cat_id, btn))

        row2_cats = [
            ("corruption_low", "Corrupt (Low)"),
            ("corruption_mid", "Corrupt (Mid)"),
            ("corruption_high", "Corrupt (High)"),
            ("relic", "Relic Branch"),
        ]
        for idx, (cat_id, cat_lbl) in enumerate(row2_cats):
            bx = 825 + idx * (col_w + spacing)
            btn = EyeButton(pg.Rect(bx, 314, col_w, 20), cat_lbl, color_theme=C_PANEL_DARK, text_color=C_MUTED)
            self.cat_buttons.append((cat_id, btn))

        # Inspector Action Buttons
        self.btn_test_popup = EyeButton(
            pg.Rect(825, 468, 145, 28), "▶ Test Pop-up", color_theme=(20, 60, 90), text_color=C_CYAN
        )
        self.btn_hold_minus = EyeButton(
            pg.Rect(978, 468, 42, 28), "-1s", color_theme=C_PANEL_DARK, text_color=C_WHITE
        )
        self.btn_hold_plus = EyeButton(
            pg.Rect(1028, 468, 42, 28), "+1s", color_theme=C_PANEL_DARK, text_color=C_WHITE
        )
        self.btn_add_speech = EyeButton(
            pg.Rect(1078, 468, 160, 28), "+ Add Speech", color_theme=(25, 60, 40), text_color=C_GREEN
        )
        self.btn_del_speech = EyeButton(
            pg.Rect(1246, 468, 164, 28), "- Delete Line", color_theme=(60, 30, 40), text_color=C_CRIMSON
        )

    def _sync_inspector_from_3d_selection(self) -> None:
        """Synchronize Inspector with currently selected 3D node."""
        node_3d = self.tree_3d.nodes_3d.get(self.tree_3d.selected_node_id or "")
        if not node_3d:
            return

        if node_3d.node_type == "speech" and isinstance(node_3d.data, SpeechItem):
            self.active_speech = node_3d.data
            self.active_node = self.mgr.get_node_by_id(self.active_speech.parent_node_id)
        elif node_3d.node_type == "entity" and isinstance(node_3d.data, StoryNode):
            self.active_node = node_3d.data
            speeches = self.mgr._get_speeches_for_node(self.active_node.node_id)
            self.active_speech = speeches[0] if speeches else None
        else:
            self.active_speech = None
            self.active_node = None

        # Resolve active GameEventItem
        if self.active_node:
            self.active_event = self.mgr.get_event_for_node(self.active_node.node_id)
        elif self.active_speech:
            self.active_event = self.mgr.get_event_by_id(self.active_speech.speech_id)
        else:
            self.active_event = None

        if self.active_speech:
            self.text_editor.set_text(self.active_speech.text)
            self._update_taunt_toggle_ui(self.active_speech.is_taunt)
            self._update_cat_buttons_ui(self.active_speech.category)
            self.sim_dialogue_char = len(self.text_editor.text)
        elif self.active_event:
            self.text_editor.set_text(self.active_event.text)
            self.sim_dialogue_char = len(self.text_editor.text)
        else:
            self.text_editor.set_text("")
            self.sim_dialogue_char = 0

        if self.active_event:
            self._update_event_cat_buttons_ui(self.active_event.category)

        self.sim_dialogue_timer = 0.0

    def _update_taunt_toggle_ui(self, is_taunt: bool) -> None:
        self.btn_type_dialogue.is_active = not is_taunt
        self.btn_type_dialogue.text_color = C_CYAN if not is_taunt else C_MUTED
        self.btn_type_taunt.is_active = is_taunt
        self.btn_type_taunt.text_color = C_CRIMSON if is_taunt else C_MUTED

    def _update_cat_buttons_ui(self, category: str) -> None:
        for cid, btn in self.cat_buttons:
            btn.is_active = (cid == category)
            btn.text_color = C_GOLD if (cid == category) else C_MUTED

    def _update_event_cat_buttons_ui(self, category: str) -> None:
        cat_u = category.upper()
        for cid, btn in self.event_cat_buttons:
            btn.is_active = (cid == cat_u)
            btn.text_color = EVENT_COLORS.get(cid, C_GOLD) if (cid == cat_u) else C_MUTED

    def _commit_editor_to_speech(self) -> None:
        new_text = self.text_editor.text
        if self.active_speech:
            self.mgr.update_speech(self.active_speech.speech_id, text=new_text)

            # Update 3D label
            node_3d = self.tree_3d.nodes_3d.get(self.active_speech.speech_id)
            if node_3d:
                preview = new_text.replace("\n", " ").strip()
                if len(preview) > 28:
                    preview = preview[:25] + "..."
                node_3d.label = f"[{'TAUNT' if self.active_speech.is_taunt else 'DIALOGUE'}] \"{preview}\""

        if self.active_event:
            self.mgr.update_event(
                self.active_event.event_id,
                title=self.active_event.title,
                text=new_text,
                category=self.active_event.category,
                hold_duration=self.active_event.hold_duration,
            )

        if self.active_node:
            self.active_node.conversations["primary"] = new_text

    def toggle_active_speech_taunt(self, is_taunt: bool) -> None:
        """Toggle taunt/dialogue state for the active speech."""
        if not self.active_speech:
            return
        self.active_speech.is_taunt = is_taunt
        self.mgr.update_speech(self.active_speech.speech_id, is_taunt=is_taunt)
        self._update_taunt_toggle_ui(is_taunt)

        # Update 3D node model
        node_3d = self.tree_3d.nodes_3d.get(self.active_speech.speech_id)
        if node_3d:
            node_3d.is_taunt = is_taunt
            node_3d.color = C_CRIMSON if is_taunt else C_CYAN
            preview = self.active_speech.text.replace("\n", " ").strip()
            if len(preview) > 28:
                preview = preview[:25] + "..."
            node_3d.label = f"[{'TAUNT' if is_taunt else 'DIALOGUE'}] \"{preview}\""

        self.status_msg = f"Updated 3D node type to {'[TAUNT]' if is_taunt else '[DIALOGUE]'}."
        self.status_timer = 3.0

    def save_changes(self) -> None:
        """Persist all speech, taunt, and event modifications to disk with backups."""
        self._commit_editor_to_speech()
        success, msg = self.mgr.save_perception()
        if success:
            self.btn_save.trigger_success("✓ SAVED!", duration=2.5)
            self.save_toast_msg = "✓ PERCEPTION & DIALOGUE SAVED TO DISK!"
            self.save_toast_timer = 3.5
            self.status_msg = f"✓ SUCCESS: {msg}"
        else:
            self.save_toast_msg = f"[!] SAVE FAILED: {msg}"
            self.save_toast_timer = 4.0
            self.status_msg = f"[!] ERROR: {msg}"
        self.status_timer = 4.5

    def revert_selected_node(self) -> None:
        """Reset the active entity's conversations and event to default factory values."""
        if self.active_node:
            self.mgr.revert_node_dialogue(self.active_node.node_id)
            if self.active_event:
                self.active_event.title = self.active_event.original_title
                self.active_event.text = self.active_event.original_text
                self.active_event.category = self.active_event.original_category
            self.tree_3d.build_3d_tree()
            self.tree_2d.rebuild_trees()
            self._sync_inspector_from_3d_selection()
            self.status_msg = f"Reverted '{self.active_node.character_name}' conversations to factory settings."
            self.status_timer = 3.5

    # ── Event Handling ────────────────────────────────────────────────────────
    def handle_event(self, event: pg.event.Event) -> None:
        if event.type == pg.QUIT:
            self.running = False
            return

        if event.type == pg.KEYDOWN:
            if event.key == pg.K_ESCAPE and not self.search_bar.active and not self.text_editor.active:
                self.running = False
                return

        # Top Bar Action Buttons
        if self.btn_save.handle_event(event):
            self.save_changes()
            return
        if self.btn_revert.handle_event(event):
            self.revert_selected_node()
            return

        # View Mode Switchers
        if self.btn_mode_3d.handle_event(event):
            self.active_view = "3D_TREE"
            self.btn_mode_3d.is_active = True
            self.btn_mode_3d.text_color = C_GOLD
            self.btn_mode_2d.is_active = False
            self.btn_mode_2d.text_color = C_MUTED
            return
        if self.btn_mode_2d.handle_event(event):
            self.active_view = "2D_TREEVIEW"
            self.btn_mode_3d.is_active = False
            self.btn_mode_3d.text_color = C_MUTED
            self.btn_mode_2d.is_active = True
            self.btn_mode_2d.text_color = C_GOLD
            return

        # 3D Camera Controls
        if self.btn_reset_cam.handle_event(event):
            self.tree_3d.reset_camera()
            return
        if self.btn_orbit_toggle.handle_event(event):
            self.tree_3d.auto_rotate = not self.tree_3d.auto_rotate
            self.btn_orbit_toggle.is_active = self.tree_3d.auto_rotate
            self.btn_orbit_toggle.text = "Orbit On" if self.tree_3d.auto_rotate else "Orbit Off"
            self.btn_orbit_toggle.text_color = C_GOLD if self.tree_3d.auto_rotate else C_MUTED
            return

        # Quick Filter Chips
        if self.btn_filter_all.handle_event(event):
            self.btn_filter_all.is_active = True
            self.btn_filter_taunt.is_active = False
            self.btn_filter_dialogue.is_active = False
            self.tree_3d.type_filter = "ALL"
            self.tree_2d.type_filter = "ALL"
            return
        if self.btn_filter_taunt.handle_event(event):
            self.btn_filter_all.is_active = False
            self.btn_filter_taunt.is_active = True
            self.btn_filter_dialogue.is_active = False
            self.tree_3d.type_filter = "TAUNT_ONLY"
            self.tree_2d.type_filter = "TAUNT_ONLY"
            return
        if self.btn_filter_dialogue.handle_event(event):
            self.btn_filter_all.is_active = False
            self.btn_filter_taunt.is_active = False
            self.btn_filter_dialogue.is_active = True
            self.tree_3d.type_filter = "DIALOGUE_ONLY"
            self.tree_2d.type_filter = "DIALOGUE_ONLY"
            return

        # Search Bar
        if self.search_bar.handle_event(event):
            self.tree_3d.search_text = self.search_bar.text
            self.tree_2d.search_text = self.search_bar.text
            return

        # "Is Taunt" Toggle Buttons
        if self.btn_type_dialogue.handle_event(event):
            self.toggle_active_speech_taunt(False)
            return
        if self.btn_type_taunt.handle_event(event):
            self.toggle_active_speech_taunt(True)
            return

        # Event Category Chips
        for cid, btn in self.event_cat_buttons:
            if btn.handle_event(event):
                if self.active_event:
                    self.active_event.category = cid
                    self._update_event_cat_buttons_ui(cid)
                    self.tree_3d.build_3d_tree()
                    self.status_msg = f"Changed event category to {cid}."
                    self.status_timer = 2.5
                return

        # Category Chips
        for cid, btn in self.cat_buttons:
            if btn.handle_event(event):
                if self.active_speech:
                    self.active_speech.category = cid
                    self.mgr.update_speech(self.active_speech.speech_id, category=cid)
                    self._update_cat_buttons_ui(cid)
                return

        # Live Pop-up Test Button
        if self.btn_test_popup.handle_event(event):
            title = self.active_event.title if self.active_event else (self.active_node.title if self.active_node else "Perception Event")
            text = self.text_editor.text or "Game perception event reached!"
            icon = self.active_event.icon_path if self.active_event else "assets/graphics/UI/PNG/Exclamation_Yellow.png"
            hold = self.active_event.hold_duration if self.active_event else 8.5
            self.side_notification.show(text, title, icon=icon, hold=hold)
            self.status_msg = f"Triggered live SideNotification: '{title}' ({hold}s hold)"
            self.status_timer = 3.5
            return

        # Hold Duration Adjustments
        if self.btn_hold_minus.handle_event(event):
            if self.active_event:
                self.active_event.hold_duration = max(1.0, round(self.active_event.hold_duration - 1.0, 1))
            elif self.active_speech:
                self.active_speech.hold_duration = max(1.0, round(self.active_speech.hold_duration - 1.0, 1))
            return

        if self.btn_hold_plus.handle_event(event):
            if self.active_event:
                self.active_event.hold_duration = round(self.active_event.hold_duration + 1.0, 1)
            elif self.active_speech:
                self.active_speech.hold_duration = round(self.active_speech.hold_duration + 1.0, 1)
            return

        # Add / Delete Speech Buttons
        if self.btn_add_speech.handle_event(event):
            if self.active_node:
                new_item = self.mgr.add_speech_item(
                    self.active_node.node_id,
                    "New custom spoken line...",
                    category="combat_taunt",
                    is_taunt=True,
                )
                self.tree_3d.build_3d_tree()
                self.tree_2d.rebuild_trees()
                if new_item:
                    self.tree_3d.selected_node_id = new_item.speech_id
                    self._sync_inspector_from_3d_selection()
            return

        if self.btn_del_speech.handle_event(event):
            if self.active_speech:
                self.mgr.delete_speech_item(self.active_speech.speech_id)
                self.tree_3d.build_3d_tree()
                self.tree_2d.rebuild_trees()
                self._sync_inspector_from_3d_selection()
            return

        # Text Editor Events
        if self.text_editor.handle_event(event):
            self._commit_editor_to_speech()
            return

        # Active View Events
        if self.active_view == "3D_TREE":
            picked = self.tree_3d.handle_event(event)
            if picked:
                self._commit_editor_to_speech()
                self._sync_inspector_from_3d_selection()
        else:
            clicked_item = self.tree_2d.handle_event(event)
            if clicked_item:
                self._commit_editor_to_speech()
                if clicked_item.node_type == "speech" and isinstance(clicked_item.data, SpeechItem):
                    self.tree_3d.selected_node_id = clicked_item.data.speech_id
                    self._sync_inspector_from_3d_selection()
                elif clicked_item.node_type == "entity" and isinstance(clicked_item.data, StoryNode):
                    self.tree_3d.selected_node_id = clicked_item.data.node_id
                    self._sync_inspector_from_3d_selection()

    # ── Update & Rendering ────────────────────────────────────────────────────
    def update(self, dt: float) -> None:
        if self.status_timer > 0:
            self.status_timer -= dt

        if self.save_toast_timer > 0:
            self.save_toast_timer = max(0.0, self.save_toast_timer - dt)

        # Update button animation timers
        self.btn_save.update(dt)
        self.btn_revert.update(dt)
        self.btn_mode_3d.update(dt)
        self.btn_mode_2d.update(dt)
        self.btn_reset_cam.update(dt)
        self.btn_orbit_toggle.update(dt)
        self.btn_filter_all.update(dt)
        self.btn_filter_taunt.update(dt)
        self.btn_filter_dialogue.update(dt)
        self.btn_type_dialogue.update(dt)
        self.btn_type_taunt.update(dt)
        self.btn_add_speech.update(dt)
        self.btn_del_speech.update(dt)
        self.btn_test_popup.update(dt)
        self.btn_hold_minus.update(dt)
        self.btn_hold_plus.update(dt)
        for _, btn in self.event_cat_buttons:
            btn.update(dt)
        for _, btn in self.cat_buttons:
            btn.update(dt)

        self.side_notification.update(dt)

        # Pulse for beacon & live orbit tracking
        self.live_pulse = (self.live_pulse + dt * 3.5) % (2.0 * math.pi)

        # Poll running game bridge every 0.2s
        self.live_poll_timer += dt
        if self.live_poll_timer >= 0.2:
            self.live_poll_timer = 0.0
            self._poll_live_game_state()

        m_pos = pg.mouse.get_pos()
        # All-Seeing Eye pupil gazes toward live runner if on screen, else follows mouse cursor
        gaze = self.live_runner_screen_pos if (self.is_game_connected and self.live_runner_screen_pos) else None
        self.eye_emblem.update(dt, m_pos, gaze_target=gaze)

        self.search_bar.update(dt)
        self.text_editor.update(dt)

        if self.active_view == "3D_TREE":
            self.tree_3d.update(dt)
        else:
            self.tree_2d.update(dt)

        self.sim_dialogue_timer += dt
        if self.sim_dialogue_timer >= 0.03:
            self.sim_dialogue_timer = 0.0
            if self.sim_dialogue_char < len(self.text_editor.text):
                self.sim_dialogue_char += 1

    def draw(self) -> None:
        self.screen.fill(C_BG)

        # 1. Header Bar
        self._draw_header()

        # 2. Left Tree Section (3D Tree or 2D TreeView)
        self._draw_tree_section()

        # 3. Right Inspector & Live Dual Simulator
        self._draw_inspector_section()

        # 4. Bottom Status Bar
        self._draw_status_bar()

        # 5. Top-Center Save Confirmation Toast Banner
        self._draw_save_toast_banner()

        # 6. Live In-Editor SideNotification Floating Pop-up
        self.side_notification.draw(self.screen)

        if not self.headless:
            pg.display.flip()

    def _draw_save_toast_banner(self) -> None:
        if self.save_toast_timer <= 0 or not self.save_toast_msg:
            return

        toast_w = 480
        toast_h = 38
        toast_x = (self.sw - toast_w) // 2
        toast_y = 10
        toast_rect = pg.Rect(toast_x, toast_y, toast_w, toast_h)

        toast_surf = pg.Surface((toast_w, toast_h), pg.SRCALPHA)
        toast_surf.fill((10, 35, 20, 240))
        pg.draw.rect(toast_surf, (0, 255, 160), toast_surf.get_rect(), width=2, border_radius=8)

        is_error = "FAILED" in self.save_toast_msg or "ERROR" in self.save_toast_msg
        text_col = (255, 80, 80) if is_error else (0, 255, 180)

        txt_surf = self.f_badge.render(self.save_toast_msg, True, text_col)
        toast_surf.blit(txt_surf, txt_surf.get_rect(center=(toast_w // 2, toast_h // 2)))

        self.screen.blit(toast_surf, toast_rect)

    def _draw_header(self) -> None:
        hdr_rect = pg.Rect(0, 0, self.sw, 56)
        pg.draw.rect(self.screen, C_HEADER, hdr_rect)
        pg.draw.line(self.screen, C_BORDER, (0, 56), (self.sw, 56), 1)

        self.eye_emblem.draw(self.screen)

        txt_title = self.f_title.render("THE EYE", True, C_GOLD)
        self.screen.blit(txt_title, (70, 16))

        txt_sub = self.f_body.render("3D Interactive Story Tree & Dialogue Controller", True, C_MUTED)
        self.screen.blit(txt_sub, (180, 20))

        # Live Game Observer Status Badge in Header
        beacon_cx = 570
        if self.is_game_connected:
            p_val = 0.5 + 0.5 * math.sin(self.live_pulse)
            b_rad = int(5 + 2 * p_val)
            pg.draw.circle(self.screen, (0, 255, 120, int(80 + 100 * p_val)), (beacon_cx, 28), b_rad + 4)
            pg.draw.circle(self.screen, (0, 255, 120), (beacon_cx, 28), b_rad)

            d_curr = self.live_state.get("world_distance", 0)
            d_end = self.live_state.get("level_end_distance", 36000)
            hp = int(self.live_state.get("player_health", 100))
            corr = int(self.live_state.get("corruption", 0))
            act_txt = self.live_state.get("active_act", "Act I")
            boss_name = self.live_state.get("active_boss")

            live_line1 = f"LIVE GAME LINKED  ·  {act_txt}"
            txt_l1 = self.f_badge.render(live_line1, True, (0, 255, 150))
            self.screen.blit(txt_l1, (beacon_cx + 14, 12))

            if boss_name:
                live_line2 = f"BOSS: {boss_name}  ·  Dist: {d_curr}m / {d_end}m  ·  HP: {hp}%"
                col_l2 = C_GOLD
            else:
                live_line2 = f"Dist: {d_curr}m / {d_end}m  ·  HP: {hp}%  ·  Corruption: {corr}%"
                col_l2 = C_CYAN
            txt_l2 = self.f_small.render(live_line2, True, col_l2)
            self.screen.blit(txt_l2, (beacon_cx + 14, 28))
        else:
            pg.draw.circle(self.screen, (100, 115, 140), (beacon_cx, 28), 5)
            txt_off1 = self.f_badge.render("OBSERVER STANDALONE MODE", True, C_MUTED)
            self.screen.blit(txt_off1, (beacon_cx + 14, 12))
            txt_off2 = self.f_small.render("Launch Pixel-Runner (main.py) for Live Real-Time Orbit Tracking", True, (90, 105, 130))
            self.screen.blit(txt_off2, (beacon_cx + 14, 28))

        self.btn_save.draw(self.screen, self.f_body)
        self.btn_revert.draw(self.screen, self.f_body)

    def _draw_tree_section(self) -> None:
        # Search & Mode buttons
        self.search_bar.draw(self.screen, self.f_small)
        self.btn_mode_3d.draw(self.screen, self.f_small)
        self.btn_mode_2d.draw(self.screen, self.f_small)

        if self.active_view == "3D_TREE":
            self.btn_reset_cam.draw(self.screen, self.f_small)
            self.btn_orbit_toggle.draw(self.screen, self.f_small)
            live_dist = self.live_state.get("world_distance") if self.is_game_connected else None
            self.live_runner_screen_pos = self.tree_3d.draw(self.screen, live_player_dist=live_dist, pulse=self.live_pulse)
        else:
            self.tree_2d.draw(self.screen)

    def _draw_inspector_section(self) -> None:
        panel_rect = pg.Rect(815, 68, 605, 762)
        pg.draw.rect(self.screen, C_PANEL, panel_rect, border_radius=10)
        pg.draw.rect(self.screen, C_BORDER, panel_rect, width=1, border_radius=10)

        # Filters at top of inspector panel
        self.btn_filter_all.draw(self.screen, self.f_small)
        self.btn_filter_taunt.draw(self.screen, self.f_small)
        self.btn_filter_dialogue.draw(self.screen, self.f_small)

        # 1. Dossier Header Box
        self._draw_dossier_box(pg.Rect(825, 110, 585, 96))

        # 2. Game Perception Event Classification Header
        lbl_type = self.f_head.render("GAME PERCEPTION EVENT & SIDENOTIFICATION", True, C_GOLD)
        self.screen.blit(lbl_type, (825, 214))

        # Event category selector chips (6 buttons for legitimate events)
        for _, btn in self.event_cat_buttons:
            btn.draw(self.screen, self.f_badge)

        # Legacy dialogue / taunt switcher (maintained for backward compatibility)
        self.btn_type_dialogue.draw(self.screen, self.f_small)
        self.btn_type_taunt.draw(self.screen, self.f_small)

        # Category chips grid
        for _, btn in self.cat_buttons:
            btn.draw(self.screen, self.f_badge)

        # Dedicated Trigger Scheduling & Status Strip
        bar_rect = pg.Rect(825, 337, 585, 20)
        pg.draw.rect(self.screen, (12, 16, 24), bar_rect, border_radius=4)
        pg.draw.rect(self.screen, (35, 45, 65), bar_rect, width=1, border_radius=4)

        if self.active_event:
            cat_txt = f"EVENT: [{self.active_event.category}]"
            trig_txt = f"TRIGGER: {self.active_event.trigger_type.upper()}"
            hold_txt = f"HOLD: {self.active_event.hold_duration}s"
            cue_txt = f"CUE: {self.active_event.audio_cue or 'default'}"
            status_txt = "STATUS: SYNCHRONIZED"
            cat_col = EVENT_COLORS.get(self.active_event.category, C_CYAN)
            self.screen.blit(self.f_badge.render(cat_txt, True, cat_col), (832, 341))
            self.screen.blit(self.f_badge.render(trig_txt, True, C_CYAN), (935, 341))
            self.screen.blit(self.f_badge.render(hold_txt, True, C_GOLD), (1095, 341))
            self.screen.blit(self.f_badge.render(cue_txt, True, C_PURPLE), (1185, 341))
            self.screen.blit(self.f_badge.render(status_txt, True, C_GREEN), (1275, 341))
        elif self.active_speech:
            trig_txt = f"TRIGGER: {self.active_speech.trigger_type.upper()}"
            hold_txt = f"HOLD: {self.active_speech.hold_duration}s"
            cue_txt = f"CUE: {self.active_speech.audio_cue or 'default'}"
            status_txt = "STATUS: SYNCHRONIZED"
            self.screen.blit(self.f_badge.render(trig_txt, True, C_CYAN), (832, 341))
            self.screen.blit(self.f_badge.render(hold_txt, True, C_GOLD), (1010, 341))
            self.screen.blit(self.f_badge.render(cue_txt, True, C_PURPLE), (1130, 341))
            self.screen.blit(self.f_badge.render(status_txt, True, C_GREEN), (1275, 341))
        else:
            self.screen.blit(self.f_badge.render("NO ACTIVE EVENT SELECTED", True, C_MUTED), (832, 341))

        # 3. Main Text Inscription Box
        self.text_editor.draw(self.screen, self.f_small, self.f_body)

        # 4. Action Buttons
        self.btn_test_popup.draw(self.screen, self.f_badge)
        self.btn_hold_minus.draw(self.screen, self.f_badge)
        self.btn_hold_plus.draw(self.screen, self.f_badge)
        self.btn_add_speech.draw(self.screen, self.f_badge)
        self.btn_del_speech.draw(self.screen, self.f_badge)

        # 5. Live SideNotification In-Game Simulation
        self._draw_simulation_preview(pg.Rect(825, 506, 585, 314))

    def _draw_dossier_box(self, rect: pg.Rect) -> None:
        pg.draw.rect(self.screen, C_PANEL_DARK, rect, border_radius=8)
        pg.draw.rect(self.screen, C_BORDER_HI, rect, width=1, border_radius=8)

        node = self.active_node
        if not node:
            txt_empty = self.f_body.render("Click any 3D tree node to inspect its properties and dialogues.", True, C_MUTED)
            self.screen.blit(txt_empty, txt_empty.get_rect(center=rect.center))
            return

        av_rect = pg.Rect(rect.x + 10, rect.y + 8, 80, 80)
        pg.draw.rect(self.screen, (10, 12, 18), av_rect, border_radius=6)
        pg.draw.rect(self.screen, NODE_COLORS.get(node.entity_type, C_GOLD), av_rect, width=1, border_radius=6)
        self._draw_avatar_image(av_rect, node)

        ix = av_rect.right + 14
        txt_name = self.f_head.render(node.character_name, True, C_GOLD)
        self.screen.blit(txt_name, (ix, rect.y + 8))

        col = NODE_COLORS.get(node.entity_type, C_CYAN)
        d_str = f"{node.distance}m" if node.distance < 1000 else f"{node.distance/1000:.1f}km"
        meta_txt = f"[{node.entity_type}]  ·  Dist: {d_str}  ·  {node.act}"
        self.screen.blit(self.f_small.render(meta_txt, True, col), (ix, rect.y + 28))

        words = node.summary.split()
        summary_line = ""
        sy = rect.y + 46
        for w in words:
            if self.f_small.size(f"{summary_line} {w}".strip())[0] <= 430:
                summary_line = f"{summary_line} {w}".strip()
            else:
                self.screen.blit(self.f_small.render(summary_line, True, C_MUTED), (ix, sy))
                sy += 15
                summary_line = w
        if summary_line:
            self.screen.blit(self.f_small.render(summary_line, True, C_MUTED), (ix, sy))

    def _draw_avatar_image(self, rect: pg.Rect, node: StoryNode) -> None:
        loaded = False
        if node.sprite_path and os.path.exists(node.sprite_path):
            try:
                target_path = node.sprite_path
                if os.path.isdir(target_path):
                    for root, _, files in os.walk(target_path):
                        pngs = [f for f in files if f.endswith(".png")]
                        if pngs:
                            target_path = os.path.join(root, pngs[0])
                            break
                if os.path.isfile(target_path):
                    raw = pg.image.load(target_path).convert_alpha()
                    scaled = pg.transform.smoothscale(raw, (rect.width - 6, rect.height - 6))
                    self.screen.blit(scaled, (rect.x + 3, rect.y + 3))
                    loaded = True
            except Exception:
                pass

        if not loaded:
            cx, cy = rect.centerx, rect.centery
            col = NODE_COLORS.get(node.entity_type, C_GOLD)
            pg.draw.circle(self.screen, col, (cx, cy), 24, width=2)
            pts = [(cx, cy - 16), (cx + 16, cy), (cx, cy + 16), (cx - 16, cy)]
            pg.draw.polygon(self.screen, (col[0] // 2, col[1] // 2, col[2] // 2), pts)
            initial = node.character_name[0] if node.character_name else "E"
            txt_init = self.f_head.render(initial, True, C_WHITE)
            self.screen.blit(txt_init, txt_init.get_rect(center=(cx, cy)))

    def _draw_simulation_preview(self, rect: pg.Rect) -> None:
        """
        Renders Live SideNotification In-Game Preview:
        Displays the legitimate game event's pop-up card with framed icon,
        glowing category notch, title, word-wrapped body, and simulated hold timer.
        """
        ev = self.active_event
        ev_cat = ev.category if ev else "INTERACTION"
        ev_title = ev.title if ev else (self.active_node.title if self.active_node else "Perception Event")
        ev_color = EVENT_COLORS.get(ev_cat, C_CYAN)
        ev_hold = ev.hold_duration if ev else (self.active_speech.hold_duration if self.active_speech else 8.5)

        pg.draw.rect(self.screen, (14, 16, 26), rect, border_radius=8)
        pg.draw.rect(self.screen, ev_color, rect, width=1, border_radius=8)

        sim_title = f"LIVE SIDENOTIFICATION PREVIEW  ·  [{ev_cat}]"
        self.screen.blit(self.f_badge.render(sim_title, True, ev_color), (rect.x + 14, rect.y + 10))

        # Real SideNotification pop-up card preview box
        card_rect = pg.Rect(rect.x + 20, rect.y + 36, rect.width - 40, rect.height - 68)
        pg.draw.rect(self.screen, (10, 16, 28), card_rect, border_radius=8)
        pg.draw.rect(self.screen, C_BORDER_HI, card_rect, width=1, border_radius=8)

        # Left accent notch
        notch_rect = pg.Rect(card_rect.x, card_rect.y, 6, card_rect.height)
        pg.draw.rect(self.screen, ev_color, notch_rect, border_top_left_radius=8, border_bottom_left_radius=8)

        # Icon Frame
        icon_box = pg.Rect(card_rect.x + 16, card_rect.y + 14, 46, 46)
        pg.draw.rect(self.screen, (18, 26, 44), icon_box, border_radius=8)
        pg.draw.rect(self.screen, ev_color, icon_box, width=1, border_radius=8)
        icon_loaded = False
        if ev and ev.icon_path and os.path.exists(ev.icon_path):
            try:
                raw_icon = pg.image.load(ev.icon_path).convert_alpha()
                scaled_icon = pg.transform.smoothscale(raw_icon, (34, 34))
                self.screen.blit(scaled_icon, (icon_box.x + 6, icon_box.y + 6))
                icon_loaded = True
            except Exception:
                pass
        if not icon_loaded:
            draw_event_category_icon(self.screen, ev_cat, ev_color, icon_box.centerx, icon_box.centery, size=24)

        # Title & Meta
        tx = icon_box.right + 14
        txt_title_surf = self.f_head.render(ev_title[:32], True, C_GOLD)
        self.screen.blit(txt_title_surf, (tx, card_rect.y + 14))

        meta_info = f"Hold Duration: {ev_hold:.1f}s  ·  Audio: {ev.audio_cue if ev else 'reveal'}"
        self.screen.blit(self.f_badge.render(meta_info, True, C_MUTED), (tx, card_rect.y + 34))

        # Body Text
        body_words = (self.text_editor.text or "").split()
        lines = []
        curr_line = ""
        for w in body_words:
            test = f"{curr_line} {w}".strip() if curr_line else w
            if self.f_body.size(test)[0] <= card_rect.width - 32:
                curr_line = test
            else:
                if curr_line:
                    lines.append(curr_line)
                curr_line = w
        if curr_line:
            lines.append(curr_line)

        qy = card_rect.y + 70
        for line in lines[:6]:
            self.screen.blit(self.f_body.render(line, True, C_TEXT), (card_rect.x + 16, qy))
            qy += 22

        # Hold Duration simulated bar
        bar_rect = pg.Rect(card_rect.x + 14, card_rect.bottom - 16, card_rect.width - 28, 4)
        pg.draw.rect(self.screen, (25, 35, 55), bar_rect, border_radius=2)
        progress_w = int(bar_rect.width * 0.85)
        pg.draw.rect(self.screen, ev_color, (bar_rect.x, bar_rect.y, progress_w, 4), border_radius=2)

        # Real-Time In-Game Broadcast Ticker if game is connected
        if self.is_game_connected and self.live_state.get("last_spoken_taunt"):
            lst = self.live_state["last_spoken_taunt"]
            spk = lst.get("speaker", "Game")
            txt = lst.get("text", "")
            is_t = lst.get("is_taunt", False)
            if len(txt) > 38:
                txt = txt[:35] + "..."
            ticker_col = C_CRIMSON if is_t else (0, 220, 255)
            ticker_label = f"[LIVE] {spk}: \"{txt}\""
            self.screen.blit(self.f_small.render(ticker_label, True, ticker_col), (rect.x + 20, rect.bottom - 22))

    def _draw_status_bar(self) -> None:
        status_col = C_GREEN if "successfully" in self.status_msg or "ready" in self.status_msg.lower() else C_TEXT
        txt_status = self.f_small.render(self.status_msg, True, status_col)
        self.screen.blit(txt_status, (20, 848))

        txt_info = self.f_small.render("Expedition Track: Drag = Pan · Wheel = Zoom · Click Event Card = Inspect · Top Chips = Act Jump", True, C_CYAN)
        self.screen.blit(txt_info, (self.sw - txt_info.get_width() - 20, 848))


# ── Entry Point ───────────────────────────────────────────────────────────────
def main() -> None:
    """Launch The Eye plugin application."""
    import argparse
    parser = argparse.ArgumentParser(description="The Eye — 3D Interactive Story Tree & Dialogue Controller")
    parser.add_argument("--smoke", action="store_true", help="Run in headless smoke test mode and exit cleanly")
    parser.add_argument("--screenshot", type=str, default="", help="Save screenshot to target path")
    args = parser.parse_args()

    app = TheEyeApp(headless=args.smoke or bool(args.screenshot))

    if args.screenshot:
        app.update(0.016)
        app.draw()
        os.makedirs(os.path.dirname(os.path.abspath(args.screenshot)), exist_ok=True)
        pg.image.save(app.screen, args.screenshot)
        print(f"[TheEye] Screenshot saved to {args.screenshot}")
        pg.quit()
        sys.exit(0)

    if args.smoke:
        print("[TheEye] 3D Story Tree smoke test initializing...")
        app.update(0.016)
        app.draw()

        # Orbit camera test
        app.tree_3d.yaw += 0.5
        app.tree_3d.pitch += 0.2
        app.update(0.016)
        app.draw()

        # Test toggle taunt
        if app.active_speech:
            app.toggle_active_speech_taunt(not app.active_speech.is_taunt)
            app.update(0.016)
            app.draw()

        # Switch to 2D TreeView
        app.active_view = "2D_TREEVIEW"
        app.update(0.016)
        app.draw()

        print("[TheEye] 3D Story Tree smoke test passed successfully.")
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
