from __future__ import annotations

import ast
import inspect
import re
from pathlib import Path

STATIC_ROOT = Path("src/splitshot/browser/static")


class _StaticBrowserSourceContract:
    def __init__(self, app_source: str, combined_source: str, app_only_snippets: set[str]):
        self._app_source = app_source
        self._combined_source = combined_source
        self._app_only_snippets = app_only_snippets

    def __contains__(self, item: object) -> bool:
        if not isinstance(item, str):
            return False
        if item in self._app_source:
            return True
        if item in self._app_only_snippets:
            return False
        return item in self._combined_source

    def __getattr__(self, name: str):
        return getattr(self._app_source, name)


def _extract_not_in_js_snippets(test_fn) -> set[str]:
    snippets: set[str] = set()
    for line in inspect.getsource(test_fn).splitlines():
        stripped = line.strip()
        if not stripped.startswith("assert ") or " not in js" not in stripped:
            continue
        match = re.match(r"assert (.+?)\s+not\s+in\s+js\s*$", stripped)
        if not match:
            continue
        snippets.add(ast.literal_eval(match.group(1).strip()))
    return snippets


def _read_split_css() -> str:
    css_dir = STATIC_ROOT / "styles"
    parts = []
    for name in ["theme.css", "layout.css", "components.css", "panes.css", "widgets.css"]:
        path = css_dir / name
        if path.exists():
            parts.append(path.read_text(encoding="utf-8"))
    return "\n".join(parts)


def _read_shell_runtime_source() -> str:
    return (STATIC_ROOT / "lib" / "shell-runtime.js").read_text()


def _read_app_shell_source() -> str:
    return (
        "\n".join([(STATIC_ROOT / "app.js").read_text(), _read_shell_runtime_source()])
        .replace("documentObject.", "document.")
        .replace("windowObject.", "window.")
    )


def test_browser_ui_is_waterfall_cockpit_workflow() -> None:
    html = (STATIC_ROOT / "index.html").read_text()
    js = (STATIC_ROOT / "app.js").read_text()
    markers_pane = (STATIC_ROOT / "panes" / "markers-pane.js").read_text()
    css = _read_split_css()

    assert 'class="app-shell cockpit-shell"' in html
    assert 'href="/static/styles.css?v=20260714a"' in html
    assert 'src="/static/app.js?v=20260501f"' in html
    assert '<script type="module" src="/static/app.js?v=20260501f"></script>' in html
    assert '<script src="/static/app.js?v=20260501f"></script>' not in html
    assert 'accept="video/*,.mp4,.m4v,.mov,.avi,.wmv,.webm,.mkv,.mpg,.mpeg,.mts,.m2ts"' in html
    assert (
        'accept="video/*,image/*,.mp4,.m4v,.mov,.avi,.wmv,.webm,.mkv,.mpg,.mpeg,.mts,.m2ts,.png,.jpg,.jpeg,.gif,.webp"'
        in html
    )
    assert 'accept=".csv,.txt,text/csv,text/plain"' in html
    assert 'class="tool-rail"' in html
    assert 'class="status-bar"' in html
    assert 'class="review-grid"' in html
    assert 'class="review-stack"' in html
    assert 'class="inspector"' in html
    assert html.index('data-tool="project"') < html.index('data-tool="merge"')
    assert html.index('data-tool="merge"') < html.index('data-tool="scoring"')
    assert html.index('data-tool="scoring"') < html.index('data-tool="timing"')
    assert html.index('data-tool="timing"') < html.index('data-tool="markers"')
    assert html.index('data-tool="markers"') < html.index('data-tool="overlay"')
    assert html.index('data-tool="overlay"') < html.index('data-tool="review"')
    assert html.index('data-tool="review"') < html.index('data-tool="export"')
    assert html.index('data-tool="export"') < html.index('data-tool="metrics"')
    assert html.index('data-tool="metrics"') < html.index('data-tool="shotml"')
    assert html.index('data-tool="shotml"') < html.index('data-tool="settings"')
    assert 'data-tool="project"' in html
    assert 'data-tool="metrics"' in html
    assert 'data-tool="review"' in html
    assert 'data-tool="timing"' in html
    assert 'data-tool="shotml"' in html
    assert 'data-tool="edit"' not in html
    assert 'data-tool="scoring"' in html
    assert 'data-tool="overlay"' in html
    assert 'data-tool="markers"' in html
    assert 'data-tool="merge"' in html
    assert 'data-tool="settings" data-short="Set"' in html
    assert 'id="settings-rail-button"' in html
    assert 'id="toggle-rail"' in html
    assert 'data-tool="layout"' not in html
    assert 'data-tool="export"' in html
    assert '<img class="rail-logo" src="/static/logo.png" alt="SplitShot" />' in html
    assert "Compose</button>" in html
    assert "Metrics</button>" in html
    assert "Review</button>" in html
    assert "Splits</button>" in html
    assert "ShotML</button>" in html
    assert "Score</button>" in html
    assert "Markers</button>" in html
    assert "⚙" in html
    for short in ["Pro", "Com", "Sco", "Spl", "Mar", "Ovr", "Rev", "Exp", "Met", "SML", "Set"]:
        assert f'data-short="{short}"' in html
    assert "🍎" not in html
    assert 'class="topbar"' not in html
    assert 'class="command-strip"' not in html
    assert 'class="empty-start"' not in html
    assert 'class="metrics-strip"' not in html
    assert 'class="sidebar-section sidebar-metrics"' not in html
    assert 'class="rail-action"' not in html
    assert "Open Stage Video" not in html
    assert "Refresh" not in html
    assert 'id="project-name"' in html
    assert 'id="project-description"' in html
    assert 'id="project-output-root"' in html
    assert 'id="browse-project-output-root"' in html
    assert 'id="match-type"' in html
    assert 'id="match-stage-number"' not in html
    assert 'id="match-competitor-name"' in html
    assert 'id="match-class"' in html
    assert 'id="match-division"' in html
    assert '<button id="browse-project-path" type="button">Select Project</button>' in html
    assert 'id="project-path" placeholder="Please create / select project" readonly' in html
    assert 'id="primary-file-path"' not in html
    assert '<button id="new-project" type="button">Create Project</button>' in html
    assert 'id="open-wizard"' not in html
    assert 'id="use-project-folder"' not in html
    assert 'id="import-practiscore"' in html
    assert 'id="open-practiscore-dashboard"' in html
    assert 'id="practiscore-status"' in html
    assert 'id="connect-practiscore"' not in html
    assert 'id="clear-practiscore-session"' not in html
    assert 'id="practiscore-remote-match"' not in html
    assert 'id="import-practiscore-selected"' not in html
    assert 'id="practiscore-session-sync-status"' not in html
    assert 'id="practiscore-session-status"' not in html
    assert 'id="practiscore-sync-status"' not in html
    assert 'id="practiscore-sync-message"' not in html
    assert 'id="practiscore-session-message"' not in html
    assert 'id="practiscore-import-summary"' in html
    assert 'id="current-file"' in html
    assert 'id="status-copy"' in html
    assert 'id="inspector-file"' not in html
    assert 'id="inspector-status-copy"' not in html
    assert 'id="processing-bar"' in html
    assert '<span id="media-badge">No project open</span>' in html
    assert 'id="selected-shot-panel"' not in html
    assert 'id="split-card-grid"' not in html
    assert 'class="video-status"' not in html
    assert "No video open" not in html
    assert 'id="apply-threshold"' in html
    assert ">Run ShotML<" in html
    assert 'data-tool-pane="shotml"' in html
    assert 'id="shotml-confidence-summary"' in html
    assert "No automatic confidence data" in html
    assert 'id="generate-shotml-proposals"' in html
    assert 'id="reset-shotml-defaults"' in html
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
    assert "cloud upload" not in html.lower()
    assert "Add Second Angle" not in html
    assert "Add Second Video" not in html
    assert "Add Media" not in html
    assert 'id="merge-media-input"' in html
    assert 'tool-item[data-tool="metrics"]:not(.active)' in css
    assert 'tool-item[data-tool="settings"]:not(.active)' not in css
    assert ".practiscore-actions {" in css
    assert ".practiscore-action-grid {" in css
    assert ".practiscore-remote-panel {" not in css
    assert ".practiscore-session-sync-status {" not in css
    rail_footer_css = css[css.index(".tool-rail-footer {") : css.index(".tool-rail-divider {")]
    assert "display: flex;" in rail_footer_css
    assert "flex-direction: column;" in rail_footer_css
    assert "grid-template-columns: repeat(2, minmax(0, 1fr));" not in rail_footer_css
    assert ".tool-rail-footer .tool-item {" in rail_footer_css
    assert "width: 44px;" in rail_footer_css
    assert "height: 44px;" in rail_footer_css
    assert "#settings-rail-button {" in rail_footer_css
    assert "#toggle-rail {" in rail_footer_css
    assert 'id="practiscore-file-input"' in html
    assert 'id="merge-media-list"' in html
    assert "New added media" not in html
    assert "Swap Primary and First Added Item" not in html
    assert "Select PractiScore File" in html
    assert "Open PractiScore Dashboard" in html
    assert "Select Project" in html
    assert "Create Project" in html
    assert "Connect PractiScore" not in html
    assert "Clear PractiScore Session" not in html
    assert "Import Selected Match" not in html
    assert "Manual fallback:" not in html
    assert html.index("Project folder") < html.index("Project name")
    assert html.index("Project name") < html.index("PractiScore Import")
    assert "John Klockenkemper" not in html
    assert 'id="match-stage-number-options"' not in html
    assert 'id="match-competitor-name-options"' not in html
    assert 'id="match-competitor-place-options"' not in html
    assert 'placeholder="Add competitor name"' not in html
    assert 'placeholder="Add stage number"' not in html
    assert 'placeholder="Optional"' not in html
    assert "Upload Primary Video" not in html
    assert "upload an IDPA CSV" not in html
    assert "Add the match data here" not in html
    assert "Multiple items export as a grid" not in html
    assert "Review Overlay Styling" not in html
    assert 'id="pip-x"' in html
    assert 'id="pip-y"' in html
    assert 'class="text-box-manager"' in html
    assert 'id="review-add-text-box"' in html
    assert 'id="review-add-imported-box"' in html
    assert "Add Custom Box" in html
    assert "Add Summary Box" in html
    assert "Show Boxes" in html
    assert 'class="review-visibility-manager"' in html
    assert 'class="check-row review-visibility-option"' in html
    assert 'id="show-markers"' in html
    assert 'id="show-pip"' in html
    assert 'id="markers-enable"' in html
    assert "Show markers" in html
    assert "Show secondary media" in html
    assert "Enable Markers" in html
    assert 'id="review-text-box-list"' in html
    assert 'data-tool-pane="markers"' in html
    assert 'data-tool-pane="settings"' in html
    assert 'id="popup-add-bubble"' in html
    assert 'id="popup-import-shots"' not in html
    assert 'id="popup-import-mode"' not in html
    assert 'id="popup-filter"' not in html
    assert 'id="popup-marker-toolbar"' not in html
    assert 'id="popup-edit-selected"' in html
    assert 'id="expand-markers"' not in html
    assert 'id="popup-prev"' not in html
    assert 'id="popup-next"' not in html
    assert 'id="popup-prev-compact"' not in html
    assert 'id="popup-next-compact"' not in html
    assert 'id="popup-play-window"' not in html
    assert 'id="popup-loop-window"' not in html
    assert 'id="popup-toggle-authoring"' not in html
    assert 'id="popup-pane-status"' in html
    assert 'id="popup-selected-summary"' not in html
    assert 'id="popup-list-status"' in html
    assert 'id="markers-workbench-status"' in html
    assert 'id="markers-workbench-selected-summary"' not in html
    assert 'id="markers-workbench-list-status"' in html
    assert 'id="markers-workbench-editor-status"' in html
    assert 'id="popup-duplicate-selected"' not in html
    assert 'id="popup-delete-selected"' not in html
    assert 'id="popup-enable-shown"' not in html
    assert 'id="popup-disable-shown"' not in html
    assert 'id="popup-bulk-duration-s"' not in html
    assert 'id="popup-apply-duration-selected"' not in html
    assert 'id="popup-apply-duration-shown"' not in html
    assert 'id="popup-apply-duration-shot-linked"' not in html
    assert 'id="popup-timeline-strip"' not in html
    assert 'id="popup-template-content-type"' not in html
    assert 'id="popup-shot-linked-list"' not in html
    assert 'id="popup-open-shot-editor"' not in html
    assert 'id="popup-shot-editor"' not in html
    assert 'id="popup-marker-list"' in html
    assert 'id="markers-workbench"' in html
    assert 'id="collapse-markers"' not in html
    assert 'id="popup-add-bubble-workbench"' in html
    assert 'id="popup-add-selected-shot-workbench"' in html
    assert 'id="popup-import-shots-workbench"' in html
    assert ">Import Shots</button>" in html
    assert "Import Visible Shots" not in html
    assert 'id="popup-prev-workbench"' in html
    assert 'id="popup-next-workbench"' in html
    assert 'id="markers-workbench-filter"' in html
    assert 'id="markers-workbench-list"' in html
    assert 'id="markers-workbench-editor"' in html
    assert 'id="popup-add-selected-shot"' not in html
    assert ">Edit</button>" in html
    assert 'id="popup-template-background-color"' not in html
    assert 'id="popup-template-motion-mode" type="hidden" value="fixed"' not in html
    assert 'data-motion-mode-target="popup-template-motion-mode"' not in html
    assert 'id="popup-floating-editor"' not in html
    assert 'id="settings-default-match-type"' in html
    assert 'id="settings-import-current"' in html
    assert 'id="settings-overlay-position"' in html
    assert 'id="settings-badge-size"' in html
    assert 'id="settings-overlay-custom-opacity"' in html
    assert 'id="settings-badge-style-grid"' in html
    assert 'id="settings-timer-badge-background-color"' in html
    assert 'id="settings-hit-factor-badge-opacity"' in html
    assert 'id="settings-layout-locked"' in html
    assert 'id="settings-layout-rail-width"' in html
    assert 'id="settings-layout-inspector-width"' in html
    assert 'id="settings-layout-waveform-height"' in html
    assert 'id="settings-use-current-layout"' in html
    assert 'id="settings-marker-use-shot-split-duration"' in html
    assert "Use shot split duration" in html
    assert "use_shot_split_duration" in js
    assert 'id="settings-release-layout"' in html
    assert 'id="settings-layout-status"' in html
    assert 'id="settings-layout-summary"' in html
    assert 'id="settings-save-current-scoring"' in html
    assert 'id="settings-reset-section-scoring"' in html
    assert 'id="settings-save-current-pip"' in html
    assert 'id="settings-reset-section-pip"' in html
    assert 'id="settings-pip-summary"' in html
    assert 'id="settings-save-current-overlay"' in html
    assert 'id="settings-reset-section-overlay"' in html
    assert 'id="settings-save-current-markers"' in html
    assert 'id="settings-reset-section-markers"' in html
    assert 'id="settings-save-current-export"' in html
    assert 'id="settings-reset-section-export"' in html
    assert 'id="settings-save-current-shotml"' in html
    assert 'id="settings-reset-section-shotml"' in html
    assert 'id="settings-merge-layout"' in html
    assert 'id="settings-merge-pip-x"' in html
    assert 'id="settings-pip-size"' in html
    assert 'id="settings-export-quality"' in html
    assert 'id="settings-export-preset"' in html
    assert 'id="settings-export-ffmpeg-preset"' in html
    assert 'id="settings-marker-background-color"' in html
    assert 'id="settings-marker-motion-mode" type="hidden" value="fixed"' in html
    assert 'data-motion-mode-target="settings-marker-motion-mode"' not in html
    assert (
        '<label class="check-row"><input id="settings-marker-follow-motion" type="checkbox" /> Enable motion</label>'
        in html
    )
    assert 'id="settings-marker-opacity"' in html
    assert 'id="settings-shotml-threshold"' in html
    assert 'id="settings-scope-status"' in html
    assert 'id="settings-layer-summary"' not in html
    assert 'class="settings-section collapsed"' in html
    for section_id in [
        "global-template",
        "layout",
        "scoring",
        "pip",
        "overlay",
        "markers",
        "export",
        "shotml",
    ]:
        assert f'data-settings-section="{section_id}"' in html
    assert '<button id="open-project" type="button">Open Project</button>' in html
    assert 'id="open-project-folder"' not in html
    assert "Open PiP" not in html
    assert "Open Score" not in html
    assert "Open Splits" not in html
    assert "Open Markers" not in html
    assert "Open Overlay" not in html
    assert "Open Review" not in html
    assert "Open Export" not in html
    assert "Open Metrics" not in html
    assert "Open ShotML" not in html
    assert "Timing tools still live in the Splits pane" not in html
    assert "Review tools stay in the Review pane" not in html
    assert "Summary and reporting stay in Metrics" not in html
    assert 'id="settings-reset-defaults"' in html
    assert 'id="wizard-panel"' not in html
    assert 'id="wizard-summary"' not in html
    assert 'id="wizard-progress-fill"' not in html
    assert 'id="wizard-copy"' not in html
    assert 'id="wizard-step-list"' not in html
    assert 'id="close-wizard"' not in html
    assert 'id="wizard-back"' not in html
    assert 'id="wizard-next"' not in html
    assert "const WIZARD_STEPS = Object.freeze([" not in js
    assert "function renderWizardPanel() {" not in js
    assert "function openWizardGuide() {" not in js
    assert "function closeWizardGuide() {" not in js
    assert "function goToWizardStep(index) {" not in js
    assert 'data-popup-field="anchor_mode"' in js
    assert 'data-popup-field="shot_id"' in js
    assert 'data-popup-field="name"' in js
    assert "function selectPopupBubble(" in js
    assert "function selectPopupBubbleForShot(shotId" in js
    assert "function importShotPopups() {" in js
    assert "function filteredPopupBubbles(bubbles = popupBubbles()) {" in js
    assert (
        "function renderPopupTimeline(allBubbles = popupBubbles(), visibleBubbles = filteredPopupBubbles(allBubbles)) {"
        in js
    )
    assert "function selectAdjacentPopupBubble(direction) {" in js
    assert "function popupShotMatchesImportMode(shot, mode) {" in js
    assert "function setPopupAuthoringCollapsed(collapsed" in js
    assert 'data-popup-field="quadrant"' not in js
    assert 'data-popup-field="opacity_percent"' in js
    assert 'data-popup-field="follow_motion"' in js
    assert 'data-popup-motion-mode="guided"' in js
    assert "Enable Motion" in js
    assert "data-popup-motion-mode-value" not in js
    assert "function popupBubbleMotionUiMode(bubble = null) {" in js
    assert "function setPopupBubbleMotionUiMode(bubbleId, uiMode, options = {}) {" in js
    assert "function syncPopupBubbleMotionModeControls(card, bubble) {" in js
    assert "function popupBubbleKeyframes(bubble) {" in js
    assert "function popupKeyframePoint(bubble, offsetMs) {" in js
    assert "function addPopupBubbleKeyframeAtPlayhead(bubbleId) {" in js
    assert "function deletePopupBubbleKeyframe(bubbleId, offsetMs) {" in js
    assert "function jumpPopupBubbleKeyframe(bubbleId, direction) {" in js
    assert "function popupMotionInBetweenOffsets(motionPath, finishOffsetMs) {" in js
    assert (
        "function popupMotionAlignPathToFinish(motionPath, finishOffsetMs, startPoint, finishPoint) {"
        in js
    )
    assert "function generatePopupBubbleMotionPathLinear(bubbleId) {" in js
    assert "function generatePopupBubbleMotionPath(bubbleId) {" in js
    assert 'data-popup-action="add_motion_step"' in js
    assert 'data-popup-action="generate_motion_path"' in js
    assert 'data-popup-action="prev_motion_step"' in js
    assert 'data-popup-action="next_motion_step"' in js
    assert 'data-popup-action="remove_motion_step"' in js
    assert 'data-popup-action="clear_motion_path"' in js
    assert 'class="danger-button" data-popup-action="clear_motion_path"' in js
    assert "data-popup-motion-step-count" in js
    assert "data-popup-motion-selected-step" in js
    assert "Selected: Start" in js
    assert (
        "Select Start or Finish below, then place it on the video. Generate first tries to trace the video motion and falls back to evenly spaced in-between points. Add Detail splits the largest remaining time gap."
        in js
    )
    assert "function popupMotionGuidePointRole(bubble, point) {" in js
    assert "function popupMotionGuideStepName(index, point = null, bubble = null) {" in js
    assert "function popupMotionGuidePointName(point, index, bubble = null) {" in js
    assert "function popupMotionGuidePointLabel(point, index, bubble = null) {" in js
    assert "popup-placement-compact-grid" in js
    assert "popup-motion-action-grid" in js
    assert "Enable motion when this marker should move." not in js
    assert (
        "const isSelectedEditorBubble = editingActive && bubble.id === selectedPopupBubbleId();"
        in markers_pane
    )
    assert "bubbleListSection.hidden = workbenchShown;" in js
    assert 'bubbleListSection.style.display = "";' in js
    assert 'bubbleListSection.style.display = markersWorkbenchShown() ? "grid" : "";' not in js
    guided_motion_template = re.search(
        r'<section class="popup-motion-guide" data-popup-motion-mode="guided" hidden>.*?</section>',
        js,
        re.DOTALL,
    )
    assert guided_motion_template is not None
    guided_motion_html = guided_motion_template.group(0)
    assert "popup-motion-action-grid" in guided_motion_html
    assert 'data-popup-action="generate_motion_path"' in guided_motion_html
    assert 'data-popup-action="add_motion_step"' in guided_motion_html
    assert 'data-popup-action="remove_motion_step"' in guided_motion_html
    assert "data-popup-guided-point-list" in guided_motion_html
    assert "Smoothness" not in guided_motion_html
    assert 'data-popup-motion-mode="advanced"' not in js
    assert 'data-popup-action="add_keyframe"' not in js
    assert 'data-popup-action="prev_keyframe"' not in js
    assert 'data-popup-action="next_keyframe"' not in js
    assert 'data-popup-action="auto_trace_motion"' not in js
    assert 'data-popup-action="copy_motion_prev"' not in js
    assert 'data-popup-action="apply_motion_visible"' not in js
    assert 'id="metrics-summary-grid"' in html
    assert 'id="metrics-trend-list"' in html
    assert 'id="metrics-stage-tree" class="metrics-stage-tree"' in html
    assert 'id="metrics-export-csv"' in html
    assert 'id="metrics-export-text"' in html
    assert 'id="show-export-log"' not in html
    assert 'id="export-export-log"' in html
    assert 'id="export-log-modal"' in html
    assert 'id="export-log-output"' in html
    assert 'id="color-picker-modal"' in html
    assert 'id="color-picker-hue"' in html
    assert 'id="color-picker-saturation"' in html
    assert 'id="color-picker-lightness"' in html
    assert 'id="color-picker-hex"' in html
    merge_start = html.index('data-tool-pane="merge"')
    export_start = html.index('data-tool-pane="export"')
    project_start = html.index('data-tool-pane="project"')
    assert merge_start < html.index('id="merge-layout"') < export_start
    assert merge_start < html.index('id="pip-size"') < export_start
    assert 'id="pip-size" type="range" min="1" max="95" step="1" value="35"' in html
    assert 'id="swap-videos"' not in html
    assert export_start < html.index('id="export-preset"') < project_start
    assert export_start < html.index('id="quality"') < project_start
    assert 'id="export-video"' not in html
    assert project_start < html.index('id="match-type"')
    assert 'id="match-stage-number"' not in html
    assert 'id="match-competitor-name"' in html
    assert 'id="match-class"' in html
    assert 'id="match-division"' in html
    assert 'id="layout-threshold"' not in html
    assert 'id="layout-scoring-enabled"' not in html
    assert 'id="layout-overlay-position"' not in html
    assert 'id="layout-max-visible-shots"' not in html
    assert 'id="layout-merge-enabled"' not in html
    assert "Show splits" in html


