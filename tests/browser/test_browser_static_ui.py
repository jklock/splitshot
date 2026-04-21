from __future__ import annotations

import re
from pathlib import Path


STATIC_ROOT = Path("src/splitshot/browser/static")


def test_browser_ui_is_waterfall_cockpit_workflow() -> None:
    html = (STATIC_ROOT / "index.html").read_text()
    js = (STATIC_ROOT / "app.js").read_text()

    assert 'class="app-shell cockpit-shell"' in html
    assert 'href="/static/styles.css?v=20260418b"' in html
    assert 'src="/static/app.js?v=20260420b"' in html
    assert 'accept="video/*,.mp4,.m4v,.mov,.avi,.wmv,.webm,.mkv,.mpg,.mpeg,.mts,.m2ts"' in html
    assert 'accept="video/*,image/*,.mp4,.m4v,.mov,.avi,.wmv,.webm,.mkv,.mpg,.mpeg,.mts,.m2ts,.png,.jpg,.jpeg,.gif,.webp"' in html
    assert 'accept=".csv,.txt,text/csv,text/plain"' in html
    assert 'class="tool-rail"' in html
    assert 'class="status-bar"' in html
    assert 'class="review-grid"' in html
    assert 'class="review-stack"' in html
    assert 'class="inspector"' in html
    assert html.index('data-tool="project"') < html.index('data-tool="scoring"')
    assert html.index('data-tool="scoring"') < html.index('data-tool="timing"')
    assert html.index('data-tool="timing"') < html.index('data-tool="shotml"')
    assert html.index('data-tool="shotml"') < html.index('data-tool="merge"')
    assert html.index('data-tool="merge"') < html.index('data-tool="overlay"')
    assert html.index('data-tool="overlay"') < html.index('data-tool="popup"')
    assert html.index('data-tool="popup"') < html.index('data-tool="review"')
    assert html.index('data-tool="review"') < html.index('data-tool="export"')
    assert html.index('data-tool="export"') < html.index('data-tool="metrics"')
    assert 'data-tool="project"' in html
    assert 'data-tool="metrics"' in html
    assert 'data-tool="review"' in html
    assert 'data-tool="timing"' in html
    assert 'data-tool="shotml"' in html
    assert 'data-tool="edit"' not in html
    assert 'data-tool="scoring"' in html
    assert 'data-tool="overlay"' in html
    assert 'data-tool="popup"' in html
    assert 'data-tool="merge"' in html
    assert 'data-tool="layout"' not in html
    assert 'data-tool="export"' in html
    assert '<img class="rail-logo" src="/static/logo.png" alt="SplitShot" />' in html
    assert '<b>PiP</b>' in html
    assert '<b>Metrics</b>' in html
    assert "<b>Review</b>" in html
    assert "<b>Splits</b>" in html
    assert "<b>ShotML</b>" in html
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
    assert 'id="project-name"' in html
    assert 'id="project-description"' in html
    assert 'id="match-type"' in html
    assert '<select id="match-stage-number">' in html
    assert '<select id="match-competitor-name">' in html
    assert '<select id="match-competitor-place">' in html
    assert '<button id="browse-project-path" type="button">Choose Project</button>' in html
    assert 'id="project-path" placeholder="~/splitshot/My Match" readonly' in html
    assert 'id="use-project-folder"' not in html
    assert 'id="import-practiscore"' in html
    assert 'id="practiscore-status"' in html
    assert 'id="practiscore-import-summary"' in html
    assert 'id="current-file"' in html
    assert 'id="status-copy"' in html
    assert 'id="inspector-file"' in html
    assert 'id="inspector-status-copy"' in html
    assert 'id="processing-bar"' in html
    assert '<span id="media-badge">No Video Selected</span>' in html
    assert 'id="selected-shot-panel"' in html
    assert 'id="split-card-grid"' not in html
    assert 'class="video-status"' not in html
    assert "No video open" not in html
    assert 'id="apply-threshold"' in html
    assert '>Re-run ShotML<' in html
    assert 'data-tool-pane="shotml"' in html
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
    assert "Add PiP Media" in html
    assert 'id="merge-media-input"' in html
    assert 'id="practiscore-file-input"' in html
    assert 'id="merge-media-list"' in html
    assert 'id="add-merge-media"' in html
    assert 'Default PiP size' in html
    assert "Swap Primary and First Added Item" not in html
    assert "Select PractiScore File" in html
    assert "Select Primary Video" in html
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
    assert 'id="review-text-box-list"' in html
    assert 'data-tool-pane="popup"' in html
    assert 'id="popup-import-shots"' in html
    assert 'data-popup-field="anchor_mode"' in html
    assert 'data-popup-field="shot_id"' in html
    assert 'data-popup-field="name"' in js
    assert 'function selectPopupBubble(' in js
    assert 'function selectPopupBubbleForShot(shotId' in js
    assert 'function importShotPopups() {' in js
    assert 'data-popup-field="quadrant"' in html
    assert 'data-popup-field="opacity_percent"' in html
    assert 'data-popup-field="follow_motion"' in html
    assert 'data-popup-field="motion_point_count"' in html
    assert 'data-popup-motion-guide' in html
    assert 'data-popup-motion-path-list' in html
    assert 'data-popup-action="clear_motion_path"' in html
    assert 'id="metrics-summary-grid"' in html
    assert 'id="metrics-trend-list"' in html
    assert 'id="metrics-export-csv"' in html
    assert 'id="metrics-export-text"' in html
    assert 'id="show-export-log"' in html
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
    assert merge_start < html.index('id="add-merge-media"') < export_start
    assert merge_start < html.index('id="merge-layout"') < export_start
    assert merge_start < html.index('id="pip-size"') < export_start
    assert 'id="pip-size" type="range" min="1" max="95" step="1" value="35"' in html
    assert 'id="swap-videos"' not in html
    assert export_start < html.index('id="export-preset"') < project_start
    assert export_start < html.index('id="quality"') < project_start
    assert export_start < html.index('id="export-video"') < project_start
    assert project_start < html.index('id="match-type"')
    assert project_start < html.index('id="match-stage-number"')
    assert project_start < html.index('id="match-competitor-name"')
    assert project_start < html.index('id="match-competitor-place"')
    assert 'id="layout-threshold"' not in html
    assert 'id="layout-scoring-enabled"' not in html
    assert 'id="layout-overlay-position"' not in html
    assert 'id="layout-max-visible-shots"' not in html
    assert 'id="layout-merge-enabled"' not in html


