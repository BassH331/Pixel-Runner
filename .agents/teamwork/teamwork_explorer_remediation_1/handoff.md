# Forensic Remediation Investigation Report: Test Suite & Editor Plugin Integrity Failures

**Investigator**: Explorer Remediation 1 (`teamwork_explorer_remediation_1`)  
**Scope**: 10 Failures in `tests/test_game_state_popup_triggers.py` and `tests/test_editor_plugins_roundtrip_integrity.py`  
**Working Directory**: `c:\Users\me\Documents\game\Pixel-Runner\.agents\teamwork\teamwork_explorer_remediation_1\`  
**Timestamp**: 2026-10-28T20:24:00Z  

---

## Executive Summary

A comprehensive, read-only forensic investigation into the 10 failed test cases across `tests/test_game_state_popup_triggers.py` and `tests/test_editor_plugins_roundtrip_integrity.py` was conducted. Every failure was traced to its exact line of code and root mechanism.

The 10 failures decompose into three distinct archetypes:
1. **Test Verification & Mock Flaws (3 failures)**:
   - Line-matching logic flagging the Python function definition `def _update_boss_combat_taunts` rather than call sites.
   - Uncaptured recursion in `unittest.mock.patch("os.path.exists", ...)` where the lambda invoked the active mock recursively.
   - Non-existent configuration key lookup `corruption_thresholds` in `game_data/storyline_config.json`.
2. **Test Inaccurate API / Typo Assumptions (4 failures)**:
   - Non-existent class `wave_editor.App` (actual: `WaveEditorApp`) plus missing runtime attributes (`level_files`, `level_data`, `modal`).
   - Calling `PopupSceneManager.load_config(tmp_target)` with a positional path argument when `load_config` takes only `self`.
   - Importing non-existent class `Slider` from `blood_zombie_editor` (actual: `MetaphorSlider`).
   - Calling non-existent method `save_all()` on `TheEyePerceptionManager` (actual: `save_perception()`).
3. **Genuine Architecture & Data Integrity Bugs (3 failures)**:
   - `SideNotification` lacking a `clear()` reset method, causing `AttributeError` in both `test_game_state_popup_triggers.py` and `test_tier5_adversarial_stress.py`.
   - `ControlsManager.save_config()` overwriting external keys via unmerged `atomic_write_json`.
   - `ShadowRegistry._check_reload()` and `save_profile()` coercing non-shadow dictionary keys into default `ShadowProfile` objects, corrupting unowned configuration layers.

---

## 1. Observation

### Observation 1.1: `test_silenced_systems_remain_disabled` Flagging Method Definition
- **File**: `tests/test_game_state_popup_triggers.py`, lines 286-302
- **Inspected Target**: `src/game/states/game_state.py`, line 826 and line 1476
- **Verbatim Error**:
  ```text
  AssertionError: Found active uncommented boss combat taunts calls in game_state.py: [(826, 'def _update_boss_combat_taunts(self, dt: float) -> None:')]
  ```
- **Code in Test**:
  ```python
  uncommented_taunts = []
  commented_found = False
  for idx, line in enumerate(lines, start=1):
      stripped = line.strip()
      if "_update_boss_combat_taunts" in stripped:
          if stripped.startswith("#"):
              commented_found = True
          else:
              uncommented_taunts.append((idx, stripped))
  ```
- **Code in Target**:
  - Line 826: `    def _update_boss_combat_taunts(self, dt: float) -> None:`
  - Line 1476: `        # self._update_boss_combat_taunts(dt)`
- **Observation Detail**: The test checks for the presence of `_update_boss_combat_taunts`. Line 826 is the method declaration. Because line 826 does not start with `#`, it was treated as an active call site and appended to `uncommented_taunts`, causing `assert len(uncommented_taunts) == 0` to fail.

---

### Observation 1.2: `test_side_notification_headless_rendering_all_scenes` Missing `clear()` Method
- **File**: `tests/test_game_state_popup_triggers.py`, line 462
- **Inspected Target**: `src/game/ui/side_notification.py`, lines 1-526
- **Verbatim Error**:
  ```text
  AttributeError: 'SideNotification' object has no attribute 'clear'
  ```
- **Code in Test**:
  ```python
  sn.update(0.1)
  sn.update(1.0)
  sn.clear()
  ```
