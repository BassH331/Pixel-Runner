#!/usr/bin/env python3
"""
Transformation Cutscene Visual Configuration Editor & Live Preview Studio.

A web-based GUI editor for tuning sounds, camera dynamics, timing, speeds,
particles, and assets with an interactive live canvas preview, visual labels,
HUD telemetry, and real-time event logs.
"""

import http.server
import json
import os
import re
import socketserver
import sys
import urllib.parse
import webbrowser
from threading import Timer

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

CONFIG_PATH = os.path.join(BASE_DIR, "game_data", "cutscene_config.json")
DEFAULT_CONFIG = {
    "phases": {
        "fade_in": {"duration": 1.5},
        "orb_collapse": {
            "frame_duration": 0.11,
            "camera_zoom": 1.45,
            "camera_zoom_speed": 1.2,
            "shake_amplitude": 3.5,
            "shake_frequency": 10.0,
            "gravity_strength": 8.0,
            "sfx": ["transform", "aura_effect"]
        },
        "orb_loop": {
            "frame_duration": 0.09,
            "loop_cycles": 3,
            "camera_zoom": 1.50,
            "camera_zoom_speed": 0.8,
            "shake_amplitude": 4.5,
            "shake_frequency": 14.0,
            "gravity_strength": 14.0,
            "sfx": ["lightning"]
        },
        "demon_burst": {
            "frame_duration": 0.035,
            "flash_color_white": [255, 255, 255],
            "flash_color_red": [180, 20, 20],
            "red_flash_trigger_frame": 3,
            "explosion_strength": 450.0,
            "shake_amplitude": 8.0,
            "shake_frequency": 20.0,
            "camera_zoom_snapback_speed": 6.0,
            "sfx": ["magic_sfx", "bells", "wendigo_screams"]
        },
        "attack_left": {
            "frame_duration": 0.055,
            "sway_x": -55.0,
            "sway_speed": 4.0,
            "sway_return_pct": 0.7,
            "sfx": ["smash_phase_2"]
        },
        "attack_right": {
            "frame_duration": 0.055,
            "sway_x": 55.0,
            "sway_speed": 4.0,
            "sway_return_pct": 0.7,
            "sfx": ["smash_phase_3"]
        },
        "special_tentacles": {
            "frame_duration": 0.075,
            "zoom_peak_frame": 11,
            "zoom_max": 1.50,
            "zoom_speed": 2.5,
            "peak_shake_amplitude": 2.5,
            "peak_shake_frequency": 8.0,
            "sfx": ["special_attack", "power_release_1"]
        },
        "revert": {
            "frame_duration": 0.07,
            "flash_count": 4,
            "flash_cycle_duration": 0.22,
            "flash_color": [200, 15, 15],
            "flash_peak_alpha": 180,
            "post_pause": 0.6,
            "sfx": []
        }
    },
    "global": {
        "sprite_scale": 3.5,
        "particle_count": 40,
        "crossfade_duration": 0.30,
        "flash_fade_speed": 0.30,
        "background_color": [12, 10, 20]
    },
    "assets": {
        "transform_dir": "assets/shadow_warrior/transform",
        "atk_left_dir": "assets/shadow_warrior/e_3_atk",
        "atk_right_dir": "assets/shadow_warrior/e_3_atk",
        "special_atk_dir": "assets/shadow_warrior/e_sp_atk",
        "revert_dir": "assets/shadow_warrior/back2human"
    }
}


def load_config() -> dict:
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"[Cutscene Editor] Error loading config: {e}")
    return dict(DEFAULT_CONFIG)


def save_config(cfg: dict) -> bool:
    try:
        os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
        with open(CONFIG_PATH, "w") as f:
            json.dump(cfg, f, indent=2)
        return True
    except Exception as e:
        print(f"[Cutscene Editor] Error saving config: {e}")
        return False


def get_available_sounds() -> dict:
    """Extract registered sounds from main.py manifest + master audio config."""
    sounds = {}
    main_path = os.path.join(BASE_DIR, "main.py")
    if os.path.exists(main_path):
        try:
            with open(main_path, "r") as f:
                content = f.read()
            match = re.search(r"audio\s*=\s*\{([^\}]+)\}", content)
            if match:
                entries = re.findall(r"[\"']([^\"']+)[\"']\s*:\s*[\"']([^\"']+)[\"']", match.group(1))
                for name, path in entries:
                    sounds[name] = path
        except Exception:
            pass

    master_path = os.path.join(BASE_DIR, "game_data", "master_audio_config.json")
    if os.path.exists(master_path):
        try:
            with open(master_path, "r") as f:
                data = json.load(f)
                if "sounds" in data:
                    for k, v in data["sounds"].items():
                        if k not in sounds:
                            sounds[k] = v
        except Exception:
            pass
    return sounds


def get_available_sprites() -> list[str]:
    """Scan shadow warrior sprite animation folders."""
    sprite_base = os.path.join(BASE_DIR, "assets", "shadow_warrior")
    if os.path.exists(sprite_base):
        dirs = [
            os.path.join("assets", "shadow_warrior", d)
            for d in sorted(os.listdir(sprite_base))
            if os.path.isdir(os.path.join(sprite_base, d))
        ]
        return dirs
    return []


def get_frames_in_dir(rel_dir: str) -> list[str]:
    """Return sorted image filenames for an animation folder."""
    p = os.path.join(BASE_DIR, rel_dir)
    if not os.path.exists(p) or not os.path.isdir(p):
        return []

    def sort_key(s: str) -> int:
        nums = re.findall(r'\d+', s)
        return int(nums[-1]) if nums else 0

    files = [f for f in sorted(os.listdir(p), key=sort_key) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))]
    return [os.path.join(rel_dir, f).replace("\\", "/") for f in files]


