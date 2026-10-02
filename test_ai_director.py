import os
import sys
import time

# Force local API
os.environ["PIXEL_RUNNER_API_URL"] = "http://127.0.0.1:8000"
os.environ["API_WRITE_SECRET"] = "dummy_secret"

# Start the local FastAPI server in a background thread
import threading
import uvicorn
from fastapi import FastAPI

# Add the API dir to path so we can import it
sys.path.append(os.path.abspath("pixel-runner-api"))
from api.index import app

def run_server():
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="error")

server_thread = threading.Thread(target=run_server, daemon=True)
server_thread.start()

# Wait for server to start
time.sleep(2)

# Now test the client
from src.game.services.ai_director_client import AiDirectorClient

print("Testing AiDirectorClient...")

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

# The client uses a background thread, so let's call the worker directly to get synchronous results
print(f"Old directive: {AiDirectorClient.get_active_directive()}")

AiDirectorClient._fetch_directive(payload)

new_directive = AiDirectorClient.get_active_directive()
print(f"New directive: {new_directive}")

import json
# Save to an artifact to show the user
with open("/home/chosen333/.gemini/antigravity-ide/brain/4d7a970c-57e1-4fad-b673-734fd5d7242b/ai_director_test_output.json", "w") as f:
    json.dump(new_directive, f, indent=2)

print("Test complete.")
