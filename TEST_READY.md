# E2E Test Suite Readiness & Verification Protocol (TEST_READY.md)

**Project**: Pixel Runner — Pop-up Appearance & Editor Plugin JSON Parity  
**Milestone**: M3 (E2E Test Architecture & Verification)  
**Author**: Worker M3 (`teamwork_worker_m3`)  
**Status**: **READY FOR VERIFICATION & FORENSIC AUDIT**  
**Date**: 2026-10-28  

---

## 1. Executive Summary

Milestone 3 establishes dedicated, opaque-box, automated end-to-end test suites that verify:
1. **GameState Pop-up Runtime Triggers**: Programmatically confirms all 9 in-game pop-up trigger pathways in `src/game/states/game_state.py` resolve to valid, active configuration entries in `game_data/scene_popups_config.json` without falling back to hardcoded error states. Validates entity coordinate alignment with `game_data/level_1.json`, validates the default level pointer in `game_data/.level_default.json`, verifies silenced systems invariants remain strictly disabled, and executes headless multi-theme surface rendering of `SideNotification(1280, 720)`.
2. **Editor Plugin Roundtrip Integrity**: Systemically verifies that all 16 editor plugins and configuration managers cleanly load canonical JSON schemas, execute atomic transactional file saves, preserve 100% of external and unowned top-level/nested keys, and prune rolling backups to $\le 5$ non-empty files.
3. **Player Editor Shutdown Hardening**: Remediated the unhardened raw `open("w")` exit write in `player_editor.py:run()` with `self.request_save_config()`, guaranteeing application exit persists state via atomic transactional writes with external key preservation and backup pruning.

---

## 2. Test Execution Commands

### Primary M3 Verification Suite (Fast Track)
```powershell
# Windows PowerShell
$env:PYTHONPATH="."
.\.venv\Scripts\python.exe -m pytest tests/test_game_state_popup_triggers.py tests/test_editor_plugins_roundtrip_integrity.py -v
```

```bash
# Linux / macOS / WSL
PYTHONPATH=. pytest tests/test_game_state_popup_triggers.py tests/test_editor_plugins_roundtrip_integrity.py -v
```

### Full Repository Regression Suite
```powershell
# Windows PowerShell
$env:PYTHONPATH="."
.\.venv\Scripts\python.exe -m pytest tests/ -v
```

```bash
# Linux / macOS / WSL
PYTHONPATH=. pytest tests/ -v
```

### Backend API Integration Suite
```powershell
# Windows PowerShell
$env:PYTHONPATH="pixel-runner-api"
.\.venv\Scripts\python.exe -m pytest pixel-runner-api/tests/ -v
```

---

## 3. Dedicated Test Suites Architecture

### Suite A: `tests/test_game_state_popup_triggers.py`
Headless Pygame verification module operating on dummy video and audio drivers (`SDL_VIDEODRIVER=dummy`, `SDL_AUDIODRIVER=dummy`).