def test_browser_ui_keeps_video_timeline_waveform_and_inspector_together() -> None:
    html = (STATIC_ROOT / "index.html").read_text()
    js = (STATIC_ROOT / "app.js").read_text()

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
    assert 'id="toggle-layout-lock-video"' in html
    assert 'id="toggle-layout-lock-waveform"' in html
    assert 'id="toggle-layout-lock-inspector"' in html
    assert 'data-waveform-mode="select"' in html
    assert 'data-waveform-mode="add"' in html
    assert 'data-waveform-mode="beep"' not in html
    assert 'id="waveform-window"' in html
    assert 'id="waveform-window-track"' in html
    assert 'id="waveform-window-handle"' in html
    assert 'id="waveform-shot-list"' in html
    assert 'id="timing-workbench"' in html
    assert 'id="expand-timing"' in html
    assert '<button id="expand-timing" type="button">Edit</button>' in html
    assert 'aria-label="Use waveform select mode"' in html
    assert 'aria-label="Use waveform add shot mode"' in html
    assert 'id="selected-shot-copy"' in html
    assert html.index('id="timing-table"') > html.index('id="selected-shot-panel"')
    assert html.index('id="timing-table"') < html.index('id="threshold"')
    timing_start = html.index('data-tool-pane="timing"')
    shotml_start = html.index('data-tool-pane="shotml"')
    assert timing_start < html.index('id="timing-table"') < shotml_start
    assert shotml_start < html.index('id="threshold"')
    assert html.index('waveform-header') < html.index('id="waveform"')
    assert html.index('id="waveform"') < html.index('class="waveform-actions waveform-footer"')
    assert 'id="badge-style-grid"' in html
    assert 'id="score-color-grid"' in html
    assert 'id="overlay-position"' in html
    assert '<option value="none">Hidden</option>' in html
    assert '<option value="bottom">Bottom</option>' in html
    assert 'id="project-name"' in html
    assert 'id="project-description"' in html
    assert 'id="merge-media-input"' in html
    assert 'id="merge-media-list"' in html
    assert 'id="add-merge-media"' in html
    assert 'id="pip-x"' in html
    assert 'id="pip-y"' in html
    assert 'aria-label="Move selected shot earlier by 10 milliseconds"' in html
    assert 'Each PiP card below has its own size, placement, transparency, and sync nudges.' in html
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
    assert 'Imported summary' in html
    assert 'Review Text Boxes' in html
    assert 'data-text-box-field="lock_to_stack"' in js
    assert 'Lock to shot stack' in js
    assert '<span class="style-card-label">Background</span>' in js
    assert '<span class="style-card-label">Opacity</span>' in js
    assert 'type="range" data-field="opacity"' not in js
    assert 'data-text-box-field="opacity" type="number"' in js
    assert 'data-field="opacity" min="0" max="100" step="1" value="90"' in js
    assert 'id="layout-threshold"' not in html
    assert 'id="scoring-preset"' in html
    assert 'id="scoring-imported-caption"' in html
    assert 'id="scoring-imported-summary"' in html
    assert 'id="score-option-grid"' in html
    assert 'Score and penalty edits live here. The Splits pane stays read-only so timing edits do not fight scoring edits.' in html
    assert 'Common shorthand: M miss, NS no-shoot, PE procedural error' in html
    assert html.index('id="scoring-shot-list"') < html.index('id="score-option-grid"')
    assert 'id="scoring-penalty-grid"' not in html
    assert 'id="score-letter"' not in html
    assert 'id="timer-x"' in html
    assert 'id="timer-y"' in html
    assert 'id="draw-x"' in html
    assert 'id="draw-y"' in html
    assert 'id="score-x"' in html
    assert 'id="score-y"' in html
    assert 'id="browse-project-path"' in html
    assert 'id="browse-export-path"' in html
    assert 'id="browse-primary-path"' in html
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
    assert 'id="color-space"' in html
    assert 'id="ffmpeg-preset"' in html
    assert 'id="show-export-log"' in html
    assert 'id="export-log-output"' in html
    assert 'id="export-log-modal"' in html
    assert 'FFmpeg Renderer' in html
    assert 'Local video' in html
    assert 'Supported export containers: MP4, M4V, MOV, and MKV.' in html
    assert "/api/files/primary" in js
    assert "/api/files/merge" in js
    assert "/api/files/practiscore" in js
    assert "/api/project/details" in js
    assert "/api/project/practiscore" in js
    assert "/api/dialog/path" in js
    assert "/api/export/settings" in js
    assert "/api/export/preset" in js
    assert "/api/events/delete" in js
    assert "/api/activity" in js
    assert "Remove timing event" in js
    assert 'activity("api.refresh", {})' in js
    assert 'if (!response.ok || data.error) throw new Error(data.error || response.statusText);' in js
    assert 'throw new Error("Received invalid project state from the local server.");' in js
    assert 'activity("button.click"' in js
    assert "wireGlobalActivityLogging" in js
    assert "document.addEventListener(\"click\"" in js
    assert "handleWaveformPointerDown" in js
    assert "handleWaveformPointerMove" in js
    assert "handleKeyboardEdit" in js
    assert "function keyboardEditTargetIsEditable(event) {" in js
    assert 'if (keyboardEditTargetIsEditable(event)) return;' in js
    assert "scheduleSecondaryPreviewSync" in js
    assert "autoApplyShotMLSettings" in js
    assert "autoApplyOverlay" in js
    assert "autoApplyMerge" in js
    assert "autoApplyExportLayout" in js
    assert "autoApplyExportSettings" in js
    assert "autoApplyScoring" in js
    assert "/api/layout" not in js
    assert "renderScoringPenaltyFields" in js
    assert "renderPractiScoreSummaries" in js
    assert "renderMergeMediaList" in js
    assert "renderCollapsibleInspectorSections" in js
    assert 'toggle.textContent = expanded ? "v" : ">";' in js
    assert 'const INSPECTOR_COMPACT_WIDTH = 700;' in js
    assert 'shell.classList.toggle("inspector-compact", layoutSizes.inspectorWidth < INSPECTOR_COMPACT_WIDTH);' in js
    assert 'buildSourceNumberInput("PiP X", "x", normalizedCoordinateValue(source.pip_x) ?? 1, 0, 1, 0.01, "0 is left, 1 is right.")' in js
    assert 'button.textContent = `${deltaMs > 0 ? "+" : ""}${deltaMs} ms`;' in js
    assert 'text.textContent = "PiP opacity";' in js
    assert 'pip_size_percent: nextSize,' in js
    assert 'let exportPathDraft = "";' in js
    assert 'let projectDetailsDraft = { name: null, description: null };' in js
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
    assert '/api/shots/restore' in js
    assert '/api/scoring/restore' in js
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
    assert 'pickPath("primary", "primary-file-path", async (path)' in js
    assert 'pickPath("secondary", "secondary-file-path", async (path)' not in js
    assert 'pickPath("project_folder", "project-path", async (selectedPath)' in js
    assert 'async function probeProjectFolder(path) {' in js
    assert 'await fetch("/api/project/probe", {' in js
    assert 'async function createNewProject(path = $("project-path").value.trim()) {' in js
    assert 'async function useProjectFolder(path = $("project-path").value.trim()) {' in js
    assert 'await flushPendingProjectDrafts();' in js
    assert 'return pickPath("project_open", "project-path");' not in js
    assert 'const kind = currentPath ? "project_open" : "project_save";' not in js
    assert 'preset: $("export-preset").value,' in js
    assert 'overlay: readOverlayPayload(),' in js
    assert 'merge: {' in js
    assert 'scoring: {' in js
    assert 'position: $("overlay-position").value,' in js
    assert 'sync_offset_ms: currentSourceSyncOffsetMs(source),' in js
    assert 'cancelPendingExportDrafts();' in js
    assert 'await callApi("/api/export", buildExportPayload(path));' in js
    assert "saveProjectFlow" not in js
    assert "useProjectFolder" in js
    assert 'await callApi("/api/project/details", readProjectDetailsPayload());' in js
    assert 'const currentPath = normalizeProjectFolderInput(state?.project?.path || "");' in js
    assert 'const probeResult = await probeProjectFolder(targetPath);' in js
    assert 'if (requestId !== projectFolderProbeRequestId)' in js
    assert 'if (targetId === "export-path") exportPathDraft = data.path;' in js
    assert '$("export-path").addEventListener("input", () => {' in js
    assert 'exportPathDraft = $("export-path").value;' in js
    assert 'const path = requireValue("export-path", "Output video path");' in js
    assert 'exportPathDraft = path;' in js
    assert 'input.step = "0.01";' in js
    assert 'Math.round((Number(value) || 0) * 1000)' in js
    assert 'const TIMING_COLUMN_DEFAULTS = Object.freeze({' in js
    assert 'timing_column_widths: { ...TIMING_COLUMN_DEFAULTS },' in js
    assert 'function beginTimingColumnResize(tableId, columnId, event) {' in js
    assert 'function moveTimingColumnResize(event) {' in js
    assert 'function endTimingColumnResize(event) {' in js
    assert 'timingAdjustmentDrafts.get(row.shot_id) ?? signedSeconds(adjustmentMs)' in js
    assert 'function buildTimingRowControlCell(row, editing) {' in js
    assert 'preserve_following_splits: true' in js
    assert 'handle.className = "timing-column-resize";' in js
    assert "openProjectWithDialog" not in js
    assert "resetMediaElement" in js
    assert '$("penalties").value = state.project.scoring.penalties' not in js
    assert "renderExportPresetOptions" in js
    assert "syncExportPathControl();" in js
    assert "processingForPath" in js
    assert 'Exporting video...' in js
    assert 'Importing media...' in js
    assert 'Parsing PractiScore results and staging a local copy' in js
    assert 'setStatus("Select a PractiScore results file (.csv or .txt).");' in js
    assert 'function openHiddenFileInput(inputId) {' in js
    assert 'if (typeof input.showPicker === "function") {' in js
    assert 'openHiddenFileInput("practiscore-file-input");' in js
    assert 'document.addEventListener("fullscreenchange", handleStageFullscreenChange);' in js
    assert 'media.defaultMuted = false;' in js
    assert 'media.muted = false;' in js
    assert 'media.muted = true;' not in js
    assert 'await callApi("/api/project/practiscore", readPractiScoreContextPayload());\n    $("practiscore-file-input")?.click();' not in js
    assert 'if (!validatePractiScoreSelection()) return;\n    setStatus("Select a PractiScore results file (.csv or .txt).");\n    $("practiscore-file-input")?.click();' not in js
    assert "Opening file browser..." not in js
    assert "function readExportLayoutPayload()" in js
    assert "function scheduleExportLayoutApply()" in js
    assert "function scheduleExportSettingsApply()" in js
    assert "function scheduleProjectDetailsApply()" in js
    assert "function schedulePractiScoreContextApply()" in js
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
    assert "function openExportLogModal()" in js
    assert "function closeExportLogModal()" in js
    assert "function exportMetrics(kind)" in js
    assert "function mediaCacheToken() {" in js
    assert "function buildMediaUrl(basePath, sourcePath = \"\") {" in js
    assert 'function practiScoreSelectionValue(value) {' in js
    assert 'preferredPractiScoreSelection(selectedValues.competitor_name, "match-competitor-name", state?.project?.scoring?.competitor_name)' in js
    assert 'function ensureWaveformTimeVisible(timeMs, { center = false, paddingRatio = 0.12, persist = true } = {}) {' in js
    assert 'function renderWaveformNavigator() {' in js
    assert 'function handleWaveformNavigatorPointerDown(event) {' in js
    assert 'function startWaveformPanDrag(event) {' in js
    assert 'function updateWaveformPanDrag(event) {' in js
    assert 'let draggingShotPointerId = null;' in js
    assert 'let interactionPreviewFrame = null;' in js
    assert 'let pendingInteractionPreview = { video: false, waveform: false, overlay: false };' in js
    assert 'function scheduleInteractionPreviewRender({ video = false, waveform = false, overlay = false } = {}) {' in js
    assert 'function flushInteractionPreviewRender() {' in js
    assert 'const segmentsByShotId = new Map((state.timing_segments || []).map((segment) => [segment.shot_id, segment]));' in js
    assert 'return (state.split_rows || []).map((row) => {' in js
    assert 'const ACTIVITY_POLL_INTERVAL_MS = 1000;' in js
    assert 'fetch(`/api/activity/poll?after=${activityCursor}`)' in js
    assert 'const CUSTOM_QUADRANT_VALUE = "custom";' in js
    assert 'const ABOVE_FINAL_TEXT_BOX_VALUE = "above_final";' in js
    assert "const BADGE_FONT_SIZES = {" in js
    assert "const PREVIEW_VIDEO_CONTROLS_SAFE_BOTTOM_PX = 48;" in js
    assert "function syncOverlayFontSizePreset()" in js
    assert "function ensureShotQuadrantDefaults()" in js
    assert 'activity("layout.resize.start"' in js
    assert 'activity("layout.resize.commit"' in js
    assert 'function persistLayoutSize(key, value, { renderWaveformNow = true } = {}) {' in js
    assert 'function previewLayoutSize(key, value) {' in js
    assert 'if (state && renderWaveformNow) renderWaveform();' in js
    assert 'font_size: Number($("overlay-font-size").value || BADGE_FONT_SIZES[$("badge-size").value] || 14),' in js
    assert 'text_boxes: textBoxes.map((box) => ({' in js
    assert 'overlay.text_boxes = (payload.text_boxes || []).map((box, index) => normalizeOverlayTextBox(box, index));' in js
    assert 'function createOverlayTextBoxId() {' in js
    assert 'function overlayTextBoxAutoSize(box) {' in js
    assert 'function syncOverlayTextBoxSizeControls(boxId) {' in js
    assert 'function setOverlayTextBoxField(boxId, field, rawValue, options = {}) {' in js
    assert 'function beginTextBoxDrag(event) {' in js
    assert 'if (textBoxDrag) return;' in js
    assert 'function moveTextBoxDrag(event) {' in js
    assert 'function endTextBoxDrag(event) {' in js
    assert 'function normalizePopupMotionPath(path) {' in js
    assert 'function popupBubbleMotionPath(bubble) {' in js
    assert 'function popupBubbleMotionPointCount(bubble) {' in js
    assert 'function popupBubbleMotionPathTemplate(bubble, totalPointCount = 4) {' in js
    assert 'function popupBubblePoint(bubble, positionMs = null) {' in js
    assert 'function resamplePopupBubbleMotionPath(bubble, totalPointCount = null, sourcePath = null) {' in js
    assert 'function seekPrimaryVideoToTimeMs(timeMs) {' in js
    assert 'function seekPrimaryVideoToShot(shotId) {' in js
    assert 'function updatePopupBubbleMotionPoint(bubble, offsetMs, x, y) {' in js
    assert 'function renderPopupBubbleMotionGuide(card, bubble) {' in js
    assert 'function popupBubbleAutoSize(bubble) {' in js
    assert 'function popupTextForShotId(shotId) {' in js
    assert 'function popupBubbleResolvedText(bubble) {' in js
    assert 'function resolvedPopupBubbleSize(bubble) {' in js
    assert 'function syncPopupBubbleSizeControls(bubbleId) {' in js
    assert 'function popupBubbleVisibleWindow(bubble) {' in js
    assert 'function popupBubbleRenderPositionMs(bubble, positionMs) {' in js
    assert 'function popupBubbleIsVisibleAtPosition(bubble, positionMs) {' in js
    assert 'function popupBubbleSeekTimeMs(bubble) {' in js
    assert 'const isSelectedEditorBubble = activeTool === "popup" && bubble.id === selectedPopupBubbleId;' in js
    assert 'positionMs: isVisible ? positionMs : popupBubbleRenderPositionMs(bubble, positionMs),' in js
    assert 'badge.classList.toggle("popup-selected", Boolean(entry.selected));' in js
    assert 'badge.classList.toggle("popup-outside-window", Boolean(entry.outsideWindow));' in js
    assert 'if (shot) return shot.time_ms;' in js
    assert 'setPopupBubbles(nextBubbles, { commit: false, rerender: false });' in js
    assert 'data-popup-field="follow_motion"' in js
    assert 'entry.text,' in js
    assert 'popupSize.width,\n      popupSize.height,\n      "center"' in js
    assert '<option value="above_final">Above Final Box</option>' in js
    assert 'const fallbackQuadrant = source === "imported_summary" ? ABOVE_FINAL_TEXT_BOX_VALUE : "top_left";' in js
    assert 'quadrant: source === "imported_summary" ? ABOVE_FINAL_TEXT_BOX_VALUE : "top_left",' in js
    assert 'if (customX === null || customY === null) return false;' in js
    assert 'group.style.left = "0px";' in js
    assert 'group.style.top = "0px";' in js
    assert 'Switch to Custom placement to edit X and Y directly.' in js
    assert 'Keeps the imported summary centered above the final score badge once it appears.' in js
    assert 'syncOverlayFontSizePreset();' in js
    assert 'const seededCoordinates = resolveRenderedOverlayBadgeCoordinates("shots") || { x: 0.5, y: 0.5 };' in js
    assert 'if (!$("overlay-custom-y").value) syncControlValue($("overlay-custom-y"), seededCoordinates.y);' in js
    assert 'function pinCustomOverlayAnchor(overlay, frameRect, customPoint = null) {' in js
    assert 'if (usesCustomQuadrant(state.project.overlay.shot_quadrant) && overlay.childElementCount > 0) {' in js
    assert 'const anchorOffsetX = (badgeRect.left - overlayRect.left) + (badgeRect.width / 2);' in js
    assert 'const anchorOffsetY = (badgeRect.top - overlayRect.top) + (badgeRect.height / 2);' in js
    assert 'timerBadge.dataset.overlayDrag = "timer";' in js
    assert 'drawBadge.dataset.overlayDrag = "draw";' in js
    assert 'function splitSeconds(ms)' in js
    assert 'function currentPipSizePercent(source = null, fallback = 35) {' in js
    assert 'function currentSourceSyncOffsetMs(source = null) {' in js
    assert 'function mergePreviewTargetTime(primaryTime, source = null) {' in js
    assert 'function formatShotBadgeSuffix(shot) {' in js
    assert 'function resolvedSplitMsForShot(shotId, shotNumber = null, absoluteTimeMs = null) {' in js
    assert 'grid.querySelectorAll(".style-card[data-badge]")' in js
    assert 'scoreGrid.querySelectorAll(".score-color-input[data-letter]").forEach((input) => {' in js
    assert 'function scoringColorOptions() {' in js
    assert 'function openColorPicker(control) {' in js
    assert 'function closeColorPicker({ commit = true } = {}) {' in js
    assert 'function renderColorPickerSwatches() {' in js
    assert 'const scoreOptions = scoringColorOptions();' in js
    assert 'const scoreKeys = scoreOptions.map((option) => option.key);' in js
    assert '...Object.keys(state.project.overlay.scoring_colors || {}),' not in js
    assert 'exportSettings.crop_center_x' in js
    assert 'exportSettings.crop_center_y' in js
    assert 'const FINAL_SHOT_FLASH_HALF_PERIOD_MS' not in js
    assert 'const FINAL_SHOT_FLASH_CYCLES' not in js
    assert 'const FINAL_SHOT_FLASH_DURATION_MS' not in js
    assert 'const customBadge = event.target instanceof Element' in js
    assert 'customBadge.dataset.textBoxDrag = "true";' in js
    assert 'customBadge.dataset.textBoxId = box.id;' in js
    assert 'customBadge.dataset.textBoxSource = box.source || "manual";' in js
    assert 'box = overlayTextBoxes().find((item) => item.source === customBadge.dataset.textBoxSource);' in js
    assert '$("video-stage").addEventListener("pointerdown", beginTextBoxDrag, true);' in js
    assert '$("video-stage").addEventListener("mousedown", beginTextBoxDrag, true);' in js
    assert 'document.addEventListener("pointerdown", beginTextBoxDrag, true);' in js
    assert 'document.addEventListener("mousedown", beginTextBoxDrag, true);' in js
    assert 'document.addEventListener("mousemove", moveTextBoxDrag);' in js
    assert 'document.addEventListener("mouseup", endTextBoxDrag);' in js
    assert 'if (positionTextBoxBadge(customBadge, box, frameRect, {' in js
    assert 'anchorBadge: box.quadrant === ABOVE_FINAL_TEXT_BOX_VALUE ? finalScoreBadge : null,' in js
    assert 'const renderedTextBoxCount = customOverlay.querySelectorAll("[data-text-box-drag=\'true\']").length;' in js
    assert 'if (nextCustomOverlayKey !== customOverlayRenderKey || renderedTextBoxCount !== textBoxEntries.length) {' in js
    assert 'customOverlay.classList.toggle("has-badge", customOverlay.childElementCount > 0);' in js
    assert 'if (result) setActiveTool("scoring");' not in js
    assert 'item.addEventListener("click", () => selectShot(segment.shot_id, { revealInWaveform: true, centerWaveform: true }));' in js
    assert '$("show-export-log")?.addEventListener("click", openExportLogModal);' in js
    assert '$("export-export-log")?.addEventListener("click", downloadExportLog);' in js
    assert '$("metrics-export-csv")?.addEventListener("click", () => exportMetrics("csv"));' in js
    assert 'function defaultScoreLetter(ruleset = activeScoringRuleset()) {' in js
    assert 'function shotBadgeBaseText(shotNumber, splitText, intervalLabel = "") {' in js
    assert 'function scoreBadgeContent(shot, shotNumber, splitText, intervalLabel = "") {' in js
    assert 'scoreBadgeContent(shot, index + 1, splitSeconds(splitMs), splitRowIntervalLabel(splitRow))' in js
    assert 'const firstTokenGap = "  ";' in js
    assert 'fragment.style.whiteSpace = "pre";' in js
    assert 'const unsetOption = document.createElement("option");' not in js
    assert 'select.value = segment.score_letter || defaultScore;' in js
    assert 'scoreCell.textContent = row.score_letter || defaultScore;' in js
    assert '{ label: "ShotML Confidence %", columnId: "confidence", resizable: true }' in js
    assert '"timing-table": ["segment", "split", "total", "action"],' in js
    assert 'function splitRowActionSummary(row) {' in js
    assert 'function splitRowIntervalLabel(row) {' in js
    assert 'function splitRowCumulativeMs(row) {' in js
    assert 'function buildSplitRowActionCell(row, expandedTable) {' in js
    assert 'function maximumSplitRowActionLabelLength() {' in js
    assert 'const actionCell = buildSplitRowActionCell(row, expandedTable);' in js
    assert 'totalCell.textContent = splitSeconds(splitRowShotMLCumulativeMs(row));' in js
    assert 'finalCell.textContent = splitSeconds(splitRowFinalTimeMs(row));' in js
    assert 'function deleteShotById(shotId, source = "selected") {' in js
    assert 'deleteShotById(row.shot_id, "timing_row")' in js
    assert 'deleteShotById(segment.shot_id, "scoring_row")' in js
    assert 'function refreshReviewMediaFrame() {' in js
    assert 'if (result) refreshReviewMediaFrame();' in js
    assert 'if (expanded) root.classList.remove("timing-expanded", "metrics-expanded");' in js
    assert 'if (expanded) root.classList.remove("waveform-expanded", "metrics-expanded");' in js
    assert 'function setMetricsExpanded(expanded, { persistUiState = true } = {}) {' in js
    assert 'function setActiveTool(tool, { collapseExpandedLayout = true, persistUiState = true } = {}) {' in js
    assert 'if (changed || (collapseExpandedLayout && hadExpandedLayout)) {' in js
    assert 'setActiveTool(normalized.active_tool, { collapseExpandedLayout: false, persistUiState: false });' in js
    assert 'setActiveTool(activeTool, { collapseExpandedLayout: false, persistUiState: false });' in js
    assert js.index('setActiveTool(normalized.active_tool, { collapseExpandedLayout: false, persistUiState: false });') < js.index('setWaveformExpanded(normalized.waveform_expanded, { persistUiState: false });')
    assert 'const PIP_DEFAULTS_SECTION_ID = "pip-defaults";' in js
    assert 'if (sourceId === PIP_DEFAULTS_SECTION_ID) return true;' in js
    assert 'if (firstSource && sourceId === sourceIdentifier(firstSource, "0")) return true;' in js
    assert 'if (sourceId === PIP_DEFAULTS_SECTION_ID) return;' in js
    assert '/media/primary-audio' not in js
    assert 'function primaryAudioPreviewNeeded(video) {' not in js
    assert 'function ensurePrimaryAudioPreview(video) {' not in js
    assert 'function syncPrimaryAudioPreview({ forceSeek = false, allowDriftCorrection = false } = {}) {' not in js
    assert 'text.startsWith("Hit Factor") || text.startsWith("Final ")' in js
    assert 'function formatPractiScoreTime(value, { includeUnits = true } = {}) {' in js
    assert 'const videoRawSeconds = state.scoring_summary?.raw_seconds;' in js
    assert 'const rawDeltaSeconds = state.scoring_summary?.raw_delta_seconds;' in js
    assert 'const importedSourceFile = imported.source_name || imported.source_path || "Selected file";' in js
    assert 'const importedMatchType = imported.match_type ? formatMatchType(imported.match_type) : "";' in js
    assert 'const importedOfficialRawSeconds = imported.raw_seconds ?? state.scoring_summary?.official_raw_seconds;' in js
    assert 'const importedFinalTime = imported.final_time ?? state.scoring_summary?.official_final_time;' in js
    assert 'const currentResultLabel = state.scoring_summary?.display_label || "Result";' in js
    assert 'const currentResultValue = state.scoring_summary?.display_value || "";' in js
    assert '["Source File", importedSourceFile],' in js
    assert '["Match Type", importedMatchType],' in js
    assert '["Official Raw", formatPractiScoreTime(importedOfficialRawSeconds)],' in js
    assert '["Video Raw", formatPractiScoreTime(videoRawSeconds)],' in js
    assert '["Raw Delta", formatPractiScoreTime(rawDeltaSeconds)],' in js
    assert '[currentResultLabel, currentResultValue],' in js
    assert '["Official Final", formatPractiScoreTime(importedFinalTime, { includeUnits: false })],' in js
    assert 'syncControlValue($("overlay-position"), state.project.overlay.position);' in js
    assert 'position: $("overlay-position").value,' in js
    assert '$("badge-style-grid").addEventListener("change", (event) => {' in js
    assert '$("score-color-grid").addEventListener("change", () => {' not in js
    assert "Behavior" not in html
    assert "Score letter is saved to that shot" not in html
    assert "Score and penalty edits live here. The Splits pane stays read-only so timing edits do not fight scoring edits." in html
    assert "Score Text Colors" in html
    assert "These colors only affect score text tokens." in html
    assert "scoring-shot-row" in js
    assert 'row.classList.toggle("collapsed", !expanded);' in js
    assert 'header.className = "scoring-shot-header";' in js
    assert 'function compactScoreDisplay(letter, ruleset = activeScoringRuleset()) {' in js
    assert 'A (-0)' not in js
    assert 'if (normalizedRuleset === "idpa_time_plus") return "-0";' in js
    assert ': `Shot ${segment.shot_number} | ${compactScoreDisplay(segment.score_letter || defaultScore, ruleset)}`;' in js
    assert 'toggle.className = "scoring-shot-toggle";' in js
    assert 'toggle.textContent = expanded ? "v" : ">";' in js
    assert 'controls.hidden = !expanded;' in js
    assert 'actions.className = "scoring-shot-actions";' in js
    assert "actions.appendChild(restore);" in js
    assert "actions.appendChild(deleteShot);" in js
    assert 'const activeShotId = selectedShotId || state.project.ui_state.selected_shot_id || state.timing_segments?.[0]?.shot_id || null;' in js
    assert 'if (penaltyFields.length > 0) {' in js
    assert 'penalty_counts: collectPenaltyCounts(controls),' in js
    assert 'updateTimingRowField(row.shot_id, "score_letter", select.value)' not in js
    assert 'let timingAdjustmentDrafts = new Map();' in js
    assert 'timingAdjustmentDrafts.set(shotId, signedSeconds(numericMs(row.adjustment_ms) ?? 0));' in js
    assert 'timingAdjustmentDrafts.set(row.shot_id, String(input.value ?? "").trim());' in js
    assert 'updateTimingRowField(shotId, "adjustment_ms", draftValue);' in js
    assert 'railWidth: Math.min(savedNumber("splitshot.layout.railWidth", 64), 72)' in js
    assert 'previewLayoutSize("railWidth", clamp(event.clientX, 48, 72));' in js
    assert 'const parentRect = canvas.parentElement?.getBoundingClientRect();' in js
    assert 'parentRect?.width' in js
    assert 'canvas.style.width = "100%";' in js
    assert "appears inside its split badge" not in html
    assert 'scheduleSecondaryPreviewSync();' in js
    assert "empty-start" not in js
    assert "setActiveTool" in js
    assert "setActivePage" not in js
    assert 'let overlayFrameMode = null;' in js
    assert 'function overlayRenderPositionMs(video, mediaTimeS = null) {' in js
    assert 'function previewOverlayFrameRect(frameRect, video) {' in js
    assert 'function requestOverlayFrame(video, tick) {' in js
    assert 'function cancelOverlayFrame(video) {' in js
    assert 'renderLiveOverlay(positionMsOverride = null)' in js
    assert 'const textBoxDragging = customOverlay.classList.contains("dragging");' in js
    assert 'if (textBoxDragging) customOverlay.classList.add("dragging");' in js
    assert 'function browserShotPresentationLagFrames(video = $("primary-video")) {' in js
    assert 'return "mozPaintedFrames" in video ? 1 : 0;' in js
    assert 'function shotDisplayTimeMs(shotTimeMs, video = $("primary-video")) {' in js
    assert 'if (shotDisplayTimeMs(shot.time_ms) <= positionMs) index = shotIndex;' in js
    assert 'return Math.max(0, Math.floor(mediaTimeS * 1000));' in js
    assert 'return Math.max(0, Math.floor((video?.currentTime || 0) * 1000));' in js


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
    assert ".status-bar {\n  align-items: center;" in css
    assert ".processing-bar {" in css
    assert ".command-strip" not in css
    assert ".empty-start" not in css
    assert ".metrics-strip" not in css
    assert ".rail-action" not in css
    assert "--rail-width: 64px;" in css
    assert "--topbar-height: 38px;" in css
    assert "--inspector-width: 440px;" in css
    assert "--waveform-height: 206px;" in css
    assert "--resize-handle-size: 4px;" in css
    assert "--app-height: 100vh;" in css
    assert "grid-template-columns: var(--rail-width) var(--resize-handle-size) minmax(0, 1fr);" in css
    assert "grid-template-rows: var(--topbar-height) minmax(0, 1fr);" in css
    assert ".processing-bar[hidden] {\n  display: none !important;" in css
    assert "grid-auto-rows: minmax(0, 1fr);" in css
    assert "overflow: hidden;" in css
    assert "display: flex;" in css
    assert "width: var(--inspector-width);" in css
    assert "overflow-x: hidden;" in css
    assert "grid-template-rows: minmax(0, 1fr) var(--resize-handle-size) minmax(112px, var(--waveform-height));" in css
    assert "grid-template-rows: minmax(320px, 1fr) 206px;" not in css
    assert ".layout-unlocked .resize-handle" in css
    assert 'content: "🔒";' not in css
    assert 'content: "🔓";' not in css
    assert ".video-stage.merge-preview" in css
    assert ".video-stage.merge-pip #secondary-video" in css
    assert ".merge-media-list" in css
    assert ".merge-media-card" in css
    assert ".merge-media-card-header" in css
    assert ".merge-source-sync-row" in css
    assert ".merge-source-sync-buttons" in css
    assert ".cockpit-shell.inspector-compact .style-card-label" in css
    assert ".cockpit-shell.inspector-compact .style-card-label {\n  display: none;" not in css
    assert ".cockpit-shell.inspector-compact .popup-style-card" in css
    assert ".popup-overlay [data-popup-drag].popup-selected" in css
    assert ".popup-overlay [data-popup-drag].popup-outside-window" in css
    assert "@container (max-width: 620px)" in css
    assert "@container (max-width: 560px)" in css
    assert "@container (max-width: 460px)" in css
    assert "@container (max-width: 420px)" in css
    assert ".popup-bubble-card .text-box-card-actions {\n  flex-wrap: wrap;" in css
    assert ".popup-motion-point-row,\n  .metrics-row {\n    grid-template-columns: minmax(0, 1fr);" in css
    assert ".color-control-pair,\n  .opacity-control-pair {\n    margin-left: 0;\n    width: 100%;" in css
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
    assert "grid-template-rows: auto auto minmax(0, 1fr) auto;" in css
    assert ".scoring-shot-toggle" in css
    assert ".scoring-shot-controls[hidden] {\n  display: none !important;" in css
    assert ".scoring-shot-actions" in css
    assert ".timing-adjustment-input" in css
    assert ".timing-column-resize" in css
    assert "grid-template-columns: minmax(0, 0.45fr) minmax(0, 1.15fr) minmax(0, 0.62fr) minmax(0, 0.62fr) minmax(0, 1.55fr) minmax(0, 0.5fr) minmax(0, 1.05fr) minmax(0, 0.9fr) minmax(0, 0.72fr) minmax(0, 0.52fr) minmax(0, 0.6fr);" in css
    assert "grid-template-columns: minmax(0, 1.15fr) minmax(0, 0.62fr) minmax(0, 0.62fr) minmax(0, 1.55fr);" in css
    assert ".scoring-shot-row.collapsed" in css
    assert ".timing-action-remove" in css
    assert "width: calc(var(--timing-action-chip-chars, 8) * 0.72ch + 3.2rem);" in css
    assert ".waveform-window-handle" in css
    assert ".penalty-grid" in css
    assert ".export-log-output" in css
    assert ".modal" in css
    assert ".metrics-summary-grid" in css
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
    assert "min-height: var(--app-height, 100vh);" in css
    assert "touch-action: none;" in css
    assert "touch-action: manipulation;" in css
    assert "-webkit-user-select: none;" in css
    assert "user-select: none;" in css
    assert "-webkit-appearance: none;" in css
    assert "input:disabled," in css
    assert "#custom-overlay.has-badge" in css
    assert '#custom-overlay.has-badge [data-text-box-drag]' in css
    assert 'min-width: 104px;' not in css
    assert 'min-width: 92px;' not in css
    assert "input[type=\"range\"]::-webkit-slider-thumb" in css
    assert "input[type=\"checkbox\"]" in css
    assert "font-family: -apple-system" in css
    assert "font-size: 13px;" in css
    assert ".color-control-pair" in css
    assert ".color-hex-input.invalid" in css


