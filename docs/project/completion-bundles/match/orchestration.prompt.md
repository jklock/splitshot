---
description: "End-to-end Match shared-shell reset orchestration using research, build, style enforcement, validation, and tester agent passes."
name: "Match Shell Reset Orchestrator"
argument-hint: "Optional Match workflow, regression, or shell seam to prioritize"
agent: "agent"
---

Use this prompt to execute the Match bundle end to end.

Primary bundle references:

- [plan](./plan.md)
- [tasks](./tasks.md)
- [spec](./spec.md)
- [outcome](./outcome.md)
- [artifacts](./artifacts.md)

You must orchestrate five role-isolated subagent passes for this bundle:

1. Research agent
   - Gather the exact Match-owned code, routes, docs, controls, and tests for the requested workflow plus any shared shell primitives Match depends on.
   - Return: affected files, workspace/backend ownership seams, risky dependencies, and recommended implementation order.

2. Build agent
   - Produce the implementation plan for the requested Match reset work.
   - If only one named subagent is available, run a separate role-specific pass and instruct it to act as the build agent.
   - Return: target files, expected changes, data-flow assumptions, and likely regressions.

3. Style enforcement agent
   - Review Stage-shell reuse, tile/info workflow integrity, naming consistency, and shell-boundary compliance.
   - Return: style violations, shell/app boundary drift, and cleanup requirements.

4. Validation agent
   - Compare the work against `spec.md`, `tasks.md`, and the Match documentation/test contract.
   - Return: unmet requirements, stale docs, route-contract drift, and missing artifacts.

5. Tester agent
   - Identify the narrowest useful Match tests first, then expand only if needed.
   - Return: exact test targets, expected failure surfaces, e2e risks, and missing proof.

Execution rules:

- Run the five agent roles in order unless a blocker requires another research pass.
- Keep each role output isolated; summarize the findings from one role before acting on the next.
- The main agent remains responsible for edits, test runs, and final synthesis.
- If only one named subagent is available, execute five separate `runSubagent` calls with role-specific prompts.
- Do not let build decisions override `spec.md` or `plan.md` without updating the bundle docs in the same change.
- Update `tasks.md`, `outcome.md`, and `artifacts.md` as work progresses.
- Prefer narrow tests first, then Match-owned suites, then broader shared validation.

Bundle-specific guardrails:

- Treat Match as a Stage-shell variant, not a separate shell family.
- Keep tiles in the main area, selected-tile information in the lower pane, and Match workflow controls in the right-hand inspector.
- Protect workspace lifecycle, stage membership, Stage auto-seed behavior, stage-open/return behavior, apply-from-first behavior, recap, composite, and batch export workflows.
- Do not let Match settings mutate Stage or Performance behavior.
- If shared shell primitives change, update the owning Stage and Performance bundle docs/tests in the same change.
- If Match controls or routes change, update the owning tests and QA docs in the same change.

Required work sequence:

1. Read `plan.md`, `spec.md`, and `tasks.md`.
2. Run the research agent pass.
3. Run the build agent pass.
4. Implement the agreed Match changes incrementally.
5. Run the style enforcement pass and apply cleanup.
6. Run the validation pass and close spec/doc gaps.
7. Run the tester pass and execute the narrowest useful tests.
8. Update `outcome.md` and `artifacts.md` with proof and residual risk notes.

Expected final output:

- Research findings
- Implementation summary
- Style enforcement findings and fixes
- Validation findings and doc-alignment updates
- Test plan and test results
- Bundle doc updates
- Remaining risks and next actions
