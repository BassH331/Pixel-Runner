import json
import os
import time
import logging
from typing import Dict, List, Optional, Any
from v3x_zulfiqar_gideon.audio_manager import AudioManager

logger = logging.getLogger("CombatCollisionLogger")

# Path to master audio config (collision_map section)
_MASTER_AUDIO_CONFIG_PATH = "game_data/master_audio_config.json"

# Hardcoded fallback — used only when config has no collision_map section
_DEFAULT_COLLISION_MAP: Dict[str, str] = {
    "skeleton": "collision_player_skeleton",
    "player": "collision_player_skeleton",
    "zombie": "collision_player_zombie",
    "bloo_zombie": "collision_player_zombie",
    "boss": "collision_player_boss",
    "fire_wizard": "collision_player_boss",
    "boss_wizard": "collision_player_boss",
    "bat": "collision_player_bat",
    "green_monster": "collision_player_green_monster",
    "defend": "collision_player_defend",
}


def _load_collision_map_from_config() -> Dict[str, str]:
    """Load the collision_map from master_audio_config.json.

    Returns the config-driven map if present, otherwise the hardcoded default.
    """
    try:
        if os.path.exists(_MASTER_AUDIO_CONFIG_PATH):
            with open(_MASTER_AUDIO_CONFIG_PATH, "r") as f:
                data = json.load(f)
            collision_map = data.get("collision_map")
            if isinstance(collision_map, dict) and collision_map:
                return dict(collision_map)
    except Exception as err:
        logger.warning(
            f"[CombatCollisionLogger] Could not load collision_map from config: {err}"
        )
    return dict(_DEFAULT_COLLISION_MAP)


class CombatCollisionLogger:
    """
    Combat encounter logger and collision sound dispatcher.
    Tracks player and enemy combat collisions by entity name/ID and maps targeted collision audio.

    Collision mappings are loaded from ``master_audio_config.json`` → ``collision_map``
    section so they can be edited through the Audio Mixer Editor.
    """
    _instance: Optional["CombatCollisionLogger"] = None

    def __init__(self, audio_manager: Optional[AudioManager] = None):
        self.audio_manager = audio_manager
        self.encounter_logs: List[Dict[str, Any]] = []
        self._max_logs: int = 100

        # Load collision sound map from config (falls back to hardcoded default)
        self.collision_sound_map: Dict[str, str] = _load_collision_map_from_config()

    def reload_collision_map(self) -> None:
        """Re-read collision_map from disk (call after the editor saves changes)."""
        self.collision_sound_map = _load_collision_map_from_config()

    @classmethod
    def get_instance(cls, audio_manager: Optional[AudioManager] = None) -> "CombatCollisionLogger":
        if cls._instance is None:
            cls._instance = CombatCollisionLogger(audio_manager=audio_manager)
        elif audio_manager is not None:
            cls._instance.audio_manager = audio_manager
        return cls._instance

    def log_collision(
        self,
        attacker: str = "player",
        defender: str = "skeleton",
        defender_id: str = "enemy_1",
        action: str = "hit",
        defender_state: str = "alive",
        custom_sound: Optional[str] = None
    ) -> str:
        """
        Log entity collision encounter and trigger targeted collision audio sound.
        
        Example: log_collision(attacker="player", defender="skeleton", defender_id="skel_01", defender_state="alive")
        """
        sound_key = custom_sound

        if not sound_key:
            if action == "defend" or defender_state == "defending":
                sound_key = "collision_player_defend"
            else:
                def_key = defender.lower().strip()
                att_key = attacker.lower().strip()
                sound_key = (
                    self.collision_sound_map.get(def_key)
                    or self.collision_sound_map.get(att_key)
                    or "collision_player_skeleton"
                )

        # Play sound via audio manager if attached
        if self.audio_manager:
            try:
                self.audio_manager.play_sound(sound_key)
            except Exception as err:
                logger.warning(f"[CombatCollisionLogger] Could not play collision sound '{sound_key}': {err}")

        # Log encounter record
        log_entry = {
            "timestamp": time.time(),
            "attacker": attacker,
            "defender": defender,
            "defender_id": defender_id,
            "action": action,
            "defender_state": defender_state,
            "sound_played": sound_key
        }

        self.encounter_logs.append(log_entry)
        if len(self.encounter_logs) > self._max_logs:
            self.encounter_logs.pop(0)

        logger.info(
            f"[CombatCollision] {attacker} -> {defender} [{defender_id}] | State: {defender_state} | Audio: '{sound_key}'"
        )
        return sound_key

    def get_encounter_logs(self) -> List[Dict[str, Any]]:
        """Return all logged combat encounter collisions."""
        return list(self.encounter_logs)

    def clear_logs(self) -> None:
        """Clear collision encounter log history."""
        self.encounter_logs.clear()
