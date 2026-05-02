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
- Browser API behavior lives in [src/splitshot/browser/server.py](../src/splitshot/browser/server.py).
- Shared project mutation logic lives in [src/splitshot/ui/controller.py](../src/splitshot/ui/controller.py).
- Analysis and export code live in [src/splitshot/analysis](../src/splitshot/analysis) and [src/splitshot/export](../src/splitshot/export).

## Testing

The repository uses `pytest` with `qt_api = pyside6`.

- **Browser tests** exercise the SplitShot control UI by driving a real browser through **Playwright** (`tests/browser/test_browser_interactions.py`, `test_browser_control.py`, and others use `sync_playwright` and `chromium.launch(headless=True)`). They are the authoritative automated check for Project-pane behavior, including PractiScore controls, alongside route-level tests that hit `BrowserControlServer` over HTTP.
- The editor’s **Simple Browser** (or any desktop browser tab on `http://127.0.0.1:8765`) is useful for quick manual inspection; it does **not** replace the Playwright suite or the PractiScore session route tests.
- Run the full suite with `uv run pytest`.
- Use `uv run python scripts/testing/run_test_suite.py --mode all-together --format table` for the canonical grouped test run.
- Use `uv run python scripts/testing/run_test_suite.py --mode one-by-one --format json --json-output artifacts/test-run.json` when you need per-file execution and a machine-readable report.
- Run a subset with `uv run pytest tests/export/test_export.py` or any other test module.
- Measure the current baseline with `uv run pytest --cov=src/splitshot --cov-report=term-missing`.
- Re-run browser-focused tests after changing `src/splitshot/browser/static`, `src/splitshot/browser/server.py`, `src/splitshot/ui/controller.py`, or `src/splitshot/overlay/render.py`.
- The Task A PractiScore session slice is covered by `uv run pytest tests/browser/test_practiscore_session_api.py`, plus the PractiScore browser regressions in `uv run pytest tests/browser/test_browser_control.py -k practiscore` and `uv run pytest tests/browser/test_project_lifecycle_contracts.py -k practiscore`.
- Use real media for browser review changes. The development validation set used a primary stage video, a merge stage video, and `example_data/IDPA/IDPA.csv`. If your local `Stage1.MP4` / `Stage2.MP4` files are not available, substitute equivalent real clips rather than synthetic placeholders.
- Use `uv run python scripts/analysis/analyze_video_shots.py /path/to/video.mp4` when you want to inspect split timing, confidence, and a recommended starting sensitivity threshold before importing a clip into the browser shell.
- The audit defaults to the available Chromium, Firefox, and Safari-class WebKit targets and also picks up installed Chrome or Edge channels when present.
- The VS Code / Cursor **Simple Browser** is useful for Chromium-class debugging of the local shell, but regression validation for browser workflows should run from the terminal through **pytest + Playwright** (and the audit scripts below when you need Firefox/WebKit or real media).

### PractiScore Session Smoke Check

- **Automated:** `uv run pytest tests/browser/test_practiscore_session_api.py` (HTTP + faked Qt runtime; no Playwright). For UI wiring, also run PractiScore-related slices in `tests/browser/test_browser_interactions.py` and `tests/browser/test_practiscore_sync_controller.py` — those use **Playwright** against the live `BrowserControlServer`.
- **Manual:** Start the browser server with `uv run splitshot --no-open`. Open the SplitShot UI in your desktop browser or the editor **Simple Browser** at `http://127.0.0.1:8765/`. Click **Connect PractiScore**. With a PractiScore login already present in a supported system browser, the session should become ready without credential fields inside SplitShot. If SplitShot opens PractiScore in the system browser, complete login or any challenge **there** (not inside SplitShot form fields). Do not add or use SplitShot UI fields for PractiScore username, password, or MFA.
- Confirm `GET /api/practiscore/session/status` transitions through the expected stable states and that `POST /api/practiscore/session/clear` resets cached session state when you need a fresh connect.

## Script Layout

- `scripts/setup/` contains workstation bootstrap scripts.
- `scripts/testing/` contains the master test runner.
- `scripts/audits/browser/` contains real browser validation helpers.
- `scripts/analysis/` contains ShotML and detection helpers.
- `scripts/export/` contains export-side utilities.
- `scripts/tooling/` contains environment validation helpers.

### Browser Audit Scripts

| Script | Purpose | Use it when | Pass means |
| --- | --- | --- | --- |
| `scripts/audits/browser/run_browser_ui_surface_audit.py` | Real browser UI smoke checks for overlay placement, waveform drag, layout resize, and merge file input flow | You changed static browser assets and want a fast rendered-shell pass | The rendered shell stays inside the video frame, resize handles persist, waveform drag still acts on the right data, and merge media controls still work in a real browser |
| `scripts/audits/browser/run_browser_av_audit.py` | Real browser audio/video playback validation against BrowserControlServer | You changed preview media handling or need Firefox/WebKit playback coverage | Real desktop browsers can load, play, pause, and mute the local media path without browser-specific regressions |
| `scripts/audits/browser/run_browser_interaction_audit.py` | Real end-to-end interaction audit with actual media files and route assertions | You changed workflow behavior and need drag, scroll, PractiScore, PiP, and review coverage | Route-backed interactions persist after rerender, including review scrolling, overlay lock/drag behavior, merge preview movement, imported-summary state, and PractiScore round trips |

