# PlugWake

PlugWake powers on a remote PC through a Home Assistant smart plug, waits for RDP, and shuts the PC down safely before cutting plug power.

It is built for small personal setups: one target PC, one smart plug, Home Assistant, SSH, and RDP. Tailscale or another private network is recommended, but not required.

## What It Does

- Turns a Home Assistant smart plug on or off.
- Reads a Home Assistant power sensor before making power decisions.
- Opens RDP when the target PC becomes reachable.
- Shuts down or reboots the target PC over SSH.
- Supports Windows and Linux clients.
- Supports Windows and Linux target hosts.

Remote OS switching is intentionally not supported.

## Requirements

- Home Assistant with a controllable smart plug and power sensor.
- SSH access to the target PC for shutdown and reboot.
- An RDP server on the target PC. Remote On treats the PC as online once TCP port 3389 opens.
- `uv` for running the Python CLI and GUI.

Target PC notes:

- Enable the BIOS/UEFI setting that powers the PC on when AC power returns (often called "Restore on AC Power Loss" or "AC Power Recovery"). Remote On starts the PC by turning the plug on, so the PC will not boot without it.
- Disable sleep on the target PC, or use hibernate instead. A sleeping PC draws little power and does not answer RDP, so PlugWake treats it as off: Remote On power-cycles it and Remote Off cuts its power, which loses the sleeping session.
- Windows targets need OpenSSH Server enabled. Built-in Remote Desktop hosting requires Windows Pro, Enterprise, or Education; Windows Home cannot act as a Remote Desktop host.
- Linux targets need an SSH server and an RDP server such as `xrdp`. Without an RDP server, the PC still powers on, but Remote On reports failure after `RDP_WAIT_SECONDS`.

Linux clients need FreeRDP for RDP launch:

```bash
# Ubuntu 24.04 / Zorin OS 18
sudo apt install freerdp3-x11

# Ubuntu 26.04 / Debian testing
sudo apt install freerdp-x11

# Fedora
sudo dnf install freerdp

# Arch / Manjaro
sudo pacman -S freerdp
```

## Network

PlugWake talks to Home Assistant over its REST API and uses SSH/RDP to reach the target PC. Home Assistant must already be set up with a smart plug switch entity and a power sensor entity.

The HA token is sent as a Bearer token on every API request. Use an `https://` Home Assistant URL when the connection crosses an untrusted network. If using `http://`, keep Home Assistant on a trusted LAN or private Tailscale network and never expose port 8123 publicly.

- Home Assistant: <https://www.home-assistant.io/>
- Home Assistant REST API: <https://developers.home-assistant.io/docs/api/rest/>
- Home Assistant long-lived access tokens: <https://developers.home-assistant.io/docs/auth_api/#long-lived-access-token>

PlugWake rejects SSH servers that are not already in the client's known-hosts file. Verify the target fingerprint once with your system SSH client before using Remote Off, Soft Reboot, or Hard Reboot:

```bash
ssh user@target-pc
```

Only accept the fingerprint if it matches the target PC. OpenSSH stores the verified key in `~/.ssh/known_hosts` on Linux/macOS and in `%USERPROFILE%\.ssh\known_hosts` on Windows.

Tailscale is optional, but it is a convenient way to keep Home Assistant and the target PC reachable without exposing them publicly. MagicDNS lets you use names like `target-pc` instead of Tailscale IP addresses. If the Tailscale CLI is installed but disconnected, PlugWake logs a warning and continues; it stops only when Home Assistant or SSH is actually unreachable.

- Tailscale: <https://tailscale.com/>
- Tailscale MagicDNS: <https://tailscale.com/docs/features/magicdns>

## Setup

1. Clone the repository.

```bash
git clone https://github.com/Superple19/PlugWake.git
cd PlugWake
```

2. Install `uv` if needed, then sync dependencies.

Windows:

```bat
install_uv.bat
uv sync
```

