#!/usr/bin/env bash
set -e

echo "==============================================================="
echo "  Pixel-Runner & V3X Engine Linux/macOS Environment Setup"
echo "==============================================================="

PYTHON_BIN=$(which python3 || which python)

if [ -z "$PYTHON_BIN" ]; then
    echo "ERROR: python3 was not found in PATH."
    exit 1
fi

"$PYTHON_BIN" setup_env.py
