import os
import json
from dataclasses import dataclass, asdict

CONFIG_PATH = "game_data/entity_dimensions.json"

@dataclass
class HitboxMargins:
    left: int
    right: int
    top: int
    bottom: int
    ground_offset: int = 0

class HitboxRegistry:
    # Standard baseline default margins matching the verified stable hitbox reductions
    DEFAULTS = {
        "player": HitboxMargins(left=315, right=315, top=150, bottom=0, ground_offset=34),
        "skeleton": HitboxMargins(left=65, right=65, top=20, bottom=0, ground_offset=127),
        "enemy": HitboxMargins(left=80, right=80, top=100, bottom=100, ground_offset=0),
        "wizard_npc": HitboxMargins(left=0, right=0, top=0, bottom=0, ground_offset=34),
        "generic_npc": HitboxMargins(left=0, right=0, top=0, bottom=0, ground_offset=34),
    }

    _cached_config: dict[str, HitboxMargins] = {}

    @classmethod
    def _load_config(cls) -> None:
        """Loads dimensions from JSON or populates with defaults if not present/file missing."""
        if not os.path.exists(CONFIG_PATH):
            cls._cached_config = dict(cls.DEFAULTS)
            cls.save_all()
            return

        try:
            with open(CONFIG_PATH, "r") as f:
                data = json.load(f)
            
            # Map raw JSON data back to HitboxMargins objects, falling back to defaults if keys are missing
            cls._cached_config = {}
            for name, default_margins in cls.DEFAULTS.items():
                if name in data:
                    item = data[name]
                    cls._cached_config[name] = HitboxMargins(
                        left=item.get("left", default_margins.left),
                        right=item.get("right", default_margins.right),
                        top=item.get("top", default_margins.top),
                        bottom=item.get("bottom", default_margins.bottom),
                        ground_offset=item.get("ground_offset", default_margins.ground_offset),
                    )
                else:
                    cls._cached_config[name] = default_margins
        except Exception as e:
            print(f"Error loading {CONFIG_PATH}: {e}. Falling back to default margins.")
            cls._cached_config = dict(cls.DEFAULTS)

    @classmethod
    def save_all(cls) -> None:
        """Persists the current cached registry configuration to JSON."""
        os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
        try:
            data = {name: asdict(margins) for name, margins in cls._cached_config.items()}
            with open(CONFIG_PATH, "w") as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            print(f"Error saving hitbox configuration to {CONFIG_PATH}: {e}")

    @classmethod
    def get_margins(cls, entity_name: str) -> HitboxMargins:
        """Retrieves the margins config for a given entity type."""
        if not cls._cached_config:
            cls._load_config()
        return cls._cached_config.get(entity_name, cls.DEFAULTS.get(entity_name, HitboxMargins(0, 0, 0, 0)))

    @classmethod
    def update_margins(cls, entity_name: str, margins: HitboxMargins) -> None:
        """Updates and immediately persists the configuration for an entity type."""
        if not cls._cached_config:
            cls._load_config()
        cls._cached_config[entity_name] = margins
        cls.save_all()
