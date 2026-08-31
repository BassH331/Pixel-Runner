#!/usr/bin/env python3
"""
Shadow Tuning & Alignment Studio.

An interactive developer GUI tool for visualizing, modifying, and saving
per-entity shadow configurations (opacity, squash ratio, ground offset,
altitude fading, snap tolerance, width scaling) in real-time.
"""

import os
import sys
import math
import pygame as pg
from unittest.mock import MagicMock

# Ensure repository root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Mock audio manager for entity initializations
mock_audio = MagicMock()

pg.init()
pg.font.init()

SCREEN_W, SCREEN_H = 1280, 720
screen = pg.display.set_mode((SCREEN_W, SCREEN_H))
pg.display.set_caption("Pixel-Runner: Shadow Tuning & Alignment Studio")

# System & Entity imports
from v3x_zulfiqar_gideon import AssetManager
from src.game.systems.shadow_registry import ShadowRegistry, ShadowProfile
from src.game.systems.shadow_renderer import ShadowRenderer
from src.game.entities.hitbox_registry import HitboxRegistry
from src.game.entities.player import Player
from src.game.entities.skeleton import Skeleton
from src.game.entities.enemy import Enemy
from src.game.entities.wizard_npc import WizardNPC
from src.game.entities.generic_npc import GenericNPC
from src.game.entities.fire_wizard import FireWizard

# Fonts
try:
    font_title = pg.font.Font("assets/graphics/Darinia/Darinia.ttf", 26)
    font_section = pg.font.Font("assets/graphics/Darinia/Darinia.ttf", 18)
    font_ui = pg.font.Font("assets/graphics/Darinia/Darinia.ttf", 14)
    font_small = pg.font.SysFont("Arial", 12)
    font_bold = pg.font.SysFont("Arial", 13, bold=True)
except Exception:
    font_title = pg.font.SysFont("Arial", 24, bold=True)
    font_section = pg.font.SysFont("Arial", 16, bold=True)
    font_ui = pg.font.SysFont("Arial", 13)
    font_small = pg.font.SysFont("Arial", 11)
    font_bold = pg.font.SysFont("Arial", 13, bold=True)


# Color Palette
BG_DARK = (18, 20, 26)
PANEL_BG = (26, 30, 40)
PANEL_BORDER = (45, 52, 68)
ACCENT_BLUE = (70, 130, 240)
ACCENT_GREEN = (60, 190, 120)
ACCENT_RED = (220, 70, 70)
TEXT_WHITE = (240, 242, 248)
TEXT_MUTED = (140, 148, 168)
CARD_BG = (34, 40, 54)
CARD_HOVER = (44, 52, 70)
CARD_ACTIVE = (50, 75, 120)


class Slider:
    """Interactive GUI slider with label, numeric readout, and dragging."""

    def __init__(self, label: str, key: str, x: int, y: int, w: int, min_val: float, max_val: float, default_val: float, is_float: bool = False, step: float = 1.0):
        self.label = label
        self.key = key
        self.rect = pg.Rect(x, y, w, 8)
        self.min_val = min_val
        self.max_val = max_val
        self.val = default_val
        self.is_float = is_float
        self.step = step
        self.handle_r = 8
        self.dragging = False

    def get_handle_pos(self) -> tuple[int, int]:
        ratio = (self.val - self.min_val) / max(1e-5, (self.max_val - self.min_val))
        ratio = max(0.0, min(1.0, ratio))
        return int(self.rect.x + ratio * self.rect.width), self.rect.centery

    def set_value(self, val: float) -> None:
        self.val = max(self.min_val, min(self.max_val, val))
        if not self.is_float:
            self.val = int(round(self.val))

    def update_from_mouse(self, mouse_x: int) -> None:
        rel = (mouse_x - self.rect.x) / max(1, self.rect.width)
        rel = max(0.0, min(1.0, rel))
        new_val = self.min_val + rel * (self.max_val - self.min_val)
        if self.is_float:
            new_val = round(new_val / self.step) * self.step
        else:
            new_val = int(round(new_val))
        self.val = max(self.min_val, min(self.max_val, new_val))

    def handle_event(self, event: pg.event.Event) -> bool:
        if event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
            hx, hy = self.get_handle_pos()
            dist = math.hypot(event.pos[0] - hx, event.pos[1] - hy)
            if dist <= self.handle_r + 4 or self.rect.inflate(0, 14).collidepoint(event.pos):
                self.dragging = True
                self.update_from_mouse(event.pos[0])
                return True
        elif event.type == pg.MOUSEBUTTONUP and event.button == 1:
            if self.dragging:
                self.dragging = False
                return True
        elif event.type == pg.MOUSEMOTION and self.dragging:
            self.update_from_mouse(event.pos[0])
            return True
        return False

    def draw(self, surface: pg.Surface) -> None:
        # Title and value
        val_str = f"{self.val:.2f}" if self.is_float else f"{int(self.val)}"
        lbl_surf = font_bold.render(self.label, True, TEXT_WHITE)
        val_surf = font_bold.render(val_str, True, ACCENT_BLUE)
        surface.blit(lbl_surf, (self.rect.x, self.rect.y - 18))
        surface.blit(val_surf, (self.rect.right - val_surf.get_width(), self.rect.y - 18))

        # Track
        pg.draw.rect(surface, (40, 46, 60), self.rect, border_radius=4)
        hx, hy = self.get_handle_pos()
        fill_rect = pg.Rect(self.rect.x, self.rect.y, max(0, hx - self.rect.x), self.rect.height)
        pg.draw.rect(surface, ACCENT_BLUE, fill_rect, border_radius=4)

        # Handle
        handle_color = (255, 255, 255) if not self.dragging else (160, 200, 255)
        pg.draw.circle(surface, handle_color, (hx, hy), self.handle_r)
        pg.draw.circle(surface, (30, 40, 60), (hx, hy), self.handle_r - 3)


