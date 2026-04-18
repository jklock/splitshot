# Left Pane Remediation Implementation Specification

This document is the implementation specification for the remaining left-pane remediation work identified in [LEFT_PANE_AUDIT.md](LEFT_PANE_AUDIT.md) and tracked in [LEFT_PANE_REMEDIATION_TODO.md](LEFT_PANE_REMEDIATION_TODO.md).

All remaining work items are equal execution priority. Risk severity still matters for validation depth, but no remaining item should be treated as a lower-class backlog item that can be ignored.

## Scope

- Remaining Project pane work: 5 items
- Remaining Score and Metrics work: 8 items
- Remaining Splits and waveform work: 4 items
- Remaining PiP and Export work: 7 items
- Remaining Overlay and Review work: 8 items
- Total remaining equal-priority work items: 32

This specification does not reopen the items already marked closed in [LEFT_PANE_REMEDIATION_TODO.md](LEFT_PANE_REMEDIATION_TODO.md).

## Equal-Priority Execution Model

- Every remaining item is in scope for the current remediation program.
- Execution order is chosen only to reduce merge conflicts and validation ambiguity.
- Risk severity is a validation multiplier, not an execution-priority override.
- No workstream is allowed to skip its lower-risk items once its code area is opened.
- A workstream is only complete when its entire assigned checklist is complete, tested, and documented.

## User-Visible Behavior Freeze

The remediation program is not a redesign. Preserve the user-visible behavior that exists today unless a separate product decision explicitly authorizes a change.

The following contracts are frozen during remediation:

- Left-rail page set, order, and labels
- Existing DOM ids and data attributes used by the browser shell
- Existing API routes and request shapes under `/api/*`
- Existing project JSON keys and saved bundle layout
- Existing export preset ids, default values, and file-path behavior
- Existing visible labels that users already rely on in the pane UI
- Existing browser audit flows that currently pass on bundled repo-local media

## Global Risk Prevention Rules

1. Characterize first.
   Add or extend tests that prove the current user-visible behavior before changing logic.

2. Change the narrowest seam.
   Fix one state handoff, serializer, or render path at a time. Do not mix unrelated cleanup into remediation.

3. Preserve current contracts.
   Do not rename routes, ids, JSON keys, export fields, or workflow labels unless the product explicitly requires it.

4. Validate all affected layers.
   If a change touches a cross-pane seam, validate browser UI, controller/state persistence, and export or presentation behavior as applicable.

5. Prefer additive targeted tests.
   Create new targeted test files instead of growing the already-large browser contract files when parallel work would otherwise collide.

6. Use real bundled media for behavior claims.
   Any preview, merge, PractiScore, or export parity claim must be backed by the bundled-media browser audits.

7. Keep hot files scoped.
   `app.js`, `browser/server.py`, `ui/controller.py`, `browser/state.py`, `presentation/stage.py`, and `export/pipeline.py` are shared hot spots. Each workstream must stay inside its named function families.

## Shared Architecture Map

| Seam | Authoritative state | Primary browser functions | Backend and model files | Main regression risk |
| --- | --- | --- | --- | --- |
| Project and import lifecycle | `Project`, `project.ui_state`, PractiScore context | `applyProjectDetailsDraft`, `readPractiScoreContextPayload`, `flushPendingProjectDrafts`, `probeProjectFolder`, `useProjectFolder` | `src/splitshot/browser/server.py`, `src/splitshot/ui/controller.py`, `src/splitshot/persistence/projects.py` | stale draft state, wrong project path, unintended resets |
| Score and Metrics | `scoring_summary`, shot score state, imported-stage data | `renderScoringShotList`, `renderScoringPenaltyFields`, `renderPractiScoreSummaries`, `buildMetricsRows`, `renderMetricsPanel` | `src/splitshot/scoring/logic.py`, `src/splitshot/browser/state.py` | imported/manual precedence drift, stale projection |
| Splits and waveform | `split_rows`, `timing_segments`, selected-shot state, timing events | `splitRowForShot`, `resolvedSplitMsForShot`, `renderTimingTable`, `renderSelection`, `renderTimingEventList`, `scheduleThresholdApply` | `src/splitshot/timeline/model.py`, `src/splitshot/presentation/stage.py`, `src/splitshot/browser/state.py`, `src/splitshot/ui/controller.py` | orphaned selection, projection drift, invalid anchors |
| PiP and Export | `merge_sources`, export settings, export payload snapshots | `syncSecondaryPreview`, `renderMergePreviewLayer`, `renderMergeMediaList`, `scheduleMergeSourceCommit`, `buildExportPayload`, `renderExportLog` | `src/splitshot/browser/server.py`, `src/splitshot/ui/controller.py`, `src/splitshot/export/pipeline.py`, `src/splitshot/merge/layouts.py` | preview/export mismatch, stale export snapshot |
| Overlay and Review | `project.overlay`, `text_boxes`, lock-to-stack state | `readOverlayPayload`, `syncOverlayPreviewStateFromControls`, `setOverlayTextBoxField`, `renderTextBoxEditors`, `beginOverlayBadgeDrag`, `beginTextBoxDrag`, `renderLiveOverlay` | `src/splitshot/ui/controller.py`, `src/splitshot/browser/server.py`, `src/splitshot/overlay/render.py` | preview/export drift, normalization drift, drag cleanup failures |

