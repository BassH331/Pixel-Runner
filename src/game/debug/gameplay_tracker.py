"""Gameplay telemetry system for frame-by-frame logging and AI tuning.

Provides non-invasive gameplay data collection including:
- Player and boss state snapshots
- Combat events (damage, state changes, spawns)
- Collision verification via pixel signatures
- JSONL file rotation with session manifest
- Headless environment support (no display dependency)
"""

from __future__ import annotations

import json
import os
from typing import Any, Optional
from datetime import datetime
from pathlib import Path
from enum import Enum

import pygame as pg
from ..services import TelemetryClient


class EventType(Enum):
    """Enumeration of all trackable event types.
    
    Extensible design: Add new event types by extending this enum.
    Each event type maps to a string key in the JSONL log.
    """
    FRAME_SAMPLE = "frame_sample"
    DAMAGE_DEALT = "damage_dealt"
    DAMAGE_RECEIVED = "damage_received"
    PLAYER_STATE_CHANGED = "player_state_changed"
    BOSS_STATE_CHANGED = "boss_state_changed"
    ENTITY_SPAWN = "entity_spawn"
    ENTITY_DESPAWN = "entity_despawn"
    SPELL_CAST = "spell_cast"
    TELEPORT = "teleport"
    MANA_CHANGE = "mana_change"


