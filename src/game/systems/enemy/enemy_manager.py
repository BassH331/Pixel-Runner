"""
Enemy management system.

This module provides a centralized system for managing all enemy spawning,
despawn, and lifecycle events in the game.
"""
from __future__ import annotations

from typing import Dict, List, Type, Optional, Set, Tuple, TypeVar
from dataclasses import dataclass, field
import pygame as pg

from .spawners import EnemySpawner, SpawnConfig
from src.game.entities.enemy import Enemy

# Type variable for enemy subclasses
E = TypeVar('E', bound=Enemy)


@dataclass
class EnemyGroup:
    """Container for a group of enemies of the same type."""
    spawner: EnemySpawner
    instances: List[Enemy] = field(default_factory=list)
    dead_enemies: Set[int] = field(default_factory=set)


class EnemyManager:
    """Manages all enemy spawning and lifecycle events."""
    
    def __init__(self, player, obstacle_group, ambient_group):
        """Initialize the enemy manager.
        
        Args:
            player: The player entity
            obstacle_group: Pygame sprite group for collidable enemies
            ambient_group: Pygame sprite group for non-collidable enemies
        """
        self.player = player
        self.obstacle_group = obstacle_group
        self.ambient_group = ambient_group
        self._spawners: Dict[Type[Enemy], EnemyGroup] = {}
        self._game_time: int = 0
    
    def register_spawner(self, spawner: EnemySpawner) -> None:
        """Register a new enemy spawner.
        
        Args:
            spawner: The spawner to register
        """
        enemy_type = spawner.enemy_type
        if enemy_type in self._spawners:
            raise ValueError(f"Spawner for {enemy_type.__name__} already registered")
        
        self._spawners[enemy_type] = EnemyGroup(spawner=spawner)
    
    def update(self, dt: float) -> None:
        """Update all managed enemies and handle spawning.
        
        Args:
            dt: Time since last update in seconds
        """
        self._game_time = pg.time.get_ticks()
        self._cleanup_dead_enemies()
        self._handle_spawning()
    
    def _cleanup_dead_enemies(self) -> None:
        """Remove dead enemies from the game world."""
        for group in self._spawners.values():
            # Remove dead enemies from instances
            group.instances = [
                enemy for enemy in group.instances 
                if not hasattr(enemy, 'is_dead') or not enemy.is_dead
            ]
    
    def _handle_spawning(self) -> None:
        """Handle spawning of new enemies based on spawner rules."""
        player_pos = pg.math.Vector2(self.player.rect.center)
        
        for group in self._spawners.values():
            spawner = group.spawner
            
            if spawner.can_spawn(len(group.instances), self._game_time):
                enemy = spawner.spawn(player_pos, self._game_time)
                
                # Add to appropriate sprite group
                if hasattr(enemy, 'is_obstacle') and enemy.is_obstacle:
                    self.obstacle_group.add(enemy)
                else:
                    self.ambient_group.add(enemy)
                
                group.instances.append(enemy)
    
    def get_enemies_of_type(self, enemy_type: Type[E]) -> List[E]:
        """Get all alive enemies of a specific type.
        
        Args:
            enemy_type: The type of enemy to retrieve
            
        Returns:
            List of alive enemies of the specified type
        """
        if enemy_type not in self._spawners:
            return []
        return [e for e in self._spawners[enemy_type].instances if not e.is_dead]
    
    def get_all_enemies(self) -> List[Enemy]:
        """Get all alive enemies.
        
        Returns:
            List of all alive enemies
        """
        enemies = []
        for group in self._spawners.values():
            enemies.extend(e for e in group.instances if not e.is_dead)
        return enemies
    
    def clear_all(self) -> None:
        """Remove all enemies from the game."""
        for group in self._spawners.values():
            for enemy in group.instances:
                if hasattr(enemy, 'kill'):
                    enemy.kill()
            group.instances.clear()
            group.dead_enemies.clear()
