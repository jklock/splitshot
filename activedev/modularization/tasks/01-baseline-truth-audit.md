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

- [ ] `T00` is `done`
- [ ] the control workspace exists
- [ ] current source docs still reflect the monolith, not a partially modularized codebase

## Implementation checklist

- [ ] verify baseline shell facts from the live repo
- [ ] update the audited-current-state sections in `00-index.md`, `modular.md`, and `plan.md`
- [ ] append ownership anchors for `app.js`, `index.html`, `styles.css`, and shared browser tests to `audit.md`
- [ ] record any unresolved ambiguity as a blocker before `T03`

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

- [ ] audited values are recorded
- [ ] ownership appendix is populated
- [ ] unresolved ambiguity is either cleared or explicitly logged
- [ ] proof file was written
- [ ] `progress.md` was updated
