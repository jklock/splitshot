# T00 — Foundation and Governance

## Metadata

| Field | Value |
| --- | --- |
| task-id | `T00` |
| status | tracked in `progress.md` |
| depends-on | `none` |
| parallel-lane | `none` |
| risk | `low` |
| touches-files | `activedev/modularization/plan.md`, `progress.md`, `orchestration-prompt.md`, `validation.md`, `audit.md`, `tasks/TEMPLATE.md`, `proof/README.md`, `activedev/00-index.md`, `activedev/modular.md` |
| forbidden-files | `src/**`, `tests/**`, `docs/project/browser-control-qa-matrix.md`, `docs/project/browser-control-coverage-plan.md`, `docs/project/browser-full-e2e-qa-plan.md` |
| owned-tests-docs | planning docs only |
| proof-file | `activedev/modularization/proof/PROOF-T00-runN.md` |

## Goal

Stand up the modularization control plane so every later task runs under one consistent set of rules for ownership, proof, validation, and audit.

## Scope

In scope:

- create the `activedev/modularization/` operating documents
- establish task ids, status conventions, proof naming, and lock protocol
- wire the source planning docs to the new control workspace

Out of scope:

- product-code changes
- browser test or QA doc restoration
- any change to UI behavior

## Preconditions

- [ ] branch is `modularization`
- [ ] no other modularization task is already claimed
- [ ] task ids are reserved in `progress.md`

## Implementation checklist

- [ ] create the control-plane documents listed in `plan.md`
- [ ] create the task template and proof rules
- [ ] create the initial task board in `progress.md`
- [ ] update `activedev/00-index.md` and `activedev/modular.md` to reference the new control workspace

## Validation

Use Tier A from `validation.md`.

Required scope:

- confirm the required files exist
- confirm task ids are consistent across `plan.md`, `progress.md`, and task files
- if no product code changed, record in proof why the full browser suite was not rerun

## Audit checks

Use the governance checks in `audit.md`:

- required control-plane files exist
- task naming is consistent
- no product-code files were changed

## Handoff outputs

- a complete control workspace under `activedev/modularization/`
- a task board ready for `T01`
- source docs linked to the control workspace

## Done criteria

- [ ] control-plane documents exist
- [ ] source planning docs point to the new workspace
- [ ] proof file was written
- [ ] `progress.md` was updated
