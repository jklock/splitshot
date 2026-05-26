# Testing Artifact Plan

## Purpose

This file tracks the testing, proof, artifact, QA/doc-sync, and signoff evidence required to call Work Effort 2 / Set 2 complete.

Current normalized bundle status: `implementation advanced / proof pending`

Cross-bundle summary authority: `../MASTER_STATUS.md`

Acceptance evidence for `testing/` must prove source-bundle completion and final program closeout. The aggregate `testing/` bundle is not complete until the relevant source bundles can close with it.

## Required evidence categories

### 1. Source-bundle proof mapping

Capture and link proof for:

- the exact source-to-aggregate mapping for Work Effort 2
- the distinction between source `predev/tests/` and aggregate `testing/`
- which existing source-bundle evidence is acceptance-valid versus historical-only

### 2. Focused test evidence

Capture and link proof for:

- Stage final-gate validation
- Match lifecycle, shell grammar, recap/composite/export, and final-gate validation
- Performance shell/detail/search-filter/backup-export and final-gate validation
- Backend route/state/persistence validation
- Modularization ownership/isolation validation
- source `predev/tests/` bundle validation and suite-ownership proof

### 3. Visual and output evidence

Capture and link proof for:

- Stage, Match, and Performance screenshots where required
- recap/export/backup/output artifacts where required
- any DOM/layout evidence needed to support the browser-visible final gates

### 4. Documentation and governance evidence

Link synchronized doc updates for:

- source `outcome.md` and `artifacts.md` ledgers
- `docs/project/browser-control-qa-matrix.md`
- `docs/project/browser-control-coverage-plan.md`
- `docs/project/browser-full-e2e-qa-plan.md`
- `docs/tests/TEST_SUITE_GUIDE.md`
- `../MASTER_STATUS.md`, `../README.md`, and `../RECOVERY_NEXT_STEPS.md` when aggregate status meaning changes

### 5. Final closeout evidence

Capture and link proof for:

- focused proof runs
- owned suite runs
- the canonical repo-wide full-suite anchor
- visual approvals
- residual risks and approved waivers

## Expected artifact locations

Use source-bundle ledgers and repo-owned artifact paths rather than temporary scratch paths whenever possible.

- Source proof anchors:
  - Expected path: source `outcome.md` and `artifacts.md` files under `../predev/`
  - Notes: prefer the source bundle that owns the detailed proof truth
- Repo-wide baseline anchor:
  - Expected path: `../../../artifacts/current-all-together.json`
  - Notes: baseline health evidence only unless the source bundle final gates say more
- Screenshots and outputs:
  - Expected path: repo-owned screenshot or artifact paths referenced by the source bundle
  - Notes: keep browser-visible acceptance evidence linked from the owning source ledger
- Final closeout notes:
  - Expected path: `testing/outcome.md`, `testing/artifacts.md`, and touched source ledgers
  - Notes: the aggregate bundle must point to the same truth as the source bundles

## Artifact ledger

- Artifact: Work Effort 2 split contract
  - Path: `plan.md`, `spec.md`, `tasks.md`, `outcome.md`, `artifacts.md`, `orchestration.prompt.md`, `../MASTER_STATUS.md`, `../README.md`, `../RECOVERY_NEXT_STEPS.md`
  - Produced by: 2026-05-25 two-effort restructure pass
  - Date: `2026-05-25`
  - Notes: records the exact Set 2 testing/signoff boundary and the distinction between source `predev/tests/` and aggregate `testing/`.

- Artifact: Stage proof anchor
  - Path: `../predev/stage/outcome.md`, `../predev/stage/artifacts.md`
  - Produced by: Stage source bundle
  - Date: `2026-05-25`
  - Notes: Work Effort 2 inherits `STG-007` plus the open `STG-008` final-gate scope.

- Artifact: Match proof anchor
  - Path: `../predev/match/outcome.md`, `../predev/match/artifacts.md`
  - Produced by: Match source bundle
  - Date: `2026-05-25`
  - Notes: Work Effort 2 inherits the remaining proof/signoff work needed to close Match.

- Artifact: Performance proof anchor
  - Path: `../predev/performance/outcome.md`, `../predev/performance/artifacts.md`
  - Produced by: Performance source bundle
  - Date: `2026-05-25`
  - Notes: Work Effort 2 inherits the remaining proof/signoff work needed to close Performance.

- Artifact: Backend proof/signoff anchor
  - Path: `../predev/backend/tasks.md`, `../predev/backend/outcome.md`, `../predev/backend/artifacts.md`
  - Produced by: Backend source bundle
  - Date: `2026-05-25`
  - Notes: `BEK-007` and `BEK-008` remain fully inside Work Effort 2.

- Artifact: Modularization proof/signoff anchor
  - Path: `../predev/modularization/tasks.md`, `../predev/modularization/outcome.md`, `../predev/modularization/artifacts.md`
  - Produced by: Modularization source bundle
  - Date: `2026-05-25`
  - Notes: `MOD-006` and `MOD-007` remain fully inside Work Effort 2.

- Artifact: Source `predev/tests/` bundle anchor
  - Path: `../predev/tests/tasks.md`, `../predev/tests/spec.md`, `../predev/tests/outcome.md`, `../predev/tests/artifacts.md`
  - Produced by: Tests source bundle
  - Date: `2026-05-25`
  - Notes: all `TST-*` work executes in Work Effort 2, but the source `predev/tests/` bundle remains the detailed truth for that lane.

- Artifact: Canonical repo-health anchor
  - Path: `../../../artifacts/current-all-together.json`
  - Produced by: canonical runner baseline
  - Date: `2026-05-24`
  - Notes: useful baseline health evidence, but not enough by itself to close the aggregate `testing/` bundle.

## Completion rule

Testing is not complete until `VAL-007` is closed, the relevant source-bundle final gates are closed, the source `predev/tests/` bundle is complete, and the final closeout chain is fully recorded.
