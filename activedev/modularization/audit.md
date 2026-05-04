# Modularization Audit Directions

Audit answers a different question than validation.

- **Validation:** does the app still work exactly the same?
- **Audit:** did the internal architecture actually improve according to the modularization design?

Both are required.

## Global structural rules

1. Pane modules must not import directly from other pane modules.
2. Shared behavior must move through backbone modules or shared components/widgets.
3. `app.js` must shrink over time toward bootstrap-only responsibility.
4. Legacy globals may remain temporarily only when the active task packet allows them as compatibility shims.
5. New module boundaries must align with `activedev/modular.md` and this program plan.
6. CSS splitting happens late; do not scatter styles early unless the task explicitly owns that work.
7. Zero UX drift remains in force even if validation passes.

## Ownership and overlap rules

A task run fails audit if it:

- edits a file not listed in the task's `touches-files`
- edits a file listed in the task's `forbidden-files`
- modifies another task's owned shared-test assertions without explicit handoff
- changes a hotspot while that hotspot is claimed by another active task

`progress.md` is the source of truth for active claims.

## Mandatory audit checks by phase

### Governance and baseline tasks (`T00`–`T02`)

- required control-plane files exist
- task ids and naming are consistent across `plan.md`, `progress.md`, task files, and proof files
- missing QA docs are either restored (`T02`) or explicitly recorded as blockers before code extraction begins

### Extraction tasks (`T03`–`T09E`)

- module boundaries match the assigned task
- no prohibited cross-pane imports were introduced
- owned tests/docs were updated in the same run when required
- compatibility shims are documented, not accidental
- `app.js` responsibility moved in the intended direction

### Cleanup and certification tasks (`T10`–`T12`)

- retired monolith paths are actually removed
- no ghost wrappers remain without purpose
- CSS is organized into the planned structure without selector drift
- final static asset layout supports future PWA shell work

## Suggested command checks

Use the smallest relevant subset for the task and record results in the proof file.

```text
wc -l src/splitshot/browser/static/app.js
find src/splitshot/browser/static -maxdepth 2 -type f | sort
rg 'from "\.\./panes/|from "\.\/.*pane' src/splitshot/browser/static/panes -g '*.js'
rg '^let ' src/splitshot/browser/static/app.js
```

The exact command list can expand once `T01` captures the ownership anchors.

## Shared hotspot audit map

| Hotspot | Audit owner expectations |
| --- | --- |
| `index.html` | only `T03` and later `T11` may touch shell/module/css wiring |
| `app.js` | active extraction task may touch only its owned anchor blocks |
| `styles.css` | remains single-owner until `T11` |
| shared browser tests | task packet must state which assertions or sections it owns |
| QA matrix/coverage docs | keep synchronized with test claims and control inventory |

## Ownership appendix

`T01` must update this section before `T03` starts.

### Required additions from `T01`

- exact current ownership anchors or line-range notes for `app.js`
- exact current ownership anchors or line-range notes for `index.html`
- exact current ownership anchors or selector blocks for `styles.css`
- exact mapping of shared test sections to `T09B`, `T09C`, `T09D`, and `T09E`

### Current state

Audited on `2026-05-02`. No new `T01` blocker is recorded beyond the existing `T02`
dependency gate for `T03`.

#### `app.js` exact anchors (`src/splitshot/browser/static/app.js`)

