#!/usr/bin/env python3
import http.server
import socketserver
import json
import urllib.parse
import os
import sys
import webbrowser
from threading import Timer

# Ensure directories are in sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, "/home/chosen333/Software/V3X-Zulfiqar-Gideon")
sys.path.insert(0, BASE_DIR)

# ── Entity-to-config-file registry ───────────────────────────────────────────
ENTITY_REGISTRY = {
    "player":          {"config": "game_data/player_audio_config.json",         "lock": "game_data/player_audio_config.lock"},
    "skeleton_minion": {"config": "game_data/skeleton_minion_audio_config.json", "lock": "game_data/skeleton_minion_audio_config.lock"},
    "skeleton_zombie": {"config": "game_data/skeleton_zombie_audio_config.json", "lock": "game_data/skeleton_zombie_audio_config.lock"},
    "skeleton_boss":   {"config": "game_data/skeleton_boss_audio_config.json",   "lock": "game_data/skeleton_boss_audio_config.lock"},
    "blood_zombie":    {"config": "game_data/blood_zombie_audio_config.json",    "lock": "game_data/blood_zombie_audio_config.lock"},
    "green_monster":   {"config": "game_data/green_monster_audio_config.json",   "lock": "game_data/green_monster_audio_config.lock"},
    "boss_wizard":     {"config": "game_data/boss_wizard_audio_config.json",     "lock": "game_data/boss_wizard_audio_config.lock"},
    "bat":             {"config": "game_data/bat_audio_config.json",             "lock": "game_data/bat_audio_config.lock"},
}
DEFAULT_EMPTY_CONFIG = {"sounds": {}, "states": {}, "enhanced_states": {}}

def extract_jukebox_sounds(main_py_path="main.py"):
    """
    Parse main.py to dynamically extract the default jukebox sound library mappings.
    """
    sounds = {}
    if not os.path.exists(main_py_path):
        return sounds
    import re
    try:
        with open(main_py_path, "r") as f:
            content = f.read()
        
        # Extract the audio dictionary literal
        match = re.search(r"audio\s*=\s*\{([^\}]+)\}", content)
        if match:
            audio_section = match.group(1)
            # Match "name": "path" or 'name': 'path'
            entries = re.findall(r"[\"']([^\"']+)[\"']\s*:\s*[\"']([^\"']+)[\"']", audio_section)
            for name, path in entries:
                sounds[name] = path
    except Exception as e:
        print(f"[Mixer Editor] Warning: Failed to parse jukebox sounds from {main_py_path}: {e}")
    return sounds

