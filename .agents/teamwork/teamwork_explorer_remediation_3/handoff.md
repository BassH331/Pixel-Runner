# Regression Remediation Investigation & Handoff Report

**Explorer**: Explorer Remediation 3 (`teamwork_explorer_remediation_3`)  
**Mission**: Full Root Cause Analysis and Surgical Fix Recommendations for 4 Regressions Identified by Forensic Auditor  
**Date**: 2026-10-28  

---

## Executive Summary

| Issue | Target File & Line | Verbatim Error / Symptom | Root Cause | Surgical Remediation |
|---|---|---|---|---|
| **1. Player Editor Backup Naming** | `tests/test_player_editor.py:75` | `AssertionError: False is not true` | Legacy unit test expects `player_config.backup_<timestamp>.json`, while unified `atomic_save.py` creates `player_config.json.backup_<timestamp>`. All M2/M3 CIA tests strictly assert `<file>.backup_*`. | Update assertion in `tests/test_player_editor.py:75` to accept `player_config.backup_` OR `player_config.json.backup_`. |
| **2. Player Ground Y Mismatch** | `tests/test_engine_presentation.py:66` | `assert player.rect.bottom == 606` (got 350) | In-memory class state pollution: `tests/test_editor_plugins_roundtrip_integrity.py:510` mutates `HitboxRegistry._cached_config["player"]` to `scale=1.0` without teardown cleanup. When `test_engine_presentation.py` runs, player frame height is 128 (scale 1.0) instead of 384 (scale 3.0), giving bottom 350 (`222 + 128`) instead of 606 (`222 + 384`). | Add cleanup/reset of `HitboxRegistry._cached_config` in `test_editor_plugins_roundtrip_integrity.py` and add an autouse session fixture in `tests/conftest.py` resetting `HitboxRegistry._cached_config = {}`. |
| **3. Missing Fields / SideNotification Clear** | `tests/test_tier5_adversarial_stress.py:102, 140` | `AttributeError: 'SideNotification' object has no attribute 'clear'` | `test_missing_fields_in_scene_definitions` calls `sn.clear()`, but `SideNotification` in `src/game/ui/side_notification.py` has no `clear()` method. (Same bug also breaks `tests/test_game_state_popup_triggers.py:462`). | Implement `def clear(self) -> None` on `SideNotification` in `src/game/ui/side_notification.py`. |
| **4. Circular Mock Recursion** | `tests/test_editor_plugins_adversarial_m2.py:157` | `RecursionError: maximum recursion depth exceeded` | In `test_adversarial_boss_editor_atomic_save_and_backup_cap`, `patch("os.path.exists", side_effect=lambda p: ... else os.path.exists(p))` calls the patched mock recursively. (Identical bug exists in `test_editor_plugins_roundtrip_integrity.py:347`). Also `level_editor.py:2460` fails to update `self.pending`. | Capture `orig_exists = os.path.exists` before `patch()` and delegate to `orig_exists(p)`. In `level_editor.py:2460`, update `self.pending = copy.deepcopy(merged_events)`. |

---

## 1. Observation

### Observation 1.1: Issue 1 — Player Editor Backup Naming Discrepancy
- **File**: `tests/test_player_editor.py:72-76`
```python
72:         # Verify backup was created
73:         self.app.scan_backups()
74:         self.assertGreater(len(self.app.backups), 0)
75:         self.assertTrue(self.app.backups[0].startswith("player_config.backup_"))
```
- **Error**:
  `AssertionError: False is not true` on line 75.
- **Runtime Execution Trace**:
  - `player_editor.py:1086-1105` invokes `atomic_write_json(self.config_path, combined_data, indent=2, backup=True, max_backups=5)`.
  - In `src/game/utils/atomic_save.py:71`:
    `backup_path = f"{file_path}.backup_{timestamp}"`
    Given `file_path = ".../player_config.json"`, `backup_path` is `player_config.json.backup_<timestamp>`.
  - In `player_editor.py:831-840`:
    ```python
    def scan_backups(self):
        self.backups = []
        if os.path.exists(self.config_dir):
            files = os.listdir(self.config_dir)
            for f in files:
                if (f.startswith("player_config.backup_") and f.endswith(".json")) or f.startswith("player_config.json.backup_") or (f.startswith("player_config") and ".backup_" in f):
                    self.backups.append(f)
            self.backups.sort(reverse=True)
    ```
  - `self.backups[0]` receives `"player_config.json.backup_<timestamp>"`.
  - `"player_config.json.backup_<timestamp>".startswith("player_config.backup_")` evaluates to `False`.
