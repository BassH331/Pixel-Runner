# Handoff Report: Editor Plugin Remediation Investigation

**Agent**: Explorer Remediation 2 (`teamwork_explorer_remediation_2`)  
**Mission**: Deep investigation of editor plugin multi-commit data clobbering and external key retention defects  
**Date**: 2026-10-28T20:23:00Z  

---

## 1. Observation

### Observation 1: `level_editor.py:commit()` Multi-Commit Data Clobbering Bug
- **File**: `level_editor.py`
- **Lines**: 2406–2463
- **Verbatim Code in `level_editor.py`**:
  ```python
  2415:         # Smart 3-way merge for world_events to preserve external plugin modifications (e.g. from The Eye)
  2416:         backup_events_map = {str(e.get("id")): e for e in self.level_backup.get("world_events", []) if e.get("id") is not None}
  2417:         disk_events_map = {str(e.get("id")): e for e in disk_data.get("world_events", []) if e.get("id") is not None}
  2418: 
  2419:         merged_events = []
  2420:         for ev in copy.deepcopy(self.pending):
  2421:             eid = str(ev.get("id")) if ev.get("id") is not None else None
  2422:             if eid and eid in disk_events_map:
  ...
  2435:                 # 3-way text merge: if user in LevelEditor did not change text, take disk update
  2436:                 if ev_params.get("text") == backup_params.get("text") and "text" in disk_params:
  2437:                     ev_params["text"] = disk_params["text"]
  ...
  2444:             merged_events.append(ev)
  2445: 
  2446:         disk_data["world_events"] = merged_events
  ...
  2455:         from src.game.utils.atomic_save import atomic_write_json
  2456:         atomic_write_json(target_path, disk_data, indent=4, backup=True, max_backups=5)
  2457: 
  2458:         HitboxRegistry.commit_transaction()
  2459:         self.level_data = disk_data
  2460:         self.level_backup = copy.deepcopy(self.level_data)
  2461:         self.reg_del = set()
  2462:         self.modal = None
  ```
- **Failing Test**: `tests/test_editor_plugins_adversarial_m2.py:284` (`test_adversarial_level_editor_commit_atomic_merge_and_backups`)
- **Verbatim Failure Output**:
  ```text
  tests\test_editor_plugins_adversarial_m2.py:284: in test_adversarial_level_editor_commit_atomic_merge_and_backups
      book_event = next(e for e in committed["world_events"] if e.get("id") == 10)
  >   assert book_event["params"]["text"] == "External Plugin Dialogue Update"
  E   AssertionError: assert 'Initial book text' == 'External Plugin Dialogue Update'
  E     - External Plugin Dialogue Update
  E     + Initial book text
  ```
- **Empirical Execution**: Running `test_adversarial_level_editor_commit_atomic_merge_and_backups` with a monkeypatched `commit()` that updates `self.pending = copy.deepcopy(disk_data["world_events"])` passed immediately (`1 passed, 4 deselected in 12.13s`).

---

### Observation 2: `ControlsManager.save_config()` Drops External Top-Level Keys
- **File**: `src/game/controls_manager.py`
- **Lines**: 137–150
- **Verbatim Code in `src/game/controls_manager.py`**:
  ```python
  137:     def save_config(self) -> bool:
  138:         """Save active configuration to local JSON file atomically."""
  139:         data = {
  140:             "active_mode": self.mode,
  141:             "keyboard_bindings": self.keyboard_bindings,
  142:             "joystick_bindings": self.joystick_bindings,
  143:         }
  144:         try:
  145:             from src.game.utils.atomic_save import atomic_write_json
  146:             return atomic_write_json(CONFIG_PATH, data, indent=4)
  147:         except Exception as e:
  148:             print(f"[ControlsManager] Failed to save controls config: {e}")
  149:             return False
  ```
- **Failing Test**: `tests/test_editor_plugins_roundtrip_integrity.py:591` (`test_controls_manager_roundtrip_and_key_preservation`)
- **Verbatim Failure Output**:
  ```text
  tests\test_editor_plugins_roundtrip_integrity.py:591: in test_controls_manager_roundtrip_and_key_preservation
  >   assert saved["external_axis_calibration"] == {"deadzone_radial": 0.12}
  E   KeyError: 'external_axis_calibration'
  ```
