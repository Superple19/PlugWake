@echo off
title Install uv
where uv >nul 2>nul
if not errorlevel 1 (
  echo uv is already installed.
  uv --version
  echo.
  pause
  exit /b 0
)

where winget >nul 2>nul
if errorlevel 1 (
  echo winget was not found.
  echo Install uv manually from:
  echo https://docs.astral.sh/uv/getting-started/installation/
  echo.
  pause
  exit /b 1
)

winget install --id astral-sh.uv -e
echo.
echo Restart your terminal or Explorer if uv is still not found.
echo.
pause
