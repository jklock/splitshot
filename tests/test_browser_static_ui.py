from __future__ import annotations

import re
from pathlib import Path


STATIC_ROOT = Path("src/splitshot/browser/static")


def test_browser_ui_is_waterfall_cockpit_workflow() -> None:
    html = (STATIC_ROOT / "index.html").read_text()

    assert 'class="app-shell cockpit-shell"' in html
    assert 'class="tool-rail"' in html
    assert 'class="status-strip"' in html
    assert 'class="review-grid"' in html
    assert 'class="review-stack"' in html
    assert 'class="inspector"' in html
    assert html.index('data-tool="project"') < html.index('data-tool="timing"')
    assert html.index('data-tool="layout"') < html.index('data-tool="review"')
    assert html.index('data-tool="review"') < html.index('data-tool="export"')
    assert 'data-tool="project"' in html
    assert 'data-tool="review"' in html
    assert 'data-tool="timing"' in html
    assert 'data-tool="edit"' not in html
    assert 'data-tool="scoring"' in html
    assert 'data-tool="overlay"' in html
    assert 'data-tool="merge"' in html
    assert 'data-tool="layout"' in html
    assert 'data-tool="export"' in html
    assert '<img class="rail-logo" src="/static/logo.png" alt="SplitShot" />' in html
    assert "<b>Review</b>" in html
    assert "<b>Splits</b>" in html
    assert "<b>Score</b>" in html
    assert "🍎" not in html
    assert 'class="topbar"' not in html
    assert 'class="command-strip"' not in html
    assert 'class="empty-start"' not in html
    assert 'class="metrics-strip"' not in html
    assert 'class="sidebar-section sidebar-metrics"' not in html
    assert 'class="rail-action"' not in html
    assert "Open Stage Video" not in html
    assert "Refresh" not in html
    assert 'id="current-file"' in html
    assert 'id="processing-bar"' in html
    assert 'id="selected-shot-panel"' in html
    assert 'class="video-status"' not in html
    assert "No video open" not in html
    assert "Apply Threshold" not in html
    assert "Apply Scoring" not in html
    assert 'id="apply-scoring"' not in html
    assert "Assign To Selected Shot" not in html
    assert "Apply Merge" not in html
    assert "Choose Primary" not in html
    assert "Choose Secondary" not in html
    assert "Import Path" not in html
    assert "Local review cockpit" not in html
    assert "Start here" not in html
    assert "SplitShot analyzes" not in html
    assert "No cloud transfer" not in html
    assert "upload" not in html.lower()
    assert "Add Second Angle" not in html
    assert "Add Second Video" in html


