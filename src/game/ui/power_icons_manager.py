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

    _instance = None

    def __init__(self, config_path: Optional[str] = None):
        PowerIconsManager._instance = self
        self.config_path = config_path or self.CONFIG_PATH
        self.config: Dict[str, Any] = {}
        self.icon_surfaces: Dict[str, pg.Surface] = {}
        self.fonts: Dict[str, pg.font.Font] = {}
        self.glow_frames: list = []
        self.active_pop_effects: list = []
        self._init_fonts()
        self.load_config()
        self._load_glow_frames()

    def _load_glow_frames(self):
        """Pre-load animated icon glow sprite frames from assets/icon_glow_sprites."""
        self.glow_frames.clear()
        folder = "assets/icon_glow_sprites"
        if not os.path.exists(folder):
            folder = "assets/icon_glow_sprites (2)"
        if os.path.exists(folder):
            for i in range(15):
                path = os.path.join(folder, f"icon_glow_{i:02d}.png")
                if os.path.exists(path):
                    try:
                        img = pg.image.load(path)
                        try:
                            img = img.convert_alpha()
                        except Exception:
                            pass
                        self.glow_frames.append(img)
                    except Exception as e:
                        print(f"[PowerIconsManager] Could not load glow frame {path}: {e}")

    @classmethod
    def trigger(cls, pkey: str, world_pos: Optional[Tuple[int, int]] = None):
        """Class helper to trigger action pop-in FX from anywhere in game code."""
        if cls._instance:
            cls._instance.trigger_power_effect(pkey, world_pos)

    def trigger_power_effect(self, pkey: str, world_pos: Optional[Tuple[int, int]] = None):
        """Trigger a Power Rangers-style action pop-in effect with full portal glow FX!"""
        self.active_pop_effects.append({
            "key": pkey,
            "start_time": pg.time.get_ticks(),
            "duration": 480,  # 480ms smooth portal animation
            "pos": world_pos
        })

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

        self._badge_cache: dict = {}
        self._cd_surface_cache: dict = {}

    def load_config(self):
        """Load power icons layout configuration from JSON file."""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r") as f:
                    self.config = json.load(f)
                self._preload_assets()
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
                    img = pg.image.load(path)
                    try:
                        img = img.convert_alpha()
                    except Exception:
                        pass
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
        """Resolve current keybinding text from ControlsManager or fallback, formatting axes nicely."""
        raw_binding = default_keybind
        try:
            from src.game.controls_manager import ControlsManager
            cm = ControlsManager()
            b = cm.get_binding(pkey)
            if b:
                raw_binding = b
        except Exception:
            pass

        return self.format_binding_label(raw_binding)

    def format_binding_label(self, binding: str) -> str:
        """Format raw binding string into clean compact HUD badge text."""
        if not binding:
            return ""

        label_map = {
            "BUTTON_0": "✕",
            "BUTTON_1": "○",
            "BUTTON_2": "△",
            "BUTTON_3": "□",
            "BUTTON_4": "L1",
            "BUTTON_5": "R1",
            "BUTTON_6": "L2",
            "BUTTON_7": "R2",
            "BUTTON_8": "SELECT",
            "BUTTON_9": "START",
            "AXIS_0_MINUS": "L←",
            "AXIS_0_PLUS":  "L→",
            "AXIS_1_MINUS": "L↑",
            "AXIS_1_PLUS":  "L↓",
            "AXIS_2_MINUS": "R←",
            "AXIS_2_PLUS":  "R→",
            "AXIS_3_MINUS": "R←",
            "AXIS_3_PLUS":  "R→",
            "AXIS_4_MINUS": "R↑",
            "AXIS_4_PLUS":  "R↓",
        }

        if "+" in binding:
            parts = [p.strip() for p in binding.split("+")]
            formatted = [label_map.get(p, p) for p in parts]
            return " + ".join(formatted)

        return label_map.get(binding, binding)

    STAMINA_COSTS: Dict[str, float] = {
        "JUMP": 12.0,
        "ROLL": 20.0,
        "DASH": 20.0,
        "ATTACK_THRUST": 22.0,
        "ATTACK_SMASH": 35.0,
        "ATTACK_POWER": 48.0,
        "SPECIAL_ATTACK": 60.0,
        "DEFEND": 15.0,
    }

    def _crop_to_circle(self, surf: pg.Surface) -> pg.Surface:
        """Crop an image surface into a smooth circular mask."""
        w, h = surf.get_size()
        r = min(w, h) // 2
        mask = pg.Surface((w, h), pg.SRCALPHA)
        pg.draw.circle(mask, (255, 255, 255, 255), (w // 2, h // 2), r)

        result = pg.Surface((w, h), pg.SRCALPHA)
        result.blit(surf, (0, 0))
        result.blit(mask, (0, 0), special_flags=pg.BLEND_RGBA_MULT)
        return result

    def draw(
        self,
        surface: pg.Surface,
        cooldowns: Optional[Dict[str, float]] = None,
        active_powers: Optional[Dict[str, bool]] = None,
        current_stamina: Optional[float] = None,
        max_stamina: Optional[float] = None,
        current_mana: Optional[float] = None,
        max_mana: Optional[float] = None
    ):
        """
        Draw all active power HUD icons to target Pygame surface.
        cooldowns: dict mapping power_key -> progress ratio (0.0 = ready, 1.0 = on full cooldown)
        active_powers: dict mapping power_key -> bool (is currently active / held)
        current_stamina: player's current stamina (dims icons when stamina is insufficient)
        """
        cooldowns = cooldowns or {}
        active_powers = active_powers or {}
        show_badges = self.config.get("show_keybind_badges", True)
        show_overlay = self.config.get("show_hud_overlay", False)

        # Only draw persistent HUD overlay icons if show_hud_overlay is enabled (e.g. Tutorial Mode)
        if show_overlay and self.config.get("icons"):
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

                # Check resource requirement to dim icon if stamina/mana is insufficient
                base_opacity = pdata.get("opacity", 255)
                resource_type = pdata.get("resource_type", "stamina")
                cost = pdata.get("cost", self.STAMINA_COSTS.get(pkey, 20.0))

                is_depleted = False
                if resource_type == "mana":
                    if current_mana is not None and current_mana < cost:
                        is_depleted = True
                elif resource_type == "stamina":
                    if current_stamina is not None and current_stamina < cost:
                        is_depleted = True

                if is_depleted:
                    effective_opacity = max(50, int(base_opacity * 0.30))
                    frame_color = (max(30, border_color[0] // 3), max(30, border_color[1] // 3), max(30, border_color[2] // 3))
                else:
                    effective_opacity = base_opacity
                    frame_color = border_color

                # Draw outer frame
                self.draw_frame(surface, rect, style, frame_color, active=is_active)

                # Draw cached icon surface
                icon_surf = self.icon_surfaces.get(pkey)
                if icon_surf:
                    icon_w = int(w * 0.88)
                    icon_h = int(h * 0.88)
                    scaled = pg.transform.smoothscale(icon_surf, (icon_w, icon_h))

                    if style in ("circle", "glowing"):
                        scaled = self._crop_to_circle(scaled)

                    if effective_opacity < 255:
                        alpha_surf = pg.Surface(scaled.get_size(), pg.SRCALPHA)
                        alpha_surf.fill((255, 255, 255, effective_opacity))
                        scaled.blit(alpha_surf, (0, 0), special_flags=pg.BLEND_RGBA_MULT)

                    surface.blit(scaled, (rect.centerx - scaled.get_width() // 2, rect.centery - scaled.get_height() // 2))

                # Render Cooldown Overlay (radial sweep / darkened arc)
                cd_ratio = cooldowns.get(pkey, 0.0)
                if cd_ratio > 0.0:
                    cd_ratio = min(1.0, max(0.0, cd_ratio))
                    size_key = (rect.width, rect.height)
                    if size_key not in self._cd_surface_cache:
                        cd_s = pg.Surface(size_key, pg.SRCALPHA).convert_alpha()
                        cd_s.fill((0, 0, 0, 160))
                        self._cd_surface_cache[size_key] = cd_s
                    cd_surf = self._cd_surface_cache[size_key]
                    cd_height = int(rect.height * cd_ratio)
                    surface.blit(cd_surf, rect.topleft, area=pg.Rect(0, 0, rect.width, cd_height))

                # Keybind Badge
                raw_keybind = pdata.get("keybind", "")
                keybind = self.get_keybind_badge_label(pkey, raw_keybind)
                if show_badges and keybind:
                    badge_bg = tuple(pdata.get("badge_bg", [0, 140, 200]))
                    if keybind not in self._badge_cache:
                        self._badge_cache[keybind] = self.badge_font.render(keybind, True, (255, 255, 255))
                    badge_txt = self._badge_cache[keybind]
                    bw = badge_txt.get_width() + 8
                    bh = 16
                    bx = rect.centerx - bw // 2
                    by = rect.bottom - bh // 2
                    badge_rect = pg.Rect(bx, by, bw, bh)

                    pg.draw.rect(surface, (10, 14, 20), badge_rect.inflate(2, 2), border_radius=4)
                    pg.draw.rect(surface, badge_bg, badge_rect, border_radius=4)
                    surface.blit(badge_txt, (bx + 4, by + 1))

        # Render active Power Rangers-style pop-in action FX with icon_glow animated frames
        now = pg.time.get_ticks()
        remaining_effects = []
        for fx in self.active_pop_effects:
            elapsed = now - fx["start_time"]
            if elapsed < fx["duration"]:
                remaining_effects.append(fx)
                t = elapsed / fx["duration"]
                scale = 1.0 + math.sin(t * math.pi) * 0.50
                alpha = int(255 * (1.0 - t))

                pkey = fx["key"]
                icon_surf = self.icon_surfaces.get(pkey)

                if fx["pos"] and icon_surf:
                    px, py = fx["pos"]
                    py_float = py - int(t * 40)
                    bw = max(10, int(50 * scale))
                    bh = max(10, int(50 * scale))

                    # Render animated icon_glow frame as power frame background
                    if self.glow_frames:
                        frame_idx = int(t * len(self.glow_frames)) % len(self.glow_frames)
                        glow_img = self.glow_frames[frame_idx]
                        glow_w = int(bw * 2.8)
                        glow_h = int(bh * 2.8)
                        glow_scaled = pg.transform.smoothscale(glow_img, (glow_w, glow_h))

                        if alpha < 255:
                            alpha_s = pg.Surface(glow_scaled.get_size(), pg.SRCALPHA)
                            alpha_s.fill((255, 255, 255, alpha))
                            glow_scaled.blit(alpha_s, (0, 0), special_flags=pg.BLEND_RGBA_MULT)

                        surface.blit(glow_scaled, (px - glow_w // 2, py_float - glow_h // 2))

                    pop_surf = pg.transform.smoothscale(icon_surf, (bw, bh))
                    if pkey in self.config.get("icons", {}):
                        style = self.config["icons"][pkey].get("frame_style", "circle")
                        if style in ("circle", "glowing"):
                            pop_surf = self._crop_to_circle(pop_surf)

                    alpha_surf = pg.Surface(pop_surf.get_size(), pg.SRCALPHA)
                    alpha_surf.fill((255, 255, 255, alpha))
                    pop_surf.blit(alpha_surf, (0, 0), special_flags=pg.BLEND_RGBA_MULT)

                    surface.blit(pop_surf, (px - bw // 2, py_float - bh // 2))

        self.active_pop_effects = remaining_effects