- **Disk File Reference**: `src/game/utils/atomic_save.py:129-168` provides `atomic_merge_json(file_path, new_data, domain_keys=..., indent=4, backup=True, max_backups=5)` specifically designed to re-read existing disk contents and update only domain keys while preserving unowned root keys.

---

### Observation 3: `ShadowRegistry` Corrupts Non-Profile Top-Level Keys
- **File**: `src/game/systems/shadow_registry.py`
- **Lines**: 130–143 & 170–190
- **Verbatim Code in `src/game/systems/shadow_registry.py`**:
  ```python
  136:                 data = json.load(f)
  137:                 loaded: dict[str, ShadowProfile] = {}
  138:                 for k, v in data.items():
  139:                     if isinstance(v, dict):
  140:                         loaded[cls.normalize_key(k)] = ShadowProfile.from_dict(v)
  141:                 cls._cache = loaded
  ...
  170:     @classmethod
  171:     def save_profile(cls, key: str, profile: ShadowProfile) -> bool:
  ...
  179:         data = {k: v.to_dict() for k, v in cls._cache.items()}
  180: 
  181:         try:
  182:             from src.game.utils.atomic_save import atomic_merge_json
  183:             success, _ = atomic_merge_json(CONFIG_PATH, data, indent=4)
  ```
- **Failing Test**: `tests/test_editor_plugins_roundtrip_integrity.py:665` (`test_shadow_registry_roundtrip_and_key_preservation`)
- **Verbatim Failure Output**:
  ```text
  tests\test_editor_plugins_roundtrip_integrity.py:665: in test_shadow_registry_roundtrip_and_key_preservation
  >   assert saved["external_shadow_layer"] == {"depth_bias": 0.05, "render_queue": 2000}
  E   AssertionError: assert {'alpha': 120, 'fade_height': 250.0, 'ground_snap': 12.0, 'scale_mult': 1.0, 'squash_ratio': 0.25, 'y_offset': 0} == {'depth_bias': 0.05, 'render_queue': 2000}
  ```
- **Corrupted Structure**: `ShadowProfile.from_dict(v)` ignores the unknown keys (`"depth_bias"`, `"render_queue"`) and populates default shadow parameters (`alpha=120`, `squash_ratio=0.25`, etc.). `save_profile()` subsequently writes this coerced dictionary back to disk.

---

### Observation 4: Mock Recursion Bug in Adversarial and Roundtrip Test Suites
- **Files**:
  - `tests/test_editor_plugins_adversarial_m2.py:121`
  - `tests/test_editor_plugins_roundtrip_integrity.py:347`
- **Verbatim Code**:
  ```python
  with patch("os.path.exists", side_effect=lambda p: True if p in (boss_config_path, minion_config_path) else os.path.exists(p)):
  ```
- **Verbatim Failure Output**:
  ```text
  RecursionError: maximum recursion depth exceeded
  ```
- **Root Cause**: The mock function inside `side_effect` calls `os.path.exists(p)` directly, which triggers the mock itself recursively without an exit condition.

---

## 2. Logic Chain

### Logic Chain 1: Multi-Commit Dialogue Clobbering in `level_editor.py`
1. **Premise**: In `level_editor.py`, `self.level_backup` acts as the base version for 3-way conflict resolution, `self.pending` represents the editor working copy, and `disk_data` represents the current file on disk.
2. **First Commit**:
   - `self.pending` contains Event 10 with `"text": "Initial book text"`.
   - `self.level_backup` contains Event 10 with `"text": "Initial book text"`.
   - `disk_data` contains Event 10 with external update `"text": "External Plugin Dialogue Update"`.
   - 3-way merge logic (line 2436): `ev_params.get("text") == backup_params.get("text")` is `True` ("Initial book text" == "Initial book text"). The external disk text is adopted into `merged_events`.
   - Lines 2459–2460: `self.level_data = disk_data`, `self.level_backup = copy.deepcopy(self.level_data)`. Now `self.level_backup` contains `"External Plugin Dialogue Update"`.
   - Crucially, `self.pending` is NOT updated! `self.pending` still contains `"Initial book text"`.
