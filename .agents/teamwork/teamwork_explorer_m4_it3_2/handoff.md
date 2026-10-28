# Handoff Report — Explorer 2 (Milestone 4 Iteration 3 Remediation)

**Remediation Target**: Failure 2 — `TestEditorPluginsRoundtripIntegrity.test_boss_editor_roundtrip_and_key_preservation` failing on `assert saved_minion["speed"] == 6.2` (`assert 2.2 == 6.2`).  
**Investigating Agent**: Explorer 2 (`teamwork_explorer_m4_it3_2`)  
**Parent Conversation ID**: `4ca1b8f5-359d-47e4-86f8-c95f371a5412`  
**Timestamp**: 2026-10-28T20:55:00Z  

---

## 1. Observation

### 1.1 Verbatim Pytest Failure from Iteration 2 Audit
From `teamwork_auditor_m4_it2\handoff.md:90-104`:
```text
_ TestEditorPluginsRoundtripIntegrity.test_boss_editor_roundtrip_and_key_preservation _

self = <test_editor_plugins_roundtrip_integrity.TestEditorPluginsRoundtripIntegrity object at 0x0000015A1523FF00>
tmp_path = WindowsPath('C:/Users/me/AppData/Local/Temp/pytest-of-me/pytest-15/test_boss_editor_roundtrip_and0')

    def test_boss_editor_roundtrip_and_key_preservation(self, tmp_path):
...
>       assert saved_minion["speed"] == 6.2
E       assert 2.2 == 6.2

tests\test_editor_plugins_roundtrip_integrity.py:361: AssertionError
```

### 1.2 Direct Inspection of `boss_editor.py:995-1008`
In `boss_editor.py`:
```python
995:             # If editing skeleton, also save to minion skeleton config file to keep in-game minion AI in sync
996:             if boss_key == "skeleton":
997:                 minion_path = "game_data/enemy_skeleton_minion_config.json"
998:                 if os.path.exists(minion_path):
999:                     try:
1000:                        with open(minion_path, "r", encoding="utf-8") as mf:
1001:                            minion_cfg = json.load(mf)
1002:                        for sync_key in ("spidey_sense", "teleport_dist_min", "teleport_dist_max", "teleport_cooldown", "teleport_reaction_delay", "speed"):
1003:                            if sync_key in config:
1004:                                minion_cfg[sync_key] = config[sync_key]
1005:                        atomic_write_json(minion_path, minion_cfg, indent=2, backup=True, max_backups=5)
1006:                        prune_backups(minion_path, max_backups=5)
1007:                    except Exception as me:
1008:                        print(f"[WARNING] Failed to sync minion config: {me}")
```
`minion_path = "game_data/enemy_skeleton_minion_config.json"` is hardcoded at line 997, ignoring any test-configured isolated file paths.

### 1.3 Direct Inspection of `src/game/utils/atomic_save.py:108-117`
In `atomic_write_json`:
```python
108:         if backup:
109:             create_validated_backup(file_path, max_backups=max_backups)
110: 
111:         tmp_path = f"{file_path}.tmp_{os.getpid()}_{uuid.uuid4().hex[:6]}"
112:         with open(tmp_path, "w", encoding="utf-8") as fh:
113:             json.dump(data, fh, indent=indent, ensure_ascii=False)
114:             fh.flush()
115:             os.fsync(fh.fileno())
116: 
117:         os.replace(tmp_path, file_path)
```
`atomic_write_json` does not write directly to `file_path`. It writes to `tmp_path = f"{file_path}.tmp_{os.getpid()}_{uuid.uuid4().hex[:6]}"` and performs an atomic filesystem operation `os.replace(tmp_path, file_path)`.

