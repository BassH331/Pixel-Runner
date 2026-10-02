# Pixel Runner Pre-Change Engineering Audit — Verification Report

## 1. Verification Summary

This report provides independent verification of the previously reported audit findings. All findings have been investigated via static analysis, code tracing, and local benchmarking, without applying any modifications to the repository.

**Overall Status**: The majority of the previous audit's findings are **CONFIRMED**, though one is **PARTIALLY CONFIRMED** due to nuances in Git tracking. 

---

## 2. Finding-by-Finding Classification & 3. Evidence

### SEC-01: Unauthenticated Telemetry POST Endpoints
**Classification:** **CONFIRMED** (CRITICAL)

* **Files & Lines:** 
  * `pixel-runner-api/api/index.py`: lines 215-263 (`post_session`, `post_events`, `post_frames`)
* **Evidence & Data Flow:**
  * **Authentication:** Missing. The `verify_write_access()` check is used for configuration updates (`/configs/{config_type}` at line 193) but is entirely absent from the telemetry endpoints.
  * **Rate Limiting:** Missing. A repository-wide search confirms no `rate_limit` or throttling logic exists anywhere in the API.
  * **Payload Limits:** Missing. `post_events` and `post_frames` accept `List[EventItem]` and `List[FrameSampleItem]` payloads. FastAPI/Pydantic by default does not restrict the length of these lists.
  * **Data Flow:** `Client -> POST /telemetry/* -> API endpoint (no auth) -> db.insert_* -> Supabase`.
* **Impact:** 
  * **Adaptive Difficulty Influence:** Yes. `post_session` inserts directly into the `pixel_runner.sessions` table, which is read by `DifficultyManager.evaluate_sessions()`. A client could fabricate sessions with `boss_defeated=True` and `duration_seconds=5` to maliciously skew the global difficulty curve.
  * **Cost/Resource Exhaustion:** Yes. An attacker can repeatedly send massive JSON arrays to `/telemetry/events`, causing unbounded inserts into Supabase, potentially exhausting database storage and incurring severe metered billing costs.

### SEC-02: Live Secrets in Local .env Files
**Classification:** **PARTIALLY CONFIRMED** (HIGH - Reassessed from Critical)

* **Files & Lines:** 
  * `pixel-runner-api/.env` (Local file, not in Git)
  * `.env.local` (Local file, not in Git)
  * `pixel-runner-api/.env.local` (Local file, not in Git)
  * `pixel-runner-api/.env.example` (Tracked in Git, but contains no real secrets)
* **Evidence:**
  * **Secrets present on disk:** `SUPABASE_SERVICE_KEY` (live admin key), `UPSTASH_REDIS_REST_TOKEN`, `VERCEL_OIDC_TOKEN` (live JWT), and `API_WRITE_SECRET` (`Bassline_333`).
  * **Git Tracking:** **None of the files containing actual secrets are tracked in Git.** They are properly ignored. The only tracked file is `pixel-runner-api/.env.example`. I verified this using `git ls-files .env* pixel-runner-api/.env*` and inspecting git history.
* **Impact:** While the secrets are present locally on the developer workstation (and thus vulnerable to local malware or accidental disclosure), they are *not* exposed in the repository or to other contributors. Therefore, this is a local environment hygiene issue, not an active repository leak.

### ARCH-01: Duplicated DifficultyManager
**Classification:** **CONFIRMED** (MEDIUM - Reassessed from Critical)

* **Files & Lines:**
  * `src/game/boss/difficulty_manager.py`
  * `pixel-runner-api/api/services/difficulty.py`
* **Evidence:**
  * Both files contain a `DifficultyManager` class with duplicated logic for `evaluate_sessions`, `PRESETS`, `SLIDER_BOUNDS`, and `BASELINE_CONFIG`.
  * **Divergence:** A diff reveals they are already diverging. The client version (`src/game/boss/difficulty_manager.py`) contains an `adjust_difficulty_level` method (for dynamic step-based scaling) that is missing from the API version.
* **Impact:** High risk of drift. If tuning constants are changed in one file and not the other, the cloud's recommendations will not match the client's execution. It is a severe architectural smell, but does not pose an immediate security or application-crashing threat.

### SEC-03: ~4,982 venv Files Committed
**Classification:** **CONFIRMED** (HIGH)

* **Files & Lines:** `venv/` directory.
* **Evidence:**
  * `git ls-files | grep venv | wc -l` returns exactly 4,982 files.
  * The history shows they were committed in `d604f4d4 feat: implement per-boss difficulty tracking...`.
* **Impact:** Bloats repository size and poses a supply chain risk. Any contributor could stealthily modify a vendored binary (e.g., in `venv/bin/` or deeply nested inside site-packages).

### PERF-01: Frame-Rate-Dependent Player Physics
**Classification:** **CONFIRMED** (HIGH)

* **Files & Lines:** `src/game/entities/player.py` lines 1723-1767 (`_apply_gravity`, `_apply_movement`)
* **Evidence:**
  * Operations like `self._gravity += self._GRAVITY_ACCELERATION` and `self.rect.y += int(self._gravity)` completely ignore the `dt` (delta-time) parameter.
  * **Benchmark Results:** Running a headless benchmark applying exactly 1 second of gravity (calling `_apply_gravity()` $FPS$ times) yields radically different results:
    * 30 FPS: `y=910`
    * 60 FPS: `y=1987`
    * 144 FPS: `y=8825`
