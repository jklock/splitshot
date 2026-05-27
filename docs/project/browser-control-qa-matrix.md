# Browser Control QA Matrix

This matrix maps SplitShot’s browser-visible control surfaces to the tests that exercise them and to the canonical taxonomy IDs they support.

The canonical definitions live in `development/Testing/spec.md`. The canonical evidence contract lives in `development/Testing/artifacts.md`.

This matrix is a browser inventory and support map. It is **not** a closure ledger.

- Inventory presence does not close a taxonomy class.
- A support seam or compat label does not close a taxonomy class.
- Every row here must ultimately resolve to accepted visual or video evidence through the canonical Testing contract.

If a control is missing from this matrix, it does not have an explicit browser-QA owner yet.

## Coverage mapping

| Surface | Taxonomy support | Coverage description |
| --- | --- | --- |
| Shared shell | Supports `TAX-0`, `TAX-1`, and `TAX-2`; contributes to `TAX-5` | Shared `stage-workspace` shell markers across Stage/Match/Performance, tool-rail collapse/minimize, surface switcher tab selection, context header display, return-to-workspace visibility, resize handles, layout lock toggle |
| Project / import | Supports `TAX-0` and `TAX-1`; contributes to `TAX-5` | Project details, create/select project, project-folder display, gated PractiScore dashboard opener, manual `Select PractiScore File` fallback, local `Match type` / `Stage #` / `Competitor name` / `Place` selectors, remote PractiScore session and sync state rendering, gated primary import, metadata-only delete |
| Match workspace | Supports `TAX-0` and `TAX-1`; contributes to `TAX-5` | Shared-shell main/lower/right Match layout, media-backed stage tiles, workspace create/open/save/add-stage/remove-stage plus loading/error states, stage card selection/open/return, setup-once preview/apply/dismiss flow, selected-stage lower-pane truth stays pinned while Composite/Export swap beneath it, shared defaults apply/reset, stage overrides apply/reset, stage clip add plus composite reorder/per-clip role-sync-audio editing/plan refresh/apply-clear cut overrides, recap stage selection plus transition/result-card configuration and render outcomes, batch export recipe selection/select all/none/start, Match settings local persistence |
| Performance Library | Supports `TAX-0` and `TAX-1`; contributes to `TAX-5` | Shared-shell main/lower/right Performance layout, loading/empty/stale state affordances, overview summary tiles, records search/sort/filter plus personal-best list, selected-record lower-pane detail, Open Stage/Open Workspace, notes/tags persistence entry points, analytics truth messaging, backup create/restore, CSV/JSON export, Performance settings local persistence |
| Compose | Supports `TAX-0`; contributes to `TAX-1`, `TAX-2`, and `TAX-5` | Add media, Composition Defaults collapse and restore, side-by-side/above-below/picture-in-picture/full-screen-portrait/dual-HUD layout selection, reusable Trim Dead Time run-window editor, per-item card toggle/remove, per-item angle-role selection, per-item layer size/opacity/position/sync controls, visible beep-sync analyze/rerun action, first-video secondary sync-analysis status/rerun, shared-lane secondary waveform visibility, GIF added-media typing |
| Score | Supports `TAX-0`; contributes to `TAX-1` and `TAX-5` | Scoring pane enable/disable, preset selection, scoring summary display, PractiScore context import, scoring table render, scoring-specific row edit behavior |
| Splits / waveform | Supports `TAX-0`; contributes to `TAX-1` and `TAX-2` | Split pane summary, enable splits toggle, Edit, timing-event controls, waveform expand/zoom/amplitude, waveform pan |
| Markers / Review / Overlay | Supports `TAX-0`; contributes to `TAX-1`, `TAX-2`, and `TAX-5` | Compact marker enable toggle, compact Edit or Collapse launcher, compact Add Time Marker action, compact marker list, edit-mode-only selected-marker editor, selected-marker Enable Motion checkbox, guided Start/Finish/Auto/Detail rows, Generate/Add Detail/Previous/Next/Remove Detail/Clear path actions, workbench add/import/filter/navigation controls, settings marker defaults plus marker default motion checkbox, workbench marker list, bubble enabled, editor duplicate/remove actions, show overlay checkbox, review show-box selectors for markers/added media/timer/draw/splits/score, review-source picker, badge size/style/custom font sizing, shared curated font list, stack gap, edge padding, timer/draw/score position inputs and lock-to-stack controls, bubble size override, font size, bold/italic controls, score colors, Export Badges output-profile handoff, marker bubble shape or typography controls, review text-box background/text color and opacity, review text-box typography controls, text boxes, popup editor, text-box drag |
| Settings | Supports `TAX-0` and `TAX-1` | Scope, landing pane, reopen-last-tool, section save current/reset default actions, layout defaults, Compose defaults, overlay defaults, marker defaults, export defaults, ShotML defaults, section collapse, template fields |
| Metrics | Supports `TAX-0` and `TAX-1`; contributes to `TAX-5` | Metrics pane summary grid, expand/collapse workbench, stage story graphs, trend table, scoring context display, timing-event metrics ordering, metrics pane row propagation, CSV/Text export buttons |
| Export | Supports `TAX-0` and `TAX-1`; contributes to `TAX-5` | Output path, preset, quality, output-profile list/create/select/delete, framing/title/logo output-hook save/close controls, show export log modal open/close/backdrop and download, CI Clip1 MP4 proof export |
| ShotML | Supports `TAX-0` and `TAX-1` | Average auto-confidence summary, threshold apply/reset, rerun, proposal generation, reset defaults |

