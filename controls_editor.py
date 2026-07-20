#!/usr/bin/env python3
"""
controls_editor.py
Interactive Control Mapping Plugin & Animation Visualizer for Pixel-Runner.
Allows remapping controls for PC Keyboard and USB Joystick/Gamepad with live action animation previews and local JSON saving.
Features a clean, modern UI layout with badge pill keycaps, non-overlapping columns, and crisp typography.
"""

import os
import sys
import json
import pygame as pg
from typing import Dict, List, Optional, Tuple, Any

# Ensure import access to src package
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from src.game.controls_manager import (
    ControlsManager,
    ACTIONS,
    ACTION_METADATA,
    JOYSTICK_LABELS,
)

# Initialize Pygame
pg.init()
pg.font.init()
pg.joystick.init()

SCREEN_W, SCREEN_H = 1280, 720

# Theme Colors (Sleek Dark Slate & Neon Palette)
BG_COLOR = (16, 18, 24)
PANEL_BG = (24, 27, 36)
PANEL_HEADER_BG = (32, 36, 48)
PREVIEW_BG = (10, 12, 16)
TEXT_COLOR = (240, 242, 248)
ACCENT_GREEN = (0, 230, 118)
ACCENT_CYAN = (0, 229, 255)
ACCENT_PURPLE = (170, 0, 255)
ACCENT_BLUE = (0, 145, 234)
ACCENT_ORANGE = (255, 145, 0)
TEXT_MUTED = (140, 148, 170)
BORDER_COLOR = (42, 48, 64)
BORDER_LIGHT = (60, 68, 90)
HIGHLIGHT_BG = (36, 42, 58)
LISTEN_BG = (70, 25, 90)
BADGE_BG = (18, 28, 44)
BADGE_BORDER = (0, 140, 200)

# Asset paths matching Player state machine
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


def get_fonts() -> Tuple[pg.font.Font, pg.font.Font, pg.font.Font, pg.font.Font, pg.font.Font]:
    """Clean, high-legibility UI sans-serif fonts."""
    font_names = "dejavusans,liberationsans,ubuntu,arial,helvetica,sans-serif"
    mono_names = "monospace,dejavusansmono,liberationmono,consolas"
    
    title_font = pg.font.SysFont(font_names, 20, bold=True)
    header_font = pg.font.SysFont(font_names, 15, bold=True)
    ui_font = pg.font.SysFont(font_names, 13, bold=True)
    value_font = pg.font.SysFont(font_names, 12)
    badge_font = pg.font.SysFont(mono_names, 12, bold=True)
    return title_font, header_font, ui_font, value_font, badge_font


class Button:
    def __init__(
        self,
        text: str,
        x: int,
        y: int,
        w: int,
        h: int,
        callback: Any,
        active: bool = False,
        color_override: Optional[Tuple[int, int, int]] = None,
    ):
        self.text = text
        self.rect = pg.Rect(x, y, w, h)
        self.callback = callback
        self.active = active
        self.color_override = color_override

    def draw(self, surface: pg.Surface, font: pg.font.Font) -> None:
        if self.color_override:
            base_color = self.color_override
        else:
            base_color = ACCENT_PURPLE if self.active else (38, 44, 58)

        m_pos = pg.mouse.get_pos()
        is_hover = self.rect.collidepoint(m_pos)

        if is_hover:
            draw_color = (
                min(255, base_color[0] + 35),
                min(255, base_color[1] + 35),
                min(255, base_color[2] + 35),
            )
            border = ACCENT_CYAN if not self.color_override else (255, 255, 255)
        else:
            draw_color = base_color
            border = ACCENT_CYAN if self.active else BORDER_LIGHT

        pg.draw.rect(surface, draw_color, self.rect, border_radius=6)
        pg.draw.rect(surface, border, self.rect, width=1, border_radius=6)

        txt = font.render(self.text, True, (255, 255, 255))
        txt_rect = txt.get_rect(center=self.rect.center)
        surface.blit(txt, txt_rect)

    def handle_event(self, event: pg.event.Event) -> bool:
        if event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                if self.callback:
                    self.callback()
                return True
        return False


