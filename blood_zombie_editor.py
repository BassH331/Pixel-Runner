#!/usr/bin/env python3
"""
blood_zombie_editor.py
An interactive, high-engine configuration editor, animation visualizer,
and behavior simulator for the Blood Zombie entity (Bloo Zombie).

Features:
- Per-frame pivot offsets (X, Y) and strike box (X, Y, W, H) fine-tuning.
- Stagnant Target Player Dummy with Hit Reaction State & Impact Detection.
- Onion Skinning (Ghost Frames) for evaluating animation motion fluidity.
- Dual English & Engineering Math Metaphors alongside formal parameters.
"""

from __future__ import annotations

import os
import sys
import json
import time
import math
import random
import pygame as pg
from typing import Any, Optional, Dict, List, Tuple

# Add path mapping to allow importing from src package
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from src.game.services import ConfigClient

# Initialize Pygame systems
pg.init()
pg.font.init()
try:
    pg.mixer.init()
except Exception:
    pass

SCREEN_W, SCREEN_H = 1280, 720
screen = pg.display.set_mode((SCREEN_W, SCREEN_H))
pg.display.set_caption("Blood Zombie Necro-Lab: Animation, Frame Pivot & Hitbox Curator")

# Load Fonts with clean UI fallbacks
try:
    title_font = pg.font.Font("assets/graphics/Darinia/Darinia.ttf", 22)
except Exception:
    title_font = pg.font.SysFont("Arial", 20, bold=True)

ui_font = pg.font.SysFont("DejaVu Sans", 13, bold=True)
if not ui_font:
    ui_font = pg.font.SysFont("Arial", 13, bold=True)

btn_font = pg.font.SysFont("DejaVu Sans", 11, bold=True)
value_font = pg.font.SysFont("Consolas", 12, bold=True)
help_font = pg.font.SysFont("Consolas", 12)
tooltip_font = pg.font.SysFont("Consolas", 11)

# Color Palette (Dark Sanguine Theme)
BG_COLOR = (14, 12, 18)
PANEL_BG = (24, 20, 30)
CANVAS_BG = (10, 8, 14)
ACCENT_BLOOD = (230, 35, 45)
ACCENT_CRIMSON = (180, 20, 30)
ACCENT_CYAN = (0, 229, 255)
ACCENT_PURPLE = (160, 60, 230)
ACCENT_GOLD = (255, 200, 50)
ACCENT_GREEN = (50, 220, 100)
TEXT_COLOR = (240, 240, 245)
TEXT_MUTED = (140, 130, 160)
BORDER_COLOR = (55, 45, 70)


class MetaphorSlider:
    """
    Slider control with integrated Sanguine Metaphor & Technical Math tooltip metadata.
    """
    def __init__(
        self,
        key: str,
        metaphor_label: str,
        tech_label: str,
        formula: str,
        x: int,
        y: int,
        w: int,
        min_val: float,
        max_val: float,
        current_val: float,
        is_float: bool = True,
        format_str: str = "{val}",
        unit: str = "",
    ):
        self.key = key
        self.metaphor_label = metaphor_label
        self.tech_label = tech_label
        self.formula = formula
        self.rect = pg.Rect(x, y + 16, w, 8)
        self.base_y = y
        self.handle_r = 8
        self.min_val = min_val
        self.max_val = max_val
        self.val = current_val
        self.dragging = False
        self.is_float = is_float
        self.format_str = format_str
        self.unit = unit
        self.hovered = False

    def get_handle_pos(self) -> Tuple[int, int]:
        if self.max_val == self.min_val:
            ratio = 0.0
        else:
            ratio = (self.val - self.min_val) / (self.max_val - self.min_val)
        return int(self.rect.x + ratio * self.rect.width), self.rect.centery

    def draw(self, surface: pg.Surface):
        val_display = self.format_str.format(
            val=round(self.val, 2) if self.is_float else int(self.val)
        ) + (f" {self.unit}" if self.unit else "")

        # Highlight if hovered
        m_pos = pg.mouse.get_pos()
        hx, hy = self.get_handle_pos()
        dist = math.hypot(m_pos[0] - hx, m_pos[1] - hy)
        self.hovered = dist <= self.handle_r + 4 or pg.Rect(self.rect.x, self.base_y, self.rect.width, 32).collidepoint(m_pos)

        label_color = ACCENT_BLOOD if self.hovered else TEXT_COLOR
        txt_label = ui_font.render(self.metaphor_label, True, label_color)
        txt_val = value_font.render(val_display, True, ACCENT_CYAN)

        surface.blit(txt_label, (self.rect.x, self.base_y - 2))
        surface.blit(txt_val, (self.rect.right - txt_val.get_width(), self.base_y - 2))

        # Slider track background
        pg.draw.rect(surface, (35, 30, 45), self.rect, border_radius=4)

        # Active fill track
        fill_rect = pg.Rect(self.rect.x, self.rect.y, max(0, hx - self.rect.x), self.rect.height)
        pg.draw.rect(surface, ACCENT_CRIMSON, fill_rect, border_radius=4)

        # Handle circle
        handle_color = (255, 255, 255) if not self.dragging else ACCENT_CYAN
        pg.draw.circle(surface, handle_color, (hx, hy), self.handle_r)
        pg.draw.circle(surface, ACCENT_BLOOD if not self.hovered else (255, 100, 100), (hx, hy), self.handle_r, 2)

    def handle_event(self, event: pg.event.Event):
        if event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
            hx, hy = self.get_handle_pos()
            m_pos = event.pos
            dist = math.hypot(m_pos[0] - hx, m_pos[1] - hy)
            if dist <= self.handle_r + 6 or pg.Rect(self.rect.x, self.base_y, self.rect.width, 32).collidepoint(m_pos):
                self.dragging = True
                self.update_val(m_pos[0])
        elif event.type == pg.MOUSEBUTTONUP and event.button == 1:
            self.dragging = False
        elif event.type == pg.MOUSEMOTION and self.dragging:
            self.update_val(event.pos[0])

    def update_val(self, mx: int):
        mx = max(self.rect.x, min(mx, self.rect.right))
        ratio = (mx - self.rect.x) / self.rect.width if self.rect.width > 0 else 0.0
        raw_val = self.min_val + ratio * (self.max_val - self.min_val)
        if self.is_float:
            self.val = round(raw_val, 2)
        else:
            self.val = int(round(raw_val))


class Button:
    def __init__(self, text: str, x: int, y: int, w: int, h: int, callback: Any, active: bool = False, color_accent: Optional[Tuple[int, int, int]] = None):
        self.text = text
        self.rect = pg.Rect(x, y, w, h)
        self.callback = callback
        self.active = active
        self.color_accent = color_accent or ACCENT_BLOOD

    def draw(self, surface: pg.Surface):
        m_pos = pg.mouse.get_pos()
        is_hovered = self.rect.collidepoint(m_pos)

        if self.active:
            bg_col = self.color_accent
            txt_col = (255, 255, 255)
        elif is_hovered:
            bg_col = (60, 40, 70)
            txt_col = ACCENT_CYAN
        else:
            bg_col = (35, 28, 45)
            txt_col = TEXT_COLOR

        pg.draw.rect(surface, bg_col, self.rect, border_radius=6)
        pg.draw.rect(surface, self.color_accent if (self.active or is_hovered) else BORDER_COLOR, self.rect, width=1, border_radius=6)

        txt = btn_font.render(self.text, True, txt_col)
        txt_rect = txt.get_rect(center=self.rect.center)
        surface.blit(txt, txt_rect)

    def handle_event(self, event: pg.event.Event):
        if event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self.callback()


class BloodParticle:
    """Arterial Blood Particle Emitter System"""
    def __init__(self, x: float, y: float, vx: float, vy: float, color: Tuple[int, int, int], lifetime: float):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.color = color
        self.max_life = lifetime
        self.life = lifetime
        self.size = random.uniform(2.0, 5.0)

    def update(self, dt: float):
        self.life -= dt
        self.x += self.vx * dt * 60
        self.y += self.vy * dt * 60
        self.vy += 0.2 * dt * 60  # Gravity

    def draw(self, surface: pg.Surface):
        if self.life <= 0:
            return
        alpha = int(255 * (self.life / self.max_life))
        r, g, b = self.color
        surf = pg.Surface((int(self.size * 2), int(self.size * 2)), pg.SRCALPHA)
        pg.draw.circle(surf, (r, g, b, alpha), (int(self.size), int(self.size)), int(self.size))
        surface.blit(surf, (self.x - self.size, self.y - self.size))


