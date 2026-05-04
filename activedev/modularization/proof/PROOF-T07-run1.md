# PROOF-T07-run1

- Task: `T07` — Components waveform and overlay
- Date: `2026-05-03`
- Owner: `copilot-orchestrator-20260503-t07-run1`
- Validation tier: `Tier B` (task packet override: exact required command was `uv run pytest tests/browser/test_timing_waveform_contracts.py tests/browser/test_overlay_review_contracts.py tests/browser/test_browser_interactions.py`)
- Result: `pass`

## Scope completed

- Created the T07-owned waveform and overlay modules:
  - `src/splitshot/browser/static/components/waveform.js`
  - `src/splitshot/browser/static/components/overlay-canvas.js`
  - `src/splitshot/browser/static/lib/waveform-state.js`
- Rewired `src/splitshot/browser/static/app.js` so waveform viewport math, waveform rendering, waveform pointer interaction handling, and the overlay video-frame scheduler delegate through the extracted factories instead of remaining inline in the monolith.
- Preserved the existing browser/global contract by keeping the legacy `app.js` function names as thin delegation wrappers, including:
  - `durationMs()`
  - `waveformWindow()`
  - `renderWaveform()`
  - `renderWaveformPlayhead()`
  - `handleWaveformPointerDown()` / `handleWaveformPointerMove()` / `handleWaveformPointerUp()`
  - `requestOverlayFrame()` / `cancelOverlayFrame()` / `startOverlayLoop()` / `stopOverlayLoop()`
- Updated the owned static browser contracts so the source-visible assertions now follow the extracted waveform and overlay-canvas boundaries rather than assuming every implementation detail still lives in `app.js`.
- Stabilized two owned browser tests uncovered during the required exact validation reruns:
  - `tests/browser/test_timing_waveform_contracts.py` now creates a project before uploading media, matching the explicit setup already used in the broader browser suites.
  - `tests/browser/test_browser_interactions.py` now waits for committed scoring state instead of relying on a fixed `250ms` timeout.

## Compatibility seams intentionally retained for T08+

The task packet required intentional seams to be documented. The following remain on purpose:

- `app.js` still owns the public wrapper functions listed above so existing render/event call sites and the legacy browser-global compatibility layer stay stable during the modularization sequence.
- `src/splitshot/browser/static/lib/waveform-state.js` owns waveform viewport persistence, navigator math, time mapping, and nearest-shot hit testing, while `src/splitshot/browser/static/components/waveform.js` owns the canvas render path and pointer-interaction flow. Later pane tasks should extend these seams rather than re-inlining the logic.
- `src/splitshot/browser/static/components/overlay-canvas.js` intentionally owns only the overlay frame scheduler seam (`request` / `cancel` / `start` / `stop`). The higher-coupling live overlay renderer (`renderLiveOverlay()` and adjacent popup/review overlay logic) intentionally remains in `app.js` for the later overlay/markers pane tasks.
- `installLegacyGlobalCompat()` remains intentionally broad so browser tests and existing runtime entry points can continue calling the legacy function names while the extraction sequence is incomplete.

## Validation performed

### Required command

The task packet required this exact command:

```text
uv run pytest tests/browser/test_timing_waveform_contracts.py tests/browser/test_overlay_review_contracts.py tests/browser/test_browser_interactions.py
```

That exact command was run after the final T07 extraction and test updates.

Passing result:

```text
==================== test session starts =====================
platform darwin -- Python 3.12.11, pytest-8.4.2, pluggy-1.6.0
PySide6 6.11.0 -- Qt runtime 6.11.0 -- Qt compiled 6.11.0
rootdir: /Volumes/Storage/GitHub/splitshot
configfile: pyproject.toml
plugins: cov-7.1.0, qt-4.5.0
collected 65 items

tests/browser/test_timing_waveform_contracts.py ...... [  9%]
..                                                     [ 12%]
tests/browser/test_overlay_review_contracts.py ....... [ 23%]
..........                                             [ 38%]
tests/browser/test_browser_interactions.py ........... [ 55%]
.............................                          [100%]

============== 65 passed in 1502.83s (0:25:02) ===============
```

### Validation notes

- The first exact-scope T07 run exposed two timing browser tests that were still relying on media upload into an empty project state. Those tests were updated within T07 ownership to create a project before uploading media, matching the explicit setup pattern already used in the broader browser suites.
- The second exact-scope T07 run exposed one scoring browser test that relied on a fixed `250ms` pause before asserting committed penalty state. That assertion was updated within T07 ownership to wait on the actual committed state instead.
- After those owned test updates, the exact required command passed unchanged.

