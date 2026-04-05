# Level Configuration Guide

This guide documents the JSON format used to configure levels in **Runner: Guardian of the Star-Fire**. Each level is defined by a single `.json` file in the `game_data/` directory.

---

## Quick Reference

```json
{
    "level_name": "The Blight Begins",
    "level_end_distance": 8000,
    "spawn_rate_min": 5000,
    "spawn_rate_max": 15000,
    "spawn_zones": [ ... ],
    "bat_spawn": { ... },
    "entities": [ ... ],
    "checkpoints": [ ... ],
    "world_events": [ ... ]
}
```

---

## Top-Level Keys

| Key | Type | Default | Description |
|---|---|---|---|
| `level_name` | `string` | `"The Blight Begins"` | Display name shown on the notification banner when the level starts. |
| `level_end_distance` | `number` | `8000` | World distance (pixels) the player must travel to trigger the "Level Complete" message. |
| `spawn_rate_min` | `integer` | `5000` | Minimum delay (ms) between bat wave spawns. |
| `spawn_rate_max` | `integer` | `15000` | Maximum delay (ms) between bat wave spawns. A random value between min and max is chosen each wave. |

---

## Spawn Zones

Controls how skeleton enemies scale in difficulty as the player travels further. The game checks the player's **max distance reached** against these zones and uses the matching zone's config for spawning.

```json
"spawn_zones": [
    {"min_dist": 0,    "max_dist": 1000,  "max_skeletons": 2, "delay": 6000},
    {"min_dist": 1000, "max_dist": 3000,  "max_skeletons": 3, "delay": 4000},
    {"min_dist": 3000, "max_dist": 6000,  "max_skeletons": 5, "delay": 3000},
    {"min_dist": 6000, "max_dist": 99999, "max_skeletons": 6, "delay": 2000}
]
```

| Field | Type | Description |
|---|---|---|
| `min_dist` | `number` | Minimum distance for this zone to activate. |
| `max_dist` | `number` | Maximum distance for this zone. Use `99999` for the final zone (treated as infinity). |
| `max_skeletons` | `integer` | Maximum simultaneous skeletons allowed on screen in this zone. |
| `delay` | `integer` | Delay (ms) between skeleton spawn attempts in this zone. Lower = more frequent. |

**How it works:** Zones are checked in reverse order (highest distance first). The first zone where `max_distance_reached >= min_dist` is selected. If no zone matches, the first zone is used as fallback.

**Design tips:**
- Start easy (few skeletons, long delays) and ramp up
- The final zone should have `max_dist: 99999` to catch all remaining distance
- Adjust `delay` to control intensity — values below `2000` feel very aggressive

---

## Bat Spawn

Controls how many bats appear per wave.

```json
"bat_spawn": {
    "min_count": 3,
    "max_count": 5
}
```

| Field | Type | Default | Description |
|---|---|---|---|
| `min_count` | `integer` | `3` | Minimum bats per wave. |
| `max_count` | `integer` | `5` | Maximum bats per wave. A random count between min and max is chosen. |

Bat wave **timing** is controlled by `spawn_rate_min` / `spawn_rate_max` (see above).

---

## Entities

Initial entity placements when the level loads.

```json
"entities": [
    {"type": "player", "x": 200, "y": 600}
]
```

| Field | Type | Description |
|---|---|---|
| `type` | `string` | Entity type. Currently only `"player"` is supported. |
| `x` | `integer` | Horizontal spawn position (pixels from left). |
| `y` | `integer` | Vertical spawn position (pixels from top). The player's `midbottom` is set to this point. |

---

## Checkpoints

Save points placed in the world (currently for future use).

```json
"checkpoints": [
    {"id": 1, "x": 1200, "y": 200}
]
```

| Field | Type | Description |
|---|---|---|
| `id` | `integer` | Unique checkpoint identifier. |
| `x` | `integer` | Horizontal position. |
| `y` | `integer` | Vertical position. |

---

## World Events

Distance-triggered events that activate as the player progresses. These are the core of level scripting — use them to tell stories, introduce NPCs, and spawn enemy ambushes.

