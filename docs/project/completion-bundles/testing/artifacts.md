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
  - Date: `2026-05-26`
  - Notes: Work Effort 2 inherits the closed Stage source bundle, including `STG-007`, the closed `STG-008` final gate, and the refreshed `2026-05-26` rerun evidence.

- Artifact: Stage final-gate rerun evidence
  - Path: `../predev/stage/outcome.md`, `../predev/stage/artifacts.md`, `../../../docs/screenshots/ProjectPane.png`, `../../../docs/screenshots/ExportPane.png`, `../../../docs/screenshots/ReviewPane.png`, `../../../docs/screenshots/automate3/responsive-stage-1280.png`, `../../../docs/screenshots/automate3/responsive-stage-900.png`, `../../../docs/screenshots/automate3/responsive-proof-results.json`
  - Produced by: 2026-05-26 Stage rerun pass
  - Date: `2026-05-26`
  - Notes: records the full Stage rerun after the Compose/Overlay/Export workflow relocation: runtime health passed, the Stage proof packs stayed green at `49`, `47`, `37`, and `59` passing tests, the repo-owned screenshots were refreshed, and the responsive proof bundle stayed green with no console errors.

- Artifact: Match proof anchor
  - Path: `../predev/match/outcome.md`, `../predev/match/artifacts.md`
  - Produced by: Match source bundle
  - Date: `2026-05-26`
  - Notes: Work Effort 2 inherits the closed Match source bundle, including the current rerun evidence and the recorded Match proof bundle.

- Artifact: Match final-gate rerun evidence
  - Path: `../predev/match/outcome.md`, `../predev/match/artifacts.md`, `../../../artifacts/match-proof-20260526/summary.txt`, `../../../artifacts/match-proof-20260526/proof-results.json`, `../../../artifacts/match-proof-20260526/screenshots/match-empty.png`, `../../../artifacts/match-proof-20260526/screenshots/match-loaded.png`, `../../../artifacts/match-proof-20260526/screenshots/match-recap.png`, `../../../artifacts/match-proof-20260526/screenshots/match-composite.png`, `../../../artifacts/match-proof-20260526/screenshots/match-export.png`, `../../../artifacts/match-proof-20260526/screenshots/match-settings.png`, `../../../artifacts/match-proof-20260526/workspace/recap.mp4`, `../../../artifacts/match-proof-20260526/workspace/exports/stage_1-stage_composite.mp4`, `../../../artifacts/match-proof-20260526/workspace/exports/stage_2-stage_composite.mp4`, `../../../artifacts/match-proof-20260526/workspace/auto-seed-proof.json`, `../../../artifacts/match-proof-20260526/workspace/composite-plan.json`, `../../../artifacts/match-proof-20260526/workspace/composite-plan-detail.txt`
  - Produced by: 2026-05-26 Match rerun pass
  - Date: `2026-05-26`
  - Notes: records the full Match rerun after Stage closure: the shared shell/static/inventory/coverage pack stayed green at `49 passed`; the lifecycle/lower-pane packs stayed green at `3 passed`, `2 passed`, and `4 passed`; the recap/batch/composite packs stayed green at `2 passed`, `2 passed`, and `4 passed`; the Match settings isolation rerun stayed green at `2 passed`; and the fresh Match proof bundle recorded the accepted screenshots plus recap/export/composite/auto-seed artifacts.

- Artifact: Performance proof anchor
  - Path: `../predev/performance/outcome.md`, `../predev/performance/artifacts.md`
  - Produced by: Performance source bundle
  - Date: `2026-05-26`
  - Notes: Work Effort 2 now inherits the closed Performance source bundle, including the focused reruns, screenshot package, output artifacts, and recorded visual approval.

- Artifact: Performance final-gate rerun evidence
  - Path: `../predev/performance/outcome.md`, `../predev/performance/artifacts.md`, `../../../docs/screenshots/automate3/loaded-library.png`, `../../../docs/screenshots/automate3/loaded-proof-results.json`, `../../../docs/screenshots/automate3/performance-analytics.png`, `../../../docs/screenshots/automate3/performance-backup.png`, `../../../docs/screenshots/automate3/performance-settings.png`, `../../../docs/screenshots/automate3/performance-section-proof-results.json`, `../../../artifacts/performance-proof-20260526/library-export.csv`, `../../../artifacts/performance-proof-20260526/library-export.json`, `../../../artifacts/performance-proof-20260526/backup-manifest.json`, `../../../artifacts/performance-proof-20260526/backup-create-result.json`, `../../../artifacts/performance-proof-20260526/backup-restore-result.json`, `../../../artifacts/performance-proof-20260526/backup_2026-05-26_22-13-50.json`, `../../../artifacts/performance-proof-20260526/performance-output-proof-results.json`
  - Produced by: 2026-05-26 Performance proof-close pass
  - Date: `2026-05-26`
  - Notes: records the full Performance closeout: focused interaction reruns at `3 passed` and `4 passed`, the backend/export pack at `72 passed`, the loaded and section-specific screenshot set, repo-owned output artifacts for CSV/JSON export plus backup create/restore, and visual approval against the refreshed captures.

- Artifact: Backend proof/signoff anchor
  - Path: `../predev/backend/tasks.md`, `../predev/backend/outcome.md`, `../predev/backend/artifacts.md`
  - Produced by: Backend source bundle
  - Date: `2026-05-26`
  - Notes: Work Effort 2 now inherits the closed backend source bundle, including the focused reruns, runtime health, owner-suite anchors, accepted residual risks, and approval.

- Artifact: Backend preflight proof rerun
  - Path: `../predev/backend/outcome.md`, `../predev/backend/artifacts.md`, `../../../artifacts/test-suite-backend-signoff.json`
  - Produced by: 2026-05-26 backend preflight validation
  - Date: `2026-05-26`
  - Notes: the focused backend proof packs reran green at `114 passed`, `38 passed`, `22 passed`, and `22 passed`, and the persistence+analysis owner-suite artifact recorded `125 passed`; this remains the focused backend closeout anchor inside the final proof package.

- Artifact: Backend final-gate rerun evidence
  - Path: `../predev/backend/outcome.md`, `../predev/backend/artifacts.md`, `../../../artifacts/test-suite-backend-signoff.json`, `../../../artifacts/test-suite-backend-browser.json`
  - Produced by: 2026-05-26 backend closeout pass
  - Date: `2026-05-26`
  - Notes: records the closed backend gate: focused reruns at `114 passed`, `38 passed`, `22 passed`, and `22 passed`, runtime health, the persistence+analysis owner-suite anchor at `125 passed`, the browser owner-suite anchor at `420 passed`, the accepted residual-risk record, and the synchronized source/aggregate/top-level ledgers.

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

Testing is not complete until `VAL-006` is closed, the relevant source-bundle final gates are closed, the source `predev/tests/` bundle is complete, and the final closeout chain is fully recorded.
