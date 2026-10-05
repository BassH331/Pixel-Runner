---
name: pixel-runner-watsonx
description: Use when working with the watsonx.ai dynamic dialogue integration in Pixel-Runner — covers the WatsonxDialogueClient, prompt design, rate limit management, and fallback behaviour.
---

# Pixel-Runner — watsonx.ai Dynamic Dialogue

Reference this skill when implementing, extending, or debugging the `WatsonxDialogueClient` and the dynamic Andras taunt system.

> **Prerequisite**: activate `pixel-runner-narrative` for context on `WhispererSystem` and the bark config format.

---

## Lite Plan Limits (as of July 2025)

| Limit | Value |
|---|---|
| Free tokens/month | 300,000 |
| Rate limit | 2 requests / second |
| Model | `ibm/granite-3-3-8b-instruct` |
| API endpoint | `POST /ml/v1/text/chat` |

At ~300 tokens per boss taunt (prompt + response), the free tier covers roughly **1,000 boss encounters per month** — well within solo development and playtesting needs. The 2 req/sec rate limit is not a constraint in practice because boss spawns occur at most once every few minutes.

> The text generation API (`/ml/v1/text/generation`) is **deprecated as of February 2026** — always use the chat endpoint `/ml/v1/text/chat`.

---

## Client

**Class**: `WatsonxDialogueClient` in `src/game/services/watsonx_dialogue_client.py`

### Constructor

```python
WatsonxDialogueClient(fallback_barks: list[str] | None = None)
```

- Reads `WATSONX_API_KEY`, `WATSONX_PROJECT_ID`, and `WATSONX_URL` from environment at construction time.
- `fallback_barks`: optional list of static strings used when the API is unavailable. If `None`, falls back to the module-level `FALLBACK_LINES` safety net.
- The `ibm_watsonx_ai` package is imported lazily on first API call — missing package degrades gracefully to fallback-only mode without crashing.
- `_available` is set to `False` if credentials are absent; all calls immediately use fallback.

### Environment Variables

Read from a `.env` file (never committed). Copy `.env.example` to `.env` and fill in values:

```
WATSONX_API_KEY=your_ibm_cloud_api_key
WATSONX_PROJECT_ID=your_watsonx_project_id
WATSONX_URL=https://us-south.ml.cloud.ibm.com
```

`.env.example` is committed to the repo. `.env` is git-ignored via `.env*` pattern with `!.env.example` negation.

### Primary Method

```python
def generate_andras_taunt(
    self,
    corruption: float,
    relics: list[str],
    boss_name: str,
    callback: callable,
) -> None
```

- **Does NOT block** — submits work to a `ThreadPoolExecutor(max_workers=1)` and returns immediately.
- When the result is ready (or fallback selected on error), calls `callback(text: str)` from the background thread.
- The caller must handle thread safety — `WhispererSystem` uses `_pending_lock` + `_pending_watsonx_bark` for this.
- **Fallback**: on any exception, unavailable client, or empty response, calls `callback` with a random bark from `fallback_barks`.

### Shutdown

```python
def shutdown(self) -> None
```

Call on game exit to release the thread pool. `GameState.on_exit()` calls `self.watsonx_client.shutdown()`.

---

## Thread-Safety Pattern in WhispererSystem

`WhispererSystem` (`src/game/systems/whisperer_system.py`) uses a lock + pending slot pattern:

```python
# In __init__
self._pending_watsonx_bark: Optional[str] = None
self._pending_lock = threading.Lock()

# Callback (called from background thread)
def _on_result(text: str) -> None:
    with self._pending_lock:
        self._pending_watsonx_bark = text

# In update(dt) — game loop thread
with self._pending_lock:
    bark = self._pending_watsonx_bark
    self._pending_watsonx_bark = None

if bark and self._cooldown_remaining <= 0:
    self._fire(Speaker.ANDRAS, bark)
```

The game loop picks up the result on the next frame after the background thread writes it — safe, non-blocking, and consistent with the existing cooldown system.

---

## When It Is Called

Dynamic generation is used **only** for the `DarkRonin` final boss encounter to minimise token spend:

| Case | Condition |
|---|---|
| Andras's dynamic boss spawn taunt | Boss entry has `"watsonx_taunt": true` in `boss_dialogue` config |

All other dialogue (NPCs, regular enemies, non-final bosses, relic reveals) uses static config strings — zero tokens consumed.

### Config Flag

In `game_data/storyline_config.json`, the `DarkRonin` entry under `boss_dialogue` has:

```json
"DarkRonin": {
  "watsonx_taunt": true,
  ...
}
```

`WhispererSystem.notify_boss_spawn(boss_name)` checks this flag and routes to `_request_watsonx_bark()` if `True` and `_watsonx_client` is not `None`. Otherwise it falls back to `_try_bark("on_boss_spawn")` as normal.

---

## How WhispererSystem Routes the Call

```python
def notify_boss_spawn(self, boss_name: str) -> None:
    boss_cfg = self._boss_dialogue_config.get(boss_name, {})
    use_watsonx = boss_cfg.get("watsonx_taunt", False) and self._watsonx_client is not None
    if use_watsonx:
        self._request_watsonx_bark(boss_name)
    else:
        self._try_bark("on_boss_spawn")
```

`self._boss_dialogue_config` is populated from `config.get("boss_dialogue", {})` in `__init__`.

---

## Prompt Design

Keep prompts under **200 tokens** to maximise the budget available for the response.

### System Prompt (constant, defined in `WatsonxDialogueClient.SYSTEM_PROMPT`)

```
You are Andras, Marquis of Discord — a demon lord who speaks in archaic, measured tones.
You are manipulative, patient, and utterly certain of your own victory.
You never break character. You address the protagonist directly, as 'runner'.
Respond with a single line of dialogue — one or two sentences maximum.
No stage directions, no quotation marks, no narration. Just the spoken line.
```

### User Turn (built per call)

```
The runner has arrived at the {boss_name} encounter.
Their corruption level is {corruption:.0f} out of 100.
Relics they have collected: {relic_summary}.
Speak to them now.
```

This keeps the user turn under 50 tokens for typical inputs.

---

## Adding New Dynamic Lines

To make a boss's spawn bark use dynamic generation instead of a static config line:

1. In `game_data/storyline_config.json`, set `"watsonx_taunt": true` in the boss's entry under `boss_dialogue`:

```json
"NewBossName": {
  "role": "corrupted_paragon",
  "pre_fight": ["Fallback static line used if API fails or times out."],
  "watsonx_taunt": true,
  ...
}
```

2. Ensure at least one `on_boss_spawn` bark exists in `whisperer_barks.andras` — this feeds the `WatsonxDialogueClient` fallback pool at startup.
3. No code changes needed. `WhispererSystem` checks `watsonx_taunt` automatically and routes to `WatsonxDialogueClient` when the flag is present.

---

## Environment Setup

1. Copy `.env.example` to `.env` in the `Pixel-Runner/` project root:

```powershell
Copy-Item Pixel-Runner/.env.example Pixel-Runner/.env
```

2. Fill in the values:
   - **API Key**: IBM Cloud → Manage → Access (IAM) → API Keys → Create.
   - **Project ID**: watsonx.ai Studio → open your project → Manage tab → General → Project ID.

3. Confirm `.env` is git-ignored. `.gitignore` has `.env*` with a `!.env.example` negation — `.env` is never committed.

---

## Fallback Behaviour Summary

| Condition | Behaviour |
|---|---|
| API call succeeds | Generated line delivered via callback, displayed on next frame |
| Any exception (network, auth, parse) | Random bark from `fallback_barks` delivered via callback |
| `WATSONX_API_KEY` or `WATSONX_PROJECT_ID` not set | `_available = False`; all calls immediately use fallback |
| `ibm-watsonx-ai` package not installed | `_get_client()` catches `ImportError`; `_available = False`; fallback used |
| Callback arrives while cooldown active | Bark is dropped (consumed from `_pending_watsonx_bark` but not fired) |

The game is never blocked and never crashes due to a missing or slow API response.
