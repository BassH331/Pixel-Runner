#!/usr/bin/env bash

if [ -f ".venv/bin/python" ]; then
    .venv/bin/python main.py "$@"
else
    echo "⚠️ .venv not found. Running with global python..."
    python3 main.py "$@"
fi
