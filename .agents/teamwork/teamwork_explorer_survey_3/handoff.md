# Investigation Report: Test & Verification Architecture (Explorer 3)

## 1. Observation

### 1.1 Existing Test Infrastructure & Environment Configuration
- **Root Configuration (`pytest.ini`)**:
  ```ini
  [pytest]
  testpaths = tests
  norecursedirs = scratch venv .venv .git
  ```
- **Global Headless Pygame Fixtures (`tests/conftest.py:5-41`)**:
  ```python
  os.environ["SDL_VIDEODRIVER"] = "dummy"
  os.environ["SDL_AUDIODRIVER"] = "dummy"
  os.environ["DISABLE_TELEMETRY"] = "1"

  @pytest.fixture(scope="session", autouse=True)
  def init_headless_pygame():
      pg.init()
      pg.font.init()
      try:
          pg.mixer.init()
      except Exception:
          pass
      screen = pg.display.set_mode((1280, 720))
      yield
      pg.quit()

  @pytest.fixture(autouse=True)
  def reset_asset_manager_font_cache():
      try:
          from v3x_zulfiqar_gideon import AssetManager
          AssetManager.clear()
      except Exception:
          pass
      if not pg.font.get_init():
          try:
              pg.font.init()
          except Exception:
              pass
      yield
      try:
          from v3x_zulfiqar_gideon import AssetManager
          AssetManager.clear()
      except Exception:
          pass
  ```
- **Virtual Environment & Test Execution**:
  - Python runtime: Python 3.14.7 (`C:\Python314\python.exe` / `.venv\Scripts\python.exe`).
  - Pytest version: `pytest 9.1.1`, `pluggy-1.6.0`, with plugins `anyio-4.15.1`, `asyncio-1.4.0`.
  - Command to run all tests:
    - Windows PowerShell: `$env:PYTHONPATH="."; .\.venv\Scripts\python.exe -m pytest`
    - Unix/Bash: `PYTHONPATH=. pytest`
- **Backend API Integration Tests (`pixel-runner-api/tests/`)**:
  - Two integration test suites: `test_ai_director_api.py` and `test_telemetry_api.py`.
  - Both prepend `pixel-runner-api` to `sys.path` (`sys.path.insert(0, os.path.abspath("pixel-runner-api"))`).
  - Use `fastapi.testclient.TestClient(app)` to test endpoints (`/health`, `/telemetry/session`, `/telemetry/events`, `/telemetry/frames`, `/telemetry/ai-director`), testing authorization headers (`X-API-Write-Secret`), Pydantic validation, array caps, and Moonshot Kimi fallback directives.

### 1.2 Inspection of Existing Plugin and Pop-up Test Files
1. **`tests/test_popup_scene_manager.py` (6 tests)**:
   - Covers `PopupSceneManager`: loading, lookups by ID/entity/flag/distance, muting/toggling, text updates, `set_all_scenes`, atomic persistence to temp files, and `SideNotification` multi-theme rendering (`gothic_gold`, `blood_bone`, `arcane_void`, `grimoire_leather`, `clean_minimalist`).
   - **Current Failing Test**: `test_popup_scene_manager_load_and_lookup` failed on line 34:
     ```
     FAILED tests/test_popup_scene_manager.py::test_popup_scene_manager_load_and_lookup
     AssertionError: assert 'The Fabricator\'s Enforcer' in ('The Awakening', 'The Dark Forest')
     ```
     5 passed, 1 failed in 2.55s.
2. **`tests/test_popup_controller.py` (17 tests)**:
   - Full GUI testing in headless mode: `PopupControllerApp`, timeline scrolling, search/category filtering (`ALL`, `DISTANCE`, `ENTITY`), modal workflows (`_open_add_modal`, `_delete_current_popup`), theme toggling, duration and buffer edits, responsive 1080p resize (`width=1920, height=1080`), button hitboxes, `IconCatalog` discovery (500+ icons), and icon gallery modal.
   - All 17 tests passed in 2.60s.
