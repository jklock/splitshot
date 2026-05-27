# Testing Task Backlog

## Usage

- This bundle tracks Work Effort 2 / Set 2 only.
- The source bundles under `../predev/` remain the detailed truth; this file is the proof/signoff overlay for subagents.
- Treat each atomic slice as incomplete until the source bundle, proof artifacts, screenshots/docs where required, and aggregate closeout docs all agree.
- Do not treat source `predev/tests/` and aggregate `testing/` as synonyms.

## Subagent execution contract

- Assign one owner per atomic slice unless this file explicitly marks a safe parallel window.
- Read the named source docs before running proof commands.
- Run the narrowest targeted proof pack first; broaden only when the slice requires it.
- Capture outputs, screenshot paths, and suite artifacts in the owning source `artifacts.md` before claiming completion.
- If a proof slice uncovers a first-order implementation defect, stop, record the failing command and exact blocker, and route it back to `development/` instead of masking it as test churn.
- Keep source-ledger updates and aggregate-ledger updates in the same change.

## Proof pack minimums

- Targeted `pytest` commands for the owning surface.
- Screenshot or capture-script output when the source lane requires browser-visible evidence.
- Documentation and QA-matrix sync when route/control/test ownership changed.
- A clear pass/fail record, artifact path, and residual-risk note in the source and aggregate ledgers.

## Command policy

- Environment repair only when needed: `uv sync --extra dev`
- Runtime health before broader signoff or final acceptance: `uv run splitshot --check`
- Narrow Python validation: `./.venv/bin/python -m pytest ...`
- Canonical grouped suite runner for owned-lane anchors: `uv run python scripts/testing/run_test_suite.py --suite ... --mode all-together --format table`
- Canonical full-suite anchor only at the program gate: `uv run python scripts/testing/run_test_suite.py --mode all-together --format table`
- Record the exact command, exit status, screenshot/output location, and any waiver/blocker in the touched `outcome.md` / `artifacts.md` files.

## VAL-001 — Lock the Work Effort 2 boundary and evidence map

- [x] Record the `development/` versus `testing/` split.
- [x] Record the exact source-bundle mapping for Work Effort 2.
- [x] Record that source `predev/tests/` is one source lane inside this effort, not the same thing as aggregate `testing/`.
- [x] Record the closeout chain for focused proof, owned suites, canonical full-suite validation, and visual approval.
- [x] Add an execution schema that subagents can follow slice by slice.

Progress note (`2026-05-25`):

- The aggregate Work Effort 2 bundle now defines atomic proof slices, blocker routing, and evidence minimums.
- `../MASTER_STATUS.md`, `../README.md`, and `../RECOVERY_NEXT_STEPS.md` remain the cross-bundle coordination points for this split.
- The detailed source bundles for this split live under `../predev/`.

Parallelization:

- Must be complete before any later `VAL-*` slice starts.

Required sources:

- `plan.md`
- `spec.md`
- `outcome.md`
- `artifacts.md`
- `../MASTER_STATUS.md`
- `../RECOVERY_NEXT_STEPS.md`

Commands:

- No repo command is required unless the Work Effort 2 boundary changes again.

Exit criteria:

- Every later slice can rely on this file for evidence minimums, blocker routing, and parallelization rules.

## VAL-002 — Stage, Match, and Performance proof closure umbrella

Source scope:

- `STG-007`
- `STG-008`
- proof/signoff side of `MCH-002` through `MCH-007`
- proof/signoff side of `PRF-002` through `PRF-007`

Parallelization:

- `VAL-002A` must finish first because it re-validates the Stage shell baseline that Match and Performance inherit.
- After `VAL-002A`, `VAL-002B` and `VAL-002D` may run in parallel.
- `VAL-002C` depends on `VAL-002B`.
- `VAL-002E` depends on `VAL-002D`.

Read first:

- `../predev/stage/tasks.md`
- `../predev/stage/outcome.md`
- `../predev/stage/artifacts.md`
- `../predev/match/tasks.md`
- `../predev/match/outcome.md`
- `../predev/match/artifacts.md`
- `../predev/performance/tasks.md`
- `../predev/performance/outcome.md`
- `../predev/performance/artifacts.md`

### VAL-002A — Stage final proof pack and signoff gate

Depends on:

- `VAL-001`

Must stay serialized before:

- `VAL-002B`
- `VAL-002C`
- `VAL-002D`
- `VAL-002E`

Allowed edit surface:

- `../predev/stage/tasks.md`
- `../predev/stage/outcome.md`
- `../predev/stage/artifacts.md`
- `outcome.md`
- `artifacts.md`
- Stage-facing docs only when evidence paths or proof wording change

Execute:

- [x] Carry forward `STG-007` as Work Effort 2 scope.
- [x] Close `STG-008` with targeted proof, screenshots, artifact paths, and final-gate notes.
- [x] Record whether Stage requires any explicit visual approval note.
- [x] Route any newly discovered first-order Stage implementation defect back to `development/`.

