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
            "peak_shake_amplitude": 9.5,
            "peak_shake_frequency": 22.0,
            "flash_color": [180, 20, 20],
            "flash_peak_alpha": 220,
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


def get_all_audio_assets() -> list[str]:
    """Scan the entire assets/ directory recursively for all audio files (like audio_mixer_editor)."""
    audio_files = []
    assets_dir = os.path.join(BASE_DIR, "assets")
    if os.path.exists(assets_dir):
        for root, dirs, files in os.walk(assets_dir):
            for file in files:
                if file.lower().endswith((".mp3", ".wav", ".ogg", ".flac", ".m4a")):
                    full_path = os.path.join(root, file)
                    rel_path = os.path.relpath(full_path, BASE_DIR).replace("\\", "/")
                    audio_files.append(rel_path)
    return sorted(audio_files)


def get_available_sounds() -> dict:
    """Extract registered sounds + all raw audio assets across assets folder."""
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
                    sounds[name] = path.replace("\\", "/")
        except Exception:
            pass

    master_path = os.path.join(BASE_DIR, "game_data", "master_audio_config.json")
    if os.path.exists(master_path):
        try:
            with open(master_path, "r") as f:
                data = json.load(f)
                if "sounds" in data:
                    for k, v in data["sounds"].items():
                        p = v if isinstance(v, str) else v.get("path", "")
                        if k not in sounds and p:
                            sounds[k] = p.replace("\\", "/")
        except Exception:
            pass

    # Include all 800+ raw audio assets from assets folder
    for rel_path in get_all_audio_assets():
        if rel_path not in sounds:
            sounds[rel_path] = rel_path

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

        .sfx-phase-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
            gap: 1rem;
        }

        .sfx-add-row {
            display: flex;
            gap: 0.4rem;
            margin-top: 0.6rem;
            align-items: center;
            width: 100%;
        }

        .sfx-add-row select {
            flex: 1 1 auto;
            min-width: 0;
            width: 0;
            text-overflow: ellipsis;
            overflow: hidden;
            white-space: nowrap;
            padding: 0.45rem 0.5rem;
            font-size: 0.8rem;
        }

        .sfx-add-row .btn {
            flex-shrink: 0;
            white-space: nowrap;
        }

        /* Audio Modal / Drawer */
        .audio-modal-backdrop {
            position: fixed;
            inset: 0;
            background: rgba(0, 0, 0, 0.82);
            backdrop-filter: blur(12px);
            z-index: 1000;
            display: none;
            justify-content: center;
            align-items: center;
            padding: 1.5rem;
        }

        .audio-modal-backdrop.active {
            display: flex;
        }

        .audio-modal {
            background: #0f172a;
            border: 1px solid var(--panel-border);
            border-radius: 12px;
            width: 100%;
            max-width: 960px;
            max-height: 85vh;
            display: flex;
            flex-direction: column;
            box-shadow: 0 20px 50px rgba(0, 0, 0, 0.8);
            overflow: hidden;
        }

        .audio-modal-header {
            padding: 1rem 1.25rem;
            border-bottom: 1px solid var(--panel-border);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .audio-modal-body {
            padding: 1.25rem;
            overflow-y: auto;
            flex: 1;
            display: flex;
            flex-direction: column;
            gap: 1rem;
        }

        .audio-asset-item {
            background: rgba(255, 255, 255, 0.03);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 8px;
            padding: 0.6rem 0.9rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 0.75rem;
            transition: all 0.15s;
        }

        .audio-asset-item:hover {
            background: rgba(255, 255, 255, 0.07);
            border-color: var(--accent-cyan);
        }

        .audio-asset-info {
            display: flex;
            flex-direction: column;
            gap: 0.15rem;
            overflow: hidden;
        }

        .audio-asset-name {
            font-size: 0.85rem;
            font-weight: 600;
            color: var(--text-main);
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }

        .audio-asset-path {
            font-size: 0.7rem;
            color: #64748b;
            font-family: 'JetBrains Mono', monospace;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }

        .audio-asset-actions {
            display: flex;
            align-items: center;
            gap: 0.5rem;
            flex-shrink: 0;
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

        .control-desc {
            font-size: 0.72rem;
            color: #64748b;
            margin-top: -0.2rem;
            margin-bottom: 0.2rem;
            line-height: 1.3;
        }

        /* ─── FILMSTRIP FRAME PICKER ─── */
        .filmstrip-card {
            background: rgba(13, 17, 23, 0.7);
            border: 1px solid rgba(239, 68, 68, 0.3);
            border-radius: 10px;
            padding: 1rem;
            margin-top: 0.5rem;
        }

        .filmstrip-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 0.75rem;
        }

        .filmstrip-scroller {
            display: flex;
            gap: 0.75rem;
            overflow-x: auto;
            padding: 0.5rem 0.25rem 1rem 0.25rem;
            scrollbar-width: thin;
        }

        .filmstrip-scroller::-webkit-scrollbar {
            height: 6px;
        }

        .filmstrip-scroller::-webkit-scrollbar-thumb {
            background: rgba(255, 255, 255, 0.2);
            border-radius: 3px;
        }

        .frame-thumb-card {
            flex: 0 0 110px;
            background: rgba(15, 23, 42, 0.85);
            border: 2px solid rgba(255, 255, 255, 0.1);
            border-radius: 8px;
            padding: 0.5rem;
            cursor: pointer;
            transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
            display: flex;
            flex-direction: column;
            align-items: center;
            position: relative;
            user-select: none;
        }

        .frame-thumb-card:hover {
            transform: translateY(-4px);
            border-color: var(--accent-cyan);
            box-shadow: 0 6px 20px rgba(6, 182, 212, 0.3);
        }

        .frame-thumb-card.border-flash {
            border-color: #ef4444;
            background: rgba(239, 68, 68, 0.15);
            box-shadow: 0 0 16px rgba(239, 68, 68, 0.5);
        }

        .frame-thumb-card.border-zoom {
            border-color: #a855f7;
            background: rgba(168, 85, 247, 0.15);
            box-shadow: 0 0 16px rgba(168, 85, 247, 0.5);
        }

        .frame-thumb-card.border-flash-zoom {
            border-color: #f59e0b;
            background: linear-gradient(135deg, rgba(239, 68, 68, 0.2), rgba(168, 85, 247, 0.2));
            box-shadow: 0 0 20px rgba(245, 158, 11, 0.6);
        }

        .frame-thumb-img-wrapper {
            width: 100%;
            height: 60px;
            display: flex;
            align-items: center;
            justify-content: center;
            overflow: hidden;
            margin-bottom: 0.4rem;
        }

        .frame-thumb-img-wrapper img {
            max-width: 100%;
            max-height: 100%;
            image-rendering: pixelated;
        }

        .frame-thumb-meta {
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 0.2rem;
            width: 100%;
        }

        .frame-num {
            font-size: 0.72rem;
            font-family: 'JetBrains Mono', monospace;
            font-weight: 700;
            color: var(--text-main);
        }

        .badge-flash {
            background: #ef4444;
            color: #fff;
            font-size: 0.6rem;
            font-weight: 800;
            padding: 0.1rem 0.35rem;
            border-radius: 3px;
            text-transform: uppercase;
            box-shadow: 0 0 8px rgba(239, 68, 68, 0.6);
        }

        .badge-zoom {
            background: #a855f7;
            color: #fff;
            font-size: 0.6rem;
            font-weight: 800;
            padding: 0.1rem 0.35rem;
            border-radius: 3px;
            text-transform: uppercase;
            box-shadow: 0 0 8px rgba(168, 85, 247, 0.6);
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
        /* ─── FL STUDIO / PRO TOOLS STYLE DAW AUDIO TIMELINE MIXER ─── */
        .daw-container {
            display: flex;
            flex-direction: column;
            background: #090d16;
            border: 1px solid #1e293b;
            border-radius: 12px;
            overflow: hidden;
            user-select: none;
            box-shadow: 0 16px 36px rgba(0,0,0,0.6), inset 0 1px 0 rgba(255,255,255,0.05);
        }

        .daw-transport {
            display: flex;
            align-items: center;
            gap: 0.75rem;
            padding: 0.65rem 1rem;
            background: linear-gradient(180deg, #131b2e 0%, #0c1220 100%);
            border-bottom: 1px solid #1e293b;
            flex-wrap: wrap;
        }

        .daw-transport-btn-group {
            display: flex;
            align-items: center;
            gap: 0.35rem;
            background: rgba(0,0,0,0.4);
            padding: 3px;
            border-radius: 8px;
            border: 1px solid rgba(255,255,255,0.06);
        }

        .daw-transport .btn {
            padding: 0.38rem 0.75rem;
            font-size: 0.78rem;
            font-weight: 600;
            border-radius: 6px;
        }

        .daw-time-display {
            font-family: 'JetBrains Mono', monospace;
            font-size: 1.15rem;
            font-weight: 700;
            color: #38bdf8;
            background: #040810;
            padding: 0.35rem 0.9rem;
            border-radius: 8px;
            border: 1px solid rgba(56,189,248,0.3);
            min-width: 230px;
            text-align: center;
            box-shadow: inset 0 2px 6px rgba(0,0,0,0.8), 0 0 12px rgba(56,189,248,0.15);
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 0.5rem;
        }

        .daw-time-phase-badge {
            font-size: 0.65rem;
            padding: 0.1rem 0.4rem;
            border-radius: 4px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }

        .daw-transport-controls {
            display: flex;
            align-items: center;
            gap: 0.75rem;
            margin-left: auto;
            flex-wrap: wrap;
        }

        .daw-transport-tool {
            display: flex;
            align-items: center;
            gap: 0.35rem;
            font-size: 0.75rem;
            color: #94a3b8;
        }

        .daw-transport-tool select, .daw-transport-tool input {
            background: #0f172a;
            border: 1px solid #334155;
            color: #f8fafc;
            border-radius: 6px;
            padding: 0.25rem 0.5rem;
            font-size: 0.75rem;
        }

        .daw-body {
            position: relative;
            overflow-x: auto;
            overflow-y: auto;
            max-height: 560px;
            background: #080c14;
        }

        .daw-scroll-area {
            position: relative;
            min-width: 100%;
        }

        /* Ruler */
        .daw-ruler {
            display: flex;
            position: sticky;
            top: 0;
            z-index: 25;
            background: #0f172a;
            border-bottom: 2px solid #334155;
            height: 48px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.5);
        }

        .daw-ruler-track-corner {
            width: 170px;
            min-width: 170px;
            position: sticky;
            left: 0;
            z-index: 30;
            background: #0b1120;
            border-right: 1px solid #1e293b;
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 0 0.75rem;
            font-size: 0.75rem;
            font-weight: 700;
            color: #94a3b8;
        }

        .daw-ruler-timeline {
            flex: 1;
            position: relative;
            height: 100%;
            cursor: pointer;
        }

        .daw-ruler-phase-block {
            position: absolute;
            top: 0;
            height: 100%;
            display: flex;
            flex-direction: column;
            justify-content: center;
            padding: 0 6px;
            border-right: 1px solid rgba(255,255,255,0.12);
            overflow: hidden;
            box-sizing: border-box;
            background: rgba(255,255,255,0.02);
            transition: background 0.15s;
        }

        .daw-ruler-phase-block:hover {
            background: rgba(255,255,255,0.06);
        }

        .daw-ruler-phase-name {
            font-size: 0.68rem;
            font-weight: 800;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }

        .daw-ruler-time-range {
            font-size: 0.58rem;
            font-family: 'JetBrains Mono', monospace;
            color: #64748b;
        }

        .daw-ruler-tick {
            position: absolute;
            bottom: 0;
            height: 10px;
            width: 1px;
            background: rgba(255,255,255,0.25);
        }

        .daw-ruler-tick.sub {
            height: 5px;
            background: rgba(255,255,255,0.1);
        }

        .daw-ruler-tick-label {
            position: absolute;
            bottom: 12px;
            transform: translateX(-50%);
            font-size: 0.58rem;
            font-family: 'JetBrains Mono', monospace;
            color: #64748b;
        }

        /* Freeform Playlist Tracks */
        .daw-tracks-container {
            position: relative;
        }

        .daw-track-row {
            display: flex;
            border-bottom: 1px solid #1e293b;
            position: relative;
            min-height: 54px;
        }

        .daw-track-row:hover {
            background: rgba(255,255,255,0.015);
        }

        .daw-track-header-box {
            width: 170px;
            min-width: 170px;
            background: #0c1322;
            border-right: 1px solid #1e293b;
            position: sticky;
            left: 0;
            z-index: 15;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            padding: 0.5rem 0.75rem;
            box-sizing: border-box;
        }

        .daw-track-header-top {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 0.35rem;
        }

        .daw-track-title {
            font-size: 0.78rem;
            font-weight: 700;
            display: flex;
            align-items: center;
            gap: 0.35rem;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            color: #f8fafc;
        }

        .daw-track-header-bottom {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-top: 0.3rem;
        }

        .daw-track-cue-count {
            font-size: 0.65rem;
            color: #64748b;
            font-family: 'JetBrains Mono', monospace;
        }

        .daw-track-actions {
            display: flex;
            align-items: center;
            gap: 0.25rem;
        }

        .daw-btn-icon-sm {
            padding: 0.15rem 0.35rem;
            font-size: 0.65rem;
            border-radius: 4px;
            border: 1px solid #334155;
            background: rgba(0,0,0,0.3);
            color: #94a3b8;
            cursor: pointer;
            font-weight: 700;
        }

        .daw-btn-icon-sm:hover {
            background: rgba(255,255,255,0.1);
            color: #f8fafc;
        }

        .daw-btn-icon-sm.active-mute {
            background: #ef4444;
            color: #fff;
            border-color: #dc2626;
        }

        .daw-btn-icon-sm.active-solo {
            background: #eab308;
            color: #000;
            border-color: #ca8a04;
        }

        .daw-track-lane-area {
            flex: 1;
            position: relative;
            height: 54px;
            display: flex;
            align-items: center;
        }

        /* Phase column guides stretching vertically down all tracks */
        .daw-phase-column-backdrop {
            position: absolute;
            top: 0;
            bottom: 0;
            opacity: 0.04;
            pointer-events: none;
            border-right: 1px dashed rgba(255,255,255,0.06);
        }

        .daw-phase-column-backdrop.active-playback {
            opacity: 0.12;
        }

        .daw-grid-line {
            position: absolute;
            top: 0;
            bottom: 0;
            width: 1px;
            background: rgba(255,255,255,0.04);
            pointer-events: none;
        }

        .daw-grid-line.major {
            background: rgba(255,255,255,0.08);
        }

        /* ─── CLIP CARD (FL Studio Capsule) ─── */
        .daw-clip {
            position: absolute;
            height: 42px;
            border-radius: 6px;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            padding: 3px 6px;
            cursor: grab;
            overflow: hidden;
            box-sizing: border-box;
            border: 1px solid rgba(255,255,255,0.25);
            background: linear-gradient(180deg, rgba(30,41,59,0.85) 0%, rgba(15,23,42,0.95) 100%);
            box-shadow: 0 4px 10px rgba(0,0,0,0.4), inset 0 1px 0 rgba(255,255,255,0.2);
            transition: box-shadow 0.1s, border-color 0.1s;
            z-index: 5;
        }

        .daw-clip:active {
            cursor: grabbing;
        }

        .daw-clip:hover {
            box-shadow: 0 0 14px rgba(56,189,248,0.3), inset 0 1px 0 rgba(255,255,255,0.3);
            border-color: rgba(255,255,255,0.5);
            z-index: 8;
        }

        .daw-clip.selected {
            border: 2px solid #38bdf8 !important;
            box-shadow: 0 0 20px rgba(56,189,248,0.55), inset 0 0 12px rgba(56,189,248,0.25) !important;
            z-index: 10;
        }

        .daw-clip.muted {
            opacity: 0.35 !important;
            filter: grayscale(0.8);
        }

        .daw-clip-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            font-size: 0.66rem;
            font-weight: 700;
            color: #f8fafc;
            gap: 0.35rem;
            pointer-events: none;
            text-shadow: 0 1px 2px rgba(0,0,0,0.8);
        }

        .daw-clip-title {
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            max-width: 140px;
        }

        .daw-clip-tags {
            display: flex;
            align-items: center;
            gap: 0.2rem;
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.58rem;
        }

        .daw-clip-tag {
            background: rgba(0,0,0,0.5);
            padding: 0.05rem 0.25rem;
            border-radius: 3px;
            color: #cbd5e1;
        }

        .daw-clip-waveform {
            position: absolute;
            left: 0;
            right: 0;
            bottom: 2px;
            height: 20px;
            pointer-events: none;
            opacity: 0.35;
        }

        /* Fade ramps overlays */
        .daw-fade-in-overlay {
            position: absolute;
            top: 0;
            bottom: 0;
            left: 0;
            background: linear-gradient(to right, rgba(0,0,0,0.85) 0%, rgba(0,0,0,0) 100%);
            pointer-events: none;
            border-top-left-radius: 5px;
            border-bottom-left-radius: 5px;
        }

        .daw-fade-out-overlay {
            position: absolute;
            top: 0;
            bottom: 0;
            right: 0;
            background: linear-gradient(to left, rgba(0,0,0,0.85) 0%, rgba(0,0,0,0) 100%);
            pointer-events: none;
            border-top-right-radius: 5px;
            border-bottom-right-radius: 5px;
        }

        /* Fade handles (top-left & top-right) */
        .daw-fade-handle {
            position: absolute;
            top: 0;
            width: 10px;
            height: 10px;
            background: #fff;
            border-radius: 50%;
            cursor: ew-resize;
            box-shadow: 0 0 6px rgba(0,0,0,0.8);
            z-index: 12;
            opacity: 0;
            transition: opacity 0.15s, transform 0.15s;
        }

        .daw-clip:hover .daw-fade-handle, .daw-clip.selected .daw-fade-handle {
            opacity: 0.85;
        }

        .daw-fade-handle:hover {
            opacity: 1 !important;
            transform: scale(1.3);
            background: #38bdf8;
        }

        .daw-fade-handle.fade-in {
            left: 0;
            border-top-left-radius: 5px;
        }

        .daw-fade-handle.fade-out {
            right: 0;
            border-top-right-radius: 5px;
        }

        /* Trim handles */
        .daw-trim-handle {
            position: absolute;
            top: 0;
            bottom: 0;
            width: 7px;
            cursor: col-resize;
            z-index: 11;
            opacity: 0;
            transition: opacity 0.15s, background 0.15s;
        }

        .daw-clip:hover .daw-trim-handle, .daw-clip.selected .daw-trim-handle {
            opacity: 0.6;
        }

        .daw-trim-handle:hover {
            opacity: 1 !important;
            background: rgba(56,189,248,0.5) !important;
        }

        .daw-trim-handle.trim-left {
            left: 0;
            border-radius: 5px 0 0 5px;
            background: rgba(255,255,255,0.2);
        }

        .daw-trim-handle.trim-right {
            right: 0;
            border-radius: 0 5px 5px 0;
            background: rgba(255,255,255,0.2);
        }

        /* Playhead */
        .daw-playhead {
            position: absolute;
            top: 0;
            bottom: 0;
            width: 2px;
            background: #ef4444;
            z-index: 40;
            pointer-events: none;
            box-shadow: 0 0 10px rgba(239,68,68,0.8);
        }

        .daw-playhead-cap {
            position: absolute;
            top: 0;
            left: -7px;
            width: 16px;
            height: 16px;
            background: #ef4444;
            clip-path: polygon(0% 0%, 100% 0%, 50% 100%);
        }

        /* Floating HUD Drag Tooltip */
        .daw-drag-tooltip {
            position: fixed;
            pointer-events: none;
            background: #0f172a;
            color: #38bdf8;
            padding: 0.35rem 0.75rem;
            border-radius: 6px;
            font-size: 0.75rem;
            font-family: 'JetBrains Mono', monospace;
            font-weight: 700;
            border: 1px solid #38bdf8;
            box-shadow: 0 8px 24px rgba(0,0,0,0.8);
            z-index: 9999;
            transform: translate(-50%, -120%);
            display: none;
        }

        /* ─── DAW INSPECTOR PANEL ─── */
        .daw-inspector {
            display: flex;
            align-items: center;
            gap: 1.25rem;
            padding: 0.85rem 1.25rem;
            background: linear-gradient(180deg, #0c1220 0%, #080d16 100%);
            border-top: 1px solid #1e293b;
            flex-wrap: wrap;
            min-height: 64px;
        }

        .daw-inspector-badge-group {
            display: flex;
            flex-direction: column;
            gap: 0.2rem;
            max-width: 220px;
        }

        .daw-inspector-title {
            font-size: 0.85rem;
            font-weight: 800;
            color: #38bdf8;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }

        .daw-inspector-path {
            font-size: 0.65rem;
            color: #64748b;
            font-family: 'JetBrains Mono', monospace;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }

        .daw-inspector-controls-grid {
            display: flex;
            align-items: center;
            gap: 0.85rem;
            flex-wrap: wrap;
        }

        .daw-param-box {
            display: flex;
            flex-direction: column;
            gap: 0.25rem;
        }

        .daw-param-label {
            font-size: 0.65rem;
            font-weight: 700;
            color: #94a3b8;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            display: flex;
            justify-content: space-between;
        }

        .daw-param-input-row {
            display: flex;
            align-items: center;
            gap: 0.35rem;
        }

        .daw-param-input-row input[type="number"] {
            width: 70px;
            background: #040810;
            border: 1px solid #334155;
            color: #f8fafc;
            border-radius: 5px;
            padding: 0.25rem 0.4rem;
            font-size: 0.75rem;
            font-family: 'JetBrains Mono', monospace;
        }

        .daw-param-input-row input[type="range"] {
            width: 85px;
            accent-color: #38bdf8;
        }

        .daw-param-val-badge {
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.7rem;
            color: #38bdf8;
            min-width: 40px;
            font-weight: 700;
        }

        .daw-inspector-actions {
            display: flex;
            align-items: center;
            gap: 0.4rem;
            margin-left: auto;
            flex-wrap: wrap;
        }

        /* Quick Add Modal */
        .daw-modal-backdrop {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0,0,0,0.8);
            backdrop-filter: blur(4px);
            display: none;
            align-items: center;
            justify-content: center;
            z-index: 10000;
        }

        .daw-modal-backdrop.active {
            display: flex;
        }

        .daw-modal-box {
            background: #0f172a;
            border: 1px solid #334155;
            border-radius: 12px;
            width: 90%;
            max-width: 600px;
            max-height: 80vh;
            display: flex;
            flex-direction: column;
            overflow: hidden;
            box-shadow: 0 25px 50px -12px rgba(0,0,0,0.85);
        }

        .daw-modal-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 1rem 1.25rem;
            background: #1e293b;
            border-bottom: 1px solid #334155;
        }

        .daw-modal-title {
            font-size: 1rem;
            font-weight: 700;
            color: #f8fafc;
        }

        .daw-modal-body {
            padding: 1rem 1.25rem;
            overflow-y: auto;
            display: flex;
            flex-direction: column;
            gap: 0.75rem;
        }

        .daw-modal-sound-list {
            display: flex;
            flex-direction: column;
            gap: 0.35rem;
            max-height: 360px;
            overflow-y: auto;
        }

        .daw-modal-sound-item {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 0.5rem 0.75rem;
            background: rgba(255,255,255,0.03);
            border: 1px solid rgba(255,255,255,0.06);
            border-radius: 6px;
            transition: background 0.15s, border-color 0.15s;
        }

        .daw-modal-sound-item:hover {
            background: rgba(56,189,248,0.08);
            border-color: rgba(56,189,248,0.4);
        }

        .daw-modal-preview-btn.active-preview {
            background: rgba(56, 189, 248, 0.25) !important;
            border-color: #38bdf8 !important;
            color: #38bdf8 !important;
            box-shadow: 0 0 10px rgba(56, 189, 248, 0.4);
        }

        .daw-phase-backdrop.active-playback {
            opacity: 0.12;
        }

        .daw-grid-line {
            position: absolute;
            top: 0;
            bottom: 0;
            width: 1px;
            background: rgba(255,255,255,0.04);
            pointer-events: none;
        }

        .daw-grid-line.major {
            background: rgba(255,255,255,0.08);
        }

        /* ─── CLIP CARD (FL Studio Capsule) ─── */
        .daw-clip {
            position: absolute;
            height: 38px;
            border-radius: 6px;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            padding: 2px 6px;
            cursor: grab;
            overflow: hidden;
            box-sizing: border-box;
            border: 1px solid rgba(255,255,255,0.25);
            background: linear-gradient(180deg, rgba(30,41,59,0.85) 0%, rgba(15,23,42,0.95) 100%);
            box-shadow: 0 4px 10px rgba(0,0,0,0.4), inset 0 1px 0 rgba(255,255,255,0.2);
            transition: box-shadow 0.1s, border-color 0.1s;
            z-index: 5;
        }

        .daw-clip:active {
            cursor: grabbing;
        }

        .daw-clip:hover {
            box-shadow: 0 0 14px rgba(56,189,248,0.3), inset 0 1px 0 rgba(255,255,255,0.3);
            border-color: rgba(255,255,255,0.5);
            z-index: 8;
        }

        .daw-clip.selected {
            border: 2px solid #38bdf8 !important;
            box-shadow: 0 0 20px rgba(56,189,248,0.55), inset 0 0 12px rgba(56,189,248,0.25) !important;
            z-index: 10;
        }

        .daw-clip.muted {
            opacity: 0.35 !important;
            filter: grayscale(0.8);
        }

        .daw-clip-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            font-size: 0.66rem;
            font-weight: 700;
            color: #f8fafc;
            gap: 0.35rem;
            pointer-events: none;
            text-shadow: 0 1px 2px rgba(0,0,0,0.8);
        }

        .daw-clip-title {
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            max-width: 140px;
        }

        .daw-clip-tags {
            display: flex;
            align-items: center;
            gap: 0.2rem;
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.58rem;
        }

        .daw-clip-tag {
            background: rgba(0,0,0,0.5);
            padding: 0.05rem 0.25rem;
            border-radius: 3px;
            color: #cbd5e1;
        }

        /* Waveform simulation inside clip */
        .daw-clip-waveform {
            position: absolute;
            left: 0;
            right: 0;
            bottom: 2px;
            height: 18px;
            pointer-events: none;
            opacity: 0.35;
        }

        /* Fade ramps overlays */
        .daw-fade-in-overlay {
            position: absolute;
            top: 0;
            bottom: 0;
            left: 0;
            background: linear-gradient(to right, rgba(0,0,0,0.85) 0%, rgba(0,0,0,0) 100%);
            pointer-events: none;
            border-top-left-radius: 5px;
            border-bottom-left-radius: 5px;
        }

        .daw-fade-out-overlay {
            position: absolute;
            top: 0;
            bottom: 0;
            right: 0;
            background: linear-gradient(to left, rgba(0,0,0,0.85) 0%, rgba(0,0,0,0) 100%);
            pointer-events: none;
            border-top-right-radius: 5px;
            border-bottom-right-radius: 5px;
        }

        /* Fade handles (top-left & top-right) */
        .daw-fade-handle {
            position: absolute;
            top: 0;
            width: 10px;
            height: 10px;
            background: #fff;
            border-radius: 50%;
            cursor: ew-resize;
            box-shadow: 0 0 6px rgba(0,0,0,0.8);
            z-index: 12;
            opacity: 0;
            transition: opacity 0.15s, transform 0.15s;
        }

        .daw-clip:hover .daw-fade-handle, .daw-clip.selected .daw-fade-handle {
            opacity: 0.85;
        }

        .daw-fade-handle:hover {
            opacity: 1 !important;
            transform: scale(1.3);
            background: #38bdf8;
        }

        .daw-fade-handle.fade-in {
            left: 0;
            border-top-left-radius: 5px;
        }

        .daw-fade-handle.fade-out {
            right: 0;
            border-top-right-radius: 5px;
        }

        /* Trim handles */
        .daw-trim-handle {
            position: absolute;
            top: 0;
            bottom: 0;
            width: 7px;
            cursor: col-resize;
            z-index: 11;
            opacity: 0;
            transition: opacity 0.15s, background 0.15s;
        }

        .daw-clip:hover .daw-trim-handle, .daw-clip.selected .daw-trim-handle {
            opacity: 0.6;
        }

        .daw-trim-handle:hover {
            opacity: 1 !important;
            background: rgba(56,189,248,0.5) !important;
        }

        .daw-trim-handle.trim-left {
            left: 0;
            border-radius: 5px 0 0 5px;
            background: rgba(255,255,255,0.2);
        }

        .daw-trim-handle.trim-right {
            right: 0;
            border-radius: 0 5px 5px 0;
            background: rgba(255,255,255,0.2);
        }

        /* Playhead */
        .daw-playhead {
            position: absolute;
            top: 0;
            bottom: 0;
            width: 2px;
            background: #ef4444;
            z-index: 40;
            pointer-events: none;
            box-shadow: 0 0 10px rgba(239,68,68,0.8);
        }

        .daw-playhead-cap {
            position: absolute;
            top: 0;
            left: -7px;
            width: 16px;
            height: 16px;
            background: #ef4444;
            clip-path: polygon(0% 0%, 100% 0%, 50% 100%);
        }

        /* Floating HUD Drag Tooltip */
        .daw-drag-tooltip {
            position: fixed;
            pointer-events: none;
            background: #0f172a;
            color: #38bdf8;
            padding: 0.35rem 0.75rem;
            border-radius: 6px;
            font-size: 0.75rem;
            font-family: 'JetBrains Mono', monospace;
            font-weight: 700;
            border: 1px solid #38bdf8;
            box-shadow: 0 8px 24px rgba(0,0,0,0.8);
            z-index: 9999;
            transform: translate(-50%, -120%);
            display: none;
        }

        /* ─── DAW INSPECTOR PANEL ─── */
        .daw-inspector {
            display: flex;
            align-items: center;
            gap: 1.25rem;
            padding: 0.85rem 1.25rem;
            background: linear-gradient(180deg, #0c1220 0%, #080d16 100%);
            border-top: 1px solid #1e293b;
            flex-wrap: wrap;
            min-height: 64px;
        }

        .daw-inspector-badge-group {
            display: flex;
            flex-direction: column;
            gap: 0.2rem;
            max-width: 220px;
        }

        .daw-inspector-title {
            font-size: 0.85rem;
            font-weight: 800;
            color: #38bdf8;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }

        .daw-inspector-path {
            font-size: 0.65rem;
            color: #64748b;
            font-family: 'JetBrains Mono', monospace;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }

        .daw-inspector-controls-grid {
            display: flex;
            align-items: center;
            gap: 0.85rem;
            flex-wrap: wrap;
        }

        .daw-param-box {
            display: flex;
            flex-direction: column;
            gap: 0.25rem;
        }

        .daw-param-label {
            font-size: 0.65rem;
            font-weight: 700;
            color: #94a3b8;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            display: flex;
            justify-content: space-between;
        }

        .daw-param-input-row {
            display: flex;
            align-items: center;
            gap: 0.35rem;
        }

        .daw-param-input-row input[type="number"] {
            width: 70px;
            background: #040810;
            border: 1px solid #334155;
            color: #f8fafc;
            border-radius: 5px;
            padding: 0.25rem 0.4rem;
            font-size: 0.75rem;
            font-family: 'JetBrains Mono', monospace;
        }

        .daw-param-input-row input[type="range"] {
            width: 85px;
            accent-color: #38bdf8;
        }

        .daw-param-val-badge {
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.7rem;
            color: #38bdf8;
            min-width: 40px;
            font-weight: 700;
        }

        .daw-inspector-actions {
            display: flex;
            align-items: center;
            gap: 0.4rem;
            margin-left: auto;
            flex-wrap: wrap;
        }

        /* Quick Add Modal */
        .daw-modal-backdrop {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0,0,0,0.8);
            backdrop-filter: blur(4px);
            display: none;
            align-items: center;
            justify-content: center;
            z-index: 10000;
        }

        .daw-modal-backdrop.active {
            display: flex;
        }

        .daw-modal-box {
            background: #0f172a;
            border: 1px solid #334155;
            border-radius: 12px;
            width: 90%;
            max-width: 600px;
            max-height: 80vh;
            display: flex;
            flex-direction: column;
            overflow: hidden;
            box-shadow: 0 25px 50px -12px rgba(0,0,0,0.85);
        }

        .daw-modal-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 1rem 1.25rem;
            background: #1e293b;
            border-bottom: 1px solid #334155;
        }

        .daw-modal-title {
            font-size: 1rem;
            font-weight: 700;
            color: #f8fafc;
        }

        .daw-modal-body {
            padding: 1rem 1.25rem;
            overflow-y: auto;
            display: flex;
            flex-direction: column;
            gap: 0.75rem;
        }

        .daw-modal-sound-list {
            display: flex;
            flex-direction: column;
            gap: 0.35rem;
            max-height: 360px;
            overflow-y: auto;
        }

        .daw-modal-sound-item {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 0.5rem 0.75rem;
            background: rgba(255,255,255,0.03);
            border: 1px solid rgba(255,255,255,0.06);
            border-radius: 6px;
            cursor: pointer;
            transition: background 0.15s, border-color 0.15s;
        }

        .daw-modal-sound-item:hover {
            background: rgba(56,189,248,0.1);
            border-color: #38bdf8;
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
            <button class="tab-btn" onclick="switchTab('timeline'); renderDAWTimeline();">🎛️ Audio Timeline</button>
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
                        <button class="btn" style="padding:0.4rem 0.9rem; background:linear-gradient(135deg, #ef4444, #b91c1c); color:#fff; font-weight:700; border:none; border-radius:6px; cursor:pointer;" onclick="setFlashToCurrentPreviewFrame()" id="setFlashBtn" title="Set the Red Flash trigger to the frame currently visible on canvas">⚡ Set Tentacle Flash to Current Frame</button>
                    </div>

                    <div class="scrubber-container">
                        <span style="font-size:0.8rem; font-family:'JetBrains Mono';" id="scrubTimeDisplay">0.00s</span>
                        <input type="range" min="0" max="10" step="0.01" value="0" class="scrubber-slider" id="timelineScrubber" oninput="onScrub(this.value)">
                        <select id="speedSelect" onchange="changePlaybackSpeed(this.value)" style="padding:0.25rem 0.5rem; font-size:0.75rem;">
                            <option value="0.25">0.25x (Slow Motion)</option>
                            <option value="0.5">0.5x Speed</option>
                            <option value="1.0" selected>1.0x (Normal Speed)</option>
                            <option value="1.5">1.5x Speed</option>
                            <option value="2.0">2.0x Speed</option>
                        </select>
                    </div>

                    <div class="phase-jump-row">
                        <button class="phase-jump-btn" onclick="jumpToPhase('fade_in')">Fade In</button>
                        <button class="phase-jump-btn" onclick="jumpToPhase('orb_collapse')">Dark Ball</button>
                        <button class="phase-jump-btn" onclick="jumpToPhase('orb_loop')">Ball Pulse</button>
                        <button class="phase-jump-btn" onclick="jumpToPhase('demon_burst')">Demon Burst</button>
                        <button class="phase-jump-btn" onclick="jumpToPhase('attack_left')">Slash Left</button>
                        <button class="phase-jump-btn" onclick="jumpToPhase('attack_right')">Slash Right</button>
                        <button class="phase-jump-btn" onclick="jumpToPhase('special_tentacles')">Tentacles ('F')</button>
                        <button class="phase-jump-btn" onclick="jumpToPhase('revert')">Back to Human</button>
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

        <!-- TAB 1: Timing & Speeds -->
        <div class="tab-panel active" id="tab-timing">
            <div class="card">
                <div class="card-header">
                    <div class="card-title">⏱️ Phase Durations & Animation Speeds (Pacing)</div>
                    <div class="card-badge">TIMING & PACING</div>
                </div>
                <div class="grid-2">
                    <div class="control-group">
                        <div class="control-label">
                            <span>🌑 Opening Black Screen Delay</span>
                            <span class="control-val" id="val_fade_in_duration">1.5s</span>
                        </div>
                        <div class="control-desc">How long the scene stays in darkness before the transformation begins.</div>
                        <input type="range" min="0.2" max="3.0" step="0.05" id="in_fade_in_duration" oninput="updateVal('fade_in_duration', this.value, 's')">
                    </div>

                    <div class="control-group">
                        <div class="control-label">
                            <span>🌀 Body Collapsing into Dark Ball Speed</span>
                            <span class="control-val" id="val_orb_frame_duration">0.11s</span>
                        </div>
                        <div class="control-desc">Time per frame as player curls and shrinks into the dark orb singularity. Higher = slower.</div>
                        <input type="range" min="0.03" max="0.25" step="0.005" id="in_orb_frame_duration" oninput="updateVal('orb_frame_duration', this.value, 's')">
                    </div>

                    <div class="control-group">
                        <div class="control-label">
                            <span>🔮 Dark Ball Pulsation Rhythm Speed</span>
                            <span class="control-val" id="val_orb_loop_frame_duration">0.09s</span>
                        </div>
                        <div class="control-desc">How rapidly the dark orb breathes and pulsates with unstable energy.</div>
                        <input type="range" min="0.03" max="0.20" step="0.005" id="in_orb_loop_frame_duration" oninput="updateVal('orb_loop_frame_duration', this.value, 's')">
                    </div>

                    <div class="control-group">
                        <div class="control-label">
                            <span>🔄 Dark Ball Pulse Repeat Count</span>
                            <span class="control-val" id="val_orb_loop_cycles">3x</span>
                        </div>
                        <div class="control-desc">How many full pulse cycles the orb performs before exploding into demon form.</div>
                        <input type="range" min="1" max="8" step="1" id="in_orb_loop_cycles" oninput="updateVal('orb_loop_cycles', this.value, 'x')">
                    </div>

                    <div class="control-group">
                        <div class="control-label">
                            <span>💥 Demon Eruption Blast Speed</span>
                            <span class="control-val" id="val_demon_burst_frame_duration">0.035s</span>
                        </div>
                        <div class="control-desc">Rapid explosion frame timing when the demon bursts out of the ball.</div>
                        <input type="range" min="0.015" max="0.10" step="0.005" id="in_demon_burst_frame_duration" oninput="updateVal('demon_burst_frame_duration', this.value, 's')">
                    </div>

                    <div class="control-group">
                        <div class="control-label">
                            <span>⚔️ Demon Dual Slash Speed</span>
                            <span class="control-val" id="val_attack_frame_duration">0.055s</span>
                        </div>
                        <div class="control-desc">Speed of Left and Right sword swings.</div>
                        <input type="range" min="0.02" max="0.12" step="0.005" id="in_attack_frame_duration" oninput="updateVal('attack_frame_duration', this.value, 's')">
                    </div>

                    <div class="control-group">
                        <div class="control-label">
                            <span>🐙 Tentacles Reach-Out & Snap Speed</span>
                            <span class="control-val" id="val_special_frame_duration">0.075s</span>
                        </div>
                        <div class="control-desc">Pacing of tentacles shooting outward and retracting into demon body.</div>
                        <input type="range" min="0.03" max="0.15" step="0.005" id="in_special_frame_duration" oninput="updateVal('special_frame_duration', this.value, 's')">
                    </div>

                    <div class="control-group">
                        <div class="control-label">
                            <span>👤 Turning Back to Human Speed</span>
                            <span class="control-val" id="val_revert_frame_duration">0.07s</span>
                        </div>
                        <div class="control-desc">Frame speed as the demon armor dissolves back into human form.</div>
                        <input type="range" min="0.03" max="0.15" step="0.005" id="in_revert_frame_duration" oninput="updateVal('revert_frame_duration', this.value, 's')">
                    </div>

                    <div class="control-group">
                        <div class="control-label">
                            <span>🧘 Post-Transformation Rest Pause</span>
                            <span class="control-val" id="val_post_pause">0.6s</span>
                        </div>
                        <div class="control-desc">Breathing room delay before transitioning into gameplay.</div>
                        <input type="range" min="0.1" max="2.0" step="0.05" id="in_post_pause" oninput="updateVal('post_pause', this.value, 's')">
                    </div>

                    <div class="control-group">
                        <div class="control-label">
                            <span>✨ Phase Transition Smoothing (Crossfade)</span>
                            <span class="control-val" id="val_crossfade_duration">0.30s</span>
                        </div>
                        <div class="control-desc">Cross-blend smoothness between sprite sequences to avoid sudden snapping.</div>
                        <input type="range" min="0.05" max="0.80" step="0.05" id="in_crossfade_duration" oninput="updateVal('crossfade_duration', this.value, 's')">
                    </div>
                </div>
            </div>
        </div>

        <!-- TAB 2: Camera Rig -->
        <div class="tab-panel" id="tab-camera">
            <div class="card">
                <div class="card-header">
                    <div class="card-title">📷 Dynamic Cinematic Camera Rig & Shake Effects</div>
                    <div class="card-badge">CAMERA RIG</div>
                </div>
                <div class="grid-2">
                    <div class="control-group">
                        <div class="control-label">
                            <span>🔍 Dark Ball Camera Zoom Depth</span>
                            <span class="control-val" id="val_orb_camera_zoom">1.45x</span>
                        </div>
                        <div class="control-desc">How close the camera punches in when the character collapses into the dark ball.</div>
                        <input type="range" min="1.0" max="2.2" step="0.05" id="in_orb_camera_zoom" oninput="updateVal('orb_camera_zoom', this.value, 'x')">
                    </div>

                    <div class="control-group">
                        <div class="control-label">
                            <span>🎥 Camera Zoom-In Smoothness</span>
                            <span class="control-val" id="val_orb_camera_zoom_speed">1.2</span>
                        </div>
                        <div class="control-desc">Lerp speed for camera zooming in.</div>
                        <input type="range" min="0.2" max="4.0" step="0.1" id="in_orb_camera_zoom_speed" oninput="updateVal('orb_camera_zoom_speed', this.value)">
                    </div>

                    <div class="control-group">
                        <div class="control-label">
                            <span>📳 Portal Vibration Rumble (Gentle Ground Shake)</span>
                            <span class="control-val" id="val_orb_shake_amp">3.5 px</span>
                        </div>
                        <div class="control-desc">Soft, low-frequency screen vibration as the portal singularity charges up.</div>
                        <input type="range" min="0.0" max="15.0" step="0.5" id="in_orb_shake_amp" oninput="updateVal('orb_shake_amp', this.value, ' px')">
                    </div>

                    <div class="control-group">
                        <div class="control-label">
                            <span>🌋 Demon Eruption Screen Shockwave</span>
                            <span class="control-val" id="val_demon_shake_amp">8.0 px</span>
                        </div>
                        <div class="control-desc">Violent camera impact shudder when the demon armor breaks free.</div>
                        <input type="range" min="0.0" max="25.0" step="0.5" id="in_demon_shake_amp" oninput="updateVal('demon_shake_amp', this.value, ' px')">
                    </div>

                    <div class="control-group">
                        <div class="control-label">
                            <span>↔️ Slash Follow Camera (Swing Sway Offset)</span>
                            <span class="control-val" id="val_attack_sway_x">55 px</span>
                        </div>
                        <div class="control-desc">Camera slides in the direction of the demon's sword strikes.</div>
                        <input type="range" min="10" max="150" step="5" id="in_attack_sway_x" oninput="updateVal('attack_sway_x', this.value, ' px')">
                    </div>

                    <div class="control-group">
                        <div class="control-label">
                            <span>🚀 Slash Camera Sway Recovery Speed</span>
                            <span class="control-val" id="val_attack_sway_speed">4.0</span>
                        </div>
                        <div class="control-desc">How rapidly the camera glides back to center after a slash.</div>
                        <input type="range" min="1.0" max="10.0" step="0.5" id="in_attack_sway_speed" oninput="updateVal('attack_sway_speed', this.value)">
                    </div>

                    <div class="control-group">
                        <div class="control-label">
                            <span>🔭 Tentacles Climax Close-Up Zoom Depth</span>
                            <span class="control-val" id="val_tentacle_zoom_max">1.50x</span>
                        </div>
                        <div class="control-desc">Peak zoom close-up factor when tentacles spread across screen.</div>
                        <input type="range" min="1.0" max="2.2" step="0.05" id="in_tentacle_zoom_max" oninput="updateVal('tentacle_zoom_max', this.value, 'x')">
                    </div>

                    <div class="control-group">
                        <div class="control-label">
                            <span>🎯 Tentacles Climax Close-Up Frame</span>
                            <span class="control-val" id="val_tentacle_peak_frame">Frame 11</span>
                        </div>
                        <div class="control-desc">Exact sprite frame when the camera reaches maximum close-up zoom.</div>
                        <input type="range" min="1" max="19" step="1" id="in_tentacle_peak_frame" oninput="updateVal('tentacle_peak_frame', this.value, 'Frame ')">
                    </div>

                    <div class="control-group">
                        <div class="control-label">
                            <span>🌪️ Tentacles Peak Violent Earthquake Rumble</span>
                            <span class="control-val" id="val_tentacle_shake_amp">9.5 px</span>
                        </div>
                        <div class="control-desc">Intense screen shudder amplitude when tentacles strike full extension.</div>
                        <input type="range" min="0.0" max="25.0" step="0.5" id="in_tentacle_shake_amp" oninput="updateVal('tentacle_shake_amp', this.value, ' px')">
                    </div>

                    <div class="control-group">
                        <div class="control-label">
                            <span>⚡ Tentacles Vibration Shiver Speed</span>
                            <span class="control-val" id="val_tentacle_shake_freq">22 Hz</span>
                        </div>
                        <div class="control-desc">Frequency / speed of the violent shudder rumble.</div>
                        <input type="range" min="5.0" max="35.0" step="1.0" id="in_tentacle_shake_freq" oninput="updateVal('tentacle_shake_freq', this.value, ' Hz')">
                    </div>
                </div>
            </div>
        </div>

        <!-- TAB 3: Audio & SFX -->
        <div class="tab-panel" id="tab-audio">
            <div class="card">
                <div class="card-header">
                    <div>
                        <div class="card-title">🔊 Sound Effects & Audio Cues Per Phase</div>
                        <div class="control-desc" style="margin-top:0.25rem;">
                            Choose from <strong>all 807+ audio files in the assets folder</strong> or registered game cues. Filter by folder, search, or open the visual browser.
                        </div>
                    </div>
                    <div style="display:flex; gap:0.5rem; align-items:center;">
                        <button class="btn btn-primary" style="padding:0.35rem 0.8rem; font-size:0.75rem;" onclick="openAudioModal()">📂 Open Audio Asset Browser (807 sounds)</button>
                    </div>
                </div>

                <!-- Global Audio Search / Folder Filter Bar -->
                <div style="display:flex; gap:0.75rem; flex-wrap:wrap; background:rgba(0,0,0,0.3); padding:0.75rem; border-radius:8px; border:1px solid var(--panel-border);">
                    <div style="flex:1; min-width:200px;">
                        <div class="control-desc" style="margin-bottom:0.25rem; font-weight:600; color:var(--text-main);">📁 Filter by Asset Folder</div>
                        <select id="sfxFolderFilter" onchange="filterSFXOptions()" style="width:100%; padding:0.4rem; font-size:0.8rem;">
                            <option value="">All Audio Folders (807 sounds)</option>
                        </select>
                    </div>
                    <div style="flex:1.5; min-width:260px;">
                        <div class="control-desc" style="margin-bottom:0.25rem; font-weight:600; color:var(--text-main);">🔍 Search Sound Name / Path</div>
                        <input type="text" id="sfxSearchInput" placeholder="Filter sounds (e.g. roar, slash, smash, magic, bell, scream)..." oninput="filterSFXOptions()" style="width:100%; padding:0.4rem; font-size:0.8rem;">
                    </div>
                </div>

                <div class="sfx-phase-grid" id="sfxPhaseCards">
                    <!-- Rendered dynamically -->
                </div>
            </div>
        </div>

        <!-- TAB 3.5: FL STUDIO / PRO TOOLS STYLE DAW AUDIO TIMELINE MIXER -->
        <div class="tab-panel" id="tab-timeline">
            <div class="daw-container">
                <!-- Transport Bar -->
                <div class="daw-transport">
                    <div class="daw-transport-btn-group">
                        <button class="btn btn-primary" id="dawPlayBtn" onclick="dawTogglePlay()">▶ Play</button>
                        <button class="btn btn-secondary" onclick="dawStop()">⏹ Stop</button>
                        <button class="btn btn-secondary" id="dawLoopBtn" onclick="dawToggleLoop()" title="Toggle loop playback">🔁 Loop</button>
                        <button class="btn btn-secondary" onclick="dawSplitSelectedClip()" title="Split / Slice selected clip at playhead (S key)">✂️ Split (S)</button>
                    </div>

                    <div class="daw-time-display" id="dawTimeDisplay">
                        <span id="dawTimeClock">0:00.000 / 0:12.495</span>
                        <span class="daw-time-phase-badge" id="dawTimePhaseBadge" style="background:#3b82f620; color:#3b82f6; border:1px solid #3b82f6;">Fade In</span>
                    </div>

                    <div class="daw-transport-controls">
                        <div class="daw-transport-tool">
                            <label title="Magnet / Snap to grid when moving and trimming clips">🧲 Snap:</label>
                            <select id="dawSnapSelect" onchange="dawSnapSec = parseFloat(this.value)">
                                <option value="0">Off (Free)</option>
                                <option value="0.02">0.02s (Sub-frame)</option>
                                <option value="0.05" selected>0.05s (Standard)</option>
                                <option value="0.10">0.10s (Frame)</option>
                                <option value="0.25">0.25s (Quarter)</option>
                                <option value="0.50">0.50s (Half)</option>
                            </select>
                        </div>

                        <div class="daw-transport-tool">
                            <label>Speed:</label>
                            <select id="dawSpeedSelect" onchange="dawSpeed = parseFloat(this.value); dawUpdatePlaybackRate();">
                                <option value="0.25">0.25x</option>
                                <option value="0.5">0.5x</option>
                                <option value="1.0" selected>1.0x</option>
                                <option value="1.5">1.5x</option>
                                <option value="2.0">2.0x</option>
                            </select>
                        </div>

                        <div class="daw-transport-tool">
                            <label>Zoom:</label>
                            <input type="range" min="30" max="220" value="90" id="dawZoomSlider" oninput="dawSetZoom(parseInt(this.value))">
                            <span id="dawZoomLabel" style="font-family:'JetBrains Mono',monospace; font-size:0.7rem; color:#64748b; min-width:45px;">90px/s</span>
                        </div>

                        <div class="daw-transport-tool" style="gap:0.2rem;">
                            <button class="daw-btn-icon-sm" onclick="dawFitAllZoom()" title="Fit entire cutscene to screen (No scrolling needed!)" style="background:rgba(56,189,248,0.2); color:#38bdf8; border-color:#38bdf8;">🔍 Fit Screen</button>
                            <button class="daw-btn-icon-sm" onclick="dawSetZoom(60)" title="Zoom Out">−</button>
                            <button class="daw-btn-icon-sm" onclick="dawSetZoom(90)" title="Default 100%">100%</button>
                            <button class="daw-btn-icon-sm" onclick="dawSetZoom(160)" title="Zoom In">+</button>
                        </div>

                        <div class="daw-transport-tool" style="margin-left:0.5rem; border-left:1px solid #334155; padding-left:0.75rem;">
                            <label title="Master Timeline Volume">🔊 Master:</label>
                            <input type="range" min="0" max="1" step="0.01" value="1.0" id="dawMasterVolSlider" oninput="dawSetMasterVolume(parseFloat(this.value))" style="width:70px;">
                            <span id="dawMasterVolLabel" style="font-family:'JetBrains Mono',monospace; font-size:0.7rem; color:#38bdf8; min-width:32px;">100%</span>
                        </div>

                        <button class="btn btn-primary" style="padding:0.3rem 0.75rem; font-size:0.75rem; margin-left:0.5rem;" onclick="dawOpenAddSoundModal(null)">+ Add Sound Cue</button>
                    </div>
                </div>

                <!-- Timeline Body -->
                <div class="daw-body" id="dawBody">
                    <div class="daw-scroll-area" id="dawScrollArea">
                        <!-- Ruler -->
                        <div class="daw-ruler" id="dawRuler">
                            <div class="daw-ruler-track-corner">
                                <span>PLAYLIST TRACKS</span>
                                <button class="daw-btn-icon-sm" style="color:#38bdf8;" onclick="dawAddNewTrack()" title="Add new audio track">+ Track</button>
                            </div>
                            <div class="daw-ruler-timeline" id="dawRulerTimeline" onmousedown="dawRulerClick(event)">
                                <!-- Rendered dynamically -->
                            </div>
                        </div>

                        <!-- Tracks Container -->
                        <div class="daw-tracks-container" id="dawTracksContainer">
                            <!-- Rendered dynamically -->
                        </div>

                        <!-- Playhead -->
                        <div class="daw-playhead" id="dawPlayhead" style="left:170px;">
                            <div class="daw-playhead-cap"></div>
                        </div>
                    </div>
                </div>

                <!-- Floating HUD Drag Tooltip -->
                <div class="daw-drag-tooltip" id="dawDragTooltip">Offset: 0.00s</div>

                <!-- Clip Inspector -->
                <div class="daw-inspector" id="dawInspector">
                    <span style="font-size:0.8rem; color:#64748b; font-style:italic;">Click any clip on the timeline to inspect, fade, tune volume, pitch & stereo pan</span>
                </div>
            </div>

            <!-- Quick Add Sound Modal -->
            <div class="daw-modal-backdrop" id="dawAddSoundModal">
                <div class="daw-modal-box">
                    <div class="daw-modal-header">
                        <div class="daw-modal-title" id="dawAddModalTitle">📂 Add Sound Cue to Timeline</div>
                        <button class="btn btn-secondary" style="padding:0.2rem 0.5rem;" onclick="dawCloseAddSoundModal()">✕</button>
                    </div>
                    <div class="daw-modal-body">
                        <div style="display:flex; gap:0.5rem;">
                            <select id="dawModalFolderSelect" onchange="dawFilterAddModalList()" style="flex:1; padding:0.4rem; background:#040810; border:1px solid #334155; color:#fff; border-radius:6px; font-size:0.78rem;">
                                <option value="">All Audio Folders (807 sounds)</option>
                            </select>
                            <input type="text" id="dawModalSearchInput" placeholder="Search roar, slash, magic, fireball..." oninput="dawFilterAddModalList()" style="flex:1.5; padding:0.4rem; background:#040810; border:1px solid #334155; color:#fff; border-radius:6px; font-size:0.78rem;">
                        </div>
                        <div class="daw-modal-sound-list" id="dawModalSoundList">
                            <!-- Populated dynamically -->
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- TAB 4: VFX & Magic -->
        <div class="tab-panel" id="tab-effects">
            <!-- Visual Frame Filmstrip Card for Tentacles Flash Placement -->
            <div class="filmstrip-card">
                <div class="filmstrip-header">
                    <div>
                        <div style="font-size:0.95rem; font-weight:700; color:var(--text-main); display:flex; align-items:center; gap:0.5rem;">
                            ⚡ Visual Frame Filmstrip — Tentacles Strike Flash & Climax Timing
                        </div>
                        <div class="control-desc" style="margin-top:0.2rem;">
                            <strong>Click any frame below</strong> to instantly set which frame triggers the blinding <strong>Red Flash</strong> and <strong>Camera Climax</strong>. Look at the thumbnails to pick the exact visual moment!
                        </div>
                    </div>
                    <button class="btn btn-secondary" style="padding:0.3rem 0.7rem; font-size:0.75rem;" onclick="renderTentacleFilmstrip()">🔄 Refresh Filmstrip</button>
                </div>
                <div class="filmstrip-scroller" id="tentacleFilmstrip">
                    <!-- 19 frame thumbnails rendered dynamically with click-to-set -->
                </div>
            </div>

            <div class="card">
                <div class="card-header">
                    <div class="card-title">✨ Gravity Vortex, Blast Force & Screen Flashes</div>
                    <div class="card-badge">VFX & FLASHES</div>
                </div>
                <div class="grid-2">
                    <div class="control-group">
                        <div class="control-label">
                            <span>⚡ Tentacle Strike Red Flash Frame</span>
                            <span class="control-val" id="val_tentacle_flash_frame">Frame 11</span>
                        </div>
                        <div class="control-desc">The exact frame (1 to 19) when the blinding Red Flash fires. You can also click the filmstrip above or use the button in Live Preview!</div>
                        <input type="range" min="1" max="19" step="1" id="in_tentacle_flash_frame" oninput="updateVal('tentacle_flash_frame', this.value, 'Frame ')">
                    </div>

                    <div class="control-group">
                        <div class="control-label">
                            <span>💡 Tentacles Red Flash Brightness (Intensity)</span>
                            <span class="control-val" id="val_tentacle_flash_alpha">220 / 255</span>
                        </div>
                        <div class="control-desc">How bright and opaque the screen flash is (255 = full blinding cover).</div>
                        <input type="range" min="0" max="255" step="5" id="in_tentacle_flash_alpha" oninput="updateVal('tentacle_flash_alpha', this.value, ' / 255')">
                    </div>

                    <div class="control-group">
                        <div class="control-label">
                            <span>🎨 Tentacles Flash Burst Color</span>
                        </div>
                        <div class="control-desc">Color tint of the special tentacle shockwave flash.</div>
                        <div class="color-row">
                            <input type="color" id="in_tentacle_flash_color" onchange="updateColor('tentacle_flash_color', this.value)">
                            <span class="control-val" id="val_tentacle_flash_color">#b41414</span>
                        </div>
                    </div>

                    <div class="control-group">
                        <div class="control-label">
                            <span>✨ Ambient Glowing Embers Density</span>
                            <span class="control-val" id="val_particle_count">40 particles</span>
                        </div>
                        <div class="control-desc">Total count of dark ember particles drifting in the vortex.</div>
                        <input type="range" min="10" max="150" step="5" id="in_particle_count" oninput="updateVal('particle_count', this.value, ' particles')">
                    </div>

                    <div class="control-group">
                        <div class="control-label">
                            <span>🧲 Black Hole Gravity Inward Pull Strength</span>
                            <span class="control-val" id="val_gravity_strength">8.0</span>
                        </div>
                        <div class="control-desc">How forcefully floating embers get sucked inward toward the character.</div>
                        <input type="range" min="0.0" max="30.0" step="1.0" id="in_gravity_strength" oninput="updateVal('gravity_strength', this.value)">
                    </div>

                    <div class="control-group">
                        <div class="control-label">
                            <span>💣 Demon Burst Explosion Blast Kick</span>
                            <span class="control-val" id="val_explosion_strength">450.0</span>
                        </div>
                        <div class="control-desc">How violently ember particles fly outward upon demon eruption.</div>
                        <input type="range" min="100.0" max="1200.0" step="25.0" id="in_explosion_strength" oninput="updateVal('explosion_strength', this.value)">
                    </div>

                    <div class="control-group">
                        <div class="control-label">
                            <span>🤍 Demon Burst White Flash Color</span>
                        </div>
                        <div class="control-desc">Initial instantaneous white explosion blast color.</div>
                        <div class="color-row">
                            <input type="color" id="in_flash_color_white" onchange="updateColor('flash_color_white', this.value)">
                            <span class="control-val" id="val_flash_color_white">#ffffff</span>
                        </div>
                    </div>

                    <div class="control-group">
                        <div class="control-label">
                            <span>🩸 Demon Shock Red Flash Color</span>
                        </div>
                        <div class="control-desc">Secondary red shockwave color after the white blast.</div>
                        <div class="color-row">
                            <input type="color" id="in_flash_color_red" onchange="updateColor('flash_color_red', this.value)">
                            <span class="control-val" id="val_flash_color_red">#b41414</span>
                        </div>
                    </div>

                    <div class="control-group">
                        <div class="control-label">
                            <span>💓 Human Form Recovery Heartbeat Pulses</span>
                            <span class="control-val" id="val_flash_count">4 flashes</span>
                        </div>
                        <div class="control-desc">Number of rhythmic red heartbeat screen pulses during human recovery.</div>
                        <input type="range" min="1" max="10" step="1" id="in_flash_count" oninput="updateVal('flash_count', this.value, ' flashes')">
                    </div>

                    <div class="control-group">
                        <div class="control-label">
                            <span>🎨 Recovery Heartbeat Flash Color</span>
                        </div>
                        <div class="control-desc">Color of the heartbeat pulses during revert.</div>
                        <div class="color-row">
                            <input type="color" id="in_revert_flash_color" onchange="updateColor('revert_flash_color', this.value)">
                            <span class="control-val" id="val_revert_flash_color">#c80f0f</span>
                        </div>
                    </div>

                    <div class="control-group">
                        <div class="control-label">
                            <span>🌌 Scene Void Backdrop Color</span>
                        </div>
                        <div class="control-desc">Background dark color behind the character and particles.</div>
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

    <!-- Audio Asset Browser Modal -->
    <div class="audio-modal-backdrop" id="audioModalBackdrop" onclick="if(event.target===this) closeAudioModal()">
        <div class="audio-modal">
            <div class="audio-modal-header">
                <div style="display:flex; align-items:center; gap:0.5rem;">
                    <span style="font-size:1.1rem; font-weight:700; color:var(--text-main);">📂 Master Audio Asset Library Browser</span>
                    <span class="card-badge" id="modalAudioCount">807 sounds</span>
                </div>
                <button class="btn btn-secondary" style="padding:0.3rem 0.7rem; font-size:0.8rem;" onclick="closeAudioModal()">✕ Close</button>
            </div>
            <div style="padding:1rem 1.25rem 0.5rem 1.25rem; display:flex; gap:0.75rem; flex-wrap:wrap; border-bottom:1px solid var(--panel-border); background:rgba(0,0,0,0.2);">
                <div style="flex:1; min-width:200px;">
                    <select id="modalFolderFilter" onchange="filterModalAudioList()" style="width:100%; padding:0.4rem; font-size:0.8rem;">
                        <option value="">All Folders</option>
                    </select>
                </div>
                <div style="flex:1.5; min-width:240px;">
                    <input type="text" id="modalSearchInput" placeholder="Filter by filename (e.g. roar, smash, scream)..." oninput="filterModalAudioList()" style="width:100%; padding:0.4rem; font-size:0.8rem;">
                </div>
                <div style="display:flex; align-items:center; gap:0.5rem;">
                    <span style="font-size:0.75rem; color:var(--text-muted);">Target Phase:</span>
                    <select id="modalTargetPhase" style="padding:0.35rem 0.6rem; font-size:0.8rem;">
                        <option value="fade_in">Fade In</option>
                        <option value="orb_collapse">Dark Ball</option>
                        <option value="orb_loop">Ball Pulse</option>
                        <option value="demon_burst">Demon Burst</option>
                        <option value="attack_left">Slash Left</option>
                        <option value="attack_right">Slash Right</option>
                        <option value="special_tentacles" selected>Tentacles ('F')</option>
                        <option value="revert">Back to Human</option>
                    </select>
                </div>
            </div>
            <div class="audio-modal-body" id="modalAudioList">
                <!-- Dynamically populated sound asset items -->
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
            if (tabId === 'timeline') {
                renderDAWTimeline();
                setTimeout(dawFitAllZoom, 50);
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
            setRange("in_tentacle_shake_amp", "val_tentacle_shake_amp", p.special_tentacles?.peak_shake_amplitude !== undefined ? p.special_tentacles.peak_shake_amplitude : 9.5, " px");
            setRange("in_tentacle_shake_freq", "val_tentacle_shake_freq", p.special_tentacles?.peak_shake_frequency !== undefined ? p.special_tentacles.peak_shake_frequency : 22.0, " Hz");

            // VFX
            setRange("in_tentacle_flash_frame", "val_tentacle_flash_frame", p.special_tentacles?.flash_trigger_frame || 11, "Frame ");
            setRange("in_tentacle_flash_alpha", "val_tentacle_flash_alpha", p.special_tentacles?.flash_peak_alpha !== undefined ? p.special_tentacles.flash_peak_alpha : 220, " / 255");
            setRange("in_particle_count", "val_particle_count", g.particle_count || 40, " particles");
            setRange("in_gravity_strength", "val_gravity_strength", p.orb_collapse?.gravity_strength || 8.0, "");
            setRange("in_explosion_strength", "val_explosion_strength", p.demon_burst?.explosion_strength || 450.0, "");
            setRange("in_flash_count", "val_flash_count", p.revert?.flash_count || 4, " flashes");

            // Colors
            setColor("in_flash_color_white", "val_flash_color_white", p.demon_burst?.flash_color_white || [255, 255, 255]);
            setColor("in_flash_color_red", "val_flash_color_red", p.demon_burst?.flash_color_red || [180, 20, 20]);
            setColor("in_tentacle_flash_color", "val_tentacle_flash_color", p.special_tentacles?.flash_color || [180, 20, 20]);
            setColor("in_revert_flash_color", "val_revert_flash_color", p.revert?.flash_color || [200, 15, 15]);
            setColor("in_bg_color", "val_bg_color", g.background_color || [12, 10, 20]);

            // Assets
            setRange("in_sprite_scale", "val_sprite_scale", g.sprite_scale || 3.5, "x");

            // Filmstrip render
            renderTentacleFilmstrip();
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
                case "tentacle_peak_frame":
                    p.special_tentacles.zoom_peak_frame = parseInt(num);
                    renderTentacleFilmstrip();
                    break;
                case "tentacle_flash_frame":
                    p.special_tentacles.flash_trigger_frame = parseInt(num);
                    renderTentacleFilmstrip();
                    break;
                case "tentacle_shake_amp": p.special_tentacles.peak_shake_amplitude = num; break;
                case "tentacle_shake_freq": p.special_tentacles.peak_shake_frequency = num; break;
                case "tentacle_flash_alpha": p.special_tentacles.flash_peak_alpha = parseInt(num); break;

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

        function renderTentacleFilmstrip() {
            const container = document.getElementById("tentacleFilmstrip");
            if (!container) return;
            const p = currentConfig.phases?.special_tentacles || {};
            const flashFrame = p.flash_trigger_frame !== undefined ? p.flash_trigger_frame : 11;
            const zoomFrame = p.zoom_peak_frame !== undefined ? p.zoom_peak_frame : 11;

            let html = '';
            for (let i = 1; i <= 19; i++) {
                const isFlash = (i === flashFrame);
                const isZoom = (i === zoomFrame);
                let borderClass = '';
                if (isFlash && isZoom) borderClass = 'border-flash-zoom';
                else if (isFlash) borderClass = 'border-flash';
                else if (isZoom) borderClass = 'border-zoom';

                html += `
                    <div class="frame-thumb-card ${borderClass}" onclick="selectTentacleFlashFrame(${i})" title="Click to trigger Red Flash at Frame ${i}">
                        <div class="frame-thumb-img-wrapper">
                            <img src="/sprites/assets/shadow_warrior/e_sp_atk/e_sp_atk_${i}.png" alt="Frame ${i}" loading="lazy" />
                        </div>
                        <div class="frame-thumb-meta">
                            <span class="frame-num">Frame ${i}</span>
                            ${isFlash ? '<span class="badge-flash">⚡ FLASH</span>' : ''}
                            ${isZoom ? '<span class="badge-zoom">🔍 ZOOM</span>' : ''}
                        </div>
                    </div>
                `;
            }
            container.innerHTML = html;
        }

        function selectTentacleFlashFrame(frameNum) {
            if (!currentConfig.phases) return;
            if (!currentConfig.phases.special_tentacles) currentConfig.phases.special_tentacles = {};
            currentConfig.phases.special_tentacles.flash_trigger_frame = frameNum;
            
            // Sync form slider & label
            setRange("in_tentacle_flash_frame", "val_tentacle_flash_frame", frameNum, "Frame ");
            renderTentacleFilmstrip();
            renderTimeline();
            showToast(`⚡ Tentacles Red Flash trigger set to Frame ${frameNum}!`);
            addLog('VFX', `Selected Tentacle Red Flash on Frame ${frameNum}`);
        }

        function setFlashToCurrentPreviewFrame() {
            const durations = getPhaseDurations();
            const p = currentConfig.phases || {};
            const fDur = p.special_tentacles?.frame_duration || 0.075;
            
            const startTime = (durations.fade_in || 0) + (durations.orb_collapse || 0) + (durations.orb_loop || 0) + (durations.demon_burst || 0) + (durations.attack_left || 0) + (durations.attack_right || 0);
            const endTime = startTime + (durations.special_tentacles || 0);
            
            let frameNum = 11;
            if (previewTime >= startTime && previewTime <= endTime) {
                const localT = previewTime - startTime;
                const spFrames = loadedFramesCache.special_tentacles || [];
                const total = Math.max(1, spFrames.length || 19);
                frameNum = Math.min(total, Math.max(1, Math.floor(localT / fDur) + 1));
            } else {
                jumpToPhase('special_tentacles');
                frameNum = 11;
            }
            
            selectTentacleFlashFrame(frameNum);
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
                case "tentacle_flash_color": p.special_tentacles.flash_color = rgb; break;
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

        let currentAudioPreviewElement = null;

        function populateFolderDropdowns() {
            const folderCounts = {};
            Object.keys(availableSounds).forEach(key => {
                const p = availableSounds[key] || key;
                const parts = p.split('/');
                if (parts.length > 1) {
                    parts.pop();
                    const folder = parts.join('/');
                    folderCounts[folder] = (folderCounts[folder] || 0) + 1;
                } else {
                    folderCounts['(registered)'] = (folderCounts['(registered)'] || 0) + 1;
                }
            });

            const sortedFolders = Object.keys(folderCounts).sort();
            const sfxSelect = document.getElementById('sfxFolderFilter');
            const modalSelect = document.getElementById('modalFolderFilter');

            const total = Object.keys(availableSounds).length;
            const optionsHtml = `<option value="">All Folders (${total} sounds)</option>` + 
                sortedFolders.map(f => `<option value="${f}">${f} (${folderCounts[f]})</option>`).join('');

            if (sfxSelect) sfxSelect.innerHTML = optionsHtml;
            if (modalSelect) modalSelect.innerHTML = optionsHtml;

            const modalCount = document.getElementById('modalAudioCount');
            if (modalCount) modalCount.innerText = `${total} sounds`;
        }

        function getFilteredSoundList(folderFilter, searchFilter) {
            folderFilter = (folderFilter || '').trim().toLowerCase();
            searchFilter = (searchFilter || '').trim().toLowerCase();

            return Object.keys(availableSounds).filter(key => {
                const path = (availableSounds[key] || key).toLowerCase();
                const kLower = key.toLowerCase();

                if (folderFilter) {
                    if (folderFilter === '(registered)') {
                        if (path.includes('/')) return false;
                    } else if (!path.startsWith(folderFilter.toLowerCase())) {
                        return false;
                    }
                }

                if (searchFilter) {
                    if (!kLower.includes(searchFilter) && !path.includes(searchFilter)) {
                        return false;
                    }
                }

                return true;
            });
        }

        function filterSFXOptions() {
            const folderFilter = document.getElementById('sfxFolderFilter')?.value || '';
            const searchFilter = document.getElementById('sfxSearchInput')?.value || '';
            const filtered = getFilteredSoundList(folderFilter, searchFilter);

            PHASES_METADATA.forEach(phase => {
                const sel = document.getElementById('sfx_select_' + phase.id);
                if (!sel) return;
                const currentVal = sel.value;

                if (filtered.length === 0) {
                    sel.innerHTML = '<option value="">(No sounds match filter)</option>';
                } else {
                    sel.innerHTML = filtered.map(k => {
                        const p = availableSounds[k] || k;
                        const filename = p.split('/').pop();
                        const isReg = (k !== p);
                        const label = isReg ? `⭐ ${k} (${filename})` : filename;
                        return `<option value="${k}" ${k === currentVal ? 'selected' : ''}>${label}</option>`;
                    }).join('');
                }
            });
        }

        function renderSFXCards() {
            const container = document.getElementById('sfxPhaseCards');
            if (!container) return;
            container.innerHTML = '';

            populateFolderDropdowns();
            const folderFilter = document.getElementById('sfxFolderFilter')?.value || '';
            const searchFilter = document.getElementById('sfxSearchInput')?.value || '';
            const filtered = getFilteredSoundList(folderFilter, searchFilter);

            const soundOptions = filtered.map(k => {
                const p = availableSounds[k] || k;
                const filename = p.split('/').pop();
                const isReg = (k !== p);
                const label = isReg ? `⭐ ${k} (${filename})` : filename;
                return `<option value="${k}">${label}</option>`;
            }).join('');

            PHASES_METADATA.forEach(phase => {
                const pCfg = currentConfig.phases[phase.id] || {};
                const sfxList = pCfg.sfx || [];

                const card = document.createElement('div');
                card.className = 'control-group';
                card.style.background = 'rgba(0,0,0,0.25)';
                card.style.padding = '0.85rem';
                card.style.borderRadius = '8px';
                card.style.border = '1px solid var(--panel-border)';

                let chipsHtml = sfxList.map((sfx, idx) => {
                    const p = availableSounds[sfx] || sfx;
                    const filename = p.split('/').pop();
                    return `
                        <div class="sfx-chip" title="${p}">
                            <span>🔊 ${filename}</span>
                            <button class="sfx-play-btn" onclick="playSound('${sfx}')" title="Preview sound">▶</button>
                            <button class="sfx-remove-btn" onclick="removeSFX('${phase.id}', ${idx})" title="Remove sound">×</button>
                        </div>
                    `;
                }).join('');

                card.innerHTML = `
                    <div class="control-label">
                        <span style="color:${phase.color}; font-weight:700;">${phase.label}</span>
                        <span style="font-size:0.75rem; color:var(--text-muted);">${sfxList.length} triggers</span>
                    </div>
                    <div class="sfx-tag-container" id="sfx_chips_${phase.id}">
                        ${chipsHtml || '<span style="font-size:0.75rem; color:var(--text-muted); font-style:italic;">No sound triggers</span>'}
                    </div>
                    <div class="sfx-add-row">
                        <select id="sfx_select_${phase.id}" style="flex:1; font-size:0.78rem;">
                            ${soundOptions || '<option value="">(No sounds match filter)</option>'}
                        </select>
                        <button class="btn btn-secondary" style="padding:0.35rem 0.6rem; font-size:0.75rem;" onclick="previewSelectedSound('${phase.id}')" title="Listen to highlighted sound">▶</button>
                        <button class="btn btn-primary" style="padding:0.35rem 0.7rem; font-size:0.75rem;" onclick="addSFX('${phase.id}')">+ Add</button>
                        <button class="btn btn-secondary" style="padding:0.35rem 0.6rem; font-size:0.75rem;" onclick="openAudioModal('${phase.id}')" title="Open full visual audio browser">📂</button>
                    </div>
                `;

                container.appendChild(card);
            });
        }

        function previewSelectedSound(phaseId) {
            const sel = document.getElementById('sfx_select_' + phaseId);
            if (sel && sel.value) {
                playSound(sel.value);
            }
        }

        function addSFX(phaseId) {
            const sel = document.getElementById('sfx_select_' + phaseId);
            const val = sel.value;
            if (!val) return;

            addSoundToPhase(phaseId, val);
        }

        function addSoundToPhase(phaseId, soundKey) {
            if (!currentConfig.phases[phaseId]) currentConfig.phases[phaseId] = {};
            if (!currentConfig.phases[phaseId].sfx) currentConfig.phases[phaseId].sfx = [];

            if (!currentConfig.phases[phaseId].sfx.includes(soundKey)) {
                currentConfig.phases[phaseId].sfx.push(soundKey);
                renderSFXCards();
                showToast(`🔊 Added '${soundKey.split('/').pop()}' to ${phaseId}!`);
                addLog('AUDIO', `Added sound '${soundKey}' to [${phaseId}]`);
            } else {
                showToast(`Sound already in ${phaseId}!`, "error");
            }
        }

        function removeSFX(phaseId, idx) {
            if (currentConfig.phases[phaseId] && currentConfig.phases[phaseId].sfx) {
                const removed = currentConfig.phases[phaseId].sfx.splice(idx, 1);
                renderSFXCards();
                showToast(`Removed sound trigger`);
                addLog('AUDIO', `Removed sound '${removed}' from [${phaseId}]`);
            }
        }

        /* ─── AUDIO MODAL LIBRARY BROWSER ─── */
        function openAudioModal(targetPhaseId) {
            const backdrop = document.getElementById('audioModalBackdrop');
            if (!backdrop) return;
            backdrop.classList.add('active');

            if (targetPhaseId) {
                const targetSel = document.getElementById('modalTargetPhase');
                if (targetSel) targetSel.value = targetPhaseId;
            }

            populateFolderDropdowns();
            filterModalAudioList();
        }

        function closeAudioModal() {
            const backdrop = document.getElementById('audioModalBackdrop');
            if (backdrop) backdrop.classList.remove('active');
            if (currentAudioPreviewElement) {
                currentAudioPreviewElement.pause();
                currentAudioPreviewElement = null;
            }
        }

        function filterModalAudioList() {
            const folderFilter = document.getElementById('modalFolderFilter')?.value || '';
            const searchFilter = document.getElementById('modalSearchInput')?.value || '';
            const filtered = getFilteredSoundList(folderFilter, searchFilter);
            renderModalAudioList(filtered);
        }

        function renderModalAudioList(keys) {
            const container = document.getElementById('modalAudioList');
            if (!container) return;

            if (keys.length === 0) {
                container.innerHTML = '<div style="text-align:center; padding:2rem; color:var(--text-muted);">No audio files found matching your search.</div>';
                return;
            }

            // Cap initial render to 100 items for performance, with lazy search
            const displayKeys = keys.slice(0, 150);
            const targetPhase = document.getElementById('modalTargetPhase')?.value || 'special_tentacles';

            container.innerHTML = displayKeys.map(k => {
                const path = availableSounds[k] || k;
                const filename = path.split('/').pop();
                const isReg = (k !== path);

                return `
                    <div class="audio-asset-item">
                        <div class="audio-asset-info">
                            <div class="audio-asset-name">
                                ${isReg ? '⭐ <span style="color:var(--accent-amber);">' + k + '</span> — ' : ''}${filename}
                            </div>
                            <div class="audio-asset-path">${path}</div>
                        </div>
                        <div class="audio-asset-actions">
                            <button class="btn btn-secondary" style="padding:0.3rem 0.6rem; font-size:0.75rem;" onclick="playSound('${k}')" title="Play Preview">▶ Play</button>
                            <button class="btn btn-primary" style="padding:0.3rem 0.7rem; font-size:0.75rem;" onclick="addSoundFromModal('${k}')">+ Add to Phase</button>
                        </div>
                    </div>
                `;
            }).join('') + (keys.length > 150 ? `<div style="text-align:center; color:var(--text-muted); font-size:0.75rem; padding:0.5rem;">Showing first 150 of ${keys.length} results. Use search filter to narrow down.</div>` : '');
        }

        function addSoundFromModal(soundKey) {
            const targetPhase = document.getElementById('modalTargetPhase')?.value || 'special_tentacles';
            addSoundToPhase(targetPhase, soundKey);
        }

        function playSound(name) {
            if (isAudioMuted) return;
            let relPath = availableSounds[name] || name;
            if (!relPath) return;

            relPath = relPath.replace(/^[\\/]+/, '');
            
            if (currentAudioPreviewElement) {
                currentAudioPreviewElement.pause();
            }

            const audioUrl = '/' + encodeURI(relPath);
            const audio = new Audio(audioUrl);
            audio.volume = 0.6;
            currentAudioPreviewElement = audio;

            audio.play().catch(e => {
                const fallbackUrl = '/audio/' + encodeURIComponent(relPath);
                const a2 = new Audio(fallbackUrl);
                a2.volume = 0.6;
                currentAudioPreviewElement = a2;
                a2.play().catch(err => console.log("Audio play error:", err));
            });
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

        /* ═══════════════════════════════════════════════════════════
           FL STUDIO / PRO TOOLS STYLE FREEFORM PLAYLIST DAW ENGINE
           ═══════════════════════════════════════════════════════════ */

        let dawPixelsPerSec = 75;
        let dawSpeed = 1.0;
        let dawSnapSec = 0.05;
        let dawMasterVolume = 1.0;
        let dawPlaying = false;
        let dawLooping = false;
        let dawCurrentTime = 0.0;
        let dawRafId = null;
        let dawLastTs = 0;
        let dawSelectedClip = null;
        const dawClips = [];
        const dawScheduledTimeouts = [];
        const dawActiveAudioSources = [];
        const TRACK_HEADER_WIDTH = 170;

        // Freeform Playlist Tracks
        let dawTracks = [
            { id: 0, name: "Track 1 (Lead SFX)", volume: 1.0, muted: false, solo: false },
            { id: 1, name: "Track 2 (Vocals & Roars)", volume: 1.0, muted: false, solo: false },
            { id: 2, name: "Track 3 (Impacts & Slashes)", volume: 1.0, muted: false, solo: false },
            { id: 3, name: "Track 4 (Magic & Spells)", volume: 1.0, muted: false, solo: false },
            { id: 4, name: "Track 5 (Atmosphere & Loops)", volume: 1.0, muted: false, solo: false },
            { id: 5, name: "Track 6 (Sub Layers)", volume: 1.0, muted: false, solo: false }
        ];

        // Web Audio API Context & Buffer Cache
        let dawAudioCtx = null;
        const dawBufferCache = {};

        function getDawAudioContext() {
            if (!dawAudioCtx) {
                const AudioCtxClass = window.AudioContext || window.webkitAudioContext;
                if (AudioCtxClass) {
                    dawAudioCtx = new AudioCtxClass();
                }
            }
            if (dawAudioCtx && dawAudioCtx.state === 'suspended') {
                dawAudioCtx.resume();
            }
            return dawAudioCtx;
        }

        async function dawFetchAudioBuffer(url) {
            if (dawBufferCache[url]) {
                return dawBufferCache[url];
            }
            try {
                const ctx = getDawAudioContext();
                if (!ctx) return null;
                const resp = await fetch(url);
                const arrayBuf = await resp.arrayBuffer();
                const audioBuf = await ctx.decodeAudioData(arrayBuf);
                dawBufferCache[url] = audioBuf;
                return audioBuf;
            } catch (err) {
                console.warn("Could not decode audio buffer for:", url, err);
                return null;
            }
        }

        function dawGetPhaseDurations() {
            const p = currentConfig.phases || {};
            return [
                { id: 'fade_in', dur: p.fade_in?.duration || 1.5 },
                { id: 'orb_collapse', dur: (p.orb_collapse?.frame_duration || 0.11) * 16 },
                { id: 'orb_loop', dur: (p.orb_loop?.frame_duration || 0.1) * 8 * (p.orb_loop?.loop_cycles || 4) },
                { id: 'demon_burst', dur: (p.demon_burst?.frame_duration || 0.055) * 13 },
                { id: 'attack_left', dur: (p.attack_left?.frame_duration || 0.065) * 12 },
                { id: 'attack_right', dur: (p.attack_right?.frame_duration || 0.065) * 12 },
                { id: 'special_tentacles', dur: (p.special_tentacles?.frame_duration || 0.1) * 19 },
                { id: 'revert', dur: (p.revert?.frame_duration || 0.09) * 14 + (p.revert?.post_pause || 0.6) }
            ];
        }

        function dawTotalDuration() {
            return dawGetPhaseDurations().reduce((sum, p) => sum + p.dur, 0);
        }

        function dawPhaseAbsoluteStarts() {
            const phases = dawGetPhaseDurations();
            let t = 0;
            return phases.map(p => {
                const start = t;
                t += p.dur;
                return { ...p, start };
            });
        }

        function dawSoundDisplayName(key) {
            if (!key) return '?';
            const parts = key.replace(/\\\\/g, '/').split('/');
            const fname = parts[parts.length - 1];
            return fname.replace(/\.(wav|mp3|ogg)$/i, '');
        }

        function dawGetPhaseAtTime(timeSec) {
            const absPhases = dawPhaseAbsoluteStarts();
            return absPhases.find(p => timeSec >= p.start && timeSec < p.start + p.dur) || absPhases[absPhases.length - 1];
        }

        function dawGetPhaseColor(timeSec) {
            const ph = dawGetPhaseAtTime(timeSec);
            const meta = PHASES_METADATA.find(m => m.id === ph.id) || { color: '#38bdf8' };
            return meta.color;
        }

        /* ─── DATA SYNC & MIGRATION ─── */
        function buildClipsFromConfig() {
            dawClips.length = 0;
            const absPhases = dawPhaseAbsoluteStarts();

            // 1. If global audio_timeline exists, load it directly
            if (currentConfig.audio_timeline && Array.isArray(currentConfig.audio_timeline) && currentConfig.audio_timeline.length > 0) {
                currentConfig.audio_timeline.forEach((entry, idx) => {
                    const time = entry.time !== undefined ? entry.time : 0.0;
                    const color = dawGetPhaseColor(time);
                    dawClips.push({
                        id: `clip_${idx}_${Date.now().toString(36)}`,
                        key: entry.key,
                        time: time,
                        duration: entry.duration !== undefined ? entry.duration : 1.5,
                        sampleStart: entry.sample_start !== undefined ? entry.sample_start : 0.0,
                        volume: entry.volume !== undefined ? entry.volume : 1.0,
                        pan: entry.pan !== undefined ? entry.pan : 0.0,
                        fadeIn: entry.fade_in !== undefined ? entry.fade_in : 0.0,
                        fadeOut: entry.fade_out !== undefined ? entry.fade_out : 0.0,
                        pitch: entry.pitch !== undefined ? entry.pitch : 1.0,
                        trackIdx: entry.track_idx !== undefined ? entry.track_idx : (idx % dawTracks.length),
                        muted: entry.muted || false,
                        solo: entry.solo || false,
                        color: color
                    });
                });
                return;
            }

            // 2. Migration from phase-based configurations
            let globalTrackIdx = 0;
            absPhases.forEach(ph => {
                const phaseConf = currentConfig.phases?.[ph.id] || {};
                const meta = PHASES_METADATA.find(m => m.id === ph.id) || { color: '#38bdf8', label: ph.id };

                const timeline = phaseConf.sfx_timeline;
                const sfx = phaseConf.sfx || [];

                if (timeline && timeline.length > 0) {
                    timeline.forEach((entry, idx) => {
                        const time = ph.start + (entry.offset || 0.0);
                        dawClips.push({
                            id: `clip_${ph.id}_${idx}_${Date.now().toString(36)}`,
                            key: entry.key,
                            time: time,
                            duration: entry.duration !== undefined ? entry.duration : Math.min(ph.dur - (entry.offset || 0), 2.0),
                            sampleStart: 0.0,
                            volume: entry.volume !== undefined ? entry.volume : 1.0,
                            pan: entry.pan !== undefined ? entry.pan : 0.0,
                            fadeIn: entry.fade_in !== undefined ? entry.fade_in : 0.0,
                            fadeOut: entry.fade_out !== undefined ? entry.fade_out : 0.0,
                            pitch: entry.pitch !== undefined ? entry.pitch : 1.0,
                            trackIdx: (globalTrackIdx++) % dawTracks.length,
                            muted: entry.muted || false,
                            solo: entry.solo || false,
                            color: meta.color
                        });
                    });
                } else if (sfx.length > 0) {
                    sfx.forEach((key, idx) => {
                        dawClips.push({
                            id: `clip_${ph.id}_${idx}_${Date.now().toString(36)}`,
                            key: key,
                            time: ph.start,
                            duration: Math.min(ph.dur, 2.0),
                            sampleStart: 0.0,
                            volume: 1.0,
                            pan: 0.0,
                            fadeIn: 0.0,
                            fadeOut: 0.0,
                            pitch: 1.0,
                            trackIdx: (globalTrackIdx++) % dawTracks.length,
                            muted: false,
                            solo: false,
                            color: meta.color
                        });
                    });
                }
            });

            syncDAWToConfig();
        }

        function syncDAWToConfig() {
            // Write global freeform timeline
            currentConfig.audio_timeline = dawClips.map(c => ({
                key: c.key,
                time: Math.round(c.time * 1000) / 1000,
                duration: Math.round(c.duration * 1000) / 1000,
                sample_start: Math.round((c.sampleStart || 0.0) * 1000) / 1000,
                volume: Math.round((c.volume !== undefined ? c.volume : 1.0) * 100) / 100,
                pan: Math.round((c.pan || 0) * 100) / 100,
                fade_in: Math.round((c.fadeIn || 0) * 1000) / 1000,
                fade_out: Math.round((c.fadeOut || 0) * 1000) / 1000,
                pitch: Math.round((c.pitch || 1.0) * 100) / 100,
                track_idx: c.trackIdx || 0,
                muted: c.muted,
                solo: c.solo
            }));

            // Also keep legacy phase sfx in sync for backward compatibility
            const absPhases = dawPhaseAbsoluteStarts();
            absPhases.forEach(ph => {
                if (!currentConfig.phases[ph.id]) currentConfig.phases[ph.id] = {};
                const phaseSounds = dawClips.filter(c => c.time >= ph.start && c.time < ph.start + ph.dur);
                currentConfig.phases[ph.id].sfx = phaseSounds.map(c => c.key);
            });
        }

        function dawAddNewTrack() {
            const newId = dawTracks.length;
            dawTracks.push({
                id: newId,
                name: `Track ${newId + 1}`,
                volume: 1.0,
                muted: false,
                solo: false
            });
            renderDAWTimeline();
            showToast(`Added Track ${newId + 1}`, 'success');
        }

        function dawSetZoom(pixelsPerSec) {
            dawPixelsPerSec = Math.max(30, Math.min(300, pixelsPerSec));
            const slider = document.getElementById('dawZoomSlider');
            if (slider) slider.value = dawPixelsPerSec;
            const lbl = document.getElementById('dawZoomLabel');
            if (lbl) lbl.textContent = dawPixelsPerSec + 'px/s';
            renderDAWTimeline();
        }

        function dawFitAllZoom() {
            const body = document.getElementById('dawBody');
            if (!body) return;
            const availableW = body.clientWidth - TRACK_HEADER_WIDTH - 50;
            const totalDur = dawTotalDuration();
            if (totalDur > 0 && availableW > 100) {
                const ideal = Math.max(30, Math.min(200, Math.floor(availableW / totalDur)));
                dawSetZoom(ideal);
                showToast(`Timeline fitted to screen (${ideal}px/s)`, 'success');
            }
        }

        function dawSetMasterVolume(vol) {
            dawMasterVolume = Math.max(0, Math.min(1, vol));
            const lbl = document.getElementById('dawMasterVolLabel');
            if (lbl) lbl.textContent = Math.round(dawMasterVolume * 100) + '%';
        }

        function dawUpdatePlaybackRate() {
            // Handled during playback
        }

        /* ─── RENDER MAIN PLAYLIST TIMELINE ─── */
        function renderDAWTimeline() {
            if (dawClips.length === 0) {
                buildClipsFromConfig();
            }

            const totalDur = dawTotalDuration();
            const totalWidth = TRACK_HEADER_WIDTH + totalDur * dawPixelsPerSec;

            const scrollArea = document.getElementById('dawScrollArea');
            if (scrollArea) scrollArea.style.width = totalWidth + 'px';

            const absPhases = dawPhaseAbsoluteStarts();

            // ── 1. RENDER RULER & SCENE PHASES ──
            const rulerTimeline = document.getElementById('dawRulerTimeline');
            if (rulerTimeline) {
                rulerTimeline.innerHTML = '';
                rulerTimeline.style.width = (totalDur * dawPixelsPerSec) + 'px';

                // Phase blocks in ruler
                absPhases.forEach(ph => {
                    const meta = PHASES_METADATA.find(m => m.id === ph.id) || { label: ph.id, color: '#38bdf8' };
                    const block = document.createElement('div');
                    block.className = 'daw-ruler-phase-block';
                    block.style.left = (ph.start * dawPixelsPerSec) + 'px';
                    block.style.width = (ph.dur * dawPixelsPerSec) + 'px';
                    block.style.borderTop = `3px solid ${meta.color}`;
                    block.innerHTML = `
                        <span class="daw-ruler-phase-name" style="color:${meta.color};">${meta.label}</span>
                        <span class="daw-ruler-time-range">${ph.start.toFixed(2)}s – ${(ph.start + ph.dur).toFixed(2)}s</span>
                    `;
                    rulerTimeline.appendChild(block);
                });

                // Second ticks & labels
                const step = dawPixelsPerSec < 50 ? 2 : (dawPixelsPerSec > 130 ? 0.5 : 1);
                for (let s = 0; s <= totalDur; s += step) {
                    const isMajor = Math.round(s) === s;
                    const tick = document.createElement('div');
                    tick.className = 'daw-ruler-tick' + (isMajor ? '' : ' sub');
                    tick.style.left = (s * dawPixelsPerSec) + 'px';
                    rulerTimeline.appendChild(tick);

                    if (isMajor || step < 1) {
                        const lbl = document.createElement('div');
                        lbl.className = 'daw-ruler-tick-label';
                        lbl.style.left = (s * dawPixelsPerSec) + 'px';
                        lbl.textContent = s.toFixed(isMajor ? 0 : 1) + 's';
                        rulerTimeline.appendChild(lbl);
                    }
                }
            }

            // ── 2. RENDER PLAYLIST TRACKS ──
            const tracksContainer = document.getElementById('dawTracksContainer');
            if (tracksContainer) {
                tracksContainer.innerHTML = '';

                // Ensure enough tracks exist
                const maxTrackNeeded = Math.max(dawTracks.length - 1, ...dawClips.map(c => c.trackIdx || 0));
                while (dawTracks.length <= maxTrackNeeded) {
                    dawTracks.push({
                        id: dawTracks.length,
                        name: `Track ${dawTracks.length + 1}`,
                        volume: 1.0,
                        muted: false,
                        solo: false
                    });
                }

                dawTracks.forEach((track, tIdx) => {
                    const row = document.createElement('div');
                    row.className = 'daw-track-row';
                    row.dataset.trackIdx = tIdx;

                    // Track Header Box
                    const header = document.createElement('div');
                    header.className = 'daw-track-header-box';

                    const trackClips = dawClips.filter(c => (c.trackIdx || 0) === tIdx);

                    header.innerHTML = `
                        <div class="daw-track-header-top">
                            <input type="text" value="${track.name}" class="daw-track-title" style="background:transparent; border:none; width:110px;" onchange="dawTracks[${tIdx}].name=this.value;">
                        </div>
                        <div class="daw-track-header-bottom">
                            <span class="daw-track-cue-count">${trackClips.length} ${trackClips.length === 1 ? 'clip' : 'clips'}</span>
                            <div class="daw-track-actions">
                                <button class="daw-btn-icon-sm ${track.muted ? 'active-mute' : ''}" onclick="dawToggleTrackMute(${tIdx})" title="Mute track">M</button>
                                <button class="daw-btn-icon-sm ${track.solo ? 'active-solo' : ''}" onclick="dawToggleTrackSolo(${tIdx})" title="Solo track">S</button>
                                <button class="daw-btn-icon-sm" style="color:#38bdf8;" onclick="dawOpenAddSoundModal(${tIdx})" title="Add sound to this track">+ Add</button>
                            </div>
                        </div>
                    `;
                    row.appendChild(header);

                    // Track Lane Area
                    const laneArea = document.createElement('div');
                    laneArea.className = 'daw-track-lane-area';
                    laneArea.dataset.trackIdx = tIdx;
                    laneArea.style.width = (totalDur * dawPixelsPerSec) + 'px';

                    // Vertical Phase Column Guides
                    absPhases.forEach(ph => {
                        const meta = PHASES_METADATA.find(m => m.id === ph.id) || { color: '#38bdf8' };
                        const col = document.createElement('div');
                        col.className = 'daw-phase-column-backdrop';
                        col.style.left = (ph.start * dawPixelsPerSec) + 'px';
                        col.style.width = (ph.dur * dawPixelsPerSec) + 'px';
                        col.style.background = meta.color;
                        col.dataset.phaseId = ph.id;
                        laneArea.appendChild(col);
                    });

                    // Grid lines (1s intervals)
                    for (let s = 0; s <= totalDur; s += 1) {
                        const gLine = document.createElement('div');
                        gLine.className = 'daw-grid-line' + (Math.round(s) % 2 === 0 ? ' major' : '');
                        gLine.style.left = (s * dawPixelsPerSec) + 'px';
                        laneArea.appendChild(gLine);
                    }

                    // Render Clips on this Track
                    trackClips.forEach(clip => {
                        clip.color = dawGetPhaseColor(clip.time);
                        const clipEl = dawCreateClipElement(clip);
                        laneArea.appendChild(clipEl);
                    });

                    row.appendChild(laneArea);
                    tracksContainer.appendChild(row);
                });
            }

            dawUpdatePlayheadPosition();
            dawUpdateTimeDisplay();
            dawRenderInspector();
        }

        /* ─── CREATE INTERACTIVE FREEFORM CLIP CAPSULE ─── */
        function dawCreateClipElement(clip) {
            const el = document.createElement('div');
            el.className = 'daw-clip' + (clip.muted ? ' muted' : '') + (dawSelectedClip?.id === clip.id ? ' selected' : '');
            el.id = 'clip_el_' + clip.id;
            el.dataset.clipId = clip.id;

            const leftPx = clip.time * dawPixelsPerSec;
            const widthPx = Math.max(20, clip.duration * dawPixelsPerSec);

            el.style.left = leftPx + 'px';
            el.style.width = widthPx + 'px';
            el.style.borderColor = clip.color;
            el.style.background = `linear-gradient(180deg, ${clip.color}35 0%, #0f172a 100%)`;

            const panLabel = (clip.pan < -0.05) ? `L${Math.round(Math.abs(clip.pan)*100)}` : (clip.pan > 0.05 ? `R${Math.round(clip.pan*100)}` : 'C');
            const volLabel = Math.round(clip.volume * 100) + '%';
            const cropLabel = (clip.sampleStart && clip.sampleStart > 0.01) ? `✂+${clip.sampleStart.toFixed(2)}s` : '';
            const fadeInPx = Math.min(widthPx / 2, (clip.fadeIn || 0) * dawPixelsPerSec);
            const fadeOutPx = Math.min(widthPx / 2, (clip.fadeOut || 0) * dawPixelsPerSec);

            el.innerHTML = `
                <!-- Fade In Overlay -->
                <div class="daw-fade-in-overlay" id="fade_in_overlay_${clip.id}" style="width:${fadeInPx}px;"></div>
                <!-- Fade Out Overlay -->
                <div class="daw-fade-out-overlay" id="fade_out_overlay_${clip.id}" style="width:${fadeOutPx}px;"></div>

                <!-- Header Bar -->
                <div class="daw-clip-header">
                    <span class="daw-clip-title" title="${clip.key}">${dawSoundDisplayName(clip.key)}</span>
                    <div class="daw-clip-tags">
                        ${cropLabel ? `<span class="daw-clip-tag" style="color:#f59e0b;" id="tag_crop_${clip.id}">${cropLabel}</span>` : ''}
                        <span class="daw-clip-tag" id="tag_vol_${clip.id}">${volLabel}</span>
                        <span class="daw-clip-tag" id="tag_pan_${clip.id}">${panLabel}</span>
                    </div>
                </div>

                <!-- Simulated Audio Waveform -->
                <svg class="daw-clip-waveform" viewBox="0 0 100 20" preserveAspectRatio="none">
                    <path d="M0,10 Q5,2 10,10 T20,10 T30,3 T40,15 T50,2 T60,18 T70,5 T80,14 T90,7 T100,10 L100,20 L0,20 Z" fill="${clip.color}" opacity="0.4"/>
                    <path d="M0,10 Q5,2 10,10 T20,10 T30,3 T40,15 T50,2 T60,18 T70,5 T80,14 T90,7 T100,10" stroke="#ffffff" stroke-width="1" fill="none" opacity="0.6"/>
                </svg>

                <!-- Handles -->
                <div class="daw-fade-handle fade-in" id="handle_fade_in_${clip.id}" style="left:${fadeInPx}px;" title="Drag to adjust Fade In"></div>
                <div class="daw-fade-handle fade-out" id="handle_fade_out_${clip.id}" style="right:${fadeOutPx}px;" title="Drag to adjust Fade Out"></div>
                <div class="daw-trim-handle trim-left" title="Drag to crop start (Sample Start)"></div>
                <div class="daw-trim-handle trim-right" title="Drag to crop/extend duration"></div>
            `;

            // Mouse Interactions
            el.addEventListener('mousedown', (e) => {
                dawSelectClip(clip);
                if (e.target.classList.contains('fade-in')) {
                    dawStartFadeInDrag(e, clip);
                } else if (e.target.classList.contains('fade-out')) {
                    dawStartFadeOutDrag(e, clip);
                } else if (e.target.classList.contains('trim-left')) {
                    dawStartTrimLeftDrag(e, clip);
                } else if (e.target.classList.contains('trim-right')) {
                    dawStartTrimRightDrag(e, clip);
                } else {
                    dawStartMoveDrag(e, clip);
                }
            });

            el.addEventListener('dblclick', (e) => {
                e.stopPropagation();
                dawPreviewClipSolo(clip);
            });

            return el;
        }

        /* ─── DIRECT ZERO-STUTTER DRAGGING ACROSS TRACKS & SCENES ─── */
        let dawActiveDrag = null;

        function dawQuantize(valSec) {
            if (dawSnapSec <= 0) return valSec;
            return Math.round(valSec / dawSnapSec) * dawSnapSec;
        }

        function dawShowTooltip(text, clientX, clientY) {
            const tip = document.getElementById('dawDragTooltip');
            if (tip) {
                tip.textContent = text;
                tip.style.left = clientX + 'px';
                tip.style.top = clientY + 'px';
                tip.style.display = 'block';
            }
        }

        function dawHideTooltip() {
            const tip = document.getElementById('dawDragTooltip');
            if (tip) tip.style.display = 'none';
        }

        // 1. Move Clip Across Timeline & Tracks
        function dawStartMoveDrag(e, clip) {
            e.preventDefault();
            const elem = document.getElementById('clip_el_' + clip.id);
            dawActiveDrag = {
                type: 'move',
                clip: clip,
                elem: elem,
                startX: e.clientX,
                startY: e.clientY,
                origTime: clip.time,
                origTrackIdx: clip.trackIdx || 0
            };
            dawShowTooltip(`Time: ${clip.time.toFixed(3)}s | Track ${(clip.trackIdx||0)+1}`, e.clientX, e.clientY);
            document.addEventListener('mousemove', dawOnGlobalMouseMove);
            document.addEventListener('mouseup', dawOnGlobalMouseUp);
        }

        // 2. Fade In Drag
        function dawStartFadeInDrag(e, clip) {
            e.preventDefault();
            e.stopPropagation();
            const overlay = document.getElementById('fade_in_overlay_' + clip.id);
            const handle = document.getElementById('handle_fade_in_' + clip.id);
            dawActiveDrag = {
                type: 'fade_in',
                clip: clip,
                overlay: overlay,
                handle: handle,
                startX: e.clientX,
                origFadeIn: clip.fadeIn || 0.0
            };
            dawShowTooltip(`Fade In: ${(clip.fadeIn || 0).toFixed(2)}s`, e.clientX, e.clientY);
            document.addEventListener('mousemove', dawOnGlobalMouseMove);
            document.addEventListener('mouseup', dawOnGlobalMouseUp);
        }

        // 3. Fade Out Drag
        function dawStartFadeOutDrag(e, clip) {
            e.preventDefault();
            e.stopPropagation();
            const overlay = document.getElementById('fade_out_overlay_' + clip.id);
            const handle = document.getElementById('handle_fade_out_' + clip.id);
            dawActiveDrag = {
                type: 'fade_out',
                clip: clip,
                overlay: overlay,
                handle: handle,
                startX: e.clientX,
                origFadeOut: clip.fadeOut || 0.0
            };
            dawShowTooltip(`Fade Out: ${(clip.fadeOut || 0).toFixed(2)}s`, e.clientX, e.clientY);
            document.addEventListener('mousemove', dawOnGlobalMouseMove);
            document.addEventListener('mouseup', dawOnGlobalMouseUp);
        }

        // 4. Crop Start (Left Trim)
        function dawStartTrimLeftDrag(e, clip) {
            e.preventDefault();
            e.stopPropagation();
            const elem = document.getElementById('clip_el_' + clip.id);
            dawActiveDrag = {
                type: 'trim_left',
                clip: clip,
                elem: elem,
                startX: e.clientX,
                origTime: clip.time,
                origDur: clip.duration,
                origSampleStart: clip.sampleStart || 0.0
            };
            document.addEventListener('mousemove', dawOnGlobalMouseMove);
            document.addEventListener('mouseup', dawOnGlobalMouseUp);
        }

        // 5. Crop Tail (Right Trim)
        function dawStartTrimRightDrag(e, clip) {
            e.preventDefault();
            e.stopPropagation();
            const elem = document.getElementById('clip_el_' + clip.id);
            dawActiveDrag = {
                type: 'trim_right',
                clip: clip,
                elem: elem,
                startX: e.clientX,
                origDur: clip.duration
            };
            document.addEventListener('mousemove', dawOnGlobalMouseMove);
            document.addEventListener('mouseup', dawOnGlobalMouseUp);
        }

        function dawOnGlobalMouseMove(e) {
            if (!dawActiveDrag) return;
            const d = dawActiveDrag;
            const dx = e.clientX - d.startX;
            const dtSec = dx / dawPixelsPerSec;
            const totalDur = dawTotalDuration();

            if (d.type === 'move') {
                let newTime = d.origTime + dtSec;
                newTime = dawQuantize(newTime);
                newTime = Math.max(0, Math.min(newTime, totalDur - 0.05));
                d.clip.time = newTime;

                // Vertical track hopping
                const trackRows = document.querySelectorAll('.daw-track-row');
                trackRows.forEach(row => {
                    const rect = row.getBoundingClientRect();
                    if (e.clientY >= rect.top && e.clientY <= rect.bottom) {
                        d.clip.trackIdx = parseInt(row.dataset.trackIdx);
                    }
                });

                if (d.elem) {
                    d.elem.style.left = (newTime * dawPixelsPerSec) + 'px';
                }

                const curPhase = dawGetPhaseAtTime(newTime);
                dawShowTooltip(`Time: ${newTime.toFixed(3)}s [${curPhase.id}] | Track ${(d.clip.trackIdx||0)+1}`, e.clientX, e.clientY);
                dawUpdateInspectorInputs();
            }
            else if (d.type === 'fade_in') {
                let newFade = Math.max(0, Math.min(d.clip.duration / 2, d.origFadeIn + dtSec));
                newFade = dawQuantize(newFade);
                d.clip.fadeIn = newFade;
                const px = newFade * dawPixelsPerSec;
                if (d.overlay) d.overlay.style.width = px + 'px';
                if (d.handle) d.handle.style.left = px + 'px';
                dawShowTooltip(`Fade In: ${newFade.toFixed(2)}s`, e.clientX, e.clientY);
                dawUpdateInspectorInputs();
            }
            else if (d.type === 'fade_out') {
                let newFade = Math.max(0, Math.min(d.clip.duration / 2, d.origFadeOut - dtSec));
                newFade = dawQuantize(newFade);
                d.clip.fadeOut = newFade;
                const px = newFade * dawPixelsPerSec;
                if (d.overlay) d.overlay.style.width = px + 'px';
                if (d.handle) d.handle.style.right = px + 'px';
                dawShowTooltip(`Fade Out: ${newFade.toFixed(2)}s`, e.clientX, e.clientY);
                dawUpdateInspectorInputs();
            }
            else if (d.type === 'trim_left') {
                let newTime = Math.max(0, Math.min(d.origTime + dtSec, d.origTime + d.origDur - 0.05));
                newTime = dawQuantize(newTime);
                const actualShift = newTime - d.origTime;
                const newDur = Math.max(0.05, d.origDur - actualShift);
                const newSampleStart = Math.max(0, d.origSampleStart + actualShift);

                d.clip.time = newTime;
                d.clip.duration = newDur;
                d.clip.sampleStart = newSampleStart;

                if (d.elem) {
                    d.elem.style.left = (newTime * dawPixelsPerSec) + 'px';
                    d.elem.style.width = (newDur * dawPixelsPerSec) + 'px';
                }
                dawShowTooltip(`Crop Head: +${newSampleStart.toFixed(2)}s | Time: ${newTime.toFixed(3)}s | Dur: ${newDur.toFixed(2)}s`, e.clientX, e.clientY);
                dawUpdateInspectorInputs();
            }
            else if (d.type === 'trim_right') {
                let newDur = Math.max(0.05, d.origDur + dtSec);
                newDur = dawQuantize(newDur);
                d.clip.duration = newDur;
                if (d.elem) {
                    d.elem.style.width = (newDur * dawPixelsPerSec) + 'px';
                }
                dawShowTooltip(`Duration: ${newDur.toFixed(3)}s`, e.clientX, e.clientY);
                dawUpdateInspectorInputs();
            }
        }

        function dawOnGlobalMouseUp() {
            if (dawActiveDrag) {
                dawHideTooltip();
                syncDAWToConfig();
                dawActiveDrag = null;
                renderDAWTimeline();
            }
            document.removeEventListener('mousemove', dawOnGlobalMouseMove);
            document.removeEventListener('mouseup', dawOnGlobalMouseUp);
        }

        /* ─── SLICING / SPLITTING AT PLAYHEAD ─── */
        function dawSplitSelectedClip() {
            if (!dawSelectedClip) {
                showToast('Select a clip to split/slice', 'error');
                return;
            }
            const c = dawSelectedClip;
            const splitTime = dawCurrentTime;

            if (splitTime <= c.time + 0.02 || splitTime >= c.time + c.duration - 0.02) {
                showToast('Move playhead inside the clip to slice it', 'error');
                return;
            }

            const cutOffset = splitTime - c.time;
            const originalDur = c.duration;
            const originalSampleStart = c.sampleStart || 0.0;

            // Clip 1 (First Half)
            c.duration = cutOffset;

            // Clip 2 (Second Half)
            const newClip = {
                ...c,
                id: `clip_slice_${Date.now().toString(36)}`,
                time: splitTime,
                duration: originalDur - cutOffset,
                sampleStart: originalSampleStart + cutOffset,
                fadeIn: 0.0,
                fadeOut: c.fadeOut || 0.0
            };

            dawClips.push(newClip);
            syncDAWToConfig();
            dawSelectedClip = newClip;
            renderDAWTimeline();
            showToast(`Sliced sound into 2 pieces at t=${splitTime.toFixed(2)}s`, 'success');
        }

        /* ─── TRACK MUTE & SOLO ─── */
        function dawToggleTrackMute(trackIdx) {
            if (dawTracks[trackIdx]) {
                dawTracks[trackIdx].muted = !dawTracks[trackIdx].muted;
                renderDAWTimeline();
            }
        }

        function dawToggleTrackSolo(trackIdx) {
            if (dawTracks[trackIdx]) {
                dawTracks[trackIdx].solo = !dawTracks[trackIdx].solo;
                renderDAWTimeline();
            }
        }

        /* ─── CLIP SELECTION & INSPECTOR ─── */
        function dawSelectClip(clip) {
            dawSelectedClip = clip;
            document.querySelectorAll('.daw-clip').forEach(c => c.classList.remove('selected'));
            const el = document.getElementById('clip_el_' + clip.id);
            if (el) el.classList.add('selected');
            dawRenderInspector();
        }

        function dawRenderInspector() {
            const inspector = document.getElementById('dawInspector');
            if (!inspector) return;

            if (!dawSelectedClip) {
                inspector.innerHTML = '<span style="font-size:0.8rem; color:#64748b; font-style:italic;">Click any clip on the playlist to inspect, crop, fade, tune volume, pitch & stereo pan</span>';
                return;
            }

            const c = dawSelectedClip;
            const panDisplay = (c.pan < -0.05) ? `Left ${Math.round(Math.abs(c.pan)*100)}%` : ((c.pan > 0.05) ? `Right ${Math.round(c.pan*100)}%` : 'Center');
            const volPct = Math.round((c.volume !== undefined ? c.volume : 1.0) * 100);

            inspector.innerHTML = `
                <div class="daw-inspector-badge-group">
                    <div class="daw-inspector-title" title="${c.key}">🎵 ${dawSoundDisplayName(c.key)}</div>
                    <div class="daw-inspector-path" title="${c.key}">${c.key}</div>
                </div>

                <div class="daw-inspector-controls-grid">
                    <!-- Global Time Position -->
                    <div class="daw-param-box">
                        <span class="daw-param-label">Start Time (s)</span>
                        <div class="daw-param-input-row">
                            <input type="number" id="insp_time" step="0.05" min="0" max="${dawTotalDuration().toFixed(2)}" value="${c.time.toFixed(3)}" onchange="dawInspectorChangeTime(this.value)">
                            <button class="daw-btn-icon-sm" onclick="dawInspectorNudgeTime(-0.1)">-0.1</button>
                            <button class="daw-btn-icon-sm" onclick="dawInspectorNudgeTime(0.1)">+0.1</button>
                        </div>
                    </div>

                    <!-- Duration -->
                    <div class="daw-param-box">
                        <span class="daw-param-label">Duration (s)</span>
                        <div class="daw-param-input-row">
                            <input type="number" id="insp_dur" step="0.05" min="0.05" max="30.0" value="${c.duration.toFixed(3)}" onchange="dawInspectorChangeDuration(this.value)">
                        </div>
                    </div>

                    <!-- Crop Head (Sample Start) -->
                    <div class="daw-param-box">
                        <span class="daw-param-label" style="color:#f59e0b;">✂️ Crop Head (s)</span>
                        <div class="daw-param-input-row">
                            <input type="number" id="insp_sample_start" step="0.05" min="0" max="30.0" value="${(c.sampleStart || 0).toFixed(3)}" onchange="dawInspectorChangeSampleStart(this.value)">
                        </div>
                    </div>

                    <!-- Fade In -->
                    <div class="daw-param-box">
                        <div class="daw-param-label">
                            <span>Fade In</span>
                            <span class="daw-param-val-badge" id="val_insp_fade_in">${(c.fadeIn || 0).toFixed(2)}s</span>
                        </div>
                        <div class="daw-param-input-row">
                            <input type="range" id="insp_fade_in" min="0" max="2.0" step="0.02" value="${c.fadeIn || 0}" oninput="dawInspectorSetFadeIn(parseFloat(this.value))">
                        </div>
                    </div>

                    <!-- Fade Out -->
                    <div class="daw-param-box">
                        <div class="daw-param-label">
                            <span>Fade Out</span>
                            <span class="daw-param-val-badge" id="val_insp_fade_out">${(c.fadeOut || 0).toFixed(2)}s</span>
                        </div>
                        <div class="daw-param-input-row">
                            <input type="range" id="insp_fade_out" min="0" max="2.0" step="0.02" value="${c.fadeOut || 0}" oninput="dawInspectorSetFadeOut(parseFloat(this.value))">
                        </div>
                    </div>

                    <!-- Volume -->
                    <div class="daw-param-box">
                        <div class="daw-param-label">
                            <span>Volume</span>
                            <span class="daw-param-val-badge" id="val_insp_volume">${volPct}%</span>
                        </div>
                        <div class="daw-param-input-row">
                            <input type="range" id="insp_volume" min="0" max="2.0" step="0.01" value="${c.volume !== undefined ? c.volume : 1.0}" oninput="dawInspectorSetVolume(parseFloat(this.value))">
                        </div>
                    </div>

                    <!-- Stereo Pan -->
                    <div class="daw-param-box">
                        <div class="daw-param-label">
                            <span>Stereo Pan</span>
                            <span class="daw-param-val-badge" id="val_insp_pan" style="color:#f59e0b;">${panLabelForVal(c.pan || 0)}</span>
                        </div>
                        <div class="daw-param-input-row">
                            <input type="range" id="insp_pan" min="-1.0" max="1.0" step="0.05" value="${c.pan || 0}" oninput="dawInspectorSetPan(parseFloat(this.value))" style="accent-color:#f59e0b;">
                        </div>
                    </div>

                    <!-- Pitch / Speed Shift -->
                    <div class="daw-param-box">
                        <span class="daw-param-label">Pitch / Speed</span>
                        <div class="daw-param-input-row">
                            <select id="insp_pitch" onchange="dawInspectorSetPitch(parseFloat(this.value))" style="background:#040810; border:1px solid #334155; color:#fff; border-radius:5px; padding:0.25rem 0.4rem; font-size:0.75rem;">
                                <option value="0.5" ${c.pitch === 0.5 ? 'selected' : ''}>0.5x Deep Demon</option>
                                <option value="0.75" ${c.pitch === 0.75 ? 'selected' : ''}>0.75x Heavy Beast</option>
                                <option value="1.0" ${(!c.pitch || c.pitch === 1.0) ? 'selected' : ''}>1.0x Normal</option>
                                <option value="1.25" ${c.pitch === 1.25 ? 'selected' : ''}>1.25x Sharp Clang</option>
                                <option value="1.5" ${c.pitch === 1.5 ? 'selected' : ''}>1.5x Screech</option>
                                <option value="2.0" ${c.pitch === 2.0 ? 'selected' : ''}>2.0x High Pitch</option>
                            </select>
                        </div>
                    </div>
                </div>

                <div class="daw-inspector-actions">
                    <button class="btn btn-secondary" style="padding:0.35rem 0.7rem; font-size:0.75rem;" onclick="dawPreviewClipSolo(dawSelectedClip)">🔊 Solo Audition</button>
                    <button class="btn btn-secondary" style="padding:0.35rem 0.7rem; font-size:0.75rem; color:#38bdf8;" onclick="dawSplitSelectedClip()" title="Slice at playhead (S key)">✂️ Split (S)</button>
                    <button class="btn btn-secondary" style="padding:0.35rem 0.65rem; font-size:0.75rem;" onclick="dawDuplicateClip(dawSelectedClip)" title="Duplicate sound (Ctrl+D)">📋 Duplicate</button>
                    <button class="btn ${c.muted ? 'btn-primary' : 'btn-secondary'}" style="padding:0.35rem 0.65rem; font-size:0.75rem;" onclick="dawInspectorToggleMute()">${c.muted ? '🔇 Unmute' : '🔇 Mute'}</button>
                    <button class="btn btn-secondary" style="padding:0.35rem 0.65rem; font-size:0.75rem; color:#f87171;" onclick="dawDeleteClip(dawSelectedClip)">🗑️ Remove</button>
                </div>
            `;
        }

        function panLabelForVal(v) {
            if (v < -0.05) return `L ${Math.round(Math.abs(v)*100)}%`;
            if (v > 0.05) return `R ${Math.round(v*100)}%`;
            return 'Center';
        }

        function dawUpdateInspectorInputs() {
            if (!dawSelectedClip) return;
            const c = dawSelectedClip;
            const inTime = document.getElementById('insp_time');
            if (inTime) inTime.value = c.time.toFixed(3);
            const inDur = document.getElementById('insp_dur');
            if (inDur) inDur.value = c.duration.toFixed(3);
            const inSample = document.getElementById('insp_sample_start');
            if (inSample) inSample.value = (c.sampleStart || 0).toFixed(3);
            const inFadeIn = document.getElementById('val_insp_fade_in');
            if (inFadeIn) inFadeIn.textContent = (c.fadeIn || 0).toFixed(2) + 's';
            const inFadeOut = document.getElementById('val_insp_fade_out');
            if (inFadeOut) inFadeOut.textContent = (c.fadeOut || 0).toFixed(2) + 's';
        }

        function dawInspectorChangeTime(val) {
            if (!dawSelectedClip) return;
            dawSelectedClip.time = Math.max(0, parseFloat(val) || 0);
            syncDAWToConfig();
            renderDAWTimeline();
        }

        function dawInspectorNudgeTime(delta) {
            if (!dawSelectedClip) return;
            dawSelectedClip.time = Math.max(0, Math.min(dawTotalDuration() - 0.05, dawSelectedClip.time + delta));
            syncDAWToConfig();
            renderDAWTimeline();
        }

        function dawInspectorChangeDuration(val) {
            if (!dawSelectedClip) return;
            dawSelectedClip.duration = Math.max(0.05, parseFloat(val) || 0.05);
            syncDAWToConfig();
            renderDAWTimeline();
        }

        function dawInspectorChangeSampleStart(val) {
            if (!dawSelectedClip) return;
            dawSelectedClip.sampleStart = Math.max(0, parseFloat(val) || 0);
            syncDAWToConfig();
            renderDAWTimeline();
        }

        function dawInspectorSetFadeIn(val) {
            if (!dawSelectedClip) return;
            dawSelectedClip.fadeIn = val;
            const valBadge = document.getElementById('val_insp_fade_in');
            if (valBadge) valBadge.textContent = val.toFixed(2) + 's';
            const overlay = document.getElementById('fade_in_overlay_' + dawSelectedClip.id);
            if (overlay) overlay.style.width = (val * dawPixelsPerSec) + 'px';
            const handle = document.getElementById('handle_fade_in_' + dawSelectedClip.id);
            if (handle) handle.style.left = (val * dawPixelsPerSec) + 'px';
            syncDAWToConfig();
        }

        function dawInspectorSetFadeOut(val) {
            if (!dawSelectedClip) return;
            dawSelectedClip.fadeOut = val;
            const valBadge = document.getElementById('val_insp_fade_out');
            if (valBadge) valBadge.textContent = val.toFixed(2) + 's';
            const overlay = document.getElementById('fade_out_overlay_' + dawSelectedClip.id);
            if (overlay) overlay.style.width = (val * dawPixelsPerSec) + 'px';
            const handle = document.getElementById('handle_fade_out_' + dawSelectedClip.id);
            if (handle) handle.style.right = (val * dawPixelsPerSec) + 'px';
            syncDAWToConfig();
        }

        function dawInspectorSetVolume(val) {
            if (!dawSelectedClip) return;
            dawSelectedClip.volume = val;
            const valBadge = document.getElementById('val_insp_volume');
            if (valBadge) valBadge.textContent = Math.round(val * 100) + '%';
            const tag = document.getElementById('tag_vol_' + dawSelectedClip.id);
            if (tag) tag.textContent = Math.round(val * 100) + '%';
            syncDAWToConfig();
        }

        function dawInspectorSetPan(val) {
            if (!dawSelectedClip) return;
            dawSelectedClip.pan = val;
            const valBadge = document.getElementById('val_insp_pan');
            if (valBadge) valBadge.textContent = panLabelForVal(val);
            const tag = document.getElementById('tag_pan_' + dawSelectedClip.id);
            const panText = (val < -0.05) ? `L${Math.round(Math.abs(val)*100)}` : (val > 0.05 ? `R${Math.round(val*100)}` : 'C');
            if (tag) tag.textContent = panText;
            syncDAWToConfig();
        }

        function dawInspectorSetPitch(val) {
            if (!dawSelectedClip) return;
            dawSelectedClip.pitch = val;
            syncDAWToConfig();
        }

        function dawInspectorToggleMute() {
            if (!dawSelectedClip) return;
            dawSelectedClip.muted = !dawSelectedClip.muted;
            syncDAWToConfig();
            renderDAWTimeline();
        }

        function dawDuplicateClip(clip) {
            if (!clip) return;
            const newClip = { ...clip };
            newClip.id = `clip_${Date.now().toString(36)}`;
            newClip.time = Math.min(dawTotalDuration() - 0.1, clip.time + clip.duration);
            dawClips.push(newClip);
            syncDAWToConfig();
            dawSelectedClip = newClip;
            renderDAWTimeline();
            showToast('Clip duplicated and placed adjacent', 'success');
        }

        function dawDeleteClip(clip) {
            if (!clip) return;
            const idx = dawClips.findIndex(c => c.id === clip.id);
            if (idx >= 0) dawClips.splice(idx, 1);
            if (dawSelectedClip?.id === clip.id) dawSelectedClip = null;
            syncDAWToConfig();
            renderDAWTimeline();
            showToast('Clip removed from timeline', 'success');
        }

        /* ─── QUICK ADD SOUND MODAL ─── */
        let dawTargetAddTrackIdx = 0;

        function dawOpenAddSoundModal(trackIdx) {
            dawTargetAddTrackIdx = trackIdx !== null && trackIdx !== undefined ? trackIdx : 0;
            const title = document.getElementById('dawAddModalTitle');
            if (title) title.textContent = `📂 Add Sound Cue to: ${dawTracks[dawTargetAddTrackIdx]?.name || 'Playlist'}`;

            populateFolderDropdowns();
            const folderSel = document.getElementById('dawModalFolderSelect');
            if (folderSel && document.getElementById('modalFolderFilter')) {
                folderSel.innerHTML = document.getElementById('modalFolderFilter').innerHTML;
            }

            dawFilterAddModalList();
            const modal = document.getElementById('dawAddSoundModal');
            if (modal) modal.classList.add('active');
        }

        let dawModalPreviewAudio = null;
        let dawModalPlayingKey = null;

        function dawCloseAddSoundModal() {
            if (dawModalPreviewAudio) {
                try { dawModalPreviewAudio.pause(); } catch(e) {}
                dawModalPreviewAudio = null;
            }
            dawModalPlayingKey = null;
            const modal = document.getElementById('dawAddSoundModal');
            if (modal) modal.classList.remove('active');
        }

        function dawPreviewSoundModal(key, btn) {
            if (dawModalPreviewAudio) {
                try { dawModalPreviewAudio.pause(); } catch(e) {}
                dawModalPreviewAudio = null;
            }

            // If already playing this key, toggle stop
            if (dawModalPlayingKey === key) {
                dawModalPlayingKey = null;
                document.querySelectorAll('.daw-modal-preview-btn').forEach(b => {
                    b.innerHTML = '▶ Play';
                    b.classList.remove('active-preview');
                });
                return;
            }

            dawModalPlayingKey = key;
            document.querySelectorAll('.daw-modal-preview-btn').forEach(b => {
                b.innerHTML = '▶ Play';
                b.classList.remove('active-preview');
            });

            if (btn) {
                btn.innerHTML = '🔊 Playing...';
                btn.classList.add('active-preview');
            }

            let relPath = availableSounds[key] || key;
            if (!relPath) return;
            relPath = relPath.replace(/^[\\/]+/, '');

            const audioUrl = '/' + encodeURI(relPath);
            const audio = new Audio(audioUrl);
            audio.volume = 0.85;
            dawModalPreviewAudio = audio;

            audio.onended = () => {
                dawModalPlayingKey = null;
                if (btn) {
                    btn.innerHTML = '▶ Play';
                    btn.classList.remove('active-preview');
                }
            };

            audio.onerror = () => {
                const fallbackUrl = '/audio/' + encodeURIComponent(relPath);
                const a2 = new Audio(fallbackUrl);
                a2.volume = 0.85;
                dawModalPreviewAudio = a2;
                a2.onended = () => {
                    dawModalPlayingKey = null;
                    if (btn) {
                        btn.innerHTML = '▶ Play';
                        btn.classList.remove('active-preview');
                    }
                };
                a2.play().catch(err => {
                    showToast('Could not play audio preview: ' + err, 'error');
                    dawModalPlayingKey = null;
                    if (btn) {
                        btn.innerHTML = '▶ Play';
                        btn.classList.remove('active-preview');
                    }
                });
            };

            audio.play().catch(e => {
                audio.onerror();
            });
        }

        function dawFilterAddModalList() {
            const folder = document.getElementById('dawModalFolderSelect')?.value || '';
            const query = document.getElementById('dawModalSearchInput')?.value || '';
            const filtered = getFilteredSoundList(folder, query);

            const container = document.getElementById('dawModalSoundList');
            if (!container) return;

            if (filtered.length === 0) {
                container.innerHTML = '<div style="text-align:center; padding:2rem; color:var(--text-muted);">No audio files matched.</div>';
                return;
            }

            container.innerHTML = filtered.slice(0, 120).map(key => {
                const isPlaying = dawModalPlayingKey === key;
                const safeKey = key.replace(/'/g, "\\'");
                return `
                <div class="daw-modal-sound-item">
                    <div style="display:flex; flex-direction:column; gap:0.15rem; max-width:380px; cursor:pointer;" onclick="dawPreviewSoundModal('${safeKey}', this.closest('.daw-modal-sound-item').querySelector('.daw-modal-preview-btn'))" title="Click to listen">
                        <span style="font-weight:700; font-size:0.82rem; color:#f8fafc;">${dawSoundDisplayName(key)}</span>
                        <span style="font-size:0.65rem; color:#64748b; font-family:'JetBrains Mono'; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">${key}</span>
                    </div>
                    <div style="display:flex; align-items:center; gap:0.4rem;">
                        <button class="btn btn-secondary daw-modal-preview-btn ${isPlaying ? 'active-preview' : ''}" style="padding:0.25rem 0.65rem; font-size:0.72rem; min-width:65px;" onclick="dawPreviewSoundModal('${safeKey}', this)" title="Listen to sound">
                            ${isPlaying ? '🔊 Playing...' : '▶ Play'}
                        </button>
                        <button class="btn btn-primary" style="padding:0.25rem 0.75rem; font-size:0.72rem;" onclick="dawInsertSoundToTimeline('${safeKey}')" title="Insert sound into playlist">+ Insert</button>
                    </div>
                </div>
            `}).join('');
        }

        function dawInsertSoundToTimeline(key) {
            const trackIdx = dawTargetAddTrackIdx;
            const timePos = dawCurrentTime || 0.0;
            const color = dawGetPhaseColor(timePos);

            const newClip = {
                id: `clip_${Date.now().toString(36)}`,
                key: key,
                time: timePos,
                duration: 1.5,
                sampleStart: 0.0,
                volume: 1.0,
                pan: 0.0,
                fadeIn: 0.0,
                fadeOut: 0.0,
                pitch: 1.0,
                trackIdx: trackIdx,
                muted: false,
                solo: false,
                color: color
            };

            dawClips.push(newClip);
            syncDAWToConfig();
            dawSelectedClip = newClip;
            dawCloseAddSoundModal();
            renderDAWTimeline();
            showToast(`Added ${dawSoundDisplayName(key)} at t=${timePos.toFixed(2)}s on ${dawTracks[trackIdx]?.name}`, 'success');
        }

        /* ─── RULER SCRUBBING ─── */
        function dawRulerClick(e) {
            const rulerTimeline = document.getElementById('dawRulerTimeline');
            if (!rulerTimeline) return;
            const rect = rulerTimeline.getBoundingClientRect();
            const clickX = e.clientX - rect.left;
            const targetTime = Math.max(0, Math.min(clickX / dawPixelsPerSec, dawTotalDuration()));
            dawCurrentTime = targetTime;
            dawUpdatePlayheadPosition();
            dawUpdateTimeDisplay();
            dawHighlightActivePhase();

            if (dawPlaying) {
                dawClearScheduledAudio();
                dawScheduleAudio();
            }
        }

        /* ─── WEB AUDIO API REAL-TIME PLAYBACK ENGINE ─── */
        function dawTogglePlay() {
            if (dawPlaying) {
                dawPause();
            } else {
                dawPlay();
            }
        }

        function dawPlay() {
            if (dawPlaying) return;
            getDawAudioContext();
            dawPlaying = true;
            dawLastTs = performance.now();

            const btn = document.getElementById('dawPlayBtn');
            if (btn) {
                btn.textContent = '⏸ Pause';
                btn.classList.remove('btn-primary');
                btn.classList.add('btn-secondary');
            }

            dawScheduleAudio();
            dawRafId = requestAnimationFrame(dawTick);
        }

        function dawPause() {
            dawPlaying = false;
            const btn = document.getElementById('dawPlayBtn');
            if (btn) {
                btn.textContent = '▶ Play';
                btn.classList.remove('btn-secondary');
                btn.classList.add('btn-primary');
            }
            if (dawRafId) cancelAnimationFrame(dawRafId);
            dawClearScheduledAudio();
            dawStopAllActiveAudio();
        }

        function dawStop() {
            dawPause();
            dawCurrentTime = 0.0;
            dawUpdatePlayheadPosition();
            dawUpdateTimeDisplay();
            dawHighlightActivePhase();
        }

        function dawToggleLoop() {
            dawLooping = !dawLooping;
            const btn = document.getElementById('dawLoopBtn');
            if (btn) {
                btn.style.background = dawLooping ? 'rgba(56,189,248,0.25)' : '';
                btn.style.borderColor = dawLooping ? '#38bdf8' : '';
                btn.style.color = dawLooping ? '#38bdf8' : '';
            }
        }

        function dawTick(ts) {
            if (!dawPlaying) return;
            const dt = (ts - dawLastTs) / 1000 * dawSpeed;
            dawLastTs = ts;
            dawCurrentTime += dt;

            const total = dawTotalDuration();
            if (dawCurrentTime >= total) {
                if (dawLooping) {
                    dawCurrentTime = 0.0;
                    dawClearScheduledAudio();
                    dawScheduleAudio();
                } else {
                    dawCurrentTime = total;
                    dawPause();
                }
            }

            dawUpdatePlayheadPosition();
            dawUpdateTimeDisplay();
            dawHighlightActivePhase();

            if (dawPlaying) {
                dawRafId = requestAnimationFrame(dawTick);
            }
        }

        function dawUpdatePlayheadPosition() {
            const ph = document.getElementById('dawPlayhead');
            if (ph) {
                ph.style.left = (TRACK_HEADER_WIDTH + dawCurrentTime * dawPixelsPerSec) + 'px';
            }
        }

        function dawUpdateTimeDisplay() {
            const clock = document.getElementById('dawTimeClock');
            if (clock) {
                clock.textContent = `${dawFormatTime(dawCurrentTime)} / ${dawFormatTime(dawTotalDuration())}`;
            }

            const badge = document.getElementById('dawTimePhaseBadge');
            if (badge) {
                const cur = dawGetPhaseAtTime(dawCurrentTime);
                if (cur) {
                    const meta = PHASES_METADATA.find(m => m.id === cur.id) || { label: cur.id, color: '#38bdf8' };
                    badge.textContent = meta.label;
                    badge.style.color = meta.color;
                    badge.style.borderColor = meta.color;
                    badge.style.background = meta.color + '20';
                }
            }
        }

        function dawFormatTime(sec) {
            const mins = Math.floor(sec / 60);
            const s = sec % 60;
            return `${mins}:${s.toFixed(3).padStart(6, '0')}`;
        }

        function dawHighlightActivePhase() {
            const absPhases = dawPhaseAbsoluteStarts();
            document.querySelectorAll('.daw-phase-column-backdrop').forEach(el => {
                const pid = el.dataset.phaseId;
                const ph = absPhases.find(p => p.id === pid);
                if (ph && dawCurrentTime >= ph.start && dawCurrentTime < ph.start + ph.dur) {
                    el.classList.add('active-playback');
                } else {
                    el.classList.remove('active-playback');
                }
            });
        }

        /* ─── WEB AUDIO SCHEDULING & SYNTHESIS ─── */
        function dawScheduleAudio() {
            dawClearScheduledAudio();

            const hasSoloTracks = dawTracks.some(t => t.solo);

            dawClips.forEach(clip => {
                if (clip.muted) return;
                const track = dawTracks[clip.trackIdx || 0] || { muted: false, solo: false };
                if (track.muted) return;
                if (hasSoloTracks && !track.solo) return;

                const absStart = clip.time;
                const delaySec = (absStart - dawCurrentTime) / dawSpeed;

                if (delaySec >= 0) {
                    const tid = setTimeout(() => {
                        dawPlayClipNode(clip, 0);
                    }, delaySec * 1000);
                    dawScheduledTimeouts.push(tid);
                } else {
                    // Currently midway through this clip
                    const elapsed = (dawCurrentTime - absStart) * dawSpeed;
                    if (elapsed < clip.duration) {
                        dawPlayClipNode(clip, elapsed);
                    }
                }
            });
        }

        function dawClearScheduledAudio() {
            dawScheduledTimeouts.forEach(id => clearTimeout(id));
            dawScheduledTimeouts.length = 0;
        }

        function dawStopAllActiveAudio() {
            dawActiveAudioSources.forEach(src => {
                try { src.stop(); src.disconnect(); } catch (e) {}
            });
            dawActiveAudioSources.length = 0;
        }

        async function dawPlayClipNode(clip, startOffsetSec = 0) {
            if (!clip.key.startsWith('assets/')) return;
            const ctx = getDawAudioContext();
            if (!ctx) return;

            const url = '/' + clip.key;
            const buf = await dawFetchAudioBuffer(url);
            if (!buf) return;

            try {
                const source = ctx.createBufferSource();
                source.buffer = buf;
                source.playbackRate.value = (clip.pitch || 1.0) * dawSpeed;

                const gainNode = ctx.createGain();
                const panNode = ctx.createStereoPanner ? ctx.createStereoPanner() : null;

                const track = dawTracks[clip.trackIdx || 0] || { volume: 1.0 };
                const targetGain = (clip.volume !== undefined ? clip.volume : 1.0) * (track.volume || 1.0) * dawMasterVolume;
                const duration = clip.duration || buf.duration;
                const sampleStart = (clip.sampleStart || 0.0) + startOffsetSec;
                const fadeIn = clip.fadeIn || 0.0;
                const fadeOut = clip.fadeOut || 0.0;

                const now = ctx.currentTime;
                const remaining = duration - startOffsetSec;
                if (remaining <= 0) return;

                // Mathematical Fade Envelopes
                if (fadeIn > 0 && startOffsetSec < fadeIn) {
                    const startVal = (startOffsetSec / fadeIn) * targetGain;
                    gainNode.gain.setValueAtTime(Math.max(0.0001, startVal), now);
                    gainNode.gain.linearRampToValueAtTime(targetGain, now + (fadeIn - startOffsetSec) / dawSpeed);
                } else {
                    gainNode.gain.setValueAtTime(targetGain, now);
                }

                if (fadeOut > 0) {
                    const fadeOutStart = Math.max(now, now + (duration - fadeOut - startOffsetSec) / dawSpeed);
                    gainNode.gain.setValueAtTime(targetGain, fadeOutStart);
                    gainNode.gain.linearRampToValueAtTime(0.0001, now + remaining / dawSpeed);
                }

                // Stereo Panning
                if (panNode && clip.pan !== undefined) {
                    panNode.pan.value = Math.max(-1.0, Math.min(1.0, clip.pan));
                    source.connect(gainNode);
                    gainNode.connect(panNode);
                    panNode.connect(ctx.destination);
                } else {
                    source.connect(gainNode);
                    gainNode.connect(ctx.destination);
                }

                source.start(0, sampleStart, remaining);
                dawActiveAudioSources.push(source);

                source.onended = () => {
                    const idx = dawActiveAudioSources.indexOf(source);
                    if (idx >= 0) dawActiveAudioSources.splice(idx, 1);
                };
            } catch (err) {
                console.warn("Playback node error:", err);
            }
        }

        async function dawPreviewClipSolo(clip) {
            if (!clip || !clip.key.startsWith('assets/')) {
                showToast('Cannot preview non-asset sound key', 'error');
                return;
            }
            const ctx = getDawAudioContext();
            if (!ctx) return;

            const url = '/' + clip.key;
            const buf = await dawFetchAudioBuffer(url);
            if (!buf) {
                showToast('Loading audio buffer failed: ' + clip.key, 'error');
                return;
            }

            try {
                const source = ctx.createBufferSource();
                source.buffer = buf;
                source.playbackRate.value = clip.pitch || 1.0;

                const gainNode = ctx.createGain();
                const panNode = ctx.createStereoPanner ? ctx.createStereoPanner() : null;

                const targetGain = (clip.volume !== undefined ? clip.volume : 1.0) * dawMasterVolume;
                const duration = clip.duration || buf.duration;
                const sampleStart = clip.sampleStart || 0.0;
                const fadeIn = clip.fadeIn || 0.0;
                const fadeOut = clip.fadeOut || 0.0;
                const now = ctx.currentTime;

                if (fadeIn > 0) {
                    gainNode.gain.setValueAtTime(0.0001, now);
                    gainNode.gain.linearRampToValueAtTime(targetGain, now + fadeIn);
                } else {
                    gainNode.gain.setValueAtTime(targetGain, now);
                }

                if (fadeOut > 0) {
                    const fadeOutStart = now + Math.max(0, duration - fadeOut);
                    gainNode.gain.setValueAtTime(targetGain, fadeOutStart);
                    gainNode.gain.linearRampToValueAtTime(0.0001, now + duration);
                }

                if (panNode && clip.pan !== undefined) {
                    panNode.pan.value = Math.max(-1.0, Math.min(1.0, clip.pan));
                    source.connect(gainNode);
                    gainNode.connect(panNode);
                    panNode.connect(ctx.destination);
                } else {
                    source.connect(gainNode);
                    gainNode.connect(ctx.destination);
                }

                source.start(0, sampleStart, duration);
                showToast(`Auditioning ${dawSoundDisplayName(clip.key)} (Crop Start: ${sampleStart.toFixed(2)}s, Vol: ${Math.round(targetGain*100)}%)`, 'success');
            } catch (e) {
                showToast('Solo preview error: ' + e, 'error');
            }
        }

        /* ─── KEYBOARD SHORTCUTS ─── */
        document.addEventListener('keydown', (e) => {
            const panel = document.getElementById('tab-timeline');
            if (!panel || !panel.classList.contains('active')) return;

            if (e.code === 'Space' && !e.target.matches('input, select, textarea')) {
                e.preventDefault();
                dawTogglePlay();
            }
            if ((e.code === 'KeyS' || e.key === 's' || e.key === 'S') && !e.target.matches('input, select, textarea')) {
                e.preventDefault();
                dawSplitSelectedClip();
            }
            if (e.code === 'KeyD' && (e.ctrlKey || e.metaKey) && !e.target.matches('input, select, textarea')) {
                e.preventDefault();
                if (dawSelectedClip) dawDuplicateClip(dawSelectedClip);
            }
            if (e.code === 'Delete' && dawSelectedClip && !e.target.matches('input, select, textarea')) {
                dawDeleteClip(dawSelectedClip);
            }
        });

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

                const peakFrame = Math.max(0, (p.special_tentacles?.zoom_peak_frame || 11) - 1);
                const flashFrame = Math.max(0, (p.special_tentacles?.flash_trigger_frame !== undefined ? p.special_tentacles.flash_trigger_frame : (p.special_tentacles?.zoom_peak_frame || 11)) - 1);
                const maxZ = p.special_tentacles?.zoom_max || 1.50;
                if (frameIdx <= peakFrame) {
                    const t = frameIdx / Math.max(peakFrame, 1);
                    targetZoom = lerp(1.0, maxZ, easeInOut(t));
                } else {
                    const t = (frameIdx - peakFrame) / Math.max(totalPhaseFrames - peakFrame, 1);
                    targetZoom = lerp(maxZ, 1.0, easeInOut(t));
                }
                targetZoomSpeed = p.special_tentacles?.zoom_speed || 2.5;

                // Violent shake at peak close-up frame
                if (frameIdx === peakFrame) {
                    targetShakeAmp = p.special_tentacles?.peak_shake_amplitude !== undefined ? p.special_tentacles.peak_shake_amplitude : 9.5;
                    shakeFreq = p.special_tentacles?.peak_shake_frequency !== undefined ? p.special_tentacles.peak_shake_frequency : 22.0;
                } else if (frameIdx === peakFrame + 1) {
                    targetShakeAmp = (p.special_tentacles?.peak_shake_amplitude !== undefined ? p.special_tentacles.peak_shake_amplitude : 9.5) * 0.6;
                    shakeFreq = p.special_tentacles?.peak_shake_frequency !== undefined ? p.special_tentacles.peak_shake_frequency : 22.0;
                }

                // Red Flash at chosen flash frame
                if (frameIdx === flashFrame) {
                    flashColor = p.special_tentacles?.flash_color || [180, 20, 20];
                    flashAlpha = ((p.special_tentacles?.flash_peak_alpha !== undefined ? p.special_tentacles.flash_peak_alpha : 220) / 255.0);
                } else if (frameIdx === flashFrame + 1) {
                    flashColor = p.special_tentacles?.flash_color || [180, 20, 20];
                    flashAlpha = ((p.special_tentacles?.flash_peak_alpha !== undefined ? p.special_tentacles.flash_peak_alpha : 220) / 255.0) * 0.45;
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
        elif path == "/api/audio-assets":
            assets = get_all_audio_assets()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"assets": assets}).encode("utf-8"))
            return

        elif path.startswith("/audio/") or path.startswith("/assets/"):
            rel = urllib.parse.unquote(path[7:] if path.startswith("/audio/") else path.lstrip("/"))
            full_path = os.path.join(BASE_DIR, rel)

            if not os.path.abspath(full_path).startswith(os.path.abspath(BASE_DIR)):
                self.send_error(403, "Access Denied")
                return

            if os.path.exists(full_path) and os.path.isfile(full_path):
                file_size = os.path.getsize(full_path)
                range_header = self.headers.get("Range")

                start_byte = 0
                end_byte = file_size - 1

                if range_header and range_header.startswith("bytes="):
                    try:
                        byte_range = range_header.split("=")[1].split("-")
                        if byte_range[0]:
                            start_byte = int(byte_range[0])
                        if len(byte_range) > 1 and byte_range[1]:
                            end_byte = int(byte_range[1])
                    except (ValueError, IndexError):
                        start_byte = 0
                        end_byte = file_size - 1

                if start_byte < 0:
                    start_byte = 0
                if end_byte >= file_size:
                    end_byte = file_size - 1

                content_length = (end_byte - start_byte) + 1

                mime_type = "application/octet-stream"
                if full_path.lower().endswith(".wav"):
                    mime_type = "audio/wav"
                elif full_path.lower().endswith(".mp3"):
                    mime_type = "audio/mpeg"
                elif full_path.lower().endswith(".ogg"):
                    mime_type = "audio/ogg"
                elif full_path.lower().endswith(".flac"):
                    mime_type = "audio/flac"
                elif full_path.lower().endswith(".png"):
                    mime_type = "image/png"
                elif full_path.lower().endswith((".jpg", ".jpeg")):
                    mime_type = "image/jpeg"
                elif full_path.lower().endswith(".webp"):
                    mime_type = "image/webp"

                if range_header:
                    self.send_response(206)
                    self.send_header("Content-Range", f"bytes {start_byte}-{end_byte}/{file_size}")
                else:
                    self.send_response(200)

                self.send_header("Content-Type", mime_type)
                self.send_header("Content-Length", str(content_length))
                self.send_header("Accept-Ranges", "bytes")
                self.end_headers()

                with open(full_path, "rb") as f:
                    f.seek(start_byte)
                    self.wfile.write(f.read(content_length))
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
