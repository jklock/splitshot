let state = null;
let selectedShotId = null;
let activeTool = "project";
let overlayFrame = null;
let waveformMode = "select";
let draggingShotId = null;
let pendingDragTimeMs = null;
let timingRowEdits = new Set();
let overlayStyleMode = "square";
let overlaySpacing = 8;
let overlayMargin = 8;
let waveformZoomX = savedNumber("splitshot.waveform.zoomX", 1);
let waveformShotAmplitudeById = {};
let waveformOffsetMs = Math.max(0, Number(window.localStorage.getItem("splitshot.waveform.offsetMs")) || 0);
let busyCount = 0;
let layoutLocked = window.localStorage.getItem("splitshot.layoutLocked") !== "false";
let layoutSizes = {
  railWidth: Math.min(savedNumber("splitshot.layout.railWidth", 64), 72),
  inspectorWidth: savedNumber("splitshot.layout.inspectorWidth", 440),
  waveformHeight: savedNumber("splitshot.layout.waveformHeight", 206),
};
let activeResize = null;
let currentProjectId = null;
let exportPathDraft = "";
let secondaryPreviewSyncFrame = null;
let secondaryPreviewPlayErrorKey = null;
let overlayColorCommitTimer = null;
let processingBarShowTimer = null;
let processingBarHideTimer = null;
let processingBarVisibleAtMs = 0;
let activityQueue = [];
let activityFlushTimer = null;
let overlayBadgeDrag = null;
let mergePreviewDrag = null;

const OVERLAY_COLOR_COMMIT_DELAY_MS = 900;
const PROCESSING_BAR_SHOW_DELAY_MS = 180;
const PROCESSING_BAR_MIN_VISIBLE_MS = 320;
const ACTIVITY_FLUSH_DELAY_MS = 160;
const ACTIVITY_BATCH_SIZE = 48;
const INSPECTOR_COMPACT_WIDTH = 700;

const $ = (id) => document.getElementById(id);

const badgeControls = [
  ["timer_badge", "Timer Badge"],
  ["shot_badge", "Shot Badge"],
  ["current_shot_badge", "Current Shot Badge"],
  ["hit_factor_badge", "Score Badge"],
];
const VALID_OVERLAY_BADGE_NAMES = new Set(badgeControls.map(([badgeName]) => badgeName));
const BADGE_FONT_SIZES = {
  XS: 10,
  S: 12,
  M: 14,
  L: 16,
  XL: 20,
};
const CUSTOM_QUADRANT_VALUE = "custom";
const HEX_COLOR_PATTERN = /^#?(?:[\da-f]{3}|[\da-f]{6})$/i;

function flushActivityQueue() {
  if (activityFlushTimer !== null) {
    window.clearTimeout(activityFlushTimer);
    activityFlushTimer = null;
  }
  if (activityQueue.length === 0) return;
  const entries = activityQueue;
  activityQueue = [];
  fetch("/api/activity", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ entries }),
    keepalive: true,
  }).catch((error) => {
    console.warn("[splitshot] activity log failed", error);
  });
}

function queueActivity(event, detail = {}) {
  activityQueue.push({ event, detail, ts: new Date().toISOString() });
  if (activityQueue.length >= ACTIVITY_BATCH_SIZE) {
    flushActivityQueue();
    return;
  }
  if (activityFlushTimer !== null) return;
  activityFlushTimer = window.setTimeout(() => {
    activityFlushTimer = null;
    flushActivityQueue();
  }, ACTIVITY_FLUSH_DELAY_MS);
}

function activity(event, detail = {}) {
  console.info("[splitshot]", event, detail);
  queueActivity(event, detail);
}

function buttonDescriptor(button) {
  return {
    id: button.id || "",
    text: button.textContent.trim().replace(/\s+/g, " "),
    tool: button.dataset.tool || "",
    waveform_mode: button.dataset.waveformMode || "",
    nudge_ms: button.dataset.nudge || "",
    sync_ms: button.dataset.sync || "",
    opens_secondary: button.hasAttribute("data-open-secondary"),
    opens_media: button.hasAttribute("data-open-merge-media") || button.hasAttribute("data-open-secondary"),
  };
}

function wireGlobalActivityLogging() {
  document.addEventListener("click", (event) => {
    if (!(event.target instanceof Element)) return;
    const button = event.target.closest("button");
    if (!button) return;
    activity("button.click", buttonDescriptor(button));
  }, true);
  document.addEventListener("change", (event) => {
    if (!(event.target instanceof HTMLElement)) return;
    const control = event.target;
    if (!["INPUT", "SELECT", "TEXTAREA"].includes(control.tagName)) return;
    activity("control.change", {
      id: control.id || "",
      name: control.name || "",
      type: control.type || control.tagName.toLowerCase(),
      value: control.type === "file" ? Array.from(control.files || []).map((file) => file.name) : control.value,
    });
  }, true);
  document.addEventListener("input", (event) => {
    if (!(event.target instanceof HTMLElement)) return;
    const control = event.target;
    if (!["INPUT", "TEXTAREA"].includes(control.tagName)) return;
    if (control.type === "file") return;
    activity("control.input", {
      id: control.id || "",
      name: control.name || "",
      type: control.type || control.tagName.toLowerCase(),
      value: control.value,
    });
  }, true);
}

function seconds(ms) {
  if (ms === null || ms === undefined || ms === "") return "--.--";
  return (ms / 1000).toFixed(2);
}

function precise(ms) {
  if (ms === null || ms === undefined || ms === "") return "";
  return (ms / 1000).toFixed(3);
}

function splitSeconds(ms) {
  if (ms === null || ms === undefined || ms === "") return "--.--s";
  return `${seconds(ms)}s`;
}

function numericMs(value) {
  if (value === null || value === undefined || value === "") return null;
  const numeric = Number(value);
  return Number.isFinite(numeric) ? numeric : null;
}

function orderedShotsByTime() {
  return [...(state?.project?.analysis?.shots || [])]
    .sort((left, right) => Number(left.time_ms || 0) - Number(right.time_ms || 0));
}

function resolvedSplitMsForShot(shotId, shotNumber = null, absoluteTimeMs = null) {
  const splitRow = (state?.split_rows || []).find((row) => row.shot_id === shotId);
  const splitMs = numericMs(splitRow?.split_ms);
  if (splitMs !== null) return Math.max(0, splitMs);

  const timingSegment = (state?.timing_segments || []).find((segment) => segment.shot_id === shotId);
  const segmentMs = numericMs(timingSegment?.segment_ms);
  if (segmentMs !== null) return Math.max(0, segmentMs);

  const effectiveShotNumber = shotNumber ?? splitRow?.shot_number ?? timingSegment?.shot_number ?? null;
  if (effectiveShotNumber !== 1) return null;

  const drawMs = numericMs(state?.metrics?.draw_ms);
  if (drawMs !== null) return Math.max(0, drawMs);

  const effectiveAbsoluteMs = numericMs(absoluteTimeMs)
    ?? numericMs(splitRow?.absolute_time_ms)
    ?? numericMs(timingSegment?.absolute_ms);
  const beepMs = numericMs(state?.project?.analysis?.beep_time_ms_primary);
  if (effectiveAbsoluteMs !== null && beepMs !== null) {
    return Math.max(0, effectiveAbsoluteMs - beepMs);
  }
  if (effectiveAbsoluteMs !== null) return Math.max(0, effectiveAbsoluteMs);

  const cumulativeMs = numericMs(timingSegment?.cumulative_ms);
  return cumulativeMs === null ? null : Math.max(0, cumulativeMs);
}

function formatMatchType(matchType) {
  return {
    uspsa: "USPSA",
    ipsc: "IPSC",
    idpa: "IDPA",
  }[String(matchType || "").toLowerCase()] || "PractiScore";
}

function formatNumber(value, digits = 2) {
  if (value === null || value === undefined || value === "") return "";
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return String(value);
  if (Number.isInteger(numeric)) return String(numeric);
  return numeric.toFixed(digits);
}

function formatImportedCounts(scoreCounts) {
  return Object.entries(scoreCounts || {})
    .filter(([, value]) => Number(value || 0) !== 0)
    .map(([label, value]) => `${label} ${formatNumber(value, 2)}`)
    .join(", ");
}

function penaltyFieldLabel(fieldId, fallbackLabel = "") {
  return {
    procedural_errors: "PE",
    manual_no_shoots: "NS",
    manual_misses: "M",
    non_threats: "NT",
    flagrant_penalties: "FP",
    failures_to_do_right: "FTDR",
    finger_pe: "FPE",
    steel_misses: "PM",
    stop_plate_failures: "SPF",
    steel_not_down: "SND",
  }[fieldId] || fallbackLabel || fieldId.replace(/_/g, " ");
}

function formatPenaltyCountsText(penaltyCounts) {
  return Object.entries(penaltyCounts || {})
    .filter(([, value]) => Number(value || 0) > 0)
    .map(([fieldId, value]) => `${penaltyFieldLabel(fieldId)} x${formatNumber(value, 1)}`)
    .join(", ");
}

function formatShotBadgeSuffix(shot) {
  if (!state?.project?.scoring?.enabled || !shot?.score) return "";
  const parts = [shot.score.letter];
  const penaltyText = formatPenaltyCountsText(shot.score.penalty_counts);
  if (penaltyText) parts.push(penaltyText);
  return ` ${parts.join(" ")}`;
}

function formatConfidenceValue(confidence) {
  if (confidence === null || confidence === undefined || confidence === "") return "Manual";
  const numeric = Number(confidence);
  if (!Number.isFinite(numeric)) return String(confidence);
  if (numeric <= 1) return `${Math.round(numeric * 100)}%`;
  return `${Math.round(numeric)}%`;
}

function isLowConfidence(confidence) {
  const numeric = Number(confidence);
  if (!Number.isFinite(numeric)) return false;
  return numeric <= 1 ? numeric < 0.9 : numeric < 90;
}

function numberInputValue(input, fallback = 0) {
  const numeric = Number(input?.value ?? fallback);
  return Number.isFinite(numeric) && numeric > 0 ? numeric : 0;
}

function collectPenaltyCounts(scope, selector = ".shot-penalty-input[data-penalty-id]") {
  const penaltyCounts = {};
  scope.querySelectorAll(selector).forEach((input) => {
    penaltyCounts[input.dataset.penaltyId] = numberInputValue(input, 0);
  });
  return penaltyCounts;
}

function renderDetailsList(id, rows) {
  const list = $(id);
  if (!list) return;
  list.innerHTML = "";
  rows
    .filter(([, value]) => value !== "" && value !== null && value !== undefined)
    .forEach(([label, value]) => {
      const title = document.createElement("dt");
      title.textContent = label;
      const detail = document.createElement("dd");
      detail.textContent = String(value);
      list.appendChild(title);
      list.appendChild(detail);
    });
}

function requireValue(id, label) {
  const value = $(id).value.trim();
  if (!value) throw new Error(`${label} is required.`);
  return value;
}

function controlIsActive(control) {
  return !!control && document.activeElement === control;
}

function syncControlValue(control, value) {
  if (!control || controlIsActive(control)) return;
  const nextValue = value === null || value === undefined ? "" : String(value);
  if (control.value !== nextValue) control.value = nextValue;
  if (isColorInput(control)) syncOverlayHexControl(control);
}

function syncControlChecked(control, checked) {
  if (!control || controlIsActive(control)) return;
  const nextChecked = Boolean(checked);
  if (control.checked !== nextChecked) control.checked = nextChecked;
}

function isColorInput(control) {
  return control instanceof HTMLInputElement && control.type === "color";
}

function fileName(path) {
  if (!path) return "No video selected";
  const normalized = path.split("\\").join("/");
  const base = normalized.split("/").filter(Boolean).pop() || path;
  return base.replace(/^[a-f0-9]{32}_/i, "");
}

function hexToRgb(hex) {
  const value = hex.replace("#", "");
  const full = value.length === 3
    ? value.split("").map((char) => char + char).join("")
    : value;
  return [
    parseInt(full.slice(0, 2), 16),
    parseInt(full.slice(2, 4), 16),
    parseInt(full.slice(4, 6), 16),
  ];
}

function rgba(hex, opacity) {
  const [r, g, b] = hexToRgb(hex || "#111827");
  return `rgba(${r}, ${g}, ${b}, ${opacity ?? 0.9})`;
}

function normalizeHexColor(value) {
  if (typeof value !== "string") return null;
  const raw = value.trim();
  if (!HEX_COLOR_PATTERN.test(raw)) return null;
  const withHash = raw.startsWith("#") ? raw : `#${raw}`;
  const normalized = withHash.length === 4
    ? `#${withHash.slice(1).split("").map((char) => char + char).join("")}`
    : withHash;
  return normalized.toLowerCase();
}

function overlayHexControlFor(colorInput) {
  return colorInput?.closest(".color-field")?.querySelector(".color-hex-input") || null;
}

function syncOverlayHexControl(colorInput) {
  if (!isColorInput(colorInput)) return;
  const hexInput = overlayHexControlFor(colorInput);
  if (!(hexInput instanceof HTMLInputElement)) return;
  const normalized = normalizeHexColor(colorInput.value) || "#000000";
  if (!controlIsActive(hexInput) && hexInput.value !== normalized.toUpperCase()) {
    hexInput.value = normalized.toUpperCase();
  }
  hexInput.classList.remove("invalid");
}

function updateColorFromHexInput(hexInput, { commit = false } = {}) {
  const colorInput = hexInput?.closest(".color-field")?.querySelector('input[type="color"]');
  if (!isColorInput(colorInput) || !(hexInput instanceof HTMLInputElement)) return;
  const normalized = normalizeHexColor(hexInput.value);
  if (!normalized) {
    hexInput.classList.add("invalid");
    if (commit) syncOverlayHexControl(colorInput);
    return;
  }
  hexInput.classList.remove("invalid");
  const changed = colorInput.value !== normalized;
  colorInput.value = normalized;
  syncOverlayHexControl(colorInput);
  if (!changed) {
    if (commit) flushOverlayColorCommit();
    return;
  }
  previewOverlayControlChanges();
  if (commit) {
    queueOverlayColorCommit();
  }
}

function clampNumber(value, min, max) {
  return Math.min(max, Math.max(min, value));
}

function isImagePath(path) {
  return !!path && /\.(png|jpe?g|webp|gif|bmp|svg)$/i.test(path);
}

function nowMs() {
  return window.performance?.now?.() ?? Date.now();
}

function clearProcessingBarShowTimer() {
  if (processingBarShowTimer === null) return;
  window.clearTimeout(processingBarShowTimer);
  processingBarShowTimer = null;
}

function clearProcessingBarHideTimer() {
  if (processingBarHideTimer === null) return;
  window.clearTimeout(processingBarHideTimer);
  processingBarHideTimer = null;
}

function hideProcessingBarNow(finalMessage = "Ready.") {
  const bar = $("processing-bar");
  clearProcessingBarShowTimer();
  clearProcessingBarHideTimer();
  processingBarVisibleAtMs = 0;
  $("processing-message").textContent = finalMessage;
  $("processing-detail").textContent = "Ready";
  bar.hidden = true;
}

function scheduleProcessingBarShow(message, detail) {
  const bar = $("processing-bar");
  clearProcessingBarHideTimer();
  $("processing-message").textContent = message;
  $("processing-detail").textContent = detail;
  if (!bar.hidden) return;
  clearProcessingBarShowTimer();
  processingBarShowTimer = window.setTimeout(() => {
    processingBarShowTimer = null;
    if (busyCount <= 0) return;
    bar.hidden = false;
    processingBarVisibleAtMs = nowMs();
  }, PROCESSING_BAR_SHOW_DELAY_MS);
}

function scheduleProcessingBarHide(finalMessage = "Ready.") {
  clearProcessingBarShowTimer();
  clearProcessingBarHideTimer();
  const bar = $("processing-bar");
  $("processing-message").textContent = finalMessage;
  $("processing-detail").textContent = "Ready";
  if (bar.hidden) return;
  const remainingMs = Math.max(0, PROCESSING_BAR_MIN_VISIBLE_MS - (nowMs() - processingBarVisibleAtMs));
  processingBarHideTimer = window.setTimeout(() => {
    processingBarHideTimer = null;
    if (busyCount !== 0) return;
    hideProcessingBarNow(finalMessage);
  }, remainingMs);
}

function forceHideProcessingBar(finalMessage = "Ready.") {
  busyCount = 0;
  hideProcessingBarNow(finalMessage);
}

function setStatus(message) {
  $("status").textContent = message;
  const processingMessage = $("processing-message");
  if (processingMessage) processingMessage.textContent = message;
  activity("ui.status", { message });
}

function beginProcessing(message, detail = "Working locally") {
  busyCount += 1;
  scheduleProcessingBarShow(message, detail);
  activity("ui.processing.start", { message, detail, busy_count: busyCount });
  return (finalMessage = "Ready.") => {
    busyCount = Math.max(0, busyCount - 1);
    activity("ui.processing.finish", { message: finalMessage, busy_count: busyCount });
    if (busyCount === 0) scheduleProcessingBarHide(finalMessage);
  };
}

function debounce(fn, delayMs = 250) {
  let timer = null;
  let lastArgs = null;

  const debounced = (...args) => {
    lastArgs = args;
    window.clearTimeout(timer);
    timer = window.setTimeout(() => {
      timer = null;
      const pendingArgs = lastArgs;
      lastArgs = null;
      fn(...(pendingArgs || []));
    }, delayMs);
  };

  debounced.cancel = () => {
    window.clearTimeout(timer);
    timer = null;
    lastArgs = null;
  };

  return debounced;
}

function savedNumber(key, fallback) {
  const value = Number(window.localStorage.getItem(key));
  return Number.isFinite(value) && value > 0 ? value : fallback;
}

function clamp(value, min, max) {
  return Math.max(min, Math.min(max, value));
}

function normalizedCoordinateValue(value) {
  if (value === null || value === undefined || value === "") return null;
  const numeric = Number(value);
  return Number.isFinite(numeric) ? clamp(numeric, 0, 1) : null;
}

function currentPipSizePercent(source = null, fallback = 35) {
  const sourceSize = Number(source?.pip_size_percent);
  if (Number.isFinite(sourceSize) && sourceSize > 0) return sourceSize;
  return Number(
    state?.project?.merge?.pip_size_percent
      ?? Number(String(state?.project?.merge?.pip_size || "35%").replace(/%$/, ""))
      ?? fallback,
  );
}

function sourceIdentifier(source, fallback = "") {
  const asset = source?.asset || source || {};
  return source?.id || asset.id || fallback || fileName(asset.path || "");
}

function currentSourceSyncOffsetMs(source = null) {
  return Math.round(Number(source?.sync_offset_ms) || 0);
}

function formatSyncOffsetLabel(offsetMs) {
  const numeric = Math.round(Number(offsetMs) || 0);
  return `Sync ${numeric > 0 ? "+" : ""}${numeric} ms`;
}

function mergePreviewTargetTime(primaryTime, source = null) {
  return Math.max(0, primaryTime + (currentSourceSyncOffsetMs(source) / 1000));
}

function mergeSourceById(sourceId) {
  return (state?.project?.merge_sources || []).find((source, index) => sourceIdentifier(source, String(index)) === sourceId) || null;
}

function syncMergeSourceControls(sourceId, pipX, pipY, pipSizePercent = null, syncOffsetMs = null) {
  const xValue = Number.isFinite(pipX) ? pipX.toFixed(3) : "";
  const yValue = Number.isFinite(pipY) ? pipY.toFixed(3) : "";
  const sizeValue = Number.isFinite(pipSizePercent) ? Math.round(pipSizePercent) : "";
  const offsetValue = Math.round(Number(syncOffsetMs) || 0);
  document.querySelectorAll(`[data-source-id="${sourceId}"][data-merge-source-field="x"]`).forEach((input) => {
    syncControlValue(input, xValue);
  });
  document.querySelectorAll(`[data-source-id="${sourceId}"][data-merge-source-field="y"]`).forEach((input) => {
    syncControlValue(input, yValue);
  });
  document.querySelectorAll(`[data-source-id="${sourceId}"][data-merge-source-field="size"]`).forEach((input) => {
    syncControlValue(input, sizeValue);
  });
  document.querySelectorAll(`[data-source-id="${sourceId}"][data-merge-source-output="size"]`).forEach((output) => {
    output.textContent = sizeValue === "" ? "" : `${sizeValue}%`;
  });
  document.querySelectorAll(`[data-source-id="${sourceId}"][data-merge-source-sync-label]`).forEach((label) => {
    label.textContent = formatSyncOffsetLabel(offsetValue);
  });
}

function updateLocalMergeSourcePosition(sourceId, pipX, pipY, pipSizePercent = null) {
  const source = mergeSourceById(sourceId);
  if (!source || !state?.project) return;
  const nextSize = clampNumber(
    Number(
      pipSizePercent
        ?? source.pip_size_percent
        ?? state.project.merge.pip_size_percent
        ?? 35,
    ) || 35,
    10,
    95,
  );
  const nextX = normalizedCoordinateValue(pipX) ?? 1;
  const nextY = normalizedCoordinateValue(pipY) ?? 1;
  source.pip_size_percent = nextSize;
  source.pip_x = nextX;
  source.pip_y = nextY;
  syncMergeSourceControls(sourceId, nextX, nextY, nextSize, source.sync_offset_ms);
}

function updateLocalMergeSourceSyncOffset(sourceId, syncOffsetMs) {
  const source = mergeSourceById(sourceId);
  if (!source || !state?.project) return;
  source.sync_offset_ms = Math.round(Number(syncOffsetMs) || 0);
  if (state.project.merge_sources?.[0]?.id === sourceId) {
    state.project.analysis.sync_offset_ms = source.sync_offset_ms;
  }
  syncMergeSourceControls(sourceId, normalizedCoordinateValue(source.pip_x), normalizedCoordinateValue(source.pip_y), currentPipSizePercent(source), source.sync_offset_ms);
}

