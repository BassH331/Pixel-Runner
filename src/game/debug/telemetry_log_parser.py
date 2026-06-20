"""Telemetry log parser for gameplay session records.

Scans, groups, and parses rotated session .jsonl files to extract detailed performance
and AI range metrics (e.g. hits, damage, range accuracies).
"""

import json
import os
import re
import math
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

class TelemetryLogParser:
    def __init__(self, log_dir: str = "logs/gameplay_tracking") -> None:
        self.log_dir = Path(log_dir)

    def _group_rotated_files(self) -> Dict[str, List[Path]]:
        """Groups rotated .jsonl files by session ID prefix.
        
        Example: session_20260620_020000_001.jsonl and session_20260620_020000_002.jsonl
        both belong to session ID 'session_20260620_020000'.
        """
        if not self.log_dir.exists():
            return {}

        session_groups: Dict[str, List[Path]] = {}
        pattern = re.compile(r"^(session_\d{8}_\d{6})_(\d{3})\.jsonl$")

        try:
            for file_path in self.log_dir.iterdir():
                if file_path.is_file():
                    match = pattern.match(file_path.name)
                    if match:
                        session_id = match.group(1)
                        if session_id not in session_groups:
                            session_groups[session_id] = []
                        session_groups[session_id].append(file_path)
        except Exception:
            pass

        # Sort chunk files within each session group to ensure chronological order
        for session_id in session_groups:
            session_groups[session_id].sort()

        return session_groups

    def get_latest_session(self) -> Optional[Tuple[str, List[Path]]]:
        """Finds and returns the latest session ID and its chunk file paths."""
        groups = self._group_rotated_files()
        if not groups:
            return None
        latest_session_id = sorted(groups.keys())[-1]
        return latest_session_id, groups[latest_session_id]

    def get_recent_sessions(self, limit: int = 5) -> List[Tuple[str, List[Path]]]:
        """Returns the latest N session IDs and their chunk file paths, sorted newest first."""
        groups = self._group_rotated_files()
        if not groups:
            return []
        sorted_ids = sorted(groups.keys(), reverse=True)
        return [(sid, groups[sid]) for sid in sorted_ids[:limit]]

    def parse_session(self, file_paths: List[Path]) -> Dict[str, Any]:
        """Parses all chunk files for a single session and aggregates telemetry metrics."""
        metrics: Dict[str, Any] = {
            "session_id": "None",
            "files_parsed": [],
            "total_valid_events": 0,
            "malformed_lines": 0,
            "start_timestamp": None,
            "end_timestamp": None,
            "duration_sec": 0.0,
            "active_combat_duration_sec": 0.0,
            "total_frames": 0,
            "avg_fps": 0.0,
            "player_damage_taken": 0.0,
            "boss_damage_taken": 0.0,
            "player_hits_received": 0,
            "boss_hits_received": 0,
            "boss_attacks": 0,
            "successful_boss_attacks": 0,
            "boss_spell_casts": 0,
            "projectile_hits": 0,
            "projectile_misses": 0,
            "time_in_detection_range_frames": 0,
            "time_in_attack_range_frames": 0,
            "boss_detected_in_range_frames": 0,
            "boss_attacked_in_range_attacks": 0,
            "bad_attacks": 0,
            "missed_opportunities": 0,
            "player_boss_distances": [],
            "player_boss_y_alignments": [],
            "player_boss_total_distances": [],
            "state_changes": 0,
            "detection_failures": 0,
            "average_horizontal_distance": 0.0,
            "average_vertical_distance": 0.0,
            "average_player_boss_distance": 0.0,
            "boss_defeated": False,
            "player_defend_frames": 0,
            "player_standing_frames": 0,
            "player_jumps": 0,
            "player_side_swaps": 0,
            "total_active_combat_frames": 0,
        }

        if file_paths:
            # Group session ID from first filename
            pattern = re.compile(r"^(session_\d{8}_\d{6})_(\d{3})\.jsonl$")
            match = pattern.match(file_paths[0].name)
            if match:
                metrics["session_id"] = match.group(1)

        fps_samples: List[float] = []
        first_timestamp: Optional[int] = None
        last_timestamp: Optional[int] = None
        active_timestamps: List[int] = []

        prev_diff_x = None
        prev_p_state = None

        for path in file_paths:
            if not path.exists():
                continue
            metrics["files_parsed"].append(path.name)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            data = json.loads(line)
                            metrics["total_valid_events"] += 1
                        except json.JSONDecodeError:
                            metrics["malformed_lines"] += 1
                            continue

                        ts = data.get("timestamp_ms")
                        if isinstance(ts, (int, float)):
                            ts_int = int(ts)
                            if first_timestamp is None:
                                first_timestamp = ts_int
                            last_timestamp = ts_int

                        entry_type = data.get("type")
                        if entry_type == "frame_sample":
                            metrics["total_frames"] += 1
                            fps = data.get("fps", 0.0)
                            if fps > 0.0:
                                fps_samples.append(float(fps))

                            player = data.get("player")
                            boss = data.get("boss")

                            if player and boss:
                                # Count this frame as active combat/tracking data
                                metrics["total_active_combat_frames"] += 1
                                if isinstance(ts, (int, float)):
                                    active_timestamps.append(int(ts))

                                b_health = boss.get("health", 100.0)
                                b_state = boss.get("state", "").lower()
                                if b_health <= 0.0 or b_state == "death":
                                    metrics["boss_defeated"] = True

                                p_state = player.get("state", "").lower()
                                if "defend" in p_state:
                                    metrics["player_defend_frames"] += 1

                                p_vel = player.get("velocity", [0.0, 0.0])
                                if (p_vel == [0.0, 0.0] or p_vel is None) and p_state in ("idle", "defend"):
                                    metrics["player_standing_frames"] += 1

                                if prev_p_state is not None:
                                    is_curr_jump = "jump" in p_state
                                    is_prev_jump = "jump" in prev_p_state
                                    if is_curr_jump and not is_prev_jump:
                                        metrics["player_jumps"] += 1
                                prev_p_state = p_state

                                p_pos = player.get("position")
                                b_pos = boss.get("position")

                                if isinstance(p_pos, list) and isinstance(b_pos, list) and len(p_pos) >= 2 and len(b_pos) >= 2:
                                    p_cx = p_pos[0] + p_pos[2] / 2 if len(p_pos) >= 4 else p_pos[0]
                                    p_cy = p_pos[1] + p_pos[3] / 2 if len(p_pos) >= 4 else p_pos[1]
                                    b_cx = b_pos[0] + b_pos[2] / 2 if len(b_pos) >= 4 else b_pos[0]
                                    b_cy = b_pos[1] + b_pos[3] / 2 if len(b_pos) >= 4 else b_pos[1]

                                    diff_x = p_cx - b_cx
                                    if prev_diff_x is not None:
                                        if diff_x * prev_diff_x < 0:
                                            metrics["player_side_swaps"] += 1
                                    prev_diff_x = diff_x

                                    dist_x = abs(b_cx - p_cx)
                                    dist_y = abs(b_cy - p_cy)
                                    dist_total = math.sqrt(dist_x**2 + dist_y**2)
                                    
                                    metrics["player_boss_distances"].append(dist_x)
                                    metrics["player_boss_y_alignments"].append(dist_y)
                                    metrics["player_boss_total_distances"].append(dist_total)

                                    # Range checks
                                    in_detection = (dist_x <= 500) and (dist_y < 150)
                                    in_attack = (120 <= dist_x <= 260) and (dist_y < 150)

                                    if in_detection:
                                        metrics["time_in_detection_range_frames"] += 1
                                        b_state = boss.get("state", "").lower()
                                        is_stagnant = boss.get("is_stagnant", False)
                                        is_recharging = boss.get("is_recharging", False)
                                        if b_state not in ("idle", "") and not is_stagnant and not is_recharging:
                                            metrics["boss_detected_in_range_frames"] += 1

                                    if in_attack:
                                        metrics["time_in_attack_range_frames"] += 1
                                        
                                        b_state = boss.get("state", "").lower()
                                        mana = boss.get("mana", 0.0)
                                        cd = boss.get("teleport_cooldown", 0.0)
                                        if mana >= 35.0 and cd <= 0.0 and b_state in ("idle", "chase"):
                                            metrics["missed_opportunities"] += 1

                        elif entry_type == "event":
                            ev_type = data.get("event_type")
                            if ev_type == "damage_received":
                                metrics["player_hits_received"] += 1
                                metrics["player_damage_taken"] += float(data.get("damage", 0.0))
                                metrics["successful_boss_attacks"] += 1
                            elif ev_type == "damage_dealt":
                                metrics["boss_hits_received"] += 1
                                metrics["boss_damage_taken"] += float(data.get("damage", 0.0))
                                if data.get("target_is_boss") and float(data.get("target_health_after", 100.0)) <= 0.0:
                                    metrics["boss_defeated"] = True
                            elif ev_type == "boss_state_changed":
                                metrics["state_changes"] += 1
                                new_s = data.get("new_state", "").lower()
                                if new_s in ("death", "none"):
                                    metrics["boss_defeated"] = True
                                elif new_s == "attack":
                                    metrics["boss_attacks"] += 1
                                    
                                    if metrics["player_boss_distances"]:
                                        last_dist_x = metrics["player_boss_distances"][-1]
                                        last_dist_y = metrics["player_boss_y_alignments"][-1]
                                        in_attack_range = (120 <= last_dist_x <= 260) and (last_dist_y < 150)
                                        if in_attack_range:
                                            metrics["boss_attacked_in_range_attacks"] += 1
                                        else:
                                            metrics["bad_attacks"] += 1
                            elif ev_type == "spell_cast":
                                metrics["boss_spell_casts"] += 1
                                # Track projectile misses or hits if spell_cast was triggered
                            elif ev_type == "projectile_hit":
                                metrics["projectile_hits"] += 1
                            elif ev_type == "projectile_miss":
                                metrics["projectile_misses"] += 1

            except Exception:
                continue

        # Timestamps
        metrics["start_timestamp"] = first_timestamp
        metrics["end_timestamp"] = last_timestamp
        if first_timestamp is not None and last_timestamp is not None:
            metrics["duration_sec"] = max(0.1, (last_timestamp - first_timestamp) / 1000.0)

        # Active combat duration calculation:
        # Difference between first active frame and last active frame
        if active_timestamps:
            metrics["active_combat_duration_sec"] = max(0.1, (max(active_timestamps) - min(active_timestamps)) / 1000.0)
        else:
            metrics["active_combat_duration_sec"] = 0.0

        if fps_samples:
            metrics["avg_fps"] = sum(fps_samples) / len(fps_samples)

        # Averages
        if metrics["player_boss_distances"]:
            metrics["average_horizontal_distance"] = sum(metrics["player_boss_distances"]) / len(metrics["player_boss_distances"])
        if metrics["player_boss_y_alignments"]:
            metrics["average_vertical_distance"] = sum(metrics["player_boss_y_alignments"]) / len(metrics["player_boss_y_alignments"])
        if metrics["player_boss_total_distances"]:
            metrics["average_player_boss_distance"] = sum(metrics["player_boss_total_distances"]) / len(metrics["player_boss_total_distances"])

        # Clean lists to avoid JSON serialization/bloat on return
        metrics.pop("player_boss_distances", None)
        metrics.pop("player_boss_y_alignments", None)
        metrics.pop("player_boss_total_distances", None)

        return metrics
