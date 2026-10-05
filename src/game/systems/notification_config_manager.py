"""
Notification Config Manager for Pixel-Runner.

Data-driven configuration manager that loads game_data/notification_config.json,
handles hot-reloading on modification, and provides API access to timing, layout,
colors, typography, and preset themes for side notifications and popups.
"""
from __future__ import annotations

import json
import os
import time
from typing import Dict, Any, Optional

CONFIG_PATH = "game_data/notification_config.json"

DEFAULT_NOTIFICATION_CONFIG: Dict[str, Any] = {
    "timing": {
        "slide_in_time": 0.35,
        "default_hold_time": 8.5,
        "slide_out_time": 0.35,
        "words_per_sec": 0.35,
        "base_hold_pad": 2.5,
        "easing_type": "cubic_ease_out",
        "breath_shimmer_enabled": True,
        "breath_amplitude": 2.0,
        "breath_speed": 3.5,
        "fade_on_slide_out": True,
    },
    "layout": {
        "anchor": "top_right",
        "tab_width": 390,
        "min_height": 82,
        "margin_x": 20,
        "top_y": 105,
        "padding_x": 14,
        "padding_y": 12,
        "corner_radius": 10,
        "border_width": 2,
        "accent_notch_width": 5,
        "accent_notch_enabled": True,
        "spacing": 4,
        "badge_size": 50,
        "icon_size": 36,
    },
    "colors": {
        "bg_color": [16, 12, 24, 235],
        "inner_color": [28, 22, 38, 225],
        "border_color": [218, 165, 32, 230],
        "accent_notch_color": [255, 215, 80, 240],
        "badge_bg_color": [10, 8, 16, 240],
        "badge_border_color": [200, 150, 40, 220],
        "title_color": [255, 215, 80],
        "title_shadow_color": [0, 0, 0],
        "body_color": [235, 230, 220],
        "body_shadow_color": [10, 8, 14],
    },
    "typography": {
        "title_font_path": "assets/font/Abaddon Bold.ttf",
        "title_font_size": 22,
        "title_drop_shadow": True,
        "body_font_path": "assets/graphics/Darinia/Darinia.ttf",
        "body_font_size": 15,
        "body_drop_shadow": True,
        "line_spacing": 1.0,
    },
}

THEME_PRESETS: Dict[str, Dict[str, Any]] = {
    "gothic_gold": {
        "name": "Gothic Gold (Classic)",
        "colors": {
            "bg_color": [16, 12, 24, 235],
            "inner_color": [28, 22, 38, 225],
            "border_color": [218, 165, 32, 230],
            "accent_notch_color": [255, 215, 80, 240],
            "badge_bg_color": [10, 8, 16, 240],
            "badge_border_color": [200, 150, 40, 220],
            "title_color": [255, 215, 80],
            "title_shadow_color": [0, 0, 0],
            "body_color": [235, 230, 220],
            "body_shadow_color": [10, 8, 14],
        },
        "layout": {"corner_radius": 10, "border_width": 2, "accent_notch_width": 5, "accent_notch_enabled": True},
    },
    "blood_bone": {
        "name": "Eldritch Blood & Bone",
        "colors": {
            "bg_color": [22, 10, 15, 245],
            "inner_color": [36, 16, 22, 235],
            "border_color": [215, 200, 185, 230],
            "accent_notch_color": [200, 30, 45, 240],
            "badge_bg_color": [18, 8, 12, 240],
            "badge_border_color": [180, 40, 50, 220],
            "title_color": [245, 75, 90],
            "title_shadow_color": [0, 0, 0],
            "body_color": [240, 230, 225],
            "body_shadow_color": [20, 5, 10],
        },
        "layout": {"corner_radius": 8, "border_width": 2, "accent_notch_width": 5, "accent_notch_enabled": True},
    },
    "arcane_void": {
        "name": "Arcane Void Cyan",
        "colors": {
            "bg_color": [8, 14, 26, 245],
            "inner_color": [14, 24, 44, 235],
            "border_color": [0, 210, 255, 230],
            "accent_notch_color": [80, 235, 255, 240],
            "badge_bg_color": [6, 12, 20, 240],
            "badge_border_color": [0, 180, 220, 220],
            "title_color": [0, 230, 255],
            "title_shadow_color": [0, 0, 0],
            "body_color": [210, 235, 250],
            "body_shadow_color": [4, 10, 18],
        },
        "layout": {"corner_radius": 10, "border_width": 2, "accent_notch_width": 5, "accent_notch_enabled": True},
    },
    "grimoire_leather": {
        "name": "Ancient Grimoire Leather",
        "colors": {
            "bg_color": [26, 18, 14, 245],
            "inner_color": [40, 28, 20, 235],
            "border_color": [185, 140, 60, 230],
            "accent_notch_color": [225, 175, 80, 240],
            "badge_bg_color": [18, 12, 9, 240],
            "badge_border_color": [160, 115, 45, 220],
            "title_color": [255, 200, 110],
            "title_shadow_color": [0, 0, 0],
            "body_color": [240, 225, 205],
            "body_shadow_color": [16, 10, 6],
        },
        "layout": {"corner_radius": 6, "border_width": 2, "accent_notch_width": 4, "accent_notch_enabled": True},
    },
    "clean_minimalist": {
        "name": "Sleek Dark Glass",
        "colors": {
            "bg_color": [12, 14, 20, 230],
            "inner_color": [20, 24, 34, 220],
            "border_color": [140, 150, 175, 220],
            "accent_notch_color": [190, 200, 220, 230],
            "badge_bg_color": [10, 12, 16, 240],
            "badge_border_color": [120, 130, 150, 200],
            "title_color": [255, 255, 255],
            "title_shadow_color": [0, 0, 0],
            "body_color": [220, 225, 235],
            "body_shadow_color": [5, 6, 10],
        },
        "layout": {"corner_radius": 14, "border_width": 1, "accent_notch_width": 0, "accent_notch_enabled": False},
    },
}