HTML_CONTENT = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Pixel Runner - Audio Configurator</title>
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
            --accent-cyan: #06b6d4;
            --accent-cyan-glow: rgba(6, 182, 212, 0.3);
            --accent-purple: #8b5cf6;
            --accent-green: #10b981;
            --accent-green-glow: rgba(16, 185, 129, 0.3);
            --accent-orange: #f59e0b;
            --accent-red: #ef4444;
            --accent-red-glow: rgba(239, 68, 68, 0.3);
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
            font-family: 'Outfit', sans-serif;
            scrollbar-width: thin;
            scrollbar-color: rgba(255, 255, 255, 0.2) transparent;
        }

        body {
            background-color: var(--bg-color);
            background-image: 
                radial-gradient(at 0% 0%, rgba(139, 92, 246, 0.08) 0px, transparent 50%),
                radial-gradient(at 100% 100%, rgba(6, 182, 212, 0.08) 0px, transparent 50%);
            color: var(--text-primary);
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            overflow-x: hidden;
        }

        header {
            background: rgba(15, 23, 42, 0.8);
            backdrop-filter: blur(12px);
            border-bottom: 1px solid var(--border-color);
            padding: 1rem 2rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
            position: sticky;
            top: 0;
            z-index: 100;
        }

        .header-title-container h1 {
            font-family: 'Space Grotesk', sans-serif;
            font-size: 1.5rem;
            font-weight: 700;
            letter-spacing: -0.025em;
            background: linear-gradient(to right, #00f0ff, #b500ff);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        .header-title-container p {
            font-size: 0.85rem;
            color: var(--text-secondary);
            margin-top: 0.1rem;
        }

        .header-actions {
            display: flex;
            align-items: center;
            gap: 1.5rem;
        }

        .lock-badge {
            display: flex;
            align-items: center;
            gap: 0.6rem;
            padding: 0.5rem 1rem;
            border-radius: 9999px;
            font-size: 0.85rem;
            font-weight: 600;
            background: rgba(17, 24, 39, 0.6);
            border: 1px solid var(--border-color);
            transition: all 0.3s ease;
        }

        .lock-badge.valid {
            border-color: var(--accent-green);
            box-shadow: 0 0 10px var(--accent-green-glow);
            color: var(--accent-green);
        }

        .lock-badge.invalid {
            border-color: var(--accent-red);
            box-shadow: 0 0 10px var(--accent-red-glow);
            color: var(--accent-red);
        }

        .lock-badge.unsaved {
            border-color: var(--accent-orange);
            color: var(--accent-orange);
        }

        .badge-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background-color: currentColor;
            display: inline-block;
        }

        .btn {
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid var(--border-color);
            color: var(--text-primary);
            padding: 0.6rem 1.2rem;
            border-radius: 8px;
            font-weight: 600;
            font-size: 0.9rem;
            cursor: pointer;
            transition: all 0.2s ease;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }

        .btn:hover {
            background: rgba(255, 255, 255, 0.1);
            border-color: var(--border-hover);
        }

        .btn-primary {
            background: var(--accent-cyan);
            border-color: var(--accent-cyan);
            color: #000;
            box-shadow: 0 4px 12px var(--accent-cyan-glow);
        }

        .btn-primary:hover {
            background: #0891b2;
            border-color: #0891b2;
            box-shadow: 0 6px 16px var(--accent-cyan-glow);
        }

        .btn-danger {
            color: var(--accent-red);
        }

        .btn-danger:hover {
            background: rgba(239, 68, 68, 0.1);
            border-color: var(--accent-red);
        }

        .main-container {
            display: grid;
            grid-template-columns: 350px 1fr;
            gap: 1.5rem;
            padding: 1.5rem;
            flex: 1;
            max-width: 1600px;
            margin: 0 auto;
            width: 100%;
        }

        .panel {
            background: var(--panel-bg);
            backdrop-filter: blur(12px);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 1.5rem;
            display: flex;
            flex-direction: column;
            gap: 1.5rem;
            overflow: hidden;
        }

        .panel-title {
            font-family: 'Space Grotesk', sans-serif;
            font-size: 1.1rem;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 0.6rem;
            border-bottom: 1px solid var(--border-color);
            padding-bottom: 0.8rem;
        }

        /* Mixer Board Styling */
        .mixer-section {
            display: flex;
            flex-direction: column;
            gap: 1.2rem;
        }

        .volume-control {
            display: flex;
            flex-direction: column;
            gap: 0.4rem;
        }

        .volume-header {
            display: flex;
            justify-content: space-between;
            font-size: 0.85rem;
            color: var(--text-secondary);
            font-weight: 500;
        }

        .volume-slider-row {
            display: flex;
            align-items: center;
            gap: 0.8rem;
        }

        .slider {
            flex: 1;
            height: 6px;
            background: rgba(255, 255, 255, 0.1);
            border-radius: 3px;
            outline: none;
            -webkit-appearance: none;
            cursor: pointer;
        }

        .slider::-webkit-slider-thumb {
            -webkit-appearance: none;
            width: 16px;
            height: 16px;
            border-radius: 50%;
            background: var(--accent-cyan);
            box-shadow: 0 0 8px var(--accent-cyan-glow);
            transition: transform 0.1s;
        }

        .slider::-webkit-slider-thumb:hover {
            transform: scale(1.2);
        }

        .volume-val {
            font-family: 'Space Grotesk', sans-serif;
            font-size: 0.9rem;
            font-weight: 600;
            width: 40px;
            text-align: right;
        }

        .search-box {
            background: rgba(255, 255, 255, 0.03);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 0.6rem;
            color: var(--text-primary);
            font-size: 0.9rem;
            width: 100%;
            outline: none;
            transition: all 0.2s;
        }

        .search-box:focus {
            border-color: var(--accent-cyan);
            background: rgba(255, 255, 255, 0.05);
        }

        .track-mixer-list {
            display: flex;
            flex-direction: column;
            gap: 0.8rem;
            overflow-y: auto;
            max-height: 400px;
            padding-right: 0.5rem;
        }

        .track-mixer-item {
            background: rgba(255, 255, 255, 0.02);
            border: 1px solid rgba(255, 255, 255, 0.04);
            border-radius: 8px;
            padding: 0.8rem;
            display: flex;
            flex-direction: column;
            gap: 0.4rem;
            transition: all 0.2s ease;
        }

        .track-mixer-item:hover {
            border-color: var(--border-hover);
            background: rgba(255, 255, 255, 0.04);
        }

        .track-info {
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .track-name {
            font-size: 0.85rem;
            font-weight: 600;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
            max-width: 180px;
        }

        .play-icon-btn {
            background: transparent;
            border: none;
            color: var(--accent-cyan);
            cursor: pointer;
            font-size: 1.1rem;
            display: flex;
            align-items: center;
            justify-content: center;
            width: 24px;
            height: 24px;
            border-radius: 50%;
            transition: all 0.2s;
        }

        .play-icon-btn:hover {
            background: rgba(6, 182, 212, 0.1);
            transform: scale(1.1);
        }

        /* Timeline / SFX Configurator Column */
        .timeline-controls {
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 1rem;
            background: rgba(255, 255, 255, 0.02);
            padding: 1rem;
            border-radius: 8px;
            border: 1px solid var(--border-color);
        }

        .control-group {
            display: flex;
            align-items: center;
            gap: 0.8rem;
        }

        .control-label {
            font-size: 0.85rem;
            color: var(--text-secondary);
            font-weight: 500;
        }

        select {
            background: #111827;
            border: 1px solid var(--border-color);
            color: var(--text-primary);
            padding: 0.5rem 1rem;
            border-radius: 8px;
            outline: none;
            cursor: pointer;
            font-weight: 500;
        }

        select:focus {
            border-color: var(--accent-cyan);
        }

        .toggle-group {
            display: flex;
            background: rgba(255, 255, 255, 0.05);
            padding: 0.2rem;
            border-radius: 8px;
            border: 1px solid var(--border-color);
        }

        .toggle-btn {
            background: transparent;
            border: none;
            color: var(--text-secondary);
            padding: 0.4rem 1rem;
            border-radius: 6px;
            font-size: 0.85rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
        }

        .toggle-btn.active {
            background: var(--accent-cyan);
            color: #000;
        }

        /* Live Animation Preview Widget */
        .live-anim-widget {
            display: flex;
            align-items: center;
            gap: 1rem;
            background: rgba(0, 0, 0, 0.5);
            border: 1px solid var(--border-color);
            padding: 0.6rem 1rem;
            border-radius: 10px;
            transition: all 0.3s ease;
        }

        .live-anim-widget.active {
            border-color: var(--accent-cyan);
            box-shadow: 0 0 16px rgba(6, 182, 212, 0.3);
            background: rgba(6, 182, 212, 0.08);
        }

        .live-anim-box {
            width: 120px;
            height: 120px;
            background: rgba(0, 0, 0, 0.7);
            border: 1.5px solid rgba(255, 255, 255, 0.15);
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            position: relative;
            overflow: hidden;
            box-shadow: inset 0 0 12px rgba(0, 0, 0, 0.8);
        }

        .live-anim-box img {
            max-width: 100%;
            max-height: 100%;
            width: auto;
            height: auto;
            object-fit: contain;
            image-rendering: pixelated;
            filter: drop-shadow(0 4px 8px rgba(0,0,0,0.8));
        }

        .live-sound-txt {
            color: var(--text-secondary);
            font-size: 0.8rem;
            font-weight: 700;
            transition: color 0.15s ease, text-shadow 0.15s ease;
        }

        .live-sound-txt.active-sound {
            color: var(--accent-cyan);
            text-shadow: 0 0 8px rgba(6, 182, 212, 0.6);
        }

        .live-anim-info {
            display: flex;
            flex-direction: column;
            gap: 0.2rem;
            font-size: 0.85rem;
        }

        .live-frame-txt {
            font-family: 'Space Grotesk', sans-serif;
            font-weight: 700;
            font-size: 0.95rem;
            color: var(--text-primary);
        }

        .live-speed-txt {
            color: var(--accent-cyan);
            font-size: 0.8rem;
            font-weight: 600;
        }

        .frame-card.preview-active {
            border-color: var(--accent-cyan) !important;
            box-shadow: 0 0 16px rgba(6, 182, 212, 0.35) !important;
            background: rgba(6, 182, 212, 0.08) !important;
            transform: translateY(-2px);
        }

        .timeline-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
            gap: 1rem;
            overflow-y: auto;
            flex: 1;
            padding-right: 0.5rem;
        }

        .frame-card {
            background: rgba(255, 255, 255, 0.02);
            border: 1px solid var(--border-color);
            border-radius: 10px;
            padding: 1rem;
            display: flex;
            flex-direction: column;
            gap: 0.8rem;
            transition: all 0.2s;
        }

        .frame-card:hover {
            border-color: rgba(255, 255, 255, 0.15);
            background: rgba(255, 255, 255, 0.03);
        }

        .frame-card.has-sound {
            border-color: var(--accent-cyan-glow);
            box-shadow: 0 0 10px rgba(6, 182, 212, 0.05);
        }

        .frame-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .frame-num {
            font-family: 'Space Grotesk', sans-serif;
            font-size: 0.9rem;
            font-weight: 700;
            background: rgba(255, 255, 255, 0.06);
            padding: 0.2rem 0.6rem;
            border-radius: 4px;
        }

        .frame-sound-label {
            font-size: 0.75rem;
            color: var(--text-secondary);
        }

        .assigned-sound-area {
            display: flex;
            align-items: center;
            justify-content: space-between;
            background: rgba(0, 0, 0, 0.2);
            padding: 0.5rem 0.8rem;
            border-radius: 6px;
            min-height: 38px;
        }

        .sound-id-text {
            font-size: 0.85rem;
            font-weight: 600;
            color: var(--accent-cyan);
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
            max-width: 180px;
        }

        .sound-id-text.empty {
            color: var(--text-secondary);
            font-style: italic;
            font-weight: 400;
        }

        .frame-card-actions {
            display: flex;
            gap: 0.5rem;
        }

        .frame-card-actions button {
            flex: 1;
            padding: 0.4rem;
            font-size: 0.8rem;
            border-radius: 6px;
        }

        .frame-preview-img-container {
            display: flex;
            align-items: center;
            justify-content: center;
            background: rgba(0, 0, 0, 0.35);
            border: 1px solid rgba(255, 255, 255, 0.05);
            border-radius: 6px;
            height: 90px;
            padding: 6px;
            position: relative;
            overflow: hidden;
        }

        .frame-preview-img {
            max-height: 100%;
            max-width: 100%;
            object-fit: contain;
            image-rendering: pixelated;
            filter: drop-shadow(0 4px 8px rgba(0, 0, 0, 0.6));
            transition: transform 0.2s ease;
        }

        .frame-preview-img:hover {
            transform: scale(1.15);
        }

        /* Modal Preview Container */
        .modal-frame-preview {
            display: flex;
            justify-content: center;
            margin-bottom: 1rem;
        }

        .modal-frame-preview .frame-preview-img-container {
            width: 120px;
            height: 120px;
        }

        /* Asset Browser Modal */
        .modal-overlay {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(9, 13, 22, 0.85);
            backdrop-filter: blur(8px);
            z-index: 1000;
            display: flex;
            justify-content: center;
            align-items: center;
            opacity: 0;
            pointer-events: none;
            transition: opacity 0.3s ease;
        }

        .modal-overlay.open {
            opacity: 1;
            pointer-events: auto;
        }

        .modal {
            background: #0f172a;
            border: 1px solid var(--border-color);
            border-radius: 12px;
            width: 760px;
            max-width: 95%;
            max-height: 90vh;
            display: flex;
            flex-direction: column;
            box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.5);
            transform: scale(0.95);
            transition: transform 0.3s ease;
        }

        .modal-overlay.open .modal {
            transform: scale(1);
        }

        .modal-header {
            padding: 1rem 1.5rem;
            border-bottom: 1px solid var(--border-color);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .modal-title {
            font-family: 'Space Grotesk', sans-serif;
            font-size: 1.1rem;
            font-weight: 600;
        }

        .modal-close {
            background: transparent;
            border: none;
            color: var(--text-secondary);
            font-size: 1.5rem;
            cursor: pointer;
        }

        .modal-close:hover {
            color: var(--text-primary);
        }

        .modal-body {
            padding: 1.2rem 1.5rem;
            overflow-y: auto;
            display: flex;
            flex-direction: column;
            gap: 1rem;
        }

        .tabs-header {
            display: flex;
            border-bottom: 1px solid var(--border-color);
        }

        .tab-link {
            background: transparent;
            border: none;
            color: var(--text-secondary);
            padding: 0.6rem 1.2rem;
            font-weight: 600;
            font-size: 0.9rem;
            cursor: pointer;
            border-bottom: 2px solid transparent;
        }

        .tab-link.active {
            color: var(--accent-cyan);
            border-bottom-color: var(--accent-cyan);
        }

        .tab-content {
            display: none;
            flex-direction: column;
            gap: 0.8rem;
        }

        .tab-content.active {
            display: flex;
        }

        .asset-list-item {
            background: rgba(255, 255, 255, 0.01);
            border: 1px solid rgba(255, 255, 255, 0.04);
            border-radius: 8px;
            padding: 0.6rem 1rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
            transition: all 0.2s;
        }

        .asset-list-item:hover {
            background: rgba(255, 255, 255, 0.03);
            border-color: var(--border-hover);
        }

        .asset-list-item.selected {
            background: rgba(6, 182, 212, 0.12);
            border-color: var(--accent-cyan);
        }

        .asset-info {
            display: flex;
            flex-direction: column;
            gap: 0.1rem;
        }

        .asset-name {
            font-size: 0.85rem;
            font-weight: 600;
        }

        .asset-path {
            font-size: 0.75rem;
            color: var(--text-secondary);
        }

        .asset-actions {
            display: flex;
            align-items: center;
            gap: 0.6rem;
        }

        .register-form {
            display: flex;
            flex-direction: column;
            gap: 0.8rem;
            background: rgba(255, 255, 255, 0.02);
            padding: 1rem;
            border-radius: 8px;
            border: 1px solid var(--border-color);
        }

        .form-row {
            display: flex;
            flex-direction: column;
            gap: 0.4rem;
        }

        .form-row label {
            font-size: 0.8rem;
            color: var(--text-secondary);
            font-weight: 500;
        }

        .form-input {
            background: #111827;
            border: 1px solid var(--border-color);
            padding: 0.5rem 0.8rem;
            border-radius: 6px;
            color: var(--text-primary);
            outline: none;
        }

        .form-input:focus {
            border-color: var(--accent-cyan);
        }

        /* Overlay warning for verification check failed */
        .verification-alert {
            display: none;
            background: rgba(239, 68, 68, 0.1);
            border: 1px solid var(--accent-red);
            border-radius: 8px;
            padding: 1rem;
            margin-bottom: 1.5rem;
            align-items: center;
            gap: 1rem;
        }

        .verification-alert-text {
            flex: 1;
            font-size: 0.85rem;
            color: #fca5a5;
        }

        /* Entity Selector Bar */
        .entity-selector-bar {
            display: flex;
            align-items: center;
            gap: 0.75rem;
            padding: 0.75rem 1rem;
            background: rgba(255,255,255,0.025);
            border: 1px solid var(--border-color);
            border-radius: 10px;
            margin-bottom: 1rem;
            flex-wrap: wrap;
        }

        .entity-chips {
            display: flex;
            flex-wrap: wrap;
            gap: 0.4rem;
            flex: 1;
        }

        .entity-chip {
            padding: 0.3rem 0.8rem;
            border-radius: 20px;
            font-size: 0.78rem;
            font-weight: 700;
            cursor: pointer;
            border: 1.5px solid transparent;
            transition: all 0.18s;
            background: rgba(255,255,255,0.04);
            color: var(--text-secondary);
            letter-spacing: 0.02em;
        }

        .entity-chip:hover {
            background: rgba(255,255,255,0.08);
            color: var(--text-primary);
        }

        .entity-chip.active {
            color: #000;
            font-weight: 800;
        }
    </style>
</head>
<body>
    <audio id="preview-player"></audio>

    <header>
        <div class="header-title-container">
            <h1>RUNNER: AUDIO MIXER & SFX EDITOR</h1>
            <p>Modify and preview character frame-by-frame triggers and volumes</p>
        </div>
        <div class="header-actions">
            <div id="lock-status" class="lock-badge valid">
                <span class="badge-dot"></span>
                <span id="lock-text">LOCKED & SECURED</span>
            </div>
            <button id="revert-btn" class="btn btn-danger">Revert</button>
            <button id="save-btn" class="btn btn-primary">Save Changes</button>
        </div>
    </header>

    <div class="main-container">
        <!-- Volume Mixer Column (Left) -->
        <div class="panel">
            <div class="panel-title">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 6V18M6 10v4M18 8v8"/></svg>
                Volume Console
            </div>

            <div class="mixer-section">
                <!-- Master Volume -->
                <div class="volume-control">
                    <div class="volume-header">
                        <span>Master Volume</span>
                        <span id="master-val" class="volume-val">1.0</span>
                    </div>
                    <div class="volume-slider-row">
                        <input type="range" id="master-slider" class="slider" min="0" max="1" step="0.05" value="1.0">
                    </div>
                </div>

                <!-- Music Volume -->
                <div class="volume-control">
                    <div class="volume-header">
                        <span>Music Volume</span>
                        <span id="music-val" class="volume-val">0.5</span>
                    </div>
                    <div class="volume-slider-row">
                        <input type="range" id="music-slider" class="slider" min="0" max="1" step="0.05" value="0.5">
                    </div>
                </div>

                <!-- SFX Volume -->
                <div class="volume-control">
                    <div class="volume-header">
                        <span>SFX Volume</span>
                        <span id="sfx-val" class="volume-val">0.8</span>
                    </div>
                    <div class="volume-slider-row">
                        <input type="range" id="sfx-slider" class="slider" min="0" max="1" step="0.05" value="0.8">
                    </div>
                </div>
            </div>

            <div class="panel-title" style="margin-top: 1rem; border-bottom: 1px solid var(--border-color);">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
                Track Volumes
            </div>

            <div style="display: flex; gap: 0.5rem; margin-bottom: 0.75rem;">
                <input type="text" id="mixer-search" class="search-box" style="margin-bottom:0; flex: 1;" placeholder="Search registered tracks...">
                <button class="btn btn-secondary" style="padding: 0.4rem 0.6rem; font-size: 0.8rem; white-space: nowrap;" onclick="openAudioBrowserModal()" title="Browse raw audio files and register new sounds">📁 Browse Audios</button>
            </div>

            <div id="track-volumes-list" class="track-mixer-list">
                <!-- Dynamic List -->
            </div>
        </div>

        <!-- Frame Timeline Column (Right) -->
        <div class="panel">
            <!-- Alert bar if config is invalid -->
            <div id="alert-bar" class="verification-alert">
                <span style="font-weight: 700; color: var(--accent-red)">Out of Sync:</span>
                <span id="alert-text" class="verification-alert-text">External changes detected. Locking required before run.</span>
            </div>

            <!-- Entity Selector Bar -->
            <div class="entity-selector-bar">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>
                <span class="control-label" style="white-space:nowrap; font-weight:700; color:var(--text-primary);">Entity:</span>
                <div id="entity-chips" class="entity-chips"></div>
            </div>

            <div class="timeline-controls">
                <div class="control-group" style="flex-wrap: wrap; gap: 0.6rem; align-items: center;">
                    <span class="control-label">Animation State:</span>
                    <select id="state-select"></select>
                    <button id="btn-preview-state" class="btn btn-primary" onclick="toggleAnimationPreview()" title="Play animation in real-time with frame sound triggers" style="padding: 0.45rem 0.9rem; font-size: 0.85rem; display: inline-flex; align-items: center; gap: 0.4rem;">
                        <span id="preview-btn-icon">▶</span>
                        <span id="preview-btn-text">Preview</span>
                    </button>
                    
                    <!-- Speed Controls -->
                    <div style="display: flex; align-items: center; gap: 0.4rem; background: rgba(0,0,0,0.3); padding: 0.25rem 0.6rem; border-radius: 6px; border: 1px solid var(--border-color);">
                        <span class="control-label" style="font-size:0.75rem; white-space: nowrap;">Speed:</span>
                        <input type="range" id="preview-speed-slider" class="slider" min="0.2" max="4.0" step="0.1" value="1.0" style="width: 75px;" oninput="onSpeedSliderChange(this.value)">
                        <span id="preview-speed-val" style="font-size: 0.8rem; font-weight: 700; color: var(--accent-cyan); min-width: 32px;">1.0x</span>
                        <button class="btn btn-secondary" style="padding: 0.15rem 0.4rem; font-size: 0.7rem;" onclick="setSpeedPreset(1.0)">1x</button>
                        <button class="btn btn-secondary" style="padding: 0.15rem 0.4rem; font-size: 0.7rem;" onclick="setSpeedPreset(1.5)">1.5x</button>
                        <button class="btn btn-secondary" style="padding: 0.15rem 0.4rem; font-size: 0.7rem;" onclick="setSpeedPreset(2.0)">2x</button>
                    </div>
                </div>

                <!-- Live Animation Preview Box -->
                <div id="live-anim-widget" class="live-anim-widget">
                    <div class="live-anim-box">
                        <img id="live-anim-img" src="" alt="Frame Preview" onerror="this.style.opacity='0';" />
                    </div>
                    <div class="live-anim-info">
                        <span id="live-anim-frame-num" class="live-frame-txt">Frame 0 / 0</span>
                        <span id="live-anim-speed-txt" class="live-speed-txt">Ready</span>
                        <span id="live-sound-txt" class="live-sound-txt">🔊 No Sound</span>
                    </div>
                </div>

                <div id="variant-toggle" class="toggle-group">
                    <button id="btn-std" class="toggle-btn active">Standard</button>
                    <button id="btn-enh" class="toggle-btn">Enhanced</button>
                </div>
            </div>

            <div id="timeline-grid" class="timeline-grid">
                <!-- Renders dynamically -->
            </div>
        </div>
    </div>

    <!-- Sound Assigner Dialog Modal -->
    <div id="assign-modal" class="modal-overlay">
        <div class="modal">
            <div class="modal-header">
                <h3 class="modal-title" id="modal-title-text">Assign Sound to Frame</h3>
                <button class="modal-close" onclick="closeModal()">&times;</button>
            </div>
            <div class="modal-body">
                <div class="modal-frame-preview">
                    <div class="frame-preview-img-container">
                        <img id="modal-frame-img" class="frame-preview-img" src="" alt="Frame Preview" onerror="this.parentElement.style.display='none';" />
                    </div>
                </div>
                <div class="tabs-header">
                    <button class="tab-link active" onclick="switchTab(event, 'tab-registered')">Registered Sounds</button>
                    <button class="tab-link" onclick="switchTab(event, 'tab-raw')">Browse Audio Assets</button>
                </div>

                <!-- Tab 1: Registered Sounds -->
                <div id="tab-registered" class="tab-content active">
                    <input type="text" id="reg-sound-search" class="search-box" placeholder="Search sound keys..." oninput="filterRegisteredSounds()">
                    <div id="registered-sounds-list" class="track-mixer-list" style="min-height: 200px; max-height: 260px; overflow-y: auto; background: rgba(0, 0, 0, 0.35); border: 1px solid var(--border-color); border-radius: 8px; padding: 0.5rem;">
                        <!-- Dynamic -->
                    </div>
                </div>

                <!-- Tab 2: Raw Audio Assets -->
                <div id="tab-raw" class="tab-content">
                    <div style="display: flex; gap: 0.5rem; margin-bottom: 0.5rem; flex-wrap: wrap; align-items: center;">
                        <select id="raw-folder-select" class="form-input" style="flex: 1; min-width: 130px; font-size: 0.8rem;" onchange="filterRawAssets()">
                            <option value="">All Folders</option>
                        </select>
                        <input type="text" id="raw-sound-search" class="search-box" style="flex: 1.5; margin-bottom: 0;" placeholder="Search audio filename or path..." oninput="filterRawAssets()">
                    </div>
                    <div id="raw-asset-count" style="font-size: 0.75rem; color: var(--text-secondary); margin-bottom: 0.4rem; font-weight: 500;"></div>
                    <div id="raw-assets-list" class="track-mixer-list" style="min-height: 200px; max-height: 260px; overflow-y: auto; background: rgba(0, 0, 0, 0.35); border: 1px solid var(--border-color); border-radius: 8px; padding: 0.5rem;">
                        <!-- Dynamic -->
                    </div>

                    <div class="register-form" style="margin-top: 0.8rem;">
                        <div style="font-size: 0.85rem; font-weight: 600; color: var(--accent-cyan); margin-bottom: 0.2rem; display: flex; align-items: center; justify-content: space-between;">
                            <span>Register Selected File as Sound ID</span>
                            <span id="register-status-badge" style="font-size: 0.75rem; color: var(--accent-green); display: none;">✓ Registered!</span>
                        </div>
                        <div class="form-row">
                            <label>Selected Asset Path:</label>
                            <div style="display: flex; gap: 0.4rem; position: relative;">
                                <input type="text" id="new-sound-path" class="form-input" style="flex: 1;" list="raw-assets-datalist" placeholder="Type, paste, or select audio asset path..." oninput="onRawPathInputChange(this.value)">
                                <datalist id="raw-assets-datalist"></datalist>
                                <button class="play-icon-btn" style="padding: 0.4rem 0.7rem;" onclick="previewSelectedRawPath()" title="Preview Selected Audio">&#9658;</button>
                            </div>
                        </div>
                        <div class="form-row">
                            <label>New Sound ID / Alias:</label>
                            <input type="text" id="new-sound-alias" class="form-input" placeholder="e.g. boss_roar">
                        </div>
                        <div style="display: flex; gap: 0.5rem; justify-content: flex-end; margin-top: 0.4rem;">
                            <button class="btn btn-secondary" onclick="registerOnlyAsset()" style="padding: 0.4rem 0.9rem;">Register Only</button>
                            <button id="btn-register-assign" class="btn btn-primary" onclick="registerAndAssignAsset()" style="padding: 0.4rem 0.9rem;">Register & Assign</button>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script>
        // ── Per-Entity Animation Metadata ──────────────────────────────────────
        // pad: zero-pad digits (0 = no pad, 2 = 2-digit zero-pad)
        // offset: 0 = 0-indexed files, 1 = 1-indexed files
        // has_variants: true = show Standard/Enhanced toggle
        const ENTITY_META = {
            player: {
                label:"Shadow Warrior", icon:"⚔️", color:"#06b6d4", has_variants:true, offset:1,
                states:{
                    IDLE:          {frames:{standard:12,enhanced:18}, pad:0, pattern:{standard:"assets/shadow_warrior/idle/idle_{}.png",          enhanced:"assets/shadow_warrior/e_idle/e_idle_{}.png"}},
                    RUN:           {frames:{standard:10,enhanced:10}, pad:0, pattern:{standard:"assets/shadow_warrior/run/run_{}.png",            enhanced:"assets/shadow_warrior/e_run/e_run_{}.png"}},
                    JUMP_UP:       {frames:{standard:3, enhanced:3},  pad:0, pattern:{standard:"assets/shadow_warrior/jump_up_loop/jump_up_loop_{}.png", enhanced:"assets/shadow_warrior/e_jump_up/e_jump_up_{}.png"}},
                    JUMP_DOWN:     {frames:{standard:3, enhanced:3},  pad:0, pattern:{standard:"assets/shadow_warrior/jump_down_loop/jump_down_loop_{}.png", enhanced:"assets/shadow_warrior/e_jump_down/e_jump_down_{}.png"}},
                    ATTACK_THRUST: {frames:{standard:9, enhanced:14}, pad:0, pattern:{standard:"assets/shadow_warrior/1_atk/1_atk_{}.png",       enhanced:"assets/shadow_warrior/e_1_atk/e_1_atk_{}.png"}},
                    ATTACK_SMASH:  {frames:{standard:17,enhanced:22}, pad:0, pattern:{standard:"assets/shadow_warrior/2_atk/2_atk_{}.png",       enhanced:"assets/shadow_warrior/e_2_atk/e_2_atk_{}.png"}},
                    ATTACK_POWER:  {frames:{standard:23,enhanced:35}, pad:0, pattern:{standard:"assets/shadow_warrior/3_atk/3_atk_{}.png",       enhanced:"assets/shadow_warrior/e_3_atk/e_3_atk_{}.png"}},
                    HURT:          {frames:{standard:6, enhanced:7},  pad:0, pattern:{standard:"assets/shadow_warrior/take_hit/take_hit_{}.png", enhanced:"assets/shadow_warrior/e_take_hit/e_take_hit_{}.png"}},
                    DEATH:         {frames:{standard:12,enhanced:12}, pad:0, pattern:{standard:"assets/shadow_warrior/death/death_{}.png",        enhanced:"assets/shadow_warrior/death/death_{}.png"}},
                    DEFEND:        {frames:{standard:7, enhanced:6},  pad:0, pattern:{standard:"assets/shadow_warrior/defend/defend_{}.png",      enhanced:"assets/shadow_warrior/e_defend/e_defend_{}.png"}},
                    ROLL:          {frames:{standard:8, enhanced:8},  pad:0, pattern:{standard:"assets/shadow_warrior/roll/roll_{}.png",          enhanced:"assets/shadow_warrior/roll/roll_{}.png"}},
                    DASH:          {frames:{standard:12,enhanced:12}, pad:0, pattern:{standard:"assets/shadow_warrior/dash/dash_{}.png",          enhanced:"assets/shadow_warrior/dash/dash_{}.png"}},
                    SPECIAL_ATTACK:{frames:{standard:34,enhanced:19}, pad:0, pattern:{standard:"assets/shadow_warrior/sp_atk/sp_atk_{}.png",    enhanced:"assets/shadow_warrior/e_sp_atk/e_sp_atk_{}.png"}},
                    TRANSFORM:     {frames:{standard:37,enhanced:37}, pad:0, pattern:{standard:"assets/shadow_warrior/transform/transform_{}.png",enhanced:"assets/shadow_warrior/transform/transform_{}.png"}},
                }
            },
            skeleton_minion: {
                label:"Skeleton Minion", icon:"💀", color:"#e2e8f0", has_variants:false, offset:0,
                states:{
                    IDLE:  {frames:8,  pad:0, pattern:"assets/skeleton/Skeleton_01_White_Idle/skeleton-idle_{}.png"},
                    CHASE: {frames:10, pad:2, pattern:"assets/skeleton/Skeleton_01_White_Walk/skeleton-walk_{}.png"},
                    ATTACK:{frames:10, pad:2, pattern:"assets/skeleton/Skeleton_01_White_Attack1/skeleton-atk2_{}.png"},
                    HURT:  {frames:5,  pad:0, pattern:"assets/skeleton/Skeleton_01_White_Hurt/skeleton-hurt_{}.png"},
                    DEATH: {frames:13, pad:2, pattern:"assets/skeleton/Skeleton_01_White_Die/skeleton-death_{}.png"},
                }
            },
            skeleton_zombie: {
                label:"Skeleton Zombie", icon:"🧟", color:"#86efac", has_variants:false, offset:0,
                states:{
                    IDLE:  {frames:8,  pad:0, pattern:"assets/graphics/SkeletonZombie/Idle/skeletonZombie_{}.png"},
                    CHASE: {frames:10, pad:2, pattern:"assets/graphics/SkeletonZombie/Chase/skeletonZombie_chase_{}.png"},
                    ATTACK:{frames:23, pad:2, pattern:"assets/graphics/SkeletonZombie/Attack/skeletonZombie_attack_{}.png"},
                    HURT:  {frames:3,  pad:0, pattern:"assets/graphics/SkeletonZombie/Hurt/skeletonZombie_die_{}.png"},
                }
            },
            skeleton_boss: {
                label:"Skeleton Boss", icon:"👑", color:"#fcd34d", has_variants:false, offset:0,
                states:{
                    IDLE:  {frames:8,  pad:0, pattern:"assets/skeleton/Skeleton_01_White_Idle/skeleton-idle_{}.png"},
                    CHASE: {frames:10, pad:2, pattern:"assets/skeleton/Skeleton_01_White_Walk/skeleton-walk_{}.png"},
                    ATTACK:{frames:10, pad:2, pattern:"assets/skeleton/Skeleton_01_White_Attack1/skeleton-atk2_{}.png"},
                    HURT:  {frames:5,  pad:0, pattern:"assets/skeleton/Skeleton_01_White_Hurt/skeleton-hurt_{}.png"},
                    DEATH: {frames:13, pad:2, pattern:"assets/skeleton/Skeleton_01_White_Die/skeleton-death_{}.png"},
                }
            },
            blood_zombie: {
                label:"Blood Zombie", icon:"🩸", color:"#f87171", has_variants:false, offset:0,
                states:{
                    IDLE:  {frames:10, pad:2, pattern:"assets/graphics/bloodZombie/Idle/blood_idle{}.png"},
                    CHASE: {frames:8,  pad:0, pattern:"assets/graphics/bloodZombie/Move/blood_chase_{}.png"},
                    ATTACK:{frames:16, pad:2, pattern:"assets/graphics/bloodZombie/Attack1/blood_attack2_{}.png"},
                    DEATH: {frames:6,  pad:0, pattern:"assets/graphics/bloodZombie/Death/blood_death_{}.png"},
                }
            },
            green_monster: {
                label:"Green Monster", icon:"👾", color:"#4ade80", has_variants:false, offset:1,
                states:{
                    IDLE:  {frames:15, pad:0, pattern:"assets/graphics/green_monster/idle/idle_{}.png"},
                    CHASE: {frames:12, pad:0, pattern:"assets/graphics/green_monster/walk/walk_{}.png"},
                    ATTACK:{frames:7,  pad:0, pattern:"assets/graphics/green_monster/1atk/1atk_{}.png"},
                    HURT:  {frames:5,  pad:0, pattern:"assets/graphics/green_monster/hurt/hurt_{}.png"},
                    DEATH: {frames:11, pad:0, pattern:"assets/graphics/green_monster/death/death_{}.png"},
                }
            },
            boss_wizard: {
                label:"Fire Wizard (Boss)", icon:"🔥", color:"#fb923c", has_variants:false, offset:0,
                states:{
                    IDLE:  {frames:8, pad:0, pattern:"assets/wizard/Idle/wizard_idle{}.png"},
                    CHASE: {frames:8, pad:0, pattern:"assets/wizard/Move/wizard_run{}.png"},
                    ATTACK:{frames:8, pad:0, pattern:"assets/wizard/Attack/wizard_atk1{}.png"},
                    HURT:  {frames:4, pad:0, pattern:"assets/wizard/Take Hit/wizard_hit{}.png"},
                    DEATH: {frames:5, pad:0, pattern:"assets/wizard/Death/wizard_death{}.png"},
                }
            },
            bat: {
                label:"Bat", icon:"🦇", color:"#a78bfa", has_variants:false, offset:0,
                states:{
                    FLY:{frames:7, pad:0, pattern:"assets/graphics/bat/running/bat_running_{}.png"},
                }
            },
        };

        function getFrameImageUrl(state, variant, frameIndex) {
            const em = ENTITY_META[currentEntity];
            if (!em) return "";
            const sd = em.states[state];
            if (!sd) return "";
            let pattern;
            if (em.has_variants) {
                pattern = sd.pattern[variant] || sd.pattern.standard;
            } else {
                pattern = sd.pattern;
            }
            const num = frameIndex + (em.offset || 0);
            const numStr = (sd.pad > 0) ? String(num).padStart(sd.pad, "0") : String(num);
            return "/" + pattern.replace("{}", numStr);
        }

        // Timing configurations extracted from game engine (Player._STATE_CONFIGS, enemy defaults)
        const STATE_TIMING_META = {
            player: {
                DEATH: { speed: 0.12, loop: false },
                DEFEND: { speed: 0.18, loop: false },
                HURT: { speed: 0.20, loop: false, frame_speeds: { 0: 0.3, 1: 0.3, 2: 0.3, 3: 0.1, 4: 0.1, 5: 0.2 } },
                ATTACK_THRUST: { speed: 0.24, loop: false, frame_speeds: { 0: 0.12, 1: 0.12, 2: 0.40, 3: 0.28, 4: 0.28, 5: 0.20, 6: 0.20, 7: 0.15, 8: 0.15 } },
                ATTACK_SMASH: { speed: 0.24, loop: false, frame_speeds: { 0: 0.12, 1: 0.12, 2: 0.35, 3: 0.35, 4: 0.35, 5: 0.15, 6: 0.15, 7: 0.32, 8: 0.32, 9: 0.32, 10: 0.22, 11: 0.22, 12: 0.22, 13: 0.18, 14: 0.18, 15: 0.14, 16: 0.14 } },
                ATTACK_POWER: { speed: 0.24, loop: false, frame_speeds: { 0: 0.10, 1: 0.10, 2: 0.10, 3: 0.10, 4: 0.10, 5: 0.10, 6: 0.30, 7: 0.30, 8: 0.30, 9: 0.30, 10: 0.30, 11: 0.18, 12: 0.18, 13: 0.18, 14: 0.18, 15: 0.35, 16: 0.35, 17: 0.35, 18: 0.35, 19: 0.35, 20: 0.35, 21: 0.35, 22: 0.12 } },
                SPECIAL_ATTACK: { speed: 0.20, loop: false, frame_speeds: { 0:0.14,1:0.14,2:0.14,3:0.14,4:0.14,5:0.14,6:0.18,7:0.18,8:0.18,9:0.18,10:0.18,11:0.18,12:0.18,13:0.18,14:0.25,15:0.25,16:0.25,17:0.30,18:0.30,19:0.30,20:0.30,21:0.30,22:0.30,23:0.30,24:0.30,25:0.30,26:0.30,27:0.16,28:0.16,29:0.16,30:0.16,31:0.16,32:0.16,33:0.16 } },
                TRANSFORM: { speed: 0.18, loop: false, frame_speeds: { 0:0.14,1:0.14,2:0.14,3:0.14,4:0.14,5:0.14,6:0.22,7:0.22,8:0.22,9:0.22,10:0.22,11:0.22,12:0.22,13:0.30,14:0.30,15:0.30,16:0.30,17:0.30,18:0.30,19:0.30,20:0.30,21:0.30,22:0.25,23:0.25,24:0.25,25:0.25,26:0.25,27:0.25,28:0.25,29:0.16,30:0.16,31:0.16,32:0.16,33:0.16,34:0.16 } },
                ROLL: { speed: 0.30, loop: false },
                DASH: { speed: 0.32, loop: false },
                JUMP_UP: { speed: 0.20, loop: true },
                JUMP_DOWN: { speed: 0.22, loop: true },
                RUN: { speed: 0.22, loop: true },
                IDLE: { speed: 0.15, loop: true }
            }
        };

        let animPreviewState = {
            running: false,
            lastTime: 0,
            animationIndex: 0.0,
            currentFrameInt: -1,
            animFrameId: null,
            flashTimeout: null
        };

        function getFrameSpeed(entity, state, frameIdx) {
            const timing = STATE_TIMING_META[entity]?.[state];
            if (timing) {
                if (timing.frame_speeds && timing.frame_speeds[frameIdx] !== undefined) {
                    return timing.frame_speeds[frameIdx];
                }
                if (timing.speed !== undefined) return timing.speed;
            }
            return 0.20;
        }

        function playMixerSound(soundId) {
            const path = appState.config.sounds[soundId] || appState.jukebox_sounds[soundId];
            if (!path) return;

            const master = parseFloat(masterSlider.value);
            const sfx = parseFloat(sfxSlider.value);
            const trackVol = appState.settings.sound_volumes[soundId] !== undefined ? appState.settings.sound_volumes[soundId] : 1.0;
            const finalVol = Math.max(0.0, Math.min(1.0, master * sfx * trackVol));
            if (finalVol <= 0.001) return;

            const audio = new Audio("/" + path);
            audio.volume = finalVol;
            audio.play().catch(e => console.error("Preview sound trigger error:", e));
        }

        function onSpeedSliderChange(val) {
            const speedVal = parseFloat(val);
            const valEl = document.getElementById("preview-speed-val");
            if (valEl) valEl.innerText = `${speedVal.toFixed(1)}x`;
        }

        function setSpeedPreset(val) {
            const slider = document.getElementById("preview-speed-slider");
            if (slider) {
                slider.value = val;
                onSpeedSliderChange(val);
            }
        }

        function updateLiveSoundInfo(soundId) {
            const soundTxt = document.getElementById("live-sound-txt");
            if (!soundTxt) return;
            soundTxt.innerText = soundId ? `🔊 ${soundId}` : "🔊 No Sound";
            if (soundId) {
                soundTxt.classList.add("active-sound");
                if (animPreviewState.flashTimeout) clearTimeout(animPreviewState.flashTimeout);
                animPreviewState.flashTimeout = setTimeout(() => {
                    soundTxt.classList.remove("active-sound");
                }, 350);
            }
        }

        function toggleAnimationPreview() {
            if (animPreviewState.running) {
                stopAnimationPreview();
            } else {
                startAnimationPreview();
            }
        }

        function startAnimationPreview() {
            stopAnimationPreview();

            const state = stateSelect.value;
            const em = ENTITY_META[currentEntity];
            if (!em || !em.states[state]) return;

            const sd = em.states[state];
            const maxFrames = em.has_variants
                ? (sd.frames[currentVariant] || sd.frames.standard)
                : sd.frames;
            if (!maxFrames || maxFrames <= 0) return;

            const timing = STATE_TIMING_META[currentEntity]?.[state];
            const isLooping = timing?.loop !== undefined ? timing.loop : (state === 'IDLE' || state === 'RUN' || state === 'FLY' || state === 'WALK' || state === 'CHASE');

            animPreviewState.running = true;
            animPreviewState.animationIndex = 0.0;
            animPreviewState.currentFrameInt = -1;
            animPreviewState.lastTime = performance.now();

            const btnIcon = document.getElementById("preview-btn-icon");
            const btnText = document.getElementById("preview-btn-text");
            const widget = document.getElementById("live-anim-widget");
            const btn = document.getElementById("btn-preview-state");

            if (btnIcon) btnIcon.innerText = "⏹";
            if (btnText) btnText.innerText = "Stop";
            if (widget) widget.classList.add("active");
            if (btn) {
                btn.classList.remove("btn-primary");
                btn.classList.add("btn-danger");
            }

            function previewStep(timestamp) {
                if (!animPreviewState.running) return;

                const deltaMs = timestamp - animPreviewState.lastTime;
                animPreviewState.lastTime = timestamp;

                // Engine runs at 60 FPS (16.6667ms per frame tick)
                const frameTicks = Math.min(3.0, deltaMs / 16.6667);

                const currentInt = Math.floor(animPreviewState.animationIndex) % maxFrames;
                const baseSpeed = getFrameSpeed(currentEntity, state, currentInt);
                const speedMultiplier = parseFloat(document.getElementById("preview-speed-slider")?.value || 1.0);
                const effectiveSpeed = baseSpeed * speedMultiplier;

                animPreviewState.animationIndex += effectiveSpeed * frameTicks;

                let nextInt = Math.floor(animPreviewState.animationIndex);
                if (nextInt >= maxFrames) {
                    if (isLooping) {
                        animPreviewState.animationIndex = animPreviewState.animationIndex % maxFrames;
                        nextInt = Math.floor(animPreviewState.animationIndex);
                    } else {
                        // Played full animation sequence once
                        updatePreviewFrameDisplay(state, maxFrames - 1, maxFrames, effectiveSpeed, speedMultiplier);
                        stopAnimationPreview();
                        return;
                    }
                }

                if (nextInt !== animPreviewState.currentFrameInt) {
                    animPreviewState.currentFrameInt = nextInt;
                    updatePreviewFrameDisplay(state, nextInt, maxFrames, effectiveSpeed, speedMultiplier);

                    // Check sound trigger
                    const targetMap = (currentVariant === "standard") 
                        ? (appState.config.states[state] || {})
                        : (appState.config.enhanced_states[state] || {});

                    const soundId = targetMap[nextInt];
                    if (soundId) {
                        playMixerSound(soundId);
                        updateLiveSoundInfo(soundId);
                    }
                }

                animPreviewState.animFrameId = requestAnimationFrame(previewStep);
            }

            animPreviewState.animFrameId = requestAnimationFrame(previewStep);
        }

        function updatePreviewFrameDisplay(state, frameIdx, maxFrames, speed, multiplier) {
            const imgUrl = getFrameImageUrl(state, currentVariant, frameIdx);
            
            const liveImg = document.getElementById("live-anim-img");
            if (liveImg) {
                liveImg.src = imgUrl;
                liveImg.style.opacity = '1';
            }

            const frameTxt = document.getElementById("live-anim-frame-num");
            if (frameTxt) frameTxt.innerText = `Frame ${frameIdx} / ${maxFrames}`;

            const speedTxt = document.getElementById("live-anim-speed-txt");
            const speedMult = multiplier || parseFloat(document.getElementById("preview-speed-slider")?.value || 1.0);
            if (speedTxt) speedTxt.innerText = `${speed.toFixed(2)} spd (${speedMult.toFixed(1)}x)`;

            // Highlight timeline card in grid
            const cards = document.querySelectorAll("#timeline-grid .frame-card");
            cards.forEach((card, idx) => {
                if (idx === frameIdx) {
                    card.classList.add("preview-active");
                } else {
                    card.classList.remove("preview-active");
                }
            });
        }

        function stopAnimationPreview() {
            animPreviewState.running = false;
            if (animPreviewState.animFrameId) {
                cancelAnimationFrame(animPreviewState.animFrameId);
                animPreviewState.animFrameId = null;
            }
            if (animPreviewState.flashTimeout) {
                clearTimeout(animPreviewState.flashTimeout);
                animPreviewState.flashTimeout = null;
            }

            const btnIcon = document.getElementById("preview-btn-icon");
            const btnText = document.getElementById("preview-btn-text");
            const widget = document.getElementById("live-anim-widget");
            const soundTxt = document.getElementById("live-sound-txt");
            const btn = document.getElementById("btn-preview-state");

            if (btnIcon) btnIcon.innerText = "▶";
            if (btnText) btnText.innerText = "Preview";
            if (widget) widget.classList.remove("active");
            if (soundTxt) {
                soundTxt.classList.remove("active-sound");
                soundTxt.innerText = "🔊 No Sound";
            }
            if (btn) {
                btn.classList.remove("btn-danger");
                btn.classList.add("btn-primary");
            }

            // Remove glow from timeline cards
            const cards = document.querySelectorAll("#timeline-grid .frame-card");
            cards.forEach(card => card.classList.remove("preview-active"));
        }

        // Application State
        let appState = {
            config: {},
            settings: {},
            jukebox_sounds: {},
            audio_assets: [],
            isModified: false,
            activeFrameTarget: null,
            valid: true,
            reason: ""
        };

        // DOM Elements
        const masterSlider  = document.getElementById("master-slider");
        const musicSlider   = document.getElementById("music-slider");
        const sfxSlider     = document.getElementById("sfx-slider");
        const stateSelect   = document.getElementById("state-select");
        const btnStd        = document.getElementById("btn-std");
        const btnEnh        = document.getElementById("btn-enh");
        const alertBar      = document.getElementById("alert-bar");
        const alertText     = document.getElementById("alert-text");
        const lockStatus    = document.getElementById("lock-status");
        const lockText      = document.getElementById("lock-text");
        const variantToggle = document.getElementById("variant-toggle");
        const entityChips   = document.getElementById("entity-chips");

        let currentVariant = "standard";
        let currentEntity  = "player";

        // Build entity chip selector
        function initEntitySelector() {
            entityChips.innerHTML = "";
            Object.entries(ENTITY_META).forEach(([key, meta]) => {
                const chip = document.createElement("button");
                chip.className = "entity-chip" + (key === currentEntity ? " active" : "");
                chip.style.borderColor = key === currentEntity ? meta.color : "transparent";
                chip.style.backgroundColor = key === currentEntity ? meta.color + "22" : "";
                chip.style.color = key === currentEntity ? meta.color : "";
                chip.textContent = meta.icon + " " + meta.label;
                chip.title = key;
                chip.addEventListener("click", () => switchEntity(key));
                entityChips.appendChild(chip);
            });
        }

        function switchEntity(key) {
            if (!ENTITY_META[key]) return;
            stopAnimationPreview();
            currentEntity = key;
            const meta = ENTITY_META[key];
            // Rebuild chips
            initEntitySelector();
            // Show/hide variant toggle
            variantToggle.style.display = meta.has_variants ? "" : "none";
            if (!meta.has_variants) currentVariant = "standard";
            // Repopulate state dropdown
            populateStateDropdown();
            // Re-fetch entity config
            fetchStatus();
        }

        function populateStateDropdown() {
            const meta = ENTITY_META[currentEntity];
            if (!meta) return;
            stateSelect.innerHTML = "";
            Object.keys(meta.states).forEach(st => {
                const opt = document.createElement("option");
                opt.value = st;
                opt.textContent = st;
                stateSelect.appendChild(opt);
            });
        }

        // Init
        window.addEventListener("DOMContentLoaded", async () => {
            initEntitySelector();
            populateStateDropdown();
            variantToggle.style.display = ENTITY_META[currentEntity].has_variants ? "" : "none";
            await fetchStatus();
            await fetchAudioAssets();
            setupEventListeners();
            renderTimeline();
        });

        async function fetchStatus() {
            try {
                const res = await fetch("/api/status?entity=" + encodeURIComponent(currentEntity));
                const data = await res.json();

                appState.config = data.config || {sounds:{}, states:{}, enhanced_states:{}};
                appState.settings = data.settings || {};
                appState.jukebox_sounds = data.jukebox_sounds || {};
                appState.valid = data.valid;
                appState.reason = data.reason;
                appState.isModified = false;

                if (!appState.settings.sound_volumes) {
                    appState.settings.sound_volumes = {};
                }

                masterSlider.value = appState.settings.master_volume || 1.0;
                document.getElementById("master-val").innerText = (appState.settings.master_volume || 1.0).toFixed(2);
                musicSlider.value = appState.settings.music_volume || 0.5;
                document.getElementById("music-val").innerText = (appState.settings.music_volume || 0.5).toFixed(2);
                sfxSlider.value = appState.settings.sfx_volume || 0.8;
                document.getElementById("sfx-val").innerText = (appState.settings.sfx_volume || 0.8).toFixed(2);

                updateLockStatusUI();
                renderTrackMixer();
                renderTimeline();
            } catch (err) {
                console.error("Error fetching status:", err);
            }
        }

        async function fetchAudioAssets() {
            try {
                const res = await fetch("/api/audio-assets");
                const data = await res.json();
                appState.audio_assets = data.assets || [];
                populateFolderDropdown();
                populateRawAssetsDatalist();
            } catch (err) {
                console.error("Error loading audio files list:", err);
            }
        }

        function populateRawAssetsDatalist() {
            const datalist = document.getElementById("raw-assets-datalist");
            if (!datalist) return;
            datalist.innerHTML = "";
            (appState.audio_assets || []).forEach(assetPath => {
                const opt = document.createElement("option");
                opt.value = assetPath;
                const filename = assetPath.split("/").pop();
                opt.label = filename;
                datalist.appendChild(opt);
            });
        }

        function populateFolderDropdown() {
            const folderSelect = document.getElementById("raw-folder-select");
            if (!folderSelect) return;
            const currentFolder = folderSelect.value;
            folderSelect.innerHTML = '<option value="">All Folders</option>';
            
            const folderCounts = {};
            (appState.audio_assets || []).forEach(assetPath => {
                const parts = assetPath.split("/");
                parts.pop(); // remove filename
                const folder = parts.join("/");
                folderCounts[folder] = (folderCounts[folder] || 0) + 1;
            });
            
            Object.keys(folderCounts).sort().forEach(folder => {
                const opt = document.createElement("option");
                opt.value = folder;
                opt.textContent = `${folder} (${folderCounts[folder]})`;
                folderSelect.appendChild(opt);
            });
            if (currentFolder) folderSelect.value = currentFolder;
        }

        function setupEventListeners() {
            // Main Sliders
            masterSlider.addEventListener("input", (e) => {
                const val = parseFloat(e.target.value);
                document.getElementById("master-val").innerText = val.toFixed(2);
                appState.settings.master_volume = val;
                markUnsaved();
            });

            musicSlider.addEventListener("input", (e) => {
                const val = parseFloat(e.target.value);
                document.getElementById("music-val").innerText = val.toFixed(2);
                appState.settings.music_volume = val;
                markUnsaved();
            });

            sfxSlider.addEventListener("input", (e) => {
                const val = parseFloat(e.target.value);
                document.getElementById("sfx-val").innerText = val.toFixed(2);
                appState.settings.sfx_volume = val;
                markUnsaved();
            });

            // Search Filter
            document.getElementById("mixer-search").addEventListener("input", renderTrackMixer);

            // Selection Controls
            stateSelect.addEventListener("change", () => {
                stopAnimationPreview();
                renderTimeline();
            });
            
            btnStd.addEventListener("click", () => {
                stopAnimationPreview();
                btnStd.classList.add("active");
                btnEnh.classList.remove("active");
                currentVariant = "standard";
                renderTimeline();
            });

            btnEnh.addEventListener("click", () => {
                stopAnimationPreview();
                btnEnh.classList.add("active");
                btnStd.classList.remove("active");
                currentVariant = "enhanced";
                renderTimeline();
            });

            // Action Buttons
            document.getElementById("save-btn").addEventListener("click", saveChanges);
            document.getElementById("revert-btn").addEventListener("click", revertChanges);
        }

        function markUnsaved() {
            appState.isModified = true;
            updateLockStatusUI();
        }

        function updateLockStatusUI() {
            lockStatus.className = "lock-badge";
            
            if (appState.isModified) {
                lockStatus.classList.add("unsaved");
                lockText.innerText = "UNSAVED CHANGES";
                alertBar.style.display = "flex";
                alertText.innerText = "Values changed in editor. Click 'Save Changes' to apply and secure lock.";
            } else if (appState.valid) {
                lockStatus.classList.add("valid");
                lockText.innerText = "LOCK SECURED";
                alertBar.style.display = "none";
            } else {
                lockStatus.classList.add("invalid");
                lockText.innerText = "LOCK OUT OF SYNC";
                alertBar.style.display = "flex";
                alertText.innerText = appState.reason || "Audios do not match lock signatures.";
            }
        }

        // Render Track Mixer List
        function renderTrackMixer() {
            const list = document.getElementById("track-volumes-list");
            list.innerHTML = "";

            const query = document.getElementById("mixer-search").value.toLowerCase();

            // Assemble all sound keys (from jukebox + config.sounds)
            const allSounds = new Set([
                ...Object.keys(appState.jukebox_sounds),
                ...Object.keys(appState.config.sounds || {})
            ]);

            Array.from(allSounds).sort().forEach(soundId => {
                if (query && !soundId.toLowerCase().includes(query)) return;

                // Find relative path for previewing
                const path = appState.config.sounds[soundId] || appState.jukebox_sounds[soundId];
                const volume = appState.settings.sound_volumes[soundId] !== undefined ? appState.settings.sound_volumes[soundId] : 1.0;

                const item = document.createElement("div");
                item.className = "track-mixer-item";
                item.innerHTML = `
                    <div class="track-info">
                        <div style="display: flex; align-items: center; gap: 0.4rem;">
                            <button class="play-icon-btn" onclick="previewSound('${soundId}')">&#9658;</button>
                            <span class="track-name" title="${soundId}">${soundId}</span>
                        </div>
                        <span id="val-${soundId}" class="volume-val" style="font-size: 0.8rem; color: var(--text-secondary);">${volume.toFixed(2)}</span>
                    </div>
                    <div class="volume-slider-row">
                        <input type="range" class="slider" min="0" max="2" step="0.05" value="${volume}" oninput="updateTrackVolume('${soundId}', this.value)">
                    </div>
                `;
                list.appendChild(item);
            });
        }

        function updateTrackVolume(soundId, value) {
            const val = parseFloat(value);
            document.getElementById(`val-${soundId}`).innerText = val.toFixed(2);
            appState.settings.sound_volumes[soundId] = val;
            markUnsaved();
        }

        // Render Frame Timeline
        function renderTimeline() {
            const grid = document.getElementById("timeline-grid");
            grid.innerHTML = "";

            const state = stateSelect.value;
            const em = ENTITY_META[currentEntity];
            if (!em || !em.states[state]) return;

            const sd = em.states[state];
            const maxFrames = em.has_variants
                ? (sd.frames[currentVariant] || sd.frames.standard)
                : sd.frames;

            // Get sound assignments map for this state
            const targetMap = (currentVariant === "standard") 
                ? (appState.config.states[state] || {})
                : (appState.config.enhanced_states[state] || {});

            for (let f = 0; f < maxFrames; f++) {
                const soundId = targetMap[f] || null;
                const card = document.createElement("div");
                card.className = "frame-card" + (soundId ? " has-sound" : "");
                
                const imgUrl = getFrameImageUrl(state, currentVariant, f);
                
                card.innerHTML = `
                    <div class="frame-header">
                        <span class="frame-num">Frame ${f}</span>
                        <span class="frame-sound-label">Trigger sound</span>
                    </div>
                    <div class="frame-preview-img-container">
                        <img class="frame-preview-img" src="${imgUrl}" alt="Frame ${f}" onerror="this.parentElement.style.display='none';" />
                    </div>
                    <div class="assigned-sound-area">
                        <span class="sound-id-text ${!soundId ? 'empty' : ''}">${soundId || 'No Trigger Assigned'}</span>
                        ${soundId ? `<button class="play-icon-btn" style="font-size: 0.9rem;" onclick="previewSound('${soundId}')">&#9658;</button>` : ''}
                    </div>
                    <div class="frame-card-actions">
                        <button class="btn" style="padding: 0.3rem;" onclick="openAssignModal('${state}', '${currentVariant}', ${f})">Assign</button>
                        ${soundId ? `<button class="btn btn-danger" style="padding: 0.3rem;" onclick="clearFrameTrigger('${state}', '${currentVariant}', ${f})">Clear</button>` : ''}
                    </div>
                `;
                grid.appendChild(card);
            }
        }

        // Preview sound with scaled volume
        function previewSound(soundId) {
            const path = appState.config.sounds[soundId] || appState.jukebox_sounds[soundId];
            if (!path) {
                alert(`No filepath mapped for sound key '${soundId}'`);
                return;
            }

            const audio = document.getElementById("preview-player");
            const master = parseFloat(masterSlider.value);
            const sfx = parseFloat(sfxSlider.value);
            const trackVol = appState.settings.sound_volumes[soundId] !== undefined ? appState.settings.sound_volumes[soundId] : 1.0;
            
            // Linear emulation: master * sfx * track volume
            const finalVol = Math.max(0.0, Math.min(1.0, master * sfx * trackVol));
            
            audio.src = "/" + path;
            audio.volume = finalVol;
            audio.play().catch(e => {
                console.error("Audio preview failed:", e);
                alert("Playback failed. Please verify if the audio file exists at: " + path);
            });
        }

        function clearFrameTrigger(state, variant, frame) {
            const targetMap = (variant === "standard") 
                ? appState.config.states
                : appState.config.enhanced_states;

            if (targetMap[state]) {
                delete targetMap[state][frame];
                // Clean up empty keys
                if (Object.keys(targetMap[state]).length === 0) {
                    delete targetMap[state];
                }
                markUnsaved();
                renderTimeline();
            }
        }

        // Modal Management
        function openAssignModal(state, variant, frame) {
            stopAnimationPreview();
            appState.activeFrameTarget = { state, variant, frame };
            document.getElementById("modal-title-text").innerText = `Assign sound to ${state} (${variant}) - Frame ${frame}`;
            
            const previewHeader = document.querySelector(".modal-frame-preview");
            if (previewHeader) previewHeader.style.display = 'block';
            const btnAssign = document.getElementById("btn-register-assign");
            if (btnAssign) btnAssign.style.display = "inline-block";

            // Set modal frame preview image
            const imgEl = document.getElementById("modal-frame-img");
            imgEl.parentElement.style.display = 'flex';
            imgEl.src = getFrameImageUrl(state, variant, frame);
            
            // Clear inputs
            document.getElementById("new-sound-path").value = "";
            document.getElementById("new-sound-alias").value = "";
            currentlySelectedRawPath = "";
            
            filterRegisteredSounds();
            filterRawAssets();
            
            document.getElementById("assign-modal").classList.add("open");
        }

        function openAudioBrowserModal() {
            stopAnimationPreview();
            appState.activeFrameTarget = null;
            document.getElementById("modal-title-text").innerText = "Browse & Register Audio Assets";
            
            const previewHeader = document.querySelector(".modal-frame-preview");
            if (previewHeader) previewHeader.style.display = "none";
            
            const btnAssign = document.getElementById("btn-register-assign");
            if (btnAssign) btnAssign.style.display = "none";
            
            document.getElementById("new-sound-path").value = "";
            document.getElementById("new-sound-alias").value = "";
            currentlySelectedRawPath = "";
            
            switchTab(null, 'tab-raw');
            filterRegisteredSounds();
            filterRawAssets();
            
            document.getElementById("assign-modal").classList.add("open");
        }

        function closeModal() {
            document.getElementById("assign-modal").classList.remove("open");
            appState.activeFrameTarget = null;
        }

        function switchTab(evt, tabId) {
            document.querySelectorAll(".tab-link").forEach(btn => btn.classList.remove("active"));
            document.querySelectorAll(".tab-content").forEach(c => c.classList.remove("active"));
            
            if (evt && evt.currentTarget) {
                evt.currentTarget.classList.add("active");
            } else if (tabId === 'tab-raw') {
                const tabs = document.querySelectorAll(".tab-link");
                if (tabs.length > 1) tabs[1].classList.add("active");
            }
            document.getElementById(tabId).classList.add("active");
        }

        function filterRegisteredSounds() {
            const list = document.getElementById("registered-sounds-list");
            if (!list) return;
            list.innerHTML = "";
            
            const query = (document.getElementById("reg-sound-search")?.value || "").toLowerCase().trim();
            
            const allSounds = new Set([
                ...Object.keys(appState.jukebox_sounds),
                ...Object.keys(appState.config.sounds || {})
            ]);

            Array.from(allSounds).sort().forEach(soundId => {
                const path = appState.config.sounds[soundId] || appState.jukebox_sounds[soundId] || "";
                if (query && !soundId.toLowerCase().includes(query) && !path.toLowerCase().includes(query)) return;
                
                const item = document.createElement("div");
                item.className = "asset-list-item";
                
                const info = document.createElement("div");
                info.className = "asset-info";
                info.style.cursor = "pointer";
                info.style.flex = "1";
                info.onclick = () => {
                    if (appState.activeFrameTarget) {
                        assignSoundToFrame(soundId);
                    } else {
                        previewSound(soundId);
                    }
                };

                const nameSpan = document.createElement("span");
                nameSpan.className = "asset-name";
                nameSpan.textContent = soundId;
                
                const pathSpan = document.createElement("span");
                pathSpan.className = "asset-path";
                pathSpan.textContent = path;
                
                info.appendChild(nameSpan);
                info.appendChild(pathSpan);
                
                const actions = document.createElement("div");
                actions.className = "asset-actions";
                
                const playBtn = document.createElement("button");
                playBtn.className = "play-icon-btn";
                playBtn.innerHTML = "&#9658;";
                playBtn.title = "Preview Sound";
                playBtn.onclick = (e) => {
                    e.stopPropagation();
                    previewSound(soundId);
                };

                const chooseBtn = document.createElement("button");
                chooseBtn.className = "btn btn-primary";
                chooseBtn.style.padding = "0.3rem 0.6rem";
                chooseBtn.style.fontSize = "0.75rem";
                chooseBtn.textContent = appState.activeFrameTarget ? "Choose" : "Preview";
                chooseBtn.onclick = (e) => {
                    e.stopPropagation();
                    if (appState.activeFrameTarget) {
                        assignSoundToFrame(soundId);
                    } else {
                        previewSound(soundId);
                    }
                };

                actions.appendChild(playBtn);
                actions.appendChild(chooseBtn);

                item.appendChild(info);
                item.appendChild(actions);
                list.appendChild(item);
            });
        }

        let currentlySelectedRawPath = "";

        function filterRawAssets() {
            const list = document.getElementById("raw-assets-list");
            const countEl = document.getElementById("raw-asset-count");
            if (!list) return;
            list.innerHTML = "";
            
            const query = (document.getElementById("raw-sound-search")?.value || "").toLowerCase().trim();
            const folderFilter = (document.getElementById("raw-folder-select")?.value || "").trim();
            
            let matchedCount = 0;

            (appState.audio_assets || []).forEach(assetPath => {
                const filename = assetPath.split("/").pop();
                const lastSlash = assetPath.lastIndexOf("/");
                const dir = lastSlash !== -1 ? assetPath.substring(0, lastSlash) : "";

                if (folderFilter && dir !== folderFilter && !dir.startsWith(folderFilter + "/")) return;
                if (query && !filename.toLowerCase().includes(query) && !assetPath.toLowerCase().includes(query)) return;
                
                matchedCount++;
                const isSelected = (assetPath === currentlySelectedRawPath);
                
                const item = document.createElement("div");
                item.className = "asset-list-item" + (isSelected ? " selected" : "");
                
                const info = document.createElement("div");
                info.className = "asset-info";
                info.style.cursor = "pointer";
                info.style.flex = "1";
                info.onclick = () => selectRawAssetForRegistration(assetPath);

                const nameSpan = document.createElement("span");
                nameSpan.className = "asset-name";
                nameSpan.style.color = isSelected ? 'var(--accent-cyan)' : 'var(--text-primary)';
                nameSpan.textContent = "🎵 " + filename;
                
                const pathSpan = document.createElement("span");
                pathSpan.className = "asset-path";
                pathSpan.textContent = assetPath;

                info.appendChild(nameSpan);
                info.appendChild(pathSpan);

                const actions = document.createElement("div");
                actions.className = "asset-actions";

                const playBtn = document.createElement("button");
                playBtn.className = "play-icon-btn";
                playBtn.innerHTML = "&#9658;";
                playBtn.title = "Preview Audio File";
                playBtn.onclick = (e) => {
                    e.stopPropagation();
                    previewRawFile(assetPath);
                };

                const selectBtn = document.createElement("button");
                selectBtn.className = "btn " + (isSelected ? 'btn-primary' : 'btn-secondary');
                selectBtn.style.padding = "0.3rem 0.6rem";
                selectBtn.style.fontSize = "0.75rem";
                selectBtn.textContent = isSelected ? "✓ Selected" : "Select";
                selectBtn.onclick = (e) => {
                    e.stopPropagation();
                    selectRawAssetForRegistration(assetPath);
                };

                actions.appendChild(playBtn);
                actions.appendChild(selectBtn);

                item.appendChild(info);
                item.appendChild(actions);
                list.appendChild(item);
            });

            if (matchedCount === 0) {
                const emptyMsg = document.createElement("div");
                emptyMsg.style.padding = "1.5rem";
                emptyMsg.style.textAlign = "center";
                emptyMsg.style.color = "var(--text-secondary)";
                emptyMsg.style.fontSize = "0.85rem";
                emptyMsg.textContent = query ? `No audio files match "${query}"` : "No audio assets found in selected folder.";
                list.appendChild(emptyMsg);
            }

            if (countEl) {
                countEl.textContent = `Showing ${matchedCount} of ${(appState.audio_assets || []).length} audio assets`;
            }
        }

        function previewRawFile(path) {
            const audio = document.getElementById("preview-player");
            const master = parseFloat(masterSlider.value);
            const sfx = parseFloat(sfxSlider.value);
            
            audio.src = "/" + path;
            audio.volume = Math.max(0.0, Math.min(1.0, master * sfx));
            audio.play().catch(err => {
                console.error("Playback failed for file:", path, err);
                alert("Cannot play preview. File might be corrupted or format unsupported by browser.");
            });
        }

        function onRawPathInputChange(val) {
            currentlySelectedRawPath = val;
            
            if (val) {
                const filename = val.split("/").pop();
                const alias = filename.split(".")[0].replace(/[^a-zA-Z0-9_]/g, "_").toLowerCase();
                const aliasInput = document.getElementById("new-sound-alias");
                if (aliasInput) aliasInput.value = alias;
            }
            
            filterRawAssets();
            
            if ((appState.audio_assets || []).includes(val)) {
                previewRawFile(val);
            }
        }

        function selectRawAssetForRegistration(path) {
            currentlySelectedRawPath = path;
            const pathInput = document.getElementById("new-sound-path");
            if (pathInput) pathInput.value = path;
            
            const filename = path.split("/").pop();
            const alias = filename.split(".")[0].replace(/[^a-zA-Z0-9_]/g, "_").toLowerCase();
            const aliasInput = document.getElementById("new-sound-alias");
            if (aliasInput) aliasInput.value = alias;
            
            filterRawAssets();
            previewRawFile(path);
            
            if (aliasInput) {
                aliasInput.focus();
                aliasInput.select();
            }
        }

        function previewSelectedRawPath() {
            const path = document.getElementById("new-sound-path").value;
            if (path) {
                previewRawFile(path);
            } else {
                alert("Please select an audio file first.");
            }
        }

        function registerOnlyAsset() {
            const path = document.getElementById("new-sound-path").value;
            const alias = document.getElementById("new-sound-alias").value.trim();
            
            if (!path) {
                alert("Please select an audio file first.");
                return;
            }
            if (!alias) {
                alert("Please specify a Sound ID / Alias.");
                return;
            }

            if (!appState.config.sounds) {
                appState.config.sounds = {};
            }
            appState.config.sounds[alias] = path;
            
            markUnsaved();
            filterRegisteredSounds();
            renderTrackMixer();
            
            const badge = document.getElementById("register-status-badge");
            if (badge) {
                badge.style.display = "inline";
                setTimeout(() => { badge.style.display = "none"; }, 2500);
            }
        }

        function assignSoundToFrame(soundId) {
            const target = appState.activeFrameTarget;
            if (!target) return;
            
            const targetMap = (target.variant === "standard") 
                ? appState.config.states 
                : appState.config.enhanced_states;

            if (!targetMap[target.state]) {
                targetMap[target.state] = {};
            }

            targetMap[target.state][target.frame] = soundId;
            
            markUnsaved();
            closeModal();
            renderTimeline();
        }

        function registerAndAssignAsset() {
            const path = document.getElementById("new-sound-path").value;
            const alias = document.getElementById("new-sound-alias").value.trim();
            
            if (!path) {
                alert("Please select an audio file first.");
                return;
            }
            if (!alias) {
                alert("Please specify a Sound ID/Alias.");
                return;
            }

            // Add to config sounds
            if (!appState.config.sounds) {
                appState.config.sounds = {};
            }
            appState.config.sounds[alias] = path;
            
            // Assign to frame
            assignSoundToFrame(alias);
        }

        // POST Save Changes
        async function saveChanges() {
            try {
                const response = await fetch("/api/save", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        config: appState.config,
                        settings: appState.settings,
                        entity: currentEntity
                    })
                });
                
                const result = await response.json();
                if (result.success) {
                    appState.isModified = false;
                    appState.valid = result.valid;
                    appState.reason = result.reason;
                    updateLockStatusUI();
                    renderTimeline();
                    renderTrackMixer();
                    alert("Configuration saved and lock signatures generated successfully!");
                } else {
                    alert("Failed to save: " + result.error);
                }
            } catch (err) {
                console.error("Error saving config:", err);
                alert("Failed to connect to the editor server to save changes.");
            }
        }

        // Revert Changes
        async function revertChanges() {
            if (confirm("Are you sure you want to revert all unsaved edits?")) {
                await fetchStatus();
                renderTimeline();
            }
        }
    </script>
</body>
</html>
"""

class MixerEditorHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Override to suppress standard HTTP logging to terminal
        pass

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

        elif path == "/api/status":
            try:
                jukebox_sounds = extract_jukebox_sounds()
                parsed = urllib.parse.parse_qs(parsed_url.query)
                entity_key = parsed.get("entity", ["player"])[0]
                if entity_key not in ENTITY_REGISTRY:
                    entity_key = "player"
                reg = ENTITY_REGISTRY[entity_key]
                config_path = reg["config"]
                lock_path   = reg["lock"]

                # Seed defaults if file missing
                if not os.path.exists(config_path):
                    if entity_key == "player":
                        default_config = {
                            "sounds": {
                                "smash_phase_1": "assets/audio/smash.wav",
                                "smash_phase_2": "assets/audio/sword-slash-and-swing-185432.mp3",
                                "smash_phase_3": "assets/audio/sword-slice-2-393845.mp3",
                                "power_release_1": "assets/audio/Magical Light Aura Sound Effect.mp3",
                            },
                            "states": {
                                "ATTACK_SMASH": {"3": "smash_phase_1", "7": "smash_phase_2", "11": "smash_phase_3"},
                                "ATTACK_POWER": {"3": "smash_phase_1", "7": "smash_phase_2", "11": "smash_phase_3", "16": "power_release_1"}
                            },
                            "enhanced_states": {}
                        }
                    else:
                        default_config = dict(DEFAULT_EMPTY_CONFIG)
                    from src.game.audio.audio_lock import save_config_and_lock
                    save_config_and_lock(default_config, config_path, lock_path)

                from src.game.audio.audio_lock import verify_config_integrity
                is_valid, reason = verify_config_integrity(config_path, lock_path)

                with open(config_path, "r") as f:
                    config = json.load(f)

                from v3x_zulfiqar_gideon.settings import SettingsManager
                sm = SettingsManager()
                sm.load()
                settings = sm.data

                self.send_json({
                    "valid": is_valid,
                    "reason": reason,
                    "config": config,
                    "settings": settings,
                    "jukebox_sounds": jukebox_sounds,
                    "entity": entity_key
                })
            except Exception as e:
                self.send_json({"error": str(e)}, 500)
            return

        elif path == "/api/audio-assets":
            try:
                audio_files = []
                assets_dir = os.path.join(BASE_DIR, "assets")
                if os.path.exists(assets_dir):
                    for root, dirs, files in os.walk(assets_dir):
                        for file in files:
                            if file.lower().endswith((".mp3", ".wav", ".ogg", ".flac", ".m4a")):
                                full_path = os.path.join(root, file)
                                rel_path = os.path.relpath(full_path, BASE_DIR)
                                audio_files.append(rel_path)
                self.send_json({"assets": sorted(audio_files)})
            except Exception as e:
                self.send_json({"error": str(e)}, 500)
            return

        # Serve static assets directly from disk
        if path.startswith("/assets/") or path.startswith("/game_data/"):
            clean_path = urllib.parse.unquote(path.lstrip("/"))
            full_path = os.path.join(BASE_DIR, clean_path)

            if not os.path.abspath(full_path).startswith(os.path.abspath(BASE_DIR)):
                self.send_error(403, "Access Denied")
                return

            if os.path.exists(full_path) and os.path.isfile(full_path):
                self.send_response(200)
                if full_path.endswith(".mp3"):
                    self.send_header("Content-Type", "audio/mpeg")
                elif full_path.endswith(".wav"):
                    self.send_header("Content-Type", "audio/wav")
                elif full_path.endswith(".ogg"):
                    self.send_header("Content-Type", "audio/ogg")
                elif full_path.endswith(".png"):
                    self.send_header("Content-Type", "image/png")
                else:
                    self.send_header("Content-Type", "application/octet-stream")
                self.send_header("Content-Length", str(os.path.getsize(full_path)))
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                with open(full_path, "rb") as f:
                    self.wfile.write(f.read())
                return
            else:
                self.send_error(404, "File Not Found")
                return

        self.send_error(404, "Not Found")

    def do_POST(self):
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path

        if path == "/api/save":
            try:
                content_length = int(self.headers['Content-Length'])
                post_data = self.rfile.read(content_length)
                payload = json.loads(post_data.decode('utf-8'))

                config_dict = payload.get("config")
                settings_dict = payload.get("settings")

                if config_dict is None or settings_dict is None:
                    self.send_json({"error": "Missing config or settings in payload"}, 400)
                    return

                # 1. Update settings
                from v3x_zulfiqar_gideon.settings import SettingsManager
                sm = SettingsManager()
                for k, v in settings_dict.items():
                    if k in sm.defaults:
                        sm.data[k] = v
                sm.save()

                # 2. Save entity-specific configuration & lockfile
                entity_key = payload.get("entity", "player")
                if entity_key not in ENTITY_REGISTRY:
                    entity_key = "player"
                reg = ENTITY_REGISTRY[entity_key]
                config_path = reg["config"]
                lock_path   = reg["lock"]

                from src.game.audio.audio_lock import save_config_and_lock, verify_config_integrity
                save_config_and_lock(config_dict, config_path, lock_path)

                is_valid, reason = verify_config_integrity(config_path, lock_path)

                self.send_json({
                    "success": True,
                    "valid": is_valid,
                    "reason": reason,
                    "entity": entity_key
                })
            except Exception as e:
                self.send_json({"error": str(e)}, 500)
            return

        self.send_error(404, "Not Found")

def start_server():
    port = 8000
    while port < 8100:
        try:
            handler = MixerEditorHandler
            with socketserver.TCPServer(("", port), handler) as httpd:
                print(f"[Mixer Editor Server] Started at http://localhost:{port}")
                
                # Autolaunch default browser after 0.5s delay
                Timer(0.5, lambda: webbrowser.open(f"http://localhost:{port}")).start()
                
                try:
                    httpd.serve_forever()
                except KeyboardInterrupt:
                    print("\n[Mixer Editor Server] Shutting down.")
                    sys.exit(0)
        except OSError:
            # Port already in use, try the next one
            port += 1

if __name__ == "__main__":
    start_server()
