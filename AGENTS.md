# AGENTS.md

## Project Overview

PlugWake is a small remote power control tool for personal PCs.

Core responsibilities:

- Control a Home Assistant smart plug through the Home Assistant REST API.
- Use a Home Assistant power sensor before making plug power decisions.
- Open RDP when the target PC becomes reachable.
- Shut down or reboot the target PC over SSH.
- Keep root `.bat` launchers usable as Windows entry points.
- Keep root `.sh` launchers usable as Linux entry points.
- Provide a `uv` + PySide6 GUI and CLI.

## Safety Rules

- Never commit `.env`, Home Assistant tokens, SSH passwords, real or private hostnames, Tailnet names, local IPs, or real entity IDs.
- Never store SSH passwords in files, docs, logs, examples, or config defaults.
- Do not add automatic OS switching or one-time Linux boot controls by default.
- Do not cut smart plug power while wattage is above the configured threshold.
- Remote Off must shut down through the OS first, then require repeated low-power confirmation before plug cutoff.
- If Home Assistant, SSH, or the power sensor fails, prefer doing nothing over cutting power.
- Remote On may power-cycle an on plug when RDP is unreachable and repeated low-power readings indicate that the target PC is off.

## Public Defaults

Use only public-safe placeholder values in committed files:

- `HA_URL=http://ha.example.local:8123`
- `HA_TOKEN=PASTE_LONG_LIVED_ACCESS_TOKEN_HERE`
- `PLUG_ENTITY=switch.smart_plug`
- `WATT_ENTITY=sensor.smart_plug_power`
- `RDP_HOST=target-pc`
- `PC_SSH_TARGET=user@target-pc`
- `TARGET_OS=windows`

## Validation

Before committing code changes, run the smallest relevant checks:

```bat
.venv\Scripts\python.exe -m py_compile src\plugwake\config.py src\plugwake\actions.py src\plugwake\cli.py src\plugwake\gui.py src\plugwake\theme.py
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run plugwake-cli --help
```

Before public commits, check for leaked local values:

```powershell
Get-ChildItem -Recurse -File -Force |
  Where-Object { $_.FullName -notmatch '\\.git\\|\\.venv\\|\\.env(\\..*)?$|__pycache__|\\dist\\|\\build\\' } |
  Select-String -Pattern 'real-home-assistant-host|real-target-host|real-ssh-user|real_entity_id|Bearer\\s+[A-Za-z0-9_\\.-]+'
```

For local review, also search any known private hostnames, usernames, entity IDs, and Tailnet IPs from the current machine. Do not write those private values into committed docs.

## Dependency Management

- Use `uv`, not `pip`, for dependency changes.
- Keep Python pinned through `.python-version`.
- Keep dependencies in `pyproject.toml` and `uv.lock`.
- Do not vendor `uv.exe`, Python runtimes, or generated build artifacts.

Useful commands:

```bat
uv sync
uv run ruff check .
uv run ruff format .
uv run plugwake
uv run plugwake-cli on
uv run plugwake-cli off
uv run plugwake-cli reboot
uv run plugwake-cli hard-reboot
uv run plugwake-cli test-ha
uv run plugwake-cli test-rdp
uv run plugwake-cli setup-shortcuts  # Windows only
```

## Message Style

User-facing log lines come from `src/plugwake/actions.py`. Keep them consistent:

- Every stop or failure raises `ActionFailed` with the reason. Do not log a failure and return a flag; the CLI and GUI print it once as `Error: <reason>`.
- Exception messages have no trailing period. Log lines end with a period.
- Decisions start with `Decision:`. Non-fatal problems start with `Warning:`.
- Power readings use `log_power()`: `Power <W> W, <status>.`
- Progress uses `progress()`: `(n/N)` for counts and `(elapsed/total s)` for time limits.
- Say how often a wait checks once, when the wait starts, not on every line.
- Use "target PC", "RDP on <host>", "smart plug", and "Home Assistant" consistently.
- Safety stops that leave plug power on end with `Not cutting plug power`.

## Commit Style

Use Conventional Commits:

- `feat:`
- `fix:`
- `docs:`
- `chore:`
- `refactor:`

Commit bodies should use contiguous `-` bullets without blank lines between bullets.

Example:

```text
fix: harden remote shutdown flow

- validate power sensor readings before use
- avoid plug cutoff when SSH shutdown fails
- document the failure behavior
```

## File Layout

- `remote_on.bat` and `remote_on.sh`: user-facing Remote On launchers.
- `remote_off.bat` and `remote_off.sh`: user-facing Remote Off launchers.
- `launch_gui.bat` and `launch_gui.sh`: user-facing GUI launchers.
- `setup_shortcuts.bat` and `setup_shortcuts.sh`: desktop shortcut setup.
- `install_uv.bat`: Windows `uv` installer helper.
- `src/plugwake/`: Python CLI and GUI code.
- `tests/`: pytest tests.
- `assets/icons/`: generated shortcut icons (`.ico` for Windows, `.png` for Linux/PySide).
- `assets/source-icons/`: source icon images documented in `NOTICE.md`.

Keep root files minimal and user-facing.
