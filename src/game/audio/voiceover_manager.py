"""
VoiceoverManager — Lightweight runtime playback manager for pre-baked voiceover audio.

Loads the voice manifest at startup, maps line IDs to .wav file paths,
and plays them on a dedicated pygame.mixer.Channel during cutscenes.

Gracefully handles missing audio files — the game continues with text-only dialogue.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, Optional

import pygame as pg


class VoiceoverManager:
    """Manages loading and playing pre-baked voiceover .wav files."""

    # Dedicated mixer channel index for voiceovers (high number to avoid collisions)
    _VO_CHANNEL_ID = 7

    def __init__(self, manifest_path: str = "tools/voice_manifest.json") -> None:
        self._manifest_path: str = manifest_path
        self._lines: Dict[str, str] = {}  # line_id -> absolute .wav path
        self._channel: Optional[pg.mixer.Channel] = None
        self._current_line_id: Optional[str] = None
        self._loaded: bool = False
        self._sound_cache: Dict[str, pg.mixer.Sound] = {}

    def load_manifest(self) -> bool:
        """
        Load voice manifest and build the line_id -> .wav path lookup.
        Returns True if manifest was loaded, False otherwise.
        """
        if not os.path.exists(self._manifest_path):
            print(f"[VoiceoverManager] Manifest not found: {self._manifest_path}")
            return False

        try:
            with open(self._manifest_path, "r") as f:
                manifest = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            print(f"[VoiceoverManager] Failed to load manifest: {e}")
            return False

        output_dir = manifest.get("output_dir", "assets/audio/voiceovers")
        lines = manifest.get("lines", [])

        self._lines.clear()
        for line in lines:
            line_id = line.get("id")
            output_file = line.get("output_file")
            if line_id and output_file:
                wav_path = os.path.join(output_dir, output_file)
                self._lines[line_id] = wav_path

        # Reserve a mixer channel
        try:
            if pg.mixer.get_init():
                num_channels = pg.mixer.get_num_channels()
                if num_channels <= self._VO_CHANNEL_ID:
                    pg.mixer.set_num_channels(self._VO_CHANNEL_ID + 1)
                self._channel = pg.mixer.Channel(self._VO_CHANNEL_ID)
        except Exception as e:
            print(f"[VoiceoverManager] Could not reserve mixer channel: {e}")
            self._channel = None

        self._loaded = True
        print(f"[VoiceoverManager] Loaded {len(self._lines)} voice line(s)")
        return True

    def play_line(self, line_id: str, volume: float = 0.85) -> bool:
        """
        Play a voiceover line by its manifest ID.

        Returns True if playback started, False if file missing or error.
        """
        if not self._loaded or not self._channel:
            return False

        wav_path = self._lines.get(line_id)
        if not wav_path:
            return False

        if not os.path.exists(wav_path):
            print(f"[VoiceoverManager] Audio file missing for '{line_id}': {wav_path}")
            return False

        # Stop any currently playing voiceover
        self.stop()

        try:
            # Use cache to avoid reloading the same sound
            if line_id not in self._sound_cache:
                sound = pg.mixer.Sound(wav_path)
                self._sound_cache[line_id] = sound
            else:
                sound = self._sound_cache[line_id]

            sound.set_volume(volume)
            self._channel.play(sound)
            self._current_line_id = line_id
            return True
        except Exception as e:
            print(f"[VoiceoverManager] Playback error for '{line_id}': {e}")
            return False

    def stop(self, fadeout_ms: int = 200) -> None:
        """Stop any currently playing voiceover with optional fade-out."""
        if self._channel and self._channel.get_busy():
            if fadeout_ms > 0:
                self._channel.fadeout(fadeout_ms)
            else:
                self._channel.stop()
        self._current_line_id = None

    def is_playing(self) -> bool:
        """Check if a voiceover is currently playing."""
        if self._channel:
            return self._channel.get_busy()
        return False

    @property
    def current_line(self) -> Optional[str]:
        """Return the line_id of the currently playing voiceover, or None."""
        if self.is_playing():
            return self._current_line_id
        return None

    def has_line(self, line_id: str) -> bool:
        """Check if a voice line exists in the manifest AND on disk."""
        wav_path = self._lines.get(line_id)
        if not wav_path:
            return False
        return os.path.exists(wav_path)

    def cleanup(self) -> None:
        """Release cached sounds and channel."""
        self.stop(fadeout_ms=0)
        self._sound_cache.clear()
        self._lines.clear()
        self._loaded = False
