# Performance Task Backlog

## Usage

- Treat each item as incomplete until its proof exists.
- Link implementation work, test evidence, screenshots, and exported artifacts in `outcome.md` and `artifacts.md`.
- Performance is not done until shared-shell behavior, real data, real persistence, and real docs all agree.

## PRF-001 — Reset the Performance contract

- [x] Rewrite the Performance bundle docs around Stage-shell reuse.
- [x] Replace the standalone Performance-app framing with the graph/info workflow contract.
- [x] Record the internal `library` naming seam and current user-facing Performance naming requirement.
- [x] Mark prior signoff evidence as historical rather than current approval.

Progress note (`2026-05-24`):

- `plan.md`, `spec.md`, `tasks.md`, `outcome.md`, `artifacts.md`, and both Performance prompts now describe Performance as a Stage-shell variant.
- The bundle no longer treats a separate Performance shell family as a requirement.

Depends on:

- none

Proof:

- Performance bundle files updated

## PRF-002 — Reuse the Stage shell grammar

- [x] Move Performance onto the same shell family as Stage.
- [x] Place summary tiles and record data in the main area.
- [x] Use the lower pane for selected-record information everywhere the spec expects it.
- [x] Keep filters, actions, and settings fully right-inspector centric.

Progress note (`2026-05-24`):

- Performance/library root markup now advertises the shared `stage-workspace` shell family.
- Summary tiles, record lists, analytics, lower selected-record detail, and right-inspector filters/actions/settings are now implemented in the shared shell.
- Proof, screenshots, and final interaction packaging for that grammar are still pending before the checklist can close.

Proof closeout note (`2026-05-26`):

- The focused shell/detail proof slice stayed green with `3 passed` across the loading/recovery, reopen, and lower-detail truth interactions.
- `docs/screenshots/automate3/loaded-library.png` plus the new section captures (`performance-analytics.png`, `performance-backup.png`, and `performance-settings.png`) now record the lower-pane detail and right-inspector grammar under the loaded Performance shell.

Depends on:

- PRF-001

Proof:

- `src/splitshot/browser/static/index.html`
- `src/splitshot/browser/static/views/library-view.js`
- `tests/browser/test_automation_ui_shell_contracts.py`
- `tests/browser/test_browser_static_ui.py`

## PRF-003 — Rebuild the record and detail workflow in the new shell

- [x] Prove loading, refresh, stale, and empty-state behavior.
- [x] Fully prove search, sort, and filter behavior.
- [x] Fully prove selected-record detail truth in the lower-pane grammar expected by the spec.
- [x] Prove stage/workspace reopen behavior from the current layout.

Progress note (`2026-05-24`):

- Loading/error recovery, manual refresh, stale state, and reopen behavior are covered.
- Search now filters the visible record list in the new shell, and the selected-record payload remains pinned in the lower pane.
- The open items are proof depth and artifact packaging for search/filter coverage and the lower-pane/detail contract.

Progress note (`2026-05-25`):

- The Performance shell now keeps recovery visible when no records are loaded: stale state exposes a banner-level `Update Library` action and error state exposes a banner-level `Retry` action.
- This closes the implementation blocker where manual recovery controls were hidden inside the unloaded Records inspector.

Proof closeout note (`2026-05-26`):

- `tests/browser/test_browser_interactions.py::test_performance_library_search_filters_records_and_keeps_lower_detail_truth` now closes the focused search/filter/detail truth gap alongside the existing loading/reopen proofs.
- The refreshed loaded-library screenshot keeps the selected record visible in the lower pane while the active Performance inspector section changes, closing the remaining record/detail grammar proof for this lane.

Depends on:

- PRF-001
- PRF-002

Proof:

- `tests/browser/test_browser_interactions.py::test_performance_library_shows_loading_and_recovers_from_route_failure`
- `tests/browser/test_browser_interactions.py::test_performance_library_settings_persist_and_manual_refresh_loads_records`
- `tests/browser/test_browser_interactions.py::test_performance_library_can_reopen_stage_and_workspace_from_selected_record`

## PRF-004 — Preserve analytics, notes/tags, backup, and export truth

- [x] Prove note and tag persistence truth through backend routes and the new shell.
- [x] Prove overview summary tiles and personal-best analytics truth.
- [x] Prove backup create/restore behavior.
- [x] Prove CSV/JSON export behavior and capture updated output artifacts.

