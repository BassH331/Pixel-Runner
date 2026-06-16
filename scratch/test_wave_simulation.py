import subprocess
import sys
import os
import json

def test_wave_simulation():
    print("Starting Wave Simulation verification test...")
    # Run main.py with wave simulation parameters
    # Start distance 750, duration 3.0s
    cmd = [".venv/bin/python", "main.py", "--start-dist", "750", "--duration", "3.0"]
    if not os.path.exists(".venv/bin/python"):
        cmd[0] = sys.executable

    # We use SDL_VIDEODRIVER=dummy so we can run headlessly
    env = dict(os.environ, PYTHONPATH=".", SDL_VIDEODRIVER="dummy")
    
    result = subprocess.run(cmd, env=env, capture_output=True, text=True)
    print("Simulation Output:")
    print(result.stdout)
    print(result.stderr)
    
    # Check if simulation report was written
    report_json_path = "scratch/simulation_report.json"
    assert os.path.exists(report_json_path), "Simulation report JSON not found!"
    
    with open(report_json_path, "r") as f:
        report = json.load(f)
        
    print("Verification of Report Structure:")
    print(json.dumps(report, indent=2))
    
    assert report["type"] == "wave", f"Expected type 'wave', got {report.get('type')}"
    assert "enemies" in report, "Report should contain 'enemies' list"
    assert "status" in report, "Report should contain 'status'"
    
    print("\nWave simulation verification test PASSED successfully!")

if __name__ == "__main__":
    test_wave_simulation()
