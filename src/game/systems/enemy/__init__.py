"""
Enemy management system for the game.

This package provides a flexible system for spawning and managing different
types of enemies with various behaviors and spawn patterns.
"""

from .enemy_manager import EnemyManager
from .spawners import (
    EnemySpawner,
    SkeletonSpawner,
    BatSpawner,
    SpawnConfig
)

__all__ = [
    'EnemyManager',
    'EnemySpawner',
    'SkeletonSpawner',
    'BatSpawner',
    'SpawnConfig'
]
