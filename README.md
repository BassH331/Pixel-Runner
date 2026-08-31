# 🏃‍♂️ Pixel Runner

An action-packed 2D side-scrolling pixel-art game built in Python using **Pygame** and the **V3X Zulfiqar Gideon Engine**. 

Pixel Runner features human-like enemy perception, multi-enemy squad flanking & pincer tactics, dynamic telemetry difficulty scaling, and a comprehensive suite of visual GUI plugin editors.

---

## 🚀 Quick Start

### 1. Installation
Set up your virtual environment and install all dependencies:
```bash
make install
```

### 2. Launch the Game
Run the game in standard story mode:
```bash
make run
# Or directly:
python main.py
```

---

## 🎮 Game Execution Modes & Command Line Flags

You can launch `main.py` in several distinct execution modes depending on whether you want to experience the story, jump straight into combat testing, or enable analytics:

| Command Target | Direct CLI Command | Description |
| :--- | :--- | :--- |
| `make run` | `python main.py` | **Full Story Experience**: Starts from the intro splash screen, cutscenes, and main menu. |
| `make dev` | `python main.py --dev` | **Developer Fast-Pass**: Bypasses all intro cutscenes and menus to spawn immediately into gameplay. |
| `make track` | `python main.py --track` | **Telemetry Mode**: Enables live frame-by-frame gameplay metric tracking and telemetry. |
| Custom Level | `python main.py --level game_data/level_01.json` | **Level Tester**: Loads a specific level configuration JSON file. |
| Custom Distance | `python main.py --start-dist 1500` | **Position Override**: Spawns the player at a specific world distance marker. |

---

## 💀 AI Difficulty Modes ("Turning Up the Heat")

Pixel Runner features an adaptive AI system with 4 distinct difficulty modes controlled via the `AI_DIFFICULTY` environment variable. These adjust enemy reaction latency, squad coordination tokens, and tactical spacing retractions:

```bash
# Easy Mode (Relaxed pacing)
AI_DIFFICULTY=EASY python main.py

# Standard Mode (Default balanced combat)
python main.py

# Hard Mode (Fast reaction times & 3 simultaneous attackers)
make hard
# Or: AI_DIFFICULTY=HARD python main.py

# Nightmare Mode (Pro-gamer 80ms reaction time & 4 simultaneous flankers)
make nightmare
# Or: AI_DIFFICULTY=NIGHTMARE python main.py
```

### Difficulty Presets Breakdown

| Difficulty Setting | Max Simultaneous Attackers | Perception Latency | Spacing Retraction Chance | Whiff Sensitivity |
| :--- | :---: | :---: | :---: | :---: |
| **EASY** | 1 | 350 ms | 25% | 0.9x |
| **MEDIUM** *(Default)* | 2 | 200 ms | 45% | 1.2x |
| **HARD** | 3 | 120 ms | 70% | 1.6x |
| **NIGHTMARE** | 4 | 80 ms | 85% | 2.0x |

---

## 🎨 Plugin Editors & Visual GUI Tools

Pixel Runner includes 10 standalone visual GUI editors for live tuning of game assets, entity statistics, animation speeds, level layouts, and sound channels.

### 1. 👑 Boss Editor
- **Command**: `make boss-editor` or `python boss_editor.py`
- **Purpose**: Visual GUI for configuring Boss attributes (health, mana recharge rate, spell costs, telegraph timing, and phase transitions).

### 2. 🎮 Player Editor
- **Command**: `make player-editor` or `python player_editor.py`
- **Purpose**: Fine-tune player movement speed, attack frame animations, combo chains, hitboxes, and invincibility frames.

### 3. 🗺️ Level Designer Editor
- **Command**: `make level-editor` or `python level_editor.py`
- **Purpose**: Drag-and-drop level creator for placing ground platforms, environmental hazard props, enemy spawn zones, and story NPCs.

### 4. 👾 Entity & Enemy Stats Editor
- **Command**: `make entity-editor` or `python entity_editor.py`
- **Purpose**: Balance enemy stats, speeds, and combat heuristics for Skeletons, Blood Zombies, Green Monsters, Dark Ronins, Fire Wizards, and Bats.