function syncOverlayFontSizePreset() {
  const badgeSize = $("badge-size").value;
  const fontSize = BADGE_FONT_SIZES[badgeSize] || BADGE_FONT_SIZES.M;
  $("overlay-font-size").value = String(fontSize);
}

function ensureShotQuadrantDefaults() {
  if (!usesCustomQuadrant($("shot-quadrant").value)) return;
  if (!$("overlay-custom-x").value) $("overlay-custom-x").value = "0.5";
  if (!$("overlay-custom-y").value) $("overlay-custom-y").value = "0.5";
}

function syncOverlayPreviewStateFromControls() {
  if (!state?.project) return;
  const payload = readOverlayPayload();
  const overlay = state.project.overlay;
  overlay.badge_size = payload.badge_size;
  overlay.style_type = payload.style_type;
  overlay.spacing = Math.max(0, Number(payload.spacing || 0));
  overlay.margin = Math.max(0, Number(payload.margin || 0));
  overlay.max_visible_shots = Math.max(1, Number(payload.max_visible_shots || overlay.max_visible_shots || 1));
  overlay.shot_quadrant = payload.shot_quadrant;
  overlay.shot_direction = payload.shot_direction;
  overlay.custom_x = normalizedCoordinateValue(payload.custom_x);
  overlay.custom_y = normalizedCoordinateValue(payload.custom_y);
  overlay.timer_x = normalizedCoordinateValue(payload.timer_x);
  overlay.timer_y = normalizedCoordinateValue(payload.timer_y);
  overlay.draw_x = normalizedCoordinateValue(payload.draw_x);
  overlay.draw_y = normalizedCoordinateValue(payload.draw_y);
  overlay.score_x = normalizedCoordinateValue(payload.score_x);
  overlay.score_y = normalizedCoordinateValue(payload.score_y);
  overlay.bubble_width = Math.max(0, Number(payload.bubble_width || 0));
  overlay.bubble_height = Math.max(0, Number(payload.bubble_height || 0));
  overlay.font_family = payload.font_family;
  overlay.font_size = Math.max(8, Number(payload.font_size || overlay.font_size || 14));
  overlay.font_bold = Boolean(payload.font_bold);
  overlay.font_italic = Boolean(payload.font_italic);
  overlay.show_timer = Boolean(payload.show_timer);
  overlay.show_draw = Boolean(payload.show_draw);
  overlay.show_shots = Boolean(payload.show_shots);
  overlay.show_score = Boolean(payload.show_score);
  overlay.custom_box_enabled = Boolean(payload.custom_box_enabled);
  overlay.custom_box_mode = payload.custom_box_mode || "manual";
  overlay.custom_box_text = payload.custom_box_text || "";
  overlay.custom_box_quadrant = payload.custom_box_quadrant;
  overlay.custom_box_x = normalizedCoordinateValue(payload.custom_box_x);
  overlay.custom_box_y = normalizedCoordinateValue(payload.custom_box_y);
  if (overlay.custom_box_x !== null || overlay.custom_box_y !== null) {
    overlay.custom_box_quadrant = CUSTOM_QUADRANT_VALUE;
  }
  overlay.custom_box_background_color = payload.custom_box_background_color;
  overlay.custom_box_text_color = payload.custom_box_text_color;
  overlay.custom_box_opacity = clamp(Number(payload.custom_box_opacity ?? overlay.custom_box_opacity ?? 0.9), 0, 1);
  overlay.custom_box_width = Math.max(0, Number(payload.custom_box_width || 0));
  overlay.custom_box_height = Math.max(0, Number(payload.custom_box_height || 0));
  Object.entries(payload.styles).forEach(([badgeName, style]) => {
    const badge = overlay[badgeName];
    if (!badge) return;
    if (style.background_color) badge.background_color = style.background_color;
    if (style.text_color) badge.text_color = style.text_color;
    if (style.opacity !== undefined) badge.opacity = clamp(Number(style.opacity), 0, 1);
  });
  overlay.scoring_colors = {
    ...overlay.scoring_colors,
    ...payload.scoring_colors,
  };
  overlayStyleMode = overlay.style_type || overlayStyleMode;
  overlaySpacing = Number(overlay.spacing ?? overlaySpacing);
  overlayMargin = Number(overlay.margin ?? overlayMargin);
}

function previewOverlayControlChanges() {
  syncOverlayPreviewStateFromControls();
  renderLiveOverlay();
}

function commitOverlayControlChanges() {
  previewOverlayControlChanges();
  scheduleOverlayApply();
}

function clearOverlayColorCommitTimer() {
  if (overlayColorCommitTimer === null) return;
  window.clearTimeout(overlayColorCommitTimer);
  overlayColorCommitTimer = null;
}

function scheduleOverlayColorCommit() {
  clearOverlayColorCommitTimer();
  overlayColorCommitTimer = window.setTimeout(() => {
    overlayColorCommitTimer = null;
    scheduleOverlayApply();
  }, OVERLAY_COLOR_COMMIT_DELAY_MS);
}

function previewOverlayColorChanges() {
  previewOverlayControlChanges();
}

function queueOverlayColorCommit() {
  previewOverlayControlChanges();
  scheduleOverlayColorCommit();
}

function flushOverlayColorCommit() {
  if (overlayColorCommitTimer === null) return;
  clearOverlayColorCommitTimer();
  scheduleOverlayApply();
}

function bindOverlayColorInput(control) {
  if (!isColorInput(control) || control.dataset.overlayColorBound === "true") return;
  control.dataset.overlayColorBound = "true";
  const hexInput = overlayHexControlFor(control);
  control.addEventListener("input", previewOverlayColorChanges);
  control.addEventListener("input", () => syncOverlayHexControl(control));
  control.addEventListener("change", () => {
    syncOverlayHexControl(control);
    queueOverlayColorCommit();
  });
  control.addEventListener("blur", () => {
    syncOverlayHexControl(control);
    flushOverlayColorCommit();
  });
  if (hexInput instanceof HTMLInputElement && hexInput.dataset.overlayColorBound !== "true") {
    hexInput.dataset.overlayColorBound = "true";
    syncOverlayHexControl(control);
    hexInput.addEventListener("input", () => updateColorFromHexInput(hexInput));
    hexInput.addEventListener("change", () => updateColorFromHexInput(hexInput, { commit: true }));
    hexInput.addEventListener("blur", () => updateColorFromHexInput(hexInput, { commit: true }));
  }
}

function syncMergePreviewStateFromControls() {
  if (!state?.project) return;
  const merge = state.project.merge;
  merge.enabled = $("merge-enabled").checked;
  merge.layout = $("merge-layout").value;
  merge.pip_size_percent = clampNumber(Number($("pip-size").value) || 35, 10, 95);
  merge.pip_x = normalizedCoordinateValue($("pip-x").value) ?? 1;
  merge.pip_y = normalizedCoordinateValue($("pip-y").value) ?? 1;
}

function usesCustomQuadrant(quadrant) {
  return quadrant === CUSTOM_QUADRANT_VALUE;
}

function defaultTimingEventLabel(kind) {
  return {
    reload: "Reload",
    malfunction: "Malfunction",
    custom_label: "Custom Label",
  }[String(kind || "")] || String(kind || "Event").replace(/_/g, " ");
}

function timingEventKindLabel(kind) {
  return {
    reload: "Reload",
    malfunction: "Malfunction",
    custom_label: "Custom",
  }[String(kind || "")] || defaultTimingEventLabel(kind);
}

function timingEventPlacementText(event) {
  if (event.after_shot_id && event.before_shot_id) {
    return `Between ${shotLabelForEvent(event.after_shot_id)} and ${shotLabelForEvent(event.before_shot_id)}`;
  }
  if (event.before_shot_id) return `Before ${shotLabelForEvent(event.before_shot_id)}`;
  if (event.after_shot_id) return `After ${shotLabelForEvent(event.after_shot_id)}`;
  return "Floating marker";
}

function syncOverlayCoordinateControlState() {
  const customEnabled = usesCustomQuadrant($("shot-quadrant").value);
  [["overlay-custom-x", "X"], ["overlay-custom-y", "Y"]].forEach(([id, axis]) => {
    const input = $(id);
    input.disabled = !customEnabled;
    input.placeholder = customEnabled ? "0.50" : "Custom only";
    input.title = customEnabled
      ? `Set custom ${axis.toLowerCase()} position from 0 to 1.`
      : "Enable the Custom quadrant to edit coordinates.";
  });
}

function effectiveCustomBoxText() {
  if (!state?.project?.overlay) return "";
  if ((state.project.overlay.custom_box_mode || "manual") === "imported_summary") {
    return state.scoring_summary?.imported_overlay_text || "";
  }
  return state.project.overlay.custom_box_text || "";
}

function syncCustomBoxModeState() {
  const mode = $("custom-box-mode").value;
  const textArea = $("custom-box-text");
  const hint = $("custom-box-mode-hint");
  const importedReady = Boolean(state?.scoring_summary?.imported_overlay_text);
  const usesImportedSummary = mode === "imported_summary";

  textArea.disabled = usesImportedSummary;
  textArea.placeholder = usesImportedSummary
    ? "Uses the imported PractiScore stage summary after the last shot"
    : "Text to show over the reviewed video";
  textArea.title = usesImportedSummary
    ? "This box auto-populates from the imported PractiScore stage and appears after the last shot."
    : "Enter the text to show over the reviewed video.";
  if (!hint) return;
  hint.textContent = usesImportedSummary
    ? importedReady
      ? "Uses the imported PractiScore stage summary and appears only after the last shot. Clear Box X/Y to use the selected quadrant."
      : "Import an IDPA CSV or USPSA/IPSC PractiScore results file first. The summary appears after the last shot. Clear Box X/Y to use the selected quadrant."
    : "Uses the text below and follows the same box styling and placement as export. Clear Box X/Y to use the selected quadrant.";
}

function syncTimingEventLabelState() {
  const kind = $("timing-event-kind")?.value || "reload";
  const input = $("timing-event-label");
  if (!input) return;
  input.placeholder = kind === "custom_label" ? "Hand switch" : defaultTimingEventLabel(kind);
  input.title = kind === "custom_label"
    ? "Enter the short phrase that should appear in the overlay."
    : "Optional short overlay label. Leave blank to use the default event name.";
}

function layoutViewportHeight() {
  const cockpit = document.querySelector(".cockpit");
  const documentHeight = document.documentElement?.clientHeight || 0;
  const visualViewportHeight = window.visualViewport?.height || 0;
  const cockpitHeight = cockpit?.getBoundingClientRect().height || cockpit?.clientHeight || 0;
  return Math.max(1, Math.floor(visualViewportHeight || documentHeight || window.innerHeight || cockpitHeight));
}

function alignToEdge(value) {
  if (value === "left" || value === "top") return "flex-start";
  if (value === "middle") return "center";
  return "flex-end";
}

function setCssPixels(name, value) {
  document.documentElement.style.setProperty(name, `${Math.round(value)}px`);
}

function capturePointer(target, pointerId) {
  if (!target || typeof target.setPointerCapture !== "function") return;
  try {
    target.setPointerCapture(pointerId);
  } catch {
    // Some browsers reject capture if the pointer is no longer active.
  }
}

function releasePointer(target, pointerId) {
  if (!target || typeof target.releasePointerCapture !== "function") return;
  try {
    target.releasePointerCapture(pointerId);
  } catch {
    // Some browsers release capture automatically when a drag ends.
  }
}

function applyLayoutState() {
  const viewportHeight = layoutViewportHeight();
  setCssPixels("--app-height", viewportHeight);
  layoutSizes = {
    railWidth: clamp(layoutSizes.railWidth, 48, 72),
    inspectorWidth: clamp(layoutSizes.inspectorWidth, 320, Math.max(320, window.innerWidth * 0.48)),
    waveformHeight: clamp(layoutSizes.waveformHeight, 112, Math.max(112, viewportHeight * 0.42)),
  };
  setCssPixels("--rail-width", layoutSizes.railWidth);
  setCssPixels("--inspector-width", layoutSizes.inspectorWidth);
  setCssPixels("--waveform-height", layoutSizes.waveformHeight);
  const shell = document.querySelector(".cockpit-shell");
  if (shell) {
    shell.classList.toggle("layout-locked", layoutLocked);
    shell.classList.toggle("layout-unlocked", !layoutLocked);
    shell.classList.toggle("resizing-layout", activeResize !== null);
    shell.classList.toggle("inspector-compact", layoutSizes.inspectorWidth < INSPECTOR_COMPACT_WIDTH);
  }
  document.querySelectorAll("[data-layout-lock-toggle]").forEach((toggle) => {
    const target = toggle.id.replace("toggle-layout-lock-", "");
    const scope = target ? `${target} layout` : "layout";
    toggle.textContent = layoutLocked ? "🔒" : "🔓";
    toggle.setAttribute("aria-label", `${layoutLocked ? "Unlock" : "Lock"} ${scope}`);
  });
}

function persistLayoutSize(key, value) {
  layoutSizes[key] = value;
  const storageKey = {
    railWidth: "splitshot.layout.railWidth",
    inspectorWidth: "splitshot.layout.inspectorWidth",
    waveformHeight: "splitshot.layout.waveformHeight",
  }[key];
  window.localStorage.setItem(storageKey, String(Math.round(value)));
  applyLayoutState();
  if (state) renderWaveform();
}

function toggleLayoutLock() {
  layoutLocked = !layoutLocked;
  window.localStorage.setItem("splitshot.layoutLocked", String(layoutLocked));
  activity("layout.lock.toggle", { locked: layoutLocked });
  applyLayoutState();
}

function resetLayout() {
  layoutSizes = { railWidth: 64, inspectorWidth: 440, waveformHeight: 206 };
  ["splitshot.layout.railWidth", "splitshot.layout.inspectorWidth", "splitshot.layout.waveformHeight"].forEach((key) => {
    window.localStorage.removeItem(key);
  });
  activity("layout.reset", layoutSizes);
  applyLayoutState();
  if (state) renderWaveform();
}

function beginLayoutResize(kind, event) {
  if (layoutLocked) {
    activity("layout.unlock.request", { kind });
    toggleLayoutLock();
    return;
  }
  activeResize = { kind, pointerId: event.pointerId, target: event.currentTarget };
  capturePointer(activeResize.target, event.pointerId);
  document.body.classList.add("resizing-layout");
  activity("layout.resize.start", { kind });
  applyLayoutState();
}

function moveLayoutResize(event) {
  if (!activeResize) return;
  if (event.pointerId !== undefined && activeResize.pointerId !== undefined && event.pointerId !== activeResize.pointerId) return;
  const kind = activeResize.kind;
  if (kind === "railWidth") {
    persistLayoutSize("railWidth", clamp(event.clientX, 48, 72));
  } else if (kind === "inspectorWidth") {
    const grid = document.querySelector(".review-grid");
    const right = grid?.getBoundingClientRect().right || window.innerWidth;
    persistLayoutSize("inspectorWidth", clamp(right - event.clientX, 320, Math.max(320, window.innerWidth * 0.48)));
  } else if (kind === "waveformHeight") {
    const stack = document.querySelector(".review-stack");
    const rect = stack?.getBoundingClientRect();
    if (rect) {
      persistLayoutSize("waveformHeight", clamp(rect.bottom - event.clientY, 112, Math.max(112, rect.height * 0.48)));
    }
  }
}

function endLayoutResize(event) {
  if (!activeResize) return;
  if (event.pointerId !== undefined && activeResize.pointerId !== undefined && event.pointerId !== activeResize.pointerId) return;
  const kind = activeResize.kind;
  releasePointer(activeResize.target, activeResize.pointerId);
  activeResize = null;
  document.body.classList.remove("resizing-layout");
  activity("layout.resize.commit", { kind, sizes: layoutSizes });
  applyLayoutState();
}

function setActiveTool(tool) {
  if (!document.querySelector(`[data-tool-pane="${tool}"]`)) tool = "project";
  const changed = activeTool !== tool;
  activeTool = tool;
  window.localStorage.setItem("splitshot.activeTool", tool);
  if (changed) {
    $("cockpit-root")?.classList.remove("waveform-expanded", "timing-expanded");
    const expand = $("expand-waveform");
    if (expand) expand.textContent = "Expand";
  }
  $("cockpit-root").classList.toggle("scoring-active", tool === "scoring");
  const inspector = document.querySelector(".inspector");
  if (inspector) inspector.dataset.activeTool = tool;
  document.querySelectorAll(".tool-item").forEach((item) => {
    item.classList.toggle("active", item.dataset.tool === tool);
  });
  document.querySelectorAll(".tool-pane").forEach((panel) => {
    panel.classList.toggle("active", panel.dataset.toolPane === tool);
  });
  if (tool === "merge") {
    $("add-merge-media")?.focus();
  }
  if (changed) activity("ui.tool.active", { tool });
  renderLiveOverlay();
}

async function api(path, payload = null) {
  activity("api.request", { path, payload });
  const processing = processingForPath(path);
  const finishProcessing = payload === null || processing === null
    ? null
    : beginProcessing(processing.message, processing.detail);
  const options = payload === null
    ? {}
    : {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      };
  const response = await fetch(path, options);
  const data = await response.json();
  if (!response.ok || data.error) throw new Error(data.error || response.statusText);
  applyRemoteState(data);
  render();
  activity("api.response", { path, status: data.status, shots: data.metrics?.total_shots });
  if (finishProcessing) finishProcessing(data.status || "Ready.");
  return data;
}

async function callApi(path, payload = null) {
  try {
    return await api(path, payload);
  } catch (error) {
    forceHideProcessingBar();
    setStatus(error.message);
    activity("api.error", { path, error: error.message });
    return null;
  }
}

function processingForPath(path) {
  if (path === "/api/export") return { message: "Exporting video...", detail: "Running FFmpeg locally" };
  if (path === "/api/import/primary") {
    return { message: "Analyzing primary video...", detail: "Detecting beep and shots locally" };
  }
  if (path === "/api/import/merge" || path === "/api/files/merge") {
    return { message: "Importing media...", detail: "Adding media to the list" };
  }
  if (path === "/api/import/secondary") {
    return { message: "Importing media...", detail: "Adding media to the list" };
  }
  if (path === "/api/project/details") return { message: "Updating project details...", detail: "Saving metadata locally" };
  if (path === "/api/project/practiscore") return { message: "Updating match import settings...", detail: "Saving stage and competitor details" };
  if (path === "/api/project/save") return { message: "Saving project...", detail: "Updating project bundle" };
  if (path === "/api/project/delete") return { message: "Deleting project...", detail: "Removing project bundle" };
  if (path === "/api/project/new") return { message: "Creating new project...", detail: "Resetting project state" };
  return null;
}

async function postFile(path, file) {
  if (!file) return null;
  const form = new FormData();
  form.append("file", file, file.name);
  const uploadState = path === "/api/files/practiscore"
    ? { message: `Importing ${file.name}...`, detail: "Parsing PractiScore stage results" }
    : path === "/api/files/merge"
      ? { message: `Importing ${file.name}...`, detail: "Adding media to the list" }
      : { message: `Analyzing ${file.name}...`, detail: "Detecting beep and shots" };
  const finishProcessing = beginProcessing(uploadState.message, uploadState.detail);
  setStatus(uploadState.message);
  activity("file.selected", { path, name: file.name, size: file.size });
  try {
    const response = await fetch(path, { method: "POST", body: form });
    const data = await response.json();
    if (!response.ok || data.error) throw new Error(data.error || response.statusText);
    applyRemoteState(data);
    render();
    activity("file.ingested", { path, name: file.name, shots: data.metrics?.total_shots });
    finishProcessing(data.status || "Analysis complete.");
    return data;
  } catch (error) {
    finishProcessing(error.message);
    setStatus(error.message);
    activity("file.error", { path, name: file.name, error: error.message });
    return null;
  }
}

async function pickPath(kind, targetId, afterSelect = null) {
  const target = $(targetId);
  activity("dialog.path.request", { kind, target: targetId, current: target.value });
  try {
    const response = await fetch("/api/dialog/path", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ kind, current: target.value }),
    });
    const data = await response.json();
    if (!response.ok || data.error) throw new Error(data.error || response.statusText);
    if (data.path) {
      target.value = data.path;
      if (targetId === "export-path") exportPathDraft = data.path;
      activity("dialog.path.selected", { kind, target: targetId, path: data.path });
      if (afterSelect) {
        await afterSelect(data.path);
      }
    } else {
      activity("dialog.path.cancelled", { kind, target: targetId });
    }
    return data.path || "";
  } catch (error) {
    setStatus(error.message);
    activity("dialog.path.error", { kind, target: targetId, error: error.message });
    return "";
  }
}

async function refresh() {
  activity("api.refresh", {});
  try {
    const response = await fetch("/api/state");
    const data = await response.json();
    if (!response.ok || data.error) throw new Error(data.error || response.statusText);
    applyRemoteState(data);
    render();
  } catch (error) {
    setStatus(error.message);
    activity("api.error", { path: "/api/state", error: error.message });
  }
}

function applyRemoteState(nextState) {
  if (!hasCompleteProjectState(nextState)) {
    throw new Error("Received invalid project state from the local server.");
  }
  const nextProjectId = nextState?.project?.id || "";
  const remoteSelectedShotId = nextState.project.ui_state?.selected_shot_id || null;
  if (currentProjectId && nextProjectId && currentProjectId !== nextProjectId) {
    resetLocalProjectView();
  }
  currentProjectId = nextProjectId;
  state = nextState;
  if (stateHasShot(state, selectedShotId)) return;
  selectedShotId = stateHasShot(state, remoteSelectedShotId) ? remoteSelectedShotId : null;
}

function hasCompleteProjectState(nextState) {
  return Boolean(
    nextState?.project?.analysis
      && nextState?.project?.overlay
      && nextState?.project?.merge
      && nextState?.project?.export
      && nextState?.project?.ui_state
      && nextState?.metrics
      && nextState?.media,
  );
}

