"""Unit tests for the AudioManager's channel-level volume implementation."""

import pygame as pg
import pytest
from unittest.mock import patch, MagicMock

# Ensure we import AudioManager correctly from the dependency
from v3x_zulfiqar_gideon.audio_manager import AudioManager, SoundPriority


@pytest.fixture(scope="function", autouse=True)
def setup_pygame_mixer():
    # Initialize pygame mixer for testing
    if not pg.get_init():
        pg.init()
    if not pg.mixer.get_init():
        try:
            pg.mixer.init()
        except pg.error:
            # Fallback if audio driver not available
            pass
    yield


def test_channel_level_volume_play_sound():
    if not pg.mixer.get_init():
        pytest.skip("Pygame mixer is not initialized (no audio device)")

    # Instantiate AudioManager
    am = AudioManager(max_channels=8)
    
    # Create a dummy Sound object with silent buffer
    # 44100Hz, 16-bit, mono: 2 bytes per sample. 1000 bytes = 500 samples.
    dummy_sound = pg.mixer.Sound(buffer=b'\x00' * 1000)
    am.sound_library["spawn_sfx"] = dummy_sound  # type: ignore

    # Let's set some master and sfx volumes
    am.master_volume = 0.8
    am.sfx_volume = 0.5 # settings might override this on init, so set it explicitly
    
    # Play sound at raw volume = 0.25
    # Expected final volume = 0.25 * 0.5 * 0.8 = 0.1
    channel_id = am.play_sound("spawn_sfx", volume=0.25)
    
    assert channel_id is not None
    channel = am.channels[channel_id]
    
    # Assert that the Sound object itself remains at full volume (1.0)
    assert dummy_sound.get_volume() == pytest.approx(1.0, abs=0.01)
    
    # Assert that the channel's volume is set to the calculated final volume
    assert channel.get_volume() == pytest.approx(0.1, abs=0.01)


def test_channel_level_volume_play_music():
    if not pg.mixer.get_init():
        pytest.skip("Pygame mixer is not initialized (no audio device)")

    am = AudioManager(max_channels=8)
    dummy_sound = pg.mixer.Sound(buffer=b'\x00' * 1000)
    am.sound_library["bg_music"] = dummy_sound  # type: ignore

    am.master_volume = 1.0
    am.music_volume = 0.8
    
    # Play music at custom volume = 0.5
    # Expected final volume = 0.5 * 0.8 * 1.0 = 0.4
    am.play_music("bg_music", volume=0.5, loop=True)
    
    music_channel = am.channels[0]
    
    # Assert that the Sound object remains at 1.0
    assert dummy_sound.get_volume() == pytest.approx(1.0, abs=0.01)
    # Assert music channel volume
    assert music_channel.get_volume() == pytest.approx(0.4, abs=0.01)
    # Assert that volume factor was tracked
    assert am.current_music_volume_factor == pytest.approx(0.5, abs=0.01)

    # Change music volume settings dynamically
    am.set_music_volume(0.4) # new music volume
    # Expected channel volume = 0.5 (factor) * 0.4 (music) * 1.0 (master) = 0.2
    assert music_channel.get_volume() == pytest.approx(0.2, abs=0.01)

    # Change master volume dynamically
    am.set_master_volume(0.5) # new master volume
    # Expected channel volume = 0.5 (factor) * 0.4 (music) * 0.5 (master) = 0.1
    assert music_channel.get_volume() == pytest.approx(0.1, abs=0.01)
