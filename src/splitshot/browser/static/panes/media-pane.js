export function createMediaPane({
  $ = (id) => document.getElementById(id),
  documentObject = document,
  getState = () => null,
  setActiveStageId = () => {},
  activity = () => {},
  callApi = async () => null,
  openPrimaryFileInput = () => {},
  openMergeMediaInput = () => {},
  fileName = (value) => String(value || ""),
  splitSeconds = (value) => String(value ?? ""),
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

  function activeStage() {
    return stages().find((stage) => stage.id === activeStageId()) || stages()[0] || null;
  }

  function hasProject() {
    return Boolean(String(project().path || "").trim());
  }

  function selectStage(stageId) {
    const proj = project();
    if (!proj || !stageId) return;
    proj.active_stage_id = stageId;
    setActiveStageId(stageId);
    sendKeepaliveJson("/api/project/select-stage", { active_stage_id: stageId });
    activity("media.select-stage", { stageId });
    render();
  }

  function stagePrimaryLabel(stage) {
    const path = stage?.primary_media?.path || "";
    return path ? fileName(path) : "No primary media";
  }

  function stagePrimaryDuration(stage) {
    const durationMs = stage?.primary_media?.duration_ms;
    return durationMs ? splitSeconds(durationMs) : "";
  }

  function stageAddedMedia(stage) {
    return Array.isArray(stage?.added_media) ? stage.added_media : [];
  }

  function selectStageAndOpen(stageId, opener, activityName) {
    if (!stageId || !hasProject()) return;
    selectStage(stageId);
    activity(activityName, { stageId });
    opener();
  }

  async function clearPrimary(stageId) {
    if (!stageId) return;
    await callApi("/api/project/stage/clear-primary", {
      stage_id: stageId,
    });
    activity("media.clear-primary", { stageId });
  }

  async function removeAdded(stageId, sourceId) {
    if (!stageId || !sourceId) return;
    await callApi("/api/project/stage/remove-added", {
      stage_id: stageId,
      source_id: sourceId,
    });
    activity("media.remove-added", { stageId, sourceId });
  }

  function renderStageRows() {
    return stages().map((stage) => {
      const isActive = stage.id === activeStageId();
      const addedCount = stageAddedMedia(stage).length;
      return `
        <tr class="stage-row ${isActive ? "stage-row-active" : ""}" data-stage-id="${stage.id}">
          <td class="stage-label">
            <span class="stage-order">${stage.order_index}.</span>
            <span>${stage.label || `Stage ${stage.order_index}`}</span>
          </td>
          <td class="stage-primary-media">
            <span class="media-name">${stagePrimaryLabel(stage)}</span>
            ${stagePrimaryDuration(stage) ? `<small>${stagePrimaryDuration(stage)}</small>` : ""}
          </td>
          <td class="stage-added-media">
            <span>${addedCount} item${addedCount === 1 ? "" : "s"}</span>
          </td>
          <td class="stage-actions">
            <button class="btn-sm btn-ghost media-select-stage-btn" type="button">Select</button>
            <button class="btn-sm btn-primary media-stage-primary-btn" type="button" ${hasProject() ? "" : "disabled"}>${stage.primary_media?.path ? "Replace" : "Primary"}</button>
            <button class="btn-sm btn-secondary media-stage-added-btn" type="button" ${hasProject() ? "" : "disabled"}>Add</button>
          </td>
        </tr>`;
    }).join("");
  }

  function renderAddedCards(stage) {
    const sources = stageAddedMedia(stage);
    if (!sources.length) {
      return '<div class="empty-state">No added media.</div>';
    }
    return sources.map((source, index) => {
      const asset = source.asset || source;
      const duration = asset.duration_ms ? splitSeconds(asset.duration_ms) : "";
      const trimActive = Boolean(
        source.trim_derivative
        && source.trim_derivative.active_path_kind === "local_derivative"
        && source.trim_derivative.derivative_path
      );
      return `
        <article class="merge-media-card" data-media-stage-source="${source.id}">
          <div class="merge-media-card-header">
            <strong>${index + 1}. ${fileName(asset.path || "")}</strong>
            <button class="btn-sm btn-danger media-remove-added-btn" type="button" data-source-id="${source.id}">Remove</button>
          </div>
          <div class="merge-media-card-body">
            <small class="merge-media-card-meta">
              ${asset.is_still_image ? "Image" : "Video"}${duration ? ` • ${duration}` : ""}${trimActive ? " • Trimmed" : ""}
            </small>
          </div>
        </article>`;
    }).join("");
  }

  function bindEvents(stage) {
    $("media-import-primary-btn")?.addEventListener("click", () => {
      selectStageAndOpen(stage?.id || "", openPrimaryFileInput, "media.import-primary");
    });
    $("media-clear-primary-btn")?.addEventListener("click", () => {
      clearPrimary(stage?.id || "");
    });
    $("media-add-added-btn")?.addEventListener("click", () => {
      selectStageAndOpen(stage?.id || "", openMergeMediaInput, "media.import-added");
    });
    documentObject.querySelectorAll(".media-remove-added-btn").forEach((button) => {
      button.addEventListener("click", () => {
        removeAdded(stage?.id || "", button.dataset.sourceId || "");
      });
    });
    documentObject.querySelectorAll(".stage-row").forEach((row) => {
      row.addEventListener("click", (event) => {
        if (event.target.closest("button")) return;
        const stageId = row.dataset.stageId || "";
        if (stageId) selectStage(stageId);
      });
    });
    documentObject.querySelectorAll(".media-select-stage-btn").forEach((button) => {
      button.addEventListener("click", (event) => {
        event.stopPropagation();
        const stageId = button.closest(".stage-row")?.dataset.stageId || "";
        if (stageId) selectStage(stageId);
      });
    });
    documentObject.querySelectorAll(".media-stage-primary-btn").forEach((button) => {
      button.addEventListener("click", (event) => {
        event.stopPropagation();
        const stageId = button.closest(".stage-row")?.dataset.stageId || "";
        selectStageAndOpen(stageId, openPrimaryFileInput, "media.import-primary");
      });
    });
    documentObject.querySelectorAll(".media-stage-added-btn").forEach((button) => {
      button.addEventListener("click", (event) => {
        event.stopPropagation();
        const stageId = button.closest(".stage-row")?.dataset.stageId || "";
        selectStageAndOpen(stageId, openMergeMediaInput, "media.import-added");
      });
    });
  }

  function render() {
    const pane = $("media-pane");
    if (!pane) return;
    const stage = activeStage();
    const primaryPath = stage?.primary_media?.path || "";
    const stageReady = hasProject() && Boolean(stage?.id);
    pane.innerHTML = `
      <div class="pane-section">
        <div class="section-header">
          <h3>Media</h3>
          <strong>${stage ? (stage.label || `Stage ${stage.order_index}`) : "No Stage"}</strong>
        </div>
        <div class="queue-toolbar">
          <button id="media-import-primary-btn" class="btn btn-primary" type="button" ${stageReady ? "" : "disabled"}>${primaryPath ? "Replace Primary" : "Import Primary"}</button>
          <button id="media-clear-primary-btn" class="btn btn-secondary" type="button" ${(stageReady && primaryPath) ? "" : "disabled"}>Clear Primary</button>
          <button id="media-add-added-btn" class="btn btn-secondary" type="button" ${stageReady ? "" : "disabled"}>Add Media</button>
        </div>
        <div class="pane-section">
          <div class="section-header sub-section-header">
            <h3>Primary</h3>
            <span>${primaryPath ? stagePrimaryLabel(stage) : "None"}</span>
          </div>
          <dl class="details">
            <div><dt>Duration</dt><dd>${stagePrimaryDuration(stage) || "—"}</dd></div>
            <div><dt>Added</dt><dd>${stage ? stageAddedMedia(stage).length : 0}</dd></div>
          </dl>
        </div>
        <div class="pane-section">
          <div class="section-header sub-section-header">
            <h3>Added Media</h3>
            <span>${stage ? stageAddedMedia(stage).length : 0}</span>
          </div>
          <div id="media-added-list" class="merge-media-list">${stage ? renderAddedCards(stage) : '<div class="empty-state">No stage selected.</div>'}</div>
        </div>
        <div class="pane-section">
          <div class="section-header sub-section-header">
            <h3>Stages</h3>
            <span>${stages().length}</span>
          </div>
          <table id="media-stage-table" class="stage-table">
            <thead>
              <tr>
                <th>Stage</th>
                <th>Primary</th>
                <th>Added</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>${stages().length ? renderStageRows() : '<tr><td colspan="4" class="empty-state">No stages.</td></tr>'}</tbody>
          </table>
        </div>
      </div>`;
    bindEvents(stage);
  }

  function mount() {
    render();
  }

  return Object.freeze({
    mount,
    render,
    selectStage,
  });
}
