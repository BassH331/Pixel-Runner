"""
Shadow Registry System.

Manages data-driven shadow profiles, loaded from game_data/shadow_config.json.
Provides thread-safe caching, live file-change detection, and save capabilities.
"""

from __future__ import annotations

import json
import os
try:
    import fcntl
except ImportError:
    fcntl = None
from dataclasses import dataclass, asdict
from typing import Optional, Any

CONFIG_PATH = "game_data/shadow_config.json"


@dataclass
class ShadowProfile:
    alpha: int = 120
    squash_ratio: float = 0.25
    y_offset: int = 0
    fade_height: float = 250.0
    ground_snap: float = 12.0
    scale_mult: float = 1.0

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ShadowProfile:
        return cls(
            alpha=int(data.get("alpha", 120)),
            squash_ratio=float(data.get("squash_ratio", 0.25)),
            y_offset=int(data.get("y_offset", 0)),
            fade_height=float(data.get("fade_height", 250.0)),
            ground_snap=float(data.get("ground_snap", 12.0)),
            scale_mult=float(data.get("scale_mult", 1.0)),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ShadowRegistry:
    """
    Registry for entity shadow profiles.
    Caches profiles in memory and automatically reloads when shadow_config.json changes.
    """

    _cache: dict[str, ShadowProfile] = {}
    _last_mtime: float = -1.0

    DEFAULTS: dict[str, ShadowProfile] = {
        "default": ShadowProfile(alpha=120, squash_ratio=0.25, y_offset=0, fade_height=250.0, ground_snap=12.0, scale_mult=1.0),
        "player": ShadowProfile(alpha=125, squash_ratio=0.25, y_offset=0, fade_height=250.0, ground_snap=12.0, scale_mult=1.0),
        "skeleton": ShadowProfile(alpha=120, squash_ratio=0.25, y_offset=0, fade_height=250.0, ground_snap=12.0, scale_mult=1.0),
        "enemy": ShadowProfile(alpha=95, squash_ratio=0.22, y_offset=0, fade_height=650.0, ground_snap=0.0, scale_mult=1.0),
        "generic_npc_masked_man": ShadowProfile(alpha=120, squash_ratio=0.25, y_offset=0, fade_height=250.0, ground_snap=12.0, scale_mult=1.0),
        "generic_npc_moonstone_keeper": ShadowProfile(alpha=120, squash_ratio=0.25, y_offset=0, fade_height=250.0, ground_snap=12.0, scale_mult=1.0),
        "evil_eye": ShadowProfile(alpha=110, squash_ratio=0.22, y_offset=0, fade_height=550.0, ground_snap=0.0, scale_mult=1.0),
        "wizard_npc": ShadowProfile(alpha=120, squash_ratio=0.25, y_offset=0, fade_height=250.0, ground_snap=12.0, scale_mult=1.0),
        "fire_wizard": ShadowProfile(alpha=125, squash_ratio=0.25, y_offset=0, fade_height=250.0, ground_snap=12.0, scale_mult=1.0),
        "green_monster": ShadowProfile(alpha=135, squash_ratio=0.28, y_offset=0, fade_height=300.0, ground_snap=15.0, scale_mult=1.05),
    }

    @classmethod
    def normalize_key(cls, key: str) -> str:
        """Normalize entity key to lowercase format."""
        k = key.lower().strip()
        if k.startswith("boss:"):
            k = k[5:]
        elif k.startswith("boss_"):
            k = k[5:]
        return k

    @classmethod
    def resolve_entity_key(cls, entity: Any) -> str:
        """Deduce configuration key from an entity instance."""
        # Explicit tag if present
        if hasattr(entity, "shadow_key"):
            return cls.normalize_key(entity.shadow_key)

        class_name = entity.__class__.__name__.lower()
        if class_name == "player":
            return "player"
        if class_name == "skeleton":
            return "skeleton"
        if class_name in ("enemy", "bat"):
            return "enemy"
        if class_name == "wizardnpc":
            return "wizard_npc"
        if class_name == "firewizard":
            return "fire_wizard"
        if class_name == "greenmonster":
            return "green_monster"

        # GenericNPC resolution by sprite directory / title
        if class_name == "genericnpc":
            if getattr(entity, "is_spirit_of_scythe", False):
                return "evil_eye"
            sprite_dir = getattr(entity, "sprite_dir", "") or ""
            folder = os.path.basename(sprite_dir.rstrip("/"))
            if folder.lower() in ("idle", "no bg", "with bg"):
                folder = os.path.basename(os.path.dirname(sprite_dir.rstrip("/")))
            key = f"generic_npc_{folder.lower()}"
            if key in cls._cache or key in cls.DEFAULTS:
                return key
            return "generic_npc_masked_man"

        return class_name

    @classmethod
    def _check_reload(cls) -> None:
        """Reload configuration if the file timestamp has changed."""
        if not os.path.exists(CONFIG_PATH):
            if not cls._cache:
                cls._cache = {k: ShadowProfile(**asdict(v)) for k, v in cls.DEFAULTS.items()}
            return

        try:
            mtime = os.path.getmtime(CONFIG_PATH)
            if mtime != cls._last_mtime:
                with open(CONFIG_PATH, "r") as f:
                    if fcntl:
                        fcntl.flock(f, fcntl.LOCK_SH)
                    data = json.load(f)
                loaded: dict[str, ShadowProfile] = {}
                for k, v in data.items():
                    if isinstance(v, dict):
                        loaded[cls.normalize_key(k)] = ShadowProfile.from_dict(v)
                cls._cache = loaded
                cls._last_mtime = mtime
        except Exception as e:
            print(f"[ShadowRegistry] Error loading {CONFIG_PATH}: {e}")
            if not cls._cache:
                cls._cache = {k: ShadowProfile(**asdict(v)) for k, v in cls.DEFAULTS.items()}

    @classmethod
    def get_profile(cls, entity_or_key: Any) -> ShadowProfile:
        """
        Retrieve shadow profile for an entity or key, falling back to 'default'.
        """
        cls._check_reload()
        if isinstance(entity_or_key, str):
            key = cls.normalize_key(entity_or_key)
        else:
            key = cls.resolve_entity_key(entity_or_key)

        profile = cls._cache.get(key)
        if profile is not None:
            return profile

        default_prof = cls.DEFAULTS.get(key)
        if default_prof is not None:
            return default_prof

        return cls._cache.get("default", cls.DEFAULTS["default"])

    @classmethod
    def save_profile(cls, key: str, profile: ShadowProfile) -> bool:
        """
        Save or update a shadow profile in game_data/shadow_config.json.
        """
        cls._check_reload()
        norm_key = cls.normalize_key(key)
        cls._cache[norm_key] = profile

        # Prepare full dictionary for disk serialization
        data = {k: v.to_dict() for k, v in cls._cache.items()}

        os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
        try:
            with open(CONFIG_PATH, "w") as f:
                if fcntl:
                    fcntl.flock(f, fcntl.LOCK_EX)
                json.dump(data, f, indent=4)
            cls._last_mtime = os.path.getmtime(CONFIG_PATH)
            return True
        except Exception as e:
            print(f"[ShadowRegistry] Failed to save {CONFIG_PATH}: {e}")
            return False

    @classmethod
    def get_all_profiles(cls) -> dict[str, ShadowProfile]:
        """Return all registered profiles."""
        cls._check_reload()
        return dict(cls._cache)
