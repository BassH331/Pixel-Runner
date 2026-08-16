"""
Clean, crystal-clear camera zoom & focus without wave distortion or screen shake.

Used for NPC cutscenes & dialogue focus:
- Bilinear crop centered on target speaker (focus_x, focus_y).
- Smooth lerp interpolation for camera zoom-in & zoom-out.
- High performance (~0.5ms per frame when active, 0ms when inactive).
"""

from typing import Optional
import pygame as pg


class CleanCameraZoom:
    """Clean camera zoom and focus on a target point."""

    def __init__(self, width: int, height: int) -> None:
        self.width: int = width
        self.height: int = height

        self.current_zoom: float = 1.0
        self.target_zoom: float = 1.0
        self.zoom_speed: float = 8.0  # lerp speed (units/second)

        self.curr_focus_x: float = float(width // 2)
        self.curr_focus_y: float = float(height // 2)
        self.target_focus_x: float = float(width // 2)
        self.target_focus_y: float = float(height // 2)

        self.is_active: bool = False
        self.buffer: pg.Surface = pg.Surface((width, height))

    def zoom_in(self, focus_x: float, focus_y: float, target_zoom: float = 1.38) -> None:
        """Start smooth camera zoom in centered on (focus_x, focus_y)."""
        self.is_active = True
        self.target_zoom = target_zoom
        self.target_focus_x = float(max(0, min(focus_x, self.width)))
        self.target_focus_y = float(max(0, min(focus_y, self.height)))

    def zoom_out(self) -> None:
        """Start smooth camera zoom out back to normal 1.0x view."""
        self.target_zoom = 1.0

    def update(self, dt_seconds: float) -> None:
        """Smoothly interpolate zoom factor and focus point."""
        if not self.is_active and abs(self.current_zoom - 1.0) < 0.001:
            return

        # Smooth lerp zoom factor
        zoom_diff = self.target_zoom - self.current_zoom
        if abs(zoom_diff) > 0.001:
            self.current_zoom += zoom_diff * min(1.0, dt_seconds * self.zoom_speed)
        else:
            self.current_zoom = self.target_zoom

        # Smooth lerp focus coordinates
        fx_diff = self.target_focus_x - self.curr_focus_x
        fy_diff = self.target_focus_y - self.curr_focus_y
        if abs(fx_diff) > 0.5 or abs(fy_diff) > 0.5:
            self.curr_focus_x += fx_diff * min(1.0, dt_seconds * self.zoom_speed)
            self.curr_focus_y += fy_diff * min(1.0, dt_seconds * self.zoom_speed)
        else:
            self.curr_focus_x = self.target_focus_x
            self.curr_focus_y = self.target_focus_y

        if abs(self.current_zoom - 1.0) < 0.001 and self.target_zoom == 1.0:
            self.current_zoom = 1.0
            self.is_active = False

    def apply(self, source_surface: pg.Surface, dest_surface: pg.Surface) -> None:
        """Apply bilinear crop zoom centered on target focus onto dest_surface."""
        if self.current_zoom <= 1.001:
            if source_surface != dest_surface:
                dest_surface.blit(source_surface, (0, 0))
            return

        zoom = self.current_zoom
        crop_w = int(self.width / zoom)
        crop_h = int(self.height / zoom)

        crop_x = int(max(0, min(self.curr_focus_x - crop_w // 2, self.width - crop_w)))
        crop_y = int(max(0, min(self.curr_focus_y - crop_h // 2, self.height - crop_h)))

        sub_surf = source_surface.subsurface((crop_x, crop_y, crop_w, crop_h))
        zoomed = pg.transform.smoothscale(sub_surf, (self.width, self.height))
        dest_surface.blit(zoomed, (0, 0))