Progress note (`2026-05-26`):

- The full Stage gate was rerun after the Compose/Overlay/Export workflow relocation.
- Runtime health passed, followed by `49 passed` across shell/static/inventory/coverage, `47 passed` across lifecycle/import and PractiScore browser+analysis proof, `37 passed` across timing/waveform/review/control proof, and `59 passed` across export/output-hook proof.
- `scripts/docs/capture_browser_screenshots.py` refreshed the repo-owned Stage screenshot set, and `scripts/docs/capture_stage_responsive_views.py` rewrote `docs/screenshots/automate3/responsive-proof-results.json` with passing responsive assertions at `1280px` and `900px`.
- No first-order Stage implementation defect was found, so nothing routes back to `development/`, and no new visual-approval note was required beyond the existing Stage signoff already recorded in the source bundle.

Commands:

- Stage shell/static proof pack: `./.venv/bin/python -m pytest tests/browser/test_automation_ui_shell_contracts.py tests/browser/test_browser_static_ui.py tests/browser/test_browser_rail_layout.py`
- Stage lifecycle/import proof pack: `./.venv/bin/python -m pytest tests/browser/test_project_lifecycle_contracts.py tests/browser/test_practiscore_session_api.py tests/browser/test_practiscore_sync_controller.py`
- Stage review/waveform proof pack: `./.venv/bin/python -m pytest tests/browser/test_timing_waveform_contracts.py tests/browser/test_overlay_review_contracts.py tests/browser/test_browser_remaining_controls_e2e.py`
- Stage screenshot pack: `./.venv/bin/python scripts/docs/capture_browser_screenshots.py`
- Stage responsive capture pack: `./.venv/bin/python scripts/docs/capture_stage_responsive_views.py`

Update when done:

- `../predev/stage/tasks.md`
- `../predev/stage/outcome.md`
- `../predev/stage/artifacts.md`
- `outcome.md`
- `artifacts.md`

Exit criteria:

- Stage has no open final-gate item.
- Stage proof artifacts and screenshot references are recorded.
- Any fresh implementation blocker is routed back to `development/` with exact failing evidence.

### VAL-002B — Match lifecycle and lower-pane proof pack

Depends on:

- `VAL-002A`

Can run in parallel with:

- `VAL-002D`

Allowed edit surface:

- `../predev/match/tasks.md`
- `../predev/match/outcome.md`
- `../predev/match/artifacts.md`
- `outcome.md`
- `artifacts.md`

Execute:

- [x] Close the proof side of Match lifecycle, membership auto-seed, lower-pane ownership, right-inspector behavior, and return-to-context flows.
- [x] Capture any required evidence for `MCH-002`, `MCH-003`, and the lifecycle portions of `MCH-004`.
- [x] Route any new implementation defect back to `development/` with exact failing command output.

Progress note (`2026-05-26`):

- The Match lifecycle proof pack stayed green with `3 passed`.
- The Match membership auto-seed pack stayed green with `2 passed`.
- The Match lower-pane / workflow proof pack stayed green with `4 passed`.
- No Match implementation defect was uncovered, so nothing routed back to `development/`.

Commands:

- Match lifecycle proof pack: `./.venv/bin/python -m pytest tests/browser/test_browser_interactions.py::test_match_workspace_open_button_uses_picker_and_loads_saved_workspace tests/browser/test_browser_interactions.py::test_match_workspace_save_button_uses_picker_for_first_save tests/browser/test_browser_interactions.py::test_match_workspace_stage_open_and_shell_return_restore_match_context`
- Match membership auto-seed pack: `./.venv/bin/python -m pytest tests/browser/test_workspace_flows.py -k "open_project_inside_saved_workspace_auto_attaches_stage_membership or save_project_without_saved_workspace_auto_creates_unsaved_match_membership"`
- Match lower-pane / workflow proof pack: `./.venv/bin/python -m pytest tests/browser/test_browser_interactions.py::test_match_workspace_setup_once_uses_preview_before_apply tests/browser/test_browser_interactions.py::test_match_workspace_shared_defaults_apply_and_reset tests/browser/test_browser_interactions.py::test_match_workspace_override_apply_and_reset_update_selected_stage tests/browser/test_browser_interactions.py::test_match_workspace_shell_keeps_selected_stage_detail_and_workflow_visible`

Update when done:

- `../predev/match/tasks.md`
- `../predev/match/outcome.md`
- `../predev/match/artifacts.md`
- `outcome.md`
- `artifacts.md`

Exit criteria:

- Match lifecycle and lower-pane proof is complete enough that only recap/composite/export and final Match closeout remain.

### VAL-002C — Match recap, composite, export, screenshots, and final gate

Depends on:

- `VAL-002B`

Must stay serialized before:

- `VAL-003A`
- `VAL-004A`
- `VAL-005A`

Allowed edit surface:

- `../predev/match/tasks.md`
- `../predev/match/outcome.md`
- `../predev/match/artifacts.md`
- `outcome.md`
- `artifacts.md`
- Match-facing docs only when proof references or screenshot locations change

Execute:

- [x] Close the proof side of `MCH-004`, `MCH-006`, and `MCH-007`.
- [x] Capture recap, composite, batch export, angle-director, screenshot, and artifact evidence.
- [x] Record the Match final-gate result and any required visual approval note.

Progress note (`2026-05-26`):

- The Match recap proof pack stayed green with `2 passed`.
- The Match batch export proof pack stayed green with `2 passed`.
- The Match composite / angle-director proof pack stayed green with `4 passed`.
- The Match settings isolation rerun stayed green with `2 passed`.
- `./.venv/bin/python scripts/docs/capture_match_proof.py` exited `0` and produced `artifacts/match-proof-20260526/`, including the empty/loaded/recap/composite/export/settings screenshot set, the recap output, the stage-composite export outputs, the auto-seed proof JSON, and the composite-plan artifacts.
- No additional visual-approval note was required beyond the Match source-bundle signoff recorded from the current proof bundle.

Commands:

- Match recap proof pack: `./.venv/bin/python -m pytest tests/browser/test_browser_interactions.py::test_match_workspace_recap_reports_success_and_error_states tests/browser/test_workspace_flows.py -k "workspace_recap_render_uses_transition_and_result_cards"`
- Match batch export proof pack: `./.venv/bin/python -m pytest tests/browser/test_browser_interactions.py::test_match_workspace_batch_export_queue_select_all_none_and_start tests/browser/test_browser_interactions.py::test_match_workspace_batch_export_reports_errors_truthfully`
- Match composite / angle-director proof pack: `./.venv/bin/python -m pytest tests/browser/test_browser_interactions.py::test_match_stage_composite_controls_update_composite_state tests/browser/test_browser_interactions.py::test_match_stage_composite_cut_override_editor_updates_plan_detail tests/browser/test_workspace_flows.py -k "angle_director_plan_merges_generated_cuts_with_persisted_override or angle_director_clear_cut_removes_only_requested_override"`
- Match proof bundle capture pack: `./.venv/bin/python scripts/docs/capture_match_proof.py`

Update when done:

- `../predev/match/tasks.md`
- `../predev/match/outcome.md`
- `../predev/match/artifacts.md`
- `outcome.md`
- `artifacts.md`

Exit criteria:

- Match has no open final-gate item.
- Match recap/composite/export proof, screenshots, and artifact references are recorded.

### VAL-002D — Performance shell, loading, search/filter, and reopen proof pack

Depends on:

- `VAL-002A`

Can run in parallel with:

- `VAL-002B`

Allowed edit surface:

- `../predev/performance/tasks.md`
- `../predev/performance/outcome.md`
- `../predev/performance/artifacts.md`
- `outcome.md`
- `artifacts.md`

Execute:

- [x] Close the proof side of Performance shell, loading/recovery, search/filter, lower-pane detail truth, and reopen flows.
- [x] Capture evidence for the shell/detail/search portions of `PRF-002`, `PRF-003`, and `PRF-004`.
- [x] Route any new first-order implementation defect back to `development/` with exact failing output.

Progress note (`2026-05-26`):

- The focused Performance shell/detail/reopen proof slice stayed green with `3 passed` across the loading/recovery, reopen, and lower-detail truth interactions.
- `docs/screenshots/automate3/loaded-library.png` plus `loaded-proof-results.json` now anchor the loaded Overview/Records/Detail grammar without reopening implementation.
- No first-order Performance implementation defect was uncovered, so nothing routed back to `development/`.

Commands:

- Performance shell/loading/reopen pack: `./.venv/bin/python -m pytest tests/browser/test_browser_interactions.py::test_performance_library_shows_loading_and_recovers_from_route_failure tests/browser/test_browser_interactions.py::test_performance_library_can_reopen_stage_and_workspace_from_selected_record`
- Performance search/detail pack: `./.venv/bin/python -m pytest tests/browser/test_browser_interactions.py::test_performance_library_search_filters_records_and_keeps_lower_detail_truth`
- Shared shell/static proof pack when shell ownership changed: `./.venv/bin/python -m pytest tests/browser/test_automation_ui_shell_contracts.py tests/browser/test_browser_static_ui.py tests/browser/test_browser_rail_layout.py`

Update when done:

- `../predev/performance/tasks.md`
- `../predev/performance/outcome.md`
- `../predev/performance/artifacts.md`
- `outcome.md`
- `artifacts.md`

Exit criteria:

- Performance shell/detail/search proof is complete enough that only analytics/settings/backup/export/screenshots and final closeout remain.

