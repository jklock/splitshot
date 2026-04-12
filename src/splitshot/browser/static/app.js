let state = null;
let selectedShotId = null;
let activeTool = window.localStorage.getItem("splitshot.activeTool") || "review";
let scorePlacementArmed = false;
let overlayFrame = null;
let waveformMode = "select";
let draggingShotId = null;
let pendingDragTimeMs = null;
let timingRowEdits = new Set();
let overlayStyleMode = "square";
let overlaySpacing = 8;
let overlayMargin = 8;
let busyCount = 0;
let layoutLocked = window.localStorage.getItem("splitshot.layoutLocked") !== "false";
let layoutSizes = {
  railWidth: savedNumber("splitshot.layout.railWidth", 96),
  inspectorWidth: savedNumber("splitshot.layout.inspectorWidth", 440),
  waveformHeight: savedNumber("splitshot.layout.waveformHeight", 206),
};
let activeResize = null;

const $ = (id) => document.getElementById(id);

const badgeControls = [
  ["timer_badge", "Timer Badge"],
  ["shot_badge", "Shot Badge"],
  ["current_shot_badge", "Current Shot Badge"],
  ["hit_factor_badge", "Score Badge"],
];

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

function setCssPixels(name, value) {
  document.documentElement.style.setProperty(name, `${Math.round(value)}px`);
}