class Button:
    """Clickable UI button with hover states and callback."""

    def __init__(self, text: str, x: int, y: int, w: int, h: int, color=ACCENT_BLUE, text_color=TEXT_WHITE):
        self.text = text
        self.rect = pg.Rect(x, y, w, h)
        self.color = color
        self.text_color = text_color
        self.hovered = False

    def handle_event(self, event: pg.event.Event) -> bool:
        if event.type == pg.MOUSEMOTION:
            self.hovered = self.rect.collidepoint(event.pos)
        elif event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                return True
        return False

    def draw(self, surface: pg.Surface) -> None:
        c = tuple(min(255, int(ch * 1.15)) for ch in self.color) if self.hovered else self.color
        pg.draw.rect(surface, c, self.rect, border_radius=6)
        pg.draw.rect(surface, (255, 255, 255, 60), self.rect, width=1, border_radius=6)

        txt_surf = font_bold.render(self.text, True, self.text_color)
        tx = self.rect.centerx - txt_surf.get_width() // 2
        ty = self.rect.centery - txt_surf.get_height() // 2
        surface.blit(txt_surf, (tx, ty))


class ToastNotification:
    """Floating feedback toast."""

    def __init__(self):
        self.message = ""
        self.timer = 0.0
        self.color = ACCENT_GREEN

    def show(self, msg: str, color=ACCENT_GREEN, duration: float = 2.5):
        self.message = msg
        self.color = color
        self.timer = duration

    def update(self, dt: float):
        if self.timer > 0.0:
            self.timer -= dt

    def draw(self, surface: pg.Surface):
        if self.timer <= 0.0:
            return
        alpha = min(255, int((self.timer / 0.4) * 255)) if self.timer < 0.4 else 255
        txt = font_bold.render(self.message, True, TEXT_WHITE)
        w = txt.get_width() + 32
        h = 36
        x = SCREEN_W // 2 - w // 2
        y = 20

        bg = pg.Surface((w, h), pg.SRCALPHA)
        pg.draw.rect(bg, (*self.color[:3], int(alpha * 0.9)), (0, 0, w, h), border_radius=8)
        pg.draw.rect(bg, (255, 255, 255, int(alpha * 0.4)), (0, 0, w, h), width=1, border_radius=8)
        bg.blit(txt, (16, (h - txt.get_height()) // 2))
        surface.blit(bg, (x, y))


class ShadowEditorApp:
    """Main Shadow Editor application."""

    def __init__(self):
        self.clock = pg.time.Clock()
        self.running = True
        self.toast = ToastNotification()

        # Available entities for tuning
        self.entity_list = [
            {"name": "Player (Kaelen)", "key": "player", "category": "PLAYER"},
            {"name": "Skeleton Minion", "key": "skeleton", "category": "ENEMIES"},
            {"name": "Ambient Bat", "key": "enemy", "category": "AIRBORNE"},
            {"name": "Necromancer NPC", "key": "generic_npc_masked_man", "category": "NPCS"},
            {"name": "Moonstone Keeper", "key": "generic_npc_moonstone_keeper", "category": "NPCS"},
            {"name": "Spirit of Scythe (Eye)", "key": "evil_eye", "category": "AIRBORNE"},
            {"name": "Old Wizard NPC", "key": "wizard_npc", "category": "NPCS"},
            {"name": "Fire Wizard", "key": "fire_wizard", "category": "ENEMIES"},
            {"name": "Green Monster Boss", "key": "green_monster", "category": "BOSSES"},
        ]
        self.current_entity_idx = 0
        self.entity_instance = None
        self.active_state_name = "idle"
        self.available_states: list[str] = []

        # Backgrounds
        self.bg_mode = 0  # 0: Forest Path, 1: Dark Slate, 2: Checkerboard
        self.ground_line_visible = True

        # Jump / Altitude simulation
        self.simulated_altitude = 0.0
        self.auto_jump_bounce = False
        self.jump_timer = 0.0

        # Sliders
        panel_x = 940
        self.sliders = {
            "alpha": Slider("Shadow Opacity (Alpha)", "alpha", panel_x, 150, 300, 0, 255, 120, is_float=False),
            "squash_ratio": Slider("Squash Factor (Perspective)", "squash_ratio", panel_x, 210, 300, 0.05, 0.60, 0.25, is_float=True, step=0.01),
            "y_offset": Slider("Vertical Shift (Offset Y)", "y_offset", panel_x, 270, 300, -30, 30, 0, is_float=False),
            "scale_mult": Slider("Width Scale Multiplier", "scale_mult", panel_x, 330, 300, 0.5, 2.0, 1.0, is_float=True, step=0.05),
            "fade_height": Slider("Fade Altitude Max", "fade_height", panel_x, 390, 300, 50.0, 800.0, 250.0, is_float=False, step=10.0),
            "ground_snap": Slider("Ground Snap Tolerance", "ground_snap", panel_x, 450, 300, 0.0, 30.0, 12.0, is_float=False),
        }
        self.altitude_slider = Slider("Test Airborne Altitude", "altitude", 320, 660, 380, 0.0, 500.0, 0.0, is_float=False)

        # Buttons
        self.btn_save = Button("SAVE CONFIG", panel_x, 595, 140, 38, color=ACCENT_GREEN)
        self.btn_reset = Button("RESET PROFILE", panel_x + 155, 595, 145, 38, color=ACCENT_RED)
        self.btn_revert = Button("REVERT", panel_x, 645, 300, 32, color=(60, 68, 85))

        self.btn_toggle_jump = Button("AUTO JUMP: OFF", 720, 650, 150, 32, color=(50, 60, 80))
        self.btn_toggle_bg = Button("CYCLE BG", 800, 80, 100, 28, color=(45, 52, 70))
        self.btn_toggle_guide = Button("GUIDE: ON", 700, 80, 90, 28, color=(45, 52, 70))

        # Preset Buttons
        self.preset_buttons = [
            Button("Sharp Pixel", panel_x, 520, 95, 26, color=(50, 60, 80)),
            Button("Soft Ambient", panel_x + 102, 520, 95, 26, color=(50, 60, 80)),
            Button("Airborne", panel_x + 204, 520, 95, 26, color=(50, 60, 80)),
        ]

        # Load entity
        self.load_selected_entity()

    def load_selected_entity(self):
        """Instantiate the selected entity and synchronize slider values with its profile."""
        ent_info = self.entity_list[self.current_entity_idx]
        key = ent_info["key"]

        # Instantiate representative entity
        try:
            if key == "player":
                self.entity_instance = Player(600, 540, mock_audio)
            elif key == "skeleton":
                self.entity_instance = Skeleton(600, 540, mock_audio)
            elif key == "enemy":
                self.entity_instance = Enemy(mock_audio)
                self.entity_instance.rect.center = (600, 300)
            elif key == "wizard_npc":
                self.entity_instance = WizardNPC(600, 540, "Greetings, traveler.")
            elif key == "generic_npc_masked_man":
                self.entity_instance = GenericNPC(600, 540, "assets/graphics/Necromancer/Idle", "Master of Secrets.", is_intro_npc=True)
            elif key == "generic_npc_moonstone_keeper":
                self.entity_instance = GenericNPC(600, 540, "assets/graphics/Moonstone_Keeper Eldermoon_Grove - By SUCART/Idle-MoonstoneKeeper-SUCART/No BG", "Gatekeeper Territory.")
            elif key == "evil_eye":
                self.entity_instance = GenericNPC(600, 380, "assets/graphics/Evil Eye Beast For Itch/Idle", "I hunger for souls.", title="Spirit of the Scythe")
                self.entity_instance.visible = True
            elif key == "fire_wizard":
                self.entity_instance = FireWizard(600, 540, mock_audio)
            else:
                self.entity_instance = Player(600, 540, mock_audio)
        except Exception as e:
            print(f"[ShadowEditor] Error creating entity {key}: {e}")
            self.entity_instance = Player(600, 540, mock_audio)

        # Extract available animation states
        self.available_states = []
        if hasattr(self.entity_instance, "animations") and self.entity_instance.animations:
            for st in self.entity_instance.animations.keys():
                st_name = st.name.lower() if hasattr(st, "name") else str(st).lower()
                self.available_states.append(st_name)
        if not self.available_states:
            self.available_states = ["idle"]
        self.active_state_name = self.available_states[0]

        # Load profile values into sliders
        profile = ShadowRegistry.get_profile(key)
        self.sliders["alpha"].set_value(profile.alpha)
        self.sliders["squash_ratio"].set_value(profile.squash_ratio)
        self.sliders["y_offset"].set_value(profile.y_offset)
        self.sliders["scale_mult"].set_value(profile.scale_mult)
        self.sliders["fade_height"].set_value(profile.fade_height)
        self.sliders["ground_snap"].set_value(profile.ground_snap)

    def apply_current_sliders_to_profile(self) -> ShadowProfile:
        return ShadowProfile(
            alpha=int(self.sliders["alpha"].val),
            squash_ratio=float(self.sliders["squash_ratio"].val),
            y_offset=int(self.sliders["y_offset"].val),
            scale_mult=float(self.sliders["scale_mult"].val),
            fade_height=float(self.sliders["fade_height"].val),
            ground_snap=float(self.sliders["ground_snap"].val),
        )

    def apply_preset(self, preset_name: str):
        if preset_name == "Sharp Pixel":
            self.sliders["alpha"].set_value(160)
            self.sliders["squash_ratio"].set_value(0.20)
            self.sliders["y_offset"].set_value(0)
            self.sliders["scale_mult"].set_value(1.0)
            self.sliders["fade_height"].set_value(200.0)
            self.sliders["ground_snap"].set_value(10.0)
            self.toast.show("Applied 'Sharp Pixel' Preset")
        elif preset_name == "Soft Ambient":
            self.sliders["alpha"].set_value(80)
            self.sliders["squash_ratio"].set_value(0.30)
            self.sliders["y_offset"].set_value(1)
            self.sliders["scale_mult"].set_value(1.15)
            self.sliders["fade_height"].set_value(350.0)
            self.sliders["ground_snap"].set_value(14.0)
            self.toast.show("Applied 'Soft Ambient' Preset")
        elif preset_name == "Airborne":
            self.sliders["alpha"].set_value(90)
            self.sliders["squash_ratio"].set_value(0.22)
            self.sliders["y_offset"].set_value(0)
            self.sliders["scale_mult"].set_value(1.0)
            self.sliders["fade_height"].set_value(650.0)
            self.sliders["ground_snap"].set_value(0.0)
            self.toast.show("Applied 'Airborne' Preset")

    def save_current_profile(self):
        key = self.entity_list[self.current_entity_idx]["key"]
        profile = self.apply_current_sliders_to_profile()
        if ShadowRegistry.save_profile(key, profile):
            self.toast.show(f"Saved [{key}] to shadow_config.json", ACCENT_GREEN)
        else:
            self.toast.show(f"Failed to save [{key}]", ACCENT_RED)

    def reset_current_profile(self):
        key = self.entity_list[self.current_entity_idx]["key"]
        default_prof = ShadowRegistry.DEFAULTS.get(key, ShadowRegistry.DEFAULTS["default"])
        self.sliders["alpha"].set_value(default_prof.alpha)
        self.sliders["squash_ratio"].set_value(default_prof.squash_ratio)
        self.sliders["y_offset"].set_value(default_prof.y_offset)
        self.sliders["scale_mult"].set_value(default_prof.scale_mult)
        self.sliders["fade_height"].set_value(default_prof.fade_height)
        self.sliders["ground_snap"].set_value(default_prof.ground_snap)
        self.toast.show(f"Reset [{key}] to Default", (220, 140, 60))

    def handle_events(self):
        for event in pg.event.get():
            if event.type == pg.QUIT:
                self.running = False
                return

            if event.type == pg.KEYDOWN:
                if event.key == pg.K_ESCAPE:
                    self.running = False
                elif event.key in (pg.K_s, pg.K_RETURN) and (pg.key.get_mods() & pg.KMOD_CTRL):
                    self.save_current_profile()
                elif event.key == pg.K_SPACE:
                    self.auto_jump_bounce = not self.auto_jump_bounce
                    self.btn_toggle_jump.text = "AUTO JUMP: ON" if self.auto_jump_bounce else "AUTO JUMP: OFF"

            # Sidebar entity selection clicks
            if event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = event.pos
                if 10 <= mx <= 260 and 80 <= my <= 680:
                    item_h = 52
                    idx = (my - 80) // item_h
                    if 0 <= idx < len(self.entity_list) and idx != self.current_entity_idx:
                        self.current_entity_idx = idx
                        self.load_selected_entity()

                # Animation state pill clicks
                if 280 <= mx <= 920 and 80 <= my <= 120:
                    pill_x = 290
                    for st in self.available_states:
                        w = font_bold.size(st.upper())[0] + 20
                        if pill_x <= mx <= pill_x + w:
                            self.active_state_name = st
                            # Switch actor state if possible
                            for enum_st in getattr(self.entity_instance, "animations", {}).keys():
                                name = enum_st.name.lower() if hasattr(enum_st, "name") else str(enum_st).lower()
                                if name == st and self.entity_instance is not None and hasattr(self.entity_instance, "set_state"):
                                    self.entity_instance.set_state(enum_st, force=True)
                                    break
                            break
                        pill_x += w + 8

            # Sliders
            for s in self.sliders.values():
                s.handle_event(event)
            self.altitude_slider.handle_event(event)

            # Buttons
            if self.btn_save.handle_event(event):
                self.save_current_profile()
            if self.btn_reset.handle_event(event):
                self.reset_current_profile()
            if self.btn_revert.handle_event(event):
                self.load_selected_entity()
                self.toast.show("Reverted Unsaved Changes", (180, 180, 180))
            if self.btn_toggle_bg.handle_event(event):
                self.bg_mode = (self.bg_mode + 1) % 3
            if self.btn_toggle_guide.handle_event(event):
                self.ground_line_visible = not self.ground_line_visible
                self.btn_toggle_guide.text = "GUIDE: ON" if self.ground_line_visible else "GUIDE: OFF"
            if self.btn_toggle_jump.handle_event(event):
                self.auto_jump_bounce = not self.auto_jump_bounce
                self.btn_toggle_jump.text = "AUTO JUMP: ON" if self.auto_jump_bounce else "AUTO JUMP: OFF"

            for pb in self.preset_buttons:
                if pb.handle_event(event):
                    self.apply_preset(pb.text)

    def update(self, dt: float):
        self.toast.update(dt)

        # Update entity animation smoothly without invoking combat/AI dependencies
        if self.entity_instance and hasattr(self.entity_instance, "animations") and self.entity_instance.animations:
            cur_state = self.entity_instance.state
            frames = self.entity_instance.animations.get(cur_state)
            if frames:
                anim_spd = 0.15
                if hasattr(self.entity_instance, "state_configs") and self.entity_instance.state_configs:
                    cfg = self.entity_instance.state_configs.get(cur_state)
                    if cfg and hasattr(cfg, "animation_speed") and cfg.animation_speed:
                        anim_spd = float(cfg.animation_speed)
                self.entity_instance.animation_index = (
                    getattr(self.entity_instance, "animation_index", 0.0) + dt * 60.0 * anim_spd
                ) % len(frames)
                self.entity_instance.image = frames[int(self.entity_instance.animation_index)]

        # Jump simulation
        if self.auto_jump_bounce:
            self.jump_timer += dt * 3.5
            self.simulated_altitude = max(0.0, math.sin(self.jump_timer) * 160.0)
            self.altitude_slider.set_value(self.simulated_altitude)
        else:
            self.simulated_altitude = self.altitude_slider.val

    def draw_viewport_background(self, viewport_rect: pg.Rect):
        """Render selected terrain / background in the preview viewport."""
        screen.set_clip(viewport_rect)

        if self.bg_mode == 0:
            # Forest Road terrain
            try:
                forest_bg = AssetManager.get_texture("assets/graphics/background images/background.png")
                if forest_bg:
                    scaled_bg = pg.transform.scale(forest_bg, (viewport_rect.width, viewport_rect.height))
                    screen.blit(scaled_bg, viewport_rect.topleft)
            except Exception:
                pg.draw.rect(screen, (35, 45, 30), viewport_rect)
            # Dirt road strip
            road_rect = pg.Rect(viewport_rect.x, 500, viewport_rect.width, 140)
            pg.draw.rect(screen, (120, 110, 80), road_rect)
            pg.draw.rect(screen, (85, 120, 60), (viewport_rect.x, 620, viewport_rect.width, 20))
        elif self.bg_mode == 1:
            # Dark Slate Studio
            pg.draw.rect(screen, (22, 26, 35), viewport_rect)
            for y in range(viewport_rect.y, viewport_rect.bottom, 40):
                pg.draw.line(screen, (30, 36, 48), (viewport_rect.x, y), (viewport_rect.right, y), 1)
        else:
            # Checkerboard pattern
            sq = 24
            for rx in range(viewport_rect.x, viewport_rect.right, sq):
                for ry in range(viewport_rect.y, viewport_rect.bottom, sq):
                    color = (38, 42, 54) if ((rx // sq + ry // sq) % 2 == 0) else (28, 32, 42)
                    pg.draw.rect(screen, color, (rx, ry, sq, sq))

        # Ground reference line
        ground_y = 540
        if self.ground_line_visible:
            pg.draw.line(screen, (240, 80, 80, 180), (viewport_rect.x, ground_y), (viewport_rect.right, ground_y), 2)
            lbl = font_small.render("Ground Plane Y: 540", True, (240, 100, 100))
            screen.blit(lbl, (viewport_rect.x + 10, ground_y - 18))

        # Draw Character and Shadow
        if self.entity_instance:
            # Anchor feet to ground_y, lifted by simulated altitude
            orig_rect = self.entity_instance.rect.copy()
            center_x = viewport_rect.centerx

            # Determine true feet level
            img = getattr(self.entity_instance, "image", None)
            if img:
                img_br = img.get_bounding_rect()
                feet_in_img = img_br.bottom if img_br.height > 0 else img.get_height()
                offset_y = self.entity_instance.image_offset.y if getattr(self.entity_instance, "image_offset", None) else 0

                # Position entity so visual feet touch (ground_y - altitude)
                self.entity_instance.rect.centerx = center_x
                self.entity_instance.rect.top = int(ground_y - self.simulated_altitude - feet_in_img + offset_y)

                # Render Shadow using active slider parameters directly onto ground_y
                ShadowRenderer.render_entity_shadow(
                    screen,
                    self.entity_instance,
                    ground_y=ground_y,
                    base_alpha=int(self.sliders["alpha"].val),
                    squash_ratio=float(self.sliders["squash_ratio"].val),
                    fade_height=float(self.sliders["fade_height"].val),
                    ground_snap=float(self.sliders["ground_snap"].val),
                    y_offset=int(self.sliders["y_offset"].val),
                    scale_mult=float(self.sliders["scale_mult"].val),
                )

                # Render Entity sprite
                if hasattr(self.entity_instance, "draw"):
                    self.entity_instance.draw(screen)
                else:
                    draw_pos = self.entity_instance.rect.topleft - (self.entity_instance.image_offset if getattr(self.entity_instance, "image_offset", None) else pg.Vector2(0, 0))
                    screen.blit(img, draw_pos)

                self.entity_instance.rect = orig_rect

        screen.set_clip(None)

    def draw(self):
        screen.fill(BG_DARK)

        # ── Top Bar ──────────────────────────────────────────────────────────
        pg.draw.rect(screen, PANEL_BG, (0, 0, SCREEN_W, 64))
        pg.draw.line(screen, PANEL_BORDER, (0, 64), (SCREEN_W, 64), 2)
        title_txt = font_title.render("SHADOW TUNING & ALIGNMENT STUDIO", True, TEXT_WHITE)
        sub_txt = font_small.render("Graphical Parameter Studio & Profile Synchronizer", True, TEXT_MUTED)
        screen.blit(title_txt, (20, 10))
        screen.blit(sub_txt, (22, 40))

        # ── Left Sidebar (Entity Selector) ───────────────────────────────────
        sidebar_rect = pg.Rect(0, 64, 270, SCREEN_H - 64)
        pg.draw.rect(screen, PANEL_BG, sidebar_rect)
        pg.draw.line(screen, PANEL_BORDER, (270, 64), (270, SCREEN_H), 2)

        sec_lbl = font_section.render("ENTITIES", True, TEXT_WHITE)
        screen.blit(sec_lbl, (20, 80))

        item_y = 110
        for i, ent in enumerate(self.entity_list):
            is_active = (i == self.current_entity_idx)
            card_rect = pg.Rect(12, item_y, 246, 44)
            card_col = CARD_ACTIVE if is_active else CARD_BG
            pg.draw.rect(screen, card_col, card_rect, border_radius=6)
            if is_active:
                pg.draw.rect(screen, ACCENT_BLUE, card_rect, width=2, border_radius=6)

            cat_txt = font_small.render(ent["category"], True, ACCENT_BLUE if is_active else TEXT_MUTED)
            name_txt = font_bold.render(ent["name"], True, TEXT_WHITE)
            screen.blit(cat_txt, (22, item_y + 5))
            screen.blit(name_txt, (22, item_y + 20))
            item_y += 50

        # ── Center Viewport ──────────────────────────────────────────────────
        viewport_rect = pg.Rect(272, 66, 646, 560)
        self.draw_viewport_background(viewport_rect)
        pg.draw.rect(screen, PANEL_BORDER, viewport_rect, width=2)

        # Animation State Pills
        pill_x = 290
        for st in self.available_states:
            is_act = (st == self.active_state_name)
            tw, th = font_bold.size(st.upper())
            pw = tw + 20
            pr = pg.Rect(pill_x, 78, pw, 28)
            pcol = ACCENT_BLUE if is_act else (35, 42, 58)
            pg.draw.rect(screen, pcol, pr, border_radius=14)
            ptxt = font_bold.render(st.upper(), True, TEXT_WHITE if is_act else TEXT_MUTED)
            screen.blit(ptxt, (pill_x + 10, 84))
            pill_x += pw + 8

        self.btn_toggle_guide.draw(screen)
        self.btn_toggle_bg.draw(screen)

        # Altitude Simulation Bar (Bottom Viewport)
        pg.draw.rect(screen, PANEL_BG, (272, 630, 646, 90))
        pg.draw.line(screen, PANEL_BORDER, (272, 630), (918, 630), 2)
        self.altitude_slider.draw(screen)
        self.btn_toggle_jump.draw(screen)

        # ── Right Inspector Panel ────────────────────────────────────────────
        inspector_rect = pg.Rect(920, 64, 360, SCREEN_H - 64)
        pg.draw.rect(screen, PANEL_BG, inspector_rect)
        pg.draw.line(screen, PANEL_BORDER, (920, 64), (920, SCREEN_H), 2)

        ins_title = font_section.render("SHADOW PARAMETERS", True, TEXT_WHITE)
        screen.blit(ins_title, (940, 80))

        # Sliders
        for s in self.sliders.values():
            s.draw(screen)

        # Presets Header
        preset_lbl = font_bold.render("QUICK PRESETS", True, TEXT_MUTED)
        screen.blit(preset_lbl, (940, 498))
        for pb in self.preset_buttons:
            pb.draw(screen)

        # Action Buttons
        self.btn_save.draw(screen)
        self.btn_reset.draw(screen)
        self.btn_revert.draw(screen)

        # Toast
        self.toast.draw(screen)

        pg.display.flip()

    def run(self):
        while self.running:
            dt = self.clock.tick(60) / 1000.0
            self.handle_events()
            self.update(dt)
            self.draw()

        pg.quit()


if __name__ == "__main__":
    app = ShadowEditorApp()
    app.run()
