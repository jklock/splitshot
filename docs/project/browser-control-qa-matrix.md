# Browser Control QA Matrix

Audited against the v1.0.7 `src/splitshot/browser/static/index.html` rail, current browser routes, and current browser suites.

This matrix names the current browser surfaces, the control families each surface owns, and the suites that keep those claims explicit. The rail order is Project, Media, Compose, Trim, Score, Splits, Markers, Overlay, Review, Export, Queue, Metrics, ShotML, and Settings.

Use `scripts/audits/browser/pane_function_audit.py` as the code-first companion audit. It inventories pane-owned functions from `src/splitshot/browser/static/panes/`, traces browser routes into `server.py` and `controller.py`, and classifies proof strength per function.

The executable static identifier inventory lives in `tests/browser/test_browser_control_inventory_audit.py`; this matrix is the retained human-readable ownership map.

| Surface | Control families | Primary suites | Current explicit ownership |
| --- | --- | --- | --- |
| Shared shell | rail routing, status bar lock, rail/sidebar/waveform resize handles, color picker shell, modal chrome | `tests/browser/test_browser_static_ui.py`; `tests/browser/test_browser_rail_layout.py`; `tests/browser/test_browser_interactions.py`; `tests/browser/test_browser_full_app_e2e.py` | tool-route visibility, layout drag persistence, resize-handle availability, shared modal shell, and broad shell rerender continuity |
| Project / import | project details, project output root, create/select/open project, project-folder display, gated PractiScore dashboard opener, project-rooted PractiScore file import, inferred match type, competitor/place/class/division selectors | `tests/browser/test_browser_control.py`; `tests/browser/test_project_lifecycle_contracts.py`; `tests/browser/test_browser_interactions.py`; `tests/browser/test_practiscore_session_api.py`; `tests/browser/test_practiscore_sync_controller.py`; `tests/browser/test_browser_full_app_e2e.py` | project-folder picker open, dashboard-open action, project `CSV/` picker root, immediate project-managed import, file-derived match type, all-imported-stage scoring hydration, required-folder creation, metadata-only save/delete safety, project-owned output root, and PractiScore session/sync parity without stage lifecycle ownership |
| Media | active stage selector, stage name, `Save`, `Delete`, `Add Stage`, persistent Primary/Added Media disclosures, `Add Primary`, primary asset `Replace`/`Clear`, `Set Primary`, `Remove`, `Add Media` | `tests/browser/test_media_pane_qa.py`; `tests/browser/test_v107_pane_visual_contract.py`; `tests/browser/test_browser_interactions.py` | stage lifecycle workflow, persistent deletion of imported stages without autosave rehydration, server-confirmed stage switching, active-stage inventory isolation, duplicate-name rejection, in-flight import mutation lock, inherited non-media stage configuration, immediate project `Input/` import, fixed project picker root, persistent flat inventory disclosure, primary designation, file removal, and live-stage continuity without queue membership ownership |
| Compose | stage default layout/size/position controls, `Reset Defaults`, per-item card toggle, per-item size/opacity/position/layout/sync controls | `tests/browser/test_merge_export_contracts.py`; `tests/browser/test_v107_pane_visual_contract.py`; `tests/browser/test_browser_remaining_controls_e2e.py`; `tests/browser/test_compose_layout_actual.py`; `tests/export/test_export.py` | stage-default vs per-source ownership, visible preview geometry truth, card expansion, single sync-value presentation, and merge/export payload parity without reclaiming media intake/removal ownership |
| Trim | selected-stage bulk trim, per-source `Apply`/`Clear`/`Undo`, still-image exclusion, sync offsets, nudge controls, sync analysis, custom `Play`/`Pause` scrubber transport, waveform compare interactions | `tests/analysis/test_analysis.py`; `tests/browser/test_trim_sync_actual.py`; `tests/browser/test_trim_pane_qa.py`; `tests/browser/test_v107_pane_visual_contract.py`; `tests/browser/test_timing_waveform_contracts.py` | easy select-all/clear stage membership, stage-wide primary and added-media trim, deterministic stage/time/date filenames, exact retained duration, native-control restoration, repeat-apply stability, source trim/sync controls, scroll reachability, and preview/status truth without redundant timing summary copy |
| Score | enable scoring toggle, preset selection, imported score reference summary, expanded scoring workbench rows, restore flow | `tests/browser/test_scoring_metrics_contracts.py`; `tests/browser/test_metrics_e2e.py`; `tests/browser/test_browser_remaining_controls_e2e.py`; `tests/browser/test_browser_full_app_e2e.py` | preset-driven score rows, sport-aware imported score and penalty reference, scoring workbench open/close flow, score restore path, and metrics handoff after edits |
| Splits / waveform | split pane summary, enable splits toggle, Edit, timing-event controls, waveform expand/zoom/amplitude, waveform pan | `tests/browser/test_timing_waveform_contracts.py`; `tests/browser/test_browser_interactions.py`; `tests/browser/test_browser_remaining_controls_e2e.py`; `tests/browser/test_metrics_e2e.py`; `tests/browser/test_browser_full_app_e2e.py` | waveform expand/zoom/amplitude, drag movement, timing-event add/delete, timing workbench lock/edit/delete/restore, and selected-shot nudge propagation |
| Markers / Review / Overlay | marker authoring, review visibility selectors, independent split-badge score visibility, overlay badge/text-box controls, imported summary preview formatting, stage presentation waterfall, marker editor, text-box drag | `tests/browser/test_overlay_review_contracts.py`; `tests/browser/test_browser_interactions.py`; `tests/browser/test_browser_remaining_controls_e2e.py`; `tests/browser/test_browser_full_app_e2e.py`; `tests/export/test_export.py` | workbench editing flow, downstream inheritance until direct override, independent split/shot-score/summary visibility, review box styling and placement, stage-specific source-derived `<division> - place/total`, `<class> - place/total`, and `Overall - place/total` parity between preview and export |
| Settings | scope, landing pane, reopen-last-tool, section save current/reset default actions, layout defaults, Compose defaults, overlay defaults, marker defaults including default quadrant, export defaults, ShotML defaults, section collapse, template fields | `tests/browser/test_settings_e2e.py`; `tests/browser/test_settings_defaults_truth_gate.py`; `tests/browser/test_browser_full_app_e2e.py`; `tests/browser/test_browser_control.py` | import-current/reset-defaults round trips, section-targeted reset semantics, layout capture/release defaults, compose media-default seeding, marker default placement capture, export/overlay/compose default propagation, and new-project seeding truth gates |
| Metrics | match/per-stage overview, active-stage summary cards, sport-aware placement cards, workbench expand/collapse, detailed graphs, CSV/TXT export, scoring/timing propagation | `tests/browser/test_metrics_e2e.py`; `tests/browser/test_scoring_metrics_contracts.py`; `tests/browser/test_competition_comparison.py`; `tests/browser/test_browser_full_app_e2e.py` | match aggregation, stage summary rows, compact Split Timeline sizing, responsive multi-column expanded graphs with readable unclipped SVG labels, visible expanded table, active-stage detail continuity, IDPA final-time and USPSA `Combined HF` labeling, timing-event ordering, and stage-identified metrics exports |
| Export | saveable output profiles, preset, quality, stage-local render settings, show export log modal open/close/backdrop and download | `tests/browser/test_merge_export_contracts.py`; `tests/browser/test_browser_remaining_controls_e2e.py`; `tests/browser/test_browser_full_app_e2e.py`; `tests/export/test_export.py` | export profile snapshot/apply/update behavior, project-owned output root usage, export log modal open/close/backdrop and download, and stage-local render settings truth without direct output execution from Export |
| Queue | `Active Stage`, queue membership, always-visible status rows, project fades, output-folder reveal, whole-queue progress, `Process Many`, `Process Into 1 File` | `tests/browser/test_queue_pane_qa.py`; `tests/browser/test_v107_pane_visual_contract.py`; `tests/browser/test_browser_control.py`; `tests/browser/test_project_lifecycle_contracts.py` | factual compact queue rows without minimize controls, queue/requeue/unqueue membership, queued/stale/complete state visibility, video/audio fade boundaries, platform-neutral output reveal, and individual vs combined progress through final validation |
| ShotML | average auto-confidence summary, threshold apply/reset, rerun, proposal generation, reset defaults | `tests/browser/test_browser_remaining_controls_e2e.py`; `tests/browser/test_browser_full_app_e2e.py`; `tests/analysis/test_analysis.py`; `tests/browser/test_browser_control.py` | average auto-confidence summary, threshold rerun/reset semantics, numeric control commits, proposal apply/discard, and section collapse state within a live session |

## Cross-check notes

### Project context restoration

- `tests/browser/test_browser_interactions.py` should own the retained `Project` selector flow for imported stage, competitor name, and competitor place.
- `tests/browser/test_project_lifecycle_contracts.py` should keep the compact PractiScore summary contract visible and prevent `Project` from regaining stage media/file controls.

### Media workflow rewrite

- `tests/browser/test_browser_interactions.py` should own the active-stage workflow:
  stage selector, stage save/delete, `Set Primary`, `Add Media`, and active-stage `Add Stage`.
- `tests/browser/test_browser_remaining_controls_e2e.py` and `tests/browser/test_browser_full_app_e2e.py` should keep media-state persistence, file-removal truth, and live-stage continuity explicit.

### Queue and Review truth

- `tests/browser/test_browser_interactions.py` and `tests/browser/test_browser_full_app_e2e.py` should own queue membership from Queue, not Media.
- `tests/browser/test_overlay_review_contracts.py`, `tests/browser/test_browser_full_app_e2e.py`, and `tests/export/test_export.py` should keep source-derived division/class acronym lines, the `Overall` line, and denominator-based placement formatting explicit across review preview and rendered/exported output.

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