def test_browser_ui_includes_webkit_rendering_guards() -> None:
    js = (STATIC_ROOT / "app.js").read_text()

    assert 'setCssPixels("--app-height", viewportHeight);' in js
    assert 'document.documentElement?.clientHeight' in js
    assert 'window.visualViewport?.height' in js
    assert 'function waveformCanvasDisplayHeight(canvas) {' in js
    assert 'function persistWaveformViewport() {' in js
    assert 'function primaryVideoStateSnapshot(video) {' in js
    assert 'function logPrimaryVideoState(eventName) {' in js
    assert 'document.addEventListener("visibilitychange", handleWindowVisibilityRestore);' in js
    assert 'window.addEventListener("focus", handleWindowVisibilityRestore);' in js
    assert 'window.addEventListener("pageshow", handleWindowVisibilityRestore);' in js
    assert 'window.getComputedStyle(shotList).display !== "none"' in js
    assert 'window.visualViewport?.addEventListener("resize", handleViewportLayoutChange);' in js
    assert 'window.visualViewport?.addEventListener("scroll", handleViewportLayoutChange);' not in js
    assert 'function renderViewportLayout() {' in js
    assert 'function requestRender() {' in js
    assert 'function withPreservedScrollState(elements, callback) {' in js
    assert 'window.requestAnimationFrame(() => renderWaveform());' in js
    assert 'typeof video.requestVideoFrameCallback === "function"' in js
    assert 'video.requestVideoFrameCallback(tick);' in js
    assert 'video.cancelVideoFrameCallback(overlayFrame);' in js
    assert 'document.addEventListener("pointermove", moveLayoutResize);' in js
    assert 'document.addEventListener("pointerup", endLayoutResize);' in js
    assert 'document.addEventListener("pointercancel", endLayoutResize);' in js
    assert 'document.addEventListener("lostpointercapture", endLayoutResize);' in js
    assert 'document.addEventListener("pointermove", handleWaveformPointerMove);' in js
    assert 'document.addEventListener("pointerup", handleWaveformPointerUp);' in js
    assert 'const timeMs = draggedShotIndex >= 0 && index === draggedShotIndex && pendingDragTimeMs !== null' in js
    assert 'document.addEventListener("pointercancel", handleWaveformPointerUp);' in js
    assert 'document.addEventListener("lostpointercapture", handleWaveformPointerUp);' in js
    assert 'document.addEventListener("lostpointercapture", endOverlayBadgeDrag);' in js
    assert 'document.addEventListener("lostpointercapture", endMergePreviewDrag);' in js
    assert 'document.addEventListener("lostpointercapture", endTextBoxDrag);' in js
    assert 'function restoreVideoElementFrame(video) {' in js
    assert 'function restoreReviewStage() {' in js
    assert 'function scheduleReviewStageRestore() {' in js
    assert 'function handleWindowVisibilityRestore() {' in js
    assert 'function computeExportCropBox(width, height, aspectRatio, centerX, centerY) {' in js
    assert 'function exportTargetDimensions(cropWidth, cropHeight) {' in js
    assert 'function fitAspectRect(width, height, aspectRatio) {' in js
    assert 'function previewFrameGeometry(video, container) {' in js
    assert 'function overlayDisplayScale(video, frameRect, outputWidth = null) {' in js
    assert 'function scaledOverlayPixelValue(value, scale, minimum = 0) {' in js
    assert 'releasePointer(activeResize.target, activeResize.pointerId);' in js
    assert '["loadedmetadata", "loadeddata"].forEach((eventName) => {' in js
    assert '$("primary-video").addEventListener("volumechange", () => {' in js
    assert '$("primary-video").addEventListener("canplay", () => {' in js
    assert '$("primary-video").addEventListener("error", () => {' in js
    assert '["volumechange", "canplay", "error"].forEach((eventName) => {' not in js
    assert 'activity("video.primary.state", {' in js
    assert 'ensurePrimaryVideoAudio($("primary-video"));' not in js
    assert 'ensurePrimaryVideoAudio(audio);' not in js
    assert 'function isColorInput(control) {' in js
    assert 'function previewOverlayControlChanges() {' in js
    assert 'function commitOverlayControlChanges() {' in js
    assert 'badge.style.fontWeight = state.project.overlay.font_bold ? "700" : "400";' in js
    assert 'badge.style.wordBreak = "normal";' in js
    assert 'const frameGeometry = previewFrameGeometry(video, stage);' in js
    assert 'const frameRect = roundedRect(previewOverlayFrameRect(frameGeometry?.frameRect || stage.getBoundingClientRect(), video));' in js
    assert 'const overlayScale = frameGeometry?.scale || overlayDisplayScale(video, frameRect);' in js
    assert 'bindOverlayColorInput(card.querySelector(\'[data-text-box-field="background_color"]\'));' in js
    assert 'bindOverlayColorInput(card.querySelector(\'[data-text-box-field="text_color"]\'));' in js
    assert 'function bindOverlayColorInput(control) {' in js
    assert 'const mediaTimeS = Number.isFinite(metadata?.mediaTime) ? metadata.mediaTime : null;' in js
    assert 'frame_source: mediaTimeS === null ? "animation-frame" : "video-frame",' in js
    assert 'syncPrimaryAudioPreview({ allowDriftCorrection: true });' not in js
    assert 'if (overlayFrame !== null) return;' in js