### 1.4 Direct Inspection of Test Interceptions
In `tests/test_editor_plugins_roundtrip_integrity.py:344-352`:
```python
344:                 def isolated_open(p, *args, **kwargs):
345:                     if p == "game_data/enemy_skeleton_minion_config.json":
346:                         return orig_open(minion_path, *args, **kwargs)
347:                     return orig_open(p, *args, **kwargs)
348: 
349:                 with patch("builtins.open", side_effect=isolated_open), \
350:                      patch("os.path.exists", side_effect=lambda p: True if p in (boss_path, minion_path, "game_data/enemy_skeleton_minion_config.json") else orig_exists(p)), \
351:                      patch("boss_editor.ConfigClient", create=True):
352:                     app.confirm_save_config()
```
And in `tests/test_editor_plugins_adversarial_m2.py:161-167`:
```python
161:                     def custom_open(path, mode="r", *args, **kwargs):
162:                         if path == "game_data/enemy_skeleton_minion_config.json":
163:                             return orig_open(minion_config_path, mode, *args, **kwargs)
164:                         return orig_open(path, mode, *args, **kwargs)
165: 
166:                     with patch("builtins.open", side_effect=custom_open):
167:                         app.confirm_save_config()
```

### 1.5 Direct Observation of Real Repository Pollution
Inspection of `game_data/` revealed that tests directly mutated the real repository file and generated 5 backup files in production git tracking:
- `game_data/enemy_skeleton_minion_config.json` contained test data:
  ```json
  {
    "max_health": 35.0,
    "speed": 6.2,
    "spidey_sense": 0.85,
    "teleport_dist_min": 220,
    "teleport_dist_max": 440,
    "teleport_cooldown": 4.5,
    "teleport_reaction_delay": 0.35,
    "external_minion_pack": "death_pack_01"
  }
  ```
- 5 rolling backup files created by the test loop (`step * 14` -> 56, 70, 84, 98, 112):
  - `game_data/enemy_skeleton_minion_config.json.backup_1700000056`
  - `game_data/enemy_skeleton_minion_config.json.backup_1700000070`
  - `game_data/enemy_skeleton_minion_config.json.backup_1700000084`
  - `game_data/enemy_skeleton_minion_config.json.backup_1700000098`
  - `game_data/enemy_skeleton_minion_config.json.backup_1700000112`

---

## 2. Logic Chain

1. **Step 1 (Root Cause of Test Mock Failure)**:
   - In `test_boss_editor_roundtrip_and_key_preservation`, the test attempts to mock `builtins.open` via `if p == "game_data/enemy_skeleton_minion_config.json": return orig_open(minion_path)`.
   - When line 1000 in `boss_editor.py` executes (`with open(minion_path, "r")`), `p == "game_data/enemy_skeleton_minion_config.json"` evaluates to `True`. `isolated_open` returns a handle to the test's `minion_path`.
   - Next, line 1005 executes `atomic_write_json(minion_path, minion_cfg)`.
   - Inside `atomic_write_json`, `file_path` is `"game_data/enemy_skeleton_minion_config.json"`.
   - `tmp_path` is constructed as `"game_data/enemy_skeleton_minion_config.json.tmp_<pid>_<uuid>"`.
   - When line 112 in `atomic_save.py` calls `open(tmp_path, "w")`, `isolated_open` receives `p = "game_data/enemy_skeleton_minion_config.json.tmp_..."`.
   - Because `p != "game_data/enemy_skeleton_minion_config.json"`, `isolated_open` falls through to `orig_open(tmp_path)`!
   - `atomic_write_json` writes the temporary file to the REAL `game_data/` folder and calls `os.replace(tmp_path, file_path)`.
   - `os.replace` replaces the real `game_data/enemy_skeleton_minion_config.json` with the new data.

2. **Step 2 (Root Cause of Assertion Failure)**:
   - The test's isolated `minion_path` (in `tmp_path`) was NEVER written to by `atomic_write_json`.
   - When the test reads `minion_path` at line 356:
     ```python
     with open(minion_path, "r", encoding="utf-8") as f:
         saved_minion = json.load(f)
     assert saved_minion["speed"] == 6.2
     ```
     `saved_minion` contains the initial test fixture data (`init_minion["speed"] = 2.2`).
   - Pytest raises `AssertionError: assert 2.2 == 6.2`.

