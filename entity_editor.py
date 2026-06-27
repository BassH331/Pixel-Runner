#!/usr/bin/env python3
import os
import sys
import glob
import json
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
from src.game.entities.fire_wizard import FireWizard

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
    def __init__(self, label, x, y, w, min_val, max_val, current_val, is_float=False):
        self.label = label
        self.rect = pg.Rect(x, y, w, 10)
        self.handle_r = 10
        self.min_val = min_val
        self.max_val = max_val
        self.val = current_val
        self.dragging = False
        self.is_float = is_float

    def get_handle_pos(self):
        if self.max_val == self.min_val:
            ratio = 0.0
        else:
            ratio = (self.val - self.min_val) / (self.max_val - self.min_val)
        return int(self.rect.x + ratio * self.rect.width), self.rect.centery

    def draw(self, surface, font):
        # Label and current value
        val_str = f"{self.val:.2f}x" if self.is_float else f"{self.val} px"
        txt = font.render(f"{self.label}: {val_str}", True, (240, 240, 240))
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
        if self.is_float:
            self.val = round(raw_val, 2)
        else:
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
        self.active_index = 0
        
        self.entity: Any = None
        self.original_image_size = (0, 0)
        self.frame_idx = 0
        self.frame_timer = 0.0

        # Confirmation & Transaction State
        self.confirming_save = False

        # Drag & Drop interaction state variables
        self.dragging_edge = None
        self.dragging_floor = False
        self.dragging_entity = False

        # Dynamically scan for actual game entities
        self.entity_configs: list[dict[str, Any]] = [
            {"key": "player", "label": "Player", "type": "player"},
            {"key": "skeleton", "label": "Skeleton", "type": "skeleton"},
            {"key": "enemy", "label": "Enemy (Bat)", "type": "enemy"},
        ]
        self.scan_level_files()

        # Build sidebar buttons
        self.sidebar_buttons = []
        for idx, config in enumerate(self.entity_configs):
            btn_y = 100 + idx * 60
            self.sidebar_buttons.append(
                Button(config["label"], 30, btn_y, 200, 45, lambda idx=idx: self.select_entity(idx))
            )
        
        # Right action buttons
        self.action_buttons = [
            Button("SAVE (S)", 950, 600, 130, 45, self.save_current_config),
            Button("RESET (R)", 1100, 600, 130, 45, self.reset_current_config),
        ]

        # Six sliders (realigned positions to fit neatly)
        self.sliders = {
            "left": Slider("Left Margin", 950, 100, 280, 0, 100, 0),
            "right": Slider("Right Margin", 950, 175, 280, 0, 100, 0),
            "top": Slider("Top Margin", 950, 250, 280, 0, 100, 0),
            "bottom": Slider("Bottom Margin", 950, 325, 280, 0, 100, 0),
            "ground_offset": Slider("Ground Offset", 950, 400, 280, 0, 200, 0),
            "scale": Slider("Scale Factor", 950, 475, 280, 0.5, 6.0, 1.0, is_float=True),
        }

        self.select_entity(0)
        HitboxRegistry.begin_transaction()

    def scan_level_files(self):
        """Scans all level configuration JSONs in game_data to find actual game NPCs and bosses."""
        added_keys = {"player", "skeleton", "enemy"}
        
        level_files = glob.glob("game_data/level_*.json")
        for filepath in level_files:
            try:
                with open(filepath, "r") as f:
                    level_data = json.load(f)
                
                # Scan world_events for NPCs and bosses
                world_events = level_data.get("world_events", [])
                for event in world_events:
                    etype = event.get("type")
                    if etype == "npc":
                        params = event.get("params", {})
                        npc_type = params.get("npc_type")
                        
                        if npc_type == "wizard":
                            key = "wizard_npc"
                            if key not in added_keys:
                                self.entity_configs.append({
                                    "key": key,
                                    "label": params.get("title", "Wizard NPC"),
                                    "type": "wizard_npc",
                                    "params": params
                                })
                                added_keys.add(key)
                        
                        elif npc_type == "generic":
                            sprite_dir = params.get("sprite_dir")
                            if sprite_dir:
                                folder_name = os.path.basename(sprite_dir.rstrip("/"))
                                if folder_name.lower() == "idle":
                                    parent_dir = os.path.dirname(sprite_dir.rstrip("/"))
                                    folder_name = os.path.basename(parent_dir)
                                key = f"generic_npc_{folder_name.lower()}"
                                
                                if key not in added_keys:
                                    self.entity_configs.append({
                                        "key": key,
                                        "label": params.get("title", "Generic NPC"),
                                        "type": "generic_npc",
                                        "params": params
                                    })
                                    added_keys.add(key)
                    elif etype == "boss":
                        params = event.get("params", {})
                        sprite_dir = params.get("sprite_dir") or ""
                        key = f"boss:{os.path.basename(sprite_dir.rstrip('/'))}" if sprite_dir else "boss"
                        if key not in added_keys:
                            self.entity_configs.append({
                                "key": key,
                                "label": f"Boss: {params.get('title', 'Boss')}",
                                "type": "boss",
                                "params": params
                            })
                            added_keys.add(key)
            except Exception as e:
                print(f"Error scanning level file {filepath}: {e}")

        # Fallbacks to ensure standard options remain present
        if "wizard_npc" not in added_keys:
            self.entity_configs.append({
                "key": "wizard_npc",
                "label": "Wizard NPC",
                "type": "wizard_npc",
                "params": {"title": "Wizard"}
            })
        if "generic_npc_goblin" not in added_keys:
            self.entity_configs.append({
                "key": "generic_npc_goblin",
                "label": "Goblin NPC",
                "type": "generic_npc",
                "params": {
                    "sprite_dir": "assets/graphics/Goblin/Idle",
                    "title": "Goblin",
                    "scale": 2.0,
                    "text": "Greetings!"
                }
            })
        if "boss:wizard" not in added_keys:
            self.entity_configs.append({
                "key": "boss:wizard",
                "label": "Boss: Wizard",
                "type": "boss",
                "params": {
                    "sprite_dir": "assets/wizard",
                    "title": "Wizard Boss",
                    "scale": 1.0,
                    "health": 150.0,
                    "tier": "boss",
                    "behaviour_map": {
                        "Attack": "ATTACK",
                        "Death": "DEATH",
                        "Idle": "IDLE",
                        "Move": "WALK",
                        "Take Hit": "ATTACK"
                    }
                }
            })
        if "skeleton_zombie" not in added_keys:
            self.entity_configs.append({
                "key": "skeleton_zombie",
                "label": "Skeleton Zombie",
                "type": "skeleton",
                "params": {
                    "sprite_root": "assets/graphics/SkeletonZombie",
                    "tier": "minion",
                    "behaviour_map": {
                        "Idle": "idle",
                        "Chase": "walk",
                        "Attack": "attack",
                        "Hurt": "hurt"
                    }
                }
            })
        if "blood_zombie" not in added_keys:
            self.entity_configs.append({
                "key": "blood_zombie",
                "label": "Blood Zombie",
                "type": "skeleton",
                "params": {
                    "sprite_root": "assets/graphics/bloodZombie",
                    "tier": "minion",
                    "behaviour_map": {
                        "Attack1": "attack",
                        "Attack2": "attack",
                        "Death": "death",
                        "Idle": "idle",
                        "Move": "walk"
                    }
                }
            })
        if "green_monster" not in added_keys:
            self.entity_configs.append({
                "key": "green_monster",
                "label": "Green Monster",
                "type": "skeleton",
                "params": {
                    "sprite_root": "assets/graphics/green_monster",
                    "tier": "minion",
                    "behaviour_map": {
                        "idle": "idle",
                        "walk": "walk",
                        "1atk": "attack",
                        "2atk": "attack",
                        "hurt": "hurt",
                        "death": "death"
                    }
                }
            })
        if "skeleton_minion" not in added_keys:
            self.entity_configs.append({
                "key": "skeleton_minion",
                "label": "Skeleton Minion",
                "type": "skeleton",
                "params": {
                    "sprite_root": "assets/skeleton",
                    "tier": "minion",
                    "behaviour_map": {
                        "Skeleton_01_White_Attack1": "attack",
                        "Skeleton_01_White_Attack2": "attack",
                        "Skeleton_01_White_Die": "death",
                        "Skeleton_01_White_Hurt": "hurt",
                        "Skeleton_01_White_Idle": "idle",
                        "Skeleton_01_White_Walk": "walk"
                    }
                }
            })

    def reload_entity(self):
        config = self.entity_configs[self.active_index]
        key = config["key"]
        ent_type = config["type"]
        params = config.get("params", {})
        
        # Update scale in memory registry before instantiating
        margins = HitboxRegistry.get_margins(key)
        margins.scale = self.sliders["scale"].val

        # Instantiate correct entity with updated scale in registry
        if ent_type == "player":
            self.entity = Player(640, 480, mock_audio)
        elif ent_type == "skeleton":
            dummy_player = Player(640, 480, mock_audio)
            self.entity = Skeleton(
                640, 480, dummy_player,
                sprite_root=params.get("sprite_root"),
                behaviour_map=params.get("behaviour_map"),
                tier=params.get("tier", "minion")
            )
        elif ent_type == "enemy":
            self.entity = Enemy()
            self.entity.rect.midbottom = (640, 480)
        elif ent_type == "wizard_npc":
            self.entity = WizardNPC(
                x=640, 
                y=480, 
                text=params.get("text", "Halt, traveler!"), 
                title=params.get("title", "Wizard"), 
                scale=self.sliders["scale"].val
            )
        elif ent_type == "generic_npc":
            self.entity = GenericNPC(
                x=640, 
                y=480, 
                sprite_dir=params.get("sprite_dir", "assets/graphics/Goblin/Idle"), 
                text=params.get("text", "Greetings!"), 
                title=params.get("title", "NPC"), 
                scale=self.sliders["scale"].val
            )
        elif ent_type == "boss":
            dummy_player = Player(640, 480, mock_audio)
            sprite_dir = params.get("sprite_dir")
            if sprite_dir and "wizard" in sprite_dir.lower():
                self.entity = FireWizard(
                    x=640,
                    y=480,
                    player=dummy_player,
                    tier=params.get("tier", "boss"),
                    sprite_root=sprite_dir
                )
            else:
                self.entity = Skeleton(
                    x=640,
                    y=480,
                    player=dummy_player,
                    sprite_root=sprite_dir,
                    behaviour_map=params.get("behaviour_map"),
                    tier=params.get("tier", "boss")
                )

        # Retrieve base texture dimensions
        if self.entity is not None and self.entity.animations and self.entity.state in self.entity.animations:
            first_frame = self.entity.animations[self.entity.state][0]
            self.original_image_size = first_frame.get_size()
        else:
            self.original_image_size = (100, 100)

        # Set up sliders dynamically based on base image size
        w, h = self.original_image_size
        self.sliders["left"].max_val = w // 2 - 1
        self.sliders["left"].val = min(self.sliders["left"].val, w // 2 - 1)

        self.sliders["right"].max_val = w // 2 - 1
        self.sliders["right"].val = min(self.sliders["right"].val, w // 2 - 1)

        self.sliders["top"].max_val = h // 2 - 1
        self.sliders["top"].val = min(self.sliders["top"].val, h // 2 - 1)

        self.sliders["bottom"].max_val = h // 2 - 1
        self.sliders["bottom"].val = min(self.sliders["bottom"].val, h // 2 - 1)

        self.update_hitbox_preview()

    def select_entity(self, idx):
        self.active_index = idx
        for i, btn in enumerate(self.sidebar_buttons):
            btn.active = (i == idx)
        
        config = self.entity_configs[idx]
        key = config["key"]
        
        # Load currently saved margins and ground offset
        margins = HitboxRegistry.get_margins(key)
        
        # Update scale slider from loaded margins
        self.sliders["scale"].val = margins.scale
        
        # Update other sliders from loaded margins
        self.sliders["left"].val = margins.left
        self.sliders["right"].val = margins.right
        self.sliders["top"].val = margins.top
        self.sliders["bottom"].val = margins.bottom
        self.sliders["ground_offset"].val = margins.ground_offset

        self.frame_idx = 0
        self.frame_timer = 0.0
        
        # Recreate entity and update slider max values
        self.reload_entity()

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
        raw_bottom = PREVIEW_SCREEN_BOTTOM - ground_offset + bottom
        self.entity.rect = first_frame.get_rect(midbottom=(PREVIEW_CENTER_X, raw_bottom))
        
        # Reset engine image offset vector
        self.entity.image_offset.x = 0.0
        self.entity.image_offset.y = 0.0
        
        # Apply the margins
        self.entity.adjust_hitbox_sides(left=left, right=right, top=top, bottom=bottom)

    def save_current_config(self):
        # Open confirmation dialog instead of writing directly
        self.confirming_save = True

    def execute_save_commit(self):
        config = self.entity_configs[self.active_index]
        key = config["key"]
        margins = HitboxMargins(
            left=self.sliders["left"].val,
            right=self.sliders["right"].val,
            top=self.sliders["top"].val,
            bottom=self.sliders["bottom"].val,
            ground_offset=self.sliders["ground_offset"].val,
            scale=self.sliders["scale"].val
        )
        # Update memory configuration
        HitboxRegistry.update_margins(key, margins)
        # Commit transaction to database exclusively locked under flock
        HitboxRegistry.commit_transaction()
        print(f"Committed and locked database update for {key}: {margins}")

    def reset_current_config(self):
        config = self.entity_configs[self.active_index]
        key = config["key"]
        
        # Rollback current in-memory changes to the last committed transaction checkpoint
        HitboxRegistry.rollback_transaction()
        
        # Reload margins from rollback state
        margins = HitboxRegistry.get_margins(key)
        
        self.sliders["scale"].val = margins.scale
        self.sliders["left"].val = margins.left
        self.sliders["right"].val = margins.right
        self.sliders["top"].val = margins.top
        self.sliders["bottom"].val = margins.bottom
        self.sliders["ground_offset"].val = margins.ground_offset
        
        self.reload_entity()
        print(f"Rolled back {key} configuration to last saved checkpoint.")

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
                return

            if self.confirming_save:
                # Handle inputs only for confirmation dialog
                if event.type == pg.KEYDOWN:
                    if event.key in (pg.K_RETURN, pg.K_y):
                        self.execute_save_commit()
                        self.confirming_save = False
                    elif event.key in (pg.K_ESCAPE, pg.K_n):
                        self.confirming_save = False
                elif event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
                    # Check Confirm/Cancel dialog button clicks
                    dialog_w, dialog_h = 500, 240
                    dialog_x = (SCREEN_W - dialog_w) // 2
                    dialog_y = (SCREEN_H - dialog_h) // 2
                    confirm_btn_rect = pg.Rect(dialog_x + 40, dialog_y + 160, 180, 45)
                    cancel_btn_rect = pg.Rect(dialog_x + 280, dialog_y + 160, 180, 45)
                    if confirm_btn_rect.collidepoint(event.pos):
                        self.execute_save_commit()
                        self.confirming_save = False
                    elif cancel_btn_rect.collidepoint(event.pos):
                        self.confirming_save = False
                continue
                
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
                    for name, slider in self.sliders.items():
                        if slider.rect.collidepoint(event.pos) or (abs(event.pos[0] - slider.get_handle_pos()[0]) <= 15 and abs(event.pos[1] - slider.get_handle_pos()[1]) <= 15):
                            slider.handle_event(event)
                            ui_event_handled = True
                            if name == "scale":
                                self.reload_entity()
                            else:
                                self.update_hitbox_preview()

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
                for name, slider in self.sliders.items():
                    if slider.dragging:
                        slider.handle_event(event)
                        if name == "scale":
                            self.reload_entity()
                        else:
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

        # ─ 7. Write Confirmation Dialog (Overlay) ──────────────
        if self.confirming_save:
            # 1. Darken the entire screen slightly
            overlay = pg.Surface((SCREEN_W, SCREEN_H), pg.SRCALPHA)
            overlay.fill((10, 10, 15, 200))  # Semi-transparent dark blue/black
            screen.blit(overlay, (0, 0))

            # 2. Draw the Modal Dialog Box
            dialog_w, dialog_h = 520, 240
            dialog_x = (SCREEN_W - dialog_w) // 2
            dialog_y = (SCREEN_H - dialog_h) // 2
            dialog_rect = pg.Rect(dialog_x, dialog_y, dialog_w, dialog_h)

            # Draw outer container with premium styling
            pg.draw.rect(screen, (25, 25, 35), dialog_rect, border_radius=16)
            pg.draw.rect(screen, (241, 196, 15), dialog_rect, width=3, border_radius=16)

            # 3. Text content
            title_text = title_font.render("COMMIT TRANSACTION?", True, (241, 196, 15))
            desc_text_1 = help_font.render("Write and lock configurations to secure bank database?", True, (240, 240, 240))
            desc_text_2 = help_font.render("This commits changes to game_data/entity_dimensions.json", True, (160, 160, 180))

            title_rect = title_text.get_rect(centerx=dialog_rect.centerx, y=dialog_rect.y + 30)
            desc_rect_1 = desc_text_1.get_rect(centerx=dialog_rect.centerx, y=dialog_rect.y + 85)
            desc_rect_2 = desc_text_2.get_rect(centerx=dialog_rect.centerx, y=dialog_rect.y + 115)

            screen.blit(title_text, title_rect)
            screen.blit(desc_text_1, desc_rect_1)
            screen.blit(desc_text_2, desc_rect_2)

            # 4. Buttons (Confirm / Cancel)
            confirm_btn_rect = pg.Rect(dialog_x + 40, dialog_y + 160, 190, 45)
            cancel_btn_rect = pg.Rect(dialog_x + 290, dialog_y + 160, 190, 45)

            # Hover states
            confirm_hover = confirm_btn_rect.collidepoint(m_pos)
            cancel_hover = cancel_btn_rect.collidepoint(m_pos)

            confirm_color = (46, 204, 113) if confirm_hover else (39, 174, 96)
            cancel_color = (231, 76, 60) if cancel_hover else (192, 57, 43)

            pg.draw.rect(screen, confirm_color, confirm_btn_rect, border_radius=8)
            pg.draw.rect(screen, cancel_color, cancel_btn_rect, border_radius=8)

            confirm_lbl = ui_font.render("CONFIRM (ENTER)", True, (255, 255, 255))
            cancel_lbl = ui_font.render("CANCEL (ESC)", True, (255, 255, 255))

            screen.blit(confirm_lbl, confirm_lbl.get_rect(center=confirm_btn_rect.center))
            screen.blit(cancel_lbl, cancel_lbl.get_rect(center=cancel_btn_rect.center))

        pg.display.flip()

    def cleanup(self):
        pg.quit()


if __name__ == "__main__":
    app = HitboxEditorApp()
    try:
        app.run()
    finally:
        app.cleanup()
