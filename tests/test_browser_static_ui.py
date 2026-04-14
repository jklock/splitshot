from __future__ import annotations

import re
from pathlib import Path


STATIC_ROOT = Path("src/splitshot/browser/static")


def test_browser_ui_is_waterfall_cockpit_workflow() -> None:
    html = (STATIC_ROOT / "index.html").read_text()

    assert 'class="app-shell cockpit-shell"' in html
    assert 'href="/static/styles.css?v=20260413c"' in html
    assert 'src="/static/app.js?v=20260414c"' in html
    assert 'accept="video/*,.mp4,.m4v,.mov,.avi,.wmv,.webm,.mkv,.mpg,.mpeg,.mts,.m2ts"' in html
    assert 'accept="video/*,image/*,.mp4,.m4v,.mov,.avi,.wmv,.webm,.mkv,.mpg,.mpeg,.mts,.m2ts,.png,.jpg,.jpeg,.gif,.webp"' in html
    assert 'accept=".csv,.txt,text/csv,text/plain"' in html
    assert 'class="tool-rail"' in html
    assert 'class="status-strip"' in html
    assert 'class="review-grid"' in html
    assert 'class="review-stack"' in html
    assert 'class="inspector"' in html
    assert html.index('data-tool="project"') < html.index('data-tool="scoring"')
    assert html.index('data-tool="scoring"') < html.index('data-tool="timing"')
    assert html.index('data-tool="timing"') < html.index('data-tool="merge"')
    assert html.index('data-tool="merge"') < html.index('data-tool="overlay"')
    assert html.index('data-tool="merge"') < html.index('data-tool="review"')
    assert html.index('data-tool="review"') < html.index('data-tool="export"')
    assert 'data-tool="project"' in html
    assert 'data-tool="review"' in html
    assert 'data-tool="timing"' in html
    assert 'data-tool="edit"' not in html
    assert 'data-tool="scoring"' in html
    assert 'data-tool="overlay"' in html
    assert 'data-tool="merge"' in html
    assert 'data-tool="layout"' not in html
    assert 'data-tool="export"' in html
    assert '<img class="rail-logo" src="/static/logo.png" alt="SplitShot" />' in html
    assert '<b>Add</b>' in html
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
    assert 'id="project-name"' in html
    assert 'id="project-description"' in html
    assert 'id="match-type"' in html
    assert 'id="match-stage-number"' in html
    assert 'id="match-competitor-name"' in html
    assert 'id="match-competitor-place"' in html
    assert 'id="import-practiscore"' in html
    assert 'id="practiscore-status"' in html
    assert 'id="practiscore-import-summary"' in html
    assert 'id="current-file"' in html
    assert 'id="processing-bar"' in html
    assert 'id="selected-shot-panel"' in html
    assert 'id="split-card-grid"' not in html
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
    assert "cloud upload" not in html.lower()
    assert "Add Second Angle" not in html
    assert "Add Second Video" not in html
    assert "Add Media" in html
    assert 'id="merge-media-input"' in html
    assert 'id="practiscore-file-input"' in html
    assert 'id="merge-media-list"' in html
    assert 'id="add-merge-media"' in html
    assert "Swap Primary and First Added Item" in html
    assert "Select PractiScore Results" in html
    assert "Select Primary Video" in html
    assert "John Klockenkemper" not in html
    assert 'placeholder="Add competitor name"' in html
    assert 'placeholder="Add stage number"' in html
    assert 'placeholder="Optional"' in html
    assert "Upload Primary Video" not in html
    assert "upload an IDPA CSV" not in html
    assert "Add the match data here" in html
    assert 'id="pip-x"' in html
    assert 'id="pip-y"' in html
    merge_start = html.index('data-tool-pane="merge"')
    export_start = html.index('data-tool-pane="export"')
    project_start = html.index('data-tool-pane="project"')
    assert merge_start < html.index('id="add-merge-media"') < export_start
    assert merge_start < html.index('id="merge-layout"') < export_start
    assert merge_start < html.index('id="pip-size"') < export_start
    assert merge_start < html.index('id="swap-videos"') < export_start
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
    assert 'id="secondary-video"' in html
    assert 'id="live-overlay"' in html
    assert 'id="custom-overlay"' in html
    assert 'id="score-layer"' in html
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
    assert 'id="waveform-shot-list"' in html
    assert 'id="timing-workbench"' in html
    assert 'id="expand-timing"' in html
    assert 'aria-label="Use waveform select mode"' in html
    assert 'aria-label="Use waveform add shot mode"' in html
    assert 'id="selected-shot-copy"' in html
    assert html.index('id="timing-table"') > html.index('id="selected-shot-panel"')
    assert html.index('id="timing-table"') < html.index('id="threshold"')
    assert html.index('waveform-header') < html.index('id="waveform"')
    assert html.index('id="waveform"') < html.index('class="waveform-actions waveform-footer"')
    assert 'id="badge-style-grid"' in html
    assert 'id="score-color-grid"' in html
    assert 'id="project-name"' in html
    assert 'id="project-description"' in html
    assert 'id="merge-media-input"' in html
    assert 'id="merge-media-list"' in html
    assert 'id="add-merge-media"' in html
    assert 'id="pip-x"' in html
    assert 'id="pip-y"' in html
    assert 'aria-label="Move selected shot earlier by 10 milliseconds"' in html
    assert 'aria-label="Adjust added media sync later by 10 milliseconds"' in html
    assert 'id="max-visible-shots"' in html
    assert 'id="shot-quadrant"' in html
    assert '<option value="custom">Custom</option>' in html
    assert 'id="shot-direction"' in html
    assert 'id="overlay-custom-x"' in html
    assert 'id="bubble-width"' in html
    assert 'id="overlay-font-family"' in html
    assert 'id="show-timer"' in html
    assert 'id="custom-box-mode"' in html
    assert 'id="custom-box-text"' in html
    assert 'Imported summary' in html
    assert 'Custom Box Style' in html
    assert 'id="layout-threshold"' not in html
    assert 'id="scoring-preset"' in html
    assert 'id="scoring-imported-caption"' in html
    assert 'id="scoring-imported-summary"' in html
    assert 'id="score-option-grid"' in html
    assert 'id="scoring-penalty-grid"' in html
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
    assert 'id="export-log"' in html
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
    assert "scheduleSecondaryPreviewSync" in js
    assert "autoApplyThreshold" in js
    assert "autoApplyOverlay" in js
    assert "autoApplyMerge" in js
    assert "autoApplyLayout" in js
    assert "autoApplyExportSettings" in js
    assert "autoApplyScoring" in js
    assert "renderScoringPenaltyFields" in js
    assert "renderPractiScoreSummaries" in js
    assert "renderMergeMediaList" in js
    assert 'let exportPathDraft = "";' in js
    assert "readProjectDetailsPayload" in js
    assert "readPractiScoreContextPayload" in js
    assert "validatePractiScoreSelection" in js
    assert "autoApplyProjectDetails" in js
    assert "autoApplyPractiScoreContext" in js
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
    assert 'pickPath("project_open", "project-path", async (path)' in js
    assert 'pickPath("project_save", "project-path"' in js
    assert 'const path = $("project-path").value.trim();' in js
    assert 'const kind = currentPath ? "project_open" : "project_save";' in js
    assert 'preset: $("export-preset").value,' in js
    assert 'callApi("/api/export", buildExportPayload(path));' in js
    assert "saveProjectFlow" in js
    assert 'await callApi("/api/project/details", readProjectDetailsPayload());' in js
    assert 'const existingPath = $("project-path").value.trim();' in js
    assert js.index('const existingPath = $("project-path").value.trim();') < js.index('await callApi("/api/project/details", readProjectDetailsPayload());')
    assert 'if (targetId === "export-path") exportPathDraft = data.path;' in js
    assert '$("export-path").addEventListener("input", () => {' in js
    assert 'exportPathDraft = $("export-path").value;' in js
    assert 'const path = requireValue("export-path", "Output video path");' in js
    assert 'exportPathDraft = path;' in js
    assert "openProjectWithDialog" in js
    assert "resetMediaElement" in js
    assert '$("penalties").value = state.project.scoring.penalties' not in js
    assert "renderExportPresetOptions" in js
    assert "syncExportPathControl();" in js
    assert "processingForPath" in js
    assert 'Exporting video...' in js
    assert 'Importing media...' in js
    assert 'Parsing PractiScore stage results' in js
    assert 'setStatus("Select a PractiScore results file.");' in js
    assert 'await callApi("/api/project/practiscore", readPractiScoreContextPayload());\n    $("practiscore-file-input")?.click();' not in js
    assert "Opening file browser..." not in js
    assert "scoring-active" in js
    assert "layoutLocked" in js
    assert "applyLayoutState" in js
    assert "beginLayoutResize" in js
    assert "syncOverlayCoordinateControlState" in js
    assert "function syncCustomBoxModeState()" in js
    assert "function effectiveCustomBoxText()" in js
    assert 'const CUSTOM_QUADRANT_VALUE = "custom";' in js
    assert "const BADGE_FONT_SIZES = {" in js
    assert "function syncOverlayFontSizePreset()" in js
    assert "function ensureShotQuadrantDefaults()" in js
    assert 'activity("layout.resize.start"' in js
    assert 'activity("layout.resize.commit"' in js
    assert 'font_size: Number($("overlay-font-size").value || BADGE_FONT_SIZES[$("badge-size").value] || 14),' in js
    assert 'custom_box_mode: $("custom-box-mode").value,' in js
    assert 'overlay.custom_box_mode = payload.custom_box_mode || "manual";' in js
    assert 'if (id === "custom-box-mode") syncCustomBoxModeState();' in js
    assert 'const importedSummaryMode = (state.project.overlay.custom_box_mode || "manual") === "imported_summary";' in js
    assert 'const customBoxHasCoordinates = normalizedCoordinateValue(state.project.overlay.custom_box_x) !== null' in js
    assert 'positionOverlayContainer(customOverlay, state.project.overlay.custom_box_quadrant, frameRect);' in js
    assert 'if (customX === null || customY === null) return false;' in js
    assert 'Clear Box X/Y to use the selected quadrant.' in js
    assert 'syncOverlayFontSizePreset();' in js
    assert 'if (!$("overlay-custom-x").value) $("overlay-custom-x").value = "0.5";' in js
    assert 'if (!$("overlay-custom-y").value) $("overlay-custom-y").value = "0.5";' in js
    assert 'function pinCustomOverlayAnchor(overlay, frameRect, customPoint = null) {' in js
    assert 'if (usesCustomQuadrant(state.project.overlay.shot_quadrant) && overlay.childElementCount > 0) {' in js
    assert 'const anchorOffsetX = (badgeRect.left - overlayRect.left) + (badgeRect.width / 2);' in js
    assert 'const anchorOffsetY = (badgeRect.top - overlayRect.top) + (badgeRect.height / 2);' in js
    assert 'function splitSeconds(ms)' in js
    assert 'grid.querySelectorAll(".style-card[data-badge]")' in js
    assert 'scoreGrid.querySelectorAll(".score-color-input[data-letter]")' in js
    assert 'const scoreKeys = state.scoring_summary?.score_options || [];' in js
    assert '...Object.keys(state.project.overlay.scoring_colors || {}),' not in js
    assert 'crop_center_x:' not in js
    assert 'crop_center_y:' not in js
    assert 'const FINAL_SHOT_FLASH_HALF_PERIOD_MS' not in js
    assert 'const FINAL_SHOT_FLASH_CYCLES' not in js
    assert 'const FINAL_SHOT_FLASH_DURATION_MS' not in js
    assert '`Shot ${index + 1} ${splitSeconds(splitMs)}${scoreText}`' in js
    assert 'text.startsWith("Hit Factor") || text.startsWith("Final ")' in js
    assert '$("badge-style-grid").addEventListener("change", (event) => {' in js
    assert '$("score-color-grid").addEventListener("change", () => {' not in js
    assert "Behavior" not in html
    assert "Score letter is saved to that shot" not in html
    assert "Assign a score value on any shot row" in html
    assert "scoring-shot-row" in js
    assert 'callApi("/api/scoring/score", { shot_id: segment.shot_id, letter: select.value })' in js
    assert 'railWidth: Math.min(savedNumber("splitshot.layout.railWidth", 64), 72)' in js
    assert 'persistLayoutSize("railWidth", clamp(event.clientX, 48, 72))' in js
    assert 'const parentRect = canvas.parentElement?.getBoundingClientRect();' in js
    assert 'parentRect?.width' in js
    assert 'canvas.style.width = "100%";' in js
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
    assert "--rail-width: 64px;" in css
    assert "--topbar-height: 38px;" in css
    assert "--inspector-width: 440px;" in css
    assert "--waveform-height: 206px;" in css
    assert "--resize-handle-size: 4px;" in css
    assert "--app-height: 100vh;" in css
    assert "grid-template-columns: var(--rail-width) var(--resize-handle-size) minmax(0, 1fr);" in css
    assert "grid-template-rows: var(--topbar-height) minmax(0, 1fr);" in css
    assert ".processing-bar[hidden] {\n  display: none !important;" in css
    assert "grid-auto-rows: minmax(72px, auto);" in css
    assert "grid-template-columns: minmax(0, 1fr) repeat(4, calc(var(--inspector-width) / 4));" in css
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
    assert "#project-description" in css
    assert "-webkit-backdrop-filter: blur(6px);" in css
    assert "top: 0;\n  right: 0;\n  bottom: 0;\n  left: 0;" in css
    assert "grid-template-rows: auto minmax(0, 1fr) auto auto;" in css
    assert "grid-row: 3;" in css
    assert "top: 2.2rem;" not in css
    assert ".project-delete-button" in css
    assert "gap: 0.5rem;" in css
    assert ".cockpit.waveform-expanded .review-grid" in css
    assert ".cockpit.waveform-expanded .video-stage" in css
    assert "display: none;" in css
    assert ".cockpit.timing-expanded .timing-workbench" in css
    assert "grid-template-rows: auto auto minmax(0, 1fr) auto;" in css
    assert ".timeline-strip" not in css
    assert ".timeline-marker" not in css
    assert "input[type=\"color\"]" in css
    assert ".penalty-grid" in css
    assert ".export-log" in css
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
    assert 'input[type="number"]::-webkit-outer-spin-button' not in css
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
    assert "input[type=\"range\"]::-webkit-slider-thumb" in css
    assert "input[type=\"checkbox\"]" in css
    assert "font-family: -apple-system" in css
    assert "font-size: 13px;" in css


