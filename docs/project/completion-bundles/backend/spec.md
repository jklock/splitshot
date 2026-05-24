# Shared Backend Specification

## Normative statement

The shared backend is the contract layer beneath the Stage, Match, and Performance apps. It must expose explicit route ownership, summary state, deterministic persistence, and recoverable error behavior without collapsing app boundaries.

## Route ownership requirements

### Shared routes

Shared routes must be limited to behavior that is genuinely shared, such as:

- `/api/state`
- global settings and app-switch support data
- landing support data where applicable
- status, processing, or shared utility flows that are not app-specific

### Stage-supporting routes

Stage-supporting routes may remain in the shared backend, but their ownership must be treated as Stage-facing contracts. This includes file import, project mutation, and PractiScore-related support used by Stage workflows.

### Match routes

Workspace routes are Match-facing contracts and must remain explicitly namespaced and documented as such.

### Performance routes

Library routes are Performance-facing contracts and must remain explicitly namespaced and documented as such.

## `/api/state` requirements

- `/api/state` must remain a summary-oriented endpoint.
- `/api/state` must provide only the data required for cross-app hydration, current status, and app summary state.
- Heavy app workflows must use dedicated routes rather than bloating `/api/state`.
- App-local settings or large workflow payloads must not drift into `/api/state` without explicit contract updates.

## Controller boundary requirements

- `ui.controller` is the mutation boundary for shared project/workspace/library truth.
- `browser.server` owns HTTP transport and browser-facing route contracts, not domain business logic.
- The backend must not require UI modules to infer hidden controller state in order to operate correctly.

## Persistence requirements

- Save/load/autosave behavior must be deterministic.
- Workspace open-stage and return-to-workspace behavior must preserve identity and truth.
- Workspace-to-library synchronization must be deterministic.
- Truth-hash behavior used to guard library sync must remain stable and testable.
- Export, backup, and restore flows must record truthful paths and results.

## Status and error requirements

- Browser callers must receive recoverable, user-visible error information for expected failure classes.
- Remote-session, sync, import, export, backup, and restore failures must not silently degrade state.
- Status and activity behavior must be consistent enough that tests and docs can rely on them.

## PractiScore and import requirements

- The backend must preserve Stage-facing PractiScore contracts used by the browser state.
- The backend must preserve manual PractiScore file import support.
- The backend must preserve supported import behavior for blank-project and saved-project flows.

## Cross-app support requirements

- Match-facing workspace routes must remain stable and namespaced.
- Performance-facing library routes must remain stable and namespaced.
- Shared backend behavior must not force Stage, Match, or Performance to depend on each other’s UI modules.

## Documentation and contract requirements

Any backend route, state, or persistence contract change requires synchronized updates to:

- owning backend/browser tests
- architecture documentation where ownership changed
- test guide documentation where validation changed
- app bundle docs that reference the changed contract

## Test requirements

At minimum, backend completion must be backed by:

- route registration and contract coverage
- browser state serialization coverage
- persistence and reopen-flow coverage
- import and PractiScore coverage
- workspace and library backend coverage

## Definition of specification success

The shared backend spec is satisfied only when routes, summary state, persistence, tests, docs, and the three app bundles all describe the same backend contract.
