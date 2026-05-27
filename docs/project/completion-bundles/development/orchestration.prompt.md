---
description: "Execute the active development bundle as a frozen-baseline, builder-agent orchestration set."
name: "Development Builder Orchestrator"
argument-hint: "Optional task ID, lane, or dependency to prioritize"
agent: "agent"
---

Use this prompt to execute the active `development/` bundle end to end.

Primary bundle references:

- [spec](./spec.md)
- [plan](./plan.md)
- [tasks](./tasks.md)
- [progress](./progress.md)
- [proof](./proof.md)
- [outcome](./outcome.md)

Frozen baseline references:

- [stage reference](./stage-reference.md)
- [match reference](./match-reference.md)

Compatibility reference:

- [artifacts compatibility note](./artifacts.md)

Status and prompt-source references:

- [master status](../MASTER_STATUS.md) — cross-bundle reference only until the integrator records a real status move there
- this unnumbered `orchestration.prompt.md` file is the canonical prompt source for the `development/` bundle
- source bundles under `../predev/` remain the detailed task truth and must be updated alongside this aggregate bundle when real implementation status moves

You must orchestrate five role-isolated subagent passes for this bundle:

1. Research agent
   - Gather the exact code, routes, docs, tests, and dependencies that own the requested task.
   - Return: affected files, hidden blockers, freeze risks, and recommended implementation order.

2. Build agent
   - Produce the implementation plan for the requested task using the task allowlist exactly.
   - Return: target files, expected changes, migration notes, and likely regressions.

3. Devil’s-advocate agent
   - Try to break the plan before code does.
   - Review freeze risks, overlap risks, hidden coupling, stale assumptions, and test gaps.
   - Return: what could still go wrong, what is under-specified, and what must be tightened before merge.

4. Validation agent
   - Compare the work against `spec.md`, `tasks.md`, `progress.md`, `proof.md`, the frozen references, and the touched source bundles.
   - Return: unmet requirements, stale docs, source/aggregate drift, and boundary violations.

5. Tester agent
   - Identify the narrowest useful validation needed to unblock implementation without claiming final proof/signoff closure.
   - Return: exact validation targets, expected failure surfaces, reopened implementation risks, and any handoff work that must stay in `testing/`.

Execution rules:

- Run the five agent roles in order unless a blocker requires another research pass.
- Execute only the task or wave listed under `Released now` in `progress.md`.
- Follow the allowlist and forbidden-edit rules in `tasks.md` exactly.
- Workers do not improvise scope and do not edit shared ledgers.
- Only the integrator merges updates into `progress.md`, `proof.md`, `outcome.md`, or shared source-lane ledgers.
- If a task is marked parallel-safe, use separate subagents for those worker tasks and a single integrator pass to merge results afterward.
- If only one named subagent is available, execute separate `runSubagent` calls for each role.
- Prefer narrow validation that unblocks implementation; leave final proof/signoff packaging to `testing/`.

Bundle-specific guardrails:

- Stage and Match are frozen behavior baselines.
- Do not change Stage or Match semantics unless the reopen protocol in `spec.md` is triggered.
- Preserve manual PractiScore fallback and the `practiscore_session`, `practiscore_sync`, and `practiscore_options` contract.
- `development/` owns proof readiness, not final proof closure.
- `testing/` owns final screenshot packages, acceptance artifacts, broad QA closeout, and signoff.

Required work sequence:

1. Read `spec.md`, `plan.md`, `tasks.md`, `progress.md`, `proof.md`, and `outcome.md`.
2. Use the command policy in `tasks.md` over generic repo-level example commands while executing this bundle.
3. Read `stage-reference.md` and `match-reference.md` before touching shared shell, route, or state seams.
4. Pick the exact `DEV-*` task from `tasks.md` before delegating any subagent work.
5. Read the touched source bundle `tasks.md`, `spec.md`, `outcome.md`, and `artifacts.md` files under `../predev/` only if the current task actually moves that source lane.
6. Run the research agent pass.
7. Run the build agent pass.
8. Implement the agreed task incrementally.
9. Run the devil’s-advocate pass and tighten anything under-specified.
10. Run the validation pass and close source/aggregate drift.
11. Run the tester pass and execute the narrowest useful implementation validation.
12. If you are the integrator, update `progress.md`, `proof.md`, `outcome.md`, and any touched source ledgers.
13. Publish the next-wave or handoff state explicitly.

Expected final output:

- Research findings
- Implementation summary
- Devil’s-advocate findings and fixes
- Validation findings and source/aggregate alignment updates
- Narrow validation plan and results
- Handoff notes for the next integrator or for `testing/`
- Remaining risks and next actions
