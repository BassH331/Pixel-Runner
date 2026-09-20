@echo off
setlocal
title Pixel-Runner Environment Setup

echo ===============================================================
echo   Pixel-Runner & V3X Engine Windows Environment Setup
echo ===============================================================

where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Python was not found in your PATH!
    echo Please install Python 3.10+ from https://www.python.org/
    echo Make sure to check "Add Python to PATH" during installation.
    pause
    exit /b 1
)

python setup_env.py
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Setup encountered errors. Please check output above.
    pause
    exit /b 1
)

echo.
echo Setup finished successfully! Press any key to exit.
pause
