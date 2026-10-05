"""
EndingManager — resolves the game's ending based on final corruption value
and pushes the correct EndingState onto the state stack.

Subscribed to the FinalBossDefeated event by GameState.__init__.
"""

from __future__ import annotations

from src.game.states.ending_state import EndingState, EndingType
from src.game.systems.custom_events import FinalBossDefeated


class EndingManager:
    """Reads corruption on final boss death, selects an ending, and pushes EndingState.

    Args:
        state_manager: The V3X StateManager instance.
        config:        Full ``storyline_config.json`` data dict.
        save_manager:  Optional SaveManager class (or instance) for persisting run data.
    """

    def __init__(self, state_manager, config: dict, save_manager=None) -> None:
        self._state_manager = state_manager
        self._config        = config
        self._save_manager  = save_manager

    # ── Public API ────────────────────────────────────────────────────────────

    def resolve(self, event: FinalBossDefeated) -> None:
        """Select and push the appropriate ending state for *event*."""
        corruption = event.corruption_value

        if corruption >= 75:
            ending_type = EndingType.DARK
            ending_key  = "dark"
        elif corruption <= 25:
            ending_type = EndingType.LIGHT
            ending_key  = "light"
        else:
            ending_type = EndingType.AMBIGUOUS
            ending_key  = "ambiguous"

        ending_data = self._config.get("endings", {}).get(ending_key, {})

        # Persist result — fire-and-forget; failure must never crash the ending.
        if self._save_manager is not None:
            self._save_result(corruption, ending_key, event.relics_collected)

        # Push EndingState — it calls manager.set(MainMenuState) when done,
        # which clears the entire stack and returns to the main menu.
        self._state_manager.push(
            EndingState(self._state_manager, ending_type, ending_data, corruption)
        )
        print(
            f"[EndingManager] Ending resolved: {ending_key.upper()} "
            f"(corruption={corruption:.1f}%)"
        )

    # ── Private helpers ───────────────────────────────────────────────────────

    def _save_result(
        self, corruption: float, ending_key: str, relics: list
    ) -> None:
        """Persist final run data to the auto-save slot via SaveManager."""
        try:
            from src.game.services.save_manager import SaveSlot, SaveManager

            # Load existing auto slot (if any) so we preserve other fields.
            existing = SaveManager.load("auto")
            if existing is None:
                existing = SaveSlot(slot_id="auto")

            # Attach ending metadata as extra attributes on the slot dict,
            # then write back.  SaveSlot.to_dict() only serialises dataclass
            # fields, so we patch the raw dict before dumping.
            slot_dict = existing.to_dict()
            slot_dict["final_corruption"] = round(corruption, 2)
            slot_dict["ending"]           = ending_key
            slot_dict["relics_collected"] = relics

            # Write atomically by rebuilding a SaveSlot from the merged dict
            # (unknown keys are stripped by SaveSlot.from_dict).
            merged_slot = SaveSlot.from_dict(slot_dict)

            import json
            import os
            import pathlib
            import tempfile

            save_dir  = pathlib.Path("save_data")
            save_dir.mkdir(parents=True, exist_ok=True)
            target    = save_dir / "slot_auto.json"

            # We need to persist extra keys that SaveSlot doesn't have as fields,
            # so write the full merged dict directly (not via SaveSlot.to_dict).
            import time
            slot_dict["slot_id"]   = "auto"
            slot_dict["timestamp"] = time.strftime("%Y-%m-%d %H:%M:%S")

            with tempfile.NamedTemporaryFile(
                "w", dir=save_dir, delete=False, suffix=".tmp"
            ) as tmp:
                json.dump(slot_dict, tmp, indent=2)
                tmp_path = tmp.name

            os.replace(tmp_path, target)
            print(
                f"[EndingManager] Saved ending result: {ending_key}, "
                f"corruption={corruption:.2f}, relics={relics}"
            )

        except Exception as err:
            # Save failure must never prevent the ending from showing.
            print(f"[EndingManager] Save failed (non-fatal): {err}")
