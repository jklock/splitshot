# SplitShot

Local-first competition shooting video analysis, merge, scoring, and export.

## Status

This repository contains:

- The implementation plan derived from `Directions.md`
- A browser-first local control interface
- A secondary Python 3.12 / PySide6 desktop interface
- Feature-focused automated tests

## Quick Start

Launch the browser control interface:

```bash
uv run --python 3.12 splitshot
```

The app runs locally and opens your browser at `127.0.0.1:8765`.

Launch without opening a browser automatically:

```bash
uv run --python 3.12 splitshot --no-open
```

Launch the secondary desktop UI:

```bash
uv run --python 3.12 splitshot --desktop
```

Validate the local runtime:

```bash
uv run --python 3.12 splitshot --check
```

Compatibility aliases are also available:

```bash
uv run splitshot-web
uv run splitshot-desktop
```

## Stage Benchmark CSV

Generate local detector output for `Stage1.MP4` through `Stage4.MP4`:

```bash
uv run splitshot-benchmark-csv --output artifacts/stage_suite_analysis.csv
```

## Test

```bash
uv run pytest
```

## Toolchain Validation

```bash
uv run splitshot --check
```

## Packaging

The source package is browser-first and runnable with one command through `uv run --python 3.12 splitshot`. Native `.dmg` and `.exe` artifacts are intentionally not required for the current workflow.

The app needs `ffmpeg` and `ffprobe`. During development it finds them from `PATH`; packaged/source distributions can also point to bundled binaries with `SPLITSHOT_FFMPEG_DIR`.
