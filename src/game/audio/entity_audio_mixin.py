"""
EntityAudioMixin — generic, reusable mixin for frame-precise audio triggers.

Any Actor subclass (Skeleton, FireWizard, BloodZombie, GreenMonster, Enemy …)
can opt in to dynamic audio configuration by:

    1. Adding ``EntityAudioMixin`` to its base classes.
    2. Calling ``self._init_entity_audio_config(audio_manager, "entity_key")``
       at the end of ``__init__``.
    3. Calling ``self._update_animation_audio()`` inside ``update()``,
       after ``super().update(dt)``.

If the config file does not exist, an empty stub is created and the entity
simply plays no custom sounds until the editor is used to assign them.
If validation fails for any reason, the failure is logged but NEVER raises —
the game continues normally without custom audio.

Config format (game_data/<entity_key>_audio_config.json):
    {
        "sounds": {
            "sound_alias": "assets/audio/my_sound.wav",
            ...
        },
        "states": {
            "ATTACK": {"3": "sound_alias", "7": "sound_alias"},
            ...
        }
    }
"""

from __future__ import annotations

import json
import os
from typing import TYPE_CHECKING, Any, Dict, Optional

if TYPE_CHECKING:
    from v3x_zulfiqar_gideon import AudioManager


class EntityAudioMixin:
    """
    Mixin that provides frame-precise audio trigger capability to any Actor.

    Attributes set by this mixin (all prefixed _eam_ to avoid collisions):
        _eam_audio_manager     — reference to the AudioManager instance
        _eam_config            — loaded config dict (sounds + states)
        _eam_frames_played     — set of frames already played in this state cycle
        _eam_last_state        — tracks state changes to reset played set
        _eam_prev_frame_index  — detects animation loops to reset played set
    """

    # ─────────────────────────────────────────────────────────────────────────
    # Initialisation
    # ─────────────────────────────────────────────────────────────────────────

    def _init_entity_audio_config(
        self,
        audio_manager: "Optional[AudioManager]",
        entity_key: str,
    ) -> None:
        """
        Load the entity's audio config from ``game_data/<entity_key>_audio_config.json``,
        validate against its lock, and pre-load all referenced sounds.

        Args:
            audio_manager: The game's AudioManager instance.
            entity_key:    Unique string identifying this entity type, e.g.
                           ``"skeleton_minion"``, ``"blood_zombie"``, …
        """
        # Guard against mock objects in tests
        is_mock = (
            type(audio_manager).__name__ in ("MagicMock", "Mock")
            or not hasattr(audio_manager, "sound_library")
        )
        if audio_manager is None or is_mock:
            self._eam_audio_manager: Optional["AudioManager"] = None
            self._eam_config: Dict[str, Any] = {}
            self._eam_frames_played: set[int] = set()
            self._eam_last_state: Any = None
            self._eam_prev_frame_index: int = 0
            return

        self._eam_audio_manager = audio_manager
        self._eam_frames_played = set()
        self._eam_last_state = None
        self._eam_prev_frame_index = 0

        config_path = f"game_data/{entity_key}_audio_config.json"
        lock_path   = f"game_data/{entity_key}_audio_config.lock"

        # ── Auto-seed empty config if missing ────────────────────────────────
        if not os.path.exists(config_path):
            empty_config: Dict[str, Any] = {"sounds": {}, "states": {}}
            try:
                from src.game.audio.audio_lock import save_config_and_lock
                save_config_and_lock(empty_config, config_path, lock_path)
            except Exception as seed_err:
                print(
                    f"[EntityAudio:{entity_key}] Warning — could not seed "
                    f"default config: {seed_err}"
                )
                self._eam_config = {}
                return

        # ── Validate against lock (non-fatal) ────────────────────────────────
        try:
            from src.game.audio.audio_lock import verify_config_integrity
            is_valid, reason = verify_config_integrity(config_path, lock_path)
            if not is_valid:
                print(
                    f"[EntityAudio:{entity_key}] Lock mismatch — {reason}. "
                    f"Custom audio disabled until re-saved via editor."
                )
                self._eam_config = {}
                return
        except Exception as val_err:
            print(f"[EntityAudio:{entity_key}] Validation error: {val_err}")
            self._eam_config = {}
            return

        # ── Load config ───────────────────────────────────────────────────────
        try:
            with open(config_path, "r") as f:
                self._eam_config = json.load(f)
        except Exception as load_err:
            print(f"[EntityAudio:{entity_key}] Failed to load config: {load_err}")
            self._eam_config = {}
            return

        # ── Pre-load all referenced sounds ────────────────────────────────────
        sounds = self._eam_config.get("sounds", {})
        for sound_name, file_path in sounds.items():
            if file_path and sound_name not in audio_manager.sound_library:
                try:
                    audio_manager.load_sound(sound_name, file_path)
                except Exception as load_sound_err:
                    print(
                        f"[EntityAudio:{entity_key}] Could not load sound "
                        f"'{sound_name}' from '{file_path}': {load_sound_err}"
                    )

    # ─────────────────────────────────────────────────────────────────────────
    # Per-frame Update
    # ─────────────────────────────────────────────────────────────────────────

    def _update_animation_audio(self) -> None:
        """
        Must be called once per update tick (after ``super().update(dt)``).
        Checks the current animation frame and plays any assigned sound trigger.
        """
        manager = getattr(self, "_eam_audio_manager", None)
        config  = getattr(self, "_eam_config", {})
        if not manager or not config:
            return

        state = getattr(self, "state", None)
        if state is None:
            return

        state_key = state.name if hasattr(state, "name") else str(state)
        states_map = config.get("states", {})
        sound_map = states_map.get(state_key)
        if not sound_map:
            return

        current_frame = int(getattr(self, "animation_index", 0))

        # Reset played set when state changes
        last_state = getattr(self, "_eam_last_state", None)
        if last_state != state:
            self._eam_frames_played = set()
            self._eam_last_state = state

        # Reset played set when animation loops back
        prev_frame = getattr(self, "_eam_prev_frame_index", 0)
        if current_frame < prev_frame:
            self._eam_frames_played = set()
        self._eam_prev_frame_index = current_frame

        # Trigger the sound for this frame (each frame fires once per cycle)
        frames_played: set[int] = getattr(self, "_eam_frames_played", set())
        sound_name = (
            sound_map.get(current_frame)
            or sound_map.get(str(current_frame))
        )
        if sound_name and current_frame not in frames_played:
            frames_played.add(current_frame)
            self._eam_frames_played = frames_played
            try:
                manager.play_sound(sound_name)
            except Exception as play_err:
                print(
                    f"[EntityAudio] Failed to play '{sound_name}': {play_err}"
                )
