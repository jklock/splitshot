# A03 — Clean server shutdown without Qt

## Status: Complete

## Changes

- `electron/backend.py`: **Deleted** — fully replaced by `splitshot --headless --no-open`
- `src/splitshot/cli.py`: A01's `run_headless` already provides clean signal-driven shutdown

## Verification

```bash
uv run splitshot --headless --no-open &
kill $!  # SIGTERM — clean shutdown
```