### VAL-002E — Performance analytics, settings, backup/export, screenshots, and final gate

Depends on:

- `VAL-002D`

Must stay serialized before:

- `VAL-003A`
- `VAL-004A`
- `VAL-005A`

Allowed edit surface:

- `../predev/performance/tasks.md`
- `../predev/performance/outcome.md`
- `../predev/performance/artifacts.md`
- `outcome.md`
- `artifacts.md`
- Performance-facing docs only when proof references or screenshot locations change

Execute:

- [x] Close the proof side of notes/tags, analytics, settings isolation, backup/export proof, and `PRF-007`.
- [x] Capture screenshot and artifact evidence for Performance final closeout.
- [x] Record any required visual approval note.

Progress note (`2026-05-26`):

- The focused notes/tags/analytics/settings pack stayed green with `4 passed`, and the backend/export proof pack stayed green with `72 passed`.
- `scripts/docs/capture_loaded_views.py` refreshed the loaded Performance shell capture, the section capture rerun added `performance-analytics.png`, `performance-backup.png`, and `performance-settings.png`, and `artifacts/performance-proof-20260526/` now records concrete CSV/JSON export plus backup create/restore artifacts.
- Visual review against the refreshed Performance screenshots passed with no reopened implementation defect, so the Performance final gate is closed.

Commands:

- Performance analytics / notes-toggles pack: `./.venv/bin/python -m pytest tests/browser/test_browser_interactions.py::test_performance_library_detail_ui_persists_tag_add_remove_and_notes tests/browser/test_browser_interactions.py::test_performance_library_summary_tiles_and_personal_bests_follow_loaded_records`
- Performance settings isolation pack: `./.venv/bin/python -m pytest tests/browser/test_browser_interactions.py::test_performance_library_settings_persist_and_manual_refresh_loads_records tests/browser/test_browser_interactions.py::test_performance_library_settings_remain_isolated_from_match_settings`
- Performance backend/export proof pack: `./.venv/bin/python -m pytest tests/browser/test_library_backend_contracts.py tests/export/test_export.py tests/export/test_merge_export_contracts.py`
- Performance loaded-state capture pack: `./.venv/bin/python scripts/docs/capture_loaded_views.py`
- Performance supplemental screenshot pack when the source ledger still needs extra evidence: `./.venv/bin/python scripts/docs/capture_additional_screenshots.py`

Update when done:

- `../predev/performance/tasks.md`
- `../predev/performance/outcome.md`
- `../predev/performance/artifacts.md`
- `outcome.md`
- `artifacts.md`

Exit criteria:

- Performance has no open final-gate item.
- Performance backup/export/screenshots/artifact references are recorded.

## VAL-003 — Backend proof and signoff umbrella

Source scope:

- `BEK-007`
- `BEK-008`

Parallelization:

- `VAL-003A` must run before `VAL-003B`.

Read first:

- `../predev/backend/spec.md`
- `../predev/backend/tasks.md`
- `../predev/backend/outcome.md`
- `../predev/backend/artifacts.md`

### VAL-003A — Backend route, state, persistence, import, and PractiScore proof pack

Depends on:

- `VAL-002C`
- `VAL-002E`

Allowed edit surface:

- `../predev/backend/tasks.md`
- `../predev/backend/outcome.md`
- `../predev/backend/artifacts.md`
- `outcome.md`
- `artifacts.md`
- backend docs only when proof references change

Execute:

- [x] Package route ownership, `/api/state`, status/error, persistence, import, and PractiScore proof against the now-explicit backend contract.
- [x] Confirm browser-visible payloads and recoverable error shapes match the documented contract.
- [x] Route any first-order contract failure back to `development/` with exact failing commands.

Progress note (`2026-05-26`):

- The focused backend proof packs stayed green with `114 passed`, `38 passed`, `22 passed`, and `22 passed`, covering the route/session/sync, persistence/reopen, cross-app backend, and PractiScore analysis slices.
- The backend source ledger now records the route/state contract, `/api/state` summary behavior, persistence truth, and recoverable PractiScore/browser error-shape proof against the same explicit backend contract.
- No first-order backend contract failure was uncovered, so nothing routed back to `development/`.

Commands:

- Backend route/session/sync proof pack: `./.venv/bin/python -m pytest tests/browser/test_practiscore_session_api.py tests/browser/test_practiscore_sync_controller.py tests/browser/test_browser_control.py`
- Backend persistence/reopen proof pack: `./.venv/bin/python -m pytest tests/persistence/test_workspace_persistence.py tests/persistence/test_persistence.py tests/persistence/test_project_lifecycle_contracts.py`
- Cross-app backend proof pack: `./.venv/bin/python -m pytest tests/browser/test_project_lifecycle_contracts.py tests/browser/test_library_backend_contracts.py`
- Analysis import proof pack: `./.venv/bin/python -m pytest tests/analysis/test_practiscore_import.py tests/analysis/test_practiscore_sync_normalize.py tests/analysis/test_practiscore_web_extract.py`

