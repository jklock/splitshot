# PROOF-T09E-run1

- Task: `T09E` — Markers and timing panes
- Date: `2026-05-03`
- Owner: `copilot-orchestrator-20260503-t09e-run1`
- Validation tier: `Tier C` (task packet override: exact required command was `uv run pytest tests/browser/test_timing_waveform_contracts.py tests/browser/test_overlay_review_contracts.py tests/browser/test_browser_interactions.py tests/browser/test_browser_remaining_controls_e2e.py`)
- Result: `pass`

## Scope completed

- Created the T09E-owned pane modules:
  - `src/splitshot/browser/static/panes/markers-pane.js`
  - `src/splitshot/browser/static/panes/timing-pane.js`
- Rewired the T09E-owned markers/timing anchors in `src/splitshot/browser/static/app.js` so the monolith now delegates pane-owned behavior through the extracted modules instead of owning the full implementations inline.
- Preserved the browser/global compatibility surface by keeping the legacy `app.js` function names as thin delegates for the moved markers/timing behavior, including:
  - Markers wrappers: `selectPopupBubble()`, `setPopupBubbles()`, `setPopupBubbleField()`, `importShotPopups()`, `generatePopupBubbleMotionPath()`, and `setMarkersExpanded()`.
  - Timing wrappers: `applyTimingTableColumns()`, `syncTimingTableColumns()`, `renderTimingEventEditor()`, `addTimingEvent()`, and `setTimingExpanded()`.
- Updated the T09E-owned markers/timing assertions in `tests/browser/test_timing_waveform_contracts.py`, `tests/browser/test_overlay_review_contracts.py`, `tests/browser/test_browser_interactions.py`, and `tests/browser/test_browser_remaining_controls_e2e.py` so the shared suites follow the extracted module boundaries while keeping the same user-visible behaviors under test.
- Preserved the zero-drift high-coupling behavior the task packet called out: marker authoring, motion-path editing, workbench navigation, waveform selection/seek flow, timing-event management, keyboard-adjacent timing actions, and selected-shot continuity all remain behavior-identical under the extracted pane seams.

## Compatibility seams intentionally retained for `T10`

- The legacy `app.js` wrapper surface above remains source-visible so the existing browser/static contracts can keep asserting the same seam while the cleanup lane removes the remaining monolith scaffolding.
- `timing-pane.js` intentionally reuses the shared generic `pane-base.js`; no new pane-to-pane coupling was introduced beyond that existing shared base.
- `markers-pane.js` continues consuming injected overlay/review/runtime helpers instead of re-owning those cross-lane seams early.
- Same-project draft/refresh preservation remains outside the pane modules for now so the extraction stays behavior-identical; `T10` can consolidate that shared logic after the last pane lane is complete.

## Validation performed

### Required command

The task packet required this exact command:

```text
uv run pytest tests/browser/test_timing_waveform_contracts.py tests/browser/test_overlay_review_contracts.py tests/browser/test_browser_interactions.py tests/browser/test_browser_remaining_controls_e2e.py
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
collected 75 items

tests/browser/test_timing_waveform_contracts.py ............. [ 17%]
tests/browser/test_overlay_review_contracts.py .............. [ 36%]
tests/browser/test_browser_interactions.py .................. [ 60%]
....................                                         [ 86%]
tests/browser/test_browser_remaining_controls_e2e.py ........ [ 97%]
..                                                           [100%]

============== 75 passed in 1753.62s (0:29:13) ===============
```

### Validation notes

- Early exact-scope reruns first exposed a browser bootstrap break plus a set of markers/timing regressions across popup motion tracing, shot-linked duration preservation, popup asset-path persistence, ShotML section route persistence, and overlay style/font continuity during same-project refreshes.
- The fixes kept the zero-drift markers/timing/browser contract intact; after those corrections, the exact required command passed unchanged.
- No broader browser suite was required because the task packet explicitly closes `T09E` on this exact validation scope.

## Audit performed

### Audit checks executed

- Confirmed `markers-pane.js` and `timing-pane.js` exist in the pane inventory.
- Confirmed no new pane-to-pane imports were introduced beyond the shared `pane-base.js` usage in `timing-pane.js`.
- Confirmed the required markers/timing delegation anchors remain source-visible in `app.js` for the shared browser/static contracts.
- Confirmed `app.js` responsibility continued shrinking and is now down to 12,083 lines after the final pane-extraction lane.
- Captured owned-path and forbidden-path status, noting that the forbidden-pane entries already present in the worktree are pre-existing earlier-task files rather than fresh T09E leakage.

### Audit command run