## Audit performed

### Audit checks executed

- Confirmed only the T07-owned component/state/app/test/proof files were modified.
- Confirmed forbidden paths stayed untouched:
  - `src/splitshot/browser/static/panes/**`
  - `src/splitshot/browser/static/styles.css`
  - `tests/browser/test_merge_export_contracts.py`
- Confirmed the new waveform and overlay-canvas modules exist and that `app.js` now delegates through them while preserving the wrapper contract.
- Confirmed the owned static/browser tests were updated in the same run to reflect the new extraction boundaries and the validation-stability fixes required by the exact command.

### Audit command run

```text
printf 'OWNED_PATH_STATUS\n' && git status --short -- activedev/modularization/progress.md src/splitshot/browser/static/app.js src/splitshot/browser/static/components/waveform.js src/splitshot/browser/static/components/overlay-canvas.js src/splitshot/browser/static/lib/waveform-state.js tests/browser/test_timing_waveform_contracts.py tests/browser/test_overlay_review_contracts.py tests/browser/test_browser_interactions.py activedev/modularization/proof/PROOF-T07-run1.md && printf '\nFORBIDDEN_PATH_STATUS\n' && git status --short -- src/splitshot/browser/static/panes src/splitshot/browser/static/styles.css tests/browser/test_merge_export_contracts.py && printf '\nCOMPONENT_AND_STATE_FILES\n' && find src/splitshot/browser/static/components -maxdepth 1 -type f | sort && printf '\nSTATE_LIB_FILES\n' && find src/splitshot/browser/static/lib -maxdepth 1 -type f | sort && printf '\nAPP_SIZE\n' && wc -l src/splitshot/browser/static/app.js
```

### Audit results

Owned-path status:

```text
OWNED_PATH_STATUS
 M activedev/modularization/progress.md
 M src/splitshot/browser/static/app.js
 M tests/browser/test_browser_interactions.py
 M tests/browser/test_overlay_review_contracts.py
 M tests/browser/test_timing_waveform_contracts.py
?? src/splitshot/browser/static/components/overlay-canvas.js
?? src/splitshot/browser/static/components/waveform.js
?? src/splitshot/browser/static/lib/waveform-state.js
```

Forbidden-path status:

```text
FORBIDDEN_PATH_STATUS
```

Component file inventory:

```text
COMPONENT_AND_STATE_FILES
src/splitshot/browser/static/components/overlay-canvas.js
src/splitshot/browser/static/components/status-bar.js
src/splitshot/browser/static/components/video-player.js
src/splitshot/browser/static/components/waveform.js
```

State-lib inventory:

```text
STATE_LIB_FILES
src/splitshot/browser/static/lib/activity.js
src/splitshot/browser/static/lib/api.js
src/splitshot/browser/static/lib/event-bus.js
src/splitshot/browser/static/lib/keys.js
src/splitshot/browser/static/lib/layout.js
src/splitshot/browser/static/lib/processing.js
src/splitshot/browser/static/lib/store.js
src/splitshot/browser/static/lib/utils.js
src/splitshot/browser/static/lib/waveform-state.js
```

Current `app.js` size:

```text
APP_SIZE
   14463 src/splitshot/browser/static/app.js
```

### Audit conclusion

- T07 stayed within its owned file list.
- No forbidden pane/CSS/merge-export-contract paths were modified.
- The extracted waveform and overlay-canvas modules exist, `app.js` now delegates through them, and the browser contract remains available through the legacy wrapper surface.
- The owned browser contracts were updated in the same run and the exact required validation command passed.

## Adoption notes for T08+

- Continue the same dependency-injection pattern for later pane extraction work; do not collapse the wrapper seams back into `app.js`.
- T08 (scoring pane) should treat the waveform component/state seam as stable infrastructure and avoid re-owning waveform pointer or navigator math.
- T09D/T09E should continue from the current overlay/waveform split: keep the scheduler in `overlay-canvas.js`, and move higher-coupling overlay/marker renderer code only when those later task packets explicitly own it.
- When later tasks move more logic out of `app.js`, move the corresponding static browser assertions in the same change so the source-visible contracts stay honest.

## Remaining risks

- `app.js` is smaller but still large; later pane tasks must keep shrinking it carefully without crossing ownership boundaries.
- The overlay renderer itself still lives in `app.js`; later overlay/markers tasks must keep that extraction aligned with the existing review and popup contracts.
- The legacy global compatibility bridge remains intentionally broad until the later cleanup tasks can retire it safely.
