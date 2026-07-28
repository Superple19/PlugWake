#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"

if ! command -v uv >/dev/null 2>&1; then
  echo "uv was not found."
  echo "Install uv first, then open this launcher again."
  read -r -p "Press Enter to exit..."
  exit 1
fi

uv run python -m plugwake.gui
