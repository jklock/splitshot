# Development Task Backlog

## Usage

- This bundle tracks Work Effort 1 / Set 1 only.
- The source bundles under `../predev/` remain the detailed truth; this file is the execution overlay for subagents.
- Treat each atomic slice as incomplete until code, narrow validation, source ledgers, and aggregate ledgers all agree.
- Do not count screenshots, proof packaging, artifact ledgers, final suite closure, or visual approval as development completion here.

## Subagent execution contract

- Assign one owner per atomic slice unless this file explicitly marks a safe parallel bundle.
- Read the named source docs before touching code.
- Keep changes inside the listed edit surface unless a directly imported helper seam forces a documented expansion.
- Run commands from the repo root in this order: bootstrap only if needed, runtime health, targeted validation, broader suite validation only if the slice requires it, then ledger sync.
- Update the touched source bundle and the aggregate `development/` ledgers in the same change.
- If a first-order implementation blocker is discovered inside a proof-owned lane, reopen a development slice explicitly; do not bury it inside `testing/` language.
- If no code change is required, still record the verification result and handoff status in the source and aggregate ledgers.

## Command policy

- Environment repair only when needed: `uv sync --extra dev`
- Runtime health before a new execution lane or cross-app handoff: `uv run splitshot --check`
- Narrow Python validation: `./.venv/bin/python -m pytest ...`
- Python lint after code changes: `uvx ruff check .`
- Final repo-health anchor only at the integration handoff gate: `uv run python scripts/testing/run_test_suite.py --mode all-together --format table`
- Record the exact command, exit status, and artifact path in the touched `outcome.md` / `artifacts.md` files.

## DEV-001 — Lock the Work Effort 1 boundary

- [x] Record the `development/` versus `testing/` split.
- [x] Record the exact source-bundle mapping for Work Effort 1.
- [x] Record that source `predev/tests/` is not the same thing as aggregate `testing/`.
- [x] Add an execution schema that subagents can follow slice by slice.
- [x] Add explicit command policy, blocker-routing, and parallelization rules to this file.

Progress note (`2026-05-25`):

- The aggregate Work Effort 1 bundle now defines atomic slices, command policy, and subagent-safe execution rules.
- `../MASTER_STATUS.md`, `../README.md`, and `../RECOVERY_NEXT_STEPS.md` remain the cross-bundle coordination points for this split.
- The detailed source bundles for this split live under `../predev/`.

Parallelization:

- Must be complete before any other `DEV-*` slice starts.

Required sources:

- `plan.md`
- `spec.md`
- `outcome.md`
- `artifacts.md`
- `../MASTER_STATUS.md`
- `../RECOVERY_NEXT_STEPS.md`

Commands:

- No code command is required unless the work-effort boundary changes again.

Exit criteria:

- Every later slice can rely on this file for scope, command policy, blocker routing, and parallelization rules.

## DEV-002 — Stage baseline integrity gate

Source scope:

- `STG-001` through `STG-006`

Parallelization:

- Must finish before any slice that changes shared Stage shell, Project-pane defaults, or Stage parity behavior.
- May run as a verification audit in parallel with `DEV-003A` and `DEV-004A` after `DEV-001` is locked.

Read first:

- `../predev/stage/plan.md`
- `../predev/stage/spec.md`
- `../predev/stage/tasks.md`
- `../predev/stage/outcome.md`
- `../predev/stage/artifacts.md`

Allowed edit surface:

- `src/splitshot/browser/static/index.html`
- `src/splitshot/browser/static/app.js`
- `src/splitshot/browser/static/styles/layout.css`
- `src/splitshot/ui/controller.py`
- `../predev/stage/tasks.md`
- `../predev/stage/outcome.md`
- `../predev/stage/artifacts.md`
- `outcome.md`
- `artifacts.md`

Do not claim here:

- `STG-007`
- `STG-008`
- screenshots
- visual approval
- final proof/signoff closure

Execute:

- [x] Carry forward `STG-001` through `STG-006` as Work Effort 1 scope.
- [x] Keep Stage shell, Project redistribution, defaults, regression closure, and parity implementation out of testing rework unless a real implementation blocker is discovered.
- [x] Verify that no newly touched code reopens the Stage shell, import/defaults, waveform/review, or PractiScore contracts.
- [x] If a blocker exists, land the smallest code fix required to restore the Stage baseline and name the reopened Stage seam explicitly in `../predev/stage/outcome.md`; no Stage reopen was required in the current pass.
- [x] Record either `no reopen required` or the reopened blocker plus its residual risk in the Stage and aggregate ledgers.

Progress note (`2026-05-25`):

- The current closeout audit re-ran runtime health plus the Stage shell/static, project/defaults/import, waveform/review/overlay, and PractiScore guardrail packs.
- The audit stayed green with `44 passed`, `13 passed`, `37 passed`, and `16 passed`, and no Stage-owned code seam required a Work Effort 1 reopen.
- Remaining Stage work stays confined to `STG-008` final-gate proof/signoff closure in `testing/`.

Commands:

