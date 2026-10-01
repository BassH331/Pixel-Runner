---
name: hive-mind-orchestrator
description: Strategy and execution workflow for parallel multi-agent orchestration, task decomposition, prompt/concept separation, and hive-mind state synchronization.
---

# Hive-Mind Orchestrator Skill

This skill provides protocols for acting as the **Hive Mind Orchestrator** in Pixel Runner, enabling efficient parallel problem solving, strict separation of high-level concepts from execution prompts, and seamless merging of work.

---

## 1. Task Decomposition & Parallelization Protocol

When a multi-faceted task (feature, bug, refactor, audit) is presented:

1. **Analyze Domain Boundaries**:
   - Classify sub-tasks into decoupled domain buckets:
     - 🎮 **Engine & Physics (`engine-core`)**: `src/game/entities/`, physics, collisions, state machine.
     - 🌐 **Backend & API (`backend-api`)**: `pixel-runner-api/`, endpoints, authorization, schemas.
     - 🎨 **UI & Presentation (`ui-graphics`)**: `src/game/ui/`, fonts, particles, cutscenes, audio.
     - 🧪 **QA & Verification (`qa-test`)**: `tests/`, test creation, validation, regression checks.

2. **Decouple File Touches**:
   - Ensure sub-tasks target non-overlapping files or independent modules to eliminate merge conflicts.

3. **Concept vs. Prompt Separation**:
   - **Do NOT** repeat domain rules or codebase definitions in subagent prompts.
   - **Do** provide minimal, crisp execution prompts containing:
     - Specific input files and target lines.
     - Clear, quantitative acceptance criteria.
     - Expected outputs/return data.

---

## 2. Subagent Execution & Synthesis Protocol

1. **Launch Independent Subtasks**:
   - Spawn domain-focused tasks for parallel or focused execution.
   - Maintain a high-level state register of active sub-tasks.

2. **Synthesize & Integrate**:
   - Upon subtask completion, review outputs for consistency against system invariants:
     - Physics timestep ($\delta = \text{dt} \times 60.0$).
     - API authorization (`X-API-Write-Secret`).
     - Font zero-width glyph handling.
     - Unified `DifficultyCore` logic.
   - Run verification commands (`PYTHONPATH=. ./venv/bin/pytest`) to confirm integration health.

3. **Update Work State**:
   - Log completed milestones and new invariants in `.agents/TRACKER.md`.
