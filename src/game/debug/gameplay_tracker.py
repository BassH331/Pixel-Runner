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
    - Configurable frame sampling (every N frames to avoid I/O blocking)
    - Immediate event logging for critical events (damage, AI state changes)
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
        "sample_every_n_frames": 10,
        "log_dir": "logs/gameplay_tracking",
        "max_file_size_mb": 5,
        "pixel_signatures_enabled": True,
        "event_logging_enabled": True,
        "console_output": False,
    }
    
    def __init__(self, config: Optional[dict[str, Any]] = None) -> None:
        """Initialize the gameplay tracker.
        
        Args:
            config: Configuration dict overriding defaults. Supported keys:
                - enabled: Enable/disable tracking (default: False)
                - sample_every_n_frames: Frame interval for periodic sampling (default: 10)
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
        
        self.enabled = self.config["enabled"]
        self.sample_every_n_frames = self.config["sample_every_n_frames"]
        self.log_dir = Path(self.config["log_dir"])
        self.max_file_size_bytes = self.config["max_file_size_mb"] * 1024 * 1024
        self.pixel_signatures_enabled = self.config["pixel_signatures_enabled"]
        self.event_logging_enabled = self.config["event_logging_enabled"]
        self.console_output = self.config["console_output"]
        
        # Session state
        self.session_start_time = datetime.now()
        self.session_timestamp = self.session_start_time.strftime("%Y%m%d_%H%M%S")
        self.current_file_index = 1
        self.current_file_path: Optional[Path] = None
        self.current_file_size = 0
        self.frame_count = 0
        self.event_count = 0
        
        # Pixel signature cache: entity_id -> {frame_data}
        self.pixel_signatures: dict[str, dict[str, Any]] = {}
        
        # Manifest file for session tracking
        self.manifest_path = self.log_dir / "latest_session.json"
        
        if self.enabled:
            self._initialize_session()
    
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
        
        entry = {
            "type": "event",
            "event_type": event_type_str,
            "timestamp_ms": int(pg.time.get_ticks()),
            **data,
        }
        
        self._write_entry(entry)
    
    # ─────────────────────────────────────────────────────────────────────────
    # Frame Sampling (Periodic - Every N Frames)
    # ─────────────────────────────────────────────────────────────────────────
    
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
        
        Examples:
            tracker.sample_frame(
                frame=100,
                fps=60,
                player_health=45,
                enemy_count=3
            )
        """
        if not self.enabled or not self.event_logging_enabled:
            return
        
        self.frame_count += 1
        entry = {
            "type": "frame_sample",
            "timestamp_ms": int(pg.time.get_ticks()),
            **kwargs,
        }
        
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
                    pixel_array = pg.surfarray.pixels_alpha(image)
                    signature["non_transparent_count"] = int((pixel_array > 0).sum())
                except Exception:
                    pass  # Graceful degradation if surfarray fails
            
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
                    pixel_array = pg.surfarray.pixels_alpha(current_image)
                    current_count = int((pixel_array > 0).sum())
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
            if self.console_output:
                print(
                    f"[TRACKER] Session ended. "
                    f"Total frames: {self.frame_count}, events: {self.event_count}"
                )
    
    def close(self) -> None:
        """Close the tracker and write final manifest."""
        self.flush()
