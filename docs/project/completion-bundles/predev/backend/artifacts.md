# Shared Backend Artifact Plan

## Purpose

This file tracks the proof package required to call the shared backend complete.

Current normalized lane status: `implementation advanced / proof pending`

Cross-lane summary authority: `../../MASTER_STATUS.md`

Work Effort 1 now owns accepted implementation evidence for `BEK-001` through `BEK-006`. Work Effort 2 still owns the final proof package, artifact closeout, and approval for `BEK-007` and `BEK-008`.

Development wave 1 later added corroborating `DEV-102`/`DEV-103`/`DEV-104` validation evidence plus a post-integration guardrail pack; `DEV-105` then added shared-controller integration evidence, expanded frozen guardrail results, and a repo-wide lint anchor; `DEV-106` then added accepted landing-recent backend evidence showing stage/single rows are preserved before truncation in `/api/landing/recent`. Those artifacts strengthen the recorded implementation evidence but do not change the normalized lane status or promote the lane to final proof closure.

## Required evidence categories

### 1. Test evidence

Record exact test outputs for shared backend coverage:

- route registration and contract tests
- browser state serialization tests
- persistence and reopen-flow tests
- import and PractiScore tests
- workspace backend tests used by Match
- library backend tests used by Performance

### 2. Contract evidence

Capture and link proof for:

- route ownership mapping
- `/api/state` summary payload expectations
- status and error behavior for expected failure classes
- shared persistence and truth-hash behavior

### 3. Cross-app dependency evidence

Capture and link proof that:

- Stage-facing backend contracts remain stable
- Match-facing workspace contracts remain stable
- Performance-facing library contracts remain stable

### 4. Documentation evidence

Link all synchronized doc updates for:

- architecture docs
- test guide docs
- app bundle docs that reference backend contract changes

## Expected artifact locations

Use repo artifact locations rather than temporary scratch paths whenever possible.

- Test run summary:
  - Expected path: `artifacts/test-run.json` or suite-specific output
  - Notes: prefer canonical runner output when used
- Route/state contract notes:
  - Expected path: repo-relative docs or artifact files
  - Notes: include exact route groups or state slices covered
- Persistence / reopen proof:
  - Expected path: `artifacts/` or documented output path
  - Notes: record the scenario exercised
- Doc diffs / references:
  - Expected path: repo-relative paths
  - Notes: include PR or commit reference when available

## Artifact ledger

- Artifact: Development wave 1 backend and persistence validation trio
  - Path: `src/splitshot/browser/server.py`, `tests/browser/test_landing_backend_routes.py`, `tests/browser/test_automation_ui_shell_contracts.py`; `src/splitshot/browser/state.py`, `tests/browser/test_library_backend_contracts.py`; `src/splitshot/persistence/library.py`, `src/splitshot/persistence/projects.py`, `tests/persistence`
  - Produced by: focused `ruff` and `.venv` pytest runs during development wave 1 integration
  - Date: `2026-05-26`
  - Notes: `DEV-102`, `DEV-103`, and `DEV-104` all closed green; results were `ruff` clean plus targeted pytest passes for landing-route contracts, `/api/state` library-contract coverage, and persistence helpers.

- Artifact: Development wave 1 post-integration browser guardrail pack
  - Path: `tests/browser/test_browser_static_ui.py`, `tests/browser/test_browser_interactions.py`, `tests/browser/test_workspace_flows.py`, `tests/browser/test_workspace_export_and_recap.py`, `tests/browser/test_practiscore_session_api.py`, `tests/browser/test_practiscore_sync_controller.py`
  - Produced by: targeted `.venv` pytest run after wave 1 integration
  - Date: `2026-05-26`
  - Notes: `177 passed`; confirms the integrated wave remained valid within the current allowlists after the backend/state/persistence changes landed.

- Artifact: Development DEV-105 shared-controller integration validation
  - Path: `src/splitshot/ui/controller.py`, `src/splitshot/ui/services/shared_backend.py`, `src/splitshot/ui/services/practiscore_sync.py`, `tests/browser/test_landing_backend_routes.py`, `tests/browser/test_practiscore_session_api.py`, `tests/browser/test_practiscore_sync_controller.py`, `tests/browser/test_library_backend_contracts.py`, `tests/browser/test_browser_interactions.py`, `tests/browser/test_automation_ui_shell_contracts.py`, `tests/browser/test_browser_static_ui.py`, `tests/browser/test_workspace_flows.py`, `tests/browser/test_workspace_export_and_recap.py`
  - Produced by: targeted `.venv` pytest runs plus repo-wide `ruff` during DEV-105 integration close
  - Date: `2026-05-26`
  - Notes: shared backend/practiscore controller extraction landed; results were `48 passed` for the lane-local backend/practiscore pack, `77 passed` for `tests/browser/test_browser_interactions.py`, `108 passed` for the complementary frozen guardrail group, and a clean `uvx ruff check .`.

