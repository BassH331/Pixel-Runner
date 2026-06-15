#!/usr/bin/env python3
import os
import sys
import pygame as pg
from unittest.mock import MagicMock
from typing import Any

# Adjust python search path to ensure we can load src
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Mock audio manager for compatibility with entity initializations
mock_audio = MagicMock()

# Initialize Pygame display and subsystems
pg.init()
pg.font.init()
SCREEN_W, SCREEN_H = 1280, 720
screen = pg.display.set_mode((SCREEN_W, SCREEN_H))
pg.display.set_caption("Runner: Graphical Hitbox, Dimension & Floor Editor")

# Import the game entities and registry
from src.game.entities.hitbox_registry import HitboxRegistry, HitboxMargins
from src.game.entities.player import Player
from src.game.entities.skeleton import Skeleton
from src.game.entities.enemy import Enemy
from src.game.entities.wizard_npc import WizardNPC
from src.game.entities.generic_npc import GenericNPC

# Load fonts
try:
    title_font = pg.font.Font("assets/graphics/Darinia/Darinia.ttf", 36)
    ui_font = pg.font.Font("assets/graphics/Darinia/Darinia.ttf", 20)
    help_font = pg.font.Font(None, 22)
except Exception:
    title_font = pg.font.SysFont("Arial", 32, bold=True)
    ui_font = pg.font.SysFont("Arial", 18)
    help_font = pg.font.SysFont("Arial", 16)

# Visual Constants
PREVIEW_SCREEN_BOTTOM = 550
PREVIEW_CENTER_X = 600


class Slider:
    def __init__(self, label, x, y, w, min_val, max_val, current_val):
        self.label = label
        self.rect = pg.Rect(x, y, w, 10)
        self.handle_r = 10
        self.min_val = min_val
        self.max_val = max_val
        self.val = current_val
        self.dragging = False

    def get_handle_pos(self):
        if self.max_val == self.min_val:
            ratio = 0.0
        else:
            ratio = (self.val - self.min_val) / (self.max_val - self.min_val)
        return int(self.rect.x + ratio * self.rect.width), self.rect.centery

    def draw(self, surface, font):
        # Label and current value
        txt = font.render(f"{self.label}: {self.val} px", True, (240, 240, 240))
        surface.blit(txt, (self.rect.x, self.rect.y - 25))

        # Slider track
        pg.draw.rect(surface, (60, 60, 80), self.rect, border_radius=5)
        
        # Fill track
        hx, hy = self.get_handle_pos()
        fill_rect = pg.Rect(self.rect.x, self.rect.y, hx - self.rect.x, self.rect.height)
        pg.draw.rect(surface, (100, 150, 255), fill_rect, border_radius=5)

        # Handle circle
        pg.draw.circle(surface, (255, 255, 255), (hx, hy), self.handle_r)
        if self.dragging:
            pg.draw.circle(surface, (150, 200, 255), (hx, hy), self.handle_r - 2)

    def handle_event(self, event):
        if event.type == pg.MOUSEBUTTONDOWN:
            if event.button == 1:
                hx, hy = self.get_handle_pos()
                m_pos = event.pos
                dist = ((m_pos[0] - hx) ** 2 + (m_pos[1] - hy) ** 2) ** 0.5
                if dist <= self.handle_r + 5 or self.rect.collidepoint(m_pos):
                    self.dragging = True
                    self.update_val(m_pos[0])
        elif event.type == pg.MOUSEBUTTONUP:
            if event.button == 1:
                self.dragging = False
        elif event.type == pg.MOUSEMOTION:
            if self.dragging:
                self.update_val(event.pos[0])

    def update_val(self, mx):
        mx = max(self.rect.x, min(mx, self.rect.right))
        if self.rect.width == 0:
            ratio = 0.0
        else:
            ratio = (mx - self.rect.x) / self.rect.width
        raw_val = self.min_val + ratio * (self.max_val - self.min_val)
        self.val = int(round(raw_val))


class Button:
    def __init__(self, text, x, y, w, h, callback, active=False):
        self.text = text
        self.rect = pg.Rect(x, y, w, h)
        self.callback = callback
        self.active = active

    def draw(self, surface, font):
        color = (100, 150, 255) if self.active else (45, 45, 60)
        hover_color = (120, 170, 255) if self.active else (60, 60, 80)
        
        m_pos = pg.mouse.get_pos()
        draw_color = hover_color if self.rect.collidepoint(m_pos) else color
        
        pg.draw.rect(surface, draw_color, self.rect, border_radius=6)
        pg.draw.rect(surface, (120, 120, 140), self.rect, width=1, border_radius=6)
        
        txt = font.render(self.text, True, (255, 255, 255))
        txt_rect = txt.get_rect(center=self.rect.center)
        surface.blit(txt, txt_rect)

    def handle_event(self, event):
        if event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self.callback()


