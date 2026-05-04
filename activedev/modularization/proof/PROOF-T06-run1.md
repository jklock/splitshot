# PROOF-T06-run1

- Task: `T06` — Components shell
- Date: `2026-05-03`
- Owner: `copilot-orchestrator-20260503-t06-run1`
- Validation tier: `Tier B` (task packet override: exact required command was `uv run pytest tests/browser/test_browser_static_ui.py tests/browser/test_browser_control.py tests/browser/test_project_lifecycle_contracts.py`)
- Result: `pass`

## Scope completed

- Created the T06 shell component modules owned by this task:
  - `src/splitshot/browser/static/components/status-bar.js`
  - `src/splitshot/browser/static/components/video-player.js`
- Rewired `src/splitshot/browser/static/app.js` so the shared shell delegates status/timing-summary rendering and video-stage/media rendering through the extracted component factories.
- Preserved the existing browser contract by keeping the legacy function names in `app.js` as thin delegation wrappers:
  - `renderHeader()`
  - `renderStats()`
  - `timingSummaryRows()`
  - `renderTimingSummary()`
  - `renderVideo()`
- Updated the owned browser contract tests so the static assertions now point at the extracted component boundaries instead of assuming those source strings still live in `app.js`.
- Synced the owned project lifecycle static contract to match the already-live guarded primary file-input flow that includes the null-file bail-out before draft flushing.
- Intentionally did **not** create `src/splitshot/browser/static/components/data-table.js` because T06 did not establish real multi-area reuse that would justify a new shared helper without crossing later ownership seams.

## Compatibility seams intentionally retained for T07

The task packet required any intentional seams left behind to be documented. The following remain on purpose:

- `app.js` still owns the wrapper functions listed above so existing render call sites and browser/global compatibility stay stable during the modularization sequence.
- `installLegacyGlobalCompat()` remains in place and still exposes the legacy monolith-facing surface while the shell is mid-extraction.
- `status-bar.js` receives `renderDetailsList()` and related shell helpers by injection rather than absorbing broader table/render infrastructure early.
- `video-player.js` receives merge/video helpers by injection and intentionally leaves adjacent higher-coupling seams in `app.js`, including the secondary-preview coordination path and merge-preview layer rendering that later tasks will own/refine.
- `data-table.js` was intentionally deferred; T07 should continue with waveform/overlay extraction rather than backfilling speculative helper modules.

## Validation performed

### Required command

The task packet required this exact command:

```text
uv run pytest tests/browser/test_browser_static_ui.py tests/browser/test_browser_control.py tests/browser/test_project_lifecycle_contracts.py
```

That exact command was run after the shell extraction and final contract sync.

Passing result:

```text
==================== test session starts =====================
platform darwin -- Python 3.12.11, pytest-8.4.2, pluggy-1.6.0
PySide6 6.11.0 -- Qt runtime 6.11.0 -- Qt compiled 6.11.0
rootdir: /Volumes/Storage/GitHub/splitshot
configfile: pyproject.toml
plugins: cov-7.1.0, qt-4.5.0
collected 103 items

tests/browser/test_browser_static_ui.py .............. [ 13%]
.........                                              [ 22%]
tests/browser/test_browser_control.py ................ [ 37%]
...................................................... [ 90%]
.                                                      [ 91%]
tests/browser/test_project_lifecycle_contracts.py .... [ 95%]
.....                                                  [100%]

============== 103 passed in 623.46s (0:10:23) ===============
```

### Validation notes

- A narrower preflight run of `tests/browser/test_browser_static_ui.py` first exposed one stale assertion still looking for `primary_display_name` inside `app.js`; that assertion was updated to follow the new `status-bar.js` boundary.
- The first exact-scope T06 run exposed one stale lifecycle-contract assertion that predated the existing null-file guard in the primary import input flow; the assertion was updated within T06 ownership and the exact command was rerun unchanged.
- No changes were required in `tests/browser/test_browser_control.py`.

## Audit performed

### Audit checks executed

- Confirmed only the T06-owned shell component files were created under `src/splitshot/browser/static/components/`.
- Confirmed forbidden paths stayed untouched, including `styles.css`, `src/splitshot/browser/static/panes/`, `components/waveform.js`, and `components/overlay-canvas.js`.
- Confirmed `app.js` shrank in responsibility while preserving the legacy wrapper contract.
- Confirmed the owned static UI contract was updated in the same run to point at the new shell component boundaries.
- Confirmed `data-table.js` was not introduced without a justified reuse case.

### Audit command run

```text
printf 'OWNED_PATH_STATUS\n' && git status --short -- activedev/modularization/progress.md src/splitshot/browser/static/app.js src/splitshot/browser/static/components/status-bar.js src/splitshot/browser/static/components/video-player.js src/splitshot/browser/static/components/data-table.js tests/browser/test_browser_static_ui.py tests/browser/test_browser_control.py tests/browser/test_project_lifecycle_contracts.py activedev/modularization/proof/PROOF-T06-run1.md && printf '\nFORBIDDEN_PATH_STATUS\n' && git status --short -- src/splitshot/browser/static/components/waveform.js src/splitshot/browser/static/components/overlay-canvas.js src/splitshot/browser/static/panes src/splitshot/browser/static/styles.css && printf '\nSHELL_COMPONENT_FILES\n' && find src/splitshot/browser/static/components -maxdepth 1 -type f | sort && printf '\nAPP_SIZE\n' && wc -l src/splitshot/browser/static/app.js
```

### Audit results

Owned-path status:

```text
OWNED_PATH_STATUS
 M activedev/modularization/progress.md
 M src/splitshot/browser/static/app.js
 M tests/browser/test_browser_static_ui.py
 M tests/browser/test_project_lifecycle_contracts.py
?? src/splitshot/browser/static/components/status-bar.js
?? src/splitshot/browser/static/components/video-player.js
```

Forbidden-path status:

```text
FORBIDDEN_PATH_STATUS
```

Shell component files present:

```text
SHELL_COMPONENT_FILES
src/splitshot/browser/static/components/status-bar.js
src/splitshot/browser/static/components/video-player.js
```

Current `app.js` size:

```text
APP_SIZE
   14832 src/splitshot/browser/static/app.js
```

### Audit conclusion

- T06 stayed within its owned file list.
- No forbidden shell/pane/CSS paths were modified.
- The extracted status-bar and video-player modules exist and `app.js` now delegates through them while preserving the zero-drift wrapper contract.
- The owned browser contract tests were updated in the same run.

## Adoption notes for T07

- Continue the same dependency-injection pattern for waveform and overlay extraction rather than introducing new global entry points.
- Preserve the thin compatibility wrappers in `app.js` until the later cleanup tasks can retire them safely.
- Keep `data-table.js` deferred unless T07 or later tasks uncover real, multi-owner reuse that can be introduced without crossing ownership boundaries.
- Treat the updated static browser contract as part of the public shell boundary; when logic moves again, move the assertions with it in the same change.

## Remaining risks

- `app.js` is smaller but still large; later component/pane tasks must keep shrinking it carefully without reintroducing overlapping state paths.
- The legacy global compatibility bridge remains intentionally broad until later cleanup work can remove it safely.
- Adjacent merge/secondary-preview helpers are still shared with `app.js`; later tasks must keep those boundaries crisp to avoid drift across T07/T09 ownership lanes.
