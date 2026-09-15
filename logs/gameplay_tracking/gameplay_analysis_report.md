# Gameplay Telemetry & Game Feel Analysis Report

**Generated on**: 2026-09-15 08:54:40
**Log File**: `session_20260915_085111_001.jsonl`

---

## 📊 Session Statistics

| Metric | Value |
|---|---|
| **Session Duration** | 52.2 seconds |
| **Average Frame Rate** | 60.7 FPS |
| **Total Frames Logged** | 3104 |
| **Control Latency (Avg)** | 0.0 ms |
| **Dodge Rolls Triggered** | 0 |
| **Dashes Triggered** | 0 |
| **Hits Avoided via Dodge** | 0 |
| **Animation Early Interrupts** | 0 |

---

## 🔄 Player State Distribution

| State | Time Spent (%) |
|---|---|
| IDLE | 91.5% |
| RUN | 7.4% |
| JUMP_DOWN | 0.6% |
| JUMP_UP | 0.5% |

---

## 🧠 God Mode AI & Game Feel Recommendations

- **Dodge mechanics underutilized.** No rolls or dashes were recorded. If the boss combat is too punishing, recommend lowering boss spell tracking.
- **Player is highly stationary (91.5% Idle).** Consider making the boss AI cast zoning spells to force player movement.

---

*Use the **Player Animation Configurator** (`player_editor.py`) to apply these recommendations by adjusting animation speeds, loop settings, or input/movement locks for the respective states.*
