---
name: pixel-runner-add-entity
description: Use when adding a new enemy, NPC, or interactive entity to Pixel-Runner — walks through the full checklist from config JSON to entity class to level event registration.
---

# Adding a New Entity to Pixel-Runner

Follow every step in order. Steps 1–6 apply to all entities. Step 7 covers custom events if needed.

> **Before starting**: activate `pixel-runner-architecture` for directory layout, config loading, and event bus patterns.

---

## Step 1 — Create the Config JSON

File: `game_data/<entity_name>_config.json`

Define the following fields:

```json
{
  "health": 80,
  "speed": 3.5,
  "animations": {
    "idle":    [0, 1, 2],
    "walk":    [0, 1, 2, 3],
    "attack":  [0, 1, 2],
    "hurt":    [0, 1],
    "death":   [0, 1, 2, 3]
  },
  "attack_configs": [
    {
      "hit_frames":      [2, 3],
      "base_damage":     12,
      "knockback_force": 6.0
    }
  ],
  "hitbox": {
    "w": 40, "h": 60,
    "offset_x": 0, "offset_y": 4
  }
}
```

- `animations` maps state name → list of frame indices (matches PNG filenames in the sprite folder).
- Multiple entries in `attack_configs` support multi-attack patterns.

---

## Step 2 — Create the Entity Class

**For enemies** — file: `src/game/entities/<entity_name>.py`

```python
from .base_enemy import BaseEnemy

class EntityName(BaseEnemy):
    CONFIG_KEY = "entity_name"  # must match the JSON filename (without _config.json)

    def __init__(self, pos, config_client, event_bus):
        super().__init__(pos, config_client, event_bus)

    def _get_state(self):
        # Optional: override FSM logic. Return a state name string.
        return super()._get_state()
```

**For NPCs** — file: `src/game/entities/<entity_name>.py`

```python
from .generic_npc import GenericNPC

class EntityName(GenericNPC):
    CONFIG_KEY = "entity_name"
```

- `ConfigClient` is injected; use `self.config` (populated by the base class) to read values.
- Only override `_get_state()` when the entity needs custom FSM logic beyond the default (idle / walk / attack / hurt / death).

---

## Step 3 — Register the Entity

### Regular enemies
Add the class to the spawn pool in `src/game/systems/wave_manager.py`. Find `_ENEMY_CLASS_MAP` (or equivalent spawn dict) and add:

```python
"entity_name": EntityName,
```

Import the class at the top of the file.

### Bosses
Add the class to `_BOSS_CLASS_MAP` in `src/game/entities/boss_manager.py`:

```python
"entity_name": EntityName,
```

If the entity is a boss, also complete the `pixel-runner-add-boss` skill steps.

---

## Step 4 — Register as a Level Event (NPCs and world-spawned enemies)

In `game_data/level_1.json`, add an entry to the `world_events` array:

```json
{
  "type":     "npc",
  "distance": 4800,
  "npc_name": "entity_name",
  "dialogue": "Opening line the NPC says when approached."
}
```

- `distance` is world-scroll pixels from level start.
- `WorldEventManager` reads this array and spawns the entity automatically — no code change needed.
- For enemies spawned via `world_events` instead of waves, use `"type": "enemy"` and add `"enemy_name"`.

---

## Step 5 — Add Sprite Assets

Place sprites in `assets/graphics/<EntityName>/` (PascalCase directory to match Pygame convention):

```
assets/graphics/EntityName/
  idle/
    0.png
    1.png
    2.png
  walk/
    0.png  ...
  attack/
    0.png  ...
  hurt/
    0.png  ...
  death/
    0.png  ...
```

- One subfolder per animation state (matching the keys in `animations` in the config JSON).
- Frames are PNGs named `0.png`, `1.png`, etc. (zero-indexed).

---

## Step 6 — Update Entity Dimensions

Add an entry to `game_data/entity_dimensions.json`:

```json
"EntityName": { "width": 40, "height": 60 }
```

This is used by the physics and collision layers independently of the per-entity config.

---

## Step 7 — Custom Events (if needed)

If the entity emits or listens to events beyond the built-in engine events (`EntityDied`, `DamageDealt`, `DamageReceived`, `StateChanged`, `EntitySpawned`):

1. Add a new dataclass to `src/game/events/custom_events.py`:

```python
from dataclasses import dataclass

@dataclass
class MyEntityTriggered:
    entity_id: int
    position: tuple
```

2. Import it in the entity file and emit via the injected `event_bus`:

```python
self.event_bus.emit(MyEntityTriggered(entity_id=self.id, position=self.rect.center))
```

3. Subscribe in any system that needs to react:

```python
event_bus.subscribe(MyEntityTriggered, self._on_my_entity_triggered)
```

**Never modify engine event files** (`v3x_zulfiqar_gideon/event_bus.py` or any file in `v3x-zulfiqar-gideon/`).