- Preflight when Stage-owned code changed: `uv run splitshot --check`
- Shell/static regression pack: `./.venv/bin/python -m pytest tests/browser/test_automation_ui_shell_contracts.py tests/browser/test_browser_static_ui.py tests/browser/test_browser_rail_layout.py`
- Project/defaults/import pack: `./.venv/bin/python -m pytest tests/browser/test_project_lifecycle_contracts.py tests/browser/test_merge_export_contracts.py`
- Review/waveform/overlay pack when those surfaces changed: `./.venv/bin/python -m pytest tests/browser/test_timing_waveform_contracts.py tests/browser/test_overlay_review_contracts.py tests/browser/test_browser_remaining_controls_e2e.py`
- PractiScore/session guardrail when Project-pane Stage import behavior changed: `./.venv/bin/python -m pytest tests/browser/test_practiscore_session_api.py tests/browser/test_practiscore_sync_controller.py`
- Lint after Python changes: `uvx ruff check .`

Update when done:

- `../predev/stage/outcome.md`
- `../predev/stage/artifacts.md`
- `outcome.md`
- `artifacts.md`

Exit criteria:

- The Stage baseline remains implementation-complete through `STG-006`.
- Any true Stage regression is either fixed now or explicitly reopened as development work.
- Only testing-owned proof/signoff work remains for Stage.

## DEV-003 — Match implementation closure umbrella

Source scope:

- `MCH-001`
- implementation side of `MCH-002` through `MCH-006`

Parallelization:

- `DEV-003A` and `DEV-003B` may run in parallel after `DEV-002`.
- `DEV-003C` is the single-owner Match integrator and must run after `DEV-003A` and `DEV-003B`.

Read first:

- `../predev/match/plan.md`
- `../predev/match/spec.md`
- `../predev/match/tasks.md`
- `../predev/match/outcome.md`
- `../predev/match/artifacts.md`
- `../predev/stage/spec.md`
- `../predev/stage/tasks.md`

Do not claim anywhere in `DEV-003`:

- `MCH-007`
- screenshots
- recap/composite/export proof package
- visual approval

### DEV-003A — Match auto-seed and workspace lifecycle integrity

Depends on:

- `DEV-001`
- `DEV-002`

Can run in parallel with:

- `DEV-003B`
- `DEV-004A`
- `DEV-004B`

Allowed edit surface:

- `src/splitshot/ui/controller.py`
- `src/splitshot/browser/server.py`
- `src/splitshot/browser/state.py`
- `../predev/match/tasks.md`
- `../predev/match/outcome.md`
- `../predev/match/artifacts.md`
- `outcome.md`
- `artifacts.md`

Execute:

- [x] Verify Stage project open/save continues to auto-attach or auto-create Match membership where the source bundle expects it.
- [x] Verify Stage open and return-to-Match context remains stable.
- [x] Land the smallest controller/state fix needed if the lifecycle contract drifted; no lifecycle drift requiring a code change was found in the current pass.
- [x] Record any remaining proof-only work for `testing/` without claiming it complete here.

Progress note (`2026-05-25`):

- The current closeout audit re-ran the Match auto-attach / auto-create controller pack (`2 passed`), the Stage-open shell-return pack (`1 passed`), and the Match open/save smoke pack (`2 passed`).
- No Match lifecycle reopen was required; the remaining Match work stays in proof/signoff packaging owned by `testing/`.

Commands:

- Preflight when controller/server/state changed: `uv run splitshot --check`
- Auto-attach / auto-create controller pack: `./.venv/bin/python -m pytest tests/browser/test_workspace_flows.py -k "open_project_inside_saved_workspace_auto_attaches_stage_membership or save_project_without_saved_workspace_auto_creates_unsaved_match_membership"`
- Browser lifecycle shell-return pack: `./.venv/bin/python -m pytest tests/browser/test_browser_interactions.py::test_match_workspace_stage_open_and_shell_return_restore_match_context`
- Workspace lifecycle smoke pack: `./.venv/bin/python -m pytest tests/browser/test_browser_interactions.py::test_match_workspace_open_button_uses_picker_and_loads_saved_workspace tests/browser/test_browser_interactions.py::test_match_workspace_save_button_uses_picker_for_first_save`
- Lint after Python changes: `uvx ruff check .`

Update when done:

- `../predev/match/outcome.md`
- `../predev/match/artifacts.md`
- `outcome.md`
- `artifacts.md`

Exit criteria:

- Match lifecycle implementation is stable enough that Work Effort 2 only has proof/signoff work left for this seam.

### DEV-003B — Match lower-pane and right-inspector implementation integrity

Depends on:

- `DEV-001`
- `DEV-002`

Can run in parallel with:

- `DEV-003A`
- `DEV-004A`
- `DEV-004B`

Allowed edit surface:

- `src/splitshot/browser/static/app.js`
- `src/splitshot/browser/static/lib/shell-runtime.js`
- `src/splitshot/browser/static/views/match-view.js`
- `src/splitshot/browser/static/index.html`
- `../predev/match/tasks.md`
- `../predev/match/outcome.md`
- `../predev/match/artifacts.md`
- `outcome.md`
- `artifacts.md`

Execute:

- [x] Verify the selected-stage lower pane remains the information owner for Match where the source spec expects it.
- [x] Verify workflow sections remain right-inspector centric.
- [x] Keep shared defaults, overrides, setup-once, and apply-from-first behavior stable.
- [x] Land the smallest shell/runtime/view fix needed if the implementation grammar drifted; no grammar drift requiring a code change was found in the current pass.

Progress note (`2026-05-25`):

- The shared-shell contract pack stayed green (`44 passed`), and the focused lower-pane/workflow pack stayed green (`4 passed`).
- Match lower-pane truth, right-inspector workflow ownership, and defaults/override behavior remain implementation-stable for Work Effort 1 handoff.

