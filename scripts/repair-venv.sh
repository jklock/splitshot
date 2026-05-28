#!/usr/bin/env bash
set -euo pipefail
# Restore .venv symlink if deleted by an agent or rebuild step.
# The real venv lives at ~/.local/share/splitshot/venv so it survives
# project-directory cleanup.
EXTERNAL="$HOME/.local/share/splitshot/venv"
LINK=".venv"
if [ ! -L "$LINK" ] || [ ! -e "$LINK/bin/python" ]; then
  echo "repair-venv: .venv missing or broken — restoring symlink"
  rm -rf "$LINK"
  if [ ! -d "$EXTERNAL/bin" ]; then
    echo "repair-venv: external venv missing at $EXTERNAL — running uv sync"
    uv sync --extra dev --no-progress
    mkdir -p "$(dirname "$EXTERNAL")"
    mv "$LINK" "$EXTERNAL"
  fi
  ln -sf "$EXTERNAL" "$LINK"
  echo "repair-venv: restored"
fi
