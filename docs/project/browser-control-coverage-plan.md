# Browser Control Coverage Plan

Audited against `src/splitshot/browser/static/index.html` on 2026-05-02.

This is the exhaustive mutable-control worklist for the current browser shell. It exists so later modularization tasks can keep browser-visible controls, control ids, and QA ownership explicit while preserving zero UX drift.

For the phase-gated execution plan that defines what counts as truthful full-control end-to-end coverage, see [browser-full-e2e-qa-plan.md](browser-full-e2e-qa-plan.md).
A full-app end-to-end QA claim requires satisfying the stricter exit criteria in [browser-full-e2e-qa-plan.md](browser-full-e2e-qa-plan.md).

The current static inventory contains 265 audited mutable identifiers. `tests/browser/test_browser_control_inventory_audit.py` is the guard that keeps this document synchronized with the live browser shell.

## How to use this plan

- Treat every identifier below as part of the live browser contract.
- When a visible control changes, update this document, [browser-control-qa-matrix.md](browser-control-qa-matrix.md), and the owning tests in the same change.
- Preserve the Project-pane manual `Select PractiScore File` fallback and the local `Match type`, `Stage #`, `Competitor name`, and `Place` controls unless product direction explicitly removes them.
- Use this document for exhaustive identifier ownership. Use the QA matrix for the summarized surface-to-suite map.

## Shared shell and global chrome

### Shared shell identifiers

- Layout and rail controls: `id:resize-rail`, `id:resize-sidebar`, `id:resize-waveform`, `id:toggle-rail`, `id:toggle-layout-lock-video`
- Shared color-picker modal: `id:close-color-picker`, `id:color-picker-hue`, `id:color-picker-saturation`, `id:color-picker-lightness`, `id:color-picker-hex`

### Shared shell suite anchors

- `tests/browser/test_browser_static_ui.py`
- `tests/browser/test_browser_rail_layout.py`
- `tests/browser/test_browser_interactions.py`
- `tests/browser/test_browser_full_app_e2e.py`

## Project / import

### Project identifiers

- Tool routing: `data-tool:project`, `data-tool-pane:project`
- Project folder lifecycle: `id:project-path`, `id:browse-project-path`, `id:new-project`, `id:delete-project`
- Saved metadata: `id:project-name`, `id:project-description`
- PractiScore actions: `id:open-practiscore-dashboard`, `id:import-practiscore`, `id:practiscore-file-input`
- PractiScore local context: `id:match-type`, `id:match-stage-number`, `id:match-competitor-name`, `id:match-competitor-place`
- Primary import path: `id:primary-file-input`, `id:primary-file-path`, `id:browse-primary-path`

### Project suite anchors

- `tests/browser/test_browser_control.py`
- `tests/browser/test_project_lifecycle_contracts.py`
- `tests/browser/test_browser_interactions.py`
- `tests/browser/test_practiscore_session_api.py`
- `tests/browser/test_practiscore_sync_controller.py`
- `tests/browser/test_browser_full_app_e2e.py`

## PiP / merge

### PiP / merge identifiers

- Tool routing: `data-tool:merge`, `data-tool-pane:merge`
- Merge media intake: `id:add-merge-media`, `id:merge-media-input`
- Merge defaults: `id:merge-enabled`, `id:merge-layout`, `id:restore-merge-defaults`
- Default PiP placement: `id:pip-size`, `id:pip-x`, `id:pip-y`

### PiP / merge suite anchors

- `tests/browser/test_merge_export_contracts.py`
- `tests/browser/test_browser_remaining_controls_e2e.py`
- `tests/browser/test_browser_full_app_e2e.py`
- `tests/export/test_export.py`

## Score

### Score identifiers

- Tool routing: `data-tool:scoring`, `data-tool-pane:scoring`
- Compact controls: `id:scoring-enabled`, `id:scoring-preset`, `id:expand-scoring`
- Expanded workbench closeout: `id:collapse-scoring`

### Score suite anchors

- `tests/browser/test_scoring_metrics_contracts.py`
- `tests/browser/test_metrics_e2e.py`
- `tests/browser/test_browser_remaining_controls_e2e.py`
- `tests/browser/test_browser_full_app_e2e.py`

## Splits / waveform

### Splits / waveform identifiers

