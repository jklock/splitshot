# Performance Specification

## Normative statement

Performance is a Stage-shell variant for history, analytics, reopen, and data-protection workflows. It must not define a separate shell family from Stage.

## Naming requirements

- User-facing documentation and UI must refer to this app as Performance or Performance Library, not as an implementation detail.
- Current internal identifiers such as `view-library` or `createLibraryView` may remain temporarily, but any rename must be coordinated across tests, docs, and code.
- Settings storage must remain app-local. If the existing `splitshot.library.settings` namespace changes, the migration must be explicit and tested.

## Performance shell requirements

### Layout grammar

The Performance app must provide:

- the same shell family as Stage
- graphs and data in the main content area
- a lower pane that shows truthful information about the selected record
- a right-hand inspector for filters, detail actions, notes/tags, backup/export, and settings
- footer order `Home` then `Settings`
- visible empty, loading, stale, and error states where relevant

### Ownership requirements

- Performance-specific behavior must stay inside Performance-owned modules and routes.
- Stage owns the canonical shell grammar reused by Performance.
- Shared shell may switch views and show global status only.

## Overview and records requirements

- Summary tiles must reflect the currently loaded record set truthfully.
- Personal-best and recent-activity summaries must not overstate missing data.
- Search input must either work as documented or be corrected in docs and UX copy.
- Sort behavior must be deterministic.
- Discipline filtering must be deterministic.
- Record selection must populate the lower selected-record detail/info pane truthfully.

## Detail and reopen requirements

- Selected-record detail must render a truthful payload.
- Open Stage must resolve a valid stage reopen target when available.
- Open Workspace must resolve a valid match/workspace reopen target when available.
- Tags and notes must not be called complete without persistence proof.

## Analytics requirements

- Score trend and discipline breakdown visuals must be backed by real data.
- Analytics empty-state and insufficient-data behavior must be user-visible.
- Outlier or comparison claims must either be implemented and proven or removed/corrected in docs.

## Backup and export requirements

- Backup create and restore behavior must be available through Performance-owned entry points.
- CSV and JSON export behavior must be available through Performance-owned entry points.
- Success and failure states for backup/export must be user-visible.
- Backup/export workflows cannot be called complete without output proof.

## Performance settings requirements

- Performance settings must be isolated to Performance behavior.
- Auto-refresh behavior must be deterministic.
- Performance settings must not mutate Stage or Match settings.

## Documentation and contract requirements

Any Performance-visible shell or workflow change requires synchronized updates to:

- owning browser tests
- browser control inventory and coverage audits where affected
- `docs/project/browser-control-qa-matrix.md`
- `docs/project/browser-control-coverage-plan.md`
- `docs/project/browser-full-e2e-qa-plan.md`
- user-facing Performance docs where behavior changed

## Test requirements

At minimum, Performance reset work must be backed by:

- static UI contract coverage for shared-shell Performance markup and ids
- route/backend coverage for list/filter/open/analytics/backup/export/tag/note behavior
- interaction/e2e coverage for record browsing, lower-pane detail truth, and reopen flows
- doc-audit and inventory coverage where Performance controls changed

## Definition of specification success

The Performance spec is satisfied only when UI behavior, shared-shell layout, library/backend truth, tests, docs, and exported artifacts all describe the same Performance product model.
