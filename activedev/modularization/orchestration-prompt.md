# Modularization Orchestration Prompt

Use this prompt as the stable preamble when launching a subagent for any task in this program.

## Required mission statement

You are executing one task from SplitShot's modularization program. This is a **zero-functional-change internal refactor**. The browser UI, visible controls, copy, layout, and workflows must remain identical to the current application.

## Read order

Before making any change, read these files in order:

1. `activedev/modularization/plan.md`
2. the assigned task file in `activedev/modularization/tasks/`
3. `activedev/modularization/validation.md`
4. `activedev/modularization/audit.md`
5. `activedev/modularization/progress.md`
6. any source documents linked by the task file

Do not begin implementation until the task status is confirmed as claimable and all dependencies are `done`.

## Operating rules

1. Claim the task in `progress.md` before editing any owned file.
2. Touch only files listed in the task's `touches-files` section.
3. Treat the task's `forbidden-files` section as absolute.
4. If the task depends on exact ownership anchors from `T01`, stop if those anchors are missing or stale.
5. Do not change visible UI behavior, copy, layout, pane order, or control ids.
6. Do not add new product features.
7. Do not silently alter API routes or persistence contracts.
8. Update related tests and docs required by the task in the same run.
9. When blocked, stop and record the blocker in `progress.md` rather than improvising outside scope.

## Required outputs

At the end of the run, the subagent must:

1. execute the task's required validation scope from `validation.md`
2. execute the task's required structural checks from `audit.md`
3. write a new proof file in `activedev/modularization/proof/`
4. update `progress.md` with status, proof link, and concise notes

## Proof content requirements

Every proof file must include:

- task id and run id
- timestamp
- branch or commit reference if available
- summary of changed files
- validation commands run
- summarized validation output or key result lines
- audit checks run and outcome
- final verdict: `pass`, `pass-with-risk`, or `fail`
- any follow-up or unblock notes

## Stop conditions

Stop and report instead of continuing when:

- a dependency task is not `done`
- owned-file boundaries are ambiguous
- a required QA or audit baseline is missing
- the change appears to require visible UI or workflow drift
- validation fails and the failure cannot be corrected inside the assigned scope

## Response format for subagent handoff

Use this short handoff structure:

- **Task:** `<task id>`
- **Changed:** `<files changed>`
- **Validated:** `<commands/tests/audits run>`
- **Proof:** `<proof file path>`
- **Result:** `<done | blocked | failed>`
- **Risks:** `<remaining concerns>`
