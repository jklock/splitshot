# Browser Full E2E QA Plan

Audited against the current browser suites on 2026-05-02.

This document defines the stricter, phase-gated standard for claiming that the browser shell has truthful end-to-end QA coverage rather than only broad smoke coverage.

`full-control QA coverage` means zero mutable controls are left at `missing`, `static`, or `smoke`.

## Coverage-state vocabulary

- `missing` — the control exists in the live browser shell, but no suite or document currently owns it.
- `static` — the control is only guarded by HTML/CSS/JS shell assertions.
- `smoke` — the control is touched by a broad route or workflow test, but the behavior is not asserted explicitly enough to serve as a truth gate.
- `truth-gated` — the control participates in an explicit interaction, route, or persisted-state assertion that would fail if the user-visible behavior drifted.

## Current phase map

| Phase | What closes out in this phase | Primary suites |
| --- | --- | --- |
| Phase 0: Lock The Truth Boundary | static shell contract, identifier inventory, QA-matrix ownership, doc guards | `tests/browser/test_browser_static_ui.py`; `tests/browser/test_browser_control_inventory_audit.py`; `tests/browser/test_browser_control_coverage_matrix.py` |
| Phase 1: Shared Shell And Drag/Layout Interactions | tool routing, rail collapse, layout lock, resize handles, waveform drag/pan shell behavior | `tests/browser/test_browser_rail_layout.py`; `tests/browser/test_browser_interactions.py`; `tests/browser/test_browser_remaining_controls_e2e.py` |
| Phase 2: Splits And Score End-To-End Closeout | timing enable/edit flow, waveform controls, scoring preset/edit/restore, metrics propagation | `tests/browser/test_timing_waveform_contracts.py`; `tests/browser/test_scoring_metrics_contracts.py`; `tests/browser/test_metrics_e2e.py`; `tests/browser/test_browser_full_app_e2e.py` |
| Phase 3: Markers, Review, Overlay, And Color Picker | marker authoring, review text boxes, overlay positioning/style, color-picker commits, WYSIWYG parity | `tests/browser/test_overlay_review_contracts.py`; `tests/browser/test_browser_interactions.py`; `tests/browser/test_browser_remaining_controls_e2e.py`; `tests/browser/test_browser_full_app_e2e.py`; `tests/export/test_export.py` |
| Phase 4: PiP, Merge, Export Settings, And Export Log | merge-source cards, PiP defaults, export payloads, export-log modal/backdrop/download | `tests/browser/test_merge_export_contracts.py`; `tests/browser/test_browser_remaining_controls_e2e.py`; `tests/browser/test_browser_full_app_e2e.py`; `tests/export/test_export.py` |
| Phase 5: Settings And ShotML Full Coverage | settings section persistence, defaults round trips, ShotML threshold/rerun/reset/proposals, numeric settings | `tests/browser/test_settings_e2e.py`; `tests/browser/test_settings_defaults_truth_gate.py`; `tests/browser/test_browser_remaining_controls_e2e.py`; `tests/browser/test_browser_full_app_e2e.py`; `tests/analysis/test_analysis.py` |
| Phase 6: Cross-Surface Final Truth Gate | saved-project, merge/export, markers/review/overlay, settings, and ShotML workflows that must survive rerender and reload together | `tests/browser/test_browser_full_app_e2e.py`; `tests/browser/test_browser_remaining_controls_e2e.py`; `tests/browser/test_metrics_e2e.py` |

## Phase 0: Lock The Truth Boundary

Before calling anything “full e2e,” the static shell and the docs that describe it must agree.

### Phase 0 suite anchors

- `tests/browser/test_browser_static_ui.py`
- `tests/browser/test_browser_control_inventory_audit.py`
- `tests/browser/test_browser_control_coverage_matrix.py`

### Phase 0 exit criteria

- The visible browser shell structure, copy, ids, and pane routing are still locked by static assertions.
- The exhaustive control inventory in `browser-control-coverage-plan.md` matches the live HTML shell.
- The summarized ownership map in `browser-control-qa-matrix.md` matches the actual suite claims.
- No later phase may claim closeout for a control family that is still undocumented here.

## Phase 1: Shared Shell And Drag/Layout Interactions

This phase closes out the shell behaviors that every pane depends on before pane-specific truth gates start stacking.

### Phase 1 suite anchors

- `tests/browser/test_browser_rail_layout.py`
- `tests/browser/test_browser_interactions.py`
- `tests/browser/test_browser_remaining_controls_e2e.py`

### Phase 1 exit criteria

- Tool routing shows the expected pane and preserves the active tool state.
- Rail collapse/expand, sidebar resize, waveform resize, and layout-lock interactions survive rerender.
- Waveform drag and pan behavior remain explicit enough that a user-visible regression would fail a test.
- Shared modal shells such as the color picker still open, close, and hand control back cleanly.

