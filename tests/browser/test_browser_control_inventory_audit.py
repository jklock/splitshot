from __future__ import annotations

import re
from html.parser import HTMLParser
from pathlib import Path

INDEX_HTML = Path("src/splitshot/browser/static/index.html")
STATIC_ROOT = Path("src/splitshot/browser/static")

# JavaScript-rendered controls are not present in index.html and were previously
# invisible to this guard. Counts are source definitions, not runtime instances:
# repeated stages, sources, shots, markers, and boxes must be parameterized by
# the interaction audit.
EXPECTED_DYNAMIC_LITERAL_CONTROL_COUNTS = {
    "app.js": 39,
    "lib/shell-runtime.js": 5,
    "panes/intro-outro-pane.js": 25,
    "panes/media-pane.js": 15,
    "panes/queue-pane.js": 10,
    "panes/review-pane.js": 22,
    "panes/trim-sync-pane.js": 26,
}

EXPECTED_PROGRAMMATIC_CONTROL_FAMILIES = {
    "app.js:ensureSectionToggle:button:toggle:1",
    "app.js:renderColorPickerSwatches:button:button:1",
    "app.js:renderPopupTimeline:button:bar:1",
    "app.js:renderTimingTable:button:handle:1",
    "app.js:renderTimingTable:input:input:1",
    "components/waveform.js:renderWaveformShotList:button:deleteBtn:1",
    "components/waveform.js:renderWaveformShotList:button:item:1",
    "lib/shell-runtime.js:renderStyleControls:button:input:1",
    "lib/shell-runtime.js:renderStyleControls:input:hex:1",
    "panes/markers-pane.js:renderPopupKeyframeOverlay:button:handle:1",
    "panes/merge-pane.js:renderMergeMediaList:button:toggle:1",
    "panes/merge-pane.js:renderMergeMediaList:input:input:1",
    "panes/merge-pane.js:renderMergeMediaList:input:input:2",
    "panes/merge-pane.js:renderMergeMediaList:input:sizeInput:1",
    "panes/merge-pane.js:renderMergeMediaList:select:placementModeSelect:1",
    "panes/metrics-pane.js:renderStageMetricsTree:details:details:1",
    "panes/scoring-pane.js:appendPenaltyRow:button:add:1",
    "panes/scoring-pane.js:appendPenaltyRow:button:remove:1",
    "panes/scoring-pane.js:appendPenaltyRow:select:select:1",
    "panes/scoring-pane.js:buildScoringDeleteCell:button:button:1",
    "panes/scoring-pane.js:buildScoringRestoreCell:button:button:1",
    "panes/scoring-pane.js:buildScoringRowControlCell:button:button:1",
    "panes/scoring-pane.js:renderScoringTable:select:select:1",
    "panes/shotml-pane.js:renderShotMLProposals:button:apply:1",
    "panes/shotml-pane.js:renderShotMLProposals:button:discard:1",
    "panes/timing-pane.js:buildSplitRowActionCell:button:remove:1",
    "panes/timing-pane.js:buildTimingDeleteCell:button:deleteShot:1",
    "panes/timing-pane.js:buildTimingRestoreCell:button:restore:1",
    "panes/timing-pane.js:buildTimingRowControlCell:button:lockButton:1",
    "panes/timing-pane.js:renderTimingEventList:button:remove:1",
}

