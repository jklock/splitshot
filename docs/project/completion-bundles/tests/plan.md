# Test Modularization Completion Plan

## Objective

Complete the test architecture so Stage, Match, and Performance each have their own tests and their own e2e coverage, with shared-shell/backend tests isolated to truly shared behavior.

## Scope

This bundle covers test architecture only:

- browser contract, interaction, and e2e test ownership
- route/backend test ownership for app-facing contracts
- fixture isolation and deterministic test data
- test runner and suite taxonomy alignment
- QA matrix and doc-audit coupling
- CI lane expectations for app-owned and shared tests
- test docs, migration notes, and proof artifacts

## Non-goals

This bundle does not complete:

- product features beyond the test coverage required to prove them
- unrelated test refactors that do not improve app ownership or modularity
- CI redesign beyond the lane splits needed to support modular ownership

## Current-state summary

The repo already has meaningful coverage, but it is still organized more by historical browser/backend concern than by app ownership.

Current facts that matter:

- many browser tests live in flat files such as `test_browser_static_ui.py`, `test_browser_interactions.py`, `test_browser_full_app_e2e.py`, `test_browser_control.py`, `test_workspace_flows.py`, and `test_library_backend_contracts.py`
- browser doc audits and QA matrices are already coupled to browser-visible controls
- some tests already map closely to Match or Performance behavior, but the suite taxonomy does not yet enforce that ownership clearly
- the user requirement is explicit: Stage has tests, Match has tests, Performance has tests, and each has its own e2e lane without hidden reliance on the others

## Target test model

The target model is four top-level ownership lanes within browser-facing validation:

- Stage-owned tests
- Match-owned tests
- Performance-owned tests
- Shared-shell/backend tests

Each app lane should contain its own:

- static contract coverage
- backend/route contract coverage as needed
- interaction coverage
- e2e coverage

## Test work phases

## Phase 1 — Inventory current test ownership

Map what exists before moving anything:

- identify Stage-owned tests
- identify Match-owned tests
- identify Performance-owned tests
- identify truly shared-shell/backend tests
- identify mixed tests that must be split

Exit criteria:

- ownership map is recorded in `spec.md`
- current-file migration targets are listed in `artifacts.md`

## Phase 2 — Define target suite structure and fixture policy

Make the new structure explicit:

- target folder or naming layout
- allowed shared fixtures and helpers
- app-local fixtures and synthetic data expectations
- isolated artifact/output paths for app e2e runs

Exit criteria:

- suite structure and fixture rules are written down and testable

## Phase 3 — Carve app-owned lanes

Split tests by app ownership:

- Stage tests and Stage e2e
- Match tests and Match e2e
- Performance tests and Performance e2e
- minimal shared-shell/backend lane for landing/global contracts

Exit criteria:

- each app has a clear owned path to green without hidden dependence on another app suite

## Phase 4 — Align docs, runner, and CI

Close the governance loop:

- update `docs/tests/TEST_SUITE_GUIDE.md`
- update QA matrix / coverage plan references where owning tests moved
- update canonical runner or suite mapping as needed
- define CI lane expectations for app-owned versus shared tests

Exit criteria:

- docs and runner agree on the same app-owned suite taxonomy

## Phase 5 — Final proof and signoff

The test architecture is complete only when:

- app-owned suites exist
- app-owned e2e exists
- shared-shell/backend coverage is isolated
- docs and runner reflect the same structure
- migration risks are recorded and approved

## Universal acceptance criteria

The test architecture must satisfy all of the following:

- Stage, Match, and Performance each have their own owned tests
- Stage, Match, and Performance each have their own owned e2e
- shared-shell/backend tests cover only truly shared behavior
- app-owned suites can be reasoned about independently
- docs and QA audits reflect the new ownership model

## Primary risks

- flat historical tests can hide cross-app assumptions that only surface during split-up
- browser doc-audit coupling can break if test ownership moves without doc updates
- migration can create duplicate coverage or gaps unless the ownership map is explicit

## Required references

- `../../tests/TEST_SUITE_GUIDE.md`
- `../../browser-control-qa-matrix.md`
- `../../browser-control-coverage-plan.md`
- `../../browser-full-e2e-qa-plan.md`
- `../../../scripts/testing/run_test_suite.py`
- `../../../tests/browser/`

## Plan result

This tests bundle is the execution contract for turning SplitShot validation into app-owned, modular test lanes that match the three-app architecture.
