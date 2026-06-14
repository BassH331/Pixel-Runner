# ── Pixel-Runner Makefile ────────────────────────────────────────────────────
# Standard dev commands for the game project.
#
# Usage:
#   make install   — Create venv and install all dependencies
#   make dev       — Install engine in editable mode (for active engine dev)
#   make run       — Launch the game
#   make sync      — Re-install engine after engine-side changes
#   make clean     — Remove venv and caches

VENV      := .venv
PYTHON    := $(VENV)/bin/python
PIP       := $(VENV)/bin/pip
ENGINE    := /home/chosen333/Software/V3X-Zulfiqar-Gideon

.PHONY: install dev run sync clean

# ── Create venv + install deps from requirements.txt ─────────────────────────
install:
	@echo "🔧 Creating virtual environment..."
	python3 -m venv $(VENV)
	@echo "📦 Installing dependencies..."
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt
	@echo "✅ Done! Run 'make run' to launch the game."

# ── Install engine in editable mode (live link to engine source) ─────────────
dev:
	@echo "🔗 Installing engine in editable mode..."
	$(PIP) install -e $(ENGINE)
	@echo "✅ Engine linked. Changes to V3X source are reflected instantly."

# ── Launch the game ──────────────────────────────────────────────────────────
run:
	@echo "🚀 Launching Pixel Runner..."
	$(PYTHON) main.py

# ── Re-install engine (after engine changes, non-editable mode) ──────────────
sync:
	@echo "🔄 Syncing engine..."
	$(PIP) install $(ENGINE) --force-reinstall --no-deps
	@echo "✅ Engine synced."

# ── Clean everything ─────────────────────────────────────────────────────────
clean:
	@echo "🧹 Cleaning up..."
	rm -rf $(VENV) __pycache__ src/**/__pycache__
	@echo "✅ Clean. Run 'make install' to start fresh."
