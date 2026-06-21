#!/usr/bin/env python3
"""
animation_speed_editor.py
Interactive editor for player animation speeds and per-frame speed curve tuning.
Allows frame-by-frame velocity adjustment, preview playback speed scaling,
and visual speed curve graphing.
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
pg.display.set_caption("Player Character: Animation Speed Curve Editor")

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

# Default configuration dictionary matching player.py _STATE_CONFIGS [ignoring loop detection]
DEFAULT_PLAYER_CONFIGS = {
    "DEATH": {
        "animation_speed": 0.12,
        "loops": False,
        "interruptible": False,
        "grants_invincibility": True,
        "locks_movement": True,
        "locks_input": True,
        "next_state": None,
        "frame_speeds": {}
    },
    "DEFEND": {
        "animation_speed": 0.18,
        "loops": False,
        "interruptible": False,
        "grants_invincibility": True,
        "locks_movement": True,
        "locks_input": False,
        "next_state": "IDLE",
        "frame_speeds": {}
    },
    "HURT": {
        "animation_speed": 0.20,
        "loops": False,
        "interruptible": False,
        "grants_invincibility": True,
        "locks_movement": True,
        "locks_input": True,
        "next_state": "IDLE",
        "frame_speeds": {
            "0": 0.30, "1": 0.30, "2": 0.30,
            "3": 0.10, "4": 0.10, "5": 0.20
        }
    },
    "ATTACK_THRUST": {
        "animation_speed": 0.24,
        "loops": False,
        "interruptible": False,
        "grants_invincibility": False,
        "locks_movement": True,
        "locks_input": False,
        "next_state": "IDLE",
        "frame_speeds": {
            "0": 0.12, "1": 0.12, "2": 0.40,
            "3": 0.28, "4": 0.28, "5": 0.20,
            "6": 0.20, "7": 0.15, "8": 0.15
        }
    },
    "ATTACK_SMASH": {
        "animation_speed": 0.24,
        "loops": False,
        "interruptible": False,
        "grants_invincibility": False,
        "locks_movement": True,
        "locks_input": False,
        "next_state": "IDLE",
        "frame_speeds": {
            "0": 0.12, "1": 0.12, "2": 0.35, "3": 0.35, "4": 0.35,
            "5": 0.15, "6": 0.15, "7": 0.32, "8": 0.32, "9": 0.32,
            "10": 0.22, "11": 0.22, "12": 0.22, "13": 0.18, "14": 0.18,
            "15": 0.14, "16": 0.14
        }
    },
    "ATTACK_POWER": {
        "animation_speed": 0.24,
        "loops": False,
        "interruptible": False,
        "grants_invincibility": False,
        "locks_movement": True,
        "locks_input": False,
        "next_state": "IDLE",
        "frame_speeds": {
            "0": 0.10, "1": 0.10, "2": 0.10, "3": 0.10, "4": 0.10, "5": 0.10,
            "6": 0.30, "7": 0.30, "8": 0.30, "9": 0.30, "10": 0.30,
            "11": 0.18, "12": 0.18, "13": 0.18, "14": 0.18,
            "15": 0.35, "16": 0.35, "17": 0.35, "18": 0.35, "19": 0.35,
            "20": 0.35, "21": 0.35, "22": 0.12
        }
    },
    "JUMP_UP": {
        "animation_speed": 0.20,
        "loops": True,
        "interruptible": True,
        "grants_invincibility": False,
        "locks_movement": False,
        "locks_input": False,
        "next_state": None,
        "frame_speeds": {}
    },
    "JUMP_DOWN": {
        "animation_speed": 0.22,
        "loops": True,
        "interruptible": True,
        "grants_invincibility": False,
        "locks_movement": False,
        "locks_input": False,
        "next_state": None,
        "frame_speeds": {}
    },
    "RUN": {
        "animation_speed": 0.22,
        "loops": True,
        "interruptible": True,
        "grants_invincibility": False,
        "locks_movement": False,
        "locks_input": False,
        "next_state": None,
        "frame_speeds": {}
    },
    "IDLE": {
        "animation_speed": 0.15,
        "loops": True,
        "interruptible": True,
        "grants_invincibility": False,
        "locks_movement": False,
        "locks_input": False,
        "next_state": None,
        "frame_speeds": {}
    },
    "SPECIAL_ATTACK": {
        "animation_speed": 0.20,
        "loops": False,
        "interruptible": False,
        "grants_invincibility": True,
        "locks_movement": True,
        "locks_input": True,
        "next_state": "IDLE",
        "frame_speeds": {
            "0": 0.14, "1": 0.14, "2": 0.14, "3": 0.14, "4": 0.14, "5": 0.14,
            "6": 0.18, "7": 0.18, "8": 0.18, "9": 0.18, "10": 0.18, "11": 0.18,
            "12": 0.18, "13": 0.18, "14": 0.25, "15": 0.25, "16": 0.25,
            "17": 0.30, "18": 0.30, "19": 0.30, "20": 0.30, "21": 0.30, "22": 0.30,
            "23": 0.30, "24": 0.30, "25": 0.30, "26": 0.30, "27": 0.16, "28": 0.16,
            "29": 0.16, "30": 0.16, "31": 0.16, "32": 0.16, "33": 0.16
        }
    },
    "TRANSFORM": {
        "animation_speed": 0.18,
        "loops": False,
        "interruptible": False,
        "grants_invincibility": True,
        "locks_movement": True,
        "locks_input": True,
        "next_state": "IDLE",
        "frame_speeds": {
            "0": 0.14, "1": 0.14, "2": 0.14, "3": 0.14, "4": 0.14, "5": 0.14,
            "6": 0.22, "7": 0.22, "8": 0.22, "9": 0.22, "10": 0.22, "11": 0.22,
            "12": 0.22, "13": 0.30, "14": 0.30, "15": 0.30, "16": 0.30, "17": 0.30,
            "18": 0.30, "19": 0.30, "20": 0.30, "21": 0.30, "22": 0.25, "23": 0.25,
            "24": 0.25, "25": 0.25, "26": 0.25, "27": 0.25, "28": 0.25, "29": 0.16,
            "30": 0.16, "31": 0.16, "32": 0.16, "33": 0.16, "34": 0.16
        }
    },
    "ROLL": {
        "animation_speed": 0.30,
        "loops": False,
        "interruptible": False,
        "grants_invincibility": True,
        "locks_movement": True,
        "locks_input": True,
        "next_state": "IDLE",
        "frame_speeds": {}
    },
    "DASH": {
        "animation_speed": 0.32,
        "loops": False,
        "interruptible": False,
        "grants_invincibility": False,
        "locks_movement": True,
        "locks_input": True,
        "next_state": "IDLE",
        "frame_speeds": {}
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
        color = (100, 100, 120) if self.enabled else (60, 60, 70)
        pg.draw.rect(surface, color, self.rect, border_radius=4)
        
        # Draw labels
        lbl = ui_font.render(self.label, True, TEXT_COLOR if self.enabled else TEXT_MUTED)
        surface.blit(lbl, (self.rect.x, self.rect.y - 22))

        val_display = round(self.val, 2) if self.is_float else int(self.val)
        val_str = self.format_str.format(val=val_display)
        val_lbl = value_font.render(val_str, True, ACCENT_CYAN if self.enabled else TEXT_MUTED)
        surface.blit(val_lbl, (self.rect.right - val_lbl.get_width(), self.rect.y - 22))

        # Handle
        hx, hy = self.get_handle_pos()
        h_color = ACCENT_CYAN if self.enabled else (80, 80, 90)
        pg.draw.circle(surface, h_color, (hx, hy), self.handle_r)
        if self.dragging:
            pg.draw.circle(surface, (255, 255, 255), (hx, hy), self.handle_r + 2, width=1)

    def handle_event(self, event: pg.event.Event):
        if not self.enabled:
            self.dragging = False
            return
            
        if event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
            hx, hy = self.get_handle_pos()
            m_pos = event.pos
            # Check collision with handle or bar
            if ((m_pos[0] - hx) ** 2 + (m_pos[1] - hy) ** 2) <= (self.handle_r + 4) ** 2 or self.rect.inflate(10, 16).collidepoint(m_pos):
                self.dragging = True
                self.update_val_from_mouse(m_pos[0])
                
        elif event.type == pg.MOUSEBUTTONUP and event.button == 1:
            self.dragging = False
            
        elif event.type == pg.MOUSEMOTION and self.dragging:
            self.update_val_from_mouse(event.pos[0])

    def update_val_from_mouse(self, mouse_x: int):
        rel_x = max(0, min(self.rect.width, mouse_x - self.rect.x))
        ratio = rel_x / self.rect.width
        raw_val = self.min_val + ratio * (self.max_val - self.min_val)
        if self.is_float:
            self.val = raw_val
        else:
            self.val = float(round(raw_val))


class Checkbox:
    def __init__(self, key: str, label: str, x: int, y: int, current_val: bool, enabled: bool = True):
        self.key = key
        self.label = label
        self.rect = pg.Rect(x, y, 20, 20)
        self.val = current_val
        self.enabled = enabled

    def draw(self, surface: pg.Surface):
        box_color = (40, 40, 55) if self.enabled else (25, 25, 30)
        pg.draw.rect(surface, box_color, self.rect, border_radius=4)
        pg.draw.rect(surface, BORDER_COLOR, self.rect, width=1, border_radius=4)
        
        if self.val:
            pg.draw.rect(surface, ACCENT_GREEN if self.enabled else TEXT_MUTED, pg.Rect(self.rect.x + 4, self.rect.y + 4, 12, 12), border_radius=2)
            
        lbl = ui_font.render(self.label, True, TEXT_COLOR if self.enabled else TEXT_MUTED)
        surface.blit(lbl, (self.rect.right + 10, self.rect.y + 2))

    def handle_event(self, event: pg.event.Event) -> bool:
        if not self.enabled:
            return False
        if event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self.val = not self.val
                return True
        return False


class Button:
    def __init__(self, text: str, x: int, y: int, w: int, h: int, callback, active: bool = False):
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


class AnimationSpeedEditor:
    def __init__(self):
        self.clock = pg.time.Clock()
        self.running = True
        
        self.config_dir = "game_data"
        self.config_path = os.path.join(self.config_dir, "player_config.json")
        self.config: Dict[str, Dict[str, Any]] = {}
        self.attack_config: Dict[str, Dict[str, Any]] = {}
        self.load_config()

        # UI Setup
        self.selected_state = "IDLE"
        self.enhanced_preview = False
        self.flip_preview = False
        self.is_playing = True
        self.frame_index = 0.0

        # Backups list tracking for rollback
        self.backups: List[str] = []
        self.selected_backup_index = -1
        self.scan_backups()

        # Left state buttons
        self.state_buttons: List[Button] = []
        self.rebuild_state_buttons()

        # State configurator sliders/checkboxes
        self.anim_speed_slider: Slider = Slider("animation_speed", "Base Animation Speed", 320, 110, 420, 0.05, 1.0, 0.2, is_float=True)
        self.frame_override_cb: Checkbox = Checkbox("override", "Enable Speed Override for Selected Frame", 320, 175, False)
        self.frame_speed_slider: Slider = Slider("frame_speed", "Frame Override Speed", 320, 240, 420, 0.01, 1.0, 0.2, is_float=True)
        self.timeline_slider: Slider = Slider("timeline", "Scrub Timeline Frame", 320, 310, 420, 0.0, 11.0, 0.0, is_float=False)

        # Action buttons
        self.action_buttons: List[Button] = []
        self.rebuild_action_buttons()

        # Visualizer options
        self.preview_scale = 3.5
        self.preview_scale_slider = Slider("scale", "Preview Scale", 800, 520, 200, 1.0, 6.0, self.preview_scale, is_float=True, format_str="{val}x")
        self.playback_rate = 1.0
        self.playback_rate_slider = Slider("rate", "Playback Rate", 1040, 520, 200, 0.2, 3.0, self.playback_rate, is_float=True, format_str="{val}x")

        # Animation Cache
        self.animation_cache = {"std": {}, "enh": {}}
        self.toast_msg = ""
        self.toast_timer = 0.0

        self.load_all_animations()
        self.select_state(self.selected_state)

    def load_config(self):
        self.config = {}
        self.attack_config = {}
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r") as f:
                    data = json.load(f)
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
            except Exception as e:
                print(f"[ERROR] Failed to load config: {e}")
                self.config = {k: v.copy() for k, v in DEFAULT_PLAYER_CONFIGS.items()}
        else:
            self.config = {k: v.copy() for k, v in DEFAULT_PLAYER_CONFIGS.items()}

    def scan_backups(self):
        self.backups = []
        if os.path.exists(self.config_dir):
            files = os.listdir(self.config_dir)
            for f in files:
                if f.startswith("player_config.backup_") and f.endswith(".json"):
                    self.backups.append(f)
            self.backups.sort(reverse=True)

    def rebuild_state_buttons(self):
        self.state_buttons = []
        x = 30
        y = 70
        for state in DEFAULT_PLAYER_CONFIGS.keys():
            btn = Button(state, x, y, 240, 36, lambda s=state: self.select_state(s), active=(state == self.selected_state))
            self.state_buttons.append(btn)
            y += 44

    def rebuild_action_buttons(self):
        self.action_buttons = [
            Button("SAVE CONFIG", 320, 640, 130, 40, self.request_save_config, active=True),
            Button("RESET TO DEFAULT", 465, 640, 160, 40, self.reset_defaults),
            Button("ROLLBACK", 940, 640, 130, 40, self.rollback_config)
        ]

    def select_state(self, state: str):
        self.save_current_parameters()
        self.selected_state = state
        self.frame_index = 0.0
        
        cfg = self.config[state]
        self.anim_speed_slider.val = cfg["animation_speed"]
        
        # Get frame count
        frame_count = self.get_current_frame_count()
        self.timeline_slider.max_val = float(frame_count - 1)
        self.timeline_slider.val = 0.0
        
        self.load_frame_parameters(0)
        self.rebuild_state_buttons()

    def get_current_frame_count(self) -> int:
        assets = STATE_ASSETS.get(self.selected_state)
        if not assets:
            return 1
        std_pat, std_count, enh_pat, enh_count = assets
        return enh_count if (self.enhanced_preview and enh_pat) else std_count

    def load_frame_parameters(self, frame_idx: int):
        cfg = self.config[self.selected_state]
        frame_speeds = cfg.setdefault("frame_speeds", {})
        
        frame_key = str(frame_idx)
        if frame_key in frame_speeds:
            self.frame_override_cb.val = True
            self.frame_speed_slider.val = float(frame_speeds[frame_key])
            self.frame_speed_slider.enabled = True
        else:
            self.frame_override_cb.val = False
            self.frame_speed_slider.val = cfg["animation_speed"]
            self.frame_speed_slider.enabled = False

    def save_current_parameters(self):
        state = self.selected_state
        cfg = self.config[state]
        cfg["animation_speed"] = self.anim_speed_slider.val
        
        frame_idx = int(self.timeline_slider.val)
        frame_key = str(frame_idx)
        frame_speeds = cfg.setdefault("frame_speeds", {})
        
        if self.frame_override_cb.val:
            frame_speeds[frame_key] = self.frame_speed_slider.val
        else:
            if frame_key in frame_speeds:
                del frame_speeds[frame_key]

    def reset_defaults(self):
        self.config[self.selected_state] = DEFAULT_PLAYER_CONFIGS[self.selected_state].copy()
        self.select_state(self.selected_state)
        self.show_toast("Reset to defaults")

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
                    frames.append(self._create_dummy_surf("Error"))
            else:
                frames.append(self._create_dummy_surf("Missing"))
        if not frames:
            frames.append(self._create_dummy_surf("Empty"))
        return frames

    def _create_dummy_surf(self, state_name: str) -> pg.Surface:
        surf = pg.Surface((96, 96), pg.SRCALPHA)
        pg.draw.rect(surf, (200, 0, 100), (24, 24, 48, 48), 2)
        txt = value_font.render(state_name, True, (200, 200, 200))
        surf.blit(txt, (48 - txt.get_width() // 2, 48 - txt.get_height() // 2))
        return surf

    def request_save_config(self):
        self.save_current_parameters()
        os.makedirs(self.config_dir, exist_ok=True)
        
        # 1. Backup old config first
        if os.path.exists(self.config_path):
            try:
                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_filename = f"player_config.backup_{ts}.json"
                backup_path = os.path.join(self.config_dir, backup_filename)
                shutil.copy2(self.config_path, backup_path)
                print(f"[INFO] Created dynamic config backup at {backup_path}")
            except Exception as e:
                print(f"[WARNING] Backup creation failed: {e}")

        # 2. Write atomic save
        try:
            temp_path = self.config_path + ".tmp"
            combined_data = {
                "states": self.config,
                "attacks": self.attack_config
            }
            with open(temp_path, "w") as f:
                json.dump(combined_data, f, indent=2)
            os.replace(temp_path, self.config_path)
            self.show_toast("Config Committed & Saved!")
            self.scan_backups()
            self.selected_backup_index = -1
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
                self.attack_config = {}
                
            # Fill missing entries
            for state, val in DEFAULT_PLAYER_CONFIGS.items():
                if state not in self.config:
                    self.config[state] = val.copy()
            
            self.select_state(self.selected_state)
            self.show_toast(f"Rolled back to {backup_file[21:36]}!")
        except Exception as e:
            self.show_toast("Rollback Failed!")
            print(f"[ERROR] Rollback failed: {e}")

    def draw(self):
        screen.fill(BG_COLOR)
        # Blueprint grid
        for x in range(0, SCREEN_W, 40):
            pg.draw.line(screen, (24, 24, 34), (x, 0), (x, SCREEN_H))
        for y in range(0, SCREEN_H, 40):
            pg.draw.line(screen, (24, 24, 34), (0, y), (SCREEN_W, y))

        # Title Header
        title_surf = title_font.render("PLAYER ANIMATION SPEED CURVE EDITOR", True, TEXT_COLOR)
        screen.blit(title_surf, (30, 22))

        # 1. Left Sidebar (State list)
        sidebar_rect = pg.Rect(20, 60, 260, 640)
        pg.draw.rect(screen, PANEL_BG, sidebar_rect, border_radius=8)
        pg.draw.rect(screen, BORDER_COLOR, sidebar_rect, width=1, border_radius=8)
        for btn in self.state_buttons:
            btn.draw(screen)

        # 2. Middle Configuration Panel
        param_panel = pg.Rect(300, 60, 460, 640)
        pg.draw.rect(screen, PANEL_BG, param_panel, border_radius=8)
        pg.draw.rect(screen, BORDER_COLOR, param_panel, width=1, border_radius=8)
        
        subtitle = title_font.render(f"CURVE: {self.selected_state}", True, ACCENT_CYAN)
        screen.blit(subtitle, (320, 75))

        self.anim_speed_slider.draw(screen)
        self.frame_override_cb.draw(screen)
        self.frame_speed_slider.draw(screen)
        self.timeline_slider.draw(screen)

        # Draw Speed Curve Graph
        graph_rect = pg.Rect(320, 360, 420, 180)
        pg.draw.rect(screen, PREVIEW_BG, graph_rect, border_radius=6)
        pg.draw.rect(screen, BORDER_COLOR, graph_rect, width=1, border_radius=6)

        # Render graph elements
        frames_count = self.get_current_frame_count()
        cfg = self.config[self.selected_state]
        base_speed = self.anim_speed_slider.val
        frame_speeds = cfg.setdefault("frame_speeds", {})

        # Grid lines
        for val in [0.25, 0.5, 0.75, 1.0]:
            y_val = graph_rect.bottom - int(val * 140)
            pg.draw.line(screen, (32, 32, 44), (graph_rect.x, y_val), (graph_rect.right, y_val))
            lbl_val = help_font.render(str(val), True, TEXT_MUTED)
            screen.blit(lbl_val, (graph_rect.x + 5, y_val - 12))

        # Bars/Points plotting
        bar_w = max(4, int(280 / frames_count))
        gap = max(2, int(80 / frames_count))
        total_w = frames_count * bar_w + (frames_count - 1) * gap
        start_x = graph_rect.centerx - total_w // 2

        active_frame = int(self.frame_index) % frames_count

        for i in range(frames_count):
            frame_key = str(i)
            has_override = frame_key in frame_speeds
            speed = float(frame_speeds[frame_key]) if has_override else base_speed
            
            # Map speed value to graph Y space
            bar_h = int(speed * 140)
            bx = start_x + i * (bar_w + gap)
            by = graph_rect.bottom - bar_h

            bar_rect = pg.Rect(bx, by, bar_w, bar_h)
            
            # Colors
            if i == active_frame:
                color = ACCENT_CYAN
                # Highlight active frame bar
                pg.draw.rect(screen, (255, 255, 255), bar_rect.inflate(2, 2), width=1, border_radius=2)
            elif has_override:
                color = ACCENT_GREEN
            else:
                color = ACCENT_BLUE

            pg.draw.rect(screen, color, bar_rect, border_radius=2)

            # Label frame index
            if frames_count <= 20 or i % 5 == 0 or i == active_frame:
                lbl_fr = help_font.render(str(i), True, TEXT_COLOR if i == active_frame else TEXT_MUTED)
                screen.blit(lbl_fr, (bx + bar_w//2 - lbl_fr.get_width()//2, graph_rect.bottom + 4))

        # Graph legend
        pg.draw.rect(screen, ACCENT_BLUE, (320, 555, 12, 12), border_radius=2)
        lbl_std = help_font.render("Base Speed", True, TEXT_COLOR)
        screen.blit(lbl_std, (338, 553))

        pg.draw.rect(screen, ACCENT_GREEN, (450, 555, 12, 12), border_radius=2)
        lbl_ovr = help_font.render("Override Speed", True, TEXT_COLOR)
        screen.blit(lbl_ovr, (468, 553))

        pg.draw.rect(screen, ACCENT_CYAN, (590, 555, 12, 12), border_radius=2)
        lbl_act = help_font.render("Selected Frame", True, TEXT_COLOR)
        screen.blit(lbl_act, (608, 553))

        # Commits & Rollback lists
        div_rect = pg.Rect(310, 580, 440, 1)
        pg.draw.rect(screen, BORDER_COLOR, div_rect)
        
        # Display revision history
        rev_label = help_font.render(f"Revisions: {len(self.backups)} backups available", True, TEXT_MUTED)
        screen.blit(rev_label, (320, 595))

        # Draw Action buttons
        for btn in self.action_buttons:
            btn.draw(screen)

        # 3. Right Visualizer Panel
        preview_panel = pg.Rect(780, 60, 480, 640)
        pg.draw.rect(screen, PANEL_BG, preview_panel, border_radius=8)
        pg.draw.rect(screen, BORDER_COLOR, preview_panel, width=1, border_radius=8)

        preview_title = title_font.render("ANIMATION PREVIEW", True, ACCENT_GREEN)
        screen.blit(preview_title, (800, 75))

        # Playback Viewport
        view_box = pg.Rect(800, 115, 440, 320)
        pg.draw.rect(screen, PREVIEW_BG, view_box, border_radius=6)
        pg.draw.rect(screen, BORDER_COLOR, view_box, width=1, border_radius=6)

        cache_key = "enh" if self.enhanced_preview else "std"
        frames = self.animation_cache[cache_key].get(self.selected_state, [])
        
        if frames:
            frame_idx = int(self.frame_index) % len(frames)
            active_surf = frames[frame_idx]
            
            if self.flip_preview:
                active_surf = pg.transform.flip(active_surf, True, False)
                
            self.preview_scale = self.preview_scale_slider.val
            new_w = int(active_surf.get_width() * self.preview_scale)
            new_h = int(active_surf.get_height() * self.preview_scale)
            scaled_surf = pg.transform.scale(active_surf, (new_w, new_h))
            
            surf_rect = scaled_surf.get_rect(center=view_box.center)
            
            screen.set_clip(view_box)
            screen.blit(scaled_surf, surf_rect)
            screen.set_clip(None)

            txt_fr = value_font.render(f"Frame: {frame_idx + 1} / {len(frames)}", True, TEXT_MUTED)
            screen.blit(txt_fr, (view_box.x + 10, view_box.bottom - 22))

            # Render speed tooltip
            frame_key = str(frame_idx)
            spd = float(frame_speeds[frame_key]) if frame_key in frame_speeds else base_speed
            txt_spd = value_font.render(f"Frame Speed: {spd:.2f}", True, ACCENT_GREEN if frame_key in frame_speeds else ACCENT_BLUE)
            screen.blit(txt_spd, (view_box.right - txt_spd.get_width() - 10, view_box.bottom - 22))

        # Checkboxes below viewport
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
        self.playback_rate_slider.draw(screen)

        # Help Guide Panel
        help_rect = pg.Rect(800, 570, 440, 115)
        pg.draw.rect(screen, PREVIEW_BG, help_rect, border_radius=6)
        pg.draw.rect(screen, BORDER_COLOR, help_rect, width=1, border_radius=6)
        
        help_lines = [
            "Use the scrub timeline slider to focus on a frame.",
            "Toggle speed override and set a custom value for that frame.",
            "Overridden frames will render in GREEN on the curve graph.",
            "Press [SPACE] to play/pause the preview animation loop."
        ]
        y_hl = help_rect.y + 8
        for hl in help_lines:
            txt_hl = help_font.render(hl, True, TEXT_MUTED)
            screen.blit(txt_hl, (help_rect.x + 15, y_hl))
            y_hl += 25

        # Draw Toast
        if self.toast_timer > 0:
            toast_surf = ui_font.render(self.toast_msg, True, (255, 255, 255))
            toast_box = pg.Rect(SCREEN_W // 2 - toast_surf.get_width() // 2 - 20, 10, toast_surf.get_width() + 40, 40)
            pg.draw.rect(screen, (40, 180, 80) if "Saved" in self.toast_msg or "Rolled" in self.toast_msg else (200, 50, 50), toast_box, border_radius=20)
            screen.blit(toast_surf, (toast_box.centerx - toast_surf.get_width() // 2, toast_box.centery - toast_surf.get_height() // 2))

    def update_timeline_selection(self):
        new_frame = int(self.timeline_slider.val)
        self.save_current_parameters()
        self.load_frame_parameters(new_frame)
        self.frame_index = float(new_frame)

    def update(self, dt: float):
        if self.toast_timer > 0:
            self.toast_timer -= dt

        frames_count = self.get_current_frame_count()

        if self.is_playing:
            # Get current frame's configured speed
            frame_idx = int(self.frame_index) % frames_count
            cfg = self.config[self.selected_state]
            frame_speeds = cfg.setdefault("frame_speeds", {})
            frame_key = str(frame_idx)
            
            speed = float(frame_speeds[frame_key]) if frame_key in frame_speeds else self.anim_speed_slider.val
            # Apply playback rate modifier
            self.frame_index = (self.frame_index + speed * self.playback_rate_slider.val) % frames_count
            
            # Sync timeline slider
            self.timeline_slider.val = float(int(self.frame_index))
            self.load_frame_parameters(int(self.frame_index))

    def handle_events(self):
        for event in pg.event.get():
            if event.type == pg.QUIT:
                self.running = False
                
            elif event.type == pg.KEYDOWN:
                if event.key == pg.K_SPACE:
                    self.is_playing = not self.is_playing

            elif event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
                # Enhanced Form Toggle
                enh_rect = pg.Rect(800, 455, 220, 20)
                if enh_rect.collidepoint(event.pos):
                    self.enhanced_preview = not self.enhanced_preview
                    self.frame_index = 0.0
                    self.select_state(self.selected_state)
                
                # Flip Facing Toggle
                flip_rect = pg.Rect(1050, 455, 220, 20)
                if flip_rect.collidepoint(event.pos):
                    self.flip_preview = not self.flip_preview

                # Graph click interaction to jump to frame
                graph_rect = pg.Rect(320, 360, 420, 180)
                if graph_rect.collidepoint(event.pos):
                    frames_count = self.get_current_frame_count()
                    bar_w = max(4, int(280 / frames_count))
                    gap = max(2, int(80 / frames_count))
                    total_w = frames_count * bar_w + (frames_count - 1) * gap
                    start_x = graph_rect.centerx - total_w // 2
                    
                    clicked_x = event.pos[0] - start_x
                    if clicked_x >= 0:
                        clicked_frame = clicked_x // (bar_w + gap)
                        if 0 <= clicked_frame < frames_count:
                            self.is_playing = False
                            self.timeline_slider.val = float(clicked_frame)
                            self.update_timeline_selection()

            # Dispatch events to active widgets
            self.anim_speed_slider.handle_event(event)
            self.preview_scale_slider.handle_event(event)
            self.playback_rate_slider.handle_event(event)

            # Timeline / Frame Scrubbing
            was_scrub = self.timeline_slider.val
            self.timeline_slider.handle_event(event)
            if self.timeline_slider.val != was_scrub or self.timeline_slider.dragging:
                self.is_playing = False
                self.update_timeline_selection()

            # Override checkbox
            if self.frame_override_cb.handle_event(event):
                self.frame_speed_slider.enabled = self.frame_override_cb.val
                # If just enabled, set override to base speed by default
                if self.frame_override_cb.val and self.frame_speed_slider.val == self.anim_speed_slider.val:
                    self.frame_speed_slider.val = self.anim_speed_slider.val

            # Frame speed override slider
            if self.frame_speed_slider.enabled:
                self.frame_speed_slider.handle_event(event)

            # Lists & action buttons
            for btn in self.state_buttons:
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

        self.save_current_parameters()
        
        # Final write
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
    app = AnimationSpeedEditor()
    app.run()
