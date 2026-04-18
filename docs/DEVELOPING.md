# Developing SplitShot

This project is designed to be run directly from source with `uv` and Python 3.12.

## Environment

- Python version: 3.12
- Package manager / runner: `uv`
- Required media tools: `ffmpeg` and `ffprobe`

The runtime locates media binaries from `PATH` first, then from bundled resources, and it also honors `SPLITSHOT_FFMPEG_DIR`.

## Common Commands

```bash
uv run splitshot
uv run splitshot --no-open
uv run splitshot --check
uv run pytest
uv run python -m playwright install chromium firefox webkit
uv run python scripts/run_browser_ui_surface_audit.py
uv run python scripts/run_browser_av_audit.py
uv run python scripts/run_browser_interaction_audit.py --primary-video /path/to/Stage1.MP4 --merge-video /path/to/Stage2.MP4 --practiscore /path/to/IDPA.csv
uv run splitshot-benchmark-csv --output artifacts/stage_suite_analysis.csv
```

## Working Areas

- Browser UI assets live in [src/splitshot/browser/static](../src/splitshot/browser/static).
- Browser API behavior lives in [src/splitshot/browser/server.py](../src/splitshot/browser/server.py).
- Shared project mutation logic lives in [src/splitshot/ui/controller.py](../src/splitshot/ui/controller.py).
- Analysis and export code live in [src/splitshot/analysis](../src/splitshot/analysis) and [src/splitshot/export](../src/splitshot/export).

## Testing

The repository uses `pytest` with `qt_api = pyside6`.

- Run the full suite with `uv run pytest`.
- Run a subset with `uv run pytest tests/test_export.py` or any other test module.
- Re-run browser-focused tests after changing `src/splitshot/browser/static` or `src/splitshot/browser/server.py`.
- Use `uv run python scripts/run_browser_ui_surface_audit.py` when you need rendered DOM smoke checks for the browser shell.
- Use `uv run python scripts/run_browser_av_audit.py` when you need a live media import, play, and mute audit against Firefox or Safari-class WebKit.
- Use `uv run python scripts/run_browser_interaction_audit.py --primary-video ... --merge-video ... --practiscore ...` when you need real interaction validation for scroll, drag, waveform, PiP, and imported-summary behavior against actual browser routes and real media files.
- The audit defaults to the available Chromium, Firefox, and Safari-class WebKit targets and also picks up installed Chrome or Edge channels when present.
- The VS Code integrated browser is useful for Chromium-class debugging, but actual cross-browser validation should run from the VS Code terminal through Playwright.

### Browser Audit Scripts

| Script | Purpose | Use it when | Typical output |
| --- | --- | --- | --- |
| `scripts/run_browser_ui_surface_audit.py` | Real browser UI smoke checks for overlay placement, waveform drag, layout resize, and merge file input flow | You changed static browser assets and want a fast rendered-shell pass | Console summary plus optional JSON report |
| `scripts/run_browser_av_audit.py` | Real browser audio/video playback validation against BrowserControlServer | You changed preview media handling or need Firefox/WebKit playback coverage | Console summary and browser/server log files |
| `scripts/run_browser_interaction_audit.py` | Real end-to-end interaction audit with actual media files and route assertions | You changed workflow behavior and need drag, scroll, PractiScore, PiP, and review coverage | Console summary, optional JSON report, and browser activity log |

- When a browser audit fails, check `logs/splitshot-browser-*.log` first.
- Use `--report-json artifacts/<name>.json` on the interaction audit when you want a saved machine-readable report.
- For large local media files, prefer the path import workflow in the browser shell over browser-upload staging.

## Project State Files

- App settings live in `~/.splitshot/settings.json`.
- Saved projects are `.ssproj` bundle directories containing `project.json` and copied media when needed.
- Browser-session imports may be stored in temporary session directories while the browser server is running.

## Change Discipline

- Keep browser behavior aligned with the shared controller and domain model when those layers change.
- Update both the project bundle load/save path and the browser state serialization when the project schema changes.
- Use the technical docs in `src/splitshot/.../README.md` to locate the owning module before adding new behavior.

**Last updated:** 2026-04-17
**Referenced files last updated:** 2026-04-17