Update when done:

- `../predev/backend/tasks.md`
- `../predev/backend/outcome.md`
- `../predev/backend/artifacts.md`
- `outcome.md`
- `artifacts.md`

Exit criteria:

- The backend proof pack demonstrates the documented contract without uncovering unowned implementation work.

### VAL-003B — Backend signoff gate and broader suite anchor

Depends on:

- `VAL-003A`

Must stay serialized before:

- `VAL-004A`
- `VAL-005A`
- `VAL-006`

Allowed edit surface:

- `../predev/backend/tasks.md`
- `../predev/backend/outcome.md`
- `../predev/backend/artifacts.md`
- `outcome.md`
- `artifacts.md`

Execute:

- [x] Close `BEK-007` and `BEK-008`.
- [x] Record the backend proof artifact paths and any doc-sync updates.
- [x] Capture a broader owner-suite anchor if the route/persistence contract changed across multiple suites.

Progress note (`2026-05-26`):

- Runtime health passed, `artifacts/test-suite-backend-signoff.json` recorded `125 passed`, and `artifacts/test-suite-backend-browser.json` recorded `420 passed` across the broader browser owner suite.
- The backend source, aggregate testing, and top-level completion ledgers now point at the same backend proof package and accepted residual-risk record.
- Backend no longer has an open final-gate item.

Commands:

- Runtime health: `uv run splitshot --check`
- Backend owner-suite anchor: `uv run python scripts/testing/run_test_suite.py --suite persistence --suite analysis --mode all-together --format table --json-output artifacts/test-suite-backend-signoff.json`
- Shared-browser anchor when backend route/control behavior changed: `uv run python scripts/testing/run_test_suite.py --suite browser --mode all-together --format table --json-output artifacts/test-suite-backend-browser.json`

Update when done:

- `../predev/backend/tasks.md`
- `../predev/backend/outcome.md`
- `../predev/backend/artifacts.md`
- `outcome.md`
- `artifacts.md`

Exit criteria:

- Backend has no open final-gate item.
- Proof, broader suite anchor, and any required doc references are recorded.

## VAL-004 — Modularization proof and signoff umbrella

Source scope:

- `MOD-006`
- `MOD-007`

Parallelization:

- `VAL-004A` must run before `VAL-004B`.

Read first:

- `../predev/modularization/spec.md`
- `../predev/modularization/tasks.md`
- `../predev/modularization/outcome.md`
- `../predev/modularization/artifacts.md`

### VAL-004A — Ownership, shell-boundary, and app-isolation proof pack

Depends on:

- `VAL-003B`

Allowed edit surface:

- `../predev/modularization/tasks.md`
- `../predev/modularization/outcome.md`
- `../predev/modularization/artifacts.md`
- `outcome.md`
- `artifacts.md`

Execute:

- [ ] Prove the documented shared-shell boundary and app-owned module boundaries.
- [ ] Prove app-local settings/persistence isolation.
- [ ] Route any newly discovered first-order ownership gap back to `development/`.

Commands:

- Shared shell/static proof pack: `./.venv/bin/python -m pytest tests/browser/test_automation_ui_shell_contracts.py tests/browser/test_browser_static_ui.py tests/browser/test_browser_rail_layout.py`
- App-isolation proof pack: `./.venv/bin/python -m pytest tests/browser/test_browser_interactions.py::test_match_workspace_shell_keeps_selected_stage_detail_and_workflow_visible tests/browser/test_browser_interactions.py::test_match_settings_persist_locally_and_control_match_return_selection tests/browser/test_browser_interactions.py::test_performance_library_search_filters_records_and_keeps_lower_detail_truth tests/browser/test_browser_interactions.py::test_performance_library_settings_remain_isolated_from_match_settings`
- Ownership inventory spot-checks: `git --no-pager grep -n 'activeSurface' -- src/splitshot/browser/static/app.js src/splitshot/browser/static/lib/shell-runtime.js src/splitshot/browser/static/views`
- Local persistence spot-checks: `git --no-pager grep -n 'localStorage' -- src/splitshot/browser/static/app.js src/splitshot/browser/static/lib src/splitshot/browser/static/views`

Update when done:

- `../predev/modularization/tasks.md`
- `../predev/modularization/outcome.md`
- `../predev/modularization/artifacts.md`
- `outcome.md`
- `artifacts.md`

Exit criteria:

- The shell/app ownership model is proof-backed enough that modularization can move to final signoff.

### VAL-004B — Modularization signoff gate and browser anchor

Depends on:

- `VAL-004A`

Must stay serialized before:

- `VAL-005A`
- `VAL-006`

Allowed edit surface:

- `../predev/modularization/tasks.md`
- `../predev/modularization/outcome.md`
- `../predev/modularization/artifacts.md`
- `outcome.md`
- `artifacts.md`

