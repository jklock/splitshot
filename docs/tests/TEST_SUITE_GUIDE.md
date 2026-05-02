# SplitShot Test Suite Guide

## Overview

The SplitShot test suite is organized into 10 suites totaling 430+ tests across analysis, browser interaction, export, scoring, and supporting infrastructure. Tests run via pytest with Playwright for browser workflow simulations and FFmpeg for export/media pipeline validation.

## Running Tests

### Canonical Runner

```bash
# All suites together (fastest):
uv run python scripts/testing/run_test_suite.py --mode all-together --format table

# One file at a time (isolates failures):
uv run python scripts/testing/run_test_suite.py --mode one-by-one --format table --stop-on-failure

# Specific suite:
uv run python scripts/testing/run_test_suite.py --suite analysis --mode all-together --format table
```

### Direct pytest

```bash
# Single test file:
uv run python -m pytest tests/analysis/

# Single test:
uv run python -m pytest tests/analysis/test_analysis.py::test_analysis_detects_beep_and_shots -v

# Browser tests (headless Playwright):
uv run python -m pytest tests/browser/test_browser_control.py --tb=short -q

# Static UI tests (no browser needed):
uv run python -m pytest tests/browser/test_browser_static_ui.py
```

### Runner Options

```
--suite <name>        Repeat to select specific suites (analysis, browser, cli, export,
                      media, persistence, presentation, scoring, benchmarks, scripts)
--mode all-together   Single pytest invocation (default: one-by-one)
--format table|json|raw  Output format (default: table)
--stop-on-failure     Halt after first failed run
--pytest-arg <arg>    Pass additional arguments to pytest (repeatable)
--dry-run             Show execution plan without running
--list                List available suites and exit
```

## Test Suites

### Analysis (`tests/analysis/` — 63 tests)

Tests shot detection, PractiScore import/sync, ShotML settings, timing analysis, and audio profiling.

**Key files:**
- `test_analysis.py` — Audio beep detection, shot detection, threshold changes, PractiScore integration, ShotML refinement, timing events, probe metadata
- `test_corpus.py` — Feature extraction consistency, beep classification, review flag generation, duplicate group detection
- `test_practiscore_import.py` — CSV/report import for IDPA and USPSA formats
- `test_practiscore_sync_normalize.py` — Remote PractiScore artifact normalization
- `test_practiscore_web_extract.py` — Match discovery and remote artifact download

**Dependencies:** `ffmpeg`, `ffprobe`, `synthetic_video_factory` fixture

### Browser (`tests/browser/` — 228 tests)

Tests the browser-based UI shell, API routes, Playwright-driven interactions, static asset integrity, and end-to-end workflow truth gates.

**Key files:**
- `test_browser_control.py` (71 tests) — Server routes, file uploads, PractiScore import, overlay API, autosave, settings, export, media serving, project lifecycle
- `test_browser_static_ui.py` (21 tests) — Static analysis of `index.html`, `app.js`, `styles.css` — no browser needed. Verifies element structure, CSS rules, JS function signatures, HTML attribute correctness
- `test_browser_interactions.py` (40 tests) — Playwright-driven UI simulation: waveform controls, marker workbench, overlay badges, text-box editing, export log modal, color picker, popup bubbles, motion paths
- `test_browser_rail_layout.py` — Layout resize handles, tool routing, layout lock, status bar, marker workbench bottom resize
- `test_browser_full_app_e2e.py` (6 tests) — End-to-end workflow truth gates covering PractiScore+tIming+scoring persistence, markers+review+overlay parity, merge+export sync, settings defaults, ShotML rerun
- `test_browser_remaining_controls_e2e.py` — Edge controls: waveform shell remaining buttons, marker templates, color picker, badge style grid, merge defaults, export encoding, ShotML numeric controls
- `test_metrics_e2e.py` — Metrics pane reflects scoring workbench edits and timing event changes
- `test_merge_export_contracts.py` — Export path contract, merge source offset persistence
- Other contract/audit files: `test_project_lifecycle_contracts.py`, `test_overlay_review_contracts.py`, `test_settings_e2e.py`, `test_settings_defaults_truth_gate.py`, `test_scoring_metrics_contracts.py`, `test_timing_waveform_contracts.py`, `test_browser_control_inventory_audit.py`, `test_browser_control_coverage_matrix.py`, `test_practiscore_session_api.py`, `test_practiscore_sync_controller.py`

**Dependencies:** `playwright` (Chromium), `synthetic_video_factory` fixture, `BrowserControlServer`

