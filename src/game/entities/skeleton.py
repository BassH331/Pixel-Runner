"""
Skeleton enemy module with precision frame-based combat system.

This module implements a skeletal enemy with state-machine AI and
frame-accurate hit detection for responsive, fair combat gameplay.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import TYPE_CHECKING, Final, Optional, Sequence

import pygame as pg

from src.my_engine.asset_manager import AssetManager
from src.my_engine.ecs import Entity

if TYPE_CHECKING:
    from src.game.entities.player import Player


class SkeletonState(Enum):
    """Enumeration of all possible skeleton behavioral states."""
    
    IDLE = auto()
    CHASE = auto()
    ATTACK = auto()
    HURT = auto()
    DEATH = auto()


@dataclass(frozen=True, slots=True)
class AttackConfig:
    """
    Configuration for a single attack type's hit detection.
    
    Attributes:
        hit_frames: Sequence of frame indices where damage is applied.
        damage: Amount of damage dealt on hit.
        knockback: Horizontal knockback force applied to target.
    """
    
    hit_frames: tuple[int, ...]
    damage: float = 1.0
    knockback: float = 5.0


@dataclass(slots=True)
class AttackState:
    """
    Mutable state tracking for the current attack sequence.
    
    Attributes:
        is_active: Whether an attack is currently in progress.
        config: Configuration for the current attack type.
        hit_connected: Whether this attack has already dealt damage.
        last_frame_checked: Last frame index that was processed.
    """
    
    is_active: bool = False
    config: Optional[AttackConfig] = None
    hit_connected: bool = False
    last_frame_checked: int = -1
    
    def reset(self) -> None:
        """Reset attack state for a new attack or return to idle."""
        self.is_active = False
        self.config = None
        self.hit_connected = False
        self.last_frame_checked = -1
        
    def begin(self, config: AttackConfig) -> None:
        """Initialize state for a new attack sequence."""
        self.is_active = True
        self.config = config
        self.hit_connected = False
        self.last_frame_checked = -1


class Skeleton(Entity):
    """
    A skeletal enemy with state-machine AI and frame-precise combat.
    
    This enemy tracks the player, engages when in range, and uses a
    configurable hit-frame system for fair, responsive combat. Damage
    is only applied during specific animation frames, allowing players
    to read and react to attack telegraphs.
    
    States:
        IDLE: Standing still, scanning for player.
        CHASE: Pursuing the player within detection range.
        ATTACK: Executing an attack sequence with active hit frames.
        HURT: Staggered after receiving damage.
        DEATH: Playing death animation before removal.
    
    Attributes:
        ATTACK_1_CONFIG: Hit frame configuration for primary attack.
        ATTACK_2_CONFIG: Hit frame configuration for secondary attack.
    """
    
    # Class-level attack configurations (immutable)
    ATTACK_1_CONFIG: Final[AttackConfig] = AttackConfig(
        hit_frames=(6,),
        damage=1.0,
        knockback=8.0,
    )
    
    ATTACK_2_CONFIG: Final[AttackConfig] = AttackConfig(
        hit_frames=(5, 6),  # Secondary attack has slightly different timing
        damage=0.75,
        knockback=5.0,
    )
    
    # Animation speed constants
    _ANIM_SPEED_IDLE: Final[float] = 0.1
    _ANIM_SPEED_WALK: Final[float] = 0.15
    _ANIM_SPEED_ATTACK: Final[float] = 0.15
    _ANIM_SPEED_HURT: Final[float] = 0.15
    _ANIM_SPEED_DEATH: Final[float] = 0.15
    
    def __init__(self, x: int, y: int, player: Player) -> None:
        """
        Initialize a skeleton enemy.
        
        Args:
            x: Initial x position in world coordinates.
            y: Initial y position in world coordinates.
            player: Reference to the player entity for AI targeting.
        """
        super().__init__(x, y)
        
        self._player: Player = player
        self._state: SkeletonState = SkeletonState.IDLE
        self._attack_state: AttackState = AttackState()
        
        # Load animation frame sequences
        self._idle_frames: list[pg.Surface] = self._load_frames(
            "assets/skeleton/Skeleton_01_White_Idle/skeleton-idle_{}.png", 8
        )
        self._walk_frames: list[pg.Surface] = self._load_frames(
            "assets/skeleton/Skeleton_01_White_Walk/skeleton-walk_{:02d}.png", 10
        )
        self._attack_frames: list[pg.Surface] = self._load_frames(
            "assets/skeleton/Skeleton_01_White_Attack1/skeleton-atk2_{:02d}.png", 10
        )
        self._attack2_frames: list[pg.Surface] = self._load_frames(
            "assets/skeleton/Skeleton_01_White_Attack2/skeleton-atk1_{}.png", 9
        )
        self._hurt_frames: list[pg.Surface] = self._load_frames(
            "assets/skeleton/Skeleton_01_White_Hurt/skeleton-hurt_{}.png", 5
        )
        self._death_frames: list[pg.Surface] = self._load_frames(
            "assets/skeleton/Skeleton_01_White_Die/skeleton-death_{:02d}.png", 13
        )
        
        # Animation state
        self._current_frames: list[pg.Surface] = self._idle_frames
        self._animation_index: float = 0.0
        self.image: pg.Surface = self._current_frames[0]
        self.rect: pg.Rect = self.image.get_rect(midbottom=(x, y))
        
        # Hitbox adjustment for gameplay feel
        self.reduce_hitbox(40, 20, align='bottom')
        
        # Movement and physics
        self._speed: float = 2.5
        self._gravity: float = 0.0
        self._ground_y: int = pg.display.Info().current_h - 34
        self._facing_left: bool = True
        
        # AI configuration
        self._detection_range: int = 1000
        self._attack_range: int = 60
        self._vertical_tolerance: int = 100
        
        # Combat state
        self._max_health: int = 30  # Increased from 4 to 30 to prevent one-shot kills
        self._health: int = self._max_health
        
    def _load_frames(
        self,
        path_pattern: str,
        count: int,
        scale_factor: int = 2,
    ) -> list[pg.Surface]:
        """
        Load and scale animation frames from a file pattern.
        
        Args:
            path_pattern: Format string for frame paths with index placeholder.
            count: Number of frames to load (0-indexed).
            scale_factor: Multiplier for sprite dimensions.
            
        Returns:
            List of scaled pygame Surface objects.
            
        Raises:
            RuntimeError: If no frames could be loaded from the pattern.
        """
        frames: list[pg.Surface] = []
        
        for i in range(count):
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
                # Log but continue - partial animation sets may be acceptable
                print(f"Warning: Failed to load frame {i} from '{path}': {e}")
                
        if not frames:
            raise RuntimeError(
                f"Failed to load any frames from pattern: {path_pattern}"
            )
            
        return frames
    
    # ─────────────────────────────────────────────────────────────────────────
    # Public API: Frame and State Inspection
    # ─────────────────────────────────────────────────────────────────────────
    
    @property
    def state(self) -> SkeletonState:
        """Current behavioral state of the skeleton."""
        return self._state
    
    @property
    def current_frame_index(self) -> int:
        """
        Current animation frame index (0-based).
        
        Returns:
            Integer index of the currently displayed frame.
        """
        return int(self._animation_index)
    
    @property
    def is_attacking(self) -> bool:
        """Whether the skeleton is currently in an attack state."""
        return self._state == SkeletonState.ATTACK
    
    @property
    def is_alive(self) -> bool:
        """Whether the skeleton is alive and can act."""
        return self._state != SkeletonState.DEATH
    
    @property
    def health(self) -> int:
        """Current health points."""
        return self._health
    
    @property
    def max_health(self) -> int:
        """Maximum health points."""
        return self._max_health
    
    def is_in_hit_frame(self) -> bool:
        """
        Check if the skeleton is currently in a damage-dealing frame.
        
        This method checks whether the current animation frame is one
        of the configured hit frames for the active attack. Use this
        to determine when to apply damage to the player.
        
        Returns:
            True if currently in a hit frame during an active attack,
            False otherwise.
            
        Example:
            >>> if skeleton.is_in_hit_frame() and player_in_range:
            ...     player.take_damage(skeleton.get_current_attack_damage())
        """
        if not self._attack_state.is_active:
            return False
            
        if self._attack_state.config is None:
            return False
            
        return self.current_frame_index in self._attack_state.config.hit_frames
    
    def should_deal_damage(self) -> bool:
        """
        Check if damage should be dealt this frame (one-shot per attack).
        
        Unlike `is_in_hit_frame()`, this method returns True only once
        per attack sequence, preventing multiple damage applications
        when the hit frame persists across multiple update cycles.
        
        Returns:
            True if damage should be applied this frame, False otherwise.
            
        Example:
            >>> if skeleton.should_deal_damage() and collision_detected:
            ...     player.take_damage(skeleton.get_current_attack_damage())
        """
        if not self.is_in_hit_frame():
            return False
            
        # Already dealt damage this attack
        if self._attack_state.hit_connected:
            return False
            
        # Prevent re-triggering on same frame across multiple calls
        current_frame = self.current_frame_index
        if current_frame == self._attack_state.last_frame_checked:
            return False
            
        self._attack_state.last_frame_checked = current_frame
        return True
    
    def register_hit(self) -> None:
        """
        Mark that this attack has successfully dealt damage.
        
        Call this after applying damage to prevent the same attack
        from dealing damage multiple times.
        """
        self._attack_state.hit_connected = True
    
    def get_current_attack_damage(self) -> float:
        """
        Get the damage value for the current attack.
        
        Returns:
            Damage value if attacking, 0.0 otherwise.
        """
        if self._attack_state.config is None:
            return 0.0
        return self._attack_state.config.damage
    
    def get_current_attack_knockback(self) -> float:
        """
        Get the knockback value for the current attack.
        
        Returns:
            Knockback force if attacking, 0.0 otherwise.
        """
        if self._attack_state.config is None:
            return 0.0
        return self._attack_state.config.knockback
    
    # ─────────────────────────────────────────────────────────────────────────
    # Core Update Loop
    # ─────────────────────────────────────────────────────────────────────────
    
    def update(self, dt: Optional[float] = None, scroll_speed: int = 0) -> None:
        """
        Update skeleton state for the current frame.
        
        Args:
            dt: Delta time since last update (seconds). Currently unused
                but provided for interface compatibility.
            scroll_speed: World scroll speed for parallax movement.
        """
        # Apply world scrolling
        self.rect.x -= scroll_speed
        
        # Core update sequence
        self._apply_gravity()
        self._update_ai()
        self._update_animation()
        
        # Parent class update
        super().update(dt)
    
    def take_damage(self, amount: int = 0.5) -> None:
        """
        Apply damage to the skeleton.
        
        Transitions to HURT state if still alive, or DEATH state if
        health is depleted. Ignores damage if already hurt or dying.
        
        Args:
            amount: Damage points to apply.
        """
        # Invulnerable during hurt/death states
        if self._state in (SkeletonState.HURT, SkeletonState.DEATH):
            return
            
        self._health = max(0, self._health - amount)
        self._animation_index = 0.0
        self._attack_state.reset()
        
        if self._health <= 0:
            self._state = SkeletonState.DEATH
        else:
            self._state = SkeletonState.HURT
    
    # ─────────────────────────────────────────────────────────────────────────
    # Private: AI Logic
    # ─────────────────────────────────────────────────────────────────────────
    
    def _update_ai(self) -> None:
        """Process AI decision-making based on player position."""
        # No AI processing without valid player or during stagger/death
        if self._player is None:
            return
        if self._state in (SkeletonState.HURT, SkeletonState.DEATH):
            return
            
        # Calculate distances to player
        player_rect = self._player.rect
        dist_x = abs(self.rect.centerx - player_rect.centerx)
        dist_y = abs(self.rect.centery - player_rect.centery)
        
        # State machine transitions
        if self._state == SkeletonState.ATTACK:
            # Attack state handles its own exit in animation update
            return
            
        # Check for attack initiation
        if dist_x < self._attack_range and dist_y < self._vertical_tolerance:
            self._begin_attack()
        # Check for chase initiation
        elif dist_x < self._detection_range and dist_y < self._vertical_tolerance:
            self._state = SkeletonState.CHASE
        else:
            self._state = SkeletonState.IDLE
            
        # Execute chase movement
        if self._state == SkeletonState.CHASE:
            self._chase_player(player_rect)
    
    def _begin_attack(self) -> None:
        """Initialize a new attack sequence with random attack selection."""
        self._state = SkeletonState.ATTACK
        self._animation_index = 0.0
        
        # Randomly select attack type and configure
        if random.random() < 0.5:
            self._current_frames = self._attack_frames
            self._attack_state.begin(self.ATTACK_1_CONFIG)
        else:
            self._current_frames = self._attack2_frames
            self._attack_state.begin(self.ATTACK_2_CONFIG)
    
    def _chase_player(self, player_rect: pg.Rect) -> None:
        """Move towards the player's position."""
        if self.rect.centerx > player_rect.centerx:
            self.rect.x -= self._speed
            self._facing_left = True
        else:
            self.rect.x += self._speed
            self._facing_left = False
    
    # ─────────────────────────────────────────────────────────────────────────
    # Private: Physics
    # ─────────────────────────────────────────────────────────────────────────
    
    def _apply_gravity(self) -> None:
        """Apply gravitational acceleration and ground collision."""
        self._gravity += 1.0
        self.rect.y += int(self._gravity)
        
        # Ground collision
        if self.rect.bottom >= self._ground_y:
            self.rect.bottom = self._ground_y
            self._gravity = 0.0
    
    # ─────────────────────────────────────────────────────────────────────────
    # Private: Animation
    # ─────────────────────────────────────────────────────────────────────────
    
    def _update_animation(self) -> None:
        """Update animation frame based on current state."""
        match self._state:
            case SkeletonState.DEATH:
                self._animate_death()
            case SkeletonState.HURT:
                self._animate_hurt()
            case SkeletonState.ATTACK:
                self._animate_attack()
            case SkeletonState.CHASE:
                self._animate_walk()
            case SkeletonState.IDLE:
                self._animate_idle()
                
        self._apply_frame()
    
    def _animate_death(self) -> None:
        """Process death animation with removal on completion."""
        self._current_frames = self._death_frames
        self._animation_index += self._ANIM_SPEED_DEATH
        
        if self._animation_index >= len(self._current_frames):
            self.kill()
    
    def _animate_hurt(self) -> None:
        """Process hurt animation with return to idle on completion."""
        self._current_frames = self._hurt_frames
        self._animation_index += self._ANIM_SPEED_HURT
        
        if self._animation_index >= len(self._current_frames):
            self._state = SkeletonState.IDLE
            self._animation_index = 0.0
    
    def _animate_attack(self) -> None:
        """Process attack animation with return to idle on completion."""
        self._animation_index += self._ANIM_SPEED_ATTACK
        
        if self._animation_index >= len(self._current_frames):
            self._state = SkeletonState.IDLE
            self._animation_index = 0.0
            self._current_frames = self._idle_frames
            self._attack_state.reset()
    
    def _animate_walk(self) -> None:
        """Process looping walk animation."""
        self._current_frames = self._walk_frames
        self._animation_index += self._ANIM_SPEED_WALK
        
        if self._animation_index >= len(self._current_frames):
            self._animation_index = 0.0
    
    def _animate_idle(self) -> None:
        """Process looping idle animation."""
        self._current_frames = self._idle_frames
        self._animation_index += self._ANIM_SPEED_IDLE
        
        if self._animation_index >= len(self._current_frames):
            self._animation_index = 0.0
    
    def _apply_frame(self) -> None:
        """Apply the current frame to the sprite image with facing direction."""
        frame_index = min(
            int(self._animation_index),
            len(self._current_frames) - 1
        )
        self.image = self._current_frames[frame_index]
        
        if self._facing_left:
            self.image = pg.transform.flip(self.image, True, False)
    
    # ─────────────────────────────────────────────────────────────────────────
    # Rendering
    # ─────────────────────────────────────────────────────────────────────────
    
    def draw(self, surface: pg.Surface) -> None:
        """
        Draw the skeleton and UI elements.
        
        Args:
            surface: Target surface for rendering.
        """
        super().draw(surface)
        
        # Draw health bar when damaged and alive
        if self._health < self._max_health and self._state != SkeletonState.DEATH:
            self._draw_health_bar(surface)
    
    def _draw_health_bar(self, surface: pg.Surface) -> None:
        """Render the health bar above the skeleton."""
        bar_width: int = 40
        bar_height: int = 5
        bar_x: int = self.rect.centerx - bar_width // 2
        bar_y: int = self.rect.top - 10
        
        # Background (empty health)
        pg.draw.rect(
            surface,
            (50, 50, 50),
            (bar_x, bar_y, bar_width, bar_height),
        )
        
        # Current health (red fill)
        health_ratio = self._health / self._max_health
        pg.draw.rect(
            surface,
            (255, 0, 0),
            (bar_x, bar_y, int(bar_width * health_ratio), bar_height),
        )