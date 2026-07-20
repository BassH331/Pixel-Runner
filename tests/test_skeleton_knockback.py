"""Unit tests for Skeleton damage/knockback implementation."""

import pygame as pg
import pytest

from src.game.entities.skeleton import Skeleton, SkeletonState


class MockPlayer:
    def __init__(self):
        self.rect = pg.Rect(100, 100, 32, 64)
        self.facing_left = True


@pytest.fixture(scope="module", autouse=True)
def setup_pygame():
    if not pg.get_init():
        pg.init()
    if not pg.font.get_init():
        pg.font.init()
    if not pg.display.get_init() or pg.display.get_surface() is None:
        pg.display.init()
        pg.display.set_mode((1280, 720))
    yield


def test_skeleton_hurt_animation_speed():
    # Make sure HURT state config uses the accelerated animation speed
    assert Skeleton.STATE_CONFIGS[SkeletonState.HURT].animation_speed == 0.30


def test_skeleton_knockback_application():
    player = MockPlayer()
    skeleton = Skeleton(200, 600, player, tier="minion", custom_scale=1.0, custom_health=100.0)  # type: ignore

    # Initial position
    initial_x = skeleton.rect.x
    initial_y = skeleton.rect.y
    assert skeleton._knockback_vel_x == 0.0

    # Apply damage with knockback (e.g. knockback force (10.0, -5.0))
    skeleton.take_damage(5.0, knockback=(10.0, -5.0))

    # Velocity should be scaled
    assert skeleton._knockback_vel_x == 10.0 * 1.5
    assert skeleton._gravity == -5.0 * 1.2

    # Run update to ensure position changes and decay is applied
    skeleton.update(dt=1.0 / 60.0, scroll_speed=0)

    # X position should have shifted due to knockback
    assert skeleton.rect.x > initial_x
    # Knockback velocity should have decayed
    assert skeleton._knockback_vel_x == pytest.approx(15.0 * 0.8)


def test_skeleton_knockback_horizontal_fallback_lift():
    player = MockPlayer()
    skeleton = Skeleton(200, 600, player, tier="minion", custom_scale=1.0, custom_health=100.0)  # type: ignore

    # Apply damage with positive y (downward/horizontal knockback vector)
    # This should trigger the fallback vertical lift (-abs(knockback[0]) * 0.4)
    skeleton.take_damage(5.0, knockback=(10.0, 5.0))

    assert skeleton._knockback_vel_x == 10.0 * 1.5
    assert skeleton._gravity == -10.0 * 0.4
