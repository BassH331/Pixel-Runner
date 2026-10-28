## 2026-10-28T18:49:59Z
You are Worker M2 (Editor Plugin Data Parity & Hardening).
Your working directory is: c:\Users\me\Documents\game\Pixel-Runner\.agents\teamwork\teamwork_worker_m2\
Original request path: c:\Users\me\Documents\game\Pixel-Runner\.agents\teamwork\ORIGINAL_REQUEST.md
Project plan path: c:\Users\me\Documents\game\Pixel-Runner\PROJECT.md
Explorer 2 handoff: c:\Users\me\Documents\game\Pixel-Runner\.agents\teamwork\teamwork_explorer_survey_2\handoff.md

You MUST read c:\Users\me\Documents\game\Pixel-Runner\.agents\teamwork\ORIGINAL_REQUEST.md and PROJECT.md before starting work.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Exclusive write ownership:
- `popup_controller.py`
- `src/game/systems/popup_scene_manager.py`
- `boss_editor.py`
- `level_editor.py`
- `wave_editor.py`
- `player_editor.py`

Tasks:
1. Harden `popup_controller.py`:
   - Replace unsafe `float(s.get("distance", 0))` with a safe distance conversion helper (e.g. `float(s.get("distance") or 0.0)`) across all sort lambdas (lines 551, 1061, 1094) and distance/tag formatting locations (lines 1339, 1749-1750, 1912, 1914, 1916) so that `"distance": null` never raises `TypeError: float() argument must be a string or a real number, not 'NoneType'`.
   - In `_render_entity_inspector()` (line 1881), wrap `int(eid)` in safe integer parsing / try-except to avoid unhandled `ValueError` when `eid` is a string like `"?"` or non-numeric.
   - In `PopupControllerApp.__init__()`, support `headless: bool = False` or safely guard `win.maximize()` in a `try...except Exception:` block so that running in headless CI without a window manager does not crash.
2. Harden `src/game/systems/popup_scene_manager.py`:
   - In `get_popups_by_distance()` (line 141-143): Safely guard distance comparison so that if `distance` is `None` or `target_dist` is `None`, it skips without raising `TypeError`.
   - In `_rebuild_indices()` (lines 102-107): Only register in `_scenes_by_entity` when `scene.get("trigger_type") == "entity"` or `entity_id` is an integer, ensuring non-entity scenes (like flag triggers sharing entity_id) don't unintentionally override the primary entity lookup.
   - In `save_config()`: Preserve external / unowned top-level fields by reading the existing disk JSON (if present) and merging `{"scenes": self._scenes}` into it, rather than overwriting with a fixed 3-key dictionary (`atomic_merge_json` or read-merge-`atomic_write_json`).
3. Harmonize Editor Plugin Atomic Saves:
   - In `boss_editor.py` (`confirm_save_config` lines 1001-1016): Replace direct `open(config_path, "w")` with `src.game.utils.atomic_save.atomic_write_json(config_path, ...)` and prune backups with `prune_backups`.
   - In `level_editor.py` (`commit` lines 2455-2458): Ensure the custom write pattern uses `atomic_write_json` or calls `os.fsync` on the temp file descriptor before `os.replace`, and creates validated rolling backups pruned to 5.
   - In `wave_editor.py`:
     - Line 260 (`commit`): Use `atomic_write_json` or ensure `os.fsync` before `os.replace` with backup pruning.
     - Line 350 (`simulate`): Do NOT write uncommitted simulation state directly to the production `level_file` with truncating `open(..., "w")`. Write to a temporary simulation file or memory structure, or use `atomic_write_json`.
   - In `player_editor.py` (lines 1097-1104): Replace direct `.tmp` write with `atomic_write_json` and `prune_backups`.
4. Run verification tests:
   `$env:PYTHONPATH="."; .\.venv\Scripts\python.exe -m pytest tests/test_popup_controller.py tests/test_popup_scene_manager.py tests/test_all_plugins_cia_integrity.py tests/test_plugin_commit_integrity.py`
5. Document all changes and test outputs in:
   `c:\Users\me\Documents\game\Pixel-Runner\.agents\teamwork\teamwork_worker_m2\handoff.md`
   Update `progress.md` and send a completion message to the orchestrator.


## 2026-10-28T19:03:39Z
[Message] sender=4ca1b8f5-359d-47e4-86f8-c95f371a5412
**Context**: Milestone 2 Implementation (Editor Plugin Data Parity & Hardening)
**Content**: Heartbeat status check. Please provide a brief update on your current progress across Tasks 1-3.
**Action**: Update your progress.md and continue execution.
