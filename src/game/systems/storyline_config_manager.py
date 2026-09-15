"""
Storyline Config Manager for Pixel-Runner.

Data-driven configuration manager that loads game_data/storyline_config.json,
handles hot-reloading on modification, and provides API access to relics, corruption physics,
boss progression hierarchy, and Angel vs. Devil micro-barks.
"""
from typing import Dict, Any, Optional, List
import json
import os
import time

CONFIG_PATH = "game_data/storyline_config.json"

class StorylineConfigManager:
    _instance: Optional["StorylineConfigManager"] = None

    def __init__(self, config_path: str = CONFIG_PATH):
        StorylineConfigManager._instance = self
        self.config_path = config_path
        self._last_mtime: float = 0.0
        self.data: Dict[str, Any] = {}
        self.load_config()

    @classmethod
    def get_instance(cls) -> "StorylineConfigManager":
        if cls._instance is None:
            cls._instance = StorylineConfigManager()
        return cls._instance

    def load_config(self) -> Dict[str, Any]:
        """Load or reload JSON configuration from file."""
        if not os.path.exists(self.config_path):
            print(f"[StorylineConfigManager] Config file {self.config_path} not found. Creating fallback.")
            self._create_default_config()

        try:
            mtime = os.path.getmtime(self.config_path)
            with open(self.config_path, "r", encoding="utf-8") as f:
                self.data = json.load(f)
            self._last_mtime = mtime
            print(f"[StorylineConfigManager] Successfully loaded {self.config_path}")
        except Exception as e:
            print(f"[StorylineConfigManager] Error loading {self.config_path}: {e}")
            if not self.data:
                self._create_default_config()

        return self.data

    def check_hot_reload(self) -> bool:
        """Check if storyline_config.json has changed on disk and reload if modified."""
        if not os.path.exists(self.config_path):
            return False
        try:
            mtime = os.path.getmtime(self.config_path)
            if mtime > self._last_mtime:
                print(f"[StorylineConfigManager] File modification detected in {self.config_path}. Hot-reloading...")
                self.load_config()
                return True
        except Exception:
            pass
        return False

    def save_config(self, new_data: Dict[str, Any]) -> bool:
        """Save configuration back to JSON with automatic backup creation."""
        try:
            # Backup existing file if present
            if os.path.exists(self.config_path):
                backup_path = f"{self.config_path}.backup_{int(time.time())}"
                with open(self.config_path, "r", encoding="utf-8") as src, open(backup_path, "w", encoding="utf-8") as dst:
                    dst.write(src.read())

            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(new_data, f, indent=2)

            self.data = new_data
            self._last_mtime = os.path.getmtime(self.config_path)
            print(f"[StorylineConfigManager] Configuration saved to {self.config_path}")
            return True
        except Exception as e:
            print(f"[StorylineConfigManager] Error saving configuration: {e}")
            return False

    def get_relics(self) -> Dict[str, Any]:
        """Return dictionary of configured relics."""
        return self.data.get("relics", {})

    def get_corruption_config(self) -> Dict[str, Any]:
        """Return corruption physics and vignette parameters."""
        return self.data.get("corruption", {
            "dash_speed_multiplier": 1.5,
            "damage_multiplier": 1.5,
            "vignette_alpha": 180,
            "instability_enabled": True
        })

    def get_boss_hierarchy(self) -> List[str]:
        """Return 5-boss progression hierarchy list."""
        return self.data.get("boss_hierarchy", [
            "green_monster", "gatekeeper", "necromancer", "fire_wizard", "dark_ronin"
        ])

    def get_whisperers(self) -> Dict[str, Any]:
        """Return Angel vs. Devil micro-barks."""
        return self.data.get("whisperers", {})

    def _create_default_config(self) -> None:
        """Fallback default config initialization."""
        self.data = {
            "version": "1.0.0",
            "relics": {},
            "corruption": {
                "dash_speed_multiplier": 1.5,
                "damage_multiplier": 1.5,
                "vignette_alpha": 180,
                "instability_enabled": True
            },
            "boss_hierarchy": ["green_monster", "gatekeeper", "necromancer", "fire_wizard", "dark_ronin"],
            "whisperers": {}
        }
