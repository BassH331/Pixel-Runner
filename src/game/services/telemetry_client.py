import os
import json
import time
import urllib.request
import urllib.error
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List

from .local_cache import LocalCache

# Default API URL. Can be overridden via environment variable.
API_BASE_URL = os.environ.get("PIXEL_RUNNER_API_URL", "https://pixel-runner-wheat.vercel.app")

# Single reusable thread pool — eliminates per-call Thread() creation overhead
_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="telemetry")


class TelemetryClient:
    """Asynchronous telemetry client that submits gameplay tracking metrics, events,
    and frame samples to the cloud API via a persistent thread pool.
    
    Uses batch coalescing to accumulate frame/event payloads in memory and
    submit them in bulk (every ~1 second), reducing HTTP overhead by ~98%.
    
    If the network is unavailable or the API fails, payloads are safely queued
    in the local SQLite cache and automatically retried during subsequent sessions.
    """

    # ── Batch Coalescing Buffers ──────────────────────────────────────────────
    _event_buffer: List[Dict[str, Any]] = []
    _frame_buffer: List[Dict[str, Any]] = []
    _buffer_lock = threading.Lock()
    _last_flush_time: float = 0.0
    _FLUSH_INTERVAL_SEC: float = 2.0     # flush batches every 2 seconds
    _EVENT_BATCH_MAX: int = 30           # or when 30 events accumulate
    _FRAME_BATCH_MAX: int = 60           # or when 60 frames accumulate

    @classmethod
    def submit_session(cls, session_data: Dict[str, Any]) -> None:
        """Submit play session summary to the server via thread pool."""
        # Sessions are always sent immediately (rare, end-of-game event)
        _executor.submit(cls._post_telemetry, "/telemetry/session", session_data)

    @classmethod
    def submit_events(cls, events: List[Dict[str, Any]]) -> None:
        """Accumulate events into a batch buffer for coalesced submission."""
        if not events:
            return
        with cls._buffer_lock:
            cls._event_buffer.extend(events)
            if len(cls._event_buffer) >= cls._EVENT_BATCH_MAX:
                batch = cls._event_buffer[:]
                cls._event_buffer.clear()
                _executor.submit(cls._post_telemetry, "/telemetry/events", batch)
                return
        cls._maybe_flush()

    @classmethod
    def submit_frames(cls, frames: List[Dict[str, Any]]) -> None:
        """Accumulate frame samples into a batch buffer for coalesced submission."""
        if not frames:
            return
        with cls._buffer_lock:
            cls._frame_buffer.extend(frames)
            if len(cls._frame_buffer) >= cls._FRAME_BATCH_MAX:
                batch = cls._frame_buffer[:]
                cls._frame_buffer.clear()
                _executor.submit(cls._post_telemetry, "/telemetry/frames", batch)
                return
        cls._maybe_flush()

    @classmethod
    def _maybe_flush(cls) -> None:
        """Flush all accumulated buffers if the time interval has elapsed."""
        now = time.monotonic()
        if now - cls._last_flush_time < cls._FLUSH_INTERVAL_SEC:
            return
        cls._last_flush_time = now
        with cls._buffer_lock:
            if cls._event_buffer:
                batch = cls._event_buffer[:]
                cls._event_buffer.clear()
                _executor.submit(cls._post_telemetry, "/telemetry/events", batch)
            if cls._frame_buffer:
                batch = cls._frame_buffer[:]
                cls._frame_buffer.clear()
                _executor.submit(cls._post_telemetry, "/telemetry/frames", batch)

    @classmethod
    def retry_pending_telemetry(cls) -> None:
        """Scan local SQLite cache for unsent telemetry and attempt resubmission."""
        _executor.submit(cls._run_retry_loop)

    @classmethod
    def _post_telemetry(cls, endpoint: str, data: Any) -> bool:
        """Perform synchronous HTTP POST request. Returns True if successful, False otherwise."""
        url = f"{API_BASE_URL.rstrip('/')}{endpoint}"
        payload = json.dumps(data).encode("utf-8")
        
        try:
            req = urllib.request.Request(
                url,
                data=payload,
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": "Pixel-Runner Game Client"
                },
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=5.0) as response:
                if response.status in (200, 201):
                    return True
        except urllib.error.URLError as e:
            if os.environ.get("DEBUG_TELEMETRY_HTTP") == "1":
                print(f"[TELEMETRY CLIENT ERROR] Connection failed for {endpoint}: {e}")
        except Exception as e:
            if os.environ.get("DEBUG_TELEMETRY_HTTP") == "1":
                print(f"[TELEMETRY CLIENT ERROR] Unexpected failure for {endpoint}: {e}")

        # If we reach here, submission failed. Queue payload in SQLite cache for later.
        if os.environ.get("DEBUG_TELEMETRY_HTTP") == "1":
            print(f"[TELEMETRY CLIENT] Queued failed telemetry for {endpoint} to local SQLite cache.")
        LocalCache.queue_telemetry(endpoint, data)
        return False

    @classmethod
    def _run_retry_loop(cls) -> None:
        """Worker thread to retry queued telemetry payloads one by one."""
        pending = LocalCache.get_pending_telemetry()
        if not pending:
            return
            
        if os.environ.get("DEBUG_TELEMETRY_HTTP") == "1":
            print(f"[TELEMETRY CLIENT] Found {len(pending)} pending telemetry items in cache. Retrying...")
        
        for queue_id, endpoint, payload in pending:
            url = f"{API_BASE_URL.rstrip('/')}{endpoint}"
            post_data = json.dumps(payload).encode("utf-8")
            
            try:
                req = urllib.request.Request(
                    url,
                    data=post_data,
                    headers={
                        "Content-Type": "application/json",
                        "User-Agent": "Pixel-Runner Game Client"
                    },
                    method="POST"
                )
                with urllib.request.urlopen(req, timeout=5.0) as response:
                    if response.status in (200, 201):
                        LocalCache.delete_queued_telemetry(queue_id)
                        if os.environ.get("DEBUG_TELEMETRY_HTTP") == "1":
                            print(f"[TELEMETRY CLIENT] Successfully sent pending item ID {queue_id} to {endpoint}")
            except Exception as e:
                # Stop retrying if the network is still down or server errors out
                if os.environ.get("DEBUG_TELEMETRY_HTTP") == "1":
                    print(f"[TELEMETRY CLIENT] Failed to resend queued item ID {queue_id} to {endpoint}: {e}. Retries paused.")
                break
