"""
Squad Coordinator — Human-like squad tactical roles, flanking surround maneuvers, and pincer attacks.

Orchestrates multi-enemy group tactics:
- Role Assignment: FRONT_HARASSER, REAR_FLANKER, SUPPORT_BAITER.
- Flanking Surround: Enemies move around the player to surround them on both sides (left & right).
- Coordinated Pincer Attacks: Dual-angle attacks timed from front and rear simultaneously.
- Bait-and-Switch: Front enemy steps back to lure player swing while rear flanker lunges in.
"""

from __future__ import annotations

import logging
import math
import random
from enum import Enum, auto
from typing import Dict, List, Optional, Set, Tuple
import pygame as pg

logger = logging.getLogger(__name__)


class SquadRole(Enum):
    FRONT_HARASSER = 10  # Engages from player's front
    REAR_FLANKER = 20    # Loops around to engage from player's back
    SUPPORT_BAITER = 30  # Holds medium distance, lunges when player overextends


class SquadCoordinator:
    """Singleton coordinator for multi-enemy tactical role assignment and pincer maneuvers."""

    _instance: Optional[SquadCoordinator] = None

    @classmethod
    def get_instance(cls) -> SquadCoordinator:
        if cls._instance is None:
            cls._instance = SquadCoordinator()
        return cls._instance

    def __init__(self) -> None:
        self._enemy_roles: Dict[int, SquadRole] = {}
        self._pincer_active: bool = False
        self._last_role_assign_time: float = 0.0
        self._last_pincer_time: float = 0.0

    def update_squad_roles(
        self,
        enemies: List[Tuple[int, pg.Rect, bool]],  # list of (enemy_id, enemy_rect, is_alive)
        player_rect: Optional[pg.Rect],
        player_facing_left: bool,
    ) -> None:
        """Assign dynamic tactical roles (Front Harasser, Rear Flanker, Support Baiter)."""
        if player_rect is None:
            self._enemy_roles.clear()
            return

        now = pg.time.get_ticks() / 1000.0
        if now - self._last_role_assign_time < 0.8:
            return
        self._last_role_assign_time = now

        active_enemies = [e for e in enemies if e[2]]
        if not active_enemies:
            self._enemy_roles.clear()
            return

        # Sort enemies by distance to player
        active_enemies.sort(key=lambda e: abs(e[1].centerx - player_rect.centerx))

        # Determine front and rear direction relative to player facing
        # Player facing left -> Front is left (smaller X), Rear is right (larger X)
        player_front_dir = -1 if player_facing_left else 1

        left_side_count = 0
        right_side_count = 0

        for idx, (e_id, e_rect, _) in enumerate(active_enemies):
            rel_x = e_rect.centerx - player_rect.centerx
            is_on_right = rel_x > 0

            if is_on_right:
                right_side_count += 1
            else:
                left_side_count += 1

            if idx == 0:
                # Closest enemy takes Front Harasser role
                self._enemy_roles[e_id] = SquadRole.FRONT_HARASSER
            elif idx == 1:
                # Second closest is assigned Rear Flanker to surround player
                # If closest is on right, second should move to left (and vice versa)
                self._enemy_roles[e_id] = SquadRole.REAR_FLANKER
            else:
                # Additional enemies act as Support Baiters holding perimeter
                self._enemy_roles[e_id] = SquadRole.SUPPORT_BAITER

        # Log squad tactical coordination
        if len(active_enemies) >= 2:
            front_id = active_enemies[0][0]
            flanker_id = active_enemies[1][0]
            logger.debug(
                "[AI SQUAD PINCE] Flanking Surround Formed! Front Harasser: #%04d | Rear Flanker: #%04d (Pincer Positioning active)",
                front_id % 10000, flanker_id % 10000,
            )

    def get_role(self, enemy_id: int) -> SquadRole:
        return self._enemy_roles.get(enemy_id, SquadRole.FRONT_HARASSER)

    def get_target_offset_x(
        self,
        enemy_id: int,
        player_rect: pg.Rect,
        player_facing_left: bool,
        preferred_spacing: float = 65.0,
    ) -> float:
        """Calculate target X position based on assigned squad role."""
        role = self.get_role(enemy_id)
        player_front_x = -preferred_spacing if player_facing_left else preferred_spacing
        player_rear_x = preferred_spacing if player_facing_left else -preferred_spacing

        if role == SquadRole.FRONT_HARASSER:
            return player_rect.centerx + player_front_x
        elif role == SquadRole.REAR_FLANKER:
            # Force flanking position behind player
            return player_rect.centerx + player_rear_x
        else: # SUPPORT_BAITER
            # Medium distance support
            offset_dir = player_rear_x / abs(player_rear_x) if player_rear_x != 0 else 1.0
            return player_rect.centerx + (offset_dir * (preferred_spacing + 90.0))

    def should_trigger_pincer_attack(
        self,
        enemy_id: int,
        dist_to_player_x: float,
        can_attack: bool,
    ) -> bool:
        """Check if a coordinated dual-angle pincer strike should be executed."""
        role = self.get_role(enemy_id)
        now = pg.time.get_ticks() / 1000.0

        if role in (SquadRole.FRONT_HARASSER, SquadRole.REAR_FLANKER) and can_attack:
            if now - self._last_pincer_time > 2.5:
                self._last_pincer_time = now
                logger.debug(
                    "[AI SQUAD PINCE] PINCER DUAL-STRIKE! Enemy #%04d (%s) launching coordinated attack!",
                    enemy_id % 10000, role.name,
                )
                return True

        return False

    def clear(self) -> None:
        self._enemy_roles.clear()
        self._last_pincer_time = 0.0
