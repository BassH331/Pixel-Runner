from __future__ import annotations

from typing import Optional
from enum import Enum

import pygame as pg

from v3x_zulfiqar_gideon import Actor, AssetManager


class NPCState(Enum):
    IDLE = 0


class WizardNPC(Actor):
    """
    Animated Wizard NPC with proximity-based dialogue support.
    """

    _SPRITE_DIR = "assets/graphics/Wizard_NPC"
    _FRAME_COUNT = 6
    _FRAME_DURATION = 0.18

    # Prompt styling (mirrors InteractionPoint)
    _FONT_PATH = "assets/graphics/Darinia/Darinia.ttf"
    _FONT_SIZE = 30
    _PROMPT_COLOR = (255, 255, 255)
    _PROMPT_BG_COLOR = (30, 30, 30, 200)
    _PROMPT_PADDING_X = 16
    _PROMPT_PADDING_Y = 8
    _PROMPT_OFFSET_Y = -70
    _PROMPT_BORDER_RADIUS = 8

    def __init__(
        self,
        x: int,
        y: int,
        text: str,
        title: str = "Wizard",
        scale: float = 2.0,
        proximity_radius: int = 160,
    ) -> None:
        super().__init__(x, y)

        self.text = text
        self.title = title
        self.proximity_radius = proximity_radius
        self._interacted: bool = False
        self._in_range: bool = False
        self.scale = scale

        # --- Animation ---
        self._load_animations()
        self.set_state(NPCState.IDLE)
        if self.state in self.animations:
            self.image = self.animations[self.state][0]

        # Calculate bounding rect of first frame to eliminate transparent padding
        first_frame = self.animations[NPCState.IDLE][0]
        bounding_rect = first_frame.get_bounding_rect()
        self.bottom_offset = first_frame.get_height() - bounding_rect.bottom
        self.visual_height = bounding_rect.height

        self.rect = self.image.get_rect(midbottom=(x, y))
        self.rect.bottom += self.bottom_offset

        # --- Talk prompt (cached surface) ---
        self._font = AssetManager.get_font(self._FONT_PATH, self._FONT_SIZE)
        self._prompt_surface = self._build_prompt()

    def _load_animations(self) -> None:
        frames: list[pg.Surface] = []
        for i in range(self._FRAME_COUNT):
            path = f"{self._SPRITE_DIR}/wizard_npc_{i}.png"
            frame = AssetManager.get_texture(path)
            if self.scale != 1.0:
                new_w = int(frame.get_width() * self.scale)
                new_h = int(frame.get_height() * self.scale)
                frame = pg.transform.scale(frame, (new_w, new_h))
            frames.append(frame)

        self.animations[NPCState.IDLE] = frames

    def _build_prompt(self) -> pg.Surface:
        """Create the cached "Talk [X / ENTER]" prompt surface."""
        text_surf = self._font.render(
            "Talk  [ X / ENTER ]", True, self._PROMPT_COLOR
        )
        w = text_surf.get_width() + self._PROMPT_PADDING_X * 2
        h = text_surf.get_height() + self._PROMPT_PADDING_Y * 2

        bg = pg.Surface((w, h), pg.SRCALPHA)
        pg.draw.rect(
            bg,
            self._PROMPT_BG_COLOR,
            (0, 0, w, h),
            border_radius=self._PROMPT_BORDER_RADIUS,
        )
        pg.draw.rect(
            bg,
            (200, 200, 200, 120),
            (0, 0, w, h),
            width=2,
            border_radius=self._PROMPT_BORDER_RADIUS,
        )
        bg.blit(text_surf, (self._PROMPT_PADDING_X, self._PROMPT_PADDING_Y))
        return bg

    @property
    def can_interact(self) -> bool:
        """True when the player is nearby and hasn't yet interacted."""
        return self._in_range and not self._interacted

    @property
    def has_been_used(self) -> bool:
        return self._interacted

    def mark_interacted(self) -> None:
        self._interacted = True

    def reset(self) -> None:
        self._interacted = False

    def check_proximity(self, player_rect: pg.Rect) -> bool:
        dx = abs(self.rect.centerx - player_rect.centerx)
        dy = abs(self.rect.centery - player_rect.centery)
        distance = (dx * dx + dy * dy) ** 0.5
        self._in_range = distance <= self.proximity_radius
        return self._in_range

    def update(
        self,
        dt: Optional[float] = None,
        scroll_speed: int = 0,
    ) -> None:
        """Scroll with the world and advance idle animation."""
        self.rect.x -= scroll_speed
        super().update(dt if dt is not None else 0.0)

    def draw(self, surface: pg.Surface) -> None:
        """Render the NPC sprite and, if applicable, the talk prompt."""
        super().draw(surface)

        if not self.can_interact:
            return

        # Pulsing alpha for visibility
        ticks = pg.time.get_ticks()
        alpha = 180 + int(75 * abs(((ticks // 8) % 200 - 100) / 100))
        self._prompt_surface.set_alpha(alpha)

        px = self.rect.centerx - self._prompt_surface.get_width() // 2
        
        # Position the prompt relative to the actual visual head, not the image rect top
        feet_y = self.rect.bottom - self.bottom_offset
        head_y = feet_y - self.visual_height
        py = head_y - 20
        
        surface.blit(self._prompt_surface, (px, py))
