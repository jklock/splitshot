# Browser Control QA Matrix

Audited against `src/splitshot/browser/static/index.html`, the current browser suites, and the released `docs/v107` Phase 18 corrective closeout on `2026-07-07`.

This matrix names the current browser surfaces, the control families each surface owns, and the suites that should keep those claims explicit during the Phase 18 corrective closeout.

Use `scripts/audits/browser/pane_function_audit.py` as the code-first companion audit. It inventories pane-owned functions from `src/splitshot/browser/static/panes/`, traces browser routes into `server.py` and `controller.py`, and classifies proof strength per function.

Use [browser-control-coverage-plan.md](browser-control-coverage-plan.md) for the exhaustive identifier inventory and [browser-full-e2e-qa-plan.md](browser-full-e2e-qa-plan.md) for the stricter phased truth-gate definition of full-app end-to-end completion.

| Surface | Control families | Primary suites | Current explicit ownership |
| --- | --- | --- | --- |
| Shared shell | rail routing, status bar lock, rail/sidebar/waveform resize handles, color picker shell, modal chrome | `tests/browser/test_browser_static_ui.py`; `tests/browser/test_browser_rail_layout.py`; `tests/browser/test_browser_interactions.py`; `tests/browser/test_browser_full_app_e2e.py` | tool-route visibility, layout drag persistence, resize-handle availability, shared modal shell, and broad shell rerender continuity |
| Project / import | project details, project output root, create/select project, project-folder display, gated PractiScore dashboard opener, gated manual PractiScore file import, match-type selection, competitor/place/class/division selectors | `tests/browser/test_browser_control.py`; `tests/browser/test_project_lifecycle_contracts.py`; `tests/browser/test_browser_interactions.py`; `tests/browser/test_practiscore_session_api.py`; `tests/browser/test_practiscore_sync_controller.py`; `tests/browser/test_browser_full_app_e2e.py` | dashboard-open action, manual file import parity, missing-folder creation notice, metadata-only delete safety, project-owned output root, and PractiScore session/sync parity without stage lifecycle ownership |
| Media | active stage selector, stage name, `Save Stage`, `Delete Stage`, active-stage `Add Stage`, primary asset, stage file rows, file intake, `Set Primary`, `Remove`, `Add Media` | `tests/browser/test_browser_interactions.py`; `tests/browser/test_media_pane_qa.py`; `tests/browser/test_browser_remaining_controls_e2e.py`; `tests/browser/test_browser_full_app_e2e.py` | stage lifecycle workflow, active-stage inventory ownership, primary designation, file removal, picker-root continuity, and live-stage continuity without queue membership ownership |
| Compose | stage default layout/size/position controls, default restore, per-item card toggle, per-item size/opacity/position/layout/sync controls | `tests/browser/test_merge_export_contracts.py`; `tests/browser/test_timing_waveform_contracts.py`; `tests/browser/test_browser_remaining_controls_e2e.py`; `tests/browser/test_browser_full_app_e2e.py`; `tests/browser/test_compose_layout_actual.py`; `tests/export/test_export.py` | stage-default vs per-source ownership, visible preview geometry truth, card expansion, sync/value persistence, and merge/export payload parity without reclaiming media intake/removal ownership |
| Trim | original-timeline buffer trim, per-source trim/apply/clear, still-image exclusion, sync offsets, nudge controls, sync analysis, custom play/pause/scrubber transport, `Undo Last Change`, waveform compare interactions | `tests/browser/test_trim_sync_actual.py`; `tests/browser/test_trim_pane_qa.py`; `tests/browser/test_timing_waveform_contracts.py`; `tests/browser/test_browser_interactions.py`; `tests/browser/test_browser_remaining_controls_e2e.py`; `tests/browser/test_browser_full_app_e2e.py` | exact retained duration, two-decimal time labels, native-control restoration, repeat-apply stability, trim/sync controls, undo-capable timing workbench edits, waveform interactions, preview/status truth, and established header/toggle treatment |
| Score | enable scoring toggle, preset selection, imported score reference summary, expanded scoring workbench rows, restore flow | `tests/browser/test_scoring_metrics_contracts.py`; `tests/browser/test_metrics_e2e.py`; `tests/browser/test_browser_remaining_controls_e2e.py`; `tests/browser/test_browser_full_app_e2e.py` | preset-driven score rows, sport-aware imported score and penalty reference, scoring workbench open/close flow, score restore path, and metrics handoff after edits |
| Splits / waveform | split pane summary, enable splits toggle, Edit, timing-event controls, waveform expand/zoom/amplitude, waveform pan | `tests/browser/test_timing_waveform_contracts.py`; `tests/browser/test_browser_interactions.py`; `tests/browser/test_browser_remaining_controls_e2e.py`; `tests/browser/test_metrics_e2e.py`; `tests/browser/test_browser_full_app_e2e.py` | waveform expand/zoom/amplitude, drag movement, timing-event add/delete, timing workbench lock/edit/delete/restore, and selected-shot nudge propagation |
| Markers / Review / Overlay | marker authoring, review visibility selectors, independent split-badge score visibility, overlay badge/text-box controls, imported summary preview formatting, popup editor, text-box drag | `tests/browser/test_overlay_review_contracts.py`; `tests/browser/test_browser_interactions.py`; `tests/browser/test_browser_remaining_controls_e2e.py`; `tests/browser/test_browser_full_app_e2e.py`; `tests/export/test_export.py` | workbench editing flow, independent split/shot-score/summary visibility, review box styling and placement, and denominator-style placement formatting parity between review preview and export output |
| Settings | scope, landing pane, reopen-last-tool, section save current/reset default actions, layout defaults, Compose defaults, overlay defaults, marker defaults including default quadrant, export defaults, ShotML defaults, section collapse, template fields | `tests/browser/test_settings_e2e.py`; `tests/browser/test_settings_defaults_truth_gate.py`; `tests/browser/test_browser_full_app_e2e.py`; `tests/browser/test_browser_control.py` | import-current/reset-defaults round trips, section-targeted reset semantics, layout capture/release defaults, compose media-default seeding, marker default placement capture, export/overlay/compose default propagation, and new-project seeding truth gates |
| Metrics | run summary cards, sport-aware overall/division/classification placement cards, workbench expand/collapse, detailed graphs, CSV/TXT export, scoring/timing propagation | `tests/browser/test_metrics_e2e.py`; `tests/browser/test_scoring_metrics_contracts.py`; `tests/browser/test_competition_comparison.py`; `tests/browser/test_browser_full_app_e2e.py` | metrics pane row propagation, IDPA final-time and USPSA hit-factor cohort ranking, timing-event ordering, graph story continuity, and metrics export downloads |
| Export | preset, quality, stage-local render settings, show export log modal open/close/backdrop and download | `tests/browser/test_merge_export_contracts.py`; `tests/browser/test_browser_remaining_controls_e2e.py`; `tests/browser/test_browser_full_app_e2e.py`; `tests/export/test_export.py` | export payload capture, project-owned output root usage, export log modal open/close/backdrop and download, and stage-local render settings truth without direct output-path browsing from the Export pane |
| Queue | stage selector, queue membership, queue status, per-stage collapse, `Apply Active Stage Settings to Queued`, `Process Many`, `Process Into 1 File` | `tests/browser/test_browser_remaining_controls_e2e.py`; `tests/browser/test_browser_full_app_e2e.py` | factual queue-entry presentation, queue/requeue/unqueue membership from Queue, queued/stale/complete state visibility, template-apply behavior, and one-file vs combined processing without re-owning stage browsing |
| ShotML | average auto-confidence summary, threshold apply/reset, rerun, proposal generation, reset defaults | `tests/browser/test_browser_remaining_controls_e2e.py`; `tests/browser/test_browser_full_app_e2e.py`; `tests/analysis/test_analysis.py`; `tests/browser/test_browser_control.py` | average auto-confidence summary, threshold rerun/reset semantics, numeric control commits, proposal apply/discard, and section collapse state within a live session |

## Phase 18 cross-check notes

### Project context restoration

- `tests/browser/test_browser_interactions.py` should own the retained `Project` selector flow for imported stage, competitor name, and competitor place.
- `tests/browser/test_project_lifecycle_contracts.py` should keep the compact PractiScore summary contract visible and prevent `Project` from regaining stage media/file controls.

### Media workflow rewrite

- `tests/browser/test_browser_interactions.py` should own the active-stage workflow:
  stage selector, stage save/delete, `Set Primary`, `Add Media`, and active-stage `Add Stage`.
- `tests/browser/test_browser_remaining_controls_e2e.py` and `tests/browser/test_browser_full_app_e2e.py` should keep media-state persistence, file-removal truth, and live-stage continuity explicit.

### Queue and Review truth

- `tests/browser/test_browser_interactions.py` and `tests/browser/test_browser_full_app_e2e.py` should own queue membership from Queue, not Media.
- `tests/browser/test_overlay_review_contracts.py`, `tests/browser/test_browser_full_app_e2e.py`, and `tests/export/test_export.py` should keep denominator-based placement formatting explicit across review preview and rendered/exported output.

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
