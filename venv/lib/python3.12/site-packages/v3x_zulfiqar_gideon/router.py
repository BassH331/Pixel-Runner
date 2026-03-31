"""
Advanced orchestration for V3X ZULFIQAR-GIDEON.
Handles asset manifests and state routing maps.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Any, Type, Optional, TYPE_CHECKING, Union, Callable

if TYPE_CHECKING:
    from .state_machine import State

@dataclass
class V3XManifest:
    """A configuration manifest for a V3X project."""
    title: str = "V3X Game"
    base_width: int = 1280
    base_height: int = 720
    audio: Dict[str, str] = field(default_factory=dict)
    theme: Dict[str, Any] = field(default_factory=dict)
    # routes maps a State class (or name) to either:
    # 1. A single next State class (default transition)
    # 2. A Dict mapping event strings to State classes
    routes: Dict[Union[Type[State], str], Union[Type[State], Dict[str, Type[State]]]] = field(default_factory=dict)
    initial_state: Optional[Type[State]] = None

class Router:
    """Manages the game flow based on a route map."""
    
    def __init__(self, routes: Dict[Union[Type[State], str], Any]):
        self._routes = routes
        self._state_manager = None
        
    def set_manager(self, manager: Any):
        self._state_manager = manager
        
    def get_next(self, current_state: State, event: Optional[str] = None) -> Optional[Type[State]]:
        """Determine the next state class based on the current state and an optional event."""
        # Try finding route by class
        route = self._routes.get(type(current_state))
        
        # If not found by class, try by name (useful for decoupled states)
        if route is None:
            route = self._routes.get(current_state.__class__.__name__)
            
        if route is None:
            return None
            
        # Case 1: Direct transition
        if isinstance(route, type):
            return route
            
        # Case 2: Event-driven transition
        if isinstance(route, dict) and event:
            return route.get(event)
            
        return None
