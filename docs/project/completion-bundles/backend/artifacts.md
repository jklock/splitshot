# Shared Backend Artifact Plan

## Purpose

This file tracks the proof package required to call the shared backend complete.

## Required evidence categories

### 1. Test evidence

Record exact test outputs for shared backend coverage:

- route registration and contract tests
- browser state serialization tests
- persistence and reopen-flow tests
- import and PractiScore tests
- workspace backend tests used by Match
- library backend tests used by Performance

### 2. Contract evidence

Capture and link proof for:

- route ownership mapping
- `/api/state` summary payload expectations
- status and error behavior for expected failure classes
- shared persistence and truth-hash behavior

### 3. Cross-app dependency evidence

Capture and link proof that:

- Stage-facing backend contracts remain stable
- Match-facing workspace contracts remain stable
- Performance-facing library contracts remain stable

### 4. Documentation evidence

Link all synchronized doc updates for:

- architecture docs
- test guide docs
- app bundle docs that reference backend contract changes

## Expected artifact locations

Use repo artifact locations rather than temporary scratch paths whenever possible.

- Test run summary:
  - Expected path: `artifacts/test-run.json` or suite-specific output
  - Notes: prefer canonical runner output when used
- Route/state contract notes:
  - Expected path: repo-relative docs or artifact files
  - Notes: include exact route groups or state slices covered
- Persistence / reopen proof:
  - Expected path: `artifacts/` or documented output path
  - Notes: record the scenario exercised
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

The shared backend is not complete until every required artifact category has at least one linked proof item and those proof items agree with `outcome.md` and the three app bundles.