- **Observation Detail**:
  `SideNotification` defines `__init__`, `is_active`, `_apply_config`, `_compute_scaling`, `show`, `_start_item`, `_load_icon_surface`, `_wrap_text`, `_build_tab_surface`, `update`, and `draw`. It defines no `clear()` or teardown method.
  Additionally, `tests/test_tier5_adversarial_stress.py` line 140 invokes `sn.clear()`, resulting in the identical failure (`test_missing_fields_in_scene_definitions`).

---

### Observation 1.3: `test_popup_scene_manager_roundtrip_and_key_preservation` Invalid Method Signature
- **File**: `tests/test_editor_plugins_roundtrip_integrity.py`, lines 103-104
- **Inspected Target**: `src/game/systems/popup_scene_manager.py`, lines 36-40, 47-56
- **Verbatim Error**:
  ```text
  TypeError: PopupSceneManager.load_config() takes 1 positional argument but 2 were given
  ```
- **Code in Test**:
  ```python
  PopupSceneManager.reset_instance()
  mgr = PopupSceneManager.get_instance()
  mgr.load_config(tmp_target)
  ```
- **Code in Target**:
  ```python
  @classmethod
  def get_instance(cls, config_path: str = DEFAULT_SCENE_POPUPS_PATH) -> PopupSceneManager:
      if cls._instance is None:
          cls._instance = cls(config_path=config_path)
      return cls._instance

  def __init__(self, config_path: str = DEFAULT_SCENE_POPUPS_PATH) -> None:
      self.config_path = config_path
      ...
      self.load_config()

  def load_config(self) -> bool:
      ...
  ```
- **Observation Detail**: `PopupSceneManager.load_config()` is declared as `def load_config(self) -> bool:` without accepting parameters. Custom paths must be passed to `get_instance(config_path=...)` or `PopupSceneManager(config_path=...)`.

---

### Observation 1.4: `test_wave_editor_roundtrip_and_key_preservation` Missing Class & State Invariants
- **File**: `tests/test_editor_plugins_roundtrip_integrity.py`, line 196
- **Inspected Target**: `wave_editor.py`, lines 191, 246-265
- **Verbatim Error**:
  ```text
  AttributeError: module 'wave_editor' has no attribute 'App'
  ```
- **Code in Test**:
  ```python
  app = wave_editor.App.__new__(wave_editor.App)
  app.level_file = tmp_target
  app.pending = copy.deepcopy(data.get("spawn_zones", []))
  ...
  app.commit()
  ```
- **Code in Target**:
  - `wave_editor.py` line 191 defines `class WaveEditorApp:`. There is no class `App`.
  - In `WaveEditorApp.commit(self)` (lines 246-264):
    ```python
    def commit(self):
        target_path = self.level_files[self.active_idx]
        disk_data = copy.deepcopy(self.level_data)
        ...
        self.level_data = disk_data
        self.level_backup = copy.deepcopy(self.level_data)
        self.modal = None
    ```
- **Observation Detail**: If `App` is simply changed to `WaveEditorApp`, `app.commit()` will fail immediately with `AttributeError: 'WaveEditorApp' object has no attribute 'level_files'` because the test set `app.level_file` instead of `app.level_files = [tmp_target]`, `app.active_idx = 0`, `app.level_data = copy.deepcopy(data)`, and `app.modal = None`.

---

### Observation 1.5: `test_boss_editor_roundtrip_and_key_preservation` Circular Mock Infinite Recursion
- **File**: `tests/test_editor_plugins_roundtrip_integrity.py`, lines 346-349
- **Also in**: `tests/test_editor_plugins_adversarial_m2.py`, line 157
- **Inspected Target**: `boss_editor.py`, lines 996-1008; `src/game/utils/atomic_save.py`, lines 55, 96
- **Verbatim Error**:
  ```text
  RecursionError: maximum recursion depth exceeded
  ```
- **Code in Test**:
  ```python
  with patch("builtins.open", side_effect=isolated_open), \
       patch("os.path.exists", side_effect=lambda p: True if p in (boss_path, minion_path, "game_data/enemy_skeleton_minion_config.json") else os.path.exists(p)), \
       patch("boss_editor.ConfigClient", create=True):
      app.confirm_save_config()
  ```
- **Observation Detail**: Inside the lambda `side_effect`, the expression `else os.path.exists(p)` evaluates the current patched mock attribute on `os.path`. Whenever `os.path.exists` is checked for backup files or directory paths, the lambda invokes itself recursively until Python's call stack exhausts. In contrast, `isolated_open` properly captured `orig_open = open` before patching.

