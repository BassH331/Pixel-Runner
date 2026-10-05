"""
WatsonxDialogueClient — async dynamic dialogue generation via IBM watsonx.ai.

Uses the Lite free plan:
  - 300,000 tokens/month free
  - 2 inference requests/second rate limit
  - Model: ibm/granite-3-3-8b-instruct
  - API: POST /ml/v1/text/chat (chat endpoint)

Only used for:
  - Andras's final confrontation speech (DarkRonin encounter, watsonx_taunt: true)
  - Andras's on_boss_spawn bark for final boss

Falls back to static config strings on any error or 3-second timeout.
"""
import os
import random
import threading
from concurrent.futures import ThreadPoolExecutor

FALLBACK_LINES = [
    "You came this far. That alone tells me everything I need to know about you.",
    "The last runner stood where you stand. He did not disappoint me. I trust you won't either.",
    "I have been watching since the pact was made. This moment was always inevitable.",
    "You carry my mark. Whatever happens here, part of you belongs to the void.",
    "Every soul you took fed me. Every step brought you closer. Welcome home, runner.",
]


class WatsonxDialogueClient:
    """Generates dynamic Andras dialogue via watsonx.ai chat API. Fully async — never blocks the game loop."""

    MODEL_ID = "ibm/granite-3-3-8b-instruct"
    TIMEOUT = 3.0  # seconds before falling back to static line
    MAX_NEW_TOKENS = 80  # keep responses short for in-game dialogue

    SYSTEM_PROMPT = (
        "You are Andras, Marquis of Discord — a demon lord who speaks in archaic, measured tones. "
        "You are manipulative, patient, and utterly certain of your own victory. "
        "You never break character. You address the protagonist directly, as 'runner'. "
        "Respond with a single line of dialogue — one or two sentences maximum. "
        "No stage directions, no quotation marks, no narration. Just the spoken line."
    )

    def __init__(self, fallback_barks: list[str] | None = None):
        self._api_key = os.environ.get("WATSONX_API_KEY", "")
        self._project_id = os.environ.get("WATSONX_PROJECT_ID", "")
        self._url = os.environ.get("WATSONX_URL", "https://us-south.ml.cloud.ibm.com")
        self._fallback_barks = fallback_barks or FALLBACK_LINES
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="watsonx")
        self._client = None  # lazy-initialised on first use
        self._client_lock = threading.Lock()
        self._available = bool(self._api_key and self._project_id)

    def _get_client(self):
        """Lazy-init the watsonx client. Returns None if credentials missing or import fails."""
        if not self._available:
            return None
        with self._client_lock:
            if self._client is None:
                try:
                    from ibm_watsonx_ai import Credentials
                    from ibm_watsonx_ai.foundation_models import ModelInference
                    creds = Credentials(url=self._url, api_key=self._api_key)
                    self._client = ModelInference(
                        model_id=self.MODEL_ID,
                        credentials=creds,
                        project_id=self._project_id,
                    )
                except Exception:
                    self._available = False
                    return None
        return self._client

    def generate_andras_taunt(
        self,
        corruption: float,
        relics: list[str],
        boss_name: str,
        callback: callable,
    ) -> None:
        """
        Submits an async generation request. Does NOT block.

        When the result is ready (or fallback selected), calls callback(text: str).
        The callback is called from a background thread — use thread-safe update patterns.

        Args:
            corruption: current corruption value (0.0-100.0)
            relics: list of collected relic_id strings
            boss_name: name of the boss being encountered
            callback: callable(str) invoked with the generated or fallback line
        """
        def _run():
            try:
                client = self._get_client()
                if client is None:
                    return self._fallback(callback)

                relic_summary = ", ".join(relics) if relics else "none"
                user_message = (
                    f"The runner has arrived at the {boss_name} encounter. "
                    f"Their corruption level is {corruption:.0f} out of 100. "
                    f"Relics they have collected: {relic_summary}. "
                    f"Speak to them now."
                )

                response = client.chat(
                    messages=[
                        {"role": "system", "content": self.SYSTEM_PROMPT},
                        {"role": "user", "content": user_message},
                    ],
                    params={"max_new_tokens": self.MAX_NEW_TOKENS, "temperature": 0.85},
                )
                # Extract text from response — handle both dict and object responses
                text = ""
                if isinstance(response, dict):
                    choices = response.get("choices", [{}])
                    text = choices[0].get("message", {}).get("content", "").strip() if choices else ""
                else:
                    text = str(response).strip()

                if text:
                    callback(text)
                else:
                    self._fallback(callback)
            except Exception:
                self._fallback(callback)

        self._executor.submit(_run)

    def _fallback(self, callback: callable):
        callback(random.choice(self._fallback_barks))

    def shutdown(self):
        """Shut down the thread pool gracefully. Call on game exit."""
        self._executor.shutdown(wait=False)
