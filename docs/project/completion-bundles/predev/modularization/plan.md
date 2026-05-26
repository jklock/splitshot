# Modularization Completion Plan

## Objective

Complete the browser-shell modularization so Stage, Match, and Performance behave as separate apps on a shared shell and shared backend, with clear ownership boundaries and minimal cross-app leakage.

## Current execution status

- Normalized lane status: `implementation advanced / proof pending`
- Task status: `MOD-001` through `MOD-005` are complete for Work Effort 1; `MOD-006` and `MOD-007` remain open proof/signoff work
- Cross-lane authority: `../../MASTER_STATUS.md`

## Scope

This bundle covers front-end modularization only:

- shared shell orchestration boundaries
- `app.js` decomposition and ownership reduction
- shared runtime services and helper boundaries
- Stage, Match, and Performance app module seams
- app-local persistence and settings isolation
- DOM ownership, event wiring, and module import rules
- modularization docs, tests, and proof artifacts

## Non-goals

This bundle does not complete:

- backend contract redesign except where module boundaries require documented backend assumptions
- visual feature completion beyond the structural changes required to preserve app ownership
- unrelated refactors that do not reduce cross-app coupling

## Current-state summary

The browser shell is partway through modularization already:

- Match rendering lives in `views/match-view.js`
- Performance rendering lives in `views/library-view.js`
- shared runtime work lives under `lib/`
- pane-specific logic lives under `panes/`

The remaining problem is that root orchestration still carries too much behavioral weight, especially around Stage-heavy workflows and shell-level coordination.

Current facts that matter:

- `app.js` still acts as the state spine and contains meaningful orchestration and behavior.
- Match and Performance view modules exist, but ownership rules are not yet written as a stable contract.
- The architecture target is three apps on a shared shell with landing and global settings/config staying shared.
- The current pass materially advanced Stage/Match/Performance behavior, and this bundle has now had its dedicated modularization execution pass.

## Architecture boundaries

### Shared shell owns

- landing page
- app switching
- global status / notifications
- route/view error handling
- truly global settings/config entry points

### Stage app owns

- Stage shell and Stage-specific interaction behavior
- Stage pane activation and editing workflows
- Stage-local persistence and tool behavior

### Match app owns

- Match shell and workspace workflows
- Match-local settings and selection state
- Match recap/composite/export interaction behavior

### Performance app owns

- Performance shell and library workflows
- Performance-local settings and selection state
- Performance analytics/backup/export interaction behavior

## Modularization work phases

## Phase 1 — Inventory current ownership

Write down the current coupling before changing it:

- map `app.js` responsibilities
- map shared-runtime responsibilities
- map Stage, Match, and Performance ownership seams
- identify cross-app DOM access and hidden state dependencies

Exit criteria:

- current ownership map is recorded in `spec.md`
- modularization risks are explicitly named

## Phase 2 — Define stable module interfaces

Define what can talk to what:

- shared shell API
- app module API
- shared runtime service API
- state hydration adapters and event contracts
- app-local persistence boundaries

Exit criteria:

- import and dependency rules are explicit in `spec.md`
- app bundles can point to those rules without contradiction

## Phase 3 — Reduce root orchestration weight

Shrink `app.js` to orchestration rather than feature ownership:

- move app-specific behavior behind app-local modules where practical
- keep `app.js` responsible for surface switching and shared coordination only
- remove accidental cross-app coupling from root wiring

Exit criteria:

- root shell is smaller in responsibility even if some glue remains
- app-specific behavior is easier to prove in app-owned tests

## Phase 4 — Isolate app-local persistence and settings

Make per-app local state explicit:

- app-local localStorage namespaces
- app-local view selection memory
- app-local settings reload/apply behavior
- no silent leakage between Stage, Match, and Performance

Exit criteria:

- each app can reload its local settings without mutating the others

## Phase 5 — Prove modularization and lock it

Finalize the structure as an enforceable contract:

- source-level ownership tests
- app-owned e2e and interaction coverage
- docs that explain shell versus app ownership
- explicit residual risk list for any accepted temporary coupling

Exit criteria:

- modularization is no longer an implicit hope; it is written down and test-backed

## Universal acceptance criteria

The modularized shell must satisfy all of the following:

- Stage, Match, and Performance are separate app modules in behavior, not just labels
- shared shell remains responsible only for shared concerns
- app-local persistence/settings are isolated
- cross-app DOM access is minimized and documented when unavoidable
- app-level tests can run without hidden dependence on other app modules

## Primary risks

- source-string tests can make safe refactors look risky if module boundaries are not updated carefully
- app-local behavior can remain indirectly coupled through shared runtime helpers unless the interfaces are explicit
- root shell code can shrink superficially while hidden dependency chains remain unchanged

## Required references

- `../../ARCHITECTURE.md`
- `../../../src/splitshot/browser/static/app.js`
- `../../../src/splitshot/browser/static/lib/shell-runtime.js`
- `../../../src/splitshot/browser/static/views/match-view.js`
- `../../../src/splitshot/browser/static/views/library-view.js`
- `../../../../tests/TEST_SUITE_GUIDE.md`

## Plan result

This modularization bundle is the execution contract for enforcing the three-app browser architecture on top of the shared shell and shared backend.