Commands:

- Shell/static contract pack: `./.venv/bin/python -m pytest tests/browser/test_automation_ui_shell_contracts.py tests/browser/test_browser_static_ui.py tests/browser/test_browser_rail_layout.py`
- Match lower-pane and workflow pack: `./.venv/bin/python -m pytest tests/browser/test_browser_interactions.py::test_match_workspace_setup_once_uses_preview_before_apply tests/browser/test_browser_interactions.py::test_match_workspace_shared_defaults_apply_and_reset tests/browser/test_browser_interactions.py::test_match_workspace_override_apply_and_reset_update_selected_stage tests/browser/test_browser_interactions.py::test_match_workspace_shell_keeps_selected_stage_detail_and_workflow_visible`
- Lint after JavaScript-adjacent Python changes only: `uvx ruff check .`

Update when done:

- `../predev/match/outcome.md`
- `../predev/match/artifacts.md`
- `outcome.md`
- `artifacts.md`

Exit criteria:

- Match implementation grammar is stable enough that screenshots and proof packaging can remain wholly in Work Effort 2.

### DEV-003C — Match implementation integrator and handoff check

Depends on:

- `DEV-003A`
- `DEV-003B`

Must stay serialized with:

- `DEV-007`

Allowed edit surface:

- `../predev/match/tasks.md`
- `../predev/match/outcome.md`
- `../predev/match/artifacts.md`
- `outcome.md`
- `artifacts.md`

Execute:

- [x] Confirm `MCH-001` plus the implementation side of `MCH-002` through `MCH-006` are either implementation-complete or explicitly deferred.
- [x] Confirm `MCH-007`, screenshots, recap/export artifact proof, and visual approval remain reserved for `testing/`.
- [x] Record any residual implementation blocker as a named reopen item rather than vague risk text; no residual Match implementation blocker remained in the current pass.

Progress note (`2026-05-25`):

- The current closeout audit confirmed that Work Effort 1 owns only the implementation side of `MCH-001` through `MCH-006`, while `MCH-007` and the remaining screenshot/artifact/signoff work stay reserved for `testing/`.
- No Match implementation reopen was required in the aggregate handoff.

Commands:

- Match integration smoke pack: `./.venv/bin/python -m pytest tests/browser/test_browser_interactions.py tests/browser/test_workspace_flows.py`

Update when done:

- `../predev/match/outcome.md`
- `../predev/match/artifacts.md`
- `outcome.md`
- `artifacts.md`

Exit criteria:

- Match is ready to hand off only proof/signoff work into `testing/`.

## DEV-004 — Performance implementation closure umbrella

Source scope:

- `PRF-001`
- implementation side of `PRF-002` through `PRF-005`

Parallelization:

- `DEV-004A` and `DEV-004B` may run in parallel after `DEV-002`.
- `DEV-004C` is the single-owner Performance integrator and must run after `DEV-004A` and `DEV-004B`.

Read first:

- `../predev/performance/plan.md`
- `../predev/performance/spec.md`
- `../predev/performance/tasks.md`
- `../predev/performance/outcome.md`
- `../predev/performance/artifacts.md`
- `../predev/stage/spec.md`

Do not claim anywhere in `DEV-004`:

- `PRF-006`
- `PRF-007`
- screenshots
- backup/export proof package
- visual approval

### DEV-004A — Performance shell, lower-pane, and reopen integrity

Depends on:

- `DEV-001`
- `DEV-002`

Can run in parallel with:

- `DEV-004B`
- `DEV-003A`
- `DEV-003B`

Allowed edit surface:

- `src/splitshot/browser/static/app.js`
- `src/splitshot/browser/static/lib/shell-runtime.js`
- `src/splitshot/browser/static/views/library-view.js`
- `src/splitshot/browser/static/index.html`
- `../predev/performance/tasks.md`
- `../predev/performance/outcome.md`
- `../predev/performance/artifacts.md`
- `outcome.md`
- `artifacts.md`

Execute:

- [x] Verify the lower pane remains the selected-record detail owner where the Performance spec expects it.
- [x] Verify filters, actions, and settings stay in the right inspector.
- [x] Verify Stage/workspace reopen behavior remains stable from the current shell.
- [x] Land the smallest shell/runtime/view fix needed if this grammar drifted; no Performance shell grammar drift requiring a code change remained after the current pass.

Progress note (`2026-05-25`):

- Existing Work Effort 1 anchors remain sufficient for closeout: the shared-shell/control-inventory pack (`50 passed`), the focused Performance/PractiScore recovery slice (`13 passed`), and the cross-surface reopen guardrail pack (`18 passed`).
- No Work Effort 1 reopen was required for the Performance lower-pane/right-inspector grammar or reopen flows.

Commands:

- Shell/static contract pack: `./.venv/bin/python -m pytest tests/browser/test_automation_ui_shell_contracts.py tests/browser/test_browser_static_ui.py tests/browser/test_browser_rail_layout.py`
- Performance shell/reopen pack: `./.venv/bin/python -m pytest tests/browser/test_browser_interactions.py::test_performance_library_shows_loading_and_recovers_from_route_failure tests/browser/test_browser_interactions.py::test_performance_library_can_reopen_stage_and_workspace_from_selected_record`
- Detail-grammar smoke pack: `./.venv/bin/python -m pytest tests/browser/test_browser_interactions.py::test_performance_library_search_filters_records_and_keeps_lower_detail_truth`

