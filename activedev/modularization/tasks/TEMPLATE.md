# TXX — Task Template

## Metadata

| Field | Value |
| --- | --- |
| task-id | `TXX` |
| status | `pending` |
| depends-on | `none` |
| parallel-lane | `none` |
| risk | `low \| medium \| high` |
| touches-files | exhaustive allowed file list |
| forbidden-files | files and areas this task must not modify |
| owned-tests-docs | explicit tests/docs this task must update when needed |
| proof-file | `activedev/modularization/proof/PROOF-TXX-runN.md` |

## Goal

A concise statement of the outcome and why it matters.

## Scope

Describe what is in scope and what is intentionally out of scope.

## Preconditions

- [ ] dependencies are `done` in `progress.md`
- [ ] required baseline docs or ownership anchors exist
- [ ] the task can be claimed without overlapping active work

## Implementation checklist

- [ ] step 1
- [ ] step 2
- [ ] step 3

## Validation

List the required validation tier from `validation.md` and the exact commands or suites required for this task.

## Audit checks

List the required structural checks from `audit.md` for this task.

## Handoff outputs

Specify what the next task needs from this one.

## Done criteria

- [ ] only owned files were touched
- [ ] required validation passed
- [ ] required audit checks passed
- [ ] proof file was written
- [ ] `progress.md` was updated