**Note on static UI tests:** The 21 static tests read `app.js`, `styles.css`, and `index.html` directly from disk and assert on string content. These tests verify function signatures, CSS class names, HTML structure, and data attributes. They do not launch a browser and run in milliseconds.

### CLI (`tests/cli/` — 8 tests)

Tests CLI argument dispatch to browser mode, log levels, and command-line help.

**Key file:** `test_cli.py`

**Pattern:** Uses `monkeypatch.setattr` to intercept browser dispatch and verify argument passing without launching.

### Export (`tests/export/` — 37 tests)

Tests FFmpeg export pipeline, overlay rendering, merge layout, and encoding presets.

**Key files:**
- `test_export.py` — Rendering to MP4, crop alignment, overlay image/badge rendering, timing markers, aspect ratio, decoder pipe shutdown
- `test_merge_export_contracts.py` — Export contract consistency

**Dependencies:** `ffmpeg`, `PySide6` (QPainter rendering), `synthetic_video_factory` fixture

### Media (`tests/media/` — 1 test)

Tests FFmpeg binary resolution from environment/configuration.

**Key file:** `test_media_toolchain.py`

**Pattern:** Writes a fake `ffmpeg` executable to `tmp_path`, sets `SPLITSHOT_FFMPEG_DIR`, asserts `resolve_media_binary` returns it.

### Persistence (`tests/persistence/` — 14 tests)

Tests project save/load round-trips, serialization correctness, and feature state preservation.

**Key files:**
- `test_persistence.py` — Project-to-dict round-trips, shot/timing/scoring/overlay/popup/practiscore persistence
- `test_project_lifecycle_contracts.py` — Project lifecycle contract tests

### Presentation (`tests/presentation/` — 14 tests)

Tests stage presentation model: timing segments, split calculations, badge rendering triggers, and popup bubble presentation.

**Key files:**
- `test_presentation.py` — Timing segments, event splits, beep-to-final timing
- `test_popup_presentation.py` — Popup bubble presentation logic
- `test_timing_contracts.py` — Timing computation contract verification

### Scoring (`tests/scoring/` — 20 tests)

Tests scoring logic, merge canvas calculation, hit factor computation, and scoring preset application.

**Key files:**
- `test_scoring_and_merge.py` — Hit factor, scoring presets, merge canvas sizes, overlay positioning
- `test_scoring_metrics_contracts.py` — Scoring metrics contract verification

**Pattern:** Pure unit tests creating in-memory `Project()` instances with inline data. No fixtures needed.

### Benchmarks (`tests/benchmarks/` — 6 tests)

Tests stage timing benchmarks against known reference values and shot detection against a shotstreamer reference.

**Key files:**
- `test_stage_raw_benchmark.py` — Parameterized test comparing raw stage time against expected values for 4 benchmark videos (requires real media in `.training/`)
- `test_stage1_benchmark.py` — Shot detection benchmark against shotstreamer reference
- `test_stage_suite_csv.py` — Export stage suite results as CSV

### Scripts (`tests/scripts/` — 40 tests)

Tests the training pipeline and analysis scripts: dataset extraction, auto-labeling, manifest bootstrapping, model training, and timing accuracy evaluation.

**Key files:**
- `test_run_test_suite.py` — Tests the test runner itself (suite listing, dry-run, JSON output)
- `test_extract_training_dataset.py`, `test_bootstrap_training_manifest.py`, `test_autolabel_training_manifest.py`
- `test_analyze_video_shots.py`, `test_audit_training_corpus.py`
- `test_evaluate_timing_accuracy.py`, `test_prioritize_training_review.py`
- `test_run_auto_training_pipeline.py`, `test_train_audio_event_model_from_dataset.py`

## Shared Fixtures

All fixtures are defined in `tests/conftest.py` and apply automatically:

| Fixture | Scope | Purpose |
|---|---|---|
| `_ensure_qapp` | function (autouse) | Creates a Qt `QApplication` with `QT_QPA_PLATFORM=offscreen` for any test that needs it |
| `_isolate_splitshot_settings` | function (autouse) | Redirects settings to `tmp_path/home/.splitshot`, preserves Playwright browser cache. All tests run with isolated configuration |
| `synthetic_video_factory` | function | Returns `create_video(name, duration_ms, beep_ms, shot_times_ms, resolution, audio_stream_offset_ms)` that generates synthetic MP4 files with programmable beep and shot sounds. Used by analysis, browser, and export tests |