3. **Step 3 (Evaluation of Solution Architecture)**:
   - Mocking `builtins.open` is inherently fragile against atomic transactional write engines that use temporary files (`.tmp_*`) and OS-level replacement (`os.replace`).
   - The correct architectural pattern—already utilized for `schema["config_file"]`—is allowing `BossEditorApp` to specify the target path for the skeleton minion config.
   - Using `getattr(self, "minion_config_path", "game_data/enemy_skeleton_minion_config.json")`:
     - Preserves 100% backward compatibility for production game loop / editor startup where `minion_config_path` is not passed or defaults to `"game_data/enemy_skeleton_minion_config.json"`.
     - Supports headless unit testing where `BossEditorApp` is instantiated via `__new__(BossEditorApp)` and `app.minion_config_path = minion_path` is assigned.
     - Entirely eliminates the need for fragile `builtins.open` and `os.path.exists` monkey patching in tests.
     - Confines all atomic temporary files, replacements, and rolling backups strictly to `tmp_path`.

---

## 3. Caveats

1. **Instantiation via `__new__` vs `__init__`**:
   In both `tests/test_editor_plugins_roundtrip_integrity.py` and `tests/test_editor_plugins_adversarial_m2.py`, `BossEditorApp` is instantiated using `BossEditorApp.__new__(BossEditorApp)` to avoid initializing Pygame surfaces, fonts, and sound engines headlessly.
   Therefore, simply initializing `self.minion_config_path` inside `__init__` is NOT sufficient. The getter in `confirm_save_config` **must** use `getattr(self, "minion_config_path", "game_data/enemy_skeleton_minion_config.json")`.
2. **Leftover Test Artifacts**:
   The 5 backup files (`game_data/enemy_skeleton_minion_config.json.backup_*`) created during previous test executions must be removed from the repository, and `game_data/enemy_skeleton_minion_config.json` must be restored to its canonical default state.

---

## 4. Conclusion & Prescribed Surgical Implementation

### 4.1 Changes in `boss_editor.py`

#### A. In `BossEditorApp.__init__` (around line 550):
Declare the default attribute:
```python
<<<<
        self.sliders: Dict[str, Slider] = {}
        self.build_sliders()
====
        self.minion_config_path = "game_data/enemy_skeleton_minion_config.json"
        self.sliders: Dict[str, Slider] = {}
        self.build_sliders()
>>>>
```

#### B. In `BossEditorApp.confirm_save_config` (lines 996-997):
Use `getattr(self, "minion_config_path", ...)`:
```python
<<<<
            # If editing skeleton, also save to minion skeleton config file to keep in-game minion AI in sync
            if boss_key == "skeleton":
                minion_path = "game_data/enemy_skeleton_minion_config.json"
                if os.path.exists(minion_path):
====
            # If editing skeleton, also save to minion skeleton config file to keep in-game minion AI in sync
            if boss_key == "skeleton":
                minion_path = getattr(self, "minion_config_path", "game_data/enemy_skeleton_minion_config.json")
                if os.path.exists(minion_path):
>>>>
```

---

### 4.2 Changes in `tests/test_editor_plugins_roundtrip_integrity.py`

