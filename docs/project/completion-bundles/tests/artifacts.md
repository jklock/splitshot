# Test Modularization Artifact Plan

## Purpose

This file tracks the proof package required to call test modularization complete.

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

- Artifact:
  - Path:
  - Produced by:
  - Date:
  - Notes:

## Completion rule

Test modularization is not complete until every required artifact category has at least one linked proof item and those proof items agree with `outcome.md`, the app bundles, and the runner/docs taxonomy.
