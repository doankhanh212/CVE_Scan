@echo off
REM ============================================================================
REM  CVE_Scan - Run Application
REM  Double-click this file to start CVE_Scan GUI
REM ============================================================================

setlocal enabledelayedexpansion

REM Check if virtual environment exists
if not exist "venv" (
    echo Virtual environment not found!
    echo Please run SETUP.bat first
    pause
    exit /b 1
)

REM Activate and run
call venv\Scripts\activate.bat
python app.py
pause
