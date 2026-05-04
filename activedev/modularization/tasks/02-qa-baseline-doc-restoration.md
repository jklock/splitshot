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

## Progress snapshot

Informational only; authoritative task state remains `activedev/modularization/progress.md`.

| Field | Value |
| --- | --- |
| current-status | `done` |
| last-synced | `2026-05-02` |
| owner | `copilot-orchestrator-20260502-t02-run1` |
| proof | `activedev/modularization/proof/PROOF-T02-run1.md` |
| notes | Restored the three QA docs, reconciled related developer docs, and passed the Tier A doc-audit test gate after repairing a broken local `.venv`. |

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

- [x] `T01` is `done`
- [x] the current control inventory has been audited
- [x] the task owner understands the current browser pane/control surface

## Implementation checklist

- [x] author `browser-control-qa-matrix.md`
- [x] author `browser-control-coverage-plan.md`
- [x] author `browser-full-e2e-qa-plan.md`
- [x] reconcile `docs/README.md`, `docs/project/DEVELOPING.md`, and `docs/tests/TEST_SUITE_GUIDE.md`
- [x] update the enforcing browser tests if their assertions require it

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

- [x] all three QA docs exist
- [x] the enforcing tests pass
- [x] related developer docs are synchronized
- [x] proof file was written
- [x] `progress.md` was updated
