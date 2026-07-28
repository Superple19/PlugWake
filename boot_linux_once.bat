@echo off
title Boot Linux Once
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\boot_linux_once.ps1"
echo.
pause
