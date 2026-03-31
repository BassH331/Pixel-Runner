"""
World Event System for distance-triggered game logic.

Provides a standard way to schedule spawns, dialogue, and other events
at specific points in a scrolling game world.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Set


@dataclass
class WorldEvent:
    """A single event triggered at a specific world distance.

    Args:
        id: Unique identifier for the event (prevents double-triggering).
        distance: World X distance when this event fires.
        event_type: String identifier for the type of event (e.g. "npc", "enemy").
        params: Arbitrary data passed to the event handler.
    """
    id: int
    distance: float
    event_type: str
    params: Dict[str, Any] = field(default_factory=dict)
    triggered: bool = False


class WorldEventManager:
    """Manages distance-based triggers and dispatches them to handlers.

    Usage:
        manager = WorldEventManager()
        
        # Register a handler for a specific event type
        manager.register_handler("spawn", lambda params: create_entity(**params))
        
        # Add events
        manager.add_event(id=1, distance=500, event_type="spawn", type="enemy")
        
        # update() in game loop
        manager.update(current_world_distance)
    """

    def __init__(self) -> None:
        self._events: List[WorldEvent] = []
        self._handlers: Dict[str, Callable[[Dict[str, Any]], None]] = {}
        self._spawned_ids: Set[int] = set()
        self._is_sorted: bool = False

    def register_handler(self, event_type: str, callback: Callable[[Dict[str, Any]], None]) -> None:
        """Register a callback function for an event type."""
        self._handlers[event_type] = callback

    def add_event(self, id: int, distance: float, event_type: str, **params: Any) -> None:
        """Schedule a new world event.
        
        Events are automatically sorted by distance during update() or finalize().
        """
        self._events.append(WorldEvent(id, distance, event_type, params))
        self._is_sorted = False

    def finalize(self) -> None:
        """Manually sort and optimize the event list. 
        
        Call this after adding all events for a level. update() will also call this
        automatically if not already sorted.
        """
        self._events.sort(key=lambda e: e.distance)
        self._is_sorted = True

    def update(self, current_distance: float) -> None:
        """Check for events to fire at the current world distance.

        Optimized to handle distance jumps and sequential triggers efficiently.
        """
        if not self._is_sorted:
            self.finalize()

        for event in self._events:
            # Skip if already triggered globally or in this session
            if event.triggered or event.id in self._spawned_ids:
                continue

            # Since list is sorted, we can stop early if we haven't reached the distance
            if event.distance > current_distance:
                break

            # Trigger the event
            handler = self._handlers.get(event.event_type)
            if handler:
                event.triggered = True
                self._spawned_ids.add(event.id)
                handler(event.params)
            else:
                print(f"[WorldEventManager] Warning: No handler registered for '{event.event_type}'")

    def reset(self) -> None:
        """Reset all events (clears triggered status)."""
        self._spawned_ids.clear()
        for event in self._events:
            event.triggered = False

    def clear(self) -> None:
        """Remove all events and handlers."""
        self._events.clear()
        self._handlers.clear()
        self._spawned_ids.clear()
        self._is_sorted = True


import pygame as pg
from typing import Optional
from .asset_manager import AssetManager

class InteractionPoint(pg.sprite.Sprite):
    """An invisible world marker that triggers dialogue on proximity.

    Args:
        x: Initial world X position.
        y: Screen Y position.
        text: Objective/dialogue text shown in the parchment overlay.
        title: Header text for the parchment overlay.
        proximity_radius: Pixel distance to trigger the talk prompt.
        font_path: Path to the font asset.
        font_size: Size of the font.
    """

    def __init__(
        self,
        x: int,
        y: int,
        text: str,
        title: str = "Objective",
        proximity_radius: int = 150,
        font_path: Optional[str] = None,
        font_size: int = 30
    ) -> None:
        super().__init__()

        self.text = text
        self.title = title
        self.proximity_radius = proximity_radius
        self._interacted: bool = False
        
        # UI Settings
        self._font_path = font_path
        self._font_size = font_size
        self._PROMPT_COLOR = (255, 255, 255)
        self._PROMPT_BG_COLOR = (30, 30, 30, 200)
        self._PROMPT_PADDING_X = 16
        self._PROMPT_PADDING_Y = 8
        self._PROMPT_OFFSET_Y = -70
        self._PROMPT_BORDER_RADIUS = 8

        # Invisible sprite
        self.image = pg.Surface((1, 1), pg.SRCALPHA)
        self.image.fill((0, 0, 0, 0))
        self.rect = pg.Rect(x, y, 1, 1)

        self._prompt_surface: Optional[pg.Surface] = None
        self._in_range: bool = False

    def _ensure_prompt(self) -> None:
        """Lazy load font and build prompt surface."""
        if self._prompt_surface is not None:
            return
            
        if self._font_path is None:
            # Fallback to default pygame font if no path provided
            font = pg.font.SysFont(None, self._font_size)
        else:
            font = AssetManager.get_font(self._font_path, self._font_size)
            
        text_surf = font.render("Talk  [ X / ENTER ]", True, self._PROMPT_COLOR)
        w = text_surf.get_width() + self._PROMPT_PADDING_X * 2
        h = text_surf.get_height() + self._PROMPT_PADDING_Y * 2

        bg = pg.Surface((w, h), pg.SRCALPHA)
        pg.draw.rect(
            bg,
            self._PROMPT_BG_COLOR,
            (0, 0, w, h),
            border_radius=self._PROMPT_BORDER_RADIUS,
        )
        pg.draw.rect(
            bg,
            (200, 200, 200, 120),
            (0, 0, w, h),
            width=2,
            border_radius=self._PROMPT_BORDER_RADIUS,
        )
        bg.blit(text_surf, (self._PROMPT_PADDING_X, self._PROMPT_PADDING_Y))
        self._prompt_surface = bg

    @property
    def can_interact(self) -> bool:
        return self._in_range and not self._interacted

    def mark_interacted(self) -> None:
        self._interacted = True

    def reset(self) -> None:
        self._interacted = False

    def check_proximity(self, player_rect: pg.Rect) -> bool:
        dx = abs(self.rect.centerx - player_rect.centerx)
        dy = abs(self.rect.centery - player_rect.centery)
        distance = (dx * dx + dy * dy) ** 0.5
        self._in_range = distance <= self.proximity_radius
        return self._in_range

    def update(self, dt: Optional[float] = None, scroll_speed: int = 0) -> None:
        self.rect.x -= scroll_speed

    def draw(self, surface: pg.Surface) -> None:
        if not self.can_interact:
            return

        self._ensure_prompt()
        if self._prompt_surface:
            # Pulsing alpha
            ticks = pg.time.get_ticks()
            alpha = 180 + int(75 * abs(((ticks // 8) % 200 - 100) / 100))
            self._prompt_surface.set_alpha(alpha)

            px = self.rect.centerx - self._prompt_surface.get_width() // 2
            py = self.rect.centery + self._PROMPT_OFFSET_Y
            surface.blit(self._prompt_surface, (px, py))


class Sky:
    """Generic multi-layer parallax sky/background component."""
    
    def __init__(self, screen_width: int, screen_height: int, layer_paths: List[str], speeds: List[int] = None):
        """
        Initialize the sky with multiple parallax layers.
        
        Args:
            screen_width: Width of the screen.
            screen_height: Height of the screen.
            layer_paths: List of file paths for the background layers.
            speeds: List of scroll speeds (pixels per second) for each layer.
        """
        self.width = screen_width
        self.height = screen_height
        self.layers = []
        for path in layer_paths:
            img = AssetManager.get_texture(path)
            scaled_img = pg.transform.scale(img, (screen_width, screen_height))
            self.layers.append(scaled_img)
            
        self.speeds = speeds or [0] * len(self.layers)
        self.offsets = [0.0] * len(self.layers)
        
    def update(self, dt_sec: float):
        """Update layer offsets based on elapsed time."""
        for i in range(len(self.offsets)):
            if self.speeds[i] == 0: continue
            self.offsets[i] -= self.speeds[i] * dt_sec
            if self.offsets[i] <= -self.width:
                self.offsets[i] += self.width
                
    def draw(self, surface: pg.Surface):
        """Draw all layers with horizontal wrapping."""
        for i, layer in enumerate(self.layers):
            if self.speeds[i] == 0:
                surface.blit(layer, (0, 0))
            else:
                surface.blit(layer, (self.offsets[i], 0))
                surface.blit(layer, (self.offsets[i] + self.width, 0))


import json
import os

class WorldLoader:
    """Generic utility for loading world/level data from JSON."""
    
    @staticmethod
    def load_json(file_path: str) -> Optional[dict]:
        """Load and parse a JSON file."""
        if not os.path.exists(file_path):
            print(f"[WorldLoader] Error: File not found: {file_path}")
            return None
            
        try:
            with open(file_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"[WorldLoader] Error parsing {file_path}: {e}")
            return None