HTML_PAGE = r"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Transformation Scene State & VFX Studio</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-main: #0a0d14;
            --panel-bg: rgba(18, 24, 38, 0.78);
            --panel-border: rgba(255, 255, 255, 0.08);
            --panel-hover: rgba(255, 255, 255, 0.14);
            --text-main: #f1f5f9;
            --text-muted: #94a3b8;
            --accent-cyan: #06b6d4;
            --accent-cyan-glow: rgba(6, 182, 212, 0.25);
            --accent-purple: #8b5cf6;
            --accent-purple-glow: rgba(139, 92, 246, 0.25);
            --accent-pink: #ec4899;
            --accent-pink-glow: rgba(236, 72, 153, 0.35);
            --accent-amber: #f59e0b;
            --accent-red: #ef4444;
            --accent-green: #10b981;
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
            font-family: 'Outfit', sans-serif;
            -webkit-font-smoothing: antialiased;
        }

        body {
            background-color: var(--bg-main);
            color: var(--text-main);
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            overflow-x: hidden;
            background-image: 
                radial-gradient(circle at 15% 20%, rgba(139, 92, 246, 0.08) 0%, transparent 40%),
                radial-gradient(circle at 85% 75%, rgba(6, 182, 212, 0.08) 0%, transparent 45%);
        }

        /* Top Header */
        header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 0.85rem 2rem;
            background: rgba(15, 23, 42, 0.88);
            backdrop-filter: blur(12px);
            border-bottom: 1px solid var(--panel-border);
            position: sticky;
            top: 0;
            z-index: 100;
        }

        .brand {
            display: flex;
            align-items: center;
            gap: 0.75rem;
        }

        .brand-icon {
            width: 36px;
            height: 36px;
            border-radius: 8px;
            background: linear-gradient(135deg, var(--accent-purple), var(--accent-cyan));
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.2rem;
            box-shadow: 0 0 16px var(--accent-purple-glow);
        }

        .brand-title h1 {
            font-size: 1.15rem;
            font-weight: 700;
            letter-spacing: -0.02em;
        }

        .brand-title p {
            font-size: 0.75rem;
            color: var(--text-muted);
        }

        .header-actions {
            display: flex;
            align-items: center;
            gap: 0.75rem;
        }

        .btn {
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
            padding: 0.55rem 1.15rem;
            border-radius: 8px;
            font-size: 0.875rem;
            font-weight: 600;
            cursor: pointer;
            border: 1px solid transparent;
            transition: all 0.2s ease;
        }

        .btn-preview {
            background: linear-gradient(135deg, #ec4899, #8b5cf6);
            color: #fff;
            box-shadow: 0 0 18px var(--accent-pink-glow);
            border: 1px solid rgba(255, 255, 255, 0.2);
            animation: pulseGlow 2.5s infinite;
        }

        @keyframes pulseGlow {
            0%, 100% { box-shadow: 0 0 16px var(--accent-pink-glow); }
            50% { box-shadow: 0 0 28px rgba(236, 72, 153, 0.6); }
        }

        .btn-preview:hover {
            transform: translateY(-1px) scale(1.02);
            filter: brightness(1.15);
        }

        .btn-primary {
            background: linear-gradient(135deg, #06b6d4, #3b82f6);
            color: #fff;
            box-shadow: 0 0 16px var(--accent-cyan-glow);
        }

        .btn-primary:hover {
            transform: translateY(-1px);
            box-shadow: 0 0 24px rgba(6, 182, 212, 0.45);
        }

        .btn-secondary {
            background: rgba(255, 255, 255, 0.05);
            color: var(--text-main);
            border-color: var(--panel-border);
        }

        .btn-secondary:hover {
            background: rgba(255, 255, 255, 0.1);
            border-color: var(--panel-hover);
        }

        /* Timeline Bar */
        .timeline-container {
            padding: 0.85rem 2rem;
            background: rgba(10, 15, 26, 0.7);
            border-bottom: 1px solid var(--panel-border);
        }

        .timeline-header {
            display: flex;
            justify-content: space-between;
            font-size: 0.75rem;
            color: var(--text-muted);
            margin-bottom: 0.4rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }

        .timeline-bar {
            height: 38px;
            background: rgba(0, 0, 0, 0.45);
            border-radius: 8px;
            border: 1px solid var(--panel-border);
            display: flex;
            overflow: hidden;
            position: relative;
        }

        .timeline-segment {
            height: 100%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 0.72rem;
            font-weight: 600;
            color: #fff;
            position: relative;
            cursor: pointer;
            transition: opacity 0.2s, transform 0.2s;
            border-right: 1px solid rgba(0,0,0,0.3);
            text-overflow: ellipsis;
            white-space: nowrap;
            padding: 0 4px;
        }

        .timeline-segment:hover {
            opacity: 0.85;
            filter: brightness(1.2);
        }

        /* Main Container */
        .main-content {
            display: flex;
            flex: 1;
            padding: 1.5rem 2rem;
            gap: 1.5rem;
            max-width: 1600px;
            width: 100%;
            margin: 0 auto;
        }

        /* Tabs Sidebar */
        .tabs-sidebar {
            width: 220px;
            display: flex;
            flex-direction: column;
            gap: 0.4rem;
        }

        .tab-btn {
            display: flex;
            align-items: center;
            gap: 0.75rem;
            padding: 0.75rem 1rem;
            border-radius: 8px;
            background: transparent;
            color: var(--text-muted);
            border: 1px solid transparent;
            font-size: 0.875rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s ease;
            text-align: left;
        }

        .tab-btn:hover {
            background: rgba(255, 255, 255, 0.04);
            color: var(--text-main);
        }

        .tab-btn.active {
            background: var(--panel-bg);
            color: var(--accent-cyan);
            border-color: var(--accent-cyan);
            box-shadow: 0 0 16px var(--accent-cyan-glow);
        }

        .tab-btn.preview-tab-btn.active {
            color: var(--accent-pink);
            border-color: var(--accent-pink);
            box-shadow: 0 0 16px var(--accent-pink-glow);
        }

        /* Panels Container */
        .tab-panel {
            flex: 1;
            display: none;
            flex-direction: column;
            gap: 1.25rem;
        }

        .tab-panel.active {
            display: flex;
        }

        .card {
            background: var(--panel-bg);
            border: 1px solid var(--panel-border);
            border-radius: 12px;
            padding: 1.25rem;
            backdrop-filter: blur(16px);
            display: flex;
            flex-direction: column;
            gap: 1rem;
        }

        .card-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding-bottom: 0.75rem;
            border-bottom: 1px solid var(--panel-border);
        }

        .card-title {
            font-size: 1rem;
            font-weight: 700;
            color: var(--text-main);
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }

        .card-badge {
            font-size: 0.7rem;
            font-weight: 600;
            padding: 0.2rem 0.6rem;
            border-radius: 20px;
            background: rgba(6, 182, 212, 0.15);
            color: var(--accent-cyan);
        }

        .card-badge.pink {
            background: rgba(236, 72, 153, 0.15);
            color: var(--accent-pink);
        }

        /* Controls Grid */
        .grid-2 {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 1rem;
        }

        .control-group {
            display: flex;
            flex-direction: column;
            gap: 0.4rem;
        }

        .control-label {
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 0.82rem;
            font-weight: 500;
            color: var(--text-muted);
        }

        .control-val {
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.8rem;
            color: var(--accent-cyan);
            font-weight: 600;
        }

        input[type="range"] {
            -webkit-appearance: none;
            width: 100%;
            height: 6px;
            border-radius: 3px;
            background: rgba(255, 255, 255, 0.1);
            outline: none;
        }

        input[type="range"]::-webkit-slider-thumb {
            -webkit-appearance: none;
            width: 16px;
            height: 16px;
            border-radius: 50%;
            background: var(--accent-cyan);
            cursor: pointer;
            box-shadow: 0 0 10px var(--accent-cyan-glow);
            transition: transform 0.1s;
        }

        input[type="range"]::-webkit-slider-thumb:hover {
            transform: scale(1.2);
        }

        select, input[type="text"], input[type="number"] {
            background: rgba(0, 0, 0, 0.4);
            border: 1px solid var(--panel-border);
            color: var(--text-main);
            padding: 0.5rem 0.75rem;
            border-radius: 6px;
            font-size: 0.85rem;
            outline: none;
            transition: border-color 0.2s;
        }

        select:focus, input[type="text"]:focus, input[type="number"]:focus {
            border-color: var(--accent-cyan);
        }

        /* Sound Chips */
        .sfx-tag-container {
            display: flex;
            flex-wrap: wrap;
            gap: 0.5rem;
            margin-top: 0.4rem;
        }

        .sfx-chip {
            display: inline-flex;
            align-items: center;
            gap: 0.4rem;
            background: rgba(139, 92, 246, 0.15);
            border: 1px solid rgba(139, 92, 246, 0.3);
            color: #d8b4fe;
            padding: 0.25rem 0.6rem;
            border-radius: 6px;
            font-size: 0.78rem;
            font-weight: 500;
        }

        .sfx-play-btn {
            background: none;
            border: none;
            color: var(--accent-cyan);
            cursor: pointer;
            font-size: 0.8rem;
            display: flex;
            align-items: center;
        }

        .sfx-remove-btn {
            background: none;
            border: none;
            color: var(--accent-red);
            cursor: pointer;
            font-weight: bold;
            font-size: 0.8rem;
        }

        .sfx-add-row {
            display: flex;
            gap: 0.5rem;
            margin-top: 0.5rem;
        }

        /* Color Picker Row */
        .color-row {
            display: flex;
            align-items: center;
            gap: 0.75rem;
        }

        input[type="color"] {
            -webkit-appearance: none;
            border: 1px solid var(--panel-border);
            width: 38px;
            height: 38px;
            border-radius: 6px;
            cursor: pointer;
            background: none;
            padding: 0;
        }

        input[type="color"]::-webkit-color-swatch-wrapper {
            padding: 0;
        }

        input[type="color"]::-webkit-color-swatch {
            border: none;
            border-radius: 5px;
        }

        /* ─── LIVE PREVIEW STUDIO STYLING ─── */
        .preview-stage-container {
            position: relative;
            width: 100%;
            border-radius: 12px;
            overflow: hidden;
            background: #000;
            border: 1px solid rgba(255, 255, 255, 0.15);
            box-shadow: 0 12px 36px rgba(0, 0, 0, 0.6);
            display: flex;
            justify-content: center;
            align-items: center;
        }

        #previewCanvas {
            width: 100%;
            max-height: 480px;
            aspect-ratio: 16 / 9;
            display: block;
            background: #0c0a14;
        }

        /* Visual Labels & HUD Telemetry Overlays */
        .hud-overlay {
            position: absolute;
            inset: 0;
            pointer-events: none;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            padding: 1rem;
        }

        .hud-top {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            gap: 1rem;
        }

        .hud-badge {
            background: rgba(10, 15, 26, 0.82);
            border: 1px solid var(--panel-border);
            backdrop-filter: blur(8px);
            padding: 0.4rem 0.75rem;
            border-radius: 6px;
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.75rem;
            display: flex;
            flex-direction: column;
            gap: 0.2rem;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.4);
        }

        .hud-phase-pill {
            font-weight: 700;
            font-size: 0.85rem;
            letter-spacing: 0.04em;
        }

        .hud-bottom {
            display: flex;
            justify-content: space-between;
            align-items: flex-end;
            gap: 1rem;
        }

        /* Playback Controller Bar */
        .playback-controls {
            display: flex;
            flex-wrap: wrap;
            align-items: center;
            justify-content: space-between;
            gap: 1rem;
            background: rgba(15, 23, 42, 0.75);
            padding: 0.75rem 1.25rem;
            border-radius: 8px;
            border: 1px solid var(--panel-border);
        }

        .playback-btns {
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }

        .scrubber-container {
            display: flex;
            align-items: center;
            gap: 0.75rem;
            flex: 1;
            min-width: 260px;
        }

        .scrubber-slider {
            flex: 1;
        }

        .phase-jump-row {
            display: flex;
            flex-wrap: wrap;
            gap: 0.4rem;
        }

        .phase-jump-btn {
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid var(--panel-border);
            color: var(--text-muted);
            padding: 0.25rem 0.6rem;
            border-radius: 4px;
            font-size: 0.72rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.15s;
        }

        .phase-jump-btn:hover {
            background: rgba(255, 255, 255, 0.12);
            color: var(--text-main);
            border-color: var(--panel-hover);
        }

        /* Live Visual Diagnostic Logs Console */
        .logs-console {
            background: #080c14;
            border: 1px solid var(--panel-border);
            border-radius: 8px;
            padding: 0.75rem 1rem;
            height: 180px;
            overflow-y: auto;
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.75rem;
            line-height: 1.6;
            display: flex;
            flex-direction: column-reverse;
        }

        .log-entry {
            display: flex;
            gap: 0.6rem;
        }

        .log-time {
            color: #64748b;
        }

        .log-tag {
            font-weight: 700;
            padding: 0 0.3rem;
            border-radius: 3px;
        }

        .log-tag.STATE { background: rgba(59, 130, 246, 0.2); color: #60a5fa; }
        .log-tag.CAMERA { background: rgba(139, 92, 246, 0.2); color: #c084fc; }
        .log-tag.AUDIO { background: rgba(245, 158, 11, 0.2); color: #fbbf24; }
        .log-tag.VFX { background: rgba(239, 68, 68, 0.2); color: #f87171; }
        .log-tag.INFO { background: rgba(6, 182, 212, 0.2); color: #22d3ee; }

        /* JSON Editor */
        #jsonTextarea {
            width: 100%;
            height: 480px;
            background: #0d1117;
            color: #58a6ff;
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.82rem;
            border: 1px solid var(--panel-border);
            border-radius: 8px;
            padding: 1rem;
            resize: vertical;
            line-height: 1.5;
            outline: none;
        }

        /* Toast */
        #toast {
            position: fixed;
            bottom: 2rem;
            right: 2rem;
            padding: 0.8rem 1.4rem;
            border-radius: 8px;
            font-size: 0.875rem;
            font-weight: 600;
            display: none;
            align-items: center;
            gap: 0.5rem;
            z-index: 9999;
            box-shadow: 0 10px 25px rgba(0,0,0,0.5);
            animation: slideUp 0.3s ease;
        }

        #toast.success { background: #064e3b; color: #6ee7b7; border: 1px solid #059669; }
        #toast.error { background: #7f1d1d; color: #fca5a5; border: 1px solid #dc2626; }

        @keyframes slideUp {
            from { transform: translateY(20px); opacity: 0; }
            to { transform: translateY(0); opacity: 1; }
        }
    </style>
</head>
<body>

    <!-- Header -->
    <header>
        <div class="brand">
            <div class="brand-icon">⚡</div>
            <div class="brand-title">
                <h1>Transformation Cutscene Editor</h1>
                <p>State Visualizer, Live Preview Studio & Camera Rig Studio</p>
            </div>
        </div>
        <div class="header-actions">
            <button class="btn btn-preview" onclick="switchTab('preview'); startCutscenePreview();">
                ▶ Live Preview
            </button>
            <button class="btn btn-secondary" onclick="resetDefaults()">↺ Reset Defaults</button>
            <button class="btn btn-primary" onclick="saveConfiguration()">💾 Save Changes</button>
        </div>
    </header>

    <!-- Timeline Visualizer -->
    <div class="timeline-container">
        <div class="timeline-header">
            <span>Sequence Timeline (Click segment to jump in Preview)</span>
            <span id="totalDurationLabel">Total: ~10.20s</span>
        </div>
        <div class="timeline-bar" id="timelineBar">
            <!-- Rendered dynamically -->
        </div>
    </div>

    <!-- Main Workspace -->
    <div class="main-content">
        <!-- Sidebar Navigation -->
        <div class="tabs-sidebar">
            <button class="tab-btn preview-tab-btn" onclick="switchTab('preview'); startCutscenePreview();">🎬 Live Preview & Logs</button>
            <button class="tab-btn active" onclick="switchTab('timing')">⏱️ Timing & Loops</button>
            <button class="tab-btn" onclick="switchTab('camera')">📷 Camera Rig</button>
            <button class="tab-btn" onclick="switchTab('audio')">🔊 Audio & SFX</button>
            <button class="tab-btn" onclick="switchTab('effects')">✨ VFX & Particles</button>
            <button class="tab-btn" onclick="switchTab('assets')">📂 Assets & Scale</button>
            <button class="tab-btn" onclick="switchTab('json')">📄 Raw JSON</button>
        </div>

        <!-- TAB 0: LIVE PREVIEW & VISUAL LOGS -->
        <div class="tab-panel" id="tab-preview">
            <div class="card">
                <div class="card-header">
                    <div class="card-title">🎬 Real-Time Interactive Canvas Preview</div>
                    <div class="card-badge pink">LIVE SIMULATOR</div>
                </div>

                <!-- Canvas Preview Stage -->
                <div class="preview-stage-container">
                    <canvas id="previewCanvas" width="1280" height="720"></canvas>

                    <!-- HUD Overlay & Visual Labels -->
                    <div class="hud-overlay" id="hudOverlay">
                        <div class="hud-top">
                            <div class="hud-badge">
                                <span class="hud-phase-pill" id="hudPhaseName" style="color: var(--accent-cyan);">PHASE 0: FADE IN</span>
                                <span id="hudTime">Time: 0.00s / 10.20s</span>
                                <span id="hudFrame">Frame: 0 / 1</span>
                            </div>
                            <div class="hud-badge">
                                <span style="color: var(--accent-purple); font-weight:700;">📷 CAMERA RIG</span>
                                <span id="hudZoom">Zoom: 1.00x</span>
                                <span id="hudShake">Shake: 0.0 px (0 Hz)</span>
                                <span id="hudSway">Sway Offset: 0 px</span>
                            </div>
                        </div>

                        <div class="hud-bottom">
                            <div class="hud-badge">
                                <span style="color: var(--accent-amber); font-weight:700;">✨ VFX ENGINE</span>
                                <span id="hudVortex">Gravity Force: 0.0</span>
                                <span id="hudFlash">Screen Flash: Alpha 0</span>
                                <span id="hudParticles">Active Embers: 40</span>
                            </div>
                            <div class="hud-badge">
                                <span style="color: var(--accent-pink); font-weight:700;">🔊 AUDIO CUES</span>
                                <span id="hudAudio">Active: None</span>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Playback Controls -->
                <div class="playback-controls">
                    <div class="playback-btns">
                        <button class="btn btn-primary" style="padding:0.4rem 0.9rem;" id="playPauseBtn" onclick="togglePlayPause()">❚❚ Pause</button>
                        <button class="btn btn-secondary" style="padding:0.4rem 0.8rem;" onclick="restartCutscenePreview()">↺ Replay</button>
                        <button class="btn btn-secondary" style="padding:0.4rem 0.8rem;" onclick="toggleAudioMute()" id="muteBtn">🔊 Audio On</button>
                        <button class="btn btn-secondary" style="padding:0.4rem 0.8rem;" onclick="toggleHUD()" id="hudToggleBtn">🏷️ Hide Labels</button>
                    </div>

                    <div class="scrubber-container">
                        <span style="font-size:0.8rem; font-family:'JetBrains Mono';" id="scrubTimeDisplay">0.00s</span>
                        <input type="range" min="0" max="10" step="0.01" value="0" class="scrubber-slider" id="timelineScrubber" oninput="onScrub(this.value)">
                        <select id="speedSelect" onchange="changePlaybackSpeed(this.value)" style="padding:0.25rem 0.5rem; font-size:0.75rem;">
                            <option value="0.25">0.25x Speed</option>
                            <option value="0.5">0.5x Speed</option>
                            <option value="1.0" selected>1.0x Speed</option>
                            <option value="1.5">1.5x Speed</option>
                            <option value="2.0">2.0x Speed</option>
                        </select>
                    </div>

                    <div class="phase-jump-row">
                        <button class="phase-jump-btn" onclick="jumpToPhase('fade_in')">Fade In</button>
                        <button class="phase-jump-btn" onclick="jumpToPhase('orb_collapse')">Orb</button>
                        <button class="phase-jump-btn" onclick="jumpToPhase('orb_loop')">Loop</button>
                        <button class="phase-jump-btn" onclick="jumpToPhase('demon_burst')">Demon Burst</button>
                        <button class="phase-jump-btn" onclick="jumpToPhase('attack_left')">Slash L</button>
                        <button class="phase-jump-btn" onclick="jumpToPhase('attack_right')">Slash R</button>
                        <button class="phase-jump-btn" onclick="jumpToPhase('special_tentacles')">Tentacles</button>
                        <button class="phase-jump-btn" onclick="jumpToPhase('revert')">Revert</button>
                    </div>
                </div>

                <!-- Visual Diagnostic Logs Box -->
                <div>
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.4rem;">
                        <span style="font-size:0.8rem; font-weight:700; color:var(--text-muted);">📊 LIVE VISUAL LOGS & EVENTS CONSOLE</span>
                        <button class="btn btn-secondary" style="padding:0.2rem 0.6rem; font-size:0.7rem;" onclick="clearLogs()">Clear Console</button>
                    </div>
                    <div class="logs-console" id="visualLogsConsole">
                        <!-- Log entries added dynamically -->
                    </div>
                </div>
            </div>
        </div>

        <!-- TAB 1: Timing & Loops -->
        <div class="tab-panel active" id="tab-timing">
            <div class="card">
                <div class="card-header">
                    <div class="card-title">⏱️ Phase Durations & Animation Speeds</div>
                    <div class="card-badge">TIMING CONFIG</div>
                </div>
                <div class="grid-2">
                    <div class="control-group">
                        <div class="control-label">
                            <span>Fade In Duration</span>
                            <span class="control-val" id="val_fade_in_duration">1.5s</span>
                        </div>
                        <input type="range" min="0.2" max="3.0" step="0.05" id="in_fade_in_duration" oninput="updateVal('fade_in_duration', this.value, 's')">
                    </div>

                    <div class="control-group">
                        <div class="control-label">
                            <span>Orb Collapse Speed (Seconds/Frame)</span>
                            <span class="control-val" id="val_orb_frame_duration">0.11s</span>
                        </div>
                        <input type="range" min="0.03" max="0.25" step="0.005" id="in_orb_frame_duration" oninput="updateVal('orb_frame_duration', this.value, 's')">
                    </div>

                    <div class="control-group">
                        <div class="control-label">
                            <span>Orb Singularity Loop Speed</span>
                            <span class="control-val" id="val_orb_loop_frame_duration">0.09s</span>
                        </div>
                        <input type="range" min="0.03" max="0.20" step="0.005" id="in_orb_loop_frame_duration" oninput="updateVal('orb_loop_frame_duration', this.value, 's')">
                    </div>

                    <div class="control-group">
                        <div class="control-label">
                            <span>Orb Loop Repetitions</span>
                            <span class="control-val" id="val_orb_loop_cycles">3x</span>
                        </div>
                        <input type="range" min="1" max="8" step="1" id="in_orb_loop_cycles" oninput="updateVal('orb_loop_cycles', this.value, 'x')">
                    </div>

                    <div class="control-group">
                        <div class="control-label">
                            <span>Demon Burst Speed (Fast Eruption)</span>
                            <span class="control-val" id="val_demon_burst_frame_duration">0.035s</span>
                        </div>
                        <input type="range" min="0.015" max="0.10" step="0.005" id="in_demon_burst_frame_duration" oninput="updateVal('demon_burst_frame_duration', this.value, 's')">
                    </div>

                    <div class="control-group">
                        <div class="control-label">
                            <span>Demon Attack Left & Right Speed</span>
                            <span class="control-val" id="val_attack_frame_duration">0.055s</span>
                        </div>
                        <input type="range" min="0.02" max="0.12" step="0.005" id="in_attack_frame_duration" oninput="updateVal('attack_frame_duration', this.value, 's')">
                    </div>

                    <div class="control-group">
                        <div class="control-label">
                            <span>Special Tentacle Attack Speed</span>
                            <span class="control-val" id="val_special_frame_duration">0.075s</span>
                        </div>
                        <input type="range" min="0.03" max="0.15" step="0.005" id="in_special_frame_duration" oninput="updateVal('special_frame_duration', this.value, 's')">
                    </div>

                    <div class="control-group">
                        <div class="control-label">
                            <span>Back to Human Revert Speed</span>
                            <span class="control-val" id="val_revert_frame_duration">0.07s</span>
                        </div>
                        <input type="range" min="0.03" max="0.15" step="0.005" id="in_revert_frame_duration" oninput="updateVal('revert_frame_duration', this.value, 's')">
                    </div>

                    <div class="control-group">
                        <div class="control-label">
                            <span>Post-Revert Rest Pause</span>
                            <span class="control-val" id="val_post_pause">0.6s</span>
                        </div>
                        <input type="range" min="0.1" max="2.0" step="0.05" id="in_post_pause" oninput="updateVal('post_pause', this.value, 's')">
                    </div>

                    <div class="control-group">
                        <div class="control-label">
                            <span>Phase Crossfade Duration</span>
                            <span class="control-val" id="val_crossfade_duration">0.30s</span>
                        </div>
                        <input type="range" min="0.05" max="0.80" step="0.05" id="in_crossfade_duration" oninput="updateVal('crossfade_duration', this.value, 's')">
                    </div>
                </div>
            </div>
        </div>

        <!-- TAB 2: Camera Rig -->
        <div class="tab-panel" id="tab-camera">
            <div class="card">
                <div class="card-header">
                    <div class="card-title">📷 Dynamic Camera Rig & Sway Effects</div>
                    <div class="card-badge">CAMERA RIG</div>
                </div>
                <div class="grid-2">
                    <div class="control-group">
                        <div class="control-label">
                            <span>Orb Collapse Max Zoom</span>
                            <span class="control-val" id="val_orb_camera_zoom">1.45x</span>
                        </div>
                        <input type="range" min="1.0" max="2.2" step="0.05" id="in_orb_camera_zoom" oninput="updateVal('orb_camera_zoom', this.value, 'x')">
                    </div>

                    <div class="control-group">
                        <div class="control-label">
                            <span>Orb Collapse Zoom In Speed</span>
                            <span class="control-val" id="val_orb_camera_zoom_speed">1.2</span>
                        </div>
                        <input type="range" min="0.2" max="4.0" step="0.1" id="in_orb_camera_zoom_speed" oninput="updateVal('orb_camera_zoom_speed', this.value)">
                    </div>

                    <div class="control-group">
                        <div class="control-label">
                            <span>Orb Portal Vibration Amplitude</span>
                            <span class="control-val" id="val_orb_shake_amp">3.5 px</span>
                        </div>
                        <input type="range" min="0.0" max="15.0" step="0.5" id="in_orb_shake_amp" oninput="updateVal('orb_shake_amp', this.value, ' px')">
                    </div>

                    <div class="control-group">
                        <div class="control-label">
                            <span>Demon Burst Shake Amplitude</span>
                            <span class="control-val" id="val_demon_shake_amp">8.0 px</span>
                        </div>
                        <input type="range" min="0.0" max="25.0" step="0.5" id="in_demon_shake_amp" oninput="updateVal('demon_shake_amp', this.value, ' px')">
                    </div>

                    <div class="control-group">
                        <div class="control-label">
                            <span>Attack Directional Camera Sway (X Offset)</span>
                            <span class="control-val" id="val_attack_sway_x">55 px</span>
                        </div>
                        <input type="range" min="10" max="150" step="5" id="in_attack_sway_x" oninput="updateVal('attack_sway_x', this.value, ' px')">
                    </div>

                    <div class="control-group">
                        <div class="control-label">
                            <span>Attack Sway Lerp Speed</span>
                            <span class="control-val" id="val_attack_sway_speed">4.0</span>
                        </div>
                        <input type="range" min="1.0" max="10.0" step="0.5" id="in_attack_sway_speed" oninput="updateVal('attack_sway_speed', this.value)">
                    </div>

                    <div class="control-group">
                        <div class="control-label">
                            <span>Special Tentacle Max Zoom ('F' Attack)</span>
                            <span class="control-val" id="val_tentacle_zoom_max">1.50x</span>
                        </div>
                        <input type="range" min="1.0" max="2.2" step="0.05" id="in_tentacle_zoom_max" oninput="updateVal('tentacle_zoom_max', this.value, 'x')">
                    </div>

                    <div class="control-group">
                        <div class="control-label">
                            <span>Tentacle Peak Zoom Frame</span>
                            <span class="control-val" id="val_tentacle_peak_frame">Frame 11</span>
                        </div>
                        <input type="range" min="5" max="18" step="1" id="in_tentacle_peak_frame" oninput="updateVal('tentacle_peak_frame', this.value, 'Frame ')">
                    </div>
                </div>
            </div>
        </div>

        <!-- TAB 3: Audio & SFX -->
        <div class="tab-panel" id="tab-audio">
            <div class="card">
                <div class="card-header">
                    <div class="card-title">🔊 Sound Effects & Cues Per Phase</div>
                    <div class="card-badge">SFX CHANNELS</div>
                </div>
                <div class="grid-2" id="sfxPhaseCards">
                    <!-- Rendered dynamically -->
                </div>
            </div>
        </div>

        <!-- TAB 4: VFX & Particles -->
        <div class="tab-panel" id="tab-effects">
            <div class="card">
                <div class="card-header">
                    <div class="card-title">✨ Gravity Vortex, Blast & Screen Flashes</div>
                    <div class="card-badge">VFX ENGINE</div>
                </div>
                <div class="grid-2">
                    <div class="control-group">
                        <div class="control-label">
                            <span>Ember Particle Density</span>
                            <span class="control-val" id="val_particle_count">40 particles</span>
                        </div>
                        <input type="range" min="10" max="150" step="5" id="in_particle_count" oninput="updateVal('particle_count', this.value, ' particles')">
                    </div>

                    <div class="control-group">
                        <div class="control-label">
                            <span>Gravitational Inward Vortex Pull</span>
                            <span class="control-val" id="val_gravity_strength">8.0</span>
                        </div>
                        <input type="range" min="0.0" max="30.0" step="1.0" id="in_gravity_strength" oninput="updateVal('gravity_strength', this.value)">
                    </div>

                    <div class="control-group">
                        <div class="control-label">
                            <span>Demon Burst Explosion Blast Force</span>
                            <span class="control-val" id="val_explosion_strength">450.0</span>
                        </div>
                        <input type="range" min="100.0" max="1200.0" step="25.0" id="in_explosion_strength" oninput="updateVal('explosion_strength', this.value)">
                    </div>

                    <div class="control-group">
                        <div class="control-label">
                            <span>Revert Red Flash Cycle Count</span>
                            <span class="control-val" id="val_flash_count">4 flashes</span>
                        </div>
                        <input type="range" min="1" max="10" step="1" id="in_flash_count" oninput="updateVal('flash_count', this.value, ' flashes')">
                    </div>

                    <div class="control-group">
                        <div class="control-label">
                            <span>Demon Eruption Flash Color (White Blast)</span>
                        </div>
                        <div class="color-row">
                            <input type="color" id="in_flash_color_white" onchange="updateColor('flash_color_white', this.value)">
                            <span class="control-val" id="val_flash_color_white">#ffffff</span>
                        </div>
                    </div>

                    <div class="control-group">
                        <div class="control-label">
                            <span>Demon Shock Flash Color (Red Flash)</span>
                        </div>
                        <div class="color-row">
                            <input type="color" id="in_flash_color_red" onchange="updateColor('flash_color_red', this.value)">
                            <span class="control-val" id="val_flash_color_red">#b41414</span>
                        </div>
                    </div>

                    <div class="control-group">
                        <div class="control-label">
                            <span>Revert Pulse Flash Color</span>
                        </div>
                        <div class="color-row">
                            <input type="color" id="in_revert_flash_color" onchange="updateColor('revert_flash_color', this.value)">
                            <span class="control-val" id="val_revert_flash_color">#c80f0f</span>
                        </div>
                    </div>

                    <div class="control-group">
                        <div class="control-label">
                            <span>Scene Backdrop Color</span>
                        </div>
                        <div class="color-row">
                            <input type="color" id="in_bg_color" onchange="updateColor('bg_color', this.value)">
                            <span class="control-val" id="val_bg_color">#0c0a14</span>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- TAB 5: Assets & Scale -->
        <div class="tab-panel" id="tab-assets">
            <div class="card">
                <div class="card-header">
                    <div class="card-title">📂 Sprite Assets & Rendering Scale</div>
                    <div class="card-badge">SPRITE SETS</div>
                </div>
                <div class="grid-2">
                    <div class="control-group">
                        <div class="control-label">
                            <span>Sprite Scale Multiplier</span>
                            <span class="control-val" id="val_sprite_scale">3.5x</span>
                        </div>
                        <input type="range" min="1.0" max="6.0" step="0.25" id="in_sprite_scale" oninput="updateVal('sprite_scale', this.value, 'x')">
                    </div>

                    <div class="control-group">
                        <div class="control-label">
                            <span>Transformation Sequence Asset Directory</span>
                        </div>
                        <select id="sel_transform_dir" onchange="updateAsset('transform_dir', this.value)"></select>
                    </div>

                    <div class="control-group">
                        <div class="control-label">
                            <span>Demon Attack Left Asset Directory</span>
                        </div>
                        <select id="sel_atk_left_dir" onchange="updateAsset('atk_left_dir', this.value)"></select>
                    </div>

                    <div class="control-group">
                        <div class="control-label">
                            <span>Demon Attack Right Asset Directory</span>
                        </div>
                        <select id="sel_atk_right_dir" onchange="updateAsset('atk_right_dir', this.value)"></select>
                    </div>

                    <div class="control-group">
                        <div class="control-label">
                            <span>Special Tentacle Attack Asset Directory</span>
                        </div>
                        <select id="sel_special_atk_dir" onchange="updateAsset('special_atk_dir', this.value)"></select>
                    </div>

                    <div class="control-group">
                        <div class="control-label">
                            <span>Human Revert Asset Directory</span>
                        </div>
                        <select id="sel_revert_dir" onchange="updateAsset('revert_dir', this.value)"></select>
                    </div>
                </div>
            </div>
        </div>

        <!-- TAB 6: Raw JSON -->
        <div class="tab-panel" id="tab-json">
            <div class="card">
                <div class="card-header">
                    <div class="card-title">📄 Raw Configuration JSON</div>
                    <div class="card-badge">DIRECT EDIT</div>
                </div>
                <textarea id="jsonTextarea" spellcheck="false" oninput="onJsonEdited()"></textarea>
            </div>
        </div>
    </div>

    <!-- Toast -->
    <div id="toast"></div>

    <audio id="audioPreview"></audio>

    <script>
        let currentConfig = {};
        let availableSounds = {};
        let availableSprites = [];

        const PHASES_METADATA = [
            { id: "fade_in", label: "Fade In", color: "#3b82f6" },
            { id: "orb_collapse", label: "Orb Collapse", color: "#8b5cf6" },
            { id: "orb_loop", label: "Singularity Loop", color: "#6366f1" },
            { id: "demon_burst", label: "Demon Burst", color: "#ef4444" },
            { id: "attack_left", label: "Slash Left", color: "#f97316" },
            { id: "attack_right", label: "Slash Right", color: "#f59e0b" },
            { id: "special_tentacles", label: "Tentacles ('F')", color: "#ec4899" },
            { id: "revert", label: "Human Revert", color: "#10b981" }
        ];

        /* ─── LIVE PREVIEW ENGINE STATE ─── */
        const loadedFramesCache = {
            transform: [],
            attack_left: [],
            attack_right: [],
            special_tentacles: [],
            revert: []
        };

        let isPreviewPlaying = false;
        let previewTime = 0.0;
        let previewPlaybackSpeed = 1.0;
        let isAudioMuted = false;
        let isHudVisible = true;
        let previewRafId = null;
        let lastFrameTimestamp = 0;

        // Camera simulated state
        let simCurrentZoom = 1.0;
        let simSwayX = 0.0;
        let simShakeAmp = 0.0;
        let simShakePhase = 0.0;

        // Particles
        let simParticles = [];
        let simExplosionFired = false;

        // Audio trigger track
        let triggeredAudioMap = {};

        async function init() {
            try {
                const [cfgRes, sfxRes, sprRes] = await Promise.all([
                    fetch('/api/config').then(r => r.json()),
                    fetch('/api/sounds').then(r => r.json()),
                    fetch('/api/sprites').then(r => r.json())
                ]);

                currentConfig = cfgRes;
                availableSounds = sfxRes;
                availableSprites = sprRes;

                populateForm();
                renderSFXCards();
                populateSpriteDropdowns();
                renderTimeline();
                updateJsonEditor();

                // Preload preview frames
                preloadAllFrames();
                initSimParticles();
            } catch (e) {
                showToast("Failed to initialize editor: " + e, "error");
            }
        }

        function switchTab(tabId) {
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
            
            const btn = Array.from(document.querySelectorAll('.tab-btn')).find(b => b.getAttribute('onclick').includes(tabId));
            if (btn) btn.classList.add('active');
            
            const panel = document.getElementById('tab-' + tabId);
            if (panel) panel.classList.add('active');

            if (tabId === 'json') {
                updateJsonEditor();
            }
        }

        function rgbToHex(rgb) {
            if (!rgb || rgb.length < 3) return "#ffffff";
            return "#" + rgb.map(x => {
                const hex = Math.min(255, Math.max(0, x)).toString(16);
                return hex.length === 1 ? "0" + hex : hex;
            }).join('');
        }

        function hexToRgb(hex) {
            const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
            return result ? [
                parseInt(result[1], 16),
                parseInt(result[2], 16),
                parseInt(result[3], 16)
            ] : [255, 255, 255];
        }

        function populateForm() {
            const p = currentConfig.phases || {};
            const g = currentConfig.global || {};

            // Timing
            setRange("in_fade_in_duration", "val_fade_in_duration", p.fade_in?.duration || 1.5, "s");
            setRange("in_orb_frame_duration", "val_orb_frame_duration", p.orb_collapse?.frame_duration || 0.11, "s");
            setRange("in_orb_loop_frame_duration", "val_orb_loop_frame_duration", p.orb_loop?.frame_duration || 0.09, "s");
            setRange("in_orb_loop_cycles", "val_orb_loop_cycles", p.orb_loop?.loop_cycles || 3, "x");
            setRange("in_demon_burst_frame_duration", "val_demon_burst_frame_duration", p.demon_burst?.frame_duration || 0.035, "s");
            setRange("in_attack_frame_duration", "val_attack_frame_duration", p.attack_left?.frame_duration || 0.055, "s");
            setRange("in_special_frame_duration", "val_special_frame_duration", p.special_tentacles?.frame_duration || 0.075, "s");
            setRange("in_revert_frame_duration", "val_revert_frame_duration", p.revert?.frame_duration || 0.07, "s");
            setRange("in_post_pause", "val_post_pause", p.revert?.post_pause || 0.6, "s");
            setRange("in_crossfade_duration", "val_crossfade_duration", g.crossfade_duration || 0.30, "s");

            // Camera
            setRange("in_orb_camera_zoom", "val_orb_camera_zoom", p.orb_collapse?.camera_zoom || 1.45, "x");
            setRange("in_orb_camera_zoom_speed", "val_orb_camera_zoom_speed", p.orb_collapse?.camera_zoom_speed || 1.2, "");
            setRange("in_orb_shake_amp", "val_orb_shake_amp", p.orb_collapse?.shake_amplitude || 3.5, " px");
            setRange("in_demon_shake_amp", "val_demon_shake_amp", p.demon_burst?.shake_amplitude || 8.0, " px");
            setRange("in_attack_sway_x", "val_attack_sway_x", Math.abs(p.attack_left?.sway_x || 55.0), " px");
            setRange("in_attack_sway_speed", "val_attack_sway_speed", p.attack_left?.sway_speed || 4.0, "");
            setRange("in_tentacle_zoom_max", "val_tentacle_zoom_max", p.special_tentacles?.zoom_max || 1.50, "x");
            setRange("in_tentacle_peak_frame", "val_tentacle_peak_frame", p.special_tentacles?.zoom_peak_frame || 11, "Frame ");

            // VFX
            setRange("in_particle_count", "val_particle_count", g.particle_count || 40, " particles");
            setRange("in_gravity_strength", "val_gravity_strength", p.orb_collapse?.gravity_strength || 8.0, "");
            setRange("in_explosion_strength", "val_explosion_strength", p.demon_burst?.explosion_strength || 450.0, "");
            setRange("in_flash_count", "val_flash_count", p.revert?.flash_count || 4, " flashes");

            // Colors
            setColor("in_flash_color_white", "val_flash_color_white", p.demon_burst?.flash_color_white || [255, 255, 255]);
            setColor("in_flash_color_red", "val_flash_color_red", p.demon_burst?.flash_color_red || [180, 20, 20]);
            setColor("in_revert_flash_color", "val_revert_flash_color", p.revert?.flash_color || [200, 15, 15]);
            setColor("in_bg_color", "val_bg_color", g.background_color || [12, 10, 20]);

            // Assets
            setRange("in_sprite_scale", "val_sprite_scale", g.sprite_scale || 3.5, "x");
        }

        function setRange(inputId, valId, val, unit) {
            const el = document.getElementById(inputId);
            const valEl = document.getElementById(valId);
            if (el) el.value = val;
            if (valEl) {
                if (unit === "Frame ") valEl.innerText = unit + val;
                else valEl.innerText = val + (unit || "");
            }
        }

        function setColor(inputId, valId, rgbArr) {
            const hex = rgbToHex(rgbArr);
            const el = document.getElementById(inputId);
            const valEl = document.getElementById(valId);
            if (el) el.value = hex;
            if (valEl) valEl.innerText = hex;
        }

        function updateVal(key, val, unit) {
            const num = parseFloat(val);
            const valEl = document.getElementById("val_" + key);
            if (valEl) {
                if (unit === "Frame ") valEl.innerText = unit + num;
                else valEl.innerText = num + (unit || "");
            }

            const p = currentConfig.phases;
            const g = currentConfig.global;

            switch (key) {
                case "fade_in_duration": p.fade_in.duration = num; break;
                case "orb_frame_duration": p.orb_collapse.frame_duration = num; break;
                case "orb_loop_frame_duration": p.orb_loop.frame_duration = num; break;
                case "orb_loop_cycles": p.orb_loop.loop_cycles = parseInt(num); break;
                case "demon_burst_frame_duration": p.demon_burst.frame_duration = num; break;
                case "attack_frame_duration":
                    p.attack_left.frame_duration = num;
                    p.attack_right.frame_duration = num;
                    break;
                case "special_frame_duration": p.special_tentacles.frame_duration = num; break;
                case "revert_frame_duration": p.revert.frame_duration = num; break;
                case "post_pause": p.revert.post_pause = num; break;
                case "crossfade_duration": g.crossfade_duration = num; break;

                case "orb_camera_zoom": p.orb_collapse.camera_zoom = num; break;
                case "orb_camera_zoom_speed": p.orb_collapse.camera_zoom_speed = num; break;
                case "orb_shake_amp": p.orb_collapse.shake_amplitude = num; break;
                case "demon_shake_amp": p.demon_burst.shake_amplitude = num; break;
                case "attack_sway_x":
                    p.attack_left.sway_x = -num;
                    p.attack_right.sway_x = num;
                    break;
                case "attack_sway_speed":
                    p.attack_left.sway_speed = num;
                    p.attack_right.sway_speed = num;
                    break;
                case "tentacle_zoom_max": p.special_tentacles.zoom_max = num; break;
                case "tentacle_peak_frame": p.special_tentacles.zoom_peak_frame = parseInt(num); break;

                case "particle_count":
                    g.particle_count = parseInt(num);
                    initSimParticles();
                    break;
                case "gravity_strength": p.orb_collapse.gravity_strength = num; break;
                case "explosion_strength": p.demon_burst.explosion_strength = num; break;
                case "flash_count": p.revert.flash_count = parseInt(num); break;
                case "sprite_scale": g.sprite_scale = num; break;
            }

            renderTimeline();
        }

        function updateColor(key, hex) {
            const rgb = hexToRgb(hex);
            const valEl = document.getElementById("val_" + key);
            if (valEl) valEl.innerText = hex;

            const p = currentConfig.phases;
            const g = currentConfig.global;

            switch (key) {
                case "flash_color_white": p.demon_burst.flash_color_white = rgb; break;
                case "flash_color_red": p.demon_burst.flash_color_red = rgb; break;
                case "revert_flash_color": p.revert.flash_color = rgb; break;
                case "bg_color": g.background_color = rgb; break;
            }
        }

        function updateAsset(key, val) {
            if (!currentConfig.assets) currentConfig.assets = {};
            currentConfig.assets[key] = val;
            preloadAllFrames();
        }

        function renderSFXCards() {
            const container = document.getElementById('sfxPhaseCards');
            container.innerHTML = '';

            const soundOptions = Object.keys(availableSounds).map(k => `<option value="${k}">${k}</option>`).join('');

            PHASES_METADATA.forEach(phase => {
                const pCfg = currentConfig.phases[phase.id] || {};
                const sfxList = pCfg.sfx || [];

                const card = document.createElement('div');
                card.className = 'control-group';
                card.style.background = 'rgba(0,0,0,0.25)';
                card.style.padding = '0.75rem';
                card.style.borderRadius = '8px';
                card.style.border = '1px solid var(--panel-border)';

                let chipsHtml = sfxList.map((sfx, idx) => `
                    <div class="sfx-chip">
                        <span>🔊 ${sfx}</span>
                        <button class="sfx-play-btn" onclick="playSound('${sfx}')" title="Preview sound">▶</button>
                        <button class="sfx-remove-btn" onclick="removeSFX('${phase.id}', ${idx})" title="Remove sound">×</button>
                    </div>
                `).join('');

                card.innerHTML = `
                    <div class="control-label">
                        <span style="color:${phase.color}; font-weight:700;">${phase.label}</span>
                        <span style="font-size:0.75rem; color:var(--text-muted);">${sfxList.length} triggers</span>
                    </div>
                    <div class="sfx-tag-container" id="sfx_chips_${phase.id}">
                        ${chipsHtml || '<span style="font-size:0.75rem; color:var(--text-muted); font-style:italic;">No sound triggers</span>'}
                    </div>
                    <div class="sfx-add-row">
                        <select id="sfx_select_${phase.id}" style="flex:1;">
                            ${soundOptions}
                        </select>
                        <button class="btn btn-secondary" style="padding:0.4rem 0.8rem; font-size:0.75rem;" onclick="addSFX('${phase.id}')">+ Add</button>
                    </div>
                `;

                container.appendChild(card);
            });
        }

        function addSFX(phaseId) {
            const sel = document.getElementById('sfx_select_' + phaseId);
            const val = sel.value;
            if (!val) return;

            if (!currentConfig.phases[phaseId]) currentConfig.phases[phaseId] = {};
            if (!currentConfig.phases[phaseId].sfx) currentConfig.phases[phaseId].sfx = [];

            if (!currentConfig.phases[phaseId].sfx.includes(val)) {
                currentConfig.phases[phaseId].sfx.push(val);
                renderSFXCards();
            }
        }

        function removeSFX(phaseId, idx) {
            if (currentConfig.phases[phaseId] && currentConfig.phases[phaseId].sfx) {
                currentConfig.phases[phaseId].sfx.splice(idx, 1);
                renderSFXCards();
            }
        }

        function playSound(name) {
            if (isAudioMuted) return;
            const relPath = availableSounds[name];
            if (!relPath) return;
            const audio = new Audio('/audio/' + encodeURIComponent(relPath));
            audio.volume = 0.6;
            audio.play().catch(e => console.log("Audio play error:", e));
        }

        function populateSpriteDropdowns() {
            const selects = [
                'sel_transform_dir', 'sel_atk_left_dir', 'sel_atk_right_dir',
                'sel_special_atk_dir', 'sel_revert_dir'
            ];

            const a = currentConfig.assets || {};
            const mapping = {
                'sel_transform_dir': a.transform_dir,
                'sel_atk_left_dir': a.atk_left_dir,
                'sel_atk_right_dir': a.atk_right_dir,
                'sel_special_atk_dir': a.special_atk_dir,
                'sel_revert_dir': a.revert_dir
            };

            selects.forEach(sId => {
                const el = document.getElementById(sId);
                if (!el) return;
                el.innerHTML = availableSprites.map(dir => {
                    const selected = (dir === mapping[sId]) ? 'selected' : '';
                    return `<option value="${dir}" ${selected}>${dir}</option>`;
                }).join('');
            });
        }

        function getPhaseDurations() {
            const p = currentConfig.phases || {};
            return {
                fade_in: p.fade_in?.duration || 1.5,
                orb_collapse: (p.orb_collapse?.frame_duration || 0.11) * 16,
                orb_loop: (p.orb_loop?.frame_duration || 0.09) * 8 * (p.orb_loop?.loop_cycles || 3),
                demon_burst: (p.demon_burst?.frame_duration || 0.035) * 13,
                attack_left: (p.attack_left?.frame_duration || 0.055) * 12,
                attack_right: (p.attack_right?.frame_duration || 0.055) * 12,
                special_tentacles: (p.special_tentacles?.frame_duration || 0.075) * 19,
                revert: (p.revert?.frame_duration || 0.07) * 14 + (p.revert?.post_pause || 0.6)
            };
        }

        function renderTimeline() {
            const bar = document.getElementById('timelineBar');
            bar.innerHTML = '';

            const durations = getPhaseDurations();
            const total = Object.values(durations).reduce((a, b) => a + b, 0);
            document.getElementById('totalDurationLabel').innerText = `Total Duration: ~${total.toFixed(2)}s`;

            const scrubber = document.getElementById('timelineScrubber');
            if (scrubber) scrubber.max = total.toFixed(2);

            let cumulative = 0;
            PHASES_METADATA.forEach(phase => {
                const d = durations[phase.id] || 1.0;
                const pct = (d / total) * 100;
                const phaseStart = cumulative;
                cumulative += d;

                const seg = document.createElement('div');
                seg.className = 'timeline-segment';
                seg.style.width = pct + '%';
                seg.style.backgroundColor = phase.color;
                seg.innerText = phase.label;
                seg.title = `${phase.label}: ${d.toFixed(2)}s (${pct.toFixed(1)}%) — Click to jump`;
                seg.onclick = () => {
                    switchTab('preview');
                    startCutscenePreview();
                    previewTime = phaseStart;
                    triggeredAudioMap = {};
                    addLog('STATE', `Jumped to phase: ${phase.label} (t=${phaseStart.toFixed(2)}s)`);
                };

                bar.appendChild(seg);
            });
        }

        function updateJsonEditor() {
            const ta = document.getElementById('jsonTextarea');
            ta.value = JSON.stringify(currentConfig, null, 2);
        }

        function onJsonEdited() {
            try {
                const ta = document.getElementById('jsonTextarea');
                const parsed = JSON.parse(ta.value);
                currentConfig = parsed;
                populateForm();
                renderSFXCards();
                renderTimeline();
                preloadAllFrames();
            } catch (e) {
                // Ignore parse errors while typing
            }
        }

        async function saveConfiguration() {
            try {
                const res = await fetch('/api/config', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(currentConfig)
                });
                const data = await res.json();
                if (data.status === 'ok') {
                    showToast('Configuration saved successfully! ✔', 'success');
                    addLog('INFO', 'Configuration saved to game_data/cutscene_config.json');
                } else {
                    showToast('Failed to save configuration: ' + data.error, 'error');
                }
            } catch (e) {
                showToast('Error saving: ' + e, 'error');
            }
        }

        async function resetDefaults() {
            if (!confirm("Are you sure you want to restore default transformation cutscene settings?")) return;
            try {
                const res = await fetch('/api/reset', { method: 'POST' });
                const data = await res.json();
                if (data.status === 'ok') {
                    currentConfig = data.config;
                    populateForm();
                    renderSFXCards();
                    populateSpriteDropdowns();
                    renderTimeline();
                    updateJsonEditor();
                    preloadAllFrames();
                    showToast('Reset to factory defaults! ↺', 'success');
                    addLog('INFO', 'Reset cutscene configuration to factory defaults');
                }
            } catch (e) {
                showToast('Reset error: ' + e, 'error');
            }
        }

        function showToast(msg, type = 'success') {
            const toast = document.getElementById('toast');
            toast.className = type;
            toast.innerText = msg;
            toast.style.display = 'flex';
            setTimeout(() => {
                toast.style.display = 'none';
            }, 3500);
        }

        /* ─── FRAME PRELOADING FOR CANVAS PREVIEW ─── */
        async function loadImagesForDir(dir) {
            if (!dir) return [];
            try {
                const res = await fetch('/api/frames?dir=' + encodeURIComponent(dir));
                const list = await res.json();
                const promises = list.map(src => {
                    return new Promise((resolve) => {
                        const img = new Image();
                        img.src = '/sprites/' + encodeURIComponent(src);
                        img.onload = () => resolve(img);
                        img.onerror = () => resolve(null);
                    });
                });
                const imgs = await Promise.all(promises);
                return imgs.filter(img => img !== null);
            } catch (e) {
                console.error("Failed to load frames for:", dir, e);
                return [];
            }
        }

        async function preloadAllFrames() {
            const a = currentConfig.assets || {};
            addLog('INFO', 'Preloading transformation sprite frames...');
            const [tfImgs, atkLImgs, atkRImgs, spImgs, revImgs] = await Promise.all([
                loadImagesForDir(a.transform_dir || "assets/shadow_warrior/transform"),
                loadImagesForDir(a.atk_left_dir || "assets/shadow_warrior/e_3_atk"),
                loadImagesForDir(a.atk_right_dir || "assets/shadow_warrior/e_3_atk"),
                loadImagesForDir(a.special_atk_dir || "assets/shadow_warrior/e_sp_atk"),
                loadImagesForDir(a.revert_dir || "assets/shadow_warrior/back2human")
            ]);

            loadedFramesCache.transform = tfImgs;
            loadedFramesCache.attack_left = atkLImgs;
            loadedFramesCache.attack_right = atkRImgs;
            loadedFramesCache.special_tentacles = spImgs;
            loadedFramesCache.revert = revImgs;
            addLog('INFO', `Loaded ${tfImgs.length} transform, ${atkLImgs.length} slash, ${spImgs.length} special, ${revImgs.length} revert frames!`);
            renderPreviewFrame(0);
        }

        function initSimParticles() {
            const count = currentConfig.global?.particle_count || 40;
            simParticles = [];
            for (let i = 0; i < count; i++) {
                simParticles.push({
                    x: Math.random() * 1280,
                    y: Math.random() * 720,
                    vx: (Math.random() - 0.5) * 40,
                    vy: -Math.random() * 25 - 5,
                    size: Math.random() * 3 + 2,
                    alphaPhase: Math.random() * Math.PI * 2,
                    r: Math.floor(Math.random() * 55 + 200),
                    g: Math.floor(Math.random() * 100 + 120),
                    b: Math.floor(Math.random() * 60 + 20)
                });
            }
        }

        /* ─── LIVE PREVIEW LOOP & LOGIC ─── */
        function startCutscenePreview() {
            if (!isPreviewPlaying) {
                isPreviewPlaying = true;
                lastFrameTimestamp = performance.now();
                document.getElementById('playPauseBtn').innerText = '❚❚ Pause';
                previewLoop();
            }
        }

        function togglePlayPause() {
            isPreviewPlaying = !isPreviewPlaying;
            document.getElementById('playPauseBtn').innerText = isPreviewPlaying ? '❚❚ Pause' : '▶ Play';
            if (isPreviewPlaying) {
                lastFrameTimestamp = performance.now();
                previewLoop();
            }
        }

        function restartCutscenePreview() {
            previewTime = 0.0;
            triggeredAudioMap = {};
            simExplosionFired = false;
            simCurrentZoom = 1.0;
            simSwayX = 0.0;
            simShakeAmp = 0.0;
            addLog('STATE', 'Restarted preview from t=0.00s');
            if (!isPreviewPlaying) {
                startCutscenePreview();
            }
        }

        function toggleAudioMute() {
            isAudioMuted = !isAudioMuted;
            document.getElementById('muteBtn').innerText = isAudioMuted ? '🔇 Audio Muted' : '🔊 Audio On';
        }

        function toggleHUD() {
            isHudVisible = !isHudVisible;
            document.getElementById('hudOverlay').style.display = isHudVisible ? 'flex' : 'none';
            document.getElementById('hudToggleBtn').innerText = isHudVisible ? '🏷️ Hide Labels' : '🏷️ Show Labels';
        }

        function changePlaybackSpeed(speed) {
            previewPlaybackSpeed = parseFloat(speed);
            addLog('INFO', `Playback speed set to ${previewPlaybackSpeed}x`);
        }

        function onScrub(val) {
            previewTime = parseFloat(val);
            triggeredAudioMap = {};
            renderPreviewFrame(0);
        }

        function jumpToPhase(phaseId) {
            switchTab('preview');
            startCutscenePreview();
            const durations = getPhaseDurations();
            let t = 0;
            for (let ph of PHASES_METADATA) {
                if (ph.id === phaseId) break;
                t += durations[ph.id];
            }
            previewTime = t;
            triggeredAudioMap = {};
            addLog('STATE', `Jumped to phase: ${phaseId} (t=${t.toFixed(2)}s)`);
        }

        function addLog(tag, msg) {
            const consoleEl = document.getElementById('visualLogsConsole');
            if (!consoleEl) return;
            const row = document.createElement('div');
            row.className = 'log-entry';
            const now = new Date();
            const timeStr = `${String(now.getHours()).padStart(2,'0')}:${String(now.getMinutes()).padStart(2,'0')}:${String(now.getSeconds()).padStart(2,'0')}.${String(Math.floor(now.getMilliseconds()/10)).padStart(2,'0')}`;
            
            row.innerHTML = `
                <span class="log-time">[${timeStr}]</span>
                <span class="log-tag ${tag}">${tag}</span>
                <span>${msg}</span>
            `;
            consoleEl.prepend(row);

            // Cap logs at 100 entries
            while (consoleEl.children.length > 100) {
                consoleEl.removeChild(consoleEl.lastChild);
            }
        }

        function clearLogs() {
            const consoleEl = document.getElementById('visualLogsConsole');
            if (consoleEl) consoleEl.innerHTML = '';
        }

        function previewLoop() {
            if (!isPreviewPlaying) return;
            const now = performance.now();
            const dt = Math.min((now - lastFrameTimestamp) / 1000, 0.1) * previewPlaybackSpeed;
            lastFrameTimestamp = now;

            previewTime += dt;
            const durations = getPhaseDurations();
            const totalDur = Object.values(durations).reduce((a, b) => a + b, 0);

            if (previewTime >= totalDur) {
                previewTime = 0.0;
                triggeredAudioMap = {};
                simExplosionFired = false;
                addLog('STATE', 'Loop sequence completed. Looping to start.');
            }

            renderPreviewFrame(dt);
            previewRafId = requestAnimationFrame(previewLoop);
        }

        function easeInOut(t) {
            return 0.5 - 0.5 * Math.cos(Math.PI * t);
        }

        function lerp(a, b, t) {
            return a + (b - a) * Math.min(1.0, Math.max(0.0, t));
        }

        function renderPreviewFrame(dt) {
            const canvas = document.getElementById('previewCanvas');
            if (!canvas) return;
            const ctx = canvas.getContext('2d');
            const W = 1280;
            const H = 720;

            const p = currentConfig.phases || {};
            const g = currentConfig.global || {};
            const durations = getPhaseDurations();
            const totalDur = Object.values(durations).reduce((a, b) => a + b, 0);

            // Find current phase and phase-local time
            let remaining = previewTime;
            let currentPhase = PHASES_METADATA[0];
            let phaseLocalTime = 0;
            let phaseDuration = durations.fade_in || 1.5;

            for (let ph of PHASES_METADATA) {
                const d = durations[ph.id] || 1.0;
                if (remaining <= d || ph.id === PHASES_METADATA[PHASES_METADATA.length - 1].id) {
                    currentPhase = ph;
                    phaseLocalTime = remaining;
                    phaseDuration = d;
                    break;
                }
                remaining -= d;
            }

            // Update Scrubber UI
            const scrubber = document.getElementById('timelineScrubber');
            if (scrubber) scrubber.value = previewTime;
            const scrubDisplay = document.getElementById('scrubTimeDisplay');
            if (scrubDisplay) scrubDisplay.innerText = previewTime.toFixed(2) + 's / ' + totalDur.toFixed(2) + 's';

            // Phase audio triggers
            const sfxList = p[currentPhase.id]?.sfx || [];
            if (sfxList.length > 0 && !triggeredAudioMap[currentPhase.id]) {
                triggeredAudioMap[currentPhase.id] = true;
                sfxList.forEach(snd => {
                    playSound(snd);
                    addLog('AUDIO', `Triggered SFX: '${snd}' on phase [${currentPhase.label}]`);
                });
            }

            // Target Camera & VFX parameters calculation based on active phase
            let targetZoom = 1.0;
            let targetZoomSpeed = 2.0;
            let targetShakeAmp = 0.0;
            let shakeFreq = 12.0;
            let targetSwayX = 0.0;
            let swaySpeed = 4.0;
            let gravityPull = 0.0;
            let explosionForce = 0.0;
            let flashAlpha = 0.0;
            let flashColor = [255, 255, 255];
            let activeSprite = null;
            let flipHorizontal = false;
            let spriteAlpha = 1.0;
            let frameIdx = 0;
            let totalPhaseFrames = 1;

            if (currentPhase.id === "fade_in") {
                const t = Math.min(1.0, phaseLocalTime / Math.max(0.01, phaseDuration));
                spriteAlpha = Math.max(0.05, easeInOut(t));
                activeSprite = (loadedFramesCache.transform && loadedFramesCache.transform[0]) || null;
                totalPhaseFrames = 1;
                frameIdx = 0;
            } else if (currentPhase.id === "orb_collapse") {
                targetZoom = p.orb_collapse?.camera_zoom || 1.45;
                targetZoomSpeed = p.orb_collapse?.camera_zoom_speed || 1.2;
                targetShakeAmp = p.orb_collapse?.shake_amplitude || 3.5;
                shakeFreq = p.orb_collapse?.shake_frequency || 10.0;
                gravityPull = p.orb_collapse?.gravity_strength || 8.0;

                const fDur = p.orb_collapse?.frame_duration || 0.11;
                const orbFrames = (loadedFramesCache.transform || []).slice(0, 16);
                totalPhaseFrames = Math.max(1, orbFrames.length);
                frameIdx = Math.min(totalPhaseFrames - 1, Math.floor(phaseLocalTime / fDur));
                activeSprite = orbFrames[frameIdx] || null;
            } else if (currentPhase.id === "orb_loop") {
                targetZoom = p.orb_loop?.camera_zoom || 1.50;
                targetZoomSpeed = p.orb_loop?.camera_zoom_speed || 0.8;
                targetShakeAmp = p.orb_loop?.shake_amplitude || 4.5;
                shakeFreq = p.orb_loop?.shake_frequency || 14.0;
                gravityPull = p.orb_loop?.gravity_strength || 14.0;

                const fDur = p.orb_loop?.frame_duration || 0.09;
                const loopFrames = (loadedFramesCache.transform || []).slice(16, 24);
                totalPhaseFrames = Math.max(1, loopFrames.length);
                frameIdx = Math.floor(phaseLocalTime / fDur) % totalPhaseFrames;
                activeSprite = loopFrames[frameIdx] || null;
            } else if (currentPhase.id === "demon_burst") {
                targetZoom = 1.0;
                targetZoomSpeed = p.demon_burst?.camera_zoom_snapback_speed || 6.0;
                targetShakeAmp = phaseLocalTime < 0.25 ? (p.demon_burst?.shake_amplitude || 8.0) : 0.0;
                shakeFreq = p.demon_burst?.shake_frequency || 20.0;
                explosionForce = p.demon_burst?.explosion_strength || 450.0;

                const fDur = p.demon_burst?.frame_duration || 0.035;
                const burstFrames = (loadedFramesCache.transform || []).slice(24);
                totalPhaseFrames = Math.max(1, burstFrames.length);
                frameIdx = Math.min(totalPhaseFrames - 1, Math.floor(phaseLocalTime / fDur));
                activeSprite = burstFrames[frameIdx] || null;

                // Screen Flashes
                if (frameIdx < 2) {
                    flashColor = p.demon_burst?.flash_color_white || [255, 255, 255];
                    flashAlpha = Math.max(0, 1.0 - (phaseLocalTime / 0.25));
                } else if (frameIdx >= (p.demon_burst?.red_flash_trigger_frame || 3) && phaseLocalTime < 0.45) {
                    flashColor = p.demon_burst?.flash_color_red || [180, 20, 20];
                    flashAlpha = 0.75 * Math.max(0, 1.0 - ((phaseLocalTime - 0.15) / 0.3));
                }

                if (!simExplosionFired) {
                    simExplosionFired = true;
                    addLog('VFX', `💥 Demon burst shockwave explosion triggered (Blast: ${explosionForce}N)`);
                }
            } else if (currentPhase.id === "attack_left") {
                const fDur = p.attack_left?.frame_duration || 0.055;
                const atkFrames = loadedFramesCache.attack_left || [];
                totalPhaseFrames = Math.max(1, atkFrames.length);
                frameIdx = Math.min(totalPhaseFrames - 1, Math.floor(phaseLocalTime / fDur));
                activeSprite = atkFrames[frameIdx] || null;

                const swayX = p.attack_left?.sway_x || -55.0;
                const returnPct = p.attack_left?.sway_return_pct || 0.7;
                targetSwayX = (frameIdx < totalPhaseFrames * returnPct) ? swayX : 0.0;
                swaySpeed = p.attack_left?.sway_speed || 4.0;
            } else if (currentPhase.id === "attack_right") {
                const fDur = p.attack_right?.frame_duration || 0.055;
                const atkFrames = loadedFramesCache.attack_right || [];
                totalPhaseFrames = Math.max(1, atkFrames.length);
                frameIdx = Math.min(totalPhaseFrames - 1, Math.floor(phaseLocalTime / fDur));
                activeSprite = atkFrames[frameIdx] || null;
                flipHorizontal = true;

                const swayX = p.attack_right?.sway_x || 55.0;
                const returnPct = p.attack_right?.sway_return_pct || 0.7;
                targetSwayX = (frameIdx < totalPhaseFrames * returnPct) ? swayX : 0.0;
                swaySpeed = p.attack_right?.sway_speed || 4.0;
            } else if (currentPhase.id === "special_tentacles") {
                const fDur = p.special_tentacles?.frame_duration || 0.075;
                const spFrames = loadedFramesCache.special_tentacles || [];
                totalPhaseFrames = Math.max(1, spFrames.length);
                frameIdx = Math.min(totalPhaseFrames - 1, Math.floor(phaseLocalTime / fDur));
                activeSprite = spFrames[frameIdx] || null;

                const peakFrame = p.special_tentacles?.zoom_peak_frame || 11;
                const maxZ = p.special_tentacles?.zoom_max || 1.50;
                if (frameIdx <= peakFrame) {
                    const t = frameIdx / Math.max(peakFrame, 1);
                    targetZoom = lerp(1.0, maxZ, easeInOut(t));
                } else {
                    const t = (frameIdx - peakFrame) / Math.max(totalPhaseFrames - peakFrame, 1);
                    targetZoom = lerp(maxZ, 1.0, easeInOut(t));
                }
                targetZoomSpeed = p.special_tentacles?.zoom_speed || 2.5;

                if (frameIdx === peakFrame) {
                    targetShakeAmp = p.special_tentacles?.peak_shake_amplitude || 2.5;
                    shakeFreq = p.special_tentacles?.peak_shake_frequency || 8.0;
                }
            } else if (currentPhase.id === "revert") {
                const fDur = p.revert?.frame_duration || 0.07;
                const revFrames = loadedFramesCache.revert || [];
                totalPhaseFrames = Math.max(1, revFrames.length);
                frameIdx = Math.min(totalPhaseFrames - 1, Math.floor(phaseLocalTime / fDur));
                activeSprite = revFrames[frameIdx] || null;

                const flashCount = p.revert?.flash_count || 4;
                const flashCycle = p.revert?.flash_cycle_duration || 0.22;
                if (phaseLocalTime < flashCount * flashCycle) {
                    const cyclePos = phaseLocalTime % flashCycle;
                    const half = flashCycle / 2.0;
                    const pulseT = cyclePos < half ? (cyclePos / half) : (1.0 - (cyclePos - half) / half);
                    flashAlpha = ((p.revert?.flash_peak_alpha || 180) / 255.0) * easeInOut(pulseT);
                    flashColor = p.revert?.flash_color || [200, 15, 15];
                }
            }

            // Lerp Camera Simulators
            simCurrentZoom += (targetZoom - simCurrentZoom) * Math.min(1.0, dt * targetZoomSpeed);
            simSwayX += (targetSwayX - simSwayX) * Math.min(1.0, dt * swaySpeed);
            simShakeAmp += (targetShakeAmp - simShakeAmp) * Math.min(1.0, dt * 6.0);

            simShakePhase += dt * shakeFreq * Math.PI * 2;
            const shakeOffsetX = (simShakeAmp > 0.1) ? Math.sin(simShakePhase) * simShakeAmp : 0;
            const shakeOffsetY = (simShakeAmp > 0.1) ? Math.cos(simShakePhase * 1.3) * simShakeAmp * 0.7 : 0;

            // ── RENDER CANVAS ──
            const bg = g.background_color || [12, 10, 20];
            ctx.fillStyle = `rgb(${bg[0]}, ${bg[1]}, ${bg[2]})`;
            ctx.fillRect(0, 0, W, H);

            // Update & Render Particles
            const cx = W / 2.0;
            const cy = H / 2.0;

            simParticles.forEach(pt => {
                const dx = cx - pt.x;
                const dy = cy - pt.y;
                const dist = Math.hypot(dx, dy);

                if (gravityPull > 0 && dist > 5) {
                    const force = gravityPull / Math.max(dist, 30.0);
                    pt.vx += (dx / dist) * force * dt * 800;
                    pt.vy += (dy / dist) * force * dt * 800;
                    pt.vx += (-dy / dist) * force * dt * 200;
                    pt.vy += (dx / dist) * force * dt * 200;
                } else if (explosionForce > 0 && phaseLocalTime < 0.1) {
                    if (dist > 2) {
                        const blast = explosionForce * (Math.random() * 0.8 + 0.6);
                        pt.vx = (dx / dist) * -blast + (Math.random() - 0.5) * 160;
                        pt.vy = (dy / dist) * -blast + (Math.random() - 0.5) * 160;
                    }
                } else {
                    pt.vy += -15.0 * dt;
                    pt.vx *= 0.98;
                }

                pt.vx *= (1.0 - 0.5 * dt);
                pt.vy *= (1.0 - 0.5 * dt);

                pt.x += pt.vx * dt;
                pt.y += pt.vy * dt;

                if (pt.x < -30) pt.x = W + 20;
                else if (pt.x > W + 30) pt.x = -20;
                if (pt.y < -30) pt.y = H + 20;
                else if (pt.y > H + 30) pt.y = -20;

                // Draw ember glow
                const alpha = (Math.sin(performance.now() * 0.005 + pt.alphaPhase) + 1.0) * 0.5 * 0.8 + 0.2;
                ctx.beginPath();
                ctx.arc(pt.x, pt.y, pt.size * 2, 0, Math.PI * 2);
                ctx.fillStyle = `rgba(${pt.r}, ${pt.g}, ${pt.b}, ${alpha * 0.35})`;
                ctx.fill();

                ctx.beginPath();
                ctx.arc(pt.x, pt.y, pt.size, 0, Math.PI * 2);
                ctx.fillStyle = `rgba(${Math.min(255, pt.r + 40)}, ${Math.min(255, pt.g + 40)}, ${pt.b}, ${alpha})`;
                ctx.fill();
            });

            // Apply Camera Transform Matrix
            ctx.save();
            ctx.translate(cx + simSwayX + shakeOffsetX, cy + shakeOffsetY);
            ctx.scale(simCurrentZoom, simCurrentZoom);
            ctx.translate(-cx, -cy);

            // Draw Sprite Frame
            if (activeSprite) {
                const scale = g.sprite_scale || 3.5;
                const sw = (activeSprite.width || 288) * scale;
                const sh = (activeSprite.height || 128) * scale;
                const sx = cx - sw / 2;
                const sy = cy - sh / 2;

                ctx.save();
                ctx.globalAlpha = spriteAlpha;

                if (flipHorizontal) {
                    ctx.translate(cx, cy);
                    ctx.scale(-1, 1);
                    ctx.drawImage(activeSprite, -sw / 2, -sh / 2, sw, sh);
                } else {
                    ctx.drawImage(activeSprite, sx, sy, sw, sh);
                }
                ctx.restore();
            } else {
                // Fallback placeholder if still loading
                ctx.save();
                ctx.fillStyle = "rgba(139, 92, 246, 0.4)";
                ctx.beginPath();
                ctx.arc(cx, cy, 60, 0, Math.PI * 2);
                ctx.fill();
                ctx.restore();
            }

            ctx.restore();

            // Screen Flash Overlay
            if (flashAlpha > 0.01) {
                ctx.fillStyle = `rgba(${flashColor[0]}, ${flashColor[1]}, ${flashColor[2]}, ${Math.min(1.0, flashAlpha)})`;
                ctx.fillRect(0, 0, W, H);
            }

            // Update Visual Labels / HUD Telemetry
            if (isHudVisible) {
                const phaseEl = document.getElementById('hudPhaseName');
                if (phaseEl) {
                    phaseEl.innerText = `PHASE: ${currentPhase.label.toUpperCase()}`;
                    phaseEl.style.color = currentPhase.color;
                }
                const timeEl = document.getElementById('hudTime');
                if (timeEl) timeEl.innerText = `Time: ${previewTime.toFixed(2)}s / ${totalDur.toFixed(2)}s`;
                const frameEl = document.getElementById('hudFrame');
                if (frameEl) frameEl.innerText = `Frame: ${frameIdx + 1} / ${totalPhaseFrames}`;
                const zoomEl = document.getElementById('hudZoom');
                if (zoomEl) zoomEl.innerText = `Zoom: ${simCurrentZoom.toFixed(2)}x (Target: ${targetZoom.toFixed(2)}x)`;
                const shakeEl = document.getElementById('hudShake');
                if (shakeEl) shakeEl.innerText = `Shake: ${simShakeAmp.toFixed(1)} px (${shakeFreq} Hz)`;
                const swayEl = document.getElementById('hudSway');
                if (swayEl) swayEl.innerText = `Sway Offset: ${simSwayX.toFixed(1)} px`;
                const vortexEl = document.getElementById('hudVortex');
                if (vortexEl) vortexEl.innerText = `Vortex Force: ${gravityPull.toFixed(1)}`;
                const flashEl = document.getElementById('hudFlash');
                if (flashEl) flashEl.innerText = `Screen Flash: Alpha ${(flashAlpha * 255).toFixed(0)}`;
                const partEl = document.getElementById('hudParticles');
                if (partEl) partEl.innerText = `Active Embers: ${simParticles.length}`;
                const audioEl = document.getElementById('hudAudio');
                if (audioEl) audioEl.innerText = `Active: ${sfxList.join(', ') || 'None'}`;
            }
        }

        window.onload = init;
    </script>
</body>
</html>
"""


class CutsceneEditorHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        if path == "/" or path == "/index.html":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML_PAGE.encode("utf-8"))
            return

        elif path == "/api/config":
            cfg = load_config()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(cfg).encode("utf-8"))
            return

        elif path == "/api/sounds":
            sfx = get_available_sounds()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(sfx).encode("utf-8"))
            return

        elif path == "/api/sprites":
            sprites = get_available_sprites()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(sprites).encode("utf-8"))
            return

        elif path == "/api/frames":
            dir_path = query.get("dir", [""])[0]
            frames = get_frames_in_dir(dir_path)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(frames).encode("utf-8"))
            return

        elif path.startswith("/sprites/"):
            rel = urllib.parse.unquote(path[9:])
            full_path = os.path.join(BASE_DIR, rel)
            if os.path.exists(full_path) and os.path.isfile(full_path):
                self.send_response(200)
                if full_path.lower().endswith(".png"):
                    self.send_header("Content-Type", "image/png")
                elif full_path.lower().endswith((".jpg", ".jpeg")):
                    self.send_header("Content-Type", "image/jpeg")
                elif full_path.lower().endswith(".webp"):
                    self.send_header("Content-Type", "image/webp")
                else:
                    self.send_header("Content-Type", "application/octet-stream")
                self.end_headers()
                with open(full_path, "rb") as f:
                    self.wfile.write(f.read())
                return
            else:
                self.send_error(404, "Sprite file not found")
                return

        elif path.startswith("/audio/"):
            rel = urllib.parse.unquote(path[7:])
            full_path = os.path.join(BASE_DIR, rel)
            if os.path.exists(full_path) and os.path.isfile(full_path):
                self.send_response(200)
                if full_path.endswith(".wav"):
                    self.send_header("Content-Type", "audio/wav")
                elif full_path.endswith(".mp3"):
                    self.send_header("Content-Type", "audio/mpeg")
                elif full_path.endswith(".ogg"):
                    self.send_header("Content-Type", "audio/ogg")
                else:
                    self.send_header("Content-Type", "application/octet-stream")
                self.end_headers()
                with open(full_path, "rb") as f:
                    self.wfile.write(f.read())
                return
            else:
                self.send_error(404, "Audio file not found")
                return

        super().do_GET()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path == "/api/config":
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)
            try:
                cfg = json.loads(body.decode("utf-8"))
                ok = save_config(cfg)
                if ok:
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps({"status": "ok"}).encode("utf-8"))
                else:
                    self.send_response(500)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps({"status": "error", "error": "Failed to write file"}).encode("utf-8"))
            except Exception as e:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "error": str(e)}).encode("utf-8"))
            return

        elif path == "/api/reset":
            ok = save_config(DEFAULT_CONFIG)
            if ok:
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"status": "ok", "config": DEFAULT_CONFIG}).encode("utf-8"))
            else:
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "error": "Failed to write default file"}).encode("utf-8"))
            return

        self.send_error(404, "Unknown endpoint")


def run_server(port: int = 8088):
    for p in range(port, port + 20):
        try:
            httpd = socketserver.TCPServer(("", p), CutsceneEditorHandler)
            print(f"\n=======================================================")
            print(f"🎬 Transformation Cutscene Studio GUI Plugin Launched!")
            print(f"🌐 Access Web Interface: http://localhost:{p}")
            print(f"=======================================================\n")
            Timer(1.0, lambda: webbrowser.open(f"http://localhost:{p}")).start()
            try:
                httpd.serve_forever()
            except KeyboardInterrupt:
                print("\n[Cutscene Editor] Shutting down...")
                httpd.server_close()
            return
        except OSError:
            continue
    print(f"[Cutscene Editor] Error: Could not bind to ports {port}-{port+20}")


if __name__ == "__main__":
    run_server()