* **Impact:** The game plays at entirely different speeds depending on the hardware or monitor refresh rate.

### GAME-01: Defend Damage Reduction Truncates
**Classification:** **CONFIRMED** (HIGH)

* **Files & Lines:** `src/game/entities/player.py` lines 1314-1319 (`take_damage`)
* **Evidence:** 
  * The code reads: `amount = int(amount * 0.3)`
  * Mathematically, if an attack deals `3.0` damage, `3.0 * 0.3 = 0.9`. `int(0.9)` evaluates to `0`. 
  * Because many enemies deal small base damage (e.g. 1.0 or 2.0), defending makes the player entirely immune to these attacks rather than reducing the damage by 70%.

### SEC-04: No Telemetry Consent Gate
**Classification:** **CONFIRMED** (MEDIUM - Reassessed from High)

* **Files & Lines:** `src/game/services/telemetry_client.py` lines 42, 49, 63, etc.
* **Evidence:**
  * The only condition preventing telemetry dispatch is the environment variable check: `os.environ.get("DISABLE_TELEMETRY") == "1"`.
  * Data sent includes combat performance, session duration, frame-by-frame positional data (`FrameSampleItem`), and framerate.
* **Impact:** Does not contain explicit PII (like names or emails), but does collect usage data persistently linked to a `session_id`. Legal/product decisions are required to determine if GDPR/CCPA applies, but technically, the collection is opt-out via environment variable only.

### TEST-01: Zero API Endpoint Test Coverage
**Classification:** **CONFIRMED** (HIGH)

* **Files & Lines:** `tests/` directory.
* **Evidence:**
  * No test files targeting the API exist (`test_api*` or similar). The test suite only covers the Pygame client logic.
* **Impact:** Unauthenticated endpoints (SEC-01) and DB integration logic have no automated regression safety net.

---

## 4. Severity Reassessment

1. **SEC-01 (Telemetry Auth):** CRITICAL. Confirmed data poisoning and resource exhaustion vectors.
2. **SEC-02 (Local Secrets):** HIGH (Down from Critical). Secrets are live, but they are *not* checked into Git. This is a local risk, not a public leak.
3. **SEC-03 (Venv Committed):** HIGH. Supply chain risk and repo bloat.
4. **PERF-01 (Frame Dependence):** HIGH. Severely impacts gameplay consistency.
5. **GAME-01 (Defend Damage):** HIGH. Fundamentally breaks game balance for low-damage enemies.
6. **TEST-01 (API Tests):** HIGH. Total lack of API regression coverage.
7. **ARCH-01 (Duplicated Logic):** MEDIUM (Down from Critical). Causes technical debt and subtle bugs, but does not crash the game or expose data.
8. **SEC-04 (Consent Gate):** MEDIUM (Down from High). Usage analytics, but no direct PII.

---

## 5. Newly Discovered Blocking Issues

During the verification process, no *additional* critical blocking issues (such as arbitrary file access or RCE) were discovered in the evaluated scope. The architecture is otherwise solid (EventBus, Squad AI). However, the lack of API rate limiting exacerbates SEC-01.

---

## 6. False Positives / Unsupported Claims

* **SEC-02 (Local Secrets in Git):** The implication that the repository is publicly leaking secrets is a **FALSE POSITIVE**. The files `.env.local` and `pixel-runner-api/.env` are properly ignored by Git and do not exist in the repository's history. Only the developer's local machine is affected.

---

## 7. Required Regression Tests

Before implementing fixes, the following regression tests must be written:
1. **GAME-01:** A unit test for `Player.take_damage()` where `amount=2.0` and `player.state=DEFEND`. It must assert that `health` is reduced by at least `1` (or the intended float value) rather than `0`.
2. **PERF-01:** A physics test (similar to the benchmark used in this verification) asserting that `player.rect.y` reaches approximately the same position after 1 real-world second of gravity, regardless of whether `update()` is called 30 or 144 times.
3. **SEC-01:** Integration tests for `/telemetry/session`, `/events`, and `/frames` asserting that requests without proper authorization headers return `401 Unauthorized`.

---

## 8. Recommended Remediation Order

1. **SEC-01:** Implement `verify_write_access` (or a dedicated telemetry token validation) and basic payload size limits on all `POST /telemetry/*` endpoints. (Blocks malicious DB writes).
2. **SEC-03:** Run `git rm -r --cached venv/` and commit the removal. (Stops repo bloat and supply chain risks).
3. **GAME-01:** Fix the `take_damage` math truncation (e.g., using `math.ceil` or `max(1, amount * 0.3)`).
4. **PERF-01:** Refactor `_apply_gravity` and `_apply_movement` to multiply fixed increments by `dt_sec`.
5. **ARCH-01:** Extract the `DifficultyManager` into a shared module or implement a CI check that ensures both files remain perfectly synced.
6. **TEST-01:** Write basic FastAPI endpoint tests.
7. **SEC-04:** Implement a main menu UI toggle that writes `DISABLE_TELEMETRY=1` to a local settings file.
8. **SEC-02:** Rotate the local developer secrets as a general best practice.
