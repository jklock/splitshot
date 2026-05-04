# T09A — Settings and Metrics Panes

## Metadata

| Field | Value |
| --- | --- |
| task-id | `T09A` |
| status | tracked in `progress.md` |
| depends-on | `T08` |
| parallel-lane | `A` |
| risk | `medium` |
| touches-files | `src/splitshot/browser/static/panes/settings-pane.js`, `src/splitshot/browser/static/panes/metrics-pane.js`, `src/splitshot/browser/static/app.js`, `tests/browser/test_settings_e2e.py`, `tests/browser/test_metrics_e2e.py`, `tests/browser/test_settings_defaults_truth_gate.py`, `activedev/modularization/progress.md` |
| forbidden-files | `src/splitshot/browser/static/panes/project-pane.js`, `src/splitshot/browser/static/panes/merge-pane.js`, `src/splitshot/browser/static/panes/export-pane.js`, `src/splitshot/browser/static/panes/review-pane.js`, `src/splitshot/browser/static/panes/shotml-pane.js`, `src/splitshot/browser/static/panes/overlay-pane.js`, `src/splitshot/browser/static/panes/markers-pane.js`, `src/splitshot/browser/static/panes/timing-pane.js`, `tests/browser/test_merge_export_contracts.py`, `tests/browser/test_overlay_review_contracts.py` |
| owned-tests-docs | `tests/browser/test_settings_e2e.py`, `tests/browser/test_metrics_e2e.py`, `tests/browser/test_settings_defaults_truth_gate.py` |
| proof-file | `activedev/modularization/proof/PROOF-T09A-runN.md` |

## Progress snapshot

Informational only; authoritative task state remains `activedev/modularization/progress.md`.

| Field | Value |
| --- | --- |
| current-status | `pending` |
| last-synced | `2026-05-02` |
| blocker | `Awaiting T08 before the parallel A/B/C wave can open.` |

## Goal

Extract two lower-coupling panes in a parallel-safe lane after the scoring-pane pilot proves the pattern.

## Scope

In scope:

- extract `settings-pane.js`
- extract `metrics-pane.js`
- update only the owned `app.js` anchor blocks for these panes

Out of scope:

- merge, project, export, review, overlay, markers, timing, or shotml pane work
- shared test files owned by other lanes

## Preconditions

- [ ] `T08` is `done`
- [ ] no overlapping lane is editing the same `app.js` anchors
- [ ] settings and metrics ownership anchors are current in `audit.md`

## Implementation checklist

- [ ] extract settings pane logic without UI drift
- [ ] extract metrics pane logic without changing read-only outputs
- [ ] preserve layout/settings behaviors and defaults exactly

## Validation

Use Tier C from `validation.md`.

Required commands:

```text
uv run pytest tests/browser/test_settings_e2e.py tests/browser/test_metrics_e2e.py tests/browser/test_settings_defaults_truth_gate.py
```

## Audit checks

Use extraction-task checks from `audit.md`:

- only lane-A-owned files and anchor blocks changed
- no shared test ownership was violated
- settings defaults and metrics flows remain contract-compatible

## Handoff outputs

- extracted settings and metrics panes
- any notes needed by `T10`

## Done criteria

- [ ] both pane modules exist
- [ ] required tests pass
- [ ] proof file was written
- [ ] `progress.md` was updated
