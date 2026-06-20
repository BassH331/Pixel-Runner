#!/usr/bin/env python3
"""
player_editor.py
Interactive configuration editor, animation visualizer, rollback manager, and hitbox tuner for the Player character.
"""

import os
import sys
import json
import shutil
import pygame as pg
from typing import Any, Optional, Dict, List
from datetime import datetime

# Add path mapping to allow importing from src package
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Initialize Pygame
pg.init()
pg.font.init()

SCREEN_W, SCREEN_H = 1280, 720
screen = pg.display.set_mode((SCREEN_W, SCREEN_H))
pg.display.set_caption("Player Character: Animation Configurator & Hitbox Tuner")

# Load Fonts
try:
    title_font = pg.font.Font("assets/graphics/Darinia/Darinia.ttf", 24)
    ui_font = pg.font.Font("assets/graphics/Darinia/Darinia.ttf", 16)
    value_font = pg.font.Font("assets/graphics/Darinia/Darinia.ttf", 14)
    help_font = pg.font.SysFont("Consolas", 14)
except Exception:
    title_font = pg.font.SysFont("Arial", 22, bold=True)
    ui_font = pg.font.SysFont("Arial", 15, bold=True)
    value_font = pg.font.SysFont("Arial", 13)
    help_font = pg.font.SysFont("monospace", 12)

# Theme Colors (Dark Slate & Neon accents)
BG_COLOR = (20, 20, 28)
PANEL_BG = (28, 28, 38)
PREVIEW_BG = (14, 14, 20)
TEXT_COLOR = (240, 240, 245)
ACCENT_GREEN = (0, 230, 118)
ACCENT_CYAN = (0, 229, 255)
ACCENT_PURPLE = (170, 0, 255)
ACCENT_BLUE = (0, 145, 234)
TEXT_MUTED = (140, 140, 160)
BORDER_COLOR = (48, 48, 64)

# Default configuration dictionary matching player.py _STATE_CONFIGS
DEFAULT_PLAYER_CONFIGS = {
    "DEATH": {
        "animation_speed": 0.15,
        "loops": False,
        "interruptible": False,
        "grants_invincibility": True,
        "locks_movement": True,
        "locks_input": True,
        "next_state": None
    },
    "DEFEND": {
        "animation_speed": 0.24,
        "loops": False,
        "interruptible": False,
        "grants_invincibility": True,
        "locks_movement": True,
        "locks_input": False,
        "next_state": "IDLE"
    },
    "HURT": {
        "animation_speed": 0.20,
        "loops": False,
        "interruptible": False,
        "grants_invincibility": True,
        "locks_movement": True,
        "locks_input": True,
        "next_state": "IDLE"
    },
    "ATTACK_THRUST": {
        "animation_speed": 0.24,
        "loops": False,
        "interruptible": False,
        "grants_invincibility": False,
        "locks_movement": True,
        "locks_input": False,
        "next_state": "IDLE"
    },
    "ATTACK_SMASH": {
        "animation_speed": 0.24,
        "loops": False,
        "interruptible": False,
        "grants_invincibility": False,
        "locks_movement": True,
        "locks_input": False,
        "next_state": "IDLE"
    },
    "ATTACK_POWER": {
        "animation_speed": 0.24,
        "loops": False,
        "interruptible": False,
        "grants_invincibility": False,
        "locks_movement": True,
        "locks_input": False,
        "next_state": "IDLE"
    },
    "JUMP_UP": {
        "animation_speed": 0.27,
        "loops": True,
        "interruptible": True,
        "grants_invincibility": False,
        "locks_movement": False,
        "locks_input": False,
        "next_state": None
    },
    "JUMP_DOWN": {
        "animation_speed": 0.27,
        "loops": True,
        "interruptible": True,
        "grants_invincibility": False,
        "locks_movement": False,
        "locks_input": False,
        "next_state": None
    },
    "RUN": {
        "animation_speed": 0.27,
        "loops": True,
        "interruptible": True,
        "grants_invincibility": False,
        "locks_movement": False,
        "locks_input": False,
        "next_state": None
    },
    "IDLE": {
        "animation_speed": 0.27,
        "loops": True,
        "interruptible": True,
        "grants_invincibility": False,
        "locks_movement": False,
        "locks_input": False,
        "next_state": None
    },
    "SPECIAL_ATTACK": {
        "animation_speed": 0.20,
        "loops": False,
        "interruptible": False,
        "grants_invincibility": True,
        "locks_movement": True,
        "locks_input": True,
        "next_state": "IDLE"
    },
    "TRANSFORM": {
        "animation_speed": 0.18,
        "loops": False,
        "interruptible": False,
        "grants_invincibility": True,
        "locks_movement": True,
        "locks_input": True,
        "next_state": "IDLE"
    },
    "ROLL": {
        "animation_speed": 0.25,
        "loops": False,
        "interruptible": False,
        "grants_invincibility": True,
        "locks_movement": True,
        "locks_input": True,
        "next_state": "IDLE"
    },
    "DASH": {
        "animation_speed": 0.25,
        "loops": False,
        "interruptible": False,
        "grants_invincibility": False,
        "locks_movement": True,
        "locks_input": True,
        "next_state": "IDLE"
    }
}

