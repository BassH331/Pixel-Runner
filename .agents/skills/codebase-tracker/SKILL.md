---
name: codebase-tracker
description: Work tracking and active context management protocols for maintaining .agents/TRACKER.md across agent turns and subagent workflows.
---

# Codebase Tracker Skill

This skill defines the procedures for reading, updating, and maintaining persistent project memory in `.agents/TRACKER.md`.

---

## 1. Context Read Protocol (Turn Start)

At the beginning of a complex request or new task session:
1. Inspect `.agents/TRACKER.md`.
2. Review active domain layers, current system health, recent milestone commits, and pending checklist items.
3. Align proposed edits with established system invariants (e.g. physics scaling, telemetry auth headers, font rendering fallbacks).

---

## 2. Context Write Protocol (Task Completion)

Upon completing a feature, bug fix, or refactoring task:
1. Run test suite to verify project health: `PYTHONPATH=. ./venv/bin/pytest`.
2. Update `.agents/TRACKER.md` with:
   - Newly completed task/commit hash.
   - Any added or updated domain components.
   - Updated system invariants or active checklist items.
3. Ensure the tracker remains concise, accurate, and structured.