3. **Second Commit**:
   - `self.pending` still contains `"Initial book text"`.
   - `self.level_backup` now contains `"External Plugin Dialogue Update"`.
   - `disk_data` contains `"External Plugin Dialogue Update"`.
   - 3-way merge logic (line 2436): `ev_params.get("text") == backup_params.get("text")` is evaluated: `"Initial book text" == "External Plugin Dialogue Update"` -> `False`!
   - Because they do not match, the algorithm interprets the disparity as an intentional user edit reverting the text back to `"Initial book text"`.
   - The external text is rejected, and `"Initial book text"` is written to disk, overwriting the external modification.
4. **Remediation**:
   - After `atomic_write_json()` succeeds at line 2456, synchronize `self.pending`:
     ```python
     self.level_data = disk_data
     self.level_backup = copy.deepcopy(self.level_data)
     self.pending = copy.deepcopy(disk_data["world_events"])
     self.pending.sort(key=self._event_dist_key)
     ```
   - This guarantees that for all subsequent commits, `self.pending` matches `self.level_backup` until the user actively edits an event in the editor UI.

---

### Logic Chain 2: External Key Loss in `ControlsManager.save_config()`
1. **Premise**: Requirements stipulate that all configuration files must preserve external unowned root keys during persistence operations.
2. **Execution Trace**:
   - `ControlsManager.save_config()` constructs a hardcoded dictionary consisting only of `"active_mode"`, `"keyboard_bindings"`, and `"joystick_bindings"`.
   - It directly calls `atomic_write_json(CONFIG_PATH, data, indent=4)`.
   - Any external keys present on disk (such as `"external_axis_calibration"`) are completely omitted from `data`, resulting in complete data loss when `atomic_write_json` replaces the file.
3. **Remediation**:
   - Replace the direct write with `atomic_merge_json`:
     ```python
     from src.game.utils.atomic_save import atomic_merge_json
     success, _ = atomic_merge_json(
         CONFIG_PATH,
         data,
         domain_keys=["active_mode", "keyboard_bindings", "joystick_bindings"],
         indent=4,
         backup=True,
         max_backups=5,
     )
     return success
     ```
   - `atomic_merge_json` reads fresh disk content, updates only the 3 specified domain keys, retains all unowned keys (like `"external_axis_calibration"`), creates validated backups, and caps rolling backups to 5.

---

### Logic Chain 3: Key Coercion & Corruption in `ShadowRegistry`
1. **Premise**: `game_data/shadow_config.json` stores shadow profiles for game entities, but external plugins and toolchains may store arbitrary metadata keys (e.g. `"external_shadow_layer": {"depth_bias": 0.05, "render_queue": 2000}`).
2. **Execution Trace**:
   - In `_check_reload()` (line 139): `for k, v in data.items(): if isinstance(v, dict): loaded[...] = ShadowProfile.from_dict(v)`.
   - Because `v` is a dictionary, `ShadowRegistry` forces it through `ShadowProfile.from_dict()`. Missing fields are replaced by default values (`alpha=120`, etc.), and unrecognized keys (`depth_bias`, `render_queue`) are silently dropped.
   - In `save_profile()` (line 180): `data = {k: v.to_dict() for k, v in cls._cache.items()}` serializes every item in `cls._cache` as a `ShadowProfile`.
   - `atomic_merge_json(CONFIG_PATH, data)` without `domain_keys` executes `merged.update(data)`, replacing the true disk structure of `"external_shadow_layer"` with the default `ShadowProfile` representation.
3. **Remediation**:
   - Differentiate genuine shadow profile dictionaries from external metadata. A dictionary represents a shadow profile if its normalized key is in `cls.DEFAULTS` or if it contains core shadow attributes (`"alpha"`, `"squash_ratio"`, `"fade_height"`, `"ground_snap"`, `"scale_mult"`).
   - In `_check_reload()`, separate entries into `_cache` (valid `ShadowProfile` instances) and `_unowned_keys` (raw dictionaries and external types).
   - In `save_profile()`, assemble `data` starting from `_unowned_keys` and updating with active `_cache` profiles, and call `atomic_merge_json` with `backup=True, max_backups=5`.

---

## 3. Caveats

1. **Other Failing Tests Documented by Auditor**:
   - While our mission focuses on `level_editor.py`, `controls_manager.py`, and `shadow_registry.py`, test execution revealed that `tests/test_editor_plugins_adversarial_m2.py` and `tests/test_editor_plugins_roundtrip_integrity.py` have unrelated unit test mock flaws (such as the `os.path.exists` mock recursion in `test_adversarial_boss_editor_atomic_save_and_backup_cap`). These must also be corrected in the test files by the test remediation worker to achieve 100% test pass rate.