def test_browser_ui_keeps_video_timeline_waveform_and_inspector_together() -> None:
    html = (STATIC_ROOT / "index.html").read_text()
    js = (STATIC_ROOT / "app.js").read_text()

    assert html.index('class="video-stage"') < html.index('class="waveform-panel"')
    assert html.index('class="waveform-panel"') < html.index('class="inspector"')
    assert 'id="primary-video" controls' in html
    assert 'id="secondary-video"' in html
    assert 'id="live-overlay"' in html
    assert 'id="custom-overlay"' in html
    assert 'id="score-layer"' in html
    assert 'id="timeline-strip"' in html
    assert 'id="waveform"' in html
    assert 'id="expand-waveform"' in html
    assert 'id="zoom-waveform-out"' in html
    assert 'id="zoom-waveform-in"' in html
    assert 'id="amp-waveform-out"' in html
    assert 'id="amp-waveform-in"' in html
    assert 'id="reset-waveform-view"' in html
    assert 'id="resize-rail"' in html
    assert 'id="resize-sidebar"' in html
    assert 'id="resize-waveform"' in html
    assert 'id="toggle-layout-lock"' in html
    assert 'id="reset-layout"' in html
    assert 'data-waveform-mode="select"' in html
    assert 'data-waveform-mode="add"' in html
    assert 'data-waveform-mode="beep"' in html
    assert 'id="waveform-shot-list"' in html
    assert 'id="timing-workbench"' in html
    assert 'id="expand-timing"' in html
    assert 'id="split-card-grid"' in html
    assert 'id="selected-shot-copy"' in html
    assert html.index('id="timing-table"') > html.index('id="selected-shot-panel"')
    assert html.index('id="waveform"') < html.index('waveform-header')
    assert 'id="badge-style-grid"' in html
    assert 'id="score-color-grid"' in html
    assert 'id="max-visible-shots"' in html
    assert 'id="shot-quadrant"' in html
    assert 'id="shot-direction"' in html
    assert 'id="overlay-custom-x"' in html
    assert 'id="bubble-width"' in html
    assert 'id="overlay-font-family"' in html
    assert 'id="show-timer"' in html
    assert 'id="custom-box-text"' in html
    assert 'id="layout-threshold"' in html
    assert 'id="layout-scoring-enabled"' in html
    assert 'id="layout-overlay-position"' in html
    assert 'id="layout-max-visible-shots"' in html
    assert 'id="layout-merge-enabled"' in html
    assert 'id="scoring-preset"' in html
    assert 'id="score-option-grid"' in html
    assert 'id="scoring-penalty-grid"' in html
    assert 'id="browse-project-path"' in html
    assert 'id="browse-export-path"' in html
    assert 'id="browse-primary-path"' in html
    assert 'id="browse-secondary-path"' in html
    assert 'id="export-preset"' in html
    assert 'id="target-width"' in html
    assert 'id="target-height"' in html
    assert 'id="frame-rate"' in html
    assert 'id="video-codec"' in html
    assert 'id="video-bitrate"' in html
    assert 'id="audio-codec"' in html
    assert 'id="audio-sample-rate"' in html
    assert 'id="audio-bitrate"' in html
    assert 'id="color-space"' in html
    assert 'id="ffmpeg-preset"' in html
    assert 'id="export-log"' in html
    assert "/api/files/primary" in js
    assert "/api/files/secondary" in js
    assert "/api/dialog/path" in js
    assert "/api/export/settings" in js
    assert "/api/export/preset" in js
    assert "/api/activity" in js
    assert 'activity("button.click"' in js
    assert "wireGlobalActivityLogging" in js
    assert "document.addEventListener(\"click\"" in js
    assert "handleWaveformPointerDown" in js
    assert "handleWaveformPointerMove" in js
    assert "handleKeyboardEdit" in js
    assert "autoApplyThreshold" in js
    assert "autoApplyOverlay" in js
    assert "autoApplyMerge" in js
    assert "autoApplyLayout" in js
    assert "autoApplyExportSettings" in js
    assert "autoApplyScoring" in js
    assert "renderScoringPenaltyFields" in js
    assert "copyLayoutOverlayControls" in js
    assert "copyLayoutMergeControls" in js
    assert "copyLayoutScoringControls" in js
    assert "importTypedPath" in js
    assert "syncSecondaryPreview" in js
    assert "merge-preview" in js
    assert 'pickPath("primary", "primary-file-path", async (path)' in js
    assert 'pickPath("secondary", "secondary-file-path", async (path)' in js
    assert '$("penalties").value = state.project.scoring.penalties' not in js
    assert "renderExportPresetOptions" in js
    assert "processingForPath" in js
    assert "Opening file browser..." not in js
    assert "scoring-active" in js
    assert "layoutLocked" in js
    assert "applyLayoutState" in js
    assert "beginLayoutResize" in js
    assert 'activity("layout.resize.start"' in js
    assert 'activity("layout.resize.commit"' in js
    assert "Score letter is saved to that shot" in html
    assert "appears inside its split badge" in html
    assert "empty-start" not in js
    assert "setActiveTool" in js
    assert "setActivePage" not in js


