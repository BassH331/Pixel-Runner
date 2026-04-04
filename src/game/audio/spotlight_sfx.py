import pygame as pg

import random

class SpotlightSFXManager:
    """
    Manages sound effects tied to specific spotlight sections/scenes.
    Supports instant play, fixed delays, random delays, continuous looping, 
    and randomly repeating sounds (like crackling fire).
    """
    def __init__(self, audio_manager=None, schedule=None):
        self.audio_manager = audio_manager
        self.current_section = -2
        self.sfx_schedule = schedule if schedule is not None else {}
        self.active_channels = []  # Track channels to stop them later
        
        self.section_timer = 0.0
        self.active_trackers = []

    def update(self, dt_sec: float, section_idx: int):
        if section_idx == -1:
            if self.current_section != -1:
                self.stop_all()
                self.current_section = -1
            return

        # Handle section transition
        if section_idx != self.current_section:
            self.stop_all()  # Stop sounds from the previous section
            self.current_section = section_idx
            self.section_timer = 0.0
            self._init_trackers(section_idx)

        # Update all audio trackers for the active section
        for tracker in self.active_trackers:
            tracker.update(self.section_timer, self.audio_manager, self.active_channels)

        self.section_timer += dt_sec

    def _init_trackers(self, section_idx: int):
        self.active_trackers = []
        sfx_list = self.sfx_schedule.get(section_idx, [])
        for item in sfx_list:
            if isinstance(item, str):
                self.active_trackers.append(SFXTracker({"name": item}))
            elif isinstance(item, dict):
                self.active_trackers.append(SFXTracker(item))

    def stop_all(self, fade_ms: int = 500):
        """Fade out all currently playing spotlight SFX before clearing them."""
        if self.audio_manager:
            for channel_id in self.active_channels:
                self.audio_manager.fadeout_sound(channel_id, fade_ms)
        self.active_channels.clear()


class SFXTracker:
    def __init__(self, config: dict):
        self.name = config.get("name")
        self.volume = config.get("volume", 1.0)
        self.loop = config.get("loop", False)
        self.repeat = config.get("repeat", None)
        
        self.next_play_time = self._resolve_time(config.get("delay", 0.0))
        self.played = False

    def _resolve_time(self, val):
        """Converts floats to floats, and resolves (min, max) tuples to random floats."""
        if isinstance(val, (tuple, list)) and len(val) == 2:
            return random.uniform(val[0], val[1])
        return float(val) if val is not None else 0.0

    def update(self, current_time: float, audio_manager, active_channels: list):
        if not self.played and current_time >= self.next_play_time:
            # Play the sound!
            if audio_manager and self.name:
                channel_id = audio_manager.play_sound(self.name, volume=self.volume, loop=self.loop)
                if channel_id is not None:
                    active_channels.append(channel_id)
            
            self.played = True
            
            # If the sound is meant to repeat (but not natively via pygame loops)
            if self.repeat is not None and not self.loop:
                self.next_play_time = current_time + self._resolve_time(self.repeat)
                self.played = False
