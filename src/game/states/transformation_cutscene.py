"""
Transformation cutscene state — Dynamic, non-cinematic transformation sequence.

Plays an immersive transformation sequence with organic camera dynamics:
  • Orb Collapse: Speed slows, camera zooms in, soft portal vibration,
    gravitational vortex pulls particles inward toward the singularity.
  • Demon Burst: Speed accelerates, explosive flash, particles blast outward.
  • Demon Attacks: Camera sways in the direction of each slash.
  • Special Tentacle Attack ('F'): Camera slowly zooms in as tentacles extend,
    slowly zooms back out as they retract.
  • Revert → Level Intro banner → GameState.

Configurable via game_data/cutscene_config.json or the cutscene editor GUI plugin.
"""

from __future__ import annotations

import json
import math
import os
import random
from enum import IntEnum, auto
from typing import Any, Callable, Optional

import pygame as pg

from v3x_zulfiqar_gideon import AssetManager, State, NotificationBanner


CONFIG_PATH = os.path.join("game_data", "cutscene_config.json")


# ─────────────────────────────────────────────────────────────────────────────
# Phase Enum
# ─────────────────────────────────────────────────────────────────────────────

class _Phase(IntEnum):
    """Sequential cutscene phases."""
    FADE_IN = 0
    ORB_COLLAPSE = auto()      # transform_1..16 → character collapses into dark orb
    ORB_LOOP = auto()          # transform_17..24 → black hole singularity pulsates
    DEMON_BURST = auto()       # transform_25..37 → explosive burst into demon form
    ATTACK_LEFT = auto()       # e_3_atk → demon slash left, camera sways left
    ATTACK_RIGHT = auto()      # e_3_atk flipped → demon slash right, camera sways right
    SPECIAL_TENTACLES = auto() # e_sp_atk → tentacle attack, zoom in/out with tentacles
    REVERT = auto()            # back2human → red flashes, reverts to human
    LEVEL_INTRO = auto()       # Act 1 banner notification
    DONE = auto()


# ─────────────────────────────────────────────────────────────────────────────
# Easing Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _ease_in_out(t: float) -> float:
    """Smooth ease-in-out (sine curve). t in [0,1] → [0,1]."""
    return 0.5 - 0.5 * math.cos(math.pi * t)


def _lerp(a: float, b: float, t: float) -> float:
    """Linear interpolation."""
    return a + (b - a) * min(1.0, max(0.0, t))


# ─────────────────────────────────────────────────────────────────────────────
# Camera Rig
# ─────────────────────────────────────────────────────────────────────────────

