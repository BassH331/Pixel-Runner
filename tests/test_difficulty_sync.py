"""
Difficulty Synchronization Unit Test (ARCH-01).
Verifies that client DifficultyManager and server DifficultyManager produce
100% identical recommendations, constants, and slider bounds for identical inputs.
"""
import os
import sys
import pytest

sys.path.insert(0, os.path.abspath("pixel-runner-api"))

from src.game.boss.difficulty_manager import DifficultyManager as ClientDifficultyManager
from api.services.difficulty import DifficultyManager as ServerDifficultyManager


def test_difficulty_manager_constants_parity():
    """Verify BASELINE_CONFIG, PRESETS, and SLIDER_BOUNDS parity across client and server."""
    client_mgr = ClientDifficultyManager()
    server_mgr = ServerDifficultyManager()

    assert client_mgr.BASELINE_CONFIG == server_mgr.BASELINE_CONFIG
    assert client_mgr.PRESETS == server_mgr.PRESETS
    assert client_mgr.SLIDER_BOUNDS == server_mgr.SLIDER_BOUNDS


def test_difficulty_manager_evaluate_sessions_parity():
    """Verify evaluate_sessions produces identical output for both client and server."""
    dummy_sessions = [
        {
            "duration_sec": 45.0,
            "active_combat_duration_sec": 40.0,
            "total_frames": 2400,
            "avg_fps": 60.0,
            "player_damage_taken": 30.0,
            "boss_damage_taken": 100.0,
            "player_hits_received": 3,
            "boss_hits_received": 10,
            "boss_attacks": 8,
            "successful_boss_attacks": 2,
            "boss_spell_casts": 4,
            "projectile_hits": 2,
            "projectile_misses": 2,
            "time_in_detection_range_frames": 1000,
            "time_in_attack_range_frames": 800,
            "boss_detected_in_range_frames": 900,
            "boss_attacked_in_range_attacks": 6,
            "bad_attacks": 0,
            "missed_opportunities": 1,
            "boss_defeated": True,
            "player_defend_frames": 100,
            "player_standing_frames": 200,
            "player_jumps": 15,
            "player_side_swaps": 4,
            "total_active_combat_frames": 2400
        }
    ]

    client_res = ClientDifficultyManager().evaluate_sessions(dummy_sessions)
    server_res = ServerDifficultyManager().evaluate_sessions(dummy_sessions)

    assert client_res == server_res
