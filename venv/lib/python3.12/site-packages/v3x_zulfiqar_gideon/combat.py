"""
Frame-based combat system for precise hit detection and damage application.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import TYPE_CHECKING, Final, Optional

import pygame as pg

if TYPE_CHECKING:
    from collections.abc import Mapping

class AttackPhase(Enum):
    """Distinct phases of an attack animation."""
    STARTUP = auto()
    ACTIVE = auto()
    RECOVERY = auto()
    COMPLETE = auto()

@dataclass(frozen=True, slots=True)
class HitboxData:
    """Immutable hitbox configuration for a specific attack frame."""
    offset_x: int = 0
    offset_y: int = 0
    width: int = 50
    height: int = 50
    
    def to_rect(self, entity_rect: pg.Rect, facing_left: bool = False) -> pg.Rect:
        actual_offset_x = -self.offset_x if facing_left else self.offset_x
        center_x = entity_rect.centerx + actual_offset_x
        center_y = entity_rect.centery + self.offset_y
        return pg.Rect(
            center_x - self.width // 2,
            center_y - self.height // 2,
            self.width,
            self.height,
        )

@dataclass(frozen=True, slots=True)
class AttackConfig:
    """Immutable configuration defining an attack's properties."""
    hit_frames: frozenset[int] = field(default_factory=frozenset)
    base_damage: float = 10.0
    knockback_force: float = 5.0
    knockback_angle: Optional[float] = None
    hit_stop_frames: int = 0
    can_hit_multiple: bool = True
    max_hits_per_target: int = 1
    frame_damage_modifiers: Mapping[int, float] = field(default_factory=dict)
    hitbox_data: Mapping[int, HitboxData] = field(default_factory=dict)
    startup_frames: frozenset[int] = field(default_factory=frozenset)
    recovery_frames: frozenset[int] = field(default_factory=frozenset)

    def __post_init__(self) -> None:
        if self.base_damage < 0: raise ValueError("base_damage cannot be negative")
        if self.knockback_force < 0: raise ValueError("knockback_force cannot be negative")
        if self.max_hits_per_target < 1: raise ValueError("max_hits_per_target must be at least 1")

_DEFAULT_HITBOX: Final[HitboxData] = HitboxData()

