# Shared Backend Task Backlog

## Usage

- Treat each item as incomplete until its proof exists.
- Link implementation work, route evidence, test results, and doc updates in `outcome.md` and `artifacts.md`.
- The backend is done only when the app bundles can point at one stable contract.

## BEK-001 — Inventory route and state ownership

- [x] Classify shared routes versus Stage, Match, and Performance routes.
- [x] Classify shared state versus app summary slices in `/api/state`.
- [x] Record global settings and landing support ownership.
- [x] Record backend-owning tests and docs.

Depends on:

- none

Proof:

- `spec.md` route/state ownership sections completed
- owning tests/docs listed in `artifacts.md`

Progress note (`2026-05-25`):

- `spec.md` now carries an explicit shared/Stage/Match/Performance route inventory, the landing/global support routes, and the current `/api/state` summary families.
- `artifacts.md` now points at the owning backend, persistence, library, and PractiScore test files used in this pass.

## BEK-002 — Harden `/api/state` summary contract

- [x] Define the summary-only contract for `/api/state`.
- [x] Record which app slices belong in the summary response.
- [x] Move or keep heavy workflows on dedicated routes by contract.
- [x] Define global versus app-local settings/state boundaries.

Depends on:

- BEK-001

Proof:

- `/api/state` behavior and docs agree
- backend/app tests for summary state remain green

Progress note (`2026-05-25`):

- `/api/state` is now documented as a summary-only contract with explicit key families for shared settings, media, timing/scoring, PractiScore, Match/workspace, and Performance summary state.
- Heavy record, backup/export, recap, and planning payloads remain on dedicated routes by contract.

## BEK-003 — Normalize status, error, and activity behavior

- [x] Define consistent success/error response expectations where practical.
- [x] Define recoverable error behavior for browser callers.
- [x] Align activity logging expectations across shared routes.
- [x] Define fallback/error behavior for import and remote-session workflows.

Depends on:

- BEK-001
- BEK-002

Proof:

- route tests and docs agree on status/error handling
- error-path evidence linked in `artifacts.md`

Progress note (`2026-05-25`):

- Recoverable browser-visible failures remain explicit for PractiScore session/sync flows and for Performance library stale/error recovery.
- The library now exposes visible manual refresh and retry entry points instead of hiding recovery inside an unloaded inspector path.

## BEK-004 — Close persistence and truth behavior

- [x] Prove workspace save/load/autosave stability.
- [x] Prove stage open and return-to-workspace stability.
- [x] Prove workspace-to-library synchronization behavior.
- [x] Prove truth-hash behavior where library sync depends on it.
- [x] Prove backup/export/import persistence correctness where shared backend owns it.

Depends on:

- BEK-002
- BEK-003

Proof:

- persistence and backend tests pass
- artifact evidence exists for cross-app reopen and sync behavior

Progress note (`2026-05-25`):

- The targeted backend/state/persistence/library pack passed with `134 passed`.
- Match auto-attach/auto-create workspace behavior and cross-surface reopen flows stayed green in the targeted browser packs used during this pass.

## BEK-005 — Protect import and PractiScore contracts

- [x] Preserve blank-project and saved-project import behavior where supported.
- [x] Preserve PractiScore session, sync, and options summary payloads.
- [x] Preserve manual file fallback behavior relied on by Stage.
- [x] Prove recoverable failure behavior for remote PractiScore flows.

Depends on:

- BEK-002
- BEK-003

Proof:

- import and PractiScore tests pass
- Stage bundle dependencies remain truthful

Progress note (`2026-05-25`):

- Targeted PractiScore browser/session/controller coverage stayed green in the `18 passed` interaction/session pack.
- PractiScore analysis import and normalization coverage stayed green in the `22 passed` analysis pack.
- The manual `Select PractiScore File` fallback path remains preserved.

## BEK-006 — Lock Match and Performance backend support

- [x] Prove workspace routes used by Match remain stable.
- [x] Prove library routes used by Performance remain stable.
- [x] Prove app reopen targets and export/backup routes are truthful.
- [x] Record any dedicated app-route guarantees in docs.

Depends on:

- BEK-004
- BEK-005

Proof:

- Match and Performance backend dependencies are green
- route evidence linked in `artifacts.md`

Progress note (`2026-05-25`):

- Match workspace lifecycle, Performance reopen targets, and library backend contracts stayed green in the targeted packs used for this pass.
- Route guarantees are now summarized in `spec.md` and linked in `artifacts.md` for Work Effort 1 handoff.

## BEK-007 — Sync backend docs and proof package

- [x] Update architecture or adjacent backend docs where ownership changed.
- [x] Update test guide or route-owner docs where validation changed.
- [x] Record route, state, persistence, and error-path proof artifacts.
- [x] Record residual risks and waivers.

Depends on:

- BEK-003
- BEK-004
- BEK-005
- BEK-006

Proof:

- doc diffs linked in `artifacts.md`
- proof package complete in `outcome.md`

Progress note (`2026-05-26`):

- Focused backend proof reruns stayed green with `114 passed` across `tests/browser/test_practiscore_session_api.py`, `tests/browser/test_practiscore_sync_controller.py`, and `tests/browser/test_browser_control.py`; `38 passed` across `tests/persistence/test_workspace_persistence.py`, `tests/persistence/test_persistence.py`, and `tests/persistence/test_project_lifecycle_contracts.py`; `22 passed` across `tests/browser/test_project_lifecycle_contracts.py` and `tests/browser/test_library_backend_contracts.py`; and `22 passed` across the PractiScore analysis import/normalize/extract pack.
- `./.venv/bin/splitshot --check` passed, and `artifacts/test-suite-backend-signoff.json` now records a green persistence+analysis owner-suite anchor (`125 passed`).
- `artifacts/test-suite-backend-browser.json` now records a green browser owner-suite anchor (`420 passed`), and the Work Effort 2 source/aggregate/top-level ledgers now point at the same backend proof package.
- No additional architecture or test-guide contract rewrite was required in the final pass because the route/state ownership docs already matched the backend truth; the closeout work in this task was the proof-package and ledger sync.

## BEK-008 — Shared backend done gate

- [x] Confirm shared backend tests are green.
- [x] Confirm Stage, Match, and Performance bundles reference the same backend truth.
- [x] Confirm required route/state/persistence artifacts exist.
- [x] Confirm residual risks are documented.
- [x] Confirm approval is recorded.

Depends on:

- BEK-007

Proof:

- `outcome.md` final gate marked complete

Progress note (`2026-05-26`):

- Runtime health passed, `artifacts/test-suite-backend-signoff.json` recorded `125 passed`, and `artifacts/test-suite-backend-browser.json` recorded `420 passed` across the broader browser owner suite.
- The backend, Stage, Match, Performance, aggregate testing, and top-level completion ledgers now reference the same backend proof truth, so the shared backend done gate is closed.