---

### Observation 1.6: `test_blood_zombie_editor_roundtrip_and_key_preservation` Class Import Mismatch
- **File**: `tests/test_editor_plugins_roundtrip_integrity.py`, line 406
- **Inspected Target**: `blood_zombie_editor.py`, lines 72-91, 577-582
- **Verbatim Error**:
  ```text
  ImportError: cannot import name 'Slider' from 'blood_zombie_editor'
  ```
- **Code in Test**:
  ```python
  from blood_zombie_editor import BloodZombieEditorApp, Slider
  ...
  app.sliders = {
      "scale": Slider("scale", "Scale", 0, 0, 100, 1.0, 4.0, 2.25, True),
      "ground_offset": Slider("ground_offset", "Ground", 0, 0, 100, -50, 50, 10, False),
  }
  ```
- **Code in Target**:
  - `blood_zombie_editor.py` line 72 declares `class MetaphorSlider:`. No class named `Slider` is declared.
  - `MetaphorSlider.__init__` signature:
    ```python
    def __init__(
        self,
        key: str,
        metaphor_label: str,
        tech_label: str,
        formula: str,
        x: int,
        y: int,
        w: int,
        min_val: float,
        max_val: float,
        current_val: float,
        is_float: bool = True,
        format_str: str = "{val}",
        unit: str = "",
    ):
    ```
- **Observation Detail**: The test attempted to import generic `Slider`. The specialized UI component in `blood_zombie_editor.py` is `MetaphorSlider`. In `save_config_file()`, the editor accesses only `slider.val`.

---

### Observation 1.7: `test_the_eye_roundtrip_and_key_preservation` Missing `save_all()` Method
- **File**: `tests/test_editor_plugins_roundtrip_integrity.py`, line 477
- **Inspected Target**: `src/game/systems/the_eye_manager.py`, line 1577
- **Verbatim Error**:
  ```text
  AttributeError: 'TheEyePerceptionManager' object has no attribute 'save_all'
  ```
- **Code in Test**:
  ```python
  mgr.save_all()
  ```
- **Code in Target**:
  Line 1577:
  ```python
  def save_perception(self) -> Tuple[bool, str]:
      """Persist all perception/conversation modifications back to disk..."""
  ```
- **Observation Detail**: `TheEyePerceptionManager` implements persistence via `save_perception()`. It does not declare `save_all()`.

---

### Observation 1.8: `test_controls_manager_roundtrip_and_key_preservation` External Keys Dropped
- **File**: `tests/test_editor_plugins_roundtrip_integrity.py`, line 591
- **Inspected Target**: `src/game/controls_manager.py`, lines 137-149
- **Verbatim Error**:
  ```text
  KeyError: 'external_axis_calibration'
  ```
- **Code in Test**:
  ```python
  data["external_axis_calibration"] = {"deadzone_radial": 0.12}
  ...
  assert mgr.save_config() is True
  ...
  assert saved["external_axis_calibration"] == {"deadzone_radial": 0.12}
  ```
- **Code in Target**:
  ```python
  def save_config(self) -> bool:
      data = {
          "active_mode": self.mode,
          "keyboard_bindings": self.keyboard_bindings,
          "joystick_bindings": self.joystick_bindings,
      }
      try:
          from src.game.utils.atomic_save import atomic_write_json
          return atomic_write_json(CONFIG_PATH, data, indent=4)
  ```
- **Observation Detail**: `save_config()` instantiates a hardcoded dictionary containing strictly `active_mode`, `keyboard_bindings`, and `joystick_bindings`. It then invokes `atomic_write_json` without merging existing disk data, completely discarding all unowned keys (e.g., `external_axis_calibration`).

---

### Observation 1.9: `test_shadow_registry_roundtrip_and_key_preservation` Data Coercion & Key Clobbering
- **File**: `tests/test_editor_plugins_roundtrip_integrity.py`, line 665
- **Inspected Target**: `src/game/systems/shadow_registry.py`, lines 138-141, 178-189
- **Verbatim Error**:
  ```text
  AssertionError: assert {'alpha': 120, 'fade_height': 250.0, ...} == {'depth_bias': 0.05, 'render_queue': 2000}
  ```
