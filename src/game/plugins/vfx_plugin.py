"""
Modular Entity VFX & Blood Plugin.

Provides data-driven querying, dynamic runtime configuration, and persistence for entity
blood and hit visual effect rules (has_blood, vfx_type, vfx_scale).
"""

import os
import json
from typing import Dict, Any, Optional

CONFIG_PATH = "game_data/vfx_config.json"


class VFXPlugin:
    """Plugin to query, update, and persist entity blood and visual effect rules."""

    _config_cache: Optional[Dict[str, Any]] = None

    @classmethod
    def load_config(cls, force_reload: bool = False) -> Dict[str, Any]:
        """Loads or reloads game_data/vfx_config.json."""
        if cls._config_cache is not None and not force_reload:
            return cls._config_cache

        if os.path.exists(CONFIG_PATH):
            try:
                with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                    data: Dict[str, Any] = json.load(f)
                    cls._config_cache = data
                    return data
            except Exception as e:
                print(f"[VFXPlugin] Error reading {CONFIG_PATH}: {e}")

        # Default fallback configuration
        cls._config_cache = {
            "vfx_library": {
                "blood": {"path": "assets/graphics/MiniBlood/Polished/1", "default_fps": 30.0},
                "blood_large": {"path": "assets/graphics/MiniBlood/Polished/3", "default_fps": 30.0},
                "magic_shot": {"path": "assets/graphics/Magic shots/1", "default_fps": 30.0},
                "magic_swirl": {"path": "assets/graphics/swirl magic shots/1", "default_fps": 30.0},
            },
            "entity_rules": {
                "player": {"has_blood": True, "vfx_type": "blood", "vfx_scale": 2.5},
                "skeleton": {"has_blood": False, "vfx_type": "magic_shot", "vfx_scale": 2.5},
                "green_monster": {"has_blood": True, "vfx_type": "blood_large", "vfx_scale": 2.8},
                "blood_zombie": {"has_blood": True, "vfx_type": "blood_large", "vfx_scale": 3.0},
                "goblin": {"has_blood": True, "vfx_type": "blood", "vfx_scale": 2.2},
            },
        }
        return cls._config_cache

    @classmethod
    def save_config(cls) -> bool:
        """Saves current configuration to game_data/vfx_config.json."""
        if cls._config_cache is None:
            return False
        try:
            os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(cls._config_cache, f, indent=4)
            print(f"[VFXPlugin] Successfully saved updated VFX configuration to {CONFIG_PATH}")
            return True
        except Exception as e:
            print(f"[VFXPlugin] Failed to save {CONFIG_PATH}: {e}")
            return False

    @classmethod
    def get_entity_key(cls, entity: Any) -> str:
        """Resolves standard entity_key string for an entity instance or class name."""
        if isinstance(entity, str):
            return entity.lower()

        cls_name = entity.__class__.__name__.lower()
        if "skeleton" in cls_name:
            return "skeleton"
        if "player" in cls_name:
            return "player"
        if "greenmonster" in cls_name or "gatekeeper" in cls_name:
            return "green_monster"
        if "bloodzombie" in cls_name:
            return "blood_zombie"
        if "goblin" in cls_name:
            return "goblin"
        if "firewizard" in cls_name or "wizard" in cls_name:
            return "fire_wizard"
        return cls_name

    @classmethod
    def get_rule(cls, entity_or_key: Any) -> Dict[str, Any]:
        """Gets blood & VFX rule dictionary for an entity or entity_key string."""
        cfg = cls.load_config()
        entity_key = cls.get_entity_key(entity_or_key)
        rules = cfg.get("entity_rules", {})

        if entity_key in rules:
            return dict(rules[entity_key])

        # Default fallback rule
        has_blood = getattr(entity_or_key, "has_blood", True)
        vfx_type = "blood" if has_blood else "magic_shot"
        return {"has_blood": bool(has_blood), "vfx_type": vfx_type, "vfx_scale": 2.5}

    @classmethod
    def set_rule(
        cls,
        entity_key: str,
        has_blood: bool,
        vfx_type: str = "blood",
        vfx_scale: float = 2.5,
        save_to_disk: bool = True,
    ) -> Dict[str, Any]:
        """Updates and optionally persists blood & VFX rules for an entity_key."""
        cfg = cls.load_config()
        key = entity_key.lower()
        rule = {
            "has_blood": has_blood,
            "vfx_type": vfx_type,
            "vfx_scale": vfx_scale,
        }
        cfg.setdefault("entity_rules", {})[key] = rule

        if save_to_disk:
            cls.save_config()
        return rule

    @classmethod
    def apply_to_entity(cls, entity: Any) -> None:
        """Injects has_blood, vfx_type, and vfx_scale attributes onto an entity instance."""
        rule = cls.get_rule(entity)
        setattr(entity, "has_blood", rule["has_blood"])
        setattr(entity, "vfx_type", rule["vfx_type"])
        setattr(entity, "vfx_scale", rule["vfx_scale"])

    @classmethod
    def get_vfx_path(cls, vfx_type: str) -> Optional[str]:
        """Looks up the folder path for a registered VFX key."""
        cfg = cls.load_config()
        lib = cfg.get("vfx_library", {})
        if vfx_type in lib:
            return lib[vfx_type].get("path")
        return None
