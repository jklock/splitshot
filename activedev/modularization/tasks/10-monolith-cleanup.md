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
| owned-tests-docs | full cleanup-related browser tests required by the task packet |
| proof-file | `activedev/modularization/proof/PROOF-T10-runN.md` |

## Progress snapshot

Informational only; authoritative task state remains `activedev/modularization/progress.md`.

| Field | Value |
| --- | --- |
| current-status | `blocked` |
| last-synced | `2026-05-03` |
| blocker | `The workspace is recovered to a healthy modularized baseline, but the remaining cleanup is blocked by shared browser-contract tests and runtime globals that still pin app.js wrapper/compat seams outside the current T10 touch list; see proof/PROOF-T10-run1.md.` |

## Goal

Delete the retired monolithic rendering/event-wiring scaffolding after all panes and shared components have moved to dedicated modules.

## Scope

In scope:

- remove obsolete monolithic `render()`/`wireEvents()` paths and retired payload-sync helpers
- remove compatibility shims that are no longer needed
- reduce `app.js` toward bootstrap-only responsibility

Out of scope:

- CSS split
- final documentation certification
- intentional UI changes

## Preconditions

- [ ] all pane extraction tasks are `done`
- [ ] no active lane still relies on a temporary compatibility shim
- [ ] shared browser suites are passing before cleanup starts

## Implementation checklist

- [ ] remove retired monolith functions and wrappers
- [ ] remove dead globals that no longer serve compatibility
- [ ] verify bootstrap responsibility stays in `app.js` and feature logic lives elsewhere

## Validation

Use Tier D from `validation.md`.

Required commands:

```text
uv run pytest tests/browser/
uv run python scripts/testing/run_test_suite.py --mode all-together --format table
```

## Audit checks

Use cleanup/certification checks from `audit.md`:

- retired monolith paths are actually removed
- no ghost wrappers remain without purpose
- `app.js` is materially smaller and narrower in responsibility

## Handoff outputs

- cleaned monolith with bootstrap-only `app.js`
- ready state for `T11` CSS work

## Done criteria

- [ ] retired monolith logic is removed
- [ ] required test suites pass
- [ ] proof file was written
- [ ] `progress.md` was updated