def test_browser_ui_includes_webkit_rendering_guards() -> None:
    js = (STATIC_ROOT / "app.js").read_text()

    assert 'setCssPixels("--app-height", viewportHeight);' in js
    assert 'document.documentElement?.clientHeight' in js
    assert 'window.visualViewport?.height' in js
    assert 'function waveformCanvasDisplayHeight(canvas) {' in js
    assert 'window.getComputedStyle(shotList).display !== "none"' in js
    assert 'window.visualViewport?.addEventListener("resize", handleViewportLayoutChange);' in js
    assert 'window.visualViewport?.addEventListener("scroll", handleViewportLayoutChange);' in js
    assert 'window.requestAnimationFrame(() => renderWaveform());' in js
    assert 'document.addEventListener("pointermove", moveLayoutResize);' in js
    assert 'document.addEventListener("pointerup", endLayoutResize);' in js
    assert 'document.addEventListener("pointercancel", endLayoutResize);' in js
    assert 'document.addEventListener("pointermove", handleWaveformPointerMove);' in js
    assert 'document.addEventListener("pointerup", handleWaveformPointerUp);' in js
    assert 'document.addEventListener("pointercancel", handleWaveformPointerUp);' in js
    assert 'releasePointer(activeResize.target, activeResize.pointerId);' in js
    assert '["loadedmetadata", "loadeddata"].forEach((eventName) => {' in js
    assert 'function isColorInput(control) {' in js
    assert 'function previewOverlayControlChanges() {' in js
    assert 'function commitOverlayControlChanges() {' in js
    assert '["custom-box-background-color", "custom-box-text-color"].forEach((id) => {' in js
    assert 'bindOverlayColorInput($(id));' in js
    assert 'function bindOverlayColorInput(control) {' in js


