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
    LAND = 4
    JUMP_START = 5
    JUMP_LOOP = 6


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

        # ── Spirit of the Scythe & Gatekeeper Identification ────────────────────
        self.is_spirit_of_scythe: bool = (
            "spirit of the scythe" in str(self.title).lower() or
            "scythe whispers" in str(self.title).lower() or
            "evil eye beast" in str(self.death_sprite_dir or "").lower() or
            "evil eye beast" in str(sprite_dir).lower()
        )
        self.is_sky_fall_npc: bool = (
            "moonstone_keeper" in str(sprite_dir).lower() or
            "gatekeeper" in str(self.title).lower()
        )
        self.is_trance_active: bool = False
        self._trance_phase: int = 0  # 0: Sky Fly-In Descent, 1: Eye Opening (Reverse Death), 2: Floating Text, 3: Eye Closing
        self._trance_text_timer: float = 0.0
        self._trance_text_duration: float = 8.0  # 8.0 seconds text stays floating (can press ENTER/SPACE to advance)
        self._fly_in_progress: float = 0.0
        self._fly_in_duration: float = 1.0  # 1.0 second smooth sky descent

        self._sky_fall_phase: int = 0  # 0: Waiting, 1: Falling, 2: Landing, 3: Speech (8s), 4: Jump Charge, 5: Sky Launch Out
        self._sky_fall_timer: float = 0.0
        self._sky_fall_text_duration: float = 8.0  # 8 seconds speech focused zoom

        self.visible: bool = not (self.is_spirit_of_scythe or self.is_sky_fall_npc)  # Hidden until player enters proximity!

        # Load animated flame frames for the Eyeball fire border
        self._flame_frames: list[pg.Surface] = []
        self._flame_index: float = 0.0
        if self.is_spirit_of_scythe:
            self.facing_left = False
            flame_dir = "assets/graphics/Fire Effect 2/Explosion2_frames"
            if os.path.exists(flame_dir):
                raw_flames = AssetManager.get_animation_frames(flame_dir)
                if raw_flames:
                    self._flame_frames = [pg.transform.smoothscale(f, (80, 80)) for f in raw_flames]

        # Resolve registry key and margins early to determine scale
        folder_name = os.path.basename(sprite_dir.rstrip("/"))
        if folder_name.lower() in ("idle", "no bg", "with bg"):
            parent_dir = os.path.dirname(sprite_dir.rstrip("/"))
            folder_name = os.path.basename(parent_dir)
            if folder_name.lower() in ("idle", "no bg", "with bg"):
                folder_name = os.path.basename(os.path.dirname(parent_dir))
        sprite_key = f"generic_npc_{folder_name.lower()}"
        margins = HitboxRegistry.get_margins(sprite_key)

        final_scale = scale if scale is not None else margins.scale
        self.scale = final_scale

        # Pre-load LAND, JUMP_START, JUMP_LOOP animation frames for Sky-Fall NPC
        if self.is_sky_fall_npc:
            land_dir = _find_action_folder(sprite_dir, ["land"])
            if land_dir and os.path.exists(land_dir):
                raw_land = AssetManager.get_animation_frames(land_dir)
                if raw_land:
                    self.animations[_GenericNPCState.LAND] = [
                        pg.transform.scale(f, (int(f.get_width() * final_scale), int(f.get_height() * final_scale)))
                        for f in raw_land
                    ]
                    self.state_configs[_GenericNPCState.LAND] = type("SC", (), {"animation_speed": frame_duration, "loops": False, "interruptible": False})()

            js_dir = _find_action_folder(sprite_dir, ["jump start"])
            if js_dir and os.path.exists(js_dir):
                raw_js = AssetManager.get_animation_frames(js_dir)
                if raw_js:
                    self.animations[_GenericNPCState.JUMP_START] = [
                        pg.transform.scale(f, (int(f.get_width() * final_scale), int(f.get_height() * final_scale)))
                        for f in raw_js
                    ]
                    self.state_configs[_GenericNPCState.JUMP_START] = type("SC", (), {"animation_speed": frame_duration, "loops": False, "interruptible": False})()

            jl_dir = _find_action_folder(sprite_dir, ["jump loop"])
            if jl_dir and os.path.exists(jl_dir):
                raw_jl = AssetManager.get_animation_frames(jl_dir)
                if raw_jl:
                    self.animations[_GenericNPCState.JUMP_LOOP] = [
                        pg.transform.scale(f, (int(f.get_width() * final_scale), int(f.get_height() * final_scale)))
                        for f in raw_jl
                    ]
                    self.state_configs[_GenericNPCState.JUMP_LOOP] = type("SC", (), {"animation_speed": frame_duration, "loops": True, "interruptible": False})()

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
        if self.is_spirit_of_scythe or self.is_sky_fall_npc:
            return False  # Hands-free floating dialogue cutscenes
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
        if getattr(self, "_sky_fall_phase", 0) in (1, 5) or getattr(self, "is_death_complete", False):
            curr_bottom = self.rect.bottom
            super().set_state(new_state, force=force)
            frames = self.animations.get(self.state)
            if frames:
                self.image = frames[int(self.animation_index)]
                old_centerx = self.rect.centerx
                self.rect = self.image.get_rect()
                self.rect.centerx = old_centerx
                self.rect.bottom = curr_bottom
            return

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
        if self.is_intro_npc:
            self._trance_phase = 5
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
                self.visible = True
                self._trance_phase = 0  # Phase 0: Sky Fly-In Descent
                self._fly_in_progress = 0.0
                self._target_ground_y = self.rect.centery
                self.rect.centery = -120  # Start off-screen top!
                self.facing_left = False  # Eyeball naturally faces left unflipped
                print(f"[SPIRIT NPC] Trance proximity reached! dist={distance:.0f}px  Eye flying in from top of screen!")

        if self.is_sky_fall_npc and not self.is_trance_active and not self.is_death_complete and not self._interacted:
            if distance <= self.proximity_radius:
                self.is_trance_active = True
                self.visible = True
                self._sky_fall_phase = 1  # Phase 1: Sky Fall Descent
                self._target_ground_y = self.rect.bottom
                self.facing_left = self.rect.centerx > player_rect.centerx
                if _GenericNPCState.JUMP_LOOP in self.animations:
                    self.set_state(_GenericNPCState.JUMP_LOOP, force=True)
                self.rect.bottom = -200  # Start off-screen top!
                print(f"[SKY FALL NPC] Proximity reached! Gatekeeper falling from sky dist={distance:.0f}px")

        if self.is_intro_npc and not self.is_trance_active and not self.is_death_complete and not self._interacted:
            if distance <= self.proximity_radius:
                self.is_trance_active = True
                self.is_walking = False
                self._interacted = True
                self.facing_left = self.rect.centerx > player_rect.centerx
                if _GenericNPCState.SPAWN in self.animations:
                    self._trance_phase = 1
                    self.is_spawning = True
                    self.set_state(_GenericNPCState.SPAWN, force=True)
                    print(f"[INTRO NPC] Proximity reached! dist={distance:.0f}px → Phase 1: SPAWN animation")
                else:
                    self._trance_phase = 2  # Start Camera Zoom-In immediately
                    self.is_spawning = False
                    self.set_state(_GenericNPCState.IDLE, force=True)
                    print(f"[INTRO NPC] Proximity reached! dist={distance:.0f}px → Phase 2: Camera Zoom-In starting")

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
            if self._trance_phase == 0:
                # Phase 0: Sky Fly-In Descent (No Zoom, starts at y = -120, eases down to _target_ground_y)
                self._fly_in_progress += delta_seconds / self._fly_in_duration
                t = min(1.0, max(0.0, self._fly_in_progress))
                ease_t = 1.0 - (1.0 - t) * (1.0 - t)
                start_y = -120
                target_y = getattr(self, "_target_ground_y", 450)
                self.rect.centery = int(start_y + ease_t * (target_y - start_y))

                if self._fly_in_progress >= 1.0:
                    self._trance_phase = 1
                    self.is_spawning = True
                    if _GenericNPCState.SPAWN in self.animations:
                        self.set_state(_GenericNPCState.SPAWN, force=True)
                        print("[SPIRIT NPC] Sky Fly-In complete → Phase 1: Eye Opening (Reverse Death) animation")
                    else:
                        self.is_spawning = False
                        self._trance_phase = 2  # Start Camera Zoom-In
            elif self._trance_phase == 1:
                # Phase 1: Eye Opening (Reverse Death SPAWN, No Zoom)
                spawn_frames = self.animations.get(_GenericNPCState.SPAWN)
                if spawn_frames and self.animation_index >= len(spawn_frames) - 1:
                    self._trance_phase = 2  # Eye opened → Start Phase 2: Camera Zoom-In
                    self.is_spawning = False
                    self.set_state(_GenericNPCState.IDLE, force=True)
                    print("[SPIRIT NPC] Eye opened → Phase 2: Camera Zoom-In starting")
            elif self._trance_phase == 2:
                # Phase 2: Camera Zoom-In (handled by GameState lerp). Once zoomed, GameState sets phase to 3
                pass
            elif self._trance_phase == 3:
                # Phase 3: Dialogue Text Display (~8.0s)
                self._trance_text_timer -= delta_seconds
                if self._trance_text_timer <= 0.0:
                    self._trance_phase = 4  # Text finished → Phase 4: Camera Zoom-Out
                    print("[SPIRIT NPC] Text finished → Phase 4: Camera Zoom-Out starting")
            elif self._trance_phase == 4:
                # Phase 4: Camera Zoom-Out (handled by GameState lerp). Once zoomed out, GameState sets phase to 5
                pass
            elif self._trance_phase == 5:
                # Phase 5: Eye Closing (Normal DEATH)
                death_frames = self.animations.get(_GenericNPCState.DEATH)
                if death_frames and self.animation_index >= len(death_frames) - 1:
                    self.is_death_complete = True
                    self.is_trance_active = False
                    self._trance_phase = 0
                    print("[SPIRIT NPC] Eye closed and despawned → Player unlocked")
        elif self.is_sky_fall_npc and self.is_trance_active:
            if self._sky_fall_phase == 1:
                # Phase 1: Falling down from sky (No Zoom, y = -200 -> _target_ground_y)
                fall_speed = 1300.0  # px/s rapid drop
                self.rect.bottom += int(fall_speed * delta_seconds)
                target_bottom = getattr(self, "_target_ground_y", 609)
                if self.rect.bottom >= target_bottom:
                    self.rect.bottom = target_bottom
                    self._sky_fall_phase = 2
                    if _GenericNPCState.LAND in self.animations:
                        self.set_state(_GenericNPCState.LAND, force=True)
                        print("[SKY FALL NPC] Impact landing on ground → Phase 2: LAND animation")
                    else:
                        self._sky_fall_phase = 3  # Start Camera Zoom-In
            elif self._sky_fall_phase == 2:
                # Phase 2: Impact Landing animation finishes -> Phase 3 Camera Zoom-In
                land_frames = self.animations.get(_GenericNPCState.LAND)
                if not land_frames or self.animation_index >= len(land_frames) - 1.05:
                    self._sky_fall_phase = 3  # Land complete → Phase 3: Camera Zoom-In
                    self.set_state(_GenericNPCState.IDLE, force=True)
                    print("[SKY FALL NPC] Land anim complete → Phase 3: Camera Zoom-In starting")
            elif self._sky_fall_phase == 3:
                # Phase 3: Camera Zoom-In (handled by GameState lerp). Once zoomed, GameState sets phase to 4
                pass
            elif self._sky_fall_phase == 4:
                # Phase 4: Speech timer (8.0s)
                self._sky_fall_timer -= delta_seconds
                if self._sky_fall_timer <= 0.0:
                    self._sky_fall_phase = 5  # Speech finished → Phase 5: Camera Zoom-Out
                    print("[SKY FALL NPC] Speech finished → Phase 5: Camera Zoom-Out starting")
            elif self._sky_fall_phase == 5:
                # Phase 5: Camera Zoom-Out (handled by GameState lerp). Once zoomed out, GameState sets phase to 6
                pass
            elif self._sky_fall_phase == 6:
                # Phase 6: JUMP_START charge anim finishes -> Phase 7 Launch Upward
                js_frames = self.animations.get(_GenericNPCState.JUMP_START)
                if not js_frames or self.animation_index >= len(js_frames) - 1.05:
                    self._sky_fall_phase = 7
                    if _GenericNPCState.JUMP_LOOP in self.animations:
                        self.set_state(_GenericNPCState.JUMP_LOOP, force=True)
                    print("[SKY FALL NPC] Jump start complete → Phase 7: Launching upward into sky")
            elif self._sky_fall_phase == 7:
                # Phase 7: Sky Launch Out (y decreases rapidly -> off-screen top)
                jump_speed = 1400.0  # px/s upward launch
                self.rect.bottom -= int(jump_speed * delta_seconds)
                if self.rect.bottom <= -200:
                    self.rect.bottom = -500
                    self.visible = False
                    self.is_death_complete = True
                    self.is_trance_active = False
                    print("[SKY FALL NPC] Sky launch out complete → Despawned & Player unlocked")
        elif self.is_intro_npc and self.is_trance_active:
            if self._trance_phase == 1:
                # Phase 1: SPAWN animation (No Zoom)
                spawn_frames = self.animations.get(_GenericNPCState.SPAWN)
                if not spawn_frames or self.animation_index >= len(spawn_frames) - 1:
                    self._trance_phase = 2  # Spawn finished → Start Phase 2: Camera Zoom-In
                    self.is_spawning = False
                    self.set_state(_GenericNPCState.IDLE, force=True)
                    print("[INTRO NPC] Spawn anim complete → Phase 2: Camera Zoom-In starting")
            elif self._trance_phase == 2:
                # Phase 2: Camera Zoom-In (handled by GameState lerp). Once zoomed, GameState sets phase to 3
                pass
            elif self._trance_phase == 3:
                # Phase 3: Dialogue Text Display (~8.0s)
                self._trance_text_timer -= delta_seconds
                if self._trance_text_timer <= 0.0:
                    self._trance_phase = 4  # Text finished → Phase 4: Camera Zoom-Out
                    print("[INTRO NPC] Text finished → Phase 4: Camera Zoom-Out starting")
            elif self._trance_phase == 4:
                # Phase 4: Camera Zoom-Out (handled by GameState lerp). Once zoomed out, GameState sets phase to 5
                pass
            elif self._trance_phase == 5:
                # Phase 5: Normal DEATH animation
                death_frames = self.animations.get(_GenericNPCState.DEATH)
                if not death_frames or self.animation_index >= len(death_frames) - 1:
                    self.is_death_complete = True
                    self.is_trance_active = False
                    self._trance_phase = 0
                    print("[INTRO NPC] Death anim complete → Player unlocked & Skeletons unlocked")
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
        if (self.is_spirit_of_scythe or self.is_sky_fall_npc) and not getattr(self, "visible", True):
            return  # Invisible until proximity trigger!

        if self.is_death_complete and self.play_death_on_interact:
            return

        import math
        ticks = pg.time.get_ticks()

        # ── Dual-Color Pulsing Glow Aura & Animated Fire Ring (Spirit only) ──
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
                glow_surf = pg.Surface((w + 64, h + 64), pg.SRCALPHA)

                # Outer Character Border Glow (Dark Crimson / Purple)
                outer_r = int(min(w, h) * 0.55 + 6 * pulse)
                pg.draw.circle(glow_surf, (180, 20, 60, int(glow_alpha * 0.40)), (w // 2 + 32, h // 2 + 32), outer_r + 16)

                # Inner Core Object Glow (Flaming Red / Gold)
                inner_r = int(min(w, h) * 0.40 + 4 * pulse)
                pg.draw.circle(glow_surf, (255, 140, 0, int(glow_alpha * 0.65)), (w // 2 + 32, h // 2 + 32), inner_r + 6)
                pg.draw.circle(glow_surf, (255, 40, 20, int(glow_alpha * 0.85)), (w // 2 + 32, h // 2 + 32), inner_r)

                gx = self.rect.centerx - (w + 64) // 2
                gy = self.rect.centery - (h + 64) // 2
                surface.blit(glow_surf, (gx, gy))

                # ── Animated Eyeball Fire Ring Border ────────────────────────
                if self._flame_frames:
                    self._flame_index += 0.35
                    f_idx = int(self._flame_index) % len(self._flame_frames)
                    flame_img = self._flame_frames[f_idx]
                    flame_alpha = int(glow_alpha * 0.85)

                    # Orbit 6 fire frames around the eyeball perimeter
                    num_flames = 6
                    orbit_r = min(w, h) * 0.60 + 8 * pulse
                    for i in range(num_flames):
                        angle = (ticks * 0.003) + (i * 2.0 * math.pi / num_flames)
                        fx = self.rect.centerx + math.cos(angle) * orbit_r - flame_img.get_width() // 2
                        fy = self.rect.centery + math.sin(angle) * orbit_r - flame_img.get_height() // 2
                        f_copy = flame_img.copy()
                        f_copy.set_alpha(flame_alpha)
                        surface.blit(f_copy, (int(fx), int(fy)))

                # ── Descending Fire Trail during Fly-In (Phase 0) ────────────
                if self._trance_phase == 0 and self._flame_frames:
                    f_idx = int(self._flame_index) % len(self._flame_frames)
                    trail_img = self._flame_frames[f_idx]
                    for trail_i in range(3):
                        ty = self.rect.centery - (trail_i + 1) * 35
                        tx = self.rect.centerx + math.sin(ticks * 0.02 + trail_i) * 12
                        t_copy = trail_img.copy()
                        t_copy.set_alpha(max(0, 200 - trail_i * 60))
                        surface.blit(t_copy, (int(tx - trail_img.get_width() // 2), int(ty - trail_img.get_height() // 2)))

        super().draw(surface)

        # (In-world cutscene dialogue text is rendered on the top-center screen overlay layer in GameState)

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
