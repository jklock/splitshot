# T01 — Baseline Truth Audit

## Metadata

| Field | Value |
| --- | --- |
| task-id | `T01` |
| status | tracked in `progress.md` |
| depends-on | `T00` |
| parallel-lane | `none` |
| risk | `medium` |
| touches-files | `activedev/00-index.md`, `activedev/modular.md`, `activedev/modularization/plan.md`, `activedev/modularization/audit.md`, `activedev/modularization/progress.md` |
| forbidden-files | `src/**`, `tests/**`, `docs/project/browser-control-qa-matrix.md`, `docs/project/browser-control-coverage-plan.md`, `docs/project/browser-full-e2e-qa-plan.md` |
| owned-tests-docs | planning docs, ownership appendix in `audit.md` |
| proof-file | `activedev/modularization/proof/PROOF-T01-runN.md` |

## Progress snapshot

Informational only; authoritative task state remains `activedev/modularization/progress.md`.

| Field | Value |
| --- | --- |
| current-status | `done` |
| last-synced | `2026-05-02` |
| owner | `copilot-orchestrator-20260502-t01-run1` |
| proof | `activedev/modularization/proof/PROOF-T01-run1.md` |
| notes | Verified live baseline facts, updated audited source docs, populated ownership anchors, and cleared the path to `T02` without introducing a new blocker. |

## Goal

Replace estimates with verified actuals and add exact ownership anchors so later extraction tasks can work without overlapping edits.

## Scope

In scope:

- verify current line counts, branch, and browser test inventory
- confirm missing QA-doc status
- update audited baseline facts in the source docs and `plan.md`
- populate `audit.md` with ownership anchors or line-range notes for shared hotspots

Out of scope:

- code changes in `src/`
- restoration of the missing QA docs themselves

## Preconditions

- [x] `T00` is `done`
- [x] the control workspace exists
- [x] current source docs still reflect the monolith, not a partially modularized codebase

## Implementation checklist

- [x] verify baseline shell facts from the live repo
- [x] update the audited-current-state sections in `00-index.md`, `modular.md`, and `plan.md`
- [x] append ownership anchors for `app.js`, `index.html`, `styles.css`, and shared browser tests to `audit.md`
- [x] record any unresolved ambiguity as a blocker before `T03`

## Validation

Use Tier A from `validation.md`.

Required scope:

- verify the audited numbers and file-status claims recorded in the proof file
- no browser suite rerun is required unless a test-supporting doc path changed

## Audit checks

Use the governance and baseline checks in `audit.md`:

- ownership appendix is populated
- shared hotspots have one current owner at a time
- later tasks have enough information to avoid overlap

## Handoff outputs

- audited actuals in the source docs and plan
- ownership appendix ready for `T03` and later extraction tasks

## Done criteria

- [x] audited values are recorded
- [x] ownership appendix is populated
- [x] unresolved ambiguity is either cleared or explicitly logged
- [x] proof file was written
- [x] `progress.md` was updated
