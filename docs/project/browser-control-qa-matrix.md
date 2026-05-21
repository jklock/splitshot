# Browser Control QA Matrix

This matrix maps every SplitShot control surface to the test files that exercise it.

It is not a claim that every button or field has its own direct behavior test. Some controls are verified through multi-step interaction tests, contract tests, or static layout checks.

If a control is missing from this matrix, it does not have an explicit owner yet.

## Coverage Mapping

| Surface | Coverage Description |
| --- | --- |
| Shared shell | tool-rail collapse/minimize, surface switcher tab selection, context header display, return-to-workspace visibility, resize handles, layout lock toggle |
| Project / import | project details, create/select project, project-folder display, gated PractiScore dashboard opener, gated manual PractiScore file import, gated primary import, metadata-only delete |
| PiP | add media, PiP default settings collapse and restore, per-item card toggle/remove, per-item size/opacity/position/sync controls, visible beep-sync analyze/rerun action, first-video secondary sync-analysis status/rerun, shared-lane secondary waveform visibility, GIF PiP media typing |
| Score | scoring pane enable/disable, preset selection, scoring summary display, PractiScore context import, scoring table render, scoring-specific row edit behavior |
| Splits / waveform | split pane summary, enable splits toggle, Edit, timing-event controls, waveform expand/zoom/amplitude, waveform pan |
| Markers / Review / Overlay | compact marker enable toggle, compact Edit or Collapse launcher, compact Add Time Marker action, compact marker list, edit-mode-only selected-marker editor, selected-marker Enable Motion checkbox, guided Start/Finish/Auto/Detail rows, Generate/Add Detail/Previous/Next/Remove Detail/Clear path actions, workbench add/import/filter/navigation controls, settings marker defaults plus marker default motion checkbox, workbench marker list, bubble enabled, editor duplicate/remove actions, show overlay checkbox, review show-box selectors for markers/PiP/timer/draw/splits/score, badge size/style/custom font sizing, shared curated font list, stack gap, edge padding, timer/draw/score position inputs and lock-to-stack controls, bubble size override, font size, bold/italic controls, score colors, marker bubble shape or typography controls, review text-box background/text color and opacity, review text-box typography controls, text boxes, popup editor, text-box drag |
| Settings | scope, landing pane, reopen-last-tool, section save current/reset default actions, layout defaults, PiP defaults, overlay defaults, marker defaults, export defaults, ShotML defaults, section collapse, template fields |
| Metrics | metrics pane summary grid, expand to workbench, stage story graphs, trend table, scoring context display, timing-event metrics ordering, metrics pane row propagation, CSV/Text export buttons |
| Export | output path, preset, quality, show export log modal open/close/backdrop and download, CI Clip1 MP4 proof export |
| ShotML | average auto-confidence summary, threshold apply/reset, rerun, proposal generation, reset defaults |

## Test Files

The following test files provide coverage for the controls listed above:

- `tests/browser/test_browser_static_ui.py`
- `tests/browser/test_browser_control.py`
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
- dashboard-open action parity with manual file import
- missing-folder creation notice on new project
- metadata-only delete safety confirmation
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
- review show-box selectors for markers/PiP/timer/draw/splits/score
- review text-box background/text color and opacity
- review text-box background/text/opacity preview
- review show-box selector state
- review source-switch after-final render
- review custom placement or size
- stack lock behavior
- review text-box creation and drag
- average auto-confidence summary
- metrics pane row propagation
- timing-event metrics ordering
- section collapse state within a live session
- layout capture/release defaults
- visible analyze or re-run beep-sync action
- CI artifact export proof from `docs/Clip1.MP4`
