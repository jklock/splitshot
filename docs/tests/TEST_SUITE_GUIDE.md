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
uv run python scripts/testing/run_test_suite.py --suite pane-match --mode all-together --format table
uv run python scripts/testing/run_test_suite.py --suite pane-performance --mode all-together --format table
uv run python -m pytest tests/browser/test_browser_static_ui.py
uv run python -m pytest tests/analysis/test_analysis.py
```

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

## Opt-in pane lanes

The canonical runner now exposes an initial set of **opt-in pane lanes** for browser-facing work.

These lanes do **not** run by default when you omit `--suite`; they are focused validation slices built from the current browser file layout while the broader pane/modularization split is still being carved out.

| Suite | Owns | Current target shape |
| --- | --- | --- |
| `pane-project` | Landing, Project pane, and PractiScore browser workflows | Project/landing contract files plus selected Project/Landing interaction node IDs |
| `pane-match` | Match workspace lifecycle, setup-once, recap, composite, batch export, and settings-return flows | `test_workspace_flows.py`, `test_workspace_export_and_recap.py`, plus selected Match interaction node IDs |
| `pane-performance` | Performance Library reopen, search/filter, detail, notes/tags, settings, and route-contract flows | `test_library_backend_contracts.py` plus selected Performance interaction node IDs |
| `pane-settings` | Settings section workflows and defaults truth gates | `test_settings_e2e.py` and `test_settings_defaults_truth_gate.py` |
| `pane-metrics` | Metrics export/workbench flows and scoring-metrics contracts | `test_metrics_e2e.py` and `test_scoring_metrics_contracts.py` |

Use these lanes when you need a pane-scoped browser run without paying for the full `browser` suite.

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
- [../../tests/export/test_export.py](../../tests/export/test_export.py)
- [../../tests/export/test_merge_export_contracts.py](../../tests/export/test_merge_export_contracts.py)

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
- [../project/browser-control-coverage-plan.md](../project/browser-control-coverage-plan.md)
- [../project/browser-full-e2e-qa-plan.md](../project/browser-full-e2e-qa-plan.md)
