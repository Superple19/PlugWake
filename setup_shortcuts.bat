@echo off
title Setup RemotePC Shortcuts
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\setup_shortcuts.ps1"
echo.
pause
