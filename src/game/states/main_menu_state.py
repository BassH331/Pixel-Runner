import os
import sys
import math
import threading
import pygame as pg
from v3x_zulfiqar_gideon import State, AssetManager

class MainMenuState(State):
    """Refined Main Menu matching the game's obsidian and gold mythology aesthetic."""

    def __init__(self, manager):
        super().__init__(manager)
        self.width = pg.display.get_surface().get_width()
        self.height = pg.display.get_surface().get_height()

        # Background Animation
        self.frames = []
        self.current_frame_index = 0
        self.frame_timer = 0.0
        self.frame_delay = 80.0  # ms
        self.loading_thread = None
        
        # Start loading in background
        self.loading_progress = 0.0
        self.converted_frames = False
        self.loading_thread = threading.Thread(target=self.load_frames, daemon=True)
        self.loading_thread.start()
        
        # Fallback/Loading placeholder
        self.bg_placeholder = pg.Surface((self.width, self.height))
        self.bg_placeholder.fill((12, 10, 20))

        # ── Ambient Floating Particles (Embers) ──────────────────────────────
        self._particles = [
            {
                "x": float((i * 97) % self.width),
                "y": float((i * 61) % self.height),
                "speed_x": 10.0 + (i % 4) * 6.0,
                "speed_y": -14.0 - (i % 3) * 7.0,
                "size": 2 + (i % 3),
                "alpha_phase": (i * 0.7),
            }
            for i in range(30)
        ]

        # ── Typography & Title ───────────────────────────────────────────────
        self.title_font = AssetManager.get_font(
            "assets/font/Abaddon Bold.ttf", 96
        )
        self.subtitle_font = AssetManager.get_font(
            "assets/font/Abaddon Bold.ttf", 28
        )
        self.prompt_font = AssetManager.get_font(
            "assets/font/Abaddon Bold.ttf", 28
        )

        self.title_text = "THE UNPAID DEBT"
        self.subtitle_text = "A PACT IN THE SHADOWS"

        # Buttons (if custom buttons are used)
        self.buttons = []
        
        # Input Cooldown & Transition
        self.input_cooldown = 0.4
        self.time_entered: float = 0.0
        self.is_starting: bool = False
        self.start_alpha: float = 0.0

    def load_frames(self):
        from v3x_zulfiqar_gideon import SettingsManager
        quality = SettingsManager().get("graphics_quality")
        bg_dir = "assets/graphics/background images/intro_bg"
        try:
            if os.path.exists(bg_dir):
                frame_files = sorted([f for f in os.listdir(bg_dir) if f.endswith(".gif") or f.endswith(".png")])
                if quality == "low":
                    frame_files = frame_files[:1]
                elif quality == "medium":
                    frame_files = frame_files[::4]
                    
                total_frames = len(frame_files)
                loaded_frames = []
                for i, f in enumerate(frame_files):
                    try:
                        img = pg.image.load(os.path.join(bg_dir, f))
                        img = pg.transform.scale(img, (self.width, self.height))
                        loaded_frames.append(img)
                    except Exception as e:
                        print(f"Error loading frame {f}: {e}")
                    
                    self.loading_progress = (i + 1) / max(1, total_frames)
                
                self.frames = loaded_frames
                print(f"Loaded {len(self.frames)} frames in background (Quality: {quality}).")
            else:
                self.loading_progress = 1.0
        except Exception as e:
            print(f"Failed to load background frames: {e}")
            self.loading_progress = 1.0

    def start_game(self):
        if not self.is_starting:
            self.is_starting = True

    def exit_game(self):
        self.manager.set_router(None)
        pg.quit()
        sys.exit()
        
    def on_enter(self):
        self.time_entered = pg.time.get_ticks() / 1000.0
        self.is_starting = False
        self.start_alpha = 0.0
        if hasattr(self.manager, 'audio_manager') and self.manager.audio_manager:
            self.manager.audio_manager.play_music("background_music", volume=0.5)

    def handle_event(self, event):
        for btn in self.buttons:
            btn.handle_event(event)
            
        current_time = pg.time.get_ticks() / 1000.0
        if current_time - self.time_entered > self.input_cooldown:
            if event.type == pg.KEYDOWN and event.key in (pg.K_SPACE, pg.K_RETURN, pg.K_e, pg.K_x):
                self.start_game()
            elif event.type == pg.JOYBUTTONDOWN and event.button in (0, 1, 6, 7):
                self.start_game()

    def update(self, dt):
        dt_sec = dt / 1000.0 if dt > 0.5 else dt

        # Convert frames to display format on main thread when thread finishes
        if self.loading_thread and not self.loading_thread.is_alive() and not self.converted_frames:
            self.frames = [f.convert() for f in self.frames]
            self.converted_frames = True

        # Update Background Animation
        if self.frames:
            self.frame_timer += dt
            if self.frame_timer >= self.frame_delay:
                self.frame_timer = 0.0
                self.current_frame_index = (self.current_frame_index + 1) % len(self.frames)

        # Update floating particles
        for p in self._particles:
            p["x"] += p["speed_x"] * dt_sec
            p["y"] += p["speed_y"] * dt_sec
            if p["x"] > self.width + 10:
                p["x"] = -10
            if p["y"] < -10:
                p["y"] = float(self.height + 10)

        for btn in self.buttons:
            btn.update(dt)

        # Transition to StoryState
        if self.is_starting:
            self.start_alpha += 480.0 * dt_sec
            if self.start_alpha >= 255.0:
                self.finish("PLAY")

    def draw(self, surface):
        if self.frames:
            surface.blit(self.frames[self.current_frame_index], (0, 0))
        else:
            surface.blit(self.bg_placeholder, (0, 0))
            
        # Dark atmospheric overlay
        vignette = pg.Surface((self.width, self.height), pg.SRCALPHA)
        vignette.fill((8, 6, 14, 140))
        surface.blit(vignette, (0, 0))

        # Floating ambient embers
        ticks = pg.time.get_ticks()
        for p in self._particles:
            p_pulse = (math.sin(ticks * 0.005 + p["alpha_phase"]) + 1.0) * 0.5
            p_alpha = int(100 + 110 * p_pulse)
            glow = pg.Surface((14, 14), pg.SRCALPHA)
            pg.draw.circle(glow, (255, 180, 40, int(p_alpha * 0.45)), (7, 7), 6)
            pg.draw.circle(glow, (255, 220, 100, p_alpha), (7, 7), p["size"])
            surface.blit(glow, (int(p["x"]) - 7, int(p["y"]) - 7))

        # ── Render Title Banner with Gold Typography ─────────────────────────
        title_cx = self.width // 2
        title_cy = int(self.height * 0.32)

        # Title Drop Shadow
        shd_surf = self.title_font.render(self.title_text, True, (0, 0, 0))
        surface.blit(shd_surf, shd_surf.get_rect(center=(title_cx + 4, title_cy + 4)))
        
        # Title Glow & Main Gold Color
        title_surf = self.title_font.render(self.title_text, True, (255, 215, 80))
        surface.blit(title_surf, title_surf.get_rect(center=(title_cx, title_cy)))

        # Subtitle Tag
        sub_shd = self.subtitle_font.render(self.subtitle_text, True, (0, 0, 0))
        surface.blit(sub_shd, sub_shd.get_rect(center=(title_cx + 2, title_cy + 60)))

        sub_surf = self.subtitle_font.render(self.subtitle_text, True, (210, 180, 120))
        surface.blit(sub_surf, sub_surf.get_rect(center=(title_cx, title_cy + 58)))

        # ── Buttons (if any) ─────────────────────────────────────────────────
        for btn in self.buttons:
            btn.draw(surface)
            
        # ── Pulsing Start Prompt (Obsidian Plate + Gold Text) ────────────────
        prompt_pulse = (math.sin(ticks * 0.006) + 1.0) * 0.5
        prompt_alpha = int(150 + 105 * prompt_pulse)

        prompt_str = "[ PRESS SPACE OR ENTER TO BEGIN ]"
        pw, ph = self.prompt_font.size(prompt_str)
        box_w = pw + 60
        box_h = ph + 24
        box_x = (self.width - box_w) // 2
        box_y = self.height - 110

        # Obsidian box behind prompt
        prompt_box = pg.Surface((box_w, box_h), pg.SRCALPHA)
        prompt_box.fill((10, 6, 18, int(prompt_alpha * 0.75)))
        pg.draw.rect(
            prompt_box,
            (255, 190, 50, int(prompt_alpha * 0.6)),
            (0, 0, box_w, box_h),
            width=2,
            border_radius=8,
        )
        surface.blit(prompt_box, (box_x, box_y))

        # Text render
        p_shd = self.prompt_font.render(prompt_str, True, (0, 0, 0))
        surface.blit(p_shd, p_shd.get_rect(center=(self.width // 2 + 2, box_y + box_h // 2 + 2)))

        p_txt = self.prompt_font.render(prompt_str, True, (255, 220, 100))
        surface.blit(p_txt, p_txt.get_rect(center=(self.width // 2, box_y + box_h // 2)))

        # ── Smooth Exit Fade Overlay ─────────────────────────────────────────
        if self.is_starting and self.start_alpha > 0.0:
            fade_surf = pg.Surface((self.width, self.height), pg.SRCALPHA)
            fade_surf.fill((0, 0, 0, int(min(255.0, self.start_alpha))))
            surface.blit(fade_surf, (0, 0))
