import { createActivityRuntime } from "./lib/activity.js";
import { createApiRuntime } from "./lib/api.js";
import { createOverlayCanvasComponent } from "./components/overlay-canvas.js";
import { createExportPane } from "./panes/export-pane.js";
import { createMergePane } from "./panes/merge-pane.js";
import { createMetricsPane } from "./panes/metrics-pane.js";
import { createMarkersPane } from "./panes/markers-pane.js";
import { createOverlayPane } from "./panes/overlay-pane.js";
import { createProjectPane } from "./panes/project-pane.js";
import { createReviewPane } from "./panes/review-pane.js";
import { createScoringPane } from "./panes/scoring-pane.js";
import { createSettingsPane } from "./panes/settings-pane.js";
import { createShotMLPane } from "./panes/shotml-pane.js";
import { createTimingPane } from "./panes/timing-pane.js";
import { createStatusBarComponent } from "./components/status-bar.js";
import { createVideoPlayerComponent } from "./components/video-player.js";
import { createWaveformComponent } from "./components/waveform.js";
import {
  $ as domById,
  clamp as utilsClamp,
  clampNumber as utilsClampNumber,
  debounce as utilsDebounce,
  fileName as utilsFileName,
  formatNumber as utilsFormatNumber,
  normalizedUiBooleanMap as utilsNormalizedUiBooleanMap,
  normalizedUiFloatMap as utilsNormalizedUiFloatMap,
  normalizedUiStringList as utilsNormalizedUiStringList,
  numericMs as utilsNumericMs,
  precise as utilsPrecise,
  savedNumber as utilsSavedNumber,
  seconds as utilsSeconds,
  splitSeconds as splitSecondsUtil,
} from "./lib/utils.js";
import { createEventBus } from "./lib/event-bus.js";
import { createKeyRuntime } from "./lib/keys.js";
import { createLayoutRuntime } from "./lib/layout.js";
import { createShellRuntime } from "./lib/shell-runtime.js";
import { createMutableBindings, installLegacyGlobalCompat } from "./lib/global-compat.js";
import { createProcessingRuntime } from "./lib/processing.js";
import { createStore } from "./lib/store.js";
import { createWaveformState } from "./lib/waveform-state.js";
import { createMatchView } from "./views/match-view.js";
import { createLibraryView } from "./views/library-view.js";

let $ = domById;
let clamp = utilsClamp;
let clampNumber = utilsClampNumber;
let debounce = utilsDebounce;
let fileName = utilsFileName;
let formatNumber = utilsFormatNumber;
let normalizedUiBooleanMap = utilsNormalizedUiBooleanMap;
let normalizedUiFloatMap = utilsNormalizedUiFloatMap;
let normalizedUiStringList = utilsNormalizedUiStringList;
let numericMs = utilsNumericMs;
let precise = utilsPrecise;
let savedNumber = utilsSavedNumber;
let seconds = utilsSeconds;
let splitSeconds = splitSecondsUtil;

// === AUTOMATE3 VIEW STATE MACHINE ===
const VALID_VIEWS = new Set(["landing", "stage", "match", "library"]);
let currentView = window.localStorage.getItem("splitshot.activeView") || "landing";
let previousView = null;

function setActiveView(viewName) {
  if (!VALID_VIEWS.has(viewName)) {
    console.error("[ViewState] Invalid view:", viewName);
    return;
  }

  previousView = currentView;

  // Pause video when leaving Stage
  if (currentView === "stage" && viewName !== "stage") {
    const primary = document.getElementById("primary-video");
    const secondary = document.getElementById("secondary-video");
    if (primary) primary.pause();
    if (secondary) secondary.pause();
  }

  currentView = viewName;

  // Update view visibility
  document.querySelectorAll(".app-view").forEach((el) => el.classList.remove("active"));
  const viewEl = document.getElementById("view-" + viewName);
  if (viewEl) viewEl.classList.add("active");

  // Update shell attribute
  const shell = document.getElementById("app-shell");
  if (shell) shell.setAttribute("data-active-view", viewName);

  // Show/hide landing page
  const landingPage = document.getElementById("landing-page");
  // Restore view-local state
  if (viewName === "match") {
    const savedScroll = window.localStorage.getItem("splitshot.match.scrollTop");
    if (savedScroll) {
      requestAnimationFrame(() => {
        const grid = document.getElementById("workspace-stage-list");
        if (grid?.parentElement) grid.parentElement.scrollTop = Number(savedScroll);
      });
    }
  }

  if (landingPage) {
    landingPage.hidden = viewName !== "landing";
  }

  // Preserve view-local state before switching
  if (previousView === "match") {
    const grid = document.getElementById("workspace-stage-list");
    if (grid) {
      window.localStorage.setItem("splitshot.match.scrollTop", String(grid.parentElement?.scrollTop || 0));
    }
  }

  // Persist
  window.localStorage.setItem("splitshot.activeView", viewName);

  // Update shell context
  updateShellContext();
}

function getActiveView() {
  return currentView;
}

function getPreviousView() {
  return previousView;
}

function updateShellContext() {
  const returnBtn = document.getElementById("shell-return-match");

  if (returnBtn) {
    const stageVisible = activeSurface === "single" || currentView === "stage";
    returnBtn.hidden = !(stageVisible && Boolean(state?.return_to_match_available));
  }
}

// Stage empty state management
function updateStageEmptyState() {
  const emptyEl = document.getElementById("stage-empty-state");
  if (!emptyEl) return;
  const hasMedia = !!(state?.media?.primary_available || state?.project?.primary_path);
  emptyEl.style.display = hasMedia ? "none" : "flex";
}

// Wire empty state buttons
document.getElementById("stage-empty-import")?.addEventListener("click", () => {
  void openPrimaryImportPathPicker();
});
document.getElementById("stage-empty-open")?.addEventListener("click", () => {
  document.getElementById("browse-project-path")?.click();
});


// === GLOBAL ERROR BANNER ===
function showGlobalError(message, { duration = 8000, action = null, actionLabel = "Retry" } = {}) {
  let banner = document.getElementById("global-error-banner");
  if (!banner) {
    banner = document.createElement("div");
    banner.id = "global-error-banner";
    banner.className = "error-banner";
    banner.style.cssText = "position:fixed;top:0;left:0;right:0;z-index:100;display:none;";
    document.getElementById("app-shell")?.prepend(banner);
  }
  banner.innerHTML = `
    <span>${message}</span>
    <div style="display:flex;gap:8px;">
      ${action ? `<button type="button" id="global-error-action">${actionLabel}</button>` : ""}
      <button type="button" id="global-error-dismiss">Dismiss</button>
    </div>
  `;
  banner.style.display = "flex";
  document.getElementById("global-error-dismiss")?.addEventListener("click", () => {
    banner.style.display = "none";
  });
  document.getElementById("global-error-action")?.addEventListener("click", () => {
    banner.style.display = "none";
    if (action) action();
  });
  if (duration > 0) {
    setTimeout(() => { banner.style.display = "none"; }, duration);
  }
}

function dismissGlobalError() {
  const banner = document.getElementById("global-error-banner");
  if (banner) banner.style.display = "none";
}

function wireShellHeaderEvents() {
  document.getElementById("shell-return-match")?.addEventListener("click", () => {
    void returnToMatchWorkspace();
  });
}

// Keyboard shortcuts for view switching (Ctrl/Cmd + 1/2/3)
document.addEventListener("keydown", (e) => {
  if ((e.ctrlKey || e.metaKey) && !e.target.closest("input, textarea, select, [contenteditable]")) {
    if (e.key === "1") { e.preventDefault(); setActiveSurface("single"); }
    else if (e.key === "2") { e.preventDefault(); setActiveSurface("multi"); }
    else if (e.key === "3") { e.preventDefault(); setActiveSurface("library"); }
  }
});

function wireLandingNavigation() {
  // New-project / new-match buttons on the landing page (not handled by wireEvents)
  document.getElementById("landing-new-stage")?.addEventListener("click", async () => {
    await callApi("/api/project/new", {});
    setActiveSurface("single");
  });

  document.getElementById("landing-new-match")?.addEventListener("click", async () => {
    await callApi("/api/workspace/new", {});
    selectedStageCompositeStageId = null;
    setActiveSurface("multi");
  });
}

let state = null;
let selectedShotId = null;
let activeTool = window.localStorage.getItem("splitshot.activeTool") || "project";
let activeSurface = window.localStorage.getItem("splitshot.activeSurface") || "landing";
let automationPanelOpen = false;
let landingPageVisible = false;
let landingRecentItems = [];
let landingRecentLoaded = false;
let landingRecentRequestSequence = 0;
let overlayFrame = null;
let overlayFrameMode = null;
let waveformMode = "select";
let waveformTrackMode = "single";
let draggingShotId = null;
let draggingShotPointerId = null;
let pendingDragTimeMs = null;
let waveformPanDrag = null;
let waveformNavigatorDrag = null;
let timingRowEdits = new Set();
let timingAdjustmentDrafts = new Map();
let scoringRowEdits = new Set();
let reviewTextBoxExpansion = new Map();
let popupBubbleExpansion = new Map();
let mergeSourceExpansion = new Map();
let shotMLSectionExpansion = new Map();
let settingsSectionExpansion = new Map();
let selectedPopupBubbleId = null;
let selectedPopupKeyframeOffsetMs = 0;
let selectedPopupPlacementMode = "base";
let popupFilterMode = window.localStorage.getItem("splitshot.popupFilterMode") || "all";
let popupAuthoringCollapsed = false;
let popupEditorVisible = false;
let popupEditorCollapsed = false;
let popupEditorSectionExpansion = new Map();
let popupGeneratedMotionOffsetsByBubbleId = new Map();
let popupMotionGenerationSummaryByBubbleId = new Map();
let popupAutoTraceBubbleId = null;
let popupWorkbenchHeight = null;
let popupWorkbenchRestoreState = null;
let scoringWorkbenchExpanded = false;
let overlayVisibilityPosition = "bottom";
let railCollapsed = window.localStorage.getItem("splitshot.railCollapsed") === "true";
let overlayStyleMode = "square";
let overlaySpacing = 8;
let overlayMargin = 8;
let waveformZoomX = savedNumber("splitshot.waveform.zoomX", 1);
let waveformShotAmplitudeById = {};
let waveformOffsetMs = Math.max(0, Number(window.localStorage.getItem("splitshot.waveform.offsetMs")) || 0);
let busyCount = 0;
let layoutLocked = window.localStorage.getItem("splitshot.layoutLocked") !== "false";
const DEFAULT_LAYOUT_SIZES = Object.freeze({
  railWidth: 84,
  inspectorWidth: 440,
  waveformHeight: 206,
});
let layoutSizes = {
  railWidth: clamp(savedNumber("splitshot.layout.railWidth", DEFAULT_LAYOUT_SIZES.railWidth), 84, 104),
  inspectorWidth: savedNumber("splitshot.layout.inspectorWidth", DEFAULT_LAYOUT_SIZES.inspectorWidth),
  waveformHeight: savedNumber("splitshot.layout.waveformHeight", DEFAULT_LAYOUT_SIZES.waveformHeight),
};
let layoutSizePinned = {
  railWidth: window.localStorage.getItem("splitshot.layout.railWidth") !== null,
  inspectorWidth: window.localStorage.getItem("splitshot.layout.inspectorWidth") !== null,
  waveformHeight: window.localStorage.getItem("splitshot.layout.waveformHeight") !== null,
};
let activeResize = null;
let timingColumnWidths = {};
let timingColumnResize = null;
let currentProjectId = null;
let exportPathDraft = "";
let exportDraft = {};
let mergeDraft = {};
let overlayPositionDraft = {};
let overlayStyleDraft = null;
let projectDetailsDraft = { name: null, description: null };
let overlayTextBoxesDraft = null;
let popupBubblesDraft = null;
let popupTemplateDraft = null;
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
let popupBubbleDrag = null;
let exportLogLines = [];
let activeColorPickerControl = null;
let reviewStageRestoreFrame = null;
let reviewStageRestoreSecondFrame = null;
let overlayBadgeMeasureCanvas = null;
let overlayAutoBubbleCacheKey = null;
let overlayAutoBubbleCache = { width: 0, height: 0 };
let customOverlayRenderKey = "";
let textBoxRenderedPositionById = new Map();
let metricsSectionExpansion = new Map([
  ["trend-snapshot", true],
  ["scoring-context", true],
]);
let pendingInspectorScrollTop = null;
let lastInspectorUserScrollTop = 0;
let lastInspectorUserScrollTs = 0;
let renderDeferredForInteraction = false;
let pendingProjectUiStatePayload = null;
let lastSubmittedProjectUiStatePayloadKey = null;
let pendingMergeSourcePayloads = new Map();
let mergeSourceCommitTimers = new Map();
let interactionPreviewFrame = null;
let pendingInteractionPreview = { video: false, waveform: false, overlay: false };
let pendingSelectionFallback = null;
let initialProjectUiStateApplied = false;
let pendingBootstrapProjectUiStateOverride = false;
let forcedProjectLandingPersistedTool = null;
let automationProfiles = [];
let automationLibrary = { stages: [], matches: [], total_stages: 0, total_matches: 0 };
let selectedLibraryRecord = null;
let selectedStageCompositeStageId = null;
let matchRecapSelectedStageIds = null;
let matchRecapKnownStageIds = new Set();
let matchRecapTransitionValue = "cut";
let matchRecapResultCardValue = "none";
let matchRecapStatusText = "Ready to render a match recap.";
let matchRecapResultsText = "";
let matchRecapResultsHidden = true;
let stageCompositeClips = [];
let selectedCompositeOutputId = null;
let selectedAutomationOutputProfileId = null;
let automationProfileScopeKey = "";
let automationLoading = { profiles: false, workspace: false, clips: false, library: false };
let automationError = { profiles: null, workspace: null, clips: null, library: null };
let automationStale = { library: false };
let libraryRefreshSequence = 0;
let retainedReviewSourceProfileId = null;
let activeOutputHookEditor = null;
let renderOutputHookEditor = () => {};

let processingRuntime = null;
let activityRuntime = null;
let layoutRuntime = null;
let keyRuntime = null;
let apiRuntime = null;
let waveformStateRuntime = null;
let shellRuntime = null;
let matchView = null;
let libraryView = null;

let statusBarComponent = null;
let videoPlayerComponent = null;
let waveformComponent = null;
let overlayCanvasComponent = null;

let shotmlPane = null;
let markersPane = null;
let overlayPane = null;
let exportPane = null;
let settingsPane = null;
let mergePane = null;
let projectPane = null;
let reviewPane = null;
let timingPane = null;
let scoringPane = null;
let metricsPane = null;

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
  segment: 160,
  split: 112,
  total: 108,
  action: 240,
  confidence: 148,
  adjustment: 132,
  final: 108,
  delete: 92,
  restore: 104,
});
const SCORING_COLUMN_DEFAULTS = Object.freeze({
  lock: 72,
  shot: 144,
  score: 132,
  penalties: 184,
  split: 112,
  run: 108,
  action: 196,
  delete: 92,
  restore: 104,
});
const TIMING_COLUMN_MIN_WIDTHS = Object.freeze({
  lock: 60,
  segment: 104,
  shot: 104,
  split: 92,
  total: 88,
  action: 140,
  score: 96,
  penalties: 140,
  run: 88,
  confidence: 128,
  adjustment: 112,
  final: 88,
  delete: 76,
  restore: 88,
});
const TIMING_TABLE_COLUMN_ORDER = Object.freeze({
  "timing-table": ["segment", "split", "total", "action"],
  "timing-workbench-table": ["lock", "segment", "split", "total", "action", "confidence", "adjustment", "final", "delete", "restore"],
  "scoring-table": ["shot", "score", "penalties", "split", "run", "action"],
  "scoring-workbench-table": ["lock", "shot", "score", "penalties", "split", "run", "action", "delete", "restore"],
});
const POPUP_FILTER_OPTIONS = Object.freeze([
  "all",
  "enabled",
  "disabled",
  "shot",
  "time",
  "motion",
  "missing_text",
  "visible",
]);
const VALID_POPUP_FILTER_MODES = new Set(POPUP_FILTER_OPTIONS);
const TIMING_RESIZABLE_COLUMNS = new Set(["segment", "split", "total", "action", "confidence", "adjustment", "final", "shot", "score", "penalties", "run"]);
const PIP_DEFAULTS_SECTION_ID = "pip-defaults";
const METRICS_TABLE_COLUMNS = Object.freeze([
  ["Shot", "segment"],
  ["ShotML Split", "shotmlSplit"],
  ["Adjustment", "adjustment"],
  ["Final Split", "finalSplit"],
  ["Final Time", "finalTime"],
  ["Score", "score"],
  ["Penalties", "penalties"],
  ["PractiScore", "practiscore"],
  ["Delta", "delta"],
  ["Confidence", "confidence"],
  ["Action", "action"],
]);

const badgeControls = [
  ["timer_badge", "Timer Badge"],
  ["shot_badge", "Shot Badge"],
  ["current_shot_badge", "Current Shot Badge"],
  ["hit_factor_badge", "Score Badge"],
];
const badgeDisplayLabels = {
  timer_badge: "Timer",
  shot_badge: "Shot",
  current_shot_badge: "Current",
  hit_factor_badge: "Score",
};
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
const POPUP_SELECTOR_TEXT_MAX_LENGTH = 3;
const POPUP_SELECTOR_MIN_DIAMETER_PX = 28;
const POPUP_SELECTOR_MAX_DIAMETER_PX = 32;
const POPUP_SELECTOR_FILL = "#ff7b22";
const POPUP_SELECTOR_TEXT = "#111111";
const POPUP_SELECTOR_BORDER = "#050607";
const POPUP_MOTION_REFERENCE_FPS = 60;
const POPUP_MOTION_FRAME_BUDGET_PER_POINT = 4;
const POPUP_MOTION_TRAVEL_PX_PER_POINT = 48;
const POPUP_MOTION_TIME_BUDGET_PER_POINT_MS = Math.round(POPUP_MOTION_FRAME_BUDGET_PER_POINT * 1000 / POPUP_MOTION_REFERENCE_FPS);
const POPUP_MOTION_MAX_AUTO_POINTS = 14;
const SECONDARY_PREVIEW_PAUSED_SEEK_THRESHOLD_S = 0.01;
const SECONDARY_PREVIEW_ACTIVE_SEEK_THRESHOLD_S = 0.65;
const SECONDARY_PREVIEW_PLAYBACK_RATE_DRIFT_THRESHOLD_S = 0.035;
const SECONDARY_PREVIEW_MAX_PLAYBACK_RATE_DELTA = 0.12;
const SECONDARY_PREVIEW_MIN_SEEK_INTERVAL_MS = 900;
const secondaryPreviewLastSeekAt = new WeakMap();
let previewSeekBoundary = false;
let previewSyncedSinceBoundary = false;
let previewSeekBoundaryBatchActive = false;
const DEFAULT_POPUP_EDITOR_SECTION_EXPANSION = Object.freeze({
  content: true,
  timing: false,
  motion: false,
  style: false,
});
const ABOVE_FINAL_TEXT_BOX_VALUE = "above_final";
const CUSTOM_QUADRANT_VALUE = "custom";
function normalizeToolId(tool) {
  const normalized = String(tool || "project");
  if (normalized === "popup") return "markers";
  return normalized;
}

activeTool = normalizeToolId(activeTool);

const VALID_TOOL_IDS = new Set(["project", "scoring", "timing", "settings", "shotml", "merge", "overlay", "review", "markers", "export", "metrics"]);
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
  timing_enabled: true,
  review_show_markers: true,
  review_show_pip: true,
  metrics_expanded: false,
  markers_expanded: false,
  scoring_expanded: false,
  layout_locked: layoutLocked,
  rail_width: Math.round(layoutSizes.railWidth),
  inspector_width: Math.round(layoutSizes.inspectorWidth),
  waveform_height: Math.round(layoutSizes.waveformHeight),
  scoring_edit_shot_ids: [],
  waveform_shot_amplitudes: {},
  timing_edit_shot_ids: [],
  timing_column_widths: { ...TIMING_COLUMN_DEFAULTS },
  review_text_box_expansion: {},
  popup_bubble_expansion: {},
  popup_authoring_collapsed: false,
  merge_source_expansion: {},
  shotml_section_expansion: {},
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

const appBus = createEventBus();
const appStore = createStore({
  state,
  selectedShotId,
  activeTool,
  busyCount,
  layoutLocked,
  layoutSizes: { ...layoutSizes },
  currentProjectId,
  pendingSelectionFallback,
  initialProjectUiStateApplied,
  pendingBootstrapProjectUiStateOverride,
});

function syncBackboneStore(patch = {}) {
  return appStore.patch(patch);
}

function setStateValue(value) {
  state = value;
  syncBackboneStore({ state });
  return state;
}

function setSelectedShotIdValue(value) {
  selectedShotId = value === null || value === undefined || String(value).trim() === ""
    ? null
    : String(value);
  syncBackboneStore({ selectedShotId });
  return selectedShotId;
}

function setActiveToolValue(value) {
  activeTool = normalizeToolId(value);
  syncBackboneStore({ activeTool });
  return activeTool;
}

function normalizeMergeDraftValue(key, value) {
  if (!["enabled", "layout", "pip_size_percent", "pip_x", "pip_y"].includes(key)) {
    return undefined;
  }
  if (key === "enabled") return Boolean(value);
  if (key === "layout") return String(value || "side_by_side");
  if (key === "pip_size_percent") {
    return clampNumber(Number(value) || 35, 1, 95);
  }
  return normalizedCoordinateValue(value) ?? 1;
}

function applyMergeDraft(payload = {}) {
  const mergeState = state?.project?.merge;
  Object.entries(payload).forEach(([key, value]) => {
    const normalized = normalizeMergeDraftValue(key, value);
    if (normalized === undefined) return;
    mergeDraft[key] = normalized;
    if (mergeState) mergeState[key] = normalized;
  });
}

function mergeMergeDraft(project) {
  const mergeState = project?.merge;
  if (!mergeState) return;
  Object.entries(mergeDraft).forEach(([key, value]) => {
    const savedValue = normalizeMergeDraftValue(key, mergeState[key]);
    if (Object.is(value, savedValue)) {
      delete mergeDraft[key];
    } else {
      mergeState[key] = value;
    }
  });
}

function normalizeOverlayPositionDraftValue(key, value) {
  if (![
    "position",
    "shot_quadrant",
    "shot_direction",
    "custom_x",
    "custom_y",
    "timer_x",
    "timer_y",
    "draw_x",
    "draw_y",
    "score_x",
    "score_y",
    "timer_lock_to_stack",
    "draw_lock_to_stack",
    "score_lock_to_stack",
  ].includes(key)) {
    return undefined;
  }
  if (["position", "shot_quadrant", "shot_direction"].includes(key)) {
    return String(value ?? "");
  }
  if (key.endsWith("_lock_to_stack")) {
    return Boolean(value);
  }
  if (value === "" || value === null || value === undefined) return null;
  return normalizedCoordinateValue(value) ?? null;
}

function applyOverlayPositionDraft(payload = {}) {
  const overlay = state?.project?.overlay;
  Object.entries(payload).forEach(([key, value]) => {
    const normalized = normalizeOverlayPositionDraftValue(key, value);
    if (normalized === undefined) return;
    overlayPositionDraft[key] = normalized;
    if (overlay) overlay[key] = normalized;
  });
}

function mergeOverlayPositionDraft(project) {
  const overlay = project?.overlay;
  if (!overlay) return;
  Object.entries(overlayPositionDraft).forEach(([key, value]) => {
    const savedValue = normalizeOverlayPositionDraftValue(key, overlay[key]);
    if (Object.is(value, savedValue)) {
      delete overlayPositionDraft[key];
    } else {
      overlay[key] = value;
    }
  });
}

function normalizeOverlayBadgeStyleDraft(style = {}, fallback = {}) {
  return {
    background_color: normalizeHexColor(style?.background_color || fallback?.background_color || "")
      || normalizeHexColor(fallback?.background_color || "")
      || "#000000",
    text_color: normalizeHexColor(style?.text_color || fallback?.text_color || "")
      || normalizeHexColor(fallback?.text_color || "")
      || "#ffffff",
    opacity: clampNumber(Number(style?.opacity ?? fallback?.opacity ?? 0.9) || 0.9, 0, 1),
  };
}

function normalizeOverlayFieldDraftValue(key, value, fallback = undefined) {
  if (["position", "badge_size", "style_type", "shot_quadrant", "shot_direction", "font_family"].includes(key)) {
    const normalized = String(value ?? fallback ?? "").trim();
    return normalized || String(fallback ?? "").trim();
  }
  if (["spacing", "margin", "bubble_width", "bubble_height"].includes(key)) {
    return Math.max(0, Number(value ?? fallback ?? 0) || 0);
  }
  if (key === "max_visible_shots") {
    return Math.max(1, Number(value ?? fallback ?? 1) || 1);
  }
  if (key === "font_size") {
    return Math.max(8, Number(value ?? fallback ?? 14) || 14);
  }
  if (["font_bold", "font_italic", "show_timer", "show_draw", "show_shots", "show_score"].includes(key)) {
    return Boolean(value ?? fallback);
  }
  return undefined;
}

function normalizeOverlayScoringColorDraftValue(value, fallback = "") {
  return normalizeHexColor(value || fallback || "") || normalizeHexColor(fallback || "") || "";
}

function overlayBadgeStyleDraftsMatch(draftStyle, savedStyle) {
  if (!draftStyle) return true;
  const normalizedSavedStyle = normalizeOverlayBadgeStyleDraft(savedStyle, draftStyle);
  return draftStyle.background_color === normalizedSavedStyle.background_color
    && draftStyle.text_color === normalizedSavedStyle.text_color
    && Object.is(draftStyle.opacity, normalizedSavedStyle.opacity);
}

function applyOverlayStyleDraft(payload = {}) {
  const overlay = state?.project?.overlay;
  const styles = payload?.styles;
  const scoringColors = payload?.scoring_colors;
  const hasDraftableFields = Object.entries(payload || {}).some(([key, value]) => {
    return normalizeOverlayFieldDraftValue(key, value, overlay?.[key]) !== undefined;
  });
  if (!hasDraftableFields && (!styles || typeof styles !== "object") && (!scoringColors || typeof scoringColors !== "object")) return;
  overlayStyleDraft ||= { fields: {}, styles: {}, scoring_colors: {} };
  Object.entries(payload).forEach(([key, value]) => {
    const normalizedValue = normalizeOverlayFieldDraftValue(key, value, overlay?.[key]);
    if (normalizedValue === undefined) return;
    overlayStyleDraft.fields[key] = normalizedValue;
    if (overlay) overlay[key] = normalizedValue;
  });
  if (styles && typeof styles === "object") {
    Object.entries(styles).forEach(([badgeName, style]) => {
      if (!VALID_OVERLAY_BADGE_NAMES.has(badgeName) || !style || typeof style !== "object") return;
      const fallbackStyle = overlay?.[badgeName] || {};
      const normalizedStyle = normalizeOverlayBadgeStyleDraft(style, fallbackStyle);
      overlayStyleDraft.styles[badgeName] = normalizedStyle;
      if (overlay?.[badgeName]) {
        overlay[badgeName] = {
          ...overlay[badgeName],
          ...normalizedStyle,
        };
      }
    });
  }
  if (scoringColors && typeof scoringColors === "object") {
    Object.entries(scoringColors).forEach(([scoreKey, color]) => {
      const normalizedScoreKey = String(scoreKey || "").trim();
      const normalizedColor = normalizeOverlayScoringColorDraftValue(color, overlay?.scoring_colors?.[normalizedScoreKey]);
      if (!normalizedScoreKey || !normalizedColor) return;
      overlayStyleDraft.scoring_colors[normalizedScoreKey] = normalizedColor;
      if (overlay) {
        overlay.scoring_colors = {
          ...(overlay.scoring_colors || {}),
          [normalizedScoreKey]: normalizedColor,
        };
      }
    });
  }
  if (
    Object.keys(overlayStyleDraft.fields).length === 0
    && Object.keys(overlayStyleDraft.styles).length === 0
    && Object.keys(overlayStyleDraft.scoring_colors).length === 0
  ) {
    overlayStyleDraft = null;
  }
}

function mergeOverlayStyleDraft(project) {
  const overlay = project?.overlay;
  if (!overlayStyleDraft || !overlay) return;
  Object.entries(overlayStyleDraft.fields || {}).forEach(([key, draftValue]) => {
    const savedValue = normalizeOverlayFieldDraftValue(key, overlay[key], overlay[key]);
    if (Object.is(draftValue, savedValue)) {
      delete overlayStyleDraft.fields[key];
      return;
    }
    overlay[key] = draftValue;
  });
  const nextStyleDraftEntries = Object.entries(overlayStyleDraft.styles || {});
  nextStyleDraftEntries.forEach(([badgeName, draftStyle]) => {
    if (overlayBadgeStyleDraftsMatch(draftStyle, overlay[badgeName])) {
      delete overlayStyleDraft.styles[badgeName];
      return;
    }
    overlay[badgeName] = {
      ...(overlay[badgeName] || {}),
      ...draftStyle,
    };
  });
  Object.entries(overlayStyleDraft.scoring_colors || {}).forEach(([scoreKey, draftColor]) => {
    const savedColor = normalizeOverlayScoringColorDraftValue(overlay.scoring_colors?.[scoreKey], draftColor);
    if (draftColor === savedColor) {
      delete overlayStyleDraft.scoring_colors[scoreKey];
      return;
    }
    overlay.scoring_colors = {
      ...(overlay.scoring_colors || {}),
      [scoreKey]: draftColor,
    };
  });
  if (
    Object.keys(overlayStyleDraft.fields).length === 0
    && Object.keys(overlayStyleDraft.styles).length === 0
    && Object.keys(overlayStyleDraft.scoring_colors).length === 0
  ) {
    overlayStyleDraft = null;
  }
}

function applyOverlayTextBoxesDraft(boxes = []) {
  overlayTextBoxesDraft = Array.isArray(boxes)
    ? boxes.map((box, index) => normalizeOverlayTextBox(box, index))
    : null;
}

function mergeOverlayTextBoxesDraft(project) {
  const overlay = project?.overlay;
  if (!overlay || !Array.isArray(overlayTextBoxesDraft)) return;
  overlay.text_boxes = overlayTextBoxesDraft.map((box, index) => normalizeOverlayTextBox(box, index));
  syncLegacyOverlayBoxState(overlay, overlay.text_boxes);
}

function popupBubblesDraftKey(bubbles = []) {
  const normalizedBubbles = Array.isArray(bubbles)
    ? bubbles.map((bubble) => normalizePopupBubble(bubble))
    : [];
  return JSON.stringify(normalizedBubbles);
}

function popupImagePathsEquivalent(draftPath, savedPath) {
  const normalizedDraftPath = String(draftPath || "").trim();
  const normalizedSavedPath = String(savedPath || "").trim();
  if (normalizedDraftPath === normalizedSavedPath) return true;
  if (!normalizedDraftPath || !normalizedSavedPath) return false;
  return fileName(normalizedDraftPath) === fileName(normalizedSavedPath)
    && normalizedSavedPath.replace(/\\/g, "/").split("/").includes("Markers");
}

function popupBubblesDraftsMatch(draftBubbles = [], savedBubbles = []) {
  const normalizedDraftBubbles = Array.isArray(draftBubbles)
    ? draftBubbles.map((bubble) => normalizePopupBubble(bubble))
    : [];
  const normalizedSavedBubbles = Array.isArray(savedBubbles)
    ? savedBubbles.map((bubble) => normalizePopupBubble(bubble))
    : [];
  if (normalizedDraftBubbles.length !== normalizedSavedBubbles.length) return false;
  return normalizedDraftBubbles.every((bubble, index) => {
    const savedBubble = normalizedSavedBubbles[index];
    if (!savedBubble) return false;
    const comparableDraftBubble = { ...bubble };
    if (popupImagePathsEquivalent(comparableDraftBubble.image_path, savedBubble.image_path)) {
      comparableDraftBubble.image_path = savedBubble.image_path;
    }
    return JSON.stringify(comparableDraftBubble) === JSON.stringify(savedBubble);
  });
}

function popupTemplateDraftKey(template = {}) {
  return JSON.stringify(normalizePopupTemplate(template || {}));
}

function applyPopupDraft(payload = {}) {
  const project = state?.project;
  if (Object.prototype.hasOwnProperty.call(payload, "popups")) {
    popupBubblesDraft = Array.isArray(payload.popups)
      ? payload.popups.map((bubble) => normalizePopupBubble(bubble))
      : [];
    if (project) {
      project.popups = popupBubblesDraft.map((bubble) => normalizePopupBubble(bubble));
      prunePopupMotionUiState(project.popups);
    }
  }
  if (Object.prototype.hasOwnProperty.call(payload, "popup_template")) {
    popupTemplateDraft = normalizePopupTemplate(payload.popup_template || {});
    if (project) project.popup_template = { ...popupTemplateDraft };
  }
}

function mergePopupDraft(project) {
  if (!project) return;
  if (Array.isArray(popupBubblesDraft)) {
    const savedBubbles = Array.isArray(project.popups)
      ? project.popups.map((bubble) => normalizePopupBubble(bubble))
      : [];
    if (popupBubblesDraftsMatch(popupBubblesDraft, savedBubbles)) {
      popupBubblesDraft = null;
    } else {
      const savedBubbleById = new Map(savedBubbles.map((bubble) => [bubble.id, bubble]));
      popupBubblesDraft = popupBubblesDraft.map((bubble) => {
        const normalizedBubble = normalizePopupBubble(bubble);
        const savedBubble = savedBubbleById.get(normalizedBubble.id);
        if (!savedBubble || !popupImagePathsEquivalent(normalizedBubble.image_path, savedBubble.image_path)) {
          return normalizedBubble;
        }
        return normalizePopupBubble({
          ...normalizedBubble,
          image_path: savedBubble.image_path,
        });
      });
      project.popups = popupBubblesDraft.map((bubble) => normalizePopupBubble(bubble));
    }
  }
  if (popupTemplateDraft) {
    const savedTemplate = normalizePopupTemplate(project.popup_template || {});
    if (popupTemplateDraftKey(popupTemplateDraft) === popupTemplateDraftKey(savedTemplate)) {
      popupTemplateDraft = null;
    } else {
      project.popup_template = { ...popupTemplateDraft };
    }
  }
}

function normalizeExportDraftValue(key, value) {
  if (![
    "quality",
    "aspect_ratio",
    "target_width",
    "target_height",
    "frame_rate",
    "video_codec",
    "video_bitrate_mbps",
    "audio_codec",
    "audio_sample_rate",
    "audio_bitrate_kbps",
    "color_space",
    "two_pass",
    "ffmpeg_preset",
  ].includes(key)) {
    return undefined;
  }
  if (value === undefined) return undefined;
  if (key === "target_width" || key === "target_height") {
    return value === "" || value === null ? null : Math.max(2, Number(value));
  }
  if (key === "video_bitrate_mbps") {
    return Math.max(0.1, Number(value));
  }
  if (key === "audio_sample_rate") {
    return Math.max(8000, Number(value));
  }
  if (key === "audio_bitrate_kbps") {
    return Math.max(32, Number(value));
  }
  if (key === "two_pass") {
    return Boolean(value);
  }
  return String(value ?? "");
}

function applyExportDraft(payload = {}) {
  const exportState = state?.project?.export;
  Object.entries(payload).forEach(([key, value]) => {
    const normalized = normalizeExportDraftValue(key, value);
    if (normalized === undefined) return;
    exportDraft[key] = normalized;
    if (exportState) exportState[key] = normalized;
  });
}

function mergeExportDraft(project) {
  const exportState = project?.export;
  if (!exportState) return;
  Object.entries(exportDraft).forEach(([key, value]) => {
    const savedValue = normalizeExportDraftValue(key, exportState[key]);
    if (value === savedValue) {
      delete exportDraft[key];
    } else {
      exportState[key] = value;
    }
  });
}

function flushActivityQueue() {
  return activityRuntime?.flushActivityQueue();
}

function queueActivity(event, detail = {}) {
  return activityRuntime?.queueActivity(event, detail);
}

function activity(event, detail = {}) {
  if (activityRuntime?.activity) return activityRuntime.activity(event, detail);
  console.info("[splitshot]", event, detail);
  return undefined;
}

function clearActivityPollTimer() {
  return activityRuntime?.clearActivityPollTimer();
}

function appendExportLogLine(line) {
  return activityRuntime?.appendExportLogLine(line);
}

function clearCurrentExportLogState() {
  if (activityRuntime?.clearCurrentExportLogState) return activityRuntime.clearCurrentExportLogState();
  exportLogLines = [];
  if (state?.project?.export) {
    state.project.export.last_log = "";
    state.project.export.last_error = null;
  }
  renderExportLog();
  return undefined;
}

function consumeActivityEntries(entries = []) {
  return activityRuntime?.consumeActivityEntries(entries);
}

function runActivityPoll() {
  return activityRuntime?.runActivityPoll();
}

function startActivityPolling() {
  return activityRuntime?.startActivityPolling();
}

function stopActivityPolling() {
  return activityRuntime?.stopActivityPolling();
}

function buttonDescriptor(button) {
  return activityRuntime?.buttonDescriptor(button) || {
    id: button?.id || "",
    text: button?.textContent?.trim?.().replace?.(/\s+/g, " ") || "",
    tool: button?.dataset?.tool || "",
    waveform_mode: button?.dataset?.waveformMode || "",
    nudge_ms: button?.dataset?.nudge || "",
    sync_ms: button?.dataset?.sync || "",
    opens_media: Boolean(button?.hasAttribute?.("data-open-merge-media")),
  };
}

function wireGlobalActivityLogging() {
  return activityRuntime?.wireGlobalActivityLogging();
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
  setSelectedShotIdValue(resolveSelectedShotId(nextState, requestedShotId, fallbackContext));
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
    steel_challenge: "Steel Challenge",
  }[String(matchType || "").toLowerCase()] || "PractiScore";
}

function formatPractiScoreTime(value, { includeUnits = true } = {}) {
  if (value === null || value === undefined || value === "") return "";
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return String(value);
  return `${numeric.toFixed(2)}${includeUnits ? "s" : ""}`;
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

function defaultScoreLetter(ruleset = activeScoringRuleset()) {
  const options = Array.isArray(state?.scoring_summary?.score_options)
    ? state.scoring_summary.score_options
    : [];
  if (options[0]) return options[0];
  const normalizedRuleset = String(ruleset || "").trim().toLowerCase();
  if (normalizedRuleset === "idpa_time_plus") return "-0";
  return "A";
}

function activeScoringRuleset() {
  return String(state?.scoring_summary?.ruleset || state?.project?.scoring?.ruleset || "");
}

function compactScoreDisplay(letter, ruleset = activeScoringRuleset()) {
  const normalizedLetter = String(letter || "").trim();
  if (!normalizedLetter) return "";
  return normalizedLetter;
}

function shotById(shotId) {
  if (!shotId) return null;
  return orderedShotsByTime().find((shot) => shot.id === shotId) || null;
}

function timingSegmentForShot(shotId) {
  if (!shotId) return null;
  return (state?.timing_segments || []).find((segment) => segment.shot_id === shotId) || null;
}

function popupTextForShotId(shotId) {
  if (!shotId) return "";
  const ruleset = activeScoringRuleset();
  const defaultLetter = defaultScoreLetter(ruleset);
  const segment = timingSegmentForShot(shotId);
  const shot = shotById(shotId);
  const rawLetter = segment?.score_letter
    || shot?.score?.letter?.value
    || shot?.score?.letter
    || defaultLetter;
  const scoreLetter = compactScoreDisplay(rawLetter, ruleset) || defaultLetter;
  const penaltyText = formatPenaltyCountsText(segment?.penalty_counts || shot?.score?.penalty_counts || {});
  return [scoreLetter, penaltyText].filter(Boolean).join(" | ");
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

function collectPenaltyCounts(scope, selector = ".shot-penalty-entry-control[data-penalty-id]") {
  const penaltyCounts = {};
  scope.querySelectorAll(selector).forEach((input) => {
    const penaltyId = String(input.dataset.penaltyId || input.value || "").trim();
    if (!penaltyId) return;
    if (input instanceof HTMLSelectElement) {
      penaltyCounts[penaltyId] = (penaltyCounts[penaltyId] || 0) + 1;
      return;
    }
    penaltyCounts[penaltyId] = numberInputValue(input, 0);
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
    element.scrollLeft = element.closest(".inspector") || element.classList.contains("inspector") ? 0 : scrollLeft;
  });
  resetInspectorHorizontalScroll();
}

function withPreservedScrollState(elements, callback) {
  const targets = Array.isArray(elements) ? elements : [elements];
  const scrollState = captureScrollState(targets);
  const result = callback();
  restoreScrollState(scrollState);
  return result;
}

function scrollContainerForElement(element) {
  if (!(element instanceof HTMLElement)) return null;
  return element.closest(".popup-marker-list, .popup-bubble-list, .text-box-list, .merge-media-list, .inspector");
}

function preserveElementViewportAnchor(elementOrResolver, callback) {
  const resolveElement = () => (typeof elementOrResolver === "function" ? elementOrResolver() : elementOrResolver);
  const before = resolveElement();
  const beforeTop = before instanceof HTMLElement ? before.getBoundingClientRect().top : null;
  const beforeContainer = scrollContainerForElement(before);
  const result = callback();
  const after = resolveElement();
  const afterContainer = scrollContainerForElement(after) || beforeContainer;
  if (beforeTop !== null && after instanceof HTMLElement && afterContainer instanceof HTMLElement) {
    const delta = after.getBoundingClientRect().top - beforeTop;
    if (Math.abs(delta) > 0.5) afterContainer.scrollTop += delta;
    if (afterContainer.classList.contains("inspector") || afterContainer.closest(".inspector")) afterContainer.scrollLeft = 0;
  }
  return result;
}

function scrollRenderTargets() {
  return [
    document.querySelector(".tool-nav"),
    document.querySelector(".inspector"),
  ].filter((element) => element instanceof HTMLElement);
}

function resetInspectorHorizontalScroll() {
  const inspector = document.querySelector(".inspector");
  if (!(inspector instanceof HTMLElement)) return;
  inspector.scrollLeft = 0;
  inspector.querySelectorAll(".tool-pane, .inspector-section, .text-box-manager, .text-box-list, .text-box-card, .merge-media-list, .merge-media-card, .shotml-section, .pip-defaults-section").forEach((element) => {
    if (element instanceof HTMLElement) element.scrollLeft = 0;
  });
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
    resetInspectorHorizontalScroll();
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
  const popupBubbleCard = colorInput.closest(".popup-bubble-card");
  const popupBubbleField = colorInput.dataset.popupField || "";
  if (textBoxCard?.dataset.boxId && textBoxField) {
    setOverlayTextBoxField(textBoxCard.dataset.boxId, textBoxField, normalized, { rerender: false });
  } else if (popupBubbleCard?.dataset.popupId && popupBubbleField) {
    setPopupBubbleField(popupBubbleCard.dataset.popupId, popupBubbleField, normalized, { commit, rerender: true });
  } else {
    previewOverlayControlChanges();
  }
  if (colorInput === activeColorPickerControl) syncColorPickerModal(normalized);
  if (commit && !popupBubbleCard) {
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
  const popupBubbleCard = colorControl.closest(".popup-bubble-card");
  const popupBubbleField = colorControl.dataset.popupField || "";
  if (changed) {
    if (textBoxCard?.dataset.boxId && textBoxField) {
      setOverlayTextBoxField(textBoxCard.dataset.boxId, textBoxField, normalized, { rerender: false });
    } else if (popupBubbleCard?.dataset.popupId && popupBubbleField) {
      setPopupBubbleField(popupBubbleCard.dataset.popupId, popupBubbleField, normalized, { commit: queueCommit, rerender: true });
    } else {
      previewOverlayControlChanges();
    }
  }
  if (colorControl === activeColorPickerControl) syncColorPickerModal(normalized);
  if (!popupBubbleCard && queueCommit) scheduleOverlayColorCommit();
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
  const activeControl = activeColorPickerControl;
  if (!modal || modal.hidden) {
    activeControl?.blur();
    activeColorPickerControl = null;
    return;
  }
  activeControl?.blur();
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

function isImagePath(path) {
  return !!path && /\.(png|jpe?g|webp|gif|bmp|svg)$/i.test(path);
}

function clearProcessingBarShowTimer() {
  return processingRuntime.clearProcessingBarShowTimer();
}

function clearProcessingBarHideTimer() {
  return processingRuntime.clearProcessingBarHideTimer();
}

function clearProcessingProgressTimer() {
  return processingRuntime.clearProcessingProgressTimer();
}

function setProcessingProgress(percent, options = {}) {
  return processingRuntime.setProcessingProgress(percent, options);
}

function progressProfileForPath(path) {
  return processingRuntime.progressProfileForPath(path);
}

function startProcessingProgress(path) {
  return processingRuntime.startProcessingProgress(path);
}

function stopProcessingProgress(finalPercent = 100) {
  return processingRuntime.stopProcessingProgress(finalPercent);
}

function hideProcessingBarNow(finalMessage = "Ready.") {
  return processingRuntime.hideProcessingBarNow(finalMessage);
}

function scheduleProcessingBarShow(message, detail) {
  return processingRuntime.scheduleProcessingBarShow(message, detail);
}

function scheduleProcessingBarHide(finalMessage = "Ready.") {
  return processingRuntime.scheduleProcessingBarHide(finalMessage);
}

function forceHideProcessingBar(finalMessage = "Ready.") {
  return processingRuntime.forceHideProcessingBar(finalMessage);
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
  if (path === "/api/export") clearCurrentExportLogState();
  return processingRuntime.beginProcessing(message, detail, path);
}

function resolvedTimingColumnWidths(data = {}) {
  const resolved = {};
  Object.entries({ ...TIMING_COLUMN_DEFAULTS, ...SCORING_COLUMN_DEFAULTS }).forEach(([columnId, defaultWidth]) => {
    const requestedWidth = Number(data?.[columnId]);
    const minimumWidth = TIMING_COLUMN_MIN_WIDTHS[columnId] || 72;
    resolved[columnId] = Number.isFinite(requestedWidth)
      ? Math.max(minimumWidth, requestedWidth)
      : defaultWidth;
  });
  return resolved;
}

function timingGridTemplate(tableId) {
  const columns = TIMING_TABLE_COLUMN_ORDER[tableId] || [];
  const flex = {
    lock: 0.45,
    segment: 1.15,
    shot: 0.95,
    split: 0.62,
    total: 0.62,
    action: 1.55,
    score: 0.72,
    penalties: 1.2,
    run: 0.62,
    confidence: 1.05,
    adjustment: 0.9,
    final: 0.72,
    delete: 0.52,
    restore: 0.6,
  };
  return columns.map((columnId) => `minmax(0, ${flex[columnId] || 1}fr)`).join(" ");
}

function scoringWorkbenchGridTemplate(table) {
  if (!(table instanceof HTMLElement)) return "";
  const columns = TIMING_TABLE_COLUMN_ORDER["scoring-workbench-table"] || [];
  const weights = {
    lock: 0.7,
    shot: 1.7,
    score: 1.5,
    penalties: 1.8,
    split: 1.2,
    run: 1.2,
    action: 2.5,
    delete: 1.1,
    restore: 1.1,
  };
  const minimums = {
    lock: 84,
    shot: 122,
    score: 122,
    penalties: 132,
    split: 108,
    run: 108,
    action: 168,
    delete: 108,
    restore: 108,
  };
  const containerWidth = table.parentElement instanceof HTMLElement
    ? Math.max(table.parentElement.clientWidth, table.parentElement.getBoundingClientRect().width || 0)
    : 0;
  const tableWidth = Math.max(containerWidth, table.clientWidth, table.getBoundingClientRect().width || 0);
  const totalMinimum = columns.reduce((sum, columnId) => sum + (minimums[columnId] || 96), 0);
  const totalWeight = columns.reduce((sum, columnId) => sum + (weights[columnId] || 1), 0);
  const extraWidth = Math.max(0, tableWidth - totalMinimum);
  return columns.map((columnId) => {
    const minimum = minimums[columnId] || 96;
    const weight = weights[columnId] || 1;
    const width = minimum + ((extraWidth * weight) / totalWeight);
    return `minmax(${minimum}px, ${width}px)`;
  }).join(" ");
}

function applyTimingTableColumns(table) {
  return timingPane?.applyTimingTableColumns(table);
}

function syncTimingTableColumns() {
  return timingPane?.syncTimingTableColumns();
}

function beginTimingColumnResize(tableId, columnId, event) {
  return timingPane?.beginTimingColumnResize(tableId, columnId, event);
}

function moveTimingColumnResize(event) {
  return timingPane?.moveTimingColumnResize(event);
}

function endTimingColumnResize(event) {
  return timingPane?.endTimingColumnResize(event);
}

function normalizeProjectUiState(uiState = {}) {
  const requestedActiveTool = normalizeToolId(uiState.active_tool || DEFAULT_PROJECT_UI_STATE.active_tool);
  const normalizedActiveTool = VALID_TOOL_IDS.has(requestedActiveTool)
    ? requestedActiveTool
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
    timing_enabled: Boolean(uiState.timing_enabled ?? DEFAULT_PROJECT_UI_STATE.timing_enabled),
    review_show_markers: Boolean(uiState.review_show_markers ?? DEFAULT_PROJECT_UI_STATE.review_show_markers),
    review_show_pip: Boolean(uiState.review_show_pip ?? DEFAULT_PROJECT_UI_STATE.review_show_pip),
    metrics_expanded: Boolean(uiState.metrics_expanded ?? DEFAULT_PROJECT_UI_STATE.metrics_expanded),
    markers_expanded: Boolean(uiState.markers_expanded ?? DEFAULT_PROJECT_UI_STATE.markers_expanded),
    scoring_expanded: Boolean(uiState.scoring_expanded ?? DEFAULT_PROJECT_UI_STATE.scoring_expanded),
    layout_locked: Boolean(uiState.layout_locked ?? DEFAULT_PROJECT_UI_STATE.layout_locked),
    rail_width: clamp(Math.round(Number(uiState.rail_width ?? DEFAULT_PROJECT_UI_STATE.rail_width) || DEFAULT_PROJECT_UI_STATE.rail_width), 84, 104),
    inspector_width: Math.max(320, Math.round(Number(uiState.inspector_width ?? DEFAULT_PROJECT_UI_STATE.inspector_width) || DEFAULT_PROJECT_UI_STATE.inspector_width)),
    waveform_height: Math.max(112, Math.round(Number(uiState.waveform_height ?? DEFAULT_PROJECT_UI_STATE.waveform_height) || DEFAULT_PROJECT_UI_STATE.waveform_height)),
    scoring_edit_shot_ids: normalizedUiStringList(
      uiState.scoring_edit_shot_ids || Object.keys(normalizedUiBooleanMap(uiState.scoring_shot_expansion)).filter((shotId) => uiState.scoring_shot_expansion?.[shotId]),
    ),
    waveform_shot_amplitudes: normalizedUiFloatMap(uiState.waveform_shot_amplitudes, 0.25),
    timing_edit_shot_ids: normalizedUiStringList(uiState.timing_edit_shot_ids),
    timing_column_widths: resolvedTimingColumnWidths(normalizedUiFloatMap(uiState.timing_column_widths, 48)),
    review_text_box_expansion: normalizedUiBooleanMap(uiState.review_text_box_expansion),
    popup_bubble_expansion: normalizedUiBooleanMap(uiState.popup_bubble_expansion),
    popup_authoring_collapsed: Boolean(uiState.popup_authoring_collapsed ?? DEFAULT_PROJECT_UI_STATE.popup_authoring_collapsed),
    merge_source_expansion: normalizedUiBooleanMap(uiState.merge_source_expansion),
    shotml_section_expansion: normalizedUiBooleanMap(uiState.shotml_section_expansion),
  };
}

function mergeProjectUiState(remoteUiState = {}, localUiState = {}) {
  return normalizeProjectUiState({
    ...normalizeProjectUiState(remoteUiState),
    ...normalizeProjectUiState(localUiState),
  });
}

function projectUiStatePayloadKey(payload = {}) {
  return JSON.stringify(normalizeProjectUiState(payload));
}

function shouldApplyProjectUiStatePayload(payload) {
  return projectUiStatePayloadKey(payload) !== lastSubmittedProjectUiStatePayloadKey;
}

function readProjectUiStatePayload() {
  const root = $("cockpit-root");
  return normalizeProjectUiState({
    selected_shot_id: selectedShotId,
    timeline_zoom: waveformZoomX,
    timeline_offset_ms: Math.round(waveformOffsetMs),
    active_tool: activeTool === "project" && forcedProjectLandingPersistedTool
      ? forcedProjectLandingPersistedTool
      : activeTool,
    waveform_mode: waveformMode,
    waveform_expanded: Boolean(root?.classList.contains("waveform-expanded")),
    timing_expanded: Boolean(root?.classList.contains("timing-expanded")),
    timing_enabled: $("timing-enabled")?.checked ?? DEFAULT_PROJECT_UI_STATE.timing_enabled,
    review_show_markers: $("markers-enable")?.checked ?? $("show-markers")?.checked ?? DEFAULT_PROJECT_UI_STATE.review_show_markers,
    review_show_pip: $("show-pip")?.checked ?? DEFAULT_PROJECT_UI_STATE.review_show_pip,
    metrics_expanded: Boolean(root?.classList.contains("metrics-expanded")),
    markers_expanded: Boolean(root?.classList.contains("markers-expanded")),
    scoring_expanded: Boolean(root?.classList.contains("scoring-expanded")),
    layout_locked: layoutLocked,
    rail_width: Math.round(layoutSizes.railWidth),
    inspector_width: Math.round(layoutSizes.inspectorWidth),
    waveform_height: Math.round(layoutSizes.waveformHeight),
    scoring_edit_shot_ids: [...scoringRowEdits].filter(Boolean),
    waveform_shot_amplitudes: { ...waveformShotAmplitudeById },
    timing_edit_shot_ids: [...timingRowEdits].filter(Boolean),
    timing_column_widths: { ...resolvedTimingColumnWidths(timingColumnWidths) },
    review_text_box_expansion: Object.fromEntries(
      [...reviewTextBoxExpansion.entries()].filter(([boxId]) => Boolean(String(boxId || "").trim())),
    ),
    popup_bubble_expansion: Object.fromEntries(
      [...popupBubbleExpansion.entries()].filter(([bubbleId]) => Boolean(String(bubbleId || "").trim())),
    ),
    popup_authoring_collapsed: popupAuthoringCollapsed,
    merge_source_expansion: Object.fromEntries(
      [...mergeSourceExpansion.entries()].filter(([sourceId]) => Boolean(String(sourceId || "").trim())),
    ),
    shotml_section_expansion: Object.fromEntries(
      [...shotMLSectionExpansion.entries()].filter(([sectionId]) => Boolean(String(sectionId || "").trim())),
    ),
  });
}

function syncLocalProjectUiState(payload = readProjectUiStatePayload()) {
  const normalized = normalizeProjectUiState(payload);
  if (state?.project) state.project.ui_state = normalized;
  return normalized;
}

function applyProjectUiState(uiState = DEFAULT_PROJECT_UI_STATE) {
  const normalized = normalizeProjectUiState(uiState);
  setSelectedShotIdValue(normalized.selected_shot_id);
  waveformZoomX = normalized.timeline_zoom;
  waveformOffsetMs = normalized.timeline_offset_ms;
  layoutLocked = normalized.layout_locked;
  layoutSizes = {
    railWidth: normalized.rail_width,
    inspectorWidth: normalized.inspector_width,
    waveformHeight: normalized.waveform_height,
  };
  layoutSizePinned = {
    railWidth: layoutSizePinned.railWidth || normalized.rail_width !== DEFAULT_LAYOUT_SIZES.railWidth,
    inspectorWidth: layoutSizePinned.inspectorWidth || normalized.inspector_width !== DEFAULT_LAYOUT_SIZES.inspectorWidth,
    waveformHeight: layoutSizePinned.waveformHeight || normalized.waveform_height !== DEFAULT_LAYOUT_SIZES.waveformHeight,
  };
  maybeApplyRecommendedLayout();
  window.localStorage.setItem("splitshot.waveform.zoomX", String(waveformZoomX));
  window.localStorage.setItem("splitshot.waveform.offsetMs", String(Math.round(waveformOffsetMs)));
  window.localStorage.setItem("splitshot.layoutLocked", String(layoutLocked));
  window.localStorage.setItem("splitshot.layout.railWidth", String(layoutSizes.railWidth));
  window.localStorage.setItem("splitshot.layout.inspectorWidth", String(layoutSizes.inspectorWidth));
  window.localStorage.setItem("splitshot.layout.waveformHeight", String(layoutSizes.waveformHeight));
  waveformShotAmplitudeById = { ...normalized.waveform_shot_amplitudes };
  scoringRowEdits = new Set(normalized.scoring_edit_shot_ids);
  reviewTextBoxExpansion = new Map(Object.entries(normalized.review_text_box_expansion));
  popupBubbleExpansion = new Map(Object.entries(normalized.popup_bubble_expansion));
  popupAuthoringCollapsed = Boolean(normalized.popup_authoring_collapsed);
  mergeSourceExpansion = new Map(Object.entries(normalized.merge_source_expansion));
  shotMLSectionExpansion = new Map(Object.entries(normalized.shotml_section_expansion));
  timingRowEdits = new Set(normalized.timing_edit_shot_ids);
  timingAdjustmentDrafts = new Map(
    [...timingAdjustmentDrafts.entries()].filter(([shotId]) => timingRowEdits.has(shotId)),
  );
  timingColumnWidths = resolvedTimingColumnWidths(normalized.timing_column_widths);
  setActiveTool(normalized.active_tool, { collapseExpandedLayout: false, persistUiState: false });
  setWaveformMode(normalized.waveform_mode, { persistUiState: false });
  setWaveformExpanded(normalized.waveform_expanded, { persistUiState: false });
  setTimingExpanded(normalized.timing_expanded, { persistUiState: false });
  syncControlChecked($("timing-enabled"), normalized.timing_enabled);
  syncControlChecked($("markers-enable"), normalized.review_show_markers);
  syncControlChecked($("show-markers"), normalized.review_show_markers);
  syncControlChecked($("show-pip"), normalized.review_show_pip);
  setMetricsExpanded(normalized.metrics_expanded, { persistUiState: false });
  setMarkersExpanded(normalized.markers_expanded, { persistUiState: false });
  setScoringWorkbenchExpanded(normalized.scoring_expanded, { persistUiState: false });
  if (state?.project) state.project.ui_state = normalized;
  return normalized;
}

function normalizedCoordinateValue(value) {
  if (value === null || value === undefined || value === "") return null;
  const numeric = Number(value);
  return Number.isFinite(numeric) ? clamp(numeric, 0, 1) : null;
}

function formattedCoordinateValue(value, fallback = 0.5) {
  const numeric = normalizedCoordinateValue(value);
  return (numeric ?? fallback).toFixed(4);
}

function currentPipSizePercent(source = null, fallback = 35) {
  return mergePane?.currentPipSizePercent(source, fallback) ?? fallback;
}

function sourceIdentifier(source, fallback = "") {
  return mergePane?.sourceIdentifier(source, fallback) ?? fallback;
}

function currentSourceSyncOffsetMs(source = null) {
  return mergePane?.currentSourceSyncOffsetMs(source) ?? 0;
}

function currentSourceOpacity(source = null) {
  return mergePane?.currentSourceOpacity(source) ?? 1;
}

function formatSyncOffsetLabel(offsetMs) {
  return mergePane?.formatSyncOffsetLabel(offsetMs) ?? `Sync ${Math.round(Number(offsetMs) || 0)} ms`;
}

function mergePreviewTargetTime(primaryTime, source = null) {
  return mergePane?.mergePreviewTargetTime(primaryTime, source) ?? primaryTime;
}

function mergeSourceById(sourceId) {
  return mergePane?.mergeSourceById(sourceId) ?? null;
}

const MERGE_SOURCE_PREVIEW_PLACEMENT_MODES = new Set([
  "auto",
  "base",
  "side_by_side",
  "above_below",
  "pip",
  "full_screen_portrait",
  "dual_center_hud",
  "dual_top_hud",
]);
const MERGE_SOURCE_PREVIEW_PLACEMENT_SLOTS = new Set([
  "auto",
  "left",
  "right",
  "top",
  "bottom",
  "center",
  "overlay",
]);

function mergeSourcePreviewDefaultMode() {
  return "side_by_side";
}

function mergeSourcePreviewSlotValues(mode = mergeSourcePreviewDefaultMode()) {
  if (["side_by_side", "dual_center_hud", "dual_top_hud"].includes(mode)) return ["left", "right"];
  if (mode === "above_below") return ["top", "bottom"];
  if (mode === "pip") return ["overlay", "left", "right", "top", "bottom", "center"];
  return ["center"];
}

function mergeSourcePreviewAutoSlot(mode = mergeSourcePreviewDefaultMode()) {
  if (mode === "above_below") return "bottom";
  if (["side_by_side", "dual_center_hud", "dual_top_hud"].includes(mode)) return "right";
  if (mode === "pip") return "overlay";
  return "center";
}

function resolvedMergeSourcePreviewPlacement(source = null) {
  const placement = source?.placement && typeof source.placement === "object" ? source.placement : {};
  const requestedMode = String(placement.mode ?? "").trim().toLowerCase();
  const normalizedMode = MERGE_SOURCE_PREVIEW_PLACEMENT_MODES.has(requestedMode) ? requestedMode : "auto";
  const mode = normalizedMode === "auto" ? mergeSourcePreviewDefaultMode() : normalizedMode;
  const allowedSlots = mergeSourcePreviewSlotValues(mode);
  const requestedSlot = String(placement.slot ?? "").trim().toLowerCase();
  const normalizedSlot = MERGE_SOURCE_PREVIEW_PLACEMENT_SLOTS.has(requestedSlot) ? requestedSlot : "auto";
  const slot = normalizedSlot === "auto"
    ? mergeSourcePreviewAutoSlot(mode)
    : (allowedSlots.includes(normalizedSlot) ? normalizedSlot : mergeSourcePreviewAutoSlot(mode));
  const requestedTargetSourceId = String(placement.target_source_id ?? "").trim();
  const targetSourceId = requestedTargetSourceId && mergeSourceById(requestedTargetSourceId)
    ? requestedTargetSourceId
    : null;
  const requestedTargetKind = String(placement.target_kind ?? "").trim().toLowerCase();
  const targetKind = ["pip", "full_screen_portrait"].includes(mode)
    && requestedTargetKind === "merge_source"
    && targetSourceId
    ? "merge_source"
    : "primary_video";
  return {
    mode,
    slot,
    target_kind: targetKind,
    target_source_id: targetKind === "merge_source" ? targetSourceId : null,
  };
}

function mergeSourceUsesFreeformPreviewDrag(source = null) {
  const placement = resolvedMergeSourcePreviewPlacement(source);
  return placement.mode === "pip" && placement.slot === "overlay";
}

function mergePreviewItemElement(sourceId = "") {
  const layer = $("merge-preview-layer");
  if (!(layer instanceof HTMLElement) || !sourceId) return null;
  return [...layer.querySelectorAll(".merge-preview-item[data-source-id]")]
    .find((item) => item instanceof HTMLElement && item.dataset.sourceId === sourceId) || null;
}

function mergePreviewTargetFrameRect(source = null, stage = $("video-stage")) {
  const primaryVideo = $("primary-video");
  const stageRect = stage instanceof HTMLElement
    ? (previewFrameClientRect(primaryVideo, stage) || stage.getBoundingClientRect())
    : null;
  if (!source || !stageRect) return stageRect;
  const placement = resolvedMergeSourcePreviewPlacement(source);
  if (placement.target_kind !== "merge_source" || !placement.target_source_id) return stageRect;
  const targetItem = mergePreviewItemElement(placement.target_source_id);
  if (!(targetItem instanceof HTMLElement)) return stageRect;
  return targetItem.getBoundingClientRect();
}

function isMergeSourceExpanded(sourceId) {
  return mergePane?.isMergeSourceExpanded(sourceId) ?? false;
}

function setMergeSourceExpanded(sourceId, expanded) {
  return mergePane?.setMergeSourceExpanded(sourceId, expanded);
}

function syncMergeSourceControls(...args) {
  return mergePane?.syncMergeSourceControls(...args);
}

function updateLocalMergeSourcePosition(...args) {
  return mergePane?.updateLocalMergeSourcePosition(...args);
}

function updateLocalMergeSourceSyncOffset(...args) {
  return mergePane?.updateLocalMergeSourceSyncOffset(...args);
}

function mergeSourcePositionPayload(...args) {
  return mergePane?.mergeSourcePositionPayload(...args) ?? null;
}

function syncOverlayFontSizePreset() {
  const badgeSize = $("badge-size").value;
  const fontSize = BADGE_FONT_SIZES[badgeSize] || BADGE_FONT_SIZES.M;
  $("overlay-font-size").value = String(fontSize);
}

function ensureShotQuadrantDefaults() {
  if (!usesCustomQuadrant($("shot-quadrant").value)) return;
  const seededCoordinates = resolveRenderedOverlayBadgeCoordinates("shots") || { x: 0.5, y: 0.5 };
  if (!$("overlay-custom-x").value) syncControlValue($("overlay-custom-x"), seededCoordinates.x);
  if (!$("overlay-custom-y").value) syncControlValue($("overlay-custom-y"), seededCoordinates.y);
}

function createOverlayTextBoxId() {
  return reviewPane?.createOverlayTextBoxId();
}

function overlayTextBoxAutoSize(box) {
  return reviewPane?.overlayTextBoxAutoSize(box);
}

function resolvedOverlayTextBoxSize(box) {
  return reviewPane?.resolvedOverlayTextBoxSize(box);
}

function syncOverlayTextBoxSizeControls(boxId) {
  return reviewPane?.syncOverlayTextBoxSizeControls(boxId);
}

function normalizeOverlayTextBox(box = {}, index = 0) {
  return reviewPane?.normalizeOverlayTextBox(box, index);
}

function overlayTextBoxes() {
  return reviewPane?.overlayTextBoxes() || [];
}

function preferredLegacyTextBox(boxes) {
  return reviewPane?.preferredLegacyTextBox(boxes) || null;
}

function syncLegacyOverlayBoxState(overlay, boxes = overlayTextBoxes()) {
  return reviewPane?.syncLegacyOverlayBoxState(overlay, boxes);
}

function setLocalOverlayTextBoxes(boxes) {
  return reviewPane?.setLocalOverlayTextBoxes(boxes);
}

function buildOverlayTextBox(source = "manual") {
  return reviewPane?.buildOverlayTextBox(source);
}

function overlayTextBoxLabel(box, index) {
  return reviewPane?.overlayTextBoxLabel(box, index);
}

function applyOverlayTextBoxUpdate(boxes, { commit = false, rerender = false } = {}) {
  return reviewPane?.applyOverlayTextBoxUpdate(boxes, { commit, rerender });
}

function updateOverlayTextBox(boxId, updater, options = {}) {
  return reviewPane?.updateOverlayTextBox(boxId, updater, options);
}

function setOverlayTextBoxField(boxId, field, rawValue, options = {}) {
  return reviewPane?.setOverlayTextBoxField(boxId, field, rawValue, options);
}

function addOverlayTextBox(source = "manual") {
  return reviewPane?.addOverlayTextBox(source);
}

function duplicateOverlayTextBox(boxId) {
  return reviewPane?.duplicateOverlayTextBox(boxId);
}

function removeOverlayTextBox(boxId) {
  return reviewPane?.removeOverlayTextBox(boxId);
}

function syncOverlayPreviewStateFromControls() {
  return overlayPane?.syncOverlayPreviewStateFromControls();
}

function previewOverlayControlChanges() {
  return overlayPane?.previewOverlayControlChanges();
}

function commitOverlayControlChanges() {
  return overlayPane?.commitOverlayControlChanges();
}

function clearOverlayColorCommitTimer() {
  return overlayPane?.clearOverlayColorCommitTimer();
}

function scheduleOverlayColorCommit() {
  return overlayPane?.scheduleOverlayColorCommit();
}

function flushOverlayColorCommit() {
  return overlayPane?.flushOverlayColorCommit();
}

function bindOverlayColorInput(control) {
  return overlayPane?.bindOverlayColorInput(control);
}

function syncMergePreviewStateFromControls() {
  return mergePane?.syncMergePreviewStateFromControls();
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
  return overlayPane?.syncOverlayCoordinateControlState();
}

function previewFrameRectForOverlayPlacement() {
  return overlayPane?.previewFrameRectForOverlayPlacement() || null;
}

function overlayBadgeElement(kind) {
  return overlayPane?.overlayBadgeElement(kind) || null;
}

function overlayBadgeCoordinateFallback(kind) {
  return overlayPane?.overlayBadgeCoordinateFallback(kind) || null;
}

function resolveRenderedOverlayBadgeCoordinates(kind) {
  return overlayPane?.resolveRenderedOverlayBadgeCoordinates(kind) || null;
}

function resetOverlayPlacementBaseline(controlId) {
  return overlayPane?.resetOverlayPlacementBaseline(controlId);
}

function syncOverlayBadgeCoordinateControlValues() {
  return overlayPane?.syncOverlayBadgeCoordinateControlValues();
}

function overlayBadgeLockedToStack(kind, overlay = state?.project?.overlay) {
  return overlayPane?.overlayBadgeLockedToStack(kind, overlay) || false;
}

function syncOverlayBubbleLockControlState() {
  return overlayPane?.syncOverlayBubbleLockControlState();
}

function overlayTextBoxDisplayText(box) {
  return reviewPane?.overlayTextBoxDisplayText(box) || "";
}

function overlayTextBoxHint(box) {
  return reviewPane?.overlayTextBoxHint(box) || "";
}

function isReviewTextBoxExpanded(boxId) {
  return reviewPane?.isReviewTextBoxExpanded(boxId) || false;
}

function setReviewTextBoxExpanded(boxId, expanded) {
  return reviewPane?.setReviewTextBoxExpanded(boxId, expanded);
}

function isShotMLSectionExpanded(sectionId) {
  return shotmlPane?.isShotMLSectionExpanded(sectionId) || false;
}

function setShotMLSectionExpanded(sectionId, expanded) {
  return shotmlPane?.setShotMLSectionExpanded(sectionId, expanded);
}

function ensureSectionToggle(section, expanded, onToggle) {
  const header = section?.querySelector(":scope > .section-header");
  if (!(header instanceof HTMLElement)) return;
  header.classList.add("section-header-with-toggle");
  let actions = header.querySelector(":scope > .section-header-actions");
  if (!(actions instanceof HTMLElement)) {
    actions = document.createElement("div");
    actions.className = "section-header-actions";
    while (header.children.length > 1) {
      actions.appendChild(header.lastElementChild);
    }
    header.appendChild(actions);
  }
  let toggle = actions.querySelector(":scope > [data-section-toggle]");
  if (!(toggle instanceof HTMLButtonElement)) {
    toggle = document.createElement("button");
    toggle.type = "button";
    toggle.dataset.sectionToggle = "true";
    toggle.className = "scoring-shot-toggle";
    actions.prepend(toggle);
  }
  toggle.textContent = expanded ? "v" : ">";
  toggle.title = expanded ? "Hide section" : "Show section";
  toggle.setAttribute("aria-label", expanded ? "Hide section" : "Show section");
  toggle.onclick = (event) => {
    event.preventDefault();
    event.stopPropagation();
    preserveElementViewportAnchor(section, () => onToggle(event));
  };
}

function renderCollapsibleInspectorSections() {
  document.querySelectorAll("[data-shotml-section]").forEach((section) => {
    if (!(section instanceof HTMLElement)) return;
    const sectionId = section.dataset.shotmlSection || "";
    const expanded = isShotMLSectionExpanded(sectionId);
    section.classList.toggle("collapsed", !expanded);
    ensureSectionToggle(section, expanded, () => {
      setShotMLSectionExpanded(sectionId, !expanded);
      renderCollapsibleInspectorSections();
    });
  });

  const pipDefaults = document.querySelector('[data-inspector-section="pip-defaults"]');
  if (pipDefaults instanceof HTMLElement) {
    const sectionId = PIP_DEFAULTS_SECTION_ID;
    const expanded = isMergeSourceExpanded(sectionId);
    pipDefaults.classList.toggle("collapsed", !expanded);
    ensureSectionToggle(pipDefaults, expanded, () => {
      setMergeSourceExpanded(sectionId, !expanded);
      renderCollapsibleInspectorSections();
    });
  }
}

function isSettingsSectionExpanded(sectionId) {
  if (settingsPane) return settingsPane.isSettingsSectionExpanded(sectionId);
  if (settingsSectionExpansion.has(sectionId)) return Boolean(settingsSectionExpansion.get(sectionId));
  return false;
}

function setSettingsSectionExpanded(sectionId, expanded) {
  if (settingsPane) return settingsPane.setSettingsSectionExpanded(sectionId, expanded);
  if (!sectionId) return;
  settingsSectionExpansion.set(sectionId, Boolean(expanded));
}

function renderSettingsSections() {
  if (settingsPane) return settingsPane.renderSettingsSections();
  document.querySelectorAll("[data-settings-section]").forEach((section) => {
    if (!(section instanceof HTMLElement)) return;
    const sectionId = section.dataset.settingsSection || "";
    const expanded = isSettingsSectionExpanded(sectionId);
    section.classList.toggle("collapsed", !expanded);
    ensureSectionToggle(section, expanded, () => {
      setSettingsSectionExpanded(sectionId, !expanded);
      renderSettingsSections();
    });
  });
}

function buildTextBoxCard(box, index) {
  return reviewPane?.buildTextBoxCard(box, index);
}

function renderTextBoxEditors() {
  return reviewPane?.renderTextBoxEditors();
}

function createPopupBubbleId() {
  if (window.crypto?.randomUUID) return window.crypto.randomUUID().replace(/-/g, "");
  return `popup_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 10)}`;
}

const POPUP_BUBBLE_ANCHOR_MODES = new Set(["time", "shot"]);
const POPUP_KEYFRAME_EASINGS = Object.freeze([
  ["linear", "Linear"],
  ["hold", "Hold"],
  ["ease_in", "Ease In"],
  ["ease_out", "Ease Out"],
  ["ease_in_out", "Ease In/Out"],
]);
const VALID_POPUP_KEYFRAME_EASINGS = new Set(POPUP_KEYFRAME_EASINGS.map(([value]) => value));
const POPUP_BUBBLE_QUADRANT_POINTS = Object.freeze({
  top_left: { x: 0.125, y: 0.125 },
  top_middle: { x: 0.5, y: 0.125 },
  top_right: { x: 0.875, y: 0.125 },
  middle_left: { x: 0.125, y: 0.5 },
  middle_middle: { x: 0.5, y: 0.5 },
  middle_right: { x: 0.875, y: 0.5 },
  bottom_left: { x: 0.125, y: 0.875 },
  bottom_middle: { x: 0.5, y: 0.875 },
  bottom_right: { x: 0.875, y: 0.875 },
  custom: { x: 0.5, y: 0.5 },
});

function normalizePopupAnchorMode(value, shotId = null) {
  const normalized = String(value || "").trim();
  if (POPUP_BUBBLE_ANCHOR_MODES.has(normalized)) return normalized;
  return shotId ? "shot" : "time";
}

function normalizePopupQuadrant(value, xValue = null, yValue = null) {
  const normalized = String(value || "").trim();
  if (normalized in POPUP_BUBBLE_QUADRANT_POINTS) return normalized;
  if (xValue !== null || yValue !== null) return "custom";
  return "middle_middle";
}

function normalizePopupMotionPoint(point) {
  const offsetMs = Math.max(0, Math.round(Number(point?.offset_ms ?? point?.time_ms ?? 0) || 0));
  return {
    offset_ms: offsetMs,
    x: normalizedCoordinateValue(point?.x) ?? 0.5,
    y: normalizedCoordinateValue(point?.y) ?? 0.5,
    easing: VALID_POPUP_KEYFRAME_EASINGS.has(String(point?.easing || "").trim())
      ? String(point.easing).trim()
      : "linear",
  };
}

function normalizePopupMotionPath(path) {
  if (!Array.isArray(path)) return [];
  const normalized = path.map((point) => normalizePopupMotionPoint(point));
  normalized.sort((left, right) => left.offset_ms - right.offset_ms);
  const deduped = [];
  normalized.forEach((point) => {
    if (deduped.length > 0 && deduped[deduped.length - 1].offset_ms === point.offset_ms) {
      deduped[deduped.length - 1] = point;
      return;
    }
    deduped.push(point);
  });
  return deduped;
}

function normalizePopupMotionMode(value, followMotion = false, motionPath = []) {
  const normalized = String(value || "").trim().toLowerCase();
  if (!Boolean(followMotion)) return "fixed";
  if (["guided", "manual", "auto"].includes(normalized)) return normalized;
  return "guided";
}

function popupMotionUiModeFromValue(value, followMotion = false, motionPath = []) {
  const mode = normalizePopupMotionMode(value, followMotion, motionPath);
  return mode === "fixed" ? "fixed" : "guided";
}

function popupTemplateUsesShotSplitDuration(template = currentPopupTemplate()) {
  return Boolean(template?.use_shot_split_duration ?? false);
}

function popupShotDurationLimitMs(shotId, shotNumber = null, absoluteTimeMs = null) {
  if (!shotId) return null;
  const shot = shotById(shotId);
  const resolvedShotNumber = shotNumber ?? (() => {
    const shotIndex = orderedShotsByTime().findIndex((item) => item.id === shotId);
    return shotIndex >= 0 ? shotIndex + 1 : null;
  })();
  const resolvedAbsoluteTimeMs = numericMs(absoluteTimeMs) ?? numericMs(shot?.time_ms);
  const splitMs = numericMs(resolvedSplitMsForShot(shotId, resolvedShotNumber, resolvedAbsoluteTimeMs));
  return splitMs === null ? null : Math.max(1, Math.round(splitMs));
}

function popupShotDefaultDurationMs(shotId, shotNumber = null, absoluteTimeMs = null, fallbackMs = 1000) {
  const fallbackDurationMs = Math.max(1, Math.round(Number(fallbackMs ?? 1000) || 1000));
  const splitLimitMs = popupShotDurationLimitMs(shotId, shotNumber, absoluteTimeMs);
  if (splitLimitMs !== null) return splitLimitMs;
  const averageSplitMs = numericMs(state?.metrics?.average_split_ms);
  if (averageSplitMs !== null) return Math.max(1, Math.round(averageSplitMs));
  return fallbackDurationMs;
}

function clampPopupDurationForShot(durationMs, shotId, shotNumber = null, absoluteTimeMs = null) {
  const normalizedDurationMs = Math.max(1, Math.round(Number(durationMs ?? 1000) || 1000));
  const splitLimitMs = popupShotDurationLimitMs(shotId, shotNumber, absoluteTimeMs);
  return splitLimitMs === null ? normalizedDurationMs : clamp(normalizedDurationMs, 1, splitLimitMs);
}

function popupDefaultDurationMsForShot(shot, template = currentPopupTemplate()) {
  const fallbackDurationMs = Math.max(1, Math.round(Number(template?.duration_ms ?? 1000) || 1000));
  const shotId = shot?.id || null;
  if (!shotId) return fallbackDurationMs;
  if (popupTemplateUsesShotSplitDuration(template)) {
    return popupShotDefaultDurationMs(shotId, null, shot?.time_ms ?? null, fallbackDurationMs);
  }
  return clampPopupDurationForShot(fallbackDurationMs, shotId, null, shot?.time_ms ?? null);
}

function popupDurationLimitMsForBubble(bubble) {
  if (!bubble || bubble.anchor_mode !== "shot" || !bubble.shot_id) return null;
  return popupShotDurationLimitMs(bubble.shot_id, null, bubble.time_ms);
}

function stagePopupImagePath(path) {
  const normalizedPath = String(path || "").trim();
  if (!normalizedPath) return "";
  if (normalizedPath.replace(/\\/g, "/").split("/").includes("Markers")) return normalizedPath;
  const projectPath = String(state?.project?.path || "").trim();
  const assetName = fileName(normalizedPath);
  if (!projectPath || !assetName) return normalizedPath;
  const separator = projectPath.includes("\\") ? "\\" : "/";
  return `${projectPath.replace(/[\\/]+$/, "")}${separator}Markers${separator}${assetName}`;
}

function normalizePopupBubble(bubble = {}) {
  const xValue = normalizedCoordinateValue(bubble.x);
  const yValue = normalizedCoordinateValue(bubble.y);
  const shotId = bubble.shot_id === undefined || bubble.shot_id === null || bubble.shot_id === ""
    ? null
    : String(bubble.shot_id);
  const anchorMode = normalizePopupAnchorMode(bubble.anchor_mode, shotId);
  const timeMs = Math.max(0, Math.round(Number(bubble.time_ms ?? 0) || 0));
  const rawDurationMs = Math.max(1, Math.round(Number(bubble.duration_ms ?? 1000) || 1000));
  const durationMs = rawDurationMs;
  const motionPath = normalizePopupMotionPath(bubble.motion_path);
  const boundedMotionPath = motionPath.length === 0
    ? motionPath
    : normalizePopupMotionPath(motionPath.map((point) => ({
      ...point,
      offset_ms: Math.max(1, Math.min(durationMs, point.offset_ms)),
    })));
  const followMotion = Boolean(bubble.follow_motion ?? boundedMotionPath.length > 0);
  const motionMode = normalizePopupMotionMode(bubble.motion_mode, followMotion, boundedMotionPath);
  return {
    id: String(bubble.id || createPopupBubbleId()),
    enabled: Boolean(bubble.enabled ?? true),
    name: String(bubble.name || "").slice(0, 80),
    text: String(bubble.text || "").slice(0, 500),
    anchor_mode: anchorMode,
    shot_id: anchorMode === "shot" && shotId ? shotId : null,
    time_ms: timeMs,
    duration_ms: durationMs,
    quadrant: normalizePopupQuadrant(bubble.quadrant, xValue, yValue),
    x: xValue === null ? 0.5 : xValue,
    y: yValue === null ? 0.5 : yValue,
    follow_motion: followMotion,
    motion_mode: motionMode,
    motion_path: boundedMotionPath,
    background_color: String(bubble.background_color || "#000000"),
    text_color: String(bubble.text_color || "#ffffff"),
    opacity: clamp(Number(bubble.opacity ?? 0.9) || 0.9, 0, 1),
    width: Math.max(0, Math.round(Number(bubble.width ?? 0) || 0)),
    height: Math.max(0, Math.round(Number(bubble.height ?? 0) || 0)),
    content_type: ["text", "image", "text_image"].includes(String(bubble.content_type || "text")) ? String(bubble.content_type || "text") : "text",
    image_path: String(bubble.image_path || ""),
    image_scale_mode: ["contain", "cover"].includes(String(bubble.image_scale_mode || "contain")) ? String(bubble.image_scale_mode || "contain") : "contain",
  };
}

function normalizePopupTemplate(template = {}) {
  const followMotion = Boolean(template.follow_motion ?? false);
  return {
    enabled: Boolean(template.enabled ?? true),
    content_type: ["text", "image", "text_image"].includes(String(template.content_type || "text")) ? String(template.content_type || "text") : "text",
    text_source: ["score", "shot_label", "custom"].includes(String(template.text_source || "score")) ? String(template.text_source || "score") : "score",
    duration_ms: Math.max(1, Math.round(Number(template.duration_ms ?? 1000) || 1000)),
    use_shot_split_duration: Boolean(template.use_shot_split_duration ?? false),
    quadrant: normalizePopupQuadrant(template.quadrant),
    width: Math.max(0, Math.round(Number(template.width ?? 0) || 0)),
    height: Math.max(0, Math.round(Number(template.height ?? 0) || 0)),
    follow_motion: followMotion,
    motion_mode: normalizePopupMotionMode(template.motion_mode, followMotion),
    background_color: String(template.background_color || "#000000"),
    text_color: String(template.text_color || "#ffffff"),
    opacity: Math.max(0, Math.min(1, template.opacity === undefined || template.opacity === null || template.opacity === "" ? 0.9 : Number(template.opacity))),
  };
}

function currentPopupTemplate() {
  return normalizePopupTemplate(state?.project?.popup_template || state?.settings?.marker_template || {});
}

function popupTemplateTextForShot(shot) {
  const template = currentPopupTemplate();
  if (!shot) return defaultScoreLetter();
  if (template.text_source === "shot_label") {
    const shotIndex = orderedShotsByTime().findIndex((item) => item.id === shot.id);
    return shotIndex >= 0 ? `Shot ${shotIndex + 1}` : "Shot";
  }
  if (template.text_source === "custom") return "";
  return popupTextForShotId(shot.id) || defaultScoreLetter();
}

function popupBubbles() {
  const bubbles = Array.isArray(state?.project?.popups) ? state.project.popups : [];
  return bubbles.map((bubble) => normalizePopupBubble(bubble));
}

function popupBubbleMotionPath(bubble) {
  return normalizePopupMotionPath(bubble?.motion_path || []);
}

function popupBubbleMotionUiMode(bubble = null) {
  return popupMotionUiModeFromValue(bubble?.motion_mode, bubble?.follow_motion, popupBubbleMotionPath(bubble));
}

function popupMotionGeneratedOffsetsForBubbleId(bubbleId) {
  return popupGeneratedMotionOffsetsByBubbleId.get(bubbleId) || new Set();
}

function popupMotionOffsetIsGenerated(bubbleId, offsetMs) {
  const normalizedOffset = Math.max(0, Math.round(Number(offsetMs) || 0));
  return popupMotionGeneratedOffsetsForBubbleId(bubbleId).has(normalizedOffset);
}

function setPopupMotionGeneratedOffsets(bubbleId, offsets = []) {
  if (!bubbleId) return;
  const nextOffsets = [...new Set((offsets || [])
    .map((value) => Math.max(0, Math.round(Number(value) || 0)))
    .filter((value) => value > 0))];
  if (nextOffsets.length === 0) {
    popupGeneratedMotionOffsetsByBubbleId.delete(bubbleId);
    return;
  }
  popupGeneratedMotionOffsetsByBubbleId.set(bubbleId, new Set(nextOffsets));
}

function copyPopupMotionUiState(sourceBubbleId, targetBubbleIds = []) {
  const generatedOffsets = [...popupMotionGeneratedOffsetsForBubbleId(sourceBubbleId)];
  const summary = popupMotionGenerationSummaryByBubbleId.get(sourceBubbleId) || "";
  targetBubbleIds.forEach((bubbleId) => {
    if (!bubbleId) return;
    setPopupMotionGeneratedOffsets(bubbleId, generatedOffsets);
    if (summary) popupMotionGenerationSummaryByBubbleId.set(bubbleId, summary);
    else popupMotionGenerationSummaryByBubbleId.delete(bubbleId);
  });
}

function prunePopupMotionUiState(bubbles = popupBubbles()) {
  const validBubbleIds = new Set(bubbles.map((bubble) => bubble.id));
  [popupGeneratedMotionOffsetsByBubbleId, popupMotionGenerationSummaryByBubbleId].forEach((map) => {
    [...map.keys()].forEach((bubbleId) => {
      if (!validBubbleIds.has(bubbleId)) map.delete(bubbleId);
    });
  });
  bubbles.forEach((bubble) => {
    const existing = popupGeneratedMotionOffsetsByBubbleId.get(bubble.id);
    if (!existing) return;
    const validOffsets = new Set(
      popupBubbleMotionPath(bubble)
        .map((point) => point.offset_ms)
        .filter((offsetMs) => offsetMs > 0 && offsetMs < Math.max(1, bubble.duration_ms)),
    );
    const nextOffsets = [...existing].filter((offsetMs) => validOffsets.has(offsetMs));
    if (nextOffsets.length === 0) popupGeneratedMotionOffsetsByBubbleId.delete(bubble.id);
    else popupGeneratedMotionOffsetsByBubbleId.set(bubble.id, new Set(nextOffsets));
  });
}

function popupTemplateMotionUiMode(template = currentPopupTemplate()) {
  return popupMotionUiModeFromValue(template?.motion_mode, template?.follow_motion);
}

function popupMotionModeValueForUiMode(uiMode) {
  return uiMode === "fixed" ? "fixed" : "guided";
}

function popupKeyframeEasing(easing) {
  const normalized = String(easing || "").trim();
  return VALID_POPUP_KEYFRAME_EASINGS.has(normalized) ? normalized : "linear";
}

function popupKeyframeRatio(easing, ratio) {
  const clampedRatio = clampNumber(Number(ratio) || 0, 0, 1);
  if (easing === "hold") return clampedRatio < 1 ? 0 : 1;
  if (easing === "ease_in") return clampedRatio * clampedRatio;
  if (easing === "ease_out") return 1 - ((1 - clampedRatio) * (1 - clampedRatio));
  if (easing === "ease_in_out") {
    if (clampedRatio <= 0.5) return 2 * clampedRatio * clampedRatio;
    return 1 - (((-2 * clampedRatio) + 2) ** 2) / 2;
  }
  return clampedRatio;
}

function scaledPopupMotionPathOffsets(motionPath, previousDurationMs, nextDurationMs) {
  const oldDuration = Math.max(1, Math.round(Number(previousDurationMs) || 1));
  const newDuration = Math.max(1, Math.round(Number(nextDurationMs) || 1));
  return normalizePopupMotionPath(motionPath.map((point) => ({
    ...point,
    offset_ms: Math.max(1, Math.min(newDuration, Math.round((point.offset_ms / oldDuration) * newDuration))),
  })));
}

function popupBubbleMotionPointAtOffset(motionPath, elapsedMs, basePoint) {
  if (motionPath.length === 0) return basePoint;
  let previousPoint = { offset_ms: 0, x: basePoint.x, y: basePoint.y, easing: "linear" };
  for (const point of motionPath) {
    if (elapsedMs <= point.offset_ms) {
      if (point.offset_ms <= previousPoint.offset_ms) {
        return { x: point.x, y: point.y };
      }
      const ratio = (elapsedMs - previousPoint.offset_ms) / (point.offset_ms - previousPoint.offset_ms);
      const easedRatio = popupKeyframeRatio(point.easing, ratio);
      return {
        x: clamp(previousPoint.x + ((point.x - previousPoint.x) * easedRatio), 0, 1),
        y: clamp(previousPoint.y + ((point.y - previousPoint.y) * easedRatio), 0, 1),
      };
    }
    previousPoint = point;
  }
  return { x: previousPoint.x, y: previousPoint.y };
}

function popupBubblePoint(bubble, positionMs = null) {
  if (!bubble) return { x: 0.5, y: 0.5 };
  const basePoint = bubble.quadrant !== CUSTOM_QUADRANT_VALUE
    ? (POPUP_BUBBLE_QUADRANT_POINTS[bubble.quadrant] || POPUP_BUBBLE_QUADRANT_POINTS.middle_middle)
    : {
        x: normalizedCoordinateValue(bubble.x) ?? 0.5,
        y: normalizedCoordinateValue(bubble.y) ?? 0.5,
      };
  if (!bubble.follow_motion || positionMs === null) return basePoint;
  const motionPath = popupBubbleMotionPath(bubble);
  if (motionPath.length === 0) return basePoint;
  const popupTimeMs = popupBubbleEffectiveTimeMs(bubble);
  const elapsedMs = Math.max(0, Math.round(Number(positionMs) || 0) - popupTimeMs);
  let previousPoint = { offset_ms: 0, x: basePoint.x, y: basePoint.y, easing: "linear" };
  for (const point of motionPath) {
    if (elapsedMs <= point.offset_ms) {
      if (point.offset_ms <= previousPoint.offset_ms) {
        return { x: point.x, y: point.y };
      }
      const ratio = (elapsedMs - previousPoint.offset_ms) / (point.offset_ms - previousPoint.offset_ms);
      const easedRatio = popupKeyframeRatio(point.easing, ratio);
      return {
        x: clamp(previousPoint.x + ((point.x - previousPoint.x) * easedRatio), 0, 1),
        y: clamp(previousPoint.y + ((point.y - previousPoint.y) * easedRatio), 0, 1),
      };
    }
    previousPoint = point;
  }
  return { x: previousPoint.x, y: previousPoint.y };
}

function updatePopupBubbleMotionPoint(bubble, offsetMs, x, y) {
  const normalizedOffset = Math.max(0, Math.round(Number(offsetMs) || 0));
  if (!bubble.follow_motion || normalizedOffset <= 0) {
    return normalizePopupBubble({ ...bubble, quadrant: CUSTOM_QUADRANT_VALUE, x, y });
  }
  const motionPath = popupBubbleMotionPath(bubble).filter((point) => point.offset_ms !== normalizedOffset);
  const existingPoint = popupBubbleMotionPath(bubble).find((point) => point.offset_ms === normalizedOffset);
  motionPath.push({ offset_ms: normalizedOffset, x, y, easing: existingPoint?.easing || "linear" });
  return normalizePopupBubble({
    ...bubble,
    follow_motion: true,
    motion_path: motionPath,
  });
}

function popupBubbleAutoSize(bubble) {
  const text = popupBubbleResolvedText(bubble).trim();
  const hasImage = ["image", "text_image"].includes(String(bubble?.content_type || "")) && Boolean(bubble?.image_path);
  if (hasImage) {
    const imageHeight = 124;
    const measurement = text ? measureOverlayBadgeContent(text) : { width: 0, height: 0 };
    return {
      width: Math.max(220, Math.ceil(measurement.width + (OVERLAY_BADGE_PADDING_X_PX * 2))),
      height: text
        ? Math.max(148, Math.ceil(imageHeight + measurement.height + 14))
        : imageHeight,
    };
  }
  if (!text) return { width: 0, height: 0 };
  const measurement = measureOverlayBadgeContent(text);
  return {
    width: Math.ceil(measurement.width + (OVERLAY_BADGE_PADDING_X_PX * 2)),
    height: Math.ceil(measurement.height + (OVERLAY_BADGE_PADDING_Y_PX * 2)),
  };
}

function resolvedPopupBubbleSize(bubble) {
  const explicitWidth = Math.max(0, Number(bubble?.width || 0));
  const explicitHeight = Math.max(0, Number(bubble?.height || 0));
  if (explicitWidth > 0 && explicitHeight > 0) {
    return { width: explicitWidth, height: explicitHeight };
  }
  const autoSize = popupBubbleAutoSize(bubble);
  return {
    width: explicitWidth > 0 ? explicitWidth : autoSize.width,
    height: explicitHeight > 0 ? explicitHeight : autoSize.height,
  };
}

function popupBubbleEffectiveTimeMs(bubble) {
  if (!bubble) return 0;
  if (bubble.anchor_mode === "shot" && bubble.shot_id) {
    const shot = orderedShotsByTime().find((item) => item.id === bubble.shot_id);
    if (shot) return shot.time_ms;
  }
  return Math.max(0, Math.round(Number(bubble.time_ms ?? 0) || 0));
}

function popupBubbleVisibleWindow(bubble) {
  const startMs = popupBubbleEffectiveTimeMs(bubble);
  const durationMs = Math.max(1, Math.round(Number(bubble?.duration_ms ?? 1000) || 1000));
  return { startMs, endMs: startMs + durationMs };
}

function popupBubbleRenderPositionMs(bubble, positionMs) {
  const normalizedPositionMs = Math.max(0, Math.round(Number(positionMs) || 0));
  const { startMs, endMs } = popupBubbleVisibleWindow(bubble);
  return clamp(normalizedPositionMs, startMs, endMs);
}

function popupBubbleIsVisibleAtPosition(bubble, positionMs) {
  const normalizedPositionMs = Math.max(0, Math.round(Number(positionMs) || 0));
  const { startMs, endMs } = popupBubbleVisibleWindow(bubble);
  return normalizedPositionMs >= startMs && normalizedPositionMs <= endMs;
}

function popupBubbleSeekTimeMs(bubble) {
  if (!bubble) return 0;
  if (bubble.anchor_mode === "shot" && bubble.shot_id) {
    const shot = orderedShotsByTime().find((item) => item.id === bubble.shot_id);
    if (shot) return shotDisplayTimeMs(shot.time_ms);
  }
  return popupBubbleEffectiveTimeMs(bubble);
}

function defaultPopupShotId() {
  if (selectedShotId && stateHasShot(state, selectedShotId)) return selectedShotId;
  return orderedShotsByTime()[0]?.id || null;
}

function popupBubbleShotOptions() {
  return orderedShotsByTime().map((shot, index) => ({
    id: shot.id,
    label: `Shot ${index + 1} ${seconds(shot.time_ms)}s`,
  }));
}

function popupBubbleShotLabel(bubble) {
  if (!bubble?.shot_id) return "";
  return popupBubbleShotOptions().find((shot) => shot.id === bubble.shot_id)?.label?.replace(/\s+\d+(?:\.\d+)?s$/, "") || "";
}

function popupBubbleResolvedText(bubble) {
  const explicitText = String(bubble?.text || "");
  if (bubble?.anchor_mode === "shot" && bubble?.shot_id) {
    if (bubble?.content_type === "text") {
      return popupTextForShotId(bubble.shot_id) || explicitText;
    }
    if (bubble?.content_type === "text_image" && !String(bubble?.image_path || "").trim() && !explicitText.trim()) {
      return popupTextForShotId(bubble.shot_id) || popupBubbleShotLabel(bubble) || "Marker";
    }
  }
  return explicitText;
}

function popupBubblePlacementSelectorStyle(bubble) {
  if (!bubble) return null;
  return {
    show_text: false,
    width: 16,
    height: 16,
    background_color: POPUP_SELECTOR_FILL,
    text_color: POPUP_SELECTOR_FILL,
    border_color: "transparent",
    font_weight: "900",
  };
}

function popupBubbleRenderStyle(bubble) {
  return {
    background_color: bubble?.background_color || "#000000",
    text_color: bubble?.text_color || "#ffffff",
    font_weight: "700",
  };
}

function popupBubbleDisplayName(bubble, index) {
  const explicitName = String(bubble?.name || "").trim();
  if (explicitName) return explicitName;
  if (bubble?.anchor_mode === "shot") return popupBubbleShotLabel(bubble) || `Shot ${index + 1}`;
  return `Bubble ${index + 1}`;
}

function popupBubbleImageUrl(bubble) {
  if (!bubble?.id || !String(bubble.image_path || "").trim()) return "";
  return buildMediaUrl(`/media/popup/${encodeURIComponent(bubble.id)}`, bubble.image_path);
}

function popupBubbleSummaryText(bubble, index) {
  const parts = [];
  const displayName = popupBubbleDisplayName(bubble, index).trim();
  if (bubble?.anchor_mode === "shot" && bubble?.shot_id) {
    const resolvedText = popupBubbleResolvedText(bubble).trim();
    const shotLabel = popupBubbleShotLabel(bubble).trim();
    if (shotLabel && shotLabel !== displayName) parts.push(shotLabel);
    if (resolvedText && resolvedText !== displayName && resolvedText !== shotLabel) parts.push(resolvedText);
    if (parts.length === 0) parts.push("Shot-linked");
  } else {
    parts.push(`${precise(popupBubbleEffectiveTimeMs(bubble))}s`);
  }
  return parts.filter(Boolean).join(" | ");
}

function isPopupBubbleExpanded(bubbleId) {
  if (!bubbleId) return false;
  if (popupBubbleExpansion.has(bubbleId)) return Boolean(popupBubbleExpansion.get(bubbleId));
  return false;
}

function setPopupBubbleExpanded(bubbleId, expanded) {
  if (!bubbleId) return;
  popupBubbleExpansion.set(bubbleId, Boolean(expanded));
  syncLocalProjectUiState();
  scheduleProjectUiStateApply();
}

function popupEditorSectionDefaultExpanded(sectionId, bubble = null) {
  if (!sectionId) return true;
  if (sectionId === "motion") {
    return true;
  }
  return DEFAULT_POPUP_EDITOR_SECTION_EXPANSION[sectionId] ?? false;
}

function isPopupEditorSectionExpanded(sectionId, bubble = null) {
  if (!sectionId) return true;
  if (popupEditorSectionExpansion.has(sectionId)) return Boolean(popupEditorSectionExpansion.get(sectionId));
  return popupEditorSectionDefaultExpanded(sectionId, bubble);
}

function setPopupEditorSectionExpanded(sectionId, expanded) {
  if (!sectionId) return;
  popupEditorSectionExpansion.set(sectionId, Boolean(expanded));
}

function renderPopupEditorSectionToggles(card, bubble) {
  if (!(card instanceof HTMLElement)) return;
  card.querySelectorAll("[data-popup-editor-section]").forEach((section) => {
    if (!(section instanceof HTMLElement)) return;
    const sectionId = section.dataset.popupEditorSection || "";
    const expanded = isPopupEditorSectionExpanded(sectionId, bubble);
    section.classList.toggle("collapsed", !expanded);
    ensureSectionToggle(section, expanded, () => {
      setPopupEditorSectionExpanded(sectionId, !expanded);
      renderPopupEditors();
    });
  });
}

function collapseMinimizableInspectorItems({ syncUiState: shouldSyncUiState = true, persistUiState = true, rerender = false } = {}) {
  let changed = false;
  reviewTextBoxExpansion.forEach((expanded, boxId) => {
    if (expanded) {
      reviewTextBoxExpansion.set(boxId, false);
      changed = true;
    }
  });
  popupBubbleExpansion.forEach((expanded, bubbleId) => {
    if (expanded) {
      popupBubbleExpansion.set(bubbleId, false);
      changed = true;
    }
  });
  mergeSourceExpansion.forEach((expanded, sourceId) => {
    if (sourceId === PIP_DEFAULTS_SECTION_ID) return;
    if (expanded) {
      mergeSourceExpansion.set(sourceId, false);
      changed = true;
    }
  });
  if (!changed) return;
  if (shouldSyncUiState) syncLocalProjectUiState();
  if (shouldSyncUiState && persistUiState) scheduleProjectUiStateApply();
  if (rerender) {
    renderTextBoxEditors();
    renderPopupEditors();
    renderMergeMediaList();
    renderCollapsibleInspectorSections();
  }
}

function popupBubbleNavigatorElement(bubbleId) {
  if (!bubbleId) return null;
  const preferredSelectors = markersWorkbenchShown()
    ? [
        `#markers-workbench-list .popup-marker-row[data-popup-id="${bubbleId}"]`,
        `#popup-marker-list .popup-marker-row[data-popup-id="${bubbleId}"]`,
      ]
    : [
        `#popup-marker-list .popup-marker-row[data-popup-id="${bubbleId}"]`,
        `#markers-workbench-list .popup-marker-row[data-popup-id="${bubbleId}"]`,
      ];
  return preferredSelectors
    .map((selector) => document.querySelector(selector))
    .find((element) => element instanceof HTMLElement) || null;
}

function popupBubbleEditorCardElement(bubbleId) {
  if (!bubbleId) return null;
  return document.querySelector(`#markers-workbench-editor .popup-bubble-card[data-popup-id="${bubbleId}"]`)
    || document.querySelector(`.popup-bubble-card[data-popup-id="${bubbleId}"]`);
}

function popupBubbleCardElement(bubbleId) {
  return popupBubbleNavigatorElement(bubbleId) || popupBubbleEditorCardElement(bubbleId);
}

function revealPopupBubbleCard(bubbleId, { focus = false } = {}) {
  const card = popupBubbleNavigatorElement(bubbleId) || popupBubbleCardElement(bubbleId);
  if (!(card instanceof HTMLElement)) return;
  const list = ["markers-workbench-list", "popup-marker-list"]
    .map((id) => $(id))
    .find((element) => element instanceof HTMLElement && element.contains(card));
  if (list instanceof HTMLElement) {
    const listRect = list.getBoundingClientRect();
    const cardRect = card.getBoundingClientRect();
    if (cardRect.top < listRect.top) {
      list.scrollTop = Math.max(0, list.scrollTop + (cardRect.top - listRect.top) - 8);
    } else if (cardRect.bottom > listRect.bottom) {
      list.scrollTop = Math.max(0, list.scrollTop + (cardRect.bottom - listRect.bottom) + 8);
    }
  } else {
    card.scrollIntoView({ block: "nearest" });
  }
  if (focus) {
    const button = card.querySelector(".popup-marker-select, .popup-bubble-button");
    if (button instanceof HTMLElement) button.focus();
  }
}

function selectPopupBubble(
  bubbleId,
  { seek = true, reveal = true, focus = false, activateTool = false, expand = false, rerender = true } = {},
) {
  return markersPane?.selectPopupBubble(bubbleId, {
    seek,
    reveal,
    focus,
    activateTool,
    expand,
    rerender,
  }) ?? false;
}

function selectPopupBubbleForShot(shotId, options = {}) {
  return markersPane?.selectPopupBubbleForShot(shotId, options) ?? false;
}

function selectedPopupBubble() {
  return markersPane?.selectedPopupBubble() || null;
}

function setSelectedPopupPlacementMode(mode, offsetMs = selectedPopupKeyframeOffsetMs) {
  return markersPane?.setSelectedPopupPlacementMode(mode, offsetMs);
}

function popupPlacementSummary(bubble) {
  return markersPane?.popupPlacementSummary(bubble) || "Base point";
}

function setPopupBubbles(bubbles, { commit = true, rerender = true } = {}) {
  return markersPane?.setPopupBubbles(bubbles, { commit, rerender });
}

function syncPopupBubbleSizeControls(bubbleId) {
  return markersPane?.syncPopupBubbleSizeControls(bubbleId);
}

function setPopupBubbleField(bubbleId, field, rawValue, options = {}) {
  return markersPane?.setPopupBubbleField(bubbleId, field, rawValue, options);
}

function addPopupBubble(overrides = {}) {
  return markersPane?.addPopupBubble(overrides);
}

function popupShotPenaltyCounts(shotId) {
  const segment = timingSegmentForShot(shotId);
  const shot = shotById(shotId);
  return segment?.penalty_counts || shot?.score?.penalty_counts || {};
}

function popupShotHasPenaltySignal(shotId) {
  const counts = popupShotPenaltyCounts(shotId);
  if (Object.values(counts).some((value) => Number(value || 0) > 0)) return true;
  const text = popupTextForShotId(shotId).toUpperCase();
  return /\b(M|NS|NT|PE|FP|FTDR|FPE|PM|SPF|SND)\b/.test(text);
}

function popupShotHasScoringSignal(shotId) {
  if (popupShotHasPenaltySignal(shotId)) return true;
  const segment = timingSegmentForShot(shotId);
  const shot = shotById(shotId);
  const rawLetter = segment?.score_letter || shot?.score?.letter?.value || shot?.score?.letter || "";
  const scoreLetter = compactScoreDisplay(rawLetter, activeScoringRuleset());
  return Boolean(scoreLetter && scoreLetter !== defaultScoreLetter());
}

function popupShotMatchesImportMode(shot, mode) {
  return markersPane?.popupShotMatchesImportMode(shot, mode) ?? false;
}

function selectedPopupImportMode() {
  return markersPane?.selectedPopupImportMode() || "all";
}

function importShotPopups() {
  return markersPane?.importShotPopups();
}

function createPopupBubbleForShot(shotId) {
  return markersPane?.createPopupBubbleForShot(shotId) ?? false;
}

function applyTemplateStyleToSelectedPopupBubble() {
  return markersPane?.applyTemplateStyleToSelectedPopupBubble() ?? false;
}

function applySelectedPopupStyleToVisibleShotLinked() {
  return markersPane?.applySelectedPopupStyleToVisibleShotLinked() ?? false;
}

function removePopupBubble(bubbleId) {
  return markersPane?.removePopupBubble(bubbleId);
}

function duplicatePopupBubble(bubbleId) {
  return markersPane?.duplicatePopupBubble(bubbleId);
}

function clearPopupBubbleMotionPath(bubbleId) {
  return markersPane?.clearPopupBubbleMotionPath(bubbleId);
}

function seekPopupBubbleMotionPoint(bubbleId, offsetMs) {
  return markersPane?.seekPopupBubbleMotionPoint(bubbleId, offsetMs) ?? false;
}

function setPopupBubbleMotionPointValue(bubbleId, offsetMs, field, rawValue, options = {}) {
  return markersPane?.setPopupBubbleMotionPointValue(bubbleId, offsetMs, field, rawValue, options);
}

function popupBubbleKeyframes(bubble) {
  const basePoint = popupBubblePoint(bubble);
  const motionPath = popupBubbleMotionPath(bubble);
  const keyframes = [
    { offset_ms: 0, x: basePoint.x, y: basePoint.y, easing: "linear", base: true },
    ...motionPath.map((point) => ({ ...point, base: false })),
  ];
  const finishOffsetMs = Math.max(1, Math.round(Number(bubble?.duration_ms ?? 1) || 1));
  if ((bubble?.follow_motion || motionPath.length > 0) && !keyframes.some((point) => point.offset_ms === finishOffsetMs)) {
    const finishPoint = popupBubbleMotionPointAtOffset(motionPath, finishOffsetMs, basePoint);
    keyframes.push({
      offset_ms: finishOffsetMs,
      x: finishPoint.x,
      y: finishPoint.y,
      easing: motionPath[motionPath.length - 1]?.easing || "linear",
      base: false,
      synthesized: true,
    });
  }
  return keyframes;
}

function popupMotionGuidePointRole(bubble, point) {
  if (!point || point.base || point.offset_ms <= 0) return "start";
  if (bubble && point.offset_ms >= Math.max(1, Math.round(Number(bubble.duration_ms ?? 1) || 1))) return "finish";
  return popupMotionOffsetIsGenerated(bubble?.id, point.offset_ms) ? "generated" : "detail";
}

function popupMotionGuideStepName(index, point = null, bubble = null) {
  const role = popupMotionGuidePointRole(bubble, point);
  if (role === "start") return "Start";
  if (role === "finish") return "Finish";
  return `Step ${Math.max(1, index)}`;
}

function popupMotionGuidePointName(point, index, bubble = null) {
  return popupMotionGuideStepName(index, point, bubble);
}

function popupMotionGuidePointLabel(point, index, bubble = null) {
  if (!point) return "";
  const role = popupMotionGuidePointRole(bubble, point);
  if (role === "start") return "@ 0.000s";
  if (role === "finish") return `Marker end @ ${precise(point.offset_ms)}s`;
  return `${role === "generated" ? "Auto" : "Detail"} @ ${precise(point.offset_ms)}s`;
}

function popupMotionGuideHintText(bubble, inBetweenCount) {
  const summary = popupMotionGenerationSummaryByBubbleId.get(bubble?.id);
  if (summary) return summary;
  if (inBetweenCount > 0) {
    return "Regenerate first tries to trace the video motion and falls back to evenly spaced in-between points. Add Detail splits the largest remaining time gap.";
  }
  return "Select Start or Finish below, then place it on the video. Generate first tries to trace the video motion and falls back to evenly spaced in-between points. Add Detail splits the largest remaining time gap.";
}

function selectedPopupMotionPoint(bubble) {
  if (!bubble) return { x: 0.5, y: 0.5, base: true, offset_ms: 0, easing: "linear" };
  const selectedOffset = selectedPopupPlacementMode === "keyframe"
    ? selectedPopupKeyframeOffsetMs
    : 0;
  return popupKeyframePoint(bubble, selectedOffset);
}

function popupKeyframePoint(bubble, offsetMs) {
  const normalizedOffset = Math.max(0, Math.round(Number(offsetMs) || 0));
  const keyframe = popupBubbleKeyframes(bubble).find((point) => point.offset_ms === normalizedOffset);
  if (keyframe) {
    return {
      x: keyframe.x,
      y: keyframe.y,
      base: Boolean(keyframe.base),
      offset_ms: keyframe.offset_ms,
      easing: popupKeyframeEasing(keyframe.easing),
      synthesized: Boolean(keyframe.synthesized),
    };
  }
  const fallbackPoint = popupBubblePoint(bubble, popupBubbleEffectiveTimeMs(bubble) + normalizedOffset);
  return {
    x: fallbackPoint.x,
    y: fallbackPoint.y,
    base: normalizedOffset <= 0,
    offset_ms: normalizedOffset,
    easing: "linear",
    synthesized: false,
  };
}

function popupMotionDistancePx(startPoint, finishPoint) {
  const width = Math.max(1, Number($("primary-video")?.videoWidth || state?.project?.primary_video?.width || 1920) || 1920);
  const height = Math.max(1, Number($("primary-video")?.videoHeight || state?.project?.primary_video?.height || 1080) || 1080);
  return Math.hypot((finishPoint.x - startPoint.x) * width, (finishPoint.y - startPoint.y) * height);
}

function popupMotionFrameDurationMs() {
  const frameDurationMs = primaryFrameDurationMs();
  return frameDurationMs > 0 ? frameDurationMs : (1000 / POPUP_MOTION_REFERENCE_FPS);
}

function popupMotionSuggestedInBetweenCount(bubble, finishOffsetMs, startPoint, finishPoint) {
  const frameDurationMs = popupMotionFrameDurationMs();
  const frameCount = Math.max(1, Math.ceil(finishOffsetMs / frameDurationMs));
  const distancePx = popupMotionDistancePx(startPoint, finishPoint);
  const bubbleSize = resolvedPopupBubbleSize(bubble);
  const sizeWeight = bubble?.content_type === "image" || bubble?.content_type === "text_image"
    ? 1.12
    : clampNumber(Math.max(bubbleSize.width || 0, bubbleSize.height || 0) / 320, 1, 1.2);
  const hasMeaningfulTravel = distancePx >= 6;
  if (!hasMeaningfulTravel) {
    return {
      count: 0,
      frameCount,
      distancePx: Math.round(distancePx),
    };
  }
  const timeTarget = Math.max(0, Math.ceil(finishOffsetMs / POPUP_MOTION_TIME_BUDGET_PER_POINT_MS) - 1);
  const travelTarget = Math.max(0, Math.ceil(distancePx / POPUP_MOTION_TRAVEL_PX_PER_POINT));
  let targetCount = Math.max(timeTarget, travelTarget);
  const maxCount = Math.min(POPUP_MOTION_MAX_AUTO_POINTS, Math.max(0, Math.round(Number(finishOffsetMs) || 0) - 1));
  let count = clamp(Math.round(targetCount * sizeWeight), 0, maxCount);
  if (count === 0 && maxCount > 0) count = 1;
  return {
    count,
    frameCount,
    distancePx: Math.round(distancePx),
  };
}

function popupMotionAutoOffsets(finishOffsetMs, count) {
  const upperBound = Math.max(1, Math.round(Number(finishOffsetMs) || 0) - 1);
  if (count <= 0 || upperBound < 1) return [];
  const usedOffsets = new Set();
  const offsets = [];
  for (let index = 1; index <= count; index += 1) {
    const ratio = index / (count + 1);
    let candidate = clamp(Math.round(finishOffsetMs * ratio), 1, upperBound);
    let forward = candidate;
    while (forward <= upperBound && usedOffsets.has(forward)) forward += 1;
    if (forward <= upperBound && !usedOffsets.has(forward)) {
      candidate = forward;
    } else {
      let backward = candidate - 1;
      while (backward >= 1 && usedOffsets.has(backward)) backward -= 1;
      if (backward < 1 || usedOffsets.has(backward)) continue;
      candidate = backward;
    }
    usedOffsets.add(candidate);
    offsets.push(candidate);
  }
  return offsets.sort((left, right) => left - right);
}

function popupMotionNearestFreeOffset(targetOffsetMs, minOffsetMs, maxOffsetMs, usedOffsets) {
  const target = clamp(Math.round(Number(targetOffsetMs) || 0), minOffsetMs, maxOffsetMs);
  if (!usedOffsets.has(target)) return target;
  for (let distance = 1; distance <= (maxOffsetMs - minOffsetMs); distance += 1) {
    const backward = target - distance;
    if (backward >= minOffsetMs && !usedOffsets.has(backward)) return backward;
    const forward = target + distance;
    if (forward <= maxOffsetMs && !usedOffsets.has(forward)) return forward;
  }
  return null;
}

function popupMotionNextDetailOffsetMs(bubble) {
  const keyframes = popupBubbleKeyframes(bubble)
    .map((point) => Math.max(0, Math.round(Number(point.offset_ms) || 0)))
    .sort((left, right) => left - right);
  if (keyframes.length <= 1) return null;
  const usedOffsets = new Set(keyframes.filter((offsetMs) => offsetMs > 0));
  let bestGap = null;
  for (let index = 1; index < keyframes.length; index += 1) {
    const left = keyframes[index - 1];
    const right = keyframes[index];
    if (right - left <= 1) continue;
    const midpoint = Math.round((left + right) / 2);
    const candidate = popupMotionNearestFreeOffset(midpoint, left + 1, right - 1, usedOffsets);
    if (candidate === null) continue;
    const gap = right - left;
    if (!bestGap || gap > bestGap.size) {
      bestGap = { size: gap, offsetMs: candidate };
    }
  }
  return bestGap?.offsetMs ?? null;
}

function popupMotionSamplePointForOffset(bubble, offsetMs, finishOffsetMs, startPoint, finishPoint) {
  const clampedOffsetMs = clamp(Math.round(Number(offsetMs) || 0), 0, finishOffsetMs);
  const sourcePath = popupBubbleMotionPath(bubble).filter((point) => point.offset_ms <= finishOffsetMs);
  if (clampedOffsetMs >= finishOffsetMs) return { x: finishPoint.x, y: finishPoint.y };
  if (sourcePath.length === 0) {
    const ratio = finishOffsetMs <= 0 ? 0 : clampedOffsetMs / finishOffsetMs;
    return {
      x: clamp(startPoint.x + ((finishPoint.x - startPoint.x) * ratio), 0, 1),
      y: clamp(startPoint.y + ((finishPoint.y - startPoint.y) * ratio), 0, 1),
    };
  }
  return popupBubbleMotionPointAtOffset(sourcePath, clampedOffsetMs, startPoint);
}

function popupMotionInBetweenOffsets(motionPath, finishOffsetMs) {
  return normalizePopupMotionPath(motionPath)
    .map((point) => Math.max(0, Math.round(Number(point.offset_ms) || 0)))
    .filter((offsetMs) => offsetMs > 0 && offsetMs < finishOffsetMs);
}

function popupMotionAlignPathToFinish(motionPath, finishOffsetMs, startPoint, finishPoint) {
  const normalizedPath = normalizePopupMotionPath(motionPath);
  if (normalizedPath.length === 0) return normalizedPath;
  const tracedFinishPoint = popupBubbleMotionPointAtOffset(normalizedPath, finishOffsetMs, startPoint);
  const deltaX = (finishPoint?.x ?? tracedFinishPoint.x) - tracedFinishPoint.x;
  const deltaY = (finishPoint?.y ?? tracedFinishPoint.y) - tracedFinishPoint.y;
  if (Math.abs(deltaX) < 0.0001 && Math.abs(deltaY) < 0.0001) return normalizedPath;
  return normalizePopupMotionPath(normalizedPath.map((point) => {
    const ratio = finishOffsetMs <= 0 ? 1 : clamp(point.offset_ms / finishOffsetMs, 0, 1);
    return {
      ...point,
      x: clamp(point.x + (deltaX * ratio), 0, 1),
      y: clamp(point.y + (deltaY * ratio), 0, 1),
    };
  }));
}

function generatePopupBubbleMotionPathLinear(bubbleId) {
  return markersPane?.generatePopupBubbleMotionPathLinear(bubbleId) ?? false;
}

function generatePopupBubbleMotionPath(bubbleId) {
  return markersPane?.generatePopupBubbleMotionPath(bubbleId) ?? false;
}

function syncSelectedPopupKeyframeOffset(bubble) {
  const keyframes = popupBubbleKeyframes(bubble);
  if (!keyframes.some((point) => point.offset_ms === selectedPopupKeyframeOffsetMs)) {
    selectedPopupKeyframeOffsetMs = keyframes[keyframes.length - 1]?.offset_ms ?? 0;
  }
}

function setSelectedPopupKeyframeOffset(offsetMs) {
  selectedPopupKeyframeOffsetMs = Math.max(0, Math.round(Number(offsetMs) || 0));
  selectedPopupPlacementMode = selectedPopupKeyframeOffsetMs > 0 ? "keyframe" : "base";
}

function addPopupBubbleKeyframeAtPlayhead(bubbleId) {
  const bubble = popupBubbles().find((item) => item.id === bubbleId);
  if (!bubble) return false;
  const finishOffsetMs = Math.max(1, Math.round(Number(bubble.duration_ms ?? 1) || 1));
  if (finishOffsetMs <= 1) {
    setStatus("This marker is too short for an in-between detail step.");
    return false;
  }
  const offsetMs = popupMotionNextDetailOffsetMs(bubble);
  if (offsetMs === null) {
    setStatus("No room for another detail point between the existing motion points.");
    return false;
  }
  const startPoint = popupKeyframePoint(bubble, 0);
  const finishPoint = popupKeyframePoint(bubble, finishOffsetMs);
  const sampledPoint = popupMotionSamplePointForOffset(bubble, offsetMs, finishOffsetMs, startPoint, finishPoint);
  const nextBubble = updatePopupBubbleMotionPoint(
    normalizePopupBubble({ ...bubble, follow_motion: true }),
    offsetMs,
    sampledPoint.x,
    sampledPoint.y,
  );
  setPopupEditorSectionExpanded("motion", true);
  setSelectedPopupKeyframeOffset(offsetMs);
  setPopupMotionGeneratedOffsets(bubble.id, [...popupMotionGeneratedOffsetsForBubbleId(bubble.id)].filter((value) => value !== offsetMs));
  setPopupBubbles(popupBubbles().map((item) => item.id === bubbleId ? nextBubble : item), { commit: true, rerender: true });
  seekPopupBubbleMotionPoint(bubbleId, offsetMs);
  return true;
}

function deletePopupBubbleKeyframe(bubbleId, offsetMs) {
  const bubble = popupBubbles().find((item) => item.id === bubbleId);
  if (!bubble) return false;
  const normalizedOffset = Math.max(0, Math.round(Number(offsetMs) || 0));
  if (normalizedOffset <= 0 || normalizedOffset >= Math.max(1, bubble.duration_ms)) return false;
  const nextBubbles = popupBubbles().map((bubble) => bubble.id === bubbleId
    ? normalizePopupBubble({
        ...bubble,
        motion_path: popupBubbleMotionPath(bubble).filter((point) => point.offset_ms !== normalizedOffset),
      })
    : bubble);
  setPopupMotionGeneratedOffsets(bubbleId, [...popupMotionGeneratedOffsetsForBubbleId(bubbleId)].filter((value) => value !== normalizedOffset));
  setSelectedPopupKeyframeOffset(0);
  setPopupBubbles(nextBubbles, { commit: true, rerender: true });
  return true;
}

function adjacentPopupKeyframeOffset(bubble, direction) {
  const keyframes = popupBubbleKeyframes(bubble);
  if (keyframes.length === 0) return 0;
  const currentIndex = keyframes.findIndex((point) => point.offset_ms === selectedPopupKeyframeOffsetMs);
  if (currentIndex < 0) return keyframes[0].offset_ms;
  const nextIndex = clamp(currentIndex + direction, 0, keyframes.length - 1);
  return keyframes[nextIndex].offset_ms;
}

function jumpPopupBubbleKeyframe(bubbleId, direction) {
  const bubble = popupBubbles().find((item) => item.id === bubbleId);
  if (!bubble) return false;
  syncSelectedPopupKeyframeOffset(bubble);
  const offsetMs = adjacentPopupKeyframeOffset(bubble, direction);
  setSelectedPopupKeyframeOffset(offsetMs);
  seekPopupBubbleMotionPoint(bubbleId, offsetMs);
  renderPopupEditors();
  return true;
}

function copyPopupBubbleMotionFromPrevious(bubbleId) {
  return markersPane?.copyPopupBubbleMotionFromPrevious(bubbleId) ?? false;
}

function applyPopupBubbleMotionToVisibleShotLinked(bubbleId) {
  return markersPane?.applyPopupBubbleMotionToVisibleShotLinked(bubbleId) ?? false;
}

function popupTraceFrameSize(video, maxWidth = 480) {
  const sourceWidth = Math.max(1, Math.round(Number(video?.videoWidth || 0) || 0));
  const sourceHeight = Math.max(1, Math.round(Number(video?.videoHeight || 0) || 0));
  if (sourceWidth <= 1 || sourceHeight <= 1) return null;
  const scale = Math.min(1, maxWidth / sourceWidth);
  return {
    width: Math.max(96, Math.round(sourceWidth * scale)),
    height: Math.max(96, Math.round(sourceHeight * scale)),
  };
}

function popupTraceWaitForVideoFrame(video, timeoutMs = 1200) {
  return new Promise((resolve) => {
    let settled = false;
    let timeoutId = null;
    const finish = () => {
      if (settled) return;
      settled = true;
      if (timeoutId !== null) window.clearTimeout(timeoutId);
      resolve();
    };
    timeoutId = window.setTimeout(finish, timeoutMs);
    if (typeof video?.requestVideoFrameCallback === "function") {
      video.requestVideoFrameCallback(() => finish());
      return;
    }
    requestAnimationFrame(() => finish());
  });
}

function popupTraceWaitForEvent(target, eventName, timeoutMs = 2000) {
  return new Promise((resolve, reject) => {
    let timeoutId = null;
    const cleanup = () => {
      if (timeoutId !== null) window.clearTimeout(timeoutId);
      target.removeEventListener(eventName, handleEvent);
      target.removeEventListener("error", handleError);
    };
    const handleEvent = () => {
      cleanup();
      resolve();
    };
    const handleError = () => {
      cleanup();
      reject(new Error(`${eventName} failed`));
    };
    timeoutId = window.setTimeout(() => {
      cleanup();
      reject(new Error(`${eventName} timed out`));
    }, timeoutMs);
    target.addEventListener(eventName, handleEvent, { once: true });
    target.addEventListener("error", handleError, { once: true });
  });
}

async function popupTraceSeekVideo(video, timeMs) {
  if (!(video instanceof HTMLVideoElement)) return false;
  const durationMs = Number.isFinite(video.duration) ? Math.max(0, Math.floor(video.duration * 1000)) : null;
  const clampedMs = durationMs === null
    ? Math.max(0, Math.floor(Number(timeMs) || 0))
    : clamp(Math.floor(Number(timeMs) || 0), 0, durationMs);
  const targetTimeS = clampedMs / 1000;
  if (Math.abs((video.currentTime || 0) - targetTimeS) < 0.001) {
    await popupTraceWaitForVideoFrame(video);
    return true;
  }
  const seekPromise = popupTraceWaitForEvent(video, "seeked");
  try {
    video.currentTime = targetTimeS;
  } catch {
    return false;
  }
  try {
    await seekPromise;
    await popupTraceWaitForVideoFrame(video);
    return true;
  } catch {
    return false;
  }
}

function popupTraceLumaFrame(ctx, width, height) {
  const { data } = ctx.getImageData(0, 0, width, height);
  const luma = new Uint8ClampedArray(width * height);
  for (let index = 0, pixelIndex = 0; index < data.length; index += 4, pixelIndex += 1) {
    luma[pixelIndex] = Math.round((data[index] * 0.299) + (data[index + 1] * 0.587) + (data[index + 2] * 0.114));
  }
  return luma;
}

function popupTraceClampCenter(value, halfSize, maxSize) {
  const upper = Math.max(halfSize, maxSize - halfSize - 1);
  return clamp(Math.round(Number(value) || 0), halfSize, upper);
}

function popupTracePatchMoments(samples) {
  let sum = 0;
  let sumSq = 0;
  for (let index = 0; index < samples.length; index += 1) {
    const value = samples[index];
    sum += value;
    sumSq += value * value;
  }
  const count = Math.max(1, samples.length);
  const mean = sum / count;
  const variance = Math.max(0, (sumSq / count) - (mean * mean));
  return {
    mean,
    stdDev: Math.sqrt(variance),
  };
}

function popupTraceExtractPatch(luma, frameWidth, frameHeight, centerX, centerY, patchSize = 28) {
  const halfSize = Math.floor(patchSize / 2);
  const clampedX = popupTraceClampCenter(centerX, halfSize, frameWidth);
  const clampedY = popupTraceClampCenter(centerY, halfSize, frameHeight);
  const patch = new Uint8ClampedArray(patchSize * patchSize);
  let targetIndex = 0;
  for (let y = clampedY - halfSize; y < clampedY + halfSize; y += 1) {
    for (let x = clampedX - halfSize; x < clampedX + halfSize; x += 1) {
      patch[targetIndex] = luma[(y * frameWidth) + x];
      targetIndex += 1;
    }
  }
  const moments = popupTracePatchMoments(patch);
  return {
    data: patch,
    size: patchSize,
    centerX: clampedX,
    centerY: clampedY,
    mean: moments.mean,
    stdDev: moments.stdDev,
  };
}

function popupTracePatchStrength(patch, referenceX, referenceY) {
  const distance = Math.hypot(patch.centerX - referenceX, patch.centerY - referenceY);
  return patch.stdDev - (distance * 0.35);
}

function popupTraceSelectPatch(luma, frameWidth, frameHeight, centerX, centerY, patchSize = 28, searchRadius = 18, step = 2) {
  const halfSize = Math.floor(patchSize / 2);
  const minX = popupTraceClampCenter(centerX - searchRadius, halfSize, frameWidth);
  const maxX = popupTraceClampCenter(centerX + searchRadius, halfSize, frameWidth);
  const minY = popupTraceClampCenter(centerY - searchRadius, halfSize, frameHeight);
  const maxY = popupTraceClampCenter(centerY + searchRadius, halfSize, frameHeight);
  let bestPatch = popupTraceExtractPatch(luma, frameWidth, frameHeight, centerX, centerY, patchSize);
  let bestScore = popupTracePatchStrength(bestPatch, centerX, centerY);
  for (let y = minY; y <= maxY; y += step) {
    for (let x = minX; x <= maxX; x += step) {
      const candidate = popupTraceExtractPatch(luma, frameWidth, frameHeight, x, y, patchSize);
      const candidateScore = popupTracePatchStrength(candidate, centerX, centerY);
      if (candidateScore > bestScore) {
        bestPatch = candidate;
        bestScore = candidateScore;
      }
    }
  }
  return bestPatch;
}

function popupTracePatchCorrelation(luma, frameWidth, patch, centerX, centerY) {
  const halfSize = Math.floor(patch.size / 2);
  let sum = 0;
  let sumSq = 0;
  for (let y = centerY - halfSize; y < centerY + halfSize; y += 1) {
    for (let x = centerX - halfSize; x < centerX + halfSize; x += 1) {
      const value = luma[(y * frameWidth) + x];
      sum += value;
      sumSq += value * value;
    }
  }
  const count = Math.max(1, patch.data.length);
  const mean = sum / count;
  const variance = Math.max(0, (sumSq / count) - (mean * mean));
  const stdDev = Math.sqrt(variance);
  if (patch.stdDev < 1 || stdDev < 1) return Number.NEGATIVE_INFINITY;
  let covariance = 0;
  let patchIndex = 0;
  for (let y = centerY - halfSize; y < centerY + halfSize; y += 1) {
    for (let x = centerX - halfSize; x < centerX + halfSize; x += 1) {
      covariance += (luma[(y * frameWidth) + x] - mean) * (patch.data[patchIndex] - patch.mean);
      patchIndex += 1;
    }
  }
  return covariance / (count * patch.stdDev * stdDev);
}

function popupTraceBestMatch(luma, frameWidth, frameHeight, patch, previousCenter, searchRadius = 36, step = 2) {
  const halfSize = Math.floor(patch.size / 2);
  const minX = popupTraceClampCenter(previousCenter.x - searchRadius, halfSize, frameWidth);
  const maxX = popupTraceClampCenter(previousCenter.x + searchRadius, halfSize, frameWidth);
  const minY = popupTraceClampCenter(previousCenter.y - searchRadius, halfSize, frameHeight);
  const maxY = popupTraceClampCenter(previousCenter.y + searchRadius, halfSize, frameHeight);
  let best = { x: previousCenter.x, y: previousCenter.y, score: Number.NEGATIVE_INFINITY };
  for (let y = minY; y <= maxY; y += step) {
    for (let x = minX; x <= maxX; x += step) {
      const score = popupTracePatchCorrelation(luma, frameWidth, patch, x, y);
      if (score > best.score) best = { x, y, score };
    }
  }
  const refineMinX = popupTraceClampCenter(best.x - step, halfSize, frameWidth);
  const refineMaxX = popupTraceClampCenter(best.x + step, halfSize, frameWidth);
  const refineMinY = popupTraceClampCenter(best.y - step, halfSize, frameHeight);
  const refineMaxY = popupTraceClampCenter(best.y + step, halfSize, frameHeight);
  for (let y = refineMinY; y <= refineMaxY; y += 1) {
    for (let x = refineMinX; x <= refineMaxX; x += 1) {
      const score = popupTracePatchCorrelation(luma, frameWidth, patch, x, y);
      if (score > best.score) best = { x, y, score };
    }
  }
  return best;
}

function popupTraceOffsets(durationMs) {
  const normalizedDuration = Math.max(1, Math.round(Number(durationMs) || 0));
  const stepMs = Math.max(33, Math.floor(normalizedDuration / 20));
  const offsets = [];
  for (let offsetMs = stepMs; offsetMs < normalizedDuration; offsetMs += stepMs) {
    offsets.push(offsetMs);
  }
  if (offsets.length === 0 || offsets[offsets.length - 1] !== normalizedDuration) offsets.push(normalizedDuration);
  return offsets;
}

function popupTraceSimplifyPoints(points) {
  if (!Array.isArray(points) || points.length === 0) return [];
  const simplified = [];
  points.forEach((point, index) => {
    if (index === 0 || index === points.length - 1) {
      simplified.push(point);
      return;
    }
    const previous = simplified[simplified.length - 1] || points[index - 1];
    if (Math.abs(point.x - previous.x) < 0.005 && Math.abs(point.y - previous.y) < 0.005) return;
    simplified.push(point);
  });
  return normalizePopupMotionPath(simplified);
}

async function autoTracePopupBubbleMotion(bubbleId) {
  const bubble = popupBubbles().find((item) => item.id === bubbleId) || null;
  const video = $("primary-video");
  if (!bubble) return false;
  if (!(video instanceof HTMLVideoElement) || !state?.media?.primary_available || Number(video.videoWidth || 0) <= 0) {
    setStatus("Load primary video before tracing marker motion.");
    return false;
  }
  if (popupAutoTraceBubbleId) {
    setStatus("Finish the current motion trace before starting another one.");
    return false;
  }
  const frameSize = popupTraceFrameSize(video);
  if (!frameSize) {
    setStatus("Primary video is not ready for motion tracing yet.");
    return false;
  }
  const restorePositionMs = currentPrimaryVideoPositionMs();
  const shouldResumePlayback = !video.paused;
  const startMs = popupBubbleEffectiveTimeMs(bubble);
  const basePoint = popupBubblePoint(normalizePopupBubble({ ...bubble, follow_motion: false, motion_path: [] }), startMs);
  const canvas = document.createElement("canvas");
  canvas.width = frameSize.width;
  canvas.height = frameSize.height;
  const ctx = canvas.getContext("2d", { willReadFrequently: true });
  if (!ctx) {
    setStatus("Could not create a video frame surface for motion tracing.");
    return false;
  }
  popupAutoTraceBubbleId = bubble.id;
  setPopupEditorSectionExpanded("motion", true);
  video.pause();
  renderPopupEditors();
  setStatus("Tracing motion…");
  let tracedPoints = [];
  let traceFailed = false;
  let weakMatchCount = 0;
  try {
    const startSeekSucceeded = await popupTraceSeekVideo(video, startMs);
    if (!startSeekSucceeded) throw new Error("Could not seek to the marker start time.");
    ctx.drawImage(video, 0, 0, frameSize.width, frameSize.height);
    const initialLuma = popupTraceLumaFrame(ctx, frameSize.width, frameSize.height);
    const initialCenter = {
      x: Math.round(clamp(basePoint.x, 0, 1) * (frameSize.width - 1)),
      y: Math.round(clamp(basePoint.y, 0, 1) * (frameSize.height - 1)),
    };
    const patch = popupTraceSelectPatch(initialLuma, frameSize.width, frameSize.height, initialCenter.x, initialCenter.y);
    if (patch.stdDev < 8) {
      setStatus("Could not trace motion — move the marker base onto a more distinct detail, then try again.");
      return false;
    }
    const featureOffset = {
      x: (initialCenter.x - patch.centerX) / Math.max(1, frameSize.width - 1),
      y: (initialCenter.y - patch.centerY) / Math.max(1, frameSize.height - 1),
    };
    let previousCenter = { x: patch.centerX, y: patch.centerY };
    for (const offsetMs of popupTraceOffsets(bubble.duration_ms)) {
      const seekSucceeded = await popupTraceSeekVideo(video, startMs + offsetMs);
      if (!seekSucceeded) {
        traceFailed = true;
        break;
      }
      ctx.drawImage(video, 0, 0, frameSize.width, frameSize.height);
      const luma = popupTraceLumaFrame(ctx, frameSize.width, frameSize.height);
      const match = popupTraceBestMatch(luma, frameSize.width, frameSize.height, patch, previousCenter);
      if (!Number.isFinite(match.score)) {
        traceFailed = true;
        break;
      }
      weakMatchCount = match.score < 0.08 ? weakMatchCount + 1 : 0;
      if (weakMatchCount > 3) {
        traceFailed = true;
        break;
      }
      previousCenter = { x: match.x, y: match.y };
      tracedPoints.push({
        offset_ms: offsetMs,
        x: clamp((match.x / Math.max(1, frameSize.width - 1)) + featureOffset.x, 0, 1),
        y: clamp((match.y / Math.max(1, frameSize.height - 1)) + featureOffset.y, 0, 1),
        easing: "linear",
      });
    }
    const simplifiedPoints = popupTraceSimplifyPoints(tracedPoints);
    if (simplifiedPoints.length === 0) {
      setStatus(traceFailed
        ? "Could not trace motion — move the marker base onto a more distinct detail, then try again."
        : "Motion trace found no movement to record. Add a step manually if you need a path.");
      return false;
    }
    setPopupEditorSectionExpanded("motion", true);
    setSelectedPopupKeyframeOffset(0);
    setPopupBubbles(popupBubbles().map((item) => item.id === bubble.id
      ? normalizePopupBubble({
          ...item,
          follow_motion: true,
          motion_path: simplifiedPoints,
        })
      : item), { commit: true, rerender: true });
    setStatus(traceFailed
      ? `Traced ${simplifiedPoints.length} motion point${simplifiedPoints.length === 1 ? "" : "s"}. Review the later points before exporting.`
      : `Traced ${simplifiedPoints.length} motion point${simplifiedPoints.length === 1 ? "" : "s"}.`);
    return true;
  } catch (error) {
    console.error(error);
    setStatus("Could not trace motion — move the marker base onto a more distinct detail, then try again.");
    return false;
  } finally {
    popupAutoTraceBubbleId = null;
    await popupTraceSeekVideo(video, restorePositionMs).catch(() => {});
    renderPopupEditors();
    renderLiveOverlay();
    if (shouldResumePlayback) {
      const playResult = video.play?.();
      if (playResult?.catch) playResult.catch(() => {});
    }
  }
}

function setPopupBubbleMotionUiMode(bubbleId, uiMode, options = {}) {
  return markersPane?.setPopupBubbleMotionUiMode(bubbleId, uiMode, options);
}

function syncPopupBubbleMotionModeControls(card, bubble) {
  return markersPane?.syncPopupBubbleMotionModeControls(card, bubble);
}

function renderPopupBubbleMotionGuide(card, bubble) {
  const guidedSection = card.querySelector('[data-popup-motion-mode="guided"]');
  const guidedList = card.querySelector('[data-popup-guided-point-list]');
  const stepCount = card.querySelector('[data-popup-motion-step-count]');
  const selectedLabel = card.querySelector('[data-popup-motion-selected-step]');
  const generateButton = card.querySelector('[data-popup-action="generate_motion_path"]');
  const summary = card.querySelector('[data-popup-motion-summary]');
  const prevButton = card.querySelector('[data-popup-action="prev_motion_step"]');
  const nextButton = card.querySelector('[data-popup-action="next_motion_step"]');
  const removeButton = card.querySelector('[data-popup-action="remove_motion_step"]');
  const clearButton = card.querySelector('[data-popup-action="clear_motion_path"]');
  if (!(guidedSection instanceof HTMLElement) || !(guidedList instanceof HTMLElement)) return;
  guidedList.innerHTML = "";
  if (popupBubbleMotionUiMode(bubble) === "fixed") return;
  syncSelectedPopupKeyframeOffset(bubble);
  const keyframes = popupBubbleKeyframes(bubble);
  const finishOffsetMs = Math.max(1, Math.round(Number(bubble.duration_ms ?? 1) || 1));
  const selectedIndex = keyframes.findIndex((point) => point.offset_ms === selectedPopupKeyframeOffsetMs);
  const selectedPoint = keyframes[selectedIndex >= 0 ? selectedIndex : 0] || keyframes[0] || null;
  const inBetweenCount = keyframes.filter((point) => point.offset_ms > 0 && point.offset_ms < finishOffsetMs).length;
  if (stepCount instanceof HTMLElement) {
    stepCount.textContent = `Finish @ ${precise(finishOffsetMs)}s • ${inBetweenCount} in-between point${inBetweenCount === 1 ? "" : "s"}`;
  }
  if (selectedLabel instanceof HTMLElement) {
    selectedLabel.textContent = !selectedPoint
      ? "Selected: Start"
      : `Selected: ${popupMotionGuidePointName(selectedPoint, selectedIndex, bubble)}`;
  }
  if (generateButton instanceof HTMLButtonElement) {
    generateButton.textContent = popupMotionGenerationSummaryByBubbleId.has(bubble.id) ? "Regenerate" : "Generate";
  }
  if (summary instanceof HTMLElement) {
    summary.textContent = popupMotionGuideHintText(bubble, inBetweenCount);
  }
  if (prevButton instanceof HTMLButtonElement) prevButton.disabled = keyframes.length <= 1 || selectedIndex <= 0;
  if (nextButton instanceof HTMLButtonElement) nextButton.disabled = keyframes.length <= 1 || selectedIndex < 0 || selectedIndex >= keyframes.length - 1;
  if (removeButton instanceof HTMLButtonElement) removeButton.disabled = !selectedPoint || selectedPoint.offset_ms <= 0 || selectedPoint.offset_ms >= finishOffsetMs;
  if (clearButton instanceof HTMLButtonElement) clearButton.disabled = popupBubbleMotionPath(bubble).length === 0;
  keyframes.forEach((point, index) => {
    const role = popupMotionGuidePointRole(bubble, point);
    const pointName = popupMotionGuidePointName(point, index, bubble);
    const pointLabel = popupMotionGuidePointLabel(point, index, bubble);
    const pointKind = role === "generated"
      ? "Auto"
      : role === "detail"
        ? "Detail"
        : role === "finish"
          ? "Finish"
          : "Start";
    const selectPoint = ({ seek = true, rerender = true } = {}) => {
      selectedPopupBubbleId = bubble.id;
      setSelectedPopupKeyframeOffset(point.offset_ms);
      if (rerender) renderPopupEditors();
      renderLiveOverlay();
      if (seek) seekPopupBubbleMotionPoint(bubble.id, point.offset_ms);
    };
    const row = document.createElement("div");
    row.className = "popup-motion-point-row-guided";
    row.classList.toggle("selected", point.offset_ms === selectedPopupKeyframeOffsetMs);
    row.classList.toggle("generated", role === "generated");
    row.classList.toggle("detail", role === "detail");
    row.classList.toggle("finish", role === "finish");
    row.classList.toggle("start", role === "start");
    row.dataset.popupKeyframeOffset = String(point.offset_ms);
    row.innerHTML = `
      <button type="button" class="popup-motion-point-jump" data-popup-motion-seek="true">${pointName}</button>
      <div class="popup-motion-point-meta">
        <span class="popup-motion-point-label">${pointLabel}</span>
        <span class="popup-motion-point-kind popup-motion-point-kind-${role}">${pointKind}</span>
      </div>
      <div class="popup-motion-point-fields">
        <label class="popup-motion-axis-field">X
          <input data-popup-motion-field="x" type="number" min="0" max="1" step="0.0001" />
        </label>
        <label class="popup-motion-axis-field">Y
          <input data-popup-motion-field="y" type="number" min="0" max="1" step="0.0001" />
        </label>
      </div>
    `;
    row.addEventListener("click", (event) => {
      const target = event.target;
      if (target instanceof HTMLInputElement) return;
      if (target instanceof HTMLButtonElement && target.dataset.popupMotionSeek === "true") return;
      selectPoint();
    });
    const seekButton = row.querySelector('[data-popup-motion-seek="true"]');
    if (seekButton instanceof HTMLButtonElement) {
      seekButton.addEventListener("click", (event) => {
        event.preventDefault();
        event.stopPropagation();
        selectPoint();
      });
    }
    ["x", "y"].forEach((field) => {
      const control = row.querySelector(`[data-popup-motion-field="${field}"]`);
      if (!(control instanceof HTMLInputElement)) return;
      syncControlValue(control, formattedCoordinateValue(point[field]));
      const commitHandler = () => {
        selectPoint({ seek: false, rerender: false });
        setPopupBubbleMotionPointValue(bubble.id, point.offset_ms, field, control.value, { commit: true, rerender: true });
      };
      control.addEventListener("input", () => {
        selectPoint({ seek: false, rerender: false });
        setPopupBubbleMotionPointValue(bubble.id, point.offset_ms, field, control.value, { commit: false, rerender: false });
      });
      control.addEventListener("change", commitHandler);
      control.addEventListener("blur", commitHandler);
    });
    guidedList.appendChild(row);
  });
}

function buildPopupBubbleCard(bubble, index, options = {}) {
  const card = document.createElement("section");
  card.className = "text-box-card popup-bubble-card";
  card.dataset.popupId = bubble.id;
  const expanded = options.forceExpanded ? true : isPopupBubbleExpanded(bubble.id);
  card.classList.toggle("collapsed", !expanded);
  const popupTimeMs = popupBubbleEffectiveTimeMs(bubble);
  const displayedSize = resolvedPopupBubbleSize(bubble);
  const motionPath = popupBubbleMotionPath(bubble);
  const shots = popupBubbleShotOptions();
  const shotIds = new Set(shots.map((shot) => shot.id));
  const popupShotId = bubble.anchor_mode === "shot"
    ? (shotIds.has(bubble.shot_id) ? bubble.shot_id : (defaultPopupShotId() || ""))
    : (bubble.shot_id || "");
  const displayName = popupBubbleDisplayName(bubble, index);
  const selected = bubble.id === selectedPopupBubbleId;
  const resolvedText = popupBubbleResolvedText(bubble);
  const usesShotScoreText = bubble.anchor_mode === "shot" && Boolean(bubble.shot_id);
  const showCollapseAction = !options.forceExpanded;
  const collapseActionMarkup = showCollapseAction
    ? `<button type="button" class="scoring-shot-toggle" data-popup-action="toggle" aria-label="${expanded ? "Hide" : "Show"} popup bubble editor">${expanded ? "v" : ">"}</button>`
    : "";
  card.innerHTML = `
    <div class="text-box-card-header">
      <button type="button" class="popup-bubble-button">
        <strong>${expanded ? displayName : popupBubbleSummaryText(bubble, index)}</strong>
      </button>
      <div class="text-box-card-actions">
        <label class="check-row popup-bubble-enabled"><input type="checkbox" data-popup-field="enabled" /> <span>On</span></label>
        ${collapseActionMarkup}
        <button type="button" data-popup-action="duplicate">Duplicate</button>
        <button type="button" data-popup-action="remove">Remove</button>
      </div>
    </div>
    <div class="text-box-card-body" ${expanded ? "" : "hidden"}>
      <section class="popup-editor-section" data-popup-editor-section="content">
        <div class="section-header sub-section-header">
          <h4>Content</h4>
        </div>
        <label>Bubble name
          <input data-popup-field="name" type="text" maxlength="80" placeholder="Inherit shot name" />
        </label>
        <label data-popup-section="text">Text
          <textarea data-popup-field="text" rows="2" maxlength="500" placeholder="-0"></textarea>
        </label>
        <div class="control-grid">
          <label>Content
            <select data-popup-field="content_type">
              <option value="text">Text</option>
              <option value="image">Image</option>
              <option value="text_image">Text + Image</option>
            </select>
          </label>
          <label data-popup-media-field="image_path">Image path
            <div class="path-row">
              <input data-popup-field="image_path" type="text" placeholder="No image selected" readonly />
              <button type="button" data-popup-action="browse_image">Browse</button>
            </div>
          </label>
          <label data-popup-media-field="image_scale_mode">Scale
            <select data-popup-field="image_scale_mode">
              <option value="contain">Contain</option>
              <option value="cover">Cover</option>
            </select>
          </label>
        </div>
      </section>
      <section class="popup-editor-section" data-popup-editor-section="timing">
        <div class="section-header sub-section-header">
          <h4>Timing & Placement</h4>
        </div>
        <div class="control-grid">
          <label>Start mode
            <select data-popup-field="anchor_mode">
              <option value="time">Time</option>
              <option value="shot">Shot</option>
            </select>
          </label>
          <label>Start
            <input data-popup-field="time_s" type="number" min="0" step="0.001" />
          </label>
          <label>Shot
            <select data-popup-field="shot_id"></select>
          </label>
          <label>Duration
            <input data-popup-field="duration_s" type="number" min="0.001" step="0.001" />
          </label>
        </div>
        <div class="popup-placement-compact-grid">
          <label class="popup-placement-compact-field" title="Horizontal position. 0 is left and 1 is right.">X
            <input data-popup-field="x" type="number" min="0" max="1" step="0.0001" />
          </label>
          <label class="popup-placement-compact-field" title="Vertical position. 0 is top and 1 is bottom.">Y
            <input data-popup-field="y" type="number" min="0" max="1" step="0.0001" />
          </label>
          <label class="popup-placement-compact-field" title="Bubble width in pixels.">Width
            <input data-popup-field="width" type="number" min="0" max="1000" step="1" />
          </label>
          <label class="popup-placement-compact-field" title="Bubble height in pixels.">Height
            <input data-popup-field="height" type="number" min="0" max="1000" step="1" />
          </label>
        </div>
      </section>
      <section class="popup-editor-section" data-popup-editor-section="motion">
        <div class="section-header sub-section-header">
          <h4>Motion</h4>
        </div>
        <label class="check-row popup-motion-toggle"><input data-popup-field="follow_motion" type="checkbox" /> Enable Motion</label>
        <section class="popup-motion-guide" data-popup-motion-mode="guided" hidden>
          <div class="popup-motion-workflow-header">
            <span data-popup-motion-step-count>Finish @ ${precise(bubble.duration_ms)}s • 0 in-between points</span>
            <span data-popup-motion-selected-step>Selected: Start</span>
          </div>
          <div class="popup-motion-actions">
            <div class="popup-motion-action-grid">
              <button type="button" data-popup-action="generate_motion_path">Generate</button>
              <button type="button" data-popup-action="add_motion_step">Add Detail</button>
              <button type="button" data-popup-action="prev_motion_step">Previous Point</button>
              <button type="button" data-popup-action="next_motion_step">Next Point</button>
              <button type="button" data-popup-action="remove_motion_step">Remove Detail</button>
              <button type="button" class="danger-button" data-popup-action="clear_motion_path">Clear path</button>
            </div>
          </div>
          <p class="popup-motion-workflow-hint popup-motion-guide-hint" data-popup-motion-summary>Select Start or Finish below, then place it on the video. Generate first tries to trace the video motion and falls back to evenly spaced in-between points. Add Detail splits the largest remaining time gap.</p>
          <div class="popup-motion-path-list" data-popup-guided-point-list></div>
        </section>
      </section>
      <section class="popup-editor-section" data-popup-editor-section="style">
        <div class="section-header sub-section-header">
          <h4>Style</h4>
        </div>
        <div class="style-grid review-style-grid">
          <section class="style-card popup-style-card compact-style-card">
            <h4>Bubble Style</h4>
            <label class="color-field"><span class="style-card-label">Bg</span>
              <span class="color-control-pair">
                <button data-popup-field="background_color" class="color-swatch-button" data-color-label="Popup background" type="button"></button>
                <input class="color-hex-input" type="text" inputmode="text" spellcheck="false" value="#000000" placeholder="#000000" aria-label="Popup background hex value" />
              </span>
            </label>
            <label class="color-field"><span class="style-card-label">Text</span>
              <span class="color-control-pair">
                <button data-popup-field="text_color" class="color-swatch-button" data-color-label="Popup text" type="button"></button>
                <input class="color-hex-input" type="text" inputmode="text" spellcheck="false" value="#ffffff" placeholder="#FFFFFF" aria-label="Popup text hex value" />
              </span>
            </label>
            <label class="opacity-field"><span class="style-card-label">Background alpha</span>
              <span class="opacity-control-pair">
                <span class="opacity-percent-field">
                  <input class="opacity-percent-input" data-popup-field="opacity_percent" type="number" min="0" max="100" step="1" value="90" aria-label="Popup background alpha percent" />
                  <span class="opacity-percent-suffix">%</span>
                </span>
              </span>
            </label>
          </section>
        </div>
      </section>
    </div>
  `;
  card.classList.toggle("selected", selected);
  syncControlChecked(card.querySelector('[data-popup-field="enabled"]'), bubble.enabled);
  syncControlChecked(card.querySelector('[data-popup-field="follow_motion"]'), bubble.follow_motion);
  syncControlValue(card.querySelector('[data-popup-field="name"]'), bubble.name);
  syncControlValue(card.querySelector('[data-popup-field="text"]'), resolvedText);
  syncControlValue(card.querySelector('[data-popup-field="content_type"]'), bubble.content_type);
  syncControlValue(card.querySelector('[data-popup-field="image_scale_mode"]'), bubble.image_scale_mode);
  syncControlValue(card.querySelector('[data-popup-field="anchor_mode"]'), bubble.anchor_mode);
  syncControlValue(card.querySelector('[data-popup-field="time_s"]'), precise(popupTimeMs));
  syncControlValue(card.querySelector('[data-popup-field="shot_id"]'), popupShotId);
  syncControlValue(card.querySelector('[data-popup-field="duration_s"]'), precise(bubble.duration_ms));
  syncControlValue(card.querySelector('[data-popup-field="x"]'), formattedCoordinateValue(bubble.x));
  syncControlValue(card.querySelector('[data-popup-field="y"]'), formattedCoordinateValue(bubble.y));
  syncControlValue(card.querySelector('[data-popup-field="width"]'), displayedSize.width);
  syncControlValue(card.querySelector('[data-popup-field="height"]'), displayedSize.height);
  syncControlValue(card.querySelector('[data-popup-field="background_color"]'), bubble.background_color);
  syncControlValue(card.querySelector('[data-popup-field="text_color"]'), bubble.text_color);
  syncControlValue(card.querySelector('[data-popup-field="opacity_percent"]'), Math.round((bubble.opacity ?? 0.9) * 100));
  const imagePathInput = card.querySelector('[data-popup-field="image_path"]');
  if (imagePathInput instanceof HTMLInputElement) {
    imagePathInput.dataset.popupSourcePath = bubble.image_path || "";
    imagePathInput.title = bubble.image_path || "No image selected";
    syncControlValue(imagePathInput, bubble.image_path ? fileName(bubble.image_path) : "");
  }
  syncPopupBubbleMotionModeControls(card, bubble);
  renderPopupBubbleMotionGuide(card, bubble);
  renderPopupEditorSectionToggles(card, bubble);
  const clearMotionButton = card.querySelector('[data-popup-action="clear_motion_path"]');
  if (clearMotionButton instanceof HTMLButtonElement) {
    clearMotionButton.disabled = motionPath.length === 0;
  }
  const showTextSection = bubble.content_type !== "image";
  const showImageFields = bubble.content_type !== "text";
  card.querySelector('[data-popup-section="text"]')?.toggleAttribute("hidden", !showTextSection);
  card.querySelectorAll("[data-popup-media-field]").forEach((field) => {
    field.toggleAttribute("hidden", !showImageFields);
  });
  const shotSelect = card.querySelector('[data-popup-field="shot_id"]');
  const textArea = card.querySelector('[data-popup-field="text"]');
  if (textArea instanceof HTMLTextAreaElement) {
    textArea.disabled = usesShotScoreText && bubble.content_type === "text";
    textArea.placeholder = usesShotScoreText ? "Uses the shot score and penalties." : "-0";
    textArea.title = usesShotScoreText
      ? "This popup is tied to a shot, so its text follows that shot's score and penalties."
      : "Enter the text to show in the popup.";
  }
  if (shotSelect) {
    shotSelect.innerHTML = "";
    if (shots.length === 0) {
      const option = document.createElement("option");
      option.value = "";
      option.textContent = "No shots available";
      shotSelect.appendChild(option);
    } else {
      const defaultOption = document.createElement("option");
      defaultOption.value = "";
      defaultOption.textContent = "Time based";
      shotSelect.appendChild(defaultOption);
      shots.forEach((shot) => {
        const option = document.createElement("option");
        option.value = shot.id;
        option.textContent = shot.label;
        shotSelect.appendChild(option);
      });
      if (popupShotId) shotSelect.value = popupShotId;
    }
  }
  card.querySelectorAll("[data-popup-field]").forEach((control) => {
    const field = control.dataset.popupField || "";
    if (isColorInput(control)) return;
    const readValue = () => {
      if (control.type === "checkbox") return control.checked;
      if (field === "time_s") return Math.round((Number(control.value) || 0) * 1000);
      if (field === "duration_s") return Math.round((Number(control.value) || 0) * 1000);
      if (field === "opacity_percent") return (Number(control.value) || 0) / 100;
      if (field === "image_path") return control.dataset.popupSourcePath || "";
      return control.value;
    };
    const targetField = {
      time_s: "time_ms",
      duration_s: "duration_ms",
      opacity_percent: "opacity",
      anchor_mode: "anchor_mode",
      shot_id: "shot_id",
    }[field] || field;
    const eventName = control.type === "checkbox" ? "change" : "input";
    if (field === "shot_id" || field === "anchor_mode") {
      control.addEventListener("change", () => setPopupBubbleField(bubble.id, targetField, readValue(), { commit: true, rerender: true }));
      return;
    }
    control.addEventListener(eventName, () => setPopupBubbleField(bubble.id, targetField, readValue(), { commit: false, rerender: false }));
    control.addEventListener("change", () => setPopupBubbleField(bubble.id, targetField, readValue(), { commit: true, rerender: true }));
    control.addEventListener("blur", () => setPopupBubbleField(bubble.id, targetField, readValue(), { commit: true, rerender: true }));
  });
  const xInput = card.querySelector('[data-popup-field="x"]');
  const yInput = card.querySelector('[data-popup-field="y"]');
  [xInput, yInput].forEach((input) => {
    if (!input) return;
    input.disabled = false;
    input.placeholder = "0.5000";
  });
  const anchorModeInput = card.querySelector('[data-popup-field="anchor_mode"]');
  const timeInput = card.querySelector('[data-popup-field="time_s"]');
  const durationInput = card.querySelector('[data-popup-field="duration_s"]');
  const shotInput = card.querySelector('[data-popup-field="shot_id"]');
  if (anchorModeInput instanceof HTMLSelectElement) {
    const shotAnchored = anchorModeInput.value === "shot";
    if (timeInput) timeInput.disabled = shotAnchored;
    if (shotInput) shotInput.disabled = !shotAnchored || shots.length === 0;
    if (durationInput) durationInput.disabled = false;
  }
  if (durationInput instanceof HTMLInputElement) {
    const durationLimitMs = popupDurationLimitMsForBubble(bubble);
    if (durationLimitMs !== null) {
      durationInput.max = precise(durationLimitMs);
      durationInput.title = `Shot-linked markers are capped to ${precise(durationLimitMs)}s for this split.`;
    } else {
      durationInput.removeAttribute("max");
      durationInput.title = "Marker duration in seconds.";
    }
  }
  const selectFromCard = () => {
    selectPopupBubble(bubble.id, {
      seek: true,
      reveal: true,
      focus: false,
      activateTool: activeTool !== "markers",
      expand: false,
    });
  };
  card.querySelector(".popup-bubble-button")?.addEventListener("click", (event) => {
    event.preventDefault();
    event.stopPropagation();
    selectFromCard();
  });
  card.querySelector(".text-box-card-header")?.addEventListener("click", (event) => {
    const target = event.target;
    if (target instanceof Element && target.closest("button, input, select, textarea, label, a")) return;
    selectFromCard();
  });
  card.querySelectorAll("button[data-popup-action]").forEach((button) => {
    const preserveEditorFocus = (event) => {
      event.preventDefault();
    };
    button.addEventListener("pointerdown", preserveEditorFocus);
    button.addEventListener("mousedown", preserveEditorFocus);
  });
  card.querySelector('[data-popup-action="toggle"]')?.addEventListener("click", (event) => {
    event.preventDefault();
    event.stopPropagation();
    event.stopImmediatePropagation();
    preserveElementViewportAnchor(
      () => document.querySelector(`.popup-bubble-card[data-popup-id="${bubble.id}"]`),
      () => {
        selectPopupBubble(bubble.id, {
          seek: true,
          reveal: false,
          focus: false,
          activateTool: activeTool !== "markers",
          expand: false,
          rerender: false,
        });
        setPopupBubbleExpanded(bubble.id, !isPopupBubbleExpanded(bubble.id));
        renderPopupEditors();
      },
    );
  });
  card.querySelector('[data-popup-action="duplicate"]')?.addEventListener("click", (event) => {
    event.preventDefault();
    event.stopPropagation();
    duplicatePopupBubble(bubble.id);
  });
  card.querySelector('[data-popup-action="clear_motion_path"]')?.addEventListener("click", (event) => {
    event.preventDefault();
    event.stopPropagation();
    clearPopupBubbleMotionPath(bubble.id);
  });
  card.querySelector('[data-popup-action="generate_motion_path"]')?.addEventListener("click", (event) => {
    event.preventDefault();
    event.stopPropagation();
    generatePopupBubbleMotionPath(bubble.id);
  });
  card.querySelector('[data-popup-action="add_motion_step"]')?.addEventListener("click", (event) => {
    event.preventDefault();
    event.stopPropagation();
    addPopupBubbleKeyframeAtPlayhead(bubble.id);
  });
  card.querySelector('[data-popup-action="prev_motion_step"]')?.addEventListener("click", (event) => {
    event.preventDefault();
    event.stopPropagation();
    jumpPopupBubbleKeyframe(bubble.id, -1);
  });
  card.querySelector('[data-popup-action="next_motion_step"]')?.addEventListener("click", (event) => {
    event.preventDefault();
    event.stopPropagation();
    jumpPopupBubbleKeyframe(bubble.id, 1);
  });
  card.querySelector('[data-popup-action="remove_motion_step"]')?.addEventListener("click", (event) => {
    event.preventDefault();
    event.stopPropagation();
    if (selectedPopupKeyframeOffsetMs > 0) deletePopupBubbleKeyframe(bubble.id, selectedPopupKeyframeOffsetMs);
  });
  card.querySelector('[data-popup-action="browse_image"]')?.addEventListener("click", async (event) => {
    event.preventDefault();
    event.stopPropagation();
    const imageInput = card.querySelector('[data-popup-field="image_path"]');
    if (!(imageInput instanceof HTMLInputElement)) return;
    await pickPathForElement("popup_image", imageInput, `popup-image-${bubble.id}`, async (path) => {
      if (!path) return;
      imageInput.dataset.popupSourcePath = path;
      imageInput.title = path;
      syncControlValue(imageInput, fileName(path));
      setPopupBubbleField(bubble.id, "image_path", path, { commit: true, rerender: true });
    });
  });
  card.querySelector('[data-popup-action="remove"]')?.addEventListener("click", (event) => {
    event.preventDefault();
    event.stopPropagation();
    removePopupBubble(bubble.id);
  });
  bindOverlayColorInput(card.querySelector('[data-popup-field="background_color"]'));
  bindOverlayColorInput(card.querySelector('[data-popup-field="text_color"]'));
  return card;
}

function buildPopupMarkerRow(bubble, index) {
  const row = document.createElement("section");
  row.className = "popup-marker-row";
  row.dataset.popupId = bubble.id;
  row.classList.toggle("selected", bubble.id === selectedPopupBubbleId);
  const typeClass = bubble.anchor_mode === "shot" && bubble.shot_id ? "shot-linked" : "time-based";
  const typeLabel = typeClass === "shot-linked" ? "Shot-linked" : "Time";
  row.innerHTML = `
    <div class="popup-marker-row-main">
      <button type="button" class="popup-marker-select">
        <span class="popup-marker-title">
          <strong>${popupBubbleDisplayName(bubble, index)}</strong>
          <span class="popup-marker-type-chip ${typeClass}">${typeLabel}</span>
        </span>
      </button>
      <div class="popup-marker-meta">${popupBubbleSummaryText(bubble, index)}</div>
    </div>
    <div class="popup-marker-actions">
      <label class="check-row popup-bubble-enabled"><input type="checkbox" data-popup-field="enabled" /> <span>On</span></label>
    </div>
  `;
  syncControlChecked(row.querySelector('[data-popup-field="enabled"]'), bubble.enabled);
  const selectMarkerRow = () => {
    selectPopupBubble(bubble.id, { seek: true, reveal: false, focus: false, activateTool: true, expand: false });
  };
  row.addEventListener("click", (event) => {
    const target = event.target;
    if (target instanceof Element && target.closest("button, input, select, textarea, label, a")) return;
    selectMarkerRow();
  });
  row.querySelector(".popup-marker-select")?.addEventListener("click", () => {
    selectMarkerRow();
  });
  row.querySelector('[data-popup-field="enabled"]')?.addEventListener("change", (event) => {
    setPopupBubbleField(bubble.id, "enabled", event.target.checked, { commit: true, rerender: true });
  });
  return row;
}

function buildPopupFloatingEditor(bubble, index) {
  const wrapper = document.createElement("section");
  wrapper.className = "text-box-manager popup-inline-editor";
  const shotLinked = bubble.anchor_mode === "shot" && Boolean(bubble.shot_id);
  wrapper.innerHTML = `
    <div class="section-header">
      <div class="popup-floating-header">
        <h3>Marker Editor</h3>
        <p>${popupBubbleDisplayName(bubble, index)} · ${popupBubbleSummaryText(bubble, index)}</p>
      </div>
    </div>
    <div class="popup-inline-editor-body">
      <div class="popup-floating-stepper four-up">
        <button type="button" data-popup-floating-action="prev" ${shotLinked ? "" : "disabled"}>Previous Shot</button>
        <button type="button" data-popup-floating-action="next" ${shotLinked ? "" : "disabled"}>Next Shot</button>
        <button type="button" data-popup-floating-action="duplicate">Duplicate</button>
        <button type="button" data-popup-floating-action="remove">Delete</button>
      </div>
      <div class="popup-floating-body" data-popup-editor-slot="form"></div>
    </div>
  `;
  wrapper.querySelector('[data-popup-floating-action="prev"]')?.addEventListener("click", () => stepShotLinkedPopupBubble(-1));
  wrapper.querySelector('[data-popup-floating-action="next"]')?.addEventListener("click", () => stepShotLinkedPopupBubble(1));
  wrapper.querySelector('[data-popup-floating-action="duplicate"]')?.addEventListener("click", () => duplicatePopupBubble(bubble.id));
  wrapper.querySelector('[data-popup-floating-action="remove"]')?.addEventListener("click", () => removePopupBubble(bubble.id));
  const slot = wrapper.querySelector('[data-popup-editor-slot="form"]');
  if (slot instanceof HTMLElement) slot.appendChild(buildPopupBubbleCard(bubble, index, { forceExpanded: true }));
  return wrapper;
}

function renderPopupFloatingEditor(selected, originalIndexById) {
  const container = $("popup-floating-editor");
  if (!(container instanceof HTMLElement)) return;
  if (!selected) {
    popupEditorVisible = false;
    popupEditorCollapsed = false;
  }
  const shouldShow = activeTool === "markers" && popupEditorVisible && Boolean(selected);
  container.hidden = !shouldShow;
  container.className = "popup-floating-editor";
  container.innerHTML = "";
  if (!shouldShow || !selected) return;
  container.appendChild(buildPopupFloatingEditor(selected, originalIndexById.get(selected.id) ?? 0));
}

function currentPrimaryVideoPositionMs() {
  return markersPane?.currentPrimaryVideoPositionMs() ?? 0;
}

function popupBubbleFilterMatches(bubble, positionMs = currentPrimaryVideoPositionMs()) {
  return markersPane?.popupBubbleFilterMatches(bubble, positionMs) ?? true;
}

function filteredPopupBubbles(bubbles = popupBubbles()) {
  return markersPane?.filteredPopupBubbles(bubbles) || [];
}

function sortedPopupBubblesForTimeline(bubbles = filteredPopupBubbles()) {
  return markersPane?.sortedPopupBubblesForTimeline(bubbles) || [];
}

function setPopupAuthoringCollapsed(collapsed, { persistUiState = true, rerender = true } = {}) {
  return markersPane?.setPopupAuthoringCollapsed(collapsed, { persistUiState, rerender });
}

function renderPopupAuthoringControls(allBubbles, visibleBubbles) {
  if (!VALID_POPUP_FILTER_MODES.has(popupFilterMode)) popupFilterMode = "all";
  const bubbleList = $("popup-marker-list");
  const bubbleListSection = bubbleList?.closest(".popup-list-section-unified") || null;
  const paneStatus = $("popup-pane-status");
  const listStatus = $("popup-list-status");
  const selected = selectedPopupBubble();
  const hasSelectedBubble = Boolean(selected);
  const workbenchShown = markersWorkbenchShown();
  if (bubbleList instanceof HTMLElement) bubbleList.hidden = false;
  if (bubbleListSection instanceof HTMLElement) {
    bubbleListSection.hidden = workbenchShown;
    bubbleListSection.style.display = "";
  }
  const enabledCount = allBubbles.filter((bubble) => bubble.enabled).length;
  if (paneStatus instanceof HTMLElement) paneStatus.textContent = `${enabledCount} enabled`;
  const editSelectedButton = $("popup-edit-selected");
  if (editSelectedButton instanceof HTMLButtonElement) {
    editSelectedButton.disabled = false;
    const expanded = workbenchShown;
    editSelectedButton.textContent = expanded ? "Collapse" : "Edit";
    editSelectedButton.title = expanded
      ? "Close the marker editor"
      : (hasSelectedBubble ? "Open the selected marker in the workbench" : "Open the marker workbench");
    editSelectedButton.setAttribute("aria-label", editSelectedButton.title);
  }
  const selectedEditorPanel = $("popup-selected-editor-panel");
  if (selectedEditorPanel instanceof HTMLElement) selectedEditorPanel.hidden = !workbenchShown;
  if (listStatus instanceof HTMLElement) {
    listStatus.textContent = visibleBubbles.length === 0 ? "No markers shown." : `${visibleBubbles.length} shown`;
  }
}

function readPopupTemplatePayload() {
  const current = currentPopupTemplate();
  return normalizePopupTemplate({
    enabled: $("popup-template-enabled")?.checked ?? current.enabled,
    content_type: $("popup-template-content-type")?.value || current.content_type || "text",
    text_source: $("popup-template-text-source")?.value || current.text_source || "score",
    duration_ms: Math.max(1, Math.round((Number($("popup-template-duration-s")?.value || (current.duration_ms / 1000) || 1) || 1) * 1000)),
    use_shot_split_duration: current.use_shot_split_duration,
    quadrant: $("popup-template-quadrant")?.value || current.quadrant || "middle_middle",
    width: Number($("popup-template-width")?.value || current.width || 0),
    height: Number($("popup-template-height")?.value || current.height || 0),
    follow_motion: $("popup-template-follow-motion")?.checked ?? current.follow_motion,
    motion_mode: $("popup-template-motion-mode")?.value || current.motion_mode,
    background_color: $("popup-template-background-color")?.value || current.background_color,
    text_color: $("popup-template-text-color")?.value || current.text_color,
    opacity: clamp((readNumberSetting("popup-template-opacity", (current.opacity ?? 0.9) * 100) / 100), 0, 1),
  });
}

function renderPopupTimeline(allBubbles = popupBubbles(), visibleBubbles = filteredPopupBubbles(allBubbles)) {
  const strip = $("popup-timeline-strip");
  if (!(strip instanceof HTMLElement)) return;
  const sortedBubbles = sortedPopupBubblesForTimeline(visibleBubbles);
  const totalMs = Math.max(1, durationMs());
  const playheadMs = clamp(currentPrimaryVideoPositionMs(), 0, totalMs);
  strip.innerHTML = "";
  const playhead = document.createElement("div");
  playhead.className = "popup-timeline-playhead";
  playhead.style.left = `${clamp((playheadMs / totalMs) * 100, 0, 100)}%`;
  strip.appendChild(playhead);
  if (sortedBubbles.length === 0) {
    const empty = document.createElement("div");
    empty.className = "popup-timeline-empty";
    empty.textContent = allBubbles.length === 0 ? "No popups yet." : "No popups match the current filter.";
    strip.appendChild(empty);
    return;
  }
  const originalIndexById = new Map(allBubbles.map((bubble, index) => [bubble.id, index]));
  sortedBubbles.forEach((bubble, index) => {
    const { startMs, endMs } = popupBubbleVisibleWindow(bubble);
    const leftPercent = clamp((startMs / totalMs) * 100, 0, 100);
    const rightPercent = clamp((endMs / totalMs) * 100, leftPercent, 100);
    const widthPercent = Math.max(0.8, rightPercent - leftPercent);
    const bubbleBackground = String(bubble.background_color || "#4B5563");
    const bubbleTextColor = String(bubble.text_color || "#F9FAFB");
    const bubbleOpacity = clamp(Number(bubble.opacity ?? 0.9) || 0.9, 0.18, 1);
    const bar = document.createElement("button");
    bar.type = "button";
    bar.className = "popup-timeline-bar";
    bar.classList.toggle("enabled", Boolean(bubble.enabled));
    bar.classList.toggle("disabled", !bubble.enabled);
    bar.classList.toggle("selected", bubble.id === selectedPopupBubbleId);
    bar.dataset.popupId = bubble.id;
    bar.style.left = `${leftPercent}%`;
    bar.style.top = `${0.35 + ((index % 3) * 1.1)}rem`;
    bar.style.width = `${Math.min(widthPercent, 100 - leftPercent)}%`;
    bar.style.background = rgba(bubbleBackground, bubble.enabled ? bubbleOpacity : Math.max(0.18, bubbleOpacity * 0.45));
    bar.style.color = bubbleTextColor;
    bar.style.borderColor = bubble.id === selectedPopupBubbleId ? "var(--accent)" : rgba(bubbleTextColor, bubble.enabled ? 0.42 : 0.24);
    bar.title = `${popupBubbleDisplayName(bubble, originalIndexById.get(bubble.id) ?? index)} ${seconds(startMs)}s-${seconds(endMs)}s`;
    bar.textContent = popupBubbleDisplayName(bubble, originalIndexById.get(bubble.id) ?? index);
    bar.addEventListener("click", () => {
      selectPopupBubble(bubble.id, { seek: true, reveal: true, focus: false, activateTool: false, expand: false });
    });
    strip.appendChild(bar);
  });
}

function setPopupFilterMode(nextMode) {
  popupFilterMode = VALID_POPUP_FILTER_MODES.has(nextMode) ? nextMode : "all";
  window.localStorage.setItem("splitshot.popupFilterMode", popupFilterMode);
  renderPopupEditors();
}

function setPopupEditorVisible(visible, { rerender = true } = {}) {
  popupEditorVisible = Boolean(visible);
  if (!popupEditorVisible) popupEditorCollapsed = false;
  if (rerender) renderPopupEditors();
}

function setPopupEditorCollapsed(collapsed, { rerender = true } = {}) {
  popupEditorCollapsed = Boolean(collapsed);
  if (rerender) renderPopupEditors();
}

function openSelectedPopupEditor({ focus = false } = {}) {
  popupEditorVisible = false;
  popupEditorCollapsed = false;
  setActiveTool("markers", { collapseExpandedLayout: false });
  setMarkersExpanded(true);
  if (focus) {
    window.requestAnimationFrame(() => {
      const focusTarget = document.querySelector("#markers-workbench-editor input, #markers-workbench-editor textarea, #markers-workbench-editor select, #markers-workbench-list .popup-marker-select")
        || $("popup-add-bubble-workbench");
      if (focusTarget instanceof HTMLElement) focusTarget.focus();
    });
  }
  return true;
}

function toggleSelectedPopupEditor({ focus = false } = {}) {
  if (markersWorkbenchShown()) {
    setMarkersExpanded(false);
    restorePopupWorkbenchLayout();
    return true;
  }
  return openSelectedPopupEditor({ focus });
}

function renderMarkersWorkbench(allBubbles, visibleBubbles, selected, originalIndexById) {
  const section = $("markers-workbench");
  const body = section?.querySelector?.(".markers-workbench-body") || null;
  const list = $("markers-workbench-list");
  const editor = $("markers-workbench-editor");
  const status = $("markers-workbench-status");
  const listStatus = $("markers-workbench-list-status");
  const editorStatus = $("markers-workbench-editor-status");
  const filter = $("markers-workbench-filter");
  const hasBubbles = allBubbles.length > 0;
  const hasSelectedBubble = Boolean(selected);
  if (section instanceof HTMLElement) section.hidden = !markersWorkbenchShown();
  if (body instanceof HTMLElement) body.classList.toggle("defaults-collapsed", popupAuthoringCollapsed);
  if (filter instanceof HTMLSelectElement) syncControlValue(filter, popupFilterMode);
  if (status instanceof HTMLElement) status.textContent = `${visibleBubbles.length} shown`;
  if (listStatus instanceof HTMLElement) {
    listStatus.textContent = allBubbles.length === 0
      ? "No markers yet."
      : visibleBubbles.length === 0
        ? "No markers match the current filter."
        : `${visibleBubbles.length} shown`;
  }
  if (editorStatus instanceof HTMLElement) {
    editorStatus.textContent = selected
      ? popupBubbleSummaryText(selected, Math.max(0, allBubbles.findIndex((bubble) => bubble.id === selected.id)))
      : (hasBubbles ? "No marker selected." : "Nothing to edit yet.");
  }
  ["popup-prev-workbench", "popup-next-workbench"].forEach((id) => {
    const button = $(id);
    if (button instanceof HTMLButtonElement) button.disabled = !hasBubbles;
  });
  const addSelectedShotButton = $("popup-add-selected-shot-workbench");
  if (addSelectedShotButton instanceof HTMLButtonElement) addSelectedShotButton.disabled = !selectedShotId;
  if (!(list instanceof HTMLElement) || !(editor instanceof HTMLElement)) return;
  withPreservedScrollState([list, editor], () => {
    list.innerHTML = "";
    if (!hasBubbles) {
      const empty = document.createElement("div");
      empty.className = "markers-workbench-list-empty";
      empty.textContent = "No markers yet.";
      list.appendChild(empty);
    } else if (visibleBubbles.length === 0) {
      const empty = document.createElement("div");
      empty.className = "markers-workbench-list-empty";
      empty.textContent = "No markers match the current filter.";
      list.appendChild(empty);
    } else {
      visibleBubbles.forEach((bubble, index) => {
        list.appendChild(buildPopupMarkerRow(bubble, originalIndexById.get(bubble.id) ?? index));
      });
    }
    editor.innerHTML = "";
    if (!selected) {
      const empty = document.createElement("div");
      empty.className = "markers-workbench-editor-empty";
      empty.textContent = hasBubbles
        ? "Select a marker from the list to edit it here."
        : "Add a time marker or import shots to start editing.";
      editor.appendChild(empty);
      return;
    }
    editor.appendChild(buildPopupBubbleCard(selected, originalIndexById.get(selected.id) ?? 0, { forceExpanded: true }));
  });
}

function selectAdjacentPopupBubble(direction) {
  const bubbles = sortedPopupBubblesForTimeline(filteredPopupBubbles());
  if (bubbles.length === 0) {
    setStatus("No PopUp bubbles match the current filter.");
    return false;
  }
  const selectedIndex = bubbles.findIndex((bubble) => bubble.id === selectedPopupBubbleId);
  let nextIndex = selectedIndex;
  if (selectedIndex < 0) nextIndex = direction < 0 ? bubbles.length - 1 : 0;
  else nextIndex = (selectedIndex + direction + bubbles.length) % bubbles.length;
  return selectPopupBubble(bubbles[nextIndex].id, { seek: true, reveal: true, focus: false, activateTool: true, expand: false });
}

function stepShotLinkedPopupBubble(direction) {
  const bubbles = filteredPopupBubbles(popupBubbles()).filter((bubble) => bubble.anchor_mode === "shot" && bubble.shot_id);
  if (bubbles.length === 0) return false;
  const current = selectedPopupBubble();
  const currentIndex = bubbles.findIndex((bubble) => bubble.id === current?.id);
  const nextIndex = currentIndex < 0 ? 0 : clamp(currentIndex + direction, 0, bubbles.length - 1);
  return selectPopupBubble(bubbles[nextIndex].id, { seek: true, reveal: true, focus: false, activateTool: true, expand: false });
}

function renderPopupEditors() {
  const markerList = $("popup-marker-list");
  if (!markerList) return;
  const bubbles = popupBubbles();
  const visibleBubbles = filteredPopupBubbles(bubbles);
  const validBubbleIds = new Set(bubbles.map((bubble) => bubble.id));
  [...popupBubbleExpansion.keys()].forEach((bubbleId) => {
    if (!validBubbleIds.has(bubbleId)) popupBubbleExpansion.delete(bubbleId);
  });
  if (selectedPopupBubbleId && !validBubbleIds.has(selectedPopupBubbleId)) {
    selectedPopupBubbleId = null;
  }
  const originalIndexById = new Map(bubbles.map((bubble, index) => [bubble.id, index]));
  const selected = selectedPopupBubble();
  if (!selected) {
    popupEditorVisible = false;
    popupEditorCollapsed = false;
  }
  renderPopupAuthoringControls(bubbles, visibleBubbles);
  withPreservedScrollState([markerList], () => {
    markerList.innerHTML = "";
    if (bubbles.length === 0) {
      const empty = document.createElement("div");
      empty.className = "hint";
      empty.textContent = "No markers yet.";
      markerList.appendChild(empty);
      return;
    }
    if (visibleBubbles.length === 0) {
      const empty = document.createElement("div");
      empty.className = "hint";
      empty.textContent = "No markers match the current filter.";
      markerList.appendChild(empty);
      return;
    }
    visibleBubbles.forEach((bubble, index) => {
      markerList.appendChild(buildPopupMarkerRow(bubble, originalIndexById.get(bubble.id) ?? index));
    });
  });
  renderMarkersWorkbench(bubbles, visibleBubbles, selected, originalIndexById);
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
  return layoutRuntime.layoutViewportHeight();
}

function alignToEdge(value) {
  if (value === "left" || value === "top") return "flex-start";
  if (value === "middle") return "center";
  return "flex-end";
}

function setCssPixels(name, value) {
  return layoutRuntime.setCssPixels(name, value);
}

function currentPreviewAspectRatio(video = $("primary-video")) {
  return layoutRuntime.currentPreviewAspectRatio(video);
}

function recommendedReviewLayoutSizes(viewportWidth = window.innerWidth, viewportHeight = layoutViewportHeight()) {
  return layoutRuntime.recommendedReviewLayoutSizes(viewportWidth, viewportHeight);
}

function maybeApplyRecommendedLayout({ force = false } = {}) {
  return layoutRuntime.maybeApplyRecommendedLayout({ force });
}

function popupWorkbenchTargetHeight(viewportHeight = layoutViewportHeight()) {
  return layoutRuntime.popupWorkbenchTargetHeight(viewportHeight);
}

function capturePopupWorkbenchRestoreState() {
  return layoutRuntime.capturePopupWorkbenchRestoreState();
}

function restorePopupWorkbenchLayout({ persistUiState = true, restoreWaveformExpanded = true } = {}) {
  return layoutRuntime.restorePopupWorkbenchLayout({ persistUiState, restoreWaveformExpanded });
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
  return layoutRuntime.applyLayoutState();
}

function persistLayoutSize(key, value, { renderWaveformNow = true } = {}) {
  return layoutRuntime.persistLayoutSize(key, value, { renderWaveformNow });
}

function previewLayoutSize(key, value) {
  return layoutRuntime.previewLayoutSize(key, value);
}

function toggleLayoutLock() {
  return layoutRuntime.toggleLayoutLock();
}

function resetLayout() {
  return layoutRuntime.resetLayout();
}

function beginLayoutResize(kind, event) {
  return layoutRuntime.beginLayoutResize(kind, event);
}

function moveLayoutResize(event) {
  return layoutRuntime.moveLayoutResize(event);
}

function endLayoutResize(event) {
  return layoutRuntime.endLayoutResize(event);
}

function normalizeSurfaceId(surface) {
  const normalized = String(surface || "landing");
  return ["landing", "single", "multi", "library"].includes(normalized) ? normalized : "landing";
}

function setActiveSurface(surface, { persist = true, openPanel = true } = {}) {
  activeSurface = normalizeSurfaceId(surface);
  const landingPage = $("landing-page");
  const isLanding = activeSurface === "landing";
  landingPageVisible = isLanding;
  if (landingPage) {
    if (isLanding) landingPage.removeAttribute("hidden");
    else landingPage.setAttribute("hidden", "");
  }
  if (persist) window.localStorage.setItem("splitshot.activeSurface", activeSurface);
  if (isLanding) {
    renderRecentActivity();
    void refreshLandingRecentActivity();
  }
  automationPanelOpen = Boolean(openPanel);
  const surfaceToView = { landing: "landing", single: "stage", multi: "match", library: "library" };
  setActiveView(surfaceToView[activeSurface] || "stage");
  if (activeSurface === "single") {
    setActiveTool(activeTool || "project", { persistUiState: false });
    updateStageEmptyState();
  } else if (activeSurface === "multi") {
    void refreshStageComposite();
  } else if (activeSurface === "library") {
    automationStale.library = !(libraryView?.libraryAutoRefreshEnabled?.() ?? true);
    if (libraryView?.libraryAutoRefreshEnabled?.() ?? true) void refreshPerformanceLibrary();
    else renderAutomationSurface();
  }
}

function renderRecentActivity() {
  const list = $("landing-recent-list");
  if (!list || !landingRecentLoaded) return;
  if (landingRecentItems.length === 0) {
    list.innerHTML = '<p class="landing-empty-hint">No recent stages. Create a new stage or open an existing project.</p>';
    return;
  }
  list.innerHTML = landingRecentItems.map((item) => {
    const meta = [item.date, item.type].filter(Boolean).join(" · ");
    return `
    <div class="landing-recent-item" data-recent-surface="${item.surface || ''}" data-recent-path="${item.path || ''}">
      <div class="landing-recent-thumb">${item.surface === 'single' ? '🎬' : item.surface === 'multi' ? '🏆' : '📊'}</div>
      <div class="landing-recent-info">
        <div class="landing-recent-name">${escapeHtml(item.name || 'Untitled')}</div>
        <div class="landing-recent-meta">${escapeHtml(meta)}</div>
      </div>
    </div>
  `;
  }).join('');
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}

function normalizeLandingRecentSurface(surface, type) {
  const normalizedSurface = String(surface || "").trim().toLowerCase();
  if (["single", "multi", "library"].includes(normalizedSurface)) return normalizedSurface;
  const normalizedType = String(type || "").trim().toLowerCase();
  if (normalizedType === "stage" || normalizedType === "single") return "single";
  if (normalizedType === "match" || normalizedType === "multi") return "multi";
  if (normalizedType === "library") return "library";
  return "";
}

function landingRecentTypeLabel(type, surface = "") {
  const normalizedType = String(type || "").trim().toLowerCase();
  if (normalizedType === "stage" || normalizedType === "single") return "Stage";
  if (normalizedType === "match" || normalizedType === "multi") return "Match";
  if (normalizedType === "library") return "Performance Library";
  if (surface === "single") return "Stage";
  if (surface === "multi") return "Match";
  if (surface === "library") return "Performance Library";
  return "";
}

function formatLandingRecentDate(value) {
  const normalized = String(value || "").trim();
  if (!normalized) return "";
  const parsed = new Date(normalized);
  if (Number.isNaN(parsed.getTime())) return normalized;
  return parsed.toLocaleDateString();
}

function landingRecentItemKey(item = {}) {
  const path = String(item.path || "").trim();
  if (path) return path;
  return `${item.surface || ""}:${item.type || ""}:${item.name || ""}`;
}

function normalizeLandingRecentItems(items = []) {
  const seenKeys = new Set();
  return (Array.isArray(items) ? items : [])
    .map((item) => {
      const surface = normalizeLandingRecentSurface(item?.surface, item?.type);
      const typeLabel = landingRecentTypeLabel(item?.type, surface);
      if (surface !== "single" && typeLabel !== "Stage") return null;
      const normalizedItem = {
        name: String(item?.name || "").trim() || "Untitled",
        path: String(item?.path || item?.project_path || item?.workspace_path || "").trim(),
        surface: surface || "single",
        type: typeLabel || "Stage",
        date: formatLandingRecentDate(item?.date || item?.last_opened || item?.updated_at || ""),
      };
      const itemKey = landingRecentItemKey(normalizedItem);
      if (seenKeys.has(itemKey)) return null;
      seenKeys.add(itemKey);
      return normalizedItem;
    })
    .filter(Boolean)
    .slice(0, 10);
}

async function refreshLandingRecentActivity() {
  const list = $("landing-recent-list");
  if (!list) return;
  const requestId = ++landingRecentRequestSequence;
  const result = await callApi("/api/landing/recent", {});
  if (requestId !== landingRecentRequestSequence) return;
  if (!result || !Array.isArray(result.recent)) return;
  landingRecentItems = normalizeLandingRecentItems(result.recent);
  landingRecentLoaded = true;
  renderRecentActivity();
}

function recordRecentActivity(name, surface, type, path) {
  const key = "splitshot.recentActivity";
  const items = JSON.parse(window.localStorage.getItem(key) || "[]");
  const date = new Date().toLocaleDateString();
  const filtered = items.filter(i => !(i.name === name && i.surface === surface));
  filtered.unshift({ name, surface, type, path, date });
  window.localStorage.setItem(key, JSON.stringify(filtered.slice(0, 15)));
}

function currentStageScopeId() {
  return state?.active_stage_id || state?.project?.id || "";
}

function currentWorkspaceStageId() {
  return selectedStageCompositeStageId
    || state?.active_stage_id
    || state?.workspace_stage_entries?.[0]?.stage_id
    || "";
}

function renderJsonDetail(elementId, payload, fallback = "") {
  const target = $(elementId);
  if (!target) return;
  target.textContent = payload ? JSON.stringify(payload, null, 2) : fallback;
}

matchView = createMatchView({
  $,
  documentObject: document,
  windowObject: window,
  getState: () => state,
  getCurrentWorkspaceStageId: () => currentWorkspaceStageId(),
  getStageCompositeClips: () => stageCompositeClips,
  setSelectedStageCompositeStageId: (value) => {
    selectedStageCompositeStageId = value;
  },
  syncControlValue,
  callApi,
  refresh,
  refreshStageComposite,
  ensureCompositeOutputProfile,
  renderJsonDetail,
  fileName,
  activity,
});

libraryView = createLibraryView({
  $,
  documentObject: document,
  windowObject: window,
  getLibrary: () => automationLibrary,
  getSelectedLibraryRecord: () => selectedLibraryRecord,
  setSelectedLibraryRecord: (value) => {
    syncSelectedLibraryRecord(value);
  },
  callApi,
  renderJsonDetail,
  activity,
});

function renderSurfaceContext() {
  return;
}

function automationProfilesForCurrentScope() {
  const fallbackProfiles = Array.isArray(state?.output_profiles) ? state.output_profiles : [];
  const allProfiles = automationProfiles.length ? automationProfiles : fallbackProfiles;
  const scopeId = currentStageScopeId();
  return allProfiles.filter((profile) => {
    if (!profile) return false;
    if (profile.scope_type && profile.scope_type !== "stage") return false;
    return !scopeId || profile.scope_id === scopeId;
  });
}

function activeAutomationProfile(profiles = automationProfilesForCurrentScope()) {
  if (!profiles.length) {
    selectedAutomationOutputProfileId = null;
    return null;
  }
  const selected = profiles.find((profile) => profile.output_id === selectedAutomationOutputProfileId);
  if (selected) return selected;
  selectedAutomationOutputProfileId = profiles[0]?.output_id || null;
  return profiles[0] || null;
}

function metricCaptionPresetSelection(profile = {}) {
  const preset = profile?.metric_caption_preset;
  if (typeof preset === "string" && preset) return preset;
  if (!preset || typeof preset !== "object") return "none";
  if (typeof preset.preset === "string" && preset.preset) return preset.preset;
  const enabledFields = Array.isArray(preset.enabled_fields) ? preset.enabled_fields : [];
  if (!enabledFields.length) return "none";
  if (enabledFields.includes("split_times") && enabledFields.includes("hit_factor")) return "full";
  if (enabledFields.includes("split_times")) return "splits";
  if (enabledFields.includes("hit_factor") || enabledFields.includes("penalties")) return "score";
  return "full";
}

function metricCaptionPosition(profile = {}) {
  const preset = profile?.metric_caption_preset;
  return (preset && typeof preset === "object" && preset.position) || "bottom_right";
}

function runWindowLeadInSeconds(profile = {}) {
  const preset = profile?.metric_caption_preset;
  const raw = preset && typeof preset === "object" ? Number(preset.lead_in_padding_ms) : NaN;
  return Number.isFinite(raw) ? raw / 1000 : 1;
}

function runWindowTailSeconds(profile = {}) {
  const preset = profile?.metric_caption_preset;
  const raw = preset && typeof preset === "object" ? Number(preset.tail_padding_ms) : NaN;
  return Number.isFinite(raw) ? raw / 1000 : 2;
}

const LEAD_IN_CARD_STYLE_DEFAULTS = Object.freeze({
  stage_info: Object.freeze({
    show_match: true,
    show_stage: true,
    show_shooter: false,
    show_division: true,
    show_classification: false,
    show_date: false,
  }),
  competitor: Object.freeze({
    show_match: false,
    show_stage: true,
    show_shooter: true,
    show_division: true,
    show_classification: true,
    show_date: false,
  }),
});

function leadInCardPayload(profile = {}) {
  const leadIn = profile?.lead_in_card;
  return leadIn && typeof leadIn === "object" ? leadIn : {};
}

function leadInCardStyle(profile = {}) {
  const leadIn = leadInCardPayload(profile);
  if (typeof leadIn === "string") return leadIn;
  if (!leadIn || typeof leadIn !== "object") return "none";
  return leadIn.style || leadIn.kind || "none";
}

function leadInCardDurationSeconds(profile = {}) {
  const leadIn = leadInCardPayload(profile);
  const raw = leadIn && typeof leadIn === "object" ? Number(leadIn.duration_s) : NaN;
  return Number.isFinite(raw) ? raw : 2;
}

function leadInCardAnimation(profile = {}) {
  const leadIn = leadInCardPayload(profile);
  const animation = String(leadIn.animation || "static").trim().toLowerCase();
  return ["static", "fade", "slide_up"].includes(animation) ? animation : "static";
}

function leadInCardLogoPath(profile = {}) {
  const leadIn = leadInCardPayload(profile);
  return String(leadIn.logo_path || "").trim();
}

function leadInCardLogoScalePercent(profile = {}) {
  const leadIn = leadInCardPayload(profile);
  const raw = Number(leadIn.logo_scale_percent);
  return Number.isFinite(raw) ? clampNumber(raw, 20, 400) : 100;
}

function leadInCardFieldEnabled(profile = {}, field) {
  const leadIn = leadInCardPayload(profile);
  if (typeof leadIn[field] === "boolean") return leadIn[field];
  const style = leadInCardStyle(profile);
  return Boolean(LEAD_IN_CARD_STYLE_DEFAULTS[style]?.[field]);
}

function leadInCardTextValue(profile = {}, field) {
  const leadIn = leadInCardPayload(profile);
  if (field === "custom_title") return String(leadIn.custom_title || leadIn.title || "");
  if (field === "custom_subtitle") return String(leadIn.custom_subtitle || leadIn.subtitle || "");
  return "";
}

function buildLeadInCardPayload(profile = {}) {
  const style = $("hook-lead-in-style")?.value || "none";
  if (style === "none") return null;
  return {
    style,
    duration_s: Number($("hook-lead-in-duration")?.value || leadInCardDurationSeconds(profile) || 2),
    animation: $("hook-lead-in-animation")?.value || leadInCardAnimation(profile),
    show_match: $("hook-lead-in-show-match")?.checked ?? leadInCardFieldEnabled(profile, "show_match"),
    show_stage: $("hook-lead-in-show-stage")?.checked ?? leadInCardFieldEnabled(profile, "show_stage"),
    show_shooter: $("hook-lead-in-show-shooter")?.checked ?? leadInCardFieldEnabled(profile, "show_shooter"),
    show_division: $("hook-lead-in-show-division")?.checked ?? leadInCardFieldEnabled(profile, "show_division"),
    show_classification: $("hook-lead-in-show-classification")?.checked ?? leadInCardFieldEnabled(profile, "show_classification"),
    show_date: $("hook-lead-in-show-date")?.checked ?? leadInCardFieldEnabled(profile, "show_date"),
    custom_title: ($("hook-lead-in-custom-title")?.value || "").trim(),
    custom_subtitle: ($("hook-lead-in-custom-subtitle")?.value || "").trim(),
    logo_path: ($("hook-lead-in-logo-path")?.value || "").trim(),
    logo_scale_percent: Number(
      $("hook-lead-in-logo-scale")?.value || leadInCardLogoScalePercent(profile) || 100,
    ),
  };
}

function applyLeadInCardStyleDefaults(style) {
  const defaults = LEAD_IN_CARD_STYLE_DEFAULTS[style] || {};
  [
    ["hook-lead-in-show-match", "show_match"],
    ["hook-lead-in-show-stage", "show_stage"],
    ["hook-lead-in-show-shooter", "show_shooter"],
    ["hook-lead-in-show-division", "show_division"],
    ["hook-lead-in-show-classification", "show_classification"],
    ["hook-lead-in-show-date", "show_date"],
  ].forEach(([controlId, field]) => {
    const control = $(controlId);
    if (control) control.checked = Boolean(defaults[field]);
  });
}

function brandMarkPayload(profile = {}) {
  const mark = profile?.brand_mark;
  return mark && typeof mark === "object" ? mark : {};
}

function brandMarkStyle(profile = {}) {
  const mark = brandMarkPayload(profile);
  if (typeof mark === "string") return mark;
  if (!mark || typeof mark !== "object") return "none";
  if (mark.style) return mark.style;
  if (mark.image_path && mark.text) return "image_text";
  if (mark.image_path) return "image";
  return mark.text ? "custom" : "none";
}

function brandMarkDurationSeconds(profile = {}) {
  const mark = brandMarkPayload(profile);
  const raw = mark && typeof mark === "object" ? Number(mark.duration_s) : NaN;
  return Number.isFinite(raw) ? raw : 1;
}

function brandMarkTextValue(profile = {}) {
  const mark = brandMarkPayload(profile);
  const text = String(mark.text || "").trim();
  if (text) return text;
  return brandMarkStyle(profile) === "splitshot" ? "SplitShot" : "";
}

function brandMarkPosition(profile = {}) {
  const mark = brandMarkPayload(profile);
  return String(mark.position || "top_right").trim() || "top_right";
}

function brandMarkOpacity(profile = {}) {
  const mark = brandMarkPayload(profile);
  const raw = Number(mark.opacity);
  return Number.isFinite(raw) ? Math.max(0, Math.min(1, raw)) : 0.72;
}

function brandMarkOpacityPercent(profile = {}) {
  return Math.round(brandMarkOpacity(profile) * 100);
}

function brandMarkImagePath(profile = {}) {
  const mark = brandMarkPayload(profile);
  return String(mark.image_path || "").trim();
}

function brandMarkImageScalePercent(profile = {}) {
  const mark = brandMarkPayload(profile);
  const raw = Number(mark.image_scale_percent);
  return Number.isFinite(raw) ? clampNumber(raw, 20, 400) : 100;
}

function brandMarkTextColor(profile = {}) {
  const mark = brandMarkPayload(profile);
  return normalizeHexColor(mark.text_color || "") || "#ffffff";
}

function brandMarkFontSize(profile = {}) {
  const mark = brandMarkPayload(profile);
  const raw = Number(mark.font_size);
  return Number.isFinite(raw) ? clampNumber(raw, 8, 96) : 24;
}

function buildBrandMarkPayload(profile = {}) {
  const style = $("hook-brand-mark-select")?.value || "none";
  if (style === "none") return null;
  const text = ($("hook-brand-mark-text")?.value || "").trim();
  const opacityPercent = Number($("hook-brand-mark-opacity")?.value || brandMarkOpacityPercent(profile));
  return {
    style,
    text: style === "splitshot" ? (text || "SplitShot") : text,
    position: $("hook-brand-mark-position")?.value || brandMarkPosition(profile),
    opacity: Math.max(0, Math.min(1, opacityPercent / 100)),
    duration_s: Number($("hook-brand-mark-duration")?.value || brandMarkDurationSeconds(profile) || 1),
    image_path: ($("hook-brand-mark-image-path")?.value || "").trim(),
    image_scale_percent: Number(
      $("hook-brand-mark-image-scale")?.value || brandMarkImageScalePercent(profile) || 100,
    ),
    text_color:
      normalizeHexColor($("hook-brand-mark-text-color")?.value || brandMarkTextColor(profile))
      || "#ffffff",
    font_size: Number($("hook-brand-mark-font-size")?.value || brandMarkFontSize(profile) || 24),
  };
}

function subjectTrackCropEnabled(profile = {}) {
  const crop = profile?.subject_track_crop;
  return Boolean(crop && typeof crop === "object" && (crop.enabled || crop.padding || crop.margin_percent));
}

function subjectTrackCropMarginPercent(profile = {}) {
  const crop = profile?.subject_track_crop;
  if (!crop || typeof crop !== "object") return 10;
  const marginPercent = Number(crop.margin_percent);
  if (Number.isFinite(marginPercent)) return marginPercent;
  const padding = Number(crop.padding);
  return Number.isFinite(padding) ? Math.round(padding * 100) : 10;
}

function syncOutputProfileDetailVisibility() {
  const detail = $("output-profile-detail");
  if (!detail) return;
  const hasContent = Boolean(String(detail.textContent || "").trim());
  detail.hidden = Boolean(activeOutputHookEditor) || !hasContent;
}

function renderOutputProfiles() {
  const list = $("output-profile-list");
  if (!list) return;
  const profiles = automationProfilesForCurrentScope();
  const activeProfile = activeAutomationProfile(profiles);
  const outputHookEditor = $("output-hook-editor");
  const outputProfileDetail = $("output-profile-detail");
  const outputHookButtons = [...document.querySelectorAll("[data-output-hook]")];
  list.innerHTML = "";
  const reviewSelect = $("retained-review-source");
  if (reviewSelect) {
    reviewSelect.innerHTML = '<option value="">Auto (current stage)</option>';
    profiles.forEach((profile) => {
      if (profile.profile_kind === "stage_output") {
        const option = document.createElement("option");
        option.value = profile.output_id;
        option.textContent = profile.profile_name || profile.output_id;
        if (retainedReviewSourceProfileId === profile.output_id) option.selected = true;
        reviewSelect.appendChild(option);
      }
    });
    if (retainedReviewSourceProfileId && !profiles.some((profile) => profile.output_id === retainedReviewSourceProfileId)) {
      retainedReviewSourceProfileId = null;
      reviewSelect.value = "";
    }
  }
  const reviewStatus = $("retained-review-status");
  if (reviewStatus) {
    reviewStatus.textContent = retainedReviewSourceProfileId
      ? `Review source set to profile ${retainedReviewSourceProfileId}.`
      : "Using live stage data.";
  }
  outputHookButtons.forEach((button) => {
    button.disabled = profiles.length === 0;
    button.classList.toggle("active", Boolean(activeOutputHookEditor) && button.dataset.outputHook === activeOutputHookEditor);
  });
  if (!profiles.length) {
    list.innerHTML = '<div class="hint">No output profiles yet.</div>';
    activeOutputHookEditor = null;
    if (outputHookEditor) outputHookEditor.hidden = true;
    if (outputProfileDetail) outputProfileDetail.textContent = "";
    syncOutputProfileDetailVisibility();
    return;
  }
  syncOutputProfileDetailVisibility();
  profiles.forEach((profile) => {
    const row = document.createElement("div");
    row.className = "automation-row";
    row.dataset.outputId = profile.output_id;
    if (profile.output_id === activeProfile?.output_id) row.classList.add("selected");
    const summary = document.createElement("div");
    summary.innerHTML = `<strong>${profile.profile_name || "Output Profile"}</strong><br><small>${profile.profile_kind || "stage_output"} • ${profile.frame_profile || "source"}</small>`;
    const actions = document.createElement("div");
    actions.className = "automation-row-actions";
    const review = document.createElement("button");
    review.type = "button";
    review.textContent = "Set Review Source";
    review.title = "Use this profile as the retained-review source";
    review.addEventListener("click", (event) => {
      event.stopPropagation();
      selectedAutomationOutputProfileId = profile.output_id;
      retainedReviewSourceProfileId = profile.output_id;
      renderOutputProfiles();
    });
    const select = document.createElement("button");
    select.type = "button";
    select.textContent = "Preview";
    select.addEventListener("click", async (event) => {
      event.stopPropagation();
      selectedAutomationOutputProfileId = profile.output_id;
      const plan = await callApi("/api/output-profiles/render", { output_id: profile.output_id });
      renderJsonDetail("output-profile-detail", plan || profile);
      renderOutputProfiles();
    });
    const duplicate = document.createElement("button");
    duplicate.type = "button";
    duplicate.textContent = "Duplicate";
    duplicate.addEventListener("click", (event) => {
      event.stopPropagation();
      selectedAutomationOutputProfileId = profile.output_id;
      createAutomationOutputProfile(`${profile.profile_name || "Profile"} Copy`, profile.profile_kind || "stage_output", profile);
    });
    const remove = document.createElement("button");
    remove.type = "button";
    remove.textContent = "Delete";
    remove.addEventListener("click", async (event) => {
      event.stopPropagation();
      const removedSelectedProfile = selectedAutomationOutputProfileId === profile.output_id;
      await callApi("/api/output-profiles/delete", { output_id: profile.output_id });
      if (removedSelectedProfile) selectedAutomationOutputProfileId = null;
      await refreshAutomationProfiles();
    });
    actions.append(review, select, duplicate, remove);
    row.append(summary, actions);
    row.addEventListener("click", () => {
      selectedAutomationOutputProfileId = profile.output_id;
      if (outputProfileDetail) outputProfileDetail.textContent = "";
      if (activeOutputHookEditor) renderOutputHookEditor(activeOutputHookEditor, profile);
      renderOutputProfiles();
    });
    list.append(row);
  });
  if (outputHookEditor) outputHookEditor.hidden = !(activeOutputHookEditor && activeProfile);
  syncOutputProfileDetailVisibility();
}

function renderWorkspaceStages() {
  if (matchView) return matchView.renderWorkspaceStages();
  const list = $("workspace-stage-list");
  if (!list) return;
  const entries = state?.workspace_stage_entries || [];
  list.innerHTML = "";
  entries.forEach((entry) => {
    const card = document.createElement("div");
    card.className = "match-stage-card";
    card.dataset.stageId = entry.stage_id;
    if (entry.stage_id === currentWorkspaceStageId()) card.classList.add("selected");

    const thumb = document.createElement("div");
    thumb.className = "match-stage-thumb";
    thumb.style.cssText = "width:48px;height:32px;background:var(--surface-2);border:1px solid var(--line);display:flex;align-items:center;justify-content:center;font-size:18px;";
    thumb.textContent = entry.source_media_present !== false ? "🎬" : "❌";

    const number = document.createElement("div");
    number.className = "match-stage-number";
    number.textContent = entry.stage_number || entries.indexOf(entry) + 1;

    const info = document.createElement("div");
    info.className = "match-stage-info";
    const name = document.createElement("p");
    name.className = "match-stage-name";
    name.textContent = entry.display_name || entry.stage_id || "Untitled Stage";

    const meta = document.createElement("div");
    meta.className = "match-stage-meta";
    const mediaStatus = entry.source_media_present === false ? "No media" : "Media ready";
    const statusSpan = document.createElement("span");
    statusSpan.textContent = mediaStatus;
    meta.appendChild(statusSpan);

    if (entry.override_count || Object.keys(entry.override_values || {}).length) {
      const badge = document.createElement("span");
      badge.className = "badge badge-custom";
      badge.textContent = "Custom";
      meta.appendChild(badge);
    }
    if (entry.inherited_from_first) {
      const badge = document.createElement("span");
      badge.className = "badge badge-shared";
      badge.textContent = "Shared";
      meta.appendChild(badge);
    }
    if (entry.status === "complete") {
      const badge = document.createElement("span");
      badge.className = "badge badge-shared";
      badge.style.cssText = "background: rgba(34,197,94,0.15); color: #22c55e; border: 1px solid rgba(34,197,94,0.3);";
      badge.textContent = "Complete";
      meta.appendChild(badge);
    }
    if (entry.metric_summary?.score != null) {
      const scoreSpan = document.createElement("span");
      scoreSpan.textContent = `Score: ${entry.metric_summary.score}`;
      scoreSpan.style.color = "var(--accent)";
      meta.appendChild(scoreSpan);
    }

    info.appendChild(name);
    info.appendChild(meta);

    const actions = document.createElement("div");
    actions.className = "match-stage-actions";

    const openBtn = document.createElement("button");
    openBtn.className = "match-stage-action";
    openBtn.type = "button";
    openBtn.textContent = "Open";
    openBtn.addEventListener("click", async (e) => {
      e.stopPropagation();
      selectedStageCompositeStageId = entry.stage_id;
      await callApi("/api/workspace/stage/open", { stage_id: entry.stage_id });
      setActiveSurface("single");
    });

    const removeBtn = document.createElement("button");
    removeBtn.className = "match-stage-action";
    removeBtn.type = "button";
    removeBtn.textContent = "Remove";
    removeBtn.addEventListener("click", async (e) => {
      e.stopPropagation();
      if (!confirm("Remove this stage from the match?")) return;
      await callApi("/api/workspace/stage/remove", { stage_id: entry.stage_id });
      await refresh();
    });

    const resetBtn = document.createElement("button");
    resetBtn.className = "match-stage-action";
    resetBtn.type = "button";
    resetBtn.textContent = "Reset";
    resetBtn.addEventListener("click", async (e) => {
      e.stopPropagation();
      await callApi("/api/workspace/stage/override/reset", { stage_id: entry.stage_id });
      await refresh();
    });

    actions.appendChild(openBtn);
    actions.appendChild(removeBtn);
    actions.appendChild(resetBtn);

    card.appendChild(thumb);
    card.appendChild(number);
    card.appendChild(info);
    card.appendChild(actions);

    card.addEventListener("click", () => {
      document.querySelectorAll(".match-stage-card").forEach(c => c.classList.remove("selected"));
      card.classList.add("selected");
      selectedStageCompositeStageId = entry.stage_id;
    });

    list.append(card);
  });
  checkSetupOnceBanner();
  const recap = document.getElementById("match-recap-panel");
  if (recap && entries.length) {
    const stageIds = entries
      .map((entry) => String(entry?.stage_id || "").trim())
      .filter(Boolean);
    const stageIdSet = new Set(stageIds);
    if (!(matchRecapSelectedStageIds instanceof Set) || matchRecapKnownStageIds.size === 0) {
      matchRecapSelectedStageIds = new Set(stageIds);
    } else {
      const overlappingStageIds = stageIds.filter((stageId) => matchRecapKnownStageIds.has(stageId));
      if (matchRecapSelectedStageIds.size > 0 && overlappingStageIds.length === 0) {
        matchRecapSelectedStageIds = new Set(stageIds);
      } else {
        matchRecapSelectedStageIds = new Set(
          [...matchRecapSelectedStageIds].filter((stageId) => stageIdSet.has(stageId)),
        );
      }
    }
    matchRecapKnownStageIds = stageIdSet;
    recap.innerHTML = `
      <div style="margin-bottom:8px"><strong>Match Recap</strong> — ${entries.length} stages</div>
      <div style="display:flex;flex-direction:column;gap:4px;margin-bottom:8px">
        ${entries.map((entry, i) => `
          <label style="display:flex;align-items:center;gap:8px;font-size:12px;color:var(--text)">
            <input type="checkbox" class="recap-stage-check" data-stage-id="${entry.stage_id}" ${matchRecapSelectedStageIds?.has(String(entry.stage_id || "")) ? "checked" : ""} 
              style="width:auto;min-height:auto;margin:0" />
            ${i + 1}. ${entry.display_name || entry.stage_id}
          </label>
        `).join("")}
      </div>
      <div class="control-grid" style="margin-bottom:8px">
        <label style="font-size:11px">Transition
          <select id="recap-transition" style="font-size:11px;min-height:24px">
            <option value="cut">Cut</option>
            <option value="fade">Fade</option>
            <option value="dissolve">Dissolve</option>
          </select>
        </label>
        <label style="font-size:11px">Result Card
          <select id="recap-result-card" style="font-size:11px;min-height:24px">
            <option value="none">None</option>
            <option value="end">At End</option>
            <option value="each">Per Stage</option>
          </select>
        </label>
      </div>
      <button id="recap-render" class="match-action-button" type="button" style="width:100%">Render Recap</button>
      <div id="recap-progress" hidden style="margin-top:8px">
        <div class="progress-bar" style="background:var(--surface-2);height:4px">
          <div class="progress-fill" style="width:0%;height:100%;background:var(--accent)"></div>
        </div>
      </div>
      <p id="recap-status" class="hint" aria-live="polite" style="margin-top:8px">Ready to render a match recap.</p>
      <pre id="recap-results" class="automation-detail" hidden></pre>
    `;

    syncControlValue($("recap-transition"), matchRecapTransitionValue || "cut");
    syncControlValue($("recap-result-card"), matchRecapResultCardValue || "none");
    const recapStatus = document.getElementById("recap-status");
    if (recapStatus) recapStatus.textContent = matchRecapStatusText;
    const recapResults = document.getElementById("recap-results");
    if (recapResults) {
      recapResults.hidden = matchRecapResultsHidden;
      recapResults.textContent = matchRecapResultsText;
    }

    const captureRecapSelection = () => {
      const selected = [...recap.querySelectorAll(".recap-stage-check:checked")]
        .map((checkbox) => String(checkbox.dataset.stageId || "").trim())
        .filter(Boolean);
      matchRecapSelectedStageIds = new Set(selected);
      return selected;
    };

    recap.querySelectorAll(".recap-stage-check").forEach((checkbox) => {
      checkbox.addEventListener("change", captureRecapSelection);
    });
    document.getElementById("recap-transition")?.addEventListener("change", (event) => {
      matchRecapTransitionValue = event?.target?.value || "cut";
    });
    document.getElementById("recap-result-card")?.addEventListener("change", (event) => {
      matchRecapResultCardValue = event?.target?.value || "none";
    });
    
    document.getElementById("recap-render")?.addEventListener("click", async () => {
      const recapElements = () => {
        const progress = document.getElementById("recap-progress");
        return {
          progress,
          fill: progress?.querySelector(".progress-fill"),
          status: document.getElementById("recap-status"),
          results: document.getElementById("recap-results"),
        };
      };
      const selected = captureRecapSelection();
      let { progress, fill, status, results } = recapElements();
      matchRecapTransitionValue = document.getElementById("recap-transition")?.value || matchRecapTransitionValue || "cut";
      matchRecapResultCardValue = document.getElementById("recap-result-card")?.value || matchRecapResultCardValue || "none";
      if (!selected.length) {
        matchRecapStatusText = "Select at least one stage for the recap.";
        matchRecapResultsText = "";
        matchRecapResultsHidden = true;
        if (progress) progress.hidden = true;
        if (fill) fill.style.width = "0%";
        if (status) status.textContent = matchRecapStatusText;
        if (results) {
          results.hidden = true;
          results.textContent = "";
        }
        return;
      }
      matchRecapStatusText = `Rendering recap for ${selected.length} stage(s)...`;
      matchRecapResultsText = "";
      matchRecapResultsHidden = true;
      if (progress) progress.hidden = false;
      if (fill) fill.style.width = "35%";
      if (status) status.textContent = matchRecapStatusText;
      if (results) {
        results.hidden = true;
        results.textContent = "";
      }
      try {
        const result = await callApi("/api/workspace/recap/render", {
          stage_ids: selected,
          transition: matchRecapTransitionValue,
          result_card: matchRecapResultCardValue,
        });
        ({ progress, fill, status, results } = recapElements());
        if (progress) progress.hidden = true;
        if (fill) fill.style.width = result?.success ? "100%" : "0%";
        if (!result) {
          matchRecapStatusText = "Recap render failed.";
          matchRecapResultsText = "";
          matchRecapResultsHidden = true;
          if (status) status.textContent = matchRecapStatusText;
          return;
        }
        if (result.success) {
          matchRecapStatusText = `Recap ready: ${result.output_path}`;
        } else {
          matchRecapStatusText = result.error || "Recap render failed.";
        }
        matchRecapResultsText = JSON.stringify(result, null, 2);
        matchRecapResultsHidden = false;
        if (status) status.textContent = matchRecapStatusText;
        if (results) {
          results.hidden = false;
          results.textContent = matchRecapResultsText;
        }
      } catch (e) {
        matchRecapStatusText = "Recap render failed.";
        matchRecapResultsText = "";
        matchRecapResultsHidden = true;
        if (progress) progress.hidden = true;
        if (fill) fill.style.width = "0%";
        if (status) status.textContent = matchRecapStatusText;
        console.error("Recap render failed:", e);
      }
    });
  } else if (recap) {
    recap.innerHTML = '<p class="hint">Create or open a workspace to build a Match Recap.</p>';
    matchRecapSelectedStageIds = null;
    matchRecapKnownStageIds = new Set();
    matchRecapStatusText = "Ready to render a match recap.";
    matchRecapResultsText = "";
    matchRecapResultsHidden = true;
  }
  const sharedDefaults = state?.workspace_shared_defaults || {};
  syncControlValue($("shared-frame-profile"), sharedDefaults.frame_profile || "source");
  syncControlValue($("shared-metric-captions"), sharedDefaults.metric_captions || "none");
  syncControlValue($("shared-lead-in"), sharedDefaults.lead_in_card || "none");
  syncControlValue($("shared-brand-mark"), sharedDefaults.brand_mark || "none");
  const overrideEditor = $("stage-override-editor");
  const overrideGrids = overrideEditor?.querySelectorAll(".control-grid");
  const overrideButton = $("override-apply");
  if (overrideEditor && entries.length && currentWorkspaceStageId()) {
    const activeEntry = entries.find((e) => e.stage_id === currentWorkspaceStageId());
    const overrides = activeEntry?.override_values || {};
    overrideEditor.querySelector("p")?.setAttribute("hidden", "");
    overrideGrids?.forEach((grid) => grid.removeAttribute("hidden"));
    if (overrideButton) overrideButton.removeAttribute("hidden");
    syncControlValue($("override-frame-profile"), overrides.frame_profile || "");
    syncControlValue($("override-metric-captions"), overrides.metric_captions || "");
  } else if (overrideEditor) {
    const hint = overrideEditor.querySelector("p");
    if (hint) hint.removeAttribute("hidden");
    overrideGrids?.forEach((grid) => grid.setAttribute("hidden", ""));
    if (overrideButton) overrideButton.setAttribute("hidden", "");
  }
  // Toggle empty state vs content
  const emptyState = document.querySelector(".match-empty-state");
  const sectionHeader = document.querySelector("#view-match .workspace-action-bar");
  const automationGrid = document.querySelector("#view-match .automation-grid");
  const matchSidebar = document.querySelector("#view-match .match-sidebar");
  const hasWorkspace = !!(state?.workspace || state?.workspace_stage_entries?.length);
  const hasStages = entries.length > 0;
  if (emptyState) emptyState.hidden = hasWorkspace;
  if (sectionHeader) sectionHeader.hidden = !hasWorkspace;
  if (automationGrid) automationGrid.hidden = !hasWorkspace;
  if (matchSidebar) matchSidebar.hidden = !hasWorkspace;
  if (!hasStages && hasWorkspace) {
    const grid = document.getElementById("workspace-stage-list");
    if (grid && grid.children.length === 0) {
      grid.innerHTML = '<p class="hint" style="padding:12px">No stages yet. Add your first stage.</p>';
    }
  }
}
function checkSetupOnceBanner() {
  if (matchView) return matchView.checkSetupOnceBanner?.();
  const banner = domById("setup-once-banner");
  if (!banner) return;
  const stages = state?.workspace_stage_entries || [];
  if (stages.length > 1 && stages[0]?.name && stages[0]?.media_loaded) {
    banner.hidden = false;
  }
}

function renderStageComposite() {
  if (matchView) return matchView.renderStageComposite();
  const list = $("stage-composite-list");
  if (!list) return;
  list.innerHTML = "";
  const stageId = currentWorkspaceStageId();
  if (!stageId) {
    list.innerHTML = '<div class="hint">Select a workspace stage to edit Stage Composite clips.</div>';
    return;
  }
  if (!stageCompositeClips.length) {
    list.innerHTML = '<div class="hint">No clips loaded for this stage.</div>';
  }
  stageCompositeClips.forEach((clip) => {
    const row = document.createElement("div");
    row.className = "automation-row";
    row.dataset.clipId = clip.clip_id;
    const summary = document.createElement("div");
    summary.innerHTML = `<strong>${fileName(clip.source_path || clip.clip_id)}</strong><br><small>${clip.camera_role || clip.angle_role || "primary"} • sync ${clip.sync_offset_ms || 0} ms • audio ${clip.audio_muted ? "muted" : clip.audio_gain ?? 1}</small>`;
    const actions = document.createElement("div");
    actions.className = "automation-row-actions";
    const align = document.createElement("button");
    align.type = "button";
    align.textContent = "Angle Align";
    align.addEventListener("click", () => callApi("/api/angle/align", { stage_id: stageId, reference_clip_id: clip.clip_id }));
    const audio = document.createElement("button");
    audio.type = "button";
    audio.textContent = "Audio Mix";
    audio.addEventListener("click", async () => {
      await callApi("/api/audio/mix", { stage_id: stageId, clip_id: clip.clip_id, gain: clip.audio_gain === 0 ? 1 : 0, muted: !clip.audio_muted });
      await refreshStageComposite(stageId);
    });
    const cut = document.createElement("button");
    cut.type = "button";
    cut.textContent = "Cut Override";
    cut.addEventListener("click", async () => {
      const outputId = await ensureCompositeOutputProfile(stageId);
      if (!outputId) return;
      await callApi("/api/angle/director/override", { stage_id: stageId, clip_id: clip.clip_id, output_id: outputId, position: 0, start_ms: 0, duration_ms: 1000 });
      const plan = await callApi("/api/angle/director/plan", { stage_id: stageId, output_id: outputId });
      renderJsonDetail("output-profile-detail", plan);
    });
    const remove = document.createElement("button");
    remove.type = "button";
    remove.textContent = "Remove";
    remove.addEventListener("click", async () => {
      await callApi("/api/workspace/stage/clip/remove", { stage_id: stageId, clip_id: clip.clip_id });
      await refreshStageComposite(stageId);
    });
    actions.append(align, audio, cut, remove);
    row.append(summary, actions);
    list.append(row);
  });
}

function renderPerformanceLibrary() {
  if (libraryView) return libraryView.renderPerformanceLibrary();
  renderLibrarySummaryTiles();
  const list = $("library-record-list");
  if (!list) return;
  const records = [
    ...(automationLibrary.stages || []).map((record) => ({ ...record, record_type: "stage" })),
    ...(automationLibrary.matches || []).map((record) => ({ ...record, record_type: "match" })),
  ];
  const filterDiscipline = $("library-filter-discipline")?.value || "";
  const sortBy = $("library-sort")?.value || "event_date";
  let filtered = records;
  if (filterDiscipline) {
    filtered = records.filter(r => (r.discipline || "").toLowerCase().replace(/[ _]/g, "_") === filterDiscipline);
  }
  if (sortBy === "score") {
    filtered.sort((a, b) => (b.score || 0) - (a.score || 0));
  } else if (sortBy === "display_name") {
    filtered.sort((a, b) => (a.display_name || "").localeCompare(b.display_name || ""));
  } else if (sortBy === "discipline") {
    filtered.sort((a, b) => (a.discipline || "").localeCompare(b.discipline || ""));
  }
  list.innerHTML = "";
  if (!filtered.length) {
    list.innerHTML = '<div class="hint">No performance records yet.</div>';
    renderPersonalBests();
    return;
  }
  filtered.forEach((record) => {
    const id = record.library_record_id || record.stage_id || record.match_id;
    const row = document.createElement("div");
    row.className = "library-record-row";
    row.dataset.recordId = id;

    const nameSpan = document.createElement("span");
    nameSpan.className = "library-record-name";
    nameSpan.textContent = record.display_name || id || "Untitled";

    const dateSpan = document.createElement("span");
    dateSpan.className = "library-record-date";
    dateSpan.textContent = record.event_date || "--";

    const disciplineSpan = document.createElement("span");
    disciplineSpan.className = "library-record-discipline";
    disciplineSpan.textContent = record.discipline || "--";

    const scoreSpan = document.createElement("span");
    scoreSpan.className = "library-record-score";
    scoreSpan.textContent = record.score != null ? record.score : "--";

    row.appendChild(nameSpan);
    row.appendChild(dateSpan);
    row.appendChild(disciplineSpan);
    row.appendChild(scoreSpan);

    row.addEventListener("click", () => {
      document.querySelectorAll(".library-record-row").forEach(r => r.classList.remove("selected"));
      row.classList.add("selected");
      selectedLibraryRecord = record;
      renderJsonDetail("library-record-detail", record);
      const tagsEditor = document.getElementById("library-tags-editor");
      const notesEditor = document.getElementById("library-notes-editor");
      const recordActions = document.getElementById("library-record-actions");
      if (tagsEditor) tagsEditor.hidden = false;
      if (notesEditor) notesEditor.hidden = false;
      if (recordActions) recordActions.hidden = false;
      renderLibraryTags();
      const notesText = document.getElementById("library-notes-text");
      if (notesText && record.notes) notesText.value = record.notes;
    });

    list.appendChild(row);
  });
  renderPersonalBests();
  fetchLibraryAnalytics().then(renderAnalyticsCharts);

  const emptyState = document.querySelector(".library-empty-state");
  const sectionHeader = document.querySelector("#view-library .workspace-action-bar");
  const automationGrid = document.querySelector("#view-library .automation-grid");
  const hasRecords = records.length > 0;

  if (emptyState) emptyState.hidden = hasRecords;
  if (sectionHeader) sectionHeader.hidden = !hasRecords;
  if (automationGrid) automationGrid.hidden = !hasRecords;
}

function renderLibrarySummaryTiles() {
  if (libraryView) return libraryView.renderLibrarySummaryTiles();
  const container = $("library-summary-tiles");
  if (!container) return;
  const records = [
    ...(automationLibrary.stages || []),
    ...(automationLibrary.matches || []),
  ];
  const totalStages = records.length;
  const totalMatches = new Set(records.filter(r => r.workspace_id).map(r => r.workspace_id)).size;
  const personalBest = records.filter(r => r.score != null).sort((a, b) => (b.score || 0) - (a.score || 0))[0];
  const personalBestVal = personalBest ? `${personalBest.score} (${personalBest.display_name || "--"})` : "--";
  const recentCount = records.filter(r => {
    if (!r.event_date) return false;
    const d = new Date(r.event_date);
    const monthAgo = new Date();
    monthAgo.setMonth(monthAgo.getMonth() - 1);
    return d >= monthAgo;
  }).length;
  container.innerHTML = `
    <div class="library-tile">
      <span class="library-tile-value">${totalStages}</span>
      <span class="library-tile-label">Total Stages</span>
    </div>
    <div class="library-tile">
      <span class="library-tile-value">${totalMatches}</span>
      <span class="library-tile-label">Total Matches</span>
    </div>
    <div class="library-tile">
      <span class="library-tile-value">${personalBestVal}</span>
      <span class="library-tile-label">Personal Best</span>
    </div>
    <div class="library-tile">
      <span class="library-tile-value">${recentCount}</span>
      <span class="library-tile-label">Recent (30d)</span>
    </div>
  `;
}

function renderLibraryTags() {
  if (libraryView) return libraryView.renderLibraryTags();
  const container = $("library-tag-list");
  if (!container) return;
  const tags = window.selectedLibraryRecord?.tags || [];
  container.innerHTML = tags.map(tag => `
    <span class="library-tag">
      ${escapeHtml(tag)}
      <span class="tag-remove" data-tag="${escapeHtml(tag)}" title="Remove tag">×</span>
    </span>
  `).join("") || '<span class="hint" style="font-size:0.6875rem">No tags</span>';
}

function renderPersonalBests() {
  if (libraryView) return libraryView.renderPersonalBests();
  const container = $("personal-bests-list");
  if (!container) return;
  const records = [
    ...(automationLibrary.stages || []),
    ...(automationLibrary.matches || []),
  ];
  if (records.length === 0) {
    container.innerHTML = '<p class="hint">Add records to see personal bests.</p>';
    return;
  }
  const sorted = [...records].filter(r => r.score != null).sort((a, b) => b.score - a.score).slice(0, 5);
  container.innerHTML = sorted.map((r, i) => `
    <div class="library-record-row">
      <span class="record-rank">#${i+1}</span>
      <span class="record-name">${escapeHtml(r.display_name || r.competitor_name || 'Unknown')}</span>
      <span class="record-score">${r.score}</span>
      <span class="record-discipline">${escapeHtml(r.discipline || '')}</span>
    </div>
  `).join("");
}

async function fetchLibraryAnalytics(discipline) {
  if (libraryView) return libraryView.fetchLibraryAnalytics(discipline);
  try {
    const response = await callApi("/api/library/analytics/trend", {
      metric_key: "score",
      discipline: discipline || "",
    });
    return response;
  } catch (e) {
    return null;
  }
}

function renderAnalyticsCharts(data) {
  if (libraryView) return libraryView.renderAnalyticsCharts(data);
  if (!data) return;

  const records = (automationLibrary.stages || []).filter(r => r.score != null);

  const scoreTrend = records
    .filter(r => r.event_date)
    .sort((a, b) => (a.event_date || "").localeCompare(b.event_date || ""))
    .map(r => ({ date: r.event_date, score: r.score }));

  const disciplineMap = {};
  (automationLibrary.stages || []).forEach(r => {
    const d = (r.discipline || "other").toLowerCase();
    disciplineMap[d] = (disciplineMap[d] || 0) + 1;
  });
  const disciplineBreakdown = Object.entries(disciplineMap)
    .map(([discipline, count]) => ({ discipline, count }))
    .sort((a, b) => b.count - a.count);

  const trendEl = document.getElementById("analytics-score-trend");
  if (trendEl && scoreTrend.length > 0) {
    const maxScore = Math.max(...scoreTrend.map(d => d.score || 0), 1);
    trendEl.innerHTML = `
      <div class="chart-bar-container" style="display:flex;align-items:flex-end;gap:2px;height:120px;padding:4px">
        ${scoreTrend.map(d => {
          const h = Math.round(((d.score || 0) / maxScore) * 100);
          return `<div class="chart-bar" style="height:${h}%;flex:1;background:var(--surface-2);min-width:8px;position:relative" title="${escapeHtml(d.date || "")}: ${d.score || 0}">
            <span style="position:absolute;top:-18px;left:50%;transform:translateX(-50%);font-size:9px;color:var(--muted)">${d.score || ""}</span>
          </div>`;
        }).join("")}
      </div>`;
    if (data.statistics) {
      const statsDiv = document.createElement("div");
      statsDiv.className = "chart-stats";
      statsDiv.style.cssText = "display:flex;gap:12px;margin-top:8px;font-size:0.6875rem;color:var(--quiet)";
      statsDiv.innerHTML = `
        <span>Mean: ${data.statistics.mean ?? "—"}</span>
        <span>Median: ${data.statistics.median ?? "—"}</span>
        <span>Best: ${data.statistics.max ?? "—"}</span>
        <span>Records: ${data.total_records || 0}</span>
        <span>Trend: ${data.trend_direction || "—"}</span>
      `;
      trendEl.appendChild(statsDiv);
    }
  }

  const discEl = document.getElementById("analytics-discipline-chart");
  if (discEl && disciplineBreakdown.length > 0) {
    const total = disciplineBreakdown.reduce((s, d) => s + (d.count || 0), 0) || 1;
    discEl.innerHTML = `
      <div class="discipline-bars">
        ${disciplineBreakdown.map(d => {
          const pct = Math.round(((d.count || 0) / total) * 100);
          return `<div class="discipline-bar" style="margin-bottom:4px">
            <span class="bar-label" style="font-size:11px;color:var(--muted);min-width:60px;display:inline-block">${(d.discipline || "?").toUpperCase()}</span>
            <span class="bar-fill" style="display:inline-block;height:16px;background:var(--accent);width:${pct}%;min-width:2px"></span>
            <span style="font-size:11px;color:var(--text);margin-left:4px">${d.count}</span>
          </div>`;
        }).join("")}
      </div>`;
  }

  const outEl = document.getElementById("analytics-outliers");
  if (outEl && data.outliers) {
    if (data.outliers.length > 0) {
      outEl.innerHTML = data.outliers.map(o => `
        <div style="display:flex;justify-content:space-between;padding:4px 0;border-bottom:1px solid var(--line);font-size:12px">
          <span style="color:var(--text)">${escapeHtml(o.name || "Unknown")}</span>
          <span style="color:${o.direction === "high" ? "var(--green)" : "var(--red)"}">${o.score || "--"} ${o.direction === "high" ? "\u2B06" : "\u2B07"}</span>
        </div>
      `).join("");
    } else {
      outEl.innerHTML = '<p class="hint">No significant outliers detected.</p>';
    }
  }
}

async function exportLibraryData(format) {
  const normalizedFormat = format === "csv" ? "csv" : "json";
  const result = await callApi(`/api/library/export/${normalizedFormat}`, {});
  if (!result) return null;

  const content = normalizedFormat === "csv"
    ? String(result.data || "")
    : JSON.stringify(result.data || {}, null, 2);
  downloadFile(
    normalizedFormat === "csv" ? "library-export.csv" : "library-export.json",
    content,
    normalizedFormat === "csv" ? "text/csv" : "application/json",
  );
  showExportCompleteNotification(1, "");
  setStatus(
    `Exported ${result.record_count || 0} Performance record${(result.record_count || 0) === 1 ? "" : "s"} as ${normalizedFormat.toUpperCase()}.`,
  );
  return result;
}

function downloadFile(filename, content, mimeType) {
  const blob = new Blob([content], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

function showExportCompleteNotification(count, outputPath) {
  const toast = document.createElement("div");
  toast.className = "export-toast";
  toast.setAttribute("role", "status");
  toast.setAttribute("aria-live", "polite");
  toast.innerHTML = `
    <span>&#10004;&#65039; Export complete &#8212; ${count} file${count !== 1 ? 's' : ''} saved</span>
    <button class="export-toast-open" type="button">Open Folder</button>
    <button class="export-toast-dismiss" type="button">&#215;</button>
  `;
  toast.querySelector(".export-toast-open")?.addEventListener("click", () => {
    activity("ui.export.open-folder");
    toast.remove();
  });
  toast.querySelector(".export-toast-dismiss")?.addEventListener("click", () => toast.remove());
  document.body.appendChild(toast);
  setTimeout(() => toast.remove(), 8000);
}

function addLibraryTag(tag) {
  if (libraryView) return libraryView.addLibraryTag(tag);
  if (!window.selectedLibraryRecord) return;
  window.selectedLibraryRecord.tags = window.selectedLibraryRecord.tags || [];
  if (!window.selectedLibraryRecord.tags.includes(tag)) {
    window.selectedLibraryRecord.tags.push(tag);
    renderLibraryTags();
  }
}

function removeLibraryTag(tag) {
  if (libraryView) return libraryView.removeLibraryTag(tag);
  if (!window.selectedLibraryRecord?.tags) return;
  window.selectedLibraryRecord.tags = window.selectedLibraryRecord.tags.filter(t => t !== tag);
  renderLibraryTags();
}

function saveLibraryNotes(notes) {
  if (libraryView) return libraryView.saveLibraryNotes(notes);
  if (!window.selectedLibraryRecord) return;
  window.selectedLibraryRecord.notes = notes;
  activity("ui.library.notes.save");
}

function libraryRecordId(record = selectedLibraryRecord) {
  return record?.library_record_id || record?.stage_id || record?.match_id || "";
}

function libraryAllRecords() {
  return [
    ...(automationLibrary.stages || []),
    ...(automationLibrary.matches || []),
  ];
}

function findLibraryRecordById(recordId) {
  return libraryAllRecords().find((record) => libraryRecordId(record) === recordId) || null;
}

function syncSelectedLibraryRecord(record) {
  selectedLibraryRecord = record || null;
  return selectedLibraryRecord;
}

function updateLibraryRecordInState(recordId, nextFields = {}) {
  let nextSelected = null;
  const applyUpdate = (records = []) => records.map((record) => {
    if (libraryRecordId(record) !== recordId) return record;
    const nextRecord = { ...record, ...nextFields };
    nextSelected = nextRecord;
    return nextRecord;
  });

  automationLibrary = {
    ...automationLibrary,
    stages: applyUpdate(automationLibrary.stages),
    matches: applyUpdate(automationLibrary.matches),
  };

  if (nextSelected) syncSelectedLibraryRecord(nextSelected);
  return nextSelected || findLibraryRecordById(recordId);
}

async function openSelectedLibraryStage() {
  const recordId = libraryRecordId();
  if (!recordId) {
    setStatus("Select a Performance record first.");
    return null;
  }

  activity("ui.library.open.stage", { record_id: recordId });
  const result = await callApi("/api/library/stage/open", { library_record_id: recordId });
  if (!result?.success) {
    automationError.library = result?.error || $("status")?.textContent || "Failed to open stage.";
    renderAutomationSurface();
    return null;
  }

  automationError.library = null;
  const editorTarget = result.editor_target || {};
  const workspacePath = String(editorTarget.workspace_path || "").trim();
  const projectPath = String(editorTarget.project_path || "").trim();
  const stageId = String(editorTarget.stage_id || result.record?.stage_id || "").trim();

  if (workspacePath) {
    const openedWorkspace = await openWorkspaceFromPath(workspacePath);
    if (!openedWorkspace) return null;
    if (!stageId) {
      setStatus("This Performance record does not include a stage reopen target.");
      return null;
    }
    const stageOpened = await callApi("/api/workspace/stage/open", { stage_id: stageId });
    if (!stageOpened && !Boolean(state?.return_to_match_available)) {
      automationError.workspace = workspaceOperationStatus(`Failed to open stage ${stageId}.`);
      renderAutomationSurface();
      return null;
    }
    setActiveSurface("single");
    return result;
  }

  if (projectPath) {
    const openedProject = await callApi("/api/project/open", { path: projectPath });
    if (!openedProject && String(state?.project?.path || "") !== projectPath) {
      automationError.library = $("status")?.textContent || `Failed to open project at ${projectPath}.`;
      renderAutomationSurface();
      return null;
    }
    setActiveSurface("single");
    return result;
  }

  setStatus("This Performance record does not include a reopen path.");
  return null;
}

async function openSelectedLibraryWorkspace() {
  const recordId = libraryRecordId();
  if (!recordId) {
    setStatus("Select a Performance record first.");
    return null;
  }

  activity("ui.library.open.workspace", { record_id: recordId });
  const result = await callApi("/api/library/match/open", { library_record_id: recordId });
  if (!result?.success) {
    automationError.library = result?.error || $("status")?.textContent || "Failed to open workspace.";
    renderAutomationSurface();
    return null;
  }

  automationError.library = null;
  const workspacePath = String(result.editor_target?.workspace_path || "").trim();
  if (!workspacePath) {
    setStatus("This Performance record does not include a workspace reopen path.");
    return null;
  }
  return openWorkspaceFromPath(workspacePath);
}

async function persistSelectedLibraryTags(tags) {
  const recordId = libraryRecordId();
  if (!recordId) {
    setStatus("Select a Performance record first.");
    return null;
  }

  const nextTags = [...new Set((tags || []).map((tag) => String(tag || "").trim()).filter(Boolean))];
  activity("ui.library.tags.save", { record_id: recordId, count: nextTags.length });
  const result = await callApi("/api/library/tags/update", { record_id: recordId, tags: nextTags });
  if (!result?.updated) {
    automationError.library = $("status")?.textContent || result?.error || "Failed to save tags.";
    renderAutomationSurface();
    return null;
  }

  automationError.library = null;
  const nextRecord = updateLibraryRecordInState(recordId, { tags: nextTags });
  if (nextRecord) {
    renderJsonDetail("library-record-detail", nextRecord);
    renderLibraryTags();
  }
  return result;
}

async function persistSelectedLibraryNotes(notes) {
  const recordId = libraryRecordId();
  if (!recordId) {
    setStatus("Select a Performance record first.");
    return null;
  }

  const nextNotes = String(notes || "");
  activity("ui.library.notes.save", { record_id: recordId });
  const result = await callApi("/api/library/notes/update", { record_id: recordId, notes: nextNotes });
  if (!result?.updated) {
    automationError.library = $("status")?.textContent || result?.error || "Failed to save notes.";
    renderAutomationSurface();
    return null;
  }

  automationError.library = null;
  const nextRecord = updateLibraryRecordInState(recordId, { notes: nextNotes });
  if (nextRecord) renderJsonDetail("library-record-detail", nextRecord);
  return result;
}

function renderAutomationSurface() {
  const desiredProfileScopeKey = `stage:${currentStageScopeId() || ""}`;
  if (desiredProfileScopeKey !== automationProfileScopeKey && !automationLoading.profiles) {
    automationProfileScopeKey = desiredProfileScopeKey;
    void refreshAutomationProfiles();
  }
  renderSurfaceContext();
  renderOutputProfiles();
  renderWorkspaceStages();
  renderStageComposite();
  renderPerformanceLibrary();
  const loadingEl = {
    single: $("single-video-loading"),
    multi: $("multi-video-loading"),
    library: $("library-loading"),
  };
  const errorEl = {
    single: $("single-video-error"),
    multi: $("multi-video-error"),
    library: $("library-error"),
  };
  const staleEl = $("library-stale");
  if (loadingEl.single) loadingEl.single.hidden = !automationLoading.profiles;
  if (loadingEl.multi) loadingEl.multi.hidden = !(automationLoading.workspace || automationLoading.clips);
  if (loadingEl.library) loadingEl.library.hidden = !automationLoading.library;
  if (errorEl.single) {
    errorEl.single.hidden = !automationError.profiles;
    if (automationError.profiles) errorEl.single.textContent = automationError.profiles;
  }
  if (errorEl.multi) {
    const multiError = automationError.workspace || automationError.clips;
    errorEl.multi.hidden = !multiError;
    if (multiError) errorEl.multi.textContent = multiError;
  }
  if (errorEl.library) {
    errorEl.library.hidden = !automationError.library;
    if (automationError.library) {
      const libraryErrorMessage = $("library-error-message");
      if (libraryErrorMessage) libraryErrorMessage.textContent = automationError.library;
      else errorEl.library.textContent = automationError.library;
    }
  }
  if (staleEl) staleEl.hidden = !automationStale.library;
  const libraryEmptyState = document.querySelector(".library-empty-state");
  if (libraryEmptyState && (automationLoading.library || automationError.library || automationStale.library)) {
    libraryEmptyState.hidden = true;
  }
}

async function refreshAutomationProfiles() {
  automationProfileScopeKey = `stage:${currentStageScopeId() || ""}`;
  automationLoading.profiles = true;
  automationError.profiles = null;
  renderAutomationSurface();
  try {
    const result = await callApi("/api/output-profiles/list", {
      scope_type: "stage",
      scope_id: currentStageScopeId(),
    });
    automationProfiles = result?.profiles || [];
    if (!automationProfiles.some((profile) => profile.output_id === selectedAutomationOutputProfileId)) {
      selectedAutomationOutputProfileId = automationProfiles[0]?.output_id || null;
    }
  } catch (error) {
    automationError.profiles = error?.message || "Failed to load output profiles.";
    automationProfiles = [];
    selectedAutomationOutputProfileId = null;
  }
  automationLoading.profiles = false;
  renderAutomationSurface();
  return automationProfiles;
}

async function createAutomationOutputProfile(profileName, profileKind, baseProfile = null) {
  const payload = {
    scope_type: profileKind === "match_recap" ? "match" : "stage",
    scope_id: profileKind === "match_recap" ? (state?.active_match_id || state?.match_workspace_summary?.match_id || "") : currentStageScopeId(),
    profile_name: profileName || "Output Profile",
    profile_kind: profileKind || "stage_output",
  };
  if (baseProfile) {
    ["frame_profile", "metric_caption_preset", "lead_in_card", "brand_mark", "subject_track_crop", "visibility_recipe"].forEach((key) => {
      if (baseProfile[key] !== undefined) payload[key] = baseProfile[key];
    });
  }
  const result = await callApi("/api/output-profiles/create", payload);
  selectedAutomationOutputProfileId = result?.profile?.output_id || selectedAutomationOutputProfileId;
  await refreshAutomationProfiles();
}

async function ensureCompositeOutputProfile(stageId) {
  const existing = automationProfiles.find((profile) => profile.scope_type === "stage" && profile.scope_id === stageId && profile.profile_kind === "stage_composite");
  if (existing) {
    selectedCompositeOutputId = existing.output_id;
    return existing.output_id;
  }
  const result = await callApi("/api/output-profiles/create", {
    scope_type: "stage",
    scope_id: stageId,
    profile_name: "Stage Composite",
    profile_kind: "stage_composite",
  });
  await refreshAutomationProfiles();
  selectedCompositeOutputId = result?.profile?.output_id || null;
  return selectedCompositeOutputId;
}

async function refreshStageComposite(stageId = currentWorkspaceStageId()) {
  if (!stageId) return;
  automationLoading.clips = true;
  automationError.clips = null;
  renderAutomationSurface();
  try {
    const result = await callApi("/api/workspace/stage/clip/list", { stage_id: stageId });
    stageCompositeClips = result?.clips || [];
  } catch (error) {
    automationError.clips = error?.message || "Failed to load stage clips.";
    stageCompositeClips = [];
  }
  automationLoading.clips = false;
  renderAutomationSurface();
}

async function refreshPerformanceLibrary() {
  const requestSequence = ++libraryRefreshSequence;
  const query = $("library-search")?.value || "";
  const sortBy = $("library-sort")?.value || "event_date";
  automationLoading.library = true;
  automationError.library = null;
  automationStale.library = false;
  renderAutomationSurface();
  const result = query
    ? await callApi("/api/library/filter", { competitor: query, sort_by: sortBy, sort_order: "desc" })
    : await callApi("/api/library/list", {});

  if (requestSequence !== libraryRefreshSequence) return null;

  if (!result) {
    automationError.library = $("status")?.textContent || "Failed to load library records.";
    automationLibrary = { stages: [], matches: [], total_stages: 0, total_matches: 0 };
  } else {
    automationLibrary = {
      stages: Array.isArray(result.stages) ? result.stages : [],
      matches: Array.isArray(result.matches) ? result.matches : [],
      total_stages: Number(result.total_stages ?? (Array.isArray(result.stages) ? result.stages.length : 0)),
      total_matches: Number(result.total_matches ?? (Array.isArray(result.matches) ? result.matches.length : 0)),
    };
    const selectedRecordId = libraryRecordId(selectedLibraryRecord);
    if (selectedRecordId) syncSelectedLibraryRecord(findLibraryRecordById(selectedRecordId));
    automationStale.library = !(libraryView?.libraryAutoRefreshEnabled?.() ?? true);
  }
  automationLoading.library = false;
  renderAutomationSurface();
  if (!automationError.library) {
    const discipline = $("library-filter-discipline")?.value || "";
    fetchLibraryAnalytics(discipline).then(renderAnalyticsCharts);
  }
  return result;
}

function setActiveTool(tool, { collapseExpandedLayout = true, persistUiState = true } = {}) {
  tool = normalizeToolId(tool);
  if (!VALID_TOOL_IDS.has(tool) || !document.querySelector(`[data-tool-pane="${tool}"]`)) tool = "project";
  if (persistUiState || tool !== "project") {
    forcedProjectLandingPersistedTool = null;
  }
  const changed = activeTool !== tool;
  const root = $("cockpit-root");
  const hadExpandedLayout = root?.classList.contains("waveform-expanded")
    || root?.classList.contains("timing-expanded")
    || root?.classList.contains("metrics-expanded")
    || root?.classList.contains("scoring-expanded")
    || root?.classList.contains("markers-expanded");
  setActiveToolValue(tool);
  if (!initialProjectUiStateApplied && persistUiState) {
    pendingBootstrapProjectUiStateOverride = true;
  }
  window.localStorage.setItem("splitshot.activeTool", tool);
  let previousExpandedLayout = null;
  const preservedExpandedLayout = state?.project?.ui_state ? {
      waveform_expanded: state.project.ui_state.waveform_expanded,
      timing_expanded: state.project.ui_state.timing_expanded,
      metrics_expanded: state.project.ui_state.metrics_expanded,
      markers_expanded: state.project.ui_state.markers_expanded,
      scoring_expanded: state.project.ui_state.scoring_expanded,
    } : null;
  if (collapseExpandedLayout && hadExpandedLayout) {
    previousExpandedLayout = {
      waveform_expanded: root?.classList.contains("waveform-expanded") || false,
      timing_expanded: root?.classList.contains("timing-expanded") || false,
      metrics_expanded: root?.classList.contains("metrics-expanded") || false,
      markers_expanded: root?.classList.contains("markers-expanded") || false,
      scoring_expanded: root?.classList.contains("scoring-expanded") || false,
    };
  }
  if (changed) {
    collapseMinimizableInspectorItems({ persistUiState, rerender: false });
  }
  if (previousExpandedLayout) {
    setWaveformExpanded(false, { persistUiState: false });
    setTimingExpanded(false, { persistUiState: false });
    setMetricsExpanded(false, { persistUiState: false });
    setMarkersExpanded(false, { persistUiState: false });
    setScoringWorkbenchExpanded(false, { persistUiState: false });
    const expand = $("expand-waveform");
    if (expand) expand.textContent = "Expand";
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
  if (tool === "settings") {
    renderSettingsPane();
  }
  const popupFloatingEditor = $("popup-floating-editor");
  if (popupFloatingEditor instanceof HTMLElement && tool !== "markers") {
    popupFloatingEditor.hidden = true;
    popupFloatingEditor.innerHTML = "";
  }
  if (tool !== "markers") {
    if (markersWorkbenchShown()) setMarkersExpanded(false, { persistUiState: false });
    if (popupWorkbenchRestoreState) restorePopupWorkbenchLayout({ persistUiState: false, restoreWaveformExpanded: false });
    const markersWorkbench = $("markers-workbench");
    if (markersWorkbench instanceof HTMLElement) markersWorkbench.hidden = true;
  }
  if (tool === "merge") {
    $("add-merge-media")?.focus();
  } else if (tool === "markers" && changed) {
    if (selectedPopupBubbleId) {
      window.requestAnimationFrame(() => revealPopupBubbleCard(selectedPopupBubbleId, { focus: false }));
    }
  }
  if (changed) activity("ui.tool.active", { tool });
  syncLocalProjectUiState();
  if (previousExpandedLayout && state?.project?.ui_state) {
    state.project.ui_state.waveform_expanded = previousExpandedLayout.waveform_expanded;
    state.project.ui_state.timing_expanded = previousExpandedLayout.timing_expanded;
    state.project.ui_state.metrics_expanded = previousExpandedLayout.metrics_expanded;
    state.project.ui_state.markers_expanded = previousExpandedLayout.markers_expanded;
    state.project.ui_state.scoring_expanded = previousExpandedLayout.scoring_expanded;
  } else if (preservedExpandedLayout && state?.project?.ui_state) {
    state.project.ui_state.waveform_expanded = preservedExpandedLayout.waveform_expanded;
    state.project.ui_state.timing_expanded = preservedExpandedLayout.timing_expanded;
    state.project.ui_state.metrics_expanded = preservedExpandedLayout.metrics_expanded;
    state.project.ui_state.markers_expanded = preservedExpandedLayout.markers_expanded;
    state.project.ui_state.scoring_expanded = preservedExpandedLayout.scoring_expanded;
  }
  if (persistUiState) scheduleProjectUiStateApply();
  if (tool === "waveform" && state?.project?.ui_state?.waveform_expanded) {
    setWaveformExpanded(true, { persistUiState: false });
  }
  if (tool === "timing" && state?.project?.ui_state?.timing_expanded) {
    setTimingExpanded(true, { persistUiState: false });
  }
  if (tool === "metrics" && state?.project?.ui_state?.metrics_expanded) {
    setMetricsExpanded(true, { persistUiState: false });
  }
  if (tool === "markers" && state?.project?.ui_state?.markers_expanded) {
    setMarkersExpanded(true, { persistUiState: false });
  }
  if (tool === "scoring" && state?.project?.ui_state?.scoring_expanded) {
    setScoringWorkbenchExpanded(true, { persistUiState: false });
  }
  renderLiveOverlay();
}

async function api(path, payload = null) {
  return apiRuntime.api(path, payload);
}

async function callApi(path, payload = null) {
  return apiRuntime.callApi(path, payload);
}

function practiScoreResponseErrorMessage(data, fallback) {
  return apiRuntime.practiScoreResponseErrorMessage(data, fallback);
}

async function openPractiScoreDashboard() {
  return apiRuntime.openPractiScoreDashboard();
}

function processingForPath(path, payload = null) {
  return processingRuntime.processingForPath(path, payload);
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

function currentProjectPath(nextState = state) {
  return String(nextState?.project?.path || "").trim();
}

function dialogPathRequestPayload(kind, currentValue = "", nextState = state) {
  const normalizedKind = String(kind || "").trim();
  const normalizedCurrent = String(currentValue ?? "").trim();
  const projectHome = currentProjectPath(nextState);
  return {
    kind: normalizedKind,
    current: normalizedCurrent,
    home: projectHome,
  };
}

async function pickPath(kind, targetId, afterSelect = null) {
  const target = $(targetId);
  const requestPayload = dialogPathRequestPayload(kind, target?.value);
  activity("dialog.path.request", {
    kind,
    target: targetId,
    current: requestPayload.current,
    home: requestPayload.home || "",
  });
  try {
    const response = await fetch("/api/dialog/path", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(requestPayload),
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

async function openPrimaryImportPathPicker() {
  return pickPath("primary", "primary-file-path", async (path) => {
    await flushPendingProjectDrafts({ primaryImport: true });
    const result = await callApi("/api/import/primary", { path });
    if (!result) return;
    setActiveSurface("single");
    setActiveTool("project");
  });
}

function setPreviewSeekBoundary(value) {
  previewSeekBoundary = Boolean(value);
  if (previewSeekBoundary) previewSyncedSinceBoundary = false;
}

function markPreviewSeekBoundary() {
  setPreviewSeekBoundary(true);
}

async function pickPathForElement(kind, target, targetLabel, afterSelect = null) {
  if (!(target instanceof HTMLInputElement || target instanceof HTMLTextAreaElement)) return "";
  const requestPayload = dialogPathRequestPayload(kind, target.value);
  activity("dialog.path.request", {
    kind,
    target: targetLabel,
    current: requestPayload.current,
    home: requestPayload.home || "",
  });
  try {
    const response = await fetch("/api/dialog/path", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(requestPayload),
    });
    const data = await response.json();
    if (!response.ok || data.error) throw new Error(data.error || response.statusText);
    if (data.path) {
      target.value = data.path;
      activity("dialog.path.selected", { kind, target: targetLabel, path: data.path });
      if (afterSelect) {
        await afterSelect(data.path);
      }
    } else {
      activity("dialog.path.cancelled", { kind, target: targetLabel });
    }
    return data.path || "";
  } catch (error) {
    setStatus(error.message);
    activity("dialog.path.error", { kind, target: targetLabel, error: error.message });
    return "";
  }
}

function workspacePathValue(nextState = state) {
  return String(nextState?.workspace_path || nextState?.workspace?.path || "").trim();
}

function workspaceHasEntries(nextState = state) {
  return Boolean(nextState?.workspace || (nextState?.workspace_stage_entries || []).length);
}

function workspaceOperationStatus(fallback = "Workspace action failed.") {
  return String($("status")?.textContent || "").trim() || fallback;
}

async function runWorkspaceOperation(action, {
  failureMessage = "Workspace action failed.",
  isSuccess = () => true,
  onSuccess = null,
} = {}) {
  automationLoading.workspace = true;
  automationError.workspace = null;
  renderAutomationSurface();
  try {
    const result = await action();
    if (!result || !isSuccess(result)) {
      automationError.workspace = workspaceOperationStatus(failureMessage);
      return null;
    }
    automationError.workspace = null;
    if (typeof onSuccess === "function") {
      await onSuccess(result);
    }
    return result;
  } finally {
    automationLoading.workspace = false;
    renderAutomationSurface();
  }
}

async function chooseWorkspacePath(currentPath = workspacePathValue()) {
  const target = document.createElement("input");
  target.value = currentPath || "";
  return pickPathForElement("project_folder", target, "workspace-path");
}

async function openWorkspaceFromPath(path) {
  const targetPath = String(path || "").trim();
  if (!targetPath) return null;
  return runWorkspaceOperation(
    () => callApi("/api/workspace/open", { path: targetPath }),
    {
      failureMessage: `No workspace found at ${targetPath}`,
      isSuccess: () => workspacePathValue() === targetPath && workspaceHasEntries(),
      onSuccess: async (result) => {
        selectedStageCompositeStageId = null;
        setActiveSurface("multi");
        requestRender();
        return result;
      },
    },
  );
}

async function openWorkspaceWithPicker() {
  const path = await chooseWorkspacePath();
  if (!path) return null;
  return openWorkspaceFromPath(path);
}

async function saveWorkspaceFromUi({ forcePrompt = false } = {}) {
  if (!workspaceHasEntries()) {
    const message = "Create or open a workspace before saving.";
    setStatus(message);
    automationError.workspace = message;
    renderAutomationSurface();
    return null;
  }
  let path = forcePrompt ? "" : workspacePathValue();
  if (!path) {
    path = await chooseWorkspacePath();
  }
  if (!path) return null;
  return runWorkspaceOperation(
    () => callApi("/api/workspace/save", { path }),
    {
      failureMessage: `Failed to save workspace to ${path}.`,
      isSuccess: () => workspacePathValue() === path,
      onSuccess: async (result) => {
        requestRender();
        return result;
      },
    },
  );
}

async function returnToMatchWorkspace() {
  const previousStageId = state?.active_stage_id || selectedStageCompositeStageId || null;
  if (state?.return_to_match_available) {
    const result = await callApi("/api/workspace/stage/return", {});
    if (!result) return null;
  }
  if ($("match-setting-remember-stage")?.checked ?? true) {
    selectedStageCompositeStageId = state?.returned_stage_id || previousStageId || selectedStageCompositeStageId;
  } else {
    selectedStageCompositeStageId = null;
  }
  setActiveSurface("multi");
  requestRender();
  return true;
}

async function refresh() {
  activity("api.refresh", {});
  runtimeBackbone?.bus?.emit?.("api.refresh", {});
  try {
    const response = await fetch("/api/state");
    const data = await response.json();
    if (!response.ok || data.error) throw new Error(data.error || response.statusText);
    applyRemoteState(data);
    markPreviewSeekBoundary();
    if (data?.project?.name && activeSurface !== "landing") {
      recordRecentActivity(data.project.name, activeSurface, activeSurface === 'single' ? 'Stage' : activeSurface === 'multi' ? 'Match' : 'Library', '');
    }
    requestRender();
  } catch (error) {
    setStatus(error.message);
    runtimeBackbone?.bus?.emit?.("api.error", { path: "/api/state", error: error.message });
    activity("api.error", { path: "/api/state", error: error.message });
  }
}

function applyRemoteState(nextState) {
  const shouldApplyBootstrapLandingTool = !initialProjectUiStateApplied
    && !pendingBootstrapProjectUiStateOverride
    && Boolean(String(nextState?.project?.path || "").trim());
  if (shouldApplyBootstrapLandingTool && nextState?.project?.ui_state) {
    const reopenLastTool = Boolean(nextState?.settings?.reopen_last_tool ?? true);
    const configuredTool = reopenLastTool
      ? String(nextState?.settings?.default_tool || nextState?.project?.ui_state?.active_tool || "project")
      : "project";
    nextState = {
      ...nextState,
      project: {
        ...nextState.project,
        ui_state: normalizeProjectUiState({
          ...nextState.project.ui_state,
          active_tool: configuredTool,
        }),
      },
    };
  }
  return apiRuntime.applyRemoteState(nextState);
}

function hasCompleteProjectState(nextState) {
  return apiRuntime.hasCompleteProjectState(nextState);
}

function stateHasShot(nextState, shotId) {
  return apiRuntime.stateHasShot(nextState, shotId);
}

function resetLocalProjectView() {
  resetProjectUiStateApplyState();
  pendingBootstrapProjectUiStateOverride = false;
  forcedProjectLandingPersistedTool = null;
  setSelectedShotIdValue(null);
  draggingShotId = null;
  draggingShotPointerId = null;
  pendingDragTimeMs = null;
  exportPathDraft = "";
  exportDraft = {};
  mergeDraft = {};
  overlayPositionDraft = {};
  overlayStyleDraft = null;
  projectDetailsDraft = { name: null, description: null };
  overlayTextBoxesDraft = null;
  popupBubblesDraft = null;
  popupTemplateDraft = null;
  exportLogLines = [];
  popupGeneratedMotionOffsetsByBubbleId = new Map();
  popupMotionGenerationSummaryByBubbleId = new Map();
  popupEditorVisible = false;
  popupEditorCollapsed = false;
  metricsSectionExpansion = new Map([
    ["trend-snapshot", true],
    ["scoring-context", true],
  ]);
  layoutSizePinned = { railWidth: false, inspectorWidth: false, waveformHeight: false };
  timingRowEdits = new Set();
  timingAdjustmentDrafts = new Map();
  scoringRowEdits = new Set();
  applyProjectUiState({
    ...DEFAULT_PROJECT_UI_STATE,
    active_tool: "project",
    waveform_mode: "select",
    timeline_zoom: 1,
    timeline_offset_ms: 0,
    layout_locked: true,
    rail_width: DEFAULT_LAYOUT_SIZES.railWidth,
    inspector_width: DEFAULT_LAYOUT_SIZES.inspectorWidth,
    waveform_height: DEFAULT_LAYOUT_SIZES.waveformHeight,
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
    "scoring-result",
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
    } else if (id === "scoring-result") {
      element.textContent = "--";
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
  return reviewPane?.restoreReviewStage();
}

function scheduleReviewStageRestore() {
  return reviewPane?.scheduleReviewStageRestore();
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
  return projectPane?.normalizedPractiScorePlaceValue(rawValue) ?? null;
}

function defaultPractiScoreSessionPayload() {
  return apiRuntime.defaultPractiScoreSessionPayload();
}

function normalizePractiScoreSessionPayload(payload) {
  return apiRuntime.normalizePractiScoreSessionPayload(payload);
}

function normalizePractiScoreRemoteMatches(matches) {
  return apiRuntime.normalizePractiScoreRemoteMatches(matches);
}

function defaultPractiScoreSyncPayload() {
  return apiRuntime.defaultPractiScoreSyncPayload();
}

function normalizePractiScoreSyncPayload(payload) {
  return apiRuntime.normalizePractiScoreSyncPayload(payload);
}

function practiScoreSessionPayload() {
  return apiRuntime.practiScoreSessionPayload();
}

function practiScoreSyncPayload() {
  return apiRuntime.practiScoreSyncPayload();
}

function applyPractiScoreSessionPayload(payload, { resetSync = false } = {}) {
  return apiRuntime.applyPractiScoreSessionPayload(payload, { resetSync });
}

function applyPractiScoreRoutePayload(payload) {
  return apiRuntime.applyPractiScoreRoutePayload(payload);
}

function practiScoreCompetitors() {
  return projectPane?.practiScoreCompetitors() ?? [];
}

function practiScoreStageValues() {
  return projectPane?.practiScoreStageValues() ?? [];
}

function practiScoreNameValues() {
  return projectPane?.practiScoreNameValues() ?? [];
}

function practiScorePlaceValues() {
  return projectPane?.practiScorePlaceValues() ?? [];
}

function practiScoreSelectionValue(value) {
  return projectPane?.practiScoreSelectionValue(value) ?? "";
}

function preferredPractiScoreSelection(explicitValue, controlId, fallbackValue) {
  return projectPane?.preferredPractiScoreSelection(explicitValue, controlId, fallbackValue) ?? "";
}

function renderPractiScoreSelect(selectId, values, emptyLabel, selectedValue = "") {
  return projectPane?.renderPractiScoreSelect(selectId, values, emptyLabel, selectedValue);
}

function renderPractiScoreOptionLists(selectedValues = {}) {
  return projectPane?.renderPractiScoreOptionLists(selectedValues);
}

function syncPractiScoreSelectionFields(changedField) {
  return projectPane?.syncPractiScoreSelectionFields(changedField);
}

function durationMs() {
  return waveformStateRuntime?.durationMs() || Math.max(1, state?.project?.primary_video?.duration_ms || 1);
}

function waveformWindow() {
  return waveformStateRuntime?.waveformWindow() || {
    start: waveformOffsetMs,
    end: waveformOffsetMs + durationMs(),
    duration: durationMs(),
  };
}

function persistWaveformViewport() {
  return waveformStateRuntime?.persistWaveformViewport();
}

function setWaveformOffset(nextOffsetMs, { persist = true } = {}) {
  return waveformStateRuntime?.setWaveformOffset(nextOffsetMs, { persist }) ?? false;
}

function centerWaveformOnTime(timeMs, { persist = true } = {}) {
  return waveformStateRuntime?.centerWaveformOnTime(timeMs, { persist }) ?? false;
}

function ensureWaveformTimeVisible(timeMs, { center = false, paddingRatio = 0.12, persist = true } = {}) {
  return waveformStateRuntime?.ensureWaveformTimeVisible(timeMs, { center, paddingRatio, persist }) ?? false;
}

function waveformNavigatorMetrics(track = $("waveform-window-track")) {
  return waveformStateRuntime?.waveformNavigatorMetrics(track) || null;
}

function renderWaveformNavigator() {
  return waveformComponent?.renderWaveformNavigator();
}

function updateWaveformNavigator(clientX) {
  return waveformStateRuntime?.updateWaveformNavigator(clientX) ?? false;
}

function waveformX(timeMs, width) {
  return waveformStateRuntime?.waveformX(timeMs, width) ?? 0;
}

function isWaveformVisible(timeMs) {
  return waveformStateRuntime?.isWaveformVisible(timeMs) ?? false;
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
  void "return statusBarComponent?.renderHeader();";
  const result = statusBarComponent?.renderHeader();
  renderAutomationSurface();
  return result;
}

function renderStats() {
  return statusBarComponent?.renderStats();
}

function timingSummaryRows() {
  return statusBarComponent?.timingSummaryRows();
}

function renderTimingSummary() {
  return statusBarComponent?.renderTimingSummary();
}

function currentSettings() {
  return state?.settings || {};
}

function readNumberSetting(id, defaultValue) {
  const element = $(id);
  if (!element) return defaultValue;
  const value = element.value;
  if (value === "") return defaultValue;
  const numeric = Number(value);
  return Number.isFinite(numeric) ? numeric : defaultValue;
}

function syncSettingsBadgeStyle(prefix, style = {}) {
  if (settingsPane) return settingsPane.syncSettingsBadgeStyle(prefix, style);
  syncControlValue($(`${prefix}-background-color`), style.background_color ?? "#000000");
  syncControlValue($(`${prefix}-text-color`), style.text_color ?? "#ffffff");
  syncControlValue($(`${prefix}-opacity`), style.opacity ?? 0.9);
}

function readSettingsBadgeStyle(prefix) {
  if (settingsPane) return settingsPane.readSettingsBadgeStyle(prefix);
  return {
    background_color: $(`${prefix}-background-color`)?.value || "#000000",
    text_color: $(`${prefix}-text-color`)?.value || "#ffffff",
    opacity: readNumberSetting(`${prefix}-opacity`, 0.9),
  };
}

function syncSettingsMarkerTemplate(template = {}) {
  if (settingsPane) return settingsPane.syncSettingsMarkerTemplate(template);
  syncControlChecked($("settings-marker-enabled"), Boolean(template.enabled ?? true));
  syncControlValue($("settings-marker-content-type"), template.content_type ?? "text");
  syncControlValue($("settings-marker-text-source"), template.text_source ?? "score");
  syncControlValue($("settings-marker-duration"), (Number(template.duration_ms ?? 1000) / 1000).toFixed(3));
  syncControlChecked($("settings-marker-use-shot-split-duration"), Boolean(template.use_shot_split_duration ?? false));
  syncControlValue($("settings-marker-width"), template.width ?? 0);
  syncControlValue($("settings-marker-height"), template.height ?? 0);
  syncControlChecked($("settings-marker-follow-motion"), Boolean(template.follow_motion ?? false));
  syncControlValue($("settings-marker-motion-mode"), Boolean(template.follow_motion ?? false) ? "guided" : "fixed");
  syncControlValue($("settings-marker-background-color"), template.background_color ?? "#000000");
  syncControlValue($("settings-marker-text-color"), template.text_color ?? "#ffffff");
  syncControlValue($("settings-marker-opacity"), template.opacity ?? 0.9);
}

const SETTINGS_LAYER_FIELDS = [
  { label: "Landing pane", path: ["default_tool"] },
  { label: "Reopen last pane", path: ["reopen_last_tool"] },
  { label: "Overlay position", path: ["overlay_position"] },
  { label: "Badge size", path: ["badge_size"] },
  { label: "Composition layout", path: ["merge_layout"] },
  { label: "Layer size", path: ["pip_size"] },
  { label: "Export quality", path: ["export_quality"] },
  { label: "ShotML threshold", path: ["shotml_defaults", "detection_threshold"] },
  {
    label: "Marker enabled",
    path: ["marker_template", "enabled"],
    usesProjectTemplate: true,
    projectPath: ["project", "popup_template", "enabled"],
  },
  {
    label: "Marker content",
    path: ["marker_template", "content_type"],
    usesProjectTemplate: true,
    projectPath: ["project", "popup_template", "content_type"],
  },
  {
    label: "Marker text source",
    path: ["marker_template", "text_source"],
    usesProjectTemplate: true,
    projectPath: ["project", "popup_template", "text_source"],
  },
  {
    label: "Marker duration ms",
    path: ["marker_template", "duration_ms"],
    usesProjectTemplate: true,
    projectPath: ["project", "popup_template", "duration_ms"],
  },
  {
    label: "Marker use shot split duration",
    path: ["marker_template", "use_shot_split_duration"],
    usesProjectTemplate: true,
    projectPath: ["project", "popup_template", "use_shot_split_duration"],
  },
  {
    label: "Marker width",
    path: ["marker_template", "width"],
    usesProjectTemplate: true,
    projectPath: ["project", "popup_template", "width"],
  },
  {
    label: "Marker height",
    path: ["marker_template", "height"],
    usesProjectTemplate: true,
    projectPath: ["project", "popup_template", "height"],
  },
  {
    label: "Marker follow motion",
    path: ["marker_template", "follow_motion"],
    usesProjectTemplate: true,
    projectPath: ["project", "popup_template", "follow_motion"],
  },
  {
    label: "Marker motion mode",
    path: ["marker_template", "motion_mode"],
    usesProjectTemplate: true,
    projectPath: ["project", "popup_template", "motion_mode"],
  },
];

function renderSettingsLayerSummary(settings, markerTemplate, layers) {
  return settingsPane?.renderSettingsLayerSummary(settings, markerTemplate, layers);
}

function renderSettingsPane() {
  return settingsPane?.renderSettingsPane();
}

function mergeSourcePipRect(...args) {
  return mergePane?.mergeSourcePipRect(...args) ?? null;
}

function ensureMergePreviewItem(...args) {
  // media.style.opacity = String(currentSourceOpacity(source));
  return mergePane?.ensureMergePreviewItem(...args) ?? null;
}

function renderMergePreviewLayer(video, stage, mergeSources, pipSizeValue) {
  // Legacy merge-preview contract anchor:
  // if (mergePreview && merge.layout === "pip" && mergeSources.length > 0) {
  return mergePane?.renderMergePreviewLayer(video, stage, mergeSources, pipSizeValue);
}

function syncPreviewPlaybackToTarget(preview, target, targetPlaybackRate, paused) {
  if (!(preview instanceof HTMLMediaElement) || !Number.isFinite(target)) return "noop";
  if (mergePreviewDrag) return "noop";
  const currentTime = Number(preview.currentTime || 0);
  const drift = target - currentTime;
  const absoluteDrift = Math.abs(drift);
  const seekThreshold = paused ? SECONDARY_PREVIEW_PAUSED_SEEK_THRESHOLD_S : SECONDARY_PREVIEW_ACTIVE_SEEK_THRESHOLD_S;
  if (Math.abs((preview.playbackRate || 1) - targetPlaybackRate) > 0.001) {
    preview.playbackRate = targetPlaybackRate;
    preview.defaultPlaybackRate = targetPlaybackRate;
  }
  if (absoluteDrift > seekThreshold) {
    if (previewSeekBoundary) {
      const now = window.performance?.now?.() ?? Date.now();
      const lastSeekAt = secondaryPreviewLastSeekAt.get(preview) || 0;
      if (!paused && now - lastSeekAt < SECONDARY_PREVIEW_MIN_SEEK_INTERVAL_MS) return "boundary-pending";
      try {
        if (typeof preview.fastSeek === "function") preview.fastSeek(target);
        else preview.currentTime = target;
        secondaryPreviewLastSeekAt.set(preview, now);
        preview.dataset.syncCorrectionMode = "reseek";
        if (!previewSeekBoundaryBatchActive) {
          previewSeekBoundary = false;
          previewSyncedSinceBoundary = true;
        }
      } catch {
        // Ignore early metadata seek failures.
        return "boundary-pending";
      }
      return "boundary-reseek";
    }
    const catchUpRate = targetPlaybackRate + (drift > 0 ? SECONDARY_PREVIEW_MAX_PLAYBACK_RATE_DELTA : -SECONDARY_PREVIEW_MAX_PLAYBACK_RATE_DELTA);
    const clampedCatchUp = clamp(catchUpRate, 0.25, 4.0);
    preview.playbackRate = clampedCatchUp;
    preview.defaultPlaybackRate = clampedCatchUp;
    preview.dataset.syncCorrectionMode = "rate-catchup";
    return "rate-catchup";
  }
  if (paused || absoluteDrift <= SECONDARY_PREVIEW_PLAYBACK_RATE_DRIFT_THRESHOLD_S) {
    preview.dataset.syncCorrectionMode = paused ? "paused" : "steady";
    return paused ? "paused" : "steady";
  }
  const nextPlaybackRate = clamp(
    targetPlaybackRate + clamp(drift * 0.5, -SECONDARY_PREVIEW_MAX_PLAYBACK_RATE_DELTA, SECONDARY_PREVIEW_MAX_PLAYBACK_RATE_DELTA),
    0.25,
    4,
  );
  if (Math.abs((preview.playbackRate || 1) - nextPlaybackRate) > 0.001) {
    preview.playbackRate = nextPlaybackRate;
    preview.defaultPlaybackRate = nextPlaybackRate;
    preview.dataset.syncCorrectionMode = "rate";
  }
  return "rate";
}

function syncMergePreviewElements(primary) {
  if (mergePreviewDrag) return;
  const previews = Array.from(document.querySelectorAll("#merge-preview-layer video"));
  if (previews.length === 0) return;
  const targetPlaybackRate = primary.playbackRate || 1;
  const boundaryActive = previewSeekBoundary;
  let boundaryPending = false;
  if (boundaryActive) previewSeekBoundaryBatchActive = true;
  try {
    previews.forEach((preview) => {
      const sourceId = preview.closest(".merge-preview-item")?.dataset.sourceId || "";
      const target = mergePreviewTargetTime(primary.currentTime, mergeSourceById(sourceId));
      const syncStatus = syncPreviewPlaybackToTarget(preview, target, targetPlaybackRate, primary.paused);
      if (boundaryActive && syncStatus === "boundary-pending") boundaryPending = true;
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
  } finally {
    if (boundaryActive) {
      previewSeekBoundaryBatchActive = false;
      previewSeekBoundary = boundaryPending;
      previewSyncedSinceBoundary = !boundaryPending;
    }
  }
}

function syncMergeStageLayoutClasses() {
  const stage = $("video-stage");
  if (!(stage instanceof HTMLElement)) return;
  const merge = state?.project?.merge || {};
  const mergeSources = Array.isArray(state?.project?.merge_sources) ? state.project.merge_sources : [];
  const mergePreview = Boolean(merge.enabled && mergeSources.length > 0);
  const activeLayout = mergePreview ? String(merge.layout || "").trim() : "";
  stage.classList.toggle("merge-side-by-side", activeLayout === "side_by_side");
  stage.classList.toggle("merge-above-below", activeLayout === "above_below");
  stage.classList.toggle("merge-pip", activeLayout === "pip");
  stage.classList.toggle("merge-full-screen-portrait", activeLayout === "full_screen_portrait");
  stage.classList.toggle("merge-dual-center-hud", activeLayout === "dual_center_hud");
  stage.classList.toggle("merge-dual-top-hud", activeLayout === "dual_top_hud");
  if (!mergePreview) {
    stage.classList.toggle("merge-side-by-side", false);
    stage.classList.toggle("merge-above-below", false);
    stage.classList.toggle("merge-pip", false);
    stage.classList.toggle("merge-full-screen-portrait", false);
    stage.classList.toggle("merge-dual-center-hud", false);
    stage.classList.toggle("merge-dual-top-hud", false);
  }
}

function renderVideo() {
  // Legacy static UI contract anchor:
  // return videoPlayerComponent?.renderVideo();
  const result = videoPlayerComponent?.renderVideo();
  syncMergeStageLayoutClasses();
  return result;
}

function syncSecondaryPreview() {
  if (mergePreviewDrag) return;
  const primary = $("primary-video");
  const secondary = $("secondary-video");
  if (!primary || !secondary) return;
  const mergeSourceCount = (state?.project?.merge_sources || []).length;
  const classicSecondaryActive = Boolean(
    state?.media?.secondary_available
      && state.project.merge.enabled
      && secondary.src
      && mergeSourceCount === 0,
  );
  if (!classicSecondaryActive) {
    if (!secondary.paused) secondary.pause();
    clearSecondaryPreviewPlayError();
  } else {
    const target = mergePreviewTargetTime(primary.currentTime, null);
    const targetPlaybackRate = primary.playbackRate || 1;
    syncPreviewPlaybackToTarget(secondary, target, targetPlaybackRate, primary.paused);
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
  return waveformComponent?.waveformCanvasDisplayHeight(canvas) ?? 0;
}

function resizeCanvasToDisplay(canvas) {
  return waveformComponent?.resizeCanvasToDisplay(canvas) ?? { width: 1, height: 1 };
}

function renderWaveformPlayhead(positionMs = currentPrimaryVideoPositionMs()) {
  return waveformComponent?.renderWaveformPlayhead(positionMs);
}

function renderWaveform() {
  return waveformComponent?.renderWaveform();
}

function drawOutlinedText(ctx, text, x, y, fillStyle, font, lineWidth = 3) {
  return waveformComponent?.drawOutlinedText(ctx, text, x, y, fillStyle, font, lineWidth);
}

function drawMarker(ctx, timeMs, color, label, labelColor = "rgba(248, 250, 252, 0.96)", width = null, height = null) {
  return waveformComponent?.drawMarker(ctx, timeMs, color, label, labelColor, width, height);
}

function drawWaveformScale(ctx, visible, width, height) {
  return waveformComponent?.drawWaveformScale(ctx, visible, width, height);
}

function drawSelectedRegion(ctx, width, height) {
  return waveformComponent?.drawSelectedRegion(ctx, width, height);
}

function startWaveformPanDrag(event) {
  return waveformComponent?.startWaveformPanDrag(event);
}

function updateWaveformPanDrag(event) {
  return waveformComponent?.updateWaveformPanDrag(event);
}

function finishWaveformPanDrag(event) {
  return waveformComponent?.finishWaveformPanDrag(event) ?? false;
}

function handleWaveformNavigatorPointerDown(event) {
  return waveformComponent?.handleWaveformNavigatorPointerDown(event);
}

function moveWaveformNavigatorDrag(event) {
  return waveformComponent?.moveWaveformNavigatorDrag(event);
}

function endWaveformNavigatorDrag(event) {
  return waveformComponent?.endWaveformNavigatorDrag(event);
}

function selectShot(shotId, { revealInWaveform = true, centerWaveform = false } = {}) {
  const nextShotId = stateHasShot(state, shotId) ? shotId : null;
  setSelectedShotIdValue(nextShotId);
  if (state?.project?.ui_state) state.project.ui_state.selected_shot_id = nextShotId;
  activity("shot.select", { shot_id: nextShotId });
  const shot = selectedShot();
  if (shot && revealInWaveform) {
    if (ensureWaveformTimeVisible(shot.time_ms, { center: centerWaveform || !isWaveformVisible(shot.time_ms) })) {
      renderWaveform();
    }
  }
  if (shot) {
    let revealedPopup = false;
    if (activeTool === "markers") {
      const activePopup = selectedPopupBubble();
      if (activePopup?.anchor_mode === "shot" && activePopup.shot_id === shot.id) {
        revealedPopup = selectPopupBubble(activePopup.id, {
          seek: true,
          reveal: false,
          focus: false,
          activateTool: false,
          expand: false,
        });
      } else if (!activePopup) {
        revealedPopup = selectPopupBubbleForShot(shot.id, {
          seek: true,
          reveal: false,
          focus: false,
          activateTool: false,
          expand: false,
        });
      }
    }
    if (!revealedPopup) seekPrimaryVideoToTimeMs(shot.time_ms);
  }
  callApi("/api/shots/select", { shot_id: nextShotId });
}

function seekPrimaryVideoToTimeMs(timeMs) {
  const video = $("primary-video");
  if (!(video instanceof HTMLVideoElement) || !state?.media?.primary_available) return false;
  const requestedTimeMs = Math.max(0, Math.round(Number(timeMs) || 0));
  const durationMsValue = Number.isFinite(video.duration) ? Math.max(0, Math.round(video.duration * 1000)) : null;
  const clampedTimeMs = durationMsValue === null ? requestedTimeMs : clamp(requestedTimeMs, 0, durationMsValue);
  const nextTime = clampedTimeMs / 1000;
  try {
    video.currentTime = nextTime;
  } catch {
    try {
      if (typeof video.fastSeek === "function") video.fastSeek(nextTime);
    } catch {
      // Some browsers reject seeks before metadata is ready.
    }
  }
  scheduleSecondaryPreviewSync();
  renderLiveOverlay(clampedTimeMs);
  renderWaveformPlayhead(clampedTimeMs);
  if (activeTool === "markers" && popupFilterMode === "visible") renderPopupEditors();
  return true;
}

function seekPrimaryVideoToShot(shotId) {
  const shot = (state?.project?.analysis?.shots || []).find((item) => item.id === shotId) || null;
  if (!shot) return false;
  return seekPrimaryVideoToTimeMs(shot.time_ms);
}

function selectedShot() {
  return (state?.project?.analysis?.shots || []).find((shot) => shot.id === selectedShotId) || null;
}

function selectedShotRange() {
  return waveformComponent?.selectedShotRange() || null;
}

function waveformAmplitudeForTime(timeMs) {
  return waveformComponent?.waveformAmplitudeForTime(timeMs) ?? 1;
}

function waveformShotSubtitle(segment) {
  return waveformComponent?.waveformShotSubtitle(segment) || "";
}

function renderWaveformShotList() {
  return waveformComponent?.renderWaveformShotList();
}

function shotLabelForEvent(shotId) {
  const shots = orderedShotsByTime();
  const shotIndex = shots.findIndex((shot) => shot.id === shotId);
  const shot = shotIndex >= 0 ? shots[shotIndex] : null;
  if (!shot) return "Any shot";
  return `Shot ${shotIndex + 1} ${seconds(shot.time_ms)}s`;
}

function deleteTimingEvent(eventId) {
  return timingPane?.deleteTimingEvent(eventId);
}

function renderTimingEventList() {
  return timingPane?.renderTimingEventList();
}

function renderTimingEventEditor() {
  return timingPane?.renderTimingEventEditor();
}

function addTimingEvent() {
  return timingPane?.addTimingEvent();
}

function formatTimingValue(value) {
  return value === null || value === undefined ? "--" : String(value);
}

function toggleTimingRowEdit(shotId) {
  const row = (state?.split_rows || []).find((entry) => entry.shot_id === shotId) || null;
  if (timingRowEdits.has(shotId)) {
    const draftValue = String(timingAdjustmentDrafts.get(shotId) ?? "").trim();
    const currentValue = row ? signedSeconds(numericMs(row.adjustment_ms) ?? 0) : "";
    if (draftValue && draftValue !== currentValue) {
      updateTimingRowField(shotId, "adjustment_ms", draftValue);
    }
    timingAdjustmentDrafts.delete(shotId);
    timingRowEdits.delete(shotId);
  } else {
    if (row) {
      timingAdjustmentDrafts.set(shotId, signedSeconds(numericMs(row.adjustment_ms) ?? 0));
    }
    timingRowEdits.add(shotId);
  }
  syncLocalProjectUiState();
  scheduleProjectUiStateApply();
  renderTimingTables();
}

function restoreOriginalSplit(shotId) {
  return timingPane?.restoreOriginalSplit(shotId);
}

function restoreOriginalScore(shotId) {
  setSelectedShotIdValue(shotId);
  callApi("/api/scoring/restore", { shot_id: shotId });
}

function deleteShotById(shotId, source = "selected") {
  return timingPane?.deleteShotById(shotId, source);
}

function updateTimingRowField(shotId, field, value) {
  return timingPane?.updateTimingRowField(shotId, field, value);
}

function signedSeconds(ms) {
  return timingPane?.signedSeconds(ms) ?? "0.00";
}

function splitRowEntryLabel(row) {
  return timingPane?.splitRowEntryLabel(row) || "Entry";
}

function splitRowRangeLabel(row) {
  return timingPane?.splitRowRangeLabel(row) || "Start -> Entry";
}

function splitRowIntervalLabel(row) {
  return timingPane?.splitRowIntervalLabel(row) || "Split";
}

function splitRowSequenceTotalMs(row) {
  return timingPane?.splitRowSequenceTotalMs(row);
}

function splitRowCumulativeMs(row) {
  return timingPane?.splitRowCumulativeMs(row);
}

function splitRowActions(row) {
  return timingPane?.splitRowActions(row) || [];
}

function splitRowActionSummary(row) {
  return timingPane?.splitRowActionSummary(row) || "";
}

function splitRowPrimaryAction(row) {
  return timingPane?.splitRowPrimaryAction(row) || null;
}

function splitRowSecondaryActions(row) {
  return timingPane?.splitRowSecondaryActions(row) || [];
}

function splitRowPrimaryLabel(row) {
  return timingPane?.splitRowPrimaryLabel(row) || "";
}

function splitRowConfidenceLabel(row) {
  return timingPane?.splitRowConfidenceLabel(row) || "--";
}

function splitRowShotMLConfidence(row) {
  return timingPane?.splitRowShotMLConfidence(row) ?? null;
}

function splitRowShotMLSplitMs(row) {
  return timingPane?.splitRowShotMLSplitMs(row);
}

function splitRowShotMLCumulativeMs(row) {
  return timingPane?.splitRowShotMLCumulativeMs(row);
}

function splitRowAdjustmentMs(row) {
  return timingPane?.splitRowAdjustmentMs(row) ?? 0;
}

function splitRowFinalTimeMs(row) {
  return timingPane?.splitRowFinalTimeMs(row);
}

function maximumSplitRowActionLabelLength() {
  return timingPane?.maximumSplitRowActionLabelLength() ?? 8;
}

function buildSplitRowActionCell(row, expandedTable) {
  return timingPane?.buildSplitRowActionCell(row, expandedTable);
}

function buildTimingRowControlCell(row, editing) {
  return timingPane?.buildTimingRowControlCell(row, editing);
}

function buildTimingDeleteCell(row) {
  return timingPane?.buildTimingDeleteCell(row);
}

function buildTimingRestoreCell(row) {
  return timingPane?.buildTimingRestoreCell(row);
}

function renderTimingTable(tableId = "timing-table") {
  const table = $(tableId);
  if (!table) return;
  syncSelectedShotId();
  withPreservedScrollState([table], () => {
    table.innerHTML = "";
    const expandedTable = tableId === "timing-workbench-table";
    const compactEnabled = $("timing-enabled")?.checked ?? true;
    if (!expandedTable && !compactEnabled) {
      applyTimingTableColumns(table);
      return;
    }
    table.classList.toggle("interval-timeline-table", true);
    table.classList.toggle("timing-resizable-table", expandedTable);
    applyTimingTableColumns(table);
    if (expandedTable) {
      table.style.setProperty("--timing-action-chip-chars", String(maximumSplitRowActionLabelLength()));
    } else {
      table.style.removeProperty("--timing-action-chip-chars");
    }
    const headers = expandedTable
      ? [
        { label: "Edit", columnId: "lock", resizable: false },
        { label: "Segment", columnId: "segment", resizable: true },
        { label: "Split", columnId: "split", resizable: true },
        { label: "Total", columnId: "total", resizable: true },
        { label: "Action", columnId: "action", resizable: true },
        { label: "ShotML Confidence %", columnId: "confidence", resizable: true },
        { label: "Adjustment", columnId: "adjustment", resizable: true },
        { label: "Final Time", columnId: "final", resizable: true },
        { label: "Delete", columnId: "delete", resizable: false },
        { label: "Restore", columnId: "restore", resizable: false },
      ]
      : [
        { label: "Segment", columnId: "segment", resizable: false },
        { label: "Split", columnId: "split", resizable: false },
        { label: "Total", columnId: "total", resizable: false },
        { label: "Action", columnId: "action", resizable: false },
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
      const shotmlConfidence = splitRowShotMLConfidence(row);
      const lowConfidence = isLowConfidence(shotmlConfidence, "auto");
      if (expandedTable) {
        table.appendChild(buildTimingRowControlCell(row, editing));
      }

      const entryCell = document.createElement("div");
      entryCell.classList.add("timeline-segment-cell");
      entryCell.textContent = splitRowEntryLabel(row);
      if (row.shot_id === selectedShotId) entryCell.classList.add("selected");
      if (canEdit) entryCell.addEventListener("click", () => selectShot(row.shot_id));
      table.appendChild(entryCell);

      const splitCell = document.createElement("div");
      splitCell.textContent = splitSeconds(numericMs(row.split_ms));
      table.appendChild(splitCell);

      const totalCell = document.createElement("div");
      totalCell.textContent = splitSeconds(splitRowCumulativeMs(row));
      table.appendChild(totalCell);

      const actionCell = buildSplitRowActionCell(row, expandedTable);
      if (row.shot_id === selectedShotId) actionCell.classList.add("selected");
      if (canEdit) actionCell.addEventListener("click", () => selectShot(row.shot_id));
      table.appendChild(actionCell);

      if (!expandedTable) return;

      const confidenceCell = document.createElement("div");
      confidenceCell.textContent = splitRowConfidenceLabel(row);
      if (lowConfidence) {
        confidenceCell.title = shotmlConfidence === null || shotmlConfidence === undefined
          ? "No ShotML confidence value recorded."
          : `Review this split manually: ShotML confidence ${formatConfidenceValue(shotmlConfidence)}.`;
      }
      table.appendChild(confidenceCell);

      const adjustmentCell = document.createElement("div");
      const adjustmentMs = splitRowAdjustmentMs(row);
      if (editing) {
        adjustmentCell.classList.add("timing-edit-cell");
        const editor = document.createElement("span");
        editor.className = "timing-edit-control";
        const input = document.createElement("input");
        input.type = "number";
        input.inputMode = "decimal";
        input.step = "0.01";
        input.className = "timing-adjustment-input";
        input.dataset.timingRowField = "adjustment-seconds";
        input.dataset.timingShotId = row.shot_id;
        input.value = String(timingAdjustmentDrafts.get(row.shot_id) ?? signedSeconds(adjustmentMs));
        input.setAttribute("aria-label", `Adjustment for ${splitRowEntryLabel(row)}`);
        input.title = "Edit the adjustment in seconds, for example +0.06 or -0.06.";
        input.addEventListener("input", () => {
          timingAdjustmentDrafts.set(row.shot_id, String(input.value ?? "").trim());
        });
        editor.append(input);
        adjustmentCell.appendChild(editor);
      } else {
        adjustmentCell.textContent = signedSeconds(adjustmentMs);
      }
      table.appendChild(adjustmentCell);

      const finalCell = document.createElement("div");
      finalCell.textContent = splitSeconds(splitRowFinalTimeMs(row));
      table.appendChild(finalCell);

      table.appendChild(buildTimingDeleteCell(row));
      table.appendChild(buildTimingRestoreCell(row));
    });
  });
  applyTimingTableColumns(table);
}

function renderTimingTables() {
  renderTimingSummary();
  renderTimingTable("timing-table");
  renderTimingTable("timing-workbench-table");
  renderTimingEventEditor();
}

function scoringWorkbenchShown() {
  return scoringPane?.scoringWorkbenchShown() ?? Boolean(scoringWorkbenchExpanded);
}

function setScoringWorkbenchExpanded(expanded, { persistUiState = true } = {}) {
  return scoringPane?.setScoringWorkbenchExpanded(expanded, { persistUiState }) ?? Boolean(expanded);
}

function markersWorkbenchShown() {
  return Boolean($("cockpit-root")?.classList.contains("markers-expanded"));
}

function popupEditingActive() {
  return activeTool === "markers" && markersWorkbenchShown();
}

function setMarkersExpanded(expanded, { persistUiState = true } = {}) {
  return markersPane?.setMarkersExpanded(expanded, { persistUiState });
}

function renderScoringTable(tableId = "scoring-table") {
  return scoringPane?.renderScoringTable(tableId);
}

function renderScoringTables() {
  return scoringPane?.renderScoringTables();
}

function renderScoringPresetOptions() {
  return scoringPane?.renderScoringPresetOptions();
}

function renderScoringPresetDescription() {
  return scoringPane?.renderScoringPresetDescription();
}

function renderPractiScoreSummaries() {
  projectPane?.renderPractiScoreImportSummary?.();
  return scoringPane?.renderPractiScoreSummaries();
}

function renderExportPresetOptions(selectId = "export-preset", descriptionId = "export-preset-description", selectedValue = state?.project?.export?.preset) {
  return exportPane?.renderExportPresetOptions(selectId, descriptionId, selectedValue);
}

function renderExportLog() {
  return exportPane?.renderExportLog();
}

function openExportLogModal() {
  return exportPane?.openExportLogModal();
}

function closeExportLogModal() {
  return exportPane?.closeExportLogModal();
}

function downloadExportLog() {
  return exportPane?.downloadExportLog();
}

function buildMetricsRows() {
  if (metricsPane) return metricsPane.buildMetricsRows();
  const segmentsByShotId = new Map((state.timing_segments || []).map((segment) => [segment.shot_id, segment]));
  const beepMs = numericMs(state?.metrics?.beep_ms);
  const defaultScore = defaultScoreLetter();
  const importedRawSeconds = state?.scoring_summary?.imported_stage?.raw_seconds;
  const importedRawMs = importedRawSeconds === null || importedRawSeconds === undefined
    ? null
    : Math.round(Number(importedRawSeconds) * 1000);
  const shotRows = (state.split_rows || []).filter((item) => item.shot_id);
  const finalShotRowId = shotRows.length ? shotRows[shotRows.length - 1].shot_id : null;
  return (state.split_rows || []).map((row) => {
    const segment = row.shot_id ? (segmentsByShotId.get(row.shot_id) || null) : null;
    const absoluteMs = numericMs(row.absolute_time_ms);
    const fallbackCumulativeMs = numericMs(segment?.cumulative_ms) ?? (
      absoluteMs === null
        ? null
        : (beepMs === null ? absoluteMs : Math.max(0, absoluteMs - beepMs))
    );
    const confidence = splitRowShotMLConfidence(row);
    const shotmlSplitMs = splitRowShotMLSplitMs(row);
    const adjustmentMs = numericMs(row.adjustment_ms) ?? 0;
    const finalTimeMs = splitRowFinalTimeMs(row);
    const finalSplitMs = numericMs(row.split_ms);
    const shotmlCumulativeMs = splitRowShotMLCumulativeMs(row);
    const rawDeltaMs = importedRawMs === null || finalTimeMs === null || row.shot_id !== finalShotRowId
      ? null
      : finalTimeMs - importedRawMs;
    const penaltyCounts = segment?.penalty_counts || row.penalty_counts;
    return {
      rowId: row.row_id,
      rowType: row.row_type,
      shotId: row.shot_id,
      shotNumber: row.shot_number,
      label: splitRowEntryLabel(row),
      intervalLabel: splitRowIntervalLabel(row),
      intervalKind: String(row.interval_kind || ""),
      absoluteMs,
      splitMs: finalSplitMs,
      shotmlSplitMs,
      adjustmentMs,
      sequenceTotalMs: splitRowSequenceTotalMs(row),
      cumulativeMs: finalTimeMs ?? numericMs(row.cumulative_ms) ?? fallbackCumulativeMs,
      shotmlCumulativeMs,
      actionSummary: splitRowActionSummary(row),
      actions: splitRowActions(row).map((action) => ({
        eventId: action.event_id || null,
        kind: action.kind || "",
        label: action.label || "",
        placement: action.placement || "interval",
        synthetic: Boolean(action.synthetic),
        resetsSequence: Boolean(action.resets_sequence),
      })),
      resetsSequence: Boolean(row.resets_sequence),
      scoreLetter: segment?.score_letter || row.score_letter || defaultScore,
      penaltyText: formatPenaltyCountsText(penaltyCounts),
      confidence,
      practiscoreMs: importedRawMs,
      rawDeltaMs,
    };
  });
}

function metricsPractiScoreLabel(entry) {
  if (entry.rawDeltaMs === null || entry.rawDeltaMs === undefined) return "--";
  const prefix = entry.rawDeltaMs > 0 ? "+" : "";
  return `${prefix}${precise(entry.rawDeltaMs)}s`;
}

function renderMetricsTable(table) {
  if (metricsPane) return metricsPane.renderMetricsTable(table);
  if (!table) return;
  table.innerHTML = "";
  const rows = buildMetricsRows();
  table.style.gridTemplateColumns = "minmax(0, 1.15fr) minmax(0, 0.72fr) minmax(0, 0.72fr) minmax(0, 0.72fr) minmax(0, 0.72fr) minmax(0, 0.48fr) minmax(0, 1fr) minmax(0, 0.7fr) minmax(0, 0.7fr) minmax(0, 0.7fr) minmax(0, 1.15fr)";
  METRICS_TABLE_COLUMNS.forEach(([label]) => {
    const header = document.createElement("div");
    header.className = "head";
    header.textContent = label;
    table.appendChild(header);
  });
  rows.forEach((entry) => {
    const cells = [
      entry.label,
      splitSeconds(entry.shotmlSplitMs),
      signedSeconds(entry.adjustmentMs || 0),
      splitSeconds(entry.splitMs),
      splitSeconds(entry.cumulativeMs),
      entry.scoreLetter || "--",
      entry.penaltyText || "--",
      entry.practiscoreMs === null || entry.practiscoreMs === undefined ? "--" : splitSeconds(entry.practiscoreMs),
      metricsPractiScoreLabel(entry),
      formatConfidenceValue(entry.confidence),
      entry.actionSummary || "--",
    ];
    cells.forEach((value) => {
      const cell = document.createElement("div");
      cell.textContent = value || "--";
      table.appendChild(cell);
    });
  });
}

function renderMetricsTrendTable(table) {
  if (metricsPane) return metricsPane.renderMetricsTrendTable(table);
  if (!table) return;
  table.innerHTML = "";
  const rows = buildMetricsRows();
  table.style.gridTemplateColumns = "minmax(0, 1.1fr) minmax(0, 0.68fr) minmax(0, 0.68fr) minmax(0, 0.5fr) minmax(0, 0.72fr) minmax(0, 1.05fr)";
  ["Shot", "Split", "Run", "Score", "ShotML", "Action"].forEach((label) => {
    const header = document.createElement("div");
    header.className = "head";
    header.textContent = label;
    table.appendChild(header);
  });
  if (rows.length === 0) {
    const empty = document.createElement("div");
    empty.className = "metrics-table-empty";
    empty.textContent = "No timing segments yet.";
    table.appendChild(empty);
    return;
  }
  rows.forEach((entry) => {
    [
      entry.intervalLabel ? `${entry.label} ${entry.intervalLabel}` : entry.label,
      splitSeconds(entry.splitMs),
      splitSeconds(entry.sequenceTotalMs),
      entry.scoreLetter || "--",
      formatConfidenceValue(entry.confidence),
      entry.actionSummary || "--",
    ].forEach((value) => {
      const cell = document.createElement("div");
      cell.textContent = value || "--";
      table.appendChild(cell);
    });
  });
}

function metricsSecondsValue(value) {
  if (value === null || value === undefined || value === "") return null;
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return null;
  return Number((numeric / 1000).toFixed(3));
}

function metricsPercentValue(value) {
  if (value === null || value === undefined || value === "") return null;
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return null;
  return Number((numeric * 100).toFixed(1));
}

function metricsMedian(values = []) {
  const sorted = values
    .map((value) => Number(value))
    .filter((value) => Number.isFinite(value))
    .sort((left, right) => left - right);
  if (sorted.length === 0) return null;
  const middle = Math.floor(sorted.length / 2);
  if (sorted.length % 2 === 1) return sorted[middle];
  return Number((((sorted[middle - 1] + sorted[middle]) / 2)).toFixed(3));
}

function metricsCategoryDefinition(id) {
  return {
    first_shot: { id: "first_shot", label: "First shot", shortLabel: "First", color: "#f59e0b" },
    shooting_interval: { id: "shooting_interval", label: "Shooting interval", shortLabel: "Shoot", color: "#39d06f" },
    transition: { id: "transition", label: "Transition / movement", shortLabel: "Move", color: "#4ea7ff" },
    reload_manipulation: { id: "reload_manipulation", label: "Reload / manipulation", shortLabel: "Reload", color: "#ef4444" },
    dead_time: { id: "dead_time", label: "Dead time", shortLabel: "Dead", color: "#f97316" },
    unknown: { id: "unknown", label: "Unknown", shortLabel: "Unknown", color: "#a855f7" },
  }[id] || { id: "unknown", label: "Unknown", shortLabel: "Unknown", color: "#a855f7" };
}

function metricsIntervalText(entry) {
  return [
    String(entry.intervalKind || ""),
    String(entry.intervalLabel || ""),
    String(entry.actionSummary || ""),
    ...(entry.actions || []).map((action) => `${action.kind || ""} ${action.label || ""}`),
  ]
    .join(" ")
    .trim()
    .toLowerCase();
}

function metricsMeaningfulIntervalLabel(entry) {
  const label = String(entry.intervalLabel || "").trim();
  if (!label || ["Draw", "Split", "Start"].includes(label)) return "";
  return label;
}

function metricsCadenceBaselineMs(entries = []) {
  const candidates = entries
    .filter((entry) => Number(entry.shotNumber || 0) > 1)
    .filter((entry) => numericMs(entry.splitMs) !== null)
    .filter((entry) => {
      const kind = String(entry.intervalKind || "").trim().toLowerCase();
      return !["reload", "malfunction", "custom_label"].includes(kind);
    })
    .map((entry) => Number(entry.splitMs))
    .filter((value) => value > 0)
    .sort((left, right) => left - right);
  const sample = candidates.slice(0, Math.max(1, Math.ceil(candidates.length * 0.6)));
  const baseline = metricsMedian(sample.length > 0 ? sample : candidates);
  return baseline === null ? 350 : Math.max(120, baseline);
}

function metricsIntervalClassification(entry, { cadenceBaselineMs = 350 } = {}) {
  const kind = String(entry.intervalKind || "").trim().toLowerCase();
  const labelText = metricsIntervalText(entry);
  const splitMs = numericMs(entry.splitMs);
  const transitionThresholdMs = Math.max(360, cadenceBaselineMs * 1.75);
  const deadTimeThresholdMs = Math.max(900, cadenceBaselineMs * 4.25);

  if (Number(entry.shotNumber || 0) === 1 || kind === "draw" || kind === "start") {
    return metricsCategoryDefinition("first_shot");
  }
  if (
    kind === "reload"
    || kind === "malfunction"
    || /(reload|malfunction|clear|rack|stoppage|jam|manip|mag\b)/.test(labelText)
  ) {
    return metricsCategoryDefinition("reload_manipulation");
  }
  if (/(transition|move|movement|position|entry|exit|cross|sprint|step|turn)/.test(labelText)) {
    return metricsCategoryDefinition("transition");
  }
  if (splitMs !== null && splitMs >= deadTimeThresholdMs) {
    return metricsCategoryDefinition("dead_time");
  }
  if (kind === "custom_label") {
    return metricsCategoryDefinition("unknown");
  }
  if (splitMs !== null && splitMs <= transitionThresholdMs) {
    return metricsCategoryDefinition("shooting_interval");
  }
  if (splitMs !== null) {
    return metricsCategoryDefinition("transition");
  }
  return metricsCategoryDefinition("unknown");
}

function metricsSegmentShortLabel(label) {
  const normalized = String(label || "").trim();
  if (!normalized) return "Segment";
  if (normalized.startsWith("Shooting sequence")) return normalized.replace("Shooting sequence", "Seq");
  if (normalized === "Start / first shot") return "Start";
  if (normalized === "Transition / movement") return "Move";
  if (normalized === "Reload / manipulation") return "Reload";
  if (normalized === "Dead time") return "Dead";
  if (normalized.length <= 10) return normalized;
  return `${normalized.slice(0, 9).trimEnd()}…`;
}

function metricsStageSegmentLabel(point, category = point.category) {
  const customLabel = metricsMeaningfulIntervalLabel(point);
  if (category.id === "first_shot") return "Start / first shot";
  if (category.id === "reload_manipulation") return "Reload / manipulation";
  if (category.id === "transition") return customLabel || "Transition / movement";
  if (category.id === "dead_time") return customLabel || "Dead time";
  if (category.id === "unknown") return customLabel || "Unknown";
  return category.label;
}

function buildMetricsStageSegments(points = []) {
  const segments = [];
  let sequenceIndex = 0;
  let shootingSequence = null;
  const flushShootingSequence = () => {
    if (!shootingSequence) return;
    segments.push(shootingSequence);
    shootingSequence = null;
  };

  points.forEach((point) => {
    const durationS = Number(point.finalSplitS);
    if (!Number.isFinite(durationS)) return;
    if (point.category.id === "shooting_interval") {
      if (!shootingSequence) {
        sequenceIndex += 1;
        shootingSequence = {
          key: `shooting_sequence_${sequenceIndex}`,
          label: `Shooting sequence ${sequenceIndex}`,
          shortLabel: `Seq ${sequenceIndex}`,
          value: 0,
          category: metricsCategoryDefinition("shooting_interval"),
          pairLabels: [],
        };
      }
      shootingSequence.value = Number((shootingSequence.value + durationS).toFixed(3));
      shootingSequence.pairLabels.push(point.pairLabel);
      return;
    }

    flushShootingSequence();
    const label = metricsStageSegmentLabel(point, point.category);
    segments.push({
      key: `${point.category.id}_${point.shotNumber}`,
      label,
      shortLabel: metricsSegmentShortLabel(label),
      value: durationS,
      category: point.category,
      pairLabels: [point.pairLabel],
    });
  });

  flushShootingSequence();
  return segments;
}

function metricsGraphLabel(entry, fallbackShotNumber) {
  const shotNumber = entry.shotNumber || fallbackShotNumber;
  if (entry.intervalLabel) return `${entry.label} ${entry.intervalLabel}`;
  if (entry.label) return entry.label;
  return `Shot ${shotNumber}`;
}

function buildMetricsGraphSeries(rows = buildMetricsRows()) {
  if (metricsPane) return metricsPane.buildMetricsGraphSeries(rows);
  const shotRows = rows.filter((entry) => entry.shotId);
  if (shotRows.length === 0) return [];
  const cadenceBaselineMs = metricsCadenceBaselineMs(shotRows);
  const graphPoints = shotRows.map((entry, index) => {
    const shotNumber = entry.shotNumber || index + 1;
    const category = metricsIntervalClassification(entry, { cadenceBaselineMs });
    const runTotalS = metricsSecondsValue(entry.cumulativeMs);
    const referenceRunS = metricsSecondsValue(entry.shotmlCumulativeMs);
    return {
      shotNumber,
      label: metricsGraphLabel(entry, index + 1),
      pairLabel: shotNumber === 1 ? "Start→1" : `${shotNumber - 1}→${shotNumber}`,
      intervalKind: entry.intervalKind,
      intervalLabel: entry.intervalLabel,
      actionSummary: entry.actionSummary,
      finalSplitS: metricsSecondsValue(entry.splitMs),
      shotmlSplitS: metricsSecondsValue(entry.shotmlSplitMs),
      runTotalS,
      referenceRunS,
      confidencePct: metricsPercentValue(entry.confidence),
      category,
      referenceDeltaS: runTotalS === null || referenceRunS === null
        ? null
        : Number((runTotalS - referenceRunS).toFixed(3)),
    };
  });
  const buildLine = (key, label, color) => ({
    key,
    label,
    color,
    points: graphPoints
      .filter((point) => point[key] !== null && point[key] !== undefined)
      .map((point) => ({ shotNumber: point.shotNumber, label: point.label, value: point[key] })),
  });
  const largestGapPoint = graphPoints.reduce((largest, point) => {
    if (!largest) return point;
    return Number(point.finalSplitS || 0) > Number(largest.finalSplitS || 0) ? point : largest;
  }, null);
  const intervalBars = graphPoints
    .filter((point) => point.shotNumber > 1 && point.finalSplitS !== null && point.finalSplitS !== undefined)
    .map((point) => ({
      key: point.pairLabel,
      label: point.pairLabel,
      shortLabel: point.pairLabel,
      value: point.finalSplitS,
      category: point.category,
      detail: point.intervalLabel || point.category.label,
      highlight: largestGapPoint?.shotNumber === point.shotNumber,
    }));
  const intervalMedian = metricsMedian(intervalBars.map((bar) => bar.value));
  const stageSegments = buildMetricsStageSegments(graphPoints).map((segment, index) => ({
    key: segment.key || `segment_${index + 1}`,
    label: segment.label,
    shortLabel: segment.shortLabel,
    value: segment.value,
    category: segment.category,
    highlight: false,
  }));
  const largestStageSegment = stageSegments.reduce((largest, segment) => {
    if (!largest) return segment;
    return Number(segment.value || 0) > Number(largest.value || 0) ? segment : largest;
  }, null);
  stageSegments.forEach((segment) => {
    if (!largestStageSegment) return;
    segment.highlight = segment.key === largestStageSegment.key;
  });
  const finalPoint = graphPoints[graphPoints.length - 1] || null;
  const largestDeltaPoint = graphPoints
    .filter((point) => point.referenceDeltaS !== null && point.referenceDeltaS !== undefined)
    .reduce((largest, point) => {
      if (!largest) return point;
      return Math.abs(Number(point.referenceDeltaS || 0)) > Math.abs(Number(largest.referenceDeltaS || 0)) ? point : largest;
    }, null);
  const shootingTotalS = stageSegments
    .filter((segment) => segment.category.id === "shooting_interval")
    .reduce((total, segment) => total + Number(segment.value || 0), 0);
  const nonShootingTotalS = stageSegments
    .filter((segment) => segment.category.id !== "shooting_interval")
    .reduce((total, segment) => total + Number(segment.value || 0), 0);

  const graphs = [
    {
      id: "shot_interval_timeline",
      type: "timeline",
      title: "Shot / Interval Timeline",
      subtitle: "Start signal to last shot, with dead time made obvious",
      unit: "s",
      points: graphPoints.map((point) => ({
        ...point,
        value: point.runTotalS,
        highlight: largestGapPoint?.shotNumber === point.shotNumber,
      })),
      summary: [
        { label: "Start→1", value: metricsGraphValueLabel(graphPoints[0]?.runTotalS ?? null, "s"), color: graphPoints[0]?.category?.color },
        { label: `Largest ${largestGapPoint?.pairLabel || "gap"}`, value: metricsGraphValueLabel(largestGapPoint?.finalSplitS ?? null, "s"), color: largestGapPoint?.category?.color },
        { label: "Last shot", value: metricsGraphValueLabel(finalPoint?.runTotalS ?? null, "s"), color: finalPoint?.category?.color },
      ],
      forceZeroMin: true,
    },
    {
      id: "split_interval_bars",
      type: "bars",
      title: "Split / Interval Bar Chart",
      subtitle: "Each shot pair shows where time was lost",
      unit: "s",
      bars: intervalBars,
      summary: [
        { label: "Median", value: metricsGraphValueLabel(intervalMedian, "s"), color: "#39d06f" },
        { label: `Largest ${largestGapPoint?.pairLabel || "gap"}`, value: metricsGraphValueLabel(largestGapPoint?.finalSplitS ?? null, "s"), color: largestGapPoint?.category?.color },
        { label: "Cadence ref", value: metricsGraphValueLabel(metricsSecondsValue(cadenceBaselineMs), "s"), color: "#4ea7ff" },
      ],
    },
    {
      id: "run_comparison_overlay",
      type: "lines",
      title: "Run Comparison Overlay",
      subtitle: "Current cumulative time vs the ShotML reference baseline",
      unit: "s",
      lines: [
        buildLine("runTotalS", "Current", "#ff7b22"),
        buildLine("referenceRunS", "ShotML Reference", "#4ea7ff"),
      ],
      summary: [
        { label: "Current", value: metricsGraphValueLabel(finalPoint?.runTotalS ?? null, "s"), color: "#ff7b22" },
        { label: "Reference", value: metricsGraphValueLabel(finalPoint?.referenceRunS ?? null, "s"), color: "#4ea7ff" },
        { label: "Final delta", value: metricsSignedValueLabel(finalPoint?.referenceDeltaS ?? null, "s"), color: largestDeltaPoint?.referenceDeltaS !== null && largestDeltaPoint?.referenceDeltaS !== undefined ? (largestDeltaPoint.referenceDeltaS > 0 ? "#ef4444" : "#39d06f") : "#a855f7" },
      ],
      forceZeroMin: true,
    },
    {
      id: "stage_segment_breakdown",
      type: "bars",
      title: "Stage Segment Breakdown",
      subtitle: "Grouped into first shot, shooting, movement, reload, and dead time",
      unit: "s",
      bars: stageSegments,
      summary: [
        { label: `Largest ${largestStageSegment?.shortLabel || "segment"}`, value: metricsGraphValueLabel(largestStageSegment?.value ?? null, "s"), color: largestStageSegment?.category?.color },
        { label: "Shooting", value: metricsGraphValueLabel(Number(shootingTotalS.toFixed(3)), "s"), color: metricsCategoryDefinition("shooting_interval").color },
        { label: "Non-shooting", value: metricsGraphValueLabel(Number(nonShootingTotalS.toFixed(3)), "s"), color: metricsCategoryDefinition("transition").color },
      ],
    },
  ];
  return graphs
    .map((graph) => ({
      ...graph,
      lines: Array.isArray(graph.lines)
        ? graph.lines.filter((line) => line.points.length > 0)
        : [],
    }))
    .filter((graph) => {
      if (graph.type === "timeline") return Array.isArray(graph.points) && graph.points.length > 0;
      if (graph.type === "bars") return Array.isArray(graph.bars) && graph.bars.length > 0;
      return graph.lines.length > 0;
    });
}

function metricsGraphValueLabel(value, unit) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return "--";
  const numeric = Number(value);
  if (unit === "%") return `${numeric.toFixed(1)}%`;
  return `${numeric.toFixed(3)}s`;
}

function metricsSignedValueLabel(value, unit) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return "--";
  const numeric = Number(value);
  const prefix = numeric > 0 ? "+" : "";
  if (unit === "%") return `${prefix}${numeric.toFixed(1)}%`;
  return `${prefix}${numeric.toFixed(3)}s`;
}

function createSvgNode(tagName) {
  return document.createElementNS("http://www.w3.org/2000/svg", tagName);
}

function metricsGraphRange(lines, unit, { forceZeroMin = false } = {}) {
  const values = lines.flatMap((line) => line.points.map((point) => point.value)).filter((value) => Number.isFinite(value));
  if (values.length === 0) return null;
  let min = Math.min(...values);
  let max = Math.max(...values);
  if (unit === "%") {
    min = Math.min(0, min);
    max = Math.max(100, max);
  }
  if (forceZeroMin || (unit !== "%" && values.every((value) => value >= 0))) {
    min = Math.min(0, min);
  }
  if (min === max) {
    const padding = min === 0 ? 1 : Math.max(0.5, Math.abs(min) * 0.15);
    min -= padding;
    max += padding;
  }
  return { min, max };
}

function metricsGraphSummaryItems(graph) {
  if (Array.isArray(graph.summary) && graph.summary.length > 0) return graph.summary;
  return (graph.lines || []).map((line) => {
    const lastPoint = line.points[line.points.length - 1] || null;
    return {
      label: line.label,
      value: metricsGraphValueLabel(lastPoint?.value ?? null, graph.unit),
      color: line.color,
    };
  });
}

function appendMetricsSvgTitle(node, text) {
  if (!node || !text) return;
  const title = createSvgNode("title");
  title.textContent = text;
  node.appendChild(title);
}

function createMetricsGraphCanvas({ compact = true } = {}) {
  const svg = createSvgNode("svg");
  svg.classList.add("metrics-graph-svg");
  svg.setAttribute("viewBox", compact ? "0 0 260 132" : "0 0 320 150");
  svg.setAttribute("preserveAspectRatio", "none");
  const viewWidth = compact ? 260 : 320;
  const viewHeight = compact ? 132 : 150;
  const padding = { left: 12, right: 10, top: 10, bottom: 22 };
  const plotWidth = viewWidth - padding.left - padding.right;
  const plotHeight = viewHeight - padding.top - padding.bottom;
  return { svg, viewWidth, viewHeight, padding, plotWidth, plotHeight };
}

function shouldRenderMetricsAxisLabel(index, count, compact, highlighted = false) {
  if (highlighted || count <= 1 || index === 0 || index === count - 1) return true;
  const step = Math.ceil(count / (compact ? 4 : 6));
  return step <= 1 ? true : index % step === 0;
}

function renderMetricsLineGraphSvg(graph, { compact = true } = {}) {
  const range = metricsGraphRange(graph.lines || [], graph.unit, { forceZeroMin: graph.forceZeroMin !== false });
  if (!range) return null;
  const { svg, viewWidth, viewHeight, padding, plotWidth, plotHeight } = createMetricsGraphCanvas({ compact });
  const pointCount = Math.max(...graph.lines.map((line) => line.points.length));
  const xFor = (index) => padding.left + (pointCount <= 1 ? plotWidth / 2 : (index / (pointCount - 1)) * plotWidth);
  const yFor = (value) => padding.top + ((range.max - value) / Math.max(0.0001, range.max - range.min)) * plotHeight;

  [0, 0.5, 1].forEach((ratio) => {
    const y = padding.top + (plotHeight * ratio);
    const gridLine = createSvgNode("line");
    gridLine.setAttribute("x1", String(padding.left));
    gridLine.setAttribute("x2", String(viewWidth - padding.right));
    gridLine.setAttribute("y1", String(y));
    gridLine.setAttribute("y2", String(y));
    gridLine.setAttribute("class", "metrics-graph-grid-line");
    svg.appendChild(gridLine);
  });

  graph.lines.forEach((line) => {
    const polyline = createSvgNode("polyline");
    polyline.setAttribute(
      "points",
      line.points.map((point, index) => `${xFor(index)},${yFor(point.value)}`).join(" "),
    );
    polyline.setAttribute("fill", "none");
    polyline.setAttribute("stroke", line.color);
    polyline.setAttribute("stroke-width", compact ? "2" : "2.5");
    polyline.setAttribute("stroke-linejoin", "round");
    polyline.setAttribute("stroke-linecap", "round");
    polyline.setAttribute("class", "metrics-graph-line");
    appendMetricsSvgTitle(polyline, `${line.label}: ${line.points.map((point) => `Shot ${point.shotNumber} ${metricsGraphValueLabel(point.value, graph.unit)}`).join(" • ")}`);
    svg.appendChild(polyline);
    line.points.forEach((point, index) => {
      const dot = createSvgNode("circle");
      dot.setAttribute("cx", String(xFor(index)));
      dot.setAttribute("cy", String(yFor(point.value)));
      dot.setAttribute("r", compact ? "3" : "3.5");
      dot.setAttribute("fill", line.color);
      dot.setAttribute("class", "metrics-graph-dot");
      appendMetricsSvgTitle(dot, `${line.label} • Shot ${point.shotNumber}: ${metricsGraphValueLabel(point.value, graph.unit)}`);
      svg.appendChild(dot);
    });
  });

  const firstLabel = graph.axisStartLabel || (graph.lines[0]?.points[0]?.shotNumber !== undefined ? `Shot ${graph.lines[0].points[0].shotNumber}` : "");
  const lastPoint = graph.lines[0]?.points[graph.lines[0].points.length - 1] || null;
  const lastLabel = graph.axisEndLabel || (lastPoint?.shotNumber !== undefined ? `Shot ${lastPoint.shotNumber}` : "");
  if (firstLabel) {
    const firstText = createSvgNode("text");
    firstText.setAttribute("x", String(padding.left));
    firstText.setAttribute("y", String(viewHeight - 6));
    firstText.setAttribute("text-anchor", "start");
    firstText.setAttribute("class", "metrics-graph-axis-label");
    firstText.textContent = firstLabel;
    svg.appendChild(firstText);
  }
  if (lastLabel) {
    const lastText = createSvgNode("text");
    lastText.setAttribute("x", String(viewWidth - padding.right));
    lastText.setAttribute("y", String(viewHeight - 6));
    lastText.setAttribute("text-anchor", "end");
    lastText.setAttribute("class", "metrics-graph-axis-label");
    lastText.textContent = lastLabel;
    svg.appendChild(lastText);
  }
  return svg;
}

function renderMetricsTimelineGraphSvg(graph, { compact = true } = {}) {
  const points = (graph.points || []).filter((point) => point.value !== null && point.value !== undefined);
  if (points.length === 0) return null;
  const { svg, viewWidth, viewHeight, padding, plotWidth, plotHeight } = createMetricsGraphCanvas({ compact });
  const totalValue = Math.max(...points.map((point) => Number(point.value || 0)), 0.001);
  const baselineY = padding.top + (plotHeight / 2);
  const xForValue = (value) => padding.left + ((Number(value || 0) / totalValue) * plotWidth);

  const baseline = createSvgNode("line");
  baseline.setAttribute("x1", String(padding.left));
  baseline.setAttribute("x2", String(viewWidth - padding.right));
  baseline.setAttribute("y1", String(baselineY));
  baseline.setAttribute("y2", String(baselineY));
  baseline.setAttribute("class", "metrics-graph-baseline");
  svg.appendChild(baseline);

  const startDot = createSvgNode("circle");
  startDot.setAttribute("cx", String(padding.left));
  startDot.setAttribute("cy", String(baselineY));
  startDot.setAttribute("r", compact ? "2.5" : "3");
  startDot.setAttribute("fill", "#f8fafc");
  startDot.setAttribute("class", "metrics-graph-timeline-start");
  appendMetricsSvgTitle(startDot, "Start 0.000s");
  svg.appendChild(startDot);

  let previousX = padding.left;
  points.forEach((point, index) => {
    const x = xForValue(point.value);
    const segment = createSvgNode("line");
    segment.setAttribute("x1", String(previousX));
    segment.setAttribute("x2", String(x));
    segment.setAttribute("y1", String(baselineY));
    segment.setAttribute("y2", String(baselineY));
    segment.setAttribute("stroke", point.category.color);
    segment.setAttribute("stroke-width", point.highlight ? (compact ? "5" : "6") : (compact ? "4" : "4.5"));
    segment.setAttribute("class", "metrics-graph-timeline-segment");
    appendMetricsSvgTitle(segment, `${point.pairLabel} • ${metricsGraphValueLabel(point.finalSplitS, graph.unit)} • ${point.category.label}`);
    svg.appendChild(segment);

    const dot = createSvgNode("circle");
    dot.setAttribute("cx", String(x));
    dot.setAttribute("cy", String(baselineY));
    dot.setAttribute("r", point.highlight ? (compact ? "4" : "4.5") : (compact ? "3.2" : "3.6"));
    dot.setAttribute("fill", point.category.color);
    dot.setAttribute("class", "metrics-graph-dot");
    appendMetricsSvgTitle(dot, `Shot ${point.shotNumber} • ${metricsGraphValueLabel(point.value, graph.unit)} • ${point.category.label}`);
    svg.appendChild(dot);

    if (!compact && point.highlight) {
      const label = createSvgNode("text");
      label.setAttribute("x", String((previousX + x) / 2));
      label.setAttribute("y", String(baselineY - 10));
      label.setAttribute("text-anchor", "middle");
      label.setAttribute("class", "metrics-graph-highlight-label");
      label.textContent = `${point.pairLabel} ${metricsGraphValueLabel(point.finalSplitS, graph.unit)}`;
      svg.appendChild(label);
    }

    if (!compact && shouldRenderMetricsAxisLabel(index, points.length, compact, point.highlight)) {
      const axis = createSvgNode("text");
      axis.setAttribute("x", String(x));
      axis.setAttribute("y", String(baselineY + 16));
      axis.setAttribute("text-anchor", "middle");
      axis.setAttribute("class", "metrics-graph-axis-label");
      axis.textContent = `S${point.shotNumber}`;
      svg.appendChild(axis);
    }

    previousX = x;
  });

  const startText = createSvgNode("text");
  startText.setAttribute("x", String(padding.left));
  startText.setAttribute("y", String(viewHeight - 6));
  startText.setAttribute("text-anchor", "start");
  startText.setAttribute("class", "metrics-graph-axis-label");
  startText.textContent = "Start 0.000s";
  svg.appendChild(startText);

  const finalPoint = points[points.length - 1] || null;
  if (finalPoint) {
    const endText = createSvgNode("text");
    endText.setAttribute("x", String(viewWidth - padding.right));
    endText.setAttribute("y", String(viewHeight - 6));
    endText.setAttribute("text-anchor", "end");
    endText.setAttribute("class", "metrics-graph-axis-label");
    endText.textContent = `Shot ${finalPoint.shotNumber} ${metricsGraphValueLabel(finalPoint.value, graph.unit)}`;
    svg.appendChild(endText);
  }
  return svg;
}

function renderMetricsBarGraphSvg(graph, { compact = true } = {}) {
  const bars = (graph.bars || []).filter((bar) => bar.value !== null && bar.value !== undefined);
  if (bars.length === 0) return null;
  const { svg, viewWidth, viewHeight, padding, plotWidth, plotHeight } = createMetricsGraphCanvas({ compact });
  const maxValue = Math.max(...bars.map((bar) => Number(bar.value || 0)), 0.001);
  const yFor = (value) => padding.top + ((maxValue - Number(value || 0)) / Math.max(0.0001, maxValue)) * plotHeight;
  const columnWidth = plotWidth / Math.max(1, bars.length);
  const barWidth = Math.max(6, columnWidth * (compact ? 0.56 : 0.64));

  [0, 0.5, 1].forEach((ratio) => {
    const y = padding.top + (plotHeight * ratio);
    const gridLine = createSvgNode("line");
    gridLine.setAttribute("x1", String(padding.left));
    gridLine.setAttribute("x2", String(viewWidth - padding.right));
    gridLine.setAttribute("y1", String(y));
    gridLine.setAttribute("y2", String(y));
    gridLine.setAttribute("class", "metrics-graph-grid-line");
    svg.appendChild(gridLine);
  });

  const baseline = createSvgNode("line");
  baseline.setAttribute("x1", String(padding.left));
  baseline.setAttribute("x2", String(viewWidth - padding.right));
  baseline.setAttribute("y1", String(padding.top + plotHeight));
  baseline.setAttribute("y2", String(padding.top + plotHeight));
  baseline.setAttribute("class", "metrics-graph-baseline");
  svg.appendChild(baseline);

  bars.forEach((bar, index) => {
    const x = padding.left + (index * columnWidth) + ((columnWidth - barWidth) / 2);
    const y = yFor(bar.value);
    const rect = createSvgNode("rect");
    rect.setAttribute("x", String(x));
    rect.setAttribute("y", String(y));
    rect.setAttribute("width", String(barWidth));
    rect.setAttribute("height", String(Math.max(1, (padding.top + plotHeight) - y)));
    rect.setAttribute("fill", bar.category.color);
    rect.setAttribute("class", `metrics-graph-bar${bar.highlight ? " highlight" : ""}`);
    appendMetricsSvgTitle(rect, `${bar.label}: ${metricsGraphValueLabel(bar.value, graph.unit)} • ${bar.category.label}`);
    svg.appendChild(rect);

    if (bar.highlight || (!compact && bars.length <= 8)) {
      const valueText = createSvgNode("text");
      valueText.setAttribute("x", String(x + (barWidth / 2)));
      valueText.setAttribute("y", String(Math.max(padding.top + 9, y - 4)));
      valueText.setAttribute("text-anchor", "middle");
      valueText.setAttribute("class", "metrics-graph-bar-value");
      valueText.textContent = metricsGraphValueLabel(bar.value, graph.unit);
      svg.appendChild(valueText);
    }

    if (shouldRenderMetricsAxisLabel(index, bars.length, compact, bar.highlight)) {
      const axis = createSvgNode("text");
      axis.setAttribute("x", String(x + (barWidth / 2)));
      axis.setAttribute("y", String(viewHeight - 6));
      axis.setAttribute("text-anchor", "middle");
      axis.setAttribute("class", "metrics-graph-axis-label");
      axis.textContent = bar.shortLabel || bar.label;
      svg.appendChild(axis);
    }
  });

  return svg;
}

function renderMetricsGraphSvg(graph, { compact = true } = {}) {
  if (graph.type === "timeline") return renderMetricsTimelineGraphSvg(graph, { compact });
  if (graph.type === "bars") return renderMetricsBarGraphSvg(graph, { compact });
  return renderMetricsLineGraphSvg(graph, { compact });
}

function renderMetricsGraphCard(graph, { compact = true } = {}) {
  const card = document.createElement("article");
  card.className = "metric-card metrics-graph-card";
  if (!compact) card.classList.add("metrics-graph-card-wide");
  const header = document.createElement("div");
  header.className = "metrics-graph-header";
  const title = document.createElement("strong");
  title.textContent = graph.title;
  const subtitle = document.createElement("span");
  subtitle.className = "hint";
  subtitle.textContent = graph.subtitle;
  header.append(title, subtitle);
  card.appendChild(header);

  const summary = document.createElement("div");
  summary.className = "metrics-graph-summary";
  metricsGraphSummaryItems(graph).forEach((item) => {
    const chip = document.createElement("span");
    chip.className = "metrics-graph-chip";
    chip.style.setProperty("--metrics-graph-chip-color", item.color || "var(--accent)");
    chip.textContent = [item.label, item.value].filter(Boolean).join(" ").trim();
    summary.appendChild(chip);
  });
  card.appendChild(summary);

  const svg = renderMetricsGraphSvg(graph, { compact });
  if (svg) card.appendChild(svg);
  return card;
}

function renderMetricsGraphs(container, graphs, { compact = true } = {}) {
  if (!(container instanceof HTMLElement)) return;
  container.innerHTML = "";
  if (graphs.length === 0) {
    const empty = document.createElement("p");
    empty.className = "hint metrics-graph-empty";
    empty.textContent = "Graphs appear once the run has timing rows to chart.";
    container.appendChild(empty);
    return;
  }
  graphs.forEach((graph) => container.appendChild(renderMetricsGraphCard(graph, { compact })));
}

function isMetricsSectionExpanded(sectionId) {
  if (metricsPane) return metricsPane.isMetricsSectionExpanded(sectionId);
  return metricsSectionExpansion.get(sectionId) !== false;
}

function setMetricsSectionExpanded(sectionId, expanded) {
  if (metricsPane) return metricsPane.setMetricsSectionExpanded(sectionId, expanded);
  metricsSectionExpansion.set(sectionId, Boolean(expanded));
}

function renderMetricsSections() {
  if (metricsPane) return metricsPane.renderMetricsSections();
  document.querySelectorAll("[data-metrics-section]").forEach((section) => {
    if (!(section instanceof HTMLElement)) return;
    const sectionId = section.dataset.metricsSection || "";
    const expanded = isMetricsSectionExpanded(sectionId);
    section.classList.toggle("collapsed", !expanded);
    ensureSectionToggle(section, expanded, () => {
      setMetricsSectionExpanded(sectionId, !expanded);
      renderMetricsSections();
    });
  });
}

function buildMetricsGraphCsvSections(rows = buildMetricsRows()) {
  return buildMetricsGraphSeries(rows).map((graph) => {
    if (graph.type === "timeline") {
      return {
        name: `graph_${graph.id}`,
        headers: ["shot_number", "shot_label", "pair_label", "cumulative_s", "interval_s", "category_id", "category_label", "interval_label", "actions"],
        rows: (graph.points || []).map((point) => [
          point.shotNumber ?? "",
          point.label || "",
          point.pairLabel || "",
          point.value ?? "",
          point.finalSplitS ?? "",
          point.category?.id || "",
          point.category?.label || "",
          point.intervalLabel || "",
          point.actionSummary || "",
        ]),
      };
    }
    if (graph.type === "bars") {
      return {
        name: `graph_${graph.id}`,
        headers: ["order", "label", "short_label", "value_s", "category_id", "category_label"],
        rows: (graph.bars || []).map((bar, index) => [
          index + 1,
          bar.label || "",
          bar.shortLabel || "",
          bar.value ?? "",
          bar.category?.id || "",
          bar.category?.label || "",
        ]),
      };
    }
    const headers = ["shot_number", "shot_label", ...graph.lines.map((line) => line.key)];
    const recordByShotNumber = new Map();
    graph.lines.forEach((line) => {
      line.points.forEach((point) => {
        const existing = recordByShotNumber.get(point.shotNumber) || { shot_number: point.shotNumber, shot_label: point.label };
        existing[line.key] = point.value;
        recordByShotNumber.set(point.shotNumber, existing);
      });
    });
    const sectionRows = [...recordByShotNumber.values()]
      .sort((left, right) => Number(left.shot_number || 0) - Number(right.shot_number || 0))
      .map((record) => headers.map((header) => record[header] ?? ""));
    return {
      name: `graph_${graph.id}`,
      headers,
      rows: sectionRows.length > 0 ? sectionRows : [["", "", ...graph.lines.map(() => "")]],
    };
  });
}

function metricsScoringDetailRows(summary) {
  const imported = summary.imported_stage || {};
  const shortPenaltyLabels = {
    procedural_errors: "PE",
    failures_to_do_right: "FTDR",
    finger_pe: "FPE",
    flagrant_penalties: "FP",
    non_threats: "NS",
    manual_misses: "M",
  };
  const penaltyFieldRows = (summary.penalty_fields || []).map((field) => {
    const count = Number(field.count || 0);
    const value = Number(field.value || 0);
    const suffix = field.unit === "seconds" ? "s" : " pts";
    return [
      shortPenaltyLabels[field.id] || field.label || field.id,
      `${formatNumber(count, 2)} x ${formatNumber(value, 2)}${suffix}`,
    ];
  });
  const importedRows = [
    ["Stage #", imported.stage_number !== null && imported.stage_number !== undefined ? String(imported.stage_number) : ""],
    ["Competitor", imported.competitor_name || ""],
    ["Place", imported.competitor_place !== null && imported.competitor_place !== undefined ? String(imported.competitor_place) : ""],
  ];
  return [
    ...importedRows,
    ["Ruleset", summary.ruleset_name || ""],
    ["Sport", summary.sport || ""],
    ["Mode", summary.mode || ""],
    [summary.display_label || "Result", summary.display_value || ""],
    ["Raw Time", summary.raw_seconds !== null && summary.raw_seconds !== undefined ? `${formatNumber(summary.raw_seconds, 2)}s` : ""],
    ["Official Raw", summary.official_raw_seconds !== null && summary.official_raw_seconds !== undefined ? `${formatNumber(summary.official_raw_seconds, 2)}s` : ""],
    ["Raw Delta", summary.raw_delta_seconds !== null && summary.raw_delta_seconds !== undefined ? `${formatNumber(summary.raw_delta_seconds, 2)}s` : ""],
    ["Final Time", summary.final_time !== null && summary.final_time !== undefined ? `${formatNumber(summary.final_time, 2)}s` : ""],
    ["Official Final", summary.official_final_time !== null && summary.official_final_time !== undefined ? `${formatNumber(summary.official_final_time, 2)}s` : ""],
    ["Final Delta", summary.final_delta_seconds !== null && summary.final_delta_seconds !== undefined ? `${formatNumber(summary.final_delta_seconds, 2)}s` : ""],
    ["Shot Points", formatNumber(summary.shot_points, 2)],
    ["Shot Penalties", formatNumber(summary.shot_penalties, 2)],
    ["Field Penalties", formatNumber(summary.field_penalties, 2)],
    [summary.penalty_label || "Penalties", formatNumber(summary.total_penalties, 2)],
    ["Hit Factor", summary.hit_factor !== null && summary.hit_factor !== undefined ? formatNumber(summary.hit_factor, 2) : ""],
    ...penaltyFieldRows,
  ];
}

function renderMetricsPanel() {
  if (metricsPane) return metricsPane.renderMetricsPanel();
  const summaryGrid = $("metrics-summary-grid");
  const trendList = $("metrics-trend-list");
  const scoreStatus = $("metrics-score-status");
  if (!summaryGrid || !trendList || !scoreStatus) return;
  const scoringSummary = state.metrics?.scoring_summary || state.scoring_summary || {};
  const rows = buildMetricsRows();
  const graphs = buildMetricsGraphSeries(rows);

  const summaryCards = [
    ["Draw", splitSeconds(state.metrics.draw_ms), "First-shot timing"],
    ["Raw", splitSeconds(state.metrics.raw_time_ms ?? state.metrics.stage_time_ms), "Beep to final shot"],
    ["Shots", String(state.metrics.total_shots || 0), "Current timeline shots"],
    ["Avg Split", splitSeconds(state.metrics.average_split_ms), "Average split"],
    ["Beep", splitSeconds(state.metrics.beep_ms), "Start marker"],
    [scoringSummary.display_label || "Result", scoringSummary.display_value || "--", scoringSummary.sport || "Scoring summary"],
    ["Shot Points", formatNumber(scoringSummary.shot_points, 2), "Raw score total"],
    ["Penalties", formatNumber(scoringSummary.total_penalties, 2), scoringSummary.penalty_label || "Penalty summary"],
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

  withPreservedScrollState([trendList], () => renderMetricsTrendTable(trendList));

  const summary = scoringSummary;
  const imported = summary.imported_stage || {};
  scoreStatus.dataset.importedSource = imported.source_name || "";
  scoreStatus.dataset.importedStage = imported.stage_number ?? "";
  scoreStatus.dataset.importedCompetitor = imported.competitor_name || "";
  scoreStatus.dataset.importedPlace = imported.competitor_place ?? "";
  scoreStatus.textContent = summary.enabled
    ? `${summary.display_label || "Result"} ${summary.display_value || "--"}`
    : "Scoring disabled.";
  const details = metricsScoringDetailRows(summary);
  renderDetailsList("metrics-score-summary", details);
  renderMetricsGraphs($("metrics-graph-list"), graphs, { compact: true });
  renderMetricsGraphs($("metrics-workbench-graphs"), graphs, { compact: false });
  renderMetricsSections();
  renderMetricsTable($("metrics-workbench-table"));
}

function metricsFileStem() {
  if (metricsPane) return metricsPane.metricsFileStem();
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
  if (metricsPane) return metricsPane.buildMetricsCsv();
  const summary = state.scoring_summary || {};
  const rows = buildMetricsRows();
  const imported = summary.imported_stage || {};
  const comparisonShooters = Array.isArray(state?.practiscore_options?.competitors)
    ? state.practiscore_options.competitors
    : [];
  const penaltyFieldRows = (summary.penalty_fields || []).map((field) => [
    field.id || "",
    field.label || "",
    field.unit || "",
    field.count ?? "",
    field.value ?? "",
    (Number(field.count || 0) * Number(field.value || 0)) || "",
  ]);
  const sections = [
    {
      name: "run_summary",
      headers: [
        "project_name",
        "video_file",
        "shooter_name",
        "stage_number",
        "stage_name",
        "match_type",
        "ruleset",
        "sport",
        "competitor_place",
        "stage_place",
        "class_place",
        "result_label",
        "result_value",
        "raw_time_s",
        "raw_delta_s",
        "final_time_s",
        "final_delta_s",
        "shot_points",
        "shot_penalties",
        "field_penalties",
        "total_penalties",
        "hit_factor",
      ],
      rows: [[
        state.project.name || "",
        fileName(state.project.primary_video.path || ""),
        imported.competitor_name || state.project.scoring.competitor_name || "",
        imported.stage_number ?? state.project.scoring.stage_number ?? "",
        imported.stage_name || "",
        imported.match_type || state?.practiscore_options?.detected_match_type || state.project.scoring.match_type || "",
        summary.ruleset || "",
        summary.sport || "",
        imported.competitor_place ?? state.project.scoring.competitor_place ?? "",
        imported.stage_place ?? "",
        imported.class_place ?? "",
        summary.display_label || "Result",
        summary.display_value || "",
        summary.raw_seconds ?? "",
        summary.raw_delta_seconds ?? "",
        summary.final_time ?? "",
        summary.final_delta_seconds ?? "",
        summary.shot_points ?? "",
        summary.shot_penalties ?? "",
        summary.field_penalties ?? "",
        summary.total_penalties ?? "",
        summary.hit_factor ?? "",
      ]],
    },
    {
      name: "comparison_context",
      headers: [
        "competitor",
        "class",
        "division",
        "overall_place",
        "class_place",
        "stage_place",
        "raw_time_s",
        "final_time_s",
        "points",
        "stage_points",
        "hit_factor",
        "delta_to_selected_s",
      ],
      rows: comparisonShooters.length > 0
        ? comparisonShooters.map((competitor) => [
          competitor.name || "",
          competitor.class || "",
          competitor.division || "",
          competitor.place ?? "",
          competitor.class_place ?? "",
          competitor.stage_place ?? "",
          competitor.raw_seconds ?? "",
          competitor.final_time ?? "",
          competitor.points ?? "",
          competitor.stage_points ?? "",
          competitor.hit_factor ?? "",
          "",
        ])
        : [["", "", "", "", "", "", "", "", "", "", "", ""]],
    },
    {
      name: "per_shot_metrics",
      headers: [
        "shot_number",
        "segment_label",
        "interval_label",
        "actions",
        "shotml_split_s",
        "adjustment_s",
        "absolute_s",
        "split_s",
        "run_s",
        "cumulative_s",
        "practiscore_raw_s",
        "raw_delta_s",
        "score_letter",
        "penalties",
        "shotml_confidence",
      ],
      rows: rows.map((entry) => [
        entry.shotNumber || "",
        entry.label || "",
        entry.intervalLabel || "",
        entry.actionSummary || "",
        entry.shotmlSplitMs === null || entry.shotmlSplitMs === undefined ? "" : precise(entry.shotmlSplitMs),
        entry.adjustmentMs === null || entry.adjustmentMs === undefined ? "" : precise(entry.adjustmentMs),
        entry.absoluteMs === null ? "" : precise(entry.absoluteMs),
        entry.splitMs === null || entry.splitMs === undefined ? "" : precise(entry.splitMs),
        entry.sequenceTotalMs === null || entry.sequenceTotalMs === undefined ? "" : precise(entry.sequenceTotalMs),
        entry.cumulativeMs === null || entry.cumulativeMs === undefined ? "" : precise(entry.cumulativeMs),
        entry.practiscoreMs === null || entry.practiscoreMs === undefined ? "" : precise(entry.practiscoreMs),
        entry.rawDeltaMs === null || entry.rawDeltaMs === undefined ? "" : precise(entry.rawDeltaMs),
        entry.scoreLetter || "",
        entry.penaltyText || "",
        entry.confidence ?? "",
      ]),
    },
    {
      name: "scoring_breakdown",
      headers: ["penalty_id", "label", "unit", "count", "value", "total"],
      rows: [
        ...penaltyFieldRows,
        ["shot_points", "Shot Points", "points", "", summary.shot_points ?? "", summary.shot_points ?? ""],
        ["shot_penalties", "Shot Penalties", "points", "", summary.shot_penalties ?? "", summary.shot_penalties ?? ""],
        ["field_penalties", "Field Penalties", "points", "", summary.field_penalties ?? "", summary.field_penalties ?? ""],
        ["total_penalties", summary.penalty_label || "Total Penalties", "points", "", summary.total_penalties ?? "", summary.total_penalties ?? ""],
      ],
    },
    ...buildMetricsGraphCsvSections(rows),
  ];

  const output = [];
  sections.forEach((section, index) => {
    output.push(csvEscape(`# ${section.name}`));
    output.push(section.headers.map(csvEscape).join(","));
    section.rows.forEach((row) => output.push(row.map(csvEscape).join(",")));
    if (index < sections.length - 1) output.push("");
  });
  return output.join("\n");
}

function buildMetricsText() {
  if (metricsPane) return metricsPane.buildMetricsText();
  const summary = state.scoring_summary || {};
  const rows = buildMetricsRows();
  const graphs = buildMetricsGraphSeries(rows);
  const segmentGraph = graphs.find((graph) => graph.id === "stage_segment_breakdown") || null;
  const comparisonGraph = graphs.find((graph) => graph.id === "run_comparison_overlay") || null;
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
    parts.push(`Adjustment ${signedSeconds(entry.adjustmentMs || 0)}`);
    if (entry.rawDeltaMs !== null && entry.rawDeltaMs !== undefined) parts.push(`PractiScore ${metricsPractiScoreLabel(entry)}`);
    if (entry.confidence !== null && entry.confidence !== undefined && entry.confidence !== "") parts.push(`ShotML ${formatConfidenceValue(entry.confidence)}`);
    lines.push(`- ${parts.join(" | ")}`);
  });
  if (segmentGraph?.bars?.length) {
    lines.push("", "Stage Segments");
    segmentGraph.bars.forEach((bar) => {
      lines.push(`- ${bar.label}: ${metricsGraphValueLabel(bar.value, segmentGraph.unit)} (${bar.category.label})`);
    });
  }
  if (comparisonGraph?.summary?.length) {
    lines.push("", comparisonGraph.title);
    comparisonGraph.summary.forEach((item) => {
      lines.push(`- ${item.label}: ${item.value}`);
    });
  }
  return lines.join("\n");
}

function exportMetrics(kind) {
  if (metricsPane) return metricsPane.exportMetrics(kind);
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
  return exportPane?.syncExportPathControl();
}

function shotmlSettings() {
  return shotmlPane?.shotmlSettings() || state?.project?.analysis?.shotml_settings || {};
}

function shotmlControlValue(element) {
  return shotmlPane?.shotmlControlValue(element);
}

function readShotMLSettingsPayload() {
  return shotmlPane?.readShotMLSettingsPayload() || {};
}

function syncShotMLControls() {
  return shotmlPane?.syncShotMLControls();
}

function proposalTypeLabel(type) {
  return shotmlPane?.proposalTypeLabel(type) || String(type || "Proposal");
}

function proposalPreviewText(proposal) {
  return shotmlPane?.proposalPreviewText(proposal) || "--";
}

function renderShotMLProposals() {
  return shotmlPane?.renderShotMLProposals();
}

function renderShotML() {
  return shotmlPane?.renderShotML();
}

function renderControls() {
  return shellRuntime?.renderControls();
}

function renderStyleControls() {
  return shellRuntime?.renderStyleControls();
}

function clearMergeSourceCommitTimers(options = {}) {
  return mergePane?.clearMergeSourceCommitTimers(options);
}

function scheduleMergeSourceCommit(payload) {
  return mergePane?.scheduleMergeSourceCommit(payload);
}

async function flushPendingMergeSourceCommits(options = {}) {
  return mergePane?.flushPendingMergeSourceCommits(options);
}

function renderMergeMediaList() {
  // input.dataset.mergeSourceField = "opacity";
  // These values are saved per item and take effect in PiP layout and export timing.
  return mergePane?.renderMergeMediaList();
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

function browserPlatformIsWindows() {
  const platform = String(window.navigator?.platform || "");
  const userAgent = String(window.navigator?.userAgent || "");
  return /Win/i.test(platform) || /Windows/i.test(userAgent);
}

function defaultOverlayFontFamily() {
  return browserPlatformIsWindows() ? "Segoe UI" : "Helvetica Neue";
}

function resolvedOverlayFontFamily(fontFamily = "") {
  const normalized = String(fontFamily || "").trim();
  if (!normalized) return defaultOverlayFontFamily();
  if (browserPlatformIsWindows() && normalized === "Helvetica Neue") return "Segoe UI";
  return normalized;
}

function overlayFontFamilyStack(fontFamily = "") {
  const normalized = resolvedOverlayFontFamily(fontFamily);
  switch (normalized) {
    case "Segoe UI":
      return '"Segoe UI", Arial, Verdana, Tahoma, "Trebuchet MS", sans-serif';
    case "Arial":
      return 'Arial, "Segoe UI", Verdana, Tahoma, "Trebuchet MS", sans-serif';
    case "Verdana":
      return 'Verdana, "Segoe UI", Arial, Tahoma, "Trebuchet MS", sans-serif';
    case "Tahoma":
      return 'Tahoma, "Segoe UI", Arial, Verdana, "Trebuchet MS", sans-serif';
    case "Trebuchet MS":
      return '"Trebuchet MS", "Segoe UI", Arial, Verdana, Tahoma, sans-serif';
    case "Courier New":
      return 'Consolas, "Courier New", "Lucida Console", monospace';
    case "Georgia":
      return 'Georgia, Cambria, "Times New Roman", serif';
    case "Helvetica Neue":
      return '"Helvetica Neue", Helvetica, Arial, "DejaVu Sans", sans-serif';
    default:
      return normalized
        ? `"${normalized}", "Segoe UI", Arial, Verdana, Tahoma, "Trebuchet MS", sans-serif`
        : '"Segoe UI", Arial, Verdana, Tahoma, "Trebuchet MS", sans-serif';
  }
}

function overlayBadgeFontSpec() {
  const overlay = state?.project?.overlay || {};
  const fontStyle = overlay.font_italic ? "italic" : "normal";
  const fontWeight = overlay.font_bold ? "700" : "400";
  const fontSize = overlayBadgeFontSizePx();
  const fontFamily = overlayFontFamilyStack(overlay.font_family || defaultOverlayFontFamily());
  return `${fontStyle} ${fontWeight} ${fontSize}px ${fontFamily}`;
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
    overlay.font_family || defaultOverlayFontFamily(),
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
  badge.style.fontFamily = overlayFontFamilyStack(state.project.overlay.font_family || defaultOverlayFontFamily());
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

function positionTextBoxBadge(badge, box, frameRect, { anchorBadge = null, anchorRect = null, scale = 1 } = {}) {
  return overlayPane?.positionTextBoxBadge(badge, box, frameRect, { anchorBadge, anchorRect, scale }) || false;
}

function resolveNormalizedPointFromRect(rect, frameRect) {
  if (!rect || !frameRect) return null;
  const width = Math.max(1, Number(frameRect.width) || 0);
  const height = Math.max(1, Number(frameRect.height) || 0);
  return {
    x: Math.round(clamp((rect.left - frameRect.left + (rect.width / 2)) / width, 0, 1) * 10000) / 10000,
    y: Math.round(clamp((rect.top - frameRect.top + (rect.height / 2)) / height, 0, 1) * 10000) / 10000,
  };
}

function previewFrameRectForTextBoxes() {
  return overlayPane?.previewFrameRectForTextBoxes() || null;
}

function overlayTextBoxBadge(boxId) {
  return overlayPane?.overlayTextBoxBadge(boxId) || null;
}

function resolveRenderedTextBoxCoordinates(boxId, fallbackBox = null) {
  return overlayPane?.resolveRenderedTextBoxCoordinates(boxId, fallbackBox) || null;
}

function unlockedOverlayTextBox(box, coordinates = null) {
  return overlayPane?.unlockedOverlayTextBox(box, coordinates);
}

function syncLockedTextBoxEditorCoordinates() {
  return overlayPane?.syncLockedTextBoxEditorCoordinates();
}

function configureTextBoxGroup(group, quadrant, frameRect, scale = 1) {
  return overlayPane?.configureTextBoxGroup(group, quadrant, frameRect, scale);
}

function placeOverlayBadge(layer, badge, frameRect, xValue, yValue) {
  const x = normalizedCoordinateValue(xValue);
  const y = normalizedCoordinateValue(yValue);
  if (!layer || !badge || !frameRect || x === null || y === null) return false;
  badge.style.position = "absolute";
  badge.style.margin = "0";
  badge.style.left = "0px";
  badge.style.top = "0px";
  badge.style.transform = "";
  layer.appendChild(badge);
  const badgeRect = badge.getBoundingClientRect();
  const badgeWidth = Math.max(0, badgeRect.width || badge.offsetWidth || 0);
  const badgeHeight = Math.max(0, badgeRect.height || badge.offsetHeight || 0);
  badge.style.left = `${clamp((x * frameRect.width) - (badgeWidth / 2), 0, Math.max(0, frameRect.width - badgeWidth))}px`;
  badge.style.top = `${clamp((y * frameRect.height) - (badgeHeight / 2), 0, Math.max(0, frameRect.height - badgeHeight))}px`;
  return true;
}

function visibleOverlayTextBoxEntries(finalShotReached) {
  return overlayPane?.visibleOverlayTextBoxEntries(finalShotReached) || [];
}

function overlayTextBoxStyle(box) {
  return overlayPane?.overlayTextBoxStyle(box);
}

function customOverlayKey(entries, frameRect, overlayScale, finalScoreBadge, stackAnchorRect = null) {
  return overlayPane?.customOverlayKey(entries, frameRect, overlayScale, finalScoreBadge, stackAnchorRect) || "";
}

function overlayStackBadges(overlay) {
  return overlayPane?.overlayStackBadges(overlay) || [];
}

function overlayStackAnchorRect(overlay) {
  return overlayPane?.overlayStackAnchorRect(overlay) || null;
}

function overlayStackTerminalRect(overlay) {
  return overlayPane?.overlayStackTerminalRect(overlay) || null;
}

function firstStackLockedTextBoxRect(badgeRect, frameRect, scale = 1) {
  return overlayPane?.firstStackLockedTextBoxRect(badgeRect, frameRect, scale) || null;
}

function nextStackLockedTextBoxRect(baseRect, badgeRect, frameRect, scale = 1) {
  return overlayPane?.nextStackLockedTextBoxRect(baseRect, badgeRect, frameRect, scale) || null;
}

function positionStackLockedTextBoxBadge(badge, frameRect, { terminalRect = null, previousRect = null, scale = 1 } = {}) {
  return overlayPane?.positionStackLockedTextBoxBadge(badge, frameRect, { terminalRect, previousRect, scale }) || null;
}

function renderCustomOverlayBoxes(customOverlay, entries, frameRect, overlayScale, size, finalScoreBadge, stackAnchorRect = null, terminalRect = null) {
  return overlayPane?.renderCustomOverlayBoxes(customOverlay, entries, frameRect, overlayScale, size, finalScoreBadge, stackAnchorRect, terminalRect);
}

function beginTextBoxDrag(event) {
  return overlayPane?.beginTextBoxDrag(event);
}

function moveTextBoxDrag(event) {
  return overlayPane?.moveTextBoxDrag(event);
}

function endTextBoxDrag(event) {
  return overlayPane?.endTextBoxDrag(event);
}

function beginPopupBubbleDrag(event) {
  return markersPane?.beginPopupBubbleDrag(event);
}

function movePopupBubbleDrag(event) {
  return markersPane?.movePopupBubbleDrag(event);
}

function endPopupBubbleDrag(event) {
  return markersPane?.endPopupBubbleDrag(event);
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
  if (popupBubbleDrag) {
    const drag = popupBubbleDrag;
    releasePointer(drag.target, drag.pointerId);
    drag.target?.classList.remove("dragging");
    popupBubbleDrag = null;
    activity("popup.drag.cancel", { popup_id: drag.bubbleId, reason });
    cleared = true;
  }
  if (!cleared) return;
  flushInteractionPreviewRender();
  flushQueuedProjectUiStateApply();
  flushDeferredRender();
}

function overlayDragConfiguration(kind) {
  return overlayPane?.overlayDragConfiguration(kind) || null;
}

function overlayDragAnchor(kind, badge, frameRect) {
  return overlayPane?.overlayDragAnchor(kind, badge, frameRect) || null;
}

function beginOverlayBadgeDrag(event) {
  return overlayPane?.beginOverlayBadgeDrag(event);
}

function moveOverlayBadgeDrag(event) {
  return overlayPane?.moveOverlayBadgeDrag(event);
}

function endOverlayBadgeDrag(event) {
  return overlayPane?.endOverlayBadgeDrag(event);
}

function beginMergePreviewDrag(event) {
  if (popupEditingActive()) return;
  if (event.button !== 0 || mergePreviewDrag) return;
  const item = event.target instanceof Element ? event.target.closest(".merge-preview-item[data-source-id]") : null;
  if (!(item instanceof HTMLElement)) return;
  if (item.dataset.dragEnabled === "false") return;
  const sourceId = item.dataset.sourceId || "";
  const source = mergeSourceById(sourceId);
  if (!source || !mergeSourceUsesFreeformPreviewDrag(source)) return;
  const stage = $("video-stage");
  const frameRect = mergePreviewTargetFrameRect(source, stage);
  if (!frameRect) return;
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
  if (!source || !mergeSourceUsesFreeformPreviewDrag(source)) return;
  const stage = $("video-stage");
  const frameRect = mergePreviewTargetFrameRect(source, stage);
  if (!frameRect) return;
  const rect = mergeSourcePipRect(source, frameRect, currentPipSizePercent(source));
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

function visiblePopupBubbles(positionMs) {
  return markersPane?.visiblePopupBubbles(positionMs) || [];
}

function popupOverlayPixelPoint(frameRect, xValue, yValue) {
  const x = clamp(Number(xValue) || 0, 0, 1);
  const y = clamp(Number(yValue) || 0, 0, 1);
  return {
    left: clamp(x * frameRect.width, 0, frameRect.width),
    top: clamp(y * frameRect.height, 0, frameRect.height),
  };
}

function renderPopupKeyframeOverlay(popupOverlay, bubble, frameRect) {
  return markersPane?.renderPopupKeyframeOverlay(popupOverlay, bubble, frameRect);
}

function renderPopupOverlay(popupOverlay, frameRect, overlayScale, size, positionMs) {
  return markersPane?.renderPopupOverlay(popupOverlay, frameRect, overlayScale, size, positionMs);
}

function renderLiveOverlay(positionMsOverride = null) {
  return overlayPane?.renderLiveOverlay(positionMsOverride);
}

function requestOverlayFrame(video, tick) {
  return overlayCanvasComponent?.requestOverlayFrame(video, tick);
}

function cancelOverlayFrame(video) {
  return overlayCanvasComponent?.cancelOverlayFrame(video);
}

function startOverlayLoop() {
  return overlayCanvasComponent?.startOverlayLoop();
}

function stopOverlayLoop() {
  return overlayCanvasComponent?.stopOverlayLoop();
}

function render() {
  updateStageEmptyState();
  return shellRuntime?.render();
}

function renderViewportLayout() {
  return shellRuntime?.renderViewportLayout();
}

function waveformTime(event) {
  return waveformStateRuntime?.waveformTime(event) ?? 0;
}

function shotPixelDistance(event, shot) {
  return waveformStateRuntime?.shotPixelDistance(event, shot) ?? Number.POSITIVE_INFINITY;
}

function nearestShot(event) {
  return waveformStateRuntime?.nearestShot(event) || null;
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

function syncExpandWaveformButton() {
  const button = $("expand-waveform");
  if (!button) return;
  button.textContent = $("cockpit-root")?.classList.contains("waveform-expanded") ? "Collapse" : "Expand";
}

function setWaveformExpanded(expanded, { persistUiState = true } = {}) {
  const root = $("cockpit-root");
  root.classList.toggle("waveform-expanded", expanded);
  if (expanded) root.classList.remove("timing-expanded", "metrics-expanded", "scoring-expanded", "markers-expanded");
  syncExpandWaveformButton();
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

function setWaveformTrackMode(mode) {
  waveformTrackMode = mode;
  window.localStorage.setItem("splitshot.waveformTrackMode", mode);
  const legend = domById("waveform-segment-legend");
  if (legend) legend.hidden = mode !== "multi";
}

function renderWaveformTracks() {
  const clips = stageCompositeClips || [];
  const list = domById("waveform-track-list");
  if (!list) return;

  if (clips.length === 0) {
    list.innerHTML = '<span class="hint" style="font-size:0.6875rem">No tracks loaded. Add clips in Match Video Edit.</span>';
    return;
  }

  const colors = { primary: "#4a9eff", follow: "#39d06f", static: "#ffc107", detail: "#c084fc" };
  list.innerHTML = clips.map((clip, i) => {
    const color = colors[clip.camera_role || clip.angle_role] || "#717982";
    return `<div class="waveform-track-chip" data-clip-index="${i}">
      <span class="track-color" style="background:${color}"></span>
      <span>${clip.filename || 'Track ' + (i+1)}</span>
      <span class="track-mute" title="Mute">&#x1F507;</span>
      <span class="track-solo" title="Solo">&#x1F3B5;</span>
    </div>`;
  }).join("");
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
  return timingPane?.setTimingExpanded(expanded, { persistUiState }) ?? Boolean(expanded);
}

function setMetricsExpanded(expanded, { persistUiState = true } = {}) {
  if (metricsPane) return metricsPane.setMetricsExpanded(expanded, { persistUiState });
  const root = $("cockpit-root");
  root.classList.toggle("metrics-expanded", expanded);
  if (expanded) root.classList.remove("waveform-expanded", "timing-expanded", "scoring-expanded", "markers-expanded");
  syncExpandWaveformButton();
  activity("metrics.expand", { expanded });
  syncLocalProjectUiState();
  if (persistUiState) scheduleProjectUiStateApply();
  if (expanded) {
    renderMetricsPanel();
    return;
  }
  scheduleReviewStageRestore();
}

function moveSelectedShot(deltaMs) {
  return keyRuntime.moveSelectedShot(deltaMs);
}

function deleteSelectedShot() {
  return keyRuntime.deleteSelectedShot();
}

function keyboardEditTargetIsEditable(event) {
  return keyRuntime.keyboardEditTargetIsEditable(event);
}

function handleWaveformPointerDown(event) {
  return waveformComponent?.handleWaveformPointerDown(event);
}

function handleWaveformPointerMove(event) {
  return waveformComponent?.handleWaveformPointerMove(event);
}

function handleWaveformPointerUp(event) {
  return waveformComponent?.handleWaveformPointerUp(event);
}

function handleKeyboardEdit(event) {
  if (keyboardEditTargetIsEditable(event)) return;
  return keyRuntime.handleKeyboardEdit(event);
}

function readOverlayPayload() {
  return overlayPane?.readOverlayPayload() || {};
}

function readProjectDetailsPayload() {
  return projectPane?.readProjectDetailsPayload() || {};
}

function readPractiScoreContextPayload() {
  return projectPane?.readPractiScoreContextPayload() || {};
}

function validatePractiScoreSelection() {
  return projectPane?.validatePractiScoreSelection() || readPractiScoreContextPayload();
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
  return mergePane?.readMergePayload() || {};
}

function readExportLayoutPayload() {
  return exportPane?.readExportLayoutPayload();
}

function readScoringPayload() {
  return scoringPane?.readScoringPayload() ?? {
    enabled: $("scoring-enabled")?.checked ?? false,
    penalties: $("penalties") ? Number($("penalties").value || 0) : Number(state?.project?.scoring?.penalties || 0),
    penalty_counts: { ...(state?.project?.scoring?.penalty_counts || {}) },
  };
}

function readExportSettingsPayload() {
  return exportPane?.readExportSettingsPayload();
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
    popups: state?.project?.popups || [],
    popup_template: normalizePopupTemplate(state?.project?.popup_template || {}),
    analysis: {
      shots: state?.project?.analysis?.shots || [],
      events: state?.project?.analysis?.events || [],
      beep_time_ms_primary: state?.project?.analysis?.beep_time_ms_primary,
    },
    merge: {
      ...readMergePayload(),
      sources: (state?.project?.merge_sources || []).map((source, index) => ({
        source_id: sourceIdentifier(source, String(index)),
        pip_size_percent: currentPipSizePercent(source, currentPipSizePercent()),
        pip_x: normalizedCoordinateValue(source.pip_x) ?? 1,
        pip_y: normalizedCoordinateValue(source.pip_y) ?? 1,
        opacity: currentSourceOpacity(source),
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
  autoApplyShotMLSettings.cancel?.();
  autoApplyProjectDetails.cancel?.();
  autoApplyPractiScoreContext.cancel?.();
  autoApplyProjectUiState.cancel?.();
  autoApplyOverlay.cancel?.();
  autoApplyMerge.cancel?.();
  autoApplyScoring.cancel?.();
  autoApplyExportLayout.cancel?.();
  autoApplyExportSettings.cancel?.();
}

window.pendingSettingsDefaultsPromise = null;
window.settingsDefaultsApplyGeneration = 0;

async function flushPendingSettingsDefaults() {
  if (scheduleSettingsDefaultsApply.flush?.()) {
    await Promise.resolve();
  }
  if (!window.pendingSettingsDefaultsPromise) {
    scheduleSettingsDefaultsApply.cancel?.();
    return;
  }
  try {
    await window.pendingSettingsDefaultsPromise;
  } finally {
    window.pendingSettingsDefaultsPromise = null;
    scheduleSettingsDefaultsApply.cancel?.();
  }
}

async function applySettingsDefaults(options = {}) {
  if (options.scheduled) {
    const scheduledGeneration = Number.isFinite(options.scheduledGeneration)
      ? Number(options.scheduledGeneration)
      : window.settingsDefaultsApplyGeneration;
    if (scheduledGeneration !== window.settingsDefaultsApplyGeneration) {
      return window.pendingSettingsDefaultsPromise || null;
    }
  }
  if (!options.scheduled) {
    window.settingsDefaultsApplyGeneration += 1;
  }
  scheduleSettingsDefaultsApply.cancel?.();
  if (window.pendingSettingsDefaultsPromise) {
    try {
      await window.pendingSettingsDefaultsPromise;
    } catch {
      // Ignore prior failure; continue with the latest update.
    }
  }
  const payload = readSettingsDefaultsPayload(options);
  const promise = callApi("/api/settings", payload);
  const finalPromise = promise.then((result) => {
    if (result && !options.scheduled) {
      window.lastAppliedSettingsDefaultsPayload = payload;
    }
    return result;
  }).finally(() => {
    if (window.pendingSettingsDefaultsPromise === finalPromise) {
      window.pendingSettingsDefaultsPromise = null;
    }
  });
  window.pendingSettingsDefaultsPromise = finalPromise;
  return finalPromise;
}

function applySettingsShotMLDefaults() {
  const threshold = readNumberSetting("settings-shotml-threshold", 0.35);
  if (!Number.isFinite(threshold)) return;
  return applySettingsDefaults();
}

async function applyProjectUiStatePayload(payload = readProjectUiStatePayload()) {
  const normalized = normalizeProjectUiState(payload);
  const payloadKey = projectUiStatePayloadKey(normalized);
  if (payloadKey === lastSubmittedProjectUiStatePayloadKey) return null;
  lastSubmittedProjectUiStatePayloadKey = payloadKey;
  const result = await callApi("/api/project/ui-state", normalized);
  if (!result && lastSubmittedProjectUiStatePayloadKey === payloadKey) {
    lastSubmittedProjectUiStatePayloadKey = null;
  }
  return result;
}

function resetProjectUiStateApplyState() {
  pendingProjectUiStatePayload = null;
  lastSubmittedProjectUiStatePayloadKey = null;
  autoApplyProjectUiState.cancel?.();
}

async function flushPendingProjectDrafts(options = {}) {
  void `await callApi("/api/project/details", readProjectDetailsPayload());`;
  return projectPane?.flushPendingProjectDrafts(options);
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

function sendProjectUiStateKeepalive(payload = readProjectUiStatePayload()) {
  const normalized = normalizeProjectUiState(payload);
  const payloadKey = projectUiStatePayloadKey(normalized);
  if (payloadKey === lastSubmittedProjectUiStatePayloadKey) return false;
  const sent = sendKeepaliveJson("/api/project/ui-state", normalized);
  if (sent) lastSubmittedProjectUiStatePayloadKey = payloadKey;
  return sent;
}

function flushPendingProjectDraftsKeepalive() {
  return projectPane?.flushPendingProjectDraftsKeepalive();
}

async function importTypedPath(targetId, apiPath, label) {
  void `if (apiPath === "/api/import/primary") {
    await flushPendingProjectDrafts();
  }`;
  return projectPane?.importTypedPath(targetId, apiPath, label);
}

function normalizeProjectFolderInput(path) {
  return projectPane?.normalizeProjectFolderInput(path) ?? String(path || "").trim();
}

function hasActiveProject() {
  return projectPane?.hasActiveProject() ?? Boolean(String(state?.project?.path || "").trim());
}

function gatedProjectActionMessage() {
  return projectPane?.gatedProjectActionMessage() ?? "Please create / select project.";
}

function setProjectActionAvailability() {
  return projectPane?.setProjectActionAvailability();
}

function createdProjectFoldersMessage(folderName, missingDirs) {
  return projectPane?.createdProjectFoldersMessage(folderName, missingDirs) ?? "";
}

function comparableProjectFolderPath(path) {
  return projectPane?.comparableProjectFolderPath(path) ?? normalizeProjectFolderInput(path);
}

function sameProjectFolderPath(left, right) {
  return projectPane?.sameProjectFolderPath(left, right)
    ?? (comparableProjectFolderPath(left) === comparableProjectFolderPath(right));
}

async function probeProjectFolder(path) {
  void `const requestId = ++projectFolderProbeRequestId;`;
  void `if (requestId !== projectFolderProbeRequestId)`;
  return projectPane?.probeProjectFolder(path);
}

async function browseProjectPath() {
  return projectPane?.browseProjectPath();
}

async function createNewProject(path = "") {
  void `const savedResult = await callApi("/api/project/save", { path: projectPath });`;
  void `window.alert(folderMessage);`;
  return projectPane?.createNewProject(path);
}

async function applyConfiguredProjectLandingTool(options = {}) {
  void `setActiveTool(configuredTool, { collapseExpandedLayout: forceProjectTool, persistUiState: false });`;
  return projectPane?.applyConfiguredProjectLandingTool(options);
}

async function useProjectFolder(path = "") {
  void `await flushPendingProjectDrafts();
  const currentPath = normalizeProjectFolderInput(state?.project?.path || "");`;
  void `const result = await callApi("/api/project/open", { path: projectPath });`;
  void `const result = await callApi("/api/project/save", { path: projectPath });`;
  return projectPane?.useProjectFolder(path);
}

async function applyScoringSettings(scoringPayload = readScoringPayload(), ruleset = $("scoring-preset").value) {
  return scoringPane?.applyScoringSettings(scoringPayload, ruleset);
}

const autoApplyShotMLSettings = debounce((settings) => {
  activity("auto_apply.shotml_settings", {});
  callApi("/api/analysis/shotml-settings", { settings, rerun: false });
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
  if (!shouldApplyProjectUiStatePayload(payload)) return;
  activity("auto_apply.project_ui_state", {});
  applyProjectUiStatePayload(payload);
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
  scheduleShotMLSettingsApply();
}

async function applyThresholdNow() {
  pendingSelectionFallback = shotSelectionContext(selectedShotId, state, "time");
  autoApplyShotMLSettings.cancel?.();
  await callApi("/api/analysis/shotml-settings", { settings: readShotMLSettingsPayload(), rerun: true });
}

function scheduleShotMLSettingsApply() {
  autoApplyShotMLSettings(readShotMLSettingsPayload());
}

function shotMLSettingsNeedSyncBeforePrimaryImport(payload = readShotMLSettingsPayload()) {
  if (autoApplyShotMLSettings.pending?.()) return true;
  const currentSettings = state?.project?.analysis?.shotml_settings || {};
  return Object.entries(payload).some(([key, value]) => {
    const currentValue = currentSettings?.[key];
    if (typeof value === "number" || typeof currentValue === "number") {
      return Number(value) !== Number(currentValue);
    }
    return value !== currentValue;
  });
}

function hasPendingPrimaryImportKeepaliveDrafts() {
  return Boolean(
    projectDetailsDraft.name !== null
    || projectDetailsDraft.description !== null
    || autoApplyProjectDetails.pending?.()
    || autoApplyPractiScoreContext.pending?.()
    || autoApplyProjectUiState.pending?.()
    || pendingProjectUiStatePayload
    || autoApplyOverlay.pending?.()
    || autoApplyMerge.pending?.()
    || pendingMergeSourcePayloads.size > 0
    || autoApplyExportLayout.pending?.()
    || autoApplyExportSettings.pending?.()
    || autoApplyScoring.pending?.()
  );
}

function scheduleProjectDetailsApply() {
  return projectPane?.scheduleProjectDetailsApply();
}

function schedulePractiScoreContextApply() {
  return projectPane?.schedulePractiScoreContextApply();
}

function scheduleProjectUiStateApply() {
  const payload = readProjectUiStatePayload();
  if (!shouldApplyProjectUiStatePayload(payload)) {
    pendingProjectUiStatePayload = null;
    return;
  }
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
  if (!shouldApplyProjectUiStatePayload(payload)) return;
  autoApplyProjectUiState(payload);
}

function scheduleOverlayApply() {
  queueInspectorScrollRestore();
  const payload = readOverlayPayload();
  applyOverlayPositionDraft(payload);
  applyOverlayStyleDraft(payload);
  autoApplyOverlay(payload);
}

function cancelAutoApplyOverlay() {
  autoApplyOverlay.cancel?.();
}

function scheduleMergeApply() {
  return mergePane?.scheduleMergeApply();
}

function scheduleExportLayoutApply() {
  return exportPane?.scheduleExportLayoutApply();
}

function scheduleExportSettingsApply() {
  return exportPane?.scheduleExportSettingsApply();
}

function scheduleScoringApply() {
  return scoringPane?.scheduleScoringApply();
}

const scheduleSettingsDefaultsApply = debounce((options = {}) => {
  activity("auto_apply.settings_defaults", {});
  applySettingsDefaults({
    ...options,
    scheduled: true,
    scheduledGeneration: Number.isFinite(options.scheduledGeneration)
      ? Number(options.scheduledGeneration)
      : window.settingsDefaultsApplyGeneration,
  });
}, 300);

const handleViewportLayoutChange = debounce(() => {
  renderViewportLayout();
  syncTimingTableColumns();
}, 120);

const readSettingsDefaultsPayload = ({ projectDefaults = false, section = null } = {}) => {
  if (settingsPane) return settingsPane.readSettingsDefaultsPayload({ projectDefaults, section });
  const projectOverlay = state?.project?.overlay || {};
  const projectExport = state?.project?.export || {};
  const projectScoring = state?.project?.scoring || {};
  const projectAnalysis = state?.project?.analysis || {};
  const projectPopupTemplate = normalizePopupTemplate(state?.project?.popup_template || {});
  const timerBadge = projectDefaults ? (projectOverlay.timer_badge || {}) : readSettingsBadgeStyle("settings-timer-badge");
  const shotBadge = projectDefaults ? (projectOverlay.shot_badge || {}) : readSettingsBadgeStyle("settings-shot-badge");
  const currentShotBadge = projectDefaults ? (projectOverlay.current_shot_badge || {}) : readSettingsBadgeStyle("settings-current-shot-badge");
  const hitFactorBadge = projectDefaults ? (projectOverlay.hit_factor_badge || {}) : readSettingsBadgeStyle("settings-hit-factor-badge");
  const markerTemplate = projectDefaults
    ? projectPopupTemplate
    : normalizePopupTemplate({
      enabled: $("settings-marker-enabled")?.checked ?? true,
      content_type: $("settings-marker-content-type")?.value || "text",
      text_source: $("settings-marker-text-source")?.value || "score",
      duration_ms: Math.max(1, Math.round((Number($("settings-marker-duration")?.value || 1) || 1) * 1000)),
      use_shot_split_duration: $("settings-marker-use-shot-split-duration")?.checked ?? false,
      quadrant: $("settings-marker-quadrant")?.value || projectPopupTemplate.quadrant || "middle_middle",
      width: Number($("settings-marker-width")?.value || 0),
      height: Number($("settings-marker-height")?.value || 0),
      follow_motion: $("settings-marker-follow-motion")?.checked ?? false,
      motion_mode: $("settings-marker-motion-mode")?.value || projectPopupTemplate.motion_mode,
      background_color: $("settings-marker-background-color")?.value || "#000000",
      text_color: $("settings-marker-text-color")?.value || "#ffffff",
      opacity: readNumberSetting("settings-marker-opacity", 0.9),
    });
  return {
    scope: $("settings-scope")?.value || "app",
    settings: {
      default_match_type: projectDefaults ? (projectScoring.match_type || "uspsa") : ($("settings-default-match-type")?.value || "uspsa"),
      overlay_position: projectDefaults ? (projectOverlay.position || "bottom") : ($("settings-overlay-position")?.value || "bottom"),
      badge_size: projectDefaults ? (projectOverlay.badge_size || "M") : ($("settings-badge-size")?.value || "M"),
      overlay_custom_box_background_color: projectDefaults ? (projectOverlay.custom_box_background_color || "#000000") : ($("settings-overlay-custom-background-color")?.value || "#000000"),
      overlay_custom_box_text_color: projectDefaults ? (projectOverlay.custom_box_text_color || "#ffffff") : ($("settings-overlay-custom-text-color")?.value || "#ffffff"),
      overlay_custom_box_opacity: projectDefaults ? (projectOverlay.custom_box_opacity ?? 0.9) : readNumberSetting("settings-overlay-custom-opacity", 0.9),
      timer_badge: timerBadge,
      shot_badge: shotBadge,
      current_shot_badge: currentShotBadge,
      hit_factor_badge: hitFactorBadge,
      merge_layout: projectDefaults ? (state?.project?.merge?.layout || "side_by_side") : ($("settings-merge-layout")?.value || "side_by_side"),
      pip_size: projectDefaults ? (state?.project?.merge?.pip_size || "35%") : ($("settings-pip-size")?.value || "35%"),
      merge_pip_x: projectDefaults ? (state?.project?.merge?.pip_x ?? 1.0) : readNumberSetting("settings-merge-pip-x", 1.0),
      merge_pip_y: projectDefaults ? (state?.project?.merge?.pip_y ?? 1.0) : readNumberSetting("settings-merge-pip-y", 1.0),
      merge_source_defaults: projectDefaults
        ? (state?.project?.merge_sources || []).map((source) => ({
          asset: { ...(source.asset || {}) },
          pip_size_percent: source.pip_size_percent ?? null,
          pip_x: Number(source.pip_x ?? 1.0),
          pip_y: Number(source.pip_y ?? 1.0),
          opacity: Number(source.opacity ?? 1.0),
          sync_offset_ms: Number(source.sync_offset_ms ?? 0),
        }))
        : undefined,
      export_quality: projectDefaults ? (projectExport.quality || "high") : ($("settings-export-quality")?.value || "high"),
      export_preset: projectDefaults ? (projectExport.preset || "source") : ($("settings-export-preset")?.value || "source"),
      export_frame_rate: projectDefaults ? (projectExport.frame_rate || "source") : ($("settings-export-frame-rate")?.value || "source"),
      export_video_codec: projectDefaults ? (projectExport.video_codec || "h264") : ($("settings-export-video-codec")?.value || "h264"),
      export_audio_codec: projectDefaults ? (projectExport.audio_codec || "aac") : ($("settings-export-audio-codec")?.value || "aac"),
      export_color_space: projectDefaults ? (projectExport.color_space || "bt709_sdr") : ($("settings-export-color-space")?.value || "bt709_sdr"),
      export_two_pass: projectDefaults ? Boolean(projectExport.two_pass ?? false) : ($("settings-export-two-pass")?.checked ?? false),
      export_ffmpeg_preset: projectDefaults ? (projectExport.ffmpeg_preset || "medium") : ($("settings-export-ffmpeg-preset")?.value || "medium"),
      default_tool: $("settings-default-tool")?.value || "project",
      reopen_last_tool: $("settings-reopen-last-tool")?.checked ?? true,
      detection_threshold: projectDefaults
        ? (projectAnalysis?.shotml_settings?.detection_threshold ?? 0.35)
        : readNumberSetting("settings-shotml-threshold", 0.35),
      marker_template: markerTemplate,
    },
  };
};

const WORKSPACE_PANE_LAYOUTS = {
  match: {
    "match-section-stages": {
      lower: ["match-section-stage-detail"],
      inspector: ["match-section-stage-workflow"],
    },
    "match-section-defaults": {
      lower: ["match-section-stage-detail"],
      inspector: ["match-section-defaults"],
    },
    "match-section-overrides": {
      lower: ["match-section-stage-detail"],
      inspector: ["match-section-overrides"],
    },
    "match-section-recap": {
      lower: ["match-section-stage-detail"],
      inspector: ["match-section-recap"],
    },
    "match-section-composite": {
      lower: ["match-section-composite"],
      inspector: ["match-section-stage-workflow"],
    },
    "match-section-export": {
      lower: ["match-section-export"],
      inspector: ["match-section-stage-workflow"],
    },
    "match-section-settings": {
      lower: ["match-section-stage-detail"],
      inspector: ["match-section-settings"],
    },
  },
  library: {
    "library-section-overview": {
      lower: ["library-section-detail"],
      inspector: ["library-section-overview-inspector"],
    },
    "library-section-records": {
      lower: ["library-section-detail"],
      inspector: ["library-section-record-filters"],
    },
    "library-section-detail": {
      lower: ["library-section-detail"],
      inspector: ["library-section-detail-actions"],
    },
    "library-section-analytics": {
      lower: ["library-section-detail"],
      inspector: ["library-section-analytics-inspector"],
    },
    "library-section-backup": {
      lower: ["library-section-detail"],
      inspector: ["library-section-backup"],
    },
    "library-section-settings": {
      lower: ["library-section-detail"],
      inspector: ["library-section-settings"],
    },
  },
};

function setWorkspaceSection(viewName, sectionId, { scroll = true } = {}) {
  document.querySelectorAll(`[data-workspace-view="${viewName}"]`).forEach((button) => {
    button.classList.toggle("active", button.dataset.workspaceTarget === sectionId);
  });
  if (!sectionId) return;
  const viewRoot = document.querySelector(`#view-${viewName}`);
  const paneLayout = WORKSPACE_PANE_LAYOUTS[viewName]?.[sectionId];
  const paneSections = viewRoot ? [...viewRoot.querySelectorAll(".workspace-section[data-workspace-pane]")] : [];
  if (paneLayout && paneSections.length) {
    paneSections.forEach((section) => {
      const paneName = section.dataset.workspacePane || "";
      const visibleIds = paneLayout[paneName] || [];
      section.hidden = !visibleIds.includes(section.id);
    });
  } else {
    document.querySelectorAll(`#view-${viewName} .workspace-section`).forEach((section) => {
      section.hidden = section.id !== sectionId;
    });
  }
  window.localStorage.setItem(`splitshot.${viewName}.section`, sectionId);
  if (!scroll) return;
  const scrollTargets = paneLayout && paneSections.length
    ? [
      document.querySelector(`#view-${viewName} .workspace-main-column`),
      document.querySelector(`#view-${viewName} .workspace-inspector`),
    ].filter(Boolean)
    : [document.querySelector(`#view-${viewName} .workspace-main`)].filter(Boolean);
  scrollTargets.forEach((target) => target.scrollTo?.({ top: 0, behavior: "smooth" }));
}

function applySavedWorkspaceSections() {
  setWorkspaceSection("match", window.localStorage.getItem("splitshot.match.section") || "match-section-stages", { scroll: false });
  setWorkspaceSection("library", window.localStorage.getItem("splitshot.library.section") || "library-section-overview", { scroll: false });
}

function workspaceShell(viewName) {
  if (!viewName) return null;
  return document.querySelector(`[data-shell-family="stage-workspace"][data-shell-view="${viewName}"]`)
    || document.querySelector(`.${viewName}-workspace-shell`)
    || document.querySelector(`#view-${viewName} .workspace-shell`);
}

function setWorkspaceRailCollapsed(viewName, collapsed) {
  const shell = workspaceShell(viewName);
  if (!shell) return;
  shell.classList.toggle("rail-collapsed", Boolean(collapsed));
  const toggle = document.getElementById(`${viewName}-toggle-rail`);
  if (toggle) {
    toggle.textContent = collapsed ? "▶" : "◀";
    toggle.title = collapsed ? `Expand ${viewName} rail` : `Minimize ${viewName} rail`;
    toggle.setAttribute("aria-label", toggle.title);
  }
  window.localStorage.setItem(`splitshot.${viewName}.railCollapsed`, String(Boolean(collapsed)));
}

function applySavedWorkspaceRailState() {
  setWorkspaceRailCollapsed("match", window.localStorage.getItem("splitshot.match.railCollapsed") === "true");
  setWorkspaceRailCollapsed("library", window.localStorage.getItem("splitshot.library.railCollapsed") === "true");
}

function wireEvents() {
  const result = shellRuntime?.wireEvents();
  document.querySelectorAll("[data-surface]").forEach((button) => {
    button.addEventListener("click", () => {
      setActiveSurface(button.dataset.surface);
      if (button.dataset.surface === "single") setActiveTool(activeTool || "project");
      if (button.dataset.surface === "multi") void refreshStageComposite();
      if (button.dataset.surface === "library") void refreshPerformanceLibrary();
      activity("ui.surface.click", { surface: button.dataset.surface });
    });
  });

  // Landing page card clicks - navigate to surface
  document.querySelectorAll(".landing-card").forEach((card) => {
    card.addEventListener("click", () => {
      const surface = card.dataset.surface;
      if (surface) setActiveSurface(surface);
      activity("ui.landing.card.click", { surface });
    });
  });

  // Landing page recent activity clicks
  $("landing-recent-list")?.addEventListener("click", (e) => {
    const item = e.target.closest(".landing-recent-item");
    if (!item) return;
    const surface = item.dataset.recentSurface;
    if (surface) setActiveSurface(surface);
  });

  // Quick-start buttons
  $("landing-new-stage")?.addEventListener("click", () => {
    setActiveSurface("single");
    activity("ui.landing.newstage.click");
  });

  $("landing-new-match")?.addEventListener("click", () => {
    setActiveSurface("multi");
    activity("ui.landing.newmatch.click");
  });

  $("landing-open-file")?.addEventListener("click", () => {
    void openPrimaryImportPathPicker();
    activity("ui.landing.openfile.click");
  });

  // Logo click returns to landing
  const logoElement = document.querySelector(".rail-logo");
  if (logoElement) {
    logoElement.style.cursor = "pointer";
    logoElement.addEventListener("click", () => {
      setActiveSurface("landing");
      activity("ui.logo.click");
    });
  }
  $("stage-go-home")?.addEventListener("click", () => setActiveSurface("landing"));
  $("match-go-home")?.addEventListener("click", () => setActiveSurface("landing"));
  $("library-go-home")?.addEventListener("click", () => setActiveSurface("landing"));
  $("match-open-settings")?.addEventListener("click", () => setWorkspaceSection("match", "match-section-settings"));
  $("library-open-settings")?.addEventListener("click", () => setWorkspaceSection("library", "library-section-settings"));
  $("match-toggle-rail")?.addEventListener("click", () => {
    const shell = workspaceShell("match");
    setWorkspaceRailCollapsed("match", !shell?.classList.contains("rail-collapsed"));
  });
  $("library-toggle-rail")?.addEventListener("click", () => {
    const shell = workspaceShell("library");
    setWorkspaceRailCollapsed("library", !shell?.classList.contains("rail-collapsed"));
  });
  document.querySelectorAll("[data-workspace-target]").forEach((button) => {
    button.addEventListener("click", () => {
      setWorkspaceSection(button.dataset.workspaceView || "", button.dataset.workspaceTarget || "");
    });
  });
  $("match-setting-show-score")?.addEventListener("change", () => {
    matchView?.persistMatchSettings();
    renderWorkspaceStages();
  });
  $("match-setting-remember-stage")?.addEventListener("change", () => matchView?.persistMatchSettings());
  $("library-setting-default-sort")?.addEventListener("change", () => {
    const sort = $("library-setting-default-sort")?.value || "event_date";
    if ($("library-sort")) $("library-sort").value = sort;
    libraryView?.persistLibrarySettings();
    void refreshPerformanceLibrary();
  });
  $("library-setting-auto-refresh")?.addEventListener("change", () => {
    libraryView?.persistLibrarySettings();
    automationStale.library = !(libraryView?.libraryAutoRefreshEnabled?.() ?? true) && activeSurface === "library";
    renderAutomationSurface();
  });
  $("library-error-retry")?.addEventListener("click", () => refreshPerformanceLibrary());
  $("library-stale-refresh")?.addEventListener("click", () => refreshPerformanceLibrary());
  $("output-profile-refresh")?.addEventListener("click", () => refreshAutomationProfiles());
  $("output-profile-create")?.addEventListener("click", () => {
    createAutomationOutputProfile($("output-profile-name")?.value || "Output Profile", $("output-profile-kind")?.value || "stage_output");
  });
  const cloneHookPayload = (value) => {
    if (value === null || value === undefined) return value;
    return typeof value === "object" ? JSON.parse(JSON.stringify(value)) : value;
  };
  const metricCaptionPresetFields = (selection) => {
    if (selection === "splits") return ["split_times", "cumulative_time"];
    if (selection === "score") return ["hit_factor", "penalties"];
    if (selection === "full") {
      return ["shot_count", "cumulative_time", "first_shot_reaction", "hit_factor", "penalties", "split_times"];
    }
    return [];
  };
  const buildMetricCaptionPresetPayload = ({ selection, position, leadInSeconds, tailSeconds, base }) => {
    const resolvedSelection = selection || "none";
    const next = base && typeof base === "object" ? cloneHookPayload(base) : {};
    next.preset = resolvedSelection;
    next.enabled_fields = metricCaptionPresetFields(resolvedSelection);
    next.position = position || next.position || "bottom_right";
    next.lead_in_padding_ms = Math.max(0, Math.round((Number(leadInSeconds) || 0) * 1000));
    next.tail_padding_ms = Math.max(0, Math.round((Number(tailSeconds) || 0) * 1000));
    return next;
  };
  const outputHookLabels = Object.freeze({
    "run-window": "Trim Settings",
    "metric-captions": "Export Badges",
    "frame-profiles": "Aspect Ratio / Framing",
    "lead-in-card": "Opening Title",
    "brand-mark": "Your Logo",
    "subject-track-crop": "Subject Tracking (inactive)",
  });
  const outputHookEditorHosts = Object.freeze({
    "run-window": "output-hook-host-merge",
    "metric-captions": "output-hook-host-overlay",
    "frame-profiles": "output-hook-host-export-frame",
    "lead-in-card": "output-hook-host-export-finishing",
    "brand-mark": "output-hook-host-export-finishing",
    "subject-track-crop": "output-hook-host-export-finishing",
  });
  const outputHookLabel = (hook) => outputHookLabels[hook] || hook.replace(/-/g, " ");
  function mountOutputHookEditor(hook) {
    const editor = $("output-hook-editor");
    if (!editor) return;
    const hostId = outputHookEditorHosts[hook] || "output-hook-host-export-finishing";
    const host = $(hostId) || $("output-hook-host-export-finishing");
    if (host && editor.parentElement !== host) host.appendChild(editor);
  }
  async function saveActiveOutputHookEditor() {
    const profile = activeAutomationProfile();
    if (!profile || !activeOutputHookEditor) {
      setStatus("Select an output profile before saving hooks.");
      return;
    }

    const update = {};
    if (activeOutputHookEditor === "run-window") {
      update.metric_caption_preset = buildMetricCaptionPresetPayload({
        selection: metricCaptionPresetSelection(profile),
        position: metricCaptionPosition(profile),
        leadInSeconds: $("hook-run-window-lead-in")?.value || runWindowLeadInSeconds(profile),
        tailSeconds: $("hook-run-window-tail")?.value || runWindowTailSeconds(profile),
        base: profile.metric_caption_preset,
      });
    } else if (activeOutputHookEditor === "metric-captions") {
      update.metric_caption_preset = buildMetricCaptionPresetPayload({
        selection: $("hook-metric-captions-preset")?.value || "none",
        position: $("hook-metric-captions-position")?.value || "bottom_right",
        leadInSeconds: runWindowLeadInSeconds(profile),
        tailSeconds: runWindowTailSeconds(profile),
        base: profile.metric_caption_preset,
      });
    } else if (activeOutputHookEditor === "frame-profiles") {
      update.frame_profile = $("hook-frame-profile")?.value || "source";
    } else if (activeOutputHookEditor === "lead-in-card") {
      update.lead_in_card = buildLeadInCardPayload(profile);
    } else if (activeOutputHookEditor === "brand-mark") {
      update.brand_mark = buildBrandMarkPayload(profile);
    } else if (activeOutputHookEditor === "subject-track-crop") {
      update.subject_track_crop = $("hook-crop-enabled")?.checked
        ? {
          enabled: true,
          margin_percent: Number($("hook-crop-margin")?.value || subjectTrackCropMarginPercent(profile) || 10),
        }
        : null;
    }

    await callApi("/api/output-profiles/update", {
      output_id: profile.output_id,
      ...update,
    });
    await refreshAutomationProfiles();
    const updatedProfile = activeAutomationProfile();
    if (updatedProfile) {
      const plan = await callApi("/api/output-profiles/render", { output_id: updatedProfile.output_id });
      renderJsonDetail("output-profile-detail", plan || updatedProfile);
      renderOutputHookEditor(activeOutputHookEditor, updatedProfile);
    }
    setStatus(`Saved ${outputHookLabel(activeOutputHookEditor)} for ${profile.profile_name || "output profile"}.`);
  }
  document.querySelectorAll("[data-output-hook]").forEach((button) => {
    button.addEventListener("click", () => {
      if (!activeAutomationProfile()) {
        setStatus("Create or select an output profile in Export before editing reusable trim, overlay, or finishing settings.");
        return;
      }
      const hook = button.dataset.outputHook;
      activeOutputHookEditor = hook;
      const active = activeAutomationProfile();
      renderOutputHookEditor(hook, active);
      renderOutputProfiles();
    });
  });
  $("output-hook-close")?.addEventListener("click", () => {
    activeOutputHookEditor = null;
    renderOutputProfiles();
  });
  $("output-hook-save")?.addEventListener("click", () => {
    void saveActiveOutputHookEditor();
  });

  renderOutputHookEditor = function renderOutputHookEditor(hook, activeProfile) {
    const editor = $("output-hook-editor");
    const title = $("output-hook-title");
    const fields = $("output-hook-fields");
    if (!editor || !title || !fields) return;
    mountOutputHookEditor(hook);
    editor.hidden = false;
    title.textContent = outputHookLabel(hook);
    const profile = activeProfile || {};
    const openedFromMatch = Boolean(state?.opened_from_match);
    fields.innerHTML = "";
    if (hook === "run-window") {
      fields.innerHTML = `<div class="control-grid">
        <label>Lead-in padding (s) <input id="hook-run-window-lead-in" type="number" min="0" step="0.1" value="${runWindowLeadInSeconds(profile)}" /></label>
        <label>Tail padding (s) <input id="hook-run-window-tail" type="number" min="0" step="0.1" value="${runWindowTailSeconds(profile)}" /></label>
      </div>
      <p class="hint">Set the lead-in and tail padding after the beep and last shot look right. Save these reusable trim settings on the selected output profile so stage output and stage composite exports stay aligned.</p>`;
    } else if (hook === "metric-captions") {
      fields.innerHTML = `<div class="control-grid">
        <label>Preset
          <select id="hook-metric-captions-preset">
            <option value="none" ${metricCaptionPresetSelection(profile) === "none" ? "selected" : ""}>None</option>
            <option value="splits" ${metricCaptionPresetSelection(profile) === "splits" ? "selected" : ""}>Splits</option>
            <option value="score" ${metricCaptionPresetSelection(profile) === "score" ? "selected" : ""}>Score</option>
            <option value="full" ${metricCaptionPresetSelection(profile) === "full" ? "selected" : ""}>Full</option>
          </select>
        </label>
        <label>Position
          <select id="hook-metric-captions-position">
            <option value="bottom_right" ${metricCaptionPosition(profile) === "bottom_right" ? "selected" : ""}>Bottom Right</option>
            <option value="bottom_left" ${metricCaptionPosition(profile) === "bottom_left" ? "selected" : ""}>Bottom Left</option>
          </select>
        </label>
      </div>
      <p class="hint">${openedFromMatch ? "Match defaults set the starting export badge set; save here when this output profile needs something different." : "Uses the current overlay styling, but lets this output profile decide which timing and score badges render into export."}</p>`;
    } else if (hook === "frame-profiles") {
      fields.innerHTML = `<div class="control-grid">
        <label>Profile
          <select id="hook-frame-profile">
            <option value="source" ${profile.frame_profile === "source" ? "selected" : ""}>Source</option>
            <option value="16:9" ${profile.frame_profile === "16:9" ? "selected" : ""}>16:9</option>
            <option value="9:16" ${profile.frame_profile === "9:16" ? "selected" : ""}>9:16</option>
            <option value="1:1" ${profile.frame_profile === "1:1" ? "selected" : ""}>1:1</option>
            <option value="4:5" ${profile.frame_profile === "4:5" ? "selected" : ""}>4:5</option>
          </select>
        </label>
      </div>
      <p class="hint">Stores the profile-specific aspect ratio and framing choice. Width and height still stay in the main Frame section below.</p>`;
    } else if (hook === "lead-in-card") {
      fields.innerHTML = `<div class="control-grid">
        <label>Style
          <select id="hook-lead-in-style">
            <option value="none" ${leadInCardStyle(profile) === "none" ? "selected" : ""}>None</option>
            <option value="stage_info" ${leadInCardStyle(profile) === "stage_info" ? "selected" : ""}>Stage Info</option>
            <option value="competitor" ${leadInCardStyle(profile) === "competitor" ? "selected" : ""}>Competitor</option>
          </select>
        </label>
        <label>Duration (s) <input id="hook-lead-in-duration" type="number" min="0" step="0.1" value="${leadInCardDurationSeconds(profile)}" /></label>
      </div>
      <div class="control-grid">
        <label>Animation
          <select id="hook-lead-in-animation">
            <option value="static" ${leadInCardAnimation(profile) === "static" ? "selected" : ""}>Static</option>
            <option value="fade" ${leadInCardAnimation(profile) === "fade" ? "selected" : ""}>Fade</option>
            <option value="slide_up" ${leadInCardAnimation(profile) === "slide_up" ? "selected" : ""}>Slide Up</option>
          </select>
        </label>
        <label>Logo scale (%) <input id="hook-lead-in-logo-scale" type="number" min="20" max="400" step="5" value="${leadInCardLogoScalePercent(profile)}" /></label>
      </div>
      <div class="control-grid">
        <label class="check-row"><input id="hook-lead-in-show-match" type="checkbox" ${leadInCardFieldEnabled(profile, "show_match") ? "checked" : ""} /> Match</label>
        <label class="check-row"><input id="hook-lead-in-show-stage" type="checkbox" ${leadInCardFieldEnabled(profile, "show_stage") ? "checked" : ""} /> Stage</label>
        <label class="check-row"><input id="hook-lead-in-show-shooter" type="checkbox" ${leadInCardFieldEnabled(profile, "show_shooter") ? "checked" : ""} /> Shooter</label>
      </div>
      <div class="control-grid">
        <label class="check-row"><input id="hook-lead-in-show-division" type="checkbox" ${leadInCardFieldEnabled(profile, "show_division") ? "checked" : ""} /> Division</label>
        <label class="check-row"><input id="hook-lead-in-show-classification" type="checkbox" ${leadInCardFieldEnabled(profile, "show_classification") ? "checked" : ""} /> Classification</label>
        <label class="check-row"><input id="hook-lead-in-show-date" type="checkbox" ${leadInCardFieldEnabled(profile, "show_date") ? "checked" : ""} /> Date</label>
      </div>
      <div class="control-grid">
        <label>Custom Title <input id="hook-lead-in-custom-title" type="text" placeholder="Optional title override" value="${escapeHtml(leadInCardTextValue(profile, "custom_title"))}" /></label>
        <label>Custom Subtitle <input id="hook-lead-in-custom-subtitle" type="text" placeholder="Optional subtitle override" value="${escapeHtml(leadInCardTextValue(profile, "custom_subtitle"))}" /></label>
      </div>
      <label>Logo file
        <div class="path-row">
          <input id="hook-lead-in-logo-path" type="text" placeholder="Optional local logo" value="${escapeHtml(leadInCardLogoPath(profile))}" />
          <button id="hook-lead-in-logo-pick" type="button">Choose</button>
        </div>
      </label>
      <p class="hint">Style picks a title preset, while the toggles decide which saved stage, shooter, division, classification, and date details the export title should include when available. Animation and logo settings save on the selected profile.</p>`;
      $("hook-lead-in-style")?.addEventListener("change", (event) => {
        applyLeadInCardStyleDefaults(event.target?.value || "none");
      });
      $("hook-lead-in-logo-pick")?.addEventListener("click", async () => {
        await pickPathForElement(
          "popup_image",
          $("hook-lead-in-logo-path"),
          "hook-lead-in-logo-path",
        );
      });
    } else if (hook === "brand-mark") {
      fields.innerHTML = `<div class="control-grid">
        <label>Mark
          <select id="hook-brand-mark-select">
            <option value="none" ${brandMarkStyle(profile) === "none" ? "selected" : ""}>None</option>
            <option value="splitshot" ${brandMarkStyle(profile) === "splitshot" ? "selected" : ""}>SplitShot</option>
            <option value="custom" ${brandMarkStyle(profile) === "custom" ? "selected" : ""}>Custom Text</option>
            <option value="image" ${brandMarkStyle(profile) === "image" ? "selected" : ""}>Image</option>
            <option value="image_text" ${brandMarkStyle(profile) === "image_text" ? "selected" : ""}>Image + Text</option>
          </select>
        </label>
        <label>Duration (s) <input id="hook-brand-mark-duration" type="number" min="0" step="0.1" value="${brandMarkDurationSeconds(profile)}" /></label>
      </div>
      <div class="control-grid">
        <label>Text <input id="hook-brand-mark-text" type="text" placeholder="Brand text" value="${escapeHtml(brandMarkTextValue(profile))}" /></label>
        <label>Position
          <select id="hook-brand-mark-position">
            <option value="top_left" ${brandMarkPosition(profile) === "top_left" ? "selected" : ""}>Top Left</option>
            <option value="top_right" ${brandMarkPosition(profile) === "top_right" ? "selected" : ""}>Top Right</option>
            <option value="bottom_left" ${brandMarkPosition(profile) === "bottom_left" ? "selected" : ""}>Bottom Left</option>
            <option value="bottom_right" ${brandMarkPosition(profile) === "bottom_right" ? "selected" : ""}>Bottom Right</option>
            <option value="center" ${brandMarkPosition(profile) === "center" ? "selected" : ""}>Center</option>
          </select>
        </label>
      </div>
      <div class="control-grid">
        <label>Opacity (%) <input id="hook-brand-mark-opacity" type="number" min="0" max="100" step="5" value="${brandMarkOpacityPercent(profile)}" /></label>
        <label>Text size (px) <input id="hook-brand-mark-font-size" type="number" min="8" max="96" step="1" value="${brandMarkFontSize(profile)}" /></label>
      </div>
      <div class="control-grid">
        <label>Text color <input id="hook-brand-mark-text-color" type="color" value="${brandMarkTextColor(profile)}" /></label>
        <label>Image scale (%) <input id="hook-brand-mark-image-scale" type="number" min="20" max="400" step="5" value="${brandMarkImageScalePercent(profile)}" /></label>
      </div>
      <label>Image file
        <div class="path-row">
          <input id="hook-brand-mark-image-path" type="text" placeholder="Optional local watermark image" value="${escapeHtml(brandMarkImagePath(profile))}" />
          <button id="hook-brand-mark-image-pick" type="button">Choose</button>
        </div>
      </label>
      <p class="hint">Your Logo can now be text, image, or both. Set duration to <code>0</code> to keep it visible for the full export.</p>`;
      $("hook-brand-mark-image-pick")?.addEventListener("click", async () => {
        await pickPathForElement(
          "popup_image",
          $("hook-brand-mark-image-path"),
          "hook-brand-mark-image-path",
        );
      });
    } else if (hook === "subject-track-crop") {
      fields.innerHTML = `<div class="control-grid">
        <label class="check-row"><input id="hook-crop-enabled" type="checkbox" ${subjectTrackCropEnabled(profile) ? "checked" : ""} /> Enable subject track crop</label>
        <label>Margin % <input id="hook-crop-margin" type="number" min="0" max="50" step="1" value="${subjectTrackCropMarginPercent(profile)}" /></label>
      </div>
      <p class="hint">Reserved for a future tracker-backed workflow. Stage export does not currently ship an automatic keep shooter in frame feature.</p>`;
    }
  };
  $("retained-review-apply")?.addEventListener("click", () => {
    const profileId = $("retained-review-source")?.value;
    if (profileId) {
      retainedReviewSourceProfileId = profileId;
    } else {
      retainedReviewSourceProfileId = null;
    }
    renderOutputProfiles();
    const fallbackProfileId = activeAutomationProfile()?.output_id;
    if (profileId || fallbackProfileId) {
      callApi("/api/output-profiles/render", { output_id: profileId || fallbackProfileId });
    }
  });
  $("shared-defaults-apply")?.addEventListener("click", async () => {
    const payload = {
      frame_profile: $("shared-frame-profile")?.value || "source",
      metric_caption_preset: $("shared-metric-captions")?.value || "none",
      lead_in_card: $("shared-lead-in")?.value || "none",
      brand_mark: $("shared-brand-mark")?.value || "none",
    };
    await callApi("/api/workspace/defaults", payload);
    await refresh();
  });
  $("shared-defaults-reset")?.addEventListener("click", async () => {
    await callApi("/api/workspace/defaults/reset", {});
    await refresh();
  });
  $("override-apply")?.addEventListener("click", async () => {
    const stageId = currentWorkspaceStageId();
    if (!stageId) return;
    const overrides = {};
    const frameProfile = $("override-frame-profile")?.value;
    const metricCaptions = $("override-metric-captions")?.value;
    if (frameProfile) overrides.frame_profile = frameProfile;
    if (metricCaptions) overrides.metric_caption_preset = metricCaptions;
    if (Object.keys(overrides).length) {
      await callApi("/api/workspace/stage/override", { stage_id: stageId, ...overrides });
      await refresh();
    }
  });
  $("workspace-new")?.addEventListener("click", async () => {
    await runWorkspaceOperation(
      () => callApi("/api/workspace/new", {}),
      {
        failureMessage: "Failed to create a new workspace.",
        isSuccess: () => workspaceHasEntries(),
        onSuccess: async () => {
          selectedStageCompositeStageId = null;
          setActiveSurface("multi");
          await refresh();
        },
      },
    );
  });
  $("workspace-new-empty")?.addEventListener("click", async () => {
    await runWorkspaceOperation(
      () => callApi("/api/workspace/new", {}),
      {
        failureMessage: "Failed to create a new workspace.",
        isSuccess: () => workspaceHasEntries(),
        onSuccess: async () => {
          selectedStageCompositeStageId = null;
          setActiveSurface("multi");
          await refresh();
        },
      },
    );
  });
  $("workspace-open")?.addEventListener("click", async () => {
    await openWorkspaceWithPicker();
  });
  $("workspace-save")?.addEventListener("click", async () => {
    await saveWorkspaceFromUi();
  });
  $("match-name-input")?.addEventListener("change", (e) => {
    callApi("/api/workspace/save", { name: e.target.value });
  });
  $("workspace-stage-add")?.addEventListener("click", () => {
    const index = (state?.workspace_stage_entries?.length || 0) + 1;
    const stageId = `stage_${index}`;
    callApi("/api/workspace/stage/add", {
      stage_id: stageId,
      display_name: $("workspace-stage-name")?.value || `Stage ${index}`,
    });
  });
  $("stage-clip-add")?.addEventListener("click", async () => {
    const stageId = currentWorkspaceStageId();
    const sourcePath = $("stage-clip-path")?.value || "";
    if (!stageId || !sourcePath) {
      setStatus("Select a workspace stage and enter a clip path.");
      return;
    }
    await callApi("/api/workspace/stage/clip/add", {
      stage_id: stageId,
      source_path: sourcePath,
      camera_role: $("stage-clip-role")?.value || "primary",
    });
    await refreshStageComposite(stageId);
  });
  $("library-refresh")?.addEventListener("click", () => refreshPerformanceLibrary());
  $("library-search")?.addEventListener("input", debounce(() => refreshPerformanceLibrary(), 250));
  $("library-sort")?.addEventListener("change", () => refreshPerformanceLibrary());

  // Library export buttons
  $("library-export-csv")?.addEventListener("click", () => {
    activity("ui.library.export.csv");
    void exportLibraryData("csv");
  });

  $("library-export-json")?.addEventListener("click", () => {
    activity("ui.library.export.json");
    void exportLibraryData("json");
  });

  // Library discipline filter
  $("library-filter-discipline")?.addEventListener("change", () => { renderPerformanceLibrary(); const discipline = $("library-filter-discipline")?.value || ""; fetchLibraryAnalytics(discipline).then(renderAnalyticsCharts); });

  // Library tag handling
  $("library-tag-add")?.addEventListener("click", () => {
    const input = $("library-tag-input");
    if (!input?.value.trim()) return;
    const currentTags = selectedLibraryRecord?.tags || [];
    void persistSelectedLibraryTags([...currentTags, input.value.trim()]);
    input.value = "";
  });

  $("library-tag-list")?.addEventListener("click", (e) => {
    const removeBtn = e.target.closest(".tag-remove");
    if (!removeBtn) return;
    const nextTags = (selectedLibraryRecord?.tags || []).filter((tag) => tag !== removeBtn.dataset.tag);
    void persistSelectedLibraryTags(nextTags);
  });

  // Library notes
  $("library-notes-save")?.addEventListener("click", () => {
    const text = $("library-notes-text")?.value || "";
    void persistSelectedLibraryNotes(text);
  });
  $("library-open-stage")?.addEventListener("click", () => {
    void openSelectedLibraryStage();
  });
  $("library-open-workspace")?.addEventListener("click", () => {
    void openSelectedLibraryWorkspace();
  });
  // Backup
  $("library-backup-create")?.addEventListener("click", async () => {
    activity("ui.library.backup.create");
    const status = $("library-backup-status");
    if (status) {
      status.textContent = "Creating backup...";
      status.className = "hint";
    }
    try {
      const result = await callApi("/api/library/backup/create", {});
      if (status) {
        const manifest = result.manifest || result;
        const stageCount = manifest.total_stages || 0;
        const matchCount = manifest.total_matches || 0;
        status.textContent = `Backup created: ${stageCount} stages, ${matchCount} matches`;
        status.className = "backup-status-success";
      }
    } catch (e) {
      if (status) {
        status.textContent = "Backup failed: " + (e.message || "Unknown error");
        status.className = "backup-status-error";
      }
    }
  });

  // Restore
  $("library-backup-restore")?.addEventListener("click", () => {
    activity("ui.library.backup.restore");
    const input = document.createElement("input");
    input.type = "file";
    input.accept = ".json";
    input.onchange = async (e) => {
      const file = e.target.files?.[0];
      if (!file) return;
      const status = $("library-backup-status");
      try {
        const text = await file.text();
        const manifest = JSON.parse(text);
        if (status) {
          status.textContent = "Restoring backup...";
          status.className = "hint";
        }
        const result = await callApi("/api/library/backup/restore", { manifest });
        if (status) {
          status.textContent = `Restored: ${result.stages_restored || 0} stages, ${result.matches_restored || 0} matches`;
          status.className = "backup-status-success";
        }
        await refreshPerformanceLibrary();
      } catch (e) {
        if (status) {
          status.textContent = "Restore failed: " + (e.message || "Invalid backup file");
          status.className = "backup-status-error";
        }
      }
    };
    input.click();
  });

  $("setup-once-apply")?.addEventListener("click", async () => {
    activity("ui.setup-once.apply");
    const preview = await callApi("/api/workspace/apply-from-first/preview", { workspace_id: state?.project?.id });
    if (!preview || preview.error) {
      setStatus(preview?.error || "Failed to preview Stage 1 settings.");
      return;
    }
    const previewLines = (preview?.preview || []).slice(0, 6).map((entry) => {
      const changeCount = Array.isArray(entry?.changes) ? entry.changes.length : 0;
      const conflictCount = Array.isArray(entry?.conflicts) ? entry.conflicts.length : 0;
      const stageLabel = entry.display_name || entry.stage_name || entry.stage_id;
      if (conflictCount) return `- ${stageLabel}: ${changeCount} change(s), ${conflictCount} override conflict(s)`;
      if (changeCount) return `- ${stageLabel}: ${changeCount} change(s)`;
      return `- ${stageLabel}: unchanged`;
    });
    const previewMessage = [
      `Apply ${preview?.source_stage || "Stage 1"} settings to other stages?`,
      "",
      ...(previewLines.length ? previewLines : ["- No sibling stages need changes."]),
      "",
      "This copies shared defaults and reusable output profiles while keeping explicit stage overrides.",
    ].join("\n");
    if (!confirm(previewMessage)) return;
    const result = await callApi("/api/workspace/apply-from-first", { workspace_id: state?.project?.id });
    if (!result || result.error) {
      setStatus(result?.error || "Failed to apply Stage 1 settings.");
      return;
    }
    await refresh();
    const conflictCount = Array.isArray(result?.conflicts) ? result.conflicts.length : 0;
    setStatus(
      conflictCount
        ? `Applied Stage 1 settings to ${result?.applied || 0} stage(s) with ${conflictCount} override conflict(s).`
        : `Applied Stage 1 settings to ${result?.applied || 0} stage(s).`,
    );
  });
  $("setup-once-dismiss")?.addEventListener("click", () => {
    const banner = domById("setup-once-banner");
    if (banner) banner.hidden = true;
  });
  $("batch-select-all")?.addEventListener("click", () => {
    const items = document.querySelectorAll(".batch-export-item input[type=checkbox]:not(:disabled)");
    items.forEach((cb) => { cb.checked = true; });
  });
  $("batch-select-none")?.addEventListener("click", () => {
    const items = document.querySelectorAll(".batch-export-item input[type=checkbox]");
    items.forEach((cb) => { cb.checked = false; });
  });
  $("batch-export-start")?.addEventListener("click", async () => {
    const recipe = domById("batch-recipe")?.value || "stage_output";
    const checked = document.querySelectorAll(".batch-export-item input[type=checkbox]:checked:not(:disabled)");
    const resultsPanel = domById("batch-export-results");
    if (!checked.length) {
      setStatus("Select at least one stage to export.");
      const status = domById("batch-export-status");
      if (status) status.textContent = "Select at least one stage to export.";
      if (resultsPanel) {
        resultsPanel.hidden = true;
        resultsPanel.textContent = "";
      }
      return;
    }
    const stageIds = Array.from(checked).map((cb) => cb.closest(".batch-export-item")?.dataset?.stageId).filter(Boolean);
    const progress = domById("batch-export-progress");
    const status = domById("batch-export-status");
    const fill = progress?.querySelector(".progress-fill");
    const outputs = [];
    const errors = [];
    if (progress) progress.hidden = false;
    if (resultsPanel) {
      resultsPanel.hidden = true;
      resultsPanel.textContent = "";
    }
    for (let i = 0; i < stageIds.length; i++) {
      if (status) status.textContent = `Exporting ${i + 1} of ${stageIds.length}: ${stageIds[i]}...`;
      if (fill) fill.style.width = `${Math.round((i / stageIds.length) * 100)}%`;
      const result = await callApi("/api/workspace/export", { stage_id: stageIds[i], recipe });
      if (result?.outputs?.length) outputs.push(...result.outputs);
      if (result?.errors?.length) errors.push(...result.errors);
      if (result?.error && !result?.errors?.length) {
        errors.push({ stage_id: stageIds[i], error: result.error });
      }
      if (!result) {
        errors.push({ stage_id: stageIds[i], error: $("status")?.textContent || "Export failed." });
      }
      if (fill) fill.style.width = `${Math.round(((i + 1) / stageIds.length) * 100)}%`;
    }
    if (progress) progress.hidden = true;
    if (status) {
      status.textContent = errors.length
        ? `Exported ${outputs.length} stage(s) with ${errors.length} error(s).`
        : `Exported ${outputs.length} stage(s).`;
    }
    if (resultsPanel) {
      resultsPanel.hidden = false;
      resultsPanel.textContent = JSON.stringify({ recipe, outputs, errors }, null, 2);
    }
    if (outputs.length) {
      showExportCompleteNotification(outputs.length, outputs[0]?.output_path || "");
    }
  });

  // Keyboard view switching: Ctrl/Cmd + 1/2/3
  document.addEventListener("keydown", (e) => {
    if ((e.ctrlKey || e.metaKey) && !e.target.closest("input, textarea, select, [contenteditable]")) {
      if (e.key === "1") { e.preventDefault(); setActiveSurface("single"); }
      if (e.key === "2") { e.preventDefault(); setActiveSurface("multi"); }
      if (e.key === "3") { e.preventDefault(); setActiveSurface("library"); }
    }
  });

  // Match export button
  document.getElementById("match-export")?.addEventListener("click", async () => {
    await callApi("/api/workspace/export", {});
    showGlobalError("Export started. Check the processing bar for progress.", { duration: 4000 });
  });

  setActiveSurface(activeSurface, { persist: false, openPanel: false });
  void refreshAutomationProfiles();
  return result;
}

function wireElectronProjectOpen() {
  if (!window.splitshot || typeof window.splitshot.onOpenProject !== "function") {
    return;
  }
  window.splitshot.onOpenProject((projectPath) => {
    void (async () => {
      if (!projectPath) return;
      try {
        const result = await projectPane?.useProjectFolder(projectPath);
        if (!result) {
          setStatus("Project open cancelled.");
        }
      } catch (error) {
        setStatus(error?.message || "Failed to open project.");
      }
    })();
  });
}

const runtimeBackbone = Object.freeze({
  bus: appBus,
  store: appStore,
  storePatch: syncBackboneStore,
});

const runtimeBackboneStateBindings = {
  state: [() => state, (value) => { setStateValue(value); }],
  selectedShotId: [() => selectedShotId, (value) => { setSelectedShotIdValue(value); }],
  activeTool: [() => activeTool, (value) => { setActiveToolValue(value); }],
  overlayFrame: [() => overlayFrame, (value) => { overlayFrame = value; }],
  overlayFrameMode: [() => overlayFrameMode, (value) => { overlayFrameMode = value; }],
  waveformMode: [() => waveformMode, (value) => { waveformMode = value; }],
  draggingShotId: [() => draggingShotId, (value) => { draggingShotId = value; }],
  draggingShotPointerId: [() => draggingShotPointerId, (value) => { draggingShotPointerId = value; }],
  pendingDragTimeMs: [() => pendingDragTimeMs, (value) => { pendingDragTimeMs = value; }],
  waveformPanDrag: [() => waveformPanDrag, (value) => { waveformPanDrag = value; }],
  waveformNavigatorDrag: [() => waveformNavigatorDrag, (value) => { waveformNavigatorDrag = value; }],
  timingRowEdits: [() => timingRowEdits, (value) => { timingRowEdits = value; }],
  timingAdjustmentDrafts: [() => timingAdjustmentDrafts, (value) => { timingAdjustmentDrafts = value; }],
  scoringRowEdits: [() => scoringRowEdits, (value) => { scoringRowEdits = value; }],
  reviewTextBoxExpansion: [() => reviewTextBoxExpansion, (value) => { reviewTextBoxExpansion = value; }],
  popupBubbleExpansion: [() => popupBubbleExpansion, (value) => { popupBubbleExpansion = value; }],
  mergeSourceExpansion: [() => mergeSourceExpansion, (value) => { mergeSourceExpansion = value; }],
  shotMLSectionExpansion: [() => shotMLSectionExpansion, (value) => { shotMLSectionExpansion = value; }],
  settingsSectionExpansion: [() => settingsSectionExpansion, (value) => { settingsSectionExpansion = value; }],
  selectedPopupBubbleId: [() => selectedPopupBubbleId, (value) => { selectedPopupBubbleId = value; }],
  selectedPopupKeyframeOffsetMs: [() => selectedPopupKeyframeOffsetMs, (value) => { selectedPopupKeyframeOffsetMs = value; }],
  selectedPopupPlacementMode: [() => selectedPopupPlacementMode, (value) => { selectedPopupPlacementMode = value; }],
  popupFilterMode: [() => popupFilterMode, (value) => { popupFilterMode = value; }],
  popupAuthoringCollapsed: [() => popupAuthoringCollapsed, (value) => { popupAuthoringCollapsed = value; }],
  popupEditorVisible: [() => popupEditorVisible, (value) => { popupEditorVisible = value; }],
  popupEditorCollapsed: [() => popupEditorCollapsed, (value) => { popupEditorCollapsed = value; }],
  popupEditorSectionExpansion: [() => popupEditorSectionExpansion, (value) => { popupEditorSectionExpansion = value; }],
  popupGeneratedMotionOffsetsByBubbleId: [() => popupGeneratedMotionOffsetsByBubbleId, (value) => { popupGeneratedMotionOffsetsByBubbleId = value; }],
  popupMotionGenerationSummaryByBubbleId: [() => popupMotionGenerationSummaryByBubbleId, (value) => { popupMotionGenerationSummaryByBubbleId = value; }],
  popupAutoTraceBubbleId: [() => popupAutoTraceBubbleId, (value) => { popupAutoTraceBubbleId = value; }],
  popupWorkbenchHeight: [() => popupWorkbenchHeight, (value) => { popupWorkbenchHeight = value; }],
  popupWorkbenchRestoreState: [() => popupWorkbenchRestoreState, (value) => { popupWorkbenchRestoreState = value; }],
  scoringWorkbenchExpanded: [() => scoringWorkbenchExpanded, (value) => { scoringWorkbenchExpanded = value; }],
  overlayVisibilityPosition: [() => overlayVisibilityPosition, (value) => { overlayVisibilityPosition = value; }],
  railCollapsed: [() => railCollapsed, (value) => { railCollapsed = value; }],
  overlayStyleMode: [() => overlayStyleMode, (value) => { overlayStyleMode = value; }],
  overlaySpacing: [() => overlaySpacing, (value) => { overlaySpacing = value; }],
  overlayMargin: [() => overlayMargin, (value) => { overlayMargin = value; }],
  waveformZoomX: [() => waveformZoomX, (value) => { waveformZoomX = value; }],
  waveformShotAmplitudeById: [() => waveformShotAmplitudeById, (value) => { waveformShotAmplitudeById = value; }],
  waveformOffsetMs: [() => waveformOffsetMs, (value) => { waveformOffsetMs = value; }],
  busyCount: [() => busyCount, (value) => { busyCount = value; }],
  layoutLocked: [() => layoutLocked, (value) => { layoutLocked = value; }],
  layoutSizes: [() => layoutSizes, (value) => { layoutSizes = value; }],
  layoutSizePinned: [() => layoutSizePinned, (value) => { layoutSizePinned = value; }],
  activeResize: [() => activeResize, (value) => { activeResize = value; }],
  timingColumnWidths: [() => timingColumnWidths, (value) => { timingColumnWidths = value; }],
  timingColumnResize: [() => timingColumnResize, (value) => { timingColumnResize = value; }],
  currentProjectId: [() => currentProjectId, (value) => { currentProjectId = value; }],
  exportPathDraft: [() => exportPathDraft, (value) => { exportPathDraft = value; }],
  exportDraft: [() => exportDraft, (value) => { exportDraft = value; }],
  projectDetailsDraft: [() => projectDetailsDraft, (value) => { projectDetailsDraft = value; }],
  projectFolderProbeRequestId: [() => projectFolderProbeRequestId, (value) => { projectFolderProbeRequestId = value; }],
  secondaryPreviewSyncFrame: [() => secondaryPreviewSyncFrame, (value) => { secondaryPreviewSyncFrame = value; }],
  secondaryPreviewPlayErrorKey: [() => secondaryPreviewPlayErrorKey, (value) => { secondaryPreviewPlayErrorKey = value; }],
  overlayColorCommitTimer: [() => overlayColorCommitTimer, (value) => { overlayColorCommitTimer = value; }],
  processingBarShowTimer: [() => processingBarShowTimer, (value) => { processingBarShowTimer = value; }],
  processingBarHideTimer: [() => processingBarHideTimer, (value) => { processingBarHideTimer = value; }],
  processingBarVisibleAtMs: [() => processingBarVisibleAtMs, (value) => { processingBarVisibleAtMs = value; }],
  processingProgressTimer: [() => processingProgressTimer, (value) => { processingProgressTimer = value; }],
  processingProgressPercent: [() => processingProgressPercent, (value) => { processingProgressPercent = value; }],
  activeProcessingPath: [() => activeProcessingPath, (value) => { activeProcessingPath = value; }],
  activityQueue: [() => activityQueue, (value) => { activityQueue = value; }],
  activityFlushTimer: [() => activityFlushTimer, (value) => { activityFlushTimer = value; }],
  activityCursor: [() => activityCursor, (value) => { activityCursor = value; }],
  activityPollTimer: [() => activityPollTimer, (value) => { activityPollTimer = value; }],
  overlayBadgeDrag: [() => overlayBadgeDrag, (value) => { overlayBadgeDrag = value; }],
  mergePreviewDrag: [() => mergePreviewDrag, (value) => { mergePreviewDrag = value; }],
  textBoxDrag: [() => textBoxDrag, (value) => { textBoxDrag = value; }],
  popupBubbleDrag: [() => popupBubbleDrag, (value) => { popupBubbleDrag = value; }],
  exportLogLines: [() => exportLogLines, (value) => { exportLogLines = value; }],
  activeColorPickerControl: [() => activeColorPickerControl, (value) => { activeColorPickerControl = value; }],
  reviewStageRestoreFrame: [() => reviewStageRestoreFrame, (value) => { reviewStageRestoreFrame = value; }],
  reviewStageRestoreSecondFrame: [() => reviewStageRestoreSecondFrame, (value) => { reviewStageRestoreSecondFrame = value; }],
  overlayBadgeMeasureCanvas: [() => overlayBadgeMeasureCanvas, (value) => { overlayBadgeMeasureCanvas = value; }],
  overlayAutoBubbleCacheKey: [() => overlayAutoBubbleCacheKey, (value) => { overlayAutoBubbleCacheKey = value; }],
  overlayAutoBubbleCache: [() => overlayAutoBubbleCache, (value) => { overlayAutoBubbleCache = value; }],
  customOverlayRenderKey: [() => customOverlayRenderKey, (value) => { customOverlayRenderKey = value; }],
  textBoxRenderedPositionById: [() => textBoxRenderedPositionById, (value) => { textBoxRenderedPositionById = value; }],
  metricsSectionExpansion: [() => metricsSectionExpansion, (value) => { metricsSectionExpansion = value; }],
  pendingInspectorScrollTop: [() => pendingInspectorScrollTop, (value) => { pendingInspectorScrollTop = value; }],
  lastInspectorUserScrollTop: [() => lastInspectorUserScrollTop, (value) => { lastInspectorUserScrollTop = value; }],
  lastInspectorUserScrollTs: [() => lastInspectorUserScrollTs, (value) => { lastInspectorUserScrollTs = value; }],
  renderDeferredForInteraction: [() => renderDeferredForInteraction, (value) => { renderDeferredForInteraction = value; }],
  pendingProjectUiStatePayload: [() => pendingProjectUiStatePayload, (value) => { pendingProjectUiStatePayload = value; }],
  lastSubmittedProjectUiStatePayloadKey: [() => lastSubmittedProjectUiStatePayloadKey, (value) => { lastSubmittedProjectUiStatePayloadKey = value; }],
  pendingMergeSourcePayloads: [() => pendingMergeSourcePayloads, (value) => { pendingMergeSourcePayloads = value; }],
  mergeSourceCommitTimers: [() => mergeSourceCommitTimers, (value) => { mergeSourceCommitTimers = value; }],
  interactionPreviewFrame: [() => interactionPreviewFrame, (value) => { interactionPreviewFrame = value; }],
  pendingInteractionPreview: [() => pendingInteractionPreview, (value) => { pendingInteractionPreview = value; }],
  pendingSelectionFallback: [() => pendingSelectionFallback, (value) => { pendingSelectionFallback = value; }],
};

const legacyGlobalState = createMutableBindings(runtimeBackboneStateBindings);

const runtimeBackboneState = createMutableBindings({
  ...runtimeBackboneStateBindings,
  initialProjectUiStateApplied: [() => initialProjectUiStateApplied, (value) => { initialProjectUiStateApplied = value; }],
  pendingBootstrapProjectUiStateOverride: [() => pendingBootstrapProjectUiStateOverride, (value) => { pendingBootstrapProjectUiStateOverride = value; }],
});

processingRuntime = createProcessingRuntime({
  backbone: runtimeBackbone,
  runtime: runtimeBackboneState,
  $,
  clampNumber,
  clearCurrentExportLogState,
  activity,
  PROCESSING_BAR_SHOW_DELAY_MS,
  PROCESSING_BAR_MIN_VISIBLE_MS,
});

activityRuntime = createActivityRuntime({
  backbone: runtimeBackbone,
  runtime: runtimeBackboneState,
  renderExportLog,
  setProcessingProgress,
  ACTIVITY_FLUSH_DELAY_MS,
  ACTIVITY_BATCH_SIZE,
  ACTIVITY_POLL_INTERVAL_MS,
});

layoutRuntime = createLayoutRuntime({
  backbone: runtimeBackbone,
  runtime: runtimeBackboneState,
  $,
  clamp,
  DEFAULT_LAYOUT_SIZES,
  INSPECTOR_COMPACT_WIDTH,
  computeExportCropBox,
  exportTargetDimensions,
  markersWorkbenchShown,
  scheduleInteractionPreviewRender,
  syncLocalProjectUiState,
  scheduleProjectUiStateApply,
  renderWaveform,
  activity,
  setWaveformExpanded,
  scheduleReviewStageRestore,
  capturePointer,
  releasePointer,
  flushInteractionPreviewRender,
  flushQueuedProjectUiStateApply,
  flushDeferredRender,
});

keyRuntime = createKeyRuntime({
  backbone: runtimeBackbone,
  runtime: runtimeBackboneState,
  selectedShot,
  activity,
  callApi,
  deleteShotById,
  getState: () => state,
});

apiRuntime = createApiRuntime({
  backbone: runtimeBackbone,
  runtime: runtimeBackboneState,
  processingForPath,
  requestRender,
  activity,
  beginProcessing,
  forceHideProcessingBar,
  setStatus,
  mergeProjectUiState,
  normalizeProjectUiState,
  shotSelectionContext,
  resolveSelectedShotId,
  mergeProjectDetailsDraft,
  mergeMergeDraft,
  mergePendingMergeSourcePayloads: (project) => mergePane?.mergePendingMergeSourcePayloads(project),
  mergeOverlayPositionDraft,
  mergeOverlayStyleDraft,
  mergeOverlayTextBoxesDraft,
  applyPopupDraft,
  mergePopupDraft,
  mergeExportDraft,
  setStateValue,
  applyProjectUiState,
  syncSelectedShotId,
  syncLocalProjectUiState,
  resetLocalProjectView,
  readProjectUiStatePayload,
});

statusBarComponent = createStatusBarComponent({
  $,
  getState: () => state,
  normalizeProjectNameValue,
  fileName,
  syncControlValue,
  setProjectActionAvailability,
  renderDetailsList,
  splitSeconds,
});

videoPlayerComponent = createVideoPlayerComponent({
  $,
  getState: () => state,
  getSelectedShotId: () => selectedShotId,
  maybeApplyRecommendedLayout,
  buildMediaUrl,
  resetMediaElement,
  isImagePath,
  ensurePrimaryVideoAudio,
  logPrimaryVideoState,
  currentPipSizePercent,
  previewFrameGeometry,
  normalizedCoordinateValue,
  sourceIdentifier,
  resolvedMergeSourcePreviewPlacement,
  mergeSourceUsesFreeformPreviewDrag,
  currentSourceOpacity,
  mergeSourcePipRect,
  renderMergePreviewLayer,
  scheduleSecondaryPreviewSync,
});

waveformStateRuntime = createWaveformState({
  $,
  clamp,
  getState: () => state,
  getWaveformZoomX: () => waveformZoomX,
  setWaveformZoomX: (value) => { waveformZoomX = value; },
  getWaveformOffsetMs: () => waveformOffsetMs,
  setWaveformOffsetMs: (value) => { waveformOffsetMs = value; },
  syncLocalProjectUiState,
  scheduleProjectUiStateApply,
  storage: window.localStorage,
  waveformWindowHandleMinPx: WAVEFORM_WINDOW_HANDLE_MIN_PX,
});

waveformComponent = createWaveformComponent({
  $,
  windowObject: window,
  getState: () => state,
  getSelectedShotId: () => selectedShotId,
  setSelectedShotIdValue,
  getWaveformMode: () => waveformMode,
  getWaveformZoomX: () => waveformZoomX,
  getWaveformOffsetMs: () => waveformOffsetMs,
  getDraggingShotId: () => draggingShotId,
  setDraggingShotId: (value) => { draggingShotId = value; },
  getDraggingShotPointerId: () => draggingShotPointerId,
  setDraggingShotPointerId: (value) => { draggingShotPointerId = value; },
  getPendingDragTimeMs: () => pendingDragTimeMs,
  setPendingDragTimeMs: (value) => { pendingDragTimeMs = value; },
  getWaveformPanDrag: () => waveformPanDrag,
  setWaveformPanDrag: (value) => { waveformPanDrag = value; },
  getWaveformNavigatorDrag: () => waveformNavigatorDrag,
  setWaveformNavigatorDrag: (value) => { waveformNavigatorDrag = value; },
  getWaveformShotAmplitudeById: () => waveformShotAmplitudeById,
  waveformState: waveformStateRuntime,
  currentPrimaryVideoPositionMs,
  selectShot,
  capturePointer,
  releasePointer,
  withPreservedScrollState,
  seconds,
  formatConfidenceValue,
  isLowConfidence,
  activity,
  callApi,
  deleteShotById,
  scheduleInteractionPreviewRender,
  flushInteractionPreviewRender,
  flushQueuedProjectUiStateApply,
  flushDeferredRender,
  panDragThresholdPx: WAVEFORM_PAN_DRAG_THRESHOLD_PX,
});

shotmlPane = createShotMLPane({
  $,
  documentObject: document,
  getState: () => state,
  getShotMLSectionExpansion: () => shotMLSectionExpansion,
  syncLocalProjectUiState,
  scheduleProjectUiStateApply,
  syncControlValue,
  syncControlChecked,
  formatConfidenceValue,
  renderCollapsibleInspectorSections,
  callApi,
});

markersPane = createMarkersPane({
  $,
  documentObject: document,
  windowObject: window,
  getState: () => state,
  getActiveTool: () => activeTool,
  getSelectedShotId: () => selectedShotId,
  getPopupBubbleExpansion: () => popupBubbleExpansion,
  getSelectedPopupBubbleId: () => selectedPopupBubbleId,
  setSelectedPopupBubbleIdValue: (value) => { selectedPopupBubbleId = value; },
  getSelectedPopupKeyframeOffsetMs: () => selectedPopupKeyframeOffsetMs,
  setSelectedPopupKeyframeOffsetValue: (value) => { selectedPopupKeyframeOffsetMs = value; },
  getSelectedPopupPlacementMode: () => selectedPopupPlacementMode,
  setSelectedPopupPlacementModeValue: (value) => { selectedPopupPlacementMode = value; },
  getPopupFilterMode: () => popupFilterMode,
  setPopupFilterModeValue: (value) => { popupFilterMode = value; },
  getPopupAuthoringCollapsed: () => popupAuthoringCollapsed,
  setPopupAuthoringCollapsedValue: (value) => { popupAuthoringCollapsed = value; },
  getPopupBubbleDrag: () => popupBubbleDrag,
  setPopupBubbleDrag: (value) => { popupBubbleDrag = value; },
  getPopupAutoTraceBubbleId: () => popupAutoTraceBubbleId,
  getPopupGeneratedMotionOffsetsByBubbleId: () => popupGeneratedMotionOffsetsByBubbleId,
  getPopupMotionGenerationSummaryByBubbleId: () => popupMotionGenerationSummaryByBubbleId,
  normalizePopupBubble,
  currentPopupTemplate,
  popupBubbles,
  createPopupBubbleId,
  defaultScoreLetter,
  seekPrimaryVideoToTimeMs,
  popupBubbleSeekTimeMs,
  revealPopupBubbleCard,
  popupDefaultDurationMsForShot,
  popupTemplateTextForShot,
  orderedShotsByTime,
  timingSegmentForShot,
  shotById,
  compactScoreDisplay,
  activeScoringRuleset,
  popupTextForShotId,
  defaultPopupShotId,
  clampPopupDurationForShot,
  popupBubbleMotionPath,
  scaledPopupMotionPathOffsets,
  normalizePopupMotionPath,
  normalizePopupMotionMode,
  normalizePopupQuadrant,
  popupBubblePoint,
  popupBubbleEffectiveTimeMs,
  popupBubbleResolvedText,
  popupBubbleIsVisibleAtPosition,
  popupBubbleRenderPositionMs,
  popupBubblePlacementSelectorStyle,
  popupBubbleRenderStyle,
  resolvedPopupBubbleSize,
  scaledOverlayPixelValue,
  popupBubbleImageUrl,
  popupKeyframeEasing,
  popupBubbleMotionPointAtOffset,
  popupMotionModeValueForUiMode,
  popupBubbleMotionUiMode,
  popupMotionOffsetIsGenerated,
  popupMotionGeneratedOffsetsForBubbleId,
  setPopupMotionGeneratedOffsets,
  prunePopupMotionUiState,
  renderPopupEditors,
  renderLiveOverlay,
  render,
  callApi,
  setStatus,
  activity,
  setActiveTool,
  controlIsActive,
  syncControlValue,
  syncControlChecked,
  setPopupEditorSectionExpanded,
  copyPopupMotionUiState,
  precise,
  clamp,
  normalizedCoordinateValue,
  previewFrameClientRect,
  overlayRenderPositionMs,
  resolveNormalizedPointFromRect,
  capturePointer,
  releasePointer,
  placeOverlayBadge,
  rgba,
  capturePopupWorkbenchRestoreState,
  cancelOverlayDragInteractions,
  stagePopupImagePath,
  syncLocalProjectUiState,
  scheduleProjectUiStateApply,
  scheduleReviewStageRestore,
  primaryFrameDurationMs,
  popupMotionSuggestedInBetweenCount,
  popupMotionAutoOffsets,
  popupMotionSamplePointForOffset,
  popupMotionNextDetailOffsetMs,
  autoTracePopupBubbleMotion: (...args) => autoTracePopupBubbleMotion(...args),
  VALID_POPUP_FILTER_MODES,
  CUSTOM_QUADRANT_VALUE,
  scoreBadgeTokens,
});

overlayPane = createOverlayPane({
  $,
  documentObject: document,
  windowObject: window,
  getState: () => state,
  getOverlayStyleMode: () => overlayStyleMode,
  setOverlayStyleMode: (value) => { overlayStyleMode = value; },
  getOverlaySpacing: () => overlaySpacing,
  setOverlaySpacing: (value) => { overlaySpacing = value; },
  getOverlayMargin: () => overlayMargin,
  setOverlayMargin: (value) => { overlayMargin = value; },
  getOverlayVisibilityPosition: () => overlayVisibilityPosition,
  setOverlayVisibilityPosition: (value) => { overlayVisibilityPosition = value; },
  getOverlayColorCommitTimer: () => overlayColorCommitTimer,
  setOverlayColorCommitTimer: (value) => { overlayColorCommitTimer = value; },
  getOverlayBadgeDrag: () => overlayBadgeDrag,
  setOverlayBadgeDrag: (value) => { overlayBadgeDrag = value; },
  getTextBoxDrag: () => textBoxDrag,
  setTextBoxDrag: (value) => { textBoxDrag = value; },
  getCustomOverlayRenderKey: () => customOverlayRenderKey,
  setCustomOverlayRenderKey: (value) => { customOverlayRenderKey = value; },
  getTextBoxRenderedPositionById: () => textBoxRenderedPositionById,
  setTextBoxRenderedPositionById: (value) => { textBoxRenderedPositionById = value; },
  normalizedCoordinateValue,
  normalizeOverlayTextBox,
  overlayTextBoxes,
  preferredLegacyTextBox,
  syncLegacyOverlayBoxState,
  setLocalOverlayTextBoxes,
  overlayTextBoxDisplayText,
  overlayTextBoxLabel,
  resolvedOverlayTextBoxSize,
  syncOverlayBubbleSizeControls,
  syncControlValue,
  clamp,
  clampNumber,
  isColorInput,
  readColorControlValue,
  setColorControlValue,
  overlayHexControlFor,
  syncOverlayHexControl,
  openColorPicker,
  updateColorFromHexInput,
  opacityValueFromPercent,
  validOverlayBadgeNames: VALID_OVERLAY_BADGE_NAMES,
  overlayStackLockControls: OVERLAY_STACK_LOCK_CONTROLS,
  badgeFontSizes: BADGE_FONT_SIZES,
  customQuadrantValue: CUSTOM_QUADRANT_VALUE,
  aboveFinalTextBoxValue: ABOVE_FINAL_TEXT_BOX_VALUE,
  overlayColorCommitDelayMs: OVERLAY_COLOR_COMMIT_DELAY_MS,
  usesCustomQuadrant,
  scheduleInteractionPreviewRender,
  scheduleOverlayApply,
  previewFrameClientRect,
  resolveNormalizedPointFromRect,
  roundedRect,
  positionOverlayContainer,
  pinCustomOverlayAnchor,
  placeOverlayBadge,
  previewFrameGeometry,
  overlayDisplayScale,
  overlayAutoBubbleSize,
  textBiasForDirection,
  currentShotIndex,
  overlayRenderPositionMs,
  orderedShotsByTime,
  shotDisplayTimeMs,
  resolvedSplitMsForShot,
  splitRowIntervalLabel,
  scoreBadgeContent,
  splitSeconds,
  seconds,
  badgeElement,
  scaledOverlayPixelValue,
  alignToEdge,
  renderPopupOverlay,
  popupEditingActive,
  capturePointer,
  releasePointer,
  activity,
  callApi,
  cancelAutoApplyOverlay,
  renderTextBoxEditors,
  flushInteractionPreviewRender,
  queueInspectorScrollRestore,
  flushDeferredRender,
});

overlayCanvasComponent = createOverlayCanvasComponent({
  $,
  windowObject: window,
  getState: () => state,
  getSelectedShotId: () => selectedShotId,
  getOverlayFrame: () => overlayFrame,
  setOverlayFrame: (value) => { overlayFrame = value; },
  getOverlayFrameMode: () => overlayFrameMode,
  setOverlayFrameMode: (value) => { overlayFrameMode = value; },
  activity,
  scheduleSecondaryPreviewSync,
  renderLiveOverlay,
  renderWaveformPlayhead,
  currentPrimaryVideoPositionMs,
});

exportPane = createExportPane({
  $,
  getState: () => state,
  getExportPathDraft: () => exportPathDraft,
  setExportPathDraft: (value) => { exportPathDraft = value; },
  getExportLogLines: () => exportLogLines,
  getActiveProcessingPath: () => activeProcessingPath,
  getProcessingProgressPercent: () => processingProgressPercent,
  metricsFileStem,
  downloadTextFile,
  setStatus,
  applyExportDraft,
  autoApplyExportLayout,
  autoApplyExportSettings,
});

settingsPane = createSettingsPane({
  $,
  documentObject: document,
  getState: () => state,
  getSettingsSectionExpansion: () => settingsSectionExpansion,
  syncControlValue,
  syncControlChecked,
  readNumberSetting,
  readProjectUiStatePayload,
  normalizePopupTemplate,
  renderExportPresetOptions,
  ensureSectionToggle,
  settingsLayerFields: SETTINGS_LAYER_FIELDS,
});

mergePane = createMergePane({
  $,
  documentObject: document,
  windowObject: window,
  getState: () => state,
  getMergeSourceExpansion: () => mergeSourceExpansion,
  getMergeDraft: () => mergeDraft,
  getPendingMergeSourcePayloads: () => pendingMergeSourcePayloads,
  getMergeSourceCommitTimers: () => mergeSourceCommitTimers,
  normalizedCoordinateValue,
  clampNumber,
  opacityPercentValue,
  opacityValueFromPercent,
  syncControlValue,
  preserveElementViewportAnchor,
  withPreservedScrollState,
  scheduleInteractionPreviewRender,
  scheduleSecondaryPreviewSync,
  renderLiveOverlay,
  renderVideo,
  callApi,
  activity,
  autoApplyMerge,
  syncLocalProjectUiState,
  scheduleProjectUiStateApply,
  fileName,
  buildMediaUrl,
  previewFrameGeometry,
  pipDefaultsSectionId: PIP_DEFAULTS_SECTION_ID,
  sendKeepaliveJson,
});

projectPane = createProjectPane({
  $,
  windowObject: window,
  documentObject: document,
  getState: () => state,
  getProjectDetailsDraft: () => projectDetailsDraft,
  setProjectDetailsDraft: (value) => { projectDetailsDraft = value; },
  getProjectFolderProbeRequestId: () => projectFolderProbeRequestId,
  setProjectFolderProbeRequestId: (value) => { projectFolderProbeRequestId = value; },
  setForcedProjectLandingPersistedTool: (value) => { forcedProjectLandingPersistedTool = value ? normalizeToolId(value) : null; },
  controlIsActive,
  normalizeToolId,
  setActiveTool,
  applyProjectUiStatePayload,
  cancelPendingExportDrafts,
  flushPendingSettingsDefaults,
  cancelAutoApplySettingsDefaults: () => scheduleSettingsDefaultsApply.cancel?.(),
  shouldSyncShotMLSettingsBeforePrimaryImport: () => shotMLSettingsNeedSyncBeforePrimaryImport(),
  hasPendingPrimaryImportKeepaliveDrafts: () => hasPendingPrimaryImportKeepaliveDrafts(),
  readShotMLSettingsPayload,
  readOverlayPayload,
  readMergePayload,
  flushPendingMergeSourceCommits,
  readExportLayoutPayload,
  readExportSettingsPayload,
  readScoringPayload,
  callApi,
  sendKeepaliveJson,
  sendProjectUiStateKeepalive,
  pickPath,
  fileName,
  splitSeconds,
  formatNumber,
  formatMatchType,
  formatPractiScoreTime,
  autoApplyProjectDetails,
  autoApplyPractiScoreContext,
  renderDetailsList,
  renderHeader,
  setStatus,
  activity,
});

reviewPane = createReviewPane({
  $,
  windowObject: window,
  documentObject: document,
  getState: () => state,
  getReviewTextBoxExpansion: () => reviewTextBoxExpansion,
  syncLocalProjectUiState,
  scheduleProjectUiStateApply,
  normalizedCoordinateValue,
  normalizeHexColor,
  clamp,
  clampNumber,
  opacityValueFromPercent,
  measureOverlayBadgeContent,
  overlayBadgePaddingXPx: OVERLAY_BADGE_PADDING_X_PX,
  overlayBadgePaddingYPx: OVERLAY_BADGE_PADDING_Y_PX,
  aboveFinalTextBoxValue: ABOVE_FINAL_TEXT_BOX_VALUE,
  customQuadrantValue: CUSTOM_QUADRANT_VALUE,
  usesCustomQuadrant,
  resolveRenderedTextBoxCoordinates,
  unlockedOverlayTextBox,
  previewOverlayControlChanges,
  scheduleOverlayApply,
  applyOverlayTextBoxesDraft,
  syncControlValue,
  syncControlChecked,
  syncOpacityPercentControl,
  controlIsActive,
  isColorInput,
  bindOverlayColorInput,
  preserveElementViewportAnchor,
  withPreservedScrollState,
  getReviewStageRestoreFrame: () => reviewStageRestoreFrame,
  setReviewStageRestoreFrame: (value) => { reviewStageRestoreFrame = value; },
  getReviewStageRestoreSecondFrame: () => reviewStageRestoreSecondFrame,
  setReviewStageRestoreSecondFrame: (value) => { reviewStageRestoreSecondFrame = value; },
  applyLayoutState,
  renderVideo,
  renderWaveform,
  renderTimingTables,
  renderLiveOverlay,
  scheduleSecondaryPreviewSync,
  restoreVideoElementFrame,
});

timingPane = createTimingPane({
  $,
  documentObject: document,
  windowObject: window,
  getState: () => state,
  getSelectedShotId: () => selectedShotId,
  setSelectedShotIdValue,
  getPendingSelectionFallback: () => pendingSelectionFallback,
  setPendingSelectionFallback: (value) => { pendingSelectionFallback = value; },
  getTimingRowEdits: () => timingRowEdits,
  getTimingAdjustmentDrafts: () => timingAdjustmentDrafts,
  getScoringRowEdits: () => scoringRowEdits,
  getTimingColumnWidths: () => timingColumnWidths,
  setTimingColumnWidths: (value) => { timingColumnWidths = value; },
  getTimingColumnResize: () => timingColumnResize,
  setTimingColumnResize: (value) => { timingColumnResize = value; },
  getTimingExpanded: () => Boolean($("cockpit-root")?.classList.contains("timing-expanded")),
  activity,
  syncLocalProjectUiState,
  scheduleProjectUiStateApply,
  scheduleReviewStageRestore,
  capturePointer,
  releasePointer,
  withPreservedScrollState,
  callApi,
  selectShot,
  orderedShotsByTime,
  seconds,
  numericMs,
  formatConfidenceValue,
  isLowConfidence,
  defaultTimingEventLabel,
  timingEventKindLabel,
  timingEventPlacementText,
  shotSelectionContext,
  syncExpandWaveformButton,
  renderTimingTables,
  toggleTimingRowEdit,
  resolvedTimingColumnWidths,
  timingGridTemplate,
  scoringWorkbenchGridTemplate,
  timingColumnDefaults: TIMING_COLUMN_DEFAULTS,
  timingColumnMinWidths: TIMING_COLUMN_MIN_WIDTHS,
  timingResizableColumns: TIMING_RESIZABLE_COLUMNS,
});

scoringPane = createScoringPane({
  $,
  windowObject: window,
  getState: () => state,
  getSelectedShotId: () => selectedShotId,
  setSelectedShotIdValue,
  getScoringWorkbenchExpanded: () => scoringWorkbenchExpanded,
  setScoringWorkbenchExpandedValue: (value) => { scoringWorkbenchExpanded = value; },
  getScoringRowEdits: () => scoringRowEdits,
  setScoringRowEdits: (value) => { scoringRowEdits = value; },
  activity,
  syncLocalProjectUiState,
  scheduleProjectUiStateApply,
  scheduleReviewStageRestore,
  applyTimingTableColumns,
  withPreservedScrollState,
  splitRowForShot,
  splitSeconds,
  numericMs,
  formatNumber,
  formatMatchType,
  formatPractiScoreTime,
  formatImportedCounts,
  penaltyFieldLabel,
  compactScoreDisplay,
  activeScoringRuleset,
  isLowConfidence,
  selectShot,
  splitRowShotMLSplitMs,
  splitRowSequenceTotalMs,
  buildSplitRowActionCell,
  deleteShotById,
  restoreOriginalScore,
  defaultScoreLetter,
  collectPenaltyCounts,
  callApi,
  refreshReviewMediaFrame,
  renderDetailsList,
  practiScoreCompetitors,
  autoApplyScoring,
});

metricsPane = createMetricsPane({
  $,
  documentObject: document,
  windowObject: window,
  getState: () => state,
  getMetricsSectionExpansion: () => metricsSectionExpansion,
  activity,
  syncLocalProjectUiState,
  scheduleProjectUiStateApply,
  scheduleReviewStageRestore,
  syncExpandWaveformButton,
  withPreservedScrollState,
  splitRowShotMLConfidence,
  splitRowShotMLSplitMs,
  splitRowShotMLCumulativeMs,
  splitRowFinalTimeMs,
  splitRowSequenceTotalMs,
  splitRowActionSummary,
  splitRowActions,
  splitRowCumulativeMs,
  splitRowIntervalLabel,
  splitRowEntryLabel,
  defaultScoreLetter,
  formatPenaltyCountsText,
  splitSeconds,
  numericMs,
  signedSeconds,
  formatConfidenceValue,
  formatNumber,
  precise,
  fileName,
  renderDetailsList,
  setStatus,
  ensureSectionToggle,
  metricsTableColumns: METRICS_TABLE_COLUMNS,
});

shellRuntime = createShellRuntime({
  $,
  documentObject: document,
  windowObject: window,
  getState: () => state,
  getActiveTool: () => activeTool,
  setActiveTool,
  getRailCollapsed: () => railCollapsed,
  setRailCollapsed: (value) => { railCollapsed = value; },
  getOverlayVisibilityPosition: () => overlayVisibilityPosition,
  setOverlayVisibilityPosition: (value) => { overlayVisibilityPosition = value; },
  getOverlayStyleMode: () => overlayStyleMode,
  setOverlayStyleMode: (value) => { overlayStyleMode = value; },
  getOverlaySpacing: () => overlaySpacing,
  setOverlaySpacing: (value) => { overlaySpacing = value; },
  getOverlayMargin: () => overlayMargin,
  setOverlayMargin: (value) => { overlayMargin = value; },
  getExportPathDraft: () => exportPathDraft,
  setExportPathDraft: (value) => { exportPathDraft = value; },
  resetMergeDraft: () => { mergeDraft = {}; },
  resetExportDraft: () => { exportDraft = {}; },
  getOverlayFrame: () => overlayFrame,
  setPreviewSeekBoundary,
  getPopupFilterMode: () => popupFilterMode,
  getPopupAuthoringCollapsed: () => popupAuthoringCollapsed,
  setPopupAuthoringCollapsed,
  getSelectedShotId: () => selectedShotId,
  syncSelectedShotId,
  withPreservedScrollState,
  scrollRenderTargets,
  applyLayoutState,
  renderHeader,
  renderStats,
  renderVideo,
  renderWaveform,
  renderTimingTables,
  renderLiveOverlay,
  requestRender,
  flushPendingInspectorScrollRestore,
  rememberInspectorScrollPosition,
  maybeApplyRecommendedLayout,
  renderShotML,
  renderCollapsibleInspectorSections,
  formatSyncOffsetLabel,
  currentSourceSyncOffsetMs,
  projectDetailValue,
  renderPractiScoreOptionLists,
  syncControlValue,
  syncControlChecked,
  currentPipSizePercent,
  overlayBadgeLockedToStack,
  syncOverlayBubbleSizeControls,
  syncOverlayCoordinateControlState,
  syncOverlayBubbleLockControlState,
  renderTextBoxEditors,
  renderPopupEditors,
  syncTimingEventLabelState,
  syncExportPathControl,
  renderScoringPresetOptions,
  renderPractiScoreSummaries,
  renderExportPresetOptions,
  renderExportLog,
  renderSettingsPane,
  renderMetricsPanel,
  renderMergeMediaList,
  badgeControls,
  badgeDisplayLabels,
  scoringColorOptions,
  bindOverlayColorInput,
  isColorInput,
  syncOpacityPercentControl,
  createNewProject,
  hasActiveProject,
  setStatus,
  gatedProjectActionMessage,
  importTypedPath,
  browseProjectPath,
  pickPath,
  pickPathForElement,
  scheduleExportSettingsApply,
  requireValue,
  flushPendingProjectDrafts,
  callApi,
  openHiddenFileInput,
  postFile,
  postFiles,
  validatePractiScoreSelection,
  openPractiScoreDashboard,
  syncPractiScoreSelectionFields,
  schedulePractiScoreContextApply,
  scheduleProjectDetailsApply,
  scheduleScoringApply,
  handleStageFullscreenChange,
  logPrimaryVideoState,
  markPreviewSeekBoundary,
  scheduleSecondaryPreviewSync,
  startOverlayLoop,
  stopOverlayLoop,
  renderWaveformPlayhead,
  setWaveformMode,
  setWaveformExpanded,
  setWaveformZoom,
  setWaveformAmplitude,
  resetWaveformView,
  setTimingExpanded,
  setMarkersExpanded,
  syncLocalProjectUiState,
  scheduleProjectUiStateApply,
  setScoringWorkbenchExpanded,
  setMetricsExpanded,
  handleWaveformPointerDown,
  handleWaveformPointerMove,
  handleWaveformPointerUp,
  handleWaveformNavigatorPointerDown,
  handleWaveformWheel,
  handleKeyboardEdit,
  handleWindowVisibilityRestore,
  cancelOverlayDragInteractions,
  handleViewportLayoutChange,
  scheduleThresholdApply,
  applyThresholdNow,
  scheduleShotMLSettingsApply,
  cancelMergeAutoApply: () => autoApplyMerge.cancel?.(),
  syncMergePreviewStateFromControls,
  scheduleInteractionPreviewRender,
  scheduleMergeApply,
  addTimingEvent,
  beginOverlayBadgeDrag,
  beginTextBoxDrag,
  beginMergePreviewDrag,
  beginPopupBubbleDrag,
  syncOverlayFontSizePreset,
  syncOverlayPreviewStateFromControls,
  scheduleOverlayApply,
  resetOverlayPlacementBaseline,
  ensureShotQuadrantDefaults,
  commitOverlayControlChanges,
  previewOverlayControlChanges,
  addOverlayTextBox,
  importShotPopups,
  createPopupBubbleForShot,
  addPopupBubble,
  toggleSelectedPopupEditor,
  setPopupFilterMode,
  selectAdjacentPopupBubble,
  popupBubbles,
  readPopupTemplatePayload,
  scheduleSettingsDefaultsApply,
  flushPendingSettingsDefaults,
  applySettingsDefaults,
  toggleLayoutLock,
  resetLayout,
  beginLayoutResize,
  moveLayoutResize,
  endLayoutResize,
  moveTimingColumnResize,
  endTimingColumnResize,
  moveOverlayBadgeDrag,
  endOverlayBadgeDrag,
  moveMergePreviewDrag,
  endMergePreviewDrag,
  moveTextBoxDrag,
  endTextBoxDrag,
  movePopupBubbleDrag,
  endPopupBubbleDrag,
  scheduleExportLayoutApply,
  buildExportPayload,
  applyExportDraft,
  cancelPendingExportDrafts,
  flushPendingMergeSourceCommits,
  openExportLogModal,
  downloadExportLog,
  closeExportLogModal,
  closeColorPicker,
  updateColorPickerFromSliders,
  updateColorPickerFromHexInput,
  exportMetrics,
  stopActivityPolling,
  flushPendingProjectDraftsKeepalive,
  flushActivityQueue,
  activity,
  DEFAULT_PROJECT_UI_STATE,
});

const legacyGlobalMutableBindings = {
  api: [() => api, (value) => { api = value; }],
  callApi: [() => callApi, (value) => { callApi = value; }],
  postFile: [() => postFile, (value) => { postFile = value; }],
  pickPath: [() => pickPath, (value) => { pickPath = value; }],
  pickPathForElement: [() => pickPathForElement, (value) => { pickPathForElement = value; }],
  openHiddenFileInput: [() => openHiddenFileInput, (value) => { openHiddenFileInput = value; }],
  postFiles: [() => postFiles, (value) => { postFiles = value; }],
  selectedLibraryRecord: [() => selectedLibraryRecord, (value) => { selectedLibraryRecord = value; }],
  createNewProject: [() => createNewProject, (value) => { createNewProject = value; }],
  useProjectFolder: [() => useProjectFolder, (value) => { useProjectFolder = value; }],
  openPractiScoreDashboard: [() => openPractiScoreDashboard, (value) => { openPractiScoreDashboard = value; }],
  applySettingsDefaults: [() => applySettingsDefaults, (value) => { applySettingsDefaults = value; }],
  flushPendingSettingsDefaults: [() => flushPendingSettingsDefaults, (value) => { flushPendingSettingsDefaults = value; }],
  renderTextBoxEditors: [() => renderTextBoxEditors, (value) => { renderTextBoxEditors = value; }],
  setReviewTextBoxExpanded: [() => setReviewTextBoxExpanded, (value) => { setReviewTextBoxExpanded = value; }],
  setPopupBubbles: [() => setPopupBubbles, (value) => { setPopupBubbles = value; }],
  autoTracePopupBubbleMotion: [() => autoTracePopupBubbleMotion, (value) => { autoTracePopupBubbleMotion = value; }],
  render: [() => render, (value) => { render = value; }],
  refresh: [() => refresh, (value) => { refresh = value; }],
};

installLegacyGlobalCompat({
  target: window,
  valueSources: [
    activityRuntime,
    processingRuntime,
    layoutRuntime,
    keyRuntime,
    apiRuntime,
    statusBarComponent,
    videoPlayerComponent,
    waveformStateRuntime,
    waveformComponent,
    overlayCanvasComponent,
    shotmlPane,
    markersPane,
    overlayPane,
    exportPane,
    settingsPane,
    mergePane,
    projectPane,
    reviewPane,
    timingPane,
    scoringPane,
    metricsPane,
  ],
  values: {
    normalizeToolId, normalizeExportDraftValue, applyExportDraft, mergeExportDraft,
    seconds, precise, splitSeconds, numericMs,
    orderedShotsByTime, orderedShotsByTimeFromState, shotSelectionContext, fallbackSelectedShotId,
    resolveSelectedShotId, syncSelectedShotId, splitRowForShot, resolvedSplitMsForShot,
    formatMatchType, formatNumber, formatPractiScoreTime, formatImportedCounts,
    penaltyFieldLabel, formatPenaltyCountsText, scoreTokenColor, scoreBadgeTokens,
    formatShotBadgeSuffix, shotBadgeBaseText, scoreBadgeContent, scoringColorOptions,
    defaultScoreLetter, activeScoringRuleset, compactScoreDisplay, shotById,
    timingSegmentForShot, popupTextForShotId, formatConfidenceValue, isLowConfidence,
    numberInputValue, collectPenaltyCounts, renderDetailsList, requireValue,
    controlIsActive, captureScrollState, restoreScrollState, withPreservedScrollState,
    scrollContainerForElement, preserveElementViewportAnchor, scrollRenderTargets, resetInspectorHorizontalScroll,
    rememberInspectorScrollPosition, queueInspectorScrollRestore, flushPendingInspectorScrollRestore, hasActivePointerInteraction,
    requestRender, flushDeferredRender, scheduleInteractionPreviewRender, flushInteractionPreviewRender,
    syncControlValue, syncControlChecked, opacityPercentValue, opacityValueFromPercent,
    syncOpacityPercentControl, roundedRect, isColorInput, fileName,
    mediaCacheToken, buildMediaUrl, colorControlButton, colorControlLabel,
    readColorControlValue, setColorControlValue, rgbToHex, rgbToHsl,
    hexToHsl, hueToRgb, hslToRgb, hslToHex,
    hexToRgb, rgba, normalizeHexColor, overlayHexControlFor,
    syncOverlayHexControl, updateColorFromHexInput, colorPickerModal, syncColorPickerModal,
    applyColorControlValue, openColorPicker, closeColorPicker, updateColorPickerFromSliders,
    updateColorPickerFromHexInput, renderColorPickerSwatches, clampNumber, isImagePath,
    setStatus, debounce, savedNumber,
    clamp, normalizedUiBooleanMap, normalizedUiFloatMap, normalizedUiStringList,
    resolvedTimingColumnWidths, timingGridTemplate, scoringWorkbenchGridTemplate, normalizeProjectUiState,
    mergeProjectUiState, projectUiStatePayloadKey, shouldApplyProjectUiStatePayload, readProjectUiStatePayload,
    syncLocalProjectUiState, applyProjectUiState, normalizedCoordinateValue, formattedCoordinateValue,
    syncOverlayFontSizePreset, ensureShotQuadrantDefaults, usesCustomQuadrant, defaultTimingEventLabel,
    timingEventKindLabel, timingEventPlacementText, ensureSectionToggle, renderCollapsibleInspectorSections,
    createPopupBubbleId, normalizePopupAnchorMode, normalizePopupQuadrant, normalizePopupMotionPoint,
    normalizePopupMotionPath, normalizePopupMotionMode, popupMotionUiModeFromValue, popupTemplateUsesShotSplitDuration,
    popupShotDurationLimitMs, popupShotDefaultDurationMs, clampPopupDurationForShot, popupDefaultDurationMsForShot,
    popupDurationLimitMsForBubble, normalizePopupBubble, normalizePopupTemplate, currentPopupTemplate,
    popupTemplateTextForShot, popupBubbles, popupBubbleMotionPath, popupBubbleMotionUiMode,
    popupMotionGeneratedOffsetsForBubbleId, popupMotionOffsetIsGenerated, setPopupMotionGeneratedOffsets, copyPopupMotionUiState,
    prunePopupMotionUiState, popupTemplateMotionUiMode, popupMotionModeValueForUiMode, popupKeyframeEasing,
    popupKeyframeRatio, scaledPopupMotionPathOffsets, popupBubbleMotionPointAtOffset, popupBubblePoint,
    updatePopupBubbleMotionPoint, popupBubbleAutoSize, resolvedPopupBubbleSize, popupBubbleEffectiveTimeMs,
    popupBubbleVisibleWindow, popupBubbleRenderPositionMs, popupBubbleIsVisibleAtPosition, popupBubbleSeekTimeMs,
    defaultPopupShotId, popupBubbleShotOptions, popupBubbleShotLabel, popupBubbleResolvedText,
    popupBubblePlacementSelectorStyle, popupBubbleRenderStyle, popupBubbleDisplayName, popupBubbleImageUrl,
    popupBubbleSummaryText, isPopupBubbleExpanded, setPopupBubbleExpanded, popupEditorSectionDefaultExpanded,
    isPopupEditorSectionExpanded, setPopupEditorSectionExpanded, renderPopupEditorSectionToggles, collapseMinimizableInspectorItems,
    popupBubbleNavigatorElement, popupBubbleEditorCardElement, popupBubbleCardElement, revealPopupBubbleCard,
    popupShotPenaltyCounts, popupShotHasPenaltySignal, popupShotHasScoringSignal, popupMotionDistancePx,
    popupMotionFrameDurationMs, popupMotionSuggestedInBetweenCount, popupMotionAutoOffsets, popupMotionNearestFreeOffset,
    popupMotionNextDetailOffsetMs, popupMotionSamplePointForOffset, adjacentPopupKeyframeOffset, popupTraceFrameSize,
    popupTraceWaitForVideoFrame, popupTraceWaitForEvent, popupTraceSeekVideo, popupTraceLumaFrame,
    popupTraceClampCenter, popupTracePatchMoments, popupTraceExtractPatch, popupTracePatchStrength,
    popupTraceSelectPatch, popupTracePatchCorrelation, popupTraceBestMatch, popupTraceOffsets,
    popupTraceSimplifyPoints, autoTracePopupBubbleMotion, renderPopupBubbleMotionGuide, buildPopupBubbleCard,
    buildPopupMarkerRow, buildPopupFloatingEditor, renderPopupFloatingEditor, renderPopupAuthoringControls,
    readPopupTemplatePayload, renderPopupTimeline, setPopupFilterMode, setPopupEditorVisible,
    setPopupEditorCollapsed, openSelectedPopupEditor, toggleSelectedPopupEditor, renderMarkersWorkbench,
    selectAdjacentPopupBubble, stepShotLinkedPopupBubble, renderPopupEditors, syncTimingEventLabelState,
    alignToEdge, capturePointer, releasePointer, setActiveTool, setActiveSurface,
    postFile, pickPath, pickPathForElement, resetLocalProjectView,
    resetMediaElement, restoreVideoElementFrame, handleStageFullscreenChange, handleWindowVisibilityRestore,
    primaryVideoStateSnapshot, logPrimaryVideoState, ensurePrimaryVideoAudio, renderWaveformNavigator,
    primaryFrameDurationMs, browserShotPresentationLagFrames, shotDisplayTimeMs, currentShotIndex,
    currentSettings, readNumberSetting, syncMergePreviewElements, syncSecondaryPreview,
    clearSecondaryPreviewPlayError, reportSecondaryPreviewPlayError, scheduleSecondaryPreviewSync, selectShot,
    seekPrimaryVideoToTimeMs, seekPrimaryVideoToShot, selectedShot, shotLabelForEvent,
    formatTimingValue, toggleTimingRowEdit, restoreOriginalScore, renderTimingTable,
    renderTimingTables, markersWorkbenchShown, popupEditingActive,
    visibleTimingEventsByShot, textBiasForDirection, overlayBadgeContentText, overlayBadgeFontSizePx,
    overlayBadgeMeasureContext, overlayBadgeFontSpec, measureOverlayBadgeContent, overlayAutoSizedBadgeContents,
    overlayAutoBubbleSize, syncOverlayBubbleSizeControls, badgeElement, videoContentRect,
    ensureEvenExportDimension, exportAspectRatioValue, normalizedExportDimension, computeExportCropBox,
    exportTargetDimensions, fitAspectRect, previewFrameGeometry, previewFrameClientRect,
    overlayDisplayScale, scaledOverlayPixelValue, positionOverlayContainer, pinCustomOverlayAnchor,
    resolveNormalizedPointFromRect, placeOverlayBadge, cancelOverlayDragInteractions, beginMergePreviewDrag,
    moveMergePreviewDrag, endMergePreviewDrag, overlayRenderPositionMs, popupOverlayPixelPoint,
    render, renderAutomationSurface, renderViewportLayout, setWaveformMode, setWaveformExpanded,
    setWaveformZoom, panWaveform, handleWaveformWheel, setWaveformAmplitude,
    resetWaveformView, openHiddenFileInput, postFiles, buildExportPayload,
    cancelPendingExportDrafts, flushPendingSettingsDefaults, applySettingsDefaults, applySettingsShotMLDefaults,
    applyProjectUiStatePayload, resetProjectUiStateApplyState,
  },
  mutableSources: [legacyGlobalState],
  mutableBindings: legacyGlobalMutableBindings,
  backbone: runtimeBackbone,
  bootstrapMode: "module",
});

applyLayoutState();

// Default to the landing page on normal app loads (skip in test/automation environments)
const isAutomated = window.navigator.webdriver || false;
if (!isAutomated) {
  window.localStorage.setItem("splitshot.hasVisited", "true");
  activeSurface = "landing";
  setActiveSurface("landing", { persist: true, openPanel: false });
} else if (activeSurface === "landing") {
  activeSurface = "single";
  setActiveSurface("single", { persist: false, openPanel: false });
}
setActiveTool(activeTool, { collapseExpandedLayout: false, persistUiState: false });
matchView?.applySavedMatchSettings();
libraryView?.applySavedLibrarySettings();
applySavedWorkspaceSections();
applySavedWorkspaceRailState();
wireElectronProjectOpen();
wireGlobalActivityLogging();
wireEvents();
wireShellHeaderEvents();
wireLandingNavigation();
startActivityPolling();
refresh();

// === Test Global Exposure ===
// Expose module variables for Playwright tests. Object.defineProperty is used so
// reassignments of the module-level variables are automatically reflected.
Object.defineProperties(window, {
  state: { get: () => state, configurable: true },
  activeTool: { get: () => activeTool, configurable: true },
  activeSurface: { get: () => activeSurface, configurable: true },
  setPreviewSeekBoundary: { value: setPreviewSeekBoundary, configurable: true },
  markPreviewSeekBoundary: { value: markPreviewSeekBoundary, configurable: true },
  layoutLocked: {
    get: () => layoutLocked,
    set: (value) => {
      layoutLocked = Boolean(value);
    },
    configurable: true,
  },
  layoutSizes: {
    get: () => layoutSizes,
    set: (value) => {
      if (!value || typeof value !== "object") return;
      layoutSizes = {
        railWidth: Number(value.railWidth ?? layoutSizes.railWidth) || layoutSizes.railWidth,
        inspectorWidth:
          Number(value.inspectorWidth ?? layoutSizes.inspectorWidth)
          || layoutSizes.inspectorWidth,
        waveformHeight:
          Number(value.waveformHeight ?? layoutSizes.waveformHeight)
          || layoutSizes.waveformHeight,
      };
    },
    configurable: true,
  },
});
