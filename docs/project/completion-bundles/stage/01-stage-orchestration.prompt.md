---
description: "End-to-end Stage-first shell reset orchestration using research, build, style enforcement, validation, and tester agent passes."
name: "01 Stage Shell Reset Orchestrator"
argument-hint: "Optional Stage workflow, regression, or shell seam to prioritize"
agent: "agent"
---

Use this prompt to execute the Stage bundle end to end.

Primary bundle references:

- [plan](./plan.md)
- [tasks](./tasks.md)
- [spec](./spec.md)
- [outcome](./outcome.md)
- [artifacts](./artifacts.md)

You must orchestrate five role-isolated subagent passes for this bundle:

1. Research agent
   - Run a read-focused pass first.
   - Gather the exact code, docs, routes, browser controls, and tests that own the requested Stage behavior and any shared shell primitives Stage owns.
   - Return: affected files, ownership seams, hidden risks, and recommended implementation order.

2. Build agent
   - Run a build-focused pass after research.
   - Produce the implementation plan for the requested Stage reset work.
   - If only one named subagent is available, still run a separate role-specific pass and instruct it to act as the build agent.
   - Return: target files, expected edits, migration notes, and likely regressions.

3. Style enforcement agent
   - Run a style pass after code/doc edits begin.
   - Check shell-family reuse, workflow-order preservation, naming, architecture boundaries, and repo-style alignment.
   - Return: structure violations, coupling concerns, and required cleanup.

4. Validation agent
   - Run a validation pass against the bundle docs and user-visible behavior.
   - Compare the implementation against `spec.md`, `tasks.md`, and the owning docs/tests.
   - Return: unmet requirements, stale docs, contract drift, and missing artifacts.

5. Tester agent
   - Run a testing pass before final signoff.
   - Identify the narrowest useful tests, then expand only as needed.
   - Return: exact test targets, expected failure surfaces, hidden-test risks, and any missing proof.

Execution rules:

- Run the five agent roles in that order unless a blocker requires a brief return to research.
- Keep each role output isolated; summarize the findings from one role before acting on the next.
- The main agent remains responsible for actual edits, test runs, and final synthesis.
- If only one named subagent is available, execute five separate `runSubagent` calls with role-specific prompts.
- Do not let build decisions override `spec.md` or `plan.md` without updating the bundle docs in the same change.
- Update `tasks.md`, `outcome.md`, and `artifacts.md` as work progresses.
- Prefer narrow tests first, then the owning suite, then broader validation.

Bundle-specific guardrails:

- Treat Stage as the canonical shell grammar reused by Match and Performance.
- Preserve the editing flow order: `Project -> PiP -> Splits/Score -> Overlay -> Markers -> Review -> Export`.
- Keep Project limited to setup/import/PractiScore responsibilities.
- Preserve the PractiScore browser-state contract: `practiscore_session`, `practiscore_sync`, and `practiscore_options`.
- Preserve the manual `Select PractiScore File` fallback plus the local `Match type`, `Stage #`, `Competitor name`, and `Place` controls unless the same change updates docs/tests.
- Treat Project-home defaults, primary-video import copy behavior, PiP waveform/sync, Review defaults/summary authoring, marker styling, and top-bar status placement as critical regressions if touched.
- If shared shell primitives change, update the owning Match and Performance bundle docs/tests in the same change.

Required work sequence:

1. Read `plan.md`, `spec.md`, and `tasks.md`.
2. Run the research agent pass.
3. Run the build agent pass.
4. Implement the agreed Stage changes incrementally.
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
