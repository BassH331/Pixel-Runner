"""
Demon Time System & The EYE Companion.

Provides the canonical Level 1 narrative companion mechanics & Dark Fantasy Unholy Telepathy theme:
1. Strict Narrative Gating: Unlocked ONLY after player defeats the Blood Zombie boss (Encounter 14)
   and collects The EYE of Andras relic. Default is_unlocked is strictly False.
2. The EYE Familiar: Autonomous hyper-speed celestial hunter hovering at an aerial apex (Y - 180px),
   leaving supersonic neon afterimage trails, locking onto foes with diegetic occult sigils,
   and firing rhythmic heavy void blasts (3/sec, 55 dmg each) before dissolving into void mist.
3. Realistic Time Dilation: Smooth temporal easing (lerping 1.0 -> 0.15 over 0.25s), pre-rendered
   radial gradient lens vignette, ambient cold void desaturation, and suspended floating void motes.
4. Dedicated Activation: Triggered strictly by [V] (Void / Vision) key or controller Select/L3/R3,
   with clean zero-conflict isolation from basic attacks (E, T, Y, RB).
"""

from __future__ import annotations

import math
import os
import random
import sys
import time
from typing import Any, Dict, List, Optional, Tuple
import pygame as pg

from v3x_zulfiqar_gideon import AssetManager


def _safe_hp(entity: Any, default: float = 1.0) -> float:
    """Safely extract float health value guarding against missing attributes or MagicMock objects."""
    if entity is None:
        return 0.0
    for attr in ("_health", "health"):
        val = getattr(entity, attr, None)
        if isinstance(val, (int, float)):
            return float(val)
    return default


class VoidBallProjectile(pg.sprite.Sprite):
    """Demonic projectile fired by The EYE during Demon Time."""

    def __init__(
        self,
        x: float,
        y: float,
        target_x: float,
        target_y: float,
        damage: float = 55.0,
        speed: float = 22.0,
    ) -> None:
        super().__init__()
        self.x = float(x)
        self.y = float(y)
        self.damage = damage
        self.speed = speed
        self.is_projectile = True
        self.is_friendly = True

        # Calculate normalized velocity vector toward target
        dx = target_x - x
        dy = target_y - y
        dist = math.hypot(dx, dy)
        if dist > 0:
            self.vx = (dx / dist) * speed
            self.vy = (dy / dist) * speed
        else:
            self.vx = speed
            self.vy = 0.0

        # Motion trail history for plasma comet tail
        self._trail: List[Tuple[float, float, float]] = []

        # Load projectile & destruction frames
        self._fly_frames: List[pg.Surface] = []
        self._destroy_frames: List[pg.Surface] = []
        self._load_frames()

        self._frame_idx: int = 0
        self._anim_timer: float = 0.0
        self._is_destroying: bool = False
        self._destroy_idx: int = 0

        self.image = (
            self._fly_frames[0]
            if self._fly_frames
            else self._create_fallback_surf()
        )
        self.rect = self.image.get_rect(center=(int(self.x), int(self.y)))

    def _load_frames(self) -> None:
        proj_dir = os.path.join(
            "assets", "graphics", "Evil Eye Beast For Itch", "Void Ball Projectilep"
        )
        has_display = pg.display.get_surface() is not None
        if os.path.exists(proj_dir):
            for i in range(1, 4):
                p_path = os.path.join(proj_dir, f"Void Ball Projectile{i}.png")
                if os.path.exists(p_path):
                    try:
                        img = pg.image.load(p_path)
                        if has_display:
                            img = img.convert_alpha()
                        self._fly_frames.append(pg.transform.smoothscale(img, (44, 44)))
                    except Exception:
                        pass

            for i in range(1, 4):
                d_path = os.path.join(proj_dir, f"Projectile Destroyed{i}.png")
                if os.path.exists(d_path):
                    try:
                        img = pg.image.load(d_path)
                        if has_display:
                            img = img.convert_alpha()
                        self._destroy_frames.append(pg.transform.smoothscale(img, (52, 52)))
                    except Exception:
                        pass

    def _create_fallback_surf(self) -> pg.Surface:
        surf = pg.Surface((34, 34), pg.SRCALPHA)
        pg.draw.circle(surf, (170, 70, 240), (17, 17), 15)
        pg.draw.circle(surf, (230, 200, 255), (17, 17), 8)
        pg.draw.circle(surf, (255, 255, 255), (17, 17), 4)
        return surf

    def update(self, dt: float = 1.0 / 60.0, scroll_speed: float = 0.0) -> None:
        if self._is_destroying:
            self._anim_timer += dt
            if self._anim_timer >= 0.06:
                self._anim_timer = 0.0
                self._destroy_idx += 1
                if self._destroy_idx < len(self._destroy_frames):
                    self.image = self._destroy_frames[self._destroy_idx]
                else:
                    self.kill()
            return

        # Record trail position
        self._trail.append((self.x, self.y, 12.0))
        if len(self._trail) > 7:
            self._trail.pop(0)

        # Advance position at high speed
        self.x += self.vx * (dt * 60.0)
        self.y += self.vy * (dt * 60.0)
        self.rect.center = (int(self.x), int(self.y))

        # Projectile animation
        if self._fly_frames:
            self._anim_timer += dt
            if self._anim_timer >= 0.06:
                self._anim_timer = 0.0
                self._frame_idx = (self._frame_idx + 1) % len(self._fly_frames)
                self.image = self._fly_frames[self._frame_idx]

        # Despawn if out of play boundary
        if self.x < -200 or self.x > 3000 or self.y < -200 or self.y > 1000:
            self.kill()

    def draw(self, surface: pg.Surface, camera_x: float = 0.0) -> None:
        """Draw projectile with smooth soft-glowing plasma comet trail."""
        for idx, (tx, ty, rad) in enumerate(self._trail):
            ratio = (idx + 1) / max(1, len(self._trail))
            trail_r = max(1, int(rad * ratio * 0.55))
            sx = int(tx - camera_x)
            sy = int(ty)
            alpha = int(120 * ratio)
            trail_surf = pg.Surface((trail_r * 2 + 2, trail_r * 2 + 2), pg.SRCALPHA)
            pg.draw.circle(trail_surf, (180, 70, 245, alpha), (trail_r + 1, trail_r + 1), trail_r)
            surface.blit(trail_surf, (sx - trail_r, sy - trail_r))

        screen_x = int(self.rect.x - camera_x)
        surface.blit(self.image, (screen_x, self.rect.y))

    def explode(self) -> None:
        """Trigger impact explosion animation."""
        if not self._is_destroying:
            self._is_destroying = True
            self._anim_timer = 0.0
            self._destroy_idx = 0
            if self._destroy_frames:
                self.image = self._destroy_frames[0]
            else:
                self.kill()