def test_browser_ui_keeps_video_timeline_waveform_and_inspector_together() -> None:
    html = (STATIC_ROOT / "index.html").read_text()
    app_js = (STATIC_ROOT / "app.js").read_text()
    shell_runtime_js = (
        _read_shell_runtime_source()
        .replace("documentObject.", "document.")
        .replace("windowObject.", "window.")
    )
    activity_js = (STATIC_ROOT / "lib" / "activity.js").read_text()
    api_js = (STATIC_ROOT / "lib" / "api.js").read_text()
    pane_base_js = (STATIC_ROOT / "panes" / "pane-base.js").read_text()
    markers_pane = (STATIC_ROOT / "panes" / "markers-pane.js").read_text()
    review_pane = (STATIC_ROOT / "panes" / "review-pane.js").read_text()
    status_bar_js = (STATIC_ROOT / "components" / "status-bar.js").read_text()
    css = _read_split_css()
    layout_js = (STATIC_ROOT / "lib" / "layout.js").read_text()
    export_pane = (STATIC_ROOT / "panes" / "export-pane.js").read_text()
    merge_pane = (STATIC_ROOT / "panes" / "merge-pane.js").read_text()
    trim_sync_pane = (STATIC_ROOT / "panes" / "trim-sync-pane.js").read_text()
    overlay_canvas_js = (STATIC_ROOT / "components" / "overlay-canvas.js").read_text()
    overlay_pane = (STATIC_ROOT / "panes" / "overlay-pane.js").read_text()
    processing_js = (STATIC_ROOT / "lib" / "processing.js").read_text()
    project_pane = (STATIC_ROOT / "panes" / "project-pane.js").read_text()
    scoring_pane = (STATIC_ROOT / "panes" / "scoring-pane.js").read_text()
    timing_pane = (STATIC_ROOT / "panes" / "timing-pane.js").read_text()
    utils_js = (STATIC_ROOT / "lib" / "utils.js").read_text()
    video_player_js = (STATIC_ROOT / "components" / "video-player.js").read_text()
    waveform_component = (STATIC_ROOT / "components" / "waveform.js").read_text()
    js = _StaticBrowserSourceContract(
        app_source=app_js,
        combined_source="\n".join(  # noqa: FLY002 - clearer for the source inventory
            [
                app_js,
                shell_runtime_js,
                activity_js,
                api_js,
                export_pane,
                layout_js,
                markers_pane,
                merge_pane,
                overlay_canvas_js,
                overlay_pane,
                pane_base_js,
                processing_js,
                project_pane,
                review_pane,
                scoring_pane,
                status_bar_js,
                timing_pane,
                utils_js,
                video_player_js,
                waveform_component,
            ]
        ),
        app_only_snippets=_extract_not_in_js_snippets(
            test_browser_ui_keeps_video_timeline_waveform_and_inspector_together
        ),
    )

    assert html.index('class="video-stage"') < html.index('class="waveform-panel"')
    assert html.index('class="waveform-panel"') < html.index('class="inspector"')
    assert 'id="primary-video" controls' in html
    assert 'controlslist="nofullscreen"' not in html
    assert 'id="secondary-video" playsinline' in html
    assert 'id="secondary-video" muted' not in html
    assert 'id="live-overlay"' in html
    assert 'id="custom-overlay"' in html
    assert 'id="score-layer"' in html
    assert 'id="toggle-primary-audio"' not in html
    assert 'id="toggle-stage-fullscreen"' not in html
    assert 'id="timeline-strip"' not in html
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
    assert 'class="status-bar-actions"' in html
    assert 'class="panel-lock-button panel-lock-button-status"' in html
    assert 'id="toggle-layout-lock-video"' in html
    assert "panel-lock-button-video" not in html
    assert (
        html.index('class="status-bar"')
        < html.index('id="toggle-layout-lock-video"')
        < html.index('class="review-grid"')
    )
    assert 'id="toggle-layout-lock-waveform"' not in html
    assert 'id="toggle-layout-lock-inspector"' not in html
    assert 'data-waveform-mode="select"' in html
    assert 'data-waveform-mode="add"' in html
    assert 'data-waveform-mode="beep"' not in html
    assert 'id="waveform-window"' in html
    assert 'id="waveform-window-track"' in html
    assert 'id="waveform-window-handle"' in html
    assert 'id="waveform-shot-list"' in html
    assert 'id="timing-workbench"' in html
    assert 'id="timing-result"' in html
    assert 'id="timing-enabled"' in html
    assert 'id="timing-imported-summary"' in html
    assert 'id="expand-timing"' in html
    assert '<button id="expand-timing" type="button">Edit</button>' in html
    assert (
        '<label class="check-row"><input id="timing-enabled" type="checkbox" /> Enable Splits</label>'
        in html
    )
    assert 'aria-label="Use waveform select mode"' in html
    assert 'aria-label="Use waveform add shot mode"' in html
    assert 'id="selected-shot-panel"' not in html
    assert 'id="selected-shot-copy"' not in html
    assert 'id="selected-timing-shot"' not in html
    assert "data-nudge=" not in html
    assert 'id="delete-selected"' not in html
    assert html.index('id="timing-enabled"') < html.index('id="expand-timing"')
    assert html.index('id="expand-timing"') < html.index('id="timing-summary"')
    assert html.index('id="timing-summary"') < html.index('id="timing-imported-summary"')
    assert html.index('id="timing-imported-summary"') < html.index('id="timing-table"')
    assert html.index('id="timing-table"') < html.index('id="threshold"')
    timing_start = html.index('data-tool-pane="timing"')
    shotml_start = html.index('data-tool-pane="shotml"')
    assert timing_start < html.index('id="timing-table"') < shotml_start
    assert shotml_start < html.index('id="threshold"')
    assert html.index("waveform-header") < html.index('id="waveform"')
    assert html.index('id="waveform"') < html.index('class="waveform-actions waveform-footer"')
    assert 'id="badge-style-grid"' in html
    assert 'id="score-color-grid"' in html
    assert 'id="show-overlay"' in html
    assert "Overlay visibility" not in html
    assert '<option value="none">Hidden</option>' in html
    assert '<option value="bottom">Bottom</option>' in html
    assert "Stack gap" in html
    assert "Edge padding" in html
    assert "Score Colors" in html
    assert html.count('<option value="custom">Custom</option>') >= 2
    assert 'id="project-name"' in html
    assert 'id="project-description"' in html
    assert 'id="merge-media-input"' in html
    assert 'id="merge-media-list"' in html
    assert 'id="media-pane"' in html
    assert 'id="pip-x"' in html
    assert 'id="pip-y"' in html
    assert "Defaults" in html
    assert "Stage Defaults" not in html
    assert 'id="restore-merge-defaults"' in html
    assert (
        "Set the defaults here, then fine-tune each PiP item in its own card so preview and export stay in sync."
        not in html
    )
    assert (
        "PiP X and Y use normalized positions: 0 pins the item to the left or top edge, and 1 pins it to the right or bottom edge."
        not in html
    )
    assert (
        "Each PiP card below has its own size, placement, transparency, and sync nudges."
        not in html
    )
    assert 'id="max-visible-shots"' in html
    assert 'id="shot-quadrant"' in html
    assert '<option value="custom">Custom</option>' in html
    assert 'id="shot-direction"' in html
    assert 'id="overlay-custom-x"' in html
    assert 'id="bubble-width"' in html
    assert 'id="bubble-width" type="number" min="0" max="400" step="4" placeholder="auto"' in html
    assert 'id="bubble-height" type="number" min="0" max="220" step="4" placeholder="auto"' in html
    assert 'id="overlay-font-family"' in html
    assert 'id="timer-lock-to-stack"' in html
    assert 'id="draw-lock-to-stack"' in html
    assert 'id="score-lock-to-stack"' in html
    assert 'id="show-timer"' in html
    assert 'id="review-text-box-list"' in html
    assert "Review Text Boxes" in html
    assert 'data-text-box-field="lock_to_stack"' in review_pane
    assert "Lock to shot stack" in review_pane
    assert "Imported summary" not in review_pane
    assert "Content source" not in review_pane
    assert "PractiScore stage summary" not in review_pane
    assert '<span class="style-card-label">Background</span>' in review_pane
    assert '<span class="style-card-label">Opacity</span>' in review_pane
    assert 'type="range" data-field="opacity"' not in js
    assert 'data-text-box-field="opacity" type="number"' in review_pane
    assert 'data-field="opacity" min="0" max="100" step="1" value="90"' in js
    assert 'id="layout-threshold"' not in html
    assert 'id="scoring-preset"' in html
    assert 'class="scoring-toggle-row"' in html
    assert 'id="scoring-imported-summary"' in html
    assert 'id="scoring-table"' in html
    assert 'id="scoring-workbench-table"' in html
    assert html.index('id="scoring-enabled"') < html.index('id="expand-scoring"')
    assert html.index('id="expand-scoring"') < html.index('id="scoring-preset"')
    assert (
        "Score and penalty edits live here. The Splits pane stays read-only so timing edits do not fight scoring edits."
        not in html
    )
    assert "Common shorthand: M miss, NS no-shoot, PE procedural error" not in html
    assert html.index('id="scoring-workbench"') < html.index('class="inspector"')
    assert 'id="scoring-penalty-grid"' not in html
    assert 'id="score-letter"' not in html
    assert 'id="timer-x"' in html
    assert 'id="timer-y"' in html
    assert 'id="draw-x"' in html
    assert 'id="draw-y"' in html
    assert 'id="score-x"' in html
    assert 'id="score-y"' in html
    assert 'id="browse-project-path"' in html
    assert '$("open-project").addEventListener("click", browseProjectPath);' in shell_runtime_js
    assert 'id="browse-project-output-root"' in html
    assert 'id="browse-primary-path"' not in html
    assert 'id="browse-secondary-path"' not in html
    assert 'id="export-preset"' in html
    assert 'id="crop-center-x"' not in html
    assert 'id="crop-center-y"' not in html
    assert 'id="target-width"' in html
    assert 'id="target-height"' in html
    assert 'id="frame-rate"' in html
    assert 'id="video-codec"' in html
    assert 'id="video-bitrate"' in html
    assert 'id="audio-codec"' in html
    assert 'id="audio-sample-rate"' in html
    assert 'id="audio-bitrate"' in html
    assert 'id="audio-output-level"' in html
    assert 'id="color-space"' in html
    assert 'id="ffmpeg-preset"' in html
    assert 'id="show-export-log"' not in html
    assert 'id="export-log-output"' in html
    assert 'id="export-log-modal"' in html
    assert "Active stage settings" in html
    assert "/api/files/primary" in js
    assert "/api/files/merge" in js
    assert "/api/files/practiscore" in js
    assert "/api/project/details" in js
    assert "/api/project/practiscore" in js
    assert "/api/dialog/path" in js
    assert "/api/export/settings" in js
    assert "/api/export/preset" in js
    assert "/api/events/delete" in timing_pane
    assert "/api/activity" in activity_js
    assert "Remove timing event" in timing_pane
    assert 'activity("api.refresh", {})' in api_js
    assert (
        "if (!response.ok || data.error) throw new Error(data.error || response.statusText);" in js
    )
    assert 'throw new Error("Received invalid project state from the local server.");' in api_js
    assert 'activity("button.click"' in activity_js
    assert "wireGlobalActivityLogging" in js
    assert 'document.addEventListener("click"' in activity_js
    assert "handleWaveformPointerDown" in js
    assert "handleWaveformPointerMove" in js
    assert "handleKeyboardEdit" in js
    assert "function keyboardEditTargetIsEditable(event) {" in js
    assert "if (keyboardEditTargetIsEditable(event)) return;" in js
    assert "scheduleSecondaryPreviewSync" in js
    assert "autoApplyShotMLSettings" in js
    assert "autoApplyOverlay" in js
    assert "autoApplyMerge" in js
    assert "autoApplyExportLayout" in js
    assert "autoApplyExportSettings" in js
    assert "autoApplyScoring" in js
    assert "/api/layout" not in js
    assert "renderScoringPenaltyFields" not in js
    assert "renderPractiScoreSummaries" in js
    assert "renderMergeMediaList" in js
    assert "renderCollapsibleInspectorSections" in js
    assert 'toggle.textContent = expanded ? "v" : ">";' in js
    assert "const INSPECTOR_COMPACT_WIDTH = 700;" in js
    assert (
        'shell.classList.toggle("inspector-compact", renderedLayoutSizes.inspectorWidth < INSPECTOR_COMPACT_WIDTH);'
        in layout_js
    )
    assert (
        'buildSourceNumberInput("Position X", "x", normalizedCoordinateValue(source.pip_x) ?? 1, 0, 1, 0.01, "0 is left, 1 is right.")'
        in merge_pane
    )
    assert 'data-sync-delta="10"' in trim_sync_pane
    assert 'text.textContent = "Opacity";' in merge_pane
    assert "pip_size_percent: nextSize," in merge_pane
    assert "let projectDetailsDraft = { name: null, description: null" in js
    assert "readProjectDetailsPayload" in js
    assert "applyProjectDetailsDraft" in js
    assert "mergeProjectDetailsDraft" in js
    assert "readPractiScoreContextPayload" in js
    assert "validatePractiScoreSelection" in js
    assert "renderPractiScoreOptionLists" in js
    assert "renderPractiScoreSelect" in js
    assert "syncPractiScoreSelectionFields" in js
    assert "function practiScoreStageValues() {" in js
    assert "function practiScoreNameValues() {" in js
    assert "function practiScorePlaceValues() {" in js
    assert "autoApplyProjectDetails" in js
    assert "autoApplyPractiScoreContext" in js
    assert "cyclePractiScoreValue" not in js
    assert "handlePractiScoreNameKeydown" not in js
    assert "handlePractiScorePlaceKeydown" not in js
    assert "renderPractiScoreDatalist" not in js
    assert "/api/shots/restore" in timing_pane
    assert "/api/scoring/restore" in js
    assert "syncExportPathControl" in js
    assert "buildExportPayload" in js
    assert "syncOverlayPreviewStateFromControls" in js
    assert "syncMergePreviewStateFromControls" in js
    assert "controlIsActive" in js
    assert "syncControlValue" in js
    assert "importTypedPath" in js
    assert "syncSecondaryPreview" in js
    assert "replaceAll(" not in js
    assert "merge-preview" in js
    assert 'pickPath("primary", "primary-file-path", async (path)' not in js
    assert 'pickPath("secondary", "secondary-file-path", async (path)' not in js
    assert 'pickPath("project_folder", "project-path", async (selectedPath)' in project_pane
    assert "async function probeProjectFolder(path) {" in js
    assert 'const response = await fetchImpl("/api/project/probe", {' in project_pane
    assert 'async function createNewProject(path = "") {' in js
    assert 'async function useProjectFolder(path = "") {' in js
    assert "await flushPendingProjectDrafts();" in js
    assert 'return pickPath("project_open", "project-path");' not in js
    assert 'const kind = currentPath ? "project_open" : "project_save";' not in js
    assert 'preset: $("export-preset").value,' in js
    assert "overlay: readOverlayPayload()," in js
    assert "merge: {" in js
    assert "scoring: {" in js
    assert 'const showOverlay = $("show-overlay")?.checked ?? true;' in overlay_pane
    assert "review_show_markers: true," in js
    assert "review_show_pip: true," in js
    assert (
        "review_show_markers: Boolean(uiState.review_show_markers ?? DEFAULT_PROJECT_UI_STATE.review_show_markers),"
        in js
    )
    assert (
        "review_show_pip: Boolean(uiState.review_show_pip ?? DEFAULT_PROJECT_UI_STATE.review_show_pip),"
        in js
    )
    assert (
        'review_show_markers: $("markers-enable")?.checked ?? $("show-markers")?.checked ?? DEFAULT_PROJECT_UI_STATE.review_show_markers,'
        in js
    )
    assert (
        'review_show_pip: $("show-pip")?.checked ?? DEFAULT_PROJECT_UI_STATE.review_show_pip,' in js
    )
    assert '$("markers-enable")?.checked' in js
    assert 'syncControlChecked($("show-markers"), normalized.review_show_markers);' in js
    assert '$("reset-layout")?.addEventListener("click", resetLayout);' in js
    assert '["resize-rail", "railWidth"],' in js
    assert 'syncControlChecked($("show-pip"), normalized.review_show_pip);' in js
    assert (
        'const position = showOverlay ? (getOverlayVisibilityPosition() || currentState()?.settings?.overlay_position || "bottom") : "none";'
        in overlay_pane
    )
    assert "sync_offset_ms: currentSourceSyncOffsetMs(source)," in js
    assert "cancelPendingExportDrafts();" in js
    assert "function buildExportPayload(path) {" in js
    assert 'await callApi("/api/export", payload);' not in js
    assert "saveProjectFlow" not in js
    assert "useProjectFolder" in js
    assert 'await callApi("/api/project/details", readProjectDetailsPayload());' in js
    assert 'const currentPath = normalizeProjectFolderInput(state?.project?.path || "");' in js
    assert "const probeResult = await probeProjectFolder(targetPath);" in project_pane
    assert "if (requestId !== getProjectFolderProbeRequestId()) {" in project_pane
    assert 'id="export-path"' not in html
    assert 'id="browse-export-path"' not in html
    assert '$("browse-project-output-root").addEventListener("click", () => pickPath(' in js
    assert 'const path = requireValue("export-path", "Output video path");' not in js
    assert "setExportPathDraft(path);" not in js
    assert 'input.step = "0.01";' in js
    assert "Math.round((Number(value) || 0) * 1000)" in timing_pane
    assert "const TIMING_COLUMN_DEFAULTS = Object.freeze({" in js
    assert "timing_column_widths: { ...TIMING_COLUMN_DEFAULTS }," in js
    assert "function beginTimingColumnResize(tableId, columnId, event) {" in js
    assert "function moveTimingColumnResize(event) {" in js
    assert "function endTimingColumnResize(event) {" in js
    assert "timingAdjustmentDrafts.get(row.shot_id) ?? signedSeconds(adjustmentMs)" in js
    assert "function buildTimingRowControlCell(row, editing) {" in js
    assert "preserve_following_splits: false" in timing_pane
    assert 'handle.className = "timing-column-resize";' in js
    assert "openProjectWithDialog" not in js
    assert "resetMediaElement" in js
    assert '$("penalties").value = state.project.scoring.penalties' not in js
    assert "renderExportPresetOptions" in js
    assert "syncExportPathControl();" in js
    assert "processingForPath" in processing_js
    assert "Exporting video..." in processing_js
    assert "Importing media..." in processing_js
    assert "Parsing PractiScore results and staging a local copy" in js
    assert 'setStatus("Select a PractiScore results file (.csv or .txt).");' in js
    assert "function openHiddenFileInput(inputId) {" in js
    assert 'if (typeof input.showPicker === "function") {' in js
    assert '"practiscore",' in js
    assert 'projectRoot ? `${projectRoot}/CSV` : ""' in js
    assert 'await callApi("/api/import/practiscore", { path: selectedPath });' in js
    assert "async function openPractiScoreDashboard() {" in js
    assert 'fetch("/api/practiscore/dashboard/open", {' in api_js
    assert "function hasActiveProject() {" in js
    assert "function setProjectActionAvailability() {" in js
    assert "window.alert(folderMessage);" in js
    assert "function renderPractiScoreRemoteState() {" not in js
    assert "function renderPractiScoreRemoteMatchOptions() {" not in js
    assert "async function connectPractiScore() {" not in js
    assert "async function clearPractiScoreSession() {" not in js
    assert "async function importSelectedPractiScoreMatch() {" not in js
    assert '$("open-practiscore-dashboard")?.addEventListener("click", async () => {' in js
    assert "await openPractiScoreDashboard();" in js
    assert '$("delete-project").addEventListener("click", async () => {' in js
    assert "Delete project metadata for:" in js
    assert 'document.addEventListener("fullscreenchange", handleStageFullscreenChange);' in js
    assert "media.defaultMuted = false;" in merge_pane
    assert "media.muted = false;" in merge_pane
    assert "media.muted = true;" not in js
    assert (
        'await callApi("/api/project/practiscore", readPractiScoreContextPayload());\n    $("practiscore-file-input")?.click();'
        not in js
    )
    assert (
        'if (!validatePractiScoreSelection()) return;\n    setStatus("Select a PractiScore results file (.csv or .txt).");\n    $("practiscore-file-input")?.click();'
        not in js
    )
    assert "Opening file browser..." not in js
    assert "function readExportLayoutPayload()" in js
    assert "function scheduleExportLayoutApply()" in js
    assert "function scheduleExportSettingsApply()" in js
    assert "function scheduleProjectDetailsApply()" in js
    assert "function schedulePractiScoreContextApply()" in js
    assert "let lastSubmittedProjectUiStatePayloadKey = null;" in js
    assert "function projectUiStatePayloadKey(payload = {}) {" in js
    assert "function shouldApplyProjectUiStatePayload(payload) {" in js
    assert (
        "async function applyProjectUiStatePayload(payload = readProjectUiStatePayload()) {" in js
    )
    assert "if (payloadKey === lastSubmittedProjectUiStatePayloadKey) return null;" in js
    assert "lastSubmittedProjectUiStatePayloadKey = payloadKey;" in js
    assert "function sendProjectUiStateKeepalive(payload = readProjectUiStatePayload()) {" in js
    assert "await applyProjectUiStatePayload(captured.projectUiState);" in project_pane
    assert "sendProjectUiStateKeepalive();" in project_pane
    assert "function scheduleOverlayApply()" in js
    assert "function scheduleMergeApply()" in js
    assert "function scheduleScoringApply()" in js
    assert 'callApi("/api/export/settings", payload);' in js
    assert '$(id).addEventListener("change", scheduleExportLayoutApply);' in js
    assert "scoring-active" in js
    assert "layoutLocked" in js
    assert "applyLayoutState" in js
    assert "beginLayoutResize" in js
    assert "syncOverlayCoordinateControlState" in js
    assert "function overlayTextBoxDisplayText(box)" in js
    assert "function renderTextBoxEditors()" in js
    assert "function downloadExportLog() {" in js
    assert "function buildMetricsRows()" in js
    assert "function renderMetricsPanel()" in js
    assert 'function openExportLogModal(startingState = "")' in js
    assert "function closeExportLogModal()" in js
    assert "function exportMetrics(kind)" in js
    assert "function mediaCacheToken() {" in js
    assert 'function buildMediaUrl(basePath, sourcePath = "") {' in js
    assert "function practiScoreSelectionValue(value) {" in js
    assert "function readPractiScoreContextPayload() {" in project_pane
    assert (
        "function ensureWaveformTimeVisible(timeMs, { center = false, paddingRatio = 0.12, persist = true } = {}) {"
        in js
    )
    assert "function renderWaveformNavigator() {" in js
    assert "function handleWaveformNavigatorPointerDown(event) {" in js
    assert "function startWaveformPanDrag(event) {" in js
    assert "function updateWaveformPanDrag(event) {" in js
    assert "let draggingShotPointerId = null;" in js
    assert "let interactionPreviewFrame = null;" in js
    assert (
        "let pendingInteractionPreview = { video: false, waveform: false, overlay: false };" in js
    )
    assert (
        "function scheduleInteractionPreviewRender({ video = false, waveform = false, overlay = false } = {}) {"
        in js
    )
    assert "function flushInteractionPreviewRender() {" in js
    assert (
        "const segmentsByShotId = new Map((state.timing_segments || []).map((segment) => [segment.shot_id, segment]));"
        in js
    )
    assert "return (state.split_rows || []).map((row) => {" in js
    assert "const ACTIVITY_POLL_INTERVAL_MS = 250;" in js
    assert "Show Log (${Math.round" not in (STATIC_ROOT / "panes" / "export-pane.js").read_text()
    finish_index = api_js.index('finishProcessing(data.status || "Ready.")')
    assert finish_index < api_js.index("requestRender();", finish_index)
    assert (
        "persistedLines.length >= visibleLines.length ? persistedLines : visibleLines"
        in export_pane
    )
    assert (
        "fetch(`/api/activity/poll?after=${runtime.activityCursor}&job_after=${runtime.processingLogCursor || 0}`)"
        in activity_js
    )
    assert 'const CUSTOM_QUADRANT_VALUE = "custom";' in js
    assert 'const ABOVE_FINAL_TEXT_BOX_VALUE = "above_final";' in js
    assert "const BADGE_FONT_SIZES = {" in js
    assert "PREVIEW_VIDEO_CONTROLS_SAFE_BOTTOM_PX" not in js
    assert "function syncOverlayFontSizePreset()" in js
    assert "function ensureShotQuadrantDefaults()" in js
    assert 'activity("layout.resize.start"' in layout_js
    assert 'activity("layout.resize.commit"' in layout_js
    assert 'activity("layout.unlock.request"' in layout_js
    assert "toggleLayoutLock();\n    }\n    const startSize =" in layout_js
    assert "[kind]: true," in layout_js
    assert "|| popupBubbleDrag" in js
    assert "function persistLayoutSize(key, value, { renderWaveformNow = true } = {}) {" in js
    assert "function previewLayoutSize(key, value) {" in js
    assert "if (runtime.state && renderWaveformNow) renderWaveform();" in layout_js
    assert (
        'font_size: Number($("overlay-font-size").value || badgeFontSizes[$("badge-size").value] || 14),'
        in overlay_pane
    )
    assert "text_boxes: textBoxes.map((box) => ({" in js
    assert "const preserveExistingTextBoxes = Boolean(" in js
    assert (
        "overlay.text_boxes = (preserveExistingTextBoxes ? previousTextBoxes : payloadTextBoxes)"
        in js
    )
    assert "function createOverlayTextBoxId() {" in js
    assert "function overlayTextBoxAutoSize(box) {" in js
    assert "function syncOverlayTextBoxSizeControls(boxId) {" in js
    assert "function setOverlayTextBoxField(boxId, field, rawValue, options = {}) {" in js
    assert "function beginTextBoxDrag(event) {" in js
    assert "if (getTextBoxDrag() || getOverlayBadgeDrag()) return;" in overlay_pane
    assert "function moveTextBoxDrag(event) {" in js
    assert "function endTextBoxDrag(event) {" in js
    assert "function normalizePopupMotionPath(path) {" in js
    assert "function popupBubbleMotionPath(bubble) {" in js
    assert "function popupBubblePoint(bubble, positionMs = null) {" in js
    assert "function popupBubbleKeyframes(bubble) {" in js
    assert "function popupKeyframePoint(bubble, offsetMs) {" in js
    assert "function popupMotionInBetweenOffsets(motionPath, finishOffsetMs) {" in js
    assert (
        "function popupMotionAlignPathToFinish(motionPath, finishOffsetMs, startPoint, finishPoint) {"
        in js
    )
    assert "function generatePopupBubbleMotionPathLinear(bubbleId) {" in js
    assert "function popupOverlayPixelPoint(frameRect, xValue, yValue) {" in js
    assert "function renderPopupKeyframeOverlay(popupOverlay, bubble, frameRect) {" in js
    assert "function seekPrimaryVideoToTimeMs(timeMs) {" in js
    assert "renderLiveOverlay(clampedTimeMs);" in js
    assert "renderWaveformPlayhead(clampedTimeMs);" in js
    assert "seekPopupBubbleMotionPoint(bubbleId, offsetMs);" in js
    assert "function seekPrimaryVideoToShot(shotId) {" in js
    assert "function updatePopupBubbleMotionPoint(bubble, offsetMs, x, y) {" in js
    assert "function renderPopupBubbleMotionGuide(card, bubble) {" in js
    assert "function popupBubbleAutoSize(bubble) {" in js
    assert "function popupBubblePlacementSelectorStyle(bubble) {" in js
    assert "function popupBubbleRenderStyle(bubble) {" in js
    assert "function popupTextForShotId(shotId) {" in js
    assert "function popupBubbleResolvedText(bubble) {" in js
    assert "function resolvedPopupBubbleSize(bubble) {" in js
    assert "function syncPopupBubbleSizeControls(bubbleId) {" in js
    assert "function popupBubbleVisibleWindow(bubble) {" in js
    assert "function popupBubbleRenderPositionMs(bubble, positionMs) {" in js
    assert "function popupBubbleIsVisibleAtPosition(bubble, positionMs) {" in js
    assert "function popupBubbleSeekTimeMs(bubble) {" in js
    assert (
        "{ seek = true, reveal = true, focus = false, activateTool = false, expand = false, rerender = true } = {}"
        in js
    )
    assert (
        'card.querySelector(".popup-bubble-button")?.addEventListener("click", (event) => {' in js
    )
    assert "expand: false,\n    });\n  };" in js
    assert "setPopupBubbleExpanded(bubble.id, !isPopupBubbleExpanded(bubble.id));" in js
    assert (
        "if (!popupBubbleExpansion.get(bubbleId)) popupBubbleExpansion.set(bubbleId, true);"
        not in js
    )
    assert (
        "const isSelectedEditorBubble = editingActive && bubble.id === selectedPopupBubbleId();"
        in markers_pane
    )
    assert (
        "positionMs: isVisible ? positionMs : popupBubbleRenderPositionMs(bubble, positionMs),"
        in js
    )
    assert 'badge.classList.toggle("popup-selected", Boolean(entry.selected));' in js
    assert 'badge.classList.toggle("popup-outside-window", Boolean(entry.outsideWindow));' in js
    assert "const selectorStyle = editingActive && entry.selected" in js
    assert 'badge.classList.toggle("popup-placement-selector", Boolean(selectorStyle));' in js
    assert "if (shot) return shot.time_ms;" in js
    assert "setPopupBubbles(nextBubbles, { commit: false, rerender: false });" in js
    assert 'data-popup-field="follow_motion"' in js
    assert 'popupBubbleMotionUiMode(bubble) === "fixed"' in js
    assert "dataset.popupKeyframeOffset" in js
    assert 'const selectorToken = selectorHasText ? String(selectorStyle?.token || "") : "";' in js
    assert "span.style.color = token.color;" in js
    assert "scoreBadgeTokens(shot)" in js
    assert "badge.style.width = `${scaledWidth}px`;" in js
    assert '<option value="above_final">Above Final Box</option>' in js
    assert 'source === "stage_name" ? "top_middle" : "top_left"' in review_pane
    assert "if (customX === null || customY === null) return false;" in js
    assert 'group.style.left = "0px";' in js
    assert 'group.style.top = "0px";' in js
    assert "Switch to Custom placement to edit X and Y directly." not in js
    assert "Keeps this box centered above the final score badge once it appears." not in js
    assert "syncOverlayFontSizePreset();" in js
    assert (
        'const seededCoordinates = resolveRenderedOverlayBadgeCoordinates("shots") || { x: 0.5, y: 0.5 };'
        in js
    )
    assert (
        'if (!$("overlay-custom-y").value) syncControlValue($("overlay-custom-y"), seededCoordinates.y);'
        in js
    )
    assert "function pinCustomOverlayAnchor(overlay, frameRect, customPoint = null) {" in js
    assert (
        "if (usesCustomQuadrant(currentState().project.overlay.shot_quadrant) && overlay.childElementCount > 0) {"
        in overlay_pane
    )
    assert (
        "const anchorOffsetX = (badgeRect.left - overlayRect.left) + (badgeRect.width / 2);" in js
    )
    assert "const anchorOffsetY = (badgeRect.top - overlayRect.top) + (badgeRect.height / 2);" in js
    assert 'timerBadge.dataset.overlayDrag = "timer";' in js
    assert 'drawBadge.dataset.overlayDrag = "draw";' in js
    assert "function splitSeconds(ms)" in utils_js
    assert "function currentPipSizePercent(source = null, fallback = 35) {" in js
    assert "function currentSourceSyncOffsetMs(source = null) {" in js
    assert "function mergePreviewTargetTime(primaryTime, source = null) {" in js
    assert "function formatShotBadgeSuffix(shot) {" in js
    assert (
        "function resolvedSplitMsForShot(shotId, shotNumber = null, absoluteTimeMs = null) {" in js
    )
    assert 'grid.querySelectorAll(".style-card[data-badge]")' in js
    assert (
        'scoreGrid.querySelectorAll(".score-color-input[data-letter]").forEach((input) => {' in js
    )
    assert "function scoringColorOptions() {" in js
    assert "function openColorPicker(control) {" in js
    assert "function closeColorPicker({ commit = true } = {}) {" in js
    assert "function renderColorPickerSwatches() {" in js
    assert "const scoreOptions = scoringColorOptions();" in js
    assert "const scoreKeys = scoreOptions.map((option) => option.key);" in js
    assert "...Object.keys(state.project.overlay.scoring_colors || {})," not in js
    assert "exportSettings.crop_center_x" in js
    assert "exportSettings.crop_center_y" in js
    assert "const FINAL_SHOT_FLASH_HALF_PERIOD_MS" not in js
    assert "const FINAL_SHOT_FLASH_CYCLES" not in js
    assert "const FINAL_SHOT_FLASH_DURATION_MS" not in js
    assert "const customBadge = event.target instanceof Element" in js
    assert 'customBadge.dataset.textBoxDrag = "true";' in js
    assert "customBadge.dataset.textBoxId = box.id;" in js
    assert 'customBadge.dataset.textBoxSource = box.source || "manual";' in js
    assert (
        "box = overlayTextBoxes().find((item) => item.source === customBadge.dataset.textBoxSource);"
        in js
    )
    assert '$("video-stage").addEventListener("pointerdown", beginTextBoxDrag, true);' in js
    assert '$("video-stage").addEventListener("mousedown", beginTextBoxDrag, true);' in js
    assert 'document.addEventListener("pointerdown", beginTextBoxDrag, true);' in js
    assert 'document.addEventListener("mousedown", beginTextBoxDrag, true);' in js
    assert 'document.addEventListener("mousemove", moveTextBoxDrag);' in js
    assert 'document.addEventListener("mouseup", endTextBoxDrag);' in js
    assert "if (positionTextBoxBadge(customBadge, box, frameRect, {" in js
    assert (
        "anchorBadge: box.quadrant === aboveFinalTextBoxValue ? finalScoreBadge : null,"
        in overlay_pane
    )
    assert (
        "const renderedTextBoxCount = customOverlay.querySelectorAll(\"[data-text-box-drag='true']\").length;"
        in js
    )
    assert (
        "if (nextCustomOverlayKey !== getCustomOverlayRenderKey() || renderedTextBoxCount !== textBoxEntries.length) {"
        in overlay_pane
    )
    assert 'customOverlay.classList.toggle("has-badge", customOverlay.childElementCount > 0);' in js
    assert 'if (result) setActiveTool("scoring");' not in js
    assert (
        'item.addEventListener("click", () => selectShot(segment.shot_id, { revealInWaveform: true, centerWaveform: true }));'
        in js
    )
    assert '$("show-export-log")?.addEventListener("click", openExportLogModal);' not in js
    assert '$("export-export-log")?.addEventListener("click", downloadExportLog);' in js
    assert '$("metrics-export-csv")?.addEventListener("click", () => exportMetrics("csv"));' in js
    assert "function defaultScoreLetter(ruleset = activeScoringRuleset()) {" in js
    assert 'function shotBadgeBaseText(shotNumber, splitText, intervalLabel = "") {' in js
    assert 'function scoreBadgeContent(shot, shotNumber, splitText, intervalLabel = "") {' in js
    assert "currentState().project.overlay.show_shot_scores" in js
    assert 'const firstTokenGap = "  ";' in js
    assert 'fragment.style.whiteSpace = "pre";' in js
    assert 'const unsetOption = document.createElement("option");' not in js
    assert "const preservedScore = preservedScoreSelects.get(segment.shot_id);" in js
    assert (
        "select.value = preservedScore ? preservedScore.value : (segment.score_letter || defaultScore);"
        in js
    )
    assert "scoreCell.textContent = row.score_letter || defaultScore;" not in js
    assert '{ label: "ShotML Confidence %", columnId: "confidence", resizable: true }' in js
    assert '"timing-table": ["segment", "split", "total", "action"],' in js
    assert "function splitRowActionSummary(row) {" in js
    assert "function splitRowIntervalLabel(row) {" in js
    assert "function splitRowCumulativeMs(row) {" in js
    assert "function buildSplitRowActionCell(row, expandedTable) {" in js
    assert "function maximumSplitRowActionLabelLength() {" in js
    assert "const actionCell = buildSplitRowActionCell(row, expandedTable);" in js
    assert "totalCell.textContent = splitSeconds(splitRowCumulativeMs(row));" in js
    assert "finalCell.textContent = splitSeconds(splitRowFinalTimeMs(row));" in js
    assert 'function deleteShotById(shotId, source = "selected") {' in js
    assert 'deleteShotById(row.shot_id, "timing_row")' in js
    assert 'deleteShotById(segment.shot_id, "scoring_row")' in js
    assert "function refreshReviewMediaFrame() {" in js
    assert "if (result) refreshReviewMediaFrame();" in js
    assert (
        'if (expanded) root.classList.remove("timing-expanded", "metrics-expanded", "scoring-expanded", "markers-expanded");'
        in js
    )
    assert (
        'collapseClasses: ["waveform-expanded", "metrics-expanded", "scoring-expanded", "markers-expanded"],'
        in timing_pane
    )
    assert (
        'if (expanded) root.classList.remove("waveform-expanded", "timing-expanded", "scoring-expanded", "markers-expanded");'
        in js
    )
    assert "function setMetricsExpanded(expanded, { persistUiState = true } = {}) {" in js
    assert "function setScoringWorkbenchExpanded(expanded, { persistUiState = true } = {}) {" in js
    assert "timing_enabled: true," in js
    assert (
        "timing_enabled: Boolean(uiState.timing_enabled ?? DEFAULT_PROJECT_UI_STATE.timing_enabled),"
        in js
    )
    assert (
        'timing_enabled: $("timing-enabled")?.checked ?? DEFAULT_PROJECT_UI_STATE.timing_enabled,'
        in js
    )
    assert 'syncControlChecked($("timing-enabled"), normalized.timing_enabled);' in js
    assert "function timingSummaryRows() {" in status_bar_js
    assert "function renderTimingSummary() {" in status_bar_js
    assert (
        'renderDetailsList("timing-imported-summary", enabled && totalShots > 0 ? timingSummaryRows() : []);'
        in status_bar_js
    )
    assert "summary.textContent = !enabled" in status_bar_js
    assert "function renderSelection() {" not in js
    assert '"selected-shot-copy"' not in js
    assert '"selected-timing-shot"' not in js
    assert '$("delete-selected").addEventListener("click", deleteSelectedShot);' not in js
    assert 'document.querySelectorAll("[data-nudge]")' not in js
    assert 'expandedClass: "scoring-expanded",' in scoring_pane
    assert (
        "function setActiveTool(tool, { collapseExpandedLayout = true, persistUiState = true } = {}) {"
        in js
    )
    assert "if (collapseExpandedLayout && hadExpandedLayout) {" in js
    assert "if (changed) {" in js
    assert (
        "setActiveTool(normalized.active_tool, { collapseExpandedLayout: false, persistUiState: false });"
        in js
    )
    assert (
        "setActiveTool(activeTool, { collapseExpandedLayout: false, persistUiState: false });" in js
    )
    assert js.index(
        "setActiveTool(normalized.active_tool, { collapseExpandedLayout: false, persistUiState: false });"
    ) < js.index("setWaveformExpanded(normalized.waveform_expanded, { persistUiState: false });")
    apply_ui_state_body = js.split(
        "function applyProjectUiState(uiState = DEFAULT_PROJECT_UI_STATE) {", 1
    )[1].split("function normalizedCoordinateValue", 1)[0]
    assert "collapseMinimizableInspectorItems" not in apply_ui_state_body
    assert 'const PIP_DEFAULTS_SECTION_ID = "pip-defaults";' in js
    assert 'if (firstSource && sourceId === sourceIdentifier(firstSource, "0")) return true;' in js
    assert "if (sourceId === PIP_DEFAULTS_SECTION_ID) return;" in js
    assert "/media/primary-audio" not in js
    assert "function primaryAudioPreviewNeeded(video) {" not in js
    assert "function ensurePrimaryAudioPreview(video) {" not in js
    assert (
        "function syncPrimaryAudioPreview({ forceSeek = false, allowDriftCorrection = false } = {}) {"
        not in js
    )
    assert 'text.startsWith("Hit Factor") || text.startsWith("Final ")' in js
    assert "function formatPractiScoreTime(value, { includeUnits = true } = {}) {" in js
    assert '["PS - Score", importedStageRecordedScoreLabel(imported)],' in js
    assert '["PS - Penalties", importedStagePenaltyLabel(imported)],' in js
    assert '"Stage Place"' not in js
    assert 'id="practiscore-import-summary"' in html
    assert 'class="details metrics-details scoring-imported-details"' not in html
    assert 'syncControlChecked($("show-overlay"), overlayPosition !== "none");' in js
    assert 'syncControlChecked($("markers-enable"), normalized.review_show_markers);' in js
    assert (
        'syncControlChecked($("show-markers"), project.ui_state?.review_show_markers ?? DEFAULT_PROJECT_UI_STATE.review_show_markers);'
        in js
    )
    assert (
        'syncControlChecked($("show-pip"), project.ui_state?.review_show_pip ?? DEFAULT_PROJECT_UI_STATE.review_show_pip);'
        in js
    )
    assert 'const showOverlay = $("show-overlay")?.checked ?? true;' in js
    assert 'if (!($("show-markers")?.checked ?? true)) {' in js
    assert 'if (!($("show-pip")?.checked ?? true)) {' in js
    assert "const badgeDisplayLabels = {" in js
    assert 'card.className = "style-card badge-style-card";' in js
    assert '<span class="style-card-label">Bg</span>' in js
    assert '<span class="style-card-label">Opacity</span>' in js
    assert '<span class="style-card-label">Alpha</span>' not in js
    assert "Background alpha" not in js
    assert "background alpha percent" not in js
    assert 'const displayTitle = badgeDisplayLabels[key] || title.replace(/ Badge$/, "");' in js
    assert "function renderMetricsTrendTable(table) {" in js
    assert '["Shot", "Split", "Run", "Score", "ShotML", "Action"].forEach((label) => {' in js
    assert (
        '["Stage #", imported.stage_number !== null && imported.stage_number !== undefined ? String(imported.stage_number) : ""],'
        in js
    )
    assert '["Score Options", (summary.score_options || []).join(", "),' not in js
    assert (
        '["Imported Stage", imported.stage_number !== null && imported.stage_number !== undefined ? `Stage ${imported.stage_number}` : ""],'
        not in js
    )
    assert "event.stopPropagation();" in js
    assert "toggle.onclick = (event) => {" in js
    assert '$("badge-style-grid").addEventListener("change", (event) => {' in js
    assert '$("score-color-grid").addEventListener("change", () => {' not in js
    assert "Behavior" not in html
    assert "Score letter is saved to that shot" not in html
    assert (
        "Score and penalty edits live here. The Splits pane stays read-only so timing edits do not fight scoring edits."
        not in html
    )
    assert "Score Colors" in html
    assert "These colors only affect score text tokens." not in html
    assert "scoring-workbench-table" in js
    assert "toggleScoringRowEdit" in js
    assert "return scoringPaneBase.setExpanded(expanded, { persistUiState });" in scoring_pane
    assert "scoring_expanded: false," in js
    assert (
        "scoring_expanded: Boolean(uiState.scoring_expanded ?? DEFAULT_PROJECT_UI_STATE.scoring_expanded),"
        in js
    )
    assert 'scoring_expanded: Boolean(root?.classList.contains("scoring-expanded")),' in js
    assert "if (!shouldApplyProjectUiStatePayload(payload)) return;" in js
    assert "function scoringWorkbenchGridTemplate(table) {" in js
    assert "const containerWidth = table.parentElement instanceof HTMLElement" in js
    assert (
        "const tableWidth = Math.max(containerWidth, table.clientWidth, table.getBoundingClientRect().width || 0);"
        in js
    )
    assert 'const template = table.id === "scoring-workbench-table"' in js
    assert "? scoringWorkbenchGridTemplate(table)" in js
    assert (
        'table.classList.toggle("timing-resizable-table", expandedTable && tableId !== "scoring-workbench-table");'
        in js
    )
    assert 'function renderScoringTable(tableId = "scoring-table") {' in js
    assert "function compactScoreDisplay(letter, ruleset = activeScoringRuleset()) {" in js
    assert "A (-0)" not in js
    assert 'if (normalizedRuleset === "idpa_time_plus") return "-0";' in js
    assert (
        "scoreCell.textContent = compactScoreDisplay(segment.score_letter || defaultScore, activeScoringRuleset()) || defaultScore;"
        in js
    )
    assert '{ label: "Current Score", columnId: "score", resizable: false },' in js
    assert "window.requestAnimationFrame(() => {" in js
    assert 'applyTimingTableColumns($("scoring-workbench-table"));' in js
    assert "function buildScoringPenaltyEditor(segment, rowScope, penaltyFields) {" in js
    assert 'select.className = "shot-penalty-select shot-penalty-entry-control";' in js
    assert 'add.textContent = "Add Penalty";' in js
    assert (
        'penalty_counts: collectPenaltyCounts(controlScope, `.shot-penalty-entry-control[data-score-shot-id="${shotId}"]`),'
        in js
    )
    assert 'toggle.className = "scoring-shot-toggle";' in js
    assert 'toggle.textContent = expanded ? "v" : ">";' in js
    assert "if (editing && penaltyFields.length > 0) {" in js
    assert "table.appendChild(buildScoringDeleteCell(segment));" in js
    assert "table.appendChild(buildScoringRestoreCell(segment));" in js
    assert ".scoring-penalty-entry {" in css
    assert ".shot-penalty-select {" in css
    assert ".add-penalty-button," in css
    assert 'updateTimingRowField(row.shot_id, "score_letter", select.value)' not in js
    assert "let timingAdjustmentDrafts = new Map();" in js
    assert (
        "timingAdjustmentDrafts.set(shotId, signedSeconds(numericMs(row.adjustment_ms) ?? 0));"
        in js
    )
    assert 'timingAdjustmentDrafts.set(row.shot_id, String(input.value ?? "").trim());' in js
    assert 'updateTimingRowField(shotId, "adjustment_ms", draftValue);' in js
    assert (
        'railWidth: clamp(savedNumber("splitshot.layout.railWidth", DEFAULT_LAYOUT_SIZES.railWidth), 84, 104)'
        in js
    )
    assert (
        'previewLayoutSize("railWidth", clamp(runtime.activeResize.startSize + deltaX, 84, 104));'
        in layout_js
    )
    assert "const parentRect = canvas.parentElement?.getBoundingClientRect();" in js
    assert "parentRect?.width" in js
    assert 'canvas.style.width = "100%";' in js
    assert "appears inside its split badge" not in html
    assert "scheduleSecondaryPreviewSync();" in js
    assert "empty-start" not in js
    assert "setActiveTool" in js
    assert "setActivePage" not in js
    assert "let overlayFrameMode = null;" in js
    assert "function overlayRenderPositionMs(video, mediaTimeS = null) {" in js
    assert "function previewFrameClientRect(video, container) {" in js
    assert "function requestOverlayFrame(video, tick) {" in js
    assert "function cancelOverlayFrame(video) {" in js
    assert "renderLiveOverlay(positionMsOverride = null)" in js
    assert 'const textBoxDragging = customOverlay.classList.contains("dragging");' in js
    assert 'if (textBoxDragging) customOverlay.classList.add("dragging");' in js
    assert 'function browserShotPresentationLagFrames(video = $("primary-video")) {' in js
    assert 'return "mozPaintedFrames" in video ? 1 : 0;' in js
    assert 'function shotDisplayTimeMs(shotTimeMs, video = $("primary-video")) {' in js
    assert "if (shotDisplayTimeMs(shot.time_ms) <= positionMs) index = shotIndex;" in js
    assert "return Math.max(0, Math.floor(mediaTimeS * 1000));" in js
    assert "return Math.max(0, Math.floor((video?.currentTime || 0) * 1000));" in js


