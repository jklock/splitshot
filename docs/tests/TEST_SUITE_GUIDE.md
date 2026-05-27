# SplitShot Test Suite Guide

This is the maintainer guide for SplitShot validation. Use it to decide which test to run, why it exists, and which subsystem owns the behavior you changed.

This guide **consumes** the canonical testing taxonomy from `../project/development/Testing/spec.md` and the canonical evidence contract from `../project/development/Testing/artifacts.md`. It does not redefine them.

## Canonical contract first

Before using any suite mapping in this guide, confirm the canonical Testing packet still defines:

- the meanings of `TAX-0` through `TAX-5`,
- the universal visual-or-video evidence rule,
- the anti-duplication/reference policy,
- and the blocker list that still prevents compliant execution.

Current suite names and pane lanes are support surfaces. They are **not** the taxonomy itself.

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
5. Make sure the changed scenario still maps to a canonical taxonomy ID and an evidence record.

Common commands:

```bash
./.venv/bin/python scripts/testing/run_test_suite.py --list
./.venv/bin/python scripts/testing/run_test_suite.py --suite browser --mode all-together --format table
./.venv/bin/python scripts/testing/run_test_suite.py --suite pane-match --mode all-together --format table
./.venv/bin/python scripts/testing/run_test_suite.py --suite pane-performance --mode all-together --format table
./.venv/bin/python scripts/testing/run_test_suite.py --suite pane-settings --mode all-together --format table
./.venv/bin/python scripts/testing/run_test_suite.py --suite pane-metrics --mode all-together --format table
./.venv/bin/python -m pytest tests/browser/test_browser_static_ui.py
./.venv/bin/python -m pytest tests/analysis/test_analysis.py
```

## Taxonomy alignment at a glance

Use the canonical definitions in `../project/development/Testing/spec.md`; this table only explains how the current suite layout supports them today.

| Current enforcement surface | Canonical taxonomy support | Important limitation |
| --- | --- | --- |
| Core suites such as `analysis`, `browser`, `export`, `persistence`, `presentation`, `scoring`, `scripts` | Mixed support across `TAX-0` through `TAX-5` depending on the scenario | Suite names are not 1:1 with taxonomy classes yet; `browser` now also carries `support_surface_ids` for the current Stage tool support slice |
| `pane-project`, `pane-match`, `pane-performance`, `pane-settings`, `pane-metrics` | Primary support lanes for `TAX-1`, with contributing scenarios for `TAX-0`, `TAX-2`, and `TAX-5` | Pane lanes remain support runners; the implemented Project/Match/Performance/Settings/Metrics closure inventories now live in `../../scripts/testing/pane_feature_manifests.json` |
| Browser QA docs in `docs/project/` | Control inventory, pane/view support mapping, and browser-slice full-flow planning | They must reference the canonical taxonomy and evidence rules instead of redefining them |
| Proof-seam metadata in `docs/project/browser-proof-seams.json` | Supporting seam strength descriptors | Seam labels never close a taxonomy class on their own |

## Current pane manifest foundation

`../../scripts/testing/pane_feature_manifests.json` is the current machine-readable pane inventory support surface for `TAX-0`/`TAX-1`. Project/Match/Performance remain the proven Wave A base, Settings/Metrics extend that same pane model, and the same file now carries support-only Stage tool rows for Compose, Score, Splits / waveform, Markers / Review / Overlay, Export, and ShotML without claiming evidence closure on its own.

| Pane | Pane ID | `TAX-1` record | `TAX-0` feature IDs | Current runner surfaces |
| --- | --- | --- | --- | --- |
| Project | `pane.project` | `tax1.project.pane` | `project.lifecycle`, `project.practiscore_import`, `project.primary_video_import` | `pane-project`, `browser` |
| Match | `pane.match` | `tax1.match.pane` | `match.workspace_lifecycle`, `match.setup_once_and_defaults`, `match.stage_navigation_shell`, `match.composite_editor`, `match.recap`, `match.batch_export`, `match.settings` | `pane-match`, `browser` |
| Performance | `pane.performance` | `tax1.performance.pane` | `performance.overview`, `performance.records_filtering`, `performance.record_detail_actions`, `performance.analytics`, `performance.backup_and_export`, `performance.settings` | `pane-performance`, `browser` |
| Settings | `pane.settings` | `tax1.settings.pane` | `settings.global_template_scope`, `settings.layout_defaults`, `settings.scoring_and_compose_defaults`, `settings.overlay_and_marker_defaults`, `settings.export_and_shotml_defaults`, `settings.section_visibility` | `pane-settings`, `browser` |
| Metrics | `pane.metrics` | `tax1.metrics.pane` | `metrics.summary_and_workbench`, `metrics.row_propagation`, `metrics.stage_story`, `metrics.scoring_context`, `metrics.export` | `pane-metrics`, `browser` |

