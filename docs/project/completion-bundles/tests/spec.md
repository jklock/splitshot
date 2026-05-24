# Test Modularization Specification

## Normative statement

SplitShot validation must reflect the three-app architecture. Stage, Match, and Performance each require owned tests and owned e2e coverage, while shared-shell/backend tests must be limited to truly shared behavior.

## Target suite structure requirements

The target browser-facing ownership model must separate tests into at least these lanes:

- Stage-owned tests
- Match-owned tests
- Performance-owned tests
- Shared-shell/backend tests

The final folder or naming layout may vary, but the ownership model must be explicit and documented.

## App-owned suite requirements

Each app lane must own its own:

- static UI contract coverage
- backend/route contract coverage where applicable
- interaction coverage
- e2e coverage

An app lane must not depend on another app lane’s tests to prove its own user-facing completeness.

## Shared-suite requirements

Shared-shell/backend suites may cover only:

- landing page and shared navigation
- global settings/config behavior
- shared backend route/state/persistence behavior
- test-doc audits that are genuinely shared

App-specific feature tests must not remain in shared suites just because that was historically convenient.

## Fixture and helper requirements

- Shared fixtures may be used only for genuinely common infrastructure.
- App-specific helpers should live with or clearly belong to the owning app lane.
- Deterministic media generation and artifact naming rules must prevent cross-app collisions.
- One app’s e2e run must not rely on another app’s leftover artifacts or state.

## Documentation and audit requirements

Any test ownership change that affects browser-visible controls or documentation references requires synchronized updates to:

- `docs/tests/TEST_SUITE_GUIDE.md`
- `docs/project/browser-control-qa-matrix.md`
- `docs/project/browser-control-coverage-plan.md`
- `docs/project/browser-full-e2e-qa-plan.md`
- any app bundle docs that cite the moved tests

## Runner and CI requirements

- The canonical runner and its docs must describe the same app-owned suite structure.
- CI lane expectations must distinguish Stage, Match, Performance, and shared tests.
- App-owned suites should be runnable independently for focused validation.

## Migration requirements

- Historical flat tests must be classified before they are moved or split.
- Mixed tests must be split when they obscure ownership.
- Temporary mixed tests must be explicitly documented with a removal plan.

## Definition of specification success

The test modularization spec is satisfied only when suites, fixtures, runner docs, CI expectations, and app bundles all describe the same ownership model for Stage, Match, Performance, and shared coverage.
