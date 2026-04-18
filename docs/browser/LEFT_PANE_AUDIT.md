# Left Pane Audit

This document is a pane-by-pane audit of the SplitShot browser shell's left-rail pages and their corresponding inspector panes. It focuses on four things:

1. what each pane visibly exposes;
2. what code paths actually own the state behind that pane;
3. how closely each pane is WYSIWYG versus a projection or orchestration surface;
4. where pane-to-pane drift can make the product feel "broken" even when part of the stack still works.

Open remediation backlog: [LEFT_PANE_REMEDIATION_TODO.md](LEFT_PANE_REMEDIATION_TODO.md).
Implementation specification: [LEFT_PANE_IMPLEMENTATION_SPEC.md](LEFT_PANE_IMPLEMENTATION_SPEC.md).

## Scope And Validation

This audit covers all eight left-rail pages in the shipped browser shell:

- Project
- Score
- Splits
- PiP
- Overlay
- Review
- Export
- Metrics

Primary code surfaces used for this audit:

- [src/splitshot/browser/static/index.html](../src/splitshot/browser/static/index.html)
- [src/splitshot/browser/static/app.js](../src/splitshot/browser/static/app.js)
- [src/splitshot/browser/server.py](../src/splitshot/browser/server.py)
- [src/splitshot/ui/controller.py](../src/splitshot/ui/controller.py)
- [src/splitshot/browser/state.py](../src/splitshot/browser/state.py)
- [src/splitshot/presentation/stage.py](../src/splitshot/presentation/stage.py)
- [src/splitshot/timeline/model.py](../src/splitshot/timeline/model.py)
- [src/splitshot/overlay/render.py](../src/splitshot/overlay/render.py)
- [src/splitshot/export/pipeline.py](../src/splitshot/export/pipeline.py)
- [src/splitshot/scoring/logic.py](../src/splitshot/scoring/logic.py)

Supporting browser validation baseline on 2026-04-18:

- `pytest tests/browser` -> `83 passed in 41.51s`
- full-suite baseline remains `204 passed` with `TOTAL 86%` coverage

## Inventory

