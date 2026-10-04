import os
import json
import urllib.request
import urllib.error
from typing import Dict, Any, List, Optional

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "AIzaSyB42ZOfBEJNakWLaPYGBW8xx0hm99nAFew")
GEMINI_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash:generateContent?key={GEMINI_API_KEY}"

SYSTEM_PROMPT = """You are the AI Narrative & Boss Director for Pixel Runner, a 2D action platformer.
LORE CONTEXT:
- Protagonist: Kaelen, a fallen knight who accepted a demonic pact for survival.
- Andras / The Demon: A Marquis of Discord manipulating Kaelen, tempting him to give in to darkness.
- Candora / The Light: An angelic spirit trying to pull Kaelen back to his humanity.

Analyze the provided frame telemetry (player/boss positions, velocities, dash/parry states, HP, defend turtling) and return ONLY a single JSON object matching this schema:
{
  "target_tactic": "PINCER_FLANK" | "BAIT_DASH" | "PARRY_COUNTER" | "RANGED_PRESSURE" | "RETREAT_BUFF" | "AGGRESSIVE_RUSH" | "GUARD_BREAK",
  "aggression_multiplier": float (0.5 to 2.0),
  "preferred_attack_sequence": list of attack string identifiers,
  "movement_bias_x": float (-1.0 to 1.0),
  "contextual_taunt": string or null,
  "narrative_event": null OR object {
    "speaker_name": "Andras" | "The Light",
    "dialogue_text": string,
    "option_1_label": string,
    "option_1_buff": dict (e.g. {"dmg_mult": 1.4, "hp_cost_pct": 0.20}),
    "option_2_label": string,
    "option_2_buff": dict (e.g. {"mana_restore": 30, "guard_buff": 0.25})
  }
}
Do NOT include markdown formatting or extra text."""


def evaluate_telemetry_directive(telemetry_payload: Dict[str, Any]) -> Dict[str, Any]:
    """Evaluate telemetry via Gemini/Moonshot LLM API or fallback to zero-cost deterministic engine if offline."""
    api_key = os.environ.get("MOONSHOT_API_KEY") or os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return generate_fallback_directive(telemetry_payload)

    try:
        req_data = {
            "system_instruction": {
                "parts": [{"text": SYSTEM_PROMPT}]
            },
            "contents": [{
                "parts": [{"text": json.dumps(telemetry_payload)}]
            }],
            "generationConfig": {
                "responseMimeType": "application/json",
                "temperature": 0.3
            }
        }

        api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash:generateContent?key={api_key}" if not os.environ.get("MOONSHOT_API_KEY") else "https://api.moonshot.cn/v1/chat/completions"

        req = urllib.request.Request(
            api_url,
            data=json.dumps(req_data).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST"
        )

        with urllib.request.urlopen(req, timeout=8.0) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if "candidates" in data:
                content = data["candidates"][0]["content"]["parts"][0]["text"]
            elif "choices" in data:
                content = data["choices"][0]["message"]["content"]
            else:
                raise ValueError(f"Unrecognized response format: {list(data.keys())}")
            parsed = json.loads(content)
            return sanitize_directive(parsed)
    except Exception as e:
        # Graceful fallback on network timeout, rate limit, or parse error
        print(f"Gemini API Exception: {e}")
        return generate_fallback_directive(telemetry_payload)


