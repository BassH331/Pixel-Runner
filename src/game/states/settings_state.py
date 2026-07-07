import pygame as pg
from v3x_zulfiqar_gideon import State, AssetManager, UIButton, SettingsManager, UITheme

class SettingsState(State):
    """
    Premium settings screen allowing customization of:
      - Graphics Quality (Low, Medium, High)
      - FPS Cap (30, 60, 120, Unlimited)
      - Music Volume (0% - 100%)
      - SFX Volume (0% - 100%)
      
    Supports both Keyboard/Gamepad navigation and direct mouse clicks/hovering.
    """
    
    def __init__(self, manager):
        super().__init__(manager)
        self.settings = SettingsManager()
        
        # Dimensions
        surface = pg.display.get_surface()
        self.width = surface.get_width()
        self.height = surface.get_height()
        
        # Overlay configurations
        cfg = UITheme.get("overlays")
        self._cfg = cfg
        
        # Dark backdrop overlay
        self._backdrop = pg.Surface((self.width, self.height), pg.SRCALPHA)
        self._backdrop.fill((0, 0, 0, cfg.get("backdrop_alpha", 140)))
        
        # Load and scale boards
        stone_scale = 0.59
        parchment_scale = 0.55
        
        raw_stone = AssetManager.get_texture(cfg["stone_path"])
        stone_w = int(self.width * stone_scale)
        stone_h = int(stone_w * (raw_stone.get_height() / raw_stone.get_width()))
        self._stone = pg.transform.smoothscale(raw_stone, (stone_w, stone_h))
        self._stone_rect = self._stone.get_rect(center=(self.width // 2, self.height // 2))
        
        raw_parch = AssetManager.get_texture(cfg["parchment_path"])
        parch_w = int(self.width * parchment_scale)
        parch_h = int(parch_w * (raw_parch.get_height() / raw_parch.get_width()))
        self._parchment = pg.transform.smoothscale(raw_parch, (parch_w, parch_h))
        self._parch_rect = self._parchment.get_rect(center=(self.width // 2, self.height // 2))
        
        # Fonts
        self._title_font = AssetManager.get_font(cfg["title_font_path"], cfg["title_font_size"])
        self._label_font = AssetManager.get_font(cfg["body_font_path"], cfg["font_size"])
        
        # Color palettes
        self.title_color = cfg.get("title_color", (45, 25, 10))
        self.text_color = cfg.get("text_color", (60, 40, 20))
        self.highlight_color = (130, 20, 20) # Reddish-gold highlight for selected
        self.arrow_color = (100, 75, 50)
        self.arrow_hover_color = (190, 130, 30) # Bright gold on hover
        
        # Load current settings values
        self.current_quality = self.settings.get("graphics_quality")
        self.current_fps = self.settings.get("fps_cap")
        self.current_music = int(self.settings.get("music_volume") * 100)
        self.current_sfx = int(self.settings.get("sfx_volume") * 100)
        
        # Setup settings options definitions
        self.options = [
            {
                "id": "quality",
                "label": "Graphics Quality",
                "type": "choice",
                "choices": ["low", "medium", "high"],
                "labels": ["Low", "Medium", "High"]
            },
            {
                "id": "fps",
                "label": "Frame Rate Cap",
                "type": "choice",
                "choices": [30, 60, 120, 0],
                "labels": ["30 FPS", "60 FPS", "120 FPS", "Unlimited"]
            },
            {
                "id": "music",
                "label": "Music Volume",
                "type": "range",
                "min": 0,
                "max": 100,
                "step": 10
            },
            {
                "id": "sfx",
                "label": "SFX Volume",
                "type": "range",
                "min": 0,
                "max": 100,
                "step": 10
            }
        ]
        
        # Selection states
        self.selected_index = 0
        
        # Coordinates layout
        self.row_start_y = self._parch_rect.top + int(self._parch_rect.height * 0.26)
        self.row_spacing = int(self._parch_rect.height * 0.11)
        self.label_x = self._parch_rect.left + int(self._parch_rect.width * 0.12)
        self.val_center_x = self._parch_rect.right - int(self._parch_rect.width * 0.22)
        
        # Back button
        btn_y = self._parch_rect.bottom - int(self._parch_rect.height * 0.18)
        self.back_button = UIButton(
            "Back",
            x=self.width // 2,
            y=btn_y,
            size="medium",
            scale=0.8,
            on_click=self._on_back
        )
        
        # Dynamic interactable zones (updated every frame/draw for correctness)
        self.hitboxes = []
        
    def _on_back(self):
        # Save final state just in case
        self.settings.save()
        self.manager.pop()
        
    def _get_value(self, option_id):
        if option_id == "quality": return self.current_quality
        if option_id == "fps": return self.current_fps
        if option_id == "music": return self.current_music
        if option_id == "sfx": return self.current_sfx
        return None
        
    def _set_value(self, option_id, value):
        if option_id == "quality":
            self.current_quality = value
            self.settings.set("graphics_quality", value)
        elif option_id == "fps":
            self.current_fps = value
            self.settings.set("fps_cap", value)
        elif option_id == "music":
            self.current_music = value
            self.settings.set("music_volume", value / 100.0)
            self.manager.audio_manager.set_music_volume(value / 100.0)
        elif option_id == "sfx":
            self.current_sfx = value
            self.settings.set("sfx_volume", value / 100.0)
            self.manager.audio_manager.set_sfx_volume(value / 100.0)
            self.manager.audio_manager.play_sound("defend")
            
    def _change_val(self, direction):
        """direction: -1 for left/down, +1 for right/up"""
        opt = self.options[self.selected_index]
        opt_id = opt["id"]
        curr_val = self._get_value(opt_id)
        
        if opt["type"] == "choice":
            choices = opt.get("choices")
            if isinstance(choices, list) and curr_val is not None and curr_val in choices:
                idx = next(i for i, val in enumerate(choices) if val == curr_val)
                new_idx = (idx + direction) % len(choices)
                self._set_value(opt_id, choices[new_idx])
        elif opt["type"] == "range":
            step = opt.get("step", 10)
            opt_min = opt.get("min", 0)
            opt_max = opt.get("max", 100)
            if curr_val is not None:
                new_val = curr_val + direction * step
                new_val = max(opt_min, min(opt_max, new_val))
                if new_val != curr_val:
                    self._set_value(opt_id, new_val)
                
    def handle_event(self, event):
        # Pass to back button first if mouse event
        if event.type in (pg.MOUSEBUTTONDOWN, pg.MOUSEBUTTONUP, pg.MOUSEMOTION):
            self.back_button.handle_event(event)
            
        if event.type == pg.MOUSEBUTTONDOWN:
            if event.button == 1: # Left click
                mouse_pos = event.pos
                # Check hitboxes
                for hb in self.hitboxes:
                    if hb["rect"].collidepoint(mouse_pos):
                        if hb["type"] == "row":
                            self.selected_index = hb["index"]
                            self.manager.audio_manager.play_sound("defend")
                        elif hb["type"] == "left":
                            self.selected_index = hb["index"]
                            self._change_val(-1)
                        elif hb["type"] == "right":
                            self.selected_index = hb["index"]
                            self._change_val(1)
                            
        elif event.type == pg.KEYDOWN:
            if event.key in (pg.K_UP, pg.K_w):
                self.selected_index = (self.selected_index - 1) % (len(self.options) + 1)
                self.manager.audio_manager.play_sound("defend")
            elif event.key in (pg.K_DOWN, pg.K_s):
                self.selected_index = (self.selected_index + 1) % (len(self.options) + 1)
                self.manager.audio_manager.play_sound("defend")
            elif event.key in (pg.K_LEFT, pg.K_a):
                if self.selected_index < len(self.options):
                    self._change_val(-1)
            elif event.key in (pg.K_RIGHT, pg.K_d):
                if self.selected_index < len(self.options):
                    self._change_val(1)
            elif event.key in (pg.K_RETURN, pg.K_SPACE):
                if self.selected_index == len(self.options):
                    self._on_back()
            elif event.key == pg.K_ESCAPE:
                self._on_back()
                
    def update(self, dt):
        self.back_button.update(dt)
        
    def draw(self, surface):
        # 1. Backdrop
        surface.blit(self._backdrop, (0, 0))
        
        # 2. Boards
        surface.blit(self._stone, self._stone_rect)
        surface.blit(self._parchment, self._parch_rect)
        
        # 3. Settings Title
        title_surf = self._title_font.render("SETTINGS", True, self.title_color)
        title_x = self._parch_rect.centerx - title_surf.get_width() // 2
        title_y = self._parch_rect.top + int(self._parch_rect.height * 0.12)
        surface.blit(title_surf, (title_x, title_y))
        
        # 4. Draw options
        self.hitboxes = []
        mouse_pos = pg.mouse.get_pos()
        
        for idx, opt in enumerate(self.options):
            row_y = self.row_start_y + idx * self.row_spacing
            is_selected = (idx == self.selected_index)
            
            # Row hover logic
            row_rect = pg.Rect(self.label_x - 10, row_y - 8, self._parch_rect.width - int(self._parch_rect.width * 0.24) + 20, 42)
            is_hovered = row_rect.collidepoint(mouse_pos)
            
            # Register row selection hitbox
            self.hitboxes.append({
                "type": "row",
                "rect": row_rect,
                "index": idx
            })
            
            color = self.highlight_color if (is_selected or is_hovered) else self.text_color
            
            # Draw label
            lbl_surf = self._label_font.render(opt["label"], True, color)
            surface.blit(lbl_surf, (self.label_x, row_y))
            
            # Draw value selector
            curr_val = self._get_value(opt["id"])
            if opt["type"] == "choice":
                choices = opt.get("choices")
                labels = opt.get("labels")
                if isinstance(choices, list) and isinstance(labels, list) and curr_val is not None and curr_val in choices:
                    label_idx = next(i for i, val in enumerate(choices) if val == curr_val)
                    val_text = str(labels[label_idx])
                else:
                    val_text = str(curr_val)
            else:
                val_text = f"{curr_val}%"
                
            val_surf = self._label_font.render(val_text, True, color)
            val_rect = val_surf.get_rect(center=(self.val_center_x, row_y + lbl_surf.get_height() // 2))
            surface.blit(val_surf, val_rect)
            
            # Left arrow
            left_arrow_rect = pg.Rect(self.val_center_x - 90, row_y + 2, 28, 28)
            arrow_l_hover = left_arrow_rect.collidepoint(mouse_pos)
            self.hitboxes.append({
                "type": "left",
                "rect": left_arrow_rect,
                "index": idx
            })
            
            # Draw left arrow triangle
            al_color = self.arrow_hover_color if arrow_l_hover else self.arrow_color
            p1 = (self.val_center_x - 70, row_y + 6)
            p2 = (self.val_center_x - 85, row_y + 16)
            p3 = (self.val_center_x - 70, row_y + 26)
            pg.draw.polygon(surface, al_color, [p1, p2, p3])
            
            # Right arrow
            right_arrow_rect = pg.Rect(self.val_center_x + 60, row_y + 2, 28, 28)
            arrow_r_hover = right_arrow_rect.collidepoint(mouse_pos)
            self.hitboxes.append({
                "type": "right",
                "rect": right_arrow_rect,
                "index": idx
            })
            
            # Draw right arrow triangle
            ar_color = self.arrow_hover_color if arrow_r_hover else self.arrow_color
            p1 = (self.val_center_x + 70, row_y + 6)
            p2 = (self.val_center_x + 85, row_y + 16)
            p3 = (self.val_center_x + 70, row_y + 26)
            pg.draw.polygon(surface, ar_color, [p1, p2, p3])
            
        # Draw Back Button
        is_back_selected = (self.selected_index == len(self.options))
        if is_back_selected:
            # Draw a subtle selection highlight around the back button
            back_rect = self.back_button._internal.rect
            rect_to_draw = (back_rect.x - 4, back_rect.y - 4, back_rect.width + 8, back_rect.height + 8)
            pg.draw.rect(surface, self.highlight_color, rect_to_draw, 2, border_radius=4)
            
        self.back_button.draw(surface)
