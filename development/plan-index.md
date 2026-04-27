# PractiScore Sync Documentation Pack

## Purpose
This folder contains implementation task documents only. It does not implement code directly.

The task pack is designed so one person can execute each task end to end with no file ownership overlap between tasks.

## Deliverables
1. `task-a-auth-session-foundation.md`
2. `task-b-acquisition-normalization.md`
3. `task-c-ui-parity-governance.md`
4. `user-workflow-simple-steps.md`

## Non-Overlap Matrix

| Area | Task A Owns | Task B Owns | Task C Owns |
| --- | --- | --- | --- |
| Backend session routes | Yes | No | No |
| Browser auth profile/session modules | Yes | No | No |
| Extraction + normalization modules | No | Yes | No |
| Controller sync orchestration | No | Yes | No |
| Browser static UI controls | No | No | Yes |
| Browser state payload fields for UI rendering | No | No | Yes |
| Route-level session API tests | Yes | No | No |
| Extraction/normalization tests | No | Yes | No |
| Browser interaction + coverage matrix tests | No | No | Yes |
| Architecture/developing docs | Yes | No | No |
| Workflow/troubleshooting docs | No | Yes | No |
| Project pane + QA matrix docs | No | No | Yes |
| Agent instruction files under `.github/` | No | No | Yes |

Hard rule: each task can only edit files listed in its own document.

## Execution Order
1. Run Task A first.
2. Run Task B second.
3. Run Task C third.

## Integration Contracts Between Tasks
1. Task A provides stable session payload states:
   - `not_authenticated`
   - `authenticated`
   - `expired`
   - `challenge_required`
   - `error`
2. Task B provides stable sync result payload fields:
   - `status`
   - `matches_processed`
   - `matches_failed`
   - `errors`
   - `practiscore_options`
3. Task C only consumes the two contract payloads above and must not redesign them.

## Definition Of Done For This Planning Pack
1. Each task doc includes numbered code steps.
2. Each task doc includes numbered test steps.
3. Each task doc includes numbered documentation steps.
4. Tasks do not share owned files.
5. User workflow doc is plain numbered English with no implementation jargon.

## Suggested Branching Strategy For Human Implementers
1. Create three sequential PRs: Task A, Task B, Task C.
2. Do not combine tasks into one PR.
3. Require tests and docs updates in the same PR as the code change.

Last updated: 2026-04-27
Referenced files last updated: 2026-04-27
