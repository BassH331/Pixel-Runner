#!/usr/bin/env python3
"""
storyline_editor.py — Storyline & Relic Plugin Editor for Pixel-Runner.

GUI editor tool to configure, tweak, and test narrative relics, memory flashback text,
corruption physics multipliers, vignette opacity, 5-boss hierarchy, and Angel vs. Devil micro-barks.
"""

import os
import sys
import json
import time
import math
from datetime import datetime
from typing import Optional, Dict, List, Any
import pygame as pg

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from src.game.systems.storyline_config_manager import StorylineConfigManager, CONFIG_PATH

pg.init()
pg.font.init()

# ── Window ────────────────────────────────────────────────────────────────────
SW, SH = 1280, 800
screen = pg.display.set_mode((SW, SH))
pg.display.set_caption("Storyline & Relic Plugin Editor  ·  Pixel Runner")
clock = pg.time.Clock()

# ── Fonts ─────────────────────────────────────────────────────────────────────
def make_font(size, bold=False):
    return pg.font.SysFont("dejavusans,ubuntu,arial,helvetica,sans-serif", size, bold=bold)

F_TITLE  = make_font(20, bold=True)
F_HEAD   = make_font(15, bold=True)
F_BODY   = make_font(13)
F_SMALL  = make_font(11)

# ── Colors ────────────────────────────────────────────────────────────────────
C_BG         = ( 13,  15,  23)
C_PANEL      = ( 22,  26,  38)
C_PANEL_DARK = ( 16,  19,  29)
C_HEADER     = ( 28,  34,  52)
C_BORDER     = ( 48,  58,  85)
C_BORDER_HI  = ( 80, 100, 150)
C_TEXT       = (230, 235, 248)
C_MUTED      = (130, 142, 170)
C_CYAN       = (  0, 220, 255)
C_GREEN      = (  0, 220, 110)
C_GOLD       = (255, 215,  60)
C_PURPLE     = (160,  60, 255)
C_RED        = (220,  50,  70)
C_WHITE      = (255, 255, 255)
C_SEL        = ( 35,  70, 110)

