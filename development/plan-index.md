# PractiScore Sync Documentation Pack

## Purpose
This folder contains the implementation plan for a one-match-at-a-time PractiScore sync flow.

The feature goal is narrow and explicit:
1. The user manually authenticates to PractiScore in a visible browser session managed by SplitShot.
2. SplitShot discovers the user's available remote matches.
3. The user selects exactly one remote match to import.
4. SplitShot downloads the selected match artifacts and feeds the existing PractiScore import path.
5. The Project pane returns to the existing local `Match type`, `Stage #`, `Competitor name`, and `Place` controls.

This pack does not implement code directly. It defines execution-ready task boundaries, contracts, and validation steps.

## Product Rules This Pack Assumes
1. A SplitShot project continues to hold one staged PractiScore source and one imported stage at a time.
2. Sync does not add multi-match storage to the project model.
3. Manual `Select PractiScore File` import remains supported as a fallback and as an overwrite path.
4. The authenticated session is user-driven. SplitShot does not collect or store PractiScore credentials in project files.
5. The browser UI renders authoritative data from `/api/state`, even when action routes are used for connect, clear, discover, and import actions.

## Deliverables
1. `task-a-auth-session-foundation.md`
2. `task-b-acquisition-normalization.md`
3. `task-c-ui-parity-governance.md`
4. `user-workflow-simple-steps.md`
5. `subagent-orchestration-prompt.md`
6. `agentstatus.md`

## Feature Contract Summary
1. Session/auth and remote-match selection are separate concerns from local PractiScore stage context.
2. Existing local import context still flows through the current PractiScore import controls after sync completes.
3. The selected remote match becomes the staged PractiScore source for the project, just like a manually selected CSV or TXT file does today.
4. Downloaded HTML and remote-match summary data are phase-one sync artifacts. They are cached locally for audit and troubleshooting, but the scoring source of truth remains the downloaded CSV or TXT import artifact.

## Ownership Matrix

| Area | Task A Owns | Task B Owns | Task C Owns |
| --- | --- | --- | --- |
| PractiScore browser profile/session modules | Yes | No | No |
| PractiScore session routes in `server.py` | Yes | No | No |
| Discovery/import route surface in `server.py` | Yes | No | No |
| Remote match discovery helpers | No | Yes | No |
| Artifact download and cache helpers | No | Yes | No |
| CSV/TXT-to-existing-import normalization bridge | No | Yes | No |
| Controller sync orchestration | No | Yes | No |
| Browser-state payload contract for session/sync | No | Yes | No |
| Project-pane HTML, JS, and CSS | No | No | Yes |
| Static UI/state-consumption tests | No | No | Yes |
| Session route tests | Yes | No | No |
| Extraction/controller tests | No | Yes | No |
| Workflow/troubleshooting docs | No | Yes | No |
| Project pane docs, QA matrix, and `.github` governance | No | No | Yes |
| Architecture/developing docs | Yes | No | No |
| Dependency manifest and generated `uv.lock` companion | Yes | No | No |

Hard rule: each task can only edit files listed in its own document.

Planning-pack coordination exception: when this task pack is being authored, maintained, or validator-remediated as one coordinated unit, `development/plan-index.md`, `development/task-a-auth-session-foundation.md`, `development/task-b-acquisition-normalization.md`, `development/task-c-ui-parity-governance.md`, `development/user-workflow-simple-steps.md`, and `development/subagent-orchestration-prompt.md` are shared coordination artifacts and do not count as ownership violations.

Execution-artifact exception: when the orchestration prompt is used, `development/agentstatus.md`, `development/task-a-proof-of-completion.md`, `development/task-b-proof-of-completion.md`, `development/task-c-proof-of-completion.md`, and `development/final-validation-proof.md` are shared execution artifacts and do not count as ownership violations.

## Execution Order
1. Run Task A first.
2. Run Task B second.
3. Run Task C third.
4. Run the final validator after Task C completes.

Parallel execution is not allowed for the main implementation tasks because Task B depends on Task A route/session contracts and Task C depends on Task A and Task B payload contracts.

## Integration Contracts Between Tasks
1. Task A provides a stable session route surface:
   - `POST /api/practiscore/session/start`
   - `GET /api/practiscore/session/status`
   - `POST /api/practiscore/session/clear`
   - `GET /api/practiscore/matches`
   - `POST /api/practiscore/sync/start`
2. Task A also provides a stable session status payload shape:
   - `state`
   - `message`
   - `details`
3. Task A session states are:
   - `not_authenticated`
   - `authenticating`
   - `authenticated_ready`
   - `challenge_required`
   - `expired`
   - `error`
4. Task B provides a stable `/api/state` contract for UI rendering:
   - `practiscore_session`
   - `practiscore_sync`
   - `practiscore_options`
5. Task B `practiscore_sync` states are:
   - `idle`
   - `discovering_matches`
   - `match_list_ready`
   - `importing_selected_match`
   - `success`
   - `error`
6. Task B exposes available remote matches as a list of stable objects with:
   - `remote_id`
   - `label`
   - `match_type`
   - `event_name`
   - `event_date`
7. Task C consumes the session, sync, and local PractiScore payloads above and must not redesign their field names.

## Artifact Contract
1. Sync operates on one selected remote match per request.
2. The selected match download must include:
   - the CSV or TXT artifact used for scoring import,
   - the selected-match HTML page,
   - a serialized summary snapshot of the selected-match metadata shown to the user.
3. The CSV or TXT artifact becomes the staged PractiScore source that drives the existing import path.
4. The HTML and summary snapshot are cached locally for audit and troubleshooting. They are not required to reopen a project in phase one.

## Conflict Resolution Rules
1. A successful sync replaces the currently staged PractiScore source in the same way a new manual file import does.
2. A later manual file import may overwrite the synced source.
3. Existing reimport-on-context-change behavior must keep working after both sync and manual imports.

## Definition Of Done For This Planning Pack
1. Each task doc includes numbered code steps.
2. Each task doc includes numbered test steps.
3. Each task doc includes numbered documentation steps.
4. Every required code surface has exactly one owner.
5. The user workflow doc matches the selected-match flow and does not claim automatic batch import.
6. The orchestration prompt matches the sequential dependency order and the shared coordination/execution-artifact exceptions.

## Suggested Branching Strategy For Human Implementers
1. Create three sequential PRs: Task A, Task B, Task C.
2. Keep the validator/proof artifacts in the same working branch during orchestration, or drop them before PR creation if they are execution-only artifacts.
3. Require tests and docs updates in the same PR as the code change.

Last updated: 2026-04-27
Referenced files last updated: 2026-04-27
