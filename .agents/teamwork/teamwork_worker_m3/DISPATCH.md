## 2026-10-28T19:24:25Z
You are Worker M3 (E2E Test Architecture & Verification).
Your working directory is: c:\Users\me\Documents\game\Pixel-Runner\.agents\teamwork\teamwork_worker_m3\
Original request path: c:\Users\me\Documents\game\Pixel-Runner\.agents\teamwork\ORIGINAL_REQUEST.md
Project plan path: c:\Users\me\Documents\game\Pixel-Runner\PROJECT.md
Test infra path: c:\Users\me\Documents\game\Pixel-Runner\TEST_INFRA.md
Explorer 3 handoff: c:\Users\me\Documents\game\Pixel-Runner\.agents\teamwork\teamwork_explorer_survey_3\handoff.md
Challenger 2 handoff: c:\Users\me\Documents\game\Pixel-Runner\.agents\teamwork\teamwork_challenger_m2_2\handoff.md

You MUST read c:\Users\me\Documents\game\Pixel-Runner\.agents\teamwork\ORIGINAL_REQUEST.md, PROJECT.md, and TEST_INFRA.md before starting work.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Exclusive write ownership:
- `tests/test_game_state_popup_triggers.py`
- `tests/test_editor_plugins_roundtrip_integrity.py`
- `player_editor.py` (lines 1968-1976 exit hook cleanup)
- `TEST_READY.md`

Tasks:
1. In `player_editor.py:1968-1976`, replace the raw `open("w")` exit write in `run()` with `self.request_save_config()`, ensuring shutdown saves use atomic transactional writes with external key preservation and backup pruning.
2. Implement `tests/test_game_state_popup_triggers.py`:
   - Headless Pygame fixture using dummy driver.
   - Test that all 9 GameState event IDs (`event_prologue_awakening`, `event_book_ponder`, `event_first_encounter`, `event_first_kill`, `event_forest_inquiry_1400m`, `event_moonstone_keeper`, `event_soul_quota_betrayal`, `event_level_complete`, `event_demon_time_unlocked`) resolve to existing, valid config entries in `scene_popups_config.json` with positive hold times, valid themes in `THEME_PRESETS`, and valid icons.
   - Programmatically confirm all pop-up triggers in `GameState` resolve to existing, valid config entries in `scene_popups_config.json` without falling back to hardcoded error states.
   - Test that `event_prologue_awakening` contains title "The Awakening" and body text specific to the prologue awakening, NOT the Fabricator's Enforcer.
   - Test that entity trigger distances and IDs match `game_data/level_1.json` (Entities 10, 14, 13, 1, 3).
   - Test that `game_data/.level_default.json` references an existing level file (`game_data/level_1.json`).
   - Test that silenced systems (`WhispererSystem.ENABLED = False`, boss taunt loop in `game_state.py:1476`, and `ObjectiveDisplay`) remain confirmed disabled.
   - Test headless rendering of `SideNotification(1280, 720)` with each retrieved config without unhandled exceptions.
3. Implement `tests/test_editor_plugins_roundtrip_integrity.py`:
   - Systemic test verifying all editor plugins and configuration managers can load, parse, and round-trip their corresponding game data files without data corruption or loss:
     - `popup_controller.py` & `PopupSceneManager`
     - `level_editor.py`
     - `wave_editor.py`
     - `notification_editor.py` & `NotificationConfigManager`
     - `cutscene_editor.py`
     - `boss_editor.py`
     - `wizard_editor.py`
     - `blood_zombie_editor.py`
     - `the_eye.py` & `TheEyePerceptionManager`
     - `entity_editor.py` & `HitboxRegistry`
     - `power_icons_editor.py`
     - `controls_editor.py` & `ControlsManager`
     - `player_editor.py`
     - `shadow_editor.py` & `ShadowRegistry`
     - `storyline_editor.py` & `StorylineConfigManager`
     - `voiceover_editor.py`
   - For each plugin/manager, verify clean loading, atomic save pattern, preservation of external keys, and backup pruning to <= 5.
4. Run verification tests:
   `$env:PYTHONPATH="."; .\.venv\Scripts\python.exe -m pytest tests/test_game_state_popup_triggers.py tests/test_editor_plugins_roundtrip_integrity.py`
5. Create `TEST_READY.md` at project root with runner command, coverage summary, and feature checklist.
6. Deliver report to `c:\Users\me\Documents\game\Pixel-Runner\.agents\teamwork\teamwork_worker_m3\handoff.md`.
