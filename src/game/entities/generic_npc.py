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

def _find_action_folder(sprite_dir: str, keywords: list[str]) -> Optional[str]:
    """Find a sibling/ancestor folder matching action keywords (e.g. walk, death, spawn)."""
    abs_sdir = os.path.abspath(sprite_dir.rstrip("/"))
    curr = abs_sdir
    is_rel = not os.path.isabs(sprite_dir)
    for _ in range(3):
        parent = os.path.dirname(curr)
        if not parent or parent == curr:
            break
        try:
            subdirs = [d for d in os.listdir(parent) if os.path.isdir(os.path.join(parent, d))]
        except OSError:
            break

        rel_from_parent = os.path.relpath(abs_sdir, parent)
        rel_parts = rel_from_parent.split(os.sep)
        sub_tail = rel_parts[-1] if len(rel_parts) > 1 and rel_parts[-1].lower() in ("no bg", "with bg") else ""

        for s in subdirs:
            s_lo = s.lower()
            if any(kw in s_lo for kw in keywords):
                cand = os.path.join(parent, s)
                res = None
                if sub_tail:
                    cand_tail = os.path.join(cand, sub_tail)
                    if os.path.isdir(cand_tail):
                        res = cand_tail
                if res is None and os.path.isdir(cand):
                    res = cand
                if res:
                    return os.path.relpath(res, os.getcwd()) if is_rel else res
        curr = parent
    return None


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
        play_death_on_interact: bool = True,
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
        if not death_sprite_dir:
            death_sprite_dir = _find_action_folder(sprite_dir, ["death", "die"])
        self.death_sprite_dir = death_sprite_dir
        if self.death_sprite_dir:
            self.play_death_on_interact = True
            self.is_death_complete = False

        if not walk_sprite_dir:
            walk_sprite_dir = _find_action_folder(sprite_dir, ["walk", "run"])
        self.walk_sprite_dir = walk_sprite_dir

        if not spawn_sprite_dir:
            spawn_sprite_dir = _find_action_folder(sprite_dir, ["spawn"])
        self.spawn_sprite_dir = spawn_sprite_dir

        # ── Spirit of the Scythe Specific Identification ───────────────────────
        self.is_spirit_of_scythe: bool = (
            "spirit of the scythe" in str(self.title).lower() or
            "scythe whispers" in str(self.title).lower() or
            "evil eye beast" in str(self.death_sprite_dir or "").lower() or
            "evil eye beast" in str(sprite_dir).lower()
        )
        self.is_trance_active: bool = False
        self._trance_phase: int = 0  # 0: None, 1: Spawning (Eye Opening), 2: Floating Text, 3: Eye Closing
        self._trance_text_timer: float = 0.0
        self._trance_text_duration: float = 3.5  # seconds text stays floating on screen

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
        # For Spirit of the Scythe, use Reverse Death frames (closed eye -> opens into glowing iris)
        if self.is_spirit_of_scythe and self.death_sprite_dir and os.path.exists(self.death_sprite_dir):
            raw_death_for_spawn = AssetManager.get_animation_frames(self.death_sprite_dir)
            if raw_death_for_spawn:
                reversed_spawn = raw_death_for_spawn[::-1]
                scaled_spawn = [
                    pg.transform.scale(f, (int(f.get_width() * final_scale), int(f.get_height() * final_scale)))
                    for f in reversed_spawn
                ]
                self.animations[_GenericNPCState.SPAWN] = scaled_spawn
                self.state_configs[_GenericNPCState.SPAWN] = type(
                    "SC", (), {"animation_speed": frame_duration, "loops": False, "interruptible": False}
                )()
        elif self.spawn_sprite_dir and os.path.exists(self.spawn_sprite_dir):
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
            self.is_walking = False
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
        if self.is_spirit_of_scythe:
            return False  # Spirit of the Scythe is hands-free, no "Talk" prompt or dialogue box
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

        if self.is_spirit_of_scythe and not self.is_trance_active and not self.is_death_complete and not self._interacted:
            if distance <= self.proximity_radius:
                self.is_trance_active = True
                self._trance_phase = 1
                self.is_spawning = True
                self.facing_left = self.rect.centerx > player_rect.centerx
                print(f"[SPIRIT NPC] Trance proximity reached! dist={distance:.0f}px  Eye.x={self.rect.centerx}  Player.x={player_rect.centerx}")
                if _GenericNPCState.SPAWN in self.animations:
                    self.set_state(_GenericNPCState.SPAWN, force=True)
                    print("[SPIRIT NPC] → Playing Reverse Death (Eye Opening) animation")
                else:
                    self.is_spawning = False
                    self._trance_phase = 2
                    self._trance_text_timer = self._trance_text_duration
                    self.set_state(_GenericNPCState.IDLE, force=True)

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

        if self.is_spirit_of_scythe and self.is_trance_active:
            if self._trance_phase == 1:
                # Phase 1: Eye Opening (Reverse Death SPAWN)
                spawn_frames = self.animations.get(_GenericNPCState.SPAWN)
                if spawn_frames and self.animation_index >= len(spawn_frames) - 1:
                    self._trance_phase = 2
                    self._trance_text_timer = self._trance_text_duration
                    self.is_spawning = False
                    self.set_state(_GenericNPCState.IDLE, force=True)
                    print("[SPIRIT NPC] Eye opened → Phase 2: In-world floating text displaying")
            elif self._trance_phase == 2:
                # Phase 2: In-world Floating Text Timer (~3.5s)
                self._trance_text_timer -= delta_seconds
                if self._trance_text_timer <= 0.0:
                    self._trance_phase = 3
                    print("[SPIRIT NPC] Text finished → Phase 3: Eye Closing (Normal Death)")
                    self.trigger_death()
            elif self._trance_phase == 3:
                # Phase 3: Eye Closing (Normal DEATH)
                death_frames = self.animations.get(_GenericNPCState.DEATH)
                if death_frames and self.animation_index >= len(death_frames) - 1:
                    self.is_death_complete = True
                    self.is_trance_active = False
                    self._trance_phase = 0
                    print("[SPIRIT NPC] Eye closed and despawned → Player unlocked")
        else:
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
        if self.is_death_complete and self.play_death_on_interact:
            return

        import math
        ticks = pg.time.get_ticks()

        # ── Dual-Color Pulsing Glow Aura (Spirit of the Scythe only) ─────────
        if self.is_spirit_of_scythe:
            pulse = (math.sin(ticks * 0.008) + 1.0) * 0.5  # 0.0 to 1.0
            if self._trance_phase == 3:
                # Fade out glow alpha during death animation
                death_frames = self.animations.get(_GenericNPCState.DEATH)
                if death_frames:
                    prog = 1.0 - (self.animation_index / max(1, len(death_frames) - 1))
                    glow_alpha = int(220 * max(0.0, prog))
                else:
                    glow_alpha = 0
            else:
                glow_alpha = int(160 + 75 * pulse)

            if glow_alpha > 0 and self.image:
                w, h = self.image.get_width(), self.image.get_height()
                glow_surf = pg.Surface((w + 48, h + 48), pg.SRCALPHA)

                # Outer Character Border Glow (Dark Crimson / Purple)
                outer_r = int(min(w, h) * 0.55 + 6 * pulse)
                pg.draw.circle(glow_surf, (180, 20, 60, int(glow_alpha * 0.40)), (w // 2 + 24, h // 2 + 24), outer_r + 14)

                # Inner Core Object Glow (Flaming Red / Gold)
                inner_r = int(min(w, h) * 0.40 + 4 * pulse)
                pg.draw.circle(glow_surf, (255, 140, 0, int(glow_alpha * 0.65)), (w // 2 + 24, h // 2 + 24), inner_r + 6)
                pg.draw.circle(glow_surf, (255, 40, 20, int(glow_alpha * 0.85)), (w // 2 + 24, h // 2 + 24), inner_r)

                gx = self.rect.centerx - (w + 48) // 2
                gy = self.rect.centery - (h + 48) // 2
                surface.blit(glow_surf, (gx, gy))

        super().draw(surface)

        # ── In-World Floating Dialogue Text (Spirit of the Scythe only) ──────
        if self.is_spirit_of_scythe and self._trance_phase == 2 and self.text:
            # Alpha fade in / fade out
            if self._trance_text_timer > 3.0:
                text_alpha = int(255 * (3.5 - self._trance_text_timer) / 0.5)
            elif self._trance_text_timer < 0.6:
                text_alpha = int(255 * (self._trance_text_timer / 0.6))
            else:
                text_alpha = 255
            text_alpha = max(0, min(255, text_alpha))

            float_y = math.sin(ticks * 0.005) * 4.0

            font = self._font
            max_w = 480
            words = self.text.split(" ")
            lines: list[str] = []
            curr = ""
            for word in words:
                test_l = f"{curr} {word}".strip() if curr else word
                if font.size(test_l)[0] <= max_w:
                    curr = test_l
                else:
                    if curr: lines.append(curr)
                    curr = word
            if curr: lines.append(curr)

            line_h = font.get_linesize() + 2
            total_text_h = len(lines) * line_h
            start_y = self.rect.top - total_text_h - 30 + int(float_y)

            for i, line_str in enumerate(lines):
                tx = self.rect.centerx - font.size(line_str)[0] // 2
                ty = start_y + i * line_h

                # Dark drop shadow
                shd_surf = font.render(line_str, True, (20, 0, 10))
                shd_surf.set_alpha(int(text_alpha * 0.85))
                surface.blit(shd_surf, (tx + 2, ty + 2))

                # Main Ethereal Gold text
                txt_surf = font.render(line_str, True, (255, 220, 90))
                txt_surf.set_alpha(text_alpha)
                surface.blit(txt_surf, (tx, ty))
            return

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
