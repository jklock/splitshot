# PROOF-T09D-run1

- Task: `T09D` — ShotML and overlay panes
- Date: `2026-05-03`
- Owner: `copilot-orchestrator-20260503-t09d-run1`
- Validation tier: `Tier C` (task packet override: exact required command was `uv run pytest tests/browser/test_overlay_review_contracts.py tests/browser/test_timing_waveform_contracts.py tests/browser/test_browser_interactions.py`)
- Result: `pass`

## Scope completed

- Created the T09D-owned pane modules:
  - `src/splitshot/browser/static/panes/shotml-pane.js`
  - `src/splitshot/browser/static/panes/overlay-pane.js`
- Rewired the T09D-owned ShotML and overlay anchors in `src/splitshot/browser/static/app.js` so the monolith now delegates pane-owned behavior through the extracted modules instead of owning the full implementations inline.
- Preserved the browser/global compatibility surface by keeping the legacy `app.js` function names as thin delegates for the moved ShotML/overlay behavior, including:
  - Overlay wrappers: `scheduleOverlayColorCommit()`, `flushOverlayColorCommit()`, `renderLiveOverlay()`, `readOverlayPayload()`, `scheduleOverlayApply()`, and the overlay placement-baseline / badge-coordinate helpers.
  - ShotML wrappers: `setShotMLSectionExpanded()`, `renderShotMLProposals()`, `renderShotML()`, `scheduleThresholdApply()`, `applyThresholdNow()`, and `scheduleShotMLSettingsApply()`.
- Updated the T09D-owned overlay source-contract coverage in `tests/browser/test_overlay_review_contracts.py` so moved overlay assertions now point at `overlay-pane.js` and the remaining `app.js` delegation seams instead of stale pre-extraction locations.
- Preserved the T09C/T09D ownership seam: review text-box state/editor logic remains owned by `review-pane.js`, while T09D continues to own live overlay rendering, overlay drag/color state, and ShotML controls.
- Stabilized the remaining browser regressions exposed during exact-scope validation by preserving same-project popup/template and export drafts during in-flight refreshes and by strengthening popup motion-path fallback generation for longer travel.

## Compatibility seams intentionally retained for `T09E` / `T10`

- Popup/marker authoring, popup editor state, and motion-path generation remain intentionally app-owned for `T09E`.
- Review text-box state/editor ownership remains in `review-pane.js`; `overlay-pane.js` consumes injected review helpers rather than re-owning them.
- The legacy `app.js` wrapper surface and browser-global compatibility bridge remain in place so existing call sites and source-visible browser contracts stay stable during later cleanup.
- `renderLiveOverlay()` and `readOverlayPayload()` remain source-visible in `app.js` even though the implementation now lives behind the extracted overlay pane boundary.

## Validation performed

### Required command

The task packet required this exact command:

```text
uv run pytest tests/browser/test_overlay_review_contracts.py tests/browser/test_timing_waveform_contracts.py tests/browser/test_browser_interactions.py
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
collected 65 items

tests/browser/test_overlay_review_contracts.py .............. [ 21%]
tests/browser/test_timing_waveform_contracts.py ............. [ 41%]
tests/browser/test_browser_interactions.py .................. [ 69%]
....................                                         [100%]

============== 65 passed in 1505.57s (0:25:05) ===============
```

### Validation notes

- Early exact-scope reruns first exposed six stale source-contract failures plus two real regressions:
  - popup motion-path fallback generation for longer travel
  - export/manual-override persistence being cleared before server echo
- The owned fixes stayed within the T09D ShotML/overlay/browser seams: overlay source contracts were moved to the extracted module boundaries, same-project draft preservation stopped remote refreshes from clobbering popup/template and export edits, and the motion fallback heuristic now generates enough evenly spaced in-between points for longer travel.
- A later exact-scope rerun surfaced two transient interaction timeouts in `test_overlay_font_controls_apply_to_timer_badge_and_bubble_size_override` and `test_scoring_workbench_rows_lock_edit_delete_and_restore`; both passed immediately in isolation and the next rerun of the exact required command passed unchanged, so no additional product change was made for those transients.
- The UI surface audit was intentionally not rerun because T09D preserved the existing shell/control inventory and did not change `index.html`, the QA docs, or the audited browser control surface; the task was closed with the exact browser scope required by the task packet.

## Audit performed

### Audit checks executed

