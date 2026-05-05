# A01 — `--headless` server mode

## Metadata

| Field | Value |
|-------|-------|
| task-id | `A01` |
| track | `A — Native CLI` |
| status | `pending` |
| depends-on | `none` |
| risk | `medium` |
| touches-files | `src/splitshot/cli.py`, `src/splitshot/browser/server.py` |
| proof-file | `activedev/electroncleanup/proof/PROOF-A01-runN.md` |

## Goal

Add a `--headless` flag to `splitshot` CLI that starts the HTTP server
without the Qt desktop runtime (`QApplication`, `SplitShotDesktopRuntime`).
The Electron app will use this mode instead of the custom `backend.py`.

## Background

Currently `splitshot --web` always starts a `QApplication` and runs the
Qt event loop via `SplitShotDesktopRuntime.run_server()`. For Electron we
need only the HTTP server — no Qt GUI, no window, no menubar.

`BrowserControlServer` already has `start_background()` and `shutdown()`
methods that work without Qt. We just need a CLI path that calls them
directly instead of going through `SplitShotDesktopRuntime`.

## Implementation

### 1. `src/splitshot/cli.py` — add `--headless` flag

Add to `build_parser()`:
```python
parser.add_argument(
    "--headless",
    action="store_true",
    help="Run the HTTP server without the Qt desktop runtime (for Electron).",
)
```

Add `headless` parameter to `run_browser()`:
```python
def run_browser(
    host: str = "127.0.0.1",
    port: int = 8765,
    open_browser: bool = True,
    project_path: Path | None = None,
    log_level: str = "off",
    headless: bool = False,
) -> int:
```

When `headless=True`:
- Skip `SplitShotDesktopRuntime` import
- Create `BrowserControlServer` + `ProjectController` directly
- Call `server.start_background(open_browser=open_browser)`
- Block on `shutdown_event.wait()` (like `backend.py` does)
- On SIGINT/SIGTERM, call `server.shutdown()` and return 0

The `headless=False` path stays unchanged (uses `SplitShotDesktopRuntime`).

### 2. `src/splitshot/browser/server.py` — no changes needed

`BrowserControlServer.start_background()` and `shutdown()` already work.
No modifications required. A01 only touches `cli.py`.

### 3. Signal handling pattern

Use `threading.Event()` for shutdown coordination (same pattern as
the current `electron/backend.py`):

```python
if headless:
    shutdown = threading.Event()

    def _handle_signal(_signum, _frame) -> None:
        shutdown.set()

    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    server.start_background(open_browser=open_browser)
    try:
        shutdown.wait()
    except KeyboardInterrupt:
        pass
    finally:
        server.shutdown()
    return 0
```

## Dependencies on other tasks

- Blocks **B02** (B02 rewrites `electron/main.js` to call `--headless`)
- Blocks **B08** (parity audit needs to test `--headless` mode)

## Validation

```bash
uv run splitshot --headless --no-open --port 8765
# Expected: server starts on port 8765, no browser opens
# Visit http://127.0.0.1:8765 — should see SplitShot UI
# CTRL+C — server stops cleanly, no Qt warnings

uv run splitshot --headless --no-open --port 8765 &
sleep 2
curl -s http://127.0.0.1:8765/api/state | python -c "import json,sys; d=json.load(sys.stdin); assert d['status']=='ok'"
kill %1
# Expected: API returns valid state, process exits cleanly

uv run splitshot --check
# Expected: still passes (no regression)
```

## Done criteria

- [ ] `splitshot --headless --no-open` starts server without Qt
- [ ] Server responds to API calls on the expected port
- [ ] CTRL+C / SIGTERM shuts down server cleanly
- [ ] No Qt warnings or errors in headless mode
- [ ] `splitshot --web` (non-headless) still works with Qt runtime
- [ ] `uv run splitshot --check` passes
- [ ] Proof written, progress updated
