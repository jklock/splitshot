export function createQueuePane({
  $ = (id) => document.getElementById(id),
  documentObject = document,
  windowObject = window,
  getState = () => null,
  activity = () => {},
  callApi = async () => null,
  openProcessingLog = async () => {},
  fileName = (value) => String(value || ""),
  setStatus = () => {},
  sendKeepaliveJson = () => false,
} = {}) {
  let queueSettingsSavePromise = Promise.resolve();

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
    return `${primaryName} · ${assetCount} asset${assetCount === 1 ? "" : "s"}`;
  }

  function queueEntryAssetSummary(entry, stage) {
    const snapshot = entry?.snapshot || {};
    const primary = snapshot.primary_media || stage?.primary_media || {};
    const added = Array.isArray(snapshot.added_media) ? snapshot.added_media : (Array.isArray(stage?.added_media) ? stage.added_media : []);
    const primaryName = primary?.path ? fileName(primary.path) : "No primary";
    const assetCount = (primary?.path ? 1 : 0) + added.length;
    return `${primaryName} · ${assetCount} asset${assetCount === 1 ? "" : "s"}`;
  }

  function queueStatusLabel(status) {
    return {
      not_queued: "Not queued",
      queued: "Queued",
      processing: "Processing",
      complete: "Complete",
      failed: "Failed",
      stale: "Stale",
    }[status] || String(status || "Not queued");
  }

  function queueActionLabel(stageId) {
    const entry = findQueueEntry(stageId);
    const status = String(entry?.status || "not_queued");
    if (status === "not_queued") return "Queue";
    if (status === "stale" || status === "failed" || status === "complete") return "Requeue";
    if (status === "processing") return "Processing";
    return "Unqueue";
  }

  function saveQueueSettings(payload) {
    project().queue_settings = {
      ...(project().queue_settings || {}),
      ...payload,
    };
    queueSettingsSavePromise = queueSettingsSavePromise
      .catch(() => null)
      .then(() => callApi("/api/project/queue/settings", payload));
    return queueSettingsSavePromise;
  }

  async function updateQueueMembership(stageId) {
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

  async function queueAllFiles() {
    const button = $("queue-all-btn");
    if (button) button.disabled = true;
    activity("queue.add-all");
    try {
      const result = await callApi("/api/project/queue/add-all", {});
      if (result) setStatus(result.status || "Queued all files.");
    } finally {
      if (button) button.disabled = false;
    }
  }

  async function processAll() {
    activity("queue.process");
    setStatus("Processing queued stages...");
    await openProcessingLog("Starting queue processing…");
    await callApi("/api/project/queue/process", { mode: "individual" });
  }

  async function processIntoOneFile() {
    activity("queue.process-combined");
    setStatus("Processing combined queue export...");
    await openProcessingLog("Starting combined queue processing…");
    await callApi("/api/project/queue/process", { mode: "combined" });
  }

  function renderQueueStage(stage) {
    const stageId = stage.id;
    const queueEntry = findQueueEntry(stageId);
    const status = queueEntry?.status || stage?.queue_status || "not_queued";
    const actionLabel = queueActionLabel(stageId);
    const disabled = status === "processing" || !stage?.primary_media?.path;
    return `
      <article class="queue-stage-card" data-queue-stage-id="${stageId}">
        <div class="queue-stage-header">
          <div class="queue-stage-copy">
            <strong>${stageLabel(stage)}</strong>
            <small>${stageAssetSummary(stage)}</small>
          </div>
          <div class="queue-stage-header-actions">
            <span class="queue-status-text queue-status-${status}">${queueStatusLabel(status)}</span>
            <button class="btn-sm btn-secondary queue-membership-btn" type="button" data-stage-id="${stageId}" ${disabled ? "disabled" : ""}>${actionLabel}</button>
          </div>
        </div>
      </article>
    `;
  }

  function renderControlsSection() {
    const combinedOutput = combinedOutputPath();
    const queueSettings = project()?.queue_settings || {};
    const introPath = project()?.intro_clip?.asset?.path || queueSettings.intro_path || "";
    const outroPath = project()?.outro_clip?.asset?.path || queueSettings.outro_path || "";
    return `
      <section class="settings-section queue-pane-section">
        <div class="section-header media-section-header">
          <strong>Match Output</strong>
        </div>
        <div class="queue-controls-body">
          <div class="queue-boundary-actions queue-include-actions">
            <label class="check-row"><input id="queue-include-intro" type="checkbox" ${queueSettings.include_intro ? "checked" : ""} ${introPath ? "" : "disabled"} /> Include intro</label>
            <label class="check-row"><input id="queue-include-outro" type="checkbox" ${queueSettings.include_outro ? "checked" : ""} ${outroPath ? "" : "disabled"} /> Include outro</label>
          </div>
          <button id="queue-show-output-folder" class="btn btn-secondary" type="button" ${project().output_root ? "" : "disabled"}>Show Output Folder</button>
          <button id="queue-show-log" class="btn btn-secondary" type="button">Show Log</button>
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

  function renderStructureKey() {
    const queueSettings = project()?.queue_settings || {};
    return JSON.stringify({
      combined_output: combinedOutputPath(),
      has_intro: Boolean(project()?.intro_clip?.asset?.path || queueSettings.intro_path),
      has_outro: Boolean(project()?.outro_clip?.asset?.path || queueSettings.outro_path),
      has_output_root: Boolean(project()?.output_root),
      stages: stages().map((stage) => {
        const entry = findQueueEntry(stage.id);
        return {
          id: stage.id,
          label: stageLabel(stage),
          primary: stage?.primary_media?.path || "",
          added: (stage?.added_media || []).map((asset) => asset?.path || ""),
          status: entry?.status || stage?.queue_status || "not_queued",
        };
      }),
    });
  }

  function syncScalarControls(pane) {
    const queueSettings = project()?.queue_settings || {};
    const syncValue = (id, value) => {
      const control = $(id);
      if (!control || documentObject.activeElement === control) return;
      control.value = String(value);
    };
    const syncChecked = (id, checked) => {
      const control = $(id);
      if (!control || documentObject.activeElement === control) return;
      control.checked = Boolean(checked);
    };
    syncValue("queue-fade-in", Number(queueSettings.fade_in_s ?? 0.5));
    syncValue("queue-fade-out", Number(queueSettings.fade_out_s ?? 0.5));
    syncChecked("queue-include-intro", queueSettings.include_intro);
    syncChecked("queue-include-outro", queueSettings.include_outro);
    const status = pane.querySelector(".pane-status-text");
    if (status) status.textContent = `${queuedCount()} queued`;
  }

  function bindEvents(pane) {
    if (!(pane instanceof HTMLElement)) return;
    pane.onclick = (event) => {
      const target = event.target instanceof HTMLElement ? event.target : null;
      if (!target) return;
      const membershipButton = target.closest(".queue-membership-btn");
      if (membershipButton instanceof HTMLElement) {
        event.stopPropagation();
        updateQueueMembership(membershipButton.dataset.stageId || "");
        return;
      }
      if (target.closest("#queue-show-output-folder")) {
        callApi("/api/project/output/reveal", {});
        return;
      }
      if (target.closest("#queue-show-log")) {
        openProcessingLog();
        return;
      }
      if (target.closest("#queue-all-btn")) {
        void queueAllFiles();
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
    };
    pane.onchange = (event) => {
      const target = event.target instanceof HTMLElement ? event.target : null;
      if (!target) return;
      if (["queue-fade-in", "queue-fade-out", "queue-include-intro", "queue-include-outro"].includes(target.id)) {
        saveQueueSettings({
          fade_in_s: Math.max(0, Number($("queue-fade-in")?.value || 0)),
          fade_out_s: Math.max(0, Number($("queue-fade-out")?.value || 0)),
          include_intro: Boolean($("queue-include-intro")?.checked),
          include_outro: Boolean($("queue-include-outro")?.checked),
        });
      }
    };
  }

  function render() {
    const pane = $("queue-pane");
    if (!pane) return;
    const structureKey = renderStructureKey();
    if (pane.dataset.renderStructureKey === structureKey && pane.querySelector(".queue-pane-shell")) {
      syncScalarControls(pane);
      return;
    }
    const count = queuedCount();
    pane.innerHTML = `
      <div class="pane-section queue-pane-shell">
        <div class="section-header pane-title-row">
          <h3>Queue</h3>
          <span class="pane-status-text">${count} queued</span>
        </div>
        ${renderControlsSection()}
        <section class="settings-section queue-pane-section">
          <div class="section-header media-section-header">
            <strong>Output Fades</strong>
          </div>
          <div class="control-grid">
            <label>Fade in (seconds)
              <input id="queue-fade-in" type="number" min="0" step="0.1" value="${Number(project()?.queue_settings?.fade_in_s ?? 0.5)}" />
            </label>
            <label>Fade out (seconds)
              <input id="queue-fade-out" type="number" min="0" step="0.1" value="${Number(project()?.queue_settings?.fade_out_s ?? 0.5)}" />
            </label>
          </div>
        </section>
        <section class="settings-section queue-pane-section queue-process-section">
          <div class="section-header media-section-header">
            <strong>Process</strong>
          </div>
          <div class="queue-process-actions">
            <button id="queue-all-btn" class="btn btn-secondary" type="button" ${stages().some((stage) => stage?.primary_media?.path) ? "" : "disabled"}>Queue All Files</button>
            <button id="queue-process-btn" class="btn btn-primary queue-process-btn" type="button">Process Queue</button>
            <button id="queue-combined-btn" class="btn queue-combined-btn" type="button">Process as One File</button>
          </div>
        </section>
        <section class="settings-section queue-pane-section">
          <div class="section-header media-section-header">
            <strong>Match Stages</strong>
          </div>
          <div class="queue-stage-list">
            ${stages().length ? stages().map((stage) => renderQueueStage(stage)).join("") : '<div class="empty-state">No match stages loaded.</div>'}
          </div>
        </section>
      </div>
    `;
    pane.dataset.renderStructureKey = structureKey;
    bindEvents(pane);
  }

  function mount() {
    render();
  }

  return Object.freeze({
    render,
    mount,
    updateQueueMembership,
  });
}
