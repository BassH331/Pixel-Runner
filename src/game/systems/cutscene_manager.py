"""
CutsceneManager — Decoupled cutscene and dialogue overlay manager.

Handles speaker camera focus zoom, cutscene phase progression, advance input,
and ethereal dialogue banner overlays.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, Any
import pygame as pg

from src.game.entities.generic_npc import _GenericNPCState

if TYPE_CHECKING:
    from src.game.states.game_state import GameState


class CutsceneManager:
    """Manages NPC cutscenes, speaker camera zoom, and dialogue overlay UI."""

    def __init__(self, game_state: GameState) -> None:
        self.game = game_state

    @property
    def is_interacting(self) -> bool:
        """Whether player is currently locked in NPC dialogue, cutscene, or Spirit trance."""
        intro_npc_locked = any(
            getattr(npc, "is_intro_npc", False)
            and getattr(npc, "is_trance_active", False)
            and not getattr(npc, "is_death_complete", False)
            for npc in self.game.npc_group
        )
        spirit_npc_locked = any(
            getattr(npc, "is_spirit_of_scythe", False)
            and getattr(npc, "is_trance_active", False)
            and not getattr(npc, "is_death_complete", False)
            for npc in self.game.npc_group
        )
        sky_fall_npc_locked = any(
            getattr(npc, "is_sky_fall_npc", False)
            and getattr(npc, "is_trance_active", False)
            and not getattr(npc, "is_death_complete", False)
            for npc in self.game.npc_group
        )
        active_dialogue_npc = (
            self.game.objective_display.is_active
            and self.game._current_interacting_npc is not None
            and not getattr(self.game._current_interacting_npc, "is_death_complete", False)
        )
        return (
            intro_npc_locked
            or spirit_npc_locked
            or sky_fall_npc_locked
            or self.game.objective_display.is_active
            or active_dialogue_npc
        )

    def handle_advance_input(self, event: pg.event.Event) -> bool:
        """Process input for cutscene dialogue advance (ENTER / SPACE / E / X / Gamepad).
        
        Returns True if the event was handled by a cutscene.
        """
        cutscene_advance_pressed = (
            (event.type == pg.KEYDOWN and event.key in (pg.K_RETURN, pg.K_SPACE, pg.K_e, pg.K_x)) or
            (event.type == pg.JOYBUTTONDOWN and event.button in (0, 1, 6))
        )
        if not cutscene_advance_pressed:
            return False

        for npc in self.game.npc_group:
            if getattr(npc, "is_spirit_of_scythe", False) and getattr(npc, "is_trance_active", False):
                if getattr(npc, "_trance_phase", 0) in (2, 3):
                    npc._trance_text_timer = 0.0
                    npc._trance_phase = 4  # Fades text and starts Zoom-Out
                    print("[SPIRIT NPC] Player pressed key → Fading text & starting Zoom-Out")
                    return True
            if getattr(npc, "is_sky_fall_npc", False) and getattr(npc, "is_trance_active", False):
                if getattr(npc, "_sky_fall_phase", 0) in (3, 4):
                    npc._sky_fall_timer = 0.0
                    npc._sky_fall_phase = 5  # Fades text and starts Zoom-Out
                    print("[SKY FALL NPC] Player pressed key → Fading text & starting Zoom-Out")
                    return True
            if getattr(npc, "is_intro_npc", False) and getattr(npc, "is_trance_active", False):
                if getattr(npc, "_trance_phase", 0) in (2, 3):
                    npc._trance_text_timer = 0.0
                    npc._trance_phase = 4  # Fades text and starts Zoom-Out
                    print("[INTRO NPC] Player pressed key → Fading text & starting Zoom-Out")
                    return True

        return False

    def update(self, dt: float) -> None:
        """Update cutscene phase machine and camera zoom focus."""
        active_speech_npc = None
        for npc in self.game.npc_group:
            if getattr(npc, "is_spirit_of_scythe", False) and getattr(npc, "is_trance_active", False):
                t_phase = getattr(npc, "_trance_phase", 0)
                if t_phase in (2, 3):
                    active_speech_npc = npc
                    if t_phase == 2 and self.game.clean_camera_zoom.current_zoom >= 1.35:
                        npc._trance_phase = 3
                        npc._trance_text_timer = npc._trance_text_duration
                        print("[SPIRIT NPC] Camera Zoom-In complete → Phase 3: Dialogue text displaying")
                    break
                elif t_phase == 4:
                    if self.game.clean_camera_zoom.current_zoom <= 1.005:
                        npc._trance_phase = 5
                        npc.trigger_death()
                        print("[SPIRIT NPC] Camera Zoom-Out complete → Phase 5: Eye Closing (Normal Death)")
                    break

            elif getattr(npc, "is_sky_fall_npc", False) and getattr(npc, "is_trance_active", False):
                s_phase = getattr(npc, "_sky_fall_phase", 0)
                if s_phase in (3, 4):
                    active_speech_npc = npc
                    if s_phase == 3 and self.game.clean_camera_zoom.current_zoom >= 1.35:
                        npc._sky_fall_phase = 4
                        npc._sky_fall_timer = npc._sky_fall_text_duration
                        print("[SKY FALL NPC] Camera Zoom-In complete → Phase 4: Dialogue text displaying")
                    break
                elif s_phase == 5:
                    if self.game.clean_camera_zoom.current_zoom <= 1.005:
                        if _GenericNPCState.JUMP_START in npc.animations:
                            npc._sky_fall_phase = 6
                            npc.set_state(_GenericNPCState.JUMP_START, force=True)
                            print("[SKY FALL NPC] Camera Zoom-Out complete → Phase 6: JUMP_START charge animation")
                        else:
                            npc._sky_fall_phase = 7
                            if _GenericNPCState.JUMP_LOOP in npc.animations:
                                npc.set_state(_GenericNPCState.JUMP_LOOP, force=True)
                    break

            elif getattr(npc, "is_intro_npc", False) and getattr(npc, "is_trance_active", False):
                t_phase = getattr(npc, "_trance_phase", 0)
                if t_phase in (2, 3):
                    active_speech_npc = npc
                    if t_phase == 2 and self.game.clean_camera_zoom.current_zoom >= 1.35:
                        npc._trance_phase = 3
                        npc._trance_text_timer = npc._trance_text_duration
                        print("[INTRO NPC] Camera Zoom-In complete → Phase 3: Dialogue text displaying")
                    break
                elif t_phase == 4:
                    if self.game.clean_camera_zoom.current_zoom <= 1.005:
                        npc._trance_phase = 5
                        npc.trigger_death()
                        print("[INTRO NPC] Camera Zoom-Out complete → Phase 5: Death animation starting")
                    break

        if active_speech_npc is not None:
            self.game.clean_camera_zoom.zoom_in(
                active_speech_npc.rect.centerx,
                active_speech_npc.rect.centery,
                target_zoom=1.38,
            )
        else:
            self.game.clean_camera_zoom.zoom_out()

        self.game.clean_camera_zoom.update(dt / 1000.0)

    def draw_dialogue_overlay(self, surface: pg.Surface) -> None:
        """Render cutscene dialogue text & glowing continue prompt in top-center screen area."""
        active_npc = None
        for npc in self.game.npc_group:
            if getattr(npc, "is_spirit_of_scythe", False) and getattr(npc, "is_trance_active", False):
                if getattr(npc, "_trance_phase", 0) == 3:
                    active_npc = npc
                    break
            elif getattr(npc, "is_sky_fall_npc", False) and getattr(npc, "is_trance_active", False):
                if getattr(npc, "_sky_fall_phase", 0) == 4:
                    active_npc = npc
                    break
            elif getattr(npc, "is_intro_npc", False) and getattr(npc, "is_trance_active", False):
                if getattr(npc, "_trance_phase", 0) == 3:
                    active_npc = npc
                    break

        if active_npc is None or not active_npc.text:
            return

        ticks = pg.time.get_ticks()

        # Calculate text fade alpha
        if getattr(active_npc, "is_sky_fall_npc", False):
            timer = getattr(active_npc, "_sky_fall_timer", 8.0)
            if timer > 7.5:
                text_alpha = int(255 * (8.0 - timer) / 0.5)
            elif timer < 0.6:
                text_alpha = int(255 * (timer / 0.6))
            else:
                text_alpha = 255
        else:
            timer = getattr(active_npc, "_trance_text_timer", 8.0)
            if timer > 7.5:
                text_alpha = int(255 * (8.0 - timer) / 0.5)
            elif timer < 0.6:
                text_alpha = int(255 * (timer / 0.6))
            else:
                text_alpha = 255

        text_alpha = max(0, min(255, text_alpha))
        if text_alpha <= 0:
            return

        font = getattr(active_npc, "_font", None)
        if font is None:
            return

        float_y = math.sin(ticks * 0.005) * 4.0

        # Word wrap text into lines (max 650px wide for top-center display)
        max_w = 650
        words = active_npc.text.split(" ")
        lines: list[str] = []
        curr = ""
        for word in words:
            test_l = f"{curr} {word}".strip() if curr else word
            if font.size(test_l)[0] <= max_w:
                curr = test_l
            else:
                if curr:
                    lines.append(curr)
                curr = word
        if curr:
            lines.append(curr)

        line_h = font.get_linesize() + 4
        total_text_h = len(lines) * line_h

        # Position text in the top-center screen area (y = 90px to 180px)
        start_y = 90 + int(float_y)
        center_x = self.game.width // 2

        # Draw subtle translucent dark background box behind text for maximum legibility
        bg_padding = 16
        max_line_w = max(font.size(l)[0] for l in lines) if lines else 400
        bg_rect = pg.Rect(
            center_x - max_line_w // 2 - bg_padding,
            start_y - bg_padding,
            max_line_w + bg_padding * 2,
            total_text_h + bg_padding * 2 + 30
        )
        bg_surf = pg.Surface((bg_rect.width, bg_rect.height), pg.SRCALPHA)
        bg_surf.fill((10, 5, 18, int(text_alpha * 0.65)))
        pg.draw.rect(bg_surf, (255, 180, 40, int(text_alpha * 0.45)), (0, 0, bg_rect.width, bg_rect.height), width=2, border_radius=8)
        surface.blit(bg_surf, bg_rect.topleft)

        # Render Gold Dialogue Text
        for i, line_str in enumerate(lines):
            tx = center_x - font.size(line_str)[0] // 2
            ty = start_y + i * line_h

            # Dark drop shadow
            shd_surf = font.render(line_str, True, (0, 0, 0))
            shd_surf.set_alpha(int(text_alpha * 0.90))
            surface.blit(shd_surf, (tx + 2, ty + 2))

            # Main Ethereal Gold text
            txt_surf = font.render(line_str, True, (255, 215, 80))
            txt_surf.set_alpha(text_alpha)
            surface.blit(txt_surf, (tx, ty))

        # Render Pulsing Continue Helper Prompt below dialogue box
        p_alpha = int(160 + 80 * abs(((ticks // 8) % 200 - 100) / 100))
        p_alpha = min(text_alpha, p_alpha)
        prompt_str = "[ PRESS ENTER OR SPACE TO CONTINUE ]"
        ptx = center_x - font.size(prompt_str)[0] // 2
        pty = start_y + len(lines) * line_h + 12

        p_shd = font.render(prompt_str, True, (0, 0, 0))
        p_shd.set_alpha(int(p_alpha * 0.85))
        surface.blit(p_shd, (ptx + 2, pty + 2))

        p_txt = font.render(prompt_str, True, (200, 240, 255))
        p_txt.set_alpha(p_alpha)
        surface.blit(p_txt, (ptx, pty))
