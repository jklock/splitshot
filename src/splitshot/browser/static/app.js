let state = null;
let selectedShotId = null;
let activeTool = window.localStorage.getItem("splitshot.activeTool") || "project";
let overlayFrame = null;
let overlayFrameMode = null;
let waveformMode = "select";
let draggingShotId = null;
let draggingShotPointerId = null;
let pendingDragTimeMs = null;
let waveformPanDrag = null;
let waveformNavigatorDrag = null;
let timingRowEdits = new Set();
let scoringShotExpansion = new Map();
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
let timingColumnWidths = {};
let timingColumnResize = null;
let currentProjectId = null;
let exportPathDraft = "";
let projectDetailsDraft = { name: null, description: null };
let projectFolderProbeRequestId = 0;
let secondaryPreviewSyncFrame = null;
let secondaryPreviewPlayErrorKey = null;
let overlayColorCommitTimer = null;
let processingBarShowTimer = null;
let processingBarHideTimer = null;
let processingBarVisibleAtMs = 0;
let processingProgressTimer = null;
let processingProgressPercent = 0;
let activeProcessingPath = null;
let activityQueue = [];
let activityFlushTimer = null;
let activityCursor = 0;
let activityPollTimer = null;
let overlayBadgeDrag = null;
let mergePreviewDrag = null;
let textBoxDrag = null;
let exportLogLines = [];
let activeColorPickerControl = null;
let reviewStageRestoreFrame = null;
let reviewStageRestoreSecondFrame = null;
let overlayBadgeMeasureCanvas = null;
let overlayAutoBubbleCacheKey = null;
let overlayAutoBubbleCache = { width: 0, height: 0 };
let customOverlayRenderKey = "";
let pendingInspectorScrollTop = null;
let lastInspectorUserScrollTop = 0;
let lastInspectorUserScrollTs = 0;
let renderDeferredForInteraction = false;
let pendingProjectUiStatePayload = null;
let pendingMergeSourcePayloads = new Map();
let mergeSourceCommitTimers = new Map();
let interactionPreviewFrame = null;
let pendingInteractionPreview = { video: false, waveform: false, overlay: false };
let pendingSelectionFallback = null;

const OVERLAY_COLOR_COMMIT_DELAY_MS = 900;
const PROCESSING_BAR_SHOW_DELAY_MS = 180;
const PROCESSING_BAR_MIN_VISIBLE_MS = 320;
const ACTIVITY_FLUSH_DELAY_MS = 160;
const ACTIVITY_BATCH_SIZE = 48;
const ACTIVITY_POLL_INTERVAL_MS = 1000;
const INSPECTOR_COMPACT_WIDTH = 700;
const WAVEFORM_PAN_DRAG_THRESHOLD_PX = 4;
const WAVEFORM_WINDOW_HANDLE_MIN_PX = 18;
const TIMING_COLUMN_DEFAULTS = Object.freeze({
  lock: 72,
  segment: 140,
  split: 196,
  total: 108,
  action: 220,
  score: 80,
  confidence: 108,
  source: 96,
});
const TIMING_COLUMN_MIN_WIDTHS = Object.freeze({
  lock: 60,
  segment: 104,
  split: 144,
  total: 88,
  action: 140,
  score: 68,
  confidence: 92,
  source: 84,
});
const TIMING_TABLE_COLUMN_ORDER = Object.freeze({
  "timing-table": ["segment", "split", "total", "action", "score"],
  "timing-workbench-table": ["lock", "segment", "split", "total", "action", "score", "confidence", "source"],
});
const TIMING_RESIZABLE_COLUMNS = new Set(["segment", "split", "total", "action", "score", "confidence", "source"]);

const $ = (id) => document.getElementById(id);

const badgeControls = [
  ["timer_badge", "Timer Badge"],
  ["shot_badge", "Shot Badge"],
  ["current_shot_badge", "Current Shot Badge"],
  ["hit_factor_badge", "Score Badge"],
];
const OVERLAY_STACK_LOCK_CONTROLS = Object.freeze({
  timer: { lockId: "timer-lock-to-stack", xId: "timer-x", yId: "timer-y", label: "Timer badge" },
  draw: { lockId: "draw-lock-to-stack", xId: "draw-x", yId: "draw-y", label: "Draw badge" },
  score: { lockId: "score-lock-to-stack", xId: "score-x", yId: "score-y", label: "Score badge" },
});
const VALID_OVERLAY_BADGE_NAMES = new Set(badgeControls.map(([badgeName]) => badgeName));
const BADGE_FONT_SIZES = {
  XS: 10,
  S: 12,
  M: 14,
  L: 16,
  XL: 20,
};
const OVERLAY_BADGE_PADDING_X_PX = 10;
const OVERLAY_BADGE_PADDING_Y_PX = 5;
const ABOVE_FINAL_TEXT_BOX_VALUE = "above_final";
const CUSTOM_QUADRANT_VALUE = "custom";
const VALID_TOOL_IDS = new Set(["project", "scoring", "timing", "merge", "overlay", "review", "export", "metrics"]);
const VALID_WAVEFORM_MODES = new Set(["select", "add"]);
const HEX_COLOR_PATTERN = /^#?(?:[\da-f]{3}|[\da-f]{6})$/i;
const CUSTOM_COLOR_SWATCHES = [
  "#111827",
  "#1d4ed8",
  "#dc2626",
  "#047857",
  "#7c3aed",
  "#f59e0b",
  "#22c55e",
  "#0ea5e9",
  "#f97316",
  "#be123c",
  "#ffffff",
  "#d1d5db",
  "#9ca3af",
  "#4b5563",
  "#000000",
];
const DEFAULT_PROJECT_UI_STATE = Object.freeze({
  selected_shot_id: null,
  timeline_zoom: waveformZoomX,
  timeline_offset_ms: Math.round(waveformOffsetMs),
  active_tool: activeTool,
  waveform_mode: waveformMode,
  waveform_expanded: false,
  timing_expanded: false,
  layout_locked: layoutLocked,
  rail_width: Math.round(layoutSizes.railWidth),
  inspector_width: Math.round(layoutSizes.inspectorWidth),
  waveform_height: Math.round(layoutSizes.waveformHeight),
  scoring_shot_expansion: {},
  waveform_shot_amplitudes: {},
  timing_edit_shot_ids: [],
  timing_column_widths: { ...TIMING_COLUMN_DEFAULTS },
});

function normalizeProjectNameValue(value) {
  return String(value ?? "").trim() || "Untitled Project";
}

function projectDetailValue(field, project = state?.project) {
  const savedValue = field === "name"
    ? normalizeProjectNameValue(project?.name)
    : String(project?.description || "");
  const draftValue = projectDetailsDraft[field];
  return draftValue === null ? savedValue : draftValue;
}

function applyProjectDetailsDraft(payload = {}) {
  const project = state?.project;
  if (Object.prototype.hasOwnProperty.call(payload, "name")) {
    const nextNameDraft = String(payload.name ?? "");
    const savedName = normalizeProjectNameValue(project?.name);
    projectDetailsDraft.name = normalizeProjectNameValue(nextNameDraft) === savedName ? null : nextNameDraft;
    if (project) project.name = normalizeProjectNameValue(nextNameDraft);
  }
  if (Object.prototype.hasOwnProperty.call(payload, "description")) {
    const nextDescriptionDraft = String(payload.description ?? "");
    const savedDescription = String(project?.description || "");
    projectDetailsDraft.description = nextDescriptionDraft === savedDescription ? null : nextDescriptionDraft;
    if (project) project.description = nextDescriptionDraft;
  }
}

function mergeProjectDetailsDraft(project) {
  if (!project) return;
  if (projectDetailsDraft.name !== null) {
    const draftName = String(projectDetailsDraft.name);
    if (normalizeProjectNameValue(draftName) === normalizeProjectNameValue(project.name)) {
      projectDetailsDraft.name = null;
    } else {
      project.name = normalizeProjectNameValue(draftName);
    }
  }
  if (projectDetailsDraft.description !== null) {
    const draftDescription = String(projectDetailsDraft.description);
    if (draftDescription === String(project.description || "")) {
      projectDetailsDraft.description = null;
    } else {
      project.description = draftDescription;
    }
  }
}

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

function clearActivityPollTimer() {
  if (activityPollTimer === null) return;
  window.clearTimeout(activityPollTimer);
  activityPollTimer = null;
}

function appendExportLogLine(line) {
  const nextLine = String(line || "").trimEnd();
  if (!nextLine) return;
  exportLogLines.push(nextLine);
  exportLogLines = exportLogLines.slice(-500);
}

function clearCurrentExportLogState() {
  exportLogLines = [];
  if (state?.project?.export) {
    state.project.export.last_log = "";
    state.project.export.last_error = null;
  }
  renderExportLog();
}

function consumeActivityEntries(entries = []) {
  let exportLogChanged = false;
  entries.forEach((entry) => {
    if (!entry || typeof entry !== "object") return;
    const seq = Number(entry.seq || 0);
    if (seq > activityCursor) activityCursor = seq;
    if (entry.event === "/api/activity/poll") return;
    if (entry.event === "api.export.log") {
      appendExportLogLine(entry.line);
      exportLogChanged = true;
      return;
    }
    if (entry.event === "api.export.progress") {
      const nextProgress = Number(entry.progress);
      if (Number.isFinite(nextProgress)) {
        setProcessingProgress(nextProgress * 100);
        exportLogChanged = true;
      }
      return;
    }
    if (entry.event === "api.export.complete") {
      setProcessingProgress(100);
      exportLogChanged = true;
    }
  });
  if (exportLogChanged) renderExportLog();
}

async function runActivityPoll() {
  clearActivityPollTimer();
  try {
    const response = await fetch(`/api/activity/poll?after=${activityCursor}`);
    const data = await response.json();
    if (!response.ok || data.error) throw new Error(data.error || response.statusText);
    consumeActivityEntries(Array.isArray(data.entries) ? data.entries : []);
    activityCursor = Math.max(activityCursor, Number(data.cursor || 0));
  } catch (error) {
    console.warn("[splitshot] activity poll failed", error);
  } finally {
    activityPollTimer = window.setTimeout(runActivityPoll, ACTIVITY_POLL_INTERVAL_MS);
  }
}

function startActivityPolling() {
  if (activityPollTimer !== null) return;
  activityPollTimer = window.setTimeout(runActivityPoll, 0);
}

