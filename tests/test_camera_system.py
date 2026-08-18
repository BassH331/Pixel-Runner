from unittest.mock import MagicMock
import pygame as pg

pg.init()
pg.display.set_mode((1280, 720), pg.NOFRAME)

from v3x_zulfiqar_gideon import EventBus, DamageDealt, Camera


def test_camera_initialization():
    cam = Camera(1280, 720)
    assert cam.width == 1280
    assert cam.height == 720
    assert cam.x == 0.0
    assert cam.y == 0.0
    assert cam.zoom_level == 1.0


def test_camera_bounds_and_transforms():
    cam = Camera(1280, 720)
    cam.set_bounds(3000.0, 1000.0)
    assert cam.world_width == 3000.0
    assert cam.world_height == 1000.0

    cam.x = 200.0
    cam.y = 50.0
    sx, sy = cam.world_to_screen(500.0, 300.0)
    assert sx == 300.0
    assert sy == 250.0

    wx, wy = cam.screen_to_world(300.0, 250.0)
    assert wx == 500.0
    assert wy == 300.0


def test_camera_follow_deadzone():
    cam = Camera(1280, 720)
    # Player moves far to the right (x=1000)
    player_rect = pg.Rect(1000, 360, 40, 80)
    cam.follow(player_rect, dt_seconds=0.1)

    assert cam.target_x > 0.0
    assert cam.x > 0.0


def test_camera_shake_decay():
    cam = Camera(1280, 720)
    cam.shake(intensity=1.0)
    assert cam._trauma == 1.0

    cam.update(dt_seconds=0.1)
    assert cam._trauma < 1.0
    assert cam.shake_offset_x != 0.0 or cam.shake_offset_y != 0.0


def test_camera_event_bus_auto_shake():
    bus = EventBus()
    cam = Camera(1280, 720, event_bus=bus)

    assert cam._trauma == 0.0

    event = DamageDealt(
        attacker=MagicMock(),
        target=MagicMock(),
        amount=25.0,
        knockback=(10.0, -5.0),
        target_tier="boss"
    )
    bus.emit(event)

    assert cam._trauma > 0.0


def test_camera_apply_surface():
    cam = Camera(1280, 720)
    source = pg.Surface((1280, 720))
    source.fill((255, 0, 0))

    # Without shake or zoom, apply returns source surface directly
    result = cam.apply(source)
    assert result == source

    # With shake, apply returns transformed buffer
    cam.shake(0.5)
    cam.update(dt_seconds=0.01)
    result_shaken = cam.apply(source)
    assert result_shaken != source