3. **`tests/test_all_plugins_cia_integrity.py` (8 tests)**:
   - Covers atomic save engine in `src/game/utils/atomic_save.py` (`atomic_write_json`, `atomic_merge_json`, `create_validated_backup`, `prune_backups`).
   - Verifies rolling validated backups (max 5, no 0-byte backups), non-clobbering disk merging, refusal of corrupt files.
   - Tests atomic commits for: `NotificationConfigManager`, `StorylineConfigManager`, `HitboxRegistry`, `ShadowRegistry`, `ControlsManager`, and `save_config_and_lock`.
4. **`tests/test_plugin_commit_integrity.py` (7 tests)**:
   - Multi-plugin concurrent commit integrity:
     - `test_the_eye_save_preserves_external_level_modifications`: verifies deleted events are NOT resurrected and external environment props are preserved when saving perception dialogue.
     - `test_level_editor_commit_preserves_wave_editor_spawn_zones`: LevelEditor commit preserves `spawn_zones`.
     - `test_wave_editor_commit_preserves_world_events_and_props`: WaveEditor commit preserves `world_events` and `environment` props.
     - `test_atomic_save_never_creates_empty_backups_and_prunes`.
     - `test_rollback_isolation_does_not_clobber_disk`.
     - `test_consecutive_multi_plugin_interleaved_saves`: 3-way interleaved edit and save between LevelEditor, WaveEditor, and TheEye.
     - `test_the_eye_close_and_reopen_persists_all_node_categories`: 100% data retention across close and reopen.

### 1.3 GameState Pop-up Trigger Audit (`src/game/states/game_state.py`)
Direct code inspection of `src/game/states/game_state.py` identified every pop-up retrieval call:
1. Line 966: `self.popup_scene_manager.get_popup("event_prologue_awakening")`
   - Trigger: Game start / prologue entry.
   - Fallback hardcoded text: `"The catacombs stir. Death has not taken you, but the dark beckons. Advance through the shadows."`, title `"The Awakening"`.
2. Line 899: `self.popup_scene_manager.get_popup("event_soul_quota_betrayal")`
   - Trigger: Soul quota reached (10,000 souls).
   - Fallback hardcoded text: `"Ten thousand souls bound by your hand!..."`, title `"The Fabricator's Betrayal"`.
3. Line 919 & 2127: `self.popup_scene_manager.get_popup("event_book_ponder")`
   - Trigger 1 (line 919): WorldManager ambient lore callback.
   - Trigger 2 (line 2127): Buff data event `book_ponder` (after Sealed Book ritual).
   - Fallback hardcoded text: `"What does this demon want with me...?"`, title `"The Runner Wonders"`.
   - **Discrepancy: MISSING from `game_data/scene_popups_config.json`!**
4. Line 1070 & 1112: `self.popup_scene_manager.get_popup_by_entity(eid)`
   - Trigger: Player proximity interaction with NPC or boss entity.
   - Entity IDs in `game_data/level_1.json`:
     - Entity 10: "The Sealed Book" at distance `1013` (in `scene_popups_config.json`, distance was erroneously `650`).
     - Entity 14: "Blood Zombie" at distance `2558`.
     - Entity 13: "The Moonstone Keeper" at distance `10500`.
     - Entity 1: "The Gatekeeper" at distance `12500`.
     - Entity 3: "The Fabricator's Enforcer" at distance `34500`.
5. Line 1575: `self.popup_scene_manager.get_popup("event_level_complete")`
   - Trigger: Level end distance reached (36,000m).
6. Line 1646: `self.popup_scene_manager.get_popup("event_demon_time_unlocked")`
   - Trigger: The EYE relic collected / Demon Time unlocked.
7. Line 1677: `self.popup_scene_manager.get_popup("event_forest_inquiry_1400m")`
   - Trigger: Distance milestone `world_distance >= 1400`.
   - Fallback hardcoded text: `"What in God's name is this forest...?"`, title `"The Runner Questions"`.
   - **Discrepancy: MISSING from `game_data/scene_popups_config.json`!**
8. Line 1835: `self.popup_scene_manager.get_popup_by_flag(p_flag)`
   - Trigger: Flag notification callback (`first_kill`).
9. Line 1840: `self.popup_scene_manager.get_popup("event_first_encounter")`
   - Trigger: Flag notification callback when text/title mentions "encounter".
   - **Discrepancy: MISSING from `game_data/scene_popups_config.json`!**
