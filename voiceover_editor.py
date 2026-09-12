#!/usr/bin/env python3
"""
Voiceover Editor — Web-based tool for managing Chatterbox TTS voice generation.

Features:
  - Dashboard with environment health checks and generation status
  - Voice profiles panel for per-NPC voice tuning
  - Voice lines table with status (Generated / Missing / Stale)
  - Generation console with real-time progress bar and ETA
  - Audio preview with in-browser playback
  - API endpoints for manifest CRUD, generation, progress streaming

Run:  python voiceover_editor.py
"""

import http.server
import socketserver
import json
import urllib.parse
import os
import sys
import webbrowser
import threading
import time
import subprocess
from threading import Timer

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(BASE_DIR, ".."))
sys.path.insert(0, BASE_DIR)

MANIFEST_PATH = os.path.join(BASE_DIR, "tools", "voice_manifest.json")

# ── Generation state (shared across threads) ────────────────────────────────
_generation_lock = threading.Lock()
_generation_active = False
_generation_log: list = []
_generation_progress: dict = {}
_generation_cancel = threading.Event()


def load_manifest():
    if not os.path.exists(MANIFEST_PATH):
        return {"voices": {}, "lines": [], "output_dir": "assets/audio/voiceovers"}
    with open(MANIFEST_PATH, "r") as f:
        return json.load(f)


def save_manifest(manifest):
    os.makedirs(os.path.dirname(MANIFEST_PATH), exist_ok=True)
    with open(MANIFEST_PATH, "w") as f:
        json.dump(manifest, f, indent=2)


def get_env_status():
    """Check Chatterbox environment health."""
    venv_path = os.path.join(BASE_DIR, "tools", "chatterbox-venv")
    venv_exists = os.path.exists(venv_path)
    python_bin = os.path.join(venv_path, "bin", "python")
    python_exists = os.path.exists(python_bin)
    chatterbox_ok = False

    if python_exists:
        try:
            result = subprocess.run(
                [python_bin, "-c", "from chatterbox.tts import ChatterboxTTS; print('ok')"],
                capture_output=True, text=True, timeout=30,
            )
            chatterbox_ok = result.returncode == 0 and "ok" in result.stdout
        except Exception:
            pass

    return {
        "venv_exists": venv_exists,
        "python_exists": python_exists,
        "chatterbox_installed": chatterbox_ok,
        "venv_path": venv_path,
        "setup_script": os.path.join(BASE_DIR, "tools", "setup_chatterbox.sh"),
    }


def get_line_status(manifest, line):
    """Return status of a voice line."""
    import hashlib
    output_dir = manifest.get("output_dir", "assets/audio/voiceovers")
    wav_path = os.path.join(BASE_DIR, output_dir, line["output_file"])
    if not os.path.exists(wav_path):
        return "missing", 0
    current_hash = hashlib.sha256(line["text"].encode("utf-8")).hexdigest()[:16]
    stored_hash = line.get("text_hash")
    file_size = os.path.getsize(wav_path)
    if stored_hash and stored_hash == current_hash:
        return "generated", file_size
    return "stale", file_size


def run_generation_thread(line_ids):
    """Run voice generation in a background thread."""
    global _generation_active, _generation_log, _generation_progress
    _generation_cancel.clear()

    try:
        sys.path.insert(0, BASE_DIR)
        from tools.chatterbox_backend import run_generation

        def on_progress(msg):
            global _generation_progress
            with _generation_lock:
                _generation_progress = msg
                _generation_log.append(msg)

        result = run_generation(MANIFEST_PATH, line_ids, on_progress)
        with _generation_lock:
            _generation_progress = {"phase": "complete", "result": result}
            _generation_log.append(_generation_progress)
    except Exception as e:
        with _generation_lock:
            _generation_progress = {"phase": "error", "message": str(e)}
            _generation_log.append(_generation_progress)
    finally:
        with _generation_lock:
            _generation_active = False


# ── HTML Content ─────────────────────────────────────────────────────────────

