---
description: "End-to-end modularization orchestration using research, build, style enforcement, validation, and tester agent passes."
name: "Modularization Completion Orchestrator"
argument-hint: "Optional ownership seam, shell boundary, or refactor area to prioritize"
agent: "agent"
---

Use this prompt to execute the modularization completion bundle end to end.

Primary bundle references:

- [plan](./plan.md)
- [tasks](./tasks.md)
- [spec](./spec.md)
- [outcome](./outcome.md)
- [artifacts](./artifacts.md)

Status and prompt-source references:

- [master status](../../MASTER_STATUS.md)
- this unnumbered `orchestration.prompt.md` file is the canonical prompt source for the Modularization lane
- `05-modularization-orchestration.prompt.md` is an archival alias and must not diverge

You must orchestrate five role-isolated subagent passes for this bundle:

1. Research agent
   - Gather the exact shell modules, app modules, shared helpers, docs, and tests that own the requested architecture seam.
   - Return: affected files, current coupling map, hidden dependencies, and recommended implementation order.

2. Build agent
   - Produce the implementation plan for the requested modularization work.
   - If only one named subagent is available, run a separate role-specific pass and instruct it to act as the build agent.
   - Return: target files, interface changes, extraction strategy, and likely regressions.

3. Style enforcement agent
   - Review naming, module boundaries, cross-app DOM access, and shell-versus-app responsibility discipline.
   - Return: architecture drift, ownership violations, and cleanup requirements.

4. Validation agent
   - Compare the work against `spec.md`, `tasks.md`, and the architecture contract.
   - Return: unmet requirements, stale docs, ownership drift, and missing artifacts.

5. Tester agent
   - Identify the narrowest useful modularization and app-boundary tests first, then expand only if needed.
   - Return: exact test targets, expected failure surfaces, hidden coupling risks, and missing proof.

Execution rules:

- Run the five agent roles in order unless a blocker requires another research pass.
- Keep each role output isolated; summarize the findings from one role before acting on the next.
- The main agent remains responsible for edits, test runs, and final synthesis.
- If only one named subagent is available, execute five separate `runSubagent` calls with role-specific prompts.
- Do not let build decisions override `spec.md` or `plan.md` without updating the bundle docs in the same change.
- Update `tasks.md`, `outcome.md`, and `artifacts.md` as work progresses.
- Prefer narrow tests first, then source-level ownership checks, then app-owned interaction coverage.

Bundle-specific guardrails:

- Stage, Match, and Performance must remain separate apps on a shared shell and shared backend.
- Keep `app.js` focused on orchestration, not app-specific feature ownership.
- Minimize cross-app DOM access and hidden shared state.
- Keep app-local settings and persistence isolated.
- Document any temporary coupling that cannot be removed immediately.

Required work sequence:

1. Read `plan.md`, `spec.md`, and `tasks.md`.
2. Run the research agent pass.
3. Run the build agent pass.
4. Implement the agreed modularization changes incrementally.
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