def test_browser_ui_guards_preview_failures_and_drag_resize() -> None:
    js = (STATIC_ROOT / "app.js").read_text()

    assert 'let secondaryPreviewPlayErrorKey = null;' in js
    assert 'if (selectedShotId && !(state.project?.analysis?.shots || []).some((shot) => shot.id === selectedShotId)) {' in js
    assert 'function clearSecondaryPreviewPlayError() {' in js
    assert 'function reportSecondaryPreviewPlayError(error) {' in js
    assert 'if (secondary.readyState < HTMLMediaElement.HAVE_CURRENT_DATA || secondaryPreviewPlayErrorKey) return;' in js
    assert 'if (error?.name === "AbortError") return;' in js
    assert 'activity("video.secondary_play.error", { name: errorName, error: errorMessage });' in js
    assert 'secondary.play().catch(() => {});' not in js
    assert 'const { startClientX, startClientY, startX, startY } = customOverlayDrag;' in js
    assert 'const frameRect = videoContentRect($("primary-video"), stage) || stage.getBoundingClientRect();' in js
    assert 'let overlayColorCommitTimer = null;' in js
    assert 'const OVERLAY_COLOR_COMMIT_DELAY_MS = 900;' in js
    assert 'function bindOverlayColorInput(control) {' in js
    assert 'control.addEventListener("input", previewOverlayColorChanges);' in js
    assert 'control.addEventListener("change", previewOverlayColorChanges);' in js
    assert 'control.addEventListener("blur", flushOverlayColorCommit);' in js
    assert 'bindOverlayColorInput(card.querySelector(\'[data-field="background_color"]\'));' in js
    assert 'bindOverlayColorInput(input);' in js
    assert 'if (isColorInput(event.target)) return;' in js


def test_browser_color_inputs_keep_native_webkit_appearance() -> None:
    css = (STATIC_ROOT / "styles.css").read_text()

    assert 'input[type="color"] {' in css
    assert '-webkit-appearance: auto;' in css
    assert 'appearance: auto;' in css
    assert 'cursor: pointer;' in css
    assert '-webkit-appearance: none;' not in css.split('input[type="color"] {', 1)[1].split('}', 1)[0]


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
        "collapse-timing",
        "add-timing-event",
        "delete-selected",
        "expand-timing",
        "swap-videos",
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


def test_readme_documents_one_command_uv_launch() -> None:
    readme = Path("README.md").read_text()

    assert Path(".python-version").read_text().strip() == "3.12"
    assert "uv run splitshot" in readme
    assert "uv run --python 3.12 splitshot" not in readme


def test_browser_static_logo_is_packaged() -> None:
    assert (STATIC_ROOT / "logo.png").is_file()