10. Line 1842: `self.popup_scene_manager.get_popup("event_first_kill")`
    - Trigger: Flag notification callback when text/title mentions "kill" or "blood".

### 1.4 Level Configuration Discrepancies
- `game_data/.level_default.json` contains:
  ```json
  {"last_level": "game_data/level_2.json"}
  ```
  `game_data/level_2.json` does NOT exist in the repository. It must reference `"game_data/level_1.json"`.
- `game_data/scene_popups_config.json:6-18`:
  `event_prologue_awakening` has title `"The Fabricator's Enforcer"` and text `"Clanking gears of malice screech in the dark..."`, which is an erroneous duplicate of `event_fabricators_enforcer` instead of the prologue awakening.

---

## 2. Logic Chain

1. **Step 1: Failure Reproduction & Root Cause Identification**:
   - Running `pytest tests/test_popup_scene_manager.py` yielded an immediate failure in `test_popup_scene_manager_load_and_lookup`.
   - Line 34 expected `prologue["title"] in ("The Awakening", "The Dark Forest")`.
   - Inspection of `game_data/scene_popups_config.json:11` confirmed `title` is set to `"The Fabricator's Enforcer"`.
   - This directly confirms requirement R1 and acceptance criteria line 35.

2. **Step 2: Fallback State Activation Due to Missing Keys**:
   - Tracing `src/game/states/game_state.py` showed explicit `get_popup(...)` lookups for `"event_book_ponder"` (lines 919, 2127), `"event_forest_inquiry_1400m"` (line 1677), and `"event_first_encounter"` (line 1840).
   - In all three locations, `GameState` has `else:` branches that fall back to hardcoded in-code string literals when `get_popup` returns `None`.
   - Inspection of `game_data/scene_popups_config.json` confirmed none of these 3 keys are defined. Thus, during normal gameplay, the game is forced into fallback state, violating the requirement that all pop-up triggers resolve to valid config entries without falling back to hardcoded error states.

3. **Step 3: Distance and Coordinate Misalignment**:
   - In `game_data/level_1.json:561`, entity 10 ("The Sealed Book") is located at distance `1013`.
   - In `game_data/scene_popups_config.json:22`, `event_sealed_book_encounter` specifies distance `650`.
   - When the player interacts with entity 10 at 1013m, `get_popup_by_entity(10)` matches by entity ID, but any distance-based lookup at 1013m misses the scene, creating data inconsistency between level definitions and popup triggers.

4. **Step 4: Audit of Plugin Save Workflows & Gaps**:
   - Analysis of all editor plugins revealed two categories:
     - *Compliant Plugins* using `atomic_save.py` (`atomic_merge_json` / `atomic_write_json`): `popup_controller.py` (via `PopupSceneManager`), `notification_editor.py` (via `NotificationConfigManager`), `cutscene_editor.py`, `storyline_editor.py` (via `StorylineConfigManager`), `wizard_editor.py`, `blood_zombie_editor.py`, `power_icons_editor.py`, `voiceover_editor.py`, `controls_editor.py` (via `ControlsManager`), `entity_editor.py` (via `HitboxRegistry`), `shadow_editor.py` (via `ShadowRegistry`), `audio_mixer_editor.py` (via `audio_lock`), `the_eye.py` (via `TheEyePerceptionManager`), `level_editor.py` (custom atomic tmp + replace), `wave_editor.py` (custom atomic tmp + replace).
     - *Non-Atomic Plugins*: `boss_editor.py` (lines 1002-1003) and `player_editor.py` (line 1970) directly use `open(..., "w")` with `json.dump`, bypassing atomic replace and risk corrupting files if interrupted.
   - Furthermore, there was no automated test verifying that all 16 editor plugins successfully load their real canonical JSON files from `game_data/` and round-trip without dropping external keys.

