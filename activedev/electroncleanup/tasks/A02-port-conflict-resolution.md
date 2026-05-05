# A02 — Port conflict resolution

## Metadata

| Field | Value |
|-------|-------|
| task-id | `A02` |
| track | `A — Native CLI` |
| status | `pending` |
| depends-on | `A01` |
| risk | `low` |
| touches-files | `src/splitshot/cli.py`, `src/splitshot/browser/server.py` |
| proof-file | `activedev/electroncleanup/proof/PROOF-A02-runN.md` |

## Goal

When the default port 8765 is in use, automatically try the next available
port instead of crashing with a bind error.

## Background

Currently `BrowserControlServer._build_httpd()` raises `OSError` on bind
failure and the app exits. For Electron this is especially bad — users get
an opaque error dialog. Auto-fallback to the next free port is standard
practice for local dev servers.

## Implementation

### 1. `src/splitshot/browser/server.py` — add `start_background()` port fallback

Modify `start_background()` to try ports in sequence:

```python
MAX_PORT_ATTEMPTS = 10

def start_background(self, open_browser: bool = False) -> None:
    base_port = self.port
    last_error = None
    for attempt in range(MAX_PORT_ATTEMPTS):
        port = base_port + attempt
        try:
            self._httpd = self._build_httpd(port=port)
        except OSError as exc:
            last_error = exc
            continue
        self.port = port  # update to actual bound port
        break
    else:
        self.activity.log("server.bind.error", host=self.host, port=base_port, error=str(last_error))
        print(f"SplitShot could not bind to {self.host}:{base_port}-{base_port + MAX_PORT_ATTEMPTS - 1}: {last_error}")
        raise RuntimeError(f"No available port in range {base_port}-{base_port + MAX_PORT_ATTEMPTS - 1}") from last_error

    self._thread = threading.Thread(target=self._httpd.serve_forever, daemon=True)
    self._thread.start()
    self.activity.log("server.start_background", url=self.url, port=self.port, open_browser=open_browser)
    if open_browser:
        self._attempt_open_browser()
```

Also modify `serve_forever()` similarly (for non-headless mode):
```python
def serve_forever(self, open_browser: bool = True) -> None:
    base_port = self.port
    last_error = None
    for attempt in range(MAX_PORT_ATTEMPTS):
        port = base_port + attempt
        try:
            self._httpd = self._build_httpd(port=port)
        except OSError as exc:
            last_error = exc
            continue
        self.port = port
        break
    else:
        self.activity.log("server.bind.error", host=self.host, port=base_port, error=str(last_error))
        print(f"SplitShot could not bind to {self.host}:{base_port}-{base_port + MAX_PORT_ATTEMPTS - 1}: {last_error}")
        raise RuntimeError(f"No available port in range {base_port}-{base_port + MAX_PORT_ATTEMPTS - 1}") from last_error
    ...
```

Update `_build_httpd()` to accept an optional port:
```python
def _build_httpd(self, port: int | None = None) -> ThreadingHTTPServer:
    return QuietThreadingHTTPServer((self.host, port or self.port), self._handler())
```

### 2. `src/splitshot/cli.py` — print actual port

After server starts in headless mode, print the actual port in use:
```python
if headless:
    print(f"SplitShot running at {server.url}")
```

## Dependencies

- Requires `A01` (A01 introduces the headless code path)

## Validation

```bash
# Start something on port 8765 first
python -m http.server 8765 &
SERVER_PID=$!

# Then start splitshot — should use 8766
uv run splitshot --headless --no-open --port 8765 &
SPLITSHOT_PID=$!
sleep 2
curl -s http://127.0.0.1:8766/api/state | python -c "import json,sys; d=json.load(sys.stdin); assert d['status']=='ok'"
echo "SplitShot bound to alternate port: OK"

kill $SPLITSHOT_PID $SERVER_PID 2>/dev/null
wait 2>/dev/null
```

## Done criteria

- [ ] Default port 8765 gets fallback port 8766, 8767, etc. if busy
- [ ] Server prints the actual bound port in startup message
- [ ] After `MAX_PORT_ATTEMPTS` failures, raises clear error
- [ ] `serve_forever()` also has port fallback for non-headless mode
- [ ] `uv run splitshot --check` passes
- [ ] Proof written, progress updated
