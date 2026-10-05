"""
HUDOverlay — Unified manager for heads-up display overlays, player UI, boss health bars,
notification banners, objective popups, and tutorial prompts.
"""

from __future__ import annotations

from typing import Any, Optional, TYPE_CHECKING
import pygame as pg

from v3x_zulfiqar_gideon import NotificationBanner
from src.game.ui.player_ui import PlayerUI
from src.game.ui.objective_display import ObjectiveDisplay
from src.game.ui.tutorial_overlay import TutorialOverlay
from src.game.ui.side_notification import SideNotification
from src.game.entities.boss_manager import BossManager

if TYPE_CHECKING:
    from src.game.systems.corruption_manager import CorruptionManager
    from src.game.systems.relic_manager import RelicManager

# Relic strip layout constants.
_RELIC_SLOT_SIZE = 16
_RELIC_SLOT_GAP = 4
_RELIC_SLOT_COUNT = 6
_RELIC_STRIP_MARGIN = 8   # distance from right / top screen edge
_RELIC_COLLECTED_COLOUR = (180, 80, 200)
_RELIC_EMPTY_COLOUR = (40, 40, 50)
_RELIC_BORDER_COLOUR = (70, 60, 80)


class HUDOverlay:
    """Consolidated heads-up display and overlay system."""

    def __init__(self, screen_width: int, screen_height: int,
                 corruption_manager: Optional["CorruptionManager"] = None,
                 relic_manager: Optional["RelicManager"] = None) -> None:
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.corruption_manager: Optional["CorruptionManager"] = corruption_manager
        self.relic_manager: Optional["RelicManager"] = relic_manager

        self.player_ui = PlayerUI()
        self.player_ui.corruption_manager = corruption_manager
        self.objective_display = ObjectiveDisplay()
        self.notification_banner = NotificationBanner(scale=1.0, banner_width_frac=0.55, icon_scale=0.7, hold=3.0)
        self.side_notification = SideNotification(self.screen_width, self.screen_height)
        self.tutorial_overlay = TutorialOverlay()

    def update(self, dt: float = 0.0) -> None:
        """Update active UI timers and animations."""
        self.player_ui.update()
        self.side_notification.update(dt)

    def draw_world_ui(self, target_surface: pg.Surface) -> None:
        """Render player HUD elements drawn directly in world surface."""
        self.player_ui.draw(target_surface)

    def draw_boss_health_bar(self, target_surface: pg.Surface, obstacle_group: pg.sprite.Group) -> None:
        """Render active boss health bar overlay."""
        BossManager.draw_boss_health_bar(target_surface, obstacle_group, self.screen_width)

    def draw_relic_strip(self, screen_surface: pg.Surface) -> None:
        """Render 6 relic collection slots in the top-right corner of the HUD."""
        collected = (
            set(self.relic_manager.collected_ids())
            if self.relic_manager is not None
            else set()
        )

        strip_w = _RELIC_SLOT_COUNT * (_RELIC_SLOT_SIZE + _RELIC_SLOT_GAP) - _RELIC_SLOT_GAP
        start_x = self.screen_width - _RELIC_STRIP_MARGIN - strip_w
        start_y = _RELIC_STRIP_MARGIN

        # Canonical order matches the boss-drop sequence from the plan.
        _ORDERED_RELIC_IDS = [
            "shattered_gauntlet",
            "tainted_sigil",
            "vial_of_void_blood",
            "hollowed_ledger_page",
            "candoras_tear",
            "amalgam_core",
        ]

        for i in range(_RELIC_SLOT_COUNT):
            slot_x = start_x + i * (_RELIC_SLOT_SIZE + _RELIC_SLOT_GAP)
            slot_rect = pg.Rect(slot_x, start_y, _RELIC_SLOT_SIZE, _RELIC_SLOT_SIZE)
            relic_id = _ORDERED_RELIC_IDS[i] if i < len(_ORDERED_RELIC_IDS) else ""
            is_collected = relic_id in collected
            fill_colour = _RELIC_COLLECTED_COLOUR if is_collected else _RELIC_EMPTY_COLOUR
            pg.draw.rect(screen_surface, fill_colour, slot_rect, border_radius=3)
            pg.draw.rect(screen_surface, _RELIC_BORDER_COLOUR, slot_rect, width=1, border_radius=3)

    def draw_screen_overlays(self, screen_surface: pg.Surface) -> None:
        """Render screen-space overlays (objective display, notification banner, tutorial, side notification)."""
        self.objective_display.draw(screen_surface)
        self.notification_banner.draw(screen_surface)
        self.tutorial_overlay.draw(screen_surface)
        self.side_notification.draw(screen_surface)

        # Relic icon strip — drawn before the vignette so it's visible through the darkness
        self.draw_relic_strip(screen_surface)

        # Corruption vignette — drawn last so it composites over all other HUD elements
        if self.corruption_manager is not None and self.corruption_manager.value > 0:
            self.player_ui.render_corruption_vignette(
                screen_surface,
                self.corruption_manager.value / 100.0,
            )