- Tool routing: `data-tool:timing`, `data-tool-pane:timing`
- Compact controls: `id:timing-enabled`, `id:expand-timing`
- Expanded timing workbench: `id:collapse-timing`, `id:timing-event-kind`, `id:timing-event-label`, `id:timing-event-position`, `id:add-timing-event`
- Waveform controls: `id:zoom-waveform-in`, `id:zoom-waveform-out`, `id:amp-waveform-in`, `id:amp-waveform-out`, `id:reset-waveform-view`, `id:expand-waveform`

### Splits / waveform suite anchors

- `tests/browser/test_timing_waveform_contracts.py`
- `tests/browser/test_browser_interactions.py`
- `tests/browser/test_browser_remaining_controls_e2e.py`
- `tests/browser/test_metrics_e2e.py`
- `tests/browser/test_browser_full_app_e2e.py`

## Markers

### Markers identifiers

- Tool routing: `data-tool:markers`, `data-tool-pane:markers`
- Compact controls: `id:markers-enable`, `id:popup-edit-selected`, `id:popup-add-bubble`
- Workbench controls: `id:popup-add-bubble-workbench`, `id:popup-add-selected-shot-workbench`, `id:popup-import-shots-workbench`, `id:markers-workbench-filter`, `id:popup-prev-workbench`, `id:popup-next-workbench`

### Markers suite anchors

- `tests/browser/test_overlay_review_contracts.py`
- `tests/browser/test_browser_interactions.py`
- `tests/browser/test_browser_remaining_controls_e2e.py`
- `tests/browser/test_browser_full_app_e2e.py`

## Review

### Review identifiers

- Tool routing: `data-tool:review`, `data-tool-pane:review`
- Show-box visibility toggles: `id:show-markers`, `id:show-pip`, `id:show-timer`, `id:show-draw`, `id:show-shots`, `id:show-score`
- Review text-box entry points: `id:review-add-text-box`, `id:review-add-imported-box`

### Review suite anchors

- `tests/browser/test_overlay_review_contracts.py`
- `tests/browser/test_browser_interactions.py`
- `tests/browser/test_browser_remaining_controls_e2e.py`
- `tests/browser/test_browser_full_app_e2e.py`
- `tests/export/test_export.py`

## Overlay

### Overlay identifiers

- Tool routing: `data-tool:overlay`, `data-tool-pane:overlay`
- Overlay visibility and stack: `id:show-overlay`, `id:badge-size`, `id:overlay-style`, `id:overlay-spacing`, `id:overlay-margin`, `id:max-visible-shots`, `id:shot-quadrant`, `id:shot-direction`
- Custom shot-stack placement: `id:overlay-custom-x`, `id:overlay-custom-y`
- Timer badge placement: `id:timer-x`, `id:timer-y`, `id:timer-lock-to-stack`
- Draw badge placement: `id:draw-x`, `id:draw-y`, `id:draw-lock-to-stack`
- Score badge placement: `id:score-x`, `id:score-y`, `id:score-lock-to-stack`
- Bubble and font controls: `id:bubble-width`, `id:bubble-height`, `id:overlay-font-family`, `id:overlay-font-size`, `id:overlay-font-bold`, `id:overlay-font-italic`

### Overlay suite anchors

- `tests/browser/test_overlay_review_contracts.py`
- `tests/browser/test_browser_interactions.py`
- `tests/browser/test_browser_remaining_controls_e2e.py`
- `tests/browser/test_browser_full_app_e2e.py`
- `tests/export/test_export.py`

## Metrics

### Metrics identifiers

- Tool routing: `data-tool:metrics`, `data-tool-pane:metrics`
- Compact and expanded controls: `id:expand-metrics`, `id:collapse-metrics`
- Export actions: `id:metrics-export-csv`, `id:metrics-export-text`

### Metrics suite anchors

- `tests/browser/test_metrics_e2e.py`
- `tests/browser/test_scoring_metrics_contracts.py`
- `tests/browser/test_browser_full_app_e2e.py`

## Export

### Export identifiers

