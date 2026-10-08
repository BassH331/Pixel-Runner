# Pixel Runner — Workspace State & Task Tracker

This document provides persistent context tracking, component mappings, active domain states, and task history across agent sessions.

---

## 1. Repository Architecture Map

| Domain Layer | Location / Key Modules | Primary Role |
| :--- | :--- | :--- |
| **Engine & Physics** | `src/game/entities/player.py`<br>`src/game/states/`<br>`v3x_zulfiqar_gideon/` | Frame-rate independent physics ($\delta = \text{dt} \times 60$), entity FSM, level loop. |
| **Shared Game Logic** | `src/game/shared/difficulty_core.py` | Canonical difficulty scaling formulas used by both client and API. |
| **Narrative & Metagame** | `src/game/systems/corruption_manager.py`<br>`src/game/systems/whisperer_system.py`<br>`src/game/systems/relic_manager.py` | Cursed corruption progression, psychological pacing, milestone force-barks. |
| **Tooling & Perception** | `the_eye.py`<br>`src/game/systems/the_eye_manager.py`<br>`notification_editor.py` | 3D Interactive Story Map & Tree, real-time pop-up notification GUI editor. |
| **Backend API Service** | `pixel-runner-api/api/index.py`<br>`pixel-runner-api/api/services/` | FastAPI telemetry, leaderboards, database service, security headers. |
| **UI & Presentation** | `src/game/ui/animated_dialogue_renderer.py`<br>`src/game/ui/hud_overlay.py`<br>`src/game/ui/player_ui.py` | 4-bar streamlined HUD (HP, MP, SP, Corruption), typewriter dialogue, safe glyph fallbacks. |
| **Audio & SFX** | `src/game/audio/audio_manager.py`<br>`src/game/audio/voiceover_manager.py` | Data-driven audio triggers, voiceover playback, missing asset fallbacks. |
| **Verification Suite** | `tests/`<br>`pixel-runner-api/tests/` | 348 unit & integration tests across engine, UI, tooling, and narrative systems. |

---

## 2. Recent Audit & Remediation Milestone Log

