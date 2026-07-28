from __future__ import annotations

import argparse
from datetime import datetime

from .actions import remote_off, remote_on
from .config import load_config


def log(text: str) -> None:
    print(f"[{datetime.now():%H:%M:%S}] {text}", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(prog="remotepc")
    parser.add_argument("command", choices=["on", "off"])
    args = parser.parse_args()

    config = load_config()
    if args.command == "on":
        remote_on(config, log)
    else:
        remote_off(config, log)


if __name__ == "__main__":
    main()
