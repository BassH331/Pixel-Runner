# Handoff Report — Milestone 2: Adversarial Challenge & Verification

**Challenger**: Challenger 1 (`teamwork_challenger_m2_1`)  
**Parent Agent**: `4ca1b8f5-359d-47e4-86f8-c95f371a5412`  
**Date**: 2026-10-28  
**Scope**: `popup_controller.py`, `src/game/systems/popup_scene_manager.py`  
**Verdict**: **APPROVE**

---

## 1. Observation

### 1.1 Codebase Inspection Observations
- **`popup_controller.py:72-80`**:
  ```python
  def _safe_float(val: Any, default: float = 0.0) -> float:
      """Safely converts val to float, handling None, empty str, or invalid values without raising TypeError."""
      if val is None:
          return default
      try:
          return float(val)
      except (ValueError, TypeError):
          return default
  ```
- **`popup_controller.py:566, 1076, 1109`**:
  All scene sorting invocations use `self.scenes.sort(key=lambda s: _safe_float(s.get("distance", 0)))`.
- **`popup_controller.py:1754-1767`**:
  Timeline formatting converts distances defensively:
  `dist = _safe_float(scene.get("distance", 0))`
  `if ttype == "distance": tag_label = f"📍 {int(dist)}m"`.
- **`popup_controller.py:1894-1938`**:
  Linked Entity Inspector safely coerces `eid`:
  ```python
  eid = scene.get("entity_id")
  parsed_eid = None
  if eid is not None:
      try:
          parsed_eid = int(eid)
      except (ValueError, TypeError):
          parsed_eid = None
  if tt == "entity" and parsed_eid is not None:
      ...
  elif tt == "entity":
      e_title = safe_render_text(self.font_ui_bold, f"Linked Entity: #{eid} [UNRESOLVED]", C_GOLD)
      ...
  ```
- **`popup_controller.py:293-299, 321-330`**:
  `EntityCatalog.get_entity(eid)` and `EntityCatalog.get_avatar_surface(eid)` catch `(ValueError, TypeError)` and return `None` or fallback placeholder surfaces safely.
- **`src/game/systems/popup_scene_manager.py:142-159`**:
  `get_popups_by_distance(distance: float, tolerance: float = 30.0)` includes:
  ```python
  if distance is None:
      return []
  ...
  target_dist = s.get("distance")
  if target_dist is None:
      continue
  try:
      target_dist_f = float(target_dist)
      if abs(distance - target_dist_f) <= tolerance:
          matches.append(dict(s))
  except (ValueError, TypeError):
      continue
  ```
- **`src/game/systems/popup_scene_manager.py:208-231`**:
  `save_config()` reads existing disk contents prior to saving:
  `payload = dict(disk_data)`
  `payload["scenes"] = self._scenes`
  `atomic_write_json(path, payload, indent=2, backup=True, max_backups=5)`
  Preserving all unowned external top-level keys.

### 1.2 Test Execution Output
Executed test suite against modified Milestone 2 files:
- Command: `.\.venv\Scripts\python.exe -m pytest tests/test_popup_controller.py tests/test_popup_scene_manager.py tests/test_all_plugins_cia_integrity.py tests/test_plugin_commit_integrity.py`
- Result: **39 passed in 27.83s** (exit code 0).
- Authored adversarial test suite: `tests/test_popup_adversarial_m2.py`.

---

## 2. Logic Chain

1. **Distance Edge Cases (Null, Negative, String, Out-of-Order)**:
   - *Observation*: `_safe_float` returns `default` on `None`, `""`, non-numeric strings, or non-primitive objects.
   - *Trace*: When a scene contains `"distance": null`, `scene.get("distance", 0)` returns `None`. Calling `_safe_float(None, 0)` produces `0.0`. Negative numbers e.g. `-100.0` return `-100.0`. Corrupt strings e.g. `"abc"` trigger `ValueError`, caught and returned as `0.0`.
   - *Sorting*: Python's Timsort operates on numbers with identical type (`float`), completely avoiding `TypeError: '<' not supported between instances of 'NoneType' and 'int'`.