function stateHasShot(nextState, shotId) {
  return Boolean(shotId)
    && (nextState?.project?.analysis?.shots || []).some((shot) => shot.id === shotId);
}

function resetLocalProjectView() {
  selectedShotId = null;
  draggingShotId = null;
  pendingDragTimeMs = null;
  exportPathDraft = "";
  timingRowEdits.clear();
  waveformMode = "select";
  waveformZoomX = 1;
  waveformShotAmplitudeById = {};
  waveformOffsetMs = 0;
  window.localStorage.removeItem("splitshot.waveform.zoomX");
  window.localStorage.removeItem("splitshot.waveform.offsetMs");
  resetMediaElement($("primary-video"));
  resetMediaElement($("secondary-video"));
  const secondaryImage = $("secondary-image");
  if (secondaryImage) secondaryImage.hidden = true;
  const root = $("cockpit-root");
  if (root) {
    root.classList.remove("waveform-expanded", "timing-expanded");
  }
  const expandWaveform = $("expand-waveform");
  if (expandWaveform) expandWaveform.textContent = "Expand";
  document.querySelectorAll("[data-waveform-mode]").forEach((button) => {
    button.classList.toggle("active", button.dataset.waveformMode === waveformMode);
  });
  const waveformHelp = $("waveform-help");
  if (waveformHelp) {
    waveformHelp.textContent = "Select mode: click a shot marker, drag to move, arrows nudge.";
  }
  [
    "project-title",
    "rail-project",
    "media-badge",
    "project-name",
    "project-description",
    "practiscore-status",
    "current-file",
    "timing-summary",
    "selected-shot-copy",
    "selected-timing-shot",
    "scoring-result",
    "scoring-imported-caption",
    "status",
    "processing-message",
    "processing-detail",
  ].forEach((id) => {
    const element = $(id);
    if (!element) return;
    if (id === "project-title" || id === "rail-project") {
      element.textContent = "Untitled Project";
    } else if (id === "project-name") {
      element.value = "Untitled Project";
    } else if (id === "project-description") {
      element.value = "";
    } else if (id === "practiscore-status") {
      element.textContent = "No results imported";
    } else if (id === "media-badge" || id === "current-file") {
      element.textContent = "No video selected";
    } else if (id === "timing-summary") {
      element.textContent = "No timing data.";
    } else if (id === "selected-shot-copy") {
      element.textContent = "No shot selected.";
    } else if (id === "selected-timing-shot") {
      element.textContent = "No shot selected";
    } else if (id === "scoring-result") {
      element.textContent = "--";
    } else if (id === "scoring-imported-caption") {
      element.textContent = "No PractiScore stage imported.";
    } else if (id === "status" || id === "processing-message") {
      element.textContent = "Ready.";
    } else if (id === "processing-detail") {
      element.textContent = "Local processing";
    }
  });
  [
    "primary-file-path",
    "project-path",
    "export-path",
    "match-type",
    "match-stage-number",
    "match-competitor-name",
    "match-competitor-place",
  ].forEach((id) => {
    const element = $(id);
    if (element) element.value = "";
  });
  const mergeMediaInput = $("merge-media-input");
  if (mergeMediaInput) mergeMediaInput.value = "";
  const practiscoreFileInput = $("practiscore-file-input");
  if (practiscoreFileInput) practiscoreFileInput.value = "";
  const mergeMediaList = $("merge-media-list");
  if (mergeMediaList) mergeMediaList.innerHTML = "";
  renderDetailsList("practiscore-import-summary", []);
  renderDetailsList("scoring-imported-summary", []);
  setActiveTool("project");
  stopOverlayLoop();
}

function resetMediaElement(video) {
  if (!video) return;
  video.pause();
  video.removeAttribute("src");
  video.dataset.sourcePath = "";
  video.load();
}

function durationMs() {
  return Math.max(1, state?.project?.primary_video?.duration_ms || 1);
}

function waveformWindow() {
  const duration = durationMs();
  waveformZoomX = clamp(waveformZoomX, 1, 200);
  const visibleDuration = Math.max(10, duration / waveformZoomX);
  waveformOffsetMs = clamp(waveformOffsetMs, 0, Math.max(0, duration - visibleDuration));
  return {
    start: waveformOffsetMs,
    end: waveformOffsetMs + visibleDuration,
    duration: visibleDuration,
  };
}

function waveformX(timeMs, width) {
  const window = waveformWindow();
  return ((timeMs - window.start) / window.duration) * width;
}

function isWaveformVisible(timeMs) {
  const window = waveformWindow();
  return timeMs >= window.start && timeMs <= window.end;
}

function currentShotIndex(positionMs) {
  const shots = orderedShotsByTime();
  let index = -1;
  shots.forEach((shot, shotIndex) => {
    if (shot.time_ms <= positionMs) index = shotIndex;
  });
  return index;
}

function renderHeader() {
  const projectName = state.project.name;
  $("project-title").textContent = projectName;
  $("rail-project").textContent = projectName;
  $("status").textContent = state.status;
  const primaryName = state.media.primary_display_name || fileName(state.project.primary_video.path);
  $("current-file").textContent = primaryName;
  const mergeCount = (state.project.merge_sources || []).length;
  syncControlValue($("primary-file-path"), state.project.primary_video.path || "");
  $("project-path").placeholder = `${state.default_project_path || "~/splitshot"}/project.ssproj`;
  syncControlValue($("project-path"), state.project.path || "");
  $("media-badge").textContent = state.media.primary_available
    ? `Primary: ${primaryName}${mergeCount > 0 ? ` • ${mergeCount} added item${mergeCount === 1 ? "" : "s"}` : ""}`
    : "No video selected";
}

function renderStats() {
  $("draw").textContent = seconds(state.metrics.draw_ms);
  $("raw-time").textContent = seconds(state.metrics.raw_time_ms ?? state.metrics.stage_time_ms);
  $("shot-count").textContent = state.metrics.total_shots;
  $("avg-split").textContent = seconds(state.metrics.average_split_ms);
  $("timing-summary").textContent = state.metrics.raw_time_ms
    ? "Click Expand and Unlock to change shot values."
    : "No timing data.";
}

function mergeSourcePipRect(source, frameRect, pipSizeValue = null) {
  const asset = source.asset || source;
  const sourceWidth = Math.max(1, asset.width || 1);
  const sourceHeight = Math.max(1, asset.height || 1);
  const effectivePipSize = currentPipSizePercent(source, pipSizeValue ?? 35);
  let insetWidth = Math.max(1, Math.round(frameRect.width * (effectivePipSize / 100)));
  let insetHeight = Math.max(1, Math.round((sourceHeight / sourceWidth) * insetWidth));
  if (insetHeight > frameRect.height) {
    const fitScale = frameRect.height / insetHeight;
    insetWidth = Math.max(1, Math.round(insetWidth * fitScale));
    insetHeight = Math.max(1, Math.round(insetHeight * fitScale));
  }
  const travelX = Math.max(0, frameRect.width - insetWidth);
  const travelY = Math.max(0, frameRect.height - insetHeight);
  const pipX = normalizedCoordinateValue(source.pip_x) ?? normalizedCoordinateValue(state.project.merge.pip_x) ?? 1;
  const pipY = normalizedCoordinateValue(source.pip_y) ?? normalizedCoordinateValue(state.project.merge.pip_y) ?? 1;
  return {
    left: frameRect.left + (travelX * pipX),
    top: frameRect.top + (travelY * pipY),
    width: insetWidth,
    height: insetHeight,
  };
}

function ensureMergePreviewItem(layer, source) {
  const asset = source.asset || source;
  const sourceId = sourceIdentifier(source, fileName(asset.path || ""));
  let item = layer.querySelector(`.merge-preview-item[data-source-id="${sourceId}"]`);
  if (!item) {
    item = document.createElement("div");
    item.className = "merge-preview-item";
    item.dataset.sourceId = sourceId;
    layer.appendChild(item);
  }
  item.dataset.sourceId = sourceId;
  item.dataset.mediaType = asset.is_still_image ? "image" : "video";
  let media = item.firstElementChild;
  const desiredTag = asset.is_still_image ? "IMG" : "VIDEO";
  if (!(media instanceof HTMLElement) || media.tagName !== desiredTag) {
    item.innerHTML = "";
    media = document.createElement(asset.is_still_image ? "img" : "video");
    if (media instanceof HTMLVideoElement) {
      media.muted = true;
      media.playsInline = true;
      media.disablePictureInPicture = true;
      media.preload = "auto";
      ["loadedmetadata", "loadeddata"].forEach((eventName) => {
        media.addEventListener(eventName, () => {
          scheduleSecondaryPreviewSync();
          renderLiveOverlay();
        });
      });
    }
    item.appendChild(media);
  }
  const mediaPath = `/media/merge/${sourceId}?v=${encodeURIComponent(asset.path || "")}`;
  if (media instanceof HTMLImageElement) {
    if (media.dataset.sourcePath !== asset.path) {
      media.dataset.sourcePath = asset.path;
      media.src = mediaPath;
    }
  } else if (media instanceof HTMLVideoElement && media.dataset.sourcePath !== asset.path) {
    media.dataset.sourcePath = asset.path;
    media.src = mediaPath;
    media.load();
  }
  return item;
}

function renderMergePreviewLayer(video, stage, mergeSources, pipSizeValue) {
  const layer = $("merge-preview-layer");
  if (!layer) return;
  const frameRect = previewFrameGeometry(video, stage)?.frameRect;
  if (!frameRect || mergeSources.length === 0) {
    layer.hidden = true;
    layer.innerHTML = "";
    return;
  }
  layer.hidden = false;
  const expectedIds = new Set(mergeSources.map((source, index) => sourceIdentifier(source, String(index))));
  layer.querySelectorAll(".merge-preview-item[data-source-id]").forEach((item) => {
    if (!expectedIds.has(item.dataset.sourceId)) item.remove();
  });
  mergeSources.forEach((source, index) => {
    const item = ensureMergePreviewItem(layer, source);
    const rect = mergeSourcePipRect(source, frameRect, pipSizeValue);
    item.style.left = `${rect.left}px`;
    item.style.top = `${rect.top}px`;
    item.style.width = `${rect.width}px`;
    item.style.height = `${rect.height}px`;
    item.style.maxWidth = `${rect.width}px`;
    item.style.maxHeight = `${rect.height}px`;
    item.title = `${index + 1}. ${fileName(source.asset?.path || "")}`;
  });
}

function syncMergePreviewElements(primary) {
  const previews = Array.from(document.querySelectorAll("#merge-preview-layer video"));
  if (previews.length === 0) return;
  const seekThreshold = primary.paused ? 0.01 : 0.05;
  const targetPlaybackRate = primary.playbackRate || 1;
  previews.forEach((preview) => {
    const sourceId = preview.closest(".merge-preview-item")?.dataset.sourceId || "";
    const target = mergePreviewTargetTime(primary.currentTime, mergeSourceById(sourceId));
    if (Math.abs((preview.playbackRate || 1) - targetPlaybackRate) > 0.001) {
      preview.playbackRate = targetPlaybackRate;
      preview.defaultPlaybackRate = targetPlaybackRate;
    }
    if (Number.isFinite(target) && Math.abs((preview.currentTime || 0) - target) > seekThreshold) {
      try {
        if (typeof preview.fastSeek === "function") preview.fastSeek(target);
        else preview.currentTime = target;
      } catch {
        // Ignore early metadata seek failures.
      }
    }
    if (primary.paused && !preview.paused) {
      preview.pause();
      return;
    }
    if (!primary.paused && preview.paused) {
      if (preview.readyState < HTMLMediaElement.HAVE_CURRENT_DATA) return;
      preview.play().catch((error) => {
        activity("video.merge_preview.error", {
          source_id: preview.closest(".merge-preview-item")?.dataset.sourceId || "",
          name: error?.name || "Error",
          error: error?.message || String(error || "Unknown error"),
        });
      });
    }
  });
}

function renderVideo() {
  const video = $("primary-video");
  const secondary = $("secondary-video");
  const secondaryImage = $("secondary-image");
  const mergePreviewLayer = $("merge-preview-layer");
  const stage = $("video-stage");
  const merge = state.project.merge;
  const mergeSources = state?.project?.merge_sources || [];
  const path = state.project.primary_video.path || "";
  if (state.media.primary_available && video.dataset.sourcePath !== path) {
    video.dataset.sourcePath = path;
    video.src = `/media/primary?v=${encodeURIComponent(path)}`;
    video.load();
  }
  if (!state.media.primary_available) {
    resetMediaElement(video);
  }

  const secondaryPath = state.project.secondary_video?.path || "";
  const imageSecondary = isImagePath(secondaryPath);
  if (state.media.secondary_available && imageSecondary) {
    if (secondaryImage.dataset.sourcePath !== secondaryPath) {
      secondaryImage.dataset.sourcePath = secondaryPath;
      secondaryImage.src = `/media/secondary?v=${encodeURIComponent(secondaryPath)}`;
    }
    resetMediaElement(secondary);
  } else if (state.media.secondary_available && !imageSecondary) {
    if (secondary.dataset.sourcePath !== secondaryPath) {
      secondary.dataset.sourcePath = secondaryPath;
      secondary.src = `/media/secondary?v=${encodeURIComponent(secondaryPath)}`;
      secondary.load();
    }
    secondaryImage.removeAttribute("src");
  } else {
    resetMediaElement(secondary);
    secondaryImage.removeAttribute("src");
    secondaryImage.hidden = true;
  }

  const mergePreview = Boolean(merge.enabled && mergeSources.length > 0);
  if (mergePreviewLayer) {
    mergePreviewLayer.hidden = true;
    if (merge.layout !== "pip") mergePreviewLayer.innerHTML = "";
  }
  stage.classList.toggle("merge-preview", mergePreview);
  stage.classList.toggle("merge-side-by-side", mergePreview && merge.layout === "side_by_side");
  stage.classList.toggle("merge-above-below", mergePreview && merge.layout === "above_below");
  stage.classList.toggle("merge-pip", mergePreview && merge.layout === "pip");

  const frameGeometry = mergePreview ? null : previewFrameGeometry(video, stage);
  const pipSizeValue = currentPipSizePercent();
  stage.style.setProperty("--pip-size", `${pipSizeValue}%`);
  if (frameGeometry) {
    const cropCenterX = normalizedCoordinateValue(state.project.export.crop_center_x) ?? 0.5;
    const cropCenterY = normalizedCoordinateValue(state.project.export.crop_center_y) ?? 0.5;
    video.hidden = false;
    video.style.position = "absolute";
    video.style.left = `${frameGeometry.frameRect.left}px`;
    video.style.top = `${frameGeometry.frameRect.top}px`;
    video.style.width = `${frameGeometry.frameRect.width}px`;
    video.style.height = `${frameGeometry.frameRect.height}px`;
    video.style.maxWidth = "none";
    video.style.maxHeight = "none";
    video.style.right = "";
    video.style.bottom = "";
    video.style.objectFit = "cover";
    video.style.objectPosition = `${cropCenterX * 100}% ${cropCenterY * 100}%`;
    video.style.zIndex = "0";
  } else {
    video.style.position = "";
    video.style.left = "";
    video.style.top = "";
    video.style.width = "";
    video.style.height = "";
    video.style.maxWidth = "";
    video.style.maxHeight = "";
    video.style.right = "";
    video.style.bottom = "";
    video.style.objectFit = "";
    video.style.objectPosition = "";
    video.style.zIndex = "";
  }
  [secondary, secondaryImage].forEach((element) => {
    element.style.left = "";
    element.style.top = "";
    element.style.right = "";
    element.style.bottom = "";
    element.style.width = "";
    element.style.height = "";
    element.style.maxWidth = "";
    element.style.maxHeight = "";
  });

  if (mergePreview && merge.layout === "pip" && mergeSources.length > 1) {
    renderMergePreviewLayer(video, stage, mergeSources, pipSizeValue);
    secondary.hidden = true;
    secondary.style.display = "none";
    secondaryImage.hidden = true;
    secondaryImage.style.display = "none";
  } else {
    const showSecondaryVideo = mergePreview && !imageSecondary;
    const showSecondaryImage = mergePreview && imageSecondary;
    secondary.hidden = !showSecondaryVideo;
    secondary.style.display = showSecondaryVideo ? "" : "none";
    secondaryImage.hidden = !showSecondaryImage;
    secondaryImage.style.display = showSecondaryImage ? "block" : "none";

    if (mergePreview) {
      const activeSecondary = imageSecondary ? secondaryImage : secondary;
      const frameRect = previewFrameGeometry(video, stage)?.frameRect;
      const secondaryWidth = Math.max(
        1,
        imageSecondary
          ? (secondaryImage.naturalWidth || state.project.secondary_video?.width || 1)
          : (secondary.videoWidth || state.project.secondary_video?.width || 1),
      );
      const secondaryHeight = Math.max(
        1,
        imageSecondary
          ? (secondaryImage.naturalHeight || state.project.secondary_video?.height || 1)
          : (secondary.videoHeight || state.project.secondary_video?.height || 1),
      );
      if (merge.layout === "pip" && frameRect) {
        const activeSource = mergeSources[0] || null;
        const rect = activeSource
          ? mergeSourcePipRect(activeSource, frameRect, pipSizeValue)
          : (() => {
              let insetWidth = Math.max(1, Math.round(frameRect.width * (pipSizeValue / 100)));
              let insetHeight = Math.max(1, Math.round((secondaryHeight / secondaryWidth) * insetWidth));
              if (insetHeight > frameRect.height) {
                const fitScale = frameRect.height / insetHeight;
                insetWidth = Math.max(1, Math.round(insetWidth * fitScale));
                insetHeight = Math.max(1, Math.round(insetHeight * fitScale));
              }
              const travelX = Math.max(0, frameRect.width - insetWidth);
              const travelY = Math.max(0, frameRect.height - insetHeight);
              return {
                left: frameRect.left + (travelX * (normalizedCoordinateValue(merge.pip_x) ?? 1)),
                top: frameRect.top + (travelY * (normalizedCoordinateValue(merge.pip_y) ?? 1)),
                width: insetWidth,
                height: insetHeight,
              };
            })();
        activeSecondary.style.left = `${rect.left}px`;
        activeSecondary.style.top = `${rect.top}px`;
        activeSecondary.style.width = `${rect.width}px`;
        activeSecondary.style.height = `${rect.height}px`;
        activeSecondary.style.maxWidth = `${rect.width}px`;
        activeSecondary.style.maxHeight = `${rect.height}px`;
      }
    }
  }

  const waveformEnabled = Boolean(state.project.analysis?.shots?.length);
  document.querySelectorAll(".waveform-actions button").forEach((button) => {
    if (button.id === "amp-waveform-out" || button.id === "amp-waveform-in") {
      button.disabled = !waveformEnabled || !selectedShotId;
    } else {
      button.disabled = !waveformEnabled;
    }
  });
  scheduleSecondaryPreviewSync();
}

function syncSecondaryPreview() {
  const primary = $("primary-video");
  const secondary = $("secondary-video");
  if (!primary || !secondary) return;
  const activeSource = (state.project.merge_sources || [])[0] || null;
  const classicSecondaryActive = Boolean(
    state?.media?.secondary_available
      && state.project.merge.enabled
      && secondary.src
      && (state.project.merge_sources || []).length <= 1,
  );
  if (!classicSecondaryActive) {
    clearSecondaryPreviewPlayError();
  } else {
    const target = mergePreviewTargetTime(primary.currentTime, activeSource);
    const seekThreshold = primary.paused ? 0.01 : 0.05;
    const targetPlaybackRate = primary.playbackRate || 1;
    if (Math.abs((secondary.playbackRate || 1) - targetPlaybackRate) > 0.001) {
      secondary.playbackRate = targetPlaybackRate;
      secondary.defaultPlaybackRate = targetPlaybackRate;
    }
    if (Number.isFinite(target) && Math.abs((secondary.currentTime || 0) - target) > seekThreshold) {
      try {
        if (typeof secondary.fastSeek === "function") secondary.fastSeek(target);
        else secondary.currentTime = target;
      } catch {
        // Some browsers reject seeks before metadata is ready.
      }
    }
    if (primary.paused && !secondary.paused) {
      secondary.pause();
      clearSecondaryPreviewPlayError();
    } else if (!primary.paused && secondary.paused) {
      if (secondary.readyState < HTMLMediaElement.HAVE_CURRENT_DATA || secondaryPreviewPlayErrorKey) {
        syncMergePreviewElements(primary);
        return;
      }
      try {
        const playPromise = secondary.play();
        if (playPromise && typeof playPromise.then === "function") {
          playPromise
            .then(() => {
              clearSecondaryPreviewPlayError();
            })
            .catch((error) => {
              reportSecondaryPreviewPlayError(error);
            });
        } else {
          clearSecondaryPreviewPlayError();
        }
      } catch (error) {
        reportSecondaryPreviewPlayError(error);
      }
    }
  }
  syncMergePreviewElements(primary);
}

function clearSecondaryPreviewPlayError() {
  secondaryPreviewPlayErrorKey = null;
}

function reportSecondaryPreviewPlayError(error) {
  if (error?.name === "AbortError") return;
  const errorName = error?.name || "Error";
  const errorMessage = error?.message || String(error || "Unknown error");
  const errorKey = `${errorName}:${errorMessage}`;
  if (secondaryPreviewPlayErrorKey === errorKey) return;
  secondaryPreviewPlayErrorKey = errorKey;
  const statusMessage = errorName === "NotAllowedError"
    ? "Secondary preview playback is blocked until the browser allows media playback."
    : `Secondary preview playback failed: ${errorMessage}`;
  setStatus(statusMessage);
  activity("video.secondary_play.error", { name: errorName, error: errorMessage });
}

function scheduleSecondaryPreviewSync() {
  if (secondaryPreviewSyncFrame !== null) return;
  secondaryPreviewSyncFrame = window.requestAnimationFrame(() => {
    secondaryPreviewSyncFrame = null;
    syncSecondaryPreview();
  });
}