- **Code in Test**:
  ```python
  data["external_shadow_layer"] = {"depth_bias": 0.05, "render_queue": 2000}
  ...
  assert ShadowRegistry.save_profile("player", prof) is True
  ...
  assert saved["external_shadow_layer"] == {"depth_bias": 0.05, "render_queue": 2000}
  ```
- **Code in Target**:
  - In `_check_reload()` (lines 138-141):
    ```python
    for k, v in data.items():
        if isinstance(v, dict):
            loaded[cls.normalize_key(k)] = ShadowProfile.from_dict(v)
    cls._cache = loaded
    ```
  - In `save_profile()` (lines 178-183):
    ```python
    data = {k: v.to_dict() for k, v in cls._cache.items()}
    success, _ = atomic_merge_json(CONFIG_PATH, data, indent=4)
    ```
- **Observation Detail**: When `_check_reload()` reads `shadow_config.json`, it attempts to convert every dictionary under every root key into a `ShadowProfile`. Because `"external_shadow_layer"` does not match shadow fields, `from_dict` constructs a default `ShadowProfile(alpha=120, squash_ratio=0.25, ...)`. When `save_profile` saves, `data` writes back this fabricated profile over `"external_shadow_layer"`.

---

### Observation 1.10: `test_storyline_manager_roundtrip_and_key_preservation` Invalid Schema Key
- **File**: `tests/test_editor_plugins_roundtrip_integrity.py`, line 690
- **Inspected Target**: `game_data/storyline_config.json`, lines 267-272
- **Verbatim Error**:
  ```text
  KeyError: 'corruption_thresholds'
  ```
- **Code in Test**:
  ```python
  mgr.data["corruption"]["corruption_thresholds"]["high"] = 92.0
  ```
- **Code in Target**:
  In `game_data/storyline_config.json`:
  ```json
  "corruption": {
    "dash_speed_multiplier": 1.5,
    "damage_multiplier": 1.5,
    "vignette_alpha": 180,
    "instability_enabled": true
  }
  ```
- **Observation Detail**: The root key `"corruption"` exists, but its child keys are `dash_speed_multiplier`, `damage_multiplier`, `vignette_alpha`, and `instability_enabled`. The key `"corruption_thresholds"` does not exist in the canonical schema.

---

## 2. Logic Chain

1. **Test Verification Integrity**:
   - `test_silenced_systems_remain_disabled` aimed to verify that `self._update_boss_combat_taunts(dt)` was not active in `game_state.py`.
   - In `game_state.py`, line 1476 is commented out (`# self._update_boss_combat_taunts(dt)`), satisfying the silenced systems invariant.
   - However, line 826 declares `def _update_boss_combat_taunts(self, dt: float) -> None:`.
   - By not distinguishing function definitions (`def ...`) from call sites, the test generated a false-positive assertion failure.
   - Filtering lines starting with `def ` allows the test to verify that no active call sites exist without falsely failing on the method declaration.

2. **UI Component Teardown & Lifecycle**:
   - `SideNotification` handles sequential animation cycles (slide in, hold, slide out).
   - In `test_side_notification_headless_rendering_all_scenes`, all pop-up scenes are tested sequentially.
   - The test called `sn.clear()` to reset the component between scenes.
   - Because `SideNotification` lacked a reset method, `AttributeError` was thrown.
   - Implementing `clear(self)` to reset `_state = IDLE`, `_timer = 0.0`, `_current_item = None`, `_queue.clear()`, and `_current_tab_surface = None` provides an authentic teardown mechanism, and moving instance creation into the test loop provides robust per-scene test isolation.

3. **Singleton & Constructor Interface Alignment**:
   - `PopupSceneManager` follows a singleton pattern where `get_instance(config_path)` and `__init__(config_path)` handle loading.
   - `load_config` is an internal zero-argument loader for `self.config_path`.
   - Passing `tmp_target` directly to `mgr.load_config()` violated the signature.
   - Re-initializing via `PopupSceneManager.reset_instance()` and `PopupSceneManager.get_instance(config_path=tmp_target)` adheres to the intended architectural contract.

4. **Editor UI Class & State Dependencies**:
   - In `wave_editor.py`, the application class is `WaveEditorApp`.
   - Its `commit()` method requires `self.level_files[self.active_idx]`, `self.level_data`, and `self.modal = None`.
   - Instantiating `WaveEditorApp` with these exact attributes allows headless execution without launching an interactive Pygame window loop.

