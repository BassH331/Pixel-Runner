# Comprehensive Exploration Report: Editor Plugins & Data Parity

**Explorer**: Explorer 2 (Editor Plugins & Data Parity)  
**Working Directory**: `c:\Users\me\Documents\game\Pixel-Runner\.agents\teamwork\teamwork_explorer_survey_2\`  
**Date**: 2026-10-28  

---

## 1. Observation

### 1.1 Repository Editor Plugins and Tools Inventory
Direct search and filesystem inspection located 18 interactive GUI editor plugins, standalone tools, and underlying configuration managers across the codebase:

1. **`popup_controller.py`** (2,701 lines / 128,809 bytes): Pop-up Notification Control System GUI plugin. Manages scene/entity notification pop-ups.
2. **`level_editor.py`** (4,135 lines / 199,122 bytes): Level Spawner & World Event Editor v2 (Wizard-style multi-stage GUI).
3. **`notification_editor.py`** (1,089 lines / 49,150 bytes): Pop-Up & Side Notification theme, timing, geometry, and live simulation GUI editor.
4. **`cutscene_editor.py`** (6,001 lines / 256,104 bytes): Transformation Cutscene Web-based Studio and live visual previewer.
5. **`boss_editor.py`** (2,382 lines / 113,904 bytes): Multi-boss configuration editor, AI telemetry simulator, and difficulty tuner.
6. **`wizard_editor.py`** (1,158 lines / 55,128 bytes): Fire Wizard boss telemetry configurator and animation tuner.
7. **`blood_zombie_editor.py`** (1,452 lines / 67,909 bytes): Blood Zombie animation, combat metrics, and metaphor tuning GUI.
8. **`the_eye.py` & `src/game/systems/the_eye_manager.py`** (2,256 lines / 101,189 bytes; 1,744 lines / 83,959 bytes): 3D interactive narrative tree, dialogue leaves, and perception manager.
9. **`wave_editor.py`** (648 lines / 27,980 bytes): Enemy Wave Designer v2 GUI plugin.
10. **`entity_editor.py`** (874 lines / 39,357 bytes): Graphical Hitbox, Dimension & Floor Editor GUI.
11. **`power_icons_editor.py`** (1,128 lines / 48,928 bytes): Power Icons & Screen Placement GUI editor.
12. **`controls_editor.py`** (741 lines / 31,415 bytes): Control Mapping & Key/Gamepad Remapping GUI visualizer.
13. **`audio_mixer_editor.py`** (3,742 lines / 184,927 bytes): Web-based Audio Configurator & Sound Mixer studio.
14. **`player_editor.py`** (1,981 lines / 92,590 bytes): Player Character Animation Configurator & Hitbox Tuner GUI.
15. **`shadow_editor.py`** (648 lines / 30,480 bytes): Shadow Tuning & Alignment Studio GUI.
16. **`storyline_editor.py`** (366 lines / 16,830 bytes): Storyline & Relic Plugin GUI Editor.
17. **`voiceover_editor.py`** (770 lines / 38,057 bytes): Chatterbox Voiceover Generation GUI plugin.
18. **`split_spritesheet.py`** (165 lines / 5,930 bytes): Sprite sheet splitter and sidecar frame metadata generator.
19. **`tools/chatterbox_backend.py`** (331 lines / 11,838 bytes): Subprocess voice manifest executor.
20. **Underlying Config Managers**:
    - `src/game/systems/popup_scene_manager.py`
    - `src/game/systems/notification_config_manager.py`
    - `src/game/systems/storyline_config_manager.py`
    - `src/game/entities/hitbox_registry.py`
    - `src/game/systems/shadow_registry.py`
    - `src/game/controls_manager.py`
    - `src/game/audio/audio_lock.py`
    - `src/game/utils/atomic_save.py`

---

### 1.2 Data Loading, Saving, Atomic Save Usage, and Key Preservation Matrix

| Plugin / Tool | Target JSON File(s) | Read Logic | Write Logic | Atomic Save (`atomic_save.py`) | Rolling Backups? | Preserves External / Unowned Keys? | Discrepancies & Violations |
|---|---|---|---|---|---|---|---|
| **`popup_controller.py`** | `game_data/scene_popups_config.json`<br>`game_data/level_1.json` | `json.load` via `PopupSceneManager` & `EntityCatalog` | `PopupSceneManager.save_config()` | `atomic_write_json` used in manager | Yes (max 5) | **NO** (Drops unowned top-level keys in `save_config`) | Crash on `distance: null` in sort/distance steppers; Missing 3 events; Text mismatch; Distance mismatch. |
| **`level_editor.py`** | `game_data/level_*.json`<br>`storyline/level_*.json`<br>`game_data/entity_dimensions.json` | `json.load` with UTF-8 | Custom `.tmp_<pid>` + `os.replace` (lines 2455-2458) | **NO** (Does not import `atomic_save.py`) | **NO** (No backup created on commit) | **YES** (Smart 3-way merge on disk read retains spawn zones, taunts, props) | No `fsync`/flush before replace; no rolling backups; does not use unified `atomic_save.py`. |
| **`notification_editor.py`** | `game_data/notification_config.json` | `NotificationConfigManager.load_config()` | `NotificationConfigManager.save_config()` | **YES** (`atomic_merge_json` line 227) | Yes (max 5) | **YES** (`atomic_merge_json` merges fresh disk dict) | None. Fully CIA compliant. |
| **`cutscene_editor.py`** | `game_data/cutscene_config.json` | `json.load` | `atomic_write_json` (line 121) | **YES** (`atomic_write_json`) | Yes (max 5) | **PARTIAL** (Overwrites top-level with frontend dict without disk merge) | Does not re-read disk or merge external keys added directly to JSON. |
| **`boss_editor.py`** | `game_data/boss_*_config.json`<br>`game_data/*_presets.json`<br>`game_data/enemy_skeleton_minion_config.json` | `json.load` | Presets: `atomic_merge_json` (line 813)<br>Boss config: `open(w)` (lines 1002, 1015) | **INCONSISTENT** (Presets use `atomic_merge_json`; main config uses direct `open(w)`) | **AD-HOC** (`shutil.copy2` to `.backup_<ts>.json` unpruned) | Presets: YES.<br>Main config: **NO** (Does not re-read fresh disk before save) | Direct `open("w")` without tmp file or atomic replace; backup accumulation without 5-file cap. |
| **`wizard_editor.py`** | `game_data/boss_wizard_config.json`<br>`game_data/wizard_presets.json` | `json.load` | `atomic_merge_json` (lines 335, 443) | **YES** (`atomic_merge_json` for both) | Yes (max 5) | **YES** (`atomic_merge_json`) | Redundant legacy `shutil.copy2` backup block prior to atomic merge. |
| **`blood_zombie_editor.py`** | `game_data/enemy_blood_zombie_config.json`<br>`game_data/blood_zombie_presets.json`<br>`game_data/entity_dimensions.json` | `json.load` | `atomic_merge_json` (line 588) & `HitboxRegistry.save_all()` | **YES** (`atomic_merge_json` & `atomic_write_json`) | Yes (max 5) | **YES** | None. Fully compliant. |
| **`the_eye.py` / `the_eye_manager.py`** | `game_data/level_1.json`<br>`game_data/storyline_config.json`<br>`game_data/notification_events.json` | `json.load` | `atomic_write_json` (lines 1148, 1584, 1742) | **YES** (`atomic_write_json`) | Yes (max 5) | **YES** (Smart 3-way merge, disk re-read, no event resurrection) | None. Fully compliant. |
| **`wave_editor.py`** | `game_data/level_*.json` | `json.load` | Commit: custom `.tmp_<pid>` + `os.replace` (line 260)<br>Simulate: direct `open(w)` (line 350) | **NO** (Does not import `atomic_save.py`) | **NO** (No backup created on commit) | Commit: **YES** (re-reads disk and updates only `spawn_zones`).<br>Simulate: **DANGEROUS** (writes uncommitted temp data directly to level file) | In `simulate()`, writes directly to `level_file` with `open("w")`. If simulation crashes, file remains corrupted. |
| **`entity_editor.py`** | `game_data/entity_dimensions.json` | `HitboxRegistry._load_config()` | `HitboxRegistry.save_all()` | **YES** (`atomic_write_json` via registry) | Yes (max 5) | **YES** (preserves unedited registry entities) | None. Fully compliant. |
| **`power_icons_editor.py`** | `game_data/power_icons_config.json` | `json.load` | `atomic_merge_json` (line 406) | **YES** (`atomic_merge_json`) | Yes (max 5) | **YES** | None. Fully compliant. |
| **`controls_editor.py`** | `game_data/controls_config.json` | `ControlsManager.load_config()` | `ControlsManager.save_config()` | **YES** (`atomic_write_json` via manager line 145) | Yes (max 5) | **NO** (constructs fixed payload dict) | Drops unknown top-level keys if present. |
| **`audio_mixer_editor.py`** | `settings.json`<br>`game_data/*_audio_config.json` | `json.load` | `save_config_and_lock()` (line 3704) | **YES** (`atomic_write_json` via `audio_lock.py`) | Yes (max 5) | **PARTIAL** (Writes full config dict from web frontend) | None. |
| **`player_editor.py`** | `game_data/player_config.json` | `json.load` | Custom `.tmp` + `os.replace` (lines 1097-1104) | **NO** (Does not import `atomic_save.py`) | **AD-HOC** (`shutil.copy2` unpruned) | **NO** (replaces file with `{"states": ..., "attacks": ...}`) | Does not use `atomic_write_json`, no fsync, unpruned backup accumulation. |
| **`shadow_editor.py`** | `game_data/shadow_config.json` | `ShadowRegistry._load_config()` | `ShadowRegistry.save_profile()` | **YES** (`atomic_merge_json` via registry line 182) | Yes (max 5) | **YES** | None. Fully compliant. |
| **`storyline_editor.py`** | `game_data/storyline_config.json` | `StorylineConfigManager.load_config()` | `StorylineConfigManager.save_config()` | **YES** (`atomic_merge_json` via manager line 68) | Yes (max 5) | **YES** | None. Fully compliant. |
| **`voiceover_editor.py`** | `tools/voice_manifest.json` | `json.load` | `atomic_write_json` (line 51) | **YES** (`atomic_write_json`) | Yes (max 5) | **PARTIAL** (writes full manifest dict) | `tools/chatterbox_backend.py` uses direct `open("w")` on same file. |
| **`split_spritesheet.py`** | None (reads PNGs) | N/A | Direct `open("w")` for sidecar `config.json` | **NO** (Direct `open`) | **NO** | N/A (Creates new file) | No atomic save on sidecar generation. |

---

### 1.3 Detailed Deep-Dive Audit: `popup_controller.py` & `scene_popups_config.json`

#### Direct Source Evidence

1. **Top-Level Field Drop in `PopupSceneManager.save_config()`**:
   *Location*: `src/game/systems/popup_scene_manager.py` lines 197-202:
   ```python
   payload = {
       "version": "1.0",
       "description": "Canonical Scene and Entity Pop-up Notification Configuration for Pixel-Runner",
       "scenes": self._scenes,
   }
   success = atomic_write_json(path, payload, indent=2, backup=True)
   ```
   *Direct Observation*: When `save_config()` is executed, any key in `game_data/scene_popups_config.json` other than `"version"`, `"description"`, and `"scenes"` is discarded. Furthermore, it does not re-read disk before writing, which means external manual or concurrent edits to non-owned fields are completely overwritten.

2. **Crash Vector 1: `TypeError: float() argument must be a string or a real number, not 'NoneType'`**:
   *Locations*: `popup_controller.py`:
   - Line 551: `self.scenes.sort(key=lambda s: float(s.get("distance", 0)))`
   - Line 1061: `self.scenes.sort(key=lambda s: float(s.get("distance", 0)))`
   - Line 1094: `self.scenes.sort(key=lambda s: float(s.get("distance", 0)))`
   *Direct Observation*: In Python, if a dictionary contains `"distance": null` (e.g. flag events or unconfigured distances), `s.get("distance", 0)` returns `None` (not `0`), because `"distance"` is a present key with value `None`. `float(None)` immediately raises:
   ```python
   TypeError: float() argument must be a string or a real number, not 'NoneType'
   ```

3. **Crash Vector 2: String Formatting and Stepper Distance Crashes**:
   *Locations*: `popup_controller.py`:
   - Line 1749-1750: `tag_label = f"📍 {int(float(dist))}m"` where `dist = scene.get("distance", 0)`
   - Line 1912: `nearest = self.catalog.get_nearest_entity(float(scene.get("distance", 0)))`
   - Line 1914: `f"Linked Trigger: Distance Milestone @ {int(float(scene.get('distance', 0)))}m"`
   - Line 1916: `f"Triggers when player runs past {int(float(scene.get('distance', 0)))}m mark{near_str}"`
   - Line 1339: `cur_dist = float(scene.get("distance", 0))`
   *Direct Observation*: All five locations assume `s.get("distance", 0)` cannot be `None`. If `distance` is `None`, each location crashes on `float(None)`.

4. **Crash Vector 3: Unhandled Conversion `int(eid)`**:
   *Locations*: `popup_controller.py`:
   - Line 1881: `avatar = self.catalog.get_avatar_surface(int(eid), size=(44, 44))`
   - Line 1884: `ent = self.catalog.get_entity(int(eid))`
   *Direct Observation*: Although `get_avatar_surface` contains internal `try...except (ValueError, TypeError)`, line 1881 calls `int(eid)` prior to passing the value into `get_avatar_surface`. If `eid` is a string that cannot be parsed as an integer (e.g. `"?"` or `"boss_bat"`), an uncaught `ValueError` crashes the renderer.

5. **Crash Vector 4: `TypeError` in `PopupSceneManager.get_popups_by_distance()`**:
   *Location*: `src/game/systems/popup_scene_manager.py` line 141-143:
   ```python
   for s in self._scenes:
       if s.get("trigger_type") == "distance":
           target_dist = s.get("distance", -9999)
           if abs(distance - target_dist) <= tolerance:
               matches.append(dict(s))
   ```
   *Direct Observation*: If a scene has `"trigger_type": "distance"` but `"distance": null`, `s.get("distance", -9999)` returns `None`. The subtraction `distance - None` immediately raises:
   ```python
   TypeError: unsupported operand type(s) for -: 'float' and 'NoneType'
   ```

6. **Crash Vector 5: Missing `headless: bool = False` Constructor Support**:
   *Location*: `popup_controller.py` lines 509-528:
   *Direct Observation*: Unlike `notification_editor.py` which accepts `NotificationEditorApp(headless=True)`, `PopupControllerApp.__init__()` takes no arguments and attempts `win = pg.Window.from_display_module(); win.maximize()`. In headless CI environments where no window manager or display server exists, this can fail unless dummy display driver is set and window maximize exceptions are caught.

---

### 1.4 Game Runtime & Configuration Parity Discrepancies

1. **Missing Pop-up Event Entries in `game_data/scene_popups_config.json`**:
   Inspection of `src/game/states/game_state.py` revealed that `GameState` actively queries `self.popup_scene_manager.get_popup()` for the following three scene IDs, none of which exist in `game_data/scene_popups_config.json`:
   - **`event_book_ponder`** (queried at `game_state.py:919` in `_show_ambient_lore` and at line 2127):
     - GameState fallback title: `"The Grimoire Whispers"` / `"The Runner Wonders"`
     - Fallback text: `"What does this demon want with me...?"`
     - Fallback icon: `"assets/graphics/magic_book_single/magic_book.png"`
     - Fallback hold: `8.5`
     - Fallback theme: `"grimoire_leather"`
   - **`event_first_encounter`** (queried at `game_state.py:1840`):
     - Fallback title: `"First Encounter"`
     - Fallback theme: `"blood_bone"`
   - **`event_forest_inquiry_1400m`** (queried at `game_state.py:1677`):
     - Fallback distance: `1400.0`
     - Fallback title: `"The Runner Questions"`
     - Fallback text: `"What in God's name is this forest...?"`
     - Fallback theme: `"clean_minimalist"`
     - Fallback icon: `"assets/graphics/UI/PNG/Exclamation_Yellow.png"`
     - Fallback hold: `6.0`

2. **Narrative Text Copy-Paste Bug in `event_prologue_awakening`**:
   *Location*: `game_data/scene_popups_config.json` lines 6-17:
   ```json
   {
     "id": "event_prologue_awakening",
     "trigger_type": "distance",
     "distance": 0,
     "entity_id": null,
     "flag": null,
     "title": "The Fabricator's Enforcer",
     "text": "Clanking gears of malice screech in the dark. The final sentinel awakens to crush your escape.",
     "theme": "gothic_gold",
     "icon": "assets/MAGE ICONS BIG PACk (by Batareya)/48.png",
     "hold": 15.0,
     "enabled": true,
     "description": "Prologue intro at game start"
   }
   ```
   *Direct Observation*: The title and text are an exact duplicate of `event_fabricators_enforcer` (Entity 3 @ 34,500m), whereas the prologue awakening narrative in `game_state.py:969-973` expects:
   - Title: `"The Awakening"`
   - Text: `"The catacombs stir. Death has not taken you, but the dark beckons. Advance through the gloom."`
   - Icon: `"assets/graphics/UI/PNG/Exclamation_Yellow.png"`
   - Hold: `6.0`
   - Theme: `"gothic_gold"`

3. **Entity Distance Misalignment with `game_data/level_1.json`**:
   - In `game_data/level_1.json` line 560-565:
     ```json
     {
         "id": 10,
         "distance": 1013,
         "type": "npc",
         "params": {
             "title": "The Sealed Book"
         }
     }
     ```
   - In `game_data/scene_popups_config.json` lines 20-24:
     ```json
     {
       "id": "event_sealed_book_encounter",
       "trigger_type": "entity",
       "distance": 650,
       "entity_id": 10
     }
     ```
   *Direct Observation*: The Sealed Book entity in `level_1.json` is at distance `1013`, but `scene_popups_config.json` lists its distance as `650`.

4. **Invalid Default Level Pointer**:
   *Location*: `game_data/.level_default.json` line 1:
   ```json
   {"last_level": "game_data/level_2.json"}
   ```
   *Direct Observation*: `find_by_name` for `level_2.json` across the entire workspace returned 0 results. Level 2 does not exist in the repository; the file must point to an existing level such as `"game_data/level_1.json"`.

5. **Silenced Systems Verification**:
   - `src/game/systems/whisperer_system.py:44`: `ENABLED: bool = False` (verified silenced).
   - `src/game/states/game_state.py:1476`: `# self._update_boss_combat_taunts(dt)` (verified commented out / silenced).
   - `src/game/ui/hud_overlay.py:50-54`: `objective_display` is never updated or drawn in `HUDOverlay.update()` or `HUDOverlay.draw()` (verified inactive).

---

## 2. Logic Chain

1. **Premise**: In-game notifications must trigger reliably across gameplay without fallback degradation or missing content.
   - *Evidence*: `GameState` at lines 919, 1677, 1840 queries `PopupSceneManager` for `event_book_ponder`, `event_forest_inquiry_1400m`, and `event_first_encounter`.
   - *Observation*: `game_data/scene_popups_config.json` contains none of these three keys.
   - *Inference*: When a player triggers these milestones, `PopupSceneManager` returns `None`. Although `GameState` has hardcoded inline fallbacks, the data-driven architecture is bypassed, and the player cannot configure these messages via `popup_controller.py`.

2. **Premise**: `popup_controller.py` must load, display, edit, and save all notifications without throwing runtime exceptions.
   - *Evidence*: In `popup_controller.py` lines 551, 1061, 1094, `s.get("distance", 0)` is wrapped directly with `float(...)`. In lines 1749, 1912, 1914, `dist` is wrapped with `float(...)`.
   - *Observation*: If a scene has `"distance": null` or is added with `None`, `s.get("distance", 0)` returns `None`. In Python, `float(None)` raises `TypeError`.
   - *Inference*: Loading or sorting any configuration with null distances crashes `popup_controller.py`. A safe helper `float(s.get("distance") or 0.0)` is strictly necessary.

3. **Premise**: Config saves across all plugins must maintain CIA integrity (atomic transactional write, fsync, non-empty rolling backups, disk re-read and key preservation).
   - *Evidence*: `src/game/utils/atomic_save.py` provides `atomic_write_json` and `atomic_merge_json` with rolling backup pruning (max 5).
   - *Observation*:
     - `level_editor.py` (lines 2455-2458) and `wave_editor.py` (lines 259-262) write to `.tmp_<pid>` without calling `atomic_save.py`, without fsync, and without generating rolling backups.
     - `boss_editor.py` (lines 1002, 1015) uses direct `open("w")` for boss and minion configs, and accumulates unpruned backups with `shutil.copy2`.
     - `player_editor.py` (lines 1097-1104) writes to `.tmp` without fsync, accumulates unpruned backups, and drops external keys.
     - `PopupSceneManager.save_config()` writes an explicit 3-key payload (`version`, `description`, `scenes`) without merging fresh disk content, dropping custom top-level fields.
   - *Inference*: These five editors violate the project's CIA commit integrity invariants. Integrating `atomic_save.py` (`atomic_merge_json` or `atomic_write_json`) across all of them will eliminate partial-write vulnerabilities and backup proliferation.

4. **Premise**: Entity links in `scene_popups_config.json` must be mathematically aligned with entity placement in `level_1.json`.
   - *Evidence*: `game_data/level_1.json:561` places Entity 10 at distance `1013`. `game_data/scene_popups_config.json:22` places Entity 10 at distance `650`.
   - *Inference*: When a player approaches Entity 10 at 1013m, a distance mismatch could lead to premature or delayed triggering. Updating `scene_popups_config.json` distance to `1013` restores 100% parity.

---

## 3. Caveats

1. **Read-Only Investigation**: As an explorer agent, no source code, configuration, or test files were modified during this investigation. All findings represent current repository state as of 2026-10-28.
2. **Subprocess/Sandbox Execution**: Terminal execution of custom python scripts was restricted by workspace sandbox policy; all code inspections and line audits were conducted via direct filesystem viewing and ripgrep tooling.
3. **External Dependencies**: Audio generation in `voiceover_editor.py` relies on an optional `tools/chatterbox-venv` environment. Lack of Chatterbox does not affect data integrity or JSON schema parity.
4. **No other caveats**: The findings above are exhaustive and directly verified against the repository source.

---

## 4. Conclusion

1. **Pop-up Runtime & Config Discrepancies**:
   - `game_data/scene_popups_config.json` is missing 3 canonical events (`event_book_ponder`, `event_first_encounter`, `event_forest_inquiry_1400m`).
   - `event_prologue_awakening` contains erroneous text copy-pasted from `event_fabricators_enforcer` and must be updated to prologue awakening text.
   - `event_sealed_book_encounter` distance must be corrected from `650` to `1013` to match Entity 10 in `game_data/level_1.json`.
   - `game_data/.level_default.json` must be updated from nonexistent `"game_data/level_2.json"` to `"game_data/level_1.json"`.
   - Silenced systems (`WhispererSystem.ENABLED = False`, commented-out boss combat taunts, inactive `ObjectiveDisplay`) are verified disabled and must remain untouched.

2. **`popup_controller.py` & `PopupSceneManager` Hardening**:
   - Fix 5 crash vectors regarding `float(None)`, unhandled `int(eid)`, and `distance - None`.
   - In `PopupSceneManager.save_config()`, preserve unowned top-level fields by reading fresh disk state and updating rather than replacing the dict.
   - Add `headless: bool = False` support to `PopupControllerApp.__init__()` to enable seamless automated testing in CI.

3. **Multi-Editor Atomic Save Harmonization**:
   - Update `boss_editor.py` (`confirm_save_config`), `level_editor.py` (`commit`), `wave_editor.py` (`commit` and `simulate`), and `player_editor.py` (`request_save_config`) to use `src/game/utils/atomic_save.py` (`atomic_merge_json` or `atomic_write_json`).
   - Replace unpruned `shutil.copy2` backup logic with `create_validated_backup` and `prune_backups`.

---

## 5. Verification Method

To independently verify these findings, perform the following steps:

1. **Inspect Missing Pop-up Event Keys**:
   - Check `game_data/scene_popups_config.json` for `"event_book_ponder"`, `"event_first_encounter"`, `"event_forest_inquiry_1400m"`. Note that none exist.
   - View `src/game/states/game_state.py` lines 919, 1677, 1840 to confirm `get_popup()` lookups for these exact event IDs.

2. **Inspect Entity 10 Coordinate Parity**:
   - View `game_data/level_1.json` line 560-565 (distance is `1013`).
   - View `game_data/scene_popups_config.json` lines 20-25 (distance is `650`).

3. **Inspect Non-Atomic Saves in Editors**:
   - View `boss_editor.py` lines 1001-1004 (direct `with open(config_path, "w")`).
   - View `level_editor.py` lines 2455-2458 (custom `.tmp_<pid>` without fsync or rolling backup).
   - View `wave_editor.py` lines 347-353 (`simulate()` direct write to `level_file`).
   - View `player_editor.py` lines 1097-1104 (custom `.tmp` without fsync).

4. **Verify Existing Integrity Test Pass Rate**:
   - Run the project test suite:
     ```bash
     PYTHONPATH=. pytest tests/test_all_plugins_cia_integrity.py tests/test_plugin_commit_integrity.py tests/test_popup_scene_manager.py tests/test_popup_controller.py
     ```
