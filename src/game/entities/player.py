"""
Player entity module with comprehensive state machine animation system.

This module implements a player character with a finite state machine (FSM)
controlling animations and behavior. The architecture is designed for
extensibility—new states can be added by following the documented pattern.

Architecture Overview:
─────────────────────────────────────────────────────────────────────────────
The player uses a PRIORITY-BASED STATE MACHINE where certain states take
precedence over others. States are organized into priority tiers:

    TIER 1 (Highest): DEATH
    TIER 2: HURT (with invincibility frames)
    TIER 3: ATTACK_THRUST, ATTACK_SMASH
    TIER 4: JUMP_UP, JUMP_DOWN
    TIER 5 (Lowest): RUN, IDLE

Higher-tier states cannot be interrupted by lower-tier states. For example,
a player in HURT state cannot transition to RUN until the hurt animation
completes.

Combat System Integration:
─────────────────────────────────────────────────────────────────────────────
The player uses a frame-based combat system where damage is only applied
during specific animation frames. This is controlled by:

    1. AttackConfig - Defines hit frames, damage, knockback per attack type
    2. AttackState - Tracks active attack and prevents duplicate hits
    3. should_deal_damage() - Query method for collision systems
    4. get_attack_hitbox() - Returns active hitbox rect for collision

External systems should use the following pattern:
    
    if player.should_deal_damage():
        hitbox = player.get_attack_hitbox()
        for enemy in enemies:
            if hitbox.colliderect(enemy.hitbox):
                if player.try_register_hit(enemy.entity_id):
                    damage = player.get_current_attack_damage()
                    knockback = player.get_attack_knockback(enemy.rect.center)
                    enemy.take_damage(damage, knockback)
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Final, Optional

import pygame as pg

from src.my_engine.asset_manager import AssetManager
from src.my_engine.ecs import Entity
from src.game.audio.footsteps import FootstepController
from .combat_system import (
    AttackConfig,
    AttackState,
    AttackPhase,
    HitboxData,
    HitResult,
    CombatProcessor,
)

if TYPE_CHECKING:
    from src.my_engine.audio_manager import AudioManager


class PlayerState(Enum):
    """
    Enumeration of player states with implicit priority ordering.
    
    Lower values = higher priority. States with higher priority cannot
    be interrupted by states with lower priority.
    
    Priority Tiers:
        0-9:   Terminal states (DEATH)
        10-19: Reactive states (HURT)
        20-29: Action states (ATTACK variants)
        30-39: Movement states (JUMP variants)
        40+:   Base states (RUN, IDLE)
    """
    
    # Terminal states (highest priority)
    DEATH = 0
    
    # Reactive states
    HURT = 10
    
    # Action states
    ATTACK_THRUST = 20
    ATTACK_SMASH = 21
    
    # Aerial states
    JUMP_UP = 30
    JUMP_DOWN = 31
    
    # Ground states (lowest priority)
    RUN = 40
    IDLE = 50


@dataclass(frozen=True, slots=True)
class StateConfig:
    """
    Configuration for a player state's animation behavior.
    
    Attributes:
        animation_speed: Frame advancement rate per update (0.1 = slow, 0.5 = fast).
        loops: Whether animation loops or plays once.
        next_state: State to transition to when animation completes (if not looping).
        interruptible: Whether this state can be cancelled by player input.
        grants_invincibility: Whether player is immune to damage in this state.
        locks_movement: Whether horizontal movement is disabled.
        locks_input: Whether all player input is ignored.
    """
    
    animation_speed: float = 0.2
    loops: bool = True
    next_state: Optional[PlayerState] = None
    interruptible: bool = True
    grants_invincibility: bool = False
    locks_movement: bool = False
    locks_input: bool = False


class Player(Entity):
    """
    Player character with state machine-driven animation and frame-based combat.
    
    The player uses a finite state machine (FSM) to manage animations
    and behavior. Combat uses a frame-based hit detection system where
    damage is only dealt during specific animation frames.
    
    Key Features:
        - Priority-based state transitions
        - Invincibility frames (i-frames) during HURT state
        - Frame-accurate attack windows with configurable hitboxes
        - Multi-hit prevention (targets can only be hit once per attack)
        - Extensible state configuration system
    
    Combat Integration:
        External collision systems should query the player's attack state
        using the provided methods rather than accessing internal state:
        
        - should_deal_damage() → Check if player can currently deal damage
        - get_attack_hitbox() → Get the active hitbox rect for collision
        - try_register_hit(id) → Register a hit (prevents duplicates)
        - get_current_attack_damage() → Get damage for current frame
        - get_attack_knockback(pos) → Get knockback vector for target
    
    Attributes:
        health: Current health points.
        max_health: Maximum health capacity.
        is_dead: Whether player has been defeated.
        is_attacking: Whether player is in an attack state.
        is_running: Whether player is moving horizontally.
        is_invincible: Whether player is immune to damage.
    """
    
    # ─────────────────────────────────────────────────────────────────────────
    # State Configuration Registry
    # ─────────────────────────────────────────────────────────────────────────
    
    _STATE_CONFIGS: Final[dict[PlayerState, StateConfig]] = {
        PlayerState.DEATH: StateConfig(
            animation_speed=0.15,
            loops=False,
            next_state=None,
            interruptible=False,
            grants_invincibility=True,
            locks_movement=True,
            locks_input=True,
        ),
        PlayerState.HURT: StateConfig(
            animation_speed=0.20,
            loops=False,
            next_state=PlayerState.IDLE,
            interruptible=False,
            grants_invincibility=True,
            locks_movement=True,
            locks_input=True,
        ),
        PlayerState.ATTACK_THRUST: StateConfig(
            animation_speed=0.24,
            loops=False,
            next_state=PlayerState.IDLE,
            interruptible=False,
            grants_invincibility=False,
            locks_movement=True,
            locks_input=False,
        ),
        PlayerState.ATTACK_SMASH: StateConfig(
            animation_speed=0.24,
            loops=False,
            next_state=PlayerState.IDLE,
            interruptible=False,
            grants_invincibility=False,
            locks_movement=True,
            locks_input=False,
        ),
        PlayerState.JUMP_UP: StateConfig(
            animation_speed=0.27,
            loops=True,
            interruptible=True,
            grants_invincibility=False,
            locks_movement=False,
        ),
        PlayerState.JUMP_DOWN: StateConfig(
            animation_speed=0.27,
            loops=True,
            interruptible=True,
            grants_invincibility=False,
            locks_movement=False,
        ),
        PlayerState.RUN: StateConfig(
            animation_speed=0.27,
            loops=True,
            interruptible=True,
            grants_invincibility=False,
            locks_movement=False,
        ),
        PlayerState.IDLE: StateConfig(
            animation_speed=0.27,
            loops=True,
            interruptible=True,
            grants_invincibility=False,
            locks_movement=False,
        ),
    }

    # ─────────────────────────────────────────────────────────────────────────
    # Attack Configurations (Frame-Based Combat)
    # ─────────────────────────────────────────────────────────────────────────
    #
    # Each attack type has a static configuration defining:
    # - Which frames deal damage (hit_frames)
    # - Base damage and knockback values
    # - Per-frame hitbox positions and sizes
    # - Per-frame damage modifiers (optional)
    #
    # Frame indices are 0-based and correspond to the animation frames.
    # Adjust these values based on your actual sprite animations.
    #

    # Thrust Attack (9 frames total)
    # Fast single-hit attack with forward reach
    # Active frames: 3-4 (wind-up on 0-2, recovery on 5-8)
    THRUST_ATTACK_CONFIG: Final[AttackConfig] = AttackConfig(
        hit_frames=frozenset({3,}),
        base_damage=15.0,
        knockback_force=8.0,
        knockback_angle=30.0,  # Slightly upward knockback
        hit_stop_frames=3,
        can_hit_multiple=True,
        max_hits_per_target=1,
        frame_damage_modifiers={
            3: 0.5,   # Early hit - 80% damage
        },
        hitbox_data={
            3: HitboxData(offset_x=60, offset_y=0, width=70, height=50),
        },
        startup_frames=frozenset({0, 1, 2}),
        recovery_frames=frozenset({5, 6, 7, 8}),
    )

    # Smash Attack (17 frames total)
    # Slow multi-hit attack with high damage
    # Active frames: 5-7 (first hit), 10-12 (second hit)
    SMASH_ATTACK_CONFIG: Final[AttackConfig] = AttackConfig(
        hit_frames=frozenset({3, 7, 11,}),
        base_damage=25.0,
        knockback_force=15.0,
        knockback_angle=45.0,  # Strong upward knockback
        hit_stop_frames=5,
        can_hit_multiple=True,
        max_hits_per_target=2,  # Can hit twice (two swing phases)
        frame_damage_modifiers={
            3: 0.3,   # First swing start
            7: 0.5,   # First swing end
            11: 0.2,  # Second swing peak - bonus damage!
        },
        hitbox_data={
            # First swing - overhead arc
            3: HitboxData(offset_x=40, offset_y=-30, width=80, height=70),
            7: HitboxData(offset_x=50, offset_y=10, width=90, height=70),
            # Second swing - horizontal sweep
            11: HitboxData(offset_x=70, offset_y=0, width=120, height=70),
        },
        startup_frames=frozenset({0, 1, 2, 3, 4}),
        recovery_frames=frozenset({13, 14, 15, 16}),
    )
    
    # Physics constants
    _GRAVITY_ACCELERATION: Final[float] = 0.8
    _JUMP_VELOCITY: Final[float] = -22  # Reduced from -29.0 to make jumps lower
    _GROUND_OFFSET: Final[int] = 34
    _AIRBORNE_THRESHOLD: Final[int] = 230
    
    # Movement constants
    _MOVE_SPEED: Final[float] = 3.4
    _AIR_MOVE_SPEED: Final[float] = 5.0  # Reduced speed while in the air
    _SCREEN_BOUND_LEFT: Final[int] = 0
    _SCREEN_BOUND_RIGHT: Final[int] = 1600
    
    _SMASH_AUDIO_FRAME_SOUNDS: Final[dict[int, str]] = {
        3: "smash_phase_1",
        7: "smash_phase_2",
        11: "smash_phase_3",
    }
    
    def __init__(self, x: int, y: int, audio_manager: AudioManager) -> None:
        """
        Initialize the player entity.
        
        Args:
            x: Initial x position in world coordinates.
            y: Initial y position in world coordinates.
            audio_manager: Audio system for playing sound effects.
        """
        super().__init__(x, y)
        
        self._audio_manager: AudioManager = audio_manager
        
        # Load all animation frame sets
        self._load_all_animations()
        
        # State machine
        self._state: PlayerState = PlayerState.IDLE
        self._current_frames: list[pg.Surface] = self._idle_frames
        self._animation_index: float = 0.0
        
        # Combat state - frame-based attack system
        self._attack_state: AttackState = AttackState()
        self._current_attack_config: Optional[AttackConfig] = None
        self._attack_audio_frames_played: set[int] = set()
        
        # Invincibility tracking (extends beyond HURT state if needed)
        self._invincibility_timer: float = 0.0
        self._invincibility_duration: float = 0.0

        # Footstep audio controller for run state
        self._footsteps = FootstepController(
            audio_manager=self._audio_manager,
            sound_name="footstep",
            interval_ms=170,
            volume=0.85,
        )
        
        # Sprite setup
        self.image: pg.Surface = self._current_frames[0]
        self.rect: pg.Rect = self.image.get_rect(midtop=(x, y))
        self._spawn_midtop: tuple[int, int] = self.rect.midtop
        self.adjust_hitbox_sides(left=315, right=315, top=150, bottom=0)
        
        # Physics state
        self._gravity: float = 0.0
        self._ground_y: int = pg.display.Info().current_h - self._GROUND_OFFSET
        
        # Movement state
        self._direction: int = 0
        self._facing_left: bool = False
        
        # Combat state
        self._max_health: int = 100
        self._health: int = self._max_health
        
        # Entity ID for combat system (used by hit registration)
        self._entity_id: int = id(self)
        
    def _load_all_animations(self) -> None:
        """
        Load all animation frame sets.
        
        Frame sets are stored as private attributes named `_<state>_frames`.
        Add new animation loads here when implementing new states.
        """
        # Base animations
        self._idle_frames = self._load_frames(
            "assets/shadow_warrior/idle/idle_{}.png", 12, start_index=1
        )
        self._run_frames = self._load_frames(
            "assets/shadow_warrior/run/run_{}.png", 10, start_index=1
        )
        
        # Aerial animations
        self._jump_up_frames = self._load_frames(
            "assets/shadow_warrior/jump_up_loop/jump_up_loop_{}.png", 3, start_index=1
        )
        self._jump_down_frames = self._load_frames(
            "assets/shadow_warrior/jump_down_loop/jump_down_loop_{}.png", 3, start_index=1
        )
        
        # Attack animations
        self._thrust_frames = self._load_frames(
            "assets/shadow_warrior/1_atk/1_atk_{}.png", 9, start_index=1
        )
        self._smash_frames = self._load_frames(
            "assets/shadow_warrior/2_atk/2_atk_{}.png", 17, start_index=1
        )
        
        # Reactive animations
        self._hurt_frames = self._load_frames(
            "assets/shadow_warrior/take_hit/take_hit_{}.png", 6, start_index=1
        )
        self._death_frames = self._load_frames(
            "assets/shadow_warrior/death/death_{}.png", 12, start_index=1
        )
    
    def _load_frames(
        self,
        path_pattern: str,
        count: int,
        start_index: int = 0,
        scale_factor: int = 3,
    ) -> list[pg.Surface]:
        """
        Load and scale animation frames from a file pattern.
        
        Args:
            path_pattern: Format string with {} placeholder for frame index.
            count: Number of frames to load.
            start_index: Starting index for frame numbering.
            scale_factor: Sprite scale multiplier.
            
        Returns:
            List of scaled pygame Surface objects.
        """
        frames: list[pg.Surface] = []
        
        for i in range(start_index, start_index + count):
            path = path_pattern.format(i)
            try:
                frame = AssetManager.get_texture(path)
                original_size = frame.get_size()
                scaled_size = (
                    original_size[0] * scale_factor,
                    original_size[1] * scale_factor,
                )
                scaled_frame = pg.transform.scale(frame, scaled_size)
                frames.append(scaled_frame)
            except (FileNotFoundError, pg.error) as e:
                print(f"Warning: Failed to load frame '{path}': {e}")
                
        return frames
    
    # ─────────────────────────────────────────────────────────────────────────
    # Public Properties
    # ─────────────────────────────────────────────────────────────────────────
    
    @property
    def entity_id(self) -> int:
        """Unique identifier for this entity (used by combat system)."""
        return self._entity_id
    
    @property
    def state(self) -> PlayerState:
        """Current state of the player state machine."""
        return self._state
    
    @property
    def current_frame_index(self) -> int:
        """Current animation frame index (0-based)."""
        return int(self._animation_index)
    
    @property
    def health(self) -> int:
        """Current health points."""
        return self._health
    
    @property
    def max_health(self) -> int:
        """Maximum health capacity."""
        return self._max_health
    
    @property
    def is_dead(self) -> bool:
        """Whether the player has been defeated."""
        return self._state == PlayerState.DEATH
    
    @property
    def is_attacking(self) -> bool:
        """Whether the player is in an attack state."""
        return self._state in (PlayerState.ATTACK_THRUST, PlayerState.ATTACK_SMASH)
    
    @property
    def is_running(self) -> bool:
        """Whether the player is moving horizontally."""
        return self._state == PlayerState.RUN and self._direction != 0
    
    @property
    def is_invincible(self) -> bool:
        """
        Whether the player is immune to damage.
        
        Returns True if:
        - Current state grants invincibility (e.g., HURT, DEATH)
        - Invincibility timer is active (extended i-frames)
        """
        config = self._STATE_CONFIGS.get(self._state)
        if config and config.grants_invincibility:
            return True
        return self._invincibility_timer > 0
    
    @property
    def is_hurt(self) -> bool:
        """Whether the player is in the hurt/stagger state."""
        return self._state == PlayerState.HURT
    
    @property
    def direction(self) -> int:
        """Current horizontal direction (-1=left, 0=none, 1=right)."""
        return self._direction
    
    @property
    def facing_left(self) -> bool:
        """Whether the player sprite is facing left."""
        return self._facing_left
    
    @property
    def attack_phase(self) -> AttackPhase:
        """Current phase of the active attack."""
        return self._attack_state.get_current_phase()
    
    # ─────────────────────────────────────────────────────────────────────────
    # Combat System Public Interface
    # ─────────────────────────────────────────────────────────────────────────
    #
    # These methods provide a clean interface for external collision systems
    # to interact with the player's combat state. Use these methods instead
    # of accessing internal state directly.
    #
    
    def should_deal_damage(self) -> bool:
        """
        Check if the player can currently deal damage.
        
        Returns True only if:
        - Player is in an attack state
        - Current animation frame is a hit frame
        - Attack state is active and not in hit stop
        
        External collision systems should call this before processing
        attack collisions.
        
        Returns:
            True if damage should be checked this frame.
            
        Example:
            >>> if player.should_deal_damage():
            ...     hitbox = player.get_attack_hitbox()
            ...     for enemy in enemies:
            ...         if hitbox.colliderect(enemy.hitbox):
            ...             # Process hit
        """
        if not self.is_attacking:
            return False
        
        return self._attack_state.is_hit_frame_active()
    
    def get_attack_hitbox(self) -> Optional[pg.Rect]:
        """
        Get the active attack hitbox for collision detection.
        
        Returns None if no attack is active or current frame
        is not a hit frame.
        
        The hitbox position is automatically adjusted based on
        the player's facing direction.
        
        Returns:
            Pygame Rect for collision detection, or None.
            
        Example:
            >>> hitbox = player.get_attack_hitbox()
            >>> if hitbox and hitbox.colliderect(enemy.rect):
            ...     # Hit detected
        """
        if not self.should_deal_damage():
            return None
        
        return self._attack_state.get_current_hitbox(
            self.rect, self._facing_left
        )
    
    def try_register_hit(self, target_id: int) -> bool:
        """
        Attempt to register a hit on a target entity.
        
        This method prevents duplicate hits - a target can only be
        hit a limited number of times per attack (defined by the
        attack configuration's max_hits_per_target).
        
        Args:
            target_id: Unique identifier for the target entity.
            
        Returns:
            True if hit was registered and damage should be applied.
            False if target was already hit or hit frame not active.
            
        Example:
            >>> if player.try_register_hit(enemy.entity_id):
            ...     damage = player.get_current_attack_damage()
            ...     enemy.take_damage(damage)
        """
        return self._attack_state.try_register_hit(target_id)
    
    def get_current_attack_damage(self) -> float:
        """
        Get the damage value for the current attack frame.
        
        Returns the base damage multiplied by any frame-specific
        damage modifiers (e.g., sweet spot frames deal more damage).
        
        Returns:
            Damage value for the current frame, or 0 if not attacking.
        """
        return self._attack_state.get_current_damage()

    def get_current_attack_frame(self) -> Optional[int]:
        """Return the current animation frame index for the active attack."""
        if not self._attack_state.is_active:
            return None
        return self._attack_state.current_frame

    def get_attack_knockback(
        self,
        target_position: tuple[float, float],
    ) -> tuple[float, float]:
        """
        Calculate knockback vector for a hit target.
        
        The knockback direction is determined by the attack configuration:
        - If knockback_angle is set, uses that fixed angle
        - Otherwise, calculates direction from player to target
        
        Args:
            target_position: Target's center position (x, y).
            
        Returns:
            Knockback vector as (x, y) tuple.
        """
        return self._attack_state.get_knockback_vector(
            self.rect.center,
            target_position,
            self._facing_left,
        )
    
    def get_attack_knockback_force(self) -> float:
        """
        Get the raw knockback force magnitude for the current attack.
        
        Returns:
            Knockback force value, or 0 if not attacking.
        """
        return self._attack_state.get_knockback_force()
    
    def has_hit_target(self, target_id: int) -> bool:
        """
        Check if a target has been hit during the current attack.
        
        Args:
            target_id: Unique identifier for the target entity.
            
        Returns:
            True if target has been hit at least once.
        """
        return self._attack_state.has_hit_target(target_id)
    
    def get_hit_count(self, target_id: int) -> int:
        """
        Get the number of times a target has been hit this attack.
        
        Args:
            target_id: Unique identifier for the target entity.
            
        Returns:
            Number of registered hits.
        """
        return self._attack_state.get_hit_count(target_id)
    
    def process_attack_collisions(
        self,
        targets: list[tuple[int, pg.Rect]],
    ) -> list[HitResult]:
        """
        Process attack collisions against multiple targets.
        
        This is a convenience method that handles the full collision
        processing pipeline: hitbox generation, collision detection,
        hit registration, and damage calculation.
        
        Args:
            targets: List of (entity_id, bounding_rect) tuples.
            
        Returns:
            List of HitResult for each successful hit. Apply these
            results to the target entities.
            
        Example:
            >>> targets = [(e.entity_id, e.rect) for e in enemies]
            >>> hits = player.process_attack_collisions(targets)
            >>> for hit in hits:
            ...     enemy = get_entity(hit.target_id)
            ...     enemy.take_damage(hit.damage, hit.knockback)
        """
        return CombatProcessor.process_attack_against_targets(
            attack_state=self._attack_state,
            attacker_rect=self.rect,
            attacker_facing_left=self._facing_left,
            targets=targets,
        )
    
    # ─────────────────────────────────────────────────────────────────────────
    # State Machine Core
    # ─────────────────────────────────────────────────────────────────────────
    
    def _get_current_config(self) -> StateConfig:
        """Get configuration for the current state."""
        return self._STATE_CONFIGS.get(self._state, StateConfig())
    
    def _can_transition_to(self, target_state: PlayerState) -> bool:
        """
        Check if transition to target state is allowed.
        
        Transition rules:
        1. Cannot transition to same state
        2. Higher priority (lower enum value) always wins
        3. Current state must be interruptible OR target has higher priority
        
        Args:
            target_state: State to potentially transition to.
            
        Returns:
            True if transition is allowed, False otherwise.
        """
        if target_state == self._state:
            return False
            
        current_config = self._get_current_config()
        
        # Higher priority states can always interrupt
        if target_state.value < self._state.value:
            return True
            
        # Otherwise, current state must be interruptible
        return current_config.interruptible
    
    def _transition_to(self, new_state: PlayerState) -> None:
        """
        Execute state transition with animation reset.
        
        Args:
            new_state: State to transition to.
        """
        # End any active attack when leaving attack states
        if self.is_attacking and new_state not in (
            PlayerState.ATTACK_THRUST,
            PlayerState.ATTACK_SMASH,
        ):
            self._attack_state.end()
            self._current_attack_config = None

        if new_state != PlayerState.RUN:
            self._footsteps.reset()

        self._state = new_state
        self._animation_index = 0.0
        
        # Map states to their frame sets
        frame_mapping: dict[PlayerState, list[pg.Surface]] = {
            PlayerState.IDLE: self._idle_frames,
            PlayerState.RUN: self._run_frames,
            PlayerState.JUMP_UP: self._jump_up_frames,
            PlayerState.JUMP_DOWN: self._jump_down_frames,
            PlayerState.ATTACK_THRUST: self._thrust_frames,
            PlayerState.ATTACK_SMASH: self._smash_frames,
            PlayerState.HURT: self._hurt_frames,
            PlayerState.DEATH: self._death_frames,
        }
        
        self._current_frames = frame_mapping.get(new_state, self._idle_frames)
    
    def _advance_animation(self) -> bool:
        """
        Advance animation frame based on current state's speed.
        
        Also updates attack state frame tracking when in attack states.
        
        Returns:
            True if animation completed (reached end of non-looping animation),
            False otherwise.
        """
        config = self._get_current_config()
        
        # Check for hit stop pause
        if self._attack_state.is_in_hit_stop:
            self._attack_state.update(self.current_frame_index)
            return False
        
        self._animation_index += config.animation_speed
        
        # Sync attack state with animation frame
        if self.is_attacking:
            self._attack_state.update(self.current_frame_index)
        
        if self._animation_index >= len(self._current_frames):
            if config.loops:
                self._animation_index = 0.0
                return False
            else:
                # Hold on last frame for non-looping animations
                self._animation_index = len(self._current_frames) - 1
                return True
                
        return False
    
    # ─────────────────────────────────────────────────────────────────────────
    # Public Actions (Call these to trigger state changes)
    # ─────────────────────────────────────────────────────────────────────────
    
    def take_damage(self, amount: float) -> bool:
        """
        Apply damage to the player.
        
        Triggers HURT state if damage is applied, or DEATH state if
        health is depleted. Respects invincibility frames.
        
        Args:
            amount: Damage points to apply.
            
        Returns:
            True if damage was applied, False if blocked by invincibility.
            
        Example:
            >>> if skeleton.should_deal_damage():
            ...     if player.take_damage(skeleton.get_current_attack_damage()):
            ...         skeleton.register_hit()
        """
        # Check invincibility
        if self.is_invincible:
            return False
            
        # Apply damage
        self._health = max(0, self._health - int(amount))
        
        # Determine resulting state
        if self._health <= 0:
            self._transition_to(PlayerState.DEATH)
            self._audio_manager.play_sound("death")
        else:
            self._transition_to(PlayerState.HURT)
            self._audio_manager.play_sound("player_hurt")
            
            # Grant extended i-frames after hurt animation
            self._invincibility_duration = 0.3
            
        return True
    
    def attack_thrust(self) -> bool:
        """
        Initiate thrust attack.
        
        Begins the thrust attack animation and initializes the
        attack state with the thrust configuration. Damage will
        only be dealt on the configured hit frames.
        
        Returns:
            True if attack started, False if blocked by current state.
        """
        if not self._can_transition_to(PlayerState.ATTACK_THRUST):
            return False
            
        self._transition_to(PlayerState.ATTACK_THRUST)
        
        # Initialize attack state with thrust configuration
        self._attack_state.begin(self.THRUST_ATTACK_CONFIG)
        self._current_attack_config = self.THRUST_ATTACK_CONFIG
        self._attack_audio_frames_played.clear()
        self._audio_manager.play_sound("thrust")
        return True
    
    def attack_smash(self) -> bool:
        """
        Initiate smash attack.
        
        Begins the smash attack animation and initializes the
        attack state with the smash configuration. This is a
        multi-hit attack that can hit targets twice.
        
        Returns:
            True if attack started, False if blocked by current state.
        """
        if not self._can_transition_to(PlayerState.ATTACK_SMASH):
            return False
            
        self._transition_to(PlayerState.ATTACK_SMASH)
        
        # Initialize attack state with smash configuration
        self._attack_state.begin(self.SMASH_ATTACK_CONFIG)
        self._current_attack_config = self.SMASH_ATTACK_CONFIG
        self._attack_audio_frames_played.clear()
        self._audio_manager.play_sound("smash")
        return True

    def set_footstep_volume(self, volume: float) -> None:
        """Set absolute footstep volume for future customization."""
        self._footsteps.set_volume(volume)

    def increase_footstep_volume(self, delta: float) -> None:
        """Adjust current footstep volume relatively."""
        self._footsteps.increase_volume(delta)
    
    def jump(self) -> bool:
        """
        Initiate jump.
        
        Returns:
            True if jump started, False if not grounded or blocked.
        """
        # Must be on ground
        if self.rect.bottom < self._ground_y - self._AIRBORNE_THRESHOLD:
            return False
            
        if not self._can_transition_to(PlayerState.JUMP_UP):
            return False
            
        self._gravity = self._JUMP_VELOCITY
        self._transition_to(PlayerState.JUMP_UP)
        self._audio_manager.play_sound("jump_grunt")
        self._audio_manager.play_sound("jump")
        return True
    
    def grant_invincibility(self, duration: float) -> None:
        """
        Grant temporary invincibility.
        
        Args:
            duration: Invincibility duration in seconds.
        """
        self._invincibility_timer = max(self._invincibility_timer, duration)

    def set_spawn_point(
        self,
        *,
        midtop: Optional[tuple[int, int]] = None,
        midbottom: Optional[tuple[int, int]] = None,
    ) -> None:
        """Update spawn location and reposition player accordingly."""
        if midtop is not None:
            self.rect.midtop = midtop
        elif midbottom is not None:
            self.rect.midbottom = midbottom
        self._spawn_midtop = self.rect.midtop

    def reset(self) -> None:
        """Restore player to initial spawn state for retries/game over."""
        self._health = self._max_health
        self._state = PlayerState.IDLE
        self._current_frames = self._idle_frames
        self._animation_index = 0.0
        self._attack_state = AttackState()
        self._current_attack_config = None
        self._invincibility_timer = 0.0
        self._invincibility_duration = 0.0
        self._direction = 0
        self._facing_left = False
        self._gravity = 0.0
        self.rect.midtop = self._spawn_midtop
        self._footsteps.reset()
    
    # ─────────────────────────────────────────────────────────────────────────
    # Input Handling
    # ─────────────────────────────────────────────────────────────────────────
    
    def player_input(self) -> None:
        """Process player input and update movement/action state."""
        config = self._get_current_config()
        
        # Input locked during certain states
        if config.locks_input:
            return
            
        keys = pg.key.get_pressed()
        joystick = self._get_joystick()
        
        # Movement input (only if not locked)
        if not config.locks_movement:
            self._process_movement_input(keys, joystick)
        
        # Action input
        self._process_action_input(keys, joystick)
    
    def _get_joystick(self) -> Optional[pg.joystick.JoystickType]:
        """Get the first connected joystick, if any."""
        if pg.joystick.get_count() > 0:
            return pg.joystick.Joystick(0)
        return None
    
    def _process_movement_input(
        self,
        keys: pg.key.ScancodeWrapper,
        joystick: Optional[pg.joystick.JoystickType],
    ) -> None:
        """Process horizontal movement input."""
        # Determine direction from input
        move_left = keys[pg.K_LEFT] or (joystick and joystick.get_axis(0) < -0.5)
        move_right = keys[pg.K_RIGHT] or (joystick and joystick.get_axis(0) > 0.5)
        
        if move_left:
            self._direction = -1
            self._facing_left = True
        elif move_right:
            self._direction = 1
            self._facing_left = False
        else:
            self._direction = 0
    
    def _process_action_input(
        self,
        keys: pg.key.ScancodeWrapper,
        joystick: Optional[pg.joystick.JoystickType],
    ) -> None:
        """Process action button input (jump, attacks)."""
        # Jump
        jump_pressed = (
            keys[pg.K_SPACE] or
            (joystick and joystick.get_button(0)) or
            (joystick and abs(joystick.get_axis(1)) > 0.5)
        )
        if jump_pressed:
            self.jump()
        
        # Thrust attack (Q or gamepad button 2)
        if keys[pg.K_q] or (joystick and joystick.get_button(2)):
            self.attack_thrust()
        
        # Smash attack (E or gamepad button 1)
        if keys[pg.K_e] or (joystick and joystick.get_button(1)):
            self.attack_smash()
    
    # ─────────────────────────────────────────────────────────────────────────
    # Physics
    # ─────────────────────────────────────────────────────────────────────────
    
    def _apply_gravity(self) -> None:
        """Apply gravitational acceleration and ground collision."""
        self._gravity += self._GRAVITY_ACCELERATION
        self.rect.y += int(self._gravity)
        
        # Ground collision
        if self.rect.bottom >= self._ground_y:
            self.rect.bottom = self._ground_y
            self._gravity = 0.0
    
    def _apply_movement(self) -> None:
        """Apply horizontal movement with screen boundary clamping."""
        if self._direction == 0:
            return
            
        # Use different speeds for ground and air movement
        if self.rect.bottom >= self._ground_y - 1:  # On ground
            move_speed = self._MOVE_SPEED
        else:  # In air
            move_speed = self._AIR_MOVE_SPEED
            
        self.rect.x += int(self._direction * move_speed)
        
        # Clamp to screen bounds
        self.rect.left = max(self.rect.left, self._SCREEN_BOUND_LEFT)
        self.rect.right = min(self.rect.right, self._SCREEN_BOUND_RIGHT)
    
    def _update_invincibility(self, dt: float) -> None:
        """
        Update invincibility timer.
        
        Args:
            dt: Delta time in seconds.
        """
        if self._invincibility_timer > 0:
            self._invincibility_timer = max(0, self._invincibility_timer - dt)
    
    # ─────────────────────────────────────────────────────────────────────────
    # Animation State Handlers
    # ─────────────────────────────────────────────────────────────────────────
    
    def _animate_death(self) -> None:
        """Handle DEATH state animation."""
        self._advance_animation()
    
    def _animate_hurt(self) -> None:
        """Handle HURT state animation."""
        completed = self._advance_animation()
        
        if completed:
            self._invincibility_timer = self._invincibility_duration
            self._transition_to(PlayerState.IDLE)
    
    def _animate_attack_thrust(self) -> None:
        """Handle ATTACK_THRUST state animation."""
        completed = self._advance_animation()
        
        if completed:
            self._attack_state.end()
            self._transition_to_movement_state()
    
    def _animate_attack_smash(self) -> None:
        """Handle ATTACK_SMASH state animation."""
        completed = self._advance_animation()
        self._trigger_attack_audio_cues()
        
        if completed:
            self._attack_state.end()
            self._transition_to_movement_state()

    def _trigger_attack_audio_cues(self) -> None:
        """Play smash attack sound cues tied to animation frames."""
        if self._state != PlayerState.ATTACK_SMASH:
            return
        frame = self.current_frame_index
        if frame in self._attack_audio_frames_played:
            return
        sound_name = self._SMASH_AUDIO_FRAME_SOUNDS.get(frame)
        if sound_name is None:
            return
        self._audio_manager.play_sound(sound_name)
        self._attack_audio_frames_played.add(frame)
    
    def _animate_jump_up(self) -> None:
        """Handle JUMP_UP state animation."""
        self._advance_animation()
        
        if self._gravity >= 0:
            self._transition_to(PlayerState.JUMP_DOWN)
    
    def _animate_jump_down(self) -> None:
        """Handle JUMP_DOWN state animation."""
        self._advance_animation()
        
        if self.rect.bottom >= self._ground_y:
            self._transition_to_movement_state()
    
    def _animate_run(self) -> None:
        """Handle RUN state animation."""
        self._advance_animation()

        grounded = self.rect.bottom >= self._ground_y - 1
        active = grounded and self._direction != 0
        self._footsteps.try_play(
            active=active,
            current_time_ms=pg.time.get_ticks(),
        )

        if self._direction == 0:
            self._transition_to(PlayerState.IDLE)
        
        if self.rect.bottom < self._ground_y - self._AIRBORNE_THRESHOLD:
            self._transition_to(PlayerState.JUMP_DOWN)
    
    def _animate_idle(self) -> None:
        """Handle IDLE state animation."""
        self._advance_animation()
        
        if self._direction != 0:
            self._transition_to(PlayerState.RUN)
        
        if self.rect.bottom < self._ground_y - self._AIRBORNE_THRESHOLD:
            self._transition_to(PlayerState.JUMP_DOWN)
    
    def _transition_to_movement_state(self) -> None:
        """Transition to appropriate movement state based on current conditions."""
        if self.rect.bottom < self._ground_y - self._AIRBORNE_THRESHOLD:
            if self._gravity < 0:
                self._transition_to(PlayerState.JUMP_UP)
            else:
                self._transition_to(PlayerState.JUMP_DOWN)
        elif self._direction != 0:
            self._transition_to(PlayerState.RUN)
        else:
            self._transition_to(PlayerState.IDLE)
    
    def _update_animation(self) -> None:
        """Update animation based on current state."""
        match self._state:
            case PlayerState.DEATH:
                self._animate_death()
            case PlayerState.HURT:
                self._animate_hurt()
            case PlayerState.ATTACK_THRUST:
                self._animate_attack_thrust()
            case PlayerState.ATTACK_SMASH:
                self._animate_attack_smash()
            case PlayerState.JUMP_UP:
                self._animate_jump_up()
            case PlayerState.JUMP_DOWN:
                self._animate_jump_down()
            case PlayerState.RUN:
                self._animate_run()
            case PlayerState.IDLE:
                self._animate_idle()
        
        self._apply_frame()
    
    def _apply_frame(self) -> None:
        """Apply current animation frame to sprite image."""
        frame_index = min(
            int(self._animation_index),
            len(self._current_frames) - 1,
        )
        self.image = self._current_frames[frame_index]
        
        if self._facing_left:
            self.image = pg.transform.flip(self.image, True, False)
        
        # Visual feedback for invincibility
        if self.is_invincible and self._state != PlayerState.HURT:
            if int(self._animation_index * 10) % 2 == 0:
                self.image.set_alpha(128)
            else:
                self.image.set_alpha(255)
        else:
            self.image.set_alpha(255)
    
    # ─────────────────────────────────────────────────────────────────────────
    # Debug Support
    # ─────────────────────────────────────────────────────────────────────────
    
    def get_debug_info(self) -> dict:
        """
        Get debug information about player state.
        
        Useful for development debugging and state visualization.
        
        Returns:
            Dictionary containing player state details.
        """
        return {
            "state": self._state.name,
            "frame": self.current_frame_index,
            "health": f"{self._health}/{self._max_health}",
            "position": (self.rect.x, self.rect.y),
            "is_attacking": self.is_attacking,
            "is_invincible": self.is_invincible,
            "attack_info": self._attack_state.get_debug_info(),
        }
    
    def draw_debug_hitboxes(self, surface: pg.Surface) -> None:
        """
        Draw debug visualization of attack hitboxes.
        
        Draws the current attack hitbox in red if active.
        
        Args:
            surface: Surface to draw on.
        """
        if self.should_deal_damage():
            hitbox = self.get_attack_hitbox()
            if hitbox:
                pg.draw.rect(surface, (255, 0, 0), hitbox, 2)
    
    # ─────────────────────────────────────────────────────────────────────────
    # Main Update Loop
    # ─────────────────────────────────────────────────────────────────────────
    
    def update(self, dt: Optional[float] = None) -> None:
        """
        Update player state for the current frame.
        
        Args:
            dt: Delta time in seconds (defaults to 1/60 if not provided).
        """
        if dt is None:
            dt = 1.0 / 60.0
        
        self.player_input()
        self._apply_gravity()
        self._apply_movement()
        self._update_animation()
        self._update_invincibility(dt)
        
        super().update(dt)