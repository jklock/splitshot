# Browser Server Terminal Hygiene Final Audit

## Result

The browser server now treats normal browser and terminal events as normal:

- Foreground `Ctrl+C` shutdown is caught and exits without a Python traceback.
- Expected media-stream disconnects are suppressed at the HTTP server level.
- Media chunk writes also return quietly if the browser closes or resets the video request.
- Real non-disconnect server errors still use the default server error path.

## Validation

- `uv run pytest tests/test_browser_control.py`
  - Result: `8 passed`
- `uv run pytest`
  - Result: `42 passed`
- `uv run --python 3.12 splitshot --no-open --port 8877`, then SIGINT
  - Result: printed `SplitShot browser control stopped.` with no traceback.

