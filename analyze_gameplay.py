#!/usr/bin/env python3
"""
analyze_gameplay.py
Command-line telemetry analysis engine that parses gameplay JSONL files,
evaluates game feel responsiveness, dodge effectiveness, animation choppiness,
and outputs a premium markdown report with configuration tuning recommendations.
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List, Optional

def analyze_session(log_path: Path) -> Optional[Dict[str, Any]]:
    print(f"[INFO] Analyzing telemetry log: {log_path}")
    
    frames: List[Dict[str, Any]] = []
    events: List[Dict[str, Any]] = []
    
    try:
        with open(log_path, "r") as f:
            for line in f:
                if not line.strip():
                    continue
                data = json.loads(line)
                if data.get("type") == "frame_sample":
                    frames.append(data)
                elif data.get("type") == "event":
                    events.append(data)
    except Exception as e:
        print(f"[ERROR] Failed to read log file: {e}")
        return None
        
    if not frames:
        print("[WARNING] No frame samples found in log file.")
        return None

    # 1. Basic Stats
    total_frames = len(frames)
    first_ts = frames[0]["timestamp_ms"]
    last_ts = frames[-1]["timestamp_ms"]
    duration_sec = (last_ts - first_ts) / 1000.0 if last_ts > first_ts else 0.0
    
    fps_values = [f["fps"] for f in frames if "fps" in f]
    avg_fps = sum(fps_values) / len(fps_values) if fps_values else 60.0

    # 2. Player State Duration & Distribution
    state_counts: Dict[str, int] = {}
    total_samples = 0
    
    for f in frames:
        p = f.get("player")
        if p and "state" in p:
            st = p["state"].upper()
            state_counts[st] = state_counts.get(st, 0) + 1
            total_samples += 1

    state_pcts = {st: (count / total_samples) * 100 for st, count in state_counts.items()} if total_samples > 0 else {}

    # 3. Input Responsiveness / Input-to-State Latency
    # We analyze transitions: when input is pressed, how many frames does it take for state to change?
    latency_records: List[float] = []
    
    # We track last frame's inputs
    last_inputs: Dict[str, bool] = {}
    pending_inputs: Dict[str, int] = {} # input_name -> timestamp of press

    for f in frames:
        p = f.get("player")
        if not p or "inputs" not in p or "state" not in p:
            continue
        
        curr_inputs = p["inputs"]
        curr_state = p["state"].upper()
        ts = f["timestamp_ms"]
        
        # Check for new press events
        for action, pressed in curr_inputs.items():
            prev_pressed = last_inputs.get(action, False)
            if pressed and not prev_pressed:
                pending_inputs[action] = ts
        
        # Check if pending inputs resulted in state changes
        for action, press_ts in list(pending_inputs.items()):
            # Map action input to expected state name substring
            matched = False
            if action == "roll" and "ROLL" in curr_state: matched = True
            elif action == "dash" and "DASH" in curr_state: matched = True
            elif action == "jump" and "JUMP" in curr_state: matched = True
            elif action == "attack" and "ATTACK" in curr_state: matched = True
            elif action == "special" and "SPECIAL" in curr_state: matched = True
            elif action == "transform" and "TRANSFORM" in curr_state: matched = True
            
            if matched:
                latency = ts - press_ts
                latency_records.append(latency)
                del pending_inputs[action]
            elif ts - press_ts > 1000: # Timeout after 1 second
                del pending_inputs[action]

        last_inputs = curr_inputs

    avg_latency_ms = sum(latency_records) / len(latency_records) if latency_records else 0.0

    # 4. Dodge & Damage Avoidance Effectiveness
    rolls_triggered = 0
    dashes_triggered = 0
    last_state = ""
    dodge_damage_avoided = 0
    
    # Damage events
    damage_events = [e for e in events if e.get("event_type") == "damage_received"]
    
    for f in frames:
        p = f.get("player")
        if not p or "state" not in p:
            continue
        
        curr_state = p["state"].upper()
        if curr_state != last_state:
            if curr_state == "ROLL":
                rolls_triggered += 1
            elif curr_state == "DASH":
                dashes_triggered += 1
        last_state = curr_state

    # Check if damage received events happened during a dodge state
    for devt in damage_events:
        devt_ts = devt.get("timestamp_ms", 0)
        # Find closest frame
        closest_frame = min(frames, key=lambda fr: abs(fr["timestamp_ms"] - devt_ts))
        p = closest_frame.get("player")
        if p:
            st = p.get("state", "").upper()
            if st in ("ROLL", "DASH") and p.get("is_invincible", False):
                dodge_damage_avoided += 1

    # 5. Choppiness & Animation Interruptions
    # Count times non-looping states changed to another state before completion
    choppiness_events = 0
    non_looping_states = ("ATTACK_THRUST", "ATTACK_SMASH", "ATTACK_POWER", "ROLL", "DASH", "TRANSFORM", "HURT")
    
    last_p_state = ""
    last_anim_idx = 0.0
    
    for f in frames:
        p = f.get("player")
        if not p or "state" not in p:
            continue
        curr_state = p["state"].upper()
        anim_idx = p.get("animation_index", 0.0)
        
        if last_p_state in non_looping_states and curr_state != last_p_state:
            # If the state changed but animation index was small (e.g. < 2.0 frames), it was interrupted early!
            if last_anim_idx < 3.0:
                choppiness_events += 1
        
        last_p_state = curr_state
        last_anim_idx = anim_idx

    # 6. Generate Game Feel Recommendations
    recommendations: List[str] = []
    
    # Analyze Roll/Dash efficiency
    total_dodges = rolls_triggered + dashes_triggered
    if total_dodges > 0:
        dodge_efficiency = (dodge_damage_avoided / total_dodges) * 100
        if dodge_efficiency < 20.0:
            recommendations.append(
                "**Dodge Roll / Dash invincibility feels too narrow.** The damage avoidance success rate is low (" + 
                f"{dodge_efficiency:.1f}%). Consider **increasing** the *grants_invincibility* duration or increasing the animation speed of `ROLL` / `DASH` by **+0.05** so it completes faster."
            )
    else:
        recommendations.append(
            "**Dodge mechanics underutilized.** No rolls or dashes were recorded. If the boss combat is too punishing, recommend lowering boss spell tracking."
        )

    # Analyze state durations
    roll_pct = state_pcts.get("ROLL", 0.0)
    dash_pct = state_pcts.get("DASH", 0.0)
    if roll_pct > 15.0 or dash_pct > 15.0:
        recommendations.append(
            "**Spamming Dodge maneuvers detected.** Player spent a high percentage of time rolling/dashing (" +
            f"Roll: {roll_pct:.1f}%, Dash: {dash_pct:.1f}%). To discourage spamming and improve tactical feel, consider setting **locks_input=True** or **locks_movement=True** on the `ROLL` configuration, or increasing recovery frames."
        )

    # Analyze responsiveness
    if avg_latency_ms > 100.0:
        recommendations.append(
            f"**High Input Latency Detected ({avg_latency_ms:.1f}ms).** Transitions to action states feel sluggish. Verify if the player's prior state config has **interruptible=False** or increase the player movement update rate."
        )
    elif avg_latency_ms > 0:
        recommendations.append(
            f"**Excellent responsiveness ({avg_latency_ms:.1f}ms average input-to-state delay).** The controls feel crisp."
        )

    # Analyze animation choppiness
    if choppiness_events > 5:
        recommendations.append(
            f"**High Animation Choppiness ({choppiness_events} early interrupts).** Players are canceling attacks/hurt animations before they finish displaying. To make animations feel more weighty and impactful, consider set **interruptible=False** on `ATTACK_THRUST`, `ATTACK_SMASH` or check state exit configurations."
        )

    # Stagnant vs running ratio
    idle_pct = state_pcts.get("IDLE", 0.0)
    run_pct = state_pcts.get("RUN", 0.0)
    if idle_pct > 40.0:
        recommendations.append(
            f"**Player is highly stationary ({idle_pct:.1f}% Idle).** Consider making the boss AI cast zoning spells to force player movement."
        )

    return {
        "log_name": log_path.name,
        "duration_sec": duration_sec,
        "avg_fps": avg_fps,
        "total_frames": total_frames,
        "state_pcts": state_pcts,
        "avg_latency_ms": avg_latency_ms,
        "rolls": rolls_triggered,
        "dashes": dashes_triggered,
        "damage_avoided": dodge_damage_avoided,
        "choppiness": choppiness_events,
        "recommendations": recommendations
    }

def generate_report(results: Dict[str, Any], output_path: Path):
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # State distribution table rows
    table_rows = []
    for state, pct in sorted(results["state_pcts"].items(), key=lambda item: item[1], reverse=True):
        table_rows.append(f"| {state} | {pct:.1f}% |")
    table_str = "\n".join(table_rows)

    recs_str = "\n".join([f"- {r}" for r in results["recommendations"]])

    content = f"""# Gameplay Telemetry & Game Feel Analysis Report

