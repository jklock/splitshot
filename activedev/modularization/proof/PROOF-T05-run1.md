# PROOF-T05-run1

- Task: `T05` — Backbone runtime
- Date: `2026-05-03`
- Owner: `copilot-orchestrator-20260502-t05-run1`
- Validation tier: `Tier B` (task packet override: exact required command was `uv run pytest tests/browser/test_browser_static_ui.py tests/browser/test_browser_control.py tests/browser/test_browser_interactions.py`)
- Result: `pass`

## Scope completed

- Created the runtime backbone modules owned by T05:
  - `src/splitshot/browser/static/lib/activity.js`
  - `src/splitshot/browser/static/lib/api.js`
  - `src/splitshot/browser/static/lib/keys.js`
  - `src/splitshot/browser/static/lib/layout.js`
  - `src/splitshot/browser/static/lib/processing.js`
- Rewired `src/splitshot/browser/static/app.js` so the browser shell routes API coordination, layout resizing, keyboard handling, processing indicators, and activity flows through the extracted runtime modules.
- Preserved the existing browser contract and compatibility bridge rather than introducing competing global pathways.
- Updated the owned browser contract assertions in `tests/browser/test_browser_static_ui.py` to point at the extracted runtime module boundaries.
- Debugged and fixed same-project remote-state overwrite races that surfaced during the exact required browser validation scope, including:
  - stale API response suppression by request domain in `lib/api.js`
  - local draft preservation for in-flight merge and export edits
  - local overlay draft preservation for overlay badge positions and review text-box state
  - review/markers/browser-contract regressions discovered by the required suite

## Compatibility shims intentionally retained

The task packet required any temporary compatibility shims to be recorded. The following remain intentional and were preserved on purpose:

- `installLegacyGlobalCompat()` still bridges legacy page-global access to the module-backed runtime state.
- `window.__splitshotBackbone` remains exposed as the runtime seam for the extracted bus/store backbone.
- `window.__splitshotBootstrapMode = "module"` remains part of the browser bootstrap contract.

These shims are temporary but necessary to keep zero functional change while `app.js` still owns later-extraction surfaces.

## Validation performed

### Required command

The task packet required this exact command:

```text
uv run pytest tests/browser/test_browser_static_ui.py tests/browser/test_browser_control.py tests/browser/test_browser_interactions.py
```

That exact command was run after the runtime extraction work and final regression fixes.

Passing result:

```text
==================== test session starts =====================
platform darwin -- Python 3.12.11, pytest-8.4.2, pluggy-1.6.0
PySide6 6.11.0 -- Qt runtime 6.11.0 -- Qt compiled 6.11.0
rootdir: /Volumes/Storage/GitHub/splitshot
configfile: pyproject.toml
plugins: cov-7.1.0, qt-4.5.0
collected 133 items

tests/browser/test_browser_static_ui.py .............. [ 10%]
........                                               [ 16%]
tests/browser/test_browser_control.py ................ [ 28%]
...................................................... [ 69%]
.                                                      [ 69%]
tests/browser/test_browser_interactions.py ........... [ 78%]
.............................                          [100%]

============== 133 passed in 1908.28s (0:31:48) ==============
```

### Validation notes

- The first exact-scope T05 runs exposed browser regressions that were within T05 ownership: stale same-project state overwrites, stale static assertions pointing at pre-extraction locations, review text-box regressions, merge/export local-state clobbering, and popup motion-path edge cases.
- The fixes stayed within the T05 `touches-files` list.
- After those owned fixes, the exact same required command was rerun unchanged and passed.

## Audit performed

### Audit checks executed

- Confirmed the runtime backbone boundaries now exist as separate `lib/` modules for `activity`, `api`, `keys`, `layout`, and `processing`.
- Confirmed no pane/component extraction leaked into T05.
- Confirmed no CSS file owned by later tasks was modified.
- Confirmed the owned static browser contract was updated in the same run to reflect the new runtime delegation seams.
- Confirmed the compatibility shims above remain intentional and documented.

### Audit command run

```text
printf 'OWNED_PATH_STATUS\n' && git status --short -- activedev/modularization/progress.md src/splitshot/browser/static/app.js src/splitshot/browser/static/lib/api.js src/splitshot/browser/static/lib/layout.js src/splitshot/browser/static/lib/keys.js src/splitshot/browser/static/lib/processing.js src/splitshot/browser/static/lib/activity.js tests/browser/test_browser_static_ui.py tests/browser/test_browser_control.py tests/browser/test_browser_interactions.py activedev/modularization/proof/PROOF-T05-run1.md && printf '\nFORBIDDEN_PATH_STATUS\n' && git status --short -- src/splitshot/browser/static/components src/splitshot/browser/static/panes src/splitshot/browser/static/styles.css && printf '\nRUNTIME_LIB_FILES\n' && find src/splitshot/browser/static/lib -maxdepth 1 -type f | sort && printf '\nAPP_SIZE\n' && wc -l src/splitshot/browser/static/app.js
```

### Audit results

Owned-path status:

```text
OWNED_PATH_STATUS
 M activedev/modularization/progress.md
 M src/splitshot/browser/static/app.js
 M tests/browser/test_browser_static_ui.py
?? src/splitshot/browser/static/lib/activity.js
?? src/splitshot/browser/static/lib/api.js
?? src/splitshot/browser/static/lib/keys.js
?? src/splitshot/browser/static/lib/layout.js
?? src/splitshot/browser/static/lib/processing.js
```

Forbidden-path status:

```text
FORBIDDEN_PATH_STATUS
```

Runtime lib files present:

```text
RUNTIME_LIB_FILES
src/splitshot/browser/static/lib/activity.js
src/splitshot/browser/static/lib/api.js
src/splitshot/browser/static/lib/event-bus.js
src/splitshot/browser/static/lib/keys.js
src/splitshot/browser/static/lib/layout.js
src/splitshot/browser/static/lib/processing.js
src/splitshot/browser/static/lib/store.js
src/splitshot/browser/static/lib/utils.js
```

Current `app.js` size:

```text
APP_SIZE
   15008 src/splitshot/browser/static/app.js
```

### Audit conclusion

- T05 stayed within its owned file list.
- No pane/component paths or `styles.css` were modified.
- The runtime backbone modules exist and `app.js` routes through them while preserving the compatibility contract.
- The owned browser contract assertions were updated in the same run.

## Adoption notes for T06

- Continue extending the existing `appBus` / `appStore` / runtime backbone seam rather than introducing new global state entry points.
- Preserve `installLegacyGlobalCompat()` until later cleanup work can retire page-global access safely.
- The same-project draft-preservation pattern now protects merge, export, overlay badge position, and review text-box edits against late remote state; later tasks should reuse or carefully consolidate that pattern instead of bypassing it.

## Remaining risks

- `installLegacyGlobalCompat()` is still intentionally broad; later cleanup tasks must reduce it carefully without breaking the browser contract.
- `app.js` remains large even after runtime extraction; later component/pane tasks should keep shrinking it without reintroducing overlapping state paths.
- The local-draft preservation added here is correct for T05’s zero-drift goal, but later cleanup should centralize it once more of the shell is extracted.