# Default attack configurations matching player.py
DEFAULT_ATTACK_CONFIGS = {
    "THRUST_ATTACK_CONFIG": {
        "hit_frames": [2, 3, 4, 5, 6, 7],
        "base_damage": 15.0,
        "knockback_force": 8.0,
        "knockback_angle": 30.0,
        "hit_stop_frames": 3,
        "can_hit_multiple": True,
        "max_hits_per_target": 1,
        "frame_damage_modifiers": {"2": 0.3, "3": 0.5, "4": 0.8, "5": 1.0, "6": 0.6, "7": 0.4},
        "hitbox_data": {
            "2": {"offset_x": 108, "offset_y": 45, "width": 399, "height": 135},
            "3": {"offset_x": 114, "offset_y": 30, "width": 396, "height": 162},
            "4": {"offset_x": 129, "offset_y": 36, "width": 378, "height": 150},
            "5": {"offset_x": 93, "offset_y": 30, "width": 426, "height": 162},
            "6": {"offset_x": 69, "offset_y": 12, "width": 447, "height": 198},
            "7": {"offset_x": 57, "offset_y": -6, "width": 432, "height": 234},
        },
        "startup_frames": [0, 1],
        "recovery_frames": [8]
    },
    "SMASH_ATTACK_CONFIG": {
        "hit_frames": [2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14],
        "base_damage": 25.0,
        "knockback_force": 15.0,
        "knockback_angle": 45.0,
        "hit_stop_frames": 11,
        "can_hit_multiple": True,
        "max_hits_per_target": 3,
        "frame_damage_modifiers": {"2": 0.2, "7": 1.0, "13": 0.5},
        "hitbox_data": {
            "2": {"offset_x": 108, "offset_y": 45, "width": 399, "height": 135},
            "3": {"offset_x": 114, "offset_y": 30, "width": 396, "height": 162},
            "4": {"offset_x": 117, "offset_y": 36, "width": 405, "height": 150},
            "5": {"offset_x": 120, "offset_y": 24, "width": 372, "height": 177},
            "6": {"offset_x": 138, "offset_y": 6, "width": 336, "height": 213},
            "7": {"offset_x": 102, "offset_y": 0, "width": 432, "height": 222},
            "8": {"offset_x": 102, "offset_y": 0, "width": 438, "height": 222},
            "9": {"offset_x": 114, "offset_y": 3, "width": 423, "height": 216},
            "10": {"offset_x": 123, "offset_y": 3, "width": 342, "height": 216},
            "11": {"offset_x": 120, "offset_y": 3, "width": 333, "height": 219},
            "12": {"offset_x": 117, "offset_y": 6, "width": 354, "height": 213},
            "13": {"offset_x": 90, "offset_y": 9, "width": 417, "height": 204},
            "14": {"offset_x": 69, "offset_y": 12, "width": 450, "height": 201},
        },
        "startup_frames": [0, 1],
        "recovery_frames": [15, 16]
    },
    "POWER_ATTACK_CONFIG": {
        "hit_frames": [6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22],
        "base_damage": 25.0,
        "knockback_force": 15.0,
        "knockback_angle": 45.0,
        "hit_stop_frames": 19,
        "can_hit_multiple": True,
        "max_hits_per_target": 2,
        "frame_damage_modifiers": {"6": 0.5, "11": 0.8, "16": 1.2, "20": 1.5},
        "hitbox_data": {
            "6": {"offset_x": 138, "offset_y": 6, "width": 336, "height": 213},
            "7": {"offset_x": 102, "offset_y": 0, "width": 432, "height": 222},
            "8": {"offset_x": 102, "offset_y": 0, "width": 438, "height": 222},
            "9": {"offset_x": 114, "offset_y": 3, "width": 423, "height": 216},
            "10": {"offset_x": 123, "offset_y": 3, "width": 342, "height": 216},
            "11": {"offset_x": 99, "offset_y": -3, "width": 375, "height": 231},
            "12": {"offset_x": 108, "offset_y": 3, "width": 372, "height": 210},
            "13": {"offset_x": 93, "offset_y": -3, "width": 408, "height": 231},
            "14": {"offset_x": 111, "offset_y": 0, "width": 366, "height": 219},
            "15": {"offset_x": 102, "offset_y": -24, "width": 381, "height": 270},
            "16": {"offset_x": 153, "offset_y": -18, "width": 486, "height": 258},
            "17": {"offset_x": 114, "offset_y": -36, "width": 405, "height": 294},
            "18": {"offset_x": 138, "offset_y": -24, "width": 393, "height": 270},
            "19": {"offset_x": 153, "offset_y": -27, "width": 543, "height": 279},
            "20": {"offset_x": 135, "offset_y": -30, "width": 582, "height": 282},
            "21": {"offset_x": 132, "offset_y": -33, "width": 582, "height": 288},
            "22": {"offset_x": 150, "offset_y": -27, "width": 555, "height": 279},
        },
        "startup_frames": [0, 1, 2, 3, 4, 5],
        "recovery_frames": []
    },
    "SPECIAL_ATTACK_CONFIG": {
        "hit_frames": [14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33],
        "base_damage": 35.0,
        "knockback_force": 15.0,
        "knockback_angle": 45.0,
        "hit_stop_frames": 15,
        "can_hit_multiple": True,
        "max_hits_per_target": 3,
        "frame_damage_modifiers": {},
        "hitbox_data": {
            "14": {"offset_x": 18, "offset_y": 99, "width": 87, "height": 24},
            "15": {"offset_x": 18, "offset_y": 78, "width": 147, "height": 66},
            "16": {"offset_x": 21, "offset_y": 24, "width": 69, "height": 174},
            "17": {"offset_x": 21, "offset_y": -3, "width": 120, "height": 231},
            "18": {"offset_x": 21, "offset_y": -3, "width": 120, "height": 231},
            "19": {"offset_x": 30, "offset_y": -12, "width": 204, "height": 249},
            "20": {"offset_x": 27, "offset_y": -60, "width": 264, "height": 189},
            "21": {"offset_x": 18, "offset_y": -51, "width": 237, "height": 195},
            "22": {"offset_x": 51, "offset_y": -51, "width": 303, "height": 213},
            "23": {"offset_x": 21, "offset_y": -51, "width": 408, "height": 306},
            "24": {"offset_x": 9, "offset_y": -54, "width": 417, "height": 312},
            "25": {"offset_x": 9, "offset_y": -57, "width": 408, "height": 321},
            "26": {"offset_x": 48, "offset_y": -54, "width": 417, "height": 312},
            "27": {"offset_x": 21, "offset_y": -51, "width": 408, "height": 306},
            "28": {"offset_x": 21, "offset_y": -51, "width": 384, "height": 303},
            "29": {"offset_x": 30, "offset_y": -45, "width": 366, "height": 273},
            "30": {"offset_x": 39, "offset_y": -36, "width": 345, "height": 294},
            "31": {"offset_x": 33, "offset_y": -30, "width": 336, "height": 285},
            "32": {"offset_x": 21, "offset_y": -21, "width": 300, "height": 264},
            "33": {"offset_x": 21, "offset_y": -18, "width": 279, "height": 261},
        },
        "startup_frames": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13],
        "recovery_frames": []
    },
    "ENHANCED_SPECIAL_ATTACK_CONFIG": {
        "hit_frames": [6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18],
        "base_damage": 50.0,
        "knockback_force": 20.0,
        "knockback_angle": 45.0,
        "hit_stop_frames": 19,
        "can_hit_multiple": True,
        "max_hits_per_target": 4,
        "frame_damage_modifiers": {},
        "hitbox_data": {
            "6": {"offset_x": 3, "offset_y": -63, "width": 810, "height": 348},
            "7": {"offset_x": -3, "offset_y": -75, "width": 810, "height": 372},
            "8": {"offset_x": 3, "offset_y": -75, "width": 837, "height": 372},
            "9": {"offset_x": 0, "offset_y": -78, "width": 846, "height": 381},
            "10": {"offset_x": -3, "offset_y": -75, "width": 810, "height": 372},
            "11": {"offset_x": 3, "offset_y": -75, "width": 837, "height": 372},
            "12": {"offset_x": 0, "offset_y": -78, "width": 846, "height": 381},
            "13": {"offset_x": -15, "offset_y": -30, "width": 507, "height": 282},
            "14": {"offset_x": -21, "offset_y": 27, "width": 249, "height": 168},
            "15": {"offset_x": -18, "offset_y": 27, "width": 162, "height": 171},
            "16": {"offset_x": -18, "offset_y": 9, "width": 159, "height": 204},
            "17": {"offset_x": -21, "offset_y": -60, "width": 177, "height": 345},
            "18": {"offset_x": 3, "offset_y": -9, "width": 213, "height": 243},
        },
        "startup_frames": [0, 1, 2, 3, 4, 5],
        "recovery_frames": []
    }
}

STATE_ASSETS = {
    "DEATH": ("assets/shadow_warrior/death/death_{}.png", 12, None, 0),
    "DEFEND": ("assets/shadow_warrior/defend/defend_{}.png", 7, "assets/shadow_warrior/e_defend/e_defend_{}.png", 6),
    "HURT": ("assets/shadow_warrior/take_hit/take_hit_{}.png", 6, "assets/shadow_warrior/e_take_hit/e_take_hit_{}.png", 7),
    "ATTACK_THRUST": ("assets/shadow_warrior/1_atk/1_atk_{}.png", 9, "assets/shadow_warrior/e_1_atk/e_1_atk_{}.png", 14),
    "ATTACK_SMASH": ("assets/shadow_warrior/2_atk/2_atk_{}.png", 17, "assets/shadow_warrior/e_2_atk/e_2_atk_{}.png", 22),
    "ATTACK_POWER": ("assets/shadow_warrior/3_atk/3_atk_{}.png", 23, "assets/shadow_warrior/e_3_atk/e_3_atk_{}.png", 35),
    "JUMP_UP": ("assets/shadow_warrior/jump_up_loop/jump_up_loop_{}.png", 3, "assets/shadow_warrior/e_jump_up/e_jump_up_{}.png", 3),
    "JUMP_DOWN": ("assets/shadow_warrior/jump_down_loop/jump_down_loop_{}.png", 3, "assets/shadow_warrior/e_jump_down/e_jump_down_{}.png", 3),
    "RUN": ("assets/shadow_warrior/run/run_{}.png", 10, "assets/shadow_warrior/e_run/e_run_{}.png", 10),
    "IDLE": ("assets/shadow_warrior/idle/idle_{}.png", 12, "assets/shadow_warrior/e_idle/e_idle_{}.png", 18),
    "SPECIAL_ATTACK": ("assets/shadow_warrior/sp_atk/sp_atk_{}.png", 34, "assets/shadow_warrior/e_sp_atk/e_sp_atk_{}.png", 19),
    "TRANSFORM": ("assets/shadow_warrior/transform/transform_{}.png", 37, None, 0),
    "ROLL": ("assets/shadow_warrior/roll/roll_{}.png", 8, None, 0),
    "DASH": ("assets/shadow_warrior/dash/dash_{}.png", 12, None, 0),
}


