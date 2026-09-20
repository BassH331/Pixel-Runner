# Cross-Platform Environment Setup Guide

This project is configured for **instant 1-click automated setup** across **Windows**, **Linux**, and **macOS**.

---

## ⚡ Quick Start (Under 1 Minute)

### 🪟 Windows Setup
1. Double-click `setup.bat` (or run `python setup_env.py` in Command Prompt / PowerShell).
2. Double-click `run.bat` (or run `run.bat --dev` in Command Prompt / PowerShell) to launch the game!

---

### 🐧 Linux & 🍎 macOS Setup
1. Run `./setup.sh` (or `python3 setup_env.py`) in terminal.
2. Run `./run.sh` (or `./run.sh --dev`) to launch the game!

---

## 🛠️ What `setup_env.py` Does Automatically:
- Creates a isolated `.venv` Python virtual environment.
- Upgrades `pip`, `setuptools`, and `wheel`.
- Automatically locates the local `V3X-Zulfiqar-Gideon` engine directory and links it in **editable mode (`pip install -e`)**.
- Installs all dependencies from `requirements.txt`.
- Verifies system compatibility (`pygame`, `v3x_zulfiqar_gideon`, `numpy`, `edge-tts`).

---

## 💻 Working with Editors & IDEs

### VSCode / Cursor / Antigravity IDE:
- Open the workspace folder in your IDE.
- Select `.venv/Scripts/python.exe` (Windows) or `.venv/bin/python` (Linux/macOS) as your Python Interpreter.
- `pyrightconfig.json` and `pyrefly.toml` use cross-platform relative paths `../V3X-Zulfiqar-Gideon` to resolve types automatically on any OS.

---

## 🚀 Dev Commands (via Makefile or Terminal)

| Action | Windows | Linux / macOS |
| :--- | :--- | :--- |
| **Install / Reset Env** | `setup.bat` | `make install` or `./setup.sh` |
| **Launch Game (Dev Mode)** | `run.bat --dev` | `./run.sh --dev` |
| **Run Unit Tests** | `.venv\Scripts\pytest tests/` | `make test` |
| **Boss Editor** | `.venv\Scripts\python boss_editor.py` | `.venv/bin/python boss_editor.py` |
| **Player Editor** | `.venv\Scripts\python player_editor.py` | `.venv/bin/python player_editor.py` |
| **Level Editor** | `.venv\Scripts\python level_editor.py` | `.venv/bin/python level_editor.py` |
