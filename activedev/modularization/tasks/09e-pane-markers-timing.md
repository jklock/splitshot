# T09E — Markers and Timing Panes

## Metadata

| Field | Value |
| --- | --- |
| task-id | `T09E` |
| status | tracked in `progress.md` |
| depends-on | `T09D` |
| parallel-lane | `E` |
| risk | `high` |
| touches-files | `src/splitshot/browser/static/panes/markers-pane.js`, `src/splitshot/browser/static/panes/timing-pane.js`, `src/splitshot/browser/static/app.js`, `tests/browser/test_timing_waveform_contracts.py`, `tests/browser/test_browser_interactions.py`, `tests/browser/test_overlay_review_contracts.py`, `tests/browser/test_browser_remaining_controls_e2e.py`, `activedev/modularization/progress.md` |
| forbidden-files | `src/splitshot/browser/static/panes/project-pane.js`, `src/splitshot/browser/static/panes/merge-pane.js`, `src/splitshot/browser/static/panes/export-pane.js`, `src/splitshot/browser/static/panes/review-pane.js`, `src/splitshot/browser/static/panes/overlay-pane.js`, `src/splitshot/browser/static/styles.css` |
| owned-tests-docs | `tests/browser/test_timing_waveform_contracts.py`, markers/timing-owned assertions in `tests/browser/test_overlay_review_contracts.py`, `tests/browser/test_browser_interactions.py`, `tests/browser/test_browser_remaining_controls_e2e.py` |
| proof-file | `activedev/modularization/proof/PROOF-T09E-runN.md` |

## Goal

Extract the highest-coupling panes last, preserving timing workbench behavior, marker editing, navigation, and all related waveform interactions exactly.

## Scope

In scope:

- extract `markers-pane.js`
- extract `timing-pane.js`
- update only the markers/timing-owned assertions in the shared tests

Out of scope:

- CSS split
- final cleanup
- changes to already extracted pane modules outside required compatibility hooks

## Preconditions

- [ ] `T09D` is `done`
- [ ] waveform, overlay, and review contract surfaces are stable
- [ ] markers/timing ownership anchors are current in `audit.md`

## Implementation checklist

- [ ] extract `markers-pane.js` without changing edit-mode or workbench behavior
- [ ] extract `timing-pane.js` without changing timing table, timing event, or waveform interactions
- [ ] preserve keyboard, selection, and seek behavior

## Validation

Use Tier C from `validation.md`.

Required commands:

```text
uv run pytest tests/browser/test_timing_waveform_contracts.py tests/browser/test_overlay_review_contracts.py tests/browser/test_browser_interactions.py tests/browser/test_browser_remaining_controls_e2e.py
```

## Audit checks

Use extraction-task checks from `audit.md`:

- only lane-E-owned assertions changed in shared tests
- high-coupling interaction surfaces remain modular but behavior-identical
- no CSS or unrelated pane work leaked into this lane

## Handoff outputs

- extracted markers and timing panes
- final pane-extraction notes for `T10`

## Done criteria

- [ ] both pane modules exist
- [ ] required tests pass
- [ ] proof file was written
- [ ] `progress.md` was updated
