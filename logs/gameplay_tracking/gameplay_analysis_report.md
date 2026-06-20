# Gameplay Telemetry & Game Feel Analysis Report

**Generated on**: 2026-06-20 15:20:46
**Log File**: `session_20260620_151918_001.jsonl`

---

## 📊 Session Statistics

| Metric | Value |
|---|---|
| **Session Duration** | 71.4 seconds |
| **Average Frame Rate** | 61.5 FPS |
| **Total Frames Logged** | 4013 |
| **Control Latency (Avg)** | 0.0 ms |
| **Dodge Rolls Triggered** | 7 |
| **Dashes Triggered** | 0 |
| **Hits Avoided via Dodge** | 0 |
| **Animation Early Interrupts** | 1 |

---

## 🔄 Player State Distribution

| State | Time Spent (%) |
|---|---|
| ATTACK_THRUST | 36.2% |
| IDLE | 25.5% |
| RUN | 13.1% |
| TRANSFORM | 10.2% |
| HURT | 6.7% |
| ROLL | 5.4% |
| JUMP_DOWN | 1.5% |
| JUMP_UP | 1.3% |

---

## 🧠 God Mode AI & Game Feel Recommendations

- **Dodge Roll / Dash invincibility feels too narrow.** The damage avoidance success rate is low (0.0%). Consider **increasing** the *grants_invincibility* duration or increasing the animation speed of `ROLL` / `DASH` by **+0.05** so it completes faster.

---

*Use the **Player Animation Configurator** (`player_editor.py`) to apply these recommendations by adjusting animation speeds, loop settings, or input/movement locks for the respective states.*