Linux:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
uv sync
```

macOS is not currently supported as a client because RDP launch is implemented for Windows and Linux.

3. Copy `.env.example` to `.env`.
4. Fill in your Home Assistant URL, token, entity IDs, RDP host, SSH target, and target OS. You can also edit these values in the GUI Settings tab.
5. Create desktop launchers if wanted:
   - Windows: run `setup_shortcuts.bat`
   - Linux: run `bash setup_shortcuts.sh`

`.env` is ignored by Git.

## Configuration

```env
HA_URL=http://ha.example.local:8123
HA_TOKEN=PASTE_LONG_LIVED_ACCESS_TOKEN_HERE
PLUG_ENTITY=switch.smart_plug
WATT_ENTITY=sensor.smart_plug_power
RDP_HOST=target-pc
PC_SSH_TARGET=user@target-pc
TARGET_OS=windows
POWER_THRESHOLD_W=5
RDP_WAIT_SECONDS=180
SHUTDOWN_WAIT_SECONDS=300
PLUG_OFF_SECONDS=10
POWER_ON_LOW_CONFIRMATIONS=3
POWER_OFF_LOW_CONFIRMATIONS=4
```

| Setting | Meaning |
| --- | --- |
| `HA_URL` | Home Assistant base URL |
| `HA_TOKEN` | Home Assistant long-lived access token |
| `PLUG_ENTITY` | Smart plug switch entity |
| `WATT_ENTITY` | Smart plug power sensor entity |
| `RDP_HOST` | Host name or address used for RDP |
| `PC_SSH_TARGET` | SSH target as `user@host` |
| `TARGET_OS` | `windows` or `linux` |
| `POWER_THRESHOLD_W` | Power at or above this value means the PC is running |
| `RDP_WAIT_SECONDS` | How long Remote On waits for RDP port 3389 |
| `SHUTDOWN_WAIT_SECONDS` | How long Remote Off waits for power to drop after shutdown; on timeout, plug power is not cut |
| `PLUG_OFF_SECONDS` | How long the plug stays off during a power cycle or Hard Reboot |
| `POWER_ON_LOW_CONFIRMATIONS` | Low-power readings Remote On needs before power-cycling an on plug |
| `POWER_OFF_LOW_CONFIRMATIONS` | Low-power readings Remote Off needs before cutting plug power |

Linux target hosts use:

```text
sudo -n systemctl poweroff
sudo -n systemctl reboot
```

The SSH user must be allowed to run those commands with sudo. With a `NOPASSWD`
sudoers rule for those commands, no password is requested. Otherwise PlugWake asks
for the sudo password and retries with `sudo -S`.

## Usage

Desktop launchers:

- `PlugWake`
- `Remote On`
- `Remote Off`

GUI:

```bash
uv sync
uv run plugwake
```

The GUI is built with Qt Quick and the [FluentWinUI3 style](https://doc.qt.io/qt-6/qtquickcontrols-fluentwinui3.html) that ships with Qt 6.8 and later. It follows the system light or dark theme and accent color. On Windows 11 22H2 or later it uses the Mica window backdrop and renders with OpenGL so the backdrop shows through; elsewhere it uses a solid background.

The Home page shows the smart plug state with its current power, for example `On (134.6 W)`, and whether RDP port 3389 answers. When the plug is on but power is below `POWER_THRESHOLD_W`, it shows `PC off`. It refreshes in the background every 15 seconds by default; change or turn this off in Settings → App → Status refresh. The Refresh button always works. It only reads and never switches the plug.

The GUI is available in English and Korean. Settings → App → Language follows the system language by default and switches right away. The choice is stored as a per-user app preference, not in `.env`. Log lines stay in English.

CLI:

```bash
uv run plugwake-cli on
uv run plugwake-cli off
uv run plugwake-cli reboot
uv run plugwake-cli hard-reboot
uv run plugwake-cli test-ha
uv run plugwake-cli test-rdp  # checks TCP port 3389 only
```

Development checks:

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
```

| GUI button | CLI command | What it does |
| --- | --- | --- |
| Remote On | `on` | Turns the plug on or power-cycles it when needed, then opens RDP |
| Remote Off | `off` | Shuts the OS down over SSH, waits for low power, then turns the plug off |
| Soft Reboot | `reboot` | Sends an OS reboot over SSH |
| Hard Reboot | `hard-reboot` | Runs Remote Off, turns the plug back on, then opens RDP |
| Test Home Assistant (Settings) | `test-ha` | Checks the Home Assistant API and token |
| Test RDP Port (Settings) | `test-rdp` | Checks TCP port 3389 only; it does not perform an RDP login |

In the GUI, the test buttons sit under their Settings groups and use the values on screen, even before you save. Save checks number fields first and refuses to write `.env` if any value is invalid.

Commands exit with code 1 when they stop without finishing, for example when Remote Off does not cut plug power.

Windows shortcut setup:

```bash
uv run plugwake-cli setup-shortcuts
```

Linux shortcut setup:

```bash
bash setup_shortcuts.sh
```

## Safety

- SSH passwords are never saved.
- `.env` is ignored by Git.
- Failed SSH shutdowns do not cut plug power.
- Invalid or unavailable power sensor readings do not cut plug power.
- Remote Off waits for repeated low-power readings before switching the plug off.
- If Home Assistant, SSH, or the power sensor fails, PlugWake prefers doing nothing over cutting power.
- When the plug is on, RDP is unreachable, and low power is repeatedly confirmed, Remote On power-cycles the plug to start the PC.
- The GUI Cancel button stops a running action at the next safe point. A plug power cycle, or Hard Reboot's off-and-on step, always finishes before the cancel takes effect.

## Files

- `remote_on.bat`: Windows launcher for Remote On
- `remote_off.bat`: Windows launcher for Remote Off
- `setup_shortcuts.bat`: Windows shortcut setup
- `launch_gui.bat`: Windows GUI launcher
- `install_uv.bat`: Windows `uv` installer helper
- `remote_on.sh`: Linux launcher for Remote On
- `remote_off.sh`: Linux launcher for Remote Off
- `setup_shortcuts.sh`: Linux desktop entry setup
- `launch_gui.sh`: Linux GUI launcher
- `src/plugwake/`: Python CLI and GUI code
- `src/plugwake/qml/`: Qt Quick GUI pages
- `tests/`: pytest tests
- `assets/`: shortcut icons and their source images

## License

MIT. See `LICENSE` and `NOTICE.md`.