function waveformCanvasDisplayHeight(canvas) {
  const panel = canvas.closest(".waveform-panel");
  if (!panel) return 0;
  const panelHeight = panel.clientHeight || panel.getBoundingClientRect().height || 0;
  if (!panelHeight) return 0;
  const headerHeight = panel.querySelector(".waveform-header")?.getBoundingClientRect().height || 0;
  const footerHeight = panel.querySelector(".waveform-footer")?.getBoundingClientRect().height || 0;
  const shotList = panel.querySelector(".waveform-shot-list");
  const shotListVisible = shotList && window.getComputedStyle(shotList).display !== "none";
  const shotListHeight = shotListVisible ? shotList.getBoundingClientRect().height : 0;
  return Math.max(1, Math.floor(panelHeight - headerHeight - footerHeight - shotListHeight));
}

function resizeCanvasToDisplay(canvas) {
  const rect = canvas.getBoundingClientRect();
  const parentRect = canvas.parentElement?.getBoundingClientRect();
  const width = Math.max(1, Math.floor(parentRect?.width || canvas.parentElement?.clientWidth || rect.width || canvas.clientWidth || 1600));
  const height = Math.max(1, Math.floor(waveformCanvasDisplayHeight(canvas) || rect.height || canvas.clientHeight || 260));
  const scale = Math.max(1, window.devicePixelRatio || 1);
  const targetWidth = Math.max(1, Math.round(width * scale));
  const targetHeight = Math.max(1, Math.round(height * scale));
  if (canvas.width !== targetWidth || canvas.height !== targetHeight) {
    canvas.width = targetWidth;
    canvas.height = targetHeight;
  }
  canvas.style.width = "100%";
  canvas.style.height = `${height}px`;
  const ctx = canvas.getContext("2d");
  ctx.setTransform(scale, 0, 0, scale, 0, 0);
  return { width, height };
}

function renderWaveform() {
  const canvas = $("waveform");
  const { width, height } = resizeCanvasToDisplay(canvas);
  const ctx = canvas.getContext("2d");
  const waveform = state.project.analysis.waveform_primary || [];
  const expanded = $("cockpit-root")?.classList.contains("waveform-expanded") ?? false;
  const visible = waveformWindow();
  ctx.clearRect(0, 0, width, height);
  ctx.fillStyle = "#102033";
  ctx.fillRect(0, 0, width, height);
  drawWaveformScale(ctx, visible, width, height);
  drawSelectedRegion(ctx, width, height);
  ctx.strokeStyle = "#3aa0ff";
  ctx.lineWidth = 1;
  ctx.beginPath();
  const startIndex = Math.max(0, Math.floor((visible.start / durationMs()) * waveform.length));
  const endIndex = Math.min(waveform.length - 1, Math.ceil((visible.end / durationMs()) * waveform.length));
  for (let index = startIndex; index <= endIndex; index += 1) {
    const value = waveform[index] || 0;
    const sampleTime = (index / Math.max(1, waveform.length - 1)) * durationMs();
    const x = waveformX(sampleTime, width);
    const amp = value * waveformAmplitudeForTime(sampleTime);
    const yTop = (height / 2) - (amp * height * 0.42);
    const yBottom = (height / 2) + (amp * height * 0.42);
    ctx.moveTo(x, yTop);
    ctx.lineTo(x, yBottom);
  }
  ctx.stroke();

  const beep = state.project.analysis.beep_time_ms_primary;
  if (beep !== null && beep !== undefined) drawMarker(ctx, beep, "#ff7b22", "BEEP", "rgba(226, 232, 240, 0.88)", width, height);
  state.project.analysis.shots.forEach((shot, index) => {
    const selected = shot.id === selectedShotId;
    const label = expanded ? `${index + 1} ${seconds(shot.time_ms)}` : "";
    const timeMs = shot.id === draggingShotId && pendingDragTimeMs !== null
      ? pendingDragTimeMs
      : shot.time_ms;
    drawMarker(
      ctx,
      timeMs,
      selected ? "#ffffff" : "#39d06f",
      label,
      selected ? "rgba(248, 250, 252, 0.98)" : "rgba(226, 232, 240, 0.88)",
      width,
      height,
    );
  });
  renderWaveformShotList();
}

function drawOutlinedText(ctx, text, x, y, fillStyle, font, lineWidth = 3) {
  ctx.save();
  ctx.font = font;
  ctx.textAlign = "left";
  ctx.textBaseline = "top";
  ctx.lineJoin = "round";
  ctx.miterLimit = 2;
  ctx.strokeStyle = "rgba(0, 0, 0, 0.88)";
  ctx.lineWidth = lineWidth;
  ctx.fillStyle = fillStyle;
  ctx.strokeText(text, x, y);
  ctx.fillText(text, x, y);
  ctx.restore();
}

function drawMarker(ctx, timeMs, color, label, labelColor = "rgba(248, 250, 252, 0.96)", width = null, height = null) {
  if (!isWaveformVisible(timeMs)) return;
  const x = waveformX(timeMs, width ?? ctx.canvas.width);
  ctx.strokeStyle = color;
  ctx.fillStyle = color;
  ctx.lineWidth = 3;
  ctx.beginPath();
  ctx.moveTo(x, 0);
  ctx.lineTo(x, height ?? ctx.canvas.height);
  ctx.stroke();
  if (label) {
    drawOutlinedText(
      ctx,
      label,
      x + 5,
      11,
      labelColor,
      "800 12px -apple-system, BlinkMacSystemFont, 'SF Pro Text', sans-serif",
    );
  }
}

function drawWaveformScale(ctx, visible, width, height) {
  const tickCount = Math.max(4, Math.min(12, Math.floor(width / 140)));
  ctx.strokeStyle = "rgba(255,255,255,0.14)";
  ctx.fillStyle = "rgba(244,245,246,0.82)";
  ctx.lineWidth = 1;
  ctx.font = "800 11px -apple-system, BlinkMacSystemFont, 'SF Pro Text', sans-serif";
  for (let index = 0; index <= tickCount; index += 1) {
    const x = (index / tickCount) * width;
    const timeMs = visible.start + ((index / tickCount) * visible.duration);
    ctx.beginPath();
    ctx.moveTo(x, 0);
    ctx.lineTo(x, height);
    ctx.stroke();
    drawOutlinedText(
      ctx,
      `${(timeMs / 1000).toFixed(3)}s`,
      x + 4,
      height - 17,
      "rgba(226, 232, 240, 0.88)",
      "800 11px -apple-system, BlinkMacSystemFont, 'SF Pro Text', sans-serif",
      3,
    );
  }
}

function drawSelectedRegion(ctx, width, height) {
  const shot = selectedShot();
  if (!shot) return;
  if (!isWaveformVisible(shot.time_ms)) return;
  const x = waveformX(shot.time_ms, width);
  ctx.fillStyle = "rgba(255, 123, 34, 0.18)";
  ctx.fillRect(Math.max(0, x - 44), 0, 88, height);
}

function selectShot(shotId) {
  selectedShotId = shotId;
  activity("shot.select", { shot_id: shotId });
  const shot = selectedShot();
  const primaryVideo = $("primary-video");
  if (shot && primaryVideo && state?.media?.primary_available) {
    try {
      primaryVideo.currentTime = shot.time_ms / 1000;
    } catch {
      // Some browsers reject seeks before metadata is ready.
    }
    scheduleSecondaryPreviewSync();
    renderLiveOverlay();
  }
  callApi("/api/shots/select", { shot_id: shotId });
}

function selectedShot() {
  return (state?.project?.analysis?.shots || []).find((shot) => shot.id === selectedShotId) || null;
}

function selectedShotRange() {
  const shots = state?.project?.analysis?.shots || [];
  const selectedIndex = shots.findIndex((shot) => shot.id === selectedShotId);
  if (selectedIndex < 0) return null;

  const shot = shots[selectedIndex];
  const previousTime = selectedIndex > 0 ? shots[selectedIndex - 1].time_ms : 0;
  const nextTime = selectedIndex < shots.length - 1 ? shots[selectedIndex + 1].time_ms : durationMs();

  return {
    shotId: shot.id,
    start: selectedIndex === 0 ? 0 : Math.max(0, Math.round((previousTime + shot.time_ms) / 2)),
    end: selectedIndex === shots.length - 1
      ? durationMs()
      : Math.min(durationMs(), Math.round((shot.time_ms + nextTime) / 2)),
  };
}

function waveformAmplitudeForTime(timeMs) {
  const range = selectedShotRange();
  if (!range || timeMs < range.start || timeMs > range.end) return 1;
  return waveformShotAmplitudeById[range.shotId] ?? 1;
}

function renderWaveformShotList() {
  const list = $("waveform-shot-list");
  if (!list) return;
  list.innerHTML = "";
  (state.timing_segments || []).forEach((segment) => {
    const item = document.createElement("button");
    item.type = "button";
    if (segment.shot_id === selectedShotId) item.classList.add("selected");
    if (isLowConfidence(segment.confidence)) {
      item.classList.add("low-confidence");
      item.title = `Review this split manually: confidence ${formatConfidenceValue(segment.confidence)}.`;
    }
    const title = document.createElement("strong");
    title.textContent = segment.card_title;
    const meta = document.createElement("small");
    meta.textContent = segment.card_meta;
    item.append(title, meta);
    item.addEventListener("click", () => selectShot(segment.shot_id));
    list.appendChild(item);
  });
}

function shotLabelForEvent(shotId) {
  const segment = (state.timing_segments || []).find((item) => item.shot_id === shotId);
  if (!segment) return "Any shot";
  return `${segment.label} ${segment.absolute_s}s`;
}

function deleteTimingEvent(eventId) {
  activity("timing.event.delete", { event_id: eventId });
  callApi("/api/events/delete", { event_id: eventId });
}

function renderTimingEventList() {
  const list = $("timing-event-list");
  if (!list) return;
  list.innerHTML = "";
  const events = state.project.analysis.events || [];
  if (events.length === 0) {
    const empty = document.createElement("div");
    empty.className = "hint";
    empty.textContent = "No timing events yet.";
    list.appendChild(empty);
    return;
  }

  events.forEach((event) => {
    const row = document.createElement("div");
    row.className = "timing-event-row";

    const label = document.createElement("strong");
    label.textContent = event.label || defaultTimingEventLabel(event.kind);

    const kind = document.createElement("span");
    kind.textContent = timingEventKindLabel(event.kind);

    const placement = document.createElement("span");
    placement.textContent = timingEventPlacementText(event);

    const remove = document.createElement("button");
    remove.type = "button";
    remove.textContent = "Remove";
    remove.setAttribute("aria-label", `Remove timing event ${event.label || defaultTimingEventLabel(event.kind)}`);
    remove.addEventListener("click", () => deleteTimingEvent(event.id));

    row.append(label, kind, placement, remove);
    list.appendChild(row);
  });
}

function renderTimingEventEditor() {
  const shotSegments = state.timing_segments || [];
  const positionSelect = $("timing-event-position");
  const addButton = $("add-timing-event");
  if (!positionSelect || !addButton) return;

  const previousPosition = positionSelect.value;
  const selectedIndex = selectedShotId
    ? shotSegments.findIndex((segment) => segment.shot_id === selectedShotId)
    : -1;

  positionSelect.innerHTML = "";
  shotSegments.forEach((segment, index) => {
    const beforeOption = document.createElement("option");
    beforeOption.value = `::${segment.shot_id}`;
    beforeOption.textContent = `Before ${segment.label}`;
    positionSelect.appendChild(beforeOption);

    const nextSegment = shotSegments[index + 1];
    const afterOption = document.createElement("option");
    afterOption.value = `${segment.shot_id}::${nextSegment?.shot_id || ""}`;
    afterOption.textContent = nextSegment
      ? `Between ${segment.label} and ${nextSegment.label}`
      : `After ${segment.label}`;
    positionSelect.appendChild(afterOption);
  });

  if (previousPosition && Array.from(positionSelect.options).some((option) => option.value === previousPosition)) {
    positionSelect.value = previousPosition;
  } else if (selectedIndex >= 0) {
    positionSelect.value = `${shotSegments[selectedIndex].shot_id}::${shotSegments[selectedIndex + 1]?.shot_id || ""}`;
  }

  addButton.disabled = shotSegments.length === 0;
  renderTimingEventList();
}

function addTimingEvent() {
  const kind = $("timing-event-kind").value;
  const labelValue = $("timing-event-label").value.trim();
  const [afterShotId = "", beforeShotId = ""] = String($("timing-event-position").value || "::").split("::");
  const label = labelValue || defaultTimingEventLabel(kind);
  activity("timing.event.add", { kind, label, after_shot_id: afterShotId, before_shot_id: beforeShotId });
  callApi("/api/events/add", {
    kind,
    label,
    after_shot_id: afterShotId,
    before_shot_id: beforeShotId,
  });
}

function formatTimingValue(value) {
  return value === null || value === undefined ? "--" : String(value);
}

function toggleTimingRowEdit(shotId) {
  if (timingRowEdits.has(shotId)) {
    timingRowEdits.delete(shotId);
  } else {
    timingRowEdits.add(shotId);
  }
  renderTimingTables();
}

function restoreOriginalSplit(shotId) {
  selectedShotId = shotId;
  callApi("/api/shots/restore", { shot_id: shotId });
}

function restoreOriginalScore(shotId) {
  selectedShotId = shotId;
  callApi("/api/scoring/restore", { shot_id: shotId });
}

function updateTimingRowField(shotId, field, value) {
  if (field === "split_ms") {
    const rows = state.split_rows || [];
    const rowIndex = rows.findIndex((row) => row.shot_id === shotId);
    if (rowIndex < 0) return;
    const splitMs = Math.max(0, Math.round((Number(value) || 0) * 1000));
    const baseTimeMs = rowIndex === 0
      ? Math.max(0, Number(state?.project?.analysis?.beep_time_ms_primary ?? 0))
      : Number(rows[rowIndex - 1]?.absolute_time_ms || 0);
    callApi("/api/shots/move", { shot_id: shotId, time_ms: baseTimeMs + splitMs });
    return;
  }
}

function renderTimingTable(tableId = "timing-table") {
  const table = $(tableId);
  if (!table) return;
  table.innerHTML = "";
  const expandedTable = tableId === "timing-workbench-table";
  const headers = expandedTable
    ? ["", "Shot", "Split", "Score", "Confidence", "Source"]
    : ["Shot", "Split", "Score", "Confidence", "Source"];
  headers.forEach((header) => {
    const cell = document.createElement("div");
    cell.className = "head";
    cell.textContent = header;
    table.appendChild(cell);
  });

  (state.split_rows || []).forEach((row) => {
    const editing = expandedTable && timingRowEdits.has(row.shot_id);
    const lowConfidence = isLowConfidence(row.confidence);
    if (expandedTable) {
      const lockCell = document.createElement("div");
      lockCell.className = "lock-cell";
      const lockButton = document.createElement("button");
      lockButton.type = "button";
      lockButton.className = `lock-button ${editing ? "unlocked" : "locked"}`;
      lockButton.textContent = editing ? "Lock" : "Unlock";
      lockButton.title = editing ? "Lock row" : "Unlock row";
      lockButton.addEventListener("click", () => toggleTimingRowEdit(row.shot_id));
      lockCell.appendChild(lockButton);
      table.appendChild(lockCell);
    }

    const shotCell = document.createElement("div");
    shotCell.textContent = String(row.shot_number);
  if (row.shot_id === selectedShotId) shotCell.classList.add("selected");
  if (lowConfidence) shotCell.classList.add("low-confidence");
    shotCell.addEventListener("click", () => selectShot(row.shot_id));
    table.appendChild(shotCell);

    const splitCell = document.createElement("div");
    const splitMs = resolvedSplitMsForShot(row.shot_id, row.shot_number, row.absolute_time_ms);
    if (editing) {
      const editor = document.createElement("span");
      editor.className = "timing-edit-control";
      const input = document.createElement("input");
      input.type = "number";
      input.min = "0";
      input.step = "0.001";
      input.className = "timing-split-input";
      input.value = precise(splitMs ?? row.absolute_time_ms);
      input.setAttribute("aria-label", `Split for shot ${row.shot_number}`);
      input.addEventListener("change", () => updateTimingRowField(row.shot_id, "split_ms", input.value));
      const restore = document.createElement("button");
      restore.type = "button";
      restore.className = "restore-button";
      restore.textContent = "Restore";
      restore.title = "Restore this split to its original timing.";
      restore.addEventListener("click", () => restoreOriginalSplit(row.shot_id));
      editor.append(input, restore);
      splitCell.appendChild(editor);
    } else {
      splitCell.textContent = splitSeconds(splitMs);
    }
    table.appendChild(splitCell);

    const scoreCell = document.createElement("div");
    if (lowConfidence) scoreCell.classList.add("low-confidence");
    scoreCell.textContent = row.score_letter || "--";
    scoreCell.addEventListener("click", () => selectShot(row.shot_id));
    table.appendChild(scoreCell);

    const confidenceCell = document.createElement("div");
    confidenceCell.textContent = row.confidence === null || row.confidence === undefined
      ? "Manual"
      : formatConfidenceValue(row.confidence);
    if (lowConfidence) {
      confidenceCell.classList.add("low-confidence");
      confidenceCell.title = `Review this split manually: confidence ${formatConfidenceValue(row.confidence)}.`;
    }
    table.appendChild(confidenceCell);

    const sourceCell = document.createElement("div");
    const sourceValue = typeof row.source === "string" ? row.source.toLowerCase() : "";
    sourceCell.textContent = sourceValue === "auto" ? "ShotML" : sourceValue === "manual" ? "Manual" : row.source || "ShotML";
    table.appendChild(sourceCell);
  });
}

function renderTimingTables() {
  renderTimingTable("timing-table");
  renderTimingTable("timing-workbench-table");
  renderTimingEventEditor();
}

function renderSelection() {
  selectedShotId = state.project.ui_state.selected_shot_id || selectedShotId;
  const segment = (state.timing_segments || []).find((item) => item.shot_id === selectedShotId);
  const selectedLabel = segment ? `Shot ${segment.shot_number}` : "No shot selected";
  const selectedSplitMs = segment ? resolvedSplitMsForShot(segment.shot_id, segment.shot_number, segment.absolute_ms) : null;
  $("selected-shot-copy").textContent = segment
    ? `${selectedLabel}: ${seconds(selectedSplitMs)}s split, ${segment.cumulative_s || "--.--"}s from beep.`
    : "No shot selected.";
  $("selected-timing-shot").textContent = selectedLabel;
}

function renderScoreOptions(summary) {
  const options = summary.score_options || ["A", "C", "D", "M", "NS", "M+NS"];
  const grid = $("score-option-grid");
  if (!grid) return;
  grid.innerHTML = "";
  options.forEach((letter) => {
    const value = summary.score_values?.[letter] ?? 0;
    const penalty = summary.score_penalties?.[letter] ?? 0;
    const item = document.createElement("span");
    const description = {
      A: "A-zone / full points",
      C: "C-zone hit",
      D: "D-zone hit",
      M: "Miss",
      NS: "No-shoot",
      "M+NS": "Miss and no-shoot",
      "-0": "Down-zero",
      "-1": "Down-one",
      "-3": "Down-three",
      HIT: "Steel hit",
      STOP: "Stop plate failure",
      "0": "GPA zero-down",
      "+1": "GPA plus-one",
      "+3": "GPA plus-three",
      "+10": "GPA plus-ten",
    }[letter] || letter;
    item.textContent = penalty ? `${letter} ${description} • ${value} / -${penalty}` : `${letter} ${description} • ${value}`;
    item.title = description;
    grid.appendChild(item);
  });
}

function renderScoringShotList() {
  const list = $("scoring-shot-list");
  if (!list) return;
  list.innerHTML = "";
  const scoreOptions = state.scoring_summary?.score_options || ["A", "C", "D", "M", "NS", "M+NS"];
  const penaltyFields = state.scoring_summary?.penalty_fields || [];
  const activeShotId = selectedShotId || state.project.ui_state.selected_shot_id || state.timing_segments?.[0]?.shot_id || null;
  (state.timing_segments || []).forEach((segment) => {
    const row = document.createElement("div");
    row.className = `scoring-shot-row ${segment.shot_id === activeShotId ? "selected" : ""}`;
    if (isLowConfidence(segment.confidence)) row.classList.add("low-confidence");

    const button = document.createElement("button");
    button.type = "button";
    button.className = "scoring-shot-button";
    const title = document.createElement("strong");
    title.textContent = `Shot ${segment.shot_number}`;
    button.append(title);
    button.title = segment.source === "manual"
      ? "Manual shot marker."
      : isLowConfidence(segment.confidence)
        ? `Low-confidence ShotML marker (${formatConfidenceValue(segment.confidence)}).`
        : "ShotML-detected shot.";
    button.addEventListener("click", () => selectShot(segment.shot_id));

    const controls = document.createElement("div");
    controls.className = "scoring-shot-controls";

    const select = document.createElement("select");
    select.className = "shot-score-select";
    select.setAttribute("aria-label", `Score shot ${segment.shot_number}`);
    const unsetOption = document.createElement("option");
    unsetOption.value = "";
    unsetOption.textContent = "--";
    select.appendChild(unsetOption);
    scoreOptions.forEach((letter) => {
      const option = document.createElement("option");
      option.value = letter;
      const value = state.scoring_summary?.score_values?.[letter] ?? 0;
      const penalty = state.scoring_summary?.score_penalties?.[letter] ?? 0;
      option.textContent = penalty ? `${letter} (${value}, -${penalty})` : `${letter} (${value})`;
      select.appendChild(option);
    });
    select.value = segment.score_letter || "";

    const applyShotScoring = () => {
      selectedShotId = segment.shot_id;
      callApi("/api/scoring/score", {
        shot_id: segment.shot_id,
        letter: select.value || null,
        penalty_counts: collectPenaltyCounts(controls),
      });
    };
    select.addEventListener("change", applyShotScoring);

    const scoreField = document.createElement("div");
    scoreField.className = "shot-score-field";
    scoreField.appendChild(select);
    controls.appendChild(scoreField);

    if (penaltyFields.length > 0) {
      const penaltyGrid = document.createElement("div");
      penaltyGrid.className = "shot-penalty-fields";
      penaltyFields.forEach((field) => {
        const label = document.createElement("label");
        label.className = "shot-penalty-field";
        label.title = [field.label, field.description].filter(Boolean).join(" - ");
        const text = document.createElement("span");
        text.textContent = penaltyFieldLabel(field.id, field.label);
        const input = document.createElement("input");
        input.type = "number";
        input.min = "0";
        input.step = "1";
        input.value = segment.penalty_counts?.[field.id] ?? 0;
        input.dataset.penaltyId = field.id;
        input.className = "shot-penalty-input";
        input.setAttribute("aria-label", `${field.label} for shot ${segment.shot_number}`);
        input.title = label.title;
        input.addEventListener("change", applyShotScoring);
        label.append(text, input);
        penaltyGrid.appendChild(label);
      });
      controls.appendChild(penaltyGrid);
    }

    const restore = document.createElement("button");
    restore.type = "button";
    restore.className = "restore-button";
    restore.textContent = "Restore";
    restore.title = "Restore this shot score and penalties to their original values.";
    restore.addEventListener("click", () => restoreOriginalScore(segment.shot_id));
    controls.appendChild(restore);

    row.append(button, controls);
    list.appendChild(row);
  });
}

