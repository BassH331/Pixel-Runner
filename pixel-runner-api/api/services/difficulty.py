"""Difficulty recommendation logic for the Fire Wizard boss.

Imports canonical DifficultyCore from src/game/shared/difficulty_core.py
and provides cloud database row conversion helpers.
"""

import sys
import os
from typing import Any, Dict

# Ensure src module root is importable
_game_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
if _game_root not in sys.path:
    sys.path.insert(0, _game_root)

from src.game.shared.difficulty_core import DifficultyCore

# Alias DifficultyManager to canonical DifficultyCore for API services compatibility
DifficultyManager = DifficultyCore


def row_to_evaluation_dict(row: Dict[str, Any]) -> Dict[str, Any]:
    """Translate a pixel_runner.sessions row into the shape evaluate_sessions() expects."""
    avg_fps = float(row.get("average_fps") or 60.0)
    total_active_frames = float(row.get("total_active_combat_frames") or 0.0)
    return {
        "duration_sec": float(row.get("duration_seconds") or 0.0),
        "active_combat_duration_sec": total_active_frames / max(1.0, avg_fps),
        "total_frames": int(row.get("total_frames") or 0),
        "avg_fps": avg_fps,
        "player_damage_taken": float(row.get("player_damage_taken") or 0.0),
        "boss_damage_taken": float(row.get("boss_damage_taken") or 0.0),
        "player_hits_received": int(row.get("player_hits_received") or 0),
        "boss_hits_received": int(row.get("boss_hits_received") or 0),
        "boss_attacks": int(row.get("boss_attacks") or 0),
        "successful_boss_attacks": float(row.get("successful_boss_attacks") or 0.0),
        "boss_spell_casts": int(row.get("boss_spell_casts") or 0),
        "projectile_hits": int(row.get("projectile_hits") or 0),
        "projectile_misses": int(row.get("projectile_misses") or 0),
        "time_in_detection_range_frames": 0,
        "time_in_attack_range_frames": 0,
        "boss_detected_in_range_frames": 0,
        "boss_attacked_in_range_attacks": 0,
        "bad_attacks": 0,
        "missed_opportunities": 0,
        "malformed_lines": 0,
        "boss_defeated": bool(row.get("boss_defeated") or False),
        "player_defend_frames": int(row.get("player_defend_frames") or 0),
        "player_standing_frames": int(row.get("player_standing_frames") or 0),
        "player_jumps": int(row.get("player_jumps") or 0),
        "player_side_swaps": int(row.get("player_side_swaps") or 0),
        "total_active_combat_frames": int(total_active_frames),
    }