## Phase 2: Splits And Score End-To-End Closeout

This phase closes out the timing and scoring workflows that directly change rows, timings, and score results.

### Phase 2 suite anchors

- `tests/browser/test_timing_waveform_contracts.py`
- `tests/browser/test_scoring_metrics_contracts.py`
- `tests/browser/test_metrics_e2e.py`
- `tests/browser/test_browser_remaining_controls_e2e.py`
- `tests/browser/test_browser_full_app_e2e.py`

### Phase 2 exit criteria

- Split enable/disable, waveform expand/zoom/amplitude/reset, and timing-event add/remove/edit are explicit assertions, not just smoke coverage.
- Timing workbench row lock/edit/restore/delete behavior survives route changes and rerender.
- Scoring enable/preset/edit/restore flows propagate into the scoring summary and the metrics surface.
- Metrics tables and graphs react to timing/scoring edits, not just initial load.

## Phase 3: Markers, Review, Overlay, And Color Picker

This phase closes out the most intertwined authoring surfaces: markers, overlay, review text boxes, and shared color editing.

### Phase 3 suite anchors

- `tests/browser/test_overlay_review_contracts.py`
- `tests/browser/test_browser_interactions.py`
- `tests/browser/test_browser_remaining_controls_e2e.py`
- `tests/browser/test_browser_full_app_e2e.py`
- `tests/export/test_export.py`

### Phase 3 exit criteria

- Marker compact controls and workbench controls cover add/import/filter/select/navigate/edit/remove truthfully.
- Motion-path workflows, guided Start/Finish/Auto/Detail flows, and selected-marker editor visibility are explicit assertions.
- Review show-box toggles, text-box add/edit/drag/stack behavior, and imported-summary switching are explicit assertions.
- Overlay badge visibility, custom placement, lock-to-stack behavior, font controls, bubble sizing, and score colors are explicit assertions.
- Color-picker open/live-preview/close-commit behavior is covered where browser users actually invoke it.
- Export-side parity remains aligned with what the browser preview renders for overlay/review content.

## Phase 4: PiP, Merge, Export Settings, And Export Log

This phase closes out the merge-and-export branch so output settings and merge layout behavior are not left at smoke level.

### Phase 4 suite anchors

- `tests/browser/test_merge_export_contracts.py`
- `tests/browser/test_browser_remaining_controls_e2e.py`
- `tests/browser/test_browser_full_app_e2e.py`
- `tests/export/test_export.py`

### Phase 4 exit criteria

- Merge media add/remove, per-card expand/collapse, sync offsets, and per-source size/opacity/position controls are explicit assertions.
- PiP defaults collapse/restore is asserted and survives route changes.
- Export quality/frame/codec/path/two-pass settings are explicit payload assertions, not only a button-click smoke test.
- The export-log modal open/close/backdrop/download flow is explicitly asserted.
- Merge/export cross-surface truth gates survive rerender and saved-state refresh.

## Phase 5: Settings And ShotML Full Coverage

This phase closes out the default-seeding and model-control surfaces that later tasks rely on for stable project creation and detector reruns.

### Phase 5 suite anchors

- `tests/browser/test_settings_e2e.py`
- `tests/browser/test_settings_defaults_truth_gate.py`
- `tests/browser/test_browser_remaining_controls_e2e.py`
- `tests/browser/test_browser_full_app_e2e.py`
- `tests/analysis/test_analysis.py`

### Phase 5 exit criteria

- Settings section toggles persist within a live session and across tool-route changes.
- Import-current, reset-defaults, and layout capture/release behavior remain explicit browser assertions.
- Overlay, PiP, export, marker-template, and ShotML defaults seed fresh state as documented.
- ShotML threshold apply/reset, proposal generation, proposal apply/discard, and numeric-control commits are explicit assertions.
- Browser-level ShotML claims remain compatible with the analysis-side truth in `tests/analysis/test_analysis.py`.

## Phase 6: Cross-Surface Final Truth Gate

This phase is the point where the browser shell stops being a pile of good local tests and becomes a trustworthy whole-app contract.

### Phase 6 suite anchors

- `tests/browser/test_browser_full_app_e2e.py`
- `tests/browser/test_browser_remaining_controls_e2e.py`
- `tests/browser/test_metrics_e2e.py`

### Phase 6 exit criteria

- PractiScore import, timing edits, scoring edits, and project save/reload survive as one coherent workflow.
- Markers, review, overlay, merge, export, settings, and ShotML still work together after route changes and rerender.
- The final truth-gate suites assert persisted state, not just transient DOM effects.
- No surface can still be described as `missing`, `static`, or `smoke` if the project claims full browser-control end-to-end closeout.

## T02 scope note

This task restores the documents that define the phased truth boundary. It does not claim that every later phase has been rerun in this task; it restores the contract those future validation runs must satisfy.