class BloodZombieEditorApp:
    def __init__(self):
        self.clock = pg.time.Clock()
        self.running = True

        self.config_path = "game_data/enemy_blood_zombie_config.json"
        self.presets_path = "game_data/blood_zombie_presets.json"
        self.load_config()

        # Audio setup
        self.audio_samples: Dict[str, pg.mixer.Sound] = {}
        self.init_audio()

        # Navigation Modes: "ANIMATION", "COMBAT_METRICS", "SIMULATOR"
        self.mode = "ANIMATION"

        # Sliders grouped by scientific & metaphor categories with clean spacing
        self.sliders: Dict[str, MetaphorSlider] = {
            # Pulse & Rheology Panel (Left Panel)
            "anim_speed": MetaphorSlider(
                "anim_speed", "Cardiac Pulse Tempo", "Frame Progression Rate", "f_pulse = 1 / dt",
                40, 155, 310, 0.05, 0.40, self.config.get("anim_speed", 0.15), is_float=True, format_str="{val}", unit="Hz"
            ),
            "scale": MetaphorSlider(
                "scale", "Mutation Mass Scale", "Sprite Render Multiplier", "S_render = Scale * Base_Dim",
                40, 215, 310, 1.0, 4.0, self.config.get("scale", 2.0), is_float=True, format_str="{val}x"
            ),
            "ground_offset": MetaphorSlider(
                "ground_offset", "Spine Anchor Y-Pivot", "Spatial Pivot Vector Offset", "Y_anchor = Y_ground + Offset",
                40, 275, 310, -50, 50, self.config.get("ground_offset", 0), is_float=False, format_str="{val}", unit="px"
            ),
            "lerp_viscosity": MetaphorSlider(
                "lerp_viscosity", "Viscous Rheology", "Transition Crossfade Fluidity", "S(t) = (1-t)A + tB",
                40, 335, 310, 0.0, 1.0, self.config.get("lerp_viscosity", 0.70), is_float=True, format_str="{val}"
            ),
            "frame_offset_x": MetaphorSlider(
                "frame_offset_x", "Frame Shift X (Nudge)", "Active Keyframe Pivot Shift X", "X_frame = Center_X + dx",
                40, 395, 310, -100, 100, 0, is_float=False, format_str="{val}", unit="px"
            ),
            "frame_offset_y": MetaphorSlider(
                "frame_offset_y", "Frame Shift Y (Nudge)", "Active Keyframe Pivot Shift Y", "Y_frame = Ground_Y + dy",
                40, 455, 310, -100, 100, 0, is_float=False, format_str="{val}", unit="px"
            ),
            "hitbox_offset_x": MetaphorSlider(
                "hitbox_offset_x", "Hitbox Reach Shift X", "Strike Box Horizontal Offset", "X_hitbox = Pivot_X + dx",
                40, 515, 310, -80, 120, 10, is_float=False, format_str="{val}", unit="px"
            ),

            # Vampiric Combat Panel (Left Panel)
            "max_health": MetaphorSlider(
                "max_health", "Vital Husk Tenacity", "Max Entity Health", "HP_max",
                40, 155, 310, 10.0, 200.0, self.config.get("max_health", 50.0), is_float=True, format_str="{val}", unit="HP"
            ),
            "speed": MetaphorSlider(
                "speed", "Stalking Velocity", "Horizontal Chase Speed", "v_x = dx/dt",
                40, 215, 310, 0.5, 6.0, self.config.get("speed", 2.2), is_float=True, format_str="{val}", unit="px/f"
            ),
            "damage_scale": MetaphorSlider(
                "damage_scale", "Laceration Severity", "Damage Output Multiplier", "D_total = D_base * D_scale",
                40, 275, 310, 0.5, 3.0, self.config.get("damage_scale", 1.2), is_float=True, format_str="{val}x"
            ),
            "knockback_scale": MetaphorSlider(
                "knockback_scale", "Kinetic Shove Multiplier", "Impulse Vector Scale", "p = m * v",
                40, 335, 310, 0.5, 3.0, self.config.get("knockback_scale", 1.2), is_float=True, format_str="{val}x"
            ),
            "detection_range": MetaphorSlider(
                "detection_range", "Smell of Blood Horizon", "Aggro Detection Radius", "R_sense = sqrt(dx^2 + dy^2)",
                40, 395, 310, 300, 1800, self.config.get("detection_range", 1200), is_float=False, format_str="{val}", unit="px"
            ),
            "attack_range": MetaphorSlider(
                "attack_range", "Carnivorous Reach", "Proximity Attack Trigger Horizon", "R_attack",
                40, 455, 310, 30, 150, self.config.get("attack_range", 65), is_float=False, format_str="{val}", unit="px"
            ),
            "attack_hitbox_width": MetaphorSlider(
                "attack_hitbox_width", "Vampiric Strike Width", "Active Attack Collider Width", "W_hitbox",
                40, 515, 310, 20, 140, self.config.get("attack_hitbox_width", 60), is_float=False, format_str="{val}", unit="px"
            ),

            # Sanguine VFX & Audio Sliders (Right Panel)
            "blood_spray_pressure": MetaphorSlider(
                "blood_spray_pressure", "Arterial Spray Pressure", "Particle Emitter Density", "Particle_Count = Pressure * dt",
                920, 265, 320, 0, 50, self.config.get("blood_spray_pressure", 20), is_float=False, format_str="{val}", unit="drops"
            ),
            "player_dummy_distance": MetaphorSlider(
                "player_dummy_distance", "Stagnant Player Spacing", "Target Dummy Distance", "X_dummy = Center_X + Dist",
                920, 325, 320, 20, 250, self.config.get("player_dummy_distance", 75), is_float=False, format_str="{val}", unit="px"
            ),
            "necrotic_glow_r": MetaphorSlider(
                "necrotic_glow_r", "Necrotic Red Tint", "RGB Color Red Channel", "Color.R",
                920, 385, 320, 0, 255, self.config.get("necrotic_glow_r", 255), is_float=False, format_str="{val}"
            ),
            "necrotic_glow_g": MetaphorSlider(
                "necrotic_glow_g", "Necrotic Green Tint", "RGB Color Green Channel", "Color.G",
                920, 445, 320, 0, 255, self.config.get("necrotic_glow_g", 255), is_float=False, format_str="{val}"
            ),
            "necrotic_glow_b": MetaphorSlider(
                "necrotic_glow_b", "Necrotic Blue Tint", "RGB Color Blue Channel", "Color.B",
                920, 505, 320, 0, 255, self.config.get("necrotic_glow_b", 255), is_float=False, format_str="{val}"
            ),
            "onion_skin_alpha": MetaphorSlider(
                "onion_skin_alpha", "Ghost Trail Alpha", "Onion Skin Opacity Guide", "Alpha_ghost",
                920, 565, 320, 0.05, 0.80, 0.35, is_float=True, format_str="{val}"
            ),
            "sanguine_phase_shift": MetaphorSlider(
                "sanguine_phase_shift", "Sanguine Phase Shift", "Chromatic RGB Channel Displacement", "RGB_split = (dx_red, dy_red)",
                920, 625, 320, 0, 15, 6.0, is_float=False, format_str="{val}", unit="px"
            ),
        }

        # Action Buttons
        self.btn_save = Button("SAVE TO ENGINE", 40, 635, 150, 36, self.request_save_config, active=True, color_accent=ACCENT_BLOOD)
        self.btn_reset = Button("RESET DEFAULTS", 200, 635, 150, 36, self.reset_defaults, color_accent=BORDER_COLOR)
        self.btn_auto_align = Button("AUTO-ALIGN PIVOTS", 40, 585, 150, 36, self.auto_align_pivots, active=True, color_accent=ACCENT_CYAN)
        self.btn_harmonic_c1 = Button("HARMONIC C1 SMOOTHER", 200, 585, 150, 36, self.harmonic_c1_smooth, active=True, color_accent=ACCENT_PURPLE)

        # Mode Selector Buttons (Top Header Nav)
        self.mode_buttons = [
            Button("ANIMATION AND TIMELINE", 400, 20, 240, 36, lambda: self.set_mode("ANIMATION"), active=True, color_accent=ACCENT_BLOOD),
            Button("COMBAT AND METRICS", 655, 20, 240, 36, lambda: self.set_mode("COMBAT_METRICS"), color_accent=ACCENT_PURPLE),
            Button("AI STATE SIMULATOR", 910, 20, 240, 36, lambda: self.set_mode("SIMULATOR"), color_accent=ACCENT_CYAN),
        ]

        # Presets Buttons (2x2 Grid)
        self.preset_buttons = [
            Button("BOSS ZOMBIE", 920, 145, 155, 32, lambda: self.apply_preset("boss_default")),
            Button("BERSERKER", 1085, 145, 155, 32, lambda: self.apply_preset("berserker")),
            Button("PLAGUE CARRIER", 920, 185, 155, 32, lambda: self.apply_preset("plague")),
            Button("LEVIATHAN", 1085, 185, 155, 32, lambda: self.apply_preset("leviathan")),
        ]

        # Animation State Buttons
        self.anim_states = ["Idle", "Move", "Attack1", "Attack2", "Death"]
        self.hit_frame_map = {
            "Attack1": {6},
            "Attack2": {5, 6},
        }
        self.current_anim_state = "Idle"
        self.anim_buttons = [
            Button("IDLE", 390, 500, 92, 32, lambda: self.select_anim("Idle")),
            Button("MOVE", 490, 500, 92, 32, lambda: self.select_anim("Move")),
            Button("ATTACK 1", 590, 500, 92, 32, lambda: self.select_anim("Attack1")),
            Button("ATTACK 2", 690, 500, 92, 32, lambda: self.select_anim("Attack2")),
            Button("DEATH", 790, 500, 92, 32, lambda: self.select_anim("Death")),
        ]
        self.update_anim_buttons()

        # Transport Controls
        self.is_playing = True
        self.play_speed_multiplier = 1.0
        self.btn_play_pause = Button("PAUSE", 390, 542, 110, 30, self.toggle_play_pause, active=True)
        self.btn_step_prev = Button("< FRAME", 510, 542, 110, 30, self.step_frame_backward)
        self.btn_step_next = Button("FRAME >", 630, 542, 110, 30, self.step_frame_forward)
        self.btn_slow_mo = Button("1.0x SPEED", 750, 542, 132, 30, self.cycle_speed)

        # Overlay Viewport Toggles & Onion Skin
        self.show_hitbox = True
        self.show_hurtbox = True
        self.show_anchor = True
        self.show_sensing = True
        self.show_particles = True
        self.show_onion_skin = True
        self.show_stagnant_player = True
        self.show_phase = True

        self.btn_toggle_hitbox = Button("HITBOX: ON", 390, 582, 92, 28, self.toggle_hitbox, active=True, color_accent=ACCENT_BLOOD)
        self.btn_toggle_hurtbox = Button("HURTBOX: ON", 490, 582, 92, 28, self.toggle_hurtbox, active=True, color_accent=ACCENT_GREEN)
        self.btn_toggle_anchor = Button("ANCHOR: ON", 590, 582, 92, 28, self.toggle_anchor, active=True, color_accent=ACCENT_GOLD)
        self.btn_toggle_onion = Button("GHOST: ON", 690, 582, 92, 28, self.toggle_onion, active=True, color_accent=ACCENT_CYAN)
        self.btn_toggle_player_dummy = Button("PLAYER: ON", 790, 582, 92, 28, self.toggle_player_dummy, active=True, color_accent=ACCENT_PURPLE)
        self.btn_toggle_phase = Button("PHASE: ON", 390, 618, 92, 28, self.toggle_phase, active=True, color_accent=ACCENT_BLOOD)
        self.phase_modes = ["CHROMATIC SPLIT", "SANGUINE GHOSTS", "ELDRITCH FRENZY"]
        self.phase_mode_idx = 2
        self.btn_phase_mode = Button("MODE: FRENZY", 490, 618, 110, 28, self.cycle_phase_mode, active=True, color_accent=ACCENT_PURPLE)

        # Ghost snapshot history buffer for phase rendering
        self.ghost_trail: List[Tuple[pg.Surface, Tuple[int, int], float]] = []

        # Load Animation Sprites
        self.animations: Dict[str, List[pg.Surface]] = {}
        self.load_animations()

        # Load Target Player Sprites
        self.player_stand_sprite: Optional[pg.Surface] = None
        self.player_hurt_sprite: Optional[pg.Surface] = None
        self.load_player_sprites()

        # Frame Scrubber & Per-Frame Offset Mapping
        self.frame_index = 0.0
        self.last_played_frame = -1
        self.frame_offsets: Dict[str, Dict[str, Dict[str, float]]] = self.config.get("frame_offsets", {})

        # Player Reaction State
        self.player_hurt_timer = 0.0
        self.player_reaction_hit = False

        # Particle System
        self.particles: List[BloodParticle] = []

        # Simulator State
        self.sim_zombie_x = 640.0
        self.sim_zombie_y = 350.0
        self.sim_zombie_vx = 0.0
        self.sim_zombie_vy = 0.0
        self.sim_player_x = 900.0
        self.sim_player_y = 350.0
        self.sim_zombie_state = "Idle"
        self.sim_zombie_health = 50.0
        self.dragging_player = False

        # Toast Message System
        self.toast_msg = ""
        self.toast_timer = 0.0

    def init_audio(self):
        sound_files = {
            "roar": "assets/audio/zombie-noise.mp3",
            "slice": "assets/audio/mixkit-quick-knife-slice-cutting-2152.mp3",
        }
        for key, filepath in sound_files.items():
            if os.path.exists(filepath):
                try:
                    self.audio_samples[key] = pg.mixer.Sound(filepath)
                    self.audio_samples[key].set_volume(0.4)
                except Exception:
                    pass

    def load_config(self):
        default_config = {
            "max_health": 50.0,
            "speed": 2.2,
            "damage_scale": 1.2,
            "knockback_scale": 1.2,
            "detection_range": 1200,
            "attack_range": 65,
            "vertical_tolerance": 100,
            "attack_hitbox_width": 60,
            "attack_hitbox_height": 80,
            "scale": 2.0,
            "anim_speed": 0.15,
            "ground_offset": 0,
            "lerp_viscosity": 0.70,
            "blood_spray_pressure": 20,
            "necrotic_glow_r": 255,
            "necrotic_glow_g": 255,
            "necrotic_glow_b": 255,
            "player_dummy_distance": 75,
            "frame_offsets": {},
        }
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    default_config.update(data)
            except Exception as e:
                print(f"Error reading config {self.config_path}: {e}")
        self.config = default_config

    def load_animations(self):
        base_path = "assets/graphics/bloodZombie"
        folder_map = {
            "Idle": os.path.join(base_path, "Idle"),
            "Move": os.path.join(base_path, "Move"),
            "Attack1": os.path.join(base_path, "Attack1"),
            "Attack2": os.path.join(base_path, "Attack2"),
            "Death": os.path.join(base_path, "Death"),
        }

        for state_key, folder in folder_map.items():
            frames = []
            if os.path.exists(folder):
                files = sorted([f for f in os.listdir(folder) if f.endswith(".png")])
                for fname in files:
                    full_p = os.path.join(folder, fname)
                    try:
                        img = pg.image.load(full_p).convert_alpha()
                        frames.append(img)
                    except Exception as e:
                        print(f"Error loading frame {full_p}: {e}")
            if not frames:
                # Fallback placeholder frame
                surf = pg.Surface((64, 64), pg.SRCALPHA)
                pg.draw.rect(surf, (200, 30, 40), (8, 8, 48, 48))
                frames.append(surf)
            self.animations[state_key] = frames

    def load_player_sprites(self):
        shadow_p = "assets/shadow_warrior/idle/idle_1.png"
        shadow_hurt_p = "assets/shadow_warrior/take_hit/take_hit_1.png"
        stand_p = "assets/graphics/Player/player_stand.png"

        if os.path.exists(shadow_p):
            try:
                raw_idle = pg.image.load(shadow_p).convert_alpha()
                bbox = raw_idle.get_bounding_rect()
                cropped = raw_idle.subsurface(bbox).copy()
                self.player_stand_sprite = pg.transform.flip(cropped, True, False)
            except Exception as e:
                print(f"Warning: Failed to load shadow warrior idle sprite: {e}")

        if self.player_stand_sprite is None and os.path.exists(stand_p):
            try:
                self.player_stand_sprite = pg.image.load(stand_p).convert_alpha()
            except Exception:
                pass

        if self.player_stand_sprite is None:
            # Fallback player surface
            surf = pg.Surface((32, 54), pg.SRCALPHA)
            pg.draw.rect(surf, (0, 180, 240), (0, 0, 32, 54), border_radius=6)
            self.player_stand_sprite = surf

        if os.path.exists(shadow_hurt_p):
            try:
                raw_hurt = pg.image.load(shadow_hurt_p).convert_alpha()
                bbox = raw_hurt.get_bounding_rect()
                cropped_hurt = raw_hurt.subsurface(bbox).copy()
                self.player_hurt_sprite = pg.transform.flip(cropped_hurt, True, False)
            except Exception as e:
                print(f"Warning: Failed to load shadow warrior take_hit sprite: {e}")

        if self.player_hurt_sprite is None and self.player_stand_sprite:
            # Create Hurt state flash sprite
            hurt_surf = self.player_stand_sprite.copy()
            tint_s = pg.Surface(hurt_surf.get_size(), pg.SRCALPHA)
            tint_s.fill((255, 40, 40, 200))
            hurt_surf.blit(tint_s, (0, 0), special_flags=pg.BLEND_RGBA_MULT)
            self.player_hurt_sprite = hurt_surf

    def get_current_frame_offset(self) -> Tuple[int, int]:
        state_map = self.frame_offsets.get(self.current_anim_state, {})
        frame_key = str(int(self.frame_index))
        offset = state_map.get(frame_key, {})
        return int(offset.get("dx", 0)), int(offset.get("dy", 0))

    def set_current_frame_offset(self, dx: int, dy: int):
        if self.current_anim_state not in self.frame_offsets:
            self.frame_offsets[self.current_anim_state] = {}
        frame_key = str(int(self.frame_index))
        if frame_key not in self.frame_offsets[self.current_anim_state]:
            self.frame_offsets[self.current_anim_state][frame_key] = {}
        self.frame_offsets[self.current_anim_state][frame_key]["dx"] = dx
        self.frame_offsets[self.current_anim_state][frame_key]["dy"] = dy

        self.sliders["frame_offset_x"].val = dx
        self.sliders["frame_offset_y"].val = dy

    def save_config_file(self):
        # Update config dict from slider values
        for key, slider in self.sliders.items():
            if key not in ["frame_offset_x", "frame_offset_y", "onion_skin_alpha"]:
                self.config[key] = slider.val

        self.config["frame_offsets"] = self.frame_offsets

        # Create backup file first
        if os.path.exists(self.config_path):
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            backup_path = f"game_data/enemy_blood_zombie_config.backup_{timestamp}.json"
            try:
                with open(self.config_path, "r", encoding="utf-8") as src, open(backup_path, "w", encoding="utf-8") as dst:
                    dst.write(src.read())
            except Exception as e:
                print(f"Backup warning: {e}")

        # Write clean JSON config and sync to RAM cache, SQLite, and cloud API
        try:
            from src.game.services import ConfigClient
            from src.game.entities.hitbox_registry import HitboxRegistry, HitboxMargins
            
            # Save and sync full enemy config via ConfigClient
            ConfigClient.save_and_sync("enemy_blood_zombie", self.config)

            # Sync scale and ground offset with HitboxRegistry if updated
            key = "boss:bloodzombie"
            old_margins = HitboxRegistry.get_margins(key)
            scale_val = float(self.config.get("scale", old_margins.scale))
            ground_val = int(self.config.get("ground_offset", old_margins.ground_offset))

            new_margins = HitboxMargins(
                left=old_margins.left,
                right=old_margins.right,
                top=old_margins.top,
                bottom=old_margins.bottom,
                ground_offset=ground_val,
                scale=scale_val,
            )
            HitboxRegistry.update_margins(key, new_margins)
            HitboxRegistry.save_all()

            self.show_toast("CONFIG & HITBOX REGISTRY SAVED AND SYNCED!")
        except Exception as e:
            self.show_toast(f"SAVE ERROR: {e}")

    def show_toast(self, msg: str):
        self.toast_msg = msg
        self.toast_timer = 2.5

    def request_save_config(self):
        self.save_config_file()

    def reset_defaults(self):
        self.load_config()
        self.frame_offsets = self.config.get("frame_offsets", {})
        for key, slider in self.sliders.items():
            if key in self.config:
                val = self.config[key]
                if isinstance(val, (int, float)):
                    slider.val = float(val)
        self.show_toast("RESET TO DEFAULT VALUES")

    def auto_align_pivots(self):
        """
        Analyze hip center of mass for all animation frames across Idle, Move, Attack1, Attack2, Death.
        Calculate per-frame pivot offsets (dx, dy) to eliminate frame-to-frame popping and ground misalignment,
        specifically smoothing out looping jumps (e.g., Move frame 7 -> frame 0) and attack recovery transitions.
        """
        if not self.animations:
            return

        def _get_hip_x(surf: pg.Surface) -> float:
            bbox = surf.get_bounding_rect()
            y_start = int(bbox.y + bbox.h * 0.3)
            y_end = int(bbox.y + bbox.h * 0.6)
            xs = []
            for y in range(y_start, y_end):
                for x in range(bbox.x, bbox.x + bbox.w):
                    if surf.get_at((x, y)).a > 50:
                        xs.append(x)
            return sum(xs) / float(len(xs)) if xs else (bbox.x + bbox.w / 2.0)

        ref_cx = 60.4
        ref_bottom = 128.0
        idle_frames = self.animations.get("Idle", [])
        if idle_frames:
            ref_bbox = idle_frames[0].get_bounding_rect()
            ref_cx = _get_hip_x(idle_frames[0])
            ref_bottom = float(ref_bbox.y + ref_bbox.h)

        for anim_key, frames in self.animations.items():
            if anim_key not in self.frame_offsets:
                self.frame_offsets[anim_key] = {}

            if not frames:
                continue

            hip_xs = [_get_hip_x(f) for f in frames]
            bottoms = [float(f.get_bounding_rect().y + f.get_bounding_rect().h) for f in frames]
            num_frames = len(frames)
            start_hip = hip_xs[0]

            for i in range(num_frames):
                hip = hip_xs[i]
                bot = bottoms[i]

                if anim_key in ("Move", "Idle"):
                    target_hip = start_hip
                elif anim_key in ("Attack1", "Attack2"):
                    rec_start = int(num_frames * 0.4)
                    if i >= rec_start and num_frames > 1:
                        progress = (i - rec_start) / float(num_frames - 1 - rec_start)
                        target_hip = hip * (1.0 - progress) + ref_cx * progress
                    else:
                        target_hip = hip
                else:
                    target_hip = start_hip

                dx = int(round(target_hip - hip))
                dy = int(round(ref_bottom - bot))

                self.frame_offsets[anim_key][str(i)] = {"dx": dx, "dy": dy}

        dx, dy = self.get_current_frame_offset()
        self.sliders["frame_offset_x"].val = float(dx)
        self.sliders["frame_offset_y"].val = float(dy)
        self.show_toast("PIVOTS & ROOT-MOTION AUTO-ALIGNED!")

    def harmonic_c1_smooth(self):
        """
        Apply a 3-tap circular Gaussian filter across per-frame dx, dy offsets for all animation loops
        to enforce C1 velocity continuity across frame transitions (especially Frame 7 -> Frame 0 loop boundary).
        """
        if not self.frame_offsets:
            self.auto_align_pivots()

        for anim_key, offsets in self.frame_offsets.items():
            if not offsets:
                continue

            sorted_keys = sorted(offsets.keys(), key=lambda k: int(k))
            num_keys = len(sorted_keys)
            if num_keys < 3:
                continue

            dx_vals = [offsets[k].get("dx", 0) for k in sorted_keys]
            dy_vals = [offsets[k].get("dy", 0) for k in sorted_keys]

            smooth_dx = []
            smooth_dy = []
            for i in range(num_keys):
                p = (i - 1) % num_keys
                n = (i + 1) % num_keys
                sdx = 0.25 * dx_vals[p] + 0.5 * dx_vals[i] + 0.25 * dx_vals[n]
                sdy = 0.25 * dy_vals[p] + 0.5 * dy_vals[i] + 0.25 * dy_vals[n]
                smooth_dx.append(int(round(sdx)))
                smooth_dy.append(int(round(sdy)))

            for idx, k in enumerate(sorted_keys):
                offsets[k]["dx"] = smooth_dx[idx]
                offsets[k]["dy"] = smooth_dy[idx]

        dx, dy = self.get_current_frame_offset()
        self.sliders["frame_offset_x"].val = float(dx)
        self.sliders["frame_offset_y"].val = float(dy)
        self.show_toast("HARMONIC C1 VELOCITY CONTINUITY APPLIED!")

    def apply_preset(self, preset_key: str):
        presets = {
            "boss_default": {
                "max_health": 50.0, "speed": 2.2, "damage_scale": 1.2, "knockback_scale": 1.2,
                "detection_range": 1200, "attack_range": 65, "scale": 2.0, "anim_speed": 0.15,
                "blood_spray_pressure": 20, "necrotic_glow_r": 255, "necrotic_glow_g": 255, "necrotic_glow_b": 255
            },
            "berserker": {
                "max_health": 80.0, "speed": 4.5, "damage_scale": 2.2, "knockback_scale": 2.0,
                "detection_range": 1600, "attack_range": 85, "scale": 2.4, "anim_speed": 0.28,
                "blood_spray_pressure": 45, "necrotic_glow_r": 255, "necrotic_glow_g": 50, "necrotic_glow_b": 50
            },
            "plague": {
                "max_health": 35.0, "speed": 1.8, "damage_scale": 0.9, "knockback_scale": 0.8,
                "detection_range": 900, "attack_range": 55, "scale": 1.8, "anim_speed": 0.12,
                "blood_spray_pressure": 15, "necrotic_glow_r": 100, "necrotic_glow_g": 255, "necrotic_glow_b": 100
            },
            "leviathan": {
                "max_health": 150.0, "speed": 1.4, "damage_scale": 2.8, "knockback_scale": 2.5,
                "detection_range": 1400, "attack_range": 110, "scale": 3.5, "anim_speed": 0.10,
                "blood_spray_pressure": 50, "necrotic_glow_r": 180, "necrotic_glow_g": 40, "necrotic_glow_b": 220
            }
        }
        if preset_key in presets:
            preset = presets[preset_key]
            for k, val in preset.items():
                if k in self.sliders:
                    self.sliders[k].val = val
            self.show_toast(f"APPLIED PRESET: {preset_key.upper()}")

    def set_mode(self, new_mode: str):
        self.mode = new_mode
        for btn in self.mode_buttons:
            btn.active = (btn.text.replace(" ", "_").find(new_mode) != -1 or
                          (new_mode == "ANIMATION" and "ANIMATION" in btn.text) or
                          (new_mode == "COMBAT_METRICS" and "COMBAT" in btn.text) or
                          (new_mode == "SIMULATOR" and "SIMULATOR" in btn.text))

    def select_anim(self, state: str):
        self.current_anim_state = state
        self.frame_index = 0.0
        self.last_played_frame = -1
        self.update_anim_buttons()
        # Update sliders with frame offset
        dx, dy = self.get_current_frame_offset()
        self.sliders["frame_offset_x"].val = dx
        self.sliders["frame_offset_y"].val = dy

    def update_anim_buttons(self):
        for btn in self.anim_buttons:
            btn.active = (btn.text.lower().replace(" ", "") == self.current_anim_state.lower())

    def toggle_play_pause(self):
        self.is_playing = not self.is_playing
        self.btn_play_pause.text = "PAUSE" if self.is_playing else "PLAY"
        self.btn_play_pause.active = self.is_playing

    def step_frame_forward(self):
        frames = self.animations.get(self.current_anim_state, [])
        if frames:
            self.frame_index = (self.frame_index + 1) % len(frames)
            dx, dy = self.get_current_frame_offset()
            self.sliders["frame_offset_x"].val = dx
            self.sliders["frame_offset_y"].val = dy

    def step_frame_backward(self):
        frames = self.animations.get(self.current_anim_state, [])
        if frames:
            self.frame_index = (self.frame_index - 1) % len(frames)
            dx, dy = self.get_current_frame_offset()
            self.sliders["frame_offset_x"].val = dx
            self.sliders["frame_offset_y"].val = dy

    def cycle_speed(self):
        speeds = [0.25, 0.5, 1.0, 2.0]
        curr_i = speeds.index(self.play_speed_multiplier) if self.play_speed_multiplier in speeds else 2
        next_i = (curr_i + 1) % len(speeds)
        self.play_speed_multiplier = speeds[next_i]
        self.btn_slow_mo.text = f"{self.play_speed_multiplier}x SPEED"

    def toggle_hitbox(self):
        self.show_hitbox = not self.show_hitbox
        self.btn_toggle_hitbox.text = f"HITBOX: {'ON' if self.show_hitbox else 'OFF'}"
        self.btn_toggle_hitbox.active = self.show_hitbox

    def toggle_hurtbox(self):
        self.show_hurtbox = not self.show_hurtbox
        self.btn_toggle_hurtbox.text = f"HURTBOX: {'ON' if self.show_hurtbox else 'OFF'}"
        self.btn_toggle_hurtbox.active = self.show_hurtbox

    def toggle_anchor(self):
        self.show_anchor = not self.show_anchor
        self.btn_toggle_anchor.text = f"ANCHOR: {'ON' if self.show_anchor else 'OFF'}"
        self.btn_toggle_anchor.active = self.show_anchor

    def toggle_onion(self):
        self.show_onion_skin = not self.show_onion_skin
        self.btn_toggle_onion.text = f"GHOST: {'ON' if self.show_onion_skin else 'OFF'}"
        self.btn_toggle_onion.active = self.show_onion_skin

    def toggle_player_dummy(self):
        self.show_stagnant_player = not self.show_stagnant_player
        self.btn_toggle_player_dummy.text = f"PLAYER: {'ON' if self.show_stagnant_player else 'OFF'}"
        self.btn_toggle_player_dummy.active = self.show_stagnant_player

    def toggle_phase(self):
        self.show_phase = not self.show_phase
        self.btn_toggle_phase.text = f"PHASE: {'ON' if self.show_phase else 'OFF'}"
        self.btn_toggle_phase.active = self.show_phase

    def cycle_phase_mode(self):
        self.phase_mode_idx = (self.phase_mode_idx + 1) % len(self.phase_modes)
        mode_str = self.phase_modes[self.phase_mode_idx]
        short_names = {"CHROMATIC SPLIT": "MODE: SPLIT", "SANGUINE GHOSTS": "MODE: GHOSTS", "ELDRITCH FRENZY": "MODE: FRENZY"}
        self.btn_phase_mode.text = short_names.get(mode_str, "MODE: FRENZY")
        self.show_toast(f"Phase Effect Mode: {mode_str}")

    def spawn_blood_burst(self, x: float, y: float, count: int = 15):
        if not self.show_particles:
            return
        pressure = self.sliders["blood_spray_pressure"].val
        for _ in range(int(count * (pressure / 20.0))):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(2.0, 7.0)
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed - random.uniform(1.0, 3.0)
            color = (
                random.randint(180, 240),
                random.randint(10, 40),
                random.randint(10, 40)
            )
            self.particles.append(BloodParticle(x, y, vx, vy, color, random.uniform(0.3, 0.8)))

    def update(self, dt: float):
        # Update Toast timer
        if self.toast_timer > 0:
            self.toast_timer -= dt

        if self.player_hurt_timer > 0:
            self.player_hurt_timer -= dt

        # Sync frame sliders
        if self.mode == "ANIMATION":
            cur_dx, cur_dy = self.get_current_frame_offset()
            if self.sliders["frame_offset_x"].val != cur_dx or self.sliders["frame_offset_y"].val != cur_dy:
                self.set_current_frame_offset(
                    int(self.sliders["frame_offset_x"].val),
                    int(self.sliders["frame_offset_y"].val)
                )

        # Update animation playback
        frames = self.animations.get(self.current_anim_state, [])
        if frames:
            anim_spf = self.sliders["anim_speed"].val
            if self.is_playing:
                self.frame_index += (dt / anim_spf) * self.play_speed_multiplier
                if self.frame_index >= len(frames):
                    self.frame_index = 0.0

            curr_frame_int = int(self.frame_index)
            if curr_frame_int != self.last_played_frame:
                self.last_played_frame = curr_frame_int

                # Check for sound & blood triggers on active hit frames
                hit_frames = self.hit_frame_map.get(self.current_anim_state, set())
                if curr_frame_int in hit_frames:
                    if "slice" in self.audio_samples:
                        self.audio_samples["slice"].play()
                    self.spawn_blood_burst(640, 260, count=25)

                    # Trigger Target Player Hurt State
                    self.player_hurt_timer = 0.4
                    self.player_reaction_hit = True

        # Update Blood Particles
        for p in self.particles:
            p.update(dt)
        self.particles = [p for p in self.particles if p.life > 0]

        # Update Simulator Logic if in SIMULATOR mode
        if self.mode == "SIMULATOR":
            self.update_simulation(dt)

    def update_simulation(self, dt: float):
        dx = self.sim_player_x - self.sim_zombie_x
        dy = self.sim_player_y - self.sim_zombie_y
        dist = math.hypot(dx, dy)

        det_range = self.sliders["detection_range"].val
        atk_range = self.sliders["attack_range"].val
        move_speed = self.sliders["speed"].val * 60.0 * dt

        if dist <= atk_range:
            self.sim_zombie_state = "Attack1"
            if random.random() < 0.02 and "roar" in self.audio_samples:
                self.audio_samples["roar"].play()
        elif dist <= det_range:
            self.sim_zombie_state = "Move"
            if dist > 0:
                self.sim_zombie_x += (dx / dist) * move_speed
                self.sim_zombie_y += (dy / dist) * move_speed
        else:
            self.sim_zombie_state = "Idle"

    def draw_timeline(self, surface: pg.Surface):
        rect = pg.Rect(390, 460, 495, 32)
        pg.draw.rect(surface, (25, 20, 35), rect, border_radius=6)
        pg.draw.rect(surface, BORDER_COLOR, rect, width=1, border_radius=6)

        frames = self.animations.get(self.current_anim_state, [])
        total_frames = max(1, len(frames))
        hit_frames = self.hit_frame_map.get(self.current_anim_state, set())

        step_w = rect.width / total_frames
        curr_frame_int = int(self.frame_index) % total_frames

        # Draw frame segments and hit frame indicators
        for i in range(total_frames):
            seg_x = rect.x + i * step_w
            seg_rect = pg.Rect(seg_x, rect.y, step_w, rect.height)

            # Hit frame highlight
            if i in hit_frames:
                pg.draw.rect(surface, (180, 20, 40), seg_rect, border_radius=2)
                txt_hit = tooltip_font.render("HIT", True, (255, 220, 0))
                surface.blit(txt_hit, (seg_x + step_w / 2 - txt_hit.get_width() / 2, rect.y + 16))

            # Active current frame highlight
            if i == curr_frame_int:
                pg.draw.rect(surface, ACCENT_CYAN, seg_rect, width=2, border_radius=2)

            # Divider line
            pg.draw.line(surface, BORDER_COLOR, (seg_x, rect.y), (seg_x, rect.bottom))

            # Frame index label
            txt_num = tooltip_font.render(str(i), True, TEXT_COLOR if i == curr_frame_int else TEXT_MUTED)
            surface.blit(txt_num, (seg_x + step_w / 2 - txt_num.get_width() / 2, rect.y + 2))

        # Handle mouse click on timeline to scrub frame
        m_pos = pg.mouse.get_pos()
        if pg.mouse.get_pressed()[0] and rect.collidepoint(m_pos):
            rel_x = m_pos[0] - rect.x
            clicked_frame = int((rel_x / rect.width) * total_frames)
            self.frame_index = float(max(0, min(total_frames - 1, clicked_frame)))
            dx, dy = self.get_current_frame_offset()
            self.sliders["frame_offset_x"].val = dx
            self.sliders["frame_offset_y"].val = dy

    def draw_canvas(self, surface: pg.Surface):
        canvas_rect = pg.Rect(390, 70, 495, 380)
        pg.draw.rect(surface, CANVAS_BG, canvas_rect, border_radius=8)
        pg.draw.rect(surface, BORDER_COLOR, canvas_rect, width=1, border_radius=8)

        # Clip canvas rendering
        surface.set_clip(canvas_rect)

        # Center point coordinates
        center_x = canvas_rect.centerx
        ground_y = canvas_rect.centery + 100 + self.sliders["ground_offset"].val

        # Ground plane line
        pg.draw.line(surface, (60, 50, 80), (canvas_rect.x, ground_y), (canvas_rect.right, ground_y), 2)
        txt_ground = tooltip_font.render("GROUND LEVEL", True, TEXT_MUTED)
        surface.blit(txt_ground, (canvas_rect.right - 95, ground_y - 16))

        # Detection Range Circle
        if self.show_sensing:
            r_sense = int(self.sliders["detection_range"].val / 4.0)  # Visual scale
            pg.draw.circle(surface, (0, 180, 220, 40), (center_x, ground_y - 40), r_sense, 1)

        # Render Particles
        for p in self.particles:
            p.draw(surface)

        anim_key = self.sim_zombie_state if self.mode == "SIMULATOR" else self.current_anim_state
        frames = self.animations.get(anim_key, [])

        if frames:
            frame_i = int(self.frame_index) % len(frames)
            scale_fac = self.sliders["scale"].val

            # ONION SKINNING (Ghost Frames)
            if self.show_onion_skin and len(frames) > 1 and self.mode == "ANIMATION":
                prev_i = (frame_i - 1) % len(frames)
                prev_sprite = frames[prev_i]
                alpha_val = int(255 * self.sliders["onion_skin_alpha"].val)

                ghost_surf = pg.transform.scale(
                    prev_sprite,
                    (int(prev_sprite.get_width() * scale_fac), int(prev_sprite.get_height() * scale_fac))
                ).copy()
                ghost_surf.set_alpha(alpha_val)

                # Previous frame offset
                prev_dx = self.frame_offsets.get(anim_key, {}).get(str(prev_i), {}).get("dx", 0)
                prev_dy = self.frame_offsets.get(anim_key, {}).get(str(prev_i), {}).get("dy", 0)

                ghost_x = center_x - ghost_surf.get_width() // 2 + prev_dx
                ghost_y = ground_y - ghost_surf.get_height() + prev_dy
                surface.blit(ghost_surf, (ghost_x, ghost_y))

            # Main Sprite
            orig_sprite = frames[frame_i]
            cur_dx, cur_dy = self.get_current_frame_offset()

            # Apply Necrotic Color Tint
            tr = self.sliders["necrotic_glow_r"].val
            tg = self.sliders["necrotic_glow_g"].val
            tb = self.sliders["necrotic_glow_b"].val

            tinted_sprite = orig_sprite.copy()
            if tr != 255 or tg != 255 or tb != 255:
                tint_surf = pg.Surface(tinted_sprite.get_size(), pg.SRCALPHA)
                tint_surf.fill((tr, tg, tb, 255))
                tinted_sprite.blit(tint_surf, (0, 0), special_flags=pg.BLEND_RGBA_MULT)

            w = int(orig_sprite.get_width() * scale_fac)
            h = int(orig_sprite.get_height() * scale_fac)
            scaled_sprite = pg.transform.scale(tinted_sprite, (w, h))

            sprite_x = center_x - w // 2 + cur_dx
            sprite_y = ground_y - h + cur_dy

            # SANGUINE PHASE SHIFT RENDERING (Chromatic RGB Split & Temporal Ghost Trail)
            active_phase_mode = self.phase_modes[self.phase_mode_idx]
            if self.show_phase:
                shift_val = int(self.sliders["sanguine_phase_shift"].val)

                # Temporal Ghost Snapshots
                if active_phase_mode in ["SANGUINE GHOSTS", "ELDRITCH FRENZY"]:
                    if len(self.ghost_trail) == 0 or math.hypot(sprite_x - self.ghost_trail[-1][1][0], sprite_y - self.ghost_trail[-1][1][1]) > 8 or self.is_playing:
                        self.ghost_trail.append((scaled_sprite.copy(), (int(sprite_x), int(sprite_y)), time.time()))
                        if len(self.ghost_trail) > 5:
                            self.ghost_trail.pop(0)

                    # Draw decaying temporal afterimages
                    for idx, (g_surf, (gx, gy), _t) in enumerate(self.ghost_trail[:-1]):
                        alpha_factor = (idx + 1) / float(len(self.ghost_trail))
                        g_copy = g_surf.copy()
                        g_tint = pg.Surface(g_surf.get_size(), pg.SRCALPHA)
                        g_tint.fill((220, 20, 50, int(160 * alpha_factor)))
                        g_copy.blit(g_tint, (0, 0), special_flags=pg.BLEND_RGBA_MULT)
                        g_copy.set_alpha(int(180 * alpha_factor))
                        surface.blit(g_copy, (gx, gy))

                # Chromatic RGB Channel Separation
                if active_phase_mode in ["CHROMATIC SPLIT", "ELDRITCH FRENZY"] and shift_val > 0:
                    red_surf = scaled_sprite.copy()
                    red_tint = pg.Surface(scaled_sprite.get_size(), pg.SRCALPHA)
                    red_tint.fill((255, 30, 40, 180))
                    red_surf.blit(red_tint, (0, 0), special_flags=pg.BLEND_RGBA_MULT)
                    surface.blit(red_surf, (sprite_x + shift_val, sprite_y - 1), special_flags=pg.BLEND_ADD)

                    cyan_surf = scaled_sprite.copy()
                    cyan_tint = pg.Surface(scaled_sprite.get_size(), pg.SRCALPHA)
                    cyan_tint.fill((0, 220, 240, 120))
                    cyan_surf.blit(cyan_tint, (0, 0), special_flags=pg.BLEND_RGBA_MULT)
                    surface.blit(cyan_surf, (sprite_x - max(1, shift_val // 2), sprite_y + 1), special_flags=pg.BLEND_ADD)

            surface.blit(scaled_sprite, (sprite_x, sprite_y))

            # SUB-FRAME VISCOUS RHEOLOGY CROSSFADE (lerp_viscosity)
            visc = float(self.sliders["lerp_viscosity"].val)
            frac = self.frame_index - math.floor(self.frame_index)
            next_i = (frame_i + 1) % len(frames)
            if visc > 0.02 and frac > 0.02 and len(frames) > 1:
                next_sprite = frames[next_i]
                next_dx = self.frame_offsets.get(anim_key, {}).get(str(next_i), {}).get("dx", 0)
                next_dy = self.frame_offsets.get(anim_key, {}).get(str(next_i), {}).get("dy", 0)

                next_tinted = next_sprite.copy()
                if tr != 255 or tg != 255 or tb != 255:
                    t_surf = pg.Surface(next_tinted.get_size(), pg.SRCALPHA)
                    t_surf.fill((int(tr), int(tg), int(tb), 255))
                    next_tinted.blit(t_surf, (0, 0), special_flags=pg.BLEND_RGBA_MULT)

                next_w = int(next_sprite.get_width() * scale_fac)
                next_h = int(next_sprite.get_height() * scale_fac)
                scaled_next = pg.transform.scale(next_tinted, (next_w, next_h))
                scaled_next.set_alpha(int(255 * frac * visc))

                next_x = center_x - next_w // 2 + next_dx
                next_y = ground_y - next_h + next_dy
                surface.blit(scaled_next, (next_x, next_y))

            # Overlay Hurtbox (Flesh Receptor)
            if self.show_hurtbox:
                hurt_w = int(40 * scale_fac)
                hurt_h = int(60 * scale_fac)
                hurt_rect = pg.Rect(sprite_x + w // 2 - hurt_w // 2, ground_y - hurt_h + cur_dy, hurt_w, hurt_h)
                pg.draw.rect(surface, ACCENT_GREEN, hurt_rect, width=2)
                txt_hb = tooltip_font.render("FLESH RECEPTOR", True, ACCENT_GREEN)
                surface.blit(txt_hb, (hurt_rect.x, hurt_rect.y - 14))

            # Overlay Hitbox (Vampiric Strike Zone)
            hit_rect = None
            if self.show_hitbox and anim_key in ["Attack1", "Attack2"]:
                hitbox_x_shift = int(self.sliders["hitbox_offset_x"].val)
                box_w = int(self.sliders["attack_hitbox_width"].val * (scale_fac / 2.0))
                box_h = int(60 * (scale_fac / 2.0))
                hit_rect = pg.Rect(sprite_x + w // 2 + hitbox_x_shift, ground_y - box_h - 10 + cur_dy, box_w, box_h)
                pg.draw.rect(surface, ACCENT_BLOOD, hit_rect, width=2)
                txt_atk = tooltip_font.render("STRIKE ZONE", True, ACCENT_BLOOD)
                surface.blit(txt_atk, (hit_rect.x, hit_rect.y - 14))

            # Overlay Spine Anchor Point & Velocity Momentum Vector
            next_dx = self.frame_offsets.get(anim_key, {}).get(str(next_i), {}).get("dx", 0)
            next_dy = self.frame_offsets.get(anim_key, {}).get(str(next_i), {}).get("dy", 0)
            vel_x = next_dx - cur_dx
            vel_y = next_dy - cur_dy

            if self.show_anchor:
                anchor_x = center_x + cur_dx
                anchor_y = ground_y + cur_dy
                pg.draw.circle(surface, ACCENT_GOLD, (anchor_x, anchor_y), 5)
                pg.draw.line(surface, ACCENT_GOLD, (anchor_x - 10, anchor_y), (anchor_x + 10, anchor_y), 1)
                pg.draw.line(surface, ACCENT_GOLD, (anchor_x, anchor_y - 10), (anchor_x, anchor_y + 10), 1)
                # Draw momentum arrow
                vec_end_x = anchor_x + vel_x * 4
                vec_end_y = anchor_y + vel_y * 4
                pg.draw.line(surface, ACCENT_CYAN, (anchor_x, anchor_y), (vec_end_x, vec_end_y), 2)
                pg.draw.circle(surface, ACCENT_CYAN, (vec_end_x, vec_end_y), 3)

            # RICH FRAME TELEMETRY METADATA OVERLAY (HUD)
            hud_box = pg.Rect(canvas_rect.x + 10, canvas_rect.y + 10, 245, 90)
            pg.draw.rect(surface, (15, 12, 25), hud_box, border_radius=6)
            pg.draw.rect(surface, BORDER_COLOR, hud_box, width=1, border_radius=6)

            first_dx = self.frame_offsets.get(anim_key, {}).get("0", {}).get("dx", 0)
            loop_gap = abs(first_dx - cur_dx)

            t_info1 = tooltip_font.render(f"FRAME TELEMETRY: {frame_i + 1}/{len(frames)} (frac = {frac:.2f})", True, ACCENT_CYAN)
            t_info2 = tooltip_font.render(f"INSTANT VELOCITY: vx = {vel_x:+} px/f, vy = {vel_y:+} px/f", True, TEXT_COLOR)
            status_color = (50, 255, 100) if loop_gap <= 2 else (255, 180, 50)
            t_info3 = tooltip_font.render(f"LOOP BOUNDARY (N->0): Δx = {loop_gap} px ({'C1 SMOOTH' if loop_gap <= 2 else 'POPPING DETECTED'})", True, status_color)
            t_info4 = tooltip_font.render(f"RHEOLOGY CROSSFADE: {int(frac * visc * 100)}% sub-frame blend", True, ACCENT_PURPLE)

            surface.blit(t_info1, (hud_box.x + 8, hud_box.y + 6))
            surface.blit(t_info2, (hud_box.x + 8, hud_box.y + 26))
            surface.blit(t_info3, (hud_box.x + 8, hud_box.y + 46))
            surface.blit(t_info4, (hud_box.x + 8, hud_box.y + 66))

            # RENDER STAGNANT TARGET PLAYER DUMMY IN REACTION MODE
            if self.show_stagnant_player and self.mode != "SIMULATOR":
                dummy_dist = self.sliders["player_dummy_distance"].val
                player_x = center_x + dummy_dist
                player_y = ground_y

                # Select Player Sprite (Hurt vs Stand)
                is_hit = (self.player_hurt_timer > 0 and frame_i in self.hit_frame_map.get(anim_key, set()))
                player_surf = self.player_hurt_sprite if (is_hit and self.player_hurt_sprite) else self.player_stand_sprite

                if player_surf:
                    pw = int(player_surf.get_width() * 2.0)
                    ph = int(player_surf.get_height() * 2.0)
                    scaled_player = pg.transform.scale(player_surf, (pw, ph))
                    p_rect = pg.Rect(player_x - pw // 2, player_y - ph, pw, ph)

                    # Check collision with zombie hit_rect
                    hit_connected = False
                    if hit_rect and hit_rect.colliderect(p_rect):
                        hit_connected = True

                    surface.blit(scaled_player, p_rect)

                    # Player Hurtbox outline
                    pg.draw.rect(surface, (0, 220, 255), p_rect, width=2)
                    txt_p = tooltip_font.render("TARGET PLAYER", True, (0, 220, 255))
                    surface.blit(txt_p, (p_rect.x - 10, p_rect.y - 16))

                    # HUD Impact Status Banner
                    if hit_rect:
                        if hit_connected:
                            banner_txt = tooltip_font.render("STATUS: IMPACT CONNECTED! (FLUID STRIKE)", True, (50, 255, 100))
                        else:
                            banner_txt = tooltip_font.render("STATUS: STRIKE MISSED (OUT OF REACH)", True, (255, 80, 80))
                        surface.blit(banner_txt, (canvas_rect.x + 10, canvas_rect.y + 10))

            # Frame Info Overlay
            info_txt = tooltip_font.render(
                f"Frame {frame_i+1}/{len(frames)} | Pivot Offset: ({cur_dx:+d}, {cur_dy:+d}) px",
                True, ACCENT_GOLD
            )
            surface.blit(info_txt, (canvas_rect.x + 10, canvas_rect.bottom - 22))

        # Simulator Mode Extra Target Dummy Render
        if self.mode == "SIMULATOR":
            pdummy_rect = pg.Rect(int(self.sim_player_x - 15), int(self.sim_player_y - 30), 30, 60)
            pg.draw.rect(surface, (0, 200, 255), pdummy_rect, border_radius=4)
            txt_dummy = tooltip_font.render("DRAG TARGET DUMMY", True, (0, 255, 255))
            surface.blit(txt_dummy, (pdummy_rect.x - 25, pdummy_rect.y - 16))

        surface.set_clip(None)

    def draw_tooltip(self, surface: pg.Surface):
        m_pos = pg.mouse.get_pos()
        hovered_slider = None
        for slider in self.sliders.values():
            if slider.hovered:
                hovered_slider = slider
                break

        if hovered_slider:
            box_w, box_h = 360, 75
            box_x = max(10, min(m_pos[0] + 15, SCREEN_W - box_w - 10))
            box_y = max(10, min(m_pos[1] + 15, SCREEN_H - box_h - 10))

            rect = pg.Rect(box_x, box_y, box_w, box_h)
            pg.draw.rect(surface, (20, 16, 26), rect, border_radius=6)
            pg.draw.rect(surface, ACCENT_BLOOD, rect, width=1, border_radius=6)

            t1 = ui_font.render(f"METAPHOR: {hovered_slider.metaphor_label}", True, ACCENT_GOLD)
            t2 = help_font.render(f"Technical: {hovered_slider.tech_label}", True, TEXT_COLOR)
            t3 = tooltip_font.render(f"Math Formula: {hovered_slider.formula}", True, ACCENT_CYAN)

            surface.blit(t1, (box_x + 10, box_y + 8))
            surface.blit(t2, (box_x + 10, box_y + 30))
            surface.blit(t3, (box_x + 10, box_y + 50))

    def draw(self):
        screen.fill(BG_COLOR)

        # Header Title Banner
        title_txt = title_font.render("BLOOD ZOMBIE NECRO-LAB: CURATOR PLUGIN", True, ACCENT_BLOOD)
        screen.blit(title_txt, (30, 12))

        sub_txt = help_font.render("Sanguine Physics & Frame-Box Laboratory", True, TEXT_MUTED)
        screen.blit(sub_txt, (30, 38))

        # Mode Selector Buttons
        for btn in self.mode_buttons:
            btn.draw(screen)

        # Left Control Panel (Sliders)
        panel_left = pg.Rect(20, 70, 350, 630)
        pg.draw.rect(screen, PANEL_BG, panel_left, border_radius=8)
        pg.draw.rect(screen, BORDER_COLOR, panel_left, width=1, border_radius=8)

        # Section Headers depending on Mode
        if self.mode == "ANIMATION":
            hdr = ui_font.render("PULSE AND RHEOLOGY CONTROLS", True, ACCENT_BLOOD)
            screen.blit(hdr, (35, 115))
            self.sliders["anim_speed"].draw(screen)
            self.sliders["scale"].draw(screen)
            self.sliders["ground_offset"].draw(screen)
            self.sliders["lerp_viscosity"].draw(screen)
            self.sliders["frame_offset_x"].draw(screen)
            self.sliders["frame_offset_y"].draw(screen)
            self.sliders["hitbox_offset_x"].draw(screen)
        else:
            hdr = ui_font.render("VAMPIRIC COMBAT METRICS", True, ACCENT_BLOOD)
            screen.blit(hdr, (35, 115))
            self.sliders["max_health"].draw(screen)
            self.sliders["speed"].draw(screen)
            self.sliders["damage_scale"].draw(screen)
            self.sliders["knockback_scale"].draw(screen)
            self.sliders["detection_range"].draw(screen)
            self.sliders["attack_range"].draw(screen)
            self.sliders["attack_hitbox_width"].draw(screen)

        # Action Buttons
        self.btn_save.draw(screen)
        self.btn_reset.draw(screen)
        self.btn_auto_align.draw(screen)
        self.btn_harmonic_c1.draw(screen)

        # Main Center Viewport Canvas
        self.draw_canvas(screen)

        # Timeline Scrubber & Animation Controls
        self.draw_timeline(screen)
        for btn in self.anim_buttons:
            btn.draw(screen)

        self.btn_play_pause.draw(screen)
        self.btn_step_prev.draw(screen)
        self.btn_step_next.draw(screen)
        self.btn_slow_mo.draw(screen)

        # Overlay Viewport Toggle Buttons
        self.btn_toggle_hitbox.draw(screen)
        self.btn_toggle_hurtbox.draw(screen)
        self.btn_toggle_anchor.draw(screen)
        self.btn_toggle_onion.draw(screen)
        self.btn_toggle_player_dummy.draw(screen)
        self.btn_toggle_phase.draw(screen)
        self.btn_phase_mode.draw(screen)

        # Right Panel (VFX, Audio & Presets)
        panel_right = pg.Rect(900, 70, 360, 630)
        pg.draw.rect(screen, PANEL_BG, panel_right, border_radius=8)
        pg.draw.rect(screen, BORDER_COLOR, panel_right, width=1, border_radius=8)

        hdr_p = ui_font.render("SANGUINE PRESETS AND SHADERS", True, ACCENT_GOLD)
        screen.blit(hdr_p, (915, 115))

        for btn in self.preset_buttons:
            btn.draw(screen)

        hdr_vfx = ui_font.render("ARTERIAL SPRAY AND GHOST TRAIL", True, ACCENT_PURPLE)
        screen.blit(hdr_vfx, (915, 230))

        self.sliders["blood_spray_pressure"].draw(screen)
        self.sliders["player_dummy_distance"].draw(screen)
        self.sliders["necrotic_glow_r"].draw(screen)
        self.sliders["necrotic_glow_g"].draw(screen)
        self.sliders["necrotic_glow_b"].draw(screen)
        self.sliders["onion_skin_alpha"].draw(screen)
        self.sliders["sanguine_phase_shift"].draw(screen)

        # Toast Message Notification
        if self.toast_timer > 0:
            toast_surf = ui_font.render(self.toast_msg, True, (255, 255, 255))
            t_rect = toast_surf.get_rect(center=(SCREEN_W // 2, 90))
            bg_rect = t_rect.inflate(30, 12)
            pg.draw.rect(screen, ACCENT_BLOOD, bg_rect, border_radius=6)
            screen.blit(toast_surf, t_rect)

        # Tooltip Overlay
        self.draw_tooltip(screen)

        pg.display.flip()

    def handle_events(self):
        for event in pg.event.get():
            if event.type == pg.QUIT:
                self.running = False
            elif event.type == pg.KEYDOWN:
                if event.key == pg.K_ESCAPE:
                    self.running = False
                elif event.key == pg.K_SPACE:
                    self.toggle_play_pause()
                elif event.key == pg.K_LEFT:
                    # Arrow Key Nudge Frame Position
                    if pg.key.get_mods() & pg.KMOD_SHIFT:
                        cur_dx, cur_dy = self.get_current_frame_offset()
                        self.set_current_frame_offset(cur_dx - 5, cur_dy)
                    else:
                        self.step_frame_backward()
                elif event.key == pg.K_RIGHT:
                    if pg.key.get_mods() & pg.KMOD_SHIFT:
                        cur_dx, cur_dy = self.get_current_frame_offset()
                        self.set_current_frame_offset(cur_dx + 5, cur_dy)
                    else:
                        self.step_frame_forward()
                elif event.key == pg.K_UP:
                    cur_dx, cur_dy = self.get_current_frame_offset()
                    step = 5 if pg.key.get_mods() & pg.KMOD_SHIFT else 1
                    self.set_current_frame_offset(cur_dx, cur_dy - step)
                elif event.key == pg.K_DOWN:
                    cur_dx, cur_dy = self.get_current_frame_offset()
                    step = 5 if pg.key.get_mods() & pg.KMOD_SHIFT else 1
                    self.set_current_frame_offset(cur_dx, cur_dy + step)

            # Handle Sliders Events
            for slider in self.sliders.values():
                slider.handle_event(event)

            # Handle Buttons Events
            self.btn_save.handle_event(event)
            self.btn_reset.handle_event(event)
            self.btn_auto_align.handle_event(event)
            self.btn_harmonic_c1.handle_event(event)
            self.btn_play_pause.handle_event(event)
            self.btn_step_prev.handle_event(event)
            self.btn_step_next.handle_event(event)
            self.btn_slow_mo.handle_event(event)
            self.btn_toggle_hitbox.handle_event(event)
            self.btn_toggle_hurtbox.handle_event(event)
            self.btn_toggle_anchor.handle_event(event)
            self.btn_toggle_onion.handle_event(event)
            self.btn_toggle_player_dummy.handle_event(event)
            self.btn_toggle_phase.handle_event(event)
            self.btn_phase_mode.handle_event(event)

            for btn in self.mode_buttons:
                btn.handle_event(event)
            for btn in self.preset_buttons:
                btn.handle_event(event)
            for btn in self.anim_buttons:
                btn.handle_event(event)

            # Target Dummy Dragging in SIMULATOR Mode
            if self.mode == "SIMULATOR":
                if event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
                    m_pos = event.pos
                    if math.hypot(m_pos[0] - self.sim_player_x, m_pos[1] - self.sim_player_y) <= 40:
                        self.dragging_player = True
                elif event.type == pg.MOUSEBUTTONUP and event.button == 1:
                    self.dragging_player = False
                elif event.type == pg.MOUSEMOTION and self.dragging_player:
                    self.sim_player_x = event.pos[0]
                    self.sim_player_y = event.pos[1]

    def run(self):
        while self.running:
            dt = self.clock.tick(60) / 1000.0
            self.handle_events()
            self.update(dt)
            self.draw()

        pg.quit()


if __name__ == "__main__":
    app = BloodZombieEditorApp()
    app.run()