function applyLayoutState() {
  layoutSizes = {
    railWidth: clamp(layoutSizes.railWidth, 72, 150),
    inspectorWidth: clamp(layoutSizes.inspectorWidth, 320, Math.max(320, window.innerWidth * 0.48)),
    waveformHeight: clamp(layoutSizes.waveformHeight, 112, Math.max(112, window.innerHeight * 0.42)),
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
  const toggle = $("toggle-layout-lock");
  if (toggle) toggle.textContent = layoutLocked ? "Unlock Layout" : "Lock Layout";
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
  layoutSizes = { railWidth: 96, inspectorWidth: 440, waveformHeight: 206 };
  ["splitshot.layout.railWidth", "splitshot.layout.inspectorWidth", "splitshot.layout.waveformHeight"].forEach((key) => {
    window.localStorage.removeItem(key);
  });
  activity("layout.reset", layoutSizes);
  applyLayoutState();
  if (state) renderWaveform();
}

function beginLayoutResize(kind, event) {
  if (layoutLocked) {
    activity("layout.resize.blocked", { kind });
    return;
  }
  activeResize = { kind, pointerId: event.pointerId };
  event.currentTarget.setPointerCapture(event.pointerId);
  document.body.classList.add("resizing-layout");
  activity("layout.resize.start", { kind });
  applyLayoutState();
}

function moveLayoutResize(event) {
  if (!activeResize) return;
  const kind = activeResize.kind;
  if (kind === "railWidth") {
    persistLayoutSize("railWidth", clamp(event.clientX, 72, 150));
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
  const kind = activeResize.kind;
  try {
    event.currentTarget.releasePointerCapture(activeResize.pointerId);
  } catch {
    // Pointer capture can already be released when the drag leaves the handle.
  }
  activeResize = null;
  document.body.classList.remove("resizing-layout");
  activity("layout.resize.commit", { kind, sizes: layoutSizes });
  applyLayoutState();
}

function setActiveTool(tool) {
  if (!document.querySelector(`[data-tool-pane="${tool}"]`)) tool = "review";
  const changed = activeTool !== tool;
  activeTool = tool;
  window.localStorage.setItem("splitshot.activeTool", tool);
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
  const processingMessage = path === "/api/export" ? "Exporting MP4..." : "Saving changes...";
  const processingDetail = path === "/api/export" ? "Running FFmpeg locally" : "Local update";
  const finishProcessing = payload === null ? null : beginProcessing(processingMessage, processingDetail);
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
  state = data;
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
    state = data;
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

async function pickPath(kind, targetId) {
  const target = $(targetId);
  const finishProcessing = beginProcessing("Opening file browser...", "Waiting for local path");
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
      activity("dialog.path.selected", { kind, target: targetId, path: data.path });
    } else {
      activity("dialog.path.cancelled", { kind, target: targetId });
    }
    finishProcessing("Ready.");
    return data.path || "";
  } catch (error) {
    finishProcessing(error.message);
    setStatus(error.message);
    activity("dialog.path.error", { kind, target: targetId, error: error.message });
    return "";
  }
}

async function refresh() {
  activity("api.refresh", {});
  const response = await fetch("/api/state");
  state = await response.json();
  render();
}

function durationMs() {
  return Math.max(1, state?.project?.primary_video?.duration_ms || 1);
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
  const secondaryName = state.media.secondary_display_name || fileName(state.project.secondary_video?.path || "");
  $("current-file").textContent = primaryName;
  $("primary-file-path").value = state.project.primary_video.path || "";
  $("secondary-file-path").value = state.project.secondary_video?.path || "";
  $("project-path").value = state.project.path || $("project-path").value || `${state.default_project_path || "~/splitshot"}/project.ssproj`;
  $("media-badge").textContent = state.media.primary_available
    ? `Primary: ${primaryName}`
    : "No video selected";
}

function renderStats() {
  $("draw").textContent = seconds(state.metrics.draw_ms);
  $("raw-time").textContent = seconds(state.metrics.raw_time_ms ?? state.metrics.stage_time_ms);
  $("shot-count").textContent = state.metrics.total_shots;
  $("avg-split").textContent = seconds(state.metrics.average_split_ms);
  const raw = seconds(state.metrics.raw_time_ms ?? state.metrics.stage_time_ms);
  $("timing-summary").textContent = state.metrics.raw_time_ms
    ? `Raw ${raw}s from beep to final shot.`
    : "No timing data.";
}

function renderVideo() {
  const video = $("primary-video");
  const path = state.project.primary_video.path || "";
  if (state.media.primary_available && video.dataset.sourcePath !== path) {
    video.dataset.sourcePath = path;
    video.src = `/media/primary?v=${encodeURIComponent(path)}`;
    video.load();
  }
  if (!state.media.primary_available) {
    video.removeAttribute("src");
    video.dataset.sourcePath = "";
  }
}

function renderTimelineStrip() {
  const strip = $("timeline-strip");
  strip.innerHTML = "";
  const beep = state.project.analysis.beep_time_ms_primary;
  if (beep !== null && beep !== undefined) {
    strip.appendChild(marker("beep", beep));
  }
  state.project.analysis.shots.forEach((shot) => {
    strip.appendChild(marker("shot", shot.time_ms));
  });
}

function resizeCanvasToDisplay(canvas) {
  const rect = canvas.getBoundingClientRect();
  const width = Math.max(1, Math.floor(rect.width || canvas.clientWidth || 1600));
  const height = Math.max(1, Math.floor(rect.height || canvas.clientHeight || 260));
  if (canvas.width !== width || canvas.height !== height) {
    canvas.width = width;
    canvas.height = height;
  }
}

function marker(kind, timeMs) {
  const node = document.createElement("span");
  node.className = `timeline-marker ${kind}`;
  node.style.left = `${Math.max(0, Math.min(100, (timeMs / durationMs()) * 100))}%`;
  return node;
}

function renderWaveform() {
  const canvas = $("waveform");
  resizeCanvasToDisplay(canvas);
  const ctx = canvas.getContext("2d");
  const width = canvas.width;
  const height = canvas.height;
  const waveform = state.project.analysis.waveform_primary || [];
  const expanded = $("cockpit-root")?.classList.contains("waveform-expanded") ?? false;
  ctx.clearRect(0, 0, width, height);
  ctx.fillStyle = "#102033";
  ctx.fillRect(0, 0, width, height);
  drawSelectedRegion(ctx, height);
  ctx.strokeStyle = "#3aa0ff";
  ctx.lineWidth = 1;
  ctx.beginPath();
  waveform.forEach((value, index) => {
    const x = (index / Math.max(1, waveform.length - 1)) * width;
    const yTop = (height / 2) - (value * height * 0.45);
    const yBottom = (height / 2) + (value * height * 0.45);
    ctx.moveTo(x, yTop);
    ctx.lineTo(x, yBottom);
  });
  ctx.stroke();

  const beep = state.project.analysis.beep_time_ms_primary;
  if (beep !== null && beep !== undefined) drawMarker(ctx, beep, "#ff7b22", "BEEP");
  state.project.analysis.shots.forEach((shot, index) => {
    const selected = shot.id === selectedShotId;
    const label = expanded ? `${index + 1} ${seconds(shot.time_ms)}` : String(index + 1);
    const timeMs = shot.id === draggingShotId && pendingDragTimeMs !== null
      ? pendingDragTimeMs
      : shot.time_ms;
    drawMarker(ctx, timeMs, selected ? "#ffffff" : "#39d06f", label);
  });
  renderWaveformShotList();
}

function drawMarker(ctx, timeMs, color, label) {
  const x = Math.max(0, Math.min(1, timeMs / durationMs())) * ctx.canvas.width;
  ctx.strokeStyle = color;
  ctx.fillStyle = color;
  ctx.lineWidth = 3;
  ctx.beginPath();
  ctx.moveTo(x, 0);
  ctx.lineTo(x, ctx.canvas.height);
  ctx.stroke();
  ctx.font = "800 12px -apple-system, BlinkMacSystemFont, 'SF Pro Text', sans-serif";
  ctx.fillText(label, x + 5, 22);
}

function drawSelectedRegion(ctx, height) {
  const shot = selectedShot();
  if (!shot) return;
  const x = Math.max(0, Math.min(1, shot.time_ms / durationMs())) * ctx.canvas.width;
  ctx.fillStyle = "rgba(255, 123, 34, 0.18)";
  ctx.fillRect(Math.max(0, x - 44), 0, 88, height);
}

function selectShot(shotId) {
  selectedShotId = shotId;
  activity("shot.select", { shot_id: shotId });
  callApi("/api/shots/select", { shot_id: shotId });
}

function selectedShot() {
  return (state?.project?.analysis?.shots || []).find((shot) => shot.id === selectedShotId) || null;
}

function renderWaveformShotList() {
  const list = $("waveform-shot-list");
  if (!list) return;
  list.innerHTML = "";
  (state.timing_segments || []).forEach((segment) => {
    const item = document.createElement("button");
    item.type = "button";
    item.className = segment.shot_id === selectedShotId ? "selected" : "";
    item.textContent = `${segment.label} ${segment.absolute_s}s`;
    item.addEventListener("click", () => selectShot(segment.shot_id));
    list.appendChild(item);
  });
}

function renderSplitCards() {
  const grid = $("split-card-grid");
  grid.innerHTML = "";
  (state.timing_segments || []).forEach((segment) => {
    const card = document.createElement("button");
    card.type = "button";
    card.className = `split-card${segment.shot_id === selectedShotId ? " selected" : ""}`;
    card.innerHTML = `
      <span>${segment.card_title}</span>
      <strong>${segment.card_value}</strong>
      <small>${segment.card_subtitle}</small>
      <small>${segment.card_meta}</small>
    `;
    card.addEventListener("click", () => selectShot(segment.shot_id));
    grid.appendChild(card);
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
  if (field === "absolute_time_ms") {
    const timeMs = Number(value);
    if (!Number.isNaN(timeMs)) {
      callApi("/api/shots/move", { shot_id: shotId, time_ms: timeMs });
    }
  } else if (field === "score_letter") {
    if (value) {
      callApi("/api/scoring/score", { shot_id: shotId, letter: value });
    }
  }
}

function renderTimingTable(tableId = "timing-table") {
  const table = $(tableId);
  if (!table) return;
  table.innerHTML = "";
  const headers = ["", "Shot", "Split", "Absolute", "Score", "Confidence", "Source"];
  headers.forEach((header) => {
    const cell = document.createElement("div");
    cell.className = "head";
    cell.textContent = header;
    table.appendChild(cell);
  });

  const scoreOptions = state.scoring_summary?.score_options || ["A", "C", "D", "M", "NS", "M+NS"];
  (state.split_rows || []).forEach((row) => {
    const editing = timingRowEdits.has(row.shot_id);
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

    const shotCell = document.createElement("div");
    shotCell.textContent = String(row.shot_number);
    if (row.shot_id === selectedShotId) shotCell.className = "selected";
    shotCell.addEventListener("click", () => selectShot(row.shot_id));
    table.appendChild(shotCell);

    const splitCell = document.createElement("div");
    splitCell.textContent = formatTimingValue(row.split_ms === null ? "--" : `${row.split_ms} ms`);
    table.appendChild(splitCell);

    const absoluteCell = document.createElement("div");
    if (editing) {
      const input = document.createElement("input");
      input.type = "number";
      input.value = String(row.absolute_time_ms);
      input.addEventListener("change", () => updateTimingRowField(row.shot_id, "absolute_time_ms", input.value));
      absoluteCell.appendChild(input);
    } else {
      absoluteCell.textContent = `${row.absolute_time_ms} ms`;
      absoluteCell.addEventListener("click", () => selectShot(row.shot_id));
    }
    table.appendChild(absoluteCell);

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
      ? "manual"
      : `${Math.round(row.confidence * 100)}%`;
    table.appendChild(confidenceCell);

    const sourceCell = document.createElement("div");
    sourceCell.textContent = row.source;
    table.appendChild(sourceCell);
  });
}

function renderTimingTables() {
  renderTimingTable("timing-table");
  renderTimingTable("timing-workbench-table");
}

function renderSelection() {
  selectedShotId = state.project.ui_state.selected_shot_id || selectedShotId;
  const segment = (state.timing_segments || []).find((item) => item.shot_id === selectedShotId);
  const selectedLabel = segment ? segment.label : "No shot selected";
  $("selected-shot-copy").textContent = segment
    ? `${segment.label}: ${segment.segment_s}s split, ${segment.cumulative_s}s from beep.`
    : "No shot selected.";
  $("selected-timing-shot").textContent = selectedLabel;
  $("selected-score-shot").textContent = selectedLabel;
  if (segment?.score_letter && Array.from($("score-letter").options).some((option) => option.value === segment.score_letter)) {
    $("score-letter").value = segment.score_letter;
  }
  $("place-score").disabled = !segment;
  $("place-score").textContent = segment ? `Place ${$("score-letter").value} for ${segment.label}` : "Select Shot";
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
  (state.timing_segments || []).forEach((segment) => {
    const item = document.createElement("button");
    item.type = "button";
    item.className = `split-card ${segment.shot_id === selectedShotId ? "selected" : ""}`;
    item.textContent = `${segment.label}${segment.score_letter ? ` • ${segment.score_letter}` : ""}`;
    item.addEventListener("click", () => selectShot(segment.shot_id));
    list.appendChild(item);
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

function renderControls() {
  $("threshold").value = state.project.analysis.detection_threshold;
  $("sync-offset").textContent = `${state.project.analysis.sync_offset_ms} ms`;
  $("merge-enabled").checked = state.project.merge.enabled;
  $("merge-layout").value = state.project.merge.layout;
  $("pip-size").value = state.project.merge.pip_size;
  $("overlay-position").value = state.project.overlay.position;
  $("badge-size").value = state.project.overlay.badge_size;
  overlayStyleMode = state.project.overlay.style_type || overlayStyleMode;
  overlaySpacing = Number(state.project.overlay.spacing ?? overlaySpacing);
  overlayMargin = Number(state.project.overlay.margin ?? overlayMargin);
  $("overlay-style").value = overlayStyleMode;
  $("overlay-spacing").value = overlaySpacing;
  $("overlay-margin").value = overlayMargin;
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
  $("export-path").value = state.project.export.output_path || $("export-path").value || `${state.default_project_path || "~/splitshot"}/output.mp4`;
  renderScoringPresetOptions();
  renderExportPresetOptions();
  renderExportLog();
  renderStyleControls();
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
  Object.entries(state.project.overlay.scoring_colors).forEach(([letter, color]) => {
    const label = document.createElement("label");
    label.textContent = `${letter} `;
    const input = document.createElement("input");
    input.type = "color";
    input.className = "score-color-input";
    input.dataset.letter = letter;
    input.value = color;
    label.appendChild(input);
    scoreGrid.appendChild(label);
  });
}

function badgeElement(text, style, size) {
  const badge = document.createElement("span");
  badge.className = `overlay-badge badge-${size}`;
  badge.textContent = text;
  badge.style.background = rgba(style.background_color, style.opacity);
  badge.style.color = style.text_color;
  badge.style.borderRadius = overlayStyleMode === "bubble" ? "999px" : overlayStyleMode === "rounded" ? "16px" : "0";
  badge.style.padding = `${overlaySpacing}px ${Math.max(8, overlaySpacing * 1.5)}px`;
  badge.style.margin = `${overlayMargin}px`;
  return badge;
}

function renderLiveOverlay() {
  if (!state?.project) return;
  const overlay = $("live-overlay");
  const scoreLayer = $("score-layer");
  const position = state.project.overlay.position;
  overlay.className = `live-overlay overlay-${position}`;
  overlay.innerHTML = "";
  scoreLayer.innerHTML = "";
  if (position === "none" || !state.media.primary_available) return;

  const video = $("primary-video");
  const positionMs = Math.round((video.currentTime || 0) * 1000);
  const beep = state.project.analysis.beep_time_ms_primary;
  const elapsed = beep === null || beep === undefined ? positionMs : Math.max(0, positionMs - beep);
  const size = state.project.overlay.badge_size;
  overlay.appendChild(badgeElement(`Timer ${seconds(elapsed)}`, state.project.overlay.timer_badge, size));
  if (state.metrics.draw_ms !== null && state.metrics.draw_ms !== undefined) {
    overlay.appendChild(badgeElement(`Draw ${seconds(state.metrics.draw_ms)}`, state.project.overlay.shot_badge, size));
  }

  const shots = state.project.analysis.shots || [];
  const currentIndex = currentShotIndex(positionMs);
  if (currentIndex >= 0) {
    const start = Math.max(0, currentIndex - 3);
    for (let index = start; index <= currentIndex; index += 1) {
      const shot = shots[index];
      const splitMs = index === 0
        ? shot.time_ms - (beep || 0)
        : shot.time_ms - shots[index - 1].time_ms;
      const style = index === currentIndex
        ? state.project.overlay.current_shot_badge
        : state.project.overlay.shot_badge;
      overlay.appendChild(badgeElement(`Shot ${index + 1} ${seconds(splitMs)}`, style, size));
    }
  }

  const summary = state.scoring_summary || {};
  if (state.project.scoring.enabled && summary.display_value && summary.display_value !== "--") {
    overlay.appendChild(
      badgeElement(`${summary.display_label} ${summary.display_value}`, state.project.overlay.hit_factor_badge, size),
    );
  }

  if (state.project.scoring.enabled) {
    shots.forEach((shot) => {
      if (!shot.score) return;
      const elapsedSince = positionMs - shot.time_ms;
      if (elapsedSince < 0 || elapsedSince > 1200) return;
      const mark = document.createElement("span");
      mark.className = "score-float";
      mark.textContent = shot.score.letter;
      mark.style.left = `${shot.score.x_norm * 100}%`;
      mark.style.top = `${shot.score.y_norm * 100}%`;
      mark.style.color = state.project.overlay.scoring_colors[shot.score.letter] || "#ffffff";
      mark.style.opacity = String(Math.max(0.2, 1 - (elapsedSince / 1200)));
      scoreLayer.appendChild(mark);
    });
  }
}

function startOverlayLoop() {
  if (overlayFrame !== null) return;
  activity("video.play", { current_time_s: $("primary-video").currentTime });
  const tick = () => {
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
  renderLiveOverlay();
}

function render() {
  if (!state?.project) return;
  applyLayoutState();
  renderHeader();
  renderStats();
  renderVideo();
  renderTimelineStrip();
  renderWaveform();
  renderSplitCards();
  renderTimingTables();
  renderControls();
  renderSelection();
  renderLiveOverlay();
  setActiveTool(activeTool);
}

function waveformTime(event) {
  const rect = $("waveform").getBoundingClientRect();
  const x = Math.max(0, Math.min(1, (event.clientX - rect.left) / rect.width));
  return Math.round(x * durationMs());
}

function shotPixelDistance(event, shot) {
  const rect = $("waveform").getBoundingClientRect();
  const shotX = (shot.time_ms / durationMs()) * rect.width;
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
  } else if (mode === "beep") {
    help.textContent = "Move Beep mode: click the waveform to place the timer beep.";
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
  if (waveformMode === "beep") {
    activity("waveform.move_beep", { time_ms });
    callApi("/api/beep", { time_ms });
    return;
  }
  const shot = nearestShot(event);
  if (shot) {
    selectedShotId = shot.id;
    draggingShotId = shot.id;
    pendingDragTimeMs = shot.time_ms;
    $("waveform").setPointerCapture(event.pointerId);
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
  try {
    $("waveform").releasePointerCapture(event.pointerId);
  } catch {
    // Pointer capture may already be released by the browser.
  }
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
  document.querySelectorAll(".style-card").forEach((card) => {
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
    position: $("overlay-position").value,
    badge_size: $("badge-size").value,
    styles,
    scoring_colors: scoringColors,
    style_type: overlayStyleMode,
    spacing: overlaySpacing,
    margin: overlayMargin,
  };
}

function readMergePayload() {
  return {
    enabled: $("merge-enabled").checked,
    layout: $("merge-layout").value,
    pip_size: $("pip-size").value,
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

function wireEvents() {
  document.querySelectorAll("[data-tool]").forEach((item) => {
    item.addEventListener("click", () => {
      activity("ui.tool.click", { tool: item.dataset.tool });
      setActiveTool(item.dataset.tool);
    });
  });
  $("new-project").addEventListener("click", () => callApi("/api/project/new", {}));
  $("choose-primary").addEventListener("click", () => $("primary-file-input").click());
  $("choose-secondary").addEventListener("click", () => $("secondary-file-input").click());
  $("import-primary-path").addEventListener("click", () => {
    const path = $("primary-file-path").value.trim();
    if (!path) return setStatus("Primary video path is required.");
    callApi("/api/import/primary", { path });
  });
  $("import-secondary-path").addEventListener("click", () => {
    const path = $("secondary-file-path").value.trim();
    if (!path) return setStatus("Secondary video path is required.");
    callApi("/api/import/secondary", { path });
  });
  $("browse-project-path").addEventListener("click", () => pickPath("project", "project-path"));
  $("browse-export-path").addEventListener("click", () => pickPath("export", "export-path"));
  $("browse-primary-path").addEventListener("click", () => pickPath("primary", "primary-file-path"));
  $("browse-secondary-path").addEventListener("click", () => pickPath("secondary", "secondary-file-path"));
  document.querySelectorAll("[data-open-primary]").forEach((item) => {
    item.addEventListener("click", () => $("primary-file-input").click());
  });
  document.querySelectorAll("[data-open-secondary]").forEach((item) => {
    item.addEventListener("click", () => $("secondary-file-input").click());
  });
  $("primary-file-input").addEventListener("change", async (event) => {
    const result = await postFile("/api/files/primary", event.target.files[0]);
    if (result) setActiveTool("review");
    event.target.value = "";
  });
  $("secondary-file-input").addEventListener("change", async (event) => {
    const result = await postFile("/api/files/secondary", event.target.files[0]);
    if (result) setActiveTool("merge");
    event.target.value = "";
  });
  $("save-project").addEventListener("click", () => callApi("/api/project/save", { path: requireValue("project-path", "Project path") }));
  $("open-project").addEventListener("click", () => callApi("/api/project/open", { path: requireValue("project-path", "Project path") }));
  $("delete-project").addEventListener("click", () => callApi("/api/project/delete", {}));
  $("primary-video").addEventListener("play", startOverlayLoop);
  $("primary-video").addEventListener("pause", stopOverlayLoop);
  $("primary-video").addEventListener("seeked", () => {
    activity("video.seeked", { current_time_s: $("primary-video").currentTime });
    renderLiveOverlay();
  });
  $("primary-video").addEventListener("timeupdate", renderLiveOverlay);
  document.querySelectorAll("[data-waveform-mode]").forEach((button) => {
    button.addEventListener("click", () => setWaveformMode(button.dataset.waveformMode));
  });
  $("expand-waveform").addEventListener("click", () => {
    setWaveformExpanded(!$("cockpit-root").classList.contains("waveform-expanded"));
  });
  $("expand-timing").addEventListener("click", () => setTimingExpanded(true));
  $("collapse-timing").addEventListener("click", () => setTimingExpanded(false));
  $("waveform").addEventListener("pointerdown", handleWaveformPointerDown);
  $("waveform").addEventListener("pointermove", handleWaveformPointerMove);
  $("waveform").addEventListener("pointerup", handleWaveformPointerUp);
  $("waveform").addEventListener("pointercancel", handleWaveformPointerUp);
  document.addEventListener("keydown", handleKeyboardEdit);
  window.addEventListener("resize", debounce(() => {
    render();
  }, 120));
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
  ["merge-enabled", "merge-layout", "pip-size"].forEach((id) => {
    $(id).addEventListener("change", autoApplyMerge);
  });
  document.querySelectorAll("[data-sync]").forEach((button) => {
    button.addEventListener("click", () => callApi("/api/sync", { delta_ms: Number(button.dataset.sync) }));
  });
  $("swap-videos").addEventListener("click", () => callApi("/api/swap", {}));
  ["overlay-position", "badge-size"].forEach((id) => {
    $(id).addEventListener("change", autoApplyOverlay);
  });
  $("badge-style-grid").addEventListener("input", autoApplyOverlay);
  $("score-color-grid").addEventListener("input", autoApplyOverlay);
  ["scoring-enabled", "scoring-preset"].forEach((id) => {
    $(id).addEventListener("change", autoApplyScoring);
  });
  $("scoring-penalty-grid").addEventListener("input", autoApplyScoring);
  $("score-letter").addEventListener("change", () => {
    assignSelectedScore();
  });
  $("toggle-layout-lock").addEventListener("click", toggleLayoutLock);
  $("reset-layout").addEventListener("click", resetLayout);
  [
    ["resize-rail", "railWidth"],
    ["resize-sidebar", "inspectorWidth"],
    ["resize-waveform", "waveformHeight"],
  ].forEach(([id, kind]) => {
    const handle = $(id);
    handle.addEventListener("pointerdown", (event) => beginLayoutResize(kind, event));
    handle.addEventListener("pointermove", moveLayoutResize);
    handle.addEventListener("pointerup", endLayoutResize);
    handle.addEventListener("pointercancel", endLayoutResize);
  });
  ["overlay-style"].forEach((id) => {
    $(id).addEventListener("change", () => {
      overlayStyleMode = $(id).value;
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
      renderLiveOverlay();
      autoApplyOverlay();
    });
  });
  $("place-score").addEventListener("click", (event) => {
    event.stopPropagation();
    scorePlacementArmed = !scorePlacementArmed;
    $("place-score").classList.toggle("armed", scorePlacementArmed);
    activity("score.place.toggle", { armed: scorePlacementArmed, shot_id: selectedShotId });
  });
  $("video-stage").addEventListener("click", (event) => {
    if (!scorePlacementArmed || !selectedShotId) return;
    const rect = $("video-stage").getBoundingClientRect();
    const x_norm = Math.max(0, Math.min(1, (event.clientX - rect.left) / rect.width));
    const y_norm = Math.max(0, Math.min(1, (event.clientY - rect.top) / rect.height));
    scorePlacementArmed = false;
    $("place-score").classList.remove("armed");
    activity("score.place.commit", { shot_id: selectedShotId, x_norm, y_norm });
    callApi("/api/scoring/position", { shot_id: selectedShotId, x_norm, y_norm });
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
  $("export-video").addEventListener("click", () => callApi("/api/export", { path: requireValue("export-path", "Output MP4 path") }));
}

applyLayoutState();
setActiveTool(activeTool);
wireGlobalActivityLogging();
wireEvents();
refresh();
