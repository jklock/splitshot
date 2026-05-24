# Modularization Specification

## Normative statement

The browser shell must implement a three-app architecture: Stage, Match, and Performance as separate app modules on top of a shared shell and shared backend.

## Shared shell requirements

The shared shell may own only the following concerns:

- landing page
- app switching and active-surface coordination
- global status and notifications
- route/view error handling
- truly global settings/config entry points

The shared shell must not become the owner of app-specific editing workflows.

## App module requirements

### Stage app

The Stage app owns:

- Stage DOM and Stage view behavior
- Stage tool activation and Stage pane behavior
- Stage-local settings and interaction logic

### Match app

The Match app owns:

- Match DOM and Match workspace behavior
- Match section switching and Match-local state
- Match recap/composite/export interaction logic

### Performance app

The Performance app owns:

- Performance DOM and record-browsing behavior
- Performance section switching and Performance-local state
- Performance analytics/backup/export interaction logic

## Dependency rules

- App modules may depend on shared shell services and shared backend calls.
- App modules must not directly own or mutate other app modules’ DOM or local state.
- Shared helpers may be used by multiple apps only when their ownership is truly shared and documented.
- Temporary exceptions must be explicitly documented in `outcome.md`.

## Root orchestration requirements

- `app.js` must remain an orchestration spine, not an app-specific feature bucket.
- Root orchestration may coordinate surface switching, refresh, and shared shell concerns.
- App-specific behavior should live behind app-owned modules or documented helper seams.

## State and persistence requirements

- App-local persistence and settings must remain app-scoped.
- Reopening or reloading one app’s settings must not silently mutate another app’s state.
- Shared shell state must be limited to truly shared concerns such as active surface, global status, and shared settings entry points.

## DOM ownership requirements

- App modules should operate within their own view roots.
- Cross-app DOM access must be avoided where possible.
- Any unavoidable cross-app DOM dependency must be documented and justified.

## Documentation and contract requirements

Any modularization change that affects ownership or test expectations requires synchronized updates to:

- app-owned tests
- any source-level ownership tests or audits
- architecture documentation where ownership changed
- app bundle docs that describe shell versus app boundaries

## Test requirements

At minimum, modularization completion must be backed by:

- source-level ownership or contract coverage
- app-owned interaction/e2e coverage where wiring changed
- docs/tests that clearly identify shared shell versus app ownership

## Definition of specification success

The modularization spec is satisfied only when code structure, tests, docs, and app bundles all describe the same three-app ownership model.
