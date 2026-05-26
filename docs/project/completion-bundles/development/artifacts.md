# Development Artifact Plan

## Purpose

This file tracks the implementation-facing evidence required to call Work Effort 1 / Set 1 complete.

Current normalized bundle status: `implementation advanced / proof pending`

Cross-bundle summary authority: `../MASTER_STATUS.md`

Acceptance evidence for `development/` must prove implementation truth and handoff readiness. It must not substitute for the screenshot, artifact, QA, or signoff evidence reserved for `testing/`.

## Required evidence categories

### 1. Source-mapping evidence

Capture and link proof for:

- the exact source-to-aggregate mapping for Work Effort 1
- the `development/` versus `testing/` split
- the distinction between source `predev/tests/` and aggregate `testing/`

### 2. Implementation evidence

Capture and link proof for:

- settled Stage implementation scope
- settled Match implementation scope
- settled Performance implementation scope
- Backend implementation progress through `BEK-001` through `BEK-006`
- Modularization implementation progress through `MOD-001` through `MOD-005`

### 3. Contract-document evidence

Link synchronized contract updates for:

- aggregate development docs
- source-bundle plans/specs/tasks/outcomes/artifacts when implementation status moved
- any implementation-facing user or developer docs updated to keep behavior truthful

### 4. Handoff evidence

Capture and link proof that:

- only testing-side work remains for Work Effort 2
- residual risks are listed explicitly
- no screenshot, artifact, or visual-signoff work is being claimed complete in `development/`

## Expected artifact locations

Use source-bundle ledgers and repo-relative docs rather than ad hoc scratch paths whenever possible.

- Source implementation anchors:
  - Expected path: source `outcome.md` and `artifacts.md` files under `../predev/`
  - Notes: prefer the source bundle that owns the detailed truth
- Contract docs:
  - Expected path: repo-relative docs
  - Notes: include aggregate and source bundle references where both moved
- Handoff notes:
  - Expected path: `development/outcome.md`, `development/artifacts.md`, and `../MASTER_STATUS.md`
  - Notes: list exact testing-side follow-up scope

## Artifact ledger

- Artifact: Work Effort 1 split contract
  - Path: `plan.md`, `spec.md`, `tasks.md`, `outcome.md`, `artifacts.md`, `orchestration.prompt.md`, `../MASTER_STATUS.md`, `../README.md`, `../RECOVERY_NEXT_STEPS.md`
  - Produced by: 2026-05-25 two-effort restructure pass
  - Date: `2026-05-25`
  - Notes: records the exact Set 1 implementation boundary and the distinction between source `predev/tests/` and aggregate `testing/`.

- Artifact: Settled Stage implementation baseline anchor
  - Path: `../predev/stage/tasks.md`, `../predev/stage/outcome.md`, `../predev/stage/artifacts.md`
  - Produced by: Stage source bundle
  - Date: `2026-05-25`
  - Notes: Work Effort 1 inherits the settled implementation scope from `STG-001` through `STG-006`.

- Artifact: Stage no-reopen integrity audit
  - Path: `../predev/stage/outcome.md`, `../predev/stage/artifacts.md`, `tests/browser/test_automation_ui_shell_contracts.py`, `tests/browser/test_browser_static_ui.py`, `tests/browser/test_browser_rail_layout.py`, `tests/browser/test_project_lifecycle_contracts.py`, `tests/browser/test_merge_export_contracts.py`, `tests/browser/test_timing_waveform_contracts.py`, `tests/browser/test_overlay_review_contracts.py`, `tests/browser/test_browser_remaining_controls_e2e.py`, `tests/browser/test_practiscore_session_api.py`, `tests/browser/test_practiscore_sync_controller.py`
  - Produced by: Work Effort 1 closeout audit
  - Date: `2026-05-25`
  - Notes: records `./.venv/bin/splitshot --check` (exit `0`), `./.venv/bin/python -m pytest tests/browser/test_automation_ui_shell_contracts.py tests/browser/test_browser_static_ui.py tests/browser/test_browser_rail_layout.py` (exit `0`, `44 passed`), `./.venv/bin/python -m pytest tests/browser/test_project_lifecycle_contracts.py tests/browser/test_merge_export_contracts.py` (exit `0`, `13 passed`), `./.venv/bin/python -m pytest tests/browser/test_timing_waveform_contracts.py tests/browser/test_overlay_review_contracts.py tests/browser/test_browser_remaining_controls_e2e.py` (exit `0`, `37 passed`), and `./.venv/bin/python -m pytest tests/browser/test_practiscore_session_api.py tests/browser/test_practiscore_sync_controller.py` (exit `0`, `16 passed`); no Stage reopen was required.

- Artifact: Match implementation baseline anchor
  - Path: `../predev/match/tasks.md`, `../predev/match/outcome.md`, `../predev/match/artifacts.md`
  - Produced by: Match source bundle
  - Date: `2026-05-25`
  - Notes: Work Effort 1 carries the implementation side of `MCH-001` through `MCH-006`; proof packaging remains in Work Effort 2.

