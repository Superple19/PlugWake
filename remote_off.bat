@echo off
title PlugWake Remote Off
cd /d "%~dp0"
where uv >nul 2>nul
if errorlevel 1 (
  echo uv was not found.
  echo Run install_uv.bat first, then open this launcher again.
  echo.
  pause
  exit /b 1
)

uv run plugwake-cli off
echo.
pause
