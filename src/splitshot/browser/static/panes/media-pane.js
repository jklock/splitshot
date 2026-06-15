import { createPaneBase } from "./pane-base.js";

export function createMediaPane({
  $ = (id) => document.getElementById(id),
  documentObject = document,
  windowObject = window,
  getState = () => null,
  setActiveStageId = () => {},
  activity = () => {},
  callApi = async () => null,
  pickPath = async () => "",
  fileName = (value) => String(value || ""),
  splitSeconds = (value) => String(value ?? ""),
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

  function activeStageId() {
    return project().active_stage_id || "";
  }

  function selectStage(stageId) {
    const proj = project();
    if (!proj || !stageId) return;
    proj.active_stage_id = stageId;
    setActiveStageId(stageId);
    const payload = { active_stage_id: stageId };
    sendKeepaliveJson("/api/project/select-stage", payload);
    activity("media.select-stage", { stageId });
  }

  async function importPrimaryMedia(stageId) {
    const paths = await pickPath();
    if (!paths || !paths.length) return;
    const result = await callApi("/api/project/stage/import-primary", {
      method: "POST",
      body: JSON.stringify({ stage_id: stageId, paths }),
    });
    if (result) {
      activity("media.import-primary", { stageId });
    }
  }

  async function importAddedMedia(stageId) {
    const paths = await pickPath();
    if (!paths || !paths.length) return;
    const result = await callApi("/api/project/stage/import-added", {
      method: "POST",
      body: JSON.stringify({ stage_id: stageId, paths }),
    });
    if (result) {
      activity("media.import-added", { stageId });
    }
  }

  function renderStageRow(stage) {
    const isActive = stage.id === activeStageId();
    const primaryPath = stage.primary_media?.path || "";
    const primaryName = primaryPath ? fileName(primaryPath) : "—";
    const primaryDuration = stage.primary_media?.duration_ms
      ? splitSeconds(stage.primary_media.duration_ms)
      : "";
    const addedCount = Array.isArray(stage.added_media) ? stage.added_media.length : 0;

    return `
      <tr class="stage-row ${isActive ? "stage-row-active" : ""}" data-stage-id="${stage.id}">
        <td class="stage-label">
          <span class="stage-order">${stage.order_index}.</span>
          <span>${stage.label || `Stage ${stage.order_index}`}</span>
        </td>
        <td class="stage-primary-media">
          <span class="media-name">${primaryName}</span>
          ${primaryDuration ? `<small>${primaryDuration}</small>` : ""}
        </td>
        <td class="stage-added-media">
          <span>${addedCount} source${addedCount !== 1 ? "s" : ""}</span>
        </td>
        <td class="stage-actions">
          ${!primaryPath
            ? '<button class="btn-sm btn-primary import-primary-btn" type="button">+ Primary</button>'
            : `<button class="btn-sm btn-ghost import-primary-btn" type="button">↻ Primary</button>`
          }
          <button class="btn-sm btn-secondary import-added-btn" type="button">+ Added</button>
        </td>
      </tr>`;
  }

  function bindEvents() {
    const table = $("media-stage-table");
    if (!table) return;

    table.querySelectorAll(".stage-row").forEach((row) => {
      row.addEventListener("click", (e) => {
        if (e.target.closest("button")) return;
        const stageId = row.dataset.stageId;
        if (stageId) selectStage(stageId);
      });
    });

    table.querySelectorAll(".import-primary-btn").forEach((btn) => {
      btn.addEventListener("click", (e) => {
        e.stopPropagation();
        const row = btn.closest(".stage-row");
        const stageId = row?.dataset.stageId;
        if (stageId) importPrimaryMedia(stageId);
      });
    });

    table.querySelectorAll(".import-added-btn").forEach((btn) => {
      btn.addEventListener("click", (e) => {
        e.stopPropagation();
        const row = btn.closest(".stage-row");
        const stageId = row?.dataset.stageId;
        if (stageId) importAddedMedia(stageId);
      });
    });
  }

  function render() {
    const pane = $("media-pane");
    if (!pane) return;

    const stageList = stages();
    const stageRows = stageList.length
      ? stageList.map((s) => renderStageRow(s)).join("")
      : '<tr><td colspan="4" class="empty-state">No stages yet. Import a PractiScore match file from the Project pane.</td></tr>';

    pane.innerHTML = `
      <div class="pane-section">
        <h3 class="section-title">Media</h3>
        <p class="section-desc">Import primary and added media for each stage.</p>
        <table id="media-stage-table" class="stage-table">
          <thead>
            <tr>
              <th>Stage</th>
              <th>Primary Media</th>
              <th>Added Media</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>${stageRows}</tbody>
        </table>
      </div>`;
    bindEvents();
  }

  function mount() {
    render();
  }

  return Object.freeze({
    render,
    mount,
    selectStage,
  });
}
