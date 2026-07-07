#!/usr/bin/env python3
"""
boss_editor.py
An interactive, dark-themed configuration editor, animation visualizer,
and AI behavior simulator for all bosses registered in the game's BossManager.
"""

import os
import sys
import json
import random
import pygame as pg
from typing import Any, Optional, Dict, List, Type

# Add path mapping to allow importing from src package
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from src.game.debug.telemetry_log_parser import TelemetryLogParser
from src.game.boss.difficulty_manager import DifficultyManager
from src.game.editor.preview_scaler import PreviewScaler
from src.game.entities.boss_manager import BossManager
from src.game.entities.enemy import Enemy
from src.game.entities.skeleton import Skeleton
from src.game.entities.fire_wizard import FireWizard
from src.game.entities.green_monster import GreenMonster
from v3x_zulfiqar_gideon import Actor

# Initialize Pygame and font systems
pg.init()
pg.font.init()

SCREEN_W, SCREEN_H = 1280, 720
screen = pg.display.set_mode((SCREEN_W, SCREEN_H))
pg.display.set_caption("Boss Configuration Editor & Simulator Plugin")

# Load Fonts
try:
    title_font = pg.font.Font("assets/graphics/Darinia/Darinia.ttf", 26)
    ui_font = pg.font.Font("assets/graphics/Darinia/Darinia.ttf", 15)
    value_font = pg.font.Font("assets/graphics/Darinia/Darinia.ttf", 13)
    help_font = pg.font.SysFont("Consolas", 14)
except Exception:
    title_font = pg.font.SysFont("Arial", 24, bold=True)
    ui_font = pg.font.SysFont("Arial", 15, bold=True)
    value_font = pg.font.SysFont("Arial", 13)
    help_font = pg.font.SysFont("monospace", 12)

# Theme Palette (Premium Dark Mode with Cyan/Purple accents)
BG_COLOR = (18, 18, 24)
PANEL_BG = (28, 28, 38)
PREVIEW_BG = (12, 12, 16)
TEXT_COLOR = (240, 240, 245)
ACCENT_CYAN = (0, 229, 255)
ACCENT_PURPLE = (170, 0, 255)
ACCENT_BLUE = (0, 145, 234)
TEXT_MUTED = (140, 140, 160)
BORDER_COLOR = (48, 48, 64)

class Slider:
    def __init__(self, key: str, label: str, x: int, y: int, w: int, min_val: float, max_val: float, current_val: float, is_float: bool = False, format_str: str = "{val}"):
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

    def get_handle_pos(self) -> tuple[int, int]:
        if self.max_val == self.min_val:
            ratio = 0.0
        else:
            ratio = (self.val - self.min_val) / (self.max_val - self.min_val)
        return int(self.rect.x + ratio * self.rect.width), self.rect.centery

    def draw(self, surface: pg.Surface):
        if self.key == "spidey_sense":
            if self.val <= 0.05:
                val_display = "Off"
            elif self.val <= 0.2:
                val_display = "Weak"
            elif self.val <= 0.5:
                val_display = "Standard"
            elif self.val <= 0.8:
                val_display = "Strong"
            else:
                val_display = "God Mode"
        else:
            val_display = self.format_str.format(val=round(self.val, 2) if self.is_float else int(self.val))
        txt_label = ui_font.render(self.label, True, TEXT_COLOR)
        txt_val = value_font.render(val_display, True, ACCENT_CYAN)
        
        surface.blit(txt_label, (self.rect.x, self.rect.y - 20))
        surface.blit(txt_val, (self.rect.right - txt_val.get_width(), self.rect.y - 20))

        # Slider track
        pg.draw.rect(surface, (40, 40, 55), self.rect, border_radius=4)
        
        # Fill track
        hx, hy = self.get_handle_pos()
        fill_rect = pg.Rect(self.rect.x, self.rect.y, hx - self.rect.x, self.rect.height)
        pg.draw.rect(surface, ACCENT_BLUE, fill_rect, border_radius=4)

        # Handle circle
        pg.draw.circle(surface, (255, 255, 255), (hx, hy), self.handle_r)
        if self.dragging:
            pg.draw.circle(surface, ACCENT_CYAN, (hx, hy), self.handle_r - 2)

    def handle_event(self, event: pg.event.Event):
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


BOSS_SCHEMAS = {
    "wizard": {
        "class": FireWizard,
        "config_file": "game_data/boss_wizard_config.json",
        "defaults": {
            "max_mana": 100.0,
            "spell_mana_cost": 35.0,
            "stagnant_duration": 3.0,
            "teleport_dist_min": 380,
            "teleport_dist_max": 450,
            "mana_recharge_rate": 50.0,
            "chase_delay_duration": 0.8,
            "attack_cooldown_min": 1.2,
            "attack_cooldown_max": 2.0,
            "spidey_sense": 0.0,
            "attack_hitbox_width": 55,
            "attack_hitbox_height": 45
        },
        "sliders": [
            ("max_mana", "Max Mana Pool", 50, 200, True, "{val} mp"),
            ("spell_mana_cost", "Spell Cost", 10, 100, True, "{val} mp"),
            ("stagnant_duration", "Stagnant/Exhausted Time", 0.5, 6.0, True, "{val} sec"),
            ("teleport_dist_min", "Teleport Min Dist", 100, 600, False, "{val} px"),
            ("teleport_dist_max", "Teleport Max Dist", 400, 1000, False, "{val} px"),
            ("mana_recharge_rate", "Mana Recharge Rate", 10, 100, True, "{val}/sec"),
            ("chase_delay_duration", "Chase Delay Window", 0.0, 3.0, True, "{val} sec"),
            ("attack_cooldown_min", "Min Spell Cooldown", 0.5, 4.0, True, "{val} sec"),
            ("attack_cooldown_max", "Max Spell Cooldown", 1.0, 6.0, True, "{val} sec"),
            ("spidey_sense", "Spidey Sense / Counter Dodge", 0.0, 1.0, True, "{val}"),
            ("attack_hitbox_width", "Attack Hitbox Width", 10, 300, False, "{val} px"),
            ("attack_hitbox_height", "Attack Hitbox Height", 10, 300, False, "{val} px")
        ],
        "simulation": {
            "player_x": 100,
            "boss_x": 400,
        }
    },
    "skeleton": {
        "class": Skeleton,
        "config_file": "game_data/boss_skeleton_config.json",
        "defaults": {
            "max_health": 150.0,
            "speed": 3.2,
            "damage_scale": 3.0,
            "knockback_scale": 1.8,
            "detection_range": 3000,
            "attack_range": 80,
            "vertical_tolerance": 500,
            "attack_hitbox_width": 60,
            "attack_hitbox_height": 80
        },
        "sliders": [
            ("max_health", "Max Health", 50, 300, True, "{val} hp"),
            ("speed", "Movement Speed", 1.0, 8.0, True, "{val} px"),
            ("damage_scale", "Damage Scale multiplier", 0.5, 5.0, True, "{val}x"),
            ("knockback_scale", "Knockback multiplier", 0.5, 4.0, True, "{val}x"),
            ("detection_range", "AI Detection Range", 200, 4000, False, "{val} px"),
            ("attack_range", "AI Attack Range", 20, 300, False, "{val} px"),
            ("vertical_tolerance", "AI Vertical Tolerance", 50, 1000, False, "{val} px"),
            ("attack_hitbox_width", "Attack Hitbox Width", 10, 300, False, "{val} px"),
            ("attack_hitbox_height", "Attack Hitbox Height", 10, 300, False, "{val} px")
        ],
        "simulation": {
            "player_x": 100,
            "boss_x": 500,
        }
    },
    "skeleton_minion": {
        "class": Skeleton,
        "config_file": "game_data/enemy_skeleton_minion_config.json",
        "defaults": {
            "max_health": 30.0,
            "speed": 2.5,
            "damage_scale": 1.0,
            "knockback_scale": 1.0,
            "detection_range": 1000,
            "attack_range": 60,
            "vertical_tolerance": 100,
            "attack_hitbox_width": 60,
            "attack_hitbox_height": 80
        },
        "sliders": [
            ("max_health", "Max Health", 10, 100, True, "{val} hp"),
            ("speed", "Movement Speed", 1.0, 6.0, True, "{val} px"),
            ("damage_scale", "Damage Scale multiplier", 0.2, 3.0, True, "{val}x"),
            ("knockback_scale", "Knockback multiplier", 0.2, 3.0, True, "{val}x"),
            ("detection_range", "AI Detection Range", 100, 2000, False, "{val} px"),
            ("attack_range", "AI Attack Range", 10, 200, False, "{val} px"),
            ("vertical_tolerance", "AI Vertical Tolerance", 20, 500, False, "{val} px"),
            ("attack_hitbox_width", "Attack Hitbox Width", 10, 200, False, "{val} px"),
            ("attack_hitbox_height", "Attack Hitbox Height", 10, 200, False, "{val} px")
        ],
        "simulation": {
            "player_x": 100,
            "boss_x": 500,
        }
    },
    "goblin": {
        "class": Skeleton,
        "config_file": "game_data/enemy_goblin_config.json",
        "defaults": {
            "max_health": 30.0,
            "speed": 2.5,
            "damage_scale": 1.0,
            "knockback_scale": 1.0,
            "detection_range": 1000,
            "attack_range": 60,
            "vertical_tolerance": 100,
            "attack_hitbox_width": 60,
            "attack_hitbox_height": 80
        },
        "sliders": [
            ("max_health", "Max Health", 10, 100, True, "{val} hp"),
            ("speed", "Movement Speed", 1.0, 6.0, True, "{val} px"),
            ("damage_scale", "Damage Scale multiplier", 0.2, 3.0, True, "{val}x"),
            ("knockback_scale", "Knockback multiplier", 0.2, 3.0, True, "{val}x"),
            ("detection_range", "AI Detection Range", 100, 2000, False, "{val} px"),
            ("attack_range", "AI Attack Range", 10, 200, False, "{val} px"),
            ("vertical_tolerance", "AI Vertical Tolerance", 20, 500, False, "{val} px"),
            ("attack_hitbox_width", "Attack Hitbox Width", 10, 200, False, "{val} px"),
            ("attack_hitbox_height", "Attack Hitbox Height", 10, 200, False, "{val} px")
        ],
        "simulation": {
            "player_x": 100,
            "boss_x": 500,
        }
    },
    "green_monster": {
        "class": GreenMonster,
        "config_file": "game_data/enemy_green_monster_config.json",
        "defaults": {
            "max_health": 40.0,
            "speed": 2.2,
            "damage_scale": 1.2,
            "knockback_scale": 1.2,
            "detection_range": 900,
            "attack_range": 110,
            "vertical_tolerance": 260,
            "attack_hitbox_width": 90,
            "attack_hitbox_height": 70,
            "max_mana": 100.0,
            "spell_mana_cost": 35.0,
            "stagnant_duration": 3.0,
            "teleport_dist_min": 380,
            "teleport_dist_max": 450,
            "mana_recharge_rate": 50.0,
            "chase_delay_duration": 0.8,
            "attack_cooldown_min": 1.0,
            "attack_cooldown_max": 1.8,
            "spidey_sense": 0.0
        },
        "sliders": [
            ("max_health", "Max Health", 10, 150, True, "{val} hp"),
            ("speed", "Movement Speed", 1.0, 6.0, True, "{val} px"),
            ("damage_scale", "Damage Scale multiplier", 0.2, 3.0, True, "{val}x"),
            ("knockback_scale", "Knockback multiplier", 0.2, 3.0, True, "{val}x"),
            ("detection_range", "AI Detection Range", 100, 2000, False, "{val} px"),
            ("attack_range", "Melee Attack Range", 10, 250, False, "{val} px"),
            ("vertical_tolerance", "AI Vertical Tolerance", 20, 500, False, "{val} px"),
            ("attack_hitbox_width", "Attack Hitbox Width", 10, 200, False, "{val} px"),
            ("attack_hitbox_height", "Attack Hitbox Height", 10, 200, False, "{val} px"),
            ("max_mana", "Max Mana Pool", 50, 200, True, "{val} mp"),
            ("spell_mana_cost", "Spell Cost", 10, 100, True, "{val} mp"),
            ("stagnant_duration", "Stagnant/Exhausted Time", 0.5, 6.0, True, "{val} sec"),
            ("teleport_dist_min", "Teleport Min Dist", 100, 600, False, "{val} px"),
            ("teleport_dist_max", "Teleport Max Dist", 400, 1000, False, "{val} px"),
            ("mana_recharge_rate", "Mana Recharge Rate", 10, 100, True, "{val}/sec"),
            ("chase_delay_duration", "Chase Delay Window", 0.0, 3.0, True, "{val} sec"),
            ("attack_cooldown_min", "Min Spell Cooldown", 0.5, 4.0, True, "{val} sec"),
            ("attack_cooldown_max", "Max Spell Cooldown", 1.0, 6.0, True, "{val} sec"),
            ("spidey_sense", "Spidey Sense / Counter Dodge", 0.0, 1.0, True, "{val}")
        ],
        "simulation": {
            "player_x": 100,
            "boss_x": 500,
        }
    },
    "skeleton_zombie": {
        "class": Skeleton,
        "config_file": "game_data/enemy_skeleton_zombie_config.json",
        "defaults": {
            "max_health": 35.0,
            "speed": 2.0,
            "damage_scale": 1.0,
            "knockback_scale": 1.0,
            "detection_range": 1000,
            "attack_range": 60,
            "vertical_tolerance": 100,
            "attack_hitbox_width": 60,
            "attack_hitbox_height": 80
        },
        "sliders": [
            ("max_health", "Max Health", 10, 120, True, "{val} hp"),
            ("speed", "Movement Speed", 1.0, 6.0, True, "{val} px"),
            ("damage_scale", "Damage Scale multiplier", 0.2, 3.0, True, "{val}x"),
            ("knockback_scale", "Knockback multiplier", 0.2, 3.0, True, "{val}x"),
            ("detection_range", "AI Detection Range", 100, 2000, False, "{val} px"),
            ("attack_range", "AI Attack Range", 10, 200, False, "{val} px"),
            ("vertical_tolerance", "AI Vertical Tolerance", 20, 500, False, "{val} px"),
            ("attack_hitbox_width", "Attack Hitbox Width", 10, 200, False, "{val} px"),
            ("attack_hitbox_height", "Attack Hitbox Height", 10, 200, False, "{val} px")
        ],
        "simulation": {
            "player_x": 100,
            "boss_x": 500,
        }
    },
    "blood_zombie": {
        "class": Skeleton,
        "config_file": "game_data/enemy_blood_zombie_config.json",
        "defaults": {
            "max_health": 50.0,
            "speed": 2.2,
            "damage_scale": 1.2,
            "knockback_scale": 1.2,
            "detection_range": 1200,
            "attack_range": 65,
            "vertical_tolerance": 100,
            "attack_hitbox_width": 60,
            "attack_hitbox_height": 80
        },
        "sliders": [
            ("max_health", "Max Health", 10, 180, True, "{val} hp"),
            ("speed", "Movement Speed", 1.0, 6.0, True, "{val} px"),
            ("damage_scale", "Damage Scale multiplier", 0.2, 3.0, True, "{val}x"),
            ("knockback_scale", "Knockback multiplier", 0.2, 3.0, True, "{val}x"),
            ("detection_range", "AI Detection Range", 100, 2000, False, "{val} px"),
            ("attack_range", "AI Attack Range", 10, 200, False, "{val} px"),
            ("vertical_tolerance", "AI Vertical Tolerance", 20, 500, False, "{val} px"),
            ("attack_hitbox_width", "Attack Hitbox Width", 10, 200, False, "{val} px"),
            ("attack_hitbox_height", "Attack Hitbox Height", 10, 200, False, "{val} px")
        ],
        "simulation": {
            "player_x": 100,
            "boss_x": 500,
        }
    },
    "bat": {
        "class": Enemy,
        "config_file": "game_data/enemy_bat_config.json",
        "defaults": {
            "speed": 250.0,
            "scale": 1.0
        },
        "sliders": [
            ("speed", "Movement Speed", 50, 600, True, "{val} px/s"),
            ("scale", "Scale Factor", 0.5, 3.0, True, "{val}x")
        ],
        "simulation": {
            "player_x": 100,
            "boss_x": 600,
        }
    }
}


