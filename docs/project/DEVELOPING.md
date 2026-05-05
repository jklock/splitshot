# Developing SplitShot

This project is designed to be run directly from source with `uv` and Python 3.12.

## Environment

- Python version: 3.12
- Package manager / runner: `uv`
- Required media tools: `ffmpeg` and `ffprobe`
- PractiScore remote sync in the live app uses PySide6 Qt WebEngine for background fetch after cookies are imported. **Automated browser UI tests** under `tests/browser/` use **Playwright** (typically headless Chromium via `sync_playwright`). Playwright is a dev/test dependency; it is not the runtime PractiScore engine.

The runtime locates media binaries from `PATH` first, then from bundled resources, and it also honors `SPLITSHOT_FFMPEG_DIR`.

## Common Commands

```bash
uv run splitshot
uv run splitshot --no-open
uv run splitshot --check
uv run python scripts/testing/run_test_suite.py --mode all-together --format table
uv run pytest --cov=src/splitshot --cov-report=term-missing
uv sync --extra dev
uv run python -m playwright install chromium firefox webkit
uv run pytest tests/browser/test_practiscore_session_api.py
uv run pytest tests/browser/test_browser_control.py -k practiscore
uv run pytest tests/browser/test_project_lifecycle_contracts.py -k practiscore
uv run python scripts/audits/browser/run_browser_ui_surface_audit.py
uv run python scripts/audits/browser/run_browser_av_audit.py
uv run python scripts/audits/browser/run_browser_interaction_audit.py --primary-video /path/to/Stage1.MP4 --merge-video /path/to/Stage2.MP4 --practiscore /path/to/IDPA.csv
uv run python scripts/analysis/analyze_video_shots.py /path/to/Stage1.MP4 --format table --json-output artifacts/shot-preview.json
uv run python scripts/export/export_stage_suite_csv.py --output artifacts/stage_suite_analysis.csv
```

## Working Areas

- Browser UI assets live in [src/splitshot/browser/static](../src/splitshot/browser/static).
  - `app.js` is now an ESM bootstrap module (26 imports, delegates to module factories).
  - `lib/` contains shared backbone modules (API client, state store, event bus, layout, keys, shell-runtime).
  - `components/` contains reusable UI components (status-bar, video-player, waveform, overlay-canvas).
  - `panes/` contains individual pane modules (11 panes plus pane-base).
  - `styles/` contains split CSS files (theme, layout, components, panes, widgets).
- Browser API behavior lives in [src/splitshot/browser/server.py](../src/splitshot/browser/server.py).
- Shared project mutation logic lives in [src/splitshot/ui/controller.py](../src/splitshot/ui/controller.py).
- Analysis and export code live in [src/splitshot/analysis](../src/splitshot/analysis) and [src/splitshot/export](../src/splitshot/export).

**Last updated:** 2026-05-04
**Referenced files last updated:** 2026-05-04
