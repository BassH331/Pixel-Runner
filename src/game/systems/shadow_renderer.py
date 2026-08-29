"""
Shadow Renderer System.

Provides high-performance, perspective-accurate ground silhouette shadows for
entities (Player, NPCs, Enemies, and airborne creatures like Bats).
Uses mask-to-surface silhouettes with intelligent O(1) frame caching.
"""

from __future__ import annotations

from typing import Optional
import pygame as pg


class ShadowRenderer:
    """
    Renders perspective-correct ground silhouette shadows for entities.
    Caches silhouettes per (surface_id, width, height, alpha) to avoid
    redundant surface allocations and transformation operations.
    """

    _cache: dict[tuple[int, int, int, int], tuple[pg.Surface, int, int]] = {}

    @classmethod
    def get_silhouette_shadow(
        cls,
        image: pg.Surface,
        target_w: int,
        target_h: int,
        alpha: int = 115,
    ) -> tuple[pg.Surface, int, int]:
        """
        Generate or retrieve a cached squashed silhouette shadow surface,
        the original image's visual feet Y offset, and the shadow's visual feet bottom.
        """
        target_w = max(2, target_w)
        target_h = max(2, target_h)
        alpha = max(0, min(255, alpha))

        key = (id(image), target_w, target_h, alpha)
        cached = cls._cache.get(key)
        if cached is not None:
            return cached

        # Generate silhouette mask with per-pixel alpha matching the sprite shape
        mask = pg.mask.from_surface(image)
        img_br = image.get_bounding_rect()
        orig_feet_y = img_br.bottom if img_br.height > 0 else image.get_height()

        sil = mask.to_surface(setcolor=(0, 0, 0, alpha), unsetcolor=(0, 0, 0, 0))
        shadow = pg.transform.smoothscale(sil, (target_w, target_h))
        s_br = shadow.get_bounding_rect()
        shadow_feet_bottom = s_br.bottom if s_br.height > 0 else target_h

        # Keep cache bounded to avoid memory leaks over long sessions
        if len(cls._cache) > 2048:
            cls._cache.clear()

        result = (shadow, orig_feet_y, shadow_feet_bottom)
        cls._cache[key] = result
        return result

    @classmethod
    def render_entity_shadow(
        cls,
        surface: pg.Surface,
        entity: pg.sprite.Sprite,
        ground_y: Optional[float] = None,
        base_alpha: int = 115,
        squash_ratio: float = 0.25,
        fade_height: float = 250.0,
        ground_snap: float = 12.0,
        y_offset: int = 0,
    ) -> None:
        """
        Render a ground-projected silhouette shadow beneath an entity.

        Args:
            surface: Target rendering surface.
            entity: Sprite entity with .image and .rect.
            ground_y: Ground plane Y-coordinate. If None, entity is treated as grounded on its feet.
            base_alpha: Maximum shadow opacity (0-255).
            squash_ratio: Vertical scale ratio for perspective ground projection.
            fade_height: Altitude in pixels at which shadow completely fades out.
            ground_snap: Snap distance (px) where entity is considered grounded.
            y_offset: Vertical adjustment in pixels.
        """
        image = getattr(entity, "image", None)
        rect = getattr(entity, "rect", None)
        if image is None or rect is None:
            return

        # Skip invisible or dead/vanished NPCs
        if hasattr(entity, "visible") and not entity.visible:
            return
        if hasattr(entity, "is_death_complete") and getattr(entity, "play_death_on_interact", False) and entity.is_death_complete:
            return

        orig_w, orig_h = image.get_size()
        image_offset = getattr(entity, "image_offset", None)
        offset_x = image_offset.x if image_offset else 0
        offset_y = image_offset.y if image_offset else 0

        draw_x = rect.left - offset_x
        draw_y = rect.top - offset_y

        # Determine scale factor and effective ground plane
        # Generate initial unscaled metadata or full-scale shadow to get orig_feet_y
        temp_w = max(4, int(orig_w))
        temp_h = max(2, int(orig_h * squash_ratio))
        _, orig_feet_y, _ = cls.get_silhouette_shadow(image, temp_w, temp_h, base_alpha)

        # True visual bottom of the sprite pixels in screen coordinates
        true_feet_y = float(draw_y + orig_feet_y)

        if ground_y is not None:
            actual_ground = ground_y
            air_height = max(0.0, actual_ground - true_feet_y)

            # Ground snap tolerance to eliminate idle jitter
            if air_height <= ground_snap:
                scale_factor = 1.0
                effective_ground_y = true_feet_y
            elif air_height >= fade_height:
                return
            else:
                scale_factor = 1.0 - (air_height / fade_height)
                effective_ground_y = actual_ground
        else:
            scale_factor = 1.0
            effective_ground_y = true_feet_y

        # Depth scaling support for ambient parallax creatures (bats)
        depth_scale = getattr(entity, "depth_scale_factor", 1.0)
        scale_factor *= depth_scale

        if scale_factor < 0.05:
            return

        shadow_w = max(4, int(orig_w * scale_factor))
        shadow_h = max(2, int(orig_h * squash_ratio * scale_factor))
        current_alpha = int(base_alpha * min(1.0, scale_factor))

        if current_alpha <= 5:
            return

        shadow_surf, _, shadow_feet_bottom = cls.get_silhouette_shadow(
            image, shadow_w, shadow_h, current_alpha
        )

        # Position: horizontally align with sprite image draw position
        shadow_x = int(draw_x + (orig_w - shadow_w) * 0.5)

        # Vertically anchor right under the feet on the ground plane:
        # shadow_feet_bottom is the exact bottom pixel of the non-empty shadow silhouette.
        # Placing shadow_y at (effective_ground_y - shadow_feet_bottom) guarantees the shadow's feet
        # touch effective_ground_y with 0px error regardless of transparent padding in the sprite.
        shadow_y = int(effective_ground_y - shadow_feet_bottom + y_offset)

        surface.blit(shadow_surf, (shadow_x, shadow_y))


