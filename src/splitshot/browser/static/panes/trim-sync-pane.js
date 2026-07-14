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

  function currentState() {
    return getState() || {};
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

  function lastShotTimeMs() {
    const shots = currentState()?.project?.analysis?.shots || [];
    if (!shots.length) return null;
    return Math.max(...shots.map((shot) => shot.time_ms ?? 0));
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

  function formatSeconds(value) {
    if (value === null || value === undefined) return "--.--";
    return Number(value).toFixed(2);
  }

  function sourceDurationMs(source) {
    return source?.active_duration_ms ?? source?.asset?.duration_ms ?? primaryVideo()?.active_duration_ms ?? primaryVideo()?.duration_ms ?? 0;
  }

  function sourceBeepTimeMs(source) {
    const primaryBeep = beepTimeMs();
    if (primaryBeep === null) return null;
    return primaryBeep + currentSourceSyncOffsetMs(source);
  }

  function sourceLastShotTimeMs(source) {
    const primaryLastShot = lastShotTimeMs();
    if (primaryLastShot === null) return null;
    return primaryLastShot + currentSourceSyncOffsetMs(source);
  }

  function sourceTrimStartS(source) {
    const td = source?.trim_derivative;
    if (td?.start_s !== null && td?.start_s !== undefined) return td.start_s;
    const beep = sourceBeepTimeMs(source);
    if (beep !== null) return (beep / 1000) - 2;
    return 0;
  }

  function sourceTrimEndS(source) {
    const td = source?.trim_derivative;
    if (td?.end_s !== null && td?.end_s !== undefined) return td.end_s;
    const lastShot = sourceLastShotTimeMs(source);
    const durMs = sourceDurationMs(source);
    if (lastShot !== null) return (lastShot / 1000) + 2;
    return durMs ? (durMs / 1000) : 0;
  }

  function computedTrimLabel(source) {
    const durMs = sourceDurationMs(source);
    const durS = durMs / 1000;
    const start = sourceTrimStartS(source);
    const end = sourceTrimEndS(source);
    const before = Math.max(0, start);
    const after = Math.max(0, durS - end);
    const kept = Math.max(0, end - start);
    return `Before trim: ${formatSeconds(before)}s  |  After trim: ${formatSeconds(after)}s  |  Kept: ${formatSeconds(kept)}s  |  Total: ${formatSeconds(durS)}s`;
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

  function queueUndoSnapshot(kind, sourceId = null) {
    if (restoringUndo) return;
    trimUndoHistory.push({
      kind,
      sourceId,
      snapshot: {
        global_start: $("trim-global-start")?.value || "",
        global_end: $("trim-global-end")?.value || "",
        sources: stageSources().map((source, index) => {
          const nextSourceId = sourceIdentifier(source, String(index));
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
        }),
      },
    });
    if (trimUndoHistory.length > 40) trimUndoHistory.shift();
  }

  function refreshTrimPreview() {
    scheduleInteractionPreviewRender({ video: true, waveform: true });
    renderVideo();
  }

  async function restoreTrimSnapshot(snapshot) {
    if (!snapshot || !Array.isArray(snapshot.sources)) return;
    restoringUndo = true;
    try {
      for (const source of snapshot.sources) {
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
      if ($("trim-global-start")) $("trim-global-start").value = snapshot.global_start || "";
      if ($("trim-global-end")) $("trim-global-end").value = snapshot.global_end || "";
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
    if (recordUndo) queueUndoSnapshot("bulk");
    activity(clear ? "trim.clear-all" : "trim.apply-all", {
      keep_before_beep_s: startValue,
      keep_after_last_shot_s: endValue,
    });
    setStatus(clear ? "Clearing trim derivatives..." : "Trimming stage media...");
    await callApi("/api/merge/source/trim-all", {
      clear,
      keep_before_beep_s: clear || !Number.isFinite(startValue) || startValue < 0 ? null : startValue,
      keep_after_last_shot_s: clear || !Number.isFinite(endValue) || endValue < 0 ? null : endValue,
    });
    setStatus(clear ? "Cleared all trims." : "Trimmed all stage media.");
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
    const primaryBeep = beepTimeMs();
    const primaryLastShot = lastShotTimeMs();
    const startInput = $("trim-global-start");
    const endInput = $("trim-global-end");
    if (primaryBeep !== null && startInput) startInput.value = Math.max(0, (primaryBeep / 1000) - 2).toFixed(2);
    if (primaryLastShot !== null && endInput) endInput.value = (primaryLastShot / 1000) + 2;
    activity("trim.global-defaults", { beep_ms: primaryBeep, last_shot_ms: primaryLastShot });
    setStatus("Reset trim defaults to 2-second buffers.");
  }

  function buildSourceCard(source, index) {
    const asset = source.asset || source;
    const sourceId = sourceIdentifier(source, String(index));
    const trimDerivative = source.trim_derivative;
    const trimActive = trimDerivative && trimDerivative.active_path_kind === "local_derivative" && trimDerivative.derivative_path;
    const activePath = source?.effective_media_path || trimDerivative?.derivative_path || asset.path || "";
    const activeDisplayName = source?.active_display_name || fileName(activePath || asset.path || "");
    const originalDisplayName = source?.original_display_name || fileName(asset.path || "");
    const startS = sourceTrimStartS(source);
    const endS = sourceTrimEndS(source);
    return `
      <article class="trim-source-card" data-source-id="${sourceId}">
        <div class="trim-source-card-header">
          <div class="trim-source-card-copy">
            <strong>${activeDisplayName}</strong>
            <small>${source.is_primary_source ? "Primary video" : (asset.is_still_image ? "Image" : "Video")}${trimActive ? "  •  Trim active" : ""}${trimActive ? `  •  ${originalDisplayName} original` : ""}</small>
          </div>
          <span class="pane-summary-token">${source.is_primary_source ? "Primary" : formatSyncOffsetLabel(currentSourceSyncOffsetMs(source))}</span>
        </div>
        <div class="trim-source-card-body">
          <div class="trim-active-path-row">
            <span class="trim-active-path-badge">${trimActive ? "Trimmed media active" : "Original media active"}</span>
            <small class="trim-active-path-value">${fileName(activePath)}</small>
          </div>
          <small class="trim-computed-label">${computedTrimLabel(source)}</small>
          <div class="trim-card-row">
            <label class="merge-source-field">
              <span>Start (s)</span>
              <input type="number" min="0" step="0.01" value="${formatSeconds(startS)}" data-trim-start="${sourceId}" />
            </label>
            <label class="merge-source-field">
              <span>End (s)</span>
              <input type="number" min="0" step="0.01" value="${formatSeconds(endS)}" data-trim-end="${sourceId}" />
            </label>
            <div class="trim-card-actions">
              <button type="button" class="btn-sm btn-primary trim-apply-btn" data-source-id="${sourceId}">Apply</button>
              <button type="button" class="btn-sm btn-secondary trim-clear-btn" data-source-id="${sourceId}">Clear</button>
              <button type="button" class="btn-sm btn-secondary trim-undo-btn" data-source-id="${sourceId}">Undo</button>
            </div>
          </div>
          <div class="trim-card-row trim-card-row-quick">
            <button type="button" class="btn-sm btn-secondary trim-beep-btn" data-source-id="${sourceId}">Start at Beep</button>
            <button type="button" class="btn-sm btn-secondary trim-last-shot-btn" data-source-id="${sourceId}">End after Last Shot</button>
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
          <button type="button" class="pane-toggle" data-trim-toggle="${sectionId}" aria-label="${expanded ? "Collapse" : "Expand"} ${title}">${expanded ? "\u25BC" : "\u25B6"}</button>
        </div>
      </div>
    `;
  }

  function bindEvents() {
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
    const existingList = $("trim-sync-list");
    const primaryBeep = beepTimeMs();
    const primaryLastShot = lastShotTimeMs();
    const primaryDurMs = primaryVideo()?.duration_ms ?? 0;
    const beepS = primaryBeep !== null ? (primaryBeep / 1000).toFixed(2) : "--.--";
    const lastShotS = primaryLastShot !== null ? (primaryLastShot / 1000).toFixed(2) : "--.--";
    const durS = primaryDurMs ? (primaryDurMs / 1000).toFixed(2) : "--.--";
    withPreservedScrollState(existingList ? [existingList] : [], () => {
      pane.innerHTML = `
        <div class="pane-section trim-pane-shell">
          <div class="section-header pane-title-row">
            <h3>Trim</h3>
            <span class="pane-summary-token">${sources.length} source${sources.length === 1 ? "" : "s"}</span>
          </div>
          <div class="settings-section trim-pane-section ${isExpanded("bulk") ? "" : "collapsed"}" data-trim-section="bulk">
            ${renderSectionHeader("Bulk Trim", "bulk")}
            <div class="trim-pane-section-body"${isExpanded("bulk") ? "" : " hidden"}>
              <div class="trim-timing-bar">
                <span>Beep: ${beepS}s</span>
                <span>Last Shot: ${lastShotS}s</span>
                <span>Total: ${durS}s</span>
              </div>
              <div class="trim-global-row">
              <label class="merge-source-field">
                <span>Keep before beep (s)</span>
                <input id="trim-global-start" type="number" min="0" step="0.01" value="2.00" placeholder="2.00" />
              </label>
              <label class="merge-source-field">
                <span>Keep after last shot (s)</span>
                <input id="trim-global-end" type="number" min="0" step="0.01" value="2.00" placeholder="2.00" />
              </label>
              <div class="trim-global-actions">
                <button id="trim-global-defaults-btn" type="button" class="btn-sm btn-secondary">Reset to 2/2</button>
                <button id="trim-global-undo" type="button" class="btn-sm btn-secondary">Undo Last Change</button>
                <button id="trim-global-apply" type="button" class="btn btn-primary">Apply to All</button>
                <button id="trim-global-clear" type="button" class="btn btn-secondary">Clear All</button>
              </div>
            </div>
            </div>
          </div>
          <div class="settings-section trim-pane-section ${isExpanded("sources") ? "" : "collapsed"}" data-trim-section="sources">
            ${renderSectionHeader("Sources", "sources", `Beep: ${beepS}s  •  Last Shot: ${lastShotS}s`)}
            <div id="trim-sync-list" class="trim-source-list">
              ${sources.length ? sources.map((source, index) => buildSourceCard(source, index)).join("") : '<div class="empty-state">No added media for this stage.</div>'}
            </div>
          </div>
        </div>
      `;
    });
    bindEvents();
  }

  return Object.freeze({
    renderTrimSyncList,
    trimAll,
  });
}
