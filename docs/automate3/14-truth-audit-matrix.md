# Truth Audit Matrix

Audit last refreshed: 2026-05-21. Implementation began 2026-05-21.

| Claim | Current Repo Truth | Gap | Status |
|---|---|---|---|
| Landing Page exists | Shell integration, copy updates ("Recent Stages"), card navigation wired | Screenshots needed; recent route is stage-only | ✅ Implemented (needs visual proof) |
| Stage Video Edit exists | Existing editor preserved inside `#view-stage`; panes intact; tool rail visible only in Stage | Output/multi-angle integration still needs wiring proof | ✅ Implemented (needs visual proof) |
| Match Video Edit exists | `.match-workspace` wrapper, `.match-*` CSS, `renderWorkspaceStages()`, empty state | First-class workflows need backend gaps resolved | ✅ Implemented (needs visual proof) |
| Performance Library exists | `.library-workspace` wrapper, `.library-*` CSS, `renderPerformanceLibrary()`, empty state | Loaded Library proof needs seeded records | ✅ Implemented (needs visual proof) |
| Four views are separate frontends | ✅ `#view-landing`, `#view-stage`, `#view-match`, `#view-library` under `#view-root`; `setActiveView` state machine with localStorage persistence | — | ✅ Done |
| Automation strip is final structure | `.surface-header` hidden; global automation strip retired | — | ✅ Done |
| Stage/Match/Library navigation is integrated | Shell header wired via `setActiveSurface` → `setActiveView`; keyboard shortcuts Ctrl+1/2/3; cross-view state retention | Return-to-Match affordance needs testing | ✅ Done |
| `/api/state` summary strategy | `activeView` frontend state machine implemented; not yet in backend `browser_state()` | Backend state integration not required for current functionality | ✅ Done (frontend) |
| workspace routes | `ProjectController` has workspace lifecycle/default/override methods and `server.py` wires routes; Match view renders workspace stages | Final Match payload/error/return UX still needs tests | Partial |
| apply-from-first routes | Routes exist, but current behavior is metadata-oriented | Does not copy/diff concrete Stage 1 project settings | Open backend gap |
| stage clip routes | Clip list/add/update/remove routes appear wired | Persistence and final composite payload must be re-verified | Partial |
| angle director routes | Controller methods exist and routes are wired | Plan schema keys are not documented for UI | Open contract gap |
| output profile routes | List/create/update/delete/render methods exist | Render-plan schema under-specified; proxy refresh empty output id needs investigation | Open contract gap |
| library routes | Library helpers and routes exist; fresh install JSONL files may be empty | Loaded Library proof needs seeded records and persistence tests | Partial |
| backup routes | Backup create/restore routes exist | Create returns manifest and restore returns counts; they do not persist/restore library store | Open backend gap |
| landing recent route | Route exists | Returns stage project directories only, not Match/Library records | Open backend gap |
| PiP sync | Bounded rate correction (±0.12), hard seek threshold (0.65s), RAF-driven, drag suppression | Performance audit not yet captured | ✅ Implemented (needs perf proof) |
| Waveform | Single-track foundation in Stage editor | Dual/tri-track proof with second and third videos needed | Partial (needs multi-track proof) |
| Export wiring | Match/Library export wired; batch export select all/none | Stage export, recap, composite workflows need backend gap fixes | ✅ UI wired |
| Utility CSS | `.btn-primary`, `.btn-ghost`, `.btn-danger`, `.badge`, `.loading-spinner`, `.skeleton`, `.error-banner`, `:focus-visible`, reduced-motion `@media` | — | ✅ Done |
| Integration polish | Responsive breakpoints (900px, 600px), reduced-motion, focus-visible; global error banner with dismiss/retry | — | ✅ Done |
| empty screenshots | Not yet captured for final UI | Requires browser launch and visual review | Open |
| loaded screenshots | Not yet captured for final UI | Must capture loaded sample media/project | Open |
| browser E2E proof | 317 browser tests pass | Must verify view-specific workflows covered | ✅ Passing |
| canonical grouped runner | Not run for Automate3 | Required before completion | Open |

## Known Backend Gaps (from `17-backend-gap-implementation-plan.md`)

These 6 backend gaps block complete UI wiring:

1. `/api/workspace/apply-from-first` — metadata only, does not copy settings
2. `/api/workspace/apply-from-first/preview` — no concrete diff
3. `/api/library/backup/create` — in-memory only, no disk persistence
4. `/api/library/backup/restore` — doesn't write to store
5. `/api/landing/recent` — stage-only, no Match/Library records
6. `proxy_refresh` — empty output ID bug

## Remaining Work

- Screenshots: empty and loaded for all four views
- Stage dual/tri waveform proof
- Marker image add/browse/render proof
- PiP performance audit
- DOM/layout assertions
- Final contact sheet
- Visual review sign-off
- Canonical grouped runner
- Backend gap fixes (6 items in `17-backend-gap-implementation-plan.md`)

## Summary

Automate3 UI: ~80% implemented (shell/view architecture, CSS, JS rendering, PiP sync, export wiring, integration polish done). Remaining: screenshots, waveform/performance proof, backend gaps, visual review.
