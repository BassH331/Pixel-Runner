"""
src/game/systems/popup_scene_manager.py

PopupSceneManager — Unified Scene & Entity Pop-up Notification Engine.

Loads, manages, and hot-reloads data-driven pop-up notifications linked to:
1. In-game distances / milestones (e.g., Awakening @ 0m, Demon Time @ 2600m, Extraction @ 36000m).
2. Entity encounters (e.g., Grimoire @ entity 10, Blood Zombie @ entity 14, Moonstone Keeper @ entity 13).
3. Storyline / gameplay flags (e.g., first_encounter, first_kill, soul_quota).

Provides atomic persistent configuration saves and live sync with SideNotification.
"""

from __future__ import annotations

import json
import os
import time
from typing import Dict, Any, List, Optional

from src.game.utils.atomic_save import atomic_write_json


DEFAULT_SCENE_POPUPS_PATH = "game_data/scene_popups_config.json"


class PopupSceneManager:
    """
    Central manager for scene and entity pop-up notifications.
    Supports distance, entity ID, and flag based retrieval with hot-reloading.
    """

    _instance: Optional[PopupSceneManager] = None

    @classmethod
    def get_instance(cls, config_path: str = DEFAULT_SCENE_POPUPS_PATH) -> PopupSceneManager:
        """Get or initialize the singleton instance."""
        if cls._instance is None:
            cls._instance = cls(config_path=config_path)
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Reset singleton instance (useful for testing)."""
        cls._instance = None

    def __init__(self, config_path: str = DEFAULT_SCENE_POPUPS_PATH) -> None:
        self.config_path = config_path
        self._last_mtime: float = 0.0
        self._scenes: List[Dict[str, Any]] = []
        self._scenes_by_id: Dict[str, Dict[str, Any]] = {}
        self._scenes_by_entity: Dict[int, Dict[str, Any]] = {}
        self._scenes_by_flag: Dict[str, Dict[str, Any]] = {}
        self.load_config()

    def load_config(self, config_path: Optional[str] = None) -> bool:
        """Load pop-up scenes from disk safely."""
        if config_path is not None:
            self.config_path = config_path
        if not os.path.exists(self.config_path):
            self._scenes = []
            self._rebuild_indices()
            return False

        try:
            mtime = os.path.getmtime(self.config_path)
            with open(self.config_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            scenes = data.get("scenes", [])
            if isinstance(scenes, list):
                self._scenes = scenes
                self._last_mtime = mtime
                self._rebuild_indices()
                return True
        except Exception as e:
            print(f"[PopupSceneManager] Error loading {self.config_path}: {e}")

        return False

    def check_reload(self) -> bool:
        """Check if config file changed on disk and reload if necessary."""
        if not os.path.exists(self.config_path):
            return False
        try:
            mtime = os.path.getmtime(self.config_path)
            if mtime > self._last_mtime:
                return self.load_config()
        except OSError:
            pass
        return False

    def _rebuild_indices(self) -> None:
        """Index scenes by ID, entity_id, and flag for O(1) lookups."""
        self._scenes_by_id.clear()
        self._scenes_by_entity.clear()
        self._scenes_by_flag.clear()

        for scene in self._scenes:
            sid = scene.get("id")
            if sid:
                self._scenes_by_id[sid] = scene

            eid = scene.get("entity_id")
            ttype = scene.get("trigger_type")
            if eid is not None:
                # Only register in _scenes_by_entity when trigger_type == "entity"
                # or when trigger_type is not a non-entity trigger and entity_id is an integer
                if ttype == "entity" or (ttype not in ("flag", "distance") and isinstance(eid, int)):
                    try:
                        int_eid = int(eid)
                        if int_eid not in self._scenes_by_entity or ttype == "entity":
                            self._scenes_by_entity[int_eid] = scene
                    except (ValueError, TypeError):
                        pass

            flag = scene.get("flag")
            if flag:
                self._scenes_by_flag[flag] = scene

    def get_all_popups(self) -> List[Dict[str, Any]]:
        """Return a copy of all loaded pop-up scenes."""
        self.check_reload()
        return [dict(s) for s in self._scenes]

    def get_popup(self, scene_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve pop-up configuration by unique scene ID."""
        self.check_reload()
        scene = self._scenes_by_id.get(scene_id)
        return dict(scene) if scene else None

    def get_popup_by_entity(self, entity_id: int) -> Optional[Dict[str, Any]]:
        """Retrieve pop-up configuration triggered by entity interaction."""
        self.check_reload()
        scene = self._scenes_by_entity.get(entity_id)
        return dict(scene) if scene else None

    def get_popup_by_flag(self, flag: str) -> Optional[Dict[str, Any]]:
        """Retrieve pop-up configuration triggered by game event flag."""
        self.check_reload()
        scene = self._scenes_by_flag.get(flag)
        return dict(scene) if scene else None

    def get_popups_by_distance(self, distance: float, tolerance: float = 30.0) -> List[Dict[str, Any]]:
        """Retrieve all pop-up scenes near the given distance."""
        self.check_reload()
        if distance is None:
            return []
        matches: List[Dict[str, Any]] = []
        for s in self._scenes:
            if s.get("trigger_type") == "distance":
                target_dist = s.get("distance")
                if target_dist is None:
                    continue
                try:
                    target_dist_f = float(target_dist)
                    if abs(distance - target_dist_f) <= tolerance:
                        matches.append(dict(s))
                except (ValueError, TypeError):
                    continue
        return matches

    def update_popup(self, scene_id: str, new_fields: Dict[str, Any]) -> bool:
        """Update fields of an existing scene in memory."""
        self.check_reload()
        for i, s in enumerate(self._scenes):
            if s.get("id") == scene_id:
                self._scenes[i].update(new_fields)
                self._rebuild_indices()
                return True
        return False

    def set_popup_enabled(self, scene_id: str, enabled: bool) -> bool:
        """Toggle an individual pop-up on or off."""
        return self.update_popup(scene_id, {"enabled": bool(enabled)})

    def add_popup(self, scene: Dict[str, Any]) -> bool:
        """Add a new scene pop-up configuration."""
        self.check_reload()
        sid = scene.get("id")
        if not sid:
            sid = f"event_custom_{int(time.time())}"
            scene["id"] = sid

        for i, s in enumerate(self._scenes):
            if s.get("id") == sid:
                self._scenes[i] = scene
                self._rebuild_indices()
                return True

        self._scenes.append(scene)
        self._rebuild_indices()
        return True

    def delete_popup(self, scene_id: str) -> bool:
        """Remove a scene pop-up configuration by ID."""
        self.check_reload()
        for i, s in enumerate(self._scenes):
            if s.get("id") == scene_id:
                del self._scenes[i]
                self._rebuild_indices()
                return True
        return False

    def set_all_scenes(self, scenes: List[Dict[str, Any]]) -> None:
        """Replace all scenes in memory and rebuild indices."""
        self._scenes = [dict(s) for s in scenes]
        self._rebuild_indices()

    def save_config(self, target_path: Optional[str] = None) -> bool:
        """Atomically persist pop-up scenes configuration to disk, preserving external keys."""
        path = target_path or self.config_path
        disk_data: Dict[str, Any] = {}
        if os.path.exists(path) and os.path.getsize(path) > 0:
            try:
                with open(path, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    if isinstance(loaded, dict):
                        disk_data = loaded
            except Exception:
                disk_data = {}

        payload = dict(disk_data)
        if "version" not in payload:
            payload["version"] = "1.0"
        if "description" not in payload:
            payload["description"] = "Canonical Scene and Entity Pop-up Notification Configuration for Pixel-Runner"
        payload["scenes"] = self._scenes

        success = atomic_write_json(path, payload, indent=2, backup=True, max_backups=5)
        if success and path == self.config_path and os.path.exists(path):
            self._last_mtime = os.path.getmtime(path)
        return success
