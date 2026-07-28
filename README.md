# RemotePC

Portable remote PC controls using Home Assistant smart plugs, SSH, and RDP.

Tailscale is recommended for private networking and MagicDNS, but not required. The client only needs network access to Home Assistant and the target PC.

## Setup

1. Copy `.env.example` to `.env`.
2. Fill in the Home Assistant token, entity IDs, RDP host, and SSH target.
3. Run `setup_shortcuts.bat` to create desktop shortcuts.
4. Use `Remote On` or `Remote Off` from the desktop.

`.env` is intentionally ignored by Git.

## GUI

The Windows shortcuts still work without Python. The optional GUI uses `uv` and PySide6.

```bat
uv sync
uv run remotepc
```

Or run:

```bat
launch_gui.bat
```

## Python CLI

The Python path currently targets Windows-to-Windows control.

```bat
uv run remotepc-cli on
uv run remotepc-cli off
```

For `Remote Off`, the GUI uses Paramiko for SSH. It tries key/agent authentication first, then opens a password prompt when needed. Passwords are retried up to three times and are never saved.

The CLI does not prompt for SSH passwords. Use SSH key login for non-GUI runs.

## Files

- `power_on_pc.bat`: Windows shortcut-friendly launcher for Remote On
- `power_off_pc.bat`: Windows shortcut-friendly launcher for Remote Off
- `boot_linux_once.bat`: Windows launcher for one-time Linux boot
- `setup_shortcuts.bat`: creates desktop shortcuts
- `launch_gui.bat`: optional PySide6 GUI launcher
- `scripts/`: PowerShell implementation
- `src/remotepc/`: Python CLI and GUI implementation
- `assets/icons/`: shortcut `.ico` files
- `assets/source-icons/`: source PNG icons
- `docs/`: planning notes
