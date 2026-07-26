#!/usr/bin/env python3
"""
power_icons_editor.py

Pixel-Runner: Power Icons & Screen Placement Plugin
An interactive dark-themed GUI tool to browse icon asset folders, select power images,
assign them to player power/attack slots, and visually position them on screen with live drag-and-drop,
scaling, frame styling, keybinding badges, and preset layouts.
"""

import os
import sys
import json
import glob
import shutil
import math
from datetime import datetime
import pygame as pg
from typing import Dict, List, Tuple, Optional, Any

# Ensure import access to src package
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from src.game.ui.power_icons_manager import PowerIconsManager

# Initialize Pygame systems
pg.init()
pg.font.init()

SCREEN_W, SCREEN_H = 1280, 720
screen = pg.display.set_mode((SCREEN_W, SCREEN_H))
pg.display.set_caption("Power Icons & Screen Placement Plugin - Pixel-Runner")

# Theme Palette (Sleek Dark Slate & Neon Accents)
BG_COLOR = (14, 16, 22)
PANEL_BG = (22, 26, 36)
PANEL_HEADER = (30, 36, 50)
CANVAS_BG = (10, 12, 16)
TEXT_MAIN = (240, 244, 250)
TEXT_MUTED = (140, 148, 165)
BORDER_COLOR = (42, 50, 68)
BORDER_LIGHT = (65, 75, 100)
ACCENT_CYAN = (0, 229, 255)
ACCENT_GREEN = (0, 230, 118)
ACCENT_PURPLE = (170, 0, 255)
ACCENT_ORANGE = (255, 145, 0)
ACCENT_RED = (255, 60, 90)
HIGHLIGHT_BG = (35, 43, 62)

# Load UI Fonts
try:
    title_font = pg.font.SysFont("dejavusans,ubuntu,arial", 18, bold=True)
    header_font = pg.font.SysFont("dejavusans,ubuntu,arial", 14, bold=True)
    ui_font = pg.font.SysFont("dejavusans,ubuntu,arial", 12, bold=True)
    small_font = pg.font.SysFont("dejavusans,ubuntu,arial", 11)
    badge_font = pg.font.SysFont("monospace,dejavusansmono", 11, bold=True)
except Exception:
    title_font = pg.font.Font(None, 24)
    header_font = pg.font.Font(None, 18)
    ui_font = pg.font.Font(None, 14)
    small_font = pg.font.Font(None, 12)
    badge_font = pg.font.Font(None, 12)