## Test Patterns

### Static File Assertion Tests

Tests in `test_browser_static_ui.py` read `index.html`, `app.js`, and `styles.css` from `src/splitshot/browser/static/` and assert on string content. These verify:
- HTML class names, data attributes, tool ordering
- JavaScript function signatures, object structures, event handlers
- CSS selectors, container queries, flex/grid layouts

No browser required. Fast (~0.5s for 21 tests).

### Playwright Interaction Tests

Tests in `test_browser_interactions.py` and `test_browser_full_app_e2e.py` launch a headless Chromium browser via Playwright. The pattern is:

```python
server = BrowserControlServer(port=0)
server.start_background(open_browser=False)
try:
    with sync_playwright() as playwright:
        browser, page = _open_test_page(playwright, server)
        try:
            # interact with page elements
            # assert page.evaluate(...) results
        finally:
            browser.close()
finally:
    server.shutdown()
```

Helper functions (`_open_test_page`, `_load_primary_video`, `_open_tool`) are shared across interaction test files.

### Controller Contract Tests

Tests in `test_browser_control.py` exercise server routes directly via HTTP POST to `http://localhost:<port>/api/<route>` without a browser. The `BrowserControlServer` runs in background thread. Tests verify JSON response payloads.

### Pure Unit Tests

Tests in `test_scoring_and_merge.py`, `test_presentation.py`, and `test_persistence.py` create domain model instances in memory and exercise business logic. No external services, no fixtures needed.

### Coverage Matrix Audit

`test_browser_control_coverage_matrix.py` reads `docs/project/browser-control-qa-matrix.md` and asserts that every browser control mentioned in the matrix has a corresponding test. This serves as a contract ensuring test coverage documentation stays in sync with the actual test suite.

## Writing Tests

### Adding a New Test

1. Place the test in the appropriate suite directory:
   - Analysis behavior → `tests/analysis/`
   - Browser route/API → `tests/browser/test_browser_control.py`
   - Browser UI interaction → `tests/browser/test_browser_interactions.py`
   - Static asset verification → `tests/browser/test_browser_static_ui.py`
   - Export pipeline → `tests/export/`
   - Business logic → `tests/scoring/`, `tests/presentation/`
   - Data persistence → `tests/persistence/`

2. Use the `synthetic_video_factory` fixture when tests need video media:
   ```python
   def test_my_feature(synthetic_video_factory) -> None:
       video = Path(synthetic_video_factory(name="my-test"))
   ```

3. For new Playwright interaction tests, use the shared helpers:
   ```python
   server = BrowserControlServer(port=0)
   server.start_background(open_browser=False)
   with sync_playwright() as playwright:
       browser, page = _open_test_page(playwright, server)
       # ...
   ```

4. Register the test suite in `scripts/testing/run_test_suite.py` if creating a new test directory.

### Test Naming

- Use `test_<feature>_<behavior>` pattern
- Browser route tests: `test_browser_<route>_<behavior>`
- Interaction tests: `test_<feature>_<action>_<expected_result>`
- Static tests: `test_browser_ui_<verification>`

## Environment & Dependencies

### Required

- Python 3.12+
- `uv` package manager
- `ffmpeg` and `ffprobe` on `PATH`
- `playwright` Chromium browser (`uv run python -m playwright install chromium`)

### Environment Variables

| Variable | Purpose |
|---|---|
| `QT_QPA_PLATFORM` | Set to `offscreen` by `conftest.py` for headless Qt |
| `HOME` | Isolated to `tmp_path/home` by `_isolate_splitshot_settings` fixture |
| `PLAYWRIGHT_BROWSERS_PATH` | Preserved to system cache by `_isolate_splitshot_settings` |
| `SPLITSHOT_FFMPEG_DIR` | Override FFmpeg binary directory (used by `test_media_toolchain.py`) |

## Regression & Audit Scripts

For browser workflow regressions, prefer:

1. Targeted pytest for the touched code.
2. Browser suite: `uv run pytest tests/browser/`
3. Canonical runner: `uv run python scripts/testing/run_test_suite.py --mode all-together --format table`
4. Full isolation: `uv run python scripts/testing/run_test_suite.py --mode one-by-one --format json --json-output artifacts/test-run.json --stop-on-failure`

Do not run browser audit scripts unless browser UI, routes, or controller behavior changed.
Do not run ShotML pipeline scripts unless analysis or timing behavior changed.

**Last updated:** 2026-05-01
