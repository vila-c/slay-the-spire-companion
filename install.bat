@echo off
chcp 65001 >nul
title STS Companion Installer

echo ============================================
echo   STS Companion - One-Click Installer
echo ============================================
echo.

:: ── Check Python ────────────────────────────────────────
echo [1/3] Checking Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found.
    echo         Please install Python 3.8+ from https://www.python.org
    echo         Make sure to check "Add Python to PATH" during install.
    pause
    exit /b 1
)
for /f "tokens=2 delims= " %%v in ('python --version 2^>^&1') do echo        Found Python %%v

:: ── Install Python dependencies ─────────────────────────
echo.
echo [2/3] Installing Python dependencies...
pip install PyQt6 -q
if errorlevel 1 (
    echo [ERROR] Failed to install dependencies.
    pause
    exit /b 1
)
echo        Dependencies installed.

:: ── Build and install mod ───────────────────────────────
echo.
echo [3/3] Building and installing game mod...
python "%~dp0sts-mod\build_mod.py"
if errorlevel 1 (
    echo [ERROR] Mod build failed. See errors above.
    pause
    exit /b 1
)

echo.
echo ============================================
echo   Installation Complete!
echo ============================================
echo.
echo   How to use:
echo     1. Launch Slay the Spire from Steam
echo     2. Select "Play with Mods"
echo     3. Enable "BaseMod" and "STS Companion"
echo     4. The companion pet appears automatically!
echo.
echo   The pet will auto-start with the game.
echo   No manual setup needed after this.
echo ============================================
echo.
pause
