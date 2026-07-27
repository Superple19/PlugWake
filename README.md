# RemotePC

Small Windows scripts for powering on a remote PC through Home Assistant and opening RDP over Tailscale.

## Setup

1. Copy `.env.example` to `.env`.
2. Set `HA_TOKEN` to a Home Assistant long-lived access token.
3. Run `setup_shortcuts.bat` to create desktop shortcuts.
4. Use `Remote On` or `Remote Off` from the desktop.

`.env` is intentionally ignored by Git.

## Files

- `power_on_pc.bat` / `power_off_pc.bat`: launchers
- `scripts/`: PowerShell logic
- `assets/icons/`: shortcut icons
