@echo off
title VTOP FFCS Assistant
echo ======================================================================
echo   Launching Chrome for VTOP Registration (Port 9222 Enabled)
echo ======================================================================
echo.
echo Launching browser...
start "" "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir="%LOCALAPPDATA%\Google\Chrome\VTOPProfile" --no-first-run --no-default-browser-check "https://vtopreg.vit.ac.in/bookmark/checkRegistration"
echo.
echo [OK] Chrome is now running!
echo.
echo 1. In the Chrome window that just opened, log in to VTOP with your credentials.
echo 2. Navigate to your FFCS / Registration page.
echo 3. Come back here and tell me: "I'm logged in, check my slots"
echo ======================================================================
