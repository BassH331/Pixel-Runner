from __future__ import annotations

from typing import Type, TypeVar, Optional, Dict, Any, List
import random
import pygame as pg

from v3x_zulfiqar_gideon.systems import Spawner, SpawnConfig
from src.game.entities.enemy import Enemy
from src.game.entities.skeleton import Skeleton

# Type variable for spawner subclasses
T = TypeVar('T', bound='Spawner')


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
    def entity_type(self) -> Type[Skeleton]:
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
    
    def spawn(self, center_pos: pg.math.Vector2, game_time: int) -> Skeleton:
        """Spawn a new skeleton."""
        from src.game.entities.player import Player  # Avoid circular import
        
        # Calculate spawn position
        spawn_x = center_pos.x + random.randint(
            self.config.min_distance,
            self.config.max_distance
        )
        spawn_y = center_pos.y + self.config.spawn_y_offset
        
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
    def entity_type(self) -> Type[Enemy]:
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
    
    def spawn(self, center_pos: pg.math.Vector2, game_time: int) -> Enemy:
        """Spawn a new bat or bat group."""
        # Calculate spawn position (random around center)
        angle = random.uniform(0, 2 * 3.14159)
        distance = random.randint(
            self.config.min_distance,
            self.config.max_distance
        )
        
        spawn_x = center_pos.x + distance * pg.math.Vector2(1, 0).rotate(angle).x
        spawn_y = center_pos.y + distance * pg.math.Vector2(1, 0).rotate(angle).y
        
        # Create bat instance
        bat = Enemy()
        bat.rect.midbottom = (spawn_x, spawn_y)
        
        # Update spawn time
        self._last_spawn_time = game_time
        
        return bat
