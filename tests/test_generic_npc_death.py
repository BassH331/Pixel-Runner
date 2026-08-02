import os
import pygame as pg
import pytest

pg.init()
pg.display.set_mode((1, 1), pg.NOFRAME)

from src.game.entities.generic_npc import GenericNPC, _GenericNPCState

def test_generic_npc_death_trigger():
    npc = GenericNPC(
        x=100,
        y=200,
        sprite_dir="assets/graphics/Necromancer/Idle",
        text="Test dialogue",
        title="Test Title",
        play_death_on_interact=True,
        death_sprite_dir="assets/graphics/Necromancer/Death"
    )
    
    assert npc.state == _GenericNPCState.IDLE
    assert npc.is_dying_or_dead is False
    assert _GenericNPCState.DEATH in npc.animations
    assert len(npc.animations[_GenericNPCState.DEATH]) == 52
    
    # Trigger death on interaction completion
    npc.trigger_death()
    
    assert npc.state == _GenericNPCState.DEATH
    assert npc.is_dying_or_dead is True
    assert npc.can_interact is False

def test_generic_npc_auto_detect_death():
    npc = GenericNPC(
        x=100,
        y=200,
        sprite_dir="assets/graphics/Necromancer/Idle",
        text="Test dialogue",
        title="Test Title",
        play_death_on_interact=True
    )
    assert npc.death_sprite_dir == "assets/graphics/Necromancer/Death"
    assert _GenericNPCState.DEATH in npc.animations
