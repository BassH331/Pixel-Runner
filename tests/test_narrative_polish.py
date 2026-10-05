"""
Unit tests for narrative polish:
- Magic book scale (1.5)
- Elimination of magenta/purple placeholder boxes
- SideNotification hold time >= 8.0s
- Blood Zombie cutscene & taunt callbacks
- Grimoire first encounter & first kill taunts
"""
import json
import os
import pytest
import pygame as pg

pg.init()
pg.display.set_mode((1, 1), pg.NOFRAME)

from src.game.ui.side_notification import SideNotification
from src.game.entities.generic_npc import GenericNPC
from src.game.entities.bloo_zombie import BloodZombie, BloodZombieState
from unittest.mock import MagicMock


def test_magic_book_dimensions_and_level_scale():
    """Verify magic book scale is set to 1.5 in both level_1.json and entity_dimensions.json."""
    with open("game_data/level_1.json", "r", encoding="utf-8") as f:
        level_data = json.load(f)

    book_event = next(
        (e for e in level_data["world_events"] if e.get("id") == 10), None
    )
    assert book_event is not None
    assert book_event["params"]["scale"] == 1.5

    with open("game_data/entity_dimensions.json", "r", encoding="utf-8") as f:
        dims = json.load(f)

    assert dims["generic_npc_magic_book_single"]["scale"] == 1.5


def test_no_purple_placeholders():
    """Verify generic NPC and player UI never create visible magenta (255, 0, 255) placeholders."""
    # Instantiating GenericNPC with nonexistent sprite dir
    npc = GenericNPC(100, 500, "nonexistent/path/xyz", "Missing Guy")
    # First frame should be transparent (alpha 0), not magenta (255, 0, 255)
    sample_color = npc.image.get_at((0, 0))
    assert sample_color.a == 0, f"Expected transparent alpha 0, got {sample_color}"


def test_side_notification_hold_time():
    """Verify side notifications hold for at least 8.0 seconds."""
    side = SideNotification(1280, 720)
    side.show("Short text", "Title")
    assert side._current_item is not None
    assert side._current_item.hold >= 8.0

    # Long text should scale even higher
    long_text = "This is a much longer narrative text intended to convey ancient grimoire taunts across the forest."
    side.show(long_text, "Title 2")
    # Queue item should have hold >= 8.5
    assert side._queue[0].hold >= 8.5


def test_blood_zombie_taunt_callback():
    """Verify Blood Zombie triggers in-character saucy taunts via callback."""
    player_mock = MagicMock()
    player_mock.rect = pg.Rect(100, 100, 32, 48)
    bz = BloodZombie(200, 100, player_mock)

    taunts_received = []
    bz.taunt_callback = lambda text, title: taunts_received.append((text, title))

    # Force trigger a taunt
    bz._last_taunt_time = 0.0
    bz._trigger_taunt("combat")
    assert len(taunts_received) == 1
    assert taunts_received[0][1] == "Blood Zombie"
    assert len(taunts_received[0][0]) > 0

    # Force hit taunt
    bz._last_taunt_time = 0.0
    bz.take_damage(10.0)
    assert len(taunts_received) >= 2


def test_level_1_wizard_and_ronin_sprite_paths():
    """Verify NPC sprite directories in level_1.json all exist on disk."""
    with open("game_data/level_1.json", "r", encoding="utf-8") as f:
        level_data = json.load(f)

    for event in level_data["world_events"]:
        if event.get("type") == "npc":
            sprite_dir = event.get("params", {}).get("sprite_dir")
            if sprite_dir:
                assert os.path.exists(sprite_dir), f"Sprite dir '{sprite_dir}' does not exist for event {event.get('id')}"
