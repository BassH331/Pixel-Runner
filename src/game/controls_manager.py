"""
src/game/controls_manager.py
Centralized input mapping and local persistence system for PC Keyboard and USB Gamepad/Joystick.
"""

import os
import json
import pygame as pg
from typing import Dict, Any, Optional, Tuple, List

CONFIG_PATH = os.path.join("game_data", "controls_config.json")

ACTIONS: List[str] = [
    "MOVE_LEFT",
    "MOVE_RIGHT",
    "JUMP",
    "ATTACK_THRUST",
    "ATTACK_SMASH",
    "ATTACK_POWER",
    "DEFEND",
    "ROLL",
    "DASH",
    "SPECIAL_ATTACK",
    "TRANSFORM",
]

ACTION_METADATA: Dict[str, Dict[str, str]] = {
    "MOVE_LEFT": {"name": "Move Left", "desc": "Walk / run to the left", "state": "RUN"},
    "MOVE_RIGHT": {"name": "Move Right", "desc": "Walk / run to the right", "state": "RUN"},
    "JUMP": {"name": "Jump", "desc": "Leap into the air", "state": "JUMP_UP"},
    "ATTACK_THRUST": {"name": "Thrust Attack", "desc": "Fast forward thrust attack", "state": "ATTACK_THRUST"},
    "ATTACK_SMASH": {"name": "Smash Attack", "desc": "Heavy downward slash attack", "state": "ATTACK_SMASH"},
    "ATTACK_POWER": {"name": "Power Attack", "desc": "Charged multi-hit spin attack", "state": "ATTACK_POWER"},
    "DEFEND": {"name": "Defend / Guard", "desc": "Raise shield to block attacks", "state": "DEFEND"},
    "ROLL": {"name": "Evade Roll", "desc": "Roll forward with invincibility", "state": "ROLL"},
    "DASH": {"name": "Quick Dash", "desc": "Fast burst movement", "state": "DASH"},
    "SPECIAL_ATTACK": {"name": "Special Attack", "desc": "Unleash ultimate shadow attack", "state": "SPECIAL_ATTACK"},
    "TRANSFORM": {"name": "Transform State", "desc": "Channel inner warrior power", "state": "TRANSFORM"},
}

DEFAULT_KEYBOARD_BINDINGS: Dict[str, str] = {
    "MOVE_LEFT": "left",
    "MOVE_RIGHT": "right",
    "JUMP": "space",
    "ATTACK_THRUST": "q",
    "ATTACK_SMASH": "e",
    "ATTACK_POWER": "w",
    "DEFEND": "r",
    "ROLL": "left shift",
    "DASH": "left ctrl",
    "SPECIAL_ATTACK": "f",
    "TRANSFORM": "t",
}

DEFAULT_JOYSTICK_BINDINGS: Dict[str, str] = {
    "MOVE_LEFT": "AXIS_0_MINUS",
    "MOVE_RIGHT": "AXIS_0_PLUS",
    "JUMP": "BUTTON_0",
    "ATTACK_THRUST": "BUTTON_2",
    "ATTACK_SMASH": "BUTTON_1",
    "ATTACK_POWER": "BUTTON_3",
    "DEFEND": "BUTTON_7",
    "ROLL": "BUTTON_4",
    "DASH": "BUTTON_5",
    "SPECIAL_ATTACK": "BUTTON_6",
    "TRANSFORM": "BUTTON_8",
}

JOYSTICK_LABELS: Dict[str, str] = {
    "BUTTON_0": "Button 0 (A / Cross)",
    "BUTTON_1": "Button 1 (B / Circle)",
    "BUTTON_2": "Button 2 (X / Square)",
    "BUTTON_3": "Button 3 (Y / Triangle)",
    "BUTTON_4": "Button 4 (L1 / LB)",
    "BUTTON_5": "Button 5 (R1 / RB)",
    "BUTTON_6": "Button 6 (L2 Trigger)",
    "BUTTON_7": "Button 7 (R2 Trigger)",
    "BUTTON_8": "Button 8 (Select / Share)",
    "BUTTON_9": "Button 9 (Start / Options)",
    "BUTTON_10": "Button 10 (L3 Stick Press)",
    "BUTTON_11": "Button 11 (R3 Stick Press)",
    "AXIS_0_MINUS": "Left Stick Left",
    "AXIS_0_PLUS": "Left Stick Right",
    "AXIS_1_MINUS": "Left Stick Up",
    "AXIS_1_PLUS": "Left Stick Down",
}