Zero-control manifest features are explicit, not fuzzy blanks. `scripts/testing/pane_feature_manifests.json` now marks `performance.overview`, `performance.analytics`, `settings.section_visibility`, `metrics.row_propagation`, `metrics.stage_story`, and `metrics.scoring_context` as `audit_model: state-led`, which means they are audited through required state/result assertions rather than pane-owned `control_ids`. `match.recap` is `audit_model: control-led`: the recap surface exposes explicit controls such as `recap-select-all`, `recap-select-none`, `.recap-stage-check`, `recap-transition`, `recap-result-card`, and `recap-render`, while its stage-selection/configuration/render-status assertions remain required proof support.

## Current stage support surface extension

These rows stay support-only. They help the browser-owned Stage tool families contribute honest `TAX-0` support without pretending the repo now has first-class `TAX-2` view lanes.

| Surface | Support surface ID | Support role | `TAX-0` feature IDs | Current runner surfaces |
| --- | --- | --- | --- | --- |
| Compose | `surface.stage.compose` | Stage-tool support surface only; not a first-class pane or view closure record. | `stage.compose.defaults_and_media`, `stage.compose.per_source_authoring`, `stage.compose.secondary_waveform_sync` | `browser` |
| Score | `surface.stage.scoring` | Stage-tool support surface only; not a first-class pane or view closure record. | `stage.scoring.enablement_and_preset`, `stage.scoring.summary_and_editing` | `browser` |
| Splits / waveform | `surface.stage.splits_waveform` | Stage-tool support surface only; not a first-class pane or view closure record. | `stage.splits_waveform.summary_and_workbench`, `stage.splits_waveform.waveform_navigation`, `stage.splits_waveform.split_row_editing` | `browser` |
| Markers / Review / Overlay | `surface.stage.markers_review_overlay` | Stage-tool support surface only; not a first-class pane or view closure record. | `stage.markers_review_overlay.marker_authoring`, `stage.markers_review_overlay.review_boxes_and_visibility`, `stage.markers_review_overlay.overlay_styling_and_positioning` | `browser` |
| Export | `surface.stage.export` | Stage-tool support surface only; not a first-class pane or view closure record. | `stage.export.render_settings`, `stage.export.output_profiles_and_hooks`, `stage.export.log_and_artifact_output` | `browser` |
| ShotML | `surface.stage.shotml` | Stage-tool support surface only; not a first-class pane or view closure record. | `stage.shotml.threshold_and_defaults`, `stage.shotml.detector_settings`, `stage.shotml.proposals_and_section_persistence` | `browser` |

The `browser` suite now exposes these rows through `support_surface_ids` in `../../scripts/testing/test_suite_taxonomy.json`. That keeps the current runner honest about ownership while the repo still lacks dedicated Stage tool lanes and first-class view manifests.

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

They support `TAX-1` pane work, but they do not replace the canonical pane manifests or the evidence contract.

The current Stage tool support slice remains browser-suite owned. There are no dedicated Compose/Score/Splits-Review/Export/ShotML lanes yet; those surfaces are tracked as support-only rows in `../../scripts/testing/pane_feature_manifests.json` and `../../scripts/testing/test_suite_taxonomy.json`.

| Suite | Owns | Current target shape |
| --- | --- | --- |
| `pane-project` | Landing bootstrap, Project pane, and PractiScore browser workflows | Project contract files plus selected Project interaction node IDs, with explicit landing support exceptions recorded in `../../scripts/testing/test_suite_taxonomy.json` |
| `pane-match` | Match workspace lifecycle, setup-once, recap, composite, batch export, and settings-return flows | `test_workspace_flows.py`, `test_workspace_export_and_recap.py`, plus selected Match interaction node IDs |
| `pane-performance` | Performance Library reopen, search/filter, detail, notes/tags, settings, and route-contract flows | `test_library_backend_contracts.py` plus selected Performance interaction node IDs |
| `pane-settings` | Settings section workflows and defaults truth gates | `test_settings_e2e.py` and `test_settings_defaults_truth_gate.py` |
| `pane-metrics` | Metrics export/workbench flows and scoring-metrics contracts | `test_metrics_e2e.py` and `test_scoring_metrics_contracts.py` |

`pane-project` now uses an explicit `support_target_exceptions` model for landing-only bootstrap targets. That keeps the lane honest about cross-surface support without pretending the landing surface is itself `pane.project`.

Use these lanes when you need a pane-scoped browser run without paying for the full `browser` suite.

For Project, Match, Performance, Settings, and Metrics, the runner/taxonomy mirror in `../../scripts/testing/test_suite_taxonomy.json` records the corresponding `pane_ids` and `pane_manifest_refs` so the suite catalog can point back to the current manifest file.

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

### Settings and Metrics pane lanes

- [../../tests/browser/test_settings_e2e.py](../../tests/browser/test_settings_e2e.py)
- [../../tests/browser/test_settings_defaults_truth_gate.py](../../tests/browser/test_settings_defaults_truth_gate.py)
- [../../tests/browser/test_metrics_e2e.py](../../tests/browser/test_metrics_e2e.py)
- [../../tests/browser/test_scoring_metrics_contracts.py](../../tests/browser/test_scoring_metrics_contracts.py)

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

If the change affects taxonomy mapping or evidence expectations, update the canonical Testing docs first and then bring this guide and the browser QA docs back into alignment.

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
- Remember that every class still needs visual or video evidence; browser interactivity alone is not enough without an accepted artifact reference.

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
