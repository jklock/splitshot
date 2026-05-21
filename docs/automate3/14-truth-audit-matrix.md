# Truth Audit Matrix

This matrix starts from audited current state. It is intentionally not a completion claim.

| Claim | Current Repo Truth | Gap | Status |
|---|---|---|---|
| Landing Page exists | Exists, but needs professional polish and proof | Visual/product quality gap | Open |
| Stage Video Edit exists | Existing editor foundation exists | Needs simplification, grouping, output/multi-angle integration | Open |
| Match Video Edit exists | Surface/panel exists | Needs first-class view and full workflows | Open |
| Performance Library exists | Surface/panel exists | Needs first-class analytics/history view | Open |
| Four views are separate frontends | No | Current UI is one cockpit plus conditional panels | Open |
| Automation strip is final structure | Present | Must be retired as permanent global layer | Open |
| Stage/Match/Library navigation is integrated | Partial | Needs clean attach/open/return/reopen flows | Open |
| `/api/state` summary strategy | `browser_state()` exists in `src/splitshot/browser/state.py`; Automate3 `active_view` is not yet established as backend state | Decide frontend-only vs backend state and test summary payload | Open |
| workspace routes | `ProjectController` has workspace lifecycle/default/override methods and `server.py` wires routes | Final Match payload/error/return UX still needs tests | Partial |
| apply-from-first routes | Routes exist, but current behavior is metadata-oriented | Does not copy/diff concrete Stage 1 project settings | Open backend gap |
| stage clip routes | Clip list/add/update/remove routes appear wired | Persistence and final composite payload must be re-verified | Partial |
| angle director routes | Controller methods exist and routes are wired | Plan schema keys are not documented for UI | Open contract gap |
| output profile routes | List/create/update/delete/render methods exist | Render-plan schema under-specified; proxy refresh empty output id needs investigation | Open contract gap |
| library routes | Library helpers and routes exist; fresh install JSONL files may be empty | Loaded Library proof needs seeded records and persistence tests | Partial |
| backup routes | Backup create/restore routes exist | Create returns manifest and restore returns counts; they do not persist/restore library store | Open backend gap |
| landing recent route | Route exists | Returns stage project directories only, not Match/Library records | Open backend gap |
| empty screenshots | Screenshot paths are required future artifacts and are not guaranteed in repo proof | Phase 0 must generate final empty proof | Open |
| loaded screenshots | Missing for final UI | Must capture loaded sample media/project | Open |
| browser E2E proof | Existing tests partial | Must cover final workflows | Open |
| canonical grouped runner | Not run for Automate3 | Required before completion | Open |

## Summary

Current Automate3 status: planned, not implemented.