def test_browser_ui_uses_hard_edged_contiguous_tool_shell() -> None:
    css = _read_split_css()

    assert "border-radius: 0;" in css
    assert "border-radius: 8px" not in css
    assert "border-radius: 9px" not in css
    assert "border-radius: 10px" not in css
    assert "html,\nbody {\n  height: 100%;" in css
    assert "overflow: hidden;" in css
    assert ".review-grid {\n  display: grid;" in css
    assert ".button-grid {\n  display: grid;\n  gap: 0;" in css
    assert ".status-bar {\n  align-items: center;" in css
    assert ".status-bar-actions {\n  align-items: center;" in css
    assert ".processing-bar {" in css
    assert ".command-strip" not in css
    assert ".empty-start" not in css
    assert ".metrics-strip" not in css
    assert ".rail-action" not in css
    assert "--rail-width: 84px;" in css
    assert "--topbar-height: 38px;" in css
    assert "--inspector-width: 440px;" in css
    assert "--waveform-height: 206px;" in css
    assert "--resize-handle-size: 4px;" in css
    assert "--app-height: 100vh;" in css
    assert "grid-template-rows: repeat(14, minmax(0, 1fr));" in css
    assert ".tool-nav > .tool-item {\n  height: 100%;" in css
    assert (
        "grid-template-columns: var(--rail-width) var(--resize-handle-size) minmax(0, 1fr);" in css
    )
    assert "grid-template-rows: var(--topbar-height) minmax(0, 1fr);" in css
    assert "min-height: var(--topbar-height);" in css
    assert "height: var(--topbar-height);" in css
    assert "top: var(--topbar-height);" not in css
    assert ".processing-bar[hidden] {\n  display: none !important;" in css
    assert "grid-auto-rows: minmax(0, 1fr);" in css
    tool_nav_css = css[css.index(".tool-nav {") : css.index(".tool-rail-footer {")]
    assert "align-content: start;" not in tool_nav_css
    assert "overflow-y: auto;" not in tool_nav_css
    assert "height: 56px;" in css
    assert "overflow: hidden;" in css
    assert "display: flex;" in css
    assert "width: var(--inspector-width);" in css
    assert "overflow-x: hidden;" in css
    assert "-ms-overflow-style: none;" in css
    assert "scrollbar-width: none;" in css
    assert ".inspector::-webkit-scrollbar {\n  height: 0;\n  width: 0;" in css
    assert (
        "grid-template-rows: minmax(0, 1fr) var(--resize-handle-size) minmax(112px, var(--waveform-height));"
        in css
    )
    assert "grid-template-rows: minmax(320px, 1fr) 206px;" not in css
    assert ".layout-unlocked .resize-handle" in css
    assert ".panel-lock-button-status {" in css
    assert ".panel-lock-button-video" not in css
    assert 'content: "🔒";' not in css
    assert 'content: "🔓";' not in css
    assert ".video-stage.merge-preview" in css
    assert ".video-stage.merge-pip #secondary-video" in css
    assert ".merge-media-list" in css
    assert ".merge-media-card" in css
    assert ".merge-media-card-header" in css
    assert ".merge-source-sync-row" in css
    assert ".merge-source-sync-buttons" in css
    assert ".inspector :is(\n  .text-box-manager," in css
    assert "overflow-x: clip;" in css
    assert "@container (max-width: 380px)" in css
    assert (
        ".text-box-card-header,\n  .popup-bubble-card .text-box-card-header,\n  .merge-media-card-header"
        in css
    )
    assert ".merge-source-sync-hint {\n  color: var(--muted);" in css
    assert ".merge-media-card .merge-source-sync-hint {\n  overflow: visible;" in css
    assert "overflow-wrap: anywhere;\n  white-space: normal;" in css
    assert ".cockpit-shell.inspector-compact .style-card-label" in css
    assert ".cockpit-shell.inspector-compact .style-card-label {\n  display: none;" not in css
    assert ".popup-authoring-bar {\n  align-items: end;" in css
    assert ".popup-duration-actions {\n  align-items: end;" not in css
    assert ".popup-authoring-panel {\n  display: grid;" in css
    assert ".popup-marker-toolbar," not in css
    assert ".popup-marker-create-actions {\n  gap: 0.35rem;" not in css
    assert ".popup-toolbar-row {\n  display: grid;" not in css
    assert ".markers-workbench {" in css
    assert ".markers-workbench-toolbar {" in css
    assert ".markers-workbench-body.defaults-collapsed {" not in css
    assert ".popup-list-section.popup-authoring-panel.collapsed > :not(.section-header) {" in css
    assert ".cockpit.markers-expanded .markers-workbench {" in css
    assert ".cockpit.markers-expanded .waveform-panel," not in css
    assert ".popup-collapsed-nav {\n  display: grid;" not in css
    assert ".popup-timeline-strip {\n  background:" not in css
    assert (
        ".popup-style-card,\n.cockpit-shell.inspector-compact .popup-style-card {\n  grid-template-columns: repeat(2, minmax(0, 1fr));"
        in css
    )
    assert ".popup-style-card .opacity-field {\n  grid-column: 1 / -1;" in css
    assert (
        ".popup-style-card .color-hex-input,\n.cockpit-shell.inspector-compact .popup-style-card .color-hex-input {\n  flex: 1 1 auto;\n  max-width: 10rem;"
        in css
    )
    assert (
        "  .popup-style-card {\n    grid-template-columns: repeat(2, minmax(0, 1fr));\n  }" in css
    )
    assert "#badge-style-grid {\n  grid-template-columns: repeat(4, minmax(0, 1fr));" in css
    assert "#badge-style-grid .badge-style-card .color-swatch-button" in css
    assert "#badge-style-grid .badge-style-card .opacity-percent-input" in css
    assert ".metrics-trend-table" in css
    assert ".metrics-details {\n  border: 1px solid var(--line);\n  grid-template-columns:" in css
    assert ".popup-overlay [data-popup-drag].popup-selected" in css
    assert ".popup-overlay [data-popup-drag].popup-outside-window" in css
    assert "@container (max-width: 620px)" in css
    assert "@container (max-width: 560px)" in css
    assert "@container (max-width: 460px)" in css
    assert "@container (max-width: 420px)" in css
    assert "flex-wrap: wrap;" in css
    assert ".popup-bubble-card .text-box-card-actions {" in css
    assert "popup-bubble-card .text-box-card-actions > .scoring-shot-toggle," in css
    assert "popup-bubble-card .text-box-card-actions > .pane-toggle" in css
    assert ".popup-placement-compact-grid {" in css
    assert ".popup-motion-point-row-guided {\n  align-items: center;" in css
    assert ".popup-motion-action-grid {" in css
    assert ".popup-motion-point-fields {" in css
    assert ".popup-motion-workflow-header {" in css
    assert ".popup-motion-workflow-hint {" in css
    assert (
        ".color-control-pair,\n  .opacity-control-pair {\n    margin-left: 0;\n    width: 100%;"
        in css
    )
    assert "container-type: inline-size;" in css
    assert "#project-description" in css
    assert "-webkit-backdrop-filter: blur(6px);" not in css
    assert "top: 0;\n  right: 0;\n  bottom: 0;\n  left: 0;" in css
    assert "grid-template-rows: auto minmax(0, 1fr) auto auto auto;" in css
    assert "grid-row: 3;" in css
    assert "top: 2.2rem;" not in css
    assert ".project-delete-button" in css
    assert "gap: 0.5rem;" in css
    assert ".cockpit.waveform-expanded .review-grid" in css
    assert ".cockpit.waveform-expanded .video-stage" in css
    assert ".cockpit.waveform-expanded .resize-handle-waveform" in css
    assert "grid-template-rows: minmax(0, 1fr);" in css
    assert "grid-template-rows: auto minmax(0, 2fr) auto auto minmax(0, 1fr);" in css
    assert "max-height: none;" in css
    assert "display: none;" in css
    assert ".cockpit.timing-expanded .timing-workbench" in css
    assert ".cockpit.scoring-expanded .scoring-workbench" in css
    assert ".cockpit.scoring-expanded .inspector" in css
    assert ".scoring-toggle-row" in css
    assert ".review-visibility-manager" in css
    assert ".review-visibility-option" in css
    assert "grid-template-rows: auto auto minmax(0, 1fr) auto;" in css
    assert ".scoring-shot-toggle" in css
    assert ".scoring-shot-controls[hidden] {\n  display: none !important;" in css
    assert ".scoring-shot-actions" in css
    assert ".timing-adjustment-input" in css
    assert ".timing-column-resize" in css
    assert (
        "grid-template-columns: minmax(0, 0.45fr) minmax(0, 1.15fr) minmax(0, 0.62fr) minmax(0, 0.62fr) minmax(0, 1.55fr) minmax(0, 0.5fr) minmax(0, 1.05fr) minmax(0, 0.9fr) minmax(0, 0.72fr) minmax(0, 0.52fr) minmax(0, 0.6fr);"
        in css
    )
    assert (
        "grid-template-columns: minmax(0, 1.15fr) minmax(0, 0.62fr) minmax(0, 0.62fr) minmax(0, 1.55fr);"
        in css
    )
    assert ".scoring-shot-row.collapsed" in css
    assert ".timing-action-remove" in css
    assert "width: calc(var(--timing-action-chip-chars, 8) * 0.72ch + 3.2rem);" in css
    assert ".waveform-window-handle" in css
    assert ".penalty-grid" in css
    assert ".export-log-output" in css
    assert ".modal" in css
    assert ".metrics-summary-grid" in css
    assert ".metrics-row" not in css
    assert ".text-box-card" in css
    assert ".cockpit.scoring-active .score-target-button" not in css
    assert ".overlay-badge.timer-badge" in css
    assert ".score-float" not in css
    assert ".overlay-left {\n  flex-direction: column;\n}" in css
    assert ".overlay-right {\n  flex-direction: column;\n}" in css
    assert "display: inline-flex;" in css
    assert "flex: 0 0 auto;" in css
    assert "height: auto;" in css
    assert "width: fit-content;" not in css
    assert "height: fit-content;" not in css
    assert 'input[type="number"]::-webkit-outer-spin-button' in css
    assert ".pip-size-control output" in css
    assert "height: var(--app-height, 100vh);" in css
    assert "html,\n  body {\n    height: 100%;\n    overflow: hidden;" in css
    assert "height: var(--app-height, 100vh);\n    min-height: 0;" in css
    assert "touch-action: none;" in css
    assert "touch-action: manipulation;" in css
    assert "-webkit-user-select: none;" in css
    assert "user-select: none;" in css
    assert "-webkit-appearance: none;" in css
    assert "input:disabled," in css
    assert "#custom-overlay.has-badge" in css
    assert "#custom-overlay.has-badge [data-text-box-drag]" in css
    assert "min-width: 104px;" not in css
    assert "min-width: 92px;" not in css
    assert 'input[type="range"]::-webkit-slider-thumb' in css
    assert 'input[type="checkbox"]' in css
    assert 'font-family: "Segoe UI", -apple-system' in css
    assert "font-size: 13px;" in css
    assert ".color-control-pair" in css
    assert ".color-hex-input.invalid" in css


