"""
PlayingState — Primary gameplay state managing core update/draw loop and state transitions.
"""

from __future__ import annotations

from typing import Optional
import pygame as pg

from v3x_zulfiqar_gideon import State, StateManager


class PlayingState(State):
    """Core playing state for active gameplay running under StateManager."""

    def __init__(self, manager: Optional[StateManager] = None) -> None:
        super().__init__(manager)
        self.is_active: bool = False
        self.is_paused: bool = False

    def on_enter(self) -> None:
        """Called when entering the playing state."""
        self.is_active = True
        self.is_paused = False

    def on_exit(self) -> None:
        """Called when exiting the playing state."""
        self.is_active = False

    def handle_event(self, event: pg.event.Event) -> None:
        """Handle Pygame input events."""
        pass

    def update(self, dt: float) -> None:
        """Update gameplay state. Subclasses implement specific frame logic."""
        pass

    def draw(self, surface: pg.Surface) -> None:
        """Render gameplay state. Subclasses implement specific frame logic."""
        pass
