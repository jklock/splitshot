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

const $ = (id) => document.getElementById(id);

const badgeControls = [
  ["timer_badge", "Timer Badge"],
  ["shot_badge", "Shot Badge"],
  ["current_shot_badge", "Current Shot Badge"],
  ["hit_factor_badge", "Score Badge"],
];
const BADGE_FONT_SIZES = {
  XS: 10,
  S: 12,
  M: 14,
  L: 16,
  XL: 20,
};
const CUSTOM_QUADRANT_VALUE = "custom";

function activity(event, detail = {}) {
  const payload = { event, detail };
  console.info("[splitshot]", event, detail);
  fetch("/api/activity", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
    keepalive: true,
  }).catch((error) => {
    console.warn("[splitshot] activity log failed", error);
  });
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

function requireValue(id, label) {
  const value = $(id).value.trim();
  if (!value) throw new Error(`${label} is required.`);
  return value;
}

function fileName(path) {
  if (!path) return "No video selected";
  const normalized = path.replaceAll("\\", "/");
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

function clampNumber(value, min, max) {
  return Math.min(max, Math.max(min, value));
}

function isImagePath(path) {
  return !!path && /\.(png|jpe?g|webp|gif|bmp|svg)$/i.test(path);
}

function setStatus(message) {
  $("status").textContent = message;
  const processingMessage = $("processing-message");
  if (processingMessage) processingMessage.textContent = message;
  activity("ui.status", { message });
}

function beginProcessing(message, detail = "Working locally") {
  busyCount += 1;
  const bar = $("processing-bar");
  $("processing-message").textContent = message;
  $("processing-detail").textContent = detail;
  bar.hidden = false;
  activity("ui.processing.start", { message, detail, busy_count: busyCount });
  return (finalMessage = "Ready.") => {
    busyCount = Math.max(0, busyCount - 1);
    activity("ui.processing.finish", { message: finalMessage, busy_count: busyCount });
    if (busyCount === 0) {
      $("processing-message").textContent = finalMessage;
      $("processing-detail").textContent = "Ready";
      bar.hidden = true;
    }
  };
}

function debounce(fn, delayMs = 250) {
  let timer = null;
  return (...args) => {
    window.clearTimeout(timer);
    timer = window.setTimeout(() => fn(...args), delayMs);
  };
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
  overlay.custom_box_text = payload.custom_box_text || "";
  overlay.custom_box_quadrant = payload.custom_box_quadrant;
  overlay.custom_box_x = normalizedCoordinateValue(payload.custom_box_x);
  overlay.custom_box_y = normalizedCoordinateValue(payload.custom_box_y);
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

function layoutViewportHeight() {
  const cockpit = document.querySelector(".cockpit");
  const documentHeight = document.documentElement?.clientHeight || 0;
  const visualViewportHeight = window.visualViewport?.height || 0;
  return Math.max(1, Math.floor(cockpit?.clientHeight || documentHeight || visualViewportHeight || window.innerHeight));
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
    if (!$("processing-bar").hidden) {
      busyCount = 0;
      $("processing-bar").hidden = true;
    }
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
    return { message: "Importing merge media...", detail: "Adding media to the merge list" };
  }
  if (path === "/api/import/secondary") {
    return { message: "Importing merge media...", detail: "Adding media to the merge list" };
  }
  if (path === "/api/project/details") return { message: "Updating project details...", detail: "Saving metadata locally" };
  if (path === "/api/project/save") return { message: "Saving project...", detail: "Updating project bundle" };
  if (path === "/api/project/delete") return { message: "Deleting project...", detail: "Removing project bundle" };
  if (path === "/api/project/new") return { message: "Creating new project...", detail: "Resetting project state" };
  return null;
}

async function postFile(path, file) {
  if (!file) return null;
  const form = new FormData();
  form.append("file", file, file.name);
  const finishProcessing = beginProcessing(`Analyzing ${file.name}...`, "Detecting beep and shots");
  setStatus(`Analyzing ${file.name} locally...`);
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
  const response = await fetch("/api/state");
  applyRemoteState(await response.json());
  render();
}

function applyRemoteState(nextState) {
  const nextProjectId = nextState?.project?.id || "";
  if (currentProjectId && nextProjectId && currentProjectId !== nextProjectId) {
    resetLocalProjectView();
  }
  currentProjectId = nextProjectId;
  state = nextState;
  if (selectedShotId && !(state.project.analysis.shots || []).some((shot) => shot.id === selectedShotId)) {
    selectedShotId = state.project.ui_state?.selected_shot_id || null;
  }
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
    "current-file",
    "timing-summary",
    "selected-shot-copy",
    "selected-timing-shot",
    "selected-score-shot",
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
    } else if (id === "media-badge" || id === "current-file") {
      element.textContent = "No video selected";
    } else if (id === "timing-summary") {
      element.textContent = "No timing data.";
    } else if (id === "selected-shot-copy") {
      element.textContent = "No shot selected.";
    } else if (id === "selected-timing-shot" || id === "selected-score-shot") {
      element.textContent = "No shot selected";
    } else if (id === "scoring-result") {
      element.textContent = "--";
    } else if (id === "status" || id === "processing-message") {
      element.textContent = "Ready.";
    } else if (id === "processing-detail") {
      element.textContent = "Local processing";
    }
  });
  ["primary-file-path", "project-path", "export-path"].forEach((id) => {
    const element = $(id);
    if (element) element.value = "";
  });
  const mergeMediaInput = $("merge-media-input");
  if (mergeMediaInput) mergeMediaInput.value = "";
  const mergeMediaList = $("merge-media-list");
  if (mergeMediaList) mergeMediaList.innerHTML = "";
  const mergeMediaSummary = $("merge-media-summary");
  if (mergeMediaSummary) mergeMediaSummary.textContent = "Add as many videos or images as you want. Multiple items export as a grid.";
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
  const shots = state?.project?.analysis?.shots || [];
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
  $("primary-file-path").value = state.project.primary_video.path || "";
  $("project-path").placeholder = `${state.default_project_path || "~/splitshot"}/project.ssproj`;
  $("project-path").value = state.project.path || "";
  $("media-badge").textContent = state.media.primary_available
    ? `Primary: ${primaryName}${mergeCount > 0 ? ` • ${mergeCount} merge item${mergeCount === 1 ? "" : "s"}` : ""}`
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