5. **Mock Scope & Call Stack Resolution**:
   - In `test_boss_editor_roundtrip_and_key_preservation` and `test_editor_plugins_adversarial_m2`, patching `os.path.exists` without preserving a reference to the unpatched built-in creates an inescapable circular dependency when `os.path.exists` is called on other paths.
   - Storing `orig_exists = os.path.exists` before entering `patch()` guarantees clean fall-through to the operating system's filesystem check.

6. **Domain Model Parity**:
   - `blood_zombie_editor.py` uses `MetaphorSlider` instead of `Slider`.
   - `TheEyePerceptionManager` uses `save_perception()` instead of `save_all()`.
   - Aligning test imports and method calls with the actual production code eliminates artificial attribute errors while providing backwards-compatible aliases where appropriate.

7. **Atomic Persistence & External Key Retention**:
   - Both `ControlsManager.save_config()` and `ShadowRegistry.save_profile()` are required by Milestone 2 and Milestone 3 invariants to retain external unowned keys.
   - In `ControlsManager`, using `atomic_merge_json(CONFIG_PATH, data, indent=4)` automatically re-reads disk data and preserves non-controls configuration keys.
   - In `ShadowRegistry`, passing `domain_keys=[norm_key]` to `atomic_merge_json` ensures only the edited shadow profile is merged, leaving external layers untouched.

8. **Configuration Schema Conformity**:
   - In `game_data/storyline_config.json`, the `"corruption"` section tunes gameplay multipliers (`dash_speed_multiplier`).
   - Mutating `mgr.data["corruption"]["dash_speed_multiplier"] = 2.25` tests canonical JSON round-trip reading and writing without schema mismatches.

---

## 3. Caveats

- **Scope Delimitation**: This report strictly covers the 10 failures in `tests/test_game_state_popup_triggers.py` and `tests/test_editor_plugins_roundtrip_integrity.py`. The related adversarial failures (`test_player_editor.py` backup prefix assertion, `level_editor.py` 3-way commit sync) were cross-referenced to ensure consistent recommendations, but remain under Worker execution scope.
- **Read-Only Invariant**: In accordance with the Teamwork Explorer archetype, no production code or test files were modified during this investigation.
- **Backwards Compatibility**: All proposed fixes recommend both updating the test suite to target canonical APIs AND providing backward-compatible aliases in production classes (`Slider = MetaphorSlider`, `save_all() -> save_perception()`, `clear()`).

---

## 4. Conclusion & Actionable Fix Recommendations

All 10 failures are fully understood, reproducible, and resolvable. The following surgical instructions are provided for the Remediation Worker.

---

### Remediation Specification

#### Fix 1: `tests/test_game_state_popup_triggers.py` (Silenced Systems Method Definition)
- **Target**: `tests/test_game_state_popup_triggers.py`, line 288-295
- **Change**: Skip lines starting with `def ` when searching for uncommented taunt call sites.
- **Code**:
  ```python
  # BEFORE (lines 288-295)
  for idx, line in enumerate(lines, start=1):
      stripped = line.strip()
      if "_update_boss_combat_taunts" in stripped:
          if stripped.startswith("#"):
              commented_found = True
          else:
              uncommented_taunts.append((idx, stripped))

  # AFTER
  for idx, line in enumerate(lines, start=1):
      stripped = line.strip()
      if "_update_boss_combat_taunts" in stripped:
          if stripped.startswith("def "):
              continue
          if stripped.startswith("#"):
              commented_found = True
          else:
              uncommented_taunts.append((idx, stripped))
  ```

---

#### Fix 2: `src/game/ui/side_notification.py` & `test_game_state_popup_triggers.py` (SideNotification Teardown)
- **Target 1**: `src/game/ui/side_notification.py`, add method `clear()`
- **Target 2**: `tests/test_game_state_popup_triggers.py`, lines 421-425
- **Code in `src/game/ui/side_notification.py`**:
  ```python
  def clear(self) -> None:
      """Clear active notification and pending queue immediately."""
      self._state = NotificationState.IDLE
      self._timer = 0.0
      self._current_item = None
      self._queue.clear()
      self._current_tab_surface = None
      self._current_x = float(self._screen_width)
  ```
- **Code in `tests/test_game_state_popup_triggers.py`**:
  Move `sn = SideNotification(1280, 720)` inside the `for scene_id, scene in all_scenes.items():` loop to guarantee complete per-iteration state isolation.

---

