# Electron Desktop App

This directory contains the Electron shell that packages SplitShot as a native desktop application.

## Structure

| File | Purpose |
|------|---------|
| `main.js` | Electron main process — starts the Python backend, creates the browser window, handles IPC |
| `preload.js` | Preload script exposing a safe API to the renderer |
| `launch-intent.js` | Single-instance lock and `.ssproj` file/open-url intent routing |
| `package.json` | Electron and electron-builder configuration |
| `assets/` | App icons, entitlements, and signing resources |
| `bundle/` | Bundled Python backend (`uv sync` output plus vendored `.venv`) |
| `build/` | Electron-builder output directory |
| `tests/` | Launch-intent and smoke tests (`node --test`) |

## Development

```bash
cd electron
npm install
npm run dev       # Bundle Python and launch Electron
```

`npm run dev` runs `scripts/bundle-python.js` first, then starts Electron. The bundled Python backend runs in headless mode (`--headless --no-open`).

## Scripts

| Command | Description |
|---------|-------------|
| `npm run dev` | Bundle Python + launch electron |
| `npm start` | Same as `npm run dev` |
| `npm run check` | Validate the Python bundle without launching Electron |
| `npm run build:mac` | Production signed DMG (macOS) |
| `npm run build:win` | Production NSIS installer (Windows) |
| `npm run build:linux` | Production AppImage (Linux) |
| `npm test` | Run `launch-intent.test.js` and `smoke.test.js` |

## How It Works

1. `main.js` calls `getPythonBinary()` to find the bundled Python interpreter in `bundle/.venv/`.
2. The Python backend is started with `splitshot --headless --no-open`. If a `.ssproj` was opened, `--project <path>` is appended.
3. Once the backend is ready, Electron creates a `BrowserWindow` pointed at `http://127.0.0.1:8765`.
4. The `launch-intent` module handles single-instance locking, `.ssproj` file associations, and `splitshot://` protocol URLs.

## Bundle

The `bundle/` directory is created by `scripts/bundle-python.js`. It contains:

- A full `uv sync` of the Python project into `bundle/`
- The `.venv` with all dependencies
- The `src/splitshot/` package installed in development mode

Regenerate the bundle whenever `src/splitshot/`, `pyproject.toml`, or `uv.lock` changes.

## Signing And Release

See [docs/project/ELECTRON_RELEASE.md](../docs/project/ELECTRON_RELEASE.md) for:

- Exporting the Developer ID `.p12` from Keychain Access
- Verifying the certificate locally
- GitHub Actions signing and notarization workflow
- Smoke builds vs real releases

## CI

The `.github/workflows/build-electron.yml` workflow:

- Runs on `workflow_dispatch` (any branch) for smoke builds
- Runs on `v*` tag pushes for real releases
- macOS: signs and notarizes via electron-builder
- Uses `MAC_CERT_BASE64` / `MAC_CERT_PASSWORD` for signing
- Prefers Apple API key notarization; falls back to Apple ID credentials

**Last updated:** 2026-05-06
**Referenced files last updated:** 2026-05-06
