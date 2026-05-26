# Stage Task Backlog

## Usage

- Treat each item as incomplete until the listed proof exists.
- Link implementation changes, test runs, screenshots, and doc updates in `outcome.md` and `artifacts.md`.
- Do not count placeholder UI or route presence alone as completion.

## STG-001 — Reset the Stage contract

- [x] Rewrite the Stage bundle docs around the Stage-first shell.
- [x] Record the required workflow order.
- [x] Record the shared-shell ownership rule for Match and Performance.
- [x] Mark the prior completion framing as superseded by the redesign.

Progress note (`2026-05-25`):

- `plan.md`, `spec.md`, `tasks.md`, `outcome.md`, `artifacts.md`, and both Stage prompts now describe Stage as the canonical shell and workflow contract.
- The bundle no longer treats Match and Performance as separate shell families.
- The contract-reset documentation lane is complete.

Depends on:

- none

Proof:

- Stage bundle files updated

## STG-002 — Remove Project automation clutter

- [x] Remove the current Stage Automation dump from Project.
- [x] Keep Project focused on setup, import, and PractiScore.
- [x] Redistribute displaced controls to Compose, Review, Export, or other logical steps.
- [x] Ensure no dead placeholder cards remain in Project.

Progress note (`2026-05-24`):

- `src/splitshot/browser/static/index.html` and the owned browser/static contracts keep the Project pane focused on setup, primary import, and PractiScore.
- Reusable output, review, and Compose controls now live in their owning panes instead of as dead Project clutter.
- The fake multi-angle launcher/editor is gone; Compose media cards now own per-source angle-role management directly in the editing flow.
- The user-facing Project guide reflects the setup-only workflow.

Depends on:

- STG-001

Proof:

- `tests/browser/test_browser_static_ui.py`
- `tests/browser/test_browser_interactions.py::test_project_pane_practiscore_and_primary_controls_enable_after_project_create`
- `tests/browser/test_browser_interactions.py::test_project_pane_manual_practiscore_file_import_remains_functional_with_active_project`
- `tests/browser/test_merge_export_contracts.py`
- `tests/browser/test_browser_control.py`
- `tests/browser/test_browser_remaining_controls_e2e.py`
- `docs/userfacing/panes/project.md`
- `docs/userfacing/panes/pip.md`

## STG-003 — Harden the shared Stage shell

- [x] Normalize the shell primitives Match and Performance must reuse.
- [x] Preserve preview dominance, right inspector, and lower info pane behavior in the Stage shell.
- [x] Remove separate-shell assumptions from the shared layout/runtime code.
- [x] Keep footer order and shared-shell status behavior stable.

Progress note (`2026-05-24`):

- Stage, Match, and Performance roots now advertise the shared `stage-workspace` shell family in `index.html`.
- `workspaceShell(viewName)` and the shared rail-collapse selectors removed stale shell-family branching from the runtime and layout CSS.
- The shell/browser slice is green against the updated contract.

Depends on:

- STG-001

Proof:

- `src/splitshot/browser/static/index.html`
- `src/splitshot/browser/static/app.js`
- `src/splitshot/browser/static/styles/layout.css`
- `tests/browser/test_automation_ui_shell_contracts.py`
- `tests/browser/test_browser_static_ui.py`
- `tests/browser/test_browser_rail_layout.py`

## STG-004 — Fix import, home-path, and output defaults

- [x] Make the selected project folder the default home for file pickers, excluding primary-video import.
- [x] Rename and implement `Import Primary Video` as a copy into the project Import folder.
- [x] Default Stage export output to the project Output folder.
- [x] Preserve the protected PractiScore fallback/session/sync contract.

Progress note (`2026-05-24`):

- Project-folder-aware picker defaults and the project JSON/folder probe behavior are covered by lifecycle tests.
- `Import Primary Video` is the Stage-owned import path and copies media into the project `Input` folder.
- Blank export output defaults resolve to the project `Output` folder.
- Manual PractiScore fallback plus session/sync payload behavior remain under direct browser coverage.

Depends on:

- STG-002

Proof:

- `tests/browser/test_project_lifecycle_contracts.py::test_project_folder_probe_and_project_json_path_use_same_folder`
- `tests/browser/test_merge_export_contracts.py::test_project_open_defaults_blank_export_output_path_to_project_output_folder`
- `tests/browser/test_browser_interactions.py::test_project_pane_practiscore_and_primary_controls_enable_after_project_create`
- `tests/browser/test_browser_interactions.py::test_project_pane_manual_practiscore_file_import_remains_functional_with_active_project`