class Slider:
    def __init__(self, key: str, label: str, x: int, y: int, w: int, min_val: float, max_val: float, current_val: float, is_float: bool = False, format_str: str = "{val}", enabled: bool = True):
        self.key = key
        self.label = label
        self.rect = pg.Rect(x, y, w, 8)
        self.handle_r = 9
        self.min_val = min_val
        self.max_val = max_val
        self.val = current_val
        self.dragging = False
        self.is_float = is_float
        self.format_str = format_str
        self.enabled = enabled

    def get_handle_pos(self) -> tuple[int, int]:
        if self.max_val == self.min_val:
            ratio = 0.0
        else:
            ratio = (self.val - self.min_val) / (self.max_val - self.min_val)
        return int(self.rect.x + ratio * self.rect.width), self.rect.centery

    def draw(self, surface: pg.Surface):
        val_display = self.format_str.format(val=round(self.val, 2) if self.is_float else int(self.val))
        label_color = TEXT_COLOR if self.enabled else TEXT_MUTED
        val_color = ACCENT_CYAN if self.enabled else TEXT_MUTED
        
        txt_label = ui_font.render(self.label, True, label_color)
        txt_val = value_font.render(val_display, True, val_color)
        
        surface.blit(txt_label, (self.rect.x, self.rect.y - 22))
        surface.blit(txt_val, (self.rect.right - txt_val.get_width(), self.rect.y - 22))

        # Slider track
        track_color = (40, 40, 55) if self.enabled else (30, 30, 40)
        pg.draw.rect(surface, track_color, self.rect, border_radius=4)
        
        # Fill track
        hx, hy = self.get_handle_pos()
        if self.enabled:
            fill_rect = pg.Rect(self.rect.x, self.rect.y, hx - self.rect.x, self.rect.height)
            pg.draw.rect(surface, ACCENT_BLUE, fill_rect, border_radius=4)
            # Handle circle
            pg.draw.circle(surface, (255, 255, 255), (hx, hy), self.handle_r)
            if self.dragging:
                pg.draw.circle(surface, ACCENT_CYAN, (hx, hy), self.handle_r - 2)
        else:
            pg.draw.circle(surface, (70, 70, 85), (hx, hy), self.handle_r)

    def handle_event(self, event: pg.event.Event):
        if not self.enabled:
            return
        if event.type == pg.MOUSEBUTTONDOWN:
            if event.button == 1:
                hx, hy = self.get_handle_pos()
                m_pos = event.pos
                dist = ((m_pos[0] - hx) ** 2 + (m_pos[1] - hy) ** 2) ** 0.5
                if dist <= self.handle_r + 5 or self.rect.collidepoint(m_pos):
                    self.dragging = True
                    self.update_val(m_pos[0])
        elif event.type == pg.MOUSEBUTTONUP:
            if event.button == 1:
                self.dragging = False
        elif event.type == pg.MOUSEMOTION:
            if self.dragging:
                self.update_val(event.pos[0])

    def update_val(self, mx: int):
        mx = max(self.rect.x, min(mx, self.rect.right))
        if self.rect.width == 0:
            ratio = 0.0
        else:
            ratio = (mx - self.rect.x) / self.rect.width
        raw_val = self.min_val + ratio * (self.max_val - self.min_val)
        if self.is_float:
            self.val = round(raw_val, 2)
        else:
            self.val = int(raw_val)


