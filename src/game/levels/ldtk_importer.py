"""
LDtk Importer — Parses LDtk level projects (.ldtk) and converts them into Pixel-Runner level configurations.
"""

from __future__ import annotations

import json
import os
from typing import Dict, Any, List, Optional


class LDtkImporter:
    """Parses LDtk project JSON format and maps levels to Pixel-Runner game schema."""

    @staticmethod
    def load_ldtk_file(ldtk_path: str) -> Dict[str, Any]:
        """Loads and parses an .ldtk project file."""
        if not os.path.exists(ldtk_path):
            raise FileNotFoundError(f"LDtk file not found: {ldtk_path}")
        with open(ldtk_path, "r", encoding="utf-8") as f:
            return json.load(f)

    @staticmethod
    def convert_ldtk_to_level_config(ldtk_data: Dict[str, Any], level_index: int = 0) -> Dict[str, Any]:
        """Converts an LDtk project dataset to Pixel-Runner's level JSON schema.
        
        Args:
            ldtk_data: Parsed LDtk JSON dictionary.
            level_index: Index of the level within the LDtk levels array.
            
        Returns:
            Dictionary matching Pixel-Runner level_*.json format.
        """
        levels = ldtk_data.get("levels", [])
        if not levels or level_index >= len(levels):
            raise ValueError(f"No level found at index {level_index} in LDtk file.")

        raw_level = levels[level_index]
        
        # 1. Base Level Metadata
        level_config: Dict[str, Any] = {
            "level_name": raw_level.get("identifier", "Level 1"),
            "level_end_distance": raw_level.get("pxWid", 36000),
            "spawn_rate_min": 5000,
            "spawn_rate_max": 15000,
            "environment": {
                "bg_music_track": "game_loop",
                "ground_y": 686,
                "sky": {
                    "layers": [
                        {"path": "assets/graphics/Clouds 3/1.png", "speed": 0},
                        {"path": "assets/graphics/Clouds 3/2.png", "speed": 0},
                        {"path": "assets/graphics/Clouds 3/3.png", "speed": 20},
                        {"path": "assets/graphics/Clouds 3/4.png", "speed": 40}
                    ]
                },
                "parallax_layers": []
            },
            "soul_harvest": {
                "starting_souls": 8500,
                "target_souls": 10000,
                "soul_values": {
                    "skeleton_minion": 5,
                    "skeleton_zombie": 8,
                    "goblin": 3,
                    "elite_boss": 150,
                    "mini_boss": 300,
                    "final_boss_remaining": True
                }
            },
            "spawn_zones": [],
            "world_events": []
        }

        # Overwrite metadata from LDtk level custom fields if present
        for field in raw_level.get("fieldInstances", []):
            fname = field.get("__identifier__")
            fval = field.get("__value__")
            if fname and fval is not None:
                if fname == "level_name":
                    level_config["level_name"] = fval
                elif fname == "level_end_distance":
                    level_config["level_end_distance"] = fval
                elif fname == "spawn_rate_min":
                    level_config["spawn_rate_min"] = fval
                elif fname == "spawn_rate_max":
                    level_config["spawn_rate_max"] = fval

        # Check background image relative path in LDtk level
        bg_rel = raw_level.get("bgRelPath")
        if bg_rel:
            level_config["environment"]["parallax_layers"].append({
                "path": bg_rel,
                "scroll_ratio": 0.1,
                "repeat_x": True
            })
        else:
            level_config["environment"]["parallax_layers"].append({
                "path": "assets/graphics/background images/new_bg_images/bg_image.png",
                "scroll_ratio": 0.1,
                "repeat_x": True
            })

        # 2. Iterate through Layer Instances to process Entities and Zones
        layer_instances = raw_level.get("layerInstances", [])
        event_id_counter = 10

        for layer in layer_instances:
            layer_name = layer.get("__identifier__", "")
            
            # Entity Layer
            if layer.get("__type__") == "Entities" or "Entities" in layer_name:
                for entity in layer.get("entityInstances", []):
                    entity_type = entity.get("__identifier__")
                    pos_x = entity.get("px", [0, 0])[0]
                    pos_y = entity.get("px", [0, 0])[1]

                    fields = {f.get("__identifier__"): f.get("__value__") for f in entity.get("fieldInstances", [])}

                    if entity_type == "NPC" or entity_type == "GenericNPC":
                        npc_params = {
                            "npc_type": fields.get("npc_type", "generic"),
                            "title": fields.get("title", "NPC"),
                            "text": fields.get("text", "Hello adventurer!"),
                            "radius": fields.get("radius", 180),
                            "sprite_dir": fields.get("sprite_dir", "assets/graphics/Necromancer/Idle"),
                            "scale": fields.get("scale", 3.38),
                        }
                        if fields.get("walk_sprite_dir"):
                            npc_params["walk_sprite_dir"] = fields["walk_sprite_dir"]
                        if fields.get("spawn_sprite_dir"):
                            npc_params["spawn_sprite_dir"] = fields["spawn_sprite_dir"]
                        if fields.get("death_sprite_dir"):
                            npc_params["death_sprite_dir"] = fields["death_sprite_dir"]
                        if fields.get("play_death_on_interact") is not None:
                            npc_params["play_death_on_interact"] = fields["play_death_on_interact"]
                        if fields.get("is_intro_npc") is not None:
                            npc_params["is_intro_npc"] = fields["is_intro_npc"]

                        level_config["world_events"].append({
                            "id": event_id_counter,
                            "distance": pos_x,
                            "type": "npc",
                            "params": npc_params
                        })
                        event_id_counter += 1

                    elif entity_type == "SpawnZone":
                        level_config["spawn_zones"].append({
                            "min_dist": pos_x,
                            "max_dist": pos_x + entity.get("width", 5000),
                            "max_skeletons": fields.get("max_skeletons", 3),
                            "delay": fields.get("delay", 4500),
                            "tier": fields.get("tier", "minion"),
                            "sprite_root": fields.get("sprite_root", "assets/skeleton")
                        })

                    elif entity_type in ("BossTrigger", "WorldEvent"):
                        level_config["world_events"].append({
                            "id": event_id_counter,
                            "distance": pos_x,
                            "type": fields.get("event_type", "boss_arena"),
                            "params": fields.get("params", {})
                        })
                        event_id_counter += 1

        return level_config

    @classmethod
    def import_and_save(cls, ldtk_path: str, output_json_path: str, level_index: int = 0) -> Dict[str, Any]:
        """Imports an .ldtk file and saves the converted JSON to output_json_path."""
        ldtk_data = cls.load_ldtk_file(ldtk_path)
        level_cfg = cls.convert_ldtk_to_level_config(ldtk_data, level_index=level_index)

        os.makedirs(os.path.dirname(os.path.abspath(output_json_path)), exist_ok=True)
        with open(output_json_path, "w", encoding="utf-8") as f:
            json.dump(level_cfg, f, indent=4)

        return level_cfg
