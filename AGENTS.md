# AGENTS.md

## Project Overview

PlugWake is a small Windows-first remote power control tool.

Core responsibilities:

- Control a Home Assistant smart plug through the Home Assistant REST API.
- Use a power sensor to avoid unsafe plug cutoffs.
- Open RDP when the target PC becomes reachable.
- Shut down or reboot the target PC over SSH.
- Keep `.bat` launchers usable as Windows entry points.
- Keep `.sh` launchers usable as Linux entry points.
- Provide an optional `uv` + PySide6 GUI.

## Safety Rules

- Never commit `.env` or any real Home Assistant token.
- Never store SSH passwords in files, docs, logs, or config examples.
- Do not add automatic OS switching or one-time Linux boot controls by default.
- Do not cut smart plug power while wattage is above the configured threshold.
- Remote shutdown must happen through OS shutdown first, then repeated low-power confirmation.
- If Home Assistant, SSH, RDP, or the power sensor fails, prefer doing nothing over cutting power.

## Public Defaults

Use public-safe placeholder values in committed files:

- `HA_URL=http://ha.example.local:8123`
- `PLUG_ENTITY=switch.smart_plug`
- `WATT_ENTITY=sensor.smart_plug_power`
- `RDP_HOST=target-pc`
- `PC_SSH_TARGET=user@target-pc`
- `TARGET_OS=windows`

Do not commit personal values such as hostnames, usernames, Tailnet names, or Home Assistant entity IDs.

## Validation

Before committing code changes, run the smallest relevant checks:

```bat
.venv\Scripts\python.exe -m py_compile src\plugwake\config.py src\plugwake\actions.py src\plugwake\cli.py src\plugwake\gui.py
```

Before public commits, check for leaked local values:

```powershell
Get-ChildItem -Recurse -File -Force |
  Where-Object { $_.FullName -notmatch '\\.git\\|\\.venv\\|\\.env$' } |
  Select-String -Pattern 'real-home-assistant-host|real-target-host|real-ssh-user|real_entity_id'
```

## Dependency Management

- Use `uv`, not `pip`, for project dependency changes.
- Keep Python pinned through `.python-version`.
- Keep GUI dependencies in `pyproject.toml` and `uv.lock`.
- Do not vendor `uv.exe` or Python runtimes into the repo.

Useful commands:

```bat
uv sync
uv run python -m plugwake.gui
uv run plugwake-cli on
uv run plugwake-cli off
uv run plugwake-cli reboot
uv run plugwake-cli test-ha
uv run plugwake-cli test-rdp
uv run plugwake-cli setup-shortcuts
```

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

- Root `.bat` files are user-facing Windows launchers.
- Root `.sh` files are user-facing Linux launchers.
- `src/plugwake/` contains Python CLI and GUI code.
- `assets/icons/` contains committed `.ico` shortcut assets.
- `assets/source-icons/` contains source icon images.
- `docs/` contains planning notes.

Keep root files minimal and user-facing.