function renderVideo() {
  const video = $("primary-video");
  const secondary = $("secondary-video");
  const secondaryImage = $("secondary-image");
  const stage = $("video-stage");
  const merge = state.project.merge;
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
  const mergePreview = Boolean(state.media.secondary_available && merge.enabled);
  const showSecondaryVideo = mergePreview && !imageSecondary;
  const showSecondaryImage = mergePreview && imageSecondary;
  secondary.hidden = !showSecondaryVideo;
  secondary.style.display = showSecondaryVideo ? "" : "none";
  secondaryImage.hidden = !showSecondaryImage;
  secondaryImage.style.display = showSecondaryImage ? "block" : "none";
  stage.classList.toggle("merge-preview", mergePreview);
  stage.classList.toggle("merge-side-by-side", mergePreview && merge.layout === "side_by_side");
  stage.classList.toggle("merge-above-below", mergePreview && merge.layout === "above_below");
  stage.classList.toggle("merge-pip", mergePreview && merge.layout === "pip");
  const pipSizeValue = Number(
    merge.pip_size_percent
      ?? Number(String(merge.pip_size || "35%").replace(/%$/, ""))
      ?? 35,
  );
  stage.style.setProperty("--pip-size", `${pipSizeValue}%`);
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
  if (mergePreview && merge.layout === "pip") {
    const activeSecondary = imageSecondary ? secondaryImage : secondary;
    const frameRect = videoContentRect(video, stage);
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
    if (frameRect) {
      let insetWidth = Math.max(1, Math.round(frameRect.width * (pipSizeValue / 100)));
      let insetHeight = Math.max(1, Math.round((secondaryHeight / secondaryWidth) * insetWidth));
      if (insetHeight > frameRect.height) {
        const fitScale = frameRect.height / insetHeight;
        insetWidth = Math.max(1, Math.round(insetWidth * fitScale));
        insetHeight = Math.max(1, Math.round(insetHeight * fitScale));
      }
      const travelX = Math.max(0, frameRect.width - insetWidth);
      const travelY = Math.max(0, frameRect.height - insetHeight);
      activeSecondary.style.left = `${frameRect.left + (travelX * (normalizedCoordinateValue(merge.pip_x) ?? 1))}px`;
      activeSecondary.style.top = `${frameRect.top + (travelY * (normalizedCoordinateValue(merge.pip_y) ?? 1))}px`;
      activeSecondary.style.width = `${insetWidth}px`;
      activeSecondary.style.height = `${insetHeight}px`;
      activeSecondary.style.maxWidth = `${insetWidth}px`;
      activeSecondary.style.maxHeight = `${insetHeight}px`;
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
  syncSecondaryPreview();
}

function syncSecondaryPreview() {
  const primary = $("primary-video");
  const secondary = $("secondary-video");
  if (!state?.media?.secondary_available || !state.project.merge.enabled || !secondary.src) return;
  const target = Math.max(0, primary.currentTime + ((state.project.analysis.sync_offset_ms || 0) / 1000));
  if (Number.isFinite(target) && Math.abs((secondary.currentTime || 0) - target) > 0.08) {
    try {
      secondary.currentTime = target;
    } catch {
      // Some browsers reject seeks before metadata is ready.
    }
  }
  if (primary.paused && !secondary.paused) {
    secondary.pause();
  } else if (!primary.paused && secondary.paused) {
    secondary.play().catch(() => {});
  }
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
    syncSecondaryPreview();
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
    item.className = segment.shot_id === selectedShotId ? "selected" : "";
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

    const kind = document.createElement("strong");
    kind.textContent = event.label || event.kind;

    const after = document.createElement("span");
    after.textContent = event.after_shot_id ? `After ${shotLabelForEvent(event.after_shot_id)}` : "After any shot";

    const before = document.createElement("span");
    before.textContent = event.before_shot_id ? `Before ${shotLabelForEvent(event.before_shot_id)}` : "Before any shot";

    const note = document.createElement("span");
    note.textContent = event.note || event.kind;

    row.append(kind, after, before, note);
    list.appendChild(row);
  });
}

function renderTimingEventEditor() {
  const shotSegments = state.timing_segments || [];
  const afterSelect = $("timing-event-after");
  const beforeSelect = $("timing-event-before");
  const addButton = $("add-timing-event");
  if (!afterSelect || !beforeSelect || !addButton) return;

  const previousAfter = afterSelect.value;
  const previousBefore = beforeSelect.value;
  const selectedIndex = selectedShotId
    ? shotSegments.findIndex((segment) => segment.shot_id === selectedShotId)
    : -1;

  afterSelect.innerHTML = "";
  beforeSelect.innerHTML = "";

  const afterBlank = document.createElement("option");
  afterBlank.value = "";
  afterBlank.textContent = "After any shot";
  afterSelect.appendChild(afterBlank);

  const beforeBlank = document.createElement("option");
  beforeBlank.value = "";
  beforeBlank.textContent = "Before any shot";
  beforeSelect.appendChild(beforeBlank);

  shotSegments.forEach((segment) => {
    const afterOption = document.createElement("option");
    afterOption.value = segment.shot_id;
    afterOption.textContent = `${segment.label} ${segment.absolute_s}s`;
    afterSelect.appendChild(afterOption);

    const beforeOption = document.createElement("option");
    beforeOption.value = segment.shot_id;
    beforeOption.textContent = `${segment.label} ${segment.absolute_s}s`;
    beforeSelect.appendChild(beforeOption);
  });

  if (previousAfter && shotSegments.some((segment) => segment.shot_id === previousAfter)) {
    afterSelect.value = previousAfter;
  } else if (selectedIndex >= 0) {
    afterSelect.value = shotSegments[selectedIndex].shot_id;
  }

  if (previousBefore && shotSegments.some((segment) => segment.shot_id === previousBefore)) {
    beforeSelect.value = previousBefore;
  } else if (selectedIndex >= 0) {
    beforeSelect.value = shotSegments[selectedIndex + 1]?.shot_id || "";
  }

  addButton.disabled = shotSegments.length === 0;
  renderTimingEventList();
}

