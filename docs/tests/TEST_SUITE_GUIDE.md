# SplitShot Test Suite Guide

This is the maintainer guide for SplitShot validation. Use it to decide which test to run, why it exists, and which subsystem owns the behavior you changed.

## Start Here

Read this after:

1. [../../README.md](../../README.md)
2. [../project/DEVELOPING.md](../project/DEVELOPING.md)
3. [../project/ARCHITECTURE.md](../project/ARCHITECTURE.md)

Then use:

- [../../scripts/testing/run_test_suite.py](../../scripts/testing/run_test_suite.py) for the canonical suite runner
- [../../scripts/README.md](../../scripts/README.md) for supporting audit and preflight commands

## Fastest Validation Path

1. Run the narrowest useful pytest target for the changed behavior.
2. Run the owning suite if the change affects a shared contract.
3. Use the canonical runner when you want a grouped suite run or a CI-like summary.
4. Use browser audits or Electron preflight only when the change touches those surfaces.

Common commands:

```bash
uv run python scripts/testing/run_test_suite.py --list
uv run python scripts/testing/run_test_suite.py --suite browser --mode all-together --format table
uv run python -m pytest tests/browser/test_browser_static_ui.py
uv run python -m pytest tests/analysis/test_analysis.py
```

The supported test baseline is Python 3.12 with `uv`, FFmpeg/FFprobe on `PATH`, and Node.js 22 plus `npm ci` in `electron/`. Browser and Python suites are platform-neutral; packaged smoke coverage runs against the macOS DMG, Windows NSIS installer, and Linux AppImage in their owning CI jobs.

## Suite Map

| Suite | Owns | Start with |
| --- | --- | --- |
| `analysis` | Shot detection, PractiScore import/normalization, review suggestions, audio feature workflows | `tests/analysis/` |
| `browser` | HTTP routes, static shell, Playwright interactions, browser truth gates, control inventory contracts | `tests/browser/` |
| `cli` | Entrypoint selection, argument parsing, runtime dispatch | `tests/cli/` |
| `export` | FFmpeg export pipeline, overlay rendering, merge export contracts | `tests/export/` |
| `media` | FFmpeg resolver and media-toolchain assumptions | `tests/media/` |
| `persistence` | Project bundle save/load/delete and reopen stability | `tests/persistence/` |
| `presentation` | Timing cards, stage metrics, display summaries | `tests/presentation/` |
| `scoring` | Rulesets, score math, hit factor, merge/scoring integration | `tests/scoring/` |
| `benchmarks` | Reference-stage benchmark helpers and CSV output | `tests/benchmarks/` |
| `scripts` | Runner behavior and analysis-script command contracts | `tests/scripts/` |

## Contract Hotspots

### Browser shell and routes

- Static string-level shell contracts:
  [../../tests/browser/test_browser_static_ui.py](../../tests/browser/test_browser_static_ui.py)
- HTTP API and controller contracts:
  [../../tests/browser/test_browser_control.py](../../tests/browser/test_browser_control.py)
- Playwright interactions:
  [../../tests/browser/test_browser_interactions.py](../../tests/browser/test_browser_interactions.py)
- Browser truth gates:
  [../../tests/browser/test_browser_full_app_e2e.py](../../tests/browser/test_browser_full_app_e2e.py)

### Timing and presentation

- [../../tests/presentation/test_timing_contracts.py](../../tests/presentation/test_timing_contracts.py)
- [../../tests/browser/test_timing_waveform_contracts.py](../../tests/browser/test_timing_waveform_contracts.py)

### Overlay, review, and export

- [../../tests/browser/test_overlay_review_contracts.py](../../tests/browser/test_overlay_review_contracts.py)
- [../../tests/browser/test_browser_rail_layout.py](../../tests/browser/test_browser_rail_layout.py) for effective-zoom viewport containment, aspect-correct video framing, and overlay-coordinate geometry
- [../../tests/export/test_export.py](../../tests/export/test_export.py)
- [../../tests/export/test_merge_export_contracts.py](../../tests/export/test_merge_export_contracts.py)

### Metrics layout and accessibility

- [../../tests/browser/test_metrics_e2e.py](../../tests/browser/test_metrics_e2e.py) owns expanded-workspace containment, responsive columns, dense 8/11/27-competitor axes, selected-shooter identification, and full-name/value accessibility labels.
- [../../tests/browser/test_browser_rail_layout.py](../../tests/browser/test_browser_rail_layout.py) owns minimum-window and scaled-effective-viewport geometry.

### Project files and queue execution

- [../../tests/browser/test_project_lifecycle_contracts.py](../../tests/browser/test_project_lifecycle_contracts.py)
- [../../tests/persistence/test_project_lifecycle_contracts.py](../../tests/persistence/test_project_lifecycle_contracts.py)
- [../../tests/persistence/test_persistence.py](../../tests/persistence/test_persistence.py)
- [../../tests/browser/test_browser_remaining_controls_e2e.py](../../tests/browser/test_browser_remaining_controls_e2e.py)

These tests own required project-folder creation, immediate import into `Input/`, `CSV/`, or `Markers/`, relative all-stage persistence, metadata-only save/autosave, and the separation between Export settings and Queue execution.

### Test-doc contract audits

- [../../tests/browser/test_browser_control_coverage_matrix.py](../../tests/browser/test_browser_control_coverage_matrix.py)
- [../../tests/browser/test_browser_control_inventory_audit.py](../../tests/browser/test_browser_control_inventory_audit.py)

If browser-visible controls change, update the owning tests and the QA docs in `docs/project/` in the same change.

## Debugging Workflow

### A failing narrow test

- Fix the direct issue first.
- Rerun only the failing target.
- Expand to the owning suite after the direct failure is resolved.

### A failing broad suite

- Isolate the smallest failing file or test first.
- Avoid rerunning the full suite repeatedly without a change.
- Use `--mode one-by-one` on the canonical runner if failure isolation matters more than speed.

### Browser regressions

- Start with `test_browser_static_ui.py` for markup, ids, strings, or CSS-contract changes.
- Move to `test_browser_control.py` when the HTTP route or controller contract changed.
- Use Playwright tests when the problem is interaction or render behavior.
- Use standalone audit scripts only when deeper browser evidence is needed.

## Shared Fixtures And Helpers

- `tests/conftest.py`
  owns the Qt app fixture, isolated settings fixture, and synthetic video factory.
- `_open_test_page`, `_load_primary_video`, and related helpers in browser tests
  own common browser setup.
- `synthetic_video_factory`
  is the standard way to generate deterministic media for analysis, browser, and export tests.

## Read This Next

- [../../scripts/README.md](../../scripts/README.md)
- [../project/browser-control-qa-matrix.md](../project/browser-control-qa-matrix.md)
