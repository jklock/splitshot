# T09D — ShotML and Overlay Panes

## Metadata

| Field | Value |
| --- | --- |
| task-id | `T09D` |
| status | tracked in `progress.md` |
| depends-on | `T09C` |
| parallel-lane | `D` |
| risk | `high` |
| touches-files | `src/splitshot/browser/static/panes/shotml-pane.js`, `src/splitshot/browser/static/panes/overlay-pane.js`, `src/splitshot/browser/static/app.js`, `tests/browser/test_overlay_review_contracts.py`, `tests/browser/test_timing_waveform_contracts.py`, `tests/browser/test_browser_interactions.py`, `activedev/modularization/progress.md` |
| forbidden-files | `src/splitshot/browser/static/panes/project-pane.js`, `src/splitshot/browser/static/panes/merge-pane.js`, `src/splitshot/browser/static/panes/export-pane.js`, `src/splitshot/browser/static/panes/review-pane.js`, `src/splitshot/browser/static/panes/markers-pane.js`, `src/splitshot/browser/static/panes/timing-pane.js` |
| owned-tests-docs | overlay-owned assertions inside `tests/browser/test_overlay_review_contracts.py`, `tests/browser/test_timing_waveform_contracts.py`, `tests/browser/test_browser_interactions.py` |
| proof-file | `activedev/modularization/proof/PROOF-T09D-runN.md` |

## Goal

Extract the ShotML and overlay panes after the review-side contracts are stable, preserving all current overlay, threshold, proposal, and confidence-review behavior.

## Scope

In scope:

- extract `shotml-pane.js`
- extract `overlay-pane.js`
- update only overlay-owned assertions in shared contract tests

Out of scope:

- review-pane ownership
- markers/timing ownership
- CSS splitting

## Preconditions

- [ ] `T09C` is `done`
- [ ] shared review/overlay ownership notes are current
- [ ] lane D has exclusive ownership of its `app.js` anchors

## Implementation checklist

- [ ] extract `shotml-pane.js` without changing current ShotML UX
- [ ] extract `overlay-pane.js` without changing overlay controls or rendering behavior
- [ ] preserve interaction with waveform and review components

## Validation

Use Tier C from `validation.md`.

Required commands:

```text
uv run pytest tests/browser/test_overlay_review_contracts.py tests/browser/test_timing_waveform_contracts.py tests/browser/test_browser_interactions.py
```

Run the UI surface audit if overlay rendering surfaces changed.

## Audit checks

Use extraction-task checks from `audit.md`:

- only overlay-owned assertions changed in shared test files
- no review-owned work leaked back into this lane
- overlay and ShotML boundaries align with the modular architecture plan

## Handoff outputs

- extracted shotml and overlay panes
- stable prerequisites for `T09E`

## Done criteria

- [ ] both pane modules exist
- [ ] required tests pass
- [ ] proof file was written
- [ ] `progress.md` was updated