2. **Singleton State in `ControlsManager`**:
   - `ControlsManager` implements the singleton pattern (`_instance`). In long-running test suites or multiple test runs, modifying `CONFIG_PATH` via `monkeypatch` requires `save_config()` to reliably read from `CONFIG_PATH` dynamically at runtime. Using `atomic_merge_json(CONFIG_PATH, ...)` guarantees fresh disk reads without requiring singleton destruction.

---

## 4. Conclusion & Surgical Recommendations

### 4.1 Surgical Fix 1: `level_editor.py`
**File**: `level_editor.py`  
**Location**: Lines 2458–2463  
**Change Description**: Update `self.pending` with the newly committed `world_events` so subsequent 3-way merges recognize external updates rather than reverting them.

```python
<<<<
        HitboxRegistry.commit_transaction()
        self.level_data = disk_data
        self.level_backup = copy.deepcopy(self.level_data)
        self.reg_del = set()
        self.modal = None
====
        HitboxRegistry.commit_transaction()
        self.level_data = disk_data
        self.level_backup = copy.deepcopy(self.level_data)
        self.pending = copy.deepcopy(disk_data["world_events"])
        self.pending.sort(key=self._event_dist_key)
        self.reg_del = set()
        self.modal = None
>>>>
```

---

### 4.2 Surgical Fix 2: `src/game/controls_manager.py`
**File**: `src/game/controls_manager.py`  
**Location**: Lines 137–150  
**Change Description**: Replace direct `atomic_write_json` with `atomic_merge_json` specifying domain keys to preserve external top-level keys like `external_axis_calibration` and enforce backup pruning.

```python
<<<<
    def save_config(self) -> bool:
        """Save active configuration to local JSON file atomically."""
        data = {
            "active_mode": self.mode,
            "keyboard_bindings": self.keyboard_bindings,
            "joystick_bindings": self.joystick_bindings,
        }
        try:
            from src.game.utils.atomic_save import atomic_write_json
            return atomic_write_json(CONFIG_PATH, data, indent=4)
        except Exception as e:
            print(f"[ControlsManager] Failed to save controls config: {e}")
            return False
====
    def save_config(self) -> bool:
        """Save active configuration to local JSON file atomically, preserving external keys."""
        data = {
            "active_mode": self.mode,
            "keyboard_bindings": self.keyboard_bindings,
            "joystick_bindings": self.joystick_bindings,
        }
        try:
            from src.game.utils.atomic_save import atomic_merge_json
            success, _ = atomic_merge_json(
                CONFIG_PATH,
                data,
                domain_keys=["active_mode", "keyboard_bindings", "joystick_bindings"],
                indent=4,
                backup=True,
                max_backups=5,
            )
            return success
        except Exception as e:
            print(f"[ControlsManager] Failed to save controls config: {e}")
            return False
>>>>
```

---

### 4.3 Surgical Fix 3: `src/game/systems/shadow_registry.py`
**File**: `src/game/systems/shadow_registry.py`  
**Location**: Lines 52–56, 137–142, and 170–190  
**Change Description**: Add `_unowned_keys` dictionary, filter out non-shadow profile items during `_check_reload()`, and merge unowned keys cleanly during `save_profile()`.

```python
<<<<
class ShadowRegistry:
    """
    Registry for entity shadow profiles.
    Caches profiles in memory and automatically reloads when shadow_config.json changes.
    """

    _cache: dict[str, ShadowProfile] = {}
    _last_mtime: float = -1.0
====
class ShadowRegistry:
    """
    Registry for entity shadow profiles.
    Caches profiles in memory and automatically reloads when shadow_config.json changes.
    """

    _cache: dict[str, ShadowProfile] = {}
    _unowned_keys: dict[str, Any] = {}
    _last_mtime: float = -1.0
>>>>
```