| Phase / Target | Description | Status | Verification |
| :--- | :--- | :--- | :--- |
| **Baseline Tests** | Fixed audio config and lightning effect baseline tests. | **COMPLETED** (`1c8e55fc`) | Pytest passed |
| **SEC-01 (API Auth)** | Enforced `X-API-Write-Secret` header authorization and payload bounds. | **COMPLETED** (`6e5b77eb`) | API test suite passed |
| **SEC-03 (Repo Clean)**| Removed 4,982 committed venv files from Git tracking. | **COMPLETED** (`c20718c4`) | Clean git index |
| **GAME-01 (Combat)** | Corrected defend damage math `max(1, math.ceil(amount * 0.3))`. | **COMPLETED** (`6ff4761a`) | `test_player_damage.py` passed |
| **PERF-01 (Physics)** | Scaled physics displacement by normalized dt with sub-stepping. | **COMPLETED** (`f071801f`) | `test_physics_timestep.py` passed |
| **TEST-01 (API Tests)**| Created full FastAPI backend test suite `test_telemetry_api.py`. | **COMPLETED** (`868c899e`) | API test suite passed |
| **ARCH-01 (Difficulty)**| Extracted unified canonical `DifficultyCore` for client & API. | **COMPLETED** (`46ee3a6b`) | `test_difficulty_sync.py` passed |
| **SEC-04 (Privacy)** | Added user telemetry consent toggle and settings persistence. | **COMPLETED** (`91e491c8`) | `test_telemetry_opt_out.py` passed |
| **UI Font Fallback** | Added missing glyph & zero-width handling in dialogue renderer. | **COMPLETED** (`c90e54e5`) | `test_animated_dialogue_renderer.py` passed |
| **KIMI-AI-01 (LLM)** | Moonshot Kimi AI Director service with zero-cost fallback & async client. | **COMPLETED** | `test_ai_director_api.py` & `test_ai_director_client.py` passed |
| **KIMI-NARRATIVE-02** | Slow-Mo Vignette Narrative Overlay, Dual-Choice Buffs & Guard-Break Anti-Turtling AI. | **COMPLETED** | `test_cinematic_narrative_overlay.py` passed |
| **NARRATIVE-BOOK-01** | Magic Book single-frame asset (`magic book _16.png`) & Andras Avatar real-time 12.5 FPS animation. | **COMPLETED** | `test_hud_overlay.py` passed (316/316 total) |
| **WIN-CROSS-PLATFORM** | Windows cross-platform setup (`setup_env.py`, `run.bat`), Python 3.14 + `pygame-ce` compatibility, Win32 ctypes clipboard, UTF-8 encoding guards, path separator normalization, and file-handle release. | **COMPLETED** | 326/326 tests passed (316 client/engine + 10 API) |
| **DISPLAY-PARITY-01** | Cross-platform ground level alignment ($Y=606$), `PixelRunnerEngine` hardware scaling (`pg.SCALED | pg.RESIZABLE`), desktop auto-maximization above Windows taskbar, F11/Alt+Enter fullscreen toggling, and `--fullscreen` CLI argument. | **COMPLETED** | `test_engine_presentation.py` passed (333/333 total tests) |
| **DEMON-PACING-02** | Demon avatar animation pacing slowed to 0.28s (~3.5 FPS), removal of unnecessary "[1] Awaken" prompt in favor of natural "[SPACE] Continue", multi-line word-wrapped dialogue card, and 18 visual forensic screenshots. | **COMPLETED** | `test_cinematic_narrative_overlay.py` passed |
| **NARRATIVE-POLISH-01** | Magic Book scaled to 1.5 (~96px), permanent removal of magenta/purple placeholder boxes (fixed Wizard_NPC and Ronin paths, safe transparent fallbacks), SideNotification hold duration extended to 8.5s+ with dynamic word-count scaling, Grimoire first-encounter and first-kill cursed taunts, Blood Zombie pre-battle cinematic mini-cutscene with animated idle avatar, and saucy in-combat pop-up taunts mixing archaic and modern vulgarity. | **COMPLETED** | `test_narrative_polish.py` + full test suite passed (314 passed) |
| **NOTIFICATION-EDITOR-01** | Interactive GUI Pop-up Notification Plugin Editor (`notification_editor.py`), data-driven config manager (`NotificationConfigManager`), hot-reloading architecture, live 1280x720 in-game simulation staging with playback freeze/scrub, curated theme presets (`Gothic Gold`, `Blood & Bone`, `Arcane Void`, `Grimoire Leather`, `Sleek Dark Glass`), and full parameter controls for timing, geometry, colors, and typography. | **COMPLETED** | `test_notification_editor.py` + full test suite passed (320/320 client tests) |
| **THE-EYE-STORY-MAP-01** | Next-level interactive story map and perception controller plugin (`the_eye.py`, `TheEyePerceptionManager`), animated All-Seeing Eye pupil tracking, 16 chronological journey checkpoints from 0m to 36,000m across 4 narrative acts, entity dossiers with animated sprite portraits, and automated timestamped backups of `storyline_config.json` and `level_1.json`. | **COMPLETED** | `test_the_eye.py` passed |
| **THE-EYE-UNITY-TREE-02** | 3D Interactive Story Tree & Dialogue Controller plugin ("The Eye"): Real-time 3D Celestial Tree (Yggdrasil of Discord) with 360° mouse drag orbit rotation, smooth zooming, panning, auto-orbit, golden angle spiral branching, depth-sorted Painter's algorithm, raycast node picking, dual view modes (`3D Interactive Tree` vs `2D List TreeView`), explicit `is_taunt: bool` toggle switch (`Dialogue (Narrative Overlay)` vs `Taunt (In-Combat Bark)`), dual live simulation (`SideNotification` popup with audio bark vs `CinematicNarrativeOverlay`), clean "Save Changes" persistence with timestamped backups, and zero missing glyph boxes. | **COMPLETED** | `test_the_eye.py` + full test suite passed (340/340 tests passed) |
| **PERF-CRASH-AUDIT-01** | Violent forensic crash & performance audit: (1) Resolved boss defeat re-entrancy deadlock in `EventBus.emit()` by transitioning from non-reentrant `threading.Lock` to `threading.RLock()` and taking snapshot copies of subscriber sets during cascaded emits (`RelicDropped` from `EntityDied`); (2) Fixed 64-bit Win32 ctypes clipboard pointer truncation in `level_editor.py` (`c_void_p` restype/argtypes); (3) Replaced off-screen fall death `sys.exit(0)` with clean lethal damage & game-over transition; (4) Eliminated hot-loop disk I/O in `ShadowRegistry.get_profile()` (throttled to 1.5s, 93% speedup from 0.081s to 0.006s); (5) Recycled 1280x720 dark overlay surface in `GameState.draw()` saving ~220 MB/s GC pressure; (6) Implemented frustum culling and layer grouping for props in `EnvironmentManager`; (7) Cached static HUD font rendering in `TutorialOverlay` and `PlayerUI`; (8) Guarded audio channel bounds and removed destructive `pg.mixer.quit()` from `AudioManager.__del__`. | **COMPLETED** | `test_boss_defeat_pipeline.py` + full test suite passed (344/344 tests passed) |
| **NARRATIVE-PSYCH-STREAMLINE-01** | Narrative & UI Streamlining: Eliminated HUD cognitive clutter by retiring the redundant 5th Soul Harvest visual meter; elevated Corruption into the 4th primary resource gauge alongside HP, MP, and SP with dynamic tier gradients (Pure Amethyst $\to$ Tainted Crimson $\to$ Void Hellfire), glowing core, and tier badge; extended `WhispererSystem` ambient combat bark cooldown from 20s to 45s and reduced kill bark chance to 15% to eliminate text fatigue; enforced priority `force=True` milestone barks on critical corruption thresholds (33%, 50%, 66%, 90%), relics, and boss encounters; added defensive parameter defaults to `GenericNPC.get_dialogue()` and `WizardNPC.get_dialogue()`. | **COMPLETED** | `tests/test_narrative_streamline.py` passed (348/348 total tests passed) |
| **RELIC-OVERLAY-FIX-01** | Post-Boss Relic Cutscene Soft-Lock & Lifecycle Preservation: (1) Resolved post-boss freeze/lock where `RelicRevealState` was instantiated with `manager=None` and ignored gamepad inputs, trapping controller players permanently; (2) Upgraded `v3x_zulfiqar_gideon`'s `StateManager` to recognize `is_overlay=True` states without deactivating underlying state lifecycles (`on_exit`) and layer-drawing underlying states; (3) Integrated `RelicRevealState` as a non-destructive in-game overlay inside `GameState` (`_show_relic_reveal`), keeping telemetry tracker handles open, preventing audio cuts, and keeping background world rendering active; (4) Added complete Xbox 360 controller button (`JOYBUTTONDOWN`), keyboard, and mouse dismissal support. | **COMPLETED** | `tests/test_boss_defeat_pipeline.py` passed (349/349 total tests passed) |
| **PACT-REVIVAL-FIX-01** | Demonic Pact Resuscitation & Entity Property Setters: (1) Resolved runtime crash `AttributeError: property 'is_dead' of 'Player' object has no setter` during demonic pact acceptance in `GameState._on_pact_choice`; (2) Added read-write `@property` setters to `Player` for `is_dead`, `health`, `max_health`, `mana`, `max_mana`, `stamina`, `max_stamina`, and `is_enhanced`; (3) Supported string names in `Player.set_state()`; (4) Fixed missing `PlayerState` import in `src/game/states/game_state.py`. | **COMPLETED** | `test_cinematic_narrative_overlay.py` + full test suite passed (350/350 total tests passed) |
| **PROP-DEPTH-AND-INTEGRITY-01** | Foreground Prop Depth & Level Data Integrity: (1) Implemented dual-pass prop depth pipeline in `EnvironmentManager` (`foreground_pass`), `GameState` (pass 1 behind actors, pass 2 in front), and `level_editor.py` Stage 5 visual canvas with `[FRONT]` / `[BEHIND]` badges and "👁 In Front of Player: ON/OFF" inspector toggle; (2) Permanent deletion persistence & zero silent rollbacks: eliminated auto-commits on `pg.QUIT`, level switch, and widget toggles; editor saves strictly on explicit user action ("Save Level ✓"); (3) Cleaned `game_data/level_1.json` down to the canonical 7 encounters (`[10, 14, 11, 12, 13, 1, 3]`), permanently eliminating the 9 unwanted narrative NPCs/lore popups; (4) Hardened `TheEyePerceptionManager` against resurrecting deleted entities; (5) CIA Triad hardening across repo. | **COMPLETED** | 366/366 tests passed (100% pass rate) |
| **PLUGIN-COMMIT-INTEGRITY-02** | Multi-Plugin Commit Integrity & 3-Way Merge: (1) Fixed cross-plugin rollback and clobbering bug where plugins (`the_eye.py`, `wave_editor.py`, `level_editor.py`) overwrote disk changes with stale in-memory snapshots; (2) Implemented intelligent 3-way merge in `level_editor.py` comparing `pending`, `backup`, and fresh `disk_data` to preserve external changes to `spawn_zones`, perception, boss sequences, and checkpoints; (3) Hardened `the_eye_manager.py` to re-read fresh level JSON on save, strictly update dialogue on existing disk entities, and never resurrect deleted entities; (4) Hardened `wave_editor.py` to re-read and atomically merge `spawn_zones`; (5) Enforced atomic file writes (`.tmp_<pid>` + `os.replace`) with UTF-8 encoding across all plugin save paths; (6) Prevented 0-byte corrupt backup files and pruned backups to maximum 5 entries; (7) Added 6 comprehensive cross-plugin integration tests in `test_plugin_commit_integrity.py`. | **COMPLETED** | 372/372 tests passed (100% pass rate) |
| **GIT-SYNC-01 (Repo Hygiene)** | Git Index & Asset Synchronization: Sanitized `.gitignore` with `screenshot_*.png` and `*env_production*` rules to prevent credential leakage, staged 1,656 untracked sprite and animation assets, preserved NPC dialogue and combat taunt updates in `level_1.json` and `storyline_config.json`, committed cleanly, and pushed to `origin/main`. | **COMPLETED** (`74d56a75`) | Working tree clean, branch in sync with `origin/main` |
| **PLUGIN-CIA-HARDENING-03** | Systemic Plugin CIA & Commit Integrity Enforcement: (1) Created unified atomic file save & disk merge module `src/game/utils/atomic_save.py` (`atomic_write_json`, `atomic_merge_json`, `create_validated_backup`, `prune_backups`); (2) Refactored ALL plugins, editors, and config managers (`blood_zombie_editor.py`, `boss_editor.py`, `wizard_editor.py`, `entity_editor.py`/`HitboxRegistry`, `shadow_editor.py`/`ShadowRegistry`, `power_icons_editor.py`, `controls_editor.py`/`ControlsManager`, `cutscene_editor.py`, `voiceover_editor.py`, `NotificationConfigManager`, `StorylineConfigManager`, `save_config_and_lock`) to eliminate direct truncating `open(..., "w")` calls; (3) Enforced atomic POSIX/Win32 file replaces (`.tmp_<pid>_<uuid>` + `os.fsync` + `os.replace`), validated non-empty backup creation, automatic 5-archive backup pruning, and fresh disk re-reading/merging prior to commit; (4) Created comprehensive 10-test verification suite in `tests/test_all_plugins_cia_integrity.py`. | **COMPLETED** | 100% pass rate across all test suites |

