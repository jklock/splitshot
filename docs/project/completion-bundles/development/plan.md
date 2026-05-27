# Development Execution Plan

## Objective

Finish the Landing Zone, shared backend, and modularization foundation in a way that lets future builder agents work in parallel **without** changing frozen Stage and Match behavior.

This bundle exists to tell builders exactly what to do, in what order, on which files, with what proof obligations and guardrails.

## Current snapshot

- Stage is a **frozen baseline**. Treat the current Stage outcome as the behavior to preserve, not to redesign.
- Match is a **frozen baseline**. Treat the current Match outcome as the behavior to preserve, not to redesign.
- Performance Library remains a real app surface, but this bundle does **not** take on new Performance product scope.
- Landing is still partially browser-local and must become backend-driven.
- Shared ownership is still too broad in `app.js`, `server.py`, and `controller.py`.
- The development document set itself has now been reset to an execution-ready form with `progress.md` and `proof.md` added.

## Operating principles

1. **Freeze behavior first.** Stage and Match are protected baselines.
2. **Separate ownership before polishing behavior.** The target is modular seams, not UI churn.
3. **Use zero-overlap lanes.** If two tasks need the same file, serialize them.
4. **Integrators merge shared docs.** Workers do not touch `progress.md`, `proof.md`, or `outcome.md`.
5. **Prove meaningful work through persisted truth or output.** A visible control alone is not enough.

## Execution order

### Milestone 0 — Freeze contract lock

Task:

- `DEV-001`

Purpose:

- lock the frozen baselines
- confirm the document set is the execution source of truth
- release the first parallel wave only after the rules are unambiguous

Exit criteria:

- Stage and Match freeze rules are active
- the progress ledger is live
- the first parallel wave can start without scope guessing

### Milestone 1 — Shared contract decomposition (parallel worker wave + integrator lane)

Tasks:

- `DEV-101` — API runtime boundary
- `DEV-102` — server route dispatch modularization
- `DEV-103` — `/api/state` summary contract split
- `DEV-104` — persistence support helpers (**integrator only**, may run in the same dependency window)

Purpose:

- stabilize response ownership
- stabilize route ownership
- keep `/api/state` summary-only
- prepare recent-activity and library helper seams without touching frozen Stage/Match semantics

Exit criteria:

- route, state, and persistence seams are explicit enough for controller extraction to start

Dispatch note:

- `DEV-101`, `DEV-102`, and `DEV-103` are the worker-parallel lanes in this milestone.
- `DEV-104` shares the same milestone timing but remains integrator-only.

### Milestone 2 — Shared service convergence

Task:

- `DEV-105`

Purpose:

- extract or isolate shared non-Stage/non-Match controller responsibilities
- unify landing, proxy, backup, and related shared behaviors behind clearer ownership

Exit criteria:

- the controller no longer acts like the invisible owner of every app concern in the active seam

### Milestone 3 — Landing adoption and shell cleanup

Tasks:

- `DEV-106` — Landing UI backend adoption
- `DEV-107` — root shell registration and fallback cleanup

Purpose:

- make Landing use backend truth
- reduce legacy fallback ownership in the root shell
- keep Stage and Match behavior unchanged while shared ownership is narrowed

Exit criteria:

- Landing is backend-driven
- root shell scope is smaller and clearer
- no Stage or Match regressions are introduced

### Milestone 4 — Frozen-baseline proof readiness

Task:

- `DEV-201`

Purpose:

- classify meaningful control families for Stage and Match
- update proof, references, and QA/coverage docs honestly
- preserve freeze rules while raising proof discipline

Exit criteria:

- Stage and Match control families are mapped to truthful proof classes
- doc/test update obligations are explicit

### Milestone 5 — Integration, review, and handoff

Task:

- `DEV-301`

Purpose:

- merge shared ledgers
- run review, devil’s advocate, and validation passes
- publish the handoff state without over-claiming signoff

Exit criteria:

- all active development tasks are closed or explicitly reopened
- shared docs are synchronized
- residual risks and next actions are explicit

## Parallelization map

| Task | Wave | May run in parallel with | Shared-file overlap allowed? |
| --- | --- | --- | --- |
| `DEV-001` | 0 | none | no |
| `DEV-101` | 1 | `DEV-102`, `DEV-103`, `DEV-104` | no |
| `DEV-102` | 1 | `DEV-101`, `DEV-103`, `DEV-104` | no |
| `DEV-103` | 1 | `DEV-101`, `DEV-102`, `DEV-104` | no |
| `DEV-104` | 1 | `DEV-101`, `DEV-102`, `DEV-103` | no |
| `DEV-105` | 2 | none | no |
| `DEV-106` | 3 | none | no |
| `DEV-107` | 3 | none | no |
| `DEV-201` | 4 | none | no |
| `DEV-301` | 5 | none | no |

## Builder-agent read and reporting order

Every task execution must follow this order:

1. read `spec.md`
2. read `plan.md`
3. read `tasks.md`
4. read `progress.md`
5. read `proof.md`
6. read `outcome.md`
7. read the frozen references and touched source lanes

Every worker must return a handoff packet with:

- task ID
- files changed
- commands run and exit codes
- guardrail results
- reopen triggered: yes/no
- required doc and proof updates
- residual risks

## Non-goals

This plan does not authorize:

- Stage feature redesign
- Match feature redesign
- Performance Library feature expansion
- final signoff or screenshot closure
- opportunistic refactors outside the active allowlist

## Primary risks

- Landing can remain split between local browser memory and backend truth if `DEV-106` is approached before the shared contract lanes settle.
- `app.js` cleanup can accidentally mutate Stage or Match behavior if fallback removal gets ahead of proof and guardrail testing.
- `/api/state` and route-response ownership can drift apart if `DEV-101`, `DEV-102`, and `DEV-103` are not kept contract-tight.
- Frozen-baseline proof can still be overstated if `DEV-201` treats “a test exists” as equivalent to persisted or output-relevant proof.

## Required references

- `stage-reference.md`
- `match-reference.md`
- `../predev/backend/tasks.md`
- `../predev/backend/spec.md`
- `../predev/modularization/tasks.md`
- `../predev/modularization/spec.md`
- `docs/project/browser-control-qa-matrix.md`
- `docs/project/browser-control-coverage-plan.md`
- `docs/project/browser-full-e2e-qa-plan.md`

## Plan result

This plan is successful only when builders can execute the remaining foundation work in parallel without overlapping files, without inventing missing rules, and without breaking the frozen Stage and Match baselines.
