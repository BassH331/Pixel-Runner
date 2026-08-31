"""
Squad Combat Token Manager — Token bucket system for tactical squad coordination.

Prevents enemy clumping by granting attack tokens to only a limited number of
enemies simultaneously (e.g. max 2 active attackers). Non-token holders hold
defensive spacing, encircle the player, or backstep to maintain a combat perimeter.
"""

from __future__ import annotations

import logging
import os
import time
from typing import Dict, Set, Optional

logger = logging.getLogger(__name__)


class SquadTokenManager:
    """Central manager for distributing combat attack tokens across active enemies."""

    _instance: Optional[SquadTokenManager] = None

    @classmethod
    def get_instance(cls) -> SquadTokenManager:
        if cls._instance is None:
            cls._instance = SquadTokenManager()
        return cls._instance

    def __init__(self, max_simultaneous_attackers: int = 2) -> None:
        diff = os.environ.get("AI_DIFFICULTY", "").upper()
        if diff == "NIGHTMARE":
            max_simultaneous_attackers = 4
        elif diff == "HARD":
            max_simultaneous_attackers = 3
        elif diff == "EASY":
            max_simultaneous_attackers = 1

        self.max_simultaneous_attackers: int = max_simultaneous_attackers
        self._active_tokens: Set[int] = set()
        self._registered_enemies: Dict[int, str] = {}  # id -> tier/type

    def register_enemy(self, enemy_id: int, tier: str = "minion") -> None:
        self._registered_enemies[enemy_id] = tier

    def unregister_enemy(self, enemy_id: int) -> None:
        self._registered_enemies.pop(enemy_id, None)
        self._active_tokens.discard(enemy_id)

    def request_attack_token(self, enemy_id: int) -> bool:
        """Request permission to initiate a melee/spell attack."""
        if enemy_id in self._active_tokens:
            return True

        tier = self._registered_enemies.get(enemy_id, "minion")
        if tier == "boss":
            self._active_tokens.add(enemy_id)
            return True

        # Count non-boss attackers active
        minion_tokens_active = sum(
            1 for e_id in self._active_tokens
            if self._registered_enemies.get(e_id, "minion") != "boss"
        )

        if minion_tokens_active < self.max_simultaneous_attackers:
            self._active_tokens.add(enemy_id)
            logger.debug(
                "[AI SQUAD TOKEN] Attack Permit GRANTED to Enemy #%04d (%s) -> Active Attackers: %d/%d",
                enemy_id % 10000, tier, minion_tokens_active + 1, self.max_simultaneous_attackers,
            )
            return True

        # Throttle denied log to avoid per-frame spam
        if not hasattr(self, "_last_denied_log"):
            self._last_denied_log = {}
        now = time.time()
        if now - self._last_denied_log.get(enemy_id, 0.0) > 2.0:
            self._last_denied_log[enemy_id] = now
            logger.debug(
                "[AI SQUAD TOKEN] DENIED to Enemy #%04d (%s) -> Max attackers (%d/%d) active! Holding perimeter spacing.",
                enemy_id % 10000, tier, self.max_simultaneous_attackers, self.max_simultaneous_attackers,
            )

        return False

    def release_attack_token(self, enemy_id: int) -> None:
        """Release an attack token when an attack animation or state ends."""
        if enemy_id in self._active_tokens:
            self._active_tokens.discard(enemy_id)
            tier = self._registered_enemies.get(enemy_id, "minion")
            if tier != "boss":
                logger.debug(
                    "[AI SQUAD TOKEN] Attack Permit RELEASED by Enemy #%04d",
                    enemy_id % 10000,
                )

    def clear(self) -> None:
        self._active_tokens.clear()
        self._registered_enemies.clear()