function renderScoringPenaltyFields(summary) {
  const grid = $("scoring-penalty-grid");
  if (!grid) return;
  grid.innerHTML = "";
}

function renderScoringPresetOptions() {
  const select = $("scoring-preset");
  const selected = state.project.scoring.ruleset;
  const presets = state.scoring_presets || [];
  const previousLength = select.options.length;
  select.innerHTML = "";
  presets.forEach((preset) => {
    const option = document.createElement("option");
    option.value = preset.id;
    option.textContent = preset.name;
    select.appendChild(option);
  });
  const hasSelected = presets.some((item) => item.id === selected);
  select.value = hasSelected ? selected : (select.options[0]?.value || "");
  const preset = presets.find((item) => item.id === select.value);
  const summary = state.scoring_summary;
  $("scoring-description").textContent = preset ? `${preset.sport}: ${preset.description}` : "Choose a scoring preset.";
  $("scoring-result").textContent = `${summary.display_label}: ${summary.display_value}`;
  renderScoreOptions(summary);
  renderScoringPenaltyFields(summary);
  renderScoringShotList();
  if (previousLength === 0) select.addEventListener("change", renderScoringPresetDescription);
}

function renderScoringPresetDescription() {
  const selected = $("scoring-preset").value;
  const preset = (state.scoring_presets || []).find((item) => item.id === selected);
  $("scoring-description").textContent = preset ? `${preset.sport}: ${preset.description}` : "";
}

function renderPractiScoreSummaries() {
  const imported = state.scoring_summary?.imported_stage;
  if (!imported) {
    $("practiscore-status").textContent = "No results imported";
    $("scoring-imported-caption").textContent = "No PractiScore stage imported.";
    renderDetailsList("practiscore-import-summary", []);
    renderDetailsList("scoring-imported-summary", []);
    return;
  }
  const stageLabel = imported.stage_name
    ? `Stage ${imported.stage_number}: ${imported.stage_name}`
    : `Stage ${imported.stage_number}`;
  const divisionLabel = [imported.division, imported.classification, imported.power_factor]
    .filter(Boolean)
    .join(" / ");
  const countsLabel = formatImportedCounts(imported.score_counts);
  const resultLabel = state.scoring_summary?.display_label || "Result";
  $("practiscore-status").textContent = `${formatMatchType(imported.match_type)} Stage ${imported.stage_number} imported`;
  $("scoring-imported-caption").textContent = `Imported ${formatMatchType(imported.match_type)} data for ${imported.competitor_name}.`;
  renderDetailsList("practiscore-import-summary", [
    ["Source", imported.source_name || "Selected file"],
    ["Match", formatMatchType(imported.match_type)],
    ["Stage", stageLabel],
    ["Competitor", imported.competitor_name],
    ["Place", imported.competitor_place ? `#${imported.competitor_place}` : ""],
    ["Division", divisionLabel],
    ["Raw Time", imported.raw_seconds !== null && imported.raw_seconds !== undefined ? `${formatNumber(imported.raw_seconds, 2)}s` : ""],
    [resultLabel, state.scoring_summary?.display_value || ""],
  ]);
  renderDetailsList("scoring-imported-summary", [
    ["Source", imported.source_name || "Selected file"],
    ["Stage", stageLabel],
    ["Competitor", imported.competitor_name],
    ["Counts", countsLabel],
    ["Official Points", imported.total_points !== null && imported.total_points !== undefined ? formatNumber(imported.total_points, 4) : ""],
    ["Stage Points", imported.stage_points !== null && imported.stage_points !== undefined ? formatNumber(imported.stage_points, 4) : ""],
    ["Stage Place", imported.stage_place ? `#${imported.stage_place}` : ""],
  ]);
}

function renderExportPresetOptions() {
  const select = $("export-preset");
  const selected = state.project.export.preset;
  select.innerHTML = "";
  (state.export_presets || []).forEach((preset) => {
    const option = document.createElement("option");
    option.value = preset.id;
    option.textContent = preset.name;
    select.appendChild(option);
  });
  const custom = document.createElement("option");
  custom.value = "custom";
  custom.textContent = "Custom";
  select.appendChild(custom);
  const hasSelected = Array.from(select.options).some((option) => option.value === selected);
  select.value = hasSelected ? selected : "custom";
  const preset = (state.export_presets || []).find((item) => item.id === select.value);
  $("export-preset-description").textContent = preset ? preset.description : "Manual custom export settings.";
}

function renderExportLog() {
  const log = state.project.export.last_error
    ? `ERROR: ${state.project.export.last_error}\n${state.project.export.last_log || ""}`
    : state.project.export.last_log;
  $("export-log").textContent = log || "No export log yet.";
}

function syncExportPathControl() {
  const input = $("export-path");
  if (!input) return;
  const savedPath = state.project.export.output_path || "";
  const defaultPath = `${state.default_project_path || "~/splitshot"}/output.mp4`;
  const draftPath = exportPathDraft.trim();
  const hasUnsavedDraft = draftPath && draftPath !== savedPath;
  const nextValue = hasUnsavedDraft ? exportPathDraft : savedPath || draftPath || input.value || defaultPath;
  if (input.value !== nextValue) input.value = nextValue;
  if (!draftPath) exportPathDraft = nextValue;
}

function renderControls() {
  syncControlValue($("threshold"), state.project.analysis.detection_threshold);
  const mergeSources = state.project.merge_sources || [];
  $("sync-offset").textContent = mergeSources.length === 0
    ? "Defaults only"
    : mergeSources.length === 1
      ? formatSyncOffsetLabel(currentSourceSyncOffsetMs(mergeSources[0]))
      : "Per-source sync";
  syncControlValue($("project-name"), state.project.name || "Untitled Project");
  syncControlValue($("project-description"), state.project.description || "");
  syncControlValue($("match-type"), state.project.scoring.match_type || "");
  syncControlValue($("match-stage-number"), state.project.scoring.stage_number ?? "");
  syncControlValue($("match-competitor-name"), state.project.scoring.competitor_name || "");
  syncControlValue($("match-competitor-place"), state.project.scoring.competitor_place ?? "");
  syncControlChecked($("merge-enabled"), state.project.merge.enabled);
  syncControlValue($("merge-layout"), state.project.merge.layout);
  const pipValue = Number(
    state.project.merge.pip_size_percent
      ?? Number(String(state.project.merge.pip_size || "35%").replace(/%$/, ""))
      ?? 35,
  );
  syncControlValue($("pip-size"), pipValue);
  $("pip-size-label").textContent = `${pipValue}%`;
  syncControlValue($("pip-x"), state.project.merge.pip_x ?? 1);
  syncControlValue($("pip-y"), state.project.merge.pip_y ?? 1);
  syncControlValue($("badge-size"), state.project.overlay.badge_size);
  overlayStyleMode = state.project.overlay.style_type || overlayStyleMode;
  overlaySpacing = Number(state.project.overlay.spacing ?? overlaySpacing);
  overlayMargin = Number(state.project.overlay.margin ?? overlayMargin);
  syncControlValue($("overlay-style"), overlayStyleMode);
  syncControlValue($("overlay-spacing"), overlaySpacing);
  syncControlValue($("overlay-margin"), overlayMargin);
  syncControlValue($("max-visible-shots"), state.project.overlay.max_visible_shots);
  syncControlValue($("shot-quadrant"), state.project.overlay.shot_quadrant);
  syncControlValue($("shot-direction"), state.project.overlay.shot_direction);
  syncControlValue($("overlay-custom-x"), state.project.overlay.custom_x ?? "");
  syncControlValue($("overlay-custom-y"), state.project.overlay.custom_y ?? "");
  syncControlValue($("timer-x"), state.project.overlay.timer_x ?? "");
  syncControlValue($("timer-y"), state.project.overlay.timer_y ?? "");
  syncControlValue($("draw-x"), state.project.overlay.draw_x ?? "");
  syncControlValue($("draw-y"), state.project.overlay.draw_y ?? "");
  syncControlValue($("score-x"), state.project.overlay.score_x ?? "");
  syncControlValue($("score-y"), state.project.overlay.score_y ?? "");
  syncControlValue($("bubble-width"), state.project.overlay.bubble_width);
  syncControlValue($("bubble-height"), state.project.overlay.bubble_height);
  syncControlValue($("overlay-font-family"), state.project.overlay.font_family);
  syncControlValue($("overlay-font-size"), state.project.overlay.font_size);
  syncControlChecked($("overlay-font-bold"), state.project.overlay.font_bold);
  syncControlChecked($("overlay-font-italic"), state.project.overlay.font_italic);
  syncControlChecked($("show-timer"), state.project.overlay.show_timer);
  syncControlChecked($("show-draw"), state.project.overlay.show_draw);
  syncControlChecked($("show-shots"), state.project.overlay.show_shots);
  syncControlChecked($("show-score"), state.project.overlay.show_score);
  syncControlChecked($("custom-box-enabled"), state.project.overlay.custom_box_enabled);
  syncControlValue($("custom-box-mode"), state.project.overlay.custom_box_mode || "manual");
  syncControlValue($("custom-box-text"), state.project.overlay.custom_box_text || "");
  syncControlValue($("custom-box-quadrant"), state.project.overlay.custom_box_quadrant);
  syncControlValue($("custom-box-x"), state.project.overlay.custom_box_x ?? "");
  syncControlValue($("custom-box-y"), state.project.overlay.custom_box_y ?? "");
  syncControlValue($("custom-box-width"), state.project.overlay.custom_box_width || 0);
  syncControlValue($("custom-box-height"), state.project.overlay.custom_box_height || 0);
  syncControlValue($("custom-box-opacity"), state.project.overlay.custom_box_opacity ?? 0.9);
  syncControlValue($("custom-box-background-color"), state.project.overlay.custom_box_background_color || "#000000");
  syncControlValue($("custom-box-text-color"), state.project.overlay.custom_box_text_color || "#ffffff");
  syncOverlayCoordinateControlState();
  syncCustomBoxModeState();
  syncTimingEventLabelState();
  syncControlChecked($("scoring-enabled"), state.project.scoring.enabled);
  syncControlValue($("quality"), state.project.export.quality);
  syncControlValue($("aspect-ratio"), state.project.export.aspect_ratio);
  syncControlValue($("target-width"), state.project.export.target_width ?? "");
  syncControlValue($("target-height"), state.project.export.target_height ?? "");
  syncControlValue($("frame-rate"), state.project.export.frame_rate);
  syncControlValue($("video-codec"), state.project.export.video_codec);
  syncControlValue($("video-bitrate"), state.project.export.video_bitrate_mbps);
  syncControlValue($("audio-codec"), state.project.export.audio_codec);
  syncControlValue($("audio-sample-rate"), state.project.export.audio_sample_rate);
  syncControlValue($("audio-bitrate"), state.project.export.audio_bitrate_kbps);
  syncControlValue($("color-space"), state.project.export.color_space);
  syncControlChecked($("two-pass"), state.project.export.two_pass);
  syncControlValue($("ffmpeg-preset"), state.project.export.ffmpeg_preset);
  syncExportPathControl();
  renderScoringPresetOptions();
  renderPractiScoreSummaries();
  renderExportPresetOptions();
  renderExportLog();
  renderStyleControls();
  renderMergeMediaList();
}

function renderStyleControls() {
  const grid = $("badge-style-grid");
  const badgeKeys = new Set(badgeControls.map(([key]) => key));
  grid.querySelectorAll(".style-card[data-badge]").forEach((card) => {
    const badgeName = card.dataset.badge;
    if (!badgeKeys.has(badgeName)) card.remove();
  });
  badgeControls.forEach(([key, title]) => {
    const style = state.project.overlay[key];
    let card = grid.querySelector(`.style-card[data-badge="${key}"]`);
    if (!card) {
      card = document.createElement("section");
      card.className = "style-card";
      card.dataset.badge = key;
      card.innerHTML = `
        <h4></h4>
        <label class="color-field"><span class="style-card-label">Background</span>
          <span class="color-control-pair">
            <input type="color" data-field="background_color" />
            <input type="text" class="color-hex-input" inputmode="text" spellcheck="false" aria-label="Background hex value" placeholder="#111827" />
          </span>
        </label>
        <label class="color-field"><span class="style-card-label">Text</span>
          <span class="color-control-pair">
            <input type="color" data-field="text_color" />
            <input type="text" class="color-hex-input" inputmode="text" spellcheck="false" aria-label="Text hex value" placeholder="#F9FAFB" />
          </span>
        </label>
        <label><span class="style-card-label">Opacity</span> <input type="range" data-field="opacity" min="0" max="1" step="0.05" /></label>
      `;
      bindOverlayColorInput(card.querySelector('[data-field="background_color"]'));
      bindOverlayColorInput(card.querySelector('[data-field="text_color"]'));
      grid.appendChild(card);
    }
    const heading = card.querySelector("h4");
    if (heading && heading.textContent !== title) heading.textContent = title;
    syncControlValue(card.querySelector('[data-field="background_color"]'), style.background_color);
    syncControlValue(card.querySelector('[data-field="text_color"]'), style.text_color);
    syncControlValue(card.querySelector('[data-field="opacity"]'), style.opacity);
  });

  const scoreGrid = $("score-color-grid");
  const scoreKeys = state.scoring_summary?.score_options || [];
  const uniqueLetters = [...new Set(scoreKeys)];
  const validLetters = new Set(uniqueLetters);
  scoreGrid.querySelectorAll(".score-color-input[data-letter]").forEach((input) => {
    if (!validLetters.has(input.dataset.letter)) {
      input.closest("label")?.remove();
    }
  });
  uniqueLetters.forEach((letter) => {
    let input = scoreGrid.querySelector(`.score-color-input[data-letter="${letter}"]`);
    if (!input) {
      const label = document.createElement("label");
      label.className = "color-field score-color-field";
      const text = document.createElement("span");
      text.textContent = letter;
      label.appendChild(text);
      const pair = document.createElement("span");
      pair.className = "color-control-pair";
      input = document.createElement("input");
      input.type = "color";
      input.className = "score-color-input";
      input.dataset.letter = letter;
      const hex = document.createElement("input");
      hex.type = "text";
      hex.className = "color-hex-input";
      hex.inputMode = "text";
      hex.spellcheck = false;
      hex.placeholder = "#FFFFFF";
      pair.append(input, hex);
      label.appendChild(pair);
      scoreGrid.appendChild(label);
      bindOverlayColorInput(input);
    }
    syncControlValue(input, state.project.overlay.scoring_colors[letter] || "#ffffff");
  });
}

function renderMergeMediaList() {
  const list = $("merge-media-list");
  if (!list) return;
  const mergeSources = state?.project?.merge_sources || [];
  list.innerHTML = "";
  if (mergeSources.length === 0) {
    const empty = document.createElement("div");
    empty.className = "hint";
    empty.textContent = "No PiP media added yet.";
    list.appendChild(empty);
    return;
  }

  mergeSources.forEach((source, index) => {
    const asset = source.asset || source;
    const sourceId = sourceIdentifier(source, String(index));
    const card = document.createElement("div");
    card.className = "merge-media-card";

    const header = document.createElement("div");
    header.className = "merge-media-card-header";
    const title = document.createElement("strong");
    title.textContent = `${index + 1}. ${fileName(asset.path || "")}`;

    const remove = document.createElement("button");
    remove.type = "button";
    remove.textContent = "Remove";
    remove.dataset.mergeSourceRemove = sourceId;
    remove.addEventListener("click", () => {
      activity("merge.media.remove", { source_id: remove.dataset.mergeSourceRemove });
      callApi("/api/merge/remove", { source_id: remove.dataset.mergeSourceRemove });
    });

    header.append(title, remove);

    const meta = document.createElement("small");
    meta.className = "merge-media-card-meta";
    const mediaType = asset.is_still_image ? "Image" : "Video";
    const dimensions = asset.width && asset.height ? ` • ${asset.width}x${asset.height}` : "";
    meta.textContent = `${mediaType}${dimensions}`;

    const controls = document.createElement("div");
    controls.className = "merge-source-controls";
    const syncRow = document.createElement("div");
    syncRow.className = "merge-source-sync-row";

    const updateSource = () => {
      const nextSize = clampNumber(Number(controls.querySelector('[data-merge-source-field="size"]')?.value) || 35, 10, 95);
      const nextX = normalizedCoordinateValue(controls.querySelector('[data-merge-source-field="x"]')?.value) ?? 1;
      const nextY = normalizedCoordinateValue(controls.querySelector('[data-merge-source-field="y"]')?.value) ?? 1;
      updateLocalMergeSourcePosition(sourceId, nextX, nextY, nextSize);
      renderVideo();
      callApi("/api/merge/source", {
        source_id: sourceId,
        pip_size_percent: nextSize,
        pip_x: nextX,
        pip_y: nextY,
      });
    };

    const buildSourceNumberInput = (labelText, field, value, min, max, step, titleText) => {
      const label = document.createElement("label");
      label.className = "merge-source-field";
      const text = document.createElement("span");
      text.textContent = labelText;
      const input = document.createElement("input");
      input.type = "number";
      input.min = String(min);
      input.max = String(max);
      input.step = String(step);
      input.value = value;
      input.dataset.mergeSourceField = field;
      input.dataset.sourceId = sourceId;
      input.title = titleText;
      input.addEventListener("input", updateSource);
      label.append(text, input);
      return label;
    };

    const sizeField = document.createElement("label");
    sizeField.className = "merge-source-field merge-source-size-field";
    const sizeText = document.createElement("span");
    sizeText.textContent = "PiP size";
    const sizeControl = document.createElement("span");
    sizeControl.className = "pip-size-control";
    const sizeInput = document.createElement("input");
    sizeInput.type = "range";
    sizeInput.min = "10";
    sizeInput.max = "95";
    sizeInput.step = "1";
    sizeInput.value = String(currentPipSizePercent(source, currentPipSizePercent()));
    sizeInput.dataset.mergeSourceField = "size";
    sizeInput.dataset.sourceId = sourceId;
    sizeInput.title = "10 is smallest, 95 is largest.";
    sizeInput.addEventListener("input", () => {
      const output = sizeField.querySelector('[data-merge-source-output="size"]');
      if (output) output.textContent = `${sizeInput.value}%`;
      updateSource();
    });
    const sizeOutput = document.createElement("output");
    sizeOutput.dataset.mergeSourceOutput = "size";
    sizeOutput.dataset.sourceId = sourceId;
    sizeOutput.textContent = `${sizeInput.value}%`;
    sizeControl.append(sizeInput, sizeOutput);
    sizeField.append(sizeText, sizeControl);

    const syncLabel = document.createElement("small");
    syncLabel.className = "merge-source-sync-label";
    syncLabel.dataset.mergeSourceSyncLabel = "true";
    syncLabel.dataset.sourceId = sourceId;
    syncLabel.textContent = formatSyncOffsetLabel(currentSourceSyncOffsetMs(source));

    const syncButtons = document.createElement("div");
    syncButtons.className = "button-grid compact merge-source-sync-buttons";
    [-10, -1, 1, 10].forEach((deltaMs) => {
      const button = document.createElement("button");
      button.type = "button";
      button.textContent = `${deltaMs > 0 ? "+" : ""}${deltaMs} ms`;
      button.title = `Nudge this PiP item ${deltaMs > 0 ? "later" : "earlier"} by ${Math.abs(deltaMs)} ms.`;
      button.addEventListener("click", () => {
        const nextOffset = currentSourceSyncOffsetMs(mergeSourceById(sourceId)) + deltaMs;
        updateLocalMergeSourceSyncOffset(sourceId, nextOffset);
        renderVideo();
        callApi("/api/merge/source", { source_id: sourceId, sync_delta_ms: deltaMs });
      });
      syncButtons.appendChild(button);
    });

    controls.append(
      sizeField,
      buildSourceNumberInput("PiP X", "x", normalizedCoordinateValue(source.pip_x) ?? 1, 0, 1, 0.01, "0 is left, 1 is right."),
      buildSourceNumberInput("PiP Y", "y", normalizedCoordinateValue(source.pip_y) ?? 1, 0, 1, 0.01, "0 is top, 1 is bottom."),
    );

    const syncHint = document.createElement("small");
    syncHint.className = "merge-source-sync-hint";
    syncHint.textContent = state.project.merge.layout === "pip"
      ? "Use these nudges or drag the preview to match the primary video exactly."
      : "These values are saved per item and take effect in PiP layout and export timing.";
    syncRow.append(syncLabel, syncButtons, syncHint);

    card.append(header, meta, controls, syncRow);
    syncMergeSourceControls(sourceId, normalizedCoordinateValue(source.pip_x), normalizedCoordinateValue(source.pip_y), currentPipSizePercent(source), currentSourceSyncOffsetMs(source));
    list.appendChild(card);
  });
}

