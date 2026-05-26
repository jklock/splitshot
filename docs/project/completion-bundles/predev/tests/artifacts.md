# Test Modularization Artifact Plan

## Purpose

This file tracks the proof package required to call test modularization complete.

Current normalized lane status: `planning baseline`

Cross-lane summary authority: `../../MASTER_STATUS.md`

This lane does not yet have acceptance evidence because it has not had a dedicated execution pass. The canonical full-suite baseline is required context, not proof of modularization completion.

## Required evidence categories

### 1. Ownership evidence

Capture and link proof for:

- current test ownership inventory
- target suite structure
- shared versus app-owned lane rules
- migration notes for mixed tests

### 2. Suite evidence

Record exact outputs or references for:

- Stage-owned suite targets
- Match-owned suite targets
- Performance-owned suite targets
- shared-shell/backend suite targets
- Stage, Match, and Performance e2e targets

### 3. Fixture and artifact evidence

Capture and link proof for:

- allowed shared fixtures
- app-local fixtures and helpers
- deterministic media rules
- isolated artifact/output paths for app e2e runs

### 4. Documentation evidence

Link all synchronized doc updates for:

- `docs/tests/TEST_SUITE_GUIDE.md`
- `docs/project/browser-control-qa-matrix.md`
- `docs/project/browser-control-coverage-plan.md`
- `docs/project/browser-full-e2e-qa-plan.md`
- app bundle docs that reference suite ownership

## Expected artifact locations

Use repo artifact locations rather than temporary scratch paths whenever possible.

- Test run summary:
  - Expected path: `artifacts/test-run.json` or suite-specific output
  - Notes: prefer canonical runner output when used
- Ownership / migration notes:
  - Expected path: repo-relative docs or artifact files
  - Notes: include moved or split test references
- App e2e outputs:
  - Expected path: `artifacts/` or app-specific output path
  - Notes: keep Stage, Match, and Performance outputs distinct
- Doc diffs / references:
  - Expected path: repo-relative paths
  - Notes: include PR or commit reference when available

## Artifact ledger

- Artifact: Canonical cross-lane validation baseline
  - Path: `artifacts/current-all-together.json`
  - Produced by: `./.venv/bin/python scripts/testing/run_test_suite.py --mode all-together --format table --raw-output artifacts/current-all-together.log --json-output artifacts/current-all-together.json`
  - Date: `2026-05-24`
  - Notes: `649 passed in 1718.96s (0:28:38)`; validates the current repo baseline after the Stage/Match/Performance work, but does **not** by itself close the Tests modularization lane.

- Artifact:
  - Path:
  - Produced by:
  - Date:
  - Notes:

## Completion rule

Test modularization is not complete until the dedicated tests pass closes `TST-001` through `TST-009`, every required artifact category has at least one linked proof item, and those proof items agree with `outcome.md`, the app bundles, and the runner/docs taxonomy.
