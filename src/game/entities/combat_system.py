"""
Frame-based combat system for precise hit detection and damage application.

This module implements a professional-grade combat system where damage is only
applied during specific animation frames. This is the standard approach used
in fighting games, action RPGs, and character action games.

Architecture Overview:
─────────────────────────────────────────────────────────────────────────────
The system consists of three core components:

    1. AttackConfig (Immutable)
       - Defines attack properties: damage, knockback, hit frames
       - Configured once per attack type, shared across all instances
       - Supports multi-hit attacks with per-frame damage modifiers

    2. HitboxData (Immutable)
       - Defines spatial hitbox properties for a specific frame
       - Supports offset from entity position and custom dimensions
       - Enables frame-accurate hitbox size/position changes

    3. AttackState (Mutable)
       - Tracks runtime state of an active attack
       - Prevents duplicate hits on same target within single attack
       - Manages hit registration and damage windows

Frame-Based Hit Detection Flow:
─────────────────────────────────────────────────────────────────────────────

    [Attack Initiated]
           │
           ▼
    ┌─────────────────────────┐
    │  AttackState.begin()    │  ◄── Initialize with AttackConfig
    │  - Reset frame counter  │
    │  - Clear hit registry   │
    └───────────┬─────────────┘
                │
                ▼
    ┌─────────────────────────┐
    │  Animation Frame Loop   │  ◄── Called each animation update
    │  AttackState.update()   │
    └───────────┬─────────────┘
                │
                ▼
    ┌─────────────────────────┐
    │  is_hit_frame_active()  │  ◄── Check if current frame deals damage
    └───────────┬─────────────┘
                │
        ┌───────┴───────┐
        │               │
        ▼               ▼
    [Active]        [Inactive]
        │               │
        ▼               │
    ┌─────────────────┐ │
    │ Collision Check │ │
    │ with targets    │ │
    └───────┬─────────┘ │
            │           │
            ▼           │
    ┌─────────────────┐ │
    │ try_register_   │ │
    │ hit(target_id)  │ │
    └───────┬─────────┘ │
            │           │
    ┌───────┴───────┐   │
    │               │   │
    ▼               ▼   │
  [New Hit]    [Already Hit]
    │               │   │
    ▼               │   │
  Apply           Skip  │
  Damage            │   │
    │               │   │
    └───────┬───────┘   │
            │           │
            └─────┬─────┘
                  │
                  ▼
           [Next Frame]

Usage Example:
─────────────────────────────────────────────────────────────────────────────

    # Define attack configuration (typically at class level)
    HEAVY_SLASH_CONFIG = AttackConfig(
        hit_frames=frozenset({4, 5, 6}),
        base_damage=25.0,
        knockback_force=12.0,
        knockback_angle=45.0,
        hit_stop_frames=3,
        frame_damage_modifiers={4: 0.5, 5: 1.0, 6: 0.75},
        hitbox_data={
            4: HitboxData(offset_x=20, offset_y=-10, width=60, height=40),
            5: HitboxData(offset_x=30, offset_y=-10, width=80, height=50),
            6: HitboxData(offset_x=25, offset_y=-5, width=70, height=45),
        },
    )

    # In entity class
    def attack_heavy(self) -> bool:
        if not self._can_attack():
            return False
        self._attack_state.begin(self.HEAVY_SLASH_CONFIG)
        return True

    # In update loop
    def _process_attack_hits(self, targets: list[Entity]) -> None:
        if not self._attack_state.is_hit_frame_active():
            return

        hitbox = self._attack_state.get_current_hitbox(self.rect)
        if hitbox is None:
            return

        for target in targets:
            if not hitbox.colliderect(target.hitbox):
                continue

            if self._attack_state.try_register_hit(target.entity_id):
                damage = self._attack_state.get_current_damage()
                knockback = self._attack_state.get_knockback_vector(
                    self.rect.center, target.rect.center
                )
                target.take_damage(damage, knockback)
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import TYPE_CHECKING, Final, Optional

import pygame as pg

if TYPE_CHECKING:
    from collections.abc import Mapping, Set


class AttackPhase(Enum):
    """
    Distinct phases of an attack animation.
    
    Used for advanced combo systems and cancellation windows.
    
    Phases:
        STARTUP: Wind-up frames before hit becomes active
        ACTIVE: Frames where hitbox can deal damage
        RECOVERY: Cool-down frames after active window
        COMPLETE: Attack has finished
    """
    
    STARTUP = auto()
    ACTIVE = auto()
    RECOVERY = auto()
    COMPLETE = auto()


@dataclass(frozen=True, slots=True)
class HitboxData:
    """
    Immutable hitbox configuration for a specific attack frame.
    
    Hitboxes are defined relative to the entity's position, allowing
    attacks to have different reach and coverage on different frames.
    
    Attributes:
        offset_x: Horizontal offset from entity center (positive = forward).
        offset_y: Vertical offset from entity center (negative = up).
        width: Hitbox width in pixels.
        height: Hitbox height in pixels.
        
    Note:
        Offset direction is automatically flipped based on entity facing
        when the hitbox rect is generated.
    """
    
    offset_x: int = 0
    offset_y: int = 0
    width: int = 50
    height: int = 50
    
    def to_rect(
        self,
        entity_rect: pg.Rect,
        facing_left: bool = False,
    ) -> pg.Rect:
        """
        Generate a pygame Rect from this hitbox data.
        
        Args:
            entity_rect: The entity's current bounding rect.
            facing_left: Whether the entity is facing left.
            
        Returns:
            A pygame Rect positioned relative to the entity.
        """
        # Flip x offset based on facing direction
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
    """
    Immutable configuration defining an attack's properties.
    
    This dataclass holds all static data for an attack type. It should be
    defined once per attack (typically as a class constant) and passed to
    AttackState.begin() when the attack is initiated.
    
    Attributes:
        hit_frames: Set of animation frame indices where damage can be dealt.
            Frame indices are 0-based and correspond to animation frames.
            
        base_damage: Base damage value before modifiers.
        
        knockback_force: Magnitude of knockback applied to hit targets.
        
        knockback_angle: Default knockback angle in degrees (0 = right, 90 = up).
            Set to None for knockback toward direction of attack.
            
        hit_stop_frames: Number of frames to freeze on hit (game feel / juice).
            Both attacker and target typically freeze for this duration.
            
        can_hit_multiple: Whether attack can hit multiple targets per frame.
            False = single target, True = hits all targets in hitbox.
            
        max_hits_per_target: Maximum times this attack can hit a single target.
            1 = single hit, >1 = multi-hit attacks (e.g., rapid jabs).
            
        frame_damage_modifiers: Per-frame damage multipliers.
            Maps frame index to damage multiplier (1.0 = full damage).
            Frames not in this dict use 1.0 as default.
            
        hitbox_data: Per-frame hitbox configurations.
            Maps frame index to HitboxData for that frame.
            Frames not in this dict use default HitboxData.
            
        startup_frames: Frame indices considered startup (before active).
            Used for determining attack phase and cancel windows.
            
        recovery_frames: Frame indices considered recovery (after active).
            Used for determining attack phase and cancel windows.
            
    Example:
        >>> QUICK_SLASH = AttackConfig(
        ...     hit_frames=frozenset({3, 4}),
        ...     base_damage=10.0,
        ...     knockback_force=5.0,
        ...     hit_stop_frames=2,
        ...     frame_damage_modifiers={3: 0.8, 4: 1.0},
        ... )
    """
    
    # Required parameters
    hit_frames: frozenset[int] = field(default_factory=frozenset)
    base_damage: float = 10.0
    knockback_force: float = 5.0
    
    # Knockback configuration
    knockback_angle: Optional[float] = None  # None = direction-based
    
    # Hit behavior
    hit_stop_frames: int = 0
    can_hit_multiple: bool = True
    max_hits_per_target: int = 1
    
    # Per-frame modifiers (frame_index -> modifier)
    frame_damage_modifiers: Mapping[int, float] = field(default_factory=dict)
    hitbox_data: Mapping[int, HitboxData] = field(default_factory=dict)
    
    # Phase frame sets (for advanced cancel/combo systems)
    startup_frames: frozenset[int] = field(default_factory=frozenset)
    recovery_frames: frozenset[int] = field(default_factory=frozenset)
    
    def __post_init__(self) -> None:
        """Validate configuration on creation."""
        if self.base_damage < 0:
            raise ValueError("base_damage cannot be negative")
        if self.knockback_force < 0:
            raise ValueError("knockback_force cannot be negative")
        if self.max_hits_per_target < 1:
            raise ValueError("max_hits_per_target must be at least 1")


# Default hitbox used when no frame-specific hitbox is configured
_DEFAULT_HITBOX: Final[HitboxData] = HitboxData()


class AttackState:
    """
    Mutable runtime state for an active attack.
    
    This class tracks the current state of an attack in progress, including
    which targets have been hit and the current animation frame. A single
    instance should be reused across attacks via the begin() method.
    
    Thread Safety:
        This class is NOT thread-safe. Each entity should have its own
        AttackState instance.
    
    Attributes:
        is_active: Whether an attack is currently in progress.
        current_frame: Current animation frame index.
        config: The AttackConfig for the current attack.
        
    Example:
        >>> attack_state = AttackState()
        >>> attack_state.begin(SLASH_CONFIG)
        >>> attack_state.update(current_animation_frame=3)
        >>> if attack_state.is_hit_frame_active():
        ...     # Process collisions
        ...     if attack_state.try_register_hit(enemy.id):
        ...         enemy.take_damage(attack_state.get_current_damage())
    """
    
    __slots__ = (
        "_config",
        "_current_frame",
        "_is_active",
        "_hit_registry",
        "_hit_counts",
        "_hit_stop_remaining",
    )
    
    def __init__(self) -> None:
        """Initialize attack state in inactive state."""
        self._config: Optional[AttackConfig] = None
        self._current_frame: int = 0
        self._is_active: bool = False
        
        # Maps target_id -> set of frames where target was hit
        self._hit_registry: dict[int, set[int]] = {}
        
        # Maps target_id -> number of times hit
        self._hit_counts: dict[int, int] = {}
        
        # Hit stop countdown
        self._hit_stop_remaining: int = 0
    
    # ─────────────────────────────────────────────────────────────────────────
    # Public Properties
    # ─────────────────────────────────────────────────────────────────────────
    
    @property
    def is_active(self) -> bool:
        """Whether an attack is currently in progress."""
        return self._is_active
    
    @property
    def current_frame(self) -> int:
        """Current animation frame index."""
        return self._current_frame
    
    @property
    def config(self) -> Optional[AttackConfig]:
        """Configuration for the current attack, or None if inactive."""
        return self._config
    
    @property
    def is_in_hit_stop(self) -> bool:
        """Whether currently in hit stop freeze."""
        return self._hit_stop_remaining > 0
    
    @property
    def hit_stop_remaining(self) -> int:
        """Remaining hit stop frames."""
        return self._hit_stop_remaining
    
    # ─────────────────────────────────────────────────────────────────────────
    # Lifecycle Methods
    # ─────────────────────────────────────────────────────────────────────────
    
    def begin(self, config: AttackConfig) -> None:
        """
        Begin a new attack with the given configuration.
        
        Resets all state and prepares for a new attack sequence.
        
        Args:
            config: The attack configuration to use.
            
        Raises:
            ValueError: If config is None.
        """
        if config is None:
            raise ValueError("AttackConfig cannot be None")
        
        self._config = config
        self._current_frame = 0
        self._is_active = True
        self._hit_registry.clear()
        self._hit_counts.clear()
        self._hit_stop_remaining = 0
    
    def update(self, current_animation_frame: int) -> None:
        """
        Update attack state with current animation frame.
        
        Should be called each frame during an active attack to sync
        the attack state with the animation system.
        
        Args:
            current_animation_frame: The current animation frame index (0-based).
        """
        if not self._is_active:
            return
        
        # Decrement hit stop
        if self._hit_stop_remaining > 0:
            self._hit_stop_remaining -= 1
            return
        
        self._current_frame = current_animation_frame
    
    def end(self) -> None:
        """
        End the current attack.
        
        Should be called when the attack animation completes or is
        cancelled. Clears all state.
        """
        self._is_active = False
        self._config = None
        self._hit_registry.clear()
        self._hit_counts.clear()
        self._hit_stop_remaining = 0
    
    # ─────────────────────────────────────────────────────────────────────────
    # Phase Detection
    # ─────────────────────────────────────────────────────────────────────────
    
    def get_current_phase(self) -> AttackPhase:
        """
        Determine the current phase of the attack.
        
        Returns:
            The current AttackPhase based on frame position.
        """
        if not self._is_active or self._config is None:
            return AttackPhase.COMPLETE
        
        frame = self._current_frame
        
        if frame in self._config.startup_frames:
            return AttackPhase.STARTUP
        elif frame in self._config.hit_frames:
            return AttackPhase.ACTIVE
        elif frame in self._config.recovery_frames:
            return AttackPhase.RECOVERY
        else:
            # Infer phase from frame position relative to hit frames
            if not self._config.hit_frames:
                return AttackPhase.RECOVERY
            
            min_hit = min(self._config.hit_frames)
            max_hit = max(self._config.hit_frames)
            
            if frame < min_hit:
                return AttackPhase.STARTUP
            elif frame > max_hit:
                return AttackPhase.RECOVERY
            else:
                # Between hit frames but not on one
                return AttackPhase.ACTIVE
    
    def is_hit_frame_active(self) -> bool:
        """
        Check if the current frame is an active hit frame.
        
        Returns:
            True if current frame can deal damage, False otherwise.
        """
        if not self._is_active or self._config is None:
            return False
        
        if self._hit_stop_remaining > 0:
            return False
        
        return self._current_frame in self._config.hit_frames
    
    # ─────────────────────────────────────────────────────────────────────────
    # Hit Registration
    # ─────────────────────────────────────────────────────────────────────────
    
    def try_register_hit(self, target_id: int) -> bool:
        """
        Attempt to register a hit on a target.
        
        Checks if the target can be hit on the current frame and
        registers the hit if valid. Prevents duplicate hits based
        on the attack configuration.
        
        Args:
            target_id: Unique identifier for the target entity.
            
        Returns:
            True if hit was registered (damage should be applied),
            False if hit was rejected (already hit or invalid state).
        """
        if not self.is_hit_frame_active():
            return False
        
        if self._config is None:
            return False
        
        # Check if target has reached max hits
        current_hits = self._hit_counts.get(target_id, 0)
        if current_hits >= self._config.max_hits_per_target:
            return False
        
        # Check if already hit on this specific frame
        hit_frames = self._hit_registry.get(target_id)
        if hit_frames is not None and self._current_frame in hit_frames:
            return False
        
        # Register the hit
        if target_id not in self._hit_registry:
            self._hit_registry[target_id] = set()
        
        self._hit_registry[target_id].add(self._current_frame)
        self._hit_counts[target_id] = current_hits + 1
        
        # Apply hit stop
        if self._config.hit_stop_frames > 0:
            self._hit_stop_remaining = self._config.hit_stop_frames
        
        return True
    
    def has_hit_target(self, target_id: int) -> bool:
        """
        Check if a target has been hit during this attack.
        
        Args:
            target_id: Unique identifier for the target entity.
            
        Returns:
            True if target has been hit at least once.
        """
        return target_id in self._hit_counts
    
    def get_hit_count(self, target_id: int) -> int:
        """
        Get the number of times a target has been hit.
        
        Args:
            target_id: Unique identifier for the target entity.
            
        Returns:
            Number of registered hits on this target.
        """
        return self._hit_counts.get(target_id, 0)
    
    def get_all_hit_targets(self) -> frozenset[int]:
        """
        Get all target IDs that have been hit during this attack.
        
        Returns:
            Frozenset of target IDs.
        """
        return frozenset(self._hit_counts.keys())
    
    # ─────────────────────────────────────────────────────────────────────────
    # Damage Calculation
    # ─────────────────────────────────────────────────────────────────────────
    
    def get_current_damage(self) -> float:
        """
        Calculate damage for the current frame.
        
        Applies frame-specific damage modifiers if configured.
        
        Returns:
            Damage value for the current frame, or 0 if inactive.
        """
        if not self._is_active or self._config is None:
            return 0.0
        
        base = self._config.base_damage
        modifier = self._config.frame_damage_modifiers.get(
            self._current_frame, 1.0
        )
        
        return base * modifier
    
    def get_knockback_force(self) -> float:
        """
        Get knockback force for the current attack.
        
        Returns:
            Knockback force value, or 0 if inactive.
        """
        if not self._is_active or self._config is None:
            return 0.0
        
        return self._config.knockback_force
    
    def get_knockback_vector(
        self,
        attacker_pos: tuple[float, float],
        target_pos: tuple[float, float],
        facing_left: bool = False,
    ) -> tuple[float, float]:
        """
        Calculate knockback vector for a hit.
        
        If knockback_angle is configured, uses that angle.
        Otherwise, calculates direction from attacker to target.
        
        Args:
            attacker_pos: Attacker's position (x, y).
            target_pos: Target's position (x, y).
            facing_left: Whether attacker is facing left.
            
        Returns:
            Tuple of (knockback_x, knockback_y).
        """
        if not self._is_active or self._config is None:
            return (0.0, 0.0)
        
        force = self._config.knockback_force
        
        if self._config.knockback_angle is not None:
            # Use configured angle
            angle_rad = math.radians(self._config.knockback_angle)
            
            # Flip horizontal component based on facing
            x_dir = -1.0 if facing_left else 1.0
            
            kb_x = math.cos(angle_rad) * force * x_dir
            kb_y = -math.sin(angle_rad) * force  # Negative Y is up
            
            return (kb_x, kb_y)
        else:
            # Calculate direction from attacker to target
            dx = target_pos[0] - attacker_pos[0]
            dy = target_pos[1] - attacker_pos[1]
            
            distance = math.sqrt(dx * dx + dy * dy)
            
            if distance < 0.001:
                # Fallback if positions overlap
                x_dir = -1.0 if facing_left else 1.0
                return (force * x_dir, -force * 0.3)
            
            # Normalize and scale
            kb_x = (dx / distance) * force
            kb_y = (dy / distance) * force
            
            return (kb_x, kb_y)
    
    # ─────────────────────────────────────────────────────────────────────────
    # Hitbox Generation
    # ─────────────────────────────────────────────────────────────────────────
    
    def get_current_hitbox_data(self) -> HitboxData:
        """
        Get hitbox data for the current frame.
        
        Returns frame-specific hitbox if configured, otherwise
        returns the default hitbox.
        
        Returns:
            HitboxData for the current frame.
        """
        if not self._is_active or self._config is None:
            return _DEFAULT_HITBOX
        
        return self._config.hitbox_data.get(
            self._current_frame, _DEFAULT_HITBOX
        )
    
    def get_current_hitbox(
        self,
        entity_rect: pg.Rect,
        facing_left: bool = False,
    ) -> Optional[pg.Rect]:
        """
        Generate hitbox rect for the current frame.
        
        Returns None if attack is inactive or not on a hit frame.
        
        Args:
            entity_rect: The attacking entity's bounding rect.
            facing_left: Whether the entity is facing left.
            
        Returns:
            Pygame Rect for the hitbox, or None if no active hitbox.
        """
        if not self.is_hit_frame_active():
            return None
        
        hitbox_data = self.get_current_hitbox_data()
        return hitbox_data.to_rect(entity_rect, facing_left)
    
    # ─────────────────────────────────────────────────────────────────────────
    # Debug Support
    # ─────────────────────────────────────────────────────────────────────────
    
    def get_debug_info(self) -> dict:
        """
        Get debug information about current attack state.
        
        Useful for development debugging and state visualization.
        
        Returns:
            Dictionary containing attack state details.
        """
        return {
            "is_active": self._is_active,
            "current_frame": self._current_frame,
            "phase": self.get_current_phase().name,
            "is_hit_frame": self.is_hit_frame_active(),
            "hit_stop_remaining": self._hit_stop_remaining,
            "targets_hit": len(self._hit_counts),
            "total_hits": sum(self._hit_counts.values()),
            "config_name": type(self._config).__name__ if self._config else None,
        }


# ─────────────────────────────────────────────────────────────────────────────
# Combat Result Types
# ─────────────────────────────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class HitResult:
    """
    Result of a successful hit registration.
    
    Contains all information needed to apply the hit effects
    to the target entity.
    
    Attributes:
        target_id: ID of the hit target.
        damage: Damage to apply.
        knockback: Knockback vector (x, y).
        hit_stop_frames: Frames of hit stop to apply.
        is_critical: Whether this was a critical hit.
        hit_frame: Animation frame when hit occurred.
    """
    
    target_id: int
    damage: float
    knockback: tuple[float, float]
    hit_stop_frames: int = 0
    is_critical: bool = False
    hit_frame: int = 0


class CombatProcessor:
    """
    Utility class for processing combat interactions.
    
    Provides static methods for common combat calculations and
    batch processing of hits.
    
    This class is stateless and all methods are class methods
    for ease of use without instantiation.
    """
    
    @classmethod
    def process_attack_against_targets(
        cls,
        attack_state: AttackState,
        attacker_rect: pg.Rect,
        attacker_facing_left: bool,
        targets: list[tuple[int, pg.Rect]],  # List of (target_id, target_rect)
    ) -> list[HitResult]:
        """
        Process an attack against multiple potential targets.
        
        Handles collision detection, hit registration, and damage
        calculation for all targets in range.
        
        Args:
            attack_state: The attacker's attack state.
            attacker_rect: The attacker's bounding rect.
            attacker_facing_left: Whether attacker is facing left.
            targets: List of (target_id, target_rect) tuples.
            
        Returns:
            List of HitResult for each successful hit.
        """
        if not attack_state.is_hit_frame_active():
            return []
        
        hitbox = attack_state.get_current_hitbox(
            attacker_rect, attacker_facing_left
        )
        
        if hitbox is None:
            return []
        
        results: list[HitResult] = []
        
        for target_id, target_rect in targets:
            # Check collision
            if not hitbox.colliderect(target_rect):
                continue
            
            # Try to register hit
            if not attack_state.try_register_hit(target_id):
                continue
            
            # Calculate hit result
            damage = attack_state.get_current_damage()
            knockback = attack_state.get_knockback_vector(
                attacker_rect.center,
                target_rect.center,
                attacker_facing_left,
            )
            
            config = attack_state.config
            hit_stop = config.hit_stop_frames if config else 0
            
            result = HitResult(
                target_id=target_id,
                damage=damage,
                knockback=knockback,
                hit_stop_frames=hit_stop,
                hit_frame=attack_state.current_frame,
            )
            results.append(result)
            
            # If attack can't hit multiple, stop after first hit
            if config and not config.can_hit_multiple:
                break
        
        return results
    
    @classmethod
    def calculate_final_damage(
        cls,
        base_damage: float,
        attacker_stats: Optional[dict] = None,
        target_stats: Optional[dict] = None,
        damage_type: str = "physical",
    ) -> float:
        """
        Calculate final damage after all modifiers.
        
        Override this method to implement custom damage formulas
        for your game's specific mechanics.
        
        Args:
            base_damage: Raw damage before modifiers.
            attacker_stats: Attacker's combat stats (attack power, etc.).
            target_stats: Target's combat stats (defense, resistances).
            damage_type: Type of damage for resistance calculations.
            
        Returns:
            Final calculated damage value.
        """
        # Default implementation - simple damage formula
        # Customize this for your game's damage system
        
        attack_power = 1.0
        defense = 0.0
        
        if attacker_stats:
            attack_power = attacker_stats.get("attack_power", 1.0)
        
        if target_stats:
            defense = target_stats.get("defense", 0.0)
            
            # Check for type-specific resistance
            resistance_key = f"{damage_type}_resistance"
            resistance = target_stats.get(resistance_key, 0.0)
            defense += resistance
        
        # Simple formula: damage = base * attack / (1 + defense/100)
        final_damage = (base_damage * attack_power) / (1 + defense / 100)
        
        return max(0.0, final_damage)
