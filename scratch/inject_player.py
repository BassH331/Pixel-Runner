import sys
import re
sys.path.append("/home/chosen333/Software/Pixel-Runner")
from player_editor import DEFAULT_ATTACK_CONFIGS

player_path = "/home/chosen333/Software/Pixel-Runner/src/game/entities/player.py"
with open(player_path, "r") as f:
    content = f.read()

def format_config(name, cfg):
    lines = [f"    {name}: Final[AttackConfig] = AttackConfig("]
    lines.append(f"        hit_frames=frozenset({cfg['hit_frames']}),")
    lines.append(f"        base_damage={cfg['base_damage']},")
    lines.append(f"        knockback_force={cfg['knockback_force']},")
    lines.append(f"        knockback_angle={cfg['knockback_angle']},")
    lines.append(f"        hit_stop_frames={cfg['hit_stop_frames']},")
    lines.append(f"        can_hit_multiple={cfg['can_hit_multiple']},")
    lines.append(f"        max_hits_per_target={cfg['max_hits_per_target']},")
    lines.append(f"        frame_damage_modifiers={cfg['frame_damage_modifiers']},")
    
    lines.append("        hitbox_data={")
    for f_idx, hb in cfg["hitbox_data"].items():
        lines.append(f"            {f_idx}: HitboxData(offset_x={hb['offset_x']}, offset_y={hb['offset_y']}, width={hb['width']}, height={hb['height']}),")
    lines.append("        },")
    
    lines.append(f"        startup_frames=frozenset({cfg['startup_frames']}),")
    lines.append(f"        recovery_frames=frozenset({cfg['recovery_frames']}),")
    lines.append("    )")
    return "\n".join(lines)

# Generate replacement string
new_configs = []
new_configs.append("    # Thrust Attack")
new_configs.append(format_config("THRUST_ATTACK_CONFIG", DEFAULT_ATTACK_CONFIGS["THRUST_ATTACK_CONFIG"]))
new_configs.append("\n    # Smash Attack")
new_configs.append(format_config("SMASH_ATTACK_CONFIG", DEFAULT_ATTACK_CONFIGS["SMASH_ATTACK_CONFIG"]))
new_configs.append("\n    # Power Attack")
new_configs.append(format_config("POWER_ATTACK_CONFIG", DEFAULT_ATTACK_CONFIGS["POWER_ATTACK_CONFIG"]))
new_configs.append("\n    # Special Attack")
new_configs.append(format_config("SPECIAL_ATTACK_CONFIG", DEFAULT_ATTACK_CONFIGS["SPECIAL_ATTACK_CONFIG"]))
new_configs.append("\n    # Enhanced Special Attack")
new_configs.append(format_config("ENHANCED_SPECIAL_ATTACK_CONFIG", DEFAULT_ATTACK_CONFIGS["ENHANCED_SPECIAL_ATTACK_CONFIG"]))

replacement = "\n".join(new_configs)

# Regex to find the block from THRUST_ATTACK_CONFIG to the end of ENHANCED_SPECIAL_ATTACK_CONFIG
pattern = re.compile(r"    # Thrust Attack.*?    ENHANCED_SPECIAL_ATTACK_CONFIG: Final\[AttackConfig\] = AttackConfig\(.*?\n    \)", re.DOTALL)

new_content = pattern.sub(replacement, content)

with open(player_path, "w") as f:
    f.write(new_content)
print("player.py successfully updated with surgical hitboxes.")
