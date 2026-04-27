# Remaining Coverage Work

Current status as of 2026-04-26:

- The browser coverage docs now include the exhaustive control inventory, the phase-gated full-browser E2E plan, and the wider QA matrix.
- The broad browser regression slice now reports 366 passed and 0 failed for the 14 browser targets in `tests/scripts/test_run_test_suite.py`.
- `tests/scripts/test_run_test_suite.py` was already updated to expect 14 browser targets.
- The missing-control test-authoring pass is now written. The new authored proof files are:
  - `tests/browser/test_browser_remaining_controls_e2e.py`
  - `tests/browser/test_settings_defaults_truth_gate.py`
  - `tests/browser/test_browser_full_app_e2e.py`
- The newly authored closeout suites were executed and remediated, and the failing scopes were rerun until green.
- The authored truth-gate scaffolds were graduated to real executable tests in the closeout suites (no `xfail` scaffolds remain in those files).
- The repo can now truthfully report that the previously documented browser-coverage closeout items were validated in browser test execution.

Status update from the latest remediation rerun on 2026-04-27:

- The authored closeout suites were rerun and remediated through the remaining broad-slice flakes.
- The broader browser slice was rerun in context across 16 browser files.
- Latest full-slice result observed in this pass: 388 passed, 0 failed.
- The previously failing scopes were remediated and revalidated in both targeted reruns and the broad rerun.
- The repo can now truthfully claim the browser-coverage closeout validation is green for this pass.

The authoritative control inventory is still in [browser-control-coverage-plan.md](docs/project/browser-control-coverage-plan.md), and the truth boundary for a full-app claim is still in [browser-full-e2e-qa-plan.md](docs/project/browser-full-e2e-qa-plan.md).

This file tracks what was authored, where the proof lives, and the validation state that closed the remaining browser-coverage gap.

## Authored Proof For The Former Remaining Gaps

### Waveform And Scoring Shell

Former remaining items:

- `Zoom -`
- `Zoom +`
- `Amp -`
- `Amp +`
- `Reset waveform view`
- `Expand waveform`
- `Splits Edit / Collapse toggle`
- `Score Edit / Collapse toggle`

Authored proof:

- `tests/browser/test_browser_remaining_controls_e2e.py`
- `test_waveform_shell_remaining_controls_and_workbench_toggles_survive_routes`

Status:

- Test coverage is authored.
- Validation completed in browser test runs on 2026-04-26.

### Markers, Review, Overlay, And Color Picker

Former remaining items:

- popup template `Enabled`
- popup bubble authoring: `name`, `text`, `content type`, `image path`, `image browse`, `image scale`, `start mode`, `start time`, `shot`, `duration`, `follow motion`, `keyframes`, `copy previous motion`, `apply to shown shot popups`, `clear path`, `placement`, `X/Y`, `width/height`
- review text box `background color`, `text color`, `opacity`
- overlay styling `font family`
- badge-style-grid per-badge `background`, `text`, and `opacity` for `timer`, `shot`, `current shot`, and `score`
- color picker modal `Done`, backdrop dismiss, `hue`, `saturation`, `lightness`, `hex input`, and swatch apply

Authored proof:

- `tests/browser/test_browser_remaining_controls_e2e.py`
- `test_markers_template_toggle_and_popup_bubble_authoring_controls_commit_state`
- `test_review_text_box_style_controls_and_color_picker_modal_commit_preview`
- `test_overlay_badge_style_grid_applies_timer_shot_current_and_score_styles`

Status:

- Test coverage is authored.
- Validation completed in browser test runs on 2026-04-26.

### PiP And Merge

Former remaining items:

- `Enable added media export`
- `Layout select`
- default PiP `size`
- default PiP `X`
- default PiP `Y`
- merge-media-card `collapse`
- merge-media-card `remove`
- merge-media-card `size`
- merge-media-card `opacity`
- merge-media-card `position`
- merge-media-card sync nudges: `-10`, `-1`, `+1`, `+10`

Authored proof:

- `tests/browser/test_browser_remaining_controls_e2e.py`
- `test_merge_remaining_controls_commit_default_and_per_source_state`

Status:

- Test coverage is authored.
- Validation completed in browser test runs on 2026-04-26.

### Export

Former remaining items:

- `Quality`
- `Aspect ratio`
- `Dimensions` (`width` and `height`)
- `Frame rate`
- `Video codec`
- `Video bitrate`
- `Audio codec`
- `Audio sample rate`
- `Audio bitrate`
- `Color space`
- `FFmpeg preset`
- `Two-pass`

Authored proof:

- `tests/browser/test_browser_remaining_controls_e2e.py`
- `test_export_remaining_encoding_controls_drive_export_payload`

Status:

- Test coverage is authored.
- Validation completed in browser test runs on 2026-04-26.

### Settings Defaults

Former remaining items:

- `Save scope`
- `Landing pane`
- `Reopen selected pane on new projects`
- PiP defaults: `PiP layout`, `PiP size`, `PiP X`, `PiP Y`
- overlay defaults: `Overlay position`, `Badge size`, stage box `background color`, stage box `text color`, stage box `opacity`, timer badge `background color`, timer badge `text color`, timer badge `opacity`, shot badge `background color`, shot badge `text color`, shot badge `opacity`, current shot badge `background color`, current shot badge `text color`, current shot badge `opacity`, score badge `background color`, score badge `text color`, score badge `opacity`
- marker defaults: `Enabled`, `Content type`, `Text source`, `Duration`, `Quadrant`, `Width`, `Height`, `Follow motion`, `Background color`, `Text color`, `Opacity`
- export defaults: `Export quality`, `Export preset`, `Frame rate`, `Video codec`, `Audio codec`, `Color space`, `FFmpeg preset`, `Two-pass`

Authored proof:

- `tests/browser/test_settings_defaults_truth_gate.py`
- `test_settings_defaults_seed_fresh_project_overlay_marker_export_pip_and_shotml_state`
- `test_settings_landing_pane_and_reopen_last_tool_apply_after_reload`
- `test_settings_scope_separates_app_and_folder_defaults_for_new_projects`

Status:

- Test coverage is authored.
- The fresh-project seeding proof is authored directly.
- The landing-pane/reopen-last-tool and scope-separation cases are now executable and validated in browser test runs on 2026-04-26.

### ShotML

Former remaining items:

- threshold: `cutoff base`, `cutoff span`
- beep detection: `onset fraction`, `search lead ms`, `tail guard ms`, `fallback window ms`, `FFT window s`, `FFT hop s`, `FFT band min Hz`, `FFT band max Hz`, `fallback multiplier`, `tonal window ms`, `tonal hop ms`, `tonal band min Hz`, `tonal band max Hz`, `refine pre ms`, `refine post ms`, `gap before first shot ms`, `exclusion radius ms`, `region cutoff base`, `region threshold weight`, `model boost floor`
- shot candidate detection: `minimum shot interval ms`, `peak minimum spacing ms`, `confidence source`
- shot refinement: `onset fraction`, `pre-window ms`, `post-window ms`, `midpoint clamp padding ms`, `minimum search window ms`, `RMS window ms`, `RMS hop ms`
- false positive suppression: `weak onset threshold`, `near-cutoff interval ms`, `confidence weight`, `support weight`, `weak support penalty`, `suppress close-pair duplicates`, `suppress sound-profile outliers`
- confidence and review: `refinement confidence weight`, `support pre ms`, `support post ms`, `support RMS window ms`, `support RMS hop ms`, `alignment divisor ms`, `alignment multiplier`, `profile search radius ms`, `profile distance limit`, `profile high confidence limit`
- advanced runtime: `window size`, `hop size`

Authored proof:

- `tests/browser/test_browser_remaining_controls_e2e.py`
- `test_shotml_remaining_numeric_controls_commit_from_browser`
- `test_shotml_section_toggles_persist_routes_and_proposal_actions_apply_or_discard`
- `tests/browser/test_settings_defaults_truth_gate.py`
- `test_settings_defaults_seed_fresh_project_overlay_marker_export_pip_and_shotml_state`

Status:

- Test coverage is authored.
- Validation completed in browser test runs on 2026-04-26.

### Full-App E2E Truth Gate

Former remaining items:

1. Fix the master browser workflow so it selects a visible shot from the Project-pane path instead of a hidden waveform card.
2. Create or open a project, import PractiScore, adjust timing, edit scores, save, reload, and verify persistence.
3. Add and edit markers, review boxes, and overlay settings, then render an export and confirm preview and export parity.
4. Add PiP media, tune merge settings, export, and confirm rendered placement and sync.
5. Change global defaults, create a fresh project, and verify the new project starts with the chosen defaults.
6. Change ShotML settings, rerun analysis, apply or discard proposals, and confirm downstream timing changes.

Authored proof:

- `tests/browser/test_browser_full_app_e2e.py`
- `_select_first_waveform_shot(page)` now selects the visible timing-table row path rather than a hidden waveform card.
- `test_browser_full_app_e2e_calls_surface_workflows`
- `test_browser_full_app_practiscore_timing_scoring_save_reload_persistence_truth_gate`
- `test_browser_full_app_markers_review_overlay_export_preview_parity_truth_gate`
- `test_browser_full_app_merge_export_sync_truth_gate`
- `test_browser_full_app_settings_defaults_seed_fresh_project_truth_gate`
- `test_browser_full_app_shotml_rerun_apply_or_discard_truth_gate`

Status:

- The full-app workflow and truth-gate scenarios are authored and executed.
- The truth-gate scenarios are now validated in `tests/browser/test_browser_full_app_e2e.py` without `xfail` scaffolds.

## What Still Actually Remains

No unresolved blockers remain from this closeout pass.

Validated closeout evidence:

1. Newly authored suites executed and green:
	- `tests/browser/test_browser_remaining_controls_e2e.py`
	- `tests/browser/test_settings_defaults_truth_gate.py`
	- `tests/browser/test_browser_full_app_e2e.py`
2. Broader browser regression slice rerun in context:
	- 16 browser files executed in this remediation pass
	- latest broad rerun snapshot: 388 passed, 0 failed
3. Truth-gate scenarios are executable tests (no `xfail` scaffolds remain in the authored closeout suite files).

The remaining work from this specific browser-coverage closeout pass is complete.