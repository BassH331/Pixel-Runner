#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────────────
# Chatterbox TTS Environment Setup
# Creates a Python 3.11 virtual environment and installs Chatterbox Turbo + 
# PyTorch CPU-only for voice generation on machines without a GPU.
# ──────────────────────────────────────────────────────────────────────────────

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="${SCRIPT_DIR}/chatterbox-venv"
REQUIRED_PYTHON="python3.11"

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║        Chatterbox TTS — Environment Setup                   ║"
echo "╚══════════════════════════════════════════════════════════════╝"

# ── Check for Python 3.11 / 3.12 / python3 ───────────────────────────────────
if command -v python3.11 &> /dev/null; then
    REQUIRED_PYTHON="python3.11"
elif command -v python3 &> /dev/null; then
    REQUIRED_PYTHON="python3"
else
    echo ""
    echo "❌ Python is not installed or not on PATH."
    exit 1
fi

PYTHON_VERSION=$("${REQUIRED_PYTHON}" --version 2>&1)
echo "✅ Found ${PYTHON_VERSION}"

# ── Create virtual environment ────────────────────────────────────────────────
if [ -d "${VENV_DIR}" ]; then
    echo "⚠️ Existing venv found at ${VENV_DIR}. Keeping existing venv..."
fi

if [ ! -d "${VENV_DIR}" ]; then
    echo "📦 Creating Python 3.11 virtual environment..."
    "${REQUIRED_PYTHON}" -m venv "${VENV_DIR}"
fi

# ── Activate ──────────────────────────────────────────────────────────────────
source "${VENV_DIR}/bin/activate"

echo "📦 Upgrading pip, setuptools, wheel..."
pip install --upgrade pip setuptools wheel --quiet

# ── Install PyTorch CPU-only ──────────────────────────────────────────────────
echo "📦 Installing PyTorch (CPU-only)..."
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu --quiet

# ── Install Chatterbox TTS ────────────────────────────────────────────────────
echo "📦 Installing chatterbox-tts dependencies..."
pip install "antlr4-python3-runtime==4.9.3" --no-build-isolation --quiet
pip install chatterbox-tts --quiet

# ── Validate installation ────────────────────────────────────────────────────
echo ""
echo "🔍 Validating installation..."
python -c "
import torch
print(f'   PyTorch {torch.__version__} (CUDA available: {torch.cuda.is_available()})')
from chatterbox.tts import ChatterboxTTS
print('   Chatterbox TTS imported successfully')
print()
print('✅ Setup complete! Chatterbox is ready for voice generation.')
"

echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║  Environment: ${VENV_DIR}                                    "
echo "║  Usage: python voiceover_editor.py                          ║"
echo "╚══════════════════════════════════════════════════════════════╝"