- **Systemic Invariant Check**:
  - `tests/test_editor_plugins_adversarial_m2.py:469`:
    `backups = glob.glob(f"{cfg_path}.backup_*")`
    `assert len(app.backups) == len(backups)`
  - `tests/test_prop_depth_and_integrity.py:187`:
    `backups = [f for f in os.listdir(tmp_path) if f.startswith("data.json.backup_")]`
  - `tests/test_plugin_commit_integrity.py:264`:
    `backups = [f for f in os.listdir(tmp_path) if f.startswith("config.json.backup_")]`
  - `tests/test_all_plugins_cia_integrity.py:52`:
    `backups = glob.glob(str(tmp_path / "test_config.json.backup_*"))`
  - `tests/test_editor_plugins_roundtrip_integrity.py:69`:
    `backups = glob.glob(f"{target_path}.backup_*")`

### Observation 1.2: Issue 2 — Player Ground Y Mismatch via In-Memory Test Pollution
- **File**: `tests/test_engine_presentation.py:63-66`
```python
63: def test_player_ground_y_matches_level_ground():
64:     """Verify player spawned at y=222 is aligned with ground level 606."""
65:     player = Player(200, 222, MagicMock())
66:     assert player.rect.bottom == 606
```
- **Error**:
  `AssertionError: assert player.rect.bottom == 606` (evaluated to `assert 350 == 606`).
- **Mathematical Decomposition**:
  - `Player` spawn position: `midtop = (200, 222)`.
  - `player.rect.top = 222`.
  - Frame asset: `assets/shadow_warrior/idle/idle_1.png` has native unscaled height of 128px.
  - In `src/game/entities/player.py:819-820` and `960-963`:
    ```python
    margins = HitboxRegistry.get_margins("player")
    self.scale = margins.scale
    # ...
    scaled_size = (int(original_size[0] * self.scale), int(original_size[1] * self.scale))
    ```
  - Standard baseline `HitboxRegistry.DEFAULTS["player"].scale = 3.0`:
    `scaled_height = 128 * 3.0 = 384px`.
    `player.rect.bottom = 222 + 384 = 606px` (Matches assertion!).
  - When `self.scale = 1.0`:
    `scaled_height = 128 * 1.0 = 128px`.
    `player.rect.bottom = 222 + 128 = 350px` (Matches failure value 350!).
- **Pollution Source**:
  - In `tests/test_editor_plugins_roundtrip_integrity.py:510-513`:
    ```python
    HitboxRegistry.update_margins(
        "player",
        HitboxMargins(left=9, right=9, top=14, bottom=0, ground_offset=0, scale=1.0)
    )
    HitboxRegistry.save_all()
    ```
  - `HitboxRegistry._cached_config` is a class-level dictionary on `HitboxRegistry`.
  - `test_hitbox_registry_roundtrip_and_key_preservation` mutates `HitboxRegistry._cached_config["player"]` to `scale=1.0` and saves it.
  - There is NO teardown or reset in `test_editor_plugins_roundtrip_integrity.py`.
  - Because `test_editor_plugins_roundtrip_integrity.py` runs before `test_engine_presentation.py` during `pytest tests/`, `HitboxRegistry.get_margins("player")` returns `scale=1.0`, poisoning `Player` initialization in `test_engine_presentation.py`.

### Observation 1.3: Issue 3 — `SideNotification` Missing `clear()` Method
- **File**: `tests/test_tier5_adversarial_stress.py:102, 140`
```python
102:     def test_missing_fields_in_scene_definitions(self, tmp_path):
...
130:         sn = SideNotification(1280, 720)
131:         sn.show(...)
138:         assert sn.is_active is True
139:         sn.update(1.0)
140:         sn.clear()
```
- **Error**:
  `AttributeError: 'SideNotification' object has no attribute 'clear'`
- **Corroborating Failure**:
  - `tests/test_game_state_popup_triggers.py:462`:
    ```python
    sn.clear()
    ```
    Failed with identical error: `AttributeError: 'SideNotification' object has no attribute 'clear'`.
