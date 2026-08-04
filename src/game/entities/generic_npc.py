"""
Generic NPC — a data-driven NPC that can use any sprite folder.

Add new NPCs purely from ``level_1.json`` without writing Python code::

    {
        "id": 6,
        "distance": 5000,
        "type": "npc",
        "params": {
            "npc_type": "generic",
            "sprite_dir": "assets/graphics/Goblin/Idle",
            "title": "Goblin Merchant",
            "radius": 160,
            "scale": 2.0,
            "text": "Got some rare trinkets, if you're interested..."
        }
    }
"""

from __future__ import annotations

import os
from typing import Optional
from enum import Enum

import pygame as pg

from v3x_zulfiqar_gideon import Actor, AssetManager
from .hitbox_registry import HitboxRegistry


class _GenericNPCState(Enum):
    IDLE = 0
    DEATH = 1
    WALK = 2
    SPAWN = 3


class GenericNPC(Actor):
    """A reusable NPC driven entirely by constructor arguments.

    Supports custom walk entrance, spawn animation, dialogue interaction, and death disintegration.
    """

    # Prompt styling (same as WizardNPC for visual consistency)
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
        sprite_dir: str,
        text: str,
        title: str = "NPC",
        scale: Optional[float] = None,
        proximity_radius: int = 180,
        frame_duration: float = 0.15,
        prompt_text: str = "Talk  [ X / ENTER ]",
        play_death_on_interact: bool = False,
        death_sprite_dir: Optional[str] = None,
        walk_sprite_dir: Optional[str] = None,
        spawn_sprite_dir: Optional[str] = None,
        is_intro_npc: bool = False,
        walk_speed: float = -150.0,
    ) -> None:
        super().__init__(x, y)

        self.text = text
        self.title = title
        self.proximity_radius = proximity_radius
        self._interacted: bool = False
        self._in_range: bool = False
        self.play_death_on_interact: bool = play_death_on_interact
        self.is_dying_or_dead: bool = False

        self.is_intro_npc: bool = is_intro_npc
        self.is_walking: bool = is_intro_npc
        self.is_spawning: bool = False
        self.is_death_complete: bool = not play_death_on_interact
        self.walk_speed: float = walk_speed

        # Auto-detect folder paths if not specified
        sdir = sprite_dir.rstrip("/")
        parent = os.path.dirname(sdir) if os.path.basename(sdir).lower() == "idle" else sdir

        if self.play_death_on_interact and not death_sprite_dir:
            for candidate in ["Death", "death", "DEATH"]:
                cand_path = os.path.join(parent, candidate)
                if os.path.isdir(cand_path):
                    death_sprite_dir = cand_path
                    break
        self.death_sprite_dir = death_sprite_dir

        if self.is_intro_npc and not walk_sprite_dir:
            for candidate in ["Walk", "walk", "WALK"]:
                cand_path = os.path.join(parent, candidate)
                if os.path.isdir(cand_path):
                    walk_sprite_dir = cand_path
                    break
        self.walk_sprite_dir = walk_sprite_dir

        if self.is_intro_npc and not spawn_sprite_dir:
            for candidate in ["Spawn", "spawn", "SPAWN"]:
                cand_path = os.path.join(parent, candidate)
                if os.path.isdir(cand_path):
                    spawn_sprite_dir = cand_path
                    break
        self.spawn_sprite_dir = spawn_sprite_dir

        # Resolve registry key and margins early to determine scale
        folder_name = os.path.basename(sprite_dir.rstrip("/"))
        if folder_name.lower() == "idle":
            parent_dir = os.path.dirname(sprite_dir.rstrip("/"))
            folder_name = os.path.basename(parent_dir)
        sprite_key = f"generic_npc_{folder_name.lower()}"
        margins = HitboxRegistry.get_margins(sprite_key)

        final_scale = scale if scale is not None else margins.scale
        self.scale = final_scale

        # ── 1. Load IDLE animation frames ──────────────────────────────────
        raw_idle_frames = AssetManager.get_animation_frames(sprite_dir)
        if not raw_idle_frames:
            placeholder = pg.Surface((32, 32), pg.SRCALPHA)
            placeholder.fill((255, 0, 255, 180))
            raw_idle_frames = [placeholder]

        scaled_idle = [
            pg.transform.scale(f, (int(f.get_width() * final_scale), int(f.get_height() * final_scale)))
            for f in raw_idle_frames
        ]
        self.animations[_GenericNPCState.IDLE] = scaled_idle
        self.state_configs[_GenericNPCState.IDLE] = type(
            "SC", (), {"animation_speed": frame_duration, "loops": True, "interruptible": False}
        )()

        # ── 2. Load WALK animation frames ──────────────────────────────────
        if self.walk_sprite_dir and os.path.exists(self.walk_sprite_dir):
            raw_walk_frames = AssetManager.get_animation_frames(self.walk_sprite_dir)
            if raw_walk_frames:
                scaled_walk = [
                    pg.transform.scale(f, (int(f.get_width() * final_scale), int(f.get_height() * final_scale)))
                    for f in raw_walk_frames
                ]
                self.animations[_GenericNPCState.WALK] = scaled_walk
                self.state_configs[_GenericNPCState.WALK] = type(
                    "SC", (), {"animation_speed": frame_duration, "loops": True, "interruptible": False}
                )()

        # ── 3. Load SPAWN animation frames ──────────────────────────────────
        if self.spawn_sprite_dir and os.path.exists(self.spawn_sprite_dir):
            raw_spawn_frames = AssetManager.get_animation_frames(self.spawn_sprite_dir)
            if raw_spawn_frames:
                scaled_spawn = [
                    pg.transform.scale(f, (int(f.get_width() * final_scale), int(f.get_height() * final_scale)))
                    for f in raw_spawn_frames
                ]
                self.animations[_GenericNPCState.SPAWN] = scaled_spawn
                self.state_configs[_GenericNPCState.SPAWN] = type(
                    "SC", (), {"animation_speed": frame_duration, "loops": False, "interruptible": False}
                )()

        # ── 4. Load DEATH animation frames ──────────────────────────────────
        if self.play_death_on_interact and self.death_sprite_dir and os.path.exists(self.death_sprite_dir):
            raw_death_frames = AssetManager.get_animation_frames(self.death_sprite_dir)
            if raw_death_frames:
                scaled_death = [
                    pg.transform.scale(f, (int(f.get_width() * final_scale), int(f.get_height() * final_scale)))
                    for f in raw_death_frames
                ]
                self.animations[_GenericNPCState.DEATH] = scaled_death
                self.state_configs[_GenericNPCState.DEATH] = type(
                    "SC", (), {"animation_speed": frame_duration, "loops": False, "interruptible": False}
                )()

        # ── Per-state bottom offsets ─────────────────────────────────────
        # Different animation sets have different frame sizes and transparent
        # padding.  Pre-compute the bottom offset for each state so we can
        # keep the NPC's feet pinned to the ground across state transitions.
        self._state_bottom_offsets: dict = {}
        for st, frames in self.animations.items():
            fr = frames[0]
            br = fr.get_bounding_rect()
            self._state_bottom_offsets[st] = fr.get_height() - br.bottom

        # Set initial animation state
        if self.is_walking and _GenericNPCState.WALK in self.animations:
            self.set_state(_GenericNPCState.WALK, force=True)
        else:
            self.set_state(_GenericNPCState.IDLE, force=True)

        if self.state in self.animations:
            self.image = self.animations[self.state][0]

        # Use the IDLE offset as the canonical ground reference
        first_frame = self.animations[_GenericNPCState.IDLE][0]
        bounding_rect = first_frame.get_bounding_rect()
        self.bottom_offset = self._state_bottom_offsets.get(_GenericNPCState.IDLE, 0)
        self.visual_height = bounding_rect.height

        self.rect = self.image.get_rect(midbottom=(x, y))
        self.rect.bottom += self._state_bottom_offsets.get(self.state, 0)

        # Intro NPCs walk in from the right → they should face left toward the player
        if self.is_intro_npc:
            self.facing_left = True

        self.adjust_hitbox_sides(left=margins.left, right=margins.right, top=margins.top, bottom=margins.bottom)

        # ── Talk prompt (cached surface) ────────────────────────────────────
        self._font = AssetManager.get_font(self._FONT_PATH, self._FONT_SIZE)
        self._prompt_surface = self._build_prompt(prompt_text)

    def _build_prompt(self, text: str) -> pg.Surface:
        text_surf = self._font.render(text, True, self._PROMPT_COLOR)
        w = text_surf.get_width() + self._PROMPT_PADDING_X * 2
        h = text_surf.get_height() + self._PROMPT_PADDING_Y * 2

        bg = pg.Surface((w, h), pg.SRCALPHA)
        pg.draw.rect(bg, self._PROMPT_BG_COLOR, (0, 0, w, h), border_radius=self._PROMPT_BORDER_RADIUS)
        pg.draw.rect(bg, (200, 200, 200, 120), (0, 0, w, h), width=2, border_radius=self._PROMPT_BORDER_RADIUS)
        bg.blit(text_surf, (self._PROMPT_PADDING_X, self._PROMPT_PADDING_Y))
        return bg

    @property
    def can_interact(self) -> bool:
        return self._in_range and not self._interacted and not self.is_dying_or_dead and not self.is_walking and not self.is_spawning

    @property
    def has_been_used(self) -> bool:
        return self._interacted or self.is_dying_or_dead

    def mark_interacted(self) -> None:
        self._interacted = True

    def set_state(self, new_state, force: bool = False) -> None:
        """Override to re-anchor the sprite to the ground when switching states.

        Different animation sets (Walk=96px, Spawn=128px, etc.) have different
        frame sizes and transparent padding.  We compute a *visual ground*
        position (rect.bottom minus per-state bottom offset) and preserve it
        across transitions so the NPC's feet stay pinned to the ground.
        """
        old_state = self.state
        old_offset = getattr(self, '_state_bottom_offsets', {}).get(old_state, 0)
        visual_ground = self.rect.bottom - old_offset  # where the feet are

        super().set_state(new_state, force=force)

        # If the state actually changed, update image & rect to the new frame
        frames = self.animations.get(self.state)
        if frames:
            self.image = frames[int(self.animation_index)]
            old_centerx = self.rect.centerx
            self.rect = self.image.get_rect()
            self.rect.centerx = old_centerx
            # Re-anchor: feet stay at the same visual ground position
            new_offset = self._state_bottom_offsets.get(self.state, 0)
            self.rect.bottom = visual_ground + new_offset

    def trigger_death(self) -> None:
        """Trigger death animation on interaction completion."""
        self._interacted = True
        self.is_dying_or_dead = True
        self.is_death_complete = False
        if _GenericNPCState.DEATH in self.animations:
            self.set_state(_GenericNPCState.DEATH, force=True)
        else:
            self.is_death_complete = True

    def reset(self) -> None:
        self._interacted = False

    def check_proximity(self, player_rect: pg.Rect) -> bool:
        dx = abs(self.rect.centerx - player_rect.centerx)
        dy = abs(self.rect.centery - player_rect.centery)
        distance = (dx * dx + dy * dy) ** 0.5

        if self.is_walking and distance <= self.proximity_radius:
            self.is_walking = False
            self.is_spawning = True
            # Face toward the player
            self.facing_left = self.rect.centerx > player_rect.centerx
            print(f"[INTRO NPC] Proximity reached! dist={distance:.0f}px  NPC.x={self.rect.centerx}  Player.x={player_rect.centerx}  facing_left={self.facing_left}")
            if _GenericNPCState.SPAWN in self.animations:
                self.set_state(_GenericNPCState.SPAWN, force=True)
                print("[INTRO NPC] → Playing SPAWN animation")
            else:
                self.is_spawning = False
                self.set_state(_GenericNPCState.IDLE, force=True)
                print("[INTRO NPC] → No spawn anim, going to IDLE")

        self._in_range = distance <= self.proximity_radius
        return self._in_range

    def update(self, dt: Optional[float] = None, scroll_speed: int = 0) -> None:
        delta_time = dt if dt is not None else 16.67
        # dt comes in as milliseconds — convert to seconds for velocity math
        delta_seconds = delta_time / 1000.0

        if not hasattr(self, "world_x"):
            self.rect.x -= scroll_speed
            if self.state == _GenericNPCState.WALK:
                self.rect.x += int(self.walk_speed * delta_seconds)

        if self.state == _GenericNPCState.SPAWN:
            spawn_frames = self.animations.get(_GenericNPCState.SPAWN)
            if spawn_frames and self.animation_index >= len(spawn_frames) - 1:
                self.is_spawning = False
                self.set_state(_GenericNPCState.IDLE, force=True)
                print("[INTRO NPC] Spawn anim complete → IDLE (ready for dialogue)")
        elif self.state == _GenericNPCState.DEATH:
            death_frames = self.animations.get(_GenericNPCState.DEATH)
            if death_frames and self.animation_index >= len(death_frames) - 1:
                if not self.is_death_complete:
                    print("[INTRO NPC] Death anim complete → Player unlocked")
                self.is_death_complete = True

        super().update(delta_time)

    def draw(self, surface: pg.Surface) -> None:
        super().draw(surface)

        if not self.can_interact:
            return

        ticks = pg.time.get_ticks()
        alpha = 180 + int(75 * abs(((ticks // 8) % 200 - 100) / 100))
        self._prompt_surface.set_alpha(alpha)

        px = self.rect.centerx - self._prompt_surface.get_width() // 2
        feet_y = self.rect.bottom - self.bottom_offset
        head_y = feet_y - self.visual_height
        py = head_y - 20

        surface.blit(self._prompt_surface, (px, py))
