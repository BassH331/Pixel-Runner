import pygame as pg

class PlayerUI:
    def __init__(self):
        self.max_health = 100
        self.current_health = 100
        self.relics = 0
        self.start_time = 0
        self.power_ups = []
        
        self.health_bar_width = 200
        self.health_bar_height = 20
        self.health_bar_pos = (20, 20)
        self.relic_icon_pos = (20, 50)
        self.power_up_icon_pos = (20, 80)
        self.time_pos = (pg.display.Info().current_w - 150, 20)
        
        self.relic_icon = self.load_icon("Resources/graphics/ui/relic_icon.png", (30, 30))
        self.power_up_icons = {
            "double_jump": self.load_icon("Resources/graphics/ui/powerup_doublejump.png", (30, 30)),
            "speed_boost": self.load_icon("Resources/graphics/ui/powerup_speed.png", (30, 30)),
            "invincibility": self.load_icon("Resources/graphics/ui/powerup_invincible.png", (30, 30))
        }
        
        self.font = pg.font.Font('Resources/font/Pixeltype.ttf', 30)
    
    def load_icon(self, path, size):
        try:
            icon = pg.image.load(path).convert_alpha()
            return pg.transform.scale(icon, size)
        except:
            surface = pg.Surface(size, pg.SRCALPHA)
            pg.draw.rect(surface, (255, 0, 0), (0, 0, *size))
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
    
    def draw(self, surface):
        health_ratio = self.current_health / self.max_health
        health_fill_width = int(self.health_bar_width * health_ratio)
        
        pg.draw.rect(surface, (50, 50, 50), 
                    (*self.health_bar_pos, self.health_bar_width, self.health_bar_height))
        health_color = (255 * (1 - health_ratio), 255 * health_ratio, 0)
        pg.draw.rect(surface, health_color, 
                    (*self.health_bar_pos, health_fill_width, self.health_bar_height))
        pg.draw.rect(surface, (255, 255, 255), 
                    (*self.health_bar_pos, self.health_bar_width, self.health_bar_height), 2)
        
        health_text = self.font.render(f"HP: {self.current_health}/{self.max_health}", True, (255, 255, 255))
        surface.blit(health_text, (self.health_bar_pos[0] + self.health_bar_width + 10, self.health_bar_pos[1]))
        
        surface.blit(self.relic_icon, self.relic_icon_pos)
        relic_text = self.font.render(f"x {self.relics}", True, (255, 255, 255))
        surface.blit(relic_text, (self.relic_icon_pos[0] + 35, self.relic_icon_pos[1]))
        
        y_offset = 0
        for power_up in self.power_ups:
            icon = self.power_up_icons.get(power_up["type"], None)
            if icon:
                surface.blit(icon, (self.power_up_icon_pos[0], self.power_up_icon_pos[1] + y_offset))
                elapsed = pg.time.get_ticks() - power_up["start_time"]
                remaining = max(0, power_up["duration"] - elapsed)
                percent = int((remaining / power_up["duration"]) * 100)
                time_text = self.font.render(f"{percent}%", True, (255, 255, 255))
                surface.blit(time_text, (self.power_up_icon_pos[0] + 35, self.power_up_icon_pos[1] + y_offset))
                y_offset += 35
        
        elapsed_seconds = self.get_elapsed_time()
        time_text = self.font.render(f"Time: {self.format_time(elapsed_seconds)}", True, (255, 255, 255))
        time_rect = time_text.get_rect(topright=self.time_pos)
        surface.blit(time_text, time_rect)