class _CameraRig:
    """Manages smooth zoom, directional sway offset, and portal vibration."""

    def __init__(self, width: int, height: int) -> None:
        self.width = width
        self.height = height

        # Zoom
        self.current_zoom: float = 1.0
        self.target_zoom: float = 1.0
        self.zoom_speed: float = 2.0  # lerp speed (units/sec)

        # Sway offset (directional camera thrust for attacks)
        self.sway_x: float = 0.0
        self.sway_y: float = 0.0
        self.target_sway_x: float = 0.0
        self.target_sway_y: float = 0.0
        self.sway_speed: float = 5.0

        # Portal vibration (low-frequency soft rumble)
        self.shake_amplitude: float = 0.0       # current shake strength (px)
        self.target_shake_amplitude: float = 0.0
        self.shake_frequency: float = 12.0      # Hz
        self._shake_phase: float = 0.0
        self._shake_offset_x: float = 0.0
        self._shake_offset_y: float = 0.0

        # Focus point (center of zoom)
        self.focus_x: float = width / 2.0
        self.focus_y: float = height / 2.0

        # Buffer
        self.buffer: pg.Surface = pg.Surface((width, height))

    def set_zoom(self, target: float, speed: float = 2.0) -> None:
        self.target_zoom = target
        self.zoom_speed = speed

    def set_sway(self, sx: float, sy: float = 0.0, speed: float = 5.0) -> None:
        self.target_sway_x = sx
        self.target_sway_y = sy
        self.sway_speed = speed

    def set_shake(self, amplitude: float, frequency: float = 12.0) -> None:
        self.target_shake_amplitude = amplitude
        self.shake_frequency = frequency

    def update(self, dt_sec: float) -> None:
        # Zoom lerp
        zoom_diff = self.target_zoom - self.current_zoom
        if abs(zoom_diff) > 0.001:
            self.current_zoom += zoom_diff * min(1.0, dt_sec * self.zoom_speed)
        else:
            self.current_zoom = self.target_zoom

        # Sway lerp
        sx_diff = self.target_sway_x - self.sway_x
        sy_diff = self.target_sway_y - self.sway_y
        self.sway_x += sx_diff * min(1.0, dt_sec * self.sway_speed)
        self.sway_y += sy_diff * min(1.0, dt_sec * self.sway_speed)

        # Shake lerp + oscillation
        amp_diff = self.target_shake_amplitude - self.shake_amplitude
        self.shake_amplitude += amp_diff * min(1.0, dt_sec * 6.0)
        self._shake_phase += dt_sec * self.shake_frequency * math.tau
        if self.shake_amplitude > 0.2:
            self._shake_offset_x = math.sin(self._shake_phase) * self.shake_amplitude
            self._shake_offset_y = math.cos(self._shake_phase * 1.3) * self.shake_amplitude * 0.7
        else:
            self._shake_offset_x = 0.0
            self._shake_offset_y = 0.0

    def apply(self, source: pg.Surface, dest: pg.Surface) -> None:
        """Apply zoom, sway, and shake to render source onto dest."""
        zoom = max(1.0, self.current_zoom)

        # Total offset = sway + shake
        total_ox = self.sway_x + self._shake_offset_x
        total_oy = self.sway_y + self._shake_offset_y

        if zoom <= 1.001 and abs(total_ox) < 0.5 and abs(total_oy) < 0.5:
            dest.blit(source, (0, 0))
            return

        # Compute crop region centered on focus + offset
        crop_w = int(self.width / zoom)
        crop_h = int(self.height / zoom)
        cx = self.focus_x + total_ox
        cy = self.focus_y + total_oy
        crop_x = int(max(0, min(cx - crop_w // 2, self.width - crop_w)))
        crop_y = int(max(0, min(cy - crop_h // 2, self.height - crop_h)))

        # Clamp to valid bounds
        crop_w = min(crop_w, self.width - crop_x)
        crop_h = min(crop_h, self.height - crop_y)
        if crop_w < 1 or crop_h < 1:
            dest.blit(source, (0, 0))
            return

        sub = source.subsurface((crop_x, crop_y, crop_w, crop_h))
        zoomed = pg.transform.smoothscale(sub, (self.width, self.height))
        dest.blit(zoomed, (0, 0))


# ─────────────────────────────────────────────────────────────────────────────
# Gravity Vortex Particle
# ─────────────────────────────────────────────────────────────────────────────

class _VortexParticle:
    """A single particle affected by gravitational pull toward a singularity."""

    __slots__ = ("x", "y", "vx", "vy", "size", "alpha_phase", "base_color", "life")

    def __init__(self, x: float, y: float, sw: int, sh: int) -> None:
        self.x = x
        self.y = y
        self.vx = random.uniform(-20, 20)
        self.vy = random.uniform(-25, -5)
        self.size = random.randint(2, 4)
        self.alpha_phase = random.uniform(0, math.tau)
        r = random.randint(200, 255)
        g = random.randint(120, 220)
        b = random.randint(20, 80)
        self.base_color = (r, g, b)
        self.life = 1.0


class _GravityVortexEngine:
    """Particle engine with gravitational pull toward a singularity point."""

    def __init__(self, count: int, sw: int, sh: int) -> None:
        self.sw = sw
        self.sh = sh
        self.particles: list[_VortexParticle] = []
        self.resize(count)

        self.cx: float = sw / 2.0
        self.cy: float = sh / 2.0

        self.gravity_strength: float = 0.0
        self.explosion_strength: float = 0.0
        self._explosion_applied: bool = False

    def resize(self, count: int) -> None:
        current_len = len(self.particles)
        if count < current_len:
            self.particles = self.particles[:count]
        elif count > current_len:
            for _ in range(count - current_len):
                self.particles.append(
                    _VortexParticle(
                        random.uniform(0, self.sw),
                        random.uniform(0, self.sh),
                        self.sw, self.sh,
                    )
                )

    def set_inward_gravity(self, strength: float) -> None:
        self.gravity_strength = strength
        self.explosion_strength = 0.0
        self._explosion_applied = False

    def set_explosion(self, strength: float) -> None:
        self.explosion_strength = strength
        self.gravity_strength = 0.0
        self._explosion_applied = False

    def set_ambient(self) -> None:
        self.gravity_strength = 0.0
        self.explosion_strength = 0.0
        self._explosion_applied = False

    def update(self, dt_sec: float) -> None:
        for p in self.particles:
            dx = self.cx - p.x
            dy = self.cy - p.y
            dist = math.hypot(dx, dy)

            if self.gravity_strength > 0 and dist > 5:
                force = self.gravity_strength / max(dist, 30.0)
                p.vx += (dx / dist) * force * dt_sec * 800
                p.vy += (dy / dist) * force * dt_sec * 800
                p.vx += (-dy / dist) * force * dt_sec * 200
                p.vy += (dx / dist) * force * dt_sec * 200
            elif self.explosion_strength > 0 and not self._explosion_applied:
                if dist > 2:
                    blast = self.explosion_strength * random.uniform(0.6, 1.4)
                    p.vx = (dx / dist) * -blast + random.uniform(-80, 80)
                    p.vy = (dy / dist) * -blast + random.uniform(-80, 80)
                else:
                    angle = random.uniform(0, math.tau)
                    blast = self.explosion_strength * random.uniform(0.6, 1.4)
                    p.vx = math.cos(angle) * blast
                    p.vy = math.sin(angle) * blast
            else:
                p.vy += -15.0 * dt_sec
                p.vx *= 0.98

            p.vx *= (1.0 - 0.5 * dt_sec)
            p.vy *= (1.0 - 0.5 * dt_sec)

            p.x += p.vx * dt_sec
            p.y += p.vy * dt_sec

            if p.x < -30:
                p.x = self.sw + 20
            elif p.x > self.sw + 30:
                p.x = -20
            if p.y < -30:
                p.y = self.sh + 20
            elif p.y > self.sh + 30:
                p.y = -20

        if self.explosion_strength > 0 and not self._explosion_applied:
            self._explosion_applied = True

    def draw(self, surface: pg.Surface) -> None:
        ticks = pg.time.get_ticks()
        for p in self.particles:
            pulse = (math.sin(ticks * 0.005 + p.alpha_phase) + 1.0) * 0.5
            alpha = int(100 + 120 * pulse)
            r, g, b = p.base_color

            glow = pg.Surface((16, 16), pg.SRCALPHA)
            pg.draw.circle(glow, (r, g, b, int(alpha * 0.35)), (8, 8), 7)
            pg.draw.circle(glow, (min(255, r + 40), min(255, g + 40), b, alpha), (8, 8), p.size)
            surface.blit(glow, (int(p.x) - 8, int(p.y) - 8))


# ─────────────────────────────────────────────────────────────────────────────
# Transformation Cutscene State
# ─────────────────────────────────────────────────────────────────────────────

class TransformationCutscene(State):
    """Full-screen dynamic transformation sequence with camera effects."""

    # Default fallback constants
    _DEFAULT_CONFIG: dict[str, Any] = {
        "phases": {
            "fade_in": {"duration": 1.5},
            "orb_collapse": {
                "frame_duration": 0.11,
                "camera_zoom": 1.45,
                "camera_zoom_speed": 1.2,
                "shake_amplitude": 3.5,
                "shake_frequency": 10.0,
                "gravity_strength": 8.0,
                "sfx": ["transform", "aura_effect"]
            },
            "orb_loop": {
                "frame_duration": 0.09,
                "loop_cycles": 3,
                "camera_zoom": 1.50,
                "camera_zoom_speed": 0.8,
                "shake_amplitude": 4.5,
                "shake_frequency": 14.0,
                "gravity_strength": 14.0,
                "sfx": ["lightning"]
            },
            "demon_burst": {
                "frame_duration": 0.035,
                "flash_color_white": [255, 255, 255],
                "flash_color_red": [180, 20, 20],
                "red_flash_trigger_frame": 3,
                "explosion_strength": 450.0,
                "shake_amplitude": 8.0,
                "shake_frequency": 20.0,
                "camera_zoom_snapback_speed": 6.0,
                "sfx": ["magic_sfx", "bells", "wendigo_screams"]
            },
            "attack_left": {
                "frame_duration": 0.055,
                "sway_x": -55.0,
                "sway_speed": 4.0,
                "sway_return_pct": 0.7,
                "sfx": ["smash_phase_2"]
            },
            "attack_right": {
                "frame_duration": 0.055,
                "sway_x": 55.0,
                "sway_speed": 4.0,
                "sway_return_pct": 0.7,
                "sfx": ["smash_phase_3"]
            },
            "special_tentacles": {
                "frame_duration": 0.075,
                "zoom_peak_frame": 11,
                "zoom_max": 1.50,
                "zoom_speed": 2.5,
                "peak_shake_amplitude": 2.5,
                "peak_shake_frequency": 8.0,
                "sfx": ["special_attack", "power_release_1"]
            },
            "revert": {
                "frame_duration": 0.07,
                "flash_count": 4,
                "flash_cycle_duration": 0.22,
                "flash_color": [200, 15, 15],
                "flash_peak_alpha": 180,
                "post_pause": 0.6,
                "sfx": []
            }
        },
        "global": {
            "sprite_scale": 3.5,
            "particle_count": 40,
            "crossfade_duration": 0.30,
            "flash_fade_speed": 0.30,
            "background_color": [12, 10, 20]
        },
        "assets": {
            "transform_dir": "assets/shadow_warrior/transform",
            "atk_left_dir": "assets/shadow_warrior/e_3_atk",
            "atk_right_dir": "assets/shadow_warrior/e_3_atk",
            "special_atk_dir": "assets/shadow_warrior/e_sp_atk",
            "revert_dir": "assets/shadow_warrior/back2human"
        }
    }

    def __init__(
        self,
        manager,
        level_title: str = "Act 1: The Dark Forest",
        notification: str = "gray",
        on_complete: Optional[Callable[[], None]] = None,
        next_state_factory: Optional[Callable[[], State]] = None,
    ) -> None:
        super().__init__(manager)
        self._level_title = level_title
        self._notification_type = notification
        self._on_complete = on_complete
        self._next_state_factory = next_state_factory

        info = pg.display.Info()
        self._sw = info.current_w
        self._sh = info.current_h

        # Load config dynamically
        self._config = self._load_config()

        # Global attributes from config
        g_cfg = self._config.get("global", {})
        self._sprite_scale = float(g_cfg.get("sprite_scale", 3.5))
        self._particle_count = int(g_cfg.get("particle_count", 40))
        self._crossfade_duration = float(g_cfg.get("crossfade_duration", 0.30))
        self._flash_fade_speed = float(g_cfg.get("flash_fade_speed", 0.30))
        self._bg_color = tuple(g_cfg.get("background_color", [12, 10, 20]))

        # Asset paths from config
        a_cfg = self._config.get("assets", {})
        transform_dir = a_cfg.get("transform_dir", "assets/shadow_warrior/transform")
        atk_left_dir = a_cfg.get("atk_left_dir", "assets/shadow_warrior/e_3_atk")
        atk_right_dir = a_cfg.get("atk_right_dir", "assets/shadow_warrior/e_3_atk")
        special_atk_dir = a_cfg.get("special_atk_dir", "assets/shadow_warrior/e_sp_atk")
        revert_dir = a_cfg.get("revert_dir", "assets/shadow_warrior/back2human")

        # ── Load & scale frame sets ──────────────────────────────────────────
        all_transform = self._load_scaled(transform_dir)
        self._frames_orb_collapse = all_transform[:16]
        self._frames_orb_loop = all_transform[16:24]
        self._frames_demon_burst = all_transform[24:]

        self._frames_atk_left = self._load_scaled(atk_left_dir)
        self._frames_atk_right = self._load_scaled(atk_right_dir, flip=True)
        self._frames_special = self._load_scaled(special_atk_dir)
        self._frames_revert = self._load_scaled(revert_dir)

        # ── Camera Rig ───────────────────────────────────────────────────────
        self._camera = _CameraRig(self._sw, self._sh)

        # ── Gravity Vortex Particles ─────────────────────────────────────────
        self._vortex = _GravityVortexEngine(self._particle_count, self._sw, self._sh)

        # ── Level intro banner ───────────────────────────────────────────────
        self._banner = NotificationBanner(scale=0.6, icon_scale=0.6)

        # ── Persistent overlay surfaces ──────────────────────────────────────
        self._overlay = pg.Surface((self._sw, self._sh), pg.SRCALPHA)
        self._scene_buffer = pg.Surface((self._sw, self._sh))

        # ── Runtime state ────────────────────────────────────────────────────
        self._reset_state()

    @classmethod
    def _load_config(cls) -> dict[str, Any]:
        """Load JSON configuration with fallback to default schema."""
        cfg = dict(cls._DEFAULT_CONFIG)
        if os.path.exists(CONFIG_PATH):
            try:
                with open(CONFIG_PATH, "r") as f:
                    loaded = json.load(f)
                if isinstance(loaded, dict):
                    # Merge loaded into cfg
                    for section in ("phases", "global", "assets"):
                        if section in loaded and isinstance(loaded[section], dict):
                            if section not in cfg:
                                cfg[section] = {}
                            cfg[section].update(loaded[section])
            except Exception as e:
                print(f"[TransformationCutscene] Warning: Could not load {CONFIG_PATH}: {e}")
        return cfg

    def _reset_state(self) -> None:
        self._phase = _Phase.FADE_IN
        self._phase_timer = 0.0
        self._frame_idx = 0
        self._frame_timer = 0.0
        self._orb_loop_count = 0

        # Cross-fade
        self._crossfading = False
        self._crossfade_timer = 0.0
        self._prev_frame: Optional[pg.Surface] = None

        # Flash VFX
        self._flash_alpha = 0.0
        self._flash_color: tuple[int, int, int] = (255, 255, 255)

        # Revert red flashes
        self._red_flashes_done = 0
        self._red_flash_timer = 0.0
        self._post_pause_timer = 0.0

        # Audio triggers (prevent duplicate fires)
        self._audio_triggered: set[str] = set()

        # Reset camera
        self._camera.current_zoom = 1.0
        self._camera.target_zoom = 1.0
        self._camera.sway_x = 0.0
        self._camera.sway_y = 0.0
        self._camera.target_sway_x = 0.0
        self._camera.target_sway_y = 0.0
        self._camera.shake_amplitude = 0.0
        self._camera.target_shake_amplitude = 0.0

        # Reset vortex
        self._vortex.set_ambient()

    def _load_scaled(
        self, directory: str, flip: bool = False
    ) -> list[pg.Surface]:
        """Load animation frames, scale them up, optionally flip horizontally."""
        raw_frames = AssetManager.get_animation_frames(directory)
        scaled: list[pg.Surface] = []
        for f in raw_frames:
            w = int(f.get_width() * self._sprite_scale)
            h = int(f.get_height() * self._sprite_scale)
            s = pg.transform.smoothscale(f, (w, h))
            if flip:
                s = pg.transform.flip(s, True, False)
            scaled.append(s)
        return scaled

    def _play_sfx_list(self, keys: list[str]) -> None:
        """Trigger a list of sound effects once."""
        for key in keys:
            if key and key not in self._audio_triggered:
                self._audio_triggered.add(key)
                try:
                    if hasattr(self.manager, "audio_manager") and self.manager.audio_manager:
                        self.manager.audio_manager.play_sound(key)
                except Exception:
                    pass

    # ─── State interface ─────────────────────────────────────────────────────

    def on_enter(self) -> None:
        # Reload config in case it was modified in the editor while running
        self._config = self._load_config()
        self._reset_state()

    def handle_event(self, event: pg.event.Event) -> None:
        if event.type == pg.KEYDOWN and event.key in (pg.K_SPACE, pg.K_RETURN):
            self._finish()

    # ─── Update ──────────────────────────────────────────────────────────────

    def update(self, dt: float) -> None:
        dt_sec = dt / 1000.0
        self._phase_timer += dt_sec

        # Decay flash overlay
        if self._flash_alpha > 0:
            fade_rate = 255.0 / max(0.01, self._flash_fade_speed)
            self._flash_alpha = max(0.0, self._flash_alpha - dt_sec * fade_rate)

        # Update camera rig
        self._camera.update(dt_sec)

        # Update vortex particles
        self._vortex.update(dt_sec)

        # Cross-fade timer
        if self._crossfading:
            self._crossfade_timer += dt_sec
            if self._crossfade_timer >= self._crossfade_duration:
                self._crossfading = False
                self._prev_frame = None

        # ── Phase-specific update ────────────────────────────────────────────
        if self._phase == _Phase.FADE_IN:
            self._update_fade_in()

        elif self._phase == _Phase.ORB_COLLAPSE:
            self._update_orb_collapse(dt_sec)

        elif self._phase == _Phase.ORB_LOOP:
            self._update_orb_loop(dt_sec)

        elif self._phase == _Phase.DEMON_BURST:
            self._update_demon_burst(dt_sec)

        elif self._phase == _Phase.ATTACK_LEFT:
            self._update_attack(dt_sec, self._frames_atk_left, _Phase.ATTACK_RIGHT, "attack_left")

        elif self._phase == _Phase.ATTACK_RIGHT:
            self._update_attack(dt_sec, self._frames_atk_right, _Phase.SPECIAL_TENTACLES, "attack_right")

        elif self._phase == _Phase.SPECIAL_TENTACLES:
            self._update_special_tentacles(dt_sec)

        elif self._phase == _Phase.REVERT:
            self._update_revert(dt_sec)

        elif self._phase == _Phase.LEVEL_INTRO:
            self._banner.update(dt)
            if not self._banner.is_active:
                self._finish()

    # ── Phase update methods ─────────────────────────────────────────────────

    def _update_fade_in(self) -> None:
        p_cfg = self._config.get("phases", {}).get("fade_in", {})
        duration = float(p_cfg.get("duration", 1.5))
        if self._phase_timer >= duration:
            self._enter_phase(_Phase.ORB_COLLAPSE)
            orb_cfg = self._config.get("phases", {}).get("orb_collapse", {})
            self._play_sfx_list(orb_cfg.get("sfx", ["transform", "aura_effect"]))

    def _update_orb_collapse(self, dt_sec: float) -> None:
        p_cfg = self._config.get("phases", {}).get("orb_collapse", {})
        f_dur = float(p_cfg.get("frame_duration", 0.11))
        zoom = float(p_cfg.get("camera_zoom", 1.45))
        zoom_speed = float(p_cfg.get("camera_zoom_speed", 1.2))
        shake_amp = float(p_cfg.get("shake_amplitude", 3.5))
        shake_freq = float(p_cfg.get("shake_frequency", 10.0))
        gravity = float(p_cfg.get("gravity_strength", 8.0))

        self._camera.set_zoom(zoom, speed=zoom_speed)
        self._camera.set_shake(shake_amp, frequency=shake_freq)
        self._vortex.set_inward_gravity(gravity)

        self._frame_timer += dt_sec
        while self._frame_timer >= f_dur:
            self._frame_timer -= f_dur
            self._frame_idx += 1
            if self._frame_idx >= len(self._frames_orb_collapse):
                self._enter_phase(_Phase.ORB_LOOP)
                loop_cfg = self._config.get("phases", {}).get("orb_loop", {})
                self._play_sfx_list(loop_cfg.get("sfx", ["lightning"]))
                return

    def _update_orb_loop(self, dt_sec: float) -> None:
        p_cfg = self._config.get("phases", {}).get("orb_loop", {})
        f_dur = float(p_cfg.get("frame_duration", 0.09))
        loop_cycles = int(p_cfg.get("loop_cycles", 3))
        zoom = float(p_cfg.get("camera_zoom", 1.50))
        zoom_speed = float(p_cfg.get("camera_zoom_speed", 0.8))
        shake_amp = float(p_cfg.get("shake_amplitude", 4.5))
        shake_freq = float(p_cfg.get("shake_frequency", 14.0))
        gravity = float(p_cfg.get("gravity_strength", 14.0))

        self._camera.set_zoom(zoom, speed=zoom_speed)
        self._camera.set_shake(shake_amp, frequency=shake_freq)
        self._vortex.set_inward_gravity(gravity)

        self._frame_timer += dt_sec
        while self._frame_timer >= f_dur:
            self._frame_timer -= f_dur
            self._frame_idx += 1
            if self._frame_idx >= len(self._frames_orb_loop):
                self._orb_loop_count += 1
                if self._orb_loop_count >= loop_cycles:
                    self._enter_phase(_Phase.DEMON_BURST)
                    return
                self._frame_idx = 0

    def _update_demon_burst(self, dt_sec: float) -> None:
        p_cfg = self._config.get("phases", {}).get("demon_burst", {})
        f_dur = float(p_cfg.get("frame_duration", 0.035))
        white_c = tuple(p_cfg.get("flash_color_white", [255, 255, 255]))
        red_c = tuple(p_cfg.get("flash_color_red", [180, 20, 20]))
        red_trigger_frame = int(p_cfg.get("red_flash_trigger_frame", 3))
        explosion_str = float(p_cfg.get("explosion_strength", 450.0))
        shake_amp = float(p_cfg.get("shake_amplitude", 8.0))
        shake_freq = float(p_cfg.get("shake_frequency", 20.0))
        snap_zoom_speed = float(p_cfg.get("camera_zoom_snapback_speed", 6.0))

        # Flash on first frame
        if self._frame_idx == 0 and self._flash_alpha < 10:
            self._flash_color = white_c
            self._flash_alpha = 255.0
            self._vortex.set_explosion(explosion_str)
            self._camera.set_shake(shake_amp, frequency=shake_freq)
            self._camera.set_zoom(1.0, speed=snap_zoom_speed)
            self._play_sfx_list(p_cfg.get("sfx", ["magic_sfx", "bells", "wendigo_screams"]))

        # Red flash after white fades
        if self._frame_idx >= red_trigger_frame and "demon_red_flash" not in self._audio_triggered:
            self._audio_triggered.add("demon_red_flash")
            self._flash_color = red_c
            self._flash_alpha = 200.0

        if self._frame_idx >= 4:
            self._camera.set_shake(0.0)
            self._vortex.set_ambient()

        self._frame_timer += dt_sec
        while self._frame_timer >= f_dur:
            self._frame_timer -= f_dur
            self._frame_idx += 1
            if self._frame_idx >= len(self._frames_demon_burst):
                self._enter_phase(_Phase.ATTACK_LEFT)
                atk_cfg = self._config.get("phases", {}).get("attack_left", {})
                self._play_sfx_list(atk_cfg.get("sfx", ["smash_phase_2"]))
                return

    def _update_attack(
        self,
        dt_sec: float,
        frames: list[pg.Surface],
        next_phase: _Phase,
        phase_key: str,
    ) -> None:
        p_cfg = self._config.get("phases", {}).get(phase_key, {})
        f_dur = float(p_cfg.get("frame_duration", 0.055))
        sway_x = float(p_cfg.get("sway_x", -55.0 if phase_key == "attack_left" else 55.0))
        sway_speed = float(p_cfg.get("sway_speed", 4.0))
        return_pct = float(p_cfg.get("sway_return_pct", 0.7))

        self._camera.set_sway(sway_x, speed=sway_speed)
        self._camera.set_zoom(1.0, speed=3.0)
        self._camera.set_shake(0.0)

        if self._frame_idx >= int(len(frames) * return_pct):
            self._camera.set_sway(0.0, speed=3.5)

        self._frame_timer += dt_sec
        while self._frame_timer >= f_dur:
            self._frame_timer -= f_dur
            self._frame_idx += 1
            if self._frame_idx >= len(frames):
                self._enter_phase(next_phase)
                next_key = "attack_right" if next_phase == _Phase.ATTACK_RIGHT else "special_tentacles"
                nxt_cfg = self._config.get("phases", {}).get(next_key, {})
                self._play_sfx_list(nxt_cfg.get("sfx", []))
                return

    def _update_special_tentacles(self, dt_sec: float) -> None:
        p_cfg = self._config.get("phases", {}).get("special_tentacles", {})
        f_dur = float(p_cfg.get("frame_duration", 0.075))
        zoom_peak_frame = int(p_cfg.get("zoom_peak_frame", 11))
        zoom_max = float(p_cfg.get("zoom_max", 1.50))
        zoom_speed = float(p_cfg.get("zoom_speed", 2.5))
        peak_shake_amp = float(p_cfg.get("peak_shake_amplitude", 2.5))
        peak_shake_freq = float(p_cfg.get("peak_shake_frequency", 8.0))

        total = len(self._frames_special) if self._frames_special else 19
        peak_idx = min(zoom_peak_frame, total - 1)

        if self._frame_idx <= peak_idx:
            t = self._frame_idx / max(peak_idx, 1)
            target_z = _lerp(1.0, zoom_max, _ease_in_out(t))
            self._camera.set_zoom(target_z, speed=zoom_speed)
        else:
            remaining = total - peak_idx
            t = (self._frame_idx - peak_idx) / max(remaining, 1)
            target_z = _lerp(zoom_max, 1.0, _ease_in_out(t))
            self._camera.set_zoom(target_z, speed=zoom_speed)

        self._camera.set_sway(0.0, speed=4.0)
        if self._frame_idx == peak_idx:
            self._camera.set_shake(peak_shake_amp, frequency=peak_shake_freq)
            self._play_sfx_list(p_cfg.get("sfx", ["special_attack", "power_release_1"]))
        elif self._frame_idx > peak_idx + 2:
            self._camera.set_shake(0.0)

        self._frame_timer += dt_sec
        while self._frame_timer >= f_dur:
            self._frame_timer -= f_dur
            self._frame_idx += 1
            if self._frame_idx >= total:
                self._enter_phase(_Phase.REVERT)
                return

    def _update_revert(self, dt_sec: float) -> None:
        p_cfg = self._config.get("phases", {}).get("revert", {})
        f_dur = float(p_cfg.get("frame_duration", 0.07))
        flash_count = int(p_cfg.get("flash_count", 4))
        flash_cycle = float(p_cfg.get("flash_cycle_duration", 0.22))
        flash_c = tuple(p_cfg.get("flash_color", [200, 15, 15]))
        peak_alpha = float(p_cfg.get("flash_peak_alpha", 180.0))
        post_pause = float(p_cfg.get("post_pause", 0.6))

        self._camera.set_zoom(1.0, speed=3.0)
        self._camera.set_sway(0.0, speed=5.0)
        self._camera.set_shake(0.0)

        self._frame_timer += dt_sec
        while self._frame_timer >= f_dur:
            self._frame_timer -= f_dur
            if self._frame_idx < len(self._frames_revert) - 1:
                self._frame_idx += 1

        if self._red_flashes_done < flash_count:
            self._red_flash_timer += dt_sec
            cycle_pos = self._red_flash_timer % flash_cycle
            half = flash_cycle / 2.0
            if cycle_pos < half:
                t = cycle_pos / half
                self._flash_color = flash_c
                self._flash_alpha = peak_alpha * _ease_in_out(t)
            else:
                t = (cycle_pos - half) / half
                self._flash_color = flash_c
                self._flash_alpha = peak_alpha * (1.0 - _ease_in_out(t))
            if self._red_flash_timer >= flash_cycle:
                self._red_flash_timer -= flash_cycle
                self._red_flashes_done += 1
        else:
            self._flash_alpha = 0.0
            if self._frame_idx >= len(self._frames_revert) - 1:
                self._post_pause_timer += dt_sec
                if self._post_pause_timer >= post_pause:
                    self._enter_phase(_Phase.LEVEL_INTRO)
                    self._banner.show(
                        self._level_title,
                        notification=self._notification_type,
                    )

    # ─── Phase management ────────────────────────────────────────────────────

    def _enter_phase(self, phase: _Phase) -> None:
        """Transition to a new phase with a cross-fade from the last frame."""
        old_frames = self._get_current_frames()
        if old_frames:
            idx = min(self._frame_idx, len(old_frames) - 1)
            self._prev_frame = old_frames[idx]
            self._crossfading = True
            self._crossfade_timer = 0.0

        self._phase = phase
        self._phase_timer = 0.0
        self._frame_idx = 0
        self._frame_timer = 0.0

    def _get_current_frames(self) -> list[pg.Surface]:
        mapping = {
            _Phase.ORB_COLLAPSE: self._frames_orb_collapse,
            _Phase.ORB_LOOP: self._frames_orb_loop,
            _Phase.DEMON_BURST: self._frames_demon_burst,
            _Phase.ATTACK_LEFT: self._frames_atk_left,
            _Phase.ATTACK_RIGHT: self._frames_atk_right,
            _Phase.SPECIAL_TENTACLES: self._frames_special,
            _Phase.REVERT: self._frames_revert,
        }
        return mapping.get(self._phase, [])

    def _finish(self) -> None:
        if self._phase == _Phase.DONE:
            return
        self._phase = _Phase.DONE

        if self._on_complete:
            self._on_complete()
        elif self._next_state_factory:
            self.manager.set(self._next_state_factory())
        elif hasattr(self.manager, 'router') and self.manager.router:
            next_class = self.manager.router.get_next(self)
            if next_class:
                self.manager.set(next_class(self.manager))

    # ─── Draw ────────────────────────────────────────────────────────────────

    def draw(self, surface: pg.Surface) -> None:
        buf = self._scene_buffer
        buf.fill(self._bg_color)

        self._vortex.draw(buf)

        if self._phase == _Phase.FADE_IN:
            self._draw_fade_in(buf)
        elif self._phase in (
            _Phase.ORB_COLLAPSE, _Phase.ORB_LOOP, _Phase.DEMON_BURST,
            _Phase.ATTACK_LEFT, _Phase.ATTACK_RIGHT, _Phase.SPECIAL_TENTACLES,
            _Phase.REVERT,
        ):
            frames = self._get_current_frames()
            self._draw_phase_sprite(buf, frames)
            self._draw_flash(buf)
        elif self._phase == _Phase.LEVEL_INTRO:
            self._banner.draw(buf)

        self._camera.apply(buf, surface)

    def _draw_fade_in(self, surface: pg.Surface) -> None:
        if not self._frames_orb_collapse:
            return
        fade_dur = float(self._config.get("phases", {}).get("fade_in", {}).get("duration", 1.5))
        t = min(1.0, self._phase_timer / max(0.01, fade_dur))
        alpha = int(255 * _ease_in_out(t))

        frame = self._frames_orb_collapse[0]
        rect = frame.get_rect(center=(self._sw // 2, self._sh // 2))
        frame.set_alpha(alpha)
        surface.blit(frame, rect)
        frame.set_alpha(255)

    def _draw_phase_sprite(
        self, surface: pg.Surface, frames: list[pg.Surface]
    ) -> None:
        cx, cy = self._sw // 2, self._sh // 2

        if self._crossfading and self._prev_frame is not None:
            t = min(1.0, self._crossfade_timer / max(0.01, self._crossfade_duration))
            fade_out = int(255 * (1.0 - _ease_in_out(t)))
            rect = self._prev_frame.get_rect(center=(cx, cy))
            self._prev_frame.set_alpha(fade_out)
            surface.blit(self._prev_frame, rect)
            self._prev_frame.set_alpha(255)

            if frames:
                idx = min(self._frame_idx, len(frames) - 1)
                frame = frames[idx]
                rect = frame.get_rect(center=(cx, cy))
                fade_in = int(255 * _ease_in_out(t))
                frame.set_alpha(fade_in)
                surface.blit(frame, rect)
                frame.set_alpha(255)
        else:
            if not frames:
                return
            idx = min(self._frame_idx, len(frames) - 1)
            frame = frames[idx]
            rect = frame.get_rect(center=(cx, cy))
            surface.blit(frame, rect)

    def _draw_flash(self, surface: pg.Surface) -> None:
        if self._flash_alpha <= 0:
            return
        r, g, b = self._flash_color
        a = int(min(255.0, self._flash_alpha))
        self._overlay.fill((r, g, b, a))
        surface.blit(self._overlay, (0, 0))
