#!/usr/bin/env python3
"""
Pixel-Runner & V3X Engine Cross-Platform Environment Installer

Automates environment setup across Windows, Linux, and macOS:
1. Creates Python virtual environment (.venv)
2. Upgrades pip and core build tools
3. Dynamically locates and installs V3X-Zulfiqar-Gideon engine in editable mode
4. Installs all project dependencies from requirements.txt
5. Verifies environment integrity (pygame, v3x_zulfiqar_gideon, edge-tts, etc.)
"""

import sys
import os
import subprocess
import shutil
from pathlib import Path

def print_step(msg: str) -> None:
    print(f"\n[SETUP] {msg}")

def run_cmd(cmd: list[str], cwd: str | None = None, check: bool = True) -> subprocess.CompletedProcess:
    print(f"  > {' '.join(cmd)}")
    return subprocess.run(cmd, cwd=cwd, check=check)

def main():
    print("===============================================================")
    print("  Pixel-Runner & V3X Engine Cross-Platform Setup")
    print("===============================================================")

    # 1. System checks
    py_version = sys.version_info
    print(f"Python Version: {py_version.major}.{py_version.minor}.{py_version.micro} ({sys.platform})")
    if py_version < (3, 10):
        print("ERROR: Python 3.10 or higher is required.")
        sys.exit(1)

    project_root = Path(__file__).resolve().parent
    venv_dir = project_root / ".venv"
    
    # Determine OS-specific venv executable paths
    if sys.platform == "win32":
        venv_python = venv_dir / "Scripts" / "python.exe"
        venv_pip = venv_dir / "Scripts" / "pip.exe"
    else:
        venv_python = venv_dir / "bin" / "python"
        venv_pip = venv_dir / "bin" / "pip"

    # 2. Create Virtual Environment if needed
    print_step("Checking Virtual Environment (.venv)...")
    if not venv_dir.exists():
        print("Creating .venv virtual environment...")
        run_cmd([sys.executable, "-m", "venv", str(venv_dir)])
        print("✅ Virtual environment created.")
    else:
        print("✅ Virtual environment already exists.")

    # 3. Upgrade Pip & Build Tools
    print_step("Upgrading pip & setuptools in .venv...")
    run_cmd([str(venv_python), "-m", "pip", "install", "--upgrade", "pip", "setuptools", "wheel"])

    # 4. Locate and Install V3X Engine (V3X-Zulfiqar-Gideon)
    print_step("Locating V3X-Zulfiqar-Gideon Engine Source...")
    engine_candidates = [
        os.environ.get("ENGINE_PATH"),
        project_root.parent / "V3X-Zulfiqar-Gideon",
        project_root.parent / "v3x-zulfiqar-gideon",
        project_root / "V3X-Zulfiqar-Gideon",
    ]

    engine_path = None
    for cand in engine_candidates:
        if cand and Path(cand).exists() and (Path(cand) / "v3x_zulfiqar_gideon").exists():
            engine_path = Path(cand).resolve()
            break

    if engine_path:
        print(f"✅ Found V3X Engine at: {engine_path}")
        print_step("Installing V3X Engine in editable mode (-e)...")
        run_cmd([str(venv_pip), "install", "-e", str(engine_path)])
    else:
        print("⚠️ Warning: Could not locate V3X-Zulfiqar-Gideon engine directory locally.")
        print("Will attempt to install pre-built package from PyPI or requirements.txt...")

    # 5. Install Project Dependencies
    requirements_file = project_root / "requirements.txt"
    if requirements_file.exists():
        print_step("Installing dependencies from requirements.txt...")
        run_cmd([str(venv_pip), "install", "-r", str(requirements_file)])
    else:
        print("⚠️ requirements.txt not found. Installing base dependencies directly...")
        run_cmd([str(venv_pip), "install", "pygame>=2.5.0", "numpy>=1.24.0", "edge-tts", "requests"])

    # 6. Verify Installation
    print_step("Verifying Environment Integrity...")
    verification_script = (
        "import pygame; "
        "import v3x_zulfiqar_gideon; "
        "import numpy; "
        "print('   [OK] pygame version:', pygame.__version__); "
        "print('   [OK] v3x_zulfiqar_gideon loaded from:', v3x_zulfiqar_gideon.__file__); "
        "print('   [OK] numpy version:', numpy.__version__)"
    )

    try:
        run_cmd([str(venv_python), "-c", verification_script])
        print("✅ Environment verification passed successfully!")
    except subprocess.CalledProcessError:
        print("⚠️ Verification check failed. Please check installation logs above.")
        sys.exit(1)

    # 7. Success Banner
    print("\n===============================================================")
    print("  🎉 Setup Completed Successfully!")
    print("===============================================================")
    print("To launch Pixel-Runner:")
    if sys.platform == "win32":
        print("  Double-click `run.bat` or run in terminal:")
        print("    .venv\\Scripts\\python.exe main.py")
        print("    .venv\\Scripts\\python.exe main.py --dev")
    else:
        print("  Run in terminal:")
        print("    ./run.sh")
        print("    .venv/bin/python main.py --dev")
    print("===============================================================\n")

if __name__ == "__main__":
    main()
