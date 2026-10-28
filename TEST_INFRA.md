# E2E Test Infra: Pixel-Runner Pop-up Appearance & Editor Plugin JSON Parity

## Test Philosophy
- Opaque-box, requirement-driven. No dependency on implementation design.
- Methodology: Category-Partition + BVA + Pairwise + Workload Testing.
- Zero tolerance for regression across existing 427+ client tests and 10 API tests.

## Feature Inventory & Test Coverage Mapping
| # | Feature | Source (requirement) | Tier 1 | Tier 2 | Tier 3 |
|---|---------|---------------------|:------:|:------:|:------:|
| F1 | Add Missing Event IDs (`event_book_ponder`, `event_first_encounter`, `event_forest_inquiry_1400m`) | ORIGINAL_REQUEST §R1 | 5 | 5 | ✓ |
| F2 | Fix Prologue Awakening Text ("The Awakening") | ORIGINAL_REQUEST §R1 | 5 | 5 | ✓ |
| F3 | Align Entity Trigger Distances (Entity 10 @ 1013m) | ORIGINAL_REQUEST §R1 | 5 | 5 | ✓ |
| F4 | Correct Default Level Pointer (`level_1.json`) | ORIGINAL_REQUEST §R1 | 5 | 5 | ✓ |
| F5 | Silenced Systems Invariant (`WhispererSystem`, Boss Taunts, ObjectiveDisplay) | ORIGINAL_REQUEST §R1 | 5 | 5 | ✓ |
| F6 | Pop-up Controller & Manager Hardening (`float(None)`, `int(eid)`, top-level keys) | ORIGINAL_REQUEST §R2 | 5 | 5 | ✓ |
| F7 | Editor Plugin Atomic Commit Parity (`atomic_save.py`, backup pruning) | ORIGINAL_REQUEST §R2 | 5 | 5 | ✓ |
| F8 | GameState Pop-up Trigger Test Suite (`test_game_state_popup_triggers.py`) | ORIGINAL_REQUEST §R3 | 5 | 5 | ✓ |
| F9 | Editor Plugin Round-Trip Test Suite (`test_editor_plugins_roundtrip_integrity.py`) | ORIGINAL_REQUEST §R3 | 5 | 5 | ✓ |
| F10 | Full Regression & Adversarial Verification | ORIGINAL_REQUEST §R3 | 5 | 5 | ✓ |

## Test Architecture
- **Headless Test Runner**:
  - Global Pygame dummy driver fixtures configured via `tests/conftest.py`.
  - Invocation: `$env:PYTHONPATH="."; .\.venv\Scripts\python.exe -m pytest` or `PYTHONPATH=. pytest`.
- **Dedicated Test Suites**:
  - `tests/test_game_state_popup_triggers.py`: Tests that every pop-up trigger path in `GameState` successfully retrieves a valid notification configuration without falling back to hardcoded error states, validates entity distance alignment, default level pointer validity, and verifies silenced systems remain disabled.
  - `tests/test_editor_plugins_roundtrip_integrity.py`: Systemic test covering all editor plugins and configuration managers (`popup_controller.py`, `level_editor.py`, `notification_editor.py`, `cutscene_editor.py`, `boss_editor.py`, `wizard_editor.py`, `blood_zombie_editor.py`, `the_eye.py`, `wave_editor.py`, `entity_editor.py`, `power_icons_editor.py`, `controls_editor.py`, `player_editor.py`, `shadow_editor.py`, `storyline_editor.py`, `voiceover_editor.py`, etc.), confirming clean loading of canonical JSONs, atomic saving, external key retention, and backup pruning.

## Real-World Application Scenarios (Tier 4)
| # | Scenario | Features Exercised | Complexity |
|---|----------|--------------------|------------|
| 1 | Full Level 1 Progression Pop-up Sequence (Prologue Awakening -> Sealed Book -> First Encounter -> First Kill -> 1400m Inquiry -> Demon Time -> Moonstone Keeper -> Gatekeeper -> Soul Quota -> Enforcer -> Level Complete) | F1, F2, F3, F5, F8 | High |
| 2 | Multi-Plugin Interleaved Edit & Save Round-Trip (`popup_controller` + `level_editor` + `wave_editor` + `boss_editor` modifying shared game data) | F6, F7, F9 | High |
| 3 | Corrupt/Missing Config Recovery & Resilient Fallback Gracefulness | F1, F6, F7, F8 | Medium |
| 4 | Offline CI Headless Execution & Test Suite Zero-Regression Verification | F5, F8, F9, F10 | Medium |
| 5 | Editor Atomic File Write Interruption & Backup Recovery Validation | F7, F9 | High |

## Coverage Thresholds
- Tier 1: ≥5 per feature
- Tier 2: ≥5 per feature (boundary and corner cases)
- Tier 3: Pairwise coverage of major feature interactions
- Tier 4: ≥5 realistic application scenarios

