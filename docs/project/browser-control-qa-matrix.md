# Browser Control QA Matrix

This matrix maps every SplitShot control surface to the test files that exercise it.

It is not a claim that every button or field has its own direct behavior test. Some controls are verified through multi-step interaction tests, contract tests, or static layout checks.

If a control is missing from this matrix, it does not have an explicit owner yet.

Coverage ownership in this matrix is **not** a proof-taxonomy class. Inventory presence, surface ownership, or companion-plan status does **not** by itself establish meaningful closure; some entries are still compat/static or `RUNTIME_EPHEMERAL` guardrails unless the underlying workflow mutates durable truth or yields an output artifact.

## Coverage Mapping

| Surface | Coverage Description |
| --- | --- |
| Shared shell | shared `stage-workspace` shell markers across Stage/Match/Performance, tool-rail collapse/minimize, surface switcher tab selection, context header display, return-to-workspace visibility, resize handles, layout lock toggle |
| Project / import | project details, create/select project, project-folder display, gated PractiScore dashboard opener, gated manual PractiScore file import, gated primary import, metadata-only delete |
| Match workspace | shared-shell main/lower/right Match layout, media-backed stage tiles, workspace create/open/save/add-stage/remove-stage plus loading/error states, stage card selection/open/return, setup-once preview/apply/dismiss flow, selected-stage lower-pane truth stays pinned while Composite/Export swap beneath it, shared defaults apply/reset, stage overrides apply/reset, stage clip add plus composite reorder/per-clip role-sync-audio editing/plan refresh/apply-clear cut overrides, recap stage selection plus transition/result-card configuration and render outcomes, batch export recipe selection/select all/none/start, Match settings local persistence |
| Performance Library | shared-shell main/lower/right Performance layout, loading/empty/stale state affordances, overview summary tiles, records search/sort/filter plus personal-best list, selected-record lower-pane detail, Open Stage/Open Workspace, notes/tags persistence entry points, analytics truth messaging, backup create/restore, CSV/JSON export, Performance settings local persistence |
| Compose | add media, Composition Defaults collapse and restore, side-by-side/above-below/picture-in-picture/full-screen-portrait/dual-HUD layout selection, reusable Trim Dead Time run-window editor, per-item card toggle/remove, per-item angle-role selection, per-item layer size/opacity/position/sync controls, visible beep-sync analyze/rerun action, first-video secondary sync-analysis status/rerun, shared-lane secondary waveform visibility, GIF added-media typing |
| Score | scoring pane enable/disable, preset selection, scoring summary display, PractiScore context import, scoring table render, scoring-specific row edit behavior |
| Splits / waveform | split pane summary, enable splits toggle, Edit, timing-event controls, waveform expand/zoom/amplitude, waveform pan |
| Markers / Review / Overlay | compact marker enable toggle, compact Edit or Collapse launcher, compact Add Time Marker action, compact marker list, edit-mode-only selected-marker editor, selected-marker Enable Motion checkbox, guided Start/Finish/Auto/Detail rows, Generate/Add Detail/Previous/Next/Remove Detail/Clear path actions, workbench add/import/filter/navigation controls, settings marker defaults plus marker default motion checkbox, workbench marker list, bubble enabled, editor duplicate/remove actions, show overlay checkbox, review show-box selectors for markers/added media/timer/draw/splits/score, review-source picker, badge size/style/custom font sizing, shared curated font list, stack gap, edge padding, timer/draw/score position inputs and lock-to-stack controls, bubble size override, font size, bold/italic controls, score colors, Export Badges output-profile handoff, marker bubble shape or typography controls, review text-box background/text color and opacity, review text-box typography controls, text boxes, popup editor, text-box drag |
| Settings | scope, landing pane, reopen-last-tool, section save current/reset default actions, layout defaults, Compose defaults, overlay defaults, marker defaults, export defaults, ShotML defaults, section collapse, template fields |
| Metrics | metrics pane summary grid, expand to workbench, stage story graphs, trend table, scoring context display, timing-event metrics ordering, metrics pane row propagation, CSV/Text export buttons |
| Export | output path, preset, quality, output-profile list/create/select/delete, framing/title/logo output-hook save/close controls, show export log modal open/close/backdrop and download, CI Clip1 MP4 proof export |
| ShotML | average auto-confidence summary, threshold apply/reset, rerun, proposal generation, reset defaults |

## Test Files

The following test files provide coverage for the controls listed above:

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

## Interaction Test Coverage Detail

The interaction suite (`tests/browser/test_browser_interactions.py`) verifies:

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
- metrics pane row propagation
- timing-event metrics ordering
- section collapse state within a live session
- layout capture/release defaults
- visible analyze or re-run beep-sync action
- CI artifact export proof from `docs/Clip1.MP4`
- `DEV-106.landing_recent` — backend-route/static render plus recent-row interaction proof for `/api/landing/recent`; row clicks intentionally switch surfaces without auto-opening a saved project or workspace
- `DEV-107.root_shell_compat` — compat/static shell contract plus workflow guardrails for Match open/return, setup-once, and pinned lower-pane truth, plus the retained host open-project and Performance-library rerender/selected-record consumers
- `project.practiscore_bridge` — manual `Select PractiScore File` fallback and local `Match type` / `Stage #` / `Competitor name` / `Place` selectors remain proof-bearing; remote session/match-list/import coverage is a browser-state bridge rather than proof of every downstream consumer
