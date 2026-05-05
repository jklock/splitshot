# A03 — Clean server shutdown without Qt

## Metadata

| Field | Value |
|-------|-------|
| task-id | `A03` |
| track | `A — Native CLI` |
| status | `pending` |
| depends-on | `A01` |
| risk | `medium` |
| touches-files | `src/splitshot/cli.py`, `electron/backend.py` |
| proof-file | `activedev/electroncleanup/proof/PROOF-A03-runN.md` |

## Goal

After A01, `electron/backend.py` is a redundant copy of the headless CLI
logic. Replace it with a thin CLI call, then verify the `--headless` mode
shuts down cleanly in all scenarios: SIGINT, SIGTERM, parent process death.

## Background

The current `electron/backend.py` duplicates the server startup logic from
`cli.py`. With `--headless` available, `electron/backend.py` should just
call `splitshot.cli:run_browser(headless=True)`. If any shutdown edge cases
exist (orphaned threads, leaked temp dirs, lingering PractiScore sessions),
they must be fixed in `cli.py` — not in `backend.py`.

## Implementation

### 1. `electron/backend.py` — rewrite as thin wrapper

```python
"""SplitShot HTTP backend for Electron — delegates to CLI."""
import sys
from splitshot.cli import run_browser

def main() -> int:
    return run_browser(
        host="127.0.0.1",
        port=8765,
        open_browser=False,
        log_level=os.environ.get("SPLITSHOT_LOG_LEVEL", "off"),
        headless=True,
    )

if __name__ == "__main__":
    raise SystemExit(main())
```

### 2. `src/splitshot/cli.py` — verify clean shutdown

Test these shutdown scenarios in the headless path:

- **SIGINT** (CTRL+C): should call `server.shutdown()`, which calls
  `practiscore_session.shutdown()`, `httpd.shutdown()`, `session_dir.cleanup()`
- **SIGTERM** (parent process kill): same cleanup path via signal handler
- **Parent death** (Electron crashes): on macOS/Linux, parent death signal
  (SIGHUP) should also trigger shutdown. Install a `SIGHUP` handler if the
  `SPLITSHOT_ELECTRON` env var is set.

Add to the headless signal handlers:
```python
if headless:
    shutdown = threading.Event()

    def _handle_signal(_signum, _frame) -> None:
        shutdown.set()

    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)
    # When running under Electron, also handle SIGHUP (parent death)
    if os.environ.get("SPLITSHOT_ELECTRON"):
        signal.signal(signal.SIGHUP, _handle_signal)
```

### 3. Temp directory leak check

`BrowserControlServer.__init__` creates a `TemporaryDirectory` for the
session. On clean shutdown, `server.shutdown()` calls `session_dir.cleanup()`.
Verify this runs in the headless path. Add a log line at shutdown confirming
cleanup.

### 4. Remove `electron/backend.py` symlink/import risk

After this change, `electron/backend.py` is ~10 lines and purely delegates
to the CLI. `electron/main.js` will be updated in B02 to call the CLI
directly instead of `backend.py`, making this file a transitional wrapper
that can be deleted once B02 confirms the direct CLI invocation works.

## Dependencies

- Requires `A01` (A01 adds the `headless` parameter to `run_browser()`)

## Validation

```bash
# Test SIGINT
uv run splitshot --headless --no-open &
PID=$!
sleep 2
kill -INT $PID
wait $PID
echo "Exit code: $?"  # Expected: 0

# Test SIGTERM
uv run splitshot --headless --no-open &
PID=$!
sleep 2
kill -TERM $PID
wait $PID
echo "Exit code: $?"  # Expected: 0

# Test that /tmp/splitshot-browser-* dirs are cleaned
ls -d /tmp/splitshot-browser-* 2>/dev/null && echo "LEAK: temp dirs remain" || echo "OK: no temp dirs"
```

## Done criteria

- [ ] `electron/backend.py` rewritten as thin CLI wrapper (~10 lines)
- [ ] SIGINT cleanly shuts down server, no orphaned threads
- [ ] SIGTERM cleanly shuts down server
- [ ] SIGHUP handled when `SPLITSHOT_ELECTRON=1`
- [ ] No temp directory leaks after shutdown
- [ ] `uv run splitshot --check` passes
- [ ] Proof written, progress updated
