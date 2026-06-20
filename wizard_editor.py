#!/usr/bin/env python3
"""
wizard_editor.py
An interactive, dark-themed configuration editor, animation visualizer,
and telemetry-based AI difficulty scaling manager for the Fire Wizard boss.
"""

import os
import sys
import json
import random
import pygame as pg
from typing import Any, Optional, Dict, List

# Add path mapping to allow importing from src package
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from src.game.debug.telemetry_log_parser import TelemetryLogParser
from src.game.boss.difficulty_manager import DifficultyManager
from src.game.editor.preview_scaler import PreviewScaler

# Initialize Pygame and font systems
pg.init()
pg.font.init()

SCREEN_W, SCREEN_H = 1280, 720
screen = pg.display.set_mode((SCREEN_W, SCREEN_H))
pg.display.set_caption("Fire Wizard Boss: AI Configurator & Telemetry Plugin")

# Load Fonts
try:
    title_font = pg.font.Font("assets/graphics/Darinia/Darinia.ttf", 28)
    ui_font = pg.font.Font("assets/graphics/Darinia/Darinia.ttf", 16)
    value_font = pg.font.Font("assets/graphics/Darinia/Darinia.ttf", 14)
    help_font = pg.font.SysFont("Consolas", 14)
except Exception:
    title_font = pg.font.SysFont("Arial", 26, bold=True)
    ui_font = pg.font.SysFont("Arial", 16, bold=True)
    value_font = pg.font.SysFont("Arial", 14)
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
        # Label & Value text
        val_display = self.format_str.format(val=round(self.val, 2) if self.is_float else int(self.val))
        txt_label = ui_font.render(self.label, True, TEXT_COLOR)
        txt_val = value_font.render(val_display, True, ACCENT_CYAN)
        
        surface.blit(txt_label, (self.rect.x, self.rect.y - 22))
        surface.blit(txt_val, (self.rect.right - txt_val.get_width(), self.rect.y - 22))

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