- When a browser audit fails, check `logs/splitshot-browser-*.log` first.
- Use `--report-json artifacts/<name>.json` on the interaction audit when you want a saved machine-readable report.
- For large local media files, prefer the path import workflow in the browser shell over browser-upload staging.

### Manual Reviewer Checklist

- Confirm overlay controls are WYSIWYG. The browser preview and exported file must agree on badge size, spacing, opacity, imported-summary placement, custom review bubbles, and merge layout.
- Confirm every opacity slider has an adjacent editable percent field. Changing the slider or the percent field should update the same value and the same visual result.
- Confirm timer, draw, score, and review-bubble lock toggles default to the overlay stack. Unlocking should allow independent drag; relocking should return the item to the stack without leaving stale free-position behavior behind.
- Confirm the Review inspector can be scrolled, then changed, without snapping back or causing review-bubble jitter after the real `/api/overlay` round trip.
- Confirm one real export from the browser shell before sign-off. Browser audits do not replace a final rendered-file check.

## Coverage Baseline And Plan

As of 2026-04-18, `uv run pytest --cov=src/splitshot --cov-report=term-missing` reports `204 passed` and `TOTAL 86%` on macOS with Python 3.12. The repository is not yet at 100% line coverage, so coverage work needs to stay explicit and staged.

“100% code covered with real non-mock tests” is not a single metric. Real browser/media/export tests should cover the critical user behavior, but some branches still need controlled tests because a live end-to-end run cannot reliably force every invalid payload, OS dialog edge, FFmpeg failure, or CLI exit path. The right standard for this repository is:

- real tests own the important user flows and WYSIWYG validation;
- coverage work stays honest about the remaining branches that need deterministic tests;
- we do not claim 100% until the measured command actually reports it.

Browser-visible controls also have an explicit coverage map in [browser-control-qa-matrix.md](browser-control-qa-matrix.md). When you change a button or field, update that matrix row and the matching tests in the same change so the browser QA claim stays explicit.

The exhaustive control-by-control worklist lives in [browser-control-coverage-plan.md](browser-control-coverage-plan.md). Use it when you need to see every user-facing control rather than the summarized coverage matrix.

The browser interaction smoke tests now cover waveform expand/zoom/amplitude, waveform pan and shot movement, layout lock/resize persistence, waveform navigator drag/reload persistence, timing/scoring workbench row actions, overlay visibility and badge toggles, and review text-box creation and drag in [tests/browser/test_browser_interactions.py](../../tests/browser/test_browser_interactions.py).

| Area | Current hotspots | Next step |
| --- | --- | --- |
| Entry points and CLI glue | `src/splitshot/__main__.py` 0%, `src/splitshot/browser/cli.py` 0%, `src/splitshot/benchmarks/cli.py` 0%, `src/splitshot/cli.py` 61% | Add command-dispatch tests that execute the public entrypoints, cover `--check` and failure exits, and verify browser/benchmark launch plumbing without opening a browser window |
| Media, export, and server error paths | `src/splitshot/media/thumbnails.py` 0%, `src/splitshot/export/pipeline.py` 83%, `src/splitshot/browser/server.py` 80% | Add tempdir integration tests for thumbnail generation, export failure branches, HTTP validation errors, and activity-log/reporting paths |
| Analysis and PractiScore parsing | `src/splitshot/analysis/detection.py` 72%, `src/splitshot/scoring/practiscore.py` 84%, `src/splitshot/utils/time.py` 43% | Add fixture-driven detection edge cases, malformed-row PractiScore coverage, and explicit time-format boundary tests |
| Overlay and controller behavior | `src/splitshot/overlay/render.py` 86%, `src/splitshot/ui/controller.py` 88% | Expand browser/control and export tests around overlay lock state, review-box stack behavior, and render-time fallback branches |

- New work in these modules should add targeted tests instead of relying on the current aggregate percentage.
- Do not claim 100% coverage in PRs or release notes until the command above actually reports it.

## Project State Files

- App settings live in `~/.splitshot/settings.json`.
- Saved projects are `.ssproj` bundle directories containing `project.json` and copied media when needed.
- Browser-session imports may be stored in temporary session directories while the browser server is running.

## Change Discipline

- Keep browser behavior aligned with the shared controller and domain model when those layers change.
- Update both the project bundle load/save path and the browser state serialization when the project schema changes.
- Use the technical docs in `src/splitshot/.../README.md` to locate the owning module before adding new behavior.

**Last updated:** 2026-04-27
**Referenced files last updated:** 2026-04-27
