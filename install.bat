@echo off
:: =============================================================================
::  AI Prompt Generator — Windows Install Script
::  Blockchain & DeFi Dev Edition
:: =============================================================================

setlocal EnableDelayedExpansion

:: ── Banner ───────────────────────────────────────────────────────────────────
echo.
echo  +----------------------------------------------------------+
echo  ^|       ^<^> AI Prompt Generator ^<^>                          ^|
echo  ^|          Blockchain ^& DeFi Dev Edition                   ^|
echo  +----------------------------------------------------------+
echo.

:: ── Project root (directory of this script) ──────────────────────────────────
cd /d "%~dp0"

:: ── Step 1: Check Python 3 ────────────────────────────────────────────────────
echo [INFO]  Checking for Python 3...
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH.
    echo         Please install Python 3.9+ from https://www.python.org/downloads/
    echo         Make sure to check "Add Python to PATH" during installation.
    pause
    exit /b 1
)

for /f "tokens=2" %%v in ('python --version 2^>^&1') do set PY_VERSION=%%v
echo [OK]    Found Python %PY_VERSION%

:: Require Python 3.9+
for /f "tokens=1,2 delims=." %%a in ("%PY_VERSION%") do (
    set PY_MAJOR=%%a
    set PY_MINOR=%%b
)
if %PY_MAJOR% LSS 3 (
    echo [ERROR] Python 3.9 or higher is required. Found %PY_VERSION%
    pause
    exit /b 1
)
if %PY_MAJOR% EQU 3 if %PY_MINOR% LSS 9 (
    echo [ERROR] Python 3.9 or higher is required. Found %PY_VERSION%
    pause
    exit /b 1
)

:: ── Step 2: Create virtual environment ───────────────────────────────────────
echo.
echo ^>^>  Creating virtual environment (.venv)
if exist ".venv\" (
    echo [WARN]  .venv already exists — skipping creation
) else (
    python -m venv .venv
    echo [OK]    Virtual environment created at .venv\
)

:: ── Step 3: Install dependencies ─────────────────────────────────────────────
echo.
echo ^>^>  Installing Python dependencies
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet
echo [OK]    Dependencies installed (Flask)

:: ── Step 4: Create run.bat ───────────────────────────────────────────────────
echo.
echo ^>^>  Creating run.bat launcher script
(
    echo @echo off
    echo :: AI Prompt Generator — Launch Script
    echo cd /d "%%~dp0"
    echo.
    echo if not exist ".venv\" (
    echo     echo [ERROR] .venv not found. Run install.bat first.
    echo     pause
    echo     exit /b 1
    echo ^)
    echo.
    echo call .venv\Scripts\activate.bat
    echo set FLASK_DEBUG=False
    echo.
    echo echo.
    echo echo   ^<^>  Starting AI Prompt Generator...
    echo echo   Open http://localhost:5000 in your browser
    echo echo   Press Ctrl+C to stop
    echo echo.
    echo start /b cmd /c "timeout /t 2 ^>nul ^&^& start http://localhost:5000"
    echo python app.py
) > run.bat
echo [OK]    run.bat created

:: ── Deactivate venv (user will use run.bat) ───────────────────────────────────
call deactivate 2>nul

:: ── Done ─────────────────────────────────────────────────────────────────────
echo.
echo  +----------------------------------------------------------+
echo  ^|  OK  Installation complete!                             ^|
echo  +----------------------------------------------------------+
echo.
echo   Quick Start:
echo     Double-click run.bat   — start the app ^& open dashboard
echo     Or open http://localhost:5000 in your browser manually
echo.
echo   Manual start:
echo     .venv\Scripts\activate.bat
echo     python app.py
echo.
echo   Enable debug mode:
echo     Set FLASK_DEBUG=true in run.bat before running
echo.

:: ── Step 5: Launch the app and open browser ──────────────────────────────────
echo [INFO]  Launching the app...
echo.
start /b cmd /c "timeout /t 2 >nul && start http://localhost:5000"
python app.py

endlocal