**Generated on**: {now_str}
**Log File**: `{results["log_name"]}`

---

## 📊 Session Statistics

| Metric | Value |
|---|---|
| **Session Duration** | {results["duration_sec"]:.1f} seconds |
| **Average Frame Rate** | {results["avg_fps"]:.1f} FPS |
| **Total Frames Logged** | {results["total_frames"]} |
| **Control Latency (Avg)** | {results["avg_latency_ms"]:.1f} ms |
| **Dodge Rolls Triggered** | {results["rolls"]} |
| **Dashes Triggered** | {results["dashes"]} |
| **Hits Avoided via Dodge** | {results["damage_avoided"]} |
| **Animation Early Interrupts** | {results["choppiness"]} |

---

## 🔄 Player State Distribution

| State | Time Spent (%) |
|---|---|
{table_str}

---

## 🧠 God Mode AI & Game Feel Recommendations

{recs_str}

---

*Use the **Player Animation Configurator** (`player_editor.py`) to apply these recommendations by adjusting animation speeds, loop settings, or input/movement locks for the respective states.*
"""

    with open(output_path, "w") as f:
        f.write(content)
    print(f"[INFO] Report generated successfully at: {output_path}")

def main():
    log_dir = Path("logs/gameplay_tracking")
    if not log_dir.exists():
        print(f"[ERROR] Telemetry directory does not exist: {log_dir}")
        sys.exit(1)
        
    # Find latest .jsonl log file
    log_files = list(log_dir.glob("*.jsonl"))
    if not log_files:
        print("[ERROR] No JSONL telemetry logs found in logs/gameplay_tracking/")
        sys.exit(1)
        
    latest_log = max(log_files, key=lambda p: p.stat().st_mtime)
    
    analysis = analyze_session(latest_log)
    if not analysis:
        print("[ERROR] Telemetry analysis failed.")
        sys.exit(1)
        
    report_path = log_dir / "gameplay_analysis_report.md"
    generate_report(analysis, report_path)

if __name__ == "__main__":
    main()
