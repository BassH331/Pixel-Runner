---
name: pixel-runner-domain-roles
description: Specialized domain mindsets and invariants for Pixel Runner codebase development across Engine, Backend API, UI/Graphics, and QA.
---

# Pixel Runner Domain Roles Skill

This skill defines the technical mindsets, scope boundaries, and non-negotiable invariants for working within the core domains of **Pixel Runner**.

---

## 🎮 Domain Role 1: Engine & Systems Specialist (`engine-core`)

- **Scope**: Game loop, delta-time physics, entity state machine (`src/game/entities/`), collision handling, camera, tilemaps, level management.
- **Invariants**:
  - **Timestep**: $\delta = \text{dt} \times 60.0$. Multiply frame-rate velocity by $\delta$; multiply acceleration/gravity by $\delta^2$.
  - **Sub-Stepping**: Divide movement into iterations if horizontal or vertical displacement exceeding 16px.
  - **State Machine**: Entity FSM states must implement `enter()`, `update(dt)`, `exit()`, `handle_input()`.

---

## 🌐 Domain Role 2: Backend API & Telemetry (`backend-api`)

- **Scope**: FastAPI endpoints (`pixel-runner-api/api/index.py`), database client (`database.py`), authorization middleware, telemetry validation schemas.
- **Invariants**:
  - **Authorization**: Write endpoints MUST verify `X-API-Write-Secret` header when configured.
  - **Validation**: Pydantic models must enforce field limits (`ge`, `le`, `max_length`) and array bounds (max 50 events, 100 frame samples).
  - **Import Safety**: Database client initialization MUST NOT crash on missing environment secrets.

---

## 🎨 Domain Role 3: UI, Graphics & Audio (`ui-graphics`)

- **Scope**: `AnimatedDialogueRenderer`, HUD overlays, fonts (`Abaddon Bold.ttf`), particle VFX, audio managers (`AudioManager`, `VoiceoverManager`).
- **Invariants**:
  - **Font Resilience**: `font.render(char)` MUST be wrapped in `try...except pg.error` to catch missing or zero-width glyphs (e.g. em-dash `—`).
  - **Audio Safety**: Missing audio files MUST be logged as warnings, allowing text/gameplay to continue smoothly without throwing uncaught exceptions.

---

## 🧪 Domain Role 4: QA & Verification (`qa-test`)

- **Scope**: Test execution in `tests/` and `pixel-runner-api/tests/`, boundary test generation, physics parity validation.
- **Invariants**:
  - **Zero Regressions**: 100% test pass rate MUST be maintained (`PYTHONPATH=. ./venv/bin/pytest`).
  - **New Feature Coverage**: Every code modification MUST be accompanied by dedicated unit tests.