```text
cd /Volumes/Storage/GitHub/splitshot && printf 'OWNED_PATH_STATUS\n' && git status --short -- activedev/modularization/progress.md src/splitshot/browser/static/app.js src/splitshot/browser/static/panes/markers-pane.js src/splitshot/browser/static/panes/timing-pane.js tests/browser/test_timing_waveform_contracts.py tests/browser/test_overlay_review_contracts.py tests/browser/test_browser_interactions.py tests/browser/test_browser_remaining_controls_e2e.py activedev/modularization/proof/PROOF-T09E-run1.md && printf '\nFORBIDDEN_PATH_STATUS\n' && git status --short -- src/splitshot/browser/static/panes/project-pane.js src/splitshot/browser/static/panes/merge-pane.js src/splitshot/browser/static/panes/export-pane.js src/splitshot/browser/static/panes/review-pane.js src/splitshot/browser/static/panes/overlay-pane.js src/splitshot/browser/static/styles.css && printf '\nAPP_SIZE\n' && wc -l src/splitshot/browser/static/app.js && printf '\nPANE_FILES\n' && find src/splitshot/browser/static/panes -maxdepth 1 -type f | sort && printf '\nCROSS_PANE_IMPORTS\n' && grep -RInE 'from "\./.*pane|from "\.\./panes/' src/splitshot/browser/static/panes/*.js || true && printf '\nDELEGATION_CHECKS\n' && grep -n 'createMarkersPane\|createTimingPane\|function selectPopupBubble\|function setPopupBubbles\|function setPopupBubbleField\|function importShotPopups\|function generatePopupBubbleMotionPath\|function setMarkersExpanded\|function applyTimingTableColumns\|function syncTimingTableColumns\|function renderTimingEventEditor\|function addTimingEvent\|function setTimingExpanded' src/splitshot/browser/static/app.js
```

### Audit results

Owned-path status:

```text
OWNED_PATH_STATUS
 M activedev/modularization/progress.md
 M src/splitshot/browser/static/app.js
 M tests/browser/test_browser_interactions.py
 M tests/browser/test_browser_remaining_controls_e2e.py
 M tests/browser/test_overlay_review_contracts.py
 M tests/browser/test_timing_waveform_contracts.py
?? src/splitshot/browser/static/panes/markers-pane.js
?? src/splitshot/browser/static/panes/timing-pane.js
```

Forbidden-path status:

```text
FORBIDDEN_PATH_STATUS
?? src/splitshot/browser/static/panes/export-pane.js
?? src/splitshot/browser/static/panes/overlay-pane.js
?? src/splitshot/browser/static/panes/review-pane.js
```

Architecture snapshot:

```text
APP_SIZE
   12083 src/splitshot/browser/static/app.js

PANE_FILES
src/splitshot/browser/static/panes/export-pane.js
src/splitshot/browser/static/panes/markers-pane.js
src/splitshot/browser/static/panes/overlay-pane.js
src/splitshot/browser/static/panes/pane-base.js
src/splitshot/browser/static/panes/review-pane.js
src/splitshot/browser/static/panes/scoring-pane.js
src/splitshot/browser/static/panes/shotml-pane.js
src/splitshot/browser/static/panes/timing-pane.js

CROSS_PANE_IMPORTS
src/splitshot/browser/static/panes/scoring-pane.js:1:import { createPaneBase } from "./pane-base.js";
src/splitshot/browser/static/panes/timing-pane.js:1:import { createPaneBase } from "./pane-base.js";
```

Delegation anchors:

```text
DELEGATION_CHECKS
5:import { createMarkersPane } from "./panes/markers-pane.js";
10:import { createTimingPane } from "./panes/timing-pane.js";
1830:function applyTimingTableColumns(table) {
1834:function syncTimingTableColumns() {
3093:function selectPopupBubble(
3107:function selectPopupBubbleForShot(shotId, options = {}) {
3123:function setPopupBubbles(bubbles, { commit = true, rerender = true } = {}) {
3131:function setPopupBubbleField(bubbleId, field, rawValue, options = {}) {
3169:function importShotPopups() {
3428:function generatePopupBubbleMotionPathLinear(bubbleId) {
3432:function generatePopupBubbleMotionPath(bubbleId) {
6219:function renderTimingEventEditor() {
6223:function addTimingEvent() {
6518:function setMarkersExpanded(expanded, { persistUiState = true } = {}) {
9217:function setTimingExpanded(expanded, { persistUiState = true } = {}) {
10873:markersPane = createMarkersPane({
11140:timingPane = createTimingPane({
```

### Audit conclusion

- `markers-pane.js` and `timing-pane.js` are present and wired through explicit imports and instantiation in `app.js`.
- No CSS changes were introduced for this lane.
- The only pane-local shared import relevant to T09E remains the generic `pane-base.js`; no new markers/timing cross-pane coupling leaked into unrelated pane modules.
- The forbidden-path status shown above reflects pre-existing earlier modularization files already in the worktree, not fresh T09E edits.

## Handoff notes for `T10`

- Remove the remaining markers/timing wrappers from `app.js` only when the shared browser/static contracts move with them in the same cleanup change.
- Keep the shared same-project draft/refresh preservation path intact while cleanup consolidates pane-independent state coordination.
- The `review-pane.js` / `overlay-pane.js` / `markers-pane.js` seam and the `waveform-state.js` / `timing-pane.js` seam are now explicit; `T10` should simplify those seams without re-inlining behavior and reintroducing drift.

## Remaining risks

- Same-project refresh preservation now spans several high-coupling surfaces and should be consolidated carefully during cleanup rather than piecemeal.
- The worktree still contains earlier-task uncommitted files, so future audits should keep isolating lane-specific changes instead of assuming a clean repository baseline.
