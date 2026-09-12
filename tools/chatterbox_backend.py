#!/usr/bin/env python3
"""
Chatterbox TTS Generation Backend

Handles voice line generation using Chatterbox Turbo in a Python 3.11 subprocess.
Called by voiceover_editor.py to generate .wav files from the voice manifest.

This module can be:
  1. Imported by voiceover_editor.py for subprocess invocation
  2. Run directly: python tools/chatterbox_backend.py --manifest tools/voice_manifest.json --line-id all
"""

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from typing import Any, Callable, Dict, List, Optional

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ── Manifest helpers ─────────────────────────────────────────────────────────

def load_manifest(manifest_path: str) -> Dict[str, Any]:
    """Load and return the voice manifest JSON."""
    with open(manifest_path, "r") as f:
        return json.load(f)


def save_manifest(manifest_path: str, manifest: Dict[str, Any]) -> None:
    """Save manifest back to disk."""
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)


def text_hash(text: str) -> str:
    """SHA256 hash of a dialogue line's text for staleness detection."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def get_line_status(manifest: Dict[str, Any], line: Dict[str, Any]) -> str:
    """
    Returns status of a voice line:
      'generated' — .wav exists and text hash matches
      'stale'     — .wav exists but text has changed
      'missing'   — .wav does not exist
    """
    output_dir = manifest.get("output_dir", "assets/audio/voiceovers")
    wav_path = os.path.join(BASE_DIR, output_dir, line["output_file"])
    if not os.path.exists(wav_path):
        return "missing"
    current_hash = text_hash(line["text"])
    stored_hash = line.get("text_hash")
    if stored_hash and stored_hash == current_hash:
        return "generated"
    return "stale"


def get_generation_status(manifest_path: str) -> Dict[str, Any]:
    """Return generation status overview for all lines."""
    manifest = load_manifest(manifest_path)
    output_dir = manifest.get("output_dir", "assets/audio/voiceovers")
    results = []
    for line in manifest.get("lines", []):
        wav_path = os.path.join(BASE_DIR, output_dir, line["output_file"])
        status = get_line_status(manifest, line)
        file_size = os.path.getsize(wav_path) if os.path.exists(wav_path) else 0
        results.append({
            "id": line["id"],
            "voice": line["voice"],
            "text": line["text"],
            "output_file": line["output_file"],
            "status": status,
            "file_size": file_size,
        })
    return {
        "lines": results,
        "total": len(results),
        "generated": sum(1 for r in results if r["status"] == "generated"),
        "stale": sum(1 for r in results if r["status"] == "stale"),
        "missing": sum(1 for r in results if r["status"] == "missing"),
    }


# ── Chatterbox venv detection ────────────────────────────────────────────────

def get_chatterbox_python() -> Optional[str]:
    """Return path to the Python binary inside the Chatterbox venv, or None."""
    venv_python = os.path.join(BASE_DIR, "tools", "chatterbox-venv", "bin", "python")
    if os.path.exists(venv_python):
        return venv_python
    return None


def is_chatterbox_installed() -> bool:
    """Check if Chatterbox is importable in the venv."""
    python_bin = get_chatterbox_python()
    if not python_bin:
        return False
    try:
        result = subprocess.run(
            [python_bin, "-c", "from chatterbox.tts import ChatterboxTTS; print('ok')"],
            capture_output=True, text=True, timeout=30,
        )
        return result.returncode == 0 and "ok" in result.stdout
    except Exception:
        return False


# ── Generation script (runs inside the Chatterbox venv) ─────────────────────

GENERATE_SCRIPT = '''
"""Chatterbox generation worker — runs inside Python 3.11 venv."""
import json
import os
import sys
import time

def generate_line(model, text, output_path, exaggeration=0.5, cfg_weight=0.5):
    """Generate a single voice line and save as WAV."""
    import torchaudio
    wav = model.generate(
        text,
        exaggeration=exaggeration,
        cfg_weight=cfg_weight,
    )
    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    torchaudio.save(output_path, wav, model.sr)
    return os.path.getsize(output_path)

def main():
    import torch
    from chatterbox.tts import ChatterboxTTS

    # Read generation request from stdin
    request = json.loads(sys.stdin.read())
    manifest_path = request["manifest_path"]
    line_ids = request["line_ids"]  # list of line IDs to generate, or ["__all__"]
    base_dir = request["base_dir"]

    with open(manifest_path, "r") as f:
        manifest = json.load(f)

    output_dir = os.path.join(base_dir, manifest.get("output_dir", "assets/audio/voiceovers"))
    voices = manifest.get("voices", {})
    lines = manifest.get("lines", [])

    # Filter lines to generate
    if "__all__" in line_ids:
        target_lines = lines
    else:
        target_lines = [l for l in lines if l["id"] in line_ids]

    if not target_lines:
        print(json.dumps({"status": "error", "message": "No lines to generate"}))
        sys.exit(1)

    # Load model (this takes a while on first run)
    progress = {"phase": "loading_model", "current": 0, "total": len(target_lines)}
    print(json.dumps(progress), flush=True)

    device = "cpu"
    model = ChatterboxTTS.from_pretrained(device=device)

    # Generate each line
    for i, line in enumerate(target_lines):
        voice_key = line.get("voice", "prologue_narrator")
        voice_cfg = voices.get(voice_key, {})
        exag = voice_cfg.get("exaggeration", 0.5)
        cfg_w = voice_cfg.get("cfg_weight", 0.5)

        output_path = os.path.join(output_dir, line["output_file"])
        clean_text = line["text"]

        progress = {
            "phase": "generating",
            "current": i + 1,
            "total": len(target_lines),
            "line_id": line["id"],
            "text_preview": clean_text[:80],
        }
        print(json.dumps(progress), flush=True)

        start_t = time.time()
        try:
            file_size = generate_line(model, clean_text, output_path, exag, cfg_w)
            elapsed = time.time() - start_t

            result = {
                "phase": "line_complete",
                "line_id": line["id"],
                "output_path": output_path,
                "file_size": file_size,
                "elapsed_seconds": round(elapsed, 1),
            }
            print(json.dumps(result), flush=True)
        except Exception as e:
            error = {
                "phase": "line_error",
                "line_id": line["id"],
                "error": str(e),
            }
            print(json.dumps(error), flush=True)

    # Done
    print(json.dumps({"phase": "complete", "total_generated": len(target_lines)}), flush=True)

if __name__ == "__main__":
    main()
'''


def run_generation(
    manifest_path: str,
    line_ids: List[str],
    progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
) -> Dict[str, Any]:
    """
    Launch Chatterbox generation in a subprocess using the Python 3.11 venv.

    Args:
        manifest_path: Path to voice_manifest.json
        line_ids: List of line IDs to generate, or ["__all__"] for all
        progress_callback: Optional callback receiving progress dicts

    Returns:
        Summary dict with results.
    """
    python_bin = get_chatterbox_python()
    if not python_bin:
        return {"error": "Chatterbox venv not found. Run tools/setup_chatterbox.sh first."}

    request_payload = json.dumps({
        "manifest_path": os.path.abspath(manifest_path),
        "line_ids": line_ids,
        "base_dir": BASE_DIR,
    })

    proc = subprocess.Popen(
        [python_bin, "-c", GENERATE_SCRIPT],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd=BASE_DIR,
    )

    proc.stdin.write(request_payload)  # type: ignore[union-attr]
    proc.stdin.close()  # type: ignore[union-attr]

    results: list[Dict[str, Any]] = []
    errors: list[Dict[str, Any]] = []

    for raw_line in (proc.stdout or []):
        raw_line = raw_line.strip()
        if not raw_line:
            continue
        try:
            msg = json.loads(raw_line)
            if progress_callback:
                progress_callback(msg)

            if msg.get("phase") == "line_complete":
                results.append(msg)
            elif msg.get("phase") == "line_error":
                errors.append(msg)
        except json.JSONDecodeError:
            pass  # Non-JSON output (e.g. model download logs)

    proc.wait()

    # Update text hashes in manifest for successfully generated lines
    if results:
        manifest = load_manifest(manifest_path)
        generated_ids = {r["line_id"] for r in results}
        for line in manifest.get("lines", []):
            if line["id"] in generated_ids:
                line["text_hash"] = text_hash(line["text"])
        save_manifest(manifest_path, manifest)

    return {
        "generated": len(results),
        "errors": len(errors),
        "results": results,
        "error_details": errors,
    }


# ── CLI interface ─────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Chatterbox TTS Voice Generation")
    parser.add_argument("--manifest", default="tools/voice_manifest.json", help="Path to voice manifest JSON")
    parser.add_argument("--line-id", default="__all__", help="Line ID to generate (or '__all__')")
    parser.add_argument("--status", action="store_true", help="Print generation status and exit")

    args = parser.parse_args()
    manifest_path = os.path.join(BASE_DIR, args.manifest)

    if args.status:
        status = get_generation_status(manifest_path)
        print(json.dumps(status, indent=2))
        return

    line_ids = [args.line_id] if args.line_id != "__all__" else ["__all__"]

    def on_progress(msg):
        phase = msg.get("phase", "")
        if phase == "loading_model":
            print(f"⏳ Loading Chatterbox model... ({msg['total']} lines queued)")
        elif phase == "generating":
            print(f"🎙️  [{msg['current']}/{msg['total']}] Generating: {msg['text_preview']}...")
        elif phase == "line_complete":
            print(f"✅ {msg['line_id']} — {msg['elapsed_seconds']}s ({msg['file_size']} bytes)")
        elif phase == "line_error":
            print(f"❌ {msg['line_id']} — Error: {msg['error']}")
        elif phase == "complete":
            print(f"\n🎉 Done! Generated {msg['total_generated']} voice lines.")

    result = run_generation(manifest_path, line_ids, on_progress)
    if result.get("error"):
        print(f"\n❌ {result['error']}")
        sys.exit(1)


if __name__ == "__main__":
    main()
