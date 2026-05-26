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

### Current file and module ownership map

| Owner | Current responsibilities | Allowed shared seams | Current temporary exceptions |
| --- | --- | --- | --- |
| `src/splitshot/browser/static/app.js` | surface switching, active-view coordination, shared status/loading/error banners, module composition, top-level shared event wiring, compatibility exports | may call shared shell services and delegate to app-owned modules | still retains legacy fallback implementations for some Match/Performance render and helper entry points; these are compatibility shims, not the preferred live owners |
| `src/splitshot/browser/static/lib/shell-runtime.js` | Stage/shared-shell DOM wiring, stage-side tool activation, layout controls, shared browser control plumbing | may expose shared shell helpers back to `app.js` | still centralizes a large amount of Stage-side control wiring while the compatibility surface remains broad |
| `src/splitshot/browser/static/views/match-view.js` | Match workspace rendering, stage list/detail panels, setup-once, recap, batch export, stage composite wiring, Match-local settings persistence | may receive shared shell callbacks and backend helpers from `app.js` | none beyond documented callback dependencies |
| `src/splitshot/browser/static/views/library-view.js` | Performance record browsing, lower-detail rendering, analytics, notes/tags, summary tiles, Performance-local settings persistence | may receive shared shell callbacks and backend helpers from `app.js` | none beyond documented callback dependencies |

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

### Current shared-to-app interface rules

- `app.js` may own shared-shell entry points such as landing/home transitions, global status surfaces, shared settings entry, and shared refresh kickoffs.
- `app.js` must delegate Match-specific rendering and workflow behavior to `match-view.js` first.
- `app.js` must delegate Performance-specific rendering, analytics, and metadata behavior to `library-view.js` first.
- `shell-runtime.js` remains the shared shell service for Stage-focused DOM/event binding and layout plumbing.
- App-owned modules must not mutate each other’s DOM directly; they operate within `#view-match` and `#view-library` roots respectively.

## Root orchestration requirements

- `app.js` must remain an orchestration spine, not an app-specific feature bucket.
- Root orchestration may coordinate surface switching, refresh, and shared shell concerns.
- App-specific behavior should live behind app-owned modules or documented helper seams.

### Current root-orchestration progress

- Match render entry points such as `renderWorkspaceStages`, `checkSetupOnceBanner`, and `renderStageComposite` now delegate directly to `match-view.js` first.
- Performance entry points such as `renderPerformanceLibrary`, `renderLibrarySummaryTiles`, `renderLibraryTags`, `renderPersonalBests`, `fetchLibraryAnalytics`, `renderAnalyticsCharts`, `addLibraryTag`, `removeLibraryTag`, and `saveLibraryNotes` now delegate directly to `library-view.js` first.
- Shared-shell recovery controls for stale and error library states remain owned at the shell level because they expose cross-surface status/recovery, but they route back into the Performance-owned refresh path.

## State and persistence requirements

- App-local persistence and settings must remain app-scoped.
- Reopening or reloading one app’s settings must not silently mutate another app’s state.
- Shared shell state must be limited to truly shared concerns such as active surface, global status, and shared settings entry points.

### Current persistence boundary map

- Shared shell keys:
  - `splitshot.activeSurface`
  - `splitshot.activeView`
  - `splitshot.activeTool`
  - `splitshot.hasVisited`
  - `splitshot.recentActivity`
  - `splitshot.layoutLocked`
  - `splitshot.layout.railWidth`
  - `splitshot.layout.inspectorWidth`
  - `splitshot.layout.waveformHeight`
- Match-local keys:
  - `splitshot.match.settings`
  - `splitshot.match.section`
  - `splitshot.match.railCollapsed`
  - `splitshot.match.scrollTop`
- Performance-local keys:
  - `splitshot.library.settings`
  - `splitshot.library.section`
  - `splitshot.library.railCollapsed`
- Stage/shared editor keys remain shell-runtime or Stage-owned where they are still shared editing concerns, such as waveform view state and popup filter mode.

## DOM ownership requirements

- App modules should operate within their own view roots.
- Cross-app DOM access must be avoided where possible.
- Any unavoidable cross-app DOM dependency must be documented and justified.

### Current cross-app DOM cautions

- `app.js` still queries multiple Match and Performance elements as fallback compatibility paths.
- `installLegacyGlobalCompat` in `app.js` continues to expose a broad compatibility surface for older global callers.
- These exceptions are currently tolerated only because live behavior now delegates to app-owned modules first and the remaining fallback paths are documented in `outcome.md`.

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
