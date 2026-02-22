"""
Objective trigger system for controlling when objectives appear.

Supports three trigger types:
- time: fires after N seconds in the game state
- flag: fires when a named game event occurs (e.g., "first_kill")
- proximity: handled externally by InteractionPoint entities
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ObjectiveTrigger:
    """A single objective trigger configuration."""

    text: str
    title: str = "Objective"
    trigger_type: str = "time"  # "time" | "flag"
    delay_seconds: float = 0.0  # for time-based triggers
    flag_name: str = ""  # for flag-based triggers
    triggered: bool = False
    enabled: bool = True


class ObjectiveTriggerManager:
    """Manages a queue of objective triggers and checks firing conditions.

    Usage:
        manager = ObjectiveTriggerManager()
        manager.add_trigger(
            text="Use Q, E, W for attacks!",
            title="Combat Tip",
            trigger_type="time",
            delay_seconds=10.0,
        )
        manager.add_trigger(
            text="Well done!",
            title="Progress",
            trigger_type="flag",
            flag_name="first_kill",
        )

        # In game loop:
        manager.update(elapsed_seconds)
        trigger = manager.get_pending()
        if trigger:
            objective_display.show(trigger.text, trigger.title)
    """

    def __init__(self) -> None:
        self._triggers: list[ObjectiveTrigger] = []
        self._flags: set[str] = set()
        self._pending: Optional[ObjectiveTrigger] = None

    def add_trigger(
        self,
        text: str,
        title: str = "Objective",
        trigger_type: str = "time",
        delay_seconds: float = 0.0,
        flag_name: str = "",
        enabled: bool = True,
    ) -> None:
        """Register a new objective trigger."""
        self._triggers.append(
            ObjectiveTrigger(
                text=text,
                title=title,
                trigger_type=trigger_type,
                delay_seconds=delay_seconds,
                flag_name=flag_name,
                enabled=enabled,
            )
        )

    def set_flag(self, name: str) -> None:
        """Mark a game event flag as completed.

        Args:
            name: Flag identifier (e.g., "first_kill", "reached_bridge").
        """
        self._flags.add(name)

    def has_flag(self, name: str) -> bool:
        """Check if a flag has been set."""
        return name in self._flags

    def update(self, elapsed_seconds: float) -> None:
        """Check all triggers and queue the first one that should fire.

        Only one trigger fires per update cycle. Triggers are checked
        in registration order (first registered = first priority).

        Args:
            elapsed_seconds: Seconds elapsed since the game state started.
        """
        if self._pending is not None:
            return  # Already have a pending trigger waiting to be consumed

        for trigger in self._triggers:
            if trigger.triggered or not trigger.enabled:
                continue

            fired = False

            if trigger.trigger_type == "time":
                if elapsed_seconds >= trigger.delay_seconds:
                    fired = True

            elif trigger.trigger_type == "flag":
                if trigger.flag_name in self._flags:
                    fired = True

            if fired:
                trigger.triggered = True
                self._pending = trigger
                return  # Only fire one per update

    def get_pending(self) -> Optional[ObjectiveTrigger]:
        """Consume and return the next pending trigger, if any.

        Returns:
            The trigger that fired, or None.
        """
        trigger = self._pending
        self._pending = None
        return trigger

    def reset(self) -> None:
        """Reset all triggers to un-triggered state."""
        self._flags.clear()
        self._pending = None
        for trigger in self._triggers:
            trigger.triggered = False