---

## 3. Current System Health & Invariants

- **Test Suite Status**: **100% pass rate** across all test suites.
- **Universal Plugin CIA & Atomic Commit Standard**: ALL editor plugins and configuration managers must save file data exclusively via `src/game/utils/atomic_save.py` (`atomic_write_json`, `atomic_merge_json`). Direct `open(..., "w")` writes to target configuration/level paths without atomic temporary files (`.tmp_<pid>_<uuid>`), `os.fsync`, and `os.replace` are strictly prohibited.
- **Multi-Plugin Write Isolation Invariant**: Editors (`level_editor.py`, `the_eye.py`, `wave_editor.py`, `blood_zombie_editor.py`, `boss_editor.py`, `wizard_editor.py`, `power_icons_editor.py`, etc.) must re-read fresh target JSON from disk, merge strictly domain-owned keys or use 3-way merging, and write atomically via temporary files (`.tmp_<pid>_<uuid>`) and `os.replace` to eliminate race conditions and stale snapshot overwriting.
- **Entity Deletion Persistence Invariant**: Secondary editors and perception managers (`TheEyePerceptionManager`) must never re-inject deleted entities into `level_1.json` when saving dialogue or perception attributes.
- **Backup Sanitization Standard**: Backup operations must verify source content is non-empty (`content.strip()`) before writing `.backup_*` files, and automatically prune backups to retain at most 5 latest valid archives.
- **Player Entity Encapsulation Invariant**: `Player` entity exposes read-write properties (`health`, `max_health`, `is_dead`, `is_enhanced`) ensuring systems modifying combat state or initiating resuscitation never raise `AttributeError`.
- **Overlay State Lifecycle Invariant**: In-game cutscene overlays (`RelicRevealState`, `CinematicNarrativeOverlay`, `TutorialOverlay`) must never trigger `GameState.on_exit()` or prematurely terminate audio channels and telemetry tracker handles.
- **Controller Parity Invariant**: All dismissable prompts and overlays must listen to `pg.JOYBUTTONDOWN` alongside `pg.KEYDOWN` and `pg.MOUSEBUTTONDOWN` to guarantee 100% playable controller parity.
- **HUD Resource Invariant**: Primary UI displays strictly 4 core horizontal gauges (Health, Mana, Stamina, Corruption). Visual 5th Soul Harvest bar retired to protect player attention, while maintaining full backwards compatibility for soul attributes (`souls_collected`, `add_souls`, etc.).
- **Psychological Pacing Invariant**: Ambient narrative barks are throttled to a minimum 45.0s cooldown; critical narrative turning points (corruption thresholds, relics, boss encounters) bypass cooldowns via `force=True`.
- **NPC Dialogue Invariant**: NPC `get_dialogue` calls must safely provide default values (`corruption_level: float = 0.0`, `relics_collected: list | None = None`) to prevent missing positional argument exceptions.
- **Event Bus Reentrancy Standard**: All event bus locks use reentrant locks (`RLock`) and iterate over snapshot copies to guarantee cascading events (e.g. boss death -> relic drop -> narrative trigger) cannot deadlock the main game loop while audio loops.
- **Audio Lifecycle Standard**: `AudioManager` safeguards against empty channel arrays when mixer is disabled/headless; never calls `pg.mixer.quit()` on garbage collection.
- **Render Allocation Standard**: Zero per-frame full-screen surface allocations in hot draw loops; static text rendering cached.
- **Cross-Platform Standard**: All file I/O explicitly enforces `encoding="utf-8"`; asset paths normalized with `os.sep` -> `/`; clipboard uses native Win32 `ctypes` on Windows without Tkinter crashes.
- **Physics & Resolution Standard**: Logical resolution locked to sovereign 1280x720 via `pg.SCALED`; ground level mathematically locked to $Y=606$; movement scaled by `dt * 60.0`.
- **Window Presentation Standard**: Window auto-maximizes on PC to fill the screen cleanly above the Windows taskbar; full-screen toggle hotkeys (`F11`, `Alt+Enter`) available at all times.
- **Font Rendering Standard**: All custom TTF rendering wrapped in zero-width glyph fallback handler.
- **Telemetry Auth Standard**: All write requests require `X-API-Write-Secret` header when configured.
- **Difficulty Sync Standard**: Both client and API inherit formulas directly from `DifficultyCore`.

