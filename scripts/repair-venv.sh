#!/usr/bin/env bash
set -euo pipefail
# Ensure .venv is a healthy real directory on the network share using
# Homebrew Python 3.12 (/opt/homebrew/opt/python@3.12/bin/python3.12).
# The path is identical on every Mac with Homebrew, so both machines
# sharing this repo over SMB can use the same .venv.
HOMEBREW_PYTHON="/opt/homebrew/opt/python@3.12/bin/python3.12"
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

  # Install Homebrew Python 3.12 if missing
  if [ ! -x "$HOMEBREW_PYTHON" ]; then
    echo "repair-venv: Homebrew Python 3.12 not found — installing"
    brew install python@3.12
  fi

  uv venv --python "$HOMEBREW_PYTHON" "$VENV"
  uv pip install --python "$VENV/bin/python" -e ".[dev]" --no-progress
  echo "repair-venv: rebuilt at $VENV with $(readlink "$VENV/bin/python")"
fi
