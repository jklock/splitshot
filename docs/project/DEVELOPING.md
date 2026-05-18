# Developing SplitShot

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
- Browser UI runtime: local HTTP server plus desktop runtime support from PySide6
- Automated browser tests: Playwright

The runtime resolves FFmpeg from `PATH`. Packaged Electron builds prepend their bundled media-tools directory to `PATH` before starting the backend.

## Bootstrap

```bash
uv python install 3.12
uv sync --extra dev
uv run python -m playwright install chromium firefox webkit
uv run splitshot --check
```

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

## Read This Next

- [ARCHITECTURE.md](ARCHITECTURE.md)
- [../tests/TEST_SUITE_GUIDE.md](../tests/TEST_SUITE_GUIDE.md)
- [../../scripts/README.md](../../scripts/README.md)
- [ELECTRON_RELEASE.md](ELECTRON_RELEASE.md)
- [GOVERNANCE.md](GOVERNANCE.md)