class HitboxEditorApp:
    def __init__(self):
        self.clock = pg.time.Clock()
        self.running = True
        
        # Available entities and active index
        self.entity_keys = ["player", "skeleton", "enemy", "wizard_npc", "generic_npc"]
        self.entity_labels = ["Player", "Skeleton", "Enemy (Bat)", "Wizard NPC", "Generic NPC"]
        self.active_index = 0
        
        self.entity: Any = None
        self.original_image_size = (0, 0)
        self.frame_idx = 0
        self.frame_timer = 0.0

        # Drag & Drop interaction state variables
        self.dragging_edge = None
        self.dragging_floor = False
        self.dragging_entity = False

        # Build sidebar buttons
        self.sidebar_buttons = []
        for idx, label in enumerate(self.entity_labels):
            btn_y = 100 + idx * 60
            self.sidebar_buttons.append(
                Button(label, 30, btn_y, 200, 45, lambda idx=idx: self.select_entity(idx))
            )
        
        # Right action buttons
        self.action_buttons = [
            Button("SAVE (S)", 950, 600, 130, 45, self.save_current_config),
            Button("RESET (R)", 1100, 600, 130, 45, self.reset_current_config),
        ]

        # Five sliders
        self.sliders = {
            "left": Slider("Left Margin", 950, 120, 280, 0, 100, 0),
            "right": Slider("Right Margin", 950, 200, 280, 0, 100, 0),
            "top": Slider("Top Margin", 950, 280, 280, 0, 100, 0),
            "bottom": Slider("Bottom Margin", 950, 360, 280, 0, 100, 0),
            "ground_offset": Slider("Ground Offset", 950, 440, 280, 0, 200, 0),
        }

        self.select_entity(0)

    def select_entity(self, idx):
        self.active_index = idx
        for i, btn in enumerate(self.sidebar_buttons):
            btn.active = (i == idx)
        
        key = self.entity_keys[idx]
        
        # Instantiate correct entity
        if key == "player":
            self.entity = Player(640, 480, mock_audio)
        elif key == "skeleton":
            dummy_player = Player(640, 480, mock_audio)
            self.entity = Skeleton(640, 480, dummy_player)
        elif key == "enemy":
            self.entity = Enemy()
            self.entity.rect.midbottom = (640, 480)
        elif key == "wizard_npc":
            self.entity = WizardNPC(640, 480, "Hi, I am a wizard.")
        elif key == "generic_npc":
            self.entity = GenericNPC(
                x=640, 
                y=480, 
                sprite_dir="assets/graphics/Goblin/Idle", 
                text="Greetings!", 
                title="Goblin", 
                scale=2.0
            )

        # Retrieve base texture dimensions
        if self.entity is not None and self.entity.animations and self.entity.state in self.entity.animations:
            first_frame = self.entity.animations[self.entity.state][0]
            self.original_image_size = first_frame.get_size()
        else:
            self.original_image_size = (100, 100)

        # Load currently saved margins and ground offset
        margins = HitboxRegistry.get_margins(key)
        
        # Set up sliders dynamically based on base image size
        w, h = self.original_image_size
        self.sliders["left"].max_val = w // 2 - 1
        self.sliders["left"].val = min(margins.left, w // 2 - 1)

        self.sliders["right"].max_val = w // 2 - 1
        self.sliders["right"].val = min(margins.right, w // 2 - 1)

        self.sliders["top"].max_val = h // 2 - 1
        self.sliders["top"].val = min(margins.top, h // 2 - 1)

        self.sliders["bottom"].max_val = h // 2 - 1
        self.sliders["bottom"].val = min(margins.bottom, h // 2 - 1)

        self.sliders["ground_offset"].val = margins.ground_offset

        self.frame_idx = 0
        self.frame_timer = 0.0
        self.update_hitbox_preview()

    def update_hitbox_preview(self):
        """Re-applies the adjusted slider margins to the entity's hitbox rect."""
        if not self.entity:
            return
        
        # Capture current slider values
        left = self.sliders["left"].val
        right = self.sliders["right"].val
        top = self.sliders["top"].val
        bottom = self.sliders["bottom"].val
        ground_offset = self.sliders["ground_offset"].val

        # Get first frame
        if self.entity.animations and self.entity.state in self.entity.animations:
            first_frame = self.entity.animations[self.entity.state][0]
        else:
            return
        
        self.entity.image = first_frame
        
        # Calculate raw rect bottom so that hitbox.bottom aligns perfectly with current floor
        # floor_y = PREVIEW_SCREEN_BOTTOM - ground_offset
        # hitbox.bottom = raw_bottom - bottom = floor_y => raw_bottom = floor_y + bottom
        raw_bottom = PREVIEW_SCREEN_BOTTOM - ground_offset + bottom
        self.entity.rect = first_frame.get_rect(midbottom=(PREVIEW_CENTER_X, raw_bottom))
        
        # Reset engine image offset vector
        self.entity.image_offset = pg.math.Vector2(0, 0)
        
        # Apply the margins
        self.entity.adjust_hitbox_sides(left=left, right=right, top=top, bottom=bottom)

    def save_current_config(self):
        key = self.entity_keys[self.active_index]
        margins = HitboxMargins(
            left=self.sliders["left"].val,
            right=self.sliders["right"].val,
            top=self.sliders["top"].val,
            bottom=self.sliders["bottom"].val,
            ground_offset=self.sliders["ground_offset"].val
        )
        HitboxRegistry.update_margins(key, margins)
        print(f"Saved configuration for {key}: {margins}")

    def reset_current_config(self):
        key = self.entity_keys[self.active_index]
        default_margins = HitboxRegistry.DEFAULTS.get(key, HitboxMargins(0, 0, 0, 0, 0))
        
        self.sliders["left"].val = default_margins.left
        self.sliders["right"].val = default_margins.right
        self.sliders["top"].val = default_margins.top
        self.sliders["bottom"].val = default_margins.bottom
        self.sliders["ground_offset"].val = default_margins.ground_offset
        
        self.update_hitbox_preview()
        print(f"Reset {key} to defaults.")

    def run(self):
        while self.running:
            dt = self.clock.tick(60) / 1000.0
            self.handle_events()
            self.update(dt)
            self.draw()

    def handle_events(self):
        m_pos = pg.mouse.get_pos()
        
        # Calculate coordinate references for collision detection
        raw_rect = pg.Rect(0, 0, 0, 0)
        hitbox = pg.Rect(0, 0, 0, 0)
        floor_y = 0
        if self.entity and self.entity.animations:
            first_frame = self.entity.animations[self.entity.state][0]
            bottom = self.sliders["bottom"].val
            ground_offset = self.sliders["ground_offset"].val
            raw_bottom = PREVIEW_SCREEN_BOTTOM - ground_offset + bottom
            raw_rect = first_frame.get_rect(midbottom=(PREVIEW_CENTER_X, raw_bottom))
            hitbox = self.entity.rect
            floor_y = PREVIEW_SCREEN_BOTTOM - ground_offset

        for event in pg.event.get():
            if event.type == pg.QUIT:
                self.running = False
                
            elif event.type == pg.KEYDOWN:
                if event.key == pg.K_ESCAPE:
                    self.running = False
                elif event.key == pg.K_s:
                    self.save_current_config()
                elif event.key == pg.K_r:
                    self.reset_current_config()

            elif event.type == pg.MOUSEBUTTONDOWN:
                if event.button == 1:
                    # 1. Check if clicking on slider or sidebar buttons
                    ui_event_handled = False
                    for btn in self.sidebar_buttons:
                        if btn.rect.collidepoint(event.pos):
                            btn.handle_event(event)
                            ui_event_handled = True
                    for btn in self.action_buttons:
                        if btn.rect.collidepoint(event.pos):
                            btn.handle_event(event)
                            ui_event_handled = True
                    for slider in self.sliders.values():
                        if slider.rect.collidepoint(event.pos) or (abs(event.pos[0] - slider.get_handle_pos()[0]) <= 15 and abs(event.pos[1] - slider.get_handle_pos()[1]) <= 15):
                            slider.handle_event(event)
                            ui_event_handled = True

                    if not ui_event_handled and self.entity:
                        # 2. Check if clicking floor line to drag
                        if abs(m_pos[1] - floor_y) <= 8 and 280 <= m_pos[0] <= 910:
                            self.dragging_floor = True
                        
                        # 3. Check if clicking hitbox boundaries
                        elif abs(m_pos[0] - hitbox.left) <= 8 and hitbox.top <= m_pos[1] <= hitbox.bottom:
                            self.dragging_edge = 'left'
                        elif abs(m_pos[0] - hitbox.right) <= 8 and hitbox.top <= m_pos[1] <= hitbox.bottom:
                            self.dragging_edge = 'right'
                        elif abs(m_pos[1] - hitbox.top) <= 8 and hitbox.left <= m_pos[0] <= hitbox.right:
                            self.dragging_edge = 'top'
                        elif abs(m_pos[1] - hitbox.bottom) <= 8 and hitbox.left <= m_pos[0] <= hitbox.right:
                            self.dragging_edge = 'bottom'
                        
                        # 4. Check if clicking entity sprite itself to move ground level
                        elif raw_rect.collidepoint(m_pos):
                            self.dragging_entity = True

            elif event.type == pg.MOUSEBUTTONUP:
                if event.button == 1:
                    self.dragging_edge = None
                    self.dragging_floor = False
                    self.dragging_entity = False
                    
                    # Also reset sliders drag status
                    for slider in self.sliders.values():
                        slider.dragging = False

            elif event.type == pg.MOUSEMOTION:
                # Handle drag events
                if self.dragging_floor or self.dragging_entity:
                    offset = PREVIEW_SCREEN_BOTTOM - event.pos[1]
                    self.sliders["ground_offset"].val = max(0, min(offset, 200))
                    self.update_hitbox_preview()
                
                elif self.dragging_edge == 'left':
                    left = event.pos[0] - raw_rect.left
                    self.sliders["left"].val = max(0, min(left, self.sliders["left"].max_val))
                    self.update_hitbox_preview()
                
                elif self.dragging_edge == 'right':
                    right = raw_rect.right - event.pos[0]
                    self.sliders["right"].val = max(0, min(right, self.sliders["right"].max_val))
                    self.update_hitbox_preview()
                
                elif self.dragging_edge == 'top':
                    top = event.pos[1] - raw_rect.top
                    self.sliders["top"].val = max(0, min(top, self.sliders["top"].max_val))
                    self.update_hitbox_preview()
                
                elif self.dragging_edge == 'bottom':
                    bottom = raw_rect.bottom - event.pos[1]
                    self.sliders["bottom"].val = max(0, min(bottom, self.sliders["bottom"].max_val))
                    self.update_hitbox_preview()

                # Delegate standard mouse motion to sliders
                for slider in self.sliders.values():
                    if slider.dragging:
                        slider.handle_event(event)
                        self.update_hitbox_preview()

    def update(self, dt):
        if self.entity and self.entity.animations:
            frames = self.entity.animations[self.entity.state]
            self.frame_timer += dt
            if self.frame_timer >= 0.1:
                self.frame_timer = 0.0
                self.frame_idx = (self.frame_idx + 1) % len(frames)
                self.entity.image = frames[self.frame_idx]

    def draw(self):
        m_pos = pg.mouse.get_pos()
        screen.fill((20, 20, 28))

        # ─ 1. Header Title ──────────────
        title_text = title_font.render("Hitbox & Dimension Editor", True, (255, 255, 255))
        screen.blit(title_text, (30, 25))

        # ─ 2. Vertical Sidebar Line ──────────────
        pg.draw.line(screen, (45, 45, 60), (260, 0), (260, SCREEN_H), 2)
        
        # ─ 3. Left Sidebar ──────────────
        for btn in self.sidebar_buttons:
            btn.draw(screen, ui_font)

        # ─ 4. Main Preview Panel ──────────────
        preview_bg = pg.Rect(280, 80, 630, 600)
        pg.draw.rect(screen, (13, 13, 18), preview_bg, border_radius=12)
        pg.draw.rect(screen, (50, 50, 70), preview_bg, width=2, border_radius=12)

        # Retrieve positioning references
        raw_rect = pg.Rect(0, 0, 0, 0)
        hitbox = pg.Rect(0, 0, 0, 0)
        floor_y = PREVIEW_SCREEN_BOTTOM
        ground_offset = 0
        if self.entity and self.entity.animations:
            first_frame = self.entity.animations[self.entity.state][0]
            bottom = self.sliders["bottom"].val
            ground_offset = self.sliders["ground_offset"].val
            raw_bottom = PREVIEW_SCREEN_BOTTOM - ground_offset + bottom
            raw_rect = first_frame.get_rect(midbottom=(PREVIEW_CENTER_X, raw_bottom))
            hitbox = self.entity.rect
            floor_y = PREVIEW_SCREEN_BOTTOM - ground_offset

        # Reference Floor Line (Cyan/Gray)
        # Check hover conditions for floor line
        hover_floor = abs(m_pos[1] - floor_y) <= 8 and 280 <= m_pos[0] <= 910
        floor_color = (0, 255, 255) if (hover_floor or self.dragging_floor) else (241, 196, 15)
        floor_thickness = 3 if (hover_floor or self.dragging_floor) else 2
        
        # Draw screen bottom line (representing the lowest pixel boundary of the game viewport)
        pg.draw.line(screen, (50, 50, 70), (290, PREVIEW_SCREEN_BOTTOM), (900, PREVIEW_SCREEN_BOTTOM), 2)
        screen.blit(help_font.render("Viewport Bottom", True, (80, 80, 100)), (295, PREVIEW_SCREEN_BOTTOM + 5))

        # Draw Player Standard Ground Level (34px offset reference)
        player_ground_y = PREVIEW_SCREEN_BOTTOM - 34
        # Draw dashed gray line for alignment reference
        for x_dash in range(290, 900, 10):
            if (x_dash // 10) % 2 == 0:
                pg.draw.line(screen, (90, 90, 110), (x_dash, player_ground_y), (x_dash + 5, player_ground_y), 1)
        screen.blit(help_font.render("Player Ground Level (34px)", True, (120, 120, 140)), (295, player_ground_y - 20))

        # Draw active entity floor line
        pg.draw.line(screen, floor_color, (290, floor_y), (900, floor_y), floor_thickness)
        floor_lbl = help_font.render(f"Entity Ground Level ({ground_offset}px)", True, floor_color)
        screen.blit(floor_lbl, (700, floor_y - 20))

        # Render entity and hitbox
        if self.entity:
            draw_pos = self.entity.rect.topleft - self.entity.image_offset
            screen.blit(self.entity.image, draw_pos)

            # Draw green bounding box representing raw frame texture bounds
            pg.draw.rect(screen, (46, 204, 113), raw_rect, 1)

            # Draw red bounding box representing the active collision hitbox, checking edge hover styles
            pg.draw.rect(screen, (231, 76, 60), hitbox, 2)
            
            # Draw visual resize handles if hovering or dragging
            hover_left = abs(m_pos[0] - hitbox.left) <= 8 and hitbox.top <= m_pos[1] <= hitbox.bottom
            hover_right = abs(m_pos[0] - hitbox.right) <= 8 and hitbox.top <= m_pos[1] <= hitbox.bottom
            hover_top = abs(m_pos[1] - hitbox.top) <= 8 and hitbox.left <= m_pos[0] <= hitbox.right
            hover_bottom = abs(m_pos[1] - hitbox.bottom) <= 8 and hitbox.left <= m_pos[0] <= hitbox.right

            if hover_left or self.dragging_edge == 'left':
                pg.draw.line(screen, (241, 196, 15), (hitbox.left, hitbox.top), (hitbox.left, hitbox.bottom), 4)
            if hover_right or self.dragging_edge == 'right':
                pg.draw.line(screen, (241, 196, 15), (hitbox.right, hitbox.top), (hitbox.right, hitbox.bottom), 4)
            if hover_top or self.dragging_edge == 'top':
                pg.draw.line(screen, (241, 196, 15), (hitbox.left, hitbox.top), (hitbox.right, hitbox.top), 4)
            if hover_bottom or self.dragging_edge == 'bottom':
                pg.draw.line(screen, (241, 196, 15), (hitbox.left, hitbox.bottom), (hitbox.right, hitbox.bottom), 4)

        # ─ 5. Info Panel ──────────────
        help_bg = pg.Rect(290, 90, 480, 80)
        pg.draw.rect(screen, (30, 30, 40, 220), help_bg, border_radius=8)
        pg.draw.rect(screen, (80, 80, 100), help_bg, width=1, border_radius=8)
        
        lbl_info_1 = help_font.render("• Green Box: Raw texture frame bounds", True, (46, 204, 113))
        lbl_info_2 = help_font.render("• Red Box: Active hitbox. Drag edges directly to edit!", True, (231, 76, 60))
        lbl_info_3 = help_font.render("• Drag the Yellow Ground line or Entity body up/down to align to floor.", True, (241, 196, 15))
        
        screen.blit(lbl_info_1, (300, 95))
        screen.blit(lbl_info_2, (300, 115))
        screen.blit(lbl_info_3, (300, 135))

        # ─ 6. Controls Panel (Right) ──────────────
        pg.draw.line(screen, (45, 45, 60), (930, 0), (930, SCREEN_H), 2)

        ctrl_title = title_font.render("Controls", True, (255, 255, 255))
        screen.blit(ctrl_title, (950, 25))

        # Draw sliders
        for slider in self.sliders.values():
            slider.draw(screen, ui_font)

        # Draw action buttons
        for btn in self.action_buttons:
            btn.draw(screen, ui_font)

        pg.display.flip()

    def cleanup(self):
        pg.quit()


if __name__ == "__main__":
    app = HitboxEditorApp()
    try:
        app.run()
    finally:
        app.cleanup()