def test_browser_ui_guards_preview_failures_and_drag_resize() -> None:
    js = (STATIC_ROOT / "app.js").read_text()

    assert 'let secondaryPreviewPlayErrorKey = null;' in js
    assert 'let processingBarShowTimer = null;' in js
    assert 'let processingBarHideTimer = null;' in js
    assert 'function stateHasShot(nextState, shotId) {' in js
    assert 'const isSameProject = currentProjectId && nextProjectId && currentProjectId === nextProjectId;' in js
    assert '? mergeProjectUiState(nextState.project.ui_state, readProjectUiStatePayload())' in js
    assert 'if (!stateHasShot(state, selectedShotId)) {' in js
    assert 'selectedShotId = stateHasShot(state, nextUiState.selected_shot_id) ? nextUiState.selected_shot_id : null;' in js
    assert 'function clearSecondaryPreviewPlayError() {' in js
    assert 'function reportSecondaryPreviewPlayError(error) {' in js
    assert 'if (secondary.readyState < HTMLMediaElement.HAVE_CURRENT_DATA || secondaryPreviewPlayErrorKey) {' in js
    assert 'syncMergePreviewElements(primary);' in js
    assert 'return;' in js
    assert 'if (error?.name === "AbortError") return;' in js
    assert 'activity("video.secondary_play.error", { name: errorName, error: errorMessage });' in js
    assert 'secondary.play().catch(() => {});' not in js
    assert 'ensurePrimaryVideoAudio(video);' not in js
    assert 'ensurePrimaryVideoAudio(audio);' not in js
    assert 'ensurePrimaryVideoAudio(secondary);' in js
    assert 'logPrimaryVideoState("source.attach");' in js
    assert 'const primaryMediaPath = buildMediaUrl(state.media.primary_url || "/media/primary", path);' in js
    assert 'const secondaryMediaPath = buildMediaUrl(state.media.secondary_url || "/media/secondary", secondaryPath);' in js
    assert 'media.dataset.mediaUrl = mediaPath;' in js
    assert 'video.dataset.mediaUrl = primaryMediaPath;' in js
    assert 'const { startClientX, startClientY, startX, startY } = textBoxDrag;' in js
    assert 'const frameRect = previewFrameClientRect($("primary-video"), stage) || stage.getBoundingClientRect();' in js
    assert 'video.style.objectFit = "cover";' in js
    assert 'video.style.objectPosition = `${cropCenterX * 100}% ${cropCenterY * 100}%`;' in js
    assert 'positionOverlayContainer(overlay, state.project.overlay.shot_quadrant, frameRect, {' in js
    assert 'const textBoxGroups = new Map();' in js
    assert 'configureTextBoxGroup(group, quadrant, frameRect, overlayScale);' in js
    assert 'let overlayColorCommitTimer = null;' in js
    assert 'let waveformPanDrag = null;' in js
    assert 'let waveformNavigatorDrag = null;' in js
    assert 'let reviewStageRestoreFrame = null;' in js
    assert 'let reviewStageRestoreSecondFrame = null;' in js
    assert 'const OVERLAY_COLOR_COMMIT_DELAY_MS = 900;' in js
    assert 'const WAVEFORM_PAN_DRAG_THRESHOLD_PX = 4;' in js
    assert 'if (event.pointerId !== undefined && draggingShotPointerId !== undefined && event.pointerId !== draggingShotPointerId) return;' in js
    assert 'if (event.pointerId !== undefined && overlayBadgeDrag.pointerId !== undefined && event.pointerId !== overlayBadgeDrag.pointerId) return;' in js
    assert 'if (event.pointerId !== undefined && mergePreviewDrag.pointerId !== undefined && event.pointerId !== mergePreviewDrag.pointerId) return;' in js
    assert 'overlay.style.flexWrap = ["left", "right"].includes(direction) ? "wrap" : "nowrap";' in js
    assert 'function bindOverlayColorInput(control) {' in js
    assert 'control.addEventListener("click", () => openColorPicker(control));' in js
    assert 'syncOverlayHexControl(control);' in js
    assert 'scheduleOverlayColorCommit();' in js
    assert 'flushOverlayColorCommit();' in js
    assert 'startWaveformPanDrag(event);' in js
    assert '$("waveform-window-track").addEventListener("pointerdown", handleWaveformNavigatorPointerDown);' in js
    assert 'bindOverlayColorInput(card.querySelector(\'[data-field="background_color"]\'));' in js
    assert 'setOverlayTextBoxField(textBoxCard.dataset.boxId, textBoxField, normalized, { rerender: false });' in js
    assert 'if (hadExpandedLayout) scheduleReviewStageRestore();' in js
    assert 'if (isColorInput(event.target)) return;' in js
    assert 'target: customOverlay,' in js


