"""
Animated Dialogue Renderer System

Provides per-character typewriter reveal with an enlarge-then-shrink animation.
Each newly revealed letter spawns enlarged (e.g. 1.8x scale) and smoothly scales down
to normal size (1.0x scale) over exactly 1.0 second.

Also supports thematic per-NPC dialogue style presets (Spirit, Necromancer, Frost, etc.).
"""

import math
import time
from typing import List, Tuple, Optional, Dict, Any
import pygame as pg


class AnimatedDialogueRenderer:
    """
    Manages stateful typewriter text rendering with per-character scaling animations
    and per-NPC thematic effects.
    """

    def __init__(
        self,
        typing_speed: float = 35.0,  # characters per second
        scale_duration: float = 1.0,  # seconds for letter to shrink from enlarged to 1.0x
        max_scale: float = 1.8,       # peak scale when letter first appears
        theme: str = "standard",
    ) -> None:
        self.typing_speed: float = typing_speed
        self.scale_duration: float = scale_duration
        self.max_scale: float = max_scale
        self.theme: str = theme

        self._text: str = ""
        self._char_progress: float = 0.0
        self._birth_times: List[float] = []
        self._is_complete: bool = False
        self._glyph_cache: Dict[Tuple[str, Tuple[int, int, int], int], pg.Surface] = {}

    def set_text(self, text: str) -> None:
        """Set new target text and reset character birth timestamps."""
        self._text = text
        self._char_progress = 0.0
        self._birth_times = []
        self._is_complete = False

    def reset(self) -> None:
        """Reset typewriter progress."""
        self._char_progress = 0.0
        self._birth_times = []
        self._is_complete = False

    def skip_to_end(self) -> None:
        """Instantly reveal all characters at scale 1.0x."""
        self._char_progress = float(len(self._text))
        now = time.time()
        # Set birth times far in the past so scale is immediately 1.0x
        self._birth_times = [now - (self.scale_duration + 0.1)] * len(self._text)
        self._is_complete = True

    @property
    def is_complete(self) -> bool:
        return self._is_complete or (int(self._char_progress) >= len(self._text))

    @property
    def current_char_count(self) -> int:
        return int(self._char_progress)

    def update(self, dt_sec: float) -> None:
        """Advance typewriter progress and record character spawn timestamps."""
        if not self._text or self._is_complete:
            return

        prev_count = int(self._char_progress)
        self._char_progress += self.typing_speed * dt_sec
        now = time.time()

        # Record birth time for newly revealed characters
        new_count = min(int(self._char_progress), len(self._text))
        for _ in range(prev_count, new_count):
            self._birth_times.append(now)

        if new_count >= len(self._text):
            self._char_progress = float(len(self._text))
            self._is_complete = True

    def wrap_text(self, font: pg.font.Font, max_width: int) -> List[str]:
        """Wrap current target text into lines that fit within max_width."""
        if not self._text:
            return []

        words = self._text.split(" ")
        lines: List[str] = []
        curr_line = ""

        for word in words:
            test_line = f"{curr_line} {word}".strip() if curr_line else word
            if font.size(test_line)[0] <= max_width:
                curr_line = test_line
            else:
                if curr_line:
                    lines.append(curr_line)
                curr_line = word
        if curr_line:
            lines.append(curr_line)

        return lines

    def render(
        self,
        surface: pg.Surface,
        font: pg.font.Font,
        rect: pg.Rect,
        color: Tuple[int, int, int] = (255, 255, 255),
        shadow_color: Optional[Tuple[int, int, int]] = (0, 0, 0),
        alpha: int = 255,
        align: str = "center",
        line_spacing: int = 6,
    ) -> int:
        """
        Draw animated typewriter text line-by-line within rect.
        Returns total height of rendered text block.
        """
        if not self._text or alpha <= 0:
            return 0

        now = time.time()
        lines = self.wrap_text(font, rect.width)
        line_height = font.get_linesize() + line_spacing
        total_text_h = len(lines) * line_height

        # Position Y
        start_y = rect.top + (rect.height - total_text_h) // 2 if align == "center_v" else rect.top

        char_idx_tracker = 0
        visible_chars = int(self._char_progress)

        ticks = pg.time.get_ticks()

        for line_i, line_str in enumerate(lines):
            line_y = start_y + line_i * line_height
            if line_y > rect.bottom:
                break

            # Calculate total standard line width for horizontal alignment
            total_line_w = font.size(line_str)[0]
            if align == "center":
                start_x = rect.centerx - total_line_w // 2
            elif align == "right":
                start_x = rect.right - total_line_w
            else:
                start_x = rect.left

            curr_x = start_x

            for char in line_str:
                if char_idx_tracker >= visible_chars:
                    break

                # Get birth timestamp for this character
                birth_t = self._birth_times[char_idx_tracker] if char_idx_tracker < len(self._birth_times) else now - 10.0
                elapsed = now - birth_t

                # Calculate scale factor (1.8x -> 1.0x over scale_duration seconds)
                if elapsed < self.scale_duration and self.scale_duration > 0:
                    shrink_progress = max(0.0, min(1.0, elapsed / self.scale_duration))
                    # Ease-out curve for smooth landing
                    ease_factor = 1.0 - (1.0 - shrink_progress) * (1.0 - shrink_progress)
                    scale = self.max_scale - (self.max_scale - 1.0) * ease_factor
                else:
                    scale = 1.0

                # Determine standard char dimensions
                c_w, c_h = font.size(char)
                if c_w <= 0:
                    c_w = font.size(" ")[0]

                # Per-theme extra offsets/effects
                offset_x, offset_y = 0, 0
                if self.theme == "spirit":
                    offset_y += math.sin(ticks * 0.006 + char_idx_tracker * 0.4) * 3.0
                elif self.theme == "necromancer":
                    if elapsed < self.scale_duration:
                        offset_x += (math.sin(ticks * 0.05 + char_idx_tracker) * 2.0) * (1.0 - elapsed / self.scale_duration)
                elif self.theme == "skyfall":
                    offset_y += math.sin(ticks * 0.003 + char_idx_tracker * 0.2) * 2.0

                # Render letter surface
                cache_key = (char, color, font.get_height())
                if cache_key not in self._glyph_cache:
                    self._glyph_cache[cache_key] = font.render(char, True, color)
                glyph_surf = self._glyph_cache[cache_key]

                # Render drop shadow if requested
                if shadow_color:
                    shd_key = (char, shadow_color, font.get_height())
                    if shd_key not in self._glyph_cache:
                        self._glyph_cache[shd_key] = font.render(char, True, shadow_color)
                    shd_surf = self._glyph_cache[shd_key]

                    # Scale shadow surface if letter is enlarged
                    if scale != 1.0:
                        sw = max(1, int(c_w * scale))
                        sh = max(1, int(c_h * scale))
                        shd_scaled = pg.transform.smoothscale(shd_surf, (sw, sh))
                        ox = (sw - c_w) // 2
                        oy = (sh - c_h) // 2
                        if alpha < 255:
                            shd_scaled.set_alpha(int(alpha * 0.8))
                        surface.blit(shd_scaled, (curr_x - ox + 2 + int(offset_x), line_y - oy + 2 + int(offset_y)))
                    else:
                        if alpha < 255:
                            shd_surf.set_alpha(int(alpha * 0.8))
                        surface.blit(shd_surf, (curr_x + 2 + int(offset_x), line_y + 2 + int(offset_y)))

                # Draw main letter surface
                if scale != 1.0:
                    sw = max(1, int(c_w * scale))
                    sh = max(1, int(c_h * scale))
                    glyph_scaled = pg.transform.smoothscale(glyph_surf, (sw, sh))
                    ox = (sw - c_w) // 2
                    oy = (sh - c_h) // 2
                    if alpha < 255:
                        glyph_scaled.set_alpha(alpha)
                    surface.blit(glyph_scaled, (curr_x - ox + int(offset_x), line_y - oy + int(offset_y)))
                else:
                    if alpha < 255:
                        glyph_surf.set_alpha(alpha)
                    surface.blit(glyph_surf, (curr_x + int(offset_x), line_y + int(offset_y)))

                curr_x += c_w
                char_idx_tracker += 1

            # Include space character for space boundary between words
            if char_idx_tracker < visible_chars and char_idx_tracker < len(self._text) and self._text[char_idx_tracker] == " ":
                char_idx_tracker += 1

        return total_text_h