---

## 4. Active Working Memory & Checklist

- [x] Baseline test fix & repository cleanup
- [x] Core security & performance remediation
- [x] UI font glyph fallback handling
- [x] Kimi LLM AI Director Specification (`kimi_ai_director_design_spec.md`) & Implementation
- [x] Slow-Motion Vignette & Dialogue Prompt UI (`CinematicNarrativeOverlay`)
- [x] Anti-Turtling Guard-Break AI & Player Guard Stun (`PlayerState.GUARD_STUN`)
- [x] Lore Engine Integration (`storyline_config.json`: Kaelen, Elysia, Voragis, Candora)
- [x] Narrative Transformation Phase 5: Demonic Pact Injection (Andras, Fallen Warrior theme)
- [x] Magic Book Single-Frame (`magic book _16.png`) & Real-Time Andras Avatar Animation
- [x] Windows Cross-Platform Setup & Test Parity (326/326 tests passing)
- [x] Cross-Platform Resolution & Dirt Road Ground Level Parity ($Y=606$)
- [x] Window Presentation & Desktop Auto-Maximization (Clean dock above taskbar + Fullscreen toggle)
- [x] Demon Animation Pacing Slowdown (0.28s / ~3.5 FPS) & Dialogue Prompt Simplification (`[SPACE] Continue`)
- [x] Visual Verification via 18 Forensic In-Engine Screenshots
- [x] Magic Book Resizing (Scale 1.5 in Level 1 & Entity Dimensions)
- [x] Elimination of Purple/Magenta Placeholder Boxes & Path Fixes (`Wizard_NPC`, `Ronin`)
- [x] SideNotification Extended Hold Times (8.5s minimum + Dynamic Text Scaling)
- [x] Grimoire First Encounter & First Kill Thematic Taunts
- [x] Blood Zombie Pre-Battle Animated Cutscene & Saucy Period/Modern Vulgar In-Combat Taunts
- [x] Pop-Up Notification GUI Plugin Editor (`notification_editor.py`) with Real-Time Timing, Layout, Colors, & Hot-Reloading
- [x] 'The Eye' Interactive Story Map & Perception Controller Plugin (`the_eye.py`, `TheEyePerceptionManager`)
- [x] 'The Eye' Unity-Style Hierarchical Story Resource Tree & Dialogue Controller with Explicit Taunt Switch (`the_eye.py`)
- [x] Mini-Boss Defeat Crash & Lock Elimination (`EventBus` RLock reentrancy, snapshot copies, relic drop recursion)
- [x] Win32 64-bit Ctypes Clipboard Access Violation Fix (`GlobalAlloc`/`GlobalLock` 64-bit pointers)
- [x] Engine Profiling & Lag Remediations (Throttled hot disk I/O, prop frustum culling, Surface allocation recycling, font caching)
- [x] Narrative & UI Streamline (HUD reduced from 5 to 4 core bars; Soul Harvest visual meter retired, Corruption elevated as central narrative spine)
- [x] Dynamic Corruption Bar Aesthetics (Pure Amethyst -> Tainted Crimson -> Void Hellfire with status badge and glowing core)
- [x] Psychological Flow & Whisperer Pacing (Combat cooldown expanded 20s -> 45s, kill barks down to 15%, priority milestone force-override for thresholds, relics, bosses)
- [x] Robust NPC Corruption Mirror Integration (`GenericNPC` & `WizardNPC` default parameter safety)
- [x] Dedicated Invariant Verification (`tests/test_narrative_streamline.py` 4/4 passing, 348/348 full suite passing)
- [x] Mini-Boss Defeat Relic Cutscene Soft-Lock & Gamepad Input Parity Fix (`RELIC-OVERLAY-FIX-01`, 349/349 tests passing)
- [x] Demonic Pact Resuscitation & Entity Property Setters (`PACT-REVIVAL-FIX-01`, 350/350 tests passing)
- [x] Foreground Prop Depth & Level Data Integrity (`PROP-DEPTH-AND-INTEGRITY-01`, 366/366 tests passing)
- [x] Multi-Plugin Commit Integrity & 3-Way Merge (`PLUGIN-COMMIT-INTEGRITY-02`, 372/372 tests passing)
- [ ] Active Feature / Next Objective: *(Ready for new development tasks)*


