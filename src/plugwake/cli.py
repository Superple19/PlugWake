from __future__ import annotations

import argparse
import getpass
import os
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path

from .actions import remote_hard_reboot, remote_off, remote_on, remote_reboot, test_home_assistant, test_rdp_host
from .config import load_config


def log(text: str) -> None:
    print(f"[{datetime.now():%H:%M:%S}] {text}", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(prog="plugwake-cli")
    parser.add_argument(
        "command", choices=["on", "off", "reboot", "hard-reboot", "test-ha", "test-rdp", "setup-shortcuts"]
    )
    args = parser.parse_args()

    try:
        config = load_config()
        if args.command == "setup-shortcuts":
            setup_shortcuts()
        elif args.command == "on":
            remote_on(config, log)
        elif args.command == "off":
            remote_off(config, log, prompt_password)
        elif args.command == "reboot":
            remote_reboot(config, log, prompt_password)
        elif args.command == "hard-reboot":
            remote_hard_reboot(config, log, prompt_password)
        elif args.command == "test-ha":
            test_home_assistant(config, log)
        elif args.command == "test-rdp":
            test_rdp_host(config, log)
    except Exception as exc:
        log(f"Error: {exc}")
        raise SystemExit(1) from None


def prompt_password(target: str) -> str:
    return getpass.getpass(f"Password for {target}: ")


def setup_shortcuts() -> None:
    if os.name != "nt":
        raise RuntimeError("setup-shortcuts is Windows only. On Linux, run setup_shortcuts.sh")

    root = Path(__file__).resolve().parents[2]
    shortcuts = [
        ("PlugWake", root / "launch_gui.bat", root / "assets" / "icons" / "plugwake.ico"),
        ("Remote On", root / "remote_on.bat", root / "assets" / "icons" / "remote-on.ico"),
        ("Remote Off", root / "remote_off.bat", root / "assets" / "icons" / "remote-off.ico"),
    ]
    script = [
        'Set shell = CreateObject("WScript.Shell")',
        'desktop = shell.SpecialFolders("Desktop")',
    ]
    for name, target, icon in shortcuts:
        shortcut = f"{name}.lnk"
        script.extend(
            [
                f'Set link = shell.CreateShortcut(desktop & "\\{vbs(shortcut)}")',
                f'link.TargetPath = "{vbs(str(target))}"',
                f'link.WorkingDirectory = "{vbs(str(root))}"',
                f'link.IconLocation = "{vbs(str(icon))},0"',
                "link.Save",
                f'WScript.Echo "Created: " & desktop & "\\{vbs(shortcut)}"',
            ]
        )

    with tempfile.NamedTemporaryFile("w", suffix=".vbs", delete=False, encoding="utf-16") as file:
        file.write("\n".join(script))
        path = file.name
    try:
        subprocess.run(["cscript.exe", "//nologo", path], check=True)
    finally:
        Path(path).unlink(missing_ok=True)


def vbs(value: str) -> str:
    return value.replace('"', '""')


if __name__ == "__main__":
    raise SystemExit(main())
