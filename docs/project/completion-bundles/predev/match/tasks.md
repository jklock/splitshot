# Match Task Backlog

## Usage

- Treat each item as incomplete until its proof exists.
- Link implementation changes, test evidence, screenshots, and output artifacts in `outcome.md` and `artifacts.md`.
- Match is not done until the shared-shell contract, workflow truth, and output proof all agree.

## MCH-001 — Reset the Match contract

- [x] Rewrite the Match bundle docs around Stage-shell reuse.
- [x] Replace the standalone Match-app framing with the tile/info workflow contract.
- [x] Record Stage auto-seed and shared-shell ownership expectations.
- [x] Mark prior Match completion as historical rather than current signoff.

Progress note (`2026-05-25`):

- `plan.md`, `spec.md`, `tasks.md`, `outcome.md`, `artifacts.md`, and both Match prompts now describe Match as a Stage-shell variant.
- The bundle no longer treats a separate Match shell family as a requirement.

Depends on:

- none

Proof:

- Match bundle files updated

## MCH-002 — Reuse the Stage shell grammar

- [x] Move Match onto the same shell family as Stage.
- [ ] Preserve the persistent rail, right inspector, and lower-pane grammar end-to-end.
- [x] Remove Match-specific shell-family assumptions from docs/tests/code.
- [x] Keep footer order and shared-shell status behavior stable.

Progress note (`2026-05-24`):

- Match root markup now advertises the shared `stage-workspace` shell family and uses the shared rail/runtime helpers.
- The Match DOM/CSS/runtime now pin stage tiles in the main area, selected-stage truth in the lower pane, and workflow sections in the right-hand inspector.
- Proof, screenshots, and full interaction coverage for that new grammar are still pending before the checkbox can close.

Depends on:

- MCH-001

Proof:

- `src/splitshot/browser/static/index.html`
- `src/splitshot/browser/static/app.js`
- `tests/browser/test_automation_ui_shell_contracts.py`
- `tests/browser/test_browser_static_ui.py`
- `tests/browser/test_browser_rail_layout.py`

## MCH-003 — Align lifecycle and auto-seed behavior

- [x] Prove new/open/save workspace flow under the shared shell.
- [x] Prove stage add/remove/select behavior.
- [ ] Auto-create or attach Match membership when a Stage folder/project is opened.
- [x] Prove Stage open from Match and return to Match.

Progress note (`2026-05-24`):

- Match new/open/save, stage add/remove/select, and Stage open/return are covered by targeted browser interactions.
- Auto-seed / auto-attach from Stage project open/save into Match membership is now implemented in `src/splitshot/ui/controller.py`.
- Targeted controller tests were added in `tests/browser/test_workspace_flows.py`, but proof is still pending until the suite is actually run.

Depends on:

- MCH-001
- MCH-002

Proof:

- `tests/browser/test_browser_interactions.py::test_match_workspace_new_from_empty_and_stage_add_select_remove_flow`
- `tests/browser/test_browser_interactions.py::test_match_workspace_open_button_uses_picker_and_loads_saved_workspace`
- `tests/browser/test_browser_interactions.py::test_match_workspace_save_button_uses_picker_for_first_save`
- `tests/browser/test_browser_interactions.py::test_match_workspace_stage_open_and_shell_return_restore_match_context`

## MCH-004 — Build the tile and lower-info workflow

- [x] Render stage/media tiles in the main area.
- [ ] Use the lower pane for selected-tile information instead of the current section-driven flow everywhere the spec expects it.
- [ ] Keep Match workflow options fully right-inspector centric.
- [x] Preserve truthful defaults, overrides, setup-once, and apply-from-first behavior.

Progress note (`2026-05-24`):

- The tile/main-area workflow, setup-once flow, shared defaults, and per-stage overrides are covered.
- The selected-stage lower pane and right-inspector workflow routing are now implemented in code.
- The remaining gap is proof depth and artifact packaging for that new grammar.

Depends on:

- MCH-002
- MCH-003

Proof:

- `tests/browser/test_browser_interactions.py::test_match_workspace_setup_once_uses_preview_before_apply`
- `tests/browser/test_browser_interactions.py::test_match_workspace_shared_defaults_apply_and_reset`
- `tests/browser/test_browser_interactions.py::test_match_workspace_override_apply_and_reset_update_selected_stage`

## MCH-005 — Close recap, composite, export, and parity gaps

- [x] Prove recap stage selection, transition/result-card configuration, and render success/error paths.
- [x] Prove full composite clip reorder, edit, align, audio-mix, plan refresh, and cut-override behavior.
- [x] Prove batch export queue, recipe, progress, and completion/error behavior.
- [x] Implement Match parity gaps: recap merge controls, Auto Trim, Split Sync / Stage Mix orchestration, intro/title/watermark parity, and score-import expansion.

Progress note (`2026-05-24`):

- Recap success/error paths and batch export queue/result behavior are directly covered, and recap rendering now respects transition plus result-card selections.
- Composite coverage now includes reorder, inline role/sync/audio editing, plan refresh, apply-cut, and clear-cut behavior inside the existing lower-pane workflow.
- The parity sub-lane now inherits the implemented Stage parity work instead of a standing Stage deferral.

Depends on:

- MCH-003
- MCH-004

Proof:

- `tests/browser/test_browser_interactions.py::test_match_workspace_recap_reports_success_and_error_states`
- `tests/browser/test_browser_interactions.py::test_match_workspace_batch_export_queue_select_all_none_and_start`
- `tests/browser/test_browser_interactions.py::test_match_stage_composite_controls_update_composite_state`
- `tests/browser/test_browser_interactions.py::test_match_stage_composite_cut_override_editor_updates_plan_detail`
- `tests/browser/test_workspace_flows.py::test_workspace_recap_render_uses_transition_and_result_cards`
- `tests/browser/test_workspace_flows.py::test_angle_director_plan_merges_generated_cuts_with_persisted_override`
- `tests/browser/test_workspace_flows.py::test_angle_director_clear_cut_removes_only_requested_override`

## MCH-006 — Isolate Match settings and sync proof

- [x] Prove Match settings save and reload behavior.
- [x] Prove Match settings affect Match only.
- [x] Prove Match settings do not mutate Stage or Performance behavior.
- [x] Finish the Match doc/proof sync package, including dedicated user-facing Match documentation.

Progress note (`2026-05-24`):

- Match settings persistence and isolation are covered.
- QA/control docs, planning docs, and the dedicated user-facing Match guide now track the shared-shell contract.

Depends on:

- MCH-002
- MCH-005

Proof:

- `tests/browser/test_browser_interactions.py::test_match_settings_persist_locally_and_control_match_return_selection`
- `tests/browser/test_browser_interactions.py::test_performance_library_settings_remain_isolated_from_match_settings`
- `docs/project/browser-control-qa-matrix.md`
- `docs/project/browser-control-coverage-plan.md`
- `docs/project/browser-full-e2e-qa-plan.md`
- `docs/userfacing/USER_GUIDE.md`
- `docs/userfacing/workflow.md`
- `docs/userfacing/panes/match.md`

## MCH-007 — Match done gate

- [ ] Confirm Match-owned tests are green for the new contract.
- [ ] Confirm shared-shell/backend dependencies used by Match are green.
- [ ] Confirm recap/export artifacts exist for the new shell.
- [ ] Confirm Stage handoff/return and auto-seed behavior are proven.
- [ ] Confirm visual approval is recorded.

Depends on:

- MCH-006

Proof:

- `outcome.md` final gate marked complete