## Planned Test File Additions

To reduce parallel conflicts, remediation work should prefer new targeted files over editing the large legacy browser test files unless a current assertion must be updated in place.

Planned targeted test files:

- `tests/browser/test_project_lifecycle_contracts.py`
- `tests/browser/test_scoring_metrics_contracts.py`
- `tests/browser/test_timing_waveform_contracts.py`
- `tests/browser/test_merge_export_contracts.py`
- `tests/browser/test_overlay_review_contracts.py`
- `tests/persistence/test_project_lifecycle_contracts.py`
- `tests/scoring/test_scoring_metrics_contracts.py`
- `tests/presentation/test_timing_contracts.py`
- `tests/export/test_merge_export_contracts.py`

These file names are part of the conflict-reduction plan. Subagents should use them unless an existing file is the only sensible location.

## Workstream A: Project, Import, and Lifecycle

Primary code ownership:

- `src/splitshot/browser/static/app.js`
  Function family: `applyProjectDetailsDraft`, `readPractiScoreContextPayload`, `flushPendingProjectDrafts`, `probeProjectFolder`, `useProjectFolder`, `autoApplyProjectDetails`, `autoApplyPractiScoreContext`, `scheduleProjectDetailsApply`, `schedulePractiScoreContextApply`
- `src/splitshot/browser/server.py`
  Route family: `/api/project/*`, `/api/files/practiscore`, `/api/import/primary`, `/api/dialog/path`
- `src/splitshot/ui/controller.py`
  Project details, project lifecycle, import, and PractiScore context mutations
- `src/splitshot/persistence/projects.py`

### Item A1: Freeze project detail draft and apply semantics across pane switches and save/open

Implementation detail:

1. Add characterization coverage for typing in project name and description, switching panes before debounce completes, explicit save, reopen, and browser refresh.
2. Confirm the current draft path: control value -> `readProjectDetailsPayload()` -> `applyProjectDetailsDraft()` -> `autoApplyProjectDetails()` -> `/api/project/details` -> autosave.
3. Ensure all project lifecycle actions that can discard local draft state explicitly call `flushPendingProjectDrafts()` first.
4. Ensure state refresh from the server does not rehydrate stale input values over newer locally typed values during an in-flight debounce window.

Risk prevention:

- Preserve the current save/open button flow and field ids.
- Preserve autosave timing; do not replace it with explicit-save-only behavior.
- Do not collapse the draft model into direct writes unless characterization proves identical behavior.

Validation:

- `pytest tests/browser/test_project_lifecycle_contracts.py`
- `pytest tests/persistence/test_project_lifecycle_contracts.py`

### Item A2: Harden project-folder probe and chosen-path consistency

Implementation detail:

1. Add characterization coverage for dialog-selected project paths, typed project paths, probe results, and open/create decisions.
2. Ensure `probeProjectFolder()` and `useProjectFolder()` resolve and compare the same normalized path value.
3. Reject mismatched probe/apply paths and ensure the UI does not proceed on stale probe results.
4. Keep current behavior for empty folders, folders with `project.json`, and explicit open paths.

Risk prevention:

- Preserve the current folder chooser behavior and readonly path field behavior.
- Do not change the meaning of `Choose Project`, `Open Project`, or `New Project`.

Validation:

- `pytest tests/browser/test_project_lifecycle_contracts.py -k project_folder`

### Item A3: Lock PractiScore context reimport determinism

Implementation detail:

1. Add characterization coverage for repeated imports of the same file, changed stage, changed competitor, and changed place.
2. Ensure the staged source file and the selected stage and competitor are the only drivers of reimport.
3. Ensure the same input file plus the same selected context produces the same `imported_stage`, `practiscore_options`, and imported-summary overlay state.
4. Ensure the current fallback behavior when competitor place changes in a new file remains stable.

Risk prevention:

- Preserve current field defaults and source-name display.
- Preserve current auto-enable behavior for the imported summary box only after real import.

Validation:

- `pytest tests/analysis/test_practiscore_import.py`
- `pytest tests/browser/test_project_lifecycle_contracts.py -k practiscore`

### Item A4: Contain primary-import side effects so unrelated pane state is not reset accidentally

Implementation detail:

1. Characterize the current intended reset set after primary import: analysis state, media-bound selection, merge state, export log freshness, and any retained reusable settings.
2. Separate intentional bootstrap resets from accidental UI-state resets.
3. Ensure primary replacement preserves reusable configuration that is already intended to persist, while clearing only media-bound state.
4. Confirm reopen and import parity so the same reset rules apply from both routes.

Risk prevention:

- Preserve the current imported-media bootstrap behavior that the tests already expect.
- Do not widen retention rules unless characterization proves current behavior already retains them.

Validation:

- `pytest tests/analysis/test_analysis.py -k primary_replacement`
- `pytest tests/browser/test_project_lifecycle_contracts.py -k primary_import`

### Item A5: Verify lifecycle restore behavior across new/open/save/delete flows

Implementation detail:

1. Add characterization tests for landing pane, active tool, expanded waveform, expanded timing, and selection state across new/open/save/delete.
2. Ensure the current server response rehydrates the current intended UI state in one consistent order.
3. Keep project deletion from leaking stale export log or stale open-project metadata into the next clean state.

Risk prevention:

- Preserve the current landing pane choices unless a product decision says otherwise.
- Do not combine lifecycle restore changes with unrelated project detail refactors.

Validation:

- `pytest tests/browser/test_project_lifecycle_contracts.py -k lifecycle`

## Workstream B: Score and Metrics

Primary code ownership:

- `src/splitshot/browser/static/app.js`
  Function family: `renderScoringShotList`, `renderScoringPenaltyFields`, `renderPractiScoreSummaries`, `buildMetricsRows`, `renderMetricsPanel`, `buildMetricsCsv`, `buildMetricsText`
- `src/splitshot/scoring/logic.py`
- `src/splitshot/browser/state.py`

### Item B1: Formalize imported-stage precedence versus manual shot edits

Implementation detail:

1. Characterize the current visible behavior when imported official data exists and the user manually edits shot scores.
2. Make the precedence rules explicit in scoring summary construction: which fields come from current project state, which remain official imported references, and which are deltas.
3. Ensure Score pane copy and Metrics projection use the same summary contract.

Risk prevention:

- Preserve current visible totals unless a product decision says they should change.
- Preserve the current Official Raw / Video Raw / Raw Delta display contract.

Validation:

- `pytest tests/scoring/test_scoring_metrics_contracts.py`
- `pytest tests/browser/test_scoring_metrics_contracts.py -k imported`

### Item B2: Harden preset-switch compatibility for penalty fields

Implementation detail:

1. Characterize current preset switches between time-plus and hit-factor profiles.
2. Define exactly which penalty fields must be retained, cleared, or hidden when the preset changes.
3. Ensure hidden incompatible penalty counts do not silently continue affecting summaries.

Risk prevention:

- Preserve current preset ids and visible preset selector behavior.
- Preserve shot-row layout and score-letter defaults.

Validation:

- `pytest tests/scoring/test_scoring_metrics_contracts.py -k preset`
- `pytest tests/browser/test_scoring_metrics_contracts.py -k preset`

### Item B3: Protect score-restore behavior after reanalysis or shot mutation

Implementation detail:

