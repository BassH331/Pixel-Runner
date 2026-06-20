import json

with open("game_data/player_config.json", "r") as f:
    overrides = json.load(f)

attacks = overrides.get("attacks", {})
for attack_key, atk_dict in attacks.items():
    print(f"Attack: {attack_key}")
    hitbox_data = {}
    for k, v in atk_dict.get("hitbox_data", {}).items():
        print(f"  Frame {k}: {v}")
