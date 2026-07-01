import os
import json
import urllib.request
import urllib.error
from typing import Any, Dict, Optional

from .local_cache import LocalCache

# Default API URL. Can be overridden via environment variable.
API_BASE_URL = os.environ.get("PIXEL_RUNNER_API_URL", "https://pixel-runner-wheat.vercel.app")

LOCAL_FILE_MAP = {
    "player": "game_data/player_config.json",
    "boss_wizard": "game_data/boss_wizard_config.json",
    "boss_skeleton": "game_data/boss_skeleton_config.json",
    "enemy_goblin": "game_data/enemy_goblin_config.json",
    "enemy_blood_zombie": "game_data/enemy_blood_zombie_config.json",
    "enemy_green_monster": "game_data/enemy_green_monster_config.json",
    "enemy_skeleton_zombie": "game_data/enemy_skeleton_zombie_config.json",
    "enemy_skeleton_minion": "game_data/enemy_skeleton_minion_config.json",
    "entity_dimensions": "game_data/entity_dimensions.json"
}

class ConfigClient:
    """Config loading client that coordinates cloud fetching, local cache lookups,
    and local JSON fallbacks.
    """

    @classmethod
    def fetch_config(cls, config_type: str) -> Dict[str, Any]:
        """Loads configuration from API -> SQLite Cache -> Local JSON fallback.
        
        Args:
            config_type: Key identifier for config (e.g. 'player', 'boss_wizard')
        """
        # 1. Try to fetch from server API
        config_data = cls._fetch_from_api(config_type)
        if config_data:
            # Update local SQLite cache for offline play
            LocalCache.set_config(config_type, config_data)
            return config_data

        # 2. Server failed or offline. Fall back to local SQLite cache
        print(f"[CONFIG CLIENT] API fetch failed for '{config_type}'. Falling back to local cache...")
        cached_data = LocalCache.get_config(config_type)
        if cached_data:
            return cached_data

        # 3. Cache missed or corrupt. Fall back to local JSON file
        print(f"[CONFIG CLIENT] Local cache missed for '{config_type}'. Falling back to raw JSON file...")
        return cls._load_fallback(config_type)

    @classmethod
    def _fetch_from_api(cls, config_type: str) -> Optional[Dict[str, Any]]:
        """HTTP GET to API server with 3 second timeout."""
        url = f"{API_BASE_URL.rstrip('/')}/api/configs/{config_type}"
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "Pixel-Runner Game Client"}
            )
            with urllib.request.urlopen(req, timeout=3.0) as response:
                if response.status == 200:
                    raw_data = response.read().decode("utf-8")
                    return json.loads(raw_data)
        except urllib.error.URLError as e:
            print(f"[CONFIG CLIENT ERROR] Connection error fetching {config_type}: {e}")
        except json.JSONDecodeError as e:
            print(f"[CONFIG CLIENT ERROR] Failed to parse config JSON for {config_type}: {e}")
        except Exception as e:
            print(f"[CONFIG CLIENT ERROR] Unexpected error fetching {config_type}: {e}")
        return None

    @classmethod
    def _load_fallback(cls, config_type: str) -> Dict[str, Any]:
        """Read configuration from raw JSON file in game_data/ folder."""
        file_path = LOCAL_FILE_MAP.get(config_type)
        if not file_path:
            raise ValueError(f"Unknown config type: {config_type}")
            
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Fallback file not found: {file_path}")

        try:
            with open(file_path, "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"[CONFIG CLIENT ERROR] Failed to read fallback file {file_path}: {e}")
            raise e
