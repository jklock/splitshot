---
description: "End-to-end Work Effort 2 testing orchestration across Stage, Match, Performance, Backend, Modularization, and the source tests bundle."
name: "Testing Work Effort Orchestrator"
argument-hint: "Optional source lane, proof gap, or closeout area to prioritize"
agent: "agent"
---

Use this prompt to execute the aggregate `testing/` bundle end to end.

Primary bundle references:

- [plan](./plan.md)
- [tasks](./tasks.md)
- [spec](./spec.md)
- [outcome](./outcome.md)
- [artifacts](./artifacts.md)

Status and prompt-source references:

- [master status](../MASTER_STATUS.md)
- this unnumbered `orchestration.prompt.md` file is the canonical prompt source for the `testing/` bundle
- source bundles under `../predev/` remain the detailed task truth and must be updated alongside this aggregate bundle when real proof/signoff status moves
- source `predev/tests/` is one source lane inside this effort; it is not the same thing as aggregate `testing/`

You must orchestrate five role-isolated subagent passes for this bundle:

1. Research agent
   - Gather the exact source-bundle proof gaps, artifacts, screenshots, docs, and suites that must close for the requested Work Effort 2 scope.
   - Return: affected files, source task IDs, evidence gaps, hidden blockers, and recommended closeout order.

2. Build agent
   - Produce the testing/proof/signoff plan for the requested Work Effort 2 change.
   - If only one named subagent is available, run a separate role-specific pass and instruct it to act as the build agent.
   - Return: target files, expected evidence work, suite strategy, and likely reopened blockers.

3. Style enforcement agent
   - Review work-effort boundary discipline, proof-source integrity, `tests/` versus `testing/` wording, and source/aggregate ledger alignment.
   - Return: documentation drift, ownership drift, and cleanup requirements.

4. Validation agent
   - Compare the work against `spec.md`, `tasks.md`, the touched source bundles, and the final-gate obligations recorded in `../MASTER_STATUS.md`.
   - Return: unmet requirements, stale docs, invalid proof assumptions, and any source gate that still cannot close.

5. Tester agent
   - Identify the narrowest useful focused tests first, then expand to owned suites and the canonical full-suite anchor only as required.
   - Return: exact validation targets, expected failure surfaces, reopened implementation risks, and any missing proof.

Execution rules:

- Run the five agent roles in order unless a blocker requires another research pass.
- Execute one atomic `VAL-*` slice per subagent unless `tasks.md` explicitly marks a safe parallel bundle.
- Treat each slice block in `tasks.md` as authoritative for dependencies, parallelization, proof minimums, allowed edit surface, and exact commands.
- When `tasks.md` marks slices as parallel-safe, use separate subagents for those slices and a single integrator pass to merge ledger updates afterward.
- Keep each role output isolated; summarize the findings from one role before acting on the next.
- The main agent remains responsible for edits, test runs, proof capture, and final synthesis.
- If only one named subagent is available, execute five separate `runSubagent` calls with role-specific prompts.
- Do not let `testing/` silently absorb first-order implementation work; if testing uncovers a real implementation blocker, reopen the relevant source bundle and hand it back to `development/` explicitly.
- Update the touched source bundles and this aggregate bundle in the same change whenever proof/signoff status actually moves.
- Prefer focused proof runs first, then owned suites, then broader closeout.

Bundle-specific guardrails:

- `testing/` owns proof packages, screenshots, artifact capture, QA/coverage/test-guide sync, final suite closure, and signoff.
- source `predev/tests/` is a detailed source lane, not a synonym for aggregate `testing/`.
- Do not count historical artifacts or the repo-health baseline alone as proof of source final-gate closure.
- No source bundle may be marked `done` unless its own `outcome.md` final gate is fully closed.
- If Work Effort 2 uncovers a real development blocker, record it explicitly instead of hiding it inside proof language.

Required work sequence:

1. Read `plan.md`, `spec.md`, and `tasks.md`.
2. Pick the exact `VAL-*` slice or slice bundle from `tasks.md` before delegating any subagent work.
3. Read the touched source bundle `tasks.md`, `outcome.md`, and `artifacts.md` files under `../predev/`.
4. Run the research agent pass.
5. Run the build agent pass.
6. Close the agreed proof, artifact, screenshot, and doc-sync work incrementally.
7. Run the style enforcement pass and apply cleanup.
8. Run the validation pass and close source/aggregate drift.
9. Run the tester pass and execute focused proof runs, owned suites, and the canonical full-suite anchor as needed.
10. Update the touched source ledgers and the aggregate `testing/` ledgers with final-gate status, residual risks, and signoff notes.

Expected final output:

- Research findings
- Proof/signoff summary
- Style enforcement findings and fixes
- Validation findings and source/aggregate alignment updates
- Test plan and results
- Artifact and screenshot updates
- Remaining risks, waivers, and next actions