class Button:
    def __init__(self, text: str, x: int, y: int, w: int, h: int, callback: Any, color: Tuple[int, int, int] = PANEL_HEADER, text_color: Tuple[int, int, int] = TEXT_MAIN):
        self.text = text
        self.rect = pg.Rect(x, y, w, h)
        self.callback = callback
        self.color = color
        self.text_color = text_color
        self.hovered = False

    def draw(self, surface: pg.Surface):
        col = HIGHLIGHT_BG if self.hovered else self.color
        pg.draw.rect(surface, col, self.rect, border_radius=6)
        pg.draw.rect(surface, BORDER_LIGHT if self.hovered else BORDER_COLOR, self.rect, width=1, border_radius=6)
        txt = ui_font.render(self.text, True, self.text_color)
        surface.blit(txt, (self.rect.centerx - txt.get_width() // 2, self.rect.centery - txt.get_height() // 2))

    def handle_event(self, event: pg.event.Event) -> bool:
        if event.type == pg.MOUSEMOTION:
            self.hovered = self.rect.collidepoint(event.pos)
        elif event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                if self.callback:
                    self.callback()
                return True
        return False


class TextInput:
    def __init__(self, label: str, x: int, y: int, w: int, h: int, value: str = "", on_change: Optional[Any] = None):
        self.label = label
        self.rect = pg.Rect(x, y, w, h)
        self.value = value
        self.active = False
        self.on_change = on_change

    def draw(self, surface: pg.Surface):
        if self.label:
            lbl = small_font.render(self.label, True, TEXT_MUTED)
            surface.blit(lbl, (self.rect.x, self.rect.y - 14))
        
        bg = HIGHLIGHT_BG if self.active else PANEL_BG
        border = ACCENT_CYAN if self.active else BORDER_COLOR
        pg.draw.rect(surface, bg, self.rect, border_radius=4)
        pg.draw.rect(surface, border, self.rect, width=1, border_radius=4)

        txt = small_font.render(self.value + ("|" if self.active else ""), True, TEXT_MAIN)
        surface.blit(txt, (self.rect.x + 6, self.rect.centery - txt.get_height() // 2))

    def handle_event(self, event: pg.event.Event) -> bool:
        if event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
            self.active = self.rect.collidepoint(event.pos)
            return self.active
        elif event.type == pg.KEYDOWN and self.active:
            if event.key == pg.K_RETURN or event.key == pg.K_ESCAPE:
                self.active = False
            elif event.key == pg.K_BACKSPACE:
                self.value = self.value[:-1]
                if self.on_change:
                    self.on_change(self.value)
            else:
                if len(event.unicode) > 0 and event.unicode.isprintable():
                    self.value += event.unicode
                    if self.on_change:
                        self.on_change(self.value)
            return True
        return False


class PowerIconsPlugin:
    def __init__(self):
        self.manager = PowerIconsManager()
        self.config = self.manager.config
        if "icons" not in self.config:
            self.config = PowerIconsManager.get_default_config()

        # Canvas & Panel dimensions
        self.left_panel = pg.Rect(0, 45, 310, SCREEN_H - 45)
        self.canvas_panel = pg.Rect(310, 45, 660, 420)
        self.canvas_controls_panel = pg.Rect(310, 465, 660, SCREEN_H - 465)
        self.right_panel = pg.Rect(970, 45, 310, SCREEN_H - 45)
        self.top_bar = pg.Rect(0, 0, SCREEN_W, 45)

        # Game Screen Viewport in Canvas
        self.game_w = self.config.get("screen_width", 1280)
        self.game_h = self.config.get("screen_height", 720)
        self.viewport = pg.Rect(325, 60, 630, 390)
        self.scale_x = self.viewport.width / self.game_w
        self.scale_y = self.viewport.height / self.game_h

        # Asset folder scanning
        self.asset_folders: List[str] = []
        self.selected_folder_idx = 0
        self.image_files: List[str] = []
        self.selected_image_path: Optional[str] = None
        self.image_thumbnails: Dict[str, pg.Surface] = {}
        self.folder_scroll = 0
        self.search_filter = ""

        # Selection & Drag state
        self.active_power_key: str = "ATTACK_THRUST"
        self.dragging_icon_key: Optional[str] = None
        self.drag_offset: Tuple[int, int] = (0, 0)
        self.cooldown_preview = 0.0

        # UI Toggles
        self.show_grid = True
        self.show_crosshairs = True
        self.show_margins = True
        self.toast_message = ""
        self.toast_timer = 0

        # Scan folders and build UI
        self._scan_assets_directory()
        self._load_image_files()
        self._init_controls()

    def _scan_assets_directory(self):
        """Find all directories containing images inside assets/."""
        assets_root = "assets"
        self.asset_folders = []
        if not os.path.exists(assets_root):
            return

        for root, dirs, files in os.walk(assets_root):
            # Check if directory contains image files
            has_images = any(f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.webp')) for f in files)
            if has_images:
                rel_path = os.path.relpath(root, ".")
                self.asset_folders.append(rel_path)

        self.asset_folders.sort()
        if not self.asset_folders:
            self.asset_folders = ["assets"]

    def _load_image_files(self):
        """Load image list for the currently selected folder."""
        self.image_files = []
        self.image_thumbnails.clear()

        if 0 <= self.selected_folder_idx < len(self.asset_folders):
            folder = self.asset_folders[self.selected_folder_idx]
            if os.path.exists(folder):
                for fname in sorted(os.listdir(folder)):
                    if fname.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.webp')):
                        full_p = os.path.join(folder, fname)
                        if not self.search_filter or self.search_filter.lower() in fname.lower():
                            self.image_files.append(full_p)

        # Generate thumbnails for first 60 images
        for path in self.image_files[:60]:
            try:
                img = pg.image.load(path).convert_alpha()
                thumb = pg.transform.smoothscale(img, (40, 40))
                self.image_thumbnails[path] = thumb
            except Exception:
                pass

    def _init_controls(self):
        """Create buttons and text inputs."""
        self.top_buttons = [
            Button("SAVE CONFIG", 10, 8, 110, 28, self.save_config, color=(0, 140, 200)),
            Button("LOAD CONFIG", 130, 8, 110, 28, self.load_config, color=PANEL_HEADER),
            Button("PRESETS", 250, 8, 90, 28, self.apply_preset_bottom_bar, color=PANEL_HEADER),
            Button("RESET", 350, 8, 80, 28, self.reset_to_default, color=(160, 40, 60)),
        ]

        self.preset_buttons = [
            Button("Bottom Bar", 325, 480, 110, 24, self.apply_preset_bottom_bar),
            Button("Right Diamond", 445, 480, 110, 24, self.apply_preset_diamond),
            Button("Left Stack", 565, 480, 110, 24, self.apply_preset_left_stack),
            Button("Arc Layout", 685, 480, 110, 24, self.apply_preset_arc),
        ]

        # Keybind input box
        self.keybind_input = TextInput(
            "Keybind Badge", 985, 430, 120, 26,
            value=self._get_active_icon_prop("keybind", "Q"),
            on_change=lambda val: self._set_active_icon_prop("keybind", val)
        )
        self.label_input = TextInput(
            "Power Label", 1120, 430, 145, 26,
            value=self._get_active_icon_prop("label", "Thrust"),
            on_change=lambda val: self._set_active_icon_prop("label", val)
        )
        self.search_input = TextInput(
            "", 15, 80, 280, 24,
            value=self.search_filter,
            on_change=self._on_search_change
        )

    def _on_search_change(self, val: str):
        self.search_filter = val
        self._load_image_files()

    def show_toast(self, msg: str):
        self.toast_message = msg
        self.toast_timer = 180  # 3 seconds at 60fps

    def _get_active_icon_prop(self, key: str, default: Any) -> Any:
        icons = self.config.get("icons", {})
        if self.active_power_key in icons:
            return icons[self.active_power_key].get(key, default)
        return default

    def _set_active_icon_prop(self, key: str, value: Any):
        if "icons" not in self.config:
            self.config["icons"] = {}
        if self.active_power_key not in self.config["icons"]:
            self.config["icons"][self.active_power_key] = {
                "enabled": True, "label": self.active_power_key, "asset_path": "",
                "x": 640, "y": 640, "width": 52, "height": 52, "scale": 1.0,
                "opacity": 255, "keybind": "Q", "frame_style": "circle",
                "border_color": [0, 229, 255], "badge_bg": [0, 140, 200], "anchor": "center"
            }
        self.config["icons"][self.active_power_key][key] = value

    def save_config(self):
        """Save config to game_data/power_icons_config.json with a timestamped backup."""
        target_path = "game_data/power_icons_config.json"
        os.makedirs("game_data", exist_ok=True)

        if os.path.exists(target_path):
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = f"game_data/power_icons_config.backup_{timestamp}.json"
            try:
                shutil.copy2(target_path, backup_path)
            except Exception as e:
                print(f"[Backup Error] {e}")

        try:
            with open(target_path, "w") as f:
                json.dump(self.config, f, indent=2)
            self.manager.load_config()
            self.show_toast("Saved to game_data/power_icons_config.json!")
        except Exception as e:
            self.show_toast(f"Save failed: {e}")

    def load_config(self):
        self.manager.load_config()
        self.config = self.manager.config
        self.show_toast("Configuration loaded!")

    def reset_to_default(self):
        self.config = PowerIconsManager.get_default_config()
        self.manager.config = self.config
        self.manager._preload_assets()
        self.show_toast("Reset to default layout.")

    # Preset Layouts
    def apply_preset_bottom_bar(self):
        icons = self.config.get("icons", {})
        enabled_keys = [k for k, v in icons.items() if v.get("enabled", True)]
        if not enabled_keys:
            return
        
        spacing = 64
        start_x = 1280 // 2 - ((len(enabled_keys) - 1) * spacing) // 2
        y = 640

        for i, k in enumerate(enabled_keys):
            icons[k]["x"] = start_x + i * spacing
            icons[k]["y"] = y
            icons[k]["anchor"] = "center"
        self.show_toast("Applied Bottom Action Bar preset.")

    def apply_preset_diamond(self):
        icons = self.config.get("icons", {})
        keys = list(icons.keys())
        if len(keys) >= 4:
            cx, cy = 1180, 600
            offsets = [(0, -50), (50, 0), (0, 50), (-50, 0)]
            for i, k in enumerate(keys[:4]):
                icons[k]["x"] = cx + offsets[i][0]
                icons[k]["y"] = cy + offsets[i][1]
        self.show_toast("Applied Right Diamond preset.")

    def apply_preset_left_stack(self):
        icons = self.config.get("icons", {})
        keys = list(icons.keys())
        start_y = 200
        for i, k in enumerate(keys):
            icons[k]["x"] = 50
            icons[k]["y"] = start_y + i * 60
            icons[k]["anchor"] = "top-left"
        self.show_toast("Applied Left Vertical Stack preset.")

    def apply_preset_arc(self):
        icons = self.config.get("icons", {})
        keys = list(icons.keys())
        cx, cy = 1100, 650
        r = 140
        n = max(1, len(keys))
        for i, k in enumerate(keys):
            angle = math.radians(180 + (i / max(1, n - 1)) * 90)
            icons[k]["x"] = int(cx + r * math.cos(angle))
            icons[k]["y"] = int(cy + r * math.sin(angle))
        self.show_toast("Applied Arc Layout preset.")

    def game_to_viewport(self, gx: int, gy: int) -> Tuple[int, int]:
        vx = self.viewport.x + int(gx * self.scale_x)
        vy = self.viewport.y + int(gy * self.scale_y)
        return vx, vy

    def viewport_to_game(self, vx: int, vy: int) -> Tuple[int, int]:
        gx = int((vx - self.viewport.x) / self.scale_x)
        gy = int((vy - self.viewport.y) / self.scale_y)
        return max(0, min(self.game_w, gx)), max(0, min(self.game_h, gy))

    # Input Event Handling
    def handle_events(self):
        for event in pg.event.get():
            if event.type == pg.QUIT:
                return False

            # Top bar buttons
            for btn in self.top_buttons:
                if btn.handle_event(event):
                    break

            # Preset buttons
            for btn in self.preset_buttons:
                if btn.handle_event(event):
                    break

            # Text inputs
            self.keybind_input.handle_event(event)
            self.label_input.handle_event(event)
            self.search_input.handle_event(event)

            # Folder selection clicks
            if event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = event.pos

                # Folder list selection
                if 10 <= mx <= 300 and 110 <= my <= 210:
                    idx = (my - 110) // 22 + self.folder_scroll
                    if 0 <= idx < len(self.asset_folders):
                        self.selected_folder_idx = idx
                        self._load_image_files()

                # Image thumbnail selection
                elif 10 <= mx <= 300 and 240 <= my <= 620:
                    row = (my - 240) // 50
                    col = (mx - 10) // 50
                    idx = row * 5 + col
                    if 0 <= idx < len(self.image_files):
                        self.selected_image_path = self.image_files[idx]

                # Power slot selection in Right Panel
                elif 980 <= mx <= 1270 and 100 <= my <= 260:
                    slot_keys = list(self.config.get("icons", {}).keys())
                    idx = (my - 100) // 26
                    if 0 <= idx < len(slot_keys):
                        self.active_power_key = slot_keys[idx]
                        self.keybind_input.value = self._get_active_icon_prop("keybind", "")
                        self.label_input.value = self._get_active_icon_prop("label", "")

                # Dragging icon on Canvas Viewport
                elif self.viewport.collidepoint((mx, my)):
                    for pkey, pdata in self.config.get("icons", {}).items():
                        gx, gy = pdata.get("x", 0), pdata.get("y", 0)
                        vx, vy = self.game_to_viewport(gx, gy)
                        w = int(pdata.get("width", 52) * self.scale_x)
                        h = int(pdata.get("height", 52) * self.scale_y)
                        r = pg.Rect(vx - w // 2, vy - h // 2, w, h)
                        if r.collidepoint((mx, my)):
                            self.active_power_key = pkey
                            self.dragging_icon_key = pkey
                            self.drag_offset = (mx - vx, my - vy)
                            self.keybind_input.value = self._get_active_icon_prop("keybind", "")
                            self.label_input.value = self._get_active_icon_prop("label", "")
                            break

            elif event.type == pg.MOUSEBUTTONUP and event.button == 1:
                self.dragging_icon_key = None

            elif event.type == pg.MOUSEMOTION and self.dragging_icon_key:
                mx, my = event.pos
                gx, gy = self.viewport_to_game(mx - self.drag_offset[0], my - self.drag_offset[1])
                self.config["icons"][self.dragging_icon_key]["x"] = gx
                self.config["icons"][self.dragging_icon_key]["y"] = gy

            elif event.type == pg.MOUSEWHEEL:
                mx, my = pg.mouse.get_pos()
                if 10 <= mx <= 300 and 110 <= my <= 210:
                    self.folder_scroll = max(0, min(len(self.asset_folders) - 4, self.folder_scroll - event.y))

            # Keyboard Arrow Keys Nudge
            elif event.type == pg.KEYDOWN:
                if not self.keybind_input.active and not self.label_input.active and not self.search_input.active:
                    icons = self.config.get("icons", {})
                    if self.active_power_key in icons:
                        step = 5 if pg.key.get_mods() & pg.KMOD_SHIFT else 1
                        if event.key == pg.K_LEFT:
                            icons[self.active_power_key]["x"] -= step
                        elif event.key == pg.K_RIGHT:
                            icons[self.active_power_key]["x"] += step
                        elif event.key == pg.K_UP:
                            icons[self.active_power_key]["y"] -= step
                        elif event.key == pg.K_DOWN:
                            icons[self.active_power_key]["y"] += step

        return True

    def assign_selected_image(self):
        """Assign current selected image path to active power slot."""
        if self.selected_image_path and self.active_power_key:
            self._set_active_icon_prop("asset_path", self.selected_image_path)
            self.manager._preload_assets()
            self.show_toast(f"Assigned image to {self.active_power_key}!")

    def add_custom_slot(self):
        """Add a new power slot."""
        new_key = f"POWER_SLOT_{len(self.config.get('icons', {})) + 1}"
        self.config.setdefault("icons", {})[new_key] = {
            "enabled": True, "label": "Custom", "asset_path": "",
            "x": 640, "y": 640, "width": 52, "height": 52, "scale": 1.0,
            "opacity": 255, "keybind": f"{len(self.config['icons'])}",
            "frame_style": "circle", "border_color": [0, 229, 255],
            "badge_bg": [0, 140, 200], "anchor": "center"
        }
        self.active_power_key = new_key
        self.show_toast(f"Created slot {new_key}")

    # Drawing Routines
    def draw_left_panel(self):
        pg.draw.rect(screen, PANEL_BG, self.left_panel)
        pg.draw.line(screen, BORDER_COLOR, (self.left_panel.right, self.left_panel.top), (self.left_panel.right, self.left_panel.bottom))

        # Title: Folder Browser
        hdr = header_font.render("ASSET FOLDERS", True, ACCENT_CYAN)
        screen.blit(hdr, (15, 55))

        # Search Bar
        self.search_input.draw(screen)

        # Folder List Box
        folder_box = pg.Rect(10, 110, 290, 100)
        pg.draw.rect(screen, CANVAS_BG, folder_box, border_radius=6)
        pg.draw.rect(screen, BORDER_COLOR, folder_box, width=1, border_radius=6)

        visible_folders = self.asset_folders[self.folder_scroll:self.folder_scroll + 4]
        for i, folder in enumerate(visible_folders):
            actual_idx = i + self.folder_scroll
            fy = 115 + i * 22
            is_sel = (actual_idx == self.selected_folder_idx)
            if is_sel:
                pg.draw.rect(screen, HIGHLIGHT_BG, (12, fy - 2, 286, 20), border_radius=4)
            
            # Shorten folder label for display
            disp = folder if len(folder) < 32 else "..." + folder[-28:]
            txt = small_font.render(disp, True, ACCENT_CYAN if is_sel else TEXT_MAIN)
            screen.blit(txt, (18, fy))

        # Image Gallery Grid Header
        hdr2 = header_font.render("ICONS GALLERY", True, ACCENT_CYAN)
        screen.blit(hdr2, (15, 220))

        gallery_box = pg.Rect(10, 240, 290, 380)
        pg.draw.rect(screen, CANVAS_BG, gallery_box, border_radius=6)
        pg.draw.rect(screen, BORDER_COLOR, gallery_box, width=1, border_radius=6)

        # Draw Image Grid
        for i, path in enumerate(self.image_files[:35]):
            row = i // 5
            col = i % 5
            ix = 15 + col * 55
            iy = 245 + row * 52

            rect = pg.Rect(ix, iy, 48, 48)
            is_selected = (path == self.selected_image_path)
            
            pg.draw.rect(screen, HIGHLIGHT_BG if is_selected else PANEL_BG, rect, border_radius=4)
            pg.draw.rect(screen, ACCENT_CYAN if is_selected else BORDER_COLOR, rect, width=2 if is_selected else 1, border_radius=4)

            thumb = self.image_thumbnails.get(path)
            if thumb:
                screen.blit(thumb, (ix + 4, iy + 4))

        # Assign Image Button
        assign_btn = Button("ASSIGN TO POWER SLOT", 10, 630, 290, 32, self.assign_selected_image, color=(0, 180, 100))
        assign_btn.draw(screen)

        if self.selected_image_path:
            bname = os.path.basename(self.selected_image_path)
            lbl = small_font.render(f"Selected: {bname[:28]}", True, TEXT_MUTED)
            screen.blit(lbl, (15, 668))

    def draw_canvas_panel(self):
        pg.draw.rect(screen, PANEL_BG, self.canvas_panel)
        pg.draw.line(screen, BORDER_COLOR, (self.canvas_panel.right, self.canvas_panel.top), (self.canvas_panel.right, self.canvas_panel.bottom))

        hdr = header_font.render("SCREEN INTERACTIVE VIEWPORT (1280x720 HUD)", True, ACCENT_CYAN)
        screen.blit(hdr, (325, 55))

        # Viewport Frame
        pg.draw.rect(screen, CANVAS_BG, self.viewport, border_radius=6)
        pg.draw.rect(screen, ACCENT_CYAN, self.viewport, width=2, border_radius=6)

        # Draw Grid lines inside Viewport
        if self.show_grid:
            for gx in range(0, 1280, 128):
                vx, _ = self.game_to_viewport(gx, 0)
                pg.draw.line(screen, (24, 30, 44), (vx, self.viewport.top), (vx, self.viewport.bottom))
            for gy in range(0, 720, 90):
                _, vy = self.game_to_viewport(0, gy)
                pg.draw.line(screen, (24, 30, 44), (self.viewport.left, vy), (self.viewport.right, vy))

        # Center Crosshairs
        if self.show_crosshairs:
            cx, cy = self.game_to_viewport(640, 360)
            pg.draw.line(screen, (40, 60, 90), (cx, self.viewport.top), (cx, self.viewport.bottom), 1)
            pg.draw.line(screen, (40, 60, 90), (self.viewport.left, cy), (self.viewport.right, cy), 1)

        # Draw icons onto Viewport using scaled coordinates
        icons = self.config.get("icons", {})
        for pkey, pdata in icons.items():
            if not pdata.get("enabled", True):
                continue

            gx, gy = pdata.get("x", 640), pdata.get("y", 640)
            vx, vy = self.game_to_viewport(gx, gy)
            w = int(pdata.get("width", 52) * self.scale_x * pdata.get("scale", 1.0))
            h = int(pdata.get("height", 52) * self.scale_y * pdata.get("scale", 1.0))
            rect = pg.Rect(vx - w // 2, vy - h // 2, w, h)

            is_active = (pkey == self.active_power_key)
            style = pdata.get("frame_style", "circle")
            bcolor = tuple(pdata.get("border_color", [0, 229, 255]))

            # Frame
            if style == "circle":
                pg.draw.circle(screen, bcolor, (vx, vy), max(8, w // 2), width=2 if is_active else 1)
            else:
                pg.draw.rect(screen, bcolor, rect, width=2 if is_active else 1, border_radius=6)

            # Icon Image
            icon_surf = self.manager.icon_surfaces.get(pkey)
            if icon_surf:
                scaled_icon = pg.transform.smoothscale(icon_surf, (max(8, w), max(8, h)))
                screen.blit(scaled_icon, rect.topleft)

            # Keybind Badge
            kb = pdata.get("keybind", "")
            if kb:
                btxt = badge_font.render(kb, True, (255, 255, 255))
                brect = pg.Rect(rect.centerx - btxt.get_width() // 2 - 3, rect.bottom - 4, btxt.get_width() + 6, 14)
                pg.draw.rect(screen, tuple(pdata.get("badge_bg", [0, 140, 200])), brect, border_radius=3)
                screen.blit(btxt, (brect.x + 3, brect.y + 1))

            # Highlight bounding box for active icon
            if is_active:
                pg.draw.rect(screen, ACCENT_ORANGE, rect.inflate(8, 8), width=2, border_radius=6)

        # Canvas Controls Subpanel
        pg.draw.rect(screen, PANEL_BG, self.canvas_controls_panel)
        hdr_pre = header_font.render("LAYOUT PRESETS & CONTROLS", True, ACCENT_CYAN)
        screen.blit(hdr_pre, (325, 455))

        for btn in self.preset_buttons:
            btn.draw(screen)

        # Cooldown Test Slider
        lbl_cd = ui_font.render(f"Live Cooldown Preview: {int(self.cooldown_preview * 100)}%", True, TEXT_MAIN)
        screen.blit(lbl_cd, (325, 520))
        track_rect = pg.Rect(325, 545, 300, 10)
        pg.draw.rect(screen, CANVAS_BG, track_rect, border_radius=4)
        pg.draw.rect(screen, ACCENT_CYAN, (track_rect.x, track_rect.y, int(300 * self.cooldown_preview), 10), border_radius=4)

        # Mouse Drag interaction for Cooldown Slider
        mx, my = pg.mouse.get_pos()
        if pg.mouse.get_pressed()[0] and track_rect.inflate(0, 10).collidepoint((mx, my)):
            self.cooldown_preview = max(0.0, min(1.0, (mx - track_rect.x) / 300.0))

    def draw_right_panel(self):
        pg.draw.rect(screen, PANEL_BG, self.right_panel)

        hdr = header_font.render("POWER SLOTS & PROPERTIES", True, ACCENT_CYAN)
        screen.blit(hdr, (985, 55))

        # Power Slot Selector List
        slot_box = pg.Rect(980, 80, 290, 140)
        pg.draw.rect(screen, CANVAS_BG, slot_box, border_radius=6)
        pg.draw.rect(screen, BORDER_COLOR, slot_box, width=1, border_radius=6)

        icons = self.config.get("icons", {})
        for i, (pkey, pdata) in enumerate(icons.items()):
            sy = 85 + i * 24
            if sy > 210:
                break
            is_sel = (pkey == self.active_power_key)
            if is_sel:
                pg.draw.rect(screen, HIGHLIGHT_BG, (982, sy - 2, 286, 22), border_radius=4)

            lbl_txt = f"{(pkey)}: {pdata.get('label', pkey)}"
            txt = small_font.render(lbl_txt[:32], True, ACCENT_ORANGE if is_sel else TEXT_MAIN)
            screen.blit(txt, (990, sy))

        # Add Custom Slot Button
        add_btn = Button("+ ADD CUSTOM POWER SLOT", 980, 230, 290, 26, self.add_custom_slot, color=PANEL_HEADER)
        add_btn.draw(screen)

        # Active Slot Properties
        hdr_prop = header_font.render("ACTIVE SLOT CONFIGURATION", True, ACCENT_CYAN)
        screen.blit(hdr_prop, (985, 270))

        if self.active_power_key in icons:
            pdata = icons[self.active_power_key]

            # X and Y Position display
            pos_str = f"Position: X={pdata.get('x', 640)}px  Y={pdata.get('y', 640)}px"
            lbl_pos = ui_font.render(pos_str, True, TEXT_MAIN)
            screen.blit(lbl_pos, (985, 295))

            # Scale slider & display
            scale_val = pdata.get("scale", 1.0)
            lbl_scale = ui_font.render(f"Icon Scale: {round(scale_val, 2)}x", True, TEXT_MAIN)
            screen.blit(lbl_scale, (985, 325))

            scale_track = pg.Rect(985, 348, 280, 8)
            pg.draw.rect(screen, CANVAS_BG, scale_track, border_radius=4)
            sw = int(280 * ((scale_val - 0.2) / 2.8))
            pg.draw.rect(screen, ACCENT_CYAN, (scale_track.x, scale_track.y, sw, 8), border_radius=4)

            mx, my = pg.mouse.get_pos()
            if pg.mouse.get_pressed()[0] and scale_track.inflate(0, 10).collidepoint((mx, my)):
                new_scale = 0.2 + ((mx - scale_track.x) / 280.0) * 2.8
                self._set_active_icon_prop("scale", round(max(0.2, min(3.0, new_scale)), 2))

            # Opacity / Alpha
            opacity_val = pdata.get("opacity", 255)
            lbl_op = ui_font.render(f"Opacity: {opacity_val} (255)", True, TEXT_MAIN)
            screen.blit(lbl_op, (985, 365))

            op_track = pg.Rect(985, 388, 280, 8)
            pg.draw.rect(screen, CANVAS_BG, op_track, border_radius=4)
            ow = int(280 * (opacity_val / 255.0))
            pg.draw.rect(screen, ACCENT_ORANGE, (op_track.x, op_track.y, ow, 8), border_radius=4)

            if pg.mouse.get_pressed()[0] and op_track.inflate(0, 10).collidepoint((mx, my)):
                new_op = int(((mx - op_track.x) / 280.0) * 255.0)
                self._set_active_icon_prop("opacity", max(0, min(255, new_op)))

            # Keybind & Label text inputs
            self.keybind_input.draw(screen)
            self.label_input.draw(screen)

            # Frame Style Selectors
            lbl_st = ui_font.render("Frame Style:", True, TEXT_MAIN)
            screen.blit(lbl_st, (985, 480))

            styles = ["circle", "square", "glowing", "none"]
            for i, st in enumerate(styles):
                bx = 985 + i * 70
                st_btn = Button(
                    st.capitalize(), bx, 502, 65, 24,
                    lambda s=st: self._set_active_icon_prop("frame_style", s),
                    color=HIGHLIGHT_BG if pdata.get("frame_style") == st else PANEL_HEADER
                )
                st_btn.draw(screen)

            # Delete Slot Button
            del_btn = Button("DELETE ACTIVE SLOT", 985, 630, 280, 30, self.delete_active_slot, color=(180, 40, 60))
            del_btn.draw(screen)

    def delete_active_slot(self):
        if self.active_power_key in self.config.get("icons", {}):
            del self.config["icons"][self.active_power_key]
            remaining = list(self.config.get("icons", {}).keys())
            self.active_power_key = remaining[0] if remaining else ""
            self.show_toast("Deleted power slot.")

    def draw_top_bar(self):
        pg.draw.rect(screen, PANEL_HEADER, self.top_bar)
        pg.draw.line(screen, BORDER_COLOR, (0, 44), (SCREEN_W, 44))

        for btn in self.top_buttons:
            btn.draw(screen)

        # Title Text
        title_txt = title_font.render("POWER ICONS & SCREEN PLACEMENT PLUGIN", True, ACCENT_CYAN)
        screen.blit(title_txt, (SCREEN_W - title_txt.get_width() - 20, 12))

        # Toast Message overlay
        if self.toast_timer > 0:
            self.toast_timer -= 1
            t_surf = header_font.render(self.toast_message, True, ACCENT_GREEN)
            t_rect = t_surf.get_rect(center=(SCREEN_W // 2, 22))
            bg_r = t_rect.inflate(20, 8)
            pg.draw.rect(screen, (10, 28, 20), bg_r, border_radius=6)
            pg.draw.rect(screen, ACCENT_GREEN, bg_r, width=1, border_radius=6)
            screen.blit(t_surf, t_rect)

    def run(self):
        clock = pg.time.Clock()
        running = True
        while running:
            running = self.handle_events()

            screen.fill(BG_COLOR)
            self.draw_left_panel()
            self.draw_canvas_panel()
            self.draw_right_panel()
            self.draw_top_bar()

            pg.display.flip()
            clock.tick(60)

        pg.quit()


if __name__ == "__main__":
    plugin = PowerIconsPlugin()
    plugin.run()
