# Pixel Runner — Workspace State & Task Tracker

This document provides persistent context tracking, component mappings, active domain states, and task history across agent sessions.

---

## 1. Repository Architecture Map

| Domain Layer | Location / Key Modules | Primary Role |
| :--- | :--- | :--- |
| **Engine & Physics** | `src/game/entities/player.py`<br>`src/game/states/`<br>`v3x_zulfiqar_gideon/` | Frame-rate independent physics ($\delta = \text{dt} \times 60$), entity FSM, level loop. |
| **Shared Game Logic** | `src/game/shared/difficulty_core.py` | Canonical difficulty scaling formulas used by both client and API. |
| **Backend API Service** | `pixel-runner-api/api/index.py`<br>`pixel-runner-api/api/services/` | FastAPI telemetry, leaderboards, database service, security headers. |
| **UI & Presentation** | `src/game/ui/animated_dialogue_renderer.py`<br>`src/game/ui/hud_overlay.py` | Typewriter dialogue rendering, HUD, safe glyph fallback handling. |
| **Audio & SFX** | `src/game/audio/audio_manager.py`<br>`src/game/audio/voiceover_manager.py` | Data-driven audio triggers, voiceover playback, missing asset fallbacks. |
| **Verification Suite** | `tests/`<br>`pixel-runner-api/tests/` | 308+ unit & integration tests. |

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

---

## 3. Current System Health & Invariants

- **Test Suite Status**: **333/333 passed** (323 engine/gameplay tests + 10 backend API tests; 100% pass rate).
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
- [ ] Active Feature / Next Objective: *(Ready for new development tasks)*