#### Fix 3: `tests/test_editor_plugins_roundtrip_integrity.py` (PopupSceneManager Custom Path)
- **Target**: `tests/test_editor_plugins_roundtrip_integrity.py`, lines 102-105
- **Change**: Pass `config_path=tmp_target` to `PopupSceneManager.get_instance()` instead of passing an argument to `load_config()`.
- **Code**:
  ```python
  # BEFORE (lines 102-105)
  PopupSceneManager.reset_instance()
  mgr = PopupSceneManager.get_instance()
  mgr.load_config(tmp_target)

  # AFTER
  PopupSceneManager.reset_instance()
  mgr = PopupSceneManager.get_instance(config_path=tmp_target)
  ```
- **Optional Hardening**: In `src/game/systems/popup_scene_manager.py:56`, define `def load_config(self, config_path: Optional[str] = None) -> bool:` so passing a path argument updates `self.config_path` gracefully.

---

#### Fix 4: `tests/test_editor_plugins_roundtrip_integrity.py` (WaveEditorApp Class & State)
- **Target**: `tests/test_editor_plugins_roundtrip_integrity.py`, lines 196-205
- **Change**: Use `wave_editor.WaveEditorApp` and initialize `level_files`, `active_idx`, `level_data`, `level_backup`, and `modal`.
- **Code**:
  ```python
  # BEFORE (lines 196-205)
  app = wave_editor.App.__new__(wave_editor.App)
  app.level_file = tmp_target
  app.pending = copy.deepcopy(data.get("spawn_zones", []))

  # AFTER
  app = wave_editor.WaveEditorApp.__new__(wave_editor.WaveEditorApp)
  app.level_files = [tmp_target]
  app.active_idx = 0
  app.level_data = copy.deepcopy(data)
  app.level_backup = copy.deepcopy(data)
  app.pending = copy.deepcopy(data.get("spawn_zones", []))
  app.modal = None
  ```
- **Optional Hardening**: In `wave_editor.py`, add `App = WaveEditorApp` at module level.

---

#### Fix 5: `tests/test_editor_plugins_roundtrip_integrity.py` & `test_editor_plugins_adversarial_m2.py` (os.path.exists Mock Recursion)
- **Target**: `tests/test_editor_plugins_roundtrip_integrity.py`, lines 340-350
- **Target**: `tests/test_editor_plugins_adversarial_m2.py`, line 157
- **Change**: Capture `orig_exists = os.path.exists` before invoking `patch("os.path.exists", ...)`.
- **Code**:
  ```python
  # BEFORE (lines 346-348)
  with patch("builtins.open", side_effect=isolated_open), \
       patch("os.path.exists", side_effect=lambda p: True if p in (boss_path, minion_path, "game_data/enemy_skeleton_minion_config.json") else os.path.exists(p)), \
       patch("boss_editor.ConfigClient", create=True):
      app.confirm_save_config()

  # AFTER
  orig_exists = os.path.exists
  def isolated_exists(p):
      if p in (boss_path, minion_path, "game_data/enemy_skeleton_minion_config.json"):
          return True
      return orig_exists(p)

  with patch("builtins.open", side_effect=isolated_open), \
       patch("os.path.exists", side_effect=isolated_exists), \
       patch("boss_editor.ConfigClient", create=True):
      app.confirm_save_config()
  ```

---

#### Fix 6: `tests/test_editor_plugins_roundtrip_integrity.py` (Blood Zombie MetaphorSlider)
- **Target**: `tests/test_editor_plugins_roundtrip_integrity.py`, lines 406, 423-426
- **Change**: Import `MetaphorSlider` and pass valid arguments.
- **Code**:
  ```python
  # BEFORE (lines 406, 423-426)
  from blood_zombie_editor import BloodZombieEditorApp, Slider
  ...
  app.sliders = {
      "scale": Slider("scale", "Scale", 0, 0, 100, 1.0, 4.0, 2.25, True),
      "ground_offset": Slider("ground_offset", "Ground", 0, 0, 100, -50, 50, 10, False),
  }

  # AFTER
  from blood_zombie_editor import BloodZombieEditorApp, MetaphorSlider
  ...
  app.sliders = {
      "scale": MetaphorSlider("scale", "Scale", "Scale", "", 0, 0, 100, 1.0, 4.0, 2.25, True),
      "ground_offset": MetaphorSlider("ground_offset", "Ground", "Ground", "", 0, 0, 100, -50, 50, 10, False),
  }
  ```
