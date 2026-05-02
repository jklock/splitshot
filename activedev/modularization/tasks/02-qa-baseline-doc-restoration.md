# T02 — QA Baseline Document Restoration

## Metadata

| Field | Value |
| --- | --- |
| task-id | `T02` |
| status | tracked in `progress.md` |
| depends-on | `T01` |
| parallel-lane | `none` |
| risk | `medium` |
| touches-files | `docs/project/browser-control-qa-matrix.md`, `docs/project/browser-control-coverage-plan.md`, `docs/project/browser-full-e2e-qa-plan.md`, `docs/README.md`, `docs/project/DEVELOPING.md`, `docs/tests/TEST_SUITE_GUIDE.md`, `tests/browser/test_browser_control_inventory_audit.py`, `tests/browser/test_browser_control_coverage_matrix.py`, `activedev/modularization/progress.md` |
| forbidden-files | `src/**`, `activedev/modularization/plan.md`, task packets unrelated to QA-doc restoration |
| owned-tests-docs | restored QA docs and the two browser tests that enforce them |
| proof-file | `activedev/modularization/proof/PROOF-T02-runN.md` |

## Goal

Restore the missing browser QA documents so the modularization program can validate zero-UX-delta against an explicit control inventory and QA matrix.

## Scope

In scope:

- create the missing QA docs in `docs/project/`
- align their wording with current browser tests and developer docs
- update the enforcing tests only as needed to match the restored documentation contract

Out of scope:

- browser product-code changes
- modular extraction work

## Preconditions

- [ ] `T01` is `done`
- [ ] the current control inventory has been audited
- [ ] the task owner understands the current browser pane/control surface

## Implementation checklist

- [ ] author `browser-control-qa-matrix.md`
- [ ] author `browser-control-coverage-plan.md`
- [ ] author `browser-full-e2e-qa-plan.md`
- [ ] reconcile `docs/README.md`, `docs/project/DEVELOPING.md`, and `docs/tests/TEST_SUITE_GUIDE.md`
- [ ] update the enforcing browser tests if their assertions require it

## Validation

Use Tier A from `validation.md`.

Required commands:

```text
uv run pytest tests/browser/test_browser_control_inventory_audit.py tests/browser/test_browser_control_coverage_matrix.py
```

## Audit checks

Use the governance and shared-doc checks in `audit.md`:

- the restored docs match current browser reality
- the enforcing tests and docs agree
- no product-code files were touched

## Handoff outputs

- restored QA docs for later tasks to update in sync
- passing control-inventory and QA-matrix tests

## Done criteria

- [ ] all three QA docs exist
- [ ] the enforcing tests pass
- [ ] related developer docs are synchronized
- [ ] proof file was written
- [ ] `progress.md` was updated