def test_browser_ui_uses_hard_edged_contiguous_tool_shell() -> None:
    css = (STATIC_ROOT / "styles.css").read_text()

    assert "border-radius: 0;" in css
    assert "border-radius: 8px" not in css
    assert "border-radius: 9px" not in css
    assert "border-radius: 10px" not in css
    assert "html,\nbody {\n  height: 100%;" in css
    assert "overflow: hidden;" in css
    assert ".review-grid {\n  display: grid;" in css
    assert ".button-grid {\n  display: grid;\n  gap: 0;" in css
    assert ".status-strip {\n  align-items: center;" in css
    assert ".processing-bar {" in css
    assert ".command-strip" not in css
    assert ".empty-start" not in css
    assert ".metrics-strip" not in css
    assert ".rail-action" not in css
    assert "--rail-width: 96px;" in css
    assert "--topbar-height: 38px;" in css
    assert "--inspector-width: 440px;" in css
    assert "--waveform-height: 206px;" in css
    assert "--resize-handle-size: 6px;" in css
    assert "grid-template-columns: var(--rail-width) var(--resize-handle-size) minmax(0, 1fr);" in css
    assert "grid-template-rows: var(--topbar-height) minmax(0, 1fr);" in css
    assert ".processing-bar[hidden] {\n  display: none !important;" in css
    assert "grid-template-rows: repeat(8, minmax(0, 1fr));" in css
    assert "grid-template-columns: minmax(0, 1fr) repeat(4, calc(var(--inspector-width) / 4));" in css
    assert "width: var(--inspector-width);" in css
    assert "overflow-x: hidden;" in css
    assert "grid-template-rows: minmax(0, 1fr) var(--resize-handle-size) minmax(112px, var(--waveform-height));" in css
    assert "grid-template-rows: minmax(320px, 1fr) 206px;" not in css
    assert ".layout-unlocked .resize-handle" in css
    assert ".video-stage.merge-preview" in css
    assert ".video-stage.merge-pip #secondary-video" in css
    assert ".project-delete-button" in css
    assert ".cockpit.waveform-expanded .review-grid" in css
    assert ".cockpit.waveform-expanded .video-stage" in css
    assert "display: none;" in css
    assert ".cockpit.timing-expanded .timing-workbench" in css
    assert "grid-template-rows: minmax(0, 1fr) 38px 26px auto;" in css
    assert "input[type=\"color\"]" in css
    assert ".penalty-grid" in css
    assert ".export-log" in css
    assert ".cockpit.scoring-active .score-target-button" not in css
    assert ".overlay-badge.timer-badge" in css
    assert ".score-float" not in css
    assert "font-family: -apple-system" in css
    assert "font-size: 13px;" in css


def test_browser_buttons_are_logged_and_wired_to_actions() -> None:
    html = (STATIC_ROOT / "index.html").read_text()
    js = (STATIC_ROOT / "app.js").read_text()

    assert 'activity("button.click"' in js

    wired_button_ids = {
        "place-score",
        "expand-waveform",
        "zoom-waveform-out",
        "zoom-waveform-in",
        "amp-waveform-out",
        "amp-waveform-in",
        "reset-waveform-view",
        "collapse-timing",
        "delete-selected",
        "expand-timing",
        "swap-videos",
        "export-video",
        "browse-export-path",
        "browse-primary-path",
        "browse-secondary-path",
        "new-project",
        "browse-project-path",
        "save-project",
        "open-project",
        "delete-project",
        "toggle-layout-lock",
        "reset-layout",
        "resize-rail",
        "resize-sidebar",
        "resize-waveform",
    }
    behavior_attributes = (
        "data-tool=",
        "data-waveform-mode=",
        "data-nudge=",
        "data-sync=",
        "data-open-secondary",
    )
    button_tags = re.findall(r"<button\b[^>]*>", html)

    assert button_tags
    for tag in button_tags:
        id_match = re.search(r'id="([^"]+)"', tag)
        has_wired_id = bool(id_match and id_match.group(1) in wired_button_ids)
        has_behavior_attribute = any(attribute in tag for attribute in behavior_attributes)
        assert has_wired_id or has_behavior_attribute, tag


def test_browser_display_names_strip_session_uuid_prefixes() -> None:
    js = (STATIC_ROOT / "app.js").read_text()

    assert "primary_display_name" in js
    assert "secondary_display_name" in js
    assert 'replace(/^[a-f0-9]{32}_/i, "")' in js


def test_readme_documents_one_command_uv_launch() -> None:
    readme = Path("README.md").read_text()

    assert Path(".python-version").read_text().strip() == "3.12"
    assert "uv run splitshot" in readme
    assert "uv run --python 3.12 splitshot" not in readme


def test_browser_static_logo_is_packaged() -> None:
    assert (STATIC_ROOT / "logo.png").is_file()