The left rail is defined in [src/splitshot/browser/static/index.html](../src/splitshot/browser/static/index.html#L15-L24).

| Left-Rail Button | `data-tool` | Inspector Pane | Primary Role | WYSIWYG Class |
| --- | --- | --- | --- | --- |
| Project | `project` | `data-tool-pane="project"` | gateway and project-state coordinator | low WYSIWYG, high orchestration |
| Score | `scoring` | `data-tool-pane="scoring"` | score editor | high WYSIWYG for scoring state |
| Splits | `timing` | `data-tool-pane="timing"` plus expanded timing workbench | timing inspector plus editor-on-demand | medium-high WYSIWYG |
| PiP | `merge` | `data-tool-pane="merge"` | merge media and PiP state editor | medium WYSIWYG |
| Overlay | `overlay` | `data-tool-pane="overlay"` | overlay badge/style editor | high WYSIWYG target, medium drift risk |
| Review | `review` | `data-tool-pane="review"` | review text-box editor over shared overlay state | medium-high WYSIWYG, not independent |
| Export | `export` | `data-tool-pane="export"` | export-state editor and render launcher | not WYSIWYG |
| Metrics | `metrics` | `data-tool-pane="metrics"` | synthesized dashboard | read-only projection |

## Global Findings

### 1. The left rail is not eight isolated pages

Every pane is connected to the same `Project` model and browser-state projection. The browser UI is a set of coordinated surfaces over shared state, not independent modules. The controlling sources of truth are:

- the domain model in [src/splitshot/domain/models.py](../src/splitshot/domain/models.py)
- mutation logic in [src/splitshot/ui/controller.py](../src/splitshot/ui/controller.py)
- serialized browser payloads in [src/splitshot/browser/state.py](../src/splitshot/browser/state.py)
- live DOM state and debounced draft state in [src/splitshot/browser/static/app.js](../src/splitshot/browser/static/app.js)

That means visible correctness in one pane does not guarantee correctness elsewhere.

### 2. There are three different classes of pane

Editor panes:

- Score
- Splits
- PiP
- Overlay
- Review

Coordinator/orchestrator panes:

- Project
- Export

Read-only projection pane:

- Metrics

Breakage often happens when a user expects an editor pane to own its own state, but the actual mutation path lives in a different surface or shared serializer.

### 3. The highest-risk drift seams are shared-state seams

The biggest pane-to-pane risk relationships are:

- Review <-> Overlay: both edit `project.overlay.text_boxes`
- Splits <-> waveform <-> presentation: all depend on `split_rows`, `timing_segments`, and selected-shot state
- Score <-> Metrics: both rely on `scoring_summary`, but only Score edits
- PiP preview <-> export renderer: preview is DOM/browser-driven while export is backend-rendered
- Export <-> everything else: Export snapshots the other panes rather than owning the user-facing preview itself

### 4. The left-rail breakage pattern is usually not a missing button

The most likely regression class if "this basic relationship worked for several days and is now broken" is one of these:

- debounced UI draft state not flushed before a cross-pane action;
- one pane re-rendering from a different derived source than another;
- shared overlay/text-box state being normalized differently on two surfaces;
- preview logic and export logic diverging;
- active-tool and `project.ui_state` restore order causing one pane to visually reset another;
- a controller mutation still occurring, but the pane rendering path no longer reflecting it correctly.

## Cross-Pane Relationship Matrix

| Pane | Actually Owns State? | Depends On Other Panes? | WYSIWYG Strength | Highest Drift Risk |
| --- | --- | --- | --- | --- |
| Project | yes, for project metadata, paths, import context | yes, because imports initialize other panes | low | typed draft state, path/dialog flow, import side effects |
| Score | yes, for shot scoring and penalties | yes, with PractiScore, Metrics, Overlay final score | high | imported-stage precedence versus manual edits |
| Splits | yes for timing edits, but compact view is read-only | yes, with waveform, presentation, Metrics | medium-high | `split_rows` versus `timing_segments` drift |
| PiP | yes, for merge state | yes, with preview playback and Export | medium | preview parity versus export serialization |
| Overlay | yes, for badge and overlay styling | yes, with Review, Score, Export | high target | live preview serializer versus export renderer |
| Review | not independently; edits shared overlay text-box state | yes, heavily with Overlay and PractiScore | medium-high | shared text-box normalization and lock-to-stack behavior |
| Export | owns export settings only; snapshots the rest | yes, with all editor panes | low | stale snapshots and render-path mismatch |
| Metrics | no, read-only | yes, with Splits and Score | medium | synthesized-data drift |

## Project Pane

The Project pane is the application gateway. It owns project metadata, primary video selection, project-folder lifecycle, and PractiScore import context, but it also triggers analysis, scoring context, browser media state, and project autosave side effects that propagate into the other panes.

### Controls

- left-rail button `data-tool="project"` in [src/splitshot/browser/static/index.html](../src/splitshot/browser/static/index.html#L17)
- pane container `data-tool-pane="project"` in [src/splitshot/browser/static/index.html](../src/splitshot/browser/static/index.html#L489)
- `#project-name`
- `#project-description`
- `#media-badge`
- `#primary-file-path`
- `#browse-primary-path`
- hidden `#primary-file-input`
- `#project-path`
- `#browse-project-path`
- `#new-project`
- `#delete-project`
- PractiScore section: `#practiscore-status`, `#match-type`, `#match-stage-number`, `#match-competitor-name`, `#match-competitor-place`, `#import-practiscore`, hidden `#practiscore-file-input`, `#practiscore-import-summary`

### Client Wiring

- tool activation through [setActiveTool()](../src/splitshot/browser/static/app.js#L2250)
- project-detail drafting through `applyProjectDetailsDraft`, `scheduleProjectDetailsApply`, and `autoApplyProjectDetails` in [src/splitshot/browser/static/app.js](../src/splitshot/browser/static/app.js)
- PractiScore context drafting through `readPractiScoreContextPayload`, `syncPractiScoreSelectionFields`, `schedulePractiScoreContextApply`, and `autoApplyPractiScoreContext` in [src/splitshot/browser/static/app.js](../src/splitshot/browser/static/app.js)
- path and folder workflow through `pickPath`, `probeProjectFolder`, and `useProjectFolder` in [src/splitshot/browser/static/app.js](../src/splitshot/browser/static/app.js)
- hidden file input upload wiring through `openHiddenFileInput()` and the `#practiscore-file-input` / `#primary-file-input` change listeners in [src/splitshot/browser/static/app.js](../src/splitshot/browser/static/app.js)
- pre-action flush through `flushPendingProjectDrafts()` in [src/splitshot/browser/static/app.js](../src/splitshot/browser/static/app.js)

### Backend Wiring

- `/api/project/details` in [src/splitshot/browser/server.py](../src/splitshot/browser/server.py)
- `/api/project/practiscore`
- `/api/project/new`
- `/api/project/open`
- `/api/project/save`
- `/api/project/delete`
- `/api/project/probe`
- `/api/import/primary`
- `/api/files/practiscore`
- controller mutations centered in [src/splitshot/ui/controller.py](../src/splitshot/ui/controller.py) for project lifecycle, media ingest, and PractiScore state
- persisted output lands in project JSON via autosave after `project_changed`

### Tests

- static contract coverage in [tests/browser/test_browser_static_ui.py](../tests/browser/test_browser_static_ui.py)
- route and persistence coverage in [tests/browser/test_browser_control.py](../tests/browser/test_browser_control.py)
- PractiScore parsing and fallback coverage in [tests/analysis/test_practiscore_import.py](../tests/analysis/test_practiscore_import.py)
- project persistence behavior in [tests/persistence/test_persistence.py](../tests/persistence/test_persistence.py)

### WYSIWYG vs Function

Project is not a WYSIWYG pane in the visual sense. It is a coordinator pane. The visible controls look simple, but they trigger deep downstream state changes:

- primary import initializes analysis, media availability, waveform, split rows, and score defaults;
- PractiScore import initializes scoring context and imported-summary overlay behavior;
- project open/save/delete reset caches, path state, and persisted browser state.

Compared with the other panes, Project is the strongest dependency hub and the weakest visual truth surface. It can look healthy while a downstream pane is already out of sync.

### Risks

- typed draft state versus saved project state
- path chooser and project-folder probe mismatches
- imported PractiScore context reimport drift
- primary import side effects resetting other panes unexpectedly
- active-tool switching and project open/save flows re-rendering controls out of order

## Score Pane

The Score pane is a real editor. It owns shot-level score assignment, penalty counts, preset selection, and scoring-summary generation. It has high parity with the underlying state because edits round-trip directly through API calls and the controller recalculates the scoring summary immediately.

### Controls

- left-rail button `data-tool="scoring"` in [src/splitshot/browser/static/index.html](../src/splitshot/browser/static/index.html#L18)
- pane container `data-tool-pane="scoring"` in [src/splitshot/browser/static/index.html](../src/splitshot/browser/static/index.html#L204)
- `#scoring-enabled`
- `#scoring-preset`
- `#scoring-description`
- `#scoring-imported-caption`
- `#scoring-imported-summary`
- `#score-option-grid`
- `#scoring-shot-list`
- dynamically rendered per-shot controls: row toggle, score select, penalty inputs, restore button, delete button

### Client Wiring

- score option rendering via `renderScoreOptions()` in [src/splitshot/browser/static/app.js](../src/splitshot/browser/static/app.js)
- per-shot editor rendering via `renderScoringShotList()`
- field-penalty rendering via `renderScoringPenaltyFields()`
- preset rendering via `renderScoringPresetOptions()`
- scoring summary display via `renderPractiScoreSummaries()`
- direct API calls to `/api/scoring`, `/api/scoring/profile`, `/api/scoring/score`, `/api/scoring/restore`, and `/api/scoring/position`

### Backend Wiring

- scoring routes in [src/splitshot/browser/server.py](../src/splitshot/browser/server.py)
- controller methods for `set_scoring_enabled`, `set_penalties`, `set_penalty_counts`, `set_scoring_preset`, `assign_score`, `restore_original_shot_score`, and scoring-color persistence in [src/splitshot/ui/controller.py](../src/splitshot/ui/controller.py)
- actual calculation in [src/splitshot/scoring/logic.py](../src/splitshot/scoring/logic.py)

### Tests

- route/persistence coverage in [tests/browser/test_browser_control.py](../tests/browser/test_browser_control.py)
- static contract assertions in [tests/browser/test_browser_static_ui.py](../tests/browser/test_browser_static_ui.py)
- scoring-logic coverage in [tests/scoring/test_scoring_and_merge.py](../tests/scoring/test_scoring_and_merge.py)

### WYSIWYG vs Function

Score is one of the strongest true-editor panes. What the user changes is what the project state becomes. The biggest caveat is imported-stage precedence: once imported official results exist, the pane can still allow manual edits while parts of the summary remain driven by imported-stage aggregates.

Compared with Splits and Overlay, Score is less visually complex and therefore less likely to suffer preview/render drift, but it is more exposed to imported-data precedence confusion.

### Risks

- imported-stage aggregates versus manual shot edits
- preset-switch penalty-field compatibility
- score restore after re-analysis or shot mutation
- scoring-summary drift into Metrics if summary generation changes without pane updates

## Splits Pane

The Splits pane is half inspector and half timing editor. The compact inspector view is read-only except for threshold and selected-shot actions; the expanded timing workbench exposes the full edit surface. It is tightly coupled to the waveform, selected-shot state, and presentation-layer timing rows.

### Controls

- left-rail button `data-tool="timing"` in [src/splitshot/browser/static/index.html](../src/splitshot/browser/static/index.html#L19)
- pane container `data-tool-pane="timing"` in [src/splitshot/browser/static/index.html](../src/splitshot/browser/static/index.html#L177)
- compact controls: `#expand-timing`, `#timing-summary`, `#selected-shot-panel`, `#selected-timing-shot`, `#selected-shot-copy`, four `data-nudge` buttons, `#delete-selected`, `#timing-table`, `#threshold`
- expanded workbench controls: `#collapse-timing`, `#timing-event-kind`, `#timing-event-label`, `#timing-event-position`, `#add-timing-event`, `#timing-workbench-table`, `#timing-event-list`

### Client Wiring

- selection and video/waveform coupling via `selectShot()` in [src/splitshot/browser/static/app.js](../src/splitshot/browser/static/app.js)
- split-table rendering via `renderTimingTable()` and `renderTimingTables()`
- selected-shot narrative via `renderSelection()`
- split-row data lookup via `splitRowForShot()` and `resolvedSplitMsForShot()`
- threshold auto-apply via `scheduleThresholdApply()` and `autoApplyThreshold()`
- shot movement and deletion via `/api/shots/move`, `/api/shots/delete`, `/api/shots/select`
- timing-event editing via `addTimingEvent()`, `renderTimingEventEditor()`, and `renderTimingEventList()`
- expansion control via `setTimingExpanded()`

### Backend Wiring

- `compute_split_rows()` in [src/splitshot/timeline/model.py](../src/splitshot/timeline/model.py)
- `build_stage_presentation()` in [src/splitshot/presentation/stage.py](../src/splitshot/presentation/stage.py)
- state serialization in [src/splitshot/browser/state.py](../src/splitshot/browser/state.py)
- controller mutation methods in [src/splitshot/ui/controller.py](../src/splitshot/ui/controller.py) for threshold changes, shot movement, deletion, and event management

### Tests

- timing and presentation coverage in [tests/presentation/test_presentation.py](../tests/presentation/test_presentation.py)
- analysis/controller coverage in [tests/analysis/test_analysis.py](../tests/analysis/test_analysis.py)
- browser route and state coverage in [tests/browser/test_browser_control.py](../tests/browser/test_browser_control.py)
- static pane contract assertions in [tests/browser/test_browser_static_ui.py](../tests/browser/test_browser_static_ui.py)

### WYSIWYG vs Function

Splits is mostly WYSIWYG, but only if the user understands that compact view and expanded edit view are separate surfaces over the same timing model. The real authority is not the table DOM; it is the underlying `split_rows` and `timing_segments` projections built from shot state and timing events.

Compared with Score, Splits is more exposed to projection drift. Compared with Metrics, Splits is closer to the authoritative timing view.

### Risks

- `split_rows` versus `timing_segments` divergence
- selected-shot orphaning after delete or reanalysis
- threshold reanalysis replacing timing state under the current selection
- timing-event anchors becoming invalid after shot deletion
- waveform and table selection getting out of sync

## PiP Pane

The PiP pane edits merge media state, but its WYSIWYG fidelity is layout-dependent. PiP layout has the richest preview parity; side-by-side and above-below are more state-editor surfaces than preview-accurate surfaces.

### Controls

- left-rail button `data-tool="merge"` in [src/splitshot/browser/static/index.html](../src/splitshot/browser/static/index.html#L20)
- pane container `data-tool-pane="merge"` in [src/splitshot/browser/static/index.html](../src/splitshot/browser/static/index.html#L349)
- `#sync-offset`
- `#add-merge-media`
- hidden `#merge-media-input`
- `#merge-enabled`
- `#merge-layout`
- `#pip-size`
- `#pip-size-label`
- `#pip-x`
- `#pip-y`
- `#merge-media-list`
- dynamic per-source controls: remove button, per-source size, x, y, sync nudges, sync label

### Client Wiring

- merge media import via hidden file input and `/api/files/merge` / `/api/import/merge`
- card rendering via `renderMergeMediaList()` in [src/splitshot/browser/static/app.js](../src/splitshot/browser/static/app.js)
- local preview sync via `syncSecondaryPreview()` and `scheduleSecondaryPreviewSync()`
- PiP preview rendering via `renderMergePreviewLayer()`
- per-source preview updates via `previewSourceUpdate()` and `scheduleMergeSourceCommit()`
- sync nudges via `/api/merge/source` with delta payloads
- drag-to-place preview interaction on PiP preview items

### Backend Wiring

- `/api/merge`, `/api/merge/source`, `/api/merge/remove`, `/api/import/merge`, `/api/files/merge` in [src/splitshot/browser/server.py](../src/splitshot/browser/server.py)
- merge-source creation, removal, sync-offset updates, and persistence in [src/splitshot/ui/controller.py](../src/splitshot/ui/controller.py)
- merge-canvas math in [src/splitshot/merge/layouts.py](../src/splitshot/merge/layouts.py)
- export-side merge serialization in [src/splitshot/export/pipeline.py](../src/splitshot/export/pipeline.py)

### Tests

- static contract assertions in [tests/browser/test_browser_static_ui.py](../tests/browser/test_browser_static_ui.py)
- browser route persistence coverage in [tests/browser/test_browser_control.py](../tests/browser/test_browser_control.py)
- merge-layout logic tests in [tests/scoring/test_scoring_and_merge.py](../tests/scoring/test_scoring_and_merge.py)
- export merge-path tests in [tests/export/test_export.py](../tests/export/test_export.py)

### WYSIWYG vs Function

PiP is only fully WYSIWYG in PiP mode. The preview and persisted state are closest there. In side-by-side and above-below, some controls are still valid state but have weak or no meaningful live preview equivalent.

Compared with Overlay and Review, PiP has a larger preview/export split because browser playback preview and backend export composition are different systems.

### Risks

- live preview sync versus persisted sync-offset state
- drag interactions not committed before export or autosave
- no strong preview feedback for non-PiP layout-specific state
- per-source merge state diverging from what the user thinks export will do

## Overlay Pane

The Overlay pane is the main badge-style and positioning editor. It drives live overlay badge rendering and exported overlay styling, but preview and export use different rendering engines, so parity depends on keeping the serializers and render math in lockstep.

### Controls

- left-rail button `data-tool="overlay"` in [src/splitshot/browser/static/index.html](../src/splitshot/browser/static/index.html#L21)
- pane container `data-tool-pane="overlay"` in [src/splitshot/browser/static/index.html](../src/splitshot/browser/static/index.html#L222)
- sizing/style controls: `#badge-size`, `#overlay-style`, `#overlay-spacing`, `#overlay-margin`
- stack/placement controls: `#max-visible-shots`, `#shot-quadrant`, `#shot-direction`, `#overlay-custom-x`, `#overlay-custom-y`
- timer controls: `#timer-x`, `#timer-y`, `#timer-lock-to-stack`
- draw controls: `#draw-x`, `#draw-y`, `#draw-lock-to-stack`
- score controls: `#score-x`, `#score-y`, `#score-lock-to-stack`
- bubble sizing: `#bubble-width`, `#bubble-height`
- font controls: `#overlay-font-family`, `#overlay-font-size`, `#overlay-font-bold`, `#overlay-font-italic`
- dynamic style grids: `#badge-style-grid`, `#score-color-grid`
- shared visibility toggles live in Review but mutate the same overlay state: `#show-timer`, `#show-draw`, `#show-shots`, `#show-score`, `#review-lock-to-stack`

### Client Wiring

- overlay payload reading via `readOverlayPayload()` in [src/splitshot/browser/static/app.js](../src/splitshot/browser/static/app.js)
- local preview sync via `syncOverlayPreviewStateFromControls()`, `previewOverlayControlChanges()`, and `scheduleOverlayApply()`
- color picker and delayed color commit via `openColorPicker()`, `bindOverlayColorInput()`, and `scheduleOverlayColorCommit()`
- text-box field normalization via `setOverlayTextBoxField()` and related helpers
- drag handling for timer/draw/score badges via `beginOverlayBadgeDrag()`, `moveOverlayBadgeDrag()`, and `endOverlayBadgeDrag()`
- live stage rendering via `renderLiveOverlay()` and overlay frame scheduling

### Backend Wiring

- `/api/overlay` in [src/splitshot/browser/server.py](../src/splitshot/browser/server.py)
- controller overlay methods in [src/splitshot/ui/controller.py](../src/splitshot/ui/controller.py): position, badge size, layout, display options, badge style, scoring colors
- export-side rendering in [src/splitshot/overlay/render.py](../src/splitshot/overlay/render.py)

### Tests

- static contract coverage in [tests/browser/test_browser_static_ui.py](../tests/browser/test_browser_static_ui.py)
- browser route persistence in [tests/browser/test_browser_control.py](../tests/browser/test_browser_control.py)
- export/render parity coverage in [tests/export/test_export.py](../tests/export/test_export.py)

### WYSIWYG vs Function

Overlay is intended to be high-WYSIWYG, but it is not self-sufficient. Live preview uses browser DOM rendering, while export uses backend overlay rendering. That means overlay parity is a contract that has to be maintained, not an automatic property.

Compared with Review, Overlay is the primary badge-style surface. Compared with Export, Overlay is the visual editor that Export depends on.

### Risks

- serializer drift between browser overlay payload and backend renderer
- color picker delayed-commit behavior
- lock-to-stack state versus explicit coordinates
- score-token color persistence versus live badge display
- overlay preview looking correct while exported output differs by font, bubble sizing, or position

## Review Pane

The Review pane is a text-box editor over shared overlay state. It is not independent from Overlay. It exists to manage review notes and imported-summary boxes with stage-visible WYSIWYG behavior and export parity.

### Controls

- left-rail button `data-tool="review"` in [src/splitshot/browser/static/index.html](../src/splitshot/browser/static/index.html#L22)
- pane container `data-tool-pane="review"` in [src/splitshot/browser/static/index.html](../src/splitshot/browser/static/index.html#L130)
- shared visibility toggles: `#show-timer`, `#show-draw`, `#show-shots`, `#show-score`
- `#review-lock-to-stack`
- text-box manager buttons: `#review-add-text-box`, `#review-add-imported-box`
- `#review-text-box-list`
- dynamic per-box card controls: enable, source, text, quadrant, x, y, width, height, background color, text color, opacity, duplicate, remove

### Client Wiring

- text-box list rendering via `renderTextBoxEditors()` in [src/splitshot/browser/static/app.js](../src/splitshot/browser/static/app.js)
- box creation via `addOverlayTextBox()` and associated helpers
- field updates via `setOverlayTextBoxField()` and `updateOverlayTextBox()`
- on-stage drag-to-custom-position through `beginTextBoxDrag()`, `moveTextBoxDrag()`, and `endTextBoxDrag()`
- live rendering through `renderLiveOverlay()` using `visibleOverlayTextBoxEntries()`
- scroll preservation around re-renders through the inspector scroll-state helpers

### Backend Wiring

- no dedicated Review API; Review writes through shared `/api/overlay`
- shared state stored in `project.overlay.text_boxes` and `project.overlay.review_boxes_lock_to_stack`
- export reads the same text-box state through the overlay rendering pipeline

### Tests

- static contract assertions in [tests/browser/test_browser_static_ui.py](../tests/browser/test_browser_static_ui.py)
- shared overlay persistence coverage in [tests/browser/test_browser_control.py](../tests/browser/test_browser_control.py)
- export-side overlay rendering checks in [tests/export/test_export.py](../tests/export/test_export.py)

### WYSIWYG vs Function

Review has strong visual parity for what it edits, but it is a second editor surface over overlay text-box state. That is its defining relationship problem. If Review and Overlay normalize or serialize text boxes differently, Review can look broken while Overlay still seems partly correct, or vice versa.

Compared with Overlay, Review is narrower in scope but more fragile because it depends on imported-summary behavior and custom text-box normalization.

### Risks

- shared text-box state drift with Overlay
- imported-summary availability and defaults
- lock-to-stack toggling not matching user expectations after drag
- inspector scroll reset during overlay round trips
- drag-state cleanup failures leaving stale interaction state

## Export Pane

The Export pane is not a preview pane. It owns export settings and the export log surface, but it snapshots scoring, overlay, merge, and other pane state at export time and hands the job to the backend render pipeline.

### Controls

- left-rail button `data-tool="export"` in [src/splitshot/browser/static/index.html](../src/splitshot/browser/static/index.html#L23)
- pane container `data-tool-pane="export"` in [src/splitshot/browser/static/index.html](../src/splitshot/browser/static/index.html#L383)
- preset/path controls: `#export-preset`, `#export-preset-description`, `#export-path`, `#browse-export-path`
- layout/settings: `#quality`, `#aspect-ratio`, `#target-width`, `#target-height`
- codec settings: `#frame-rate`, `#video-codec`, `#video-bitrate`, `#audio-codec`, `#audio-sample-rate`, `#audio-bitrate`, `#color-space`
- FFmpeg options: `#ffmpeg-preset`, `#two-pass`
- actions/log UI: `#export-video`, `#show-export-log`, `#export-log-modal`, `#export-log-output`, `#export-log-summary`, `#export-log-error`, `#export-log-status`, `#export-export-log`, `#close-export-log`

### Client Wiring

- preset option rendering via `renderExportPresetOptions()` in [src/splitshot/browser/static/app.js](../src/splitshot/browser/static/app.js)
- export-path draft handling via `syncExportPathControl()`
- debounced export layout/settings apply via `scheduleExportLayoutApply()` and `scheduleExportSettingsApply()`
- payload construction via `buildExportPayload()`
- pre-export flush through `cancelPendingExportDrafts()` and `flushPendingProjectDrafts()`
- live log/progress handling through activity-log consumption and `renderExportLog()`
- modal helpers `openExportLogModal()`, `closeExportLogModal()`, and log download helper `downloadExportLog()`

### Backend Wiring

- `/api/export/settings`, `/api/export/preset`, and `/api/export` in [src/splitshot/browser/server.py](../src/splitshot/browser/server.py)
- export-setting persistence in [src/splitshot/ui/controller.py](../src/splitshot/ui/controller.py)
- actual rendering in [src/splitshot/export/pipeline.py](../src/splitshot/export/pipeline.py)
- output path, last log, and last error persisted in project export state

### Tests

- static contract assertions in [tests/browser/test_browser_static_ui.py](../tests/browser/test_browser_static_ui.py)
- route/persistence coverage in [tests/browser/test_browser_control.py](../tests/browser/test_browser_control.py)
- render pipeline coverage in [tests/export/test_export.py](../tests/export/test_export.py)

### WYSIWYG vs Function

Export is explicitly not WYSIWYG. It is a render launcher and state snapshotter. If the product feels broken because preview and output differ, Export may be correct as an orchestrator while another pane's preview parity contract has already failed.

Compared with every other pane except Project, Export is the least visually truthful and the most dependent on complete cross-pane state flushes.

### Risks

- stale pending draft state at export time
- export path draft drift
- preset/custom-mode ambiguity
- render output reflecting a different snapshot than the user thinks is on screen
- export log persistence making old failures look current

## Metrics Pane

The Metrics pane is a synthesized read-only dashboard. It does not own mutations. It depends on the timing and scoring projections staying internally consistent.

### Controls

- left-rail button `data-tool="metrics"` in [src/splitshot/browser/static/index.html](../src/splitshot/browser/static/index.html#L24)
- pane container `data-tool-pane="metrics"` in [src/splitshot/browser/static/index.html](../src/splitshot/browser/static/index.html#L154)
- `#metrics-summary-grid`
- `#metrics-trend-list`
- `#metrics-score-status`
- `#metrics-score-summary`
- `#metrics-export-csv`
- `#metrics-export-text`

### Client Wiring

- metrics row synthesis via `buildMetricsRows()` in [src/splitshot/browser/static/app.js](../src/splitshot/browser/static/app.js)
- full pane render via `renderMetricsPanel()`
- file export via `buildMetricsCsv()`, `buildMetricsText()`, and `exportMetrics()`

### Backend Wiring

- browser-state assembly through [src/splitshot/browser/state.py](../src/splitshot/browser/state.py)
- timing metrics from [src/splitshot/presentation/stage.py](../src/splitshot/presentation/stage.py) and [src/splitshot/timeline/model.py](../src/splitshot/timeline/model.py)
- scoring summary from [src/splitshot/scoring/logic.py](../src/splitshot/scoring/logic.py)

### Tests

- browser-state metrics coverage in [tests/browser/test_browser_control.py](../tests/browser/test_browser_control.py)
- static contract checks in [tests/browser/test_browser_static_ui.py](../tests/browser/test_browser_static_ui.py)
- analysis/presentation coverage in [tests/analysis/test_analysis.py](../tests/analysis/test_analysis.py) and [tests/presentation/test_presentation.py](../tests/presentation/test_presentation.py)

### WYSIWYG vs Function

Metrics is only as trustworthy as the projections it consumes. It is visually clean but not authoritative by itself. If Splits, Score, and imported-stage summary generation disagree, Metrics will faithfully show whichever derived data path it was coded to trust, which may not be what the user expects.

Compared with all other panes, Metrics is the purest projection surface and the one most likely to look fine while actually reflecting a deeper data drift upstream.

### Risks

- synthesized `split_rows` + `timing_segments` join drift
- stale imported-stage scoring context
- beep-null edge cases
- confidence values lagging reanalysis changes
- export files matching the pane while the pane itself is already reflecting stale derived data

## Likely Breakage Axes

If the left-rail page relationships worked for several days and now feel broken, these are the highest-value code paths to inspect first.

### Shared Overlay State

Review and Overlay both mutate shared overlay fields and shared text-box state in [src/splitshot/browser/static/app.js](../src/splitshot/browser/static/app.js) and [src/splitshot/ui/controller.py](../src/splitshot/ui/controller.py). If one pane normalizes a field differently, the other pane will appear to "lose" changes.

### Derived Timing State

Splits, waveform, Metrics, and parts of Overlay timing text all depend on `split_rows`, `timing_segments`, and metrics built from timing state. If the presentation pipeline changes in [src/splitshot/timeline/model.py](../src/splitshot/timeline/model.py) or [src/splitshot/presentation/stage.py](../src/splitshot/presentation/stage.py) without matching browser updates, pane relationships break.

### Draft Flush And Debounce

Project, Overlay, Merge, Scoring, and Export all use debounced apply flows in [src/splitshot/browser/static/app.js](../src/splitshot/browser/static/app.js). If a cross-pane action happens before all drafts flush, the next pane can render from stale state.

### Preview Versus Export Renderer

Overlay and PiP preview behavior are browser-side; final export rendering is backend-side. If parity logic drifts between [src/splitshot/browser/static/app.js](../src/splitshot/browser/static/app.js), [src/splitshot/overlay/render.py](../src/splitshot/overlay/render.py), and [src/splitshot/export/pipeline.py](../src/splitshot/export/pipeline.py), the product feels inconsistent even if each individual subsystem still "works" on its own terms.

### Active Tool And UI State Restore

Tool activation and UI-state restore are centralized in [src/splitshot/browser/static/app.js](../src/splitshot/browser/static/app.js). If `active_tool`, expanded timing/waveform state, or selected-shot state reapply out of order, one pane can look like it is resetting another.

## Fastest Triage Order

For a current regression involving pane-to-pane WYSIWYG/function mismatch, check these files first:

1. [src/splitshot/browser/static/app.js](../src/splitshot/browser/static/app.js)
2. [src/splitshot/browser/server.py](../src/splitshot/browser/server.py)
3. [src/splitshot/ui/controller.py](../src/splitshot/ui/controller.py)
4. [src/splitshot/browser/state.py](../src/splitshot/browser/state.py)
5. [src/splitshot/timeline/model.py](../src/splitshot/timeline/model.py)
6. [src/splitshot/presentation/stage.py](../src/splitshot/presentation/stage.py)
7. [src/splitshot/overlay/render.py](../src/splitshot/overlay/render.py)
8. [src/splitshot/export/pipeline.py](../src/splitshot/export/pipeline.py)

Then validate the browser contract with:

```bash
uv run python -m pytest tests/browser
```

If a change touched live overlay or PiP parity, run the relevant browser audit scripts from [docs/DEVELOPING.md](DEVELOPING.md).

**Last updated:** 2026-04-18
**Referenced files last updated:** 2026-04-18