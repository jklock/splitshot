# Todo

## Phase 0: Audit And Baseline

- [x] Inspect current browser UI files.
- [x] Verify current backend routes and payloads.
- [x] Baseline tests verified — all 10 sacred test suites pass (183 tests); 316 browser tests pass; 565/566 canonical runner pass.
- [ ] Capture or confirm current screenshot audit artifacts. (Deferred: requires visual review workflow.)
- [ ] Update gap matrix with current evidence. (Partially done — see `14-truth-audit-matrix.md`.)

## Phase 1: Shell And View Architecture

- [x] Add explicit view controller with `setActiveView`, `getActiveView`, `updateShellContext`.
- [x] Split Landing, Stage, Match, and Library view bodies (`#view-root` > `#view-landing`, `#view-stage`, `#view-match`, `#view-library`).
- [x] Preserve shared shell/context (`#app-shell` > `.shell-header` + `#view-root`).
- [x] Remove permanent global automation strip (`.surface-header` hidden; replaced by `.shell-header`).
- [x] Keep Stage panes inside Stage view (tool rail hidden in Match, Library, Landing via `data-active-view` CSS).
- [x] Shell header navigation wired through `setActiveSurface` → `setActiveView`.

## Phase 2: Landing Page

- [x] Build returning-user state (card navigation wired, `.landing-card` clicks → `setActiveSurface`).
- [x] Wire recent activity ("Recent Stages" title, `/api/landing/recent`).
- [x] Wire quick starts (New Stage, New Match, Open File cards).
- [ ] Capture empty/returning screenshots.

## Phase 3: Stage Video Edit

- [x] Preserve existing panes (tool panes mount inside `#view-stage`).
- [ ] Simplify/group tool navigation. (Pending polish.)
- [ ] Integrate output profile manager.
- [ ] Integrate retained review source and render plan.
- [ ] Add workspace-stage context.
- [ ] Add create/attach Match flow.
- [ ] Capture empty/loaded screenshots.

## Phase 4: PiP, Waveform, Multi-Angle

- [x] Implement bounded sync strategy (rate correction ±0.12, hard seek threshold 0.65s, RAF-driven, drag suppression).
- [x] Stop drag/playback route churn.
- [ ] Add multi-track waveform. (Single-track done; dual/tri proof needed.)
- [ ] Add segments and auto-cuts.
- [ ] Add camera jobs/audio/smart-cut controls.
- [ ] Complete performance proof. (PiP performance audit pending.)

## Phase 5: Match Video Edit

- [x] Build match header (in `.match-workspace`).
- [x] Build stage grid (`renderWorkspaceStages()` with `.match-stage-card` classes).
- [x] Wire workspace lifecycle.
- [x] Match empty state added.
- [x] Full CSS class system for Match views (`.match-*` in layout.css).
- [ ] Wire defaults and overrides.
- [ ] Implement Setup Once Apply Everywhere. (Blocked on backend gap.)
- [ ] Implement recap/composite/batch export.
- [ ] Capture empty/loaded screenshots.

## Phase 6: Performance Library

- [x] Build dashboard/table/detail structure (`renderPerformanceLibrary()` with `.library-record-row`).
- [x] Library empty state added.
- [x] Full CSS class system for Library views (`.library-*` in layout.css).
- [ ] Build filters/table/detail.
- [ ] Wire proxy/archive actions.
- [ ] Wire analytics/comparison.
- [ ] Wire tags/notes/export.
- [ ] Wire reopen actions.
- [ ] Capture empty/loaded screenshots.

## Phase 7: Integration, Proof, Release

- [x] All 317 browser tests pass.
- [x] Global error banner (`showGlobalError`) with dismiss/retry.
- [x] Keyboard shortcuts: Ctrl+1/2/3 for Stage/Match/Library view switching.
- [x] Cross-view state preservation (scroll position, etc.) via localStorage.
- [x] Responsive breakpoints (900px, 600px), reduced-motion, focus-visible.
- [x] Utility CSS classes: `.btn-primary`, `.btn-ghost`, `.btn-danger`, `.badge`, `.loading-spinner`, `.skeleton`, `.error-banner`.
- [ ] Run canonical grouped runner.
- [ ] Capture final contact sheet.
- [ ] Update proof matrix and readiness gate.

## Backend Gaps (from `docs/automate3/17-backend-gap-implementation-plan.md`)

- [ ] Gap 1: `/api/workspace/apply-from-first` — copy concrete settings from Stage 1 to siblings.
- [ ] Gap 2: `/api/workspace/apply-from-first/preview` — concrete diff with conflicts.
- [ ] Gap 3: `/api/library/backup/create` — persist to disk.
- [ ] Gap 4: `/api/library/backup/restore` — write to library store.
- [ ] Gap 5: `/api/landing/recent` — include Match/Library records.
- [ ] Gap 6: `proxy_refresh` — fix empty output ID bug.

## Pending Visual Proof

- [ ] Screenshots: empty and loaded for all four views.
- [ ] Stage dual/tri waveform proof (add second/third videos, verify distinct tracks).
- [ ] Marker image add/browse/render proof in live Stage workflow.
- [ ] PiP performance audit.
- [ ] DOM/layout assertions for all captured views.
- [ ] Final contact sheet with surface, state, viewport, scenario labels.
- [ ] Visual review sign-off.
- [ ] Proof docs: gap matrix, proof matrix, readiness gate updated to reflect actual completion state.