def generate_fallback_directive(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Zero-cost deterministic fallback logic derived from player/boss frame metrics."""
    frames = payload.get("frames", [])
    if not frames:
        return {
            "target_tactic": "AGGRESSIVE_RUSH",
            "aggression_multiplier": 1.0,
            "preferred_attack_sequence": ["SLASH"],
            "movement_bias_x": 0.0,
            "contextual_taunt": None,
            "narrative_event": None
        }

    last_frame = frames[-1]
    world_dist = last_frame.get("world_distance", 100.0)
    player = last_frame.get("player", {}) or {}
    boss = last_frame.get("boss", {}) or {}
    
    player_hp = player.get("hp", 100)
    player_state = str(player.get("state", ""))
    is_turtling = player_state.upper() == "DEFEND" or player.get("is_defending", False)

    # Detect turtling vs standard tactics
    if is_turtling:
        tactic = "GUARD_BREAK"
        taunt = "Mashing your shield won't save you from the Darkness!"
        narrative_evt = {
            "speaker_name": "Andras",
            "dialogue_text": "Feel your humanity slipping, Kaelen? Cowardice only speeds up the process!",
            "option_1_label": "[1] Accept Shadow Edge (+40% DMG, -20% HP)",
            "option_1_buff": {"dmg_mult": 1.4, "hp_cost_pct": 0.20},
            "option_2_label": "[2] Hold Elysia's Memory (+30 Mana, Guard Resilient)",
            "option_2_buff": {"mana_restore": 30, "guard_buff": 0.25}
        }
    elif player_hp < 30:
        tactic = "AGGRESSIVE_RUSH"
        taunt = "Your blood runs cold, my vessel!"
        narrative_evt = {
            "speaker_name": "The Light",
            "dialogue_text": "Stay human, Kaelen! You do not have to give in to his power.",
            "option_1_label": "[1] Silver Light Healing (+40 HP)",
            "option_1_buff": {"hp_restore": 40},
            "option_2_label": "[2] Runner's Will (+30% Movement Speed)",
            "option_2_buff": {"speed_mult": 1.3}
        }
    elif world_dist < 80.0:
        tactic = "PINCER_FLANK"
        taunt = "You are cornered!"
        narrative_evt = None
    elif player.get("is_dashing"):
        tactic = "BAIT_DASH"
        taunt = "Dash all you want, you cannot escape!"
        narrative_evt = None
    else:
        tactic = "RANGED_PRESSURE"
        taunt = None
        narrative_evt = None

    aggression = 1.4 if is_turtling or player_hp < 30 else 1.0

    return {
        "target_tactic": tactic,
        "aggression_multiplier": aggression,
        "preferred_attack_sequence": ["GUARD_BREAK_SLAM", "FIREBALL"] if is_turtling else ["SWIPE", "FIREBALL"],
        "movement_bias_x": -0.5 if world_dist < 50.0 else 0.5,
        "contextual_taunt": taunt,
        "narrative_event": narrative_evt
    }


def sanitize_directive(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Ensure output fields stay strictly bounded to valid types and ranges."""
    valid_tactics = {"PINCER_FLANK", "BAIT_DASH", "PARRY_COUNTER", "RANGED_PRESSURE", "RETREAT_BUFF", "AGGRESSIVE_RUSH", "GUARD_BREAK"}
    tactic = raw.get("target_tactic") if raw.get("target_tactic") in valid_tactics else "AGGRESSIVE_RUSH"
    
    try:
        aggression = max(0.5, min(2.0, float(raw.get("aggression_multiplier", 1.0))))
    except (TypeError, ValueError):
        aggression = 1.0
        
    try:
        bias = max(-1.0, min(1.0, float(raw.get("movement_bias_x", 0.0))))
    except (TypeError, ValueError):
        bias = 0.0

    seq = raw.get("preferred_attack_sequence", [])
    if not isinstance(seq, list):
        seq = []
    seq = [str(item) for item in seq[:5]]

    taunt = str(raw.get("contextual_taunt"))[:120] if raw.get("contextual_taunt") else None
    
    narrative_evt = raw.get("narrative_event")
    if not isinstance(narrative_evt, dict):
        narrative_evt = None
    else:
        narrative_evt = {
            "speaker_name": str(narrative_evt.get("speaker_name", "Andras"))[:60],
            "dialogue_text": str(narrative_evt.get("dialogue_text", ""))[:250],
            "option_1_label": str(narrative_evt.get("option_1_label", "[1] Option 1"))[:80],
            "option_1_buff": narrative_evt.get("option_1_buff", {}) if isinstance(narrative_evt.get("option_1_buff"), dict) else {},
            "option_2_label": str(narrative_evt.get("option_2_label", "[2] Option 2"))[:80],
            "option_2_buff": narrative_evt.get("option_2_buff", {}) if isinstance(narrative_evt.get("option_2_buff"), dict) else {}
        }

    return {
        "target_tactic": tactic,
        "aggression_multiplier": aggression,
        "preferred_attack_sequence": seq,
        "movement_bias_x": bias,
        "contextual_taunt": taunt,
        "narrative_event": narrative_evt
    }