- Artifact: Development DEV-106 landing recent backend truth hardening
  - Path: `src/splitshot/ui/services/shared_backend.py`, `tests/browser/test_landing_backend_routes.py`, `tests/browser/test_browser_static_ui.py`, `tests/browser/test_browser_interactions.py::test_landing_recent_stage_rows_switch_surface_without_auto_open`, `docs/project/browser-proof-seams.json`
  - Produced by: targeted `.venv` pytest runs plus focused `ruff` during DEV-106 close
  - Date: `2026-05-26`
  - Notes: `/api/landing/recent` now preserves stage/single rows before sort/truncate so newer match/library recents cannot crowd them out; results were `19 passed` for the landing backend-route pack, `27 passed` for the landing static contract pack, the dedicated recent-row interaction proof was added under seam ID `DEV-106.landing_recent`, and the reopened close finished with a green `691 passed` all-together anchor. This is now backend-route plus static-render-contract plus interaction evidence for Work Effort 1.

- Artifact: Route and `/api/state` ownership inventory
  - Path: `spec.md`, `tasks.md`, `outcome.md`, `artifacts.md`
  - Produced by: Work Effort 1 backend implementation pass
  - Date: `2026-05-25`
  - Notes: records the shared/Stage/Match/Performance route groups, landing/global support routes, `/api/state` summary families, and the owning test/doc anchors.

- Artifact: Backend/state/persistence/library validation pack
  - Path: `tests/browser/test_browser_control.py`, `tests/persistence/test_persistence.py`, `tests/persistence/test_workspace_persistence.py`, `tests/browser/test_library_backend_contracts.py`
  - Produced by: targeted `.venv` pytest run
  - Date: `2026-05-25`
  - Notes: `134 passed`; anchors browser state serialization, persistence truth, workspace/library backend coverage, and shared contract stability.

- Artifact: Match/Performance reopen and PractiScore browser guardrail pack
  - Path: `tests/browser/test_browser_interactions.py::test_match_workspace_stage_open_and_shell_return_restore_match_context`, `tests/browser/test_browser_interactions.py::test_performance_library_can_reopen_stage_and_workspace_from_selected_record`, `tests/browser/test_practiscore_session_api.py`, `tests/browser/test_practiscore_sync_controller.py`
  - Produced by: targeted `.venv` pytest run
  - Date: `2026-05-25`
  - Notes: `18 passed`; anchors reopen behavior, Match/Performance backend support, and browser-facing PractiScore session/sync behavior.

- Artifact: Match workspace auto-attach lifecycle pack
  - Path: `tests/browser/test_workspace_flows.py -k "open_project_inside_saved_workspace_auto_attaches_stage_membership or save_project_without_saved_workspace_auto_creates_unsaved_match_membership"`
  - Produced by: targeted `.venv` pytest run
  - Date: `2026-05-25`
  - Notes: `2 passed`; anchors deterministic workspace membership and save/open lifecycle truth.

- Artifact: PractiScore analysis import pack
  - Path: `tests/analysis/test_practiscore_import.py`, `tests/analysis/test_practiscore_sync_normalize.py`, `tests/analysis/test_practiscore_web_extract.py`
  - Produced by: targeted `.venv` pytest run
  - Date: `2026-05-25`
  - Notes: `22 passed`; anchors shared import normalization and recoverable remote-import behavior.

- Artifact: Browser-visible library recovery and shell contract pack
  - Path: `tests/browser/test_automation_ui_shell_contracts.py`, `tests/browser/test_browser_static_ui.py`, `tests/browser/test_browser_rail_layout.py`, `tests/browser/test_browser_interactions.py::test_match_settings_persist_locally_and_control_match_return_selection`, `tests/browser/test_browser_interactions.py::test_performance_library_settings_persist_and_manual_refresh_loads_records`, `tests/browser/test_browser_interactions.py::test_performance_library_settings_remain_isolated_from_match_settings`, `tests/browser/test_browser_interactions.py::test_performance_library_shows_loading_and_recovers_from_route_failure`, `tests/browser/test_browser_control_inventory_audit.py`
  - Produced by: targeted `.venv` pytest run
  - Date: `2026-05-25`
  - Notes: `50 passed in 232.11s (0:03:52)`; anchors recoverable Performance library stale/error behavior plus the static shell/control inventory contract used by the backend-owned browser summary flows.

- Artifact: Cross-bundle handoff references
  - Path: `../../development/outcome.md`, `../../development/artifacts.md`, `../performance/outcome.md`, `../modularization/outcome.md`, `../../MASTER_STATUS.md`
  - Produced by: Work Effort 1 ledger sync
  - Date: `2026-05-25`
  - Notes: keeps the backend handoff aligned across aggregate and source bundles without claiming testing-owned signoff work.

## Completion rule

The shared backend is not `done` until `BEK-007` and `BEK-008` close the final proof package and approval. Work Effort 1 now records accepted implementation evidence for `BEK-001` through `BEK-006`; Work Effort 2 must still finish the remaining proof/signoff ledger.
