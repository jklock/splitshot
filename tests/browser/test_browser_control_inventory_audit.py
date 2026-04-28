from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path


INDEX_HTML = Path("src/splitshot/browser/static/index.html")
INVENTORY_PLAN = Path("docs/project/browser-control-coverage-plan.md")
FULL_E2E_PLAN = Path("docs/project/browser-full-e2e-qa-plan.md")

EXPECTED_STATIC_MUTABLE_CONTROL_IDENTIFIERS = {
    line.strip()
    for line in """
data-settings-section:export
data-settings-section:global-template
data-settings-section:markers
data-settings-section:overlay
data-settings-section:pip
data-settings-section:scoring
data-settings-section:shotml
data-shotml-section:advanced_runtime
data-shotml-section:beep_detection
data-shotml-section:confidence_review
data-shotml-section:false_positive_suppression
data-shotml-section:shot_candidate_detection
data-shotml-section:shot_refinement
data-shotml-section:threshold
data-shotml-section:timing_changer
data-shotml-setting:beep_exclusion_radius_ms
data-shotml-setting:beep_fallback_min_window_ms
data-shotml-setting:beep_fallback_threshold_multiplier
data-shotml-setting:beep_heuristic_band_max_hz
data-shotml-setting:beep_heuristic_band_min_hz
data-shotml-setting:beep_heuristic_fft_window_s
data-shotml-setting:beep_heuristic_hop_s
data-shotml-setting:beep_model_boost_floor
data-shotml-setting:beep_onset_fraction
data-shotml-setting:beep_refine_min_gap_before_first_shot_ms
data-shotml-setting:beep_refine_post_ms
data-shotml-setting:beep_refine_pre_ms
data-shotml-setting:beep_region_cutoff_base
data-shotml-setting:beep_region_cutoff_threshold_weight
data-shotml-setting:beep_search_lead_ms
data-shotml-setting:beep_search_tail_guard_ms
data-shotml-setting:beep_tonal_band_max_hz
data-shotml-setting:beep_tonal_band_min_hz
data-shotml-setting:beep_tonal_hop_ms
data-shotml-setting:beep_tonal_window_ms
data-shotml-setting:detection_threshold
data-shotml-setting:hop_size
data-shotml-setting:min_shot_interval_ms
data-shotml-setting:near_cutoff_interval_ms
data-shotml-setting:onset_support_alignment_penalty_divisor_ms
data-shotml-setting:onset_support_alignment_penalty_multiplier
data-shotml-setting:onset_support_post_ms
data-shotml-setting:onset_support_pre_ms
data-shotml-setting:onset_support_rms_hop_ms
data-shotml-setting:onset_support_rms_window_ms
data-shotml-setting:refinement_confidence_weight
data-shotml-setting:shot_confidence_source
data-shotml-setting:shot_detection_cutoff_base
data-shotml-setting:shot_detection_cutoff_span
data-shotml-setting:shot_onset_fraction
data-shotml-setting:shot_peak_min_spacing_ms
data-shotml-setting:shot_refine_midpoint_clamp_padding_ms
data-shotml-setting:shot_refine_min_search_window_ms
data-shotml-setting:shot_refine_post_ms
data-shotml-setting:shot_refine_pre_ms
data-shotml-setting:shot_refine_rms_hop_ms
data-shotml-setting:shot_refine_rms_window_ms
data-shotml-setting:shot_selection_confidence_weight
data-shotml-setting:shot_selection_support_weight
data-shotml-setting:sound_profile_distance_limit
data-shotml-setting:sound_profile_high_confidence_limit
data-shotml-setting:sound_profile_search_radius_ms
data-shotml-setting:suppress_close_pair_duplicates
data-shotml-setting:suppress_sound_profile_outliers
data-shotml-setting:weak_onset_support_threshold
data-shotml-setting:weak_support_penalty
data-shotml-setting:window_size
data-tool-pane:export
data-tool-pane:markers
data-tool-pane:merge
data-tool-pane:metrics
data-tool-pane:overlay
data-tool-pane:project
data-tool-pane:review
data-tool-pane:scoring
data-tool-pane:settings
data-tool-pane:shotml
data-tool-pane:timing
data-tool:export
data-tool:markers
data-tool:merge
data-tool:metrics
data-tool:overlay
data-tool:project
data-tool:review
data-tool:scoring
data-tool:settings
data-tool:shotml
data-tool:timing
id:add-merge-media
id:add-timing-event
id:amp-waveform-in
id:amp-waveform-out
id:apply-threshold
id:aspect-ratio
id:audio-bitrate
id:audio-codec
id:audio-sample-rate
id:badge-size
id:browse-export-path
id:browse-primary-path
id:browse-project-path
id:bubble-height
id:bubble-width
id:close-color-picker
id:close-export-log
id:collapse-metrics
id:collapse-scoring
id:collapse-timing
id:color-picker-hex
id:color-picker-hue
id:color-picker-lightness
id:color-picker-saturation
id:color-space
id:delete-project
id:delete-selected
id:draw-lock-to-stack
id:draw-x
id:draw-y
id:expand-metrics
id:expand-scoring
id:expand-timing
id:expand-waveform
id:export-export-log
id:export-path
id:export-preset
id:export-video
id:ffmpeg-preset
id:frame-rate
id:generate-shotml-proposals
id:import-practiscore
id:open-practiscore-dashboard
id:match-competitor-name
id:match-competitor-place
id:match-stage-number
id:match-type
id:max-visible-shots
id:merge-enabled
id:merge-layout
id:merge-media-input
id:metrics-export-csv
id:metrics-export-text
id:new-project
id:overlay-custom-x
id:overlay-custom-y
id:overlay-font-bold
id:overlay-font-family
id:overlay-font-italic
id:overlay-font-size
id:overlay-margin
id:overlay-spacing
id:overlay-style
id:pip-size
id:pip-x
id:pip-y
id:popup-add-bubble
id:popup-filter
id:popup-import-mode
id:popup-import-shots
id:popup-loop-window
id:popup-next-compact
id:popup-open-shot-editor
id:popup-play-window
id:popup-prev-compact
id:popup-shot-editor-delete
id:popup-shot-editor-done
id:popup-shot-editor-duplicate
id:popup-shot-editor-next
id:popup-shot-editor-prev
id:popup-template-content-type
id:popup-template-duration-s
id:popup-template-enabled
id:popup-template-follow-motion
id:popup-template-height
id:popup-template-text-source
id:popup-template-width
id:popup-toggle-authoring
id:practiscore-file-input
id:primary-file-input
id:primary-file-path
id:project-description
id:project-name
id:project-path
id:quality
id:reset-shotml-defaults
id:reset-waveform-view
id:resize-rail
id:resize-sidebar
id:resize-waveform
id:review-add-imported-box
id:review-add-text-box
id:score-lock-to-stack
id:score-x
id:score-y
id:scoring-enabled
id:scoring-preset
id:settings-badge-size
id:settings-current-shot-badge-background-color
id:settings-current-shot-badge-opacity
id:settings-current-shot-badge-text-color
id:settings-default-match-type
id:settings-default-tool
id:settings-export-audio-codec
id:settings-export-color-space
id:settings-export-ffmpeg-preset
id:settings-export-frame-rate
id:settings-export-preset
id:settings-export-quality
id:settings-export-two-pass
id:settings-export-video-codec
id:settings-hit-factor-badge-background-color
id:settings-hit-factor-badge-opacity
id:settings-hit-factor-badge-text-color
id:settings-import-current
id:settings-marker-background-color
id:settings-marker-content-type
id:settings-marker-duration
id:settings-marker-enabled
id:settings-marker-follow-motion
id:settings-marker-height
id:settings-marker-opacity
id:settings-marker-text-color
id:settings-marker-text-source
id:settings-marker-width
id:settings-merge-layout
id:settings-merge-pip-x
id:settings-merge-pip-y
id:settings-overlay-custom-background-color
id:settings-overlay-custom-opacity
id:settings-overlay-custom-text-color
id:settings-overlay-position
id:settings-pip-size
id:settings-rail-button
id:settings-reopen-last-tool
id:settings-reset-defaults
id:settings-scope
id:settings-shot-badge-background-color
id:settings-shot-badge-opacity
id:settings-shot-badge-text-color
id:settings-shotml-threshold
id:settings-timer-badge-background-color
id:settings-timer-badge-opacity
id:settings-timer-badge-text-color
id:shot-direction
id:shot-quadrant
id:show-draw
id:show-export-log
id:show-overlay
id:show-score
id:show-shots
id:show-timer
id:target-height
id:target-width
id:threshold
id:timer-lock-to-stack
id:timer-x
id:timer-y
id:timing-event-kind
id:timing-event-label
id:timing-event-position
id:toggle-layout-lock-video
id:toggle-rail
id:two-pass
id:video-bitrate
id:video-codec
id:zoom-waveform-in
id:zoom-waveform-out
""".splitlines()
    if line.strip()
}


