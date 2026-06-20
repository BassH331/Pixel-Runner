#!/usr/bin/env python3
"""
wizard_editor.py
An interactive, dark-themed configuration editor and animation visualizer/simulator for the Fire Wizard boss.
"""

import os
import sys
import json
import random
import pygame as pg
from typing import Any, Optional, Dict, List

# Initialize Pygame and font systems
pg.init()
pg.font.init()

SCREEN_W, SCREEN_H = 1280, 720
screen = pg.display.set_mode((SCREEN_W, SCREEN_H))
pg.display.set_caption("Fire Wizard Boss: AI Configurator & Animator")

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
        self.mode = "REVIEW"
        self.init_simulation_state()

        # Review Control UI Elements
        self.review_buttons = [
            Button("IDLE", 450, 520, 100, 35, lambda: self.set_review_state("IDLE")),
            Button("CHASE", 560, 520, 100, 35, lambda: self.set_review_state("CHASE")),
            Button("ATTACK", 670, 520, 100, 35, lambda: self.set_review_state("ATTACK")),
            Button("HURT", 780, 520, 100, 35, lambda: self.set_review_state("HURT")),
            Button("DEATH", 890, 520, 100, 35, lambda: self.set_review_state("DEATH")),
        ]
        self.update_review_buttons()

        # Mode Buttons
        self.mode_buttons = [
            Button("ANIMATION LOOP", 450, 600, 200, 40, lambda: self.set_mode("REVIEW")),
            Button("AI FLOW SIMULATION", 680, 600, 200, 40, lambda: self.set_mode("SIMULATION")),
        ]
        self.update_mode_buttons()

        self.restart_sim_btn = Button("RESTART SIMULATION", 450, 650, 200, 35, self.request_sim_reset)

        # Visualizer Play/Pause & Scale Sliders
        self.preview_scale_slider = Slider("scale", "Preview Scale", 920, 610, 300, 1.0, 6.0, self.preview_scale, is_float=True, format_str="{val}x")
        self.playback_speed_slider = Slider("speed", "Playback Speed", 920, 670, 300, 0.2, 3.0, self.play_speed, is_float=True, format_str="{val}x")

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
        try:
            with open(self.config_path, "w") as f:
                json.dump(self.config, f, indent=2)
            self.toast_message = "Configuration Saved!"
            self.toast_timer = 2.0
            print("[INFO] Configuration saved successfully.")
        except Exception as e:
            self.toast_message = "Save Failed!"
            self.toast_timer = 2.0
            print("[ERROR] Failed to save config: {e}")

    def reset_defaults(self):
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
        for k, v in defaults.items():
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

    def update_review_buttons(self):
        for btn in self.review_buttons:
            btn.active = (btn.text == self.current_state)

    def update_mode_buttons(self):
        for btn in self.mode_buttons:
            if btn.text == "ANIMATION LOOP" and self.mode == "REVIEW":
                btn.active = True
            elif btn.text == "AI FLOW SIMULATION" and self.mode == "SIMULATION":
                btn.active = True
            else:
                btn.active = False

    def init_simulation_state(self):
        # Simulation entities
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
        
        # Log of events in simulator
        self.sim_events: List[str] = ["Simulation started."]
        
        # Fireballs spawned during simulation
        self.sim_fireballs: List[Dict[str, Any]] = []

    def add_sim_log(self, text: str):
        self.sim_events.append(text)
        if len(self.sim_events) > 8:
            self.sim_events.pop(0)

    def update_simulation(self, dt: float):
        # Gather latest parameters from sliders
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
            # remove out of bounds
            if abs(fb["x"] - self.sim_boss_x) > 600:
                self.sim_fireballs.remove(fb)
            # Collision with mock player
            elif abs(fb["x"] - self.sim_player_x) < 20:
                self.sim_fireballs.remove(fb)
                self.add_sim_log("Fireball HIT mock player!")
                # Stagger the player (mock visual effect)

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
                # Timer expired! Teleport anyway to recharge
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
                # attack anim finished
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
        if self.sim_boss_state == "ATTACK":
            return # Locked in attack animation

        if self.sim_boss_state == "HURT":
            return # Locked in hurt animation

        # 1. Low mana stagnant check
        if self.sim_boss_mana < spell_cost and not self.sim_boss_is_recharging and not self.sim_boss_is_stagnant:
            self.sim_boss_is_stagnant = True
            self.sim_boss_stagnant_timer = stagnant_duration
            self.sim_boss_state = "IDLE"
            self.add_sim_log(f"Low mana! Exhausted/Stagnant for {stagnant_duration:.1f}s")
            return

        if self.sim_boss_is_stagnant:
            self.sim_boss_state = "IDLE"
            # Random player attack simulation during stagnant phase (e.g. 1.5% chance per frame)
            if random.random() < 0.015:
                self.add_sim_log("Player attacked boss while stagnant!")
                self.sim_boss_state = "HURT"
                self.frame_index = 0.0
                self.sim_boss_teleport_after_hurt = True
            return

        if self.sim_boss_is_recharging:
            self.sim_boss_state = "IDLE"
            return

        # Regular combat movement & sweet-spot
        dist_x = self.sim_boss_x - self.sim_player_x
        abs_dist_x = abs(dist_x)
        self.sim_boss_facing_left = (dist_x > 0)

        # Sweet spot check (between 120 and 260px)
        if 120 <= abs_dist_x <= 260:
            if self.sim_boss_attack_cooldown <= 0.0 and self.sim_boss_mana >= spell_cost:
                # Begin attack!
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
            # Clamp limits
            self.sim_boss_x = max(100, min(1180, self.sim_boss_x))

        # Chase if player is too far
        elif abs_dist_x > 260:
            # Player ran away: trigger Chase Delay
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
        
        # Teleport offset
        dist_offset = random.randint(int(teleport_min), int(teleport_max))
        if self.sim_boss_x > self.sim_player_x:
            target_x = self.sim_player_x + dist_offset
        else:
            target_x = self.sim_player_x - dist_offset
            
        self.sim_boss_x = max(100, min(1180, target_x))
        self.sim_boss_state = "IDLE"
        self.frame_index = 0.0
        self.add_sim_log(f"TELEPORTED to x={self.sim_boss_x}! Starting mana recharge.")

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
                for btn in self.review_buttons:
                    btn.handle_event(event)
                for btn in self.mode_buttons:
                    btn.handle_event(event)
                if self.mode == "SIMULATION":
                    self.restart_sim_btn.handle_event(event)
                self.preview_scale_slider.handle_event(event)
                self.playback_speed_slider.handle_event(event)

            # Update live settings if not in modal
            if not self.confirming_save and not self.confirming_sim_reset:
                self.preview_scale = self.preview_scale_slider.val
                self.play_speed = self.playback_speed_slider.val

            # 2. Update logic based on Mode
            if not self.confirming_save and not self.confirming_sim_reset:
                if self.mode == "REVIEW":
                    frames_count = len(self.animations[self.current_state])
                    self.frame_index += self.play_speed * 10 * dt
                    if self.frame_index >= frames_count:
                        self.frame_index = 0.0
                else:
                    # Interactive mock player control using mouse in preview container
                    m_pos = pg.mouse.get_pos()
                    # If mouse inside preview rect (x: 430-1250, y: 80-480)
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
            txt_preview_title = title_font.render(
                "ANIMATION PREVIEW LOOP" if self.mode == "REVIEW" else "BOSS AI BEHAVIOR SIMULATOR",
                True, TEXT_COLOR
            )
            screen.blit(txt_preview_title, (430, 35))

            # Render the Wizard sprite
            state_key = self.current_state if self.mode == "REVIEW" else self.sim_boss_state
            frames = self.animations[state_key]
            current_frame = frames[min(int(self.frame_index), len(frames) - 1)]

            # Apply scale transformation
            w, h = current_frame.get_size()
            scaled_w = int(w * self.preview_scale)
            scaled_h = int(h * self.preview_scale)
            scaled_frame = pg.transform.scale(current_frame, (scaled_w, scaled_h))

            # Mirror based on direction
            if self.mode == "SIMULATION" and self.sim_boss_facing_left:
                scaled_frame = pg.transform.flip(scaled_frame, True, False)

            # Get target drawing position (floor aligned)
            # Floor visual y = 420
            floor_y = 420
            px_x = 840 if self.mode == "REVIEW" else int(430 + (self.sim_boss_x / 1200) * 820)
            px_y = floor_y - int(scaled_h * 0.72) # offset origin

            # Draw visual floor line in preview
            pg.draw.line(screen, (75, 75, 100), (430, floor_y), (1250, floor_y), 3)

            # Teleport flash transparency
            if self.mode == "SIMULATION" and self.sim_boss_teleport_flash_timer > 0.0:
                alpha = 80 if int(self.sim_boss_teleport_flash_timer * 30) % 2 == 0 else 180
                scaled_frame.set_alpha(alpha)
            else:
                scaled_frame.set_alpha(255)

            # Blit Wizard
            screen.blit(scaled_frame, (px_x - scaled_w // 2, px_y))

            # Draw recharge aura if recharging
            if self.mode == "SIMULATION" and self.sim_boss_is_recharging:
                glow_radius = int(55 + 5 * random.random())
                # transparent cyan circle overlay
                aura = pg.Surface((glow_radius * 2, glow_radius * 2), pg.SRCALPHA)
                pg.draw.circle(aura, (0, 229, 255, 60), (glow_radius, glow_radius), glow_radius)
                screen.blit(aura, (px_x - glow_radius, floor_y - int(scaled_h * 0.36) - glow_radius))

            # Render Mock Player in Simulation mode
            if self.mode == "SIMULATION":
                p_px_x = int(430 + (self.sim_player_x / 1200) * 820)
                # simple player avatar
                pg.draw.circle(screen, (100, 255, 100), (p_px_x, floor_y - 35), 18)
                pg.draw.rect(screen, (80, 200, 80), (p_px_x - 6, floor_y - 20, 12, 20))
                # Label
                txt_lbl = help_font.render("PLAYER (MOUSE)", True, (100, 255, 100))
                screen.blit(txt_lbl, (p_px_x - txt_lbl.get_width() // 2, floor_y - 70))

                # Draw simulated Fireballs
                for fb in self.sim_fireballs:
                    fb_x = int(430 + (fb["x"] / 1200) * 820)
                    pg.draw.circle(screen, (255, 100, 0), (fb_x, fb["y"]), 8)
                    pg.draw.circle(screen, (255, 200, 0), (fb_x, fb["y"]), 5)

                # Render health/mana bars above boss
                bar_w = 80
                bar_h = 6
                bx_y = floor_y - scaled_h - 20
                # health bar (mock full)
                pg.draw.rect(screen, (255, 50, 50), (px_x - bar_w // 2, bx_y, bar_w, bar_h), border_radius=3)
                # mana bar
                mana_ratio = self.sim_boss_mana / self.sliders["max_mana"].val
                pg.draw.rect(screen, (33, 150, 243), (px_x - bar_w // 2, bx_y + 9, int(bar_w * mana_ratio), bar_h), border_radius=3)
                pg.draw.rect(screen, (60, 60, 60), (px_x - bar_w // 2, bx_y + 9, bar_w, bar_h), width=1, border_radius=3)

                # Draw telemetry logs
                log_y = 95
                for ev in self.sim_events:
                    txt_ev = help_font.render(ev, True, ACCENT_CYAN if "TELEPORTED" in ev or "recharged" in ev else TEXT_COLOR)
                    screen.blit(txt_ev, (450, log_y))
                    log_y += 18

                # Draw sweet spot bounds lines
                bound_1 = int(px_x - 260 * (820 / 1200))
                bound_2 = int(px_x - 120 * (820 / 1200))
                bound_3 = int(px_x + 120 * (820 / 1200))
                bound_4 = int(px_x + 260 * (820 / 1200))
                
                pg.draw.line(screen, (60, 60, 80), (bound_1, floor_y - 15), (bound_1, floor_y + 15), 1)
                pg.draw.line(screen, (60, 60, 80), (bound_2, floor_y - 15), (bound_2, floor_y + 15), 1)
                pg.draw.line(screen, (60, 60, 80), (bound_3, floor_y - 15), (bound_3, floor_y + 15), 1)
                pg.draw.line(screen, (60, 60, 80), (bound_4, floor_y - 15), (bound_4, floor_y + 15), 1)

            # Draw panel controls depending on Mode
            if self.mode == "REVIEW":
                for btn in self.review_buttons:
                    btn.draw(screen)
            else:
                self.restart_sim_btn.draw(screen)
            for btn in self.mode_buttons:
                btn.draw(screen)

            # Draw scale & speed sliders
            self.preview_scale_slider.draw(screen)
            self.playback_speed_slider.draw(screen)

            # Draw Toast Messages if active
            if self.toast_timer > 0.0:
                self.toast_timer -= dt
                toast_surf = pg.Surface((320, 45), pg.SRCALPHA)
                pg.draw.rect(toast_surf, (24, 40, 24, 220) if "Saved" in self.toast_message or "Loaded" in self.toast_message else (40, 24, 24, 220), (0, 0, 320, 45), border_radius=6)
                pg.draw.rect(toast_surf, (46, 204, 113) if "Saved" in self.toast_message or "Loaded" in self.toast_message else (231, 76, 60), (0, 0, 320, 45), width=1, border_radius=6)
                txt_toast = ui_font.render(self.toast_message, True, (255, 255, 255))
                toast_surf.blit(txt_toast, txt_toast.get_rect(center=(160, 22)))
                screen.blit(toast_surf, (910, 20))

            # Render Confirmation Overlays
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