And in `_is_shadow_profile_data()`, `_check_reload()`, and `save_profile()`:
```python
<<<<
                loaded: dict[str, ShadowProfile] = {}
                for k, v in data.items():
                    if isinstance(v, dict):
                        loaded[cls.normalize_key(k)] = ShadowProfile.from_dict(v)
                cls._cache = loaded
                cls._last_mtime = mtime
====
                loaded: dict[str, ShadowProfile] = {}
                unowned: dict[str, Any] = {}
                profile_fields = {"alpha", "squash_ratio", "fade_height", "ground_snap", "scale_mult"}
                for k, v in data.items():
                    norm_k = cls.normalize_key(k)
                    if isinstance(v, dict) and (norm_k in cls.DEFAULTS or any(pk in v for pk in profile_fields)):
                        loaded[norm_k] = ShadowProfile.from_dict(v)
                    else:
                        unowned[k] = v
                cls._cache = loaded
                cls._unowned_keys = unowned
                cls._last_mtime = mtime
>>>>
```

```python
<<<<
    @classmethod
    def save_profile(cls, key: str, profile: ShadowProfile) -> bool:
        """
        Save or update a shadow profile in game_data/shadow_config.json atomically.
        """
        cls._check_reload()
        norm_key = cls.normalize_key(key)
        cls._cache[norm_key] = profile

        # Prepare full dictionary for disk serialization
        data = {k: v.to_dict() for k, v in cls._cache.items()}

        try:
            from src.game.utils.atomic_save import atomic_merge_json
            success, _ = atomic_merge_json(CONFIG_PATH, data, indent=4)
            if success and os.path.exists(CONFIG_PATH):
                cls._last_mtime = os.path.getmtime(CONFIG_PATH)
            return success
        except Exception as e:
            print(f"[ShadowRegistry] Failed to save {CONFIG_PATH}: {e}")
            return False
====
    @classmethod
    def save_profile(cls, key: str, profile: ShadowProfile) -> bool:
        """
        Save or update a shadow profile in game_data/shadow_config.json atomically.
        """
        cls._check_reload()
        norm_key = cls.normalize_key(key)
        cls._cache[norm_key] = profile

        # Prepare full dictionary for disk serialization, preserving unowned keys
        data = dict(cls._unowned_keys)
        for k, v in cls._cache.items():
            data[k] = v.to_dict()

        try:
            from src.game.utils.atomic_save import atomic_merge_json
            success, _ = atomic_merge_json(
                CONFIG_PATH,
                data,
                indent=4,
                backup=True,
                max_backups=5,
            )
            if success and os.path.exists(CONFIG_PATH):
                cls._last_mtime = os.path.getmtime(CONFIG_PATH)
            return success
        except Exception as e:
            print(f"[ShadowRegistry] Failed to save {CONFIG_PATH}: {e}")
            return False
>>>>
```

---

### 4.4 Surgical Fix 4: Test Suite Mock Recursion (For Test Worker)
**Files**:
- `tests/test_editor_plugins_adversarial_m2.py:157`
- `tests/test_editor_plugins_roundtrip_integrity.py:347`
**Change**: Capture the original `os.path.exists` before patching to prevent indefinite recursion.
```python
orig_exists = os.path.exists
with patch("os.path.exists", side_effect=lambda p: True if p in (boss_config_path, minion_config_path) else orig_exists(p)):
```

---

## 5. Verification Method

Once the Worker applies the above surgical changes, independently verify the fixes by running the following commands:

```powershell
# 1. Verify level_editor 3-way merge and multi-commit retention
.\.venv\Scripts\python.exe -m pytest tests/test_editor_plugins_adversarial_m2.py -k "test_adversarial_level_editor_commit_atomic_merge_and_backups" -v

# 2. Verify controls_manager unowned key retention and backup cap
.\.venv\Scripts\python.exe -m pytest tests/test_editor_plugins_roundtrip_integrity.py -k "test_controls_manager_roundtrip_and_key_preservation" -v

# 3. Verify shadow_registry unowned key retention and profile preservation
.\.venv\Scripts\python.exe -m pytest tests/test_editor_plugins_roundtrip_integrity.py -k "test_shadow_registry_roundtrip_and_key_preservation" -v

# 4. Invalidation Condition:
# If assert saved["external_axis_calibration"] raises KeyError, ControlsManager.save_config() is still using atomic_write_json rather than atomic_merge_json.
# If assert saved["external_shadow_layer"] returns a dictionary with 'alpha' or 'fade_height', ShadowRegistry is still coercing non-profile dictionaries.
# If book_event["params"]["text"] == "Initial book text", level_editor.py:commit() has not updated self.pending.
```