Update when done:

- `../predev/performance/outcome.md`
- `../predev/performance/artifacts.md`
- `outcome.md`
- `artifacts.md`

Exit criteria:

- Performance shell and reopen behavior are implementation-stable enough that Work Effort 2 only needs proof, screenshots, and final closeout.

### DEV-004B — Performance search, analytics, backup, and export implementation integrity

Depends on:

- `DEV-001`
- `DEV-002`

Can run in parallel with:

- `DEV-004A`
- `DEV-003A`
- `DEV-003B`

Allowed edit surface:

- `src/splitshot/browser/static/views/library-view.js`
- `src/splitshot/browser/server.py`
- `src/splitshot/browser/state.py`
- `src/splitshot/ui/controller.py`
- `../predev/performance/tasks.md`
- `../predev/performance/outcome.md`
- `../predev/performance/artifacts.md`
- `outcome.md`
- `artifacts.md`

Execute:

- [x] Verify search, sort, and filter behavior remains implementation-complete.
- [x] Verify note/tag persistence and analytics truth remain stable.
- [x] Verify backup and export implementation seams are code-complete even if proof packaging remains for `testing/`.
- [x] Land the smallest backend/controller/view fix needed if the implementation seam drifted; no Performance backend/controller/view reopen was required in the current pass.

Progress note (`2026-05-25`):

- Existing source-ledger anchors already cover the Work Effort 1 implementation seam for search/detail, notes/tags persistence, analytics truth, settings isolation, and backend/export support.
- Backup/export proof packaging remains reserved for `testing/`, but no first-order implementation blocker remained open in Work Effort 1.

Commands:

- Search/detail pack: `./.venv/bin/python -m pytest tests/browser/test_browser_interactions.py::test_performance_library_search_filters_records_and_keeps_lower_detail_truth`
- Analytics and notes/tags pack: `./.venv/bin/python -m pytest tests/browser/test_browser_interactions.py::test_performance_library_detail_ui_persists_tag_add_remove_and_notes tests/browser/test_browser_interactions.py::test_performance_library_summary_tiles_and_personal_bests_follow_loaded_records`
- Settings isolation pack when persistence changed: `./.venv/bin/python -m pytest tests/browser/test_browser_interactions.py::test_performance_library_settings_persist_and_manual_refresh_loads_records tests/browser/test_browser_interactions.py::test_performance_library_settings_remain_isolated_from_match_settings`
- Backend/export smoke pack when backup/export code changed: `./.venv/bin/python -m pytest tests/browser/test_library_backend_contracts.py tests/export/test_export.py`
- Lint after Python changes: `uvx ruff check .`

Update when done:

- `../predev/performance/outcome.md`
- `../predev/performance/artifacts.md`
- `outcome.md`
- `artifacts.md`

Exit criteria:

- Performance implementation is stable enough that Work Effort 2 only needs proof packaging, screenshots, and final signoff.

### DEV-004C — Performance implementation integrator and handoff check

Depends on:

- `DEV-004A`
- `DEV-004B`

Must stay serialized with:

- `DEV-007`

Allowed edit surface:

- `../predev/performance/tasks.md`
- `../predev/performance/outcome.md`
- `../predev/performance/artifacts.md`
- `outcome.md`
- `artifacts.md`

Execute:

- [x] Confirm `PRF-001` plus the implementation side of `PRF-002` through `PRF-005` are either implementation-complete or explicitly deferred.
- [x] Confirm `PRF-006`, `PRF-007`, screenshots, backup/export proof, and visual approval remain reserved for `testing/`.
- [x] Record any residual implementation blocker as a named reopen item; no residual Performance implementation blocker remained after the current pass.

Progress note (`2026-05-25`):

- The aggregate handoff now treats the current Performance implementation baseline as closed for Work Effort 1, with `PRF-006`, `PRF-007`, and the remaining screenshot/artifact/signoff work explicitly reserved for `testing/`.
- No Performance implementation reopen was required after the stale/error recovery fix and source-ledger sync.

Commands:

- Performance integration smoke pack: `./.venv/bin/python -m pytest tests/browser/test_browser_interactions.py tests/browser/test_library_backend_contracts.py`

Update when done:

- `../predev/performance/outcome.md`
- `../predev/performance/artifacts.md`
- `outcome.md`
- `artifacts.md`

Exit criteria:

- Performance is ready to hand off only proof/signoff work into `testing/`.

## DEV-005 — Backend implementation pass umbrella

Source scope:

- `BEK-001` through `BEK-006`

Parallelization:

- `DEV-005A` must finish first.
- `DEV-005B` and `DEV-005C` must follow `DEV-005A`.
- `DEV-005D` and `DEV-005E` may run in parallel after `DEV-005B` and `DEV-005C` are stable.
- `DEV-005F` is the single-owner backend integrator and must run last inside the backend lane.

Read first:

- `../predev/backend/plan.md`
- `../predev/backend/spec.md`
- `../predev/backend/tasks.md`
- `../predev/backend/outcome.md`
- `../predev/backend/artifacts.md`

Resolved baseline for this umbrella:

- The source backend docs now carry the explicit route/state inventory, `/api/state` summary families, and owning-test matrix needed for downstream backend slice closure.

Progress note (`2026-05-25`):