class _InteractiveControlParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.identifiers: set[str] = set()

    def handle_starttag(self, tag: str, attrs) -> None:
        attr_map = dict(attrs)
        if "data-tool" in attr_map:
            self.identifiers.add(f"data-tool:{attr_map['data-tool']}")
        if "data-tool-pane" in attr_map:
            self.identifiers.add(f"data-tool-pane:{attr_map['data-tool-pane']}")
        if "data-settings-section" in attr_map:
            self.identifiers.add(f"data-settings-section:{attr_map['data-settings-section']}")
        if "data-shotml-section" in attr_map:
            self.identifiers.add(f"data-shotml-section:{attr_map['data-shotml-section']}")
        if "data-shotml-setting" in attr_map:
            self.identifiers.add(f"data-shotml-setting:{attr_map['data-shotml-setting']}")

        control_id = attr_map.get("id")
        if not control_id or tag == "section":
            return
        if tag == "input" and attr_map.get("type") == "hidden" and control_id not in {
            "primary-file-input",
            "merge-media-input",
            "practiscore-file-input",
        }:
            return
        if tag not in {"button", "input", "select", "textarea"}:
            return
        self.identifiers.add(f"id:{control_id}")


def _extract_static_mutable_control_identifiers() -> set[str]:
    parser = _InteractiveControlParser()
    parser.feed(INDEX_HTML.read_text(encoding="utf-8"))
    return parser.identifiers


