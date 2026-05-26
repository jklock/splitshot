# Testing Completion Plan

## Objective

Complete Work Effort 2 / Set 2 as the testing, proof-packaging, artifact, QA/doc-sync, and signoff overlay across the SplitShot completion program.

This bundle aggregates the testing and closeout work across the source bundles stored under `../predev/` so the program can finish in one final validation effort after Work Effort 1 hands off implementation.

## Current execution status

- Bundle: `testing`
- Work effort: `Work Effort 2 / Set 2`
- Status: `implementation advanced / proof pending`
- Cross-bundle authority: `../MASTER_STATUS.md`

## Scope

This bundle aggregates testing, proof, and signoff work from the source bundles:

- Stage testing/signoff scope: `STG-007` and `STG-008`
- Match testing/signoff scope: proof and closeout tied to `MCH-002`, `MCH-003`, `MCH-004`, `MCH-006`, and all of `MCH-007`
- Performance testing/signoff scope: proof and closeout tied to `PRF-002`, `PRF-003`, `PRF-004`, `PRF-006`, and all of `PRF-007`
- Backend testing/signoff scope: `BEK-007` and `BEK-008`
- Modularization testing/signoff scope: `MOD-006` and `MOD-007`
- all source `predev/tests/` bundle work: `TST-001` through `TST-009`
- screenshots, artifact capture, QA matrix sync, coverage-plan sync, test-guide sync, owned suite runs, full-suite closeout, and visual approval

## Non-goals

This bundle does not own:

- new feature development outside testability/truthfulness fixes that must be explicitly reopened
- broad implementation or architecture redesign that belongs in `development/`
- done credit based only on historical artifacts or broad green runs without source-bundle proof packaging
- any attempt to replace the source `predev/tests/` bundle with aggregate `testing/`

## Current-state summary

Current facts that matter:

- Stage already carries a recorded docs/test/proof sync baseline through `STG-007`, but `STG-008` remains open.
- Match and Performance both have meaningful focused proof anchors, but their remaining proof-packaging, screenshots, artifacts, and final gates are still open.
- Backend and Modularization still need their dedicated proof/signoff passes after Work Effort 1 settles implementation.
- The source `predev/tests/` bundle remains a planning baseline and must be executed in this work effort.
- `../../../artifacts/current-all-together.json` is a valuable repo-health anchor, but it does not close the open source-bundle gates by itself.
- The source `predev/tests/` bundle is not the same thing as aggregate `testing/`; it is one source lane inside this larger work effort.

## Source-bundle mapping

### Stage source scope

Work Effort 2 owns:

- `STG-007` — Stage docs/tests/proof sync
- `STG-008` — Stage done gate

### Match source scope

Work Effort 2 owns:

- proof/signoff closure tied to `MCH-002`
- proof/signoff closure tied to `MCH-003`
- proof/signoff closure tied to `MCH-004`
- proof/signoff closure tied to `MCH-006`
- all of `MCH-007`
- recap/composite/export artifact packaging required to close the Match final gate

### Performance source scope

Work Effort 2 owns:

- proof/signoff closure tied to `PRF-002`
- proof/signoff closure tied to `PRF-003`
- proof/signoff closure tied to `PRF-004`
- all of `PRF-006`
- all of `PRF-007`
- screenshots and artifact packaging required to close the Performance final gate

### Backend source scope

Work Effort 2 owns:

- `BEK-007`
- `BEK-008`

### Modularization source scope

Work Effort 2 owns:

- `MOD-006`
- `MOD-007`

### Source `predev/tests/` bundle scope

Work Effort 2 owns the entire source `predev/tests/` bundle:

- `TST-001` through `TST-009`

## Architecture boundaries

### `testing/` owns

- proof packaging
- screenshots
- artifact capture
- QA matrix, coverage-plan, and test-guide closeout
- source-bundle final gates
- final suite closure and visual approval
- aggregate closeout reporting across the source bundles

### `development/` owns

