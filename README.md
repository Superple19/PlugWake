# RemotePC

Portable remote PC controls using Home Assistant smart plugs, SSH, and RDP.

Tailscale is recommended for private networking and MagicDNS, but not required. The client only needs network access to Home Assistant and the target PC.

## Features

- Power on a remote Windows PC through a Home Assistant smart plug.
- Open RDP when the target PC becomes reachable.
- Shut down Windows over SSH, then turn the plug off only after repeated low-power readings.
- Reboot the target PC over SSH from the GUI or CLI.
- Use simple Windows `.bat` launchers, Linux `.sh` launchers, the Python CLI, or the optional GUI.

Remote OS switching is intentionally not supported by default.

## Requirements

- Home Assistant with a controllable smart plug and power sensor.
- SSH access to the target PC for shutdown and reboot.
- For Windows RDP hosts, Windows Pro, Enterprise, or Education is required. Windows Home cannot act as a built-in Remote Desktop host.
- Linux clients need FreeRDP installed for RDP launch:
  - Ubuntu 24.04: `sudo apt install freerdp3-x11`
  - Ubuntu 26.04 / Debian testing: `sudo apt install freerdp-x11`
  - Fedora: `sudo dnf install freerdp`
  - Arch / Manjaro: `sudo pacman -S freerdp`

## Setup

1. Run `install_uv.bat` if `uv` is not installed.
2. Copy `.env.example` to `.env`.
3. Fill in the Home Assistant token, entity IDs, RDP host, SSH target, and target OS.
4. On Windows, run `setup_shortcuts.bat` to create desktop shortcuts. On Linux, run `bash setup_desktop_entries.sh`.
5. Use `Remote On` or `Remote Off` from the desktop.

`.env` is intentionally ignored by Git.

## GUI

The Windows shortcuts use `uv` and the Python CLI. The optional GUI uses PySide6.

```bat
uv sync
uv run remotepc
```

Or run:

```bat
launch_gui.bat
```

If `uv` is not installed, run:

```bat
install_uv.bat
```

## Python CLI

The Python path supports Windows clients with `mstsc.exe` and Linux clients with `xfreerdp`.

```bat
uv run remotepc-cli on
uv run remotepc-cli off
uv run remotepc-cli reboot
uv run remotepc-cli test-ha
uv run remotepc-cli test-rdp
uv run remotepc-cli setup-shortcuts
```

`setup-shortcuts` creates Windows desktop shortcuts. Use `bash setup_desktop_entries.sh` on Linux.

For `Remote Off` and `Reboot Now`, Paramiko tries key/agent authentication first, then prompts for a password when needed. Passwords are retried up to three times and are never saved.

Set `TARGET_OS=windows` for Windows hosts or `TARGET_OS=linux` for Linux hosts. Linux hosts use `sudo -S systemctl poweroff` and `sudo -S systemctl reboot`, so the SSH user must be allowed to run those commands with sudo.

## Safety

- `.env` is ignored by Git and should contain all local secrets and host-specific values.
- SSH passwords are never saved.
- Failed SSH shutdowns do not cut plug power.
- Unavailable or invalid power sensor readings do not cut plug power.
- Remote Off waits for repeated low-power readings before switching the plug off.

## Files

- `power_on_pc.bat`: Windows shortcut-friendly launcher for Remote On
- `power_off_pc.bat`: Windows shortcut-friendly launcher for Remote Off
- `setup_shortcuts.bat`: creates desktop shortcuts
- `launch_gui.bat`: optional PySide6 GUI launcher
- `install_uv.bat`: optional uv installer using winget
- `remote_on.sh`: Linux launcher for Remote On
- `remote_off.sh`: Linux launcher for Remote Off
- `setup_desktop_entries.sh`: creates Linux desktop entries
- `launch_gui.sh`: Linux PySide6 GUI launcher
- `src/remotepc/`: Python CLI and GUI implementation
- `assets/icons/`: shortcut `.ico` files
- `assets/source-icons/`: source PNG icons
- `docs/`: planning notes