HTML_CONTENT = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Pixel Runner — Voiceover Studio</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&family=Space+Grotesk:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-color: #0b0f19;
            --panel-bg: rgba(17, 24, 39, 0.75);
            --border-color: rgba(255, 255, 255, 0.08);
            --border-hover: rgba(255, 255, 255, 0.16);
            --text-primary: #f8fafc;
            --text-secondary: #94a3b8;
            --accent-amber: #f59e0b;
            --accent-amber-glow: rgba(245, 158, 11, 0.3);
            --accent-purple: #8b5cf6;
            --accent-purple-glow: rgba(139, 92, 246, 0.3);
            --accent-green: #10b981;
            --accent-green-glow: rgba(16, 185, 129, 0.3);
            --accent-red: #ef4444;
            --accent-red-glow: rgba(239, 68, 68, 0.3);
            --accent-cyan: #06b6d4;
        }

        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Outfit', sans-serif; scrollbar-width: thin; scrollbar-color: rgba(255,255,255,0.2) transparent; }
        body { background-color: var(--bg-color); background-image: radial-gradient(at 0% 0%, rgba(245,158,11,0.06) 0px, transparent 50%), radial-gradient(at 100% 100%, rgba(139,92,246,0.06) 0px, transparent 50%); color: var(--text-primary); min-height: 100vh; display: flex; flex-direction: column; overflow-x: hidden; }

        header { background: rgba(15,23,42,0.8); backdrop-filter: blur(12px); border-bottom: 1px solid var(--border-color); padding: 1rem 2rem; display: flex; justify-content: space-between; align-items: center; position: sticky; top: 0; z-index: 100; }
        .header-title h1 { font-family: 'Space Grotesk', sans-serif; font-size: 1.5rem; font-weight: 700; letter-spacing: -0.025em; background: linear-gradient(to right, #f59e0b, #ef4444); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        .header-title p { font-size: 0.85rem; color: var(--text-secondary); margin-top: 2px; }
        .header-actions { display: flex; gap: 0.75rem; align-items: center; }

        .status-pill { display: inline-flex; align-items: center; gap: 6px; padding: 4px 12px; border-radius: 20px; font-size: 0.78rem; font-weight: 500; }
        .status-pill.green { background: rgba(16,185,129,0.15); color: #34d399; border: 1px solid rgba(16,185,129,0.3); }
        .status-pill.red { background: rgba(239,68,68,0.15); color: #f87171; border: 1px solid rgba(239,68,68,0.3); }
        .status-pill.amber { background: rgba(245,158,11,0.15); color: #fbbf24; border: 1px solid rgba(245,158,11,0.3); }
        .status-pill .dot { width: 7px; height: 7px; border-radius: 50%; }
        .status-pill.green .dot { background: #34d399; }
        .status-pill.red .dot { background: #f87171; }
        .status-pill.amber .dot { background: #fbbf24; }

        main { padding: 1.5rem 2rem; flex: 1; display: flex; flex-direction: column; gap: 1.5rem; }

        .panel { background: var(--panel-bg); border: 1px solid var(--border-color); border-radius: 12px; padding: 1.25rem; backdrop-filter: blur(8px); }
        .panel-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem; }
        .panel-header h2 { font-family: 'Space Grotesk', sans-serif; font-size: 1.1rem; font-weight: 600; }
        .panel-header .badge { font-size: 0.75rem; background: rgba(139,92,246,0.2); color: #a78bfa; padding: 3px 10px; border-radius: 12px; }

        .stats-row { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 1rem; margin-bottom: 1rem; }
        .stat-card { background: rgba(30,41,59,0.6); border: 1px solid var(--border-color); border-radius: 10px; padding: 1rem; text-align: center; }
        .stat-card .value { font-family: 'Space Grotesk', sans-serif; font-size: 2rem; font-weight: 700; }
        .stat-card .label { font-size: 0.8rem; color: var(--text-secondary); margin-top: 4px; }
        .stat-card.green .value { color: #34d399; }
        .stat-card.amber .value { color: #fbbf24; }
        .stat-card.red .value { color: #f87171; }
        .stat-card.purple .value { color: #a78bfa; }

        .btn { display: inline-flex; align-items: center; gap: 6px; padding: 8px 16px; border-radius: 8px; border: none; font-size: 0.85rem; font-weight: 500; cursor: pointer; transition: all 0.2s; font-family: 'Outfit', sans-serif; }
        .btn:hover { transform: translateY(-1px); }
        .btn-primary { background: linear-gradient(135deg, #f59e0b, #ef4444); color: white; box-shadow: 0 4px 15px rgba(245,158,11,0.25); }
        .btn-primary:hover { box-shadow: 0 6px 20px rgba(245,158,11,0.4); }
        .btn-primary:disabled { opacity: 0.5; cursor: not-allowed; transform: none; }
        .btn-secondary { background: rgba(255,255,255,0.06); color: var(--text-primary); border: 1px solid var(--border-color); }
        .btn-secondary:hover { background: rgba(255,255,255,0.1); border-color: var(--border-hover); }
        .btn-danger { background: rgba(239,68,68,0.15); color: #f87171; border: 1px solid rgba(239,68,68,0.3); }
        .btn-danger:hover { background: rgba(239,68,68,0.25); }
        .btn-sm { padding: 5px 10px; font-size: 0.78rem; }

        /* Voice Lines Table */
        .lines-table { width: 100%; border-collapse: collapse; }
        .lines-table th { text-align: left; font-size: 0.78rem; color: var(--text-secondary); font-weight: 500; padding: 8px 12px; border-bottom: 1px solid var(--border-color); text-transform: uppercase; letter-spacing: 0.05em; }
        .lines-table td { padding: 10px 12px; border-bottom: 1px solid rgba(255,255,255,0.04); font-size: 0.88rem; vertical-align: middle; }
        .lines-table tr:hover td { background: rgba(255,255,255,0.02); }
        .lines-table .text-col { max-width: 400px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: var(--text-secondary); }
        .lines-table .voice-col { color: #a78bfa; font-weight: 500; }
        .lines-table .status-generated { color: #34d399; }
        .lines-table .status-missing { color: #f87171; }
        .lines-table .status-stale { color: #fbbf24; }
        .lines-table .actions { display: flex; gap: 4px; }

        /* Progress Console */
        .console { background: rgba(0,0,0,0.4); border: 1px solid var(--border-color); border-radius: 8px; padding: 1rem; font-family: 'Space Grotesk', monospace; font-size: 0.82rem; max-height: 300px; overflow-y: auto; }
        .console .log-entry { padding: 3px 0; color: var(--text-secondary); }
        .console .log-entry.success { color: #34d399; }
        .console .log-entry.error { color: #f87171; }
        .console .log-entry.info { color: #60a5fa; }
        .console .log-entry.generating { color: #fbbf24; }

        .progress-bar-container { background: rgba(255,255,255,0.06); border-radius: 8px; height: 24px; overflow: hidden; position: relative; margin: 1rem 0; }
        .progress-bar-fill { height: 100%; background: linear-gradient(90deg, #f59e0b, #ef4444); border-radius: 8px; transition: width 0.5s ease; min-width: 0%; }
        .progress-bar-text { position: absolute; top: 0; left: 0; right: 0; bottom: 0; display: flex; align-items: center; justify-content: center; font-size: 0.78rem; font-weight: 600; color: white; text-shadow: 0 1px 3px rgba(0,0,0,0.5); }

        /* Voice Profiles Grid */
        .profiles-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 1rem; }
        .profile-card { background: rgba(30,41,59,0.5); border: 1px solid var(--border-color); border-radius: 10px; padding: 1rem; transition: border-color 0.2s; }
        .profile-card:hover { border-color: var(--border-hover); }
        .profile-card .name { font-weight: 600; font-size: 0.95rem; color: #fbbf24; margin-bottom: 4px; }
        .profile-card .desc { font-size: 0.82rem; color: var(--text-secondary); margin-bottom: 10px; }
        .profile-card label { display: block; font-size: 0.75rem; color: var(--text-secondary); margin-top: 8px; margin-bottom: 3px; text-transform: uppercase; letter-spacing: 0.05em; }
        .profile-card input[type="range"] { width: 100%; accent-color: #f59e0b; }
        .profile-card .slider-val { font-size: 0.78rem; color: #fbbf24; font-weight: 600; float: right; }

        /* Audio player */
        .audio-preview { display: flex; align-items: center; gap: 8px; }
        .audio-preview audio { height: 32px; flex: 1; }
        .play-btn { width: 32px; height: 32px; border-radius: 50%; background: rgba(245,158,11,0.2); border: 1px solid rgba(245,158,11,0.4); color: #fbbf24; cursor: pointer; display: flex; align-items: center; justify-content: center; font-size: 14px; transition: all 0.2s; }
        .play-btn:hover { background: rgba(245,158,11,0.35); transform: scale(1.1); }

        @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.5; } }
        .generating-indicator { animation: pulse 1.5s ease-in-out infinite; color: #fbbf24; }
    </style>
</head>
<body>
    <header>
        <div class="header-title">
            <h1>🎙️ Voiceover Studio</h1>
            <p>Chatterbox TTS — Voice Generation & Management</p>
        </div>
        <div class="header-actions">
            <span id="envStatus" class="status-pill red"><span class="dot"></span>Checking...</span>
            <button class="btn btn-secondary" onclick="refreshAll()">↻ Refresh</button>
        </div>
    </header>

    <main>
        <!-- Stats Overview -->
        <div class="stats-row">
            <div class="stat-card green"><div class="value" id="statGenerated">-</div><div class="label">Generated</div></div>
            <div class="stat-card amber"><div class="value" id="statStale">-</div><div class="label">Stale</div></div>
            <div class="stat-card red"><div class="value" id="statMissing">-</div><div class="label">Missing</div></div>
            <div class="stat-card purple"><div class="value" id="statTotal">-</div><div class="label">Total Lines</div></div>
        </div>

        <!-- Generation Console -->
        <div class="panel">
            <div class="panel-header">
                <h2>🔥 Generation Console</h2>
                <div style="display:flex;gap:8px;">
                    <button class="btn btn-primary" id="btnGenerateAll" onclick="generateAll()">⚡ Generate All</button>
                    <button class="btn btn-danger" id="btnCancel" onclick="cancelGeneration()" style="display:none;">✕ Cancel</button>
                </div>
            </div>
            <div class="progress-bar-container" id="progressContainer" style="display:none;">
                <div class="progress-bar-fill" id="progressFill" style="width:0%"></div>
                <div class="progress-bar-text" id="progressText">0%</div>
            </div>
            <div class="console" id="console">
                <div class="log-entry info">Ready. Click "Generate All" to synthesize voice lines.</div>
            </div>
        </div>

        <!-- Voice Lines Table -->
        <div class="panel">
            <div class="panel-header">
                <h2>📋 Voice Lines</h2>
                <span class="badge" id="lineCount">0 lines</span>
            </div>
            <table class="lines-table">
                <thead>
                    <tr>
                        <th>Line ID</th>
                        <th>Voice</th>
                        <th>Text</th>
                        <th>Status</th>
                        <th>Size</th>
                        <th>Preview</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody id="linesBody"></tbody>
            </table>
        </div>

        <!-- Voice Profiles -->
        <div class="panel">
            <div class="panel-header">
                <h2>🎭 Voice Profiles</h2>
                <button class="btn btn-secondary btn-sm" onclick="saveProfiles()">💾 Save Profiles</button>
            </div>
            <div class="profiles-grid" id="profilesGrid"></div>
        </div>
    </main>

    <script>
        let manifest = null;
        let lineStatuses = {};
        let pollingInterval = null;

        async function fetchJSON(url, opts = {}) {
            const resp = await fetch(url, opts);
            return resp.json();
        }

        async function refreshAll() {
            await loadEnvStatus();
            await loadManifest();
            await loadLineStatuses();
        }

        // ── Environment Status ──────────────────────────────────────────
        async function loadEnvStatus() {
            try {
                const data = await fetchJSON('/api/env-status');
                const el = document.getElementById('envStatus');
                if (data.chatterbox_installed) {
                    el.className = 'status-pill green';
                    el.innerHTML = '<span class="dot"></span>Chatterbox Ready';
                } else if (data.venv_exists) {
                    el.className = 'status-pill amber';
                    el.innerHTML = '<span class="dot"></span>Venv exists, Chatterbox not installed';
                } else {
                    el.className = 'status-pill red';
                    el.innerHTML = '<span class="dot"></span>Environment not set up';
                }
            } catch(e) {
                document.getElementById('envStatus').className = 'status-pill red';
                document.getElementById('envStatus').innerHTML = '<span class="dot"></span>Error';
            }
        }

        // ── Manifest & Lines ────────────────────────────────────────────
        async function loadManifest() {
            manifest = await fetchJSON('/api/manifest');
            renderProfiles();
        }

        async function loadLineStatuses() {
            const data = await fetchJSON('/api/line-status');
            lineStatuses = data;

            document.getElementById('statGenerated').textContent = data.generated || 0;
            document.getElementById('statStale').textContent = data.stale || 0;
            document.getElementById('statMissing').textContent = data.missing || 0;
            document.getElementById('statTotal').textContent = data.total || 0;
            document.getElementById('lineCount').textContent = `${data.total || 0} lines`;

            renderLines(data.lines || []);
        }

        function renderLines(lines) {
            const tbody = document.getElementById('linesBody');
            tbody.innerHTML = '';
            lines.forEach(line => {
                const statusClass = line.status === 'generated' ? 'status-generated' : line.status === 'stale' ? 'status-stale' : 'status-missing';
                const statusIcon = line.status === 'generated' ? '✅' : line.status === 'stale' ? '⚠️' : '❌';
                const sizeStr = line.file_size > 0 ? `${(line.file_size / 1024).toFixed(1)} KB` : '—';
                const previewHtml = line.status !== 'missing'
                    ? `<button class="play-btn" onclick="playPreview('${line.id}', '${line.output_file}')">▶</button>`
                    : '<span style="color:var(--text-secondary)">—</span>';

                const row = document.createElement('tr');
                row.innerHTML = `
                    <td><code style="color:#fbbf24;font-size:0.82rem;">${line.id}</code></td>
                    <td class="voice-col">${line.voice}</td>
                    <td class="text-col" title="${line.text}">${line.text}</td>
                    <td class="${statusClass}">${statusIcon} ${line.status}</td>
                    <td style="color:var(--text-secondary);font-size:0.82rem;">${sizeStr}</td>
                    <td>${previewHtml}</td>
                    <td class="actions">
                        <button class="btn btn-secondary btn-sm" onclick="generateLine('${line.id}')">🎙️</button>
                    </td>
                `;
                tbody.appendChild(row);
            });
        }

        // ── Audio Preview ───────────────────────────────────────────────
        let currentAudio = null;
        function playPreview(lineId, outputFile) {
            if (currentAudio) { currentAudio.pause(); currentAudio = null; }
            const url = `/assets/audio/voiceovers/${outputFile}`;
            currentAudio = new Audio(url);
            currentAudio.play().catch(e => console.warn('Playback error:', e));
        }

        // ── Voice Profiles ──────────────────────────────────────────────
        function renderProfiles() {
            if (!manifest) return;
            const grid = document.getElementById('profilesGrid');
            grid.innerHTML = '';
            const voices = manifest.voices || {};
            for (const [key, voice] of Object.entries(voices)) {
                const card = document.createElement('div');
                card.className = 'profile-card';
                card.innerHTML = `
                    <div class="name">${voice.display_name || key}</div>
                    <div class="desc">${voice.description || ''}</div>
                    <label>Exaggeration (Emotion) <span class="slider-val" id="exag-val-${key}">${voice.exaggeration || 0.5}</span></label>
                    <input type="range" min="0" max="1" step="0.05" value="${voice.exaggeration || 0.5}" id="exag-${key}" oninput="document.getElementById('exag-val-${key}').textContent=this.value">
                    <label>CFG Weight <span class="slider-val" id="cfg-val-${key}">${voice.cfg_weight || 0.5}</span></label>
                    <input type="range" min="0" max="1" step="0.05" value="${voice.cfg_weight || 0.5}" id="cfg-${key}" oninput="document.getElementById('cfg-val-${key}').textContent=this.value">
                `;
                grid.appendChild(card);
            }
        }

        async function saveProfiles() {
            if (!manifest) return;
            const voices = manifest.voices || {};
            for (const key of Object.keys(voices)) {
                const exagEl = document.getElementById(`exag-${key}`);
                const cfgEl = document.getElementById(`cfg-${key}`);
                if (exagEl) voices[key].exaggeration = parseFloat(exagEl.value);
                if (cfgEl) voices[key].cfg_weight = parseFloat(cfgEl.value);
            }
            manifest.voices = voices;
            await fetchJSON('/api/manifest', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(manifest)
            });
            addLog('💾 Voice profiles saved.', 'success');
        }

        // ── Generation ──────────────────────────────────────────────────
        async function generateAll() {
            await startGeneration(['__all__']);
        }

        async function generateLine(lineId) {
            await startGeneration([lineId]);
        }

        async function startGeneration(lineIds) {
            const btnGen = document.getElementById('btnGenerateAll');
            const btnCancel = document.getElementById('btnCancel');
            const progContainer = document.getElementById('progressContainer');

            btnGen.disabled = true;
            btnCancel.style.display = 'inline-flex';
            progContainer.style.display = 'block';
            updateProgress(0, 'Starting...');
            addLog('🚀 Starting voice generation...', 'info');

            try {
                await fetchJSON('/api/generate', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ line_ids: lineIds })
                });
                startPolling();
            } catch(e) {
                addLog(`❌ Failed to start: ${e.message}`, 'error');
                btnGen.disabled = false;
                btnCancel.style.display = 'none';
            }
        }

        async function cancelGeneration() {
            try {
                await fetchJSON('/api/generate/cancel', { method: 'POST' });
                addLog('⛔ Cancellation requested...', 'error');
            } catch(e) {}
        }

        function startPolling() {
            if (pollingInterval) clearInterval(pollingInterval);
            pollingInterval = setInterval(pollProgress, 1500);
        }

        async function pollProgress() {
            try {
                const data = await fetchJSON('/api/generate/status');
                if (!data.active && data.progress && data.progress.phase === 'complete') {
                    clearInterval(pollingInterval);
                    pollingInterval = null;
                    finishGeneration(data.progress.result || {});
                    return;
                }
                if (!data.active && data.progress && data.progress.phase === 'error') {
                    clearInterval(pollingInterval);
                    pollingInterval = null;
                    addLog(`❌ ${data.progress.message}`, 'error');
                    resetGenerationUI();
                    return;
                }
                if (data.progress) {
                    const p = data.progress;
                    if (p.phase === 'loading_model') {
                        addLog('⏳ Loading Chatterbox model (this may take a minute on first run)...', 'info');
                        updateProgress(5, 'Loading model...');
                    } else if (p.phase === 'generating') {
                        const pct = Math.round((p.current / p.total) * 100);
                        updateProgress(pct, `${p.current}/${p.total} — ${p.text_preview || ''}`);
                        addLog(`🎙️ [${p.current}/${p.total}] ${p.text_preview || p.line_id}`, 'generating');
                    } else if (p.phase === 'line_complete') {
                        addLog(`✅ ${p.line_id} — ${p.elapsed_seconds}s (${(p.file_size/1024).toFixed(1)} KB)`, 'success');
                    } else if (p.phase === 'line_error') {
                        addLog(`❌ ${p.line_id}: ${p.error}`, 'error');
                    }
                }
                // Process new log entries
                if (data.log_count > 0) {
                    // logs are processed via progress above
                }
            } catch(e) {}
        }

        function finishGeneration(result) {
            const gen = result.generated || 0;
            const errs = result.errors || 0;
            updateProgress(100, `Done! ${gen} generated, ${errs} errors`);
            addLog(`🎉 Generation complete: ${gen} lines generated, ${errs} errors.`, 'success');
            resetGenerationUI();
            loadLineStatuses();
        }

        function resetGenerationUI() {
            document.getElementById('btnGenerateAll').disabled = false;
            document.getElementById('btnCancel').style.display = 'none';
        }

        function updateProgress(pct, text) {
            document.getElementById('progressFill').style.width = `${pct}%`;
            document.getElementById('progressText').textContent = text;
        }

        function addLog(msg, type = '') {
            const console_el = document.getElementById('console');
            const entry = document.createElement('div');
            entry.className = `log-entry ${type}`;
            const ts = new Date().toLocaleTimeString();
            entry.textContent = `[${ts}] ${msg}`;
            console_el.appendChild(entry);
            console_el.scrollTop = console_el.scrollHeight;
        }

        // ── Init ────────────────────────────────────────────────────────
        refreshAll();
    </script>
</body>
</html>
"""


class VoiceoverEditorHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # Suppress HTTP logging

    def send_json(self, data, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path

        if path in ("/", "/index.html"):
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(HTML_CONTENT.encode("utf-8"))
            return

        elif path == "/api/env-status":
            self.send_json(get_env_status())
            return

        elif path == "/api/manifest":
            self.send_json(load_manifest())
            return

        elif path == "/api/line-status":
            try:
                manifest = load_manifest()
                lines_data = []
                generated = stale = missing = 0
                for line in manifest.get("lines", []):
                    status, file_size = get_line_status(manifest, line)
                    if status == "generated": generated += 1
                    elif status == "stale": stale += 1
                    else: missing += 1
                    lines_data.append({
                        "id": line["id"],
                        "voice": line.get("voice", ""),
                        "text": line.get("text", ""),
                        "output_file": line.get("output_file", ""),
                        "status": status,
                        "file_size": file_size,
                    })
                self.send_json({
                    "lines": lines_data,
                    "total": len(lines_data),
                    "generated": generated,
                    "stale": stale,
                    "missing": missing,
                })
            except Exception as e:
                self.send_json({"error": str(e)}, 500)
            return

        elif path == "/api/generate/status":
            with _generation_lock:
                self.send_json({
                    "active": _generation_active,
                    "progress": dict(_generation_progress),
                    "log_count": len(_generation_log),
                })
            return

        # Serve audio files for browser preview
        elif path.startswith("/assets/audio/"):
            clean_path = urllib.parse.unquote(path.lstrip("/"))
            full_path = os.path.join(BASE_DIR, clean_path)

            if not os.path.abspath(full_path).startswith(os.path.abspath(BASE_DIR)):
                self.send_error(403, "Access Denied")
                return

            if os.path.exists(full_path) and os.path.isfile(full_path):
                file_size = os.path.getsize(full_path)
                self.send_response(200)
                self.send_header("Accept-Ranges", "bytes")
                if full_path.endswith(".wav"):
                    self.send_header("Content-Type", "audio/wav")
                elif full_path.endswith(".mp3"):
                    self.send_header("Content-Type", "audio/mpeg")
                else:
                    self.send_header("Content-Type", "application/octet-stream")
                self.send_header("Content-Length", str(file_size))
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                try:
                    with open(full_path, "rb") as f:
                        while chunk := f.read(65536):
                            self.wfile.write(chunk)
                except (ConnectionResetError, BrokenPipeError, OSError):
                    pass
                return
            else:
                self.send_error(404, "File Not Found")
                return

        self.send_error(404, "Not Found")

    def do_POST(self):
        global _generation_active, _generation_log, _generation_progress
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path

        if path == "/api/manifest":
            try:
                content_length = int(self.headers['Content-Length'])
                post_data = self.rfile.read(content_length)
                manifest_data = json.loads(post_data.decode('utf-8'))
                save_manifest(manifest_data)
                self.send_json({"success": True})
            except Exception as e:
                self.send_json({"error": str(e)}, 500)
            return

        elif path == "/api/generate":
            try:
                content_length = int(self.headers['Content-Length'])
                post_data = self.rfile.read(content_length)
                payload = json.loads(post_data.decode('utf-8'))
                line_ids = payload.get("line_ids", ["__all__"])

                with _generation_lock:
                    if _generation_active:
                        self.send_json({"error": "Generation already in progress"}, 409)
                        return
                    _generation_active = True
                    _generation_log = []
                    _generation_progress = {"phase": "starting"}

                thread = threading.Thread(
                    target=run_generation_thread,
                    args=(line_ids,),
                    daemon=True,
                )
                thread.start()
                self.send_json({"success": True, "message": "Generation started"})
            except Exception as e:
                with _generation_lock:
                    _generation_active = False
                self.send_json({"error": str(e)}, 500)
            return

        elif path == "/api/generate/cancel":
            _generation_cancel.set()
            self.send_json({"success": True, "message": "Cancel requested"})
            return

        elif path == "/api/setup-env":
            try:
                setup_script = os.path.join(BASE_DIR, "tools", "setup_chatterbox.sh")
                if not os.path.exists(setup_script):
                    self.send_json({"error": "Setup script not found"}, 404)
                    return
                result = subprocess.run(
                    ["bash", setup_script],
                    capture_output=True, text=True, timeout=600,
                    cwd=BASE_DIR,
                )
                self.send_json({
                    "success": result.returncode == 0,
                    "stdout": result.stdout[-2000:],
                    "stderr": result.stderr[-1000:],
                })
            except Exception as e:
                self.send_json({"error": str(e)}, 500)
            return

        self.send_error(404, "Not Found")


def start_server():
    port = 8200
    while port < 8300:
        try:
            handler = VoiceoverEditorHandler
            with socketserver.TCPServer(("", port), handler) as httpd:
                print(f"\n╔══════════════════════════════════════════════════════════════╗")
                print(f"║  🎙️  Voiceover Studio — http://localhost:{port}                ║")
                print(f"╚══════════════════════════════════════════════════════════════╝\n")

                Timer(0.5, lambda: webbrowser.open(f"http://localhost:{port}")).start()

                try:
                    httpd.serve_forever()
                except KeyboardInterrupt:
                    print("\n[Voiceover Editor] Shutting down.")
                    sys.exit(0)
        except OSError:
            port += 1


if __name__ == "__main__":
    start_server()
