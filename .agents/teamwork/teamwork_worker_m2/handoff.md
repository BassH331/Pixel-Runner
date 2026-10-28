# Handoff Report — Milestone 2: Editor Plugin Data Parity & Hardening

**Worker**: Worker M2 (`teamwork_worker_m2`)  
**Parent Agent**: `4ca1b8f5-359d-47e4-86f8-c95f371a5412`  
**Date**: 2026-10-28  
**Scope**: `popup_controller.py`, `src/game/systems/popup_scene_manager.py`, `boss_editor.py`, `level_editor.py`, `wave_editor.py`, `player_editor.py`

---

## 1. Observation

### 1.1 `popup_controller.py` Vulnerabilities
- **Unsafe float conversions**:
  - `popup_controller.py:551, 1061, 1094`: Direct calls to `float(s.get("distance", 0))` in scene sorting lambdas.
  - `popup_controller.py:1339, 1345`: Direct calls to `float(scene.get("distance", 0))` in distance steppers (`dist_minus` and `dist_plus`).
  - `popup_controller.py:1749`: Direct call to `int(float(dist))` where `dist = scene.get("distance", 0)`.
  - `popup_controller.py:1912, 1914, 1916`: Direct calls to `float(scene.get("distance", 0))` in distance milestone inspector cards.
  - *Observation*: When a scene contains `"distance": null` (common in flag-based popups), `s.get("distance", 0)` returns `None` rather than the default `0`. Calling `float(None)` triggers `TypeError: float() argument must be a string or a real number, not 'NoneType'`.
- **Unhandled `int(eid)`**:
  - `popup_controller.py:1881, 1884`: `avatar = self.catalog.get_avatar_surface(int(eid))` and `self.catalog.get_entity(int(eid))` called `int(eid)` without a try-except block, causing an uncaught `ValueError` if `eid` was `"?"` or non-numeric.
- **Headless CI display initialization**:
  - `popup_controller.py:509-528`: Did not accept `headless: bool` and attempted desktop window maximizing without a headless flag guard.

### 1.2 `src/game/systems/popup_scene_manager.py` Deficiencies
- **Distance comparison NoneType exception**:
  - `src/game/systems/popup_scene_manager.py:141-143`: `target_dist = s.get("distance", -9999)` returns `None` if `"distance": null`, causing `abs(distance - target_dist)` to crash with `TypeError: unsupported operand type(s) for -: 'float' and 'NoneType'`.
- **Entity index clobbering**:
  - `src/game/systems/popup_scene_manager.py:102-107`: All scenes with an `entity_id` were unconditionally stored in `self._scenes_by_entity[int(eid)]`. Flag triggers (such as `event_book_ponder` which references entity 10) risked clobbering primary entity encounter lookups (e.g., `event_sealed_book_encounter`).
- **External key loss on disk save**:
  - `src/game/systems/popup_scene_manager.py:197-202`: `save_config()` constructed a fixed 3-key dictionary (`"version"`, `"description"`, `"scenes"`), completely discarding any custom or external top-level metadata present in `game_data/scene_popups_config.json`.

### 1.3 Editor Plugins Atomic Persistence Violations
- **`boss_editor.py`**:
  - `boss_editor.py:1002-1016`: Used raw `open(config_path, "w")` and `open(minion_path, "w")` without tmp file or atomic replacement, while accumulating unpruned backups via `shutil.copy2`.
- **`level_editor.py`**:
  - `level_editor.py:2455-2458`: Used custom `.tmp_<pid>` without `os.fsync` or rolling backups.
- **`wave_editor.py`**:
  - `wave_editor.py:260`: Used custom `.tmp_<pid>` without fsync or rolling backup pruning in `commit()`.
  - `wave_editor.py:350`: In `simulate()`, wrote uncommitted simulation state directly to the production `level_file` with truncating `open(..., "w")`.
- **`player_editor.py`**:
  - `player_editor.py:1085-1104`: Accumulated unpruned backups via `shutil.copy2` and wrote to `.tmp` without fsync or disk key preservation.

---

## 2. Logic Chain

1. **Defensive Distance Helper**:
   - Implemented `_safe_float(val: Any, default: float = 0.0) -> float` in `popup_controller.py`.
   - Replaced all raw `float(s.get("distance", 0))` calls with `_safe_float(s.get("distance", 0))`.
   - Result: Any scene with `"distance": null`, missing keys, or invalid types safely defaults to `0.0` without throwing a `TypeError`.
2. **Safe Entity ID Parsing & Headless Guard**:
   - In `popup_controller.py` line 1894+, wrapped `eid` conversion in a `try...except (ValueError, TypeError)` block and rendered an unresolved fallback card if `eid` is non-numeric.
   - Updated `PopupControllerApp.__init__(self, headless: bool = False)` to set `SDL_VIDEODRIVER="dummy"` and bypass desktop `win.maximize()` in headless environments.
