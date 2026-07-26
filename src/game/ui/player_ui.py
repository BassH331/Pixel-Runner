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

        self.souls_collected = 0
        self.souls_icon_pos = (20, self.stamina_bar_pos[1] + 38)
        self.relic_icon_pos = (150, self.stamina_bar_pos[1] + 38)
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
        except:
            surface = pg.Surface(size, pg.SRCALPHA)
            pg.draw.rect(surface, (255, 0, 0), (0, 0, *size))
            return surface

    def _make_clock_icon(self, size):
        """Simple clock-face placeholder icon (circle + hands) for the Time display."""
        surface = pg.Surface(size, pg.SRCALPHA)
        w, h = size
        center = (w // 2, h // 2)
        radius = min(w, h) // 2 - 1
        pg.draw.circle(surface, (255, 255, 255), center, radius, width=2)
        # Hour hand (pointing up-right) and minute hand (pointing up)
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
        pg.draw.polygon(surface, (90, 160, 255), points)
        return surface

    def _make_stamina_icon(self, size):
        """Small lightning-bolt placeholder icon for the Stamina bar."""
        surface = pg.Surface(size, pg.SRCALPHA)
        w, h = size
        points = [(w * 0.55, 0), (0, h * 0.6), (w * 0.4, h * 0.6), (w * 0.35, h), (w, h * 0.35), (w, h * 0.35)]
        pg.draw.polygon(surface, (140, 230, 90), points)
        return surface

    def start_timer(self):
        self.start_time = pg.time.get_ticks()
    
    def get_elapsed_time(self):
        return (pg.time.get_ticks() - self.start_time) // 1000
    
    def format_time(self, seconds):
        minutes = seconds // 60
        seconds = seconds % 60
        return f"{minutes:02d}:{seconds:02d}"
    
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
    
    def update(self):
        current_time = pg.time.get_ticks()
        self.power_ups = [pu for pu in self.power_ups 
                         if current_time - pu["start_time"] < pu["duration"]]
    
    def _crop_to_circle(self, surf: pg.Surface) -> pg.Surface:
        """Crop image into a smooth circle."""
        w, h = surf.get_size()
        r = min(w, h) // 2
        mask = pg.Surface((w, h), pg.SRCALPHA)
        pg.draw.circle(mask, (255, 255, 255, 255), (w // 2, h // 2), r)

        result = pg.Surface((w, h), pg.SRCALPHA)
        result.blit(surf, (0, 0))
        result.blit(mask, (0, 0), special_flags=pg.BLEND_RGBA_MULT)
        return result

    def _draw_framed_icon(self, surface, icon_surf, pos, border_color=(160, 60, 255), opacity=255):
        """Draw an enlarged circular icon with a vibrant purple glowing border frame."""
        w, h = icon_surf.get_size()
        circle_img = self._crop_to_circle(icon_surf)

        container = pg.Surface((w + 8, h + 8), pg.SRCALPHA)
        cx, cy = (w + 8) // 2, (h + 8) // 2
        r = w // 2 + 1

        # Glowing purple frame rings
        glow_alpha = min(220, opacity)
        pg.draw.circle(container, (*border_color[:3], glow_alpha // 2), (cx, cy), r + 3, width=2)
        pg.draw.circle(container, (*border_color[:3], glow_alpha), (cx, cy), r + 1, width=2)
        pg.draw.circle(container, (20, 20, 35, glow_alpha), (cx, cy), r, width=1)

        # Apply per-pixel alpha opacity for active/inactive state
        icon_alpha = circle_img.copy()
        if opacity < 255:
            alpha_mask = pg.Surface(icon_alpha.get_size(), pg.SRCALPHA)
            alpha_mask.fill((255, 255, 255, opacity))
            icon_alpha.blit(alpha_mask, (0, 0), special_flags=pg.BLEND_RGBA_MULT)

        container.blit(icon_alpha, (4, 4))
        surface.blit(container, (pos[0] - 4, pos[1] - 4))
        return pg.Rect(pos[0] - 4, pos[1] - 4, w + 8, h + 8)

    def _draw_resource_bar(self, surface, pos, icon, current, maximum, fill_color, bg_color, border_color=(160, 60, 255)):
        """Draw an enlarged framed icon + outlined resource bar."""
        is_active = (current > 0.0) if maximum > 0 else True
        opacity = 255 if is_active else 80

        icon_rect = self._draw_framed_icon(surface, icon, pos, border_color=border_color, opacity=opacity)

        bar_x = icon_rect.right + 8
        bar_w, bar_h = self._resource_bar_size
        bg_rect = pg.Rect(bar_x, pos[1] + (icon_rect.height - bar_h) // 2, bar_w, bar_h)
        pg.draw.rect(surface, bg_color, bg_rect, border_radius=4)

        ratio = max(0.0, min(1.0, current / maximum)) if maximum > 0 else 0.0
        if ratio > 0:
            fill_rect = pg.Rect(bar_x, bg_rect.y, int(bar_w * ratio), bar_h)
            pg.draw.rect(surface, fill_color, fill_rect, border_radius=4)
        pg.draw.rect(surface, (0, 0, 0, 140), bg_rect, width=1, border_radius=4)

    def draw(self, surface):
        import math
        now = pg.time.get_ticks()
        float_y = int(math.sin(now * 0.0035) * 2.5)  # Subtle 2.5px floating motion for HUD icons

        # Update HUD icons dynamically if configured in power_icons_editor (Enlarged 36x36 sizes)
        if self.power_icons_manager:
            mana_surf = self.power_icons_manager.icon_surfaces.get("MANA_BAR_ICON")
            if mana_surf:
                self.mana_icon = pg.transform.smoothscale(mana_surf, (36, 36))
            stamina_surf = self.power_icons_manager.icon_surfaces.get("STAMINA_BAR_ICON")
            if stamina_surf:
                self.stamina_icon = pg.transform.smoothscale(stamina_surf, (36, 36))
            souls_surf = self.power_icons_manager.icon_surfaces.get("SOULS_COUNTER_ICON")
            if souls_surf:
                self.souls_icon = pg.transform.smoothscale(souls_surf, (36, 36))
            relic_surf = self.power_icons_manager.icon_surfaces.get("RELIC_COUNTER_ICON")
            if relic_surf:
                self.relic_icon = pg.transform.smoothscale(relic_surf, (36, 36))

        # Select the correct dragon HP bar frame based on health ratio
        health_ratio = max(0.0, min(1.0, self.current_health / self.max_health))
        frame_index = round((1.0 - health_ratio) * 7)  # 0 = full, 7 = empty
        frame_index = max(0, min(7, frame_index))
        surface.blit(self.health_frames[frame_index], self.health_bar_pos)

        self._draw_resource_bar(
            surface, (self.mana_bar_pos[0], self.mana_bar_pos[1] + float_y), self.mana_icon,
            self.current_mana, self.max_mana,
            fill_color=(70, 130, 220), bg_color=(20, 25, 45),
            border_color=(160, 60, 255)
        )
        self._draw_resource_bar(
            surface, (self.stamina_bar_pos[0], self.stamina_bar_pos[1] + float_y), self.stamina_icon,
            self.current_stamina, self.max_stamina,
            fill_color=(110, 200, 70), bg_color=(20, 35, 20),
            border_color=(160, 60, 255)
        )

        # Draw Souls Collected counter with purple glowing frame
        souls_y = self.souls_icon_pos[1] + float_y
        self._draw_framed_icon(surface, self.souls_icon, (self.souls_icon_pos[0], souls_y), border_color=(160, 60, 255), opacity=255)
        souls_text = self.medium_font.render(f"x {self.souls_collected}", True, (240, 220, 255))
        surface.blit(souls_text, (self.souls_icon_pos[0] + 44, souls_y + 8))

        # Draw Relics counter with purple glowing frame
        relic_y = self.relic_icon_pos[1] + float_y
        self._draw_framed_icon(surface, self.relic_icon, (self.relic_icon_pos[0], relic_y), border_color=(255, 215, 0), opacity=255)
        relic_text = self.medium_font.render(f"x {self.relics}", True, (255, 255, 255))
        surface.blit(relic_text, (self.relic_icon_pos[0] + 44, relic_y + 8))
        
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
        time_text = self.small_font.render(f"Time: {self.format_time(elapsed_seconds)}", True, (255, 255, 255))
        time_rect = time_text.get_rect(topright=(self.time_pos[0], self.time_pos[1] + float_y))
        time_icon_rect = self.time_icon.get_rect(midright=(time_rect.left - 8, time_rect.centery))
        surface.blit(self.time_icon, time_icon_rect)
        surface.blit(time_text, time_rect)

        # Distance display (right below time)
        dist_text = self.small_font.render(f"Dist: {int(self.distance)}", True, (255, 255, 255))
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