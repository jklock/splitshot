import { createPaneBase } from "./pane-base.js";

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
  formatNumber = (value) => String(value ?? ""),
  renderHeader = () => {},
  setStatus = () => {},
  sendKeepaliveJson = () => false,
} = {}) {
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

  function findQueueEntry(stageId) {
    return queueEntries().find((e) => e.stage_id === stageId) || null;
  }

  function queueStatusBadge(status) {
    const colors = {
      not_queued: "badge-neutral",
      queued: "badge-info",
      processing: "badge-warning",
      complete: "badge-success",
      failed: "badge-error",
      stale: "badge-stale",
    };
    const labels = {
      not_queued: "Not Queued",
      queued: "Queued",
      processing: "Processing",
      complete: "Complete",
      failed: "Failed",
      stale: "Stale",
    };
    return `<span class="badge ${colors[status] || "badge-neutral"}">${labels[status] || status}</span>`;
  }

  async function addToQueue() {
    const stageId = activeStageId();
    if (!stageId) return;
    activity("queue.add", { stageId });
    const result = await callApi("/api/project/queue/add", {
      method: "POST",
      body: JSON.stringify({ stage_id: stageId }),
    });
    if (result) setStatus("Stage added to queue.");
  }

  async function removeFromQueue(stageId) {
    if (!stageId) return;
    activity("queue.remove", { stageId });
    await callApi("/api/project/queue/remove", {
      method: "POST",
      body: JSON.stringify({ stage_id: stageId }),
    });
  }

  async function applySettingsToAll() {
    activity("queue.apply-all");
    await callApi("/api/project/queue/apply-all", {
      method: "POST",
      body: JSON.stringify({}),
    });
    setStatus("Settings applied to all stages.");
  }

  async function processAll() {
    activity("queue.process");
    setStatus("Processing queued stages...");
    await callApi("/api/project/queue/process", {
      method: "POST",
      body: JSON.stringify({ mode: "individual" }),
    });
  }

  async function processIntoOneFile() {
    activity("queue.process-combined");
    setStatus("Processing combined export...");
    await callApi("/api/project/queue/process", {
      method: "POST",
      body: JSON.stringify({ mode: "combined" }),
    });
  }

  function editStage(stageId) {
    if (!stageId) return;
    selectStageFromQueue(stageId);
    setActiveTool("merge");
  }

  function selectStageFromQueue(stageId) {
    const proj = project();
    if (!proj || !stageId) return;
    proj.active_stage_id = stageId;
    setActiveStageId(stageId);
    sendKeepaliveJson("/api/project/select-stage", { active_stage_id: stageId });
    activity("queue.select-stage", { stageId });
  }

  function renderQueueRow(stage) {
    const entry = findQueueEntry(stage.id);
    const status = entry?.status || "not_queued";
    const isActive = stage.id === activeStageId();
    const primaryName = stage.primary_media?.path
      ? fileName(stage.primary_media.path)
      : "No primary media";

    return `
      <tr class="queue-row ${isActive ? "queue-row-active" : ""}" data-stage-id="${stage.id}">
        <td class="queue-stage">
          <span class="stage-order">${stage.order_index}.</span>
          <span>${stage.label || `Stage ${stage.order_index}`}</span>
        </td>
        <td class="queue-media">${primaryName}</td>
        <td class="queue-status">${queueStatusBadge(status)}</td>
        <td class="queue-actions">
          <button class="btn-sm btn-ghost queue-edit-btn" type="button">Edit Stage</button>
          ${status === "queued"
            ? '<button class="btn-sm btn-danger queue-remove-btn" type="button">Remove</button>'
            : ""}
          ${status === "stale"
            ? '<button class="btn-sm btn-warning queue-requeue-btn" type="button">Requeue</button>'
            : ""}
        </td>
      </tr>`;
  }

  function bindEvents() {
    const table = $("queue-stage-table");
    if (!table) return;

    table.querySelectorAll(".queue-row").forEach((row) => {
      row.addEventListener("click", (e) => {
        if (e.target.closest("button")) return;
        const stageId = row.dataset.stageId;
        if (stageId) selectStageFromQueue(stageId);
      });
    });

    table.querySelectorAll(".queue-edit-btn").forEach((btn) => {
      btn.addEventListener("click", (e) => {
        e.stopPropagation();
        const row = btn.closest(".queue-row");
        const stageId = row?.dataset.stageId;
        if (stageId) editStage(stageId);
      });
    });

    table.querySelectorAll(".queue-remove-btn").forEach((btn) => {
      btn.addEventListener("click", (e) => {
        e.stopPropagation();
        const row = btn.closest(".queue-row");
        const stageId = row?.dataset.stageId;
        if (stageId) removeFromQueue(stageId);
      });
    });

    const addBtn = $("queue-add-btn");
    if (addBtn) addBtn.addEventListener("click", addToQueue);

    const applyAllBtn = $("queue-apply-all-btn");
    if (applyAllBtn) applyAllBtn.addEventListener("click", applySettingsToAll);

    const processBtn = $("queue-process-btn");
    if (processBtn) processBtn.addEventListener("click", processAll);

    const combinedBtn = $("queue-combined-btn");
    if (combinedBtn) combinedBtn.addEventListener("click", processIntoOneFile);
  }

  function render() {
    const pane = $("queue-pane");
    if (!pane) return;

    const stageList = stages();
    const stageRows = stageList.length
      ? stageList.map((s) => renderQueueRow(s)).join("")
      : '<tr><td colspan="4" class="empty-state">No stages. Import PractiScore data from Project, then pair media in Media.</td></tr>';

    pane.innerHTML = `
      <div class="pane-section">
        <h3 class="section-title">Queue</h3>
        <p class="section-desc">Review queued stages and process exports.</p>
        <div class="queue-toolbar">
          <button id="queue-add-btn" class="btn btn-primary" type="button">Add To Queue</button>
          <button id="queue-apply-all-btn" class="btn btn-secondary" type="button">Apply Settings To All</button>
        </div>
        <table id="queue-stage-table" class="stage-table">
          <thead>
            <tr>
              <th>Stage</th>
              <th>Primary Media</th>
              <th>Status</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>${stageRows}</tbody>
        </table>
        <div class="queue-process-actions">
          <button id="queue-process-btn" class="btn btn-primary" type="button">Process</button>
          <button id="queue-combined-btn" class="btn btn-primary" type="button">Process Into 1 File</button>
        </div>
      </div>`;
    bindEvents();
  }

  function mount() {
    render();
  }

  return Object.freeze({
    render,
    mount,
    addToQueue,
  });
}
