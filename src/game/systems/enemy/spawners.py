"""
Spawner classes for different enemy types.

This module provides base and specific spawner implementations for creating
and managing enemy entities in the game world.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Type, TypeVar, Protocol, Optional, Dict, Any, List
import random
import pygame as pg

from src.game.entities.enemy import Enemy
from src.game.entities.skeleton import Skeleton

# Type variable for spawner subclasses
T = TypeVar('T', bound='EnemySpawner')


@dataclass
class SpawnConfig:
    """Configuration for enemy spawning."""
    max_count: int = 3
    min_distance: int = 100
    max_distance: int = 300
    respawn_delay: int = 5000
    spawn_y_offset: int = 0
    spawn_area_padding: int = 50
    spawn_weights: Dict[str, float] = field(default_factory=dict)
    spawn_conditions: Dict[str, Any] = field(default_factory=dict)


class EnemySpawner(Protocol):
    """Base protocol for all enemy spawners."""
    
    @property
    def enemy_type(self) -> Type[Enemy]:
        """Return the type of enemy this spawner creates."""
        ...
    
    @property
    def config(self) -> SpawnConfig:
        """Return the spawn configuration."""
        ...
    
    def can_spawn(self, current_count: int, game_time: int) -> bool:
        """Check if a new enemy can be spawned."""
        ...
    
    def spawn(self, player_pos: pg.math.Vector2, game_time: int) -> Enemy:
        """Spawn a new enemy instance."""
        ...


class SkeletonSpawner:
    """Spawner for skeleton enemies."""
    
    def __init__(self, config: Optional[SpawnConfig] = None):
        self._config = config or SpawnConfig(
            max_count=3,
            min_distance=150,
            max_distance=400,
            respawn_delay=5000,
            spawn_y_offset=-50,
            spawn_weights={
                'normal': 0.8,
                'elite': 0.15,
                'boss': 0.05
            }
        )
        self._last_spawn_time: int = 0
    
    @property
    def enemy_type(self) -> Type[Skeleton]:
        return Skeleton
    
    @property
    def config(self) -> SpawnConfig:
        return self._config
    
    def can_spawn(self, current_count: int, game_time: int) -> bool:
        """Check if a new skeleton can be spawned."""
        if current_count >= self.config.max_count:
            return False
            
        time_since_last_spawn = game_time - self._last_spawn_time
        return time_since_last_spawn >= self.config.respawn_delay
    
    def spawn(self, player_pos: pg.math.Vector2, game_time: int) -> Skeleton:
        """Spawn a new skeleton."""
        from src.game.entities.player import Player  # Avoid circular import
        
        # Calculate spawn position (right side of screen, random y)
        spawn_x = player_pos.x + random.randint(
            self.config.min_distance,
            self.config.max_distance
        )
        spawn_y = player_pos.y + self.config.spawn_y_offset
        
        # Create skeleton instance
        skeleton = Skeleton(
            x=spawn_x,
            y=spawn_y,
            player=Player(0, 0, None)  # Dummy player, will be set by game state
        )
        
        # Update spawn time
        self._last_spawn_time = game_time
        
        return skeleton


class BatSpawner:
    """Spawner for bat enemies."""
    
    def __init__(self, config: Optional[SpawnConfig] = None):
        self._config = config or SpawnConfig(
            max_count=5,
            min_distance=200,
            max_distance=500,
            respawn_delay=3000,
            spawn_y_offset=0,
            spawn_weights={
                'normal': 0.9,
                'swarm': 0.1
            }
        )
        self._last_spawn_time: int = 0
    
    @property
    def enemy_type(self) -> Type[Enemy]:
        from src.game.entities.enemy import Enemy  # Avoid circular import
        return Enemy
    
    @property
    def config(self) -> SpawnConfig:
        return self._config
    
    def can_spawn(self, current_count: int, game_time: int) -> bool:
        """Check if new bats can be spawned."""
        if current_count >= self.config.max_count:
            return False
            
        time_since_last_spawn = game_time - self._last_spawn_time
        return time_since_last_spawn >= self.config.respawn_delay
    
    def spawn(self, player_pos: pg.math.Vector2, game_time: int) -> Enemy:
        """Spawn a new bat or bat group."""
        from src.game.entities.enemy import Enemy  # Avoid circular import
        
        # Calculate spawn position (random around player)
        angle = random.uniform(0, 2 * 3.14159)
        distance = random.randint(
            self.config.min_distance,
            self.config.max_distance
        )
        
        spawn_x = player_pos.x + distance * pg.math.Vector2(1, 0).rotate(angle).x
        spawn_y = player_pos.y + distance * pg.math.Vector2(1, 0).rotate(angle).y
        
        # Create bat instance
        bat = Enemy()
        bat.rect.midbottom = (spawn_x, spawn_y)
        
        # Update spawn time
        self._last_spawn_time = game_time
        
        return bat