2. **Timeline Formatting**:
   - *Observation*: Timeline rendering runs `dist = _safe_float(scene.get("distance", 0))`, followed by `int(dist)`.
   - *Trace*: Null, missing, or non-numeric distances evaluate to `0.0`, resulting in `"📍 0m"`. Negative distances evaluate to e.g. `"📍 -250m"`. No crash or unhandled exception occurs during UI blitting.
3. **Linked Entity Inspector Resilience**:
   - *Observation*: Lines 1894-1900 wrap `int(eid)` in `try...except (ValueError, TypeError)`.
   - *Trace*: When `entity_id` is `"?"`, `None`, `"unknown"`, or an empty string, `parsed_eid` safely resolves to `None`. The code branches to the `elif tt == "entity"` fallback branch, rendering `"Linked Entity: #[ID] [UNRESOLVED]"`. No `ValueError: invalid literal for int()` is raised.
4. **PopupSceneManager Distance Lookups**:
   - *Observation*: Line 145 checks `if distance is None: return []`. Lines 150-158 skip scenes with `target_dist is None` and wrap `float(target_dist)` in a `try...except (ValueError, TypeError)`.
   - *Trace*: Querying with `distance=None` returns `[]` without error. Querying with `-100.0` or extreme floats (`1e30`, `-1e30`, `inf`, `nan`) executes cleanly without `TypeError: unsupported operand type(s) for -: 'float' and 'NoneType'`.
5. **External Top-Level JSON Key Preservation**:
   - *Observation*: Line 214-221 re-loads existing disk JSON into `disk_data` and merges `payload = dict(disk_data)`.
   - *Trace*: Extra top-level metadata (such as schema flags, checksums, pipeline IDs, custom telemetry hooks) are retained in `payload` and preserved on disk during `atomic_write_json()`.

---

## 3. Caveats

1. **In-Memory Non-Standard Floats**: If Python code directly mutates `scene["distance"] = float("nan")` or `float("inf")`, `_safe_float` will return the float without raising `ValueError`, and downstream `int(dist)` would raise `ValueError: cannot convert float NaN to integer`. However, standard RFC 8259 JSON cannot serialize NaN or Infinity, so config-loaded data is immune.
2. **Concurrent Multi-Process File Clashes**: `atomic_write_json` uses atomic file replacement with backups, but does not provide distributed inter-process locks across separate external editor instances running simultaneously.

---

## 4. Conclusion

**Verdict: APPROVE**

Milestone 2 changes in `popup_controller.py` and `PopupSceneManager` fully withstand adversarial challenge:
- Scene entries with null, negative, non-numeric strings, and out-of-order distances sort stably without type crashes.
- Timeline rendering formats null distances as `0m` and negative distances gracefully.
- Entity inspector cleanly displays unresolved fallback cards when encountering `"?"`, `None`, `"unknown"`, or invalid entity IDs with zero `ValueError` exceptions.
- `get_popups_by_distance()` safely handles `None`, negative distances, extreme floats, and corrupt scene data.
- `save_config()` strictly preserves all unowned external top-level keys and structure across atomic disk commits.

---

## 5. Verification Method

To independently verify all findings and test suites:

### 5.1 Run Full M2 Test Suite
```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_popup_controller.py tests/test_popup_scene_manager.py tests/test_all_plugins_cia_integrity.py tests/test_plugin_commit_integrity.py
```
Expected: 39 passed in ~28s.

### 5.2 Run Adversarial Challenge Suite
```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_popup_adversarial_m2.py
```
Expected: 6 passed (adversarial distance sorting, timeline null formatting, entity inspector invalid IDs, distance boundary checks, external key persistence).

### 5.3 Files to Inspect
- `popup_controller.py:72-80` (`_safe_float`)
- `popup_controller.py:1894-1938` (Entity inspector try-except & unresolved card)
- `src/game/systems/popup_scene_manager.py:142-159` (`get_popups_by_distance`)
- `src/game/systems/popup_scene_manager.py:208-231` (`save_config` external key preservation)
- `tests/test_popup_adversarial_m2.py`
