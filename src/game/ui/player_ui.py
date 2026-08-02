from typing import Callable, Optional
import math
import pygame as pg
from v3x_zulfiqar_gideon import AssetManager

class PlayerUI:
    def __init__(self):
        self.max_health = 100
        self.current_health = 100
        self.max_mana = 100.0
        self.current_mana = 100.0
        self.max_stamina = 100.0
        self.current_stamina = 100.0
        self.relics = 0
        self.distance: float = 0.0
        self.start_time = 0
        self.power_ups = []

        # ── Soul Harvest System ──────────────────────────────────────────────
        self.souls_collected = 0          # Souls gained *this level* (added on top of starting)
        self.soul_harvest_start = 9000    # Pre-existing souls from Kaelen's past hunts
        self.soul_harvest_target = 10000  # The contract's quota
        self._soul_pulse_timer: float = 0.0   # Countdown for glow pulse on soul gain
        self._soul_pulse_scale: float = 1.0   # Current pulse scale multiplier
        self._soul_last_total: int = 9000     # Track changes for pulse trigger
        self._soul_complete: bool = False      # True once quota is met
        self._soul_complete_callback: Optional[Callable[[], None]] = None    # Called once when quota is met
        # ─────────────────────────────────────────────────────────────────────

        # Load dragon HP bar sprite frames (0 = full, 7 = empty)
        self.health_frames = []
        for i in range(8):
            frame = AssetManager.get_texture(f"assets/dragonhpbar/health_bar_{i}.png")
            scaled = pg.transform.scale(frame, (frame.get_width() * 3, frame.get_height() * 3))
            self.health_frames.append(scaled)

        self.health_bar_pos = (20, 10)
        bar_h = self.health_frames[0].get_height()

        # Enlarged mana/stamina bars stacked directly under the health bar
        self.mana_bar_pos = (20, self.health_bar_pos[1] + bar_h + 8)
        self.stamina_bar_pos = (20, self.mana_bar_pos[1] + 32)
        self._resource_bar_size = (200, 16)

        self.souls_icon_pos = (20, self.stamina_bar_pos[1] + 38)
        self.relic_icon_pos = (20, self.stamina_bar_pos[1] + 82)
        self.power_up_icon_pos = (20, self.relic_icon_pos[1] + 48)
        self.time_pos = (pg.display.Info().current_w - 160, 20)

        self.souls_icon = self.load_icon("assets/free-undead-loot-pixel-art-icons/PNG/Transperent/Icon1.png", (36, 36))
        self.relic_icon = self.load_icon("assets/graphics/ui/relic_icon.png", (36, 36))
        self.power_up_icons = {
            "double_jump": self.load_icon("assets/graphics/ui/powerup_doublejump.png", (36, 36)),
            "speed_boost": self.load_icon("assets/graphics/ui/powerup_speed.png", (36, 36)),
            "invincibility": self.load_icon("assets/graphics/ui/powerup_invincible.png", (36, 36))
        }

        # Default pixel art image assets for Mana and Stamina bar icons
        self.time_icon = self._make_clock_icon((28, 28))
        self.dist_icon = self._make_flag_icon((28, 28))
        self.mana_icon = self.load_icon("assets/MAGE ICONS BIG PACk (by Batareya)/179.png", (36, 36))
        self.stamina_icon = self.load_icon("assets/Free-Undead-Skill-Pixel-Art-Icons/PNG/Icon24.png", (36, 36))

        self.font = AssetManager.get_font('assets/graphics/Darinia/Darinia.ttf', 30)
        self.medium_font = AssetManager.get_font('assets/graphics/Darinia/Darinia.ttf', 22)
        self.small_font = AssetManager.get_font('assets/graphics/Darinia/Darinia.ttf', 16)

        # Performance surface caches for low-end GPU/CPU hardware
        self._framed_icon_cache: dict = {}
        self._souls_label_surf: pg.Surface = self.small_font.render("SOULS", True, (140, 120, 180))
        self._relics_cache: tuple = (None, None)
        self._time_cache: tuple = (None, None)
        self._dist_cache: tuple = (None, None)
        self._soul_count_cache: tuple = (None, None)

        from typing import Optional, Any
        self.power_icons_manager: Optional[Any] = None
        try:
            from src.game.ui.power_icons_manager import PowerIconsManager
            self.power_icons_manager = PowerIconsManager()
        except Exception as e:
            print(f"[PlayerUI] Could not initialize PowerIconsManager: {e}")

    def load_icon(self, path, size):
        try:
            icon = AssetManager.get_texture(path)
            return pg.transform.scale(icon, size)
        except Exception:
            surface = pg.Surface(size, pg.SRCALPHA)
            surface.fill((255, 0, 255))
            return surface

    def _make_clock_icon(self, size):
        """Simple clock placeholder icon for the Time display."""
        surface = pg.Surface(size, pg.SRCALPHA)
        w, h = size
        center = (w // 2, h // 2)
        radius = min(w, h) // 2 - 2
        pg.draw.circle(surface, (255, 255, 255), center, radius, width=2)
        pg.draw.line(surface, (255, 255, 255), center, (center[0], center[1] - radius + 2), 2)
        pg.draw.line(surface, (255, 255, 255), center, (center[0] + radius // 2, center[1]), 2)
        return surface

    def _make_flag_icon(self, size):
        """Simple checkpoint-flag placeholder icon for the Distance display."""
        surface = pg.Surface(size, pg.SRCALPHA)
        w, h = size
        pole_x = 3
        pg.draw.line(surface, (255, 255, 255), (pole_x, 1), (pole_x, h - 1), 2)
        flag_points = [(pole_x, 2), (w - 2, h * 0.32), (pole_x, h * 0.58)]
        pg.draw.polygon(surface, (255, 255, 255), flag_points)
        return surface

    def _make_mana_icon(self, size):
        """Small droplet placeholder icon for the Mana bar."""
        surface = pg.Surface(size, pg.SRCALPHA)
        w, h = size
        points = [(w / 2, 0), (w - 1, h * 0.62), (w / 2, h - 1), (1, h * 0.62)]
        pg.draw.polygon(surface, (100, 200, 255), points)
        return surface

    def _make_stamina_icon(self, size):
        """Small lightning/bolt placeholder icon for the Stamina bar."""
        surface = pg.Surface(size, pg.SRCALPHA)
        w, h = size
        points = [
            (w * 0.55, 0), (w * 0.15, h * 0.55), (w * 0.50, h * 0.55),
            (w * 0.40, h),       (w * 0.85, h * 0.42), (w * 0.50, h * 0.42),
        ]
        pg.draw.polygon(surface, (255, 220, 80), points)
        return surface

    def start_timer(self):
        self.start_time = pg.time.get_ticks()
    
    def get_elapsed_time(self):
        if self.start_time == 0:
            return 0
        return (pg.time.get_ticks() - self.start_time) / 1000.0
    
    def format_time(self, seconds):
        mins = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{mins:02d}:{secs:02d}"
    
    def update_health(self, amount):
        self.current_health = max(0, min(self.max_health, self.current_health + amount))
    
    def add_relic(self, amount=1):
        self.relics += amount
    
    def add_power_up(self, power_up_type, duration):
        self.power_ups.append({
            "type": power_up_type,
            "start_time": pg.time.get_ticks(),
            "duration": duration
        })
    
    @property
    def current_soul_total(self) -> int:
        """Returns starting souls + souls reaped in the current level."""
        return self.soul_harvest_start + self.souls_collected

    def add_souls(self, count: int) -> None:
        """Add souls and trigger pulse effect + callback if quota met."""
        self.souls_collected += count
        self._soul_pulse_timer = 0.6  # Pulse for 0.6s
        
        # Check quota completion
        if not self._soul_complete and self.current_soul_total >= self.soul_harvest_target:
            self._soul_complete = True
            if self._soul_complete_callback is not None:
                self._soul_complete_callback()

    def update(self) -> None:
        """Update UI timers (e.g. pulse decay)."""
        current_time = pg.time.get_ticks()
        self.power_ups = [pu for pu in self.power_ups 
                         if current_time - pu["start_time"] < pu["duration"]]

        # Decay soul pulse animation
        if self._soul_pulse_timer > 0:
            self._soul_pulse_timer = max(0.0, self._soul_pulse_timer - 0.016)  # ~60fps
            # Ease out the scale
            t = self._soul_pulse_timer / 0.6
            self._soul_pulse_scale = 1.0 + 0.25 * t
    
    def _crop_to_circle(self, surf: pg.Surface) -> pg.Surface:
        """Crop image into a smooth circle."""
        w, h = surf.get_size()
        r = min(w, h) // 2
        mask = pg.Surface((w, h), pg.SRCALPHA).convert_alpha()
        pg.draw.circle(mask, (255, 255, 255, 255), (w // 2, h // 2), r)

        result = pg.Surface((w, h), pg.SRCALPHA).convert_alpha()
        result.blit(surf, (0, 0))
        result.blit(mask, (0, 0), special_flags=pg.BLEND_RGBA_MULT)
        return result

    def _get_framed_icon_surface(self, icon_surf: pg.Surface, border_color=(160, 60, 255), opacity=255) -> pg.Surface:
        key = (id(icon_surf), tuple(border_color[:3]), opacity)
        if key in self._framed_icon_cache:
            return self._framed_icon_cache[key]

        w, h = icon_surf.get_size()
        circle_img = self._crop_to_circle(icon_surf)

        container = pg.Surface((w + 8, h + 8), pg.SRCALPHA).convert_alpha()
        cx, cy = (w + 8) // 2, (h + 8) // 2
        r = w // 2 + 1

        glow_alpha = min(220, opacity)
        pg.draw.circle(container, (*border_color[:3], glow_alpha // 2), (cx, cy), r + 3, width=2)
        pg.draw.circle(container, (*border_color[:3], glow_alpha), (cx, cy), r + 1, width=2)
        pg.draw.circle(container, (20, 20, 35, glow_alpha), (cx, cy), r, width=1)

        icon_alpha = circle_img.copy()
        if opacity < 255:
            alpha_mask = pg.Surface(icon_alpha.get_size(), pg.SRCALPHA).convert_alpha()
            alpha_mask.fill((255, 255, 255, opacity))
            icon_alpha.blit(alpha_mask, (0, 0), special_flags=pg.BLEND_RGBA_MULT)

        container.blit(icon_alpha, (4, 4))
        self._framed_icon_cache[key] = container
        return container

    def _draw_framed_icon(self, surface, icon_surf, pos, border_color=(160, 60, 255), opacity=255):
        """Draw an enlarged circular icon with a vibrant purple glowing border frame."""
        w, h = icon_surf.get_size()
        container = self._get_framed_icon_surface(icon_surf, border_color, opacity)
        surface.blit(container, (pos[0] - 4, pos[1] - 4))
        return pg.Rect(pos[0] - 4, pos[1] - 4, w + 8, h + 8)

    def _draw_resource_bar(self, surface, pos, icon, current, maximum, fill_color, bg_color, border_color=(160, 60, 255)):
        """Draw an enlarged framed icon + outlined resource bar."""
        is_active = (current > 0.0) if maximum > 0 else True
        opacity = 255 if is_active else 80

        icon_rect = self._draw_framed_icon(surface, icon, pos, border_color=border_color, opacity=opacity)
        
        ratio = max(0.0, min(1.0, current / maximum)) if maximum > 0 else 0.0
        
        # Position bar cleanly aligned right of the framed icon
        bar_x = icon_rect.right + 10
        bar_y = pos[1] + (icon.get_height() // 2) - 8
        bar_w, bar_h = self._resource_bar_size
        
        # Background bar
        bg_rect = pg.Rect(bar_x, bar_y, bar_w, bar_h)
        pg.draw.rect(surface, bg_color, bg_rect, border_radius=4)
        
        # Fill bar
        if ratio > 0:
            fill_w = max(2, int(bar_w * ratio))
            fill_rect = pg.Rect(bar_x, bar_y, fill_w, bar_h)
            pg.draw.rect(surface, fill_color, fill_rect, border_radius=4)
            
            # Subtle top highlight
            highlight_rect = pg.Rect(bar_x, bar_y, fill_w, bar_h // 2)
            highlight_color = (min(255, fill_color[0] + 50), min(255, fill_color[1] + 50), min(255, fill_color[2] + 50))
            pg.draw.rect(surface, highlight_color, highlight_rect, border_radius=4)
            
        # Border
        pg.draw.rect(surface, (200, 200, 220), bg_rect, width=1, border_radius=4)

    def draw(self, surface):
        if self.start_time == 0:
            self.start_time = pg.time.get_ticks()

        # Small idle float offset
        float_y = int(math.sin(pg.time.get_ticks() * 0.003) * 2)

        # ── Health Bar ───────────────────────────────────────────────────────
        health_ratio = max(0.0, min(1.0, self.current_health / self.max_health))
        frame_idx = 7 - int(round(health_ratio * 7))
        frame_idx = max(0, min(7, frame_idx))
        hp_frame = self.health_frames[frame_idx]
        hp_pos = (self.health_bar_pos[0], self.health_bar_pos[1] + float_y)
        surface.blit(hp_frame, hp_pos)

        # ── Mana Bar ─────────────────────────────────────────────────────────
        self._draw_resource_bar(
            surface, (self.mana_bar_pos[0], self.mana_bar_pos[1] + float_y),
            self.mana_icon, self.current_mana, self.max_mana,
            fill_color=(0, 180, 255), bg_color=(15, 25, 45), border_color=(0, 200, 255)
        )

        # ── Stamina Bar ──────────────────────────────────────────────────────
        self._draw_resource_bar(
            surface, (self.stamina_bar_pos[0], self.stamina_bar_pos[1] + float_y),
            self.stamina_icon, self.current_stamina, self.max_stamina,
            fill_color=(255, 210, 40), bg_color=(35, 30, 15), border_color=(255, 220, 80)
        )

        # ── Soul Harvest Display ─────────────────────────────────────────────
        self._draw_soul_harvest(surface, float_y)

        # Draw Relics counter with golden glowing frame
        relic_y = self.relic_icon_pos[1] + float_y
        self._draw_framed_icon(surface, self.relic_icon, (self.relic_icon_pos[0], relic_y), border_color=(255, 215, 0), opacity=255)
        if self._relics_cache[0] != self.relics:
            relic_surf = self.medium_font.render(f"x {self.relics}", True, (255, 255, 255))
            self._relics_cache = (self.relics, relic_surf)
        if self._relics_cache[1] is not None:
            surface.blit(self._relics_cache[1], (self.relic_icon_pos[0] + 44, relic_y + 8))
        
        y_offset = 0
        for power_up in self.power_ups:
            icon = self.power_up_icons.get(power_up["type"], None)
            if icon:
                surface.blit(icon, (self.power_up_icon_pos[0], self.power_up_icon_pos[1] + y_offset + float_y))
                elapsed = pg.time.get_ticks() - power_up["start_time"]
                remaining = max(0, power_up["duration"] - elapsed)
                percent = int((remaining / power_up["duration"]) * 100)
                time_text = self.small_font.render(f"{percent}%", True, (255, 255, 255))
                surface.blit(time_text, (self.power_up_icon_pos[0] + 35, self.power_up_icon_pos[1] + y_offset + 4))
                y_offset += 35
        
        elapsed_seconds = self.get_elapsed_time()
        if self._time_cache[0] != elapsed_seconds:
            time_surf = self.small_font.render(f"Time: {self.format_time(elapsed_seconds)}", True, (255, 255, 255))
            self._time_cache = (elapsed_seconds, time_surf)
        time_text = self._time_cache[1]
        time_rect = time_text.get_rect(topright=(self.time_pos[0], self.time_pos[1] + float_y))
        time_icon_rect = self.time_icon.get_rect(midright=(time_rect.left - 8, time_rect.centery))
        surface.blit(self.time_icon, time_icon_rect)
        surface.blit(time_text, time_rect)

        # Distance display (right below time)
        dist_int = int(self.distance)
        if self._dist_cache[0] != dist_int:
            dist_surf = self.small_font.render(f"Dist: {dist_int}", True, (255, 255, 255))
            self._dist_cache = (dist_int, dist_surf)
        dist_text = self._dist_cache[1]
        dist_rect = dist_text.get_rect(topright=(self.time_pos[0], time_rect.bottom + 4))
        dist_icon_rect = self.dist_icon.get_rect(midright=(dist_rect.left - 8, dist_rect.centery))
        surface.blit(self.dist_icon, dist_icon_rect)
        surface.blit(dist_text, dist_rect)

        # Draw Power HUD Icons overlay if available
        if self.power_icons_manager is not None:
            self.power_icons_manager.draw(
                surface,
                current_stamina=self.current_stamina,
                max_stamina=self.max_stamina,
                current_mana=getattr(self, "current_mana", 100.0),
                max_mana=getattr(self, "max_mana", 100.0)
            )

    def _draw_soul_harvest(self, surface: pg.Surface, float_y: int) -> None:
        souls_y = self.souls_icon_pos[1] + float_y
        total = self.current_soul_total
        target = self.soul_harvest_target
        ratio = min(1.0, total / target) if target > 0 else 0.0

        if self._soul_complete:
            bar_fill = (255, 215, 50)
            bar_border = (255, 200, 0)
            text_color = (255, 240, 180)
        elif ratio >= 0.95:
            bar_fill = (200, 40, 40)
            bar_border = (255, 60, 60)
            text_color = (255, 180, 180)
        elif ratio >= 0.80:
            bar_fill = (200, 140, 30)
            bar_border = (230, 170, 50)
            text_color = (255, 220, 160)
        else:
            bar_fill = (120, 50, 200)
            bar_border = (160, 60, 255)
            text_color = (220, 200, 255)

        pulse_alpha = 0
        if self._soul_pulse_timer > 0:
            pulse_alpha = int(180 * (self._soul_pulse_timer / 0.6))

        icon_border = bar_border if self._soul_pulse_timer <= 0 else (255, 220, 80)
        self._draw_framed_icon(
            surface, self.souls_icon,
            (self.souls_icon_pos[0], souls_y),
            border_color=icon_border, opacity=255
        )

        bar_x = self.souls_icon_pos[0] + 50
        bar_w = 180
        bar_h = 14
        bar_y_center = souls_y + 18 - bar_h // 2

        bg_rect = pg.Rect(bar_x, bar_y_center, bar_w, bar_h)
        pg.draw.rect(surface, (15, 12, 25), bg_rect, border_radius=4)

        if ratio > 0:
            fill_w = max(2, int(bar_w * ratio))
            fill_rect = pg.Rect(bar_x, bar_y_center, fill_w, bar_h)
            pg.draw.rect(surface, bar_fill, fill_rect, border_radius=4)

            top_rect = pg.Rect(bar_x, bar_y_center, fill_w, bar_h // 2)
            shimmer = (*[min(255, c + 40) for c in bar_fill[:3]],)
            pg.draw.rect(surface, shimmer, top_rect, border_radius=4)

        if pulse_alpha > 0:
            glow_surf = pg.Surface((bar_w + 6, bar_h + 6), pg.SRCALPHA).convert_alpha()
            glow_surf.fill((255, 220, 80, pulse_alpha))
            surface.blit(glow_surf, (bar_x - 3, bar_y_center - 3))

        pg.draw.rect(surface, bar_border, bg_rect, width=1, border_radius=4)

        label_text = self.small_font.render("SOULS", True, (140, 120, 180))
        surface.blit(label_text, (bar_x, bar_y_center + bar_h + 2))