In `test_boss_editor_roundtrip_and_key_preservation` (lines 330-364):
Set `app.minion_config_path = minion_path`, remove fragile `builtins.open` / `os.path.exists` patches, mock `LocalCache`, and verify minion backups:
```python
<<<<
        app.boss_configs = {"skeleton": copy.deepcopy(init_boss)}
        app.sliders = {
            "speed": Slider("speed", "Speed", 0, 0, 100, 1.0, 10.0, 6.2, True),
            "spidey_sense": Slider("spidey_sense", "Spidey", 0, 0, 100, 0.0, 1.0, 0.85, True),
            "teleport_dist_min": Slider("teleport_dist_min", "TeleMin", 0, 0, 100, 50, 500, 220, False),
            "teleport_dist_max": Slider("teleport_dist_max", "TeleMax", 0, 0, 100, 50, 500, 440, False),
        }

        # Save 8 times
        for step in range(1, 9):
            fake_ts = 1700000000 + (step * 14)
            with patch("time.time", return_value=fake_ts):
                orig_open = open
                orig_exists = os.path.exists
                def isolated_open(p, *args, **kwargs):
                    if p == "game_data/enemy_skeleton_minion_config.json":
                        return orig_open(minion_path, *args, **kwargs)
                    return orig_open(p, *args, **kwargs)

                with patch("builtins.open", side_effect=isolated_open), \
                     patch("os.path.exists", side_effect=lambda p: True if p in (boss_path, minion_path, "game_data/enemy_skeleton_minion_config.json") else orig_exists(p)), \
                     patch("boss_editor.ConfigClient", create=True):
                    app.confirm_save_config()

        with open(boss_path, "r", encoding="utf-8") as f:
            saved_boss = json.load(f)
        with open(minion_path, "r", encoding="utf-8") as f:
            saved_minion = json.load(f)

        assert saved_boss["external_boss_lore"] == "Crypt Monarch of the Ash Woods"
        assert saved_minion["external_minion_pack"] == "death_pack_01"
        assert saved_minion["speed"] == 6.2
        assert saved_minion["spidey_sense"] == 0.85
        _assert_backups_clean_and_capped(boss_path, max_backups=5)
====
        app.boss_configs = {"skeleton": copy.deepcopy(init_boss)}
        app.minion_config_path = minion_path
        app.sliders = {
            "speed": Slider("speed", "Speed", 0, 0, 100, 1.0, 10.0, 6.2, True),
            "spidey_sense": Slider("spidey_sense", "Spidey", 0, 0, 100, 0.0, 1.0, 0.85, True),
            "teleport_dist_min": Slider("teleport_dist_min", "TeleMin", 0, 0, 100, 50, 500, 220, False),
            "teleport_dist_max": Slider("teleport_dist_max", "TeleMax", 0, 0, 100, 50, 500, 440, False),
        }

        # Save 8 times
        for step in range(1, 9):
            fake_ts = 1700000000 + (step * 14)
            with patch("time.time", return_value=fake_ts), \
                 patch("boss_editor.ConfigClient", create=True), \
                 patch("boss_editor.LocalCache", create=True):
                app.confirm_save_config()

        with open(boss_path, "r", encoding="utf-8") as f:
            saved_boss = json.load(f)
        with open(minion_path, "r", encoding="utf-8") as f:
            saved_minion = json.load(f)

        assert saved_boss["external_boss_lore"] == "Crypt Monarch of the Ash Woods"
        assert saved_minion["external_minion_pack"] == "death_pack_01"
        assert saved_minion["speed"] == 6.2
        assert saved_minion["spidey_sense"] == 0.85
        _assert_backups_clean_and_capped(boss_path, max_backups=5)
        _assert_backups_clean_and_capped(minion_path, max_backups=5)
>>>>
```

---

### 4.3 Changes in `tests/test_editor_plugins_adversarial_m2.py`

