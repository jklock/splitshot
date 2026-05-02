# T07 — Components Waveform and Overlay

## Metadata

| Field | Value |
| --- | --- |
| task-id | `T07` |
| status | tracked in `progress.md` |
| depends-on | `T06` |
| parallel-lane | `none` |
| risk | `high` |
| touches-files | `src/splitshot/browser/static/components/waveform.js`, `src/splitshot/browser/static/components/overlay-canvas.js`, `src/splitshot/browser/static/lib/waveform-state.js`, `src/splitshot/browser/static/app.js`, `tests/browser/test_timing_waveform_contracts.py`, `tests/browser/test_overlay_review_contracts.py`, `tests/browser/test_browser_interactions.py`, `activedev/modularization/progress.md` |
| forbidden-files | `src/splitshot/browser/static/panes/**`, `src/splitshot/browser/static/styles.css`, `tests/browser/test_merge_export_contracts.py` |
| owned-tests-docs | `tests/browser/test_timing_waveform_contracts.py`, `tests/browser/test_overlay_review_contracts.py`, `tests/browser/test_browser_interactions.py` |
| proof-file | `activedev/modularization/proof/PROOF-T07-runN.md` |

## Goal

Extract the most interaction-heavy shared components before pane extraction begins, while preserving waveform, overlay, and review-adjacent behavior exactly.

## Scope

In scope:

- waveform rendering and interaction extraction
- overlay-canvas extraction
- shared waveform-state module if needed
- `app.js` delegation to the new shared components

Out of scope:

- pane-specific ownership
- export, project, or scoring pane extraction
- CSS splitting

## Preconditions

- [ ] `T06` is `done`
- [ ] waveform/overlay ownership anchors are available in `audit.md`
- [ ] baseline interaction artifacts are available for comparison

## Implementation checklist

- [ ] extract waveform logic into a dedicated component module
- [ ] extract overlay-canvas logic into a dedicated component module
- [ ] isolate shared waveform state without changing behavior
- [ ] preserve all current drag, zoom, pan, and redraw behavior

## Validation

Use Tier B from `validation.md`.

Required commands:

```text
uv run pytest tests/browser/test_timing_waveform_contracts.py tests/browser/test_overlay_review_contracts.py tests/browser/test_browser_interactions.py
```

If audit scripts are rerun, explain any artifact diffs in the proof file.

## Audit checks

Use extraction-task checks from `audit.md`:

- no pane extraction leaked into this task
- waveform and overlay shared state boundaries are explicit
- `app.js` responsibility moved out of the monolith in the expected areas

## Handoff outputs

- extracted waveform and overlay components ready for pane extraction
- notes on any preserved compatibility shims

## Done criteria

- [ ] shared component files exist and are wired safely
- [ ] required tests pass
- [ ] proof file was written
- [ ] `progress.md` was updated