| Planned owner | Exact anchors / line notes | Scope note |
| --- | --- | --- |
| `T03` | `setActiveTool()` line 6076; `render()` lines 12731–12747; `renderViewportLayout()` line 12748; `wireEvents()` lines 13763–14376 | Bootstrap shell, tool activation, monolith switchboard, and final module wiring seam |
| `T04` | file prologue lines 1–292; shared helpers from `splitSeconds()` line 570 through `endTimingColumnResize()` line 1742; project-ui-state normalization `normalizeProjectUiState()` line 1757 through `applyProjectUiState()` line 1861 | Backbone-core extraction candidates (`utils`, state helpers, shared selection plumbing) |
| `T05` | activity/runtime helpers `flushActivityQueue()` line 406 through `beginProcessing()` line 1537; layout/runtime helpers `applyLayoutState()` line 5934 through `endLayoutResize()` line 6051; `api()` line 6178; `callApi()` line 6201; `applyRemoteState()` line 6376; PractiScore session/route payload helpers lines 6713–6719 | Backbone-runtime extraction candidates (`activity`, `processing`, `layout`, `api`) |
| `T06` | `renderHeader()` line 7015; `renderStats()` line 7039; `renderVideo()` line 7483 | Shared shell/status/video component seam |
| `T07` | `renderWaveformNavigator()` line 6943; `renderWaveformPlayhead()` line 7774; `renderWaveform()` line 7794; `renderWaveformShotList()` line 8103; waveform pointer handlers `handleWaveformPointerDown/Move/Up()` lines 12929–12976 | Waveform component seam; coordinate with `T09E` on timing-selection assertions |
| `T08` | `setScoringWorkbenchExpanded()` line 8673; `renderScoringTable()` line 8862; `renderScoringTables()` line 8989; `renderScoringPresetOptions()` line 8995; `renderScoringPresetDescription()` line 9017; `renderPractiScoreSummaries()` line 9023; `readScoringPayload()` line 13167; `applyScoringSettings()` line 13563; `scheduleScoringApply()` line 13684 | Pilot scoring-pane extraction seam |
| `T09A` | `renderSettingsSections()` line 2731; `renderSettingsLayerSummary()` line 7244; `renderSettingsPane()` line 7269; `setMetricsSectionExpanded()` line 9996; `renderMetricsSections()` line 10000; `renderMetricsPanel()` line 10111; `buildMetricsCsv()` line 10189; `buildMetricsText()` line 10350; `exportMetrics()` line 10396; `setMetricsExpanded()` line 12893 | Settings + metrics pane lane |
| `T09B` | project/practiscore anchors: `normalizeProjectNameValue()` line 293, `readProjectUiStatePayload()` line 1815, `syncLocalProjectUiState()` line 1855, `openPractiScoreDashboard()` line 6220, `renderPractiScoreSelect()` line 6778, `renderPractiScoreOptionLists()` line 6800, `readProjectDetailsPayload()` line 13108, `readPractiScoreContextPayload()` line 13115, `useProjectFolder()` line 13506, `scheduleProjectDetailsApply()` line 13631, `schedulePractiScoreContextApply()` line 13637, `scheduleProjectUiStateApply()` line 13641; merge anchors: `setMergeSourceExpanded()` line 1967, `syncMergePreviewStateFromControls()` line 2469, `renderMergePreviewLayer()` line 7414, `renderMergeMediaList()` line 10775, `readMergePayload()` line 13149, `scheduleMergeApply()` line 13668 | Project + merge lane; must preserve PractiScore fallback/local controls and parity contract |
| `T09C` | review/editor anchors: `createOverlayTextBoxId()` line 2063, `overlayTextBoxAutoSize()` line 2069, `resolvedOverlayTextBoxSize()` line 2079, `syncOverlayTextBoxSizeControls()` line 2092, `overlayTextBoxes()` line 2146, `preferredLegacyTextBox()` line 2176, `setLocalOverlayTextBoxes()` line 2201, `applyOverlayTextBoxUpdate()` line 2231, `setOverlayTextBoxField()` line 2249, `setReviewTextBoxExpanded()` line 2646, `scheduleReviewStageRestore()` line 6578; export anchors: `renderExportPresetOptions()` line 9075, `renderExportLog()` line 9098, `openExportLogModal()` line 9139, `closeExportLogModal()` line 9148, `downloadExportLog()` line 9154, `syncExportPathControl()` line 10408, `readExportLayoutPayload()` line 13160, `readExportSettingsPayload()` line 13175, `scheduleExportLayoutApply()` line 13672, `scheduleExportSettingsApply()` line 13678 | Export + review lane; owns editor-side text-box state and export controls |
| `T09D` | overlay anchors: `overlayHexControlFor()` line 1244, `syncOverlayFontSizePreset()` line 2050, `scheduleOverlayColorCommit()` line 2434, `renderCustomOverlayBoxes()` line 11812, `beginOverlayBadgeDrag()` line 12144, `renderLiveOverlay()` line 12500, `readOverlayPayload()` line 13021, `scheduleOverlayApply()` line 13663; ShotML anchors: `setShotMLSectionExpanded()` line 2659, `readShotMLSettingsPayload()` line 10435, `renderShotMLProposals()` line 10481, `renderShotML()` line 10532, `scheduleThresholdApply()` line 13616, `applyThresholdNow()` line 13621, `scheduleShotMLSettingsApply()` line 13627 | Overlay + ShotML lane; owns live preview renderer, overlay drag/color state, and ShotML controls |
| `T09E` | markers anchors: `createPopupBubbleId()` line 2945, `setPopupBubbleExpanded()` line 3471, `renderPopupEditorSectionToggles()` line 3497, `renderPopupFloatingEditor()` line 5475, `readPopupTemplatePayload()` line 5554, `renderPopupTimeline()` line 5573, `setPopupFilterMode()` line 5622, `renderMarkersWorkbench()` line 5663, `renderPopupEditors()` line 5750, `beginPopupBubbleDrag()` line 11979, `visiblePopupBubbles()` line 12311, `renderPopupKeyframeOverlay()` line 12343, `renderPopupOverlay()` line 12396; timing anchors: `applyTimingTableColumns()` line 1696, `renderTimingEventList()` line 8158, `renderTimingEventEditor()` line 8197, `renderTimingTable()` line 8524, `renderTimingTables()` line 8662, `setMarkersExpanded()` line 8701, `setTimingExpanded()` line 12878 | Markers + timing lane; coordinate with `T07` on waveform pointer math and selection plumbing |
| `T10` | cleanup of compatibility wrappers and retired monolith scaffolding after all extraction lanes land, especially `render()` and `wireEvents()` | Cleanup-only task; no early ownership |

