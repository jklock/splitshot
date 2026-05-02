# T08 — Pilot Scoring Pane

## Metadata

| Field | Value |
| --- | --- |
| task-id | `T08` |
| status | tracked in `progress.md` |
| depends-on | `T07` |
| parallel-lane | `none` |
| risk | `high` |
| touches-files | `src/splitshot/browser/static/panes/pane-base.js`, `src/splitshot/browser/static/panes/scoring-pane.js`, `src/splitshot/browser/static/app.js`, `tests/browser/test_scoring_metrics_contracts.py`, `tests/browser/test_browser_interactions.py`, `activedev/modularization/progress.md` |
| forbidden-files | `src/splitshot/browser/static/panes/settings-pane.js`, `src/splitshot/browser/static/panes/project-pane.js`, `src/splitshot/browser/static/panes/merge-pane.js`, `src/splitshot/browser/static/panes/review-pane.js`, `src/splitshot/browser/static/panes/overlay-pane.js`, `src/splitshot/browser/static/panes/markers-pane.js`, `src/splitshot/browser/static/panes/timing-pane.js` |
| owned-tests-docs | `tests/browser/test_scoring_metrics_contracts.py`, `tests/browser/test_browser_interactions.py` |
| proof-file | `activedev/modularization/proof/PROOF-T08-runN.md` |

## Goal

Prove the pane-extraction pattern with the least-coupled pane before parallel pane work begins.

## Scope

In scope:

- create the pane base abstraction
- extract the scoring pane into its own module
- remove scoring responsibilities from the owned `app.js` anchor blocks

Out of scope:

- extraction of any other pane
- cleanup of all monolith scaffolding
- CSS changes

## Preconditions

- [ ] `T07` is `done`
- [ ] component extraction is stable
- [ ] scoring-pane ownership anchors are present in `audit.md`

## Implementation checklist

- [ ] create `pane-base.js`
- [ ] extract `scoring-pane.js`
- [ ] delegate from `app.js` to the scoring pane module
- [ ] preserve scoring behavior and selected-shot interactions exactly

## Validation

Use Tier C from `validation.md`.

Required commands:

```text
uv run pytest tests/browser/test_scoring_metrics_contracts.py tests/browser/test_browser_interactions.py
```

## Audit checks

Use extraction-task checks from `audit.md`:

- pane-base abstraction is generic and not scoring-specific glue in disguise
- no other pane work leaked into `T08`
- scoring extraction reduced monolithic responsibility in the expected anchor blocks

## Handoff outputs

- proven pane-extraction pattern
- notes that unblock `T09A`, `T09B`, and `T09C`

## Done criteria

- [ ] `pane-base.js` exists
- [ ] `scoring-pane.js` owns scoring behavior
- [ ] required tests pass
- [ ] proof file was written
- [ ] `progress.md` was updated
