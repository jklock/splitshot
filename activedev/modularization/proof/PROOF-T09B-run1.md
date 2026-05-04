# PROOF-T09B-run1

- Task: `T09B` — Project and merge panes
- Date: `2026-05-03`
- Owner: `copilot-orchestrator-20260503-t09b-run1`
- Validation tier: `Tier C` (task packet override: exact required command was `uv run pytest tests/browser/test_project_lifecycle_contracts.py tests/browser/test_merge_export_contracts.py tests/browser/test_practiscore_session_api.py tests/browser/test_practiscore_sync_controller.py`)
- Result: `pass`

## Scope completed

- Created the T09B-owned pane modules:
  - `src/splitshot/browser/static/panes/project-pane.js`
  - `src/splitshot/browser/static/panes/merge-pane.js`
- Rewired the T09B-owned Project / PractiScore and merge anchors in `src/splitshot/browser/static/app.js` so the monolith now delegates pane-owned behavior through those extracted modules instead of keeping the full implementations inline.
- Preserved the existing Project-pane browser contract, including the manual `Select PractiScore File` fallback path, the local `Match type`, `Stage #`, `Competitor name`, and `Place` controls, the PractiScore browser opener flow, and same-project draft preservation.
- Preserved the existing merge preview / PiP contract, including per-source PiP preview geometry, opacity/sync controls, delayed source commit batching, and flush-before-export ordering.
- Kept the legacy `app.js` function names as thin delegates so the browser/global compatibility surface and the source-visible contract assertions remain stable.
- Updated the owned browser contract coverage in:
  - `tests/browser/test_project_lifecycle_contracts.py`
  - `tests/browser/test_merge_export_contracts.py`
  so the moved implementation details are asserted at the extracted pane boundary while the required `app.js` delegation seams remain visible.
- Reviewed `docs/userfacing/panes/project.md` and `docs/project/browser-control-qa-matrix.md` against the final behavior and left them unchanged because the Project-pane / PractiScore controls, routes, and user-facing workflow did not change.

## Compatibility seams intentionally retained for `T10`

The following seams intentionally remain in `src/splitshot/browser/static/app.js`:

- Project / PractiScore wrappers such as `renderPractiScoreSelect()`, `readProjectDetailsPayload()`, `readPractiScoreContextPayload()`, `flushPendingProjectDrafts()`, `probeProjectFolder()`, `createNewProject()`, and `useProjectFolder()` remain source-visible so the existing browser/static contracts do not drift while the implementation lives in `project-pane.js`.
- Merge wrappers such as `mergeSourcePipRect()`, `renderMergePreviewLayer()`, `flushPendingMergeSourceCommits()`, `renderMergeMediaList()`, `readMergePayload()`, and `scheduleMergeApply()` remain source-visible for the same reason while the implementation lives in `merge-pane.js`.
- The browser payload contract `practiscore_session`, `practiscore_sync`, and `practiscore_options` remains unchanged and is still enforced by the unchanged dedicated PractiScore session/sync suites.
- App-level draft flush / keepalive sequencing remains visible in `app.js` so later cleanup can retire it deliberately instead of accidentally breaking save/open/import ordering.

## Validation performed

### Required command

The task packet required this exact command:

```text
uv run pytest tests/browser/test_project_lifecycle_contracts.py tests/browser/test_merge_export_contracts.py tests/browser/test_practiscore_session_api.py tests/browser/test_practiscore_sync_controller.py
```

That exact command was run after the final T09B extraction and contract updates.

Passing result:

```text
==================== test session starts =====================
platform darwin -- Python 3.12.11, pytest-8.4.2, pluggy-1.6.0
PySide6 6.11.0 -- Qt runtime 6.11.0 -- Qt compiled 6.11.0
rootdir: /Volumes/Storage/GitHub/splitshot
configfile: pyproject.toml
plugins: cov-7.1.0, qt-4.5.0
collected 29 items

tests/browser/test_project_lifecycle_contracts.py .........
tests/browser/test_merge_export_contracts.py ....
tests/browser/test_practiscore_session_api.py ............
tests/browser/test_practiscore_sync_controller.py ....

============== 29 passed in 95.03s (0:01:35) ==============
```

