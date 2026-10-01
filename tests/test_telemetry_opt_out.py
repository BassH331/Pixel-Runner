"""
Unit test for SEC-04 telemetry opt-out logic.
"""
import os
import pytest
from unittest.mock import patch, MagicMock

from src.game.services.telemetry_client import TelemetryClient


def test_telemetry_is_disabled_when_env_var_set():
    """Verify TelemetryClient.is_telemetry_enabled() returns False when DISABLE_TELEMETRY=1."""
    with patch.dict(os.environ, {"DISABLE_TELEMETRY": "1"}):
        assert TelemetryClient.is_telemetry_enabled() is False


def test_telemetry_is_disabled_when_setting_false():
    """Verify TelemetryClient.is_telemetry_enabled() returns False when settingsManager returns False."""
    with patch("v3x_zulfiqar_gideon.SettingsManager.get", return_value=False):
        assert TelemetryClient.is_telemetry_enabled() is False


def test_telemetry_is_enabled_default():
    """Verify TelemetryClient.is_telemetry_enabled() returns True by default when not in pytest/opt-out."""
    with patch.dict(os.environ, {}, clear=True), \
         patch("v3x_zulfiqar_gideon.SettingsManager.get", return_value=True):
        assert TelemetryClient.is_telemetry_enabled() is True
