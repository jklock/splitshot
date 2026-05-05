# E01 — Electron Shell

## Metadata

| Field | Value |
| --- | --- |
| task-id | `E01` |
| status | `pending` |
| depends-on | `none` |
| risk | `low` |
| touches-files | `electron/package.json`, `electron/main.js`, `electron/preload.js`, `.gitignore`, `activedev/electron/progress.md` |
| proof-file | `activedev/electron/proof/PROOF-E01-runN.md` |

## Goal

Create the Electron app skeleton that spawns the Python backend, opens a BrowserWindow, and shuts down cleanly.

## Implementation

### 1. `electron/package.json`

Create with the config from `plan.md`. Dependencies: `electron`, `electron-builder`.

### 2. `electron/main.js`

Main process that:
- Spawns `python -m splitshot --web --host 127.0.0.1 --port 8765 --no-open` as a child process
- Polls `http://127.0.0.1:8765/api/state` until the server responds (up to 15s)
- Opens a `BrowserWindow` pointed at the server URL
- Kills the Python process on window close or app quit
- Handles `open-file` / `open-project` IPC calls from the renderer

### 3. `electron/preload.js`

Exposes `window.splitshot` bridge with:
- `getVersion()` — returns app version
- `onOpenProject(callback)` — receives `.ssproj` file open events from the OS

### 4. `.gitignore`

Add `electron/bundle/`, `electron/build/`, `electron/node_modules/`.

## Validation

```bash
npm --prefix electron install
npm --prefix electron run start
```

Expected: Electron window opens, loads SplitShot UI, all features work. Close window → Python process exits.

## Done criteria

- [ ] `electron/` directory exists with `package.json`, `main.js`, `preload.js`
- [ ] `npm --prefix electron run start` opens SplitShot in a native window
- [ ] Python process spawns and is reachable at port 8765
- [ ] Closing the window kills the Python process
- [ ] `.gitignore` excludes bundle/build/node_modules
- [ ] Proof written, progress updated
