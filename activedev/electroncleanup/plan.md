# SplitShot Electron Cleanup — Master Plan

## Architecture

Two independent tracks, one goal: **zero perceptible difference** between
`uv run splitshot` and the Electron app — on macOS, Windows, **and Linux**.

```
Track A: Native CLI (non-Electron)
  Fixes to the Python backend itself so it can run standalone
  without the Qt desktop runtime. These are changes to src/.
  Platform-agnostic — works identically on macOS, Windows, Linux.

Track B: Electron Packaging
  Fixes to the Electron wrapper so it properly wraps Track A
  on all three platforms. These are changes to electron/, scripts/, .github/.
```

Both tracks must pass the same verification on all platforms. The Electron
app must be nothing more than `Track A + packaging`. No behavior difference,
no quality difference, no speed difference.

## Track A — Native CLI (non-Electron)

Make the CLI a proper headless server that Electron (or any other consumer)
can call without importing Qt. Platform-agnostic.

| Task | Title | Depends on | Risk | Touches |
|------|-------|-----------|------|---------|
| A01 | `--headless` server mode | none | medium | `src/splitshot/cli.py`, `src/splitshot/browser/server.py` |
| A02 | Port conflict resolution | A01 | low | `src/splitshot/cli.py`, `src/splitshot/browser/server.py` |
| A03 | Clean server shutdown without Qt | A01 | medium | `src/splitshot/cli.py`, `electron/backend.py` |

## Track B — Electron Packaging

Wrap Track A properly with a clean Electron shell, correct IPC, full build
pipeline producing installers for **all three platforms**, and tests that
prove parity on each.

| Task | Title | Depends on | Risk | Touches |
|------|-------|-----------|------|---------|
| B01 | Delete root main.js + organize assets | none | low | `./main.js`, `electron/build/`, `electron/assets/` |
| B02 | Use CLI entrypoint properly | A01, B01 | high | `electron/main.js`, `electron/backend.py`, `electron/preload.js` |
| B03 | IPC bridge — wire all preload methods | B02 | medium | `electron/main.js`, `electron/preload.js` |
| B04 | Application menu | B02 | medium | `electron/main.js` |
| B05 | File associations all 3 platforms | B02 | medium | `electron/main.js`, `electron/package.json` |
| B06 | Dev workflow (skip bundle, fast startup) | B02 | low | `electron/package.json`, `electron/main.js` |
| B07 | Build pipeline all 3 platforms | B01, B06 | high | `scripts/bundle-python.js`, `.github/workflows/build-electron.yml`, `electron/package.json` |
| B08 | Testing — parity, e2e, installers all 3 platforms | A01, B02, B07 | high | `scripts/audits/`, `tests/`, `.github/workflows/build-electron.yml` |

## Dependency graph

```
A01 ──┬── B02 ──┬── B03 ── B04 ── B05
      │         │
      │         ├── B06 ── B07 ── B08
      │         │
A02 ──┤         │
      │         │
A03 ──┘         
```

- B01 has no deps, can run first or in parallel with A01
- A01 must complete before B02 (B02 rewrites main.js to use `--headless`)
- A01 and A02 are additive (port resolution added to headless mode)
- A03 replaces backend.py, depends on A01 existing
- B06 then B07 fixes dev/build speed, B07 depends on B06
- B08 is last, needs A01 + B02 + B07
- B03/B04/B05 are parallel after B02

## Platform-specific treatment

Each platform gets full treatment — not just "it compiles":

| Concern | macOS | Windows | Linux |
|---------|-------|---------|-------|
| **Installer** | `.dmg` | `.exe` (NSIS) | `.AppImage` + `.deb` + `.rpm` (TODO: confirm target set) |
| **Icon format** | `.icns` | `.ico` | `.png` (256x256 + 512x512) |
| **File assoc.** | `CFBundleDocumentTypes` (Info.plist) | Registry (NSIS) | `.desktop` + MIME XML (FreeDesktop) |
| **Deep links** | `open-url` event | command line | `.desktop` MimeType registration |
| **App menu** | macOS app menu + Window menu | File > Quit | File > Quit |
| **Python venv** | `bin/python` | `Scripts/python.exe` | `bin/python` (same as macOS) |
| **FFmpeg** | `static_ffmpeg` | `static_ffmpeg` | `static_ffmpeg` |
| **Bundle symlinks** | Resolve uv symlinks | N/A (no symlinks) | N/A (no symlinks) |
| **CI runner** | `macos-14` | `windows-latest` | `ubuntu-latest` |
| **CI test** | Run browser tests | Run browser tests (if Playwright) | Run browser tests |

## Files changed

### src/ (Track A — never touched by Track B)

| File | Task |
|------|------|
| `src/splitshot/cli.py` | A01, A02, A03 |
| `src/splitshot/browser/server.py` | A01, A02 |

### electron/ (Track B)

| File | Task |
|------|------|
| `electron/main.js` | B02, B03, B04, B05 |
| `electron/preload.js` | B02, B03 |
| `electron/backend.py` | A03 (rewrite as thin wrapper) |
| `electron/package.json` | B05, B06, B07 |
| `electron/build/` → `electron/assets/` | B01 |

### scripts/ (Track B)

| File | Task |
|------|------|
| `scripts/bundle-python.js` | B07 |
| `scripts/audits/electron_parity_audit.py` | B08 |

### .github/ (Track B)

| File | Task |
|------|------|
| `.github/workflows/build-electron.yml` | B07, B08 |

### Root cleanup

| File | Task |
|------|------|
| `./main.js` | B01 (DELETE) |

## Verification — all platforms

```
# Track A — Native CLI (any platform)
uv run splitshot --check
uv run splitshot --headless --no-open    # verify CTRL+C clean
uv run pytest tests/ -q

# Track B — macOS
npm --prefix electron run build:mac       # produces electron/build/SplitShot-*.dmg
# Manual: mount .dmg, drag to /Applications, launch, verify everything

# Track B — Windows
npm --prefix electron run build:win       # produces electron/build/SplitShot-*.exe
# Manual: run installer, launch, verify everything

# Track B — Linux
npm --prefix electron run build:linux     # produces electron/build/SplitShot-*.AppImage
# Manual: chmod +x, run, verify everything

# Regression — all platforms
uv run python scripts/testing/run_test_suite.py --mode all-together --format table
uvx ruff check .
```

## Blocker Log

| Blocker | Status | Resolution |
|---------|--------|------------|
| `cli.py` must have `--headless` before B02 can start | OPEN | A01 delivers this |
| `ProjectController.__init__` creates QObject without QApp | INVESTIGATE | Need to verify no signals fire during headless init |
| Windows `.ico` generation tool not available on macOS | OPEN | CI handles this or add `png2ico` via pip |
| Linux `.desktop` file integration in electron-builder | INVESTIGATE | `fileAssociations` in package.json generates this — verify it produces correct FreeDesktop entries |
| `static_ffmpeg` not confirmed in dependency tree | OPEN | Verify during A01/A02 |
| Linux `.AppImage` not testable on macOS during dev | ACCEPTED | Build on CI or use Docker |