## Pane manifest references

The current `TAX-0`/`TAX-1` Wave A pane manifest foundation lives in `scripts/testing/pane_feature_manifests.json`.

| Surface | Pane ID | `TAX-1` record | `TAX-0` feature IDs | Current runner support |
| --- | --- | --- | --- | --- |
| Project / import | `pane.project` | `tax1.project.pane` | `project.lifecycle`, `project.practiscore_import`, `project.primary_video_import` | `pane-project`, `browser` |
| Match workspace | `pane.match` | `tax1.match.pane` | `match.workspace_lifecycle`, `match.setup_once_and_defaults`, `match.stage_navigation_shell`, `match.composite_editor`, `match.recap`, `match.batch_export`, `match.settings` | `pane-match`, `browser` |
| Performance Library | `pane.performance` | `tax1.performance.pane` | `performance.overview`, `performance.records_filtering`, `performance.record_detail_actions`, `performance.analytics`, `performance.backup_and_export`, `performance.settings` | `pane-performance`, `browser` |
| Settings | `pane.settings` | `tax1.settings.pane` | `settings.global_template_scope`, `settings.layout_defaults`, `settings.scoring_and_compose_defaults`, `settings.overlay_and_marker_defaults`, `settings.export_and_shotml_defaults`, `settings.section_visibility` | `pane-settings`, `browser` |
| Metrics | `pane.metrics` | `tax1.metrics.pane` | `metrics.summary_and_workbench`, `metrics.row_propagation`, `metrics.stage_story`, `metrics.scoring_context`, `metrics.export` | `pane-metrics`, `browser` |

These manifest rows are pane-owned only. Landing bootstrap targets that currently support the `pane-project` lane live as explicit `support_target_exceptions` in `scripts/testing/test_suite_taxonomy.json`; they do not become `pane.project` feature rows.

The current manifest also declares explicit `state-led` zero-control features in `scripts/testing/pane_feature_manifests.json`: `performance.overview`, `performance.analytics`, `settings.section_visibility`, `metrics.row_propagation`, `metrics.stage_story`, and `metrics.scoring_context`. `match.recap` is `control-led`: the recap section exposes explicit controls such as `recap-select-all`, `recap-select-none`, `.recap-stage-check`, `recap-transition`, `recap-result-card`, and `recap-render`, while its stage-selection/configuration/render-status assertions remain required.

## Stage support surface manifests

These rows stay support-only. They map the current Stage tool families to live `TAX-0` feature IDs without pretending the repo now has first-class view lanes.

| Surface | Support surface ID | Support role | `TAX-0` feature IDs | Current runner support |
| --- | --- | --- | --- | --- |
| Compose | `surface.stage.compose` | Stage-tool support surface only; not a first-class pane or view closure record. | `stage.compose.defaults_and_media`, `stage.compose.per_source_authoring`, `stage.compose.secondary_waveform_sync` | `browser` |
| Score | `surface.stage.scoring` | Stage-tool support surface only; not a first-class pane or view closure record. | `stage.scoring.enablement_and_preset`, `stage.scoring.summary_and_editing` | `browser` |
| Splits / waveform | `surface.stage.splits_waveform` | Stage-tool support surface only; not a first-class pane or view closure record. | `stage.splits_waveform.summary_and_workbench`, `stage.splits_waveform.waveform_navigation`, `stage.splits_waveform.split_row_editing` | `browser` |
| Markers / Review / Overlay | `surface.stage.markers_review_overlay` | Stage-tool support surface only; not a first-class pane or view closure record. | `stage.markers_review_overlay.marker_authoring`, `stage.markers_review_overlay.review_boxes_and_visibility`, `stage.markers_review_overlay.overlay_styling_and_positioning` | `browser` |
| Export | `surface.stage.export` | Stage-tool support surface only; not a first-class pane or view closure record. | `stage.export.render_settings`, `stage.export.output_profiles_and_hooks`, `stage.export.log_and_artifact_output` | `browser` |
| ShotML | `surface.stage.shotml` | Stage-tool support surface only; not a first-class pane or view closure record. | `stage.shotml.threshold_and_defaults`, `stage.shotml.detector_settings`, `stage.shotml.proposals_and_section_persistence` | `browser` |

The `browser` suite now carries these support rows through `support_surface_ids` in `scripts/testing/test_suite_taxonomy.json`.

## Current blocker note

Any control family that is backed only by inventory presence, static coverage, compat wiring, or a supporting proof seam remains a blocker against taxonomy closure until the canonical evidence record is accepted.

## Test files

The following test files provide browser-side support for the controls listed above:

- `tests/browser/test_browser_static_ui.py`
- `tests/browser/test_browser_control.py`
- `tests/browser/test_landing_backend_routes.py`
- `tests/browser/test_library_backend_contracts.py`
- `tests/browser/test_browser_control_inventory_audit.py`
- `tests/browser/test_browser_control_coverage_matrix.py`
- `tests/browser/test_browser_interactions.py`
- `tests/browser/test_metrics_e2e.py`
- `tests/browser/test_settings_defaults_truth_gate.py`
- `tests/browser/test_settings_e2e.py`
- `tests/browser/test_scoring_metrics_contracts.py`
- `tests/browser/test_project_lifecycle_contracts.py`
- `tests/browser/test_timing_waveform_contracts.py`
- `tests/browser/test_merge_export_contracts.py`
- `tests/browser/test_overlay_review_contracts.py`
- `tests/export/test_export.py`
- `tests/analysis/test_analysis.py`

## Interaction test coverage detail

The interaction suite (`tests/browser/test_browser_interactions.py`) contributes browser evidence support for:

- dashboard-open action
- manual file import parity
- PractiScore session-start browser-state bridge
- PractiScore remote match-list and selected-match import browser-state bridge
- PractiScore expired-session browser-state bridge
- dashboard-open action parity with manual file import
- missing-folder creation notice on new project
- metadata-only delete safety confirmation and cancel path
- project-pane keyboard tab order through primary controls
- output-profile create/select plus Compose Trim Dead Time, Overlay Export Badges, and Export framing/title/logo output-hook save/close flows
- Match workspace new/open/save lifecycle plus stage add/select/remove and loading/error states
- Match workspace stage open and shell return-to-Match behavior
- Match workspace live preview tiles and selected-stage lower-pane truth across Composite/Export lower-pane swaps
- Match shared defaults apply/reset, stage override apply/reset, and selected-stage lower-pane / workflow-inspector routing
- setup-once preview/apply confirmation and dismiss
- Match Stage Composite reorder, per-clip role/sync/audio editing, plan refresh, and apply/clear cut override actions plus refreshed state
- Match recap stage selection plus transition/result-card configuration and success/error status
- Match batch export recipe selection, queue select all/none, and truthful success/error reporting
- Match settings local persistence and remember-stage behavior
- Performance Library selected-record reopen to Stage and Match workspace plus search-filter / lower-detail shell truth
- Performance Library settings local persistence, stale banner, and manual refresh load behavior
- waveform expand/zoom/amplitude and drag movement
- workbench import-selected-shot seek behavior
- Enable Motion checkbox state transitions
- guided step workflow state in motion editor
- selected-marker panel visible only in edit mode
- workbench list select and seek
- workbench open/close flow
- bubble enabled live-badge toggle
- selected-editor duplicate or remove rerender
- workbench editor continuity across select
- timer badge background color-picker live preview and close-commit
- marker template defaults for fresh shot-linked markers
- workbench marker navigation (prev/next)
- overlay visibility and badge toggles
- timer/draw/score badge position inputs and lock-to-stack controls
- overlay bubble size override
- overlay custom badge sizing
- font size, bold/italic controls
- export log modal open/close/backdrop and download
- review show-box selectors for markers/added media/timer/draw/splits/score
- review text-box background/text color and opacity
- review text-box background/text/opacity preview
- review show-box selector state
- review source-switch after-final render
- review custom placement or size
- stack lock behavior
- review text-box creation and drag
- per-item composition angle-role selection and saved source-management state
- average auto-confidence summary
- visible analyze or re-run beep-sync action
- CI artifact export proof from `docs/Clip1.MP4`
- `DEV-106.landing_recent` — backend-route/static render plus recent-row interaction proof for `/api/landing/recent`; row clicks intentionally switch surfaces without auto-opening a saved project or workspace
- `DEV-107.root_shell_compat` — compat/static shell contract plus workflow guardrails for Match open/return, setup-once, and pinned lower-pane truth, plus the retained host open-project and Performance-library rerender/selected-record consumers
- `project.practiscore_bridge` — manual `Select PractiScore File` fallback and local `Match type` / `Stage #` / `Competitor name` / `Place` selectors remain proof-bearing; remote session/match-list/import coverage is a browser-state bridge that supports Project-pane taxonomy mapping but does not close every downstream consumer path by itself

The Settings pane suites (`tests/browser/test_settings_e2e.py` and `tests/browser/test_settings_defaults_truth_gate.py`) contribute browser evidence support for:

- settings defaults seeding overlay/marker/export/pip/shotml state into fresh projects
- settings save-current and section-reset actions for scoring, pip, overlay, markers, export, and ShotML defaults
- landing pane and reopen-last-tool defaults across reload and project switching
- app-vs-folder settings scope separation without cross-scope rewrites
- section collapse state within a live session
- layout capture/release defaults; rendered layout field values remain state assertions rather than live interaction owners

The Metrics pane suites (`tests/browser/test_metrics_e2e.py` and `tests/browser/test_scoring_metrics_contracts.py`) contribute browser evidence support for:

- metrics pane row propagation
- timing-event metrics ordering
- metrics workbench expand/collapse shell state
- metrics stage story graphs and scoring-context truth
- metrics CSV/Text export downloads for the current context