- **Optional Hardening**: In `blood_zombie_editor.py`, add `Slider = MetaphorSlider` at module scope.

---

#### Fix 7: `tests/test_editor_plugins_roundtrip_integrity.py` & `src/game/systems/the_eye_manager.py` (TheEye save_perception)
- **Target**: `tests/test_editor_plugins_roundtrip_integrity.py`, line 477
- **Target**: `src/game/systems/the_eye_manager.py`, line 1577
- **Code in Test**:
  ```python
  # BEFORE
  mgr.save_all()

  # AFTER
  mgr.save_perception()
  ```
- **Code in `src/game/systems/the_eye_manager.py`**:
  ```python
  def save_all(self) -> Tuple[bool, str]:
      """Alias for save_perception to provide unified editor plugin API."""
      return self.save_perception()
  ```

---

#### Fix 8: `src/game/controls_manager.py` (Preserve External Keys in save_config)
- **Target**: `src/game/controls_manager.py`, lines 137-149
- **Change**: Replace raw `atomic_write_json` with `atomic_merge_json` to preserve external configuration keys.
- **Code**:
  ```python
  # BEFORE (lines 137-149)
  def save_config(self) -> bool:
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

  # AFTER
  def save_config(self) -> bool:
      data = {
          "active_mode": self.mode,
          "keyboard_bindings": self.keyboard_bindings,
          "joystick_bindings": self.joystick_bindings,
      }
      try:
          from src.game.utils.atomic_save import atomic_merge_json
          success, _ = atomic_merge_json(CONFIG_PATH, data, indent=4, backup=True, max_backups=5)
          return success
      except Exception as e:
          print(f"[ControlsManager] Failed to save controls config: {e}")
          return False
  ```

---

#### Fix 9: `src/game/systems/shadow_registry.py` (Preserve External Shadow Layers)
- **Target**: `src/game/systems/shadow_registry.py`, lines 170-189
- **Change**: Pass `domain_keys=[norm_key]` to `atomic_merge_json` so only the modified profile is updated on disk.
- **Code**:
  ```python
  # BEFORE (lines 178-186)
  data = {k: v.to_dict() for k, v in cls._cache.items()}
  try:
      from src.game.utils.atomic_save import atomic_merge_json
      success, _ = atomic_merge_json(CONFIG_PATH, data, indent=4)

  # AFTER
  try:
      from src.game.utils.atomic_save import atomic_merge_json
      success, _ = atomic_merge_json(
          CONFIG_PATH,
          {norm_key: profile.to_dict()},
          domain_keys=[norm_key],
          indent=4,
          backup=True,
          max_backups=5,
      )
  ```

---

#### Fix 10: `tests/test_editor_plugins_roundtrip_integrity.py` (Storyline Manager Corruption Key)
- **Target**: `tests/test_editor_plugins_roundtrip_integrity.py`, lines 690, 701
- **Change**: Mutate the valid key `"dash_speed_multiplier"` under `"corruption"`.
- **Code**:
  ```python
  # BEFORE (lines 690, 701)
  mgr.data["corruption"]["corruption_thresholds"]["high"] = 92.0
  ...
  assert saved["corruption"]["corruption_thresholds"]["high"] == 92.0

  # AFTER
  mgr.data["corruption"]["dash_speed_multiplier"] = 2.25
  ...
  assert saved["corruption"]["dash_speed_multiplier"] == 2.25
  ```

---

## 5. Verification Method

Once the Remediation Worker applies the fixes above, execute the following commands to independently verify complete remediation:

```powershell
# 1. Execute the targeted M3 test suites (Expected: 31 PASSED, 0 FAILED)
$env:PYTHONPATH="."
.\.venv\Scripts\python.exe -m pytest tests/test_game_state_popup_triggers.py tests/test_editor_plugins_roundtrip_integrity.py -v

# 2. Execute related adversarial tests (Expected: 100% PASSED)
.\.venv\Scripts\python.exe -m pytest tests/test_editor_plugins_adversarial_m2.py tests/test_tier5_adversarial_stress.py -v
```

### Invalidation Conditions
- If any test in `test_game_state_popup_triggers.py` or `test_editor_plugins_roundtrip_integrity.py` fails with `AttributeError`, `TypeError`, `KeyError`, or `RecursionError`, this investigation report's conclusions are invalidated.
