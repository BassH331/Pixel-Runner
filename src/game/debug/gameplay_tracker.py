"""
Gameplay Tracker Module for Pixel-Runner.
Provides robust, non-invasive gameplay telemetry, JSONL frame sampling, event logging,
file size-based rotation, and sprite signature verification.
"""

from __future__ import annotations
import os
import sys
import json
import math
import time
import datetime
import pygame as pg
from typing import Any, Dict, List, Optional, Set, Tuple

# Default tracking configuration parameters
DEFAULT_CONFIG = {
    "enabled": False,
    "sample_every_n_frames": 10,
    "log_dir": "logs/gameplay_tracking",
    "max_file_size_mb": 5.0,
    "pixel_signatures_enabled": True,
    "event_logging_enabled": True,
    "console_output": False
}

class GameplayTracker:
    """Manages gameplay state logging and analysis frame-by-frame."""
    
    def __init__(self, overrides: Optional[Dict[str, Any]] = None) -> None:
        # Load configuration: start with defaults, apply overrides, then env variables and CLI flags
        self.config = dict(DEFAULT_CONFIG)
        if overrides:
            self.config.update(overrides)
            
        # Environment overrides
        for key in self.config.keys():
            env_key = f"GAMEPLAY_TRACKING_{key.upper()}"
            if env_key in os.environ:
                val = os.environ[env_key]
                if isinstance(self.config[key], bool):
                    self.config[key] = val.lower() in ("true", "1", "yes")
                elif isinstance(self.config[key], int):
                    self.config[key] = int(val)
                elif isinstance(self.config[key], float):
                    self.config[key] = float(val)
                else:
                    self.config[key] = val

        # Command-line check
        if "--track" in sys.argv:
            self.config["enabled"] = True
            
        # Parse command line sample frequency override (e.g. --track-samples 5)
        if "--track-samples" in sys.argv:
            try:
                idx = sys.argv.index("--track-samples")
                if idx + 1 < len(sys.argv):
                    self.config["sample_every_n_frames"] = int(sys.argv[idx + 1])
            except (ValueError, IndexError):
                pass

        self.enabled: bool = bool(self.config["enabled"])
        self.log_dir: str = str(self.config["log_dir"])
        self.max_file_size_bytes: int = int(float(self.config["max_file_size_mb"]) * 1024 * 1024)
        
        self.session_id: str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        self.file_index: int = 1
        self.total_files_written: int = 0
        
        # Sprite signature cache
        self._player_signatures: Dict[Tuple[Any, int], Dict[str, Any]] = {}
        self._boss_signatures: Dict[Tuple[Any, int], Dict[str, Any]] = {}
        self._signatures_cached: bool = False
        
        if self.enabled:
            os.makedirs(self.log_dir, exist_ok=True)
            self._write_manifest()

    def _get_current_log_path(self) -> str:
        return os.path.join(self.log_dir, f"session_{self.session_id}_{self.file_index:03d}.jsonl")

    def _write_manifest(self) -> None:
        manifest_path = os.path.join(self.log_dir, "latest_session.json")
        manifest_data = {
            "session_id": self.session_id,
            "latest_log_file": self._get_current_log_path(),
            "created_at": datetime.datetime.now().isoformat(),
            "total_files": self.file_index,
            "config": self.config
        }
        try:
            with open(manifest_path, "w") as f:
                json.dump(manifest_data, f, indent=4)
        except Exception as e:
            print(f"[TRACKER ERROR] Failed to write manifest: {e}", file=sys.stderr)

    def _rotate_file_if_needed(self, new_line_len: int) -> None:
        current_path = self._get_current_log_path()
        if os.path.exists(current_path):
            try:
                size = os.path.getsize(current_path)
                if size + new_line_len > self.max_file_size_bytes:
                    self.file_index += 1
                    self._write_manifest()
            except Exception:
                pass

    def _write_line(self, data: Dict[str, Any]) -> None:
        if not self.enabled:
            return
            
        line = json.dumps(data) + "\n"
        self._rotate_file_if_needed(len(line))
        
        current_path = self._get_current_log_path()
        try:
            with open(current_path, "a") as f:
                f.write(line)
            if self.config["console_output"]:
                print(f"[TRACKER] {data.get('event', 'frame_sample')} {line.strip()}")
        except Exception as e:
            print(f"[TRACKER ERROR] Failed to write log line: {e}", file=sys.stderr)

    def log_event(self, event_type: str, event_data: Dict[str, Any]) -> None:
        """Immediately record a gameplay event."""
        if not self.enabled or not self.config["event_logging_enabled"]:
            return
            
        log_entry = {
            "timestamp": datetime.datetime.now().isoformat(),
            "session_id": self.session_id,
            "event": event_type,
            "data": event_data
        }
        self._write_line(log_entry)

    def _compute_signature(self, surface: Optional[pg.Surface]) -> Dict[str, Any]:
        if surface is None:
            return {}
        try:
            w, h = surface.get_size()
            coords = [
                (w // 2, h // 2),        # Center
                (w // 4, h // 4),        # Top-Left
                (3 * w // 4, h // 4),    # Top-Right
                (w // 4, 3 * h // 4),    # Bottom-Left
                (3 * w // 4, 3 * h // 4) # Bottom-Right
            ]
            colors = []
            for cx, cy in coords:
                cx = max(0, min(w - 1, cx))
                cy = max(0, min(h - 1, cy))
                color = surface.get_at((cx, cy))
                colors.append([color.r, color.g, color.b, color.a])
            
            mask = pg.mask.from_surface(surface)
            non_transparent_count = mask.count()
            
            rects_any: Any = mask.get_bounding_rects()
            if rects_any:
                union_rect = rects_any[0].copy()
                for r in rects_any[1:]:
                    union_rect.union_ip(r)
                mask_bounds = [union_rect.x, union_rect.y, union_rect.width, union_rect.height]
            else:
                mask_bounds = [0, 0, 0, 0]
                
            return {
                "size": [w, h],
                "non_transparent_count": non_transparent_count,
                "colors": colors,
                "mask_bounds": mask_bounds
            }
        except Exception:
            return {}

    def _cache_signatures(self, player: Any, boss: Any) -> None:
        if player and hasattr(player, "animations") and player.animations:
            for state, frames in player.animations.items():
                for idx, frame in enumerate(frames):
                    self._player_signatures[(state, idx)] = self._compute_signature(frame)
        if boss and hasattr(boss, "animations") and boss.animations:
            for state, frames in boss.animations.items():
                for idx, frame in enumerate(frames):
                    self._boss_signatures[(state, idx)] = self._compute_signature(frame)
        self._signatures_cached = True

    def _verify_signature(self, entity: Any, is_boss: bool = False) -> bool:
        if not self.config["pixel_signatures_enabled"]:
            return True
            
        if not hasattr(entity, "animations") or not hasattr(entity, "state") or not hasattr(entity, "animation_index"):
            return False
            
        state = entity.state
        idx = int(entity.animation_index)
        
        cache = self._boss_signatures if is_boss else self._player_signatures
        cached = cache.get((state, idx))
        if not cached:
            return False
            
        image = getattr(entity, "image", None)
        if image is None:
            return False
            
        runtime = self._compute_signature(image)
        if not runtime:
            return False
            
        if runtime["size"] != cached["size"]:
            return False
        if runtime["non_transparent_count"] != cached["non_transparent_count"]:
            return False
            
        facing_left = getattr(entity, "facing_left", False)
        cached_colors = cached["colors"]
        runtime_colors = runtime["colors"]
        
        if facing_left:
            # Map cached colors as if flipped horizontally
            # Coord index mappings:
            # 0 -> 0 (Center)
            # 1 -> 2 (Top-Left swaps with Top-Right)
            # 2 -> 1
            # 3 -> 4 (Bottom-Left swaps with Bottom-Right)
            # 4 -> 3
            if len(cached_colors) >= 5:
                expected_colors = [
                    cached_colors[0],
                    cached_colors[2],
                    cached_colors[1],
                    cached_colors[4],
                    cached_colors[3]
                ]
            else:
                expected_colors = cached_colors
        else:
            expected_colors = cached_colors
            
        for c1, c2 in zip(runtime_colors, expected_colors):
            if c1 != c2:
                return False
                
        return True

    def _check_position_mismatch(self, entity: Any) -> bool:
        if not hasattr(entity, "image") or not hasattr(entity, "rect") or not hasattr(entity, "image_offset"):
            return False
            
        image = entity.image
        if image is None:
            return False
            
        try:
            mask = pg.mask.from_surface(image)
            rects_any: Any = mask.get_bounding_rects()
            if not rects_any:
                return False
                
            union_rect = rects_any[0].copy()
            for r in rects_any[1:]:
                union_rect.union_ip(r)
                
            draw_x = entity.rect.x - entity.image_offset.x
            draw_y = entity.rect.y - entity.image_offset.y
            
            visual_rect = pg.Rect(
                draw_x + union_rect.x,
                draw_y + union_rect.y,
                union_rect.width,
                union_rect.height
            )
            
            # Check overlap and distance threshold
            if not entity.rect.colliderect(visual_rect):
                dist = pg.math.Vector2(entity.rect.center).distance_to(visual_rect.center)
                if dist > 300:
                    return True
            return False
        except Exception:
            return False

    def _resolve_frame_path(self, entity: Any, is_boss: bool = False) -> str:
        if not hasattr(entity, "state") or not hasattr(entity, "animation_index"):
            return ""
        state = entity.state
        idx = int(entity.animation_index)
        
        if not is_boss:
            # Player mapping
            state_name = getattr(state, "name", "")
            mapping = {
                "IDLE": "assets/shadow_warrior/idle/idle_{}.png",
                "RUN": "assets/shadow_warrior/run/run_{}.png",
                "JUMP_UP": "assets/shadow_warrior/jump_up_loop/jump_up_loop_{}.png",
                "JUMP_DOWN": "assets/shadow_warrior/jump_down_loop/jump_down_loop_{}.png",
                "ATTACK_THRUST": "assets/shadow_warrior/1_atk/1_atk_{}.png",
                "ATTACK_SMASH": "assets/shadow_warrior/2_atk/2_atk_{}.png",
                "ATTACK_POWER": "assets/shadow_warrior/3_atk/3_atk_{}.png",
                "HURT": "assets/shadow_warrior/take_hit/take_hit_{}.png",
                "DEATH": "assets/shadow_warrior/death/death_{}.png",
                "DEFEND": "assets/shadow_warrior/defend/defend_{}.png"
            }
            pattern = mapping.get(state_name)
            if pattern:
                return pattern.format(idx + 1)
        else:
            # Boss mapping
            state_name = getattr(state, "name", "")
            mapping = {
                "IDLE": "assets/wizard/Idle/wizard_idle{}.png",
                "CHASE": "assets/wizard/Move/wizard_run{}.png",
                "ATTACK": "assets/wizard/Attack/wizard_atk1{}.png",
                "HURT": "assets/wizard/Take Hit/wizard_hit{}.png",
                "DEATH": "assets/wizard/Death/wizard_death{}.png"
            }
            pattern = mapping.get(state_name)
            if pattern:
                return pattern.format(idx)
        return ""

    def sample_frame(
        self,
        frame: int,
        dt: float,
        fps: float,
        game_state_name: str,
        player: Any,
        boss: Optional[Any],
        world_distance: float
    ) -> None:
        """Sample and log all relevant telemetry for the current frame."""
        if not self.enabled:
            return
            
        # Lazy signature cache initialization
        if not self._signatures_cached:
            self._cache_signatures(player, boss)
            
        # 1. Player Telemetry
        player_state_name = getattr(player.state, "name", "unknown") if hasattr(player, "state") else "unknown"
        player_animation = self._resolve_frame_path(player, is_boss=False)
        player_vel = [float(player.velocity.x), float(player.velocity.y)] if hasattr(player, "velocity") else [0.0, 0.0]
        
        player_hitbox_data = None
        if hasattr(player, "get_attack_hitbox"):
            hb = player.get_attack_hitbox()
            if hb:
                player_hitbox_data = [hb.x, hb.y, hb.width, hb.height]

        player_data = {
            "name": "Shadow Warrior",
            "world_pos": [float(player.rect.x + world_distance), float(player.rect.y)],
            "screen_pos": [player.rect.x, player.rect.y],
            "rect": [player.rect.x, player.rect.y, player.rect.width, player.rect.height],
            "center": [player.rect.centerx, player.rect.centery],
            "velocity": player_vel,
            "animation": player_animation,
            "state": player_state_name,
            "health": getattr(player, "health", 0.0),
            "is_attacking": getattr(player, "is_attacking", False),
            "asset_folder": "assets/shadow_warrior",
            "hitbox": player_hitbox_data
        }
        
        # 2. Boss Telemetry (if active)
        boss_data = None
        relative_data = None
        
        # Sprite verification
        player_sig_match = self._verify_signature(player, is_boss=False)
        boss_sig_match = True
        player_mask_overlap_wizard = False
        pos_mismatch = self._check_position_mismatch(player)
        
        if boss is not None:
            boss_state_name = getattr(boss.state, "name", "unknown") if hasattr(boss, "state") else "unknown"
            boss_animation = self._resolve_frame_path(boss, is_boss=True)
            boss_vel = [float(boss.velocity.x), float(boss.velocity.y)] if hasattr(boss, "velocity") else [0.0, 0.0]
            
            # Determine boss AI state representation
            is_stagnant = getattr(boss, "_is_stagnant", False)
            is_recharging = getattr(boss, "_is_recharging", False)
            chase_delay = getattr(boss, "_chase_delay_active", False)
            
            if is_stagnant:
                boss_ai_state = "stagnant"
            elif is_recharging:
                boss_ai_state = "recharging"
            elif chase_delay:
                boss_ai_state = "chase_delay"
            else:
                boss_ai_state = boss_state_name.lower()
                
            boss_is_attacking = (boss_state_name == "ATTACK")
            
            boss_data = {
                "name": getattr(boss, "boss_title", "Fire Wizard"),
                "world_pos": [float(boss.rect.x + world_distance), float(boss.rect.y)],
                "screen_pos": [boss.rect.x, boss.rect.y],
                "rect": [boss.rect.x, boss.rect.y, boss.rect.width, boss.rect.height],
                "center": [boss.rect.centerx, boss.rect.centery],
                "velocity": boss_vel,
                "ai_state": boss_ai_state,
                "animation": boss_animation,
                "is_attacking": boss_is_attacking,
                "detection_range": 500.0,
                "attack_range": 260.0
            }
            
            # 3. Relative calculations
            dist_x = abs(boss.rect.centerx - player.rect.centerx)
            dist_y = boss.rect.centery - player.rect.centery
            euclidean = math.sqrt(dist_x**2 + dist_y**2)
            
            vertical_tolerance = getattr(boss, "_vertical_tolerance", 100.0)
            aligned_y = abs(dist_y) <= vertical_tolerance
            in_attack_range = (120.0 <= dist_x <= 260.0) and aligned_y
            in_detection = euclidean <= 500.0
            
            relative_data = {
                "distance_x": dist_x,
                "distance_y": dist_y,
                "euclidean_distance": round(euclidean, 2),
                "player_in_detection_range": in_detection,
                "player_in_attack_range": in_attack_range,
                "aligned_y": aligned_y
            }
            
            boss_sig_match = self._verify_signature(boss, is_boss=True)
            if self._check_position_mismatch(boss):
                pos_mismatch = True
                
            # Check mask overlap
            try:
                p_mask = pg.mask.from_surface(player.image)
                b_mask = pg.mask.from_surface(boss.image)
                offset = (boss.rect.x - player.rect.x, boss.rect.y - player.rect.y)
                player_mask_overlap_wizard = p_mask.overlap(b_mask, offset) is not None
            except Exception:
                pass

        sprite_detection = {
            "player_asset": "shadow_warrior",
            "player_signature_match": player_sig_match,
            "wizard_signature_match": boss_sig_match,
            "player_mask_overlap_wizard": player_mask_overlap_wizard,
            "logical_visual_position_mismatch": pos_mismatch
        }

        # Assemble sample entry
        sample_entry = {
            "timestamp": datetime.datetime.now().isoformat(),
            "session_id": self.session_id,
            "frame": frame,
            "dt": dt,
            "fps": round(fps, 1),
            "state": game_state_name,
            "camera_offset": [world_distance, 0.0],
            "player": player_data,
            "boss": boss_data,
            "relative": relative_data,
            "sprite_detection": sprite_detection
        }
        
        self._write_line(sample_entry)
        
        # Log mismatch alert if anything is suspicious
        if pos_mismatch and self.config["event_logging_enabled"]:
            self.log_event("suspicious_mismatch", {
                "frame": frame,
                "player_mismatch": self._check_position_mismatch(player),
                "boss_mismatch": self._check_position_mismatch(boss) if boss else False
            })
        if (not player_sig_match or not boss_sig_match) and self.config["event_logging_enabled"]:
            self.log_event("suspicious_asset_mismatch", {
                "frame": frame,
                "player_sig_match": player_sig_match,
                "boss_sig_match": boss_sig_match
            })