function visibleTimingEventsByShot(currentIndex) {
  const shots = orderedShotsByTime();
  const shotIndexById = new Map(shots.map((shot, index) => [shot.id, index]));
  const beforeByShotId = new Map();
  const afterByShotId = new Map();
  (state?.project?.analysis?.events || []).forEach((event) => {
    const eventLabel = event.label || defaultTimingEventLabel(event.kind);
    const eventPayload = { ...event, label: eventLabel };
    const beforeIndex = event.before_shot_id ? shotIndexById.get(event.before_shot_id) : undefined;
    const afterIndex = event.after_shot_id ? shotIndexById.get(event.after_shot_id) : undefined;
    if (beforeIndex !== undefined && beforeIndex <= currentIndex) {
      const existing = beforeByShotId.get(event.before_shot_id) || [];
      existing.push(eventPayload);
      beforeByShotId.set(event.before_shot_id, existing);
      return;
    }
    if (afterIndex !== undefined && afterIndex < currentIndex) {
      const existing = afterByShotId.get(event.after_shot_id) || [];
      existing.push(eventPayload);
      afterByShotId.set(event.after_shot_id, existing);
    }
  });
  return { beforeByShotId, afterByShotId };
}

function textBiasForDirection(direction) {
  if (direction === "left") return "right";
  if (direction === "right") return "left";
  return "center";
}

function badgeElement(
  text,
  style,
  size,
  badgeColorOverride = null,
  widthOverride = null,
  heightOverride = null,
  textBias = "center",
  scale = 1,
) {
  const badge = document.createElement("span");
  const role = text.startsWith("Timer")
    ? "timer-badge"
    : text.startsWith("Draw")
      ? "draw-badge"
      : text.startsWith("Hit Factor") || text.startsWith("Final ")
        ? "score-badge"
        : "shot-badge";
  badge.className = `overlay-badge badge-${size} ${role}`;
  badge.textContent = text;
  badge.style.background = rgba(badgeColorOverride || style.background_color, style.opacity);
  badge.style.color = style.text_color;
  badge.style.borderRadius = overlayStyleMode === "bubble" ? "999px" : overlayStyleMode === "rounded" ? "16px" : "0";
  badge.style.display = "inline-flex";
  badge.style.alignItems = "center";
  badge.style.justifyContent = textBias === "left" ? "flex-start" : textBias === "right" ? "flex-end" : "center";
  badge.style.textAlign = textBias;
  badge.style.overflow = "hidden";
  badge.style.whiteSpace = text.includes("\n") ? "pre-line" : "nowrap";
  badge.style.wordBreak = "normal";
  badge.style.overflowWrap = "normal";
  badge.style.lineHeight = "1";
  const scaledPaddingY = scaledOverlayPixelValue(overlaySpacing, scale, 0);
  const scaledPaddingX = scaledOverlayPixelValue(overlaySpacing * 1.5, scale, 0);
  badge.style.padding = `${scaledPaddingY}px ${scaledPaddingX}px`;
  badge.style.margin = "0";
  const scaledWidth = widthOverride > 0
    ? scaledOverlayPixelValue(widthOverride, scale, 1)
    : state.project.overlay.bubble_width > 0
      ? scaledOverlayPixelValue(state.project.overlay.bubble_width, scale, 1)
      : 0;
  const scaledHeight = heightOverride > 0
    ? scaledOverlayPixelValue(heightOverride, scale, 1)
    : state.project.overlay.bubble_height > 0
      ? scaledOverlayPixelValue(state.project.overlay.bubble_height, scale, 1)
      : 0;
  if (scaledWidth > 0) badge.style.width = `${scaledWidth}px`;
  if (scaledHeight > 0) badge.style.height = `${scaledHeight}px`;
  badge.style.fontFamily = state.project.overlay.font_family || "Helvetica Neue";
  badge.style.fontSize = `${scaledOverlayPixelValue(state.project.overlay.font_size || 14, scale, 1)}px`;
  badge.style.fontWeight = state.project.overlay.font_bold ? "700" : "400";
  badge.style.fontStyle = state.project.overlay.font_italic ? "italic" : "normal";
  return badge;
}

function videoContentRect(video, container) {
  if (!video || !container) return null;
  const containerRect = container.getBoundingClientRect();
  const boxRect = video.getBoundingClientRect();
  const boxWidth = Math.max(1, boxRect.width || video.clientWidth || containerRect.width);
  const boxHeight = Math.max(1, boxRect.height || video.clientHeight || containerRect.height);
  const sourceWidth = Math.max(1, video.videoWidth || boxWidth);
  const sourceHeight = Math.max(1, video.videoHeight || boxHeight);
  const sourceAspect = sourceWidth / sourceHeight;
  const boxAspect = boxWidth / boxHeight;
  let contentWidth = boxWidth;
  let contentHeight = boxHeight;
  let offsetX = 0;
  let offsetY = 0;
  if (sourceAspect > boxAspect) {
    contentHeight = boxWidth / sourceAspect;
    offsetY = (boxHeight - contentHeight) / 2;
  } else {
    contentWidth = boxHeight * sourceAspect;
    offsetX = (boxWidth - contentWidth) / 2;
  }
  return {
    left: (boxRect.left - containerRect.left) + offsetX,
    top: (boxRect.top - containerRect.top) + offsetY,
    width: contentWidth,
    height: contentHeight,
  };
}

function ensureEvenExportDimension(value) {
  const numeric = Math.max(2, Math.trunc(Number(value) || 0));
  return numeric % 2 === 0 ? numeric : numeric - 1;
}

function exportAspectRatioValue(aspectRatio) {
  return {
    original: null,
    "16:9": [16, 9],
    "9:16": [9, 16],
    "1:1": [1, 1],
    "4:5": [4, 5],
  }[String(aspectRatio || "original")] ?? null;
}

function normalizedExportDimension(value) {
  if (value === null || value === undefined || value === "") return null;
  const numeric = Math.trunc(Number(value));
  if (!Number.isFinite(numeric)) return null;
  return Math.max(2, numeric);
}

function computeExportCropBox(width, height, aspectRatio, centerX, centerY) {
  const target = exportAspectRatioValue(aspectRatio);
  if (target === null) {
    return {
      left: 0,
      top: 0,
      width: ensureEvenExportDimension(width),
      height: ensureEvenExportDimension(height),
    };
  }

  const targetRatio = target[0] / target[1];
  const currentRatio = width / height;
  let cropWidth;
  let cropHeight;
  if (currentRatio > targetRatio) {
    cropHeight = ensureEvenExportDimension(height);
    cropWidth = ensureEvenExportDimension(Math.round(cropHeight * targetRatio));
  } else {
    cropWidth = ensureEvenExportDimension(width);
    cropHeight = ensureEvenExportDimension(Math.round(cropWidth / targetRatio));
  }

  cropWidth = Math.max(2, Math.min(width, cropWidth));
  cropHeight = Math.max(2, Math.min(height, cropHeight));

  const centerPx = (normalizedCoordinateValue(centerX) ?? 0.5) * width;
  const centerPy = (normalizedCoordinateValue(centerY) ?? 0.5) * height;
  let left = Math.round(centerPx - (cropWidth / 2));
  let top = Math.round(centerPy - (cropHeight / 2));
  left = Math.max(0, Math.min(width - cropWidth, left));
  top = Math.max(0, Math.min(height - cropHeight, top));
  return { left, top, width: cropWidth, height: cropHeight };
}

function exportTargetDimensions(cropWidth, cropHeight) {
  const exportSettings = state?.project?.export || {};
  const targetWidth = normalizedExportDimension(exportSettings.target_width);
  const targetHeight = normalizedExportDimension(exportSettings.target_height);
  if (targetWidth === null || targetHeight === null) {
    return {
      width: ensureEvenExportDimension(cropWidth),
      height: ensureEvenExportDimension(cropHeight),
    };
  }
  return {
    width: ensureEvenExportDimension(targetWidth),
    height: ensureEvenExportDimension(targetHeight),
  };
}

function fitAspectRect(width, height, aspectRatio) {
  const safeWidth = Math.max(1, Number(width) || 1);
  const safeHeight = Math.max(1, Number(height) || 1);
  const safeAspect = Number(aspectRatio) > 0 ? Number(aspectRatio) : 1;
  let rectWidth = safeWidth;
  let rectHeight = rectWidth / safeAspect;
  if (rectHeight > safeHeight) {
    rectHeight = safeHeight;
    rectWidth = rectHeight * safeAspect;
  }
  return {
    left: (safeWidth - rectWidth) / 2,
    top: (safeHeight - rectHeight) / 2,
    width: rectWidth,
    height: rectHeight,
  };
}

function previewFrameGeometry(video, container) {
  const exportSettings = state?.project?.export;
  if (!container) return null;
  const containerRect = container.getBoundingClientRect();
  const containerWidth = Math.max(1, Number(containerRect.width || container.clientWidth || 1));
  const containerHeight = Math.max(1, Number(containerRect.height || container.clientHeight || 1));
  const sourceWidth = Math.max(1, Number(video?.videoWidth || state?.project?.primary_video?.width || containerWidth || 1));
  const sourceHeight = Math.max(1, Number(video?.videoHeight || state?.project?.primary_video?.height || containerHeight || 1));
  if (!exportSettings) {
    const sourceAspect = sourceWidth / sourceHeight;
    const frameRect = fitAspectRect(containerWidth, containerHeight, sourceAspect);
    return {
      frameRect,
      outputWidth: sourceWidth,
      outputHeight: sourceHeight,
      scale: overlayDisplayScale(video, frameRect, sourceWidth),
      cropBox: { left: 0, top: 0, width: sourceWidth, height: sourceHeight },
    };
  }

  const cropBox = computeExportCropBox(
    sourceWidth,
    sourceHeight,
    exportSettings.aspect_ratio,
    exportSettings.crop_center_x,
    exportSettings.crop_center_y,
  );
  const outputDimensions = exportTargetDimensions(cropBox.width, cropBox.height);
  const frameRect = fitAspectRect(containerWidth, containerHeight, outputDimensions.width / outputDimensions.height);
  return {
    frameRect,
    outputWidth: outputDimensions.width,
    outputHeight: outputDimensions.height,
    scale: overlayDisplayScale(video, frameRect, outputDimensions.width),
    cropBox,
  };
}

function overlayDisplayScale(video, frameRect, outputWidth = null) {
  if (!video || !frameRect) return 1;
  const sourceWidth = Number(outputWidth) || Number(video.videoWidth) || 0;
  if (sourceWidth <= 0) return 1;
  const scale = frameRect.width / sourceWidth;
  return Number.isFinite(scale) && scale > 0 ? scale : 1;
}

function scaledOverlayPixelValue(value, scale, minimum = 0) {
  const numeric = Number(value) || 0;
  return Math.max(minimum, Math.round(numeric * scale * 100) / 100);
}

function positionOverlayContainer(overlay, quadrantValue = null, frameRect = null, customPoint = null, scale = 1) {
  const settings = state.project.overlay;
  const quadrant = quadrantValue || settings.shot_quadrant || "bottom_left";
  const direction = settings.shot_direction || "right";
  overlay.style.left = "";
  overlay.style.right = "";
  overlay.style.top = "";
  overlay.style.bottom = "";
  overlay.style.transform = "";
  overlay.style.width = "auto";
  overlay.style.height = "auto";
  overlay.style.boxSizing = "border-box";
  const scaledMargin = scaledOverlayPixelValue(overlayMargin, scale, 0);
  overlay.style.padding = `${scaledMargin}px`;
  overlay.style.gap = `${scaledMargin}px`;
  overlay.style.maxWidth = frameRect ? `${Math.max(0, frameRect.width)}px` : "calc(100% - 12px)";
  overlay.style.maxHeight = frameRect ? `${Math.max(0, frameRect.height)}px` : "calc(100% - 12px)";
  overlay.style.overflow = "hidden";
  overlay.style.alignContent = "flex-start";
  overlay.style.flexDirection = ["left", "right"].includes(direction) ? "row" : "column";
  overlay.style.flexWrap = ["left", "right"].includes(direction) ? "wrap" : "nowrap";
  if (direction === "left") overlay.style.flexDirection = "row-reverse";
  if (direction === "up") overlay.style.flexDirection = "column-reverse";

  if (quadrant === CUSTOM_QUADRANT_VALUE) {
    const x = normalizedCoordinateValue(customPoint?.x) ?? 0.5;
    const y = normalizedCoordinateValue(customPoint?.y) ?? 0.5;
    if (frameRect) {
      overlay.style.left = `${frameRect.left + (x * frameRect.width)}px`;
      overlay.style.top = `${frameRect.top + (y * frameRect.height)}px`;
    }
    overlay.style.justifyContent = "flex-start";
    overlay.style.alignItems = "flex-start";
    overlay.style.transform = "";
    return;
  }

  if (!frameRect) return;

  const [vertical, horizontal] = quadrant.split("_");
  const anchorX = horizontal === "left"
    ? frameRect.left
    : horizontal === "middle"
      ? frameRect.left + (frameRect.width / 2)
      : frameRect.left + frameRect.width;
  const anchorY = vertical === "top"
    ? frameRect.top
    : vertical === "middle"
      ? frameRect.top + (frameRect.height / 2)
      : frameRect.top + frameRect.height;
  const translateX = horizontal === "left" ? "0" : horizontal === "middle" ? "-50%" : "-100%";
  const translateY = vertical === "top" ? "0" : vertical === "middle" ? "-50%" : "-100%";
  overlay.style.left = `${anchorX}px`;
  overlay.style.top = `${anchorY}px`;
  overlay.style.justifyContent = "flex-start";
  overlay.style.alignItems = "flex-start";
  overlay.style.transform = translateX === "0" && translateY === "0"
    ? ""
    : `translate(${translateX}, ${translateY})`;
}

function pinCustomOverlayAnchor(overlay, frameRect, customPoint = null) {
  if (!overlay || !frameRect) return;
  const anchorBadge = overlay.firstElementChild;
  if (!(anchorBadge instanceof HTMLElement)) return;
  const x = normalizedCoordinateValue(customPoint?.x) ?? 0.5;
  const y = normalizedCoordinateValue(customPoint?.y) ?? 0.5;
  overlay.style.left = `${frameRect.left + (x * frameRect.width)}px`;
  overlay.style.top = `${frameRect.top + (y * frameRect.height)}px`;
  overlay.style.justifyContent = "flex-start";
  overlay.style.alignItems = "flex-start";
  overlay.style.transform = "";
  const overlayRect = overlay.getBoundingClientRect();
  const badgeRect = anchorBadge.getBoundingClientRect();
  const anchorOffsetX = (badgeRect.left - overlayRect.left) + (badgeRect.width / 2);
  const anchorOffsetY = (badgeRect.top - overlayRect.top) + (badgeRect.height / 2);
  overlay.style.transform = `translate(${-anchorOffsetX}px, ${-anchorOffsetY}px)`;
}

function positionCustomBadge(badge, frameRect) {
  const customX = normalizedCoordinateValue(state.project.overlay.custom_box_x);
  const customY = normalizedCoordinateValue(state.project.overlay.custom_box_y);
  if (customX === null || customY === null) return false;
  badge.style.position = "absolute";
  badge.style.margin = "0";
  badge.style.left = `${clamp(customX * frameRect.width, 0, frameRect.width)}px`;
  badge.style.top = `${clamp(customY * frameRect.height, 0, frameRect.height)}px`;
  badge.style.transform = "translate(-50%, -50%)";
  return true;
}

function placeOverlayBadge(layer, badge, frameRect, xValue, yValue) {
  const x = normalizedCoordinateValue(xValue);
  const y = normalizedCoordinateValue(yValue);
  if (!layer || !badge || !frameRect || x === null || y === null) return false;
  badge.style.position = "absolute";
  badge.style.margin = "0";
  badge.style.left = `${clamp(x * frameRect.width, 0, frameRect.width)}px`;
  badge.style.top = `${clamp(y * frameRect.height, 0, frameRect.height)}px`;
  badge.style.transform = "translate(-50%, -50%)";
  layer.appendChild(badge);
  return true;
}

let customOverlayDrag = null;

function beginCustomOverlayDrag(event) {
  const customOverlay = $("custom-overlay");
  const customBadge = event.target instanceof Element
    ? event.target.closest("[data-custom-box-drag]")
    : null;
  if (
    event.button !== 0
    || !customOverlay
    || !customOverlay.classList.contains("has-badge")
    || !state.project.overlay.custom_box_enabled
    || !effectiveCustomBoxText().trim()
    || !(customBadge instanceof HTMLElement)
    || !customOverlay.contains(customBadge)
  ) return;
  event.preventDefault();
  const stage = $("video-stage");
  const frameRect = previewFrameGeometry($("primary-video"), stage)?.frameRect || stage.getBoundingClientRect();
  const badgeRect = customBadge.getBoundingClientRect();
  const startX = clamp((badgeRect.left - frameRect.left + badgeRect.width / 2) / frameRect.width, 0, 1);
  const startY = clamp((badgeRect.top - frameRect.top + badgeRect.height / 2) / frameRect.height, 0, 1);
  customOverlayDrag = {
    target: customOverlay,
    pointerId: event.pointerId,
    startClientX: event.clientX,
    startClientY: event.clientY,
    startX,
    startY,
  };
  capturePointer(customOverlay, event.pointerId);
  customOverlay.classList.add("dragging");
  activity("overlay.custom_box.drag.start", { x: startX, y: startY });
}

function moveCustomOverlayDrag(event) {
  if (!customOverlayDrag) return;
  if (event.pointerId !== undefined && customOverlayDrag.pointerId !== undefined && event.pointerId !== customOverlayDrag.pointerId) return;
  const stage = $("video-stage");
  if (!stage) return;
  const frameRect = previewFrameGeometry($("primary-video"), stage)?.frameRect || stage.getBoundingClientRect();
  const width = Math.max(1, frameRect.width || 0);
  const height = Math.max(1, frameRect.height || 0);
  const { startClientX, startClientY, startX, startY } = customOverlayDrag;
  const deltaX = (event.clientX - startClientX) / width;
  const deltaY = (event.clientY - startClientY) / height;
  const newX = clamp(startX + deltaX, 0, 1);
  const newY = clamp(startY + deltaY, 0, 1);
  $("custom-box-quadrant").value = CUSTOM_QUADRANT_VALUE;
  $("custom-box-x").value = newX.toFixed(3);
  $("custom-box-y").value = newY.toFixed(3);
  syncOverlayPreviewStateFromControls();
  renderLiveOverlay();
  scheduleOverlayApply();
}

function endCustomOverlayDrag(event) {
  if (!customOverlayDrag) return;
  if (event.pointerId !== undefined && customOverlayDrag.pointerId !== undefined && event.pointerId !== customOverlayDrag.pointerId) return;
  const customOverlay = $("custom-overlay");
  releasePointer(customOverlayDrag.target || customOverlay, event.pointerId);
  customOverlay?.classList.remove("dragging");
  activity("overlay.custom_box.drag.commit", {
    x: normalizedCoordinateValue($("custom-box-x")?.value),
    y: normalizedCoordinateValue($("custom-box-y")?.value),
  });
  autoApplyOverlay.cancel();
  callApi("/api/overlay", readOverlayPayload());
  customOverlayDrag = null;
}

function overlayDragConfiguration(kind) {
  return {
    timer: { xId: "timer-x", yId: "timer-y" },
    draw: { xId: "draw-x", yId: "draw-y" },
    score: { xId: "score-x", yId: "score-y" },
    shots: {
      xId: "overlay-custom-x",
      yId: "overlay-custom-y",
      quadrantId: "shot-quadrant",
      quadrantValue: CUSTOM_QUADRANT_VALUE,
    },
  }[kind] || null;
}

function overlayDragAnchor(kind, badge, frameRect) {
  if (kind === "shots") {
    const overlay = $("live-overlay");
    const anchorBadge = overlay?.firstElementChild;
    const anchorRect = anchorBadge?.getBoundingClientRect() || overlay?.getBoundingClientRect() || badge.getBoundingClientRect();
    return {
      x: clamp((anchorRect.left - frameRect.left + (anchorRect.width / 2)) / Math.max(1, frameRect.width), 0, 1),
      y: clamp((anchorRect.top - frameRect.top + (anchorRect.height / 2)) / Math.max(1, frameRect.height), 0, 1),
    };
  }
  const rect = badge.getBoundingClientRect();
  return {
    x: clamp((rect.left - frameRect.left + (rect.width / 2)) / Math.max(1, frameRect.width), 0, 1),
    y: clamp((rect.top - frameRect.top + (rect.height / 2)) / Math.max(1, frameRect.height), 0, 1),
  };
}

function beginOverlayBadgeDrag(event) {
  if (event.button !== 0 || overlayBadgeDrag) return;
  const badge = event.target instanceof Element ? event.target.closest("[data-overlay-drag]") : null;
  if (!(badge instanceof HTMLElement)) return;
  const kind = badge.dataset.overlayDrag || "";
  const config = overlayDragConfiguration(kind);
  if (!config || !state?.project) return;
  const stage = $("video-stage");
  const frameRect = previewFrameGeometry($("primary-video"), stage)?.frameRect || stage.getBoundingClientRect();
  const anchor = overlayDragAnchor(kind, badge, frameRect);
  overlayBadgeDrag = {
    target: stage,
    kind,
    pointerId: event.pointerId,
    startClientX: event.clientX,
    startClientY: event.clientY,
    startX: anchor.x,
    startY: anchor.y,
  };
  capturePointer(stage, event.pointerId);
  stage.classList.add("overlay-dragging");
  event.preventDefault();
  activity("overlay.drag.start", { kind, x: anchor.x, y: anchor.y });
}

