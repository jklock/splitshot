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
  setStatus = () => {},
} = {}) {
  const mediaSectionExpansionKey = "splitshot.media.sectionExpanded";

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
    const stage = stages().find((item) => item.id === activeStageId()) || stages()[0] || null;
    if (!stage) return null;
    const activeId = activeStageId();
    if (!activeId || stage.id !== activeId) return stage;
    return {
      ...stage,
      primary_media: project().primary_video || stage.primary_media,
      added_media: project().merge_sources || stage.added_media,
    };
  }

  function hasOpenProject() {
    return Boolean(String(project().path || "").trim());
  }

  function htmlEscape(value) {
    return String(value || "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;");
  }

  function stageImported(stage) {
    return stage?.scoring?.imported_stage || null;
  }

  function stageDisplayNumber(stage) {
    return stage?.scoring?.stage_number ?? stage?.imported_stage_number ?? stage?.order_index ?? "";
  }

  function stageLabel(stage) {
    if (!stage) return "No stage";
    return stage.label || stageImported(stage)?.stage_name || `Stage ${stage.order_index}`;
  }

  function stageAddedMedia(stage) {
    return Array.isArray(stage?.added_media) ? stage.added_media : [];
  }

  function stageAssetCount(stage) {
    return (stage?.primary_media?.path ? 1 : 0) + stageAddedMedia(stage).length;
  }

  function assetTypeLabel(asset) {
    return asset?.is_still_image ? "Image" : "Video";
  }

  function assetMeta(asset) {
    const parts = [assetTypeLabel(asset)];
    const dur = asset?.duration_ms ? splitSeconds(asset.duration_ms) : "";
    if (dur) parts.push(dur);
    const dims = asset?.width && asset?.height ? `${asset.width}×${asset.height}` : "";
    if (dims) parts.push(dims);
    return parts.join(" · ");
  }

  function activeAssetMeta(sourceOrAsset) {
    const asset = sourceOrAsset?.asset || sourceOrAsset || {};
    const activeAsset = {
      ...asset,
      duration_ms: sourceOrAsset?.active_duration_ms ?? asset.duration_ms,
      width: sourceOrAsset?.active_width ?? asset.width,
      height: sourceOrAsset?.active_height ?? asset.height,
      media_kind: sourceOrAsset?.active_media_kind ?? asset.media_kind,
    };
    return assetMeta(activeAsset);
  }

  function joinProjectPath(base, leaf) {
    const normalized = String(base || "").trim().replace(/[\\/]+$/, "");
    if (!normalized) return "";
    return `${normalized}/${leaf}`;
  }

  function mediaPickerDefaultRoot() {
    const projectPath = String(project().path || "").trim();
    const inputRoot = joinProjectPath(projectPath, "Input");
    return inputRoot || projectPath || "";
  }

  function readSectionExpansion() {
    try {
      const parsed = JSON.parse(windowObject?.localStorage?.getItem(mediaSectionExpansionKey) || "{}");
      return parsed && typeof parsed === "object" ? parsed : {};
    } catch (_) {
      return {};
    }
  }

  function sectionExpanded(sectionId) {
    return readSectionExpansion()[sectionId] !== false;
  }

  function setSectionExpanded(sectionId, expanded) {
    const stored = readSectionExpansion();
    stored[sectionId] = Boolean(expanded);
    try {
      windowObject?.localStorage?.setItem(mediaSectionExpansionKey, JSON.stringify(stored));
    } catch (_) {}
  }

  function toggleSection(sectionId) {
    activity("media.toggle-section", { sectionId });
    setSectionExpanded(sectionId, !sectionExpanded(sectionId));
    render();
  }

  async function selectStage(stageId) {
    const proj = project();
    if (!proj || !stageId) return false;
    if (stageId === activeStageId()) return true;
    activity("media.select-stage", { stageId });
    const result = await callApi("/api/project/select-stage", { active_stage_id: stageId });
    if (!result) return false;
    setActiveStageId(stageId);
    render();
    return true;
  }

  async function createStage() {
    activity("media.create-stage");
    await callApi("/api/project/stage/create", {});
    setStatus("Created new stage.");
  }

  async function renameStage(stageId, label) {
    const trimmed = String(label || "").trim();
    if (!stageId || !trimmed) return;
    activity("media.rename-stage", { stageId, label: trimmed });
    await callApi("/api/project/stage/update", { stage_id: stageId, label: trimmed });
    setStatus(`Renamed stage to "${trimmed}".`);
  }

  async function deleteStage(stageId) {
    if (!stageId) return;
    activity("media.delete-stage", { stageId });
    await callApi("/api/project/stage/delete", { stage_id: stageId });
    setStatus("Deleted stage.");
  }

  async function clearPrimary(stageId) {
    if (!stageId) return;
    activity("media.clear-primary", { stageId });
    await callApi("/api/project/stage/clear-primary", { stage_id: stageId });
    setStatus("Cleared primary media.");
  }

  async function removeAdded(stageId, sourceId) {
    if (!stageId || !sourceId) return;
    activity("media.remove-added", { stageId, sourceId });
    await callApi("/api/project/stage/remove-added", { stage_id: stageId, source_id: sourceId });
    setStatus("Removed added media.");
  }

  async function setPrimary(stageId, sourceId) {
    if (!stageId || !sourceId) return;
    activity("media.set-primary", { stageId, sourceId });
    await callApi("/api/project/stage/set-primary", { stage_id: stageId, source_id: sourceId });
    setStatus("Set as primary media.");
  }

  async function openPrimaryForStage(stageId) {
    if (!stageId || !hasOpenProject()) return;
    if (!(await selectStage(stageId))) return;
    activity("media.import-primary", { stageId });
    const selectedPath = await pickPath("primary", null, null, mediaPickerDefaultRoot());
    if (selectedPath) {
      await callApi("/api/project/stage/import-primary", { stage_id: stageId, path: selectedPath });
      setStatus("Imported primary media.");
    }
  }

  async function openAddMoreForStage(stageId) {
    if (!stageId || !hasOpenProject()) return;
    if (!(await selectStage(stageId))) return;
    const stage = activeStage();
    if (!stage?.primary_media?.path) {
      setStatus("Add primary media before adding secondary media.");
      return;
    }
    activity("media.import-added", { stageId });
    const selectedPath = await pickPath("primary", null, null, mediaPickerDefaultRoot());
    if (selectedPath) {
      await callApi("/api/project/stage/import-added", { stage_id: stageId, path: selectedPath });
      setStatus("Imported added media.");
    }
  }

  function renderInventoryFileRow(stageId, source, isPrimary = false) {
    const asset = source.asset || source;
    const sourceId = isPrimary ? "primary" : (source.id || "");
    const activeName = source?.active_display_name || fileName(asset.path || "");
    return `
      <article class="media-asset-row" data-stage-id="${stageId}" data-source-id="${sourceId}">
        <div class="media-asset-copy">
          <strong>${htmlEscape(activeName)}</strong>
          <small>${htmlEscape(activeAssetMeta(source))}</small>
        </div>
        <div class="media-asset-actions">
          ${isPrimary
            ? `<button class="btn-sm btn-secondary media-replace-primary-btn" type="button" data-stage-id="${stageId}">Replace</button>
               <button class="btn-sm btn-danger media-remove-file-btn" type="button" data-stage-id="${stageId}" data-source-id="primary">Clear</button>`
            : `<button class="btn-sm btn-secondary media-set-primary-btn" type="button" data-stage-id="${stageId}" data-source-id="${sourceId}">Set Primary</button>
               <button class="btn-sm btn-danger media-remove-file-btn" type="button" data-stage-id="${stageId}" data-source-id="${sourceId}">Remove</button>`}
        </div>
      </article>
    `;
  }

  function renderActiveStageSection(stage) {
    const stageOptions = stages()
      .map((item) => `<option value="${item.id}" ${item.id === stage?.id ? "selected" : ""}>${htmlEscape(stageLabel(item))}</option>`)
      .join("");
    return `
      <section class="settings-section media-pane-section media-pane-section-static">
        <div class="section-header media-section-header">
          <strong>Stage</strong>
        </div>
        <div class="media-pane-section-body">
          <div class="control-grid">
            <label>Stage
              <select id="media-active-stage-select">${stageOptions}</select>
            </label>
            <label>Name
              <input id="media-active-stage-label" type="text" value="${htmlEscape(stage ? stageLabel(stage) : "")}" placeholder="Stage name" />
            </label>
          </div>
          <div class="media-active-stage-actions media-pane-actions media-pane-actions-split">
            <button class="btn-sm btn-primary media-save-stage-btn" type="button" ${stage ? "" : "disabled"}>Save</button>
            <button class="btn-sm btn-danger media-delete-stage-btn" type="button" data-stage-id="${stage?.id || ""}" ${stages().length > 1 ? "" : "disabled"}>Delete</button>
          </div>
          <button class="primary-button media-add-stage-btn media-add-stage-full" type="button">Add Stage</button>
        </div>
      </section>
    `;
  }

  function renderStagesSection(stage) {
    const added = stage ? stageAddedMedia(stage) : [];
    const primaryExpanded = sectionExpanded("primary");
    const addedExpanded = sectionExpanded("added");
    return `
      <section class="settings-section media-pane-section ${primaryExpanded ? "" : "collapsed"}">
        <div class="section-header media-section-header">
          <strong>Primary</strong>
          <div class="section-header-actions">
            ${stage?.primary_media?.path
              ? ""
              : `<button class="btn-sm btn-primary media-section-action-btn media-add-primary-btn" type="button" data-stage-id="${stage?.id || ""}">Add Primary</button>`}
            <button class="pane-toggle media-section-toggle" type="button" data-media-section="primary" aria-label="${primaryExpanded ? "Collapse" : "Expand"} Primary">${primaryExpanded ? "v" : ">"}</button>
          </div>
        </div>
        <div class="media-pane-section-body"${primaryExpanded ? "" : " hidden"}>
          ${stage?.primary_media?.path
            ? renderInventoryFileRow(stage.id, stage.primary_media, true)
            : '<div class="empty-state">No primary media.</div>'}
        </div>
      </section>
      <section class="settings-section media-pane-section ${addedExpanded ? "" : "collapsed"}">
        <div class="section-header media-section-header">
          <strong>Added Media</strong>
          <div class="section-header-actions">
            <button class="btn-sm btn-primary media-intake-btn media-section-action-btn media-add-more-btn" type="button" data-stage-id="${stage?.id || ""}" ${stage?.primary_media?.path ? "" : "disabled"}>Add Media</button>
            <button class="pane-toggle media-section-toggle" type="button" data-media-section="added" aria-label="${addedExpanded ? "Collapse" : "Expand"} Added Media">${addedExpanded ? "v" : ">"}</button>
          </div>
        </div>
        <div class="media-pane-section-body media-asset-stack"${addedExpanded ? "" : " hidden"}>
          ${added.length
            ? added.map((source) => renderInventoryFileRow(stage.id, source, false)).join("")
            : '<div class="empty-state">No added media.</div>'}
        </div>
      </section>
    `;
  }

  function bindEvents(pane) {
    if (!(pane instanceof HTMLElement)) return;
    pane.onclick = (event) => {
      const target = event.target instanceof HTMLElement ? event.target : null;
      if (!target) return;
      const toggle = target.closest(".media-section-toggle");
      if (toggle instanceof HTMLElement) {
        event.preventDefault();
        event.stopPropagation();
        toggleSection(toggle.dataset.mediaSection || "");
        return;
      }
      if (target.closest(".media-add-stage-btn")) {
        createStage();
        return;
      }
      if (target.closest(".media-save-stage-btn")) {
        const stage = activeStage();
        if (!stage) return;
        renameStage(stage.id, $("media-active-stage-label")?.value || "");
        return;
      }
      const deleteStageButton = target.closest(".media-delete-stage-btn");
      if (deleteStageButton instanceof HTMLElement) {
        deleteStage(deleteStageButton.dataset.stageId || "");
        return;
      }
      const addPrimaryButton = target.closest(".media-add-primary-btn, .media-replace-primary-btn");
      if (addPrimaryButton instanceof HTMLElement) {
        openPrimaryForStage(addPrimaryButton.dataset.stageId || activeStage()?.id || "");
        return;
      }
      const addMoreButton = target.closest(".media-add-more-btn");
      if (addMoreButton instanceof HTMLElement) {
        openAddMoreForStage(addMoreButton.dataset.stageId || activeStage()?.id || "");
        return;
      }
      const setPrimaryButton = target.closest(".media-set-primary-btn");
      if (setPrimaryButton instanceof HTMLElement) {
        setPrimary(setPrimaryButton.dataset.stageId || "", setPrimaryButton.dataset.sourceId || "");
        return;
      }
      const removeButton = target.closest(".media-remove-file-btn");
      if (removeButton instanceof HTMLElement) {
        const stageId = removeButton.dataset.stageId || "";
        const sourceId = removeButton.dataset.sourceId || "";
        if (sourceId === "primary") {
          clearPrimary(stageId);
          return;
        }
        removeAdded(stageId, sourceId);
        return;
      }
    };
    pane.onchange = (event) => {
      const target = event.target instanceof HTMLElement ? event.target : null;
      if (!target) return;
      if (target.id === "media-active-stage-select") {
        void selectStage(target.value || "");
      }
    };
  }

  function render() {
    const pane = $("media-pane");
    if (!pane) return;
    const stage = activeStage();
    const count = stageAssetCount(stage);
    pane.innerHTML = `
      <div class="pane-section media-pane-shell">
        <div class="section-header pane-title-row">
          <h3>Media</h3>
          <span class="pane-status-text">${count} asset${count === 1 ? "" : "s"}</span>
        </div>
        ${renderActiveStageSection(stage)}
        ${renderStagesSection(stage)}
      </div>
    `;
    bindEvents(pane);
  }

  function mount() {
    render();
  }

  return Object.freeze({
    mount,
    render,
    selectStage,
    toggleSection,
  });
}
