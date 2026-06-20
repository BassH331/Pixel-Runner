"""
Boss Manager module containing Registry-based Factory and UI drawing logic.
"""

from typing import Optional, Dict, Any, Type
import os
import pygame as pg

from v3x_zulfiqar_gideon import Actor
from src.game.entities.skeleton import Skeleton
from src.game.entities.fire_wizard import FireWizard


class BossManager:
    """
    Registry-based Factory and Manager for all boss entities.
    Handles spawning, status checking, and rendering the boss health bar.
    """
    
    # ── Boss Registry Mapping ────────────────────────────────────────────────
    # Map keywords/substrings in the sprite_dir to their respective boss classes.
    # Add new boss classes to this dictionary to integrate them seamlessly.
    _BOSS_REGISTRY: Dict[str, Type[Actor]] = {
        "wizard": FireWizard,
        "skeleton": Skeleton,
    }
    
    @classmethod
    def resolve_boss_class(cls, sprite_dir: Optional[str]) -> Type[Actor]:
        """
        Scan the sprite directory string to resolve the matching boss class.
        Falls back to Skeleton if no match is found.
        """
        if sprite_dir:
            sprite_dir_lower = sprite_dir.lower()
            for key, boss_cls in cls._BOSS_REGISTRY.items():
                if key in sprite_dir_lower:
                    return boss_cls
        return Skeleton

    @classmethod
    def spawn_boss(
        cls,
        params: dict,
        player_sprite: Any,
        screen_width: int,
        screen_height: int
    ) -> Actor:
        """
        Polymorphically spawn and initialize a boss entity using the registry factory.
        
        Args:
            params: Dictionary of parameters from the level configuration.
            player_sprite: Player instance reference.
            screen_width: Width of game window.
            screen_height: Height of game window.
            
        Returns:
            The instantiated boss Actor instance with configured metadata.
        """
        title = params.get("title", "Boss")
        health = params.get("health")
        if health is not None:
            health = float(health)
            
        tier = params.get("tier", "boss")
        sprite_dir = params.get("sprite_dir") or None
        behaviour_map = params.get("behaviour_map") or None
        scale = params.get("scale")
        if scale is not None:
            scale = float(scale)
            
        # Default spawn coordinates
        spawn_x = screen_width + 200
        spawn_y = screen_height - 70
        
        # 1. Resolve boss class dynamically
        boss_class: Any = cls.resolve_boss_class(sprite_dir)
        
        # 2. Instantiate using the unified constructor signature
        boss = boss_class(
            x=spawn_x,
            y=spawn_y,
            player=player_sprite,
            tier=tier,
            sprite_root=sprite_dir,
            behaviour_map=behaviour_map,
            custom_scale=scale,
            custom_health=health
        )
        
        # 3. Attach common metadata tags for the game engine
        setattr(boss, "is_boss", True)
        setattr(boss, "boss_title", title)
        setattr(boss, "tier", tier)
        setattr(boss, "event_id", params.get("_event_id"))
        setattr(boss, "event_distance", params.get("_event_distance"))
        
        return boss

    @classmethod
    def get_active_boss(cls, obstacle_group: pg.sprite.Group) -> Optional[Actor]:
        """
        Return the active, living boss sprite from the obstacle group.
        """
        for sprite in obstacle_group.sprites():
            if getattr(sprite, "is_boss", False):
                state = getattr(sprite, "state", None)
                state_name = getattr(state, "name", None)
                health = getattr(sprite, "_health", 0.0)
                if state_name != "DEATH" and health > 0:
                    return sprite
        return None

    @classmethod
    def is_boss_active(cls, obstacle_group: pg.sprite.Group) -> bool:
        """
        Check if any boss is currently active and alive in the scene.
        """
        return cls.get_active_boss(obstacle_group) is not None

    @classmethod
    def draw_boss_health_bar(
        cls,
        surface: pg.Surface,
        obstacle_group: pg.sprite.Group,
        screen_width: int,
        screen_height: int
    ) -> None:
        """
        Render a premium boss health bar overlay if a boss is active.
        """
        boss_sprite = cls.get_active_boss(obstacle_group)
        if boss_sprite is None:
            return
            
        title = getattr(boss_sprite, "boss_title", "Boss")
        health = getattr(boss_sprite, "_health", 0.0)
        max_health = getattr(boss_sprite, "_max_health", 100.0)
        pct = max(0.0, min(1.0, health / max_health))
        
        # Layout math
        bar_w = 600
        bar_h = 24
        bar_x = (screen_width - bar_w) // 2
        bar_y = screen_height - 80
        
        # Draw shadows/glow
        glow_rect = pg.Rect(bar_x - 3, bar_y - 3, bar_w + 6, bar_h + 6)
        pg.draw.rect(surface, (15, 15, 20), glow_rect, border_radius=6)
        pg.draw.rect(surface, (231, 76, 60), glow_rect, width=1, border_radius=6)  # Red outline
        
        # Draw background bar
        bg_rect = pg.Rect(bar_x, bar_y, bar_w, bar_h)
        pg.draw.rect(surface, (30, 30, 35), bg_rect, border_radius=4)
        
        # Draw filled part
        if pct > 0:
            fill_w = int(bar_w * pct)
            fill_rect = pg.Rect(bar_x, bar_y, fill_w, bar_h)
            # Draw gradient red
            pg.draw.rect(surface, (192, 57, 43), fill_rect, border_radius=4)
            # Highlight top half
            top_rect = pg.Rect(bar_x, bar_y, fill_w, bar_h // 2)
            pg.draw.rect(surface, (231, 76, 60), top_rect, border_radius=4)
            
        # Draw boss name and health numbers
        font = pg.font.SysFont("Arial", 14, bold=True)
        lbl = f"{title.upper()}  —  {int(health)}/{int(max_health)}"
        txt_surf = font.render(lbl, True, (255, 255, 255))
        txt_rect = txt_surf.get_rect(center=bg_rect.center)
        surface.blit(txt_surf, txt_rect)