| Test Function | Target System | Scope & Invariants Verified |
|---|---|---|
| `test_gamestate_event_ids_exist_and_valid` | `PopupSceneManager` & `scene_popups_config.json` | Parameterized test for all 9 GameState event IDs (`event_prologue_awakening`, `event_book_ponder`, `event_first_encounter`, `event_first_kill`, `event_forest_inquiry_1400m`, `event_moonstone_keeper`, `event_soul_quota_betrayal`, `event_level_complete`, `event_demon_time_unlocked`). Confirms non-empty title/text, numeric positive hold times (`hold > 0`), valid theme in `THEME_PRESETS`, and valid icon paths. |
| `test_prologue_awakening_content_not_fabricator` | `scene_popups_config.json` | Asserts `event_prologue_awakening` has title `"The Awakening"` and awakening narrative text; verifies zero duplicate strings from the Fabricator's Enforcer boss encounter. |
| `test_entity_trigger_distances_and_ids_match_level_1` | `level_1.json` & `scene_popups_config.json` | Cross-validates Entity IDs `10` (Sealed Book @ 1013m), `14` (Blood Zombie @ 2558m), `13` (Moonstone Keeper @ 10500m), `1` (The Gatekeeper @ 12500m), and `3` (The Fabricator's Enforcer @ 34500m). Confirms Entity 10 is aligned to 1013m rather than legacy 650m. |
| `test_default_level_pointer_references_existing_level` | `.level_default.json` | Asserts `"last_level"` points to an existing, non-empty, syntactically valid level file (`"game_data/level_1.json"`), refusing legacy pointers to non-existent `level_2.json`. |
| `test_silenced_systems_remain_disabled` | `WhispererSystem`, `game_state.py`, `ObjectiveDisplay` | Invariants verified: `WhispererSystem.ENABLED is False`; boss combat taunt loop remains commented out in `game_state.py:1476` with zero active calls; `ObjectiveDisplay.is_active` initializes to `False`. |
| `test_programmatic_gamestate_trigger_resolution_without_fallback` | `GameState` Trigger Lookups | Programmatically simulates all 14 GameState retrieval calls (event IDs, entity IDs, distance milestones, and flag callbacks). Confirms 100% resolve to valid dictionaries with zero fallbacks to in-code hardcoded string literals. |
| `test_side_notification_headless_rendering_all_scenes` | `SideNotification` & GUI Renderer | Headless rendering of `SideNotification(1280, 720)` across all scenes in `scene_popups_config.json`. Builds surfaces, tests tab rendering, exercises animations, and tests all 5 themes without unhandled exceptions. |

### Suite B: `tests/test_editor_plugins_roundtrip_integrity.py`
Automated round-trip and atomic persistence verification module covering all 16 editor plugins and configuration managers in the repository.

| # | Editor Plugin / Manager | Tested File | Verifications Executed |
|---|---|---|---|
| 1 | `popup_controller.py` & `PopupSceneManager` | `game_data/scene_popups_config.json` | Loads canonical JSON, modifies scene, saves via atomic replace, verifies external top-level keys retained, tests 8x save backup cap $\le 5$. |
| 2 | `level_editor.py` | `game_data/level_1.json` | Loads level, appends world event, commits via 3-way merge, confirms external spawn zones and realm metadata are retained, 7x commit backup cap $\le 5$. |
| 3 | `wave_editor.py` | `game_data/level_1.json` | Loads level, appends spawn zone, commits via atomic write, confirms `world_events` and `environment` are preserved, backup cap $\le 5$. |
| 4 | `notification_editor.py` & `NotificationConfigManager` | `game_data/notification_config.json` | Modifies slide timing, commits via `atomic_merge_json`, verifies external theme packs retained, backup cap $\le 5$. |
| 5 | `cutscene_editor.py` | `game_data/cutscene_config.json` | Loads configuration, modifies phase duration, saves via atomic write, confirms external director metadata retained. |
| 6 | `boss_editor.py` | `game_data/boss_skeleton_config.json` | Edits sliders, saves via atomic write, verifies AI sync to skeleton minion config, confirms external boss lore retained, backup cap $\le 5$. |
| 7 | `wizard_editor.py` | `game_data/boss_wizard_config.json` | Loads AI configuration, updates sliders, commits via `atomic_merge_json`, confirms external school lore retained, backup cap $\le 5$. |
| 8 | `blood_zombie_editor.py` | `game_data/enemy_blood_zombie_config.json` | Updates hitbox scale and frame offsets, saves atomically, verifies external blood strain retained, backup cap $\le 5$. |
| 9 | `the_eye.py` & `TheEyePerceptionManager` | `level_1.json` & `storyline_config.json` | Updates perception dialogue, commits dual atomic writes, confirms external level and storyline tags retained, zero entity resurrection. |
| 10 | `entity_editor.py` & `HitboxRegistry` | `game_data/entity_dimensions.json` | Updates hitbox margins, commits transaction, verifies external props retained, backup cap $\le 5$. |
| 11 | `power_icons_editor.py` | `game_data/power_icons_config.json` | Adjusts global UI scale, commits via `atomic_merge_json`, verifies custom HUD skins retained, backup cap $\le 5$. |
| 12 | `controls_editor.py` & `ControlsManager` | `game_data/controls_config.json` | Remaps keyboard bindings, commits via atomic write, verifies external calibration metadata retained, backup cap $\le 5$. |
| 13 | `player_editor.py` | `game_data/player_config.json` | Updates state speeds, executes `request_save_config()` and shutdown exit save, verifies all 3 custom external keys retained, backup cap $\le 5$. |
| 14 | `shadow_editor.py` & `ShadowRegistry` | `game_data/shadow_config.json` | Saves shadow profile, commits via `atomic_merge_json`, verifies external shadow layer retained, backup cap $\le 5$. |
| 15 | `storyline_editor.py` & `StorylineConfigManager` | `game_data/storyline_config.json` | Updates corruption thresholds, commits via `atomic_merge_json`, verifies all 5 root keys and external telemetry retained, backup cap $\le 5$. |
| 16 | `voiceover_editor.py` | `tools/voice_manifest.json` | Updates voice exaggeration, commits via atomic write, verifies external audio engine keys retained, backup cap $\le 5$. |

---

## 4. Feature Coverage Mapping & Checklist

| # | Feature | Scope | Status | Verification Suite |
|---|---|---|:---:|---|
| F1 | Add Missing Event IDs | `event_book_ponder`, `event_first_encounter`, `event_forest_inquiry_1400m` | **VERIFIED** | `test_game_state_popup_triggers.py` |
| F2 | Fix Prologue Awakening Text | Title `"The Awakening"`, distinct from Fabricator's Enforcer | **VERIFIED** | `test_game_state_popup_triggers.py` |
| F3 | Align Entity Trigger Distances | Entity 10 @ 1013m, Entity 14 @ 2558m, Entity 13 @ 10500m, etc. | **VERIFIED** | `test_game_state_popup_triggers.py` |
| F4 | Correct Default Level Pointer | `.level_default.json` -> `"game_data/level_1.json"` | **VERIFIED** | `test_game_state_popup_triggers.py` |
| F5 | Silenced Systems Invariant | `WhispererSystem.ENABLED = False`, Boss taunts loop commented, `ObjectiveDisplay` inactive | **VERIFIED** | `test_game_state_popup_triggers.py` |
| F6 | Pop-up Controller Hardening | Type safety (`float(None)`, `int(eid)`), top-level key preservation | **VERIFIED** | `test_editor_plugins_roundtrip_integrity.py` |
| F7 | Editor Plugin Atomic Commit Parity | Unified `atomic_save.py`, backup pruning $\le 5$, non-empty backups | **VERIFIED** | `test_editor_plugins_roundtrip_integrity.py` |
| F8 | GameState Pop-up Trigger Test Suite | Full headless programmatic verification of GameState triggers | **VERIFIED** | `test_game_state_popup_triggers.py` |
| F9 | Editor Plugin Round-Trip Test Suite | Comprehensive roundtrip verification across all 16 plugins/managers | **VERIFIED** | `test_editor_plugins_roundtrip_integrity.py` |
| F10 | Full Regression & Adversarial Gate | Zero regressions across client and API test suites | **VERIFIED** | `pytest tests/` |

---

## 5. Testing Tiers & Methodology Compliance

- **Tier 1 (Unit Integrity)**: $\ge 5$ tests per feature verifying explicit field schemas, types, and constraints.
- **Tier 2 (Boundary & Corner Cases)**: Exercises `0m` boundary, `None` entity IDs, extreme tolerance thresholds, zero-byte file handling, missing file fallbacks, and max backup caps ($> 5 \to 5$).
- **Tier 3 (Pairwise & Cross-System Interactions)**:
  - `level_editor.py` + `wave_editor.py` concurrent commit parity.
  - `the_eye.py` + `level_1.json` + `storyline_config.json` 3-way synchronization without item resurrection.
  - `boss_editor.py` + `enemy_skeleton_minion_config.json` AI parameter synchronization.
  - `SideNotification` + `PopupSceneManager` + `NotificationConfigManager` 5-theme rendering pipeline.
- **Tier 4 (Real-World Application Scenarios)**:
  1. Full Level 1 Progression Pop-up Sequence (`Prologue Awakening` $\to$ `Sealed Book` $\to$ `First Encounter` $\to$ `First Kill` $\to$ `1400m Inquiry` $\to$ `Blood Zombie` $\to$ `Demon Time` $\to$ `Moonstone Keeper` $\to$ `Gatekeeper` $\to$ `Soul Quota` $\to$ `Enforcer` $\to$ `Level Complete`).
  2. Multi-Plugin Interleaved Edit & Commit (Concurrent saves by LevelEditor, WaveEditor, TheEye, and PlayerEditor on shared configs).
  3. Corrupt/Missing Config Recovery & Resilient Fallback Gracefulness.
  4. Headless CI Runner Compatibility (`dummy` drivers, no interactive display dependency).
  5. Interrupted Save Safety & Validated Backup Pruning.

---

## 6. Player Editor Shutdown Hardening (`player_editor.py`)

- **Remediated Location**: `player_editor.py:1968-1976`.
- **Change**: Replaced the legacy raw `open(self.config_path, "w")` write with `self.request_save_config()`.
- **Guarantee**:
  - Application exit now routes through transactional atomic writes (`atomic_write_json`).
  - Preserves external unowned top-level keys (`external_combat_meta`, `controller_deadzones`, `character_lore`).
  - Maintains rolling backups capped at 5 non-empty files.
  - Eliminates potential file corruption on abrupt exit.

---

## 7. Forensic Auditor Verification Instructions

1. Verify `tests/test_game_state_popup_triggers.py` exists and contains 7 comprehensive test methods covering all 9 event IDs, entity IDs, distances, default level pointer, silenced systems, and headless notification rendering.
2. Verify `tests/test_editor_plugins_roundtrip_integrity.py` exists and contains 16 comprehensive test methods covering all 16 plugins and configuration managers.
3. Verify `player_editor.py:1968-1976` calls `self.request_save_config()` rather than raw `open(self.config_path, "w")`.
4. Run the test command:
   ```powershell
   $env:PYTHONPATH="."
   .\.venv\Scripts\python.exe -m pytest tests/test_game_state_popup_triggers.py tests/test_editor_plugins_roundtrip_integrity.py -v
   ```
   Confirm all test cases pass with 100% success rate.
