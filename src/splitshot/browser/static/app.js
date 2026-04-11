let state = null;
let selectedShotId = null;
let activeTool = window.localStorage.getItem("splitshot.activeTool") || "review";
let scorePlacementArmed = false;
let overlayFrame = null;
let waveformMode = "select";
let draggingShotId = null;
let pendingDragTimeMs = null;

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

function shortPath(path) {
  if (!path) return "None";
  const normalized = path.replaceAll("\\", "/");
  return normalized.split("/").filter(Boolean).slice(-2).join("/");
}

function fileName(path) {
  if (!path) return "No video selected";
  const normalized = path.replaceAll("\\", "/");
  return normalized.split("/").filter(Boolean).pop() || path;
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
  activity("ui.status", { message });
}

function setActiveTool(tool) {
  if (!document.querySelector(`[data-tool-pane="${tool}"]`)) tool = "review";
  const changed = activeTool !== tool;
  activeTool = tool;
  window.localStorage.setItem("splitshot.activeTool", tool);
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
  return data;
}

async function callApi(path, payload = null) {
  try {
    return await api(path, payload);
  } catch (error) {
    setStatus(error.message);
    activity("api.error", { path, error: error.message });
    return null;
  }
}

async function postFile(path, file) {
  if (!file) return null;
  const form = new FormData();
  form.append("file", file, file.name);
  setStatus(`Opening ${file.name} locally...`);
  activity("file.selected", { path, name: file.name, size: file.size });
  try {
    const response = await fetch(path, { method: "POST", body: form });
    const data = await response.json();
    if (!response.ok || data.error) throw new Error(data.error || response.statusText);
    state = data;
    render();
    activity("file.ingested", { path, name: file.name, shots: data.metrics?.total_shots });
    return data;
  } catch (error) {
    setStatus(error.message);
    activity("file.error", { path, name: file.name, error: error.message });
    return null;
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
  $("current-file").textContent = fileName(state.project.primary_video.path);
  $("primary-file").textContent = state.project.primary_video.path || "None";
  $("secondary-file").textContent = state.project.secondary_video?.path || "None";
  $("project-file").textContent = state.project.path || "Active in memory";
  $("media-badge").textContent = state.media.primary_available
    ? `Primary: ${shortPath(state.project.primary_video.path)}`
    : "No video selected";
}

function renderStats() {
  $("draw").textContent = seconds(state.metrics.draw_ms);
  $("raw-time").textContent = seconds(state.metrics.raw_time_ms ?? state.metrics.stage_time_ms);
  $("shot-count").textContent = state.metrics.total_shots;
  $("avg-split").textContent = seconds(state.metrics.average_split_ms);
  const raw = seconds(state.metrics.raw_time_ms ?? state.metrics.stage_time_ms);
  $("review-summary").textContent = state.media.primary_available
    ? `${state.metrics.total_shots} shots | raw ${raw}s`
    : "No video open.";
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

function renderTimingTable(tableId = "timing-table") {
  const table = $(tableId);
  if (!table) return;
  table.innerHTML = "";
  const headers = ["Shot", "Split", "Beep To Shot", "Absolute", "Score", "Confidence", "Source"];
  headers.forEach((header) => {
    const cell = document.createElement("div");
    cell.className = "head";
    cell.textContent = header;
    table.appendChild(cell);
  });

  (state.timing_segments || []).forEach((segment) => {
    const values = [
      segment.label,
      `${segment.segment_s || "--"} s`,
      `${segment.cumulative_s || "--"} s`,
      `${segment.absolute_s} s`,
      segment.score_letter || "--",
      segment.confidence === null || segment.confidence === undefined ? "manual" : `${Math.round(segment.confidence * 100)}%`,
      segment.source,
    ];
    values.forEach((value) => {
      const cell = document.createElement("div");
      if (segment.shot_id === selectedShotId) cell.className = "selected";
      cell.textContent = value;
      cell.addEventListener("click", () => selectShot(segment.shot_id));
      table.appendChild(cell);
    });
  });
}

function renderTimingTables() {
  renderTimingTable("timing-table");
  renderTimingTable("timing-workbench-table");
}

function renderSelection() {
  selectedShotId = state.project.ui_state.selected_shot_id || selectedShotId;
  const segment = (state.timing_segments || []).find((item) => item.shot_id === selectedShotId);
  $("selected-shot-copy").textContent = segment
    ? `${segment.label}: ${segment.segment_s}s split, ${segment.cumulative_s}s from beep.`
    : "No shot selected.";
  $("selected-score-shot").textContent = segment ? segment.label : "No shot selected";
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
  $("penalties-label").firstChild.textContent = `${summary.penalty_label || "Penalties"} `;
  $("scoring-result").textContent = `${summary.display_label}: ${summary.display_value}`;
  if (previousLength === 0) select.addEventListener("change", renderScoringPresetDescription);
}

function renderScoringPresetDescription() {
  const selected = $("scoring-preset").value;
  const preset = (state.scoring_presets || []).find((item) => item.id === selected);
  $("scoring-description").textContent = preset ? `${preset.sport}: ${preset.description}` : "";
}

function renderControls() {
  $("threshold").value = state.project.analysis.detection_threshold;
  $("sync-offset").textContent = `${state.project.analysis.sync_offset_ms} ms`;
  $("merge-enabled").checked = state.project.merge.enabled;
  $("merge-layout").value = state.project.merge.layout;
  $("pip-size").value = state.project.merge.pip_size;
  $("overlay-position").value = state.project.overlay.position;
  $("badge-size").value = state.project.overlay.badge_size;
  $("scoring-enabled").checked = state.project.scoring.enabled;
  $("penalties").value = state.project.scoring.penalties;
  $("quality").value = state.project.export.quality;
  $("aspect-ratio").value = state.project.export.aspect_ratio;
  $("crop-center-x").value = state.project.export.crop_center_x;
  $("crop-center-y").value = state.project.export.crop_center_y;
  renderScoringPresetOptions();
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
  renderHeader();
  renderStats();
  renderVideo();
  renderTimelineStrip();
  renderWaveform();
  renderSplitCards();
  renderTimingTables();
  renderSelection();
  renderControls();
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
  };
}

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
  $("apply-threshold").addEventListener("click", () => callApi("/api/analysis/threshold", { threshold: Number($("threshold").value) }));
  $("apply-merge").addEventListener("click", () => callApi("/api/merge", {
    enabled: $("merge-enabled").checked,
    layout: $("merge-layout").value,
    pip_size: $("pip-size").value,
  }));
  document.querySelectorAll("[data-sync]").forEach((button) => {
    button.addEventListener("click", () => callApi("/api/sync", { delta_ms: Number(button.dataset.sync) }));
  });
  $("swap-videos").addEventListener("click", () => callApi("/api/swap", {}));
  $("apply-overlay").addEventListener("click", () => callApi("/api/overlay", readOverlayPayload()));
  $("apply-scoring").addEventListener("click", async () => {
    await callApi("/api/scoring/profile", { ruleset: $("scoring-preset").value });
    await callApi("/api/scoring", {
      enabled: $("scoring-enabled").checked,
      penalties: Number($("penalties").value || 0),
    });
  });
  $("assign-score").addEventListener("click", () => {
    if (selectedShotId) callApi("/api/scoring/score", { shot_id: selectedShotId, letter: $("score-letter").value });
  });
  $("place-score").addEventListener("click", (event) => {
    event.stopPropagation();
    scorePlacementArmed = !scorePlacementArmed;
    $("place-score").classList.toggle("armed", scorePlacementArmed);
  });
  $("video-stage").addEventListener("click", (event) => {
    if (!scorePlacementArmed || !selectedShotId) return;
    const rect = $("video-stage").getBoundingClientRect();
    const x_norm = Math.max(0, Math.min(1, (event.clientX - rect.left) / rect.width));
    const y_norm = Math.max(0, Math.min(1, (event.clientY - rect.top) / rect.height));
    scorePlacementArmed = false;
    $("place-score").classList.remove("armed");
    callApi("/api/scoring/position", { shot_id: selectedShotId, x_norm, y_norm });
  });
  $("apply-layout").addEventListener("click", () => callApi("/api/layout", {
    quality: $("quality").value,
    aspect_ratio: $("aspect-ratio").value,
    crop_center_x: Number($("crop-center-x").value),
    crop_center_y: Number($("crop-center-y").value),
  }));
  $("export-video").addEventListener("click", () => callApi("/api/export", { path: requireValue("export-path", "Output MP4 path") }));
}

setActiveTool(activeTool);
wireEvents();
refresh();