- Artifact: Match no-reopen handoff audit
  - Path: `../predev/match/outcome.md`, `../predev/match/artifacts.md`, `tests/browser/test_workspace_flows.py`, `tests/browser/test_browser_interactions.py`, `tests/browser/test_automation_ui_shell_contracts.py`, `tests/browser/test_browser_static_ui.py`, `tests/browser/test_browser_rail_layout.py`
  - Produced by: Work Effort 1 closeout audit
  - Date: `2026-05-25`
  - Notes: records `./.venv/bin/python -m pytest tests/browser/test_workspace_flows.py -k "open_project_inside_saved_workspace_auto_attaches_stage_membership or save_project_without_saved_workspace_auto_creates_unsaved_match_membership"` (exit `0`, `2 passed`), `./.venv/bin/python -m pytest tests/browser/test_browser_interactions.py::test_match_workspace_stage_open_and_shell_return_restore_match_context` (exit `0`, `1 passed`), `./.venv/bin/python -m pytest tests/browser/test_browser_interactions.py::test_match_workspace_open_button_uses_picker_and_loads_saved_workspace tests/browser/test_browser_interactions.py::test_match_workspace_save_button_uses_picker_for_first_save` (exit `0`, `2 passed`), `./.venv/bin/python -m pytest tests/browser/test_automation_ui_shell_contracts.py tests/browser/test_browser_static_ui.py tests/browser/test_browser_rail_layout.py` (exit `0`, `44 passed`), and `./.venv/bin/python -m pytest tests/browser/test_browser_interactions.py::test_match_workspace_setup_once_uses_preview_before_apply tests/browser/test_browser_interactions.py::test_match_workspace_shared_defaults_apply_and_reset tests/browser/test_browser_interactions.py::test_match_workspace_override_apply_and_reset_update_selected_stage tests/browser/test_browser_interactions.py::test_match_workspace_shell_keeps_selected_stage_detail_and_workflow_visible` (exit `0`, `4 passed`); no Match implementation reopen was required.

- Artifact: Performance implementation baseline anchor
  - Path: `../predev/performance/tasks.md`, `../predev/performance/outcome.md`, `../predev/performance/artifacts.md`
  - Produced by: Performance source bundle
  - Date: `2026-05-25`
  - Notes: Work Effort 1 carries the implementation side of `PRF-001` through `PRF-005`; proof packaging remains in Work Effort 2.

- Artifact: Performance no-reopen handoff audit
  - Path: `../predev/performance/outcome.md`, `../predev/performance/artifacts.md`
  - Produced by: Work Effort 1 source-ledger reconciliation
  - Date: `2026-05-25`
  - Notes: the current source anchors remain sufficient for Work Effort 1 closeout — `50 passed in 232.11s (0:03:52)`, `18 passed`, and `13 passed in 174.04s (0:02:54)` — and no Performance implementation reopen was required after the stale/error recovery fix; backup/export proof packaging remains reserved for `testing/`.

- Artifact: Backend implementation scope anchor
  - Path: `../predev/backend/tasks.md`, `../predev/backend/spec.md`, `../predev/backend/outcome.md`, `../predev/backend/artifacts.md`
  - Produced by: Backend source bundle
  - Date: `2026-05-25`
  - Notes: `BEK-001` through `BEK-006` are now materially executed and recorded as Work Effort 1 implementation scope.

- Artifact: Modularization implementation scope anchor
  - Path: `../predev/modularization/tasks.md`, `../predev/modularization/spec.md`, `../predev/modularization/outcome.md`, `../predev/modularization/artifacts.md`
  - Produced by: Modularization source bundle
  - Date: `2026-05-25`
  - Notes: `MOD-001` through `MOD-005` are now materially executed and recorded as Work Effort 1 implementation scope.

- Artifact: Backend targeted validation anchor
  - Path: `../predev/backend/artifacts.md`
  - Produced by: Work Effort 1 backend implementation pass
  - Date: `2026-05-25`
  - Notes: records the `134 passed`, `18 passed`, `2 passed`, `22 passed`, and `50 passed` targeted backend/persistence/PractiScore/library validation anchors used to close `BEK-001` through `BEK-006`.

- Artifact: Modularization targeted validation anchor
  - Path: `../predev/modularization/artifacts.md`
  - Produced by: Work Effort 1 modularization implementation pass
  - Date: `2026-05-25`
  - Notes: records the `50 passed`, `13 passed`, and `8 passed` shell/static/settings/control-inventory validation anchors used to close `MOD-001` through `MOD-005`.

- Artifact: Performance recovery follow-up anchor
  - Path: `../predev/performance/tasks.md`, `../predev/performance/outcome.md`, `../predev/performance/artifacts.md`
  - Produced by: Work Effort 1 follow-up implementation fix
  - Date: `2026-05-25`
  - Notes: records the resolved Performance library stale/error recovery blocker and the updated validation anchors for the visible `Update Library` / `Retry` controls.

- Artifact: Aggregate handoff sync
  - Path: `outcome.md`, `artifacts.md`, `../MASTER_STATUS.md`
  - Produced by: Work Effort 1 ledger sync
  - Date: `2026-05-25`
  - Notes: publishes that only testing-owned proof/signoff work remains after the current implementation pass and that the aggregate execution overlay is synchronized with the touched source bundles.

## Completion rule

Development remains `implementation advanced / proof pending` until Work Effort 2 closes the testing-owned proof/signoff work, but Work Effort 1 handoff is now ready because the mapped implementation tasks are complete or explicitly deferred and only testing-side work remains.