### Validation notes

- The dedicated PractiScore session/sync suites stayed unchanged and passed, which confirms the extracted Project-pane work preserved the `practiscore_session`, `practiscore_sync`, and `practiscore_options` contract.
- No docs update was required because the final browser-visible Project-pane / PractiScore workflow, control set, and QA ownership claims remained unchanged.
- `get_errors` reported no problems in the modified JS and owned test files before the final exact-scope validation run.

## Audit performed

### Audit checks executed

- Confirmed `project-pane.js` and `merge-pane.js` exist and are wired through explicit imports / instantiation in `app.js`.
- Confirmed the owned Project / PractiScore and merge wrapper anchors remain source-visible in `app.js`.
- Confirmed the dedicated PractiScore API/controller suites remained untouched by T09B.
- Reviewed the Project-pane user guide and QA matrix and confirmed no T09B doc delta was needed because the user-visible workflow did not change.
- Recorded owned-path status separately from the existing worktree noise so the proof distinguishes T09B edits from earlier modularization tasks already present in the workspace.

### Audit commands run

```text
printf 'OWNED_PATH_STATUS\n' && git status --short -- activedev/modularization/progress.md src/splitshot/browser/static/app.js src/splitshot/browser/static/panes/project-pane.js src/splitshot/browser/static/panes/merge-pane.js tests/browser/test_project_lifecycle_contracts.py tests/browser/test_merge_export_contracts.py docs/userfacing/panes/project.md docs/project/browser-control-qa-matrix.md activedev/modularization/proof/PROOF-T09B-run1.md && printf '\nFORBIDDEN_PATH_STATUS\n' && git status --short -- src/splitshot/browser/static/panes/export-pane.js src/splitshot/browser/static/panes/review-pane.js src/splitshot/browser/static/panes/shotml-pane.js src/splitshot/browser/static/panes/overlay-pane.js src/splitshot/browser/static/panes/markers-pane.js src/splitshot/browser/static/panes/timing-pane.js tests/browser/test_practiscore_session_api.py tests/browser/test_practiscore_sync_controller.py && printf '\nDELEGATION_CHECKS\n' && grep -n 'createProjectPane\|createMergePane\|function renderPractiScoreSelect\|function readProjectDetailsPayload\|function flushPendingProjectDrafts\|function probeProjectFolder\|function createNewProject\|function useProjectFolder\|function mergeSourcePipRect\|function renderMergePreviewLayer\|function flushPendingMergeSourceCommits\|function renderMergeMediaList\|function readMergePayload\|function scheduleMergeApply' src/splitshot/browser/static/app.js && printf '\nMODULE_FILES\n' && find src/splitshot/browser/static/panes -maxdepth 1 -type f | sort
```

```text
printf 'T09B_OWNED_STATUS\n' && git status --short -- activedev/modularization/progress.md src/splitshot/browser/static/app.js src/splitshot/browser/static/panes/project-pane.js src/splitshot/browser/static/panes/merge-pane.js tests/browser/test_project_lifecycle_contracts.py tests/browser/test_merge_export_contracts.py activedev/modularization/proof/PROOF-T09B-run1.md && printf '\nDOC_STATUS_REVIEW\n' && git status --short -- docs/userfacing/panes/project.md docs/project/browser-control-qa-matrix.md
```

### Audit results

Clean owned-path snapshot:

```text
T09B_OWNED_STATUS
 M activedev/modularization/progress.md
 M src/splitshot/browser/static/app.js
 M tests/browser/test_merge_export_contracts.py
 M tests/browser/test_project_lifecycle_contracts.py
?? src/splitshot/browser/static/panes/merge-pane.js
?? src/splitshot/browser/static/panes/project-pane.js
```

Doc review snapshot:

```text
DOC_STATUS_REVIEW
?? docs/project/browser-control-qa-matrix.md
```

Adjacent-path and delegation snapshot:

```text
FORBIDDEN_PATH_STATUS
?? src/splitshot/browser/static/panes/export-pane.js
?? src/splitshot/browser/static/panes/markers-pane.js
?? src/splitshot/browser/static/panes/overlay-pane.js
?? src/splitshot/browser/static/panes/review-pane.js
?? src/splitshot/browser/static/panes/shotml-pane.js
?? src/splitshot/browser/static/panes/timing-pane.js

DELEGATION_CHECKS
5:import { createMergePane } from "./panes/merge-pane.js";
8:import { createProjectPane } from "./panes/project-pane.js";
5217:function renderPractiScoreSelect(selectId, values, emptyLabel, selectedValue = "") {
5590:function mergeSourcePipRect(...args) {
5599:function renderMergePreviewLayer(video, stage, mergeSources, pipSizeValue) {
7712:async function flushPendingMergeSourceCommits(options = {}) {
7716:function renderMergeMediaList() {
8690:function readProjectDetailsPayload() {
8723:function readMergePayload() {
8855:async function flushPendingProjectDrafts() {
8892:function flushPendingProjectDraftsKeepalive() {
8932:async function probeProjectFolder(path) {
8942:async function createNewProject(path = "") {
8953:async function useProjectFolder(path = "") {
9068:function scheduleMergeApply() {
10345:mergePane = createMergePane({
10377:projectPane = createProjectPane({

MODULE_FILES
src/splitshot/browser/static/panes/export-pane.js
src/splitshot/browser/static/panes/markers-pane.js
src/splitshot/browser/static/panes/merge-pane.js
src/splitshot/browser/static/panes/overlay-pane.js
src/splitshot/browser/static/panes/pane-base.js
src/splitshot/browser/static/panes/project-pane.js
src/splitshot/browser/static/panes/review-pane.js
src/splitshot/browser/static/panes/scoring-pane.js
src/splitshot/browser/static/panes/shotml-pane.js
src/splitshot/browser/static/panes/timing-pane.js
```

### Audit conclusion

- The two new T09B pane modules are present and wired through explicit imports / instantiation in `app.js`.
- The owned Project / PractiScore and merge wrapper anchors remain visible in `app.js`, which preserves the browser/global compatibility seam while the implementation lives in the extracted pane modules.
- The clean owned-path snapshot was captured immediately before proof-file finalization, so `PROOF-T09B-run1.md` does not appear in that particular `git status` output.
- `docs/userfacing/panes/project.md` remained clean and unchanged; `docs/project/browser-control-qa-matrix.md` showed pre-existing untracked workspace noise from earlier documentation work rather than a new T09B edit.
- The forbidden-path status reflects earlier modularization work already present in the workspace, not new T09B edits. The dedicated PractiScore API/controller tests remained unchanged.

## Handoff notes for `T10`

- Keep the source-visible Project / PractiScore and merge wrappers in `app.js` until the later monolith-cleanup task can retire those browser/static contracts deliberately.
- Preserve the current same-project draft handling and merge-source commit ordering when removing the remaining wrappers; both are now centralized behind the extracted pane boundaries but still anchored by `app.js` sequencing.
- If a later task changes the Project-pane / PractiScore user-visible workflow, update `docs/userfacing/panes/project.md`, `docs/project/browser-control-qa-matrix.md`, and the dedicated PractiScore browser coverage in the same change.

## Remaining risks

- `app.js` still carries the source-visible wrapper seams for Project / PractiScore and merge behavior; later cleanup must preserve the current browser contract until those assertions move.
- The worktree already contains unrelated modularization changes and untracked doc artifacts from earlier tasks, so later audits should continue isolating lane-specific edits rather than assuming a clean diff baseline.
- The extracted panes preserve the existing zero-drift behavior, but later cleanup should avoid reformatting or renaming the wrapper anchors that the browser contract tests still inspect by source text.
