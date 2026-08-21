# Electron Desktop App

<!-- Documentation reviewed: 2026-08-11 -->

This directory contains the Electron shell that packages SplitShot as a native desktop application.

Use Node.js 22 and `npm ci`. Building the bundled backend also requires Python 3.12 and `uv`; source media checks require `ffmpeg` and `ffprobe` on `PATH`.

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
npm ci
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
| `npm run build:mac` | Production DMG using explicit signing/notarization env (macOS) |
| `npm run build:mac:local` | Export the local login-keychain identity, build a local signed DMG, and install `/Applications/SplitShot.app` |
| `npm run build:win` | Production NSIS installer (Windows) |
| `npm run build:linux` | Production AppImage (Linux) |
| `npm run test:launch-intent` | Run the Node launch-intent tests |
| `npm run test:electron-smoke` | Run the Electron smoke test entrypoint |
| `npm run test:electron-iterate` | Run the iterative Electron test entrypoint |

Artifact-native package validation uses:

- [test_packaged_artifact.py](../scripts/testing/test_packaged_artifact.py)
- [test_electron_app.py](../scripts/testing/test_electron_app.py)
- [test_packaged_app_e2e.py](../scripts/testing/test_packaged_app_e2e.py)

That path validates the actual user-download artifact instead of an unpacked stand-in:

- macOS mounts the `.dmg`, copies the `.app`, then launches it
- Windows silently installs the NSIS `.exe`, then launches the installed app
- Linux launches the `.AppImage` itself

## How It Works

1. `main.js` calls `getPythonBinary()` to find the bundled Python interpreter in `bundle/.venv/`.
   On Windows the packaged app uses an app-local runtime under `bundle/python/` instead of a virtualenv so the installed NSIS app does not depend on the build machine's base Python location.
   On macOS and Linux the packaged app now sets `PYTHONHOME` to the bundled `.venv`, which carries the copied stdlib needed for a self-contained installed runtime.
2. The Python backend is started with `splitshot --headless --no-open`. If a `.ssproj` was opened, `--project <path>` is appended.
3. Once the backend is ready, Electron creates a `BrowserWindow` pointed at `http://127.0.0.1:8765`. Each window launch resets the page zoom factor to 90%; the standard `View` menu zoom commands remain available after launch.
4. The `launch-intent` module handles single-instance locking, `.ssproj` file associations, and `splitshot://` protocol URLs.

## Bundle

The `bundle/` directory is created by `scripts/bundle-python.js`. It contains:

- A full `uv sync` of the Python project into `bundle/`
- The `.venv` with all dependencies plus a copied stdlib on macOS/Linux, or an app-local `python/` runtime on Windows
- The `src/splitshot/` package installed in development mode

Regenerate the bundle whenever `src/splitshot/`, `pyproject.toml`, or `uv.lock` changes.

Packaged builds no longer copy `ffmpeg` or `ffprobe` from the host machine. `scripts/bundle-python.js` fetches portable release binaries for the target platform, bundles them into the app resources, and rejects media tools that still reference Homebrew-managed libraries on macOS.

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

The package targets are a DMG on macOS, an NSIS installer on Windows, and an AppImage on Linux. Signing and notarization are platform/release operations, not requirements for source startup or ordinary local smoke packages. macOS uses the documented Apple signing/notarization path; Windows and Linux do not use that stack.

For local macOS parity, prefer `npm run build:mac:local` from `electron/`. It mirrors the CI certificate import path by exporting the current login-keychain signing identity to a temporary `.p12`, feeding that through `CSC_LINK`, disabling notarization only when Apple notarization credentials are absent, and installing the generated DMG app into `/Applications`.
