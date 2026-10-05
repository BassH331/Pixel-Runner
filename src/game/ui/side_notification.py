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
from src.game.systems.notification_config_manager import NotificationConfigManager


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
        hold: float = 8.5,
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
    - Data-driven configuration from game_data/notification_config.json with live hot-reloading.
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
        slide_in_time: Optional[float] = None,
        slide_out_time: Optional[float] = None,
        default_hold_time: Optional[float] = None,
        config_manager: Optional[NotificationConfigManager] = None,
    ) -> None:
        self._screen_width = max(100, screen_width)
        self._screen_height = max(100, screen_height)

        self._explicit_slide_in = slide_in_time is not None
        self._explicit_slide_out = slide_out_time is not None
        self._explicit_hold = default_hold_time is not None

        self._slide_in_time = slide_in_time if slide_in_time is not None else 0.35
        self._slide_out_time = slide_out_time if slide_out_time is not None else 0.35
        self._default_hold_time = default_hold_time if default_hold_time is not None else 8.5

        self._config_mgr = config_manager or NotificationConfigManager.get_instance()

        self._state: NotificationState = NotificationState.IDLE
        self._timer: float = 0.0
        self._current_item: Optional[_NotificationItem] = None
        self._queue: List[_NotificationItem] = []

        # Cached layout & rendering surfaces
        self._scale: float = 1.0
        self._current_tab_surface: Optional[pg.Surface] = None
        self._cached_icon: Optional[pg.Surface] = None

        # Load all parameters from config manager
        self._apply_config(force_rebuild=False)
        self._last_config_revision = self._config_mgr.revision if self._config_mgr else -1
        self._current_x: float = float(self._screen_width)

    @property
    def is_active(self) -> bool:
        """Returns True if a notification is currently animating or displayed."""
        return self._state != NotificationState.IDLE

    def _apply_config(self, force_rebuild: bool = False) -> None:
        """Read and apply styling and timing parameters from config manager."""
        cfg = self._config_mgr.data if self._config_mgr else {}
        timing = cfg.get("timing", {})
        layout = cfg.get("layout", {})
        colors = cfg.get("colors", {})
        typography = cfg.get("typography", {})

        if not self._explicit_slide_in:
            self._slide_in_time = float(timing.get("slide_in_time", 0.35))
        if not self._explicit_slide_out:
            self._slide_out_time = float(timing.get("slide_out_time", 0.35))
        if not self._explicit_hold:
            self._default_hold_time = float(timing.get("default_hold_time", 8.5))

        self._words_per_sec = float(timing.get("words_per_sec", 0.35))
        self._base_hold_pad = float(timing.get("base_hold_pad", 2.5))
        self._breath_shimmer_enabled = bool(timing.get("breath_shimmer_enabled", True))
        self._breath_amplitude = float(timing.get("breath_amplitude", 2.0))
        self._breath_speed = float(timing.get("breath_speed", 3.5))
        self._fade_on_slide_out = bool(timing.get("fade_on_slide_out", True))

        # Layout baseline params (designed for 1280x720 baseline)
        self._base_tab_width = int(layout.get("tab_width", 390))
        self._base_min_height = int(layout.get("min_height", 82))
        self._base_margin_x = int(layout.get("margin_x", 20))
        self._base_top_y = int(layout.get("top_y", 105))
        self._base_padding_x = int(layout.get("padding_x", 14))
        self._base_padding_y = int(layout.get("padding_y", 12))
        self._base_corner_radius = int(layout.get("corner_radius", 10))
        self._base_border_width = int(layout.get("border_width", 2))
        self._base_accent_notch_width = int(layout.get("accent_notch_width", 5))
        self._accent_notch_enabled = bool(layout.get("accent_notch_enabled", True))
        self._base_spacing = int(layout.get("spacing", 4))
        self._base_badge_size = int(layout.get("badge_size", 50))
        self._base_icon_size = int(layout.get("icon_size", 36))

        # Colors
        self._bg_color = tuple(colors.get("bg_color", [16, 12, 24, 235]))
        self._inner_color = tuple(colors.get("inner_color", [28, 22, 38, 225]))
        self._border_color = tuple(colors.get("border_color", [218, 165, 32, 230]))
        self._accent_notch_color = tuple(colors.get("accent_notch_color", [255, 215, 80, 240]))
        self._badge_bg_color = tuple(colors.get("badge_bg_color", [10, 8, 16, 240]))
        self._badge_border_color = tuple(colors.get("badge_border_color", [200, 150, 40, 220]))
        self._title_color = tuple(colors.get("title_color", [255, 215, 80]))
        self._title_shadow_color = tuple(colors.get("title_shadow_color", [0, 0, 0]))
        self._body_color = tuple(colors.get("body_color", [235, 230, 220]))
        self._body_shadow_color = tuple(colors.get("body_shadow_color", [10, 8, 14]))

        # Typography
        self._title_font_path = typography.get("title_font_path", self.TITLE_FONT_PATH)
        self._title_font_size = int(typography.get("title_font_size", 22))
        self._title_drop_shadow = bool(typography.get("title_drop_shadow", True))
        self._body_font_path = typography.get("body_font_path", self.BODY_FONT_PATH)
        self._body_font_size = int(typography.get("body_font_size", 15))
        self._body_drop_shadow = bool(typography.get("body_drop_shadow", True))
        self._line_spacing_mult = float(typography.get("line_spacing", 1.0))

        self._compute_scaling(self._screen_width, self._screen_height)
        if force_rebuild and self._current_item:
            self._build_tab_surface(self._current_item)

    def _compute_scaling(self, screen_width: int, screen_height: int) -> None:
        """Calculate resolution scaling factor based on virtual 1280x720 baseline."""
        self._screen_width = max(100, screen_width)
        self._screen_height = max(100, screen_height)

        # Scale uniformly preserving legibility across small and 4K screens
        raw_scale = min(self._screen_width / 1280.0, self._screen_height / 720.0)
        self._scale = max(0.65, min(2.5, raw_scale))

        self._tab_width = int(self._base_tab_width * self._scale)
        # Position tab cleanly below top-right HUD (Time & Dist counters)
        self._top_y = max(int(self._base_top_y * self._scale), int(self._screen_height * 0.12))
        self._target_x = self._screen_width - self._tab_width - int(self._base_margin_x * self._scale)

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
        cleaned_text = text.strip()
        if hold is not None:
            effective_hold = hold
        elif self._explicit_hold and self._default_hold_time <= 2.0:
            effective_hold = self._default_hold_time
        else:
            word_count = len(cleaned_text.split())
            effective_hold = max(self._default_hold_time, word_count * self._words_per_sec + self._base_hold_pad)

        item = _NotificationItem(
            text=cleaned_text,
            title=title.strip(),
            icon=icon,
            hold=effective_hold,
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
        title_font_size = max(12, int(self._title_font_size * self._scale))
        body_font_size = max(10, int(self._body_font_size * self._scale))

        title_font = AssetManager.get_font(self._title_font_path, title_font_size)
        body_font = AssetManager.get_font(self._body_font_path, body_font_size)

        # Fallback to system font if custom fonts fail
        if not title_font:
            title_font = pg.font.SysFont("Arial", title_font_size, bold=True)
        if not body_font:
            body_font = pg.font.SysFont("Arial", body_font_size)

        # 2. Icon badge dimensions
        badge_size = max(24, int(self._base_badge_size * self._scale))
        icon_size = max(16, int(self._base_icon_size * self._scale))
        self._cached_icon = self._load_icon_surface(item.icon, icon_size)

        # 3. Text layout & wrap calculations
        padding_x = int(self._base_padding_x * self._scale)
        padding_y = int(self._base_padding_y * self._scale)
        spacing = int(self._base_spacing * self._scale)

        content_x = padding_x + badge_size + int(10 * self._scale)
        available_text_w = self._tab_width - content_x - padding_x

        title_surf = title_font.render(item.title, True, self._title_color)
        lines = self._wrap_text(item.text, body_font, available_text_w)

        line_h = int(body_font.get_linesize() * self._line_spacing_mult)
        total_text_h = title_surf.get_height() + spacing + len(lines) * line_h

        # Dynamic card height matching text length
        min_h = int(self._base_min_height * self._scale)
        needed_h = max(min_h, total_text_h + padding_y * 2)
        needed_h = max(needed_h, badge_size + padding_y * 2)
        self._tab_height = needed_h

        # 4. Construct composite tab surface
        tab_surf = pg.Surface((self._tab_width, self._tab_height), pg.SRCALPHA)

        # Dark fantasy obsidian/slate background
        corner_rad = max(0, int(self._base_corner_radius * self._scale))
        bg_rect = pg.Rect(0, 0, self._tab_width, self._tab_height)
        pg.draw.rect(tab_surf, self._bg_color, bg_rect, border_radius=corner_rad)

        # Subtle gradient inner fill
        inner_pad = max(1, int(3 * self._scale))
        inner_rect = bg_rect.inflate(-inner_pad * 2, -inner_pad * 2)
        if inner_rect.width > 0 and inner_rect.height > 0:
            pg.draw.rect(tab_surf, self._inner_color, inner_rect, border_radius=max(0, corner_rad - 2))

        # Antique Gold Outer Border
        border_w = max(0, int(self._base_border_width * self._scale))
        if border_w > 0:
            pg.draw.rect(tab_surf, self._border_color, bg_rect, width=border_w, border_radius=corner_rad)

        # Decorative left golden accent notch
        if self._accent_notch_enabled and self._base_accent_notch_width > 0:
            accent_w = max(2, int(self._base_accent_notch_width * self._scale))
            top_pad = border_w + int(4 * self._scale)
            accent_h = self._tab_height - top_pad * 2
            if accent_h > 0:
                pg.draw.rect(
                    tab_surf,
                    self._accent_notch_color,
                    (border_w, top_pad, accent_w, accent_h),
                    border_radius=max(0, corner_rad // 2),
                )

        # 5. Render framed icon badge on left
        badge_y = (self._tab_height - badge_size) // 2
        badge_rect = pg.Rect(padding_x, badge_y, badge_size, badge_size)
        badge_radius = max(0, int(corner_rad * 0.7))
        pg.draw.rect(tab_surf, self._badge_bg_color, badge_rect, border_radius=badge_radius)
        badge_border_w = max(1, int(1.5 * self._scale))
        pg.draw.rect(tab_surf, self._badge_border_color, badge_rect, width=badge_border_w, border_radius=badge_radius)

        if self._cached_icon:
            ix = badge_rect.centerx - self._cached_icon.get_width() // 2
            iy = badge_rect.centery - self._cached_icon.get_height() // 2
            tab_surf.blit(self._cached_icon, (ix, iy))

        # 6. Render Title (with optional drop shadow)
        ty = padding_y
        if self._title_drop_shadow:
            shd_offset = max(1, int(1.5 * self._scale))
            title_shd = title_font.render(item.title, True, self._title_shadow_color)
            tab_surf.blit(title_shd, (content_x + shd_offset, ty + shd_offset))
        tab_surf.blit(title_surf, (content_x, ty))

        # 7. Render Body Text lines (with optional drop shadow)
        by = ty + title_surf.get_height() + spacing
        for line in lines:
            if self._body_drop_shadow:
                line_shd = body_font.render(line, True, self._body_shadow_color)
                tab_surf.blit(line_shd, (content_x + 1, by + 1))
            line_surf = body_font.render(line, True, self._body_color)
            tab_surf.blit(line_surf, (content_x, by))
            by += line_h

        self._current_tab_surface = tab_surf

    def update(self, dt: float) -> None:
        """
        Advance state timers and animation positions.
        dt is in seconds (or milliseconds if dt > 1.0).
        """
        # Hot-reload detection from external editor saves or in-memory config updates
        if self._config_mgr:
            self._config_mgr.check_hot_reload()
            if self._config_mgr.revision != self._last_config_revision:
                self._apply_config(force_rebuild=True)
                self._last_config_revision = self._config_mgr.revision

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
        if self._state == NotificationState.SLIDE_OUT and self._fade_on_slide_out:
            fade_prog = min(1.0, self._timer / self._slide_out_time)
            alpha = max(0, int(255 * (1.0 - fade_prog)))

        draw_surf = self._current_tab_surface
        if alpha < 255:
            draw_surf = self._current_tab_surface.copy()
            draw_surf.set_alpha(alpha)

        # Floating breath shimmer during hold
        draw_y = self._top_y
        if self._state == NotificationState.HOLD and self._breath_shimmer_enabled:
            breath = int(math.sin(self._timer * self._breath_speed) * (self._breath_amplitude * self._scale))
            draw_y += breath

        surface.blit(draw_surf, (int(self._current_x), draw_y))

