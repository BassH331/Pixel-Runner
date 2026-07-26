import os
import json
import math
import pygame as pg
from typing import Dict, Any, Optional, Tuple

class PowerIconsManager:
    """
    Runtime manager for displaying configured Power HUD icons on screen.
    Loads settings from game_data/power_icons_config.json and renders icons,
    frames, keybinding badges, and cooldown overlays during gameplay.
    """
    CONFIG_PATH = "game_data/power_icons_config.json"

    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or self.CONFIG_PATH
        self.config: Dict[str, Any] = {}
        self.icon_surfaces: Dict[str, pg.Surface] = {}
        self.fonts: Dict[str, pg.font.Font] = {}
        self._init_fonts()
        self.load_config()

    def _init_fonts(self):
        if not pg.font.get_init():
            pg.font.init()
        try:
            self.badge_font = pg.font.SysFont("Arial", 11, bold=True)
            self.label_font = pg.font.SysFont("Arial", 10, bold=True)
            self.timer_font = pg.font.SysFont("Consolas", 14, bold=True)
        except Exception:
            self.badge_font = pg.font.Font(None, 14)
            self.label_font = pg.font.Font(None, 12)
            self.timer_font = pg.font.Font(None, 16)

    def load_config(self):
        """Load power icons layout configuration from JSON file."""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r") as f:
                    self.config = json.load(f)
            except Exception as e:
                print(f"[PowerIconsManager] Failed to load {self.config_path}: {e}")
                self.config = self.get_default_config()
        else:
            self.config = self.get_default_config()

        self._preload_assets()

    @staticmethod
    def get_default_config() -> Dict[str, Any]:
        return {
            "screen_width": 1280,
            "screen_height": 720,
            "show_cooldown_timers": True,
            "show_keybind_badges": True,
            "global_scale": 1.0,
            "icons": {
                "ATTACK_THRUST": {
                    "enabled": True,
                    "label": "Thrust",
                    "asset_path": "",
                    "x": 480,
                    "y": 640,
                    "width": 52,
                    "height": 52,
                    "scale": 1.0,
                    "opacity": 255,
                    "keybind": "Q",
                    "frame_style": "circle",
                    "border_color": [0, 229, 255],
                    "badge_bg": [0, 140, 200],
                    "anchor": "center"
                },
                "ATTACK_POWER": {
                    "enabled": True,
                    "label": "Power Atk",
                    "asset_path": "",
                    "x": 545,
                    "y": 640,
                    "width": 52,
                    "height": 52,
                    "scale": 1.0,
                    "opacity": 255,
                    "keybind": "W",
                    "frame_style": "circle",
                    "border_color": [255, 145, 0],
                    "badge_bg": [200, 100, 0],
                    "anchor": "center"
                },
                "SPECIAL_ATTACK": {
                    "enabled": True,
                    "label": "Special",
                    "asset_path": "",
                    "x": 610,
                    "y": 640,
                    "width": 58,
                    "height": 58,
                    "scale": 1.1,
                    "opacity": 255,
                    "keybind": "F",
                    "frame_style": "glowing",
                    "border_color": [170, 0, 255],
                    "badge_bg": [130, 0, 200],
                    "anchor": "center"
                }
            }
        }

    def _preload_assets(self):
        """Load and cache icon images."""
        self.icon_surfaces.clear()
        icons = self.config.get("icons", {})

        for pkey, pdata in icons.items():
            path = pdata.get("asset_path", "")
            if path and os.path.exists(path):
                try:
                    img = pg.image.load(path).convert_alpha()
                    w = int(pdata.get("width", 52) * pdata.get("scale", 1.0))
                    h = int(pdata.get("height", 52) * pdata.get("scale", 1.0))
                    scaled = pg.transform.smoothscale(img, (w, h))
                    self.icon_surfaces[pkey] = scaled
                except Exception as e:
                    print(f"[PowerIconsManager] Could not load image {path}: {e}")
                    self.icon_surfaces[pkey] = self._create_placeholder_icon(pkey, pdata)
            else:
                self.icon_surfaces[pkey] = self._create_placeholder_icon(pkey, pdata)

    def _create_placeholder_icon(self, key: str, pdata: Dict[str, Any]) -> pg.Surface:
        """Create clean stylized procedural placeholder icon when no image file is set."""
        w = int(pdata.get("width", 52) * pdata.get("scale", 1.0))
        h = int(pdata.get("height", 52) * pdata.get("scale", 1.0))
        surf = pg.Surface((w, h), pg.SRCALPHA)

        color = pdata.get("border_color", [0, 229, 255])
        # Dark gradient background
        pg.draw.circle(surf, (20, 24, 34, 220), (w // 2, h // 2), min(w, h) // 2 - 2)
        pg.draw.circle(surf, color, (w // 2, h // 2), min(w, h) // 2 - 2, width=2)

        # Draw letter identifier
        label = pdata.get("label", key)[:2].upper()
        txt = self.badge_font.render(label, True, (240, 240, 245))
        surf.blit(txt, (w // 2 - txt.get_width() // 2, h // 2 - txt.get_height() // 2))

        return surf

    def draw_frame(self, surface: pg.Surface, rect: pg.Rect, style: str, border_color: Tuple[int, int, int], active: bool = False):
        """Render stylish icon outer frame/border (circle, square, hexagon, glowing ring)."""
        color = border_color
        cx, cy = rect.center
        r = min(rect.width, rect.height) // 2

        if style == "circle":
            pg.draw.circle(surface, (14, 18, 26, 200), (cx, cy), r)
            pg.draw.circle(surface, color, (cx, cy), r, width=2 if not active else 3)
        elif style == "square":
            pg.draw.rect(surface, (14, 18, 26, 200), rect, border_radius=8)
            pg.draw.rect(surface, color, rect, width=2 if not active else 3, border_radius=8)
        elif style == "hexagon":
            pts = []
            for i in range(6):
                angle = math.radians(60 * i - 30)
                pts.append((cx + r * math.cos(angle), cy + r * math.sin(angle)))
            pg.draw.polygon(surface, (14, 18, 26, 200), pts)
            pg.draw.polygon(surface, color, pts, width=2)
        elif style == "glowing":
            # Glow rings
            for g_r, alpha in [(r + 4, 40), (r + 2, 90), (r, 220)]:
                glow_surf = pg.Surface((g_r * 2 + 4, g_r * 2 + 4), pg.SRCALPHA)
                pg.draw.circle(glow_surf, (*color, alpha), (g_r + 2, g_r + 2), g_r, width=2)
                surface.blit(glow_surf, (cx - g_r - 2, cy - g_r - 2))
            pg.draw.circle(surface, (14, 18, 26, 220), (cx, cy), r)
            pg.draw.circle(surface, (255, 255, 255), (cx, cy), r, width=2)

    def get_keybind_badge_label(self, pkey: str, default_keybind: str) -> str:
        """Resolve current keybinding text from ControlsManager or fallback."""
        try:
            from src.game.controls_manager import ControlsManager
            cm = ControlsManager()
            binding = cm.get_binding(pkey)
            if binding:
                if cm.mode == "JOYSTICK":
                    btn_map = {
                        "BUTTON_0": "✕",  # Bottom (Cross)
                        "BUTTON_1": "○",  # Right (Circle)
                        "BUTTON_2": "□",  # Left (Box / Square)
                        "BUTTON_3": "△",  # Top (Triangle)
                        "BUTTON_4": "L1",
                        "BUTTON_5": "R1",
                        "BUTTON_6": "L2",
                        "BUTTON_7": "R2",
                        "BUTTON_8": "SELECT",
                        "BUTTON_9": "START",
                    }
                    for key, val in btn_map.items():
                        if key in binding:
                            return val
                    return binding
                else:
                    return binding.upper()
        except Exception:
            pass
        return default_keybind

    def draw(
        self,
        surface: pg.Surface,
        cooldowns: Optional[Dict[str, float]] = None,
        active_powers: Optional[Dict[str, bool]] = None
    ):
        """
        Draw all active power HUD icons to target Pygame surface.
        cooldowns: dict mapping power_key -> progress ratio (0.0 = ready, 1.0 = on full cooldown)
        active_powers: dict mapping power_key -> bool (is currently active / held)
        """
        if not self.config.get("icons"):
            return

        cooldowns = cooldowns or {}
        active_powers = active_powers or {}
        show_badges = self.config.get("show_keybind_badges", True)

        for pkey, pdata in self.config["icons"].items():
            if not pdata.get("enabled", True):
                continue

            x = pdata.get("x", 100)
            y = pdata.get("y", 100)
            w = int(pdata.get("width", 52) * pdata.get("scale", 1.0))
            h = int(pdata.get("height", 52) * pdata.get("scale", 1.0))
            anchor = pdata.get("anchor", "center")

            # Handle anchor positioning
            if anchor == "center":
                rect = pg.Rect(x - w // 2, y - h // 2, w, h)
            elif anchor == "top-left":
                rect = pg.Rect(x, y, w, h)
            elif anchor == "top-right":
                rect = pg.Rect(x - w, y, w, h)
            elif anchor == "bottom-left":
                rect = pg.Rect(x, y - h, w, h)
            elif anchor == "bottom-right":
                rect = pg.Rect(x - w, y - h, w, h)
            else:
                rect = pg.Rect(x - w // 2, y - h // 2, w, h)

            style = pdata.get("frame_style", "circle")
            border_color = tuple(pdata.get("border_color", [0, 229, 255]))
            is_active = active_powers.get(pkey, False)

            # Draw outer frame
            self.draw_frame(surface, rect, style, border_color, active=is_active)

            # Draw cached icon surface
            icon_surf = self.icon_surfaces.get(pkey)
            if icon_surf:
                opacity = pdata.get("opacity", 255)
                if opacity < 255:
                    temp = icon_surf.copy()
                    temp.set_alpha(opacity)
                    surface.blit(temp, (rect.centerx - temp.get_width() // 2, rect.centery - temp.get_height() // 2))
                else:
                    surface.blit(icon_surf, (rect.centerx - icon_surf.get_width() // 2, rect.centery - icon_surf.get_height() // 2))

            # Render Cooldown Overlay (radial sweep / darkened arc)
            cd_ratio = cooldowns.get(pkey, 0.0)
            if cd_ratio > 0.0:
                cd_ratio = min(1.0, max(0.0, cd_ratio))
                cd_surf = pg.Surface((rect.width, rect.height), pg.SRCALPHA)
                cd_surf.fill((0, 0, 0, 160))
                # Crop height proportional to cooldown remaining
                cd_height = int(rect.height * cd_ratio)
                surface.blit(cd_surf, rect.topleft, area=pg.Rect(0, 0, rect.width, cd_height))

            # Keybind Badge
            raw_keybind = pdata.get("keybind", "")
            keybind = self.get_keybind_badge_label(pkey, raw_keybind)
            if show_badges and keybind:
                badge_bg = tuple(pdata.get("badge_bg", [0, 140, 200]))
                badge_txt = self.badge_font.render(keybind, True, (255, 255, 255))
                bw = badge_txt.get_width() + 8
                bh = 16
                bx = rect.centerx - bw // 2
                by = rect.bottom - bh // 2
                badge_rect = pg.Rect(bx, by, bw, bh)

                pg.draw.rect(surface, (10, 14, 20), badge_rect.inflate(2, 2), border_radius=4)
                pg.draw.rect(surface, badge_bg, badge_rect, border_radius=4)
                surface.blit(badge_txt, (bx + 4, by + 1))