class AttackState:
    """Mutable runtime state for an active attack."""
    __slots__ = (
        "_config", "_current_frame", "_is_active", 
        "_hit_registry", "_hit_counts", "_hit_stop_remaining",
    )
    
    def __init__(self) -> None:
        self._config: Optional[AttackConfig] = None
        self._current_frame: int = 0
        self._is_active: bool = False
        self._hit_registry: dict[int, set[int]] = {}
        self._hit_counts: dict[int, int] = {}
        self._hit_stop_remaining: int = 0

    @property
    def is_active(self) -> bool: return self._is_active
    @property
    def current_frame(self) -> int: return self._current_frame
    @property
    def config(self) -> Optional[AttackConfig]: return self._config
    @property
    def is_in_hit_stop(self) -> bool: return self._hit_stop_remaining > 0

    def begin(self, config: AttackConfig) -> None:
        if config is None: raise ValueError("AttackConfig cannot be None")
        self._config = config
        self._current_frame = 0
        self._is_active = True
        self._hit_registry.clear()
        self._hit_counts.clear()
        self._hit_stop_remaining = 0

    def update(self, current_animation_frame: int) -> None:
        if not self._is_active: return
        if self._hit_stop_remaining > 0:
            self._hit_stop_remaining -= 1
            return
        self._current_frame = current_animation_frame

    def end(self) -> None:
        self._is_active = False
        self._config = None
        self._hit_registry.clear()
        self._hit_counts.clear()
        self._hit_stop_remaining = 0

    def get_current_phase(self) -> AttackPhase:
        if not self._is_active or self._config is None: return AttackPhase.COMPLETE
        frame = self._current_frame
        if frame in self._config.startup_frames: return AttackPhase.STARTUP
        elif frame in self._config.hit_frames: return AttackPhase.ACTIVE
        elif frame in self._config.recovery_frames: return AttackPhase.RECOVERY
        else:
            if not self._config.hit_frames: return AttackPhase.RECOVERY
            min_hit = min(self._config.hit_frames); max_hit = max(self._config.hit_frames)
            if frame < min_hit: return AttackPhase.STARTUP
            elif frame > max_hit: return AttackPhase.RECOVERY
            else: return AttackPhase.ACTIVE

    def is_hit_frame_active(self) -> bool:
        if not self._is_active or self._config is None or self._hit_stop_remaining > 0: return False
        return self._current_frame in self._config.hit_frames

    def try_register_hit(self, target_id: int) -> bool:
        if not self.is_hit_frame_active() or self._config is None: return False
        current_hits = self._hit_counts.get(target_id, 0)
        if current_hits >= self._config.max_hits_per_target: return False
        hit_frames = self._hit_registry.get(target_id)
        if hit_frames is not None and self._current_frame in hit_frames: return False
        if target_id not in self._hit_registry: self._hit_registry[target_id] = set()
        self._hit_registry[target_id].add(self._current_frame)
        self._hit_counts[target_id] = current_hits + 1
        if self._config.hit_stop_frames > 0: self._hit_stop_remaining = self._config.hit_stop_frames
        return True

    def get_current_damage(self) -> float:
        if not self._is_active or self._config is None: return 0.0
        return self._config.base_damage * self._config.frame_damage_modifiers.get(self._current_frame, 1.0)

    def get_knockback_vector(self, attacker_pos: tuple[float, float], target_pos: tuple[float, float], facing_left: bool = False) -> tuple[float, float]:
        if not self._is_active or self._config is None: return (0.0, 0.0)
        force = self._config.knockback_force
        if self._config.knockback_angle is not None:
            angle_rad = math.radians(self._config.knockback_angle)
            x_dir = -1.0 if facing_left else 1.0
            return (math.cos(angle_rad) * force * x_dir, -math.sin(angle_rad) * force)
        dx = target_pos[0] - attacker_pos[0]; dy = target_pos[1] - attacker_pos[1]
        dist = math.sqrt(dx*dx + dy*dy)
        if dist < 0.001: return (force * (-1.0 if facing_left else 1.0), -force * 0.3)
        return ((dx / dist) * force, (dy / dist) * force)

    def get_current_hitbox(self, entity_rect: pg.Rect, facing_left: bool = False) -> Optional[pg.Rect]:
        if not self.is_hit_frame_active() or self._config is None: return None
        return self._config.hitbox_data.get(self._current_frame, _DEFAULT_HITBOX).to_rect(entity_rect, facing_left)

@dataclass(frozen=True, slots=True)
class HitResult:
    """Result of a successful hit registration."""
    target_id: int
    damage: float
    knockback: tuple[float, float]
    hit_stop_frames: int = 0
    is_critical: bool = False
    hit_frame: int = 0

class CombatProcessor:
    """Utility class for processing combat interactions."""
    @classmethod
    def process_attack_against_targets(cls, attack_state: AttackState, attacker_rect: pg.Rect, attacker_facing_left: bool, targets: list[tuple[int, pg.Rect]]) -> list[HitResult]:
        if not attack_state.is_hit_frame_active(): return []
        hitbox = attack_state.get_current_hitbox(attacker_rect, attacker_facing_left)
        if hitbox is None: return []
        results = []
        for tid, trect in targets:
            if hitbox.colliderect(trect) and attack_state.try_register_hit(tid):
                results.append(HitResult(
                    target_id=tid,
                    damage=attack_state.get_current_damage(),
                    knockback=attack_state.get_knockback_vector(attacker_rect.center, trect.center, attacker_facing_left),
                    hit_stop_frames=attack_state.config.hit_stop_frames if attack_state.config else 0,
                    hit_frame=attack_state.current_frame
                ))
        return results
