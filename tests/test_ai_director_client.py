"""
Client AI Director Integration Unit Test Suite.
Verifies asynchronous request dispatching, fallback retention, and settings toggling.
"""
import os
import sys
import time
import pytest
from unittest.mock import patch, MagicMock

from src.game.services.ai_director_client import AiDirectorClient


def test_ai_director_client_default_directive():
    """Verify get_active_directive returns valid default strategic directive dictionary."""
    directive = AiDirectorClient.get_active_directive()
    assert "target_tactic" in directive
    assert "aggression_multiplier" in directive
    assert "movement_bias_x" in directive


def test_ai_director_client_toggle_disabled():
    """Verify request_directive_async does not dispatch HTTP requests when feature is disabled."""
    mock_executor = MagicMock()
    with patch("src.game.services.ai_director_client._ai_executor", mock_executor), \
         patch.object(AiDirectorClient, "is_ai_director_enabled", return_value=False):
        
        AiDirectorClient.request_directive_async({"session_id": "test_sess", "frames": []})
        mock_executor.submit.assert_not_called()


def test_ai_director_client_async_dispatch():
    """Verify request_directive_async submits fetch task to thread pool worker."""
    mock_executor = MagicMock()
    with patch("src.game.services.ai_director_client._ai_executor", mock_executor), \
         patch.object(AiDirectorClient, "is_ai_director_enabled", return_value=True):
        
        # Reset last dispatch timestamp to ensure invocation
        AiDirectorClient._last_dispatch_time = 0.0
        AiDirectorClient.request_directive_async({"session_id": "test_sess", "frames": []})
        mock_executor.submit.assert_called_once()


def test_ai_director_client_fetch_success_updates_directive():
    """Verify _fetch_directive updates active directive upon receiving success response from backend API."""
    mock_resp = MagicMock()
    mock_resp.read.return_value = json_to_bytes({
        "status": "success",
        "directive": {
            "target_tactic": "PINCER_FLANK",
            "aggression_multiplier": 1.5,
            "preferred_attack_sequence": ["FIREBALL"],
            "movement_bias_x": 0.3,
            "contextual_taunt": "Dynamic taunt!"
        }
    })
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", return_value=mock_resp):
        AiDirectorClient._fetch_directive({"session_id": "sess_123", "frames": []})
        directive = AiDirectorClient.get_active_directive()
        assert directive["target_tactic"] == "PINCER_FLANK"
        assert directive["aggression_multiplier"] == 1.5
        assert directive["contextual_taunt"] == "Dynamic taunt!"


def json_to_bytes(obj):
    import json
    return json.dumps(obj).encode("utf-8")
