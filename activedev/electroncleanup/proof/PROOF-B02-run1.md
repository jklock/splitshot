# B02 — Use CLI entrypoint properly

## Status: Complete

## Changes

- `electron/main.js`: Rewritten to spawn `splitshot --headless --no-open` instead of custom `backend.py`
  - Packaged mode: runs `python -m splitshot --headless --no-open` from bundle venv
  - Dev mode: runs `uv run splitshot --headless --no-open`
  - Added `open-file` macOS event handler for file associations
- `electron/preload.js`: Cleaned up — only exposes handlers that have corresponding IPC channels (`get-version`, `get-platform`, `open-file`)
- `electron/backend.py`: Deleted (via A03 — no longer needed)

## Verification

```bash
# Dev mode
npm --prefix electron run dev  # spawns via uv run
```
