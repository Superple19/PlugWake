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
- `uv` for running the Python CLI and GUI.
- Windows RDP hosts require Windows Pro, Enterprise, or Education. Windows Home cannot act as a built-in Remote Desktop host.

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

- Home Assistant: <https://www.home-assistant.io/>
- Home Assistant REST API: <https://developers.home-assistant.io/docs/api/rest/>
- Home Assistant long-lived access tokens: <https://developers.home-assistant.io/docs/auth_api/#long-lived-access-token>

PlugWake rejects SSH servers that are not already in the client's known-hosts file. Verify the target fingerprint once with your system SSH client before using Remote Off or Reboot:

```bash
ssh user@target-pc
```

Only accept the fingerprint if it matches the target PC. OpenSSH stores the verified key in `~/.ssh/known_hosts` on Linux/macOS and in `%USERPROFILE%\.ssh\known_hosts` on Windows.

Tailscale is optional, but it is a convenient way to keep Home Assistant and the target PC reachable without exposing them publicly. MagicDNS lets you use names like `ha-server` instead of Tailscale IP addresses.

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

Linux/macOS:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
uv sync
```

3. Copy `.env.example` to `.env`.
4. Fill in your Home Assistant URL, token, entity IDs, RDP host, SSH target, and target OS.
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
POWER_ON_LOW_CONFIRMATIONS=3
POWER_OFF_LOW_CONFIRMATIONS=4
```

Use `TARGET_OS=windows` for Windows hosts and `TARGET_OS=linux` for Linux hosts.

Linux target hosts use:

```text
sudo -S systemctl poweroff
sudo -S systemctl reboot
```

The SSH user must be allowed to run those commands with sudo.

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

CLI:

```bash
uv run plugwake-cli on
uv run plugwake-cli off
uv run plugwake-cli reboot
uv run plugwake-cli hard-reboot
uv run plugwake-cli test-ha
uv run plugwake-cli test-rdp
```

Development checks:

```bash
uv run ruff check .
uv run ruff format --check .
```

`reboot` sends an OS reboot over SSH. `hard-reboot` shuts the OS down, waits for low power, power-cycles the plug, then opens RDP.

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
- If Home Assistant, SSH, RDP, or the power sensor fails, PlugWake prefers doing nothing over cutting power.

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
- `assets/`: shortcut icons and source icons

## License

MIT. See `LICENSE` and `NOTICE.md`.
