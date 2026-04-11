# Stage Suite, Browser Control, and Packaging Plan

## Inputs

- `Directions.md` remains the source of truth for the local Shot Streamer-style editing workflow.
- `Stage1.MP4` is the first calibrated benchmark. The confirmed real stage time from beep to final shot is 13.55 seconds.
- `Stage2.MP4`, `Stage3.MP4`, and `Stage4.MP4` are new benchmark inputs that need SplitShot-generated data in the same comparison format so Shot Streamer results can be added later.
- The screenshot `Raw` column is the timing benchmark for stage performance. SplitShot's beep-to-final-shot duration should be exported as `raw_time_*`.
- Shot Streamer parity still means upload-first automatic analysis, timer beep detection, shot detection, waveform review, split timing, scoring, overlay, merge, layout, export, save/load, and project re-export.

## Research Notes

- Qt for Python includes deployment tooling through `pyside6-deploy`, which can produce platform executables including `.exe` on Windows and `.app` on macOS. It does not by itself create a signed/notarized `.dmg`.
- PyInstaller spec files can explicitly include binary files. That is the right packaging escape hatch for bundling `ffmpeg` and `ffprobe` with SplitShot instead of requiring users to install them separately.
- A browser control interface can be built without adding a web framework by using Python's standard library HTTP server and the existing SplitShot controller/domain/export pipeline.

## Goals

1. Produce a repeatable Stage1-4 benchmark CSV from the local detector.
2. Add a web-browser control mode that runs locally, uses the same backend model, and exposes the same main workflow as the desktop app.
3. Validate the video toolchain and application features with feature-focused automated tests and a written audit.
4. Add packaging support that expects bundled FFmpeg/FFprobe binaries and can produce a self-contained macOS `.dmg` and Windows `.exe` from native builders.

## Benchmark CSV

Create a script that:

- Accepts one or more video paths.
- Runs `analyze_video_audio` at the configured threshold.
- Computes beep time, draw time, raw time, shot count, average split, absolute shot times, split times, and confidences.
- Writes a wide CSV that matches the screenshot comparison shape: one stage per row with summary columns and repeated `shot_*` / `split_*` columns.
- Writes deterministic column order so future Shot Streamer values can be merged manually or by a later script.

Expected output file:

- `artifacts/stage_suite_analysis.csv`

## Browser Control Mode

Add a local browser mode with:

- CLI command: `splitshot-web`.
- Static single-page UI served locally.
- JSON API backed by `ProjectController`.
- Upload/import by local filesystem path.
- Automatic primary analysis after primary import.
- Automatic secondary analysis and sync after secondary import.
- Project state summary with draw, stage, shot count, average split, waveform data, shot list, scoring, overlay, merge, layout, export, and status.
- Video preview using the local server as a media source.
- Waveform canvas and split-card review.
- Controls for shot add/move/delete, beep move, score assignment, penalties, overlay position, merge layout, PiP size, export quality, save/open project, and MP4 export.

This is a local control interface, not a hosted SaaS replacement. It should bind to `127.0.0.1` by default.

## Packaging

Add packaging support with:

- Runtime FFmpeg resolver that checks bundled app resources before falling back to `PATH`.
- A packaging manifest/spec that includes package data, browser assets, and bundled media-tool binaries.
- A macOS build script that creates a `.app` and wraps it in a `.dmg`.
- A Windows build script that creates an `.exe` bundle using the same spec and bundled Windows FFmpeg binaries.
- Documentation of the native-build constraint: `.dmg` should be built on macOS, `.exe` should be built on Windows.

## Validation

Automated validation should cover:

- Benchmark CSV generation from real stage files when present.
- Browser API state output after automatic analysis.
- Browser API edit controls mutating the same project model correctly.
- FFmpeg resolver choosing a bundled binary when available.
- Existing desktop analysis, merge, scoring, persistence, export, and UI tests.

Manual/toolchain audit should cover:

- FFmpeg/FFprobe detection and bundled fallback.
- Analysis accuracy evidence.
- Export path and codec assumptions.
- Desktop UI workflow.
- Browser control workflow.
- Packaging readiness and platform constraints.
