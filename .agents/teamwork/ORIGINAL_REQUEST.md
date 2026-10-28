# Original User Request

## Initial Request — 2026-10-28T18:00:00Z

Resolve all pop-up notification appearance issues and eliminate JSON and data flow mismatches across the game runtime, configuration files, and all project editor plugins. Ensure all configured in-game pop-ups trigger seamlessly and data reading/writing remains consistent across the entire development workflow without regressions.

Integrity mode: development

## Requirements

### R1. Pop-up Configuration and Runtime Appearance
Fix missing configuration keys and data discrepancies so that all in-game pop-ups appear at their intended triggers during gameplay:
- Add missing event entries referenced in `src/game/states/game_state.py` (`event_book_ponder`, `event_first_encounter`, `event_forest_inquiry_1400m`) to `game_data/scene_popups_config.json`.
- Correct the prologue awakening configuration (`event_prologue_awakening`) so its title and narrative text describe the prologue awakening rather than the Fabricator's Enforcer boss encounter.
- Align trigger distances and entity IDs in `game_data/scene_popups_config.json` with entity definitions in `game_data/level_1.json`.
- Update `game_data/.level_default.json` to point to a valid, existing level file.
- Keep currently silenced systems (WhispererSystem, boss combat taunts, and ObjectiveDisplay/ItemLoreSystem) disabled as configured.

### R2. End-to-End JSON and Data Parity Across All Editor Plugins
Audit and synchronize the data reading and writing workflows across all editor plugins and tools in the repository (including `popup_controller.py`, `level_editor.py`, `notification_editor.py`, `cutscene_editor.py`, `boss_editor.py`, and related editors):
- Ensure every plugin reads the canonical game JSON schemas without missing fields, key errors, or parsing crashes.
- Ensure all plugin save operations preserve external keys, follow atomic and non-clobbering file write patterns, and write valid JSON matching game runtime expectations.
- Eliminate discrepancies where plugins expect different data types, naming conventions, or file structures than the game runtime uses.

### R3. Automated Verification and Integrity Test Suite
Provide comprehensive automated test scripts that verify JSON integrity and plugin compatibility:
- Implement automated test scripts validating that all editor plugins can load, parse, and round-trip their corresponding game data files without data corruption or loss.
- Implement programmatic verification confirming that all pop-up triggers in `GameState` resolve to existing, valid config entries in `scene_popups_config.json`.
- Ensure all existing tests in the project pass with zero regressions.

## Acceptance Criteria

### Pop-up Configuration and Runtime Display
- [ ] All scene pop-up event IDs referenced in `src/game/states/game_state.py` (`event_prologue_awakening`, `event_book_ponder`, `event_first_encounter`, `event_first_kill`, `event_forest_inquiry_1400m`, `event_moonstone_keeper`, `event_soul_quota_betrayal`, `event_level_complete`) are defined in `game_data/scene_popups_config.json`.
- [ ] `event_prologue_awakening` in `game_data/scene_popups_config.json` contains title and body text specific to the prologue awakening, not the Fabricator's Enforcer.
- [ ] Entity trigger distances and entity IDs in `game_data/scene_popups_config.json` match the entity coordinates and IDs in `game_data/level_1.json` (including the Sealed Book at ~1013m and boss encounters).
- [ ] `game_data/.level_default.json` references an existing level configuration file (e.g., `"game_data/level_1.json"`).
- [ ] Silenced systems (`WhispererSystem.ENABLED = False`, commented-out boss combat taunts, inactive ObjectiveDisplay) remain disabled.

### Editor Plugin Data Flow and Schema Parity
- [ ] `popup_controller.py` loads, edits, displays, and saves all scene pop-up notifications and level entity links without schema errors or dropped fields.
- [ ] All editor plugins (`level_editor.py`, `notification_editor.py`, `cutscene_editor.py`, `boss_editor.py`, etc.) load and parse their corresponding JSON configurations without unhandled exceptions or data loss.
- [ ] Saving configurations from any editor plugin preserves external fields and maintains atomic save and backup safety standards.

### Test Suite and Verification
- [ ] Dedicated automated test scripts verify JSON schema validity and round-trip load/save operations across all editor plugins.
- [ ] Headless test verifies that every pop-up trigger path in `GameState` successfully retrieves a valid notification configuration without falling back to hardcoded error states.
- [ ] Full existing test suite (`PYTHONPATH=. pytest`) passes with 100% success rate (zero regressions).

