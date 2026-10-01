"""
Physics time-step regression test (PERF-01).
Verifies that vertical gravity displacement after 1 second of physics updates
remains frame-rate-independent across 30 FPS, 60 FPS, and 144 FPS.
"""
import pytest
import pygame as pg

pg.init()
pg.display.set_mode((1, 1), pg.NOFRAME)

from src.game.entities.player import Player


def simulate_gravity_fall(fps: int, duration_sec: float = 1.0) -> int:
    """Simulate duration_sec of gravity fall at target FPS and return final Y position."""
    player = Player(x=100, y=0, audio_manager=None)
    player._ground_y = None  # Freefall
    
    total_steps = int(fps * duration_sec)
    dt = 1.0 / fps
    
    for _ in range(total_steps):
        player._apply_gravity(dt)
        
    return player.rect.y


def test_gravity_frame_rate_independence():
    """Verify displacement parity across 30 FPS, 60 FPS, and 144 FPS for 1s fall."""
    y_30 = simulate_gravity_fall(30)
    y_60 = simulate_gravity_fall(60)
    y_144 = simulate_gravity_fall(144)
    
    # 60 FPS is our baseline reference
    ref_y = y_60
    
    # Assert positions at 30 FPS and 144 FPS are within 5% tolerance of 60 FPS baseline
    assert abs(y_30 - ref_y) / ref_y < 0.05, f"30 FPS position drift out of bounds: y_30={y_30}, ref_y={ref_y}"
    assert abs(y_144 - ref_y) / ref_y < 0.05, f"144 FPS position drift out of bounds: y_144={y_144}, ref_y={ref_y}"
