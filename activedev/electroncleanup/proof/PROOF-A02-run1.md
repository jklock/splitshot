# A02 — Port conflict resolution

## Status: Complete

## Changes

- `src/splitshot/browser/server.py`:
  - Added `find_free_port(host, desired, max_attempts)` — tries ports from `desired` upward until one is free
  - Added `socket` and `contextlib.closing` imports
- `src/splitshot/cli.py`:
  - `run_headless` uses `find_free_port` before starting server
  - Prints message when port is auto-resolved

## Verification

```bash
uv run splitshot --headless --no-open --port 8765 &
# Then start another on same port — should auto-resolve to 8766
```
