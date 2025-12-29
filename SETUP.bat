@echo off
REM ============================================================================
REM  CVE_Scan - One-Click Setup for Windows
REM  Just run this file and everything will be set up automatically
REM ============================================================================

setlocal enabledelayedexpansion

cls
echo ============================================================================
echo.
echo   CVE_SCAN - Automatic Setup
echo   Version 1.0
echo.
echo ============================================================================
echo.

REM Check if Python is installed
echo [1/5] Checking Python installation...
python --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo ERROR: Python 3.11+ is required but not installed!
    echo.
    echo Please download Python from: https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during installation
    echo.
    pause
    exit /b 1
)
for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo ✓ Python %PYTHON_VERSION% found

REM Check if nmap is installed
echo [2/5] Checking Nmap installation...
nmap --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo WARNING: Nmap not found in PATH
    echo This is required for network scanning
    echo.
    echo Download from: https://nmap.org/download.html
    echo.
    pause
)
echo ✓ Nmap check completed

REM Create virtual environment
echo [3/5] Creating Python environment...
if not exist "venv" (
    python -m venv venv
    echo ✓ Virtual environment created
) else (
    echo ✓ Virtual environment already exists
)

REM Activate virtual environment and install packages
echo [4/5] Installing packages...
call venv\Scripts\activate.bat
pip install -q --upgrade pip
pip install -q -r requirements.txt
if errorlevel 1 (
    echo ERROR: Failed to install packages
    pause
    exit /b 1
)
echo ✓ Packages installed successfully

REM Verify installation
echo [5/5] Verifying installation...
python verify_installation.py
if errorlevel 1 (
    echo.
    echo WARNING: Some verifications failed, but trying to run anyway...
    echo.
)

REM Success
cls
echo ============================================================================
echo.
echo   ✓ CVE_SCAN SETUP COMPLETE!
echo.
echo ============================================================================
echo.
echo   You can now start scanning! 
echo.
echo   To run the application, double-click:  RUN_CVESCAN.bat
echo   Or type in terminal:                    python app.py
echo.
echo ============================================================================
echo.
pause