class DemonEyeCompanion:
    """
    The EYE familiar companion.
    
    During Demon Time, operates as an elevated aerial telepathic sentinel:
    - Hovers at an aerial apex (Y - 180px above targets), raining down diagonal void strikes.
    - Moves with supersonic snappy kinematics and ethereal violet afterimage motion trails.
    - Marks targets with an occult diegetic eye sigil (no gaudy neon arcade boxes).
    - Rapid-fires rhythmic heavy void pulses (~3.1/s, 55 dmg each) that shatter guards and stagger foes.
    - If no enemies exist on screen, patrols around the player in a celestial surveillance orbit.
    """

    STATE_INACTIVE = "inactive"
    STATE_APPEARING = "appearing"
    STATE_IDLE = "idle"
    STATE_ATTACKING = "attacking"
    STATE_DISAPPEARING = "disappearing"

    def __init__(self) -> None:
        self.state: str = self.STATE_INACTIVE
        self.x: float = 0.0
        self.y: float = 0.0
        self.vx: float = 0.0
        self.vy: float = 0.0
        self.facing_right: bool = True
        self.is_overdrive: bool = False

        # Target tracking for telepathic laser lock
        self.current_target: Optional[Any] = None
        self.target_pos: Tuple[float, float] = (0.0, 0.0)

        # Animation frames
        self._anim_frames: Dict[str, List[pg.Surface]] = {
            "appearing": [],
            "idle": [],
            "attack": [],
            "disappearing": [],
        }
        self._frame_idx: int = 0
        self._anim_timer: float = 0.0
        self._float_time: float = 0.0

        # Rhythmic strike cadence: ~3.1 shots/sec (every 0.32s) for heavy deliberate impact
        self._auto_fire_timer: float = 0.0
        self._auto_fire_interval: float = 0.32

        # Supersonic afterimages buffer: list of dicts with x, y, surf, alpha, facing_right
        self._afterimages: List[Dict[str, Any]] = []
        self._afterimage_timer: float = 0.0

        # Audio manager reference
        self.audio_manager: Optional[Any] = None

        self._load_animations()

    def _load_animations(self) -> None:
        base_dir = os.path.join("assets", "graphics", "Evil Eye Beast For Itch")
        scale = 1.35
        has_display = pg.display.get_surface() is not None

        def _load_folder(folder: str, prefix: str, count: int) -> List[pg.Surface]:
            frames = []
            f_dir = os.path.join(base_dir, folder)
            if os.path.exists(f_dir):
                for i in range(1, count + 1):
                    p = os.path.join(f_dir, f"{prefix}{i}.png")
                    if os.path.exists(p):
                        try:
                            img = pg.image.load(p)
                            if has_display:
                                img = img.convert_alpha()
                            w = int(img.get_width() * scale)
                            h = int(img.get_height() * scale)
                            frames.append(pg.transform.smoothscale(img, (w, h)))
                        except Exception:
                            pass
            return frames

        self._anim_frames["appearing"] = _load_folder("Movement", "Eye Beast Moving", 13)
        self._anim_frames["idle"] = _load_folder("Idle", "Eye Beast Idle", 20)
        self._anim_frames["attack"] = _load_folder("Attack", "Eye Beast Attack", 13)
        self._anim_frames["disappearing"] = _load_folder("Death", "Eye Beast Death", 15)

        # Procedural fallback if frames are missing
        for key in ("appearing", "idle", "attack", "disappearing"):
            if not self._anim_frames[key]:
                self._anim_frames[key] = [self._create_fallback_avatar(scale)]

    def _create_fallback_avatar(self, scale: float = 1.35) -> pg.Surface:
        surf = pg.Surface((int(54 * scale), int(54 * scale)), pg.SRCALPHA)
        center = (surf.get_width() // 2, surf.get_height() // 2)
        r = int(22 * scale)
        pg.draw.circle(surf, (130, 40, 210), center, r)
        pg.draw.circle(surf, (220, 200, 245), center, int(14 * scale))
        pg.draw.circle(surf, (70, 15, 120), center, int(8 * scale))
        pg.draw.circle(surf, (255, 255, 255), (center[0] - int(3 * scale), center[1] - int(3 * scale)), int(3 * scale))
        return surf

    def summon(self, player_x: float, player_y: float) -> None:
        """Manifest The EYE beside the player in supersonic overdrive mode."""
        self.state = self.STATE_APPEARING
        self.is_overdrive = True
        self.x = player_x - 50.0
        self.y = player_y - 70.0
        self.vx = 0.0
        self.vy = 0.0
        self._frame_idx = 0
        self._anim_timer = 0.0
        self._float_time = 0.0
        self._auto_fire_timer = 0.10  # Initial quick pulse
        self._afterimages.clear()
        self.current_target = None

    def trigger_attack(self) -> None:
        """Trigger Void Ball casting attack animation at hyper-speed."""
        if self.state in (self.STATE_IDLE, self.STATE_APPEARING, self.STATE_ATTACKING):
            self.state = self.STATE_ATTACKING
            self._frame_idx = 0
            self._anim_timer = 0.0

    def dismiss(self) -> None:
        """Begin dissolving disappearance animation."""
        if self.state != self.STATE_INACTIVE:
            self.state = self.STATE_DISAPPEARING
            self.is_overdrive = False
            self.current_target = None
            self._frame_idx = 0
            self._anim_timer = 0.0

    def _find_best_target(self, enemies: Optional[List[Any]], boss: Optional[Any]) -> Optional[Any]:
        """Locate the highest-priority live on-screen enemy."""
        # 1. Boss takes high priority if on-screen and alive
        if boss and hasattr(boss, "rect"):
            is_alive = getattr(boss, "alive", lambda: True)() if callable(getattr(boss, "alive", None)) else getattr(boss, "alive", True)
            boss_hp = _safe_hp(boss, 1.0)
            if is_alive and boss_hp > 0 and -100 <= boss.rect.centerx <= 1380:
                return boss

        # 2. Nearest live enemy on screen
        best_enemy = None
        best_dist = float("inf")

        if enemies:
            for enemy in enemies:
                if not hasattr(enemy, "rect"):
                    continue
                is_alive = getattr(enemy, "alive", lambda: True)() if callable(getattr(enemy, "alive", None)) else getattr(enemy, "alive", True)
                if not is_alive or getattr(enemy, "is_dead", False):
                    continue
                hp = _safe_hp(enemy, 1.0)
                if hp <= 0:
                    continue

                if -120 <= enemy.rect.centerx <= 1400:
                    dist = math.hypot(enemy.rect.centerx - self.x, enemy.rect.centery - self.y)
                    if dist < best_dist:
                        best_dist = dist
                        best_enemy = enemy

        return best_enemy

    def update(
        self,
        dt: float,
        player_x: float,
        player_y: float,
        facing_right: bool = True,
        enemies: Optional[List[Any]] = None,
        boss: Optional[Any] = None,
        projectiles_group: Optional[pg.sprite.Group] = None,
    ) -> None:
        if self.state == self.STATE_INACTIVE:
            return

        self._float_time += dt
        overdrive_speed_multiplier = 2.4 if self.is_overdrive else 1.0

        # ── 1. Target Acquisition & Elevated Apex Kinematics ─────────────────────
        if self.is_overdrive:
            target = self._find_best_target(enemies, boss)
            self.current_target = target

            if target and hasattr(target, "rect"):
                t_rect = target.rect
                self.target_pos = (float(t_rect.centerx), float(t_rect.centery))

                # Elevated apex positioning: hovers 170px to the flank and 180px elevated above target
                offset_x = -170.0 if t_rect.centerx >= self.x else 170.0
                dest_x = max(80.0, min(1200.0, t_rect.centerx + offset_x))
                dest_y = max(80.0, min(440.0, t_rect.centery - 180.0 + math.sin(self._float_time * 5.0) * 8.0))

                # Snappy supersonic motion
                dist_x = dest_x - self.x
                dist_y = dest_y - self.y
                move_factor = min(1.0, dt * 14.0 * overdrive_speed_multiplier)
                self.x += dist_x * move_factor
                self.y += dist_y * move_factor

                # Faces toward the target
                self.facing_right = (t_rect.centerx >= self.x)

                # ── Rhythmic Heavy Strike Cadence ─────────────────────────────
                self._auto_fire_timer -= dt * overdrive_speed_multiplier
                if self._auto_fire_timer <= 0.0 and projectiles_group is not None:
                    self._auto_fire_timer = self._auto_fire_interval
                    self.trigger_attack()

                    pupil_ox = 30.0 if self.facing_right else -30.0
                    proj = VoidBallProjectile(
                        x=self.x + pupil_ox,
                        y=self.y + 12.0,
                        target_x=float(t_rect.centerx),
                        target_y=float(t_rect.centery),
                        damage=55.0,
                        speed=22.0,
                    )
                    projectiles_group.add(proj)

                    if self.audio_manager:
                        try:
                            self.audio_manager.play_sound("magic_sfx")
                        except Exception:
                            pass
            else:
                # No live enemies in sight: celestial surveillance orbit around player
                orbit_radius_x = 120.0
                orbit_radius_y = 55.0
                orbit_speed = 4.8
                orbit_angle = self._float_time * orbit_speed
                dest_x = player_x + math.cos(orbit_angle) * orbit_radius_x
                dest_y = (player_y - 45.0) + math.sin(orbit_angle) * orbit_radius_y

                move_factor = min(1.0, dt * 11.0 * overdrive_speed_multiplier)
                self.x += (dest_x - self.x) * move_factor
                self.y += (dest_y - self.y) * move_factor
                self.facing_right = (math.cos(orbit_angle + 0.1) >= 0)
        else:
            self.facing_right = facing_right
            target_offset_x = -45.0 if facing_right else 45.0
            dest_x = player_x + target_offset_x
            dest_y = (player_y - 20.0) + math.sin(self._float_time * 3.5) * 4.0
            self.x += (dest_x - self.x) * min(1.0, dt * 10.0)
            self.y += (dest_y - self.y) * min(1.0, dt * 10.0)

        # ── 2. Supersonic Neon Afterimages ──────────────────────────────────────
        if self.is_overdrive:
            self._afterimage_timer += dt
            if self._afterimage_timer >= 0.04:
                self._afterimage_timer = 0.0
                frame = self._get_current_frame()
                if frame:
                    self._afterimages.append({
                        "x": self.x,
                        "y": self.y,
                        "surf": frame,
                        "alpha": 170,
                        "facing_right": self.facing_right,
                    })

        for img_data in self._afterimages:
            img_data["alpha"] = max(0, img_data["alpha"] - int(dt * 650))
        self._afterimages = [img for img in self._afterimages if img["alpha"] > 0]

        # ── 3. Animation State Updates ──────────────────────────────────────────
        self._anim_timer += dt
        frame_speed = 0.04 if self.is_overdrive else 0.06

        if self.state == self.STATE_APPEARING:
            frames = self._anim_frames["appearing"]
            if frames and self._anim_timer >= frame_speed:
                self._anim_timer = 0.0
                self._frame_idx += 1
                if self._frame_idx >= len(frames):
                    self.state = self.STATE_IDLE
                    self._frame_idx = 0

        elif self.state == self.STATE_IDLE:
            frames = self._anim_frames["idle"]
            if frames and self._anim_timer >= frame_speed:
                self._anim_timer = 0.0
                self._frame_idx = (self._frame_idx + 1) % len(frames)

        elif self.state == self.STATE_ATTACKING:
            frames = self._anim_frames["attack"]
            if frames and self._anim_timer >= frame_speed:
                self._anim_timer = 0.0
                self._frame_idx += 1
                if self._frame_idx >= len(frames):
                    self.state = self.STATE_IDLE
                    self._frame_idx = 0

        elif self.state == self.STATE_DISAPPEARING:
            frames = self._anim_frames["disappearing"]
            if frames and self._anim_timer >= frame_speed:
                self._anim_timer = 0.0
                self._frame_idx += 1
                if self._frame_idx >= len(frames):
                    self.state = self.STATE_INACTIVE
                    self._frame_idx = 0

    def _get_current_frame(self) -> Optional[pg.Surface]:
        frame_key = {
            self.STATE_APPEARING: "appearing",
            self.STATE_IDLE: "idle",
            self.STATE_ATTACKING: "attack",
            self.STATE_DISAPPEARING: "disappearing",
        }.get(self.state, "idle")

        frames = self._anim_frames.get(frame_key, [])
        if not frames:
            return None
        idx = min(self._frame_idx, len(frames) - 1)
        return frames[idx]

    def draw(self, surface: pg.Surface, camera_x: float = 0.0) -> None:
        if self.state == self.STATE_INACTIVE:
            return

        raw_frame = self._get_current_frame()
        if not raw_frame:
            return

        # ── 1. Diegetic Occult Sigil & Crackling Psychic Arc ────────────────────
        if self.is_overdrive and self.current_target and hasattr(self.current_target, "rect"):
            t_rect = self.current_target.rect
            pupil_screen_x = int((self.x + (25 if self.facing_right else -25)) - camera_x)
            pupil_screen_y = int(self.y + 14)
            target_screen_x = int(t_rect.centerx - camera_x)
            target_screen_y = int(t_rect.centery)

            # Slender psychic laser sight line
            pg.draw.line(surface, (140, 40, 230), (pupil_screen_x, pupil_screen_y), (target_screen_x, target_screen_y), 3)
            pg.draw.line(surface, (230, 210, 255), (pupil_screen_x, pupil_screen_y), (target_screen_x, target_screen_y), 1)

            # Ethereal energy packet speeding down beam
            pulse_progress = (self._float_time * 6.5) % 1.0
            pulse_x = int(pupil_screen_x + (target_screen_x - pupil_screen_x) * pulse_progress)
            pulse_y = int(pupil_screen_y + (target_screen_y - pupil_screen_y) * pulse_progress)
            pg.draw.circle(surface, (255, 255, 255), (pulse_x, pulse_y), 4)
            pg.draw.circle(surface, (180, 70, 245), (pulse_x, pulse_y), 7, 1)

            # Diegetic Occult Eye Sigil hovering above the enemy's head
            sigil_cx = target_screen_x
            sigil_cy = int(t_rect.top - 20 + math.sin(self._float_time * 6.0) * 3.0)
            pg.draw.circle(surface, (190, 80, 255), (sigil_cx, sigil_cy), 8, 1)
            pg.draw.circle(surface, (240, 210, 255), (sigil_cx, sigil_cy), 3)
            pg.draw.line(surface, (190, 80, 255), (sigil_cx - 12, sigil_cy), (sigil_cx + 12, sigil_cy), 1)
            pg.draw.line(surface, (190, 80, 255), (sigil_cx, sigil_cy - 10), (sigil_cx, sigil_cy + 10), 1)

        # ── 2. Supersonic Neon Afterimages ──────────────────────────────────────
        for after in self._afterimages:
            asurf = after["surf"]
            if after["facing_right"]:
                asurf = pg.transform.flip(asurf, True, False)
            tinted = asurf.copy()
            tint_overlay = pg.Surface(tinted.get_size(), pg.SRCALPHA)
            tint_overlay.fill((160, 45, 245, after["alpha"]))
            tinted.blit(tint_overlay, (0, 0), special_flags=pg.BLEND_RGBA_MULT)
            tinted.set_alpha(after["alpha"])
            surface.blit(tinted, (int(after["x"] - camera_x), int(after["y"])))

        # ── 3. Main Companion Frame & Demonic Halo ──────────────────────────────
        frame = raw_frame if not self.facing_right else pg.transform.flip(raw_frame, True, False)

        glow_surf = frame.copy()
        tint = pg.Surface(glow_surf.get_size(), pg.SRCALPHA)
        tint.fill((170, 70, 255, 130 if self.is_overdrive else 80))
        glow_surf.blit(tint, (0, 0), special_flags=pg.BLEND_RGBA_MULT)

        screen_x = int(self.x - camera_x)
        screen_y = int(self.y)

        # Soft outer purple halo
        halo_r = int((frame.get_width() // 2 + 10) + math.sin(self._float_time * 6.0) * 3.0)
        halo_surf = pg.Surface((halo_r * 2 + 10, halo_r * 2 + 10), pg.SRCALPHA)
        center = (halo_surf.get_width() // 2, halo_surf.get_height() // 2)
        pg.draw.circle(halo_surf, (140, 35, 240, 75 if self.is_overdrive else 45), center, halo_r)
        pg.draw.circle(halo_surf, (210, 150, 255, 110 if self.is_overdrive else 60), center, halo_r // 2)
        surface.blit(halo_surf, (screen_x + frame.get_width() // 2 - center[0], screen_y + frame.get_height() // 2 - center[1]))

        surface.blit(glow_surf, (screen_x, screen_y))


class DemonTimeSystem:
    """
    Orchestrates bullet-time Demon Time, companion summoning, and autonomous void blasting.
    
    Strict Invariants:
    - Narrative Gating: Locked by default (is_unlocked = False); unlocks strictly after Blood Zombie defeat.
    - Time Dilation: Smooth temporal easing ramps time down to 0.15x for enemies and background scrolling.
    - Pre-rendered Radial Vignette: Smooth optical quadratic falloff (no harsh box frames).
    - Ambient Cold Void Color Grading: Mutes saturation using BLEND_MULT into an unholy twilight trance.
    - Activation: Dedicated conflict-free [V] key or gamepad Select/L3/R3.
    """

    def __init__(self) -> None:
        # STRICT Narrative Gating: Never unlock on startup/dev; strictly earned via Blood Zombie relic drop
        self.is_unlocked: bool = False
        self.is_active: bool = False

        # Smooth temporal easing
        self.current_time_scale: float = 1.0
        self.target_time_scale: float = 1.0
        self.time_scale: float = 0.15
        self.world_time_scale: float = 0.15

        self.duration_total: float = 5.5
        self.duration_remaining: float = 0.0
        self.cooldown_total: float = 16.0
        self.cooldown_remaining: float = 0.0

        # Stats tracking
        self.targets_purged: int = 0
        self._time_elapsed: float = 0.0

        # QTE manual bonus strike prompt
        self.qte_available: bool = False
        self.qte_prompt_text: str = "[SPACE / V] VOID BARRAGE"

        # Subsystems
        self.companion = DemonEyeCompanion()
        self.projectiles: pg.sprite.Group = pg.sprite.Group()
        self.audio_manager: Optional[Any] = None

        # Pre-rendered visual effect surfaces
        self._vignette_surf: Optional[pg.Surface] = None
        self._ambient_tint_surf: Optional[pg.Surface] = None

        # Suspended floating void motes
        self._void_motes: List[Dict[str, float]] = []
        self._init_void_motes()

    def _init_void_motes(self) -> None:
        """Initialize 16 suspended void dust particles that hang frozen in mid-air."""
        self._void_motes.clear()
        for _ in range(16):
            self._void_motes.append({
                "x": random.uniform(20.0, 1260.0),
                "y": random.uniform(40.0, 680.0),
                "radius": random.uniform(1.2, 3.2),
                "alpha": random.uniform(90.0, 200.0),
                "drift_speed": random.uniform(0.1, 0.4),
            })

    def _get_radial_vignette(self, width: int = 1280, height: int = 720) -> pg.Surface:
        """Generate smooth radial optical gradient vignette once to preserve 60 FPS."""
        if self._vignette_surf is not None and self._vignette_surf.get_size() == (width, height):
            return self._vignette_surf

        vignette = pg.Surface((width, height), pg.SRCALPHA)
        center_x, center_y = width // 2, height // 2
        max_dist = math.hypot(center_x, center_y)

        # Draw concentric rings with quadratic falloff
        for r in range(int(max_dist), 0, -4):
            ratio = (r / max_dist) ** 2
            alpha = int(220 * ratio)
            alpha = max(0, min(220, alpha))
            if alpha > 0:
                pg.draw.circle(vignette, (12, 5, 24, alpha), (center_x, center_y), r)

        self._vignette_surf = vignette
        return self._vignette_surf

    def _get_ambient_tint(self, width: int = 1280, height: int = 720) -> pg.Surface:
        """Generate cold twilight desaturation surface for subtle BLEND_MULT grading."""
        if self._ambient_tint_surf is not None and self._ambient_tint_surf.get_size() == (width, height):
            return self._ambient_tint_surf

        tint = pg.Surface((width, height))
        tint.fill((190, 180, 225))
        self._ambient_tint_surf = tint
        return self._ambient_tint_surf

    def unlock(self) -> None:
        """Call when The EYE of Andras relic is collected from Blood Zombie."""
        self.is_unlocked = True

    def activate(
        self,
        duration: float = 5.5,
        time_scale: float = 0.15,
        player_x: float = 0.0,
        player_y: float = 0.0,
    ) -> bool:
        """Activate Demon Time slow-motion mode and summon The EYE in autonomous overdrive."""
        if not self.is_unlocked:
            return False
        if self.is_active or self.cooldown_remaining > 0.0:
            return False

        self.is_active = True
        self.time_scale = time_scale
        self.world_time_scale = time_scale
        self.target_time_scale = time_scale
        self.current_time_scale = time_scale
        self.duration_total = duration
        self.duration_remaining = duration
        self.qte_available = True
        self.targets_purged = 0

        self.companion.audio_manager = self.audio_manager
        self.companion.summon(player_x, player_y)

        if self.audio_manager:
            try:
                self.audio_manager.play_sound("aura_effect")
                self.audio_manager.play_sound("bells")
            except Exception:
                pass

        return True

    def handle_input(
        self,
        event: pg.event.Event,
        player_x: float,
        player_y: float,
        target_x: float,
        target_y: float,
    ) -> bool:
        """
        Handle player hotkeys for Demon Time and manual Void Strikes.
        
        Strictly triggers on dedicated [V] key or gamepad Select/L3/R3.
        NEVER triggers on core attack keys (E, T, Y, RB).
        """
        if not self.is_unlocked:
            return False

        # 1. Manual Bonus Void Strike during Demon Time
        if self.is_active:
            trigger_shot = False
            if event.type == pg.KEYDOWN and event.key in (pg.K_SPACE, pg.K_a, pg.K_f):
                trigger_shot = True
            elif event.type == pg.JOYBUTTONDOWN and event.button in (0, 2):  # A or X
                trigger_shot = True

            if trigger_shot:
                self.qte_available = False
                self.companion.trigger_attack()
                proj = VoidBallProjectile(
                    x=self.companion.x + (30.0 if self.companion.facing_right else -30.0),
                    y=self.companion.y + 12.0,
                    target_x=target_x,
                    target_y=target_y,
                    damage=65.0,
                    speed=26.0,
                )
                self.projectiles.add(proj)
                if self.audio_manager:
                    try:
                        self.audio_manager.play_sound("magic_sfx")
                    except Exception:
                        pass
                return True

        # 2. Dedicated [V] Key Demon Time Activation
        if not self.is_active and self.cooldown_remaining <= 0.0:
            activate_req = False
            if event.type == pg.KEYDOWN and event.key == pg.K_v:
                activate_req = True
            elif event.type == pg.JOYBUTTONDOWN and event.button in (8, 10, 11):  # Select, L3, R3
                activate_req = True

            if activate_req:
                return self.activate(player_x=player_x, player_y=player_y)

        return False

    def update(
        self,
        dt: float,
        player_x: float,
        player_y: float,
        facing_right: bool = True,
        enemies: Optional[List[Any]] = None,
        boss: Optional[Any] = None,
    ) -> None:
        """Update Demon Time timers, temporal easing, companion hunting, and projectile collisions."""
        self._time_elapsed += dt

        # Smooth temporal easing: lerp current_time_scale toward target
        lerp_target = self.target_time_scale if self.is_active else 1.0
        self.current_time_scale += (lerp_target - self.current_time_scale) * min(1.0, dt * 8.0)

        # Update cooldown
        if self.cooldown_remaining > 0.0:
            self.cooldown_remaining = max(0.0, self.cooldown_remaining - dt)

        # Update active Demon Time
        if self.is_active:
            self.duration_remaining -= dt
            if self.duration_remaining <= 0.0:
                self.is_active = False
                self.target_time_scale = 1.0
                self.cooldown_remaining = self.cooldown_total
                self.companion.dismiss()

        # Update suspended void motes drift
        if self.is_active:
            for mote in self._void_motes:
                mote["y"] -= mote["drift_speed"] * (dt * 60.0)
                if mote["y"] < 20.0:
                    mote["y"] = 700.0
                    mote["x"] = random.uniform(20.0, 1260.0)

        # Update companion familiar position, targeting AI & animations
        self.companion.update(
            dt,
            player_x,
            player_y,
            facing_right,
            enemies=enemies if self.is_active else None,
            boss=boss if self.is_active else None,
            projectiles_group=self.projectiles if self.is_active else None,
        )

        # Update projectiles
        self.projectiles.update(dt)

        # Check projectile hit collisions with enemies & boss
        for proj in list(self.projectiles):
            if getattr(proj, "_is_destroying", False):
                continue

            hit = False

            # Check boss collision
            if boss and hasattr(boss, "rect") and getattr(boss, "alive", lambda: True)():
                if proj.rect.colliderect(boss.rect):
                    hit = True
                    if hasattr(boss, "take_damage"):
                        boss.take_damage(proj.damage)
                    elif hasattr(boss, "health"):
                        boss.health = max(0.0, boss.health - proj.damage)
                    proj.explode()
                    if _safe_hp(boss, 1.0) <= 0:
                        self.targets_purged += 1
                    continue

            # Check regular enemy collision
            if enemies and not hit:
                for enemy in enemies:
                    if hasattr(enemy, "rect") and getattr(enemy, "alive", lambda: True)():
                        if proj.rect.colliderect(enemy.rect):
                            hit = True
                            prev_hp = _safe_hp(enemy, 1.0)
                            if hasattr(enemy, "take_damage"):
                                enemy.take_damage(proj.damage)
                            elif hasattr(enemy, "health"):
                                enemy.health = max(0.0, enemy.health - proj.damage)
                            proj.explode()

                            new_hp = _safe_hp(enemy, 0.0)
                            if prev_hp > 0 and new_hp <= 0:
                                self.targets_purged += 1
                            break

    def get_enemy_time_scale(self) -> float:
        """Return smoothed delta-time scale factor for enemies and combat physics."""
        return self.current_time_scale if self.is_active else 1.0

    def get_world_time_scale(self) -> float:
        """Return smoothed delta-time scale factor for background scrolling & environment."""
        return self.current_time_scale if self.is_active else 1.0

    def get_player_time_scale(self) -> float:
        """Player remains agile to dodge while enemies crawl in slow motion."""
        return 1.0

    def draw(self, surface: pg.Surface, camera_x: float = 0.0) -> None:
        """Draw companion familiar and projectiles."""
        self.companion.draw(surface, camera_x)
        for proj in self.projectiles:
            if hasattr(proj, "draw"):
                proj.draw(surface, camera_x)
            else:
                screen_x = int(proj.rect.x - camera_x)
                surface.blit(proj.image, (screen_x, proj.rect.y))

    def draw_overlay(self, surface: pg.Surface, enemies: Optional[List[Any]] = None, boss: Optional[Any] = None) -> None:
        """
        Draw Dark Fantasy Telepathy HUD:
        - When active: Optical radial gradient vignette, ambient cold void tint, suspended void motes, and sleek status gauge.
        - When inactive: Unobtrusive [V] DEMON TIME [READY] prompt or cooldown meter.
        """
        w, h = surface.get_size()

        if self.is_active:
            # ── 1. Ambient Cold Void Desaturation Tint ───────────────────────────
            tint_surf = self._get_ambient_tint(w, h)
            surface.blit(tint_surf, (0, 0), special_flags=pg.BLEND_MULT)

            # ── 2. Pre-rendered Optical Radial Gradient Lens Vignette ─────────────
            vignette = self._get_radial_vignette(w, h)
            intensity = min(1.0, (1.0 - self.current_time_scale) / (1.0 - self.time_scale + 0.001))
            vignette.set_alpha(int(220 * intensity))
            surface.blit(vignette, (0, 0))

            # ── 3. Suspended Floating Arcane Motes ─────────────────────────────────
            for mote in self._void_motes:
                mx, my = int(mote["x"]), int(mote["y"])
                m_rad = int(mote["radius"])
                alpha = int(mote["alpha"] * intensity)
                mote_surf = pg.Surface((m_rad * 2 + 2, m_rad * 2 + 2), pg.SRCALPHA)
                pg.draw.circle(mote_surf, (210, 180, 255, alpha), (m_rad + 1, m_rad + 1), m_rad)
                surface.blit(mote_surf, (mx - m_rad, my - m_rad))

            # ── 4. Sleek Minimalist Top Stasis Banner ──────────────────────────────
            banner_w, banner_h = 380, 36
            banner_x = (w - banner_w) // 2
            banner_y = 16
            banner_rect = pg.Rect(banner_x, banner_y, banner_w, banner_h)
            pg.draw.rect(surface, (14, 6, 26, 220), banner_rect, border_radius=6)
            pg.draw.rect(surface, (170, 70, 240), banner_rect, width=1, border_radius=6)

            # Slender 3px void purple gauge line
            ratio = max(0.0, min(1.0, self.duration_remaining / max(0.01, self.duration_total)))
            fill_w = int((banner_w - 8) * ratio)
            if fill_w > 0:
                pg.draw.rect(
                    surface,
                    (210, 90, 255),
                    (banner_x + 4, banner_y + banner_h - 5, fill_w, 3),
                    border_radius=1,
                )

            font_title = AssetManager.get_font(None, 18)
            overdrive_title = f"SEAL OF ANDRAS // TEMPORAL STASIS  [{self.duration_remaining:.1f}s]"
            t_surf = font_title.render(overdrive_title, True, (240, 220, 255))
            surface.blit(
                t_surf,
                (
                    banner_x + (banner_w - t_surf.get_width()) // 2,
                    banner_y + 4,
                ),
            )

            font_micro = AssetManager.get_font(None, 13)
            telemetry_tag = f"DILATION: {self.current_time_scale:.2f}x  //  PURGED: {self.targets_purged}"
            sub_surf = font_micro.render(telemetry_tag, True, (180, 140, 235))
            surface.blit(
                sub_surf,
                (
                    banner_x + (banner_w - sub_surf.get_width()) // 2,
                    banner_y + 19,
                ),
            )

        else:
            # ── 5. Inactive State: Unobtrusive Ready / Cooldown HUD Badge ──────────
            if self.is_unlocked:
                font_hud = AssetManager.get_font(None, 16)
                badge_x = 24
                badge_y = h - 46

                if self.cooldown_remaining <= 0.0:
                    pulse_alpha = int(180 + math.sin(self._time_elapsed * 4.5) * 60)
                    ready_text = "[V] DEMON TIME: READY"
                    txt_surf = font_hud.render(ready_text, True, (240, 215, 255))
                    bg_rect = pg.Rect(badge_x, badge_y, txt_surf.get_width() + 20, 28)
                    pg.draw.rect(surface, (18, 8, 32, 210), bg_rect, border_radius=6)
                    pg.draw.rect(surface, (170, 70, 240, pulse_alpha), bg_rect, width=1, border_radius=6)
                    surface.blit(txt_surf, (badge_x + 10, badge_y + 5))
                else:
                    cd_text = f"DEMON TIME: {self.cooldown_remaining:.1f}s"
                    txt_surf = font_hud.render(cd_text, True, (150, 130, 165))
                    bg_rect = pg.Rect(badge_x, badge_y, txt_surf.get_width() + 20, 28)
                    pg.draw.rect(surface, (18, 12, 22, 160), bg_rect, border_radius=6)
                    pg.draw.rect(surface, (90, 60, 110), bg_rect, width=1, border_radius=6)
                    surface.blit(txt_surf, (badge_x + 10, badge_y + 5))
