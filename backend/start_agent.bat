@echo off
title Janus Windows Agent
cd /d "%~dp0"

echo ============================================
echo   Janus Windows Agent Launcher
echo ============================================
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found!
    echo Please install Python 3.12: winget install Python.Python.3.12
    pause
    exit /b 1
)

echo [1/3] Installing dependencies...
pip install fastapi uvicorn pillow pywin32 --quiet --upgrade

echo [2/3] Starting Windows Agent on port 5001...
echo.
echo Docker access URL: http://host.docker.internal:5001
echo.

echo [3/3] Agent running! Press Ctrl+C to stop.
echo ============================================
echo.

python windows_agent.py

pause