1. Characterize restore behavior after shot move, shot delete, and threshold reanalysis.
2. Ensure restore uses the correct current shot identity and source snapshot.
3. Prevent restore operations from resurrecting incompatible penalty state after shot replacement.

Risk prevention:

- Preserve current restore button semantics and visible values.
- Do not change shot ids or restore endpoints to solve this.

Validation:

- `pytest tests/scoring/test_scoring_metrics_contracts.py -k restore`
- `pytest tests/browser/test_scoring_metrics_contracts.py -k restore`

### Item B4: Lock the Score-to-Metrics summary contract

Implementation detail:

1. Identify the summary fields consumed by both Score and Metrics.
2. Ensure both panes read from the same `scoring_summary` schema and do not recompute overlapping fields differently.
3. Assert that exported Metrics text and CSV use the same values as the rendered Metrics pane.

Risk prevention:

- Preserve existing metric labels, CSV headings, and text-export structure.

Validation:

- `pytest tests/browser/test_scoring_metrics_contracts.py -k metrics`

### Item B5: Lock imported-stage scoring-context freshness in Metrics

Implementation detail:

1. Characterize Metrics after PractiScore import, reimport, stage change, and competitor change.
2. Ensure Metrics rerenders when imported-stage context changes.
3. Ensure Metrics does not lag behind Score on imported-stage source or stage metadata.

### Item B6: Define beep-null and missing-data projection behavior

Implementation detail:

1. Characterize current Metrics rendering when beep time is missing, raw time is unavailable, or imported-stage data is incomplete.
2. Explicitly normalize blank versus zero versus unavailable values.
3. Ensure CSV and text export use the same missing-data policy.

### Item B7: Keep confidence display fresh after reanalysis

Implementation detail:

1. Characterize Metrics before and after threshold reanalysis and primary reimport.
2. Ensure the pane rerenders from fresh shot confidence values and does not retain stale projections.

### Item B8: Ensure Metrics exports reflect the same current derived state as the pane

Implementation detail:

1. Assert that `buildMetricsRows()`, `buildMetricsCsv()`, and `buildMetricsText()` are all fed from the same current row model.
2. Prevent export helpers from taking stale snapshots after a rerender.

Risk prevention for B5-B8:

- Preserve current labels, wording, and file naming.
- Do not introduce a second scoring-summary model for Metrics.

Validation for B5-B8:

- `pytest tests/browser/test_scoring_metrics_contracts.py`
- `pytest tests/scoring/test_scoring_metrics_contracts.py`

## Workstream C: Splits and Waveform

Primary code ownership:

- `src/splitshot/browser/static/app.js`
  Function family: `splitRowForShot`, `resolvedSplitMsForShot`, `renderTimingEventList`, `renderTimingEventEditor`, `addTimingEvent`, `renderTimingTable`, `renderTimingTables`, `renderSelection`, `setTimingExpanded`, `autoApplyThreshold`, `scheduleThresholdApply`
- `src/splitshot/timeline/model.py`
- `src/splitshot/presentation/stage.py`
- `src/splitshot/browser/state.py`
- `src/splitshot/ui/controller.py`

### Item C1: Prevent selected-shot orphaning after delete or reanalysis

Implementation detail:

1. Characterize the current fallback selection after delete, threshold reanalysis, and primary reimport.
2. Ensure selected-shot state is revalidated against current shots after every destructive timing mutation.
3. Apply the same validation logic to compact table, expanded workbench, waveform, and browser UI state restore.

### Item C2: Preserve user context when threshold reanalysis replaces timing state

Implementation detail:

1. Characterize threshold changes while a shot is selected and while the timing workbench is expanded.
2. Preserve user context to the same shot when it still exists, otherwise move to the nearest valid successor or predecessor using a deterministic rule.
3. Keep the current threshold control behavior and debounce cadence.

### Item C3: Validate timing-event anchors after shot deletion and movement

Implementation detail:

1. Characterize current timing-event behavior when anchor shots move or disappear.
2. Ensure event anchors are revalidated after shot mutations and before split-row generation.
3. Keep valid events and reject only invalid or dangling anchors.

### Item C4: Keep waveform and timing-table selection in sync under all navigation paths

Implementation detail:

1. Characterize table click, waveform click, waveform drag, nudge buttons, delete, and restore.
2. Ensure the same selected shot id drives waveform highlight, selected-shot panel, and timing row highlight.
3. Reuse one selection source of truth across waveform and table rerenders.

Risk prevention:

- Preserve existing keyboard behavior, nudge buttons, and timing workbench layout.
- Do not change timing column ids or selection affordances.

Validation:

- `pytest tests/browser/test_timing_waveform_contracts.py`
- `pytest tests/presentation/test_timing_contracts.py`
- `pytest tests/analysis/test_analysis.py -k timing`

## Workstream D: PiP and Export

Primary code ownership:

- `src/splitshot/browser/static/app.js`
  Function family: `syncSecondaryPreview`, `scheduleSecondaryPreviewSync`, `renderMergePreviewLayer`, `renderMergeMediaList`, `scheduleMergeSourceCommit`, `buildExportPayload`, `scheduleExportLayoutApply`, `scheduleExportSettingsApply`, `renderExportLog`
- `src/splitshot/browser/server.py`
  Route family: `/api/merge*`, `/api/export*`
- `src/splitshot/ui/controller.py`
- `src/splitshot/export/pipeline.py`
- `src/splitshot/merge/layouts.py`

### Item D1: Lock live preview sync to persisted `sync_offset_ms` behavior

Implementation detail:

1. Characterize current preview playback offset, saved merge source offset, reopened project offset, and export offset.
2. Ensure preview time calculation reads the same persisted source offset that export uses.
3. Remove any preview-only offset path that is not persisted.

### Item D2: Guarantee drag interactions commit before autosave and export

Implementation detail:

1. Characterize merge preview drag end followed immediately by save, reopen, and export.
2. Ensure drag end always produces a committed merge-source payload before autosave or export snapshot creation.
3. Use one commit path for drag, blur, and explicit control changes.

### Item D3: Make non-PiP layout expectations explicit without changing existing layout behavior

Implementation detail:

1. Characterize what the current preview does and does not show in side-by-side and above-below.
2. Add coverage that documents those expectations.
3. If UI clarification is needed, keep it descriptive rather than behavioral.

### Item D4: Validate multi-source merge expectations beyond current source serialization

Implementation detail:

1. Expand merge tests around source ordering, per-source offsets, and layout combinations.
2. Ensure export order matches the order the browser state intends.

### Item D5: Lock export-path draft consistency

Implementation detail:

1. Characterize current export-path typing, browse, reopen, preset change, and save behavior.
2. Ensure the path control, persisted state, and final export target all reflect the same current value.

### Item D6: Clarify preset versus custom-mode behavior without changing current render settings

Implementation detail:

1. Characterize current preset application, manual override, and custom-mode persistence.
2. Make the mode boundary explicit in state handling without altering existing exported output.

### Item D7: Prevent stale export-log state from looking like a current failure

Implementation detail:

1. Characterize log state after success, failure, close, reopen, and next export.
2. Ensure stale error/log state is cleared or clearly historical before the next run.

Risk prevention:

- Preserve existing layout math and current export defaults.
- Preserve current output file naming, preset ids, and export modal behavior.

Validation:

- `pytest tests/browser/test_merge_export_contracts.py`
- `pytest tests/export/test_merge_export_contracts.py`
- `python scripts/audits/browser/run_browser_interaction_audit.py --browser chromium --report-json logs/browser-interaction-audit-test-videos-merge-export.json`
- `python scripts/audits/browser/run_browser_export_matrix.py`

## Workstream E: Overlay and Review

Primary code ownership:

- `src/splitshot/browser/static/app.js`
  Function family: `readOverlayPayload`, `syncOverlayPreviewStateFromControls`, `previewOverlayControlChanges`, `setOverlayTextBoxField`, `renderTextBoxEditors`, `beginTextBoxDrag`, `beginOverlayBadgeDrag`, `renderLiveOverlay`, `scheduleOverlayApply`
- `src/splitshot/browser/server.py`
  Route family: `/api/overlay`
- `src/splitshot/ui/controller.py`
- `src/splitshot/overlay/render.py`

### Item E1: Lock browser overlay payload parity with backend overlay rendering

Implementation detail:

1. Characterize current browser preview and exported output for badge style, font, bubble size, custom box geometry, and lock-to-stack behavior.
2. Make browser payload serialization and backend renderer consumption identical for those fields.
3. Add export render checks and real-browser checks around the currently supported overlay configurations.

