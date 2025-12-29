@echo off
setlocal

REM One-click Npcap installer launcher
REM This will run the PowerShell installer with admin elevation if needed.

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\install_npcap.ps1"

if %ERRORLEVEL% EQU 0 (
  echo [SUCCESS] Npcap installed or already present.
) else (
  echo [INFO] Installer exited with code %ERRORLEVEL%.
  echo If a browser opened, please install Npcap manually and rerun.
)

pause