- implementation changes
- route/state/controller refactors
- shell and app behavior changes
- architecture work that must be complete before testing can claim signoff

### Source bundles own

- detailed lane-local tasks, specs, outcomes, and artifacts
- the detailed truth for what each task ID actually means

### Source `predev/tests/` bundle owns

- the detailed `TST-*` modularization truth that Work Effort 2 must execute
- the detailed suite ownership and fixture/runner/CI carve-out contract

## Testing work phases

## Phase 1 — Lock the Work Effort 2 contract and evidence map

- record the testing-only boundary explicitly
- map all source-bundle proof/signoff work into Work Effort 2
- record the distinction between source `predev/tests/` and aggregate `testing/`
- classify current evidence as acceptance-valid, partial, or historical-only

Exit criteria:

- `testing/plan.md`, `testing/spec.md`, `testing/tasks.md`, `testing/outcome.md`, and `testing/artifacts.md` all describe the same Work Effort 2 boundary

## Phase 2 — Close Stage, Match, and Performance proof packages

Preserve this order unless a blocker requires a documented change:

- close the remaining Match lifecycle and shell-convergence proof package
- close the Stage testing/signoff gate
- close the remaining Match recap/composite/export artifact package
- close the remaining Performance shell/detail/backup/export proof package

Exit criteria:

- Stage, Match, and Performance source bundles can close their remaining final-gate items without reopening first-order implementation scope

## Phase 3 — Close Backend and Modularization proof/signoff scope

- execute `BEK-007` and `BEK-008`
- execute `MOD-006` and `MOD-007`
- capture route/state/ownership evidence and record residual risks

Exit criteria:

- Backend and Modularization can both close their source final gates on documented proof rather than implied confidence

## Phase 4 — Execute the source `predev/tests/` bundle

- execute `TST-001` through `TST-009`
- make Stage, Match, Performance, and shared tests explicitly own their coverage
- sync runner, docs, fixtures, artifacts, and CI expectations

Exit criteria:

- the source `predev/tests/` bundle can close on explicit suite ownership and no longer relies on historical mixed-lane assumptions

## Phase 5 — Close the program

- refresh bundle ledgers, QA docs, coverage docs, and user-facing docs where required
- run focused proof slices, owned suites, and the canonical full suite
- record visual approval, waivers, and final residual risks
- close the aggregate `testing/` bundle only when the source bundles are genuinely closed

Exit criteria:

- Work Effort 2 can close without any source final gate remaining open

## Universal acceptance criteria

The testing bundle is satisfied only when all of the following are true:

- every mapped source-bundle proof/signoff task is complete or explicitly deferred with approval
- no source bundle is marked `done` without its own `outcome.md` final gate being closed
- screenshots, artifacts, and QA/doc sync exist where the source bundle requires them
- the source `predev/tests/` bundle is complete and no longer a planning baseline
- focused tests, owned suites, and the canonical full-suite anchor are all recorded
- visual approval and residual risks are recorded where required

## Primary risks

- broad green runs can create false confidence if source-bundle proof packaging stays incomplete
- `predev/tests/` and `testing/` can be confused unless the distinction is enforced in every closeout doc
- historical artifacts can be mistaken for current acceptance evidence
- Work Effort 2 can silently absorb reopened implementation blockers unless those blockers are pushed back into the relevant source bundle and `development/`

## Required references

- `../MASTER_STATUS.md`
- `../RECOVERY_NEXT_STEPS.md`
- `../predev/stage/outcome.md`
- `../predev/match/outcome.md`
- `../predev/performance/outcome.md`
- `../predev/backend/outcome.md`
- `../predev/modularization/outcome.md`
- `../predev/tests/outcome.md`
- `../../../artifacts/current-all-together.json`

## Plan result

This testing bundle is the execution contract for Work Effort 2 / Set 2: finish all testing, proof packaging, artifact capture, QA/doc sync, and signoff work across the completion-bundles directory.