def test_browser_overlay_badges_scale_with_video_display_size() -> None:
    js = (STATIC_ROOT / "app.js").read_text()

    assert 'const scaledMargin = scaledOverlayPixelValue(overlayMargin, scale, 0);' in js
    assert 'const scaledGap = scaledOverlayPixelValue(overlaySpacing, scale, 0);' in js
    assert 'const OVERLAY_BADGE_PADDING_X_PX = 10;' in js
    assert 'const OVERLAY_BADGE_PADDING_Y_PX = 5;' in js
    assert 'function overlayAutoSizedBadgeContents() {' in js
    assert 'function overlayAutoBubbleSize() {' in js
    assert 'function syncOverlayBubbleSizeControls() {' in js
    assert 'const scaledPaddingY = scaledOverlayPixelValue(OVERLAY_BADGE_PADDING_Y_PX, scale, 0);' in js
    assert 'const scaledPaddingX = scaledOverlayPixelValue(OVERLAY_BADGE_PADDING_X_PX, scale, 0);' in js
    assert 'badge.style.fontSize = `${scaledOverlayPixelValue(state.project.overlay.font_size || 14, scale, 1)}px`;' in js
    assert 'const resolvedWidth = widthOverride > 0' in js
    assert 'const resolvedHeight = heightOverride > 0' in js
    assert 'const autoBubbleSize = state.project.overlay.bubble_width > 0 && state.project.overlay.bubble_height > 0' in js
    assert 'badgeElement(`Timer ${seconds(elapsed)}`, state.project.overlay.timer_badge, size, null, null, null, "center", overlayScale, autoBubbleSize);' in js
    assert 'scoreBadgeContent(shot, index + 1, splitSeconds(splitMs), splitRowIntervalLabel(splitRow))' in js
    assert 'badgeElement(`${summary.display_label} ${summary.display_value}`, state.project.overlay.hit_factor_badge, size, null, null, null, "center", overlayScale, autoBubbleSize);' in js
    assert 'function scoreTokenColor(token) {' in js


