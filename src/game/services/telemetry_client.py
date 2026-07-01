import os
import json
import urllib.request
import urllib.error
import threading
from typing import Any, Dict, List

from .local_cache import LocalCache

# Default API URL. Can be overridden via environment variable.
API_BASE_URL = os.environ.get("PIXEL_RUNNER_API_URL", "https://pixel-runner-wheat.vercel.app")

class TelemetryClient:
    """Asynchronous telemetry client that submits gameplay tracking metrics, events,
    and frame samples to the cloud API in background threads.
    
    If the network is unavailable or the API fails, payloads are safely queued
    in the local SQLite cache and automatically retried during subsequent sessions.
    """

    @classmethod
    def submit_session(cls, session_data: Dict[str, Any]) -> None:
        """Submit play session summary to the server in a background thread."""
        threading.Thread(
            target=cls._post_telemetry,
            args=("/api/telemetry/session", session_data),
            daemon=True
        ).start()

    @classmethod
    def submit_events(cls, events: List[Dict[str, Any]]) -> None:
        """Submit a batch of events to the server in a background thread."""
        if not events:
            return
        threading.Thread(
            target=cls._post_telemetry,
            args=("/api/telemetry/events", events),
            daemon=True
        ).start()

    @classmethod
    def submit_frames(cls, frames: List[Dict[str, Any]]) -> None:
        """Submit a batch of frame samples to the server in a background thread."""
        if not frames:
            return
        threading.Thread(
            target=cls._post_telemetry,
            args=("/api/telemetry/frames", frames),
            daemon=True
        ).start()

    @classmethod
    def retry_pending_telemetry(cls) -> None:
        """Scan local SQLite cache for unsent telemetry and attempt resubmission."""
        threading.Thread(
            target=cls._run_retry_loop,
            daemon=True
        ).start()

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
            print(f"[TELEMETRY CLIENT ERROR] Connection failed for {endpoint}: {e}")
        except Exception as e:
            print(f"[TELEMETRY CLIENT ERROR] Unexpected failure for {endpoint}: {e}")

        # If we reach here, submission failed. Queue payload in SQLite cache for later.
        print(f"[TELEMETRY CLIENT] Queued failed telemetry for {endpoint} to local SQLite cache.")
        LocalCache.queue_telemetry(endpoint, data)
        return False

    @classmethod
    def _run_retry_loop(cls) -> None:
        """Worker thread to retry queued telemetry payloads one by one."""
        pending = LocalCache.get_pending_telemetry()
        if not pending:
            return
            
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
                        print(f"[TELEMETRY CLIENT] Successfully sent pending item ID {queue_id} to {endpoint}")
            except Exception as e:
                # Stop retrying if the network is still down or server errors out
                print(f"[TELEMETRY CLIENT] Failed to resend queued item ID {queue_id} to {endpoint}: {e}. Retries paused.")
                break
