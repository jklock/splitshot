# PROOF-T09C-run1

- Task: `T09C` — Export and review panes
- Date: `2026-05-03`
- Owner: `copilot-orchestrator-20260503-t09c-run1`
- Validation tier: `Tier C` (task packet override: exact required command was `uv run pytest tests/browser/test_merge_export_contracts.py tests/browser/test_overlay_review_contracts.py tests/browser/test_browser_interactions.py`)
- Result: `pass`

## Scope completed

- Created the T09C-owned pane modules:
  - `src/splitshot/browser/static/panes/export-pane.js`
  - `src/splitshot/browser/static/panes/review-pane.js`
- Rewired the T09C-owned export/review anchors in `src/splitshot/browser/static/app.js` so the monolith now delegates pane-owned behavior through the extracted modules instead of owning the export preset/log helpers and review text-box editor logic inline.
- Preserved the existing browser/global compatibility surface by keeping the legacy `app.js` function names as thin delegates, including:
  - Review wrappers: `createOverlayTextBoxId()`, `overlayTextBoxAutoSize()`, `resolvedOverlayTextBoxSize()`, `syncOverlayTextBoxSizeControls()`, `normalizeOverlayTextBox()`, `overlayTextBoxes()`, `preferredLegacyTextBox()`, `syncLegacyOverlayBoxState()`, `setLocalOverlayTextBoxes()`, `buildOverlayTextBox()`, `overlayTextBoxLabel()`, `applyOverlayTextBoxUpdate()`, `updateOverlayTextBox()`, `setOverlayTextBoxField()`, `addOverlayTextBox()`, `duplicateOverlayTextBox()`, `removeOverlayTextBox()`, `overlayTextBoxDisplayText()`, `overlayTextBoxHint()`, `isReviewTextBoxExpanded()`, `setReviewTextBoxExpanded()`, `buildTextBoxCard()`, `renderTextBoxEditors()`, `restoreReviewStage()`, and `scheduleReviewStageRestore()`.
  - Export wrappers: `renderExportPresetOptions()`, `renderExportLog()`, `openExportLogModal()`, `closeExportLogModal()`, `downloadExportLog()`, `syncExportPathControl()`, `readExportLayoutPayload()`, `readExportSettingsPayload()`, `scheduleExportLayoutApply()`, and `scheduleExportSettingsApply()`.
- Updated the owned review source-contract coverage in `tests/browser/test_overlay_review_contracts.py` so the moved review text-box/editor assertions now point at `review-pane.js` while still asserting the delegation seam remains visible in `app.js`.
- Preserved the exact export trigger/order and overlay-adjacent workflows with no UX drift; the required runtime browser suites in `tests/browser/test_merge_export_contracts.py` and `tests/browser/test_browser_interactions.py` passed unchanged.

## Compatibility seams intentionally retained for T09D/T10

The following seams intentionally remain in `src/splitshot/browser/static/app.js`:

- `readOverlayPayload()` and the overlay render/drag math remain app-owned because they are the `T09D` stabilization seam and still coordinate review text boxes with overlay placement/rendering.
- The export button click handler, `buildExportPayload()`, and `cancelPendingExportDrafts()` remain app-owned so the exact export-order contract stays source-visible in `app.js`.
- `beginProcessing()` and `clearCurrentExportLogState()` retain the source-visible export-log reset anchors required by the existing cross-lane merge/export browser contract.
- A legacy merge-preview source anchor remains visible in `app.js` to satisfy the unchanged cross-lane merge/export source contract while the underlying merge-preview behavior stays untouched.
- The browser-global compatibility layer still exports the legacy wrapper names so existing call sites and hidden browser hooks remain stable during later pane cleanup.

## Validation performed

### Required command

The task packet required this exact command:

```text
uv run pytest tests/browser/test_merge_export_contracts.py tests/browser/test_overlay_review_contracts.py tests/browser/test_browser_interactions.py
```

That exact command was rerun until it passed.

Passing result:

```text
==================== test session starts =====================
platform darwin -- Python 3.12.11, pytest-8.4.2, pluggy-1.6.0
PySide6 6.11.0 -- Qt runtime 6.11.0 -- Qt compiled 6.11.0
rootdir: /Volumes/Storage/GitHub/splitshot
configfile: pyproject.toml
plugins: cov-7.1.0, qt-4.5.0
collected 61 items

tests/browser/test_merge_export_contracts.py ....      [  6%]
tests/browser/test_overlay_review_contracts.py ....... [ 18%]
..........                                             [ 34%]
tests/browser/test_browser_interactions.py ........... [ 52%]
.............................                          [100%]

============== 61 passed in 1437.14s (0:23:57) ===============
```

### Validation notes

- The first exact-scope run exposed three source-contract mismatches:
  - the export-log reset anchor in `beginProcessing()` / `clearCurrentExportLogState()` had to remain source-visible in `app.js`
  - two moved review text-box source assertions still pointed at `app.js` instead of `review-pane.js`
- Those were corrected by restoring the source-visible export-log reset seam in `app.js` and updating only the T09C-owned review source assertions to follow the extracted review module.
- A later exact-scope rerun surfaced one transient browser timeout in `test_overlay_font_controls_apply_to_timer_badge_and_bubble_size_override`; the test passed immediately in isolation and the next rerun of the exact required command passed unchanged, so no product-side change was made for that transient.

## Audit performed

### Audit checks executed