#### `index.html` exact line ranges (`src/splitshot/browser/static/index.html`)

| Lines | Area | Planned owner | Notes |
| --- | --- | --- | --- |
| 1–10 | head + stylesheet wiring | `T03` until cleanup; `T11` may only rewrite stylesheet wiring | Keep existing labels, ids, and copy frozen |
| 11–62 | rail / tool nav / footer controls | `T03`/`T10` shell ownership | Pane lanes must not edit rail labels, order, or ids |
| 63–103 | review stack / video stage / waveform host | `T06`/`T07` shared shell-components seam | Pane lanes consume this host but do not restructure it |
| 104–128 | timing workbench | `T09E` | Expanded timing editor shell |
| 129–138 | metrics workbench | `T09A` | Expanded metrics workbench shell |
| 139–146 | scoring workbench | `T08` | Pilot-pane workbench shell |
| 147–189 | markers workbench | `T09E` | Expanded markers editor shell |
| 190–218 | review pane | `T09C` | Review-pane markup only |
| 219–245 | metrics pane | `T09A` | Metrics-pane markup only |
| 246–261 | timing pane | `T09E` | Timing-pane markup only |
| 262–425 | ShotML pane | `T09D` | ShotML-pane markup only |
| 426–551 | overlay pane | `T09D` | Overlay-pane markup only |
| 552–583 | markers pane | `T09E` | Markers-pane markup only |
| 584–620 | merge pane | `T09B` | Merge-pane markup only |
| 621–720 | export pane | `T09C` | Export-pane markup only |
| 721–1068 | settings pane | `T09A` | Settings-pane markup only |
| 1069–1191 | project pane | `T09B` | Project-pane + PractiScore contract markup |
| 1192–1194 | script bootstrap tag | `T03`; later `T10` cleanup | Module-switch seam |

#### `styles.css` exact selector / range map (`src/splitshot/browser/static/styles.css`)

`styles.css` remains single-owner until `T11`. The ranges below are the verified split anchors that `T11` must preserve while later pane tasks treat them as read-only reference only.

| Lines | Selector anchors | Planned owner | Notes |
| --- | --- | --- | --- |
| 1–248 | `:root` and shared global tokens/base rules | `T11` only | Theme variables and shared element defaults |
| 249–490 | `.cockpit-shell`, `.tool-rail`, rail footer/button rules | `T11` only | Shell/rail layout block |
| 491–558 | `.status-bar*` | `T11` only | Shared shell status/header styling |
| 559–732 | `.review-grid`, `.review-stack`, `.resize-handle-*` | `T11` only | Shared stage/inspector/waveform layout seam |
| 733–1132 | `.video-stage`, `.merge-preview-*`, `.live-overlay`, `.popup-overlay` | `T11` only | Functionally referenced by `T07`, `T09B`, `T09D`, and `T09E` |
| 1133–1327 | `.waveform-panel`, `.timing-event-*` | `T11` only | Functionally referenced by `T07` and `T09E` |
| 1328–1660 | `.inspector-*`, `.tool-pane` | `T11` only | Shared pane-shell styling |
| 1661–3132 | `.shotml-section`, `.settings-section` and descendants | `T11` only | Functionally referenced by `T09A` and `T09D` |
| 3133–4204 | `.metrics-*` | `T11` only | Metrics styling block |
| 4205–4236 | `.review-visibility-manager` and late pane-specific controls | `T11` only | Functionally referenced by `T09C`, `T09D`, and `T09E` |
| 4237–4587 | responsive rules | `T11` only | Final layout/media-query block |

