# RemotePC Plan

## Goal

Keep the current Windows `.bat` shortcuts working, then add a cross-platform Python GUI for users who want one control panel on Windows or Linux.

## Current Stable Layer

Keep these as the simple Windows path:

- `power_on_pc.bat`
- `power_off_pc.bat`
- `boot_linux_once.bat`
- `setup_shortcuts.bat`
- `scripts/*.ps1`

## Target GUI

Use PySide6.

Minimum actions:

- Remote On
- Remote Off
- Boot Linux Once
- Save settings
- Test Home Assistant
- Test RDP host
- Show boot entries

## Cross-Platform Split

Shared Python logic:

- load `.env`
- call Home Assistant API
- read plug state
- read watt sensor
- set plug on/off
- check TCP ports
- run SSH shutdown
- stream logs to GUI

OS-specific logic:

- Windows RDP: `mstsc /v:<host> /f`
- Linux RDP: `xfreerdp /v:<host> /f`
- Windows boot once: `bcdedit /bootsequence <id>`
- Linux boot once: defer until needed

## Non-Goals For Now

- no cloud account
- no Home Assistant automation
- no password storage
- no multi-PC dashboard
- no background service
- no tray app