def test_browser_processing_bar_uses_delayed_show_and_minimum_visibility() -> None:
    js = (STATIC_ROOT / "app.js").read_text()

    assert 'const PROCESSING_BAR_SHOW_DELAY_MS = 180;' in js
    assert 'const PROCESSING_BAR_MIN_VISIBLE_MS = 320;' in js
    assert 'function scheduleProcessingBarShow(message, detail) {' in js
    assert 'function scheduleProcessingBarHide(finalMessage = "Ready.") {' in js
    assert 'function forceHideProcessingBar(finalMessage = "Ready.") {' in js
    assert 'scheduleProcessingBarShow(message, detail);' in js
    assert 'if (busyCount === 0) {' in js
    assert 'stopProcessingProgress(100);' in js
    assert 'scheduleProcessingBarHide(finalMessage);' in js
    assert 'forceHideProcessingBar();' in js


def test_browser_overlay_badges_use_container_gap_instead_of_per_badge_margin() -> None:
    js = (STATIC_ROOT / "app.js").read_text()

    assert 'badge.style.margin = "0";' in js
    assert 'customOverlay.style.padding = "0";' in js
    assert 'customOverlay.style.gap = "0";' in js


def test_browser_color_picker_is_custom_and_os_agnostic() -> None:
    css = (STATIC_ROOT / "styles.css").read_text()
    html = (STATIC_ROOT / "index.html").read_text()
    js = (STATIC_ROOT / "app.js").read_text()

    assert '.color-swatch-button {' in css
    assert '.color-picker-dialog {' in css
    assert '.color-picker-swatches {' in css
    assert 'cursor: pointer;' in css
    assert 'input[type="color"] {' not in css
    assert 'id="color-picker-modal"' in html
    assert 'id="color-picker-preview"' in html
    assert 'id="close-color-picker"' in html
    assert 'data-close-color-picker="true"' in html
    assert 'function updateColorPickerFromSliders({ commit = false } = {}) {' in js
    assert 'function updateColorPickerFromHexInput({ commit = false } = {}) {' in js


