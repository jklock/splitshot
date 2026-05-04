# PROOF-T04-run1

- Task: `T04` — Backbone core
- Date: `2026-05-02`
- Owner: `copilot-orchestrator-20260502-t04-run1`
- Validation tier: `Tier B` (task packet override: exact required command was `uv run pytest tests/browser/test_browser_static_ui.py tests/browser/test_browser_control.py`)
- Result: `pass`

## Scope completed

- Created `src/splitshot/browser/static/lib/utils.js` for zero-dependency shared helpers.
- Created `src/splitshot/browser/static/lib/event-bus.js` with a thin pub/sub API.
- Created `src/splitshot/browser/static/lib/store.js` with a thin mutable state container API.
- Delegated the owned `app.js` backbone-core seam to those modules without changing browser-visible behavior.
- Kept the existing module-mode compatibility contract intact by bridging the new store-backed state setters through the legacy global shim.
- Updated the owned static shell contract in `tests/browser/test_browser_static_ui.py` so it asserts the T04 delegation boundary rather than the old pre-extraction helper locations.

## Validation performed

### Required command

The task packet required this exact command:

```text
uv run pytest tests/browser/test_browser_static_ui.py tests/browser/test_browser_control.py
```

The first run surfaced three static-contract failures because the owned assertions still expected pre-extraction helper bodies and direct `selectedShotId` assignment text inside `app.js`:

```text
FAILED tests/browser/test_browser_static_ui.py::test_browser_ui_guards_preview_failures_and_drag_resize
FAILED tests/browser/test_browser_static_ui.py::test_browser_display_names_strip_session_uuid_prefixes
FAILED tests/browser/test_browser_static_ui.py::test_browser_client_validates_remote_state_shape_and_restores_server_selection
=================== 3 failed, 90 passed in 548.16s (0:09:08) ===================
```

The fix stayed within T04 ownership: the static UI test was updated to assert the new `setSelectedShotIdValue(...)` delegation in `app.js` and the extracted UUID-prefix stripping helper in `lib/utils.js`.

After that owned-test correction, the exact same required command was rerun unchanged and passed:

```text
uv run pytest tests/browser/test_browser_static_ui.py tests/browser/test_browser_control.py
```

Passing result:

```text
============================= test session starts ==============================
platform darwin -- Python 3.12.11, pytest-8.4.2, pluggy-1.6.0
PySide6 6.11.0 -- Qt runtime 6.11.0 -- Qt compiled 6.11.0
rootdir: /Volumes/Storage/GitHub/splitshot
configfile: pyproject.toml
plugins: cov-7.1.0, qt-4.5.0
collected 93 items

tests/browser/test_browser_static_ui.py ......................           [ 23%]
tests/browser/test_browser_control.py .................................. [ 60%]
.....................................                                    [100%]

======================== 93 passed in 553.85s (0:09:13) ========================
```

### Validation notes

- The exact Tier B command required by the T04 task packet was run and passed.
- No broader browser suite was rerun because the task packet explicitly narrowed validation to this command and the implementation stayed within the owned backbone-core and static-contract paths.

## Audit performed

### Audit checks executed

- Confirmed the new module boundaries match T04 ownership: only `utils.js`, `event-bus.js`, and `store.js` were added under `src/splitshot/browser/static/lib/`.
- Confirmed no runtime-only backbone files owned by `T05` were touched.
- Confirmed the owned static UI contract was updated in the same run to reflect the new delegation boundary.
- Confirmed the compatibility shim remains intentional rather than accidental: `app.js` bridges `state`, `selectedShotId`, and `activeTool` through explicit setter helpers and exposes `window.__splitshotBackbone` for later extraction work.
- Confirmed `app.js` responsibility moved in the intended direction by importing shared helpers from the new backbone modules instead of owning those helper implementations inline.

### Audit command run

```text
printf 'OWNED_PATH_STATUS\n' && git status --short -- activedev/modularization/progress.md src/splitshot/browser/static/app.js src/splitshot/browser/static/lib/utils.js src/splitshot/browser/static/lib/event-bus.js src/splitshot/browser/static/lib/store.js tests/browser/test_browser_static_ui.py activedev/modularization/proof/PROOF-T04-run1.md && printf '\nFORBIDDEN_PATH_STATUS\n' && git status --short -- src/splitshot/browser/static/lib/api.js src/splitshot/browser/static/lib/layout.js src/splitshot/browser/static/lib/keys.js src/splitshot/browser/static/components src/splitshot/browser/static/panes && printf '\nSTATIC_LIB_FILES\n' && find src/splitshot/browser/static/lib -maxdepth 1 -type f | sort && printf '\nAPP_SIZE\n' && wc -l src/splitshot/browser/static/app.js
```

### Audit results

Owned-path status:

```text
OWNED_PATH_STATUS
 M activedev/modularization/progress.md
 M src/splitshot/browser/static/app.js
 M tests/browser/test_browser_static_ui.py
?? activedev/modularization/proof/PROOF-T04-run1.md
?? src/splitshot/browser/static/lib/event-bus.js
?? src/splitshot/browser/static/lib/store.js
?? src/splitshot/browser/static/lib/utils.js
```

Forbidden-path status:

```text
FORBIDDEN_PATH_STATUS
```

Extracted backbone-core lib files:

```text
STATIC_LIB_FILES
src/splitshot/browser/static/lib/event-bus.js
src/splitshot/browser/static/lib/store.js
src/splitshot/browser/static/lib/utils.js
```

Current `app.js` size:

```text
APP_SIZE
   15206 src/splitshot/browser/static/app.js
```

### Audit conclusion

- T04 stayed within its owned file list.
- No `T05` runtime-backbone files or pane/component paths were modified.
- The new module boundaries align with the task packet: utility helpers, event bus, and store exist as separate files and are consumed from `app.js`.
- The static test updates remained within the T04-owned browser contract surface.
- The compatibility layer remains intentionally broad for now, but the new backbone seam is in place for later runtime extraction.

## Delegation notes for T05

- Extend runtime coordination from the new `store` / `event-bus` seam rather than adding fresh global pathways.
- Keep `api`, `layout`, `processing`, and `activity` extraction separate from the zero-dependency helpers introduced here.
- Preserve the existing `installLegacyGlobalCompat()` bridge until the later cleanup task can retire page-global access safely.

## Remaining risks

- `installLegacyGlobalCompat()` is still large and intentionally temporary; later tasks must reduce it carefully without breaking the browser contract.
- The new store currently synchronizes only the initial backbone state (`state`, `selectedShotId`, and `activeTool`). That is sufficient for T04, but T05 must extend runtime module adoption without reintroducing overlapping state paths.
