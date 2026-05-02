# T06 — Components Shell

## Metadata

| Field | Value |
| --- | --- |
| task-id | `T06` |
| status | tracked in `progress.md` |
| depends-on | `T05` |
| parallel-lane | `none` |
| risk | `medium` |
| touches-files | `src/splitshot/browser/static/components/status-bar.js`, `src/splitshot/browser/static/components/video-player.js`, `src/splitshot/browser/static/components/data-table.js`, `src/splitshot/browser/static/app.js`, `tests/browser/test_browser_static_ui.py`, `tests/browser/test_browser_control.py`, `tests/browser/test_project_lifecycle_contracts.py`, `activedev/modularization/progress.md` |
| forbidden-files | `src/splitshot/browser/static/components/waveform.js`, `src/splitshot/browser/static/components/overlay-canvas.js`, `src/splitshot/browser/static/panes/**`, `src/splitshot/browser/static/styles.css` |
| owned-tests-docs | `tests/browser/test_browser_static_ui.py`, `tests/browser/test_browser_control.py`, `tests/browser/test_project_lifecycle_contracts.py` |
| proof-file | `activedev/modularization/proof/PROOF-T06-runN.md` |

## Goal

Extract the lower-risk shared components that shape the shell but do not yet require full pane ownership.

## Scope

In scope:

- status-bar extraction
- video-player extraction
- shared table helper extraction
- safe `app.js` delegation to those components

Out of scope:

- waveform and overlay-canvas extraction
- pane ownership changes
- stylesheet splitting

## Preconditions

- [ ] `T05` is `done`
- [ ] backbone runtime modules are available
- [ ] component ownership anchors are current in `audit.md`

## Implementation checklist

- [ ] extract `status-bar.js`
- [ ] extract `video-player.js`
- [ ] extract `data-table.js` only if reused by more than one later area
- [ ] keep DOM output and shell behavior unchanged

## Validation

Use Tier B from `validation.md`.

Required commands:

```text
uv run pytest tests/browser/test_browser_static_ui.py tests/browser/test_browser_control.py tests/browser/test_project_lifecycle_contracts.py
```

## Audit checks

Use extraction-task checks from `audit.md`:

- component boundaries are clean
- waveform and pane logic did not leak into this task
- `app.js` continues to shrink in responsibility

## Handoff outputs

- extracted shell components ready for `T07`
- notes on any shared rendering seams

## Done criteria

- [ ] component files exist and are wired safely
- [ ] required tests pass
- [ ] proof file was written
- [ ] `progress.md` was updated
