# Pixel Runner — Hive Mind & Multi-Agent Customization Rules

These rules govern agent behavior, parallel subagent orchestration, domain role division, and project state tracking for the **Pixel Runner** repository.

---

## 1. Core Operating Philosophy: Hive Mind with Domain Individualism

1. **Decoupled Parallel Execution**:
   - When facing multi-domain or complex tasks (e.g. backend API + client engine + UI renderer + test suite), break the work down into independent domain sub-tasks.
   - Delegate domain sub-tasks to concurrent subagents or specialized mindsets, allowing each domain specialist to operate with single-topic focus.
   - The primary agent acts as the **Hive Mind Orchestrator**, collecting, synthesizing, and integrating domain results while maintaining system coherence.

2. **Strict Separation of Concept from Execution Prompts**:
   - **Concepts (Rules & Domain Constraints)**: Reside statically in `.agents/AGENTS.md` and domain SKILL documentation.
   - **Execution Prompts**: Dynamically generated for specific tasks, containing explicit inputs, file targets, quantitative acceptance criteria, and expected outputs without repeating static architectural concepts.

3. **Persistent Work & Mindset Tracking**:
   - Before executing complex multi-step work, inspect `.agents/TRACKER.md`.
   - Update `.agents/TRACKER.md` whenever core architecture changes, new features are completed, or domain boundaries are modified.

---

## 2. Specialized Domain Roles for Pixel Runner

Every task in Pixel Runner must be evaluated through one or more of the following specialized mindsets:

### 🎮 Role 1: Engine & Systems Specialist (`engine-core`)
- **Domain Scope**: Pygame main loop (`main.py`), state machine (`v3x_zulfiqar_gideon`), entity logic (`src/game/entities/`), physics (`_apply_gravity`, `_apply_movement`), collision detection, camera, level management, and math utils.
- **Invariants**:
  - All physics calculations **must** be frame-rate independent, scaled by normalized delta-time factor ($\delta = \text{dt} \times 60.0$).
  - Position sub-stepping must be enforced when movement vector magnitude exceeds 16px.
  - No blocking calls or heavy I/O in main game loop iteration.

### 🌐 Role 2: Backend API & Telemetry Specialist (`backend-api`)
- **Domain Scope**: FastAPI backend service (`pixel-runner-api/`), Supabase/Database service (`database.py`), authorization headers (`X-API-Write-Secret`), Pydantic validation models, rate limiting, payload caps.
- **Invariants**:
  - API endpoints must enforce strict security validation (header secrets, field bounds `ge`/`le`/`max_length`, array caps).
  - Database instantiation must be wrapped safely to prevent import-time crashes when external environment secrets are absent.

### 🎨 Role 3: UI, Graphics & Audio Specialist (`ui-graphics`)
- **Domain Scope**: Dialogue rendering (`AnimatedDialogueRenderer`), HUD overlays (`hud_overlay.py`), cutscenes, font handling (`Abaddon Bold.ttf`), VFX particle emitters, and audio triggers (`AudioManager`, `VoiceoverManager`).
- **Invariants**:
  - All font rendering calls **must** handle missing or zero-width glyphs safely (`try...except pg.error` fallbacks).
  - Never allow non-ASCII or unmapped unicode characters to crash renderer loops.
  - Audio and asset loading must fail gracefully with warnings rather than raising uncaught exceptions.

### 🧪 Role 4: QA & Verification Specialist (`qa-test`)
- **Domain Scope**: Test suite in `tests/` and `pixel-runner-api/tests/`, continuous verification, physics parity validation, boundary testing.
- **Invariants**:
  - Every bug fix or feature addition **must** include a corresponding unit or integration test.
  - Test suite pass rate must remain at 100% (zero regressions).

---

## 3. Parallel Workflows & Execution Rules

1. **Task Partitioning**:
   - Identify domain boundaries: `Engine`, `API`, `UI`, `QA`.
   - Ensure sub-tasks do not edit the exact same lines of code simultaneously to avoid merge conflicts.

2. **Verification & State Sync**:
   - After sub-tasks complete, run `PYTHONPATH=. ./venv/bin/pytest` to confirm overall repository health.
   - Log completed work and updated state in `.agents/TRACKER.md`.
