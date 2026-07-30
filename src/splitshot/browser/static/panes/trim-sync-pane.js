export function createTrimSyncPane({
  $ = (id) => document.getElementById(id),
  documentObject = document,
  getState = () => null,
  withPreservedScrollState = (_elements, callback) => callback(),
  activity = () => {},
  callApi = async () => null,
  scheduleInteractionPreviewRender = () => {},
  renderVideo = () => {},
  setStatus = () => {},
  fileName = (value) => String(value || ""),
  sourceIdentifier = (source, fallback) => String(source?.id || fallback || ""),
  currentSourceSyncOffsetMs = (source) => Math.round(Number(source?.sync_offset_ms) || 0),
} = {}) {
  const PRIMARY_SOURCE_ID = "__primary__";
  const sectionExpansion = new Map([
    ["bulk", true],
    ["sources", true],
  ]);
  const trimUndoHistory = [];
  let restoringUndo = false;
  let keepBeforeBeepS = 2;
  let keepAfterLastShotS = 2;
  let transportActive = false;
  let transportVideo = null;
  let stageSelectionInitialized = false;
  let knownTrimStageIds = new Set();
  const selectedTrimStageIds = new Set();

  function currentState() {
    return getState() || {};
  }

  function htmlEscape(value) {
    return String(value || "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;");
  }

  function isExpanded(sectionId) {
    return sectionExpansion.get(sectionId) !== false;
  }

  function primaryVideo() {
    return currentState()?.project?.primary_video || {};
  }

  function beepTimeMs() {
    return currentState()?.project?.analysis?.beep_time_ms_primary ?? null;
  }

  function primaryTrimOffsetMs() {
    const trim = currentState()?.project?.primary_trim_derivative || {};
    return trim?.active_path_kind === "local_derivative" && trim?.derivative_path
      ? Math.round((Number(trim.start_s) || 0) * 1000)
      : 0;
  }

  function originalBeepTimeMs() {
    const beep = beepTimeMs();
    return beep === null ? null : beep + primaryTrimOffsetMs();
  }

  function lastShotTimeMs() {
    const shots = currentState()?.project?.analysis?.shots || [];
    if (!shots.length) return null;
    return Math.max(...shots.map((shot) => shot.time_ms ?? 0));
  }

  function originalLastShotTimeMs() {
    const lastShot = lastShotTimeMs();
    return lastShot === null ? null : lastShot + primaryTrimOffsetMs();
  }

  function mergeSources() {
    return currentState()?.project?.merge_sources || [];
  }

  function primaryTrimSource() {
    const primary = primaryVideo();
    if (!primary?.path) return null;
    return {
      id: PRIMARY_SOURCE_ID,
      asset: {
        ...primary,
        path: primary.original_path || primary.path || "",
      },
      trim_derivative: currentState()?.project?.primary_trim_derivative || {},
      effective_media_path: primary.effective_media_path || primary.path || "",
      trim_active: Boolean(primary.trim_active),
      active_display_name: primary.active_display_name || fileName(primary.effective_media_path || primary.path || ""),
      original_display_name: primary.original_display_name || fileName(primary.path || ""),
      active_duration_ms: primary.active_duration_ms ?? primary.duration_ms ?? 0,
      active_width: primary.active_width ?? primary.width ?? 0,
      active_height: primary.active_height ?? primary.height ?? 0,
      active_media_kind: primary.active_media_kind || primary.media_kind || "video",
      supports_sync_analysis: false,
      sync_offset_ms: 0,
      is_primary_source: true,
    };
  }

  function stageSources() {
    const primary = primaryTrimSource();
    return primary ? [primary, ...mergeSources()] : mergeSources();
  }

  function trimmableStages() {
    const project = currentState()?.project || {};
    return (project.stages || [])
      .map((stage) => (
        stage?.id === project.active_stage_id && !stage?.primary_media?.path && project.primary_video?.path
          ? {
              ...stage,
              primary_media: project.primary_video,
              added_media: project.merge_sources || stage.added_media || [],
            }
          : stage
      ))
      .filter((stage) => Boolean(stage?.primary_media?.path));
  }

  function syncTrimStageSelection() {
    const stages = trimmableStages();
    const currentIds = new Set(stages.map((stage) => String(stage.id || "")));
    [...selectedTrimStageIds].forEach((stageId) => {
      if (!currentIds.has(stageId)) selectedTrimStageIds.delete(stageId);
    });
    if (!stageSelectionInitialized) {
      stages.forEach((stage) => selectedTrimStageIds.add(String(stage.id || "")));
      stageSelectionInitialized = true;
    } else {
      stages.forEach((stage) => {
        const stageId = String(stage.id || "");
        if (stageId && !knownTrimStageIds.has(stageId)) selectedTrimStageIds.add(stageId);
      });
    }
    knownTrimStageIds = currentIds;
    return stages;
  }

  function updateTrimStageSelectionSummary() {
    const output = $("trim-stage-selection-count");
    if (output) {
      const count = selectedTrimStageIds.size;
      output.textContent = `${count} selected`;
    }
  }

  function formatSeconds(value) {
    if (value === null || value === undefined) return "--.--";
    return Number(value).toFixed(2);
  }

  function formatTime(value) {
    const numeric = Number(value);
    return `${(Number.isFinite(numeric) ? numeric : 0).toFixed(2)}s`;
  }

  function syncTransport() {
    const video = $("primary-video");
    if (!video) return;
    const duration = Number.isFinite(video.duration) ? video.duration : 0;
    const stateDuration = Number(primaryVideo()?.active_duration_ms ?? primaryVideo()?.duration_ms) / 1000;
    const displayDuration = Number.isFinite(stateDuration) && stateDuration > 0 ? stateDuration : duration;
    const current = Number.isFinite(video.currentTime) ? video.currentTime : 0;
    const scrubber = $("trim-video-scrubber");
    if (scrubber) {
      scrubber.max = String(duration);
      scrubber.value = String(Math.min(current, duration || current));
    }
    const readout = $("trim-video-time");
    if (readout) readout.textContent = `${formatTime(current)} / ${formatTime(displayDuration)}`;
    const toggle = $("trim-video-toggle");
    if (toggle) toggle.textContent = video.paused ? "Play" : "Pause";
  }

  function bindTransportVideo() {
    const video = $("primary-video");
    if (!video || transportVideo === video) return;
    transportVideo = video;
    ["timeupdate", "durationchange", "loadedmetadata", "play", "pause", "ended"].forEach((eventName) => {
      video.addEventListener(eventName, syncTransport);
    });
  }

  function setActive(active) {
    transportActive = Boolean(active);
    const video = $("primary-video");
    if (video) video.controls = !transportActive;
    if (transportActive) bindTransportVideo();
    syncTransport();
  }

  function sourceDurationMs(source) {
    return source?.asset?.duration_ms ?? primaryVideo()?.duration_ms ?? 0;
  }

  function sourceBeepTimeMs(source) {
    const primaryBeep = originalBeepTimeMs();
    if (primaryBeep === null) return null;
    return primaryBeep + currentSourceSyncOffsetMs(source);
  }

  function sourceLastShotTimeMs(source) {
    const primaryLastShot = originalLastShotTimeMs();
    if (primaryLastShot === null) return null;
    return primaryLastShot + currentSourceSyncOffsetMs(source);
  }

  function sourceTrimStartS(source) {
    const td = source?.trim_derivative;
    if (td?.start_s !== null && td?.start_s !== undefined) return td.start_s;
    const beep = sourceBeepTimeMs(source);
    if (beep !== null) return Math.max(0, (beep / 1000) - 2);
    return 0;
  }

  function sourceTrimEndS(source) {
    const td = source?.trim_derivative;
    if (td?.end_s !== null && td?.end_s !== undefined) return td.end_s;
    const lastShot = sourceLastShotTimeMs(source);
    const durMs = sourceDurationMs(source);
    if (lastShot !== null) {
      const bufferedEnd = (lastShot / 1000) + 2;
      return durMs ? Math.min(bufferedEnd, durMs / 1000) : bufferedEnd;
    }
    return durMs ? (durMs / 1000) : 0;
  }

  function computedTrimLabel(source) {
    const durMs = sourceDurationMs(source);
    const durS = durMs / 1000;
    const start = sourceTrimStartS(source);
    const end = sourceTrimEndS(source);
    const trimActive = source?.trim_derivative?.active_path_kind === "local_derivative"
      && source?.trim_derivative?.derivative_path;
    const kept = trimActive && Number(source?.active_duration_ms) > 0
      ? Number(source.active_duration_ms) / 1000
      : Math.max(0, end - start);
    return `Start ${formatSeconds(start)}s · End ${formatSeconds(end)}s · Duration ${formatSeconds(kept)}s`;
  }

  function sourceSyncStatusLabel(source = null) {
    if (!source?.supports_sync_analysis) return "";
    const status = String(source.sync_analysis_status || "idle");
    if (status === "running") return "Analyzing beep sync...";
    if (status === "ready") return `Beep ${Math.round(Number(source.secondary_beep_time_ms) || 0)} ms`;
    if (status === "no_beep") return "No beep detected.";
    return String(source.sync_analysis_message || "");
  }

  function formatSyncOffsetLabel(offsetMs) {
    const numeric = Math.round(Number(offsetMs) || 0);
    return `Sync ${numeric > 0 ? "+" : ""}${numeric} ms`;
  }

  function trimSourceSnapshot(source, fallbackId) {
    const nextSourceId = sourceIdentifier(source, fallbackId);
    return {
      source_id: nextSourceId,
      sync_offset_ms: currentSourceSyncOffsetMs(source),
      start_s: source?.trim_derivative?.start_s ?? null,
      end_s: source?.trim_derivative?.end_s ?? null,
      clear: !(
        source?.trim_derivative
        && source.trim_derivative.active_path_kind === "local_derivative"
        && source.trim_derivative.derivative_path
      ),
    };
  }

  function queueUndoSnapshot(kind, sourceId = null, stageIds = []) {
    if (restoringUndo) return;
    const selectedIds = new Set(stageIds);
    trimUndoHistory.push({
      kind,
      sourceId,
      snapshot: {
        active_stage_id: currentState()?.project?.active_stage_id || "",
        global_start: $("trim-global-start")?.value || "",
        global_end: $("trim-global-end")?.value || "",
        sources: stageSources().map((source, index) => trimSourceSnapshot(source, String(index))),
        stages: kind === "bulk"
          ? (currentState()?.project?.stages || [])
            .filter((stage) => selectedIds.has(String(stage.id || "")))
            .map((stage) => ({
              stage_id: String(stage.id || ""),
              sources: [
                {
                  id: PRIMARY_SOURCE_ID,
                  trim_derivative: stage.primary_trim_derivative || {},
                  sync_offset_ms: 0,
                },
                ...(Array.isArray(stage.added_media) ? stage.added_media : []),
              ].map((source, index) => trimSourceSnapshot(source, String(index))),
            }))
          : [],
      },
    });
    if (trimUndoHistory.length > 40) trimUndoHistory.shift();
  }

  function refreshTrimPreview() {
    scheduleInteractionPreviewRender({ video: true, waveform: true });
    renderVideo();
  }

  async function restoreSourceSnapshots(sources) {
    for (const source of sources) {
      if (source.source_id !== PRIMARY_SOURCE_ID) {
        await callApi("/api/merge/source", {
          source_id: source.source_id,
          sync_offset_ms: Math.round(Number(source.sync_offset_ms) || 0),
        });
        await callApi("/api/merge/source/trim", {
          source_id: source.source_id,
          clear: Boolean(source.clear),
          start_s: source.clear || source.start_s === null ? null : Number(source.start_s),
          end_s: source.clear || source.end_s === null ? null : Number(source.end_s),
        });
      } else {
        await callApi("/api/primary/trim", {
          clear: Boolean(source.clear),
          start_s: source.clear || source.start_s === null ? null : Number(source.start_s),
          end_s: source.clear || source.end_s === null ? null : Number(source.end_s),
        });
      }
    }
  }

  async function restoreTrimSnapshot(snapshot) {
    if (!snapshot || !Array.isArray(snapshot.sources)) return;
    restoringUndo = true;
    try {
      if (Array.isArray(snapshot.stages) && snapshot.stages.length) {
        for (const stage of snapshot.stages) {
          await callApi("/api/project/select-stage", {
            active_stage_id: stage.stage_id,
          });
          await restoreSourceSnapshots(stage.sources || []);
        }
        if (snapshot.active_stage_id) {
          await callApi("/api/project/select-stage", {
            active_stage_id: snapshot.active_stage_id,
          });
        }
      } else {
        await restoreSourceSnapshots(snapshot.sources);
      }
      if ($("trim-global-start")) $("trim-global-start").value = snapshot.global_start || "";
      if ($("trim-global-end")) $("trim-global-end").value = snapshot.global_end || "";
      const restoredBefore = parseFloat(snapshot.global_start || "");
      const restoredAfter = parseFloat(snapshot.global_end || "");
      if (Number.isFinite(restoredBefore) && restoredBefore >= 0) keepBeforeBeepS = restoredBefore;
      if (Number.isFinite(restoredAfter) && restoredAfter >= 0) keepAfterLastShotS = restoredAfter;
      refreshTrimPreview();
      setStatus("Restored trim changes.");
    } finally {
      restoringUndo = false;
    }
  }

  async function undoLastTrimChange(sourceId = null) {
    const index = sourceId
      ? [...trimUndoHistory].map((entry, idx) => ({ entry, idx })).reverse().find((item) => item.entry.sourceId === sourceId)?.idx
      : trimUndoHistory.length - 1;
    if (index === undefined || index < 0) {
      setStatus(sourceId ? "No source-level trim changes to undo." : "No trim changes to undo.");
      return;
    }
    const [entry] = trimUndoHistory.splice(index, 1);
    await restoreTrimSnapshot(entry?.snapshot);
  }

  async function trimAll(clear = false, { recordUndo = true } = {}) {
    const startInput = $("trim-global-start");
    const endInput = $("trim-global-end");
    const startValue = parseFloat(startInput?.value || "");
    const endValue = parseFloat(endInput?.value || "");
    if (!clear && Number.isFinite(startValue) && startValue >= 0) keepBeforeBeepS = startValue;
    if (!clear && Number.isFinite(endValue) && endValue >= 0) keepAfterLastShotS = endValue;
    const stageIds = [...selectedTrimStageIds];
    const legacyActiveMedia = stageIds.length === 0
      && (currentState()?.project?.stages || []).length === 0
      && Boolean(primaryVideo()?.path);
    if (stageIds.length === 0 && !legacyActiveMedia) {
      setStatus("Select at least one stage.");
      return;
    }
    const selectedCount = legacyActiveMedia ? 1 : stageIds.length;
    if (recordUndo) queueUndoSnapshot("bulk", null, stageIds);
    activity(clear ? "trim.clear-all" : "trim.apply-all", {
      keep_before_beep_s: startValue,
      keep_after_last_shot_s: endValue,
      stage_ids: stageIds,
    });
    setStatus(
      clear
        ? `Clearing trim for ${selectedCount} selected stage${selectedCount === 1 ? "" : "s"}...`
        : `Trimming ${selectedCount} selected stage${selectedCount === 1 ? "" : "s"}...`,
    );
    const request = {
      clear,
      keep_before_beep_s: clear || !Number.isFinite(startValue) || startValue < 0 ? null : startValue,
      keep_after_last_shot_s: clear || !Number.isFinite(endValue) || endValue < 0 ? null : endValue,
    };
    if (!legacyActiveMedia) request.stage_ids = stageIds;
    await callApi("/api/merge/source/trim-all", request);
    setStatus(
      `${clear ? "Cleared trim for" : "Trimmed"} ${selectedCount} selected stage`
      + `${selectedCount === 1 ? "" : "s"}.`,
    );
    refreshTrimPreview();
  }

  async function trimSource(sourceId, clear = false, { recordUndo = true } = {}) {
    const startInput = documentObject.querySelector(`[data-trim-start="${sourceId}"]`);
    const endInput = documentObject.querySelector(`[data-trim-end="${sourceId}"]`);
    const startValue = parseFloat(startInput?.value || "");
    const endValue = parseFloat(endInput?.value || "");
    if (recordUndo) queueUndoSnapshot("source", sourceId);
    activity(clear ? "trim.clear" : "trim.apply", { sourceId, start_s: startValue, end_s: endValue });
    setStatus(clear ? "Clearing trim derivative..." : "Trimming source...");
    if (sourceId === PRIMARY_SOURCE_ID) {
      await callApi("/api/primary/trim", {
        clear,
        start_s: clear || !Number.isFinite(startValue) || startValue <= 0 ? null : startValue,
        end_s: clear || !Number.isFinite(endValue) || endValue <= 0 ? null : endValue,
      });
    } else {
      await callApi("/api/merge/source/trim", {
        source_id: sourceId,
        clear,
        start_s: clear || !Number.isFinite(startValue) || startValue <= 0 ? null : startValue,
        end_s: clear || !Number.isFinite(endValue) || endValue <= 0 ? null : endValue,
      });
    }
    setStatus(clear ? "Cleared trim for source." : "Trimmed source.");
    refreshTrimPreview();
  }

  async function setSourceTrimToBeep(sourceId) {
    const source = stageSources().find((s) => sourceIdentifier(s, "") === sourceId) || null;
    const beep = source ? sourceBeepTimeMs(source) : null;
    if (beep === null) return;
    const input = documentObject.querySelector(`[data-trim-start="${sourceId}"]`);
    if (input) {
      input.value = (beep / 1000).toFixed(2);
      activity("trim.set-beep", { sourceId, start_s: beep / 1000 });
      await trimSource(sourceId, false, { recordUndo: true });
      setStatus("Set trim start to beep time.");
    }
  }

  async function setSourceTrimToLastShot(sourceId) {
    const source = stageSources().find((s) => sourceIdentifier(s, "") === sourceId) || null;
    const lastShot = source ? sourceLastShotTimeMs(source) : null;
    if (lastShot === null) return;
    const input = documentObject.querySelector(`[data-trim-end="${sourceId}"]`);
    if (input) {
      input.value = (lastShot / 1000).toFixed(2);
      activity("trim.set-last-shot", { sourceId, end_s: lastShot / 1000 });
      await trimSource(sourceId, false, { recordUndo: true });
      setStatus("Set trim end to last shot time.");
    }
  }

  function applyGlobalDefaults() {
    const startInput = $("trim-global-start");
    const endInput = $("trim-global-end");
    if (startInput) startInput.value = "2.00";
    if (endInput) endInput.value = "2.00";
    keepBeforeBeepS = 2;
    keepAfterLastShotS = 2;
    activity("trim.global-defaults", { keep_before_beep_s: 2, keep_after_last_shot_s: 2 });
    setStatus("Reset trim defaults to 2-second buffers.");
  }

  function buildSourceCard(source, index) {
    const asset = source.asset || source;
    const sourceId = sourceIdentifier(source, String(index));
    const trimDerivative = source.trim_derivative;
    const trimActive = trimDerivative && trimDerivative.active_path_kind === "local_derivative" && trimDerivative.derivative_path;
    const isTrimmable = !asset.is_still_image && asset.media_kind !== "animated_gif";
    const activePath = source?.effective_media_path || trimDerivative?.derivative_path || asset.path || "";
    const activeDisplayName = source?.active_display_name || fileName(activePath || asset.path || "");
    const startS = sourceTrimStartS(source);
    const endS = sourceTrimEndS(source);
    return `
      <article class="trim-source-card" data-source-id="${sourceId}">
        <div class="trim-source-card-header">
          <div class="trim-source-card-copy">
            <strong>${activeDisplayName}</strong>
            <small>${source.is_primary_source ? "Primary video" : `${asset.is_still_image ? "Image" : "Video"} · ${formatSyncOffsetLabel(currentSourceSyncOffsetMs(source))}`}</small>
          </div>
        </div>
        <div class="trim-source-card-body">
          <div class="trim-active-path-row">
            <small class="trim-active-path-state">${trimActive ? "Using trimmed media" : "Using original"}</small>
          </div>
          <small class="trim-computed-label">${isTrimmable ? computedTrimLabel(source) : "Still image • Trim not applicable"}</small>
          <div class="trim-card-row">
            <label class="merge-source-field">
              <span>Start</span>
              <input type="number" min="0" step="0.01" value="${formatSeconds(startS)}" data-trim-start="${sourceId}" ${isTrimmable ? "" : "disabled"} />
            </label>
            <label class="merge-source-field">
              <span>End</span>
              <input type="number" min="0" step="0.01" value="${formatSeconds(endS)}" data-trim-end="${sourceId}" ${isTrimmable ? "" : "disabled"} />
            </label>
            <div class="trim-card-actions">
              <button type="button" class="btn-sm btn-primary trim-apply-btn" data-source-id="${sourceId}" ${isTrimmable ? "" : "disabled"}>Apply</button>
              <button type="button" class="btn-sm btn-secondary trim-clear-btn" data-source-id="${sourceId}">Clear</button>
              <button type="button" class="btn-sm btn-secondary trim-undo-btn" data-source-id="${sourceId}">Undo</button>
            </div>
          </div>
          <div class="trim-card-row trim-card-row-quick">
            <button type="button" class="btn-sm btn-secondary trim-beep-btn" data-source-id="${sourceId}" ${isTrimmable ? "" : "disabled"}>Start at Beep</button>
            <button type="button" class="btn-sm btn-secondary trim-last-shot-btn" data-source-id="${sourceId}" ${isTrimmable ? "" : "disabled"}>End at Last Shot</button>
          </div>
          ${source.is_primary_source ? "" : `<div class="trim-card-row trim-card-row-sync">
            <label class="merge-source-field trim-sync-offset-field">
              <span>Offset ms</span>
              <input type="number" class="trim-sync-offset-input" step="1" value="${currentSourceSyncOffsetMs(source)}" data-source-sync-offset="${sourceId}" />
            </label>
            <div class="trim-sync-nudge-buttons">
              <button type="button" class="btn-sm btn-secondary" data-sync-delta="-10" data-source-id="${sourceId}">-10</button>
              <button type="button" class="btn-sm btn-secondary" data-sync-delta="-1" data-source-id="${sourceId}">-1</button>
              <button type="button" class="btn-sm btn-secondary" data-sync-delta="1" data-source-id="${sourceId}">+1</button>
              <button type="button" class="btn-sm btn-secondary" data-sync-delta="10" data-source-id="${sourceId}">+10</button>
            </div>
            <div class="trim-card-actions">
              ${source.supports_sync_analysis
                ? `<button type="button" class="btn-sm btn-secondary trim-analyze-btn" data-source-id="${sourceId}" ${source.sync_analysis_status === "running" ? "disabled" : ""}>${source.sync_analysis_status === "ready" ? "Re-run Sync" : "Analyze Sync"}</button>`
                : ""}
            </div>
          </div>
          <small class="merge-source-sync-hint">${source.supports_sync_analysis ? sourceSyncStatusLabel(source) : formatSyncOffsetLabel(currentSourceSyncOffsetMs(source))}</small>`}
        </div>
      </article>
    `;
  }

  function renderSectionHeader(title, sectionId, detail = "") {
    const expanded = isExpanded(sectionId);
    return `
      <div class="section-header trim-section-header">
        <strong>${title}</strong>
        <div class="section-header-actions">
          ${detail ? `<small>${detail}</small>` : ""}
          <button type="button" class="pane-toggle" data-trim-toggle="${sectionId}" aria-label="${expanded ? "Collapse" : "Expand"} ${title}">${expanded ? "v" : ">"}</button>
        </div>
      </div>
    `;
  }

  function bindEvents() {
    $("trim-video-toggle")?.addEventListener("click", async () => {
      const video = $("primary-video");
      if (!video) return;
      if (video.paused) await video.play();
      else video.pause();
      syncTransport();
    });
    $("trim-video-scrubber")?.addEventListener("input", (event) => {
      const video = $("primary-video");
      if (!video) return;
      video.currentTime = Number(event.currentTarget.value) || 0;
      syncTransport();
    });
    documentObject.querySelectorAll("[data-trim-toggle]").forEach((button) => {
      button.addEventListener("click", () => {
        const sectionId = button.dataset.trimToggle || "";
        sectionExpansion.set(sectionId, !isExpanded(sectionId));
        renderTrimSyncList();
      });
    });
    $("trim-global-apply")?.addEventListener("click", () => trimAll(false));
    $("trim-global-clear")?.addEventListener("click", () => trimAll(true));
    $("trim-global-undo")?.addEventListener("click", () => undoLastTrimChange());
    $("trim-global-defaults-btn")?.addEventListener("click", applyGlobalDefaults);
    $("trim-stage-select-all")?.addEventListener("click", () => {
      trimmableStages().forEach((stage) => selectedTrimStageIds.add(String(stage.id || "")));
      documentObject.querySelectorAll("[data-trim-stage-id]").forEach((input) => {
        input.checked = true;
      });
      updateTrimStageSelectionSummary();
    });
    $("trim-stage-clear")?.addEventListener("click", () => {
      selectedTrimStageIds.clear();
      documentObject.querySelectorAll("[data-trim-stage-id]").forEach((input) => {
        input.checked = false;
      });
      updateTrimStageSelectionSummary();
    });
    documentObject.querySelectorAll("[data-trim-stage-id]").forEach((input) => {
      input.addEventListener("change", () => {
        const stageId = input.dataset.trimStageId || "";
        if (input.checked) selectedTrimStageIds.add(stageId);
        else selectedTrimStageIds.delete(stageId);
        updateTrimStageSelectionSummary();
      });
    });
    documentObject.querySelectorAll(".trim-apply-btn").forEach((button) => {
      button.addEventListener("click", () => {
        trimSource(button.dataset.sourceId || "", false);
      });
    });
    documentObject.querySelectorAll(".trim-clear-btn").forEach((button) => {
      button.addEventListener("click", () => {
        trimSource(button.dataset.sourceId || "", true);
      });
    });
    documentObject.querySelectorAll(".trim-undo-btn").forEach((button) => {
      button.addEventListener("click", () => {
        undoLastTrimChange(button.dataset.sourceId || "");
      });
    });
    documentObject.querySelectorAll(".trim-beep-btn").forEach((button) => {
      button.addEventListener("click", () => {
        setSourceTrimToBeep(button.dataset.sourceId || "");
      });
    });
    documentObject.querySelectorAll(".trim-last-shot-btn").forEach((button) => {
      button.addEventListener("click", () => {
        setSourceTrimToLastShot(button.dataset.sourceId || "");
      });
    });
    documentObject.querySelectorAll("[data-source-sync-offset]").forEach((input) => {
      input.addEventListener("change", async () => {
        const sourceId = input.dataset.sourceSyncOffset || "";
        const offsetMs = Math.round(Number(input.value) || 0);
        queueUndoSnapshot("source", sourceId);
        activity("trim.sync.set", { sourceId, offset_ms: offsetMs });
        await callApi("/api/merge/source", { source_id: sourceId, sync_offset_ms: offsetMs });
        setStatus(`Updated sync offset to ${offsetMs > 0 ? "+" : ""}${offsetMs} ms.`);
        refreshTrimPreview();
      });
    });
    documentObject.querySelectorAll("[data-sync-delta]").forEach((button) => {
      button.addEventListener("click", async () => {
        const sourceId = button.dataset.sourceId || "";
        const deltaMs = Math.round(Number(button.dataset.syncDelta) || 0);
        queueUndoSnapshot("source", sourceId);
        activity("trim.sync.nudge", { sourceId, delta_ms: deltaMs });
        await callApi("/api/merge/source", { source_id: sourceId, sync_delta_ms: deltaMs });
        setStatus(`Nudged sync offset by ${deltaMs > 0 ? "+" : ""}${deltaMs} ms.`);
        refreshTrimPreview();
      });
    });
    documentObject.querySelectorAll(".trim-analyze-btn").forEach((button) => {
      button.addEventListener("click", async () => {
        const sourceId = button.dataset.sourceId || "";
        queueUndoSnapshot("source", sourceId);
        activity("trim.sync.analyze", { sourceId });
        await callApi("/api/merge/source/analyze", { source_id: sourceId });
        setStatus("Sync analysis started.");
        refreshTrimPreview();
      });
    });
  }

  function renderTrimSyncList() {
    const pane = documentObject.querySelector('[data-tool-pane="trim-sync"]');
    if (!pane) return;
    const sources = stageSources();
    const stages = syncTrimStageSelection();
    const existingList = $("trim-sync-list");
    withPreservedScrollState(existingList ? [existingList] : [], () => {
      pane.innerHTML = `
        <div class="pane-section trim-pane-shell">
          <div class="section-header pane-title-row">
            <h3>Trim</h3>
            <span class="pane-status-text">${sources.length} source${sources.length === 1 ? "" : "s"}</span>
          </div>
          <div class="settings-section trim-pane-section ${isExpanded("bulk") ? "" : "collapsed"}" data-trim-section="bulk">
            ${renderSectionHeader("Bulk Trim", "bulk")}
            <div class="trim-pane-section-body"${isExpanded("bulk") ? "" : " hidden"}>
              <div class="trim-stage-selector">
                <div class="trim-stage-selector-header">
                  <strong>Stages</strong>
                  <div class="trim-stage-selector-actions">
                    <small id="trim-stage-selection-count">${selectedTrimStageIds.size} selected</small>
                    <button id="trim-stage-select-all" type="button" class="btn-sm btn-secondary">Select All</button>
                    <button id="trim-stage-clear" type="button" class="btn-sm btn-secondary">Clear</button>
                  </div>
                </div>
                <div class="trim-stage-checklist">
                  ${stages.map((stage) => {
                    const stageId = String(stage.id || "");
                    const sourceCount = 1 + (Array.isArray(stage.added_media) ? stage.added_media.length : 0);
                    return `<label class="check-row trim-stage-option">
                      <input type="checkbox" data-trim-stage-id="${stageId}" ${selectedTrimStageIds.has(stageId) ? "checked" : ""} />
                      <span>${htmlEscape(stage.label || "Stage")} · ${sourceCount} source${sourceCount === 1 ? "" : "s"}</span>
                    </label>`;
                  }).join("")}
                </div>
              </div>
              <div class="trim-transport" aria-label="Trim video transport">
                <button id="trim-video-toggle" type="button" class="btn-sm btn-secondary">Play</button>
                <input id="trim-video-scrubber" type="range" min="0" max="0" step="0.01" value="0" aria-label="Trim video position" />
                <output id="trim-video-time">0.00s / 0.00s</output>
              </div>
              <div class="trim-global-row">
              <label class="merge-source-field">
                <span>Before beep</span>
                <input id="trim-global-start" type="number" min="0" step="0.01" value="${formatSeconds(keepBeforeBeepS)}" placeholder="2.00" />
              </label>
              <label class="merge-source-field">
                <span>After last shot</span>
                <input id="trim-global-end" type="number" min="0" step="0.01" value="${formatSeconds(keepAfterLastShotS)}" placeholder="2.00" />
              </label>
              <div class="trim-global-actions">
                <button id="trim-global-defaults-btn" type="button" class="btn-sm btn-secondary">Reset</button>
                <button id="trim-global-undo" type="button" class="btn-sm btn-secondary">Undo</button>
                <button id="trim-global-apply" type="button" class="btn btn-primary">Apply All</button>
                <button id="trim-global-clear" type="button" class="btn btn-secondary">Clear All</button>
              </div>
            </div>
            </div>
          </div>
          <div class="settings-section trim-pane-section ${isExpanded("sources") ? "" : "collapsed"}" data-trim-section="sources">
            ${renderSectionHeader("Sources", "sources")}
            <div id="trim-sync-list" class="trim-source-list">
              ${sources.length ? sources.map((source, index) => buildSourceCard(source, index)).join("") : '<div class="empty-state">No added media for this stage.</div>'}
            </div>
          </div>
        </div>
      `;
    });
    bindEvents();
    setActive(transportActive);
  }

  return Object.freeze({
    renderTrimSyncList,
    trimAll,
    setActive,
  });
}
