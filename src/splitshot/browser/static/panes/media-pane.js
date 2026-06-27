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
  sendKeepaliveJson = () => false,
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
    return stages().find((stage) => stage.id === activeStageId()) || stages()[0] || null;
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

  function stageDivision(stage) {
    return String(stageImported(stage)?.division || "");
  }

  function stageOfficialTime(stage) {
    const imported = stageImported(stage);
    const value = imported?.final_time ?? imported?.raw_seconds;
    if (value === null || value === undefined || value === "") return "";
    return `${Number(value).toFixed(2)}s`;
  }

  function stageAddedMedia(stage) {
    return Array.isArray(stage?.added_media) ? stage.added_media : [];
  }

  function stageAssetCount(stage) {
    return (stage?.primary_media?.path ? 1 : 0) + stageAddedMedia(stage).length;
  }

  function stageMeta(stage) {
    const parts = [];
    const number = stageDisplayNumber(stage);
    if (number !== "" && number !== null && number !== undefined) parts.push(`#${number}`);
    const division = stageDivision(stage);
    if (division) parts.push(division);
    const time = stageOfficialTime(stage);
    if (time) parts.push(time);
    return parts.join(" • ");
  }

  function assetTypeLabel(asset) {
    return asset?.is_still_image ? "Image" : "Video";
  }

  function assetMeta(asset) {
    const parts = [assetTypeLabel(asset)];
    const dur = asset?.duration_ms ? splitSeconds(asset.duration_ms) : "";
    if (dur) parts.push(dur);
    const dims = asset?.width && asset?.height ? `${asset.width}x${asset.height}` : "";
    if (dims) parts.push(dims);
    return parts.join(" • ");
  }

  function directoryOf(path) {
    const normalized = String(path || "").trim().replace(/[\\/]+$/, "");
    if (!normalized) return "";
    const index = Math.max(normalized.lastIndexOf("/"), normalized.lastIndexOf("\\"));
    return index > 0 ? normalized.slice(0, index) : "";
  }

  function joinProjectPath(base, leaf) {
    const normalized = String(base || "").trim().replace(/[\\/]+$/, "");
    if (!normalized) return "";
    return `${normalized}/${leaf}`;
  }

  function mediaPickerDefaultRoot(stage) {
    const primaryDir = directoryOf(stage?.primary_media?.path || "");
    if (primaryDir) return primaryDir;
    const firstAdded = stageAddedMedia(stage)[0];
    const firstAddedDir = directoryOf(firstAdded?.asset?.path || "");
    if (firstAddedDir) return firstAddedDir;
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
    const stored = readSectionExpansion();
    return stored[sectionId] !== false;
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

  function selectStage(stageId) {
    const proj = project();
    if (!proj || !stageId) return;
    proj.active_stage_id = stageId;
    setActiveStageId(stageId);
    sendKeepaliveJson("/api/project/select-stage", { active_stage_id: stageId });
    activity("media.select-stage", { stageId });
    render();
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
    const stage = stages().find((item) => item.id === stageId) || activeStage();
    selectStage(stageId);
    activity("media.import-primary", { stageId });
    const selectedPath = await pickPath("primary", null, null, mediaPickerDefaultRoot(stage));
    if (selectedPath) {
      await callApi("/api/project/stage/import-primary", { stage_id: stageId, path: selectedPath });
      setStatus("Imported primary media.");
    }
  }

  async function openAddMoreForStage(stageId) {
    if (!stageId || !hasOpenProject()) return;
    const stage = stages().find((item) => item.id === stageId) || activeStage();
    selectStage(stageId);
    activity("media.import-added", { stageId });
    const selectedPath = await pickPath("primary", null, null, mediaPickerDefaultRoot(stage));
    if (selectedPath) {
      await callApi("/api/project/stage/import-added", { stage_id: stageId, path: selectedPath });
      setStatus("Imported added media.");
    }
  }

  function renderInventoryFileRow(stageId, source, isPrimary = false) {
    const asset = source.asset || source;
    const sourceId = isPrimary ? "primary" : (source.id || "");
    return `
      <article class="media-asset-row" data-stage-id="${stageId}" data-source-id="${sourceId}">
        <div class="media-asset-copy">
          <strong>${isPrimary ? "Primary" : "Added"}</strong>
          <span>${htmlEscape(fileName(asset.path || ""))}</span>
          <small>${htmlEscape(assetMeta(asset))}</small>
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
          <strong>Active Stage</strong>
          <div class="section-header-actions">
            <span class="pane-summary-token">${htmlEscape(stage ? stageLabel(stage) : "No Stage")}</span>
          </div>
        </div>
        <div class="media-pane-section-body">
          <div class="control-grid">
            <label>Stage #
              <select id="media-active-stage-select">${stageOptions}</select>
            </label>
            <label>Stage Name
              <input id="media-active-stage-label" type="text" value="${htmlEscape(stage ? stageLabel(stage) : "")}" placeholder="Stage name" />
            </label>
          </div>
          <div class="media-active-stage-actions media-stage-nav-actions media-stage-nav-actions-split">
            <button class="btn-sm btn-primary media-save-stage-btn" type="button" ${stage ? "" : "disabled"}>Save Stage</button>
            <button class="btn-sm btn-danger media-delete-stage-btn" type="button" data-stage-id="${stage?.id || ""}" ${stages().length > 1 ? "" : "disabled"}>Delete Stage</button>
          </div>
        </div>
      </section>
    `;
  }

  function renderStagesSection(stage) {
    const expanded = sectionExpanded("stages");
    const navExpanded = sectionExpanded("stage-navigator");
    const added = stage ? stageAddedMedia(stage) : [];
    return `
      <section class="settings-section media-pane-section ${expanded ? "" : "collapsed"}">
        <div class="section-header media-section-header">
          <strong>Stages</strong>
          <div class="section-header-actions">
            <button class="pane-toggle media-section-toggle" type="button" data-media-section="stages" aria-label="${expanded ? "Collapse" : "Expand"} stages">${expanded ? "\u25BC" : "\u25B6"}</button>
          </div>
        </div>
        <div class="media-pane-section-body"${expanded ? "" : " hidden"}>
          <section class="media-pane-inner-section">
            <div class="media-inner-section-header">
              <strong>Primary</strong>
            </div>
            ${stage?.primary_media?.path
              ? renderInventoryFileRow(stage.id, stage.primary_media, true)
              : `<div class="empty-state">
                   <p>No primary asset for ${htmlEscape(stageLabel(stage))}.</p>
                   <button class="btn-sm btn-secondary media-add-primary-btn" type="button" data-stage-id="${stage?.id || ""}">Add Primary</button>
                 </div>`}
          </section>
          <section class="media-pane-inner-section">
            <div class="media-inner-section-header">
              <strong>Active Media</strong>
              <button class="btn-sm btn-secondary media-add-more-btn" type="button" data-stage-id="${stage?.id || ""}" ${stage ? "" : "disabled"}>Add Media</button>
            </div>
            <div class="media-asset-stack">
              ${added.length
                ? added.map((source) => renderInventoryFileRow(stage.id, source, false)).join("")
                : '<div class="empty-state">No added media for this stage.</div>'}
            </div>
          </section>
          <section class="media-pane-inner-section">
            <div class="media-inner-section-header">
              <strong>Stage Navigator</strong>
              <button class="pane-toggle media-section-toggle" type="button" data-media-section="stage-navigator" aria-label="${navExpanded ? "Collapse" : "Expand"} stage navigator">${navExpanded ? "\u25BC" : "\u25B6"}</button>
            </div>
            <div class="media-stage-nav-list"${navExpanded ? "" : " hidden"}>
              ${stages().map((item) => `
                <article class="media-stage-nav-card ${item.id === stage?.id ? "selected" : ""}" data-stage-nav-id="${item.id}">
                  <div class="media-stage-nav-copy">
                    <strong>${htmlEscape(stageLabel(item))}</strong>
                    <small>${htmlEscape(stageMeta(item) || `${stageAssetCount(item)} assets`)}</small>
                  </div>
                  <div class="media-stage-nav-actions">
                    ${item.id === stage?.id ? '<span class="primary-badge">Live</span>' : '<button class="btn-sm btn-ghost media-edit-stage-btn" type="button" data-stage-id="' + item.id + '">Select</button>'}
                  </div>
                </article>
              `).join("")}
            </div>
          </section>
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
      const editStageButton = target.closest(".media-edit-stage-btn");
      if (editStageButton instanceof HTMLElement) {
        selectStage(editStageButton.dataset.stageId || "");
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
      const navCard = target.closest("[data-stage-nav-id]");
      if (navCard instanceof HTMLElement) {
        selectStage(navCard.dataset.stageNavId || "");
      }
    };
    pane.onchange = (event) => {
      const target = event.target instanceof HTMLElement ? event.target : null;
      if (!target) return;
      if (target.id === "media-active-stage-select") {
        selectStage(target.value || "");
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
          <span class="pane-summary-token">${count} asset${count === 1 ? "" : "s"}</span>
        </div>
        ${renderActiveStageSection(stage)}
        ${renderStagesSection(stage)}
        <button class="primary-button media-add-stage-btn media-add-stage-full" type="button">Add Stage</button>
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
