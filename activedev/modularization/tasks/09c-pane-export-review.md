# T09C — Export and Review Panes

## Metadata

| Field | Value |
| --- | --- |
| task-id | `T09C` |
| status | tracked in `progress.md` |
| depends-on | `T08` |
| parallel-lane | `C` |
| risk | `high` |
| touches-files | `src/splitshot/browser/static/panes/export-pane.js`, `src/splitshot/browser/static/panes/review-pane.js`, `src/splitshot/browser/static/app.js`, `tests/browser/test_merge_export_contracts.py`, `tests/browser/test_overlay_review_contracts.py`, `tests/browser/test_browser_interactions.py`, `activedev/modularization/progress.md` |
| forbidden-files | `src/splitshot/browser/static/panes/project-pane.js`, `src/splitshot/browser/static/panes/merge-pane.js`, `src/splitshot/browser/static/panes/overlay-pane.js`, `src/splitshot/browser/static/panes/markers-pane.js`, `src/splitshot/browser/static/panes/timing-pane.js`, `tests/browser/test_practiscore_session_api.py`, `tests/browser/test_practiscore_sync_controller.py` |
| owned-tests-docs | export/review-owned assertions inside `tests/browser/test_merge_export_contracts.py`, review-owned assertions inside `tests/browser/test_overlay_review_contracts.py`, `tests/browser/test_browser_interactions.py` |
| proof-file | `activedev/modularization/proof/PROOF-T09C-runN.md` |

## Progress snapshot

Informational only; authoritative task state remains `activedev/modularization/progress.md`.

| Field | Value |
| --- | --- |
| current-status | `pending` |
| last-synced | `2026-05-02` |
| blocker | `Awaiting T08 before the parallel A/B/C wave can open.` |

## Goal

Extract the export and review panes without changing export controls, review box behavior, or shared overlay-adjacent workflows.

## Scope

In scope:

- extract `export-pane.js`
- extract `review-pane.js`
- update only export/review-owned assertions inside the shared browser test files

Out of scope:

- project/merge ownership
- overlay ownership
- markers/timing ownership

## Preconditions

- [ ] `T08` is `done`
- [ ] lane C has exclusive ownership of its `app.js` anchors
- [ ] shared-test ownership notes are current in `audit.md`

## Implementation checklist

- [ ] extract `export-pane.js` with no change to export UX or log workflow
- [ ] extract `review-pane.js` with no change to text-box or visibility behavior
- [ ] keep shared overlay/review workflows contract-compatible for `T09D`

## Validation

Use Tier C from `validation.md`.

Required commands:

```text
uv run pytest tests/browser/test_merge_export_contracts.py tests/browser/test_overlay_review_contracts.py tests/browser/test_browser_interactions.py
```

Add browser export or AV audits if the task packet owner changes export execution plumbing.

## Audit checks

Use extraction-task checks from `audit.md`:

- only export/review-owned assertions changed in shared test files
- export log and review visibility workflows remain identical
- no overlay-owned work leaked into this lane

## Handoff outputs

- extracted export and review pane modules
- stable review/overlay contract surface for `T09D`

## Done criteria

- [ ] both pane modules exist
- [ ] required tests pass
- [ ] proof file was written
- [ ] `progress.md` was updated
