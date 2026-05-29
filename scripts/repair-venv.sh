#!/usr/bin/env bash
set -euo pipefail
# Restore .venv symlink if deleted by an agent or rebuild step.
# The real venv lives at ~/.local/share/splitshot/venv so it survives
# project-directory cleanup.
EXTERNAL="$HOME/.local/share/splitshot/venv"
LINK=".venv"

# If .venv is a real directory (agent-created), nuke it
if [ -d "$LINK" ] && [ ! -L "$LINK" ]; then
  echo "repair-venv: .venv is a real dir — removing and restoring symlink"
  rm -rf "$LINK"
fi

if [ ! -L "$LINK" ] || [ ! -e "$LINK/bin/python" ]; then
  echo "repair-venv: .venv missing or broken — restoring symlink"
  rm -rf "$LINK"
  if [ ! -d "$EXTERNAL/bin" ]; then
    echo "repair-venv: external venv missing at $EXTERNAL — creating"
    uv venv "$EXTERNAL"
    uv pip install --python "$EXTERNAL/bin/python" -e ".[dev]" --no-progress
  fi
  ln -sf "$EXTERNAL" "$LINK"
  echo "repair-venv: restored"
fi

# Ensure .venv is a symlink (uv managed=false might break this)
if [ -d "$LINK" ] && [ ! -L "$LINK" ]; then
  echo "repair-venv: .venv was recreated as a directory — fixing"
  rm -rf "$LINK"
  ln -sf "$EXTERNAL" "$LINK"
fi