def test_browser_ui_includes_webkit_rendering_guards() -> None:
    js = _read_app_shell_source()
    layout_js = (STATIC_ROOT / "lib" / "layout.js").read_text()
    overlay_canvas_js = (STATIC_ROOT / "components" / "overlay-canvas.js").read_text()
    overlay_pane = (STATIC_ROOT / "panes" / "overlay-pane.js").read_text()
    review_pane = (STATIC_ROOT / "panes" / "review-pane.js").read_text()
    waveform_component = (STATIC_ROOT / "components" / "waveform.js").read_text()

    assert 'setCssPixels("--app-height", viewportHeight);' in layout_js
    assert "document.documentElement?.clientHeight" in layout_js
    assert "window.visualViewport?.height" in layout_js
    assert "function waveformCanvasDisplayHeight(canvas) {" in js
    assert "function persistWaveformViewport() {" in js
    assert "function primaryVideoStateSnapshot(video) {" in js
    assert "function logPrimaryVideoState(eventName) {" in js
    assert 'document.addEventListener("visibilitychange", handleWindowVisibilityRestore);' in js
    assert 'window.addEventListener("focus", handleWindowVisibilityRestore);' in js
    assert 'window.addEventListener("pageshow", handleWindowVisibilityRestore);' in js
    assert 'windowObject.getComputedStyle(shotList).display !== "none"' in waveform_component
    assert 'window.visualViewport?.addEventListener("resize", handleViewportLayoutChange);' in js
    assert (
        'window.visualViewport?.addEventListener("scroll", handleViewportLayoutChange);' not in js
    )
    assert "function renderViewportLayout() {" in js
    assert "function resetInspectorHorizontalScroll() {" in js
    assert "resetInspectorHorizontalScroll();" in js
    assert (
        'element.scrollLeft = element.closest(".inspector") || element.classList.contains("inspector") ? 0 : scrollLeft;'
        in js
    )
    assert "function requestRender() {" in js
    assert "function withPreservedScrollState(elements, callback) {" in js
    assert "window.requestAnimationFrame(() => renderWaveform());" in js
    assert 'typeof video.requestVideoFrameCallback === "function"' in overlay_canvas_js
    assert "setOverlayFrame(video.requestVideoFrameCallback(tick));" in overlay_canvas_js
    assert "video.cancelVideoFrameCallback(overlayFrame);" in overlay_canvas_js
    assert 'document.addEventListener("pointermove", moveLayoutResize);' in js
    assert 'document.addEventListener("pointerup", endLayoutResize);' in js
    assert 'document.addEventListener("pointercancel", endLayoutResize);' in js
    assert 'document.addEventListener("lostpointercapture", endLayoutResize);' in js
    assert 'document.addEventListener("pointermove", handleWaveformPointerMove);' in js
    assert 'document.addEventListener("pointerup", handleWaveformPointerUp);' in js
    assert (
        "const timeMs = draggedShotIndex >= 0 && index === draggedShotIndex && pendingDragTimeMs !== null"
        in waveform_component
    )
    assert 'document.addEventListener("pointercancel", handleWaveformPointerUp);' in js
    assert 'document.addEventListener("lostpointercapture", handleWaveformPointerUp);' in js
    assert 'document.addEventListener("lostpointercapture", endOverlayBadgeDrag);' in js
    assert 'document.addEventListener("lostpointercapture", endMergePreviewDrag);' in js
    assert 'document.addEventListener("lostpointercapture", endTextBoxDrag);' in js
    assert "function restoreVideoElementFrame(video) {" in js
    assert "function restoreReviewStage() {" in js
    assert "function scheduleReviewStageRestore() {" in js
    assert "function handleWindowVisibilityRestore() {" in js
    assert "function computeExportCropBox(width, height, aspectRatio, centerX, centerY) {" in js
    assert "function exportTargetDimensions(cropWidth, cropHeight) {" in js
    assert "function fitAspectRect(width, height, aspectRatio) {" in js
    assert "function previewFrameGeometry(video, container) {" in js
    assert "function overlayDisplayScale(video, frameRect, outputWidth = null) {" in js
    assert "function scaledOverlayPixelValue(value, scale, minimum = 0) {" in js
    assert (
        "releasePointer(runtime.activeResize.target, runtime.activeResize.pointerId);" in layout_js
    )
    assert '["loadedmetadata", "loadeddata"].forEach((eventName) => {' in js
    assert '$("primary-video").addEventListener("volumechange", () => {' in js
    assert '$("primary-video").addEventListener("canplay", () => {' in js
    assert '$("primary-video").addEventListener("error", () => {' in js
    assert '["volumechange", "canplay", "error"].forEach((eventName) => {' not in js
    assert 'activity("video.primary.state", {' in js
    assert 'ensurePrimaryVideoAudio($("primary-video"));' not in js
    assert "ensurePrimaryVideoAudio(audio);" not in js
    assert "function isColorInput(control) {" in js
    assert "function previewOverlayControlChanges() {" in js
    assert "function commitOverlayControlChanges() {" in js
    assert 'badge.style.fontWeight = state.project.overlay.font_bold ? "700" : "400";' in js
    assert 'badge.style.wordBreak = "normal";' in js
    assert "const frameGeometry = previewFrameGeometry(video, stage);" in overlay_pane
    assert (
        "const frameRect = roundedRect(frameGeometry?.frameRect || stage.getBoundingClientRect());"
        in overlay_pane
    )
    assert (
        "const overlayScale = frameGeometry?.scale || overlayDisplayScale(video, frameRect);"
        in overlay_pane
    )
    assert (
        "bindOverlayColorInput(card.querySelector('[data-text-box-field=\"background_color\"]'));"
        in review_pane
    )
    assert (
        "bindOverlayColorInput(card.querySelector('[data-text-box-field=\"text_color\"]'));"
        in review_pane
    )
    assert "function bindOverlayColorInput(control) {" in overlay_pane
    assert (
        "const mediaTimeS = Number.isFinite(metadata?.mediaTime) ? metadata.mediaTime : null;"
        in overlay_canvas_js
    )
    assert (
        'frame_source: mediaTimeS === null ? "animation-frame" : "video-frame",'
        in overlay_canvas_js
    )
    assert "syncPrimaryAudioPreview({ allowDriftCorrection: true });" not in js
    assert "if (getOverlayFrame() !== null) return;" in js


