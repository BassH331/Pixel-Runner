---
name: pixel-runner-narrative
description: Use when modifying or extending the Pixel-Runner narrative systems — covers the corruption meter, whisperer voices, relic system, boss encounter flow, and three-ending resolution.
---

# Pixel-Runner Narrative Systems

Reference this skill whenever you touch corruption, relics, voiced dialogue, boss encounters, or endings. All narrative state is data-driven via `game_data/storyline_config.json`.

> **Prerequisite**: activate `pixel-runner-architecture` first for event bus patterns, state machine usage, and directory layout.

---

## Corruption Meter

**Class**: `CorruptionManager` in `src/game/systems/corruption_manager.py`

### Value and Methods

- Float, clamped to `0.0`–`100.0`. `0` = pure light, `100` = full void.
- `add(amount)` — increases corruption (clamped at 100).
- `reduce(amount)` — decreases corruption (clamped at 0).
- `value` — read-only property returning current float.

### Threshold Properties

| Property | Condition | Effect |
|---|---|---|
| `is_tainted` | `value > 33` | Mild visual vignette, Andras starts to speak more |
| `is_corrupted` | `value > 66` | Strong vignette, boss stat boost, audio distortion |
| `is_void` | `value > 90` | Maximum vignette, Andras dominant |

### Event-Driven Updates

- Subscribes to `EntityDied` and `DamageDealt` via the `EventBus`.
- Per-event corruption deltas are stored in `storyline_config.json` under `corruption_events` — never hardcode deltas in Python.

```json
"corruption_events": {
  "enemy_kill":      0.5,
  "boss_kill":       0.0,
  "damage_dealt":    0.1
}
```

Boss kill deltas come from `relic_boss_map` (applied when the relic is collected, not on boss death directly).

### Rendering

- HUD vignette overlay: `src/game/ui/hud_overlay.py` reads `corruption_manager.value` and scales vignette alpha.
- Corruption bar / soul-stain indicator: `src/game/ui/player_ui.py`.

---

## Relic System

**Class**: `RelicManager` in `src/game/systems/relic_manager.py`

### Relic Definitions

Defined in `storyline_config.json` under `relics`:

```json
"relics": {
  "shattered_gauntlet": {
    "display_name": "Shattered Gauntlet",
    "lore":         "Lore text shown in the reveal cutscene.",
    "icon":         "assets/graphics/ui/relics/shattered_gauntlet.png"
  }
}
```

### Boss-to-Relic Mapping

Defined in `storyline_config.json` under `relic_boss_map`. Each boss maps to a list of 1 or 2 relic entries:

```json
"relic_boss_map": {
  "BloodZombie": [
    { "relic_id": "vial_of_void_blood",   "corruption_delta": 12 },
    { "relic_id": "hollowed_ledger_page", "corruption_delta":  6 }
  ]
}
```

- Blood Zombie and Dark Ronin each drop 2 relics. `RelicManager` emits the second relic 2 seconds after the first.
- Relic collect → `RelicDropped` event → `GameState` pushes `RelicRevealState` → after player dismisses, `CorruptionManager.add(delta)` is called.

### Relic Reveal State

- Class: `RelicRevealState` in `src/game/states/relic_reveal_state.py`
- A lightweight `State` pushed by `GameState` on `RelicDropped`.
- Shows: relic icon, display name, typewriter lore text (via `AnimatedDialogueRenderer`).
- Pops itself when the player presses any key.

### Querying Collected Relics

```python
relic_manager.collected_ids          # list[str] of collected relic IDs
relic_manager.has_relic("relic_id")  # bool
relic_manager.get_lore_text("relic_id")  # str
```

---

## Whisperer System

**Class**: `WhispererSystem` in `src/game/systems/whisperer_system.py`

### What It Does

Delivers reactive spoken-style text overlays from two competing internal voices: **Andras** (demon patron) and **Moon Knight** (moral counterweight). No audio — text overlays only, rendered via `CinematicNarrativeOverlay`.

### Trigger Events

