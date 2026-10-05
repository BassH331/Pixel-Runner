"""
Custom game events for the Pixel-Runner narrative system.

These dataclasses are emitted via EventBus and consumed by systems such as
RelicManager, WhispererSystem, and EndingManager.
"""

from dataclasses import dataclass
from enum import Enum, auto


class Speaker(Enum):
    """Identifies the whisperer voice shown via CinematicNarrativeOverlay."""
    ANDRAS = auto()
    MOON_KNIGHT = auto()



@dataclass(slots=True)
class RelicDropped:
    """Emitted when a boss dies and drops a relic."""
    relic_id: str
    corruption_delta: float
    boss_name: str


@dataclass(slots=True)
class FinalBossDefeated:
    """Emitted when the last boss in the sequence dies."""
    corruption_value: float
    relics_collected: list  # list of relic_id strings
    boss_name: str