class NotificationConfigManager:
    """Singleton manager for reading, caching, hot-reloading, and saving notification parameters."""

    _instance: Optional["NotificationConfigManager"] = None

    def __init__(self, config_path: str = CONFIG_PATH):
        if config_path == CONFIG_PATH:
            NotificationConfigManager._instance = self
        self.config_path = config_path
        self._last_mtime: float = 0.0
        self.revision: int = 0
        self.data: Dict[str, Any] = {}
        self.load_config()

    @classmethod
    def get_instance(cls, config_path: str = CONFIG_PATH) -> "NotificationConfigManager":
        if cls._instance is None or cls._instance.config_path != config_path:
            cls._instance = NotificationConfigManager(config_path=config_path)
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Reset the singleton instance for testing isolation."""
        cls._instance = None

    def load_config(self) -> Dict[str, Any]:
        """Load configuration from JSON file or create fallback if absent."""
        if not os.path.exists(self.config_path):
            self.data = json.loads(json.dumps(DEFAULT_NOTIFICATION_CONFIG))
            self._save_to_disk(self.data)
            self.revision += 1
            return self.data

        try:
            mtime = os.path.getmtime(self.config_path)
            with open(self.config_path, "r", encoding="utf-8") as f:
                loaded = json.load(f)

            # Ensure all sections exist by deep merging with defaults
            merged = json.loads(json.dumps(DEFAULT_NOTIFICATION_CONFIG))
            for section, subdict in loaded.items():
                if isinstance(subdict, dict) and section in merged:
                    merged[section].update(subdict)
                else:
                    merged[section] = subdict

            self.data = merged
            self._last_mtime = mtime
            self.revision += 1
        except Exception as e:
            print(f"[NotificationConfigManager] Error loading {self.config_path}: {e}")
            if not self.data:
                self.data = json.loads(json.dumps(DEFAULT_NOTIFICATION_CONFIG))
                self.revision += 1

        return self.data

    def check_hot_reload(self) -> bool:
        """Check if file was modified on disk and reload if necessary."""
        if not os.path.exists(self.config_path):
            return False
        try:
            mtime = os.path.getmtime(self.config_path)
            if mtime > self._last_mtime:
                self.load_config()
                return True
        except Exception:
            pass
        return False

    def save_config(self, new_data: Dict[str, Any]) -> bool:
        """Save configuration with automatic timestamped backup."""
        try:
            if os.path.exists(self.config_path):
                backup_path = f"{self.config_path}.backup_{int(time.time())}"
                with open(self.config_path, "r", encoding="utf-8") as src, open(backup_path, "w", encoding="utf-8") as dst:
                    dst.write(src.read())

            self._save_to_disk(new_data)
            self.data = json.loads(json.dumps(new_data))
            self._last_mtime = os.path.getmtime(self.config_path)
            self.revision += 1
            return True
        except Exception as e:
            print(f"[NotificationConfigManager] Failed to save {self.config_path}: {e}")
            return False

    def _save_to_disk(self, data: Dict[str, Any]) -> None:
        os.makedirs(os.path.dirname(os.path.abspath(self.config_path)), exist_ok=True)
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)

    def apply_preset(self, preset_key: str) -> bool:
        """Apply a curated visual theme preset."""
        preset = THEME_PRESETS.get(preset_key)
        if not preset:
            return False

        if "colors" in preset:
            self.data["colors"].update(preset["colors"])
        if "layout" in preset:
            self.data["layout"].update(preset["layout"])

        self.revision += 1
        return True
