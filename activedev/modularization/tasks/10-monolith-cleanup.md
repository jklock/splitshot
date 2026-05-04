# T10 — Monolith Cleanup

## Metadata

| Field | Value |
| --- | --- |
| task-id | `T10` |
| status | tracked in `progress.md` |
| depends-on | `T09A`, `T09B`, `T09C`, `T09D`, `T09E` |
| parallel-lane | `none` |
| risk | `high` |
| touches-files | `src/splitshot/browser/static/app.js`, `src/splitshot/browser/static/lib/**`, `src/splitshot/browser/static/components/**`, `src/splitshot/browser/static/panes/**`, `tests/browser/test_browser_static_ui.py`, `tests/browser/test_browser_interactions.py`, `activedev/modularization/progress.md` |
| forbidden-files | `src/splitshot/browser/static/styles.css`, `src/splitshot/browser/static/index.html` unless strictly required by cleanup, `docs/project/browser-control-qa-matrix.md` |
| owned-tests-docs | targeted owned cleanup browser tests for the touched seams; shared contract migration suites belong to `T10.5` |
| proof-file | `activedev/modularization/proof/PROOF-T10-runN.md` |

## Progress snapshot

Informational only; authoritative task state remains `activedev/modularization/progress.md`.

| Field | Value |
| --- | --- |
| current-status | `pending` |
| last-synced | `2026-05-04` |
| blocker | `None after the control-plane split: finish the remaining owned cleanup implementation here, then hand any remaining shared-contract bridge work to T10.5.` |

## Goal

Finish all owned monolith-cleanup implementation before the cleanup bridge starts: shrink `app.js` to bootstrap plus only documented bridge anchors, move any still-app-owned cleanup seams into shared `lib/` modules, and leave `T10.5` with only cross-lane contract migration / leftover consolidation that truly needs shared ownership.

## Scope

In scope:

- move `installLegacyGlobalCompat()` out of `app.js` into `lib/global-compat.js`
- remove obsolete monolithic `render()` / `wireEvents()` scaffolding, dead wrappers, and retired payload-sync helpers that are fully owned by this task
- centralize still-app-owned same-project draft / refresh preservation and debounce / flush orchestration into shared `lib/` seams when real reuse exists
- resolve the `data-table.js` deferral as create-or-waive if cleanup proves a real shared helper is warranted
- reduce `app.js` to bootstrap plus only the temporary bridge anchors that `T10.5` must retire next

Out of scope:

- CSS split
- shared browser-contract migration outside this task's owned touch list; that bridge work belongs to `T10.5`
- final documentation / audit certification
- broad browser-suite / canonical-runner / audit certification; record targeted implementation validation only and defer the wide gate to `T12`
- intentional UI changes

## Preconditions

- [ ] all pane extraction tasks are `done`
- [ ] the targeted owned suites for the cleanup slice being edited are green, or any known failures are already understood and isolated before more cleanup lands

## Implementation checklist

- [ ] move `installLegacyGlobalCompat()` into `lib/global-compat.js` and keep only the bootstrap call in `app.js`
- [ ] remove or delegate any remaining dead wrappers / duplicate logic in `app.js`
- [ ] centralize same-project draft / refresh preservation if it is still app-owned after the shell-runtime extraction
- [ ] centralize app-level debounce / flush orchestration if it is still app-owned after the pane extractions
- [ ] resolve `data-table.js` as create-or-permanent-waiver if cleanup shows real multi-area reuse
- [ ] record an explicit handoff list of temporary bridge anchors, retained bare globals, and shared contract migrations that `T10.5` must clear immediately next

## Validation

Use targeted Tier D support from `validation.md`.

During `T10`, rerun only the narrowest owned tests that cover each edited cleanup slice. Prefer individual test functions or `-k` filters in `test_browser_static_ui.py` and `test_browser_interactions.py`, and stop / hand off to `T10.5` if a cleanup step would require migrating shared browser-contract suites outside this task's touch list.

Example commands:

```text
uv run pytest tests/browser/test_browser_static_ui.py::test_name
uv run pytest tests/browser/test_browser_interactions.py -k "touched-flow"
```

Record the exact commands in proof and explicitly defer broad browser / audit certification to `T12`.

## Audit checks

Use cleanup/certification checks from `audit.md`:

- retired monolith paths are actually removed
- no ghost wrappers remain without purpose
- `app.js` is materially smaller and narrower in responsibility

## Handoff outputs

- cleaned monolith with `app.js` reduced to bootstrap plus only documented bridge anchors
- explicit handoff list for `T10.5` covering temporary bridge anchors, retained bare globals, wrapper-retirement decisions, and any residual shared-contract migrations
- ready state for `T10.5` cleanup bridge work

## Done criteria

- [ ] retired monolith logic is removed
- [ ] all owned cleanup implementation is complete
- [ ] `app.js` is bootstrap plus only the temporary bridge anchors explicitly documented for `T10.5`
- [ ] targeted validation for each touched cleanup slice passed
- [ ] proof file was written
- [ ] `progress.md` was updated
