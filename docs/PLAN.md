# RemotePC Plan

## Current Goal

Keep RemotePC focused on safe remote Windows power control:

- power on through Home Assistant
- open RDP when reachable
- shut down or reboot through SSH
- avoid unsafe smart plug cutoffs
- keep simple `.bat` launchers, Python CLI, and optional GUI

## Done

Stable Windows launchers:

- `power_on_pc.bat`
- `power_off_pc.bat`
- `setup_shortcuts.bat`

Python GUI and CLI:

- `uv` project setup
- PySide6 GUI
- `remotepc-cli on`
- `remotepc-cli off`
- `remotepc-cli reboot`
- `remotepc-cli test-ha`
- `remotepc-cli test-rdp`
- `remotepc-cli setup-shortcuts`
- Paramiko SSH password prompt for SSH actions
- Reboot Now action
- Home Assistant and RDP tests

Safety behavior:

- `.env` for local settings
- no SSH password storage
- no plug cutoff after SSH failure
- repeated low-power checks before plug cutoff
- OS switching removed from default controls

## Next

Defer until needed:

- Linux client support with `xfreerdp`
- GUI polish after real usage
- packaging only if `uv run` becomes annoying

## Non-Goals For Now

- no cloud account
- no Home Assistant automation
- no password storage
- no multi-PC dashboard
- no background service
- no tray app
- no default OS switching or one-time Linux boot controls
