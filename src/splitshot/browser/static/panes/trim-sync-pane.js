export function createTrimSyncPane({
  $ = (id) => document.getElementById(id),
  documentObject = document,
  getState = () => null,
  withPreservedScrollState = (_elements, callback) => callback(),
  activity = () => {},
  callApi = async () => null,
  scheduleInteractionPreviewRender = () => {},
  renderVideo = () => {},
  fileName = (value) => String(value || ""),
  sourceIdentifier = (source, fallback) => String(source?.id || fallback || ""),
  currentSourceSyncOffsetMs = (source) => Math.round(Number(source?.sync_offset_ms) || 0),
} = {}) {
  function currentState() {
    return getState() || {};
  }

  function activeStageLabel() {
    const activeStageId = currentState()?.project?.active_stage_id || "";
    const stages = Array.isArray(currentState()?.project?.stages) ? currentState().project.stages : [];
    const stage = stages.find((item) => item.id === activeStageId) || null;
    return stage?.label || (stage ? `Stage ${stage.order_index}` : "Trim");
  }

  function mergeSources() {
    return currentState()?.project?.merge_sources || [];
  }

  async function trimAll(clear = false) {
    const startInput = $("trim-sync-bulk-start");
    const endInput = $("trim-sync-bulk-end");
    const startValue = parseFloat(startInput?.value || "");
    const endValue = parseFloat(endInput?.value || "");
    await callApi("/api/merge/source/trim-all", {
      clear,
      start_s: clear || !Number.isFinite(startValue) || startValue <= 0 ? null : startValue,
      end_s: clear || !Number.isFinite(endValue) || endValue <= 0 ? null : endValue,
    });
  }

  function sourceSyncStatusLabel(source = null) {
    if (!source?.supports_sync_analysis) return "";
    const status = String(source.sync_analysis_status || "idle");
    if (status === "running") return "Analyzing beep sync...";
    if (status === "ready") {
      const beepMs = Number(source.secondary_beep_time_ms);
      const sourceLabel = String(source.sync_offset_source || "manual");
      return Number.isFinite(beepMs)
        ? `Beep ${Math.round(beepMs)} ms • ${sourceLabel === "auto" ? "ShotML sync applied" : "manual sync active"}`
        : "Beep detected.";
    }
    if (status === "no_beep") return "No beep detected.";
    return String(source.sync_analysis_message || "");
  }

  function formatSyncOffsetLabel(offsetMs) {
    const numeric = Math.round(Number(offsetMs) || 0);
    return `Sync ${numeric > 0 ? "+" : ""}${numeric} ms`;
  }

  function renderTrimSyncList() {
    const list = $("trim-sync-list");
    if (!list) return;
    const sources = mergeSources();
    const stageLabel = $("trim-sync-stage-label");
    if (stageLabel) stageLabel.textContent = activeStageLabel();
    const applyAllButton = $("trim-sync-apply-all");
    if (applyAllButton) applyAllButton.onclick = () => trimAll(false);
    const clearAllButton = $("trim-sync-clear-all");
    if (clearAllButton) clearAllButton.onclick = () => trimAll(true);
    withPreservedScrollState([list], () => {
      list.innerHTML = "";
      if (sources.length === 0) {
        const empty = documentObject.createElement("div");
        empty.className = "empty-state";
        empty.textContent = "No added media.";
        list.appendChild(empty);
        return;
      }

      sources.forEach((source, index) => {
        const asset = source.asset || source;
        const sourceId = sourceIdentifier(source, String(index));
        const isAddedVideo = index > 0;

        const card = documentObject.createElement("div");
        card.className = "merge-media-card trim-sync-card";
        card.dataset.sourceId = sourceId;

        const header = documentObject.createElement("div");
        header.className = "merge-media-card-header";
        const title = documentObject.createElement("strong");
        title.textContent = `${index + 1}. ${fileName(asset.path || "")}`;

        const meta = documentObject.createElement("small");
        meta.className = "merge-media-card-meta";
        const mediaType = asset.is_still_image ? "Image" : "Video";
        const dimensions = asset.width && asset.height ? ` • ${asset.width}x${asset.height}` : "";
        meta.textContent = `${mediaType}${dimensions}`;

        header.append(title);
        const body = documentObject.createElement("div");
        body.className = "merge-media-card-body";

        body.appendChild(meta);

        // --- Trim section ---
        const trimSection = documentObject.createElement("div");
        trimSection.className = "merge-source-trim-section";
        const trimHeader = documentObject.createElement("strong");
        trimHeader.textContent = "Trim Video";
        const trimRow = documentObject.createElement("div");
        trimRow.className = "merge-source-trim-row";
        const trimStartInput = documentObject.createElement("input");
        trimStartInput.type = "number";
        trimStartInput.min = "0";
        trimStartInput.step = "0.001";
        trimStartInput.placeholder = "Start (s)";
        trimStartInput.dataset.trimStart = sourceId;
        const trimEndInput = documentObject.createElement("input");
        trimEndInput.type = "number";
        trimEndInput.min = "0";
        trimEndInput.step = "0.001";
        trimEndInput.placeholder = "End (s)";
        trimEndInput.dataset.trimEnd = sourceId;
        const trimApply = documentObject.createElement("button");
        trimApply.type = "button";
        trimApply.textContent = "Apply";
        trimApply.addEventListener("click", () => {
          const s = parseFloat(trimStartInput.value) || 0;
          const e = parseFloat(trimEndInput.value) || 0;
          callApi("/api/merge/source/trim", { source_id: sourceId, start_s: s > 0 ? s : null, end_s: e > 0 ? e : null });
        });
        const trimClear = documentObject.createElement("button");
        trimClear.type = "button";
        trimClear.textContent = "Clear";
        trimClear.addEventListener("click", () => {
          callApi("/api/merge/source/trim", { source_id: sourceId, clear: true });
        });
        const trimStatus = documentObject.createElement("small");
        trimStatus.className = "merge-source-trim-status";
        const trimDerivative = source.trim_derivative;
        if (trimDerivative && trimDerivative.active_path_kind === "local_derivative" && trimDerivative.derivative_path) {
          trimStatus.textContent = "Trim active";
          trimStatus.style.color = "var(--accent)";
        }
        trimRow.append(trimStartInput, trimEndInput, trimApply, trimClear);
        trimSection.append(trimHeader, trimRow, trimStatus);
        body.appendChild(trimSection);

        // --- Manual sync section ---
        const syncSection = documentObject.createElement("div");
        syncSection.className = "trim-sync-offset-section";

        const syncHeader = documentObject.createElement("strong");
        syncHeader.textContent = "Manual Sync";

        const syncInputRow = documentObject.createElement("div");
        syncInputRow.className = "trim-sync-input-row";

        const offsetLabel = documentObject.createElement("label");
        offsetLabel.className = "merge-source-field trim-sync-offset-label";
        const offsetText = documentObject.createElement("span");
        offsetText.textContent = "Offset ms";
        const offsetInput = documentObject.createElement("input");
        offsetInput.type = "number";
        offsetInput.className = "trim-sync-offset-input";
        offsetInput.step = "1";
        offsetInput.value = String(currentSourceSyncOffsetMs(source));
        offsetInput.title = "Manual sync offset in milliseconds.";
        offsetInput.addEventListener("change", () => {
          const offsetMs = Math.round(Number(offsetInput.value) || 0);
          callApi("/api/merge/source", { source_id: sourceId, sync_offset_ms: offsetMs });
          scheduleInteractionPreviewRender({ video: true });
          renderVideo();
        });
        offsetInput.addEventListener("blur", () => {
          const offsetMs = Math.round(Number(offsetInput.value) || 0);
          callApi("/api/merge/source", { source_id: sourceId, sync_offset_ms: offsetMs });
        });
        offsetLabel.append(offsetText, offsetInput);

        syncInputRow.appendChild(offsetLabel);

        const nudgeButtons = documentObject.createElement("div");
        nudgeButtons.className = "button-grid compact trim-sync-nudge-buttons";
        [-10, -1, 1, 10].forEach((deltaMs) => {
          const button = documentObject.createElement("button");
          button.type = "button";
          button.textContent = `${deltaMs > 0 ? "+" : ""}${deltaMs}`;
          button.title = `Nudge ${deltaMs > 0 ? "later" : "earlier"} by ${Math.abs(deltaMs)} ms.`;
          button.addEventListener("click", () => {
            const nextOffset = currentSourceSyncOffsetMs(source) + deltaMs;
            offsetInput.value = String(nextOffset);
            callApi("/api/merge/source", { source_id: sourceId, sync_delta_ms: deltaMs });
            renderVideo();
          });
          nudgeButtons.appendChild(button);
        });

        const syncStatusEl = documentObject.createElement("small");
        syncStatusEl.className = "merge-source-sync-hint";
        if (source.supports_sync_analysis) {
          syncStatusEl.textContent = sourceSyncStatusLabel(source);
        } else {
          syncStatusEl.textContent = formatSyncOffsetLabel(currentSourceSyncOffsetMs(source));
        }

        syncSection.append(syncHeader, syncInputRow, nudgeButtons, syncStatusEl);
        body.appendChild(syncSection);

        // --- Analyze button ---
        if (source.supports_sync_analysis) {
          const analyzeRow = documentObject.createElement("div");
          analyzeRow.className = "trim-sync-analyze-row";
          const analyzeButton = documentObject.createElement("button");
          analyzeButton.type = "button";
          analyzeButton.className = "primary-button";
          analyzeButton.textContent = source.sync_analysis_status === "ready" ? "Re-run beep sync" : "Analyze beep sync";
          analyzeButton.disabled = source.sync_analysis_status === "running";
          analyzeButton.title = "Use ShotML to find this video's start beep and set sync automatically.";
          analyzeButton.addEventListener("click", () => {
            callApi("/api/merge/source/analyze", { source_id: sourceId });
          });
          analyzeRow.appendChild(analyzeButton);
          body.appendChild(analyzeRow);
        }

        card.append(header, body);
        list.appendChild(card);
      });
    });
  }

  return Object.freeze({
    renderTrimSyncList,
    trimAll,
    activeStageLabel,
  });
}
