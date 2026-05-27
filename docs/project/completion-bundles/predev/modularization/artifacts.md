# Modularization Artifact Plan

## Purpose

This file tracks the proof package required to call browser modularization complete.

Current normalized lane status: `implementation advanced / proof pending`

Cross-lane summary authority: `../../MASTER_STATUS.md`

Work Effort 1 now owns accepted implementation evidence for `MOD-001` through `MOD-005`. Work Effort 2 still owns final proof coverage, residual-risk closeout, and approval for `MOD-006` and `MOD-007`.

Development `DEV-107` later added accepted compat-seam cleanup evidence: root-shell globals now route through `installLegacyGlobalCompat(...)`, duplicate tail-end `window.*` exposure was trimmed, and the owned shell/static/interaction/workspace guardrail pack reran green. Those artifacts strengthen the recorded implementation evidence but do not change the normalized lane status or promote the lane to exhaustive legacy-consumer proof.

## Required evidence categories

### 1. Source-level evidence

Capture and link proof for:

- current-to-target ownership inventory
- module interface boundaries
- reduced root orchestration scope
- documented cross-app dependencies that remain

### 2. Test evidence

Record exact test outputs for modularization coverage:

- source-level ownership or contract tests
- app-owned interaction/e2e tests affected by wiring changes
- any doc-audit tests affected by ownership changes

### 3. App-isolation evidence

Capture and link proof that:

- Stage settings and local state remain Stage-local
- Match settings and local state remain Match-local
- Performance settings and local state remain Performance-local
- shared shell state is limited to shared concerns

### 4. Documentation evidence

Link all synchronized doc updates for:

- architecture docs
- app bundle docs that describe ownership boundaries
- any test-guide references affected by modularization

## Expected artifact locations

Use repo artifact locations rather than temporary scratch paths whenever possible.

- Test run summary:
  - Expected path: `artifacts/test-run.json` or suite-specific output
  - Notes: prefer canonical runner output when used
- Ownership notes:
  - Expected path: repo-relative docs or artifact files
  - Notes: include module names and boundary decisions
- Wiring / app-isolation proof:
  - Expected path: `artifacts/` or documented proof path
  - Notes: record the specific scenario exercised
- Doc diffs / references:
  - Expected path: repo-relative paths
  - Notes: include PR or commit reference when available

## Artifact ledger

- Artifact: Ownership and interface inventory
  - Path: `spec.md`, `tasks.md`, `outcome.md`, `artifacts.md`
  - Produced by: Work Effort 1 modularization implementation pass
  - Date: `2026-05-25`
  - Notes: records the current ownership map for `app.js`, `shell-runtime.js`, `match-view.js`, and `library-view.js`, plus persistence boundaries and temporary exceptions.

- Artifact: Match/Performance delegation cleanup
  - Path: `src/splitshot/browser/static/app.js`, `src/splitshot/browser/static/views/match-view.js`, `src/splitshot/browser/static/views/library-view.js`
  - Produced by: Work Effort 1 modularization implementation pass
  - Date: `2026-05-25`
  - Notes: active Match and Performance render/helper entry points now delegate through the app-owned modules first; remaining fallback blocks stay documented as compatibility shims.

- Artifact: Development DEV-107 root-shell compat cleanup validation
  - Path: `src/splitshot/browser/static/app.js`, `src/splitshot/browser/static/lib/global-compat.js`, `tests/browser/test_automation_ui_shell_contracts.py`, `tests/browser/test_browser_static_ui.py`, `tests/browser/test_browser_interactions.py::test_shell_compat_host_on_open_project_callback_opens_saved_project`, `tests/browser/test_browser_interactions.py::test_performance_library_compat_selected_record_and_render_rerender_detail_truth`, `tests/browser/test_workspace_flows.py`, `docs/project/browser-proof-seams.json`, `tests/browser/test_browser_control_coverage_matrix.py`, `tests/browser/test_browser_control_inventory_audit.py`
  - Produced by: targeted `.venv` pytest run plus focused `ruff` during DEV-107 close
  - Date: `2026-05-26`
  - Notes: duplicate tail-end `window.*` exposure was trimmed, `setActiveSurface` and `renderAutomationSurface` now ride the compat value surface, and `selectedLibraryRecord` remains compat-bound; the reopened close added explicit proof for the retained host open-project callback and the direct Performance Library compat-consumer path, wired those claims into the seam-registry audits, and finished with a green `691 passed` all-together anchor. This is stronger compat-consumer evidence for Work Effort 1, but it still is not exhaustive proof of every legacy global consumer path.

- Artifact: Shell/static/settings/control inventory validation pack
  - Path: `tests/browser/test_automation_ui_shell_contracts.py`, `tests/browser/test_browser_static_ui.py`, `tests/browser/test_browser_rail_layout.py`, `tests/browser/test_browser_interactions.py::test_match_settings_persist_locally_and_control_match_return_selection`, `tests/browser/test_browser_interactions.py::test_performance_library_settings_persist_and_manual_refresh_loads_records`, `tests/browser/test_browser_interactions.py::test_performance_library_settings_remain_isolated_from_match_settings`, `tests/browser/test_browser_interactions.py::test_performance_library_shows_loading_and_recovers_from_route_failure`, `tests/browser/test_browser_control_inventory_audit.py`
  - Produced by: targeted `.venv` pytest run
  - Date: `2026-05-25`
  - Notes: `50 passed in 232.11s (0:03:52)`; anchors shared-shell ownership, control inventory, layout, app-local settings isolation, and the visible stale/error recovery controls.

- Artifact: Focused Performance/PractiScore interaction slice
  - Path: `tests/browser/test_browser_interactions.py -k "performance_library or practiscore"`
  - Produced by: targeted `.venv` pytest run
  - Date: `2026-05-25`
  - Notes: `13 passed in 174.04s (0:02:54)`; anchors Performance-owned interactions that were most sensitive to the modularization and recovery-control changes.

- Artifact: Control inventory and shell contract audit slice
  - Path: `tests/browser/test_browser_control_inventory_audit.py`, `tests/browser/test_automation_ui_shell_contracts.py`
  - Produced by: targeted `.venv` pytest run
  - Date: `2026-05-25`
  - Notes: `8 passed in 2.27s`; anchors the explicit browser control inventory and the shared-shell contract documentation.

- Artifact: Cross-bundle handoff references
  - Path: `../../development/outcome.md`, `../../development/artifacts.md`, `../backend/outcome.md`, `../performance/outcome.md`, `../../MASTER_STATUS.md`
  - Produced by: Work Effort 1 ledger sync
  - Date: `2026-05-25`
  - Notes: keeps the modularization handoff aligned across aggregate and source bundles without claiming testing-owned final proof/signoff.

## Completion rule

Modularization is not `done` until `MOD-006` and `MOD-007` close the final proof package and approval. Work Effort 1 now records accepted implementation evidence for `MOD-001` through `MOD-005`; Work Effort 2 must still finish the remaining proof/signoff ledger.