function addTimingEvent() {
  const kind = $("timing-event-kind").value;
  const afterShotId = $("timing-event-after").value || selectedShotId || "";
  const beforeShotId = $("timing-event-before").value;
  activity("timing.event.add", { kind, after_shot_id: afterShotId, before_shot_id: beforeShotId });
  callApi("/api/events/add", {
    kind,
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

function updateTimingRowField(shotId, field, value) {
  if (field === "score_letter") {
    if (value) {
      callApi("/api/scoring/score", { shot_id: shotId, letter: value });
    }
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

  const scoreOptions = state.scoring_summary?.score_options || ["A", "C", "D", "M", "NS", "M+NS"];
  (state.split_rows || []).forEach((row) => {
    const editing = expandedTable && timingRowEdits.has(row.shot_id);
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
    if (row.shot_id === selectedShotId) shotCell.className = "selected";
    shotCell.addEventListener("click", () => selectShot(row.shot_id));
    table.appendChild(shotCell);

    const splitCell = document.createElement("div");
    splitCell.textContent = row.split_ms === null ? "--.--s" : `${seconds(row.split_ms)}s`;
    table.appendChild(splitCell);

    const scoreCell = document.createElement("div");
    if (editing) {
      const select = document.createElement("select");
      scoreOptions.forEach((letter) => {
        const option = document.createElement("option");
        option.value = letter;
        option.textContent = letter;
        select.appendChild(option);
      });
      select.value = row.score_letter || scoreOptions[0];
      select.addEventListener("change", () => updateTimingRowField(row.shot_id, "score_letter", select.value));
      scoreCell.appendChild(select);
    } else {
      scoreCell.textContent = row.score_letter || "--";
      scoreCell.addEventListener("click", () => selectShot(row.shot_id));
    }
    table.appendChild(scoreCell);

    const confidenceCell = document.createElement("div");
    confidenceCell.textContent = row.confidence === null || row.confidence === undefined
      ? "Manual"
      : Number(row.confidence).toFixed(2);
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
  const selectedLabel = segment ? segment.label : "No shot selected";
  $("selected-shot-copy").textContent = segment
    ? `${segment.label}: ${segment.segment_s || "--.--"}s split, ${segment.cumulative_s || "--.--"}s from beep.`
    : "No shot selected.";
  $("selected-timing-shot").textContent = selectedLabel;
  $("selected-score-shot").textContent = selectedLabel;
  if (segment?.score_letter && Array.from($("score-letter").options).some((option) => option.value === segment.score_letter)) {
    $("score-letter").value = segment.score_letter;
  }
}

function renderScoreOptions(summary) {
  const selected = $("score-letter").value;
  const options = summary.score_options || ["A", "C", "D", "M", "NS", "M+NS"];
  $("score-letter").innerHTML = "";
  options.forEach((letter) => {
    const option = document.createElement("option");
    option.value = letter;
    option.textContent = letter;
    $("score-letter").appendChild(option);
  });
  $("score-letter").value = options.includes(selected) ? selected : options[0];

  const grid = $("score-option-grid");
  grid.innerHTML = "";
  options.forEach((letter) => {
    const value = summary.score_values?.[letter] ?? 0;
    const penalty = summary.score_penalties?.[letter] ?? 0;
    const item = document.createElement("span");
    item.textContent = penalty ? `${letter}: ${value} / -${penalty}` : `${letter}: ${value}`;
    grid.appendChild(item);
  });
}

function renderScoringShotList() {
  const list = $("scoring-shot-list");
  if (!list) return;
  list.innerHTML = "";
  const scoreOptions = state.scoring_summary?.score_options || ["A", "C", "D", "M", "NS", "M+NS"];
  (state.timing_segments || []).forEach((segment) => {
    const row = document.createElement("div");
    row.className = `scoring-shot-row ${segment.shot_id === selectedShotId ? "selected" : ""}`;
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = `${segment.label} | ${segment.cumulative_s}s`;
    button.addEventListener("click", () => selectShot(segment.shot_id));
    const select = document.createElement("select");
    select.setAttribute("aria-label", `Score ${segment.label}`);
    scoreOptions.forEach((letter) => {
      const option = document.createElement("option");
      option.value = letter;
      const value = state.scoring_summary?.score_values?.[letter] ?? 0;
      const penalty = state.scoring_summary?.score_penalties?.[letter] ?? 0;
      option.textContent = penalty ? `${letter} (${value}, -${penalty})` : `${letter} (${value})`;
      select.appendChild(option);
    });
    select.value = segment.score_letter || scoreOptions[0];
    select.addEventListener("change", () => {
      selectedShotId = segment.shot_id;
      callApi("/api/scoring/score", { shot_id: segment.shot_id, letter: select.value });
    });
    row.appendChild(button);
    row.appendChild(select);
    list.appendChild(row);
  });
}

function renderScoringPenaltyFields(summary) {
  const grid = $("scoring-penalty-grid");
  grid.innerHTML = "";
  const manual = document.createElement("label");
  manual.textContent = `${summary.penalty_label || "Manual penalties"} `;
  const manualInput = document.createElement("input");
  manualInput.id = "penalties";
  manualInput.type = "number";
  manualInput.value = state.project.scoring.penalties;
  manualInput.min = "0";
  manualInput.step = summary.mode === "hit_factor" ? "1" : "0.5";
  manualInput.dataset.penaltyManual = "true";
  manual.appendChild(manualInput);
  grid.appendChild(manual);

  (summary.penalty_fields || []).forEach((field) => {
    const label = document.createElement("label");
    label.textContent = `${field.label} `;
    const input = document.createElement("input");
    input.className = "penalty-input";
    input.type = "number";
    input.min = "0";
    input.step = "1";
    input.value = field.count ?? 0;
    input.dataset.penaltyId = field.id;
    input.title = `${field.description || ""} ${field.value} ${field.unit}`.trim();
    label.appendChild(input);
    grid.appendChild(label);
  });
}

function renderScoringPresetOptions() {
  const select = $("scoring-preset");
  const selected = state.project.scoring.ruleset;
  const previousLength = select.options.length;
  select.innerHTML = "";
  (state.scoring_presets || []).forEach((preset) => {
    const option = document.createElement("option");
    option.value = preset.id;
    option.textContent = preset.name;
    select.appendChild(option);
  });
  select.value = selected;
  const preset = (state.scoring_presets || []).find((item) => item.id === selected);
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
  $("threshold").value = state.project.analysis.detection_threshold;
    $("sync-offset").textContent = `${state.project.analysis.sync_offset_ms || 0} ms`;
  $("project-name").value = state.project.name || "Untitled Project";
  $("project-description").value = state.project.description || "";
  $("merge-enabled").checked = state.project.merge.enabled;
  $("merge-layout").value = state.project.merge.layout;
  const pipValue = Number(
    state.project.merge.pip_size_percent
      ?? Number(String(state.project.merge.pip_size || "35%").replace(/%$/, ""))
      ?? 35,
  );
  $("pip-size").value = pipValue;
  $("pip-size-label").textContent = `${pipValue}%`;
  $("pip-x").value = state.project.merge.pip_x ?? 1;
  $("pip-y").value = state.project.merge.pip_y ?? 1;
  $("badge-size").value = state.project.overlay.badge_size;
  overlayStyleMode = state.project.overlay.style_type || overlayStyleMode;
  overlaySpacing = Number(state.project.overlay.spacing ?? overlaySpacing);
  overlayMargin = Number(state.project.overlay.margin ?? overlayMargin);
  $("overlay-style").value = overlayStyleMode;
  $("overlay-spacing").value = overlaySpacing;
  $("overlay-margin").value = overlayMargin;
  $("max-visible-shots").value = state.project.overlay.max_visible_shots;
  $("shot-quadrant").value = state.project.overlay.shot_quadrant;
  $("shot-direction").value = state.project.overlay.shot_direction;
  $("overlay-custom-x").value = state.project.overlay.custom_x ?? "";
  $("overlay-custom-y").value = state.project.overlay.custom_y ?? "";
  $("bubble-width").value = state.project.overlay.bubble_width;
  $("bubble-height").value = state.project.overlay.bubble_height;
  $("overlay-font-family").value = state.project.overlay.font_family;
  $("overlay-font-size").value = state.project.overlay.font_size;
  $("overlay-font-bold").checked = state.project.overlay.font_bold;
  $("overlay-font-italic").checked = state.project.overlay.font_italic;
  $("show-timer").checked = state.project.overlay.show_timer;
  $("show-draw").checked = state.project.overlay.show_draw;
  $("show-shots").checked = state.project.overlay.show_shots;
  $("show-score").checked = state.project.overlay.show_score;
  $("custom-box-enabled").checked = state.project.overlay.custom_box_enabled;
  $("custom-box-text").value = state.project.overlay.custom_box_text || "";
  $("custom-box-quadrant").value = state.project.overlay.custom_box_quadrant;
  $("custom-box-x").value = state.project.overlay.custom_box_x ?? "";
  $("custom-box-y").value = state.project.overlay.custom_box_y ?? "";
  $("custom-box-width").value = state.project.overlay.custom_box_width || 0;
  $("custom-box-height").value = state.project.overlay.custom_box_height || 0;
  $("custom-box-opacity").value = state.project.overlay.custom_box_opacity ?? 0.9;
  $("custom-box-background-color").value = state.project.overlay.custom_box_background_color || "#000000";
  $("custom-box-text-color").value = state.project.overlay.custom_box_text_color || "#ffffff";
  syncOverlayCoordinateControlState();
  $("scoring-enabled").checked = state.project.scoring.enabled;
  $("quality").value = state.project.export.quality;
  $("aspect-ratio").value = state.project.export.aspect_ratio;
  $("crop-center-x").value = state.project.export.crop_center_x;
  $("crop-center-y").value = state.project.export.crop_center_y;
  $("target-width").value = state.project.export.target_width ?? "";
  $("target-height").value = state.project.export.target_height ?? "";
  $("frame-rate").value = state.project.export.frame_rate;
  $("video-codec").value = state.project.export.video_codec;
  $("video-bitrate").value = state.project.export.video_bitrate_mbps;
  $("audio-codec").value = state.project.export.audio_codec;
  $("audio-sample-rate").value = state.project.export.audio_sample_rate;
  $("audio-bitrate").value = state.project.export.audio_bitrate_kbps;
  $("color-space").value = state.project.export.color_space;
  $("two-pass").checked = state.project.export.two_pass;
  $("ffmpeg-preset").value = state.project.export.ffmpeg_preset;
  syncExportPathControl();
  renderScoringPresetOptions();
  renderExportPresetOptions();
  renderExportLog();
  renderStyleControls();
  renderMergeMediaList();
}

function renderStyleControls() {
  const grid = $("badge-style-grid");
  grid.innerHTML = "";
  badgeControls.forEach(([key, title]) => {
    const style = state.project.overlay[key];
    const card = document.createElement("section");
    card.className = "style-card";
    card.dataset.badge = key;
    card.innerHTML = `
      <h4>${title}</h4>
      <label>Background <input type="color" data-field="background_color" value="${style.background_color}" /></label>
      <label>Text <input type="color" data-field="text_color" value="${style.text_color}" /></label>
      <label>Opacity <input type="range" data-field="opacity" min="0" max="1" step="0.05" value="${style.opacity}" /></label>
    `;
    grid.appendChild(card);
  });

  const scoreGrid = $("score-color-grid");
  scoreGrid.innerHTML = "";
  const scoreKeys = [
    ...(state.scoring_summary?.score_options || []),
    ...Object.keys(state.project.overlay.scoring_colors || {}),
  ];
  [...new Set(scoreKeys)].forEach((letter) => {
    const label = document.createElement("label");
    label.textContent = `${letter} `;
    const input = document.createElement("input");
    input.type = "color";
    input.className = "score-color-input";
    input.dataset.letter = letter;
    input.value = state.project.overlay.scoring_colors[letter] || "#ffffff";
    label.appendChild(input);
    scoreGrid.appendChild(label);
  });
}

function renderMergeMediaList() {
  const list = $("merge-media-list");
  const summary = $("merge-media-summary");
  if (!list || !summary) return;
  const mergeSources = state?.project?.merge_sources || [];
  const multiSource = mergeSources.length > 1;
  summary.textContent = mergeSources.length > 0
    ? `${mergeSources.length} merge item${mergeSources.length === 1 ? "" : "s"} loaded. Multiple items export as a grid.`
    : "Add as many videos or images as you want. Multiple items export as a grid.";
  const mergeLayout = $("merge-layout");
  if (mergeLayout) mergeLayout.disabled = multiSource;
  const pipSize = $("pip-size");
  if (pipSize) pipSize.disabled = multiSource;
  const pipX = $("pip-x");
  if (pipX) pipX.disabled = multiSource;
  const pipY = $("pip-y");
  if (pipY) pipY.disabled = multiSource;
  list.innerHTML = "";
  if (mergeSources.length === 0) {
    const empty = document.createElement("div");
    empty.className = "hint";
    empty.textContent = "No merge media added yet.";
    list.appendChild(empty);
    return;
  }

  mergeSources.forEach((source, index) => {
    const asset = source.asset || source;
    const card = document.createElement("div");
    card.className = "merge-media-card";
    const info = document.createElement("div");
    const title = document.createElement("strong");
    title.textContent = `${index + 1}. ${fileName(asset.path || "")}`;
    const meta = document.createElement("small");
    const mediaType = asset.is_still_image ? "Image" : "Video";
    const dimensions = asset.width && asset.height ? ` • ${asset.width}x${asset.height}` : "";
    meta.textContent = `${mediaType}${dimensions}`;
    info.append(title, meta);

    const remove = document.createElement("button");
    remove.type = "button";
    remove.textContent = "Remove";
    remove.dataset.mergeSourceRemove = source.id || asset.id || String(index);
    remove.addEventListener("click", () => {
      activity("merge.media.remove", { source_id: remove.dataset.mergeSourceRemove });
      callApi("/api/merge/remove", { source_id: remove.dataset.mergeSourceRemove });
    });

    card.append(info, remove);
    list.appendChild(card);
  });
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
  badge.style.display = "flex";
  badge.style.alignItems = "center";
  badge.style.justifyContent = textBias === "left" ? "flex-start" : textBias === "right" ? "flex-end" : "center";
  badge.style.textAlign = textBias;
  badge.style.overflow = "hidden";
  badge.style.padding = `${overlaySpacing}px ${Math.max(8, overlaySpacing * 1.5)}px`;
  badge.style.margin = `${overlayMargin}px`;
  if (widthOverride > 0) badge.style.width = `${widthOverride}px`;
  else if (state.project.overlay.bubble_width > 0) badge.style.width = `${state.project.overlay.bubble_width}px`;
  if (heightOverride > 0) badge.style.height = `${heightOverride}px`;
  else if (state.project.overlay.bubble_height > 0) badge.style.height = `${state.project.overlay.bubble_height}px`;
  badge.style.fontFamily = state.project.overlay.font_family || "Helvetica Neue";
  badge.style.fontSize = `${state.project.overlay.font_size || 14}px`;
  badge.style.fontWeight = state.project.overlay.font_bold ? "950" : "700";
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

function positionOverlayContainer(overlay, quadrantValue = null, frameRect = null, customPoint = null) {
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
  overlay.style.maxWidth = "calc(100% - 12px)";
  overlay.style.maxHeight = "calc(100% - 12px)";
  overlay.style.overflow = "hidden";
  overlay.style.flexDirection = ["left", "right"].includes(direction) ? "row" : "column";
  if (direction === "left") overlay.style.flexDirection = "row-reverse";
  if (direction === "up") overlay.style.flexDirection = "column-reverse";

  if (quadrant === CUSTOM_QUADRANT_VALUE) {
    const x = normalizedCoordinateValue(customPoint?.x) ?? 0.5;
    const y = normalizedCoordinateValue(customPoint?.y) ?? 0.5;
    if (frameRect) {
      overlay.style.left = `${frameRect.left + (x * frameRect.width)}px`;
      overlay.style.top = `${frameRect.top + (y * frameRect.height)}px`;
    }
    overlay.style.justifyContent = "center";
    overlay.style.alignItems = "center";
    overlay.style.transform = "translate(-50%, -50%)";
    return;
  }

  if (frameRect) {
    overlay.style.left = `${frameRect.left}px`;
    overlay.style.top = `${frameRect.top}px`;
    overlay.style.width = `${frameRect.width}px`;
    overlay.style.height = `${frameRect.height}px`;
  }

  const [vertical, horizontal] = quadrant.split("_");
  const rowLayout = ["left", "right"].includes(direction);
  const primaryAxis = rowLayout ? horizontal : vertical;
  const crossAxis = rowLayout ? vertical : horizontal;
  overlay.style.justifyContent = alignToEdge(primaryAxis);
  overlay.style.alignItems = alignToEdge(crossAxis);
}

function positionCustomBadge(badge, frameRect) {
  const customX = state.project.overlay.custom_box_x;
  const customY = state.project.overlay.custom_box_y;
  if (customX === null || customX === undefined || customX === "" || customY === null || customY === undefined || customY === "") {
    return;
  }
  badge.style.position = "absolute";
  badge.style.margin = "0";
  badge.style.left = `${clamp(Number(customX) * frameRect.width, 0, frameRect.width)}px`;
  badge.style.top = `${clamp(Number(customY) * frameRect.height, 0, frameRect.height)}px`;
  badge.style.transform = "translate(-50%, -50%)";
}

let customOverlayDrag = null;

function beginCustomOverlayDrag(event) {
  const customOverlay = $("custom-overlay");
  if (event.button !== 0 || !customOverlay || !customOverlay.classList.contains("has-badge") || !state.project.overlay.custom_box_enabled || !state.project.overlay.custom_box_text) return;
  event.preventDefault();
  const stage = $("video-stage");
  const frameRect = videoContentRect($("primary-video"), stage) || stage.getBoundingClientRect();
  const badgeRect = customOverlay.firstElementChild?.getBoundingClientRect() || customOverlay.getBoundingClientRect();
  const startX = clamp((badgeRect.left - frameRect.left + badgeRect.width / 2) / frameRect.width, 0, 1);
  const startY = clamp((badgeRect.top - frameRect.top + badgeRect.height / 2) / frameRect.height, 0, 1);
  customOverlayDrag = {
    startClientX: event.clientX,
    startClientY: event.clientY,
    startX,
    startY,
    frameRect,
  };
  capturePointer(customOverlay, event.pointerId);
  customOverlay.classList.add("dragging");
}

function moveCustomOverlayDrag(event) {
  if (!customOverlayDrag) return;
  const { startClientX, startClientY, startX, startY, frameRect } = customOverlayDrag;
  const deltaX = (event.clientX - startClientX) / frameRect.width;
  const deltaY = (event.clientY - startClientY) / frameRect.height;
  const newX = clamp(startX + deltaX, 0, 1);
  const newY = clamp(startY + deltaY, 0, 1);
  $("custom-box-x").value = newX.toFixed(3);
  $("custom-box-y").value = newY.toFixed(3);
  $("custom-box-quadrant").value = "middle_middle";
  syncOverlayPreviewStateFromControls();
  renderLiveOverlay();
  autoApplyOverlay();
}

function endCustomOverlayDrag(event) {
  if (!customOverlayDrag) return;
  const customOverlay = $("custom-overlay");
  releasePointer(customOverlay, event.pointerId);
  customOverlay?.classList.remove("dragging");
  customOverlayDrag = null;
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
  const frameRect = videoContentRect($("primary-video"), stage) || stage.getBoundingClientRect();
  positionOverlayContainer(overlay, state.project.overlay.shot_quadrant, frameRect, {
    x: state.project.overlay.custom_x,
    y: state.project.overlay.custom_y,
  });
  positionOverlayContainer(customOverlay, state.project.overlay.custom_box_quadrant, frameRect);

  const video = $("primary-video");
  const positionMs = Math.round((video.currentTime || 0) * 1000);
  const beep = state.project.analysis.beep_time_ms_primary;
  let elapsed = beep === null || beep === undefined ? positionMs : Math.max(0, positionMs - beep);
  const shots = state.project.analysis.shots || [];
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
  if (state.project.overlay.show_timer) {
    overlay.appendChild(badgeElement(`Timer ${seconds(elapsed)}`, state.project.overlay.timer_badge, size, null, null, null, "center"));
  }
  if (
    state.project.overlay.show_draw
    && firstShotTime !== null
    && positionMs < firstShotTime
    && state.metrics.draw_ms !== null
    && state.metrics.draw_ms !== undefined
  ) {
    overlay.appendChild(badgeElement(`Draw ${seconds(state.metrics.draw_ms)}`, state.project.overlay.shot_badge, size, null, null, null, "center"));
  }

  const currentIndex = currentShotIndex(positionMs);
  if (state.project.overlay.show_shots && currentIndex >= 0) {
    const maxVisible = Math.max(1, Number(state.project.overlay.max_visible_shots || 4));
    const start = Math.max(0, currentIndex - maxVisible + 1);
    for (let index = start; index <= currentIndex; index += 1) {
      const shot = shots[index];
      if (!shot) continue;
      const splitMs = index === 0
        ? shot.time_ms - (beep || 0)
        : shot.time_ms - shots[index - 1].time_ms;
      const style = index === currentIndex
        ? state.project.overlay.current_shot_badge
        : state.project.overlay.shot_badge;
      const scoreText = state.project.scoring.enabled && shot.score ? ` ${shot.score.letter}` : "";
      const scoreColor = state.project.scoring.enabled && shot.score
        ? state.project.overlay.scoring_colors[shot.score.letter]
        : null;
      overlay.appendChild(badgeElement(`Shot ${index + 1} ${splitSeconds(splitMs)}${scoreText}`, style, size, scoreColor, null, null, shotTextBias));
    }
  }

  const summary = state.scoring_summary || {};
  if (finalShotReached && state.project.scoring.enabled && state.project.overlay.show_score && summary.display_value && summary.display_value !== "--") {
    overlay.appendChild(
      badgeElement(`${summary.display_label} ${summary.display_value}`, state.project.overlay.hit_factor_badge, size),
    );
  }

  if (state.project.overlay.custom_box_enabled && state.project.overlay.custom_box_text) {
    const customBoxStyle = {
      background_color: state.project.overlay.custom_box_background_color || state.project.overlay.hit_factor_badge.background_color,
      text_color: state.project.overlay.custom_box_text_color || state.project.overlay.hit_factor_badge.text_color,
      opacity: state.project.overlay.custom_box_opacity ?? state.project.overlay.hit_factor_badge.opacity,
    };
    const customBadge = badgeElement(
      state.project.overlay.custom_box_text,
      customBoxStyle,
      size,
      null,
      state.project.overlay.custom_box_width,
      state.project.overlay.custom_box_height,
      "center",
    );
    positionCustomBadge(customBadge, frameRect);
    customOverlay.appendChild(customBadge);
    customOverlay.classList.add("has-badge");
  }
}

function startOverlayLoop() {
  if (overlayFrame !== null) return;
  activity("video.play", { current_time_s: $("primary-video").currentTime });
  syncSecondaryPreview();
  const tick = () => {
    syncSecondaryPreview();
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
  syncSecondaryPreview();
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
    const badge = card.dataset.badge;
    styles[badge] = {};
    card.querySelectorAll("input").forEach((input) => {
      const value = input.type === "range" ? Number(input.value) : input.value;
      styles[badge][input.dataset.field] = value;
    });
  });
  const scoringColors = {};
  document.querySelectorAll(".score-color-input").forEach((input) => {
    scoringColors[input.dataset.letter] = input.value;
  });
  return {
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
    custom_box_text: $("custom-box-text").value,
    custom_box_quadrant: $("custom-box-quadrant").value,
    custom_box_x: $("custom-box-x").value,
    custom_box_y: $("custom-box-y").value,
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

async function postFiles(path, files) {
  const selectedFiles = Array.from(files || []);
  let lastResult = null;
  for (const file of selectedFiles) {
    lastResult = await postFile(path, file);
  }
  return lastResult;
}

function readMergePayload() {
  const pipValue = Number($("pip-size").value);
  return {
    enabled: $("merge-enabled").checked,
    layout: $("merge-layout").value,
    pip_size_percent: Number.isFinite(pipValue) ? pipValue : 35,
    pip_x: normalizedCoordinateValue($("pip-x").value) ?? 1,
    pip_y: normalizedCoordinateValue($("pip-y").value) ?? 1,
  };
}

function readLayoutPayload() {
  return {
    quality: $("quality").value,
    aspect_ratio: $("aspect-ratio").value,
    crop_center_x: Number($("crop-center-x").value),
    crop_center_y: Number($("crop-center-y").value),
  };
}

function readScoringPayload() {
  const penaltyCounts = {};
  document.querySelectorAll(".penalty-input").forEach((input) => {
    penaltyCounts[input.dataset.penaltyId] = Number(input.value || 0);
  });
  return {
    enabled: $("scoring-enabled").checked,
    penalties: Number($("penalties")?.value || 0),
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

async function importTypedPath(targetId, apiPath, label) {
  const path = $(targetId).value.trim();
  if (!path) {
    setStatus(`${label} video path is required.`);
    return null;
  }
  return callApi(apiPath, { path });
}

async function openProjectWithDialog() {
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

async function applyScoringSettings() {
  const scoringPayload = readScoringPayload();
  const ruleset = $("scoring-preset").value;
  const previousRuleset = state.project.scoring.ruleset;
  if (ruleset !== previousRuleset) scoringPayload.penalty_counts = {};
  await callApi("/api/scoring/profile", { ruleset });
  await callApi("/api/scoring", scoringPayload);
}

function assignSelectedScore() {
  if (!selectedShotId) {
    activity("score.assign.skipped", { reason: "no_selected_shot" });
    return;
  }
  callApi("/api/scoring/score", { shot_id: selectedShotId, letter: $("score-letter").value });
}

const autoApplyThreshold = debounce(() => {
  activity("auto_apply.threshold", { threshold: Number($("threshold").value) });
  callApi("/api/analysis/threshold", { threshold: Number($("threshold").value) });
}, 450);

const autoApplyProjectDetails = debounce(() => {
  activity("auto_apply.project_details", {});
  callApi("/api/project/details", readProjectDetailsPayload());
}, 300);

const autoApplyOverlay = debounce(() => {
  activity("auto_apply.overlay", {});
  callApi("/api/overlay", readOverlayPayload());
}, 300);

const autoApplyMerge = debounce(() => {
  activity("auto_apply.merge", {});
  callApi("/api/merge", readMergePayload());
}, 300);

const autoApplyLayout = debounce(() => {
  activity("auto_apply.layout", {});
  callApi("/api/layout", readLayoutPayload());
}, 300);

const autoApplyExportSettings = debounce(() => {
  activity("auto_apply.export_settings", {});
  callApi("/api/export/settings", readExportSettingsPayload());
}, 300);

const autoApplyScoring = debounce(() => {
  activity("auto_apply.scoring", {});
  applyScoringSettings();
}, 300);

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
  $("browse-project-path").addEventListener("click", () => pickPath("project_save", "project-path"));
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
    item.addEventListener("click", () => $("merge-media-input")?.click());
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
  $("save-project").addEventListener("click", saveProjectFlow);
  $("open-project").addEventListener("click", openProjectWithDialog);
  $("delete-project").addEventListener("click", () => callApi("/api/project/delete", {}));
  ["project-name", "project-description"].forEach((id) => {
    $(id).addEventListener("input", autoApplyProjectDetails);
  });
  ["loadedmetadata", "loadeddata"].forEach((eventName) => {
    $("primary-video").addEventListener(eventName, () => {
      syncSecondaryPreview();
      renderLiveOverlay();
    });
    $("secondary-video").addEventListener(eventName, () => {
      syncSecondaryPreview();
      renderLiveOverlay();
    });
  });
  $("primary-video").addEventListener("play", startOverlayLoop);
  $("primary-video").addEventListener("pause", stopOverlayLoop);
  $("primary-video").addEventListener("seeked", () => {
    activity("video.seeked", { current_time_s: $("primary-video").currentTime });
    syncSecondaryPreview();
    renderLiveOverlay();
  });
  $("primary-video").addEventListener("timeupdate", () => {
    syncSecondaryPreview();
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
  $("threshold").addEventListener("input", autoApplyThreshold);
  ["merge-enabled", "merge-layout"].forEach((id) => {
    $(id).addEventListener("change", () => {
      syncMergePreviewStateFromControls();
      renderVideo();
      autoApplyMerge();
    });
  });
  $("pip-size").addEventListener("input", () => {
    $("pip-size-label").textContent = `${$("pip-size").value}%`;
    syncMergePreviewStateFromControls();
    renderVideo();
    autoApplyMerge();
  });
  ["pip-x", "pip-y"].forEach((id) => {
    $(id).addEventListener("input", () => {
      syncMergePreviewStateFromControls();
      renderVideo();
      autoApplyMerge();
    });
  });
  document.querySelectorAll("[data-sync]").forEach((button) => {
    button.addEventListener("click", () => callApi("/api/sync", { delta_ms: Number(button.dataset.sync) }));
  });
  $("swap-videos").addEventListener("click", () => callApi("/api/swap", {}));
  $("add-timing-event").addEventListener("click", addTimingEvent);
  $("custom-overlay").addEventListener("pointerdown", beginCustomOverlayDrag);
  ["badge-size"].forEach((id) => {
    $(id).addEventListener("change", () => {
      syncOverlayFontSizePreset();
      syncOverlayPreviewStateFromControls();
      renderLiveOverlay();
      autoApplyOverlay();
    });
  });
  [
    "max-visible-shots",
    "shot-quadrant",
    "shot-direction",
    "overlay-custom-x",
    "overlay-custom-y",
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
    "custom-box-text",
    "custom-box-quadrant",
    "custom-box-x",
    "custom-box-y",
    "custom-box-width",
    "custom-box-height",
    "custom-box-opacity",
    "custom-box-background-color",
    "custom-box-text-color",
  ].forEach((id) => {
    const eventName = $(id).tagName === "SELECT" || $(id).type === "checkbox" ? "change" : "input";
    $(id).addEventListener(eventName, () => {
      if (id === "shot-quadrant") {
        syncOverlayCoordinateControlState();
        ensureShotQuadrantDefaults();
      }
      syncOverlayPreviewStateFromControls();
      renderLiveOverlay();
      autoApplyOverlay();
    });
  });
  $("badge-style-grid").addEventListener("input", (event) => {
    syncOverlayPreviewStateFromControls();
    renderLiveOverlay();
    const target = event.target;
    if (target instanceof HTMLInputElement && target.type === "color") return;
    autoApplyOverlay();
  });
  $("badge-style-grid").addEventListener("change", () => {
    syncOverlayPreviewStateFromControls();
    renderLiveOverlay();
    autoApplyOverlay();
  });
  $("score-color-grid").addEventListener("input", () => {
    syncOverlayPreviewStateFromControls();
    renderLiveOverlay();
  });
  $("score-color-grid").addEventListener("change", () => {
    syncOverlayPreviewStateFromControls();
    renderLiveOverlay();
    autoApplyOverlay();
  });
  ["scoring-enabled", "scoring-preset"].forEach((id) => {
    $(id).addEventListener("change", autoApplyScoring);
  });
  $("scoring-penalty-grid").addEventListener("input", autoApplyScoring);
  $("score-letter").addEventListener("change", () => {
    assignSelectedScore();
  });
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
  document.addEventListener("pointermove", moveCustomOverlayDrag);
  document.addEventListener("pointerup", endCustomOverlayDrag);
  document.addEventListener("pointercancel", endCustomOverlayDrag);
  ["overlay-style"].forEach((id) => {
    $(id).addEventListener("change", () => {
      overlayStyleMode = $(id).value;
      syncOverlayPreviewStateFromControls();
      renderLiveOverlay();
      autoApplyOverlay();
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
      autoApplyOverlay();
    });
  });
  ["quality", "aspect-ratio"].forEach((id) => {
    $(id).addEventListener("change", autoApplyLayout);
  });
  ["crop-center-x", "crop-center-y"].forEach((id) => {
    $(id).addEventListener("input", autoApplyLayout);
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
    $(id).addEventListener("input", autoApplyExportSettings);
  });
  [
    "frame-rate",
    "video-codec",
    "audio-codec",
    "color-space",
    "ffmpeg-preset",
    "two-pass",
  ].forEach((id) => {
    $(id).addEventListener("change", autoApplyExportSettings);
  });
  $("export-video").addEventListener("click", () => {
    const path = requireValue("export-path", "Output video path");
    exportPathDraft = path;
    callApi("/api/export", { path });
  });
}

applyLayoutState();
setActiveTool(activeTool);
wireGlobalActivityLogging();
wireEvents();
refresh();
