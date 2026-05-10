# Browser Control QA Matrix

Audited against `src/splitshot/browser/static/index.html` and the current browser suites on 2026-05-02.

This matrix names the current browser surfaces, the control families each surface owns, and the suites that currently make those claims explicit.

It is not a claim that every button or field has its own direct behavior test.
If a control is missing from this matrix, it does not have an explicit owner yet.

Use [browser-control-coverage-plan.md](browser-control-coverage-plan.md) for the exhaustive identifier inventory and [browser-full-e2e-qa-plan.md](browser-full-e2e-qa-plan.md) for the stricter phased truth-gate definition of full-app end-to-end completion.

| Surface | Control families | Primary suites | Current explicit ownership |
| --- | --- | --- | --- |
| Shared shell | rail routing, status bar lock, rail/sidebar/waveform resize handles, color picker shell, modal chrome | `tests/browser/test_browser_static_ui.py`; `tests/browser/test_browser_rail_layout.py`; `tests/browser/test_browser_interactions.py`; `tests/browser/test_browser_full_app_e2e.py` | tool-route visibility, layout drag persistence, resize-handle availability, shared modal shell, and broad shell rerender continuity |
| Project / import | project details, create/select project, project-folder display, gated PractiScore dashboard opener, gated manual PractiScore file import, gated primary import, metadata-only delete | `tests/browser/test_browser_control.py`; `tests/browser/test_project_lifecycle_contracts.py`; `tests/browser/test_browser_interactions.py`; `tests/browser/test_practiscore_session_api.py`; `tests/browser/test_practiscore_sync_controller.py`; `tests/browser/test_browser_full_app_e2e.py` | dashboard-open action, manual file import parity, missing-folder creation notice, metadata-only delete safety, PractiScore session/sync parity, project-owned PractiScore summary rendering, and save/reload truth-gate persistence |
| PiP | add media, PiP default settings collapse and restore, per-item card toggle/remove, per-item size/opacity/position/sync controls | `tests/browser/test_merge_export_contracts.py`; `tests/browser/test_browser_remaining_controls_e2e.py`; `tests/browser/test_browser_full_app_e2e.py`; `tests/export/test_export.py` | merge-source add/remove, per-card sync-offset buttons, per-item card expansion, default PiP collapse/restore, and merge/export payload parity |
| Score | enable scoring toggle, preset selection, imported score reference summary, expanded scoring workbench rows, restore flow | `tests/browser/test_scoring_metrics_contracts.py`; `tests/browser/test_metrics_e2e.py`; `tests/browser/test_browser_remaining_controls_e2e.py`; `tests/browser/test_browser_full_app_e2e.py` | preset-driven score rows, sport-aware imported score and penalty reference, scoring workbench open/close flow, score restore path, and metrics handoff after edits |
| Splits / waveform | split pane summary, enable splits toggle, Edit, timing-event controls, waveform expand/zoom/amplitude, waveform pan | `tests/browser/test_timing_waveform_contracts.py`; `tests/browser/test_browser_interactions.py`; `tests/browser/test_browser_remaining_controls_e2e.py`; `tests/browser/test_metrics_e2e.py`; `tests/browser/test_browser_full_app_e2e.py` | waveform expand/zoom/amplitude, drag movement, timing-event add/delete, timing workbench lock/edit/delete/restore, and selected-shot nudge propagation |
| Markers / Review / Overlay | compact marker enable toggle, compact Edit or Collapse launcher, compact Add Time Marker action, compact marker list, edit-mode-only selected-marker editor, selected-marker Enable Motion checkbox, guided Start/Finish/Auto/Detail rows, Generate/Add Detail/Previous/Next/Remove Detail/Clear path actions, workbench add/import/filter/navigation controls, settings marker defaults plus marker default motion checkbox, workbench marker list, bubble enabled, editor duplicate/remove actions, show overlay checkbox, review show-box selectors for markers/PiP/timer/draw/splits/score, badge size/style/custom font sizing, stack gap, edge padding, timer/draw/score position inputs and lock-to-stack controls, bubble size override, font size, bold/italic controls, score colors, review text-box background/text color and opacity, text boxes, popup editor, text-box drag | `tests/browser/test_overlay_review_contracts.py`; `tests/browser/test_browser_interactions.py`; `tests/browser/test_browser_remaining_controls_e2e.py`; `tests/browser/test_browser_full_app_e2e.py`; `tests/export/test_export.py` | workbench import-selected-shot seek, Enable Motion checkbox state, guided step workflow state, selected-marker panel visible only in edit mode, workbench list select and seek, workbench open/close flow, bubble enabled live-badge toggle, selected-editor duplicate or remove rerender, workbench editor continuity, timer badge background color-picker live preview and close-commit, marker template defaults for fresh shot-linked markers, workbench marker navigation, overlay visibility and badge toggles, timer/draw/score badge position inputs and lock-to-stack controls, overlay bubble size override, overlay custom badge sizing, font size, bold/italic controls, review show-box selector state, review source-switch after-final render, review custom placement or size, stack lock behavior, review text-box background/text/opacity preview, and review text-box creation and drag |
| Settings | scope, landing pane, reopen-last-tool, section save current/reset default actions, layout defaults, PiP defaults, overlay defaults, marker defaults, export defaults, ShotML defaults, section collapse, template fields | `tests/browser/test_settings_e2e.py`; `tests/browser/test_settings_defaults_truth_gate.py`; `tests/browser/test_browser_full_app_e2e.py`; `tests/browser/test_browser_control.py` | import-current/reset-defaults round trips, section-targeted reset semantics, layout capture/release defaults, PiP media-default seeding, export/overlay/PiP default propagation, and new-project seeding truth gates |
| Metrics | summary cards, workbench expand/collapse, graphs, CSV/TXT export, scoring/timing propagation | `tests/browser/test_metrics_e2e.py`; `tests/browser/test_scoring_metrics_contracts.py`; `tests/browser/test_browser_full_app_e2e.py` | metrics pane row propagation, timing-event metrics ordering, graph story continuity, and metrics export downloads |
| Export | output path, preset, quality, show export log modal open/close/backdrop and download | `tests/browser/test_merge_export_contracts.py`; `tests/browser/test_browser_remaining_controls_e2e.py`; `tests/browser/test_browser_full_app_e2e.py`; `tests/export/test_export.py` | export payload capture, export log modal open/close/backdrop and download, merge/export sync truth gate, and rendered-output parity |
| ShotML | average auto-confidence summary, threshold apply/reset, rerun, proposal generation, reset defaults | `tests/browser/test_browser_remaining_controls_e2e.py`; `tests/browser/test_browser_full_app_e2e.py`; `tests/analysis/test_analysis.py`; `tests/browser/test_browser_control.py` | average auto-confidence summary, threshold rerun/reset semantics, numeric control commits, proposal apply/discard, and section collapse state within a live session |

