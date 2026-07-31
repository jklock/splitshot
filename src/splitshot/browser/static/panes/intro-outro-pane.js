const MATCH_METRICS = Object.freeze([
  ["match_result", "Final Match Result"],
  ["raw_time", "Raw Time"],
  ["stage_count", "Stages"],
  ["total_shots", "Shots"],
  ["shot_points", "Shot Points"],
  ["penalties", "Penalties"],
  ["competitor", "Competitor"],
  ["division", "Division"],
  ["classification", "Class"],
  ["overall_place", "Overall Place"],
]);

const DEFAULT_MATCH_METRICS = Object.freeze([
  "match_result",
  "raw_time",
  "stage_count",
  "total_shots",
  "penalties",
  "division",
  "classification",
  "overall_place",
]);

export function createIntroOutroPane({
  $ = (id) => document.getElementById(id),
  documentObject = document,
  getState = () => null,
  callApi = async () => null,
  pickPath = async () => "",
  activity = () => {},
  fileName = (value) => String(value || ""),
} = {}) {
  let selectedKind = "intro";

  function state() {
    return getState() || {};
  }

  function project() {
    return state().project || {};
  }

  function clip(kind = selectedKind) {
    return project()?.[`${kind}_clip`] || { asset: {}, overlay: {} };
  }

  function boxes(kind = selectedKind) {
    return Array.isArray(clip(kind)?.overlay?.text_boxes) ? clip(kind).overlay.text_boxes : [];
  }

  function escapeHtml(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;");
  }

  function matchValue(metricId) {
    const metrics = state().match_metrics || {};
    const scoring = project().scoring || {};
    const values = {
      match_result: metrics.display_value || "",
      raw_time: metrics.raw_time_ms == null ? "" : `${(Number(metrics.raw_time_ms) / 1000).toFixed(2)}s`,
      stage_count: metrics.stage_count || "",
      total_shots: metrics.total_shots || "",
      shot_points: Number(metrics.shot_points || 0).toString(),
      penalties: Number(metrics.total_penalties || 0).toString(),
      competitor: scoring.competitor_name || "",
      division: scoring.division || "",
      classification: scoring.classification || "",
      overall_place: scoring.competitor_place || "",
    };
    return String(values[metricId] ?? "");
  }

  function boxDisplayText(box) {
    if (box.source !== "match_summary") return String(box.text || "");
    const requested = Array.isArray(box.summary_metric_ids) && box.summary_metric_ids.length
      ? box.summary_metric_ids
      : DEFAULT_MATCH_METRICS;
    const resultLabel = String(state().match_metrics?.result_label || "Final");
    return MATCH_METRICS
      .filter(([id]) => requested.includes(id) && matchValue(id))
      .map(([id, label]) => `${id === "match_result" ? resultLabel : label} ${matchValue(id)}`)
      .join("\n");
  }

  function normalizedBox(box = {}) {
    return {
      id: box.id || `boundary-${Date.now().toString(36)}-${Math.random().toString(16).slice(2)}`,
      enabled: box.enabled !== false,
      lock_to_stack: false,
      source: box.source === "match_summary" ? "match_summary" : "manual",
      text: String(box.text || ""),
      quadrant: box.quadrant || "top_right",
      x: box.x ?? null,
      y: box.y ?? null,
      background_color: box.background_color || "#000000",
      text_color: box.text_color || "#ffffff",
      opacity: Number(box.opacity ?? 0.9),
      width: Number(box.width || 0),
      height: Number(box.height || 0),
      summary_metric_ids: Array.isArray(box.summary_metric_ids) ? box.summary_metric_ids : [],
      style_type: box.style_type || "square",
      font_family: box.font_family || "Arial",
      font_size: Number(box.font_size || 28),
      font_bold: box.font_bold !== false,
      font_italic: Boolean(box.font_italic),
    };
  }

  async function saveBoxes(nextBoxes) {
    activity("intro-outro.overlay.update", { kind: selectedKind, count: nextBoxes.length });
    await callApi("/api/project/intro-outro/overlay", {
      kind: selectedKind,
      text_boxes: nextBoxes.map(normalizedBox),
    });
  }

  async function selectVideo(kind) {
    const path = await pickPath("queue_media", null);
    if (!path) return;
    selectedKind = kind;
    await callApi("/api/project/queue/media", { kind, path });
  }

  function updatePreview() {
    const pane = $("intro-outro-pane");
    if (!pane?.classList.contains("active")) return;
    const video = $("primary-video");
    const path = clip()?.asset?.path || "";
    if (video && path) {
      const expected = `${window.location.origin}/media/${selectedKind}`;
      if (!String(video.src || "").startsWith(expected)) video.src = `/media/${selectedKind}?v=${encodeURIComponent(state().media?.cache_token || "")}`;
    }
    if (video) video.hidden = !path;
    $("secondary-video")?.setAttribute("hidden", "");
    $("secondary-image")?.setAttribute("hidden", "");
    const liveOverlay = $("live-overlay");
    if (liveOverlay) liveOverlay.innerHTML = "";
    const overlay = $("custom-overlay");
    if (!overlay) return;
    overlay.innerHTML = "";
    boxes().filter((box) => box.enabled && boxDisplayText(box).trim()).forEach((box) => {
      const badge = documentObject.createElement("div");
      badge.className = "overlay-badge intro-outro-preview-badge";
      badge.textContent = boxDisplayText(box);
      badge.style.background = box.background_color || "#000000";
      badge.style.color = box.text_color || "#ffffff";
      badge.style.opacity = String(box.opacity ?? 0.9);
      badge.style.fontSize = `${Math.max(8, Number(box.font_size || 28))}px`;
      badge.style.fontFamily = box.font_family || "Arial";
      badge.style.fontWeight = box.font_bold === false ? "400" : "700";
      badge.style.fontStyle = box.font_italic ? "italic" : "normal";
      badge.style.borderRadius = box.style_type === "rounded" ? "10px" : box.style_type === "bubble" ? "999px" : "0";
      if (box.width) badge.style.width = `${box.width}px`;
      if (box.height) badge.style.height = `${box.height}px`;
      const positions = {
        top_left: ["4%", "6%"], top_middle: ["50%", "6%"], top_right: ["96%", "6%"],
        middle_left: ["4%", "50%"], middle_middle: ["50%", "50%"], middle_right: ["96%", "50%"],
        bottom_left: ["4%", "94%"], bottom_middle: ["50%", "94%"], bottom_right: ["96%", "94%"],
      };
      const [left, top] = box.quadrant === "custom"
        ? [`${Number(box.x ?? 0.5) * 100}%`, `${Number(box.y ?? 0.5) * 100}%`]
        : (positions[box.quadrant] || positions.top_right);
      badge.style.left = left;
      badge.style.top = top;
      badge.style.transform = `translate(${left === "4%" ? "0" : left === "96%" ? "-100%" : "-50%"}, ${top === "6%" ? "0" : top === "94%" ? "-100%" : "-50%"})`;
      overlay.appendChild(badge);
    });
    overlay.classList.toggle("has-badge", overlay.childElementCount > 0);
  }

  function metricChecklist(box, index) {
    if (box.source !== "match_summary") return "";
    const selected = box.summary_metric_ids?.length ? box.summary_metric_ids : DEFAULT_MATCH_METRICS;
    return `<fieldset class="intro-outro-metrics"><legend>Match data</legend>${MATCH_METRICS.map(([id, label]) => `
      <label class="check-row"><input type="checkbox" data-box-index="${index}" data-metric-id="${id}" ${selected.includes(id) ? "checked" : ""} /> ${label}</label>
    `).join("")}</fieldset>`;
  }

  function boxEditor(box, index) {
    return `<article class="text-box-card intro-outro-box" data-box-index="${index}">
      <div class="section-header"><strong>${box.source === "match_summary" ? "Match Results" : `Text Box ${index + 1}`}</strong><button type="button" data-remove-box="${index}">Remove</button></div>
      <label class="check-row"><input type="checkbox" data-box-field="enabled" ${box.enabled ? "checked" : ""} /> Show box</label>
      <label>Source<select data-box-field="source"><option value="manual" ${box.source !== "match_summary" ? "selected" : ""}>Custom text</option><option value="match_summary" ${box.source === "match_summary" ? "selected" : ""}>Match results</option></select></label>
      <label>Text<textarea data-box-field="text" rows="3" ${box.source === "match_summary" ? "placeholder=\"Leave blank to use selected match data\"" : ""}>${escapeHtml(box.text || "")}</textarea></label>
      ${metricChecklist(box, index)}
      <div class="control-grid"><label>Position<select data-box-field="quadrant">${["top_left", "top_middle", "top_right", "middle_left", "middle_middle", "middle_right", "bottom_left", "bottom_middle", "bottom_right", "custom"].map((value) => `<option value="${value}" ${box.quadrant === value ? "selected" : ""}>${value.replaceAll("_", " ")}</option>`).join("")}</select></label><label>Shape<select data-box-field="style_type"><option value="square" ${box.style_type === "square" ? "selected" : ""}>Square</option><option value="rounded" ${box.style_type === "rounded" ? "selected" : ""}>Rounded</option><option value="bubble" ${box.style_type === "bubble" ? "selected" : ""}>Bubble</option></select></label></div>
      <div class="control-grid"><label>X (0–1)<input data-box-field="x" type="number" min="0" max="1" step="0.01" value="${box.x ?? 0.5}" /></label><label>Y (0–1)<input data-box-field="y" type="number" min="0" max="1" step="0.01" value="${box.y ?? 0.5}" /></label></div>
      <div class="control-grid"><label>Width (auto 0)<input data-box-field="width" type="number" min="0" value="${Number(box.width || 0)}" /></label><label>Height (auto 0)<input data-box-field="height" type="number" min="0" value="${Number(box.height || 0)}" /></label></div>
      <div class="control-grid"><label>Font<input data-box-field="font_family" type="text" value="${escapeHtml(box.font_family || "Arial")}" /></label><label>Font size<input data-box-field="font_size" type="number" min="8" max="72" value="${Number(box.font_size || 28)}" /></label></div>
      <div class="control-grid"><label>Background<input data-box-field="background_color" type="color" value="${escapeHtml(box.background_color || "#000000")}" /></label><label>Text color<input data-box-field="text_color" type="color" value="${escapeHtml(box.text_color || "#ffffff")}" /></label></div>
      <div class="control-grid"><label>Opacity %<input data-box-field="opacity" type="number" min="0" max="100" value="${Math.round(Number(box.opacity ?? 0.9) * 100)}" /></label><div><label class="check-row"><input data-box-field="font_bold" type="checkbox" ${box.font_bold ? "checked" : ""} /> Bold</label><label class="check-row"><input data-box-field="font_italic" type="checkbox" ${box.font_italic ? "checked" : ""} /> Italic</label></div></div>
    </article>`;
  }

  function render() {
    const pane = $("intro-outro-pane");
    if (!pane) return;
    const selectedClip = clip();
    const path = selectedClip?.asset?.path || "";
    pane.innerHTML = `<div class="pane-section intro-outro-shell">
      <div class="section-header pane-title-row"><h3>Intro / Outro</h3><span class="pane-status-text">Match media</span></div>
      <div class="button-grid two-up intro-outro-kind-tabs"><button type="button" data-boundary-kind="intro" class="${selectedKind === "intro" ? "active" : ""}">Intro</button><button type="button" data-boundary-kind="outro" class="${selectedKind === "outro" ? "active" : ""}">Outro</button></div>
      <section class="settings-section"><div class="section-header"><strong>${selectedKind === "intro" ? "Intro" : "Outro"} Video</strong></div><button id="intro-outro-select-video" class="btn btn-primary" type="button">${path ? "Replace Video" : "Select Video"}</button><small class="intro-outro-file">${path ? escapeHtml(fileName(path)) : "No video selected"}</small></section>
      <section class="settings-section"><div class="section-header"><strong>Text Overlays</strong></div><div class="button-grid two-up"><button id="intro-outro-add-text" type="button">Add Text Box</button><button id="intro-outro-add-match" type="button">Add Match Results</button></div><div class="intro-outro-box-list">${boxes().map((box, index) => boxEditor(normalizedBox(box), index)).join("") || '<div class="empty-state">Add a text box or Match Results overlay.</div>'}</div></section>
    </div>`;
    bindEvents(pane);
    updatePreview();
  }

  function bindEvents(pane) {
    pane.onclick = async (event) => {
      const target = event.target instanceof HTMLElement ? event.target : null;
      if (!target) return;
      const kindButton = target.closest("[data-boundary-kind]");
      if (kindButton) { selectedKind = kindButton.dataset.boundaryKind || "intro"; render(); return; }
      if (target.closest("#intro-outro-select-video")) { await selectVideo(selectedKind); return; }
      if (target.closest("#intro-outro-add-text")) { await saveBoxes([...boxes(), normalizedBox({ source: "manual", text: "Title" })]); return; }
      if (target.closest("#intro-outro-add-match")) { await saveBoxes([...boxes(), normalizedBox({ source: "match_summary", summary_metric_ids: [...DEFAULT_MATCH_METRICS], quadrant: "top_right" })]); return; }
      const remove = target.closest("[data-remove-box]");
      if (remove) await saveBoxes(boxes().filter((_box, index) => index !== Number(remove.dataset.removeBox)));
    };
    pane.onchange = async (event) => {
      const target = event.target instanceof HTMLInputElement || event.target instanceof HTMLSelectElement || event.target instanceof HTMLTextAreaElement ? event.target : null;
      if (!target) return;
      if (target.dataset.metricId) {
        const index = Number(target.dataset.boxIndex);
        const next = boxes().map(normalizedBox);
        const selected = new Set(next[index].summary_metric_ids?.length ? next[index].summary_metric_ids : DEFAULT_MATCH_METRICS);
        target.checked ? selected.add(target.dataset.metricId) : selected.delete(target.dataset.metricId);
        next[index].summary_metric_ids = [...selected];
        await saveBoxes(next);
        return;
      }
      const card = target.closest("[data-box-index]");
      if (!card || !target.dataset.boxField) return;
      const index = Number(card.dataset.boxIndex);
      const next = boxes().map(normalizedBox);
      const field = target.dataset.boxField;
      let value = target instanceof HTMLInputElement && target.type === "checkbox" ? target.checked : target.value;
      if (["font_size", "width", "height", "x", "y"].includes(field)) value = Number(value);
      if (field === "opacity") value = Number(value) / 100;
      next[index][field] = value;
      if (field === "source" && value === "match_summary" && !next[index].summary_metric_ids.length) next[index].summary_metric_ids = [...DEFAULT_MATCH_METRICS];
      await saveBoxes(next);
    };
  }

  return Object.freeze({ render, updatePreview, selectedKind: () => selectedKind });
}