def test_browser_ui_guards_preview_failures_and_drag_resize() -> None:
    api_js = (STATIC_ROOT / "lib" / "api.js").read_text()
    js = _read_app_shell_source()
    merge_pane = (STATIC_ROOT / "panes" / "merge-pane.js").read_text()
    overlay_pane = (STATIC_ROOT / "panes" / "overlay-pane.js").read_text()
    video_player_js = (STATIC_ROOT / "components" / "video-player.js").read_text()
    waveform_component = (STATIC_ROOT / "components" / "waveform.js").read_text()

    assert "let secondaryPreviewPlayErrorKey = null;" in js
    assert "let processingBarShowTimer = null;" in js
    assert "let processingBarHideTimer = null;" in js
    assert "function stateHasShot(nextState, shotId) {" in api_js
    assert (
        "const isSameProject = runtime.currentProjectId && nextProjectId && runtime.currentProjectId === nextProjectId;"
        in api_js
    )
    assert (
        "? mergeProjectUiState(nextState.project.ui_state, readProjectUiStatePayload())" in api_js
    )
    assert "if (!stateHasShot(runtime.state, runtime.selectedShotId)) {" in api_js
    assert (
        "runtime.selectedShotId = stateHasShot(runtime.state, nextUiState.selected_shot_id) ? nextUiState.selected_shot_id : null;"
        in api_js
    )
    assert "function clearSecondaryPreviewPlayError() {" in js
    assert "function reportSecondaryPreviewPlayError(error) {" in js
    assert (
        "if (secondary.readyState < HTMLMediaElement.HAVE_CURRENT_DATA || secondaryPreviewPlayErrorKey) {"
        in js
    )
    assert "syncMergePreviewElements(primary);" in js
    assert "return;" in js
    assert 'if (error?.name === "AbortError") return;' in js
    assert 'activity("video.secondary_play.error", { name: errorName, error: errorMessage });' in js
    assert "secondary.play().catch(() => {});" not in js
    assert "ensurePrimaryVideoAudio(video);" not in js
    assert "ensurePrimaryVideoAudio(audio);" not in js
    assert "ensurePrimaryVideoAudio(secondary);" in video_player_js
    assert 'logPrimaryVideoState("source.attach");' in video_player_js
    assert (
        'const primaryMediaPath = buildMediaUrl(boundaryKind ? `/media/${boundaryKind}` : (state.media.primary_url || "/media/primary"), path);'
        in video_player_js
    )
    assert (
        'const secondaryMediaPath = buildMediaUrl(state.media.secondary_url || "/media/secondary", secondaryPath);'
        in video_player_js
    )
    assert "media.dataset.mediaUrl = mediaPath;" in merge_pane
    assert "video.dataset.mediaUrl = primaryMediaPath;" in video_player_js
    assert "const { startClientX, startClientY, startX, startY } = drag;" in overlay_pane
    assert (
        'const frameRect = previewFrameClientRect($("primary-video"), stage) || stage.getBoundingClientRect();'
        in js
    )
    assert 'video.style.objectFit = "cover";' in video_player_js
    assert (
        "video.style.objectPosition = `${cropCenterX * 100}% ${cropCenterY * 100}%`;"
        in video_player_js
    )
    assert (
        "positionOverlayContainer(overlay, currentState().project.overlay.shot_quadrant, frameRect, {"
        in overlay_pane
    )
    assert "const textBoxGroups = new Map();" in overlay_pane
    assert "configureTextBoxGroup(group, quadrant, frameRect, overlayScale);" in overlay_pane
    assert "let overlayColorCommitTimer = null;" in js
    assert "let waveformPanDrag = null;" in js
    assert "let waveformNavigatorDrag = null;" in js
    assert "let reviewStageRestoreFrame = null;" in js
    assert "let reviewStageRestoreSecondFrame = null;" in js
    assert "const OVERLAY_COLOR_COMMIT_DELAY_MS = 900;" in js
    assert "const WAVEFORM_PAN_DRAG_THRESHOLD_PX = 4;" in js
    assert (
        "if (event.pointerId !== undefined && getDraggingShotPointerId() !== undefined && event.pointerId !== getDraggingShotPointerId()) return;"
        in waveform_component
    )
    assert (
        "if (event.pointerId !== undefined && drag.pointerId !== undefined && event.pointerId !== drag.pointerId) return;"
        in overlay_pane
    )
    assert (
        "if (event.pointerId !== undefined && mergePreviewDrag.pointerId !== undefined && event.pointerId !== mergePreviewDrag.pointerId) return;"
        in js
    )
    assert (
        'overlay.style.flexWrap = ["left", "right"].includes(direction) ? "wrap" : "nowrap";' in js
    )
    assert "function bindOverlayColorInput(control) {" in overlay_pane
    assert 'control.addEventListener("click", () => openColorPicker(control));' in overlay_pane
    assert "syncOverlayHexControl(control);" in js
    assert "scheduleOverlayColorCommit();" in js
    assert "flushOverlayColorCommit();" in js
    assert "startWaveformPanDrag(event);" in js
    assert (
        '$("waveform-window-track").addEventListener("pointerdown", handleWaveformNavigatorPointerDown);'
        in js
    )
    assert "bindOverlayColorInput(card.querySelector('[data-field=\"background_color\"]'));" in js
    assert (
        "setOverlayTextBoxField(textBoxCard.dataset.boxId, textBoxField, normalized, { rerender: false });"
        in js
    )
    assert "setScoringWorkbenchExpanded(false, { persistUiState: false });" in js
    assert "if (isColorInput(event.target)) return;" in js
    assert "target: customOverlay," in overlay_pane