### 5. 🎵 Audio Mixer Editor
- **Command**: `make audio-editor` or `python audio_mixer_editor.py`
- **Purpose**: Real-time sound effect and background music editor for tuning volume levels, sound triggers, pitch variations, and spatial audio channels.

### 6. 🌊 Wave Manager Editor
- **Command**: `make wave-editor` or `python wave_editor.py`
- **Purpose**: Configure wave escalation curves, enemy spawn intervals, and minion caps per wave.

### 7. 🧙 Fire Wizard Spell Editor
- **Command**: `make wizard-editor` or `python wizard_editor.py`
- **Purpose**: Specialized editor for tuning Fire Wizard fireball spell velocities, teleportation cooldowns, and range parameters.

### 8. 👥 Ground Shadow Editor
- **Command**: `make shadow-editor` or `python shadow_editor.py`
- **Purpose**: Adjust ground shadow scale multipliers, vertical Y-offsets, and opacity for every character and enemy sprite.

### 9. ⌨️ Controls & Keybindings Editor
- **Command**: `make controls-editor` or `python controls_editor.py`
- **Purpose**: Remap keyboard keys and gamepad controller buttons.

### 10. 🎨 Power Icons & HUD Editor
- **Command**: `make power-icons-editor` or `python power_icons_editor.py`
- **Purpose**: Customize HUD element positioning, power-up icon coordinates, and status effect overlays.

---

## 📊 Analytics & Telemetry Tools

### Gameplay Analytics Report Tool
Analyze local gameplay tracking databases to generate performance reports on player accuracy, kill counts, and combat efficiency:
```bash
make analyze
# Or: python analyze_gameplay.py
```

### Serverless Telemetry API (`pixel-runner-api/`)
The cloud backend is a **FastAPI** serverless application deployed on Vercel that ingests live telemetry sessions and evaluates aggregated difficulty recommendations.

- **Vercel API URL**: `https://pixel-runner-wheat.vercel.app`
- **Health Check Endpoint**: `https://pixel-runner-wheat.vercel.app/health`
- **Deploying API Updates**:
  ```bash
  npx vercel --prod
  ```

---

## ⚙️ Environment Variables Summary

| Environment Variable | Allowed Values | Default | Purpose |
| :--- | :--- | :--- | :--- |
| `AI_DIFFICULTY` | `EASY`, `MEDIUM`, `HARD`, `NIGHTMARE` | `MEDIUM` | Controls enemy sensory perception and tactical squad aggression. |
| `TRACKER_ENABLED` | `1`, `0` | `0` | Enables live telemetry tracking and metrics collection. |
| `DEBUG_TELEMETRY_HTTP` | `1`, `0` | `0` | Prints verbose HTTP network connection logs for telemetry sync. |
| `PIXEL_RUNNER_API_URL` | URL string | `https://pixel-runner-wheat.vercel.app` | Base URL for the cloud telemetry API server. |
| `GAME_LEVEL_PATH` | File path string | `None` | Overrides the default level configuration JSON file. |

---

## 🛠️ Makefile Command Reference

```bash
make install           # Create .venv and install dependencies
make engine-dev        # Link engine source code in editable mode
make run               # Launch standard game (Full story mode)
make dev               # Launch directly into combat scene (Fast-pass)
make track             # Launch game with live telemetry tracking enabled
make hard              # Launch game in HARD AI difficulty
make nightmare         # Launch game in NIGHTMARE AI difficulty
make test              # Run complete unit test suite (pytest)
make analyze           # Generate gameplay analytics report
make boss-editor       # Launch Boss Visual GUI Editor
make player-editor     # Launch Player Animation & Move-Set Editor
make level-editor      # Launch Level Designer Tool
make entity-editor     # Launch Enemy Stats & Heuristic Editor
make audio-editor      # Launch Audio & SFX Mixer Editor
make wave-editor       # Launch Enemy Wave Spawning Manager
make wizard-editor     # Launch Fire Wizard Spell Editor
make shadow-editor     # Launch Ground Shadow Scale & Offset Editor
make controls-editor   # Launch Keybindings & Gamepad Remapper
make power-icons-editor# Launch Power Icons & HUD Placement Editor
make clean             # Remove virtual environment and bytecode caches
```