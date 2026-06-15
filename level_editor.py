import os
import sys
import json
import fcntl
import copy
import pygame as pg

# Visual Setup
SCREEN_W = 1280
SCREEN_H = 720

NPC_SPRITE_OPTIONS = [
    "assets/graphics/masked_man",
    "assets/graphics/Goblin/Idle",
    "assets/graphics/Wizard_NPC"
]

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
        val_str = f"{self.val}"
        txt = font.render(f"{self.label}: {val_str}", True, (240, 240, 240))
        surface.blit(txt, (self.rect.x, self.rect.y - 25))

        pg.draw.rect(surface, (60, 60, 80), self.rect, border_radius=5)
        hx, hy = self.get_handle_pos()
        fill_rect = pg.Rect(self.rect.x, self.rect.y, hx - self.rect.x, self.rect.height)
        pg.draw.rect(surface, (100, 150, 255), fill_rect, border_radius=5)

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


class TextInput:
    def __init__(self, label, x, y, w, h, initial_val=""):
        self.label = label
        self.rect = pg.Rect(x, y, w, h)
        self.val = str(initial_val)
        self.active = False

    def draw(self, surface, font):
        lbl_txt = font.render(self.label, True, (200, 200, 200))
        surface.blit(lbl_txt, (self.rect.x, self.rect.y - 22))

        bg_color = (35, 35, 45) if not self.active else (50, 50, 65)
        border_color = (100, 150, 255) if self.active else (80, 80, 100)
        pg.draw.rect(surface, bg_color, self.rect, border_radius=6)
        pg.draw.rect(surface, border_color, self.rect, width=2, border_radius=6)

        txt_surf = font.render(self.val, True, (255, 255, 255))
        if txt_surf.get_width() > self.rect.width - 20:
            crop_rect = pg.Rect(txt_surf.get_width() - (self.rect.width - 20), 0, self.rect.width - 20, self.rect.height)
            surface.blit(txt_surf, (self.rect.x + 10, self.rect.y + (self.rect.height - txt_surf.get_height()) // 2), crop_rect)
        else:
            surface.blit(txt_surf, (self.rect.x + 10, self.rect.y + (self.rect.height - txt_surf.get_height()) // 2))

        if self.active and (pg.time.get_ticks() // 500) % 2 == 0:
            cursor_x = min(self.rect.x + 10 + txt_surf.get_width(), self.rect.right - 10)
            pg.draw.line(surface, (255, 255, 255), (cursor_x, self.rect.y + 8), (cursor_x, self.rect.bottom - 8), 2)

    def handle_event(self, event):
        if event.type == pg.MOUSEBUTTONDOWN:
            if event.button == 1:
                self.active = self.rect.collidepoint(event.pos)
        elif event.type == pg.KEYDOWN and self.active:
            if event.key == pg.K_BACKSPACE:
                self.val = self.val[:-1]
            elif event.key == pg.K_RETURN:
                self.active = False
            elif event.unicode.isprintable():
                self.val += event.unicode


class Button:
    def __init__(self, text, x, y, w, h, callback, active=False, color=None):
        self.text = text
        self.rect = pg.Rect(x, y, w, h)
        self.callback = callback
        self.active = active
        self.custom_color = color

    def draw(self, surface, font):
        if self.custom_color:
            color = self.custom_color
            hover_color = (min(color[0] + 30, 255), min(color[1] + 30, 255), min(color[2] + 30, 255))
        else:
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


class LevelEditorApp:
    def __init__(self):
        pg.init()
        pg.display.set_caption("Level Spawner Editor")
        self.screen = pg.display.set_mode((SCREEN_W, SCREEN_H))
        self.clock = pg.time.Clock()
        self.running = True

        # Transaction & Modal State
        self.confirming_save = False
        self.level_files = []
        self.active_file_idx = 0
        self.level_data = {}
        self.level_data_backup = {}
        
        self.selected_event = None
        self.dragging_event = None
        self.drag_offset = 0

        # Timeline offset (visible distance viewport center) and zoom (pixels/meter)
        self.timeline_offset = 0.0
        self.zoom = 0.25 # 1m = 0.25px
        self.timeline_w = 580
        self.timeline_x = 345
        self.timeline_y = 530

        # Fonts
        self.title_font = pg.font.SysFont("Arial", 24, bold=True)
        self.ui_font = pg.font.SysFont("Arial", 16)
        self.small_font = pg.font.SysFont("Arial", 13)

        # Scanned files
        self.scan_level_files()
        self.load_active_level()

        # UI Components
        self.init_ui()

        # Animation Cache for preview simulation
        self.preview_cache = {}
        self.preview_timer = 0.0
        self.preview_frame_idx = 0

    def scan_level_files(self):
        self.level_files = sorted([
            os.path.join("game_data", f)
            for f in os.listdir("game_data")
            if f.startswith("level_") and f.endswith(".json")
        ])
        if not self.level_files:
            print("No levels detected in game_data! Creating empty level_1.json")
            os.makedirs("game_data", exist_ok=True)
            empty_data = {
                "level_name": "New Level",
                "level_end_distance": 8000,
                "spawn_rate_min": 5000,
                "spawn_rate_max": 15000,
                "spawn_zones": [],
                "entities": [],
                "checkpoints": [],
                "world_events": []
            }
            with open("game_data/level_1.json", "w") as f:
                json.dump(empty_data, f, indent=4)
            self.level_files = ["game_data/level_1.json"]

    def load_active_level(self):
        file_path = self.level_files[self.active_file_idx]
        try:
            with open(file_path, "r") as f:
                # Exclusive lock during read for integrity
                fcntl.flock(f, fcntl.LOCK_EX)
                self.level_data = json.load(f)
            
            # Ensure world_events exists
            if "world_events" not in self.level_data:
                self.level_data["world_events"] = []

            # Create checkpoint for transactional rollbacks
            self.level_data_backup = copy.deepcopy(self.level_data)
            self.selected_event = None
            self.timeline_offset = 0.0
            print(f"Loaded {file_path} successfully. Transaction backup prepared.")
        except Exception as e:
            print(f"Error loading level file {file_path}: {e}")

    def save_active_level_commit(self):
        file_path = self.level_files[self.active_file_idx]
        try:
            # Sort world events by distance for ordering integrity
            self.level_data["world_events"] = sorted(
                self.level_data["world_events"],
                key=lambda x: x["distance"]
            )
            with open(file_path, "w") as f:
                # Exclusively lock database file during write
                fcntl.flock(f, fcntl.LOCK_EX)
                json.dump(self.level_data, f, indent=4)
            
            # Update rollback checkpoint
            self.level_data_backup = copy.deepcopy(self.level_data)
            print(f"Level changes committed and locked successfully to {file_path}.")
        except Exception as e:
            print(f"Error saving level {file_path}: {e}")

    def rollback_level(self):
        self.level_data = copy.deepcopy(self.level_data_backup)
        self.selected_event = None
        self.sync_inspector()
        print("Level data rolled back to last committed checkpoint.")

    def init_ui(self):
        # Navigation buttons
        self.nav_prev = Button("<", 30, 45, 40, 35, self.prev_level)
        self.nav_next = Button(">", 250, 45, 40, 35, self.next_level)

        # Right sidebar creation buttons (visible when no event is selected)
        self.btn_add_npc = Button("+ NPC EVENT", 970, 100, 280, 45, lambda: self.add_event("npc"))
        self.btn_add_enemy = Button("+ ENEMY WAVE", 970, 160, 280, 45, lambda: self.add_event("enemy_wave"))
        self.btn_add_interact = Button("+ INTERACTION", 970, 220, 280, 45, lambda: self.add_event("interaction"))

        # Right sidebar edit elements
        self.text_inputs = {
            "title": TextInput("Title", 970, 120, 280, 35),
            "text": TextInput("Dialogue / Event Text", 970, 200, 280, 35),
        }
        self.sliders = {
            "radius": Slider("Proximity Radius", 970, 290, 280, 50, 300, 160),
            "count": Slider("Enemy Count", 970, 290, 280, 1, 12, 3),
        }

        # Sprite select cycle buttons for NPCs
        self.btn_sprite_prev = Button("<", 970, 360, 40, 35, lambda: self.cycle_sprite_option(-1))
        self.btn_sprite_next = Button(">", 1210, 360, 40, 35, lambda: self.cycle_sprite_option(1))

        self.btn_npc_type_toggle = Button("Toggle NPC Type", 970, 415, 280, 35, self.toggle_npc_type)

        self.btn_delete = Button("DELETE EVENT", 970, 600, 280, 45, self.delete_selected_event, color=(231, 76, 60))

        # Bottom actions
        self.btn_save = Button("SAVE LEVEL (S)", 30, 600, 130, 45, self.trigger_save)
        self.btn_reset = Button("RESET (R)", 170, 600, 130, 45, self.rollback_level)

    def prev_level(self):
        if self.active_file_idx > 0:
            self.active_file_idx -= 1
            self.load_active_level()

    def next_level(self):
        if self.active_file_idx < len(self.level_files) - 1:
            self.active_file_idx += 1
            self.load_active_level()

    def get_next_id(self):
        evts = self.level_data.get("world_events", [])
        if not evts:
            return 1
        return max(evt["id"] for evt in evts) + 1

    def add_event(self, etype):
        # Spawn at 100m in front of timeline offset
        dist = int(self.timeline_offset + 500)
        dist = max(0, min(dist, self.level_data.get("level_end_distance", 8000)))

        params = {}
        if etype == "npc":
            params = {
                "npc_type": "generic",
                "sprite_dir": "assets/graphics/masked_man",
                "title": "Masked Stranger",
                "radius": 160,
                "scale": 2.0,
                "text": "Greetings, traveler!"
            }
        elif etype == "enemy_wave":
            params = {
                "count": 3,
                "type": "bat"
            }
        elif etype == "interaction":
            params = {
                "title": "Interactive Sign",
                "radius": 160,
                "text": "Checkpoint ahead."
            }

        new_evt = {
            "id": self.get_next_id(),
            "distance": dist,
            "type": etype,
            "params": params
        }
        self.level_data["world_events"].append(new_evt)
        self.selected_event = new_evt
        self.sync_inspector()

    def delete_selected_event(self):
        if self.selected_event:
            self.level_data["world_events"].remove(self.selected_event)
            self.selected_event = None
            self.sync_inspector()

    def cycle_sprite_option(self, direction):
        if not self.selected_event or self.selected_event["type"] != "npc":
            return
        params = self.selected_event["params"]
        if params.get("npc_type") != "generic":
            return
        
        current_dir = params.get("sprite_dir", "")
        if current_dir in NPC_SPRITE_OPTIONS:
            idx = NPC_SPRITE_OPTIONS.index(current_dir)
            new_idx = (idx + direction) % len(NPC_SPRITE_OPTIONS)
        else:
            new_idx = 0
        params["sprite_dir"] = NPC_SPRITE_OPTIONS[new_idx]
        self.preview_cache.clear() # Clear preview to force reload

    def toggle_npc_type(self):
        if not self.selected_event or self.selected_event["type"] != "npc":
            return
        params = self.selected_event["params"]
        current_type = params.get("npc_type", "generic")
        if current_type == "generic":
            params["npc_type"] = "wizard"
            params.pop("sprite_dir", None)
        else:
            params["npc_type"] = "generic"
            params["sprite_dir"] = NPC_SPRITE_OPTIONS[0]
        self.preview_cache.clear()

    def sync_inspector(self):
        if not self.selected_event:
            return
        
        params = self.selected_event["params"]
        self.text_inputs["title"].val = str(params.get("title", ""))
        self.text_inputs["text"].val = str(params.get("text", ""))
        
        if self.selected_event["type"] == "npc":
            self.sliders["radius"].val = params.get("radius", 160)
        elif self.selected_event["type"] == "enemy_wave":
            self.sliders["count"].val = params.get("count", 3)
        elif self.selected_event["type"] == "interaction":
            self.sliders["radius"].val = params.get("radius", 160)

    def sync_back_to_data(self):
        if not self.selected_event:
            return
        
        params = self.selected_event["params"]
        params["title"] = self.text_inputs["title"].val
        params["text"] = self.text_inputs["text"].val

        if self.selected_event["type"] == "npc":
            params["radius"] = self.sliders["radius"].val
        elif self.selected_event["type"] == "enemy_wave":
            params["count"] = self.sliders["count"].val
        elif self.selected_event["type"] == "interaction":
            params["radius"] = self.sliders["radius"].val

    def trigger_save(self):
        self.confirming_save = True

    def load_preview_animation(self):
        if not self.selected_event:
            return None

        key = ""
        sprite_dir = ""
        scale = 2.0
        
        if self.selected_event["type"] == "npc":
            params = self.selected_event["params"]
            if params.get("npc_type") == "wizard":
                key = "wizard"
                sprite_dir = "assets/graphics/Wizard_NPC"
                scale = 1.5
            else:
                sprite_dir = params.get("sprite_dir", NPC_SPRITE_OPTIONS[0])
                key = sprite_dir
                scale = 2.0
        elif self.selected_event["type"] == "enemy_wave":
            key = "bat"
            sprite_dir = "assets/graphics/bat/running"
            scale = 2.0
        else:
            return None

        if key in self.preview_cache:
            return self.preview_cache[key]

        # Attempt to load images
        frames = []
        if os.path.exists(sprite_dir):
            try:
                files = sorted([f for f in os.listdir(sprite_dir) if f.endswith(".png")])
                for f in files:
                    img = pg.image.load(os.path.join(sprite_dir, f)).convert_alpha()
                    w, h = img.get_size()
                    scaled = pg.transform.scale(img, (int(w * scale), int(h * scale)))
                    frames.append(scaled)
            except Exception as e:
                print(f"Error loading preview frames: {e}")
        
        if not frames:
            # Generate backup box
            box = pg.Surface((50, 50), pg.SRCALPHA)
            box.fill((100, 150, 255) if key != "bat" else (231, 76, 60))
            frames = [box]

        self.preview_cache[key] = frames
        return frames

    def update(self, dt):
        # Update preview frame indexes
        self.preview_timer += dt
        if self.preview_timer >= 0.15:
            self.preview_timer = 0.0
            self.preview_frame_idx += 1

    def handle_events(self):
        m_pos = pg.mouse.get_pos()

        for event in pg.event.get():
            if event.type == pg.QUIT:
                self.running = False
                return

            if self.confirming_save:
                # Modal confirmation inputs
                if event.type == pg.KEYDOWN:
                    if event.key in (pg.K_RETURN, pg.K_y):
                        self.save_active_level_commit()
                        self.confirming_save = False
                    elif event.key in (pg.K_ESCAPE, pg.K_n):
                        self.confirming_save = False
                elif event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
                    dialog_w, dialog_h = 520, 240
                    dialog_x = (SCREEN_W - dialog_w) // 2
                    dialog_y = (SCREEN_H - dialog_h) // 2
                    confirm_btn_rect = pg.Rect(dialog_x + 40, dialog_y + 160, 190, 45)
                    cancel_btn_rect = pg.Rect(dialog_x + 290, dialog_y + 160, 190, 45)
                    if confirm_btn_rect.collidepoint(event.pos):
                        self.save_active_level_commit()
                        self.confirming_save = False
                    elif cancel_btn_rect.collidepoint(event.pos):
                        self.confirming_save = False
                continue

            # Standard inputs
            if event.type == pg.KEYDOWN:
                if event.key == pg.K_ESCAPE:
                    self.running = False
                elif event.key == pg.K_s:
                    self.trigger_save()
                elif event.key == pg.K_r:
                    self.rollback_level()
                
                # Scroll timeline with keys
                elif event.key == pg.K_LEFT:
                    scroll_offset = 200 if pg.key.get_mods() & pg.KMOD_SHIFT else 50
                    self.timeline_offset = max(0.0, self.timeline_offset - scroll_offset)
                elif event.key == pg.K_RIGHT:
                    scroll_offset = 200 if pg.key.get_mods() & pg.KMOD_SHIFT else 50
                    max_offset = max(0, self.level_data.get("level_end_distance", 8000) - (self.timeline_w / self.zoom))
                    self.timeline_offset = min(max_offset, self.timeline_offset + scroll_offset)

            # Delegate to inputs in the inspector
            if self.selected_event:
                self.text_inputs["title"].handle_event(event)
                self.text_inputs["text"].handle_event(event)
                if self.selected_event["type"] == "npc":
                    self.sliders["radius"].handle_event(event)
                    if self.selected_event["params"].get("npc_type") == "generic":
                        self.btn_sprite_prev.handle_event(event)
                        self.btn_sprite_next.handle_event(event)
                    self.btn_npc_type_toggle.handle_event(event)
                elif self.selected_event["type"] == "enemy_wave":
                    self.sliders["count"].handle_event(event)
                elif self.selected_event["type"] == "interaction":
                    self.sliders["radius"].handle_event(event)
                
                self.btn_delete.handle_event(event)
                self.sync_back_to_data()
            else:
                self.btn_add_npc.handle_event(event)
                self.btn_add_enemy.handle_event(event)
                self.btn_add_interact.handle_event(event)

            # Navigation
            self.nav_prev.handle_event(event)
            self.nav_next.handle_event(event)
            self.btn_save.handle_event(event)
            self.btn_reset.handle_event(event)

            # Timeline interaction
            if event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
                # 1. Check if clicking on an event node in the timeline
                clicked_node = False
                events = self.level_data.get("world_events", [])
                for evt in events:
                    node_x = self.timeline_x + (evt["distance"] - self.timeline_offset) * self.zoom
                    node_y = self.timeline_y - 35
                    if abs(m_pos[0] - node_x) <= 15 and abs(m_pos[1] - node_y) <= 15:
                        self.selected_event = evt
                        self.dragging_event = evt
                        self.sync_inspector()
                        clicked_node = True
                        break
                
                # 2. Check if clicking level event list on the left
                if not clicked_node and 30 <= m_pos[0] <= 290 and 150 <= m_pos[1] <= 550:
                    y_offset = 150
                    for idx, evt in enumerate(events):
                        evt_rect = pg.Rect(30, y_offset + idx * 30, 260, 25)
                        if evt_rect.collidepoint(event.pos):
                            self.selected_event = evt
                            self.sync_inspector()
                            # Center timeline on clicked event
                            self.timeline_offset = max(0.0, evt["distance"] - (self.timeline_w / (2 * self.zoom)))
                            clicked_node = True
                            break

                # 3. If clicking background of the timeline, start dragging/scrolling timeline itself
                if not clicked_node and pg.Rect(self.timeline_x, self.timeline_y - 120, self.timeline_w, 150).collidepoint(event.pos):
                    self.dragging_event = "timeline"
                    self.drag_offset = event.pos[0]

            elif event.type == pg.MOUSEBUTTONUP:
                if event.button == 1:
                    self.dragging_event = None

            elif event.type == pg.MOUSEMOTION:
                if self.dragging_event == "timeline":
                    dx = event.pos[0] - self.drag_offset
                    self.drag_offset = event.pos[0]
                    # Moving mouse right (dx > 0) scrolls timeline left
                    self.timeline_offset -= dx / self.zoom
                    self.timeline_offset = max(0.0, self.timeline_offset)
                    max_offset = max(0, self.level_data.get("level_end_distance", 8000) - (self.timeline_w / self.zoom))
                    self.timeline_offset = min(max_offset, self.timeline_offset)
                elif self.dragging_event and self.dragging_event != "timeline":
                    # Dragging node
                    new_dist = self.timeline_offset + (event.pos[0] - self.timeline_x) / self.zoom
                    new_dist = max(0, min(new_dist, self.level_data.get("level_end_distance", 8000)))
                    self.dragging_event["distance"] = int(round(new_dist))

    def draw(self):
        self.screen.fill((20, 20, 28))
        m_pos = pg.mouse.get_pos()

        # ─ 1. Left Panel (Selector & Level Info) ──────────────
        pg.draw.rect(self.screen, (30, 30, 40), (0, 0, 320, SCREEN_H))
        pg.draw.rect(self.screen, (45, 45, 60), (0, 0, 320, SCREEN_H), width=2)

        self.nav_prev.draw(self.screen, self.ui_font)
        self.nav_next.draw(self.screen, self.ui_font)

        # Level name
        name_txt = self.title_font.render(self.level_data.get("level_name", "Level"), True, (255, 255, 255))
        self.screen.blit(name_txt, (30, 95))

        end_dist = self.level_data.get("level_end_distance", 8000)
        dist_lbl = self.ui_font.render(f"Length: {end_dist}m", True, (180, 180, 200))
        self.screen.blit(dist_lbl, (30, 125))

        # Event List
        evt_header = self.title_font.render("Level Events", True, (241, 196, 15))
        self.screen.blit(evt_header, (30, 170))

        events = self.level_data.get("world_events", [])
        y_offset = 210
        for idx, evt in enumerate(events):
            if idx >= 11:
                break # Clamp list display to avoid overflow
            
            evt_rect = pg.Rect(30, y_offset + idx * 32, 260, 28)
            is_active = (self.selected_event == evt)
            bg_col = (100, 150, 255, 120) if is_active else (40, 40, 50)
            
            # Hover check
            if evt_rect.collidepoint(m_pos):
                bg_col = (70, 70, 90) if not is_active else (120, 170, 255)
            
            pg.draw.rect(self.screen, bg_col, evt_rect, border_radius=4)
            pg.draw.rect(self.screen, (100, 100, 120), evt_rect, width=1, border_radius=4)

            # Render info label
            label = ""
            if evt["type"] == "npc":
                label = f"[NPC] {evt['params'].get('title', 'NPC')} ({evt['distance']}m)"
            elif evt["type"] == "enemy_wave":
                label = f"[Wave] {evt['params'].get('count', 3)}x {evt['params'].get('type', 'bat')} ({evt['distance']}m)"
            elif evt["type"] == "interaction":
                label = f"[Interact] {evt['params'].get('title', 'Sign')} ({evt['distance']}m)"

            lbl_surf = self.ui_font.render(label, True, (255, 255, 255))
            self.screen.blit(lbl_surf, (40, y_offset + idx * 32 + 4))

        # ─ 2. Center Panel (Timeline Viewer) ──────────────
        # Display Area
        preview_bg = pg.Rect(340, 20, self.timeline_w + 10, 420)
        pg.draw.rect(self.screen, (25, 25, 35), preview_bg, border_radius=8)
        pg.draw.rect(self.screen, (45, 45, 60), preview_bg, width=2, border_radius=8)

        # Help instructions
        help_title = self.title_font.render("Level Timeline Editor", True, (255, 255, 255))
        self.screen.blit(help_title, (360, 40))
        help_desc = self.small_font.render("Drag events left/right. Drag timeline background to scroll. Left/Right keys to scroll.", True, (160, 160, 180))
        self.screen.blit(help_desc, (360, 70))

        # Render timeline track line
        track_y = self.timeline_y
        pg.draw.line(self.screen, (120, 120, 140), (self.timeline_x, track_y), (self.timeline_x + self.timeline_w, track_y), 4)

        # Draw timeline rulers
        # We start drawing ticks from the next multiple of 100 before the offset
        start_tick = int(self.timeline_offset - (self.timeline_offset % 100))
        end_tick = start_tick + int(self.timeline_w / self.zoom) + 100
        
        for tick in range(start_tick, end_tick, 100):
            if tick > end_dist:
                break
            tick_x = self.timeline_x + (tick - self.timeline_offset) * self.zoom
            if self.timeline_x <= tick_x <= self.timeline_x + self.timeline_w:
                if tick % 500 == 0:
                    pg.draw.line(self.screen, (241, 196, 15), (tick_x, track_y - 12), (tick_x, track_y + 12), 2)
                    lbl = self.small_font.render(f"{tick}m", True, (241, 196, 15))
                    self.screen.blit(lbl, (tick_x - lbl.get_width() // 2, track_y + 18))
                else:
                    pg.draw.line(self.screen, (120, 120, 140), (tick_x, track_y - 6), (tick_x, track_y + 6), 1)

        # Render event nodes
        for evt in events:
            node_x = self.timeline_x + (evt["distance"] - self.timeline_offset) * self.zoom
            node_y = track_y - 35
            
            if self.timeline_x - 10 <= node_x <= self.timeline_x + self.timeline_w + 10:
                is_selected = (self.selected_event == evt)
                # Hover color
                h_active = abs(m_pos[0] - node_x) <= 15 and abs(m_pos[1] - node_y) <= 15
                
                # Draw vertical indicator line to the track
                line_color = (241, 196, 15) if is_selected else (80, 80, 100)
                line_w = 2 if is_selected else 1
                pg.draw.line(self.screen, line_color, (node_x, node_y), (node_x, track_y), line_w)

                # Node shape depending on type
                if evt["type"] == "npc":
                    node_color = (100, 150, 255) if not h_active else (130, 180, 255)
                    if is_selected: node_color = (255, 235, 100)
                    pg.draw.circle(self.screen, node_color, (int(node_x), int(node_y)), 12)
                    lbl = self.small_font.render("NPC", True, (255, 255, 255))
                    self.screen.blit(lbl, (node_x - lbl.get_width() // 2, node_y - 28))
                elif evt["type"] == "enemy_wave":
                    node_color = (231, 76, 60) if not h_active else (255, 106, 90)
                    if is_selected: node_color = (255, 235, 100)
                    # Triangle shape
                    points = [
                        (node_x, node_y - 12),
                        (node_x - 12, node_y + 12),
                        (node_x + 12, node_y + 12)
                    ]
                    pg.draw.polygon(self.screen, node_color, points)
                    lbl = self.small_font.render("Wave", True, (255, 255, 255))
                    self.screen.blit(lbl, (node_x - lbl.get_width() // 2, node_y - 28))
                elif evt["type"] == "interaction":
                    node_color = (155, 89, 182) if not h_active else (185, 119, 212)
                    if is_selected: node_color = (255, 235, 100)
                    rect = pg.Rect(node_x - 10, node_y - 10, 20, 20)
                    pg.draw.rect(self.screen, node_color, rect, border_radius=3)
                    lbl = self.small_font.render("Interact", True, (255, 255, 255))
                    self.screen.blit(lbl, (node_x - lbl.get_width() // 2, node_y - 28))

        # Display viewport distance range info
        start_m = int(self.timeline_offset)
        end_m = start_m + int(self.timeline_w / self.zoom)
        range_lbl = self.ui_font.render(f"Viewport: {start_m}m - {end_m}m", True, (150, 150, 170))
        self.screen.blit(range_lbl, (self.timeline_x, track_y - 100))

        # ─ 3. Inspector Panel (Right) ──────────────
        pg.draw.rect(self.screen, (30, 30, 40), (950, 0, 330, SCREEN_H))
        pg.draw.line(self.screen, (45, 45, 60), (950, 0), (950, SCREEN_H), 2)

        if self.selected_event:
            # Selected event details
            evt_title = self.title_font.render("Event Inspector", True, (241, 196, 15))
            self.screen.blit(evt_title, (970, 25))

            dist_lbl = self.ui_font.render(f"Distance: {self.selected_event['distance']} meters", True, (255, 255, 255))
            self.screen.blit(dist_lbl, (970, 65))
            
            type_lbl = self.small_font.render(f"Event Type: {self.selected_event['type'].upper()}  (ID: {self.selected_event['id']})", True, (160, 160, 180))
            self.screen.blit(type_lbl, (970, 85))

            self.text_inputs["title"].draw(self.screen, self.ui_font)
            self.text_inputs["text"].draw(self.screen, self.ui_font)

            if self.selected_event["type"] == "npc":
                self.sliders["radius"].draw(self.screen, self.ui_font)
                
                # Show sprite option selectors if generic type
                params = self.selected_event["params"]
                if params.get("npc_type") == "generic":
                    s_label = self.small_font.render("NPC Sprite Dir:", True, (200, 200, 200))
                    self.screen.blit(s_label, (970, 335))
                    
                    self.btn_sprite_prev.draw(self.screen, self.ui_font)
                    self.btn_sprite_next.draw(self.screen, self.ui_font)
                    
                    # Display active folder name
                    folder_name = os.path.basename(params.get("sprite_dir", "").rstrip("/"))
                    f_lbl = self.ui_font.render(folder_name, True, (255, 255, 255))
                    self.screen.blit(f_lbl, (f_lbl.get_rect(center=(1110, 377))))
                else:
                    w_label = self.ui_font.render("Dedicated Wizard NPC", True, (255, 255, 255))
                    self.screen.blit(w_label, (970, 360))

                self.btn_npc_type_toggle.draw(self.screen, self.ui_font)

            elif self.selected_event["type"] == "enemy_wave":
                self.sliders["count"].draw(self.screen, self.ui_font)

            elif self.selected_event["type"] == "interaction":
                self.sliders["radius"].draw(self.screen, self.ui_font)

            self.btn_delete.draw(self.screen, self.ui_font)

            # Draw preview container box
            preview_box = pg.Rect(970, 465, 280, 120)
            pg.draw.rect(self.screen, (25, 25, 35), preview_box, border_radius=6)
            pg.draw.rect(self.screen, (80, 80, 100), preview_box, width=1, border_radius=6)

            # Draw preview label
            prev_label = self.small_font.render("Live Preview Simulation", True, (160, 160, 180))
            self.screen.blit(prev_label, (980, 470))

            # Load and render preview frames
            frames = self.load_preview_animation()
            if frames:
                frame = frames[self.preview_frame_idx % len(frames)]
                f_rect = frame.get_rect(center=preview_box.center)
                self.screen.blit(frame, f_rect)
        else:
            # Creation buttons
            c_title = self.title_font.render("Creation Toolbar", True, (255, 255, 255))
            self.screen.blit(c_title, (970, 25))

            self.btn_add_npc.draw(self.screen, self.ui_font)
            self.btn_add_enemy.draw(self.screen, self.ui_font)
            self.btn_add_interact.draw(self.screen, self.ui_font)

            # Draw empty preview placeholder box
            preview_box = pg.Rect(970, 465, 280, 120)
            pg.draw.rect(self.screen, (25, 25, 35), preview_box, border_radius=6)
            pg.draw.rect(self.screen, (80, 80, 100), preview_box, width=1, border_radius=6)
            p_lbl = self.small_font.render("Select an event to preview", True, (120, 120, 140))
            self.screen.blit(p_lbl, p_lbl.get_rect(center=preview_box.center))

        # ─ 4. Bottom Panel ──────────────
        self.btn_save.draw(self.screen, self.ui_font)
        self.btn_reset.draw(self.screen, self.ui_font)

        # ─ 5. Write Confirmation Dialog (Overlay) ──────────────
        if self.confirming_save:
            # 1. Darken the screen
            overlay = pg.Surface((SCREEN_W, SCREEN_H), pg.SRCALPHA)
            overlay.fill((10, 10, 15, 200))
            self.screen.blit(overlay, (0, 0))

            # 2. Draw Dialog Box
            dialog_w, dialog_h = 520, 240
            dialog_x = (SCREEN_W - dialog_w) // 2
            dialog_y = (SCREEN_H - dialog_h) // 2
            dialog_rect = pg.Rect(dialog_x, dialog_y, dialog_w, dialog_h)

            pg.draw.rect(self.screen, (25, 25, 35), dialog_rect, border_radius=16)
            pg.draw.rect(self.screen, (241, 196, 15), dialog_rect, width=3, border_radius=16)

            title_text = self.title_font.render("COMMIT LEVEL CHANGES?", True, (241, 196, 15))
            desc_text_1 = self.ui_font.render("Write and lock configurations to level database?", True, (240, 240, 240))
            desc_text_2 = self.small_font.render(f"This commits changes directly to: {self.level_files[self.active_file_idx]}", True, (160, 160, 180))

            title_rect = title_text.get_rect(centerx=dialog_rect.centerx, y=dialog_rect.y + 30)
            desc_rect_1 = desc_text_1.get_rect(centerx=dialog_rect.centerx, y=dialog_rect.y + 85)
            desc_rect_2 = desc_text_2.get_rect(centerx=dialog_rect.centerx, y=dialog_rect.y + 115)

            self.screen.blit(title_text, title_rect)
            self.screen.blit(desc_text_1, desc_rect_1)
            self.screen.blit(desc_text_2, desc_rect_2)

            # 3. Buttons (Confirm / Cancel)
            confirm_btn_rect = pg.Rect(dialog_x + 40, dialog_y + 160, 190, 45)
            cancel_btn_rect = pg.Rect(dialog_x + 290, dialog_y + 160, 190, 45)

            confirm_hover = confirm_btn_rect.collidepoint(m_pos)
            cancel_hover = cancel_btn_rect.collidepoint(m_pos)

            confirm_color = (46, 204, 113) if confirm_hover else (39, 174, 96)
            cancel_color = (231, 76, 60) if cancel_hover else (192, 57, 43)

            pg.draw.rect(self.screen, confirm_color, confirm_btn_rect, border_radius=8)
            pg.draw.rect(self.screen, cancel_color, cancel_btn_rect, border_radius=8)

            confirm_lbl = self.ui_font.render("CONFIRM (ENTER)", True, (255, 255, 255))
            cancel_lbl = self.ui_font.render("CANCEL (ESC)", True, (255, 255, 255))

            self.screen.blit(confirm_lbl, confirm_lbl.get_rect(center=confirm_btn_rect.center))
            self.screen.blit(cancel_lbl, cancel_lbl.get_rect(center=cancel_btn_rect.center))

        pg.display.flip()

    def run(self):
        while self.running:
            dt = self.clock.tick(60) / 1000.0
            self.handle_events()
            self.update(dt)
            self.draw()

    def cleanup(self):
        pg.quit()


if __name__ == "__main__":
    app = LevelEditorApp()
    try:
        app.run()
    finally:
        app.cleanup()
