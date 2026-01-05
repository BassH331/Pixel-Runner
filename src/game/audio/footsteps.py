from __future__ import annotations

from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from src.my_engine.audio_manager import AudioManager


class FootstepController:
    """Utility to gate repetitive footstep sounds for characters."""

    def __init__(
        self,
        audio_manager: "AudioManager",
        sound_name: str,
        interval_ms: int = 900,
        volume: float = 0.6,
    ) -> None:
        self.audio_manager = audio_manager
        self.sound_name = sound_name
        self.interval_ms = max(300, interval_ms)
        self._volume = max(0.0, min(1.0, volume))
        self._last_play_time: Optional[int] = None

    def set_volume(self, volume: float) -> None:
        """Set absolute volume (0.0 - 1.0)."""
        self._volume = max(0.0, min(1.0, volume))

    def increase_volume(self, delta: float) -> None:
        """Adjust volume relatively while clamping to valid bounds."""
        self.set_volume(self._volume + delta)

    def set_interval(self, interval_ms: int) -> None:
        """Update cadence interval while enforcing sane limits."""
        self.interval_ms = max(30, interval_ms)

    def reset(self) -> None:
        """Reset timer so the next active step plays immediately."""
        self._last_play_time = None

    def try_play(self, *, active: bool, current_time_ms: int) -> None:
        """Attempt to play the sound if active movement warrants it."""
        if not active:
            self.reset()
            return

        if self._last_play_time is None:
            self._emit(current_time_ms)
            return

        if current_time_ms - self._last_play_time >= self.interval_ms:
            self._emit(current_time_ms)

    def _emit(self, timestamp: int) -> None:
        self.audio_manager.play_sound(self.sound_name, volume=self._volume)
        self._last_play_time = timestamp
