# Progress

This is the live execution ledger for Automate3 UI.

## Current Phase

Phase: Core implementation done (~80%). Remaining work: visual proof (screenshots, DOM assertions, PiP/perf audits), backend gap fixes (6 items), and final readiness gate. Last updated 2026-05-22.

## Required Phase 0 Evidence

- Screenshots not yet captured. Deferred until visual review workflow is established.
- Treat any existing local artifacts as stale until Phase 0 refreshes them for the active branch.

## Completed

- [x] Automate3 documentation package created
- [x] Automate3 UI documentation package created
- [x] Current visual failure captured as planning assessment
- [x] Phase 0: Baseline tests verified — all 10 sacred test suites pass (183 tests); 316 browser tests pass; 565/566 canonical runner pass (1 pre-existing tesseract env gap)
- [x] Fix dual `active` view class bug (`#view-landing` and `#view-stage`)
- [x] Landing page copy: "Recent Activity" → "Recent Stages", updated empty hint
- [x] Hide obsolete `.surface-header` (replaced by `.shell-header`)
- [x] Add `--warning` and `--info` CSS custom properties to theme.css
- [x] Phase 1: Shell and view architecture — `#app-shell` > `.shell-header` + `#view-root` with `#view-landing`, `#view-stage`, `#view-match`, `#view-library`
- [x] View state machine (`setActiveView`, `getActiveView`, `updateShellContext`) with localStorage persistence
- [x] Shell header navigation wired through `setActiveSurface` → `setActiveView`
- [x] Tool rail hidden in Match, Library, and Landing views via `data-active-view` CSS
- [x] Phase 2: Landing Page card navigation wired (`.landing-card` clicks → `setActiveSurface`)
- [x] Phase 4/5: Match view `.match-workspace` wrapper, Library view `.library-workspace` wrapper
- [x] Match and Library empty states added
- [x] Full CSS class system for Match views (`.match-*`) and Library views (`.library-*`) in layout.css
- [x] Utility CSS classes: `.btn-primary`, `.btn-ghost`, `.btn-danger`, `.badge`, `.loading-spinner`, `.skeleton`, `.error-banner`, `:focus-visible`, reduced-motion `@media`
- [x] Phase 4: Match JS rendering — `renderWorkspaceStages()` renders stage grid cards with `.match-stage-card` classes
- [x] Phase 5: Library JS rendering — `renderPerformanceLibrary()` renders records with `.library-record-row` classes
- [x] Phase 6: PiP sync — bounded rate correction (±0.12), hard seek threshold (0.65s), RAF-driven, drag suppression
- [x] Phase 7: Export wiring for Match and Library views, batch export select all/none
- [x] Phase 8-9: Integration polish — responsive breakpoints (900px, 600px), reduced-motion, focus-visible
- [x] Global error banner (`showGlobalError`) with dismiss/retry
- [x] Keyboard shortcuts: Ctrl+1/2/3 for Stage/Match/Library view switching
- [x] Cross-view state preservation (scroll position, etc.) via localStorage
- [x] Second-pass audit applied — all 12 gaps from `16-second-pass-audit.md` resolved in planning docs
- [x] All 317 browser tests pass

## Pending

- [ ] Screenshots: empty and loaded for all four views (Landing, Stage, Match, Library)
- [ ] Stage dual/tri waveform proof after adding second and third videos
- [ ] Marker image add/browse/render proof in live Stage workflow
- [ ] PiP performance audit
- [ ] DOM/layout assertions for all captured views
- [ ] Final contact sheet creation with surface, state, viewport, and scenario labels
- [ ] Update proof matrix (`artifacts/ui-proof-matrix.md`) and readiness gate
- [ ] Backend gap fixes (6 items in `docs/automate3/17-backend-gap-implementation-plan.md`):
  - [ ] `/api/workspace/apply-from-first` — copy concrete settings
  - [ ] `/api/workspace/apply-from-first/preview` — concrete diff
  - [ ] `/api/library/backup/create` — persist to disk
  - [ ] `/api/library/backup/restore` — write to library store
  - [ ] `/api/landing/recent` — include Match/Library records
  - [ ] `proxy_refresh` — fix empty output ID
- [ ] Canonical grouped runner for final verification
- [ ] Visual review sign-off (requires vision-capable or human reviewer)

## Blockers

- Screenshots require browser launch and visual review (no vision capability in current agent)
- Backend route gaps (apply-from-first, library backup/restore, landing recent) documented but not yet implemented
- Visual review may identify layout/design issues not detectable by automated tests

## Risks

- Backend route gaps (apply-from-first, library backup/restore) remain as documented open items
- Visual design contract is reconciled with existing theme.css, but visual review still needed
- Current `docs/screenshots/automate3/loaded-stage.png` does not prove a loaded Stage view.
