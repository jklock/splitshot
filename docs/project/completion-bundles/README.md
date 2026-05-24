# SplitShot Completion Bundles

This directory is the execution-grade planning set for the SplitShot completion program.

These bundles break the larger completion effort into six owned lanes:

- `stage/`
- `match/`
- `performance/`
- `backend/`
- `modularization/`
- `tests/`

Each lane uses the same file set:

- `plan.md` — scope, sequencing, boundaries, risks, and acceptance criteria
- `tasks.md` — actionable work backlog with dependencies and proof requirements
- `spec.md` — normative requirements and non-regression contract
- `outcome.md` — definition of done, status ledger, and signoff record
- `artifacts.md` — required evidence, artifact paths, and proof checklist
- `orchestration.prompt.md` — bundle-local end-to-end subagent orchestration prompt

## How to use these bundles

1. Read the lane `plan.md` first.
2. Use `tasks.md` as the execution backlog for that lane.
3. Treat `spec.md` as the normative implementation contract.
4. Record lane status, waivers, and signoff in `outcome.md`.
5. Store proof references and expected artifact paths in `artifacts.md`.
6. Use `orchestration.prompt.md` when you want a copy-pasteable multi-agent execution prompt for that lane.

## Bundle-local prompt note

Each lane now includes an `orchestration.prompt.md` file alongside the core planning docs.

These prompt files are stored with the bundle so the execution prompt lives next to the plan/spec/tasks it must obey.
They are bundle-local prompt assets, not workspace-discoverable slash prompts. If you want them to appear in the chat prompt picker later, mirror them into `.github/prompts/`.

## Shared rules

- These bundles are execution documents, not aspirational notes.
- A lane is not done because code landed; it is done only when the owning tests, docs, artifacts, and visual proof are complete.
- Browser-visible changes must keep browser contract tests, inventory audits, and QA docs in sync.
- Stage, Match, and Performance remain separate apps on a shared backend.
- Shared backend and modularization work may support those apps, but must not blur ownership back into one mixed surface.

## Related repo docs

- `../ARCHITECTURE.md`
- `../browser-control-coverage-plan.md`
- `../browser-control-qa-matrix.md`
- `../browser-full-e2e-qa-plan.md`
- `../../tests/TEST_SUITE_GUIDE.md`
- `../../automatecomplete/product-foundation/00-product-definition.md`
- `../../remediation/01-design-contract.md`

## Bundle index

- `stage/` — Stage-only completion and proof
- `match/` — Match-only completion and proof
- `performance/` — Performance Library completion and proof
- `backend/` — shared backend completion and contract hardening
- `modularization/` — browser shell and ownership isolation plan
- `tests/` — modular test architecture, CI lanes, and proof governance
