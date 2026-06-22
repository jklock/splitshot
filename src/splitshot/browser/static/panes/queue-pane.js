export function createQueuePane({
  $ = (id) => document.getElementById(id),
  documentObject = document,
  windowObject = window,
  getState = () => null,
  setActiveTool = () => {},
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

  function queuedCount() {
    return queueEntries().filter((entry) => entry.status === "queued" || entry.status === "stale").length;
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

  async function addToQueue(stageId = activeStageId()) {
    if (!stageId) return;
    activity("queue.add", { stageId });
    const result = await callApi("/api/project/queue/add", { stage_id: stageId });
    if (result) setStatus(`Queued ${stageLabel(stages().find((stage) => stage.id === stageId))}.`);
  }

  async function removeFromQueue(stageId) {
    if (!stageId) return;
    activity("queue.remove", { stageId });
    await callApi("/api/project/queue/remove", { stage_id: stageId });
  }

  async function applySettingsToAll() {
    activity("queue.apply-all");
    await callApi("/api/project/queue/apply-all", {});
    setStatus("Applied the current stage template across the queue.");
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

  function selectStageFromQueue(stageId) {
    const proj = project();
    if (!proj || !stageId) return;
    proj.active_stage_id = stageId;
    setActiveStageId(stageId);
    sendKeepaliveJson("/api/project/select-stage", { active_stage_id: stageId });
    activity("queue.select-stage", { stageId });
    render();
  }

  function editStage(stageId) {
    if (!stageId) return;
    activity("queue.edit-stage", { stageId, tool: "media" });
    selectStageFromQueue(stageId);
    setActiveTool("media");
  }

  function renderQueueStage(stage) {
    const queueEntry = findQueueEntry(stage.id);
    const status = queueEntry?.status || stage.queue_status || "not_queued";
    const selected = stage.id === activeStageId();
    const expanded = isStageExpanded(stage.id);
    const canQueue = Boolean(stage?.primary_media?.path);
    return `
      <article class="queue-stage-card ${selected ? "selected" : ""}" data-queue-stage-id="${stage.id}">
        <div class="queue-stage-header section-header-with-toggle">
          <div class="queue-stage-copy">
            <strong>${stageLabel(stage)}</strong>
            <small>${stageAssetSummary(stage)}</small>
          </div>
          <div class="queue-stage-header-actions">
            <span class="queue-status-pill queue-status-${status}">${queueStatusLabel(status)}</span>
            <button class="scoring-shot-toggle queue-stage-toggle" type="button" data-stage-id="${stage.id}" aria-label="${expanded ? "Collapse" : "Expand"} queue stage">${expanded ? "\u25BC" : "\u25B6"}</button>
          </div>
        </div>
        <div class="queue-stage-body"${expanded ? "" : " hidden"}>
          <div class="queue-stage-actions">
            <button class="btn-sm btn-ghost queue-edit-btn" type="button" data-stage-id="${stage.id}">Edit Stage</button>
            ${status === "queued" || status === "stale"
              ? `<button class="btn-sm btn-danger queue-remove-btn" type="button" data-stage-id="${stage.id}">Remove</button>`
              : `<button class="btn-sm btn-secondary queue-add-btn" type="button" data-stage-id="${stage.id}" ${canQueue ? "" : "disabled"}>${status === "stale" ? "Requeue" : "Queue"}</button>`}
          </div>
        </div>
      </article>
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
      const editButton = target.closest(".queue-edit-btn");
      if (editButton instanceof HTMLElement) {
        editStage(editButton.dataset.stageId || "");
        return;
      }
      const removeButton = target.closest(".queue-remove-btn");
      if (removeButton instanceof HTMLElement) {
        removeFromQueue(removeButton.dataset.stageId || "");
        return;
      }
      const addButton = target.closest(".queue-add-btn");
      if (addButton instanceof HTMLElement) {
        addToQueue(addButton.dataset.stageId || "");
        return;
      }
      if (target.closest(".queue-apply-all-btn")) {
        applySettingsToAll();
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
        selectStageFromQueue(card.dataset.queueStageId || "");
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
          <span class="pane-summary-token">${count} ready</span>
        </div>
        <div class="queue-stage-list">
          ${stages().length ? stages().map((stage) => renderQueueStage(stage)).join("") : '<div class="empty-state">No stages.</div>'}
        </div>
        <div class="queue-pane-actions">
          <button id="queue-apply-all-btn" class="btn btn-secondary queue-apply-all-btn" type="button">Apply To All</button>
          <button id="queue-process-btn" class="btn btn-primary queue-process-btn" type="button">Process Many</button>
          <button id="queue-combined-btn" class="btn btn-primary queue-combined-btn" type="button">Process Into 1 File</button>
        </div>
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
    addToQueue,
    toggleStage,
  });
}