- **Source Inspection**:
  - In `src/game/ui/side_notification.py`:
    Methods defined: `__init__`, `is_active`, `_apply_config`, `_compute_scaling`, `show`, `_start_item`, `_load_icon_surface`, `_wrap_text`, `_build_tab_surface`, `update`, `draw`.
    No `clear()` method exists on `SideNotification`.

### Observation 1.4: Issue 4 — Circular Mock Recursion & LevelEditor Stale Pending State
- **File**: `tests/test_editor_plugins_adversarial_m2.py:157`
```python
155:             with patch("time.time", return_value=fake_ts):
156:                 # Temporarily patch the hardcoded minion path inside confirm_save_config
157:                 with patch("os.path.exists", side_effect=lambda p: True if p in (boss_config_path, minion_config_path) else os.path.exists(p)):
```
- **Error**:
  `RecursionError: maximum recursion depth exceeded`
- **Mechanism**:
  - `patch("os.path.exists", ...)` replaces `os.path.exists` in the `os` module with a MagicMock.
  - The lambda executes: for any path `p` not equal to `boss_config_path` or `minion_config_path`, it calls `os.path.exists(p)`.
  - Since `os.path.exists` has been replaced by the mock whose `side_effect` is this lambda, it calls itself infinitely.
- **Corroborating Circular Mock**:
  - `tests/test_editor_plugins_roundtrip_integrity.py:347`:
    ```python
    patch("os.path.exists", side_effect=lambda p: True if p in (boss_path, minion_path, "game_data/enemy_skeleton_minion_config.json") else os.path.exists(p))
    ```
    Suffers from identical `RecursionError`.
- **Associated Level Editor Bug (`test_adversarial_level_editor_commit_atomic_merge_and_backups`)**:
  - `level_editor.py:2446-2462`:
    ```python
    disk_data["world_events"] = merged_events
    atomic_write_json(target_path, disk_data, indent=4, backup=True, max_backups=5)
    HitboxRegistry.commit_transaction()
    self.level_data = disk_data
    self.level_backup = copy.deepcopy(self.level_data)
    # BUG: self.pending is NEVER updated to merged_events!
    ```
  - When subsequent commits occur in a loop (lines 264-267 of `test_editor_plugins_adversarial_m2.py`), `self.pending` retains stale event text ("Initial book text") while `self.level_backup` has the external update ("External Plugin Dialogue Update").
  - Line 2436: `if ev_params.get("text") == backup_params.get("text") and "text" in disk_params:` evaluates to `False`, clobbering external dialogue updates on subsequent commits.

---

## 2. Logic Chain

1. **Issue 1 (Player Editor Backup Naming)**:
   - Premise 1: Pre-existing legacy test `test_player_editor.py:75` was written before `atomic_save.py` and asserted `self.app.backups[0].startswith("player_config.backup_")`.
   - Premise 2: `atomic_save.py` creates backups named `f"{file_path}.backup_{timestamp}"` (e.g. `player_config.json.backup_1730146000`).
   - Premise 3: Changing `atomic_save.py` to strip the extension before adding `.backup_` breaks `f"{target_path}.backup_*"` globs in 5 other test suites (`test_editor_plugins_adversarial_m2.py`, `test_editor_plugins_roundtrip_integrity.py`, `test_prop_depth_and_integrity.py`, `test_plugin_commit_integrity.py`, `test_all_plugins_cia_integrity.py`).
   - Premise 4: Creating two separate backup files in `player_editor.py` breaks `test_editor_plugins_adversarial_m2.py:476` (`assert len(app.backups) == len(backups)`).
   - Inference: The only consistent and safe resolution is updating `tests/test_player_editor.py:75` to accept both naming conventions (`player_config.backup_` or `player_config.json.backup_`), guaranteeing full backward and forward compatibility without side effects.

