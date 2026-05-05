# A01 — `--headless` server mode

## Status: Complete

## Changes

- `src/splitshot/cli.py`:
  - Added `--headless` flag to argument parser
  - Added `run_headless()` function — starts HTTP server without Qt runtime
  - Uses signal-based shutdown (SIGINT/SIGTERM)
  - No PySide6/Qt import needed
  - `main()` routes `--headless` to `run_headless()`

## Verification

```bash
uv run splitshot --check
uv run splitshot --headless --no-open
# Expected: server starts, prints URL, waits for signal
```

## Proof

- `run_headless` imports only `BrowserControlServer` and `ProjectController`
- Server starts via `start_background(open_browser=False)`
- SIGINT/SIGTERM cause clean shutdown via `server.shutdown()`
