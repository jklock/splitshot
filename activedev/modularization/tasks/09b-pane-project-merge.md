# T09B — Project and Merge Panes

## Metadata

| Field | Value |
| --- | --- |
| task-id | `T09B` |
| status | tracked in `progress.md` |
| depends-on | `T08` |
| parallel-lane | `B` |
| risk | `high` |
| touches-files | `src/splitshot/browser/static/panes/project-pane.js`, `src/splitshot/browser/static/panes/merge-pane.js`, `src/splitshot/browser/static/app.js`, `tests/browser/test_project_lifecycle_contracts.py`, `tests/browser/test_merge_export_contracts.py`, `tests/browser/test_practiscore_session_api.py`, `tests/browser/test_practiscore_sync_controller.py`, `docs/userfacing/panes/project.md`, `docs/project/browser-control-qa-matrix.md`, `activedev/modularization/progress.md` |
| forbidden-files | `src/splitshot/browser/static/panes/export-pane.js`, `src/splitshot/browser/static/panes/review-pane.js`, `src/splitshot/browser/static/panes/overlay-pane.js`, `src/splitshot/browser/static/panes/markers-pane.js`, `src/splitshot/browser/static/panes/timing-pane.js`, `tests/browser/test_overlay_review_contracts.py` |
| owned-tests-docs | `tests/browser/test_project_lifecycle_contracts.py`, merge-owned assertions inside `tests/browser/test_merge_export_contracts.py`, `tests/browser/test_practiscore_session_api.py`, `tests/browser/test_practiscore_sync_controller.py`, `docs/userfacing/panes/project.md`, `docs/project/browser-control-qa-matrix.md` |
| proof-file | `activedev/modularization/proof/PROOF-T09B-runN.md` |

## Goal

Extract the project and merge panes while preserving the full current Project-pane experience, including PractiScore parity requirements.

## Scope

In scope:

- extract `project-pane.js`
- extract `merge-pane.js`
- preserve the manual `Select PractiScore File` fallback path and existing local controls
- update only the merge-owned assertions inside `test_merge_export_contracts.py`

Out of scope:

- export-pane ownership
- review-pane ownership
- overlay, markers, timing, or shotml pane extraction

## Preconditions

- [ ] `T08` is `done`
- [ ] lane B is not overlapping another active owner in `app.js`
- [ ] PractiScore parity rules from repository instructions are understood

## Implementation checklist

- [ ] extract `project-pane.js` without changing the current Project-pane UI contract
- [ ] extract `merge-pane.js` without changing merge behavior
- [ ] preserve `practiscore_session`, `practiscore_sync`, and `practiscore_options` browser contract expectations
- [ ] update owned project/merge docs and QA-matrix rows if required by the extraction

## Validation

Use Tier C from `validation.md`.

Required commands:

```text
uv run pytest tests/browser/test_project_lifecycle_contracts.py tests/browser/test_merge_export_contracts.py tests/browser/test_practiscore_session_api.py tests/browser/test_practiscore_sync_controller.py
```

Add `tests/browser/test_browser_static_ui.py` if shell markup or control ids change.

## Audit checks

Use extraction-task checks from `audit.md` plus the PractiScore repository rules:

- manual fallback path is preserved
- local Project-pane controls remain present
- only merge-owned assertions in the shared merge/export test file were changed
- docs/tests stayed in sync with the pane contract

## Handoff outputs

- extracted project and merge pane modules
- updated Project-pane docs and QA ownership notes if needed

## Done criteria

- [ ] both pane modules exist
- [ ] PractiScore parity requirements remain satisfied
- [ ] required tests pass
- [ ] proof file was written
- [ ] `progress.md` was updated
