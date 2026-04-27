# Subagent Orchestration Prompt (runSubagent)

Use this prompt in an orchestrator session to execute Task A, then Task B, then Task C, and then run a final validation subagent.

## Orchestrator Responsibilities
1. Launch the Task A subagent first.
2. Require the Task A subagent to produce a proof-of-completion document that maps every task line item to objective evidence.
3. Require the Task A subagent to write status updates into `development/agentstatus.md`.
4. Do not launch Task B until Task A completes and its proof document exists.
5. Do not launch Task C until Task B completes and its proof document exists.
6. Launch a final validation subagent after all three task subagents complete.
7. Verify proof documents exist, are complete, and include evidence for each line item.
8. Mark orchestration complete only when the validator confirms 100% line-item completion across all tasks.

## Required Output Files
1. `development/task-a-proof-of-completion.md`
2. `development/task-b-proof-of-completion.md`
3. `development/task-c-proof-of-completion.md`
4. `development/final-validation-proof.md`
5. `development/agentstatus.md` (shared status log)

## Shared Coordination And Execution-Artifact Rule
The following files are shared orchestration artifacts and are allowed even though task docs otherwise use exclusive file ownership:

Shared planning-pack coordination files:
1. `development/plan-index.md`
2. `development/task-a-auth-session-foundation.md`
3. `development/task-b-acquisition-normalization.md`
4. `development/task-c-ui-parity-governance.md`
5. `development/user-workflow-simple-steps.md`
6. `development/subagent-orchestration-prompt.md`

Shared execution artifacts:
7. `development/agentstatus.md`
8. `development/task-a-proof-of-completion.md`
9. `development/task-b-proof-of-completion.md`
10. `development/task-c-proof-of-completion.md`
11. `development/final-validation-proof.md`

## Shared Status Logging Contract
Every subagent must append entries to `development/agentstatus.md` with this structure:

```md
## <UTC timestamp> | <agent-name> | <task-id>
- Status: not-started | in-progress | blocked | completed | validated
- Current line item: <exact line number or text from task doc>
- Evidence path(s): <file paths>
- Notes: <brief delta>
```

## Proof-Of-Completion Contract (Per Task)
Each task proof document must include:
1. A complete checklist of every numbered line item from its task document.
2. For each line item:
   - `Status: complete|incomplete`
   - `Evidence:` exact file paths, test names, command outputs, and doc sections.
   - `Validation note:` one sentence describing why the evidence proves completion.
3. A final summary table with:
   - total line items,
   - completed line items,
   - incomplete line items,
   - completion percent.
4. If any item is incomplete, include a remediation plan and owner.

## Sequential Execution Plan
1. Run Task A subagent.
2. Verify `development/task-a-proof-of-completion.md` exists.
3. Run Task B subagent.
4. Verify `development/task-b-proof-of-completion.md` exists.
5. Run Task C subagent.
6. Verify `development/task-c-proof-of-completion.md` exists.
7. Run the final validator subagent.

---

## runSubagent Call 1: Task A Agent
Use exactly this payload:

Description: `Implement Task A`

Prompt:
```text
You are responsible only for Task A in development/task-a-auth-session-foundation.md.

Hard boundaries:
1. Edit only Task A owned files from the task document.
2. The only allowed shared files are the orchestration artifacts under development/ listed in the orchestration prompt.
3. Do not edit Task B or Task C owned files.
4. Append status updates to development/agentstatus.md at start, major milestones, blockers, and completion.

Execution requirements:
1. Implement every numbered line item in Task A.
2. Run all Task A test commands listed in the task document.
3. Complete all Task A documentation updates listed in the task document.
4. Produce development/task-a-proof-of-completion.md.

Proof requirements:
1. Include every Task A line item as its own checklist row.
2. For each row, provide objective evidence: file paths, tests run, and output summary.
3. Provide final completion percent.
4. If not 100%, list remaining actions.

Definition of done:
- Task A implementation completed.
- Task A tests executed and passing, or exact blocker evidence is documented.
- Task A docs updated.
- task-a-proof-of-completion.md written.
- Final status appended to development/agentstatus.md.
```