- Tool routing: `data-tool:export`, `data-tool-pane:export`
- Export quality and frame controls: `id:export-preset`, `id:quality`, `id:aspect-ratio`, `id:target-width`, `id:target-height`, `id:frame-rate`
- Codec controls: `id:video-codec`, `id:video-bitrate`, `id:audio-codec`, `id:audio-sample-rate`, `id:audio-bitrate`, `id:color-space`, `id:ffmpeg-preset`, `id:two-pass`
- Output path and actions: `id:export-path`, `id:browse-export-path`, `id:export-video`, `id:show-export-log`, `id:close-export-log`, `id:export-export-log`

### Export suite anchors

- `tests/browser/test_merge_export_contracts.py`
- `tests/browser/test_browser_remaining_controls_e2e.py`
- `tests/browser/test_browser_full_app_e2e.py`
- `tests/export/test_export.py`

## Settings

### Global settings selectors

- Tool routing and rail entry point: `data-tool:settings`, `data-tool-pane:settings`, `id:settings-rail-button`

### Global template section

- Section selector: `data-settings-section:global-template`
- Controls: `id:settings-scope`, `id:settings-default-tool`, `id:settings-reopen-last-tool`, `id:settings-import-current`, `id:settings-reset-defaults`

### Layout section

- Section selector: `data-settings-section:layout`
- Controls: `id:settings-layout-locked`, `id:settings-layout-rail-width`, `id:settings-layout-inspector-width`, `id:settings-layout-waveform-height`, `id:settings-use-current-layout`, `id:settings-release-layout`

### Scoring defaults section

- Section selector: `data-settings-section:scoring`
- Controls: `id:settings-default-match-type`

### PiP defaults section

- Section selector: `data-settings-section:pip`
- Controls: `id:settings-merge-layout`, `id:settings-pip-size`, `id:settings-merge-pip-x`, `id:settings-merge-pip-y`

### Overlay defaults section

- Section selector: `data-settings-section:overlay`
- Controls: `id:settings-overlay-position`, `id:settings-badge-size`, `id:settings-overlay-custom-background-color`, `id:settings-overlay-custom-text-color`, `id:settings-overlay-custom-opacity`, `id:settings-timer-badge-background-color`, `id:settings-timer-badge-text-color`, `id:settings-timer-badge-opacity`, `id:settings-shot-badge-background-color`, `id:settings-shot-badge-text-color`, `id:settings-shot-badge-opacity`, `id:settings-current-shot-badge-background-color`, `id:settings-current-shot-badge-text-color`, `id:settings-current-shot-badge-opacity`, `id:settings-hit-factor-badge-background-color`, `id:settings-hit-factor-badge-text-color`, `id:settings-hit-factor-badge-opacity`

### Marker defaults section

- Section selector: `data-settings-section:markers`
- Controls: `id:settings-marker-enabled`, `id:settings-marker-content-type`, `id:settings-marker-text-source`, `id:settings-marker-duration`, `id:settings-marker-use-shot-split-duration`, `id:settings-marker-width`, `id:settings-marker-height`, `id:settings-marker-follow-motion`, `id:settings-marker-background-color`, `id:settings-marker-text-color`, `id:settings-marker-opacity`

### Export defaults section

- Section selector: `data-settings-section:export`
- Controls: `id:settings-export-quality`, `id:settings-export-preset`, `id:settings-export-frame-rate`, `id:settings-export-video-codec`, `id:settings-export-audio-codec`, `id:settings-export-color-space`, `id:settings-export-ffmpeg-preset`, `id:settings-export-two-pass`

### ShotML defaults section

- Section selector: `data-settings-section:shotml`
- Controls: `id:settings-shotml-threshold`

### Settings suite anchors

- `tests/browser/test_settings_e2e.py`
- `tests/browser/test_settings_defaults_truth_gate.py`
- `tests/browser/test_browser_full_app_e2e.py`
- `tests/browser/test_browser_control.py`

## ShotML

### Tool selectors and top-level actions

- Tool routing: `data-tool:shotml`, `data-tool-pane:shotml`
- Top-level controls: `id:threshold`, `id:apply-threshold`, `id:reset-shotml-defaults`, `id:generate-shotml-proposals`

### Threshold section

- Section selector: `data-shotml-section:threshold`
- Settings: `data-shotml-setting:detection_threshold`, `data-shotml-setting:shot_detection_cutoff_base`, `data-shotml-setting:shot_detection_cutoff_span`