## STG-005 — Close Compose, Review, marker, and top-bar regressions

- [x] Show the secondary waveform beneath the primary waveform/info lane when added media exists.
- [x] Default Review added media on when added media exists.
- [x] Keep Review Splits, Score, and Overlay enabled by default.
- [x] Fix secondary preview lag/drift.
- [x] Restore imported/custom summary authoring.
- [x] Finish the exact two-column Review styling proof / adjustment lane.
- [x] Separate marker styling from overlay styling.
- [x] Keep the status/progress bar inside the top bar.

Progress note (`2026-05-24`):

- `waveform.js` now renders a stacked secondary waveform lane whenever analyzed added media exists, and the timing/waveform browser suite proves the lane flips from `single` to `stacked` after merge analysis.
- Review added-media defaults remain on via the Stage UI-state defaults, and overlay visibility defaults still keep Splits, Score, and Overlay enabled by default.
- Secondary preview sync hardening remains covered by merge/export contracts.
- Imported summary authoring, marker-vs-overlay separation, top-bar containment, and the Review two-column style-card layout are now covered by focused static/browser proof.

Depends on:

- STG-003
- STG-004

Proof:

- `tests/browser/test_browser_static_ui.py::test_browser_ui_uses_hard_edged_contiguous_tool_shell`
- `tests/browser/test_browser_interactions.py::test_review_text_box_style_controls_use_two_column_layout`
- `tests/browser/test_browser_interactions.py::test_review_text_box_color_swatches_and_opacity_update_live_preview`

- `tests/browser/test_timing_waveform_contracts.py`
- `tests/browser/test_merge_export_contracts.py::test_app_merge_export_commit_and_log_freshness_contracts`
- `tests/browser/test_overlay_review_contracts.py::test_imported_summary_defaults_and_above_final_contract_are_source_visible`
- `tests/browser/test_overlay_review_contracts.py::test_review_text_box_auto_size_is_independent_of_global_bubble_size`
- `tests/browser/test_browser_rail_layout.py::test_status_bar_hosts_layout_lock_and_processing_bar_fills_top_row`

## STG-006 — Close Stage-owned parity gaps

- [x] Implement Stage Auto Trim.
- [x] Close or truthfully defer Compose layout parity beyond the current picture-in-picture / side-by-side / above-below coverage.
- [x] Close or truthfully defer Match composite parity beyond the current Angle Director + override workflow.
- [x] Close animated/logo-capable intro title-card parity.
- [x] Close image/text watermark parity.
- [x] Implement score-import coverage for the in-scope PractiScore disciplines (IDPA / USPSA / Steel Challenge) across local CSV/TXT import and remote normalization.

Progress note (`2026-05-24`):

- Stage Auto Trim is implemented via run-window resolution from the start beep and final shot.
- Compose now closes the requested layout parity through `Side by side`, `Above / below`, `Picture in picture`, `Full-screen portrait`, `Dual center HUD`, and `Dual top HUD` across Stage preview, export planning, and saved defaults.
- Match composite parity now closes through Match-owned composite orchestration: clip reorder, per-clip role/sync/audio controls, plan review, persisted cut overrides, and override-clear routing all land in the existing lower-pane workflow instead of a stray side flow.
- Opening Title now supports richer composition through the saved output-profile payload (`match`, `stage`, `shooter`, `division`, `classification`, `date`, `custom title`, and `custom subtitle` when present), plus animation mode and a local logo file.
- Your Logo now supports text, image, or image-plus-text rendering with position, opacity, font/color sizing, and full-export visibility when duration is set to `0`.
- PractiScore import now covers the in-scope disciplines end-to-end: IDPA, USPSA, and Steel Challenge all resolve through the Project pane, local CSV/TXT import, and remote artifact normalization.
- Legacy IPSC compatibility remains tolerated in the parser, but it is no longer treated as part of the Stage parity target.

Depends on:

- STG-002
- STG-003

Proof:

- `src/splitshot/ui/controller.py`
- `src/splitshot/browser/static/app.js`
- `src/splitshot/browser/static/index.html`
- `src/splitshot/browser/static/views/match-view.js`
- `src/splitshot/export/pipeline.py`
- `src/splitshot/merge/layouts.py`
- `src/splitshot/overlay/render.py`
- `src/splitshot/scoring/practiscore.py`
- `src/splitshot/scoring/practiscore_sync_normalize.py`
- `src/splitshot/scoring/practiscore_web_extract.py`
- `src/splitshot/overlay/render.py`
- `tests/export/test_export.py`
- `tests/analysis/test_practiscore_import.py`
- `tests/analysis/test_practiscore_sync_normalize.py`
- `tests/analysis/test_practiscore_web_extract.py`
- `tests/browser/test_browser_control.py`
- `tests/browser/test_browser_static_ui.py`
- `docs/userfacing/panes/project.md`
- `docs/userfacing/panes/settings.md`
- `docs/userfacing/panes/export.md`
- `docs/project/completion-bundles/predev/newfeatures/from-shooting-cut.md`

## STG-007 — Sync tests, docs, and proof

- [x] Update Stage-owning browser tests and audits.
- [x] Update the QA matrix, coverage-plan / full-browser-E2E references, and user-facing Stage / Project docs for the redistributed flow.
- [x] Capture refreshed Stage screenshots and artifact notes for the redistributed flow.

Progress note (`2026-05-24`):

- The shell contracts, rail layout tests, timing/waveform contracts, and owned interaction slices reflect the current Stage shell and Project redistribution.
- The QA matrix, coverage plan, full browser E2E plan, and user-facing Project/guide docs are aligned with the shared-shell Stage contract.
- The repo-owned screenshot generator refreshed the documented Stage screenshot set in `docs/screenshots/`, including the Project, Settings, Review, Export, Metrics, Compose, Score, Splits, ShotML, and marker captures.

Depends on:

- STG-004
- STG-005
- STG-006

Proof:

- `tests/browser/test_automation_ui_shell_contracts.py`
- `tests/browser/test_browser_static_ui.py`
- `tests/browser/test_browser_rail_layout.py`
- `tests/browser/test_timing_waveform_contracts.py`
- `tests/browser/test_browser_control_coverage_matrix.py`
- `docs/project/browser-control-qa-matrix.md`
- `docs/project/browser-control-coverage-plan.md`
- `docs/project/browser-full-e2e-qa-plan.md`
- `docs/userfacing/USER_GUIDE.md`
- `docs/userfacing/panes/project.md`

## STG-008 — Stage done gate

- [x] Confirm Stage-owned tests are green for the full new contract.
- [x] Confirm Match and Performance reuse no longer depends on a stale Stage shell contract.
- [x] Confirm all required artifacts exist.
- [x] Confirm visual approval is recorded.
- [x] Confirm no undocumented Stage-visible regressions remain open.

Progress note (`2026-05-25`):

- `./.venv/bin/splitshot --check` exited `0`.
- Targeted closeout verification exited `0` with `42 passed in 99.04s (0:01:39)` across `tests/browser/test_automation_ui_shell_contracts.py`, `tests/browser/test_browser_static_ui.py`, `tests/browser/test_browser_control_inventory_audit.py`, `tests/browser/test_browser_control_coverage_matrix.py`, `tests/browser/test_browser_remaining_controls_e2e.py::test_merge_remaining_controls_commit_default_and_per_source_state`, `tests/browser/test_browser_full_app_e2e.py::test_browser_full_app_merge_export_sync_truth_gate`, `tests/browser/test_browser_full_app_e2e.py::test_browser_full_app_settings_defaults_seed_fresh_project_truth_gate`, `tests/browser/test_browser_interactions.py::test_match_workspace_shell_keeps_selected_stage_detail_and_workflow_visible`, `tests/browser/test_browser_interactions.py::test_match_stage_composite_controls_update_composite_state`, and `tests/browser/test_browser_interactions.py::test_match_stage_composite_cut_override_editor_updates_plan_detail`.
- The required Stage screenshot package was re-verified as present and non-empty via `stage_screenshots_ok`.
- Live browser validation on `http://127.0.0.1:8765/` confirmed the Compose rail label plus the final Stage wording for Settings (`Landing pane` -> `Compose`, `Picture in picture`, `No saved added-media defaults.`) and Review (`Show added media`).
- No new Stage-visible regressions were found during diagnostics, the targeted browser slice, or the live visual pass.

Depends on:

- STG-007

Proof:

- `outcome.md` final gate marked complete
- `artifacts.md` final done-gate closeout artifact recorded