class ControlsManager:
    _instance: Optional['ControlsManager'] = None

    def __new__(cls) -> 'ControlsManager':
        if cls._instance is None:
            cls._instance = super(ControlsManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if getattr(self, '_initialized', False):
            return
        self._initialized = True
        self.mode: str = "KEYBOARD"  # "KEYBOARD" or "JOYSTICK"
        self.keyboard_bindings: Dict[str, str] = dict(DEFAULT_KEYBOARD_BINDINGS)
        self.joystick_bindings: Dict[str, str] = dict(DEFAULT_JOYSTICK_BINDINGS)
        self.load_config()

    def get_mode(self) -> str:
        return self.mode

    def set_mode(self, mode: str) -> None:
        if mode in ("KEYBOARD", "JOYSTICK"):
            self.mode = mode

    def load_config(self) -> None:
        """Load bindings from local JSON configuration file."""
        if not os.path.exists(CONFIG_PATH):
            self.reset_to_defaults()
            return
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.mode = data.get("active_mode", "KEYBOARD")
                
                kb = data.get("keyboard_bindings", {})
                for action in ACTIONS:
                    if action in kb:
                        self.keyboard_bindings[action] = str(kb[action])

                js = data.get("joystick_bindings", {})
                for action in ACTIONS:
                    if action in js:
                        self.joystick_bindings[action] = str(js[action])
        except Exception as e:
            print(f"[ControlsManager] Failed to load controls config: {e}. Reverting to defaults.")
            self.reset_to_defaults()

    def save_config(self) -> bool:
        """Save active configuration to local JSON file."""
        data = {
            "active_mode": self.mode,
            "keyboard_bindings": self.keyboard_bindings,
            "joystick_bindings": self.joystick_bindings,
        }
        try:
            os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
            return True
        except Exception as e:
            print(f"[ControlsManager] Failed to save controls config: {e}")
            return False

    def reset_to_defaults(self) -> None:
        self.mode = "KEYBOARD"
        self.keyboard_bindings = dict(DEFAULT_KEYBOARD_BINDINGS)
        self.joystick_bindings = dict(DEFAULT_JOYSTICK_BINDINGS)
        self.save_config()

    def get_binding(self, action: str, mode: Optional[str] = None) -> str:
        target_mode = mode or self.mode
        if target_mode == "KEYBOARD":
            return self.keyboard_bindings.get(action, DEFAULT_KEYBOARD_BINDINGS.get(action, ""))
        else:
            return self.joystick_bindings.get(action, DEFAULT_JOYSTICK_BINDINGS.get(action, ""))

    def set_binding(self, action: str, raw_binding: str, mode: Optional[str] = None) -> None:
        target_mode = mode or self.mode
        if target_mode == "KEYBOARD":
            self.keyboard_bindings[action] = raw_binding
        else:
            self.joystick_bindings[action] = raw_binding

    def get_display_name_for_binding(self, raw_binding: str, mode: Optional[str] = None) -> str:
        target_mode = mode or self.mode
        if not raw_binding:
            return "UNBOUND"

        sub_inputs = [s.strip() for s in raw_binding.split("+")]
        display_parts = []

        for sub in sub_inputs:
            if target_mode == "KEYBOARD":
                display_parts.append(sub.upper())
            else:
                display_parts.append(JOYSTICK_LABELS.get(sub, sub.replace("_", " ")))

        return " + ".join(display_parts)

    def get_keycode(self, action: str) -> Optional[int]:
        binding_str = self.get_binding(action, "KEYBOARD")
        if not binding_str:
            return None
        # If combination, take the last key (primary action key)
        primary_key = binding_str.split("+")[-1].strip()
        try:
            return pg.key.key_code(primary_key)
        except Exception:
            return None

    def _check_single_joystick_input(self, js_binding: str, joystick: Any) -> bool:
        if js_binding.startswith("BUTTON_"):
            try:
                btn_idx = int(js_binding.split("_")[1])
                if btn_idx < joystick.get_numbuttons():
                    return bool(joystick.get_button(btn_idx))
            except Exception:
                return False

        elif js_binding.startswith("AXIS_"):
            parts = js_binding.split("_")
            if len(parts) >= 3:
                try:
                    axis_idx = int(parts[1])
                    direction = parts[2]
                    if axis_idx < joystick.get_numaxes():
                        val = joystick.get_axis(axis_idx)
                        if direction == "MINUS" and val < -0.5:
                            return True
                        elif direction == "PLUS" and val > 0.5:
                            return True
                except Exception:
                    return False
        return False

    def is_action_pressed(
        self,
        action: str,
        keys: Any,
        joystick: Optional[Any] = None,
    ) -> bool:
        """Check if a given action is currently active based on key state or joystick state. Supports combinations (e.g. 'left shift + f', 'BUTTON_4 + BUTTON_5')."""
        if self.mode == "KEYBOARD" or joystick is None:
            kb_binding = self.get_binding(action, "KEYBOARD")
            if not kb_binding:
                return False

            parts = [p.strip() for p in kb_binding.split("+")]
            for part in parts:
                try:
                    code = pg.key.key_code(part)
                    if not keys[code]:
                        return False
                except Exception:
                    return False
            return True
        
        # JOYSTICK mode
        js_binding = self.get_binding(action, "JOYSTICK")
        if not js_binding:
            return False

        parts = [p.strip() for p in js_binding.split("+")]
        for part in parts:
            if not self._check_single_joystick_input(part, joystick):
                return False
        return True


