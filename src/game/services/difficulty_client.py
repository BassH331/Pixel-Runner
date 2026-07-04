import os
import json
import threading
import urllib.request
import urllib.error
from typing import Any, Dict, Optional

# Default API URL. Can be overridden via environment variable.
API_BASE_URL = os.environ.get("PIXEL_RUNNER_API_URL", "https://pixel-runner-wheat.vercel.app")


class DifficultyFetchHandle:
    """Thread-safe handle for a background difficulty-recommendation fetch.

    Exposes is_done()/result() as two separate calls (rather than a single
    poll() that returns None both while pending and once finished-with-nothing)
    so callers can tell "still waiting" apart from "finished, no recommendation".
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._done = False
        self._result: Optional[Dict[str, Any]] = None

    def _set_result(self, result: Optional[Dict[str, Any]]) -> None:
        with self._lock:
            self._result = result
            self._done = True

    def is_done(self) -> bool:
        with self._lock:
            return self._done

    def result(self) -> Optional[Dict[str, Any]]:
        """The recommended config dict, or None if the fetch failed/found nothing.
        Only meaningful once is_done() is True."""
        with self._lock:
            return self._result


class DifficultyClient:
    """Fetches a cloud-aggregated difficulty recommendation for a boss in a
    background thread, mirroring TelemetryClient's async submission pattern.
    Never blocks the caller; any network failure resolves to a None result so
    the caller can safely fall back to the boss's already-loaded defaults."""

    @classmethod
    def fetch_recommendation_async(cls, boss_key: str) -> DifficultyFetchHandle:
        handle = DifficultyFetchHandle()
        threading.Thread(
            target=cls._fetch, args=(boss_key, handle), daemon=True
        ).start()
        return handle

    @classmethod
    def _fetch(cls, boss_key: str, handle: DifficultyFetchHandle) -> None:
        url = f"{API_BASE_URL.rstrip('/')}/api/difficulty/{boss_key}"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Pixel-Runner Game Client"})
            with urllib.request.urlopen(req, timeout=3.0) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode("utf-8"))
                    handle._set_result(data.get("config"))
                    return
        except urllib.error.URLError as e:
            print(f"[DIFFICULTY CLIENT ERROR] Connection error fetching {boss_key}: {e}")
        except Exception as e:
            print(f"[DIFFICULTY CLIENT ERROR] Unexpected error fetching {boss_key}: {e}")
        handle._set_result(None)