def test_browser_overlay_badges_scale_with_video_display_size() -> None:
    js = (STATIC_ROOT / "app.js").read_text()
    overlay_pane = (STATIC_ROOT / "panes" / "overlay-pane.js").read_text()

    assert 'function overlayFontFamilyStack(fontFamily = "") {' in js
    assert "function defaultOverlayFontFamily() {" in js
    assert (
        'if (browserPlatformIsWindows() && normalized === "Helvetica Neue") return "Segoe UI";'
        in js
    )
    assert 'return \'Consolas, "Courier New", "Lucida Console", monospace\';' in js
    assert 'return \'"Segoe UI", Arial, Verdana, Tahoma, "Trebuchet MS", sans-serif\';' in js
    assert (
        '? `"${normalized}", "Segoe UI", Arial, Verdana, Tahoma, "Trebuchet MS", sans-serif`' in js
    )
    assert "const scaledMargin = scaledOverlayPixelValue(overlayMargin, scale, 0);" in js
    assert "const scaledGap = scaledOverlayPixelValue(overlaySpacing, scale, 0);" in js
    assert "const OVERLAY_BADGE_PADDING_X_PX = 10;" in js
    assert "const OVERLAY_BADGE_PADDING_Y_PX = 5;" in js
    assert "function overlayAutoSizedBadgeContents() {" in js
    assert "function overlayAutoBubbleSize() {" in js
    assert "function syncOverlayBubbleSizeControls() {" in js
    assert (
        "const scaledPaddingY = scaledOverlayPixelValue(OVERLAY_BADGE_PADDING_Y_PX, scale, 0);"
        in js
    )
    assert (
        "const scaledPaddingX = scaledOverlayPixelValue(OVERLAY_BADGE_PADDING_X_PX, scale, 0);"
        in js
    )
    assert (
        "badge.style.fontSize = `${scaledOverlayPixelValue(state.project.overlay.font_size || 14, scale, 1)}px`;"
        in js
    )
    assert "const resolvedWidth = widthOverride > 0" in js
    assert "const resolvedHeight = heightOverride > 0" in js
    assert (
        "const autoBubbleSize = currentState().project.overlay.bubble_width > 0 && currentState().project.overlay.bubble_height > 0"
        in overlay_pane
    )
    assert (
        'badgeElement(`Timer ${seconds(elapsed)}`, currentState().project.overlay.timer_badge, size, null, null, null, "center", overlayScale, autoBubbleSize);'
        in overlay_pane
    )
    assert "currentState().project.overlay.show_shot_scores" in overlay_pane
    assert (
        'badgeElement(`${officialScoreLabel} ${officialScoreValue}`, currentState().project.overlay.hit_factor_badge, size, null, null, null, "center", overlayScale, autoBubbleSize);'
        in overlay_pane
    )
    assert "function scoreTokenColor(token) {" in js


