# Project: Pixel-Runner Pop-up Appearance & Editor Plugin JSON Parity

## Architecture
- **Runtime Pop-up System**:
  - `src/game/states/game_state.py`: Manages the main game loop, level distance, and queries `PopupSceneManager` for pop-up notifications.
  - `src/game/systems/popup_scene_manager.py`: Singleton manager providing O(1) indexed lookups by event ID, entity ID, flag, or distance. Persists data to `game_data/scene_popups_config.json`.
  - `src/game/ui/hud_overlay.py` & `src/game/ui/side_notification.py`: Renders visual notifications with theme presets (`gothic_gold`, `blood_bone`, `arcane_void`, `grimoire_leather`, `clean_minimalist`).
- **Configuration & Game Data**:
  - `game_data/scene_popups_config.json`: Canonical registry of all Level 1 scene pop-ups.
  - `game_data/level_1.json`: Canonical level definition including `world_events`, `spawn_zones`, and `environment`.
  - `game_data/.level_default.json`: Default level pointer for editor and engine sessions.
- **Editor Plugins & Tools**:
  - `popup_controller.py`: Visual GUI for scene pop-up notifications and in-game entity linking.
  - `level_editor.py`: Multi-stage level spawner, prop placement, and event editor.
  - `notification_editor.py`: Pop-up layout and theme timing editor.
  - `cutscene_editor.py`, `boss_editor.py`, `wizard_editor.py`, `blood_zombie_editor.py`, `the_eye.py`, `wave_editor.py`, `entity_editor.py`, `power_icons_editor.py`, `controls_editor.py`, `player_editor.py`, `shadow_editor.py`, `storyline_editor.py`, `voiceover_editor.py`.
- **Atomic Persistence Layer**:
  - `src/game/utils/atomic_save.py`: Canonical transactional atomic save engine (`atomic_write_json`, `atomic_merge_json`, `create_validated_backup`, `prune_backups`).
- **Verification Layer**:
  - `tests/`: 427+ existing tests with headless Pygame fixtures (`tests/conftest.py`).
  - `tests/test_game_state_popup_triggers.py`: New headless verification for GameState pop-up triggers and silenced systems.
  - `tests/test_editor_plugins_roundtrip_integrity.py`: New round-trip integrity test suite for all editor plugins.

---

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| F1 | Add Missing Event IDs | Add `event_book_ponder`, `event_first_encounter`, and `event_forest_inquiry_1400m` to `game_data/scene_popups_config.json`. | M1 | Survey (Explorer 1 & 3) |
| F2 | Fix Prologue Awakening Text | Update `event_prologue_awakening` title to `"The Awakening"` and text to prologue narrative rather than Fabricator's Enforcer. | M1 | Survey (Explorer 1 & 3) |
| F3 | Align Entity Trigger Distances | Correct Entity 10 (Sealed Book) distance from 650m to 1013m in `game_data/scene_popups_config.json` to match `game_data/level_1.json`. | M1 | Survey (Explorer 1 & 2) |
| F4 | Correct Default Level Pointer | Update `game_data/.level_default.json` to point to valid existing level (`"game_data/level_1.json"`). | M1 | Survey (Explorer 1 & 3) |
| F5 | Silenced Systems Preservation | Ensure `WhispererSystem.ENABLED = False`, boss combat taunts remain commented out, and `ObjectiveDisplay`/`ItemLoreSystem` remain inactive. | M1 | Survey (Explorer 1 & 3) |
| F6 | Pop-up Controller & Manager Hardening | Fix `float(None)` TypeErrors, unhandled `int(eid)`, distance subtraction `NoneType`, and preserve external top-level keys in `save_config()`. | M2 | Survey (Explorer 2) |
| F7 | Editor Plugin Atomic Commit Parity | Harmonize `boss_editor.py`, `level_editor.py`, `wave_editor.py`, and `player_editor.py` to use `atomic_save.py` and prune backups without field loss. | M2 | Survey (Explorer 2) |
| F8 | GameState Pop-up Trigger Test Suite | Implement `tests/test_game_state_popup_triggers.py` verifying all 9 triggers resolve to valid configs without fallbacks. | M3 | Survey (Explorer 3) |
| F9 | Editor Plugin Round-Trip Test Suite | Implement `tests/test_editor_plugins_roundtrip_integrity.py` verifying all editor plugins load, parse, and round-trip game data cleanly. | M3 | Survey (Explorer 3) |
| F10 | Full Regression & Adversarial Gate | Ensure 100% pass rate across the full test suite (`PYTHONPATH=. pytest`) and perform adversarial verification. | M4 | Survey (Explorer 3) |

---

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | Pop-up Config & Runtime Alignment | Fix `scene_popups_config.json`, `.level_default.json`, and verify silenced systems invariants (F1-F5). | None | DONE |
| M2 | Editor Plugin Data Parity & Hardening | Harden `popup_controller.py`, `PopupSceneManager`, and harmonize atomic saves across `boss_editor.py`, `level_editor.py`, `wave_editor.py`, `player_editor.py` (F6-F7). | M1 | DONE |
| M3 | E2E Testing Track (Automated Verifiers) | Implement `test_game_state_popup_triggers.py` and `test_editor_plugins_roundtrip_integrity.py` (F8-F9). | M1, M2 | IN_PROGRESS |
| M4 | Final Milestone (100% E2E Pass & Audit) | Run full test suite, verify zero regressions, adversarial coverage hardening, and forensic audit (F10). | M1, M2, M3 | BLOCKED: Forensic Audit Failed (Integrity Violation) |

---

## Interface Contracts

### `PopupSceneManager` ↔ `GameState`
- `get_popup(scene_id: str) -> dict | None`: Must return a valid dictionary containing `"title": str`, `"text": str`, `"theme": str`, `"icon": str`, `"hold": float`, `"enabled": bool` for all 9 referenced IDs.
- `get_popup_by_entity(entity_id: int) -> dict | None`: Must return the corresponding scene dictionary for entity IDs `10`, `14`, `13`, `1`, `3`.
- `get_popup_by_flag(flag: str) -> dict | None`: Must return matching scene dictionary for flag triggers (`"first_kill"`, `"soul_quota"`, `"book_ponder"`).

### Editor Plugins ↔ `src/game/utils/atomic_save.py`
- All configuration file writes must invoke `atomic_write_json(file_path, data, indent=2, backup=True)` or `atomic_merge_json(file_path, updates, indent=2, backup=True)`.
- Direct `open(..., "w")` or raw `shutil.copy2` to unpruned backup directories is prohibited.
- Backup retention is capped at 5 files via `prune_backups(file_path, max_backups=5)`.

---

## Code Layout
- `game_data/`:
  - `scene_popups_config.json`: Owned by M1
  - `.level_default.json`: Owned by M1
  - `level_1.json`: Read-only reference for M1/M2/M3
- `src/game/systems/`:
  - `popup_scene_manager.py`: Owned by M2
  - `whisperer_system.py`: Read-only (invariant: `ENABLED = False`)
- `popup_controller.py`: Owned by M2
- `boss_editor.py`: Owned by M2
- `level_editor.py`: Owned by M2
- `wave_editor.py`: Owned by M2
- `player_editor.py`: Owned by M2
- `tests/`:
  - `test_game_state_popup_triggers.py`: Owned by M3
  - `test_editor_plugins_roundtrip_integrity.py`: Owned by M3
  - Existing tests: Read-only verification targets
