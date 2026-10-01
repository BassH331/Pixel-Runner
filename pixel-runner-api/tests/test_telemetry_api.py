"""
FastAPI Telemetry API Integration Test Suite (TEST-01).
Covers write authorization, Pydantic field bounds, payload array caps, and health endpoint.
"""
import os
import sys
import pytest
from unittest.mock import patch, MagicMock

# Add pixel-runner-api root to sys.path so 'api.index' can be imported
sys.path.insert(0, os.path.abspath("pixel-runner-api"))

from fastapi.testclient import TestClient
from api.index import app

client = TestClient(app)


def test_health_check_endpoint():
    """Verify GET /health returns 200 and connectivity status dict."""
    response = client.get("/health")
    assert response.status_code == 200
    json_data = response.json()
    assert "status" in json_data
    assert "database" in json_data
    assert "cache" in json_data


def test_telemetry_session_unauthorized_when_secret_set():
    """Verify POST /telemetry/session returns 401 when API_WRITE_SECRET is set but header is missing/invalid."""
    with patch.dict(os.environ, {"API_WRITE_SECRET": "test_secret_123"}):
        # 1. Missing header -> 401
        res_missing = client.post("/telemetry/session", json={
            "session_id": "test_sess_001",
            "boss_defeated": True
        })
        assert res_missing.status_code == 401

        # 2. Invalid header -> 401
        res_invalid = client.post(
            "/telemetry/session",
            json={"session_id": "test_sess_001", "boss_defeated": True},
            headers={"X-API-Write-Secret": "wrong_secret"}
        )
        assert res_invalid.status_code == 401


def test_telemetry_session_valid_insertion():
    """Verify POST /telemetry/session succeeds when write authorization matches."""
    with patch.dict(os.environ, {"API_WRITE_SECRET": "test_secret_123"}), \
         patch("api.services.database.insert_session", return_value={"id": "uuid-1", "session_id": "sess-123"}):
        res = client.post(
            "/telemetry/session",
            json={"session_id": "sess-123", "duration_seconds": 120.5, "boss_defeated": True},
            headers={"X-API-Write-Secret": "test_secret_123"}
        )
        assert res.status_code == 200
        assert res.json()["status"] == "success"


def test_telemetry_events_array_cap_limit():
    """Verify POST /telemetry/events returns 422 when event batch exceeds 50 items."""
    oversized_events = [
        {"session_id": f"sess_{i}", "timestamp_ms": 1000 + i, "event_type": "BOSS_HIT"}
        for i in range(51)
    ]
    with patch.dict(os.environ, {"API_WRITE_SECRET": "test_secret_123"}):
        res = client.post(
            "/telemetry/events",
            json=oversized_events,
            headers={"X-API-Write-Secret": "test_secret_123"}
        )
        assert res.status_code == 422
        assert "50 items" in res.json()["detail"]


def test_telemetry_frames_array_cap_limit():
    """Verify POST /telemetry/frames returns 422 when frame sample batch exceeds 100 items."""
    oversized_frames = [
        {"session_id": f"sess_{i}", "timestamp_ms": 1000 + i, "frame_number": i, "fps": 60.0, "world_distance": 100.0}
        for i in range(101)
    ]
    with patch.dict(os.environ, {"API_WRITE_SECRET": "test_secret_123"}):
        res = client.post(
            "/telemetry/frames",
            json=oversized_frames,
            headers={"X-API-Write-Secret": "test_secret_123"}
        )
        assert res.status_code == 422
        assert "100 items" in res.json()["detail"]


def test_telemetry_session_invalid_numeric_bounds():
    """Verify Pydantic validation rejects out-of-bounds numeric fields (e.g. negative FPS)."""
    with patch.dict(os.environ, {"API_WRITE_SECRET": "test_secret_123"}):
        res = client.post(
            "/telemetry/session",
            json={"session_id": "sess-123", "average_fps": -10.0},
            headers={"X-API-Write-Secret": "test_secret_123"}
        )
        assert res.status_code == 422
