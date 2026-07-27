@echo off
title Power Off PC
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0power_off_pc.ps1"
echo.
pause
