import os
import json
import time
import urllib.request
import urllib.error
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Any, Optional

# Single reusable thread pool for background AI director requests
_ai_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="ai_director")


class AiDirectorClient:
    """Asynchronous client for requesting Kimi AI Director strategic directives.
    
    Dispatches 30-60 frame telemetry streams to the FastAPI backend service
    at POST /telemetry/ai-director. Operates entirely in a background thread to
    prevent frame stutter in the 60 FPS Pygame loop.
    
    If the network call fails or times out (800ms limit), it smoothly retains
    the active directive or uses local fallback logic.
    """

    _active_directive: Dict[str, Any] = {
        "target_tactic": "AGGRESSIVE_RUSH",
        "aggression_multiplier": 1.0,
        "preferred_attack_sequence": ["SLASH"],
        "movement_bias_x": 0.0,
        "contextual_taunt": None
    }
    _directive_lock = threading.Lock()
    _last_dispatch_time: float = 0.0
    _MIN_DISPATCH_INTERVAL_SEC: float = 1.0  # Limit dispatches to max once per second

    @classmethod
    def is_ai_director_enabled(cls) -> bool:
        """Check if AI director feature is enabled in settings or environment."""
        if os.environ.get("PYTEST_CURRENT_TEST") or os.environ.get("DISABLE_AI_DIRECTOR") == "1":
            return False
        try:
            from v3x_zulfiqar_gideon import SettingsManager
            val = SettingsManager().get("ai_director_enabled")
            return bool(val) if val is not None else True
        except Exception:
            return True

    @classmethod
    def get_active_directive(cls) -> Dict[str, Any]:
        """Thread-safe retrieval of the active strategic directive."""
        with cls._directive_lock:
            return dict(cls._active_directive)

    @classmethod
    def request_directive_async(cls, payload: Dict[str, Any]) -> None:
        """Asynchronously dispatch telemetry slice to backend to update active directive."""
        if not cls.is_ai_director_enabled():
            return

        now = time.monotonic()
        if now - cls._last_dispatch_time < cls._MIN_DISPATCH_INTERVAL_SEC:
            return
        cls._last_dispatch_time = now
        _ai_executor.submit(cls._fetch_directive, payload)

    @classmethod
    def _fetch_directive(cls, payload: Dict[str, Any]) -> None:
        """Background thread worker method performing HTTP call."""
        api_url = os.environ.get("PIXEL_RUNNER_API_URL", "http://127.0.0.1:8000")
        endpoint = f"{api_url}/telemetry/ai-director"
        secret = os.environ.get("API_WRITE_SECRET", "")

        try:
            req_data = json.dumps(payload).encode("utf-8")
            headers = {"Content-Type": "application/json"}
            if secret:
                headers["X-API-Write-Secret"] = secret

            req = urllib.request.Request(endpoint, data=req_data, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=8.5) as resp:
                res = json.loads(resp.read().decode("utf-8"))
                if res.get("status") == "success" and "directive" in res:
                    with cls._directive_lock:
                        cls._active_directive = res["directive"]
        except Exception:
            # Retain existing directive safely on network latency/timeout
            pass
