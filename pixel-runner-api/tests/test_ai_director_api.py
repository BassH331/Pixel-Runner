"""
FastAPI AI Director Telemetry API Integration Test Suite.
Covers write authorization, Pydantic field validation, payload frame limits, fallback handling, and Kimi response parsing.
"""
import os
import sys
import pytest
from unittest.mock import patch, MagicMock

# Add pixel-runner-api root to sys.path so 'api.index' can be imported
sys.path.insert(0, os.path.abspath("pixel-runner-api"))

from fastapi.testclient import TestClient
from api.index import app
from api.services import kimi_service

client = TestClient(app)


def test_ai_director_unauthorized_when_secret_set():
    """Verify POST /telemetry/ai-director returns 401 when API_WRITE_SECRET is set but header is missing/invalid."""
    payload = {
        "session_id": "sess_ai_001",
        "current_phase": 1,
        "frames": [
            {
                "session_id": "sess_ai_001",
                "timestamp_ms": 1000,
                "frame_number": 1,
                "fps": 60.0,
                "world_distance": 50.0
            }
        ]
    }
    with patch.dict(os.environ, {"API_WRITE_SECRET": "test_secret_123"}):
        # 1. Missing header -> 401
        res_missing = client.post("/telemetry/ai-director", json=payload)
        assert res_missing.status_code == 401

        # 2. Invalid header -> 401
        res_invalid = client.post(
            "/telemetry/ai-director",
            json=payload,
            headers={"X-API-Write-Secret": "wrong_secret"}
        )
        assert res_invalid.status_code == 401


def test_ai_director_valid_fallback_response():
    """Verify POST /telemetry/ai-director returns 200 and fallback directive when MOONSHOT_API_KEY is unconfigured."""
    payload = {
        "session_id": "sess_ai_002",
        "boss_key": "gideon_boss",
        "current_phase": 1,
        "frames": [
            {
                "session_id": "sess_ai_002",
                "timestamp_ms": 1000,
                "frame_number": 1,
                "fps": 60.0,
                "world_distance": 40.0,
                "player": {"hp": 20, "is_dashing": True}
            }
        ]
    }
    with patch.dict(os.environ, {"API_WRITE_SECRET": "test_secret_123", "MOONSHOT_API_KEY": ""}, clear=True):
        res = client.post(
            "/telemetry/ai-director",
            json=payload,
            headers={"X-API-Write-Secret": "test_secret_123"}
        )
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "success"
        assert "directive" in data
        directive = data["directive"]
        assert directive["target_tactic"] in {"PINCER_FLANK", "BAIT_DASH", "PARRY_COUNTER", "RANGED_PRESSURE", "RETREAT_BUFF", "AGGRESSIVE_RUSH"}
        assert 0.5 <= directive["aggression_multiplier"] <= 2.0


def test_ai_director_frame_limit():
    """Verify POST /telemetry/ai-director returns 422 if frame count exceeds 60."""
    oversized_frames = [
        {
            "session_id": "sess_ai_003",
            "timestamp_ms": 1000 + i,
            "frame_number": i,
            "fps": 60.0,
            "world_distance": 100.0
        }
        for i in range(61)
    ]
    payload = {
        "session_id": "sess_ai_003",
        "current_phase": 1,
        "frames": oversized_frames
    }
    with patch.dict(os.environ, {"API_WRITE_SECRET": "test_secret_123"}):
        res = client.post(
            "/telemetry/ai-director",
            json=payload,
            headers={"X-API-Write-Secret": "test_secret_123"}
        )
        assert res.status_code == 422


def test_kimi_service_mocked_llm_parsing():
    """Verify kimi_service parses and sanitizes raw JSON output from mocked Kimi API."""
    mock_llm_json = '{"target_tactic": "BAIT_DASH", "aggression_multiplier": 1.8, "preferred_attack_sequence": ["CHARGE", "SLAM"], "movement_bias_x": -0.8, "contextual_taunt": "Hold still!"}'
    
    mock_resp = MagicMock()
    mock_resp.read.return_value = json_to_bytes({
        "choices": [{"message": {"content": mock_llm_json}}]
    })
    mock_resp.__enter__.return_value = mock_resp

    with patch.dict(os.environ, {"MOONSHOT_API_KEY": "sk-test-key"}), \
         patch("urllib.request.urlopen", return_value=mock_resp):
        res = kimi_service.evaluate_telemetry_directive({"frames": []})
        assert res["target_tactic"] == "BAIT_DASH"
        assert res["aggression_multiplier"] == 1.8
        assert res["preferred_attack_sequence"] == ["CHARGE", "SLAM"]
        assert res["movement_bias_x"] == -0.8
        assert res["contextual_taunt"] == "Hold still!"


def json_to_bytes(obj):
    import json
    return json.dumps(obj).encode("utf-8")
