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

from v3x_zulfiqar_gideon.asset_manager import AssetManager
from v3x_zulfiqar_gideon.ecs import Actor
from v3x_zulfiqar_gideon.audio_manager import FootstepController
from v3x_zulfiqar_gideon.combat import (
    AttackConfig,
    AttackState,
    AttackPhase,
    HitboxData,
    HitResult,
    CombatProcessor,
)

if TYPE_CHECKING:
    from v3x_zulfiqar_gideon.audio_manager import AudioManager


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
    DEFEND = 8
    
    # Reactive states
    HURT = 10
    
    # Action states
    ATTACK_THRUST = 20
    ATTACK_SMASH = 21
    ATTACK_POWER = 22
    
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


class Player(Actor):
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
        PlayerState.DEFEND: StateConfig(
            animation_speed=0.24,
            loops=False,
            next_state=PlayerState.IDLE,
            interruptible=False,
            grants_invincibility=True,
            locks_movement=True,
            locks_input=False,
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
        PlayerState.ATTACK_POWER: StateConfig(
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
            3: HitboxData(offset_x=180, offset_y=30, width=250, height=100),
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
        max_hits_per_target=3,  # Can hit twice (two swing phases)
        frame_damage_modifiers={
            3: 0.3,   # First swing start
            7: 0.5,   # First swing end
            11: 0.2,  # Second swing peak - bonus damage!
        },
        hitbox_data={
            # First swing - overhead arc
            3: HitboxData(offset_x=180, offset_y=30, width=250, height=100),
            7: HitboxData(offset_x=180, offset_y=20, width=270, height=200),
            # Second swing - horizontal sweep
            11: HitboxData(offset_x=180, offset_y=20, width=240, height=200),
        },
        startup_frames=frozenset({0, 1, 2, 3}),
        recovery_frames=frozenset({13, 14, 15, 16}),
    )

    # Power attack (23 frames total)
    # Slow multi-hit attack with high damage
    # Active frames: 5-7 (first hit), 10-12 (second hit)
    POWER_ATTACK_CONFIG: Final[AttackConfig] = AttackConfig(
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
            16: 0.2,
            17: 0.1,
            18: 0.1,
            19: 0.1,
            20: 0.8,
        },
        hitbox_data={
            # First swing - overhead arc
            3: HitboxData(offset_x=40, offset_y=-30, width=80, height=70),
            7: HitboxData(offset_x=50, offset_y=10, width=90, height=70),
            # Second swing - horizontal sweep
            11: HitboxData(offset_x=70, offset_y=0, width=120, height=70),
            16: HitboxData(offset_x=70, offset_y=0, width=120, height=70),
            17: HitboxData(offset_x=70, offset_y=0, width=120, height=70),
            18: HitboxData(offset_x=70, offset_y=0, width=120, height=70),
            19: HitboxData(offset_x=70, offset_y=0, width=120, height=70),
            20: HitboxData(offset_x=70, offset_y=0, width=120, height=70),
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
    
    _ATTACK_AUDIO_FRAME_SOUNDS: Final[dict[int, str]] = {
        PlayerState.ATTACK_SMASH: {
            3: "smash_phase_1",
            7: "smash_phase_2",
            11: "smash_phase_3",
        },
        PlayerState.ATTACK_POWER: {
            3: "smash_phase_1",
            7: "smash_phase_2",
            11: "smash_phase_3",
            16: "power_release_1",
            17: "power_release_2",
            18: "power_release_3",
            19: "power_release_4",
            20: "power_release_5",
        }
    }
    
    def __init__(self, x: int, y: int, audio_manager: AudioManager) -> None:
        super().__init__(x, y)
        
        self._audio_manager: AudioManager = audio_manager
        
        # State machine configuration (from static registry)
        self.state_configs = self._STATE_CONFIGS
        
        # Load all animation frame sets
        self._load_all_animations()
        
        self.set_state(PlayerState.IDLE)
        
        # Combat state
        self._attack_audio_frames_played: set[int] = set()

        # Defend animation phase tracking
        self._defend_releasing: bool = False
        
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
        self.facing_left: bool = False
        
        # Combat state
        self._max_health: int = 100
        self._health: int = self._max_health
        
        # Entity ID for combat system (used by hit registration)
        self._entity_id: int = id(self)

        # Add this line with other state variables
        self._defend_handled = False  
        
    def _load_all_animations(self) -> None:
        self.animations[PlayerState.IDLE] = self._load_frames(
            "assets/shadow_warrior/idle/idle_{}.png", 12, start_index=1
        )
        self.animations[PlayerState.RUN] = self._load_frames(
            "assets/shadow_warrior/run/run_{}.png", 10, start_index=1
        )
        self.animations[PlayerState.JUMP_UP] = self._load_frames(
            "assets/shadow_warrior/jump_up_loop/jump_up_loop_{}.png", 3, start_index=1
        )
        self.animations[PlayerState.JUMP_DOWN] = self._load_frames(
            "assets/shadow_warrior/jump_down_loop/jump_down_loop_{}.png", 3, start_index=1
        )
        self.animations[PlayerState.ATTACK_THRUST] = self._load_frames(
            "assets/shadow_warrior/1_atk/1_atk_{}.png", 9, start_index=1
        )
        self.animations[PlayerState.ATTACK_SMASH] = self._load_frames(
            "assets/shadow_warrior/2_atk/2_atk_{}.png", 17, start_index=1
        )
        self.animations[PlayerState.ATTACK_POWER] = self._load_frames(
            "assets/shadow_warrior/3_atk/3_atk_{}.png", 23, start_index=1
        )
        self.animations[PlayerState.HURT] = self._load_frames(
            "assets/shadow_warrior/take_hit/take_hit_{}.png", 6, start_index=1
        )
        self.animations[PlayerState.DEATH] = self._load_frames(
            "assets/shadow_warrior/death/death_{}.png", 12, start_index=1
        )
        self.animations[PlayerState.DEFEND] = self._load_frames(
            "assets/shadow_warrior/defend/defend_{}.png", 7, start_index=1
        )
        # Frame index to freeze on while defend button is held (0-indexed).
        # Frames before this play as the "raise" intro; frames after play on release.
        self._DEFEND_HOLD_FRAME: Final[int] = 3
    
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
    def is_invincible(self) -> bool:
        return self._invincibility_timer > 0 or (
            self.state_configs.get(self.state) and self.state_configs[self.state].grants_invincibility
        )

    @property
    def health(self) -> int: return self._health
    @property
    def max_health(self) -> int: return self._max_health
    @property
    def entity_id(self) -> int: return id(self)
    @property
    def current_frame_index(self) -> int: return int(self.animation_index)
    @property
    def is_dead(self) -> bool: return self.state == PlayerState.DEATH
    @property
    def is_running(self) -> bool: return self.state == PlayerState.RUN
    @property
    def direction(self) -> int: return self._direction
    
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
        
        return self.attack_state.is_hit_frame_active()
    
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
        
        return self.attack_state.get_current_hitbox(
            self.rect, self.facing_left
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
        return self.attack_state.try_register_hit(target_id)
    
    def get_current_attack_damage(self) -> float:
        """
        Get the damage value for the current attack frame.
        
        Returns the base damage multiplied by any frame-specific
        damage modifiers (e.g., sweet spot frames deal more damage).
        
        Returns:
            Damage value for the current frame, or 0 if not attacking.
        """
        return self.attack_state.get_current_damage()

    def get_current_attack_frame(self) -> Optional[int]:
        """Return the current animation frame index for the active attack."""
        if not self.attack_state.is_active:
            return None
        return self.attack_state.current_frame

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
        return self.attack_state.get_knockback_vector(
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
        return self.attack_state.get_knockback_force()
    
    def has_hit_target(self, target_id: int) -> bool:
        """
        Check if a target has been hit during the current attack.
        
        Args:
            target_id: Unique identifier for the target entity.
            
        Returns:
            True if target has been hit at least once.
        """
        return self.attack_state.has_hit_target(target_id)
    
    def get_hit_count(self, target_id: int) -> int:
        """
        Get the number of times a target has been hit this attack.
        
        Args:
            target_id: Unique identifier for the target entity.
            
        Returns:
            Number of registered hits.
        """
        return self.attack_state.get_hit_count(target_id)
    
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
            attack_state=self.attack_state,
            attacker_rect=self.rect,
            attacker_facing_left=self._facing_left,
            targets=targets,
        )
    
    # ─────────────────────────────────────────────────────────────────────────
    # State Machine Core
    # ─────────────────────────────────────────────────────────────────────────
    
    
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
            
        # Check if defending
        if self._state == PlayerState.DEFEND:
            # Reduce damage by 70% when defending
            amount = int(amount * 0.3)
            self._audio_manager.play_sound("defend_hit")
        else:
            self._audio_manager.play_sound("player_hurt")
        
        # Apply damage
        self._health = max(0, self._health - int(amount))
        
        # Determine resulting state
        if self._health <= 0:
            self._transition_to(PlayerState.DEATH)
            self._audio_manager.play_sound("player_death")
        elif self._state != PlayerState.DEFEND:  # Only go to HURT state if not defending
            self._transition_to(PlayerState.HURT)
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
        self.attack_state.begin(self.THRUST_ATTACK_CONFIG)
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
        self.attack_state.begin(self.SMASH_ATTACK_CONFIG)
        self._current_attack_config = self.SMASH_ATTACK_CONFIG
        self._attack_audio_frames_played.clear()
        self._audio_manager.play_sound("smash")
        return True

    def attack_power(self) -> bool:
        """
        Initiate power attack.
        
        Begins the power attack animation and initializes the
        attack state with the power configuration. Damage will
        only be dealt on the configured hit frames.
        
        Returns:
            True if attack started, False if blocked by current state.
        """
        if not self._can_transition_to(PlayerState.ATTACK_POWER):
            return False
            
        self._transition_to(PlayerState.ATTACK_POWER)
        
        # Initialize attack state with thrust configuration
        self.attack_state.begin(self.POWER_ATTACK_CONFIG)
        self._current_attack_config = self.POWER_ATTACK_CONFIG
        self._attack_audio_frames_played.clear()
        self._audio_manager.play_sound("thrust")
        return True

    def defend(self) -> bool:
        """
        Initiate defend action.
        
        Returns:
            True if defend started, False if not allowed in current state.
        """
        if not self._can_transition_to(PlayerState.DEFEND):
            return False
            
        self._transition_to(PlayerState.DEFEND)
        self._audio_manager.play_sound("defend")
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
        self.attack_state = AttackState()
        self._current_attack_config = None
        self._invincibility_timer = 0.0
        self._invincibility_duration = 0.0
        self._direction = 0
        self._facing_left = False
        self._gravity = 0.0
        self.rect.midtop = self._spawn_midtop
        self._footsteps.reset()
        self._defend_releasing = False
    
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
        stick_y = joystick.get_axis(1) if joystick else 0
        jump_pressed = (
            keys[pg.K_SPACE] or
            (joystick and joystick.get_button(0)) or
            stick_y < -0.9
        )
        if jump_pressed:
            self.jump()
        
        # Thrust attack (Q or gamepad button 2)
        if keys[pg.K_q] or (joystick and joystick.get_button(2)):
            self.attack_thrust()
        
        # Smash attack (E or gamepad button 1)
        if keys[pg.K_e] or (joystick and joystick.get_button(1)):
            self.attack_smash()

        # Power attack (W or gamepad button 3)
        if keys[pg.K_w] or (joystick and joystick.get_button(3)):
            self.attack_power()

        # Defend (R or gamepad R2 trigger)
        r2_trigger = (joystick and joystick.get_axis(5) > 0.5)  # R2 is axis 5
        defend_pressed = keys[pg.K_r] or r2_trigger
        
        if defend_pressed:
            # Only trigger defend if we're not already defending
            if self._state != PlayerState.DEFEND:
                self.defend()
        # Note: Button release is now handled in _animate_defend()
    
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
    
    
    def _apply_frame(self) -> None:
        """Apply current animation frame to sprite image."""
        frame_index = min(
            int(self._animation_index),
            len(self._current_frames) - 1,
        )
        self.image = self._current_frames[frame_index]
        
        if self._facing_left:
            self.image = pg.transform.flip(self.image, True, False)
        
        # Visual feedback for invincibility (skip flicker during HURT/DEFEND)
        if self.is_invincible and self._state not in (PlayerState.HURT, PlayerState.DEFEND):
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
            "attack_info": self.attack_state.get_debug_info(),
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
        if dt is None: dt = 1.0 / 60.0
        
        if self._invincibility_timer > 0:
            self._invincibility_timer -= dt

        self.player_input()
        self._apply_gravity()
        self._apply_movement()
        self._update_state_logic()
        self._update_defend_logic()
        
        super().update(dt)

        self._update_attack_audio()
        if self.state == PlayerState.RUN:
             self._footsteps.update(dt * 1000)
        
        # Visual feedback for invincibility (skip during HURT/DEFEND)
        if self.is_invincible and self.state not in (PlayerState.HURT, PlayerState.DEFEND):
            if int(pg.time.get_ticks() / 100) % 2 == 0:
                self.image.set_alpha(128)
            else:
                self.image.set_alpha(255)
        else:
            self.image.set_alpha(255)
