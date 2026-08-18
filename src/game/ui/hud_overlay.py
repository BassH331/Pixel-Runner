"""
HUDOverlay — Unified manager for heads-up display overlays, player UI, boss health bars,
notification banners, objective popups, and tutorial prompts.
"""

from __future__ import annotations

from typing import Any, Optional
import pygame as pg

from v3x_zulfiqar_gideon import NotificationBanner
from src.game.ui.player_ui import PlayerUI
from src.game.ui.objective_display import ObjectiveDisplay
from src.game.ui.tutorial_overlay import TutorialOverlay
from src.game.entities.boss_manager import BossManager


class HUDOverlay:
    """Consolidated heads-up display and overlay system."""

    def __init__(self, screen_width: int, screen_height: int) -> None:
        self.screen_width = screen_width
        self.screen_height = screen_height

        self.player_ui = PlayerUI()
        self.objective_display = ObjectiveDisplay()
        self.notification_banner = NotificationBanner(scale=0.6, icon_scale=0.6)
        self.tutorial_overlay = TutorialOverlay()

    def update(self) -> None:
        """Update active UI timers and animations."""
        self.player_ui.update()

    def draw_world_ui(self, target_surface: pg.Surface) -> None:
        """Render player HUD elements drawn directly in world surface."""
        self.player_ui.draw(target_surface)

    def draw_boss_health_bar(self, target_surface: pg.Surface, obstacle_group: pg.sprite.Group) -> None:
        """Render active boss health bar overlay."""
        BossManager.draw_boss_health_bar(target_surface, obstacle_group, self.screen_width)

    def draw_screen_overlays(self, screen_surface: pg.Surface) -> None:
        """Render screen-space overlays (objective display, notification banner, tutorial)."""
        self.objective_display.draw(screen_surface)
        self.notification_banner.draw(screen_surface)
        self.tutorial_overlay.draw(screen_surface)
