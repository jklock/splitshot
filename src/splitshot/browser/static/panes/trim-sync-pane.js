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
  const sectionExpansion = new Map([
    ["bulk", true],
    ["sources", true],
  ]);

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

  function isExpanded(sectionId) {
    return sectionExpansion.get(sectionId) !== false;
  }

  function renderSectionHeader(title, sectionId, detail = "") {
    const expanded = isExpanded(sectionId);
    return `
      <div class="section-header trim-section-header">
        <strong>${title}</strong>
        <div class="section-header-actions">
          ${detail ? `<small>${detail}</small>` : ""}
          <button type="button" class="scoring-shot-toggle" data-trim-toggle="${sectionId}" aria-label="${expanded ? "Collapse" : "Expand"} ${title}">${expanded ? "\u25BC" : "\u25B6"}</button>
        </div>
      </div>
    `;
  }

  async function trimAll(clear = false) {
    const startInput = $("trim-sync-bulk-start");
    const endInput = $("trim-sync-bulk-end");
    const startValue = parseFloat(startInput?.value || "");
    const endValue = parseFloat(endInput?.value || "");
    activity(clear ? "trim.clear-all" : "trim.apply-all", {
      stageLabel: activeStageLabel(),
      start_s: startValue,
      end_s: endValue,
    });
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
    if (status === "ready") return `Beep ${Math.round(Number(source.secondary_beep_time_ms) || 0)} ms`;
    if (status === "no_beep") return "No beep detected.";
    return String(source.sync_analysis_message || "");
  }

  function formatSyncOffsetLabel(offsetMs) {
    const numeric = Math.round(Number(offsetMs) || 0);
    return `Sync ${numeric > 0 ? "+" : ""}${numeric} ms`;
  }

  function buildSourceCard(source, index) {
    const asset = source.asset || source;
    const sourceId = sourceIdentifier(source, String(index));
    const trimDerivative = source.trim_derivative;
    const trimStatus = trimDerivative && trimDerivative.active_path_kind === "local_derivative" && trimDerivative.derivative_path
      ? "Trim active"
      : "No trim";
    return `
      <article class="trim-source-card" data-source-id="${sourceId}">
        <div class="trim-source-card-header">
          <div class="trim-source-card-copy">
            <strong>${fileName(asset.path || "")}</strong>
            <small>${asset.is_still_image ? "Image" : "Video"} • ${trimStatus}</small>
          </div>
          <span class="pane-summary-token">${formatSyncOffsetLabel(currentSourceSyncOffsetMs(source))}</span>
        </div>
        <div class="trim-source-card-body">
          <div class="trim-card-row">
            <label class="merge-source-field">
              <span>Start</span>
              <input type="number" min="0" step="0.001" placeholder="0.000" data-trim-start="${sourceId}" />
            </label>
            <label class="merge-source-field">
              <span>End</span>
              <input type="number" min="0" step="0.001" placeholder="0.000" data-trim-end="${sourceId}" />
            </label>
            <div class="trim-card-actions">
              <button type="button" class="btn-sm btn-primary trim-apply-btn" data-source-id="${sourceId}">Apply</button>
              <button type="button" class="btn-sm btn-secondary trim-clear-btn" data-source-id="${sourceId}">Clear</button>
            </div>
          </div>
          <div class="trim-card-row trim-card-row-sync">
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
          <small class="merge-source-sync-hint">${source.supports_sync_analysis ? sourceSyncStatusLabel(source) : formatSyncOffsetLabel(currentSourceSyncOffsetMs(source))}</small>
        </div>
      </article>
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
    $("trim-sync-apply-all")?.addEventListener("click", () => trimAll(false));
    $("trim-sync-clear-all")?.addEventListener("click", () => trimAll(true));
    documentObject.querySelectorAll(".trim-apply-btn").forEach((button) => {
      button.addEventListener("click", () => {
        const sourceId = button.dataset.sourceId || "";
        const startValue = parseFloat(documentObject.querySelector(`[data-trim-start="${sourceId}"]`)?.value || "");
        const endValue = parseFloat(documentObject.querySelector(`[data-trim-end="${sourceId}"]`)?.value || "");
        activity("trim.apply", { sourceId, start_s: startValue, end_s: endValue });
        callApi("/api/merge/source/trim", {
          source_id: sourceId,
          start_s: Number.isFinite(startValue) && startValue > 0 ? startValue : null,
          end_s: Number.isFinite(endValue) && endValue > 0 ? endValue : null,
        });
      });
    });
    documentObject.querySelectorAll(".trim-clear-btn").forEach((button) => {
      button.addEventListener("click", () => {
        const sourceId = button.dataset.sourceId || "";
        activity("trim.clear", { sourceId });
        callApi("/api/merge/source/trim", { source_id: sourceId, clear: true });
      });
    });
    documentObject.querySelectorAll("[data-source-sync-offset]").forEach((input) => {
      input.addEventListener("change", () => {
        const sourceId = input.dataset.sourceSyncOffset || "";
        const offsetMs = Math.round(Number(input.value) || 0);
        activity("trim.sync.set", { sourceId, offset_ms: offsetMs });
        callApi("/api/merge/source", { source_id: sourceId, sync_offset_ms: offsetMs });
        scheduleInteractionPreviewRender({ video: true });
        renderVideo();
      });
    });
    documentObject.querySelectorAll("[data-sync-delta]").forEach((button) => {
      button.addEventListener("click", () => {
        const sourceId = button.dataset.sourceId || "";
        const deltaMs = Math.round(Number(button.dataset.syncDelta) || 0);
        activity("trim.sync.nudge", { sourceId, delta_ms: deltaMs });
        callApi("/api/merge/source", { source_id: sourceId, sync_delta_ms: deltaMs });
        renderVideo();
      });
    });
    documentObject.querySelectorAll(".trim-analyze-btn").forEach((button) => {
      button.addEventListener("click", () => {
        const sourceId = button.dataset.sourceId || "";
        activity("trim.sync.analyze", { sourceId });
        callApi("/api/merge/source/analyze", { source_id: sourceId });
      });
    });
  }

  function renderTrimSyncList() {
    const pane = documentObject.querySelector('[data-tool-pane="trim-sync"]');
    if (!pane) return;
    const sources = mergeSources();
    const existingList = $("trim-sync-list");
    withPreservedScrollState(existingList ? [existingList] : [], () => {
      pane.innerHTML = `
        <div class="pane-section trim-pane-shell">
          <div class="section-header pane-title-row">
            <h3>Trim</h3>
            <span class="pane-summary-token">${sources.length} source${sources.length === 1 ? "" : "s"}</span>
          </div>
          <div class="settings-section trim-pane-section ${isExpanded("bulk") ? "" : "collapsed"}" data-trim-section="bulk">
            ${renderSectionHeader("Bulk Trim", "bulk")}
            <div class="trim-bulk-grid">
              <label class="merge-source-field">
                <span>Start</span>
                <input id="trim-sync-bulk-start" type="number" min="0" step="0.001" placeholder="0.000" />
              </label>
              <label class="merge-source-field">
                <span>End</span>
                <input id="trim-sync-bulk-end" type="number" min="0" step="0.001" placeholder="0.000" />
              </label>
              <div class="trim-bulk-actions">
                <button id="trim-sync-apply-all" type="button" class="btn btn-primary">Apply All</button>
                <button id="trim-sync-clear-all" type="button" class="btn btn-secondary">Clear All</button>
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
  }

  return Object.freeze({
    renderTrimSyncList,
    trimAll,
    activeStageLabel,
  });
}
