# Stage Suite, Browser Control, and Packaging Todos

## Benchmark CSV

- [x] Add benchmark CSV generation module or script.
- [x] Include Stage1-4 by default when present.
- [x] Record summary columns: beep, draw, stage time, shot count, average split.
- [x] Record per-shot absolute times, splits, and confidences.
- [x] Generate `artifacts/stage_suite_analysis.csv`.
- [x] Add feature test for CSV generation.

## Browser Control

- [x] Add `splitshot.browser` package with state serialization and local server.
- [x] Add static HTML/CSS/JS browser UI.
- [x] Add `splitshot-web` CLI entry point.
- [x] Support primary/secondary import and automatic analysis.
- [x] Serve local primary/secondary video media to the browser.
- [x] Expose waveform, metric cards, split cards, merge, overlay, scoring, layout, save/open, and export controls.
- [x] Add tests for state serialization and browser API behavior.
- [x] Update README launch instructions.

## Toolchain and Packaging

- [x] Add bundle-aware FFmpeg/FFprobe resolver.
- [x] Keep PATH fallback for development.
- [x] Add packaging README with native build steps.
- [x] Add PyInstaller spec or equivalent packaging manifest.
- [x] Add macOS build script for `.app` and `.dmg`.
- [x] Add Windows build script for `.exe`.
- [x] Document FFmpeg/FFprobe binary placement for bundled builds.

## Validation and Audit

- [x] Run Stage1-4 benchmark generation.
- [x] Run full automated tests.
- [x] Run browser smoke/API validation.
- [x] Run app boot smoke validation.
- [x] Write final audit for analysis, UI, browser, export, toolchain, and packaging.