EXPECTED_STATIC_MUTABLE_CONTROL_IDENTIFIERS = {
    line.strip()
    for line in """
data-settings-section:export
data-settings-section:global-template
data-settings-section:layout
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
data-tool-pane:intro-outro
data-tool-pane:media
data-tool-pane:markers
data-tool-pane:merge
data-tool-pane:metrics
data-tool-pane:overlay
data-tool-pane:project
data-tool-pane:queue
data-tool-pane:review
data-tool-pane:scoring
data-tool-pane:settings
data-tool-pane:shotml
data-tool-pane:timing
data-tool-pane:trim-sync
data-tool:export
data-tool:intro-outro
data-tool:media
data-tool:markers
data-tool:merge
data-tool:metrics
data-tool:overlay
data-tool:project
data-tool:queue
data-tool:review
data-tool:scoring
data-tool:settings
data-tool:shotml
data-tool:timing
data-tool:trim-sync
id:add-timing-event
id:amp-waveform-in
id:amp-waveform-out
id:apply-threshold
id:aspect-ratio
id:audio-bitrate
id:audio-codec
id:audio-sample-rate
id:badge-size
id:browse-project-output-root
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
id:create-output-profile
id:delete-output-profile
id:save-output-profile
id:delete-project
id:timing-enabled
id:draw-lock-to-stack
id:draw-x
id:draw-y
id:expand-metrics
id:expand-scoring
id:expand-timing
id:expand-waveform
id:export-badges
id:export-export-log
id:export-preset
id:ffmpeg-preset
id:frame-rate
id:generate-shotml-proposals
id:import-practiscore
id:open-practiscore-dashboard
id:open-project
id:match-type
id:match-class
id:match-competitor-name
id:match-competitor-place
id:match-division
id:max-visible-shots
id:markers-enable
id:markers-workbench-filter
id:merge-enabled
id:merge-layout
id:merge-media-input
id:media-add-more-input
id:metrics-export-csv
id:metrics-export-text
id:new-project
id:output-profile-frame
id:output-profile-name
id:output-profile-select
id:output-profile-type
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
id:popup-add-bubble-workbench
id:popup-edit-selected
id:popup-import-shots-workbench
id:popup-next-workbench
id:popup-prev-workbench
id:popup-add-selected-shot-workbench
id:practiscore-file-input
id:primary-file-input
id:project-description
id:project-name
id:project-path
id:project-output-root
id:quality
id:reset-shotml-defaults
id:restore-merge-defaults
id:reset-waveform-view
id:trim-global-apply
id:trim-global-clear
id:trim-global-defaults-btn
id:trim-global-end
id:trim-global-start
id:trim-global-undo
id:resize-rail
id:resize-sidebar
id:resize-waveform
id:review-add-imported-box
id:review-add-stage-name-box
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
id:settings-layout-inspector-width
id:settings-layout-locked
id:settings-layout-rail-width
id:settings-layout-waveform-height
id:settings-marker-background-color
id:settings-marker-content-type
id:settings-marker-duration
id:settings-marker-enabled
id:settings-marker-follow-motion
id:settings-marker-quadrant
id:settings-marker-use-shot-split-duration
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
id:settings-release-layout
id:settings-rail-button
id:settings-reopen-last-tool
id:settings-reset-defaults
id:settings-reset-section-export
id:settings-reset-section-markers
id:settings-reset-section-overlay
id:settings-reset-section-pip
id:settings-reset-section-scoring
id:settings-reset-section-shotml
id:settings-save-current-export
id:settings-save-current-markers
id:settings-save-current-overlay
id:settings-save-current-pip
id:settings-save-current-scoring
id:settings-save-current-shotml
id:settings-shot-badge-background-color
id:settings-shot-badge-opacity
id:settings-shot-badge-text-color
id:settings-shotml-threshold
id:settings-timer-badge-background-color
id:settings-timer-badge-opacity
id:settings-timer-badge-text-color
id:settings-use-current-layout
id:shot-direction
id:shot-quadrant
id:show-draw
id:show-markers
id:show-overlay
id:show-pip
id:show-score
id:show-shot-scores
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
data-tool:media
data-tool:queue
data-tool-pane:media
data-tool-pane:queue
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
        if (
            tag == "input"
            and attr_map.get("type") == "hidden"
            and control_id
            not in {
                "primary-file-input",
                "merge-media-input",
                "media-add-more-input",
                "practiscore-file-input",
            }
        ):
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
    assert not unexpected, (
        f"New static browser controls need explicit inventory ownership:\n{_sorted_lines(unexpected)}"
    )
    assert len(actual_identifiers) == len(EXPECTED_STATIC_MUTABLE_CONTROL_IDENTIFIERS)


_INTERACTIVE_TAG_RE = re.compile(
    r"<(button|input|select|textarea|details|video)\b([^>]*)>", re.IGNORECASE | re.DOTALL
)
_FUNCTION_RE = re.compile(r"(?:async\s+)?function\s+([A-Za-z0-9_]+)\s*\(")
_PROGRAMMATIC_CONTROL_RE = re.compile(
    r"(?:const|let|var)?\s*([A-Za-z_$][\w$]*)\s*=\s*"
    r"(?:documentObject|document)\.createElement\([\"']"
    r"(button|input|select|textarea|details|video)[\"']\)"
)


def _dynamic_literal_control_counts() -> dict[str, int]:
    counts: dict[str, int] = {}
    for path in sorted(STATIC_ROOT.rglob("*.js")):
        text = path.read_text(encoding="utf-8")
        count = 0
        for match in _INTERACTIVE_TAG_RE.finditer(text):
            attributes = match.group(2)
            if re.search(r"\breadonly(?:\s|>|$)", attributes):
                continue
            if re.search(r"\bdisabled(?:\s|>|$)", attributes) and not re.search(
                r"\b(?:id|class|data-[A-Za-z0-9_-]+)\s*=", attributes
            ):
                continue
            count += 1
            assert re.search(r"\b(?:id|class|data-[A-Za-z0-9_-]+)\s*=", attributes), (
                "JavaScript-rendered interactive control needs a stable id, class, or data owner: "
                f"{path}:{text.count(chr(10), 0, match.start()) + 1}"
            )
        if count:
            counts[str(path.relative_to(STATIC_ROOT))] = count
    return counts


def _programmatic_control_families() -> set[str]:
    families: set[str] = set()
    for path in sorted(STATIC_ROOT.rglob("*.js")):
        text = path.read_text(encoding="utf-8")
        function_matches = list(_FUNCTION_RE.finditer(text))
        occurrences: dict[tuple[str, str, str], int] = {}
        for match in _PROGRAMMATIC_CONTROL_RE.finditer(text):
            enclosing = [item for item in function_matches if item.start() < match.start()]
            function_name = enclosing[-1].group(1) if enclosing else "<module>"
            variable, tag = match.groups()
            key = (function_name, tag, variable)
            occurrences[key] = occurrences.get(key, 0) + 1
            families.add(
                f"{path.relative_to(STATIC_ROOT)}:{function_name}:{tag}:{variable}:{occurrences[key]}"
            )
    return families


def test_javascript_rendered_mutable_control_inventory_is_exhaustive() -> None:
    assert _dynamic_literal_control_counts() == EXPECTED_DYNAMIC_LITERAL_CONTROL_COUNTS
    assert _programmatic_control_families() == EXPECTED_PROGRAMMATIC_CONTROL_FAMILIES
