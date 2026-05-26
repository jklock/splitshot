# Development Completion Plan

## Objective

Complete Work Effort 1 / Set 1 as the implementation-only overlay across the SplitShot completion program.

This bundle aggregates all development work across the existing source bundles stored under `../predev/` so the program can hand off into one final testing and signoff effort instead of continuing as six loosely synchronized threads.

## Current execution status

- Bundle: `development`
- Work effort: `Work Effort 1 / Set 1`
- Status: `implementation advanced / proof pending`
- Cross-bundle authority: `../MASTER_STATUS.md`

## Scope

This bundle aggregates implementation-only work from the source bundles stored under `../predev/`:

- Stage development scope: `STG-001` through `STG-006`
- Match development scope: `MCH-001` plus the implementation side of `MCH-002` through `MCH-006`
- Performance development scope: `PRF-001` plus the implementation side of `PRF-002` through `PRF-005`
- Backend development scope: `BEK-001` through `BEK-006`
- Modularization development scope: `MOD-001` through `MOD-005`
- implementation-facing contract, spec, and behavior docs required to keep the delivered behavior truthful while development lands

## Non-goals

This bundle does not close:

- Stage testing/signoff scope in `STG-007` and `STG-008`
- Match proof packaging, screenshots, artifact capture, or `MCH-007`
- Performance proof packaging, screenshots, artifact capture, or `PRF-006` / `PRF-007`
- Backend proof/signoff scope in `BEK-007` and `BEK-008`
- Modularization proof/signoff scope in `MOD-006` and `MOD-007`
- any `TST-*` work from the source `predev/tests/` bundle
- screenshot packages, QA matrix closeout, final artifact ledgers, final suite closure, or visual approval

## Current-state summary

Current facts that matter:

- Stage implementation baseline is already materially settled through `STG-006`.
- Match implementation baseline is materially advanced through `MCH-006` and now has a clean Work Effort 1 handoff with no open implementation reopen recorded.
- Performance implementation baseline is materially advanced through `PRF-005` and now has a clean Work Effort 1 handoff with no open implementation reopen recorded.
- Backend has now had its dedicated implementation pass; `BEK-001` through `BEK-006` are recorded as Work Effort 1 implementation-complete while proof/signoff stays in Work Effort 2.
- Modularization has now had its dedicated implementation pass; `MOD-001` through `MOD-005` are recorded as Work Effort 1 implementation-complete while proof/signoff stays in Work Effort 2.
- The source `predev/tests/` bundle remains outside Work Effort 1 and must not be confused with the aggregate `testing/` bundle.

## Source-bundle mapping

### Stage source scope

Work Effort 1 owns the implementation side of the Stage source bundle:

- `STG-001` — contract reset
- `STG-002` — Project cleanup and redistribution
- `STG-003` — shared shell hardening
- `STG-004` — import/home/output defaults
- `STG-005` — workflow regressions
- `STG-006` — Stage-owned parity closure

### Match source scope

Work Effort 1 owns the implementation side of the Match source bundle:

- `MCH-001`
- implementation closure from `MCH-002`
- implementation closure from `MCH-003`
- implementation closure from `MCH-004`
- `MCH-005`
- implementation-facing portions of `MCH-006`

### Performance source scope

Work Effort 1 owns the implementation side of the Performance source bundle:

- `PRF-001`
- implementation closure from `PRF-002`
- implementation closure from `PRF-003`
- implementation closure from `PRF-004`
- `PRF-005`

### Backend source scope

Work Effort 1 owns the implementation side of the Backend source bundle:

- `BEK-001` through `BEK-006`

### Modularization source scope

Work Effort 1 owns the implementation side of the Modularization source bundle:

- `MOD-001` through `MOD-005`

## Architecture boundaries

### `development/` owns

- implementation changes
- route/state and controller contract hardening
- shell and app behavior changes
- refactors required to make ownership boundaries real
- development-facing spec and behavior-doc updates required to keep the code truthful
- the handoff package into `testing/`

