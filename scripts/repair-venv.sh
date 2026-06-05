#!/usr/bin/env bash
set -euo pipefail
# Ensure .venv is a healthy real directory on the network share using
# uv-managed Python 3.12. uv venv auto-installs the managed Python if
# not already present, so no Homebrew dependency.
VENV=".venv"

# If .venv is a symlink (old approach pointing to user-local path),
# nuke it — the symlink target won't exist on the other machine.
if [ -L "$VENV" ]; then
  echo "repair-venv: .venv is a symlink (broken cross-machine) — creating real dir"
  rm -f "$VENV"
fi

# If .venv is missing or its Python binary doesn't resolve, rebuild it.
if [ ! -d "$VENV/bin" ] || [ ! -x "$VENV/bin/python" ]; then
  echo "repair-venv: .venv missing or broken — rebuilding"
  rm -rf "$VENV"

  uv venv --python 3.12 --prompt splitshot "$VENV"
  uv pip install --python "$VENV/bin/python" -e ".[dev]" --no-progress
  echo "repair-venv: rebuilt at $VENV with $(readlink "$VENV/bin/python")"
fi
