import os
import json
import fcntl
import copy
from dataclasses import dataclass, asdict

CONFIG_PATH = "game_data/entity_dimensions.json"

@dataclass
class HitboxMargins:
    left: int
    right: int
    top: int
    bottom: int
    ground_offset: int = 0
    scale: float = 1.0

class HitboxRegistry:
    # Standard baseline default margins matching the verified stable hitbox reductions
    DEFAULTS = {
        "player": HitboxMargins(left=315, right=315, top=150, bottom=0, ground_offset=34, scale=3.0),
        "skeleton": HitboxMargins(left=65, right=65, top=20, bottom=0, ground_offset=127, scale=2.0),
        "enemy": HitboxMargins(left=80, right=80, top=100, bottom=100, ground_offset=0, scale=2.0),
        "wizard_npc": HitboxMargins(left=0, right=0, top=0, bottom=0, ground_offset=34, scale=2.0),
        "generic_npc_masked_man": HitboxMargins(left=0, right=0, top=0, bottom=0, ground_offset=34, scale=2.0),
        "generic_npc_goblin": HitboxMargins(left=0, right=0, top=0, bottom=0, ground_offset=34, scale=2.0),
    }

    _cached_config: dict[str, HitboxMargins] = {}
    _rollback_checkpoint: dict[str, HitboxMargins] = {}

    @classmethod
    def _load_config(cls) -> None:
        """Loads dimensions from JSON or populates with defaults if not present/file missing."""
        if not os.path.exists(CONFIG_PATH):
            cls._cached_config = dict(cls.DEFAULTS)
            cls.save_all()
            cls._rollback_checkpoint = copy.deepcopy(cls._cached_config)
            return

        try:
            with open(CONFIG_PATH, "r") as f:
                # Exclusive lock during reading to ensure integrity
                fcntl.flock(f, fcntl.LOCK_EX)
                data = json.load(f)
            
            # Map raw JSON data back to HitboxMargins objects, falling back to defaults if keys are missing
            cls._cached_config = {}
            for name, item in data.items():
                default_margins = cls.DEFAULTS.get(name) or (
                    HitboxMargins(0, 0, 0, 0, 34, scale=2.0) if name.startswith("generic_npc_") else HitboxMargins(0, 0, 0, 0, 0, scale=1.0)
                )
                cls._cached_config[name] = HitboxMargins(
                    left=item.get("left", default_margins.left),
                    right=item.get("right", default_margins.right),
                    top=item.get("top", default_margins.top),
                    bottom=item.get("bottom", default_margins.bottom),
                    ground_offset=item.get("ground_offset", default_margins.ground_offset),
                    scale=item.get("scale", default_margins.scale),
                )
            
            # Populate any missing default entries
            for name, default_margins in cls.DEFAULTS.items():
                if name not in cls._cached_config:
                    cls._cached_config[name] = default_margins
            
            cls._rollback_checkpoint = copy.deepcopy(cls._cached_config)
        except Exception as e:
            print(f"Error loading {CONFIG_PATH}: {e}. Falling back to default margins.")
            cls._cached_config = dict(cls.DEFAULTS)
            cls._rollback_checkpoint = copy.deepcopy(cls._cached_config)

    @classmethod
    def save_all(cls) -> None:
        """Persists the current cached registry configuration to JSON securely using an exclusive lock."""
        os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
        try:
            data = {name: asdict(margins) for name, margins in cls._cached_config.items()}
            with open(CONFIG_PATH, "w") as f:
                # Acquire exclusive lock for database safety/consistency
                fcntl.flock(f, fcntl.LOCK_EX)
                json.dump(data, f, indent=4)
        except Exception as e:
            print(f"Error saving hitbox configuration to {CONFIG_PATH}: {e}")

    @classmethod
    def begin_transaction(cls) -> None:
        """Creates a rollback checkpoint representing the last committed/saved state."""
        if not cls._cached_config:
            cls._load_config()
        cls._rollback_checkpoint = copy.deepcopy(cls._cached_config)

    @classmethod
    def commit_transaction(cls) -> None:
        """Saves the current config securely under an exclusive file lock and updates the checkpoint."""
        cls.save_all()
        cls._rollback_checkpoint = copy.deepcopy(cls._cached_config)

    @classmethod
    def rollback_transaction(cls) -> None:
        """Reverts the in-memory cache to the last rollback checkpoint."""
        if cls._rollback_checkpoint:
            cls._cached_config = copy.deepcopy(cls._rollback_checkpoint)
        else:
            cls._load_config()

    @classmethod
    def get_margins(cls, entity_name: str) -> HitboxMargins:
        """Retrieves the margins config for a given entity type."""
        if not cls._cached_config:
            cls._load_config()
        if entity_name in cls._cached_config:
            return cls._cached_config[entity_name]
        if entity_name in cls.DEFAULTS:
            return cls.DEFAULTS[entity_name]
        
        # Dynamic fallback for generic NPCs
        if entity_name.startswith("generic_npc_"):
            return HitboxMargins(0, 0, 0, 0, 34, scale=2.0)
        return HitboxMargins(0, 0, 0, 0, 0, scale=1.0)

    @classmethod
    def update_margins(cls, entity_name: str, margins: HitboxMargins) -> None:
        """Updates the configuration in memory. Must commit transaction to save to disk."""
        if not cls._cached_config:
            cls._load_config()
        cls._cached_config[entity_name] = margins