class ControlsEditorApp:
    def __init__(self, surface: Optional[pg.Surface] = None):
        self.external_surface = surface
        if surface is None:
            self.screen = pg.display.set_mode((SCREEN_W, SCREEN_H))
            pg.display.set_caption("Pixel-Runner: Control Mapping Plugin")
        else:
            self.screen = surface

        self.clock = pg.time.Clock()
        self.running = True

        (
            self.title_font,
            self.header_font,
            self.ui_font,
            self.value_font,
            self.badge_font,
        ) = get_fonts()
        self.controls_mgr = ControlsManager()

        self.selected_action = "JUMP"
        self.listening_action: Optional[str] = None

        # Animation visualizer properties
        self.preview_scale = 3.2
        self.enhanced_preview = False
        self.flip_preview = False
        self.frame_index = 0.0
        self.anim_speed = 0.18

        # Toast notifications
        self.toast_msg = ""
        self.toast_timer = 0.0

        # Joystick handle
        self.joystick: Optional[pg.joystick.JoystickType] = None
        self._init_joystick()

        # Animation cache
        self.animation_cache: Dict[str, Dict[str, List[pg.Surface]]] = {
            "std": {},
            "enh": {},
        }
        self._load_all_animations()

        # Buttons
        self._init_buttons()

    def _init_joystick(self) -> None:
        if pg.joystick.get_count() > 0:
            try:
                self.joystick = pg.joystick.Joystick(0)
                if not self.joystick.get_init():
                    self.joystick.init()
            except Exception:
                self.joystick = None
        else:
            self.joystick = None

    def _load_all_animations(self) -> None:
        for state, (std_pat, std_count, enh_pat, enh_count) in STATE_ASSETS.items():
            self.animation_cache["std"][state] = self._load_frames(
                std_pat, std_count
            )
            if enh_pat:
                self.animation_cache["enh"][state] = self._load_frames(
                    enh_pat, enh_count
                )
            else:
                self.animation_cache["enh"][state] = self.animation_cache["std"][
                    state
                ]

    def _load_frames(self, pattern: str, count: int) -> List[pg.Surface]:
        frames = []
        for i in range(1, count + 1):
            f_path = pattern.format(i)
            if os.path.exists(f_path):
                try:
                    frames.append(pg.image.load(f_path).convert_alpha())
                except Exception:
                    frames.append(self._create_dummy_frame())
            else:
                frames.append(self._create_dummy_frame())
        if not frames:
            frames.append(self._create_dummy_frame())
        return frames

    def _create_dummy_frame(self) -> pg.Surface:
        surf = pg.Surface((96, 96), pg.SRCALPHA)
        pg.draw.rect(surf, (200, 0, 100), (24, 24, 48, 48), 2)
        txt = self.value_font.render("Sprite", True, (200, 200, 200))
        surf.blit(txt, (48 - txt.get_width() // 2, 48 - txt.get_height() // 2))
        return surf

    def _init_buttons(self) -> None:
        # Top Mode Segmented Pill Control
        self.btn_kb = Button(
            "KEYBOARD MODE",
            455,
            16,
            160,
            34,
            lambda: self.set_mode("KEYBOARD"),
            active=(self.controls_mgr.mode == "KEYBOARD"),
        )
        self.btn_js = Button(
            "JOYSTICK MODE",
            620,
            16,
            160,
            34,
            lambda: self.set_mode("JOYSTICK"),
            active=(self.controls_mgr.mode == "JOYSTICK"),
        )

        # Left panel preview toggles
        self.btn_flip = Button("Flip: Left", 40, 582, 120, 32, self.toggle_flip)
        self.btn_enh = Button(
            "Form: Standard", 170, 582, 140, 32, self.toggle_enhanced
        )

        # Bottom action bar buttons
        self.btn_save = Button(
            "SAVE MAPPINGS",
            495,
            655,
            170,
            42,
            self.save_config,
            color_override=(0, 140, 70),
        )
        self.btn_reset = Button(
            "RESET DEFAULTS",
            680,
            655,
            170,
            42,
            self.reset_defaults,
            color_override=(140, 35, 35),
        )
        self.btn_back = Button(
            "BACK / EXIT",
            865,
            655,
            150,
            42,
            self.exit_app,
            color_override=(50, 55, 70),
        )

    def set_mode(self, mode: str) -> None:
        self.controls_mgr.set_mode(mode)
        self.btn_kb.active = (mode == "KEYBOARD")
        self.btn_js.active = (mode == "JOYSTICK")
        self.show_toast(f"Switched to {mode} Control Mode")

    def toggle_flip(self) -> None:
        self.flip_preview = not self.flip_preview
        self.btn_flip.text = "Flip: Right" if self.flip_preview else "Flip: Left"

    def toggle_enhanced(self) -> None:
        self.enhanced_preview = not self.enhanced_preview
        self.btn_enh.text = (
            "Form: Enhanced" if self.enhanced_preview else "Form: Standard"
        )

    def show_toast(self, message: str) -> None:
        self.toast_msg = message
        self.toast_timer = 2.8

    def save_config(self) -> None:
        if self.controls_mgr.save_config():
            self.show_toast("Controls saved locally to game_data/controls_config.json!")
        else:
            self.show_toast("Error saving control configuration!")

    def reset_defaults(self) -> None:
        self.controls_mgr.reset_to_defaults()
        self.btn_kb.active = (self.controls_mgr.mode == "KEYBOARD")
        self.btn_js.active = (self.controls_mgr.mode == "JOYSTICK")
        self.show_toast("Control mappings reset to defaults!")

    def exit_app(self) -> None:
        self.running = False

    def _capture_joystick_combo(self, trigger_str: str) -> str:
        inputs = []
        if self.joystick:
            for b in range(self.joystick.get_numbuttons()):
                b_str = f"BUTTON_{b}"
                if self.joystick.get_button(b) or b_str == trigger_str:
                    if b_str not in inputs:
                        inputs.append(b_str)
            for a in range(self.joystick.get_numaxes()):
                val = self.joystick.get_axis(a)
                if val < -0.6:
                    a_str = f"AXIS_{a}_MINUS"
                    if a_str not in inputs:
                        inputs.append(a_str)
                elif val > 0.6:
                    a_str = f"AXIS_{a}_PLUS"
                    if a_str not in inputs:
                        inputs.append(a_str)
        if trigger_str not in inputs:
            inputs.append(trigger_str)
        return " + ".join(inputs)


    def handle_events(self) -> None:
        for event in pg.event.get():
            if event.type == pg.QUIT:
                self.running = False
                return

            # Listening Mode: Catch next key or joystick input (supports single or combination inputs)
            if self.listening_action:
                if event.type == pg.KEYDOWN:
                    if event.key == pg.K_ESCAPE:
                        self.listening_action = None
                        self.show_toast("Remapping cancelled")
                    else:
                        pressed_key_name = pg.key.name(event.key)
                        keys = pg.key.get_pressed()

                        held_keys = []
                        modifier_candidates = [
                            pg.K_LSHIFT, pg.K_RSHIFT, pg.K_LCTRL, pg.K_RCTRL,
                            pg.K_LALT, pg.K_RALT, pg.K_SPACE, pg.K_UP,
                            pg.K_DOWN, pg.K_LEFT, pg.K_RIGHT
                        ]

                        for mod_code in modifier_candidates:
                            if keys[mod_code] and mod_code != event.key:
                                name = pg.key.name(mod_code)
                                if name not in held_keys:
                                    held_keys.append(name)

                        if held_keys:
                            combo_str = " + ".join(held_keys + [pressed_key_name])
                        else:
                            combo_str = pressed_key_name

                        self.controls_mgr.set_binding(
                            self.listening_action, combo_str, mode="KEYBOARD"
                        )
                        display_name = self.controls_mgr.get_display_name_for_binding(
                            combo_str, mode="KEYBOARD"
                        )
                        self.show_toast(
                            f"Mapped {self.listening_action} -> '{display_name}'"
                        )
                        self.listening_action = None
                    continue

                elif event.type == pg.JOYBUTTONDOWN:
                    trigger_str = f"BUTTON_{event.button}"
                    combo_str = self._capture_joystick_combo(trigger_str)
                    self.controls_mgr.set_binding(
                        self.listening_action, combo_str, mode="JOYSTICK"
                    )
                    display_name = self.controls_mgr.get_display_name_for_binding(
                        combo_str, mode="JOYSTICK"
                    )
                    self.show_toast(
                        f"Mapped {self.listening_action} -> '{display_name}'"
                    )
                    self.listening_action = None
                    continue

                elif event.type == pg.JOYAXISMOTION:
                    if abs(event.value) > 0.7:
                        dir_str = "MINUS" if event.value < 0 else "PLUS"
                        trigger_str = f"AXIS_{event.axis}_{dir_str}"
                        combo_str = self._capture_joystick_combo(trigger_str)
                        self.controls_mgr.set_binding(
                            self.listening_action, combo_str, mode="JOYSTICK"
                        )
                        display_name = self.controls_mgr.get_display_name_for_binding(
                            combo_str, mode="JOYSTICK"
                        )
                        self.show_toast(
                            f"Mapped {self.listening_action} -> '{display_name}'"
                        )
                        self.listening_action = None
                    continue


            # Standard UI handle events
            if self.btn_kb.handle_event(event):
                continue
            if self.btn_js.handle_event(event):
                continue
            if self.btn_flip.handle_event(event):
                continue
            if self.btn_enh.handle_event(event):
                continue
            if self.btn_save.handle_event(event):
                continue
            if self.btn_reset.handle_event(event):
                continue
            if self.btn_back.handle_event(event):
                continue

            # Right panel table row click selection & REMAP button trigger
            if event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = event.pos
                if 495 <= mx <= 1255 and 140 <= my <= 635:
                    row_idx = (my - 146) // 44
                    if 0 <= row_idx < len(ACTIONS):
                        action = ACTIONS[row_idx]
                        self.selected_action = action

                        # Check if click hit REMAP button
                        remap_rect = pg.Rect(1160, 146 + row_idx * 44 + 6, 80, 28)
                        if remap_rect.collidepoint((mx, my)):
                            self.listening_action = action

    def update(self, dt: float) -> None:
        if self.toast_timer > 0:
            self.toast_timer -= dt
            if self.toast_timer <= 0:
                self.toast_msg = ""

        self._init_joystick()

        anim_state = ACTION_METADATA.get(self.selected_action, {}).get(
            "state", "IDLE"
        )
        cache_key = "enh" if self.enhanced_preview else "std"
        frames = self.animation_cache[cache_key].get(anim_state, [])
        if frames:
            self.frame_index += self.anim_speed
            if self.frame_index >= len(frames):
                self.frame_index = 0.0

    def draw(self) -> None:
        self.screen.fill(BG_COLOR)

        # ──────────────────────────────────────────────────────────────────────
        # 1. HEADER SECTION
        # ──────────────────────────────────────────────────────────────────────
        # Main Title (Left)
        t_main = self.title_font.render("PIXEL-RUNNER", True, ACCENT_CYAN)
        t_sub = self.value_font.render("CONTROL MAPPER PLUGIN", True, TEXT_MUTED)
        self.screen.blit(t_main, (25, 14))
        self.screen.blit(t_sub, (25, 38))

        # Mode Segmented Control Bar (Center)
        mode_bg = pg.Rect(450, 14, 335, 38)
        pg.draw.rect(self.screen, PANEL_BG, mode_bg, border_radius=8)
        pg.draw.rect(self.screen, BORDER_COLOR, mode_bg, width=1, border_radius=8)
        self.btn_kb.draw(self.screen, self.ui_font)
        self.btn_js.draw(self.screen, self.ui_font)

        # USB Gamepad Status Indicator (Right)
        status_box = pg.Rect(800, 14, 455, 38)
        pg.draw.rect(self.screen, PANEL_BG, status_box, border_radius=8)
        pg.draw.rect(self.screen, BORDER_COLOR, status_box, width=1, border_radius=8)

        if self.joystick:
            dot_color = ACCENT_GREEN
            js_name = self.joystick.get_name()
            if len(js_name) > 34:
                js_name = js_name[:31] + "..."
            status_str = f"Gamepad: {js_name}"
            txt_color = TEXT_COLOR
        else:
            dot_color = TEXT_MUTED
            status_str = "USB Gamepad: None Detected"
            txt_color = TEXT_MUTED

        pg.draw.circle(self.screen, dot_color, (820, 33), 5)
        st_surf = self.ui_font.render(status_str, True, txt_color)
        self.screen.blit(st_surf, (833, 24))

        # Header Separator
        pg.draw.line(self.screen, BORDER_COLOR, (25, 66), (1255, 66), 1)

        # ──────────────────────────────────────────────────────────────────────
        # 2. LEFT PANEL - PLAYER ACTION & ANIMATION PREVIEW
        # ──────────────────────────────────────────────────────────────────────
        left_panel = pg.Rect(25, 80, 450, 560)
        pg.draw.rect(self.screen, PANEL_BG, left_panel, border_radius=8)
        pg.draw.rect(self.screen, BORDER_COLOR, left_panel, width=1, border_radius=8)

        meta = ACTION_METADATA.get(
            self.selected_action,
            {"name": self.selected_action, "desc": "", "state": "IDLE"},
        )

        # Action Metadata Info
        lbl_preview = self.header_font.render(
            f"ACTION PREVIEW: {meta['name'].upper()}", True, ACCENT_GREEN
        )
        self.screen.blit(lbl_preview, (40, 95))

        lbl_state = self.value_font.render(
            f"State: {meta['state']}", True, ACCENT_CYAN
        )
        self.screen.blit(lbl_state, (40, 118))

        lbl_desc = self.value_font.render(
            f"Description: {meta['desc']}", True, TEXT_MUTED
        )
        self.screen.blit(lbl_desc, (40, 136))

        # Sprite Visualizer Box
        preview_rect = pg.Rect(40, 160, 420, 405)
        pg.draw.rect(self.screen, PREVIEW_BG, preview_rect, border_radius=6)
        pg.draw.rect(self.screen, BORDER_COLOR, preview_rect, width=1, border_radius=6)

        # Render Player Animation Frame
        anim_state = meta["state"]
        cache_key = "enh" if self.enhanced_preview else "std"
        frames = self.animation_cache[cache_key].get(anim_state, [])
        if frames:
            frame_img = frames[int(self.frame_index) % len(frames)]
            if self.flip_preview:
                frame_img = pg.transform.flip(frame_img, True, False)

            w, h = frame_img.get_size()
            scaled_surf = pg.transform.scale(
                frame_img,
                (int(w * self.preview_scale), int(h * self.preview_scale)),
            )
            s_rect = scaled_surf.get_rect(center=preview_rect.center)
            self.screen.blit(scaled_surf, s_rect)

        # Preview Toggle Buttons
        self.btn_flip.draw(self.screen, self.ui_font)
        self.btn_enh.draw(self.screen, self.ui_font)

        # ──────────────────────────────────────────────────────────────────────
        # 3. RIGHT PANEL - CONTROL MAPPING TABLE
        # ──────────────────────────────────────────────────────────────────────
        right_panel = pg.Rect(495, 80, 760, 560)
        pg.draw.rect(self.screen, PANEL_BG, right_panel, border_radius=8)
        pg.draw.rect(self.screen, BORDER_COLOR, right_panel, width=1, border_radius=8)

        cur_mode = self.controls_mgr.mode
        t_title = self.header_font.render(
            f"CONTROL MAPPING TABLE [{cur_mode} MODE]", True, ACCENT_CYAN
        )
        self.screen.blit(t_title, (515, 95))

        # Table Column Headers
        h_action = self.ui_font.render("ACTION NAME", True, TEXT_MUTED)
        h_desc = self.ui_font.render("DESCRIPTION", True, TEXT_MUTED)
        h_bound = self.ui_font.render("MAPPED CONTROL", True, TEXT_MUTED)
        h_remap = self.ui_font.render("ASSIGN", True, TEXT_MUTED)

        self.screen.blit(h_action, (515, 120))
        self.screen.blit(h_desc, (680, 120))
        self.screen.blit(h_bound, (920, 120))
        self.screen.blit(h_remap, (1170, 120))
        pg.draw.line(self.screen, BORDER_COLOR, (505, 140), (1245, 140), 1)

        # Render Rows
        row_y = 146
        for action in ACTIONS:
            a_meta = ACTION_METADATA[action]
            is_selected = action == self.selected_action
            is_listening = action == self.listening_action

            row_rect = pg.Rect(505, row_y, 740, 40)

            if is_listening:
                pg.draw.rect(self.screen, LISTEN_BG, row_rect, border_radius=4)
                pg.draw.rect(
                    self.screen, ACCENT_PURPLE, row_rect, width=2, border_radius=4
                )
            elif is_selected:
                pg.draw.rect(self.screen, HIGHLIGHT_BG, row_rect, border_radius=4)
                pg.draw.rect(
                    self.screen, ACCENT_CYAN, row_rect, width=1, border_radius=4
                )

            # Action Name
            n_color = ACCENT_GREEN if is_selected else TEXT_COLOR
            txt_name = self.ui_font.render(a_meta["name"], True, n_color)
            self.screen.blit(txt_name, (515, row_y + 11))

            # Action Description (Cleanly truncated to max 220px to prevent overlap)
            desc_text = a_meta["desc"]
            if len(desc_text) > 30:
                desc_text = desc_text[:27] + "..."
            txt_desc = self.value_font.render(desc_text, True, TEXT_MUTED)
            self.screen.blit(txt_desc, (680, row_y + 12))

            # Mapped Control Pill Badge
            raw_bind = self.controls_mgr.get_binding(action)
            disp_bind = self.controls_mgr.get_display_name_for_binding(raw_bind)

            pill_rect = pg.Rect(920, row_y + 6, 225, 28)

            if is_listening:
                disp_bind = "PRESS ANY INPUT..."
                p_bg = LISTEN_BG
                p_border = ACCENT_CYAN
                p_txt_color = ACCENT_CYAN
            else:
                p_bg = BADGE_BG
                p_border = BADGE_BORDER if raw_bind else (140, 40, 40)
                p_txt_color = ACCENT_CYAN if raw_bind else (240, 80, 80)

            pg.draw.rect(self.screen, p_bg, pill_rect, border_radius=5)
            pg.draw.rect(self.screen, p_border, pill_rect, width=1, border_radius=5)

            txt_bind = self.badge_font.render(disp_bind, True, p_txt_color)
            b_rect = txt_bind.get_rect(center=pill_rect.center)
            self.screen.blit(txt_bind, b_rect)

            # REMAP Button
            remap_btn_rect = pg.Rect(1160, row_y + 6, 80, 28)
            b_bg = ACCENT_PURPLE if is_listening else (48, 54, 72)
            m_pos = pg.mouse.get_pos()
            is_hover = remap_btn_rect.collidepoint(m_pos)
            if is_hover:
                b_bg = (
                    min(255, b_bg[0] + 30),
                    min(255, b_bg[1] + 30),
                    min(255, b_bg[2] + 30),
                )

            pg.draw.rect(self.screen, b_bg, remap_btn_rect, border_radius=5)
            pg.draw.rect(
                self.screen, BORDER_LIGHT, remap_btn_rect, width=1, border_radius=5
            )

            remap_txt = self.ui_font.render("REMAP", True, (255, 255, 255))
            self.screen.blit(
                remap_txt, remap_txt.get_rect(center=remap_btn_rect.center)
            )

            row_y += 44

        # ──────────────────────────────────────────────────────────────────────
        # 4. BOTTOM ACTION BAR & TOAST MESSAGES
        # ──────────────────────────────────────────────────────────────────────
        self.btn_save.draw(self.screen, self.ui_font)
        self.btn_reset.draw(self.screen, self.ui_font)
        self.btn_back.draw(self.screen, self.ui_font)

        if self.toast_msg:
            t_surf = self.ui_font.render(self.toast_msg, True, (255, 255, 255))
            t_box = pg.Rect(25, 655, t_surf.get_width() + 36, 42)
            pg.draw.rect(self.screen, (15, 80, 50), t_box, border_radius=6)
            pg.draw.rect(self.screen, ACCENT_GREEN, t_box, width=1, border_radius=6)
            self.screen.blit(t_surf, (43, 668))

        pg.display.flip()

    def run(self) -> None:
        while self.running:
            dt = self.clock.tick(60) / 1000.0
            self.handle_events()
            self.update(dt)
            self.draw()


if __name__ == "__main__":
    app = ControlsEditorApp()
    app.run()
    pg.quit()
