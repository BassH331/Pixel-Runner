import json
import pytest
from src.game.services.config_client import ConfigClient

def test_config_client_local_override(monkeypatch):
    # Mock API fetch to return a cloud configuration
    def mock_fetch_from_api(config_type):
        if config_type == "player":
            return {
                "states": {
                    "RUN": {
                        "animation_speed": 0.24,
                        "loops": True
                    },
                    "IDLE": {
                        "animation_speed": 0.2
                    }
                },
                "speed": 10.0
            }
        return {}

    # Mock local fallback to return local edits
    def mock_load_fallback(config_type):
        if config_type == "player":
            return {
                "states": {
                    "RUN": {
                        "animation_speed": 0.55  # Local edit (overrides 0.24)
                    }
                },
                "speed": 12.0  # Local edit (overrides 10.0)
            }
        return {}

    monkeypatch.setattr(ConfigClient, "_fetch_from_api", mock_fetch_from_api)
    monkeypatch.setattr(ConfigClient, "_load_fallback", mock_load_fallback)

    # Call fetch_config
    config = ConfigClient.fetch_config("player")

    # Assert deep merge logic:
    # 1. Local overrides should take precedence
    assert config["states"]["RUN"]["animation_speed"] == 0.55
    assert config["speed"] == 12.0

    # 2. Cloud-only keys should be preserved
    assert config["states"]["RUN"]["loops"] is True
    assert config["states"]["IDLE"]["animation_speed"] == 0.2
