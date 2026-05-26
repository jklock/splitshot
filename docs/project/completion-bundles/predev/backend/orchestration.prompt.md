---
description: "End-to-end shared-backend completion orchestration using research, build, style enforcement, validation, and tester agent passes."
name: "Shared Backend Completion Orchestrator"
argument-hint: "Optional backend route, state, persistence, or contract area to prioritize"
agent: "agent"
---

Use this prompt to execute the shared backend completion bundle end to end.

Primary bundle references:

- [plan](./plan.md)
- [tasks](./tasks.md)
- [spec](./spec.md)
- [outcome](./outcome.md)
- [artifacts](./artifacts.md)

Status and prompt-source references:

- [master status](../../MASTER_STATUS.md)
- this unnumbered `orchestration.prompt.md` file is the canonical prompt source for the Backend lane
- `04-backend-orchestration.prompt.md` is an archival alias and must not diverge

You must orchestrate five role-isolated subagent passes for this bundle:

1. Research agent
   - Gather the exact shared-backend routes, state serializers, controller seams, persistence helpers, docs, and tests that own the requested change.
   - Return: affected files, route/state ownership, risky cross-app dependencies, and recommended implementation order.

2. Build agent
   - Produce the implementation plan for the requested backend work.
   - If only one named subagent is available, run a separate role-specific pass and instruct it to act as the build agent.
   - Return: target files, payload changes, migration notes, and likely regressions.

3. Style enforcement agent
   - Review route naming, ownership boundaries, status/error shape, and shared-versus-app contract discipline.
   - Return: architecture drift, naming violations, hidden coupling, and cleanup requirements.

4. Validation agent
   - Compare the work against `spec.md`, `tasks.md`, and the backend/app contract docs.
   - Return: unmet requirements, stale docs, route/state drift, and missing artifacts.

5. Tester agent
   - Identify the narrowest useful backend tests first, then expand only if needed.
   - Return: exact route/state/persistence test targets, expected failure surfaces, and hidden-test risks.

Execution rules:

- Run the five agent roles in order unless a blocker requires another research pass.
- Keep each role output isolated; summarize the findings from one role before acting on the next.
- The main agent remains responsible for edits, test runs, and final synthesis.
- If only one named subagent is available, execute five separate `runSubagent` calls with role-specific prompts.
- Do not let build decisions override `spec.md` or `plan.md` without updating the bundle docs in the same change.
- Update `tasks.md`, `outcome.md`, and `artifacts.md` as work progresses.
- Prefer narrow tests first, then shared-backend suites, then broader app-dependent validation.

Bundle-specific guardrails:

- Keep `/api/state` summary-oriented.
- Keep heavy workflows on dedicated routes instead of bloating the summary state spine.
- Preserve Stage-facing import and PractiScore contracts unless intentionally changed and synchronized.
- Preserve Match-facing workspace route stability and Performance-facing library route stability.
- Treat the shared backend as shared infrastructure, not as a reason to blur Stage, Match, and Performance back into one app.

Required work sequence:

1. Read `plan.md`, `spec.md`, and `tasks.md`.
2. Run the research agent pass.
3. Run the build agent pass.
4. Implement the agreed backend changes incrementally.
5. Run the style enforcement pass and apply cleanup.
6. Run the validation pass and close spec/doc gaps.
7. Run the tester pass and execute the narrowest useful tests.
8. Update `outcome.md` and `artifacts.md` with proof and residual risk notes.

Expected final output:

- Research findings
- Implementation summary
- Style enforcement findings and fixes
- Validation findings and doc alignment updates
- Test plan and test results
- Bundle doc updates
- Remaining risks and next actions
