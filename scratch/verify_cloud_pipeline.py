import sys
import os
import time

# Add src/ to python path so we can import services
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from game.services.config_client import ConfigClient
from game.services.telemetry_client import TelemetryClient

def main():
    print("=== STARTING CLOUD PIPELINE VERIFICATION ===")
    
    # 1. Verify Config Fetch from Vercel
    print("\n1. Fetching config 'player' from live Vercel API...")
    try:
        player_config = ConfigClient.fetch_config("player")
        if player_config and "states" in player_config:
            print("[SUCCESS] Successfully fetched player config from cloud!")
            idle_speed = player_config["states"]["IDLE"]["animation_speed"]
            print(f" -> Player IDLE animation speed: {idle_speed}")
        else:
            print("[ERROR] Config fetch returned invalid or empty data.")
    except Exception as e:
        print(f"[ERROR] Failed to fetch config: {e}")

    # 2. Verify Telemetry Submission to Vercel
    mock_session_id = f"test_session_{int(time.time())}"
    print(f"\n2. Submitting mock telemetry session: {mock_session_id}")
    
    mock_payload = {
        "session_id": mock_session_id,
        "started_at": "2026-07-01T16:50:00Z",
        "ended_at": "2026-07-01T16:51:00Z",
        "duration_seconds": 60.0,
        "total_frames": 3600,
        "average_fps": 60.0,
        "player_damage_taken": 10.5,
        "boss_damage_taken": 100.0,
        "player_hits_received": 2,
        "boss_hits_received": 5,
        "boss_attacks": 3,
        "successful_boss_attacks": 1,
        "boss_spell_casts": 2,
        "projectile_hits": 2,
        "projectile_misses": 1,
        "boss_defeated": True,
        "average_horizontal_distance": 120.0,
        "average_vertical_distance": 10.0,
        "average_player_boss_distance": 120.5,
        "player_defend_frames": 150,
        "player_standing_frames": 1200,
        "player_jumps": 4,
        "total_active_combat_frames": 300
    }
    
    try:
        TelemetryClient.submit_session(mock_payload)
        print("[INFO] Submission thread started. Waiting 3 seconds for background upload to Vercel...")
        time.sleep(3)
        print("[SUCCESS] Telemetry submission pipeline triggered.")
    except Exception as e:
        print(f"[ERROR] Telemetry submission failed: {e}")

    print("\n=== PIPELINE VERIFICATION COMPLETE ===")

if __name__ == "__main__":
    main()