#### Shared browser test ownership map

| File | Lines | Default owner | Assertion scope |
| --- | --- | --- | --- |
| `tests/browser/test_merge_export_contracts.py` | 44–188 | `T09B` | merge/export freshness seam + merge-source persistence |
| `tests/browser/test_merge_export_contracts.py` | 189–236 | `T09C` | export path preset/custom-mode persistence |
| `tests/browser/test_overlay_review_contracts.py` | 31–121 | `T09D` | overlay payload defaults, locked-coordinate renderer behavior |
| `tests/browser/test_overlay_review_contracts.py` | 122–259 | `T09C` | review text-box lock/auto-size assertions |
| `tests/browser/test_overlay_review_contracts.py` | 260–496 | `T09E` | popup-bubble text, score, and motion-path contracts |
| `tests/browser/test_overlay_review_contracts.py` | 497–541 | `T09D` | overlay/review payload-sync and drag-cleanup seam |
| `tests/browser/test_overlay_review_contracts.py` | 562–615 | `T09C` | imported-summary source visibility + review unlock/drag contract |
| `tests/browser/test_overlay_review_contracts.py` | 616–631 | `T09D` | overlay mode-switch baseline seeding |
| `tests/browser/test_browser_interactions.py` | 286–384 | `T09B` | project-pane + PractiScore browser interaction flow |
| `tests/browser/test_browser_interactions.py` | 566–665 | `T09D` | overlay visibility and badge-toggle browser flow |
| `tests/browser/test_browser_interactions.py` | 666–1192 | `T09C` | review text-box authoring/editor interactions |
| `tests/browser/test_browser_interactions.py` | 1193–2183 | `T09E` | markers import, marker editor, motion-path generation, and marker selection flow |
| `tests/browser/test_browser_interactions.py` | 2184–2348 | `T09D` | ShotML threshold/settings interaction flow |
| `tests/browser/test_browser_interactions.py` | 2349–2542 | `T09B` | merge preview layout / PiP controls |
| `tests/browser/test_browser_interactions.py` | 2543–2867 | `T09E` | time-marker list, stage no-create guard, popup marker editing, workbench hide/show |
| `tests/browser/test_browser_interactions.py` | 2868–3213 | `T09D` | overlay color, position, and font controls |
| `tests/browser/test_browser_interactions.py` | 3214–3351 | `T09C` | export log modal and export settings controls |
| `tests/browser/test_project_lifecycle_contracts.py` | 66–336 | `T09B` | project lifecycle + PractiScore contract assertions |
| `tests/browser/test_timing_waveform_contracts.py` | 21–183 | `T07` | waveform/timing shared selection plumbing |
| `tests/browser/test_timing_waveform_contracts.py` | 184–324 | `T09E` | timing workbench row and timing-event controls |

#### Boundary notes

- `T09C` / `T09D` seam: review text-box editor/state helpers stay with `T09C`; live overlay rendering, overlay drag math, and overlay color/font preview assertions stay with `T09D`. If one change spans both zones, only one active task may claim `app.js` and the shared tests for that run.
- `T07` / `T09E` seam: waveform pointer math and shared selection resolution stay with `T07` until timing extraction reaches the workbench/table layer; `T09E` owns the timing rows/events assertions at `tests/browser/test_timing_waveform_contracts.py` lines 184–324.
- Missing QA-doc status is verified and explicitly handed to `T02`; `T03` remains gated by that existing dependency, not by a new `T01` ambiguity.

## PWA-readiness audit targets

Modularization is successful only if the resulting structure makes future PWA work straightforward. The audit should verify that the architecture now supports:

- a module-based application shell
- clean static asset boundaries suitable for precache lists
- isolated storage and file-loading seams
- centralized browser API and state coordination
- deployment-friendly static organization for a later `manifest.json`, `sw.js`, and Cloudflare Pages hosting model

## Proof requirements

Every audit run recorded in a proof file must state:

- which audit checks were executed
- whether ownership boundaries were respected
- whether any compatibility shim remains intentionally
- whether architectural drift or overlap was detected
- whether the task passed audit, passed with risk, or failed
