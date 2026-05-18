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
npm start
```

`npm start` runs `scripts/bundle-python.js` first, then starts Electron. The bundled Python backend runs in headless mode (`--headless --no-open`).

## Scripts

| Command | Description |
|---------|-------------|
| `npm run bundle` | Rebuild the Electron Python bundle without launching the app |
| `npm run dev` | Launch Electron without rebuilding the Python bundle first |
| `npm start` | Rebuild the bundle, then launch Electron |
| `npm run check` | Validate the Python bundle without launching Electron |
| `npm run build:mac` | Production signed DMG (macOS) |
| `npm run build:win` | Production NSIS installer (Windows) |
| `npm run build:linux` | Production AppImage (Linux) |
| `npm test` | Run the Electron smoke test entrypoints when invoked directly in the package environment |

Artifact-native package validation uses:

- [scripts/testing/test_packaged_artifact.py](/Volumes/Storage/GitHub/splitshot/scripts/testing/test_packaged_artifact.py)
- [scripts/testing/test_electron_app.py](/Volumes/Storage/GitHub/splitshot/scripts/testing/test_electron_app.py)
- [scripts/testing/test_packaged_app_e2e.py](/Volumes/Storage/GitHub/splitshot/scripts/testing/test_packaged_app_e2e.py)

That path validates the actual user-download artifact instead of an unpacked stand-in:

- macOS mounts the `.dmg`, copies the `.app`, then launches it
- Windows silently installs the NSIS `.exe`, then launches the installed app
- Linux launches the `.AppImage` itself

## How It Works

1. `main.js` calls `getPythonBinary()` to find the bundled Python interpreter in `bundle/.venv/`.
   On Windows the packaged app uses an app-local runtime under `bundle/python/` instead of a virtualenv so the installed NSIS app does not depend on the build machine's base Python location.
   On macOS and Linux the packaged app now sets `PYTHONHOME` to the bundled `.venv`, which carries the copied stdlib needed for a self-contained installed runtime.
2. The Python backend is started with `splitshot --headless --no-open`. If a `.ssproj` was opened, `--project <path>` is appended.
3. Once the backend is ready, Electron creates a `BrowserWindow` pointed at `http://127.0.0.1:8765`.
4. The `launch-intent` module handles single-instance locking, `.ssproj` file associations, and `splitshot://` protocol URLs.

## Bundle

The `bundle/` directory is created by `scripts/bundle-python.js`. It contains:

- A full `uv sync` of the Python project into `bundle/`
- The `.venv` with all dependencies plus a copied stdlib on macOS/Linux, or an app-local `python/` runtime on Windows
- The `src/splitshot/` package installed in development mode

Regenerate the bundle whenever `src/splitshot/`, `pyproject.toml`, or `uv.lock` changes.

## Signing And Release

See [docs/project/ELECTRON_RELEASE.md](../docs/project/ELECTRON_RELEASE.md) for:

- Exporting the Developer ID `.p12` from Keychain Access
- Verifying the certificate locally
- GitHub Actions signing and notarization workflow
- Smoke builds vs real releases

## CI

The Electron packaging and test workflows are split by platform:

- `.github/workflows/build-macos.yml`
- `.github/workflows/build-windows.yml`
- `.github/workflows/build-linux.yml`
- `.github/workflows/release.yml`
- platform smoke and test coverage in `.github/workflows/test-*.yml`

macOS is the signed/notarized release path. Windows and Linux have configured packaging and smoke coverage, but their release flow does not use the macOS signing/notarization stack.