function moveOverlayBadgeDrag(event) {
  if (!overlayBadgeDrag || !state?.project) return;
  const config = overlayDragConfiguration(overlayBadgeDrag.kind);
  if (!config) return;
  const stage = $("video-stage");
  const frameRect = previewFrameGeometry($("primary-video"), stage)?.frameRect || stage.getBoundingClientRect();
  const width = Math.max(1, frameRect.width || 0);
  const height = Math.max(1, frameRect.height || 0);
  const deltaX = (event.clientX - overlayBadgeDrag.startClientX) / width;
  const deltaY = (event.clientY - overlayBadgeDrag.startClientY) / height;
  const nextX = clamp(overlayBadgeDrag.startX + deltaX, 0, 1);
  const nextY = clamp(overlayBadgeDrag.startY + deltaY, 0, 1);

  if (config.quadrantId) {
    $(config.quadrantId).value = config.quadrantValue;
    syncOverlayCoordinateControlState();
  }
  $(config.xId).value = nextX.toFixed(3);
  $(config.yId).value = nextY.toFixed(3);
  syncOverlayPreviewStateFromControls();
  renderLiveOverlay();
}

function endOverlayBadgeDrag(event) {
  if (!overlayBadgeDrag) return;
  const config = overlayDragConfiguration(overlayBadgeDrag.kind);
  releasePointer(overlayBadgeDrag.target, event.pointerId);
  overlayBadgeDrag.target.classList.remove("overlay-dragging");
  if (config) {
    activity("overlay.drag.commit", {
      kind: overlayBadgeDrag.kind,
      x: normalizedCoordinateValue($(config.xId)?.value),
      y: normalizedCoordinateValue($(config.yId)?.value),
    });
    scheduleOverlayApply();
  }
  overlayBadgeDrag = null;
}

function beginMergePreviewDrag(event) {
  if (event.button !== 0 || mergePreviewDrag || state?.project?.merge?.layout !== "pip") return;
  const item = event.target instanceof Element ? event.target.closest(".merge-preview-item[data-source-id]") : null;
  if (!(item instanceof HTMLElement)) return;
  const sourceId = item.dataset.sourceId || "";
  const source = mergeSourceById(sourceId);
  if (!source) return;
  const stage = $("video-stage");
  const frameRect = previewFrameGeometry($("primary-video"), stage)?.frameRect || stage.getBoundingClientRect();
  const itemRect = item.getBoundingClientRect();
  mergePreviewDrag = {
    item,
    sourceId,
    pointerId: event.pointerId,
    startClientX: event.clientX,
    startClientY: event.clientY,
    startLeftPx: itemRect.left - frameRect.left,
    startTopPx: itemRect.top - frameRect.top,
  };
  capturePointer(item, event.pointerId);
  item.classList.add("dragging");
  event.preventDefault();
  activity("merge.preview.drag.start", {
    source_id: sourceId,
    pip_x: normalizedCoordinateValue(source.pip_x),
    pip_y: normalizedCoordinateValue(source.pip_y),
  });
}

function moveMergePreviewDrag(event) {
  if (!mergePreviewDrag || !state?.project) return;
  const source = mergeSourceById(mergePreviewDrag.sourceId);
  if (!source) return;
  const stage = $("video-stage");
  const frameRect = previewFrameGeometry($("primary-video"), stage)?.frameRect || stage.getBoundingClientRect();
  const rect = mergeSourcePipRect(source, frameRect, currentPipSizePercent());
  const travelX = Math.max(0, frameRect.width - rect.width);
  const travelY = Math.max(0, frameRect.height - rect.height);
  const nextLeft = clamp(mergePreviewDrag.startLeftPx + (event.clientX - mergePreviewDrag.startClientX), 0, travelX);
  const nextTop = clamp(mergePreviewDrag.startTopPx + (event.clientY - mergePreviewDrag.startClientY), 0, travelY);
  const nextX = travelX === 0 ? 0 : nextLeft / travelX;
  const nextY = travelY === 0 ? 0 : nextTop / travelY;
  updateLocalMergeSourcePosition(mergePreviewDrag.sourceId, nextX, nextY);
  renderVideo();
}

function endMergePreviewDrag(event) {
  if (!mergePreviewDrag) return;
  releasePointer(mergePreviewDrag.item, event.pointerId);
  mergePreviewDrag.item.classList.remove("dragging");
  const source = mergeSourceById(mergePreviewDrag.sourceId);
  if (source) {
    activity("merge.preview.drag.commit", {
      source_id: mergePreviewDrag.sourceId,
      pip_x: normalizedCoordinateValue(source.pip_x),
      pip_y: normalizedCoordinateValue(source.pip_y),
    });
    callApi("/api/merge/source", {
      source_id: mergePreviewDrag.sourceId,
      pip_x: normalizedCoordinateValue(source.pip_x) ?? 1,
      pip_y: normalizedCoordinateValue(source.pip_y) ?? 1,
    });
  }
  mergePreviewDrag = null;
}

function renderLiveOverlay() {
  if (!state?.project) return;
  const overlay = $("live-overlay");
  const customOverlay = $("custom-overlay");
  const scoreLayer = $("score-layer");
  const position = state.project.overlay.position;
  overlay.className = `live-overlay overlay-${position}`;
  customOverlay.className = `live-overlay overlay-${position}`;
  overlay.innerHTML = "";
  customOverlay.innerHTML = "";
  scoreLayer.innerHTML = "";
  if (position === "none" || !state.media.primary_available) return;
  const stage = $("video-stage");
  const video = $("primary-video");
  const frameGeometry = previewFrameGeometry(video, stage);
  const frameRect = frameGeometry?.frameRect || stage.getBoundingClientRect();
  const overlayScale = frameGeometry?.scale || overlayDisplayScale(video, frameRect);
  positionOverlayContainer(overlay, state.project.overlay.shot_quadrant, frameRect, {
    x: state.project.overlay.custom_x,
    y: state.project.overlay.custom_y,
  }, overlayScale);
  const customBoxHasCoordinates = normalizedCoordinateValue(state.project.overlay.custom_box_x) !== null
    && normalizedCoordinateValue(state.project.overlay.custom_box_y) !== null;
  if (customBoxHasCoordinates) {
    customOverlay.style.left = `${frameRect.left}px`;
    customOverlay.style.top = `${frameRect.top}px`;
    customOverlay.style.width = `${frameRect.width}px`;
    customOverlay.style.height = `${frameRect.height}px`;
    customOverlay.style.transform = "";
    customOverlay.style.justifyContent = "flex-start";
    customOverlay.style.alignItems = "flex-start";
    customOverlay.style.padding = "0";
    customOverlay.style.gap = "0";
  } else {
    positionOverlayContainer(customOverlay, state.project.overlay.custom_box_quadrant, frameRect, null, overlayScale);
  }

  const positionMs = Math.round((video.currentTime || 0) * 1000);
  const beep = state.project.analysis.beep_time_ms_primary;
  let elapsed = beep === null || beep === undefined ? positionMs : Math.max(0, positionMs - beep);
  const shots = orderedShotsByTime();
  const firstShotTime = shots.length > 0 ? shots[0].time_ms : null;
  const finalShotIndex = shots.length - 1;
  const finalShotTime = finalShotIndex >= 0 ? shots[finalShotIndex].time_ms : null;
  const finalShotReached = finalShotTime !== null && finalShotTime !== undefined && positionMs >= finalShotTime;
  if (beep !== null && beep !== undefined && shots.length > 0) {
    const lastShotMs = shots[shots.length - 1].time_ms;
    elapsed = Math.min(elapsed, Math.max(0, lastShotMs - beep));
  }
  const size = state.project.overlay.badge_size;
  const shotTextBias = textBiasForDirection(state.project.overlay.shot_direction || "right");
  const currentIndex = currentShotIndex(positionMs);
  const visibleEvents = visibleTimingEventsByShot(currentIndex);
  const appendOverlayBadge = (badge, xValue = null, yValue = null) => {
    if (!placeOverlayBadge(scoreLayer, badge, frameRect, xValue, yValue)) {
      overlay.appendChild(badge);
    }
  };
  if (state.project.overlay.show_timer) {
    const timerBadge = badgeElement(`Timer ${seconds(elapsed)}`, state.project.overlay.timer_badge, size, null, null, null, "center", overlayScale);
    timerBadge.dataset.overlayDrag = "timer";
    appendOverlayBadge(timerBadge, state.project.overlay.timer_x, state.project.overlay.timer_y);
  }
  if (
    state.project.overlay.show_draw
    && firstShotTime !== null
    && (beep === null || beep === undefined || positionMs >= beep)
    && positionMs < firstShotTime
    && state.metrics.draw_ms !== null
    && state.metrics.draw_ms !== undefined
    && Number(state.metrics.draw_ms) > 0
  ) {
    const drawBadge = badgeElement(`Draw ${seconds(state.metrics.draw_ms)}`, state.project.overlay.shot_badge, size, null, null, null, "center", overlayScale);
    drawBadge.dataset.overlayDrag = "draw";
    appendOverlayBadge(drawBadge, state.project.overlay.draw_x, state.project.overlay.draw_y);
  }

  if (state.project.overlay.show_shots && currentIndex >= 0) {
    const maxVisible = Math.max(1, Number(state.project.overlay.max_visible_shots || 4));
    const start = Math.max(0, currentIndex - maxVisible + 1);
    for (let index = start; index <= currentIndex; index += 1) {
      const shot = shots[index];
      if (!shot) continue;
      (visibleEvents.beforeByShotId.get(shot.id) || []).forEach((event) => {
        const eventBadge = badgeElement(event.label, state.project.overlay.timer_badge, size, null, null, null, "center", overlayScale);
        eventBadge.dataset.overlayDrag = "shots";
        overlay.appendChild(eventBadge);
      });
      const splitMs = resolvedSplitMsForShot(shot.id, index + 1, shot.time_ms);
      const style = index === currentIndex
        ? state.project.overlay.current_shot_badge
        : state.project.overlay.shot_badge;
      const badgeSuffix = formatShotBadgeSuffix(shot);
      const scoreColor = state.project.scoring.enabled && shot.score
        ? state.project.overlay.scoring_colors[shot.score.letter]
        : null;
      const shotBadge = badgeElement(`Shot ${index + 1} ${splitSeconds(splitMs)}${badgeSuffix}`, style, size, scoreColor, null, null, shotTextBias, overlayScale);
      shotBadge.dataset.overlayDrag = "shots";
      overlay.appendChild(shotBadge);
      (visibleEvents.afterByShotId.get(shot.id) || []).forEach((event) => {
        const eventBadge = badgeElement(event.label, state.project.overlay.timer_badge, size, null, null, null, "center", overlayScale);
        eventBadge.dataset.overlayDrag = "shots";
        overlay.appendChild(eventBadge);
      });
    }
  }

  const summary = state.scoring_summary || {};
  if (finalShotReached && state.project.scoring.enabled && state.project.overlay.show_score && summary.display_value && summary.display_value !== "--") {
    const scoreBadge = badgeElement(`${summary.display_label} ${summary.display_value}`, state.project.overlay.hit_factor_badge, size, null, null, null, "center", overlayScale);
    scoreBadge.dataset.overlayDrag = "score";
    appendOverlayBadge(scoreBadge, state.project.overlay.score_x, state.project.overlay.score_y);
  }

  if (usesCustomQuadrant(state.project.overlay.shot_quadrant) && overlay.childElementCount > 0) {
    pinCustomOverlayAnchor(overlay, frameRect, {
      x: state.project.overlay.custom_x,
      y: state.project.overlay.custom_y,
    });
  }

  const customBoxText = effectiveCustomBoxText().trim();
  const importedSummaryMode = (state.project.overlay.custom_box_mode || "manual") === "imported_summary";
  if (state.project.overlay.custom_box_enabled && customBoxText && (!importedSummaryMode || finalShotReached)) {
    const customBoxStyle = {
      background_color: state.project.overlay.custom_box_background_color || state.project.overlay.hit_factor_badge.background_color,
      text_color: state.project.overlay.custom_box_text_color || state.project.overlay.hit_factor_badge.text_color,
      opacity: state.project.overlay.custom_box_opacity ?? state.project.overlay.hit_factor_badge.opacity,
    };
    const customBadge = badgeElement(
      customBoxText,
      customBoxStyle,
      size,
      null,
      state.project.overlay.custom_box_width,
      state.project.overlay.custom_box_height,
      "center",
      overlayScale,
    );
    customBadge.dataset.customBoxDrag = "true";
    customBadge.dataset.overlayDrag = "custom_box";
    positionCustomBadge(customBadge, frameRect);
    customOverlay.appendChild(customBadge);
    customOverlay.classList.add("has-badge");
  }
}

function startOverlayLoop() {
  if (overlayFrame !== null) return;
  activity("video.play", { current_time_s: $("primary-video").currentTime });
  scheduleSecondaryPreviewSync();
  const tick = () => {
    activity("frame.overlay", {
      current_time_s: $("primary-video").currentTime,
      merge_sources: (state?.project?.merge_sources || []).length,
      selected_shot_id: selectedShotId || "",
    });
    scheduleSecondaryPreviewSync();
    renderLiveOverlay();
    overlayFrame = requestAnimationFrame(tick);
  };
  overlayFrame = requestAnimationFrame(tick);
}

function stopOverlayLoop() {
  if (overlayFrame === null) return;
  activity("video.pause", { current_time_s: $("primary-video").currentTime });
  cancelAnimationFrame(overlayFrame);
  overlayFrame = null;
  scheduleSecondaryPreviewSync();
  renderLiveOverlay();
}

function render() {
  if (!state?.project) return;
  applyLayoutState();
  renderHeader();
  renderStats();
  renderVideo();
  renderWaveform();
  renderTimingTables();
  renderControls();
  renderSelection();
  renderLiveOverlay();
  setActiveTool(activeTool);
}

function waveformTime(event) {
  const rect = $("waveform").getBoundingClientRect();
  const x = Math.max(0, Math.min(1, (event.clientX - rect.left) / rect.width));
  const visible = waveformWindow();
  return Math.round(visible.start + (x * visible.duration));
}

function shotPixelDistance(event, shot) {
  const rect = $("waveform").getBoundingClientRect();
  if (!isWaveformVisible(shot.time_ms)) return Number.POSITIVE_INFINITY;
  const shotX = waveformX(shot.time_ms, rect.width);
  return Math.abs((event.clientX - rect.left) - shotX);
}

function nearestShot(event) {
  const shots = state?.project?.analysis?.shots || [];
  let nearest = null;
  let nearestDistance = Number.POSITIVE_INFINITY;
  shots.forEach((shot) => {
    const distance = shotPixelDistance(event, shot);
    if (distance < nearestDistance) {
      nearest = shot;
      nearestDistance = distance;
    }
  });
  return nearestDistance <= 28 ? nearest : null;
}

function setWaveformMode(mode) {
  waveformMode = mode;
  document.querySelectorAll("[data-waveform-mode]").forEach((button) => {
    button.classList.toggle("active", button.dataset.waveformMode === mode);
  });
  const help = $("waveform-help");
  if (mode === "add") {
    help.textContent = "Add Shot mode: click the waveform to add a manual shot.";
  } else {
    help.textContent = "Select mode: click a shot marker, drag to move, arrows nudge.";
  }
  activity("waveform.mode", { mode });
}

function setWaveformExpanded(expanded) {
  const root = $("cockpit-root");
  root.classList.toggle("waveform-expanded", expanded);
  root.classList.remove("timing-expanded");
  $("expand-waveform").textContent = expanded ? "Collapse" : "Expand";
  activity("waveform.expand", { expanded });
  renderWaveform();
  window.requestAnimationFrame(() => renderWaveform());
}

function setWaveformZoom(delta) {
  const oldWindow = waveformWindow();
  const center = oldWindow.start + (oldWindow.duration / 2);
  waveformZoomX = clamp(waveformZoomX * delta, 1, 200);
  const newDuration = durationMs() / waveformZoomX;
  waveformOffsetMs = clamp(center - (newDuration / 2), 0, Math.max(0, durationMs() - newDuration));
  window.localStorage.setItem("splitshot.waveform.zoomX", String(waveformZoomX));
  window.localStorage.setItem("splitshot.waveform.offsetMs", String(Math.round(waveformOffsetMs)));
  activity("waveform.zoom_x", { zoom: waveformZoomX, offset_ms: waveformOffsetMs });
  renderWaveform();
}

function setWaveformAmplitude(delta) {
  if (!selectedShotId) {
    activity("waveform.shot_amplitude.skipped", { reason: "no_selected_shot" });
    return;
  }
  const currentZoom = waveformShotAmplitudeById[selectedShotId] || 1;
  const nextZoom = clamp(currentZoom * delta, 0.25, 12);
  waveformShotAmplitudeById[selectedShotId] = nextZoom;
  activity("waveform.shot_amplitude", { shot_id: selectedShotId, zoom: nextZoom });
  renderWaveform();
}

function resetWaveformView() {
  waveformZoomX = 1;
  waveformShotAmplitudeById = {};
  waveformOffsetMs = 0;
  window.localStorage.removeItem("splitshot.waveform.zoomX");
  window.localStorage.removeItem("splitshot.waveform.offsetMs");
  activity("waveform.zoom_reset", {});
  renderWaveform();
}

function setTimingExpanded(expanded) {
  const root = $("cockpit-root");
  root.classList.toggle("timing-expanded", expanded);
  root.classList.remove("waveform-expanded");
  $("expand-waveform").textContent = "Expand";
  activity("timing.expand", { expanded });
  renderTimingTables();
}

function moveSelectedShot(deltaMs) {
  const shot = selectedShot();
  if (!shot) return;
  activity("shot.keyboard_nudge", { shot_id: shot.id, delta_ms: deltaMs });
  callApi("/api/shots/move", { shot_id: shot.id, time_ms: shot.time_ms + deltaMs });
}

function deleteSelectedShot() {
  if (!selectedShotId) return;
  activity("shot.delete_selected", { shot_id: selectedShotId });
  callApi("/api/shots/delete", { shot_id: selectedShotId });
}

function handleWaveformPointerDown(event) {
  $("waveform").focus();
  const time_ms = waveformTime(event);
  if (waveformMode === "add") {
    activity("waveform.add_shot", { time_ms });
    callApi("/api/shots/add", { time_ms });
    return;
  }
  const shot = nearestShot(event);
  if (shot) {
    selectedShotId = shot.id;
    draggingShotId = shot.id;
    pendingDragTimeMs = shot.time_ms;
    capturePointer($("waveform"), event.pointerId);
    activity("waveform.drag_start", { shot_id: shot.id, time_ms: shot.time_ms });
    callApi("/api/shots/select", { shot_id: shot.id });
    renderWaveform();
    return;
  }
  const video = $("primary-video");
  if (state?.media?.primary_available) {
    video.currentTime = time_ms / 1000;
    activity("waveform.seek", { time_ms });
  }
}

function handleWaveformPointerMove(event) {
  if (!draggingShotId) return;
  pendingDragTimeMs = waveformTime(event);
  renderWaveform();
}

function handleWaveformPointerUp(event) {
  if (!draggingShotId) return;
  const shotId = draggingShotId;
  const timeMs = pendingDragTimeMs ?? waveformTime(event);
  draggingShotId = null;
  pendingDragTimeMs = null;
  releasePointer($("waveform"), event.pointerId);
  activity("waveform.drag_commit", { shot_id: shotId, time_ms: timeMs });
  callApi("/api/shots/move", { shot_id: shotId, time_ms: timeMs });
}

function handleKeyboardEdit(event) {
  const target = event.target;
  if (target && ["INPUT", "SELECT", "TEXTAREA"].includes(target.tagName)) return;
  if (!selectedShotId) return;
  if (event.key === "ArrowLeft") {
    event.preventDefault();
    moveSelectedShot(event.shiftKey ? -10 : -1);
  } else if (event.key === "ArrowRight") {
    event.preventDefault();
    moveSelectedShot(event.shiftKey ? 10 : 1);
  } else if (event.key === "Delete" || event.key === "Backspace") {
    event.preventDefault();
    deleteSelectedShot();
  }
}

function readOverlayPayload() {
  const styles = {};
  document.querySelectorAll(".style-card[data-badge]").forEach((card) => {
    const badge = card.dataset.badge || "";
    if (!VALID_OVERLAY_BADGE_NAMES.has(badge)) return;
    styles[badge] = {};
    card.querySelectorAll("input[data-field]").forEach((input) => {
      const value = input.type === "range" ? Number(input.value) : input.value;
      styles[badge][input.dataset.field] = value;
    });
  });
  const scoringColors = {};
  document.querySelectorAll(".score-color-input").forEach((input) => {
    scoringColors[input.dataset.letter] = input.value;
  });
  const customBoxX = $("custom-box-x").value;
  const customBoxY = $("custom-box-y").value;
  const hasCustomBoxCoordinates = normalizedCoordinateValue(customBoxX) !== null || normalizedCoordinateValue(customBoxY) !== null;
  return {
    position: state.project.overlay.position,
    badge_size: $("badge-size").value,
    styles,
    scoring_colors: scoringColors,
    style_type: overlayStyleMode,
    spacing: overlaySpacing,
    margin: overlayMargin,
    max_visible_shots: Number($("max-visible-shots").value || 4),
    shot_quadrant: $("shot-quadrant").value,
    shot_direction: $("shot-direction").value,
    custom_x: $("overlay-custom-x").value,
    custom_y: $("overlay-custom-y").value,
    timer_x: $("timer-x").value,
    timer_y: $("timer-y").value,
    draw_x: $("draw-x").value,
    draw_y: $("draw-y").value,
    score_x: $("score-x").value,
    score_y: $("score-y").value,
    bubble_width: Number($("bubble-width").value || 0),
    bubble_height: Number($("bubble-height").value || 0),
    font_family: $("overlay-font-family").value,
    font_size: Number($("overlay-font-size").value || BADGE_FONT_SIZES[$("badge-size").value] || 14),
    font_bold: $("overlay-font-bold").checked,
    font_italic: $("overlay-font-italic").checked,
    show_timer: $("show-timer").checked,
    show_draw: $("show-draw").checked,
    show_shots: $("show-shots").checked,
    show_score: $("show-score").checked,
    custom_box_enabled: $("custom-box-enabled").checked,
    custom_box_mode: $("custom-box-mode").value,
    custom_box_text: $("custom-box-text").value,
    custom_box_quadrant: hasCustomBoxCoordinates ? CUSTOM_QUADRANT_VALUE : $("custom-box-quadrant").value,
    custom_box_x: customBoxX,
    custom_box_y: customBoxY,
    custom_box_background_color: $("custom-box-background-color").value,
    custom_box_text_color: $("custom-box-text-color").value,
    custom_box_opacity: Number($("custom-box-opacity").value || 0.9),
    custom_box_width: Number($("custom-box-width").value || 0),
    custom_box_height: Number($("custom-box-height").value || 0),
  };
}

