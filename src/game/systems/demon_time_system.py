"""
Demon Time System & The EYE Companion.

Provides the canonical Level 1 narrative companion mechanics:
1. The EYE Familiar: hovers beside player shoulder, manifests (Movement animation),
   idles with purple demonic glow, fires Void Ball Projectile (Attack animation),
   and dissolves into void mist (Death animation).
2. Demon Time: World and enemy physics slow down to 0.20x speed while the player
   maintains normal 1.0x speed for evasion and targeting.
3. [PRESS A] Void Strike: QTE projectile counter-strike that damages and stuns foes.
"""

from __future__ import annotations

import math
import os
from typing import Any, Dict, List, Optional
import pygame as pg

from v3x_zulfiqar_gideon import AssetManager


class VoidBallProjectile(pg.sprite.Sprite):
    """Demonic projectile fired by The EYE during Demon Time Void Strike."""

    def __init__(
        self,
        x: float,
        y: float,
        target_x: float,
        target_y: float,
        damage: float = 75.0,
        speed: float = 14.0,
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
        if os.path.exists(proj_dir):
            for i in range(1, 4):
                p_path = os.path.join(proj_dir, f"Void Ball Projectile{i}.png")
                if os.path.exists(p_path):
                    img = pg.image.load(p_path).convert_alpha()
                    self._fly_frames.append(pg.transform.smoothscale(img, (48, 48)))

            for i in range(1, 4):
                d_path = os.path.join(proj_dir, f"Projectile Destroyed{i}.png")
                if os.path.exists(d_path):
                    img = pg.image.load(d_path).convert_alpha()
                    self._destroy_frames.append(pg.transform.smoothscale(img, (48, 48)))

    def _create_fallback_surf(self) -> pg.Surface:
        surf = pg.Surface((32, 32), pg.SRCALPHA)
        pg.draw.circle(surf, (180, 80, 255), (16, 16), 14)
        pg.draw.circle(surf, (255, 255, 255), (16, 16), 7)
        return surf

    def update(self, dt: float = 1.0 / 60.0, scroll_speed: float = 0.0) -> None:
        if self._is_destroying:
            self._anim_timer += dt
            if self._anim_timer >= 0.08:
                self._anim_timer = 0.0
                self._destroy_idx += 1
                if self._destroy_idx < len(self._destroy_frames):
                    self.image = self._destroy_frames[self._destroy_idx]
                else:
                    self.kill()
            return

        # Advance position
        self.x += self.vx * (dt * 60.0)
        self.y += self.vy * (dt * 60.0)
        self.rect.center = (int(self.x), int(self.y))

        # Projectile animation
        if self._fly_frames:
            self._anim_timer += dt
            if self._anim_timer >= 0.07:
                self._anim_timer = 0.0
                self._frame_idx = (self._frame_idx + 1) % len(self._fly_frames)
                self.image = self._fly_frames[self._frame_idx]

        # Despawn if out of play boundary
        if self.x < -200 or self.x > 3000 or self.y < -200 or self.y > 1000:
            self.kill()

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
    """The EYE familiar that hovers beside the player during Demon Time."""

    STATE_INACTIVE = "inactive"
    STATE_APPEARING = "appearing"
    STATE_IDLE = "idle"
    STATE_ATTACKING = "attacking"
    STATE_DISAPPEARING = "disappearing"

    def __init__(self) -> None:
        self.state: str = self.STATE_INACTIVE
        self.x: float = 0.0
        self.y: float = 0.0
        self.facing_right: bool = True

        self._anim_frames: Dict[str, List[pg.Surface]] = {
            "appearing": [],
            "idle": [],
            "attack": [],
            "disappearing": [],
        }
        self._frame_idx: int = 0
        self._anim_timer: float = 0.0
        self._float_time: float = 0.0

        self._load_animations()

    def _load_animations(self) -> None:
        base_dir = os.path.join("assets", "graphics", "Evil Eye Beast For Itch")
        scale = 1.3

        def _load_folder(folder: str, prefix: str, count: int) -> List[pg.Surface]:
            frames = []
            f_dir = os.path.join(base_dir, folder)
            if os.path.exists(f_dir):
                for i in range(1, count + 1):
                    p = os.path.join(f_dir, f"{prefix}{i}.png")
                    if os.path.exists(p):
                        try:
                            img = pg.image.load(p).convert_alpha()
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

    def summon(self, player_x: float, player_y: float) -> None:
        """Manifest The EYE beside the player."""
        self.state = self.STATE_APPEARING
        self.x = player_x - 45.0
        self.y = player_y - 25.0
        self._frame_idx = 0
        self._anim_timer = 0.0
        self._float_time = 0.0

    def trigger_attack(self) -> None:
        """Trigger Void Ball casting attack animation."""
        if self.state in (self.STATE_IDLE, self.STATE_APPEARING):
            self.state = self.STATE_ATTACKING
            self._frame_idx = 0
            self._anim_timer = 0.0

    def dismiss(self) -> None:
        """Begin dissolving disappearance animation."""
        if self.state != self.STATE_INACTIVE:
            self.state = self.STATE_DISAPPEARING
            self._frame_idx = 0
            self._anim_timer = 0.0

    def update(self, dt: float, player_x: float, player_y: float, facing_right: bool = True) -> None:
        if self.state == self.STATE_INACTIVE:
            return

        self.facing_right = facing_right
        self._float_time += dt

        # Smooth companion following position beside player shoulder
        target_offset_x = -45.0 if facing_right else 45.0
        target_x = player_x + target_offset_x
        # 4px subtle sine bob
        target_y = (player_y - 20.0) + math.sin(self._float_time * 3.5) * 4.0

        # Gentle ease toward target position
        self.x += (target_x - self.x) * min(1.0, dt * 10.0)
        self.y += (target_y - self.y) * min(1.0, dt * 10.0)

        # Update animation frames
        self._anim_timer += dt
        frame_speed = 0.06

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

    def draw(self, surface: pg.Surface, camera_x: float = 0.0) -> None:
        if self.state == self.STATE_INACTIVE:
            return

        frame_key = {
            self.STATE_APPEARING: "appearing",
            self.STATE_IDLE: "idle",
            self.STATE_ATTACKING: "attack",
            self.STATE_DISAPPEARING: "disappearing",
        }.get(self.state, "idle")

        frames = self._anim_frames.get(frame_key, [])
        if not frames:
            return

        raw_frame = frames[min(self._frame_idx, len(frames) - 1)]

        # Facing direction
        frame = raw_frame if not self.facing_right else pg.transform.flip(raw_frame, True, False)

        # Apply purple demonic glow during Demon Time
        glow_surf = frame.copy()
        tint = pg.Surface(glow_surf.get_size(), pg.SRCALPHA)
        tint.fill((160, 60, 255, 120))
        glow_surf.blit(tint, (0, 0), special_flags=pg.BLEND_RGBA_MULT)

        screen_x = int(self.x - camera_x)
        screen_y = int(self.y)

        # Draw outer purple halo
        halo_surf = pg.Surface((frame.get_width() + 16, frame.get_height() + 16), pg.SRCALPHA)
        center = (halo_surf.get_width() // 2, halo_surf.get_height() // 2)
        pg.draw.circle(halo_surf, (140, 40, 240, 70), center, halo_surf.get_width() // 2 - 2)
        surface.blit(halo_surf, (screen_x - 8, screen_y - 8))

        # Blit companion sprite
        surface.blit(glow_surf, (screen_x, screen_y))


class DemonTimeSystem:
    """Orchestrates bullet-time Demon Time, companion summoning, and QTE Void Strikes."""

    def __init__(self) -> None:
        self.is_unlocked: bool = False
        self.is_active: bool = False
        self.time_scale: float = 0.20
        self.duration_total: float = 4.5
        self.duration_remaining: float = 0.0
        self.cooldown_total: float = 16.0
        self.cooldown_remaining: float = 0.0

        # QTE prompt state
        self.qte_available: bool = False
        self.qte_prompt_text: str = "[PRESS A] VOID STRIKE"

        # Subsystems
        self.companion = DemonEyeCompanion()
        self.projectiles: pg.sprite.Group = pg.sprite.Group()

    def unlock(self) -> None:
        """Call when The EYE relic is acquired."""
        self.is_unlocked = True

    def activate(self, duration: float = 4.5, time_scale: float = 0.20, player_x: float = 0.0, player_y: float = 0.0) -> bool:
        """Activate Demon Time slow-motion mode."""
        if not self.is_unlocked:
            return False
        if self.is_active or self.cooldown_remaining > 0.0:
            return False

        self.is_active = True
        self.time_scale = time_scale
        self.duration_total = duration
        self.duration_remaining = duration
        self.qte_available = True

        self.companion.summon(player_x, player_y)
        return True

    def handle_input(
        self,
        event: pg.event.Event,
        player_x: float,
        player_y: float,
        target_x: float,
        target_y: float,
    ) -> bool:
        """Handle player hotkeys for Demon Time and Void Strike."""
        if not self.is_unlocked:
            return False

        # 1. Trigger Void Strike during Demon Time
        if self.is_active and self.qte_available:
            trigger_shot = False
            if event.type == pg.KEYDOWN and event.key in (pg.K_a, pg.K_SPACE, pg.K_f):
                trigger_shot = True
            elif event.type == pg.JOYBUTTONDOWN and event.button in (0, 2):  # A or X
                trigger_shot = True

            if trigger_shot:
                self.qte_available = False
                self.companion.trigger_attack()
                proj = VoidBallProjectile(
                    x=self.companion.x + 20.0,
                    y=self.companion.y + 10.0,
                    target_x=target_x,
                    target_y=target_y,
                )
                self.projectiles.add(proj)
                return True

        # 2. Trigger Demon Time summon
        if not self.is_active and self.cooldown_remaining <= 0.0:
            activate_req = False
            if event.type == pg.KEYDOWN and event.key in (pg.K_t, pg.K_e):
                activate_req = True
            elif event.type == pg.JOYBUTTONDOWN and event.button in (3, 5):  # Y or RB
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
        """Update Demon Time timers, companion, and projectile collisions."""
        # Update cooldown
        if self.cooldown_remaining > 0.0:
            self.cooldown_remaining = max(0.0, self.cooldown_remaining - dt)

        # Update active Demon Time
        if self.is_active:
            self.duration_remaining -= dt
            if self.duration_remaining <= 0.0:
                self.is_active = False
                self.cooldown_remaining = self.cooldown_total
                self.companion.dismiss()

        # Update companion position & animations
        self.companion.update(dt, player_x, player_y, facing_right)

        # Update projectiles
        self.projectiles.update(dt)

        # Check projectile hit collisions with enemies & boss
        for proj in list(self.projectiles):
            if not getattr(proj, "_is_destroying", False):
                # Check boss collision
                if boss and hasattr(boss, "rect") and getattr(boss, "alive", lambda: True)():
                    if proj.rect.colliderect(boss.rect):
                        if hasattr(boss, "take_damage"):
                            boss.take_damage(proj.damage)
                        elif hasattr(boss, "health"):
                            boss.health = max(0.0, boss.health - proj.damage)
                        proj.explode()
                        continue

                # Check enemy collision
                if enemies:
                    for enemy in enemies:
                        if hasattr(enemy, "rect") and getattr(enemy, "alive", lambda: True)():
                            if proj.rect.colliderect(enemy.rect):
                                if hasattr(enemy, "take_damage"):
                                    enemy.take_damage(proj.damage)
                                elif hasattr(enemy, "health"):
                                    enemy.health = max(0.0, enemy.health - proj.damage)
                                proj.explode()
                                break

    def get_enemy_time_scale(self) -> float:
        """Return delta-time scale factor for enemies and world physics."""
        return self.time_scale if self.is_active else 1.0

    def get_player_time_scale(self) -> float:
        """Player stays at full normal speed (1.0x)."""
        return 1.0

    def draw(self, surface: pg.Surface, camera_x: float = 0.0) -> None:
        """Draw companion familiar and projectiles."""
        self.companion.draw(surface, camera_x)
        for proj in self.projectiles:
            screen_x = int(proj.rect.x - camera_x)
            surface.blit(proj.image, (screen_x, proj.rect.y))

    def draw_overlay(self, surface: pg.Surface) -> None:
        """Draw Demon Time atmospheric purple vignette and QTE prompt."""
        if not self.is_active:
            return

        w, h = surface.get_size()

        # Subtle purple border vignette
        vignette = pg.Surface((w, h), pg.SRCALPHA)
        pg.draw.rect(vignette, (130, 30, 220, 35), (0, 0, w, h), width=28)
        pg.draw.rect(vignette, (180, 50, 255, 60), (0, 0, w, h), width=10)
        surface.blit(vignette, (0, 0))

        # Top banner: "DEMON TIME: 0.20x SLOW-MOTION"
        banner_w, banner_h = 320, 32
        banner_x = (w - banner_w) // 2
        banner_y = 18
        banner_rect = pg.Rect(banner_x, banner_y, banner_w, banner_h)
        pg.draw.rect(surface, (20, 10, 35, 230), banner_rect, border_radius=6)
        pg.draw.rect(surface, (190, 80, 255), banner_rect, width=2, border_radius=6)

        # Duration progress bar
        ratio = max(0.0, min(1.0, self.duration_remaining / max(0.01, self.duration_total)))
        fill_w = int((banner_w - 6) * ratio)
        if fill_w > 0:
            pg.draw.rect(
                surface,
                (200, 100, 255),
                (banner_x + 3, banner_y + banner_h - 6, fill_w, 3),
                border_radius=2,
            )

        font_sm = AssetManager.get_font(None, 18)
        timer_text = f"DEMON TIME  [{self.duration_remaining:.1f}s]"
        t_surf = font_sm.render(timer_text, True, (240, 210, 255))
        surface.blit(
            t_surf,
            (
                banner_x + (banner_w - t_surf.get_width()) // 2,
                banner_y + (banner_h - 6 - t_surf.get_height()) // 2,
            ),
        )

        # QTE Prompt when strike available
        if self.qte_available:
            qte_w, qte_h = 240, 36
            qte_x = (w - qte_w) // 2
            qte_y = banner_y + 42
            qte_rect = pg.Rect(qte_x, qte_y, qte_w, qte_h)
            pg.draw.rect(surface, (40, 15, 60, 240), qte_rect, border_radius=6)
            pg.draw.rect(surface, (255, 220, 90), qte_rect, width=2, border_radius=6)

            font_qte = AssetManager.get_font(None, 20)
            q_surf = font_qte.render(self.qte_prompt_text, True, (255, 235, 120))
            surface.blit(
                q_surf,
                (
                    qte_x + (qte_w - q_surf.get_width()) // 2,
                    qte_y + (qte_h - q_surf.get_height()) // 2,
                ),
            )
