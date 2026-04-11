# Stage Suite, Browser Control, and Packaging Gap Analysis

## Current State

- Stage1 has a benchmark test and is close to the confirmed real stage time.
- Stage2, Stage3, and Stage4 exist but do not yet have CSV output.
- The app is desktop-only.
- The video toolchain currently shells out to `ffmpeg` and `ffprobe` from `PATH`.
- There is no packaging manifest for browser assets or bundled media binaries.
- Existing tests cover analysis, UI shell, merge, scoring, persistence, and export, but not benchmark CSV generation or browser control.

## Gaps

1. Multi-stage benchmark output is manual.
   - Impact: SplitShot results cannot be compared consistently against Shot Streamer for Stage2-4.
   - Closure: Add a repeatable benchmark CSV script and commit generated CSV output.

2. Browser control interface is missing.
   - Impact: Users cannot choose browser-based operation.
   - Closure: Add a local HTTP control server, static browser UI, JSON API, and CLI entry point.

3. Browser mode must not duplicate business logic.
   - Impact: Parallel implementations would drift from desktop behavior.
   - Closure: Reuse `ProjectController`, timeline metrics, project persistence, and export pipeline.

4. FFmpeg/FFprobe are not bundle-aware.
   - Impact: Packaged builds would still fail on machines without system FFmpeg.
   - Closure: Add binary resolution that checks packaged resources first and falls back to `PATH`.

5. Packaging outputs are not defined.
   - Impact: There is no reliable route to `.dmg` or `.exe`.
   - Closure: Add PyInstaller spec plus native macOS and Windows build scripts.

6. Full feature/toolchain validation is only partially documented.
   - Impact: It is unclear what is proven versus assumed.
   - Closure: Add an audit document after implementation with test results, benchmark output, packaging status, and remaining risks.

## Acceptance Checklist

- `artifacts/stage_suite_analysis.csv` exists and includes Stage1-4 output.
- `uv run splitshot-web` starts a local browser-control server.
- Browser API can import a video, analyze it, return split metrics, mutate shot/beep state, and export.
- Existing desktop UI remains available through `uv run splitshot`.
- FFmpeg resolver supports bundled binaries.
- Packaging scripts exist for macOS `.dmg` and Windows `.exe` native builds.
- Feature tests pass.
- Final audit explains what was validated, what was not, and what is required for production packaging.
