"""
WaveManager — Data-driven enemy wave spawner and minion zone manager.
"""

from __future__ import annotations

import random
from typing import Any, Callable, Dict, List, Optional
import pygame as pg


_DEFAULT_SPAWN_ZONES: list[dict] = [
    {"min_dist": 0,    "max_dist": 1000,        "max_skeletons": 2, "delay": 6000},
    {"min_dist": 1000, "max_dist": 3000,        "max_skeletons": 3, "delay": 4000},
    {"min_dist": 3000, "max_dist": 6000,        "max_skeletons": 5, "delay": 3000},
    {"min_dist": 6000, "max_dist": float("inf"), "max_skeletons": 6, "delay": 2000},
]


class WaveManager:
    """Manages distance-scaled enemy spawn zones and wave timers."""

    def __init__(self) -> None:
        self.spawn_zones: list[dict] = list(_DEFAULT_SPAWN_ZONES)
        self.bat_min_delay: int = 5000
        self.bat_max_delay: int = 15000
        self.bat_min_count: int = 3
        self.bat_max_count: int = 5
        self.next_bat_group_time: int = 0
        self.intro_npc_done: bool = True

    def load_level_config(self, level_data: dict) -> None:
        """Load spawn zones and bat spawn parameters from level JSON."""
        self.bat_min_delay = level_data.get("spawn_rate_min", 5000)
        self.bat_max_delay = level_data.get("spawn_rate_max", 15000)

        json_zones = level_data.get("spawn_zones", None)
        if json_zones:
            for zone in json_zones:
                if zone.get("max_dist", 0) >= 99999:
                    zone["max_dist"] = float("inf")
            self.spawn_zones = json_zones
        else:
            self.spawn_zones = list(_DEFAULT_SPAWN_ZONES)

        bat_cfg = level_data.get("bat_spawn", {})
        self.bat_min_count = bat_cfg.get("min_count", 3)
        self.bat_max_count = bat_cfg.get("max_count", 5)

    def get_active_spawn_zones(self, max_distance_reached: float) -> list[dict]:
        """Get all active spawn zones based on player distance."""
        active_zones = []
        for zone in self.spawn_zones:
            min_dist = zone.get("min_dist", 0)
            max_dist = zone.get("max_dist")

            if max_distance_reached >= min_dist:
                if max_dist is None or max_distance_reached <= max_dist:
                    active_zones.append(zone)
        return active_zones

    def get_spawn_zone(self, max_distance_reached: float) -> Optional[dict]:
        """Get primary active spawn zone for backward compatibility."""
        active = self.get_active_spawn_zones(max_distance_reached)
        return active[0] if active else None
