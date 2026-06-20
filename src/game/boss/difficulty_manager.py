"""Difficulty and intelligence scaling manager for the Fire Wizard boss.

Evaluates aggregated telemetry metrics, recommends AI difficulty presets,
and applies safe scaling relative to original baseline configurations.
"""

from typing import Any, Dict, List, Tuple

class DifficultyManager:
    # Original baseline parameters for Fire Wizard AI
    BASELINE_CONFIG = {
        "max_mana": 100.0,
        "spell_mana_cost": 35.0,
        "stagnant_duration": 3.0,
        "teleport_dist_min": 380,
        "teleport_dist_max": 450,
        "mana_recharge_rate": 50.0,
        "chase_delay_duration": 0.8,
        "attack_cooldown_min": 1.2,
        "attack_cooldown_max": 2.0
    }

    # Preset scaling rules
    PRESETS = {
        "EASY": {
            "max_mana": 80.0,
            "spell_mana_cost": 45.0,
            "stagnant_duration": 4.5,
            "teleport_dist_min": 450,
            "teleport_dist_max": 550,
            "mana_recharge_rate": 35.0,
            "chase_delay_duration": 1.5,
            "attack_cooldown_min": 2.0,
            "attack_cooldown_max": 3.5
        },
        "MEDIUM": {
            "max_mana": 100.0,
            "spell_mana_cost": 35.0,
            "stagnant_duration": 3.0,
            "teleport_dist_min": 380,
            "teleport_dist_max": 450,
            "mana_recharge_rate": 50.0,
            "chase_delay_duration": 0.8,
            "attack_cooldown_min": 1.2,
            "attack_cooldown_max": 2.0
        },
        "HARD": {
            "max_mana": 120.0,
            "spell_mana_cost": 28.0,
            "stagnant_duration": 2.0,
            "teleport_dist_min": 300,
            "teleport_dist_max": 400,
            "mana_recharge_rate": 70.0,
            "chase_delay_duration": 0.5,
            "attack_cooldown_min": 0.8,
            "attack_cooldown_max": 1.5
        },
        "NIGHTMARE": {
            "max_mana": 150.0,
            "spell_mana_cost": 20.0,
            "stagnant_duration": 1.0,
            "teleport_dist_min": 200,
            "teleport_dist_max": 300,
            "mana_recharge_rate": 90.0,
            "chase_delay_duration": 0.2,
            "attack_cooldown_min": 0.5,
            "attack_cooldown_max": 1.0
        }
    }

    # Slider bounds from wizard_editor.py
    SLIDER_BOUNDS = {
        "max_mana": (50.0, 200.0),
        "spell_mana_cost": (10.0, 100.0),
        "stagnant_duration": (0.5, 6.0),
        "teleport_dist_min": (100.0, 600.0),
        "teleport_dist_max": (400.0, 1000.0),
        "mana_recharge_rate": (10.0, 100.0),
        "chase_delay_duration": (0.0, 3.0),
        "attack_cooldown_min": (0.5, 4.0),
        "attack_cooldown_max": (1.0, 6.0)
    }

    def evaluate_sessions(self, sessions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyzes a list of session metrics and generates a difficulty recommendation."""
        # Filter valid sessions: at least 60 seconds of active combat time
        valid_sessions = [
            s for s in sessions 
            if s.get("active_combat_duration_sec", 0.0) >= 60.0 and s.get("total_frames", 0) > 0
        ]

        if not valid_sessions:
            return {
                "valid_session_count": 0,
                "recommended_difficulty": "None",
                "confidence": "none",
                "description": "Insufficient telemetry data for reliable recommendation.",
                "metrics": {},
                "warning": "Insufficient telemetry data for reliable recommendation."
            }

        # Average metrics across valid sessions
        num_sessions = len(valid_sessions)
        avg_metrics: Dict[str, float] = {
            "duration_sec": sum(s["duration_sec"] for s in valid_sessions) / num_sessions,
            "active_combat_duration_sec": sum(s.get("active_combat_duration_sec", 0.0) for s in valid_sessions) / num_sessions,
            "total_frames": sum(s["total_frames"] for s in valid_sessions) / num_sessions,
            "avg_fps": sum(s["avg_fps"] for s in valid_sessions) / num_sessions,
            "player_damage_taken": sum(s["player_damage_taken"] for s in valid_sessions) / num_sessions,
            "boss_damage_taken": sum(s["boss_damage_taken"] for s in valid_sessions) / num_sessions,
            "player_hits_received": sum(s["player_hits_received"] for s in valid_sessions) / num_sessions,
            "boss_hits_received": sum(s["boss_hits_received"] for s in valid_sessions) / num_sessions,
            "boss_attacks": sum(s["boss_attacks"] for s in valid_sessions) / num_sessions,
            "successful_boss_attacks": sum(s.get("successful_boss_attacks", 0.0) for s in valid_sessions) / num_sessions,
            "boss_spell_casts": sum(s.get("boss_spell_casts", 0) for s in valid_sessions) / num_sessions,
            "projectile_hits": sum(s.get("projectile_hits", 0) for s in valid_sessions) / num_sessions,
            "projectile_misses": sum(s.get("projectile_misses", 0) for s in valid_sessions) / num_sessions,
            "time_in_detection_range_frames": sum(s["time_in_detection_range_frames"] for s in valid_sessions) / num_sessions,
            "time_in_attack_range_frames": sum(s["time_in_attack_range_frames"] for s in valid_sessions) / num_sessions,
            "boss_detected_in_range_frames": sum(s["boss_detected_in_range_frames"] for s in valid_sessions) / num_sessions,
            "boss_attacked_in_range_attacks": sum(s["boss_attacked_in_range_attacks"] for s in valid_sessions) / num_sessions,
            "bad_attacks": sum(s["bad_attacks"] for s in valid_sessions) / num_sessions,
            "missed_opportunities": sum(s["missed_opportunities"] for s in valid_sessions) / num_sessions,
            "malformed_lines": sum(s.get("malformed_lines", 0) for s in valid_sessions) / num_sessions,
        }

        # Normalize metrics to per-minute values based on active combat time
        min_factor = max(0.1, avg_metrics["active_combat_duration_sec"]) / 60.0
        
        player_damage_per_min = avg_metrics["player_damage_taken"] / min_factor
        player_hits_per_min = avg_metrics["player_hits_received"] / min_factor
        successful_boss_attacks_per_min = avg_metrics["successful_boss_attacks"] / min_factor
        boss_damage_per_min = avg_metrics["boss_damage_taken"] / min_factor
        boss_hits_per_min = avg_metrics["boss_hits_received"] / min_factor

        # Formula: player_damage_taken_per_min + player_hits_received_per_min + successful_boss_attacks_per_min - boss_damage_taken_per_min - boss_hits_received_per_min
        pressure_score = (player_damage_per_min + player_hits_per_min + successful_boss_attacks_per_min) - (boss_damage_per_min + boss_hits_per_min)

        # Recommendation logic
        if pressure_score > 15.0:
            rec = "EASY"
            desc = f"Boss pressure is extremely high ({pressure_score:.1f} pts/min). Suggest lowering difficulty to Easy."
        elif -10.0 <= pressure_score <= 15.0:
            rec = "MEDIUM"
            desc = f"Boss pressure is balanced ({pressure_score:.1f} pts/min). Recommend keeping at Medium."
        elif -35.0 <= pressure_score < -10.0:
            rec = "HARD"
            desc = f"Player is defeating the boss easily ({pressure_score:.1f} pts/min). Suggest raising difficulty to Hard."
        else:
            rec = "NIGHTMARE"
            desc = f"Player is dominating the encounter ({pressure_score:.1f} pts/min). Recommend Nightmare difficulty."

        # Confidence level mapping:
        # none: no valid telemetry data (already handled)
        # low: only one valid session or weak combat data
        # medium: 2 valid sessions
        # high: 3 to 5 valid sessions with good combat data
        if num_sessions >= 3:
            confidence = "high"
        elif num_sessions == 2:
            confidence = "medium"
        else:
            confidence = "low"

        # Calculate accuracy metrics
        det_acc = (avg_metrics["boss_detected_in_range_frames"] / max(1, avg_metrics["time_in_detection_range_frames"])) * 100.0
        atk_acc = (avg_metrics["boss_attacked_in_range_attacks"] / max(1, avg_metrics["boss_attacks"])) * 100.0

        accuracies = {
            "detection_accuracy": min(100.0, det_acc),
            "attack_accuracy": min(100.0, atk_acc),
            "bad_attacks": avg_metrics["bad_attacks"],
            "missed_opportunities": avg_metrics["missed_opportunities"]
        }

        return {
            "valid_session_count": num_sessions,
            "recommended_difficulty": rec,
            "confidence": confidence,
            "description": desc,
            "pressure_score": pressure_score,
            "metrics": avg_metrics,
            "accuracies": accuracies,
            "warning": ""
        }

    def get_preset_config(self, preset_name: str) -> Dict[str, Any]:
        """Returns the cloned and clamped configuration for a given preset."""
        preset = self.PRESETS.get(preset_name.upper(), self.BASELINE_CONFIG)
        clamped = {}
        for key, val in preset.items():
            min_b, max_b = self.SLIDER_BOUNDS[key]
            clamped_val = max(min_b, min(max_b, val))
            
            # Specific AI safety rules
            if key == "spell_mana_cost":
                clamped_val = max(1.0, clamped_val)
            elif key == "stagnant_duration":
                clamped_val = max(0.5, clamped_val)
            elif key == "attack_cooldown_min":
                clamped_val = max(0.2, clamped_val)
                
            clamped[key] = clamped_val

        # Ensure min <= max ordering
        if clamped["teleport_dist_max"] < clamped["teleport_dist_min"]:
            clamped["teleport_dist_max"] = clamped["teleport_dist_min"]
        if clamped["attack_cooldown_max"] < clamped["attack_cooldown_min"]:
            clamped["attack_cooldown_max"] = clamped["attack_cooldown_min"]

        return clamped
