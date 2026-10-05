"""
RelicManager — tracks collected relics, handles drop delays, applies corruption
deltas, and pushes the RelicRevealState cutscene.

Drop sequencing rules (per the plan):
  - First relic in a boss's drop list: collected immediately (0.0 s delay).
  - Second relic in a boss's drop list: collected after a 2.0 s delay.
  - Only one relic reveal is processed per frame to avoid stacking overlays.
  - Duplicate relic IDs (same ID already pending or collected) are silently skipped.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.game.systems.corruption_manager import CorruptionManager

_SECOND_RELIC_DELAY = 2.0  # seconds


class RelicManager:
    """Tracks collected relics and orchestrates the lore-reveal cutscene sequence.

    Args:
        event_bus:           Shared ``EventBus`` instance.
        corruption_manager:  ``CorruptionManager`` to push/pull corruption on collect.
        config:              Full ``storyline_config.json`` data dict.
        state_push_callback: Callable that accepts a ``State`` instance — wraps
                             ``state_manager.push``.
    """

    def __init__(self, event_bus, corruption_manager: "CorruptionManager",
                 config: dict, state_push_callback) -> None:
        self._event_bus = event_bus
        self._corruption_manager = corruption_manager
        self._config = config
        self._push_state = state_push_callback

        # Ordered list of relic IDs that have been fully collected.
        self._collected: list[str] = []

        # Pending drops: list of (relic_id, corruption_delta, timer_remaining).
        # When timer_remaining <= 0 the relic is collected on the next update tick.
        self._pending_drops: list[tuple[str, float, float]] = []

        # Final boss pending: if set, FinalBossDefeated is emitted after pending queue drains.
        self._final_boss_name: str | None = None

        # Subscribe to RelicDropped events.
        from src.game.systems.custom_events import RelicDropped
        event_bus.subscribe(RelicDropped, self._on_relic_dropped)

    # ── Event handler ─────────────────────────────────────────────────────────

    def _on_relic_dropped(self, event) -> None:
        """Receive a RelicDropped event and queue the relic for collection.

        The delay is determined by how many relics for this boss are already
        in the pending queue: first queued = 0 s, second queued = 2 s.
        Already-collected or already-pending relic IDs are skipped.
        """
        relic_id: str = event.relic_id
        delta: float = float(event.corruption_delta)

        if relic_id in self._collected:
            return
        if any(r[0] == relic_id for r in self._pending_drops):
            return

        # Count how many relics from the same boss drop are already queued so
        # we can assign the correct positional delay (0 s or 2 s).
        existing_pending = len(self._pending_drops)
        timer = 0.0 if existing_pending == 0 else _SECOND_RELIC_DELAY

        self._pending_drops.append((relic_id, delta, timer))
        print(f"[RelicManager] Queued '{relic_id}' (delta={delta:+.1f}, delay={timer}s)")

    # ── Update ────────────────────────────────────────────────────────────────

    def update(self, dt: float) -> None:
        """Tick down pending timers and collect relics when ready.

        Only one relic is collected per frame to prevent overlapping reveals.
        """
        if not self._pending_drops:
            # If the final boss was flagged and all relics are collected, emit now.
            if self._final_boss_name is not None:
                self._emit_final_boss_defeated(self._final_boss_name)
                self._final_boss_name = None
            return

        # Decrement all timers but only collect the first ready one this frame.
        updated: list[tuple[str, float, float]] = []
        collected_one = False

        for relic_id, delta, timer in self._pending_drops:
            timer -= dt
            if timer <= 0.0 and not collected_one:
                self._collect_relic(relic_id, delta)
                collected_one = True
                # Don't re-append: relic is consumed.
            else:
                updated.append((relic_id, delta, timer))

        self._pending_drops = updated

    # ── Collect ───────────────────────────────────────────────────────────────

    def _collect_relic(self, relic_id: str, delta: float) -> None:
        """Mark relic as collected, apply corruption delta, and push the reveal state."""
        if relic_id in self._collected:
            return

        self._collected.append(relic_id)

        # Apply corruption shift.
        if delta > 0:
            self._corruption_manager.add(delta)
        elif delta < 0:
            self._corruption_manager.reduce(abs(delta))

        # Push the relic reveal cutscene.
        from src.game.states.relic_reveal_state import RelicRevealState
        relic_data = self._config.get("relics", {}).get(relic_id, {})
        self._push_state(RelicRevealState(None, relic_id, relic_data))
        print(f"[RelicManager] Collected '{relic_id}' (corruption={self._corruption_manager.value:.1f})")

    # ── Public API ────────────────────────────────────────────────────────────

    def set_final_boss_pending(self, boss_name: str) -> None:
        """Mark that FinalBossDefeated should be emitted once the drop queue drains.

        If there are no pending relics at the time of the call the event is
        emitted immediately on the next update tick.
        """
        self._final_boss_name = boss_name

    def _emit_final_boss_defeated(self, boss_name: str) -> None:
        """Emit the FinalBossDefeated event via the event bus."""
        from src.game.systems.custom_events import FinalBossDefeated
        event = FinalBossDefeated(
            corruption_value=self._corruption_manager.value,
            relics_collected=self.collected_ids(),
            boss_name=boss_name,
        )
        self._event_bus.emit(event)
        print(
            f"[RelicManager] FinalBossDefeated emitted "
            f"(boss={boss_name}, corruption={self._corruption_manager.value:.1f})"
        )

    def is_collected(self, relic_id: str) -> bool:
        """Return True if the relic has already been collected."""
        return relic_id in self._collected

    def collected_ids(self) -> list[str]:
        """Return an ordered copy of all collected relic IDs."""
        return list(self._collected)

    def get_lore_text(self, relic_id: str) -> str:
        """Return the lore string for a relic from the config."""
        return self._config.get("relics", {}).get(relic_id, {}).get("lore", "")
