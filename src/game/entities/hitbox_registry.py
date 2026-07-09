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
        """Loads dimensions from ConfigClient, falling back to local JSON or defaults."""
        data = None
        try:
            from ..services import ConfigClient
            data = ConfigClient.fetch_config("entity_dimensions")
        except Exception as e:
            print(f"[CACHE NOTE] Could not fetch hitbox config from client services: {e}")

        if not data:
            if not os.path.exists(CONFIG_PATH):
                cls._cached_config = dict(cls.DEFAULTS)
                cls.save_all()
                cls._rollback_checkpoint = copy.deepcopy(cls._cached_config)
                return

            try:
                with open(CONFIG_PATH, "r") as f:
                    fcntl.flock(f, fcntl.LOCK_EX)
                    data = json.load(f)
            except Exception as e:
                print(f"Error loading local {CONFIG_PATH}: {e}. Falling back to default margins.")
                cls._cached_config = dict(cls.DEFAULTS)
                cls._rollback_checkpoint = copy.deepcopy(cls._cached_config)
                return

    @classmethod
    def _normalize_key(cls, key: str) -> str:
        name_lower = key.lower()
        if name_lower == "boss_gatekeeper":
            return "boss:green_monster"
        if name_lower.startswith("boss_") and name_lower != "boss_":
            return "boss:" + name_lower[5:]
        return name_lower

    @classmethod
    def _load_config(cls) -> None:
        """Loads dimensions from ConfigClient, falling back to local JSON or defaults."""
        local_data = {}
        if os.path.exists(CONFIG_PATH):
            try:
                with open(CONFIG_PATH, "r") as f:
                    fcntl.flock(f, fcntl.LOCK_EX)
                    local_data = json.load(f)
            except Exception as e:
                print(f"Error loading local {CONFIG_PATH}: {e}")

        remote_data = None
        try:
            from ..services import ConfigClient
            remote_data = ConfigClient.fetch_config("entity_dimensions")
        except Exception as e:
            print(f"[CACHE NOTE] Could not fetch hitbox config from client services: {e}")

        data = dict(remote_data) if remote_data else {}
        data.update(local_data)

        if not data:
            cls._cached_config = dict(cls.DEFAULTS)
            cls.save_all()
            cls._rollback_checkpoint = copy.deepcopy(cls._cached_config)
            return

        try:
            # Map raw JSON data back to HitboxMargins objects, falling back to defaults if keys are missing
            cls._cached_config = {}
            for name, item in data.items():
                norm_name = cls._normalize_key(name)
                default_margins = cls.DEFAULTS.get(norm_name) or (
                    HitboxMargins(0, 0, 0, 0, 34, scale=2.0) if norm_name.startswith("generic_npc_") else HitboxMargins(0, 0, 0, 0, 0, scale=1.0)
                )
                cls._cached_config[norm_name] = HitboxMargins(
                    left=item.get("left", default_margins.left),
                    right=item.get("right", default_margins.right),
                    top=item.get("top", default_margins.top),
                    bottom=item.get("bottom", default_margins.bottom),
                    ground_offset=item.get("ground_offset", default_margins.ground_offset),
                    scale=item.get("scale", default_margins.scale),
                )
            
            # Populate any missing default entries
            for name, default_margins in cls.DEFAULTS.items():
                norm_name = cls._normalize_key(name)
                if norm_name not in cls._cached_config:
                    cls._cached_config[norm_name] = default_margins
            
            cls._rollback_checkpoint = copy.deepcopy(cls._cached_config)
        except Exception as e:
            print(f"Error parsing hitbox dimensions: {e}. Falling back to default margins.")
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
            
        name_lower = cls._normalize_key(entity_name)
        
        # 1. Direct case-insensitive match in cached config
        for k, v in cls._cached_config.items():
            if cls._normalize_key(k) == name_lower:
                return v
                
        # 2. Case-insensitive match for skeleton name fallback to generic NPC
        if name_lower.startswith("skeleton_"):
            base_name = name_lower.replace("skeleton_", "", 1)
            alt_key = f"generic_npc_{base_name}"
            for k, v in cls._cached_config.items():
                if cls._normalize_key(k) == alt_key:
                    return v
                    
        # 3. Direct case-insensitive match in Defaults
        for k, v in cls.DEFAULTS.items():
            if cls._normalize_key(k) == name_lower:
                return v
        
        # Dynamic fallback for generic NPCs
        if name_lower.startswith("generic_npc_"):
            return HitboxMargins(0, 0, 0, 0, 34, scale=2.0)
        if name_lower.startswith("boss:") or name_lower == "boss":
            skeleton_margins = cls.DEFAULTS.get("skeleton") or HitboxMargins(65, 65, 20, 0, 127, scale=2.0)
            for k, v in cls._cached_config.items():
                if k.lower() == "skeleton":
                    skeleton_margins = v
                    break
            return copy.deepcopy(skeleton_margins)
        return HitboxMargins(0, 0, 0, 0, 0, scale=1.0)

    @classmethod
    def has_custom_margins(cls, entity_name: str) -> bool:
        """Checks if the database JSON file contains an entry for entity_name."""
        if not os.path.exists(CONFIG_PATH):
            return False
        try:
            with open(CONFIG_PATH, "r") as f:
                data = json.load(f)
            name_lower = cls._normalize_key(entity_name)
            
            # Direct case-insensitive match
            if any(cls._normalize_key(k) == name_lower for k in data.keys()):
                return True
                
            # Fallback mapping check for skeleton
            if name_lower.startswith("skeleton_"):
                base_name = name_lower.replace("skeleton_", "", 1)
                alt_key = f"generic_npc_{base_name}"
                if any(cls._normalize_key(k) == alt_key for k in data.keys()):
                    return True
                    
            return False
        except Exception:
            return False

    @classmethod
    def update_margins(cls, entity_name: str, margins: HitboxMargins) -> None:
        """Updates the configuration in memory. Must commit transaction to save to disk."""
        if not cls._cached_config:
            cls._load_config()
        norm_name = cls._normalize_key(entity_name)
        cls._cached_config[norm_name] = margins

    @classmethod
    def sync_with_level_config(cls, level_data: dict | None) -> None:
        """Scan level_data world_events for 'npc' and 'boss' types. If a scale is defined,
        ensure that it matches what's in the registry. If not, update the registry's scale
        to match it, and save the registry.
        """
        if level_data is None:
            return

        if not cls._cached_config:
            cls._load_config()

        modified = False
        events = level_data.get("world_events", [])
        for ev in events:
            etype = ev.get("type")
            if etype not in ("npc", "boss"):
                continue
            params = ev.get("params", {})
            if "scale" not in params:
                continue
            try:
                json_scale = float(params["scale"])
            except (ValueError, TypeError):
                continue

            # Determine registry key
            if etype == "npc":
                ntype = params.get("npc_type", "generic")
                if ntype == "wizard":
                    reg_key = "wizard_npc"
                else:
                    sprite_dir = params.get("sprite_dir", "")
                    folder_name = os.path.basename(sprite_dir.rstrip("/"))
                    if folder_name.lower() == "idle":
                        parent_dir = os.path.dirname(sprite_dir.rstrip("/"))
                        folder_name = os.path.basename(parent_dir)
                    reg_key = f"generic_npc_{folder_name.lower()}"
            else:  # boss
                sprite_dir = params.get("sprite_dir", "")
                if sprite_dir:
                    folder_name = os.path.basename(sprite_dir.rstrip("/"))
                    if folder_name.lower() in ("idle", "walk", "run", "fly", "1atk", "2atk", "hurt", "death"):
                        parent_dir = os.path.dirname(sprite_dir.rstrip("/"))
                        folder_name = os.path.basename(parent_dir)
                    reg_key = f"boss:{folder_name.lower()}"
                else:
                    reg_key = "boss"

            # Check if key already exists (case-insensitive)
            existing_key = None
            existing_margins = None
            for k, v in cls._cached_config.items():
                if k.lower() == reg_key.lower():
                    existing_key = k
                    existing_margins = v
                    break

            if existing_margins and existing_key:
                if abs(existing_margins.scale - json_scale) > 0.01:
                    existing_margins.scale = json_scale
                    modified = True
            else:
                # Add default entry with specified scale
                default_margins = cls.DEFAULTS.get(reg_key)
                if not default_margins:
                    # Look up by case-insensitive key in DEFAULTS
                    for dk, dv in cls.DEFAULTS.items():
                        if dk.lower() == reg_key.lower():
                            default_margins = dv
                            break

                if not default_margins:
                    if reg_key.lower().startswith("generic_npc_"):
                        default_margins = HitboxMargins(0, 0, 0, 0, 34, scale=json_scale)
                    elif reg_key.lower().startswith("boss:") or reg_key.lower() == "boss":
                        skeleton = cls.get_margins("skeleton")
                        default_margins = HitboxMargins(
                            left=skeleton.left,
                            right=skeleton.right,
                            top=skeleton.top,
                            bottom=skeleton.bottom,
                            ground_offset=skeleton.ground_offset,
                            scale=json_scale
                        )
                    else:
                        default_margins = HitboxMargins(0, 0, 0, 0, 0, scale=json_scale)
                else:
                    default_margins = copy.deepcopy(default_margins)
                    default_margins.scale = json_scale

                cls._cached_config[reg_key] = default_margins
                modified = True

        if modified:
            cls.save_all()
