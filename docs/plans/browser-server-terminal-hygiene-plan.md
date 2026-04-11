# Browser Server Terminal Hygiene Plan

## Problem

The browser server runs correctly, but the terminal output is noisy:

- Pressing `Ctrl+C` exits with a Python `KeyboardInterrupt` traceback.
- Browser video playback can close or restart range requests during normal seeking/playback, which logs `BrokenPipeError` or `ConnectionResetError` tracebacks.

## Requirements

- Treat `Ctrl+C` as a normal shutdown path.
- Suppress expected client-disconnect noise during media streaming.
- Preserve real API errors as JSON responses.
- Keep media range support intact.
- Add tests for clean media disconnect handling and graceful interrupt behavior.

## Acceptance

- `Ctrl+C` stops the browser server without a traceback.
- Browser-cancelled media streams do not print server tracebacks.
- Browser control tests and full test suite pass.

