"""
Enemy management system for the game.

This package provides a flexible system for spawning and managing different
types of enemies with various behaviors and spawn patterns.
"""

from v3x_zulfiqar_gideon import EntityManager as EnemyManager, SpawnConfig
from .spawners import (
    SkeletonSpawner,
    BatSpawner,
)

__all__ = [
    'EnemyManager',
    'SkeletonSpawner',
    'BatSpawner',
    'SpawnConfig'
]

