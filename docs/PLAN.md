# RemotePC Plan

## Goal

Keep the current Windows `.bat` shortcuts working, then add a Python GUI for users who want one control panel.

## Current Stable Layer

Keep these as the simple Windows path:

- `power_on_pc.bat`
- `power_off_pc.bat`
- `setup_shortcuts.bat`
- `scripts/*.ps1`

## Target GUI

Use PySide6.

Minimum actions:

- Remote On
- Remote Off
- Reboot Now
- Save settings
- Test Home Assistant
- Test RDP host

## Cross-Platform Split

Shared Python logic:

- load `.env`
- call Home Assistant API
- read plug state
- read watt sensor
- set plug on/off
- check TCP ports
- run SSH shutdown
- run SSH reboot
- stream logs to GUI

OS-specific logic:

- Windows RDP: `mstsc /v:<host> /f`
- Linux RDP support: defer until needed
- OS switching: do not support by default

## Non-Goals For Now

- no cloud account
- no Home Assistant automation
- no password storage
- no multi-PC dashboard
- no background service
- no tray app