3. **PopupSceneManager Indexing & Distance Lookups**:
   - In `_rebuild_indices()`, restricted `self._scenes_by_entity` indexing to scenes where `trigger_type == "entity"` or non-flag/distance triggers with integer `entity_id`. Primary entity encounter scenes take precedence.
   - In `get_popups_by_distance()`, guarded `distance is None` and `target_dist is None`, skipping invalid distances cleanly.
   - In `save_config()`, re-read existing disk JSON prior to saving, preserving all external/unowned top-level fields while atomically writing `scenes`.
4. **Harmonizing Atomic Commit Workflow Across Editors**:
   - Integrated `atomic_write_json` and `prune_backups` from `src.game.utils.atomic_save` into `boss_editor.py`, `level_editor.py`, `wave_editor.py`, and `player_editor.py`.
   - In `wave_editor.py`, isolated simulation runs into a temporary simulation file (`sim_file = f"{level_file}.sim_{os.getpid()}.json"`), passed `--level sim_file` to `main.py`, and cleaned up the temp file in `finally:`, preventing production level file corruption.
   - In `player_editor.py`, preserved external disk keys, added rolling backup pruning, and updated `scan_backups` to recognize both legacy and atomic_save backup patterns.

---

## 3. Caveats

1. **Headless Execution Environment**: Headless execution in CI requires `SDL_VIDEODRIVER="dummy"`, which is now natively supported by `PopupControllerApp(headless=True)`.
2. **Backups Directory Retention**: Backup files are strictly capped at 5 files per target configuration file via `prune_backups`.
3. **No other caveats**: All 6 owned files have been hardened according to specifications with zero scope creep.

---

## 4. Conclusion

Milestone 2 objectives are completely fulfilled:
- `popup_controller.py` is fully hardened against `NoneType` distance crashes, non-numeric entity IDs, and headless environments.
- `src/game/systems/popup_scene_manager.py` safely handles distance lookups, prevents entity index clobbering by flag scenes, and preserves external top-level keys across saves.
- `boss_editor.py`, `level_editor.py`, `wave_editor.py`, and `player_editor.py` are harmonized to use canonical atomic transactional writes (`atomic_write_json`) with rolling backup pruning capped at 5 files.
- `wave_editor.py` simulation workflow no longer touches or truncates production level files.

---

## 5. Verification Method

### 5.1 Automated Pytest Execution
Run the test suite verifying all modified systems and commit integrity:
```powershell
$env:PYTHONPATH="."; .\.venv\Scripts\python.exe -m pytest tests/test_popup_controller.py tests/test_popup_scene_manager.py tests/test_all_plugins_cia_integrity.py tests/test_plugin_commit_integrity.py
```
Expected result: 39 passed in ~8s.

### 5.2 Files to Inspect
1. `popup_controller.py`:
   - Inspect line 71: `def _safe_float(val: Any, default: float = 0.0) -> float`
   - Inspect line 520: `def __init__(self, headless: bool = False)`
   - Inspect lines 1895-1940: `parsed_eid` safe integer parsing and `_safe_float` distance card
2. `src/game/systems/popup_scene_manager.py`:
   - Inspect lines 102-114: `_rebuild_indices` entity trigger filtering
   - Inspect lines 136-155: `get_popups_by_distance` None guards
   - Inspect lines 208-230: `save_config` disk re-read and key preservation
3. `boss_editor.py`:
   - Inspect lines 987-1020: `atomic_write_json` and `prune_backups`
4. `level_editor.py`:
   - Inspect lines 2454-2458: `atomic_write_json(target_path, disk_data, indent=4, backup=True, max_backups=5)`
5. `wave_editor.py`:
   - Inspect line 260: `atomic_write_json` in `commit()`
   - Inspect lines 340-380: Isolated temp simulation file and `--level sim_file` in `simulate()`
6. `player_editor.py`:
   - Inspect lines 831-840: Multi-pattern backup scanning
   - Inspect lines 1085-1120: `atomic_write_json` and `prune_backups` with disk key preservation

### 5.3 Invalidation Conditions
- Any occurrence of `TypeError: float() argument must be a string or a real number, not 'NoneType'` in `popup_controller.py`.
- Any occurrence of unhandled `ValueError` when `entity_id` is a string or non-numeric in `popup_controller.py`.
- Any loss of unowned top-level fields when `PopupSceneManager.save_config()` or `PlayerEditor.request_save_config()` is invoked.
- Production `level_1.json` being truncated or left corrupted during a cancelled wave simulation.
