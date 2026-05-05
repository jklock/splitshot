# B02 — Use CLI entrypoint properly

## Metadata

| Field | Value |
|-------|-------|
| task-id | `B02` |
| track | `B — Electron Packaging` |
| status | `pending` |
| depends-on | `A01`, `B01` |
| risk | `high` |
| touches-files | `electron/main.js`, `electron/backend.py`, `electron/preload.js`, `electron/package.json` |
| proof-file | `activedev/electroncleanup/proof/PROOF-B02-runN.md` |

## Goal

Replace the custom `backend.py` spawn logic in `electron/main.js` with a
direct CLI call to `splitshot --headless --no-open`. This ensures the
Electron app uses exactly the same code path as `uv run splitshot`.

## Background

Current `electron/main.js` spawns `backend.py` as a subprocess. `backend.py`
duplicates the server logic from `cli.py`. After A01, `--headless` mode
exists in `cli.py`. The Electron app should call it directly.

## Implementation

### 1. `electron/main.js` — change spawn target

Change from:
```javascript
const backendScript = app.isPackaged
  ? path.join(process.resourcesPath, 'backend.py')
  : path.join(__dirname, 'backend.py');

pythonProcess = spawn(python, [backendScript], { ... });
```

To:
```javascript
const cliArgs = [
  '-m', 'splitshot',
  '--headless',
  '--no-open',
  '--host', '127.0.0.1',
  '--port', String(PORT),
];

if (process.env.SPLITSHOT_LOG_LEVEL) {
  cliArgs.push('--log-level', process.env.SPLITSHOT_LOG_LEVEL);
}

pythonProcess = spawn(python, cliArgs, {
  cwd: bundlePath,
  env: {
    ...process.env,
    PYTHONPATH: modulePath,
    SPLITSHOT_ELECTRON: '1',
  },
  stdio: ['ignore', 'pipe', 'pipe'],
});
```

### 2. `electron/backend.py` — deprecate (keep as fallback)

Keep `backend.py` but add a deprecation warning. It will be used only
if someone launches it directly. The Electron main process no longer
references it.

```python
"""SplitShot HTTP backend for Electron — DEPRECATED.

Use `python -m splitshot --headless --no-open` instead.
"""
import os
import signal
import sys
import threading
from pathlib import Path

os.environ.setdefault("SPLITSHOT_ELECTRON", "1")
print("[splitshot] WARNING: backend.py is deprecated, use --headless mode", file=sys.stderr)

from splitshot.cli import run_browser

def main() -> int:
    host = os.environ.get("SPLITSHOT_HOST", "127.0.0.1")
    port = int(os.environ.get("SPLITSHOT_PORT", "8765"))
    log_level = os.environ.get("SPLITSHOT_LOG_LEVEL", "off")
    return run_browser(host=host, port=port, open_browser=False, log_level=log_level, headless=True)

if __name__ == "__main__":
    raise SystemExit(main())
```

### 3. `electron/preload.js` — clean up for B03

Remove methods that have no handlers yet (they'll be wired in B03):
```javascript
contextBridge.exposeInMainWorld('splitshot', {
  getVersion: () => ipcRenderer.invoke('get-version'),
});
```

Keep only `getVersion` for now. B03 adds the rest.

### 4. `electron/main.js` — remove unused IPC handlers

Remove `open-file` handler (it's unused without a preload bridge for its
result). B03 properly wires this.

### 5. `electron/package.json` — remove backend.py from extraResources

Since `main.js` no longer references `backend.py`, remove it from
electron-builder's `extraResources`:

```json
"extraResources": [
  {
    "from": "bundle",
    "to": "bundle",
    "filter": ["**/*"]
  }
]
```

Remove the `backend.py` entry (line 36-39 in current file).

## Validation

```bash
# Test CLI spawn directly
python -m splitshot --headless --no-open --port 8765 &
PID=$!
sleep 2
curl -s http://127.0.0.1:8765/api/state > /dev/null && echo "OK: CLI headless mode works"
kill $PID

# Test Electron dev mode (requires bundle or SPLITSHOT_DEV=1)
SPLITSHOT_DEV=1 npm --prefix electron run dev &
# Verify window opens, API reachable
kill %1 2>/dev/null
```

## Done criteria

- [ ] `electron/main.js` spawns `python -m splitshot --headless --no-open`
- [ ] `electron/backend.py` deprecated but kept as fallback
- [ ] `electron/package.json` no longer bundles `backend.py`
- [ ] Preload stripped to minimum (ready for B03)
- [ ] Removed orphaned IPC handlers
- [ ] `uv run splitshot --check` passes
- [ ] Proof written, progress updated
