# PROOF-T08-run1

- Task: `T08` — Pilot scoring pane
- Date: `2026-05-03`
- Owner: `copilot-orchestrator-20260503-t08-run1`
- Validation tier: `Tier C` (task packet override: exact required command was `uv run pytest tests/browser/test_scoring_metrics_contracts.py tests/browser/test_browser_interactions.py`)
- Result: `pass`

## Scope completed

- Created the T08-owned pane modules:
  - `src/splitshot/browser/static/panes/pane-base.js`
  - `src/splitshot/browser/static/panes/scoring-pane.js`
- Rewired the T08-owned scoring anchors in `src/splitshot/browser/static/app.js` so the monolith now delegates scoring behavior through the extracted pane module instead of owning the scoring workbench logic inline.
- Preserved the existing browser/global contract by keeping the legacy `app.js` function names as thin delegates, including:
  - `setScoringWorkbenchExpanded()`
  - `renderScoringTable()`
  - `renderScoringTables()`
  - `renderScoringPresetOptions()`
  - `renderScoringPresetDescription()`
  - `renderPractiScoreSummaries()`
  - `readScoringPayload()`
  - `applyScoringSettings()`
  - `scheduleScoringApply()`
- Moved the scoring-only row editing/rendering internals out of `app.js`, including the former inline helpers for row edit toggles, score updates, penalty editing, and scoring table row construction.
- Updated the owned browser/static tests so the T08 seam is covered explicitly:
  - `tests/browser/test_scoring_metrics_contracts.py` now asserts that `app.js` delegates through `createScoringPane()`, that the scoring-only helpers no longer live in `app.js`, and that `pane-base.js` stays generic.
  - `tests/browser/test_browser_interactions.py` now explicitly verifies that clicking a scoring workbench row selects the shot and seeks the video, and it also stabilizes an unrelated owned markers regression that was flaking during the required exact-suite reruns.

## Pane-base abstraction notes

The task packet required proof that the pane base is genuinely generic rather than scoring glue in disguise.

`src/splitshot/browser/static/panes/pane-base.js` owns only generic pane mechanics:

- expanded-state getter/setter hooks
- root class toggling
- optional peer expanded-class collapse
- section hide/show behavior
- activity hook emission
- UI-state sync and persistence hooks
- optional expand/collapse callbacks

It contains no scoring strings, no scoring DOM ids, no score/penalty logic, and no PractiScore-specific behavior. The scoring-specific details live in `scoring-pane.js`, which injects its own expanded class, section id, peer-collapse list, and scoring callbacks into the generic base.

## Compatibility seams intentionally retained for T09+

The following seams remain on purpose:

- `app.js` still owns the public wrapper functions listed above so existing render/event call sites and the legacy browser-global compatibility layer remain stable during the rest of the pane-extraction sequence.
- `autoApplyScoring` intentionally remains in `app.js` so broader draft flush / keepalive flows continue using the same app-level debounce/cancel seam while `scheduleScoringApply()` delegates to the pane.
- `scoring-pane.js` owns the scoring workbench state/render/update path, but it continues to use injected shared helpers such as `selectShot()`, `buildSplitRowActionCell()`, `callApi()`, `renderDetailsList()`, and timing-row readers instead of re-owning unrelated timing/project infrastructure.

## Validation performed

### Required command

The task packet required this exact command:

```text
uv run pytest tests/browser/test_scoring_metrics_contracts.py tests/browser/test_browser_interactions.py
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
collected 45 items

tests/browser/test_scoring_metrics_contracts.py .....  [ 11%]
tests/browser/test_browser_interactions.py ........... [ 35%]
.............................                          [100%]

============== 45 passed in 1409.55s (0:23:29) ===============
```

### Validation notes

- The first exact-scope T08 run exposed a browser-suite collection typo in the newly added scoring selected-shot assertion; this was corrected inside the owned test file and the same exact command was rerun.
- The next exact-scope reruns exposed an unrelated markers browser regression inside the same owned browser suite (`test_marker_badge_drag_keeps_motion_path_intact_when_editing_base_point`). An isolated run showed the product behavior itself was intact, but the owned assertion was flaky under full-suite timing.
- That owned markers test was stabilized by atomically capturing the pre-drag motion-path payload and waiting for the same serialized payload after the base-point drag before asserting equality.
- After those owned test fixes, the exact required command passed unchanged.

## Audit performed

### Audit checks executed

- Confirmed only the T08-owned files were modified.
- Confirmed forbidden pane files stayed untouched:
  - `src/splitshot/browser/static/panes/settings-pane.js`
  - `src/splitshot/browser/static/panes/project-pane.js`
  - `src/splitshot/browser/static/panes/merge-pane.js`
  - `src/splitshot/browser/static/panes/review-pane.js`
  - `src/splitshot/browser/static/panes/overlay-pane.js`
  - `src/splitshot/browser/static/panes/markers-pane.js`
  - `src/splitshot/browser/static/panes/timing-pane.js`