### Item E2: Harden delayed color-commit behavior

Implementation detail:

1. Characterize picker open, preview change, commit, cancel, blur, and reopen flows.
2. Ensure preview-only color changes are clearly local until committed.
3. Ensure committed colors survive autosave, reopen, and export.

### Item E3: Formalize lock-to-stack versus explicit-coordinate contract

Implementation detail:

1. Characterize current behavior when the user drags a badge or text box and then toggles lock-to-stack.
2. Define one precedence rule and apply it consistently in browser preview, persisted overlay payload, and export render.

### Item E4: Lock score-token color persistence to live badge rendering

Implementation detail:

1. Characterize score-color grid changes in preview, reopen, and export.
2. Ensure the same token color mapping is used at preview and export time.

### Item E5: Lock imported-summary availability and default box behavior across import and reopen flows

Implementation detail:

1. Characterize imported-summary visibility, default quadrant, and auto-enable state across import, reopen, and project replace.
2. Ensure the imported-summary box exists only when current imported-stage data exists.

### Item E6: Harden post-drag `review_boxes_lock_to_stack` semantics

Implementation detail:

1. Characterize drag then toggle behavior for review text boxes.
2. Ensure the resulting state is deterministic and matches the same precedence rule used by export.

### Item E7: Preserve inspector scroll position through overlay round trips

Implementation detail:

1. Characterize scroll retention while editing multiple text boxes and while rerendering the review pane.
2. Preserve current card ordering and restore scroll position after overlay refreshes.

### Item E8: Ensure drag-state cleanup always completes after canceled or interrupted interactions

Implementation detail:

1. Characterize interrupted pointer flows, blur, pane switch, lost pointer capture, and rerender during drag.
2. Ensure all drag termination paths clear transient overlay interaction state.

Risk prevention:

- Preserve current overlay control ids, review card structure, and imported-summary defaults.
- Do not redesign badge visuals or review editor layout during remediation.

Validation:

- `pytest tests/browser/test_overlay_review_contracts.py`
- `pytest tests/export/test_export.py -k overlay`
- `python scripts/audits/browser/run_browser_interaction_audit.py --browser chromium --report-json logs/browser-interaction-audit-test-videos-overlay-review.json`

## Parallel Execution and Merge Protocol

Parallel execution is allowed, but each workstream must stay inside its owned function families and targeted test files.

Subagent merge rules:

1. Create or use the targeted test files listed in this spec whenever possible.
2. If a workstream must edit a shared hot file outside its owned function family, stop and escalate before broadening scope.
3. Do not perform unrelated cleanup or file moves while implementing remediation.
4. Every subagent deliverable must include:
   - changed files
   - tests run
   - browser audits run, if any
   - explicit statement that current user-visible behavior was preserved
   - any residual risk or merge conflict hotspot

## Required Integration Pass

After the subagent packets land, run the integration pass before declaring the remediation program complete.

Required integration validation:

- `pytest tests/browser`
- `pytest tests/analysis`
- `pytest tests/presentation`
- `pytest tests/scoring`
- `pytest tests/export`
- `pytest tests/persistence`
- `python scripts/audits/browser/run_browser_interaction_audit.py --browser chromium --report-json logs/browser-interaction-audit-test-videos-integration.json`
- `python scripts/audits/browser/run_browser_export_matrix.py`

## Subagent Packet Documents

The parallel work packets derived from this spec are:

- [SUBAGENT_TODO_PROJECT_AND_IMPORT.md](SUBAGENT_TODO_PROJECT_AND_IMPORT.md)
- [SUBAGENT_TODO_SCORE_AND_METRICS.md](SUBAGENT_TODO_SCORE_AND_METRICS.md)
- [SUBAGENT_TODO_SPLITS_AND_WAVEFORM.md](SUBAGENT_TODO_SPLITS_AND_WAVEFORM.md)
- [SUBAGENT_TODO_MERGE_AND_EXPORT.md](SUBAGENT_TODO_MERGE_AND_EXPORT.md)
- [SUBAGENT_TODO_OVERLAY_AND_REVIEW.md](SUBAGENT_TODO_OVERLAY_AND_REVIEW.md)