import os
import json
import copy
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

    Network is only attempted ONCE per config key per game session.
    All repeat calls are served instantly from the in-memory session cache.
    """

    # In-memory session cache — populated on first fetch, reused for all subsequent calls.
    _session_cache: Dict[str, Dict[str, Any]] = {}
    # Track which keys already had their network attempt this session (avoids repeated 404 calls).
    _api_attempted: set = set()

    @classmethod
    def _deep_merge(cls, source: Dict[str, Any], destination: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively merges source into destination. Source keys take precedence."""
        for key, value in source.items():
            if isinstance(value, dict):
                node = destination.setdefault(key, {})
                if isinstance(node, dict):
                    cls._deep_merge(value, node)
                else:
                    destination[key] = value
            else:
                destination[key] = value
        return destination

    @classmethod
    def fetch_config(cls, config_type: str) -> Dict[str, Any]:
        """Loads configuration: session cache -> API (once) -> SQLite Cache -> Local JSON.

        Network is only hit ONCE per config key per session. After that, the merged
        result is served instantly from RAM to avoid per-spawn blocking lag.

        Args:
            config_type: Key identifier for config (e.g. 'player', 'boss_wizard')
        """
        # 0. Session cache hit — return immediately, zero I/O
        if config_type in cls._session_cache:
            return copy.deepcopy(cls._session_cache[config_type])

        config_data: Optional[Dict[str, Any]] = None

        # 1. Try API once per session only
        if config_type not in cls._api_attempted:
            cls._api_attempted.add(config_type)
            config_data = cls._fetch_from_api(config_type)
            if config_data:
                # Update local SQLite cache for offline play
                LocalCache.set_config(config_type, config_data)
            else:
                # 2. API failed — fall back to SQLite cache
                print(f"[CONFIG CLIENT] API fetch failed for '{config_type}'. Falling back to local cache...")
                config_data = LocalCache.get_config(config_type)
        else:
            # Already attempted this session — go straight to SQLite cache
            config_data = LocalCache.get_config(config_type)

        # 3. Load local JSON fallback (always applied on top to prioritize local edits)
        local_data = None
        try:
            local_data = cls._load_fallback(config_type)
        except Exception as e:
            print(f"[CONFIG CLIENT NOTE] Could not load fallback for '{config_type}': {e}")

        # Merge local_data on top of config_data
        merged: Dict[str, Any] = {}
        if config_data:
            merged = copy.deepcopy(config_data)
        if local_data:
            cls._deep_merge(local_data, merged)

        if not merged and local_data:
            merged = local_data

        # Store in session cache — all future calls skip network and disk entirely
        cls._session_cache[config_type] = copy.deepcopy(merged)

        return merged

    @classmethod
    def invalidate_cache(cls, config_type: Optional[str] = None) -> None:
        """Clear session cache so next fetch re-loads from source.

        Call this if config data changes at runtime (e.g. after saving in the audio editor).
        Pass a specific config_type to invalidate just that key, or None to clear all.
        """
        if config_type:
            cls._session_cache.pop(config_type, None)
            cls._api_attempted.discard(config_type)
        else:
            cls._session_cache.clear()
            cls._api_attempted.clear()

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