Execute:

- [ ] Close `MOD-006` and `MOD-007`.
- [ ] Record the ownership-proof artifact paths and any doc-sync updates.
- [ ] Capture a broader browser-suite anchor when shared shell/app boundaries changed materially.

Commands:

- Browser owner-suite anchor: `uv run python scripts/testing/run_test_suite.py --suite browser --mode all-together --format table --json-output artifacts/test-suite-modularization-signoff.json`

Update when done:

- `../predev/modularization/tasks.md`
- `../predev/modularization/outcome.md`
- `../predev/modularization/artifacts.md`
- `outcome.md`
- `artifacts.md`

Exit criteria:

- Modularization has no open final-gate item.
- Proof and broader suite anchor are recorded.

## VAL-005 — Source `predev/tests/` execution and cross-doc sync umbrella

Source scope:

- `TST-001` through `TST-009`

Parallelization:

- `VAL-005A` must run first.
- `VAL-005B`, `VAL-005C`, and `VAL-005D` may run in parallel after `VAL-005A`.
- `VAL-005E` depends on `VAL-005B`, `VAL-005C`, and `VAL-005D`.
- `VAL-005F` is the single-owner tests-bundle closeout gate.

Read first:

- `../predev/tests/spec.md`
- `../predev/tests/tasks.md`
- `../predev/tests/outcome.md`
- `../predev/tests/artifacts.md`
- `docs/tests/TEST_SUITE_GUIDE.md`
- `docs/project/browser-control-qa-matrix.md`
- `docs/project/browser-control-coverage-plan.md`
- `docs/project/browser-full-e2e-qa-plan.md`

### VAL-005A — Inventory the current suite map and target ownership model

Depends on:

- `VAL-004B`

Must stay serialized before:

- `VAL-005B`
- `VAL-005C`
- `VAL-005D`
- `VAL-005E`
- `VAL-005F`

Allowed edit surface:

- `../predev/tests/spec.md`
- `../predev/tests/tasks.md`
- `../predev/tests/outcome.md`
- `../predev/tests/artifacts.md`
- `docs/tests/TEST_SUITE_GUIDE.md`
- `outcome.md`
- `artifacts.md`

Execute:

- [ ] Build the current inventory of Stage-owned, Match-owned, Performance-owned, and shared-shell/backend tests.
- [ ] Write the target ownership map into `../predev/tests/spec.md` and `../predev/tests/outcome.md`.
- [ ] Record mixed tests that still need splitting and the exact removal plan.

Commands:

- Canonical runner inventory: `uv run python scripts/testing/run_test_suite.py --list`
- Collect-only inventory: `./.venv/bin/python -m pytest --collect-only tests/browser tests/persistence tests/analysis`
- Test-definition inventory: `git --no-pager grep -n 'def test_' -- tests/browser tests/persistence tests/analysis`

Update when done:

- `../predev/tests/spec.md`
- `../predev/tests/tasks.md`
- `../predev/tests/outcome.md`
- `../predev/tests/artifacts.md`
- `docs/tests/TEST_SUITE_GUIDE.md`
- `outcome.md`
- `artifacts.md`

Exit criteria:

- Later `VAL-005*` slices can execute against an explicit ownership map rather than inference.

### VAL-005B — Carve and verify Stage-owned suites

Depends on:

- `VAL-005A`

Can run in parallel with:

- `VAL-005C`
- `VAL-005D`

Allowed edit surface:

- `tests/browser/`
- `../predev/tests/tasks.md`
- `../predev/tests/outcome.md`
- `../predev/tests/artifacts.md`
- `docs/tests/TEST_SUITE_GUIDE.md`
- `docs/project/browser-control-qa-matrix.md`
- `docs/project/browser-control-coverage-plan.md`
- `docs/project/browser-full-e2e-qa-plan.md`
- `outcome.md`
- `artifacts.md`

Execute:

- [ ] Isolate or classify Stage-owned shell/static, project lifecycle, waveform, review, and Stage-facing PractiScore proof.
- [ ] Split mixed tests if ownership is still ambiguous.
- [ ] Update owned-doc references for the moved or renamed Stage tests.

Commands:

- Stage collect-only pack: `./.venv/bin/python -m pytest --collect-only tests/browser/test_automation_ui_shell_contracts.py tests/browser/test_browser_static_ui.py tests/browser/test_project_lifecycle_contracts.py tests/browser/test_timing_waveform_contracts.py tests/browser/test_overlay_review_contracts.py`
- Stage owned-suite smoke pack: `./.venv/bin/python -m pytest tests/browser/test_automation_ui_shell_contracts.py tests/browser/test_browser_static_ui.py tests/browser/test_project_lifecycle_contracts.py tests/browser/test_timing_waveform_contracts.py tests/browser/test_overlay_review_contracts.py tests/browser/test_practiscore_session_api.py tests/browser/test_practiscore_sync_controller.py`