class Checkbox:
    def __init__(self, key: str, label: str, x: int, y: int, val: bool, enabled: bool = True):
        self.key = key
        self.label = label
        self.rect = pg.Rect(x, y, 20, 20)
        self.val = val
        self.enabled = enabled

    def draw(self, surface: pg.Surface):
        bg_color = (40, 40, 55) if self.enabled else (25, 25, 35)
        pg.draw.rect(surface, bg_color, self.rect, border_radius=4)
        pg.draw.rect(surface, BORDER_COLOR, self.rect, width=1, border_radius=4)
        if self.val:
            tick_color = ACCENT_GREEN if self.enabled else TEXT_MUTED
            tick_rect = pg.Rect(self.rect.x + 4, self.rect.y + 4, 12, 12)
            pg.draw.rect(surface, tick_color, tick_rect, border_radius=2)
        
        label_color = TEXT_COLOR if self.enabled else TEXT_MUTED
        txt_label = ui_font.render(self.label, True, label_color)
        surface.blit(txt_label, (self.rect.right + 10, self.rect.y + (self.rect.height - txt_label.get_height()) // 2))

    def handle_event(self, event: pg.event.Event):
        if not self.enabled:
            return False
        if event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
            # Collide with checkbox or its label area
            clickable_area = pg.Rect(self.rect.x, self.rect.y, 220, self.rect.height)
            if clickable_area.collidepoint(event.pos):
                self.val = not self.val
                return True
        return False


class Button:
    def __init__(self, text: str, x: int, y: int, w: int, h: int, callback: Any, active: bool = False):
        self.text = text
        self.rect = pg.Rect(x, y, w, h)
        self.callback = callback
        self.active = active

    def draw(self, surface: pg.Surface):
        color = ACCENT_PURPLE if self.active else (48, 48, 64)
        hover_color = (200, 50, 255) if self.active else (64, 64, 86)
        
        m_pos = pg.mouse.get_pos()
        draw_color = hover_color if self.rect.collidepoint(m_pos) else color
        
        pg.draw.rect(surface, draw_color, self.rect, border_radius=6)
        pg.draw.rect(surface, BORDER_COLOR, self.rect, width=1, border_radius=6)
        
        txt = ui_font.render(self.text, True, (255, 255, 255))
        txt_rect = txt.get_rect(center=self.rect.center)
        surface.blit(txt, txt_rect)

    def handle_event(self, event: pg.event.Event):
        if event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self.callback()


class PlayerEditorApp:
    def __init__(self):
        self.clock = pg.time.Clock()
        self.running = True
        
        # Navigation / Screen Mode: "MENU", "STATES", "ATTACKS"
        self.mode = "MENU"
        
        self.config_dir = "game_data"
        self.config_path = os.path.join(self.config_dir, "player_config.json")
        self.config: Dict[str, Dict[str, Any]] = {}
        self.attack_config: Dict[str, Dict[str, Any]] = {}
        self.load_config()

        # UI Setup (States mode defaults)
        self.selected_state = "IDLE"
        self.enhanced_preview = False
        self.flip_preview = False
        self.is_playing = True
        self.frame_index = 0.0

        # UI Setup (Attacks mode defaults)
        self.selected_attack = "THRUST_ATTACK_CONFIG"
        self.selected_attack_frame = 0

        # Backups list tracking for rollback
        self.backups: List[str] = []
        self.selected_backup_index = -1
        self.scan_backups()

        # Left lists rebuild
        self.state_buttons: List[Button] = []
        self.attack_buttons: List[Button] = []
        self.rebuild_state_buttons()
        self.rebuild_attack_buttons()

        # State configurator sliders/checkboxes
        self.anim_speed_slider: Slider = Slider("animation_speed", "Animation Frame Speed", 320, 100, 420, 0.05, 1.0, 0.2, is_float=True)
        self.checkboxes: List[Checkbox] = []
        self.load_state_parameters(self.selected_state)

        # Attack configurator sliders/checkboxes
        self.attack_sliders: List[Slider] = []
        self.attack_can_hit_multiple_cb: Optional[Checkbox] = None
        self.attack_frame_slider: Optional[Slider] = None
        self.frame_role_checkboxes: List[Checkbox] = []
        self.frame_sliders: List[Slider] = []

        # Visualizer options
        self.preview_scale = 3.5
        self.preview_scale_slider = Slider("scale", "Preview Scale", 830, 520, 200, 1.0, 6.0, self.preview_scale, is_float=True, format_str="{val}x")
        self.playback_speed = 1.0
        self.playback_speed_slider = Slider("play_speed", "Playback Rate", 1050, 520, 200, 0.2, 3.0, self.playback_speed, is_float=True, format_str="{val}x")

        # Action Buttons will be set dynamically per mode
        self.action_buttons: List[Button] = []
        
        # Setup Main Menu Buttons
        self.menu_buttons = [
            Button("1. EDIT STATE MACHINE CONFIGS", SCREEN_W // 2 - 220, 220, 440, 60, lambda: self.enter_mode("STATES")),
            Button("2. EDIT ATTACK HITBOX & COMBAT CONFIGS", SCREEN_W // 2 - 220, 310, 440, 60, lambda: self.enter_mode("ATTACKS")),
            Button("3. EXIT EDITOR", SCREEN_W // 2 - 220, 400, 440, 60, self.exit_app)
        ]

        # Toast Message system
        self.toast_msg = ""
        self.toast_timer = 0.0

        # Animation Cache
        self.animation_cache: Dict[str, Dict[str, List[pg.Surface]]] = {"std": {}, "enh": {}}
        self.load_all_animations()

    def enter_mode(self, mode: str):
        self.mode = mode
        self.frame_index = 0.0
        self.is_playing = True
        
        if mode == "STATES":
            self.load_state_parameters(self.selected_state)
            self.rebuild_state_buttons()
            self.action_buttons = [
                Button("SAVE & MENU", 320, 640, 140, 40, self.request_save_config, active=True),
                Button("RESET DEFAULTS", 475, 640, 140, 40, self.reset_defaults),
                Button("ROLLBACK", 940, 640, 130, 40, self.rollback_config),
                Button("BACK TO MENU", 630, 640, 140, 40, lambda: self.enter_mode("MENU"))
            ]
        elif mode == "ATTACKS":
            self.load_attack_parameters(self.selected_attack)
            self.rebuild_attack_buttons()
            self.action_buttons = [
                Button("SAVE & MENU", 320, 640, 140, 40, self.request_save_config, active=True),
                Button("RESET DEFAULTS", 475, 640, 140, 40, self.reset_attack_defaults),
                Button("BACK TO MENU", 630, 640, 140, 40, lambda: self.enter_mode("MENU"))
            ]

    def exit_app(self):
        self.running = False

    def load_config(self):
        self.config = {}
        self.attack_config = {}
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r") as f:
                    data = json.load(f)
                
                # Dynamic detection of nested vs legacy structure
                if isinstance(data, dict) and ("states" in data or "attacks" in data):
                    self.config = data.get("states", {})
                    self.attack_config = data.get("attacks", {})
                else:
                    self.config = data
                    self.attack_config = {}

                # Backfill missing states
                for state, val in DEFAULT_PLAYER_CONFIGS.items():
                    if state not in self.config:
                        self.config[state] = val.copy()

                # Backfill missing attacks
                for attack, val in DEFAULT_ATTACK_CONFIGS.items():
                    if attack not in self.attack_config:
                        self.attack_config[attack] = json.loads(json.dumps(val))
            except Exception as e:
                print(f"[WARNING] Failed to load config: {e}. Reverting to defaults.")
                self.config = {k: v.copy() for k, v in DEFAULT_PLAYER_CONFIGS.items()}
                self.attack_config = json.loads(json.dumps(DEFAULT_ATTACK_CONFIGS))
        else:
            self.config = {k: v.copy() for k, v in DEFAULT_PLAYER_CONFIGS.items()}
            self.attack_config = json.loads(json.dumps(DEFAULT_ATTACK_CONFIGS))

    def scan_backups(self):
        self.backups = []
        if os.path.exists(self.config_dir):
            files = os.listdir(self.config_dir)
            for f in files:
                if f.startswith("player_config.backup_") and f.endswith(".json"):
                    self.backups.append(f)
            # Sort chronologically by name
            self.backups.sort(reverse=True)

    def load_state_parameters(self, state: str):
        cfg = self.config[state]
        self.anim_speed_slider = Slider("animation_speed", "Animation Frame Speed", 320, 100, 420, 0.05, 1.0, cfg["animation_speed"], is_float=True)
        
        self.checkboxes = [
            Checkbox("loops", "Loops Animation", 320, 160, cfg["loops"]),
            Checkbox("interruptible", "Interruptible State", 320, 200, cfg["interruptible"]),
            Checkbox("grants_invincibility", "Grants Invincibility (i-frames)", 320, 240, cfg["grants_invincibility"]),
            Checkbox("locks_movement", "Locks Horizontal Movement", 320, 280, cfg["locks_movement"]),
            Checkbox("locks_input", "Locks Action/Input controls", 320, 320, cfg["locks_input"]),
        ]

    def save_current_state_parameters(self):
        state = self.selected_state
        self.config[state]["animation_speed"] = self.anim_speed_slider.val
        for cb in self.checkboxes:
            self.config[state][cb.key] = cb.val

    def get_attack_state_and_frames(self) -> tuple[str, int]:
        if self.selected_attack == "THRUST_ATTACK_CONFIG":
            return "ATTACK_THRUST", 9
        elif self.selected_attack == "SMASH_ATTACK_CONFIG":
            return "ATTACK_SMASH", 17
        elif self.selected_attack == "POWER_ATTACK_CONFIG":
            return "ATTACK_POWER", 23
        elif self.selected_attack == "SPECIAL_ATTACK_CONFIG":
            return "SPECIAL_ATTACK", 34
        elif self.selected_attack == "ENHANCED_SPECIAL_ATTACK_CONFIG":
            return "SPECIAL_ATTACK", 19
        return "IDLE", 1

    def load_attack_parameters(self, attack: str):
        # Auto swap enhanced form checkbox to match selected special variant
        if attack == "ENHANCED_SPECIAL_ATTACK_CONFIG":
            self.enhanced_preview = True
        elif attack == "SPECIAL_ATTACK_CONFIG":
            self.enhanced_preview = False

        atk = self.attack_config[attack]
        
        # General parameters (compact layout)
        self.attack_sliders = [
            Slider("base_damage", "Base Damage", 320, 105, 420, 0.0, 100.0, float(atk.get("base_damage", 10.0)), is_float=True),
            Slider("knockback_force", "Knockback Force", 320, 143, 420, 0.0, 50.0, float(atk.get("knockback_force", 5.0)), is_float=True),
            Slider("knockback_angle", "Knockback Angle", 320, 181, 420, 0.0, 360.0, float(atk.get("knockback_angle", 45.0)) if atk.get("knockback_angle") is not None else 45.0, is_float=True),
            Slider("hit_stop_frames", "Hit Stop Frames", 320, 219, 420, 0.0, 60.0, float(atk.get("hit_stop_frames", 0.0)), is_float=False),
            Slider("max_hits_per_target", "Max Hits Per Target", 320, 257, 420, 1.0, 10.0, float(atk.get("max_hits_per_target", 1.0)), is_float=False),
        ]
        self.attack_can_hit_multiple_cb = Checkbox("can_hit_multiple", "Can Hit Multiple Targets", 320, 290, bool(atk.get("can_hit_multiple", True)))
        
        # Timeline slider
        state_name, total_frames = self.get_attack_state_and_frames()
        self.selected_attack_frame = 0
        self.attack_frame_slider = Slider("frame_idx", "Selected Active Frame", 320, 350, 420, 0.0, float(total_frames - 1), 0.0, is_float=False)
        
        self.load_frame_parameters()

    def load_frame_parameters(self):
        atk = self.attack_config[self.selected_attack]
        frame = self.selected_attack_frame
        
        is_hit = frame in atk.get("hit_frames", [])
        is_startup = frame in atk.get("startup_frames", [])
        is_recovery = frame in atk.get("recovery_frames", [])
        
        self.frame_role_checkboxes = [
            Checkbox("is_hit", "Is Active/Hit Frame", 320, 400, is_hit),
            Checkbox("is_startup", "Is Startup Frame", 470, 400, is_startup),
            Checkbox("is_recovery", "Is Recovery/End Frame", 610, 400, is_recovery)
        ]
        
        # Load hitbox data
        hitbox_dict = atk.get("hitbox_data", {})
        hb_data = hitbox_dict.get(str(frame), {})
        offset_x = hb_data.get("offset_x", 180)
        offset_y = hb_data.get("offset_y", 20)
        width = hb_data.get("width", 250)
        height = hb_data.get("height", 100)
        
        # Load frame damage modifier
        modifiers_dict = atk.get("frame_damage_modifiers", {})
        modifier = modifiers_dict.get(str(frame), 1.0)
        
        # Hitbox sliders are only interactive/enabled when Is Hit Frame is checked
        self.frame_sliders = [
            Slider("offset_x", "Hitbox Offset X", 320, 445, 200, -400.0, 400.0, float(offset_x), is_float=False, enabled=is_hit),
            Slider("offset_y", "Hitbox Offset Y", 540, 445, 200, -400.0, 400.0, float(offset_y), is_float=False, enabled=is_hit),
            Slider("width", "Hitbox Width", 320, 495, 200, 10.0, 800.0, float(width), is_float=False, enabled=is_hit),
            Slider("height", "Hitbox Height", 540, 495, 200, 10.0, 800.0, float(height), is_float=False, enabled=is_hit),
            Slider("modifier", "Frame Damage Modifier", 320, 545, 420, 0.0, 2.0, float(modifier), is_float=True, enabled=is_hit)
        ]

    def save_current_frame_parameters(self):
        atk = self.attack_config[self.selected_attack]
        frame = self.selected_attack_frame
        
        is_hit = self.frame_role_checkboxes[0].val
        is_startup = self.frame_role_checkboxes[1].val
        is_recovery = self.frame_role_checkboxes[2].val
        
        # 1. Update lists
        hit_list = atk.setdefault("hit_frames", [])
        if is_hit and frame not in hit_list:
            hit_list.append(frame)
        elif not is_hit and frame in hit_list:
            if frame in hit_list:
                hit_list.remove(frame)
        hit_list.sort()
            
        startup_list = atk.setdefault("startup_frames", [])
        if is_startup and frame not in startup_list:
            startup_list.append(frame)
        elif not is_startup and frame in startup_list:
            if frame in startup_list:
                startup_list.remove(frame)
        startup_list.sort()
            
        recovery_list = atk.setdefault("recovery_frames", [])
        if is_recovery and frame not in recovery_list:
            recovery_list.append(frame)
        elif not is_recovery and frame in recovery_list:
            if frame in recovery_list:
                recovery_list.remove(frame)
        recovery_list.sort()
            
        # 2. Update hitbox sliders if active
        offset_x = int(self.frame_sliders[0].val)
        offset_y = int(self.frame_sliders[1].val)
        width = int(self.frame_sliders[2].val)
        height = int(self.frame_sliders[3].val)
        modifier = self.frame_sliders[4].val
        
        hitbox_dict = atk.setdefault("hitbox_data", {})
        if is_hit:
            hitbox_dict[str(frame)] = {
                "offset_x": offset_x,
                "offset_y": offset_y,
                "width": width,
                "height": height
            }
        else:
            if str(frame) in hitbox_dict:
                del hitbox_dict[str(frame)]
                
        modifiers_dict = atk.setdefault("frame_damage_modifiers", {})
        if is_hit and modifier != 1.0:
            modifiers_dict[str(frame)] = modifier
        else:
            if str(frame) in modifiers_dict:
                del modifiers_dict[str(frame)]

    def save_current_attack_parameters(self):
        atk = self.attack_config[self.selected_attack]
        atk["base_damage"] = self.attack_sliders[0].val
        atk["knockback_force"] = self.attack_sliders[1].val
        atk["knockback_angle"] = self.attack_sliders[2].val
        atk["hit_stop_frames"] = int(self.attack_sliders[3].val)
        atk["max_hits_per_target"] = int(self.attack_sliders[4].val)
        if self.attack_can_hit_multiple_cb is not None:
            atk["can_hit_multiple"] = self.attack_can_hit_multiple_cb.val
        
        self.save_current_frame_parameters()

    def rebuild_state_buttons(self):
        self.state_buttons = []
        x = 30
        y = 70
        for state in DEFAULT_PLAYER_CONFIGS.keys():
            btn = Button(state, x, y, 240, 36, lambda s=state: self.select_state(s), active=(state == self.selected_state))
            self.state_buttons.append(btn)
            y += 44

    def rebuild_attack_buttons(self):
        self.attack_buttons = []
        x = 30
        y = 70
        attacks = [
            "THRUST_ATTACK_CONFIG",
            "SMASH_ATTACK_CONFIG",
            "POWER_ATTACK_CONFIG",
            "SPECIAL_ATTACK_CONFIG",
            "ENHANCED_SPECIAL_ATTACK_CONFIG"
        ]
        for atk in attacks:
            clean_label = atk.replace("_CONFIG", "")
            btn = Button(clean_label, x, y, 240, 36, lambda a=atk: self.select_attack(a), active=(atk == self.selected_attack))
            self.attack_buttons.append(btn)
            y += 44

    def select_state(self, state: str):
        self.save_current_state_parameters()
        self.selected_state = state
        self.frame_index = 0.0
        self.load_state_parameters(state)
        self.rebuild_state_buttons()

    def select_attack(self, attack: str):
        self.save_current_attack_parameters()
        self.selected_attack = attack
        self.frame_index = 0.0
        self.load_attack_parameters(attack)
        self.rebuild_attack_buttons()

    def request_save_config(self):
        if self.mode == "STATES":
            self.save_current_state_parameters()
        elif self.mode == "ATTACKS":
            self.save_current_attack_parameters()
            
        os.makedirs(self.config_dir, exist_ok=True)
        
        # Safe transaction: 1. Backup old config first
        if os.path.exists(self.config_path):
            try:
                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_filename = f"player_config.backup_{ts}.json"
                backup_path = os.path.join(self.config_dir, backup_filename)
                shutil.copy2(self.config_path, backup_path)
                print(f"[INFO] Created dynamic config backup at {backup_path}")
            except Exception as e:
                print(f"[WARNING] Backup creation failed: {e}")

        # Safe transaction: 2. Write atomic save
        try:
            temp_path = self.config_path + ".tmp"
            combined_data = {
                "states": self.config,
                "attacks": self.attack_config
            }
            with open(temp_path, "w") as f:
                json.dump(combined_data, f, indent=2)
            os.replace(temp_path, self.config_path) # Atomic file replace
            self.show_toast("Config Committed & Saved!")
            self.scan_backups()
            self.selected_backup_index = -1
            
            # Save returns back to Main Menu
            self.mode = "MENU"
        except Exception as e:
            self.show_toast("Commit Failed!")
            print(f"[ERROR] Atomic commit failed: {e}")

    def rollback_config(self):
        if self.selected_backup_index < 0 or self.selected_backup_index >= len(self.backups):
            self.show_toast("Select Backup First!")
            return
            
        backup_file = self.backups[self.selected_backup_index]
        backup_path = os.path.join(self.config_dir, backup_file)
        
        try:
            with open(backup_path, "r") as f:
                rolled_data = json.load(f)
            
            if isinstance(rolled_data, dict) and ("states" in rolled_data or "attacks" in rolled_data):
                self.config = rolled_data.get("states", {})
                self.attack_config = rolled_data.get("attacks", {})
            else:
                self.config = rolled_data
                self.attack_config = json.loads(json.dumps(DEFAULT_ATTACK_CONFIGS))
                
            # Fill missing entries
            for state, val in DEFAULT_PLAYER_CONFIGS.items():
                if state not in self.config:
                    self.config[state] = val.copy()
            for attack, val in DEFAULT_ATTACK_CONFIGS.items():
                if attack not in self.attack_config:
                    self.attack_config[attack] = json.loads(json.dumps(val))
            
            if self.mode == "STATES":
                self.load_state_parameters(self.selected_state)
            elif self.mode == "ATTACKS":
                self.load_attack_parameters(self.selected_attack)
                
            self.show_toast(f"Rolled back to {backup_file[21:36]}!")
        except Exception as e:
            self.show_toast("Rollback Failed!")
            print(f"[ERROR] Rollback failed: {e}")

    def reset_defaults(self):
        self.config = {k: v.copy() for k, v in DEFAULT_PLAYER_CONFIGS.items()}
        self.load_state_parameters(self.selected_state)
        self.show_toast("Reset states to defaults")

    def reset_attack_defaults(self):
        self.attack_config = json.loads(json.dumps(DEFAULT_ATTACK_CONFIGS))
        self.load_attack_parameters(self.selected_attack)
        self.show_toast("Reset attacks to defaults")

    def show_toast(self, msg: str):
        self.toast_msg = msg
        self.toast_timer = 2.0

    def load_all_animations(self):
        for state, (std_pattern, std_count, enh_pattern, enh_count) in STATE_ASSETS.items():
            self.animation_cache["std"][state] = self._load_frames_direct(std_pattern, std_count)
            if enh_pattern:
                self.animation_cache["enh"][state] = self._load_frames_direct(enh_pattern, enh_count)
            else:
                self.animation_cache["enh"][state] = self.animation_cache["std"][state]

    def _load_frames_direct(self, pattern: str, count: int) -> List[pg.Surface]:
        frames = []
        for i in range(1, count + 1):
            f_path = pattern.format(i)
            if os.path.exists(f_path):
                try:
                    frames.append(pg.image.load(f_path).convert_alpha())
                except Exception as e:
                    print(f"[WARNING] Failed to load frame {f_path}: {e}")
                    frames.append(self._create_dummy_surf(state_name="Error"))
            else:
                frames.append(self._create_dummy_surf(state_name="Missing"))
        if not frames:
            frames.append(self._create_dummy_surf(state_name="Empty"))
        return frames

    def _create_dummy_surf(self, state_name: str) -> pg.Surface:
        surf = pg.Surface((96, 96), pg.SRCALPHA)
        pg.draw.rect(surf, (200, 0, 100), (24, 24, 48, 48), 2)
        txt = value_font.render(state_name, True, (200, 200, 200))
        surf.blit(txt, (48 - txt.get_width() // 2, 48 - txt.get_height() // 2))
        return surf

    def draw_menu(self):
        screen.fill(BG_COLOR)
        
        # Blueprint grid effect
        for x in range(0, SCREEN_W, 40):
            pg.draw.line(screen, (24, 24, 34), (x, 0), (x, SCREEN_H))
        for y in range(0, SCREEN_H, 40):
            pg.draw.line(screen, (24, 24, 34), (0, y), (SCREEN_W, y))
            
        # Draw Menu Panel
        menu_panel = pg.Rect(SCREEN_W // 2 - 300, 60, 600, 580)
        pg.draw.rect(screen, PANEL_BG, menu_panel, border_radius=12)
        pg.draw.rect(screen, BORDER_COLOR, menu_panel, width=1, border_radius=12)

        # Title
        menu_title = title_font.render("PLAYER CHARACTER EDITOR", True, ACCENT_GREEN)
        screen.blit(menu_title, (SCREEN_W // 2 - menu_title.get_width() // 2, 90))
        
        subtitle = ui_font.render("Configure Player Animations, Hitboxes, and Stats", True, TEXT_MUTED)
        screen.blit(subtitle, (SCREEN_W // 2 - subtitle.get_width() // 2, 130))
        
        # Descriptions
        descs = [
            ("Edit State Machine Configs", "Tune animation frame speeds, looping, and reactive action lock states."),
            ("Edit Attack Hitbox Configs", "Configure base damages, knockbacks, active frames, and frame-perfect hitboxes."),
            ("Exit Editor", "Close configurations and return to command line terminal.")
        ]
        
        for btn in self.menu_buttons:
            btn.draw(screen)

        # Draw descriptions next to the options
        y_offset = 240
        for label, desc in descs:
            txt_desc = help_font.render(desc, True, TEXT_MUTED)
            screen.blit(txt_desc, (SCREEN_W // 2 - txt_desc.get_width() // 2, y_offset))
            y_offset += 90

    def draw_states(self):
        # 1. Left Sidebar (State list)
        sidebar_rect = pg.Rect(20, 60, 260, 640)
        pg.draw.rect(screen, PANEL_BG, sidebar_rect, border_radius=8)
        pg.draw.rect(screen, BORDER_COLOR, sidebar_rect, width=1, border_radius=8)
        for btn in self.state_buttons:
            btn.draw(screen)

        # 2. Middle Parameter Panel
        param_panel = pg.Rect(300, 60, 460, 640)
        pg.draw.rect(screen, PANEL_BG, param_panel, border_radius=8)
        pg.draw.rect(screen, BORDER_COLOR, param_panel, width=1, border_radius=8)
        
        subtitle = title_font.render(f"CONFIG: {self.selected_state}", True, ACCENT_CYAN)
        screen.blit(subtitle, (320, 75))

        self.anim_speed_slider.draw(screen)
        for cb in self.checkboxes:
            cb.draw(screen)

        # Commits & Rollback sub-panel
        div_rect = pg.Rect(310, 360, 440, 1)
        pg.draw.rect(screen, BORDER_COLOR, div_rect)
        
        rollback_title = ui_font.render("REVISION HISTORY & ROLLBACK LOCKS", True, ACCENT_PURPLE)
        screen.blit(rollback_title, (320, 375))
        
        # Render a simple revision list
        rev_box = pg.Rect(320, 405, 420, 215)
        pg.draw.rect(screen, PREVIEW_BG, rev_box, border_radius=6)
        pg.draw.rect(screen, BORDER_COLOR, rev_box, width=1, border_radius=6)

        # Draw revision list items
        y_offset = rev_box.y + 10
        visible_backups = self.backups[:5]
        if not visible_backups:
            txt = value_font.render("No backup revisions found.", True, TEXT_MUTED)
            screen.blit(txt, (rev_box.x + 15, rev_box.y + 15))
        else:
            for idx, backup in enumerate(visible_backups):
                # Highlight if selected
                item_rect = pg.Rect(rev_box.x + 5, y_offset - 2, rev_box.width - 10, 32)
                if idx == self.selected_backup_index:
                    pg.draw.rect(screen, (55, 30, 75), item_rect, border_radius=4)
                    pg.draw.rect(screen, ACCENT_PURPLE, item_rect, width=1, border_radius=4)
                
                # Render label
                timestamp_str = backup[21:36]
                try:
                    dt = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
                    friendly_time = dt.strftime("%Y-%m-%d %H:%M:%S")
                except:
                    friendly_time = timestamp_str
                
                txt_time = value_font.render(friendly_time, True, TEXT_COLOR)
                screen.blit(txt_time, (rev_box.x + 15, y_offset + 5))
                y_offset += 38

        # Draw Action buttons
        for btn in self.action_buttons:
            btn.draw(screen)

        # 3. Right Visualizer Panel
        preview_panel = pg.Rect(780, 60, 480, 640)
        pg.draw.rect(screen, PANEL_BG, preview_panel, border_radius=8)
        pg.draw.rect(screen, BORDER_COLOR, preview_panel, width=1, border_radius=8)

        preview_title = title_font.render("ANIMATION PREVIEW", True, ACCENT_GREEN)
        screen.blit(preview_title, (800, 75))

        # Real-time player animation viewport
        view_box = pg.Rect(800, 115, 440, 320)
        pg.draw.rect(screen, PREVIEW_BG, view_box, border_radius=6)
        pg.draw.rect(screen, BORDER_COLOR, view_box, width=1, border_radius=6)

        # Get active frame list
        cache_key = "enh" if self.enhanced_preview else "std"
        frames = self.animation_cache[cache_key].get(self.selected_state, [])
        
        if frames:
            frame_idx = int(self.frame_index) % len(frames)
            active_surf = frames[frame_idx]
            
            # Flip if enabled
            if self.flip_preview:
                active_surf = pg.transform.flip(active_surf, True, False)
                
            # Scale
            self.preview_scale = self.preview_scale_slider.val
            new_w = int(active_surf.get_width() * self.preview_scale)
            new_h = int(active_surf.get_height() * self.preview_scale)
            scaled_surf = pg.transform.scale(active_surf, (new_w, new_h))
            
            # Center on viewport
            surf_rect = scaled_surf.get_rect(center=view_box.center)
            
            # Clip inside viewport
            screen.set_clip(view_box)
            screen.blit(scaled_surf, surf_rect)
            screen.set_clip(None)

            # Frame label
            txt_fr = value_font.render(f"Frame: {frame_idx + 1} / {len(frames)}", True, TEXT_MUTED)
            screen.blit(txt_fr, (view_box.x + 10, view_box.bottom - 22))

        # Preview control buttons/switches
        enh_cb_rect = pg.Rect(800, 455, 20, 20)
        pg.draw.rect(screen, (40, 40, 55), enh_cb_rect, border_radius=4)
        if self.enhanced_preview:
            pg.draw.rect(screen, ACCENT_CYAN, pg.Rect(804, 459, 12, 12), border_radius=2)
        txt_enh = ui_font.render("Enhanced / Shadow Form", True, TEXT_COLOR)
        screen.blit(txt_enh, (830, 455))

        flip_cb_rect = pg.Rect(1050, 455, 20, 20)
        pg.draw.rect(screen, (40, 40, 55), flip_cb_rect, border_radius=4)
        if self.flip_preview:
            pg.draw.rect(screen, ACCENT_CYAN, pg.Rect(1054, 459, 12, 12), border_radius=2)
        txt_flip = ui_font.render("Flip Facing Left", True, TEXT_COLOR)
        screen.blit(txt_flip, (1080, 455))

        self.preview_scale_slider.draw(screen)
        self.playback_speed_slider.draw(screen)

        # Info Box explaining effects
        info_rect = pg.Rect(800, 570, 440, 115)
        pg.draw.rect(screen, PREVIEW_BG, info_rect, border_radius=6)
        pg.draw.rect(screen, BORDER_COLOR, info_rect, width=1, border_radius=6)
        
        help_lines = [
            "State priority tier dictates action override controls.",
            "Invincibility: player ignores boss attacks during these frames.",
            "Locks Movement: horizontal input velocity is zeroed.",
            "Locks Input: player cannot switch states or trigger attacks."
        ]
        y_hl = info_rect.y + 10
        for hl in help_lines:
            txt_hl = help_font.render(hl, True, TEXT_MUTED)
            screen.blit(txt_hl, (info_rect.x + 15, y_hl))
            y_hl += 24

    def draw_attacks(self):
        # 1. Left Sidebar (Attack config list)
        sidebar_rect = pg.Rect(20, 60, 260, 640)
        pg.draw.rect(screen, PANEL_BG, sidebar_rect, border_radius=8)
        pg.draw.rect(screen, BORDER_COLOR, sidebar_rect, width=1, border_radius=8)
        for btn in self.attack_buttons:
            btn.draw(screen)

        # 2. Middle Parameter Panel (Attack stats)
        param_panel = pg.Rect(300, 60, 460, 640)
        pg.draw.rect(screen, PANEL_BG, param_panel, border_radius=8)
        pg.draw.rect(screen, BORDER_COLOR, param_panel, width=1, border_radius=8)
        
        subtitle = title_font.render(f"ATTACK CONFIG", True, ACCENT_CYAN)
        screen.blit(subtitle, (320, 75))

        # Render general sliders
        for sl in self.attack_sliders:
            sl.draw(screen)
        if self.attack_can_hit_multiple_cb is not None:
            self.attack_can_hit_multiple_cb.draw(screen)

        # Separator line
        div_rect = pg.Rect(310, 320, 440, 1)
        pg.draw.rect(screen, BORDER_COLOR, div_rect)

        # Sub-panel title
        frame_t_title = ui_font.render("PER-FRAME HITBOX & DAMAGE", True, ACCENT_PURPLE)
        screen.blit(frame_t_title, (320, 335))

        # Frame timeline slider
        if self.attack_frame_slider is not None:
            self.attack_frame_slider.draw(screen)

        # Role checkboxes
        for cb in self.frame_role_checkboxes:
            cb.draw(screen)

        # Frame hitbox sliders
        for sl in self.frame_sliders:
            sl.draw(screen)

        # Draw Action buttons
        for btn in self.action_buttons:
            btn.draw(screen)

        # 3. Right Visualizer Panel
        preview_panel = pg.Rect(780, 60, 480, 640)
        pg.draw.rect(screen, PANEL_BG, preview_panel, border_radius=8)
        pg.draw.rect(screen, BORDER_COLOR, preview_panel, width=1, border_radius=8)

        preview_title = title_font.render("ATTACK HITBOX PREVIEW", True, ACCENT_GREEN)
        screen.blit(preview_title, (800, 75))

        # Real-time player animation viewport
        view_box = pg.Rect(800, 115, 440, 320)
        pg.draw.rect(screen, PREVIEW_BG, view_box, border_radius=6)
        pg.draw.rect(screen, BORDER_COLOR, view_box, width=1, border_radius=6)

        # Get active frame list & render
        state_name, total_frames = self.get_attack_state_and_frames()
        cache_key = "enh" if self.enhanced_preview else "std"
        frames = self.animation_cache[cache_key].get(state_name, [])
        
        if frames:
            frame_idx = int(self.frame_index) % len(frames)
            active_surf = frames[frame_idx]
            
            # Flip if enabled
            if self.flip_preview:
                active_surf = pg.transform.flip(active_surf, True, False)
                
            # Scale
            self.preview_scale = self.preview_scale_slider.val
            new_w = int(active_surf.get_width() * self.preview_scale)
            new_h = int(active_surf.get_height() * self.preview_scale)
            scaled_surf = pg.transform.scale(active_surf, (new_w, new_h))
            
            # Center on viewport
            surf_rect = scaled_surf.get_rect(center=view_box.center)
            
            # Clip inside viewport
            screen.set_clip(view_box)
            screen.blit(scaled_surf, surf_rect)

            # Draw HITBOX Overlay if active frame has hitbox data
            atk = self.attack_config[self.selected_attack]
            is_hit_active = frame_idx in atk.get("hit_frames", [])
            if is_hit_active:
                hb_dict = atk.get("hitbox_data", {}).get(str(frame_idx), {})
                if hb_dict:
                    offset_x = hb_dict.get("offset_x", 0)
                    offset_y = hb_dict.get("offset_y", 0)
                    width = hb_dict.get("width", 50)
                    height = hb_dict.get("height", 50)

                    # Scale hitbox offsets & size
                    scaled_offset_x = int(offset_x * self.preview_scale)
                    scaled_offset_y = int(offset_y * self.preview_scale)
                    scaled_width = int(width * self.preview_scale)
                    scaled_height = int(height * self.preview_scale)

                    # Offset depending on flip facing
                    if self.flip_preview:
                        actual_offset_x = -scaled_offset_x
                    else:
                        actual_offset_x = scaled_offset_x

                    center_x = view_box.centerx + actual_offset_x
                    center_y = view_box.centery + scaled_offset_y

                    # Draw red semi-transparent hitbox fill & border
                    rect = pg.Rect(center_x - scaled_width // 2, center_y - scaled_height // 2, scaled_width, scaled_height)
                    hb_surf = pg.Surface((scaled_width, scaled_height), pg.SRCALPHA)
                    hb_surf.fill((255, 0, 0, 90)) # alpha 90
                    screen.blit(hb_surf, rect.topleft)
                    pg.draw.rect(screen, (255, 50, 50), rect, width=2)

            screen.set_clip(None)

            # Frame label
            txt_fr = value_font.render(f"Frame: {frame_idx + 1} / {len(frames)}", True, TEXT_MUTED)
            screen.blit(txt_fr, (view_box.x + 10, view_box.bottom - 22))

        # Preview control buttons/switches
        enh_cb_rect = pg.Rect(800, 455, 20, 20)
        pg.draw.rect(screen, (40, 40, 55), enh_cb_rect, border_radius=4)
        if self.enhanced_preview:
            pg.draw.rect(screen, ACCENT_CYAN, pg.Rect(804, 459, 12, 12), border_radius=2)
        txt_enh = ui_font.render("Enhanced / Shadow Form", True, TEXT_COLOR)
        screen.blit(txt_enh, (830, 455))

        flip_cb_rect = pg.Rect(1050, 455, 20, 20)
        pg.draw.rect(screen, (40, 40, 55), flip_cb_rect, border_radius=4)
        if self.flip_preview:
            pg.draw.rect(screen, ACCENT_CYAN, pg.Rect(1054, 459, 12, 12), border_radius=2)
        txt_flip = ui_font.render("Flip Facing Left", True, TEXT_COLOR)
        screen.blit(txt_flip, (1080, 455))

        self.preview_scale_slider.draw(screen)
        self.playback_speed_slider.draw(screen)

        # Info Box explaining effects
        info_rect = pg.Rect(800, 570, 440, 115)
        pg.draw.rect(screen, PREVIEW_BG, info_rect, border_radius=6)
        pg.draw.rect(screen, BORDER_COLOR, info_rect, width=1, border_radius=6)
        
        help_lines = [
            "Use the frame timeline slider to scrub frames manually.",
            "Toggle frame roles to set startup, active/hit, and recovery phases.",
            "Active Hitboxes are rendered in RED above.",
            "Press [SPACE] to play/pause the preview loop."
        ]
        y_hl = info_rect.y + 8
        for hl in help_lines:
            txt_hl = help_font.render(hl, True, TEXT_MUTED)
            screen.blit(txt_hl, (info_rect.x + 15, y_hl))
            y_hl += 25

    def draw(self):
        if self.mode == "MENU":
            self.draw_menu()
        else:
            screen.fill(BG_COLOR)
            # Blueprint grid effect
            for x in range(0, SCREEN_W, 40):
                pg.draw.line(screen, (24, 24, 34), (x, 0), (x, SCREEN_H))
            for y in range(0, SCREEN_H, 40):
                pg.draw.line(screen, (24, 24, 34), (0, y), (SCREEN_W, y))

            # Header title
            title_text = "PLAYER ANIMATION CONFIGURATOR & COMMIT MANAGER" if self.mode == "STATES" else "PLAYER ATTACK CONFIGURATOR & HITBOX TUNER"
            title_surf = title_font.render(title_text, True, TEXT_COLOR)
            screen.blit(title_surf, (30, 22))

            if self.mode == "STATES":
                self.draw_states()
            elif self.mode == "ATTACKS":
                self.draw_attacks()

        # Draw Toast
        if self.toast_timer > 0:
            toast_surf = ui_font.render(self.toast_msg, True, (255, 255, 255))
            toast_box = pg.Rect(SCREEN_W // 2 - toast_surf.get_width() // 2 - 20, 10, toast_surf.get_width() + 40, 40)
            pg.draw.rect(screen, (40, 180, 80) if "Saved" in self.toast_msg or "Rolled" in self.toast_msg else (200, 50, 50), toast_box, border_radius=20)
            screen.blit(toast_surf, (toast_box.centerx - toast_surf.get_width() // 2, toast_box.centery - toast_surf.get_height() // 2))

    def check_frame_slider_change(self):
        if self.attack_frame_slider is None:
            return
        new_frame = int(self.attack_frame_slider.val)
        if new_frame != self.selected_attack_frame:
            self.save_current_frame_parameters()
            self.selected_attack_frame = new_frame
            self.load_frame_parameters()
            # Sync animation frame index to frame selector
            self.frame_index = float(new_frame)

    def update(self, dt: float):
        if self.toast_timer > 0:
            self.toast_timer -= dt
            
        if self.mode == "MENU":
            return

        state_name, total_frames = self.get_attack_state_and_frames() if self.mode == "ATTACKS" else (self.selected_state, 1)

        # Update animation frames
        if self.is_playing:
            if self.mode == "STATES":
                speed = self.anim_speed_slider.val * self.playback_speed_slider.val
                self.frame_index += speed
            elif self.mode == "ATTACKS":
                # Average speed for attack playback
                speed = 0.20 * self.playback_speed_slider.val
                self.frame_index = (self.frame_index + speed) % total_frames
                if self.attack_frame_slider is not None:
                    self.attack_frame_slider.val = int(self.frame_index)
                self.check_frame_slider_change()

    def handle_events(self):
        for event in pg.event.get():
            if event.type == pg.QUIT:
                self.running = False
                
            elif event.type == pg.KEYDOWN:
                if event.key == pg.K_SPACE:
                    self.is_playing = not self.is_playing

            elif event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
                # Handle Main Menu buttons
                if self.mode == "MENU":
                    for btn in self.menu_buttons:
                        btn.handle_event(event)
                    continue

                # Handle visualizer options checkboxes
                enh_rect = pg.Rect(800, 455, 220, 20)
                if enh_rect.collidepoint(event.pos):
                    self.enhanced_preview = not self.enhanced_preview
                    self.frame_index = 0.0
                
                flip_rect = pg.Rect(1050, 455, 220, 20)
                if flip_rect.collidepoint(event.pos):
                    self.flip_preview = not self.flip_preview

                # Mode-specific clicks
                if self.mode == "STATES":
                    # Check revision panel box
                    rev_box = pg.Rect(320, 405, 420, 215)
                    if rev_box.collidepoint(event.pos):
                        relative_y = event.pos[1] - rev_box.y - 10
                        clicked_idx = relative_y // 38
                        if 0 <= clicked_idx < len(self.backups[:5]):
                            self.selected_backup_index = clicked_idx

                elif self.mode == "ATTACKS":
                    # Check mutual exclusive role checkboxes
                    clicked_role = None
                    for idx, cb in enumerate(self.frame_role_checkboxes):
                        if cb.handle_event(event):
                            if cb.val: # If checked to True
                                clicked_role = idx
                                break
                    if clicked_role is not None:
                        for idx, cb in enumerate(self.frame_role_checkboxes):
                            if idx != clicked_role:
                                cb.val = False
                        # Save role changes immediately and reload slider availability
                        self.save_current_frame_parameters()
                        self.load_frame_parameters()

            # Dispatch events to components depending on mode
            if self.mode == "STATES":
                self.anim_speed_slider.handle_event(event)
                self.preview_scale_slider.handle_event(event)
                self.playback_speed_slider.handle_event(event)
                for cb in self.checkboxes:
                    cb.handle_event(event)
                for btn in self.state_buttons:
                    btn.handle_event(event)
                for btn in self.action_buttons:
                    btn.handle_event(event)

            elif self.mode == "ATTACKS":
                self.preview_scale_slider.handle_event(event)
                self.playback_speed_slider.handle_event(event)
                if self.attack_frame_slider is not None:
                    was_val = self.attack_frame_slider.val
                    self.attack_frame_slider.handle_event(event)
                    if self.attack_frame_slider.val != was_val or self.attack_frame_slider.dragging:
                        self.is_playing = False
                        self.frame_index = self.attack_frame_slider.val
                # Check frame slider change to load frame properties
                self.check_frame_slider_change()
                
                for sl in self.attack_sliders:
                    sl.handle_event(event)
                if self.attack_can_hit_multiple_cb is not None:
                    self.attack_can_hit_multiple_cb.handle_event(event)
                for sl in self.frame_sliders:
                    sl.handle_event(event)
                for btn in self.attack_buttons:
                    btn.handle_event(event)
                for btn in self.action_buttons:
                    btn.handle_event(event)

    def run(self):
        while self.running:
            dt = self.clock.tick(60) / 1000.0
            self.handle_events()
            self.update(dt)
            self.draw()
            pg.display.flip()

        # Save current config on quit
        if self.mode == "STATES":
            self.save_current_state_parameters()
        elif self.mode == "ATTACKS":
            self.save_current_attack_parameters()
            
        # Perform final write
        try:
            combined_data = {
                "states": self.config,
                "attacks": self.attack_config
            }
            with open(self.config_path, "w") as f:
                json.dump(combined_data, f, indent=2)
        except Exception as e:
            print(f"[ERROR] Failed to save config on exit: {e}")
            
        pg.quit()


if __name__ == "__main__":
    app = PlayerEditorApp()
    app.run()