### `testing/` owns

- proof packaging
- screenshots
- artifact capture
- QA matrix and coverage-plan closeout
- final source-bundle gates
- final suite closure and visual approval

### Source bundles own

- detailed task truth
- detailed lane-local specs
- detailed lane-local outcomes and artifacts
- the source of truth for exact task IDs and detailed proof obligations

### Source `predev/tests/` bundle owns

- the detailed `TST-*` test modularization contract
- the executable test-ownership carve-out work that must run inside Work Effort 2

## Development work phases

## Phase 1 — Lock the Work Effort 1 contract

- record the development/testing split explicitly
- map the source bundles into Work Effort 1
- record that source `predev/tests/` and aggregate `testing/` are not the same thing

Exit criteria:

- `development/plan.md`, `development/spec.md`, `development/tasks.md`, `development/outcome.md`, and `development/artifacts.md` all describe the same Work Effort 1 boundary

## Phase 2 — Preserve settled Stage, Match, and Performance implementation baselines

- carry forward the settled Stage implementation baseline from `STG-001` through `STG-006`
- keep Match implementation scope aligned with `MCH-001` through the implementation side of `MCH-006`
- keep Performance implementation scope aligned with `PRF-001` through the implementation side of `PRF-005`
- document any newly discovered implementation blockers that must be resolved before testing owns the remaining work

Exit criteria:

- only testing-side proof/signoff work remains open for Stage, Match, and Performance

## Phase 3 — Execute the dedicated Backend implementation pass

- complete `BEK-001` through `BEK-006`
- make route/state ownership explicit
- keep `/api/state` summary-oriented
- make persistence, import, and cross-app backend behavior implementation-complete before testing claims proof

Exit criteria:

- Backend implementation truth is explicit enough that `BEK-007` and `BEK-008` can be closed in Work Effort 2 without reopening development scope

## Phase 4 — Execute the dedicated Modularization implementation pass

- complete `MOD-001` through `MOD-005`
- make shell versus app ownership explicit
- shrink root orchestration responsibility where required
- isolate app-local settings and persistence behavior

Exit criteria:

- modularization structure is explicit enough that Work Effort 2 can prove it without still discovering first-order architecture work

## Phase 5 — Publish the development handoff to `testing/`

- list what implementation is complete
- list what testing-side work remains by source bundle
- record residual risks and implementation deferrals
- confirm that no testing-only work is being claimed complete in `development/`

Exit criteria:

- Work Effort 2 can proceed without re-litigating the intended development boundary

## Universal acceptance criteria

The development bundle is satisfied only when all of the following are true:

- all mapped implementation work is complete or explicitly deferred
- the source bundles and aggregate bundle describe the same implementation truth
- only proof, artifact, QA/doc sync, suite closure, and signoff work remain for `testing/`
- `development/` does not silently claim completion of screenshot, artifact, or visual approval work
- source `predev/tests/` work remains reserved for Work Effort 2

## Primary risks

- Match and Performance can look implementation-complete while lifecycle or lower-pane grammar blockers still remain hidden.
- Backend and Modularization now have dedicated implementation passes, but route/ownership proof depth and residual-risk closeout still remain visible Work Effort 2 concerns.
- The source `predev/tests/` bundle can be confused with aggregate `testing/` unless the distinction is reinforced in every handoff.
- Documentation work can blur between implementation truth and proof packaging unless the boundary is enforced.

## Required references

- `../MASTER_STATUS.md`
- `../predev/stage/tasks.md`
- `../predev/match/tasks.md`
- `../predev/performance/tasks.md`
- `../predev/backend/tasks.md`
- `../predev/modularization/tasks.md`
- `../predev/tests/tasks.md`
- `../RECOVERY_NEXT_STEPS.md`

## Plan result

This development bundle is the execution contract for Work Effort 1 / Set 1: finish all implementation work across the completion-bundles directory, then hand the program to Work Effort 2 for testing, proof packaging, and signoff.
