---
name: pixel-runner-add-boss
description: Use when adding a new boss to Pixel-Runner — covers entity class, encounter dialogue config, relic drop assignment, corruption delta, and ending system impact.
---

# Adding a New Boss to Pixel-Runner

A boss is a special enemy with encounter dialogue, a relic drop, corruption impact, and optionally ending-system influence. Follow all steps below.

> **Prerequisite**: complete the `pixel-runner-add-entity` skill steps first (config JSON, entity class, sprite assets, entity dimensions). Return here after Step 3 of that skill (registering in `boss_manager.py`).

---

## Step 1 — Complete the `pixel-runner-add-entity` Checklist

Run all 7 steps of `pixel-runner-add-entity`. When registering the entity (Step 3 of that skill), add it to `_BOSS_CLASS_MAP` in `src/game/entities/boss_manager.py`.

---

## Step 2 — Add the Boss to the Level Sequence

In `game_data/level_1.json`, add the boss name to the `boss_sequence` array at the correct position. Order is strictly enforced — `BossEncounterManager` spawns bosses in this sequence:

```json
"boss_sequence": [
  "GreenMonster",
  "Gatekeeper",
  "BloodZombie",
  "FireWizard",
  "DarkRonin",
  "NewBossName"
]
```

Placement matters for narrative flow. Early slots = Andras soldiers. Mid slots = corrupted souls. Late slots = corrupted paragons.

---

## Step 3 — Add Boss Dialogue Config

In `game_data/storyline_config.json`, add an entry under `boss_dialogue`:

```json
"NewBossName": {
  "role": "soldier",
  "pre_fight": [
    "Line one spoken before the fight begins.",
    "Line two — optional second line."
  ],
  "death_line": "Final words spoken on defeat.",
  "corruption_variants": {
    "low":  "Alternate pre-fight line when player corruption is ≤33.",
    "mid":  "Alternate pre-fight line when player corruption is 34–66.",
    "high": "Alternate pre-fight line when player corruption is ≥67."
  }
}
```

- `role` options: `"soldier"` (Andras agent, aggressive), `"corrupted_soul"` (shows pain, hints backstory), `"corrupted_paragon"` (fallen hero, references player's corruption).
- `BossEncounterManager` selects the `corruption_variants` line automatically based on `CorruptionManager` thresholds at the moment of encounter. No code change needed.

### Optional flags in the boss dialogue entry

| Flag | Effect |
|---|---|
| `"is_final": true` | Marks this as the final boss. `EndingManager` checks this flag to trigger the ending sequence after defeat. |
| `"watsonx_taunt": true` | `WhispererSystem` will call `WatsonxDialogueClient` for a dynamically generated Andras taunt on this boss's spawn bark instead of using a static config line. Ensure a static fallback line exists in `pre_fight`. |

---

## Step 4 — Add the Relic Drop

In `game_data/storyline_config.json`, add an entry under `relic_boss_map`:

```json
"NewBossName": [
  { "relic_id": "relic_name",         "corruption_delta": 10 },
  { "relic_id": "second_relic_name",  "corruption_delta": -5 }
]
```

- A boss can drop 1 or 2 relics. If 2, `RelicManager` emits them 2 seconds apart.
- `corruption_delta` is applied to `CorruptionManager` when the player collects the relic (positive = darker, negative = lighter).
- `relic_id` must match a key in the `relics` block of `storyline_config.json`. Add a new relic entry there if needed:

```json
"relics": {
  "relic_name": {
    "display_name": "Human-Readable Name",
    "lore":         "One to three sentences of lore text shown in the relic reveal cutscene.",
    "icon":         "assets/graphics/ui/relics/relic_name.png"
  }
}
```

---

## Step 5 — Verify Automatic Wiring

No further code changes are required once the JSON is correct. Confirm the following:

- `BossEncounterManager` (`src/game/systems/boss_encounter_manager.py`) reads `boss_dialogue` and `relic_boss_map` automatically on boss spawn.
- `RelicManager` (`src/game/systems/relic_manager.py`) listens for the `RelicDropped` event and calls `CorruptionManager.add(delta)`.
- `EndingManager` (`src/game/systems/ending_manager.py`) reads `is_final` to know when to trigger the ending after defeat.

If any of these systems does not exist yet, check the sub-task status in `game-overhaul-plan.md` — they may need to be implemented first.

---

## Step 6 — Final Boss Specifics

If the boss is the final boss (`"is_final": true`):

1. It must be the last entry in `boss_sequence` in `level_1.json`.
2. `boss_manager.py` emits `FinalBossDefeated` (a custom event) on its death.
3. `EndingManager.resolve()` is called in `GameState` when `FinalBossDefeated` is received.
4. The ending type is determined by `CorruptionManager.value` at that moment:
   - `DARK` (≥75), `LIGHT` (≤25), `AMBIGUOUS` (26–74).

---

## Boss Role Reference

| Role | Narrative Tone | Suggested Corruption Delta (relic) |
|---|---|---|
| `soldier` | Aggressive, no remorse, short barks | +8 to +12 |
| `corrupted_soul` | Shows pain, hints at backstory | +6 to +15 |
| `corrupted_paragon` | Fallen hero, references player's corruption | +15 to −20 (can be redemptive) |
