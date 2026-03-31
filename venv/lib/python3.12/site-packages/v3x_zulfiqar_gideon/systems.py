"""
Global game systems like objective and trigger management.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Type, Any, Set, TypeVar, Protocol

@dataclass
class ObjectiveTrigger:
    """A single objective trigger configuration."""
    text: str
    title: str = "Objective"
    trigger_type: str = "time"  # "time" | "flag"
    delay_seconds: float = 0.0
    flag_name: str = ""
    triggered: bool = False
    enabled: bool = True

class ObjectiveTriggerManager:
    """Manages a queue of objective triggers and checks firing conditions."""
    def __init__(self) -> None:
        self._triggers: list[ObjectiveTrigger] = []
        self._flags: set[str] = set()
        self._pending: Optional[ObjectiveTrigger] = None

    def add_trigger(self, text: str, title: str = "Objective", trigger_type: str = "time", delay_seconds: float = 0.0, flag_name: str = "", enabled: bool = True) -> None:
        self._triggers.append(ObjectiveTrigger(text=text, title=title, trigger_type=trigger_type, delay_seconds=delay_seconds, flag_name=flag_name, enabled=enabled))

    def set_flag(self, name: str) -> None:
        self._flags.add(name)

    def has_flag(self, name: str) -> bool:
        return name in self._flags

    def update(self, elapsed_seconds: float) -> None:
        if self._pending is not None: return
        for trigger in self._triggers:
            if trigger.triggered or not trigger.enabled: continue
            fired = False
            if trigger.trigger_type == "time":
                if elapsed_seconds >= trigger.delay_seconds: fired = True
            elif trigger.trigger_type == "flag":
                if trigger.flag_name in self._flags: fired = True
            if fired:
                trigger.triggered = True
                self._pending = trigger
                return

    def get_pending(self) -> Optional[ObjectiveTrigger]:
        trigger = self._pending
        self._pending = None
        return trigger

    def reset(self) -> None:
        self._flags.clear()
        self._pending = None
        for trigger in self._triggers: trigger.triggered = False




@dataclass
class SpawnConfig:
    """Configuration for entity spawning."""
    max_count: int = 3
    min_distance: int = 100
    max_distance: int = 300
    respawn_delay: int = 5000
    spawn_y_offset: int = 0
    spawn_area_padding: int = 50
    spawn_weights: Dict[str, float] = field(default_factory=dict)
    spawn_conditions: Dict[str, Any] = field(default_factory=dict)

class Spawner(Protocol):
    """Base protocol for all entity spawners."""
    @property
    def entity_type(self) -> Type[Any]: ...
    @property
    def config(self) -> SpawnConfig: ...
    def can_spawn(self, current_count: int, game_time: int) -> bool: ...
    def spawn(self, center_pos: pg.math.Vector2, game_time: int) -> Any: ...

@dataclass
class EntityGroup:
    """Container for a group of entities managed by a spawner."""
    spawner: Spawner
    instances: List[Any] = field(default_factory=list)
    dead_ids: Set[int] = field(default_factory=set)

class EntityManager:
    """Manages spawning and lifecycle of entity groups."""
    def __init__(self, target_entity, sprite_groups: List[pg.sprite.Group]):
        self.target = target_entity # e.g. player
        self.sprite_groups = sprite_groups
        self._groups: Dict[Type[Any], EntityGroup] = {}
        self._game_time: int = 0

    def register_spawner(self, spawner: Spawner) -> None:
        etype = spawner.entity_type
        if etype in self._groups:
            raise ValueError(f"Spawner for {etype.__name__} already registered")
        self._groups[etype] = EntityGroup(spawner=spawner)

    def update(self, dt: float) -> None:
        self._game_time = pg.time.get_ticks()
        self._cleanup_dead()
        self._handle_spawning()

    def _cleanup_dead(self) -> None:
        for group in self._groups.values():
            group.instances = [
                e for e in group.instances 
                if (hasattr(e, 'alive') and e.alive()) or 
                   (hasattr(e, 'is_dead') and not e.is_dead) or
                   (hasattr(e, 'health') and e.health > 0)
            ]

    def _handle_spawning(self) -> None:
        if not hasattr(self.target, 'rect'): return
        target_pos = pg.math.Vector2(self.target.rect.center)
        
        for group in self._groups.values():
            spawner = group.spawner
            if spawner.can_spawn(len(group.instances), self._game_time):
                entity = spawner.spawn(target_pos, self._game_time)
                for sg in self.sprite_groups:
                    sg.add(entity)
                group.instances.append(entity)

    def clear(self) -> None:
        for group in self._groups.values():
            for entity in group.instances:
                if hasattr(entity, 'kill'): entity.kill()
            group.instances.clear()
