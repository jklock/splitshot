---
description: "End-to-end Work Effort 1 development orchestration across Stage, Match, Performance, Backend, and Modularization."
name: "Development Work Effort Orchestrator"
argument-hint: "Optional source lane, implementation seam, or dependency to prioritize"
agent: "agent"
---

Use this prompt to execute the aggregate `development/` bundle end to end.

Primary bundle references:

- [plan](./plan.md)
- [tasks](./tasks.md)
- [spec](./spec.md)
- [outcome](./outcome.md)
- [artifacts](./artifacts.md)

Status and prompt-source references:

- [master status](../MASTER_STATUS.md)
- this unnumbered `orchestration.prompt.md` file is the canonical prompt source for the `development/` bundle
- source bundles under `../predev/` remain the detailed task truth and must be updated alongside this aggregate bundle when real implementation status moves

You must orchestrate five role-isolated subagent passes for this bundle:

1. Research agent
   - Gather the exact source-bundle tasks, code, routes, docs, and dependencies that own the requested implementation seam.
   - Return: affected files, source task IDs, hidden blockers, and recommended implementation order.

2. Build agent
   - Produce the implementation plan for the requested Work Effort 1 change.
   - If only one named subagent is available, run a separate role-specific pass and instruct it to act as the build agent.
   - Return: target files, expected changes, migration notes, and likely regressions.

3. Style enforcement agent
   - Review work-effort boundary discipline, shell/app ownership, route/state ownership, naming consistency, and source-bundle sync.
   - Return: structure violations, coupling concerns, and required cleanup.

4. Validation agent
   - Compare the work against `spec.md`, `tasks.md`, the touched source bundles, and the `development/` versus `testing/` split.
   - Return: unmet requirements, stale docs, source/aggregate drift, and boundary violations.

5. Tester agent
   - Identify the narrowest useful validation needed to unblock implementation without claiming final proof/signoff closure.
   - Return: exact validation targets, expected failure surfaces, reopened implementation risks, and any handoff work that must stay in `testing/`.

Execution rules:

- Run the five agent roles in order unless a blocker requires another research pass.
- Execute one atomic `DEV-*` slice per subagent unless `tasks.md` explicitly marks a safe parallel bundle.
- Treat each slice block in `tasks.md` as authoritative for dependencies, parallelization, allowed edit surface, and exact commands.
- When `tasks.md` marks slices as parallel-safe, use separate subagents for those slices and a single integrator pass to merge ledger updates afterward.
- Keep each role output isolated; summarize the findings from one role before acting on the next.
- The main agent remains responsible for edits, limited validation, and final synthesis.
- If only one named subagent is available, execute five separate `runSubagent` calls with role-specific prompts.
- Do not let implementation decisions override `spec.md` or the touched source bundles without updating those docs in the same change.
- Update the touched source bundles and this aggregate bundle in the same change whenever implementation status actually moves.
- Prefer narrow validation that unblocks implementation; leave proof packaging, screenshots, and final gate closure to `testing/`.

Bundle-specific guardrails:

- `development/` is implementation-only.
- `testing/` owns proof packages, screenshots, artifact capture, QA/coverage closeout, final suite closure, and signoff.
- source `predev/tests/` is a detailed source lane, not the same thing as aggregate `testing/`.
- Do not silently claim `TST-*` work, final artifacts, or visual approval inside `development/`.
- If testing discovers a real implementation blocker, reopen the relevant source bundle explicitly instead of smuggling that blocker into Work Effort 2.

Required work sequence:

1. Read `plan.md`, `spec.md`, and `tasks.md`.
2. Pick the exact `DEV-*` slice or slice bundle from `tasks.md` before delegating any subagent work.
3. Read the touched source bundle `tasks.md`, `spec.md`, `outcome.md`, and `artifacts.md` files under `../predev/`.
4. Run the research agent pass.
5. Run the build agent pass.
6. Implement the agreed development changes incrementally.
7. Run the style enforcement pass and apply cleanup.
8. Run the validation pass and close source/aggregate drift.
9. Run the tester pass and execute the narrowest useful implementation validation.
10. Update the touched source ledgers and the aggregate `development/` ledgers with handoff notes and residual risks.

Expected final output:

- Research findings
- Implementation summary
- Style enforcement findings and fixes
- Validation findings and source/aggregate alignment updates
- Narrow validation plan and results
- Handoff notes for `testing/`
- Remaining risks and next actions