In `test_adversarial_boss_editor_atomic_save_and_backup_cap` (lines 145-168):
Set `app.minion_config_path = minion_config_path` and eliminate inner `custom_open` / `os.path.exists` patches:
```python
<<<<
    # Patch minion path in boss_editor to point to our isolated temporary minion config
    with patch("boss_editor.LocalCache", create=True), \
         patch("boss_editor.ConfigClient", create=True):

        # Save 8 times to challenge backup rotation cap (max 5)
        # Use patch to simulate different timestamps so backups have distinct names
        for step in range(1, 9):
            app.sliders["speed"].val = 5.0 + (step * 0.1)
            fake_ts = 1700000000 + (step * 10)
            with patch("time.time", return_value=fake_ts):
                # Temporarily patch the hardcoded minion path inside confirm_save_config
                orig_exists = os.path.exists
                with patch("os.path.exists", side_effect=lambda p: True if p in (boss_config_path, minion_config_path) else orig_exists(p)):
                    # Custom patch for open in minion section
                    orig_open = open
                    def custom_open(path, mode="r", *args, **kwargs):
                        if path == "game_data/enemy_skeleton_minion_config.json":
                            return orig_open(minion_config_path, mode, *args, **kwargs)
                        return orig_open(path, mode, *args, **kwargs)

                    with patch("builtins.open", side_effect=custom_open):
                        app.confirm_save_config()
====
    app.minion_config_path = minion_config_path

    # Mock cache services in boss_editor
    with patch("boss_editor.LocalCache", create=True), \
         patch("boss_editor.ConfigClient", create=True):

        # Save 8 times to challenge backup rotation cap (max 5)
        # Use patch to simulate different timestamps so backups have distinct names
        for step in range(1, 9):
            app.sliders["speed"].val = 5.0 + (step * 0.1)
            fake_ts = 1700000000 + (step * 10)
            with patch("time.time", return_value=fake_ts):
                app.confirm_save_config()
>>>>
```

---

### 4.4 Repository Clean-up in `game_data/`

1. Delete the 5 stray backup files:
   - `game_data/enemy_skeleton_minion_config.json.backup_1700000056`
   - `game_data/enemy_skeleton_minion_config.json.backup_1700000070`
   - `game_data/enemy_skeleton_minion_config.json.backup_1700000084`
   - `game_data/enemy_skeleton_minion_config.json.backup_1700000098`
   - `game_data/enemy_skeleton_minion_config.json.backup_1700000112`
2. Restore `game_data/enemy_skeleton_minion_config.json` to its canonical defaults:
```json
{
  "max_health": 30.0,
  "speed": 2.5,
  "spidey_sense": 0.25,
  "teleport_dist_min": 180,
  "teleport_dist_max": 240,
  "teleport_cooldown": 4.5,
  "teleport_reaction_delay": 0.1
}
```

---

## 5. Verification Method

### 5.1 Verification Commands
```powershell
$env:PYTHONPATH="."
.\.venv\Scripts\python.exe -m pytest tests/test_editor_plugins_roundtrip_integrity.py -k test_boss_editor_roundtrip_and_key_preservation -v
.\.venv\Scripts\python.exe -m pytest tests/test_editor_plugins_adversarial_m2.py -k test_adversarial_boss_editor_atomic_save_and_backup_cap -v
```

### 5.2 Expected Outcomes
- Both tests execute cleanly and report `100% PASSED`.
- `saved_minion["speed"]` strictly equals `6.2` in `test_boss_editor_roundtrip_and_key_preservation`.
- Both `boss_path` and `minion_path` have exactly 5 rolling backups in `tmp_path`, non-empty, and valid JSON.
- `game_data/enemy_skeleton_minion_config.json` remains untouched with mtime unchanged during the test run.
- Zero stray backup files (`.backup_*`) exist in `game_data/`.

### 5.3 Invalidation Conditions
- If `boss_editor.py` fails to use `getattr(self, "minion_config_path", ...)` and instead checks `self.minion_config_path` directly, it will raise `AttributeError` whenever `BossEditorApp.__new__` is used without `__init__`.
- If `app.minion_config_path` is not set in `test_editor_plugins_roundtrip_integrity.py`, `atomic_write_json` will continue targeting `game_data/enemy_skeleton_minion_config.json`, causing `assert 2.2 == 6.2` to fail.