## Cross-check notes

### Project and PractiScore parity

- `tests/browser/test_project_lifecycle_contracts.py` owns the dashboard-open action, manual file import parity, missing-folder creation notice, and metadata-only delete safety.
- `tests/browser/test_browser_interactions.py` covers the live Project-pane gating for the PractiScore dashboard button and the manual `Select PractiScore File` fallback path.
- `tests/browser/test_practiscore_session_api.py` and `tests/browser/test_practiscore_sync_controller.py` keep the `practiscore_session`, `practiscore_sync`, and `practiscore_options` contract visible.

### Splits, score, and metrics propagation

- `tests/browser/test_browser_remaining_controls_e2e.py` and `tests/browser/test_timing_waveform_contracts.py` own waveform expand/zoom/amplitude, drag movement, timing workbench edits, and workbench toggle persistence.
- `tests/browser/test_metrics_e2e.py` owns metrics pane row propagation and timing-event metrics ordering after scoring or timing edits.
- `tests/browser/test_scoring_metrics_contracts.py` keeps the scoring-to-metrics data contract explicit when browser behavior rerenders.

### Markers, review, overlay, and color workflow

- `tests/browser/test_browser_interactions.py` owns workbench import-selected-shot seek, workbench list select and seek, workbench open/close flow, bubble enabled live-badge toggle, selected-editor duplicate or remove rerender, and workbench editor continuity.
- `tests/browser/test_browser_remaining_controls_e2e.py` owns Enable Motion checkbox state, guided step workflow state, timer badge background color-picker live preview and close-commit, marker template defaults for fresh shot-linked markers, workbench marker navigation, overlay custom badge sizing, overlay bubble size override, font size, bold/italic controls, review text-box background/text/opacity preview, and review custom placement or size.
- `tests/browser/test_overlay_review_contracts.py` owns selected-marker panel visible only in edit mode, review show-box selector state, review source-switch after-final render, stack lock behavior, and review text-box background/text color and opacity.
- `tests/browser/test_browser_full_app_e2e.py` and `tests/export/test_export.py` back overlay visibility and badge toggles, timer/draw/score badge position inputs and lock-to-stack controls, and cross-surface WYSIWYG parity.

## Suites referenced by this matrix

- `tests/browser/test_browser_static_ui.py`
- `tests/browser/test_browser_control.py`
- `tests/browser/test_browser_control_inventory_audit.py`
- `tests/browser/test_browser_control_coverage_matrix.py`
- `tests/browser/test_browser_interactions.py`
- `tests/browser/test_browser_remaining_controls_e2e.py`
- `tests/browser/test_browser_full_app_e2e.py`
- `tests/browser/test_metrics_e2e.py`
- `tests/browser/test_settings_defaults_truth_gate.py`
- `tests/browser/test_settings_e2e.py`
- `tests/browser/test_scoring_metrics_contracts.py`
- `tests/browser/test_project_lifecycle_contracts.py`
- `tests/browser/test_timing_waveform_contracts.py`
- `tests/browser/test_merge_export_contracts.py`
- `tests/browser/test_overlay_review_contracts.py`
- `tests/browser/test_practiscore_session_api.py`
- `tests/browser/test_practiscore_sync_controller.py`
- `tests/export/test_export.py`
- `tests/analysis/test_analysis.py`
