---
name: pixel-runner-architecture
description: Use when working in the Pixel-Runner codebase and needing to understand or navigate its architecture — covers the V3X engine patterns, entity system, state machine, event bus, config loading, and game loop.
---

# Pixel-Runner Architecture

Reference this skill whenever you need to understand how the game is structured, where to find a system, or how the pieces connect before making changes.

---

## Tech Stack

- **Language**: Python 3.10+
- **Renderer**: Pygame
- **Engine**: V3X Zulfiqar-Gideon — installed as a local package from `v3x-zulfiqar-gideon/`. Import as `v3x_zulfiqar_gideon`.
- **Rule**: never modify files inside `v3x-zulfiqar-gideon/`. All game changes live inside `Pixel-Runner/`.

---

## State Machine

- Class: `StateManager` in `v3x_zulfiqar_gideon/state_machine.py`
- Stack-based. Methods: `push(state)`, `pop()`, `set(state)` (replaces the whole stack).
- Every screen is a `State` subclass with `update(dt)`, `draw(surface)`, `on_enter()`, `on_exit()`.
- Game screen states live in `src/game/states/`.
- To push a modal (e.g. a relic reveal, a pause menu): `state_manager.push(MyState(...))`. It pops itself when done.

---

## Entity System (ECS-lite)

- `Entity` — Pygame sprite + component registry. Base for all game objects.
- `Actor` — extends `Entity` with a priority FSM, animation controller, and combat support.
- Entity files: `src/game/entities/`
- Engine ECS primitives: `v3x_zulfiqar_gideon/ecs.py`
- For enemies, subclass `BaseEnemy` (`src/game/entities/base_enemy.py`).
- For NPCs, subclass `GenericNPC` (`src/game/entities/generic_npc.py`).

---

## Event Bus

- Class: `EventBus` in `v3x_zulfiqar_gideon/event_bus.py`
- Pub/sub with weak references — subscribers are not kept alive by the bus.
- **Subscribe**: `bus.subscribe(EventType, callback)`
- **Emit**: `bus.emit(EventInstance)`
- **Key engine events**: `EntityDied`, `DamageDealt`, `DamageReceived`, `StateChanged`, `EntitySpawned`
- **Custom game events** (not in engine): define new event dataclasses in `src/game/events/custom_events.py` and import them where needed. Never add custom events to engine files.

---

## World Progression

- Class: `WorldEventManager` in `v3x_zulfiqar_gideon/world.py`
- Distance-based: events fire at specific `world_distance` values (pixels scrolled).
- The game loop in `GameState.update(dt)` advances `world_distance` each frame.
- World event data lives in `game_data/level_1.json` under the `world_events` array.
- Event types supported: `"enemy"`, `"boss"`, `"npc"`, `"ambient"`.

---

## Config Loading

- Service: `src/game/services/config_client.py` — `ConfigClient`
- Loads from `game_data/*.json`. Hot-reload supported during development.
- Access pattern: `config_client.get("entity_name")` returns the parsed dict for that JSON file.
- File mapping:
  - Player → `game_data/player_config.json`
  - Bosses → `game_data/boss_*_config.json`
  - Enemies → `game_data/enemy_*_config.json`
  - Narrative/story → `game_data/storyline_config.json`
  - Level events → `game_data/level_1.json`
  - Entity collision boxes → `game_data/entity_dimensions.json`

---

## Game Loop — `GameState`

- File: `src/game/states/game_state.py`
- `GameState` is the primary gameplay state (not a menu or cutscene).
- All systems are instantiated in `__init__` and ticked in `update(dt)` / rendered in `draw(surface)`.
- Systems wired here: wave manager, combat system, HUD, cutscene overlay, corruption manager, relic manager, whisperer system, boss encounter manager, ending manager.
- To add a new system: instantiate it in `__init__`, call its `update(dt)` in `update`, call its `draw(surface)` in `draw` if it renders anything.

---

## Combat System

- File: `src/game/systems/combat_system.py`
- Decoupled from entities — hit detection runs in the system, not in entity `update()`.
- On hit: emits `DamageDealt` and `DamageReceived` events. Other systems react via the event bus.

---

## Key Directory Map

| Directory | Contents |
|---|---|
| `src/game/states/` | All `State` subclasses (screens, modals, endings) |
| `src/game/entities/` | Entity classes: player, enemies, bosses, NPCs |
| `src/game/systems/` | Standalone systems: combat, wave, corruption, relic, whisperer, ending |
| `src/game/ui/` | HUD components, overlays, dialogue renderers |
| `src/game/services/` | Config client, save manager, telemetry, watsonx client |
| `src/game/ai/` | Enemy AI behaviours |
| `src/game/effects/` | Particle effects, visual feedback |
| `src/game/events/` | Custom event dataclasses (do not edit engine events) |
| `game_data/` | All JSON config files — single source of truth for story and entity data |
| `assets/graphics/` | Sprite sheets, one subfolder per entity, one subfolder per animation state |