class WizardEditorApp:
    def __init__(self):
        self.clock = pg.time.Clock()
        self.running = True
        
        self.config_path = "game_data/boss_wizard_config.json"
        self.load_config()

        # Build Sliders for AI Configurations
        self.sliders: Dict[str, Slider] = {
            "max_mana": Slider("max_mana", "Max Mana Pool", 40, 100, 320, 50, 200, self.config["max_mana"], is_float=True, format_str="{val} mp"),
            "spell_mana_cost": Slider("spell_mana_cost", "Spell Cost", 40, 160, 320, 10, 100, self.config["spell_mana_cost"], is_float=True, format_str="{val} mp"),
            "stagnant_duration": Slider("stagnant_duration", "Stagnant/Exhausted Time", 40, 220, 320, 0.5, 6.0, self.config["stagnant_duration"], is_float=True, format_str="{val} sec"),
            "teleport_dist_min": Slider("teleport_dist_min", "Teleport Min Dist", 40, 280, 320, 100, 600, self.config["teleport_dist_min"], is_float=False, format_str="{val} px"),
            "teleport_dist_max": Slider("teleport_dist_max", "Teleport Max Dist", 40, 340, 320, 400, 1000, self.config["teleport_dist_max"], is_float=False, format_str="{val} px"),
            "mana_recharge_rate": Slider("mana_recharge_rate", "Mana Recharge Rate", 40, 400, 320, 10, 100, self.config["mana_recharge_rate"], is_float=True, format_str="{val}/sec"),
            "chase_delay_duration": Slider("chase_delay_duration", "Chase Delay Window", 40, 460, 320, 0.0, 3.0, self.config["chase_delay_duration"], is_float=True, format_str="{val} sec"),
            "attack_cooldown_min": Slider("attack_cooldown_min", "Min Spell Cooldown", 40, 520, 320, 0.5, 4.0, self.config["attack_cooldown_min"], is_float=True, format_str="{val} sec"),
            "attack_cooldown_max": Slider("attack_cooldown_max", "Max Spell Cooldown", 40, 580, 320, 1.0, 6.0, self.config["attack_cooldown_max"], is_float=True, format_str="{val} sec"),
        }

        # Action Buttons
        self.action_buttons = [
            Button("SAVE CONFIG", 40, 640, 150, 42, self.request_save_config, active=True),
            Button("RESET DEFAULT", 210, 640, 150, 42, self.reset_defaults),
        ]

        self.confirming_save = False
        self.confirming_sim_reset = False
        self.toast_message = ""
        self.toast_timer = 0.0

        # Load Animation Sprites
        self.animations: Dict[str, List[pg.Surface]] = {}
        self.anim_states = ["IDLE", "CHASE", "ATTACK", "HURT", "DEATH"]
        self.current_state = "IDLE"
        self.load_animations()

        # Animation Playback State
        self.frame_index = 0.0
        self.play_speed = 1.0
        self.is_playing = True
        self.preview_scale = 4.11

        # Interactive Mode State
        # "REVIEW" - Loop single animation.
        # "SIMULATION" - Run wizard AI loop against a mock player.
        # "ANALYTICS" - View telemetry dashboards & auto-tune difficulty.
        self.mode = "REVIEW"
        self.init_simulation_state()

        # Review Control UI Elements (Adjusted Y to fit the new mode selector)
        self.review_buttons = [
            Button("IDLE", 450, 560, 80, 35, lambda: self.set_review_state("IDLE")),
            Button("CHASE", 540, 560, 80, 35, lambda: self.set_review_state("CHASE")),
            Button("ATTACK", 630, 560, 80, 35, lambda: self.set_review_state("ATTACK")),
            Button("HURT", 720, 560, 80, 35, lambda: self.set_review_state("HURT")),
            Button("DEATH", 810, 560, 80, 35, lambda: self.set_review_state("DEATH")),
        ]
        self.update_review_buttons()

        # Mode Buttons (Y adjusted to 500, horizontally aligned)
        self.mode_buttons = [
            Button("ANIMATION LOOP", 430, 500, 220, 40, lambda: self.set_mode("REVIEW")),
            Button("AI FLOW SIMULATION", 670, 500, 220, 40, lambda: self.set_mode("SIMULATION")),
            Button("DIFFICULTY TUNER", 910, 500, 220, 40, lambda: self.set_mode("ANALYTICS")),
        ]
        self.update_mode_buttons()

        self.restart_sim_btn = Button("RESTART SIMULATION", 450, 560, 200, 35, self.request_sim_reset)

        # Visualizer Play/Pause & Scale Sliders
        self.preview_scale_slider = Slider("scale", "Preview Scale", 920, 610, 300, 1.0, 6.0, self.preview_scale, is_float=True, format_str="{val}x")
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

        # Analytics Dashboard Preset Buttons:
        # 1. REFRESH LOGS
        # 2. Left Arrow [ < LOWER ]
        # 3. Right Arrow [ HIGHER > ]
        # 4. PRESET 1
        # 5. PRESET 2
        # 6. PRESET 3
        # 7. SAVE PRESET
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

    def apply_recommended_difficulty(self):
        if not self.recent_sessions_analytics or self.recent_sessions_analytics.get("valid_session_count", 0) == 0:
            self.toast_message = "No recommendation available!"
            self.toast_timer = 2.0
            return
        
        rec_diff = self.recent_sessions_analytics.get("recommended_difficulty")
        if rec_diff in ("EASY", "MEDIUM", "HARD", "NIGHTMARE"):
            preset_config = self.difficulty_manager.get_preset_config(rec_diff)
            for key, val in preset_config.items():
                if key in self.sliders:
                    self.sliders[key].val = val
            self.toast_message = f"Applied Recommended {rec_diff} Preset!"
            self.toast_timer = 2.0
        else:
            self.toast_message = "Invalid recommended difficulty!"
            self.toast_timer = 2.0

    def adjust_difficulty(self, direction: int):
        current_config = {k: slider.val for k, slider in self.sliders.items()}
        new_config = self.difficulty_manager.adjust_difficulty_level(current_config, direction)
        for k, val in new_config.items():
            if k in self.sliders:
                self.sliders[k].val = val
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
        self.parsed_files_count = sum(len(paths) for _, paths in recent)
        self.toast_message = "Telemetry Logs Refreshed!"
        self.toast_timer = 2.0

    def load_config(self):
        defaults = {
            "max_mana": 100.0,
            "spell_mana_cost": 35.0,
            "stagnant_duration": 3.0,
            "teleport_dist_min": 380,
            "teleport_dist_max": 450,
            "mana_recharge_rate": 50.0,
            "chase_delay_duration": 0.8,
            "attack_cooldown_min": 1.2,
            "attack_cooldown_max": 2.0
        }
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r") as f:
                    self.config = json.load(f)
                    # merge defaults for missing values
                    for k, v in defaults.items():
                        if k not in self.config:
                            self.config[k] = v
            except Exception:
                self.config = defaults.copy()
        else:
            self.config = defaults.copy()

    def request_save_config(self):
        self.confirming_save = True

    def confirm_save_config(self):
        # Update config dictionary from slider values
        for k, slider in self.sliders.items():
            self.config[k] = slider.val
        
        # Enforce ordering constraints
        if self.config["teleport_dist_max"] < self.config["teleport_dist_min"]:
            self.config["teleport_dist_max"] = self.config["teleport_dist_min"]
            self.sliders["teleport_dist_max"].val = self.config["teleport_dist_min"]
            
        if self.config["attack_cooldown_max"] < self.config["attack_cooldown_min"]:
            self.config["attack_cooldown_max"] = self.config["attack_cooldown_min"]
            self.sliders["attack_cooldown_max"].val = self.config["attack_cooldown_min"]

        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        # Create timestamped backup of current file
        if os.path.exists(self.config_path):
            try:
                import shutil
                from datetime import datetime
                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_path = f"game_data/boss_wizard_config.backup_{ts}.json"
                shutil.copy2(self.config_path, backup_path)
                print(f"[INFO] Created config backup at {backup_path}")
            except Exception as e:
                print(f"[WARNING] Failed to create backup: {e}")

        try:
            with open(self.config_path, "w") as f:
                json.dump(self.config, f, indent=2)
            self.toast_message = "Configuration Saved!"
            self.toast_timer = 2.0
            print("[INFO] Configuration saved successfully.")
        except Exception as e:
            self.toast_message = "Save Failed!"
            self.toast_timer = 2.0
            print(f"[ERROR] Failed to save config: {e}")

    def reset_defaults(self):
        for k, v in self.difficulty_manager.BASELINE_CONFIG.items():
            if k in self.sliders:
                self.sliders[k].val = v
        self.toast_message = "Defaults Loaded (Press Save)"
        self.toast_timer = 2.0

    def request_sim_reset(self):
        self.confirming_sim_reset = True

    def load_animations(self):
        paths = {
            "IDLE": ("assets/wizard/Idle/wizard_idle{}.png", 8),
            "CHASE": ("assets/wizard/Move/wizard_run{}.png", 8),
            "ATTACK": ("assets/wizard/Attack/wizard_atk1{}.png", 8),
            "HURT": ("assets/wizard/Hurt/wizard_hurt{}.png", 4),
            "DEATH": ("assets/wizard/Death/wizard_death{}.png", 4),
        }
        
        for state, (pattern, count) in paths.items():
            frames = []
            for i in range(count):
                f_path = pattern.format(i)
                if os.path.exists(f_path):
                    frames.append(pg.image.load(f_path).convert_alpha())
                else:
                    # fallback dummy surf
                    dummy = pg.Surface((150, 150), pg.SRCALPHA)
                    pg.draw.rect(dummy, (255, 0, 100), (40, 40, 70, 70), 2)
                    frames.append(dummy)
            self.animations[state] = frames

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
        self.sim_player_x = 100
        self.sim_boss_x = 400
        self.sim_boss_state = "CHASE"
        self.sim_boss_mana = self.sliders["max_mana"].val
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
        self.sim_boss_facing_left = False
        self.sim_events = ["Simulation started."]
        self.sim_fireballs = []

    def add_sim_log(self, text: str):
        self.sim_events.append(text)
        if len(self.sim_events) > 8:
            self.sim_events.pop(0)

    def update_simulation(self, dt: float):
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
                self.add_sim_log("Fireball HIT mock player!")

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
        frames_count = len(self.animations[self.sim_boss_state])
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
                self.add_sim_log(f"Fireball cast! Mana consumed (-{spell_cost:.1f}). Remaining: {self.sim_boss_mana:.1f}")

        # AI State Machine Decision Tree
        if self.sim_boss_state == "ATTACK" or self.sim_boss_state == "HURT":
            return

        # 1. Low mana stagnant check
        if self.sim_boss_mana < spell_cost and not self.sim_boss_is_recharging and not self.sim_boss_is_stagnant:
            self.sim_boss_is_stagnant = True
            self.sim_boss_stagnant_timer = stagnant_duration
            self.sim_boss_state = "IDLE"
            self.add_sim_log(f"Low mana! Exhausted/Stagnant for {stagnant_duration:.1f}s")
            return

        if self.sim_boss_is_stagnant:
            self.sim_boss_state = "IDLE"
            if random.random() < 0.015:
                self.add_sim_log("Player attacked boss while stagnant!")
                self.sim_boss_state = "HURT"
                self.frame_index = 0.0
                self.sim_boss_teleport_after_hurt = True
            return

        if self.sim_boss_is_recharging:
            self.sim_boss_state = "IDLE"
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
            ("Wizard Attack Count", f"{int(metrics.get('boss_attacks', 0))}"),
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
            curr_y += 24

        divider2_y = content_y + 230
        pg.draw.line(surface, BORDER_COLOR, (start_x, divider2_y), (rect.right - margin_x, divider2_y), 1)

        rec_y = divider2_y + 15
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
        surface.blit(txt_desc, (start_x, rec_y + 25))

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
                    frames_count = len(self.animations[self.current_state])
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
            txt_title = title_font.render("WIZARD CONFIG EDITOR", True, TEXT_COLOR)
            screen.blit(txt_title, (30, 30))

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
                title_str = "ANIMATION PREVIEW LOOP"
            elif self.mode == "SIMULATION":
                title_str = "BOSS AI BEHAVIOR SIMULATOR"
            else:
                title_str = "TELEMETRY LOG ANALYTICS & DIFFICULTY TUNER"
            txt_preview_title = title_font.render(title_str, True, TEXT_COLOR)
            screen.blit(txt_preview_title, (430, 35))

            if self.mode in ("REVIEW", "SIMULATION"):
                state_key = self.current_state if self.mode == "REVIEW" else self.sim_boss_state
                frames = self.animations[state_key]
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

                scaled_frame = pg.transform.scale(current_frame, (scaled_w, scaled_h))

                if self.mode == "SIMULATION" and self.sim_boss_facing_left:
                    scaled_frame = pg.transform.flip(scaled_frame, True, False)

                # Draw floor
                pg.draw.line(screen, (75, 75, 100), (430, 420), (1250, 420), 3)

                if self.mode == "SIMULATION" and self.sim_boss_teleport_flash_timer > 0.0:
                    alpha = 80 if int(self.sim_boss_teleport_flash_timer * 30) % 2 == 0 else 180
                    scaled_frame.set_alpha(alpha)
                else:
                    scaled_frame.set_alpha(255)

                screen.blit(scaled_frame, (px_x - scaled_w // 2, px_y))

                if self.mode == "SIMULATION" and self.sim_boss_is_recharging:
                    glow_radius = int(55 + 5 * random.random())
                    aura = pg.Surface((glow_radius * 2, glow_radius * 2), pg.SRCALPHA)
                    pg.draw.circle(aura, (0, 229, 255, 60), (glow_radius, glow_radius), glow_radius)
                    screen.blit(aura, (px_x - glow_radius, 420 - int(scaled_h * 0.36) - glow_radius))

                if self.mode == "SIMULATION":
                    p_px_x = int(430 + (self.sim_player_x / 1200) * 820)
                    pg.draw.circle(screen, (100, 255, 100), (p_px_x, 420 - 35), 18)
                    pg.draw.rect(screen, (80, 200, 80), (p_px_x - 6, 420 - 20, 12, 20))
                    txt_lbl = help_font.render("PLAYER (MOUSE)", True, (100, 255, 100))
                    screen.blit(txt_lbl, (p_px_x - txt_lbl.get_width() // 2, 420 - 70))

                    for fb in self.sim_fireballs:
                        fb_x = int(430 + (fb["x"] / 1200) * 820)
                        pg.draw.circle(screen, (255, 100, 0), (fb_x, fb["y"]), 8)
                        pg.draw.circle(screen, (255, 200, 0), (fb_x, fb["y"]), 5)

                    bar_w = 80
                    bar_h = 6
                    bx_y = 420 - scaled_h - 20
                    pg.draw.rect(screen, (255, 50, 50), (px_x - bar_w // 2, bx_y, bar_w, bar_h), border_radius=3)
                    mana_ratio = self.sim_boss_mana / self.sliders["max_mana"].val
                    pg.draw.rect(screen, (33, 150, 243), (px_x - bar_w // 2, bx_y + 9, int(bar_w * mana_ratio), bar_h), border_radius=3)
                    pg.draw.rect(screen, (60, 60, 60), (px_x - bar_w // 2, bx_y + 9, bar_w, bar_h), width=1, border_radius=3)

                    log_y = 95
                    for ev in self.sim_events:
                        txt_ev = help_font.render(ev, True, ACCENT_CYAN if "TELEPORTED" in ev or "recharged" in ev else TEXT_COLOR)
                        screen.blit(txt_ev, (450, log_y))
                        log_y += 18

                    bound_1 = int(px_x - 260 * (820 / 1200))
                    bound_2 = int(px_x - 120 * (820 / 1200))
                    bound_3 = int(px_x + 120 * (820 / 1200))
                    bound_4 = int(px_x + 260 * (820 / 1200))
                    pg.draw.line(screen, (60, 60, 80), (bound_1, 420 - 15), (bound_1, 420 + 15), 1)
                    pg.draw.line(screen, (60, 60, 80), (bound_2, 420 - 15), (bound_2, 420 + 15), 1)
                    pg.draw.line(screen, (60, 60, 80), (bound_3, 420 - 15), (bound_3, 420 + 15), 1)
                    pg.draw.line(screen, (60, 60, 80), (bound_4, 420 - 15), (bound_4, 420 + 15), 1)

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
                    screen.blit(txt_label, (920, 610 - 22))
                    screen.blit(txt_val, (1220 - txt_val.get_width(), 610 - 22))
                    pg.draw.rect(screen, (30, 30, 35), (920, 610, 300, 8), border_radius=4)
                else:
                    self.preview_scale_slider.draw(screen)

            # Toast messages
            if self.toast_timer > 0.0:
                self.toast_timer -= dt
                toast_surf = pg.Surface((320, 45), pg.SRCALPHA)
                pg.draw.rect(toast_surf, (24, 40, 24, 220) if "Saved" in self.toast_message or "Applied" in self.toast_message or "Refreshed" in self.toast_message else (40, 24, 24, 220), (0, 0, 320, 45), border_radius=6)
                pg.draw.rect(toast_surf, (46, 204, 113) if "Saved" in self.toast_message or "Applied" in self.toast_message or "Refreshed" in self.toast_message else (231, 76, 60), (0, 0, 320, 45), width=1, border_radius=6)
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
                    desc_str = "Write dynamic parameters to boss_wizard_config.json?"
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
    app = WizardEditorApp()
    app.run()