2. **Issue 2 (Player Ground Y Mismatch)**:
   - Premise 1: `Player(200, 222, MagicMock())` has top 222.
   - Premise 2: Idle frame height is 128px unscaled.
   - Premise 3: Under default `scale = 3.0`, bottom is `222 + 128 * 3.0 = 606px`. Under `scale = 1.0`, bottom is `222 + 128 * 1.0 = 350px`.
   - Premise 4: `tests/test_editor_plugins_roundtrip_integrity.py:510` mutates `HitboxRegistry._cached_config["player"]` to `scale = 1.0` on the class singleton and does not restore it.
   - Premise 5: In pytest execution order, `test_editor_plugins_roundtrip_integrity.py` runs before `test_engine_presentation.py`.
   - Inference: The failure is 100% caused by cross-test class-state leakage from `test_editor_plugins_roundtrip_integrity.py`. Adding teardown cache restoration and an autouse pytest fixture resetting `HitboxRegistry._cached_config = {}` completely resolves the regression.

3. **Issue 3 (`SideNotification` Missing `clear()`)**:
   - Premise 1: Both `tests/test_tier5_adversarial_stress.py:140` and `tests/test_game_state_popup_triggers.py:462` call `sn.clear()`.
   - Premise 2: `SideNotification` does not implement `clear()`, raising `AttributeError`.
   - Inference: Adding `def clear(self) -> None:` to `SideNotification` satisfies the interface contract and allows clean UI state resets in headless tests.

4. **Issue 4 (Circular Mock Recursion & Level Editor State)**:
   - Premise 1: `with patch("os.path.exists", side_effect=lambda p: ... else os.path.exists(p))` calls the active patch within the lambda.
   - Premise 2: Any lookup for non-overridden paths re-invokes the mock, exceeding Python's recursion limit.
   - Premise 3: Preserving `orig_exists = os.path.exists` outside the patch and delegating to `orig_exists(p)` avoids recursion.
   - Premise 4: In `level_editor.py:commit()`, failing to update `self.pending = copy.deepcopy(merged_events)` causes subsequent commits to compare against stale pending data, clobbering external updates.
   - Inference: Fixing the mock reference and adding `self.pending = copy.deepcopy(merged_events)` fixes both tests in `test_editor_plugins_adversarial_m2.py`.

---

## 3. Caveats

- **Test Suite Isolation**: Tests in `tests/` heavily rely on singleton classes (`HitboxRegistry`, `AssetManager`, `NotificationConfigManager`, `PopupSceneManager`). Any test mutating class-level attributes without resetting them in a `try...finally` block can cause non-deterministic failures depending on test execution order.
- **No Implementation Edits Undertaken**: In accordance with the Explorer role, no source or test files outside `.agents/teamwork/teamwork_explorer_remediation_3/` were modified. The proposed fixes below are concrete code recipes for the Worker.

---

## 4. Conclusion & Surgical Fix Recommendations

### Remediation 1: `tests/test_player_editor.py`
**File**: `tests/test_player_editor.py:75`  
**Change**:
```python
<<<<
        self.assertTrue(self.app.backups[0].startswith("player_config.backup_"))
====
        self.assertTrue(
            self.app.backups[0].startswith("player_config.backup_") or
            self.app.backups[0].startswith("player_config.json.backup_")
        )
>>>>
```

---

### Remediation 2: `HitboxRegistry` Cache Reset & Test Isolation
**File 1**: `tests/conftest.py` (Add autouse reset fixture)  
```python
@pytest.fixture(autouse=True)
def reset_hitbox_registry_cache():
    """Ensure HitboxRegistry in-memory cache is pristine across all test boundaries."""
    from src.game.entities.hitbox_registry import HitboxRegistry
    HitboxRegistry._cached_config = {}
    HitboxRegistry._rollback_checkpoint = {}
    yield
    HitboxRegistry._cached_config = {}
    HitboxRegistry._rollback_checkpoint = {}
```

**File 2**: `tests/test_editor_plugins_roundtrip_integrity.py:510-527` (Wrap in try/finally)
```python
        orig_cache = copy.deepcopy(HitboxRegistry._cached_config)
        try:
            HitboxRegistry.update_margins(
                "player",
                HitboxMargins(left=9, right=9, top=14, bottom=0, ground_offset=0, scale=1.0)
            )

            for step in range(1, 8):
                fake_ts = 1700000000 + (step * 15)
                with patch("time.time", return_value=fake_ts):
                    HitboxRegistry.save_all()

            with open(tmp_target, "r", encoding="utf-8") as f:
                saved = json.load(f)

            assert "external_custom_prop" in saved
            assert saved["external_custom_prop"]["left"] == 4
            assert saved["player"]["left"] == 9
            _assert_backups_clean_and_capped(tmp_target, max_backups=5)
        finally:
            HitboxRegistry._cached_config = orig_cache
            HitboxRegistry._rollback_checkpoint = {}
```

