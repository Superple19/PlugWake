@echo off
title Power On PC
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0power_on_pc.ps1"
echo.
pause
