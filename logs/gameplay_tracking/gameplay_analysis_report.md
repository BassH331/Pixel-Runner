# Gameplay Telemetry & Game Feel Analysis Report

**Generated on**: 2026-06-21 10:29:51
**Log File**: `session_20260621_102816_001.jsonl`

---

## 📊 Session Statistics

| Metric | Value |
|---|---|
| **Session Duration** | 77.8 seconds |
| **Average Frame Rate** | 61.2 FPS |
| **Total Frames Logged** | 4631 |
| **Control Latency (Avg)** | 3.5 ms |
| **Dodge Rolls Triggered** | 0 |
| **Dashes Triggered** | 0 |
| **Hits Avoided via Dodge** | 0 |
| **Animation Early Interrupts** | 0 |

---

## 🔄 Player State Distribution

| State | Time Spent (%) |
|---|---|
| IDLE | 27.8% |
| SPECIAL_ATTACK | 27.5% |
| ATTACK_POWER | 10.4% |
| ATTACK_SMASH | 8.5% |
| RUN | 6.8% |
| DEFEND | 6.5% |
| ATTACK_THRUST | 5.4% |
| TRANSFORM | 4.4% |
| HURT | 1.5% |
| JUMP_DOWN | 0.7% |
| JUMP_UP | 0.6% |

---

## 🧠 God Mode AI & Game Feel Recommendations

- **Dodge mechanics underutilized.** No rolls or dashes were recorded. If the boss combat is too punishing, recommend lowering boss spell tracking.
- **Excellent responsiveness (3.5ms average input-to-state delay).** The controls feel crisp.

---

*Use the **Player Animation Configurator** (`player_editor.py`) to apply these recommendations by adjusting animation speeds, loop settings, or input/movement locks for the respective states.*