- Confirmed the scoring-only helper implementations are no longer present in `app.js`.
- Confirmed `pane-base.js` contains no scoring strings, supporting the generic-base requirement.
- Confirmed the new pane inventory contains only the T08-owned pane files.

### Audit command run

```text
printf 'OWNED_PATH_STATUS\n' && git status --short -- activedev/modularization/progress.md src/splitshot/browser/static/app.js src/splitshot/browser/static/panes/pane-base.js src/splitshot/browser/static/panes/scoring-pane.js tests/browser/test_scoring_metrics_contracts.py tests/browser/test_browser_interactions.py activedev/modularization/proof/PROOF-T08-run1.md && printf '\nFORBIDDEN_PATH_STATUS\n' && git status --short -- src/splitshot/browser/static/panes/settings-pane.js src/splitshot/browser/static/panes/project-pane.js src/splitshot/browser/static/panes/merge-pane.js src/splitshot/browser/static/panes/review-pane.js src/splitshot/browser/static/panes/overlay-pane.js src/splitshot/browser/static/panes/markers-pane.js src/splitshot/browser/static/panes/timing-pane.js && printf '\nSCORING_DELEGATION_CHECKS\n' && grep -n 'createScoringPane\|function renderScoringTable\|function renderScoringTables\|function readScoringPayload\|function scheduleScoringApply' src/splitshot/browser/static/app.js && printf '\nAPP_SCORING_HELPERS_REMAINING\n' && grep -n 'function toggleScoringRowEdit\|function applyShotScoringUpdate\|function buildScoringPenaltyEditor' src/splitshot/browser/static/app.js || true && printf '\nPANE_BASE_SCORING_STRINGS\n' && grep -in 'scoring' src/splitshot/browser/static/panes/pane-base.js || true && printf '\nPANE_FILES\n' && find src/splitshot/browser/static/panes -maxdepth 1 -type f | sort
```

### Audit results

Owned-path status:

```text
OWNED_PATH_STATUS
 M activedev/modularization/progress.md
 M src/splitshot/browser/static/app.js
 M tests/browser/test_browser_interactions.py
 M tests/browser/test_scoring_metrics_contracts.py
?? src/splitshot/browser/static/panes/pane-base.js
?? src/splitshot/browser/static/panes/scoring-pane.js
```

Forbidden-path status:

```text
FORBIDDEN_PATH_STATUS
```

Scoring delegation checks:

```text
SCORING_DELEGATION_CHECKS
4:import { createScoringPane } from "./panes/scoring-pane.js";
7717:function renderScoringTable(tableId = "scoring-table") {
7721:function renderScoringTables() {
11696:function readScoringPayload() {
12214:function scheduleScoringApply() {
13256:scoringPane = createScoringPane({
```

Remaining inline scoring-helper checks:

```text
APP_SCORING_HELPERS_REMAINING
```

Pane-base scoring-string check:

```text
PANE_BASE_SCORING_STRINGS
```

Pane file inventory:

```text
PANE_FILES
src/splitshot/browser/static/panes/pane-base.js
src/splitshot/browser/static/panes/scoring-pane.js
```

### Audit conclusion

- T08 stayed within its owned file list.
- No forbidden pane files were modified.
- `pane-base.js` is generic by construction and by content audit.
- `scoring-pane.js` now owns the scoring workbench behavior while `app.js` retains only the thin compatibility/delegation surface in the owned scoring anchors.

## Handoff notes for `T09A`, `T09B`, and `T09C`

### `T09A` — Settings and metrics panes

- Reuse `createPaneBase()` for pane-expanded state and section visibility, but keep settings/metrics behavior in their own modules rather than broadening the base.
- Follow the T08 pattern: leave `app.js` wrapper names in place for compatibility, move pane-only helpers into the extracted module, and update owned browser/static contracts in the same change.
- The scoring-pane test seam shows how to prove extraction statically without dragging unrelated metrics source strings out of `app.js` too early.

### `T09B` — Project and merge panes

- Preserve the existing PractiScore/project-pane browser contract while extracting; T08 proves the module pattern works without changing UI behavior.
- Keep app-level debounce/flush seams in `app.js` until the later cleanup task can retire them safely.
- Avoid coupling merge/project extraction to scoring; the shared pattern should be the delegate wrapper style, not shared pane-specific internals.

### `T09C` — Export and review panes

- Mirror the T08 approach for apply/schedule delegates: pane modules can own the behavior while app-level flush / keepalive / legacy-global compatibility remains stable.
- T08 demonstrates that selected-item interactions can be strengthened in browser tests during extraction with no UX drift; use the same tactic for review/export interaction preservation.

## Remaining risks

- `app.js` is smaller in scoring responsibility but still large; later pane tasks must keep shrinking it without crossing ownership boundaries.
- The app-level debounce/flush seams are still centralized in `app.js`; that is intentional for now, but later tasks must keep wrapper contracts aligned until `T10` can remove retired scaffolding safely.
- Full browser suites remain sensitive to timing in some legacy markers flows; T08 stabilized the owned flaky assertion encountered during validation, but later pane work should keep using state-based waits instead of fixed pauses.
