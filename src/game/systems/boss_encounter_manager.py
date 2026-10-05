"""
Boss Encounter Manager — orchestrates pre-fight dialogue, AI freeze,
corruption-based stat scaling, and death lines for boss encounters.
"""
from __future__ import annotations

from typing import Optional, Any


class BossEncounterManager:
    """Orchestrates pre-fight dialogue, AI freeze, stat scaling, and death lines for bosses."""

    FREEZE_DURATION = 0.5          # seconds of AI freeze before dialogue starts
    DIALOGUE_LINE_DURATION = 3.5   # seconds each pre-fight line is shown

    def __init__(
        self,
        event_bus: Any,
        corruption_manager: Any,
        config: dict,
        overlay: Any,
        boss_sequence: list,
    ) -> None:
        self._event_bus = event_bus
        self._corruption_manager = corruption_manager
        self._dialogue_config: dict = config.get("boss_dialogue", {})
        self._overlay = overlay
        self._boss_sequence: list = boss_sequence
        self._sequence_index: int = 0  # tracks next expected boss in sequence

        self._active_boss: Optional[Any] = None       # boss entity currently in encounter
        self._encounter_phase: Optional[str] = None   # "freeze", "dialogue", "combat"
        self._phase_timer: float = 0.0
        self._dialogue_queue: list = []               # lines remaining to show
        self._bosses_frozen: bool = False             # whether boss AI is frozen

    # ── Public API ────────────────────────────────────────────────────────────

    def begin_encounter(self, boss_name: str, boss_entity: Any) -> None:
        """Called when a boss spawns.  boss_entity is the boss Actor instance."""
        cfg = self._dialogue_config.get(boss_name, {})
        if not cfg:
            return  # No dialogue config — skip encounter sequence

        self._active_boss = boss_entity
        self._bosses_frozen = True
        boss_entity.ai_frozen = True  # gate the entity's AI update

        # Apply corruption-based stat scaling before fight begins
        corruption = self._corruption_manager.value
        boss_entity.apply_corruption_scaling(corruption)

        # Select the corruption-variant line
        if corruption <= 33:
            variant = cfg["corruption_variants"].get("low", "")
        elif corruption <= 66:
            variant = cfg["corruption_variants"].get("mid", "")
        else:
            variant = cfg["corruption_variants"].get("high", "")

        # Build dialogue queue: variant first, then pre_fight lines
        self._dialogue_queue = list(cfg.get("pre_fight", []))
        if variant:
            self._dialogue_queue.insert(0, variant)

        self._encounter_phase = "freeze"
        self._phase_timer = self.FREEZE_DURATION

    def on_boss_died(self, boss_name: str) -> None:
        """Called when a boss's death animation completes. Shows the death line."""
        cfg = self._dialogue_config.get(boss_name, {})
        death_line = cfg.get("death_line", "")
        if death_line and self._overlay:
            show_fn = getattr(self._overlay, "show_bark", None)
            if show_fn:
                show_fn(death_line, speaker=None)  # death lines carry no speaker tint

    def update(self, dt: float) -> None:
        """Advance the encounter state machine each frame."""
        if self._encounter_phase is None:
            return

        self._phase_timer -= dt

        if self._encounter_phase == "freeze":
            if self._phase_timer <= 0:
                self._encounter_phase = "dialogue"
                self._phase_timer = self.DIALOGUE_LINE_DURATION
                self._show_next_line()

        elif self._encounter_phase == "dialogue":
            if self._phase_timer <= 0:
                if self._dialogue_queue:
                    self._phase_timer = self.DIALOGUE_LINE_DURATION
                    self._show_next_line()
                else:
                    # All lines shown — release boss AI
                    self._encounter_phase = "combat"
                    if self._active_boss is not None:
                        self._active_boss.ai_frozen = False
                    self._bosses_frozen = False

        elif self._encounter_phase == "combat":
            self._encounter_phase = None  # encounter sequence complete

    def is_boss_frozen(self) -> bool:
        return self._bosses_frozen

    def advance_sequence(self) -> None:
        """Call after each boss death to advance the sequence index."""
        if self._sequence_index < len(self._boss_sequence) - 1:
            self._sequence_index += 1

    def is_final_boss(self, boss_name: str) -> bool:
        cfg = self._dialogue_config.get(boss_name, {})
        return cfg.get("is_final", False)

    # ── Private helpers ───────────────────────────────────────────────────────

    def _show_next_line(self) -> None:
        if not self._dialogue_queue:
            return
        line = self._dialogue_queue.pop(0)
        if self._overlay:
            show_fn = getattr(self._overlay, "show_bark", None)
            if show_fn:
                show_fn(line, speaker=None)  # boss lines shown without Andras/MK tint
