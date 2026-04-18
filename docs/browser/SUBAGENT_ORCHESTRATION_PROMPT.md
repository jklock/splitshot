# Subagent Orchestration Prompt

Copy and paste the text below into a new chat if you want an orchestrator agent to run the entire left-pane remediation program end to end.

---

You are the remediation orchestrator for the SplitShot left-pane hardening program in `/Volumes/Storage/GitHub/splitshot`.

Your job is to complete, validate, test, remediate, revalidate, and close all remaining left-pane work by coordinating subagents and doing any required integration work yourself. Do not stop at planning. Execute the program to completion.

## Mission

Finish every remaining left-pane remediation item defined by the current documentation set, produce proof of completion, and produce evidence for zero known regressions against the frozen user-visible contracts.

## Required Source Documents

Read these first and treat them as the source of truth:

- `/Volumes/Storage/GitHub/splitshot/docs/browser/LEFT_PANE_AUDIT.md`
- `/Volumes/Storage/GitHub/splitshot/docs/browser/LEFT_PANE_REMEDIATION_TODO.md`
- `/Volumes/Storage/GitHub/splitshot/docs/browser/LEFT_PANE_IMPLEMENTATION_SPEC.md`
- `/Volumes/Storage/GitHub/splitshot/docs/browser/SUBAGENT_TODO_PROJECT_AND_IMPORT.md`
- `/Volumes/Storage/GitHub/splitshot/docs/browser/SUBAGENT_TODO_SCORE_AND_METRICS.md`
- `/Volumes/Storage/GitHub/splitshot/docs/browser/SUBAGENT_TODO_SPLITS_AND_WAVEFORM.md`
- `/Volumes/Storage/GitHub/splitshot/docs/browser/SUBAGENT_TODO_MERGE_AND_EXPORT.md`
- `/Volumes/Storage/GitHub/splitshot/docs/browser/SUBAGENT_TODO_OVERLAY_AND_REVIEW.md`
- `/Volumes/Storage/GitHub/splitshot/docs/browser/progress.md`

## First Required Action

Before doing any other work, update `/Volumes/Storage/GitHub/splitshot/docs/browser/progress.md` to reflect that orchestration has started.

At minimum:

- set overall program status to `in-progress`
- set orchestrator status to `in-progress`
- add the current date to the validation ledger or subagent ledger as orchestration start
- record which workstreams are pending

Do not skip this. `progress.md` is the authoritative execution ledger and must stay current throughout the run.

## Hard Constraints

- Preserve current user-visible behavior unless a documented remediation item explicitly fixes a bug.
- Do not redesign the product.
- Do not rename existing DOM ids, browser data attributes, API routes, request shapes, project JSON keys, export preset ids, or saved bundle structure.
- Do not revert unrelated user changes in the worktree.
- Prefer narrow fixes and additive targeted tests over broad rewrites.
- Use real bundled media and the existing browser audit scripts for any preview or export parity claim.
- Do not claim `0 regressions` until all frozen contracts have passing evidence and no known regressions remain.

## Frozen Contracts

These must remain stable unless an item explicitly documents a bug fix that preserves the user-facing contract:

- left rail page set, order, and labels
- existing DOM ids and data attributes used by the browser shell
- existing `/api/*` routes and request shapes
- existing project JSON keys and saved bundle layout
- existing export preset ids, default values, and file-path behavior
- existing visible labels users already rely on in the pane UI
- existing bundled-media browser audit flows that already pass

## Execution Model

You must run the program as an orchestrator with subagents.

### Workstreams

Dispatch and complete all five workstreams:

1. Project and Import
2. Score and Metrics
3. Splits and Waveform
4. Merge and Export
5. Overlay and Review

### Subagent Rules

- Use one subagent per workstream whenever practical.
- Each subagent must be given its packet file as the primary scope contract.
- Each subagent must be told to write code, add or update targeted tests, run its owned validations, and report changed files, tests run, results, and residual risks.
- Keep each subagent inside its owned file and function families unless a cross-seam dependency is unavoidable.
- If two workstreams need the same hot file, stage the higher-isolation change first and integrate carefully.

### Orchestrator Responsibilities

- Launch the workstream subagents.
- Review their outputs for completeness and regression risk.
- Apply any required integration fixes yourself.
- Run the required cross-workstream validations after all packets land.
- Keep `progress.md` current before, during, and after execution.
- Do not stop when a subagent finishes; continue until the whole program is validated end to end.

## Required Workflow

### Phase 1: Intake and progress initialization

1. Read the required source documents.
2. Update `progress.md` to `in-progress`.
3. Create a concise execution plan only if needed for coordination. Do not stall in planning.

### Phase 2: Workstream execution

1. Dispatch the five workstreams.
2. For each returned subagent result:
   - verify all checklist items in the packet were addressed
   - verify targeted tests were added or updated
   - verify required validations were actually run
   - update `progress.md` with status, evidence, and any blockers
3. If a subagent leaves gaps, remediate them immediately or re-dispatch a focused follow-up subagent.

### Phase 3: Integration remediation

1. Read the combined diff carefully.
2. Resolve conflicts across shared hot files.
3. Run any additional code fixes needed to preserve frozen contracts and align cross-pane behavior.
4. Update `progress.md` after each major integration repair.

### Phase 4: Validation and proof

Run the full validation program after all workstreams are complete.

Required validation commands:

- `pytest tests/browser`
- `pytest tests/analysis`
- `pytest tests/presentation`
- `pytest tests/scoring`
- `pytest tests/export`
- `pytest tests/persistence`
- `python scripts/audits/browser/run_browser_interaction_audit.py --browser chromium --report-json logs/browser-interaction-audit-test-videos-integration.json`
- `python scripts/audits/browser/run_browser_export_matrix.py`

Also run the workstream-level validations that each packet requires if they were not already run or if integration changes touched those seams again.

### Phase 5: Final closeout

You are only done when all of the following are true:

- every workstream is marked complete in `progress.md`
- all required validations are green
- browser audits are green where required
- no known user-visible regressions remain against the frozen contracts
- `progress.md` includes final proof of completion
- your final user-facing summary includes concrete evidence, not just claims

## What Each Subagent Prompt Must Require

When launching a workstream subagent, require the subagent to:

- read its packet file first
- implement the packet fully, not partially
- add or update the targeted tests named in the packet
- run the packet validation commands
- preserve current user-visible behavior
- report:
  - changed files
  - checklist items completed
  - tests run and results
  - browser audits run and results, if any
  - known risks or unresolved blockers

## Progress File Update Protocol

Every time something material changes, update `/Volumes/Storage/GitHub/splitshot/docs/browser/progress.md`.

Minimum required updates:

- orchestration start
- each subagent launch
- each subagent completion
- every validation attempt, with pass or fail result
- every discovered blocker or regression
- final completion proof

Do not leave the file stale.

## Definition of Proof

Your final proof must be evidence-based.

You must provide:

- the completed workstream list
- changed files summary
- targeted tests added or updated
- exact validation commands run
- pass or fail results for each validation command
- browser audit report locations
- explicit statement of whether any known regressions remain
- explicit statement supporting the `0 regressions` verdict from the validation evidence

## Definition of Done

The job is done only when the repo is fully remediated for all remaining left-pane items, validated end to end, and `progress.md` records proof of completion.

If a validation fails, you are not done. Fix it, update `progress.md`, and rerun validation.

If a subagent finishes only part of its packet, you are not done. Re-dispatch or finish the work yourself.

If any frozen contract regresses, you are not done. Remediate it and prove the fix.

Proceed now.

---