"""Auto-fit aspect-ratio preview scaler for Pygame animation sprites.

Calculates scale factors using non-transparent bounding boxes and aligns feet to
the dynamic floor coordinate.
"""

import pygame as pg
from typing import Any, Dict, Tuple

class PreviewScaler:
    @staticmethod
    def calculate_auto_fit(
        surface: pg.Surface,
        preview_rect: pg.Rect,
        floor_y: int,
        margin: float = 0.90
    ) -> Dict[str, Any]:
        """Calculates scale and positions to fit the sprite surface into the preview rect.
        
        Preserves aspect ratio, aligns feet/bottom to floor_y, and uses
        non-transparent bounding box if possible.
        """
        # Find non-transparent bounding box
        visible_rect = surface.get_bounding_rect()
        fallback = False

        if visible_rect.width == 0 or visible_rect.height == 0:
            visible_rect = pg.Rect(0, 0, surface.get_width(), surface.get_height())
            fallback = True

        # Calculate maximum limits
        max_w = preview_rect.width * margin
        # Height limit is from top of container to floor line
        max_h = (floor_y - preview_rect.y) * margin

        # Prevent division by zero
        vis_w = max(1, visible_rect.width)
        vis_h = max(1, visible_rect.height)

        # Scale factor is limited by the tighter constraint
        scale = min(max_w / vis_w, max_h / vis_h)

        # Calculate scaled dimensions
        scaled_w = int(surface.get_width() * scale)
        scaled_h = int(surface.get_height() * scale)

        # Center X position within preview_rect for Review mode
        # Center visible rect center with preview center
        offset_x = (visible_rect.x + visible_rect.width / 2) * scale
        x_pos_centered = int(preview_rect.centerx - offset_x)

        # Align visible bottom to floor_y
        offset_y = visible_rect.bottom * scale
        y_pos = int(floor_y - offset_y)

        return {
            "scale": scale,
            "scaled_width": scaled_w,
            "scaled_height": scaled_h,
            "x_pos_centered": x_pos_centered,
            "y_pos": y_pos,
            "visible_rect": (visible_rect.x, visible_rect.y, visible_rect.width, visible_rect.height),
            "fallback": fallback
        }
