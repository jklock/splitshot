# Shared Backend Task Backlog

## Usage

- Treat each item as incomplete until its proof exists.
- Link implementation work, route evidence, test results, and doc updates in `outcome.md` and `artifacts.md`.
- The backend is done only when the app bundles can point at one stable contract.

## BEK-001 — Inventory route and state ownership

- [ ] Classify shared routes versus Stage, Match, and Performance routes.
- [ ] Classify shared state versus app summary slices in `/api/state`.
- [ ] Record global settings and landing support ownership.
- [ ] Record backend-owning tests and docs.

Depends on:

- none

Proof:

- `spec.md` route/state ownership sections completed
- owning tests/docs listed in `artifacts.md`

## BEK-002 — Harden `/api/state` summary contract

- [ ] Define the summary-only contract for `/api/state`.
- [ ] Record which app slices belong in the summary response.
- [ ] Move or keep heavy workflows on dedicated routes by contract.
- [ ] Define global versus app-local settings/state boundaries.

Depends on:

- BEK-001

Proof:

- `/api/state` behavior and docs agree
- backend/app tests for summary state remain green

## BEK-003 — Normalize status, error, and activity behavior

- [ ] Define consistent success/error response expectations where practical.
- [ ] Define recoverable error behavior for browser callers.
- [ ] Align activity logging expectations across shared routes.
- [ ] Define fallback/error behavior for import and remote-session workflows.

Depends on:

- BEK-001
- BEK-002

Proof:

- route tests and docs agree on status/error handling
- error-path evidence linked in `artifacts.md`

## BEK-004 — Close persistence and truth behavior

- [ ] Prove workspace save/load/autosave stability.
- [ ] Prove stage open and return-to-workspace stability.
- [ ] Prove workspace-to-library synchronization behavior.
- [ ] Prove truth-hash behavior where library sync depends on it.
- [ ] Prove backup/export/import persistence correctness where shared backend owns it.

Depends on:

- BEK-002
- BEK-003

Proof:

- persistence and backend tests pass
- artifact evidence exists for cross-app reopen and sync behavior

## BEK-005 — Protect import and PractiScore contracts

- [ ] Preserve blank-project and saved-project import behavior where supported.
- [ ] Preserve PractiScore session, sync, and options summary payloads.
- [ ] Preserve manual file fallback behavior relied on by Stage.
- [ ] Prove recoverable failure behavior for remote PractiScore flows.

Depends on:

- BEK-002
- BEK-003

Proof:

- import and PractiScore tests pass
- Stage bundle dependencies remain truthful

## BEK-006 — Lock Match and Performance backend support

- [ ] Prove workspace routes used by Match remain stable.
- [ ] Prove library routes used by Performance remain stable.
- [ ] Prove app reopen targets and export/backup routes are truthful.
- [ ] Record any dedicated app-route guarantees in docs.

Depends on:

- BEK-004
- BEK-005

Proof:

- Match and Performance backend dependencies are green
- route evidence linked in `artifacts.md`

## BEK-007 — Sync backend docs and proof package

- [ ] Update architecture or adjacent backend docs where ownership changed.
- [ ] Update test guide or route-owner docs where validation changed.
- [ ] Record route, state, persistence, and error-path proof artifacts.
- [ ] Record residual risks and waivers.

Depends on:

- BEK-003
- BEK-004
- BEK-005
- BEK-006

Proof:

- doc diffs linked in `artifacts.md`
- proof package complete in `outcome.md`

## BEK-008 — Shared backend done gate

- [ ] Confirm shared backend tests are green.
- [ ] Confirm Stage, Match, and Performance bundles reference the same backend truth.
- [ ] Confirm required route/state/persistence artifacts exist.
- [ ] Confirm residual risks are documented.
- [ ] Confirm approval is recorded.

Depends on:

- BEK-007

Proof:

- `outcome.md` final gate marked complete