def test_browser_processing_bar_uses_delayed_show_and_minimum_visibility() -> None:
    js = (STATIC_ROOT / "app.js").read_text()
    processing_js = (STATIC_ROOT / "lib" / "processing.js").read_text()

    assert "const PROCESSING_BAR_SHOW_DELAY_MS = 180;" in js
    assert "const PROCESSING_BAR_MIN_VISIBLE_MS = 320;" in js
    assert "function scheduleProcessingBarShow(message, detail) {" in js
    assert 'function scheduleProcessingBarHide(finalMessage = "Ready.") {' in js
    assert 'function forceHideProcessingBar(finalMessage = "Ready.") {' in js
    assert "scheduleProcessingBarShow(message, detail);" in js
    assert "if (runtime.busyCount === 0) {" in processing_js
    assert "stopProcessingProgress(100);" in processing_js
    assert "scheduleProcessingBarHide(finalMessage);" in processing_js
    assert "hideProcessingBarNow(finalMessage);" in processing_js


def test_browser_overlay_badges_use_container_gap_instead_of_per_badge_margin() -> None:
    js = (STATIC_ROOT / "app.js").read_text()
    overlay_pane = (STATIC_ROOT / "panes" / "overlay-pane.js").read_text()

    assert 'badge.style.margin = "0";' in js
    assert 'customOverlay.style.padding = "0";' in overlay_pane
    assert 'customOverlay.style.gap = "0";' in overlay_pane


def test_browser_color_picker_is_custom_and_os_agnostic() -> None:
    css = _read_split_css()
    html = (STATIC_ROOT / "index.html").read_text()
    js = (STATIC_ROOT / "app.js").read_text()

    assert ".color-swatch-button {" in css
    assert ".color-picker-dialog {" in css
    assert ".color-picker-swatches {" in css
    assert "cursor: pointer;" in css
    assert 'input[type="color"] {' not in css
    assert 'id="color-picker-modal"' in html
    assert 'id="color-picker-preview"' in html
    assert 'id="close-color-picker"' in html
    assert 'data-close-color-picker="true"' in html
    assert "function updateColorPickerFromSliders({ commit = false } = {}) {" in js
    assert "function updateColorPickerFromHexInput({ commit = false } = {}) {" in js


def test_processing_log_opens_before_trim_and_queue_requests() -> None:
    trim_source = (STATIC_ROOT / "panes" / "trim-sync-pane.js").read_text()
    queue_source = (STATIC_ROOT / "panes" / "queue-pane.js").read_text()
    export_source = (STATIC_ROOT / "panes" / "export-pane.js").read_text()

    assert trim_source.index(
        "await openProcessingLog", trim_source.index("async function trimAll")
    ) < trim_source.index(
        'await callApi("/api/merge/source/trim-all"', trim_source.index("async function trimAll")
    )
    assert trim_source.index(
        "await openProcessingLog", trim_source.index("async function trimSource")
    ) < trim_source.index(
        'await callApi("/api/primary/trim"', trim_source.index("async function trimSource")
    )
    assert queue_source.index(
        "await openProcessingLog", queue_source.index("async function processAll")
    ) < queue_source.index(
        'await callApi("/api/project/queue/process"',
        queue_source.index("async function processAll"),
    )
    combined_start = queue_source.index("async function processIntoOneFile")
    assert queue_source.index("await openProcessingLog", combined_start) < queue_source.index(
        'await callApi("/api/project/queue/process"', combined_start
    )
    modal_start = export_source.index("async function openExportLogModal")
    assert export_source.index("modal.hidden = false", modal_start) < export_source.index(
        "await refreshState()", modal_start
    )


def test_browser_buttons_are_logged_and_wired_to_actions() -> None:
    html = (STATIC_ROOT / "index.html").read_text()
    activity_js = (STATIC_ROOT / "lib" / "activity.js").read_text()

    assert 'activity("button.click"' in activity_js

    wired_button_ids = {
        "expand-waveform",
        "zoom-waveform-out",
        "zoom-waveform-in",
        "amp-waveform-out",
        "amp-waveform-in",
        "reset-waveform-view",
        "apply-threshold",
        "collapse-timing",
        "collapse-metrics",
        "expand-metrics",
        "popup-add-bubble",
        "popup-edit-selected",
        "popup-add-bubble-workbench",
        "popup-add-selected-shot-workbench",
        "popup-import-shots-workbench",
        "popup-prev-workbench",
        "popup-next-workbench",
        "show-overlay",
        "show-markers",
        "show-pip",
        "expand-scoring",
        "collapse-scoring",
        "settings-import-current",
        "settings-reset-defaults",
        "settings-save-current-scoring",
        "settings-reset-section-scoring",
        "settings-save-current-pip",
        "settings-reset-section-pip",
        "settings-save-current-overlay",
        "settings-reset-section-overlay",
        "settings-save-current-markers",
        "settings-reset-section-markers",
        "settings-save-current-export",
        "settings-reset-section-export",
        "settings-save-current-shotml",
        "settings-reset-section-shotml",
        "add-timing-event",
        "timing-enabled",
        "expand-timing",
        "browse-project-output-root",
        "new-project",
        "browse-project-path",
        "open-project",
        "open-practiscore-dashboard",
        "import-practiscore",
        "save-project",
        "delete-project",
        "review-add-text-box",
        "queue-all-btn",
        "review-add-imported-box",
        "review-add-stage-name-box",
        "review-set-source",
        "export-badges",
        "create-output-profile",
        "save-output-profile",
        "delete-output-profile",
        "export-export-log",
        "close-export-log",
        "close-color-picker",
        "metrics-export-csv",
        "metrics-export-text",
        "trim-global-apply",
        "trim-global-clear",
        "trim-global-defaults-btn",
        "trim-global-undo",
        "generate-shotml-proposals",
        "reset-shotml-defaults",
        "restore-merge-defaults",
        "settings-use-current-layout",
        "settings-release-layout",
        "toggle-layout-lock-video",
        "toggle-rail",
        "resize-rail",
        "resize-sidebar",
        "resize-waveform",
        "waveform-mode-single",
        "waveform-mode-multi",
    }
    behavior_attributes = (
        "data-tool=",
        "data-waveform-mode=",
        "data-sync=",
        "data-layout-lock-toggle",
        "data-motion-mode-value=",
        "data-popup-action=",
    )
    button_tags = re.findall(r"<button\b[^>]*>", html)

    assert button_tags
    for tag in button_tags:
        id_match = re.search(r'id="([^"]+)"', tag)
        has_wired_id = bool(id_match and id_match.group(1) in wired_button_ids)
        has_behavior_attribute = any(attribute in tag for attribute in behavior_attributes)
        assert has_wired_id or has_behavior_attribute, tag


def test_browser_display_names_strip_session_uuid_prefixes() -> None:
    status_bar_js = (STATIC_ROOT / "components" / "status-bar.js").read_text()
    utils = (STATIC_ROOT / "lib" / "utils.js").read_text()

    assert "primary_display_name" in status_bar_js
    assert 'replace(/^[a-f0-9]{32}_/i, "")' in utils


def test_browser_ui_removes_gpa_from_browser_preset_catalog() -> None:
    js = (STATIC_ROOT / "app.js").read_text()

    assert "gpa_time_plus" not in js


def test_browser_overlay_color_inputs_preview_on_input_and_commit_on_change() -> None:
    overlay_pane = (STATIC_ROOT / "panes" / "overlay-pane.js").read_text()
    match = re.search(
        r"function bindOverlayColorInput\(control\) \{(?P<body>.*?)\n\}", overlay_pane, re.DOTALL
    )

    assert match is not None
    body = match.group("body")
    assert 'control.addEventListener("click", () => openColorPicker(control));' in body
    assert 'control.addEventListener("keydown", (event) => {' in body
    assert 'if (event.key !== "Enter" && event.key !== " ") return;' in body
    assert "openColorPicker(control);" in body
    assert 'hexInput.addEventListener("input", () => updateColorFromHexInput(hexInput));' in body
    assert (
        'hexInput.addEventListener("change", () => updateColorFromHexInput(hexInput, { commit: true }));'
        in body
    )
    assert (
        'hexInput.addEventListener("blur", () => updateColorFromHexInput(hexInput, { commit: true }));'
        in body
    )


def test_browser_client_validates_remote_state_shape_and_restores_server_selection() -> None:
    api_js = (STATIC_ROOT / "lib" / "api.js").read_text()

    assert "function hasCompleteProjectState(nextState)" in api_js
    assert "nextState?.project?.overlay" in api_js
    assert "nextState?.project?.merge" in api_js
    assert "nextState?.project?.export" in api_js
    assert "nextState?.project?.ui_state" in api_js
    assert "nextState?.metrics" in api_js
    assert "nextState?.media" in api_js
    assert (
        "const isSameProject = runtime.currentProjectId && nextProjectId && runtime.currentProjectId === nextProjectId;"
        in api_js
    )
    assert "if (isSameProject) {" in api_js
    assert "mergeProjectDetailsDraft(nextState.project);" in api_js
    assert "applyProjectUiState(nextUiState);" in api_js
    assert (
        "runtime.selectedShotId = stateHasShot(runtime.state, nextUiState.selected_shot_id) ? nextUiState.selected_shot_id : null;"
        in api_js
    )


def test_browser_overlay_payload_filters_unknown_badge_cards() -> None:
    overlay_pane = (STATIC_ROOT / "panes" / "overlay-pane.js").read_text()
    match = re.search(
        r"function readOverlayPayload\(\) \{(?P<body>.*?)\n  \}", overlay_pane, re.DOTALL
    )

    assert "validOverlayBadgeNames = new Set()," in overlay_pane
    assert match is not None
    body = match.group("body")
    assert "if (!validOverlayBadgeNames.has(badge)) return;" in body
    assert 'card.querySelectorAll("[data-field]")' in body
    assert "const value = isColorInput(input)" in body
    assert "? readColorControlValue(input)" in body
    assert "? opacityValueFromPercent(input.value)" in body


def test_browser_auto_apply_snapshots_form_payloads_before_debounce() -> None:
    export_pane = (STATIC_ROOT / "panes" / "export-pane.js").read_text()
    js = _read_app_shell_source()
    merge_pane = (STATIC_ROOT / "panes" / "merge-pane.js").read_text()
    project_pane = (STATIC_ROOT / "panes" / "project-pane.js").read_text()

    assert "async function applyThresholdNow() {" in js
    assert "const autoApplyShotMLSettings = debounce((settings) => {" in js
    assert "const autoApplyProjectDetails = debounce((payload) => {" in js
    assert "const autoApplyPractiScoreContext = debounce((payload) => {" in js
    assert "const autoApplyOverlay = debounce((payload) => {" in js
    assert "const autoApplyMerge = debounce((payload) => {" in js
    assert "const autoApplyExportLayout = debounce((payload) => {" in js
    assert "const autoApplyExportSettings = debounce((payload) => {" in js
    assert "const autoApplyScoring = debounce(({ scoringPayload, ruleset }) => {" in js
    assert "scheduleShotMLSettingsApply();" in js
    assert "const payload = readProjectDetailsPayload();" in project_pane
    assert "applyProjectDetailsDraft(payload);" in project_pane
    assert "renderHeader();" in project_pane
    assert "autoApplyProjectDetails(payload);" in project_pane
    assert "autoApplyPractiScoreContext.cancel?.();" in project_pane
    assert (
        'return callApi("/api/project/practiscore", readPractiScoreContextPayload());'
        in project_pane
    )
    assert "autoApplyShotMLSettings.cancel?.();" in js
    assert "autoApplyProjectDetails.cancel?.();" in js
    assert "autoApplyPractiScoreContext.cancel?.();" in js
    assert "const payload = readOverlayPayload();" in js
    assert "applyOverlayPositionDraft(payload);" in js
    assert "autoApplyOverlay(payload);" in js
    assert "const payload = readMergePayload();" in merge_pane
    assert "applyMergeDraft(payload);" in merge_pane
    assert "autoApplyMerge(payload);" in merge_pane
    assert "const payload = readExportLayoutPayload();" in export_pane
    assert "autoApplyExportLayout(payload);" in export_pane
    assert "const payload = readExportSettingsPayload();" in export_pane
    assert "autoApplyExportSettings(payload);" in export_pane
    assert '$("threshold").addEventListener("change", scheduleThresholdApply);' in js
    assert '$("apply-threshold").addEventListener("click", applyThresholdNow);' in js
    assert '$("new-project").addEventListener("click", async () => {' in js
    assert "await createNewProject();" in js
    assert (
        "const shouldReplace = windowObject.confirm(`A SplitShot project already exists in:"
        in project_pane
    )
    assert "Replace it with a new blank project?`);" in project_pane
    assert 'const resetResult = await callApi("/api/project/new", {});' in project_pane
    assert (
        'const savedResult = await callApi("/api/project/save", { path: projectPath });'
        in project_pane
    )
    assert (
        "const shouldDelete = window.confirm(`Delete project metadata for:\\n\\n${projectPath}\\n\\nProject folders and files will be kept on disk.`);"
        in js
    )
    assert "if (!shouldDelete) return;" in js
    assert "await flushPendingProjectDrafts();" in js
    assert 'await callApi("/api/project/delete", {});' in js