class StorylineEditor:
    def __init__(self):
        self.config_mgr = StorylineConfigManager.get_instance()
        self.data = json.loads(json.dumps(self.config_mgr.data))  # Deep copy

        self.current_tab = "relics"  # "relics", "corruption", "bosses"
        self.relic_keys = list(self.data.get("relics", {}).keys())
        self.selected_relic_index = 0 if self.relic_keys else -1

        # Text input active tracking
        self.active_input_field: Optional[str] = None
        self.status_msg: str = "Ready. Select a tab to edit parameters."
        self.status_timer: float = 0.0

        # Flashback Preview Animation
        self.preview_flashback: Optional[dict] = None
        self.preview_timer: float = 0.0

    def get_selected_relic(self) -> Optional[dict]:
        if 0 <= self.selected_relic_index < len(self.relic_keys):
            r_key = self.relic_keys[self.selected_relic_index]
            return self.data["relics"].get(r_key)
        return None

    def trigger_preview_flashback(self, relic: dict):
        self.preview_flashback = relic
        self.preview_timer = float(relic.get("flashback_duration", 3.5))

    def save_changes(self):
        success = self.config_mgr.save_config(self.data)
        if success:
            self.status_msg = "Successfully saved changes to game_data/storyline_config.json!"
        else:
            self.status_msg = "Error saving configuration!"
        self.status_timer = 4.0

    def update(self, dt: float):
        if self.status_timer > 0:
            self.status_timer -= dt

        if self.preview_timer > 0:
            self.preview_timer = max(0.0, self.preview_timer - dt)
            if self.preview_timer <= 0:
                self.preview_flashback = None

        from src.game.effects.lightning_effect import LightningEffect
        LightningEffect.get_instance().update(dt)

    def handle_event(self, event: pg.event.Event):
        if event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos

            # Tab Buttons
            if 30 <= my <= 65:
                if 20 <= mx <= 160:
                    self.current_tab = "relics"
                elif 170 <= mx <= 310:
                    self.current_tab = "corruption"
                elif 320 <= mx <= 460:
                    self.current_tab = "bosses"

            # Save Button
            if SW - 160 <= mx <= SW - 20 and 20 <= my <= 60:
                self.save_changes()

            # Tab-specific click handling
            if self.current_tab == "relics":
                # Relic List selection
                if 20 <= mx <= 280:
                    y_start = 100
                    for i in range(len(self.relic_keys)):
                        if y_start + i * 55 <= my <= y_start + i * 55 + 48:
                            self.selected_relic_index = i
                            self.active_input_field = None
                            break

                # Preview Flashback Button & Test Lightning Button
                relic = self.get_selected_relic()
                if relic and 320 <= mx <= 560 and 400 <= my <= 445:
                    self.trigger_preview_flashback(relic)
                elif 580 <= mx <= 820 and 400 <= my <= 445:
                    from src.game.effects.lightning_effect import LightningEffect
                    LightningEffect.get_instance().trigger(duration=1.0)

                # Field Clicks
                if relic and 320 <= mx <= 800:
                    if 130 <= my <= 165:
                        self.active_input_field = "title"
                    elif 200 <= my <= 235:
                        self.active_input_field = "category"
                    elif 270 <= my <= 370:
                        self.active_input_field = "memory_text"

            elif self.current_tab == "corruption":
                corr = self.data.get("corruption", {})
                # Instability Checkbox
                if 320 <= mx <= 345 and 280 <= my <= 305:
                    corr["instability_enabled"] = not corr.get("instability_enabled", True)

        elif event.type == pg.KEYDOWN:
            if self.active_input_field and self.current_tab == "relics":
                relic = self.get_selected_relic()
                if relic:
                    current_val = relic.get(self.active_input_field, "")
                    if event.key == pg.K_BACKSPACE:
                        relic[self.active_input_field] = current_val[:-1]
                    elif event.key in (pg.K_RETURN, pg.K_ESCAPE):
                        self.active_input_field = None
                    else:
                        if len(event.unicode) > 0 and ord(event.unicode) >= 32:
                            relic[self.active_input_field] = current_val + event.unicode

    def draw(self, surf: pg.Surface):
        surf.fill(C_BG)

        # ── Header ─────────────────────────────────────────────────────────────
        pg.draw.rect(surf, C_HEADER, (0, 0, SW, 75))
        pg.draw.line(surf, C_BORDER, (0, 75), (SW, 75), 2)

        title_surf = F_TITLE.render("STORYLINE & RELIC PLUGIN EDITOR", True, C_GOLD)
        surf.blit(title_surf, (20, 8))

        # Tabs
        tabs = [("relics", "📜 Relics & Lore"), ("corruption", "⚡ Corruption Mechanics"), ("bosses", "👑 Bosses & Whisperers")]
        for i, (tab_id, tab_name) in enumerate(tabs):
            tx = 20 + i * 150
            is_active = (self.current_tab == tab_id)
            btn_col = C_SEL if is_active else C_PANEL
            border_col = C_GOLD if is_active else C_BORDER
            pg.draw.rect(surf, btn_col, (tx, 35, 140, 32), border_radius=6)
            pg.draw.rect(surf, border_col, (tx, 35, 140, 32), width=2, border_radius=6)
            t_surf = F_HEAD.render(tab_name, True, C_TEXT if is_active else C_MUTED)
            surf.blit(t_surf, (tx + 10, 42))

        # Save Button
        pg.draw.rect(surf, C_GREEN, (SW - 160, 20, 140, 40), border_radius=8)
        s_surf = F_HEAD.render("💾 SAVE & APPLY", True, (0, 0, 0))
        surf.blit(s_surf, (SW - 150, 30))

        # ── Content Panels ──────────────────────────────────────────────────────
        if self.current_tab == "relics":
            self.draw_relics_tab(surf)
        elif self.current_tab == "corruption":
            self.draw_corruption_tab(surf)
        elif self.current_tab == "bosses":
            self.draw_bosses_tab(surf)

        # Status Bar
        pg.draw.rect(surf, C_PANEL_DARK, (0, SH - 35, SW, 35))
        st_surf = F_BODY.render(self.status_msg, True, C_CYAN if self.status_timer > 0 else C_MUTED)
        surf.blit(st_surf, (20, SH - 26))

        # Render Flashback Preview if active
        self.draw_flashback_preview(surf)

        # Render Lightning Effect if active
        from src.game.effects.lightning_effect import LightningEffect
        LightningEffect.get_instance().render(surf)

    def draw_relics_tab(self, surf: pg.Surface):
        # Left Panel - Relic Selector
        pg.draw.rect(surf, C_PANEL, (20, 90, 260, SH - 140), border_radius=8)
        pg.draw.rect(surf, C_BORDER, (20, 90, 260, SH - 140), width=2, border_radius=8)

        head_surf = F_HEAD.render("SELECT RELIC", True, C_GOLD)
        surf.blit(head_surf, (35, 105))

        y = 135
        for i, r_key in enumerate(self.relic_keys):
            relic = self.data["relics"][r_key]
            is_sel = (i == self.selected_relic_index)
            col = C_SEL if is_sel else C_PANEL_DARK
            b_col = C_GOLD if is_sel else C_BORDER
            pg.draw.rect(surf, col, (30, y, 240, 48), border_radius=6)
            pg.draw.rect(surf, b_col, (30, y, 240, 48), width=1, border_radius=6)

            r_title = F_HEAD.render(relic.get("title", r_key), True, C_TEXT)
            r_cat = F_SMALL.render(f"Category: {relic.get('category', 'Memory')}", True, C_MUTED)
            surf.blit(r_title, (42, y + 6))
            surf.blit(r_cat, (42, y + 26))
            y += 55

        # Right Panel - Relic Form Editor
        pg.draw.rect(surf, C_PANEL, (300, 90, SW - 320, SH - 140), border_radius=8)
        pg.draw.rect(surf, C_BORDER, (300, 90, SW - 320, SH - 140), width=2, border_radius=8)

        relic = self.get_selected_relic()
        if not relic:
            return

        # Title Field
        surf.blit(F_HEAD.render("Relic Title:", True, C_CYAN), (320, 110))
        t_active = (self.active_input_field == "title")
        pg.draw.rect(surf, C_PANEL_DARK, (320, 130, 480, 35), border_radius=6)
        pg.draw.rect(surf, C_GOLD if t_active else C_BORDER, (320, 130, 480, 35), width=2, border_radius=6)
        surf.blit(F_BODY.render(relic.get("title", ""), True, C_TEXT), (330, 138))

        # Category Field
        surf.blit(F_HEAD.render("Category:", True, C_CYAN), (320, 180))
        c_active = (self.active_input_field == "category")
        pg.draw.rect(surf, C_PANEL_DARK, (320, 200, 480, 35), border_radius=6)
        pg.draw.rect(surf, C_GOLD if c_active else C_BORDER, (320, 200, 480, 35), width=2, border_radius=6)
        surf.blit(F_BODY.render(relic.get("category", ""), True, C_TEXT), (330, 208))

        # Memory Text Field
        surf.blit(F_HEAD.render("Plain-Spoken Memory Flashback Text:", True, C_CYAN), (320, 250))
        m_active = (self.active_input_field == "memory_text")
        pg.draw.rect(surf, C_PANEL_DARK, (320, 270, 580, 100), border_radius=6)
        pg.draw.rect(surf, C_GOLD if m_active else C_BORDER, (320, 270, 580, 100), width=2, border_radius=6)
        
        # Wrapped memory text
        mem_text = relic.get("memory_text", "")
        surf.blit(F_BODY.render(mem_text, True, C_TEXT), (330, 280))

        # Test Flashback Preview Button & Test Staff Lightning Button
        pg.draw.rect(surf, C_PURPLE, (320, 400, 240, 45), border_radius=8)
        surf.blit(F_HEAD.render("👁️ TEST FLASHBACK PREVIEW", True, C_WHITE), (330, 412))

        pg.draw.rect(surf, C_CYAN, (580, 400, 240, 45), border_radius=8)
        surf.blit(F_HEAD.render("⚡ TEST STAFF LIGHTNING", True, (0, 0, 0)), (590, 412))

    def draw_corruption_tab(self, surf: pg.Surface):
        pg.draw.rect(surf, C_PANEL, (20, 90, SW - 40, SH - 140), border_radius=8)
        pg.draw.rect(surf, C_BORDER, (20, 90, SW - 40, SH - 140), width=2, border_radius=8)

        corr = self.data.get("corruption", {})
        surf.blit(F_TITLE.render("⚡ SHADOW TRANSFORM CORRUPTION PARAMETERS", True, C_GOLD), (40, 110))

        # Sliders/Values Information
        y = 160
        params = [
            ("Dash Speed Multiplier", corr.get("dash_speed_multiplier", 1.5), "+50% boost when transformed (default 1.5x)"),
            ("Attack Damage Multiplier", corr.get("damage_multiplier", 1.5), "+50% damage boost when transformed (default 1.5x)"),
            ("Vignette Max Alpha", corr.get("vignette_alpha", 180), "Dark shadow vignette screen intensity (0 - 255)"),
        ]

        for p_name, p_val, p_desc in params:
            surf.blit(F_HEAD.render(f"{p_name}:  {p_val}", True, C_CYAN), (40, y))
            surf.blit(F_BODY.render(p_desc, True, C_MUTED), (40, y + 22))
            y += 70

        # Checkbox Instability
        surf.blit(F_HEAD.render("Control Physics Instability:", True, C_CYAN), (40, y))
        is_inst = corr.get("instability_enabled", True)
        pg.draw.rect(surf, C_PANEL_DARK, (320, y - 5, 25, 25), border_radius=4)
        pg.draw.rect(surf, C_GOLD if is_inst else C_BORDER, (320, y - 5, 25, 25), width=2, border_radius=4)
        if is_inst:
            surf.blit(F_HEAD.render("✓", True, C_GREEN), (326, y - 4))
        surf.blit(F_BODY.render("Applies subtle micro-jitter to movement when transformed", True, C_MUTED), (360, y))

    def draw_bosses_tab(self, surf: pg.Surface):
        pg.draw.rect(surf, C_PANEL, (20, 90, SW - 40, SH - 140), border_radius=8)
        pg.draw.rect(surf, C_BORDER, (20, 90, SW - 40, SH - 140), width=2, border_radius=8)

        surf.blit(F_TITLE.render("👑 5-BOSS HIERARCHY & PROGRESSION ORDER", True, C_GOLD), (40, 110))

        bosses = self.data.get("boss_hierarchy", [])
        y = 160
        for i, b_name in enumerate(bosses):
            pg.draw.rect(surf, C_PANEL_DARK, (40, y, 500, 45), border_radius=6)
            pg.draw.rect(surf, C_BORDER, (40, y, 500, 45), width=1, border_radius=6)
            surf.blit(F_HEAD.render(f"Act Boss #{i+1}:  {b_name.upper().replace('_', ' ')}", True, C_TEXT), (55, y + 12))
            y += 55

    def draw_flashback_preview(self, surf: pg.Surface):
        if not self.preview_flashback or self.preview_timer <= 0:
            return

        w, h = surf.get_size()
        progress = self.preview_timer / float(self.preview_flashback.get("flashback_duration", 3.5))
        alpha_factor = math.sin(progress * math.pi)

        # Sepia overlay
        sepia_surf = pg.Surface((w, h), pg.SRCALPHA)
        sepia_surf.fill((40, 20, 5, int(110 * alpha_factor)))
        surf.blit(sepia_surf, (0, 0))

        # Banner Card
        bw, bh = int(w * 0.72), 95
        bx, by = (w - bw) // 2, int(h * 0.15)
        banner = pg.Surface((bw, bh), pg.SRCALPHA)
        pg.draw.rect(banner, (15, 10, 25, int(220 * alpha_factor)), (0, 0, bw, bh), border_radius=8)
        pg.draw.rect(banner, (220, 180, 70, int(255 * alpha_factor)), (0, 0, bw, bh), width=2, border_radius=8)

        t_surf = F_HEAD.render(f"MEMORY FLASHBACK: {self.preview_flashback.get('title', '').upper()}", True, C_GOLD)
        m_surf = F_BODY.render(f'"{self.preview_flashback.get("memory_text", "")}"', True, C_TEXT)
        banner.blit(t_surf, (20, 12))
        banner.blit(m_surf, (20, 48))
        surf.blit(banner, (bx, by))

def main():
    editor = StorylineEditor()
    running = True

    while running:
        dt = clock.tick(60) / 1000.0
        for event in pg.event.get():
            if event.type == pg.QUIT:
                running = False
            editor.handle_event(event)

        editor.update(dt)
        editor.draw(screen)
        pg.display.flip()

    pg.quit()

if __name__ == "__main__":
    main()
