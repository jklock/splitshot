export function createQueuePane({
  $ = (id) => document.getElementById(id),
  documentObject = document,
  windowObject = window,
  getState = () => null,
  setActiveStageId = () => {},
  activity = () => {},
  callApi = async () => null,
  fileName = (value) => String(value || ""),
  setStatus = () => {},
  sendKeepaliveJson = () => false,
} = {}) {
  const expansionKey = "splitshot.queue.stageExpanded";

  function currentState() {
    return getState() || {};
  }

  function project() {
    return currentState().project || {};
  }

  function stages() {
    return Array.isArray(project().stages) ? project().stages : [];
  }

  function queueEntries() {
    return Array.isArray(project().queue) ? project().queue : [];
  }

  function activeStageId() {
    return project().active_stage_id || "";
  }

  function activeStage() {
    return stages().find((stage) => stage.id === activeStageId()) || stages()[0] || null;
  }

  function queuedCount() {
    return queueEntries().filter((entry) => entry.status === "queued" || entry.status === "stale").length;
  }

  function combinedOutputPath() {
    return String(project().last_combined_output_path || "");
  }

  function visibleQueueEntries() {
    return queueEntries()
      .filter((entry) => entry.stage_id && entry.status !== "not_queued")
      .sort((left, right) => {
        const leftStage = stages().find((stage) => stage.id === left.stage_id) || null;
        const rightStage = stages().find((stage) => stage.id === right.stage_id) || null;
        return (leftStage?.order_index ?? 999) - (rightStage?.order_index ?? 999);
      });
  }

  function findQueueEntry(stageId) {
    return queueEntries().find((entry) => entry.stage_id === stageId) || null;
  }

  function stageLabel(stage) {
    return stage?.label || `Stage ${stage?.order_index || 1}`;
  }

  function stageAssetSummary(stage) {
    const primaryName = stage?.primary_media?.path ? fileName(stage.primary_media.path) : "No primary";
    const assetCount = (stage?.primary_media?.path ? 1 : 0) + (Array.isArray(stage?.added_media) ? stage.added_media.length : 0);
    return `${primaryName} • ${assetCount} asset${assetCount === 1 ? "" : "s"}`;
  }

  function queueEntryAssetSummary(entry, stage) {
    const snapshot = entry?.snapshot || {};
    const primary = snapshot.primary_media || stage?.primary_media || {};
    const added = Array.isArray(snapshot.added_media) ? snapshot.added_media : (Array.isArray(stage?.added_media) ? stage.added_media : []);
    const primaryName = primary?.path ? fileName(primary.path) : "No primary";
    const assetCount = (primary?.path ? 1 : 0) + added.length;
    return `${primaryName} • ${assetCount} asset${assetCount === 1 ? "" : "s"}`;
  }

  function queueStatusLabel(status) {
    return {
      not_queued: "Not queued",
      queued: "Queued",
      processing: "Processing",
      complete: "Complete",
      failed: "Failed",
      stale: "Needs requeue",
    }[status] || String(status || "Not queued");
  }

  function isStageExpanded(stageId) {
    try {
      const stored = JSON.parse(windowObject?.localStorage?.getItem(expansionKey) || "{}");
      if (stored && typeof stored === "object" && stored[stageId] !== undefined) return Boolean(stored[stageId]);
    } catch (_) {}
    return false;
  }

  function setStageExpanded(stageId, expanded) {
    try {
      const stored = JSON.parse(windowObject?.localStorage?.getItem(expansionKey) || "{}");
      const next = { ...(stored && typeof stored === "object" ? stored : {}), [stageId]: expanded };
      windowObject?.localStorage?.setItem(expansionKey, JSON.stringify(next));
    } catch (_) {}
  }

  function toggleStage(stageId) {
    setStageExpanded(stageId, !isStageExpanded(stageId));
    render();
  }

  function selectStage(stageId) {
    const proj = project();
    if (!proj || !stageId) return;
    proj.active_stage_id = stageId;
    setActiveStageId(stageId);
    sendKeepaliveJson("/api/project/select-stage", { active_stage_id: stageId });
    activity("queue.select-stage", { stageId });
    render();
  }

  function queueActionLabel(stageId) {
    const entry = findQueueEntry(stageId);
    const status = String(entry?.status || "not_queued");
    if (status === "not_queued") return "Queue";
    if (status === "stale" || status === "failed" || status === "complete") return "Requeue";
    if (status === "processing") return "Processing";
    return "Unqueue";
  }

  async function updateQueueMembership(stageId = activeStageId()) {
    if (!stageId) return;
    const action = queueActionLabel(stageId);
    if (action === "Queue" || action === "Requeue") {
      activity("queue.add", { stageId });
      const result = await callApi("/api/project/queue/add", { stage_id: stageId });
      if (result) setStatus(`${action}d ${stageLabel(stages().find((stage) => stage.id === stageId))}.`);
      return;
    }
    if (action === "Unqueue") {
      activity("queue.remove", { stageId });
      await callApi("/api/project/queue/remove", { stage_id: stageId });
      setStatus(`Unqueued ${stageLabel(stages().find((stage) => stage.id === stageId))}.`);
      return;
    }
  }

  async function applySettingsToQueued() {
    activity("queue.apply-all");
    await callApi("/api/project/queue/apply-all", {});
    setStatus("Applied the active stage settings to queued stages.");
  }

  async function processAll() {
    activity("queue.process");
    setStatus("Processing queued stages...");
    await callApi("/api/project/queue/process", { mode: "individual" });
  }

  async function processIntoOneFile() {
    activity("queue.process-combined");
    setStatus("Processing combined queue export...");
    await callApi("/api/project/queue/process", { mode: "combined" });
  }

  function renderQueueStage(queueEntry) {
    const stage = stages().find((item) => item.id === queueEntry.stage_id) || null;
    const stageId = queueEntry.stage_id;
    const status = queueEntry?.status || stage?.queue_status || "not_queued";
    const selected = stageId === activeStageId();
    const expanded = isStageExpanded(stageId);
    const actionLabel = queueActionLabel(stageId);
    const disabled = status === "processing";
    return `
      <article class="queue-stage-card ${selected ? "selected" : ""}" data-queue-stage-id="${stageId}">
        <div class="queue-stage-header section-header-with-toggle">
          <div class="queue-stage-copy">
            <strong>${stageLabel(stage || queueEntry?.snapshot || {})}</strong>
            <small>${queueEntryAssetSummary(queueEntry, stage)}</small>
          </div>
          <div class="queue-stage-header-actions">
            <span class="queue-status-pill queue-status-${status}">${queueStatusLabel(status)}</span>
            <button class="pane-toggle queue-stage-toggle" type="button" data-stage-id="${stageId}" aria-label="${expanded ? "Collapse" : "Expand"} queue stage">${expanded ? "\u25BC" : "\u25B6"}</button>
          </div>
        </div>
        <div class="queue-stage-body"${expanded ? "" : " hidden"}>
          <div class="queue-stage-actions">
            <button class="btn-sm btn-secondary queue-membership-btn" type="button" data-stage-id="${stageId}" ${disabled ? "disabled" : ""}>${actionLabel}</button>
          </div>
        </div>
      </article>
    `;
  }

  function renderControlsSection() {
    const stage = activeStage();
    const stageOptions = stages()
      .map((item) => `<option value="${item.id}" ${item.id === stage?.id ? "selected" : ""}>${stageLabel(item)}</option>`)
      .join("");
    const combinedOutput = combinedOutputPath();
    return `
      <section class="settings-section queue-pane-section">
        <div class="section-header media-section-header">
          <strong>Queue Controls</strong>
        </div>
        <div class="queue-controls-body">
          <label>Stage
            <select id="queue-stage-select">${stageOptions}</select>
          </label>
          <button class="btn btn-secondary queue-membership-btn" type="button" data-stage-id="${stage?.id || ""}" ${stage ? "" : "disabled"}>${queueActionLabel(stage?.id || "")}</button>
          <button id="queue-apply-all-btn" class="btn btn-secondary queue-apply-all-btn" type="button">Apply Active Stage Settings to Queued</button>
          <button id="queue-process-btn" class="btn btn-primary queue-process-btn" type="button">Process Many</button>
          <button id="queue-combined-btn" class="btn btn-primary queue-combined-btn" type="button">Process Into 1 File</button>
        </div>
        ${combinedOutput ? `
          <div class="queue-combined-output" data-queue-combined-output="${combinedOutput}">
            <strong>Combined Output</strong>
            <span>${fileName(combinedOutput)}</span>
          </div>
        ` : ""}
      </section>
    `;
  }

  function bindEvents(pane) {
    if (!(pane instanceof HTMLElement)) return;
    pane.onclick = (event) => {
      const target = event.target instanceof HTMLElement ? event.target : null;
      if (!target) return;
      const toggle = target.closest(".queue-stage-toggle");
      if (toggle instanceof HTMLElement) {
        event.preventDefault();
        event.stopPropagation();
        toggleStage(toggle.dataset.stageId || "");
        return;
      }
      const membershipButton = target.closest(".queue-membership-btn");
      if (membershipButton instanceof HTMLElement) {
        updateQueueMembership(membershipButton.dataset.stageId || activeStage()?.id || "");
        return;
      }
      if (target.closest(".queue-apply-all-btn")) {
        applySettingsToQueued();
        return;
      }
      if (target.closest(".queue-process-btn")) {
        processAll();
        return;
      }
      if (target.closest(".queue-combined-btn")) {
        processIntoOneFile();
        return;
      }
      const card = target.closest("[data-queue-stage-id]");
      if (card instanceof HTMLElement) {
        selectStage(card.dataset.queueStageId || "");
      }
    };
    pane.onchange = (event) => {
      const target = event.target instanceof HTMLElement ? event.target : null;
      if (!target) return;
      if (target.id === "queue-stage-select") {
        selectStage(target.value || "");
      }
    };
  }

  function render() {
    const pane = $("queue-pane");
    if (!pane) return;
    const count = queuedCount();
    pane.innerHTML = `
      <div class="pane-section queue-pane-shell">
        <div class="section-header pane-title-row">
          <h3>Queue</h3>
          <span class="pane-summary-token">${count} queued</span>
        </div>
        ${renderControlsSection()}
        <section class="settings-section queue-pane-section">
          <div class="section-header media-section-header">
            <strong>Queued Stages</strong>
          </div>
          <div class="queue-stage-list">
            ${visibleQueueEntries().length ? visibleQueueEntries().map((entry) => renderQueueStage(entry)).join("") : '<div class="empty-state">No queued stages.</div>'}
          </div>
        </section>
      </div>
    `;
    bindEvents(pane);
  }

  function mount() {
    render();
  }

  return Object.freeze({
    render,
    mount,
    updateQueueMembership,
    toggleStage,
  });
}
