import pygame as pg
import os
import math
from typing import Dict, Optional, List, Tuple
from dataclasses import dataclass
from enum import IntEnum

class SoundPriority(IntEnum):
    LOW = 1
    NORMAL = 5
    HIGH = 10
    CRITICAL = 20

@dataclass
class SoundInstance:
    sound: pg.mixer.Sound
    channel: Optional[pg.mixer.Channel]
    priority: int
    volume: float = 1.0
    loop: bool = False

class AudioManager:
    def __init__(self, max_channels: int = 32):
        """
        Initialize the AudioManager.
        Assumes pg.mixer.pre_init() and pg.init() have been called externally.
        """
        self.max_channels = max_channels
        # Channels are managed by pygame, we just track usage
        self.channels = [pg.mixer.Channel(i) for i in range(max_channels)]
        self.sound_library: Dict[str, pg.mixer.Sound] = {}
        self.master_volume = 1.0
        
    def load_sound(self, sound_name: str, file_path: str) -> None:
        """Load a sound file into the sound library."""
        try:
            self.sound_library[sound_name] = pg.mixer.Sound(file_path)
        except Exception as e:
            print(f"Error loading sound {sound_name} from {file_path}: {e}")
    
    def load_sounds_from_directory(self, directory: str) -> None:
        """Load all .wav and .ogg files from a directory."""
        for filename in os.listdir(directory):
            if filename.endswith(('.wav', '.ogg')):
                name = os.path.splitext(filename)[0]
                self.load_sound(name, os.path.join(directory, filename))
    
    def _find_free_channel_id(self) -> Optional[int]:
        """Find the index of a free channel."""
        for i, channel in enumerate(self.channels):
            if not channel.get_busy():
                return i
        return None

    def _steal_channel_id(self, new_priority: int) -> Optional[int]:
        """Find the ID of the least important busy channel to interrupt."""
        # Try to find a free channel first
        free_id = self._find_free_channel_id()
        if free_id is not None:
            return free_id
            
        # If no free channel, and priority is high, steal channel 0 (simplification)
        if new_priority >= SoundPriority.HIGH:
            return 0
            
        return None
    
    def play_sound(self, sound_name: str, 
                  priority: int = SoundPriority.NORMAL,
                  volume: float = 1.0,
                  loop: bool = False,
                  location: Optional[Tuple[float, float]] = None,
                  player_pos: Optional[Tuple[float, float]] = None) -> Optional[int]:
        """
        Play a sound with optional spatial audio.
        """
        if sound_name not in self.sound_library:
            print(f"Sound not found: {sound_name}")
            return None
            
        sound = self.sound_library[sound_name]
        
        # Spatial Audio Calculation
        final_volume = volume * self.master_volume
        if location and player_pos:
            dist = math.hypot(location[0] - player_pos[0], location[1] - player_pos[1])
            max_dist = 500 # pixels
            if dist > max_dist:
                return None # Too far to hear
            # Linear attenuation
            final_volume *= (1.0 - (dist / max_dist))
            
        sound.set_volume(max(0.0, min(1.0, final_volume)))
        
        # Channel Management
        channel_id = self._find_free_channel_id()
        if channel_id is None:
            channel_id = self._steal_channel_id(priority)
            
        if channel_id is not None:
            channel = self.channels[channel_id]
            if loop:
                channel.play(sound, loops=-1)
            else:
                channel.play(sound)
            return channel_id
            
        return None
    
    def stop_sound(self, channel_id: int) -> None:
        """Stop a sound on the specified channel index."""
        if 0 <= channel_id < len(self.channels):
            self.channels[channel_id].stop()
    
    def stop_all_sounds(self) -> None:
        """Stop all currently playing sounds."""
        if not pg.mixer.get_init():
            return
        for channel in self.channels:
            channel.stop()
    
    def set_master_volume(self, volume: float) -> None:
        """Set the master volume (0.0 to 1.0)."""
        self.master_volume = max(0.0, min(1.0, volume))
    
    def update(self) -> None:
        """Update loop (placeholder for future cross-fading logic)."""
        pass
    
    def __del__(self):
        """Clean up resources."""
        self.stop_all_sounds()
        if pg.mixer.get_init():
            pg.mixer.quit()