## runSubagent Call 2: Task B Agent
Use exactly this payload after Task A completes:

Description: `Implement Task B`

Prompt:
```text
You are responsible only for Task B in development/task-b-acquisition-normalization.md.

Hard boundaries:
1. Edit only Task B owned files from the task document.
2. The only allowed shared files are the orchestration artifacts under development/ listed in the orchestration prompt.
3. Do not edit Task A or Task C owned files.
4. Append status updates to development/agentstatus.md at start, major milestones, blockers, and completion.

Execution requirements:
1. Implement every numbered line item in Task B.
2. Run all Task B test commands listed in the task document.
3. Complete all Task B documentation updates listed in the task document.
4. Produce development/task-b-proof-of-completion.md.

Proof requirements:
1. Include every Task B line item as its own checklist row.
2. For each row, provide objective evidence: file paths, tests run, and output summary.
3. Provide final completion percent.
4. If not 100%, list remaining actions.

Definition of done:
- Task B implementation completed.
- Task B tests executed and passing, or exact blocker evidence is documented.
- Task B docs updated.
- task-b-proof-of-completion.md written.
- Final status appended to development/agentstatus.md.
```

## runSubagent Call 3: Task C Agent
Use exactly this payload after Task B completes:

Description: `Implement Task C`

Prompt:
```text
You are responsible only for Task C in development/task-c-ui-parity-governance.md.

Hard boundaries:
1. Edit only Task C owned files from the task document.
2. The only allowed shared files are the orchestration artifacts under development/ listed in the orchestration prompt.
3. Do not edit Task A or Task B owned files.
4. Append status updates to development/agentstatus.md at start, major milestones, blockers, and completion.

Execution requirements:
1. Implement every numbered line item in Task C.
2. Run all Task C test commands listed in the task document.
3. Complete all Task C documentation updates listed in the task document.
4. Produce development/task-c-proof-of-completion.md.

Proof requirements:
1. Include every Task C line item as its own checklist row.
2. For each row, provide objective evidence: file paths, tests run, and output summary.
3. Provide final completion percent.
4. If not 100%, list remaining actions.

Definition of done:
- Task C implementation completed.
- Task C tests executed and passing, or exact blocker evidence is documented.
- Task C docs updated.
- task-c-proof-of-completion.md written.
- Final status appended to development/agentstatus.md.
```

## runSubagent Call 4: Final Validator Agent
Use exactly this payload after Calls 1-3 complete:

Description: `Validate all task completion`

Prompt:
```text
You are the final validator for development task pack execution.

Inputs to validate:
1. development/task-a-auth-session-foundation.md
2. development/task-b-acquisition-normalization.md
3. development/task-c-ui-parity-governance.md
4. development/task-a-proof-of-completion.md
5. development/task-b-proof-of-completion.md
6. development/task-c-proof-of-completion.md
7. development/agentstatus.md

Validation requirements:
1. Confirm each task proof doc includes every numbered line item from the corresponding task doc.
2. Confirm each line item has objective evidence: file paths, tests, doc updates, and command results.
3. Confirm evidence is consistent with actual changed files and test outputs.
4. Confirm no cross-task file ownership violations occurred outside the shared execution artifacts.
5. Compute completion percentages for Task A, Task B, Task C, and overall.
6. Append validator status updates to development/agentstatus.md.
7. Write development/final-validation-proof.md with:
   - per-task completion summary,
   - failed or missing evidence,
   - ownership boundary violations,
   - final overall completion percent,
   - explicit `PASS` only if all line items across all tasks are complete with valid evidence.

Definition of done:
- final-validation-proof.md exists.
- Overall completion percent is clearly stated.
- PASS only when completion is 100% with valid evidence.
```

## Orchestrator Completion Gate
The orchestrator must not finish until all are true:
1. Task A, Task B, and Task C proof documents exist and show 100% completion.
2. `development/final-validation-proof.md` exists and reports `PASS`.
3. `development/agentstatus.md` includes start and completion entries for all four agents.
4. No task ownership boundary violations remain unresolved.

Last updated: 2026-04-27
Referenced files last updated: 2026-04-27
