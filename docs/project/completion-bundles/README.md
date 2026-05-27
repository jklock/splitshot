# SplitShot Completion Bundles

This directory is the execution-grade planning set for the SplitShot completion program.

`MASTER_STATUS.md` is the authoritative cross-bundle status board for this directory.

Use `MASTER_STATUS.md` to determine what is actually done, what is only implemented but still waiting on proof packaging, what has not yet had a dedicated execution pass, and how the source bundles map into the two aggregate work efforts.

## Directory model

This directory now uses a three-directory working structure.

### Top-level working directories

- `development/` — aggregate Work Effort 1 / Set 1 for all implementation and development work across the source bundles
- `testing/` — aggregate Work Effort 2 / Set 2 for all testing, proof packaging, artifact capture, QA/doc sync, final gates, and signoff across the source bundles
- `predev/` — container for all detailed source bundles and parity-input/reference material

### `predev/` = detailed source bundles

These six source bundles remain intact inside `predev/` and remain the detailed truth for lane-local scope, tasks, specs, outcomes, and artifacts:

- `predev/stage/`
- `predev/match/`
- `predev/performance/`
- `predev/backend/`
- `predev/modularization/`
- `predev/tests/`

`predev/newfeatures/from-shooting-cut.md` remains parity-input/reference material, not completion proof.

Important distinction:

- `predev/tests/` is the source bundle for test modularization.
- `testing/` is the aggregate Work Effort 2 overlay.
- They are related, but they are **not** the same thing.

Each source or aggregate bundle uses the same file set:

- `plan.md` — scope, sequencing, boundaries, risks, and acceptance criteria
- `tasks.md` — actionable work backlog with dependencies and proof requirements
- `spec.md` — normative requirements and non-regression contract
- `outcome.md` — definition of done, status ledger, and signoff record
- `artifacts.md` — required evidence, artifact paths, and proof checklist
- `orchestration.prompt.md` — bundle-local end-to-end subagent orchestration prompt

## Authority model

- `MASTER_STATUS.md` is the only file in this directory that should summarize status across multiple source bundles or across the two aggregate work efforts.
- source-bundle `plan.md`, `tasks.md`, `spec.md`, `outcome.md`, and `artifacts.md` remain the source of detailed lane execution truth.
- aggregate-bundle `plan.md`, `tasks.md`, `spec.md`, `outcome.md`, and `artifacts.md` in `development/` and `testing/` are execution overlays for Work Effort 1 and Work Effort 2.
- `predev/newfeatures/from-shooting-cut.md` is a parity-input brief, not completion proof.

## Shared status vocabulary

Every source or aggregate bundle in this directory should use the same status model:

- `planning baseline`
  - contract, backlog, and proof requirements exist,
  - but the bundle has not yet had a dedicated execution pass.
- `implementation advanced / proof pending`
  - the bundle was materially worked,
  - but final proof packaging, screenshots, artifact recording, and/or visual approval still remain open.
- `done`
  - the bundle `outcome.md` final gate is closed,
  - required evidence is linked,
  - and approval is recorded.

## How to use these bundles

1. Read `MASTER_STATUS.md` first for the current program state, work-effort order, and source-to-aggregate mapping.
2. Decide whether the work belongs to `development/` for Work Effort 1 / Set 1 or `testing/` for Work Effort 2 / Set 2.
3. Read the relevant aggregate bundle `plan.md`, `tasks.md`, and `spec.md`.
4. Read the relevant source bundle(s) under `predev/` for the detailed task and artifact truth.
5. Treat `spec.md` as the normative contract, `tasks.md` as the actionable backlog, `outcome.md` as the status/signoff ledger, and `artifacts.md` as the proof ledger.
6. Update the touched source bundle and the touched aggregate bundle in the same change whenever real status moves.

## Bundle-local prompt note

Each lane now includes an `orchestration.prompt.md` file alongside the core planning docs.

These prompt files are stored with the bundle so the execution prompt lives next to the plan/spec/tasks it must obey.
They are bundle-local prompt assets, not workspace-discoverable slash prompts. If you want them to appear in the chat prompt picker later, mirror them into `.github/prompts/`.

The unnumbered `orchestration.prompt.md` file is the canonical prompt source for each bundle.

For the new aggregate bundles:

- `development/orchestration.prompt.md` is canonical,
- `testing/orchestration.prompt.md` is canonical,
- and no numbered duplicate prompt files are used for those aggregate bundles.

## Shared rules

- These bundles are execution documents, not aspirational notes.
- A source bundle is not done because code landed; it is done only when the owning tests, docs, artifacts, and visual proof are complete.
- `development/` must not silently absorb proof/signoff work reserved for `testing/`.
- `testing/` must not pretend to replace the source `predev/tests/` bundle.
- Browser-visible changes must keep browser contract tests, inventory audits, and QA docs in sync.
- Stage, Match, and Performance remain separate apps on a shared backend.
- Shared backend and modularization work may support those apps, but must not blur ownership back into one mixed surface.

## Current execution reality (`2026-05-26`)

- Work Effort 1 / `development/` is now complete: DEV-301 closed with the added DEV-106/DEV-107 interaction and compat-consumer proof, seam-registry-backed audits, runtime health, and a fresh all-together suite anchor.
- Backend and Modularization implementation scope no longer block Work Effort 1; their source bundles remain `implementation advanced / proof pending` only because final proof/signoff work is reserved for `testing/`.
- Work Effort 2 / `testing/` already contains Stage docs/test/proof sync and focused proof baselines for Match and Performance, but the remaining Performance proof package, Backend/Modularization signoff, the source `predev/tests/` bundle modularization work, and the final gates are still open.
- The source `predev/tests/` bundle remains `planning baseline` even though the repo-wide suite has a passing baseline.
- Canonical repo-wide proof anchor: `../../../artifacts/all-together.json` records `691 passed` on `2026-05-26`, but that repo-health baseline does not by itself close Work Effort 2.

## Related repo docs

- `../ARCHITECTURE.md`
- `../browser-control-coverage-plan.md`
- `../browser-control-qa-matrix.md`
- `../browser-full-e2e-qa-plan.md`
- `../../tests/TEST_SUITE_GUIDE.md`
- `../../automatecomplete/product-foundation/00-product-definition.md`
- `../../remediation/01-design-contract.md`

## Bundle index

### Aggregate directories

- `development/` — Work Effort 1 / Set 1 implementation overlay
- `testing/` — Work Effort 2 / Set 2 testing/signoff overlay

### Source-bundle container

- `predev/` — detailed source bundles plus parity-input/reference material
  - `predev/stage/` — Stage-only completion and proof source lane
  - `predev/match/` — Match-only completion and proof source lane
  - `predev/performance/` — Performance-only completion and proof source lane
  - `predev/backend/` — shared backend completion and contract hardening source lane
  - `predev/modularization/` — browser shell and ownership isolation source lane
  - `predev/tests/` — source lane for test modularization, suite ownership, and CI/test-governance work
  - `predev/newfeatures/` — parity-input/reference material