Progress note (`2026-05-24`):

- Notes/tags persistence and summary-tile / personal-best analytics truth are covered.
- Backup create/restore and export artifact proof remain open.

Proof closeout note (`2026-05-26`):

- The focused notes/analytics/settings slice stayed green with `4 passed`, and the backend/export pack stayed green with `72 passed` across `tests/browser/test_library_backend_contracts.py`, `tests/export/test_export.py`, and `tests/export/test_merge_export_contracts.py`.
- `artifacts/performance-proof-20260526/` now records concrete CSV/JSON export outputs, the backup manifest and copied backup file, and the backup create/restore result payloads for the current shell contract.

Depends on:

- PRF-002
- PRF-003

Proof:

- `tests/browser/test_browser_interactions.py::test_performance_library_detail_ui_persists_tag_add_remove_and_notes`
- `tests/browser/test_browser_interactions.py::test_performance_library_summary_tiles_and_personal_bests_follow_loaded_records`

## PRF-005 — Isolate Performance settings and shared-shell stability

- [x] Prove Performance settings save and reload behavior.
- [x] Prove auto-refresh toggle behavior.
- [x] Prove settings affect Performance only.
- [x] Keep naming truthful even if the internal `library` storage key remains.

Progress note (`2026-05-24`):

- Performance settings persistence, auto-refresh, and isolation from Match are directly covered.
- The user-facing Performance naming seam remains documented while the internal storage key stays `library`.

Progress note (`2026-05-25`):

- Auto-refresh-disabled recovery now remains accessible from the stale banner instead of depending on a hidden Records inspector control.
- Performance error recovery now mirrors that behavior with a visible retry control in the library error banner.

Depends on:

- PRF-001
- PRF-002

Proof:

- `tests/browser/test_browser_interactions.py::test_performance_library_settings_persist_and_manual_refresh_loads_records`
- `tests/browser/test_browser_interactions.py::test_performance_library_settings_remain_isolated_from_match_settings`
- `docs/userfacing/panes/performance.md`

## PRF-006 — Sync docs and proof package

- [x] Update QA matrix, coverage plan, and full browser E2E plan for Performance-owned controls and workflows.
- [x] Update user-facing Performance docs.
- [x] Capture Overview, Records, Detail, Analytics, Backup, and Settings screenshots for the new shell.
- [x] Finish the remaining proof-package notes / deferrals.

Progress note (`2026-05-24`):

- QA/control docs, the coverage planning docs, and the user-facing Performance guide are aligned with the shared shell.
- Screenshot packaging and the remaining proof/deferral notes are still open.

Proof closeout note (`2026-05-26`):

- `scripts/docs/capture_loaded_views.py` refreshed the repo-owned loaded Performance screenshot set, including `loaded-library.png` and `loaded-proof-results.json`.
- The section capture rerun added `performance-analytics.png`, `performance-backup.png`, `performance-settings.png`, and `performance-section-proof-results.json`, closing the remaining Performance screenshot package.

Depends on:

- PRF-003
- PRF-004
- PRF-005

Proof:

- `docs/project/browser-control-qa-matrix.md`
- `docs/project/browser-control-coverage-plan.md`
- `docs/project/browser-full-e2e-qa-plan.md`
- `docs/userfacing/panes/performance.md`
- `tests/browser/test_browser_control_coverage_matrix.py`

## PRF-007 — Performance done gate

- [x] Confirm Performance-owned tests are green for the new contract.
- [x] Confirm shared-shell/backend dependencies used by Performance are green.
- [x] Confirm reopen, analytics, backup, and export proof artifacts exist for the new shell.
- [x] Confirm visual approval is recorded.
- [x] Confirm user-facing naming and doc truth are aligned.

Depends on:

- PRF-006

Proof:

- `outcome.md` final gate marked complete

Progress note (`2026-05-26`):

- The Performance gate now closes on the green `3 passed`, `4 passed`, and `72 passed` reruns, the refreshed loaded-library shell screenshot, the new analytics/backup/settings section screenshots, the repo-owned backup/export artifacts under `artifacts/performance-proof-20260526/`, and recorded visual approval against those refreshed captures.
