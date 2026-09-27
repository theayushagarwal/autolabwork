@echo off
setlocal enabledelayedexpansion
title Autonomous Assessment & Coding Engine

echo ======================================================================
echo   Autonomous Engine - 1-Click Quick Launcher
echo ======================================================================
echo.

REM 1. Verify Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not added to your system PATH!
    echo Please install Python 3.10+ from https://www.python.org
    echo (Make sure to check "Add Python to PATH" during installation)
    echo.
    pause
    exit /b 1
)

REM 2. Check and auto-install dependencies if missing
echo [*] Checking Python dependencies...
python -c "import selenium, requests" >nul 2>&1
if %errorlevel% neq 0 (
    echo [*] Installing required packages (selenium, requests)...
    pip install selenium requests
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to install dependencies via pip.
        pause
        exit /b 1
    )
    echo [OK] Dependencies installed successfully.
) else (
    echo [OK] All dependencies are ready.
)

REM 3. First-time setup: Prompt for Groq API key if missing
if not exist "%~dp0.env" (
    if "%GROQ_API_KEY%"=="" (
        echo.
        echo ======================================================================
        echo   First-Time Setup: Groq API Key Required
        echo ======================================================================
        echo Get a free key in 30 seconds at: https://console.groq.com/keys
        echo.
        set /p USER_KEY="Paste your Groq API key here (starts with gsk_): "
        if not "!USER_KEY!"=="" (
            echo GROQ_API_KEY=!USER_KEY! > "%~dp0.env"
            echo [OK] Saved your API key to .env!
        ) else (
            echo [!] No key provided. You can add it to .env later.
        )
        echo ======================================================================
    )
)

echo.
echo [*] Launching Autonomous Engine...
echo ======================================================================
echo.

python "%~dp0solve.py" %*

echo.
echo [*] Process finished.
pause