```json
"world_events": [
    {
        "id": 1,
        "distance": 400,
        "type": "interaction",
        "params": { ... }
    }
]
```

### Common Fields

| Field | Type | Description |
|---|---|---|
| `id` | `integer` | Unique event ID. Must not repeat within a level. |
| `distance` | `number` | World distance at which this event triggers. Events fire once when the player crosses this threshold. |
| `type` | `string` | Event type: `"interaction"`, `"npc"`, or `"enemy_wave"`. |
| `params` | `object` | Type-specific parameters (see below). |

---

### Event Type: `interaction`

Spawns an interaction point (proximity trigger with dialogue text).

```json
{
    "id": 1,
    "distance": 400,
    "type": "interaction",
    "params": {
        "title": "Old Warrior",
        "radius": 160,
        "text": "The path ahead grows darker, traveler..."
    }
}
```

| Param | Type | Description |
|---|---|---|
| `title` | `string` | Header text shown in the objective overlay. |
| `radius` | `integer` | Proximity radius (pixels) — how close the player must be to interact. |
| `text` | `string` | Dialogue/story text shown when the player interacts. |

---

### Event Type: `npc`

Spawns an animated NPC with dialogue.

```json
{
    "id": 4,
    "distance": 1200,
    "type": "npc",
    "params": {
        "npc_type": "wizard",
        "title": "Wizard",
        "radius": 180,
        "text": "Halt, traveler! The ancient wards grow weak..."
    }
}
```

| Param | Type | Description |
|---|---|---|
| `npc_type` | `string` | NPC variant. Currently supported: `"wizard"`. |
| `title` | `string` | NPC name shown in the dialogue overlay. |
| `radius` | `integer` | Proximity radius for interaction. |
| `text` | `string` | Dialogue text. |

---

### Event Type: `enemy_wave`

Spawns a group of enemies at the given distance.

```json
{
    "id": 5,
    "distance": 3500,
    "type": "enemy_wave",
    "params": {
        "count": 6,
        "type": "bat"
    }
}
```

| Param | Type | Description |
|---|---|---|
| `count` | `integer` | Number of enemies to spawn in this wave. |
| `type` | `string` | Enemy type: `"bat"` or `"skeleton"`. |

---

## Creating a New Level

1. **Copy** `level_1.json` and rename it (e.g. `level_2.json`).
2. **Update** `level_name` and `level_end_distance`.
3. **Tune** spawn difficulty using `spawn_zones` and `bat_spawn`.
4. **Script** the journey using `world_events` — place interactions, NPCs, and ambushes at specific distances.
5. **Update** `game_state.py` to load your new file:
   ```python
   self.level_data = WorldLoader.load_json(os.path.join("game_data", "level_2.json"))
   ```

### Example: A Harder Level

```json
{
    "level_name": "The Bone Fields",
    "level_end_distance": 12000,
    "spawn_rate_min": 3000,
    "spawn_rate_max": 8000,
    "spawn_zones": [
        {"min_dist": 0,    "max_dist": 500,   "max_skeletons": 3, "delay": 4000},
        {"min_dist": 500,  "max_dist": 2000,  "max_skeletons": 5, "delay": 3000},
        {"min_dist": 2000, "max_dist": 5000,  "max_skeletons": 7, "delay": 2000},
        {"min_dist": 5000, "max_dist": 99999, "max_skeletons": 10, "delay": 1500}
    ],
    "bat_spawn": {
        "min_count": 5,
        "max_count": 8
    },
    "entities": [
        {"type": "player", "x": 200, "y": 600}
    ],
    "checkpoints": [],
    "world_events": [
        {
            "id": 1,
            "distance": 300,
            "type": "enemy_wave",
            "params": {"count": 4, "type": "skeleton"}
        },
        {
            "id": 2,
            "distance": 2000,
            "type": "npc",
            "params": {
                "npc_type": "wizard",
                "title": "Dark Wizard",
                "radius": 180,
                "text": "You should not have come here..."
            }
        }
    ]
}
```
