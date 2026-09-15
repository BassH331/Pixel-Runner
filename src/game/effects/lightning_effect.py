"""
Black & White Lightning Flash Effect module for Pixel-Runner.

Renders a high-contrast black-and-white lightning screen flash with procedurally generated
lightning bolts and a 1-second smooth fade-in/fade-out envelope. Silent (no audio).
"""
from typing import Optional, List, Tuple
import math
import random
import pygame as pg

class LightningEffect:
    _instance: Optional["LightningEffect"] = None

    def __init__(self):
        LightningEffect._instance = self
        self.active: bool = False
        self.timer: float = 0.0
        self.duration: float = 1.0  # 1 second duration
        self.bolt_points: List[List[Tuple[int, int]]] = []
        self._last_bolt_gen: float = 0.0

    @classmethod
    def get_instance(cls) -> "LightningEffect":
        if cls._instance is None:
            cls._instance = LightningEffect()
        return cls._instance

    def trigger(self, duration: float = 1.0, staff_pos: Optional[Tuple[int, int]] = None) -> None:
        """Trigger a 1-second smooth black & white lightning flash sequence (silent)."""
        self.active = True
        self.duration = duration
        self.timer = duration
        self._generate_bolts(staff_pos)
        print("[LightningEffect] Black & White Staff Strike Lightning triggered (silent, 1.0s duration).")

    def _generate_bolts(self, staff_pos: Optional[Tuple[int, int]] = None) -> None:
        """Generate procedural jagged lightning bolt paths."""
        self.bolt_points.clear()
        screen_surf = pg.display.get_surface()
        w = screen_surf.get_width() if screen_surf else 1280
        h = screen_surf.get_height() if screen_surf else 720

        num_bolts = random.randint(2, 4)
        for _ in range(num_bolts):
            start_x = staff_pos[0] if staff_pos else random.randint(int(w * 0.2), int(w * 0.8))
            start_y = 0
            end_x = start_x + random.randint(-150, 150)
            end_y = staff_pos[1] if staff_pos else h

            segments = 10
            points = [(start_x, start_y)]
            curr_x, curr_y = start_x, start_y
            dx = (end_x - start_x) / segments
            dy = (end_y - start_y) / segments

            for i in range(1, segments):
                curr_x += dx + random.randint(-35, 35)
                curr_y += dy
                points.append((int(curr_x), int(curr_y)))

            points.append((end_x, end_y))
            self.bolt_points.append(points)

    def update(self, dt: float) -> None:
        """Update lightning timer and regenerate bolt jitter."""
        if not self.active:
            return

        self.timer = max(0.0, self.timer - dt)
        if self.timer <= 0.0:
            self.active = False
            self.bolt_points.clear()
        else:
            # Regenerate bolt jitter every 0.08s for fast flashing
            if self.duration - self.timer - self._last_bolt_gen > 0.08:
                self._generate_bolts()
                self._last_bolt_gen = self.duration - self.timer

    def render(self, surface: pg.Surface) -> None:
        """Render smooth 1s fade black-and-white lightning overlay and jagged bolts."""
        if not self.active or self.timer <= 0.0:
            return

        w, h = surface.get_size()
        progress = self.timer / self.duration
        alpha_factor = math.sin(progress * math.pi)  # Smooth 1s fade in / fade out

        # Fast strobe flicker multiplier for black/white flash
        strobe = math.sin(progress * math.pi * 12.0)
        flash_color = (255, 255, 255) if strobe > 0 else (0, 0, 0)
        flash_alpha = int(140 * alpha_factor)

        # 1. High-contrast screen flash overlay
        flash_surf = pg.Surface((w, h), pg.SRCALPHA)
        flash_surf.fill((*flash_color, flash_alpha))
        surface.blit(flash_surf, (0, 0))

        # 2. Render bright white lightning bolts with black outline
        bolt_alpha = int(255 * alpha_factor)
        for points in self.bolt_points:
            if len(points) > 1:
                # Black outer glow/shadow
                pg.draw.lines(surface, (0, 0, 0, bolt_alpha), False, points, width=6)
                # Stark white core lightning
                pg.draw.lines(surface, (255, 255, 255, bolt_alpha), False, points, width=3)