- The backend source bundle is now materially executed through `BEK-006`.
- `../predev/backend/spec.md` now carries the explicit route/state inventory and `/api/state` summary families required by this umbrella.
- Targeted backend/persistence/PractiScore/library packs are recorded in `../predev/backend/artifacts.md`, and the aggregate handoff now treats `BEK-007` / `BEK-008` as testing-owned proof/signoff work.

### DEV-005A — Inventory route and state ownership

Depends on:

- `DEV-001`
- `DEV-003C`
- `DEV-004C`

Must stay serialized before:

- `DEV-005B`
- `DEV-005C`
- `DEV-005D`
- `DEV-005E`
- `DEV-005F`

Allowed edit surface:

- `src/splitshot/browser/server.py`
- `src/splitshot/browser/state.py`
- `src/splitshot/ui/controller.py`
- `../predev/backend/spec.md`
- `../predev/backend/tasks.md`
- `../predev/backend/outcome.md`
- `../predev/backend/artifacts.md`
- `outcome.md`
- `artifacts.md`

Execute:

- [x] Expand `../predev/backend/spec.md` with an explicit route table labeling every route as shared, Stage-facing, Match-facing, or Performance-facing.
- [x] Expand `../predev/backend/spec.md` with an explicit `/api/state` summary key inventory.
- [x] Record the owning test files and docs for each route/state family in `../predev/backend/artifacts.md`.
- [x] Record any hidden ownership ambiguity as a blocker before later backend slices begin.

Commands:

- Route inventory grep: `git --no-pager grep -n '"/api/' -- src/splitshot/browser/server.py src/splitshot/browser/static/app.js src/splitshot/browser/static/views`
- State inventory grep: `git --no-pager grep -n '/api/state' -- src/splitshot/browser/server.py src/splitshot/browser/static/app.js src/splitshot/browser/static/views`
- Shared-route contract pack: `./.venv/bin/python -m pytest tests/browser/test_automation_ui_shell_contracts.py tests/browser/test_browser_control.py`

Update when done:

- `../predev/backend/spec.md`
- `../predev/backend/outcome.md`
- `../predev/backend/artifacts.md`
- `outcome.md`
- `artifacts.md`

Exit criteria:

- Later backend slices can point at an explicit ownership inventory rather than general prose.

### DEV-005B — Harden `/api/state` summary contract

Depends on:

- `DEV-005A`

Can run in parallel with:

- `DEV-005C`

Allowed edit surface:

- `src/splitshot/browser/server.py`
- `src/splitshot/browser/state.py`
- `src/splitshot/ui/controller.py`
- `../predev/backend/spec.md`
- `../predev/backend/outcome.md`
- `../predev/backend/artifacts.md`
- `outcome.md`
- `artifacts.md`

Execute:

- [x] Define exactly which summary slices are allowed in `/api/state` and which heavy payloads must stay on dedicated routes.
- [x] Keep app-local settings and large workflow payloads out of `/api/state` unless the contract explicitly changes.
- [x] Update source docs if the summary schema changes.

Commands:

- `/api/state` inventory grep: `git --no-pager grep -n '/api/state' -- src/splitshot/browser/server.py src/splitshot/browser/static/app.js src/splitshot/browser/static/views`
- Summary-state validation pack: `./.venv/bin/python -m pytest tests/browser/test_browser_control.py tests/persistence/test_persistence.py tests/persistence/test_workspace_persistence.py`
- Lint after Python changes: `uvx ruff check .`

Update when done:

- `../predev/backend/spec.md`
- `../predev/backend/outcome.md`
- `../predev/backend/artifacts.md`
- `outcome.md`
- `artifacts.md`

Exit criteria:

- `/api/state` is explicitly summary-oriented and test-backed.

### DEV-005C — Normalize status, error, and activity behavior

Depends on:

- `DEV-005A`

Can run in parallel with:

- `DEV-005B`

Allowed edit surface:

- `src/splitshot/browser/server.py`
- `src/splitshot/browser/state.py`
- `src/splitshot/ui/controller.py`
- `../predev/backend/spec.md`
- `../predev/backend/outcome.md`
- `../predev/backend/artifacts.md`
- `outcome.md`
- `artifacts.md`

Execute:

- [x] Define consistent success/error payload expectations for shared routes.
- [x] Keep browser-visible failures recoverable and explicit.
- [x] Normalize activity/error behavior across import, sync, export, backup, and restore seams.

Commands:

- PractiScore/session error pack: `./.venv/bin/python -m pytest tests/browser/test_practiscore_session_api.py tests/browser/test_practiscore_sync_controller.py`
- Browser lifecycle error pack: `./.venv/bin/python -m pytest tests/browser/test_project_lifecycle_contracts.py tests/browser/test_workspace_flows.py`
- Lint after Python changes: `uvx ruff check .`

Update when done:

- `../predev/backend/spec.md`
- `../predev/backend/outcome.md`
- `../predev/backend/artifacts.md`
- `outcome.md`
- `artifacts.md`

Exit criteria:

- Shared backend error and status behavior is explicit enough for testing to package proof without rediscovering route semantics.

### DEV-005D — Close persistence, reopen, and truth-hash behavior

Depends on:

- `DEV-005B`
- `DEV-005C`

Can run in parallel with:

- `DEV-005E`

Allowed edit surface:

- `src/splitshot/ui/controller.py`
- `src/splitshot/browser/server.py`
- `src/splitshot/browser/state.py`
- `../predev/backend/tasks.md`
- `../predev/backend/outcome.md`
- `../predev/backend/artifacts.md`
- `outcome.md`
- `artifacts.md`

Execute:

- [x] Keep workspace save/load/autosave deterministic.
- [x] Keep open-stage and return-to-workspace identity stable.
- [x] Keep workspace-to-library synchronization deterministic and truth-hash behavior stable.
- [x] Keep shared export/backup/import persistence paths truthful.

Commands:

- Persistence pack: `./.venv/bin/python -m pytest tests/persistence/test_workspace_persistence.py tests/persistence/test_persistence.py tests/persistence/test_project_lifecycle_contracts.py`
- Cross-app reopen/library sync pack: `./.venv/bin/python -m pytest tests/browser/test_project_lifecycle_contracts.py tests/browser/test_library_backend_contracts.py`
- Lint after Python changes: `uvx ruff check .`

Update when done:

- `../predev/backend/outcome.md`
- `../predev/backend/artifacts.md`
- `outcome.md`
- `artifacts.md`

Exit criteria:

- Persistence and reopen behavior are implementation-complete enough that Work Effort 2 only has proof/signoff left.

### DEV-005E — Protect import and PractiScore contracts

Depends on:

- `DEV-005B`
- `DEV-005C`

Can run in parallel with:

- `DEV-005D`

Allowed edit surface:

- `src/splitshot/ui/controller.py`
- `src/splitshot/browser/server.py`
- `src/splitshot/browser/state.py`
- `src/splitshot/scoring/practiscore.py`
- `src/splitshot/scoring/practiscore_sync_normalize.py`
- `src/splitshot/scoring/practiscore_web_extract.py`
- `../predev/backend/tasks.md`
- `../predev/backend/outcome.md`
- `../predev/backend/artifacts.md`
- `outcome.md`
- `artifacts.md`

Execute:

- [x] Preserve manual PractiScore file fallback and Stage-facing session/sync/options payload contracts.
- [x] Preserve supported blank-project and saved-project import behavior.
- [x] Keep recoverable remote-session and remote-import failures explicit.

Commands:

- PractiScore browser route pack: `./.venv/bin/python -m pytest tests/browser/test_practiscore_session_api.py tests/browser/test_practiscore_sync_controller.py`
- Stage/Project import pack: `./.venv/bin/python -m pytest tests/browser/test_project_lifecycle_contracts.py`
- Analysis import pack: `./.venv/bin/python -m pytest tests/analysis/test_practiscore_import.py tests/analysis/test_practiscore_sync_normalize.py tests/analysis/test_practiscore_web_extract.py`
- Lint after Python changes: `uvx ruff check .`

Update when done:

- `../predev/backend/outcome.md`
- `../predev/backend/artifacts.md`
- `outcome.md`
- `artifacts.md`

Exit criteria:

- Stage-facing import and PractiScore contracts are implementation-stable and clearly reserved for proof closure in `testing/`.

### DEV-005F — Lock Match and Performance backend support

Depends on:

- `DEV-005D`
- `DEV-005E`

Must stay serialized before:

- `DEV-007`

Allowed edit surface:

- `src/splitshot/ui/controller.py`
- `src/splitshot/browser/server.py`
- `src/splitshot/browser/state.py`
- `../predev/backend/tasks.md`
- `../predev/backend/outcome.md`
- `../predev/backend/artifacts.md`
- `outcome.md`
- `artifacts.md`

Execute:

- [x] Confirm Match-facing workspace routes remain stable and namespaced.
- [x] Confirm Performance-facing library routes remain stable and namespaced.
- [x] Confirm reopen/export/backup support routes remain truthful for both apps.
- [x] Record any dedicated app-route guarantees in the backend ledgers.

Commands:

- Match/Performance backend smoke pack: `./.venv/bin/python -m pytest tests/browser/test_workspace_flows.py tests/browser/test_browser_interactions.py tests/browser/test_library_backend_contracts.py`
- Persistence cross-check: `./.venv/bin/python -m pytest tests/persistence/test_workspace_persistence.py tests/persistence/test_persistence.py`
- Lint after Python changes: `uvx ruff check .`

Update when done:

- `../predev/backend/outcome.md`
- `../predev/backend/artifacts.md`
- `outcome.md`
- `artifacts.md`

Exit criteria:

- Backend implementation is explicit enough that `BEK-007` and `BEK-008` can remain pure proof/signoff work.

## DEV-006 — Modularization implementation pass umbrella

Source scope:

- `MOD-001` through `MOD-005`

Parallelization:

- `DEV-006A` must run first.
- `DEV-006B` must follow `DEV-006A`.
- `DEV-006C` and `DEV-006D` may run in parallel after `DEV-006B` if one integrator owns merge/sync.
- `DEV-006E` must run after `DEV-006C` and `DEV-006D`.

Read first:

- `../predev/modularization/plan.md`
- `../predev/modularization/spec.md`
- `../predev/modularization/tasks.md`
- `../predev/modularization/outcome.md`
- `../predev/modularization/artifacts.md`

Resolved baseline for this umbrella:

- The source modularization docs now carry the explicit file/module ownership map, interface rules, persistence boundaries, and temporary exceptions needed for downstream slice closure.

Progress note (`2026-05-25`):