Update when done:

- `../predev/tests/tasks.md`
- `../predev/tests/outcome.md`
- `../predev/tests/artifacts.md`
- `docs/tests/TEST_SUITE_GUIDE.md`
- `docs/project/browser-control-qa-matrix.md`
- `docs/project/browser-control-coverage-plan.md`
- `docs/project/browser-full-e2e-qa-plan.md`
- `outcome.md`
- `artifacts.md`

Exit criteria:

- Stage-owned suites are explicit and their docs point at the right tests.

### VAL-005C — Carve and verify Match-owned suites

Depends on:

- `VAL-005A`

Can run in parallel with:

- `VAL-005B`
- `VAL-005D`

Allowed edit surface:

- `tests/browser/`
- `../predev/tests/tasks.md`
- `../predev/tests/outcome.md`
- `../predev/tests/artifacts.md`
- `docs/tests/TEST_SUITE_GUIDE.md`
- `docs/project/browser-control-qa-matrix.md`
- `docs/project/browser-control-coverage-plan.md`
- `docs/project/browser-full-e2e-qa-plan.md`
- `outcome.md`
- `artifacts.md`

Execute:

- [ ] Isolate or classify Match-owned lifecycle, lower-pane, recap, composite, and export tests.
- [ ] Split mixed tests if ownership is still ambiguous.
- [ ] Update owned-doc references for the moved or renamed Match tests.

Commands:

- Match collect-only pack: `./.venv/bin/python -m pytest --collect-only tests/browser/test_browser_interactions.py tests/browser/test_workspace_flows.py`
- Match lifecycle / workflow smoke pack: `./.venv/bin/python -m pytest tests/browser/test_browser_interactions.py -k "match_workspace or composite or batch_export or recap" tests/browser/test_workspace_flows.py -k "open_project_inside_saved_workspace_auto_attaches_stage_membership or save_project_without_saved_workspace_auto_creates_unsaved_match_membership or angle_director or workspace_recap_render_uses_transition_and_result_cards"`

Update when done:

- `../predev/tests/tasks.md`
- `../predev/tests/outcome.md`
- `../predev/tests/artifacts.md`
- `docs/tests/TEST_SUITE_GUIDE.md`
- `docs/project/browser-control-qa-matrix.md`
- `docs/project/browser-control-coverage-plan.md`
- `docs/project/browser-full-e2e-qa-plan.md`
- `outcome.md`
- `artifacts.md`

Exit criteria:

- Match-owned suites are explicit and their docs point at the right tests.

### VAL-005D — Carve and verify Performance-owned suites

Depends on:

- `VAL-005A`

Can run in parallel with:

- `VAL-005B`
- `VAL-005C`

Allowed edit surface:

- `tests/browser/`
- `tests/export/`
- `../predev/tests/tasks.md`
- `../predev/tests/outcome.md`
- `../predev/tests/artifacts.md`
- `docs/tests/TEST_SUITE_GUIDE.md`
- `docs/project/browser-control-qa-matrix.md`
- `docs/project/browser-control-coverage-plan.md`
- `docs/project/browser-full-e2e-qa-plan.md`
- `outcome.md`
- `artifacts.md`

Execute:

- [ ] Isolate or classify Performance-owned library, analytics, notes/tags, settings, backup, and export tests.
- [ ] Split mixed tests if ownership is still ambiguous.
- [ ] Update owned-doc references for the moved or renamed Performance tests.

Commands:

- Performance collect-only pack: `./.venv/bin/python -m pytest --collect-only tests/browser/test_browser_interactions.py tests/browser/test_library_backend_contracts.py tests/export/test_export.py tests/export/test_merge_export_contracts.py`
- Performance owned-suite smoke pack: `./.venv/bin/python -m pytest tests/browser/test_browser_interactions.py -k "performance_library" tests/browser/test_library_backend_contracts.py tests/export/test_export.py tests/export/test_merge_export_contracts.py`

Update when done:

- `../predev/tests/tasks.md`
- `../predev/tests/outcome.md`
- `../predev/tests/artifacts.md`
- `docs/tests/TEST_SUITE_GUIDE.md`
- `docs/project/browser-control-qa-matrix.md`
- `docs/project/browser-control-coverage-plan.md`
- `docs/project/browser-full-e2e-qa-plan.md`
- `outcome.md`
- `artifacts.md`

Exit criteria:

- Performance-owned suites are explicit and their docs point at the right tests.

### VAL-005E — Sync shared suites, fixtures, runner docs, and CI references

Depends on:

- `VAL-005B`
- `VAL-005C`
- `VAL-005D`

Must stay serialized before:

- `VAL-005F`

Allowed edit surface:

- `tests/`
- `scripts/testing/run_test_suite.py`
- `docs/tests/TEST_SUITE_GUIDE.md`
- `docs/project/browser-control-qa-matrix.md`
- `docs/project/browser-control-coverage-plan.md`
- `docs/project/browser-full-e2e-qa-plan.md`
- `.github/workflows/test-macos.yml`
- `.github/workflows/test-windows.yml`
- `.github/workflows/test-linux.yml`
- `../predev/tests/tasks.md`
- `../predev/tests/outcome.md`
- `../predev/tests/artifacts.md`
- `outcome.md`
- `artifacts.md`

Execute:

- [ ] Keep shared-shell/backend suites limited to truly shared behavior.
- [ ] Update fixture/helper placement if app-specific helpers still live in shared lanes.
- [ ] Update the canonical runner docs and CI references to match the owned suite structure.
- [ ] Update QA/docs references when control/test ownership changed.

Commands:

- Runner inventory refresh: `uv run python scripts/testing/run_test_suite.py --list`
- Browser audit smoke pack: `./.venv/bin/python -m pytest tests/browser/test_browser_control_coverage_matrix.py tests/browser/test_browser_control_inventory_audit.py`
- Cross-lane collect-only sanity check: `./.venv/bin/python -m pytest --collect-only tests/browser tests/persistence tests/analysis`

Update when done:

- `../predev/tests/tasks.md`
- `../predev/tests/outcome.md`
- `../predev/tests/artifacts.md`
- `docs/tests/TEST_SUITE_GUIDE.md`
- `docs/project/browser-control-qa-matrix.md`
- `docs/project/browser-control-coverage-plan.md`
- `docs/project/browser-full-e2e-qa-plan.md`
- `.github/workflows/test-macos.yml`
- `.github/workflows/test-windows.yml`
- `.github/workflows/test-linux.yml`
- `outcome.md`
- `artifacts.md`

Exit criteria:

- The runner, docs, QA matrix, and CI references describe the same owned suite layout.

### VAL-005F — Close the source `predev/tests/` bundle

Depends on:

- `VAL-005E`

Must stay serialized before:

- `VAL-006`

Allowed edit surface:

- `../predev/tests/spec.md`
- `../predev/tests/tasks.md`
- `../predev/tests/outcome.md`
- `../predev/tests/artifacts.md`
- `docs/tests/TEST_SUITE_GUIDE.md`
- `outcome.md`
- `artifacts.md`

Execute:

- [ ] Close `TST-001` through `TST-009`.
- [ ] Confirm the source `predev/tests/` bundle is no longer a planning baseline.
- [ ] Confirm source `predev/tests/` and aggregate `testing/` remain clearly distinguished in all touched docs.

Commands:

- Owned-suite anchor: `uv run python scripts/testing/run_test_suite.py --suite browser --suite persistence --suite analysis --mode all-together --format table --json-output artifacts/test-suite-owned-lanes.json`

Update when done:

- `../predev/tests/spec.md`
- `../predev/tests/tasks.md`
- `../predev/tests/outcome.md`
- `../predev/tests/artifacts.md`
- `docs/tests/TEST_SUITE_GUIDE.md`
- `outcome.md`
- `artifacts.md`

Exit criteria:

- The source tests bundle is execution-complete and no longer just a planning lane.

## VAL-006 — Final acceptance gate and program signoff

Parallelization:

- Single-owner integrator only.

Read first:

- `../MASTER_STATUS.md`
- `../RECOVERY_NEXT_STEPS.md`
- every touched `../predev/*/outcome.md`
- every touched `../predev/*/artifacts.md`
- `outcome.md`
- `artifacts.md`

Execute:

- [ ] Confirm every mapped source-bundle final gate is closed.
- [ ] Confirm focused proof runs, owned suites, and the canonical full-suite anchor are recorded.
- [ ] Confirm screenshots, artifacts, QA/docs, and visual approvals are recorded where required.
- [ ] Confirm residual risks and waivers are explicitly recorded.
- [ ] Mark the aggregate `testing/` outcome as complete only when the program can genuinely close.

Commands:

- Runtime health: `uv run splitshot --check`
- Cross-doc audit pack: `./.venv/bin/python -m pytest tests/browser/test_browser_control_coverage_matrix.py tests/browser/test_browser_control_inventory_audit.py`
- Canonical full-suite anchor: `uv run python scripts/testing/run_test_suite.py --mode all-together --format table --json-output artifacts/current-all-together.json`

Update when done:

- `outcome.md`
- `artifacts.md`
- `../MASTER_STATUS.md` when program state changes
- `../RECOVERY_NEXT_STEPS.md` when the ordered work list changes
- every touched `../predev/*/outcome.md`
- every touched `../predev/*/artifacts.md`

Exit criteria:

- Every mapped source-bundle gate is closed.
- The repo has a fresh canonical suite anchor and recorded proof artifacts.
- The program can close without hidden blockers, ambiguous waivers, or missing evidence.
