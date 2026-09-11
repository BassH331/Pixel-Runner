"""
Unit tests for AnimatedDialogueRenderer typewriter and letter scaling system.
"""

import time
import pytest
import pygame as pg

pg.init()
pg.font.init()

from src.game.ui.animated_dialogue_renderer import AnimatedDialogueRenderer


def test_renderer_initialization():
    renderer = AnimatedDialogueRenderer(typing_speed=30.0, scale_duration=1.0, max_scale=1.8)
    renderer.set_text("Hello World")
    assert renderer.current_char_count == 0
    assert not renderer.is_complete


def test_typewriter_progress_and_birth_times():
    renderer = AnimatedDialogueRenderer(typing_speed=10.0, scale_duration=1.0)
    renderer.set_text("Test string")
    
    # Advance 0.5s -> should reveal 5 chars
    renderer.update(0.5)
    assert renderer.current_char_count == 5
    assert len(renderer._birth_times) == 5

    # Advance 1.0s more -> should reveal rest of characters
    renderer.update(1.0)
    assert renderer.current_char_count == len("Test string")
    assert renderer.is_complete


def test_skip_to_end():
    renderer = AnimatedDialogueRenderer(typing_speed=10.0, scale_duration=1.0)
    renderer.set_text("Long cutscene dialogue text")
    renderer.skip_to_end()
    assert renderer.is_complete
    assert renderer.current_char_count == len("Long cutscene dialogue text")
    assert len(renderer._birth_times) == len("Long cutscene dialogue text")


def test_render_drawing():
    surface = pg.Surface((800, 600))
    font = pg.font.SysFont("arial", 20)
    renderer = AnimatedDialogueRenderer(typing_speed=50.0)
    renderer.set_text("Sample dialogue line for testing standard typewriter display.")
    renderer.update(0.2)  # reveal some characters
    
    rect = pg.Rect(50, 50, 700, 300)
    height = renderer.render(surface, font, rect, color=(255, 215, 80))
    assert height > 0
