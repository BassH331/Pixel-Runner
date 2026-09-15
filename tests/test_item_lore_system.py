"""
Unit tests for ItemLoreSystem and memory flashback mechanics.
"""
import pytest
import pygame as pg

# Initialize headless video driver for testing
pg.init()
pg.display.set_mode((1, 1), pg.NOFRAME)

from src.game.systems.item_lore_system import ItemLoreSystem, RelicData


def test_item_lore_system_initialization():
    system = ItemLoreSystem.get_instance()
    assert len(system.relics) == 6
    assert "shattered_gauntlet" in system.relics
    assert "voragis_inkwell" in system.relics
    assert "candoras_tear" in system.relics


def test_relic_discovery_triggers_flashback():
    system = ItemLoreSystem.get_instance()
    assert system.active_flashback is None

    result = system.discover_relic("shattered_gauntlet")
    assert result is True
    assert system.active_flashback is not None
    assert system.active_flashback.id == "shattered_gauntlet"
    assert system.active_flashback.discovered is True
    assert "rain and stone dust" in system.active_flashback.memory_text
    assert system.flashback_timer == 3.5


def test_flashback_timer_decay():
    system = ItemLoreSystem.get_instance()
    system.discover_relic("candoras_tear")
    assert system.active_flashback is not None

    system.update(2.0)
    assert system.flashback_timer == 1.5
    assert system.active_flashback is not None

    system.update(2.0)
    assert system.flashback_timer == 0.0
    assert system.active_flashback is None
