# Modularization Artifact Plan

## Purpose

This file tracks the proof package required to call browser modularization complete.

## Required evidence categories

### 1. Source-level evidence

Capture and link proof for:

- current-to-target ownership inventory
- module interface boundaries
- reduced root orchestration scope
- documented cross-app dependencies that remain

### 2. Test evidence

Record exact test outputs for modularization coverage:

- source-level ownership or contract tests
- app-owned interaction/e2e tests affected by wiring changes
- any doc-audit tests affected by ownership changes

### 3. App-isolation evidence

Capture and link proof that:

- Stage settings and local state remain Stage-local
- Match settings and local state remain Match-local
- Performance settings and local state remain Performance-local
- shared shell state is limited to shared concerns

### 4. Documentation evidence

Link all synchronized doc updates for:

- architecture docs
- app bundle docs that describe ownership boundaries
- any test-guide references affected by modularization

## Expected artifact locations

Use repo artifact locations rather than temporary scratch paths whenever possible.

- Test run summary:
  - Expected path: `artifacts/test-run.json` or suite-specific output
  - Notes: prefer canonical runner output when used
- Ownership notes:
  - Expected path: repo-relative docs or artifact files
  - Notes: include module names and boundary decisions
- Wiring / app-isolation proof:
  - Expected path: `artifacts/` or documented proof path
  - Notes: record the specific scenario exercised
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

Modularization is not complete until every required artifact category has at least one linked proof item and those proof items agree with `outcome.md` and the app bundles.
