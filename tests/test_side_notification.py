"""
Unit tests for SideNotification right-side pop-up notification system.
Validates non-blocking animations, resolution scaling, and queue handling.
"""

import pygame as pg

if not pg.get_init():
    pg.init()
if not pg.display.get_surface():
    pg.display.set_mode((1280, 720), pg.NOFRAME)

from src.game.ui.side_notification import SideNotification, NotificationState


def test_side_notification_initialization():
    notif = SideNotification(1280, 720)
    assert not notif.is_active
    assert notif._scale == 1.0
    assert notif._tab_width == 390


def test_side_notification_resolution_scaling():
    # Test 1080p resolution scaling
    notif_1080 = SideNotification(1920, 1080)
    assert notif_1080._scale == 1.5
    assert notif_1080._tab_width == int(390 * 1.5)

    # Test 4K resolution scaling
    notif_4k = SideNotification(3840, 2160)
    assert notif_4k._scale == 2.5  # Clamped to max 2.5
    assert notif_4k._tab_width == int(390 * 2.5)

    # Test smaller screen (800x600)
    notif_small = SideNotification(800, 600)
    assert notif_small._scale >= 0.65


def test_side_notification_animation_lifecycle():
    notif = SideNotification(1280, 720, slide_in_time=0.2, slide_out_time=0.2, default_hold_time=1.0)
    surface = pg.Surface((1280, 720))

    # Show notification
    notif.show("The undead fall before your blade!", "First kill!!")
    assert notif.is_active is True
    assert notif._state == NotificationState.SLIDE_IN

    # Advance during slide-in
    notif.update(0.1)
    assert notif._state == NotificationState.SLIDE_IN
    notif.draw(surface)

    # Complete slide-in -> HOLD
    notif.update(0.15)
    assert notif._state == NotificationState.HOLD
    notif.draw(surface)

    # Hold state
    notif.update(0.5)
    assert notif._state == NotificationState.HOLD

    # Complete hold -> SLIDE_OUT
    notif.update(0.6)
    assert notif._state == NotificationState.SLIDE_OUT
    notif.draw(surface)

    # Complete slide-out -> IDLE
    notif.update(0.25)
    assert notif._state == NotificationState.IDLE
    assert not notif.is_active


def test_side_notification_queue():
    notif = SideNotification(1280, 720, slide_in_time=0.1, slide_out_time=0.1, default_hold_time=0.5)
    notif.show("First message", "Notification 1")
    notif.show("Second message", "Notification 2")

    assert notif._current_item is not None
    assert notif._current_item.title == "Notification 1"
    assert len(notif._queue) == 1
    assert notif._queue[0].title == "Notification 2"

    # Fast forward through first notification
    notif.update(0.15)  # slide in done -> hold
    notif.update(0.6)   # hold done -> slide out
    notif.update(0.15)  # slide out done -> triggers next item from queue

    assert notif._current_item is not None
    assert notif._current_item.title == "Notification 2"
    assert len(notif._queue) == 0


def test_side_notification_dynamic_resize():
    notif = SideNotification(1280, 720)
    notif.show("Dynamic resize test", "Resize")

    surf_1080 = pg.Surface((1920, 1080))
    notif.draw(surf_1080)
    assert notif._screen_width == 1920
    assert notif._screen_height == 1080
    assert notif._scale == 1.5