### Beep detection section

- Section selector: `data-shotml-section:beep_detection`
- Settings: `data-shotml-setting:beep_onset_fraction`, `data-shotml-setting:beep_search_lead_ms`, `data-shotml-setting:beep_search_tail_guard_ms`, `data-shotml-setting:beep_fallback_min_window_ms`, `data-shotml-setting:beep_heuristic_fft_window_s`, `data-shotml-setting:beep_heuristic_hop_s`, `data-shotml-setting:beep_heuristic_band_min_hz`, `data-shotml-setting:beep_heuristic_band_max_hz`, `data-shotml-setting:beep_fallback_threshold_multiplier`, `data-shotml-setting:beep_tonal_window_ms`, `data-shotml-setting:beep_tonal_hop_ms`, `data-shotml-setting:beep_tonal_band_min_hz`, `data-shotml-setting:beep_tonal_band_max_hz`, `data-shotml-setting:beep_refine_pre_ms`, `data-shotml-setting:beep_refine_post_ms`, `data-shotml-setting:beep_refine_min_gap_before_first_shot_ms`, `data-shotml-setting:beep_exclusion_radius_ms`, `data-shotml-setting:beep_region_cutoff_base`, `data-shotml-setting:beep_region_cutoff_threshold_weight`, `data-shotml-setting:beep_model_boost_floor`

### Shot candidate detection section

- Section selector: `data-shotml-section:shot_candidate_detection`
- Settings: `data-shotml-setting:min_shot_interval_ms`, `data-shotml-setting:shot_peak_min_spacing_ms`, `data-shotml-setting:shot_confidence_source`

### Shot refinement section

- Section selector: `data-shotml-section:shot_refinement`
- Settings: `data-shotml-setting:shot_onset_fraction`, `data-shotml-setting:shot_refine_pre_ms`, `data-shotml-setting:shot_refine_post_ms`, `data-shotml-setting:shot_refine_midpoint_clamp_padding_ms`, `data-shotml-setting:shot_refine_min_search_window_ms`, `data-shotml-setting:shot_refine_rms_window_ms`, `data-shotml-setting:shot_refine_rms_hop_ms`

### False positive suppression section

- Section selector: `data-shotml-section:false_positive_suppression`
- Settings: `data-shotml-setting:weak_onset_support_threshold`, `data-shotml-setting:near_cutoff_interval_ms`, `data-shotml-setting:shot_selection_confidence_weight`, `data-shotml-setting:shot_selection_support_weight`, `data-shotml-setting:weak_support_penalty`, `data-shotml-setting:suppress_close_pair_duplicates`, `data-shotml-setting:suppress_sound_profile_outliers`

### Confidence and review section

- Section selector: `data-shotml-section:confidence_review`
- Settings: `data-shotml-setting:refinement_confidence_weight`, `data-shotml-setting:onset_support_pre_ms`, `data-shotml-setting:onset_support_post_ms`, `data-shotml-setting:onset_support_rms_window_ms`, `data-shotml-setting:onset_support_rms_hop_ms`, `data-shotml-setting:onset_support_alignment_penalty_divisor_ms`, `data-shotml-setting:onset_support_alignment_penalty_multiplier`, `data-shotml-setting:sound_profile_search_radius_ms`, `data-shotml-setting:sound_profile_distance_limit`, `data-shotml-setting:sound_profile_high_confidence_limit`

### Timing changer section

- Section selector: `data-shotml-section:timing_changer`
- Control anchor: `id:generate-shotml-proposals`

### Advanced runtime section

- Section selector: `data-shotml-section:advanced_runtime`
- Settings: `data-shotml-setting:window_size`, `data-shotml-setting:hop_size`

### ShotML suite anchors

- `tests/browser/test_browser_remaining_controls_e2e.py`
- `tests/browser/test_browser_full_app_e2e.py`
- `tests/browser/test_browser_control.py`
- `tests/analysis/test_analysis.py`

## Document guards

- `tests/browser/test_browser_control_inventory_audit.py` verifies the live static mutable-control inventory still matches this document and the full e2e plan references.
- `tests/browser/test_browser_control_coverage_matrix.py` verifies the summarized surface ownership claims in [browser-control-qa-matrix.md](browser-control-qa-matrix.md).
