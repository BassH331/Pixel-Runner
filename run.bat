@echo off
setlocal

title Pixel-Runner Game Launcher

if exist .venv\Scripts\python.exe (
    .venv\Scripts\python.exe main.py %*
) else (
    echo [WARNING] .venv virtual environment not found. Running with global python...
    python main.py %*
)

if %errorlevel% neq 0 (
    echo.
    echo Game exited with error code %errorlevel%.
    pause
)
