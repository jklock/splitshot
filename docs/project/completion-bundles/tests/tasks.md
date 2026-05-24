# Test Modularization Task Backlog

## Usage

- Treat each item as incomplete until its proof exists.
- Link moved tests, suite outputs, runner changes, and doc updates in `outcome.md` and `artifacts.md`.
- Test modularization is done only when ownership is explicit and runnable.

## TST-001 — Inventory current test ownership

- [ ] Classify current browser/backend tests as Stage, Match, Performance, or shared.
- [ ] Identify mixed tests that need to be split.
- [ ] Identify current app-e2e gaps.
- [ ] Record QA-matrix and doc-audit dependencies for each owned area.

Depends on:

- none

Proof:

- `spec.md` ownership inventory completed
- migration targets listed in `artifacts.md`

## TST-002 — Define target suite structure

- [ ] Define the target app-owned suite layout.
- [ ] Define where shared-shell/backend tests live.
- [ ] Define fixture-sharing rules.
- [ ] Define artifact/output path rules for app e2e.

Depends on:

- TST-001

Proof:

- `spec.md` suite structure and fixture policy completed
- docs and runner targets can reference the same structure

## TST-003 — Carve Stage-owned suites

- [ ] Identify Stage static contract tests.
- [ ] Identify Stage backend/route contract tests.
- [ ] Identify Stage interaction tests.
- [ ] Define or move Stage-owned e2e coverage.
- [ ] Remove hidden Match/Performance dependence from Stage lanes.

Depends on:

- TST-002

Proof:

- Stage-owned suite and e2e targets are explicit
- Stage app bundle can reference them directly

## TST-004 — Carve Match-owned suites

- [ ] Identify Match static contract tests.
- [ ] Identify Match workspace/backend tests.
- [ ] Identify Match interaction tests.
- [ ] Define or move Match-owned e2e coverage.
- [ ] Remove hidden Stage/Performance dependence from Match lanes.

Depends on:

- TST-002

Proof:

- Match-owned suite and e2e targets are explicit
- Match app bundle can reference them directly

## TST-005 — Carve Performance-owned suites

- [ ] Identify Performance static contract tests.
- [ ] Identify Performance library/backend tests.
- [ ] Identify Performance interaction tests.
- [ ] Define or move Performance-owned e2e coverage.
- [ ] Remove hidden Stage/Match dependence from Performance lanes.

Depends on:

- TST-002

Proof:

- Performance-owned suite and e2e targets are explicit
- Performance app bundle can reference them directly

## TST-006 — Lock shared-shell and backend suites

- [ ] Identify truly shared shell tests.
- [ ] Identify landing/global/backend tests that should stay shared.
- [ ] Remove app-owned behavior from shared suites.
- [ ] Document the rule for when a test belongs to shared versus an app lane.

Depends on:

- TST-003
- TST-004
- TST-005

Proof:

- shared suite scope is documented and minimal
- app bundles no longer rely on broad mixed suites by default

## TST-007 — Isolate fixtures and deterministic media

- [ ] Define allowed shared fixtures.
- [ ] Define app-local fixture patterns.
- [ ] Define deterministic media and artifact naming rules.
- [ ] Ensure one app’s e2e artifacts do not collide with another’s.

Depends on:

- TST-002
- TST-006

Proof:

- fixture policy written in `spec.md`
- artifact paths and helper rules recorded in `artifacts.md`

## TST-008 — Sync runner, docs, and CI

- [ ] Update `docs/tests/TEST_SUITE_GUIDE.md` for app-owned suites.
- [ ] Update QA matrix / coverage plan references where owning tests moved.
- [ ] Update canonical runner mappings or docs if suite names change.
- [ ] Define CI lane expectations for Stage, Match, Performance, and shared tests.

Depends on:

- TST-006
- TST-007

Proof:

- docs and runner agree on the same suite taxonomy
- doc diffs linked in `artifacts.md`

## TST-009 — Test modularization done gate

- [ ] Confirm Stage-owned suite and e2e exist.
- [ ] Confirm Match-owned suite and e2e exist.
- [ ] Confirm Performance-owned suite and e2e exist.
- [ ] Confirm shared-shell/backend suite scope is explicit.
- [ ] Confirm approval is recorded.

Depends on:

- TST-008

Proof:

- `outcome.md` final gate marked complete