- The modularization source bundle is now materially executed through `MOD-005`.
- `../predev/modularization/spec.md` now carries the explicit file/module ownership map, persistence boundaries, and temporary exceptions required by this umbrella.
- The aggregate handoff now treats `MOD-006` / `MOD-007` as testing-owned proof/signoff work.

### DEV-006A — Inventory current shell and module ownership

Depends on:

- `DEV-001`
- `DEV-005F`

Must stay serialized before:

- `DEV-006B`
- `DEV-006C`
- `DEV-006D`
- `DEV-006E`

Allowed edit surface:

- `src/splitshot/browser/static/app.js`
- `src/splitshot/browser/static/lib/shell-runtime.js`
- `src/splitshot/browser/static/views/match-view.js`
- `src/splitshot/browser/static/views/library-view.js`
- `../predev/modularization/spec.md`
- `../predev/modularization/outcome.md`
- `../predev/modularization/artifacts.md`
- `outcome.md`
- `artifacts.md`

Execute:

- [x] Expand `../predev/modularization/spec.md` with a file/module ownership map for `app.js`, shared runtime helpers, Match view, and Performance view.
- [x] Record cross-app DOM queries, shared state seams, and hidden localStorage dependencies in `../predev/modularization/outcome.md`.
- [x] Name any unavoidable temporary exceptions explicitly.

Commands:

- Root orchestration inventory: `git --no-pager grep -n 'activeSurface' -- src/splitshot/browser/static/app.js src/splitshot/browser/static/lib/shell-runtime.js src/splitshot/browser/static/views`
- DOM dependency inventory: `git --no-pager grep -n 'querySelector' -- src/splitshot/browser/static/app.js src/splitshot/browser/static/lib src/splitshot/browser/static/views`
- Local persistence inventory: `git --no-pager grep -n 'localStorage' -- src/splitshot/browser/static/app.js src/splitshot/browser/static/lib src/splitshot/browser/static/views`
- Shell contract smoke pack: `./.venv/bin/python -m pytest tests/browser/test_automation_ui_shell_contracts.py tests/browser/test_browser_static_ui.py`

Update when done:

- `../predev/modularization/spec.md`
- `../predev/modularization/outcome.md`
- `../predev/modularization/artifacts.md`
- `outcome.md`
- `artifacts.md`

Exit criteria:

- Later modularization slices can point at an explicit ownership map rather than inference.

### DEV-006B — Define stable interfaces and dependency rules

Depends on:

- `DEV-006A`

Must stay serialized before:

- `DEV-006C`
- `DEV-006D`
- `DEV-006E`

Allowed edit surface:

- `src/splitshot/browser/static/app.js`
- `src/splitshot/browser/static/lib/shell-runtime.js`
- `src/splitshot/browser/static/views/match-view.js`
- `src/splitshot/browser/static/views/library-view.js`
- `../predev/modularization/spec.md`
- `../predev/modularization/outcome.md`
- `../predev/modularization/artifacts.md`
- `outcome.md`
- `artifacts.md`

Execute:

- [x] Define which shell services `app.js` may own and which behaviors must move behind app-owned modules or helpers.
- [x] Define shared-runtime helper boundaries.
- [x] Define app-local persistence boundaries and any compatibility shims.

Commands:

- Shared-shell dependency inventory: `git --no-pager grep -n 'workspaceShell' -- src/splitshot/browser/static/app.js src/splitshot/browser/static/lib/shell-runtime.js src/splitshot/browser/static/views`
- Shared-shell contract pack: `./.venv/bin/python -m pytest tests/browser/test_automation_ui_shell_contracts.py tests/browser/test_browser_rail_layout.py`

Update when done:

- `../predev/modularization/spec.md`
- `../predev/modularization/outcome.md`
- `../predev/modularization/artifacts.md`
- `outcome.md`
- `artifacts.md`

Exit criteria:

- `DEV-006C` through `DEV-006E` can implement against a documented interface contract.

### DEV-006C — Extract and isolate Stage-owned behavior

Depends on:

- `DEV-006B`

Can run in parallel with:

- `DEV-006D`

Allowed edit surface:

- `src/splitshot/browser/static/app.js`
- `src/splitshot/browser/static/lib/shell-runtime.js`
- Stage-owned pane or helper modules already wired by `app.js`
- `../predev/modularization/outcome.md`
- `../predev/modularization/artifacts.md`
- `outcome.md`
- `artifacts.md`

Execute:

- [x] Move or isolate Stage-specific behavior out of generic shell logic where practical.
- [x] Remove accidental Match/Performance knowledge from Stage code paths.
- [x] Record any remaining exception explicitly if the extraction cannot fully land in this slice.

Commands:

- Stage-shell grep pack: `git --no-pager grep -n 'stage' -- src/splitshot/browser/static/app.js src/splitshot/browser/static/lib/shell-runtime.js src/splitshot/browser/static/views`
- Shell/static verification pack: `./.venv/bin/python -m pytest tests/browser/test_automation_ui_shell_contracts.py tests/browser/test_browser_static_ui.py tests/browser/test_browser_rail_layout.py`

Update when done:

- `../predev/modularization/outcome.md`
- `../predev/modularization/artifacts.md`
- `outcome.md`
- `artifacts.md`

Exit criteria:

- Stage behavior is explicitly owned and no longer hiding inside generic shell seams.

### DEV-006D — Constrain shared shell behavior

Depends on:

- `DEV-006B`

Can run in parallel with:

- `DEV-006C`

Allowed edit surface:

- `src/splitshot/browser/static/app.js`
- `src/splitshot/browser/static/lib/shell-runtime.js`
- `src/splitshot/browser/static/views/match-view.js`
- `src/splitshot/browser/static/views/library-view.js`
- `../predev/modularization/outcome.md`
- `../predev/modularization/artifacts.md`
- `outcome.md`
- `artifacts.md`

Execute:

- [x] Keep `app.js` focused on landing, switching, shared status, and shared settings entry points.
- [x] Remove accidental Match or Performance feature ownership from root orchestration.
- [x] Record any temporary shared-shell exception explicitly.

Commands:

- Root orchestration grep: `git --no-pager grep -n 'setActiveSurface\|activeSurface\|refresh' -- src/splitshot/browser/static/app.js src/splitshot/browser/static/views`
- Shared-shell contract pack: `./.venv/bin/python -m pytest tests/browser/test_automation_ui_shell_contracts.py tests/browser/test_browser_rail_layout.py tests/browser/test_browser_static_ui.py`

Update when done:

- `../predev/modularization/outcome.md`
- `../predev/modularization/artifacts.md`
- `outcome.md`
- `artifacts.md`

Exit criteria:

- Shared shell scope is explicit enough that testing can prove it without discovering fresh architecture work.

### DEV-006E — Isolate app-local persistence and settings

Depends on:

- `DEV-006C`
- `DEV-006D`

Must stay serialized before:

- `DEV-007`

Allowed edit surface:

- `src/splitshot/browser/static/app.js`
- `src/splitshot/browser/static/lib/shell-runtime.js`
- `src/splitshot/browser/static/views/match-view.js`
- `src/splitshot/browser/static/views/library-view.js`
- `../predev/modularization/spec.md`
- `../predev/modularization/outcome.md`
- `../predev/modularization/artifacts.md`
- `outcome.md`
- `artifacts.md`

Execute:

- [x] Verify app-local settings and persistence keys remain scoped by app.
- [x] Prevent one app’s reload path from mutating another app’s local state.
- [x] Record any migration or compatibility shim in the source and aggregate ledgers.

Commands:

- Local persistence inventory: `git --no-pager grep -n 'localStorage' -- src/splitshot/browser/static/app.js src/splitshot/browser/static/lib src/splitshot/browser/static/views`
- Settings isolation pack: `./.venv/bin/python -m pytest tests/browser/test_browser_interactions.py::test_match_settings_persist_locally_and_control_match_return_selection tests/browser/test_browser_interactions.py::test_performance_library_settings_persist_and_manual_refresh_loads_records tests/browser/test_browser_interactions.py::test_performance_library_settings_remain_isolated_from_match_settings`

Update when done:

- `../predev/modularization/spec.md`
- `../predev/modularization/outcome.md`
- `../predev/modularization/artifacts.md`
- `outcome.md`
- `artifacts.md`

Exit criteria:

- App-local persistence and settings are isolated enough that Work Effort 2 can verify them without finding fresh architecture work.

## DEV-007 — Development integration and handoff gate

Parallelization:

- Single-owner integrator only.

Read first:

- `../MASTER_STATUS.md`
- `../RECOVERY_NEXT_STEPS.md`
- `../predev/stage/outcome.md`
- `../predev/match/outcome.md`
- `../predev/performance/outcome.md`
- `../predev/backend/outcome.md`
- `../predev/modularization/outcome.md`
- `outcome.md`
- `artifacts.md`

Execute:

- [x] Confirm all mapped implementation slices are complete or explicitly deferred.
- [x] Confirm only testing, proof, artifact, QA/doc sync, suite closure, and signoff work remain for Work Effort 2.
- [x] Confirm the aggregate `development/` bundle and all touched source bundles describe the same implementation truth.
- [x] Publish the Work Effort 2 handoff matrix by lane, including any residual implementation blockers or approved deferrals.

Progress note (`2026-05-25`):

- Work Effort 1 now hands off Backend and Modularization as implementation-advanced source bundles rather than planning baselines.
- The current pass also resolved the Performance library stale/error recovery implementation blocker discovered during shell validation.
- After ledger sync, only testing-owned proof/signoff work remains unless a new first-order implementation blocker is discovered.

Commands:

- Runtime health: `uv run splitshot --check`
- Cross-doc audit pack: `./.venv/bin/python -m pytest tests/browser/test_browser_control_coverage_matrix.py tests/browser/test_browser_control_inventory_audit.py`
- Broad owner-suite pack when shared shell or backend changed: `uv run python scripts/testing/run_test_suite.py --suite browser --suite persistence --suite analysis --mode all-together --format table --json-output artifacts/test-suite-development-handoff.json`
- Canonical repo-health anchor when the integrator needs a fresh full-suite baseline: `uv run python scripts/testing/run_test_suite.py --mode all-together --format table --json-output artifacts/current-all-together.json`

Update when done:

- `outcome.md`
- `artifacts.md`
- every touched `../predev/*/outcome.md`
- every touched `../predev/*/artifacts.md`

Exit criteria:

- Work Effort 1 is implementation-complete or has named, approved deferrals.
- `testing/` inherits only proof/signoff work plus any explicitly reopened implementation blockers.
- The development handoff matrix is explicit enough that parallel testing subagents do not need to rediscover scope.