def _sorted_lines(values: set[str]) -> str:
    return "\n".join(sorted(values))


def test_browser_shell_static_mutable_control_inventory_is_exhaustive() -> None:
    actual_identifiers = _extract_static_mutable_control_identifiers()

    missing = EXPECTED_STATIC_MUTABLE_CONTROL_IDENTIFIERS - actual_identifiers
    unexpected = actual_identifiers - EXPECTED_STATIC_MUTABLE_CONTROL_IDENTIFIERS

    assert not missing, f"Static browser controls missing from audit:\n{_sorted_lines(missing)}"
    assert not unexpected, f"New static browser controls need explicit inventory ownership:\n{_sorted_lines(unexpected)}"
    assert len(actual_identifiers) == 267


def test_browser_shell_inventory_is_wired_to_the_coverage_docs() -> None:
    inventory_plan = INVENTORY_PLAN.read_text(encoding="utf-8")
    full_e2e_plan = FULL_E2E_PLAN.read_text(encoding="utf-8")

    assert "For the phase-gated execution plan that defines what counts as truthful full-control end-to-end coverage" in inventory_plan
    assert "A full-app end-to-end QA claim requires satisfying the stricter exit criteria" in inventory_plan

    for snippet in [
        "Phase 0: Lock The Truth Boundary",
        "Phase 1: Shared Shell And Drag/Layout Interactions",
        "Phase 2: Splits And Score End-To-End Closeout",
        "Phase 3: Markers, Review, Overlay, And Color Picker",
        "Phase 4: PiP, Merge, Export Settings, And Export Log",
        "Phase 5: Settings And ShotML Full Coverage",
        "Phase 6: Cross-Surface Final Truth Gate",
        "`full-control QA coverage` means zero mutable controls are left at `missing`, `static`, or `smoke`.",
    ]:
        assert snippet in full_e2e_plan
