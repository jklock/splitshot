# Developing SplitShot

<!-- Documentation reviewed: 2026-08-12 -->

This guide is the day-1 path for a developer or fork owner working from source.

## Start Here

Read in this order:

1. [../../README.md](../../README.md)
2. [ARCHITECTURE.md](ARCHITECTURE.md)
3. [../../src/splitshot/README.md](../../src/splitshot/README.md)
4. [../tests/TEST_SUITE_GUIDE.md](../tests/TEST_SUITE_GUIDE.md)
5. [../../scripts/README.md](../../scripts/README.md)

## Environment

- Python: `3.12`
- Package manager and runner: `uv`
- Required media tools: `ffmpeg`, `ffprobe`
- Electron toolchain: Node.js `22` and `npm`
- Browser UI runtime: local HTTP server plus desktop runtime support from PySide6
- Automated browser tests: Playwright

The runtime resolves FFmpeg from `PATH`. Packaged Electron builds prepend their bundled media-tools directory to `PATH` before starting the backend.

Install platform prerequisites before bootstrapping:

- macOS: Xcode Command Line Tools plus FFmpeg (Homebrew is supported).
- Windows: FFmpeg/FFprobe on `PATH`; use PowerShell for the commands below.
- Linux: FFmpeg/FFprobe and the desktop libraries required by Qt, Electron, and Playwright. AppImage builds additionally require the normal FUSE/AppImage runtime supplied by the distribution.

## Bootstrap

```bash
uv python install 3.12
uv sync --extra dev
uv run python -m playwright install chromium firefox webkit
uv run splitshot --check
cd electron
npm ci
```

`uv run splitshot --check` verifies the Python/runtime prerequisites. `npm ci` installs the exact Electron dependency lock on every supported desktop platform.

## First Commands To Run

```bash
uv run splitshot
uv run splitshot --headless
uv run python scripts/testing/run_test_suite.py --list
uv run python scripts/testing/run_test_suite.py --mode all-together --format table
uvx ruff check .
```

## Day-1 Reading Path

### Product and runtime

- [../../README.md](../../README.md)
- [ARCHITECTURE.md](ARCHITECTURE.md)
- [../../docs/userfacing/USER_GUIDE.md](../userfacing/USER_GUIDE.md)

### Code entrypoints

- [../../src/splitshot/cli.py](../../src/splitshot/cli.py)
- [../../src/splitshot/browser/server.py](../../src/splitshot/browser/server.py)
- [../../src/splitshot/ui/controller.py](../../src/splitshot/ui/controller.py)
- [../../src/splitshot/domain/models.py](../../src/splitshot/domain/models.py)

### Operations

- [../tests/TEST_SUITE_GUIDE.md](../tests/TEST_SUITE_GUIDE.md)
- [../../scripts/README.md](../../scripts/README.md)
- [ELECTRON_RELEASE.md](ELECTRON_RELEASE.md)
- [GOVERNANCE.md](GOVERNANCE.md)

## Working Areas

- Browser shell: [../../src/splitshot/browser/static/README.md](../../src/splitshot/browser/static/README.md)
- Browser API and state serialization: [../../src/splitshot/browser/README.md](../../src/splitshot/browser/README.md)
- Shared mutation layer: [../../src/splitshot/ui/README.md](../../src/splitshot/ui/README.md)
- Project schema: [../../src/splitshot/domain/README.md](../../src/splitshot/domain/README.md)
- Analysis pipeline: [../../src/splitshot/analysis/README.md](../../src/splitshot/analysis/README.md)
- Export pipeline: [../../src/splitshot/export/README.md](../../src/splitshot/export/README.md)

## Validation Strategy

- Start with the narrowest owning pytest target.
- Use [../tests/TEST_SUITE_GUIDE.md](../tests/TEST_SUITE_GUIDE.md) to choose the right suite.
- Use [../../scripts/README.md](../../scripts/README.md) for CI-local, Electron preflight, and browser audit commands.
- Run browser audit scripts only when browser UI, routes, or interaction behavior changed.

## Project And File Contracts

- Creating or selecting a project folder creates `Input/`, `CSV/`, `Markers/`, `Output/`, and `project.json`.
- Media, PractiScore, marker-image, and output pickers start at the corresponding project-owned location. The native dialog may navigate elsewhere; selected inputs are copied into the project immediately.
- Save and autosave update metadata only. Project-local paths are serialized relative to the project root across every stage.
- `Export` configures the active stage's FFmpeg/render settings. `Queue` executes individual, batch, and combined outputs.

Keep this behavior platform-neutral: use `pathlib` in Python and accept both `/` and `\\` at browser boundaries. Never build persisted paths by assuming one operating system's separator.

## Desktop Packaging

From `electron/`, the supported local package commands are:

```bash
npm run build:mac
npm run build:win
npm run build:linux
```

The release artifacts are a macOS DMG, Windows NSIS installer, and Linux AppImage. Packaging is platform-specific; use the matching host or CI job. The normal macOS release path requires signing and notarization credentials. Unsigned local validation is distinct from a publishable macOS release; see [ELECTRON_RELEASE.md](ELECTRON_RELEASE.md).

Before package-native release work, validate the committed corpus and exhaustive manifest:

```bash
uv run python scripts/testing/validate_release_data.py
uv run python scripts/testing/validate_packaged_release_evidence.py manifest
```

Release validation may use only the three tracked files under `tests/release_data/`. Every installed runtime identity and manifest case needs explicit evidence. `scripts/testing/build_packaged_release_summary.py` reports missing identity results, missing case records, skips, and gaps as failures; do not replace those records with a package-launch or pane-screenshot assertion.

## Read This Next

- [ARCHITECTURE.md](ARCHITECTURE.md)
- [../tests/TEST_SUITE_GUIDE.md](../tests/TEST_SUITE_GUIDE.md)
- [../../scripts/README.md](../../scripts/README.md)
- [ELECTRON_RELEASE.md](ELECTRON_RELEASE.md)
- [GOVERNANCE.md](GOVERNANCE.md)