- Confirmed `shotml-pane.js` and `overlay-pane.js` exist in the pane inventory.
- Confirmed no pane module imports another pane module; the only pane-local shared import reported by the audit was `scoring-pane.js` importing `pane-base.js`.
- Confirmed the required `app.js` delegation anchors remain source-visible for shared browser contracts, including instantiation of `shotmlPane` / `overlayPane` and wrapper anchors for `scheduleOverlayColorCommit()`, `renderLiveOverlay()`, `readOverlayPayload()`, `setShotMLSectionExpanded()`, `renderShotMLProposals()`, `renderShotML()`, `scheduleThresholdApply()`, `applyThresholdNow()`, and `scheduleShotMLSettingsApply()`.
- Confirmed the `T09C` / `T09D` / `T09E` boundaries remain aligned with the modularization plan: review text-box logic stays in `review-pane.js`, popup/marker ownership stays app-owned for `T09E`, and no cross-pane imports were introduced.

### Audit commands run

```text
cd /Volumes/Storage/GitHub/splitshot && printf 'APP_SIZE\n' && wc -l src/splitshot/browser/static/app.js && printf '\nPANE_FILES\n' && find src/splitshot/browser/static/panes -maxdepth 1 -type f | sort && printf '\nCROSS_PANE_IMPORTS\n' && grep -RInE 'from "\./.*pane|from "\.\./panes/' src/splitshot/browser/static/panes/*.js || true
```

```text
cd /Volumes/Storage/GitHub/splitshot && printf 'DELEGATION_CHECKS\n' && grep -n 'createOverlayPane\|createShotMLPane\|function scheduleOverlayColorCommit\|function renderLiveOverlay\|function readOverlayPayload\|function setShotMLSectionExpanded\|function renderShotMLProposals\|function renderShotML\|function scheduleThresholdApply\|function applyThresholdNow\|function scheduleShotMLSettingsApply' src/splitshot/browser/static/app.js
```

### Audit results

Architecture snapshot:

```text
APP_SIZE
   12826 src/splitshot/browser/static/app.js

PANE_FILES
src/splitshot/browser/static/panes/export-pane.js
src/splitshot/browser/static/panes/overlay-pane.js
src/splitshot/browser/static/panes/pane-base.js
src/splitshot/browser/static/panes/review-pane.js
src/splitshot/browser/static/panes/scoring-pane.js
src/splitshot/browser/static/panes/shotml-pane.js

CROSS_PANE_IMPORTS
src/splitshot/browser/static/panes/scoring-pane.js:1:import { createPaneBase } from "./pane-base.js";
```

Delegation anchors:

```text
DELEGATION_CHECKS
5:import { createOverlayPane } from "./panes/overlay-pane.js";
8:import { createShotMLPane } from "./panes/shotml-pane.js";
2098:function scheduleOverlayColorCommit() {
2205:function setShotMLSectionExpanded(sectionId, expanded) {
8461:function renderShotMLProposals() {
8465:function renderShotML() {
9948:function renderLiveOverlay(positionMsOverride = null) {
10158:function readOverlayPayload() {
10650:function scheduleThresholdApply() {
10655:async function applyThresholdNow() {
10661:function scheduleShotMLSettingsApply() {
11750:shotmlPane = createShotMLPane({
11764:overlayPane = createOverlayPane({
```

### Audit conclusion

- `app.js` responsibility continued moving in the intended direction and is now down to 12,826 lines after the T09D extraction.
- `shotml-pane.js` and `overlay-pane.js` are present, no prohibited cross-pane imports were introduced, and the remaining review/popup seams are intentional rather than accidental.
- The worktree still contains pre-existing uncommitted modularization changes from earlier tasks, so this audit focused on structural checks and the T09D delegation seams rather than raw repo cleanliness; no architectural drift was detected in the T09D lane.

## Handoff notes for `T09E`

- Popup/marker motion-path authoring remains in `app.js` and now depends on the preserved same-project popup/template draft behavior.
- `T09E` should keep the strengthened motion fallback heuristic intact while moving marker/timing ownership out of `app.js`.
- The `review-pane.js` / `overlay-pane.js` seam is now explicit; `T09E` should depend on it rather than re-own review text-box state.

## Remaining risks

- Same-project popup/template draft preservation still depends on the shared API/runtime merge seam; later cleanup should consolidate that contract once `T09E` finishes marker/popup extraction.
- `app.js` still owns popup/marker authoring and motion-path workflows; `T09E` must preserve those zero-drift flows while continuing the extraction.
- The worktree already contains unrelated modularization changes from earlier tasks, so future audits should continue isolating lane-specific seams instead of assuming a clean diff baseline.
