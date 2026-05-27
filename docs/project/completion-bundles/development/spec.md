# Development Specification

## Normative statement

`development/` is the active execution bundle for finishing the Landing Zone, shared backend, and modularization foundation without changing frozen Stage and Match behavior.

It is a **builder-facing execution contract**, not a historical archive and not the final signoff bundle.

## Required document set

The active `development/` bundle must contain and keep synchronized:

- `spec.md` — normative contract and execution rules
- `plan.md` — sequencing, dependencies, milestones, and exit criteria
- `tasks.md` — active executable backlog for builders
- `progress.md` — integrator-owned shared progress ledger
- `proof.md` — proof taxonomy and evidence requirements
- `outcome.md` — status narrative and current gate position
- `orchestration.prompt.md` — agent execution instructions

`artifacts.md` may remain only as a backward-compatibility pointer. New execution truth belongs in `progress.md`, `proof.md`, and `outcome.md`.

## Frozen behavior baselines

### Stage baseline

Stage behavior is frozen against:

- `stage-reference.md`
- `../predev/stage/outcome.md`
- `../predev/stage/artifacts.md`

### Match baseline

Match behavior is frozen against:

- `match-reference.md`
- `../predev/match/outcome.md`
- `../predev/match/artifacts.md`

### Frozen-baseline rules

- Do **not** introduce new Stage or Match features in this bundle.
- Do **not** change Stage or Match user-visible workflow semantics unless an explicit reopen is triggered.
- Treat the current Stage and Match source-lane outcomes as the baseline the foundation work must preserve.
- Use **Performance Library** in user-facing language. Internal `library` naming may remain in code and storage during this bundle unless a dedicated rename task is opened later.

### Protected route and behavior freeze

The following route families are frozen by default in this bundle:

- `/api/workspace/*`
- `/api/angle/*`
- `/api/audio/mix`
- `/api/scoring*`
- `/api/shots/*`

They may be touched only to preserve existing behavior while refactoring ownership boundaries. A semantic change to any of them is a reopen trigger.

## Active scope

This bundle actively owns only the remaining foundation work required to support modular, parallel-safe app development:

- make Landing Zone backend-driven and trustworthy
- split shared shell versus app ownership more explicitly
- keep `/api/state` summary-only and slice-based
- make route ownership explicit in the browser/server boundary
- extract shared services out of monolithic controller ownership where required
- remove legacy fallback ownership from root shell code where safe
- codify proof readiness for frozen Stage and Match behavior families
- prepare the system so a future app module can slot beside Stage, Match, and Performance Library without direct cross-app dependence

## Excluded scope

This bundle does **not** own:

- new Stage feature scope
- new Match feature scope
- Performance Library product expansion beyond foundation-seam work
- final screenshot packages
- final proof bundles and acceptance artifact capture
- final QA matrix closeout
- final visual approval and signoff
- silent reinterpretation of source-lane ownership

## Parallel execution model

### One owner per file per wave

- Each active task must have an explicit allowlist and forbid widening its edit surface without integrator approval.
- In a parallel wave, no two worker tasks may claim the same file.
- If two tasks need the same file, the plan must serialize them.

### Worker versus integrator responsibilities

- Worker tasks edit only their allowed implementation files and task-local tests.
- Worker tasks do **not** edit `progress.md`, `proof.md`, `outcome.md`, or shared source-lane ledgers.
- The integrator task owns shared ledgers, cross-lane synthesis, review-agent follow-up, and final handoff updates.

### Read order

Every execution pass must read in this order:

1. `spec.md`
2. `plan.md`
3. `tasks.md`
4. `progress.md`
5. `proof.md`
6. `outcome.md`
7. `stage-reference.md` and `match-reference.md`

## Reopen protocol

A frozen baseline may be reopened only when one of the following objective triggers fires:

1. a protected guardrail test fails after a foundation refactor
2. a semantic change to a protected frozen route or state contract becomes unavoidable
3. a data-loss, persistence-corruption, or reopen-path bug is found in the frozen baseline
4. a mandatory contract such as PractiScore fallback support cannot be preserved without a named behavior change

When a reopen trigger fires:

- stop the current worker task
- record the trigger in `progress.md`
- create a named reopen item in `outcome.md`
- update the relevant source lane before continuing
- do **not** hide the reopen inside general cleanup language

## Documentation and update obligations

Whenever a control owner, route, persistence target, or output path changes, the same change must update all applicable anchors:

- `stage-reference.md` and/or `match-reference.md`
- `proof.md`
- `docs/project/browser-control-qa-matrix.md`
- `docs/project/browser-control-coverage-plan.md` when coverage claims change
- `docs/project/browser-full-e2e-qa-plan.md` when end-to-end scope changes
- `tests/browser/test_browser_control_coverage_matrix.py`
- `tests/browser/test_browser_control_inventory_audit.py` when IDs or surfaces change
- relevant interaction, contract, persistence, and export tests
- user-facing docs when user-visible naming or workflow changes

Worker tasks satisfy this requirement by returning the required doc and proof updates in their handoff packet. The integrator merges those shared-ledger updates in the same integrated change before the wave is considered complete.

If a Project-pane PractiScore workflow or state changes, the same change must also preserve and update:

- manual `Select PractiScore File` fallback
- local `Match type`, `Stage #`, `Competitor name`, and `Place` controls
- `practiscore_session`, `practiscore_sync`, and `practiscore_options`

## Proof boundary

This bundle owns proof readiness, honest proof classification, and evidence requirements.

This bundle does **not** own final acceptance closure. Final screenshot packaging, acceptance artifacts, broad signoff, and testing-owned gates remain outside this bundle.

## Definition of success

The development specification is satisfied only when all of the following are true:

- Stage and Match remain frozen or are explicitly reopened and reclosed through the documented protocol
- Landing/shared shell/backend ownership is explicit enough for builder agents to work in parallel without overlap
- `plan.md`, `tasks.md`, `progress.md`, `proof.md`, and `outcome.md` all describe the same active execution model
- builder agents can execute tasks without inventing missing rules or widening scope on their own
- proof requirements are explicit enough that later `testing/` work does not need to rediscover what counts as meaningful closure
