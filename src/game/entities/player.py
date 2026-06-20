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
from typing import TYPE_CHECKING, Final, Optional, cast

import os
import json
import pygame as pg

from v3x_zulfiqar_gideon import AssetManager, Actor, FootstepController
from .hitbox_registry import HitboxRegistry
from v3x_zulfiqar_gideon import (
    AttackConfig,
    AttackState,
    AttackPhase,
    HitboxData,
    HitResult,
    CombatProcessor,
)

if TYPE_CHECKING:
    from v3x_zulfiqar_gideon import AudioManager


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
    SPECIAL_ATTACK = 23
    TRANSFORM = 24
    ROLL = 25
    DASH = 26
    
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
    def to_dict(self) -> dict:
        """Return a JSON‑serializable representation of the player."""
        return {
            "health": self.health,
            "max_health": self.max_health,
            "state": self.state.name if self.state else None,
            "position": (self.rect.x, self.rect.y),
            "is_invincible": self.is_invincible,
            "is_dead": self.is_dead,
            "is_running": self.is_running,
            "direction": self._direction,
        }

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
    
    _STATE_CONFIGS: Final[dict[Enum, StateConfig]] = {
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
        PlayerState.SPECIAL_ATTACK: StateConfig(
            animation_speed=0.20,
            loops=False,
            next_state=PlayerState.IDLE,
            interruptible=False,
            grants_invincibility=True,
            locks_movement=True,
            locks_input=True,
        ),
        PlayerState.TRANSFORM: StateConfig(
            animation_speed=0.18,
            loops=False,
            next_state=PlayerState.IDLE,
            interruptible=False,
            grants_invincibility=True,
            locks_movement=True,
            locks_input=True,
        ),
        PlayerState.ROLL: StateConfig(
            animation_speed=0.25,
            loops=False,
            next_state=PlayerState.IDLE,
            interruptible=False,
            grants_invincibility=True,
            locks_movement=True,
            locks_input=True,
        ),
        PlayerState.DASH: StateConfig(
            animation_speed=0.25,
            loops=False,
            next_state=PlayerState.IDLE,
            interruptible=False,
            grants_invincibility=False,
            locks_movement=True,
            locks_input=True,
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

    # Thrust Attack
    THRUST_ATTACK_CONFIG: Final[AttackConfig] = AttackConfig(
        hit_frames=frozenset([2, 3, 4, 5, 6, 7]),
        base_damage=15.0,
        knockback_force=8.0,
        knockback_angle=30.0,
        hit_stop_frames=3,
        can_hit_multiple=True,
        max_hits_per_target=1,
        frame_damage_modifiers={'2': 0.3, '3': 0.5, '4': 0.8, '5': 1.0, '6': 0.6, '7': 0.4},
        hitbox_data={
            2: HitboxData(offset_x=108, offset_y=45, width=399, height=135),
            3: HitboxData(offset_x=114, offset_y=30, width=396, height=162),
            4: HitboxData(offset_x=129, offset_y=36, width=378, height=150),
            5: HitboxData(offset_x=93, offset_y=30, width=426, height=162),
            6: HitboxData(offset_x=69, offset_y=12, width=447, height=198),
            7: HitboxData(offset_x=57, offset_y=-6, width=432, height=234),
        },
        startup_frames=frozenset([0, 1]),
        recovery_frames=frozenset([8]),
    )

    # Smash Attack
    SMASH_ATTACK_CONFIG: Final[AttackConfig] = AttackConfig(
        hit_frames=frozenset([2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14]),
        base_damage=25.0,
        knockback_force=15.0,
        knockback_angle=45.0,
        hit_stop_frames=11,
        can_hit_multiple=True,
        max_hits_per_target=3,
        frame_damage_modifiers={'2': 0.2, '7': 1.0, '13': 0.5},
        hitbox_data={
            2: HitboxData(offset_x=108, offset_y=45, width=399, height=135),
            3: HitboxData(offset_x=114, offset_y=30, width=396, height=162),
            4: HitboxData(offset_x=117, offset_y=36, width=405, height=150),
            5: HitboxData(offset_x=120, offset_y=24, width=372, height=177),
            6: HitboxData(offset_x=138, offset_y=6, width=336, height=213),
            7: HitboxData(offset_x=102, offset_y=0, width=432, height=222),
            8: HitboxData(offset_x=102, offset_y=0, width=438, height=222),
            9: HitboxData(offset_x=114, offset_y=3, width=423, height=216),
            10: HitboxData(offset_x=123, offset_y=3, width=342, height=216),
            11: HitboxData(offset_x=120, offset_y=3, width=333, height=219),
            12: HitboxData(offset_x=117, offset_y=6, width=354, height=213),
            13: HitboxData(offset_x=90, offset_y=9, width=417, height=204),
            14: HitboxData(offset_x=69, offset_y=12, width=450, height=201),
        },
        startup_frames=frozenset([0, 1]),
        recovery_frames=frozenset([15, 16]),
    )

    # Power Attack
    POWER_ATTACK_CONFIG: Final[AttackConfig] = AttackConfig(
        hit_frames=frozenset([6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22]),
        base_damage=25.0,
        knockback_force=15.0,
        knockback_angle=45.0,
        hit_stop_frames=19,
        can_hit_multiple=True,
        max_hits_per_target=2,
        frame_damage_modifiers={'6': 0.5, '11': 0.8, '16': 1.2, '20': 1.5},
        hitbox_data={
            6: HitboxData(offset_x=138, offset_y=6, width=336, height=213),
            7: HitboxData(offset_x=102, offset_y=0, width=432, height=222),
            8: HitboxData(offset_x=102, offset_y=0, width=438, height=222),
            9: HitboxData(offset_x=114, offset_y=3, width=423, height=216),
            10: HitboxData(offset_x=123, offset_y=3, width=342, height=216),
            11: HitboxData(offset_x=99, offset_y=-3, width=375, height=231),
            12: HitboxData(offset_x=108, offset_y=3, width=372, height=210),
            13: HitboxData(offset_x=93, offset_y=-3, width=408, height=231),
            14: HitboxData(offset_x=111, offset_y=0, width=366, height=219),
            15: HitboxData(offset_x=102, offset_y=-24, width=381, height=270),
            16: HitboxData(offset_x=153, offset_y=-18, width=486, height=258),
            17: HitboxData(offset_x=114, offset_y=-36, width=405, height=294),
            18: HitboxData(offset_x=138, offset_y=-24, width=393, height=270),
            19: HitboxData(offset_x=153, offset_y=-27, width=543, height=279),
            20: HitboxData(offset_x=135, offset_y=-30, width=582, height=282),
            21: HitboxData(offset_x=132, offset_y=-33, width=582, height=288),
            22: HitboxData(offset_x=150, offset_y=-27, width=555, height=279),
        },
        startup_frames=frozenset([0, 1, 2, 3, 4, 5]),
        recovery_frames=frozenset([]),
    )

    # Special Attack
    SPECIAL_ATTACK_CONFIG: Final[AttackConfig] = AttackConfig(
        hit_frames=frozenset([14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33]),
        base_damage=35.0,
        knockback_force=15.0,
        knockback_angle=45.0,
        hit_stop_frames=15,
        can_hit_multiple=True,
        max_hits_per_target=3,
        frame_damage_modifiers={},
        hitbox_data={
            14: HitboxData(offset_x=18, offset_y=99, width=87, height=24),
            15: HitboxData(offset_x=18, offset_y=78, width=147, height=66),
            16: HitboxData(offset_x=21, offset_y=24, width=69, height=174),
            17: HitboxData(offset_x=21, offset_y=-3, width=120, height=231),
            18: HitboxData(offset_x=21, offset_y=-3, width=120, height=231),
            19: HitboxData(offset_x=30, offset_y=-12, width=204, height=249),
            20: HitboxData(offset_x=27, offset_y=-60, width=264, height=189),
            21: HitboxData(offset_x=18, offset_y=-51, width=237, height=195),
            22: HitboxData(offset_x=51, offset_y=-51, width=303, height=213),
            23: HitboxData(offset_x=21, offset_y=-51, width=408, height=306),
            24: HitboxData(offset_x=9, offset_y=-54, width=417, height=312),
            25: HitboxData(offset_x=9, offset_y=-57, width=408, height=321),
            26: HitboxData(offset_x=48, offset_y=-54, width=417, height=312),
            27: HitboxData(offset_x=21, offset_y=-51, width=408, height=306),
            28: HitboxData(offset_x=21, offset_y=-51, width=384, height=303),
            29: HitboxData(offset_x=30, offset_y=-45, width=366, height=273),
            30: HitboxData(offset_x=39, offset_y=-36, width=345, height=294),
            31: HitboxData(offset_x=33, offset_y=-30, width=336, height=285),
            32: HitboxData(offset_x=21, offset_y=-21, width=300, height=264),
            33: HitboxData(offset_x=21, offset_y=-18, width=279, height=261),
        },
        startup_frames=frozenset([0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13]),
        recovery_frames=frozenset([]),
    )

    # Enhanced Special Attack
    ENHANCED_SPECIAL_ATTACK_CONFIG: Final[AttackConfig] = AttackConfig(
        hit_frames=frozenset([6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18]),
        base_damage=50.0,
        knockback_force=20.0,
        knockback_angle=45.0,
        hit_stop_frames=19,
        can_hit_multiple=True,
        max_hits_per_target=4,
        frame_damage_modifiers={},
        hitbox_data={
            6: HitboxData(offset_x=3, offset_y=-63, width=810, height=348),
            7: HitboxData(offset_x=-3, offset_y=-75, width=810, height=372),
            8: HitboxData(offset_x=3, offset_y=-75, width=837, height=372),
            9: HitboxData(offset_x=0, offset_y=-78, width=846, height=381),
            10: HitboxData(offset_x=-3, offset_y=-75, width=810, height=372),
            11: HitboxData(offset_x=3, offset_y=-75, width=837, height=372),
            12: HitboxData(offset_x=0, offset_y=-78, width=846, height=381),
            13: HitboxData(offset_x=-15, offset_y=-30, width=507, height=282),
            14: HitboxData(offset_x=-21, offset_y=27, width=249, height=168),
            15: HitboxData(offset_x=-18, offset_y=27, width=162, height=171),
            16: HitboxData(offset_x=-18, offset_y=9, width=159, height=204),
            17: HitboxData(offset_x=-21, offset_y=-60, width=177, height=345),
            18: HitboxData(offset_x=3, offset_y=-9, width=213, height=243),
        },
        startup_frames=frozenset([0, 1, 2, 3, 4, 5]),
        recovery_frames=frozenset([]),
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
    
    _ATTACK_AUDIO_FRAME_SOUNDS: Final[dict[Enum, dict[int, str]]] = {
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
        
        # State machine configuration (from static registry, dynamically overridden from config if present)
        self.state_configs = dict(self._STATE_CONFIGS)
        
        # Initialize attack configs to defaults
        self.thrust_attack_config = self.THRUST_ATTACK_CONFIG
        self.smash_attack_config = self.SMASH_ATTACK_CONFIG
        self.power_attack_config = self.POWER_ATTACK_CONFIG
        self.special_attack_config = self.SPECIAL_ATTACK_CONFIG
        self.enhanced_special_attack_config = self.ENHANCED_SPECIAL_ATTACK_CONFIG
        
        try:
            config_path = "game_data/player_config.json"
            if os.path.exists(config_path):
                with open(config_path, "r") as f:
                    overrides = json.load(f)
                
                # Check for new nested format vs legacy format
                if isinstance(overrides, dict) and ("states" in overrides or "attacks" in overrides):
                    states_overrides = overrides.get("states", {})
                    attacks_overrides = overrides.get("attacks", {})
                else:
                    states_overrides = overrides
                    attacks_overrides = {}
                    
                # Load state overrides
                for state_name, cfg_dict in states_overrides.items():
                    try:
                        state_enum = PlayerState[state_name]
                        orig_cfg = self._STATE_CONFIGS.get(state_enum, StateConfig())
                        next_state_val = orig_cfg.next_state
                        if "next_state" in cfg_dict and cfg_dict["next_state"]:
                            try:
                                next_state_val = PlayerState[cfg_dict["next_state"]]
                            except KeyError:
                                pass
                        self.state_configs[state_enum] = StateConfig(
                            animation_speed=cfg_dict.get("animation_speed", orig_cfg.animation_speed),
                            loops=cfg_dict.get("loops", orig_cfg.loops),
                            next_state=next_state_val,
                            interruptible=cfg_dict.get("interruptible", orig_cfg.interruptible),
                            grants_invincibility=cfg_dict.get("grants_invincibility", orig_cfg.grants_invincibility),
                            locks_movement=cfg_dict.get("locks_movement", orig_cfg.locks_movement),
                            locks_input=cfg_dict.get("locks_input", orig_cfg.locks_input),
                        )
                    except KeyError:
                        pass
                        
                # Load attack overrides
                for attack_key, atk_dict in attacks_overrides.items():
                    try:
                        hit_frames = frozenset(atk_dict.get("hit_frames", []))
                        startup_frames = frozenset(atk_dict.get("startup_frames", []))
                        recovery_frames = frozenset(atk_dict.get("recovery_frames", []))
                        base_damage = float(atk_dict.get("base_damage", 10.0))
                        knockback_force = float(atk_dict.get("knockback_force", 5.0))
                        knockback_angle = float(atk_dict.get("knockback_angle", 45.0)) if atk_dict.get("knockback_angle") is not None else None
                        hit_stop_frames = int(atk_dict.get("hit_stop_frames", 0))
                        can_hit_multiple = bool(atk_dict.get("can_hit_multiple", True))
                        max_hits_per_target = int(atk_dict.get("max_hits_per_target", 1))
                        
                        frame_damage_modifiers = {}
                        for k, v in atk_dict.get("frame_damage_modifiers", {}).items():
                            frame_damage_modifiers[int(k)] = float(v)
                            
                        hitbox_data = {}
                        for k, v in atk_dict.get("hitbox_data", {}).items():
                            hitbox_data[int(k)] = HitboxData(
                                offset_x=int(v.get("offset_x", 0)),
                                offset_y=int(v.get("offset_y", 0)),
                                width=int(v.get("width", 50)),
                                height=int(v.get("height", 50))
                            )
                            
                        config_obj = AttackConfig(
                            hit_frames=hit_frames,
                            base_damage=base_damage,
                            knockback_force=knockback_force,
                            knockback_angle=knockback_angle,
                            hit_stop_frames=hit_stop_frames,
                            can_hit_multiple=can_hit_multiple,
                            max_hits_per_target=max_hits_per_target,
                            frame_damage_modifiers=frame_damage_modifiers,
                            hitbox_data=hitbox_data,
                            startup_frames=startup_frames,
                            recovery_frames=recovery_frames
                        )
                        
                        if attack_key == "THRUST_ATTACK_CONFIG":
                            self.thrust_attack_config = config_obj
                        elif attack_key == "SMASH_ATTACK_CONFIG":
                            self.smash_attack_config = config_obj
                        elif attack_key == "POWER_ATTACK_CONFIG":
                            self.power_attack_config = config_obj
                        elif attack_key == "SPECIAL_ATTACK_CONFIG":
                            self.special_attack_config = config_obj
                        elif attack_key == "ENHANCED_SPECIAL_ATTACK_CONFIG":
                            self.enhanced_special_attack_config = config_obj
                    except Exception as ex:
                        print(f"[PLAYER ATTACK CONFIG ERROR] Failed to load attack override {attack_key}: {ex}")
        except Exception as e:
            print(f"[PLAYER CONFIG ERROR] Failed to load custom configurations: {e}")
        
        # Load margins and scale first
        margins = HitboxRegistry.get_margins("player")
        self.scale = margins.scale
        
        # Enhanced form state and animation tracking
        self._is_enhanced = False
        self.enhanced_animations = {}
        
        # Load all animation frame sets
        self._load_all_animations()
        
        self.set_state(PlayerState.IDLE)
        
        # Combat state
        self._current_attack_config: Optional[AttackConfig] = None
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
        if self.state is not None and self.state in self.animations:
            self.image = self.animations[self.state][0]
        self.rect: pg.Rect = self.image.get_rect(midtop=(x, y))
        self._spawn_midtop: tuple[int, int] = self.rect.midtop
        self.adjust_hitbox_sides(left=margins.left, right=margins.right, top=margins.top, bottom=margins.bottom)
        
        # Physics state
        self._gravity: float = 0.0
        surf = pg.display.get_surface()
        height = surf.get_height() if surf else 720
        self._ground_y: int = height - margins.ground_offset
        
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
        scale = self.scale
        self.animations[PlayerState.IDLE] = self._load_frames(
            "assets/shadow_warrior/idle/idle_{}.png", 12, start_index=1, scale_factor=scale
        )
        self.animations[PlayerState.RUN] = self._load_frames(
            "assets/shadow_warrior/run/run_{}.png", 10, start_index=1, scale_factor=scale
        )
        self.animations[PlayerState.JUMP_UP] = self._load_frames(
            "assets/shadow_warrior/jump_up_loop/jump_up_loop_{}.png", 3, start_index=1, scale_factor=scale
        )
        self.animations[PlayerState.JUMP_DOWN] = self._load_frames(
            "assets/shadow_warrior/jump_down_loop/jump_down_loop_{}.png", 3, start_index=1, scale_factor=scale
        )
        self.animations[PlayerState.ATTACK_THRUST] = self._load_frames(
            "assets/shadow_warrior/1_atk/1_atk_{}.png", 9, start_index=1, scale_factor=scale
        )
        self.animations[PlayerState.ATTACK_SMASH] = self._load_frames(
            "assets/shadow_warrior/2_atk/2_atk_{}.png", 17, start_index=1, scale_factor=scale
        )
        self.animations[PlayerState.ATTACK_POWER] = self._load_frames(
            "assets/shadow_warrior/3_atk/3_atk_{}.png", 23, start_index=1, scale_factor=scale
        )
        self.animations[PlayerState.HURT] = self._load_frames(
            "assets/shadow_warrior/take_hit/take_hit_{}.png", 6, start_index=1, scale_factor=scale
        )
        self.animations[PlayerState.DEATH] = self._load_frames(
            "assets/shadow_warrior/death/death_{}.png", 12, start_index=1, scale_factor=scale
        )
        self.animations[PlayerState.DEFEND] = self._load_frames(
            "assets/shadow_warrior/defend/defend_{}.png", 7, start_index=1, scale_factor=scale
        )
        self.animations[PlayerState.ROLL] = self._load_frames(
            "assets/shadow_warrior/roll/roll_{}.png", 8, start_index=1, scale_factor=scale
        )
        self.animations[PlayerState.DASH] = self._load_frames(
            "assets/shadow_warrior/dash/dash_{}.png", 12, start_index=1, scale_factor=scale
        )
        self.animations[PlayerState.SPECIAL_ATTACK] = self._load_frames(
            "assets/shadow_warrior/sp_atk/sp_atk_{}.png", 34, start_index=1, scale_factor=scale
        )
        self.animations[PlayerState.TRANSFORM] = self._load_frames(
            "assets/shadow_warrior/transform/transform_{}.png", 37, start_index=1, scale_factor=scale
        )
        
        # Load enhanced animations
        self.enhanced_animations[PlayerState.IDLE] = self._load_frames(
            "assets/shadow_warrior/e_idle/e_idle_{}.png", 18, start_index=1, scale_factor=scale
        )
        self.enhanced_animations[PlayerState.RUN] = self._load_frames(
            "assets/shadow_warrior/e_run/e_run_{}.png", 10, start_index=1, scale_factor=scale
        )
        self.enhanced_animations[PlayerState.JUMP_UP] = self._load_frames(
            "assets/shadow_warrior/e_jump_up/e_jump_up_{}.png", 3, start_index=1, scale_factor=scale
        )
        self.enhanced_animations[PlayerState.JUMP_DOWN] = self._load_frames(
            "assets/shadow_warrior/e_jump_down/e_jump_down_{}.png", 3, start_index=1, scale_factor=scale
        )
        self.enhanced_animations[PlayerState.ATTACK_THRUST] = self._load_frames(
            "assets/shadow_warrior/e_1_atk/e_1_atk_{}.png", 14, start_index=1, scale_factor=scale
        )
        self.enhanced_animations[PlayerState.ATTACK_SMASH] = self._load_frames(
            "assets/shadow_warrior/e_2_atk/e_2_atk_{}.png", 22, start_index=1, scale_factor=scale
        )
        self.enhanced_animations[PlayerState.ATTACK_POWER] = self._load_frames(
            "assets/shadow_warrior/e_3_atk/e_3_atk_{}.png", 35, start_index=1, scale_factor=scale
        )
        self.enhanced_animations[PlayerState.HURT] = self._load_frames(
            "assets/shadow_warrior/e_take_hit/e_take_hit_{}.png", 7, start_index=1, scale_factor=scale
        )
        self.enhanced_animations[PlayerState.DEFEND] = self._load_frames(
            "assets/shadow_warrior/e_defend/e_defend_{}.png", 6, start_index=1, scale_factor=scale
        )
        self.enhanced_animations[PlayerState.SPECIAL_ATTACK] = self._load_frames(
            "assets/shadow_warrior/e_sp_atk/e_sp_atk_{}.png", 19, start_index=1, scale_factor=scale
        )
        
        # Fallbacks for states without enhanced equivalents
        self.enhanced_animations[PlayerState.DEATH] = self.animations[PlayerState.DEATH]
        self.enhanced_animations[PlayerState.ROLL] = self.animations[PlayerState.ROLL]
        self.enhanced_animations[PlayerState.DASH] = self.animations[PlayerState.DASH]
        self.enhanced_animations[PlayerState.TRANSFORM] = self.animations[PlayerState.TRANSFORM]

        # Frame index to freeze on while defend button is held (0-indexed).
        # Frames before this play as the "raise" intro; frames after play on release.
        self._DEFEND_HOLD_FRAME = 3
    
    def _load_frames(
        self,
        path_pattern: str,
        count: int,
        start_index: int = 0,
        scale_factor: float = 3.0,
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
                    int(original_size[0] * scale_factor),
                    int(original_size[1] * scale_factor),
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
        if self.state is None:
            return self._invincibility_timer > 0
        cfg = self.state_configs.get(self.state)
        grants_inv = bool(cfg.grants_invincibility) if cfg else False
        return self._invincibility_timer > 0 or grants_inv

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
    @property
    def is_attacking(self) -> bool:
        return self.state in (
            PlayerState.ATTACK_THRUST,
            PlayerState.ATTACK_SMASH,
            PlayerState.ATTACK_POWER,
            PlayerState.SPECIAL_ATTACK,
        )
    
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
        
        return cast(
            Optional[pg.Rect],
            self.attack_state.get_current_hitbox(self.rect, self.facing_left)
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
        damage = self.attack_state.get_current_damage()
        if self._is_enhanced:
            return damage * 1.5
        return damage

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
            self.facing_left,
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
            attacker_facing_left=self.facing_left,
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
        if self.state == PlayerState.DEFEND:
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
        elif self.state != PlayerState.DEFEND:  # Only go to HURT state if not defending
            self._transition_to(PlayerState.HURT)
            # Grant extended i-frames after hurt animation
            self._invincibility_duration = 0.3
            
        return True
    
    def attack_thrust(self) -> bool:
        """
        Initiate thrust attack.

        Button: ``Q`` (keyboard) / Gamepad button 2

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
        self.attack_state.begin(self.thrust_attack_config)
        self._current_attack_config = self.thrust_attack_config
        self._attack_audio_frames_played.clear()
        self._audio_manager.play_sound("thrust")
        return True
    
    def attack_smash(self) -> bool:
        """
        Initiate smash attack.

        Button: ``E`` (keyboard) / Gamepad button 1

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
        self.attack_state.begin(self.smash_attack_config)
        self._current_attack_config = self.smash_attack_config
        self._attack_audio_frames_played.clear()
        self._audio_manager.play_sound("smash")
        return True

    def attack_power(self) -> bool:
        """
        Initiate power attack.

        Button: ``W`` (keyboard) / Gamepad button 3

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
        self.attack_state.begin(self.power_attack_config)
        self._current_attack_config = self.power_attack_config
        self._attack_audio_frames_played.clear()
        self._audio_manager.play_sound("thrust")
        return True

    def defend(self) -> bool:
        """
        Initiate defend action.

        Button: ``R`` (keyboard) / Gamepad R2 trigger (axis 5 > 0.5)

        Returns:
            True if defend started, False if not allowed in current state.
        """
        if not self._can_transition_to(PlayerState.DEFEND):
            return False
            
        self._transition_to(PlayerState.DEFEND)
        self._audio_manager.play_sound("defend")
        return True

    def roll(self) -> bool:
        """
        Initiate dodge roll.
        
        Button: ``LSHIFT`` (keyboard) / Gamepad Button 4 (L1)
        
        Returns:
            True if roll started, False if blocked.
        """
        if not self._can_transition_to(PlayerState.ROLL):
            return False
        on_ground = self.rect.bottom >= self._ground_y - 1
        if not on_ground:
            return False
        self._transition_to(PlayerState.ROLL)
        self._audio_manager.play_sound("roll")
        return True

    def dash(self) -> bool:
        """
        Initiate fast dash.
        
        Button: ``LCTRL`` (keyboard) / Gamepad Button 5 (R1)
        
        Returns:
            True if dash started, False if blocked.
        """
        if not self._can_transition_to(PlayerState.DASH):
            return False
        self._transition_to(PlayerState.DASH)
        self._audio_manager.play_sound("dash")
        return True

    def special_attack(self) -> bool:
        """
        Initiate special slash-storm attack.
        
        Button: ``F`` (keyboard) / Gamepad L2 trigger
        
        Returns:
            True if attack started, False if blocked.
        """
        if not self._can_transition_to(PlayerState.SPECIAL_ATTACK):
            return False
            
        cfg = self.enhanced_special_attack_config if self._is_enhanced else self.special_attack_config
        self._current_attack_config = cfg
        self._transition_to(PlayerState.SPECIAL_ATTACK)
        self.attack_state.begin(cfg)
        self._attack_audio_frames_played.clear()
        self._audio_manager.play_sound("special_attack")
        return True

    def transform(self) -> bool:
        """
        Initiate shadow/enhanced transformation sequence.
        
        Button: ``T`` (keyboard) / Gamepad button 8
        
        Returns:
            True if transformation started, False if blocked.
        """
        if not self._can_transition_to(PlayerState.TRANSFORM):
            return False
        self._transition_to(PlayerState.TRANSFORM)
        self._audio_manager.play_sound("transform")
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

        Button: ``SPACE`` (keyboard) / Gamepad button 0 / Left-stick up (axis 1 < -0.9)

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

    def set_state(self, new_state: Enum, force: bool = False) -> None:
        """Sets the player state, applying post-damage invincibility upon exiting HURT state."""
        if self.state == PlayerState.HURT and new_state != PlayerState.HURT:
            if self._invincibility_duration > 0:
                self._invincibility_timer = self._invincibility_duration
                self._invincibility_duration = 0.0
        super().set_state(new_state, force=force)

    def reset(self) -> None:
        """Restore player to initial spawn state for retries/game over."""
        self._health = self._max_health
        self.set_state(PlayerState.IDLE, force=True)
        self.animation_index = 0.0
        self.attack_state = AttackState()
        self._current_attack_config = None
        self._invincibility_timer = 0.0
        self._invincibility_duration = 0.0
        self._direction = 0
        self.facing_left = False
        self._gravity = 0.0
        self.rect.midtop = self._spawn_midtop
        self._footsteps.reset()
        self._defend_releasing = False
    
    # ─────────────────────────────────────────────────────────────────────────
    # Input Handling
    # ─────────────────────────────────────────────────────────────────────────
    
    def _get_current_config(self) -> StateConfig:
        """Return the StateConfig for the current state, or a safe default."""
        if self.state is None:
            return StateConfig()
        return self.state_configs.get(self.state, StateConfig())

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
            self.facing_left = True
        elif move_right:
            self._direction = 1
            self.facing_left = False
        else:
            self._direction = 0
    
    def _process_action_input(
        self,
        keys: pg.key.ScancodeWrapper,
        joystick: Optional[pg.joystick.JoystickType],
    ) -> None:
        """Process action button input (jump, attacks, defend).

        Button → Move mapping:
            SPACE / Gamepad btn 0 / Stick-up  →  jump()
            Q     / Gamepad btn 2             →  attack_thrust()
            E     / Gamepad btn 1             →  attack_smash()
            W     / Gamepad btn 3             →  attack_power()
            R     / Gamepad R2 (axis 5)       →  defend()
        """
        # ── Jump  (SPACE | gamepad btn 0 | left-stick up) ─────────────────────
        stick_y = joystick.get_axis(1) if joystick else 0
        jump_pressed = (
            keys[pg.K_SPACE] or
            (joystick and joystick.get_button(0)) or
            stick_y < -0.9
        )
        if jump_pressed:
            self.jump()

        # ── Thrust attack  (Q | gamepad btn 2) ────────────────────────────────
        if keys[pg.K_q] or (joystick and joystick.get_button(2)):
            self.attack_thrust()

        # ── Smash attack   (E | gamepad btn 1) ────────────────────────────────
        if keys[pg.K_e] or (joystick and joystick.get_button(1)):
            self.attack_smash()

        # ── Power attack   (W | gamepad btn 3) ────────────────────────────────
        if keys[pg.K_w] or (joystick and joystick.get_button(3)):
            self.attack_power()

        # ── Defend         (R | gamepad R2 trigger, axis 5 > 0.5) ─────────────
        r2_trigger = (joystick and joystick.get_axis(5) > 0.5)  # R2 is axis 5
        defend_pressed = keys[pg.K_r] or r2_trigger
        if defend_pressed:
            if self.state != PlayerState.DEFEND:   # don't re-trigger mid-defend
                self.defend()
        # Note: button-release logic is handled inside _update_defend_logic()

        # ── Roll           (LSHIFT | gamepad btn 4 / L1) ──────────────────────
        if keys[pg.K_LSHIFT] or (joystick and joystick.get_button(4)):
            self.roll()

        # ── Dash           (LCTRL | gamepad btn 5 / R1) ───────────────────────
        if keys[pg.K_LCTRL] or (joystick and joystick.get_button(5)):
            self.dash()

        # ── Special Attack (F | gamepad L2 trigger, axis 4 > 0.5) ─────────────
        l2_trigger = joystick and joystick.get_axis(4) > 0.5 if joystick else False
        if keys[pg.K_f] or l2_trigger:
            self.special_attack()

        # ── Transform      (T | gamepad btn 8) ────────────────────────────────
        if keys[pg.K_t] or (joystick and joystick.get_button(8)):
            self.transform()
    
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
        if self.state == PlayerState.ROLL:
            roll_dir = -1 if self.facing_left else 1
            self.rect.x += int(roll_dir * 8.5)
        elif self.state == PlayerState.DASH:
            dash_dir = -1 if self.facing_left else 1
            self.rect.x += int(dash_dir * 14.0)
        else:
            if self._direction == 0:
                return

            # Use different speeds for ground and air movement
            if self.rect.bottom >= self._ground_y - 1:  # On ground
                move_speed = self._MOVE_SPEED
            else:  # In air
                move_speed = self._AIR_MOVE_SPEED

            self.rect.x += int(self._direction * move_speed)

        # Clamp to screen bounds
        screen_surf = pg.display.get_surface()
        screen_w = screen_surf.get_width() if screen_surf else 1280
        self.rect.left = max(self.rect.left, self._SCREEN_BOUND_LEFT)
        self.rect.right = min(self.rect.right, screen_w)

    # ─────────────────────────────────────────────────────────────────────────
    # State Transition Helpers
    # ─────────────────────────────────────────────────────────────────────────

    def _can_transition_to(self, new_state: PlayerState) -> bool:
        """Check if a transition to new_state is allowed from the current state."""
        if self.state == new_state:
            return False
        if self.state is None:
            return True
        # Higher priority state (lower value) cannot be interrupted by lower priority
        current_cfg = self.state_configs.get(self.state)
        if current_cfg and not current_cfg.interruptible:
            # Only allow transition to equal or higher priority (lower value)
            if new_state.value > self.state.value:
                return False
        return True

    def _transition_to(self, new_state: PlayerState) -> None:
        """Force a state transition using the Actor's set_state."""
        self.set_state(new_state, force=True)

    def set_state(self, new_state: Enum, force: bool = False) -> None:
        """Override to intercept transformation exit and toggle enhanced mode."""
        if self.state == PlayerState.TRANSFORM and new_state != PlayerState.TRANSFORM:
            self._is_enhanced = not self._is_enhanced
        super().set_state(new_state, force=force)

    def update_animation(self, dt: float) -> None:
        """Override to dynamically swap standard and enhanced animations."""
        orig_animations = self.animations
        if self._is_enhanced:
            self.animations = self.enhanced_animations
        try:
            super().update_animation(dt)
        finally:
            self.animations = orig_animations

    # ─────────────────────────────────────────────────────────────────────────
    # Per-Frame Logic Updates
    # ─────────────────────────────────────────────────────────────────────────

    def _update_state_logic(self) -> None:
        """Auto-manage state transitions based on physics (grounded, airborne, etc.)."""
        on_ground = self.rect.bottom >= self._ground_y - 1

        # Airborne state management
        if not on_ground:
            if self._gravity < 0 and self._can_transition_to(PlayerState.JUMP_UP):
                self._transition_to(PlayerState.JUMP_UP)
            elif self._gravity >= 0 and self._can_transition_to(PlayerState.JUMP_DOWN):
                self._transition_to(PlayerState.JUMP_DOWN)
            return

        # Grounded state management (only for interruptible states)
        cfg = self.state_configs.get(self.state) if self.state is not None else None
        if cfg and not cfg.interruptible:
            return

        if self.state in (PlayerState.JUMP_UP, PlayerState.JUMP_DOWN):
            # Just landed
            if self._direction != 0:
                self._transition_to(PlayerState.RUN)
            else:
                self._transition_to(PlayerState.IDLE)
        elif self._direction != 0:
            if self.state != PlayerState.RUN:
                self._transition_to(PlayerState.RUN)
        else:
            if self.state != PlayerState.IDLE:
                self._transition_to(PlayerState.IDLE)

    def _update_defend_logic(self) -> None:
        """Handle defend animation hold/release behavior."""
        if self.state != PlayerState.DEFEND:
            self._defend_releasing = False
            return

        # Check if defend button is still held
        keys = pg.key.get_pressed()
        joystick = self._get_joystick()
        r2_trigger = joystick and joystick.get_axis(5) > 0.5 if joystick else False
        defend_held = keys[pg.K_r] or r2_trigger

        current_frame = int(self.animation_index)

        if defend_held and not self._defend_releasing:
            # Freeze on hold frame while button is held
            if current_frame >= self._DEFEND_HOLD_FRAME:
                self.animation_index = float(self._DEFEND_HOLD_FRAME)
        else:
            # Button released — let animation finish from hold frame onward
            self._defend_releasing = True

    def _update_attack_audio(self) -> None:
        """Play frame-synced audio for multi-hit attacks."""
        if self.state is None:
            return
        sound_map = self._ATTACK_AUDIO_FRAME_SOUNDS.get(self.state)
        if not sound_map:
            return

        current_frame = int(self.animation_index)
        if current_frame in sound_map and current_frame not in self._attack_audio_frames_played:
            self._attack_audio_frames_played.add(current_frame)
            self._audio_manager.play_sound(sound_map[current_frame])

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
             self._footsteps.try_play(active=True, current_time_ms=pg.time.get_ticks())
        else:
             self._footsteps.try_play(active=False, current_time_ms=pg.time.get_ticks())
        
        # Visual feedback for invincibility (skip during HURT/DEFEND)
        if self.is_invincible and self.state not in (PlayerState.HURT, PlayerState.DEFEND):
            if int(pg.time.get_ticks() / 100) % 2 == 0:
                self.image.set_alpha(128)
            else:
                self.image.set_alpha(255)
        else:
            self.image.set_alpha(255)