def test_browser_buttons_are_logged_and_wired_to_actions() -> None:
    html = (STATIC_ROOT / "index.html").read_text()
    js = (STATIC_ROOT / "app.js").read_text()

    assert 'activity("button.click"' in js

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
        "popup-import-shots",
        "add-timing-event",
        "delete-selected",
        "expand-timing",
        "export-video",
        "browse-export-path",
        "browse-primary-path",
        "new-project",
        "browse-project-path",
        "import-practiscore",
        "save-project",
        "open-project",
        "delete-project",
        "add-merge-media",
        "review-add-text-box",
        "review-add-imported-box",
        "show-export-log",
        "export-export-log",
        "close-export-log",
        "close-color-picker",
        "metrics-export-csv",
        "metrics-export-text",
        "generate-shotml-proposals",
        "reset-shotml-defaults",
        "toggle-layout-lock-video",
        "toggle-layout-lock-waveform",
        "toggle-layout-lock-inspector",
        "resize-rail",
        "resize-sidebar",
        "resize-waveform",
    }
    behavior_attributes = (
        "data-tool=",
        "data-waveform-mode=",
        "data-nudge=",
        "data-sync=",
        "data-open-merge-media",
        "data-layout-lock-toggle",
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
    js = (STATIC_ROOT / "app.js").read_text()

    assert "primary_display_name" in js
    assert 'replace(/^[a-f0-9]{32}_/i, "")' in js


def test_browser_ui_removes_gpa_from_browser_preset_catalog() -> None:
    js = (STATIC_ROOT / "app.js").read_text()

    assert "gpa_time_plus" not in js


def test_browser_overlay_color_inputs_preview_on_input_and_commit_on_change() -> None:
    js = (STATIC_ROOT / "app.js").read_text()
    match = re.search(r"function bindOverlayColorInput\(control\) \{(?P<body>.*?)\n\}", js, re.S)

    assert match is not None
    body = match.group("body")
    assert 'control.addEventListener("click", () => openColorPicker(control));' in body
    assert 'control.addEventListener("keydown", (event) => {' in body
    assert 'if (event.key !== "Enter" && event.key !== " ") return;' in body
    assert 'openColorPicker(control);' in body
    assert 'hexInput.addEventListener("input", () => updateColorFromHexInput(hexInput));' in body
    assert 'hexInput.addEventListener("change", () => updateColorFromHexInput(hexInput, { commit: true }));' in body
    assert 'hexInput.addEventListener("blur", () => updateColorFromHexInput(hexInput, { commit: true }));' in body


def test_browser_client_validates_remote_state_shape_and_restores_server_selection() -> None:
    js = (STATIC_ROOT / "app.js").read_text()

    assert "function hasCompleteProjectState(nextState)" in js
    assert "nextState?.project?.overlay" in js
    assert "nextState?.project?.merge" in js
    assert "nextState?.project?.export" in js
    assert "nextState?.project?.ui_state" in js
    assert "nextState?.metrics" in js
    assert "nextState?.media" in js
    assert "const isSameProject = currentProjectId && nextProjectId && currentProjectId === nextProjectId;" in js
    assert "if (isSameProject) mergeProjectDetailsDraft(nextState.project);" in js
    assert "applyProjectUiState(nextUiState);" in js
    assert "selectedShotId = stateHasShot(state, nextUiState.selected_shot_id) ? nextUiState.selected_shot_id : null;" in js


def test_browser_overlay_payload_filters_unknown_badge_cards() -> None:
    js = (STATIC_ROOT / "app.js").read_text()
    match = re.search(r"function readOverlayPayload\(\) \{(?P<body>.*?)\n\}", js, re.S)

    assert "const VALID_OVERLAY_BADGE_NAMES = new Set(badgeControls.map(([badgeName]) => badgeName));" in js
    assert match is not None
    body = match.group("body")
    assert 'if (!VALID_OVERLAY_BADGE_NAMES.has(badge)) return;' in body
    assert 'card.querySelectorAll("[data-field]")' in body
    assert 'const value = isColorInput(input)' in body
    assert '? readColorControlValue(input)' in body
    assert '? opacityValueFromPercent(input.value)' in body


def test_browser_auto_apply_snapshots_form_payloads_before_debounce() -> None:
    js = (STATIC_ROOT / "app.js").read_text()

    assert 'async function applyThresholdNow() {' in js
    assert 'const autoApplyShotMLSettings = debounce((settings) => {' in js
    assert 'const autoApplyProjectDetails = debounce((payload) => {' in js
    assert 'const autoApplyPractiScoreContext = debounce((payload) => {' in js
    assert 'const autoApplyOverlay = debounce((payload) => {' in js
    assert 'const autoApplyMerge = debounce((payload) => {' in js
    assert 'const autoApplyExportLayout = debounce((payload) => {' in js
    assert 'const autoApplyExportSettings = debounce((payload) => {' in js
    assert 'const autoApplyScoring = debounce(({ scoringPayload, ruleset }) => {' in js
    assert 'scheduleShotMLSettingsApply();' in js
    assert 'applyProjectDetailsDraft(readProjectDetailsPayload());' in js
    assert 'renderHeader();' in js
    assert 'autoApplyProjectDetails(readProjectDetailsPayload());' in js
    assert 'autoApplyPractiScoreContext(readPractiScoreContextPayload());' in js
    assert 'autoApplyShotMLSettings.cancel?.();' in js
    assert 'autoApplyProjectDetails.cancel?.();' in js
    assert 'autoApplyPractiScoreContext.cancel?.();' in js
    assert 'autoApplyOverlay(readOverlayPayload());' in js
    assert 'autoApplyMerge(readMergePayload());' in js
    assert 'autoApplyExportLayout(readExportLayoutPayload());' in js
    assert 'autoApplyExportSettings(readExportSettingsPayload());' in js
    assert '$("threshold").addEventListener("change", scheduleThresholdApply);' in js
    assert '$("apply-threshold").addEventListener("click", applyThresholdNow);' in js
    assert '$("new-project").addEventListener("click", async () => {\n    await createNewProject();' in js
    assert 'const shouldReplace = window.confirm(`A SplitShot project already exists in:\\n${targetPath}\\n\\nReplace it with a new blank project?`);' in js
    assert 'const resetResult = await callApi("/api/project/new", {});' in js
    assert 'const savedResult = await callApi("/api/project/save", { path: projectPath });' in js
    assert 'const shouldDelete = window.confirm(`Delete this project folder from disk?\\n\\n${projectPath}\\n\\nThis cannot be undone.`);' in js
    assert 'if (!shouldDelete) return;\n    await flushPendingProjectDrafts();\n    await callApi("/api/project/delete", {});' in js


def test_browser_merge_file_uploads_treat_partial_success_as_success() -> None:
    js = (STATIC_ROOT / "app.js").read_text()
    match = re.search(r"async function postFiles\(path, files\) \{(?P<body>.*?)\n\}", js, re.S)

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
    assert 'SUPPORTED_BROWSERS = tuple(BROWSER_TARGETS)' in script
    assert 'def audit_overlay_surfaces(page: Page) -> CheckResult:' in script
    assert 'def audit_waveform_drag(page: Page) -> CheckResult:' in script
    assert 'def audit_layout_resize_persists(page: Page) -> CheckResult:' in script
    assert 'def audit_merge_file_input_change(page: Page, primary_video: Path) -> CheckResult:' in script


def test_browser_interaction_audit_script_exists_for_real_browser_workflow() -> None:
    script = Path("scripts/audits/browser/run_browser_interaction_audit.py").read_text()

    assert '"chromium": BrowserTarget(' in script
    assert '"firefox": BrowserTarget(' in script
    assert '"safari": BrowserTarget(' in script
    assert '"webkit": BrowserTarget(' in script
    assert 'def import_primary_video(page: Page, server: BrowserControlServer, primary_video: Path) -> CheckResult:' in script
    assert 'def drag_waveform_viewport(page: Page, server: BrowserControlServer) -> CheckResult:' in script
    assert 'def drag_waveform_shot(page: Page, server: BrowserControlServer) -> CheckResult:' in script
    assert 'def drag_timer_badge(page: Page, server: BrowserControlServer) -> CheckResult:' in script
    assert 'def resize_layout_persists(page: Page, server: BrowserControlServer) -> CheckResult:' in script
    assert 'def import_practiscore_file(page: Page, server: BrowserControlServer, practiscore_path: Path) -> CheckResult:' in script
    assert 'def audit_imported_summary_default_anchor(page: Page) -> CheckResult:' in script
    assert 'def drag_imported_summary_box(page: Page, server: BrowserControlServer) -> CheckResult:' in script
    assert 'def preserve_review_inspector_scroll(page: Page, server: BrowserControlServer) -> CheckResult:' in script
    assert 'def import_merge_media(page: Page, server: BrowserControlServer, merge_video: Path) -> CheckResult:' in script
    assert 'def drag_merge_preview_persists(page: Page, server: BrowserControlServer, merge_video: Path) -> CheckResult:' in script
    assert 'def drag_merge_size_slider_commits(page: Page, server: BrowserControlServer) -> CheckResult:' in script
    assert 'def sync_nudge_commits(page: Page, server: BrowserControlServer) -> CheckResult:' in script


def test_readme_documents_one_command_uv_launch() -> None:
    readme = Path("README.md").read_text()

    assert Path(".python-version").read_text().strip() == "3.12"
    assert "uv run splitshot" in readme
    assert "uv run --python 3.12 splitshot" not in readme


def test_browser_static_logo_is_packaged() -> None:
    assert (STATIC_ROOT / "logo.png").is_file()
