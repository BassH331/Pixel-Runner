"""
SideNotification — Non-blocking, right-side pop-up notification tab.

Renders achievement, objective, and milestone notifications smoothly on the
right side of the screen while gameplay continues uninterrupted.
Scales dynamically across different screen resolutions and aspect ratios.
"""

from __future__ import annotations

import math
import os
from enum import Enum, auto
from typing import Optional, List, Tuple, Any, Union
import pygame as pg

from v3x_zulfiqar_gideon import AssetManager


class NotificationState(Enum):
    IDLE = auto()
    SLIDE_IN = auto()
    HOLD = auto()
    SLIDE_OUT = auto()


class _NotificationItem:
    def __init__(
        self,
        text: str,
        title: str,
        icon: Optional[Union[str, pg.Surface]] = None,
        hold: float = 4.5,
    ) -> None:
        self.text = text
        self.title = title
        self.icon = icon
        self.hold = hold


class SideNotification:
    """
    Non-blocking pop-up notification tab rendered on the right side of the screen.

    Automatically handles:
    - Dynamic resolution scaling (720p, 1080p, 1440p, 4K, laptops, ultrawide).
    - Consistent font typography matching in-game NPC dialogues and HUD.
    - Framed icon display with glowing borders.
    - Smooth ease-out slide-in, hold, and slide-out transitions.
    - Multi-notification queuing without blocking gameplay.
    """

    DEFAULT_ICON_PATHS = [
        "assets/free-undead-loot-pixel-art-icons/PNG/Transperent/Icon1.png",
        "assets/free-undead-loot-pixel-art-icons (2)/PNG/Transperent/Icon1.png",
        "assets/graphics/UI/PNG/Exclamation_Yellow.png",
        "assets/graphics/ui/relic_icon.png",
    ]

    TITLE_FONT_PATH = "assets/font/Abaddon Bold.ttf"
    BODY_FONT_PATH = "assets/graphics/Darinia/Darinia.ttf"

    def __init__(
        self,
        screen_width: int = 1280,
        screen_height: int = 720,
        slide_in_time: float = 0.35,
        slide_out_time: float = 0.35,
        default_hold_time: float = 4.5,
    ) -> None:
        self._screen_width = max(100, screen_width)
        self._screen_height = max(100, screen_height)
        self._slide_in_time = slide_in_time
        self._slide_out_time = slide_out_time
        self._default_hold_time = default_hold_time

        self._state: NotificationState = NotificationState.IDLE
        self._timer: float = 0.0
        self._current_item: Optional[_NotificationItem] = None
        self._queue: List[_NotificationItem] = []

        # Cached layout & rendering surfaces
        self._scale: float = 1.0
        self._current_tab_surface: Optional[pg.Surface] = None
        self._cached_icon: Optional[pg.Surface] = None
        self._tab_width: int = 390
        self._tab_height: int = 90
        self._top_y: int = 110
        self._target_x: int = self._screen_width - self._tab_width - 24
        self._current_x: float = float(self._screen_width)

        self._compute_scaling(self._screen_width, self._screen_height)

    @property
    def is_active(self) -> bool:
        """Returns True if a notification is currently animating or displayed."""
        return self._state != NotificationState.IDLE

    def _compute_scaling(self, screen_width: int, screen_height: int) -> None:
        """Calculate resolution scaling factor based on virtual 1280x720 baseline."""
        self._screen_width = max(100, screen_width)
        self._screen_height = max(100, screen_height)

        # Scale uniformly preserving legibility across small and 4K screens
        raw_scale = min(self._screen_width / 1280.0, self._screen_height / 720.0)
        self._scale = max(0.65, min(2.5, raw_scale))

        self._tab_width = int(390 * self._scale)
        # Position tab cleanly below top-right HUD (Time & Dist counters)
        self._top_y = max(int(105 * self._scale), int(self._screen_height * 0.15))
        self._target_x = self._screen_width - self._tab_width - int(20 * self._scale)

    def show(
        self,
        text: str,
        title: str = "Milestone",
        icon: Optional[Union[str, pg.Surface]] = None,
        hold: Optional[float] = None,
    ) -> None:
        """
        Trigger a non-blocking side notification.
        If a notification is already visible, the new one is queued.
        """
        item = _NotificationItem(
            text=text.strip(),
            title=title.strip(),
            icon=icon,
            hold=hold if hold is not None else self._default_hold_time,
        )

        if self._state == NotificationState.IDLE:
            self._start_item(item)
        else:
            self._queue.append(item)

    def _start_item(self, item: _NotificationItem) -> None:
        """Initiate the slide-in animation for a notification item."""
        self._current_item = item
        self._timer = 0.0
        self._state = NotificationState.SLIDE_IN
        self._current_x = float(self._screen_width + 10)
        self._build_tab_surface(item)

    def _load_icon_surface(self, icon_spec: Optional[Union[str, pg.Surface]], target_size: int) -> pg.Surface:
        """Load and scale an icon safely."""
        if isinstance(icon_spec, pg.Surface):
            return pg.transform.smoothscale(icon_spec, (target_size, target_size))

        chosen_path = icon_spec
        if not chosen_path or not os.path.exists(str(chosen_path)):
            # Search fallback default icon paths
            chosen_path = None
            for p in self.DEFAULT_ICON_PATHS:
                if os.path.exists(p):
                    chosen_path = p
                    break

        if chosen_path and os.path.exists(chosen_path):
            try:
                raw_img = AssetManager.get_texture(chosen_path)
                return pg.transform.smoothscale(raw_img, (target_size, target_size))
            except Exception:
                pass

        # Procedural fallback icon (stylized diamond/star)
        surf = pg.Surface((target_size, target_size), pg.SRCALPHA)
        cx, cy = target_size // 2, target_size // 2
        r = target_size // 2 - 2
        pts = [(cx, cy - r), (cx + r, cy), (cx, cy + r), (cx - r, cy)]
        pg.draw.polygon(surf, (255, 215, 80), pts)
        pg.draw.polygon(surf, (255, 255, 255), pts, width=max(1, int(2 * self._scale)))
        return surf

    def _wrap_text(self, text: str, font: pg.font.Font, max_w: int) -> List[str]:
        """Wrap body text across multiple lines to prevent card overflow."""
        words = text.split()
        lines: List[str] = []
        curr_line = ""

        for word in words:
            test = f"{curr_line} {word}".strip() if curr_line else word
            if font.size(test)[0] <= max_w:
                curr_line = test
            else:
                if curr_line:
                    lines.append(curr_line)
                curr_line = word
        if curr_line:
            lines.append(curr_line)
        return lines

    def _build_tab_surface(self, item: _NotificationItem) -> None:
        """Pre-render the complete notification card with dynamic height."""
        # 1. Fonts with resolution-matched sizing
        title_font_size = max(13, int(22 * self._scale))
        body_font_size = max(11, int(15 * self._scale))

        title_font = AssetManager.get_font(self.TITLE_FONT_PATH, title_font_size)
        body_font = AssetManager.get_font(self.BODY_FONT_PATH, body_font_size)

        # Fallback to system font if custom fonts fail
        if not title_font:
            title_font = pg.font.SysFont("Arial", title_font_size, bold=True)
        if not body_font:
            body_font = pg.font.SysFont("Arial", body_font_size)

        # 2. Icon badge dimensions
        badge_size = max(36, int(50 * self._scale))
        icon_size = max(26, int(36 * self._scale))
        self._cached_icon = self._load_icon_surface(item.icon, icon_size)

        # 3. Text layout & wrap calculations
        padding_x = int(14 * self._scale)
        padding_y = int(12 * self._scale)
        spacing = int(4 * self._scale)

        content_x = padding_x + badge_size + int(12 * self._scale)
        available_text_w = self._tab_width - content_x - padding_x

        title_surf = title_font.render(item.title, True, (255, 215, 80))
        lines = self._wrap_text(item.text, body_font, available_text_w)

        line_h = body_font.get_linesize()
        total_text_h = title_surf.get_height() + spacing + len(lines) * line_h

        # Dynamic card height matching text length
        needed_h = max(int(82 * self._scale), total_text_h + padding_y * 2)
        needed_h = max(needed_h, badge_size + padding_y * 2)
        self._tab_height = needed_h

        # 4. Construct composite tab surface
        tab_surf = pg.Surface((self._tab_width, self._tab_height), pg.SRCALPHA)

        # Dark fantasy obsidian/slate background
        corner_rad = max(4, int(10 * self._scale))
        bg_rect = pg.Rect(0, 0, self._tab_width, self._tab_height)
        pg.draw.rect(tab_surf, (16, 12, 24, 235), bg_rect, border_radius=corner_rad)

        # Subtle gradient inner fill
        inner_rect = bg_rect.inflate(-int(4 * self._scale), -int(4 * self._scale))
        pg.draw.rect(tab_surf, (28, 22, 38, 225), inner_rect, border_radius=max(2, corner_rad - 2))

        # Antique Gold Outer Border
        border_w = max(1, int(2 * self._scale))
        pg.draw.rect(tab_surf, (218, 165, 32, 230), bg_rect, width=border_w, border_radius=corner_rad)

        # Decorative left golden accent notch
        accent_w = max(3, int(5 * self._scale))
        pg.draw.rect(
            tab_surf,
            (255, 215, 80, 240),
            (border_w, border_w + int(4 * self._scale), accent_w, self._tab_height - (border_w + int(4 * self._scale)) * 2),
            border_radius=max(1, corner_rad // 2),
        )

        # 5. Render framed icon badge on left
        badge_y = (self._tab_height - badge_size) // 2
        badge_rect = pg.Rect(padding_x, badge_y, badge_size, badge_size)
        badge_radius = max(4, int(8 * self._scale))
        pg.draw.rect(tab_surf, (10, 8, 16, 240), badge_rect, border_radius=badge_radius)
        pg.draw.rect(tab_surf, (200, 150, 40, 220), badge_rect, width=max(1, int(1.5 * self._scale)), border_radius=badge_radius)

        if self._cached_icon:
            ix = badge_rect.centerx - self._cached_icon.get_width() // 2
            iy = badge_rect.centery - self._cached_icon.get_height() // 2
            tab_surf.blit(self._cached_icon, (ix, iy))

        # 6. Render Title (with drop shadow)
        ty = padding_y
        shd_offset = max(1, int(1.5 * self._scale))
        title_shd = title_font.render(item.title, True, (0, 0, 0))
        tab_surf.blit(title_shd, (content_x + shd_offset, ty + shd_offset))
        tab_surf.blit(title_surf, (content_x, ty))

        # 7. Render Body Text lines (with subtle drop shadow)
        by = ty + title_surf.get_height() + spacing
        for line in lines:
            line_shd = body_font.render(line, True, (10, 10, 15))
            line_surf = body_font.render(line, True, (235, 230, 220))
            tab_surf.blit(line_shd, (content_x + 1, by + 1))
            tab_surf.blit(line_surf, (content_x, by))
            by += line_h

        self._current_tab_surface = tab_surf

    def update(self, dt: float) -> None:
        """
        Advance state timers and animation positions.
        dt is in seconds (or milliseconds if dt > 1.0).
        """
        if self._state == NotificationState.IDLE:
            if self._queue:
                next_item = self._queue.pop(0)
                self._start_item(next_item)
            return

        dt_sec = dt if dt < 1.0 else dt / 1000.0
        self._timer += dt_sec

        if self._state == NotificationState.SLIDE_IN:
            prog = min(1.0, self._timer / self._slide_in_time)
            # Smooth ease-out cubic
            ease = 1.0 - math.pow(1.0 - prog, 3)
            start_x = float(self._screen_width + 10)
            self._current_x = start_x + (self._target_x - start_x) * ease

            if prog >= 1.0:
                self._current_x = float(self._target_x)
                self._state = NotificationState.HOLD
                self._timer = 0.0

        elif self._state == NotificationState.HOLD:
            self._current_x = float(self._target_x)
            hold_time = self._current_item.hold if self._current_item else self._default_hold_time
            if self._timer >= hold_time:
                self._state = NotificationState.SLIDE_OUT
                self._timer = 0.0

        elif self._state == NotificationState.SLIDE_OUT:
            prog = min(1.0, self._timer / self._slide_out_time)
            # Smooth ease-in cubic
            ease = math.pow(prog, 3)
            end_x = float(self._screen_width + 10)
            self._current_x = float(self._target_x) + (end_x - float(self._target_x)) * ease

            if prog >= 1.0:
                self._state = NotificationState.IDLE
                self._current_item = None
                self._current_tab_surface = None
                if self._queue:
                    next_item = self._queue.pop(0)
                    self._start_item(next_item)

    def draw(self, surface: pg.Surface) -> None:
        """Render notification tab onto the display surface."""
        if self._state == NotificationState.IDLE or not self._current_tab_surface:
            return

        # Dynamically detect resolution/window changes
        sw, sh = surface.get_size()
        if sw != self._screen_width or sh != self._screen_height:
            self._compute_scaling(sw, sh)
            if self._current_item:
                self._build_tab_surface(self._current_item)

        # Alpha calculation for smooth fade on slide-out
        alpha = 255
        if self._state == NotificationState.SLIDE_OUT:
            fade_prog = min(1.0, self._timer / self._slide_out_time)
            alpha = max(0, int(255 * (1.0 - fade_prog)))

        draw_surf = self._current_tab_surface
        if alpha < 255:
            draw_surf = self._current_tab_surface.copy()
            draw_surf.set_alpha(alpha)

        # Floating breath shimmer during hold
        draw_y = self._top_y
        if self._state == NotificationState.HOLD:
            breath = int(math.sin(self._timer * 3.5) * (2 * self._scale))
            draw_y += breath

        surface.blit(draw_surf, (int(self._current_x), draw_y))