class GameplayTracker:
    """Frame-by-frame gameplay telemetry logger with file rotation and verification.
    
    **Modularity & Design**:
    - Configurable via dict (can be loaded from JSON)
    - Non-invasive (disabled by default, opt-in)
    - Headless-compatible (no pygame display required)
    - Event-driven architecture with extensible event types via EventType enum
    - Automatic file rotation preventing disk bloat
    - Full error handling with graceful degradation
    
    **Features**:
    - **Performance Overhead**: Frame sampling will run every 1 frame (configurable) to avoid I/O blocking, while critical events (damage, spells, AI state changes) are logged immediately.
    - Automatic file rotation when exceeding max_file_size_mb
    - Pixel signature caching for visual-logical alignment verification
    - Session manifest tracking (latest_session.json)
    - Per-entity tracking with optional pixel signatures
    
    **Usage**:
        # Initialize with default config (disabled)
        tracker = GameplayTracker()
        
        # Enable tracking via config
        tracker = GameplayTracker({"enabled": True, "console_output": True})
        
        # Log events
        tracker.log_event("damage_dealt", {"target": "Skeleton", "damage": 10})
        tracker.log_event(EventType.PLAYER_STATE_CHANGED, {"old": "idle", "new": "attack"})
        
        # Sample frames periodically
        tracker.sample_frame(frame=100, fps=60, player_health=45)
        
        # Close on session end
        tracker.close()
    """
    
    DEFAULT_CONFIG = {
        "enabled": False,
        "sample_every_n_frames": 1,
        "log_dir": "logs/gameplay_tracking",
        "max_file_size_mb": 5,
        "pixel_signatures_enabled": True,
        "event_logging_enabled": True,
        "console_output": False,
    }
    _instance: Optional[GameplayTracker] = None
    
    @classmethod
    def get_instance(cls) -> Optional[GameplayTracker]:
        """Return the current active instance of the tracker."""
        return cls._instance

    def set_boss_key(self, boss_key: Optional[str]) -> None:
        """Record which boss type is associated with the current session, so
        it's included in telemetry for cloud-aggregated difficulty analysis."""
        self.current_boss_key = boss_key

    def __init__(self, config: Optional[dict[str, Any]] = None) -> None:
        """Initialize the gameplay tracker.
        
        Args:
            config: Configuration dict overriding defaults. Supported keys:
                - enabled: Enable/disable tracking (default: False)
                - sample_every_n_frames: Frame interval for periodic sampling (default: 1)
                - log_dir: Base directory for logs (default: "logs/gameplay_tracking")
                - max_file_size_mb: Max JSONL file size before rotation (default: 5)
                - pixel_signatures_enabled: Cache pixel data for verification (default: True)
                - event_logging_enabled: Log critical events immediately (default: True)
                - console_output: Print logs to console (default: False)
        """
        # Merge user config with defaults
        self.config = {**self.DEFAULT_CONFIG}
        if config:
            self.config.update(config)
        
        self.enabled = self.config["enabled"] or os.environ.get("TRACKER_ENABLED") == "1"
        self.sample_every_n_frames = self.config["sample_every_n_frames"]
        self.log_dir = Path(self.config["log_dir"])
        self.max_file_size_bytes = self.config["max_file_size_mb"] * 1024 * 1024
        self.pixel_signatures_enabled = self.config["pixel_signatures_enabled"]
        self.event_logging_enabled = self.config["event_logging_enabled"]
        self.console_output = self.config["console_output"]
        
        # Session state
        self.session_start_time = datetime.now()
        self.session_timestamp = self.session_start_time.strftime("%Y%m%d_%H%M%S")
        self.session_id = f"session_{self.session_timestamp}"
        self.current_file_index = 1
        self.current_file_path: Optional[Path] = None
        self.current_file_size = 0
        self.frame_count = 0
        self.event_count = 0
        
        # In-memory telemetry aggregator counters
        self.player_damage_taken = 0.0
        self.boss_damage_taken = 0.0
        self.player_hits_received = 0
        self.boss_hits_received = 0
        self.boss_attacks = 0
        self.successful_boss_attacks = 0
        self.boss_spell_casts = 0
        self.projectile_hits = 0
        self.projectile_misses = 0
        self.boss_defeated = False
        self.player_jumps = 0
        self.total_frames_sampled = 0
        self.fps_sum = 0.0
        self.horizontal_distances = []
        self.vertical_distances = []
        self.player_boss_distances = []
        self.player_defend_frames = 0
        self.player_standing_frames = 0
        self.player_side_swaps = 0
        self.active_combat_frames = 0
        self.current_boss_key: Optional[str] = None
        self._last_player_facing_left = None
        self._last_player_state = None
        
        # Pixel signature cache: entity_id -> {frame_data}
        self.pixel_signatures: dict[str, dict[str, Any]] = {}
        
        # Manifest file for session tracking
        self.manifest_path = self.log_dir / "latest_session.json"
        
        self.last_world_distance = 0.0
        self.damage_logged_this_frame = False
        GameplayTracker._instance = self
        
        if self.enabled:
            self._initialize_session()
            # Retry any pending telemetry from offline cache in the background
            TelemetryClient.retry_pending_telemetry()
    
    # ─────────────────────────────────────────────────────────────────────────
    # Session Management
    # ─────────────────────────────────────────────────────────────────────────
    
    def _initialize_session(self) -> None:
        """Create log directory and set up first log file."""
        try:
            self.log_dir.mkdir(parents=True, exist_ok=True)
            self._rotate_file()
            self._write_manifest()
            if self.console_output:
                print(f"[TRACKER] Session started: {self.session_timestamp}")
        except Exception as e:
            print(f"[TRACKER ERROR] Failed to initialize session: {e}")
            self.enabled = False
    
    def _rotate_file(self) -> None:
        """Create new log file, increment file index."""
        try:
            self.current_file_path = (
                self.log_dir / f"session_{self.session_timestamp}_{self.current_file_index:03d}.jsonl"
            )
            self.current_file_size = 0
            self.current_file_index += 1
            if self.console_output:
                print(f"[TRACKER] Rotated to: {self.current_file_path.name}")
        except Exception as e:
            print(f"[TRACKER ERROR] Failed to rotate file: {e}")
    
    def _write_manifest(self) -> None:
        """Update latest_session.json manifest with current session state."""
        if not self.enabled or not self.current_file_path:
            return
        
        try:
            manifest = {
                "session_timestamp": self.session_timestamp,
                "session_start": self.session_start_time.isoformat(),
                "latest_file": str(self.current_file_path),
                "total_log_files": self.current_file_index - 1,
                "frame_count": self.frame_count,
                "event_count": self.event_count,
                "config": self.config,
            }
            
            with open(self.manifest_path, "w") as f:
                json.dump(manifest, f, indent=2)
        except Exception as e:
            print(f"[TRACKER ERROR] Failed to write manifest: {e}")
    
    def _check_rotation(self) -> None:
        """Check if current file exceeds size limit and rotate if needed."""
        if not self.enabled or not self.current_file_path:
            return
        
        try:
            if self.current_file_path.exists():
                actual_size = self.current_file_path.stat().st_size
                if actual_size >= self.max_file_size_bytes:
                    self._rotate_file()
                    if self.console_output:
                        print(f"[TRACKER] File rotated due to size; now using file #{self.current_file_index - 1}")
        except Exception as e:
            print(f"[TRACKER ERROR] Failed to check rotation: {e}")
    
    # ─────────────────────────────────────────────────────────────────────────
    # Event Logging (Critical Events - Logged Immediately)
    # ─────────────────────────────────────────────────────────────────────────
    
    def log_event(
        self,
        event_type: str | EventType,
        data: dict[str, Any],
    ) -> None:
        """Log a critical event immediately (damage, spawn, state change, spell cast, etc.).
        
        This is the primary API for all gameplay events. Supports both string and
        EventType enum for flexibility and extensibility.
        
        Args:
            event_type: Event category (use EventType enum or string like "damage_dealt")
            data: Event-specific metadata. Should include relevant entity IDs, values, etc.
                  Example for damage: {"target": "Skeleton", "damage": 15, "health_after": 45}
        
        Examples:
            tracker.log_event("damage_dealt", {"target": "Skeleton", "damage": 10})
            tracker.log_event(EventType.PLAYER_STATE_CHANGED, {"old": "idle", "new": "attack"})
        """
        if not self.enabled or not self.event_logging_enabled:
            return
        
        self.event_count += 1
        
        # Convert EventType enum to string if needed
        event_type_str = (
            event_type.value if isinstance(event_type, EventType) else event_type
        )
        
        if event_type_str == "damage_received":
            self.damage_logged_this_frame = True
            self.player_damage_taken += float(data.get("damage", 0.0))
            self.player_hits_received += 1
        elif event_type_str == "damage_dealt":
            self.boss_damage_taken += float(data.get("damage", 0.0))
            self.boss_hits_received += 1
            if data.get("target_is_boss") and data.get("target_health_after", 1.0) <= 0.0:
                self.boss_defeated = True
        elif event_type_str == "boss_state_changed":
            if data.get("new") == "attack":
                self.boss_attacks += 1
            elif data.get("new") == "spell_cast" or data.get("new") == "cast":
                self.boss_spell_casts += 1
        elif event_type_str == "spell_cast":
            self.boss_spell_casts += 1
        elif event_type_str == "projectile_hit":
            self.projectile_hits += 1
        elif event_type_str == "projectile_miss":
            self.projectile_misses += 1
        elif event_type_str == "boss_defeated":
            self.boss_defeated = True
        elif event_type_str == "boss_attack_hit_player":
            self.successful_boss_attacks += 1
            
        entry = {
            "type": "event",
            "event_type": event_type_str,
            "timestamp_ms": pg.time.get_ticks(),
            **data,
        }
        
        # Submit to remote telemetry
        telemetry_item = {
            "session_id": self.session_id,
            "timestamp_ms": entry["timestamp_ms"],
            "event_type": event_type_str,
            "event_data": data
        }
        TelemetryClient.submit_events([telemetry_item])
        
        self._write_entry(entry)
    
    # ─────────────────────────────────────────────────────────────────────────
    # Frame Sampling (Periodic - Every N Frames)
    # ─────────────────────────────────────────────────────────────────────────
    
    def _serialize_entity(self, entity: Any) -> Optional[dict[str, Any]]:
        """Convert a complex game entity into a JSON-serializable dictionary."""
        if entity is None:
            return None
        
        try:
            entity_class = entity.__class__.__name__
            rect = getattr(entity, "rect", None)
            
            serialized = {
                "class": entity_class,
                "health": float(getattr(entity, "health", getattr(entity, "_health", 0.0))),
                "position": [rect.x, rect.y, rect.width, rect.height] if rect else None,
                "facing_left": bool(getattr(entity, "facing_left", False)),
                "state": getattr(getattr(entity, "state", None), "name", "").lower() or str(getattr(entity, "state", "")),
                "animation_index": float(getattr(entity, "animation_index", 0.0)),
            }
            
            # Player specific fields
            if entity_class == "Player":
                locks_movement = False
                locks_input = False
                state_configs = getattr(entity, "state_configs", None)
                curr_state = getattr(entity, "state", None)
                if state_configs and curr_state in state_configs:
                    cfg = state_configs[curr_state]
                    locks_movement = getattr(cfg, "locks_movement", False)
                    locks_input = getattr(cfg, "locks_input", False)

                inputs = {
                    "left": False, "right": False, "jump": False, "attack": False,
                    "roll": False, "dash": False, "special": False, "transform": False
                }
                if pg.display.get_init():
                    try:
                        keys = pg.key.get_pressed()
                        inputs["left"] = keys[pg.K_LEFT] or keys[pg.K_a]
                        inputs["right"] = keys[pg.K_RIGHT] or keys[pg.K_d]
                        inputs["jump"] = keys[pg.K_SPACE] or keys[pg.K_w] or keys[pg.K_UP]
                        inputs["attack"] = keys[pg.K_j]
                        inputs["roll"] = keys[pg.K_LSHIFT]
                        inputs["dash"] = keys[pg.K_LCTRL]
                        inputs["special"] = keys[pg.K_f]
                        inputs["transform"] = keys[pg.K_t]
                    except Exception:
                        pass

                vel = getattr(entity, "velocity", None)
                serialized.update({
                    "velocity": [vel.x, vel.y] if vel else [0.0, 0.0],
                    "is_invincible": bool(getattr(entity, "is_invincible", False)),
                    "is_attacking": "attack" in serialized["state"] or "special_attack" in serialized["state"],
                    "locks_movement": locks_movement,
                    "locks_input": locks_input,
                    "inputs": inputs,
                })
            
            # FireWizard/Skeleton/Enemy specific fields
            elif "Wizard" in entity_class or "Skeleton" in entity_class or entity_class == "Enemy":
                serialized.update({
                    "mana": float(getattr(entity, "mana", getattr(entity, "_mana", 0.0))),
                    "is_stagnant": bool(getattr(entity, "_is_stagnant", False)),
                    "is_recharging": bool(getattr(entity, "_is_recharging", False)),
                    "stagnant_timer": float(getattr(entity, "_stagnant_timer", 0.0)),
                    "teleport_cooldown": float(getattr(entity, "_teleport_cooldown", 0.0)),
                })
                
            return serialized
        except Exception as e:
            return {"error": f"Serialization failed: {e}", "class": entity.__class__.__name__}

    def sample_frame(self, **kwargs: Any) -> None:
        """Log a frame sample (called every N frames to avoid I/O overhead).
        
        Accepts flexible kwargs to capture any game state snapshot.
        Frame sampling is less frequent than event logging to minimize I/O impact.
        
        Args:
            **kwargs: Flexible key-value pairs representing frame state. Common examples:
                - frame: Current frame number
                - dt: Delta time
                - fps: Frames per second
                - player: Player entity state dict
                - boss: Boss entity state dict (if active)
                - world_distance: Distance traveled
                - active_entities: Count of live entities
        """
        if not self.enabled or not self.event_logging_enabled:
            return
        
        self.frame_count += 1
        
        processed_kwargs = {}
        for k, v in kwargs.items():
            if k in ("player", "boss") or hasattr(v, "rect"):
                processed_kwargs[k] = self._serialize_entity(v)
            else:
                processed_kwargs[k] = v
                
        # Aggregate frame statistics
        self.total_frames_sampled += 1
        fps_val = processed_kwargs.get("fps")
        fps_num = float(fps_val) if isinstance(fps_val, (int, float)) else 60.0
        self.fps_sum += fps_num
        
        player_data = processed_kwargs.get("player")
        boss_data = processed_kwargs.get("boss")
        
        is_player_attacking = False
        if player_data:
            state = player_data.get("state")
            if state:
                if self._last_player_state != state:
                    if state in ("jump_up", "jump_down") and self._last_player_state not in ("jump_up", "jump_down"):
                        self.player_jumps += 1
                    self._last_player_state = state
                
                if "defend" in state:
                    self.player_defend_frames += 1
                elif "idle" in state:
                    self.player_standing_frames += 1
            
            facing_left = player_data.get("facing_left")
            if facing_left is not None:
                if self._last_player_facing_left is not None and self._last_player_facing_left != facing_left:
                    self.player_side_swaps += 1
                self._last_player_facing_left = facing_left
                
            is_player_attacking = player_data.get("is_attacking", False)
            
        is_boss_attacking = False
        if boss_data:
            boss_state = boss_data.get("state", "")
            is_boss_attacking = "attack" in boss_state or "cast" in boss_state or "spell" in boss_state
            
        if is_player_attacking or is_boss_attacking:
            self.active_combat_frames += 1
            
        if player_data and boss_data:
            p_pos = player_data.get("position")
            b_pos = boss_data.get("position")
            if p_pos and b_pos:
                px, py = p_pos[0], p_pos[1]
                bx, by = b_pos[0], b_pos[1]
                h_dist = abs(px - bx)
                v_dist = abs(py - by)
                pb_dist = (h_dist**2 + v_dist**2)**0.5
                self.horizontal_distances.append(h_dist)
                self.vertical_distances.append(v_dist)
                self.player_boss_distances.append(pb_dist)
                
        entry = {
            "type": "frame_sample",
            "timestamp_ms": pg.time.get_ticks(),
            **processed_kwargs,
        }
        
        # Submit to remote telemetry
        frame_val = processed_kwargs.get("frame")
        frame_num = int(frame_val) if isinstance(frame_val, (int, float)) else self.frame_count
        
        dist_val = processed_kwargs.get("world_distance")
        dist_num = float(dist_val) if isinstance(dist_val, (int, float)) else self.last_world_distance
        
        entities_val = processed_kwargs.get("active_entities")
        entities_num = int(entities_val) if isinstance(entities_val, (int, float)) else 0
        
        frame_payload = {
            "session_id": self.session_id,
            "timestamp_ms": entry["timestamp_ms"],
            "frame_number": frame_num,
            "fps": fps_num,
            "world_distance": dist_num,
            "player": player_data,
            "boss": boss_data,
            "active_entities": entities_num
        }
        TelemetryClient.submit_frames([frame_payload])
        
        self._write_entry(entry)
    
    # ─────────────────────────────────────────────────────────────────────────
    # Pixel Signature Caching (Visual-Logical Verification)
    # ─────────────────────────────────────────────────────────────────────────
    
    def cache_pixel_signature(
        self,
        entity_id: str,
        entity_type: str,
        image: pg.Surface,
        bounding_box: tuple[int, int, int, int],
        sample_points: list[tuple[int, int]],
    ) -> None:
        """Cache pixel signature for an entity (used for visual-logical alignment verification).
        
        This allows offline verification that sprite rendering matches game logic.
        Particularly useful for bosses and complex animations.
        
        Args:
            entity_id: Unique entity identifier
            entity_type: Type of entity ("player", "boss", "skeleton", etc.)
            image: Current rendered surface
            bounding_box: (x, y, width, height) of entity bounds
            sample_points: List of (x, y) coordinates to sample RGBA values from
        """
        if not self.enabled or not self.pixel_signatures_enabled:
            return
        
        try:
            signature = {
                "entity_id": entity_id,
                "entity_type": entity_type,
                "bounding_box": bounding_box,
                "non_transparent_count": 0,
                "sample_points": [],
            }
            
            # Count non-transparent pixels if alpha channel exists
            if image.get_flags() & pg.SRCALPHA:
                try:
                    mask = pg.mask.from_surface(image)
                    signature["non_transparent_count"] = mask.count()
                except Exception:
                    pass
            
            # Sample RGBA at specific points for verification
            for sx, sy in sample_points[:5]:
                try:
                    color = image.get_at((sx, sy))
                    signature["sample_points"].append({
                        "x": sx,
                        "y": sy,
                        "rgba": list(color[:4]) if len(color) >= 4 else list(color),
                    })
                except IndexError:
                    pass  # Out of bounds — skip
            
            self.pixel_signatures[entity_id] = signature
            
            if self.console_output:
                print(f"[TRACKER] Cached pixel signature for {entity_type}#{entity_id}")
        except Exception as e:
            print(f"[TRACKER ERROR] Failed to cache pixel signature: {e}")
    
    def verify_visual_alignment(
        self,
        entity_id: str,
        current_image: pg.Surface,
        is_flipped: bool = False,
    ) -> dict[str, Any]:
        """Verify that visual appearance matches cached signature (accounting for flips).
        
        Useful for debugging animation/logic mismatches.
        
        Args:
            entity_id: Entity to verify
            current_image: Current rendered surface
            is_flipped: Whether entity is horizontally flipped
        
        Returns:
            Alignment verification result dict with 'verified' boolean and details
        """
        if not self.enabled or not self.pixel_signatures_enabled:
            return {"verified": False, "reason": "tracking disabled"}
        
        if entity_id not in self.pixel_signatures:
            return {"verified": False, "reason": "no cached signature"}
        
        try:
            cached = self.pixel_signatures[entity_id]
            result = {
                "entity_id": entity_id,
                "verified": True,
                "is_flipped": is_flipped,
                "checks": {},
            }
            
            # Check 1: Non-transparent pixel count (should be similar)
            if current_image.get_flags() & pg.SRCALPHA:
                try:
                    mask = pg.mask.from_surface(current_image)
                    current_count = mask.count()
                    cached_count = cached["non_transparent_count"]
                    
                    # Allow ±10% variance
                    variance = abs(current_count - cached_count) / max(cached_count, 1)
                    result["checks"]["pixel_variance"] = {
                        "cached": cached_count,
                        "current": current_count,
                        "variance_pct": variance * 100,
                        "passed": variance < 0.1,
                    }
                    
                    if not result["checks"]["pixel_variance"]["passed"]:
                        result["verified"] = False
                except Exception:
                    pass  # Graceful degradation
            
            # Check 2: Color samples (should match cached sample points)
            if "sample_points" in cached and cached["sample_points"]:
                result["checks"]["color_samples"] = {
                    "passed": True,
                    "details": []
                }
                curr_w, curr_h = current_image.get_size()
                for sample in cached["sample_points"]:
                    sx, sy = sample["x"], sample["y"]
                    # If flipped, map coordinate horizontally
                    if is_flipped:
                        sx = curr_w - 1 - sx
                    
                    try:
                        current_color = current_image.get_at((sx, sy))
                        current_rgba = list(current_color[:4]) if len(current_color) >= 4 else list(current_color)
                        cached_rgba = sample["rgba"]
                        
                        # Compare colors with absolute tolerance of 2 per channel
                        color_match = all(abs(c - r) <= 2 for c, r in zip(current_rgba, cached_rgba))
                        
                        result["checks"]["color_samples"]["details"].append({
                            "x": sx,
                            "y": sy,
                            "cached_rgba": cached_rgba,
                            "current_rgba": current_rgba,
                            "passed": color_match
                        })
                        
                        if not color_match:
                            result["checks"]["color_samples"]["passed"] = False
                            result["verified"] = False
                    except IndexError:
                        result["checks"]["color_samples"]["details"].append({
                            "x": sx,
                            "y": sy,
                            "passed": False,
                            "reason": "out of bounds"
                        })
                        result["checks"]["color_samples"]["passed"] = False
                        result["verified"] = False

            # Check 3: Bounding box size match
            if "bounding_box" in cached:
                cached_box = cached["bounding_box"]
                curr_w, curr_h = current_image.get_size()
                box_match = (curr_w == cached_box[2] and curr_h == cached_box[3])
                result["checks"]["bounding_box_size"] = {
                    "cached_size": [cached_box[2], cached_box[3]],
                    "current_size": [curr_w, curr_h],
                    "passed": box_match
                }
                if not box_match:
                    result["verified"] = False
            
            return result
        except Exception as e:
            print(f"[TRACKER ERROR] Verification failed: {e}")
            return {"verified": False, "reason": "verification error"}
    
    # ─────────────────────────────────────────────────────────────────────────
    # File I/O
    # ─────────────────────────────────────────────────────────────────────────
    
    def _write_entry(self, entry: dict[str, Any]) -> None:
        """Write a single entry to the current log file."""
        if not self.enabled or not self.current_file_path:
            return
        
        try:
            line = json.dumps(entry) + "\n"
            
            with open(self.current_file_path, "a") as f:
                f.write(line)
            
            self.current_file_size += len(line.encode("utf-8"))
            
            if self.console_output:
                event_type = entry.get("event_type", entry.get("type", "unknown"))
                print(f"[TRACKER] {event_type}")
            
            # Check if we need to rotate
            self._check_rotation()
        except Exception as e:
            print(f"[TRACKER ERROR] Failed to write entry: {e}")
    
    # ─────────────────────────────────────────────────────────────────────────
    # Session Lifecycle
    # ─────────────────────────────────────────────────────────────────────────
    
    def flush(self) -> None:
        """Flush and finalize logging (call on session exit)."""
        if self.enabled:
            self._write_manifest()
            
            # Submit final session metrics
            avg_fps = self.fps_sum / max(self.total_frames_sampled, 1)
            avg_h_dist = sum(self.horizontal_distances) / max(len(self.horizontal_distances), 1) if self.horizontal_distances else None
            avg_v_dist = sum(self.vertical_distances) / max(len(self.vertical_distances), 1) if self.vertical_distances else None
            avg_pb_dist = sum(self.player_boss_distances) / max(len(self.player_boss_distances), 1) if self.player_boss_distances else None
            
            session_payload = {
                "session_id": self.session_id,
                "boss_key": self.current_boss_key,
                "started_at": self.session_start_time.isoformat(),
                "ended_at": datetime.now().isoformat(),
                "duration_seconds": float((datetime.now() - self.session_start_time).total_seconds()),
                "total_frames": int(self.frame_count),
                "average_fps": float(avg_fps),
                "player_damage_taken": float(self.player_damage_taken),
                "boss_damage_taken": float(self.boss_damage_taken),
                "player_hits_received": int(self.player_hits_received),
                "boss_hits_received": int(self.boss_hits_received),
                "boss_attacks": int(self.boss_attacks),
                "successful_boss_attacks": int(self.successful_boss_attacks),
                "boss_spell_casts": int(self.boss_spell_casts),
                "projectile_hits": int(self.projectile_hits),
                "projectile_misses": int(self.projectile_misses),
                "boss_defeated": bool(self.boss_defeated),
                "average_horizontal_distance": avg_h_dist,
                "average_vertical_distance": avg_v_dist,
                "average_player_boss_distance": avg_pb_dist,
                "player_defend_frames": int(self.player_defend_frames),
                "player_standing_frames": int(self.player_standing_frames),
                "player_jumps": int(self.player_jumps),
                "player_side_swaps": int(self.player_side_swaps),
                "total_active_combat_frames": int(self.active_combat_frames)
            }
            TelemetryClient.submit_session(session_payload)
            
            if self.console_output:
                print(
                    f"[TRACKER] Session ended. "
                    f"Total frames: {self.frame_count}, events: {self.event_count}"
                )
    
    def close(self) -> None:
        """Close the tracker and write final manifest."""
        self.flush()