5. **Step 5: Architectural Formulation of Automated Verification Tests**:
   - To satisfy Requirement R3, two dedicated test suites must be created in `tests/`:
     1. `tests/test_editor_plugins_roundtrip_integrity.py`:
        - Headless execution.
        - Tests load, parse, and round-trip across all plugins.
        - Verifies external key retention, schema compliance, backup pruning, and atomic commit semantics.
     2. `tests/test_game_state_popup_triggers.py`:
        - Headless execution using `tests/conftest.py` dummy drivers.
        - Programmatic audit of all 9 event IDs, entity triggers (entities 10, 14, 13, 1, 3), flag triggers (`first_kill`), and `.level_default.json` pointer validity.
        - Asserts zero fallbacks to hardcoded error states.
        - Asserts silenced systems (`WhispererSystem.ENABLED = False`, inactive boss combat taunts, inactive ObjectiveDisplay) remain disabled.

---

## 3. Caveats
- No modifications were made to source files or config files during this investigation (strictly read-only).
- During test execution on Windows, running PowerShell commands that invoke `.venv\Scripts\python.exe` directly works synchronously; permission prompts should not be bypassed if denied.
- `pixel-runner-api/tests` are separated by `pytest.ini` (`testpaths = tests`), so running `pytest` from the root directory runs game tests in `tests/`. API tests are run with `PYTHONPATH=pixel-runner-api pytest pixel-runner-api/tests`.

---

## 4. Conclusion & Proposed Test Specifications

### 4.1 Required Test Suite 1: `tests/test_game_state_popup_triggers.py`
A dedicated headless test suite confirming that:
1. **Event ID Completeness**: Every scene ID referenced in `GameState` exists in `game_data/scene_popups_config.json`:
   - `event_prologue_awakening`
   - `event_book_ponder`
   - `event_first_encounter`
   - `event_first_kill`
   - `event_forest_inquiry_1400m`
   - `event_moonstone_keeper`
   - `event_soul_quota_betrayal`
   - `event_level_complete`
   - `event_demon_time_unlocked`
