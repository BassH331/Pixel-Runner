# ── Pixel-Runner Makefile ────────────────────────────────────────────────────
# Standard dev commands for launching game modes, tests, and plugin editors.

VENV      := .venv
PYTHON    := $(VENV)/bin/python
PIP       := $(VENV)/bin/pip
ENGINE    := /home/chosen333/Software/V3X-Zulfiqar-Gideon

.PHONY: install engine-dev run dev track hard nightmare test analyze clean \
        boss-editor player-editor level-editor entity-editor audio-editor \
        wave-editor wizard-editor shadow-editor controls-editor power-icons-editor

# ── Setup & Installation ───────────────────────────────────────────────────
install:
	@echo "🔧 Creating virtual environment..."
	python3 -m venv $(VENV)
	@echo "📦 Installing dependencies..."
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt
	@echo "✅ Setup complete! Run 'make run' to launch the game."

engine-dev:
	@echo "🔗 Linking engine source in editable mode..."
	$(PIP) install -e $(ENGINE)
	@echo "✅ Engine linked. Engine source modifications reflect instantly."

# ── Game Execution Modes ───────────────────────────────────────────────────
run:
	@echo "🚀 Launching Pixel Runner (Full Experience with Cutscenes)..."
	$(PYTHON) main.py

dev:
	@echo "⚡ Launching directly into gameplay (Bypassing Cutscenes & Menus)..."
	$(PYTHON) main.py --dev

track:
	@echo "📊 Launching game with live Telemetry Tracking enabled..."
	$(PYTHON) main.py --track

hard:
	@echo "🔥 Launching game in HARD AI Difficulty..."
	AI_DIFFICULTY=HARD $(PYTHON) main.py

nightmare:
	@echo "💀 Launching game in NIGHTMARE AI Difficulty..."
	AI_DIFFICULTY=NIGHTMARE $(PYTHON) main.py

# ── Testing & Telemetry Analysis ────────────────────────────────────────────
test:
	@echo "🧪 Running complete unit test suite..."
	PYTHONPATH=. $(VENV)/bin/pytest tests/

analyze:
	@echo "📈 Running Telemetry Analytics Tool..."
	$(PYTHON) analyze_gameplay.py

# ── Plugin Editors & Visual Tools ───────────────────────────────────────────
boss-editor:
	@echo "👑 Launching Boss Stats & Combat Phase Visual Editor..."
	$(PYTHON) boss_editor.py

player-editor:
	@echo "🎮 Launching Player Animation & Move-Set Editor..."
	$(PYTHON) player_editor.py

level-editor:
	@echo "🗺️ Launching Level Designer & Environment Editor..."
	$(PYTHON) level_editor.py

entity-editor:
	@echo "👾 Launching Enemy Stats & Heuristics Editor..."
	$(PYTHON) entity_editor.py

audio-editor:
	@echo "🎵 Launching Audio Mixer & SFX Channel Editor..."
	$(PYTHON) audio_mixer_editor.py

wave-editor:
	@echo "🌊 Launching Enemy Wave Spawning Manager Editor..."
	$(PYTHON) wave_editor.py

wizard-editor:
	@echo "🧙 Launching Fire Wizard Spell & Teleport Editor..."
	$(PYTHON) wizard_editor.py

shadow-editor:
	@echo "👥 Launching Ground Shadow Scale & Offset Editor..."
	$(PYTHON) shadow_editor.py

controls-editor:
	@echo "⌨️ Launching Keybindings & Gamepad Remapper..."
	$(PYTHON) controls_editor.py

power-icons-editor:
	@echo "🎨 Launching Power Icons & HUD Layout Editor..."
	$(PYTHON) power_icons_editor.py

# ── Clean ───────────────────────────────────────────────────────────────────
clean:
	@echo "🧹 Cleaning virtual environment and bytecode caches..."
	rm -rf $(VENV) __pycache__ src/**/__pycache__
	@echo "✅ Clean complete. Run 'make install' to reinstall."
