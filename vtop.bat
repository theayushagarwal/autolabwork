@echo off
title VTOP FFCS Assistant
echo ======================================================================
echo   Launching Chrome for VTOP Registration (Port 9222 Enabled)
echo ======================================================================
echo.

set CHROME_EXE=""

if exist "C:\Program Files\Google\Chrome\Application\chrome.exe" (
    set CHROME_EXE="C:\Program Files\Google\Chrome\Application\chrome.exe"
) else if exist "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe" (
    set CHROME_EXE="C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
) else if exist "%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe" (
    set CHROME_EXE="%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"
) else (
    set CHROME_EXE=chrome.exe
)

echo Launching Chrome: %CHROME_EXE%
start "" %CHROME_EXE% --remote-debugging-port=9222 --user-data-dir="%LOCALAPPDATA%\Google\Chrome\VTOPProfile" --no-first-run --no-default-browser-check "https://vtopreg.vit.ac.in/indexplus/"
echo.
echo [OK] Chrome is now running!
echo.
echo 1. In the Chrome window that just opened, log in to VTOP with your credentials.
echo 2. Navigate to your FFCS / Registration page.
echo ======================================================================
