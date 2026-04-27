# PractiScore Sync Agent Boundaries

PractiScore sync work in this repository is intentionally split by ownership.

## Ownership Model

- Task A owns PractiScore session internals and the session-route foundation.
- Task B owns remote match discovery, artifact download, normalization, and the `/api/state` payload bridge.
- Task C owns the Project-pane browser UI, owned browser tests, user-facing docs, QA matrix updates, and the `.github` governance files for this feature area.

## Working Rules

- Do not edit another task's owned files unless a follow-up task explicitly transfers ownership.
- For Project-pane PractiScore changes, update source, owned tests, user docs, and QA/governance docs together so the browser shell, coverage claims, and guidance stay in parity.
- Keep the manual file-import fallback available unless product direction explicitly removes it.
- If a requested change crosses the Task A or Task B boundary, stop at the boundary and either split the work or escalate the ownership issue instead of making opportunistic edits.