def test_browser_merge_file_uploads_treat_partial_success_as_success() -> None:
    js = (STATIC_ROOT / "app.js").read_text()
    match = re.search(r"async function postFiles\(path, files\) \{(?P<body>.*?)\n\}", js, re.DOTALL)

    assert match is not None
    body = match.group("body")
    assert "let latestSuccess = null;" in body
    assert "const result = await postFile(path, file);" in body
    assert "if (result) latestSuccess = result;" in body
    assert "return latestSuccess;" in body


def test_browser_ui_surface_audit_script_exists_for_cross_browser_matrix() -> None:
    script = Path("scripts/audits/browser/run_browser_ui_surface_audit.py").read_text()

    assert '"chromium": BrowserTarget(' in script
    assert '"chrome": BrowserTarget(' in script
    assert '"edge": BrowserTarget(' in script
    assert '"firefox": BrowserTarget(' in script
    assert '"safari": BrowserTarget(' in script
    assert '"webkit": BrowserTarget(' in script
    assert "SUPPORTED_BROWSERS = tuple(BROWSER_TARGETS)" in script
    assert "def audit_overlay_surfaces(page: Page) -> CheckResult:" in script
    assert "def audit_waveform_drag(page: Page) -> CheckResult:" in script
    assert "def audit_layout_resize_persists(page: Page) -> CheckResult:" in script
    assert "def audit_merge_file_input_change(" in script


def test_browser_interaction_audit_script_exists_for_real_browser_workflow() -> None:
    script = Path("scripts/audits/browser/run_browser_interaction_audit.py").read_text()

    assert '"chromium": BrowserTarget(' in script
    assert '"firefox": BrowserTarget(' in script
    assert '"safari": BrowserTarget(' in script
    assert '"webkit": BrowserTarget(' in script
    assert "def import_primary_video(" in script
    assert (
        "def drag_waveform_viewport(page: Page, activity_source: BrowserControlServer | str) -> CheckResult:"
        in script
    )
    assert (
        "def drag_waveform_shot(page: Page, activity_source: BrowserControlServer | str) -> CheckResult:"
        in script
    )
    assert (
        "def drag_timer_badge(page: Page, activity_source: BrowserControlServer | str) -> CheckResult:"
        in script
    )
    assert (
        "def resize_layout_persists(page: Page, activity_source: BrowserControlServer | str) -> CheckResult:"
        in script
    )
    assert "def import_practiscore_file(" in script
    assert "activity_source: BrowserControlServer | str" in script
    assert "practiscore_path: Path" in script
    assert "def audit_imported_summary_default_anchor(page: Page) -> CheckResult:" in script
    assert "def drag_imported_summary_box(" in script
    assert "def preserve_review_inspector_scroll(" in script
    assert "def import_merge_media(" in script
    assert "def drag_merge_preview_persists(" in script
    assert "def drag_merge_size_slider_commits(" in script
    assert "def sync_nudge_commits(" in script


def test_browser_app_bootstrap_delegates_backbone_core_modules() -> None:
    activity_runtime = (STATIC_ROOT / "lib" / "activity.js").read_text()
    api_runtime = (STATIC_ROOT / "lib" / "api.js").read_text()
    global_compat = (STATIC_ROOT / "lib" / "global-compat.js").read_text()
    js = (STATIC_ROOT / "app.js").read_text()
    key_runtime = (STATIC_ROOT / "lib" / "keys.js").read_text()
    layout_runtime = (STATIC_ROOT / "lib" / "layout.js").read_text()
    processing_runtime = (STATIC_ROOT / "lib" / "processing.js").read_text()
    utils = (STATIC_ROOT / "lib" / "utils.js").read_text()
    event_bus = (STATIC_ROOT / "lib" / "event-bus.js").read_text()
    store = (STATIC_ROOT / "lib" / "store.js").read_text()

    assert 'from "./lib/activity.js"' in js
    assert 'from "./lib/api.js"' in js
    assert 'from "./lib/utils.js"' in js
    assert 'from "./lib/event-bus.js"' in js
    assert 'from "./lib/global-compat.js"' in js
    assert 'from "./lib/keys.js"' in js
    assert 'from "./lib/layout.js"' in js
    assert 'from "./lib/processing.js"' in js
    assert 'from "./lib/store.js"' in js
    assert "let $ = domById;" in js
    assert "const appBus = createEventBus();" in js
    assert "const appStore = createStore({" in js
    assert "let activityRuntime = null;" in js
    assert "let processingRuntime = null;" in js
    assert "let layoutRuntime = null;" in js
    assert "let keyRuntime = null;" in js
    assert "let apiRuntime = null;" in js
    assert "storePatch: syncBackboneStore," in js
    assert "function syncBackboneStore(patch = {}) {" in js
    assert "function setStateValue(value) {" in js
    assert "function setSelectedShotIdValue(value) {" in js
    assert "function setActiveToolValue(value) {" in js
    assert "setStateValue(nextState);" in api_runtime
    assert "setSelectedShotIdValue(nextShotId);" in js
    assert "setActiveToolValue(tool);" in js
    assert "const runtimeBackbone = Object.freeze({" in js
    assert "const runtimeBackboneStateBindings = {" in js
    assert "const legacyGlobalState = createMutableBindings(runtimeBackboneStateBindings);" in js
    assert "const runtimeBackboneState = createMutableBindings({" in js
    assert "processingRuntime = createProcessingRuntime({" in js
    assert "activityRuntime = createActivityRuntime({" in js
    assert "layoutRuntime = createLayoutRuntime({" in js
    assert "keyRuntime = createKeyRuntime({" in js
    assert "apiRuntime = createApiRuntime({" in js
    assert "installLegacyGlobalCompat({" in js
    assert "target: window," in js
    assert "valueSources: [" in js
    assert "activityRuntime," in js
    assert "metricsPane," in js
    assert "mutableSources: [legacyGlobalState]," in js
    assert "mutableBindings: legacyGlobalMutableBindings," in js
    assert "backbone: runtimeBackbone," in js

    assert "export function createMutableBindings(bindings = {}) {" in global_compat
    assert "export function installMutableGlobals(target, source) {" in global_compat
    assert "export function installValueGlobals(target, values = {}) {" in global_compat
    assert "export function installLegacyGlobalCompat({" in global_compat
    assert "installValueGlobals(target, mergedValues);" in global_compat
    assert "installMutableGlobals(target, source);" in global_compat
    assert "installMutableGlobals(target, createMutableBindings(mutableBindings));" in global_compat
    assert (
        "target.__splitshotBackbone = Object.freeze({ bus: backbone.bus, store: backbone.store });"
        in global_compat
    )
    assert "target.__splitshotBootstrapMode = bootstrapMode;" in global_compat

    legacy_mutable_bindings = js.split("const legacyGlobalMutableBindings = {", 1)[1].split(
        "\n};\n\ninstallLegacyGlobalCompat({", 1
    )[0]
    legacy_values = js.split("  values: {", 1)[1].split("\n  },\n  mutableSources:", 1)[0]

    assert "sendKeepaliveJson: [() => sendKeepaliveJson" not in legacy_mutable_bindings
    assert (
        "sendProjectUiStateKeepalive: [() => sendProjectUiStateKeepalive"
        not in legacy_mutable_bindings
    )
    assert "createNewProject: [() => createNewProject" in legacy_mutable_bindings
    assert "renderTextBoxEditors: [() => renderTextBoxEditors" in legacy_mutable_bindings
    assert "setPopupBubbles: [() => setPopupBubbles" in legacy_mutable_bindings

    assert "renderControls, renderStyleControls," not in legacy_values
    assert "sendKeepaliveJson, sendProjectUiStateKeepalive," not in legacy_values
    assert (
        "scheduleThresholdApply, applyThresholdNow, scheduleShotMLSettingsApply, scheduleProjectUiStateApply,"
        not in legacy_values
    )
    assert "flushQueuedProjectUiStateApply, scheduleOverlayApply, wireEvents," not in legacy_values

    assert "export const $ = (id) => document.getElementById(id);" in utils
    assert "export function debounce(fn, delayMs = 250) {" in utils
    assert "export function splitSeconds(ms) {" in utils
    assert "export function normalizedUiStringList(data) {" in utils

    assert "export function createEventBus() {" in event_bus
    assert "return Object.freeze({" in event_bus
    assert "emit," in event_bus

    assert "export function createStore(initialState = {}) {" in store
    assert "function patch(nextPatch = {}) {" in store
    assert "function subscribe(listener) {" in store

    assert "export function createActivityRuntime({" in activity_runtime
    assert "function wireGlobalActivityLogging() {" in activity_runtime
    assert (
        "fetch(`/api/activity/poll?after=${runtime.activityCursor}&job_after=${runtime.processingLogCursor || 0}`)"
        in activity_runtime
    )

    assert "export function createProcessingRuntime({" in processing_runtime
    assert "function processingForPath(path, payload = null) {" in processing_runtime
    assert "Exporting video..." in processing_runtime

    assert "export function createLayoutRuntime({" in layout_runtime
    assert "function applyLayoutState() {" in layout_runtime
    assert "function beginLayoutResize(kind, event) {" in layout_runtime

    assert "export function createKeyRuntime({" in key_runtime
    assert "function handleKeyboardEdit(event) {" in key_runtime

    assert "export function createApiRuntime({" in api_runtime
    assert "function applyRemoteState(nextState" in api_runtime
    assert "function normalizePractiScoreSyncPayload(payload) {" in api_runtime


def test_browser_app_bootstrap_delegates_shell_components() -> None:
    js = (STATIC_ROOT / "app.js").read_text()
    status_bar = (STATIC_ROOT / "components" / "status-bar.js").read_text()
    video_player = (STATIC_ROOT / "components" / "video-player.js").read_text()

    assert 'from "./components/status-bar.js"' in js
    assert 'from "./components/video-player.js"' in js
    assert "let statusBarComponent = null;" in js
    assert "let videoPlayerComponent = null;" in js
    assert "return statusBarComponent?.renderHeader();" in js
    assert "return statusBarComponent?.renderStats();" in js
    assert "return statusBarComponent?.timingSummaryRows();" in js
    assert "return statusBarComponent?.renderTimingSummary();" in js
    assert "const result = videoPlayerComponent?.renderVideo();" in js
    assert "statusBarComponent = createStatusBarComponent({" in js
    assert "videoPlayerComponent = createVideoPlayerComponent({" in js
    assert "getState: () => state," in js
    assert "getSelectedShotId: () => selectedShotId," in js

    assert "export function createStatusBarComponent({" in status_bar
    assert "function renderHeader() {" in status_bar
    assert "function renderStats() {" in status_bar
    assert "function timingSummaryRows() {" in status_bar
    assert "function renderTimingSummary() {" in status_bar
    assert '$("media-badge").textContent = state?.media?.primary_available' in status_bar

    assert "export function createVideoPlayerComponent({" in video_player
    assert "function renderVideo() {" in video_player
    assert (
        'const primaryMediaPath = buildMediaUrl(boundaryKind ? `/media/${boundaryKind}` : (state.media.primary_url || "/media/primary"), path);'
        in video_player
    )
    assert "const waveformEnabled = Boolean(state.project.analysis?.shots?.length);" in video_player
    assert "scheduleSecondaryPreviewSync();" in video_player


def test_readme_documents_one_command_uv_launch() -> None:
    readme = Path("README.md").read_text()

    assert Path(".python-version").read_text().strip() == "3.12"
    assert "uv run splitshot" in readme
    assert "uv run --python 3.12 splitshot" not in readme


def test_browser_static_logo_is_packaged() -> None:
    assert (STATIC_ROOT / "logo.png").is_file()


def test_badge_opacity_control_removes_number_spinner_and_keeps_suffix() -> None:
    css = _read_split_css()
    selector = "#badge-style-grid .badge-style-card .opacity-percent-input"
    within = css[css.index(selector) : css.index(selector) + 650]
    assert "min-width: 0;" in within
    assert "padding: var(--space-1) 0.75rem;" in within
    assert "width: 100%;" in within
    assert re.search(r"(?m)^\.opacity-percent-input \{[^}]*appearance: textfield;[^}]*\}", css)
    assert re.search(
        r"\.opacity-percent-input::webkit-outer-spin-button|"
        r"\.opacity-percent-input::-webkit-outer-spin-button",
        css,
    )
    assert re.search(
        r"(?m)^\.opacity-percent-input::?-webkit-inner-spin-button \{[^}]*"
        r"-webkit-appearance: none;",
        css,
    )
    suffix = css.index("#badge-style-grid .badge-style-card .opacity-percent-suffix")
    assert "margin-left: 0;" in css[suffix : suffix + 400]


def test_every_opacity_number_control_uses_the_spinnerless_class() -> None:
    source_paths = [
        STATIC_ROOT / "index.html",
        STATIC_ROOT / "app.js",
        STATIC_ROOT / "lib" / "shell-runtime.js",
        STATIC_ROOT / "panes" / "intro-outro-pane.js",
        STATIC_ROOT / "panes" / "review-pane.js",
    ]
    opacity_number_lines = [
        line
        for path in source_paths
        for line in path.read_text().splitlines()
        if 'type="number"' in line and "opacity" in line.lower()
    ]
    assert len(opacity_number_lines) == 10
    assert all('class="opacity-percent-input"' in line for line in opacity_number_lines)

    merge_source = (STATIC_ROOT / "panes" / "merge-pane.js").read_text()
    opacity_builder = merge_source[
        merge_source.index("const buildSourceOpacityInput") : merge_source.index(
            "const opacityField = buildSourceOpacityInput"
        )
    ]
    assert 'input.type = "number";' in opacity_builder
    assert 'input.className = "opacity-percent-input";' in opacity_builder


def test_intro_outro_preview_uses_asset_geometry_and_preserves_playback_time() -> None:
    pane = (STATIC_ROOT / "panes" / "intro-outro-pane.js").read_text()
    player = (STATIC_ROOT / "components" / "video-player.js").read_text()

    assert "const playbackTimes = { intro: 0, outro: 0 };" in pane
    assert "width: Math.max(1, Number(media.width || 1920))" in pane
    assert "height: Math.max(1, Number(media.height || 1080))" in pane
    assert "restorePlaybackTime(kind);" in pane
    assert "const frameGeometry = mergePreview || boundaryKind" in player
    assert "containedMediaFrameClientRect(" in pane
    assert 'video.addEventListener("loadedmetadata", updatePreview, { once: true });' in pane


def test_static_browser_shell_audit_keeps_all_panes_modularized() -> None:
    app_js = (STATIC_ROOT / "app.js").read_text()
    expected_imports = {
        "createProjectPane": "./panes/project-pane.js",
        "createReviewPane": "./panes/review-pane.js",
        "createTimingPane": "./panes/timing-pane.js",
        "createScoringPane": "./panes/scoring-pane.js",
        "createMarkersPane": "./panes/markers-pane.js",
        "createOverlayPane": "./panes/overlay-pane.js",
        "createMergePane": "./panes/merge-pane.js",
        "createExportPane": "./panes/export-pane.js",
        "createMetricsPane": "./panes/metrics-pane.js",
        "createShotMLPane": "./panes/shotml-pane.js",
        "createSettingsPane": "./panes/settings-pane.js",
    }
    for factory, path in expected_imports.items():
        assert f'import {{ {factory} }} from "{path}";' in app_js
        assert f"{factory}({{" in app_js
    assert "function renderPractiScoreSummaries() {" in app_js
    assert "projectPane?.renderPractiScoreImportSummary?.();" in app_js
    assert "return scoringPane?.renderPractiScoreSummaries();" in app_js
