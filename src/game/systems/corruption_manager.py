"""
CorruptionManager — tracks and exposes the player's corruption level (0.0–100.0).

The corruption value is the central spine of the narrative system:
  - 0.0  → "pure"     (no corruption)
  - >33  → "tainted"
  - >66  → "corrupted"
  - >90  → "void"

All per-event deltas are loaded from ``storyline_config.json`` under the
``corruption_events`` key so that tuning never requires a code change.

Audio distortion (activates above 66) is deferred — complex audio threading
is out of scope for Sub-task 1.
# TODO: wire low-frequency distortion filter when corruption > 66 (Sub-task 3+)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from v3x_zulfiqar_gideon import EventBus

from v3x_zulfiqar_gideon import EntityDied, DamageDealt

# Fallback deltas used when the JSON config key is missing.
_DEFAULT_EVENT_DELTAS: dict = {
    "enemy_kill": 0.5,
    "boss_defeated": 0.0,   # Boss deltas come from the relic system (Sub-task 2)
}

# Vignette alpha breakpoints: (corruption_value, alpha)
_VIGNETTE_BREAKPOINTS = [(0, 0), (33, 40), (66, 120), (100, 220)]


def _lerp_vignette_alpha(value: float) -> int:
    """Linearly interpolate vignette alpha from the breakpoint table."""
    for i in range(len(_VIGNETTE_BREAKPOINTS) - 1):
        x0, a0 = _VIGNETTE_BREAKPOINTS[i]
        x1, a1 = _VIGNETTE_BREAKPOINTS[i + 1]
        if x0 <= value <= x1:
            t = (value - x0) / (x1 - x0) if x1 != x0 else 0.0
            return int(a0 + t * (a1 - a0))
    return _VIGNETTE_BREAKPOINTS[-1][1]


class CorruptionManager:
    """Tracks the player's corruption level and reacts to game events.

    Args:
        event_bus: Shared ``EventBus`` instance used to subscribe to
            ``EntityDied`` and ``DamageDealt`` events.
        config: The full ``storyline_config.json`` data dict.  The
            ``corruption_events`` key is read for per-event deltas.
    """

    def __init__(self, event_bus: "EventBus", config: dict) -> None:
        self._value: float = 0.0

        # Load per-event deltas from config; fall back to defaults for any
        # missing keys so future JSON additions are automatically picked up.
        cfg_deltas: dict = config.get("corruption_events", {})
        self._event_deltas: dict = {**_DEFAULT_EVENT_DELTAS, **cfg_deltas}

        # Subscribe to engine events via the shared EventBus.
        event_bus.subscribe(EntityDied, self._on_entity_died)
        event_bus.subscribe(DamageDealt, self._on_damage_dealt)

    # ── Value access ──────────────────────────────────────────────────────────

    @property
    def value(self) -> float:
        """Current corruption value (0.0–100.0), read-only."""
        return self._value

    def add(self, amount: float) -> None:
        """Increase corruption, clamped to 100.0."""
        self._value = min(100.0, self._value + amount)

    def reduce(self, amount: float) -> None:
        """Decrease corruption, clamped to 0.0."""
        self._value = max(0.0, self._value - amount)

    # ── Threshold properties ──────────────────────────────────────────────────

    @property
    def is_tainted(self) -> bool:
        return self._value > 33

    @property
    def is_corrupted(self) -> bool:
        return self._value > 66

    @property
    def is_void(self) -> bool:
        return self._value > 90

    @property
    def corruption_level(self) -> str:
        """Human-readable corruption tier string."""
        if self.is_void:
            return "void"
        if self.is_corrupted:
            return "corrupted"
        if self.is_tainted:
            return "tainted"
        return "pure"

    @property
    def vignette_alpha(self) -> int:
        """Screen overlay alpha (0–220) mapped linearly from corruption value."""
        return _lerp_vignette_alpha(self._value)

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def update(self, dt: float) -> None:
        """Per-frame update stub — reserved for future decay mechanics."""
        pass  # Future: apply passive decay or instability pulses here

    def reset(self) -> None:
        """Reset corruption to zero (call at new-game start)."""
        self._value = 0.0

    # ── Event handlers ────────────────────────────────────────────────────────

    def _on_entity_died(self, event: EntityDied) -> None:
        """Add corruption only when a non-player entity is killed."""
        from src.game.entities.player import Player
        if isinstance(event.entity, Player):
            return  # Player death does not add corruption

        if event.is_boss:
            # Boss corruption deltas are applied by the relic system (Sub-task 2).
            # The "boss_defeated" entry in _event_deltas defaults to 0.0 here.
            delta = self._event_deltas.get("boss_defeated", 0.0)
        else:
            delta = self._event_deltas.get("enemy_kill", 0.5)

        if delta != 0.0:
            self.add(delta)

    def _on_damage_dealt(self, event: DamageDealt) -> None:
        """Hook for future use — damage events are too frequent for automatic corruption.

        No corruption is applied here to avoid runaway accumulation from
        multi-hit attacks.  Sub-task 3 (WhispererSystem) may use this hook
        to detect sustained aggression patterns.
        """
        pass  # Intentional no-op — reserved for future use
