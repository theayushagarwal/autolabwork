@echo off
setlocal enabledelayedexpansion
title Autonomous Assessment and Coding Engine

echo ======================================================================
echo   Autonomous Engine - 1-Click Quick Launcher
echo ======================================================================
echo.

REM 1. Find working Python command (checks 'python', then 'py')
set PYTHON_CMD=
python --version >nul 2>&1
if not errorlevel 1 (
    set PYTHON_CMD=python
) else (
    py --version >nul 2>&1
    if not errorlevel 1 (
        set PYTHON_CMD=py
    )
)

if "%PYTHON_CMD%"=="" (
    echo ======================================================================
    echo   [ERROR] Python is NOT installed or not in your Windows PATH!
    echo ======================================================================
    echo.
    echo   Easiest fix in 1 minute:
    echo   1. Open the "Microsoft Store" app on Windows.
    echo   2. Search for "Python 3.12" and click "Get" or "Install".
    echo   3. Once installed, reopen Command Prompt and run solve.bat again.
    echo ======================================================================
    echo.
    pause
    exit /b 1
)

echo [OK] Using Python: %PYTHON_CMD%
%PYTHON_CMD% --version
echo.

REM 2. Check and auto-install dependencies if missing
echo [*] Checking Python dependencies...
%PYTHON_CMD% -c "import selenium, requests" >nul 2>&1
if errorlevel 1 (
    echo [*] Installing required packages: selenium, requests...
    %PYTHON_CMD% -m pip install selenium requests
    if errorlevel 1 (
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
        set /p USER_KEY="Paste your Groq API key here [starts with gsk_]: "
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

%PYTHON_CMD% "%~dp0solve.py" %*

echo.
echo [*] Process finished.
pause
