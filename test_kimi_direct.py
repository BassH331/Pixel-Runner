import sys
import os
sys.path.append(os.path.abspath("pixel-runner-api"))
from api.services.kimi_service import evaluate_telemetry_directive
import json

payload = {
    "session_id": "test_session_123",
    "current_phase": 1,
    "frames": [
        {
            "session_id": "test_session_123",
            "timestamp_ms": 1000,
            "frame_number": 60,
            "fps": 60.0,
            "world_distance": 20.0,
            "player": {
                "state": "DEFEND",
                "is_defending": True,
                "hp": 100
            },
            "boss": {},
            "active_entities": 2
        }
    ]
}

try:
    print("Calling evaluate_telemetry_directive directly...")
    result = evaluate_telemetry_directive(payload)
    print("Result:")
    print(json.dumps(result, indent=2))
except Exception as e:
    print(f"Exception occurred: {e}")
