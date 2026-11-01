@echo off
title VIT FFCS High-Speed Registration Assistant
cls
echo =====================================================================
echo           VIT VELLORE INSTANT FFCS REGISTRATION BOT
echo   Student: Ayush Agarwal (26BCE3181) ^| Branch: B.Tech CSE (ACE)
echo =====================================================================
echo.
echo Please choose an option:
echo.
echo [1] Scan Live Seat Availability (Check Plan A ^& B teachers)
echo [2] Instant Register ALL 7 Courses (Plan A with Auto Plan B Fallback)
echo [3] View Currently Registered Courses
echo [4] Exit
echo.
set /p choice="Enter choice (1-4): "

if "%choice%"=="1" (
    python fast_ffcs_register.py --scan
    pause
) else if "%choice%"=="2" (
    python fast_ffcs_register.py --all
    pause
) else if "%choice%"=="3" (
    python fast_ffcs_register.py --view
    pause
) else (
    exit
)