2. **Schema & Theme Compliance**: Each popup has non-empty `title`, `text`, valid `theme` in `THEME_PRESETS`, positive `hold`, boolean `enabled`, and valid `trigger_type` (`"distance"`, `"entity"`, `"flag"`).
3. **Prologue Awakening Identity**: `event_prologue_awakening` title is `"The Awakening"` (or contains `"Awakening"`), not `"The Fabricator's Enforcer"`.
4. **Entity ID and Distance Parity**:
   - Entity 10: distance `1013` (matches Sealed Book in `game_data/level_1.json`).
   - Entity 14: distance `2558` (Blood Zombie).
   - Entity 13: distance `10500` (Moonstone Keeper).
   - Entity 1: distance `12500` (The Gatekeeper).
   - Entity 3: distance `34500` (The Fabricator's Enforcer).
5. **Headless Resolution & Surface Building**:
   - Calling `PopupSceneManager.get_popup(id)` for all IDs returns a valid dict (never `None`).
   - Calling `SideNotification(1280, 720).show(...)` with the retrieved configuration populates `_current_item` and successfully calls `_build_tab_surface()` headlessly without raising any exceptions.
6. **Default Level Integrity**: `game_data/.level_default.json` points to an existing file (`"game_data/level_1.json"`).
7. **Silenced Systems Verification**:
   - `WhispererSystem.ENABLED is False`
   - Periodic boss combat taunt update remains disabled/commented in `GameState`
   - `objective_display.is_active` remains false on start.

### 4.2 Required Test Suite 2: `tests/test_editor_plugins_roundtrip_integrity.py`
A dedicated automated test suite confirming that all editor plugins can load, parse, and round-trip game data without loss or corruption:
1. **`popup_controller.py` & `PopupSceneManager`**:
   - Loads `game_data/scene_popups_config.json`.
   - Modifies a scene in memory, saves via `save_config(target_path=tmp)`, reloads, asserts 100% field parity.
2. **`level_editor.py`**:
   - Loads `game_data/level_1.json`.
   - Modifies environment prop, commits, reloads, asserts `spawn_zones`, `world_events`, `bat_spawn`, `boss_sequence` remain intact.
3. **`wave_editor.py`**:
   - Loads `game_data/level_1.json`.
   - Appends spawn zone, commits, reloads, asserts `world_events` and `environment` are preserved.
4. **`notification_editor.py` & `NotificationConfigManager`**:
   - Loads `game_data/notification_config.json`.
   - Modifies timing and layout parameters, saves via `atomic_merge_json`, asserts schema validity.
5. **`cutscene_editor.py`**:
   - Loads `game_data/cutscene_config.json`, saves via `save_config`, asserts round-trip parity.
6. **`storyline_editor.py` & `StorylineConfigManager`**:
   - Loads `game_data/storyline_config.json`, modifies relic / dialogue, saves via `atomic_merge_json`, asserts all root keys (`boss_dialogue`, `enemy_taunts`, `relics`, `narrative_nodes`, `boss_hierarchy`) remain intact.
7. **`voiceover_editor.py`**:
   - Loads `game_data/voice_manifest.json`, saves via `atomic_write_json`, asserts manifest integrity.
8. **`power_icons_editor.py`**:
   - Loads `game_data/power_icons_config.json`, saves via `atomic_merge_json`, asserts icons preservation.
9. **`blood_zombie_editor.py`**:
   - Loads `game_data/enemy_blood_zombie_config.json`, saves via `atomic_merge_json`, asserts frame offsets and hitbox scale sync.
10. **`wizard_editor.py`**:
    - Loads `game_data/boss_wizard_config.json`, saves via `atomic_merge_json`, asserts spell and teleport configs preserved.
11. **`boss_editor.py`**:
    - Loads `game_data/boss_wizard_config.json`, `game_data/boss_skeleton_config.json`, `game_data/enemy_green_monster_config.json`, and `game_data/enemy_skeleton_minion_config.json`, verifying safe JSON parsing and serialization.
12. **`controls_editor.py` & `ControlsManager`**:
    - Loads `game_data/controls_config.json`, modifies keybinding, saves via `atomic_write_json`, asserts bindings preserved.
13. **`entity_editor.py` & `HitboxRegistry`**:
    - Loads `game_data/entity_dimensions.json`, commits hitbox margins, asserts all entities preserved.
14. **`shadow_editor.py` & `ShadowRegistry`**:
    - Loads `game_data/shadow_config.json`, saves profile via `atomic_merge_json`, asserts integrity.
15. **`audio_mixer_editor.py` & `audio_lock`**:
    - Loads `game_data/audio_config.json`, saves and creates lockfile via `save_config_and_lock`, verifies lockfile and json content.
16. **`the_eye.py` & `TheEyePerceptionManager`**:
    - Loads `level_1.json` and `storyline_config.json`, saves perception and events, asserts zero item resurrection and 100% data retention.

---

## 5. Verification Method

### 5.1 Test Execution Commands
- Run all unit and integration tests:
  ```powershell
  $env:PYTHONPATH="."; .\.venv\Scripts\python.exe -m pytest
  ```
- Run pop-up and plugin tests specifically:
  ```powershell
  $env:PYTHONPATH="."; .\.venv\Scripts\python.exe -m pytest tests/test_popup_scene_manager.py tests/test_popup_controller.py tests/test_all_plugins_cia_integrity.py tests/test_plugin_commit_integrity.py
  ```
- Run the new test suites (once implemented by the implementing agent):
  ```powershell
  $env:PYTHONPATH="."; .\.venv\Scripts\python.exe -m pytest tests/test_game_state_popup_triggers.py tests/test_editor_plugins_roundtrip_integrity.py
  ```

### 5.2 Verification Files to Inspect
- `tests/test_popup_scene_manager.py`: Verifies `event_prologue_awakening` lookup passes once title is updated to `"The Awakening"`.
- `game_data/scene_popups_config.json`: Inspect presence of `event_book_ponder`, `event_first_encounter`, `event_forest_inquiry_1400m`, and entity 10 distance = 1013.
- `game_data/.level_default.json`: Inspect that `"last_level"` points to `"game_data/level_1.json"`.

### 5.3 Invalidation Conditions
- If any editor plugin save drops an existing key from a JSON configuration file, the test must fail.
- If any pop-up trigger path in `GameState` encounters a missing ID in `scene_popups_config.json` and triggers fallback code, the test must fail.
- If any backup file is 0 bytes or exceeds 5 rolling backups, the test must fail.