class BossEditorApp:
    def __init__(self):
        self.clock = pg.time.Clock()
        self.running = True
        
        # 1. Populate all supported bosses/enemies
        self.bosses = {}
        for key, schema in BOSS_SCHEMAS.items():
            self.bosses[key] = {
                "class": schema["class"],
                "schema": schema
            }
        
        self.boss_keys = list(self.bosses.keys())
        self.selected_boss = self.boss_keys[0]
        
        # Load all configurations
        self.boss_configs = {}
        for bkey in self.boss_keys:
            self.load_boss_config(bkey)
            
        # 2. Build Selection Grid Buttons (3 columns)
        self.tab_buttons = []
        cols = 3
        tab_w = 340 // cols
        for i, bkey in enumerate(self.boss_keys):
            col_idx = i % cols
            row_idx = i // cols
            bx = 30 + col_idx * tab_w
            by = 75 + row_idx * 38
            btn = Button(bkey.replace("_", " ").upper(), bx, by, tab_w - 5, 32, lambda k=bkey: self.select_boss(k))
            self.tab_buttons.append(btn)
            
        self.tab_buttons[0].active = True
        
        self.sliders: Dict[str, Slider] = {}
        self.build_sliders()

        # Action Buttons
        self.action_buttons = [
            Button("SAVE CONFIG", 40, 650, 150, 40, self.request_save_config, active=True),
            Button("RESET DEFAULT", 210, 650, 150, 40, self.reset_defaults),
        ]

        self.confirming_save = False
        self.confirming_sim_reset = False
        self.toast_message = ""
        self.toast_timer = 0.0

        # Load Animation Sprites for all detected bosses
        self.animations: Dict[str, Dict[str, List[pg.Surface]]] = {}
        self.load_all_animations()

        # Animation Playback State
        self.frame_index = 0.0
        self.play_speed = 1.0
        self.is_playing = True
        self.preview_scale = 1.0
        self.current_state = "IDLE"

        # Interactive Mode State
        # "REVIEW" - Loop single animation.
        # "SIMULATION" - Run boss AI loop against a mock player.
        # "ANALYTICS" - View telemetry dashboards & auto-tune difficulty.
        self.mode = "REVIEW"
        self.init_simulation_state()

        # Review Control UI Elements
        self.review_buttons = [
            Button("IDLE", 450, 560, 80, 35, lambda: self.set_review_state("IDLE")),
            Button("CHASE", 540, 560, 80, 35, lambda: self.set_review_state("CHASE")),
            Button("ATTACK", 630, 560, 80, 35, lambda: self.set_review_state("ATTACK")),
            Button("HURT", 720, 560, 80, 35, lambda: self.set_review_state("HURT")),
            Button("DEATH", 810, 560, 80, 35, lambda: self.set_review_state("DEATH")),
        ]
        self.update_review_buttons()

        # Mode Buttons
        self.mode_buttons = [
            Button("ANIMATION LOOP", 430, 500, 220, 40, lambda: self.set_mode("REVIEW")),
            Button("AI FLOW SIMULATION", 670, 500, 220, 40, lambda: self.set_mode("SIMULATION")),
            Button("DIFFICULTY TUNER", 910, 500, 220, 40, lambda: self.set_mode("ANALYTICS")),
        ]
        self.update_mode_buttons()

        self.restart_sim_btn = Button("RESTART SIMULATION", 450, 560, 200, 35, self.request_sim_reset)

        # Visualizer Play/Pause & Scale Sliders
        self.preview_scale_slider = Slider("scale", "Preview Scale", 920, 610, 300, 1.0, 6.0, 3.0, is_float=True, format_str="{val}x")
        self.playback_speed_slider = Slider("speed", "Playback Speed", 920, 670, 300, 0.2, 3.0, self.play_speed, is_float=True, format_str="{val}x")

        # Telemetry & Difficulty scaling system properties
        self.log_parser = TelemetryLogParser()
        self.difficulty_manager = DifficultyManager()
        self.recent_sessions_analytics = {}
        self.latest_session_name = "None"
        self.parsed_files_count = 0

        # Auto-Fit Scaling System (ON by default)
        self.auto_fit_enabled = True
        self.autofit_btn = Button("AUTO-FIT: ON", 920, 560, 145, 30, self.toggle_autofit, active=True)
        self.apply_fit_btn = Button("APPLY TO SLIDER", 1075, 560, 145, 30, self.apply_fit_to_slider)

        # Presets Slot Path & Active State
        self.presets_path = "game_data/wizard_presets.json"
        self.active_preset_slot = 1
        self.presets_data = {}
        self.load_presets()

        # Analytics Dashboard buttons
        self.analytics_buttons = [
            Button("REFRESH LOGS", 430, 560, 130, 35, self.refresh_analytics),
            Button("[ < LOWER ]", 570, 640, 100, 42, lambda: self.adjust_difficulty(-1)),
            Button("[ HIGHER > ]", 680, 640, 100, 42, lambda: self.adjust_difficulty(1)),
            Button("[ AUTO-TUNING ]", 790, 640, 140, 42, self.apply_recommended_difficulty),
            Button("PRESET 1", 790, 560, 95, 35, lambda: self.apply_preset_slot(1)),
            Button("PRESET 2", 895, 560, 95, 35, lambda: self.apply_preset_slot(2)),
            Button("PRESET 3", 1000, 560, 95, 35, lambda: self.apply_preset_slot(3)),
            Button("SAVE PRESET", 1105, 560, 120, 35, self.save_to_active_preset),
        ]
        self.update_preset_buttons()

        # Initial fetch of telemetry logs
        self.refresh_analytics()

    def select_boss(self, boss_key: str):
        self.selected_boss = boss_key
        for btn in self.tab_buttons:
            btn.active = (btn.text.lower() == boss_key)
        self.build_sliders()
        self.frame_index = 0.0
        self.init_simulation_state()
        
        # Load preset path for wizards/green monster
        if self.selected_boss == "wizard":
            self.presets_path = "game_data/wizard_presets.json"
            self.load_presets()
            self.update_preset_buttons()
        elif self.selected_boss == "green_monster":
            self.presets_path = "game_data/green_monster_presets.json"
            self.load_presets()
            self.update_preset_buttons()
        
    def load_boss_config(self, boss_key: str):
        schema = self.bosses[boss_key]["schema"]
        config_path = schema["config_file"]
        defaults = schema["defaults"]
        
        config = {}
        if os.path.exists(config_path):
            try:
                with open(config_path, "r") as f:
                    config = json.load(f)
                    for k, v in defaults.items():
                        if k not in config:
                            config[k] = v
            except Exception:
                config = defaults.copy()
        else:
            config = defaults.copy()
        self.boss_configs[boss_key] = config

    def build_sliders(self):
        self.sliders = {}
        schema = self.bosses[self.selected_boss]["schema"]
        config = self.boss_configs[self.selected_boss]
        
        num_keys = len(self.boss_keys)
        rows = (num_keys + 2) // 3
        grid_bottom = 75 + rows * 38
        
        y_pos = grid_bottom + 10
        spacing = 42 if num_keys > 3 else 48
        
        for slider_key, label, min_val, max_val, is_float, format_str in schema["sliders"]:
            current_val = config.get(slider_key, schema["defaults"][slider_key])
            slider = Slider(
                key=slider_key,
                label=label,
                x=30,
                y=y_pos,
                w=340,
                min_val=min_val,
                max_val=max_val,
                current_val=current_val,
                is_float=is_float,
                format_str=format_str
            )
            self.sliders[slider_key] = slider
            y_pos += spacing

    def toggle_autofit(self):
        self.auto_fit_enabled = not self.auto_fit_enabled
        self.autofit_btn.text = f"AUTO-FIT: {'ON' if self.auto_fit_enabled else 'OFF'}"
        self.autofit_btn.active = self.auto_fit_enabled
        self.preview_scale_slider.dragging = False

    def apply_fit_to_slider(self):
        self.preview_scale_slider.val = self.preview_scale
        self.toast_message = "Applied Fit Scale to Slider"
        self.toast_timer = 1.5

    def load_presets(self):
        defaults = {
            "1": self.difficulty_manager.get_preset_config("MEDIUM"),
            "2": self.difficulty_manager.get_preset_config("HARD"),
            "3": self.difficulty_manager.get_preset_config("NIGHTMARE")
        }
        if os.path.exists(self.presets_path):
            try:
                with open(self.presets_path, "r") as f:
                    self.presets_data = json.load(f)
                    for slot in ("1", "2", "3"):
                        if slot not in self.presets_data:
                            self.presets_data[slot] = defaults[slot].copy()
            except Exception:
                self.presets_data = defaults
        else:
            self.presets_data = defaults

    def update_preset_buttons(self):
        if len(self.analytics_buttons) >= 7:
            self.analytics_buttons[4].active = (self.active_preset_slot == 1)
            self.analytics_buttons[5].active = (self.active_preset_slot == 2)
            self.analytics_buttons[6].active = (self.active_preset_slot == 3)

    def apply_preset_slot(self, slot: int):
        if self.selected_boss not in ("wizard", "green_monster"):
            self.toast_message = "Presets only supported on Wizard and Green Monster bosses"
            self.toast_timer = 1.5
            return
            
        self.active_preset_slot = slot
        self.update_preset_buttons()
        preset_config = self.presets_data.get(str(slot))
        if preset_config:
            for key, val in preset_config.items():
                if key in self.sliders:
                    self.sliders[key].val = val
            self.toast_message = f"Preset {slot} Loaded!"
            self.toast_timer = 1.5

    def save_to_active_preset(self):
        if self.selected_boss not in ("wizard", "green_monster"):
            self.toast_message = "Presets only supported on Wizard and Green Monster bosses"
            self.toast_timer = 1.5
            return
            
        current_config = {}
        for k, slider in self.sliders.items():
            current_config[k] = slider.val
        
        self.presets_data[str(self.active_preset_slot)] = current_config
        
        try:
            os.makedirs(os.path.dirname(self.presets_path), exist_ok=True)
            with open(self.presets_path, "w") as f:
                json.dump(self.presets_data, f, indent=4)
            self.toast_message = f"Saved to Preset {self.active_preset_slot}!"
            self.toast_timer = 2.0
        except Exception as e:
            self.toast_message = f"Error: {e}"
            self.toast_timer = 2.0

    def apply_non_wizard_preset(self, difficulty_name: str):
        # Multipliers based on difficulty
        multipliers = {
            "EASY": {
                "max_health": 0.7,
                "speed": 0.8,
                "damage_scale": 0.7,
                "knockback_scale": 0.7,
                "detection_range": 0.7,
                "attack_range": 0.9,
                "vertical_tolerance": 0.8,
                "scale": 0.8
            },
            "MEDIUM": {
                "max_health": 1.0,
                "speed": 1.0,
                "damage_scale": 1.0,
                "knockback_scale": 1.0,
                "detection_range": 1.0,
                "attack_range": 1.0,
                "vertical_tolerance": 1.0,
                "scale": 1.0
            },
            "HARD": {
                "max_health": 1.3,
                "speed": 1.2,
                "damage_scale": 1.3,
                "knockback_scale": 1.3,
                "detection_range": 1.3,
                "attack_range": 1.1,
                "vertical_tolerance": 1.2,
                "scale": 1.3
            },
            "NIGHTMARE": {
                "max_health": 1.6,
                "speed": 1.4,
                "damage_scale": 1.6,
                "knockback_scale": 1.6,
                "detection_range": 1.6,
                "attack_range": 1.2,
                "vertical_tolerance": 1.5,
                "scale": 1.6
            }
        }
        
        mults = multipliers.get(difficulty_name.upper(), multipliers["MEDIUM"])
        schema = self.bosses[self.selected_boss]["schema"]
        defaults = schema["defaults"]
        
        # Apply the scaling to each slider if applicable, clamping to the slider bounds
        for key, mult in mults.items():
            if key in self.sliders:
                slider = self.sliders[key]
                base_val = defaults.get(key, slider.min_val)
                new_val = base_val * mult
                slider.val = max(slider.min_val, min(slider.max_val, new_val))

    def apply_recommended_difficulty(self):
        if not self.recent_sessions_analytics or self.recent_sessions_analytics.get("valid_session_count", 0) == 0:
            self.toast_message = "No recommendation available!"
            self.toast_timer = 2.0
            return
            
        rec_diff = self.recent_sessions_analytics.get("recommended_difficulty")
        if rec_diff in ("EASY", "MEDIUM", "HARD", "NIGHTMARE"):
            if self.selected_boss in ("wizard", "green_monster"):
                preset_config = self.difficulty_manager.get_preset_config(rec_diff)
                for key, val in preset_config.items():
                    if key in self.sliders:
                        self.sliders[key].val = val
            else:
                self.apply_non_wizard_preset(rec_diff)
            self.toast_message = f"Applied Recommended {rec_diff} Preset!"
            self.toast_timer = 2.0
        else:
            self.toast_message = "Invalid recommended difficulty!"
            self.toast_timer = 2.0

    def adjust_difficulty(self, direction: int):
        if self.selected_boss in ("wizard", "green_monster"):
            current_config = {k: slider.val for k, slider in self.sliders.items()}
            new_config = self.difficulty_manager.adjust_difficulty_level(current_config, direction)
            for k, val in new_config.items():
                if k in self.sliders:
                    self.sliders[k].val = val
        else:
            schema = self.bosses[self.selected_boss]["schema"]
            defaults = schema["defaults"]
            
            # Parameters to adjust (handles generic skeleton bosses/minions and bats)
            keys_to_adjust = ["max_health", "speed", "damage_scale", "knockback_scale", "detection_range", "attack_range", "vertical_tolerance", "scale"]
            
            for key in keys_to_adjust:
                if key in self.sliders:
                    slider = self.sliders[key]
                    base_val = defaults.get(key, slider.min_val)
                    # Adjust by direction * 10% of the default/baseline value
                    delta = direction * 0.1 * base_val
                    new_val = slider.val + delta
                    slider.val = max(slider.min_val, min(slider.max_val, new_val))
                    
        self.toast_message = "Difficulty " + ("Increased" if direction > 0 else "Decreased")
        self.toast_timer = 1.5

    def refresh_analytics(self):
        recent = self.log_parser.get_recent_sessions(limit=5)
        sessions_data = []
        for sid, paths in recent:
            sessions_data.append(self.log_parser.parse_session(paths))
        self.recent_sessions_analytics = self.difficulty_manager.evaluate_sessions(sessions_data)
        latest = self.log_parser.get_latest_session()
        self.latest_session_name = latest[0] if latest else "None"
        self.parsed_files_count = len(latest[1]) if latest else 0
        self.toast_message = "Telemetry Logs Refreshed!"
        self.toast_timer = 2.0

    def request_save_config(self):
        self.confirming_save = True

    def confirm_save_config(self):
        boss_key = self.selected_boss
        schema = self.bosses[boss_key]["schema"]
        config_path = schema["config_file"]
        
        # Update config dictionary from slider values
        config = self.boss_configs[boss_key]
        for k, slider in self.sliders.items():
            config[k] = slider.val
            
        # Enforce ordering constraints
        if boss_key in ("wizard", "green_monster"):
            if config["teleport_dist_max"] < config["teleport_dist_min"]:
                config["teleport_dist_max"] = config["teleport_dist_min"]
                self.sliders["teleport_dist_max"].val = config["teleport_dist_min"]
            if config["attack_cooldown_max"] < config["attack_cooldown_min"]:
                config["attack_cooldown_max"] = config["attack_cooldown_min"]
                self.sliders["attack_cooldown_max"].val = config["attack_cooldown_min"]
        elif "detection_range" in config and "attack_range" in config:
            if config["detection_range"] < config["attack_range"]:
                config["detection_range"] = config["attack_range"]
                self.sliders["detection_range"].val = config["attack_range"]

        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        # Create timestamped backup of current file
        if os.path.exists(config_path):
            try:
                import shutil
                from datetime import datetime
                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                base_name = os.path.splitext(os.path.basename(config_path))[0]
                backup_path = f"game_data/{base_name}.backup_{ts}.json"
                shutil.copy2(config_path, backup_path)
                print(f"[INFO] Created config backup at {backup_path}")
            except Exception as e:
                print(f"[WARNING] Failed to create backup: {e}")

        try:
            with open(config_path, "w") as f:
                json.dump(config, f, indent=2)
            self.toast_message = "Configuration Saved!"
            self.toast_timer = 2.0
            print(f"[INFO] Configuration saved successfully for {boss_key}.")
        except Exception as e:
            self.toast_message = "Save Failed!"
            self.toast_timer = 2.0
            print(f"[ERROR] Failed to save config: {e}")

    def reset_defaults(self):
        schema = self.bosses[self.selected_boss]["schema"]
        for k, v in schema["defaults"].items():
            if k in self.sliders:
                self.sliders[k].val = v
        self.toast_message = "Defaults Loaded (Press Save)"
        self.toast_timer = 2.0

    def request_sim_reset(self):
        self.confirming_sim_reset = True

    def scan_boss_animations(self, boss_key: str, boss_class: Type[Actor]) -> Dict[str, List[pg.Surface]]:
        state_patterns = {
            "IDLE": ["idle"],
            "CHASE": ["chase", "run", "walk", "move", "fly"],
            "ATTACK": ["attack", "atk", "atk1", "atk2", "1atk", "2atk"],
            "HURT": ["hurt", "hit", "take_hit", "take hit"],
            "DEATH": ["death", "die"]
        }
        
        animations = {}
        base_paths = [
            os.path.join("assets", boss_key),
            os.path.join("assets", "graphics", boss_key),
            os.path.join("assets", boss_class.__name__.lower()),
            os.path.join("assets", "graphics", boss_class.__name__.lower())
        ]
        base_paths.append(os.path.join("assets", "graphics", boss_key.capitalize()))
        base_paths.append(os.path.join("assets", "graphics", boss_class.__name__))
        
        found_base = None
        for bp in base_paths:
            if os.path.exists(bp) and os.path.isdir(bp):
                found_base = bp
                break
                
        # Hardcoded wizard loading fallback since folder patterns differ slightly
        if boss_key == "wizard":
            wizard_patterns = {
                "IDLE": ("assets/wizard/Idle/wizard_idle{}.png", 8),
                "CHASE": ("assets/wizard/Move/wizard_run{}.png", 8),
                "ATTACK": ("assets/wizard/Attack/wizard_atk1{}.png", 8),
                "HURT": ("assets/wizard/Hurt/wizard_hurt{}.png", 4),
                "DEATH": ("assets/wizard/Death/wizard_death{}.png", 4),
            }
            loaded_wizard = {}
            for state, (pattern, count) in wizard_patterns.items():
                frames = []
                for i in range(count):
                    f_path = pattern.format(i)
                    if os.path.exists(f_path):
                        frames.append(pg.image.load(f_path).convert_alpha())
                    else:
                        dummy = pg.Surface((150, 150), pg.SRCALPHA)
                        pg.draw.rect(dummy, (255, 0, 100), (40, 40, 70, 70), 2)
                        frames.append(dummy)
                loaded_wizard[state] = frames
            return loaded_wizard
            
        # Hardcoded skeleton loading fallback
        if boss_key in ("skeleton", "skeleton_minion"):
            skel_patterns = {
                "IDLE": ("assets/skeleton/Skeleton_01_White_Idle/skeleton-idle_{}.png", 8),
                "CHASE": ("assets/skeleton/Skeleton_01_White_Walk/skeleton-walk_{:02d}.png", 10),
                "ATTACK": ("assets/skeleton/Skeleton_01_White_Attack1/skeleton-atk2_{:02d}.png", 10),
                "HURT": ("assets/skeleton/Skeleton_01_White_Hurt/skeleton-hurt_{}.png", 5),
                "DEATH": ("assets/skeleton/Skeleton_01_White_Die/skeleton-death_{:02d}.png", 13),
            }
            loaded_skel = {}
            for state, (pattern, count) in skel_patterns.items():
                frames = []
                for i in range(count):
                    f_path = pattern.format(i)
                    if os.path.exists(f_path):
                        frames.append(pg.image.load(f_path).convert_alpha())
                    else:
                        dummy = pg.Surface((150, 150), pg.SRCALPHA)
                        pg.draw.rect(dummy, (255, 0, 100), (40, 40, 70, 70), 2)
                        frames.append(dummy)
                loaded_skel[state] = frames
            return loaded_skel

        # Hardcoded goblin loading fallback
        if boss_key == "goblin":
            goblin_patterns = {
                "IDLE": ("assets/graphics/Goblin/Idle/idle_{}.png", 4),
                "CHASE": ("assets/graphics/Goblin/Run/goblin_{}.png", 8),
                "ATTACK": ("assets/graphics/Goblin/Attack/goblin_atk_{}.png", 8),
                "HURT": ("assets/graphics/Goblin/Idle/idle_{}.png", 4),
                "DEATH": ("assets/graphics/Goblin/Idle/idle_{}.png", 4),
            }
            loaded_goblin = {}
            for state, (pattern, count) in goblin_patterns.items():
                frames = []
                for i in range(count):
                    f_path = pattern.format(i)
                    if os.path.exists(f_path):
                        frames.append(pg.image.load(f_path).convert_alpha())
                    else:
                        dummy = pg.Surface((100, 100), pg.SRCALPHA)
                        pg.draw.rect(dummy, (0, 255, 100), (20, 20, 60, 60), 2)
                        frames.append(dummy)
                loaded_goblin[state] = frames
            return loaded_goblin

        # Hardcoded green_monster loading fallback
        if boss_key == "green_monster":
            monster_patterns = {
                "IDLE": ("assets/graphics/green_monster/idle/idle_{}.png", 15),
                "CHASE": ("assets/graphics/green_monster/walk/walk_{}.png", 12),
                "ATTACK": ("assets/graphics/green_monster/1atk/1atk_{}.png", 7),
                "HURT": ("assets/graphics/green_monster/hurt/hurt_{}.png", 5),
                "DEATH": ("assets/graphics/green_monster/death/death_{}.png", 11),
            }
            loaded_monster = {}
            for state, (pattern, count) in monster_patterns.items():
                frames = []
                for i in range(1, count + 1):
                    f_path = pattern.format(i)
                    if os.path.exists(f_path):
                        frames.append(pg.image.load(f_path).convert_alpha())
                    else:
                        dummy = pg.Surface((120, 120), pg.SRCALPHA)
                        pg.draw.rect(dummy, (100, 255, 0), (20, 20, 80, 80), 2)
                        frames.append(dummy)
                loaded_monster[state] = frames
            return loaded_monster

        # Hardcoded skeleton_zombie loading fallback
        if boss_key == "skeleton_zombie":
            zombie_patterns = {
                "IDLE": ("assets/graphics/SkeletonZombie/Idle/skeletonZombie_{}.png", 8),
                "CHASE": ("assets/graphics/SkeletonZombie/Chase/skeletonZombie_chase_{:02d}.png", 10),
                "ATTACK": ("assets/graphics/SkeletonZombie/Attack/skeletonZombie_attack_{:02d}.png", 23),
                "HURT": ("assets/graphics/SkeletonZombie/Hurt/skeletonZombie_die_{}.png", 3),
                "DEATH": ("assets/graphics/SkeletonZombie/Hurt/skeletonZombie_die_{}.png", 3),
            }
            loaded_zombie = {}
            for state, (pattern, count) in zombie_patterns.items():
                frames = []
                for i in range(count):
                    f_path = pattern.format(i)
                    if os.path.exists(f_path):
                        frames.append(pg.image.load(f_path).convert_alpha())
                    else:
                        dummy = pg.Surface((100, 100), pg.SRCALPHA)
                        pg.draw.rect(dummy, (200, 100, 50), (20, 20, 60, 60), 2)
                        frames.append(dummy)
                loaded_zombie[state] = frames
            return loaded_zombie

        # Hardcoded blood_zombie loading fallback
        if boss_key == "blood_zombie":
            blood_patterns = {
                "IDLE": ("assets/graphics/bloodZombie/Idle/blood_idle{:02d}.png", 10),
                "CHASE": ("assets/graphics/bloodZombie/Move/blood_chase_{}.png", 8),
                "ATTACK": ("assets/graphics/bloodZombie/Attack1/blood_attack2_{:02d}.png", 16),
                "HURT": ("assets/graphics/bloodZombie/Death/blood_death_{}.png", 6),
                "DEATH": ("assets/graphics/bloodZombie/Death/blood_death_{}.png", 6),
            }
            loaded_blood = {}
            for state, (pattern, count) in blood_patterns.items():
                frames = []
                for i in range(count):
                    f_path = pattern.format(i)
                    if os.path.exists(f_path):
                        frames.append(pg.image.load(f_path).convert_alpha())
                    else:
                        dummy = pg.Surface((120, 120), pg.SRCALPHA)
                        pg.draw.rect(dummy, (220, 30, 30), (20, 20, 80, 80), 2)
                        frames.append(dummy)
                loaded_blood[state] = frames
            return loaded_blood

        # Hardcoded bat loading fallback
        if boss_key == "bat":
            bat_patterns = {
                "IDLE": ("assets/graphics/bat/idle/bat_idle_{}.png", 9),
                "CHASE": ("assets/graphics/bat/running/bat_running_{}.png", 8),
                "ATTACK": ("assets/graphics/bat/attacking/bat_atk1_{}.png", 8),
                "HURT": ("assets/graphics/bat/idle/bat_idle_{}.png", 9),
                "DEATH": ("assets/graphics/bat/idle/bat_idle_{}.png", 9),
            }
            loaded_bat = {}
            for state, (pattern, count) in bat_patterns.items():
                frames = []
                for i in range(count):
                    f_path = pattern.format(i)
                    if os.path.exists(f_path):
                        frames.append(pg.image.load(f_path).convert_alpha())
                    else:
                        dummy = pg.Surface((80, 80), pg.SRCALPHA)
                        pg.draw.rect(dummy, (0, 180, 255), (10, 10, 60, 60), 2)
                        frames.append(dummy)
                loaded_bat[state] = frames
            return loaded_bat

        if not found_base:
            # default fallback
            for state in state_patterns:
                dummy_list = []
                for i in range(4):
                    dummy = pg.Surface((150, 150), pg.SRCALPHA)
                    pg.draw.rect(dummy, (255, 0, 100), (40, 40, 70, 70), 2)
                    dummy_list.append(dummy)
                animations[state] = dummy_list
            return animations
            
        subdirs = [d for d in os.listdir(found_base) if os.path.isdir(os.path.join(found_base, d))]
        for state, matches in state_patterns.items():
            matched_dir = None
            for sd in subdirs:
                if any(m in sd.lower() for m in matches):
                    matched_dir = os.path.join(found_base, sd)
                    break
            
            frames = []
            if matched_dir:
                img_files = sorted([
                    os.path.join(matched_dir, f) for f in os.listdir(matched_dir)
                    if f.lower().endswith((".png", ".jpg", ".jpeg"))
                ])
                for fpath in img_files:
                    try:
                        img = pg.image.load(fpath).convert_alpha()
                        frames.append(img)
                    except Exception:
                        pass
            if not frames:
                # dummy fallback
                for i in range(4):
                    dummy = pg.Surface((150, 150), pg.SRCALPHA)
                    pg.draw.rect(dummy, (255, 0, 100), (40, 40, 70, 70), 2)
                    frames.append(dummy)
            animations[state] = frames
        return animations

    def load_all_animations(self):
        for bkey, binfo in self.bosses.items():
            self.animations[bkey] = self.scan_boss_animations(bkey, binfo["class"])

    def set_review_state(self, state: str):
        if self.mode == "REVIEW":
            self.current_state = state
            self.frame_index = 0.0
            self.update_review_buttons()

    def set_mode(self, mode: str):
        self.mode = mode
        self.update_mode_buttons()
        if mode == "SIMULATION":
            self.init_simulation_state()
        elif mode == "ANALYTICS":
            self.refresh_analytics()

    def update_review_buttons(self):
        for btn in self.review_buttons:
            btn.active = (btn.text == self.current_state)

    def update_mode_buttons(self):
        for btn in self.mode_buttons:
            if btn.text == "ANIMATION LOOP" and self.mode == "REVIEW":
                btn.active = True
            elif btn.text == "AI FLOW SIMULATION" and self.mode == "SIMULATION":
                btn.active = True
            elif btn.text == "DIFFICULTY TUNER" and self.mode == "ANALYTICS":
                btn.active = True
            else:
                btn.active = False

    def init_simulation_state(self):
        schema = self.bosses[self.selected_boss]["schema"]
        self.sim_player_x = 100
        self.sim_boss_x = schema["simulation"].get("boss_x", 400)
        self.sim_boss_state = "CHASE"
        self.sim_boss_facing_left = (self.selected_boss == "bat")
        self.sim_events = ["Simulation started."]
        
        # Wizard specific simulation fields
        self.sim_boss_mana = self.sliders.get("max_mana", Slider("x", "y", 0, 0, 0, 0, 0, 100)).val
        self.sim_boss_is_stagnant = False
        self.sim_boss_stagnant_timer = 0.0
        self.sim_boss_is_recharging = False
        self.sim_boss_recharge_timer = 0.0
        self.sim_boss_attack_cooldown = 0.0
        self.sim_boss_chase_delay_timer = 0.0
        self.sim_boss_chase_delay_active = False
        self.sim_boss_teleport_flash_timer = 0.0
        self.sim_boss_teleport_after_hurt = False
        self.sim_boss_has_cast = False
        self.sim_fireballs = []
        
        # Melee/Skeleton specific simulation fields
        self.sim_boss_cooldown = 0.0

    def add_sim_log(self, text: str):
        self.sim_events.append(text)
        if len(self.sim_events) > 8:
            self.sim_events.pop(0)

    def update_simulation(self, dt: float):
        if self.selected_boss in ("wizard", "green_monster"):
            self.update_wizard_simulation(dt)
        elif self.selected_boss == "bat":
            self.update_bat_simulation(dt)
        else:
            self.update_skeleton_simulation(dt)

    def update_bat_simulation(self, dt: float):
        speed = self.sliders["speed"].val
        self.sim_boss_facing_left = True
        self.sim_boss_state = "CHASE"
        
        self.sim_boss_x = int(self.sim_boss_x - speed * dt)
        if self.sim_boss_x < 50:
            self.sim_boss_x = 1000
            self.add_sim_log("Bat spawned on the right!")
            
        frames = self.animations[self.selected_boss][self.sim_boss_state]
        frames_count = len(frames)
        self.frame_index += self.play_speed * 10 * dt
        if self.frame_index >= frames_count:
            self.frame_index = 0.0

    def update_wizard_simulation(self, dt: float):
        max_mana = self.sliders["max_mana"].val
        spell_cost = self.sliders["spell_mana_cost"].val
        stagnant_duration = self.sliders["stagnant_duration"].val
        teleport_min = self.sliders["teleport_dist_min"].val
        teleport_max = self.sliders["teleport_dist_max"].val
        recharge_rate = self.sliders["mana_recharge_rate"].val
        chase_delay = self.sliders["chase_delay_duration"].val
        cd_min = self.sliders["attack_cooldown_min"].val
        cd_max = self.sliders["attack_cooldown_max"].val

        # Update fireball movements
        for fb in list(self.sim_fireballs):
            fb["x"] += fb["speed"] * dt * fb["dir"]
            if abs(fb["x"] - self.sim_boss_x) > 600:
                self.sim_fireballs.remove(fb)
            elif abs(fb["x"] - self.sim_player_x) < 20:
                self.sim_fireballs.remove(fb)
                proj_name = "Toxic glob" if self.selected_boss == "green_monster" else "Fireball"
                self.add_sim_log(f"{proj_name} HIT mock player!")

        # Decrement cooldowns & timers
        if self.sim_boss_attack_cooldown > 0.0:
            self.sim_boss_attack_cooldown = max(0.0, self.sim_boss_attack_cooldown - dt)
        if self.sim_boss_chase_delay_timer > 0.0:
            self.sim_boss_chase_delay_timer = max(0.0, self.sim_boss_chase_delay_timer - dt)
        if self.sim_boss_teleport_flash_timer > 0.0:
            self.sim_boss_teleport_flash_timer = max(0.0, self.sim_boss_teleport_flash_timer - dt)

        # Handle stagnant timer
        if self.sim_boss_is_stagnant:
            self.sim_boss_stagnant_timer = max(0.0, self.sim_boss_stagnant_timer - dt)
            if self.sim_boss_stagnant_timer <= 0.0:
                self.trigger_sim_teleport()

        # Handle recharge logic
        if self.sim_boss_is_recharging:
            self.sim_boss_mana = min(max_mana, self.sim_boss_mana + recharge_rate * dt)
            if self.sim_boss_mana >= max_mana:
                self.sim_boss_is_recharging = False
                self.add_sim_log("Mana fully recharged!")

        # Animation index update
        frames_count = len(self.animations[self.selected_boss][self.sim_boss_state])
        self.frame_index += self.play_speed * 10 * dt
        if self.frame_index >= frames_count:
            self.frame_index = 0.0
            if self.sim_boss_state == "ATTACK":
                self.sim_boss_state = "IDLE"
                self.sim_boss_has_cast = False
                self.sim_boss_attack_cooldown = random.uniform(cd_min, cd_max)
                self.add_sim_log(f"Attack finished. Cooldown set to {self.sim_boss_attack_cooldown:.1f}s")
            elif self.sim_boss_state == "HURT":
                self.sim_boss_state = "IDLE"
                if getattr(self, "sim_boss_teleport_after_hurt", False):
                    self.sim_boss_teleport_after_hurt = False
                    self.trigger_sim_teleport()

        # Cast fireball at frame 4 of ATTACK animation
        if self.sim_boss_state == "ATTACK" and not self.sim_boss_has_cast:
            if int(self.frame_index) == 4:
                self.sim_boss_has_cast = True
                self.sim_boss_mana = max(0.0, self.sim_boss_mana - spell_cost)
                self.sim_fireballs.append({
                    "x": self.sim_boss_x,
                    "y": 320,
                    "speed": 350.0,
                    "dir": -1 if self.sim_boss_facing_left else 1
                })
                proj_name = "Toxic glob" if self.selected_boss == "green_monster" else "Fireball"
                self.add_sim_log(f"{proj_name} cast! Mana consumed (-{spell_cost:.1f}). Remaining: {self.sim_boss_mana:.1f}")

        if self.sim_boss_state in ("ATTACK", "HURT"):
            return

        # Low mana stagnant check
        if self.sim_boss_mana < spell_cost and not self.sim_boss_is_recharging and not self.sim_boss_is_stagnant:
            self.sim_boss_is_stagnant = True
            self.sim_boss_stagnant_timer = stagnant_duration
            self.sim_boss_state = "IDLE"
            self.add_sim_log(f"Low mana! Exhausted/Stagnant for {stagnant_duration:.1f}s")
            return

        if self.sim_boss_is_stagnant or self.sim_boss_is_recharging:
            self.sim_boss_state = "IDLE"
            if self.sim_boss_is_stagnant and random.random() < 0.015:
                self.add_sim_log("Player attacked boss while stagnant!")
                self.sim_boss_state = "HURT"
                self.frame_index = 0.0
                self.sim_boss_teleport_after_hurt = True
            return

        dist_x = self.sim_boss_x - self.sim_player_x
        abs_dist_x = abs(dist_x)
        self.sim_boss_facing_left = (dist_x > 0)

        # Sweet spot check (between 120 and 260px)
        if 120 <= abs_dist_x <= 260:
            if self.sim_boss_attack_cooldown <= 0.0 and self.sim_boss_mana >= spell_cost:
                self.sim_boss_state = "ATTACK"
                self.frame_index = 0.0
                self.sim_boss_chase_delay_active = False
                self.sim_boss_chase_delay_timer = 0.0
                self.add_sim_log("Boss stands sweet-spot: initiates ATTACK")
                return
            else:
                self.sim_boss_state = "IDLE"

        # Retreat if player is too close
        elif abs_dist_x < 120:
            self.sim_boss_state = "CHASE"
            retreat_speed = 130.0
            if dist_x > 0:
                self.sim_boss_x = int(self.sim_boss_x + retreat_speed * dt)
            else:
                self.sim_boss_x = int(self.sim_boss_x - retreat_speed * dt)
            self.sim_boss_x = max(100, min(1180, self.sim_boss_x))

        # Chase if player is too far
        elif abs_dist_x > 260:
            if self.sim_boss_state == "IDLE" and not self.sim_boss_chase_delay_active:
                self.sim_boss_chase_delay_timer = chase_delay
                self.sim_boss_chase_delay_active = True
                self.add_sim_log(f"Player fled! Chase delay activated: {chase_delay:.1f}s")
                
            if self.sim_boss_chase_delay_active:
                if self.sim_boss_chase_delay_timer > 0.0:
                    self.sim_boss_state = "IDLE"
                else:
                    self.sim_boss_chase_delay_active = False
            else:
                self.sim_boss_state = "CHASE"
                chase_speed = 100.0
                if dist_x > 0:
                    self.sim_boss_x = int(self.sim_boss_x - chase_speed * dt)
                else:
                    self.sim_boss_x = int(self.sim_boss_x + chase_speed * dt)

    def trigger_sim_teleport(self):
        teleport_min = self.sliders["teleport_dist_min"].val
        teleport_max = self.sliders["teleport_dist_max"].val
        
        self.sim_boss_is_stagnant = False
        self.sim_boss_stagnant_timer = 0.0
        self.sim_boss_is_recharging = True
        self.sim_boss_teleport_flash_timer = 0.6
        
        dist_offset = random.randint(int(teleport_min), int(teleport_max))
        if self.sim_boss_x > self.sim_player_x:
            target_x = self.sim_player_x + dist_offset
        else:
            target_x = self.sim_player_x - dist_offset
            
        self.sim_boss_x = max(100, min(1180, target_x))
        self.sim_boss_state = "IDLE"
        self.frame_index = 0.0
        self.add_sim_log(f"TELEPORTED to x={self.sim_boss_x}! Starting mana recharge.")

    def update_skeleton_simulation(self, dt: float):
        speed = self.sliders["speed"].val
        detection_range = self.sliders["detection_range"].val
        attack_range = self.sliders["attack_range"].val

        if self.sim_boss_cooldown > 0.0:
            self.sim_boss_cooldown = max(0.0, self.sim_boss_cooldown - dt)

        # Animation index update
        frames_count = len(self.animations[self.selected_boss][self.sim_boss_state])
        self.frame_index += self.play_speed * 10 * dt
        if self.frame_index >= frames_count:
            self.frame_index = 0.0
            if self.sim_boss_state == "ATTACK":
                self.sim_boss_state = "IDLE"
                self.sim_boss_cooldown = 1.2
                self.add_sim_log("Melee strike finished. Cooldown set to 1.2s")
            elif self.sim_boss_state == "HURT":
                self.sim_boss_state = "IDLE"

        if self.sim_boss_state in ("ATTACK", "HURT"):
            # Trigger hit log on critical frames
            if self.sim_boss_state == "ATTACK" and int(self.frame_index) == 6:
                dist_x = abs(self.sim_boss_x - self.sim_player_x)
                if dist_x < attack_range:
                    self.add_sim_log("Melee STRIKE HIT mock player!")
            return

        dist_x = self.sim_boss_x - self.sim_player_x
        abs_dist_x = abs(dist_x)
        self.sim_boss_facing_left = (dist_x > 0)

        if abs_dist_x < attack_range:
            if self.sim_boss_cooldown <= 0.0:
                self.sim_boss_state = "ATTACK"
                self.frame_index = 0.0
                self.add_sim_log("Player in range: initiates ATTACK")
            else:
                self.sim_boss_state = "IDLE"
        elif abs_dist_x < detection_range:
            self.sim_boss_state = "CHASE"
            move_step = int(speed * dt * 60)
            if dist_x > 0:
                self.sim_boss_x -= move_step
            else:
                self.sim_boss_x += move_step
            self.sim_boss_x = max(100, min(1180, self.sim_boss_x))
        else:
            self.sim_boss_state = "IDLE"

        # Mock player damage simulation (small random chance of hitting the boss)
        if self.sim_boss_state == "CHASE" and random.random() < 0.005:
            self.sim_boss_state = "HURT"
            self.frame_index = 0.0
            self.add_sim_log("Player struck boss during pursuit!")

    def draw_analytics_dashboard(self, surface: pg.Surface, rect: pg.Rect):
        margin_x = 25
        margin_y = 20
        start_x = rect.x + margin_x
        start_y = rect.y + margin_y

        txt_sess = ui_font.render(f"Latest Session ID: {self.latest_session_name}", True, ACCENT_CYAN)
        txt_active_preset = ui_font.render(f"Active Preset Slot: Preset {self.active_preset_slot}", True, ACCENT_PURPLE)
        txt_chunks = value_font.render(f"Parsed rotated files: {self.parsed_files_count}", True, TEXT_MUTED)
        surface.blit(txt_sess, (start_x, start_y))
        surface.blit(txt_chunks, (rect.right - margin_x - txt_chunks.get_width(), start_y))
        surface.blit(txt_active_preset, (start_x, start_y + 24))
        
        divider_y = start_y + 55
        pg.draw.line(surface, BORDER_COLOR, (start_x, divider_y), (rect.right - margin_x, divider_y), 1)

        analytics = self.recent_sessions_analytics
        if not analytics or analytics.get("valid_session_count", 0) == 0:
            txt_nodata = title_font.render("Insufficient telemetry data for reliable recommendation.", True, (231, 76, 60))
            txt_nodata_rect = txt_nodata.get_rect(centerx=rect.centerx, centery=rect.centery)
            surface.blit(txt_nodata, txt_nodata_rect)

            txt_hint = ui_font.render("Ensure session duration is at least 60 seconds OR the boss was defeated.", True, TEXT_MUTED)
            txt_hint_rect = txt_hint.get_rect(centerx=rect.centerx, y=txt_nodata_rect.bottom + 15)
            surface.blit(txt_hint, txt_hint_rect)
            return

        col1_x = start_x
        col2_x = rect.x + 420
        content_y = divider_y + 20

        metrics = analytics["metrics"]
        dur = metrics.get("duration_sec", 0.0)
        fps = metrics.get("avg_fps", 0.0)
        
        col1_lines = [
            ("Session Duration", f"{dur:.1f} seconds"),
            ("Average FPS", f"{fps:.1f} FPS"),
            ("Total Frame Samples", f"{int(metrics.get('total_frames', 0))}"),
            ("Player Damage Taken", f"{metrics.get('player_damage_taken', 0.0):.1f} hp"),
            ("Boss Damage Taken", f"{metrics.get('boss_damage_taken', 0.0):.1f} hp"),
            ("Player Hit Count", f"{int(metrics.get('player_hits_received', 0))}"),
            ("Boss Hit Count", f"{int(metrics.get('boss_hits_received', 0))}"),
            ("Boss Attack Count", f"{int(metrics.get('boss_attacks', 0))}"),
        ]

        curr_y = content_y
        col1_header = ui_font.render("COMBAT & PERFORMANCE METRICS", True, (255, 255, 255))
        surface.blit(col1_header, (col1_x, curr_y))
        curr_y += 30

        for label, val in col1_lines:
            txt_lbl = value_font.render(label, True, TEXT_MUTED)
            txt_val = value_font.render(val, True, TEXT_COLOR)
            surface.blit(txt_lbl, (col1_x, curr_y))
            surface.blit(txt_val, (col1_x + 220, curr_y))
            curr_y += 24

        accuracies = analytics["accuracies"]
        col2_lines = [
            ("Detection Accuracy", f"{accuracies.get('detection_accuracy', 0.0):.1f}%"),
            ("Attack Accuracy", f"{accuracies.get('attack_accuracy', 0.0):.1f}%"),
            ("Bad Attacks (Out of range)", f"{int(accuracies.get('bad_attacks', 0))}"),
            ("Missed Opportunities", f"{int(accuracies.get('missed_opportunities', 0))} frames"),
        ]

        curr_y = content_y
        col2_header = ui_font.render("AI DETECTION & RANGE ACCURACY", True, (255, 255, 255))
        surface.blit(col2_header, (col2_x, curr_y))
        curr_y += 30

        for label, val in col2_lines:
            txt_lbl = value_font.render(label, True, TEXT_MUTED)
            txt_val = value_font.render(val, True, TEXT_COLOR)
            surface.blit(txt_lbl, (col2_x, curr_y))
            surface.blit(txt_val, (col2_x + 240, curr_y))
            curr_y += 20

        # Render player style & combat dynamics section
        curr_y += 10
        col2_header2 = ui_font.render("PLAYER STYLE & COMBAT DYNAMICS", True, (255, 255, 255))
        surface.blit(col2_header2, (col2_x, curr_y))
        curr_y += 24

        dynamics = analytics.get("combat_dynamics", {})
        col2_lines2 = [
            ("Player Defensive Ratio", f"{dynamics.get('player_defensive_ratio', 0.0):.1f}%"),
            ("Player Stand Still Ratio", f"{dynamics.get('player_standing_ratio', 0.0):.1f}%"),
            ("Player Jumps / Min", f"{dynamics.get('player_jumps_per_min', 0.0):.1f}"),
            ("Player Side Swaps / Min", f"{dynamics.get('player_side_swaps_per_min', 0.0):.1f}"),
            ("Boss Spell Accuracy", f"{dynamics.get('boss_spell_accuracy', 0.0):.1f}%"),
        ]

        for label, val in col2_lines2:
            txt_lbl = value_font.render(label, True, TEXT_MUTED)
            txt_val = value_font.render(val, True, TEXT_COLOR)
            surface.blit(txt_lbl, (col2_x, curr_y))
            surface.blit(txt_val, (col2_x + 240, curr_y))
            curr_y += 18

        divider2_y = content_y + 250
        pg.draw.line(surface, BORDER_COLOR, (start_x, divider2_y), (rect.right - margin_x, divider2_y), 1)

        rec_y = divider2_y + 10
        rec_diff = analytics["recommended_difficulty"]
        confidence = analytics["confidence"]
        description = analytics["description"]

        rec_color = ACCENT_CYAN
        if rec_diff == "EASY":
            rec_color = (46, 204, 113)
        elif rec_diff == "HARD":
            rec_color = (241, 196, 15)
        elif rec_diff == "NIGHTMARE":
            rec_color = (231, 76, 60)

        txt_rec_title = ui_font.render("RECOMMENDED TUNING PRESET: ", True, TEXT_MUTED)
        txt_rec_val = ui_font.render(f"{rec_diff}", True, rec_color)
        txt_conf = value_font.render(f"(Confidence: {confidence.capitalize()})", True, ACCENT_BLUE if confidence.lower() == "high" else TEXT_MUTED)

        surface.blit(txt_rec_title, (start_x, rec_y))
        surface.blit(txt_rec_val, (start_x + txt_rec_title.get_width(), rec_y))
        surface.blit(txt_conf, (start_x + txt_rec_title.get_width() + txt_rec_val.get_width() + 10, rec_y + 2))

        txt_desc = help_font.render(description, True, TEXT_COLOR)
        surface.blit(txt_desc, (start_x, rec_y + 22))

        advisory_notes = dynamics.get("advisory", [])
        if advisory_notes:
            adv_y = rec_y + 36
            txt_adv_hdr = help_font.render("AI Suggestion: ", True, ACCENT_CYAN)
            surface.blit(txt_adv_hdr, (start_x, adv_y))
            adv_text = " | ".join(advisory_notes)
            txt_adv = help_font.render(adv_text, True, TEXT_COLOR)
            surface.blit(txt_adv, (start_x + txt_adv_hdr.get_width(), adv_y))

    def run(self):
        while self.running:
            dt = self.clock.tick(60) / 1000.0
            
            # 1. Event Handling
            events = pg.event.get()
            for event in events:
                if event.type == pg.QUIT:
                    self.running = False
                elif event.type == pg.KEYDOWN:
                    if event.key == pg.K_ESCAPE:
                        if self.confirming_save:
                            self.confirming_save = False
                        elif self.confirming_sim_reset:
                            self.confirming_sim_reset = False
                        else:
                            self.running = False
                    elif event.key == pg.K_RETURN or event.key == pg.K_KP_ENTER:
                        if self.confirming_save:
                            self.confirm_save_config()
                            self.confirming_save = False
                        elif self.confirming_sim_reset:
                            self.init_simulation_state()
                            self.confirming_sim_reset = False
                    elif event.key == pg.K_s:
                        if not self.confirming_save and not self.confirming_sim_reset:
                            self.confirming_save = True
                    elif event.key == pg.K_r:
                        if not self.confirming_save and not self.confirming_sim_reset:
                            if self.mode == "SIMULATION":
                                self.confirming_sim_reset = True
                            else:
                                self.reset_defaults()
                        
                # Handle Modal click inputs first
                if self.confirming_save:
                    if event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
                        dialog_w, dialog_h = 500, 200
                        dialog_x = (SCREEN_W - dialog_w) // 2
                        dialog_y = (SCREEN_H - dialog_h) // 2
                        confirm_rect = pg.Rect(dialog_x + 40, dialog_y + 120, 180, 42)
                        cancel_rect = pg.Rect(dialog_x + 280, dialog_y + 120, 180, 42)
                        if confirm_rect.collidepoint(event.pos):
                            self.confirm_save_config()
                            self.confirming_save = False
                        elif cancel_rect.collidepoint(event.pos):
                            self.confirming_save = False
                    continue
                    
                if self.confirming_sim_reset:
                    if event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
                        dialog_w, dialog_h = 500, 200
                        dialog_x = (SCREEN_W - dialog_w) // 2
                        dialog_y = (SCREEN_H - dialog_h) // 2
                        confirm_rect = pg.Rect(dialog_x + 40, dialog_y + 120, 180, 42)
                        cancel_rect = pg.Rect(dialog_x + 280, dialog_y + 120, 180, 42)
                        if confirm_rect.collidepoint(event.pos):
                            self.init_simulation_state()
                            self.confirming_sim_reset = False
                        elif cancel_rect.collidepoint(event.pos):
                            self.confirming_sim_reset = False
                    continue

                # Handle normal inputs
                for btn in self.tab_buttons:
                    btn.handle_event(event)
                for slider in self.sliders.values():
                    slider.handle_event(event)
                for btn in self.action_buttons:
                    btn.handle_event(event)
                for btn in self.mode_buttons:
                    btn.handle_event(event)

                # Mode dependent control inputs
                if self.mode == "REVIEW":
                    for btn in self.review_buttons:
                        btn.handle_event(event)
                elif self.mode == "SIMULATION":
                    self.restart_sim_btn.handle_event(event)
                elif self.mode == "ANALYTICS":
                    for btn in self.analytics_buttons:
                        btn.handle_event(event)

                if self.mode != "ANALYTICS":
                    self.autofit_btn.handle_event(event)
                    self.apply_fit_btn.handle_event(event)

                    if not self.auto_fit_enabled:
                        self.preview_scale_slider.handle_event(event)
                    self.playback_speed_slider.handle_event(event)

            # Update live settings if not in modal
            if not self.confirming_save and not self.confirming_sim_reset:
                if not self.auto_fit_enabled:
                    self.preview_scale = self.preview_scale_slider.val
                self.play_speed = self.playback_speed_slider.val

            # 2. Update logic based on Mode
            if not self.confirming_save and not self.confirming_sim_reset:
                if self.mode == "REVIEW":
                    frames = self.animations[self.selected_boss][self.current_state]
                    frames_count = len(frames)
                    self.frame_index += self.play_speed * 10 * dt
                    if self.frame_index >= frames_count:
                        self.frame_index = 0.0
                elif self.mode == "SIMULATION":
                    m_pos = pg.mouse.get_pos()
                    if 430 <= m_pos[0] <= 1250 and 80 <= m_pos[1] <= 480:
                        self.sim_player_x = int((m_pos[0] - 430) / (820 / 1200))
                    self.update_simulation(dt)

            # 3. Drawing
            screen.fill(BG_COLOR)
            
            # Left panel sidebar background
            pg.draw.rect(screen, PANEL_BG, (0, 0, 400, SCREEN_H))
            pg.draw.line(screen, BORDER_COLOR, (400, 0), (400, SCREEN_H), 2)

            # Draw Sidebar Title
            txt_title = title_font.render("BOSS CONFIG EDITOR", True, TEXT_COLOR)
            screen.blit(txt_title, (30, 30))

            # Draw Boss Selection Tabs
            for btn in self.tab_buttons:
                btn.draw(screen)

            # Draw Sliders & Action Buttons
            for slider in self.sliders.values():
                slider.draw(screen)
            for btn in self.action_buttons:
                btn.draw(screen)

            # Draw Preview Container
            preview_rect = pg.Rect(430, 80, 820, 400)
            pg.draw.rect(screen, PREVIEW_BG, preview_rect, border_radius=8)
            pg.draw.rect(screen, BORDER_COLOR, preview_rect, width=2, border_radius=8)

            # Title of Preview
            if self.mode == "REVIEW":
                title_str = f"{self.selected_boss.upper()} ANIMATION PREVIEW"
            elif self.mode == "SIMULATION":
                title_str = f"{self.selected_boss.upper()} AI FLOW SIMULATOR"
            else:
                title_str = "TELEMETRY LOG ANALYTICS & DIFFICULTY TUNER"
            txt_preview_title = title_font.render(title_str, True, TEXT_COLOR)
            screen.blit(txt_preview_title, (430, 35))

            if self.mode in ("REVIEW", "SIMULATION"):
                state_key = self.current_state if self.mode == "REVIEW" else self.sim_boss_state
                frames = self.animations[self.selected_boss][state_key]
                current_frame = frames[min(int(self.frame_index), len(frames) - 1)]

                # Auto-Fit scaling vs manual scaling
                if self.auto_fit_enabled:
                    fit = PreviewScaler.calculate_auto_fit(current_frame, preview_rect, floor_y=420)
                    self.preview_scale = fit["scale"]
                    scaled_w = fit["scaled_width"]
                    scaled_h = fit["scaled_height"]
                    
                    if self.mode == "REVIEW":
                        px_x = fit["x_pos_centered"] + scaled_w // 2
                        px_y = fit["y_pos"]
                    else:
                        px_x = int(430 + (self.sim_boss_x / 1200) * 820)
                        px_y = fit["y_pos"]
                else:
                    w, h = current_frame.get_size()
                    scaled_w = int(w * self.preview_scale)
                    scaled_h = int(h * self.preview_scale)
                    px_x = 840 if self.mode == "REVIEW" else int(430 + (self.sim_boss_x / 1200) * 820)
                    px_y = 420 - int(scaled_h * 0.72)

                if self.selected_boss == "bat":
                    px_y -= 100

                scaled_frame = pg.transform.scale(current_frame, (scaled_w, scaled_h))

                if self.mode == "SIMULATION" and self.sim_boss_facing_left:
                    scaled_frame = pg.transform.flip(scaled_frame, True, False)

                # Draw floor
                pg.draw.line(screen, (75, 75, 100), (430, 420), (1250, 420), 3)

                if self.mode == "SIMULATION" and self.selected_boss in ("wizard", "green_monster") and self.sim_boss_teleport_flash_timer > 0.0:
                    alpha = 80 if int(self.sim_boss_teleport_flash_timer * 30) % 2 == 0 else 180
                    scaled_frame.set_alpha(alpha)
                else:
                    scaled_frame.set_alpha(255)

                screen.blit(scaled_frame, (px_x - scaled_w // 2, px_y))

                # Draw Body Hitbox outline (green)
                body_rect = pg.Rect(px_x - scaled_w // 2, px_y, scaled_w, scaled_h)
                pg.draw.rect(screen, (46, 204, 113), body_rect, 1)

                # Draw Attack Hitbox outline/filled rect (orange when idle/tuning, red when attacking)
                if "attack_hitbox_width" in self.sliders and "attack_hitbox_height" in self.sliders:
                    atk_w = self.sliders["attack_hitbox_width"].val
                    atk_h = self.sliders["attack_hitbox_height"].val
                    scaled_atk_w = int(atk_w * self.preview_scale)
                    scaled_atk_h = int(atk_h * self.preview_scale)
                    
                    facing_left = False
                    if self.mode == "SIMULATION":
                        facing_left = self.sim_boss_facing_left
                        
                    if facing_left:
                        hitbox_x = (px_x - scaled_w // 2) - scaled_atk_w
                    else:
                        hitbox_x = (px_x + scaled_w // 2)
                        
                    if self.selected_boss == "wizard":
                        hitbox_y = (px_y + scaled_h // 2) - scaled_atk_h // 2
                    else:
                        hitbox_y = (px_y + scaled_h) - scaled_atk_h
                        
                    atk_rect = pg.Rect(hitbox_x, hitbox_y, scaled_atk_w, scaled_atk_h)
                    
                    is_attacking = False
                    if self.mode == "SIMULATION":
                        is_attacking = (self.sim_boss_state == "ATTACK")
                    else:
                        is_attacking = (self.current_state == "ATTACK")
                        
                    if is_attacking:
                        s = pg.Surface((scaled_atk_w, scaled_atk_h), pg.SRCALPHA)
                        s.fill((231, 76, 60, 80))
                        screen.blit(s, (hitbox_x, hitbox_y))
                        pg.draw.rect(screen, (231, 76, 60), atk_rect, 2)
                    else:
                        pg.draw.rect(screen, (230, 126, 34), atk_rect, 1)

                if self.mode == "SIMULATION" and self.selected_boss in ("wizard", "green_monster") and self.sim_boss_is_recharging:
                    glow_radius = int(55 + 5 * random.random())
                    aura = pg.Surface((glow_radius * 2, glow_radius * 2), pg.SRCALPHA)
                    # Green glow for green monster, cyan glow for wizard
                    glow_color = (0, 230, 118, 60) if self.selected_boss == "green_monster" else (0, 229, 255, 60)
                    pg.draw.circle(aura, glow_color, (glow_radius, glow_radius), glow_radius)
                    screen.blit(aura, (px_x - glow_radius, 420 - int(scaled_h * 0.36) - glow_radius))

                if self.mode == "SIMULATION":
                    p_px_x = int(430 + (self.sim_player_x / 1200) * 820)
                    pg.draw.circle(screen, (100, 255, 100), (p_px_x, 420 - 35), 18)
                    pg.draw.rect(screen, (80, 200, 80), (p_px_x - 6, 420 - 20, 12, 20))
                    txt_lbl = help_font.render("PLAYER (MOUSE)", True, (100, 255, 100))
                    screen.blit(txt_lbl, (p_px_x - txt_lbl.get_width() // 2, 420 - 70))

                    if self.selected_boss in ("wizard", "green_monster"):
                        for fb in self.sim_fireballs:
                            fb_x = int(430 + (fb["x"] / 1200) * 820)
                            if self.selected_boss == "green_monster":
                                pg.draw.circle(screen, (46, 204, 113), (fb_x, fb["y"]), 8)
                                pg.draw.circle(screen, (100, 255, 100), (fb_x, fb["y"]), 5)
                            else:
                                pg.draw.circle(screen, (255, 100, 0), (fb_x, fb["y"]), 8)
                                pg.draw.circle(screen, (255, 200, 0), (fb_x, fb["y"]), 5)

                    # Health & Mana bar overlay
                    bar_w = 80
                    bar_h = 6
                    bx_y = 420 - scaled_h - 20
                    if self.selected_boss in ("wizard", "green_monster"):
                        pg.draw.rect(screen, (255, 50, 50), (px_x - bar_w // 2, bx_y, bar_w, bar_h), border_radius=3)
                        mana_ratio = self.sim_boss_mana / self.sliders["max_mana"].val
                        pg.draw.rect(screen, (33, 150, 243), (px_x - bar_w // 2, bx_y + 9, int(bar_w * mana_ratio), bar_h), border_radius=3)
                        pg.draw.rect(screen, (60, 60, 60), (px_x - bar_w // 2, bx_y + 9, bar_w, bar_h), width=1, border_radius=3)
                    else:
                        # Standard health bar
                        pg.draw.rect(screen, (255, 50, 50), (px_x - bar_w // 2, bx_y, bar_w, bar_h), border_radius=3)
                        pg.draw.rect(screen, (60, 60, 60), (px_x - bar_w // 2, bx_y, bar_w, bar_h), width=1, border_radius=3)

                    log_y = 95
                    for ev in self.sim_events:
                        txt_ev = help_font.render(ev, True, ACCENT_CYAN if "TELEPORTED" in ev or "recharged" in ev or "HIT" in ev else TEXT_COLOR)
                        screen.blit(txt_ev, (450, log_y))
                        log_y += 18

                # Draw floor range/detection indicators for both REVIEW and SIMULATION modes
                if self.selected_boss == "wizard":
                    bound_1 = int(px_x - 260 * (820 / 1200))
                    bound_2 = int(px_x - 120 * (820 / 1200))
                    bound_3 = int(px_x + 120 * (820 / 1200))
                    bound_4 = int(px_x + 260 * (820 / 1200))
                    pg.draw.line(screen, (60, 60, 80), (bound_1, 420 - 15), (bound_1, 420 + 15), 1)
                    pg.draw.line(screen, (60, 60, 80), (bound_2, 420 - 15), (bound_2, 420 + 15), 1)
                    pg.draw.line(screen, (60, 60, 80), (bound_3, 420 - 15), (bound_3, 420 + 15), 1)
                    pg.draw.line(screen, (60, 60, 80), (bound_4, 420 - 15), (bound_4, 420 + 15), 1)
                elif "attack_range" in self.sliders and "detection_range" in self.sliders:
                    atk_range = self.sliders["attack_range"].val
                    det_range = self.sliders["detection_range"].val
                    if self.mode == "SIMULATION":
                        ax1 = int(px_x - atk_range * (820 / 1200))
                        ax2 = int(px_x + atk_range * (820 / 1200))
                        dx1 = int(px_x - det_range * (820 / 1200))
                        dx2 = int(px_x + det_range * (820 / 1200))
                    else:
                        ax1 = px_x - int(atk_range * self.preview_scale)
                        ax2 = px_x + int(atk_range * self.preview_scale)
                        dx1 = px_x - int(det_range * self.preview_scale)
                        dx2 = px_x + int(det_range * self.preview_scale)
                    pg.draw.line(screen, (231, 76, 60), (ax1, 420 - 10), (ax1, 420 + 10), 2)
                    pg.draw.line(screen, (231, 76, 60), (ax2, 420 - 10), (ax2, 420 + 10), 2)
                    pg.draw.line(screen, (0, 145, 234), (dx1, 420 - 5), (dx1, 420 + 5), 1)
                    pg.draw.line(screen, (0, 145, 234), (dx2, 420 - 5), (dx2, 420 + 5), 1)

            elif self.mode == "ANALYTICS":
                self.draw_analytics_dashboard(screen, preview_rect)

            # Draw bottom controls depending on mode
            if self.mode == "REVIEW":
                for btn in self.review_buttons:
                    btn.draw(screen)
            elif self.mode == "SIMULATION":
                self.restart_sim_btn.draw(screen)
            elif self.mode == "ANALYTICS":
                for btn in self.analytics_buttons:
                    btn.draw(screen)

            # Draw Mode Switcher Buttons
            for btn in self.mode_buttons:
                btn.draw(screen)

            # Draw Auto-Fit options & Sliders
            if self.mode != "ANALYTICS":
                self.autofit_btn.draw(screen)
                self.apply_fit_btn.draw(screen)
                
                self.playback_speed_slider.draw(screen)

                if self.auto_fit_enabled:
                    val_display = f"{round(self.preview_scale, 2)}x [AUTO]"
                    txt_label = ui_font.render("Preview Scale", True, TEXT_MUTED)
                    txt_val = value_font.render(val_display, True, TEXT_MUTED)
                    screen.blit(txt_label, (920, 610 - 20))
                    screen.blit(txt_val, (1220 - txt_val.get_width(), 610 - 20))
                    pg.draw.rect(screen, (30, 30, 35), (920, 610, 300, 8), border_radius=4)
                else:
                    self.preview_scale_slider.draw(screen)

            # Toast messages
            if self.toast_timer > 0.0:
                self.toast_timer -= dt
                toast_surf = pg.Surface((320, 45), pg.SRCALPHA)
                pg.draw.rect(toast_surf, (24, 40, 24, 220) if "Saved" in self.toast_message or "Applied" in self.toast_message or "Refreshed" in self.toast_message or "Loaded" in self.toast_message else (40, 24, 24, 220), (0, 0, 320, 45), border_radius=6)
                pg.draw.rect(toast_surf, (46, 204, 113) if "Saved" in self.toast_message or "Applied" in self.toast_message or "Refreshed" in self.toast_message or "Loaded" in self.toast_message else (231, 76, 60), (0, 0, 320, 45), width=1, border_radius=6)
                txt_toast = ui_font.render(self.toast_message, True, (255, 255, 255))
                toast_surf.blit(txt_toast, txt_toast.get_rect(center=(160, 22)))
                screen.blit(toast_surf, (910, 20))

            # Render Confirmation overlays
            if self.confirming_save or self.confirming_sim_reset:
                overlay = pg.Surface((SCREEN_W, SCREEN_H), pg.SRCALPHA)
                overlay.fill((10, 10, 15, 220))
                screen.blit(overlay, (0, 0))

                dialog_w, dialog_h = 500, 200
                dialog_x = (SCREEN_W - dialog_w) // 2
                dialog_y = (SCREEN_H - dialog_h) // 2
                dialog_rect = pg.Rect(dialog_x, dialog_y, dialog_w, dialog_h)
                
                pg.draw.rect(screen, PANEL_BG, dialog_rect, border_radius=12)
                pg.draw.rect(screen, ACCENT_CYAN, dialog_rect, width=2, border_radius=12)

                if self.confirming_save:
                    title_str = "SAVE CONFIGURATION?"
                    cfg_file = os.path.basename(self.bosses[self.selected_boss]["schema"]["config_file"])
                    desc_str = f"Write dynamic parameters to {cfg_file}?"
                else:
                    title_str = "RESTART AI SIMULATION?"
                    desc_str = "Reset mock entities and logs to start positions?"

                txt_m_title = title_font.render(title_str, True, ACCENT_CYAN)
                txt_m_desc = ui_font.render(desc_str, True, TEXT_COLOR)
                
                screen.blit(txt_m_title, txt_m_title.get_rect(centerx=dialog_rect.centerx, y=dialog_rect.y + 30))
                screen.blit(txt_m_desc, txt_m_desc.get_rect(centerx=dialog_rect.centerx, y=dialog_rect.y + 75))

                m_pos = pg.mouse.get_pos()
                confirm_btn_rect = pg.Rect(dialog_x + 40, dialog_y + 120, 180, 42)
                cancel_btn_rect = pg.Rect(dialog_x + 280, dialog_y + 120, 180, 42)

                c_hover = confirm_btn_rect.collidepoint(m_pos)
                x_hover = cancel_btn_rect.collidepoint(m_pos)

                c_color = (46, 204, 113) if c_hover else (39, 174, 96)
                x_color = (231, 76, 60) if x_hover else (192, 57, 43)

                pg.draw.rect(screen, c_color, confirm_btn_rect, border_radius=6)
                pg.draw.rect(screen, x_color, cancel_btn_rect, border_radius=6)

                lbl_c = ui_font.render("CONFIRM (ENTER)", True, (255, 255, 255))
                lbl_x = ui_font.render("CANCEL (ESC)", True, (255, 255, 255))

                screen.blit(lbl_c, lbl_c.get_rect(center=confirm_btn_rect.center))
                screen.blit(lbl_x, lbl_x.get_rect(center=cancel_btn_rect.center))

            pg.display.flip()

        pg.quit()

if __name__ == "__main__":
    app = BossEditorApp()
    app.run()