---

### Remediation 3: `SideNotification.clear()` Method
**File**: `src/game/ui/side_notification.py:105`  
**Add Method**:
```python
    def clear(self) -> None:
        """Reset the notification state, dismiss any active display, and purge queued items."""
        self._state = NotificationState.IDLE
        self._timer = 0.0
        self._current_item = None
        self._queue.clear()
        self._current_tab_surface = None
        self._cached_icon = None
```

---

### Remediation 4: Circular Mock in Adversarial & Round-Trip Tests + `LevelEditor.commit()`
**File 1**: `tests/test_editor_plugins_adversarial_m2.py:155-157`  
```python
<<<<
            with patch("time.time", return_value=fake_ts):
                # Temporarily patch the hardcoded minion path inside confirm_save_config
                with patch("os.path.exists", side_effect=lambda p: True if p in (boss_config_path, minion_config_path) else os.path.exists(p)):
====
            with patch("time.time", return_value=fake_ts):
                orig_exists = os.path.exists
                with patch("os.path.exists", side_effect=lambda p: True if p in (boss_config_path, minion_config_path) else orig_exists(p)):
>>>>
```

**File 2**: `tests/test_editor_plugins_roundtrip_integrity.py:345-348`  
```python
<<<<
                with patch("builtins.open", side_effect=isolated_open), \
                     patch("os.path.exists", side_effect=lambda p: True if p in (boss_path, minion_path, "game_data/enemy_skeleton_minion_config.json") else os.path.exists(p)), \
                     patch("boss_editor.ConfigClient", create=True):
====
                orig_exists = os.path.exists
                with patch("builtins.open", side_effect=isolated_open), \
                     patch("os.path.exists", side_effect=lambda p: True if p in (boss_path, minion_path, "game_data/enemy_skeleton_minion_config.json") else orig_exists(p)), \
                     patch("boss_editor.ConfigClient", create=True):
>>>>
```

**File 3**: `level_editor.py:2460`  
```python
<<<<
        self.level_data = disk_data
        self.level_backup = copy.deepcopy(self.level_data)
        self.reg_del = set()
        self.modal = None
====
        self.level_data = disk_data
        self.level_backup = copy.deepcopy(self.level_data)
        self.pending = copy.deepcopy(merged_events)
        self.reg_del = set()
        self.modal = None
>>>>
```

---

## 5. Verification Method

To verify all 4 remediations once implemented by the Worker:

1. **Verify Player Editor**:
   ```powershell
   $env:PYTHONPATH="."
   .\.venv\Scripts\python.exe -m pytest tests/test_player_editor.py -v
   ```
   *Expected*: `test_save_and_backup_transaction` and all 8 tests pass (100%).

2. **Verify Engine Presentation & Ground Alignment**:
   ```powershell
   $env:PYTHONPATH="."
   .\.venv\Scripts\python.exe -m pytest tests/test_engine_presentation.py -v
   ```
   *Expected*: `test_player_ground_y_matches_level_ground` passes (100%).

3. **Verify Tier 5 Adversarial Stress & GameState Triggers**:
   ```powershell
   $env:PYTHONPATH="."
   .\.venv\Scripts\python.exe -m pytest tests/test_tier5_adversarial_stress.py tests/test_game_state_popup_triggers.py -v
   ```
   *Expected*: `test_missing_fields_in_scene_definitions` passes without `AttributeError: clear`.

4. **Verify Adversarial Plugins M2**:
   ```powershell
   $env:PYTHONPATH="."
   .\.venv\Scripts\python.exe -m pytest tests/test_editor_plugins_adversarial_m2.py -v
   ```
   *Expected*: No `RecursionError` on `test_adversarial_boss_editor_atomic_save_and_backup_cap` and no text clobber on `test_adversarial_level_editor_commit_atomic_merge_and_backups`.

5. **Full Regression Suite**:
   ```powershell
   $env:PYTHONPATH="."
   .\.venv\Scripts\python.exe -m pytest tests/ -q
   ```
   *Expected*: Zero regressions across all 500 tests.
