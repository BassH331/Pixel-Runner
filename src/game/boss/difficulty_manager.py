"""Difficulty and intelligence scaling manager for the Fire Wizard boss.

Evaluates aggregated telemetry metrics, recommends AI difficulty presets,
and applies safe scaling relative to original baseline configurations.
Delegates core calculations to canonical DifficultyCore.
"""

from src.game.shared.difficulty_core import DifficultyCore


class DifficultyManager(DifficultyCore):
    """Client DifficultyManager inheriting canonical DifficultyCore logic."""
    pass
