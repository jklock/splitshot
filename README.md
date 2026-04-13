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
uv run splitshot
```

The app runs locally and opens your browser at `127.0.0.1:8765`.

Launch without opening a browser automatically:

```bash
uv run splitshot --no-open
```

Launch the secondary desktop UI:

```bash
uv run splitshot --desktop
```

Validate the local runtime:

```bash
uv run splitshot --check
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

## Export

SplitShot exports with local FFmpeg. The app renders the selected video/merge, overlays, and scoring into frames, then encodes a local video file with the selected export variables.

Browser export controls expose:

- Presets: Source MP4, Universal Vertical Master, Short-Form Vertical, YouTube Long-Form 1080p, YouTube Long-Form 4K, and Custom.
- Video: aspect ratio, crop center, target width/height, source/30/60 fps, H.264 or HEVC, bitrate, FFmpeg preset, and optional two-pass encode.
- Audio: AAC, sample rate, and bitrate.
- Color: Rec.709 SDR.
- Containers: output path extensions `.mp4`, `.m4v`, `.mov`, and `.mkv` are supported.
- Logs: the Export pane stores the FFmpeg command/log output for the last export so failures are visible.

Browser file pickers and typed-path imports support common stage containers including `.mp4`, `.m4v`, `.mov`, `.avi`, `.wmv`, `.webm`, `.mkv`, `.mpg`, `.mpeg`, `.mts`, and `.m2ts`.

## Packaging

The source package is browser-first and runnable with one command through `uv run splitshot`. The repository includes `.python-version` with Python 3.12, so `uv` creates/uses the right virtual environment without requiring `--python 3.12` on every command. Native `.dmg` and `.exe` artifacts are intentionally not required for the current workflow.

The app needs `ffmpeg` and `ffprobe`. During development it finds them from `PATH`; packaged/source distributions can also point to bundled binaries with `SPLITSHOT_FFMPEG_DIR`.
