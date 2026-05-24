---
description: "End-to-end test modularization orchestration using research, build, style enforcement, validation, and tester agent passes."
name: "Test Modularization Orchestrator"
argument-hint: "Optional app lane, test migration area, or fixture problem to prioritize"
agent: "agent"
---

Use this prompt to execute the test modularization bundle end to end.

Primary bundle references:

- [plan](./plan.md)
- [tasks](./tasks.md)
- [spec](./spec.md)
- [outcome](./outcome.md)
- [artifacts](./artifacts.md)

You must orchestrate five role-isolated subagent passes for this bundle:

1. Research agent
   - Gather the exact Stage-, Match-, Performance-, and shared-owned tests, fixtures, docs, and runner mappings relevant to the requested change.
   - Return: affected files, current ownership map, mixed-test risks, and recommended implementation order.

2. Build agent
   - Produce the implementation plan for the requested test-architecture work.
   - If only one named subagent is available, run a separate role-specific pass and instruct it to act as the build agent.
   - Return: target files, suite or folder changes, fixture changes, and likely regressions.

3. Style enforcement agent
   - Review test naming, ownership boundaries, fixture isolation, artifact-path discipline, and suite taxonomy consistency.
   - Return: architecture drift, suite-boundary violations, and cleanup requirements.

4. Validation agent
   - Compare the work against `spec.md`, `tasks.md`, and the test-guide / QA-matrix contract.
   - Return: unmet requirements, stale docs, ownership drift, and missing artifacts.

5. Tester agent
   - Identify the narrowest useful validation path for the changed suites first, then expand only if needed.
   - Return: exact test targets, expected failure surfaces, hidden coupling risks, and missing proof.

Execution rules:

- Run the five agent roles in order unless a blocker requires another research pass.
- Keep each role output isolated; summarize the findings from one role before acting on the next.
- The main agent remains responsible for edits, test runs, and final synthesis.
- If only one named subagent is available, execute five separate `runSubagent` calls with role-specific prompts.
- Do not let build decisions override `spec.md` or `plan.md` without updating the bundle docs in the same change.
- Update `tasks.md`, `outcome.md`, and `artifacts.md` as work progresses.
- Prefer narrow tests first, then app-owned suites, then broader shared validation.

Bundle-specific guardrails:

- Stage, Match, and Performance must each have owned tests and owned e2e.
- Shared-shell/backend suites must stay limited to truly shared behavior.
- Fixture and artifact isolation must prevent one app lane from depending on another lane’s leftovers.
- If test ownership or browser-visible coverage changes, update the QA and coverage docs in the same change.

Required work sequence:

1. Read `plan.md`, `spec.md`, and `tasks.md`.
2. Run the research agent pass.
3. Run the build agent pass.
4. Implement the agreed test-architecture changes incrementally.
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
