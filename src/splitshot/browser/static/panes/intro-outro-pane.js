const MATCH_METRICS = Object.freeze([
  ["score_time", "Score / Time"],
  ["raw_time", "Raw Time"],
  ["points_down", "Points Down"],
  ["penalties", "Penalties"],
  ["division_placement", "Division"],
  ["class_placement", "Class"],
  ["overall_placement", "Overall"],
]);

const DEFAULT_MATCH_METRICS = Object.freeze([
  "score_time",
  "raw_time",
  "points_down",
  "penalties",
  "division_placement",
  "class_placement",
  "overall_placement",
]);

const LEGACY_MATCH_METRIC_IDS = Object.freeze({
  match_result: "score_time",
  shot_points: "points_down",
  division: "division_placement",
  classification: "class_placement",
  overall_place: "overall_placement",
});

const MATCH_RENDER_METRICS = Object.freeze([
  ...MATCH_METRICS,
  ["stage_count", "Stages"],
  ["total_shots", "Shots"],
  ["competitor", "Competitor"],
]);

export function createIntroOutroPane({
  $ = (id) => document.getElementById(id),
  documentObject = document,
  windowObject = window,
  getState = () => null,
  callApi = async () => null,
  pickPath = async () => "",
  activity = () => {},
  fileName = (value) => String(value || ""),
  buildMediaUrl = (url) => url,
  containedMediaFrameClientRect = () => null,
} = {}) {
  let selectedKind = "intro";
  const draftClips = new Map();
  const draftVersions = { intro: 0, outro: 0 };
  const saveRevisions = { intro: 0, outro: 0 };
  const saveChains = { intro: Promise.resolve(), outro: Promise.resolve() };
  const playbackTimes = { intro: 0, outro: 0 };
  let boundaryDrag = null;

  function state() {
    return getState() || {};
  }

  function project() {
    return state().project || {};
  }

  function storedClip(kind = selectedKind) {
    return project()?.[`${kind}_clip`] || { asset: {}, overlay: {} };
  }

  function clip(kind = selectedKind) {
    return draftClips.get(kind) || storedClip(kind);
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
      score_time: metrics.display_value || "",
      raw_time: metrics.raw_time_ms == null ? "" : `${(Number(metrics.raw_time_ms) / 1000).toFixed(2)}s`,
      stage_count: metrics.stage_count || "",
      total_shots: metrics.total_shots || "",
      points_down: Number(metrics.points_down || 0).toString(),
      penalties: Number(metrics.total_penalties || 0).toString(),
      competitor: metrics.competitor || scoring.competitor_name || "",
      division_placement: [
        metrics.division || scoring.division || "",
        metrics.division_placement || "",
      ].filter(Boolean).join(" - "),
      class_placement: [
        metrics.classification || scoring.classification || "",
        metrics.class_placement || "",
      ].filter(Boolean).join(" - "),
      overall_placement: metrics.overall_placement || "",
    };
    return String(values[metricId] ?? "");
  }

  function normalizedMatchMetricIds(metricIds = []) {
    return [...new Set(metricIds.map((id) => LEGACY_MATCH_METRIC_IDS[id] || id))];
  }

  function boxDisplayText(box) {
    if (box.source !== "match_summary") return String(box.text || "");
    const requested = Array.isArray(box.summary_metric_ids) && box.summary_metric_ids.length
      ? normalizedMatchMetricIds(box.summary_metric_ids)
      : DEFAULT_MATCH_METRICS;
    const resultLabel = String(state().match_metrics?.result_label || "Final");
    return MATCH_RENDER_METRICS
      .filter(([id]) => requested.includes(id) && matchValue(id))
      .map(([id, label]) => `${id === "score_time" ? resultLabel : label} ${matchValue(id)}`)
      .join("\n");
  }

  function previewOutputSize() {
    const media = clip()?.asset || {};
    return {
      width: Math.max(1, Number(media.width || 1920)),
      height: Math.max(1, Number(media.height || 1080)),
    };
  }

  function colorWithOpacity(color, opacity) {
    const value = String(color || "#000000").replace(/^#/, "");
    const expanded = value.length === 3 ? value.split("").map((part) => `${part}${part}`).join("") : value;
    const parsed = Number.parseInt(expanded, 16);
    if (!Number.isFinite(parsed)) return `rgba(0, 0, 0, ${opacity})`;
    return `rgba(${(parsed >> 16) & 255}, ${(parsed >> 8) & 255}, ${parsed & 255}, ${opacity})`;
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

  function editableClip(kind = selectedKind) {
    const currentDraft = draftClips.get(kind);
    if (currentDraft) return currentDraft;
    const current = storedClip(kind);
    const draft = {
      ...current,
      asset: { ...(current.asset || {}) },
      overlay: {
        ...(current.overlay || {}),
        text_boxes: (Array.isArray(current?.overlay?.text_boxes) ? current.overlay.text_boxes : []).map(normalizedBox),
      },
    };
    draftClips.set(kind, draft);
    return draft;
  }

  function setDraftBoxes(kind, nextBoxes) {
    const draft = editableClip(kind);
    draft.overlay = { ...(draft.overlay || {}), text_boxes: nextBoxes.map(normalizedBox) };
    draftClips.set(kind, draft);
    draftVersions[kind] += 1;
  }

  function queueSave(kind, path, payload) {
    const video = $("primary-video");
    if (kind === selectedKind && video && Number.isFinite(video.currentTime)) {
      playbackTimes[kind] = video.currentTime;
    }
    const revision = ++saveRevisions[kind];
    const draftVersion = draftVersions[kind];
    saveChains[kind] = saveChains[kind]
      .catch(() => null)
      .then(() => callApi(path, payload));
    return saveChains[kind].then((result) => {
      if (saveRevisions[kind] === revision && draftVersions[kind] === draftVersion) {
        draftClips.delete(kind);
        render();
        restorePlaybackTime(kind);
      }
      return result;
    });
  }

  function restorePlaybackTime(kind = selectedKind) {
    if (kind !== selectedKind) return;
    const video = $("primary-video");
    const target = Number(playbackTimes[kind] || 0);
    if (!video || target <= 0) return;
    const apply = () => {
      if (Number.isFinite(video.duration)) video.currentTime = Math.min(target, video.duration);
    };
    if (video.readyState >= HTMLMediaElement.HAVE_METADATA) apply();
    else video.addEventListener("loadedmetadata", apply, { once: true });
  }

  async function saveBoxes(nextBoxes, kind = selectedKind) {
    const currentBoxes = boxes(kind).map(normalizedBox);
    const normalizedBoxes = nextBoxes.map(normalizedBox);
    const controlsChanged = currentBoxes.length !== normalizedBoxes.length
      || currentBoxes.some((box, index) => box.source !== normalizedBoxes[index]?.source);
    setDraftBoxes(kind, normalizedBoxes);
    if (kind === selectedKind) {
      if (controlsChanged) render({ force: true });
      else updatePreview();
    }
    activity("intro-outro.overlay.update", { kind, count: normalizedBoxes.length });
    await queueSave(kind, "/api/project/intro-outro/overlay", {
      kind,
      text_boxes: normalizedBoxes,
    });
  }

  async function saveFades() {
    const kind = selectedKind;
    const draft = editableClip(kind);
    draft.fade_in_s = Math.max(0, Number($("intro-outro-fade-in")?.value || 0));
    draft.fade_out_s = Math.max(0, Number($("intro-outro-fade-out")?.value || 0));
    draftVersions[kind] += 1;
    await queueSave(kind, "/api/project/intro-outro/fades", {
      kind,
      fade_in_s: draft.fade_in_s,
      fade_out_s: draft.fade_out_s,
    });
  }

  async function selectVideo(kind) {
    const electronPicker = windowObject.splitshot?.openInOutVideoDialog;
    const path = typeof electronPicker === "function"
      ? await electronPicker()
      : await pickPath("in_out_media", null);
    if (!path) return;
    selectedKind = kind;
    const result = await callApi("/api/project/in-out/media", { kind, path });
    if (result) {
      draftClips.delete(kind);
      render({ force: true });
      updatePreview();
    }
  }

  function updatePreview() {
    const pane = $("intro-outro-pane");
    if (!pane?.classList.contains("active")) return;
    const video = $("primary-video");
    const path = clip()?.asset?.path || "";
    if (video && !path) {
      video.pause();
      video.removeAttribute("src");
      delete video.dataset.sourcePath;
      delete video.dataset.mediaUrl;
      video.load();
    } else if (video) {
      const mediaUrl = buildMediaUrl(`/media/${selectedKind}`, path);
      if (video.dataset.sourcePath !== path || video.dataset.mediaUrl !== mediaUrl) {
        video.dataset.sourcePath = path;
        video.dataset.mediaUrl = mediaUrl;
        video.src = mediaUrl;
        video.addEventListener("loadedmetadata", updatePreview, { once: true });
        video.load();
      }
    }
    if (video) video.hidden = !path;
    $("secondary-video")?.setAttribute("hidden", "");
    $("secondary-image")?.setAttribute("hidden", "");
    const liveOverlay = $("live-overlay");
    if (liveOverlay) liveOverlay.innerHTML = "";
    const overlay = $("custom-overlay");
    if (!overlay) return;
    const stage = $("video-stage");
    const frame = frameRect();
    const stageRect = stage?.getBoundingClientRect();
    if (frame && stageRect) {
      overlay.style.inset = "auto";
      overlay.style.left = `${frame.left - stageRect.left}px`;
      overlay.style.top = `${frame.top - stageRect.top}px`;
      overlay.style.width = `${frame.width}px`;
      overlay.style.height = `${frame.height}px`;
    }
    const outputSize = previewOutputSize();
    const scaleX = Math.max(0.01, Number(frame?.width || 1) / outputSize.width);
    const scaleY = Math.max(0.01, Number(frame?.height || 1) / outputSize.height);
    const fontScale = Math.min(scaleX, scaleY);
    const margin = Math.max(0, Number(clip()?.overlay?.margin ?? project()?.overlay?.margin ?? 20));
    const visibleBoxes = boxes()
      .map((box, index) => ({ box, index }))
      .filter(({ box }) => box.enabled && boxDisplayText(box).trim());
    const structureKey = visibleBoxes
      .map(({ box }) => `${selectedKind}:${normalizedBox(box).id}`)
      .join("|");
    if (overlay.dataset.introOutroStructureKey !== structureKey) {
      overlay.innerHTML = "";
      visibleBoxes.forEach(() => {
        const badge = documentObject.createElement("div");
        badge.className = "overlay-badge intro-outro-preview-badge";
        badge.dataset.introOutroBoxDrag = "true";
        badge.dataset.textBoxDrag = "true";
        badge.addEventListener("pointerdown", beginBoundaryDrag);
        overlay.appendChild(badge);
      });
      overlay.dataset.introOutroStructureKey = structureKey;
    }
    visibleBoxes.forEach(({ box, index }, visibleIndex) => {
      const badge = overlay.children[visibleIndex];
      if (!(badge instanceof HTMLElement)) return;
      badge.dataset.boxIndex = String(index);
      badge.dataset.boundaryKind = selectedKind;
      badge.textContent = boxDisplayText(box);
      badge.style.background = colorWithOpacity(box.background_color, Number(box.opacity ?? 0.9));
      badge.style.color = box.text_color || "#ffffff";
      badge.style.opacity = "1";
      badge.style.fontSize = `${Math.max(1, Number(box.font_size || 28) * fontScale)}px`;
      badge.style.fontFamily = box.font_family || "Arial";
      badge.style.fontWeight = box.font_bold === false ? "400" : "700";
      badge.style.fontStyle = box.font_italic ? "italic" : "normal";
      badge.style.borderRadius = box.style_type === "rounded" ? `${10 * fontScale}px` : box.style_type === "bubble" ? "999px" : "0";
      badge.style.boxSizing = "border-box";
      badge.style.lineHeight = "normal";
      badge.style.padding = `${5 * scaleY}px ${10 * scaleX}px`;
      badge.style.width = box.width ? `${Number(box.width) * scaleX}px` : "auto";
      badge.style.height = box.height ? `${Number(box.height) * scaleY}px` : "auto";
      badge.style.transform = "none";
      const badgeWidth = badge.getBoundingClientRect().width;
      const badgeHeight = badge.getBoundingClientRect().height;
      const frameWidth = Number(frame?.width || 1);
      const frameHeight = Number(frame?.height || 1);
      const [vertical, horizontal] = String(box.quadrant || "top_right").split("_");
      let left = box.quadrant === "custom"
        ? (Number(box.x ?? 0.5) * frameWidth) - (badgeWidth / 2)
        : horizontal === "left" ? margin * scaleX
          : horizontal === "middle" ? (frameWidth - badgeWidth) / 2
            : frameWidth - badgeWidth - (margin * scaleX);
      let top = box.quadrant === "custom"
        ? (Number(box.y ?? 0.5) * frameHeight) - (badgeHeight / 2)
        : vertical === "top" ? margin * scaleY
          : vertical === "middle" ? (frameHeight - badgeHeight) / 2
            : frameHeight - badgeHeight - (margin * scaleY);
      left = Math.max(0, Math.min(left, Math.max(0, frameWidth - badgeWidth)));
      top = Math.max(0, Math.min(top, Math.max(0, frameHeight - badgeHeight)));
      badge.style.left = `${left}px`;
      badge.style.top = `${top}px`;
    });
    overlay.classList.toggle("has-badge", overlay.childElementCount > 0);
  }

  function metricChecklist(box, index) {
    if (box.source !== "match_summary") return "";
    const selected = box.summary_metric_ids?.length
      ? normalizedMatchMetricIds(box.summary_metric_ids)
      : DEFAULT_MATCH_METRICS;
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
      <div class="control-grid"><label>Opacity %<input class="opacity-percent-input" data-box-field="opacity" type="number" min="0" max="100" value="${Math.round(Number(box.opacity ?? 0.9) * 100)}" /></label><div><label class="check-row"><input data-box-field="font_bold" type="checkbox" ${box.font_bold ? "checked" : ""} /> Bold</label><label class="check-row"><input data-box-field="font_italic" type="checkbox" ${box.font_italic ? "checked" : ""} /> Italic</label></div></div>
    </article>`;
  }

  function render({ force = false } = {}) {
    const pane = $("intro-outro-pane");
    if (!pane) return;
    const selectedClip = clip();
    const shell = pane.querySelector(".intro-outro-shell");
    if (!force && shell?.dataset.renderedBoundaryKind === selectedKind) {
      updatePreview();
      return;
    }
    const focused = documentObject.activeElement;
    if (!force && focused instanceof HTMLElement && pane.contains(focused) && focused.matches("input, select, textarea")) {
      updatePreview();
      return;
    }
    const path = selectedClip?.asset?.path || "";
    pane.innerHTML = `<div class="pane-section intro-outro-shell" data-rendered-boundary-kind="${selectedKind}">
      <div class="section-header pane-title-row"><h3>Intro / Outro</h3><span class="pane-status-text">Match media</span></div>
      <div class="button-grid two-up intro-outro-kind-tabs"><button type="button" data-boundary-kind="intro" class="${selectedKind === "intro" ? "active" : ""}">Intro</button><button type="button" data-boundary-kind="outro" class="${selectedKind === "outro" ? "active" : ""}">Outro</button></div>
      <section class="settings-section"><div class="section-header"><strong>${selectedKind === "intro" ? "Intro" : "Outro"} Video</strong></div><button id="intro-outro-select-video" class="btn btn-primary" type="button">${path ? "Replace Video" : "Select Video"}</button><small class="intro-outro-file">${path ? escapeHtml(fileName(path)) : "No video selected"}</small><div class="control-grid"><label>Fade in (seconds)<input id="intro-outro-fade-in" type="number" min="0" step="0.1" value="${Number(selectedClip.fade_in_s ?? 0.5)}" /></label><label>Fade out (seconds)<input id="intro-outro-fade-out" type="number" min="0" step="0.1" value="${Number(selectedClip.fade_out_s ?? 0.5)}" /></label></div></section>
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
      if (kindButton) {
        const video = $("primary-video");
        if (video && Number.isFinite(video.currentTime)) playbackTimes[selectedKind] = video.currentTime;
        selectedKind = kindButton.dataset.boundaryKind || "intro";
        render({ force: true });
        restorePlaybackTime(selectedKind);
        return;
      }
      if (target.closest("#intro-outro-select-video")) { await selectVideo(selectedKind); return; }
      if (target.closest("#intro-outro-add-text")) { await saveBoxes([...boxes(), normalizedBox({ source: "manual", text: "Title" })]); return; }
      if (target.closest("#intro-outro-add-match")) { await saveBoxes([...boxes(), normalizedBox({ source: "match_summary", summary_metric_ids: [...DEFAULT_MATCH_METRICS], quadrant: "top_right" })]); return; }
      const remove = target.closest("[data-remove-box]");
      if (remove) await saveBoxes(boxes().filter((_box, index) => index !== Number(remove.dataset.removeBox)));
    };
    pane.onchange = async (event) => {
      const target = event.target instanceof HTMLInputElement || event.target instanceof HTMLSelectElement || event.target instanceof HTMLTextAreaElement ? event.target : null;
      if (!target) return;
      if (target.matches("#intro-outro-fade-in, #intro-outro-fade-out")) {
        await saveFades();
        return;
      }
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
    pane.oninput = (event) => {
      const target = event.target instanceof HTMLInputElement || event.target instanceof HTMLTextAreaElement ? event.target : null;
      if (!target || target.matches("#intro-outro-fade-in, #intro-outro-fade-out")) return;
      const card = target.closest("[data-box-index]");
      if (!card || !target.dataset.boxField) return;
      const index = Number(card.dataset.boxIndex);
      const next = boxes().map(normalizedBox);
      const field = target.dataset.boxField;
      let value = target.type === "checkbox" ? target.checked : target.value;
      if (["font_size", "width", "height", "x", "y"].includes(field)) value = Number(value);
      if (field === "opacity") value = Number(value) / 100;
      next[index][field] = value;
      setDraftBoxes(selectedKind, next);
      updatePreview();
    };
  }

  function frameRect() {
    const stage = $("video-stage");
    if (!stage) return null;
    const media = clip()?.asset || {};
    return containedMediaFrameClientRect(
      $("primary-video"),
      stage,
      media.width,
      media.height,
    ) || stage.getBoundingClientRect();
  }

  function beginBoundaryDrag(event) {
    if (event.button !== 0) return;
    const badge = event.currentTarget instanceof HTMLElement ? event.currentTarget : null;
    const rect = frameRect();
    if (!badge || !rect || rect.width <= 0 || rect.height <= 0) return;
    const index = Number(badge.dataset.boxIndex);
    const kind = badge.dataset.boundaryKind || selectedKind;
    const box = boxes(kind)[index];
    if (!box) return;
    const badgeRect = badge.getBoundingClientRect();
    event.preventDefault();
    event.stopPropagation();
    boundaryDrag = {
      kind,
      index,
      pointerId: event.pointerId,
      startClientX: event.clientX,
      startClientY: event.clientY,
      startX: Math.max(0, Math.min(1, (badgeRect.left - rect.left + (badgeRect.width / 2)) / rect.width)),
      startY: Math.max(0, Math.min(1, (badgeRect.top - rect.top + (badgeRect.height / 2)) / rect.height)),
      badge,
    };
    badge.setPointerCapture?.(event.pointerId);
    $("custom-overlay")?.classList.add("dragging");
  }

  function moveBoundaryDrag(event) {
    if (!boundaryDrag || (event.pointerId !== undefined && event.pointerId !== boundaryDrag.pointerId)) return;
    const rect = frameRect();
    if (!rect || rect.width <= 0 || rect.height <= 0) return;
    const next = boxes(boundaryDrag.kind).map(normalizedBox);
    const box = next[boundaryDrag.index];
    if (!box) return;
    box.quadrant = "custom";
    box.x = Math.max(0, Math.min(1, boundaryDrag.startX + ((event.clientX - boundaryDrag.startClientX) / rect.width)));
    box.y = Math.max(0, Math.min(1, boundaryDrag.startY + ((event.clientY - boundaryDrag.startClientY) / rect.height)));
    setDraftBoxes(boundaryDrag.kind, next);
    if (boundaryDrag.kind === selectedKind) updatePreview();
  }

  function endBoundaryDrag(event) {
    if (!boundaryDrag || (event.pointerId !== undefined && event.pointerId !== boundaryDrag.pointerId)) return;
    const { kind, pointerId, badge } = boundaryDrag;
    boundaryDrag = null;
    if (badge?.hasPointerCapture?.(pointerId)) badge.releasePointerCapture(pointerId);
    $("custom-overlay")?.classList.remove("dragging");
    void saveBoxes(boxes(kind), kind);
  }

  documentObject.addEventListener("pointermove", moveBoundaryDrag);
  documentObject.addEventListener("pointerup", endBoundaryDrag);
  documentObject.addEventListener("pointercancel", endBoundaryDrag);
  windowObject.addEventListener("blur", endBoundaryDrag);

  return Object.freeze({ render, updatePreview, selectedKind: () => selectedKind });
}
