# Shared Backend Completion Plan

## Objective

Complete the shared backend as the stable contract layer for landing, global settings/config, Stage, Match, and Performance without re-merging the three apps into one indistinct surface.

## Scope

This bundle covers the shared backend only:

- browser route ownership in `src/splitshot/browser/server.py`
- browser state serialization and summary behavior
- controller mutation boundaries in `src/splitshot/ui/controller.py`
- shared persistence and truth-hash behavior
- workspace, library, import, and PractiScore contracts used across apps
- global settings, landing support, and app-switching data needs
- backend docs, tests, and proof artifacts

## Non-goals

This bundle does not complete:

- visual app-shell work beyond backend contract support
- broad domain-model redesign unless required to make app contracts truthful
- independent analysis-algorithm changes that do not affect shared app contracts

## Current-state summary

The current shared backend already has the right broad shape:

- one browser server with namespaced routes
- one controller mutation boundary
- dedicated route groups for workspace, library, PractiScore, and media flows
- a summary state endpoint at `/api/state`
- persistence helpers for workspaces, library records, and project bundles

The current risk is not missing routes so much as mixed ownership and uneven proof:

- app-specific behavior can still feel monolithic when server/controller responsibilities are not explicitly mapped to app ownership
- `/api/state` can become overloaded if heavy app-specific payloads drift into the summary spine
- status and error behavior is not yet documented as one stable backend contract across all app lanes

## Architecture boundaries

### Shared backend owns

- route transport and request validation
- controller mutation entry points
- persistence truth and autosave behavior
- summary state serialization
- global settings and cross-app status surfaces
- landing support data that is truly shared

### Stage, Match, and Performance own

- their UI behavior and per-app interaction flows
- app-local persistence settings and visual state
- app-specific proof artifacts and user-visible docs

### Shared shell owns

- app switching
- landing page shell
- global status and notification presentation
- global settings entry points

## Backend work phases

## Phase 1 — Route and ownership inventory

Make ownership explicit before changing behavior:

- classify shared routes versus Stage, Match, and Performance routes
- classify which state keys belong in `/api/state`
- classify which mutations must remain dedicated POST routes

Exit criteria:

- route ownership is recorded in `spec.md`
- test and doc owners are listed in `artifacts.md`

## Phase 2 — Summary-state contract hardening

Keep `/api/state` summary-oriented:

- define app summary slices
- define which data is safe for every refresh
- keep heavy app flows on dedicated routes
- define app-local versus global settings/state boundaries

Exit criteria:

- `/api/state` is documented as a summary spine, not a dumping ground
- app bundles can rely on stable summary slices

## Phase 3 — Status, error, and activity normalization

Unify backend truth presentation:

- consistent success/error payload shape where practical
- consistent activity logging
- consistent recoverable error semantics for browser callers
- explicit fallback behavior for known remote or file-import failures

Exit criteria:

- backend-facing docs and tests share the same status/error assumptions

## Phase 4 — Persistence and truth closure

Close persistence and cross-app truth behavior:

- workspace save/load/autosave stability
- stage open / return-to-workspace stability
- workspace-to-library synchronization and truth hash behavior
- backup/export/import persistence correctness

Exit criteria:

- persistence behavior is proven and documented across Stage, Match, and Performance dependencies

## Phase 5 — Shared-contract signoff

Finalize backend readiness for the three apps:

- Stage, Match, and Performance bundles reference the same backend contract truth
- shared backend tests are green
- route, state, and docs all agree on ownership and payload behavior

Exit criteria:

- no app bundle is relying on undocumented backend behavior

## Universal acceptance criteria

The shared backend must satisfy all of the following:

- `/api/state` remains summary-oriented
- heavy app-specific workflows use dedicated routes
- route namespaces match app ownership or clearly shared behavior
- persistence and reopen flows are deterministic
- recoverable error paths are visible and testable

## Primary risks

- monolithic refactors can break source-string and route-registration tests even when behavior looks unchanged
- hidden coupling between controller state and app UI can create false positives in narrow backend tests
- app bundles can drift if backend route ownership is implied rather than written down

## Required references

- `../../ARCHITECTURE.md`
- `../../../tests/TEST_SUITE_GUIDE.md`
- `../../../src/splitshot/browser/server.py`
- `../../../src/splitshot/browser/state.py`
- `../../../src/splitshot/ui/controller.py`

## Plan result

This backend bundle is the execution contract for keeping the SplitShot shared backend stable, explicit, and aligned with the three-app architecture.