| Trigger | Event Subscribed |
|---|---|
| `on_kill` | `EntityDied` |
| `on_relic` | `RelicDropped` |
| `on_near_death` | `DamageReceived` (when player HP < 20%) |
| `on_boss_spawn` | `StateChanged` (boss encounter start) |
| `on_threshold_crossed` | Internal — fired by `CorruptionManager` when crossing 33/66/90 |

### Speaker Selection

| Corruption Value | Speaker |
|---|---|
| < 40 | Moon Knight |
| 40–60 | Both compete — random weighted selection |
| > 60 | Andras dominant |
| > 50 | Andras dominant overall |

An 8-second minimum cooldown applies between any bark, regardless of trigger.

### Bark Config

Barks are defined in `storyline_config.json` under `whisperer_barks`:

```json
"whisperer_barks": {
  "andras": {
    "on_kill":     ["line 1", "line 2"],
    "on_relic":    ["line 1"],
    "on_boss_spawn": ["line 1", "line 2"]
  },
  "moon_knight": {
    "on_kill":     ["line 1"],
    "on_near_death": ["line 1", "line 2"]
  }
}
```

### CinematicNarrativeOverlay

- File: `src/game/ui/cinematic_narrative_overlay.py`
- Call: `overlay.show(speaker, bark_text)` where `speaker` is `Speaker.ANDRAS` or `Speaker.MOON_KNIGHT`.
- Andras tint: red/dark. Moon Knight tint: silver/blue.
- Uses existing typewriter animation — no new renderer needed.

---

## Boss Encounter Flow

**Class**: `BossEncounterManager` in `src/game/systems/boss_encounter_manager.py`

1. Boss spawn triggers `BossEncounterManager.begin_encounter(boss_name)`.
2. Boss AI is frozen briefly.
3. Pre-fight dialogue shown via `CinematicNarrativeOverlay`. Variant selected by corruption thresholds (`low` ≤33, `mid` 34–66, `high` ≥67).
4. After dialogue, boss AI is released — combat begins.
5. On boss death: death line shown, then `RelicDropped` event emitted (handled by `RelicManager` and `GameState`).

Boss order is enforced via `boss_sequence` in `game_data/level_1.json`. Bosses cannot spawn out of order.

---

## Three-Ending Resolution

**Class**: `EndingManager` in `src/game/systems/ending_manager.py`

### Trigger

- `boss_manager.py` emits `FinalBossDefeated` when the last boss in `boss_sequence` dies.
- `GameState` subscribes to `FinalBossDefeated` and calls `EndingManager.resolve()`.

### Ending Types

| Ending | Corruption Range | Narrative |
|---|---|---|
| `DARK` | ≥ 75 | Protagonist consumed by Andras. |
| `LIGHT` | ≤ 25 | Protagonist breaks the pact. |
| `AMBIGUOUS` | 26–74 | Protagonist survives but remains marked. |

### Ending State

- Class: `EndingState` in `src/game/states/ending_state.py`
- Pushed by `EndingManager`. Receives ending type as an enum (`EndingType.DARK / LIGHT / AMBIGUOUS`).
- Renders typewriter outro text, final Andras or Moon Knight bark, then credits scroll.
- On completion, pops to `MainMenuState`.

### Persistence

`save_manager.py` persists on ending:
- `final_corruption_value` (float)
- `ending_type` (string: `"dark"` / `"light"` / `"ambiguous"`)
- `relics_collected` (list of relic IDs)

---

## Config Reference Cheatsheet

| Config File | Key | Purpose |
|---|---|---|
| `storyline_config.json` | `corruption_events` | Per-event corruption deltas |
| `storyline_config.json` | `relics` | Relic definitions (lore, icon) |
| `storyline_config.json` | `relic_boss_map` | Boss → relic list with corruption delta |
| `storyline_config.json` | `boss_dialogue` | Per-boss pre-fight, death, and corruption-variant lines |
| `storyline_config.json` | `whisperer_barks` | Bark pool by speaker and trigger |
| `level_1.json` | `boss_sequence` | Ordered list of boss names |
| `level_1.json` | `world_events` | Distance-based spawn and NPC events |
