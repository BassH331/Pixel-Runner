"""
WorldManager — Unified system managing background environment, parallax scrolling,
level geometry ground height, and distance-triggered world events.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, Optional
import pygame as pg

from v3x_zulfiqar_gideon import WorldEventManager
from src.game.systems.environment_manager import EnvironmentManager, EnvironmentProp


class WorldManager:
    """Unified manager for level environment, parallax layers, props, and distance events."""

    def __init__(
        self,
        screen_width: int,
        screen_height: int,
        notification_callback: Optional[Callable[[str, float], None]] = None,
    ) -> None:
        self.screen_width = screen_width
        self.screen_height = screen_height
        self._notification_callback = notification_callback

        self.environment_manager = EnvironmentManager(screen_width, screen_height)
        self.event_manager = WorldEventManager()

        # Register built-in ambient_lore handler immediately so callers don't need to.
        self.event_manager.register_handler("ambient_lore", self._handle_ambient_lore)

    @property
    def ground_y(self) -> int:
        """Get base ground Y level."""
        return self.environment_manager.ground_y

    @property
    def props(self) -> list[EnvironmentProp]:
        """Get environmental props list."""
        return self.environment_manager.props

    @property
    def sky(self) -> Any:
        """Get sky rendering layer."""
        return self.environment_manager.sky

    def load_level_config(self, level_data: dict) -> None:
        """Load environment layers, props, sky configuration, and world events from level JSON."""
        if "environment" in level_data:
            self.environment_manager.load_config(level_data["environment"])

        world_events = level_data.get("world_events", [])
        for evt in world_events:
            evt_id = evt.get("id", 0)
            dist = float(evt.get("distance", 0.0))
            evt_type = evt.get("event_type", "")
            params = evt.get("params", {})
            self.event_manager.add_event(id=evt_id, distance=dist, event_type=evt_type, **params)
        self.event_manager.finalize()

    def register_event_handler(self, event_type: str, callback: Callable[[Dict[str, Any]], None]) -> None:
        """Register a callback for distance-triggered world events."""
        self.event_manager.register_handler(event_type, callback)

    def get_ground_y_at(self, world_x: float) -> int:
        """Get precise ground Y height at specified world X coordinate."""
        ground = self.environment_manager.get_ground_y_at(world_x)
        return int(ground) if ground is not None else self.environment_manager.ground_y

    def update(self, dt_seconds: float, bg_scroll_speed: float, world_distance: float) -> None:
        """Update parallax layers, environmental props, and check distance event triggers."""
        self.environment_manager.update(dt_seconds, bg_scroll_speed * 60.0)
        self.event_manager.update(world_distance)

    def _handle_ambient_lore(self, params: dict) -> None:
        """Handler for 'ambient_lore' distance events — shows flavour text via notification."""
        text = params.get("text", "")
        if text and self._notification_callback:
            self._notification_callback(text, 5.0)

    def draw(self, target_surface: pg.Surface, camera_offset_x: float = 0.0) -> None:
        """Render sky, background parallax layers, and environmental props onto target_surface."""
        self.environment_manager.draw(target_surface, cam_x=camera_offset_x)