function stopActivityPolling() {
  clearActivityPollTimer();
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

function orderedShotsByTimeFromState(nextState = state) {
  return [...(nextState?.project?.analysis?.shots || [])]
    .sort((left, right) => Number(left.time_ms || 0) - Number(right.time_ms || 0));
}

function shotSelectionContext(shotId = selectedShotId, nextState = state, fallbackMode = "time") {
  if (!shotId) return null;
  const shots = orderedShotsByTimeFromState(nextState);
  const index = shots.findIndex((shot) => shot.id === shotId);
  if (index < 0) return null;
  return {
    shotId,
    timeMs: Number(shots[index].time_ms || 0),
    index,
    fallbackMode,
  };
}

function fallbackSelectedShotId(nextState, context = null) {
  const shots = orderedShotsByTimeFromState(nextState);
  if (!shots.length || !context) return null;
  if (stateHasShot(nextState, context.shotId)) return context.shotId;
  if (context.fallbackMode === "index" && Number.isFinite(Number(context.index))) {
    return shots[Math.min(Math.max(0, Number(context.index)), shots.length - 1)].id;
  }
  const targetTime = Number(context.timeMs);
  if (!Number.isFinite(targetTime)) return shots[0].id;
  return shots
    .map((shot, index) => ({ shot, index }))
    .sort((left, right) => {
      const leftDistance = Math.abs(Number(left.shot.time_ms || 0) - targetTime);
      const rightDistance = Math.abs(Number(right.shot.time_ms || 0) - targetTime);
      return leftDistance - rightDistance || left.index - right.index;
    })[0].shot.id;
}

function resolveSelectedShotId(nextState, requestedShotId = null, fallbackContext = null, alternateShotId = null) {
  if (stateHasShot(nextState, requestedShotId)) return requestedShotId;
  if (stateHasShot(nextState, alternateShotId)) return alternateShotId;
  if (requestedShotId || fallbackContext) return fallbackSelectedShotId(nextState, fallbackContext);
  return null;
}

function syncSelectedShotId(nextState = state, fallbackContext = null) {
  const requestedShotId = selectedShotId || nextState?.project?.ui_state?.selected_shot_id || null;
  selectedShotId = resolveSelectedShotId(nextState, requestedShotId, fallbackContext);
  if (nextState?.project?.ui_state) nextState.project.ui_state.selected_shot_id = selectedShotId;
  return selectedShotId;
}

function splitRowForShot(shotId) {
  return (state?.split_rows || []).find((row) => row.shot_id === shotId) || null;
}

function resolvedSplitMsForShot(shotId, shotNumber = null, absoluteTimeMs = null) {
  const splitRow = splitRowForShot(shotId);
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

function scoreTokenColor(token) {
  const normalizedToken = String(token || "").trim();
  if (!normalizedToken) return null;
  return state?.project?.overlay?.scoring_colors?.[normalizedToken] || null;
}

function scoreBadgeTokens(shot) {
  if (!state?.project?.scoring?.enabled || !shot?.score) return [];
  const tokens = [{ text: shot.score.letter, color: scoreTokenColor(shot.score.letter) }];
  Object.entries(shot.score.penalty_counts || {})
    .filter(([, value]) => Number(value || 0) > 0)
    .forEach(([fieldId, value]) => {
      const token = penaltyFieldLabel(fieldId);
      tokens.push({
        text: token,
        color: scoreTokenColor(token),
        countText: ` x${formatNumber(value, 1)}`,
      });
    });
  return tokens;
}

function formatShotBadgeSuffix(shot) {
  const tokens = scoreBadgeTokens(shot);
  if (tokens.length === 0) return "";
  return ` ${tokens.map((token) => `${token.text}${token.countText || ""}`).join(" ")}`;
}

function shotBadgeBaseText(shotNumber, splitText, intervalLabel = "") {
  const normalizedLabel = String(intervalLabel || "").trim();
  if (!normalizedLabel || normalizedLabel === "Split") {
    return `Shot ${shotNumber} ${splitText}`;
  }
  return `Shot ${shotNumber} ${normalizedLabel} ${splitText}`;
}

function scoreBadgeContent(shot, shotNumber, splitText, intervalLabel = "") {
  const baseText = shotBadgeBaseText(shotNumber, splitText, intervalLabel);
  const tokens = scoreBadgeTokens(shot);
  if (tokens.length === 0) {
    return { text: baseText, runs: null };
  }
  const firstTokenGap = "  ";
  const runs = [
    { text: baseText },
    { text: firstTokenGap },
    { text: tokens[0].text, color: tokens[0].color },
  ];
  let text = `${baseText}${firstTokenGap}${tokens[0].text}`;
  tokens.slice(1).forEach((token) => {
    runs.push({ text: " " });
    runs.push({ text: token.text, color: token.color });
    runs.push({ text: token.countText || "" });
    text += ` ${token.text}${token.countText || ""}`;
  });
  return { text, runs };
}

function scoringColorOptions() {
  const options = Array.isArray(state?.scoring_summary?.scoring_color_options)
    ? state.scoring_summary.scoring_color_options
    : [];
  if (options.length > 0) return options;
  const fallback = [];
  const seen = new Set();
  (state?.scoring_summary?.score_options || []).forEach((token) => {
    const key = String(token || "").trim();
    if (!key || seen.has(key)) return;
    seen.add(key);
    fallback.push({ key, label: key, description: "Score token" });
  });
  (state?.scoring_summary?.penalty_fields || []).forEach((field) => {
    const key = penaltyFieldLabel(field.id, field.label);
    if (!key || seen.has(key)) return;
    seen.add(key);
    fallback.push({ key, label: key, description: field.label || key });
  });
  return fallback;
}

function defaultScoreLetter() {
  const options = Array.isArray(state?.scoring_summary?.score_options)
    ? state.scoring_summary.score_options
    : [];
  return options[0] || "A";
}

function formatConfidenceValue(confidence) {
  if (confidence === null || confidence === undefined || confidence === "") return "Manual";
  const numeric = Number(confidence);
  if (!Number.isFinite(numeric)) return String(confidence);
  const percent = numeric <= 1 ? numeric * 100 : numeric;
  const clamped = Math.max(0, Math.min(100, percent));
  return `${clamped.toFixed(1)}%`;
}

function isLowConfidence(confidence, source = "") {
  if (String(source || "").toLowerCase() === "manual") return false;
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
  withPreservedScrollState([list], () => {
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

function captureScrollState(elements = []) {
  return elements
    .filter((element) => element instanceof HTMLElement)
    .map((element) => ({
      element,
      scrollTop: element.scrollTop,
      scrollLeft: element.scrollLeft,
    }));
}

function restoreScrollState(states = []) {
  states.forEach(({ element, scrollTop, scrollLeft }) => {
    if (!(element instanceof HTMLElement)) return;
    element.scrollTop = scrollTop;
    element.scrollLeft = scrollLeft;
  });
}

function withPreservedScrollState(elements, callback) {
  const targets = Array.isArray(elements) ? elements : [elements];
  const scrollState = captureScrollState(targets);
  const result = callback();
  restoreScrollState(scrollState);
  return result;
}

function scrollRenderTargets() {
  return [
    document.querySelector(".tool-nav"),
    document.querySelector(".inspector"),
  ].filter((element) => element instanceof HTMLElement);
}

function rememberInspectorScrollPosition() {
  const inspector = document.querySelector(".inspector");
  if (!(inspector instanceof HTMLElement)) return;
  lastInspectorUserScrollTop = inspector.scrollTop;
  lastInspectorUserScrollTs = Date.now();
}

function queueInspectorScrollRestore() {
  const inspector = document.querySelector(".inspector");
  if (!(inspector instanceof HTMLElement)) return;
  const currentScrollTop = inspector.scrollTop;
  const hasRecentScroll = (Date.now() - lastInspectorUserScrollTs) <= 2000;
  if (hasRecentScroll && lastInspectorUserScrollTop > currentScrollTop + 24) {
    pendingInspectorScrollTop = lastInspectorUserScrollTop;
    return;
  }
  pendingInspectorScrollTop = currentScrollTop;
}

function flushPendingInspectorScrollRestore() {
  if (pendingInspectorScrollTop === null) return;
  const inspector = document.querySelector(".inspector");
  if (inspector instanceof HTMLElement) {
    inspector.scrollTop = pendingInspectorScrollTop;
  }
  pendingInspectorScrollTop = null;
}

function hasActivePointerInteraction() {
  return Boolean(
    activeResize
      || timingColumnResize
      || overlayBadgeDrag
      || mergePreviewDrag
      || textBoxDrag
      || draggingShotId
      || waveformPanDrag
      || waveformNavigatorDrag,
  );
}

function requestRender() {
  if (hasActivePointerInteraction()) {
    renderDeferredForInteraction = true;
    return;
  }
  renderDeferredForInteraction = false;
  render();
}

function flushDeferredRender() {
  if (!renderDeferredForInteraction || hasActivePointerInteraction()) return;
  renderDeferredForInteraction = false;
  render();
}

function scheduleInteractionPreviewRender({ video = false, waveform = false, overlay = false } = {}) {
  pendingInteractionPreview.video = pendingInteractionPreview.video || Boolean(video);
  pendingInteractionPreview.waveform = pendingInteractionPreview.waveform || Boolean(waveform);
  pendingInteractionPreview.overlay = pendingInteractionPreview.overlay || Boolean(overlay);
  if (interactionPreviewFrame !== null) return;
  interactionPreviewFrame = window.requestAnimationFrame(() => {
    interactionPreviewFrame = null;
    flushInteractionPreviewRender();
  });
}

function flushInteractionPreviewRender() {
  if (interactionPreviewFrame !== null) {
    window.cancelAnimationFrame(interactionPreviewFrame);
    interactionPreviewFrame = null;
  }
  const pending = pendingInteractionPreview;
  pendingInteractionPreview = { video: false, waveform: false, overlay: false };
  if (!pending.video && !pending.waveform && !pending.overlay) return;
  if (pending.video) renderVideo();
  if (pending.waveform) renderWaveform();
  if (pending.overlay) renderLiveOverlay();
}

function syncControlValue(control, value) {
  if (!control || controlIsActive(control)) return;
  const nextValue = value === null || value === undefined ? "" : String(value);
  if (isColorInput(control)) {
    setColorControlValue(control, nextValue || "#000000");
    syncOverlayHexControl(control);
    if (colorControlButton(control) === activeColorPickerControl) {
      syncColorPickerModal(nextValue || "#000000");
    }
    return;
  }
  if (control.value !== nextValue) control.value = nextValue;
}

function syncControlChecked(control, checked) {
  if (!control || controlIsActive(control)) return;
  const nextChecked = Boolean(checked);
  if (control.checked !== nextChecked) control.checked = nextChecked;
}

function opacityPercentValue(value) {
  return clampNumber(Math.round(clampNumber(Number(value) || 0, 0, 1) * 100), 0, 100);
}

function opacityValueFromPercent(value) {
  return clampNumber((clampNumber(Number(value) || 0, 0, 100)) / 100, 0, 1);
}

function syncOpacityPercentControl(control, opacity) {
  if (!(control instanceof HTMLInputElement) || controlIsActive(control)) return;
  const nextValue = String(opacityPercentValue(opacity));
  if (control.value !== nextValue) control.value = nextValue;
}

function bindOpacityPercentPair(rangeInput, percentInput) {
  if (!(rangeInput instanceof HTMLInputElement) || !(percentInput instanceof HTMLInputElement)) return;
  if (percentInput.dataset.opacityPairBound === "true") return;
  percentInput.dataset.opacityPairBound = "true";
  rangeInput.dataset.opacityPairBound = "true";
  const syncPercent = () => syncOpacityPercentControl(percentInput, rangeInput.value);
  rangeInput.addEventListener("input", syncPercent);
  rangeInput.addEventListener("change", syncPercent);
  const syncRange = () => {
    rangeInput.value = opacityValueFromPercent(percentInput.value).toFixed(2);
  };
  percentInput.addEventListener("input", syncRange);
  percentInput.addEventListener("change", syncRange);
  percentInput.addEventListener("blur", syncPercent);
  syncPercent();
}

function roundedRect(rect) {
  if (!rect) return null;
  return {
    left: Math.round(rect.left || 0),
    top: Math.round(rect.top || 0),
    width: Math.max(1, Math.round(rect.width || 0)),
    height: Math.max(1, Math.round(rect.height || 0)),
  };
}

function isColorInput(control) {
  return control instanceof HTMLButtonElement && control.classList.contains("color-swatch-button");
}

function fileName(path) {
  if (!path) return "No Video Selected";
  const normalized = path.split("\\").join("/");
  const base = normalized.split("/").filter(Boolean).pop() || path;
  return base.replace(/^[a-f0-9]{32}_/i, "");
}

function mediaCacheToken() {
  return state?.media?.cache_token || "";
}

function buildMediaUrl(basePath, sourcePath = "") {
  const params = new URLSearchParams();
  if (sourcePath) params.set("v", sourcePath);
  const token = mediaCacheToken();
  if (token) params.set("mt", token);
  const query = params.toString();
  return query ? `${basePath}?${query}` : basePath;
}

function colorControlButton(control) {
  if (isColorInput(control)) return control;
  if (!(control instanceof Element)) return null;
  return control.closest(".color-field")?.querySelector(".color-swatch-button") || null;
}

function colorControlLabel(control) {
  const field = colorControlButton(control)?.closest(".color-field");
  return field?.querySelector(".style-card-label, .score-color-label")?.textContent?.trim() || "Color";
}

function readColorControlValue(control) {
  const button = colorControlButton(control);
  return normalizeHexColor(button?.dataset.colorValue || "") || "#000000";
}

function setColorControlValue(control, value) {
  const button = colorControlButton(control);
  if (!button) return;
  const normalized = normalizeHexColor(value) || "#000000";
  button.dataset.colorValue = normalized;
  button.style.setProperty("--swatch-color", normalized);
  button.setAttribute("aria-label", `${button.dataset.colorLabel || colorControlLabel(button)} ${normalized.toUpperCase()}`);
}

function rgbToHex(red, green, blue) {
  return `#${[red, green, blue].map((value) => Math.round(clampNumber(value, 0, 255)).toString(16).padStart(2, "0")).join("")}`;
}

function rgbToHsl(red, green, blue) {
  const r = clampNumber(red, 0, 255) / 255;
  const g = clampNumber(green, 0, 255) / 255;
  const b = clampNumber(blue, 0, 255) / 255;
  const max = Math.max(r, g, b);
  const min = Math.min(r, g, b);
  const lightness = (max + min) / 2;
  if (max === min) {
    return { h: 0, s: 0, l: lightness * 100 };
  }
  const delta = max - min;
  const saturation = lightness > 0.5 ? delta / (2 - max - min) : delta / (max + min);
  let hue = 0;
  switch (max) {
    case r:
      hue = ((g - b) / delta) + (g < b ? 6 : 0);
      break;
    case g:
      hue = ((b - r) / delta) + 2;
      break;
    default:
      hue = ((r - g) / delta) + 4;
      break;
  }
  return {
    h: (hue * 60) % 360,
    s: saturation * 100,
    l: lightness * 100,
  };
}

function hexToHsl(hex) {
  return rgbToHsl(...hexToRgb(hex));
}

function hueToRgb(channelA, channelB, hue) {
  let nextHue = hue;
  if (nextHue < 0) nextHue += 1;
  if (nextHue > 1) nextHue -= 1;
  if (nextHue < 1 / 6) return channelA + ((channelB - channelA) * 6 * nextHue);
  if (nextHue < 1 / 2) return channelB;
  if (nextHue < 2 / 3) return channelA + ((channelB - channelA) * ((2 / 3) - nextHue) * 6);
  return channelA;
}

function hslToRgb(hue, saturation, lightness) {
  const h = ((Number(hue) || 0) % 360 + 360) % 360 / 360;
  const s = clampNumber(Number(saturation) || 0, 0, 100) / 100;
  const l = clampNumber(Number(lightness) || 0, 0, 100) / 100;
  if (s === 0) {
    const grayscale = Math.round(l * 255);
    return [grayscale, grayscale, grayscale];
  }
  const channelB = l < 0.5 ? l * (1 + s) : l + s - (l * s);
  const channelA = 2 * l - channelB;
  return [
    Math.round(hueToRgb(channelA, channelB, h + (1 / 3)) * 255),
    Math.round(hueToRgb(channelA, channelB, h) * 255),
    Math.round(hueToRgb(channelA, channelB, h - (1 / 3)) * 255),
  ];
}

function hslToHex(hue, saturation, lightness) {
  return rgbToHex(...hslToRgb(hue, saturation, lightness));
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
  const normalized = readColorControlValue(colorInput);
  if (!controlIsActive(hexInput) && hexInput.value !== normalized.toUpperCase()) {
    hexInput.value = normalized.toUpperCase();
  }
  hexInput.classList.remove("invalid");
}

function updateColorFromHexInput(hexInput, { commit = false } = {}) {
  const colorInput = hexInput?.closest(".color-field")?.querySelector(".color-swatch-button");
  if (!isColorInput(colorInput) || !(hexInput instanceof HTMLInputElement)) return;
  const normalized = normalizeHexColor(hexInput.value);
  if (!normalized) {
    hexInput.classList.add("invalid");
    if (commit) syncOverlayHexControl(colorInput);
    return;
  }
  hexInput.classList.remove("invalid");
  const changed = readColorControlValue(colorInput) !== normalized;
  setColorControlValue(colorInput, normalized);
  syncOverlayHexControl(colorInput);
  if (!changed) {
    if (colorInput === activeColorPickerControl) syncColorPickerModal(normalized);
    if (commit) scheduleOverlayColorCommit();
    return;
  }
  const textBoxCard = colorInput.closest(".text-box-card");
  const textBoxField = colorInput.dataset.textBoxField || "";
  if (textBoxCard?.dataset.boxId && textBoxField) {
    setOverlayTextBoxField(textBoxCard.dataset.boxId, textBoxField, normalized, { rerender: false });
  } else {
    previewOverlayControlChanges();
  }
  if (colorInput === activeColorPickerControl) syncColorPickerModal(normalized);
  if (commit) {
    scheduleOverlayColorCommit();
  }
}

function colorPickerModal() {
  return $("color-picker-modal");
}

function syncColorPickerModal(hexValue = null) {
  if (!activeColorPickerControl) return;
  const normalized = normalizeHexColor(hexValue || readColorControlValue(activeColorPickerControl)) || "#000000";
  const { h, s, l } = hexToHsl(normalized);
  syncControlValue($("color-picker-hue"), Math.round(h));
  syncControlValue($("color-picker-saturation"), Math.round(s));
  syncControlValue($("color-picker-lightness"), Math.round(l));
  const hexInput = $("color-picker-hex");
  if (hexInput instanceof HTMLInputElement && !controlIsActive(hexInput)) {
    hexInput.value = normalized.toUpperCase();
    hexInput.classList.remove("invalid");
  }
  const preview = $("color-picker-preview");
  if (preview) preview.style.setProperty("--picker-color", normalized);
  const current = $("color-picker-current");
  if (current) current.textContent = normalized.toUpperCase();
  const target = $("color-picker-target");
  if (target) target.textContent = colorControlLabel(activeColorPickerControl);
}

function applyColorControlValue(control, value, { queueCommit = false } = {}) {
  const colorControl = colorControlButton(control);
  const normalized = normalizeHexColor(value);
  if (!colorControl || !normalized) return;
  const changed = readColorControlValue(colorControl) !== normalized;
  setColorControlValue(colorControl, normalized);
  syncOverlayHexControl(colorControl);
  const textBoxCard = colorControl.closest(".text-box-card");
  const textBoxField = colorControl.dataset.textBoxField || "";
  if (changed) {
    if (textBoxCard?.dataset.boxId && textBoxField) {
      setOverlayTextBoxField(textBoxCard.dataset.boxId, textBoxField, normalized, { rerender: false });
    } else {
      previewOverlayControlChanges();
    }
  }
  if (colorControl === activeColorPickerControl) syncColorPickerModal(normalized);
  if (queueCommit) scheduleOverlayColorCommit();
}

function openColorPicker(control) {
  const colorControl = colorControlButton(control);
  const modal = colorPickerModal();
  if (!colorControl || !modal) return;
  activeColorPickerControl = colorControl;
  modal.hidden = false;
  renderColorPickerSwatches();
  syncColorPickerModal(readColorControlValue(colorControl));
}

function closeColorPicker({ commit = true } = {}) {
  const modal = colorPickerModal();
  if (!modal || modal.hidden) {
    activeColorPickerControl = null;
    return;
  }
  if (commit) flushOverlayColorCommit();
  modal.hidden = true;
  activeColorPickerControl = null;
}

function updateColorPickerFromSliders({ commit = false } = {}) {
  if (!activeColorPickerControl) return;
  const hue = Number($("color-picker-hue")?.value || 0);
  const saturation = Number($("color-picker-saturation")?.value || 0);
  const lightness = Number($("color-picker-lightness")?.value || 0);
  const normalized = hslToHex(hue, saturation, lightness);
  applyColorControlValue(activeColorPickerControl, normalized, { queueCommit: true });
  if (commit) flushOverlayColorCommit();
}

function updateColorPickerFromHexInput({ commit = false } = {}) {
  if (!activeColorPickerControl) return;
  const hexInput = $("color-picker-hex");
  if (!(hexInput instanceof HTMLInputElement)) return;
  const normalized = normalizeHexColor(hexInput.value);
  if (!normalized) {
    hexInput.classList.add("invalid");
    return;
  }
  hexInput.classList.remove("invalid");
  applyColorControlValue(activeColorPickerControl, normalized, { queueCommit: true });
  if (commit) flushOverlayColorCommit();
}

function renderColorPickerSwatches() {
  const container = $("color-picker-swatches");
  if (!container || container.childElementCount > 0) return;
  CUSTOM_COLOR_SWATCHES.forEach((hex) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "color-picker-swatch";
    button.dataset.colorValue = hex;
    button.style.setProperty("--picker-color", hex);
    button.setAttribute("aria-label", `Use ${hex.toUpperCase()}`);
    button.addEventListener("click", () => {
      applyColorControlValue(activeColorPickerControl, hex, { queueCommit: true });
      flushOverlayColorCommit();
    });
    container.appendChild(button);
  });
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

function clearProcessingProgressTimer() {
  if (processingProgressTimer === null) return;
  window.clearInterval(processingProgressTimer);
  processingProgressTimer = null;
}

function setProcessingProgress(percent, options = {}) {
  const allowDecrease = Boolean(options.allowDecrease);
  const nextPercent = clampNumber(Number(percent) || 0, 0, 100);
  processingProgressPercent = allowDecrease
    ? nextPercent
    : Math.max(processingProgressPercent, nextPercent);
  const fill = $("processing-progress-fill");
  const label = $("processing-percent");
  if (fill) fill.style.width = `${processingProgressPercent}%`;
  if (label) label.textContent = `${Math.round(processingProgressPercent)}%`;
}

function progressProfileForPath(path) {
  if (path === "/api/export") return { ceiling: 99, step: 4 };
  if (path === "/api/files/practiscore" || path === "/api/project/practiscore") return { ceiling: 95, step: 15 };
  if (path === "/api/project/save") return { ceiling: 92, step: 18 };
  if (path === "/api/import/primary" || path === "/api/files/primary") return { ceiling: 95, step: 12 };
  if (path === "/api/import/secondary" || path === "/api/import/merge" || path === "/api/files/merge") {
    return { ceiling: 95, step: 16 };
  }
  return { ceiling: 90, step: 20 };
}

function startProcessingProgress(path) {
  activeProcessingPath = path;
  clearProcessingProgressTimer();
  setProcessingProgress(0, { allowDecrease: true });
  if (path === "/api/export") return;
  const profile = progressProfileForPath(path);
  processingProgressTimer = window.setInterval(() => {
    const next = Math.min(profile.ceiling, processingProgressPercent + profile.step);
    if (next !== processingProgressPercent) setProcessingProgress(next);
  }, 1000);
}

function stopProcessingProgress(finalPercent = 100) {
  clearProcessingProgressTimer();
  activeProcessingPath = null;
  setProcessingProgress(finalPercent, { allowDecrease: true });
}

function hideProcessingBarNow(finalMessage = "Ready.") {
  const bar = $("processing-bar");
  clearProcessingBarShowTimer();
  clearProcessingBarHideTimer();
  clearProcessingProgressTimer();
  processingBarVisibleAtMs = 0;
  $("processing-message").textContent = finalMessage;
  $("processing-detail").textContent = "Ready";
  setProcessingProgress(0, { allowDecrease: true });
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
  const statusCopy = $("status-copy");
  if (statusCopy) statusCopy.textContent = message;
  const inspectorStatusCopy = $("inspector-status-copy");
  if (inspectorStatusCopy) inspectorStatusCopy.textContent = message;
  const processingMessage = $("processing-message");
  if (processingMessage) processingMessage.textContent = message;
  activity("ui.status", { message });
}

function beginProcessing(message, detail = "Working locally", path = null) {
  busyCount += 1;
  if (path === "/api/export") {
    clearCurrentExportLogState();
  }
  if (busyCount === 1) startProcessingProgress(path);
  scheduleProcessingBarShow(message, detail);
  activity("ui.processing.start", { message, detail, busy_count: busyCount });
  return (finalMessage = "Ready.") => {
    busyCount = Math.max(0, busyCount - 1);
    activity("ui.processing.finish", { message: finalMessage, busy_count: busyCount });
    if (busyCount === 0) {
      stopProcessingProgress(100);
      scheduleProcessingBarHide(finalMessage);
    }
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

function normalizedUiBooleanMap(data) {
  if (!data || typeof data !== "object" || Array.isArray(data)) return {};
  return Object.fromEntries(
    Object.entries(data)
      .map(([key, value]) => [String(key || "").trim(), Boolean(value)])
      .filter(([key]) => Boolean(key)),
  );
}

function normalizedUiFloatMap(data, minimum = 0) {
  if (!data || typeof data !== "object" || Array.isArray(data)) return {};
  return Object.fromEntries(
    Object.entries(data)
      .map(([key, value]) => [String(key || "").trim(), Number(value)])
      .filter(([key, value]) => Boolean(key) && Number.isFinite(value) && value >= minimum),
  );
}

function normalizedUiStringList(data) {
  if (!Array.isArray(data)) return [];
  return data
    .map((value) => String(value || "").trim())
    .filter(Boolean);
}

function resolvedTimingColumnWidths(data = {}) {
  const resolved = {};
  Object.entries(TIMING_COLUMN_DEFAULTS).forEach(([columnId, defaultWidth]) => {
    const requestedWidth = Number(data?.[columnId]);
    const minimumWidth = TIMING_COLUMN_MIN_WIDTHS[columnId] || 72;
    resolved[columnId] = Number.isFinite(requestedWidth)
      ? Math.max(minimumWidth, Math.round(requestedWidth))
      : defaultWidth;
  });
  return resolved;
}

function timingGridTemplate(tableId) {
  const columns = TIMING_TABLE_COLUMN_ORDER[tableId] || [];
  const widths = resolvedTimingColumnWidths(timingColumnWidths);
  return columns.map((columnId) => `${widths[columnId] || TIMING_COLUMN_DEFAULTS[columnId] || 96}px`).join(" ");
}

function applyTimingTableColumns(table) {
  if (!table) return;
  if (window.innerWidth <= 680) {
    table.style.removeProperty("grid-template-columns");
    return;
  }
  const template = timingGridTemplate(table.id);
  if (template) table.style.gridTemplateColumns = template;
}

function syncTimingTableColumns() {
  applyTimingTableColumns($("timing-table"));
  applyTimingTableColumns($("timing-workbench-table"));
}

function beginTimingColumnResize(tableId, columnId, event) {
  if (!TIMING_RESIZABLE_COLUMNS.has(columnId)) return;
  timingColumnResize = {
    tableId,
    columnId,
    pointerId: event.pointerId,
    startX: event.clientX,
    startWidth: resolvedTimingColumnWidths(timingColumnWidths)[columnId] || TIMING_COLUMN_DEFAULTS[columnId] || 96,
    target: event.currentTarget,
  };
  capturePointer(timingColumnResize.target, event.pointerId);
  document.body.classList.add("resizing-layout");
  activity("timing.column.resize.start", { table_id: tableId, column_id: columnId });
}

function moveTimingColumnResize(event) {
  if (!timingColumnResize) return;
  if (event.pointerId !== undefined && timingColumnResize.pointerId !== undefined && event.pointerId !== timingColumnResize.pointerId) return;
  const minimumWidth = TIMING_COLUMN_MIN_WIDTHS[timingColumnResize.columnId] || 72;
  const nextWidth = Math.max(minimumWidth, Math.round(timingColumnResize.startWidth + (event.clientX - timingColumnResize.startX)));
  timingColumnWidths = {
    ...resolvedTimingColumnWidths(timingColumnWidths),
    [timingColumnResize.columnId]: nextWidth,
  };
  syncTimingTableColumns();
}

function endTimingColumnResize(event) {
  if (!timingColumnResize) return;
  if (event.pointerId !== undefined && timingColumnResize.pointerId !== undefined && event.pointerId !== timingColumnResize.pointerId) return;
  releasePointer(timingColumnResize.target, timingColumnResize.pointerId);
  activity("timing.column.resize.commit", {
    table_id: timingColumnResize.tableId,
    column_id: timingColumnResize.columnId,
    width: timingColumnWidths[timingColumnResize.columnId],
  });
  timingColumnResize = null;
  document.body.classList.remove("resizing-layout");
  syncLocalProjectUiState();
  scheduleProjectUiStateApply();
}

function normalizeProjectUiState(uiState = {}) {
  const normalizedActiveTool = VALID_TOOL_IDS.has(String(uiState.active_tool || DEFAULT_PROJECT_UI_STATE.active_tool))
    ? String(uiState.active_tool || DEFAULT_PROJECT_UI_STATE.active_tool)
    : DEFAULT_PROJECT_UI_STATE.active_tool;
  const normalizedWaveformMode = VALID_WAVEFORM_MODES.has(String(uiState.waveform_mode || DEFAULT_PROJECT_UI_STATE.waveform_mode))
    ? String(uiState.waveform_mode || DEFAULT_PROJECT_UI_STATE.waveform_mode)
    : DEFAULT_PROJECT_UI_STATE.waveform_mode;
  const rawSelectedShotId = uiState.selected_shot_id;
  return {
    selected_shot_id: rawSelectedShotId === null || rawSelectedShotId === undefined || String(rawSelectedShotId).trim() === ""
      ? null
      : String(rawSelectedShotId),
    timeline_zoom: clamp(Number(uiState.timeline_zoom ?? DEFAULT_PROJECT_UI_STATE.timeline_zoom) || DEFAULT_PROJECT_UI_STATE.timeline_zoom, 1, 200),
    timeline_offset_ms: Math.max(0, Math.round(Number(uiState.timeline_offset_ms ?? DEFAULT_PROJECT_UI_STATE.timeline_offset_ms) || 0)),
    active_tool: normalizedActiveTool,
    waveform_mode: normalizedWaveformMode,
    waveform_expanded: Boolean(uiState.waveform_expanded ?? DEFAULT_PROJECT_UI_STATE.waveform_expanded),
    timing_expanded: Boolean(uiState.timing_expanded ?? DEFAULT_PROJECT_UI_STATE.timing_expanded),
    layout_locked: Boolean(uiState.layout_locked ?? DEFAULT_PROJECT_UI_STATE.layout_locked),
    rail_width: clamp(Math.round(Number(uiState.rail_width ?? DEFAULT_PROJECT_UI_STATE.rail_width) || DEFAULT_PROJECT_UI_STATE.rail_width), 48, 72),
    inspector_width: Math.max(320, Math.round(Number(uiState.inspector_width ?? DEFAULT_PROJECT_UI_STATE.inspector_width) || DEFAULT_PROJECT_UI_STATE.inspector_width)),
    waveform_height: Math.max(112, Math.round(Number(uiState.waveform_height ?? DEFAULT_PROJECT_UI_STATE.waveform_height) || DEFAULT_PROJECT_UI_STATE.waveform_height)),
    scoring_shot_expansion: normalizedUiBooleanMap(uiState.scoring_shot_expansion),
    waveform_shot_amplitudes: normalizedUiFloatMap(uiState.waveform_shot_amplitudes, 0.25),
    timing_edit_shot_ids: normalizedUiStringList(uiState.timing_edit_shot_ids),
    timing_column_widths: resolvedTimingColumnWidths(normalizedUiFloatMap(uiState.timing_column_widths, 48)),
  };
}

function mergeProjectUiState(remoteUiState = {}, localUiState = {}) {
  return normalizeProjectUiState({
    ...normalizeProjectUiState(remoteUiState),
    ...normalizeProjectUiState(localUiState),
  });
}

function readProjectUiStatePayload() {
  const root = $("cockpit-root");
  return normalizeProjectUiState({
    selected_shot_id: selectedShotId,
    timeline_zoom: waveformZoomX,
    timeline_offset_ms: Math.round(waveformOffsetMs),
    active_tool: activeTool,
    waveform_mode: waveformMode,
    waveform_expanded: Boolean(root?.classList.contains("waveform-expanded")),
    timing_expanded: Boolean(root?.classList.contains("timing-expanded")),
    layout_locked: layoutLocked,
    rail_width: Math.round(layoutSizes.railWidth),
    inspector_width: Math.round(layoutSizes.inspectorWidth),
    waveform_height: Math.round(layoutSizes.waveformHeight),
    scoring_shot_expansion: Object.fromEntries(
      [...scoringShotExpansion.entries()].filter(([shotId]) => Boolean(String(shotId || "").trim())),
    ),
    waveform_shot_amplitudes: { ...waveformShotAmplitudeById },
    timing_edit_shot_ids: [...timingRowEdits].filter(Boolean),
    timing_column_widths: { ...resolvedTimingColumnWidths(timingColumnWidths) },
  });
}

function syncLocalProjectUiState(payload = readProjectUiStatePayload()) {
  const normalized = normalizeProjectUiState(payload);
  if (state?.project) state.project.ui_state = normalized;
  return normalized;
}

function applyProjectUiState(uiState = DEFAULT_PROJECT_UI_STATE) {
  const normalized = normalizeProjectUiState(uiState);
  selectedShotId = normalized.selected_shot_id;
  waveformZoomX = normalized.timeline_zoom;
  waveformOffsetMs = normalized.timeline_offset_ms;
  layoutLocked = normalized.layout_locked;
  layoutSizes = {
    railWidth: normalized.rail_width,
    inspectorWidth: normalized.inspector_width,
    waveformHeight: normalized.waveform_height,
  };
  window.localStorage.setItem("splitshot.waveform.zoomX", String(waveformZoomX));
  window.localStorage.setItem("splitshot.waveform.offsetMs", String(Math.round(waveformOffsetMs)));
  window.localStorage.setItem("splitshot.layoutLocked", String(layoutLocked));
  window.localStorage.setItem("splitshot.layout.railWidth", String(layoutSizes.railWidth));
  window.localStorage.setItem("splitshot.layout.inspectorWidth", String(layoutSizes.inspectorWidth));
  window.localStorage.setItem("splitshot.layout.waveformHeight", String(layoutSizes.waveformHeight));
  waveformShotAmplitudeById = { ...normalized.waveform_shot_amplitudes };
  scoringShotExpansion = new Map(Object.entries(normalized.scoring_shot_expansion));
  timingRowEdits = new Set(normalized.timing_edit_shot_ids);
  timingColumnWidths = resolvedTimingColumnWidths(normalized.timing_column_widths);
  setActiveTool(normalized.active_tool, { persistUiState: false });
  setWaveformMode(normalized.waveform_mode, { persistUiState: false });
  setWaveformExpanded(normalized.waveform_expanded, { persistUiState: false });
  setTimingExpanded(normalized.timing_expanded, { persistUiState: false });
  if (state?.project) state.project.ui_state = normalized;
  return normalized;
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

function mergeSourcePositionPayload(sourceId, source) {
  return {
    source_id: sourceId,
    pip_size_percent: currentPipSizePercent(source, currentPipSizePercent()),
    pip_x: normalizedCoordinateValue(source?.pip_x) ?? 1,
    pip_y: normalizedCoordinateValue(source?.pip_y) ?? 1,
  };
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

function createOverlayTextBoxId() {
  const generated = window.crypto?.randomUUID?.();
  if (generated) return generated.replace(/-/g, "");
  return `textbox-${Date.now().toString(36)}-${Math.random().toString(16).slice(2, 10)}`;
}

function overlayTextBoxAutoSize(box) {
  const text = overlayTextBoxDisplayText(box).trim();
  if (!text) return { width: 0, height: 0 };
  const measurement = measureOverlayBadgeContent(text);
  return {
    width: Math.ceil(measurement.width + (OVERLAY_BADGE_PADDING_X_PX * 2)),
    height: Math.ceil(measurement.height + (OVERLAY_BADGE_PADDING_Y_PX * 2)),
  };
}

function normalizeOverlayTextBox(box = {}, index = 0) {
  const normalizedX = normalizedCoordinateValue(box.x);
  const normalizedY = normalizedCoordinateValue(box.y);
  const source = box.source === "imported_summary" ? "imported_summary" : "manual";
  const validQuadrants = new Set([
    ABOVE_FINAL_TEXT_BOX_VALUE,
    "top_left",
    "top_middle",
    "top_right",
    "middle_left",
    "middle_middle",
    "middle_right",
    "bottom_left",
    "bottom_middle",
    "bottom_right",
    CUSTOM_QUADRANT_VALUE,
  ]);
  const fallbackQuadrant = source === "imported_summary" ? ABOVE_FINAL_TEXT_BOX_VALUE : "top_left";
  const requestedQuadrant = validQuadrants.has(box.quadrant) ? box.quadrant : fallbackQuadrant;
  const usesExplicitCoordinates = requestedQuadrant === CUSTOM_QUADRANT_VALUE || normalizedX !== null || normalizedY !== null;
  let width = Math.max(0, Number(box.width || 0));
  let height = Math.max(0, Number(box.height || 0));
  if (source === "imported_summary" && (width <= 0 || height <= 0)) {
    const autoSize = overlayTextBoxAutoSize({ ...box, source, text: String(box.text || "") });
    if (width <= 0 && autoSize.width > 0) width = autoSize.width;
    if (height <= 0 && autoSize.height > 0) height = autoSize.height;
  }
  return {
    id: box.id || createOverlayTextBoxId(),
    enabled: Boolean(box.enabled ?? true),
    source,
    text: String(box.text || "").slice(0, 500),
    quadrant: usesExplicitCoordinates ? CUSTOM_QUADRANT_VALUE : requestedQuadrant,
    x: usesExplicitCoordinates ? normalizedX ?? 0.5 : null,
    y: usesExplicitCoordinates ? normalizedY ?? 0.5 : null,
    background_color: normalizeHexColor(box.background_color || "#000000") || "#000000",
    text_color: normalizeHexColor(box.text_color || "#ffffff") || "#ffffff",
    opacity: clamp(Number(box.opacity ?? 0.9), 0, 1),
    width,
    height,
    order: Number(box.order ?? index),
  };
}

function overlayTextBoxes() {
  if (!state?.project?.overlay) return [];
  const boxes = Array.isArray(state.project.overlay.text_boxes) ? state.project.overlay.text_boxes : [];
  if (boxes.length > 0) {
    return boxes.map((box, index) => normalizeOverlayTextBox(box, index));
  }
  const overlay = state.project.overlay;
  const hasLegacyBox = Boolean(
    overlay.custom_box_enabled
      || (overlay.custom_box_mode || "manual") === "imported_summary"
      || overlay.custom_box_text,
  );
  if (!hasLegacyBox) return [];
  return [normalizeOverlayTextBox({
    id: "legacy-custom-box",
    enabled: overlay.custom_box_enabled,
    source: overlay.custom_box_mode || "manual",
    text: overlay.custom_box_text || "",
    quadrant: overlay.custom_box_quadrant || "top_right",
    x: overlay.custom_box_x,
    y: overlay.custom_box_y,
    background_color: overlay.custom_box_background_color || "#000000",
    text_color: overlay.custom_box_text_color || "#ffffff",
    opacity: overlay.custom_box_opacity ?? 0.9,
    width: overlay.custom_box_width || 0,
    height: overlay.custom_box_height || 0,
  })];
}

function preferredLegacyTextBox(boxes) {
  return boxes.find((box) => box.source === "imported_summary") || boxes[0] || null;
}

function syncLegacyOverlayBoxState(overlay, boxes = overlayTextBoxes()) {
  const primary = preferredLegacyTextBox(boxes);
  if (!primary) {
    overlay.custom_box_enabled = false;
    overlay.custom_box_mode = "manual";
    overlay.custom_box_text = "";
    return;
  }
  overlay.custom_box_enabled = Boolean(primary.enabled);
  overlay.custom_box_mode = primary.source;
  overlay.custom_box_text = primary.text;
  overlay.custom_box_quadrant = primary.quadrant;
  overlay.custom_box_x = primary.x;
  overlay.custom_box_y = primary.y;
  overlay.custom_box_background_color = primary.background_color;
  overlay.custom_box_text_color = primary.text_color;
  overlay.custom_box_opacity = primary.opacity;
  overlay.custom_box_width = primary.width;
  overlay.custom_box_height = primary.height;
}

function setLocalOverlayTextBoxes(boxes) {
  if (!state?.project?.overlay) return;
  const normalized = boxes.map((box, index) => normalizeOverlayTextBox(box, index));
  state.project.overlay.text_boxes = normalized;
  syncLegacyOverlayBoxState(state.project.overlay, normalized);
}

function buildOverlayTextBox(source = "manual") {
  return normalizeOverlayTextBox({
    id: createOverlayTextBoxId(),
    enabled: true,
    source,
    text: "",
    quadrant: source === "imported_summary" ? ABOVE_FINAL_TEXT_BOX_VALUE : "top_left",
    x: null,
    y: null,
    background_color: "#000000",
    text_color: "#ffffff",
    opacity: 0.9,
    width: 0,
    height: 0,
  });
}

function overlayTextBoxLabel(box, index) {
  if (box.source === "imported_summary") return `Imported Summary ${index + 1}`;
  return `Custom Box ${index + 1}`;
}

function applyOverlayTextBoxUpdate(boxes, { commit = false, rerender = false } = {}) {
  setLocalOverlayTextBoxes(boxes);
  previewOverlayControlChanges();
  if (rerender) renderTextBoxEditors();
  if (commit) scheduleOverlayApply();
}

function updateOverlayTextBox(boxId, updater, options = {}) {
  const boxes = overlayTextBoxes();
  const index = boxes.findIndex((box) => box.id === boxId);
  if (index === -1) return;
  const nextBox = updater({ ...boxes[index] }, index, boxes);
  if (!nextBox) return;
  const nextBoxes = boxes.slice();
  nextBoxes[index] = normalizeOverlayTextBox(nextBox, index);
  applyOverlayTextBoxUpdate(nextBoxes, options);
}

function setOverlayTextBoxField(boxId, field, rawValue, options = {}) {
  updateOverlayTextBox(boxId, (box) => {
    if (field === "enabled") {
      box.enabled = Boolean(rawValue);
      return box;
    }
    if (field === "source") {
      box.source = rawValue === "imported_summary" ? "imported_summary" : "manual";
      if (box.source === "imported_summary") {
        if (!usesCustomQuadrant(box.quadrant)) {
          box.quadrant = ABOVE_FINAL_TEXT_BOX_VALUE;
          box.x = null;
          box.y = null;
        }
        const autoSize = overlayTextBoxAutoSize(box);
        if (!(Number(box.width) > 0) && autoSize.width > 0) box.width = autoSize.width;
        if (!(Number(box.height) > 0) && autoSize.height > 0) box.height = autoSize.height;
      }
      return box;
    }
    if (field === "text") {
      box.text = String(rawValue || "");
      return box;
    }
    if (field === "quadrant") {
      if (usesCustomQuadrant(rawValue)) {
        box.quadrant = CUSTOM_QUADRANT_VALUE;
        box.x = box.x ?? 0.5;
        box.y = box.y ?? 0.5;
      } else {
        box.quadrant = rawValue;
        box.x = null;
        box.y = null;
      }
      return box;
    }
    if (field === "x") {
      box.quadrant = CUSTOM_QUADRANT_VALUE;
      box.x = normalizedCoordinateValue(rawValue);
      box.y = box.y ?? 0.5;
      return box;
    }
    if (field === "y") {
      box.quadrant = CUSTOM_QUADRANT_VALUE;
      box.x = box.x ?? 0.5;
      box.y = normalizedCoordinateValue(rawValue);
      return box;
    }
    if (field === "width" || field === "height") {
      box[field] = Math.max(0, Number(rawValue || 0));
      return box;
    }
    if (field === "background_color" || field === "text_color") {
      box[field] = normalizeHexColor(rawValue) || box[field];
      return box;
    }
    if (field === "opacity") {
      box.opacity = clampNumber(Number(rawValue) || 0, 0, 1);
      return box;
    }
    return box;
  }, options);
}

function addOverlayTextBox(source = "manual") {
  const boxes = overlayTextBoxes();
  boxes.push(buildOverlayTextBox(source));
  applyOverlayTextBoxUpdate(boxes, { commit: true, rerender: true });
}

function duplicateOverlayTextBox(boxId) {
  const boxes = overlayTextBoxes();
  const index = boxes.findIndex((box) => box.id === boxId);
  if (index === -1) return;
  const duplicate = normalizeOverlayTextBox({
    ...boxes[index],
    id: createOverlayTextBoxId(),
  }, index + 1);
  const nextBoxes = boxes.slice();
  nextBoxes.splice(index + 1, 0, duplicate);
  applyOverlayTextBoxUpdate(nextBoxes, { commit: true, rerender: true });
}

function removeOverlayTextBox(boxId) {
  const nextBoxes = overlayTextBoxes().filter((box) => box.id !== boxId);
  applyOverlayTextBoxUpdate(nextBoxes, { commit: true, rerender: true });
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
  overlay.timer_lock_to_stack = Boolean(payload.timer_lock_to_stack);
  overlay.draw_lock_to_stack = Boolean(payload.draw_lock_to_stack);
  overlay.score_lock_to_stack = Boolean(payload.score_lock_to_stack);
  overlay.review_boxes_lock_to_stack = Boolean(payload.review_boxes_lock_to_stack);
  overlay.text_boxes = (payload.text_boxes || []).map((box, index) => normalizeOverlayTextBox(box, index));
  syncLegacyOverlayBoxState(overlay, overlay.text_boxes);
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
  syncOverlayBubbleSizeControls();
}

function previewOverlayControlChanges() {
  syncOverlayPreviewStateFromControls();
  scheduleInteractionPreviewRender({ overlay: true });
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
  setColorControlValue(control, readColorControlValue(control));
  syncOverlayHexControl(control);
  control.addEventListener("click", () => openColorPicker(control));
  control.addEventListener("keydown", (event) => {
    if (event.key !== "Enter" && event.key !== " ") return;
    event.preventDefault();
    openColorPicker(control);
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

function overlayBadgeLockedToStack(kind, overlay = state?.project?.overlay) {
  if (!overlay || !(kind in OVERLAY_STACK_LOCK_CONTROLS)) return false;
  return Boolean(overlay[`${kind}_lock_to_stack`] ?? true);
}

function reviewBoxesLockedToOverlayStack(overlay = state?.project?.overlay) {
  return Boolean(overlay?.review_boxes_lock_to_stack);
}

function syncOverlayBubbleLockControlState() {
  Object.values(OVERLAY_STACK_LOCK_CONTROLS).forEach(({ lockId, xId, yId, label }) => {
    const lockControl = $(lockId);
    const isLocked = Boolean(lockControl?.checked);
    [[xId, "X"], [yId, "Y"]].forEach(([id, axis]) => {
      const input = $(id);
      if (!input) return;
      input.disabled = isLocked;
      input.placeholder = isLocked ? "Stack locked" : "auto";
      input.title = isLocked
        ? `${label} follows the shot stack while locked.`
        : `${label} ${axis} uses a normalized coordinate from 0 to 1. Leave it blank to follow the stack.`;
    });
  });
}

function overlayTextBoxDisplayText(box) {
  if (box.source === "imported_summary") {
    return state?.scoring_summary?.imported_overlay_text || "";
  }
  return box.text || "";
}

function overlayTextBoxHint(box) {
  if (reviewBoxesLockedToOverlayStack()) {
    return "Locked to the overlay stack. Unlock Review text boxes to edit placement or use the Above Final anchor.";
  }
  const importedReady = Boolean(state?.scoring_summary?.imported_overlay_text);
  if (box.quadrant === ABOVE_FINAL_TEXT_BOX_VALUE) {
    return box.source === "imported_summary"
      ? "Keeps the imported summary centered above the final score badge once it appears."
      : "Keeps this box centered above the final score badge once it appears.";
  }
  if (box.source === "imported_summary") {
    return importedReady
      ? "Uses the imported PractiScore stage summary and appears after the final shot."
      : "Import PractiScore results first. The summary box will populate after the final shot when imported data is available.";
  }
  return "Uses custom text and the same box model in Review and Export. Switch to Custom placement to edit X and Y directly.";
}

function buildTextBoxCard(box, index) {
  const card = document.createElement("section");
  card.className = "text-box-card";
  card.dataset.boxId = box.id;
  const usesCustomPlacement = usesCustomQuadrant(box.quadrant);
  const reviewBoxesLocked = reviewBoxesLockedToOverlayStack();
  card.innerHTML = `
    <div class="text-box-card-header">
      <label class="check-row"><input type="checkbox" data-text-box-field="enabled" /> <strong>${overlayTextBoxLabel(box, index)}</strong></label>
      <div class="text-box-card-actions">
        <button type="button" data-text-box-action="duplicate">Duplicate</button>
        <button type="button" data-text-box-action="remove">Remove</button>
      </div>
    </div>
    <label>Content Source
      <select data-text-box-field="source">
        <option value="manual">Custom text</option>
        <option value="imported_summary">Imported summary</option>
      </select>
    </label>
    <p class="hint" data-text-box-hint="true"></p>
    <label>Box text
      <textarea data-text-box-field="text" rows="3"></textarea>
    </label>
    <div class="control-grid">
      <label>Box placement
        <select data-text-box-field="quadrant">
          <option value="above_final">Above Final Box</option>
          <option value="top_left">Top left</option>
          <option value="top_middle">Top middle</option>
          <option value="top_right">Top right</option>
          <option value="middle_left">Middle left</option>
          <option value="middle_middle">Middle middle</option>
          <option value="middle_right">Middle right</option>
          <option value="bottom_left">Bottom left</option>
          <option value="bottom_middle">Bottom middle</option>
          <option value="bottom_right">Bottom right</option>
          <option value="custom">Custom</option>
        </select>
      </label>
      <label>Box X (0 left, 1 right)
        <input data-text-box-field="x" type="number" min="0" max="1" step="0.01" />
      </label>
      <label>Box Y (0 top, 1 bottom)
        <input data-text-box-field="y" type="number" min="0" max="1" step="0.01" />
      </label>
    </div>
    <div class="control-grid">
      <label>Box width
        <input data-text-box-field="width" type="number" min="0" max="1000" step="1" value="0" />
      </label>
      <label>Box height
        <input data-text-box-field="height" type="number" min="0" max="1000" step="1" value="0" />
      </label>
    </div>
    <div class="style-grid review-style-grid">
      <section class="style-card custom-box-style-card">
        <h4>Box Style</h4>
        <label class="color-field"><span class="style-card-label">Background</span>
          <span class="color-control-pair">
            <button data-text-box-field="background_color" class="color-swatch-button" data-color-label="Text box background" type="button"></button>
            <input class="color-hex-input" type="text" inputmode="text" spellcheck="false" value="#000000" placeholder="#000000" aria-label="Text box background hex value" />
          </span>
        </label>
        <label class="color-field"><span class="style-card-label">Text</span>
          <span class="color-control-pair">
            <button data-text-box-field="text_color" class="color-swatch-button" data-color-label="Text box text" type="button"></button>
            <input class="color-hex-input" type="text" inputmode="text" spellcheck="false" value="#ffffff" placeholder="#FFFFFF" aria-label="Text box text hex value" />
          </span>
        </label>
        <label class="opacity-field"><span class="style-card-label">Opacity</span>
          <span class="opacity-control-pair">
            <input data-text-box-field="opacity" type="range" min="0" max="1" step="0.01" value="0.9" />
            <span class="opacity-percent-field">
              <input class="opacity-percent-input" data-text-box-opacity-percent="opacity" type="number" min="0" max="100" step="1" value="90" aria-label="Opacity percent" />
              <span class="opacity-percent-suffix">%</span>
            </span>
          </span>
        </label>
      </section>
    </div>
  `;
  syncControlChecked(card.querySelector('[data-text-box-field="enabled"]'), box.enabled);
  syncControlValue(card.querySelector('[data-text-box-field="source"]'), box.source);
  syncControlValue(card.querySelector('[data-text-box-field="quadrant"]'), box.quadrant);
  syncControlValue(card.querySelector('[data-text-box-field="x"]'), box.x ?? "");
  syncControlValue(card.querySelector('[data-text-box-field="y"]'), box.y ?? "");
  syncControlValue(card.querySelector('[data-text-box-field="width"]'), box.width || 0);
  syncControlValue(card.querySelector('[data-text-box-field="height"]'), box.height || 0);
  syncControlValue(card.querySelector('[data-text-box-field="background_color"]'), box.background_color);
  syncControlValue(card.querySelector('[data-text-box-field="text_color"]'), box.text_color);
  syncControlValue(card.querySelector('[data-text-box-field="opacity"]'), box.opacity ?? 0.9);
  syncOpacityPercentControl(card.querySelector('[data-text-box-opacity-percent="opacity"]'), box.opacity ?? 0.9);
  const textArea = card.querySelector('[data-text-box-field="text"]');
  textArea.value = box.text || "";
  textArea.disabled = box.source === "imported_summary";
  textArea.placeholder = box.source === "imported_summary"
    ? "Uses the imported PractiScore stage summary after the final shot"
    : "Text to show over the video";
  const hint = card.querySelector('[data-text-box-hint="true"]');
  if (hint) hint.textContent = overlayTextBoxHint(box);
  const quadrantInput = card.querySelector('[data-text-box-field="quadrant"]');
  quadrantInput.disabled = reviewBoxesLocked;
  const xInput = card.querySelector('[data-text-box-field="x"]');
  const yInput = card.querySelector('[data-text-box-field="y"]');
  [xInput, yInput].forEach((input) => {
    input.disabled = reviewBoxesLocked || !usesCustomPlacement;
    input.placeholder = reviewBoxesLocked ? "Stack locked" : usesCustomPlacement ? "0.50" : "Custom only";
  });
  card.querySelectorAll("[data-text-box-field]").forEach((control) => {
    const field = control.dataset.textBoxField || "";
    if (!field) return;
    if (isColorInput(control)) return;
    const readValue = () => (control.type === "checkbox" ? control.checked : control.value);
    if (control.tagName === "SELECT") {
      control.addEventListener("change", () => setOverlayTextBoxField(box.id, field, readValue(), {
        commit: true,
        rerender: field === "source" || field === "quadrant",
      }));
      return;
    }
    if (control.type === "checkbox") {
      control.addEventListener("change", () => setOverlayTextBoxField(box.id, field, readValue(), { commit: true, rerender: false }));
      return;
    }
    if (control.type === "range") {
      control.addEventListener("input", () => setOverlayTextBoxField(box.id, field, readValue(), { rerender: false }));
      control.addEventListener("change", () => setOverlayTextBoxField(box.id, field, readValue(), { commit: true, rerender: false }));
      return;
    }
    control.addEventListener("input", () => setOverlayTextBoxField(box.id, field, readValue(), { rerender: false }));
    control.addEventListener("change", () => setOverlayTextBoxField(box.id, field, readValue(), { commit: true, rerender: false }));
    control.addEventListener("blur", () => setOverlayTextBoxField(box.id, field, readValue(), { commit: true, rerender: false }));
  });
  const opacityRange = card.querySelector('[data-text-box-field="opacity"]');
  const opacityPercent = card.querySelector('[data-text-box-opacity-percent="opacity"]');
  bindOpacityPercentPair(opacityRange, opacityPercent);
  if (opacityPercent instanceof HTMLInputElement) {
    const applyOpacity = (commit = false) => {
      const nextOpacity = opacityValueFromPercent(opacityPercent.value);
      syncControlValue(opacityRange, nextOpacity.toFixed(2));
      setOverlayTextBoxField(box.id, "opacity", nextOpacity, { commit, rerender: false });
      syncOpacityPercentControl(opacityPercent, nextOpacity);
    };
    opacityPercent.addEventListener("input", () => applyOpacity(false));
    opacityPercent.addEventListener("change", () => applyOpacity(true));
    opacityPercent.addEventListener("blur", () => applyOpacity(true));
  }
  card.querySelector('[data-text-box-action="duplicate"]')?.addEventListener("click", () => duplicateOverlayTextBox(box.id));
  card.querySelector('[data-text-box-action="remove"]')?.addEventListener("click", () => removeOverlayTextBox(box.id));
  bindOverlayColorInput(card.querySelector('[data-text-box-field="background_color"]'));
  bindOverlayColorInput(card.querySelector('[data-text-box-field="text_color"]'));
  return card;
}

function renderTextBoxEditors() {
  const containers = [$("review-text-box-list")].filter(Boolean);
  if (containers.length === 0) return;
  const boxes = overlayTextBoxes();
  containers.forEach((container) => {
    withPreservedScrollState([container, document.querySelector(".inspector")].filter(Boolean), () => {
      container.innerHTML = "";
      if (boxes.length === 0) {
        const empty = document.createElement("div");
        empty.className = "hint";
        empty.textContent = "No text boxes yet. Add a custom box or an imported summary box here and it will render in both review and export.";
        container.appendChild(empty);
        return;
      }
      boxes.forEach((box, index) => {
        container.appendChild(buildTextBoxCard(box, index));
      });
    });
  });
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

function persistLayoutSize(key, value, { renderWaveformNow = true } = {}) {
  layoutSizes[key] = value;
  const storageKey = {
    railWidth: "splitshot.layout.railWidth",
    inspectorWidth: "splitshot.layout.inspectorWidth",
    waveformHeight: "splitshot.layout.waveformHeight",
  }[key];
  window.localStorage.setItem(storageKey, String(Math.round(value)));
  applyLayoutState();
  syncLocalProjectUiState();
  scheduleProjectUiStateApply();
  if (state && renderWaveformNow) renderWaveform();
}

function previewLayoutSize(key, value) {
  layoutSizes[key] = value;
  applyLayoutState();
  scheduleInteractionPreviewRender({ video: true, waveform: true, overlay: true });
}

function toggleLayoutLock() {
  layoutLocked = !layoutLocked;
  window.localStorage.setItem("splitshot.layoutLocked", String(layoutLocked));
  activity("layout.lock.toggle", { locked: layoutLocked });
  applyLayoutState();
  syncLocalProjectUiState();
  scheduleProjectUiStateApply();
}

function resetLayout() {
  layoutSizes = { railWidth: 64, inspectorWidth: 440, waveformHeight: 206 };
  ["splitshot.layout.railWidth", "splitshot.layout.inspectorWidth", "splitshot.layout.waveformHeight"].forEach((key) => {
    window.localStorage.removeItem(key);
  });
  activity("layout.reset", layoutSizes);
  applyLayoutState();
  syncLocalProjectUiState();
  scheduleProjectUiStateApply();
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
    previewLayoutSize("railWidth", clamp(event.clientX, 48, 72));
  } else if (kind === "inspectorWidth") {
    const grid = document.querySelector(".review-grid");
    const right = grid?.getBoundingClientRect().right || window.innerWidth;
    previewLayoutSize("inspectorWidth", clamp(right - event.clientX, 320, Math.max(320, window.innerWidth * 0.48)));
  } else if (kind === "waveformHeight") {
    const stack = document.querySelector(".review-stack");
    const rect = stack?.getBoundingClientRect();
    if (rect) {
      previewLayoutSize("waveformHeight", clamp(rect.bottom - event.clientY, 112, Math.max(112, rect.height * 0.48)));
    }
  }
}

function endLayoutResize(event) {
  if (!activeResize) return;
  if (event.pointerId !== undefined && activeResize.pointerId !== undefined && event.pointerId !== activeResize.pointerId) return;
  const kind = activeResize.kind;
  const sizeKey = {
    railWidth: "railWidth",
    inspectorWidth: "inspectorWidth",
    waveformHeight: "waveformHeight",
  }[kind];
  releasePointer(activeResize.target, activeResize.pointerId);
  activeResize = null;
  document.body.classList.remove("resizing-layout");
  if (sizeKey) persistLayoutSize(sizeKey, layoutSizes[sizeKey], { renderWaveformNow: false });
  activity("layout.resize.commit", { kind, sizes: layoutSizes });
  flushInteractionPreviewRender();
  flushQueuedProjectUiStateApply();
  flushDeferredRender();
}

function setActiveTool(tool, { persistUiState = true } = {}) {
  if (!VALID_TOOL_IDS.has(tool) || !document.querySelector(`[data-tool-pane="${tool}"]`)) tool = "project";
  const changed = activeTool !== tool;
  const root = $("cockpit-root");
  const hadExpandedLayout = root?.classList.contains("waveform-expanded") || root?.classList.contains("timing-expanded");
  activeTool = tool;
  window.localStorage.setItem("splitshot.activeTool", tool);
  if (changed) {
    root?.classList.remove("waveform-expanded", "timing-expanded");
    const expand = $("expand-waveform");
    if (expand) expand.textContent = "Expand";
    if (hadExpandedLayout) scheduleReviewStageRestore();
  }
  root.classList.toggle("scoring-active", tool === "scoring");
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
  syncLocalProjectUiState();
  if (persistUiState) scheduleProjectUiStateApply();
  renderLiveOverlay();
}

async function api(path, payload = null) {
  activity("api.request", { path, payload });
  const processing = processingForPath(path);
  const finishProcessing = payload === null || processing === null
    ? null
    : beginProcessing(processing.message, processing.detail, path);
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
  requestRender();
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
  if (path === "/api/analysis/threshold" && state?.project?.primary_video?.path) {
    return { message: "Re-running ShotML...", detail: "Refreshing shot detections for the current threshold" };
  }
  if (path === "/api/import/merge" || path === "/api/files/merge") {
    return { message: "Importing media...", detail: "Adding media to the list" };
  }
  if (path === "/api/import/secondary") {
    return { message: "Importing media...", detail: "Adding media to the list" };
  }
  if (path === "/api/project/details") return { message: "Updating project details...", detail: "Saving metadata locally" };
  if (path === "/api/project/practiscore") return { message: "Updating match import settings...", detail: "Saving stage and competitor details" };
  if (path === "/api/project/open") return { message: "Opening project folder...", detail: "Loading project.json and local assets" };
  if (path === "/api/project/save") return { message: "Updating project folder...", detail: "Writing project.json and organizing local assets" };
  if (path === "/api/project/delete") return { message: "Deleting project folder...", detail: "Removing the project folder from disk" };
  if (path === "/api/project/new") return { message: "Creating new project...", detail: "Resetting project state" };
  return null;
}

async function postFile(path, file) {
  if (!file) return null;
  const form = new FormData();
  form.append("file", file, file.name);
  const uploadState = path === "/api/files/practiscore"
    ? { message: `Importing ${file.name}...`, detail: "Parsing PractiScore results and staging a local copy" }
    : path === "/api/files/merge"
      ? { message: `Importing ${file.name}...`, detail: "Adding media to the list" }
      : { message: `Analyzing ${file.name}...`, detail: "Detecting beep and shots" };
  const finishProcessing = beginProcessing(uploadState.message, uploadState.detail, path);
  setStatus(uploadState.message);
  activity("file.selected", { path, name: file.name, size: file.size });
  try {
    const response = await fetch(path, { method: "POST", body: form });
    const data = await response.json();
    if (!response.ok || data.error) throw new Error(data.error || response.statusText);
    applyRemoteState(data);
    requestRender();
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
    requestRender();
  } catch (error) {
    setStatus(error.message);
    activity("api.error", { path: "/api/state", error: error.message });
  }
}

function applyRemoteState(nextState) {
  if (!hasCompleteProjectState(nextState)) {
    throw new Error("Received invalid project state from the local server.");
  }
  const previousSelectionContext = pendingSelectionFallback
    || shotSelectionContext(selectedShotId, state)
    || shotSelectionContext(state?.project?.ui_state?.selected_shot_id, state);
  pendingSelectionFallback = null;
  const nextProjectId = nextState?.project?.id || "";
  const isSameProject = currentProjectId && nextProjectId && currentProjectId === nextProjectId;
  if (currentProjectId && nextProjectId && currentProjectId !== nextProjectId) {
    resetLocalProjectView();
  }
  const remoteSelectedShotId = nextState.project.ui_state.selected_shot_id;
  const nextUiState = isSameProject
    ? mergeProjectUiState(nextState.project.ui_state, readProjectUiStatePayload())
    : normalizeProjectUiState(nextState.project.ui_state);
  nextUiState.selected_shot_id = resolveSelectedShotId(
    nextState,
    nextUiState.selected_shot_id,
    previousSelectionContext,
    remoteSelectedShotId,
  );
  nextState.project.ui_state = nextUiState;
  if (isSameProject) mergeProjectDetailsDraft(nextState.project);
  currentProjectId = nextProjectId;
  state = nextState;
  applyProjectUiState(nextUiState);
  if (!stateHasShot(state, selectedShotId)) {
    selectedShotId = stateHasShot(state, nextUiState.selected_shot_id) ? nextUiState.selected_shot_id : null;
  }
  syncSelectedShotId(state, previousSelectionContext);
  syncLocalProjectUiState();
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
  draggingShotPointerId = null;
  pendingDragTimeMs = null;
  exportPathDraft = "";
  projectDetailsDraft = { name: null, description: null };
  exportLogLines = [];
  timingRowEdits = new Set();
  scoringShotExpansion = new Map();
  applyProjectUiState({
    ...DEFAULT_PROJECT_UI_STATE,
    active_tool: "project",
    waveform_mode: "select",
    timeline_zoom: 1,
    timeline_offset_ms: 0,
    layout_locked: true,
    rail_width: 64,
    inspector_width: 440,
    waveform_height: 206,
  });
  window.localStorage.removeItem("splitshot.waveform.zoomX");
  window.localStorage.removeItem("splitshot.waveform.offsetMs");
  resetMediaElement($("primary-video"));
  resetMediaElement($("secondary-video"));
  const secondaryImage = $("secondary-image");
  if (secondaryImage) secondaryImage.hidden = true;
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
      element.textContent = "No Video Selected";
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
  if (!(video instanceof HTMLMediaElement)) return;
  video.pause();
  video.removeAttribute("src");
  video.dataset.sourcePath = "";
  video.dataset.mediaUrl = "";
  video.load();
}

function restoreVideoElementFrame(video) {
  if (!(video instanceof HTMLVideoElement)) return;
  if (video.hidden || !video.isConnected || !video.currentSrc) return;
  if (video.readyState < HTMLMediaElement.HAVE_CURRENT_DATA) return;
  video.style.willChange = "transform";
  void video.getBoundingClientRect();
  window.requestAnimationFrame(() => {
    if (video.style.willChange === "transform") video.style.willChange = "";
  });
  if (!video.paused) return;
  const currentTime = Number.isFinite(video.currentTime) ? video.currentTime : 0;
  try {
    if (typeof video.fastSeek === "function") video.fastSeek(currentTime);
    else video.currentTime = currentTime;
  } catch {
    // Some browsers reject same-time seeks while the element is restoring.
  }
}

function refreshReviewMediaFrame() {
  renderLiveOverlay();
  scheduleSecondaryPreviewSync();
  restoreVideoElementFrame($("primary-video"));
  restoreVideoElementFrame($("secondary-video"));
}

function restoreReviewStage() {
  if (!state?.project) return;
  applyLayoutState();
  renderVideo();
  renderWaveform();
  renderTimingTables();
  renderSelection();
  renderLiveOverlay();
  scheduleSecondaryPreviewSync();
  restoreVideoElementFrame($("primary-video"));
  restoreVideoElementFrame($("secondary-video"));
  document.querySelectorAll("#merge-preview-layer video").forEach((video) => restoreVideoElementFrame(video));
}

function scheduleReviewStageRestore() {
  if (reviewStageRestoreFrame !== null) window.cancelAnimationFrame(reviewStageRestoreFrame);
  if (reviewStageRestoreSecondFrame !== null) window.cancelAnimationFrame(reviewStageRestoreSecondFrame);
  reviewStageRestoreFrame = window.requestAnimationFrame(() => {
    reviewStageRestoreFrame = null;
    restoreReviewStage();
    reviewStageRestoreSecondFrame = window.requestAnimationFrame(() => {
      reviewStageRestoreSecondFrame = null;
      restoreReviewStage();
    });
  });
}

function handleStageFullscreenChange() {
  scheduleReviewStageRestore();
}

function handleWindowVisibilityRestore() {
  if (document.visibilityState && document.visibilityState !== "visible") return;
  scheduleReviewStageRestore();
}

function primaryVideoStateSnapshot(video) {
  if (!video) return {};
  const volume = Number.isFinite(video.volume) ? Math.round(video.volume * 1000) / 1000 : null;
  const currentTime = Number.isFinite(video.currentTime) ? Math.round(video.currentTime * 1000) / 1000 : null;
  const duration = Number.isFinite(video.duration) ? Math.round(video.duration * 1000) / 1000 : null;
  const audioTrackCount = typeof video.audioTracks?.length === "number" ? video.audioTracks.length : null;
  const webkitAudioDecodedByteCount = Number(video.webkitAudioDecodedByteCount);
  return {
    muted: video.muted,
    default_muted: video.defaultMuted,
    volume,
    paused: video.paused,
    ended: video.ended,
    ready_state: video.readyState,
    network_state: video.networkState,
    current_time_s: currentTime,
    duration_s: duration,
    source_path: video.dataset.sourcePath || "",
    current_src: video.currentSrc || video.src || "",
    audio_tracks: audioTrackCount,
    moz_has_audio: typeof video.mozHasAudio === "boolean" ? video.mozHasAudio : null,
    webkit_audio_decoded_bytes: Number.isFinite(webkitAudioDecodedByteCount) ? webkitAudioDecodedByteCount : null,
    error_code: video.error?.code || null,
    error_message: video.error?.message || "",
  };
}

function logPrimaryVideoState(eventName) {
  const video = $("primary-video");
  if (!video) return;
  activity("video.primary.state", {
    event: eventName,
    ...primaryVideoStateSnapshot(video),
  });
}

function ensurePrimaryVideoAudio(video) {
  if (!video) return;
  video.defaultMuted = false;
  video.muted = false;
  video.volume = 1;
}

function normalizedPractiScorePlaceValue(rawValue) {
  if (rawValue === null || rawValue === undefined || String(rawValue).trim() === "") return null;
  const numeric = Number(rawValue);
  if (!Number.isFinite(numeric) || numeric < 1) return null;
  return Math.trunc(numeric);
}

function practiScoreCompetitors() {
  return Array.isArray(state?.practiscore_options?.competitors)
    ? state.practiscore_options.competitors
    : [];
}

function practiScoreStageValues() {
  return [...new Set(
    (Array.isArray(state?.practiscore_options?.stage_numbers) ? state.practiscore_options.stage_numbers : [])
      .map((value) => String(value || "").trim())
      .filter(Boolean),
  )];
}

function practiScoreNameValues() {
  return [...new Set(practiScoreCompetitors().map((option) => String(option.name || "").trim()).filter(Boolean))];
}

function practiScorePlaceValues() {
  return [...new Set(
    practiScoreCompetitors()
      .map((option) => normalizedPractiScorePlaceValue(option.place))
      .filter((value) => value !== null),
  )].map((value) => String(value));
}

function practiScoreSelectionValue(value) {
  if (value === null || value === undefined) return "";
  return String(value).trim();
}

function preferredPractiScoreSelection(explicitValue, controlId, fallbackValue) {
  if (explicitValue !== undefined) return practiScoreSelectionValue(explicitValue);
  const controlValue = practiScoreSelectionValue($(controlId)?.value);
  if (controlValue) return controlValue;
  return practiScoreSelectionValue(fallbackValue);
}

function renderPractiScoreSelect(selectId, values, emptyLabel, selectedValue = "") {
  const select = $(selectId);
  if (!(select instanceof HTMLSelectElement)) return;
  const optionValues = [...new Set((values || []).map((value) => practiScoreSelectionValue(value)).filter(Boolean))];
  const desiredValue = practiScoreSelectionValue(selectedValue);
  const activeValue = controlIsActive(select) ? practiScoreSelectionValue(select.value) : "";
  const preservedValue = activeValue || desiredValue;
  if (preservedValue && !optionValues.includes(preservedValue)) optionValues.unshift(preservedValue);
  select.innerHTML = "";
  const emptyOption = document.createElement("option");
  emptyOption.value = "";
  emptyOption.textContent = emptyLabel;
  select.appendChild(emptyOption);
  optionValues.forEach((value) => {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = value;
    select.appendChild(option);
  });
  select.value = preservedValue && optionValues.includes(preservedValue) ? preservedValue : "";
}

function renderPractiScoreOptionLists(selectedValues = {}) {
  renderPractiScoreSelect(
    "match-stage-number",
    practiScoreStageValues(),
    "Select stage",
    preferredPractiScoreSelection(selectedValues.stage_number, "match-stage-number", state?.project?.scoring?.stage_number),
  );
  renderPractiScoreSelect(
    "match-competitor-name",
    practiScoreNameValues(),
    "Select competitor",
    preferredPractiScoreSelection(selectedValues.competitor_name, "match-competitor-name", state?.project?.scoring?.competitor_name),
  );
  renderPractiScoreSelect(
    "match-competitor-place",
    practiScorePlaceValues(),
    "Select place",
    preferredPractiScoreSelection(selectedValues.competitor_place, "match-competitor-place", state?.project?.scoring?.competitor_place),
  );
}

function syncPractiScoreSelectionFields(changedField) {
  const competitors = practiScoreCompetitors();
  const stageSelect = $("match-stage-number");
  const nameSelect = $("match-competitor-name");
  const placeSelect = $("match-competitor-place");
  if (!(nameSelect instanceof HTMLSelectElement) || !(placeSelect instanceof HTMLSelectElement)) {
    renderPractiScoreOptionLists();
    return;
  }

  if (competitors.length === 0) {
    renderPractiScoreOptionLists({
      stage_number: practiScoreSelectionValue(stageSelect?.value),
      competitor_name: nameSelect.value,
      competitor_place: placeSelect.value,
    });
    return;
  }

  const selectedName = nameSelect.value.trim();
  const selectedPlace = normalizedPractiScorePlaceValue(placeSelect.value);
  if (changedField === "name") {
    const matches = competitors.filter((option) => option.name === selectedName);
    if (!selectedName || matches.length === 0) {
      placeSelect.value = "";
    } else if (matches.length === 1 && matches[0].place !== null) {
      placeSelect.value = String(matches[0].place);
    } else if (selectedPlace !== null && !matches.some((option) => Number(option.place) === selectedPlace)) {
      placeSelect.value = "";
    }
  }
  if (changedField === "place") {
    if (selectedPlace === null) {
      nameSelect.value = "";
    } else {
      const matches = competitors.filter((option) => Number(option.place) === selectedPlace);
      if (matches.length === 0) {
        nameSelect.value = "";
      } else if (matches.length === 1) {
        nameSelect.value = matches[0].name;
      } else if (selectedName && !matches.some((option) => option.name === selectedName)) {
        nameSelect.value = "";
      }
    }
  }

  renderPractiScoreOptionLists({
    stage_number: practiScoreSelectionValue(stageSelect?.value),
    competitor_name: nameSelect.value,
    competitor_place: placeSelect.value,
  });
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

function persistWaveformViewport() {
  window.localStorage.setItem("splitshot.waveform.zoomX", String(waveformZoomX));
  window.localStorage.setItem("splitshot.waveform.offsetMs", String(Math.round(waveformOffsetMs)));
  syncLocalProjectUiState();
  scheduleProjectUiStateApply();
}

function setWaveformOffset(nextOffsetMs, { persist = true } = {}) {
  const visible = waveformWindow();
  const maxOffset = Math.max(0, durationMs() - visible.duration);
  const clampedOffset = clamp(nextOffsetMs, 0, maxOffset);
  if (Math.abs(clampedOffset - waveformOffsetMs) < 0.5) return false;
  waveformOffsetMs = clampedOffset;
  if (persist) persistWaveformViewport();
  return true;
}

function centerWaveformOnTime(timeMs, { persist = true } = {}) {
  const visible = waveformWindow();
  const maxOffset = Math.max(0, durationMs() - visible.duration);
  if (maxOffset <= 0) return false;
  return setWaveformOffset(timeMs - (visible.duration / 2), { persist });
}

function ensureWaveformTimeVisible(timeMs, { center = false, paddingRatio = 0.12, persist = true } = {}) {
  const visible = waveformWindow();
  const maxOffset = Math.max(0, durationMs() - visible.duration);
  if (!Number.isFinite(timeMs) || maxOffset <= 0) return false;
  if (center || timeMs < visible.start || timeMs > visible.end) {
    return centerWaveformOnTime(timeMs, { persist });
  }
  const padding = Math.min(visible.duration / 2, Math.max(20, visible.duration * paddingRatio));
  if (timeMs < visible.start + padding) return setWaveformOffset(timeMs - padding, { persist });
  if (timeMs > visible.end - padding) return setWaveformOffset(timeMs - visible.duration + padding, { persist });
  return false;
}

function waveformNavigatorMetrics(track = $("waveform-window-track")) {
  if (!track) return null;
  const visible = waveformWindow();
  const totalDuration = Math.max(1, durationMs());
  const rect = track.getBoundingClientRect();
  const trackWidth = Math.max(1, rect.width || track.clientWidth || 1);
  const maxOffset = Math.max(0, totalDuration - visible.duration);
  const idealHandleWidth = trackWidth * (visible.duration / totalDuration);
  const handleWidth = maxOffset <= 0
    ? trackWidth
    : clamp(Math.max(WAVEFORM_WINDOW_HANDLE_MIN_PX, idealHandleWidth), WAVEFORM_WINDOW_HANDLE_MIN_PX, trackWidth);
  const maxLeft = Math.max(0, trackWidth - handleWidth);
  const left = maxLeft <= 0 ? 0 : (waveformOffsetMs / maxOffset) * maxLeft;
  return { track, rect, trackWidth, totalDuration, visible, maxOffset, handleWidth, maxLeft, left };
}

function renderWaveformNavigator() {
  const nav = $("waveform-window");
  const track = $("waveform-window-track");
  const handle = $("waveform-window-handle");
  const expanded = $("cockpit-root")?.classList.contains("waveform-expanded") ?? false;
  if (!nav || !track || !handle) return;
  nav.hidden = !expanded || !state?.project;
  if (nav.hidden) return;
  const metrics = waveformNavigatorMetrics(track);
  if (!metrics) return;
  const canPan = metrics.maxOffset > 0;
  nav.classList.toggle("interactive", canPan);
  track.classList.toggle("interactive", canPan);
  handle.classList.toggle("interactive", canPan);
  handle.style.width = `${metrics.handleWidth}px`;
  handle.style.transform = `translateX(${metrics.left}px)`;
  const startLabel = `${(metrics.visible.start / 1000).toFixed(2)}s`;
  const endLabel = `${(metrics.visible.end / 1000).toFixed(2)}s`;
  track.title = canPan
    ? `Drag to pan the zoomed waveform window (${startLabel} to ${endLabel}).`
    : `Zoom in to pan the waveform window (${startLabel} to ${endLabel}).`;
}

function updateWaveformNavigator(clientX) {
  const metrics = waveformNavigatorMetrics();
  if (!metrics || metrics.maxOffset <= 0) return false;
  const ratio = clamp((clientX - metrics.rect.left) / metrics.trackWidth, 0, 1);
  return centerWaveformOnTime(ratio * metrics.totalDuration);
}

function waveformX(timeMs, width) {
  const window = waveformWindow();
  return ((timeMs - window.start) / window.duration) * width;
}

function isWaveformVisible(timeMs) {
  const window = waveformWindow();
  return timeMs >= window.start && timeMs <= window.end;
}

function primaryFrameDurationMs() {
  const fps = Number(state?.project?.primary_video?.fps || 0);
  return fps > 0 ? 1000 / fps : 0;
}

function browserShotPresentationLagFrames(video = $("primary-video")) {
  if (!(video instanceof HTMLVideoElement)) return 0;
  // Firefox can surface the next media time before the corresponding frame is visibly painted.
  return "mozPaintedFrames" in video ? 1 : 0;
}

function shotDisplayTimeMs(shotTimeMs, video = $("primary-video")) {
  const normalizedShotTimeMs = Math.max(0, Math.floor(Number(shotTimeMs) || 0));
  const frameDurationMs = primaryFrameDurationMs();
  if (!(frameDurationMs > 0)) return normalizedShotTimeMs;
  const frameIndex = Math.ceil((normalizedShotTimeMs / frameDurationMs) - Number.EPSILON);
  const displayFrameIndex = frameIndex + browserShotPresentationLagFrames(video);
  return Math.max(
    normalizedShotTimeMs,
    Math.ceil((displayFrameIndex * frameDurationMs) - Number.EPSILON),
  );
}

function currentShotIndex(positionMs) {
  const shots = orderedShotsByTime();
  let index = -1;
  shots.forEach((shot, shotIndex) => {
    if (shotDisplayTimeMs(shot.time_ms) <= positionMs) index = shotIndex;
  });
  return index;
}

function renderHeader() {
  const projectName = normalizeProjectNameValue(state.project.name);
  $("project-title").textContent = projectName;
  $("rail-project").textContent = projectName;
  $("status").textContent = state.status;
  const primaryName = state.media.primary_available
    ? (state.media.primary_display_name || fileName(state.project.primary_video.path))
    : "No Video Selected";
  $("current-file").textContent = primaryName;
  const statusCopy = $("status-copy");
  if (statusCopy) statusCopy.textContent = state.status;
  const inspectorFile = $("inspector-file");
  if (inspectorFile) inspectorFile.textContent = primaryName;
  const inspectorStatusCopy = $("inspector-status-copy");
  if (inspectorStatusCopy) inspectorStatusCopy.textContent = state.status;
  const mergeCount = (state.project.merge_sources || []).length;
  syncControlValue($("primary-file-path"), state.project.primary_video.path || "");
  $("project-path").placeholder = `${state.default_project_path || "~/splitshot"}/My Match`;
  syncControlValue($("project-path"), state.project.path || "");
  $("media-badge").textContent = state.media.primary_available
    ? `Primary: ${primaryName}${mergeCount > 0 ? ` • ${mergeCount} added item${mergeCount === 1 ? "" : "s"}` : ""}`
    : "No Video Selected";
}

function renderStats() {
  $("timing-summary").textContent = state.metrics.raw_time_ms
    ? "Click Edit and Unlock to change shot values."
    : "No timing data.";
  $("apply-threshold").disabled = !state?.project?.primary_video?.path;
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
      media.defaultMuted = false;
      media.muted = false;
      media.volume = 1;
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
  const mediaPath = buildMediaUrl(`/media/merge/${sourceId}`, asset.path || "");
  if (media instanceof HTMLImageElement) {
    if (media.dataset.sourcePath !== asset.path || media.dataset.mediaUrl !== mediaPath) {
      media.dataset.sourcePath = asset.path;
      media.dataset.mediaUrl = mediaPath;
      media.src = mediaPath;
    }
  } else if (media instanceof HTMLVideoElement && (media.dataset.sourcePath !== asset.path || media.dataset.mediaUrl !== mediaPath)) {
    media.dataset.sourcePath = asset.path;
    media.dataset.mediaUrl = mediaPath;
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
  const primaryMediaPath = buildMediaUrl(state.media.primary_url || "/media/primary", path);
  if (state.media.primary_available && (video.dataset.sourcePath !== path || video.dataset.mediaUrl !== primaryMediaPath)) {
    video.dataset.sourcePath = path;
    video.dataset.mediaUrl = primaryMediaPath;
    video.src = primaryMediaPath;
    video.load();
    logPrimaryVideoState("source.attach");
  }
  if (!state.media.primary_available) {
    resetMediaElement(video);
  }

  const secondaryPath = state.project.secondary_video?.path || "";
  const imageSecondary = isImagePath(secondaryPath);
  const secondaryMediaPath = buildMediaUrl(state.media.secondary_url || "/media/secondary", secondaryPath);
  if (state.media.secondary_available && imageSecondary) {
    if (secondaryImage.dataset.sourcePath !== secondaryPath || secondaryImage.dataset.mediaUrl !== secondaryMediaPath) {
      secondaryImage.dataset.sourcePath = secondaryPath;
      secondaryImage.dataset.mediaUrl = secondaryMediaPath;
      secondaryImage.src = secondaryMediaPath;
    }
    resetMediaElement(secondary);
  } else if (state.media.secondary_available && !imageSecondary) {
    if (secondary.dataset.sourcePath !== secondaryPath || secondary.dataset.mediaUrl !== secondaryMediaPath) {
      secondary.dataset.sourcePath = secondaryPath;
      secondary.dataset.mediaUrl = secondaryMediaPath;
      secondary.src = secondaryMediaPath;
      ensurePrimaryVideoAudio(secondary);
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
  const windowHeight = panel.querySelector(".waveform-window")?.getBoundingClientRect().height || 0;
  const footerHeight = panel.querySelector(".waveform-footer")?.getBoundingClientRect().height || 0;
  const shotList = panel.querySelector(".waveform-shot-list");
  const shotListVisible = shotList && window.getComputedStyle(shotList).display !== "none";
  const shotListHeight = shotListVisible ? shotList.getBoundingClientRect().height : 0;
  return Math.max(1, Math.floor(panelHeight - headerHeight - windowHeight - footerHeight - shotListHeight));
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
  canvas.classList.toggle("waveform-pannable", expanded && waveformZoomX > 1);
  canvas.classList.toggle("waveform-panning", Boolean(waveformPanDrag));
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
  renderWaveformNavigator();
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

function startWaveformPanDrag(event) {
  const canvas = $("waveform");
  waveformPanDrag = {
    target: canvas,
    pointerId: event.pointerId,
    startClientX: event.clientX,
    startOffsetMs: waveformOffsetMs,
    moved: false,
  };
  capturePointer(canvas, event.pointerId);
  canvas.classList.add("waveform-panning");
  activity("waveform.pan_drag.start", { offset_ms: waveformOffsetMs });
  event.preventDefault();
}

function updateWaveformPanDrag(event) {
  if (!waveformPanDrag) return;
  if (event.pointerId !== undefined && waveformPanDrag.pointerId !== undefined && event.pointerId !== waveformPanDrag.pointerId) return;
  const canvas = $("waveform");
  const rect = canvas.getBoundingClientRect();
  const visible = waveformWindow();
  const deltaPx = event.clientX - waveformPanDrag.startClientX;
  if (Math.abs(deltaPx) >= WAVEFORM_PAN_DRAG_THRESHOLD_PX) waveformPanDrag.moved = true;
  if (!waveformPanDrag.moved) return;
  const nextOffset = waveformPanDrag.startOffsetMs - ((deltaPx / Math.max(1, rect.width)) * visible.duration);
  setWaveformOffset(nextOffset);
  scheduleInteractionPreviewRender({ waveform: true });
}

function finishWaveformPanDrag(event) {
  if (!waveformPanDrag) return false;
  if (event.pointerId !== undefined && waveformPanDrag.pointerId !== undefined && event.pointerId !== waveformPanDrag.pointerId) return true;
  releasePointer(waveformPanDrag.target, waveformPanDrag.pointerId);
  waveformPanDrag.target?.classList.remove("waveform-panning");
  const moved = waveformPanDrag.moved;
  waveformPanDrag = null;
  if (moved) {
    activity("waveform.pan_drag.commit", { offset_ms: waveformOffsetMs });
    flushInteractionPreviewRender();
  }
  flushQueuedProjectUiStateApply();
  flushDeferredRender();
  return moved;
}

function handleWaveformNavigatorPointerDown(event) {
  if (event.button !== 0) return;
  const track = $("waveform-window-track");
  const metrics = waveformNavigatorMetrics(track);
  if (!metrics || metrics.maxOffset <= 0) return;
  waveformNavigatorDrag = {
    target: track,
    pointerId: event.pointerId,
  };
  capturePointer(track, event.pointerId);
  updateWaveformNavigator(event.clientX);
  scheduleInteractionPreviewRender({ waveform: true });
  event.preventDefault();
}

function moveWaveformNavigatorDrag(event) {
  if (!waveformNavigatorDrag) return;
  if (event.pointerId !== undefined && waveformNavigatorDrag.pointerId !== undefined && event.pointerId !== waveformNavigatorDrag.pointerId) return;
  updateWaveformNavigator(event.clientX);
  scheduleInteractionPreviewRender({ waveform: true });
}

function endWaveformNavigatorDrag(event) {
  if (!waveformNavigatorDrag) return;
  if (event.pointerId !== undefined && waveformNavigatorDrag.pointerId !== undefined && event.pointerId !== waveformNavigatorDrag.pointerId) return;
  releasePointer(waveformNavigatorDrag.target, waveformNavigatorDrag.pointerId);
  waveformNavigatorDrag = null;
  flushInteractionPreviewRender();
  flushQueuedProjectUiStateApply();
  flushDeferredRender();
}

function selectShot(shotId, { revealInWaveform = true, centerWaveform = false } = {}) {
  const nextShotId = stateHasShot(state, shotId) ? shotId : null;
  selectedShotId = nextShotId;
  if (nextShotId && !scoringShotExpansion.has(nextShotId)) scoringShotExpansion.set(nextShotId, true);
  if (state?.project?.ui_state) state.project.ui_state.selected_shot_id = nextShotId;
  activity("shot.select", { shot_id: nextShotId });
  const shot = selectedShot();
  if (shot && revealInWaveform) {
    if (ensureWaveformTimeVisible(shot.time_ms, { center: centerWaveform || !isWaveformVisible(shot.time_ms) })) {
      renderWaveform();
    }
  }
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
  callApi("/api/shots/select", { shot_id: nextShotId });
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
  withPreservedScrollState([list], () => {
    list.innerHTML = "";
    (state.timing_segments || []).forEach((segment) => {
      const item = document.createElement("button");
      item.type = "button";
      if (segment.shot_id === selectedShotId) item.classList.add("selected");
      if (isLowConfidence(segment.confidence, segment.source)) {
        item.classList.add("low-confidence");
        item.title = `Review this split manually: model confidence ${formatConfidenceValue(segment.confidence)}.`;
      }
      const title = document.createElement("strong");
      title.textContent = segment.card_title;
      const meta = document.createElement("small");
      meta.textContent = segment.card_meta;
      item.append(title, meta);
      item.addEventListener("click", () => selectShot(segment.shot_id, { revealInWaveform: true, centerWaveform: true }));
      list.appendChild(item);
    });
  });
}

function shotLabelForEvent(shotId) {
  const shots = orderedShotsByTime();
  const shotIndex = shots.findIndex((shot) => shot.id === shotId);
  const shot = shotIndex >= 0 ? shots[shotIndex] : null;
  if (!shot) return "Any shot";
  return `Shot ${shotIndex + 1} ${seconds(shot.time_ms)}s`;
}

function deleteTimingEvent(eventId) {
  activity("timing.event.delete", { event_id: eventId });
  callApi("/api/events/delete", { event_id: eventId });
}

function renderTimingEventList() {
  const list = $("timing-event-list");
  if (!list) return;
  withPreservedScrollState([list], () => {
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
  });
}

function renderTimingEventEditor() {
  syncSelectedShotId();
  const shots = orderedShotsByTime();
  const positionSelect = $("timing-event-position");
  const addButton = $("add-timing-event");
  if (!positionSelect || !addButton) return;

  const previousPosition = positionSelect.value;
  const selectedIndex = selectedShotId
    ? shots.findIndex((shot) => shot.id === selectedShotId)
    : -1;

  positionSelect.innerHTML = "";
  shots.forEach((shot, index) => {
    const beforeOption = document.createElement("option");
    beforeOption.value = `::${shot.id}`;
    beforeOption.textContent = `Before Shot ${index + 1}`;
    positionSelect.appendChild(beforeOption);

    const nextShot = shots[index + 1];
    const afterOption = document.createElement("option");
    afterOption.value = `${shot.id}::${nextShot?.id || ""}`;
    afterOption.textContent = nextShot
      ? `Between Shot ${index + 1} and Shot ${index + 2}`
      : `After Shot ${index + 1}`;
    positionSelect.appendChild(afterOption);
  });

  if (previousPosition && Array.from(positionSelect.options).some((option) => option.value === previousPosition)) {
    positionSelect.value = previousPosition;
  } else if (selectedIndex >= 0) {
    positionSelect.value = `${shots[selectedIndex].id}::${shots[selectedIndex + 1]?.id || ""}`;
  }

  addButton.disabled = shots.length === 0;
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
  syncLocalProjectUiState();
  scheduleProjectUiStateApply();
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

function deleteShotById(shotId, source = "selected") {
  if (!shotId) return;
  if (selectedShotId === shotId) {
    pendingSelectionFallback = shotSelectionContext(shotId, state, "index");
    selectedShotId = null;
  }
  timingRowEdits.delete(shotId);
  scoringShotExpansion.delete(shotId);
  if (state?.project?.ui_state?.selected_shot_id === shotId) state.project.ui_state.selected_shot_id = null;
  activity(source === "selected" ? "shot.delete_selected" : "shot.delete_row", { shot_id: shotId, source });
  callApi("/api/shots/delete", { shot_id: shotId });
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

function splitRowEntryLabel(row) {
  return row.label || (row.shot_number ? `Shot ${row.shot_number}` : row.end_label || "Entry");
}

function splitRowRangeLabel(row) {
  return `${row.start_label || "Start"} -> ${row.end_label || (row.shot_number ? `Shot ${row.shot_number}` : "Entry")}`;
}

function splitRowIntervalLabel(row) {
  const intervalLabel = String(row?.interval_label || "").trim();
  if (intervalLabel) return intervalLabel;
  if (Number(row?.shot_number || 0) === 1) return "Draw";
  return "Split";
}

function splitRowSequenceTotalMs(row) {
  return numericMs(row?.sequence_total_ms);
}

function splitRowCumulativeMs(row) {
  const cumulativeMs = numericMs(row?.cumulative_ms);
  if (cumulativeMs !== null && cumulativeMs !== undefined) return cumulativeMs;
  const absoluteMs = numericMs(row?.absolute_time_ms);
  const beepMs = numericMs(state?.metrics?.beep_ms);
  if (absoluteMs === null || absoluteMs === undefined) return null;
  return beepMs === null || beepMs === undefined ? absoluteMs : Math.max(0, absoluteMs - beepMs);
}

function splitRowActions(row) {
  return Array.isArray(row.actions) ? row.actions : [];
}

function splitRowActionSummary(row) {
  return splitRowActions(row).map((action) => action.label).filter(Boolean).join(" • ");
}

function splitRowPrimaryAction(row) {
  if (row?.event_id) {
    return splitRowActions(row).find((action) => action.event_id === row.event_id) || null;
  }
  return splitRowActions(row).find((action) => action.event_id) || null;
}

function splitRowSecondaryActions(row) {
  const primaryAction = splitRowPrimaryAction(row);
  return splitRowActions(row).filter((action) => action !== primaryAction);
}

function splitRowPrimaryLabel(row) {
  const primaryAction = splitRowPrimaryAction(row);
  if (primaryAction?.label) return primaryAction.label;
  const intervalLabel = splitRowIntervalLabel(row);
  return intervalLabel && intervalLabel !== "Split" ? intervalLabel : "";
}

function splitRowSourceLabel(row) {
  const sourceValue = typeof row.source === "string" ? row.source.toLowerCase() : "";
  if (sourceValue === "auto") return "ShotML";
  if (sourceValue === "manual") return "Manual";
  return row.source || "ShotML";
}

function splitRowConfidenceLabel(row) {
  return String(row?.source || "").toLowerCase() === "manual" || row.confidence === null || row.confidence === undefined
    ? "Manual"
    : formatConfidenceValue(row.confidence);
}

function maximumSplitRowActionLabelLength() {
  let longest = 8;
  (state?.split_rows || []).forEach((row) => {
    const labels = [];
    const primaryLabel = splitRowPrimaryLabel(row);
    if (primaryLabel) labels.push(primaryLabel);
    splitRowSecondaryActions(row).forEach((action) => labels.push(action.label || action.kind || "Action"));
    labels.forEach((label) => {
      longest = Math.max(longest, String(label || "").trim().length);
    });
  });
  return longest;
}

function buildSplitRowActionCell(row, expandedTable) {
  const cell = document.createElement("div");
  cell.className = "timeline-action-cell";
  const primaryAction = splitRowPrimaryAction(row);
  const primaryLabel = splitRowPrimaryLabel(row);
  const secondaryActions = splitRowSecondaryActions(row);
  if (!expandedTable) {
    cell.textContent = splitRowActionSummary(row) || primaryLabel || "--";
    return cell;
  }

  if (!primaryLabel && secondaryActions.length === 0) {
    cell.textContent = "--";
    return cell;
  }

  const list = document.createElement("div");
  list.className = "timeline-action-list";
  const appendChip = (labelText, { synthetic = false, eventId = null } = {}) => {
    const chip = document.createElement("span");
    chip.className = `timing-action-chip ${synthetic ? "synthetic" : "recorded"}`;
    const chipLabel = document.createElement("span");
    chipLabel.textContent = labelText;
    chip.appendChild(chipLabel);
    if (eventId) {
      const remove = document.createElement("button");
      remove.type = "button";
      remove.className = "timing-action-remove";
      remove.textContent = "×";
      remove.title = `Remove ${labelText || "timing event"}`;
      remove.setAttribute("aria-label", `Remove timing event ${labelText || "action"}`);
      remove.addEventListener("click", (event) => {
        event.preventDefault();
        event.stopPropagation();
        deleteTimingEvent(eventId);
      });
      chip.appendChild(remove);
    }
    list.appendChild(chip);
  };

  if (primaryLabel) {
    appendChip(primaryLabel, {
      synthetic: !primaryAction?.event_id,
      eventId: primaryAction?.event_id && !primaryAction.synthetic ? primaryAction.event_id : null,
    });
  }
  secondaryActions.forEach((action) => {
    const labelText = action.label || action.kind || "Action";
    appendChip(labelText, {
      synthetic: action.synthetic,
      eventId: action.event_id && !action.synthetic ? action.event_id : null,
    });
  });
  cell.appendChild(list);
  return cell;
}

function renderTimingTable(tableId = "timing-table") {
  const table = $(tableId);
  if (!table) return;
  syncSelectedShotId();
  withPreservedScrollState([table], () => {
    table.innerHTML = "";
    const expandedTable = tableId === "timing-workbench-table";
    table.classList.toggle("interval-timeline-table", true);
    table.classList.toggle("timing-resizable-table", true);
    applyTimingTableColumns(table);
    if (expandedTable) {
      table.style.setProperty("--timing-action-chip-chars", String(maximumSplitRowActionLabelLength()));
    } else {
      table.style.removeProperty("--timing-action-chip-chars");
    }
    const defaultScore = defaultScoreLetter();
    const headers = expandedTable
      ? [
        { label: "", columnId: "lock", resizable: false },
        { label: "Segment", columnId: "segment", resizable: true },
        { label: "Split", columnId: "split", resizable: true },
        { label: "Total", columnId: "total", resizable: true },
        { label: "Action", columnId: "action", resizable: true },
        { label: "Score", columnId: "score", resizable: true },
        { label: "Confidence", columnId: "confidence", resizable: true },
        { label: "Source", columnId: "source", resizable: true },
      ]
      : [
        { label: "Segment", columnId: "segment", resizable: true },
        { label: "Split", columnId: "split", resizable: true },
        { label: "Total", columnId: "total", resizable: true },
        { label: "Action", columnId: "action", resizable: true },
        { label: "Score", columnId: "score", resizable: true },
      ];
    headers.forEach((header) => {
      const cell = document.createElement("div");
      cell.className = "head";
      cell.dataset.timingColumn = header.columnId;
      const label = document.createElement("span");
      label.className = "timing-header-label";
      label.textContent = header.label;
      cell.appendChild(label);
      if (header.resizable && window.innerWidth > 680) {
        const handle = document.createElement("button");
        handle.type = "button";
        handle.className = "timing-column-resize";
        handle.setAttribute("aria-label", `Resize ${header.label} column`);
        handle.title = `Resize ${header.label} column`;
        handle.addEventListener("pointerdown", (event) => {
          event.preventDefault();
          event.stopPropagation();
          beginTimingColumnResize(tableId, header.columnId, event);
        });
        cell.appendChild(handle);
      }
      table.appendChild(cell);
    });

    (state.split_rows || []).forEach((row) => {
      const canEdit = Boolean(row.shot_id);
      const editing = canEdit && expandedTable && timingRowEdits.has(row.shot_id);
      const lowConfidence = isLowConfidence(row.confidence, row.source);
      if (expandedTable) {
        const lockCell = document.createElement("div");
        lockCell.className = "lock-cell";
        if (canEdit) {
          const lockButton = document.createElement("button");
          lockButton.type = "button";
          lockButton.className = `lock-button ${editing ? "unlocked" : "locked"}`;
          lockButton.textContent = editing ? "Lock" : "Unlock";
          lockButton.title = editing ? "Lock row" : "Unlock row";
          lockButton.addEventListener("click", () => toggleTimingRowEdit(row.shot_id));
          lockCell.appendChild(lockButton);
        }
        table.appendChild(lockCell);
      }

      const entryCell = document.createElement("div");
      entryCell.classList.add("timeline-segment-cell");
      entryCell.textContent = splitRowEntryLabel(row);
      if (row.shot_id === selectedShotId) entryCell.classList.add("selected");
      if (lowConfidence) entryCell.classList.add("low-confidence");
      if (canEdit) entryCell.addEventListener("click", () => selectShot(row.shot_id));
      table.appendChild(entryCell);

      const splitCell = document.createElement("div");
      const splitMs = numericMs(row.split_ms);
      if (editing) {
        const editor = document.createElement("span");
        editor.className = "timing-edit-control";
        const input = document.createElement("input");
        input.type = "number";
        input.inputMode = "decimal";
        input.min = "0";
        input.step = "0.01";
        input.className = "timing-split-input";
        input.value = seconds(splitMs ?? row.absolute_time_ms);
        input.setAttribute("aria-label", `Split for ${splitRowEntryLabel(row)}`);
        input.title = "Edit the split in seconds using 0.00 format.";
        input.addEventListener("change", () => updateTimingRowField(row.shot_id, "split_ms", input.value));
        const actions = document.createElement("span");
        actions.className = "timing-edit-actions";
        const restore = document.createElement("button");
        restore.type = "button";
        restore.className = "restore-button";
        restore.textContent = "Restore";
        restore.title = "Restore this split to its original timing.";
        restore.addEventListener("click", () => restoreOriginalSplit(row.shot_id));
        const deleteShot = document.createElement("button");
        deleteShot.type = "button";
        deleteShot.className = "danger-button restore-button";
        deleteShot.textContent = "Delete";
        deleteShot.title = "Delete this shot from the run.";
        deleteShot.addEventListener("click", () => deleteShotById(row.shot_id, "timing_row"));
        actions.append(restore, deleteShot);
        editor.append(input, actions);
        splitCell.appendChild(editor);
      } else {
        splitCell.textContent = splitSeconds(splitMs);
      }
      table.appendChild(splitCell);

      const totalCell = document.createElement("div");
      totalCell.textContent = splitSeconds(splitRowCumulativeMs(row));
      table.appendChild(totalCell);

      const actionCell = buildSplitRowActionCell(row, expandedTable);
      if (row.shot_id === selectedShotId) actionCell.classList.add("selected");
      if (lowConfidence) actionCell.classList.add("low-confidence");
      if (canEdit) actionCell.addEventListener("click", () => selectShot(row.shot_id));
      table.appendChild(actionCell);

      const scoreCell = document.createElement("div");
      if (lowConfidence) scoreCell.classList.add("low-confidence");
      scoreCell.textContent = row.score_letter || defaultScore;
      if (canEdit) scoreCell.addEventListener("click", () => selectShot(row.shot_id));
      table.appendChild(scoreCell);

      if (!expandedTable) return;

      const confidenceCell = document.createElement("div");
      confidenceCell.textContent = splitRowConfidenceLabel(row);
      if (lowConfidence) {
        confidenceCell.classList.add("low-confidence");
        confidenceCell.title = row.confidence === null || row.confidence === undefined
          ? "Manual timing edit."
          : `Review this split manually: model confidence ${formatConfidenceValue(row.confidence)}.`;
      }
      table.appendChild(confidenceCell);

      const sourceCell = document.createElement("div");
      sourceCell.textContent = splitRowSourceLabel(row);
      table.appendChild(sourceCell);
    });
  });
  applyTimingTableColumns(table);
}

function renderTimingTables() {
  renderTimingTable("timing-table");
  renderTimingTable("timing-workbench-table");
  renderTimingEventEditor();
}

function renderSelection() {
  syncSelectedShotId();
  const segment = (state.timing_segments || []).find((item) => item.shot_id === selectedShotId);
  const selectedLabel = segment ? `Shot ${segment.shot_number}` : "No shot selected";
  const splitRow = segment ? splitRowForShot(segment.shot_id) : null;
  const selectedSplitMs = segment ? resolvedSplitMsForShot(segment.shot_id, segment.shot_number, segment.absolute_ms) : null;
  const runMs = splitRowSequenceTotalMs(splitRow);
  const stageMs = numericMs(splitRow?.cumulative_ms) ?? numericMs(segment?.cumulative_ms);
  const intervalLabel = splitRowIntervalLabel(splitRow);
  $("selected-shot-copy").textContent = segment
    ? `${selectedLabel}: ${intervalLabel} ${seconds(selectedSplitMs)}s, ${seconds(runMs)}s since last reset, ${seconds(stageMs)}s from beep.`
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

function isScoringShotExpanded(shotId, activeShotId = null) {
  if (!shotId) return false;
  if (scoringShotExpansion.has(shotId)) return Boolean(scoringShotExpansion.get(shotId));
  return shotId === activeShotId;
}

function setScoringShotExpanded(shotId, expanded) {
  if (!shotId) return;
  scoringShotExpansion.set(shotId, Boolean(expanded));
  syncLocalProjectUiState();
  scheduleProjectUiStateApply();
}

function renderScoringShotList() {
  const list = $("scoring-shot-list");
  if (!list) return;
  withPreservedScrollState([list], () => {
    list.innerHTML = "";
    const scoreOptions = state.scoring_summary?.score_options || ["A", "C", "D", "M", "NS", "M+NS"];
    const penaltyFields = state.scoring_summary?.penalty_fields || [];
    const defaultScore = scoreOptions[0] || "A";
    const activeShotId = selectedShotId || state.project.ui_state.selected_shot_id || state.timing_segments?.[0]?.shot_id || null;
    const visibleShotIds = new Set((state.timing_segments || []).map((segment) => segment.shot_id));
    [...scoringShotExpansion.keys()].forEach((shotId) => {
      if (!visibleShotIds.has(shotId)) scoringShotExpansion.delete(shotId);
    });
    (state.timing_segments || []).forEach((segment) => {
      const expanded = isScoringShotExpanded(segment.shot_id, activeShotId);
      const row = document.createElement("div");
      row.className = `scoring-shot-row ${segment.shot_id === activeShotId ? "selected" : ""}`;
      row.classList.toggle("collapsed", !expanded);
      if (isLowConfidence(segment.confidence, segment.source)) row.classList.add("low-confidence");

      const header = document.createElement("div");
      header.className = "scoring-shot-header";

      const button = document.createElement("button");
      button.type = "button";
      button.className = "scoring-shot-button";
      const title = document.createElement("strong");
      title.textContent = `Shot ${segment.shot_number}`;
      button.append(title);
      button.title = segment.source === "manual"
        ? "Manual shot marker."
        : isLowConfidence(segment.confidence, segment.source)
          ? `Low-confidence ShotML marker (${formatConfidenceValue(segment.confidence)}).`
          : "ShotML-detected shot.";
      button.addEventListener("click", () => selectShot(segment.shot_id));
      header.appendChild(button);

      const toggle = document.createElement("button");
      toggle.type = "button";
      toggle.className = "scoring-shot-toggle";
      toggle.textContent = expanded ? "v" : ">";
      toggle.title = expanded ? "Hide score controls" : "Show score controls";
      toggle.setAttribute("aria-label", `${expanded ? "Hide" : "Show"} score controls for shot ${segment.shot_number}`);
      toggle.addEventListener("click", (event) => {
        event.preventDefault();
        event.stopPropagation();
        setScoringShotExpanded(segment.shot_id, !expanded);
        renderScoringShotList();
      });
      header.appendChild(toggle);

      const controls = document.createElement("div");
      controls.className = "scoring-shot-controls";
      controls.hidden = !expanded;

      const select = document.createElement("select");
      select.className = "shot-score-select";
      select.setAttribute("aria-label", `Score shot ${segment.shot_number}`);
      scoreOptions.forEach((letter) => {
        const option = document.createElement("option");
        option.value = letter;
        const value = state.scoring_summary?.score_values?.[letter] ?? 0;
        const penalty = state.scoring_summary?.score_penalties?.[letter] ?? 0;
        option.textContent = penalty ? `${letter} (${value}, -${penalty})` : `${letter} (${value})`;
        select.appendChild(option);
      });
      select.value = segment.score_letter || defaultScore;

      const applyShotScoring = async () => {
        selectedShotId = segment.shot_id;
        const result = await callApi("/api/scoring/score", {
          shot_id: segment.shot_id,
          letter: select.value || defaultScore,
          penalty_counts: collectPenaltyCounts(controls),
        });
        if (result) refreshReviewMediaFrame();
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

      const deleteShot = document.createElement("button");
      deleteShot.type = "button";
      deleteShot.className = "danger-button restore-button";
      deleteShot.textContent = "Delete";
      deleteShot.title = "Delete this shot from the run.";
      deleteShot.addEventListener("click", () => deleteShotById(segment.shot_id, "scoring_row"));
      controls.appendChild(deleteShot);

      row.append(header, controls);
      list.appendChild(row);
    });
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
  const stagedSource = state?.practiscore_options?.source_name || "";
  const stagedMatchType = state?.practiscore_options?.detected_match_type || "";
  const stagedStages = Array.isArray(state?.practiscore_options?.stage_numbers)
    ? state.practiscore_options.stage_numbers
    : [];
  const stagedCompetitorCount = practiScoreCompetitors().length;
  if (!imported) {
    $("practiscore-status").textContent = stagedSource ? `${stagedSource} loaded` : "No results imported";
    $("scoring-imported-caption").textContent = "No PractiScore stage imported.";
    renderDetailsList("practiscore-import-summary", stagedSource ? [
      ["Source", stagedSource],
      ["Match", stagedMatchType ? formatMatchType(stagedMatchType) : ""],
      ["Stages", stagedStages.length > 0 ? stagedStages.join(", ") : ""],
      ["Competitors", stagedCompetitorCount > 0 ? String(stagedCompetitorCount) : ""],
    ] : []);
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
  const videoRawSeconds = state.scoring_summary?.raw_seconds;
  const rawDeltaSeconds = state.scoring_summary?.raw_delta_seconds;
  $("practiscore-status").textContent = `${formatMatchType(imported.match_type)} Stage ${imported.stage_number} imported`;
  $("scoring-imported-caption").textContent = `Imported ${formatMatchType(imported.match_type)} data for ${imported.competitor_name}.`;
  renderDetailsList("practiscore-import-summary", [
    ["Source", imported.source_name || "Selected file"],
    ["Match", formatMatchType(imported.match_type)],
    ["Stage", stageLabel],
    ["Competitor", imported.competitor_name],
    ["Place", imported.competitor_place ? `#${imported.competitor_place}` : ""],
    ["Division", divisionLabel],
    ["Official Raw", imported.raw_seconds !== null && imported.raw_seconds !== undefined ? `${formatNumber(imported.raw_seconds, 2)}s` : ""],
    ["Video Raw", videoRawSeconds !== null && videoRawSeconds !== undefined ? `${formatNumber(videoRawSeconds, 2)}s` : ""],
    ["Raw Delta", rawDeltaSeconds !== null && rawDeltaSeconds !== undefined ? `${formatNumber(rawDeltaSeconds, 2)}s` : ""],
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
  const persistedLines = (state.project.export.last_log || "")
    .split(/\r?\n/)
    .filter(Boolean);
  const visibleLines = exportLogLines.length > 0 ? exportLogLines : persistedLines;
  const output = $("export-log-output");
  const summary = $("export-log-summary");
  const errorBox = $("export-log-error");
  const status = $("export-log-status");
  const button = $("show-export-log");
  const exportButton = $("export-export-log");
  if (output) {
    output.textContent = visibleLines.join("\n") || "No export log yet.";
    if (activeProcessingPath === "/api/export") output.scrollTop = output.scrollHeight;
  }
  if (summary) {
    summary.textContent = activeProcessingPath === "/api/export"
      ? `Export in progress • ${Math.round(processingProgressPercent)}%`
      : (visibleLines.length > 0 ? "Most recent local export output." : "No export activity yet.");
  }
  if (errorBox) {
    errorBox.hidden = !state.project.export.last_error;
    errorBox.textContent = state.project.export.last_error || "";
  }
  if (status) {
    status.textContent = state.project.export.last_error
      ? `Latest export failed: ${state.project.export.last_error}`
      : activeProcessingPath === "/api/export"
        ? `Export log is updating in real time. Current progress: ${Math.round(processingProgressPercent)}%.`
        : (visibleLines.length > 0
          ? "The last local export log is available in the modal window."
          : "The live export log opens in a separate window so the output settings stay readable while rendering runs.");
  }
  if (button) {
    button.textContent = activeProcessingPath === "/api/export"
      ? `Show Log (${Math.round(processingProgressPercent)}%)`
      : "Show Log";
  }
  if (exportButton) exportButton.disabled = visibleLines.length === 0;
}

function openExportLogModal() {
  const modal = $("export-log-modal");
  if (!modal) return;
  modal.hidden = false;
  renderExportLog();
  const output = $("export-log-output");
  if (output) output.scrollTop = output.scrollHeight;
}

function closeExportLogModal() {
  const modal = $("export-log-modal");
  if (!modal) return;
  modal.hidden = true;
}

function downloadExportLog() {
  const persistedLines = (state?.project?.export?.last_log || "")
    .split(/\r?\n/)
    .filter(Boolean);
  const visibleLines = exportLogLines.length > 0 ? exportLogLines : persistedLines;
  if (visibleLines.length === 0) {
    setStatus("No export log available yet.");
    return;
  }
  downloadTextFile(`${metricsFileStem()}-export-log.txt`, `${visibleLines.join("\n")}\n`, "text/plain");
  setStatus("Downloaded export log.");
}

function buildMetricsRows() {
  const segmentsByShotId = new Map((state.timing_segments || []).map((segment) => [segment.shot_id, segment]));
  const beepMs = numericMs(state?.metrics?.beep_ms);
  const defaultScore = defaultScoreLetter();
  return (state.split_rows || []).map((row) => {
    const segment = row.shot_id ? (segmentsByShotId.get(row.shot_id) || null) : null;
    const absoluteMs = numericMs(row.absolute_time_ms);
    const fallbackCumulativeMs = numericMs(segment?.cumulative_ms) ?? (
      absoluteMs === null
        ? null
        : (beepMs === null ? absoluteMs : Math.max(0, absoluteMs - beepMs))
    );
    const source = segment ? (segment.source || "") : (row.source || "");
    const confidence = segment ? (segment.confidence ?? null) : (row.confidence ?? null);
    const penaltyCounts = segment?.penalty_counts || row.penalty_counts;
    return {
      rowId: row.row_id,
      rowType: row.row_type,
      shotId: row.shot_id,
      shotNumber: row.shot_number,
      label: splitRowEntryLabel(row),
      intervalLabel: splitRowIntervalLabel(row),
      absoluteMs,
      splitMs: numericMs(row.split_ms),
      sequenceTotalMs: splitRowSequenceTotalMs(row),
      cumulativeMs: numericMs(row.cumulative_ms) ?? fallbackCumulativeMs,
      actionSummary: splitRowActionSummary(row),
      scoreLetter: segment?.score_letter || row.score_letter || defaultScore,
      penaltyText: formatPenaltyCountsText(penaltyCounts),
      source,
      confidence,
    };
  });
}

function renderMetricsPanel() {
  const summaryGrid = $("metrics-summary-grid");
  const trendList = $("metrics-trend-list");
  const scoreStatus = $("metrics-score-status");
  if (!summaryGrid || !trendList || !scoreStatus) return;

  const summaryCards = [
    ["Draw", splitSeconds(state.metrics.draw_ms), "First-shot timing"],
    ["Raw", splitSeconds(state.metrics.raw_time_ms ?? state.metrics.stage_time_ms), "Beep to final shot"],
    ["Shots", String(state.metrics.total_shots || 0), "Current timeline shots"],
    ["Avg Split", splitSeconds(state.metrics.average_split_ms), "Average split"],
    ["Beep", splitSeconds(state.metrics.beep_ms), "Start marker"],
    [state.scoring_summary?.display_label || "Result", state.scoring_summary?.display_value || "--", "Scoring summary"],
  ];
  summaryGrid.innerHTML = "";
  summaryCards.forEach(([label, value, caption]) => {
    const card = document.createElement("article");
    card.className = "metric-card";
    const eyebrow = document.createElement("small");
    eyebrow.textContent = label;
    const strong = document.createElement("strong");
    strong.textContent = value;
    const hint = document.createElement("span");
    hint.className = "hint";
    hint.textContent = caption;
    card.append(eyebrow, strong, hint);
    summaryGrid.appendChild(card);
  });

  withPreservedScrollState([trendList], () => {
    trendList.innerHTML = "";
    const rows = buildMetricsRows();
    if (rows.length === 0) {
      const empty = document.createElement("div");
      empty.className = "hint";
      empty.textContent = "No timing segments yet.";
      trendList.appendChild(empty);
    } else {
      rows.forEach((entry) => {
        const row = document.createElement("div");
        row.className = "metrics-row";
        const label = document.createElement("strong");
        label.textContent = `${entry.label} • ${entry.intervalLabel}`;
        const meta = document.createElement("span");
        meta.textContent = entry.absoluteMs === null ? "Timing" : `At ${precise(entry.absoluteMs)}s`;
        const split = document.createElement("span");
        split.textContent = entry.splitMs === null || entry.splitMs === undefined
          ? "Split --.--"
          : `Split ${splitSeconds(entry.splitMs)}`;
        const cumulative = document.createElement("span");
        cumulative.textContent = entry.sequenceTotalMs === null || entry.sequenceTotalMs === undefined
          ? "Run --.--"
          : `Run ${splitSeconds(entry.sequenceTotalMs)}`;
        const detail = document.createElement("small");
        const sourceLabel = entry.source === "manual"
          ? "Manual"
          : (entry.confidence === null || entry.confidence === undefined || entry.confidence === ""
              ? entry.source
              : formatConfidenceValue(entry.confidence));
        const detailParts = [
          entry.cumulativeMs === null || entry.cumulativeMs === undefined ? "" : `Stage ${splitSeconds(entry.cumulativeMs)}`,
          entry.actionSummary,
          entry.scoreLetter ? `Score ${entry.scoreLetter}` : "",
          entry.penaltyText,
          sourceLabel,
        ].filter(Boolean);
        detail.textContent = detailParts.join(" • ") || "Timing";
        row.append(label, meta, split, cumulative, detail);
        trendList.appendChild(row);
      });
    }
  });

  const summary = state.scoring_summary || {};
  const imported = summary.imported_stage || {};
  scoreStatus.dataset.importedSource = imported.source_name || "";
  scoreStatus.dataset.importedStage = imported.stage_number ?? "";
  scoreStatus.dataset.importedCompetitor = imported.competitor_name || "";
  scoreStatus.dataset.importedPlace = imported.competitor_place ?? "";
  scoreStatus.textContent = summary.enabled
    ? `${summary.display_label || "Result"} ${summary.display_value || "--"}`
    : "Scoring disabled.";
  renderDetailsList("metrics-score-summary", [
    ["Ruleset", summary.ruleset_name || ""],
    [summary.display_label || "Result", summary.display_value || ""],
    ["Shot Points", formatNumber(summary.shot_points, 2)],
    [summary.penalty_label || "Penalties", formatNumber(summary.total_penalties, 2)],
    ["Raw Time", summary.raw_seconds !== null && summary.raw_seconds !== undefined ? `${formatNumber(summary.raw_seconds, 2)}s` : ""],
    ["Imported", summary.imported_stage?.source_name || ""],
  ]);
}

function metricsFileStem() {
  const raw = state?.project?.name || fileName(state?.project?.primary_video?.path || "") || "splitshot";
  return raw
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "") || "splitshot";
}

function csvEscape(value) {
  const text = value === null || value === undefined ? "" : String(value);
  return /[",\n]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text;
}

function downloadTextFile(filename, text, mimeType = "text/plain") {
  const blob = new Blob([text], { type: `${mimeType};charset=utf-8` });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 0);
}

function buildMetricsCsv() {
  const summary = state.scoring_summary || {};
  const rows = buildMetricsRows();
  const headers = [
    "project",
    "primary_video",
    "result_label",
    "result_value",
    "raw_time_s",
    "shot_number",
    "segment_label",
    "interval_label",
    "actions",
    "source",
    "absolute_s",
    "split_s",
    "cumulative_s",
    "score_letter",
    "penalties",
    "confidence",
  ];
  const metricsRows = rows.map((entry) => [
    state.project.name || "",
    fileName(state.project.primary_video.path || ""),
    summary.display_label || "Result",
    summary.display_value || "",
    summary.raw_seconds ?? "",
    entry.shotNumber || "",
    entry.label || "",
    entry.intervalLabel || "",
    entry.actionSummary || "",
    entry.source || "",
    entry.absoluteMs === null ? "" : precise(entry.absoluteMs),
    entry.splitMs === null || entry.splitMs === undefined ? "" : precise(entry.splitMs),
    entry.cumulativeMs === null || entry.cumulativeMs === undefined ? "" : precise(entry.cumulativeMs),
    entry.scoreLetter || "",
    entry.penaltyText || "",
    entry.confidence ?? "",
  ]);
  return [headers.join(","), ...metricsRows.map((row) => row.map(csvEscape).join(","))].join("\n");
}

function buildMetricsText() {
  const summary = state.scoring_summary || {};
  const rows = buildMetricsRows();
  const lines = [
    state.project.name || "Untitled Project",
    `Video: ${fileName(state.project.primary_video.path || "")}`,
    `${summary.display_label || "Result"}: ${summary.display_value || "--"}`,
    `Raw Time: ${summary.raw_seconds !== null && summary.raw_seconds !== undefined ? `${formatNumber(summary.raw_seconds, 2)}s` : "--"}`,
    `Shots: ${state.metrics.total_shots || 0}`,
    "",
    "Split Timeline",
  ];
  rows.forEach((entry) => {
    const parts = [
      entry.label || (entry.shotNumber ? `Shot ${entry.shotNumber}` : "Entry"),
      entry.intervalLabel ? `Interval ${entry.intervalLabel}` : "",
      entry.absoluteMs === null ? "Absolute --.--" : `Absolute ${precise(entry.absoluteMs)}s`,
      entry.splitMs === null || entry.splitMs === undefined ? "Split --.--" : `Split ${splitSeconds(entry.splitMs)}`,
      entry.cumulativeMs === null || entry.cumulativeMs === undefined ? "Total --.--" : `Total ${splitSeconds(entry.cumulativeMs)}`,
    ];
    if (entry.actionSummary) parts.push(`Actions ${entry.actionSummary}`);
    if (entry.scoreLetter) parts.push(`Score ${entry.scoreLetter}`);
    if (entry.penaltyText) parts.push(entry.penaltyText);
    if (entry.source === "manual") parts.push("Manual");
    else if (entry.confidence !== null && entry.confidence !== undefined && entry.confidence !== "") {
      parts.push(formatConfidenceValue(entry.confidence));
    }
    lines.push(`- ${parts.join(" | ")}`);
  });
  return lines.join("\n");
}

function exportMetrics(kind) {
  if (!state?.project) return;
  const stem = metricsFileStem();
  if (kind === "csv") {
    downloadTextFile(`${stem}-metrics.csv`, buildMetricsCsv(), "text/csv");
    setStatus("Downloaded metrics CSV.");
    return;
  }
  downloadTextFile(`${stem}-metrics.txt`, buildMetricsText(), "text/plain");
  setStatus("Downloaded metrics summary.");
}

function syncExportPathControl() {
  const input = $("export-path");
  if (!input) return;
  const savedPath = state.project.export.output_path || "";
  const defaultPath = state.project.path
    ? `${state.project.path}/Output/output.mp4`
    : `${state.default_project_path || "~/splitshot"}/output.mp4`;
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
  syncControlValue($("project-name"), projectDetailValue("name"));
  syncControlValue($("project-description"), projectDetailValue("description"));
  syncControlValue($("match-type"), state.project.scoring.match_type || "");
  renderPractiScoreOptionLists({
    stage_number: state.project.scoring.stage_number ?? "",
    competitor_name: state.project.scoring.competitor_name || "",
    competitor_place: state.project.scoring.competitor_place ?? "",
  });
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
  syncControlChecked($("timer-lock-to-stack"), overlayBadgeLockedToStack("timer", state.project.overlay));
  syncControlChecked($("draw-lock-to-stack"), overlayBadgeLockedToStack("draw", state.project.overlay));
  syncControlChecked($("score-lock-to-stack"), overlayBadgeLockedToStack("score", state.project.overlay));
  syncOverlayBubbleSizeControls();
  syncControlValue($("overlay-font-family"), state.project.overlay.font_family);
  syncControlValue($("overlay-font-size"), state.project.overlay.font_size);
  syncControlChecked($("overlay-font-bold"), state.project.overlay.font_bold);
  syncControlChecked($("overlay-font-italic"), state.project.overlay.font_italic);
  syncControlChecked($("show-timer"), state.project.overlay.show_timer);
  syncControlChecked($("show-draw"), state.project.overlay.show_draw);
  syncControlChecked($("show-shots"), state.project.overlay.show_shots);
  syncControlChecked($("show-score"), state.project.overlay.show_score);
  syncControlChecked($("review-lock-to-stack"), reviewBoxesLockedToOverlayStack(state.project.overlay));
  syncOverlayCoordinateControlState();
  syncOverlayBubbleLockControlState();
  renderTextBoxEditors();
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
  renderMetricsPanel();
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
            <button type="button" class="color-swatch-button" data-color-label="Badge background" data-field="background_color"></button>
            <input type="text" class="color-hex-input" inputmode="text" spellcheck="false" aria-label="Background hex value" placeholder="#111827" />
          </span>
        </label>
        <label class="color-field"><span class="style-card-label">Text</span>
          <span class="color-control-pair">
            <button type="button" class="color-swatch-button" data-color-label="Badge text" data-field="text_color"></button>
            <input type="text" class="color-hex-input" inputmode="text" spellcheck="false" aria-label="Text hex value" placeholder="#F9FAFB" />
          </span>
        </label>
        <label class="opacity-field"><span class="style-card-label">Opacity</span>
          <span class="opacity-control-pair">
            <input type="range" data-field="opacity" min="0" max="1" step="0.01" />
            <span class="opacity-percent-field">
              <input type="number" class="opacity-percent-input" data-opacity-percent="opacity" min="0" max="100" step="1" value="90" aria-label="Opacity percent" />
              <span class="opacity-percent-suffix">%</span>
            </span>
          </span>
        </label>
      `;
      bindOverlayColorInput(card.querySelector('[data-field="background_color"]'));
      bindOverlayColorInput(card.querySelector('[data-field="text_color"]'));
      bindOpacityPercentPair(card.querySelector('[data-field="opacity"]'), card.querySelector('[data-opacity-percent="opacity"]'));
      grid.appendChild(card);
    }
    const heading = card.querySelector("h4");
    if (heading && heading.textContent !== title) heading.textContent = title;
    syncControlValue(card.querySelector('[data-field="background_color"]'), style.background_color);
    syncControlValue(card.querySelector('[data-field="text_color"]'), style.text_color);
    syncControlValue(card.querySelector('[data-field="opacity"]'), style.opacity);
    syncOpacityPercentControl(card.querySelector('[data-opacity-percent="opacity"]'), style.opacity);
  });

  const scoreGrid = $("score-color-grid");
  const scoreOptions = scoringColorOptions();
  const scoreKeys = scoreOptions.map((option) => option.key);
  const validLetters = new Set(scoreKeys);
  scoreGrid.querySelectorAll(".score-color-input[data-letter]").forEach((input) => {
    if (!validLetters.has(input.dataset.letter)) {
      input.closest("label")?.remove();
    }
  });
  scoreOptions.forEach((option) => {
    const key = option.key;
    const labelText = option.label || key;
    let input = [...scoreGrid.querySelectorAll(".score-color-input[data-letter]")].find((candidate) => candidate.dataset.letter === key);
    if (!input) {
      const label = document.createElement("label");
      label.className = "color-field score-color-field";
      label.title = option.description || labelText;
      const text = document.createElement("span");
      text.className = "score-color-label";
      text.textContent = labelText;
      label.appendChild(text);
      const pair = document.createElement("span");
      pair.className = "color-control-pair";
      input = document.createElement("button");
      input.type = "button";
      input.className = "score-color-input color-swatch-button";
      input.dataset.letter = key;
      input.dataset.colorLabel = `${labelText} color`;
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
    syncControlValue(
      input,
      state.project.overlay.scoring_colors[key]
      || "#ffffff",
    );
    const label = input.closest("label");
    if (label) label.title = option.description || labelText;
  });
}

function clearMergeSourceCommitTimers({ clearPayloads = false } = {}) {
  mergeSourceCommitTimers.forEach((timerId) => window.clearTimeout(timerId));
  mergeSourceCommitTimers.clear();
  if (clearPayloads) pendingMergeSourcePayloads.clear();
}

function scheduleMergeSourceCommit(payload) {
  const sourceId = String(payload?.source_id || "").trim();
  if (!sourceId) return;
  pendingMergeSourcePayloads.set(sourceId, payload);
  const existingTimer = mergeSourceCommitTimers.get(sourceId);
  if (existingTimer !== undefined) window.clearTimeout(existingTimer);
  const timerId = window.setTimeout(() => {
    mergeSourceCommitTimers.delete(sourceId);
    const nextPayload = pendingMergeSourcePayloads.get(sourceId);
    pendingMergeSourcePayloads.delete(sourceId);
    if (nextPayload) callApi("/api/merge/source", nextPayload);
  }, 120);
  mergeSourceCommitTimers.set(sourceId, timerId);
}

async function flushPendingMergeSourceCommits({ keepalive = false } = {}) {
  if (pendingMergeSourcePayloads.size === 0) return;
  clearMergeSourceCommitTimers();
  const payloads = [...pendingMergeSourcePayloads.values()];
  pendingMergeSourcePayloads.clear();
  if (keepalive) {
    payloads.forEach((payload) => sendKeepaliveJson("/api/merge/source", payload));
    return;
  }
  for (const payload of payloads) {
    await callApi("/api/merge/source", payload);
  }
}

function renderMergeMediaList() {
  const list = $("merge-media-list");
  if (!list) return;
  const mergeSources = state?.project?.merge_sources || [];
  withPreservedScrollState([list], () => {
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

      const readSourcePayload = () => {
        const nextSize = clampNumber(Number(controls.querySelector('[data-merge-source-field="size"]')?.value) || 35, 10, 95);
        const nextX = normalizedCoordinateValue(controls.querySelector('[data-merge-source-field="x"]')?.value) ?? 1;
        const nextY = normalizedCoordinateValue(controls.querySelector('[data-merge-source-field="y"]')?.value) ?? 1;
        return {
          source_id: sourceId,
          pip_size_percent: nextSize,
          pip_x: nextX,
          pip_y: nextY,
        };
      };

      const previewSourceUpdate = () => {
        const payload = readSourcePayload();
        updateLocalMergeSourcePosition(sourceId, payload.pip_x, payload.pip_y, payload.pip_size_percent);
        scheduleInteractionPreviewRender({ video: true });
        return payload;
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
        input.addEventListener("input", previewSourceUpdate);
        input.addEventListener("change", () => scheduleMergeSourceCommit(previewSourceUpdate()));
        input.addEventListener("blur", () => scheduleMergeSourceCommit(readSourcePayload()));
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
        previewSourceUpdate();
      });
      sizeInput.addEventListener("change", () => scheduleMergeSourceCommit(previewSourceUpdate()));
      sizeInput.addEventListener("blur", () => scheduleMergeSourceCommit(readSourcePayload()));
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
  });
}

function visibleTimingEventsByShot(currentIndex) {
  const shots = orderedShotsByTime();
  const shotIndexById = new Map(shots.map((shot, index) => [shot.id, index]));
  const beforeByShotId = new Map();
  const afterByShotId = new Map();
  const tailEvents = [];
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
      return;
    }
    if (afterIndex !== undefined && afterIndex === currentIndex && currentIndex === shots.length - 1 && !event.before_shot_id) {
      tailEvents.push(eventPayload);
    }
  });
  return { beforeByShotId, afterByShotId, tailEvents };
}

function textBiasForDirection(direction) {
  if (direction === "left") return "right";
  if (direction === "right") return "left";
  return "center";
}

function overlayBadgeContentText(content) {
  if (typeof content === "string") return content;
  if (Array.isArray(content)) return content.map((part) => part?.text || "").join("");
  return String(content?.text || "");
}

function overlayBadgeFontSizePx() {
  const badgeSize = state?.project?.overlay?.badge_size || "M";
  return Math.max(8, Number(state?.project?.overlay?.font_size || BADGE_FONT_SIZES[badgeSize] || BADGE_FONT_SIZES.M));
}

function overlayBadgeMeasureContext() {
  if (!overlayBadgeMeasureCanvas) overlayBadgeMeasureCanvas = document.createElement("canvas");
  return overlayBadgeMeasureCanvas.getContext("2d");
}

function overlayBadgeFontSpec() {
  const overlay = state?.project?.overlay || {};
  const fontStyle = overlay.font_italic ? "italic" : "normal";
  const fontWeight = overlay.font_bold ? "700" : "400";
  const fontSize = overlayBadgeFontSizePx();
  const fontFamily = overlay.font_family || "Helvetica Neue";
  return `${fontStyle} ${fontWeight} ${fontSize}px "${fontFamily}"`;
}

function measureOverlayBadgeContent(content) {
  const context = overlayBadgeMeasureContext();
  const fallbackFontSize = overlayBadgeFontSizePx();
  if (!context) {
    return { width: 0, height: fallbackFontSize };
  }
  context.font = overlayBadgeFontSpec();
  const lines = overlayBadgeContentText(content).split(/\r?\n/);
  let maxWidth = 0;
  let totalHeight = 0;
  lines.forEach((line) => {
    const metrics = context.measureText(line || " ");
    const lineHeight = Math.max(
      fallbackFontSize,
      Math.ceil((metrics.actualBoundingBoxAscent || 0) + (metrics.actualBoundingBoxDescent || 0)),
    );
    maxWidth = Math.max(maxWidth, Math.ceil(metrics.width));
    totalHeight += lineHeight;
  });
  return {
    width: maxWidth,
    height: Math.max(fallbackFontSize, totalHeight),
  };
}

function overlayAutoSizedBadgeContents() {
  if (!state?.project?.overlay) return [];
  const overlay = state.project.overlay;
  const contents = [];
  if (overlay.show_timer) contents.push(`Timer ${seconds(state?.metrics?.raw_time_ms)}`);
  if (overlay.show_draw && numericMs(state?.metrics?.draw_ms) !== null && Number(state.metrics.draw_ms) > 0) {
    contents.push(`Draw ${seconds(state.metrics.draw_ms)}`);
  }
  if (overlay.show_shots) {
    const shots = orderedShotsByTime();
    const splitRowsByShotId = new Map((state?.split_rows || []).filter((row) => row.shot_id).map((row) => [row.shot_id, row]));
    shots.forEach((shot, index) => {
      const splitRow = splitRowsByShotId.get(shot.id) || null;
      const splitMs = resolvedSplitMsForShot(shot.id, index + 1, shot.time_ms);
      contents.push(scoreBadgeContent(shot, index + 1, splitSeconds(splitMs), splitRowIntervalLabel(splitRow)));
    });
  }
  const summary = state?.scoring_summary || {};
  if (overlay.show_score && state?.project?.scoring?.enabled && summary.display_value && summary.display_value !== "--") {
    contents.push(`${summary.display_label} ${summary.display_value}`);
  }
  return contents;
}

function overlayAutoBubbleSize() {
  const overlay = state?.project?.overlay;
  if (!overlay) return { width: 0, height: 0 };
  const texts = overlayAutoSizedBadgeContents().map((content) => overlayBadgeContentText(content)).filter(Boolean);
  const cacheKey = [
    overlay.font_family || "Helvetica Neue",
    String(overlayBadgeFontSizePx()),
    overlay.font_bold ? "700" : "400",
    overlay.font_italic ? "italic" : "normal",
    ...texts,
  ].join("\u0001");
  if (cacheKey === overlayAutoBubbleCacheKey) return overlayAutoBubbleCache;
  let maxWidth = 0;
  let maxHeight = 0;
  texts.forEach((text) => {
    const measurement = measureOverlayBadgeContent(text);
    maxWidth = Math.max(maxWidth, measurement.width);
    maxHeight = Math.max(maxHeight, measurement.height);
  });
  overlayAutoBubbleCacheKey = cacheKey;
  overlayAutoBubbleCache = {
    width: maxWidth > 0 ? Math.ceil(maxWidth + (OVERLAY_BADGE_PADDING_X_PX * 2)) : 0,
    height: maxHeight > 0 ? Math.ceil(maxHeight + (OVERLAY_BADGE_PADDING_Y_PX * 2)) : 0,
  };
  return overlayAutoBubbleCache;
}

function syncOverlayBubbleSizeControls() {
  const widthInput = $("bubble-width");
  const heightInput = $("bubble-height");
  const overlay = state?.project?.overlay;
  const autoSize = overlayAutoBubbleSize();
  if (widthInput) {
    widthInput.placeholder = autoSize.width > 0 ? String(autoSize.width) : "auto";
    if (!controlIsActive(widthInput)) {
      widthInput.value = overlay?.bubble_width > 0 ? String(overlay.bubble_width) : "";
    }
  }
  if (heightInput) {
    heightInput.placeholder = autoSize.height > 0 ? String(autoSize.height) : "auto";
    if (!controlIsActive(heightInput)) {
      heightInput.value = overlay?.bubble_height > 0 ? String(overlay.bubble_height) : "";
    }
  }
}

function badgeElement(
  content,
  style,
  size,
  badgeColorOverride = null,
  widthOverride = null,
  heightOverride = null,
  textBias = "center",
  scale = 1,
  autoBubbleSize = null,
) {
  const text = overlayBadgeContentText(content);
  const textRuns = Array.isArray(content) ? content : content?.runs || null;
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
  badge.textContent = "";
  if (textRuns && textRuns.length > 0) {
    textRuns.forEach((part) => {
      const fragment = document.createElement("span");
      fragment.textContent = part?.text || "";
      if (part?.color) fragment.style.color = part.color;
      fragment.style.whiteSpace = "pre";
      badge.appendChild(fragment);
    });
  } else {
    badge.textContent = text;
  }
  const scaledPaddingY = scaledOverlayPixelValue(OVERLAY_BADGE_PADDING_Y_PX, scale, 0);
  const scaledPaddingX = scaledOverlayPixelValue(OVERLAY_BADGE_PADDING_X_PX, scale, 0);
  badge.style.padding = `${scaledPaddingY}px ${scaledPaddingX}px`;
  badge.style.margin = "0";
  const resolvedWidth = widthOverride > 0
    ? widthOverride
    : state.project.overlay.bubble_width > 0
      ? state.project.overlay.bubble_width
      : autoBubbleSize?.width || 0;
  const resolvedHeight = heightOverride > 0
    ? heightOverride
    : state.project.overlay.bubble_height > 0
      ? state.project.overlay.bubble_height
      : autoBubbleSize?.height || 0;
  const scaledWidth = resolvedWidth > 0 ? scaledOverlayPixelValue(resolvedWidth, scale, 1) : 0;
  const scaledHeight = resolvedHeight > 0 ? scaledOverlayPixelValue(resolvedHeight, scale, 1) : 0;
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

function previewFrameClientRect(video, container) {
  if (!container) return null;
  const geometry = previewFrameGeometry(video, container);
  if (!geometry?.frameRect) return container.getBoundingClientRect();
  const containerRect = container.getBoundingClientRect();
  return {
    left: containerRect.left + geometry.frameRect.left,
    top: containerRect.top + geometry.frameRect.top,
    width: geometry.frameRect.width,
    height: geometry.frameRect.height,
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
  const scaledGap = scaledOverlayPixelValue(overlaySpacing, scale, 0);
  const scaledMargin = scaledOverlayPixelValue(overlayMargin, scale, 0);
  overlay.style.padding = `${scaledMargin}px`;
  overlay.style.gap = `${scaledGap}px`;
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

function positionTextBoxBadge(badge, box, frameRect, { anchorBadge = null, scale = 1 } = {}) {
  if (box.quadrant === ABOVE_FINAL_TEXT_BOX_VALUE) {
    if (!(anchorBadge instanceof HTMLElement)) return false;
    const anchorRect = anchorBadge.getBoundingClientRect();
    const badgeRect = badge.getBoundingClientRect();
    const gap = scaledOverlayPixelValue(overlaySpacing, scale, 0);
    const halfWidth = Math.max(0, badgeRect.width / 2);
    const centerX = clamp(
      (anchorRect.left - frameRect.left) + (anchorRect.width / 2),
      halfWidth,
      Math.max(halfWidth, frameRect.width - halfWidth),
    );
    const top = clamp(
      (anchorRect.top - frameRect.top) - gap,
      Math.max(0, badgeRect.height),
      Math.max(0, frameRect.height),
    );
    badge.style.position = "absolute";
    badge.style.margin = "0";
    badge.style.left = `${centerX}px`;
    badge.style.top = `${top}px`;
    badge.style.transform = "translate(-50%, -100%)";
    return true;
  }
  const customX = normalizedCoordinateValue(box.x);
  const customY = normalizedCoordinateValue(box.y);
  if (customX === null || customY === null) return false;
  badge.style.position = "absolute";
  badge.style.margin = "0";
  badge.style.left = `${clamp(customX * frameRect.width, 0, frameRect.width)}px`;
  badge.style.top = `${clamp(customY * frameRect.height, 0, frameRect.height)}px`;
  badge.style.transform = "translate(-50%, -50%)";
  return true;
}

function configureTextBoxGroup(group, quadrant, frameRect, scale = 1) {
  const [vertical = "top", horizontal = "left"] = String(quadrant || "top_left").split("_");
  const horizontalLayout = vertical === "middle";
  group.classList.remove("horizontal", "vertical");
  group.classList.add(horizontalLayout ? "horizontal" : "vertical");
  group.style.justifyContent = alignToEdge(vertical);
  group.style.alignItems = alignToEdge(horizontal);
  const scaledGap = scaledOverlayPixelValue(overlaySpacing, scale, 0);
  const scaledMargin = scaledOverlayPixelValue(overlayMargin, scale, 0);
  group.style.padding = `${scaledMargin}px`;
  group.style.gap = `${scaledGap}px`;
  group.style.left = "0px";
  group.style.top = "0px";
  group.style.width = "100%";
  group.style.height = "100%";
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

function visibleOverlayTextBoxEntries(finalShotReached) {
  return overlayTextBoxes()
    .map((box, index) => {
      const textValue = overlayTextBoxDisplayText(box).trim();
      if (!box.enabled || !textValue || (box.source === "imported_summary" && !finalShotReached)) return null;
      return { box, index, textValue };
    })
    .filter(Boolean);
}

function overlayTextBoxStyle(box) {
  return {
    background_color: box.background_color || state.project.overlay.hit_factor_badge.background_color,
    text_color: box.text_color || state.project.overlay.hit_factor_badge.text_color,
    opacity: box.opacity ?? state.project.overlay.hit_factor_badge.opacity,
  };
}

function customOverlayKey(entries, frameRect, overlayScale, finalScoreBadge) {
  const overlayState = state?.project?.overlay || {};
  const finalScoreRect = finalScoreBadge?.getBoundingClientRect();
  return JSON.stringify({
    frame: roundedRect(frameRect),
    scale: Math.round(overlayScale * 1000) / 1000,
    spacing: overlaySpacing,
    margin: overlayMargin,
    style_type: overlayStyleMode,
    badge_size: overlayState.badge_size,
    bubble_width: overlayState.bubble_width,
    bubble_height: overlayState.bubble_height,
    font_family: overlayState.font_family,
    font_size: overlayState.font_size,
    font_bold: overlayState.font_bold,
    font_italic: overlayState.font_italic,
    final_score: roundedRect(finalScoreRect),
    entries: entries.map(({ box, textValue }) => ({
      id: box.id,
      source: box.source,
      text: textValue,
      quadrant: box.quadrant,
      x: box.x,
      y: box.y,
      width: box.width,
      height: box.height,
      background_color: box.background_color,
      text_color: box.text_color,
      opacity: box.opacity,
    })),
  });
}

function renderCustomOverlayBoxes(customOverlay, entries, frameRect, overlayScale, size, finalScoreBadge) {
  customOverlay.innerHTML = "";
  const textBoxGroups = new Map();
  entries.forEach(({ box, index, textValue }) => {
    const customBadge = badgeElement(
      textValue,
      overlayTextBoxStyle(box),
      size,
      null,
      box.width,
      box.height,
      "center",
      overlayScale,
    );
    customBadge.dataset.textBoxDrag = "true";
    customBadge.dataset.textBoxId = box.id;
    customBadge.dataset.textBoxLabel = overlayTextBoxLabel(box, index);
    customOverlay.appendChild(customBadge);
    if (positionTextBoxBadge(customBadge, box, frameRect, { anchorBadge: finalScoreBadge, scale: overlayScale })) {
      return;
    }
    customBadge.remove();
    const quadrant = box.quadrant === ABOVE_FINAL_TEXT_BOX_VALUE
      ? "top_middle"
      : (box.quadrant || "top_right");
    let group = textBoxGroups.get(quadrant);
    if (!group) {
      group = document.createElement("div");
      group.className = "text-box-group";
      configureTextBoxGroup(group, quadrant, frameRect, overlayScale);
      textBoxGroups.set(quadrant, group);
      customOverlay.appendChild(group);
    }
    group.appendChild(customBadge);
  });
  customOverlay.classList.toggle("has-badge", customOverlay.childElementCount > 0);
}

function beginTextBoxDrag(event) {
  const customOverlay = $("custom-overlay");
  const customBadge = event.target instanceof Element
    ? event.target.closest("[data-text-box-drag]")
    : null;
  const boxId = customBadge?.dataset?.textBoxId || "";
  const box = overlayTextBoxes().find((item) => item.id === boxId);
  if (
    event.button !== 0
    || !customOverlay
    || !customOverlay.classList.contains("has-badge")
    || !box
    || !overlayTextBoxDisplayText(box).trim()
    || !(customBadge instanceof HTMLElement)
    || !customOverlay.contains(customBadge)
  ) return;
  event.preventDefault();
  const stage = $("video-stage");
  const frameRect = previewFrameClientRect($("primary-video"), stage) || stage.getBoundingClientRect();
  const badgeRect = customBadge.getBoundingClientRect();
  const startX = clamp((badgeRect.left - frameRect.left + badgeRect.width / 2) / frameRect.width, 0, 1);
  const startY = clamp((badgeRect.top - frameRect.top + badgeRect.height / 2) / frameRect.height, 0, 1);
  textBoxDrag = {
    boxId,
    target: customOverlay,
    pointerId: event.pointerId,
    startClientX: event.clientX,
    startClientY: event.clientY,
    startX,
    startY,
  };
  capturePointer(customOverlay, event.pointerId);
  customOverlay.classList.add("dragging");
  activity("overlay.text_box.drag.start", { box_id: boxId, x: startX, y: startY });
}

function moveTextBoxDrag(event) {
  if (!textBoxDrag) return;
  if (event.pointerId !== undefined && textBoxDrag.pointerId !== undefined && event.pointerId !== textBoxDrag.pointerId) return;
  const stage = $("video-stage");
  if (!stage) return;
  const frameRect = previewFrameClientRect($("primary-video"), stage) || stage.getBoundingClientRect();
  const width = Math.max(1, frameRect.width || 0);
  const height = Math.max(1, frameRect.height || 0);
  const { startClientX, startClientY, startX, startY } = textBoxDrag;
  const deltaX = (event.clientX - startClientX) / width;
  const deltaY = (event.clientY - startClientY) / height;
  const newX = clamp(startX + deltaX, 0, 1);
  const newY = clamp(startY + deltaY, 0, 1);
  const boxes = overlayTextBoxes().map((box) => box.id === textBoxDrag.boxId
    ? normalizeOverlayTextBox({ ...box, quadrant: CUSTOM_QUADRANT_VALUE, x: newX, y: newY })
    : box);
  setLocalOverlayTextBoxes(boxes);
  syncOverlayPreviewStateFromControls();
  scheduleInteractionPreviewRender({ overlay: true });
}

function endTextBoxDrag(event) {
  if (!textBoxDrag) return;
  if (event.pointerId !== undefined && textBoxDrag.pointerId !== undefined && event.pointerId !== textBoxDrag.pointerId) return;
  const customOverlay = $("custom-overlay");
  releasePointer(textBoxDrag.target || customOverlay, textBoxDrag.pointerId ?? event.pointerId);
  customOverlay?.classList.remove("dragging");
  const drag = textBoxDrag;
  const box = overlayTextBoxes().find((item) => item.id === drag.boxId);
  activity("overlay.text_box.drag.commit", {
    box_id: drag.boxId,
    x: box?.x ?? null,
    y: box?.y ?? null,
  });
  autoApplyOverlay.cancel();
  textBoxDrag = null;
  flushInteractionPreviewRender();
  queueInspectorScrollRestore();
  callApi("/api/overlay", readOverlayPayload());
  flushDeferredRender();
}

function cancelOverlayDragInteractions(reason = "interrupted") {
  let cleared = false;
  if (overlayBadgeDrag) {
    const drag = overlayBadgeDrag;
    releasePointer(drag.target, drag.pointerId);
    drag.target?.classList?.remove("overlay-dragging");
    overlayBadgeDrag = null;
    activity("overlay.drag.cancel", { kind: drag.kind, reason });
    cleared = true;
  }
  if (textBoxDrag) {
    const drag = textBoxDrag;
    const customOverlay = $("custom-overlay");
    releasePointer(drag.target || customOverlay, drag.pointerId);
    customOverlay?.classList.remove("dragging");
    textBoxDrag = null;
    activity("overlay.text_box.drag.cancel", { box_id: drag.boxId, reason });
    cleared = true;
  }
  if (!cleared) return;
  flushInteractionPreviewRender();
  flushQueuedProjectUiStateApply();
  flushDeferredRender();
}

function overlayDragConfiguration(kind) {
  return {
    timer: { lockId: "timer-lock-to-stack", xId: "timer-x", yId: "timer-y" },
    draw: { lockId: "draw-lock-to-stack", xId: "draw-x", yId: "draw-y" },
    score: { lockId: "score-lock-to-stack", xId: "score-x", yId: "score-y" },
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
  if (config.lockId && $(config.lockId)?.checked) {
    $(config.lockId).checked = false;
    syncOverlayBubbleLockControlState();
    syncOverlayPreviewStateFromControls();
  }
  const stage = $("video-stage");
  const frameRect = previewFrameClientRect($("primary-video"), stage) || stage.getBoundingClientRect();
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
  if (event.pointerId !== undefined && overlayBadgeDrag.pointerId !== undefined && event.pointerId !== overlayBadgeDrag.pointerId) return;
  const config = overlayDragConfiguration(overlayBadgeDrag.kind);
  if (!config) return;
  const stage = $("video-stage");
  const frameRect = previewFrameClientRect($("primary-video"), stage) || stage.getBoundingClientRect();
  const width = Math.max(1, frameRect.width || 0);
  const height = Math.max(1, frameRect.height || 0);
  const deltaX = (event.clientX - overlayBadgeDrag.startClientX) / width;
  const deltaY = (event.clientY - overlayBadgeDrag.startClientY) / height;
  const nextX = clamp(overlayBadgeDrag.startX + deltaX, 0, 1);
  const nextY = clamp(overlayBadgeDrag.startY + deltaY, 0, 1);

  if (config.quadrantId) {
    $(config.quadrantId).value = config.quadrantValue;
    ["timer-x", "timer-y", "draw-x", "draw-y"].forEach((id) => {
      if ($(id)) $(id).value = "";
    });
    syncOverlayCoordinateControlState();
  }
  $(config.xId).value = nextX.toFixed(3);
  $(config.yId).value = nextY.toFixed(3);
  syncOverlayPreviewStateFromControls();
  scheduleInteractionPreviewRender({ overlay: true });
}

function endOverlayBadgeDrag(event) {
  if (!overlayBadgeDrag) return;
  if (event.pointerId !== undefined && overlayBadgeDrag.pointerId !== undefined && event.pointerId !== overlayBadgeDrag.pointerId) return;
  const config = overlayDragConfiguration(overlayBadgeDrag.kind);
  const drag = overlayBadgeDrag;
  releasePointer(drag.target, drag.pointerId ?? event.pointerId);
  drag.target.classList.remove("overlay-dragging");
  overlayBadgeDrag = null;
  flushInteractionPreviewRender();
  if (config) {
    activity("overlay.drag.commit", {
      kind: drag.kind,
      x: normalizedCoordinateValue($(config.xId)?.value),
      y: normalizedCoordinateValue($(config.yId)?.value),
    });
    scheduleOverlayApply();
  }
  flushDeferredRender();
}

function beginMergePreviewDrag(event) {
  if (event.button !== 0 || mergePreviewDrag || state?.project?.merge?.layout !== "pip") return;
  const item = event.target instanceof Element ? event.target.closest(".merge-preview-item[data-source-id]") : null;
  if (!(item instanceof HTMLElement)) return;
  const sourceId = item.dataset.sourceId || "";
  const source = mergeSourceById(sourceId);
  if (!source) return;
  const stage = $("video-stage");
  const frameRect = previewFrameClientRect($("primary-video"), stage) || stage.getBoundingClientRect();
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
  if (event.pointerId !== undefined && mergePreviewDrag.pointerId !== undefined && event.pointerId !== mergePreviewDrag.pointerId) return;
  const source = mergeSourceById(mergePreviewDrag.sourceId);
  if (!source) return;
  const stage = $("video-stage");
  const frameRect = previewFrameClientRect($("primary-video"), stage) || stage.getBoundingClientRect();
  const rect = mergeSourcePipRect(source, frameRect, currentPipSizePercent());
  const travelX = Math.max(0, frameRect.width - rect.width);
  const travelY = Math.max(0, frameRect.height - rect.height);
  const nextLeft = clamp(mergePreviewDrag.startLeftPx + (event.clientX - mergePreviewDrag.startClientX), 0, travelX);
  const nextTop = clamp(mergePreviewDrag.startTopPx + (event.clientY - mergePreviewDrag.startClientY), 0, travelY);
  const nextX = travelX === 0 ? 0 : nextLeft / travelX;
  const nextY = travelY === 0 ? 0 : nextTop / travelY;
  updateLocalMergeSourcePosition(mergePreviewDrag.sourceId, nextX, nextY);
  scheduleInteractionPreviewRender({ video: true });
}

function endMergePreviewDrag(event) {
  if (!mergePreviewDrag) return;
  if (event.pointerId !== undefined && mergePreviewDrag.pointerId !== undefined && event.pointerId !== mergePreviewDrag.pointerId) return;
  const drag = mergePreviewDrag;
  releasePointer(drag.item, event.pointerId);
  drag.item.classList.remove("dragging");
  const source = mergeSourceById(drag.sourceId);
  mergePreviewDrag = null;
  flushInteractionPreviewRender();
  if (source) {
    activity("merge.preview.drag.commit", {
      source_id: drag.sourceId,
      pip_x: normalizedCoordinateValue(source.pip_x),
      pip_y: normalizedCoordinateValue(source.pip_y),
    });
    scheduleMergeSourceCommit(mergeSourcePositionPayload(drag.sourceId, source));
  }
  flushDeferredRender();
}

function overlayRenderPositionMs(video, mediaTimeS = null) {
  if (Number.isFinite(mediaTimeS)) return Math.max(0, Math.floor(mediaTimeS * 1000));
  return Math.max(0, Math.floor((video?.currentTime || 0) * 1000));
}

function renderLiveOverlay(positionMsOverride = null) {
  if (!state?.project) return;
  const overlay = $("live-overlay");
  const customOverlay = $("custom-overlay");
  const scoreLayer = $("score-layer");
  const position = state.project.overlay.position;
  overlay.className = `live-overlay overlay-${position}`;
  customOverlay.className = `live-overlay overlay-${position}`;
  overlay.innerHTML = "";
  scoreLayer.innerHTML = "";
  if (position === "none" || !state.media.primary_available) {
    customOverlay.innerHTML = "";
    customOverlay.classList.remove("has-badge");
    customOverlayRenderKey = "";
    return;
  }
  const stage = $("video-stage");
  const video = $("primary-video");
  const frameGeometry = previewFrameGeometry(video, stage);
  const frameRect = roundedRect(frameGeometry?.frameRect || stage.getBoundingClientRect());
  const overlayScale = frameGeometry?.scale || overlayDisplayScale(video, frameRect);
  positionOverlayContainer(overlay, state.project.overlay.shot_quadrant, frameRect, {
    x: state.project.overlay.custom_x,
    y: state.project.overlay.custom_y,
  }, overlayScale);
  customOverlay.style.left = `${frameRect.left}px`;
  customOverlay.style.top = `${frameRect.top}px`;
  customOverlay.style.width = `${frameRect.width}px`;
  customOverlay.style.height = `${frameRect.height}px`;
  customOverlay.style.transform = "";
  customOverlay.style.justifyContent = "flex-start";
  customOverlay.style.alignItems = "flex-start";
  customOverlay.style.padding = "0";
  customOverlay.style.gap = "0";

  const positionMs = Number.isFinite(positionMsOverride)
    ? Math.max(0, Math.floor(positionMsOverride))
    : overlayRenderPositionMs(video);
  const beep = state.project.analysis.beep_time_ms_primary;
  let elapsed = beep === null || beep === undefined ? positionMs : Math.max(0, positionMs - beep);
  const shots = orderedShotsByTime();
  const firstShotTime = shots.length > 0 ? shotDisplayTimeMs(shots[0].time_ms) : null;
  const finalShotIndex = shots.length - 1;
  const finalShotTime = finalShotIndex >= 0 ? shotDisplayTimeMs(shots[finalShotIndex].time_ms) : null;
  const finalShotReached = finalShotTime !== null && finalShotTime !== undefined && positionMs >= finalShotTime;
  if (beep !== null && beep !== undefined && shots.length > 0) {
    const lastShotMs = shots[shots.length - 1].time_ms;
    elapsed = Math.min(elapsed, Math.max(0, lastShotMs - beep));
  }
  const size = state.project.overlay.badge_size;
  const shotTextBias = textBiasForDirection(state.project.overlay.shot_direction || "right");
  const autoBubbleSize = state.project.overlay.bubble_width > 0 && state.project.overlay.bubble_height > 0
    ? null
    : overlayAutoBubbleSize();
  const currentIndex = currentShotIndex(positionMs);
  const splitRowsByShotId = new Map((state.split_rows || []).filter((row) => row.shot_id).map((row) => [row.shot_id, row]));
  const appendOverlayBadge = (badge, kind = "", xValue = null, yValue = null) => {
    if (!overlayBadgeLockedToStack(kind) && placeOverlayBadge(scoreLayer, badge, frameRect, xValue, yValue)) {
      return;
    }
    if (kind === "" && placeOverlayBadge(scoreLayer, badge, frameRect, xValue, yValue)) {
      return;
    }
    if (kind === "shots") {
      overlay.appendChild(badge);
      return;
    }
    overlay.appendChild(badge);
  };
  if (state.project.overlay.show_timer) {
    const timerBadge = badgeElement(`Timer ${seconds(elapsed)}`, state.project.overlay.timer_badge, size, null, null, null, "center", overlayScale, autoBubbleSize);
    timerBadge.dataset.overlayDrag = "timer";
    appendOverlayBadge(timerBadge, "timer", state.project.overlay.timer_x, state.project.overlay.timer_y);
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
    const drawBadge = badgeElement(`Draw ${seconds(state.metrics.draw_ms)}`, state.project.overlay.shot_badge, size, null, null, null, "center", overlayScale, autoBubbleSize);
    drawBadge.dataset.overlayDrag = "draw";
    appendOverlayBadge(drawBadge, "draw", state.project.overlay.draw_x, state.project.overlay.draw_y);
  }

  if (state.project.overlay.show_shots && currentIndex >= 0) {
    const maxVisible = Math.max(1, Number(state.project.overlay.max_visible_shots || 4));
    const start = Math.max(0, currentIndex - maxVisible + 1);
    for (let index = start; index <= currentIndex; index += 1) {
      const shot = shots[index];
      if (!shot) continue;
      const splitRow = splitRowsByShotId.get(shot.id) || null;
      const splitMs = resolvedSplitMsForShot(shot.id, index + 1, shot.time_ms);
      const style = index === currentIndex
        ? state.project.overlay.current_shot_badge
        : state.project.overlay.shot_badge;
      const shotBadge = badgeElement(
        scoreBadgeContent(shot, index + 1, splitSeconds(splitMs), splitRowIntervalLabel(splitRow)),
        style,
        size,
        null,
        null,
        null,
        shotTextBias,
        overlayScale,
        autoBubbleSize,
      );
      shotBadge.dataset.overlayDrag = "shots";
      appendOverlayBadge(shotBadge, "shots");
    }
  }

  const summary = state.scoring_summary || {};
  let finalScoreBadge = null;
  if (finalShotReached && state.project.scoring.enabled && state.project.overlay.show_score && summary.display_value && summary.display_value !== "--") {
    const scoreBadge = badgeElement(`${summary.display_label} ${summary.display_value}`, state.project.overlay.hit_factor_badge, size, null, null, null, "center", overlayScale, autoBubbleSize);
    scoreBadge.dataset.overlayDrag = "score";
    appendOverlayBadge(scoreBadge, "score", state.project.overlay.score_x, state.project.overlay.score_y);
    finalScoreBadge = scoreBadge;
  }

  if (usesCustomQuadrant(state.project.overlay.shot_quadrant) && overlay.childElementCount > 0) {
    pinCustomOverlayAnchor(overlay, frameRect, {
      x: state.project.overlay.custom_x,
      y: state.project.overlay.custom_y,
    });
  }

  const textBoxEntries = visibleOverlayTextBoxEntries(finalShotReached);
  if (reviewBoxesLockedToOverlayStack()) {
    textBoxEntries.forEach(({ box, textValue }) => {
      overlay.appendChild(
        badgeElement(
          textValue,
          overlayTextBoxStyle(box),
          size,
          null,
          box.width,
          box.height,
          "center",
          overlayScale,
        )
      );
    });
    if (customOverlay.childElementCount > 0 || customOverlayRenderKey) {
      customOverlay.innerHTML = "";
      customOverlay.classList.remove("has-badge");
      customOverlayRenderKey = "";
    }
    return;
  }

  const nextCustomOverlayKey = textBoxEntries.length === 0
    ? ""
    : customOverlayKey(textBoxEntries, frameRect, overlayScale, finalScoreBadge);
  if (!nextCustomOverlayKey) {
    if (customOverlay.childElementCount > 0 || customOverlayRenderKey) {
      customOverlay.innerHTML = "";
      customOverlay.classList.remove("has-badge");
      customOverlayRenderKey = "";
    }
    return;
  }
  // Keep the review text-box layer stable while video frames advance; it only needs a rebuild when its own layout changes.
  if (nextCustomOverlayKey !== customOverlayRenderKey) {
    renderCustomOverlayBoxes(customOverlay, textBoxEntries, frameRect, overlayScale, size, finalScoreBadge);
    customOverlayRenderKey = nextCustomOverlayKey;
  }
}

function requestOverlayFrame(video, tick) {
  if (!(video instanceof HTMLVideoElement)) return;
  if (typeof video.requestVideoFrameCallback === "function") {
    overlayFrameMode = "video-frame";
    overlayFrame = video.requestVideoFrameCallback(tick);
    return;
  }
  overlayFrameMode = "animation-frame";
  overlayFrame = requestAnimationFrame((now) => tick(now, null));
}

function cancelOverlayFrame(video) {
  if (overlayFrame === null) return;
  if (overlayFrameMode === "video-frame" && typeof video?.cancelVideoFrameCallback === "function") {
    video.cancelVideoFrameCallback(overlayFrame);
  } else {
    cancelAnimationFrame(overlayFrame);
  }
  overlayFrame = null;
  overlayFrameMode = null;
}

function startOverlayLoop() {
  const video = $("primary-video");
  if (!(video instanceof HTMLVideoElement) || overlayFrame !== null) return;
  activity("video.play", { current_time_s: video.currentTime });
  scheduleSecondaryPreviewSync();
  const tick = (_now, metadata = null) => {
    overlayFrame = null;
    overlayFrameMode = null;
    const mediaTimeS = Number.isFinite(metadata?.mediaTime) ? metadata.mediaTime : null;
    activity("frame.overlay", {
      current_time_s: mediaTimeS ?? video.currentTime,
      frame_source: mediaTimeS === null ? "animation-frame" : "video-frame",
      merge_sources: (state?.project?.merge_sources || []).length,
      selected_shot_id: selectedShotId || "",
    });
    scheduleSecondaryPreviewSync();
    renderLiveOverlay(mediaTimeS === null ? null : mediaTimeS * 1000);
    if (video.paused || video.ended) return;
    requestOverlayFrame(video, tick);
  };
  requestOverlayFrame(video, tick);
}

function stopOverlayLoop() {
  const video = $("primary-video");
  if (!(video instanceof HTMLVideoElement) || overlayFrame === null) return;
  activity("video.pause", { current_time_s: video.currentTime });
  cancelOverlayFrame(video);
  scheduleSecondaryPreviewSync();
  renderLiveOverlay();
}

function render() {
  if (!state?.project) return;
  syncSelectedShotId();
  withPreservedScrollState(scrollRenderTargets(), () => {
    applyLayoutState();
    renderHeader();
    renderStats();
    renderVideo();
    renderWaveform();
    renderTimingTables();
    renderControls();
    renderSelection();
    renderLiveOverlay();
    setActiveTool(activeTool, { persistUiState: false });
  });
  flushPendingInspectorScrollRestore();
}

function renderViewportLayout() {
  if (!state?.project) return;
  withPreservedScrollState(scrollRenderTargets(), () => {
    applyLayoutState();
    renderVideo();
    renderWaveform();
    renderLiveOverlay();
  });
  flushPendingInspectorScrollRestore();
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

function setWaveformMode(mode, { persistUiState = true } = {}) {
  if (!VALID_WAVEFORM_MODES.has(mode)) mode = "select";
  waveformMode = mode;
  document.querySelectorAll("[data-waveform-mode]").forEach((button) => {
    button.classList.toggle("active", button.dataset.waveformMode === mode);
  });
  const help = $("waveform-help");
  if (mode === "add") {
    help.textContent = "Add Shot mode: click the waveform to add a manual shot.";
  } else {
    help.textContent = "Select mode: click a shot marker, drag a shot to move, drag empty space to pan, arrows nudge.";
  }
  activity("waveform.mode", { mode });
  syncLocalProjectUiState();
  if (persistUiState) scheduleProjectUiStateApply();
}

function setWaveformExpanded(expanded, { persistUiState = true } = {}) {
  const root = $("cockpit-root");
  root.classList.toggle("waveform-expanded", expanded);
  if (expanded) root.classList.remove("timing-expanded");
  $("expand-waveform").textContent = root.classList.contains("waveform-expanded") ? "Collapse" : "Expand";
  activity("waveform.expand", { expanded });
  syncLocalProjectUiState();
  if (persistUiState) scheduleProjectUiStateApply();
  if (expanded) {
    renderWaveform();
    window.requestAnimationFrame(() => renderWaveform());
    return;
  }
  scheduleReviewStageRestore();
}

function setWaveformZoom(delta) {
  const oldWindow = waveformWindow();
  const center = oldWindow.start + (oldWindow.duration / 2);
  waveformZoomX = clamp(waveformZoomX * delta, 1, 200);
  const newDuration = durationMs() / waveformZoomX;
  waveformOffsetMs = clamp(center - (newDuration / 2), 0, Math.max(0, durationMs() - newDuration));
  persistWaveformViewport();
  activity("waveform.zoom_x", { zoom: waveformZoomX, offset_ms: waveformOffsetMs });
  renderWaveform();
}

function panWaveform(deltaMs) {
  const visible = waveformWindow();
  const maxOffset = Math.max(0, durationMs() - visible.duration);
  if (maxOffset <= 0) return;
  setWaveformOffset(waveformOffsetMs + deltaMs);
  activity("waveform.pan", { offset_ms: waveformOffsetMs, delta_ms: deltaMs });
  renderWaveform();
}

function handleWaveformWheel(event) {
  if (waveformZoomX <= 1) return;
  const horizontalDelta = Math.abs(event.deltaX) > 0 ? event.deltaX : (event.shiftKey ? event.deltaY : 0);
  if (!horizontalDelta) return;
  const canvas = $("waveform");
  const width = Math.max(1, canvas.getBoundingClientRect().width || canvas.clientWidth || 1);
  const visible = waveformWindow();
  event.preventDefault();
  panWaveform((horizontalDelta / width) * visible.duration);
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
  syncLocalProjectUiState();
  scheduleProjectUiStateApply();
  renderWaveform();
}

function resetWaveformView() {
  waveformZoomX = 1;
  waveformShotAmplitudeById = {};
  waveformOffsetMs = 0;
  window.localStorage.removeItem("splitshot.waveform.zoomX");
  window.localStorage.removeItem("splitshot.waveform.offsetMs");
  activity("waveform.zoom_reset", {});
  syncLocalProjectUiState();
  scheduleProjectUiStateApply();
  renderWaveform();
}

function setTimingExpanded(expanded, { persistUiState = true } = {}) {
  const root = $("cockpit-root");
  root.classList.toggle("timing-expanded", expanded);
  if (expanded) root.classList.remove("waveform-expanded");
  $("expand-waveform").textContent = root.classList.contains("waveform-expanded") ? "Collapse" : "Expand";
  activity("timing.expand", { expanded });
  syncLocalProjectUiState();
  if (persistUiState) scheduleProjectUiStateApply();
  if (expanded) {
    renderTimingTables();
    return;
  }
  scheduleReviewStageRestore();
}

function moveSelectedShot(deltaMs) {
  const shot = selectedShot();
  if (!shot) return;
  activity("shot.keyboard_nudge", { shot_id: shot.id, delta_ms: deltaMs });
  callApi("/api/shots/move", { shot_id: shot.id, time_ms: shot.time_ms + deltaMs });
}

function deleteSelectedShot() {
  deleteShotById(selectedShotId, "selected");
}

function handleWaveformPointerDown(event) {
  if (event.button !== 0) return;
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
    draggingShotPointerId = event.pointerId;
    pendingDragTimeMs = shot.time_ms;
    capturePointer($("waveform"), event.pointerId);
    activity("waveform.drag_start", { shot_id: shot.id, time_ms: shot.time_ms });
    callApi("/api/shots/select", { shot_id: shot.id });
    renderWaveform();
    return;
  }
  if (($("cockpit-root")?.classList.contains("waveform-expanded") ?? false) && waveformZoomX > 1) {
    startWaveformPanDrag(event);
    return;
  }
  const video = $("primary-video");
  if (state?.media?.primary_available) {
    video.currentTime = time_ms / 1000;
    activity("waveform.seek", { time_ms });
  }
}

function handleWaveformPointerMove(event) {
  if (waveformNavigatorDrag) {
    moveWaveformNavigatorDrag(event);
    return;
  }
  if (waveformPanDrag) {
    updateWaveformPanDrag(event);
    return;
  }
  if (!draggingShotId) return;
  if (event.pointerId !== undefined && draggingShotPointerId !== undefined && event.pointerId !== draggingShotPointerId) return;
  pendingDragTimeMs = waveformTime(event);
  scheduleInteractionPreviewRender({ waveform: true });
}

function handleWaveformPointerUp(event) {
  if (waveformNavigatorDrag) {
    endWaveformNavigatorDrag(event);
    return;
  }
  if (waveformPanDrag) {
    const moved = finishWaveformPanDrag(event);
    if (!moved) {
      const time_ms = waveformTime(event);
      const video = $("primary-video");
      if (state?.media?.primary_available) {
        video.currentTime = time_ms / 1000;
        activity("waveform.seek", { time_ms });
      }
    }
    return;
  }
  if (!draggingShotId) return;
  if (event.pointerId !== undefined && draggingShotPointerId !== undefined && event.pointerId !== draggingShotPointerId) return;
  const shotId = draggingShotId;
  const timeMs = pendingDragTimeMs ?? waveformTime(event);
  flushInteractionPreviewRender();
  draggingShotId = null;
  draggingShotPointerId = null;
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
    card.querySelectorAll("[data-field]").forEach((input) => {
      const value = input.type === "range" ? Number(input.value) : (isColorInput(input) ? readColorControlValue(input) : input.value);
      styles[badge][input.dataset.field] = value;
    });
  });
  const scoringColors = {};
  document.querySelectorAll(".score-color-input").forEach((input) => {
    scoringColors[input.dataset.letter] = readColorControlValue(input);
  });
  const textBoxes = overlayTextBoxes().map((box, index) => normalizeOverlayTextBox(box, index));
  const primaryTextBox = preferredLegacyTextBox(textBoxes);
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
    timer_lock_to_stack: $("timer-lock-to-stack").checked,
    draw_lock_to_stack: $("draw-lock-to-stack").checked,
    score_lock_to_stack: $("score-lock-to-stack").checked,
    review_boxes_lock_to_stack: $("review-lock-to-stack").checked,
    text_boxes: textBoxes.map((box) => ({
      id: box.id,
      enabled: box.enabled,
      source: box.source,
      text: box.text,
      quadrant: box.quadrant,
      x: box.x,
      y: box.y,
      background_color: box.background_color,
      text_color: box.text_color,
      opacity: box.opacity,
      width: box.width,
      height: box.height,
    })),
    custom_box_enabled: Boolean(primaryTextBox?.enabled),
    custom_box_mode: primaryTextBox?.source || "manual",
    custom_box_text: primaryTextBox?.text || "",
    custom_box_quadrant: primaryTextBox?.quadrant || "top_right",
    custom_box_x: primaryTextBox?.x ?? "",
    custom_box_y: primaryTextBox?.y ?? "",
    custom_box_background_color: primaryTextBox?.background_color || "#000000",
    custom_box_text_color: primaryTextBox?.text_color || "#ffffff",
    custom_box_opacity: Number(primaryTextBox?.opacity ?? 0.9),
    custom_box_width: Number(primaryTextBox?.width || 0),
    custom_box_height: Number(primaryTextBox?.height || 0),
  };
}

function readProjectDetailsPayload() {
  return {
    name: $("project-name")?.value ?? projectDetailValue("name"),
    description: $("project-description")?.value ?? projectDetailValue("description"),
  };
}

function readPractiScoreContextPayload() {
  return {
    match_type: $("match-type").value,
    stage_number: $("match-stage-number").value ? Number($("match-stage-number").value) : "",
    competitor_name: $("match-competitor-name").value.trim(),
    competitor_place: normalizedPractiScorePlaceValue($("match-competitor-place").value) ?? "",
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
  const outputPath = $("export-path")?.value.trim() || exportPathDraft.trim() || state?.project?.export?.output_path || "";
  return {
    output_path: outputPath,
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
  clearMergeSourceCommitTimers();
  autoApplyThreshold.cancel?.();
  autoApplyProjectDetails.cancel?.();
  autoApplyPractiScoreContext.cancel?.();
  autoApplyProjectUiState.cancel?.();
  autoApplyOverlay.cancel?.();
  autoApplyMerge.cancel?.();
  autoApplyScoring.cancel?.();
  autoApplyExportLayout.cancel?.();
  autoApplyExportSettings.cancel?.();
}

async function flushPendingProjectDrafts() {
  if (!state?.project) return;
  cancelPendingExportDrafts();
  await callApi("/api/analysis/threshold", { threshold: Number($("threshold").value) });
  await callApi("/api/project/details", readProjectDetailsPayload());
  await callApi("/api/project/practiscore", readPractiScoreContextPayload());
  await callApi("/api/project/ui-state", readProjectUiStatePayload());
  await callApi("/api/overlay", readOverlayPayload());
  await callApi("/api/merge", readMergePayload());
  await flushPendingMergeSourceCommits();
  await callApi("/api/export/settings", readExportLayoutPayload());
  await callApi("/api/export/settings", readExportSettingsPayload());
  await callApi("/api/scoring/profile", { ruleset: $("scoring-preset").value });
  await callApi("/api/scoring", readScoringPayload());
}

function sendKeepaliveJson(path, payload) {
  const body = JSON.stringify(payload);
  try {
    if (navigator.sendBeacon) {
      const sent = navigator.sendBeacon(path, new Blob([body], { type: "application/json" }));
      if (sent) return true;
    }
  } catch {
    // Ignore keepalive failures during shutdown.
  }
  try {
    fetch(path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body,
      keepalive: true,
    });
    return true;
  } catch {
    return false;
  }
}

function flushPendingProjectDraftsKeepalive() {
  if (!state?.project) return;
  cancelPendingExportDrafts();
  sendKeepaliveJson("/api/analysis/threshold", { threshold: Number($("threshold").value) });
  sendKeepaliveJson("/api/project/details", readProjectDetailsPayload());
  sendKeepaliveJson("/api/project/practiscore", readPractiScoreContextPayload());
  sendKeepaliveJson("/api/project/ui-state", readProjectUiStatePayload());
  sendKeepaliveJson("/api/overlay", readOverlayPayload());
  sendKeepaliveJson("/api/merge", readMergePayload());
  flushPendingMergeSourceCommits({ keepalive: true });
  sendKeepaliveJson("/api/export/settings", readExportLayoutPayload());
  sendKeepaliveJson("/api/export/settings", readExportSettingsPayload());
  sendKeepaliveJson("/api/scoring/profile", { ruleset: $("scoring-preset").value });
  sendKeepaliveJson("/api/scoring", readScoringPayload());
}

async function importTypedPath(targetId, apiPath, label) {
  const path = $(targetId).value.trim();
  if (!path) {
    setStatus(`${label} video path is required.`);
    return null;
  }
  if (apiPath === "/api/import/primary") {
    await flushPendingProjectDrafts();
  }
  return callApi(apiPath, { path });
}

function normalizeProjectFolderInput(path) {
  return String(path || "").trim();
}

function comparableProjectFolderPath(path) {
  let normalized = normalizeProjectFolderInput(path).replace(/[\\/]+$/, "");
  normalized = normalized.replace(/[\\/]project\.json$/i, "");
  return normalized;
}

function sameProjectFolderPath(left, right) {
  return comparableProjectFolderPath(left) === comparableProjectFolderPath(right);
}

async function probeProjectFolder(path) {
  const targetPath = normalizeProjectFolderInput(path);
  const requestId = ++projectFolderProbeRequestId;
  const response = await fetch("/api/project/probe", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ path: targetPath }),
  });
  const data = await response.json();
  if (!response.ok || data.error) throw new Error(data.error || response.statusText);
  if (requestId !== projectFolderProbeRequestId) {
    throw new Error("Project folder selection changed. Try again.");
  }
  if (!sameProjectFolderPath(data.path || targetPath, targetPath)) {
    throw new Error("Project folder probe returned a different path.");
  }
  return {
    path: targetPath,
    normalized_path: comparableProjectFolderPath(data.normalized_path || data.path || targetPath),
    has_project_file: Boolean(data.has_project_file),
    request_id: requestId,
  };
}

async function browseProjectPath() {
  return pickPath("project_folder", "project-path", async (selectedPath) => {
    await useProjectFolder(selectedPath);
  });
}

async function useProjectFolder(path = $("project-path").value.trim()) {
  const targetPath = normalizeProjectFolderInput(path);
  if (!targetPath) {
    return pickPath("project_folder", "project-path", async (selectedPath) => {
      await useProjectFolder(selectedPath);
    });
  }

  await flushPendingProjectDrafts();
  const currentPath = normalizeProjectFolderInput(state?.project?.path || "");
  if (currentPath && sameProjectFolderPath(currentPath, targetPath)) {
    const result = await callApi("/api/project/save", { path: targetPath });
    if (result) setActiveTool("project");
    return result;
  }

  try {
    const probeResult = await probeProjectFolder(targetPath);
    const projectPath = probeResult.normalized_path || targetPath;
    if (!probeResult.has_project_file) {
      const shouldCreate = window.confirm(`No project.json found in:\n${targetPath}\n\nCreate this folder for the current project?`);
      if (!shouldCreate) {
        setStatus("Project folder selection cancelled.");
        return null;
      }
      if (probeResult.request_id !== projectFolderProbeRequestId) {
        setStatus("Project folder selection changed. Try again.");
        return null;
      }
      const result = await callApi("/api/project/save", { path: projectPath });
      if (result) setActiveTool("project");
      return result;
    }

    if (probeResult.request_id !== projectFolderProbeRequestId) {
      setStatus("Project folder selection changed. Try again.");
      return null;
    }
    const result = await callApi("/api/project/open", { path: projectPath });
    if (result) setActiveTool("project");
    return result;
  } catch (error) {
    setStatus(error.message);
    activity("api.error", { path: "/api/project/probe", error: error.message });
    return null;
  }
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

const autoApplyProjectUiState = debounce((payload) => {
  activity("auto_apply.project_ui_state", {});
  callApi("/api/project/ui-state", payload);
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
  pendingSelectionFallback = shotSelectionContext(selectedShotId, state, "time");
  autoApplyThreshold({ threshold: Number($("threshold").value) });
}

async function applyThresholdNow() {
  pendingSelectionFallback = shotSelectionContext(selectedShotId, state, "time");
  autoApplyThreshold.cancel?.();
  await callApi("/api/analysis/threshold", { threshold: Number($("threshold").value) });
}

function scheduleProjectDetailsApply() {
  applyProjectDetailsDraft(readProjectDetailsPayload());
  renderHeader();
  autoApplyProjectDetails(readProjectDetailsPayload());
}

function schedulePractiScoreContextApply() {
  autoApplyPractiScoreContext(readPractiScoreContextPayload());
}

function scheduleProjectUiStateApply() {
  const payload = readProjectUiStatePayload();
  if (hasActivePointerInteraction()) {
    pendingProjectUiStatePayload = payload;
    return;
  }
  pendingProjectUiStatePayload = null;
  autoApplyProjectUiState(payload);
}

function flushQueuedProjectUiStateApply() {
  if (!pendingProjectUiStatePayload) return;
  const payload = pendingProjectUiStatePayload;
  pendingProjectUiStatePayload = null;
  autoApplyProjectUiState(payload);
}

function scheduleOverlayApply() {
  queueInspectorScrollRestore();
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
  renderViewportLayout();
  syncTimingTableColumns();
}, 120);

function wireEvents() {
  document.querySelectorAll("[data-tool]").forEach((item) => {
    item.addEventListener("click", () => {
      activity("ui.tool.click", { tool: item.dataset.tool });
      setActiveTool(item.dataset.tool);
    });
  });
  $("new-project").addEventListener("click", async () => {
    await flushPendingProjectDrafts();
    await callApi("/api/project/new", {});
  });
  $("primary-file-path").addEventListener("keydown", async (event) => {
    if (event.key !== "Enter") return;
    event.preventDefault();
    const result = await importTypedPath("primary-file-path", "/api/import/primary", "Primary");
    if (result) setActiveTool("project");
  });
  $("browse-project-path").addEventListener("click", browseProjectPath);
  $("browse-export-path").addEventListener("click", () => pickPath("export", "export-path", async () => {
    scheduleExportSettingsApply();
  }));
  $("export-path").addEventListener("input", () => {
    exportPathDraft = $("export-path").value;
    scheduleExportSettingsApply();
  });
  $("browse-primary-path").addEventListener("click", () => pickPath("primary", "primary-file-path", async (path) => {
    await flushPendingProjectDrafts();
    const result = await callApi("/api/import/primary", { path });
    if (result) setActiveTool("project");
  }));
  document.querySelectorAll("[data-open-primary]").forEach((item) => {
    item.addEventListener("click", () => pickPath("primary", "primary-file-path", async (path) => {
      await flushPendingProjectDrafts();
      const result = await callApi("/api/import/primary", { path });
      if (result) setActiveTool("project");
    }));
  });
  document.querySelectorAll("[data-open-merge-media]").forEach((item) => {
    item.addEventListener("click", () => openHiddenFileInput("merge-media-input"));
  });
  $("primary-file-input").addEventListener("change", async (event) => {
    await flushPendingProjectDrafts();
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
    setStatus("Select a PractiScore results file (.csv or .txt).");
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
    event.target.value = "";
  });
  $("delete-project").addEventListener("click", async () => {
    const projectPath = (state?.project?.path || "").trim();
    if (!projectPath) return;
    const shouldDelete = window.confirm(`Delete this project folder from disk?\n\n${projectPath}`);
    if (!shouldDelete) return;
    await flushPendingProjectDrafts();
    await callApi("/api/project/delete", {});
  });
  ["project-name", "project-description"].forEach((id) => {
    $(id).addEventListener("input", scheduleProjectDetailsApply);
  });
  ["match-type", "match-stage-number"].forEach((id) => {
    $(id).addEventListener("change", schedulePractiScoreContextApply);
  });
  $("match-competitor-name").addEventListener("change", () => {
    syncPractiScoreSelectionFields("name");
    schedulePractiScoreContextApply();
  });
  $("match-competitor-place").addEventListener("change", () => {
    syncPractiScoreSelectionFields("place");
    schedulePractiScoreContextApply();
  });
  document.addEventListener("fullscreenchange", handleStageFullscreenChange);
  document.addEventListener("webkitfullscreenchange", handleStageFullscreenChange);
  ["loadedmetadata", "loadeddata"].forEach((eventName) => {
    $("primary-video").addEventListener(eventName, () => {
      logPrimaryVideoState(eventName);
      scheduleSecondaryPreviewSync();
      renderLiveOverlay();
    });
    $("secondary-video").addEventListener(eventName, () => {
      scheduleSecondaryPreviewSync();
      renderLiveOverlay();
    });
  });
  $("primary-video").addEventListener("volumechange", () => {
    logPrimaryVideoState("volumechange");
  });
  $("primary-video").addEventListener("canplay", () => {
    logPrimaryVideoState("canplay");
  });
  $("primary-video").addEventListener("error", () => {
    logPrimaryVideoState("error");
  });
  $("primary-video").addEventListener("play", () => {
    logPrimaryVideoState("play");
  });
  $("primary-video").addEventListener("pause", () => {
    logPrimaryVideoState("pause");
  });
  $("primary-video").addEventListener("play", startOverlayLoop);
  $("primary-video").addEventListener("pause", stopOverlayLoop);
  $("primary-video").addEventListener("seeked", () => {
    activity("video.seeked", { current_time_s: $("primary-video").currentTime });
    scheduleSecondaryPreviewSync();
    renderLiveOverlay();
  });
  $("primary-video").addEventListener("timeupdate", () => {
    if (overlayFrame !== null) return;
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
  $("waveform-window-track").addEventListener("pointerdown", handleWaveformNavigatorPointerDown);
  $("waveform").addEventListener("wheel", handleWaveformWheel, { passive: false });
  document.addEventListener("pointermove", handleWaveformPointerMove);
  document.addEventListener("pointerup", handleWaveformPointerUp);
  document.addEventListener("pointercancel", handleWaveformPointerUp);
  document.addEventListener("lostpointercapture", handleWaveformPointerUp);
  document.addEventListener("keydown", handleKeyboardEdit);
  document.addEventListener("visibilitychange", handleWindowVisibilityRestore);
  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState && document.visibilityState !== "visible") {
      cancelOverlayDragInteractions("document.hidden");
    }
  });
  window.addEventListener("resize", handleViewportLayoutChange);
  window.addEventListener("focus", handleWindowVisibilityRestore);
  window.addEventListener("pageshow", handleWindowVisibilityRestore);
  window.addEventListener("blur", () => cancelOverlayDragInteractions("window.blur"));
  window.visualViewport?.addEventListener("resize", handleViewportLayoutChange);
  document.querySelector(".inspector")?.addEventListener("scroll", rememberInspectorScrollPosition, { passive: true });
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
  $("threshold").addEventListener("change", applyThresholdNow);
  $("threshold").addEventListener("keydown", (event) => {
    if (event.key !== "Enter") return;
    event.preventDefault();
    applyThresholdNow();
  });
  $("apply-threshold").addEventListener("click", applyThresholdNow);
  ["merge-enabled", "merge-layout"].forEach((id) => {
    $(id).addEventListener("change", () => {
      syncMergePreviewStateFromControls();
      scheduleInteractionPreviewRender({ video: true });
      scheduleMergeApply();
    });
  });
  $("pip-size").addEventListener("input", () => {
    $("pip-size-label").textContent = `${$("pip-size").value}%`;
    syncMergePreviewStateFromControls();
    scheduleInteractionPreviewRender({ video: true });
    scheduleMergeApply();
  });
  ["pip-x", "pip-y"].forEach((id) => {
    $(id).addEventListener("input", () => {
      syncMergePreviewStateFromControls();
      scheduleInteractionPreviewRender({ video: true });
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
  $("custom-overlay").addEventListener("pointerdown", beginTextBoxDrag);
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
    "timer-lock-to-stack",
    "timer-x",
    "timer-y",
    "draw-lock-to-stack",
    "draw-x",
    "draw-y",
    "score-lock-to-stack",
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
    "review-lock-to-stack",
  ].forEach((id) => {
    const eventName = $(id).tagName === "SELECT" || $(id).type === "checkbox" ? "change" : "input";
    $(id).addEventListener(eventName, () => {
      if (id === "shot-quadrant") {
        syncOverlayCoordinateControlState();
        ensureShotQuadrantDefaults();
      }
      if (id.endsWith("-lock-to-stack")) {
        syncOverlayBubbleLockControlState();
        if (id === "review-lock-to-stack") {
          syncOverlayPreviewStateFromControls();
          renderTextBoxEditors();
          scheduleInteractionPreviewRender({ overlay: true });
          scheduleOverlayApply();
          return;
        }
      }
      commitOverlayControlChanges();
    });
  });
  [
    ["review-add-text-box", "manual"],
    ["review-add-imported-box", "imported_summary"],
  ].forEach(([id, source]) => {
    $(id)?.addEventListener("click", () => addOverlayTextBox(source));
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
  document.addEventListener("pointermove", moveTimingColumnResize);
  document.addEventListener("pointerup", endTimingColumnResize);
  document.addEventListener("pointercancel", endTimingColumnResize);
  document.addEventListener("lostpointercapture", endTimingColumnResize);
  document.addEventListener("pointermove", moveOverlayBadgeDrag);
  document.addEventListener("pointerup", endOverlayBadgeDrag);
  document.addEventListener("pointercancel", endOverlayBadgeDrag);
  document.addEventListener("lostpointercapture", endOverlayBadgeDrag);
  document.addEventListener("pointermove", moveMergePreviewDrag);
  document.addEventListener("pointerup", endMergePreviewDrag);
  document.addEventListener("pointercancel", endMergePreviewDrag);
  document.addEventListener("lostpointercapture", endMergePreviewDrag);
  document.addEventListener("pointermove", moveTextBoxDrag);
  document.addEventListener("pointerup", endTextBoxDrag);
  document.addEventListener("pointercancel", endTextBoxDrag);
  document.addEventListener("lostpointercapture", endTextBoxDrag);
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
    await flushPendingMergeSourceCommits();
    await callApi("/api/export", buildExportPayload(path));
  });
  $("show-export-log")?.addEventListener("click", openExportLogModal);
  $("export-export-log")?.addEventListener("click", downloadExportLog);
  $("close-export-log")?.addEventListener("click", closeExportLogModal);
  $("close-color-picker")?.addEventListener("click", () => closeColorPicker({ commit: true }));
  document.querySelectorAll("[data-close-color-picker]").forEach((element) => {
    element.addEventListener("click", () => closeColorPicker({ commit: true }));
  });
  ["color-picker-hue", "color-picker-saturation", "color-picker-lightness"].forEach((id) => {
    $(id)?.addEventListener("input", () => updateColorPickerFromSliders({ commit: false }));
    $(id)?.addEventListener("change", () => updateColorPickerFromSliders({ commit: true }));
  });
  $("color-picker-hex")?.addEventListener("input", () => updateColorPickerFromHexInput({ commit: false }));
  $("color-picker-hex")?.addEventListener("change", () => updateColorPickerFromHexInput({ commit: true }));
  $("color-picker-hex")?.addEventListener("blur", () => updateColorPickerFromHexInput({ commit: true }));
  document.querySelectorAll("[data-close-export-log]").forEach((element) => {
    element.addEventListener("click", closeExportLogModal);
  });
  $("metrics-export-csv")?.addEventListener("click", () => exportMetrics("csv"));
  $("metrics-export-text")?.addEventListener("click", () => exportMetrics("text"));
  window.addEventListener("beforeunload", () => {
    stopActivityPolling();
    flushPendingProjectDraftsKeepalive();
    flushActivityQueue();
  });
  window.addEventListener("pagehide", () => {
    flushPendingProjectDraftsKeepalive();
  });
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && !$("color-picker-modal")?.hidden) {
      closeColorPicker({ commit: true });
      return;
    }
    if (event.key === "Escape" && !$("export-log-modal")?.hidden) {
      closeExportLogModal();
    }
  });
}

applyLayoutState();
setActiveTool(activeTool, { persistUiState: false });
wireGlobalActivityLogging();
wireEvents();
startActivityPolling();
refresh();