function readProjectDetailsPayload() {
  return {
    name: $("project-name").value,
    description: $("project-description").value,
  };
}

function readPractiScoreContextPayload() {
  return {
    match_type: $("match-type").value,
    stage_number: $("match-stage-number").value ? Number($("match-stage-number").value) : "",
    competitor_name: $("match-competitor-name").value.trim(),
    competitor_place: $("match-competitor-place").value ? Number($("match-competitor-place").value) : "",
  };
}

function validatePractiScoreSelection() {
  return readPractiScoreContextPayload();
}

function openHiddenFileInput(inputId) {
  const input = $(inputId);
  if (!(input instanceof HTMLInputElement)) return;
  input.value = "";
  if (typeof input.showPicker === "function") {
    input.showPicker();
    return;
  }
  input.click();
}

async function postFiles(path, files) {
  const selectedFiles = Array.from(files || []);
  let latestSuccess = null;
  for (const file of selectedFiles) {
    const result = await postFile(path, file);
    if (result) latestSuccess = result;
  }
  return latestSuccess;
}

function readMergePayload() {
  const pipValue = Number($("pip-size").value);
  return {
    enabled: $("merge-enabled").checked,
    layout: $("merge-layout").value,
    pip_size_percent: Number.isFinite(pipValue) ? clampNumber(pipValue, 10, 95) : 35,
    pip_x: normalizedCoordinateValue($("pip-x").value) ?? 1,
    pip_y: normalizedCoordinateValue($("pip-y").value) ?? 1,
  };
}

function readExportLayoutPayload() {
  return {
    quality: $("quality").value,
    aspect_ratio: $("aspect-ratio").value,
  };
}

function readScoringPayload() {
  const penaltyGrid = $("scoring-penalty-grid");
  const penaltyCounts = penaltyGrid
    ? collectPenaltyCounts(penaltyGrid, ".penalty-input[data-penalty-id]")
    : { ...(state.project?.scoring?.penalty_counts || {}) };
  return {
    enabled: $("scoring-enabled").checked,
    penalties: $("penalties") ? Number($("penalties").value || 0) : Number(state.project?.scoring?.penalties || 0),
    penalty_counts: penaltyCounts,
  };
}

function readExportSettingsPayload() {
  return {
    target_width: $("target-width").value ? Number($("target-width").value) : "",
    target_height: $("target-height").value ? Number($("target-height").value) : "",
    frame_rate: $("frame-rate").value,
    video_codec: $("video-codec").value,
    video_bitrate_mbps: Number($("video-bitrate").value || 15),
    audio_codec: $("audio-codec").value,
    audio_sample_rate: Number($("audio-sample-rate").value || 48000),
    audio_bitrate_kbps: Number($("audio-bitrate").value || 320),
    color_space: $("color-space").value,
    two_pass: $("two-pass").checked,
    ffmpeg_preset: $("ffmpeg-preset").value,
  };
}

function buildExportPayload(path) {
  return {
    path,
    preset: $("export-preset").value,
    scoring: {
      ruleset: $("scoring-preset").value,
      ...readScoringPayload(),
    },
    overlay: readOverlayPayload(),
    merge: {
      ...readMergePayload(),
      sources: (state?.project?.merge_sources || []).map((source, index) => ({
        source_id: sourceIdentifier(source, String(index)),
        pip_size_percent: currentPipSizePercent(source, currentPipSizePercent()),
        pip_x: normalizedCoordinateValue(source.pip_x) ?? 1,
        pip_y: normalizedCoordinateValue(source.pip_y) ?? 1,
        sync_offset_ms: currentSourceSyncOffsetMs(source),
      })),
    },
    ...readExportLayoutPayload(),
    ...readExportSettingsPayload(),
  };
}

function cancelPendingExportDrafts() {
  clearOverlayColorCommitTimer();
  autoApplyOverlay.cancel?.();
  autoApplyMerge.cancel?.();
  autoApplyScoring.cancel?.();
  autoApplyExportLayout.cancel?.();
  autoApplyExportSettings.cancel?.();
}

async function importTypedPath(targetId, apiPath, label) {
  const path = $(targetId).value.trim();
  if (!path) {
    setStatus(`${label} video path is required.`);
    return null;
  }
  return callApi(apiPath, { path });
}

async function openProjectWithDialog() {
  const path = $("project-path").value.trim();
  if (path) {
    const result = await callApi("/api/project/open", { path });
    if (result) setActiveTool("project");
    return result;
  }
  return pickPath("project_open", "project-path", async (path) => {
    const result = await callApi("/api/project/open", { path });
    if (result) setActiveTool("project");
  });
}

async function browseProjectPath() {
  return pickPath("project_open", "project-path", async (path) => {
    const result = await callApi("/api/project/open", { path });
    if (result) setActiveTool("project");
  });
}

async function saveProjectFlow() {
  const existingPath = $("project-path").value.trim();
  await callApi("/api/project/details", readProjectDetailsPayload());
  if (existingPath) {
    return callApi("/api/project/save", { path: existingPath });
  }
  return pickPath("project_save", "project-path", async (path) => {
    await callApi("/api/project/save", { path });
  });
}

async function applyScoringSettings(scoringPayload = readScoringPayload(), ruleset = $("scoring-preset").value) {
  const previousRuleset = state.project.scoring.ruleset;
  if (ruleset !== previousRuleset) scoringPayload.penalty_counts = {};
  await callApi("/api/scoring/profile", { ruleset });
  await callApi("/api/scoring", scoringPayload);
}

const autoApplyThreshold = debounce((payload) => {
  activity("auto_apply.threshold", payload);
  callApi("/api/analysis/threshold", payload);
}, 450);

const autoApplyProjectDetails = debounce((payload) => {
  activity("auto_apply.project_details", {});
  callApi("/api/project/details", payload);
}, 300);

const autoApplyPractiScoreContext = debounce((payload) => {
  activity("auto_apply.practiscore_context", {});
  callApi("/api/project/practiscore", payload);
}, 300);

const autoApplyOverlay = debounce((payload) => {
  activity("auto_apply.overlay", {});
  callApi("/api/overlay", payload);
}, 300);

const autoApplyMerge = debounce((payload) => {
  activity("auto_apply.merge", {});
  callApi("/api/merge", payload);
}, 300);

const autoApplyExportLayout = debounce((payload) => {
  activity("auto_apply.export_layout", {});
  callApi("/api/export/settings", payload);
}, 300);

const autoApplyExportSettings = debounce((payload) => {
  activity("auto_apply.export_settings", {});
  callApi("/api/export/settings", payload);
}, 300);

const autoApplyScoring = debounce(({ scoringPayload, ruleset }) => {
  activity("auto_apply.scoring", {});
  applyScoringSettings(scoringPayload, ruleset);
}, 300);

function scheduleThresholdApply() {
  autoApplyThreshold({ threshold: Number($("threshold").value) });
}

function scheduleProjectDetailsApply() {
  autoApplyProjectDetails(readProjectDetailsPayload());
}

function schedulePractiScoreContextApply() {
  autoApplyPractiScoreContext(readPractiScoreContextPayload());
}

function scheduleOverlayApply() {
  autoApplyOverlay(readOverlayPayload());
}

function scheduleMergeApply() {
  autoApplyMerge(readMergePayload());
}

function scheduleExportLayoutApply() {
  autoApplyExportLayout(readExportLayoutPayload());
}

function scheduleExportSettingsApply() {
  autoApplyExportSettings(readExportSettingsPayload());
}

function scheduleScoringApply() {
  autoApplyScoring({
    scoringPayload: readScoringPayload(),
    ruleset: $("scoring-preset").value,
  });
}

const handleViewportLayoutChange = debounce(() => {
  applyLayoutState();
  if (state?.project) render();
}, 120);

function wireEvents() {
  document.querySelectorAll("[data-tool]").forEach((item) => {
    item.addEventListener("click", () => {
      activity("ui.tool.click", { tool: item.dataset.tool });
      setActiveTool(item.dataset.tool);
    });
  });
  $("new-project").addEventListener("click", async () => {
    resetLocalProjectView();
    await callApi("/api/project/new", {});
  });
  $("primary-file-path").addEventListener("keydown", async (event) => {
    if (event.key !== "Enter") return;
    event.preventDefault();
    const result = await importTypedPath("primary-file-path", "/api/import/primary", "Primary");
    if (result) setActiveTool("project");
  });
  $("browse-project-path").addEventListener("click", browseProjectPath);
  $("browse-export-path").addEventListener("click", () => pickPath("export", "export-path"));
  $("export-path").addEventListener("input", () => {
    exportPathDraft = $("export-path").value;
  });
  $("browse-primary-path").addEventListener("click", () => pickPath("primary", "primary-file-path", async (path) => {
    const result = await callApi("/api/import/primary", { path });
    if (result) setActiveTool("project");
  }));
  document.querySelectorAll("[data-open-primary]").forEach((item) => {
    item.addEventListener("click", () => pickPath("primary", "primary-file-path", async (path) => {
      const result = await callApi("/api/import/primary", { path });
      if (result) setActiveTool("project");
    }));
  });
  document.querySelectorAll("[data-open-merge-media]").forEach((item) => {
    item.addEventListener("click", () => openHiddenFileInput("merge-media-input"));
  });
  $("primary-file-input").addEventListener("change", async (event) => {
    const result = await postFile("/api/files/primary", event.target.files[0]);
    if (result) setActiveTool("project");
    event.target.value = "";
  });
  $("merge-media-input").addEventListener("change", async (event) => {
    const files = Array.from(event.target.files || []);
    const result = await postFiles("/api/files/merge", files);
    if (result) setActiveTool("merge");
    event.target.value = "";
  });
  $("import-practiscore").addEventListener("click", () => {
    setStatus("Select a PractiScore results file.");
    openHiddenFileInput("practiscore-file-input");
  });
  $("practiscore-file-input").addEventListener("change", async (event) => {
    const payload = validatePractiScoreSelection();
    if (!payload) {
      event.target.value = "";
      return;
    }
    const context = await callApi("/api/project/practiscore", payload);
    if (!context) {
      event.target.value = "";
      return;
    }
    const result = await postFile("/api/files/practiscore", event.target.files[0]);
    if (result) setActiveTool("scoring");
    event.target.value = "";
  });
  $("save-project").addEventListener("click", saveProjectFlow);
  $("open-project").addEventListener("click", openProjectWithDialog);
  $("delete-project").addEventListener("click", () => callApi("/api/project/delete", {}));
  ["project-name", "project-description"].forEach((id) => {
    $(id).addEventListener("input", scheduleProjectDetailsApply);
  });
  ["match-type", "match-stage-number", "match-competitor-name", "match-competitor-place"].forEach((id) => {
    $(id).addEventListener("input", schedulePractiScoreContextApply);
    $(id).addEventListener("change", schedulePractiScoreContextApply);
  });
  ["loadedmetadata", "loadeddata"].forEach((eventName) => {
    $("primary-video").addEventListener(eventName, () => {
      scheduleSecondaryPreviewSync();
      renderLiveOverlay();
    });
    $("secondary-video").addEventListener(eventName, () => {
      scheduleSecondaryPreviewSync();
      renderLiveOverlay();
    });
  });
  $("primary-video").addEventListener("play", startOverlayLoop);
  $("primary-video").addEventListener("pause", stopOverlayLoop);
  $("primary-video").addEventListener("seeked", () => {
    activity("video.seeked", { current_time_s: $("primary-video").currentTime });
    scheduleSecondaryPreviewSync();
    renderLiveOverlay();
  });
  $("primary-video").addEventListener("timeupdate", () => {
    scheduleSecondaryPreviewSync();
    renderLiveOverlay();
  });
  document.querySelectorAll("[data-waveform-mode]").forEach((button) => {
    button.addEventListener("click", () => setWaveformMode(button.dataset.waveformMode));
  });
  $("expand-waveform").addEventListener("click", () => {
    setWaveformExpanded(!$("cockpit-root").classList.contains("waveform-expanded"));
  });
  $("zoom-waveform-out").addEventListener("click", () => setWaveformZoom(0.5));
  $("zoom-waveform-in").addEventListener("click", () => setWaveformZoom(2));
  $("amp-waveform-out").addEventListener("click", () => setWaveformAmplitude(0.5));
  $("amp-waveform-in").addEventListener("click", () => setWaveformAmplitude(2));
  $("reset-waveform-view").addEventListener("click", resetWaveformView);
  $("expand-timing").addEventListener("click", () => setTimingExpanded(true));
  $("collapse-timing").addEventListener("click", () => setTimingExpanded(false));
  $("waveform").addEventListener("pointerdown", handleWaveformPointerDown);
  $("waveform").addEventListener("pointermove", handleWaveformPointerMove);
  $("waveform").addEventListener("pointerup", handleWaveformPointerUp);
  $("waveform").addEventListener("pointercancel", handleWaveformPointerUp);
  document.addEventListener("pointermove", handleWaveformPointerMove);
  document.addEventListener("pointerup", handleWaveformPointerUp);
  document.addEventListener("pointercancel", handleWaveformPointerUp);
  document.addEventListener("lostpointercapture", handleWaveformPointerUp);
  document.addEventListener("keydown", handleKeyboardEdit);
  window.addEventListener("resize", handleViewportLayoutChange);
  window.visualViewport?.addEventListener("resize", handleViewportLayoutChange);
  window.visualViewport?.addEventListener("scroll", handleViewportLayoutChange);
  $("delete-selected").addEventListener("click", deleteSelectedShot);
  document.querySelectorAll("[data-nudge]").forEach((button) => {
    button.addEventListener("click", () => {
      if (!selectedShotId) return;
      const shot = state.project.analysis.shots.find((item) => item.id === selectedShotId);
      if (shot) {
        activity("shot.button_nudge", { shot_id: selectedShotId, delta_ms: Number(button.dataset.nudge) });
        callApi("/api/shots/move", { shot_id: selectedShotId, time_ms: shot.time_ms + Number(button.dataset.nudge) });
      }
    });
  });
  $("threshold").addEventListener("input", scheduleThresholdApply);
  ["merge-enabled", "merge-layout"].forEach((id) => {
    $(id).addEventListener("change", () => {
      syncMergePreviewStateFromControls();
      renderVideo();
      scheduleMergeApply();
    });
  });
  $("pip-size").addEventListener("input", () => {
    $("pip-size-label").textContent = `${$("pip-size").value}%`;
    syncMergePreviewStateFromControls();
    renderVideo();
    scheduleMergeApply();
  });
  ["pip-x", "pip-y"].forEach((id) => {
    $(id).addEventListener("input", () => {
      syncMergePreviewStateFromControls();
      renderVideo();
      scheduleMergeApply();
    });
  });
  document.querySelectorAll("[data-sync]").forEach((button) => {
    button.addEventListener("click", () => callApi("/api/sync", { delta_ms: Number(button.dataset.sync) }));
  });
  $("timing-event-kind").addEventListener("change", syncTimingEventLabelState);
  $("add-timing-event").addEventListener("click", addTimingEvent);
  $("video-stage").addEventListener("pointerdown", beginOverlayBadgeDrag);
  $("merge-preview-layer").addEventListener("pointerdown", beginMergePreviewDrag);
  $("custom-overlay").addEventListener("pointerdown", beginCustomOverlayDrag);
  ["badge-size"].forEach((id) => {
    $(id).addEventListener("change", () => {
      syncOverlayFontSizePreset();
      syncOverlayPreviewStateFromControls();
      renderLiveOverlay();
      scheduleOverlayApply();
    });
  });
  [
    "max-visible-shots",
    "shot-quadrant",
    "shot-direction",
    "overlay-custom-x",
    "overlay-custom-y",
    "timer-x",
    "timer-y",
    "draw-x",
    "draw-y",
    "score-x",
    "score-y",
    "bubble-width",
    "bubble-height",
    "overlay-font-family",
    "overlay-font-size",
    "overlay-font-bold",
    "overlay-font-italic",
    "show-timer",
    "show-draw",
    "show-shots",
    "show-score",
    "custom-box-enabled",
    "custom-box-mode",
    "custom-box-text",
    "custom-box-quadrant",
    "custom-box-x",
    "custom-box-y",
    "custom-box-width",
    "custom-box-height",
    "custom-box-opacity",
  ].forEach((id) => {
    const eventName = $(id).tagName === "SELECT" || $(id).type === "checkbox" ? "change" : "input";
    $(id).addEventListener(eventName, () => {
      if (id === "shot-quadrant") {
        syncOverlayCoordinateControlState();
        ensureShotQuadrantDefaults();
      }
      if (id === "custom-box-mode") syncCustomBoxModeState();
      commitOverlayControlChanges();
    });
  });
  ["custom-box-background-color", "custom-box-text-color"].forEach((id) => {
    bindOverlayColorInput($(id));
  });
  $("badge-style-grid").addEventListener("input", (event) => {
    const target = event.target;
    if (isColorInput(target)) return;
    previewOverlayControlChanges();
    scheduleOverlayApply();
  });
  $("badge-style-grid").addEventListener("change", (event) => {
    if (isColorInput(event.target)) return;
    commitOverlayControlChanges();
  });
  ["scoring-enabled", "scoring-preset"].forEach((id) => {
    $(id).addEventListener("change", scheduleScoringApply);
  });
  $("scoring-penalty-grid")?.addEventListener("input", scheduleScoringApply);
  document.querySelectorAll("[data-layout-lock-toggle]").forEach((button) => {
    button.addEventListener("click", toggleLayoutLock);
  });
  $("reset-layout")?.addEventListener("click", resetLayout);
  [
    ["resize-rail", "railWidth"],
    ["resize-sidebar", "inspectorWidth"],
    ["resize-waveform", "waveformHeight"],
  ].forEach(([id, kind]) => {
    const handle = $(id);
    handle.addEventListener("pointerdown", (event) => beginLayoutResize(kind, event));
  });
  document.addEventListener("pointermove", moveLayoutResize);
  document.addEventListener("pointerup", endLayoutResize);
  document.addEventListener("pointercancel", endLayoutResize);
  document.addEventListener("lostpointercapture", endLayoutResize);
  document.addEventListener("pointermove", moveOverlayBadgeDrag);
  document.addEventListener("pointerup", endOverlayBadgeDrag);
  document.addEventListener("pointercancel", endOverlayBadgeDrag);
  document.addEventListener("lostpointercapture", endOverlayBadgeDrag);
  document.addEventListener("pointermove", moveMergePreviewDrag);
  document.addEventListener("pointerup", endMergePreviewDrag);
  document.addEventListener("pointercancel", endMergePreviewDrag);
  document.addEventListener("lostpointercapture", endMergePreviewDrag);
  document.addEventListener("pointermove", moveCustomOverlayDrag);
  document.addEventListener("pointerup", endCustomOverlayDrag);
  document.addEventListener("pointercancel", endCustomOverlayDrag);
  document.addEventListener("lostpointercapture", endCustomOverlayDrag);
  ["overlay-style"].forEach((id) => {
    $(id).addEventListener("change", () => {
      overlayStyleMode = $(id).value;
      syncOverlayPreviewStateFromControls();
      renderLiveOverlay();
      scheduleOverlayApply();
    });
  });
  ["overlay-spacing", "overlay-margin"].forEach((id) => {
    $(id).addEventListener("input", () => {
      const value = Number($(id).value);
      if (id === "overlay-spacing") {
        overlaySpacing = value;
      } else {
        overlayMargin = value;
      }
      syncOverlayPreviewStateFromControls();
      renderLiveOverlay();
      scheduleOverlayApply();
    });
  });
  ["quality", "aspect-ratio"].forEach((id) => {
    $(id).addEventListener("change", scheduleExportLayoutApply);
  });
  $("export-preset").addEventListener("change", () => {
    activity("auto_apply.export_preset", { preset: $("export-preset").value });
    callApi("/api/export/preset", { preset: $("export-preset").value });
  });
  [
    "target-width",
    "target-height",
    "video-bitrate",
    "audio-sample-rate",
    "audio-bitrate",
  ].forEach((id) => {
    $(id).addEventListener("input", scheduleExportSettingsApply);
  });
  [
    "frame-rate",
    "video-codec",
    "audio-codec",
    "color-space",
    "ffmpeg-preset",
    "two-pass",
  ].forEach((id) => {
    $(id).addEventListener("change", scheduleExportSettingsApply);
  });
  $("export-video").addEventListener("click", async () => {
    const path = requireValue("export-path", "Output video path");
    exportPathDraft = path;
    cancelPendingExportDrafts();
    await callApi("/api/export", buildExportPayload(path));
  });
}

applyLayoutState();
setActiveTool(activeTool);
wireGlobalActivityLogging();
wireEvents();
refresh();