- Confirmed the extracted pane inventory now includes the two new T09C-owned pane modules.
- Confirmed the owned export/review wrapper anchors remain source-visible in `app.js`.
- Confirmed the T09D-owned overlay render/drag source anchors remain in `app.js`.
- Recorded worktree status for owned and forbidden paths so the proof captures the existing pre-T09C workspace noise separately from the T09C edits.

### Audit command run

```text
printf 'OWNED_PATH_STATUS\n' && git status --short -- activedev/modularization/progress.md src/splitshot/browser/static/app.js src/splitshot/browser/static/panes/export-pane.js src/splitshot/browser/static/panes/review-pane.js tests/browser/test_merge_export_contracts.py tests/browser/test_overlay_review_contracts.py tests/browser/test_browser_interactions.py activedev/modularization/proof/PROOF-T09C-run1.md && printf '\nFORBIDDEN_PATH_STATUS\n' && git status --short -- src/splitshot/browser/static/panes/pane-base.js src/splitshot/browser/static/panes/scoring-pane.js src/splitshot/browser/static/panes/project-pane.js src/splitshot/browser/static/panes/merge-pane.js src/splitshot/browser/static/panes/settings-pane.js src/splitshot/browser/static/panes/overlay-pane.js src/splitshot/browser/static/panes/markers-pane.js src/splitshot/browser/static/panes/timing-pane.js tests/browser/test_practiscore_sync.py tests/browser/test_browser_static_ui.py && printf '\nDELEGATION_CHECKS\n' && grep -n 'createExportPane\|createReviewPane\|function buildOverlayTextBox\|function renderTextBoxEditors\|function renderExportPresetOptions\|function renderExportLog\|function readExportLayoutPayload\|function readExportSettingsPayload\|function scheduleExportLayoutApply\|function scheduleExportSettingsApply' src/splitshot/browser/static/app.js && printf '\nMODULE_FILES\n' && find src/splitshot/browser/static/panes -maxdepth 1 -type f | sort
```

### Audit results

Owned-path status:

```text
OWNED_PATH_STATUS
 M activedev/modularization/progress.md
 M src/splitshot/browser/static/app.js
 M tests/browser/test_browser_interactions.py
 M tests/browser/test_overlay_review_contracts.py
?? activedev/modularization/proof/PROOF-T09C-run1.md
?? src/splitshot/browser/static/panes/export-pane.js
?? src/splitshot/browser/static/panes/review-pane.js
```

Forbidden-path status:

```text
FORBIDDEN_PATH_STATUS
 M tests/browser/test_browser_static_ui.py
?? src/splitshot/browser/static/panes/pane-base.js
?? src/splitshot/browser/static/panes/scoring-pane.js
```

Delegation checks:

```text
DELEGATION_CHECKS
4:import { createExportPane } from "./panes/export-pane.js";
5:import { createReviewPane } from "./panes/review-pane.js";
1999:function buildOverlayTextBox(source = "manual") {
2398:function renderTextBoxEditors() {
7277:function renderExportPresetOptions(selectId = "export-preset", descriptionId = "export-preset-description", selectedValue = state?.project?.export?.preset) {
7281:function renderExportLog() {
11141:function readExportLayoutPayload() {
11153:function readExportSettingsPayload() {
11637:function scheduleExportLayoutApply() {
11641:function scheduleExportSettingsApply() {
12687:exportPane = createExportPane({
12703:reviewPane = createReviewPane({
```

Pane file inventory:

```text
MODULE_FILES
src/splitshot/browser/static/panes/export-pane.js
src/splitshot/browser/static/panes/pane-base.js
src/splitshot/browser/static/panes/review-pane.js
src/splitshot/browser/static/panes/scoring-pane.js
```

Audit conclusion:

- The two new T09C pane modules are present and wired through explicit imports/instantiation in `app.js`.
- The owned export/review wrapper anchors remain visible in `app.js`, which preserves the browser/global compatibility seam while the implementation lives in the extracted modules.
- The forbidden-path status reflects pre-existing workspace noise from earlier tasks (`pane-base.js`, `scoring-pane.js`, and `tests/browser/test_browser_static_ui.py`), not new T09C edits.
- `tests/browser/test_browser_interactions.py` also showed as modified in the worktree before proof finalization, but T09C required no new content change there; the exact required suite still passed with that file unchanged in this run.

## Handoff notes for `T09D`

- `readOverlayPayload()`, overlay placement baselines, rendered-position unlock/lock math, and live overlay drag/render ownership remain in `app.js`; `T09D` should extract only after preserving the now-explicit review wrapper seam.
- `review-pane.js` already centralizes text-box normalization/editor/state behavior, so `T09D` can inject or delegate to that review module rather than re-owning text-box business logic.
- `export-pane.js` now owns export preset/log/path/settings helpers, but the actual export orchestration order is intentionally still app-owned. Do not move the export button click sequence until the later cleanup task can retire the source contract safely.

## Remaining risks

- `app.js` still carries the cross-lane source-contract anchors for export ordering/log reset and overlay render ownership; later extraction tasks must preserve those contracts until their owned browser assertions move.
- The worktree already contained unrelated unstaged changes outside T09C ownership before this run; the audit records them explicitly so later tasks do not misattribute them to T09C.
- One overlay browser interaction timed out once under the full suite but passed in isolation and on the final exact rerun; keep using state-based waits in later pane tasks rather than adding fixed sleeps.
