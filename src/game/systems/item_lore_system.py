"""
Item Lore & Memory Flashback System for Pixel-Runner.

Manages plain-spoken narrative relics, memory flashback triggers, visual screen sepia effects,
and discovered lore tracking according to STORY_BIBLE.md.
"""
from dataclasses import dataclass
from typing import Dict, Optional, List, Tuple
import math
import pygame as pg
from v3x_zulfiqar_gideon import AssetManager

from src.game.systems.storyline_config_manager import StorylineConfigManager

@dataclass
class RelicData:
    id: str
    title: str
    category: str
    memory_text: str
    icon_path: str
    discovered: bool = False

class ItemLoreSystem:
    _instance: Optional["ItemLoreSystem"] = None

    def __init__(self):
        ItemLoreSystem._instance = self
        self.relics: Dict[str, RelicData] = {}
        self.reload_relics_from_config()

        # Active Flashback Animation State
        self.active_flashback: Optional[RelicData] = None
        self.flashback_timer: float = 0.0
        self.flashback_duration: float = 3.5

        # Cached Fonts
        self.font = AssetManager.get_font('assets/graphics/Darinia/Darinia.ttf', 24)
        self.small_font = AssetManager.get_font('assets/graphics/Darinia/Darinia.ttf', 17)

    @classmethod
    def get_instance(cls) -> "ItemLoreSystem":
        if cls._instance is None:
            cls._instance = ItemLoreSystem()
        return cls._instance

    def reload_relics_from_config(self) -> None:
        """Load or reload relic data from StorylineConfigManager JSON."""
        cfg_mgr = StorylineConfigManager.get_instance()
        relics_data = cfg_mgr.get_relics()
        for r_id, r_info in relics_data.items():
            discovered = self.relics[r_id].discovered if r_id in self.relics else False
            self.relics[r_id] = RelicData(
                id=r_info.get("id", r_id),
                title=r_info.get("title", r_id),
                category=r_info.get("category", "Memory"),
                memory_text=r_info.get("memory_text", ""),
                icon_path=r_info.get("icon_path", ""),
                discovered=discovered
            )

    def discover_relic(self, relic_id: str) -> bool:
        """Trigger discovery and active memory flashback for a relic."""
        self.reload_relics_from_config()
        if relic_id not in self.relics:
            return False
        
        relic = self.relics[relic_id]
        relic.discovered = True
        self.active_flashback = relic
        
        cfg_mgr = StorylineConfigManager.get_instance()
        r_info = cfg_mgr.get_relics().get(relic_id, {})
        self.flashback_duration = float(r_info.get("flashback_duration", 3.5))
        self.flashback_timer = self.flashback_duration
        print(f"[ItemLoreSystem] Memory Flashback Triggered: {relic.title}")
        return True

    def update(self, dt: float) -> None:
        """Update flashback timer and check for config hot-reloads."""
        StorylineConfigManager.get_instance().check_hot_reload()
        if self.flashback_timer > 0.0:
            self.flashback_timer = max(0.0, self.flashback_timer - dt)
            if self.flashback_timer <= 0.0:
                self.active_flashback = None

    def render_flashback_overlay(self, surface: pg.Surface) -> None:
        """Render sepia memory flashback vignette and banner if flashback is active."""
        if self.active_flashback is None or self.flashback_timer <= 0.0:
            return

        w, h = surface.get_size()
        progress = self.flashback_timer / self.flashback_duration

        # Fade in and out alpha envelope
        alpha_factor = math.sin(progress * math.pi)

        # 1. Sepia Memory Flash Screen Vignette
        sepia_surf = pg.Surface((w, h), pg.SRCALPHA)
        sepia_color = (40, 20, 5, int(110 * alpha_factor))
        sepia_surf.fill(sepia_color)
        surface.blit(sepia_surf, (0, 0))

        # 2. Sleek Memory Banner Card
        banner_w = int(w * 0.72)
        banner_h = 95
        bx = (w - banner_w) // 2
        by = int(h * 0.15)

        banner = pg.Surface((banner_w, banner_h), pg.SRCALPHA)
        bg_alpha = int(220 * alpha_factor)
        pg.draw.rect(banner, (15, 10, 25, bg_alpha), (0, 0, banner_w, banner_h), border_radius=8)
        pg.draw.rect(banner, (220, 180, 70, int(255 * alpha_factor)), (0, 0, banner_w, banner_h), width=2, border_radius=8)

        # Title Text
        title_surf = self.font.render(f"MEMORY FLASHBACK: {self.active_flashback.title.upper()}", True, (255, 215, 0))
        banner.blit(title_surf, (20, 12))

        # Memory Text
        mem_surf = self.small_font.render(f'"{self.active_flashback.memory_text}"', True, (240, 240, 240))
        banner.blit(mem_surf, (20, 48))

        surface.blit(banner, (bx, by))
